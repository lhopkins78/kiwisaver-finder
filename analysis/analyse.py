"""
KiwiSaver Fund Analyser

Loads fund data, applies the avoid algorithm, and produces recommendations.

Usage:
    python analyse.py                    # analyse all funds
    python analyse.py --type growth      # filter by fund type
    python analyse.py --output json      # output as JSON
"""

import csv
import json
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent.parent / "data"
INPUT_FILE = BASE_DIR / "funds.csv"

# Avoid thresholds
AVOID_FEE_HIGH = 1.0          # Any fund >1% fees is automatically flagged
AVOID_FEE_MEDIUM = 0.8        # >0.8% AND underperforms benchmark
AVOID_UNDERPERFORMANCE_YRS = 3 # consecutive years of underperformance
AVOID_SHARPE = 0.5            # risk-adjusted return below this is poor

# Recommended thresholds
REC_FEE_MAX = 0.4             # fee must be <0.4% to be recommended
REC_MIN_RETURNS_BENCHMARK = -0.5  # can't be more than 0.5% below benchmark

def load_funds():
    """Load fund data from CSV"""
    funds = []
    if not INPUT_FILE.exists():
        print(f"[error] No data file found at {INPUT_FILE}")
        return funds
    
    with open(INPUT_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            funds.append(row)
    
    print(f"[data] Loaded {len(funds)} funds")
    return funds

def classify_fund(equity_pct):
    """Classify fund type based on equity percentage"""
    if equity_pct >= 95:
        return "Total Equities"
    elif equity_pct >= 85:
        return "Aggressive"
    elif equity_pct >= 70:
        return "Growth"
    elif equity_pct >= 50:
        return "Balanced"
    elif equity_pct >= 30:
        return "Moderate"
    else:
        return "Defensive"

def get_fee_tier(fee_pct):
    """Get fee tier label"""
    try:
        fee = float(fee_pct)
        if fee < 0.30:
            return "Low"
        elif fee < 0.70:
            return "Medium"
        else:
            return "High"
    except:
        return "Unknown"

def calculate_fee_impact(fee_pct, balance=50000, years=30, return_rate=0.07):
    """
    Calculate the cost of fees over time vs a low-fee alternative.
    Returns extra fees paid vs a 0.2% baseline fund.
    """
    try:
        fee = float(fee_pct)
        balance = float(balance)
        years = int(years)
        return_rate = float(return_rate)
    except:
        return None
    
    baseline_fee = 0.002  # 0.2% passive index baseline
    
    # Future value with given fee
    net_rate = return_rate - fee
    future_value_high_fee = balance * ((1 + net_rate) ** years - 1)
    
    # Future value with baseline fee
    net_rate_baseline = return_rate - baseline_fee
    future_value_baseline = balance * ((1 + net_rate_baseline) ** years - 1)
    
    cost_diff = future_value_baseline - future_value_high_fee
    return round(cost_diff, 0)

def analyse_fund(fund):
    """Analyse a single fund and return recommendation"""
    try:
        fee_pct = float(fund.get("fee_pct", 0))
        returns_5yr = float(fund.get("returns_5yr_pct", 0))
        benchmark_5yr = float(fund.get("benchmark_5yr_pct", 0))
        sharpe_5yr = float(fund.get("sharpe_5yr", 0))
        equity_pct = int(fund.get("type_equity_pct", 0))
        active_passive = fund.get("active_passive", "unknown").lower()
    except (ValueError, TypeError):
        return {"status": "unknown", "reasons": ["Missing or invalid data"]}
    
    recommendation = "review"  # default
    reasons = []
    
    # Apply avoid algorithm
    
    # Rule 1: Fee > 1.0% always flagged
    if fee_pct > AVOID_FEE_HIGH:
        recommendation = "avoid"
        reasons.append(f"High fees ({fee_pct*100:.1f}%) — passive alternatives under 0.3% exist")
    
    # Rule 2: Fee > 0.8% AND underperforming benchmark
    elif fee_pct > AVOID_FEE_MEDIUM:
        if returns_5yr < benchmark_5yr - 0.5:
            recommendation = "avoid"
            reasons.append(f"Fee ({fee_pct*100:.1f}%) above 0.8% and underperforming benchmark by {benchmark_5yr - returns_5yr:.1f}%")
    
    # Rule 3: Active fund underperforming for 3+ years
    if active_passive == "active":
        # Check if we have consecutive underperformance data
        underperform_years = 0
        for yr in ["returns_1yr_pct", "returns_3yr_pct"]:
            val = fund.get(yr)
            bench = fund.get(f"benchmark_{yr.split('_')[1]}_pct")
            if val and bench:
                try:
                    if float(val) < float(bench):
                        underperform_years += 1
                except ValueError:
                    pass
        
        if underperform_years >= AVOID_UNDERPERFORMANCE_YRS:
            recommendation = "avoid"
            reasons.append(f"Underperformed benchmark for {underperform_years} consecutive periods")
    
    # Rule 4: Poor risk-adjusted returns
    if sharpe_5yr and sharpe_5yr < AVOID_SHARPE:
        if recommendation != "avoid":
            recommendation = "avoid"
        reasons.append(f"Poor risk-adjusted returns (Sharpe {sharpe_5yr:.2f} < {AVOID_SHARPE})")
    
    # Recommendations: low fee AND meeting benchmark
    if recommendation != "avoid":
        if fee_pct < REC_FEE_MAX and returns_5yr >= benchmark_5yr + REC_MIN_RETURNS_BENCHMARK:
            recommendation = "recommended"
    
    return {
        "status": recommendation,
        "reasons": reasons,
        "fee_tier": get_fee_tier(fee_pct),
        "fund_type": classify_fund(equity_pct),
        "fee_impact_30yr": calculate_fee_impact(fee_pct)
    }

def format_output(fund, analysis):
    """Format fund with analysis for display"""
    equity = fund.get("type_equity_pct", "?")
    bonds = fund.get("type_bonds_pct", "?")
    geo = []
    if fund.get("geo_nz_pct", "0") != "0":
        geo.append(f"{fund['geo_nz_pct']}% NZ")
    if fund.get("geo_aus_pct", "0") != "0":
        geo.append(f"{fund['geo_aus_pct']}% AUS")
    if fund.get("geo_global_pct", "0") != "0":
        geo.append(f"{fund['geo_global_pct']}% Global")
    
    geo_str = " · ".join(geo) if geo else "Unknown"
    
    return {
        "scheme": fund.get("scheme", "Unknown"),
        "fund_name": fund.get("fund_name", "Unknown"),
        "type": f"{equity}% Equity / {bonds}% Bonds",
        "geography": geo_str,
        "fee": f"{float(fund.get('fee_pct', 0)) * 100:.2f}%",
        "active_passive": fund.get("active_passive", "unknown").title(),
        "returns_5yr": f"{fund.get('returns_5yr_pct', '?')}%" if fund.get('returns_5yr_pct') else "?",
        "benchmark_5yr": f"{fund.get('benchmark_5yr_pct', '?')}%" if fund.get('benchmark_5yr_pct') else "?",
        "recommendation": analysis["status"],
        "reasons": analysis["reasons"],
        "fee_impact_30yr": f"${analysis['fee_impact_30yr']:,.0f}" if analysis.get("fee_impact_30yr") else "?"
    }

def main():
    output_format = "text"
    filter_type = None
    
    args = sys.argv[1:]
    if "--json" in args:
        output_format = "json"
        args.remove("--json")
    if "--type" in args:
        idx = args.index("--type")
        filter_type = args[idx + 1]
    
    funds = load_funds()
    results = []
    
    for fund in funds:
        if filter_type:
            equity = int(fund.get("type_equity_pct", 0))
            fund_type = classify_fund(equity)
            if fund_type.lower() != filter_type.lower():
                continue
        
        analysis = analyse_fund(fund)
        formatted = format_output(fund, analysis)
        formatted["raw"] = fund  # include raw data for JSON output
        results.append(formatted)
    
    if output_format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(f"\n{'='*80}")
        print(f"KIWISAVER FUND ANALYSIS — {datetime.now().strftime('%Y-%m-%d')}")
        print(f"{'='*80}\n")
        
        recommended = [r for r in results if r["recommendation"] == "recommended"]
        avoid = [r for r in results if r["recommendation"] == "avoid"]
        review = [r for r in results if r["recommendation"] == "review"]
        
        print(f"✅ RECOMMENDED ({len(recommended)})\n")
        for r in recommended:
            print(f"  {r['fund_name']} ({r['scheme']})")
            print(f"    {r['type']} · {r['geography']} · {r['fee']} fees · {r['active_passive']}")
            print(f"    5yr return: {r['returns_5yr']} (benchmark {r['benchmark_5yr']})")
            if r.get('fee_impact_30yr') and r['fee_impact_30yr'] != '?':
                print(f"    Fee impact vs passive: {r['fee_impact_30yr']} extra over 30yr")
            print()
        
        print(f"\n❌ AVOID ({len(avoid)})\n")
        for r in avoid:
            print(f"  {r['fund_name']} ({r['scheme']})")
            print(f"    {r['type']} · {r['geography']} · {r['fee']} fees")
            for reason in r.get('reasons', []):
                print(f"    ⚠️ {reason}")
            print()
        
        print(f"\n📋 REVIEW ({len(review)}) — neither recommended nor avoided\n")
        for r in review:
            print(f"  {r['fund_name']} ({r['scheme']})")
            print(f"    {r['type']} · {r['geography']} · {r['fee']} fees")
            print()

if __name__ == "__main__":
    main()
