"""
research_agent.py
-----------------
Upgrades your existing research_company() from a single Gemini prompt
to a multi-source research pipeline:

  1. Web search  — DuckDuckGo news (no API key needed)
  2. MCA check   — Ministry of Corporate Affairs signals
  3. Gemini AI   — Deep analysis of all gathered data
  4. Sector risk — India-specific sector headwind detection

DROP-IN REPLACEMENT — same function name, much richer output.
"""
import json
import re
import time
from typing import Optional

import google.generativeai as genai

# ── Your existing setup (kept as-is) ─────────────────────────────────────────
try:
    from app.config.settings import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = ""

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER: Clean Gemini JSON output (fixes your existing regex bug)
# ─────────────────────────────────────────────────────────────────────────────
def _clean_json(text: str) -> dict:
    """
    Fixed version of your clean_json() from decision_agent.py.
    Your original used .replace(r"```json|```") which doesn't work —
    replace() treats the argument as a literal string, not regex.
    """
    text = re.sub(r"```json|```", "", text).strip()
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > start:
        text = text[start:end]
    try:
        return json.loads(text)
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────────────────────
#  SOURCE 1: Web News Search (DuckDuckGo — no API key needed)
# ─────────────────────────────────────────────────────────────────────────────
def _search_news(company_name: str, promoter_name: str = "") -> list[dict]:
    """
    Search real news about the company and promoters.
    Uses DuckDuckGo instant search — works without any API key.
    """
    try:
        from duckduckgo_search import DDGS
        results = []
        queries = [
            f"{company_name} fraud scam NPA India",
            f"{company_name} NCLT insolvency court case",
            f"{company_name} RBI default wilful",
        ]
        if promoter_name:
            queries.append(f"{promoter_name} fraud criminal case India")

        with DDGS() as ddgs:
            for query in queries[:3]:   # limit to 3 searches
                try:
                    hits = list(ddgs.text(query, max_results=3))
                    for h in hits:
                        results.append({
                            "title":   h.get("title", ""),
                            "snippet": h.get("body", ""),
                            "url":     h.get("href", ""),
                            "query":   query,
                        })
                    time.sleep(0.5)     # be polite to DDG
                except Exception:
                    continue
        return results

    except ImportError:
        # duckduckgo_search not installed — graceful fallback
        return []
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
#  SOURCE 2: MCA21 Signal Detection
# ─────────────────────────────────────────────────────────────────────────────
def _check_mca_signals(data: dict) -> dict:
    """
    Checks MCA-related signals from the input data.
    In production: integrate with mca.gov.in API.
    For hackathon: uses structured heuristics on available data.
    """
    signals = []
    risk    = "Low"

    directors     = data.get("directors", [])
    disqualified  = data.get("disqualified_directors", [])
    charges       = data.get("charges_created", 0)
    charges_sat   = data.get("charges_satisfied", 0)
    company_age   = data.get("years_in_business", 5)
    filings_late  = data.get("late_filings_count", 0)

    if disqualified:
        signals.append(f"Disqualified director(s) found: {disqualified}")
        risk = "High"

    if charges > 0 and charges_sat < charges:
        pending = charges - charges_sat
        signals.append(f"{pending} unsatisfied charge(s) on MCA — possible encumbrance")
        risk = "High" if pending > 2 else "Medium"

    if filings_late > 3:
        signals.append(f"{filings_late} late ROC filings — compliance concern")
        risk = max(risk, "Medium", key=lambda x: ["Low","Medium","High"].index(x))

    if company_age < 2:
        signals.append("Company incorporated < 2 years ago — limited track record")

    return {
        "mca_risk":   risk,
        "mca_signals": signals,
        "directors_count": len(directors),
        "pending_charges": max(0, charges - charges_sat),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  SOURCE 3: India Sector Risk Detection
# ─────────────────────────────────────────────────────────────────────────────
SECTOR_RISK_MAP = {
    # High risk sectors (RBI watch-list / stressed)
    "real estate":    ("High",   "Sector under RBI stress — high NPA history"),
    "construction":   ("High",   "High working capital stress, delayed payments"),
    "textile":        ("Medium", "Export volatility, competition from Bangladesh/Vietnam"),
    "edtech":         ("High",   "Post-COVID consolidation, funding winter"),
    "crypto":         ("High",   "RBI regulatory uncertainty, VASP framework pending"),
    "nbfc":           ("Medium", "RBI tightening norms — higher provisioning required"),
    "aviation":       ("High",   "Fuel cost volatility, thin margins"),
    "steel":          ("Medium", "China dumping risk, cyclical commodity"),
    "pharma":         ("Low",    "Defensive sector, stable demand"),
    "it":             ("Low",    "Stable exports, strong margin profile"),
    "fmcg":           ("Low",    "Resilient domestic demand"),
    "renewable energy":("Medium","Policy risk, long gestation, but growing"),
}

def _get_sector_risk(sector: str) -> dict:
    sector_lower = (sector or "").lower()
    for key, (risk, note) in SECTOR_RISK_MAP.items():
        if key in sector_lower:
            return {"sector_risk": risk, "sector_note": note}
    return {"sector_risk": "Medium", "sector_note": "Sector-specific risk not assessed"}


# ─────────────────────────────────────────────────────────────────────────────
#  SOURCE 4: Gemini Deep Analysis (your existing approach — upgraded prompt)
# ─────────────────────────────────────────────────────────────────────────────
def _gemini_analysis(data: dict, news_results: list, mca: dict) -> dict:
    """
    Upgraded Gemini prompt — feeds it real news + MCA data for better analysis.
    """
    news_text = "\n".join([
        f"- [{r['title']}]: {r['snippet'][:200]}"
        for r in news_results[:6]
    ]) or "No news found."

    mca_text = json.dumps(mca, indent=2)

    prompt = f"""
You are a senior Indian credit analyst with 20 years of experience in corporate lending.

Analyze the following company for credit risk. Be specific, factual, and concise.

## Company Data:
{json.dumps(data, indent=2)}

## Recent News (web search results):
{news_text}

## MCA / ROC Signals:
{mca_text}

## Your Task:
Assess the company across these 4 dimensions and return ONLY valid JSON.

Return this exact JSON structure (no text outside JSON):
{{
  "fraud_risk": "Low | Medium | High",
  "legal_risk": "Low | Medium | High",
  "reputation": "Good | Neutral | Poor",
  "sector_risk": "Low | Medium | High",
  "wilful_defaulter": false,
  "red_flags": [
    "specific flag 1 with evidence",
    "specific flag 2 with evidence"
  ],
  "promoter_assessment": "1-2 sentence assessment of promoter background",
  "key_concerns": "Top 2-3 concerns a credit committee should know",
  "positive_factors": "Any genuine positives found",
  "overall_risk_summary": "2-3 sentence executive summary"
}}

RULES:
- Base findings on actual data provided, not assumptions
- If news contains fraud/NPA/NCLT mentions, flag as High risk
- wilful_defaulter: true only if explicitly found in data/news
- red_flags must be specific, not generic (e.g. "NCLT case filed 2023-Q3" not just "legal issues")
"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip() if response.text else ""
        result = _clean_json(raw)

        # Validate required fields exist
        required = ["fraud_risk", "legal_risk", "reputation", "red_flags"]
        if all(k in result for k in required):
            return result
    except Exception as e:
        print(f"⚠️ Gemini analysis error: {e}")

    # Fallback
    return {
        "fraud_risk":          "Unknown",
        "legal_risk":          "Unknown",
        "reputation":          "Unknown",
        "sector_risk":         "Medium",
        "wilful_defaulter":    False,
        "red_flags":           [],
        "promoter_assessment": "Unable to assess",
        "key_concerns":        "Manual review required",
        "positive_factors":    "N/A",
        "overall_risk_summary":"Automated analysis failed — manual due diligence required",
    }


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API — Drop-in replacement for your research_company()
# ─────────────────────────────────────────────────────────────────────────────
def research_company(data: dict, company_name: str = "", promoter_name: str = "") -> dict:
    """
    UPGRADED version of your research_company().

    Now runs a 4-source pipeline:
      1. Web news search   (DuckDuckGo)
      2. MCA signal check  (structured heuristics)
      3. Sector risk map   (India-specific)
      4. Gemini deep analysis (with real context)

    Returns same keys as before PLUS rich additional data.
    Backward-compatible: fraud_risk, legal_risk, reputation, red_flags all preserved.
    """
    # Extract company/promoter name from data if not passed directly
    if not company_name:
        company_name = (
            data.get("company_name") or
            data.get("name") or
            "Unknown Company"
        )
    if not promoter_name:
        promoter_name = data.get("promoter_name", "")

    sector = data.get("industry_sector", data.get("sector", ""))

    print(f"🔍 Researching: {company_name} | Sector: {sector}")

    # ── Run all 4 sources ────────────────────────────────────────────────────
    print("  [1/4] Web news search...")
    news_results = _search_news(company_name, promoter_name)

    print("  [2/4] MCA signal check...")
    mca_signals  = _check_mca_signals(data)

    print("  [3/4] Sector risk assessment...")
    sector_risk  = _get_sector_risk(sector)

    print("  [4/4] Gemini deep analysis...")
    gemini_result = _gemini_analysis(data, news_results, mca_signals)

    # ── Merge all results ────────────────────────────────────────────────────
    # Combine red flags from all sources
    all_red_flags = list(gemini_result.get("red_flags", []))
    all_red_flags += mca_signals.get("mca_signals", [])
    if sector_risk["sector_risk"] == "High":
        all_red_flags.append(f"⚠️ Sector alert: {sector_risk['sector_note']}")

    # Aggregate risk level (worst-case wins)
    def _max_risk(*risks):
        order = {"Low": 0, "Medium": 1, "High": 2, "Unknown": 1}
        return max(risks, key=lambda r: order.get(r, 1))

    final_fraud_risk = _max_risk(
        gemini_result.get("fraud_risk", "Unknown"),
        "High" if mca_signals.get("pending_charges", 0) > 2 else "Low",
    )
    final_legal_risk = _max_risk(
        gemini_result.get("legal_risk", "Unknown"),
        mca_signals.get("mca_risk", "Low"),
    )

    return {
        # ── Original fields (backward compatible) ──────────────────────────
        "fraud_risk":  final_fraud_risk,
        "legal_risk":  final_legal_risk,
        "reputation":  gemini_result.get("reputation", "Unknown"),
        "red_flags":   all_red_flags,

        # ── New rich fields ────────────────────────────────────────────────
        "sector_risk":         sector_risk["sector_risk"],
        "sector_note":         sector_risk["sector_note"],
        "wilful_defaulter":    gemini_result.get("wilful_defaulter", False),
        "mca_risk":            mca_signals.get("mca_risk", "Low"),
        "mca_signals":         mca_signals.get("mca_signals", []),
        "promoter_assessment": gemini_result.get("promoter_assessment", ""),
        "key_concerns":        gemini_result.get("key_concerns", ""),
        "positive_factors":    gemini_result.get("positive_factors", ""),
        "overall_risk_summary":gemini_result.get("overall_risk_summary", ""),

        # ── Source metadata (for CAM report citations) ─────────────────────
        "sources": {
            "news_articles_found": len(news_results),
            "news_headlines":      [r["title"] for r in news_results[:5]],
            "mca_checked":         True,
            "gemini_model":        "gemini-2.5-flash",
        },
    }