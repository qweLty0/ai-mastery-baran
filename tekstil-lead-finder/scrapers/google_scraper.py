"""
Google Search Scraper for finding textile buyers and importers
Uses DuckDuckGo as a fallback (more scraping-friendly)
"""
import re
import logging
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urlparse
import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GoogleScraper(BaseScraper):
    """Scraper for Google Search results"""

    def get_source_name(self) -> str:
        return "google"

    def search(self, query: str, location: str = None, max_results: int = 30) -> List[Dict]:
        """
        Search Google for potential leads

        Args:
            query: Search query (e.g., "textile importer")
            location: Location to add to query (e.g., "Berlin Germany")
            max_results: Maximum number of results to return
        """
        leads = []

        # Build search query
        search_query = query
        if location:
            search_query = f"{query} {location}"

        logger.info(f"Searching Google for: {search_query}")

        # Try DuckDuckGo HTML (more reliable for scraping)
        leads = self._search_duckduckgo(search_query, max_results)

        if not leads:
            # Fallback to Google (might get blocked)
            leads = self._search_google(search_query, max_results)

        return leads

    def _search_duckduckgo(self, query: str, max_results: int) -> List[Dict]:
        """Search using DuckDuckGo HTML version"""
        leads = []
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

        soup = self.fetch_page(url)
        if not soup:
            return leads

        results = soup.find_all("div", class_="result")

        for result in results[:max_results]:
            try:
                # Extract title and URL
                title_elem = result.find("a", class_="result__a")
                if not title_elem:
                    continue

                title = self.clean_text(title_elem.get_text())
                link = title_elem.get("href", "")

                # Extract snippet
                snippet_elem = result.find("a", class_="result__snippet")
                snippet = self.clean_text(snippet_elem.get_text()) if snippet_elem else ""

                # Parse domain for company website
                parsed_url = urlparse(link)
                domain = parsed_url.netloc.replace("www.", "")

                # Skip non-company results
                if self._is_skip_domain(domain):
                    continue

                lead = {
                    "company_name": self._extract_company_name(title, domain),
                    "website": f"https://{domain}" if domain else link,
                    "source_url": link,
                    "snippet": snippet,
                    "search_query": query,
                    "source": "duckduckgo"
                }

                # Try to extract contact info from snippet
                emails = self.extract_email_from_text(snippet)
                phones = self.extract_phone_from_text(snippet)

                if emails:
                    lead["email"] = emails[0]
                if phones:
                    lead["phone"] = phones[0]

                leads.append(lead)

            except Exception as e:
                logger.debug(f"Error parsing result: {e}")
                continue

        logger.info(f"Found {len(leads)} leads from DuckDuckGo")
        return leads

    def _search_google(self, query: str, max_results: int) -> List[Dict]:
        """Search using Google (fallback)"""
        leads = []
        url = f"https://www.google.com/search?q={quote_plus(query)}&num={max_results}"

        soup = self.fetch_page(url)
        if not soup:
            return leads

        # Google search results structure
        for g in soup.find_all("div", class_="g"):
            try:
                title_elem = g.find("h3")
                link_elem = g.find("a")

                if not title_elem or not link_elem:
                    continue

                title = self.clean_text(title_elem.get_text())
                link = link_elem.get("href", "")

                if not link.startswith("http"):
                    continue

                parsed_url = urlparse(link)
                domain = parsed_url.netloc.replace("www.", "")

                if self._is_skip_domain(domain):
                    continue

                lead = {
                    "company_name": self._extract_company_name(title, domain),
                    "website": f"https://{domain}",
                    "source_url": link,
                    "search_query": query,
                    "source": "google"
                }

                leads.append(lead)

            except Exception as e:
                logger.debug(f"Error parsing Google result: {e}")
                continue

        return leads

    def _is_skip_domain(self, domain: str) -> bool:
        """Check if domain should be skipped (social media, directories, etc.)"""
        skip_domains = [
            "facebook.com", "twitter.com", "linkedin.com", "instagram.com",
            "youtube.com", "pinterest.com", "tiktok.com",
            "wikipedia.org", "amazon.com", "ebay.com", "alibaba.com",
            "google.com", "bing.com", "yahoo.com",
            "yelp.com", "yellowpages.com", "tripadvisor.com",
            "reddit.com", "quora.com", "medium.com",
            "gov.", ".gov", ".edu",
        ]
        return any(skip in domain.lower() for skip in skip_domains)

    def _extract_company_name(self, title: str, domain: str) -> str:
        """Try to extract company name from title or domain"""
        # Clean up title
        separators = [" - ", " | ", " – ", " :: ", " : "]
        for sep in separators:
            if sep in title:
                title = title.split(sep)[0]
                break

        # If title is too generic, use domain
        if len(title) < 3 or title.lower() in ["home", "welcome", "index"]:
            # Convert domain to readable name
            name = domain.split(".")[0]
            name = re.sub(r"[-_]", " ", name)
            return name.title()

        return title.strip()

    def search_with_contact_page(self, query: str, location: str = None) -> List[Dict]:
        """
        Search and then visit each result's contact page to find emails

        This is more thorough but slower
        """
        leads = self.search(query, location)

        for lead in leads:
            if not lead.get("email") and lead.get("website"):
                contact_info = self._scrape_contact_page(lead["website"])
                lead.update(contact_info)
                self.random_delay()

        return leads

    def _scrape_contact_page(self, website: str) -> Dict:
        """Visit website's contact page to extract contact info"""
        contact_info = {}
        contact_paths = ["/contact", "/contact-us", "/kontakt", "/about", "/about-us", "/impressum"]

        # First try the homepage
        soup = self.fetch_page(website)
        if soup:
            page_text = soup.get_text()
            emails = self.extract_email_from_text(page_text)
            phones = self.extract_phone_from_text(page_text)

            if emails:
                contact_info["email"] = emails[0]
            if phones:
                contact_info["phone"] = phones[0]

        # If no email found, try contact pages
        if not contact_info.get("email"):
            for path in contact_paths:
                try:
                    contact_url = website.rstrip("/") + path
                    soup = self.fetch_page(contact_url)
                    if soup:
                        page_text = soup.get_text()
                        emails = self.extract_email_from_text(page_text)
                        phones = self.extract_phone_from_text(page_text)

                        if emails:
                            contact_info["email"] = emails[0]
                        if phones and not contact_info.get("phone"):
                            contact_info["phone"] = phones[0]

                        if contact_info.get("email"):
                            break

                except Exception:
                    continue

        return contact_info


class GoogleMapsSearcher(BaseScraper):
    """
    Strategy for finding businesses on Google Maps
    Note: Direct scraping is against ToS, use official API or manual process
    """

    def get_source_name(self) -> str:
        return "google_maps"

    def generate_search_urls(self, query: str, locations: List[str]) -> List[str]:
        """
        Generate Google Maps search URLs for manual research

        These URLs can be opened in a browser to manually find leads
        """
        urls = []
        base_url = "https://www.google.com/maps/search/"

        for location in locations:
            search_term = f"{query} {location}"
            url = f"{base_url}{quote_plus(search_term)}"
            urls.append({
                "location": location,
                "query": query,
                "url": url
            })

        return urls

    def search(self, query: str, location: str = None) -> List[Dict]:
        """
        Returns search URLs for manual research
        Direct Google Maps scraping requires API or Selenium
        """
        logger.info("Google Maps direct scraping not implemented. Use generate_search_urls() for manual research.")
        return []
