def compute_trending_score(token_data: dict) -> int:
    """
    Very basic trending score algorithm.
    Later we upgrade it to your real AI-based scoring.
    """
    score = 0

    # Market cap boosts
    mc = token_data.get("market_cap", 0)
    if mc > 50000:
        score += 20
    elif mc > 15000:
        score += 10

    # Volume boosts
    vol = token_data.get("volume_1h", 0)
    if vol > 20000:
        score += 25
    elif vol > 5000:
        score += 10

    # Liquidity boost
    if token_data.get("liquidity_locked", False):
        score += 15

    # Dev safety boost
    if token_data.get("dev_score", 0) > 70:
        score += 10

    # Prevent negative
    if score < 0:
        score = 0

    return min(score, 100)
