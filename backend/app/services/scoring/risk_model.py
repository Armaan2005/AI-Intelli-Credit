def calculate_risk(f):

    score = 0

    score += 3 if f["debt_ratio"] > 0.7 else 0
    score += 2 if f["profit_margin"] < 0.1 else 0
    score += 3 if f["cashflow_flag"] else 0
    score += 2 if f["fraud_count"] > 0 else 0
    score += 2 if f["legal_count"] > 1 else 0

    if score >= 7:
        return "HIGH"
    elif score >= 4:
        return "MEDIUM"
    return "LOW"