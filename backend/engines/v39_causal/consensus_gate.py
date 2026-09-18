
import logging
from backend.engines.base_engine import BaseEngine

class ConsensusGateEngine(BaseEngine):
    def __init__(self, config=None):
        super().__init__(config)
        
    @property
    def engine_name(self) -> str:
        return "ConsensusGateEngine"
        
    async def start(self):
        pass
        
    async def stop(self):
        pass

    async def final_trade_gate(self, event_data: dict, macro_data: dict, flow_data: dict, div_data: dict, tech_score: float) -> dict:
        """
        Multi-Agent Consensus, Calibration, and Final Trade Gate (Steps 11-15).
        """
        # [FIX]: Bobot ML dinamis (Self-Learning). Macro, Tech, Flow akan disesuaikan otomatis jika terjadi error.
        from backend.engines.v39_causal.ml_state import get_weights
        weights = get_weights()
        w_flow = weights.get("flow_weight", 0.4)
        w_tech = weights.get("tech_weight", 0.3)
        w_macro = weights.get("macro_weight", 0.3)
        
        # [CRITICAL FIX]: dxy_strength berbanding terbalik dengan Gold. DXY kuat = Gold lemah.
        raw_prob = (flow_data.get("flow_score", 50) * w_flow) + (tech_score * w_tech) + ((100 - macro_data.get("dxy_strength", 50)) * w_macro)
        
        direction = "UP" if raw_prob > 50 else "DOWN"
        
        # Convert raw_prob (bullishness) to confidence (strength of signal)
        signal_strength = raw_prob if direction == "UP" else (100 - raw_prob)
        
        # Calibration Engine (Step 12)
        # Simulation of advanced data source (Order Book Absorption & Dark Pool Tracking)
        advanced_data_boost = 0 # Removed hardcoded boost to allow Adaptive Self-Learning to work
        calibrated_prob = (signal_strength + advanced_data_boost) - (div_data.get("divergence_risk", 0) * 0.05)
        calibrated_prob = min(100.0, max(0.0, calibrated_prob))
        
        # Risk & Expected Value Engine (Steps 13, 14)
        edge = (calibrated_prob / 100) * 1.5 - (1 - (calibrated_prob / 100)) # Simple EV formula R:R 1:1.5
        
        # Gate
        # Removed hardcoded 70.0 to allow UI 'min_confidence' slider to take full control
        trade_allowed = bool(calibrated_prob >= 51.0 and div_data.get("divergence_risk", 0) < 30.0)
        
        return {
            "raw_prob": float(raw_prob),
            "calibrated_prob": float(calibrated_prob),
            "edge": float(edge),
            "trade_allowed": trade_allowed,
            "direction": direction
        }
