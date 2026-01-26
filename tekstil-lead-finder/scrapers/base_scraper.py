"""
Base Scraper Class with common functionality
"""
import time
import random
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from config.settings import SCRAPING_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all scrapers"""

    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.config = SCRAPING_CONFIG

    def get_headers(self) -> Dict[str, str]:
        """Generate random headers to avoid detection"""
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def random_delay(self):
        """Add random delay between requests"""
        min_delay, max_delay = self.config["delay_between_requests"]
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def fetch_page(self, url: str, retries: int = None) -> Optional[BeautifulSoup]:
        """Fetch a page with retry logic"""
        if retries is None:
            retries = self.config["max_retries"]

        for attempt in range(retries):
            try:
                self.random_delay()
                response = self.session.get(
                    url,
                    headers=self.get_headers(),
                    timeout=self.config["timeout"]
                )
                response.raise_for_status()
                return BeautifulSoup(response.text, "html.parser")

            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch {url} after {retries} attempts")
                    return None

    def extract_email_from_text(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        import re
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        # Filter out common false positives
        filtered = [e for e in emails if not any(x in e.lower() for x in
                   ['example.com', 'test.com', 'domain.com', '.png', '.jpg', '.gif'])]
        return list(set(filtered))

    def extract_phone_from_text(self, text: str) -> List[str]:
        """Extract phone numbers from text"""
        import re
        # Various phone patterns
        patterns = [
            r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}',
            r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
        ]
        phones = []
        for pattern in patterns:
            phones.extend(re.findall(pattern, text))
        return list(set(phones))

    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        return " ".join(text.split()).strip()

    @abstractmethod
    def search(self, query: str, location: str = None) -> List[Dict]:
        """Search for leads - must be implemented by subclasses"""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Return the source name"""
        pass
