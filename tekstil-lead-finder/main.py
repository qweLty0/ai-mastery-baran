#!/usr/bin/env python3
"""
Tekstil Lead Finder - Main CLI Application
Automated customer acquisition system for textile manufacturers
"""
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from typing import Optional, List
import pandas as pd

from config.settings import (
    SEARCH_KEYWORDS, TARGET_MARKETS, COMPANY_INFO,
    DATA_DIR, EXPORTS_DIR
)
from database.models import init_db, get_session, Lead
from scrapers import GoogleScraper, EuropagesScraper, KompassScraper
from email_tools import EmailFinder, EmailValidator, EmailEnricher
from outreach import EmailSender, CampaignManager, EmailTemplateManager

# Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = typer.Typer(help="Tekstil Lead Finder - Otomatik Müşteri Bulma Sistemi")
console = Console()


@app.command()
def init():
    """Initialize the database and directories"""
    console.print("[bold blue]Initializing Tekstil Lead Finder...[/bold blue]")

    # Create directories
    for dir_path in [DATA_DIR, EXPORTS_DIR]:
        dir_path.mkdir(exist_ok=True)
        console.print(f"  ✓ Created {dir_path}")

    # Initialize database
    init_db()
    console.print("  ✓ Database initialized")

    console.print("\n[bold green]✓ Initialization complete![/bold green]")
    console.print("\nNext steps:")
    console.print("  1. Edit config/settings.py with your company info")
    console.print("  2. Create .env file with SMTP settings")
    console.print("  3. Run: python main.py search --help")


@app.command()
def search(
    query: str = typer.Option(None, "--query", "-q", help="Search query"),
    country: str = typer.Option(None, "--country", "-c", help="Target country"),
    city: str = typer.Option(None, "--city", help="Target city"),
    source: str = typer.Option("all", "--source", "-s",
                               help="Source: google, europages, kompass, all"),
    max_results: int = typer.Option(50, "--max", "-m", help="Max results"),
    enrich: bool = typer.Option(False, "--enrich", "-e", help="Find emails")
):
    """Search for potential customers/leads"""

    if not query:
        # Use default textile keywords
        query = "textile importer"

    location = ""
    if city:
        location = f"{city} {country}" if country else city
    elif country:
        location = country

    console.print(Panel(
        f"[bold]Searching for:[/bold] {query}\n"
        f"[bold]Location:[/bold] {location or 'Global'}\n"
        f"[bold]Source:[/bold] {source}",
        title="🔍 Lead Search"
    ))

    leads = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        if source in ["google", "all"]:
            task = progress.add_task("Searching Google/DuckDuckGo...", total=None)
            scraper = GoogleScraper()
            google_leads = scraper.search(query, location, max_results)
            leads.extend(google_leads)
            progress.update(task, completed=True,
                          description=f"✓ Google: {len(google_leads)} leads")

        if source in ["europages", "all"]:
            task = progress.add_task("Searching Europages...", total=None)
            scraper = EuropagesScraper()
            euro_leads = scraper.search(query, location)
            leads.extend(euro_leads)
            progress.update(task, completed=True,
                          description=f"✓ Europages: {len(euro_leads)} leads")

        if source in ["kompass", "all"]:
            task = progress.add_task("Searching Kompass...", total=None)
            scraper = KompassScraper()
            kompass_leads = scraper.search(query, location)
            leads.extend(kompass_leads)
            progress.update(task, completed=True,
                          description=f"✓ Kompass: {len(kompass_leads)} leads")

        # Enrich with emails if requested
        if enrich and leads:
            task = progress.add_task("Finding emails...", total=len(leads))
            enricher = EmailEnricher()

            for i, lead in enumerate(leads):
                leads[i] = enricher.enrich_lead(lead)
                progress.update(task, advance=1)

    # Save to database
    session = get_session()
    saved_count = 0

    for lead_data in leads:
        # Check for duplicates
        existing = session.query(Lead).filter_by(
            company_name=lead_data.get("company_name"),
            website=lead_data.get("website")
        ).first()

        if not existing:
            lead = Lead(
                company_name=lead_data.get("company_name"),
                website=lead_data.get("website"),
                email=lead_data.get("email"),
                email_verified=lead_data.get("email_verified", False),
                phone=lead_data.get("phone"),
                country=country,
                city=city,
                source=lead_data.get("source"),
                search_query=query,
                source_url=lead_data.get("source_url")
            )
            session.add(lead)
            saved_count += 1

    session.commit()
    session.close()

    # Display results
    console.print(f"\n[bold green]✓ Found {len(leads)} leads, saved {saved_count} new[/bold green]")

    if leads[:10]:
        table = Table(title="Top Results")
        table.add_column("Company", style="cyan")
        table.add_column("Website")
        table.add_column("Email", style="green")
        table.add_column("Source")

        for lead in leads[:10]:
            table.add_row(
                lead.get("company_name", "")[:40],
                lead.get("website", "")[:30],
                lead.get("email", "-"),
                lead.get("source", "")
            )

        console.print(table)


@app.command()
def bulk_search(
    market: str = typer.Option("europe", help="Market: europe, middle_east, usa, turkey"),
    keywords_lang: str = typer.Option("en", help="Keywords language: en, de, fr, ar"),
    enrich: bool = typer.Option(True, help="Find emails automatically")
):
    """Run bulk search across multiple countries and keywords"""

    if market not in TARGET_MARKETS:
        console.print(f"[red]Invalid market. Choose from: {list(TARGET_MARKETS.keys())}[/red]")
        return

    if keywords_lang not in SEARCH_KEYWORDS:
        console.print(f"[red]Invalid language. Choose from: {list(SEARCH_KEYWORDS.keys())}[/red]")
        return

    countries = TARGET_MARKETS[market]
    keywords = SEARCH_KEYWORDS[keywords_lang]

    total_leads = 0

    console.print(Panel(
        f"[bold]Market:[/bold] {market}\n"
        f"[bold]Countries:[/bold] {len(countries)}\n"
        f"[bold]Keywords:[/bold] {len(keywords)}",
        title="🌍 Bulk Search"
    ))

    for country, cities in countries.items():
        for keyword in keywords[:3]:  # Limit keywords per country
            console.print(f"\n[yellow]→ Searching: {keyword} in {country}[/yellow]")

            # Run search for each country
            search(
                query=keyword,
                country=country,
                source="all",
                max_results=20,
                enrich=enrich
            )

    console.print(f"\n[bold green]✓ Bulk search complete![/bold green]")


@app.command()
def list_leads(
    status: str = typer.Option(None, "--status", "-s", help="Filter by status"),
    country: str = typer.Option(None, "--country", "-c", help="Filter by country"),
    has_email: bool = typer.Option(False, "--with-email", help="Only leads with email"),
    limit: int = typer.Option(50, "--limit", "-l", help="Number of leads to show")
):
    """List leads from database"""

    session = get_session()
    query = session.query(Lead)

    if status:
        query = query.filter(Lead.status == status)
    if country:
        query = query.filter(Lead.country == country)
    if has_email:
        query = query.filter(Lead.email.isnot(None))

    leads = query.order_by(Lead.created_at.desc()).limit(limit).all()

    if not leads:
        console.print("[yellow]No leads found[/yellow]")
        return

    table = Table(title=f"Leads ({len(leads)} shown)")
    table.add_column("ID", style="dim")
    table.add_column("Company", style="cyan")
    table.add_column("Country")
    table.add_column("Email", style="green")
    table.add_column("Status")
    table.add_column("Source")

    for lead in leads:
        table.add_row(
            str(lead.id),
            (lead.company_name or "")[:35],
            lead.country or "-",
            lead.email or "-",
            lead.status or "new",
            lead.source or "-"
        )

    console.print(table)
    session.close()


@app.command()
def export(
    format: str = typer.Option("excel", "--format", "-f", help="Format: excel, csv"),
    status: str = typer.Option(None, "--status", help="Filter by status"),
    has_email: bool = typer.Option(False, "--with-email", help="Only with email")
):
    """Export leads to Excel or CSV"""

    session = get_session()
    query = session.query(Lead)

    if status:
        query = query.filter(Lead.status == status)
    if has_email:
        query = query.filter(Lead.email.isnot(None))

    leads = query.all()

    if not leads:
        console.print("[yellow]No leads to export[/yellow]")
        return

    # Convert to DataFrame
    data = [lead.to_dict() for lead in leads]
    df = pd.DataFrame(data)

    # Export
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")

    if format == "excel":
        filepath = EXPORTS_DIR / f"leads_{timestamp}.xlsx"
        df.to_excel(filepath, index=False)
    else:
        filepath = EXPORTS_DIR / f"leads_{timestamp}.csv"
        df.to_csv(filepath, index=False)

    console.print(f"[green]✓ Exported {len(leads)} leads to {filepath}[/green]")
    session.close()


@app.command()
def enrich_emails(
    limit: int = typer.Option(100, "--limit", "-l", help="Max leads to enrich")
):
    """Find emails for leads that don't have one"""

    session = get_session()

    # Get leads without email but with website
    leads = session.query(Lead).filter(
        Lead.email.is_(None),
        Lead.website.isnot(None)
    ).limit(limit).all()

    if not leads:
        console.print("[yellow]No leads need email enrichment[/yellow]")
        return

    console.print(f"[bold]Enriching {len(leads)} leads...[/bold]")

    enricher = EmailEnricher()
    enriched_count = 0

    with Progress(console=console) as progress:
        task = progress.add_task("Finding emails...", total=len(leads))

        for lead in leads:
            result = enricher.enrich_lead({"website": lead.website})

            if result.get("email"):
                lead.email = result["email"]
                lead.email_verified = result.get("email_verified", False)
                enriched_count += 1

            progress.update(task, advance=1)

    session.commit()
    session.close()

    console.print(f"[green]✓ Found emails for {enriched_count}/{len(leads)} leads[/green]")


@app.command()
def send_campaign(
    template: str = typer.Option("initial_contact_en", help="Template name"),
    status: str = typer.Option("new", help="Lead status to target"),
    limit: int = typer.Option(10, help="Max emails to send"),
    dry_run: bool = typer.Option(True, help="Preview without sending")
):
    """Send email campaign to leads"""

    session = get_session()

    # Get leads with email
    leads = session.query(Lead).filter(
        Lead.email.isnot(None),
        Lead.status == status
    ).limit(limit).all()

    if not leads:
        console.print("[yellow]No leads found for campaign[/yellow]")
        return

    console.print(Panel(
        f"[bold]Template:[/bold] {template}\n"
        f"[bold]Recipients:[/bold] {len(leads)}\n"
        f"[bold]Dry Run:[/bold] {dry_run}",
        title="📧 Email Campaign"
    ))

    if dry_run:
        # Preview mode
        template_mgr = EmailTemplateManager(COMPANY_INFO)

        table = Table(title="Preview - Emails to be sent")
        table.add_column("To")
        table.add_column("Company")
        table.add_column("Subject")

        for lead in leads[:5]:
            try:
                rendered = template_mgr.render_template(template, {
                    "contact_name": lead.contact_name or "Sir/Madam",
                    "their_company": lead.company_name,
                    "company_name": lead.company_name
                })
                table.add_row(
                    lead.email,
                    lead.company_name[:30],
                    rendered["subject"][:50]
                )
            except Exception as e:
                console.print(f"[red]Error with template: {e}[/red]")

        console.print(table)
        console.print("\n[yellow]This is a dry run. Add --no-dry-run to send emails.[/yellow]")

    else:
        # Actually send
        if not EMAIL_CONFIG.get("smtp_user"):
            console.print("[red]SMTP not configured! Set up .env file first.[/red]")
            return

        campaign_mgr = CampaignManager()
        lead_ids = [lead.id for lead in leads]

        # Create campaign
        campaign_id = campaign_mgr.create_campaign(
            name=f"Campaign {pd.Timestamp.now().strftime('%Y-%m-%d')}",
            template_name=template,
            lead_ids=lead_ids
        )

        # Run campaign
        def progress_cb(sent, total, result):
            status = "✓" if result["success"] else "✗"
            console.print(f"  {status} {sent}/{total}: {result['to_email']}")

        results = campaign_mgr.run_campaign(
            campaign_id=campaign_id,
            lead_ids=lead_ids,
            template_name=template,
            progress_callback=progress_cb
        )

        console.print(f"\n[green]✓ Campaign complete: {results['sent']} sent, {results['failed']} failed[/green]")

    session.close()


@app.command()
def stats():
    """Show lead statistics"""

    session = get_session()

    total = session.query(Lead).count()
    with_email = session.query(Lead).filter(Lead.email.isnot(None)).count()
    by_status = {}

    for status in ["new", "contacted", "responded", "interested", "converted"]:
        count = session.query(Lead).filter(Lead.status == status).count()
        if count > 0:
            by_status[status] = count

    # By country
    from sqlalchemy import func
    by_country = session.query(
        Lead.country, func.count(Lead.id)
    ).group_by(Lead.country).order_by(func.count(Lead.id).desc()).limit(10).all()

    session.close()

    console.print(Panel(
        f"[bold]Total Leads:[/bold] {total}\n"
        f"[bold]With Email:[/bold] {with_email} ({100*with_email/total:.1f}%)" if total else "",
        title="📊 Lead Statistics"
    ))

    if by_status:
        table = Table(title="By Status")
        table.add_column("Status")
        table.add_column("Count", justify="right")

        for status, count in by_status.items():
            table.add_row(status, str(count))
        console.print(table)

    if by_country:
        table = Table(title="Top Countries")
        table.add_column("Country")
        table.add_column("Leads", justify="right")

        for country, count in by_country:
            if country:
                table.add_row(country, str(count))
        console.print(table)


@app.command()
def dashboard():
    """Launch web dashboard (Streamlit)"""
    import subprocess
    dashboard_path = Path(__file__).parent / "dashboard" / "app.py"
    console.print("[bold]Launching dashboard...[/bold]")
    subprocess.run(["streamlit", "run", str(dashboard_path)])


if __name__ == "__main__":
    app()
