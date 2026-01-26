"""
Email Finder and Validator Tools
Finds and validates email addresses for leads
"""
import re
import logging
import dns.resolver
from typing import List, Dict, Optional, Tuple
from email_validator import validate_email, EmailNotValidError
from urllib.parse import urlparse
import requests

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class EmailFinder:
    """Find email addresses for companies"""

    # Common email patterns
    EMAIL_PATTERNS = [
        "{first}@{domain}",
        "{last}@{domain}",
        "{first}.{last}@{domain}",
        "{f}{last}@{domain}",
        "{first}{l}@{domain}",
        "{first}_{last}@{domain}",
        "info@{domain}",
        "contact@{domain}",
        "sales@{domain}",
        "export@{domain}",
        "import@{domain}",
        "purchasing@{domain}",
        "procurement@{domain}",
        "buyer@{domain}",
        "orders@{domain}",
        "inquiry@{domain}",
        "hello@{domain}",
    ]

    def __init__(self):
        self.scraper = BaseScraper.__subclasses__()[0]() if BaseScraper.__subclasses__() else None

    def find_email_from_website(self, website: str) -> List[str]:
        """
        Scrape website to find email addresses
        """
        emails = set()

        if not website:
            return list(emails)

        # Normalize website URL
        if not website.startswith("http"):
            website = f"https://{website}"

        # Pages to check
        pages_to_check = [
            "",
            "/contact",
            "/contact-us",
            "/kontakt",
            "/about",
            "/about-us",
            "/impressum",
            "/imprint",
            "/legal",
        ]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        for page in pages_to_check:
            try:
                url = website.rstrip("/") + page
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    # Find emails in page
                    page_emails = self._extract_emails(response.text)
                    emails.update(page_emails)

                    if emails:
                        break  # Found emails, no need to check more pages

            except Exception as e:
                logger.debug(f"Error fetching {url}: {e}")
                continue

        # Filter and prioritize emails
        return self._prioritize_emails(list(emails))

    def _extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)

        # Filter out invalid/image emails
        filtered = []
        for email in emails:
            email_lower = email.lower()
            if not any(x in email_lower for x in [
                '.png', '.jpg', '.gif', '.svg', '.webp',
                'example.com', 'test.com', 'domain.com',
                'email.com', 'mail.com', 'yourdomain'
            ]):
                filtered.append(email.lower())

        return list(set(filtered))

    def _prioritize_emails(self, emails: List[str]) -> List[str]:
        """
        Sort emails by relevance for B2B outreach
        Priority: sales/export/import > info/contact > personal
        """
        priority_prefixes = [
            'export', 'import', 'sales', 'purchasing', 'procurement',
            'buyer', 'orders', 'inquiry', 'info', 'contact', 'hello'
        ]

        def get_priority(email: str) -> int:
            prefix = email.split('@')[0].lower()
            for i, p in enumerate(priority_prefixes):
                if p in prefix:
                    return i
            return len(priority_prefixes)

        return sorted(emails, key=get_priority)

    def generate_email_patterns(self, domain: str, first_name: str = None,
                                 last_name: str = None) -> List[str]:
        """
        Generate possible email addresses based on common patterns
        """
        emails = []

        # Generic emails that don't need names
        generic_patterns = [
            "info@{domain}",
            "contact@{domain}",
            "sales@{domain}",
            "export@{domain}",
            "import@{domain}",
            "purchasing@{domain}",
            "orders@{domain}",
            "hello@{domain}",
        ]

        for pattern in generic_patterns:
            emails.append(pattern.format(domain=domain))

        # Personal emails if name is provided
        if first_name and last_name:
            first = first_name.lower()
            last = last_name.lower()
            f = first[0] if first else ""
            l = last[0] if last else ""

            personal_patterns = [
                f"{first}@{domain}",
                f"{last}@{domain}",
                f"{first}.{last}@{domain}",
                f"{first}_{last}@{domain}",
                f"{f}{last}@{domain}",
                f"{first}{l}@{domain}",
                f"{first}{last}@{domain}",
            ]
            emails.extend(personal_patterns)

        return emails

    def get_domain_from_website(self, website: str) -> str:
        """Extract domain from website URL"""
        if not website:
            return ""

        if not website.startswith("http"):
            website = f"https://{website}"

        parsed = urlparse(website)
        domain = parsed.netloc.replace("www.", "")
        return domain


class EmailValidator:
    """Validate email addresses"""

    def __init__(self):
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = 5
        self.resolver.lifetime = 5

    def validate(self, email: str) -> Tuple[bool, str]:
        """
        Validate an email address

        Returns:
            Tuple of (is_valid, message)
        """
        # Step 1: Format validation
        try:
            valid = validate_email(email)
            email = valid.email
        except EmailNotValidError as e:
            return False, str(e)

        # Step 2: Domain MX record check
        domain = email.split('@')[1]
        has_mx = self._check_mx_record(domain)

        if not has_mx:
            return False, "Domain has no MX records"

        return True, "Valid"

    def _check_mx_record(self, domain: str) -> bool:
        """Check if domain has MX records"""
        try:
            self.resolver.resolve(domain, 'MX')
            return True
        except Exception:
            return False

    def validate_bulk(self, emails: List[str]) -> List[Dict]:
        """
        Validate multiple emails

        Returns:
            List of dicts with email, is_valid, message
        """
        results = []
        for email in emails:
            is_valid, message = self.validate(email)
            results.append({
                "email": email,
                "is_valid": is_valid,
                "message": message
            })
        return results


class EmailEnricher:
    """
    Combine email finding and validation
    """

    def __init__(self):
        self.finder = EmailFinder()
        self.validator = EmailValidator()

    def enrich_lead(self, lead: Dict) -> Dict:
        """
        Find and validate email for a lead

        Args:
            lead: Dictionary with company info (website required)

        Returns:
            Lead dictionary with email fields added
        """
        enriched = lead.copy()

        website = lead.get("website")
        if not website:
            return enriched

        # Find emails from website
        found_emails = self.finder.find_email_from_website(website)

        if found_emails:
            # Validate first email
            is_valid, _ = self.validator.validate(found_emails[0])
            enriched["email"] = found_emails[0]
            enriched["email_verified"] = is_valid
            enriched["all_emails"] = found_emails

        else:
            # Generate pattern-based emails
            domain = self.finder.get_domain_from_website(website)
            if domain:
                generated = self.finder.generate_email_patterns(domain)
                # Validate generated emails
                for email in generated[:5]:  # Check first 5
                    is_valid, _ = self.validator.validate(email)
                    if is_valid:
                        enriched["email"] = email
                        enriched["email_verified"] = False  # Pattern-based, not confirmed
                        enriched["email_type"] = "generated"
                        break

        return enriched

    def enrich_leads_bulk(self, leads: List[Dict],
                          progress_callback=None) -> List[Dict]:
        """
        Enrich multiple leads with email data

        Args:
            leads: List of lead dictionaries
            progress_callback: Optional callback function(current, total)
        """
        enriched_leads = []
        total = len(leads)

        for i, lead in enumerate(leads):
            enriched = self.enrich_lead(lead)
            enriched_leads.append(enriched)

            if progress_callback:
                progress_callback(i + 1, total)

        return enriched_leads
