import asyncio
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    Message, BufferedInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
import os

logger = logging.getLogger("xedy.telegram.handlers")
WIB = timezone(timedelta(hours=7))

def get_dashboard_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Creates institutional inline buttons for 1-click dashboard access.
    """
    buttons = [
        [
            InlineKeyboardButton(text="📊 Bloomberg S/R Live (16:9)", callback_data="menu:sr"),
            InlineKeyboardButton(text="🧠 Precision Engine (16:9)", callback_data="menu:engine")
        ],
        [
            InlineKeyboardButton(text="🌊 Money Flow Radar (16:9)", callback_data="menu:flow"),
            InlineKeyboardButton(text="📜 Narasi Analisis Pasar", callback_data="menu:nr_menu")
        ],
        [
            InlineKeyboardButton(text="⚙️ Level S/R Aktif", callback_data="menu:setsnr"),
            InlineKeyboardButton(text="📈 Ringkasan Metrik", callback_data="menu:status")
        ],
        [
            InlineKeyboardButton(text="📖 Legend Grade & Status", callback_data="menu:legend"),
            InlineKeyboardButton(text="🚀 Kirim Semua (3-in-1)", callback_data="menu:all")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_narrative_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Inline buttons for 1-click individual pair narrative selection.
    """
    buttons = [
        [
            InlineKeyboardButton(text="📜 Narasi XAUUSD (Gold)", callback_data="menu:nr:xauusd"),
            InlineKeyboardButton(text="📜 Narasi USDJPY", callback_data="menu:nr:usdjpy")
        ],
        [
            InlineKeyboardButton(text="📜 Narasi EURUSD", callback_data="menu:nr:eurusd"),
            InlineKeyboardButton(text="📜 Narasi GBPUSD", callback_data="menu:nr:gbpusd")
        ],
        [
            InlineKeyboardButton(text="📜 Narasi OIL (WTI)", callback_data="menu:nr:oil"),
            InlineKeyboardButton(text="🧩 38 Pertanyaan Inti", callback_data="menu:38:xauusd")
        ],
        [
            InlineKeyboardButton(text="🔙 Kembali ke Menu Utama", callback_data="menu:back")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def register_handlers(dp: Dispatcher, admin_id: int, sr_monitor=None):
    """
    Registers all bot commands and callback query handlers.
    Secured by comparing chat ID or user ID with admin_id.
    """
    def is_authorized(user_or_chat_id: int) -> bool:
        if not admin_id or admin_id == 0:
            return True
        if user_or_chat_id == admin_id:
            return True
        return False

    async def do_send_sr(target: Message):
        if not sr_monitor:
            await target.answer("⚠️ S/R Monitor Engine belum diinisialisasi.")
            return
        now_wib = datetime.now(WIB)
        try:
            await sr_monitor.check_all_symbols(now_wib)
            summary = sr_monitor.get_current_status_summary()
            photo_bytes = sr_monitor.generate_current_photo_card()
            input_file = BufferedInputFile(photo_bytes, filename="bloomberg_live.png")
            await target.answer_photo(photo=input_file, caption=summary, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error on sr popup: {e}")
            summary = sr_monitor.get_current_status_summary()
            await target.answer(summary, parse_mode="HTML")

    async def do_send_engine(target: Message):
        now_wib = datetime.now(WIB)
        try:
            from backend.telegram.precision_engine import PrecisionTradingEngine
            engine = getattr(sr_monitor, "precision_engine", None)
            if not engine:
                engine = PrecisionTradingEngine()
                
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, engine.fetch_live_data)
            photo_bytes = engine.generate_current_card_bytes(now_wib)
            summary = engine.get_current_summary()
            
            input_file = BufferedInputFile(photo_bytes, filename="xedy_precision_engine.png")
            await target.answer_photo(photo=input_file, caption=summary, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error generating precision engine: {e}")
            await target.answer(f"⚠️ Gagal memuat Precision Trading Engine: {e}")

    async def do_send_flow(target: Message):
        now_wib = datetime.now(WIB)
        try:
            from backend.telegram.money_flow_engine import MoneyFlowRadarEngine
            engine = getattr(sr_monitor, "money_flow_engine", None)
            if not engine:
                engine = MoneyFlowRadarEngine()
                
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, engine.fetch_live_market_data)
            photo_bytes = engine.generate_current_radar_card(now_wib)
            summary = engine.get_current_radar_summary()
            
            input_file = BufferedInputFile(photo_bytes, filename="money_flow_radar.png")
            await target.answer_photo(photo=input_file, caption=summary, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error generating money flow radar: {e}")
    async def do_send_narrative(target: Message, symbol: str):
        try:
            from backend.telegram.narrative_engine import build_narrative_text
            loop = asyncio.get_running_loop()
            text = await loop.run_in_executor(None, build_narrative_text, symbol)
            await target.answer(text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error sending narrative for {symbol}: {e}")
            await target.answer(f"⚠️ Gagal menyusun narasi untuk {symbol}: {e}")

    async def do_send_38_questions(target: Message, symbol: str = "XAUUSD"):
        try:
            from backend.telegram.narrative_engine import build_38_questions_text
            loop = asyncio.get_running_loop()
            parts = await loop.run_in_executor(None, build_38_questions_text, symbol)
            for p in parts:
                await target.answer(p, parse_mode="HTML")
                await asyncio.sleep(0.4)
        except Exception as e:
            logger.error(f"Error sending 38 questions analysis for {symbol}: {e}")
            await target.answer(f"⚠️ Gagal menyusun 38 Pertanyaan Inti: {e}")

    async def do_send_legend(target: Message):
        legend_text = (
            "🏛️ <b>LEGEND SIGNAL GRADE &amp; FINAL STATUS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎖️ <b>1. SIGNAL GRADE (KUALITAS SINYAL):</b>\n"
            "• 🟢 <b>[A+] STRONG ENTRY</b>\n"
            "   Confidence ≥ 90% | Action ≥ 85 | SNR Ekstrem (≤ 15% / ≥ 85%) | Vol ≥ 65% | Delta ±15%.\n"
            "   <i>Sinyal langka &amp; sangat presisi. Hanya dieksekusi saat seluruh filter lolos sempurna.</i>\n\n"
            "• 🟢 <b>[A] ENTRY</b>\n"
            "   Confidence ≥ 85% | Action ≥ 75 | Major filters confirmed.\n"
            "   <i>Sinyal entri standar institusional yang terverifikasi kuat.</i>\n\n"
            "• 🟡 <b>[B] SETUP / WATCH</b>\n"
            "   Confidence ≥ 75% | Action ≥ 65.\n"
            "   <i>Peluang potensial sedang terbentuk, pantau konfirmasi candle rejection.</i>\n\n"
            "• 🟠 <b>[C] WAIT</b>\n"
            "   Confidence ≥ 65% | Action ≥ 50.\n"
            "   <i>Data belum lengkap, risiko tinggi jika masuk sekarang.</i>\n\n"
            "• 🔴 <b>[D] NO TRADE</b>\n"
            "   Confidence &lt; 65% atau Action &lt; 50.\n"
            "   <i>Dilarang open posisi. Disiplin menunggu kondisi pasar optimal.</i>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🚦 <b>2. FINAL STATUS (15 HIERARKI PRIORITAS):</b>\n"
            "1. <b>STRONG BUY</b> : Dekat Support (≤ 15%) + Buy Vol ≥ 65% + Delta +15% + Conf ≥ 90\n"
            "2. <b>STRONG SELL</b> : Dekat Resistance (≥ 85%) + Sell Vol ≥ 65% + Delta -15% + Conf ≥ 90\n"
            "3. <b>BREAKOUT BUY</b> : Harga menembus Resistance + Buy Vol ≥ 60% + Trend UP\n"
            "4. <b>BREAKDOWN</b> : Harga menembus Support + Sell Vol ≥ 60% + Trend DOWN\n"
            "5. <b>REVERSAL UP</b> : Zona Support (≤ 20%) + Reversal Score ≥ 60 + Buy flow aktif\n"
            "6. <b>REVERSAL DOWN</b> : Zona Resistance (≥ 80%) + Reversal Score ≥ 60 + Sell flow aktif\n"
            "7. <b>BUY</b> : Zona Support (≤ 20%) + Buy dominan + Conf ≥ 70 + Action ≥ 75\n"
            "8. <b>SELL</b> : Zona Resistance (≥ 80%) + Sell dominan + Conf ≥ 70 + Action ≥ 75\n"
            "9. <b>BREAKOUT WATCH</b> : Mendekati Resistance (≥ 70%) + Buy volume aktif\n"
            "10. <b>BREAKDOWN RISK</b> : Mendekati Support (≤ 30%) + Sell volume aktif\n"
            "11. <b>BUY SETUP</b> : Dekat Support atau Action ≥ 65 dengan bias beli aktif\n"
            "12. <b>SELL SETUP</b> : Dekat Resistance atau Action ≥ 65 dengan bias jual aktif\n"
            "13. <b>BUY PRESSURE</b> : Aliran volume beli kuat (&gt; 55% / &gt; 65%)\n"
            "14. <b>SELL PRESSURE</b> : Aliran volume jual kuat (&gt; 55% / &gt; 65%)\n"
            "15. <b>WAIT / NO TRADE</b> : Konsolidasi netral tanpa konfirmasi setup\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 <i>Ketik /popup untuk melihat kartu Bloomberg live dengan legend visual di bagian bawah.</i>"
        )
        await target.answer(legend_text, parse_mode="HTML")

    async def do_send_setsnr_info(target: Message):
        if not sr_monitor:
            await target.answer("⚠️ S/R Monitor Engine belum diinisialisasi.")
            return
        lines = [
            "⚙️ <b>PENGATURAN LEVEL SUPPORT &amp; RESISTANCE (S/R)</b>",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "<b>Level S/R Aktif Saat Ini:</b>"
        ]
        for sym, cfg in sr_monitor.CONFIG.items():
            digits = cfg["digits"]
            lines.append(f"• <b>{cfg['name']}</b> ({cfg['subtitle']}): S = <code>{cfg['support']:,.{digits}f}</code> | R = <code>{cfg['resistance']:,.{digits}f}</code>")
        
        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━",
            "<b>Cara Merubah Level S/R:</b>",
            "Ketik perintah: <code>/setsnr &lt;PAIR&gt; &lt;SUPPORT&gt; &lt;RESISTANCE&gt;</code>\n",
            "<b>Contoh:</b>",
            "• <code>/setsnr GOLD 3855 4230</code>",
            "• <code>/setsnr USDJPY 156.20 159.40</code>",
            "• <code>/setsnr EURUSD 1.1100 1.1320</code>",
            "• <code>/setsnr OIL 87.90 99.10</code>\n",
            "💡 <i>Setelah diupdate, kartu visual Bloomberg terbaru akan langsung dikirimkan seketika!</i>"
        ])
        await target.answer("\n".join(lines), parse_mode="HTML")

    # =========================================================================
    # COMMAND HANDLERS
    # =========================================================================

    @dp.message(Command("id"))
    async def cmd_id(message: Message):
        await message.answer(
            f"🆔 <b>Chat ID:</b> <code>{message.chat.id}</code>\n"
            f"👤 <b>User ID:</b> <code>{message.from_user.id}</code>\n"
            f"Rezim Chat: <b>{message.chat.type.upper()}</b>",
            parse_mode="HTML"
        )

    @dp.message(Command("menu", "start", "help"))
    async def cmd_menu(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
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
        await message.answer(menu_text, reply_markup=get_dashboard_menu_keyboard(), parse_mode="HTML")

    @dp.message(Command("legend", "rules", "grade", "rule"))
    async def cmd_legend(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        await do_send_legend(message)
        
    @dp.message(Command("sr", "popup", "dashboard", "now"))
    async def cmd_popup(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        await do_send_sr(message)

    @dp.message(Command("flow", "moneyflow", "radar"))
    async def cmd_flow(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        await do_send_flow(message)

    @dp.message(Command("engine", "precision", "xedyai", "master"))
    async def cmd_engine(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        await do_send_engine(message)

    @dp.message(Command("setsnr", "snr", "ubahsnr"))
    async def cmd_setsnr(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        if not sr_monitor:
            await message.answer("⚠️ S/R Monitor Engine belum diinisialisasi.")
            return

        text = message.text.strip()
        parts = text.split()

        if len(parts) >= 4:
            raw_sym = parts[1]
            try:
                supp = float(parts[2].replace(",", "."))
                res = float(parts[3].replace(",", "."))
            except ValueError:
                await message.answer("⚠️ Format angka tidak valid. Contoh: <code>/setsnr GOLD 3900 4250</code>", parse_mode="HTML")
                return

            success, msg = sr_monitor.set_snr(raw_sym, supp, res)
            if success:
                now_wib = datetime.now(WIB)
                try:
                    await sr_monitor.check_all_symbols(now_wib)
                    summary = sr_monitor.get_current_status_summary()
                    photo_bytes = sr_monitor.generate_current_photo_card()
                    input_file = BufferedInputFile(photo_bytes, filename="snr_updated.png")
                    full_caption = f"{msg}\n\n{summary}"
                    await message.answer_photo(photo=input_file, caption=full_caption, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Error rendering after set_snr: {e}")
                    await message.answer(msg, parse_mode="HTML")
            else:
                await message.answer(msg, parse_mode="HTML")
        else:
            await do_send_setsnr_info(message)

    @dp.message(Command("status"))
    async def cmd_status(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        if sr_monitor:
            summary = sr_monitor.get_current_status_summary()
            await message.answer(summary, parse_mode="HTML")
        else:
            await message.answer("⚠️ S/R Monitor Engine belum diinisialisasi.")

    @dp.message(Command("nr", "narasi", "narrative"))
    async def cmd_narrative(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        parts = message.text.strip().split()
        if len(parts) >= 2:
            raw_sym = parts[1]
            await do_send_narrative(message, raw_sym)
        else:
            prompt_text = (
                "📜 <b>XEDY AI — INSTITUTIONAL MARKET NARRATIVE</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Pilih instrumen di bawah ini atau ketik langsung perintah:\n\n"
                "• <code>/nr xauusd</code> — Narasi komprehensif Gold Spot\n"
                "• <code>/nr usdjpy</code> — Narasi komprehensif USD/JPY\n"
                "• <code>/nr eurusd</code> — Narasi komprehensif EUR/USD\n"
                "• <code>/nr gbpusd</code> — Narasi komprehensif GBP/USD\n"
                "• <code>/nr oil</code> — Narasi komprehensif WTI Crude Oil\n\n"
                "<i>Menjawab 12 pertanyaan kausal mendalam (Makro, Kebijakan, Geopolitik, Yield, Flow, Teknikal, S/R & Parameter OP/SL/TP).</i>\n\n"
                "💡 <i>Ketik <code>/38 xauusd</code> untuk analisis lengkap 38 Pertanyaan Inti.</i>"
            )
            await message.answer(prompt_text, reply_markup=get_narrative_menu_keyboard(), parse_mode="HTML")

    @dp.message(Command("38", "qa", "pertanyaan38", "analisis38"))
    async def cmd_38_questions(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        parts = message.text.strip().split()
        sym = parts[1] if len(parts) >= 2 else "XAUUSD"
        await do_send_38_questions(message, sym)

    # =========================================================================
    # CALLBACK QUERY HANDLER (INTERACTIVE BUTTONS)
    # =========================================================================
    @dp.callback_query()
    async def on_menu_callback(callback: CallbackQuery):
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else user_id
        if not is_authorized(chat_id) and not is_authorized(user_id):
            await callback.answer("⚠️ Akses tidak diizinkan.", show_alert=True)
            return

        action = callback.data
        target_msg = callback.message

        if action == "menu:sr":
            await callback.answer("⏳ Memuat Bloomberg S/R Dashboard...")
            await do_send_sr(target_msg)

        elif action == "menu:engine":
            await callback.answer("⏳ Menganalisis 5 Pair dengan Multi-Agent Engine...")
            await do_send_engine(target_msg)

        elif action == "menu:flow":
            await callback.answer("⏳ Mengumpulkan Capital Money Flow Data...")
            await do_send_flow(target_msg)

        elif action == "menu:nr_menu":
            await callback.answer("📜 Membuka menu narasi pasar...")
            prompt_text = (
                "📜 <b>PILIH NARASI PASAR INSTITUTIONAL</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Pilih instrumen yang ingin dianalisis secara kausal mendalam:"
            )
            await target_msg.answer(prompt_text, reply_markup=get_narrative_menu_keyboard(), parse_mode="HTML")

        elif action.startswith("menu:nr:"):
            sym = action.split("menu:nr:")[1]
            await callback.answer(f"⏳ Menyusun narasi {sym.upper()}...")
            await do_send_narrative(target_msg, sym)

        elif action.startswith("menu:38:"):
            sym = action.split("menu:38:")[1] if len(action.split("menu:38:")) > 1 else "XAUUSD"
            await callback.answer(f"⏳ Menyusun 38 Pertanyaan Inti {sym.upper()}...")
            await do_send_38_questions(target_msg, sym)

        elif action == "menu:back":
            await callback.answer()
            menu_text = (
                "🏛️ <b>XEDY AI MISSION CONTROL — EXECUTIVE MENU</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Pilih menu interaktif di bawah ini:"
            )
            await target_msg.answer(menu_text, reply_markup=get_dashboard_menu_keyboard(), parse_mode="HTML")

        elif action == "menu:setsnr":
            await callback.answer("⚙️ Membuka parameter S/R aktif...")
            await do_send_setsnr_info(target_msg)

        elif action == "menu:legend":
            await callback.answer("📖 Memuat panduan Grade & Status...")
            await do_send_legend(target_msg)

        elif action == "menu:status":
            await callback.answer("📈 Memuat ringkasan harga...")
            if sr_monitor:
                summary = sr_monitor.get_current_status_summary()
                await target_msg.answer(summary, parse_mode="HTML")

        elif action == "menu:all":
            await callback.answer("🚀 Mengirim seluruh dashboard (3-in-1)...")
            await do_send_sr(target_msg)
            await do_send_engine(target_msg)
            await do_send_flow(target_msg)

        else:
            await callback.answer()

    logger.info("Telegram handlers registered successfully.")
