"""
schemas.py
----------
Upgrades your existing schemas to match the full upgraded pipeline output.

Your original issues:
  ❌ FeatureSchema — only 5 fields, now we have 25+
  ❌ AnalyzeResponse — risk is just str, decision is Any (no structure)
  ❌ No schemas for Research, ExplainabilityResult, FiveCScores, etc.
  ❌ No UploadResponse, ReportRequest schemas
  ❌ DecisionSchema — only 4 fields, no rating/conditions/five_c

All backward-compatible — AnalyzeRequest still works as before.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


# ─────────────────────────────────────────────────────────────────────────────
#  REQUEST SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    """Upgraded — was just file_path: str"""
    file_path:            str
    app_id:               Optional[str]   = "default"
    company_name:         Optional[str]   = ""
    promoter_name:        Optional[str]   = ""
    loan_amount:          Optional[float] = 0
    # Primary insight fields (Pillar 2)
    officer_notes:        Optional[str]   = ""
    site_visit_notes:     Optional[str]   = ""
    factory_capacity_pct: Optional[float] = None


class ReportRequest(BaseModel):
    analysis_result: dict
    company_name:    Optional[str] = "Unknown Company"
    filename:        Optional[str] = None


class OfficerNotesRequest(BaseModel):
    """Credit officer qualitative notes — adjusts risk score"""
    app_id:               str
    officer_notes:        Optional[str]   = ""
    site_visit_notes:     Optional[str]   = ""
    management_notes:     Optional[str]   = ""
    factory_capacity_pct: Optional[float] = None   # e.g. 40.0 = 40%


# ─────────────────────────────────────────────────────────────────────────────
#  FEATURE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class FeatureSchema(BaseModel):
    """
    Upgraded — was 5 fields, now 25+.
    All original fields preserved for backward compat.
    """
    # ── Your original 5 (preserved) ──────────────────────────────────────────
    debt_ratio:     float = 0.0
    profit_margin:  float = 0.0
    cashflow_flag:  int   = 0
    fraud_count:    int   = 0
    legal_count:    int   = 0

    # ── Liquidity ─────────────────────────────────────────────────────────────
    current_ratio:  float = 0.0
    quick_ratio:    float = 0.0
    cash_ratio:     float = 0.0
    wc_to_revenue:  float = 0.0

    # ── Leverage ──────────────────────────────────────────────────────────────
    debt_to_equity:     float = 0.0
    interest_coverage:  float = 0.0
    dscr:               float = 0.0
    total_leverage:     float = 0.0
    loan_to_revenue:    float = 0.0

    # ── Profitability ─────────────────────────────────────────────────────────
    ebitda_margin:  float = 0.0
    roa:            float = 0.0
    roe:            float = 0.0

    # ── India-specific GST ────────────────────────────────────────────────────
    gst_revenue_match:    float = 0.0
    itc_utilisation:      float = 0.0
    gst_compliance_score: float = 0.0

    # ── Behavioural ───────────────────────────────────────────────────────────
    cheque_bounce_flag:   int   = 0
    emi_delay_flag:       int   = 0
    collateral_coverage:  float = 0.0
    business_vintage:     float = 0.0

    class Config:
        extra = "allow"    # allow extra fields without breaking


# ─────────────────────────────────────────────────────────────────────────────
#  FIVE Cs SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

class FiveCScores(BaseModel):
    """Five Cs of Credit — each score 0-100"""
    character:  float = 0.0
    capacity:   float = 0.0
    capital:    float = 0.0
    collateral: float = 0.0
    conditions: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
#  DECISION SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

class DecisionSchema(BaseModel):
    """
    Upgraded — was 4 fields, now full structured output.
    Your original fields (decision, interest_rate, loan_amount, reason) preserved.
    """
    # ── Your original 4 (preserved) ──────────────────────────────────────────
    decision:      str = "N/A"
    interest_rate: str = "N/A"
    loan_amount:   str = "N/A"
    reason:        str = ""

    # ── New fields ────────────────────────────────────────────────────────────
    rating:        Optional[str]        = None    # AAA / AA / A / BBB ...
    risk_level:    Optional[str]        = None    # LOW / MEDIUM / HIGH / CRITICAL
    total_score:   Optional[float]      = None    # 0-100
    rationale:     Optional[str]        = None    # detailed explanation
    conditions:    Optional[List[str]]  = []
    five_c_scores: Optional[FiveCScores] = None
    risk_flags:    Optional[List[str]]  = []


# ─────────────────────────────────────────────────────────────────────────────
#  RESEARCH SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

class ResearchSchema(BaseModel):
    """Output from research_agent.research_company()"""
    fraud_risk:           str        = "Unknown"
    legal_risk:           str        = "Unknown"
    sector_risk:          str        = "Medium"
    reputation:           str        = "Unknown"
    wilful_defaulter:     bool       = False
    red_flags:            List[str]  = []
    key_concerns:         str        = ""
    overall_risk_summary: str        = ""
    promoter_assessment:  str        = ""
    positive_factors:     str        = ""
    mca_risk:             str        = "Low"
    mca_signals:          List[str]  = []
    sources:              Dict[str, Any] = {}

    class Config:
        extra = "allow"


# ─────────────────────────────────────────────────────────────────────────────
#  EXPLAINABILITY SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

class ChartDataPoint(BaseModel):
    """Single data point for frontend Recharts bar chart"""
    name:         str
    score:        float   # 0-100
    contribution: float
    max:          float
    fill:         str     # hex color


class ExplainabilitySchema(BaseModel):
    """Output from explainer.explain()"""
    reasons:       List[str]           = []   # backward compat
    narrative:     str                 = ""
    chart_data:    List[ChartDataPoint] = []
    five_c_detail: Dict[str, Any]      = {}
    score_pct:     float               = 0.0

    class Config:
        extra = "allow"


# ─────────────────────────────────────────────────────────────────────────────
#  AI VALIDATION SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

class AIValidationSchema(BaseModel):
    """Gemini's validation of the scoring engine decision"""
    decision:              str  = "N/A"
    credit_committee_note: str  = ""
    agrees_with_model:     bool = False


# ─────────────────────────────────────────────────────────────────────────────
#  UPLOAD RESPONSE SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    status:       str
    file_id:      str
    filename:     str
    saved_as:     str
    path:         str
    doc_type:     str
    app_id:       str
    size_mb:      float
    rag_chunks:   int
    analyze_url:  str


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN ANALYZE RESPONSE — replaces your AnalyzeResponse
# ─────────────────────────────────────────────────────────────────────────────

class AnalyzeResponse(BaseModel):
    """
    Upgraded — was risk:str, features:FeatureSchema, decision:Any, reasons:List[str]
    Now fully typed matching analyze.py output.
    All original top-level fields preserved.
    """
    status: str = "success"

    # ── Main decision (your original fields at top level) ─────────────────────
    decision:      str = "N/A"
    interest_rate: str = "N/A"
    loan_amount:   str = "N/A"
    rating:        str = "N/A"
    risk_level:    str = "N/A"
    total_score:   float = 0.0
    rationale:     str = ""
    conditions:    List[str] = []

    # ── Structured breakdowns ─────────────────────────────────────────────────
    five_c_scores:  Optional[FiveCScores]         = None
    risk_flags:     List[str]                      = []
    research:       Optional[ResearchSchema]       = None
    explainability: Optional[ExplainabilitySchema] = None
    ai_validation:  Optional[AIValidationSchema]   = None
    features:       Optional[FeatureSchema]        = None

    # ── Metadata ──────────────────────────────────────────────────────────────
    meta: Optional[Dict[str, Any]] = {}

    # ── Backward compat — your original AnalyzeResponse fields ───────────────
    @property
    def risk(self) -> str:
        """Backward compat: risk_level was called risk before"""
        return self.risk_level

    @property
    def reasons(self) -> List[str]:
        """Backward compat: reasons were top-level before"""
        if self.explainability:
            return self.explainability.reasons
        return []

    class Config:
        extra = "allow"


# ─────────────────────────────────────────────────────────────────────────────
#  RISK MODEL SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class RiskResult(BaseModel):
    """Output from risk_model.calculate_risk()"""
    risk_level:    str             = "MEDIUM"
    total_score:   float           = 50.0
    rating:        str             = "BBB"
    hard_reject:   bool            = False
    five_c_scores: Optional[FiveCScores] = None
    risk_flags:    List[str]       = []
    key_factors:   Dict[str, Any]  = {}

    class Config:
        extra = "allow"