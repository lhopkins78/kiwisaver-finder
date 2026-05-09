// KiwiSaver Fund Finder — Frontend Logic

const fundData = [];
let filteredFunds = [];

async function loadFundData() {
    try {
        const response = await fetch('data/funds.json');
        if (response.ok) {
            const data = await response.json();
            fundData.splice(0, 0, ...data);
            renderAllFunds();
        }
    } catch (e) {
        console.log('Fund data not yet available — early development');
    }
}

function classifyAge(age) {
    age = parseInt(age);
    if (age < 35) return 'aggressive';
    if (age < 50) return 'growth';
    if (age < 60) return 'balanced';
    return 'conservative';
}

function recommendFund(fund) {
    const fee = fund.fee_total_pct;
    const ret = fund.returns_5yr_pct;
    const retAvg = fund.returns_5yr_avg_pct || 0;

    // NZ passive benchmark: Simplicity 0.10%, Kernel 0.20%, Smartshares 0.30-0.50%
    // Any fund <0.70% is in passive territory — compare to benchmark returns
    if (fee < 0.70) {
        // Passive fund — check if it performs acceptably vs average
        if (ret != null && retAvg != null) {
            if (ret >= retAvg * 0.9) {
                // Within 90% of average — it's tracking the index well
                return { status: 'recommended', reasons: [] };
            } else {
                // Significantly below average for a passive fund — minor concern
                return {
                    status: 'review',
                    reasons: [`Return ${ret.toFixed(1)}% vs avg ${retAvg.toFixed(1)}% — below passive benchmark`]
                };
            }
        }
        // No return data but low fee — tentatively recommended
        return { status: 'recommended', reasons: [] };
    }

    // Active fund >0.70% — must justify the fee premium
    if (fee > 1.0) {
        return {
            status: 'avoid',
            reasons: [
                `Fees ${fee.toFixed(2)}% — passive alternative under 0.7%`,
                ret != null && retAvg != null && ret < retAvg
                    ? `Underperformed benchmark by ${(retAvg - ret).toFixed(1)}% over 5 years`
                    : 'Active fees not justified without strong outperformance'
            ]
        };
    }


    // 0.70-1.0% active fund — review if underperforming
    if (ret != null && retAvg != null && ret < retAvg - 0.5) {
        return {
            status: 'avoid',
            reasons: [
                `Fees ${fee.toFixed(2)}% — marginal value`,
                `Underperformed benchmark by ${(retAvg - ret).toFixed(1)}%`
            ]
        };
    }

    return { status: 'review', reasons: [] };
}

function renderResults(age, goal, type) {
    const recList = document.getElementById('recommended-list');
    const avoidList = document.getElementById('avoid-list');

    let effectiveType = type === 'unknown' ? classifyAge(age) : type;

    // Filter and score all funds
    const scored = fundData
        .filter(f => f.fund_type === effectiveType || !effectiveType || effectiveType === 'unknown')
        .map(f => ({ ...f, ...recommendFund(f) }))
        .sort((a, b) => {
            // recommended first, then by fee asc
            if (a.status === 'recommended' && b.status !== 'recommended') return -1;
            if (a.status !== 'recommended' && b.status === 'recommended') return 1;
            if (a.status === 'avoid' && b.status !== 'avoid') return 1;
            if (a.status !== 'avoid' && b.status === 'avoid') return -1;
            return (a.fee_total_pct || 999) - (b.fee_total_pct || 999);
        });

    const recommended = scored.filter(f => f.status === 'recommended');
    const avoid = scored.filter(f => f.status === 'avoid');
    const review = scored.filter(f => f.status === 'review');

    recList.innerHTML = buildSection('✅ Recommended', recommended);
    avoidList.innerHTML = buildSection('⚠️ Review', review) + buildSection('❌ Avoid', avoid);
}

function buildSection(title, funds) {
    if (!funds.length) return '';
    let html = `<div class="rec-section">`;
    html += `<h3>${title} <span class="count">${funds.length}</span></h3>`;
    funds.slice(0, 5).forEach(f => html += buildFundCard(f));
    if (funds.length > 5) {
        html += `<div style="text-align:center;color:var(--text-muted);padding:10px;font-size:0.9rem;">+${funds.length - 5} more</div>`;
    }
    html += `</div>`;
    return html;
}

function buildFundCard(fund) {
    const statusClass = fund.status;
    const feeVal = fund.fee_total_pct || 0;
    const feeClass = feeVal > 0.70 ? 'high' : feeVal > 0.30 ? 'medium' : 'low';
    const feeLabel = feeVal > 0 ? `${feeVal.toFixed(2)}%` : 'N/A';

    let reasonsHTML = '';
    if (fund.reasons && fund.reasons.length) {
        reasonsHTML = '<div style="margin-top:8px;">';
        fund.reasons.forEach(r => {
            reasonsHTML += `<div style="font-size:0.82rem;color:#c0392b;">⚠️ ${r}</div>`;
        });
        reasonsHTML += '</div>';
    }

    const ret5yr = fund.returns_5yr_pct;
    const retAvg = fund.returns_5yr_avg_pct;
    const retLabel = ret5yr != null ? `${ret5yr >= 0 ? '+' : ''}${ret5yr.toFixed(1)}%` : 'N/A';
    const benchLabel = retAvg != null ? `${retAvg >= 0 ? '+' : ''}${retAvg.toFixed(1)}%` : 'N/A';

    return `
    <div class="fund-card ${statusClass}">
        <div class="fund-info">
            <h4>${fund.fund_name}</h4>
            <div class="scheme">${fund.scheme || ''}</div>
            <div class="fund-meta">
                <span>${fund.fund_type || ''}</span>
                ${fund.asset_shares_pct != null ? `<span>${fund.asset_shares_pct}% equities</span>` : ''}
            </div>
            ${reasonsHTML}
        </div>
        <div class="fund-stats">
            <div class="fee ${feeClass}">${feeLabel}</div>
            <div class="returns">5yr: ${retLabel} <span style="color:var(--text-muted)">(avg ${benchLabel})</span></div>
        </div>
    </div>`;
}

function renderAllFunds() {
    const container = document.getElementById('fund-list');
    if (!container || !fundData.length) return;

    const typeFilter = document.getElementById('filter-type')?.value || '';
    const recFilter = document.getElementById('filter-recommendation')?.value || '';

    let funds = fundData.map(f => ({ ...f, ...recommendFund(f) }));

    if (typeFilter) {
        funds = funds.filter(f => f.fund_type === typeFilter);
    }

    if (recFilter) {
        funds = funds.filter(f => f.status === recFilter);
    }

    funds.sort((a, b) => (a.fee_total_pct || 999) - (b.fee_total_pct || 999));

    if (!funds.length) {
        container.innerHTML = '<p class="empty-state">No funds match your filters.</p>';
        return;
    }

    container.innerHTML = funds.slice(0, 50).map(f => buildFundCard(f)).join('') +
        (funds.length > 50 ? `<p class="empty-state">Showing 50 of ${funds.length} funds. More in development.</p>` : '');
}

// Wire up filters
document.addEventListener('DOMContentLoaded', () => {
    const typeFilter = document.getElementById('filter-type');
    const recFilter = document.getElementById('filter-recommendation');
    if (typeFilter) typeFilter.addEventListener('change', renderAllFunds);
    if (recFilter) recFilter.addEventListener('change', renderAllFunds);
});

loadFundData();
