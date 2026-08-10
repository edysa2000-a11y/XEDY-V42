import re

de_path = "backend/engines/decision_engine.py"
with open(de_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace logger info with a much quieter trace level or just remove it to stop log spam
target_log = """        # Log Divergence Risk
        div_risk_pct = divergence_penalty * 100
        self.logger.info(f"Market State: {self.current_signal} (Raw: {confidence:.4f}, Smth: {self.smoothed_confidence:.4f}, DivRisk: {div_risk_pct:.1f}%, Sideways: {is_sideways})")
        
        from backend.api.websocket import ws_manager
        await ws_manager.broadcast_signal(self.smoothed_confidence, self.current_signal)
        
        if self.current_signal in ["BUY", "SELL"] and self.risk_engine:
            await self.risk_engine.validate_trade(self.current_signal, price, self.smoothed_confidence)"""

new_log = """        # Log Divergence Risk
        div_risk_pct = divergence_penalty * 100
        # self.logger.info(f"Market State: {self.current_signal} (Raw: {confidence:.4f}, Smth: {self.smoothed_confidence:.4f}, DivRisk: {div_risk_pct:.1f}%, Sideways: {is_sideways})")
        
        from backend.api.websocket import ws_manager
        await ws_manager.broadcast_signal(self.smoothed_confidence, self.current_signal)
        
        # [V38 DEPRECATED] V38 Decision Engine is no longer allowed to execute trades.
        # It only calculates the smoothed_confidence for backwards compatibility in the UI.
        # if self.current_signal in ["BUY", "SELL"] and self.risk_engine:
        #     await self.risk_engine.validate_trade(self.current_signal, price, self.smoothed_confidence)"""

content = content.replace(target_log, new_log)

with open(de_path, "w", encoding="utf-8") as f:
    f.write(content)

print("decision_engine.py V38 logic has been safely deprecated and muted.")
