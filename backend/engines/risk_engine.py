from .base_engine import BaseEngine
from .claude_tactical_advisor import ClaudeTacticalAdvisor
from .decision_priority_engine import DecisionPriorityEngine
import json
import os

def load_holy_grail_params():
    filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "holy_grail_params.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

HOLY_GRAIL_PARAMS = load_holy_grail_params()

class RiskEngine(BaseEngine):
    """
    Risk Engine: Validates trades against max drawdown and margin rules.
    """
    
    @property
    def engine_name(self) -> str:
        return "RiskEngine"

    def __init__(self, config=None, execution_engine=None):
        import os
        self.symbol = os.environ.get("TRADE_SYMBOL", "XAUUSD")
        if config and "symbol" in config:
            self.symbol = config["symbol"]
        super().__init__(config)
        self.execution_engine = execution_engine
        self.news_engine = None
        self.max_daily_drawdown = self.config.get("max_daily_drawdown", 0.02)
        self.current_drawdown = 0.0
        self.autotrade_enabled = False # Starts disabled for safety until toggled from UI
        import os
        self.max_positions = int(os.environ.get("AVERAGING_MAX_POSITIONS", "3"))
        self.hedging_enabled = os.environ.get("HEDGING_ENABLED", "True").lower() == "true"
        self._trailing_task = None
        self._intra_candle_task = None
        self._logical_sls = {}
        self._hedge_locks = {}
        self.last_trade_time = 0.0
        self._highest_profits = {}
        self.claude_advisor = ClaudeTacticalAdvisor()
        self.decision_priority_engine = DecisionPriorityEngine()

    async def start(self):
        self.logger.info("Risk engine online.")
        import asyncio
        self._trailing_task = asyncio.create_task(self._trailing_stop_loop())
        self._confidence_task = asyncio.create_task(self._confidence_method_loop())

    async def stop(self):
        if hasattr(self, "_trailing_task") and self._trailing_task:
            self._trailing_task.cancel()
        if hasattr(self, "_confidence_task") and self._confidence_task:
            self._confidence_task.cancel()
        self.logger.info("Risk engine offline.")

    def _get_daily_profit(self) -> float:
        import MetaTrader5 as mt5
        import datetime
        now = datetime.datetime.now()
        start_of_day = datetime.datetime(now.year, now.month, now.day)
        
        if not mt5.initialize():
            return 0.0
            
        deals = mt5.history_deals_get(start_of_day, now + datetime.timedelta(days=1))
        if deals is None:
            return 0.0
            
        total_profit = 0.0
        for d in deals:
            # DEAL_TYPE_BUY=0, DEAL_TYPE_SELL=1. Avoid DEAL_TYPE_BALANCE(2) and CREDIT(3)
            if d.type in (0, 1):
                total_profit += float(d.profit) + float(d.swap) + float(d.commission)
        return total_profit

    def _is_news_blackout(self) -> bool:
        import os
        import time
        blackout_enabled = os.environ.get("NEWS_BLACKOUT_ENABLED", "True").lower() == "true"
        if not blackout_enabled:
            return False
            
        if not hasattr(self, "news_engine") or not self.news_engine:
            return False
            
        now = time.time()
        # Suspend trading if any high-impact news was published within the last 30 minutes (1800s)
        # Using the RSS news_feed from news_engine
        if hasattr(self.news_engine, "news_feed"):
            for news in self.news_engine.news_feed:
                if news.get("relevancy", 0) >= 90 and news.get("regime", "") in ["High Volatility", "VIP (High Impact)"]:
                    news_time = news.get("timestamp", 0)
                    if 0 <= (now - news_time) <= 1800:
                        return True
        return False

    async def validate_trade(self, signal: str, price: float, confidence: float = 0.5):
        """
        Validates if a trade can be taken based on current risk exposure and market sentiment.
        """
        if not self.autotrade_enabled:
            self.logger.info(f"AutoTrade is OFF. Trade request ignored: {signal} at {price}")
            return
            

        # Debounce Filter (prevent multiple fast consecutive orders within 60 seconds)
        import time
        now = time.time()
        if now - self.last_trade_time < 60.0:
            self.logger.warning(f"Risk Reject: Debounce filter active. Last execution was {now - self.last_trade_time:.1f}s ago (Cooldown: 60s).")
            return
            
        # --- Safety Limits & News Blackout ---
        
        import MetaTrader5 as mt5
        symbol = self.symbol
        
        if mt5.initialize():
            positions = mt5.positions_get(symbol=symbol)
            has_positions = positions is not None and len(positions) > 0
            
            if not has_positions:

                if self._is_news_blackout():
                    self.logger.warning(f"Safety Lock: News Blackout active. Trading suspended for 30 mins.")
                    return
        
        # Default fallback values
        thresh = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.68"))
        max_op = int(os.environ.get("AVERAGING_MAX_POSITIONS", "4"))
        
        # Proactively refresh the session and dynamic parameters on the fly before checking entry constraints
        auto_lot = os.environ.get("AUTO_LOT_ENABLED", "False").lower() == "true"
        if auto_lot:
            import datetime
            utc_hour = datetime.datetime.utcnow().hour
            if utc_hour >= 22 or utc_hour < 8:
                session_name = "ASIA (Tokyo/Sydney)"
                lot = 0.40
                thresh = 0.65
                max_op = 4
            elif utc_hour >= 8 and utc_hour < 13:
                session_name = "LONDON (Europe)"
                lot = 0.30
                thresh = 0.68
                max_op = 4
            else:
                session_name = "NEW YORK (USA)"
                lot = 0.20
                thresh = 0.72
                max_op = 3
                
            self.config["lot_size"] = lot
            os.environ["BASE_LOT_SIZE"] = str(lot)
            
        # If Qwen AI has determined custom optimal parameters, we load those from the strategist engine (Always active)
        macro_strat = getattr(self, "macro_strategist", None)
        if not macro_strat and hasattr(self, "decision_engine") and self.decision_engine:
            macro_strat = getattr(self.decision_engine, "macro_strategist", None)
            
        if macro_strat:
            qwen_thresh = getattr(macro_strat, "optimal_confidence_threshold", None)
            qwen_max_op = getattr(macro_strat, "optimal_max_op", None)
            if qwen_thresh is not None: thresh = float(qwen_thresh)
            if qwen_max_op is not None: max_op = int(qwen_max_op)
            
        self.max_positions = max_op
        os.environ["AVERAGING_MAX_POSITIONS"] = str(max_op)
        self.logger.info(f"Entry parameter auto-refresh: Max OP={max_op}, Threshold={thresh}")
        
        # 0. Sniper Score Evaluation
        prob = confidence if signal == "BUY" else (1.0 - confidence)
        ues_score = int(round(prob * 100))
        sniper_score_threshold = int(os.environ.get("SNIPER_SCORE_THRESHOLD", "80"))
        is_sniper_entry = ues_score >= sniper_score_threshold
            
        # 1. News Cool-down Filter (15 minutes before or after high-impact news)
        if self.news_engine:
            high_impact_keywords = ["NFP", "CPI", "FOMC", "FED RATE", "INTEREST RATE", "PAYROLLS", "DECISION", "CENTRAL BANK"]
            
            for news in getattr(self.news_engine, "news_feed", []):
                headline = news.get("headline", "").upper()
                ts = news.get("timestamp", 0)
                if any(kw in headline for kw in high_impact_keywords):
                    age = abs(now - ts)
                    if age <= 900: # 15 minutes = 900 seconds
                        self.logger.warning(f"Risk Reject: Trade blocked by News Cool-down filter. High-Impact News: '{headline}' was published {age/60:.1f} minutes ago.")
                        return

        # Check if there is already an active position or pending order for the symbol to prevent multiple entries
        positions = mt5.positions_get(symbol=symbol)
        orders = mt5.orders_get(symbol=symbol)
        
        # Check if averaging is enabled
        averaging_enabled = os.environ.get("AVERAGING_ENABLED", "False").lower() == "true"
        
        is_averaging = False
        first_position_volume = None
        
        if (positions is not None and len(positions) > 0) or (orders is not None and len(orders) > 0):
            # Check global max positions limit
            if len(positions) >= self.max_positions:
                self.logger.info(f"Trade Blocked: Max global positions limit reached ({len(positions)}/{self.max_positions})")
                return
                
            # Filter positions of the same direction/type (0 = BUY, 1 = SELL)
            same_type_positions = [p for p in positions if p.type == (0 if signal == "BUY" else 1)]
            
            if len(same_type_positions) > 0:
                is_averaging = True
                # Get the oldest position in this direction to match its initial lot size
                first_pos = min(same_type_positions, key=lambda p: p.time)
                first_position_volume = float(first_pos.volume)
                
                if not averaging_enabled:
                    self.logger.info(f"Trade Blocked: Averaging is disabled and a position of direction {signal} already exists.")
                    return
                # We have open positions of the same type. Enforce spacing limit!
                avg_tf_name = os.environ.get("AVERAGING_TIMEFRAME", "M30")
                avg_mult = float(os.environ.get("AVERAGING_ATR_MULTIPLIER", "1.0"))
                
                tf_map = {
                    "M1": mt5.TIMEFRAME_M1,
                    "M5": mt5.TIMEFRAME_M5,
                    "M15": mt5.TIMEFRAME_M15,
                    "M30": mt5.TIMEFRAME_M30,
                    "H1": mt5.TIMEFRAME_H1,
                    "H4": mt5.TIMEFRAME_H4,
                    "D1": mt5.TIMEFRAME_D1
                }
                tf_const = tf_map.get(avg_tf_name, mt5.TIMEFRAME_M30)
                
                rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, 15)
                if rates is not None and len(rates) >= 15:
                    import numpy as np
                    highs = np.array([r[2] for r in rates])
                    lows = np.array([r[3] for r in rates])
                    closes = np.array([r[4] for r in rates])
                    
                    tr_list = []
                    for i in range(1, len(rates)):
                        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
                        tr_list.append(tr)
                    atr = float(np.mean(tr_list[-14:]))
                else:
                    atr = 9.09
                    
                # Adaptive Volatility & Market Session Spacing Adjustment
                import datetime
                utc_hour = datetime.datetime.now(datetime.timezone.utc).hour
                
                session_name = "Asian Session"
                session_mult = 0.8
                
                if utc_hour >= 8 and utc_hour < 13:
                    session_name = "European Session"
                    session_mult = 1.2
                elif utc_hour >= 13 and utc_hour < 17:
                    session_name = "London/NY Overlap"
                    session_mult = 2.2
                elif utc_hour >= 17 and utc_hour < 21:
                    session_name = "American Session"
                    session_mult = 1.8
                    
                avg_mult *= session_mult
                self.logger.info(f"Session Spacing: Current session: {session_name} (Hour: {utc_hour} UTC). Spacing multiplier adjusted to {avg_mult}x")
                
                regime = "Normal"
                if self.macro_strategist:
                    regime = getattr(self.macro_strategist, "volatility_regime", "Normal")
                
                # Stretch spacing by 2.0x during high news/volatility to prevent clustering grid positions
                if regime in ["HIGH_NEWS", "HIGH_VOLATILITY", "VIP (High Impact)"]:
                    avg_mult *= 2.0
                    self.logger.info(f"Dynamic Spacing: High volatility regime ({regime}) detected. Stretching grid multiplier to {avg_mult}x")
                    
                required_distance = atr * avg_mult
                
                # Get the last opened position of the same type
                last_pos = max(same_type_positions, key=lambda p: p.time)
                last_entry = float(last_pos.price_open)
                actual_distance = abs(price - last_entry)
                
                if actual_distance < required_distance:
                    self.logger.info(f"Trade Blocked: Price {price} is too close to last entry {last_entry} (Distance: {actual_distance:.2f} < Required: {required_distance:.2f})")
                    return
                    
                self.logger.info(f"Additional Position Triggered: Last Entry={last_entry}, Distance={actual_distance:.2f} >= Required={required_distance:.2f}")
            else:
                # No active positions of the same type exist (only opposing positions exist).
                # If hedging is enabled, this is allowed immediately without distance checks!
                if not self.hedging_enabled:
                    self.logger.info("Trade Blocked: Opposing active position exists, and Hedging is disabled.")
                    return
                self.logger.info(f"Hedging Entry Triggered: Opening {signal} opposite to current positions.")
            
        # Check Qwen3.7 Macro Strategist Bias
        if hasattr(self, "macro_strategist") and self.macro_strategist:
            bias = self.macro_strategist.macro_bias
            if bias == "WAIT":
                self.logger.warning(f"Risk Reject: Trade blocked by Macro Strategist Bias (WAIT)")
                return
            elif bias == "BUY_ONLY" and signal != "BUY":
                self.logger.warning(f"Risk Reject: {signal} blocked by Macro Strategist Bias (BUY_ONLY)")
                return
            elif bias == "SELL_ONLY" and signal != "SELL":
                self.logger.warning(f"Risk Reject: {signal} blocked by Macro Strategist Bias (SELL_ONLY)")
                return

        if self.current_drawdown >= self.max_daily_drawdown:
            self.logger.warning(f"Risk Reject: Max Drawdown Reached ({self.current_drawdown * 100:.2f}%)")
            return
            
        # Sentiment Execution Filter (GSI Composite)
        gsi_score = 50.0
        if self.news_engine:
            gsi_score = self.news_engine.current_sentiment_score
            
        # Calculate base volume based on Auto Lot settings and Risk Percent
        auto_lot = os.environ.get("AUTO_LOT_ENABLED", "False").lower() == "true"
        if auto_lot:
            acc = mt5.account_info()
            equity = acc.equity if acc else 10000.0
            risk_percent = float(os.environ.get("RISK_PERCENT", "1.0"))
            risk_usd = equity * (risk_percent / 100.0)
            
            # Retrieve ATR for dynamic SL distance calculation
            avg_tf_name = os.environ.get("AVERAGING_TIMEFRAME", "M30")
            tf_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1
            }
            tf_const = tf_map.get(avg_tf_name, mt5.TIMEFRAME_M30)
            rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, 15)
            atr = 9.09
            if rates is not None and len(rates) >= 15:
                import numpy as np
                highs = np.array([r[2] for r in rates])
                lows = np.array([r[3] for r in rates])
                closes = np.array([r[4] for r in rates])
                tr_list = []
                for i in range(1, len(rates)):
                    tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
                    tr_list.append(tr)
                atr = float(np.mean(tr_list[-14:]))
            
            # Read current SL multiplier from env or config (defaults to 1.5)
            sl_mult = float(os.environ.get("SL_MULTIPLIER", "1.5"))
            sl_distance = sl_mult * atr
            
            # Formula: base_volume = risk_amount / (SL_distance * contract_size)
            base_volume = risk_usd / (sl_distance * 100.0)
            base_volume = round(max(0.01, base_volume), 2)
            self.logger.info(f"Dynamic Auto LOT: Equity=${equity:.2f}, Risk={risk_percent}%, SL Distance={sl_distance:.2f} USD. Calculated Base Volume={base_volume} Lot")
        else:
            base_volume = float(os.environ.get("LOT_SIZE", "0.10"))
        
        # 2. Confidence-Based Sizing & Sniper Override
        sniper_lot = float(os.environ.get("SNIPER_LOT_SIZE", "0.0"))
        
        if is_sniper_entry and sniper_lot > 0:
            volume = sniper_lot
            self.logger.info(f"AI Sizing: Sniper Mode Activated (Score: {ues_score} >= {sniper_score_threshold}). Using strict Sniper Lot: {volume}")
        else:
            if prob <= 0.70:
                volume = base_volume * 0.5
                self.logger.info(f"AI Sizing: Low Confidence ({prob:.2f}), scaling lot from {base_volume} to {volume}")
            elif prob <= 0.80:
                volume = base_volume
                self.logger.info(f"AI Sizing: Normal Confidence ({prob:.2f}), lot set to {base_volume}")
            else:
                volume = base_volume * 1.5
                self.logger.info(f"AI Sizing: High Confidence ({prob:.2f}), scaling lot from {base_volume} to {volume}")
            
        volume = round(max(0.01, volume), 2)
        
        # Sentiment Filter (Scale or Reject)
        if signal == "BUY":
            if gsi_score < 30.0:
                self.logger.warning(f"Risk Reject: BUY order blocked due to severe BEARISH GSI index ({gsi_score:.1f}% < 30.0%)")
                return
            elif gsi_score < 35.0:
                scaled_volume = round(max(0.01, volume * 0.5), 2)
                self.logger.warning(f"Sentiment Filter: Scaling BUY lot from {volume} to {scaled_volume} due to BEARISH GSI index ({gsi_score:.1f}%)")
                volume = scaled_volume
        elif signal == "SELL":
            if gsi_score > 70.0:
                self.logger.warning(f"Risk Reject: SELL order blocked due to severe BULLISH GSI index ({gsi_score:.1f}% > 70.0%)")
                return
            elif gsi_score > 65.0:
                scaled_volume = round(max(0.01, volume * 0.5), 2)
                self.logger.warning(f"Sentiment Filter: Scaling SELL lot from {volume} to {scaled_volume} due to BULLISH GSI index ({gsi_score:.1f}%)")
                volume = scaled_volume
            
        if is_averaging and first_position_volume is not None:
            volume = first_position_volume
            self.logger.info(f"Grid Averaging Match: Overriding dynamic lot size with oldest grid position volume: {volume} Lot to maintain grid balance.")
            
        self.logger.info(f"Risk Approved: {signal} {volume} Lot at {price}")
        if self.execution_engine:
            import time
            self.last_trade_time = time.time()
            await self.execution_engine.execute_order(symbol, signal, volume)

    async def _trailing_stop_loop(self):
        """
        Background trailing stop loop running every 5 seconds.
        Handles:
        1. Universal emergency drawdown exit (Basket exit).
        2. Daily profit/loss capping.
        3. Trailing Stop / Breakeven Lock on individual standalone positions.
        """
        import json
        import os
        
        self._highest_pips = getattr(self, "_highest_pips", {})
        news_feed_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "news_feed.json")
        """
        4. Dynamic Hedge Locking (Hedge-Lock trigger at logical SL).
        5. AI Review Loop (Analyzes macroeconomic bias after 15 minutes to resolve the hedge).
        """
        import asyncio
        import MetaTrader5 as mt5
        import os
        import time
        import numpy as np
        
        while True:
            try:
                if mt5.initialize():
                    symbol = self.symbol
                    positions = mt5.positions_get(symbol=symbol)
                    
                    # 5. AI Review Loop (15 minutes after hedge lock)
                    now_time = time.time()
                    resolved_tickets = []
                    for orig_ticket, lock_info in list(self._hedge_locks.items()):
                        age = now_time - lock_info["lock_time"]
                        if age >= 900: # 15 minutes = 900 seconds
                            bias = "WAIT"
                            if hasattr(self, "macro_strategist") and self.macro_strategist:
                                bias = self.macro_strategist.macro_bias
                                
                            opp_ticket = lock_info["opposing_ticket"]
                            
                            if bias == "SELL_ONLY" and lock_info["type"] == 0: # Original BUY, locked by SELL
                                # Confirm downtrend: close original BUY position
                                if self.execution_engine:
                                    self.logger.info(f"AI Hedge Review: Trend confirmed DOWN. Closing original BUY #{orig_ticket}.")
                                    await self.execution_engine.close_position(orig_ticket)
                                    if hasattr(self.execution_engine, "notifier") and self.execution_engine.notifier:
                                        msg = (
                                            f"🧠 <b>AI RESOLVED HEDGE: TREND DOWN CONFIRMED</b>\n\n"
                                            f"Analisis 15 menit pasca-berita mengkonfirmasi tren turun (bias: SELL_ONLY).\n"
                                            f"Memotong rugi posisi BUY #{orig_ticket} dan membiarkan posisi SELL #{opp_ticket} berjalan."
                                        )
                                        await self.execution_engine.notifier._send_safe(msg)
                                resolved_tickets.append(orig_ticket)
                            elif bias == "BUY_ONLY" and lock_info["type"] == 1: # Original SELL, locked by BUY
                                # Confirm uptrend: close original SELL position
                                if self.execution_engine:
                                    self.logger.info(f"AI Hedge Review: Trend confirmed UP. Closing original SELL #{orig_ticket}.")
                                    await self.execution_engine.close_position(orig_ticket)
                                    if hasattr(self.execution_engine, "notifier") and self.execution_engine.notifier:
                                        msg = (
                                            f"🧠 <b>AI RESOLVED HEDGE: TREND UP CONFIRMED</b>\n\n"
                                            f"Analisis 15 menit pasca-berita mengkonfirmasi tren naik (bias: BUY_ONLY).\n"
                                            f"Memotong rugi posisi SELL #{orig_ticket} dan membiarkan posisi BUY #{opp_ticket} berjalan."
                                        )
                                        await self.execution_engine.notifier._send_safe(msg)
                                resolved_tickets.append(orig_ticket)
                                
                    for t in resolved_tickets:
                        self._hedge_locks.pop(t, None)
                        self._logical_sls.pop(t, None)

                    if positions:
                        # 1. Dynamic Basket Take Profit (Volume-Weighted Recovery)
                        combined_profit = sum(float(p.profit) for p in positions)
                        total_volume = sum(float(p.volume) for p in positions)
                        
                        # Scale target profit: $15.00 for every 0.10 lot size (e.g. 1.0 lot targets $150.00)
                        dynamic_target = (total_volume / 0.10) * 15.00
                        
                        # Adjust target based on current market session
                        import datetime
                        utc_hour = datetime.datetime.now(datetime.timezone.utc).hour
                        if utc_hour >= 0 and utc_hour < 8: # Asian Session (chop): Exit quickly!
                            dynamic_target *= 0.7
                        elif utc_hour >= 13 and utc_hour < 21: # US Session (trend): Hold for more!
                            dynamic_target *= 1.3
                            
                        basket_tp = max(5.00, round(dynamic_target, 2))
                        
                        if len(positions) >= 2 and combined_profit >= basket_tp:
                            self.logger.info(f"AI Basket Target Achieved: Combined Profit {combined_profit:.2f} >= Dynamic Target {basket_tp:.2f} (Vol: {total_volume:.2f} Lot). Closing all positions!")
                            if self.execution_engine:
                                await self.execution_engine.close_all_positions()
                            continue
                            
                        # Calculate ATR for SL/TP calculations
                        avg_tf_name = os.environ.get("AVERAGING_TIMEFRAME", "M30")
                        tf_map = {
                            "M1": mt5.TIMEFRAME_M1,
                            "M5": mt5.TIMEFRAME_M5,
                            "M15": mt5.TIMEFRAME_M15,
                            "M30": mt5.TIMEFRAME_M30,
                            "H1": mt5.TIMEFRAME_H1,
                            "H4": mt5.TIMEFRAME_H4,
                            "D1": mt5.TIMEFRAME_D1
                        }
                        tf_const = tf_map.get(avg_tf_name, mt5.TIMEFRAME_M30)
                        rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, 15)
                        if rates is not None and len(rates) >= 15:
                            highs = np.array([r[2] for r in rates])
                            lows = np.array([r[3] for r in rates])
                            closes = np.array([r[4] for r in rates])
                            tr_list = []
                            for i in range(1, len(rates)):
                                tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
                                tr_list.append(tr)
                            atr = float(np.mean(tr_list[-14:]))
                        else:
                            atr = 9.09
                            
                        sl_mult = 1.5
                        tp_mult = 3.0
                        if hasattr(self, "macro_strategist") and self.macro_strategist:
                            sl_mult = self.macro_strategist.sl_mult
                            tp_mult = self.macro_strategist.tp_mult

                        # 2. Consolidated Basket SL/TP Synchronization
                        for direction in [0, 1]: # 0 = BUY, 1 = SELL
                            dir_positions = [p for p in positions if p.type == direction]
                            if len(dir_positions) >= 2:
                                total_vol = sum(p.volume for p in dir_positions)
                                weighted_sum = sum(p.price_open * p.volume for p in dir_positions)
                                avg_entry = weighted_sum / total_vol
                                
                                # Dynamic SL Compression: Tighten SL multiplier as grid size grows
                                grid_size = len(dir_positions)
                                sl_tightener = 1.0 if grid_size < 2 else (0.50 if grid_size == 2 else 0.35)
                                tightened_sl_mult = min(1.0, sl_mult) * sl_tightener
                                
                                if direction == 0: # BUY
                                    logical_sl = round(avg_entry - (tightened_sl_mult * atr), 2)
                                    disaster_sl = round(avg_entry - (tightened_sl_mult * atr * 1.5), 2)
                                    target_tp = round(avg_entry + (tp_mult * atr), 2)
                                if direction == 1: # SELL
                                    logical_sl = round(avg_entry + (tightened_sl_mult * atr), 2)
                                    disaster_sl = round(avg_entry + (tightened_sl_mult * atr * 1.5), 2)
                                    target_tp = round(avg_entry - (tp_mult * atr), 2)
                                    
                                for p in dir_positions:
                                    self._logical_sls[p.ticket] = logical_sl
                                    if abs(float(p.sl) - disaster_sl) > 0.05 or abs(float(p.tp) - target_tp) > 0.05:
                                        self.logger.info(f"Syncing Basket Position #{p.ticket}: Modifying SL to Disaster {disaster_sl}, TP to {target_tp} (Based on Average Entry: {avg_entry:.2f})")
                                        self._modify_position_sl(p.ticket, disaster_sl, target_tp)
                                        
                        # 3. Individual position trailing stop logic
                        for p in positions:
                            ticket = p.ticket
                            p_type = p.type # 0 = BUY, 1 = SELL
                            entry_price = float(p.price_open)
                            current_price = float(p.price_current)
                            current_sl = float(p.sl)
                            
                            same_dir_count = sum(1 for pos in positions if pos.type == p_type)
                            
                            # Handle standalone target logical SL & disaster SL
                            if same_dir_count == 1:
                                if p_type == 0: # BUY
                                    logical_sl = round(entry_price - (min(1.0, sl_mult) * atr), 2)
                                    disaster_sl = round(entry_price - (min(1.0, sl_mult) * atr * 1.5), 2)
                                else: # SELL
                                    logical_sl = round(entry_price + (min(1.0, sl_mult) * atr), 2)
                                    disaster_sl = round(entry_price + (min(1.0, sl_mult) * atr * 1.5), 2)
                                    
                                self._logical_sls[ticket] = logical_sl
                                if abs(current_sl - disaster_sl) > 0.05:
                                    self._modify_position_sl(ticket, disaster_sl, p.tp)
                                    
                            # 4. Dynamic Hedge Locking (Check if price hit logical SL)
                            logical_sl = self._logical_sls.get(ticket)
                            if logical_sl:
                                hit_hedge = False
                                if p_type == 0 and current_price <= logical_sl:
                                    hit_hedge = True
                                elif p_type == 1 and current_price >= logical_sl:
                                    hit_hedge = True
                                    
                                if hit_hedge and ticket not in self._hedge_locks:
                                    opp_action = "SELL" if p_type == 0 else "BUY"
                                    self.logger.warning(f"Logical SL hit at {logical_sl} for Position #{ticket}. Triggering Hedge Lock: {opp_action} {p.volume} Lot.")
                                    
                                    if self.execution_engine:
                                        res = await self.execution_engine.execute_order(symbol, opp_action, p.volume)
                                        if res.get("status") == "success":
                                            opp_ticket = int(res.get("ticket"))
                                            self._hedge_locks[ticket] = {
                                                "lock_time": time.time(),
                                                "opposing_ticket": opp_ticket,
                                                "volume": p.volume,
                                                "type": p_type
                                            }
                                            
                                            # Send Telegram notification
                                            if hasattr(self.execution_engine, "notifier") and self.execution_engine.notifier:
                                                msg = (
                                                    f"🔒 <b>HEDGE LOCK DIPICU (HEDGE ACTIVATED)</b>\n\n"
                                                    f"Posisi #{ticket} ({'BUY' if p_type == 0 else 'SELL'}) menyentuh SL logis di {logical_sl}.\n"
                                                    f"Membuka posisi kunci lawan #{opp_ticket} ({opp_action}) sebesar {p.volume} lot untuk membekukan kerugian."
                                                )
                                                await self.execution_engine.notifier._send_safe(msg)

                            # Method 10: Hybrid (Trailing Stop + Dynamic Break-Even) Exits
                            # Bypass individual trailing exits for forecast-hlc-bound grid to let basket TP execute collectively
                            active_method = os.environ.get("ACTIVE_METHOD", "intra-candle-scalper")
                            if ticket not in self._hedge_locks and active_method != "forecast-hlc-bound":
                                pips = (current_price - entry_price) if p_type == 0 else (entry_price - current_price)
                                usd_profit = pips * 100.0 * float(p.volume)
                                 
                                # Track peak profit achieved by this ticket
                                if ticket not in self._highest_profits:
                                    self._highest_profits[ticket] = 0.0
                                if usd_profit > self._highest_profits[ticket]:
                                    self._highest_profits[ticket] = usd_profit
                                     
                                peak_prof = self._highest_profits[ticket]
                                # Read latest AI Confidence and Macro Impact from news_feed
                                latest_confidence = 0.75
                                news_impact = "LOW"
                                fed_shock = 0
                                if os.path.exists(news_feed_path):
                                    try:
                                        with open(news_feed_path, "r", encoding="utf-8") as f:
                                            feed_data = json.load(f)
                                            macro_data = feed_data.get("macro_analysis", {})
                                            latest_confidence = float(macro_data.get("causal_confidence", 0.75))
                                            news_impact = str(macro_data.get("news_event_impact", "LOW")).upper()
                                            fed_shock = int(macro_data.get("fed_shock_level", 0))
                                    except:
                                        pass
                                
                                # Track peak pips (price movement in nominal terms) for dynamic pip-based trailing
                                if ticket not in self._highest_pips:
                                    self._highest_pips[ticket] = 0.0
                                if pips > self._highest_pips[ticket]:
                                    self._highest_pips[ticket] = pips
                                     
                                peak_pips = self._highest_pips[ticket]
                                should_exit = False
                                exit_reason = ""
                                 
                                # Confidence-Based Dynamic Trailing Stop Tiers
                                if latest_confidence >= 0.85 and (news_impact == "HIGH" or fed_shock >= 4):
                                    ts_activation = 10.00 # +$10.00 Gold movement (100 pips)
                                    ts_distance = 7.00    # Trail by 70 pips (Kebal guncangan NFP)
                                    tier_str = "Tier 4 (Macro Badai/NFP)"
                                elif latest_confidence < 0.75:
                                    ts_activation = 1.50 # +$1.50 Gold movement (15 pips)
                                    ts_distance = 1.00   # Trail by 10 pips
                                    tier_str = "Tier 1 (Ragu)"
                                elif latest_confidence < 0.85:
                                    ts_activation = 2.50 # +$2.50 Gold movement (25 pips)
                                    ts_distance = 1.50   # Trail by 15 pips
                                    tier_str = "Tier 2 (Normal)"
                                else:
                                    ts_activation = 4.00 # +$4.00 Gold movement (40 pips)
                                    ts_distance = 2.50   # Trail by 25 pips
                                    tier_str = "Tier 3 (Yakin Penuh)"
                                
                                # 1. Dynamic Confidence-Based Trailing Stop Lock-in
                                if peak_pips >= ts_activation and pips < (peak_pips - ts_distance):
                                    should_exit = True
                                    exit_reason = f"Dynamic Trailing Stop [{tier_str} - Conf: {latest_confidence*100:.0f}%] (Peak: +{peak_pips:.2f} Pips, Current: +{pips:.2f} Pips)"
                                # 2. Dynamic Break-Even ($30 trigger, exit at $0.00 or reversal)
                                elif peak_prof >= 30.0 and usd_profit <= 0.0:
                                    should_exit = True
                                    exit_reason = f"Break-Even Protection (Peak: ${peak_prof:.2f}, Current: ${usd_profit:.2f})"
                                     
                                if should_exit and self.execution_engine:
                                    self.logger.info(f"AI Exit Triggered for Position #{ticket}: {exit_reason}. Closing position!")
                                    await self.execution_engine.close_position(ticket)
                                    self._highest_profits.pop(ticket, None)
                                    self._highest_pips.pop(ticket, None)
                                     
                                    # Send Telegram Notification
                                    if hasattr(self.execution_engine, "notifier") and self.execution_engine.notifier:
                                        msg = (
                                            f"👑 <b>AI HYBRID EXIT EXECUTED (METHOD 10)</b>\n\n"
                                            f"Posisi #{ticket} ({'BUY' if p_type == 0 else 'SELL'}) telah ditutup otomatis.\n"
                                            f"• <b>Alasan</b>: <code>{exit_reason}</code>\n"
                                            f"• <b>Lot Size</b>: <code>{p.volume} Lot</code>\n"
                                            f"• <b>Profit Terkunci</b>: <code>${usd_profit:.2f}</code>"
                                        )
                                        await self.execution_engine.notifier._send_safe(msg)
            except Exception as e:
                self.logger.error(f"Error in trailing stop loop: {e}")
            await asyncio.sleep(5)

    def _modify_position_sl(self, ticket: int, sl: float, tp: float):
        import MetaTrader5 as mt5
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": sl,
            "tp": tp
        }
        res = mt5.order_send(request)
        if res.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(f"Breakeven Locked: Moved SL of Position #{ticket} to {sl} (Profit Protected)")
        else:
            self.logger.warning(f"Failed to move SL of Position #{ticket} to {sl}: {res.comment}")


    async def _confidence_method_loop(self):
        import asyncio
        from backend.main import app
        import os
        import MetaTrader5 as mt5

        while True:
            try:
                # Get autotrade status
                autotrade_enabled = os.environ.get("AUTOTRADE_ENABLED", "False").lower() == "true"
                if not autotrade_enabled:
                    await asyncio.sleep(1)
                    continue

                if not getattr(self, 'execution_engine', None):
                    await asyncio.sleep(1)
                    continue

                # Ensure MT5 is connected
                if not mt5.terminal_info():
                    await asyncio.sleep(1)
                    continue

                # 1. Fetch Decision Engine Smoothed Confidence & Action
                de = getattr(app.state, 'decision_engine', None)
                if not de:
                    await asyncio.sleep(1)
                    continue
                
                # We expect decision engine to give a smoothed confidence and signal
                confidence = de.smoothed_confidence
                raw_signal = de.current_signal

                if confidence < 0.65 or raw_signal not in ["BUY", "SELL"]:
                    await asyncio.sleep(1)
                    continue

                # 2. Fetch Technical Indicators from Data Engine
                data_e = getattr(app.state, 'data_engine', None)
                if not data_e or not getattr(data_e, 'technicals', None):
                    await asyncio.sleep(1)
                    continue
                    
                techs = data_e.technicals.get(self.symbol)
                if not techs:
                    await asyncio.sleep(1)
                    continue

                rsi = techs.get("rsi", 50)
                macd = techs.get("macd", 0)
                macd_signal = techs.get("macd_signal", 0)
                atr = techs.get("atr", 0.0010) # Safe default if missing

                # 3. Technical Confirmation Filter
                # Buy confirmed if MACD > Signal and RSI < 70 (not overbought)
                # Sell confirmed if MACD < Signal and RSI > 30 (not oversold)
                is_confirmed = False
                if raw_signal == "BUY" and macd > macd_signal and rsi < 70:
                    is_confirmed = True
                elif raw_signal == "SELL" and macd < macd_signal and rsi > 30:
                    is_confirmed = True
                    
                if not is_confirmed:
                    await asyncio.sleep(1)
                    continue

                # 4. Check Open Positions (Avoid stacking)
                positions = mt5.positions_get(symbol=self.symbol)
                num_positions = len(positions) if positions else 0
                max_pos = int(os.environ.get("AVERAGING_MAX_POSITIONS", "3"))
                
                if num_positions >= max_pos:
                    await asyncio.sleep(1)
                    continue

                # 5. Calculate Dynamic Risk (1% to 5%)
                # Confidence 0.65 -> 1.0% Risk
                # Confidence 1.00 -> 5.0% Risk
                capped_conf = min(max(confidence, 0.65), 1.0)
                risk_pct = 1.0 + ((capped_conf - 0.65) / 0.35) * 4.0
                
                # Fetch Balance
                acc = mt5.account_info()
                if not acc:
                    await asyncio.sleep(1)
                    continue
                    
                balance = acc.balance
                risk_amount = balance * (risk_pct / 100.0)
                
                # Point value logic (Standard Lot $10/pip or custom based on symbol)
                # Just scale using SL (ATR) if possible, but for simplicity we will rely on 
                # a base lot multiplier logic or standard os.environ LOT_SIZE if dynamic is too risky.
                # However, user explicitly requested "Risk 1 - 5%".
                
                sl_distance = atr * 1.5 # We use 1.5 ATR for SL
                
                # Convert SL distance to dollars
                multiplier = 100000.0
                if "XAU" in self.symbol: multiplier = 100.0
                if "JPY" in self.symbol: multiplier = 1000.0
                
                pip_value_per_lot = multiplier # Approximate
                
                # Lot = Risk Amount / (SL Distance * Pip Value per lot)
                calculated_lot = risk_amount / (sl_distance * pip_value_per_lot)
                
                # Clamp lot
                min_lot = 0.01
                max_lot = 5.0
                final_lot = max(min_lot, min(max_lot, round(calculated_lot, 2)))

                # 6. Execute Order
                self.logger.info(f"[Confidence Method] {raw_signal} on {self.symbol} | Conf: {confidence:.2f} | Risk: {risk_pct:.1f}% (${risk_amount:.2f}) | Lot: {final_lot}")
                
                res = await self.execution_engine.execute_order(
                    symbol=self.symbol,
                    action=raw_signal,
                    lot_size=final_lot
                )
                
                # Prevent spamming
                await asyncio.sleep(60)

            except Exception as e:
                self.logger.error(f"Error in _confidence_method_loop: {e}")
                await asyncio.sleep(5)
