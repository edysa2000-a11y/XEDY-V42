from .base_engine import BaseEngine

class DecisionEngine(BaseEngine):
    @property
    def engine_name(self) -> str:
        return "DecisionEngine"

    def __init__(self, config=None, risk_engine=None):
        super().__init__(config)
        self.risk_engine = risk_engine
        self.confidence_threshold = 0.65
        
        # Level 2 Cognitive Variables
        self.smoothed_confidence = 0.5
        self.current_signal = "WAIT"
        self.signal_streak = 0
        
        # Divergence Engine Variables
        self.last_price = 0.0
        self.last_macd = 0.0
        self.last_rsi = 50.0

    async def start(self):
        self.logger.info("Decision engine online.")

    async def stop(self):
        self.logger.info("Decision engine offline.")

    async def evaluate_market_state(self, confidence: float, rsi: float, macd: float, price: float, atr: float = 0.0):
        # 1. Calculate Divergence Risk (V39 Upgrade)
        divergence_penalty = 0.0
        is_sideways = False
        
        if self.last_price != 0.0:
            price_diff = price - self.last_price
            macd_diff = macd - self.last_macd
            
            # Bearish Divergence: Price Up, Momentum Down
            if price_diff > 0 and macd_diff < 0:
                divergence_penalty += 0.15 # 15% penalty
            # Bullish Divergence: Price Down, Momentum Up
            elif price_diff < 0 and macd_diff > 0:
                divergence_penalty += 0.15
                
            # If RSI is stagnant while price moves, add penalty
            if abs(price_diff) > (atr * 0.2) and abs(rsi - self.last_rsi) < 1.0:
                divergence_penalty += 0.09 # 9% penalty
                
            # Cap penalty at 24%
            divergence_penalty = min(divergence_penalty, 0.24)
            
            # Detect Sideways (Very low ATR or flat MACD)
            if atr < 0.5 or abs(macd_diff) < 0.01:
                is_sideways = True
                
        self.last_price = price
        self.last_macd = macd
        self.last_rsi = rsi

        # 2. Adaptive EMA Smoothing
        momentum = abs(macd)
        if momentum > 1.5:
            alpha = 0.4
        elif momentum > 0.5:
            alpha = 0.2
        else:
            alpha = 0.05
            
        # Apply Raw Confidence calculation based on Base Confidence minus Divergence Penalty
        adjusted_confidence = confidence - divergence_penalty
        
        # Apply Sideways Filter (cap at 75% to prevent false positives)
        if is_sideways and adjusted_confidence > 0.75:
            adjusted_confidence = 0.75
            
        # Allow up to 96% if momentum is massive and NO divergence
        if divergence_penalty == 0.0 and momentum > 2.0:
            adjusted_confidence = min(adjusted_confidence + 0.10, 0.96)
            
        self.smoothed_confidence = (alpha * adjusted_confidence) + ((1.0 - alpha) * self.smoothed_confidence)
        
        # Ensure bounds
        self.smoothed_confidence = max(0.0, min(self.smoothed_confidence, 1.0))

        # 3. Trigger Logic
        raw_signal = self.current_signal
        
        if self.current_signal == "WAIT":
            if self.smoothed_confidence >= self.confidence_threshold:
                raw_signal = "BUY"
            elif self.smoothed_confidence <= (1.0 - self.confidence_threshold):
                raw_signal = "SELL"
                
        elif self.current_signal == "BUY":
            if self.smoothed_confidence < (self.confidence_threshold - 0.05):
                raw_signal = "SELL" if self.smoothed_confidence <= (1.0 - self.confidence_threshold) else "WAIT"
                    
        elif self.current_signal == "SELL":
            if self.smoothed_confidence > ((1.0 - self.confidence_threshold) + 0.05):
                raw_signal = "BUY" if self.smoothed_confidence >= self.confidence_threshold else "WAIT"

        # 4. Debouncing
        required_streak = 2 if momentum > 0.8 else 3
            
        if raw_signal == self.current_signal:
            self.signal_streak = 0
        else:
            self.signal_streak += 1
            
        if self.signal_streak >= required_streak:
            self.current_signal = raw_signal
            self.signal_streak = 0
            
        # Log Divergence Risk
        div_risk_pct = divergence_penalty * 100
        self.logger.info(f"Market State: {self.current_signal} (Raw: {confidence:.4f}, Smth: {self.smoothed_confidence:.4f}, DivRisk: {div_risk_pct:.1f}%, Sideways: {is_sideways})")
        
        from backend.api.websocket import ws_manager
        await ws_manager.broadcast_signal(self.smoothed_confidence, self.current_signal)
        
        if self.current_signal in ["BUY", "SELL"] and self.risk_engine:
            await self.risk_engine.validate_trade(self.current_signal, price, self.smoothed_confidence)
