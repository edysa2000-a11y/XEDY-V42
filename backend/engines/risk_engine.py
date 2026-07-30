from .base_engine import BaseEngine

class RiskEngine(BaseEngine):
    """
    Risk Engine: Validates trades against max drawdown and margin rules.
    """
    
    @property
    def engine_name(self) -> str:
        return "RiskEngine"

    def __init__(self, config=None, execution_engine=None):
        super().__init__(config)
        self.execution_engine = execution_engine
        self.news_engine = None
        self.max_daily_drawdown = self.config.get("max_daily_drawdown", 0.02)
        self.current_drawdown = 0.0
        self.autotrade_enabled = False # Starts disabled for safety until toggled from UI
        import os
        self.max_positions = int(os.getenv("AVERAGING_MAX_POSITIONS", "3"))
        self.hedging_enabled = os.getenv("HEDGING_ENABLED", "True").lower() == "true"
        self._trailing_task = None
        self._logical_sls = {}
        self._hedge_locks = {}
        self.last_trade_time = 0.0

    async def start(self):
        self.logger.info("Risk engine online.")
        import asyncio
        self._trailing_task = asyncio.create_task(self._trailing_stop_loop())

    async def stop(self):
        if self._trailing_task:
            self._trailing_task.cancel()
        self.logger.info("Risk engine offline.")

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
            
        import os
        import MetaTrader5 as mt5
        symbol = os.getenv("TRADE_SYMBOL", "XAUUSD")
        
        # Proactively refresh the session and dynamic parameters on the fly before checking entry constraints
        auto_lot = os.getenv("AUTO_LOT_ENABLED", "False").lower() == "true"
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
                
            # If Qwen AI has determined custom optimal parameters, we load those from the strategist engine
            macro_strat = getattr(self, "macro_strategist", None)
            if not macro_strat and hasattr(self, "decision_engine") and self.decision_engine:
                macro_strat = getattr(self.decision_engine, "macro_strategist", None)
                
            if macro_strat:
                qwen_thresh = getattr(macro_strat, "optimal_confidence_threshold", None)
                qwen_max_op = getattr(macro_strat, "optimal_max_op", None)
                if qwen_thresh is not None: thresh = float(qwen_thresh)
                if qwen_max_op is not None: max_op = int(qwen_max_op)
                
            self.max_positions = max_op
            self.config["lot_size"] = lot
            os.environ["BASE_LOT_SIZE"] = str(lot)
            os.environ["AVERAGING_MAX_POSITIONS"] = str(max_op)
            self.logger.info(f"Entry parameter auto-refresh: Session={session_name}, Lot={lot}, Max OP={max_op}, Threshold={thresh}")
        
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
        averaging_enabled = os.getenv("AVERAGING_ENABLED", "False").lower() == "true"
        
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
                avg_tf_name = os.getenv("AVERAGING_TIMEFRAME", "M30")
                avg_mult = float(os.getenv("AVERAGING_ATR_MULTIPLIER", "1.0"))
                
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
        auto_lot = os.getenv("AUTO_LOT_ENABLED", "False").lower() == "true"
        if auto_lot:
            acc = mt5.account_info()
            equity = acc.equity if acc else 10000.0
            risk_percent = float(os.getenv("RISK_PERCENT", "1.0"))
            risk_usd = equity * (risk_percent / 100.0)
            
            # Retrieve ATR for dynamic SL distance calculation
            avg_tf_name = os.getenv("AVERAGING_TIMEFRAME", "M30")
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
            sl_mult = float(os.getenv("SL_MULTIPLIER", "1.5"))
            sl_distance = sl_mult * atr
            
            # Formula: base_volume = risk_amount / (SL_distance * contract_size)
            base_volume = risk_usd / (sl_distance * 100.0)
            base_volume = round(max(0.01, base_volume), 2)
            self.logger.info(f"Dynamic Auto LOT: Equity=${equity:.2f}, Risk={risk_percent}%, SL Distance={sl_distance:.2f} USD. Calculated Base Volume={base_volume} Lot")
        else:
            base_volume = float(os.getenv("LOT_SIZE", "0.10"))
        
        # 2. Confidence-Based Sizing (Dynamic Lot Sizing)
        prob = confidence if signal == "BUY" else (1.0 - confidence)
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
        Performs:
        1. Basket Take Profit Closeout (Hedge Recovery).
        2. Consolidated Basket SL/TP Synchronization (Disaster SL on MT5, Logical SL tracked in memory).
        3. Trailing Stop / Breakeven Lock on individual standalone positions.
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
                    symbol = os.getenv("TRADE_SYMBOL", "XAUUSD")
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
                        # 1. Basket Take Profit (Hedge Recovery Closeout)
                        combined_profit = sum(float(p.profit) for p in positions)
                        basket_tp = float(os.getenv("BASKET_TP", "5.00"))
                        
                        if len(positions) >= 2 and combined_profit >= basket_tp:
                            self.logger.info(f"AI Basket Target Achieved: Combined Profit {combined_profit:.2f} >= Target {basket_tp:.2f}. Closing all positions!")
                            if self.execution_engine:
                                await self.execution_engine.close_all_positions()
                            continue
                            
                        # Calculate ATR for SL/TP calculations
                        avg_tf_name = os.getenv("AVERAGING_TIMEFRAME", "M30")
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
                                
                                if direction == 0: # BUY
                                    logical_sl = round(avg_entry - (sl_mult * atr), 2)
                                    disaster_sl = round(avg_entry - (sl_mult * atr * 3.0), 2)
                                    target_tp = round(avg_entry + (tp_mult * atr), 2)
                                if direction == 1: # SELL
                                    logical_sl = round(avg_entry + (sl_mult * atr), 2)
                                    disaster_sl = round(avg_entry + (sl_mult * atr * 3.0), 2)
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
                                    logical_sl = round(entry_price - (sl_mult * atr), 2)
                                    disaster_sl = round(entry_price - (sl_mult * atr * 3.0), 2)
                                else: # SELL
                                    logical_sl = round(entry_price + (sl_mult * atr), 2)
                                    disaster_sl = round(entry_price + (sl_mult * atr * 3.0), 2)
                                    
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

                            # Standalone breakeven trailing stop
                            if same_dir_count == 1 and ticket not in self._hedge_locks:
                                if p_type == 0: # BUY
                                    floating_points = current_price - entry_price
                                    if floating_points >= 2.50:
                                        target_sl = round(entry_price + 0.50, 2)
                                        if current_sl < entry_price:
                                            self._modify_position_sl(ticket, target_sl, p.tp)
                                elif p_type == 1: # SELL
                                    floating_points = entry_price - current_price
                                    if floating_points >= 2.50:
                                        target_sl = round(entry_price - 0.50, 2)
                                        if current_sl == 0 or current_sl > entry_price:
                                            self._modify_position_sl(ticket, target_sl, p.tp)
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
