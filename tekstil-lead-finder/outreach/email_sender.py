"""
Automated Email Sender with Rate Limiting and Tracking
"""
import smtplib
import ssl
import time
import random
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

from config.settings import EMAIL_CONFIG, COMPANY_INFO
from database.models import Lead, EmailLog, EmailCampaign, get_session
from .email_templates import EmailTemplateManager

logger = logging.getLogger(__name__)


class EmailSender:
    """
    Send emails with rate limiting and tracking
    """

    def __init__(self):
        self.config = EMAIL_CONFIG
        self.company_info = COMPANY_INFO
        self.template_manager = EmailTemplateManager(COMPANY_INFO)
        self.daily_sent = 0
        self.last_reset = datetime.now().date()

    def _check_daily_limit(self) -> bool:
        """Check and reset daily send limit"""
        today = datetime.now().date()
        if today > self.last_reset:
            self.daily_sent = 0
            self.last_reset = today

        return self.daily_sent < self.config["daily_send_limit"]

    def _get_smtp_connection(self):
        """Create SMTP connection"""
        context = ssl.create_default_context()

        server = smtplib.SMTP(
            self.config["smtp_server"],
            self.config["smtp_port"]
        )
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(
            self.config["smtp_user"],
            self.config["smtp_password"]
        )
        return server

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachments: List[str] = None,
        lead_id: int = None,
        campaign_id: int = None
    ) -> Dict:
        """
        Send a single email

        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body (plain text)
            attachments: List of file paths to attach
            lead_id: Associated lead ID for tracking
            campaign_id: Associated campaign ID

        Returns:
            Dict with status and details
        """
        result = {
            "success": False,
            "to_email": to_email,
            "error": None,
            "sent_at": None
        }

        # Check daily limit
        if not self._check_daily_limit():
            result["error"] = "Daily send limit reached"
            logger.warning(f"Daily limit reached ({self.config['daily_send_limit']})")
            return result

        # Validate inputs
        if not to_email or not subject:
            result["error"] = "Missing email or subject"
            return result

        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = f"{self.config['from_name']} <{self.config['from_email']}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            # Add body
            msg.attach(MIMEText(body, "plain"))

            # Add attachments
            if attachments:
                for filepath in attachments:
                    self._attach_file(msg, filepath)

            # Send
            server = self._get_smtp_connection()
            server.sendmail(
                self.config["from_email"],
                to_email,
                msg.as_string()
            )
            server.quit()

            # Update tracking
            self.daily_sent += 1
            result["success"] = True
            result["sent_at"] = datetime.now()

            # Log to database
            self._log_email(
                lead_id=lead_id,
                campaign_id=campaign_id,
                to_email=to_email,
                subject=subject,
                status="sent"
            )

            logger.info(f"Email sent to {to_email}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Failed to send email to {to_email}: {e}")

            # Log failure
            self._log_email(
                lead_id=lead_id,
                campaign_id=campaign_id,
                to_email=to_email,
                subject=subject,
                status="failed",
                error_message=str(e)
            )

        return result

    def _attach_file(self, msg: MIMEMultipart, filepath: str):
        """Attach a file to the email"""
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"Attachment not found: {filepath}")
            return

        with open(path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())

        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={path.name}"
        )
        msg.attach(part)

    def _log_email(
        self,
        to_email: str,
        subject: str,
        status: str,
        lead_id: int = None,
        campaign_id: int = None,
        error_message: str = None
    ):
        """Log email to database"""
        try:
            session = get_session()
            log = EmailLog(
                lead_id=lead_id,
                campaign_id=campaign_id,
                to_email=to_email,
                subject=subject,
                status=status,
                error_message=error_message,
                sent_at=datetime.now() if status == "sent" else None
            )
            session.add(log)
            session.commit()
            session.close()
        except Exception as e:
            logger.error(f"Failed to log email: {e}")

    def send_template_email(
        self,
        to_email: str,
        template_name: str,
        variables: dict,
        **kwargs
    ) -> Dict:
        """
        Send an email using a template

        Args:
            to_email: Recipient email
            template_name: Name of the template to use
            variables: Variables to replace in template
            **kwargs: Additional args passed to send_email
        """
        try:
            rendered = self.template_manager.render_template(
                template_name, variables
            )
            return self.send_email(
                to_email=to_email,
                subject=rendered["subject"],
                body=rendered["body"],
                **kwargs
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}


class CampaignManager:
    """
    Manage email campaigns with scheduling and tracking
    """

    def __init__(self):
        self.sender = EmailSender()
        self.config = EMAIL_CONFIG

    def create_campaign(
        self,
        name: str,
        template_name: str,
        lead_ids: List[int] = None
    ) -> EmailCampaign:
        """Create a new email campaign"""
        session = get_session()

        campaign = EmailCampaign(
            name=name,
            template_name=template_name,
            status="draft",
            total_recipients=len(lead_ids) if lead_ids else 0
        )
        session.add(campaign)
        session.commit()

        campaign_id = campaign.id
        session.close()

        return campaign_id

    def run_campaign(
        self,
        campaign_id: int,
        lead_ids: List[int],
        template_name: str,
        extra_variables: dict = None,
        progress_callback=None
    ) -> Dict:
        """
        Run an email campaign

        Args:
            campaign_id: Campaign ID
            lead_ids: List of lead IDs to email
            template_name: Template to use
            extra_variables: Additional template variables
            progress_callback: Optional callback(sent, total, result)

        Returns:
            Campaign results summary
        """
        session = get_session()

        # Update campaign status
        campaign = session.query(EmailCampaign).get(campaign_id)
        if campaign:
            campaign.status = "active"
            campaign.started_at = datetime.now()
            session.commit()

        results = {
            "total": len(lead_ids),
            "sent": 0,
            "failed": 0,
            "skipped": 0
        }

        for i, lead_id in enumerate(lead_ids):
            # Get lead
            lead = session.query(Lead).get(lead_id)
            if not lead or not lead.email:
                results["skipped"] += 1
                continue

            # Prepare variables
            variables = {
                "contact_name": lead.contact_name or "Sir/Madam",
                "their_company": lead.company_name,
                "company_name": lead.company_name,
                **(extra_variables or {})
            }

            # Send email
            result = self.sender.send_template_email(
                to_email=lead.email,
                template_name=template_name,
                variables=variables,
                lead_id=lead_id,
                campaign_id=campaign_id
            )

            if result["success"]:
                results["sent"] += 1
                lead.status = "contacted"
                lead.last_contacted = datetime.now()
            else:
                results["failed"] += 1

            session.commit()

            # Callback
            if progress_callback:
                progress_callback(i + 1, len(lead_ids), result)

            # Rate limiting delay
            if i < len(lead_ids) - 1:
                min_delay, max_delay = self.config["delay_between_emails"]
                time.sleep(random.uniform(min_delay, max_delay))

        # Update campaign status
        if campaign:
            campaign.status = "completed"
            campaign.completed_at = datetime.now()
            campaign.sent_count = results["sent"]
            session.commit()

        session.close()
        return results

    def get_campaign_stats(self, campaign_id: int) -> Dict:
        """Get campaign statistics"""
        session = get_session()

        campaign = session.query(EmailCampaign).get(campaign_id)
        if not campaign:
            return {}

        logs = session.query(EmailLog).filter_by(campaign_id=campaign_id).all()

        stats = {
            "campaign_name": campaign.name,
            "status": campaign.status,
            "total_recipients": campaign.total_recipients,
            "sent": len([l for l in logs if l.status == "sent"]),
            "failed": len([l for l in logs if l.status == "failed"]),
            "opened": len([l for l in logs if l.opened_at]),
            "replied": len([l for l in logs if l.replied_at]),
            "started_at": campaign.started_at,
            "completed_at": campaign.completed_at
        }

        session.close()
        return stats
