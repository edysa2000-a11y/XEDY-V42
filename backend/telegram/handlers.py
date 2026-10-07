import logging
from datetime import datetime, timezone, timedelta
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
import os

logger = logging.getLogger("xedy.telegram.handlers")
WIB = timezone(timedelta(hours=7))

def register_handlers(dp: Dispatcher, admin_id: int, sr_monitor=None):
    """
    Registers all bot commands.
    Secured by comparing chat ID or user ID with admin_id.
    """
    def is_authorized(message: Message) -> bool:
        if not admin_id or admin_id == 0:
            return True
        # Allow if chat is the authorized group/channel or direct from admin
        if message.chat.id == admin_id or message.from_user.id == admin_id:
            return True
        return False
    
    @dp.message(Command("id"))
    async def cmd_id(message: Message):
        await message.answer(
            f"🆔 <b>Chat ID:</b> <code>{message.chat.id}</code>\n"
            f"👤 <b>User ID:</b> <code>{message.from_user.id}</code>\n"
            f"Rezim Chat: <b>{message.chat.type.upper()}</b>",
            parse_mode="HTML"
        )

    @dp.message(Command("start", "help"))
    async def cmd_start(message: Message):
        if not is_authorized(message):
            return
        help_text = (
            "🤖 <b>XEDY MASTER S/R MONITOR BOT ACTIVE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Memantau 4 Aset Kunci secara Real-Time:\n"
            "• 🟡 <b>GOLD</b> (XAUUSD)\n"
            "• 🔵 <b>EURUSD</b> (EUR/USD)\n"
            "• ⚫ <b>OIL</b> (WTI CRUDE)\n"
            "• 🟣 <b>USDJPY</b> (USD/JPY)\n\n"
            "<b>Perintah Tersedia:</b>\n"
            "⚡ <b>/popup</b> atau <b>/sr</b> — Request instan Dashboard 16:9 Bloomberg S/R\n"
            "🧠 <b>/engine</b> atau <b>/xedyai</b> — Request instan Dashboard 16:9 XEDY AI Precision Trading Engine (5 Aset)\n"
            "🌊 <b>/flow</b> atau <b>/moneyflow</b> — Request instan Dashboard 16:9 Money Flow Radar (Jillywosy & TradingView)\n"
            "📖 <b>/legend</b> — Penjelasan lengkap Grade (A+, A, B, C, D) & 15 Final Status\n"
            "⚙️ <b>/setsnr</b> — Merubah level Support & Resistance lewat Telegram\n"
            "📊 <b>/status</b> — Ringkasan teks metrik harga & status S/R\n"
            "🆔 <b>/id</b> — Mengetahui Chat ID & User ID\n\n"
            "💡 <i>Update otomatis terkirim setiap 15 menit (S/R Card) dan setiap 30 menit (XEDY AI Precision Engine & Money Flow Radar), serta alert instan jika harga mengenai batas SNR.</i>"
        )
        await message.answer(help_text, parse_mode="HTML")

    @dp.message(Command("legend", "rules", "grade", "rule"))
    async def cmd_legend(message: Message):
        if not is_authorized(message):
            return
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
        await message.answer(legend_text, parse_mode="HTML")
        
    @dp.message(Command("sr", "popup", "dashboard", "now"))
    async def cmd_popup(message: Message):
        """
        Request popup on demand without waiting for scheduled interval.
        Fetches fresh cloud prices and immediately generates the latest 16:9 card.
        """
        if not is_authorized(message):
            return
        if not sr_monitor:
            await message.answer("⚠️ S/R Monitor Engine belum diinisialisasi.")
            return

        now_wib = datetime.now(WIB)
        try:
            # Rescan live market immediately from cloud
            await sr_monitor.check_all_symbols(now_wib)
            summary = sr_monitor.get_current_status_summary()
            photo_bytes = sr_monitor.generate_current_photo_card()
            input_file = BufferedInputFile(photo_bytes, filename="bloomberg_live.png")
            await message.answer_photo(photo=input_file, caption=summary, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error on on-demand popup: {e}")
            summary = sr_monitor.get_current_status_summary()
            await message.answer(summary, parse_mode="HTML")

    @dp.message(Command("flow", "moneyflow", "radar"))
    async def cmd_flow(message: Message):
        """
        Request Money Flow Radar card on demand.
        Fetches live data matching Jillywosy & TradingView and returns the 16:9 card.
        """
        if not is_authorized(message):
            return
        
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
            await message.answer_photo(photo=input_file, caption=summary, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error generating money flow radar on-demand: {e}")
            await message.answer(f"⚠️ Gagal memuat Money Flow Radar: {e}")

    @dp.message(Command("engine", "precision", "xedyai", "master"))
    async def cmd_engine(message: Message):
        """
        Request XEDY AI Precision Trading Engine 1-page 16:9 dashboard card on demand.
        Executes Multi-Agent analysis across 5 assets and returns the decision matrix.
        """
        if not is_authorized(message):
            return
        
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
            await message.answer_photo(photo=input_file, caption=summary, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error generating precision engine on-demand: {e}")
            await message.answer(f"⚠️ Gagal memuat Precision Trading Engine: {e}")

    @dp.message(Command("setsnr", "snr", "ubahsnr"))
    async def cmd_setsnr(message: Message):
        """
        Set or update Support & Resistance for any pair directly from Telegram.
        Usage: /setsnr <PAIR> <SUPPORT> <RESISTANCE>
        """
        if not is_authorized(message):
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
            # Display current SNR levels and clear instructions
            lines = [
                "⚙️ <b>PENGATURAN LEVEL SUPPORT & RESISTANCE (S/R)</b>",
                "━━━━━━━━━━━━━━━━━━━━━━",
                "<b>Level S/R Aktif Saat Ini:</b>"
            ]
            for sym, cfg in sr_monitor.CONFIG.items():
                digits = cfg["digits"]
                lines.append(f"• <b>{cfg['name']}</b> ({cfg['subtitle']}): S = <code>{cfg['support']:,.{digits}f}</code> | R = <code>{cfg['resistance']:,.{digits}f}</code>")
            
            lines.extend([
                "━━━━━━━━━━━━━━━━━━━━━━",
                "<b>Cara Merubah Level:</b>",
                "Ketik: <code>/setsnr &lt;PAIR&gt; &lt;SUPPORT&gt; &lt;RESISTANCE&gt;</code>\n",
                "<b>Contoh Perintah:</b>",
                "• <code>/setsnr GOLD 3900 4250</code>",
                "• <code>/setsnr USDJPY 156.50 159.80</code>",
                "• <code>/setsnr EURUSD 1.1120 1.1350</code>",
                "• <code>/setsnr OIL 88.00 98.50</code>\n",
                "💡 <i>Setelah diupdate, kartu visual Bloomberg terbaru akan langsung dikirimkan seketika!</i>"
            ])
            await message.answer("\n".join(lines), parse_mode="HTML")

    @dp.message(Command("status"))
    async def cmd_status(message: Message):
        if not is_authorized(message):
            return
        if sr_monitor:
            summary = sr_monitor.get_current_status_summary()
            await message.answer(summary, parse_mode="HTML")
        else:
            await message.answer("⚠️ S/R Monitor Engine belum diinisialisasi.")

    logger.info("Telegram handlers registered successfully.")

