import logging
from aiogram import Bot

logger = logging.getLogger("xedy.telegram.notifier")

class TelegramNotifier:
    """
    Service layer for internal backend engines to push notifications 
    to the Telegram Admin.
    """
    def __init__(self, bot: Bot, admin_id: int):
        self.bot = bot
        self.admin_id = admin_id

    async def notify_trade(self, action: str, symbol: str, price: float, ticket: str):
        msg = f"🔔 <b>Trade Dieksekusi</b>\n\nAksi: {action}\nSimbol: {symbol}\nHarga: {price}\nTiket: {ticket}"
        await self._send_safe(msg)
        
    async def notify_news(self, time_str: str, date_str: str, current_price: float, headline: str, trend: str, estimated_price: float, news_sentiment: float, usd_strength: float, equity_strength: float, gsi_before: float, gsi_after: float, tech_rsi: float = None, tech_trend: str = None, tech_ma20: str = None, tech_ma200: str = None, ai_confidence: float = None, ai_recommendation: str = None):
        trend_upper = trend.upper()
        if "BULLISH" in trend_upper:
            trend_formatted = "🟢 <b>BULLISH</b>"
        elif "BEARISH" in trend_upper:
            trend_formatted = "🔴 <b>BEARISH</b>"
        else:
            trend_formatted = f"<b>{trend}</b>"

        # Format Technical Block if available
        tech_block = ""
        if tech_rsi is not None:
            rsi_desc = "Overbought" if tech_rsi >= 70 else ("Oversold" if tech_rsi <= 30 else "Neutral")
            trend_icon = "🟢" if tech_trend == "BULLISH" else "🔴"
            tech_block = (
                f"🔍 <b>Analisis Teknikal (M15):</b>\n"
                f"{trend_icon} Trend Bias: <b>{tech_trend}</b>\n"
                f"📊 <i>RSI (14): {tech_rsi:.1f} ({rsi_desc})</i>\n"
                f"📈 <i>MA-20 Signal: {tech_ma20}</i>\n"
                f"📉 <i>MA-200 Signal: {tech_ma200}</i>\n\n"
            )

        # Format AI Block if available
        ai_block = ""
        if ai_confidence is not None:
            conf_val = ai_confidence / 100.0
            if conf_val >= 0.70 or conf_val <= 0.30:
                acc_label = "Akurasi Sinyal Tinggi"
            elif 0.40 <= conf_val <= 0.60:
                acc_label = "Akurasi Sinyal Rendah"
            else:
                acc_label = "Akurasi Sinyal Sedang"
            ai_block = (
                f"🧠 <b>Rekomendasi AI (XGBoost):</b>\n"
                f"Skor Keyakinan AI: {ai_confidence:.2f}% ({acc_label})\n"
                f"Rekomendasi AI: <b>{ai_recommendation}</b>\n\n"
            )

        # Determine GSI Label
        if gsi_after > 55.0:
            gsi_label = "🟢 BULLISH"
        elif gsi_after < 45.0:
            gsi_label = "🔴 BEARISH"
        else:
            gsi_label = "⚪ NEUTRAL"

        msg = (
            f"📰 <b>Berita Makro Baru</b>\n\n"
            f"🕒 Jam: {time_str}\n"
            f"📅 Tanggal: {date_str}\n"
            f"💰 Harga XAUUSD Saat Ini: ${current_price:.2f}\n"
            f"📢 Berita: <i>{headline}</i>\n"
            f"📈 Trend Dampak: {trend_formatted}\n\n"
            f"{tech_block}"
            f"{ai_block}"
            f"📊 <b>Metrik Sentimen Global: {gsi_label} ({gsi_after:.1f}%)</b>\n"
            f"💬 <i>Sentiment Market (News): {news_sentiment:.1f}%</i>\n"
            f"💵 <i>Currency Index (USD): {usd_strength:.1f}%</i>\n"
            f"🏢 <i>Market Strength (Equity): {equity_strength:.1f}%</i>\n"
            f"⚙️ Global Sentiment Index (GSI): {gsi_before:.1f}% ➔ {gsi_after:.1f}%\n\n"
            f"🎯 Estimasi Harga Dampak: ${estimated_price:.2f}"
        )
        await self._send_safe(msg)
        

    async def notify_v39_consensus(self, v39_data: dict, price: float, action: str):
        event = v39_data.get("event", {})
        macro = v39_data.get("macro", {})
        flow = v39_data.get("flow", {})
        div = v39_data.get("div", {})
        gate = v39_data.get("gate", {})
        
        # Color coding
        gate_status = "🟢 TRADE ALLOWED" if gate.get("trade_allowed") else "🔴 TRADE BLOCKED"
        div_icon = "🟢" if div.get("divergence_risk", 0) < 30 else "🔴"
        flow_icon = "🟢" if flow.get("flow_regime") == "ACCUMULATION" else ("🔴" if flow.get("flow_regime") == "DISTRIBUTION" else "⚪")
        
        msg = (
            f"🚀 <b>XEDY V39 CAUSAL ENGINE ALERT</b>\n\n"
            f"💰 <b>Harga XAUUSD Saat Ini: ${price:.2f}</b>\n"
            f"🎯 <b>Rekomendasi Arah: {action}</b>\n\n"
            f"⚡ <b>① EVENT SHOCK</b>\n"
            f"• <i>{event.get('event_type', 'Normal')} Score: {event.get('shock_score', 0):.1f}/100</i>\n"
            f"• <i>Regime: {event.get('regime', 'Normal')}</i>\n\n"
            f"🏦 <b>② MACRO & YIELD</b>\n"
            f"• <i>Δ Yield: {macro.get('real_yield_change', 0):.2f}%</i>\n"
            f"• <i>DXY Strength: {macro.get('dxy_strength', 50):.1f}/100</i>\n"
            f"• <i>Bias: {macro.get('expected_direction', 'Neutral')}</i>\n\n"
            f"💸 <b>③ INSTITUTIONAL FLOW (PROXY)</b>\n"
            f"• <i>Flow Score: {flow.get('flow_score', 50):.1f}/100</i>\n"
            f"• <i>Regime: {flow_icon} {flow.get('flow_regime', 'NEUTRAL')}</i>\n\n"
            f"⚠️ <b>④ DIVERGENCE ENGINE</b>\n"
            f"• <i>Risk Penalty: {div_icon} {div.get('divergence_risk', 0):.1f}%</i>\n"
            f"• <i>Status: {div.get('status', 'ALIGNED')}</i>\n\n"
            f"🧠 <b>⑤ CONSENSUS GATE</b>\n"
            f"• <i>Raw Probability: {gate.get('raw_prob', 50):.1f}%</i>\n"
            f"• <i>Calibrated Prob: {gate.get('calibrated_prob', 50):.1f}%</i>\n"
            f"• <i>Expected Value: {gate.get('edge', 0):.2f}R</i>\n\n"
            f"🛡️ <b>FINAL DECISION:</b>\n"
            f"<b>{gate_status}</b>"
        )
        await self._send_safe(msg)

    async def notify_risk_alert(self, message: str):
        msg = f"⚠️ <b>Peringatan Risiko</b>\n\n{message}"
        await self._send_safe(msg)

    async def notify_system_status(self, message: str):
        msg = f"ℹ️ <b>Sistem XEDY</b>\n\n{message}"
        await self._send_safe(msg)

    async def _send_safe(self, text: str):
        try:
            if self.bot and self.admin_id:
                await self.bot.send_message(chat_id=self.admin_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
