def calculate_lead_score(budget: int, interest: str, lead_status: str):
    score = 0

    if budget >= 500000:
        score += 40
    elif budget >= 200000:
        score += 25
    elif budget >= 100000:
        score += 10

    if "ai" in interest.lower():
        score += 30

    if lead_status == "contacted":
        score += 10
    elif lead_status == "qualified":
        score += 20
    elif lead_status == "proposal":
        score += 25

    return min(score, 100)