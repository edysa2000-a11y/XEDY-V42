import re

with open("backend/engines/risk_engine.py", "r") as f:
    lines = f.readlines()

# Truncate at line 748
lines = lines[:749]

content = "".join(lines)

# Replace start/stop
new_start = """    async def start(self):
        self.logger.info("Risk engine online.")
        import asyncio
        self._trailing_task = asyncio.create_task(self._trailing_stop_loop())
        self._confidence_task = asyncio.create_task(self._confidence_method_loop())

    async def stop(self):
        if hasattr(self, "_trailing_task") and self._trailing_task:
            self._trailing_task.cancel()
        if hasattr(self, "_confidence_task") and self._confidence_task:
            self._confidence_task.cancel()
        self.logger.info("Risk engine offline.")
"""

# We need to replace lines 51 to 78 with new_start
# Let's just use regex
content = re.sub(r'    async def start\(self\):.*?    async def stop\(self\):.*?        self\.logger\.info\("Risk engine offline\."\)\n', new_start, content, flags=re.DOTALL)

# Append the new loop
new_loop = """
    async def _confidence_method_loop(self):
        import asyncio
        from backend.main import app
        import os
        import MetaTrader5 as mt5

        while True:
            try:
                # Get autotrade status
                autotrade_enabled = os.environ.get("AUTOTRADE_ENABLED", "False").lower() == "true"
                if not autotrade_enabled:
                    await asyncio.sleep(1)
                    continue

                if not getattr(self, 'execution_engine', None):
                    await asyncio.sleep(1)
                    continue

                # Ensure MT5 is connected
                if not mt5.terminal_info():
                    await asyncio.sleep(1)
                    continue

                # 1. Fetch Decision Engine Smoothed Confidence & Action
                de = getattr(app.state, 'decision_engine', None)
                if not de:
                    await asyncio.sleep(1)
                    continue
                
                # We expect decision engine to give a smoothed confidence and signal
                confidence = de.smoothed_confidence
                raw_signal = de.current_signal

                if confidence < 0.65 or raw_signal not in ["BUY", "SELL"]:
                    await asyncio.sleep(1)
                    continue

                # 2. Fetch Technical Indicators from Data Engine
                data_e = getattr(app.state, 'data_engine', None)
                if not data_e or not getattr(data_e, 'technicals', None):
                    await asyncio.sleep(1)
                    continue
                    
                techs = data_e.technicals.get(self.symbol)
                if not techs:
                    await asyncio.sleep(1)
                    continue

                rsi = techs.get("rsi", 50)
                macd = techs.get("macd", 0)
                macd_signal = techs.get("macd_signal", 0)
                atr = techs.get("atr", 0.0010) # Safe default if missing

                # 3. Technical Confirmation Filter
                # Buy confirmed if MACD > Signal and RSI < 70 (not overbought)
                # Sell confirmed if MACD < Signal and RSI > 30 (not oversold)
                is_confirmed = False
                if raw_signal == "BUY" and macd > macd_signal and rsi < 70:
                    is_confirmed = True
                elif raw_signal == "SELL" and macd < macd_signal and rsi > 30:
                    is_confirmed = True
                    
                if not is_confirmed:
                    await asyncio.sleep(1)
                    continue

                # 4. Check Open Positions (Avoid stacking)
                positions = mt5.positions_get(symbol=self.symbol)
                num_positions = len(positions) if positions else 0
                max_pos = int(os.environ.get("AVERAGING_MAX_POSITIONS", "3"))
                
                if num_positions >= max_pos:
                    await asyncio.sleep(1)
                    continue

                # 5. Calculate Dynamic Risk (1% to 5%)
                # Confidence 0.65 -> 1.0% Risk
                # Confidence 1.00 -> 5.0% Risk
                capped_conf = min(max(confidence, 0.65), 1.0)
                risk_pct = 1.0 + ((capped_conf - 0.65) / 0.35) * 4.0
                
                # Fetch Balance
                acc = mt5.account_info()
                if not acc:
                    await asyncio.sleep(1)
                    continue
                    
                balance = acc.balance
                risk_amount = balance * (risk_pct / 100.0)
                
                # Point value logic (Standard Lot $10/pip or custom based on symbol)
                # Just scale using SL (ATR) if possible, but for simplicity we will rely on 
                # a base lot multiplier logic or standard os.environ LOT_SIZE if dynamic is too risky.
                # However, user explicitly requested "Risk 1 - 5%".
                
                sl_distance = atr * 1.5 # We use 1.5 ATR for SL
                
                # Convert SL distance to dollars
                multiplier = 100000.0
                if "XAU" in self.symbol: multiplier = 100.0
                if "JPY" in self.symbol: multiplier = 1000.0
                
                pip_value_per_lot = multiplier # Approximate
                
                # Lot = Risk Amount / (SL Distance * Pip Value per lot)
                calculated_lot = risk_amount / (sl_distance * pip_value_per_lot)
                
                # Clamp lot
                min_lot = 0.01
                max_lot = 5.0
                final_lot = max(min_lot, min(max_lot, round(calculated_lot, 2)))

                # 6. Execute Order
                self.logger.info(f"[Confidence Method] {raw_signal} on {self.symbol} | Conf: {confidence:.2f} | Risk: {risk_pct:.1f}% (${risk_amount:.2f}) | Lot: {final_lot}")
                
                res = await self.execution_engine.execute_order(
                    symbol=self.symbol,
                    action=raw_signal,
                    lot_size=final_lot
                )
                
                # Prevent spamming
                await asyncio.sleep(60)

            except Exception as e:
                self.logger.error(f"Error in _confidence_method_loop: {e}")
                await asyncio.sleep(5)
"""

content += new_loop

with open("backend/engines/risk_engine.py", "w") as f:
    f.write(content)

print("Updated risk_engine.py successfully.")
