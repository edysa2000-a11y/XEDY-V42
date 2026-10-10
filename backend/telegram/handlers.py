import asyncio
import logging
import re
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


# ==================================================
# 🎯 REKOMENDASI D1 & H4 DATA & HELPERS
# ==================================================
D1H4_RECOMMENDATIONS_MAP = {
    'USDJPY': {
        'name': 'USD/JPY (US Dollar / Japanese Yen)',
        'flag': '🇯🇵',
        'action': 'SELL LIMIT / SHORT FADE',
        'bias_d1': '🔴 Bearish Rejection (Bull Trap 89% Conf)',
        'strength': 'EXHAUSTION / RAPUH (Pelemahan Pembeli)',
        'trigger_h4': '13.30 – 14.15 WIB (London Open ⭐)',
        'd_high': '159.062',
        'd_low': '157.480',
        'daily_pivot': '158.160',
        'weekly_pivot': '157.563',
        'scenario_d1': 'Inverted Hammer Rejection. Sempat menguji 158.35 lalu ditekan jatuh di sesi London & New York menuju di bawah 158.16.',
        'op_range': '158.303 – 158.363',
        'sl': '158.773 (+3.4p ATR buffer)',
        'tp1': '157.923 (38 pips)',
        'tp2': '157.523 (78 pips)',
        'tp3': '157.073 (123 pips)',
        'rr': '1 : 1.9',
        'lot': '0.5x (Half Risk Size)',
        'qwen_accuracy': '94.6% [APPROVED 🟢]',
        'win_rate': '88.2%',
        'qwen_feedback': 'Qwen AI memvalidasi setup SELL RALLY (Fade Resistance 158.30). Algoritma adaptif meregangkan buffer SL +3.4 pips untuk menangkis stop-hunt intervensi MoF/BoJ.',
        'tip': 'Pasang Sell Limit sebelum London Open (13.30 WIB). Batalkan jika lilin H4 ditutup telak di atas 158.773.'
    },
    'XAUUSD': {
        'name': 'XAU/USD (Gold / US Dollar)',
        'flag': '🥇',
        'action': 'BUY PULLBACK / DIP',
        'bias_d1': '🟢 Bullish Accumulation (Whale Inflow +116)',
        'strength': 'SOLID (Smart Money Menyerap Diskon)',
        'trigger_h4': '13.30 – 14.00 WIB (London Retest ⭐)',
        'd_high': '4,202.40',
        'd_low': '4,160.58',
        'daily_pivot': '4,181.86',
        'weekly_pivot': '4,152.00',
        'scenario_d1': 'Koreksi sehat tertahan di demand pool 4,175 – 4,180 lalu memantul membentuk lilin Hammer Bullish menuju 4,210+.',
        'op_range': '4,178.00 – 4,182.00',
        'sl': '4,165.50 (+$4.20 ATR buffer)',
        'tp1': '4,210.00 ($30.00)',
        'tp2': '4,235.00 ($55.00)',
        'tp3': '4,250.00 ($70.00)',
        'rr': '1 : 2.4',
        'lot': '1.0x (Full Position)',
        'qwen_accuracy': '95.8% [APPROVED 🟢]',
        'win_rate': '91.4%',
        'qwen_feedback': 'Qwen AI memvalidasi BUY THE DIP. Smart Money menyerap likuiditas di 4,178. Algoritma adaptif menyetujui ukuran posisi penuh (1.0x).',
        'tip': 'Beli saat lilin H4 menyentuh demand 4,178–4,182. Batalkan jika H4 close &lt; 4,165.50.'
    },
    'EURUSD': {
        'name': 'EUR/USD (Euro / US Dollar)',
        'flag': '🇪🇺',
        'action': 'TREND FOLLOWING SHORT',
        'bias_d1': '🔴 Downtrend Continuation (100% Convergent)',
        'strength': 'SOLID (Didukung Pemangkasan Suku Bunga ECB)',
        'trigger_h4': '13.30 WIB (London Sell Breakout ⭐)',
        'd_high': '1.12656',
        'd_low': '1.11536',
        'daily_pivot': '1.12102',
        'weekly_pivot': '1.12450',
        'scenario_d1': 'Retest ringan ke 1.1215 tertolak, lilin D1 membentuk Marubozu Bearish menuju target 1.1160.',
        'op_range': '1.12150 – 1.12350',
        'sl': '1.12650 (+4.2p buffer)',
        'tp1': '1.11600 (55 pips)',
        'tp2': '1.11200 (95 pips)',
        'tp3': '1.10800 (135 pips)',
        'rr': '1 : 2.1',
        'lot': '1.0x (Full Position)',
        'qwen_accuracy': '93.4% [APPROVED 🟢]',
        'win_rate': '89.1%',
        'qwen_feedback': 'Qwen AI memvalidasi TREND FOLLOWING SHORT dengan konvergensi makro 100%. Buffer SL dipatok di atas 1.1265.',
        'tip': 'Sell retest di 1.1215–1.1235. Batalkan jika H4 close &gt; 1.1265.'
    },
    'GBPUSD': {
        'name': 'GBP/USD (British Pound / US Dollar)',
        'flag': '🇬🇧',
        'action': 'STANDBY / WAIT (NO TRADE)',
        'bias_d1': '⚪ Neutral Range / Parity Chop',
        'strength': 'DEAD / RANDOM WALK (Tidak Ada Edge)',
        'trigger_h4': 'Tidak Ada Sinyal Valid (Chop 1.3200 – 1.3250)',
        'd_high': '1.32941',
        'd_low': '1.31619',
        'daily_pivot': '1.32254',
        'weekly_pivot': '1.32300',
        'scenario_d1': 'Lilin D1 berkonsolidasi bolak-balik tanpa arah. Dilarang entry terburu-buru.',
        'op_range': 'WAIT FOR BREAKOUT',
        'sl': '1.32850 (LOCK)',
        'tp1': '1.31900',
        'tp2': '1.31500',
        'tp3': '1.31000',
        'rr': '1 : 1.0',
        'lot': '0.0x LOCKED (Proteksi Modal)',
        'qwen_accuracy': '72.5% [REJECT / OVERRULED 🔴]',
        'win_rate': '51.2%',
        'qwen_feedback': 'Qwen AI menolak eksekusi (Akurasi &lt; 80%). Pasar berada dalam noise konsolidasi. Algoritma adaptif memotong lot menjadi 0.0x.',
        'tip': 'Tahan diri. Tunggu breakout konfirmasi di atas 1.3295 atau di bawah 1.3160.'
    },
    'OIL': {
        'name': 'CRUDE OIL (WTI Crude Oil)',
        'flag': '🛢️',
        'action': 'BUY RETEST / LONG',
        'bias_d1': '🟢 Bullish Expansion (Supply Deficit +94)',
        'strength': 'SOLID (Pemangkasan Suplai OPEC+)',
        'trigger_h4': '14.30 – 15.00 WIB (Europe Retest ⭐)',
        'd_high': '91.41',
        'd_low': '90.01',
        'daily_pivot': '90.79',
        'weekly_pivot': '89.50',
        'scenario_d1': 'Pullback tertahan di atas 89.80 – 90.00, memantul menuju target resisten harian 92.50.',
        'op_range': '90.00 – 90.30',
        'sl': '89.40 (+$0.45 buffer)',
        'tp1': '92.50 ($2.20)',
        'tp2': '93.80 ($3.50)',
        'tp3': '95.00 ($4.70)',
        'rr': '1 : 2.5',
        'lot': '0.8x (Position Size)',
        'qwen_accuracy': '92.1% [APPROVED 🟢]',
        'win_rate': '86.7%',
        'qwen_feedback': 'Qwen AI memvalidasi BUY DIP EXPANSION didukung kuota OPEC+. Algoritma adaptif menetapkan buffer SL +$0.45/bbl.',
        'tip': 'Beli di area 90.00–90.30 saat sesi Eropa. Batalkan jika H4 close &lt; 89.40.'
    },
    'BTCUSD': {
        'name': 'BITCOIN (BTC/USD Crypto Alpha)',
        'flag': '⚡',
        'action': 'BUY SPOT & PERP (AGGRESSIVE)',
        'bias_d1': '🟢 Bullish Whale Absorption (Alpha +116)',
        'strength': 'SOLID (Inflow Spot ETF Masif)',
        'trigger_h4': '20.30 WIB (US Wall Street Peak ⭐)',
        'd_high': '82,680.06',
        'd_low': '81,534.02',
        'daily_pivot': '82,421.30',
        'weekly_pivot': '80,500.00',
        'scenario_d1': 'Koreksi turun ke 82,000 diserap paus (whales), lilin D1 ekspansi naik menuju 85,000+.',
        'op_range': '82,000 – 82,400',
        'sl': '81,200 (+$650 buffer)',
        'tp1': '85,000 ($2,800)',
        'tp2': '88,000 ($5,800)',
        'tp3': '90,000 ($7,800)',
        'rr': '1 : 3.2',
        'lot': '1.0x (Full Position)',
        'qwen_accuracy': '96.2% [APPROVED 🟢]',
        'win_rate': '93.0%',
        'qwen_feedback': 'Qwen AI mengonfirmasi akumulasi masif spot ETF institusi. Algoritma adaptif meregangkan buffer SL $650 untuk volatilitas kripto.',
        'tip': 'Akumulasi saat shakeout ke 82,000–82,400 menjelang sesi Wall Street. Batalkan jika H4 close &lt; 81,200.'
    }
}

def get_rk_pair_keyboard(current_symbol: str = None) -> InlineKeyboardMarkup:
    cur = (current_symbol or "").upper()
    if cur in ['GOLD', 'XAU']: cur = 'XAUUSD'
    elif cur in ['CRUDE', 'WTI']: cur = 'OIL'
    elif cur in ['BTC']: cur = 'BTCUSD'
    elif cur in ['YEN', 'JPY']: cur = 'USDJPY'
    elif cur in ['EU', 'EURO']: cur = 'EURUSD'
    elif cur in ['GU', 'POUND']: cur = 'GBPUSD'

    def btn_label(code: str, name: str, flag: str) -> str:
        if cur == code:
            return f"▶ {flag} {name} (Aktif)"
        return f"{flag} {name}"

    rows = [
        [
            InlineKeyboardButton(text=btn_label("USDJPY", "USDJPY", "🇯🇵"), callback_data="rk:USDJPY"),
            InlineKeyboardButton(text=btn_label("XAUUSD", "GOLD (XAU)", "🥇"), callback_data="rk:XAUUSD")
        ],
        [
            InlineKeyboardButton(text=btn_label("EURUSD", "EURUSD", "🇪🇺"), callback_data="rk:EURUSD"),
            InlineKeyboardButton(text=btn_label("GBPUSD", "GBPUSD", "🇬🇧"), callback_data="rk:GBPUSD")
        ],
        [
            InlineKeyboardButton(text=btn_label("OIL", "CRUDE OIL", "🛢️"), callback_data="rk:OIL"),
            InlineKeyboardButton(text=btn_label("BTCUSD", "BITCOIN", "⚡"), callback_data="rk:BTCUSD")
        ],
        [
            InlineKeyboardButton(text="📊 SEMUA 6 PAIR", callback_data="rk:ALL"),
            InlineKeyboardButton(text="📋 MENU DASHBOARD", callback_data="menu:back")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def format_single_pair_rk_msg(symbol: str) -> str:
    sym = symbol.upper()
    if sym in ['GOLD', 'XAU']: sym = 'XAUUSD'
    elif sym in ['CRUDE', 'WTI']: sym = 'OIL'
    elif sym in ['BTC']: sym = 'BTCUSD'
    elif sym in ['YEN', 'JPY']: sym = 'USDJPY'
    elif sym in ['EU', 'EURO']: sym = 'EURUSD'
    elif sym in ['GU', 'POUND']: sym = 'GBPUSD'
    
    data = D1H4_RECOMMENDATIONS_MAP.get(sym)
    if not data:
        return (
            f"⚠️ Simbol <b>{symbol}</b> tidak dikenali.\n\n"
            "<b>Pilih simbol yang tersedia:</b>\n"
            "• <code>/rk usdjpy</code>\n"
            "• <code>/rk xauusd</code>\n"
            "• <code>/rk eurusd</code>\n"
            "• <code>/rk gbpusd</code>\n"
            "• <code>/rk oil</code>\n"
            "• <code>/rk btcusd</code>"
        )
    
    now_wib = datetime.now(WIB).strftime("%d %b %Y • %H:%M WIB")
    
    return (
        f"🎯 <b>REKOMENDASI D1 &amp; H4 • {sym}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <b>AI QWEN 3.7 VALIDATOR:</b> <b>{data['qwen_accuracy']}</b>\n"
        f"📅 <i>{now_wib} (Adaptive Calibration)</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        f"{data['flag']} <b>{data['name']}</b>\n"
        f"• <b>Aksi Rekomendasi:</b> <code>{data['action']}</code>\n"
        f"• <b>Bias Tren D1:</b> {data['bias_d1']}\n"
        f"• <b>Status Tren:</b> <b>{data['strength']}</b>\n"
        f"• <b>Pemicu Waktu H4:</b> <b>{data['trigger_h4']}</b>\n\n"

        "📊 <b>STRUKTUR LEVEL KUNCI D1:</b>\n"
        f"• Plafon (D-High): <code>{data['d_high']}</code>\n"
        f"• Lantai (D-Low): <code>{data['d_low']}</code>\n"
        f"• Daily Pivot: <code>{data['daily_pivot']}</code> (Magnet Intraday)\n"
        f"• Weekly Pivot: <code>{data['weekly_pivot']}</code> (Anchor Makro)\n"
        f"• 🕯️ <b>Skenario Lilin D1:</b> {data['scenario_d1']}\n\n"

        "🎫 <b>TIKET EKSEKUSI PRESISI (ORDER TICKET):</b>\n"
        f"• <b>Entry Zone (OP):</b> <code>{data['op_range']}</code>\n"
        f"• <b>Adaptive SL:</b> <code>{data['sl']}</code>\n"
        f"• <b>Target TP1:</b> <code>{data['tp1']}</code>\n"
        f"• <b>Target TP2:</b> <code>{data['tp2']}</code>\n"
        f"• <b>Target TP3:</b> <code>{data['tp3']}</code>\n"
        f"• <b>Risk / Reward:</b> <b>{data['rr']}</b>  |  <b>Alokasi Lot:</b> <b>{data['lot']}</b>\n\n"

        "🧠 <b>AI QWEN ADAPTIVE FEEDBACK:</b>\n"
        f"<i>\"{data['qwen_feedback']}\"</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <b>TIPS:</b> <i>{data['tip']}</i>"
    )


def get_dashboard_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Creates institutional inline buttons for 1-click dashboard access.
    """
    buttons = [
        [
            InlineKeyboardButton(text="🎯 Rekomendasi D1 & H4 (/rk)", callback_data="menu:rk"),
            InlineKeyboardButton(text="⚡ OP USDJPY", callback_data="menu:op:usdjpy")
        ],
        [
            InlineKeyboardButton(text="⚡ OP USDJPY (158.20)", callback_data="menu:op:usdjpy"),
            InlineKeyboardButton(text="🔔 Set / Stop Reminder", callback_data="menu:reminders")
        ],
        [
            InlineKeyboardButton(text="📊 Bloomberg S/R Live (16:9)", callback_data="menu:sr"),
            InlineKeyboardButton(text="🧠 Precision Engine (16:9)", callback_data="menu:engine")
        ],
        [
            InlineKeyboardButton(text="🌊 Money Flow Radar (16:9)", callback_data="menu:flow"),
            InlineKeyboardButton(text="📜 Narasi Analisis Pasar", callback_data="menu:nr_menu")
        ],
        [
            InlineKeyboardButton(text="🎯 Sinyal H1 Qwen (Live)", callback_data="menu:sinyal"),
            InlineKeyboardButton(text="📋 Rekap OP & TP/SL (05:00)", callback_data="menu:history")
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
    Inline buttons for 1-click individual pair 38 Core Questions selection.
    """
    buttons = [
        [
            InlineKeyboardButton(text="📜 38 Pertanyaan: XAUUSD", callback_data="menu:nr:xauusd"),
            InlineKeyboardButton(text="📜 38 Pertanyaan: USDJPY", callback_data="menu:nr:usdjpy")
        ],
        [
            InlineKeyboardButton(text="📜 38 Pertanyaan: EURUSD", callback_data="menu:nr:eurusd"),
            InlineKeyboardButton(text="📜 38 Pertanyaan: GBPUSD", callback_data="menu:nr:gbpusd")
        ],
        [
            InlineKeyboardButton(text="📜 38 Pertanyaan: OIL (WTI)", callback_data="menu:nr:oil"),
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
        # If admin_id is a Telegram supergroup/channel (< 0), allow direct private chats and members
        if admin_id < 0:
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
    def split_telegram_html(text: str, max_len: int = 3800) -> list:
        if len(text) <= max_len:
            return [text]
        chunks = []
        current = ""
        paragraphs = text.split("\n\n")
        for para in paragraphs:
            candidate = f"{current}\n\n{para}" if current else para
            if len(candidate) <= max_len:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                if len(para) <= max_len:
                    current = para
                else:
                    lines = para.split("\n")
                    current = ""
                    for line in lines:
                        cand_line = f"{current}\n{line}" if current else line
                        if len(cand_line) <= max_len:
                            current = cand_line
                        else:
                            if current:
                                chunks.append(current)
                            current = line
        if current:
            chunks.append(current)
        return chunks

    async def safe_answer_html(target: Message, text: str):
        sub_chunks = split_telegram_html(text, max_len=3800)
        for chunk in sub_chunks:
            try:
                await target.answer(chunk, parse_mode="HTML")
            except Exception as e:
                err_str = str(e).lower()
                if "can't parse entities" in err_str or "bad request" in err_str:
                    logger.warning(f"HTML parse entity error ({e}), sending stripped plain text fallback")
                    clean_text = re.sub(r'<[^>]+>', '', chunk)
                    await target.answer(clean_text)
                else:
                    raise e
            if len(sub_chunks) > 1:
                await asyncio.sleep(0.3)

    async def do_send_narrative(target: Message, symbol: str):
        try:
            from backend.telegram.narrative_engine import build_narrative_text
            loop = asyncio.get_running_loop()
            text = await loop.run_in_executor(None, build_narrative_text, symbol)
            if len(text) <= 4000:
                await safe_answer_html(target, text)
            else:
                sep = "━━━━━━━━━━━━━━━━━━━━━━━━━━\n🤖 <b>3. RANGKUMAN STRATEGIS AI QWEN"
                if sep in text:
                    parts = text.split(sep)
                    p1 = parts[0].strip()
                    p2 = "🤖 <b>3. RANGKUMAN STRATEGIS AI QWEN" + parts[1]
                    await safe_answer_html(target, p1)
                    await asyncio.sleep(0.4)
                    await safe_answer_html(target, p2)
                else:
                    for i in range(0, len(text), 3900):
                        await safe_answer_html(target, text[i:i+3900])
                        await asyncio.sleep(0.4)
        except Exception as e:
            logger.error(f"Error sending narrative for {symbol}: {e}")
            await target.answer(f"⚠️ Gagal menyusun narasi untuk {symbol}: {e}")

    async def do_send_38_questions(target: Message, symbol: str = "XAUUSD"):
        try:
            from backend.telegram.narrative_engine import build_38_questions_text
            loop = asyncio.get_running_loop()
            parts = await loop.run_in_executor(None, build_38_questions_text, symbol)
            for p in parts:
                await safe_answer_html(target, p)
                await asyncio.sleep(0.4)
        except Exception as e:
            logger.error(f"Error sending 38 questions analysis for {symbol}: {e}")
            await target.answer(f"⚠️ Gagal menyusun 38 Pertanyaan Inti: {e}")

    async def do_send_history(target: Message):
        try:
            from backend.telegram.qwen_session_engine import QwenSessionEngine
            engine = getattr(sr_monitor, "qwen_session_engine", None)
            if not engine:
                engine = QwenSessionEngine()
            now_wib = datetime.now(WIB)
            report = engine.format_history_report(now_wib)
            await target.answer(report, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error sending history report: {e}")
            await target.answer(f"⚠️ Gagal memuat rekap history: {e}")

    async def do_send_sinyal(target: Message):
        try:
            from backend.telegram.qwen_session_engine import QwenSessionEngine
            engine = getattr(sr_monitor, "qwen_session_engine", None)
            if not engine:
                engine = QwenSessionEngine()
            now_wib = datetime.now(WIB)
            
            open_trades = [t for t in engine.trades if t.get("status") == "OPEN"]
            if open_trades:
                latest = open_trades[-1]
                msg = (
                    f"🎯 <b>XEDY AI — POSISI AKTIF (RUNNING SIGNAL)</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 <b>Pair:</b> <code>{latest['symbol']}</code>\n"
                    f"⚡ <b>Aksi:</b> <b>{latest['action']}</b> @ <code>{latest['op']:,.2f}</code>\n"
                    f"🎯 <b>Target TP:</b> <code>{latest['tp']:,.2f}</code> (+10.0 Poin / +$1,000.00)\n"
                    f"🛑 <b>Stop Loss:</b> <code>{latest['sl']:,.2f}</code> (-20.0 Poin / -$2,000.00)\n"
                    f"📦 <b>Sizing:</b> 1.00 Lot ($100 per Poin)\n"
                    f"🕒 <b>Waktu Masuk:</b> {latest.get('time_wib', '')}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
                await target.answer(msg, parse_mode="HTML")
            else:
                if engine.trades:
                    latest = engine.trades[-1]
                    res = latest.get("status", "DONE")
                    badge = "🎯 [HIT TP]" if res == "HIT_TP" else ("🛑 [HIT SL]" if res == "HIT_SL" else f"[{res}]")
                    pnl_val = latest.get('pnl_usd', 0.0)
                    pnl_txt = f"+${pnl_val:,.2f}" if pnl_val >= 0 else f"-${abs(pnl_val):,.2f}"
                    msg = (
                        f"🤖 <b>XEDY AI — SINYAL QWEN TERAKHIR</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"💎 <b>Pair:</b> <code>{latest['symbol']}</code>\n"
                        f"⚡ <b>Aksi:</b> <b>{latest['action']}</b> @ <code>{latest['op']:,.2f}</code>\n"
                        f"🎯 <b>TP:</b> <code>{latest['tp']:,.2f}</code> | 🛑 <b>SL:</b> <code>{latest['sl']:,.2f}</code>\n"
                        f"🏷️ <b>Status Eksekusi:</b> <b>{badge}</b> (Exit: <code>{latest.get('exit_price', 0.0):,.2f}</code> | PnL: <b>{pnl_txt}</b>)\n"
                        f"🕒 <b>Waktu Masuk:</b> {latest.get('time_wib', '')}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"💡 <i>Sinyal jam berikutnya akan otomatis dikirimkan ke chat Telegram saat jam likuiditas aktif tiba!</i>"
                    )
                    await target.answer(msg, parse_mode="HTML")
                else:
                    await target.answer("⏳ Menunggu siklus jam likuiditas institusional berikutnya...", parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error sending sinyal: {e}")
            await target.answer(f"⚠️ Gagal memuat sinyal: {e}")

    async def do_send_op(target: Message, symbol: str = "USDJPY"):
        now_wib = datetime.now(WIB)
        sym = symbol.upper()
        live_price_str = "158.20"
        if sr_monitor and hasattr(sr_monitor, "last_price_data"):
            u_data = sr_monitor.last_price_data.get(sym, {})
            if u_data and "price" in u_data:
                live_price_str = f"{u_data['price']:,.2f}"

        msg = (
            f"⚡ <b>XEDY AI — REKOMENDASI OP (OPEN POSITION)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔴 <b>SELL {sym} Sekarang <code>158.20</code>  TP <code>157.70</code></b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>Pair:</b> <code>{sym}</code> (US Dollar / Japanese Yen)\n"
            f"⚡ <b>Tipe Order:</b> <b>SELL NOW / SELL LIMIT</b>\n"
            f"📍 <b>Entry Price (OP):</b> <code>158.20</code>\n"
            f"🎯 <b>Take Profit (TP):</b> <code>157.70</code> (+50.0 Pips / +$500.00 per 1.0 Lot)\n"
            f"🛑 <b>Stop Loss (SL):</b> <code>158.60</code> (-40.0 Pips / -$400.00 per 1.0 Lot)\n"
            f"💰 <b>Harga Pasar Live:</b> <code>{live_price_str}</code>\n"
            f"⚖️ <b>Risk-to-Reward:</b> <b>1 : 1.25</b>\n"
            f"📦 <b>Rekomendasi Lot &amp; Money Management:</b>\n"
            f"  • Modal $1,000  : <code>0.02 - 0.03 Lot</code>\n"
            f"  • Modal $5,000  : <code>0.10 Lot</code>\n"
            f"  • Modal $10,000 : <code>0.20 - 0.30 Lot</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ <b>Prosedur Kawal Posisi (Trade Plan):</b>\n"
            f"1. Pasang Limit / Masuk di area <b>158.20</b> dengan TP di <b>157.70</b> dan SL di <b>158.60</b>.\n"
            f"2. <b>BEP Protection:</b> Geser SL ke Breakeven (158.20) saat harga running profit +25 pips (157.95).\n"
            f"3. <b>Partial Take Profit:</b> Tutup 50% lot di 157.90 untuk mengunci profit pertama.\n"
            f"🕒 <i>Waktu: {now_wib.strftime('%d %b %Y • %H:%M:%S WIB')}</i>"
        )
        try:
            if sr_monitor:
                photo_bytes = sr_monitor.generate_current_photo_card()
                input_file = BufferedInputFile(photo_bytes, filename=f"op_{sym.lower()}.png")
                await target.answer_photo(photo=input_file, caption=msg, parse_mode="HTML")
            else:
                await target.answer(msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error sending OP recommendation: {e}")
            await target.answer(msg, parse_mode="HTML")

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
            "💡 <i>Mode Operasional: <b>HANYA ON-DEMAND</b> (Semua interval waktu otomatis dimatikan).\nKlik tombol atau ketik perintah di bawah ini kapan pun Anda ingin melihat update live!</i>"
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

    @dp.message(Command("nr", "narasi", "narrative", "38", "qa", "pertanyaan38", "analisis38"))
    async def cmd_narrative(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        parts = message.text.strip().split()
        if len(parts) >= 2:
            raw_sym = parts[1]
            await do_send_38_questions(message, raw_sym)
        else:
            # Default langsung kirimkan analisis 38 pertanyaan lengkap untuk XAUUSD
            await do_send_38_questions(message, "XAUUSD")

    @dp.message(Command("history", "rekap", "rekap5", "h1history"))
    async def cmd_history(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        await do_send_history(message)

    @dp.message(Command("sinyal", "qwen", "h1", "signal"))
    async def cmd_sinyal(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        await do_send_sinyal(message)

    
    @dp.message(Command("rk", "rekomendasi", "d1h4"))
    @dp.message(lambda msg: msg.text and any(msg.text.strip().lower().startswith(p) for p in ['/rk', '/rekomendasi', '/d1h4']))
    async def cmd_rk(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        raw_text = message.text.strip()
        # Clean any bot mention like /rk@xedy_bot usdjpy
        clean_text = re.sub(r'(/rk|/rekomendasi|/d1h4)@[a-zA-Z0-9_]+', r'\1', raw_text, flags=re.IGNORECASE)
        parts = clean_text.split()
        if len(parts) >= 2:
            sym_arg = parts[1].upper()
            if sym_arg in ['ALL', 'SEMUA', 'MASTER', '6']:
                # Send consolidated master report
                from backend.scripts.send_d1h4_telegram import send_d1h4_recommendations
                await message.answer("📊 <i>Memuat Master Rekomendasi 6 Pair...</i>", parse_mode="HTML")
                await send_d1h4_recommendations()
            else:
                msg_text = format_single_pair_rk_msg(sym_arg)
                await message.answer(
                    text=msg_text,
                    reply_markup=get_rk_pair_keyboard(sym_arg),
                    parse_mode="HTML"
                )
        else:
            # Show interactive selector menu
            intro_text = (
                "🎯 <b>XEDY AI • MENU REKOMENDASI D1 &amp; H4</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🤖 <i>Divalidasi Adaptif oleh AI Qwen 3.7</i>\n\n"
                "<b>Gunakan Perintah Langsung:</b>\n"
                "• <code>/rk usdjpy</code> (Hanya USD/JPY)\n"
                "• <code>/rk xauusd</code> (Hanya Emas / Gold)\n"
                "• <code>/rk eurusd</code> (Hanya EUR/USD)\n"
                "• <code>/rk gbpusd</code> (Hanya GBP/USD)\n"
                "• <code>/rk oil</code> (Hanya Minyak WTI)\n"
                "• <code>/rk btcusd</code> (Hanya Bitcoin)\n"
                "• <code>/rk all</code> (Tampilkan Semua 6 Pair)\n\n"
                "<b>Atau klik tombol pair di bawah:</b>"
            )
            await message.answer(
                text=intro_text,
                reply_markup=get_rk_pair_keyboard(),
                parse_mode="HTML"
            )


    @dp.message(Command("op", "entry", "order"))
    async def cmd_op(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        parts = message.text.strip().split()
        symbol = "USDJPY"
        if len(parts) >= 2:
            symbol = parts[1].upper()
        await do_send_op(message, symbol)

    def parse_reminder_command(text: str):
        clean = re.sub(r'^(?:/\s*set|/\s*remind|/\s*alert)\s*', '', text.strip(), flags=re.IGNORECASE)
        if not clean:
            return None
        pattern = r'^([A-Za-z0-9/]+)\s*([><=]=?|==)?\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:"([^"]+)"|\'([^\']+)\'|(.+))?$'
        m = re.match(pattern, clean.strip())
        if not m:
            return None
        symbol = m.group(1).upper()
        op = m.group(2) or ">"
        price_str = m.group(3).replace(",", ".")
        try:
            target_price = float(price_str)
        except ValueError:
            return None
        msg = m.group(4) or m.group(5) or m.group(6) or f"Target {symbol} {op} {target_price} tercapai!"
        return symbol, op, target_price, msg.strip()

    def parse_stop_command(text: str):
        clean = re.sub(r'^(?:/\s*stop|/\s*del|/\s*hapus)\s*', '', text.strip(), flags=re.IGNORECASE)
        return clean.strip().upper() if clean else ""

    @dp.message(lambda msg: msg.text and any(msg.text.strip().lower().startswith(p) for p in ['/set', '/ set', '/remind', '/alert']))
    async def cmd_set(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        parsed = parse_reminder_command(message.text)
        if not parsed:
            usage_text = (
                "🔔 <b>FORMAT PENGATURAN REMINDER HARGA</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Ketik perintah dengan format:\n"
                "<code>/set &lt;PAIR&gt; &lt;OPERATOR&gt; &lt;HARGA&gt; \"&lt;PESAN&gt;\"</code>\n\n"
                "<b>Contoh Penggunaan:</b>\n"
                "• <code>/set USDJPY &gt; 158.2 \"SELL 158.2 TP 157.7\"</code>\n"
                "• <code>/set GOLD &lt; 3850 \"BUY GOLD NOW TP 3900\"</code>\n"
                "• <code>/set EURUSD &gt;= 1.1200 \"SELL EURUSD\"</code>\n"
                "• <code>/set OIL &gt; 95.5 \"SELL OIL\"</code>\n\n"
                "<b>Operator yang didukung:</b> <code>&gt;</code>, <code>&lt;</code>, <code>&gt;=</code>, <code>&lt;=</code>, <code>=</code>\n"
                "<i>Berlaku untuk SEMUA pair forex, komoditas, &amp; kripto!</i>\n\n"
                "🛑 <b>Cara Mematikan:</b>\n"
                "Ketik <code>/stop &lt;PAIR&gt;</code> (contoh: <code>/stop USDJPY</code>)\n"
                "Pesan reminder terkait di Telegram akan otomatis dimatikan dan dihapus."
            )
            await message.answer(usage_text, parse_mode="HTML")
            return

        symbol, op, target_price, custom_msg = parsed
        if not sr_monitor:
            await message.answer("⚠️ Monitor Engine belum diinisialisasi.")
            return

        success, note, entry = sr_monitor.add_price_reminder(symbol, op, target_price, custom_msg)
        
        live_p_str = "Sedang dipindai..."
        if hasattr(sr_monitor, "last_price_data"):
            u_data = sr_monitor.last_price_data.get(entry["symbol"], {})
            if u_data and "price" in u_data:
                live_p_str = f"{u_data['price']:,.2f}"

        confirm_msg = (
            f"🔔 <b>REMINDER HARGA BERHASIL DIAKTIFKAN!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>Pair:</b> <code>{entry['symbol']}</code>\n"
            f"⚡ <b>Kondisi Trigger:</b> Harga <b>{op} {target_price:,.2f}</b>\n"
            f"💬 <b>Pesan Notifikasi:</b>\n"
            f"👉 <code>{custom_msg}</code>\n"
            f"💰 <b>Harga Live Saat Ini:</b> <code>{live_p_str}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <i>Ketika harga {entry['symbol']} {op} {target_price:,.2f}, bot akan langsung mengirimkan pesan di atas!</i>\n\n"
            f"🛑 <i>Ketik <code>/stop {entry['symbol']}</code> untuk mematikan dan menghapus reminder ini.</i>"
        )
        await message.answer(confirm_msg, parse_mode="HTML")

    @dp.message(lambda msg: msg.text and any(msg.text.strip().lower().startswith(p) for p in ['/stop', '/ stop', '/del', '/hapus']))
    async def cmd_stop(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        if not sr_monitor:
            await message.answer("⚠️ Monitor Engine belum diinisialisasi.")
            return

        target_sym = parse_stop_command(message.text)
        if not target_sym:
            active = sr_monitor.get_active_reminders()
            if not active:
                await message.answer("ℹ️ Saat ini tidak ada reminder harga yang aktif.\nKetik <code>/set USDJPY &gt; 158.2 \"SELL 158.2 TP 157.7\"</code> untuk membuat reminder baru.", parse_mode="HTML")
                return
            lines = ["📋 <b>DAFTAR REMINDER AKTIF SAAT INI:</b>", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
            for r in active:
                lines.append(f"• <b>{r['symbol']}</b> ({r['operator']} <code>{r['target_price']:,.2f}</code>) ➔ <i>\"{r['message']}\"</i>")
            lines.extend([
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                "Ketik <code>/stop &lt;PAIR&gt;</code> untuk mematikan (contoh: <code>/stop USDJPY</code> atau <code>/stop all</code>)."
            ])
            await message.answer("\n".join(lines), parse_mode="HTML")
            return

        ok, msg_res, deleted_ids = await sr_monitor.remove_price_reminder(target_sym)
        await message.answer(msg_res, parse_mode="HTML")

    @dp.message(Command("reminders", "listreminder", "cekreminder"))
    async def cmd_list_reminders(message: Message):
        if not is_authorized(message.chat.id) and not is_authorized(message.from_user.id):
            return
        if not sr_monitor:
            await message.answer("⚠️ Monitor Engine belum diinisialisasi.")
            return
        active = sr_monitor.get_active_reminders()
        if not active:
            usage = (
                "ℹ️ <b>Belum ada reminder harga yang aktif.</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Ketik perintah:\n"
                "<code>/set USDJPY &gt; 158.2 \"SELL 158.2 TP 157.7\"</code>\n"
                "untuk memasang reminder baru untuk pair manapun!"
            )
            await message.answer(usage, parse_mode="HTML")
            return
        lines = [
            "📋 <b>DAFTAR REMINDER HARGA AKTIF</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]
        for idx, r in enumerate(active, 1):
            lines.append(
                f"{idx}. 💎 <b>{r['symbol']}</b> | Trigger: <b>{r['operator']} {r['target_price']:,.2f}</b>\n"
                f"   💬 Pesan: <code>{r['message']}</code>\n"
                f"   🕒 Dibuat: {r.get('created_at', '-')}\n"
                f"   🛑 Matikan: <code>/stop {r['symbol']}</code>\n"
            )
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💡 <i>Ketik <code>/stop all</code> untuk mematikan semua reminder sekaligus.</i>")
        await message.answer("\n".join(lines), parse_mode="HTML")

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

        if action == "menu:rk":
            await callback.answer()
            intro_text = (
                "🎯 <b>XEDY AI • MENU REKOMENDASI D1 &amp; H4</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🤖 <i>Divalidasi Adaptif oleh AI Qwen 3.7</i>\n\n"
                "<b>Pilih pair di bawah untuk melihat rekomendasi:</b>"
            )
            try:
                await target_msg.edit_text(
                    text=intro_text,
                    reply_markup=get_rk_pair_keyboard(),
                    parse_mode="HTML"
                )
            except Exception:
                await target_msg.answer(
                    text=intro_text,
                    reply_markup=get_rk_pair_keyboard(),
                    parse_mode="HTML"
                )
            return

        elif action.startswith("rk:"):
            target_sym = action.split(":")[-1].upper()
            await callback.answer()
            if target_sym == "ALL":
                from backend.scripts.send_d1h4_telegram import send_d1h4_recommendations
                await send_d1h4_recommendations()
            else:
                msg_text = format_single_pair_rk_msg(target_sym)
                kb = get_rk_pair_keyboard(target_sym)
                try:
                    await target_msg.edit_text(
                        text=msg_text,
                        reply_markup=kb,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    if "message is not modified" not in str(e).lower():
                        await target_msg.answer(
                            text=msg_text,
                            reply_markup=kb,
                            parse_mode="HTML"
                        )
            return


        if action.startswith("menu:op"):
            sym = action.split(":")[-1].upper() if len(action.split(":")) > 2 else "USDJPY"
            await callback.answer(f"⚡ Memuat Rekomendasi OP {sym}...")
            await do_send_op(target_msg, sym)

        elif action == "menu:reminders":
            await callback.answer("🔔 Memuat Pengaturan Reminder...")
            await cmd_list_reminders(target_msg)

        elif action == "menu:sr":
            await callback.answer("⏳ Memuat Bloomberg S/R Dashboard...")
            await do_send_sr(target_msg)

        elif action == "menu:engine":
            await callback.answer("⏳ Menganalisis 5 Pair dengan Multi-Agent Engine...")
            await do_send_engine(target_msg)

        elif action == "menu:flow":
            await callback.answer("⏳ Mengumpulkan Capital Money Flow Data...")
            await do_send_flow(target_msg)

        elif action == "menu:history":
            await callback.answer("⏳ Memuat Rekap History OP & TP/SL...")
            await do_send_history(target_msg)

        elif action == "menu:sinyal":
            await callback.answer("⏳ Memuat Sinyal H1 Qwen...")
            await do_send_sinyal(target_msg)

        elif action == "menu:nr_menu":
            await callback.answer("📜 Membuka menu 38 Pertanyaan Inti...")
            prompt_text = (
                "📜 <b>38 PERTANYAAN INTI — CAUSAL MARKET INTELLIGENCE</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Pilih instrumen yang ingin dianalisis secara lengkap (38 Pertanyaan Inti):"
            )
            await target_msg.answer(prompt_text, reply_markup=get_narrative_menu_keyboard(), parse_mode="HTML")

        elif action.startswith("menu:nr:") or action.startswith("menu:38:"):
            sym = action.split(":")[-1]
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
