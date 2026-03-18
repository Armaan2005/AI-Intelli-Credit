import json
import google.generativeai as genai
from app.config.settings import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")


def extract_structured_data(text):

    prompt = f"""
    Extract financial data and RETURN ONLY JSON:

    {{
      "revenue": number,
      "profit": number,
      "debt": number,
      "cashflow": number,
      "fraud_signals": [],
      "legal_issues": []
    }}

    TEXT:
    {text[:3000]}
    """

    response = model.generate_content(prompt)

    # 🔥 SAFE RAW EXTRACTION
    raw = ""
    if hasattr(response, "text") and response.text:
        raw = response.text.strip()
    else:
        raw = response

    print("🔍 GEMINI RAW:", raw)

    # ✅ CASE 1: already dict
    if isinstance(raw, dict):
        return raw

    # ✅ CASE 2: empty response
    if not raw:
        return default_data()

    # ✅ CASE 3: string → parse JSON
    try:
        return json.loads(raw)
    except:
        print("⚠️ JSON parse failed, using fallback")
        return default_data()


def default_data():
    return {
        "revenue": 0,
        "profit": 0,
        "debt": 0,
        "cashflow": 0,
        "fraud_signals": [],
        "legal_issues": []
    }