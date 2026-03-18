from fastapi import APIRouter
from app.services.extraction.pdf_parser import extract_text
from app.services.extraction.structured_extractor import extract_structured_data
from app.services.scoring.feature_engineering import create_features
from app.services.scoring.risk_model import calculate_risk
from app.services.agents.decision_agent import final_decision
from app.services.explainability.explainer import explain
from fastapi.responses import FileResponse
from app.services.report_generator import generate_report

# 🔥 NEW IMPORTS (FIXED SYNTAX)
from app.services.agents.research_agent import research_company
from app.services.scoring.advanced_scoring import calculate_5C, final_recommendation

import json

router = APIRouter()


@router.post("/")
def analyze(file_path: str):
    try:
        # 📄 STEP 1: Extract text
        text = extract_text(file_path)

        # 🧠 STEP 2: Structured data
        structured = extract_structured_data(text)

        # 📊 STEP 3: Features
        features = create_features(structured)

        # ⚠️ STEP 4: Basic risk
        risk = calculate_risk(features)

        # 🔥 STEP 5: Research Agent (Pillar 2)
        research = research_company(structured)

        # 🔥 STEP 6: 5C Scoring (Pillar 3)
        score = calculate_5C(features, research)

        recommendation = final_recommendation(score)

        # 🤖 OPTIONAL Gemini decision (backup)
        decision_raw = final_decision(structured, risk)

        try:
            decision_parsed = json.loads(decision_raw) if isinstance(decision_raw, str) else decision_raw
        except:
            decision_parsed = {"decision": decision_raw}

        # 💡 Explainability
        reasons = explain(features)

        # 🚀 FINAL RESPONSE
        return {
            "risk": risk,
            "features": features,
            "research": research,

            # 🔥 MAIN OUTPUT (Advanced)
            "decision": recommendation.get("decision", "N/A"),
            "interest_rate": recommendation.get("interest_rate", "N/A"),
            "loan_amount": recommendation.get("loan_amount", "N/A"),

            # 🔥 OPTIONAL AI DECISION
            "ai_decision": decision_parsed.get("decision", "N/A"),

            "score": score,

            "reasons": reasons if isinstance(reasons, list) else [str(reasons)]
        }

    except Exception as e:
        print("ERROR:", str(e))
        return {"error": str(e)}
  
@router.get("/report")
def download_report(file_path:str):
      try:
            result=analyze(file_path)
            file=generate_report(result)
            return FileResponse(
                  file,
                  media_type='application/pdf',
                  filename="report.pdf"
            )
      except Exception as e:
            print("Report error ",str(e))
            return {"error":str(e)}