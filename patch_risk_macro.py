import re

risk_path = "backend/engines/risk_engine.py"
with open(risk_path, "r", encoding="utf-8") as f:
    content = f.read()

# Disable Macro Strategist Block in Risk Engine
target = """            # Check Macro Strategist Bias
            if macro_strat and hasattr(macro_strat, "macro_bias"):
                bias = macro_strat.macro_bias
                if bias == "BUY_ONLY" and signal == "SELL":
                    self.logger.warning(f"Risk Reject: Trade blocked by Macro Strategist Bias (BUY_ONLY)")
                    return
                elif bias == "SELL_ONLY" and signal == "BUY":
                    self.logger.warning(f"Risk Reject: Trade blocked by Macro Strategist Bias (SELL_ONLY)")
                    return
                elif bias == "WAIT":
                    self.logger.warning(f"Risk Reject: Trade blocked by Macro Strategist Bias (WAIT)")
                    return"""

new_logic = """            # Check Macro Strategist Bias
            # [V38 DEPRECATED] - MacroStrategist bias blocking is disabled.
            # V39 Causal Engine now handles macro and yield bias dynamically via consensus_gate.
            pass"""

if "Trade blocked by Macro Strategist Bias" in content:
    content = content.replace(target, new_logic)
    with open(risk_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Risk Engine Macro Strategist blocking disabled.")
else:
    print("Target not found or already patched.")
