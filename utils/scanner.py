import re
from typing import Optional, Dict, Any

import httpx

from .trending import compute_trending_score

DEX_API = "https://api.dexscreener.com/latest/dex/tokens/{mint}"

PLACEHOLDER_IMG = "https://dummyimage.com/600x600/000000/ffffff&text=TOKEN"


def parse_token_from_text(text: str) -> Optional[str]:
    """
    Extract a Solana mint from raw text or Pump.fun URL.
    We assume the mint is the last 44-char base58-ish segment.
    """
    text = text.strip()

    # if it's a pump.fun URL, grab last path segment
    m = re.search(r"pump\.fun/.+?/([1-9A-HJ-NP-Za-km-z]{32,64})", text)
    if m:
        return m.group(1)

    # else see if there's a bare mint in the text
    m = re.search(r"([1-9A-HJ-NP-Za-km-z]{32,64})", text)
    if m:
        return m.group(1)

    return None


async def fetch_dex_data(mint: str) -> Optional[Dict[str, Any]]:
    url = DEX_API.format(mint=mint)
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return None
        data = r.json()
    if not data.get("pairs"):
        return None
    # pick highest liquidity pair
    pairs = sorted(
        data["pairs"],
        key=lambda p: p.get("liquidity", {}).get("usd", 0) or 0,
        reverse=True,
    )
    return pairs[0]


async def analyze_token(mint: str) -> Optional[Dict[str, Any]]:
    pair = await fetch_dex_data(mint)
    if not pair:
        return None

    base = pair["baseToken"]
    quote = pair.get("quoteToken", {})
    info = pair.get("info") or {}
    liq = pair.get("liquidity", {})

    mc = float(pair.get("fdv") or pair.get("marketCap") or 0)
    liq_usd = float(liq.get("usd") or 0)
    liq_quote = float(liq.get("quote") or 0)

    # placeholder LP lock info – later we plug Solscan/lockers
    lp_info = {
        "status": "Unknown (v1)",
        "pct": "Unknown",
        "provider": "Unknown",
        "unlock_time": "Unknown",
        "note": "LP lock check will be upgraded in the next version.",
    }

    # placeholder dev info
    dev_info = {
        "score": 70,
        "grade": "B",
        "launches": "Unknown",
        "rugs": "Unknown",
        "history_lines": [
            "Dev history analytics coming soon.",
            "For now, focus on LP, MC and volume trends.",
        ],
    }

    # placeholder promo info
    promo_info = {
        "dex_ads": "Unknown",
        "x_linked": "Yes" if info.get("websites") else "Unknown",
        "web_linked": "Yes" if info.get("websites") else "Unknown",
        "notes": "Promo / ads detection will be expanded later.",
    }

    age_mins = pair.get("ageMinutes")
    vol_1h = float(pair.get("volume", {}).get("h1", 0) or 0)
    buys_1h = int(pair.get("txns", {}).get("h1", {}).get("buys", 0) or 0)
    sells_1h = int(pair.get("txns", {}).get("h1", {}).get("sells", 0) or 0)
    holders = None  # requires Solscan or RPC – later

    trending_score = compute_trending_score(
        mc_now=mc,
        vol_1h=vol_1h,
        buys_1h=buys_1h,
        sells_1h=sells_1h,
        new_holders_1h=0,
    )

    token_data: Dict[str, Any] = {
        "mint": mint,
        "symbol": base["symbol"],
        "name": base["name"],
        "mc": mc,
        "liq_usd": liq_usd,
        "liq_quote": liq_quote,
        "quote_symbol": quote.get("symbol"),
        "age_mins": age_mins,
        "holders": holders,
        "safety_score": 80,  # placeholder global score
        "lp": lp_info,
        "dev": dev_info,
        "promo": promo_info,
        "trend_score": trending_score,
        "vol_1h": vol_1h,
        "buys_1h": buys_1h,
        "sells_1h": sells_1h,
        "ath_mult": 1.0,
        "entry_mult": 1.0,
        "logo_url": info.get("imageUrl") or PLACEHOLDER_IMG,
        "placeholder_img": PLACEHOLDER_IMG,
        "chart_url": pair.get("url"),
        "dex_url": pair.get("url"),
        "pump_url": f"https://pump.fun/{mint}",
    }
    return token_data
