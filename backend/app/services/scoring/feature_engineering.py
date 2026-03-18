"""
feature_engineering.py
-----------------------
Upgrades your existing create_features() with 25+ India-specific
financial ratios used by actual Indian credit officers.

DROP-IN REPLACEMENT — same function name, extended output.
"""
import json
from typing import Union


def safe_div(a, b):
    """Your existing helper — kept as-is."""
    return a / b if b != 0 else 0


def create_features(data_str: Union[str, dict]) -> dict:
    """
    Extended version of your create_features().
    Input:  same dict/JSON string as before
    Output: 25+ features instead of 5
    """
    data = data_str if isinstance(data_str, dict) else json.loads(data_str)

    # ── Raw inputs ────────────────────────────────────────────────────────────
    revenue     = float(data.get("revenue", 1) or 1)
    debt        = float(data.get("debt", 0) or 0)
    profit      = float(data.get("profit", 0) or 0)
    cashflow    = float(data.get("cashflow", 0) or 0)
    ebitda      = float(data.get("ebitda", profit * 1.2) or 0)   # fallback estimate
    interest    = float(data.get("interest_expense", 0) or 0)
    current_assets  = float(data.get("current_assets", 0) or 0)
    current_liab    = float(data.get("current_liabilities", 1) or 1)
    inventory   = float(data.get("inventory", 0) or 0)
    total_assets    = float(data.get("total_assets", revenue) or revenue)
    equity      = float(data.get("equity", total_assets - debt) or 1)
    loan_requested  = float(data.get("loan_amount", 0) or 0)

    # GST-specific (India)
    gst_declared    = float(data.get("gst_declared_revenue", revenue) or revenue)
    gst_itc_claimed = float(data.get("gst_itc_claimed", 0) or 0)
    gst_itc_eligible = float(data.get("gst_itc_eligible", gst_itc_claimed) or 1)

    # Counts
    fraud_signals   = data.get("fraud_signals", [])
    legal_issues    = data.get("legal_issues", [])
    bounced_cheques = int(data.get("bounced_cheques", 0) or 0)
    emi_delays      = int(data.get("emi_delays", 0) or 0)
    years_in_biz    = int(data.get("years_in_business", 3) or 3)
    existing_loans  = float(data.get("existing_loans", 0) or 0)
    collateral_val  = float(data.get("collateral_value", 0) or 0)

    # ── Feature 1-5: Your original features (preserved) ──────────────────────
    debt_ratio      = safe_div(debt, revenue)
    profit_margin   = safe_div(profit, revenue)
    cashflow_flag   = 1 if cashflow < 0 else 0      # ✅ Fixed: 1=negative=BAD
    fraud_count     = len(fraud_signals)
    legal_count     = len(legal_issues)

    # ── Feature 6-10: Liquidity ───────────────────────────────────────────────
    current_ratio   = safe_div(current_assets, current_liab)
    # Good: >1.5 | Caution: 1-1.5 | Bad: <1
    quick_ratio     = safe_div(current_assets - inventory, current_liab)
    # Good: >1.0 | Bad: <0.5
    working_capital = current_assets - (current_liab if current_liab else 0)
    wc_to_revenue   = safe_div(working_capital, revenue)
    cash_ratio      = safe_div(cashflow, current_liab)

    # ── Feature 11-15: Debt & Leverage ───────────────────────────────────────
    debt_to_equity  = safe_div(debt, equity)
    # Good: <2 | Caution: 2-4 | Bad: >4
    interest_coverage = safe_div(ebitda, interest) if interest > 0 else 10.0
    # Good: >3 | Caution: 1.5-3 | Bad: <1.5
    dscr = safe_div(cashflow, interest + (loan_requested * 0.1))
    # Debt Service Coverage Ratio — Good: >1.25 | Bad: <1
    total_leverage  = safe_div(debt + existing_loans, total_assets)
    loan_to_revenue = safe_div(loan_requested, revenue)

    # ── Feature 16-18: Profitability ─────────────────────────────────────────
    ebitda_margin   = safe_div(ebitda, revenue)
    roa             = safe_div(profit, total_assets)   # Return on Assets
    roe             = safe_div(profit, equity)          # Return on Equity

    # ── Feature 19-21: India-specific GST Intelligence ───────────────────────
    gst_revenue_match = safe_div(gst_declared, revenue)
    # Should be ~1.0; <0.7 = revenue inflation red flag
    itc_utilisation = safe_div(gst_itc_claimed, gst_itc_eligible)
    # >1.05 = ITC overclaim red flag (GSTR-2A vs 3B mismatch)
    gst_compliance_score = 1.0 if 0.85 <= gst_revenue_match <= 1.15 else (
        0.5 if 0.7 <= gst_revenue_match < 0.85 else 0.0
    )

    # ── Feature 22-25: Behavioural / Credit History ───────────────────────────
    cheque_bounce_flag  = 1 if bounced_cheques > 2 else 0
    emi_delay_flag      = 1 if emi_delays > 3 else 0
    collateral_coverage = safe_div(collateral_val, loan_requested) if loan_requested else 0
    # Good: >1.5x | Minimum: 1.0x | Bad: <1.0x
    business_vintage    = min(years_in_biz / 10.0, 1.0)  # 0-1 normalized

    return {
        # ── Original 5 (preserved for backward compat) ──
        "debt_ratio":           round(debt_ratio, 4),
        "profit_margin":        round(profit_margin, 4),
        "cashflow_flag":        cashflow_flag,
        "fraud_count":          fraud_count,
        "legal_count":          legal_count,

        # ── Liquidity ────────────────────────────────────
        "current_ratio":        round(current_ratio, 4),
        "quick_ratio":          round(quick_ratio, 4),
        "working_capital":      round(working_capital, 2),
        "wc_to_revenue":        round(wc_to_revenue, 4),
        "cash_ratio":           round(cash_ratio, 4),

        # ── Leverage & Debt ──────────────────────────────
        "debt_to_equity":       round(debt_to_equity, 4),
        "interest_coverage":    round(interest_coverage, 4),
        "dscr":                 round(dscr, 4),
        "total_leverage":       round(total_leverage, 4),
        "loan_to_revenue":      round(loan_to_revenue, 4),

        # ── Profitability ────────────────────────────────
        "ebitda_margin":        round(ebitda_margin, 4),
        "roa":                  round(roa, 4),
        "roe":                  round(roe, 4),

        # ── GST Intelligence (India-specific) ───────────
        "gst_revenue_match":    round(gst_revenue_match, 4),
        "itc_utilisation":      round(itc_utilisation, 4),
        "gst_compliance_score": round(gst_compliance_score, 4),

        # ── Behavioural ──────────────────────────────────
        "cheque_bounce_flag":   cheque_bounce_flag,
        "emi_delay_flag":       emi_delay_flag,
        "collateral_coverage":  round(collateral_coverage, 4),
        "business_vintage":     round(business_vintage, 4),

        # ── Raw values (needed by risk_model & scoring) ──
        "_revenue":             revenue,
        "_loan_requested":      loan_requested,
        "_collateral_value":    collateral_val,
        "_years_in_business":   years_in_biz,
    }