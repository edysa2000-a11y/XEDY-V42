import os

engines_dir = "backend/engines/v39_causal"
os.makedirs(engines_dir, exist_ok=True)

# 1_event_engine.py
event_code = """
import logging
from backend.engines.base_engine import BaseEngine
from backend.engines.aivene_client import AiveneClient

class EventShockEngine(BaseEngine):
    def __init__(self, config=None):
        super().__init__(config)
        self.client = AiveneClient()
        self.shock_score = 0.0
        
    @property
    def engine_name(self) -> str:
        return "EventShockEngine"
        
    async def process_news(self, news_text: str) -> dict:
        \"\"\"
        Process news using Qwen3 Embedding (0.6B equivalent) via Aivene API.
        Extracts Impact Score, Surprise vs Consensus, and Event Severity.
        \"\"\"
        self.logger.info("Processing event shock via Qwen3 Embedding...")
        emb = await self.client.get_embeddings(news_text)
        
        # Proxy mock calculation based on embedding magnitude (since we don't have a vector DB)
        magnitude = sum(abs(x) for x in emb[:50]) * 10
        
        if magnitude > 8.0:
            self.shock_score = 90.0 # High Impact
            regime = "EVENT SHOCK"
        else:
            self.shock_score = 30.0
            regime = "NORMAL"
            
        return {
            "shock_score": self.shock_score,
            "regime": regime,
            "event_type": "CPI/PCE" if "CPI" in news_text.upper() else "Normal"
        }
"""
with open(f"{engines_dir}/1_event_engine.py", "w", encoding="utf-8") as f:
    f.write(event_code)

# 2_macro_yield_engine.py
macro_code = """
import logging
from backend.engines.base_engine import BaseEngine

class MacroYieldEngine(BaseEngine):
    def __init__(self, config=None):
        super().__init__(config)
        self.real_yield = 0.0
        self.dxy_strength = 0.0
        
    @property
    def engine_name(self) -> str:
        return "MacroYieldEngine"
        
    async def calculate_yield_dxy(self, event_data: dict) -> dict:
        \"\"\"
        Correlates Event Shock with Rate Expectations, Yield, and DXY.
        \"\"\"
        # Mock calculation: High shock usually means DXY up, Yield up if inflation
        if event_data.get("shock_score", 0) > 80:
            self.real_yield += 0.1
            self.dxy_strength = 85.0
            direction = "Bearish for Gold"
        else:
            self.real_yield -= 0.05
            self.dxy_strength = 45.0
            direction = "Bullish for Gold"
            
        return {
            "real_yield_change": self.real_yield,
            "dxy_strength": self.dxy_strength,
            "expected_direction": direction
        }
"""
with open(f"{engines_dir}/2_macro_yield_engine.py", "w", encoding="utf-8") as f:
    f.write(macro_code)

# 3_money_flow_engine.py
flow_code = """
import logging
from backend.engines.base_engine import BaseEngine

class MoneyFlowEngine(BaseEngine):
    def __init__(self, config=None):
        super().__init__(config)
        self.flow_score = 50.0
        
    @property
    def engine_name(self) -> str:
        return "MoneyFlowEngine"
        
    async def aggregate_flow_channels(self, price_volatility: float, tick_volume: int) -> dict:
        \"\"\"
        Uses proxy data (Tick volume + volatility) to simulate Dark Pool, ETF, and COMEX flow.
        \"\"\"
        strength = min(100, tick_volume / 10)
        velocity = min(100, price_volatility * 100)
        
        self.flow_score = (strength * 0.6) + (velocity * 0.4)
        regime = "ACCUMULATION" if self.flow_score > 70 else "DISTRIBUTION" if self.flow_score < 30 else "NEUTRAL"
        
        return {
            "flow_strength": strength,
            "flow_velocity": velocity,
            "flow_score": self.flow_score,
            "flow_regime": regime
        }
"""
with open(f"{engines_dir}/3_money_flow_engine.py", "w", encoding="utf-8") as f:
    f.write(flow_code)

# 4_divergence_engine.py
div_code = """
import logging
from backend.engines.base_engine import BaseEngine

class DivergenceEngine(BaseEngine):
    def __init__(self, config=None):
        super().__init__(config)
        self.divergence_risk = 0.0
        
    @property
    def engine_name(self) -> str:
        return "DivergenceEngine"
        
    async def check_divergence(self, price_change: float, flow_data: dict, macro_data: dict) -> dict:
        \"\"\"
        Advanced Divergence Engine (Safe-Haven Check, Absorption, Distribution).
        \"\"\"
        risk = 0.0
        status = "ALIGNED"
        
        # Flow up but price down -> Distribution Warning
        if flow_data.get("flow_regime") == "ACCUMULATION" and price_change < 0:
            risk += 20.0
            status = "DISTRIBUTION WARNING"
            
        # DXY up but price up -> Safe Haven Check
        if macro_data.get("dxy_strength", 50) > 70 and price_change > 0:
            risk += 15.0
            status = "SAFE HAVEN DEMAND"
            
        self.divergence_risk = min(100.0, risk)
        return {
            "divergence_risk": self.divergence_risk,
            "status": status
        }
"""
with open(f"{engines_dir}/4_divergence_engine.py", "w", encoding="utf-8") as f:
    f.write(div_code)

# 5_consensus_gate.py
gate_code = """
import logging
from backend.engines.base_engine import BaseEngine

class ConsensusGateEngine(BaseEngine):
    def __init__(self, config=None):
        super().__init__(config)
        
    @property
    def engine_name(self) -> str:
        return "ConsensusGateEngine"
        
    async def final_trade_gate(self, event_data: dict, macro_data: dict, flow_data: dict, div_data: dict, tech_score: float) -> dict:
        \"\"\"
        Multi-Agent Consensus, Calibration, and Final Trade Gate (Steps 11-15).
        \"\"\"
        raw_prob = (flow_data.get("flow_score", 50) * 0.4) + (tech_score * 0.4) + (macro_data.get("dxy_strength", 50) * 0.2)
        
        # Calibration Engine (Step 12)
        calibrated_prob = raw_prob - (div_data.get("divergence_risk", 0) * 0.5)
        
        # Risk & Expected Value Engine (Steps 13, 14)
        edge = (calibrated_prob / 100) * 2.4 - (1 - (calibrated_prob / 100)) # Simple EV formula R:R 1:2.4
        
        # Gate
        trade_allowed = calibrated_prob >= 70.0 and edge > 0 and div_data.get("divergence_risk", 0) < 30.0
        
        return {
            "raw_prob": raw_prob,
            "calibrated_prob": calibrated_prob,
            "edge": edge,
            "trade_allowed": trade_allowed,
            "direction": "UP" if raw_prob > 50 else "DOWN"
        }
"""
with open(f"{engines_dir}/5_consensus_gate.py", "w", encoding="utf-8") as f:
    f.write(gate_code)

print("V39 Causal Engine files created successfully.")
