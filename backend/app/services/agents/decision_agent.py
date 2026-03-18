import json
import re
import google.generativeai as genai
from app.config.settings import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")


def clean_json(text):
    # remove
    text = text.replace(r"```json|```", "").replace("```","").strip()

    # extract JSON only
    start = text.find("{")
    end = text.rfind("}") + 1

    if start != -1 and end != -1:
        text = text[start:end]

    try:
        return json.loads(text)
    except:
        return {
            "decision": "Unknown",
            "interest_rate": "N/A",
            "loan_amount": "N/A",
            "reason": "Parsing failed"
        }


def final_decision(data, risk):

    prompt = f"""
    You are a senior credit officer.

    Analyze the data and risk.

    STRICT RULE:
    - Return ONLY valid JSON
    - No explanation outside JSON

    Format:
    {{
      "decision": "Approve / Reject",
      "interest_rate": "e.g. 7.5%",
      "loan_amount": "number",
      "reason": "short explanation"
    }}

    Data:
    {data}

    Risk:
    {risk}
    """

    response = model.generate_content(prompt)

    raw = response.text if response.text else ""
    print("🔍 DECISION RAW:", raw)

    return clean_json(raw)