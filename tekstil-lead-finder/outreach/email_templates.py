"""
Email Templates for Textile B2B Outreach
Multiple languages and scenarios
"""

TEMPLATES = {
    "initial_contact_en": {
        "subject": "Textile Manufacturing Partnership - {company_name}",
        "body": """Dear {contact_name},

I hope this email finds you well.

I am reaching out from {our_company}, a textile manufacturer based in Turkey with a monthly production capacity of {monthly_capacity}.

We specialize in:
{specialization_list}

Our certifications include: {certifications}

We are currently seeking new partnerships with companies like {their_company} and would be interested in discussing how we might work together.

Would you be available for a brief call to explore potential collaboration?

Best regards,
{sender_name}
{sender_title}
{our_company}
{contact_info}
"""
    },

    "initial_contact_de": {
        "subject": "Textilproduktion Partnerschaft - {company_name}",
        "body": """Sehr geehrte(r) {contact_name},

ich hoffe, diese E-Mail erreicht Sie wohlauf.

Ich schreibe Ihnen im Namen von {our_company}, einem Textilhersteller mit Sitz in der Türkei und einer monatlichen Produktionskapazität von {monthly_capacity}.

Wir sind spezialisiert auf:
{specialization_list}

Unsere Zertifizierungen umfassen: {certifications}

Wir suchen derzeit nach neuen Partnerschaften mit Unternehmen wie {their_company} und würden gerne besprechen, wie wir zusammenarbeiten können.

Wären Sie für ein kurzes Gespräch verfügbar, um eine mögliche Zusammenarbeit zu erkunden?

Mit freundlichen Grüßen,
{sender_name}
{sender_title}
{our_company}
{contact_info}
"""
    },

    "initial_contact_tr": {
        "subject": "Tekstil Üretim İş Birliği Teklifi - {company_name}",
        "body": """Sayın {contact_name},

Bu e-postanın sizi iyi bulmasını dilerim.

Türkiye merkezli, aylık {monthly_capacity} üretim kapasitesine sahip bir tekstil üreticisi olan {our_company} adına sizinle iletişime geçiyorum.

Uzmanlık alanlarımız:
{specialization_list}

Sertifikalarımız: {certifications}

{their_company} gibi firmalarla yeni iş birlikleri kurmak istiyoruz ve nasıl birlikte çalışabileceğimizi görüşmek isteriz.

Potansiyel iş birliği için kısa bir görüşme yapmaya müsait misiniz?

Saygılarımla,
{sender_name}
{sender_title}
{our_company}
{contact_info}
"""
    },

    "initial_contact_ar": {
        "subject": "شراكة تصنيع المنسوجات - {company_name}",
        "body": """السيد/السيدة {contact_name} المحترم(ة)،

أتمنى أن تصلكم رسالتي وأنتم بخير.

أتواصل معكم من {our_company}، وهي شركة تصنيع منسوجات مقرها تركيا بطاقة إنتاجية شهرية تبلغ {monthly_capacity}.

نحن متخصصون في:
{specialization_list}

شهاداتنا تشمل: {certifications}

نبحث حالياً عن شراكات جديدة مع شركات مثل {their_company} ونرغب في مناقشة إمكانية التعاون.

هل أنتم متاحون لمكالمة قصيرة لاستكشاف التعاون المحتمل؟

مع أطيب التحيات،
{sender_name}
{sender_title}
{our_company}
{contact_info}
"""
    },

    "follow_up_1": {
        "subject": "Re: Textile Manufacturing Partnership - Following Up",
        "body": """Dear {contact_name},

I wanted to follow up on my previous email regarding a potential textile manufacturing partnership.

I understand you may be busy, but I believe our production capabilities could be a great fit for {their_company}'s sourcing needs.

A few quick highlights:
- Monthly capacity: {monthly_capacity}
- Quick turnaround times
- Competitive pricing
- Quality certifications: {certifications}

Would you have 15 minutes for a quick call this week?

Best regards,
{sender_name}
{our_company}
"""
    },

    "follow_up_2": {
        "subject": "Final Follow-up: Textile Manufacturing Inquiry",
        "body": """Dear {contact_name},

This is my final follow-up regarding our textile manufacturing capabilities.

If you're not the right person for this inquiry, could you please point me to the appropriate contact in your purchasing/sourcing department?

I'd be happy to send our product catalog and price list if that would be helpful.

Thank you for your time.

Best regards,
{sender_name}
{our_company}
{contact_info}
"""
    },

    "catalog_offer": {
        "subject": "Product Catalog & Price List - {our_company}",
        "body": """Dear {contact_name},

Thank you for your interest in {our_company}.

As requested, please find attached our product catalog and price list.

Key information:
- MOQ: {moq}
- Lead time: {lead_time}
- Payment terms: {payment_terms}
- Shipping: {shipping_info}

Please don't hesitate to reach out if you have any questions or would like to request samples.

Best regards,
{sender_name}
{our_company}
"""
    }
}


class EmailTemplateManager:
    """Manage and render email templates"""

    def __init__(self, company_info: dict = None):
        self.templates = TEMPLATES
        self.company_info = company_info or {}

    def get_template(self, template_name: str) -> dict:
        """Get a template by name"""
        return self.templates.get(template_name, {})

    def render_template(self, template_name: str, variables: dict) -> dict:
        """
        Render a template with variables

        Args:
            template_name: Name of the template
            variables: Dict of variables to replace

        Returns:
            Dict with rendered subject and body
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        # Merge company info with provided variables
        all_vars = {**self.company_info, **variables}

        # Handle specialization list formatting
        if "specialization" in all_vars and isinstance(all_vars["specialization"], list):
            all_vars["specialization_list"] = "\n".join(
                f"• {item}" for item in all_vars["specialization"]
            )

        if "certifications" in all_vars and isinstance(all_vars["certifications"], list):
            all_vars["certifications"] = ", ".join(all_vars["certifications"])

        # Render template
        try:
            subject = template["subject"].format(**all_vars)
            body = template["body"].format(**all_vars)
        except KeyError as e:
            raise ValueError(f"Missing variable in template: {e}")

        return {
            "subject": subject,
            "body": body
        }

    def list_templates(self) -> list:
        """List all available templates"""
        return list(self.templates.keys())

    def add_template(self, name: str, subject: str, body: str):
        """Add a new template"""
        self.templates[name] = {
            "subject": subject,
            "body": body
        }

    def get_template_for_language(self, base_name: str, language: str) -> str:
        """Get template name for specific language"""
        lang_template = f"{base_name}_{language}"
        if lang_template in self.templates:
            return lang_template
        return f"{base_name}_en"  # Fallback to English
