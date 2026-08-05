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
        
        # Level 2 Cognitive Variables
        self.smoothed_confidence = 0.5
        self.current_signal = "WAIT"
        self.signal_streak = 0

    async def start(self):
        self.logger.info("Decision engine online.")

    async def stop(self):
        self.logger.info("Decision engine offline.")

    async def evaluate_market_state(self, confidence: float, rsi: float, macd: float, price: float, atr: float = 0.0):
        """
        Core logic matrix based on Manifest rules.
        Optimized with Adaptive EMA, Dynamic Hysteresis, and Smart Debouncing.
        """
        
        # 1. Adaptive EMA (Alpha based on MACD momentum)
        momentum = abs(macd)
        if momentum > 1.5:
            alpha = 0.4  # Fast response for breakout
        elif momentum > 0.5:
            alpha = 0.2  # Medium response
        else:
            alpha = 0.05 # Strong smoothing for choppy market
            
        self.smoothed_confidence = (alpha * confidence) + ((1.0 - alpha) * self.smoothed_confidence)
        
        # 2. Dynamic Volatility Hysteresis (Gap based on ATR)
        if atr > 2.0:
            hysteresis_gap = 0.08  # 8% tolerance for wild markets
        elif atr > 1.0:
            hysteresis_gap = 0.05
        else:
            hysteresis_gap = 0.02  # 2% tolerance for calm markets

        # 3. Hysteresis Trigger Logic
        raw_signal = self.current_signal
        
        if self.current_signal == "WAIT":
            if self.smoothed_confidence >= self.confidence_threshold:
                raw_signal = "BUY"
            elif self.smoothed_confidence <= (1.0 - self.confidence_threshold):
                raw_signal = "SELL"
                
        elif self.current_signal == "BUY":
            # Must drop below (threshold - gap) to exit BUY
            if self.smoothed_confidence < (self.confidence_threshold - hysteresis_gap):
                if self.smoothed_confidence <= (1.0 - self.confidence_threshold):
                    raw_signal = "SELL"
                else:
                    raw_signal = "WAIT"
                    
        elif self.current_signal == "SELL":
            # Must rise above (threshold + gap) to exit SELL
            if self.smoothed_confidence > ((1.0 - self.confidence_threshold) + hysteresis_gap):
                if self.smoothed_confidence >= self.confidence_threshold:
                    raw_signal = "BUY"
                else:
                    raw_signal = "WAIT"

        # 4. Volume-Weighted Debouncing
        required_streak = 3
        if momentum > 1.5:
            required_streak = 1
        elif momentum > 0.8:
            required_streak = 2
            
        if raw_signal == self.current_signal:
            self.signal_streak = 0
        else:
            self.signal_streak += 1
            
        if self.signal_streak >= required_streak:
            self.current_signal = raw_signal
            self.signal_streak = 0
            
        self.logger.info(f"Market State: {self.current_signal} (Raw Conf: {confidence:.4f}, Smth Conf: {self.smoothed_confidence:.4f}, Price: {price})")
        
        from backend.api.websocket import ws_manager
        await ws_manager.broadcast_signal(self.smoothed_confidence, self.current_signal)
        
        if self.current_signal in ["BUY", "SELL"] and self.risk_engine:
            await self.risk_engine.validate_trade(self.current_signal, price, self.smoothed_confidence)
