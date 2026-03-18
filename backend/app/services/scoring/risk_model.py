"""
risk_model.py — FIXED
---------------------
Bug: "Unknown" fraud_risk/legal_risk was being treated as HIGH risk
     causing Character score = 0 even for clean companies.

Fix: "Unknown" = neutral (no penalty), only explicit "High" penalizes.
"""
from typing import Union

WEIGHTS = {
    "character":   25,
    "capacity":    30,
    "capital":     20,
    "collateral":  15,
    "conditions":  10,
}

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


def _score_character(f: dict, research: dict) -> tuple:
    score = 25.0
    flags = []

    fraud_count = f.get("fraud_count", 0)
    legal_count = f.get("legal_count", 0)

    # ── Fraud signals from document ───────────────────────────────
    if fraud_count >= 3:
        score -= 20
        flags.append("🚨 Multiple fraud signals detected in documents")
    elif fraud_count > 0:
        score -= fraud_count * 5
        flags.append(f"⚠️ {fraud_count} fraud signal(s) found in documents")

    # ── Legal issues from document ────────────────────────────────
    if legal_count > 3:
        score -= 15
        flags.append("🚨 High litigation count found in documents")
    elif legal_count > 1:
        score -= legal_count * 3
        flags.append(f"⚠️ {legal_count} legal issue(s) found")

    # ── Research-based (FIXED: Unknown = neutral, not penalty) ────
    fraud_risk = research.get("fraud_risk", "Unknown")
    legal_risk = research.get("legal_risk", "Unknown")

    if fraud_risk == "High":
        score -= 15
        flags.append("🚨 High fraud risk from secondary research")
    elif fraud_risk == "Medium":
        score -= 6
        flags.append("⚠️ Medium fraud risk from research")
    # Unknown / Low = no penalty ✅

    if legal_risk == "High":
        score -= 10
        flags.append("🚨 High litigation risk — court records found")
    elif legal_risk == "Medium":
        score -= 4
        flags.append("⚠️ Medium legal risk detected")
    # Unknown / Low = no penalty ✅

    # ── Hard reject: wilful defaulter ────────────────────────────
    if research.get("wilful_defaulter"):
        score = 0
        flags.append("🚨 HARD REJECT: Wilful defaulter on RBI list")

    return max(0, score), flags


def _score_capacity(f: dict) -> tuple:
    score = 30.0
    flags = []

    dscr = f.get("dscr", 0)

    # ── FIXED: if dscr=0 it means data missing, not zero cashflow ─
    if dscr == 0:
        # No cashflow data extracted — give neutral score
        score -= 5
        flags.append("ℹ️ DSCR could not be calculated — cashflow data missing")
    elif dscr >= 1.5:
        pass
    elif dscr >= 1.25:
        score -= 5
        flags.append(f"ℹ️ DSCR {dscr:.2f}x — adequate but tight")
    elif dscr >= 1.0:
        score -= 12
        flags.append(f"⚠️ DSCR {dscr:.2f}x — barely covering debt service")
    else:
        score -= 22
        flags.append(f"🚨 DSCR {dscr:.2f}x — insufficient cashflow")

    icr = f.get("interest_coverage", 0)
    if icr == 0:
        score -= 3   # missing data, small penalty only
    elif icr < 1.5:
        score -= 10
        flags.append(f"🚨 ICR {icr:.2f}x — EBITDA barely covers interest")
    elif icr < 2.5:
        score -= 4
        flags.append(f"⚠️ ICR {icr:.2f}x — thin interest coverage")

    if f.get("cashflow_flag"):
        score -= 5
        flags.append("⚠️ Negative operating cashflow")

    pm = f.get("profit_margin", 0)
    if pm < 0:
        score -= 8
        flags.append(f"🚨 Net loss — profit margin {pm*100:.1f}%")
    elif pm < 0.05:
        score -= 3
        flags.append(f"⚠️ Very thin margin {pm*100:.1f}%")

    return max(0, score), flags


def _score_capital(f: dict) -> tuple:
    score = 20.0
    flags = []

    dte = f.get("debt_to_equity", 0)
    if dte == 0:
        score -= 2   # missing data only
    elif dte > 4:
        score -= 15
        flags.append(f"🚨 Very high D/E ratio {dte:.2f}x — over-leveraged")
    elif dte > 2:
        score -= 6
        flags.append(f"⚠️ High D/E ratio {dte:.2f}x")
    elif dte > 1:
        score -= 2

    dr = f.get("debt_ratio", 0)
    if dr > 0.8:
        score -= 6
        flags.append(f"🚨 Debt/Revenue {dr:.2f} — highly leveraged")
    elif dr > 0.5:
        score -= 2

    if f.get("roa", 0) < 0:
        score -= 4
        flags.append("⚠️ Negative Return on Assets")

    return max(0, score), flags


def _score_collateral(f: dict) -> tuple:
    score = 15.0
    flags = []

    cov = f.get("collateral_coverage", 0)
    if cov == 0:
        # No collateral data — small penalty, not zero
        score -= 5
        flags.append("ℹ️ Collateral data not found in document")
    elif cov >= 1.5:
        pass
    elif cov >= 1.25:
        score -= 3
        flags.append(f"ℹ️ Collateral {cov:.2f}x — acceptable")
    elif cov >= 1.0:
        score -= 7
        flags.append(f"⚠️ Collateral {cov:.2f}x — minimal margin")
    else:
        score -= 12
        flags.append(f"🚨 Under-collateralised — {cov:.2f}x coverage")

    return max(0, score), flags


def _score_conditions(f: dict, research: dict) -> tuple:
    score = 10.0
    flags = []

    gst = f.get("gst_compliance_score", 1.0)
    if gst == 0:
        score -= 5
        flags.append("🚨 GST revenue mismatch detected")
    elif gst < 1.0:
        score -= 2
        flags.append("⚠️ Minor GST discrepancy")

    itc = f.get("itc_utilisation", 1.0)
    if itc > 1.1:
        score -= 3
        flags.append(f"🚨 ITC overclaim {itc:.2f} — GSTR-2A/3B mismatch")

    # FIXED: Unknown sector_risk = neutral
    sector_risk = research.get("sector_risk", "Unknown")
    if sector_risk == "High":
        score -= 3
        flags.append("⚠️ Sector facing headwinds per research")

    if f.get("business_vintage", 0.5) < 0.2:
        score -= 2
        flags.append("⚠️ Business less than 2 years old")

    if f.get("cheque_bounce_flag"):
        score -= 3
        flags.append("⚠️ Multiple cheque bounces")

    return max(0, score), flags


def _get_rating(score: float) -> tuple:
    for lo, hi, rating, risk in RATING_BANDS:
        if lo <= score < hi:
            return rating, risk
    return "D", "CRITICAL"


def calculate_risk(f: dict, research: dict = None) -> dict:
    if research is None:
        research = {}

    char_score,  char_flags  = _score_character(f, research)
    cap_score,   cap_flags   = _score_capacity(f)
    capit_score, capit_flags = _score_capital(f)
    coll_score,  coll_flags  = _score_collateral(f)
    cond_score,  cond_flags  = _score_conditions(f, research)

    total   = char_score + cap_score + capit_score + coll_score + cond_score
    rating, risk_level = _get_rating(total)
    all_flags = char_flags + cap_flags + capit_flags + coll_flags + cond_flags

    hard_reject = any([
        research.get("wilful_defaulter"),
        f.get("fraud_count", 0) >= 3,
    ])

    return {
        "risk_level":   "CRITICAL" if hard_reject else risk_level,
        "total_score":  round(total, 2),
        "rating":       "D" if hard_reject else rating,
        "hard_reject":  hard_reject,
        "five_c_scores": {
            "character":  round(char_score, 2),
            "capacity":   round(cap_score, 2),
            "capital":    round(capit_score, 2),
            "collateral": round(coll_score, 2),
            "conditions": round(cond_score, 2),
        },
        "risk_flags":  all_flags,
        "key_factors": {
            "dscr":                f.get("dscr", 0),
            "debt_to_equity":      f.get("debt_to_equity", 0),
            "collateral_coverage": f.get("collateral_coverage", 0),
            "gst_compliance":      f.get("gst_compliance_score", 0),
            "fraud_count":         f.get("fraud_count", 0),
            "legal_count":         f.get("legal_count", 0),
        }
    }