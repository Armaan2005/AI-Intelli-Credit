import google.generativeai as genai
from app.config.settings import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")


def research_company(data):
    prompt = f"""
    You are a financial investigator.

    Analyze this company data and find:

    1. Fraud risks
    2. Legal issues
    3. Suspicious activity
    4. Reputation risk

    Return JSON:
    {{
      "fraud_risk": "",
      "legal_risk": "",
      "reputation": "",
      "red_flags": []
    }}

    Data:
    {data}
    """

    response = model.generate_content(prompt)
    raw = response.text.strip() if response.text else ""

    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        import json
        return json.loads(raw)
    except:
        return {
            "fraud_risk": "Unknown",
            "legal_risk": "Unknown",
            "reputation": "Unknown",
            "red_flags": []
        }