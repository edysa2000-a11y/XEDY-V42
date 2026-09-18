
import logging
from backend.engines.base_engine import BaseEngine
import random

class EventShockEngine(BaseEngine):
    def __init__(self, config=None):
        super().__init__(config)
        self.shock_score = 0.0
        
    @property
    def engine_name(self) -> str:
        return "EventShockEngine"
        
    async def start(self):
        pass
        
    async def stop(self):
        pass

    async def process_news(self, news_text: str) -> dict:
        """
        Algorithmic event shock analysis without API dependency.
        Extracts Impact Score, Surprise vs Consensus, and Event Severity.
        """
        self.logger.info("Processing event shock algorithmically...")
        
        # Simple mock calculation based on keywords to avoid token usage
        magnitude = 5.0
        if "CPI" in news_text.upper() or "FED" in news_text.upper() or "RATE" in news_text.upper():
            magnitude += 4.5
        
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
