"""
Database Models for Lead Management
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import enum

from config.settings import DATABASE_URL

Base = declarative_base()


class LeadStatus(enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    CONVERTED = "converted"


class LeadSource(enum.Enum):
    GOOGLE = "google"
    EUROPAGES = "europages"
    KOMPASS = "kompass"
    LINKEDIN = "linkedin"
    MANUAL = "manual"
    REFERRAL = "referral"


class Lead(Base):
    """Main Lead/Prospect table"""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Company Information
    company_name = Column(String(255), nullable=False)
    website = Column(String(255))
    industry = Column(String(100))
    company_size = Column(String(50))

    # Contact Information
    contact_name = Column(String(255))
    contact_title = Column(String(100))
    email = Column(String(255))
    email_verified = Column(Boolean, default=False)
    phone = Column(String(50))

    # Location
    country = Column(String(100))
    city = Column(String(100))
    address = Column(Text)

    # Lead Details
    source = Column(String(50))
    status = Column(String(50), default="new")
    score = Column(Integer, default=0)
    tags = Column(String(500))  # Comma-separated tags
    notes = Column(Text)

    # Search Context
    search_query = Column(String(255))
    source_url = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_contacted = Column(DateTime)

    def __repr__(self):
        return f"<Lead(id={self.id}, company='{self.company_name}', email='{self.email}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "company_name": self.company_name,
            "website": self.website,
            "contact_name": self.contact_name,
            "email": self.email,
            "phone": self.phone,
            "country": self.country,
            "city": self.city,
            "source": self.source,
            "status": self.status,
            "score": self.score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EmailCampaign(Base):
    """Email campaign tracking"""
    __tablename__ = "email_campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    subject = Column(String(255))
    template_name = Column(String(100))
    status = Column(String(50), default="draft")  # draft, active, paused, completed

    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    open_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)


class EmailLog(Base):
    """Individual email send log"""
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer)
    campaign_id = Column(Integer)

    to_email = Column(String(255))
    subject = Column(String(255))
    status = Column(String(50))  # sent, failed, bounced
    error_message = Column(Text)

    sent_at = Column(DateTime)
    opened_at = Column(DateTime)
    replied_at = Column(DateTime)


class SearchHistory(Base):
    """Track search history for avoiding duplicates"""
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String(255))
    source = Column(String(50))
    results_count = Column(Integer)
    searched_at = Column(DateTime, default=datetime.utcnow)


# Database initialization
engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(engine)
    print("Database initialized successfully!")


def get_session():
    """Get database session"""
    Session = sessionmaker(bind=engine)
    return Session()


if __name__ == "__main__":
    init_db()
