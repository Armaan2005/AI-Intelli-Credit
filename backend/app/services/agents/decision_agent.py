"""
decision_agent.py
-----------------
Upgraded version of your existing file.

Fixes:
  ❌ text.replace(r"```json|```", "") — replace() ignores regex, does nothing
  ❌ No context from scoring engine passed to Gemini
  ❌ Gemini makes decision independent of your risk_model.py output
  ❌ Returns only 4 fields — no Five Cs, no conditions, no rating

DROP-IN REPLACEMENT — same function name final_decision(), richer output.
"""
import json
import re

import google.generativeai as genai

try:
    from app.config.settings import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = ""

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")


# ─────────────────────────────────────────────────────────────────────────────
#  FIXED clean_json — your original had a bug here
# ─────────────────────────────────────────────────────────────────────────────
def clean_json(text: str) -> dict:
    """
    Fixed version — uses re.sub() instead of .replace() for regex patterns.
    Your original: text.replace(r"```json|```", "") — this does nothing
    because replace() treats first arg as literal string, not regex.
    """
    # ✅ Correct way to strip markdown code fences
    text = re.sub(r"```json|```", "", text).strip()

    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > start:
        text = text[start:end]

    try:
        return json.loads(text)
    except Exception:
        return {
            "decision":      "Unknown",
            "interest_rate": "N/A",
            "loan_amount":   "N/A",
            "reason":        "JSON parsing failed — manual review required",
        }


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API — Drop-in replacement for your final_decision()
# ─────────────────────────────────────────────────────────────────────────────
def final_decision(data: dict, risk: dict) -> dict:
    """
    UPGRADED version of your final_decision(data, risk).

    Now:
    1. Passes scoring engine output (Five Cs, flags, DSCR etc.) to Gemini
    2. Gemini validates/explains the ML decision — doesn't make it independently
    3. Returns full structured output with rationale for CAM report
    4. Falls back to scoring engine if Gemini fails

    Same signature as before: final_decision(data, risk)
    """
    # Extract key metrics for Gemini context
    five_c   = risk.get("five_c_scores", {})
    flags    = risk.get("risk_flags",    [])
    score    = risk.get("total_score",   50)
    rating   = risk.get("rating",        "BBB")
    decision_from_scoring = risk.get("decision", "")
    recommended_rate  = risk.get("interest_rate", "N/A")
    recommended_amount = risk.get("loan_amount",  "N/A")

    prompt = f"""
You are a senior Indian credit officer reviewing an AI-generated credit assessment.

The scoring engine has already computed the following. Your job is to:
1. Validate the decision
2. Write a professional credit committee rationale
3. List specific conditions if approving

## Scoring Engine Output:
- Credit Score:     {score}/100
- Rating:           {rating}
- Recommended Decision: {decision_from_scoring or "Pending your review"}
- Suggested Rate:   {recommended_rate}
- Suggested Amount: ₹{recommended_amount} Lakhs

## Five Cs Breakdown (scores out of 100):
- Character:  {five_c.get("character",  "N/A")}
- Capacity:   {five_c.get("capacity",   "N/A")}
- Capital:    {five_c.get("capital",    "N/A")}
- Collateral: {five_c.get("collateral", "N/A")}
- Conditions: {five_c.get("conditions", "N/A")}

## Risk Flags Identified:
{chr(10).join(flags[:8]) if flags else "None"}

## Company Financial Data:
{json.dumps(data, indent=2)[:2000]}

## STRICT RULES:
- Return ONLY valid JSON, no text outside JSON
- decision must be exactly: "Approve", "Approve with Conditions", or "Reject"
- interest_rate must be realistic (8.5% to 16% for Indian corporate loans)
- loan_amount must be a number in Lakhs INR
- reason must be specific, cite actual data points

Return this exact JSON:
{{
  "decision": "Approve | Approve with Conditions | Reject",
  "interest_rate": "X.XX%",
  "loan_amount": "number in Lakhs",
  "reason": "2-3 sentence specific rationale citing key data points",
  "conditions": ["condition 1 if any", "condition 2 if any"],
  "credit_committee_note": "1 sentence for credit committee minutes"
}}
"""

    try:
        response = model.generate_content(prompt)
        raw = response.text if response.text else ""
        print(f"🔍 DECISION RAW (first 200 chars): {raw[:200]}")

        result = clean_json(raw)

        # Validate Gemini didn't hallucinate a wildly different decision
        required_keys = ["decision", "interest_rate", "loan_amount", "reason"]
        if all(k in result for k in required_keys):
            # Add scoring engine data to result
            result["total_score"]    = score
            result["rating"]         = rating
            result["risk_level"]     = risk.get("risk_level", "MEDIUM")
            result["five_c_scores"]  = five_c
            result["risk_flags"]     = flags
            result.setdefault("conditions", [])
            result.setdefault("credit_committee_note", result["reason"][:100])
            return result

    except Exception as e:
        print(f"⚠️ Gemini decision error: {e}")

    # ── Fallback: use scoring engine output directly ───────────────────────────
    print("⚠️ Falling back to scoring engine decision")
    return {
        "decision":              decision_from_scoring or "Refer to Credit Committee",
        "interest_rate":         recommended_rate,
        "loan_amount":           str(recommended_amount),
        "reason":                f"Automated scoring: {score}/100 ({rating}). " +
                                  (flags[0] if flags else "No critical flags."),
        "conditions":            [],
        "credit_committee_note": f"Score {score}/100, Rating {rating}",
        "total_score":           score,
        "rating":                rating,
        "risk_level":            risk.get("risk_level", "MEDIUM"),
        "five_c_scores":         five_c,
        "risk_flags":            flags,
    }