"""
report.py  (routes)
--------------------
Upgrades your existing generate_report() with:
  ❌ Naming conflict — router.post("/") AND generate_report() same name
     as function imported in analyze.py
  ❌ Plain text PDF — no colors, no tables, no Five Cs section
  ❌ No research section, no explainability, no conditions
  ❌ No output dir creation guard
  ❌ Returns dict with path instead of actual FileResponse

Fixed:
  ✅ Naming conflict resolved — route is /report/generate
  ✅ Professional CAM layout with colors and tables
  ✅ Full Five Cs section
  ✅ Research findings section
  ✅ Risk flags, conditions, recommendations
  ✅ Returns FileResponse directly
"""
import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles  import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units   import inch
from reportlab.lib          import colors
from reportlab.lib.enums   import TA_CENTER, TA_LEFT

router     = APIRouter()
OUTPUT_DIR = "outputs/reports"


# ── Colors matching your presentation palette ─────────────────────────────────
NAVY  = colors.HexColor("#0F1F3D")
TEAL  = colors.HexColor("#00B4D8")
GOLD  = colors.HexColor("#F4A261")
GREEN = colors.HexColor("#22C55E")
RED   = colors.HexColor("#EF4444")
LGRAY = colors.HexColor("#EEF2F7")
MGRAY = colors.HexColor("#4A6080")


class ReportRequest(BaseModel):
    analysis_result: dict
    company_name:    Optional[str] = "Unknown Company"
    filename:        Optional[str] = None


def _get_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "CAMTitle", parent=base["Title"],
            fontSize=22, textColor=NAVY, spaceAfter=6, alignment=TA_CENTER
        ),
        "subtitle": ParagraphStyle(
            "CAMSub", parent=base["Normal"],
            fontSize=11, textColor=MGRAY, alignment=TA_CENTER, spaceAfter=20
        ),
        "section": ParagraphStyle(
            "CAMSection", parent=base["Heading2"],
            fontSize=13, textColor=NAVY, spaceBefore=16, spaceAfter=6,
            borderPad=4, backColor=LGRAY
        ),
        "body": ParagraphStyle(
            "CAMBody", parent=base["Normal"],
            fontSize=10, textColor=colors.black, spaceAfter=4, leading=14
        ),
        "flag_red": ParagraphStyle(
            "FlagRed", parent=base["Normal"],
            fontSize=10, textColor=RED, spaceAfter=3
        ),
        "flag_gold": ParagraphStyle(
            "FlagGold", parent=base["Normal"],
            fontSize=10, textColor=GOLD, spaceAfter=3
        ),
        "flag_green": ParagraphStyle(
            "FlagGreen", parent=base["Normal"],
            fontSize=10, textColor=GREEN, spaceAfter=3
        ),
        "small": ParagraphStyle(
            "CAMSmall", parent=base["Normal"],
            fontSize=9, textColor=MGRAY, spaceAfter=2
        ),
    }
    return styles


def _decision_color(decision: str):
    d = (decision or "").lower()
    if "reject" in d:  return RED
    if "condition" in d: return GOLD
    return GREEN


def build_cam_pdf(data: dict, file_path: str, company_name: str):
    """Build the full CAM PDF document."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    doc    = SimpleDocTemplate(
        file_path,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.75*inch,   bottomMargin=0.75*inch,
    )
    S      = _get_styles()
    story  = []
    now    = datetime.now().strftime("%d %B %Y, %I:%M %p")

    # ── HEADER ───────────────────────────────────────────────────────────────
    story.append(Paragraph("CREDIT APPRAISAL MEMO (CAM)", S["title"]))
    story.append(Paragraph(
        f"Prepared by Intelli-Credit AI System &nbsp;|&nbsp; {now}", S["subtitle"]
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=TEAL, spaceAfter=12))

    # ── DECISION SUMMARY BOX ─────────────────────────────────────────────────
    decision     = data.get("decision", "N/A")
    rating       = data.get("rating", "N/A")
    score        = data.get("total_score", 0)
    interest     = data.get("interest_rate", "N/A")
    loan_amt     = data.get("loan_amount", "N/A")
    risk_level   = data.get("risk_level", "N/A")
    dec_color    = _decision_color(decision)

    summary_data = [
        ["Company",         company_name,        "Application Date", now.split(",")[0]],
        ["Decision",        decision,             "Credit Rating",    rating],
        ["Credit Score",    f"{score}/100",       "Risk Level",       risk_level],
        ["Recommended Rate",interest,             "Loan Amount",      f"₹{loan_amt} Lakhs"],
    ]
    summary_table = Table(summary_data, colWidths=[1.5*inch, 2.5*inch, 1.5*inch, 2.0*inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("BACKGROUND",  (0,1), (0,-1), LGRAY),
        ("BACKGROUND",  (2,1), (2,-1), LGRAY),
        ("FONTNAME",    (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,0), (-1,-1), 10),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("ALIGN",       (0,0), (-1,-1), "LEFT"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, LGRAY]),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("TEXTCOLOR",   (1,1), (1,1),   dec_color),
        ("FONTNAME",    (1,1), (1,1),   "Helvetica-Bold"),
        ("FONTSIZE",    (1,1), (1,1),   11),
        ("TOPPADDING",  (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    # ── RATIONALE ────────────────────────────────────────────────────────────
    rationale = data.get("rationale", "")
    if rationale:
        story.append(Paragraph("Decision Rationale", S["section"]))
        story.append(Paragraph(rationale, S["body"]))

    # ── CONDITIONS ───────────────────────────────────────────────────────────
    conditions = data.get("conditions", [])
    if conditions:
        story.append(Paragraph("Conditions for Approval", S["section"]))
        for c in conditions:
            story.append(Paragraph(f"• {c}", S["body"]))

    # ── FIVE Cs SCORECARD ─────────────────────────────────────────────────────
    story.append(Paragraph("Five Cs Credit Assessment", S["section"]))
    five_c = data.get("five_c_scores", {})
    five_c_rows = [
        ["C", "Dimension", "Score", "Assessment"],
        ["Character",  "Promoter integrity, fraud & litigation history",
         f"{five_c.get('character', 'N/A')}/100",
         "✓ Strong" if float(five_c.get('character', 0)) >= 70 else "⚠ Concern"],
        ["Capacity",   "Cashflow, DSCR, interest coverage",
         f"{five_c.get('capacity', 'N/A')}/100",
         "✓ Strong" if float(five_c.get('capacity', 0)) >= 70 else "⚠ Concern"],
        ["Capital",    "Leverage, debt/equity, profitability",
         f"{five_c.get('capital', 'N/A')}/100",
         "✓ Strong" if float(five_c.get('capital', 0)) >= 70 else "⚠ Concern"],
        ["Collateral", "Security coverage, asset quality",
         f"{five_c.get('collateral', 'N/A')}/100",
         "✓ Strong" if float(five_c.get('collateral', 0)) >= 70 else "⚠ Concern"],
        ["Conditions", "GST compliance, sector outlook",
         f"{five_c.get('conditions', 'N/A')}/100",
         "✓ Strong" if float(five_c.get('conditions', 0)) >= 70 else "⚠ Concern"],
    ]
    five_c_table = Table(five_c_rows, colWidths=[1.2*inch, 3.2*inch, 1.0*inch, 1.8*inch])
    five_c_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTNAME",      (0,1), (0,-1),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("ALIGN",         (2,0), (3,-1),  "CENTER"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story.append(five_c_table)
    story.append(Spacer(1, 12))

    # ── KEY FINANCIAL METRICS ─────────────────────────────────────────────────
    story.append(Paragraph("Key Financial Metrics", S["section"]))
    features  = data.get("features", {})
    kf        = data.get("explainability", {}).get("five_c_detail", {})
    metrics   = [
        ["Metric",                "Value",    "Benchmark",  "Status"],
        ["DSCR",                  f"{features.get('dscr', 'N/A'):.2f}x" if isinstance(features.get('dscr'), float) else "N/A",
         ">1.25x",  "✓" if float(features.get('dscr', 0)) >= 1.25 else "✗"],
        ["Debt/Equity",           f"{features.get('debt_to_equity', 'N/A'):.2f}x" if isinstance(features.get('debt_to_equity'), float) else "N/A",
         "<2.0x",   "✓" if float(features.get('debt_to_equity', 99)) <= 2.0 else "✗"],
        ["Interest Coverage",     f"{features.get('interest_coverage', 'N/A'):.2f}x" if isinstance(features.get('interest_coverage'), float) else "N/A",
         ">3.0x",   "✓" if float(features.get('interest_coverage', 0)) >= 3.0 else "✗"],
        ["Current Ratio",         f"{features.get('current_ratio', 'N/A'):.2f}" if isinstance(features.get('current_ratio'), float) else "N/A",
         ">1.5",    "✓" if float(features.get('current_ratio', 0)) >= 1.5 else "✗"],
        ["Profit Margin",         f"{float(features.get('profit_margin', 0))*100:.1f}%" if features.get('profit_margin') is not None else "N/A",
         ">10%",    "✓" if float(features.get('profit_margin', 0)) >= 0.10 else "✗"],
        ["Collateral Coverage",   f"{features.get('collateral_coverage', 'N/A'):.2f}x" if isinstance(features.get('collateral_coverage'), float) else "N/A",
         ">1.5x",   "✓" if float(features.get('collateral_coverage', 0)) >= 1.5 else "✗"],
        ["GST Compliance",        f"{float(features.get('gst_compliance_score', 0))*100:.0f}%" if features.get('gst_compliance_score') is not None else "N/A",
         ">85%",    "✓" if float(features.get('gst_compliance_score', 0)) >= 0.85 else "✗"],
    ]
    met_table = Table(metrics, colWidths=[2.2*inch, 1.5*inch, 1.3*inch, 1.0*inch])
    met_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  TEAL),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("ALIGN",         (1,0), (-1,-1), "CENTER"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(met_table)
    story.append(Spacer(1, 12))

    # ── RESEARCH FINDINGS ─────────────────────────────────────────────────────
    research = data.get("research", {})
    if research:
        story.append(Paragraph("Secondary Research Findings", S["section"]))
        research_rows = [
            ["Dimension",        "Finding"],
            ["Fraud Risk",       research.get("fraud_risk", "N/A")],
            ["Legal Risk",       research.get("legal_risk", "N/A")],
            ["Sector Risk",      research.get("sector_risk", "N/A")],
            ["Wilful Defaulter", "YES — REJECT" if research.get("wilful_defaulter") else "No"],
        ]
        r_table = Table(research_rows, colWidths=[2.0*inch, 5.2*inch])
        r_table.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  NAVY),
            ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
            ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTNAME",      (0,1), (0,-1),  "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 10),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, LGRAY]),
            ("GRID",          (0,0), (-1,-1), 0.5, colors.lightgrey),
            ("TOPPADDING",    (0,0), (-1,-1), 7),
            ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ]))
        story.append(r_table)

        key_concerns = research.get("key_concerns", "")
        if key_concerns:
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>Key Concerns:</b> {key_concerns}", S["body"]))

        summary = research.get("overall_risk_summary", "")
        if summary:
            story.append(Paragraph(f"<b>Research Summary:</b> {summary}", S["body"]))

    # ── RISK FLAGS ────────────────────────────────────────────────────────────
    risk_flags = data.get("risk_flags", [])
    if risk_flags:
        story.append(Paragraph("Risk Flags", S["section"]))
        for flag in risk_flags:
            style = S["flag_red"] if "🚨" in flag else S["flag_gold"]
            story.append(Paragraph(flag, style))

    # ── EXPLAINABILITY ────────────────────────────────────────────────────────
    expl = data.get("explainability", {})
    narrative = expl.get("narrative", "")
    if narrative:
        story.append(Paragraph("AI Explainability", S["section"]))
        story.append(Paragraph(narrative, S["body"]))

    # ── AI VALIDATION ─────────────────────────────────────────────────────────
    ai_val = data.get("ai_validation", {})
    if ai_val:
        story.append(Paragraph("Credit Committee Note", S["section"]))
        cc_note = ai_val.get("credit_committee_note", "")
        agrees  = ai_val.get("agrees_with_model", False)
        story.append(Paragraph(
            f"<b>Gemini AI Validation:</b> {'✓ Agrees with scoring model' if agrees else '⚠ Differs from scoring model'}",
            S["body"]
        ))
        if cc_note:
            story.append(Paragraph(f"<b>Note for Minutes:</b> {cc_note}", S["body"]))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Generated by <b>Intelli-Credit AI System</b> &nbsp;|&nbsp; "
        f"Confidential — For Internal Use Only &nbsp;|&nbsp; {now}",
        S["small"]
    ))

    doc.build(story)
    return file_path


# ─────────────────────────────────────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/generate")
def generate_report_route(req: ReportRequest):
    """
    Generate CAM PDF from analysis result.
    Fixed naming conflict — was generate_report() same as imported function.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = req.filename or f"CAM_{req.company_name.replace(' ','_')}_{timestamp}.pdf"
    file_path = os.path.join(OUTPUT_DIR, filename)

    try:
        build_cam_pdf(req.analysis_result, file_path, req.company_name)
        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename=filename,
        )
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")


@router.post("/generate-and-analyze")
def analyze_and_report(file_path: str, company_name: str = "Company"):
    """
    Convenience endpoint: analyze a file AND generate the CAM PDF in one call.
    Replaces your /analyze/report endpoint (which had the naming conflict).
    """
    from app.routes.analyze import analyze, AnalyzeRequest

    result = analyze(AnalyzeRequest(file_path=file_path, company_name=company_name))
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = os.path.join(OUTPUT_DIR, f"CAM_{company_name.replace(' ','_')}_{timestamp}.pdf")
    build_cam_pdf(result, out_path, company_name)

    return FileResponse(out_path, media_type="application/pdf", filename=os.path.basename(out_path))