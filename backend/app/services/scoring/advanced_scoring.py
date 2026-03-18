def calculate_5C(features, research):
    score = 0

    # Character (fraud + legal)
    if research["fraud_risk"] == "High":
        score -= 30
    if research["legal_risk"] == "High":
        score -= 20

    # Capacity (cashflow)
    if features["cashflow_flag"] > 0:
        score += 20

    # Capital (profit)
    if features["profit_margin"] > 0:
        score += 20

    # Collateral (dummy)
    score += 10

    # Conditions (risk)
    if features["debt_ratio"] > 1:
        score -= 20

    return score


def final_recommendation(score):
    if score > 20:
        return {
            "decision": "Approve",
            "interest_rate": "7%",
            "loan_amount": "100000"
        }
    elif score > 0:
        return {
            "decision": "Approve with conditions",
            "interest_rate": "10%",
            "loan_amount": "50000"
        }
    else:
        return {
            "decision": "Reject",
            "interest_rate": "N/A",
            "loan_amount": "0"
        }