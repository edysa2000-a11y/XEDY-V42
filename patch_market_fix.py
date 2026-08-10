import re

market_path = "backend/engines/market_engine.py"
with open(market_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the data_engine.get_historical_data call with MT5 call
old_logic = """                        # Use actual OANDA tick volume if available
                        tick_vol = 500
                        if self.data_engine:
                            df = self.data_engine.get_historical_data("XAUUSD", "M5", 1)
                            if not df.empty and 'tick_volume' in df.columns:
                                tick_vol = int(df['tick_volume'].iloc[-1])"""

new_logic = """                        # Use actual tick volume from MT5 if available
                        tick_vol = 500
                        try:
                            rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M5, 0, 1)
                            if rates is not None and len(rates) > 0:
                                tick_vol = int(rates[0]['tick_volume'])
                        except Exception:
                            pass"""

content = content.replace(old_logic, new_logic)

with open(market_path, "w", encoding="utf-8") as f:
    f.write(content)

print("market_engine.py patched to fix get_historical_data error.")
