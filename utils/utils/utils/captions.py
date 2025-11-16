from .trending import build_meter_bar


def build_scan_caption(token: dict) -> str:
    symbol = token["symbol"]
    name = token["name"]
    mc = token["mc"]
    liq = token["liq_quote"]
    age = token.get("age_mins")
    safety = token.get("safety_score", 0)
    trend = token.get("trend_score", 0)

    age_str = f"{age:.0f} min" if age is not None else "Unknown"

    line1 = f"🚀 <b>${symbol}</b> ({name}) scan result\n\n"
    stats = (
        f"MC: <b>${mc:,.0f}</b>  |  Liq: <b>{liq:.1f}</b> {token.get('quote_symbol','')}\n"
        f"Age: <b>{age_str}</b>\n"
    )

    lp = token.get("lp", {})
    lp_line = f"LP Lock: <b>{lp.get('status','Unknown')}</b>\n"

    safety_line = f"Safety Score: <b>{safety}/100</b>\n"
    trend_bar = build_meter_bar(trend)
    trend_line = f"\n🔥 Trending Meter: {trend_bar}\n"

    safu_read = (
        "\nSafu Read:\n"
        "Locked LP checks and dev / promo analytics will improve over time.\n"
        "Use this as an early filter, not financial advice."
    )

    return line1 + stats + lp_line + safety_line + trend_line + safu_read


def build_channel_caption(token: dict) -> str:
    symbol = token["symbol"]
    name = token["name"]
    mc = token["mc"]
    trend = token.get("trend_score", 0)
    trend_bar = build_meter_bar(trend)

    text = (
        f"🚀 <b>${symbol}</b> ({name}) – Early Phathom Trending\n\n"
        f"MC: <b>${mc:,.0f}</b>\n"
        f"🔥 Trending Meter: {trend_bar}\n\n"
        "Screened by Early Phathom Trending (migrated Pump.fun plays, "
        "locked LP focus, dev / promo notes).\n"
        "Always DYOR. 🛡"
    )
    return text
