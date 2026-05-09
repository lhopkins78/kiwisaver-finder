"""
Sorted Smart Investor scraper — efficient resumable version.
API returns JSON with HTML card fragments in `results` array.
Saves progress after each page so we can resume if interrupted.
"""
import json, time, sys
from pathlib import Path
import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).parent.parent.parent / "data"
OUTPUT_FILE = BASE_DIR / "sorted_funds.json"
STATE_FILE = BASE_DIR / "sorted_funds_state.json"

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            s = json.load(f)
        return {"page": s["page"], "seen_ids": set(s["seen_ids"])}
    return {"page": 1, "seen_ids": set()}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump({"page": state["page"], "seen_ids": list(state["seen_ids"])}, f)

def scrape_page(page, per_page=10, retries=3):
    url = "https://smartinvestor.sorted.org.nz/kiwisaver-and-managed-funds/get_results/"
    params = {
        "managedFundTypes": "kiwisaver-funds",
        "sortColumn": "fundName",
        "sortDirection": "asc",
        "page": page,
        "results_per_page": per_page
    }
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code != 200:
                print(f"HTTP {r.status_code}", file=sys.stderr)
                return None
            return r.json()
        except Exception as e:
            print(f"attempt {attempt+1} failed: {e}", file=sys.stderr)
            time.sleep(2 ** attempt)
    return None

def parse_fund_card(html_str):
    """Parse a single fund card HTML string into a dict."""
    soup = BeautifulSoup(html_str, 'html.parser')
    fund = {}

    card_div = soup.find('div', class_='card')
    if card_div:
        fund['scheme'] = card_div.get('data-scheme', '').strip()
        fund['card_id'] = card_div.get('data-id', '').strip()

    title_el = soup.find('h3', class_='card__title')
    if title_el:
        fund['fund_name'] = title_el.get_text(strip=True)

    # Fund type tag — format is 'Tag -Defensive', 'Tag -Conservative' etc
    for tag in soup.find_all(class_='tag'):
        text = tag.get_text(strip=True)
        if text.startswith('Tag -'):
            fund_type = text.split('Tag -', 1)[-1].lower()
            if fund_type in ['defensive', 'conservative', 'balanced', 'growth', 'aggressive']:
                fund['fund_type'] = fund_type
                break

    # Find fee canvases (data-label='Fees') — may be multiple
    # Positive values represent annual fee %; take the largest (most representative)
    pos_fees = []
    for canvas in soup.find_all('canvas', {'data-label': 'Fees'}):
        dataset_str = canvas.get('data-dataset', '').replace('&quot;', '"')
        if not dataset_str:
            continue
        try:
            dataset = json.loads(dataset_str)
            if dataset and len(dataset) >= 1:
                data = dataset[0].get('data', [])
                if data and len(data) >= 1:
                    val = float(data[0])
                    if val > 0:
                        pos_fees.append(val)
        except:
            pass
    if pos_fees:
        fund['fee_total_pct'] = round(max(pos_fees), 4)

    # Find the returns canvas (has year/fund/average structure — 5 entries for 5 years)
    for canvas in soup.find_all('canvas'):
        dataset_str = canvas.get('data-dataset', '').replace('&quot;', '"')
        if not dataset_str:
            continue
        try:
            dataset = json.loads(dataset_str)
            if dataset and isinstance(dataset[0], dict) and 'year' in dataset[0]:
                # dataset is sorted by year ascending — last entry = most recent (2026)
                last = dataset[-1]
                fund['returns_1yr_pct'] = round(float(last['fund']), 2)
                fund['returns_1yr_avg_pct'] = round(float(last['average']), 2)
                # Use cumulative return from last year entry as 5yr return
                fund['returns_5yr_pct'] = round(float(last['fund']), 2)
                fund['returns_5yr_avg_pct'] = round(float(last['average']), 2)
                break
        except:
            pass

    # Asset class percentages — second entry's data value is the actual %
    asset_map = {
        'Shares': 'asset_shares_pct',
        'Property': 'asset_property_pct',
        'Bonds': 'asset_bonds_pct',
        'Fixed Interest': 'asset_bonds_pct',
        'Cash': 'asset_cash_pct',
    }
    for canvas in soup.find_all('canvas'):
        dataset_str = canvas.get('data-dataset', '').replace('&quot;', '"')
        label = canvas.get('data-label', '')
        if not dataset_str or label not in asset_map:
            continue
        try:
            dataset = json.loads(dataset_str)
            if dataset and len(dataset) >= 2:
                # Second entry's data[0] = percentage for this asset class
                pct = float(dataset[1]['data'][0])
                key = asset_map[label]
                fund[key] = round(pct, 2)
        except:
            pass

    return {k: v for k, v in fund.items() if v is not None}

def main():
    print("[sorted] KiwiSaver fund scraper — resumable")
    print(f"[sorted] Output: {OUTPUT_FILE}\n")

    state = load_state()
    start_page = state["page"]
    seen_ids = state["seen_ids"]
    all_funds = []

    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            existing = json.load(f)
        if isinstance(existing, list):
            for fund in existing:
                cid = fund.get('card_id')
                if cid and cid not in seen_ids:
                    all_funds.append(fund)
                    seen_ids.add(cid)
            print(f"[sorted] Loaded {len(existing)} existing funds, {len(all_funds)} new needed")

    print(f"[sorted] Starting from page {start_page}\n")

    page = start_page
    consecutive_empty = 0

    while True:
        data = scrape_page(page)
        if not data:
            print(f"\n[sorted] Failed to fetch page {page} — resuming later")
            save_state({"page": page, "seen_ids": list(seen_ids)})
            break

        results = data.get('results', [])
        print(f"[sorted] Page {page}: {len(results)} cards | total: {len(all_funds)}", flush=True)

        if not results:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                print("[sorted] 3 empty pages — done")
                break
        else:
            consecutive_empty = 0

        new_count = 0
        for html_str in results:
            # Quick dedup
            try:
                soup_t = BeautifulSoup(html_str, 'html.parser')
                card_div = soup_t.find('div', class_='card')
                card_id = card_div.get('data-id', '').strip() if card_div else ''
            except:
                card_id = ''

            if card_id in seen_ids:
                continue

            fund = parse_fund_card(html_str)
            if fund.get('fund_name'):
                fund['card_id'] = card_id
                all_funds.append(fund)
                seen_ids.add(card_id)
                new_count += 1

        has_more = data.get('has_more', False)
        print(f"[sorted]   +{new_count} new | next page: {data.get('next_page') or 'none'}", flush=True)

        if not has_more:
            print("[sorted] Reached last page")
            break

        # Checkpoint every 5 pages
        if page > start_page and page % 5 == 0:
            save_state({"page": page + 1, "seen_ids": list(seen_ids)})
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(all_funds, f, indent=2)
            print(f"[sorted] Checkpoint saved ({len(all_funds)} funds)")

        page += 1
        time.sleep(0.3)

    # Final save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_funds, f, indent=2)
    if STATE_FILE.exists():
        STATE_FILE.unlink()

    print(f"\n[sorted] Done — {len(all_funds)} funds saved")

    if all_funds:
        sample = dict(all_funds[0])
        print(f"\nSample: {json.dumps(sample, indent=2)}")

        fees = [f.get('fee_total_pct') for f in all_funds if f.get('fee_total_pct')]
        returns = [f.get('returns_5yr_pct') for f in all_funds if f.get('returns_5yr_pct')]
        types = {}
        for f in all_funds:
            types[f.get('fund_type', 'unknown')] = types.get(f.get('fund_type', 'unknown'), 0) + 1

        print(f"\nStats ({len(all_funds)} funds):")
        if fees:
            print(f"  Fee range: {min(fees):.2f}% – {max(fees):.2f}%")
        if returns:
            print(f"  5yr return range: {min(returns):.2f}% – {max(returns):.2f}%")
        print(f"  Fund types: {types}")

if __name__ == "__main__":
    main()
