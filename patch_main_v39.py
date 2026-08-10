import re

file_path = "backend/main.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

import_statement = """from backend.engines.feature_store import FeatureStore
from backend.engines.market_engine import MarketEngine
from backend.engines.data_engine import DataEngine
from backend.engines.news_engine import HybridNewsEngine
from backend.engines.v39_causal.1_event_engine import EventShockEngine
from backend.engines.v39_causal.2_macro_yield_engine import MacroYieldEngine
from backend.engines.v39_causal.3_money_flow_engine import MoneyFlowEngine
from backend.engines.v39_causal.4_divergence_engine import DivergenceEngine
from backend.engines.v39_causal.5_consensus_gate import ConsensusGateEngine"""

content = content.replace(
    "from backend.engines.feature_store import FeatureStore\nfrom backend.engines.market_engine import MarketEngine\nfrom backend.engines.data_engine import DataEngine\nfrom backend.engines.news_engine import HybridNewsEngine",
    import_statement
)

init_v39_engines = """
        ml_instance = MLEngine(decision_engine=de_instance)
        fs_instance = FeatureStore(ml_engine=ml_instance)
        
        # Initialize V39 Causal Scaffolding
        event_engine = EventShockEngine()
        macro_yield = MacroYieldEngine()
        money_flow = MoneyFlowEngine()
        divergence = DivergenceEngine()
        consensus = ConsensusGateEngine()
        
        app.state.asset_engines[symbol] = {
            "risk_engine": re_instance,
            "decision_engine": de_instance,
            "ml_engine": ml_instance,
            "feature_store": fs_instance,
            "v39_event": event_engine,
            "v39_macro": macro_yield,
            "v39_flow": money_flow,
            "v39_div": divergence,
            "v39_consensus": consensus
        }
"""
content = re.sub(r'        ml_instance = MLEngine\(decision_engine=de_instance\)\n        fs_instance = FeatureStore\(ml_engine=ml_instance\)\n        \n        app\.state\.asset_engines\[symbol\] = {\n            "risk_engine": re_instance,\n            "decision_engine": de_instance,\n            "ml_engine": ml_instance,\n            "feature_store": fs_instance\n        }', init_v39_engines, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("backend/main.py patched successfully to include V39 Causal Engines.")
