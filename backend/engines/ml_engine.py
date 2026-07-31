from .base_engine import BaseEngine
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import xgboost as xgb
import numpy as np

# Global model instance for the thread pool
_XGB_MODEL = None

def load_model():
    global _XGB_MODEL
    if _XGB_MODEL is None:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        model_path = os.path.join(project_root, 'models', 'xgboost_base.json')
        if os.path.exists(model_path):
            _XGB_MODEL = xgb.XGBClassifier()
            _XGB_MODEL.load_model(model_path)
            print(f"XGBoost Model loaded from {model_path}")
        else:
            print("WARNING: Model file not found. AI will be inactive.")

def cpu_bound_inference(rsi: float, macd: float, adx: float, atr: float, nfp_surprise: float, cpi_surprise: float, fed_rate: float, dxy_trend: float, yield_trend: float, session_asia: float, session_europe: float, session_america: float, session_overlap: float) -> float:
    """
    Runs in a ThreadPool. Predicts probability of BUY (class 1).
    """
    global _XGB_MODEL
    if _XGB_MODEL is None:
        return 0.5

    # XGBoost expects 2D array of 13 features
    X = np.array([[
        rsi, macd, adx, atr, 
        nfp_surprise, cpi_surprise, fed_rate, 
        dxy_trend, yield_trend,
        session_asia, session_europe, session_america, session_overlap
    ]])
    probs = _XGB_MODEL.predict_proba(X)
    return float(probs[0][1])

class MLEngine(BaseEngine):
    """
    Machine Learning Engine: Uses ThreadPoolExecutor and real XGBoost model.
    """
    
    @property
    def engine_name(self) -> str:
        return "MLEngine"

    def __init__(self, config=None, decision_engine=None):
        super().__init__(config)
        self.decision_engine = decision_engine
        self.executor = ThreadPoolExecutor(max_workers=2)
        
    async def start(self):
        self.logger.info("Loading ML Models (XGBoost) into Thread Pool...")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.executor, load_model)

    async def stop(self):
        self.logger.info("Shutting down Thread Pool...")
        self.executor.shutdown(wait=True)

    async def process_features(self, rsi: float, macd: float, adx: float, atr: float, nfp_surprise: float, cpi_surprise: float, fed_rate: float, dxy_trend: float, yield_trend: float, price: float):
        """Called by FeatureStore."""
        import datetime
        # Calculate current UTC session variables in real-time
        utc_hour = datetime.datetime.now(datetime.timezone.utc).hour
        session_asia = 1.0 if (utc_hour >= 0 and utc_hour < 8) else 0.0
        session_europe = 1.0 if (utc_hour >= 8 and utc_hour < 13) else 0.0
        session_america = 1.0 if (utc_hour >= 13 and utc_hour < 21) else 0.0
        session_overlap = 1.0 if (utc_hour >= 13 and utc_hour < 17) else 0.0

        loop = asyncio.get_running_loop()
        # Offload inference to prevent blocking
        confidence = await loop.run_in_executor(
            self.executor, cpu_bound_inference, 
            rsi, macd, adx, atr, 
            nfp_surprise, cpi_surprise, fed_rate, 
            dxy_trend, yield_trend,
            session_asia, session_europe, session_america, session_overlap
        )
        # Pass to Decision Engine
        if self.decision_engine:
            await self.decision_engine.evaluate_market_state(confidence, rsi, macd, price)
