"""
KiwiSaver Fund Data Scraper

Pulls fund data from:
- Companies Office scheme registry
- Provider disclosure statements
- Sorted.org.nz

Usage:
    python scrape.py                 # scrape all sources
    python scrape.py --provider "simplicity"  # scrape specific provider
"""

import csv
import json
import os
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent / "data"
BASE_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = BASE_DIR / "funds.csv"

PROVIDERS = {
    "simplicity": "https://www.simplicity.kiwi/kiwisaver/",
    "booster": "https://www.booster.co.nz/kiwisaver/",
    "fisher": "https://www.fisherfunds.co.nz/kiwisaver/",
    "milford": "https://www.milford.co.nz/kiwisaver/",
    "anz": "https://www.anz.co.nz/investments/kiwisaver/",
    "asb": "https://www.asb.co.nz/kiwisaver/",
    "westpac": "https://www.westpac.co.nz/kiwisaver/",
    "bnz": "https://www.bnz.co.nz/personal/investing/kiwisaver",
    "generate": "https://www.generatewealth.co.nz/kiwisaver/",
    "kernel": "https://www.kernel.co.nz/kiwisaver/",
    "kiw wealth": "https://www.kiwiwealth.co.nz/kiwisaver/",
    "mercer": "https://www.mercer.co.nz/kiwisaver/",
}

def scrape_sorted():
    """Pull comparison data from sorted.org.nz"""
    # Sorted provides fund finder data - placeholder for actual scraping
    print("[sorted] Pulling fund comparison data...")
    # In production: scrape the fund finder results
    return {}

def scrape_companies_office():
    """Pull registered scheme list from Companies Office"""
    print("[companies office] Pulling scheme registry...")
    url = "https://www.companiesoffice.govt.nz/companies/osd/app/kiwisaver/schemes"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"[companies office] Error: {e}")
    return {}

def scrape_provider(provider_name, url):
    """Scrape individual provider's fund data"""
    print(f"[{provider_name}] Scraping {url}...")
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            # Parse provider's fund data from their website
            return {"provider": provider_name, "status": "ok", "url": url}
    except Exception as e:
        print(f"[{provider_name}] Error: {e}")
    return {"provider": provider_name, "status": "error"}

def write_csv(funds_data):
    """Write collected data to CSV"""
    fieldnames = [
        "scheme", "fund_name", "type_equity_pct", "type_bonds_pct",
        "geo_nz_pct", "geo_aus_pct", "geo_global_pct", "currency_hedged",
        "fee_pct", "active_passive", "benchmark", "returns_1yr_pct",
        "returns_3yr_pct", "returns_5yr_pct", "returns_10yr_pct",
        "benchmark_5yr_pct", "sharpe_5yr", "std_dev_5yr", "max_drawdown_pct",
        "fund_age_years", "manager_tenure_years", "last_updated", "notes"
    ]
    
    existing = []
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing = list(reader)
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in existing:
            writer.writerow(row)
        for fund in funds_data:
            writer.writerow(fund)
    
    print(f"[output] Wrote {len(funds_data)} funds to {OUTPUT_FILE}")

def main():
    print(f"KiwiSaver scraper starting at {datetime.now().isoformat()}")
    
    # Scrape all sources
    sorted_data = scrape_sorted()
    companies_data = scrape_companies_office()
    
    # Scrape each provider
    for provider_name, url in PROVIDERS.items():
        result = scrape_provider(provider_name, url)
        time.sleep(1)  # Rate limit
    
    print("[complete] Data collection finished")

if __name__ == "__main__":
    main()
