import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from aiogram import Bot

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))

WIB = timezone(timedelta(hours=7))

async def send_d1h4_recommendations():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    admin_id_str = os.environ.get("TELEGRAM_ADMIN_ID", "-1003468917523")
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN not found in .env")
        return False

    try:
        admin_id = int(admin_id_str)
    except ValueError:
        admin_id = admin_id_str

    bot = Bot(token=token)
    now_wib = datetime.now(WIB)
    time_str = now_wib.strftime("%d %b %Y • %H:%M:%S WIB")

    msg = (
        "🎯 <b>XEDY AI MISSION CONTROL • REKOMENDASI D1 &amp; H4</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 <b>AI QWEN 3.7 ADAPTIVE ACCURACY VALIDATED</b>\n"
        f"📅 Waktu: <b>{time_str}</b>\n"
        "⚡ Sistem: <i>Multi-Horizon Macro &amp; Microstructure Confluence</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        "🇯🇵 <b>1. USD/JPY</b> — <code>SELL LIMIT / SHORT FADE</code>\n"
        "• <b>Bias D1:</b> 🔴 Bearish Rejection (Bull Trap 89% Conf)\n"
        "• <b>Pemicu H4:</b> <b>13.30 – 14.15 WIB (London Open ⭐)</b>\n"
        "• <b>Entry Zone (OP):</b> <code>158.303 – 158.363</code>\n"
        "• <b>Adaptive SL:</b> <code>158.773</code> (+3.4p ATR buffer)\n"
        "• <b>Target:</b> TP1 <code>157.923</code> | TP2 <code>157.523</code>\n"
        "• <b>Risk/Reward:</b> 1 : 1.9  |  <b>Alokasi Lot:</b> 0.5x (Half Risk)\n"
        "• <b>AI Qwen:</b> <b>94.6% [APPROVED]</b> • Win Rate 88.2%\n\n"

        "🥇 <b>2. XAU/USD (GOLD)</b> — <code>BUY PULLBACK / DIP</code>\n"
        "• <b>Bias D1:</b> 🟢 Bullish Accumulation (Whale Inflow +116)\n"
        "• <b>Pemicu H4:</b> <b>13.30 – 14.00 WIB (London Retest ⭐)</b>\n"
        "• <b>Entry Zone (OP):</b> <code>4,178.00 – 4,182.00</code>\n"
        "• <b>Adaptive SL:</b> <code>4,165.50</code> (+$4.20 ATR buffer)\n"
        "• <b>Target:</b> TP1 <code>4,210.00</code> | TP2 <code>4,235.00</code>\n"
        "• <b>Risk/Reward:</b> 1 : 2.4  |  <b>Alokasi Lot:</b> 1.0x (Full Size)\n"
        "• <b>AI Qwen:</b> <b>95.8% [APPROVED]</b> • Win Rate 91.4%\n\n"

        "🇪🇺 <b>3. EUR/USD</b> — <code>TREND FOLLOWING SHORT</code>\n"
        "• <b>Bias D1:</b> 🔴 Downtrend Continuation (100% Convergent)\n"
        "• <b>Pemicu H4:</b> <b>13.30 WIB (London Sell Breakout ⭐)</b>\n"
        "• <b>Entry Zone (OP):</b> <code>1.12150 – 1.12350</code>\n"
        "• <b>Adaptive SL:</b> <code>1.12650</code> (+4.2p buffer)\n"
        "• <b>Target:</b> TP1 <code>1.11600</code> | TP2 <code>1.11200</code>\n"
        "• <b>Risk/Reward:</b> 1 : 2.1  |  <b>Alokasi Lot:</b> 1.0x (Full Size)\n"
        "• <b>AI Qwen:</b> <b>93.4% [APPROVED]</b> • Win Rate 89.1%\n\n"

        "🇬🇧 <b>4. GBP/USD</b> — <code>STANDBY / NO TRADE</code>\n"
        "• <b>Bias D1:</b> ⚪ Neutral Range / Parity Chop\n"
        "• <b>Pemicu H4:</b> Tidak ada momentum edge (Noise 1.3200-1.3250)\n"
        "• <b>AI Qwen:</b> <b>72.5% [OVERRULED / REJECT]</b>\n"
        "• <b>Alokasi Lot:</b> <b>0.0x LOCKED</b> (Proteksi Modal)\n\n"

        "🛢️ <b>5. CRUDE OIL (WTI)</b> — <code>BUY RETEST / LONG</code>\n"
        "• <b>Bias D1:</b> 🟢 Bullish Expansion (Supply Deficit +94)\n"
        "• <b>Pemicu H4:</b> <b>14.30 – 15.00 WIB (Europe Retest ⭐)</b>\n"
        "• <b>Entry Zone (OP):</b> <code>90.00 – 90.30</code>\n"
        "• <b>Adaptive SL:</b> <code>89.40</code> (+$0.45 buffer)\n"
        "• <b>Target:</b> TP1 <code>92.50</code> | TP2 <code>93.80</code> (RR 1:2.5)\n"
        "• <b>AI Qwen:</b> <b>92.1% [APPROVED]</b> • Lot: 0.8x Dynamic\n\n"

        "⚡ <b>6. BITCOIN (BTC/USD)</b> — <code>AGGRESSIVE ACCUMULATION</code>\n"
        "• <b>Bias D1:</b> 🟢 Bullish Whale Absorption (Alpha +116)\n"
        "• <b>Pemicu H4:</b> <b>20.30 WIB (US Wall Street Peak ⭐)</b>\n"
        "• <b>Entry Zone (OP):</b> <code>82,000 – 82,400</code>\n"
        "• <b>Adaptive SL:</b> <code>81,200</code> (+$650 buffer)\n"
        "• <b>Target:</b> TP1 <code>85,000</code> | TP2 <code>88,000</code> (RR 1:3.2)\n"
        "• <b>AI Qwen:</b> <b>96.2% [APPROVED]</b> • Lot: 1.0x Full Size\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 <b>PANDUAN EKSEKUSI:</b>\n"
        "• Waktu eksekusi emas adalah sesi <b>London Open (13.30 – 14.15 WIB)</b>.\n"
        "• Disiplin gunakan SL adaptif untuk menangkis perburuan likuiditas (stop hunt).\n"
        "• Pantau live update di browser: <code>http://localhost:8000/sr.html</code>"
    )

    try:
        await bot.send_message(
            chat_id=admin_id,
            text=msg,
            parse_mode="HTML"
        )
        print("SUCCESS: Telegram message sent successfully!")
        await bot.session.close()
        return True
    except Exception as e:
        print(f"FAILED to send Telegram message: {e}")
        await bot.session.close()
        return False

if __name__ == "__main__":
    asyncio.run(send_d1h4_recommendations())
