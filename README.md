# KiwiSaver Fund Finder

Open source, recommendation-led fund comparison for NZ KiwiSaver schemes.

**Problem:** Existing tools list all funds and leave the decision work to the user. High-fee active funds that consistently underperform are buried in sortable tables.

**Solution:** Do the work for the user. Flag actively underperforming funds, expose fee drag, recommend passive alternatives, and make switching frictionless.

---

## Principles

- **Recommendation-led, not list-led** — The tool tells you what to avoid and why, rather than just presenting numbers
- **Fees compound, and they're the biggest variable** — Display fee impact prominently, not as a footnote
- **No ESG scoring** — Pure financial performance. What you own affects returns, not Dow Jones assessments
- **Community-maintained data** — Corrections via PR, auditable methodology

---

## Classification System

### Fund Type = Equity% / Bond%

| Type | Equity | Bonds |
|------|--------|-------|
| Defensive | 0-30% | 70-100% |
| Moderate | 30-50% | 50-70% |
| Balanced | 50-70% | 30-50% |
| Growth | 70-85% | 15-30% |
| Aggressive | 85-95% | 5-15% |
| Total Equities | 95-100% | 0-5% |

### Geographic Split (within equities)

| Label | Description |
|-------|-------------|
| NZ Heavy | >30% NZX |
| AUS Heavy | >30% ASX |
| Global Diversified | Mixed global |
| Global Unhedged | Global passive, no FX hedging |
| Global Hedged | Global with currency hedging applied |

### Fee Tiers

| Tier | Fee Rate |
|------|----------|
| Low | <0.30% |
| Medium | 0.30-0.70% |
| High | >0.70% |

---

## Avoid Algorithm

A fund is flagged **Avoid** when:
- Fee > 0.8% AND 5yr annualised return below peer median
- Fee > 1.0% (passive alternative exists under 0.3%)
- Active fund that has underperformed its benchmark for 3+ consecutive years
- 5yr Sharpe ratio below 0.5 (risk-adjusted returns poor)

---

## Data

All fund data lives in `/data/funds.csv`. Contributions welcome via PR.

Data sources:
- Scheme disclosure statements (quarterly reports)
- Companies Office scheme registry
- Sorted.org.nz comparison tool

---

## Tech Stack

- **Data:** Python scripts for scraping and analysis
- **Storage:** CSV files in repo (auditable, community-updatable)
- **Web:** Static site (deploy to GitHub Pages)
- **Hosting:** Free, open source

---

## Status

Early stages. Data collection and schema design in progress.

## Contributing

Corrections to fund data welcome. Please include source when submitting PRs.
