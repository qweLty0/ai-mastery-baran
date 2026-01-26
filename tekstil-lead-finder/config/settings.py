"""
Tekstil Lead Finder - Configuration Settings
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"
LOGS_DIR = BASE_DIR / "logs"

# Create directories
for dir_path in [DATA_DIR, EXPORTS_DIR, LOGS_DIR]:
    dir_path.mkdir(exist_ok=True)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/leads.db")

# Scraping Settings
SCRAPING_CONFIG = {
    "delay_between_requests": (2, 5),  # Random delay range in seconds
    "max_retries": 3,
    "timeout": 30,
    "max_results_per_search": 100,
}

# Target Keywords for Textile Industry
SEARCH_KEYWORDS = {
    "en": [
        "textile importer",
        "clothing wholesaler",
        "garment buyer",
        "fashion brand manufacturer",
        "apparel sourcing",
        "textile procurement",
        "fabric importer",
        "private label clothing",
        "OEM garment manufacturer",
        "textile trading company",
    ],
    "de": [
        "textil importeur",
        "bekleidung großhandel",
        "mode einkäufer",
        "textil beschaffung",
    ],
    "fr": [
        "importateur textile",
        "grossiste vêtements",
        "acheteur mode",
    ],
    "ar": [
        "مستورد ملابس",
        "تجارة المنسوجات",
    ]
}

# Target Countries and Cities
TARGET_MARKETS = {
    "europe": {
        "Germany": ["Berlin", "Hamburg", "Munich", "Frankfurt", "Düsseldorf"],
        "UK": ["London", "Manchester", "Birmingham", "Leeds"],
        "France": ["Paris", "Lyon", "Marseille"],
        "Italy": ["Milan", "Rome", "Florence"],
        "Spain": ["Madrid", "Barcelona", "Valencia"],
        "Netherlands": ["Amsterdam", "Rotterdam"],
        "Poland": ["Warsaw", "Krakow"],
    },
    "middle_east": {
        "UAE": ["Dubai", "Abu Dhabi"],
        "Saudi Arabia": ["Riyadh", "Jeddah"],
        "Qatar": ["Doha"],
        "Kuwait": ["Kuwait City"],
    },
    "usa": {
        "USA": ["New York", "Los Angeles", "Chicago", "Miami", "Dallas"],
    },
    "turkey": {
        "Turkey": ["Istanbul", "Ankara", "Izmir", "Bursa", "Gaziantep"],
    }
}

# Email Settings
EMAIL_CONFIG = {
    "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", 587)),
    "smtp_user": os.getenv("SMTP_USER", ""),
    "smtp_password": os.getenv("SMTP_PASSWORD", ""),
    "from_name": os.getenv("FROM_NAME", "Your Company"),
    "from_email": os.getenv("FROM_EMAIL", ""),
    "daily_send_limit": 50,  # Stay under spam limits
    "delay_between_emails": (30, 60),  # Seconds
}

# Company Information (customize this)
COMPANY_INFO = {
    "name": os.getenv("COMPANY_NAME", "Your Textile Company"),
    "monthly_capacity": "200,000 pieces",
    "specialization": [
        "T-shirts",
        "Polo shirts",
        "Hoodies",
        "Sportswear",
        "Casual wear",
    ],
    "certifications": [
        "ISO 9001",
        "OEKO-TEX",
        "GOTS",
    ],
    "website": os.getenv("COMPANY_WEBSITE", "www.yourcompany.com"),
    "contact_email": os.getenv("CONTACT_EMAIL", "export@yourcompany.com"),
    "phone": os.getenv("CONTACT_PHONE", "+90 xxx xxx xx xx"),
}

# Lead Scoring Weights
LEAD_SCORING = {
    "has_email": 20,
    "has_phone": 10,
    "has_website": 15,
    "is_importer": 25,
    "company_size_large": 15,
    "relevant_industry": 15,
}
