import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from aiogram import Bot

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

from backend.telegram.handlers import get_dashboard_menu_keyboard

WIB = timezone(timedelta(hours=7))

async def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    admin_id = int(os.environ.get("TELEGRAM_ADMIN_ID", "-1003468917523"))
    if not token:
        print("No token")
        return

    bot = Bot(token=token)
    now_wib = datetime.now(WIB)
    menu_text = (
        "🏛️ <b>XEDY AI MISSION CONTROL — DASHBOARD MENU</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Sistem Monitoring Institutional-Grade Multi-Asset (Full HD 16:9)</i>\n"
        f"⏰ Waktu: <b>{now_wib.strftime('%d %b %Y, %H:%M:%S WIB')}</b>\n\n"
        "<b>Pilih Dashboard / Aksi melalui tombol interaktif di bawah:</b>\n\n"
        "1️⃣ 📊 <b>Bloomberg S/R Live</b>\n"
        "   Live tick flow, volume donut ratio, delta, action score & signal grade.\n\n"
        "2️⃣ 🧠 <b>XEDY AI Precision Engine</b>\n"
        "   25 Multi-Agent Engine, independent decision matrix & horizontal range.\n\n"
        "3️⃣ 🌊 <b>Money Flow Radar</b>\n"
        "   Capital flow map, Jillywosy basket, commodity/yield & multi-asset heatmap.\n\n"
        "4️⃣ ⚙️ <b>Level S/R Aktif</b>\n"
        "   Cek & sesuaikan parameter batas Support & Resistance mingguan.\n\n"
        "5️⃣ 📖 <b>Legend Grade & Status</b>\n"
        "   Penjelasan matriks Confidence, Action Score, Grade A+ s/d D, dan 15 Final Status.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 <i>Update otomatis terkirim setiap 15 menit (S/R) & 30 menit (Engine + Radar), atau klik tombol di bawah untuk melihat live on-demand.</i>"
    )
    await bot.send_message(
        chat_id=admin_id,
        text=menu_text,
        reply_markup=get_dashboard_menu_keyboard(),
        parse_mode="HTML"
    )
    print("Dashboard menu sent to Telegram successfully!")
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
