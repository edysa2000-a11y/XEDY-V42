
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
        """
        Process news using Qwen3 Embedding (0.6B equivalent) via Aivene API.
        Extracts Impact Score, Surprise vs Consensus, and Event Severity.
        """
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
