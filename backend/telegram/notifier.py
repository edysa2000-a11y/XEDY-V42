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

    async def notify_ascii_dashboard(self, ascii_text: str):
        """Sends zero-token ASCII dashboard inside <pre> for perfect alignment."""
        await self._send_safe(f"<pre>{ascii_text}</pre>")

    async def notify_final_outlook(self, narrative_markdown: str):
        """
        Sends the FINAL XEDY OUTLOOK to Telegram. 
        Converts standard markdown headers into bold for Telegram HTML.
        """
        import re
        
        html_text = narrative_markdown
        # Basic markdown to HTML formatting for Telegram
        html_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html_text)
        html_text = re.sub(r'__(.*?)__', r'<u>\1</u>', html_text)
        html_text = re.sub(r'`(.*?)`', r'<code>\1</code>', html_text)
        html_text = re.sub(r'### (.*)', r'<b>\1</b>', html_text)
        html_text = re.sub(r'## (.*)', r'<b>\1</b>', html_text)
        html_text = re.sub(r'# (.*)', r'<b>\1</b>', html_text)
        
        await self._send_safe(html_text)

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
