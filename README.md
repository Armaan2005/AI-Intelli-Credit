# 🧠 Intelli-Credit — AI-Powered Credit Decisioning Engine

> **Next-Gen Corporate Credit Appraisal: Bridging the Intelligence Gap**

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.0_Flash-orange?logo=google)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-purple)](LICENSE)

---

## 🎯 Problem We Solve

Aaj ek bank ko kisi company ka **loan approve ya reject** karne mein **3-4 hafte** lagte hain. Credit manager ko manually:
- 50+ PDF documents padhne padte hain
- GST returns manually check karne padte hain  
- Court records, news, MCA filings manually dhundne padte hain
- Sab data ek jagah jodke decision lena padta hai

**Yeh process slow, expensive, aur error-prone hai.**

---

## ✅ Our Solution

**Intelli-Credit** wahi kaam **10 minute mein** automatically karta hai.

```
📄 Document Upload
       ↓
🔍 AI Text Extraction (PDF/Excel/CSV)
       ↓
📊 25+ Financial Features Engineering
       ↓
🌐 Web Research Agent (News + MCA + Sector)
       ↓
🤖 Five Cs Scoring Engine (ML-based)
       ↓
📋 Credit Appraisal Memo (CAM) — PDF Download
```

---

## 🏗️ Architecture — Three Pillars

### Pillar 1 — Data Ingestor
- PDF, Excel, CSV documents parse karta hai
- OCR support for scanned documents (Hindi + English)
- **GST Intelligence** — GSTR-2A vs 3B cross-verification
- Circular trading & revenue inflation detection
- 20+ financial fields auto-extract (Revenue, EBITDA, DSCR, D/E ratio)

### Pillar 2 — Research Agent
- **Web search** — company news, promoter background, fraud signals
- **MCA check** — director disqualification, pending charges
- **Sector risk map** — 12 India-specific sectors (Real Estate, Textile, IT, etc.)
- **Primary insights portal** — credit officer site visit notes, factory capacity
- Gemini AI deep analysis of all gathered data

### Pillar 3 — Recommendation Engine
- **Five Cs scoring** — Character, Capacity, Capital, Collateral, Conditions
- **MCLR-linked interest rates** — AAA=8.5% to CCC=15%
- **DSCR-based loan amount** — not hardcoded, calculated from financials
- **Explainability** — every decision has a specific rationale
- **CAM PDF generator** — professional Credit Appraisal Memo download

---

## 🇮🇳 India-Specific Intelligence

| Feature | Detail |
|---|---|
| GST Compliance | GSTR-2A vs 3B mismatch detection |
| CIBIL Integration | Commercial score + SMA classification |
| MCA21 | Director disqualification, charge creation |
| e-Courts | NCLT, DRT, civil suits detection |
| SARFAESI | Action monitoring |
| RBI Defaulter | Wilful defaulter cross-check |
| IndAS | Indian Accounting Standards aware |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | HTML, CSS, JavaScript (Glass morphism UI) |
| **Backend** | FastAPI, Python 3.11 |
| **AI / LLM** | Google Gemini 2.0 Flash |
| **PDF Parsing** | pdfplumber, pytesseract (OCR) |
| **RAG Pipeline** | Custom vector store + Gemini embeddings |
| **Report Generation** | ReportLab (Professional PDF) |
| **Web Research** | DuckDuckGo Search (no API key needed) |
| **Deployment** | Render (Backend) + Netlify (Frontend) |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Gemini API Key ([Get free here](https://aistudio.google.com))

### Setup

```bash
# 1. Clone karo
git clone https://github.com/Armaan2005/AI-Intelli-Credit
cd AI-Intelli-Credit

# 2. Environment setup
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Dependencies install karo
pip install -r requirements.txt

# 4. .env file banao
echo "GEMINI_API_KEY=your-key-here" > .env

# 5. Server start karo
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
# frontend/ folder mein sirf teen files hain
# index.html, style.css, script.js
# Kisi bhi static server pe serve karo ya Netlify pe drag & drop karo
```

---

## 📁 Project Structure

```
AI-Intelli-Credit/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── config/
│   │   │   └── settings.py            # Environment config
│   │   ├── routes/
│   │   │   ├── upload.py              # Document upload
│   │   │   ├── analyze.py             # Full analysis pipeline
│   │   │   └── report.py              # CAM PDF generation
│   │   ├── services/
│   │   │   ├── agents/
│   │   │   │   ├── research_agent.py  # Web + MCA + Gemini research
│   │   │   │   └── decision_agent.py  # Final Gemini validation
│   │   │   ├── extraction/
│   │   │   │   ├── pdf_parser.py      # PDF/Excel/CSV extraction
│   │   │   │   ├── ocr_pipeline.py    # OCR for scanned docs
│   │   │   │   └── structured_extractor.py  # Regex + Gemini extraction
│   │   │   ├── scoring/
│   │   │   │   ├── feature_engineering.py   # 25+ financial features
│   │   │   │   ├── risk_model.py             # Five Cs weighted scoring
│   │   │   │   └── advanced_scoring.py       # MCLR rates + recommendation
│   │   │   ├── explainability/
│   │   │   │   └── explainer.py       # SHAP-style explanations
│   │   │   └── rag/
│   │   │       ├── embedder.py        # Gemini text embeddings
│   │   │       ├── vector_store.py    # Cosine similarity search
│   │   │       └── retriever.py       # Semantic document retrieval
│   │   └── models/
│   │       └── schemas.py             # Pydantic schemas
│   └── requirements.txt
├── frontend/
│   ├── index.html                     # Main UI
│   ├── style.css                      # Glass morphism design
│   └── script.js                      # API integration
└── README.md
```

---

## 🎬 How It Works — Demo Flow

1. **Upload** company's Annual Report / Bank Statement / GST Return
2. **Fill** company name, promoter name, loan amount requested
3. **Click** "Analyze Document"
4. **Watch** the 6-step AI pipeline run:
   - 📄 Text extraction
   - 📊 Feature engineering  
   - 🌐 Research agent
   - 🤖 Five Cs scoring
   - 💡 AI decision
   - 📋 Report generation
5. **Get** complete credit assessment with:
   - Approve / Reject / Conditional decision
   - Credit score (0-100) + Rating (AAA to D)
   - Recommended loan amount + Interest rate
   - Five Cs breakdown with scores
   - Risk flags with specific evidence
   - Download CAM PDF

---

## 📊 Sample Output

```json
{
  "decision": "Approve",
  "rating": "BBB",
  "total_score": 68.5,
  "interest_rate": "10.75%",
  "loan_amount": "450",
  "rationale": "Application APPROVED. Score 68.5/100 (BBB). 
                DSCR 1.38x adequate. GST compliant. 
                No fraud signals. Collateral 1.52x coverage.",
  "five_c_scores": {
    "character": 82,
    "capacity": 71,
    "capital": 65,
    "collateral": 88,
    "conditions": 75
  }
}
```

---

## 🏆 Hackathon — Intelli-Credit Challenge

Built for the **"Next-Gen Corporate Credit Appraisal"** hackathon.

**Evaluation Criteria Coverage:**

| Criteria | How We Address It |
|---|---|
| ✅ Extraction Accuracy | pdfplumber + OCR + Regex + Gemini pipeline |
| ✅ Research Depth | DuckDuckGo + MCA signals + Sector risk map |
| ✅ Explainability | Every decision has specific rationale with data points |
| ✅ India Context | GSTR-2A/3B, CIBIL, SARFAESI, MCA21, IndAS aware |

---

## 👨‍💻 Developer

**Armaan** — [GitHub](https://github.com/Armaan2005)

---

*From weeks to hours. From black box to transparent. From data overload to actionable intelligence.* 🚀
