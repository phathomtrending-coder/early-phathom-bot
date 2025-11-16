def compute_trending_score(mc_now: float, vol_1h: float, buys_1h: int, sells_1h: int, new_holders_1h: int) -> int:
    vol_component = min(vol_1h / 50_000, 2.0) * 25  # up to 50 pts
    flow_ratio = (buys_1h + 1) / (sells_1h + 1)
    flow_component = min(flow_ratio, 3.0) / 3.0 * 25  # up to 25 pts
    holder_component = min(new_holders_1h / 200, 1.0) * 25  # up to 25 pts

    if 100_000 <= mc_now <= 800_000:
        band_bonus = 10
    else:
        band_bonus = 0

    score = vol_component + flow_component + holder_component + band_bonus
    return int(max(0, min(score, 100)))


def build_meter_bar(score: int) -> str:
    blocks = 10
    filled = int(round(score / 100 * blocks))
    bar = "█" * filled + "░" * (blocks - filled)
    return f"[{bar}] {score}/100"


def build_trend_details_text(token_data: dict) -> str:
    s = token_data.get("trend_score", 0)
    vol = token_data.get("vol_1h", 0)
    buys = token_data.get("buys_1h", 0)
    sells = token_data.get("sells_1h", 0)

    text = (
        "🔥 <b>Trend Analytics</b>\n\n"
        f"Trending Score: {s}/100\n"
        f"Vol (1h): ${vol:,.0f}\n"
        f"Buys (1h): {buys} • Sells (1h): {sells}\n\n"
        "Higher scores generally mean stronger short-term momentum, "
        "but nothing is guaranteed – always manage your risk."
    )
    return text
