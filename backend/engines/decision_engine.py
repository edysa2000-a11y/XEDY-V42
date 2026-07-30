from .base_engine import BaseEngine

class DecisionEngine(BaseEngine):
    """
    Institutional Decision Engine: Aggregates signals and makes trading decisions.
    Passes decisions to Risk Engine.
    """
    
    @property
    def engine_name(self) -> str:
        return "DecisionEngine"

    def __init__(self, config=None, risk_engine=None):
        super().__init__(config)
        self.risk_engine = risk_engine
        self.confidence_threshold = self.config.get("confidence_threshold", 0.68)

    async def start(self):
        self.logger.info("Decision engine online.")

    async def stop(self):
        self.logger.info("Decision engine offline.")

    async def evaluate_market_state(self, confidence: float, rsi: float, macd: float, price: float):
        """
        Core logic matrix based on Manifest rules.
        """
        signal = "WAIT"
        
        if confidence >= self.confidence_threshold:
            signal = "BUY"
        elif confidence <= (1.0 - self.confidence_threshold):
            signal = "SELL"
            
        self.logger.info(f"Evaluasi Keadaan Pasar: {signal} (Skor Keyakinan: {confidence:.4f}, Harga: {price})")
        
        from backend.api.websocket import ws_manager
        await ws_manager.broadcast_signal(confidence, signal)
        
        if signal in ["BUY", "SELL"] and self.risk_engine:
            await self.risk_engine.validate_trade(signal, price, confidence)
