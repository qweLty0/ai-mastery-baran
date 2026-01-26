"""
Business Directory Scrapers (Europages, Kompass, etc.)
These are public business directories designed for B2B discovery
"""
import re
import logging
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class EuropagesScraper(BaseScraper):
    """
    Scraper for Europages - Europe's leading B2B directory
    https://www.europages.com
    """

    BASE_URL = "https://www.europages.com"

    def get_source_name(self) -> str:
        return "europages"

    def search(self, query: str, location: str = None, max_pages: int = 5) -> List[Dict]:
        """
        Search Europages for companies

        Args:
            query: Search term (e.g., "textile importer")
            location: Country or city
            max_pages: Maximum number of result pages to scrape
        """
        leads = []

        # Build search URL
        search_term = query
        if location:
            search_term = f"{query} {location}"

        for page in range(1, max_pages + 1):
            page_leads = self._scrape_search_page(search_term, page)
            if not page_leads:
                break
            leads.extend(page_leads)
            logger.info(f"Scraped page {page}, total leads: {len(leads)}")

        return leads

    def _scrape_search_page(self, query: str, page: int) -> List[Dict]:
        """Scrape a single search result page"""
        leads = []

        url = f"{self.BASE_URL}/en/search?q={quote_plus(query)}&page={page}"
        soup = self.fetch_page(url)

        if not soup:
            return leads

        # Find company cards
        company_cards = soup.find_all("article", class_=re.compile(r"company-card|result"))

        if not company_cards:
            # Try alternative selectors
            company_cards = soup.find_all("div", class_=re.compile(r"company|result"))

        for card in company_cards:
            try:
                lead = self._parse_company_card(card)
                if lead and lead.get("company_name"):
                    leads.append(lead)
            except Exception as e:
                logger.debug(f"Error parsing company card: {e}")
                continue

        return leads

    def _parse_company_card(self, card: BeautifulSoup) -> Optional[Dict]:
        """Parse a company card from search results"""
        lead = {"source": self.get_source_name()}

        # Company name
        name_elem = card.find(["h2", "h3", "a"], class_=re.compile(r"name|title|company"))
        if name_elem:
            lead["company_name"] = self.clean_text(name_elem.get_text())

            # Get company profile URL
            if name_elem.name == "a":
                lead["source_url"] = urljoin(self.BASE_URL, name_elem.get("href", ""))
            else:
                link = card.find("a")
                if link:
                    lead["source_url"] = urljoin(self.BASE_URL, link.get("href", ""))

        # Location
        location_elem = card.find(class_=re.compile(r"location|country|address"))
        if location_elem:
            location_text = self.clean_text(location_elem.get_text())
            # Try to split into city and country
            parts = location_text.split(",")
            if len(parts) >= 2:
                lead["city"] = parts[0].strip()
                lead["country"] = parts[-1].strip()
            else:
                lead["country"] = location_text

        # Description/Activity
        desc_elem = card.find(class_=re.compile(r"description|activity|sector"))
        if desc_elem:
            lead["industry"] = self.clean_text(desc_elem.get_text())

        # Extract any visible contact info
        card_text = card.get_text()
        emails = self.extract_email_from_text(card_text)
        phones = self.extract_phone_from_text(card_text)

        if emails:
            lead["email"] = emails[0]
        if phones:
            lead["phone"] = phones[0]

        return lead

    def get_company_details(self, profile_url: str) -> Dict:
        """
        Scrape detailed company information from profile page
        """
        details = {}

        soup = self.fetch_page(profile_url)
        if not soup:
            return details

        # Extract all text for contact info
        page_text = soup.get_text()
        emails = self.extract_email_from_text(page_text)
        phones = self.extract_phone_from_text(page_text)

        if emails:
            details["email"] = emails[0]
        if phones:
            details["phone"] = phones[0]

        # Website
        website_elem = soup.find("a", href=re.compile(r"^https?://(?!.*europages)"))
        if website_elem:
            details["website"] = website_elem.get("href")

        # Company size
        size_elem = soup.find(text=re.compile(r"employees|staff|personnel", re.I))
        if size_elem:
            parent = size_elem.find_parent()
            if parent:
                size_text = self.clean_text(parent.get_text())
                details["company_size"] = size_text

        # Address
        address_elem = soup.find(class_=re.compile(r"address|location"))
        if address_elem:
            details["address"] = self.clean_text(address_elem.get_text())

        return details


class KompassScraper(BaseScraper):
    """
    Scraper for Kompass - Global B2B directory
    https://www.kompass.com
    """

    BASE_URL = "https://www.kompass.com"

    def get_source_name(self) -> str:
        return "kompass"

    def search(self, query: str, location: str = None, max_pages: int = 3) -> List[Dict]:
        """Search Kompass directory"""
        leads = []

        search_term = query
        if location:
            search_term = f"{query} {location}"

        for page in range(1, max_pages + 1):
            url = f"{self.BASE_URL}/searchCompanies?text={quote_plus(search_term)}&page={page}"

            soup = self.fetch_page(url)
            if not soup:
                break

            # Find company listings
            companies = soup.find_all("div", class_=re.compile(r"company|result|listing"))

            if not companies:
                break

            for company in companies:
                try:
                    lead = self._parse_listing(company)
                    if lead:
                        leads.append(lead)
                except Exception as e:
                    logger.debug(f"Error parsing Kompass listing: {e}")

        return leads

    def _parse_listing(self, listing: BeautifulSoup) -> Optional[Dict]:
        """Parse a company listing"""
        lead = {"source": self.get_source_name()}

        # Company name
        name_elem = listing.find(["h2", "h3", "a"], class_=re.compile(r"name|title"))
        if name_elem:
            lead["company_name"] = self.clean_text(name_elem.get_text())

        # Location
        location_elem = listing.find(class_=re.compile(r"location|country"))
        if location_elem:
            lead["country"] = self.clean_text(location_elem.get_text())

        # Profile URL
        link = listing.find("a", href=True)
        if link:
            lead["source_url"] = urljoin(self.BASE_URL, link.get("href"))

        # Contact info
        text = listing.get_text()
        emails = self.extract_email_from_text(text)
        phones = self.extract_phone_from_text(text)

        if emails:
            lead["email"] = emails[0]
        if phones:
            lead["phone"] = phones[0]

        return lead if lead.get("company_name") else None


class TurkishExporterScraper(BaseScraper):
    """
    Scraper for TurkishExporter.net - Turkish B2B platform
    """

    BASE_URL = "https://www.turkishexporter.net"

    def get_source_name(self) -> str:
        return "turkish_exporter"

    def search(self, query: str, location: str = None) -> List[Dict]:
        """Search Turkish Exporter directory"""
        leads = []

        # For Turkish Exporter, we search for importers in target countries
        url = f"{self.BASE_URL}/search?q={quote_plus(query)}"

        soup = self.fetch_page(url)
        if not soup:
            return leads

        # Parse results
        results = soup.find_all("div", class_=re.compile(r"company|result|listing"))

        for result in results:
            try:
                name_elem = result.find(["h2", "h3", "a"])
                if name_elem:
                    lead = {
                        "company_name": self.clean_text(name_elem.get_text()),
                        "source": self.get_source_name(),
                        "search_query": query
                    }

                    text = result.get_text()
                    emails = self.extract_email_from_text(text)
                    if emails:
                        lead["email"] = emails[0]

                    leads.append(lead)
            except Exception:
                continue

        return leads
