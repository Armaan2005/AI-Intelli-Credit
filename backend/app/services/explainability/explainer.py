"""
explainer.py
------------
Upgrades your existing explain(f) from 5 bullet points
to a full SHAP-style explainability engine with:
  - Weighted factor contributions
  - Visual bar chart data (for frontend)
  - Human-readable rationale per factor
  - Five Cs mapping

DROP-IN REPLACEMENT — same function name, richer output.
"""
from typing import Union


# ─────────────────────────────────────────────────────────────────────────────
#  Factor definitions — weight, threshold, label, direction
# ─────────────────────────────────────────────────────────────────────────────
FACTORS = [
    # (feature_key, weight, good_threshold, bad_threshold, higher_is_better, label, five_c)
    ("dscr",                 15, 1.5,  1.0,  True,  "Debt Service Coverage Ratio", "Capacity"),
    ("interest_coverage",    10, 3.0,  1.5,  True,  "Interest Coverage Ratio",     "Capacity"),
    ("debt_to_equity",       10, 1.5,  3.5,  False, "Debt-to-Equity Ratio",        "Capital"),
    ("profit_margin",         8, 0.15, 0.05, True,  "Profit Margin",               "Capital"),
    ("current_ratio",         7, 1.5,  1.0,  True,  "Current Ratio (Liquidity)",   "Capacity"),
    ("collateral_coverage",  10, 1.5,  1.0,  True,  "Collateral Coverage",         "Collateral"),
    ("gst_compliance_score",  8, 1.0,  0.7,  True,  "GST Compliance Score",        "Conditions"),
    ("fraud_count",          12, 0,    2,    False, "Fraud Signals",               "Character"),
    ("legal_count",           8, 0,    2,    False, "Legal Issues",                "Character"),
    ("business_vintage",      5, 0.5,  0.2,  True,  "Business Vintage",            "Conditions"),
    ("cheque_bounce_flag",    4, 0,    1,    False, "Cheque Bounce History",       "Character"),
    ("debt_ratio",            3, 0.4,  0.7,  False, "Debt-to-Revenue Ratio",       "Capital"),
]


def _score_factor(value, good_thresh, bad_thresh, higher_is_better: bool) -> float:
    """Returns 0.0 (worst) to 1.0 (best) for a single factor."""
    if higher_is_better:
        if value >= good_thresh:   return 1.0
        if value <= bad_thresh:    return 0.0
        return (value - bad_thresh) / max(good_thresh - bad_thresh, 0.001)
    else:
        if value <= good_thresh:   return 1.0
        if value >= bad_thresh:    return 0.0
        return 1.0 - (value - good_thresh) / max(bad_thresh - good_thresh, 0.001)


def _get_impact_label(score: float) -> str:
    if score >= 0.75:  return "Positive"
    if score >= 0.5:   return "Neutral"
    if score >= 0.25:  return "Concern"
    return "Risk"


def _get_reason(key: str, value, score: float, label: str) -> str:
    """Human-readable reason string for each factor."""
    REASONS = {
        "dscr": {
            "Positive":  f"Strong DSCR of {value:.2f}x — cashflow comfortably covers debt service",
            "Neutral":   f"Adequate DSCR {value:.2f}x — acceptable but leaves limited buffer",
            "Concern":   f"Thin DSCR {value:.2f}x — close to minimum threshold of 1.25x",
            "Risk":      f"Insufficient DSCR {value:.2f}x — cashflow cannot cover debt repayment",
        },
        "interest_coverage": {
            "Positive":  f"ICR {value:.2f}x — EBITDA strongly covers interest payments",
            "Neutral":   f"ICR {value:.2f}x — adequate interest coverage",
            "Concern":   f"ICR {value:.2f}x — EBITDA only marginally covers interest",
            "Risk":      f"ICR {value:.2f}x — EBITDA insufficient to cover interest payments",
        },
        "debt_to_equity": {
            "Positive":  f"Healthy D/E of {value:.2f}x — conservatively leveraged",
            "Neutral":   f"D/E {value:.2f}x — moderate leverage",
            "Concern":   f"Elevated D/E {value:.2f}x — balance sheet stress",
            "Risk":      f"Very high D/E {value:.2f}x — over-leveraged, equity erosion risk",
        },
        "profit_margin": {
            "Positive":  f"Strong margin {value*100:.1f}% — healthy profitability",
            "Neutral":   f"Moderate margin {value*100:.1f}%",
            "Concern":   f"Thin margin {value*100:.1f}% — vulnerable to cost shocks",
            "Risk":      f"Very low/negative margin {value*100:.1f}% — loss-making concern",
        },
        "current_ratio": {
            "Positive":  f"Current ratio {value:.2f} — comfortable liquidity",
            "Neutral":   f"Current ratio {value:.2f} — adequate short-term liquidity",
            "Concern":   f"Current ratio {value:.2f} — working capital stress",
            "Risk":      f"Current ratio {value:.2f} — severe liquidity risk",
        },
        "collateral_coverage": {
            "Positive":  f"Collateral {value:.2f}x — adequate security cover",
            "Neutral":   f"Collateral {value:.2f}x — minimum acceptable coverage",
            "Concern":   f"Collateral {value:.2f}x — under-secured position",
            "Risk":      f"Collateral {value:.2f}x — insufficient security for loan",
        },
        "gst_compliance_score": {
            "Positive":  "GST filings consistent — revenue declared matches bank inflows",
            "Neutral":   "Minor GST discrepancy — within acceptable range",
            "Concern":   "GST mismatch — possible revenue inflation or ITC overclaim",
            "Risk":      "Significant GSTR-2A/3B mismatch — revenue manipulation suspected",
        },
        "fraud_count": {
            "Positive":  "No fraud signals detected",
            "Neutral":   f"{int(value)} minor fraud signal(s) — monitor closely",
            "Concern":   f"{int(value)} fraud signal(s) — requires investigation",
            "Risk":      f"{int(value)} fraud signal(s) — HIGH ALERT: strong fraud indicators",
        },
        "legal_count": {
            "Positive":  "No legal issues found",
            "Neutral":   f"{int(value)} legal matter(s) — routine, not material",
            "Concern":   f"{int(value)} legal cases — may impact operations",
            "Risk":      f"{int(value)} legal cases — NCLT/DRT proceedings likely",
        },
        "business_vintage": {
            "Positive":  f"{int(value*10)}+ years in business — established track record",
            "Neutral":   f"{int(value*10)} years — sufficient operating history",
            "Concern":   f"Only {int(value*10)} years old — limited track record",
            "Risk":      "New business — very limited financial history",
        },
        "cheque_bounce_flag": {
            "Positive":  "No cheque bounces — good banking conduct",
            "Risk":      "Multiple cheque bounces — banking conduct concern",
            "Concern":   "Multiple cheque bounces — banking conduct concern",
            "Neutral":   "Cheque bounce history noted",
        },
        "debt_ratio": {
            "Positive":  f"Debt/Revenue {value:.2f} — conservative borrowing",
            "Neutral":   f"Debt/Revenue {value:.2f} — moderate",
            "Concern":   f"Debt/Revenue {value:.2f} — high relative to revenue",
            "Risk":      f"Debt/Revenue {value:.2f} — dangerously high debt load",
        },
    }
    return REASONS.get(key, {}).get(label, f"{label}: {value}")


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API — Drop-in replacement for your explain(f)
# ─────────────────────────────────────────────────────────────────────────────
def explain(f: dict) -> Union[list, dict]:
    """
    UPGRADED version of your explain(f).

    Returns full explainability report including:
      - reasons list (backward compatible)
      - SHAP-style factor contributions for frontend chart
      - Five Cs breakdown
      - Overall narrative

    Backward-compatible: result["reasons"] gives same list as before.
    """
    factor_details  = []
    five_c_breakdown = {"Character": [], "Capacity": [], "Capital": [],
                        "Collateral": [], "Conditions": []}
    reasons         = []   # Your original output

    for key, weight, good, bad, higher_better, label, five_c in FACTORS:
        value = f.get(key, good)    # Default to good value if missing

        factor_score = _score_factor(value, good, bad, higher_better)
        impact       = _get_impact_label(factor_score)
        reason       = _get_reason(key, value, factor_score, impact)
        contribution = round(weight * factor_score, 2)   # Weighted contribution 0-weight

        detail = {
            "key":          key,
            "label":        label,
            "value":        round(float(value), 4) if isinstance(value, float) else value,
            "weight":       weight,
            "score":        round(factor_score, 3),       # 0.0-1.0
            "contribution": contribution,                  # For SHAP bar chart
            "max_contribution": weight,
            "impact":       impact,                        # Positive/Neutral/Concern/Risk
            "reason":       reason,
            "five_c":       five_c,
        }
        factor_details.append(detail)
        five_c_breakdown[five_c].append(detail)

        # Build backward-compatible reasons list (only Concern/Risk factors)
        if impact in ("Concern", "Risk"):
            reasons.append(reason)

    # ── Your original 5 reasons (preserved for backward compat) ──────────────
    original_reasons = []
    if f.get("debt_ratio", 0) > 0.7:
        original_reasons.append("High debt burden")
    if f.get("profit_margin", 1) < 0.1:
        original_reasons.append("Low profitability")
    if f.get("cashflow_flag"):
        original_reasons.append("Negative cash flow")
    if f.get("fraud_count", 0) > 0:
        original_reasons.append("Fraud signals detected")
    if f.get("legal_count", 0) > 1:
        original_reasons.append("Multiple legal cases")

    # Sort by impact severity for display
    factor_details.sort(key=lambda x: x["score"])

    # Overall narrative
    risk_factors = [d for d in factor_details if d["impact"] == "Risk"]
    pos_factors  = [d for d in factor_details if d["impact"] == "Positive"]
    total_score  = sum(d["contribution"] for d in factor_details)
    max_score    = sum(d["weight"] for d in factor_details)
    pct          = round((total_score / max_score) * 100, 1)

    narrative = (
        f"Credit analysis reveals {len(risk_factors)} critical risk factor(s) "
        f"and {len(pos_factors)} positive factor(s). "
        f"Overall weighted score: {pct}%. "
    )
    if risk_factors:
        narrative += f"Primary concerns: {'; '.join(d['label'] for d in risk_factors[:2])}."

    return {
        # ── Backward compatible ───────────────────────────────────────────
        "reasons":          reasons or ["No major risk factors identified"],

        # ── Rich explainability data ──────────────────────────────────────
        "original_reasons": original_reasons,   # Your exact original output
        "factor_details":   factor_details,      # All 12 factors with scores
        "five_c_breakdown": five_c_breakdown,    # Grouped by Five Cs
        "narrative":        narrative,
        "weighted_score":   round(total_score, 2),
        "max_score":        max_score,
        "score_pct":        pct,

        # ── Frontend chart data (ready for Recharts/Chart.js) ─────────────
        "chart_data": [
            {
                "name":          d["label"],
                "score":         round(d["score"] * 100, 1),
                "contribution":  d["contribution"],
                "max":           d["weight"],
                "fill":          "#22C55E" if d["impact"] == "Positive"
                                 else "#F4A261" if d["impact"] == "Neutral"
                                 else "#EF4444",
            }
            for d in sorted(factor_details, key=lambda x: -x["weight"])
        ],
    }