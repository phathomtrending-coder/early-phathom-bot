import asyncio
import logging
import os

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from utils.scanner import analyze_token, parse_token_from_text
from utils.captions import build_scan_caption, build_channel_caption
from utils.trending import build_trend_details_text
from utils.storage import init_storage, get_cached_token, cache_token_result

# ---------- CONFIG ----------

BOT_TOKEN = os.environ.get("BOT_TOKEN")  # put in Render env var
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1002557126923"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------- HELPERS ----------

def build_main_keyboard(token_data: dict) -> InlineKeyboardMarkup:
    token_addr = token_data["mint"]
    chart_url = token_data.get("chart_url") or token_data.get("dex_url", "")
    pump_url = token_data.get("pump_url", "")

    keyboard = [
        [
            InlineKeyboardButton("📊 Chart", url=chart_url or "https://dexscreener.com/solana"),
            InlineKeyboardButton("🪙 Pump.fun", url=pump_url or "https://pump.fun"),
            InlineKeyboardButton("💧 LP Info", callback_data=f"lp:{token_addr}"),
        ],
        [
            InlineKeyboardButton("👤 Dev History", callback_data=f"dev:{token_addr}"),
            InlineKeyboardButton("📣 Promo", callback_data=f"promo:{token_addr}"),
            InlineKeyboardButton("🔥 Trend Details", callback_data=f"trend:{token_addr}"),
        ],
        [
            InlineKeyboardButton("📡 Post to Channel", callback_data=f"post:{token_addr}")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def send_scan_result(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    token_data: dict,
    as_reply: bool = True,
):
    caption = build_scan_caption(token_data)
    keyboard = build_main_keyboard(token_data)

    target = update.effective_chat.id if as_reply else CHANNEL_ID
    await context.bot.send_photo(
        chat_id=target,
        photo=token_data.get("logo_url", token_data.get("placeholder_img")),
        caption=caption,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )


# ---------- COMMAND HANDLERS ----------

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👻 <b>Welcome to Early Phathom Trending</b>\n\n"
        "I scan migrated Pump.fun tokens on Solana and highlight safer early plays:\n"
        "• Locked LP & basic safety checks\n"
        "• Dev history notes (when known)\n"
        "• A live trending meter\n\n"
        "Use:\n"
        "<code>/scan &lt;token_mint_or_pumpfun_link&gt;</code>\n\n"
        "Always <b>DYOR</b>. I just help filter the noise. 🛡"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🧾 <b>Commands</b>\n\n"
        "/start – Intro & how it works\n"
        "/help – This help menu\n"
        "/scan &lt;mint_or_link&gt; – Safety + trending scan\n"
        "/feature &lt;mint_or_link&gt; – Scan and post to the channel\n\n"
        "You can also just paste a Pump.fun link or token mint in DM and I’ll try to scan it."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Send a Pump.fun link or token mint.\nExample:\n<code>/scan 4fU9...Mint</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    raw = " ".join(context.args).strip()
    await run_scan_flow(update, context, raw)


async def feature_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan a token and post it straight into the channel."""
    if not context.args:
        await update.message.reply_text(
            "Usage:\n<code>/feature &lt;mint_or_pumpfun_link&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    raw = " ".join(context.args).strip()
    token_addr = parse_token_from_text(raw)
    if not token_addr:
        await update.message.reply_text("I couldn't parse a token mint from that.")
        return

    await update.message.reply_text("Scanning and posting to channel…")
    token_data = await analyze_token(token_addr)
    if not token_data:
        await update.message.reply_text("Scan failed or token not found.")
        return

    cache_token_result(token_data)
    # send to channel
    await send_scan_result(update, context, token_data, as_reply=False)


async def run_scan_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, raw: str):
    token_addr = parse_token_from_text(raw)
    if not token_addr:
        await update.message.reply_text("I couldn't detect a Solana mint. Paste a valid mint or Pump.fun link.")
        return

    await update.message.reply_text("⏳ Scanning token on Solana…")

    token_data = await analyze_token(token_addr)
    if not token_data:
        await update.message.reply_text("Scan failed – token not found or API offline.")
        return

    cache_token_result(token_data)
    await send_scan_result(update, context, token_data)


# ---------- MESSAGE HANDLER (plain text in DM) ----------

async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Treat any plain text in DM as potential token
    if update.effective_chat.type != "private":
        return  # ignore group messages for now

    raw = update.message.text.strip()
    token_addr = parse_token_from_text(raw)
    if not token_addr:
        await update.message.reply_text(
            "Paste a Pump.fun link or Solana token mint to scan.\n"
            "Or use <code>/scan &lt;mint_or_link&gt;</code>.",
            parse_mode=ParseMode.HTML,
        )
        return

    await run_scan_flow(update, context, raw)


# ---------- CALLBACKS ----------

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if ":" not in data:
        return

    action, token_addr = data.split(":", 1)
    token_data = get_cached_token(token_addr)
    if not token_data:
        # Re-scan as a fallback
        token_data = await analyze_token(token_addr)
        if not token_data:
            await query.message.reply_text("Token info not available right now.")
            return
        cache_token_result(token_data)

    if action == "lp":
        lp = token_data.get("lp", {})
        text = (
            "💧 <b>LP Lock Information</b>\n\n"
            f"Lock status: {lp.get('status', 'Unknown')}\n"
            f"Locked %: {lp.get('pct', 'Unknown')}\n"
            f"Locker: {lp.get('provider', 'Unknown')}\n"
            f"Unlocks: {lp.get('unlock_time', 'Unknown')}\n\n"
            f"{lp.get('note', '')}"
        )
        await query.message.reply_text(text, parse_mode=ParseMode.HTML)

    elif action == "dev":
        dev = token_data.get("dev", {})
        history_lines = dev.get("history_lines", ["No detailed history yet."])
        text = (
            "👤 <b>Dev History</b>\n\n"
            f"Score: {dev.get('grade', 'N/A')} ({dev.get('score', '0')}/100)\n"
            f"Launches: {dev.get('launches', 'Unknown')} • Rugs: {dev.get('rugs', 'Unknown')}\n\n"
            + "\n".join(history_lines)
        )
        await query.message.reply_text(text, parse_mode=ParseMode.HTML)

    elif action == "promo":
        promo = token_data.get("promo", {})
        text = (
            "📣 <b>Promo / Marketing</b>\n\n"
            f"Dex ads: {promo.get('dex_ads', 'Unknown')}\n"
            f"X linked: {promo.get('x_linked', 'Unknown')}\n"
            f"Website: {promo.get('web_linked', 'Unknown')}\n\n"
            f"{promo.get('notes', 'No extra promo info yet.')}"
        )
        await query.message.reply_text(text, parse_mode=ParseMode.HTML)

    elif action == "trend":
        text = build_trend_details_text(token_data)
        await query.message.reply_text(text, parse_mode=ParseMode.HTML)

    elif action == "post":
        # post current token to channel
        await send_scan_result(update, context, token_data, as_reply=False)
        await query.message.reply_text("Posted to @EarlyPhathomTrending ✅")


# ---------- MAIN ----------

async def main():
    init_storage()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("scan", scan_cmd))
    application.add_handler(CommandHandler("feature", feature_cmd))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    application.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("Starting EarlyPhathomTrendingBot…")
    await application.run_polling(close_loop=False)


if __name__ == "__main__":
    asyncio.run(main())
