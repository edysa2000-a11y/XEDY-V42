import sys
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.telegram.bot import TelegramEcosystem

async def main():
    bot = TelegramEcosystem()
    await bot.start()
    
    mock_v39 = {
        "event": {"risk_level": "LOW", "score": 85, "sentiment": 0.8},
        "macro": {"trend": "BULLISH", "causal_confidence": 0.90},
        "flow": {"score": 90},
        "div": {"risk": 15},
        "gate": {"direction": "BUY", "calibrated_prob": 88, "edge": 1.5, "trade_allowed": True}
    }
    
    if bot.notifier:
        print("Mengirim pesan test ke Telegram...")
        await bot.notifier.notify_v39_consensus(mock_v39, 4350.00, "BUY")
        print("Pesan terkirim!")
    await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
