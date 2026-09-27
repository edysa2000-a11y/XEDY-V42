import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
import os

logger = logging.getLogger("xedy.telegram.handlers")

def register_handlers(dp: Dispatcher, admin_id: int, sr_monitor=None):
    """
    Registers all bot commands.
    Secured by comparing user ID with admin_id.
    """
    
    @dp.message(Command("id"))
    async def cmd_id(message: Message):
        await message.answer(f"🆔 <b>Chat ID:</b> <code>{message.chat.id}</code>\nRezim Chat: <b>{message.chat.type.upper()}</b>")

    @dp.message(Command("start"))
    async def cmd_start(message: Message):
        if message.from_user.id != admin_id:
            return
        await message.answer("✅ XEDY S/R Real-Time Monitor Active.\nKetik /sr untuk melihat status Support & Resistance XAUUSD & USDJPY.")
        
    @dp.message(Command("sr"))
    async def cmd_sr(message: Message):
        if message.from_user.id != admin_id:
            return
        if sr_monitor:
            summary = sr_monitor.get_current_status_summary()
            try:
                from aiogram.types import BufferedInputFile
                photo_bytes = sr_monitor.generate_current_photo_card()
                input_file = BufferedInputFile(photo_bytes, filename="weekly_sr_card.png")
                await message.answer_photo(photo=input_file, caption=summary, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Error sending S/R photo on /sr: {e}")
                await message.answer(summary, parse_mode="HTML")
        else:
            await message.answer("⚠️ S/R Monitor Engine belum diinisialisasi.")

    @dp.message(Command("status"))
    async def cmd_status(message: Message):
        if message.from_user.id != admin_id:
            return
        sr_info = sr_monitor.get_current_status_summary() if sr_monitor else "S/R Engine: Off"
        await message.answer(f"🤖 <b>STATUS SISTEM XEDY S/R MONITOR</b>\n\n📈 MT5: Terhubung\n⏱️ Interval: 1 Menit\n📍 Timezone: WIB (UTC+7)\n\n{sr_info}", parse_mode="HTML")
        
    @dp.message(Command("pause"))
    async def cmd_pause(message: Message):
        if message.from_user.id != admin_id:
            return
        await message.answer("⏸️ Perintah Jeda Diterima.")

    @dp.message(Command("resume"))
    async def cmd_resume(message: Message):
        if message.from_user.id != admin_id:
            return
        await message.answer("▶️ Monitor S/R dilanjutkan.")

    @dp.message(Command("macro", "summary"))
    async def cmd_macro(message: Message):
        if message.from_user.id != admin_id:
            return
        macro_text = (
            "🌍 <b>MACRO & FUNDAMENTAL TREND SUMMARY</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🟡 <b>XAUUSD (GOLD) — BIAS: BULLISH (UPTREND)</b>\n"
            "• <b>Indikator US</b>: Pemangkasan suku bunga The Fed (dovish cycle) menekan Real Yield & DXY, sangat mendongkrak daya tarik emas.\n"
            "• <b>Geopolitik</b>: Eskalasi Timur Tengah & perang regional memicu pembelian Safe Haven masif serta akumulasi cadangan devisa emas oleh Bank Sentral (PBoC, BRICS).\n"
            "• <b>Oil & Komoditas</b>: Fluktuasi energi menjaga ekspektasi inflasi tetap tinggi, memperkuat emas sebagai lindung nilai (hedge).\n"
            "🎯 <i>Key Range: Support 4220.00 | Resistance 4580.00</i>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💴 <b>USDJPY — BIAS: BEARISH / TEKANAN TURUN</b>\n"
            "• <b>Indikator 2 Negara (US vs Japan)</b>: Divergensi moneter (The Fed memangkas suku bunga vs BOJ menaikkan suku bunga secara bertahap). Penyempitan yield spread memicu <i>Carry Trade Unwind</i> (penguatan Yen).\n"
            "• <b>Geopolitik</b>: Status Yen sebagai mata uang pendanaan safe haven regional di Asia membatasi ruang penguatan USD.\n"
            "• <b>Oil Impact</b>: Jepang adalah 90%+ net importir minyak. Penurunan/stabilisasi harga minyak mengurangi beban neraca dagang Jepang, memperkuat Yen (menekan USDJPY turun).\n"
            "🎯 <i>Key Range: Support 152.80 | Resistance 158.30</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
        await message.answer(macro_text, parse_mode="HTML")

    @dp.message(Command("usdjpy", "jpy"))
    async def cmd_usdjpy(message: Message):
        if message.from_user.id != admin_id:
            return
        
        cfg = sr_monitor.CONFIG.get("USDJPY", {"support": 152.80, "resistance": 158.30, "digits": 2}) if sr_monitor else {"support": 152.80, "resistance": 158.30, "digits": 2}
        jdata = sr_monitor.last_price_data.get("USDJPY", {}) if sr_monitor else {}
        live_p = jdata.get("mid", 157.29)
        dist_s = jdata.get("dist_s", live_p - cfg["support"])
        dist_r = jdata.get("dist_r", cfg["resistance"] - live_p)
        st = jdata.get("status", "NORMAL")
        
        text = (
            "💴 <b>USDJPY — COMPLETE S/R & MACRO SUMMARY</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📊 <b>TECHNICAL & S/R SNAPSHOT</b>\n"
            f"• 💰 Current Price: <b>{live_p:.2f}</b>\n"
            f"• 🔒 Resistance: <b>{cfg['resistance']:.2f}</b> (Jarak: {dist_r:+.2f} | {(dist_r/cfg['resistance'])*100:+.2f}%)\n"
            f"• 🔒 Support: <b>{cfg['support']:.2f}</b> (Jarak: {dist_s:+.2f} | {(dist_s/cfg['support'])*100:+.2f}%)\n"
            f"• 📍 Status: <b>{st}</b> (Near R: ≥ 157.83 | Near S: ≤ 153.26)\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🏛️ <b>1. INDIKATOR EKONOMI 2 NEGARA (US vs JEPANG)</b>\n"
            "• <b>The Fed (Dovish / Rate Cut)</b>: Pelonggaran suku bunga AS menekan imbal hasil US Treasury 10Y.\n"
            "• <b>BOJ (Hawkish / Normalisasi)</b>: Inflasi Jepang >2% mendorong Bank of Japan menaikkan suku bunga.\n"
            "• <b>Yield Spread & Carry Trade</b>: Selisih yield menyempit → Penutupan Carry Trade secara masif → Permintaan Yen naik → USDJPY tertekan turun.\n\n"
            "⚔️ <b>2. FAKTOR GEOPOLITIK</b>\n"
            "• <b>Risk-Off Sentiment</b>: Konflik global memperkuat reputasi Yen sebagai mata uang safe haven utama di Asia, membatasi kenaikan USD.\n\n"
            "🛢️ <b>3. DAMPAK MINYAK & KOMODITAS</b>\n"
            "• <b>Ketergantungan Energi 90%+</b>: Penurunan atau stabilisasi harga minyak mengurangi beban neraca dagang Jepang, memperkuat fundamental Yen secara bertahap.\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎯 <b>KESIMPULAN & BIAS TREN</b>:\n"
            "<b>BEARISH / TEKANAN TURUN (Sell on Strength)</b>\n"
            "Area Resistance 158.30 menjadi benteng pertahanan penjual (rejection zone), dengan target pelemahan menguji area Support 152.80."
        )
        await message.answer(text, parse_mode="HTML")

    logger.info("Telegram handlers registered.")
