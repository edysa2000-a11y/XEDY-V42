import re

market_path = "backend/engines/market_engine.py"
with open(market_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """                                # Execute Trade via ExecutionEngine
                                if hasattr(app.state, "execution_engine") and app.state.execution_engine:
                                    try:
                                        await app.state.execution_engine.execute_trade(
                                            symbol="XAUUSD",
                                            action=action,
                                            confidence=gate_res.get("calibrated_prob", 0)/100.0,
                                            source="V39_CAUSAL_ENGINE"
                                        )"""

new_logic = """                                # Execute Trade via RiskEngine (To respect Drawdown, Max Positions, Margin limits)
                                if hasattr(app.state, "risk_engine") and app.state.risk_engine:
                                    try:
                                        # V39 Causal Engine sends signal to RiskEngine
                                        await app.state.risk_engine.validate_trade(
                                            signal=action, 
                                            price=current_price, 
                                            confidence=gate_res.get("calibrated_prob", 0)/100.0
                                        )
                                    except Exception as e:
                                        self.logger.error(f"V39 Execution Error: {e}")"""

if "await app.state.execution_engine.execute_trade" in content:
    content = content.replace(target, new_logic)
    with open(market_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Market Engine execution logic routed through RiskEngine.")
else:
    print("Already patched or target not found.")
