from pydantic import BaseModel
from typing import List, Dict, Any


class AnalyzeRequest(BaseModel):
    file_path: str


class FeatureSchema(BaseModel):
    debt_ratio: float
    profit_margin: float
    cashflow_flag: int
    fraud_count: int
    legal_count: int


class DecisionSchema(BaseModel):
    decision: str
    interest_rate: str
    loan_amount: str
    reason: str


class AnalyzeResponse(BaseModel):
    risk: str
    features: FeatureSchema
    decision: Any
    reasons: List[str]