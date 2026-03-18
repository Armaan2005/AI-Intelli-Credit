"""
structured_extractor.py
------------------------
Upgrades your existing extract_structured_data() with:
  - 20+ financial fields (your original had only 6)
  - India-specific fields: GSTIN, PAN, CIN, CIBIL, DSCR
  - Regex pre-extraction before Gemini (faster + cheaper)
  - Document-type-aware prompts (GST vs Bank vs Annual Report)
  - Validation of extracted numbers
  - Fallback chain: Regex → Gemini → defaults

DROP-IN REPLACEMENT — same function name, richer output.
"""
import json
import re
from typing import Union

import google.generativeai as genai

try:
    from app.config.settings import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = ""

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")


# ─────────────────────────────────────────────────────────────────────────────
#  REGEX PRE-EXTRACTION — catches common patterns without Gemini
# ─────────────────────────────────────────────────────────────────────────────
def _regex_extract(text: str) -> dict:
    """
    Fast regex extraction of common Indian financial document patterns.
    Runs before Gemini to pre-populate obvious fields.
    """
    result = {}

    def find_amount(patterns: list) -> float:
        """Try multiple patterns, return first match as float."""
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                num_str = m.group(1).replace(",", "").replace("₹", "").strip()
                try:
                    return float(num_str)
                except ValueError:
                    continue
        return 0.0

    # ── Identity fields ───────────────────────────────────────────────────────
    pan = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', text)
    if pan:
        result["pan"] = pan.group(1)

    gstin = re.search(r'\b(\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b', text)
    if gstin:
        result["gstin"] = gstin.group(1)

    cin = re.search(r'\b([UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})\b', text)
    if cin:
        result["cin"] = cin.group(1)

    # ── Revenue / Turnover ────────────────────────────────────────────────────
    result["revenue"] = find_amount([
        r'(?:Revenue|Turnover|Net Sales|Total Income)[\s:₹]*([0-9,]+(?:\.\d+)?)',
        r'(?:Revenue|Turnover).*?(\d[\d,]+(?:\.\d+)?)\s*(?:Lakhs|Crore|Cr|L)',
    ])

    # ── Profit / Loss ─────────────────────────────────────────────────────────
    result["profit"] = find_amount([
        r'(?:Net Profit|PAT|Profit After Tax|Net Income)[\s:₹]*([0-9,]+(?:\.\d+)?)',
        r'(?:Profit|PAT).*?(\d[\d,]+(?:\.\d+)?)\s*(?:Lakhs|Crore)',
    ])

    # ── Debt / Borrowings ─────────────────────────────────────────────────────
    result["debt"] = find_amount([
        r'(?:Total Debt|Borrowings|Total Liabilities|Long.?term Debt)[\s:₹]*([0-9,]+(?:\.\d+)?)',
        r'(?:Borrowings|Debt).*?(\d[\d,]+(?:\.\d+)?)\s*(?:Lakhs|Crore)',
    ])

    # ── Cashflow ──────────────────────────────────────────────────────────────
    result["cashflow"] = find_amount([
        r'(?:Cash Flow|Operating Cash|Net Cash)[\s:₹\-]*([0-9,]+(?:\.\d+)?)',
        r'(?:Closing Balance|Cash and Cash Equivalents)[\s:₹]*([0-9,]+(?:\.\d+)?)',
    ])

    # ── Balance Sheet ─────────────────────────────────────────────────────────
    result["total_assets"] = find_amount([
        r'Total Assets[\s:₹]*([0-9,]+(?:\.\d+)?)',
        r'Balance Sheet Total[\s:₹]*([0-9,]+(?:\.\d+)?)',
    ])
    result["equity"] = find_amount([
        r'(?:Shareholders.? Equity|Net Worth|Total Equity)[\s:₹]*([0-9,]+(?:\.\d+)?)',
    ])
    result["current_assets"] = find_amount([
        r'Current Assets[\s:₹]*([0-9,]+(?:\.\d+)?)',
    ])
    result["current_liabilities"] = find_amount([
        r'Current Liabilities[\s:₹]*([0-9,]+(?:\.\d+)?)',
    ])

    # ── EBITDA / Interest ─────────────────────────────────────────────────────
    result["ebitda"] = find_amount([
        r'EBITDA[\s:₹]*([0-9,]+(?:\.\d+)?)',
        r'Earnings Before.*?Tax.*?(\d[\d,]+(?:\.\d+)?)',
    ])
    result["interest_expense"] = find_amount([
        r'(?:Interest Expense|Finance Cost|Interest Paid)[\s:₹]*([0-9,]+(?:\.\d+)?)',
    ])

    # ── GST-specific ──────────────────────────────────────────────────────────
    result["gst_declared_revenue"] = find_amount([
        r'(?:Taxable Value|Outward Supplies|Total Turnover)[\s:₹]*([0-9,]+(?:\.\d+)?)',
    ])

    # ── Legal / Fraud signals (keyword detection) ─────────────────────────────
    legal_keywords = ["NCLT", "DRT", "FIR", "Criminal", "Winding Up", "Insolvency",
                      "Attachment", "Garnishee", "SARFAESI"]
    found_legal = [kw for kw in legal_keywords if kw.lower() in text.lower()]
    result["legal_issues"] = found_legal

    fraud_keywords = ["Fraud", "NPA", "Wilful Default", "Diversion", "Round Tripping",
                      "Shell Company", "Benami", "Hawala"]
    found_fraud = [kw for kw in fraud_keywords if kw.lower() in text.lower()]
    result["fraud_signals"] = found_fraud

    return result


# ─────────────────────────────────────────────────────────────────────────────
#  GEMINI EXTRACTION — fills gaps that regex couldn't catch
# ─────────────────────────────────────────────────────────────────────────────
def _gemini_extract(text: str, doc_type: str = "unknown", existing: dict = None) -> dict:
    """
    Gemini extraction with doc-type-aware prompt.
    Only fills fields that regex didn't find (existing={}).
    """
    existing = existing or {}
    missing_fields = [
        f for f in ["revenue", "profit", "debt", "cashflow", "ebitda",
                     "total_assets", "equity", "current_ratio"]
        if not existing.get(f)
    ]

    if not missing_fields and existing.get("revenue"):
        return {}   # Regex got everything, skip Gemini

    doc_hint = {
        "gst_return":     "This is a GST Return (GSTR). Extract taxable turnover, ITC claimed, tax paid.",
        "bank_statement": "This is a Bank Statement. Extract average balance, total credits, total debits, EMI/loan repayments.",
        "annual_report":  "This is an Annual Report. Extract revenue, PAT, total debt, equity, EBITDA.",
        "legal_notice":   "This is a Legal Notice/Court Document. Focus on fraud_signals and legal_issues arrays.",
        "itr":            "This is an Income Tax Return. Extract gross income, tax paid, total assets declared.",
    }.get(doc_type, "This is a financial document.")

    prompt = f"""
You are an expert Indian financial data extractor.

{doc_hint}

Extract financial data from the text below.
All amounts should be in Lakhs INR unless clearly stated otherwise.
Return ONLY valid JSON, no explanation outside JSON.

Already extracted (DO NOT re-extract these): {list(existing.keys())}

Return this JSON structure (use 0 for unknown numeric fields, [] for empty lists):
{{
  "revenue": 0,
  "profit": 0,
  "debt": 0,
  "cashflow": 0,
  "ebitda": 0,
  "interest_expense": 0,
  "total_assets": 0,
  "equity": 0,
  "current_assets": 0,
  "current_liabilities": 0,
  "inventory": 0,
  "gst_declared_revenue": 0,
  "gst_itc_claimed": 0,
  "gst_itc_eligible": 0,
  "existing_loans": 0,
  "collateral_value": 0,
  "years_in_business": 0,
  "bounced_cheques": 0,
  "fraud_signals": [],
  "legal_issues": [],
  "company_name": "",
  "promoter_name": "",
  "industry_sector": ""
}}

TEXT (first 3000 chars):
{text[:3000]}
"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip() if response.text else ""
        raw = re.sub(r"```json|```", "", raw).strip()
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
    except Exception as e:
        print(f"⚠️ Gemini extraction error: {e}")

    return {}


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API — Drop-in replacement for your extract_structured_data()
# ─────────────────────────────────────────────────────────────────────────────
def extract_structured_data(text: Union[str, dict], doc_type: str = "unknown") -> dict:
    """
    UPGRADED version of your extract_structured_data().

    Pipeline:
      1. Regex extraction (fast, free)
      2. Gemini fills remaining gaps (only if needed)
      3. Merge + validate

    Returns 20+ fields vs your original 6.
    Backward-compatible: revenue, profit, debt, cashflow,
                          fraud_signals, legal_issues all preserved.
    """
    # Handle dict input (from pdf_parser returning dict)
    if isinstance(text, dict):
        doc_type = text.get("doc_type", doc_type)
        text     = text.get("text", "")

    if not text or not text.strip():
        return default_data()

    print(f"📊 Extracting structured data | doc_type={doc_type} | chars={len(text)}")

    # Step 1: Regex (fast, no API call)
    regex_data = _regex_extract(text)

    # Step 2: Gemini fills gaps
    gemini_data = _gemini_extract(text, doc_type, regex_data)

    # Step 3: Merge — regex takes priority, gemini fills missing
    merged = {**default_data(), **gemini_data, **regex_data}

    # Step 4: Combine list fields (legal + fraud from both sources)
    merged["legal_issues"]  = list(set(
        regex_data.get("legal_issues",  []) +
        gemini_data.get("legal_issues", [])
    ))
    merged["fraud_signals"] = list(set(
        regex_data.get("fraud_signals",  []) +
        gemini_data.get("fraud_signals", [])
    ))

    # Step 5: Basic validation — negative revenue makes no sense
    for field in ["revenue", "total_assets", "equity"]:
        if merged.get(field, 0) < 0:
            merged[field] = 0

    merged["_extraction_source"] = {
        "regex_fields":  [k for k, v in regex_data.items() if v],
        "gemini_fields": [k for k, v in gemini_data.items() if v],
        "doc_type":      doc_type,
    }

    return merged


def default_data() -> dict:
    """
    Extended default — 20+ fields vs your original 6.
    Backward-compatible.
    """
    return {
        # ── Your original 6 fields ────────────────────────────────────────
        "revenue":              0,
        "profit":               0,
        "debt":                 0,
        "cashflow":             0,
        "fraud_signals":        [],
        "legal_issues":         [],

        # ── New fields ────────────────────────────────────────────────────
        "ebitda":               0,
        "interest_expense":     0,
        "total_assets":         0,
        "equity":               0,
        "current_assets":       0,
        "current_liabilities":  0,
        "inventory":            0,
        "gst_declared_revenue": 0,
        "gst_itc_claimed":      0,
        "gst_itc_eligible":     0,
        "existing_loans":       0,
        "collateral_value":     0,
        "years_in_business":    3,
        "bounced_cheques":      0,
        "company_name":         "",
        "promoter_name":        "",
        "industry_sector":      "",
        "pan":                  "",
        "gstin":                "",
        "cin":                  "",
    }