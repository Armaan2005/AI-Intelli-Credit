import json
def safe_div(a,b):
    return a/b if b!=0 else 0

def create_features(data_str):
    if isinstance(data_str,dict):
        data=data_str
    else:
        data=json.loads(data_str)

    revenue = float(data.get("revenue", 1))
    dept = float(data.get("debt", 0))
    profit = float(data.get("profit", 0))
    cashflow = float(data.get("cashflow", 0))

    return {
        "debt_ratio": safe_div(dept,revenue),
        "profit_margin": safe_div(profit,revenue),
        "cashflow_flag": 1 if cashflow < 0 else 0,
        "fraud_count": len(data.get("fraud_signals", [])),
        "legal_count": len(data.get("legal_issues", []))
    }