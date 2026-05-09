# Methodology

## Data Sources

1. **Companies Office Scheme Registry** — registered KiwiSaver schemes in NZ
2. **Provider disclosure statements** — quarterly/annual reports with fund performance and fee data
3. **Sorted.org.nz** — comparison tool data
4. **NZX / market data** — benchmark indices for performance comparison

## Fund Classification

### Primary: Equity/Bond Split

The fund type is expressed as actual percentages, not NZ-specific labels.

| Classification | Equity | Bonds |
|---|---|---|
| Defensive | 0–30% | 70–100% |
| Moderate | 30–50% | 50–70% |
| Balanced | 50–70% | 30–50% |
| Growth | 70–85% | 15–30% |
| Aggressive | 85–95% | 5–15% |
| Total Equities | 95–100% | 0–5% |

### Secondary: Geographic Split

For equity portion only:

- **NZ Heavy**: >30% NZX-listed equities
- **AUS Heavy**: >30% ASX-listed equities  
- **Global Diversified**: Mixed international markets
- **Global (Unhedged)**: Pure global index, no FX hedging
- **Global (Hedged)**: Global index with NZD currency hedging

### Active vs Passive

- **Passive**: Index-tracking fund, mimics benchmark exactly
- **Active**: Fund manager makes allocation decisions, aims to beat benchmark

## Performance Metrics

### Annualised Returns

Reported as net of fees, before tax. Displayed for:
- 1 year
- 3 years
- 5 years
- 10 years (where available)

### Benchmark Comparison

Each fund has a relevant market index benchmark:
- NZ 50 / S&P/NZX 50 for NZ-heavy funds
- MSCI Australia for AUS-heavy funds
- MSCI World or MSCI ACWI for global funds

Outperformance is measured *after fees*. A fund that beats benchmark by 0.5% but charges 1.2% is still worse than a passive fund at 0.2%.

### Risk Metrics

- **Sharpe Ratio**: Risk-adjusted return (return above cash rate / standard deviation). Above 0.5 is acceptable for growth funds, above 0.7 is good.
- **Standard Deviation**: Annualised volatility. Higher = more ups and downs.
- **Max Drawdown**: Largest peak-to-trough loss over the measurement period.

## Avoid Algorithm

A fund is flagged **Avoid** when it meets **any** of these conditions:

1. **Fee > 1.0%** — regardless of performance. Passive alternatives exist at under 0.3%.
2. **Fee > 0.8% AND 5yr return below benchmark** — paying premium fees for underperformance
3. **Active fund that has missed benchmark for 3+ consecutive years** — persistent underperformance
4. **Sharpe ratio < 0.5 over 5 years** — poor risk-adjusted returns

## Recommended Criteria

A fund is flagged **Recommended** when:

1. **Fee < 0.4%**
2. **5yr annualised return within 0.5% of benchmark** (passive funds can't beat benchmark, but should track it closely)
3. **Sharpe ratio > 0.5**

A passive fund with very low fees that tracks its benchmark closely is the ideal. High fees on active funds are the primary problem.

## Fee Impact Calculation

Fee impact is calculated as:

```
Baseline: 0.2% passive index fund
vs
Fund in question

Assume: $50k balance, 30 years, 7% gross return
```

The difference in terminal balances is shown as the "fee cost" — e.g., "$95,000 more expensive over 30 years than the passive alternative."

This is not the total fees paid — it's the *opportunity cost* of being in a high-fee fund vs a low-fee passive alternative. It compounds in reverse.

## Data Freshness

- Fund data is updated monthly
- Performance data is updated quarterly (after providers report)
- Users can submit corrections via GitHub PR
- All corrections require a source citation

## Limitations

- Past performance does not guarantee future returns
- Data is indicative — always verify with the provider before switching
- Tax treatment varies by personal situation and PIR rate
- This tool is financial information, not financial advice
