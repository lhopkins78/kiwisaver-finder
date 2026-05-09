"""
Sorted Smart Investor scraper.

Pulls KiwiSaver fund data from the Sorted API and parses into structured records.

API endpoint: https://smartinvestor.sorted.org.nz/kiwisaver-and-managed-funds/get_results/
Returns HTML card fragments — we parse those for fund data.
"""

import json
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent / "data"
OUTPUT_FILE = BASE_DIR / "sorted_funds.json"

def scrape_sorted_page(page=1, per_page=50):
    """Fetch one page of Sorted fund results."""
    url = "https://smartinvestor.sorted.org.nz/kiwisaver-and-managed-funds/get_results/"
    params = {
        "managedFundTypes": "kiwisaver-funds",
        "searchType": "quick",
        "sort": "growth-assets-asc",
        "page": page,
        "results_per_page": per_page
    }
    
    print(f"[sorted] Fetching page {page}...")
    response = requests.get(url, params=params, timeout=30)
    
    if response.status_code != 200:
        print(f"[sorted] Error: HTTP {response.status_code}")
        return None
    
    return response.text  # HTML fragment

def parse_fund_card(html):
    """Parse a single fund card HTML into a dict."""
    soup = BeautifulSoup(html, 'html.parser')
    
    fund = {}
    
    # Scheme name (appears above fund name in grey small text)
    scheme_el = soup.find('p', class_=lambda x: x and 'colour--grey-mid' in x.split())
    if scheme_el:
        fund['scheme'] = scheme_el.get_text(strip=True)
    
    # Fund name
    title_el = soup.find('h3', class_=lambda x: x and 'card__title' in x.split())
    if title_el:
        fund['fund_name'] = title_el.get_text(strip=True)
    
    # Fund type (tag)
    tags = soup.find_all('div', class_='tag')
    fund_type = None
    for tag in tags:
        text = tag.get_text(strip=True)
        if text.lower() in ['defensive', 'conservative', 'balanced', 'growth', 'aggressive']:
            fund_type = text
            break
    fund['fund_type_raw'] = fund_type
    
    # Extract fees from doughnut chart data
    # Data is in canvas element: data-dataset="[{&quot;labels&quot;:[&quot;Value&quot;,&quot;Base&quot;],&quot;data&quot;:[0.68,1.2192]}]"
    fees_canvas = soup.find('canvas', class_=lambda x: x and 'js-inline-doughnut' in x.split() if x else False)
    if fees_canvas:
        dataset_str = fees_canvas.get('data-dataset', '')
        # Extract the fee percentage from the dataset
        match = re.search(r'data-colour="purple"[^>]*data-dataset="\[\{&quot;labels&quot;:\[&quot;Value&quot;,&quot;Base&quot;\],&quot;data&quot;:\[([0-9.]+)', dataset_str)
        if not match:
            # Try alternate pattern
            match = re.search(r'data-colour="purple".*?data-dataset="\[\{\"labels\":\[\"Value\",\"Base\"\],\"data\":\[([0-9.]+)', dataset_str)
        if match:
            fee_rate = float(match.group(1))
            # The fee rate seems to be stored differently - look for actual fee %
            # Actually the purple doughnut shows the fee. Let's look for the text "0.55%"
            fee_text = soup.find('span', class_=lambda x: x and 'colour--purple-dark' in x.split() if x else False)
            if fee_text:
                fee_match = re.search(r'([0-9.]+)%', fee_text.get_text())
                if fee_match:
                    fund['fee_pct'] = float(fee_match.group(1))
    
    # Extract returns from the returns doughnut
    returns_canvas = soup.find('canvas', class_=lambda x: x and 'js-inline-doughnut' in x.split())
    if returns_canvas:
        dataset_str = returns_canvas.get('data-dataset', '')
        # Look for return value in the green doughnut
        return_match = re.search(r'data-colour="green"[^>]*data-dataset="\[\{\"labels\":\[\"Value\",\"Base\"\],\"data\":\[([0-9.]+)', dataset_str)
        if return_match:
            fund['return_5yr_raw'] = float(return_match.group(1))
    
    # Growth assets % from horizontal bar chart
    growth_chart = soup.find('canvas', {'data-label': 'Asset Mix'})
    if growth_chart:
        dataset = growth_chart.get('data-dataset', '')
        # Extract growth assets percentage
        growth_match = re.search(r'"Growth assets","data":\["?([0-9.]+)', dataset)
        if growth_match:
            fund['growth_assets_pct'] = float(growth_match.group(1))
    
    # Get 5yr returns from the line chart
    line_chart = soup.find('canvas', class_=lambda x: x and 'js-inline-line-chart' in x.split() if x else False)
    if line_chart:
        dataset = line_chart.get('data-dataset', '')
        # Extract years and returns
        year_matches = re.findall(r'"year":(\d+)', dataset)
        fund_matches = re.findall(r'"fund":"?(-?[0-9.]+)"?', dataset)
        avg_matches = re.findall(r'"average":"?(-?[0-9.]+)"?', dataset)
        
        if year_matches and fund_matches:
            fund['returns_5yr_pct'] = float(fund_matches[-1])  # Most recent year
            fund['returns_5yr_series'] = {
                yr: {'fund': float(f), 'average': float(a)} 
                for yr, f, a in zip(year_matches, fund_matches, avg_matches) if f and a
            }
    
    # Get fee breakdown table
    fee_table = soup.find('table')
    if fee_table:
        rows = fee_table.find_all('tr')
        for row in rows:
            if 'This fund' in row.get_text():
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 4:
                    # Total %, Management %, Other %
                    fund['fee_pct'] = float(cells[1].get_text().replace('%', ''))
                    fund['fee_management_pct'] = float(cells[3].get_text().replace('%', ''))
                    fund['fee_other_pct'] = float(cells[4].get_text().replace('%', ''))
                    break
    
    # Asset mix detail - extract from canvas data
    mix_canvases = soup.find_all('canvas', class_=lambda x: x and 'js-inline-horizontal-bar-chart' in x.split() if x else False)
    for canvas in mix_canvases:
        label = canvas.get('data-label', '')
        dataset = canvas.get('data-dataset', '')
        
        # Parse the dataset JSON (HTML-encoded)
        dataset = dataset.replace('&quot;', '"').replace('&amp;', '&')
        
        if 'Shares' in label:
            match = re.search(r'"data":\["?([0-9.]+)', dataset)
            if match:
                fund['asset_shares_pct'] = float(match.group(1))
        elif 'Property' in label:
            match = re.search(r'"data":\["?([0-9.]+)', dataset)
            if match:
                fund['asset_property_pct'] = float(match.group(1))
        elif 'Bonds' in label:
            match = re.search(r'"data":\["?([0-9.]+)', dataset)
            if match:
                fund['asset_bonds_pct'] = float(match.group(1))
        elif 'Cash' in label:
            match = re.search(r'"data":\["?([0-9.]+)', dataset)
            if match:
                fund['asset_cash_pct'] = float(match.group(1))
    
    return fund

def scrape_all_pages():
    """Scrape all pages of KiwiSaver funds from Sorted."""
    all_funds = []
    page = 1
    per_page = 50
    total = None
    
    while True:
        html = scrape_sorted_page(page, per_page)
        if not html:
            break
        
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('div', class_='card')
        
        if not cards:
            print(f"[sorted] No cards found on page {page}")
            break
        
        print(f"[sorted] Found {len(cards)} cards on page {page}")
        
        for card_html in cards:
            fund = parse_fund_card(str(card_html))
            if fund.get('fund_name'):
                all_funds.append(fund)
        
        # Check if there are more pages
        # The API doesn't seem to return structured JSON, so we rely on total count
        if total is None:
            # Try to find total in the page
            total_text = soup.find(['span', 'p'], class_=lambda x: x and 'total' in x.lower() if x else False)
            # Otherwise just iterate until we run out
            if len(cards) < per_page:
                break
        
        page += 1
        time.sleep(1)  # Rate limit
    
    return all_funds

def main():
    print(f"[sorted] Starting scrape at {datetime.now().isoformat()}")
    
    funds = scrape_all_pages()
    
    print(f"\n[sorted] Total funds scraped: {len(funds)}")
    
    # Save to JSON
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            "scraped_at": datetime.now().isoformat(),
            "source": "https://smartinvestor.sorted.org.nz",
            "total_funds": len(funds),
            "funds": funds
        }, f, indent=2, ensure_ascii=False)
    
    print(f"[sorted] Saved to {OUTPUT_FILE}")
    
    # Print sample
    if funds:
        print("\nSample fund:")
        print(json.dumps(funds[0], indent=2))

if __name__ == "__main__":
    main()