import asyncio
import os
import json
import dotenv
import MetaTrader5 as mt5

dotenv.load_dotenv(override=True)
from backend.engines.decision_priority_engine import DecisionPriorityEngine

async def main():
    print("Testing Decision Priority Engine...")
    
    # Check MT5
    if not mt5.initialize():
        print("MT5 initialization failed! Make sure MT5 is open.")
        return
        
    print("MT5 Connected.")
    symbol = "XAUUSD"
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 15)
    tick = mt5.symbol_info_tick(symbol)
    
    if rates is None or len(rates) == 0 or tick is None:
        print("Failed to get MT5 rates/tick data.")
        return
        
    current_price = tick.ask
    print(f"Current price: {current_price}")
    
    technicals = {
        "RSI_14": 50.0,
        "EMA_50": current_price,
    }
    news_text = "No major news."
    atr = 9.0
    
    engine = DecisionPriorityEngine()
    print("Evaluating market (calling Aivene API)...")
    
    try:
        decision_data = await engine.evaluate_market(
            technicals=technicals,
            news_text=news_text,
            current_price=current_price,
            atr=atr
        )
        print("\n=== EVALUATION RESULT ===")
        print(json.dumps(decision_data, indent=2))
        print("=========================")
    except Exception as e:
        print(f"\nException occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
