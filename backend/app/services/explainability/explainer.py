def explain(f):

    reasons = []

    if f["debt_ratio"] > 0.7:
        reasons.append("High debt burden")

    if f["profit_margin"] < 0.1:
        reasons.append("Low profitability")

    if f["cashflow_flag"]:
        reasons.append("Negative cash flow")

    if f["fraud_count"] > 0:
        reasons.append("Fraud signals detected")

    if f["legal_count"] > 1:
        reasons.append("Multiple legal cases")

    return reasons