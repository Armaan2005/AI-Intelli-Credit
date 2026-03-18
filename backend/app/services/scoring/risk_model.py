"""
risk_model.py
-------------
Upgrades your existing calculate_risk() from 5 hardcoded rules
to a weighted multi-factor scoring engine with India-specific thresholds.

DROP-IN REPLACEMENT — same function name, much richer output.
"""
from typing import Union


# ─────────────────────────────────────────────────────────────────────────────
#  SCORING WEIGHTS  (total = 100 points)
#  Based on actual Indian bank credit policy weightage
# ─────────────────────────────────────────────────────────────────────────────
WEIGHTS = {
    "character":   25,   # Fraud, legal, promoter background
    "capacity":    30,   # Cashflow, DSCR, interest coverage
    "capital":     20,   # Leverage, debt/equity, profitability
    "collateral":  15,   # Coverage ratio, asset quality
    "conditions":  10,   # GST compliance, sector, vintage
}

# ─────────────────────────────────────────────────────────────────────────────
#  RATING BANDS  (maps 0-100 score → rating → risk level)
# ─────────────────────────────────────────────────────────────────────────────
RATING_BANDS = [
    (90, 100, "AAA", "VERY_LOW"),
    (80,  90, "AA",  "LOW"),
    (70,  80, "A",   "LOW"),
    (60,  70, "BBB", "MEDIUM"),
    (50,  60, "BB",  "MEDIUM"),
    (40,  50, "B",   "HIGH"),
    (30,  40, "CCC", "HIGH"),
    (0,   30, "D",   "CRITICAL"),
]


def _score_character(f: dict, research: dict) -> tuple[float, list]:
    """
    Character: Who is the borrower? Track record, fraud, litigation.
    Max score: 25 points
    """
    score = 25.0
    flags = []

    # Fraud signals (your existing fraud_count)
    if f["fraud_count"] >= 3:
        score -= 25
        flags.append("🚨 Multiple fraud signals detected")
    elif f["fraud_count"] > 0:
        score -= f["fraud_count"] * 6
        flags.append(f"⚠️ {f['fraud_count']} fraud signal(s) found")

    # Legal issues (your existing legal_count)
    if f["legal_count"] > 3:
        score -= 20
        flags.append("🚨 High litigation count — NCLT/DRT proceedings likely")
    elif f["legal_count"] > 1:
        score -= f["legal_count"] * 4
        flags.append(f"⚠️ {f['legal_count']} legal issue(s) found")

    # Research-based character (from your research_agent)
    if research.get("fraud_risk") == "High":
        score -= 15
        flags.append("🚨 High fraud risk from secondary research")
    elif research.get("fraud_risk") == "Medium":
        score -= 7
        flags.append("⚠️ Medium fraud risk from news/MCA research")

    if research.get("legal_risk") == "High":
        score -= 10
        flags.append("🚨 High litigation risk — court records found")
    elif research.get("legal_risk") == "Medium":
        score -= 5
        flags.append("⚠️ Medium legal risk detected")

    # Wilful defaulter / NPA check
    if research.get("wilful_defaulter"):
        score = 0
        flags.append("🚨 HARD REJECT: Wilful defaulter on RBI list")

    return max(0, score), flags


def _score_capacity(f: dict) -> tuple[float, list]:
    """
    Capacity: Can they repay? Cashflow, DSCR, interest coverage.
    Max score: 30 points
    """
    score = 30.0
    flags = []

    # DSCR — Debt Service Coverage Ratio (most important)
    dscr = f.get("dscr", 1.0)
    if dscr >= 1.5:
        pass  # Full marks
    elif dscr >= 1.25:
        score -= 5
        flags.append(f"ℹ️ DSCR {dscr:.2f} — adequate but tight")
    elif dscr >= 1.0:
        score -= 12
        flags.append(f"⚠️ DSCR {dscr:.2f} — barely covering debt service")
    else:
        score -= 25
        flags.append(f"🚨 DSCR {dscr:.2f} — insufficient cashflow to service debt")

    # Interest Coverage Ratio
    icr = f.get("interest_coverage", 3.0)
    if icr < 1.5:
        score -= 10
        flags.append(f"🚨 ICR {icr:.2f} — EBITDA barely covers interest")
    elif icr < 2.5:
        score -= 4
        flags.append(f"⚠️ ICR {icr:.2f} — thin interest coverage")

    # Cashflow flag (your original — negative cashflow)
    if f.get("cashflow_flag"):
        score -= 8
        flags.append("⚠️ Negative operating cashflow")

    # Profit margin
    pm = f.get("profit_margin", 0)
    if pm < 0:
        score -= 8
        flags.append(f"🚨 Net loss — profit margin {pm*100:.1f}%")
    elif pm < 0.05:
        score -= 4
        flags.append(f"⚠️ Very thin margin {pm*100:.1f}%")

    return max(0, score), flags


def _score_capital(f: dict) -> tuple[float, list]:
    """
    Capital: Financial strength — leverage, equity, profitability.
    Max score: 20 points
    """
    score = 20.0
    flags = []

    # Debt-to-equity
    dte = f.get("debt_to_equity", 1.0)
    if dte > 4:
        score -= 15
        flags.append(f"🚨 Very high D/E ratio {dte:.2f}x — over-leveraged")
    elif dte > 2:
        score -= 7
        flags.append(f"⚠️ High D/E ratio {dte:.2f}x")
    elif dte > 1:
        score -= 3

    # Debt ratio (your original)
    dr = f.get("debt_ratio", 0)
    if dr > 0.8:
        score -= 8
        flags.append(f"🚨 Debt/Revenue ratio {dr:.2f} — highly leveraged")
    elif dr > 0.5:
        score -= 3

    # ROA / ROE
    if f.get("roa", 0) < 0:
        score -= 5
        flags.append("⚠️ Negative Return on Assets")

    return max(0, score), flags


def _score_collateral(f: dict) -> tuple[float, list]:
    """
    Collateral: Security coverage.
    Max score: 15 points
    """
    score = 15.0
    flags = []

    cov = f.get("collateral_coverage", 0)
    if cov >= 1.5:
        pass  # Full marks — 1.5x coverage is ideal
    elif cov >= 1.25:
        score -= 3
        flags.append(f"ℹ️ Collateral coverage {cov:.2f}x — acceptable")
    elif cov >= 1.0:
        score -= 7
        flags.append(f"⚠️ Collateral coverage {cov:.2f}x — minimal margin")
    elif cov > 0:
        score -= 12
        flags.append(f"🚨 Under-collateralised — coverage only {cov:.2f}x")
    else:
        score -= 15
        flags.append("🚨 No collateral provided")

    return max(0, score), flags


def _score_conditions(f: dict, research: dict) -> tuple[float, list]:
    """
    Conditions: External factors — GST compliance, sector outlook, vintage.
    Max score: 10 points
    """
    score = 10.0
    flags = []

    # GST compliance (India-specific)
    gst_score = f.get("gst_compliance_score", 1.0)
    if gst_score == 0:
        score -= 6
        flags.append("🚨 GST revenue mismatch — possible revenue inflation")
    elif gst_score < 1.0:
        score -= 3
        flags.append("⚠️ Minor GST discrepancy detected")

    # ITC overclaim (GSTR-2A vs 3B)
    itc = f.get("itc_utilisation", 1.0)
    if itc > 1.1:
        score -= 4
        flags.append(f"🚨 ITC utilisation {itc:.2f} — possible GSTR-2A/3B mismatch")

    # Sector outlook
    if research.get("sector_risk") == "High":
        score -= 4
        flags.append("⚠️ Sector facing headwinds per research")

    # Business vintage
    vintage = f.get("business_vintage", 0.3)
    if vintage < 0.2:   # < 2 years
        score -= 3
        flags.append("⚠️ Business less than 2 years old")

    # Cheque bounces
    if f.get("cheque_bounce_flag"):
        score -= 4
        flags.append("⚠️ Multiple cheque bounces — banking conduct issue")

    return max(0, score), flags


def _get_rating(total_score: float) -> tuple[str, str]:
    for lo, hi, rating, risk in RATING_BANDS:
        if lo <= total_score < hi:
            return rating, risk
    return "D", "CRITICAL"


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API — Drop-in replacement for your calculate_risk()
# ─────────────────────────────────────────────────────────────────────────────

def calculate_risk(f: dict, research: dict = None) -> Union[str, dict]:
    """
    UPGRADED version of your calculate_risk(f).

    Now accepts optional research dict (from research_agent.py).
    Returns full dict instead of just "HIGH"/"MEDIUM"/"LOW".

    Backward-compatible: if you only check result["risk_level"]
    it still works exactly like before.
    """
    if research is None:
        research = {}

    char_score,  char_flags  = _score_character(f, research)
    cap_score,   cap_flags   = _score_capacity(f)
    capit_score, capit_flags = _score_capital(f)
    coll_score,  coll_flags  = _score_collateral(f)
    cond_score,  cond_flags  = _score_conditions(f, research)

    total = char_score + cap_score + capit_score + coll_score + cond_score
    rating, risk_level = _get_rating(total)

    all_flags = char_flags + cap_flags + capit_flags + coll_flags + cond_flags

    # Hard reject rules — override everything
    hard_reject = any([
        research.get("wilful_defaulter"),
        f.get("fraud_count", 0) >= 3,
        f.get("dscr", 1.0) < 0.5,
    ])

    return {
        # Backward-compatible field (your original return value)
        "risk_level": "CRITICAL" if hard_reject else risk_level,

        # New fields for advanced_scoring & explainer
        "total_score":  round(total, 2),
        "rating":       "D" if hard_reject else rating,
        "hard_reject":  hard_reject,

        # Five Cs breakdown (for CAM report)
        "five_c_scores": {
            "character":  round(char_score, 2),
            "capacity":   round(cap_score, 2),
            "capital":    round(capit_score, 2),
            "collateral": round(coll_score, 2),
            "conditions": round(cond_score, 2),
        },

        # All risk flags with emojis (for explainability)
        "risk_flags": all_flags,

        # Feature summary for SHAP-style display
        "key_factors": {
            "dscr":               f.get("dscr", 0),
            "debt_to_equity":     f.get("debt_to_equity", 0),
            "collateral_coverage":f.get("collateral_coverage", 0),
            "gst_compliance":     f.get("gst_compliance_score", 0),
            "fraud_count":        f.get("fraud_count", 0),
            "legal_count":        f.get("legal_count", 0),
        }
    }