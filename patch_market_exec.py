import re

market_path = "backend/engines/market_engine.py"
with open(market_path, "r", encoding="utf-8") as f:
    content = f.read()

# I will find the V39 payload block in market_engine.py and inject the notifier and execution logic.
target = """                        v39_payload = {
                            "event": event_res,
                            "macro": macro_res,
                            "flow": flow_res,
                            "div": div_res,
                            "gate": gate_res
                        }
                        await ws_manager.broadcast_v39_causal(v39_payload)"""

new_logic = """                        v39_payload = {
                            "event": event_res,
                            "macro": macro_res,
                            "flow": flow_res,
                            "div": div_res,
                            "gate": gate_res
                        }
                        await ws_manager.broadcast_v39_causal(v39_payload)
                        
                        # Only trigger Telegram/Execution rarely, to avoid spam, maybe use a cooldown mechanism
                        # Let's check if trade is allowed and probabilty is high
                        import time
                        current_time = time.time()
                        if not hasattr(self, "last_v39_trade_time"):
                            self.last_v39_trade_time = 0
                            
                        if gate_res.get("trade_allowed") and gate_res.get("calibrated_prob", 0) > 75.0:
                            # 5-minute cooldown for signals
                            if current_time - self.last_v39_trade_time > 300:
                                self.last_v39_trade_time = current_time
                                action = gate_res.get("direction", "BUY")
                                
                                # Send Telegram
                                from backend.main import app
                                if hasattr(app.state, "telegram_bot") and app.state.telegram_bot.notifier:
                                    last_tick = mt5.symbol_info_tick("XAUUSD")
                                    current_price = last_tick.ask if action == "BUY" else last_tick.bid if last_tick else 0.0
                                    await app.state.telegram_bot.notifier.notify_v39_consensus(v39_payload, current_price, action)
                                
                                # Execute Trade via ExecutionEngine
                                if hasattr(app.state, "execution_engine") and app.state.execution_engine:
                                    try:
                                        await app.state.execution_engine.execute_trade(
                                            symbol="XAUUSD",
                                            action=action,
                                            confidence=gate_res.get("calibrated_prob", 0)/100.0,
                                            source="V39_CAUSAL_ENGINE"
                                        )
                                    except Exception as e:
                                        self.logger.error(f"V39 Execution Error: {e}")"""

content = content.replace(target, new_logic)

with open(market_path, "w", encoding="utf-8") as f:
    f.write(content)

print("V39 execution logic injected into market_engine.py")
