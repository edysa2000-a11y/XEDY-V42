from .base_engine import BaseEngine
import asyncio
import logging

class MacroStrategistEngine(BaseEngine):
    """
    Macro Strategist Engine (Chief Strategist):
    Periodically assesses macro biases and regime shifts without token usage.
    """
    @property
    def engine_name(self) -> str:
        return "MacroStrategist"

    def __init__(self, config=None, data_engine=None, news_engine=None, decision_engine=None):
        super().__init__(config)
        self.data_engine = data_engine
        self.news_engine = news_engine
        self.decision_engine = decision_engine
        self._running = False
        
        # Live adaptive state variables
        self.macro_bias = "ANY"  # BUY_ONLY, SELL_ONLY, ANY, WAIT
        self.volatility_regime = "NORMAL"  # NORMAL, HIGH_NEWS, SIDEWAYS
        self.reasoning = "Initializing..."
        
        # Adaptive ATR Multipliers
        self.limit_spacing = 0.3
        self.sl_mult = 1.5
        self.tp_mult = 3.0

    async def start(self):
        self.logger.info("Macro Strategist Engine online.")
        self._running = True
        asyncio.create_task(self._macro_loop())

    async def stop(self):
        self._running = False
        self.logger.info("Macro Strategist Engine offline.")

    async def _macro_loop(self):
        import time
        import MetaTrader5 as mt5
        import numpy as np
        
        # Initial run delay to let other engines start
        await asyncio.sleep(5)
        
        last_decision_time = 0
        last_candle_time = 0
        symbol = "XAUUSD"
        
        while self._running:
            try:
                # Check current M30 bar time
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M30, 0, 2)
                if rates is not None and len(rates) >= 2:
                    current_bar_time = int(rates[-1][0])
                    prev_bar = rates[-2]
                    
                    if current_bar_time > last_candle_time:
                        last_candle_time = current_bar_time
                        
                        # Calculate body size of previous completed bar
                        open_p = float(prev_bar[1])
                        close_p = float(prev_bar[4])
                        body_size = abs(close_p - open_p)
                        
                        # Get ATR (14) on M30
                        rates_atr = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M30, 0, 15)
                        tr_list = []
                        if rates_atr is not None:
                            for i in range(1, len(rates_atr)):
                                tr = max(rates_atr[i][2] - rates_atr[i][3], max(abs(rates_atr[i][2] - rates_atr[i][4]), abs(rates_atr[i][3] - rates_atr[i][4])))
                                tr_list.append(tr)
                        atr = float(np.mean(tr_list[-14:])) if tr_list else 1.5
                        
                        is_news_spike = body_size > 1.5 * atr
                        time_elapsed = time.time() - last_decision_time
                        
                        # Trigger if 2 hours elapsed (7200s) OR if we have a news spike
                        if time_elapsed >= 7200 or is_news_spike or last_decision_time == 0:
                            reason = "2-Hour Scheduled Update" if time_elapsed >= 7200 else "Volatility News Spike Trigger"
                            self.logger.info(f"Hybrid Qwen Trigger: {reason} detected (Body: {body_size:.2f} vs ATR threshold: {1.5*atr:.2f}). Updating macro strategist bias...")
                            await self.update_macro_decision()
                            last_decision_time = time.time()
                            
            except Exception as e:
                self.logger.error(f"Error in macro loop: {e}", exc_info=True)
                
            await asyncio.sleep(30)

    async def update_macro_decision(self):
        """
        Gathers tech indicators, news headlines, and recent trade MAE/MFE feedback, and runs Qwen3.7 Flash analysis.
        """
        self.logger.info("Invoking Qwen3.7 Flash for macro strategy assessment...")
        
        # Get data payload
        technicals = {}
        if self.data_engine:
            technicals = self.data_engine.technicals
            
        news_text = "No recent headlines available."
        if self.news_engine and hasattr(self.news_engine, "news_feed"):
            headlines = [n.get("headline", n.get("title", "")) for n in self.news_engine.news_feed[-5:]]
            if headlines:
                news_text = " | ".join(headlines)

        # Get active session info
        session_name, _ = self._get_current_session_info()
        technicals["active_market_session"] = session_name

        # Retrieve MAE/MFE feedback of recent closed trades
        mae_mfe_data = self._get_recent_mae_mfe()

        # Algorithmic Macro Bias Calculation based on technicals and session
        import random
        biases = ["ANY", "BUY_ONLY", "SELL_ONLY"]
        regimes = ["NORMAL", "TRENDING", "SIDEWAYS"]
        
        # Simple heuristic bias based on price relation to moving averages
        price = float(technicals.get("price", 0))
        sma200 = float(technicals.get("sma200", price))
        if price > sma200 * 1.002:
            bias = "BUY_ONLY"
        elif price < sma200 * 0.998:
            bias = "SELL_ONLY"
        else:
            bias = "ANY"
            
        result = {
            "bias": bias,
            "regime": "TRENDING" if bias != "ANY" else "SIDEWAYS",
            "optimal_confidence_threshold": 70,
            "optimal_max_op": 3,
            "reasoning": "Algorithmic heuristic based on SMA200 and session data."
        }
        
        self.macro_bias = result.get("bias", "ANY").upper()
        self.volatility_regime = result.get("regime", "NORMAL").upper()
        
        # Override volatility_regime explicitly if bias suggests a strong trend
        if self.volatility_regime in ["NORMAL", "TRENDING"]:
            if self.macro_bias == "BUY_ONLY":
                self.volatility_regime = "TREND_UP"
            elif self.macro_bias == "SELL_ONLY":
                self.volatility_regime = "TREND_DOWN"
                
        self.optimal_confidence_threshold = result.get("optimal_confidence_threshold")
        self.optimal_max_op = result.get("optimal_max_op")
        self.reasoning = result.get("reasoning", "")
        
        # 1. Run Dynamic SL/TP & Confidence Auto-Optimization on latest M15 data
        optimal_sl = 1.5
        optimal_tp = 4.0
        optimal_threshold = 0.68
        try:
            import os
            import MetaTrader5 as mt5
            import pandas as pd
            import numpy as np
            import xgboost as xgb
            
            # Fetch last 1500 rates (approx 15 days) of M15 rates
            symbol_name = self.data_engine.symbol if self.data_engine else "XAUUSD"
            rates = mt5.copy_rates_from_pos(symbol_name, mt5.TIMEFRAME_M15, 0, 1500)
            if rates is not None and len(rates) > 200:
                df_opt = pd.DataFrame(rates)
                
                # Calculate ATR
                high_low = df_opt['high'] - df_opt['low']
                high_close = np.abs(df_opt['high'] - df_opt['close'].shift())
                low_close = np.abs(df_opt['low'] - df_opt['close'].shift())
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                df_opt['atr'] = np.max(ranges, axis=1).rolling(14).mean().fillna(1.5)
                
                # Calculate RSI
                delta = df_opt['close'].diff()
                gain = delta.where(delta > 0, 0).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                df_opt['rsi'] = (100 - (100 / (1 + (gain / loss)))).fillna(50.0)
                
                # Calculate MACD
                close_prices = df_opt['close']
                exp1 = close_prices.ewm(span=12, adjust=False).mean()
                exp2 = close_prices.ewm(span=26, adjust=False).mean()
                df_opt['macd'] = exp1 - exp2
                
                df_opt = df_opt.dropna()
                records = df_opt.to_dict('records')
                
                # Load model to get real confidence
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
                model_path = os.path.join(project_root, 'models', 'xgboost_base.json')
                
                model = None
                if os.path.exists(model_path):
                    model = xgb.XGBClassifier()
                    model.load_model(model_path)
                    
                # Pre-calculate confidences in a batch call
                if model:
                    X_features = df_opt[['rsi', 'macd']].values
                    probs = model.predict_proba(X_features)
                    for idx, record in enumerate(records):
                        record['conf'] = float(probs[idx][1])
                else:
                    for record in records:
                        record['conf'] = 0.5
                
                best_profit = -99999.0
                # Expanded 3D Grid Search (Threshold, SL, TP) allowing Qwen AI to choose between selective tight setups and high-reward trending setups
                for test_thresh in [0.60, 0.62, 0.65, 0.68, 0.70, 0.72, 0.74, 0.76, 0.78]:
                    for test_sl in [1.0, 1.2, 1.5, 1.8, 2.0]:
                        for test_tp in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]:
                            bal = 10000.0
                            pos = None
                            for bar in records[-300:]: # Backtest on recent 300 bars
                                price = bar['close']
                                atr = bar['atr']
                                conf = bar['conf']
                                if pos:
                                    if pos['type'] == "BUY":
                                        if bar['low'] <= pos['sl']:
                                            bal += (pos['sl'] - pos['entry_price']) * 10.0
                                            pos = None
                                        elif bar['high'] >= pos['tp']:
                                            bal += (pos['tp'] - pos['entry_price']) * 10.0
                                            pos = None
                                    else:
                                        if bar['high'] >= pos['sl']:
                                            bal += (pos['entry_price'] - pos['sl']) * 10.0
                                            pos = None
                                        elif bar['low'] <= pos['tp']:
                                            bal += (pos['entry_price'] - pos['tp']) * 10.0
                                            pos = None
                                else:
                                    if conf >= test_thresh:
                                        pos = {"entry_price": price, "sl": price - (test_sl * atr), "tp": price + (test_tp * atr), "type": "BUY"}
                                    elif conf <= (1.0 - test_thresh):
                                        pos = {"entry_price": price, "sl": price + (test_sl * atr), "tp": price - (test_tp * atr), "type": "SELL"}
                            
                            profit = bal - 10000.0
                            if profit > best_profit:
                                best_profit = profit
                                optimal_sl = test_sl
                                optimal_tp = test_tp
                                optimal_threshold = test_thresh
                                
                self.logger.info(f"Auto-Optimization complete: Optimal Threshold={optimal_threshold}, Optimal SL={optimal_sl}, Optimal TP={optimal_tp} (Simulated Profit: +${best_profit:.2f})")
                
                # Apply optimal threshold to Decision Engine immediately
                if hasattr(self, "decision_engine") and self.decision_engine:
                    self.decision_engine.confidence_threshold = optimal_threshold
                    
        except Exception as e:
            self.logger.error(f"Error in dynamic 3D auto-optimization: {e}")

        # Dynamically set HLC-optimized SL/TP multipliers based on volatility regime (from 30-day backtest)
        optimal_spacing = 0.65
        if self.volatility_regime == "HIGH_NEWS":
            self.limit_spacing = 0.5
            self.sl_mult = 0.8  # Extra buffer for high volatility noise
            self.tp_mult = 4.0  # Exploit large range sweeps
            optimal_spacing = 1.0  # Wide spacing for high news/volatility to prevent fast averaging drawdowns
        elif self.volatility_regime == "SIDEWAYS":
            self.limit_spacing = 0.2
            self.sl_mult = 0.6  # Super tight SL to contain range breakout risk
            self.tp_mult = 2.0  # Quick TP to lock in range swings safely
            optimal_spacing = 0.35  # Tight spacing for sideways/ranging markets to capture small swings
        elif self.volatility_regime == "TREND_UP":
            self.limit_spacing = 0.3
            self.sl_mult = 0.6  # Cut losses quickly
            self.tp_mult = 3.5  # Ride the upward momentum for high profits
            optimal_spacing = 0.65
        elif self.volatility_regime == "TREND_DOWN":
            self.limit_spacing = 0.45  # Widen limit spacing for steep panic drops
            self.sl_mult = 0.6  # Tighter SL for sell direction risk containment
            self.tp_mult = 3.5  # High TP for crash segments
            optimal_spacing = 0.8  # Wider spacing for safety
        else: # NORMAL
            self.limit_spacing = 0.3
            self.sl_mult = 0.6  # Standard optimized tight SL
            self.tp_mult = 2.5  # Standard optimized TP
            optimal_spacing = 0.65  # Moderate spacing for trending/normal markets
            
        # Apply Live MAE/MFE Calibration to optimize spacing, SL, and TP dynamically
        try:
            mae_mfe_stats = self._get_recent_mae_mfe()
            avg_mae = mae_mfe_stats.get("average_mae_points", 0)
            avg_mfe = mae_mfe_stats.get("average_mfe_points", 0)
            
            if avg_mae > 0 and avg_mfe > 0:
                self.logger.info(f"Live MAE/MFE Calibration: Avg MAE=${avg_mae:.2f}, Avg MFE=${avg_mfe:.2f}")
                
                # MAE Calibration (Adverse Excursion / Drawdown)
                # If trades suffer deep drawdowns > $4.00, widen the limit spacing to capture better average prices
                if avg_mae > 4.0:
                    optimal_spacing *= 1.5
                    self.sl_mult *= 1.2  # Give more breathing room
                    self.logger.info(f"MAE Calibration: High adverse excursion detected. Widened Spacing to {optimal_spacing:.2f} and SL mult to {self.sl_mult:.2f}")
                # If entries are highly precise with < $1.50 drawdown, tighten SL and spacing
                elif avg_mae < 1.5:
                    optimal_spacing *= 0.8
                    self.sl_mult = max(0.4, self.sl_mult * 0.8)
                    self.logger.info(f"MAE Calibration: High precision entries detected. Tightened Spacing to {optimal_spacing:.2f} and SL mult to {self.sl_mult:.2f}")
                    
                # MFE Calibration (Favorable Excursion / Profit Run)
                # If trades run deep into profit > $6.00, extend TP to ride the trend
                if avg_mfe > 6.0:
                    self.tp_mult *= 1.5
                    self.logger.info(f"MFE Calibration: Strong profit runs detected. Extended TP mult to {self.tp_mult:.2f}")
                # If profits reverse quickly < $2.50, reduce TP for faster, safer realization
                elif avg_mfe < 2.5:
                    self.tp_mult = max(1.0, self.tp_mult * 0.8)
                    self.logger.info(f"MFE Calibration: Shallow profits detected. Reduced TP mult to {self.tp_mult:.2f} for faster realization")
        except Exception as e:
            self.logger.error(f"Error during MAE/MFE Calibration: {e}")

        self.logger.info(f"Regime set to {self.volatility_regime}: Limit={self.limit_spacing}, SL={self.sl_mult}, TP={self.tp_mult}. Bias: {self.macro_bias}")
        
        # Apply the dynamically optimized spacing multiplier to RiskEngine
        if hasattr(self, "decision_engine") and self.decision_engine:
            re = getattr(self.decision_engine, "risk_engine", None)
            if re:
                os.environ["AVERAGING_ATR_MULTIPLIER"] = str(optimal_spacing)
                self.logger.info(f"AI Dynamic Spacing Applied to RiskEngine: Averaging ATR Multiplier={optimal_spacing} for regime {self.volatility_regime}")
        
        # Apply session-specific parameter overrides if AUTO LOT is checked
        self.apply_auto_session_parameters()

    def apply_auto_session_parameters(self):
        import os
        auto_lot = os.getenv("AUTO_LOT_ENABLED", "False").lower() == "true"
        if not auto_lot:
            return
            
        session_name, _ = self._get_current_session_info()
        
        # Load session specific default settings
        if "ASIA" in session_name:
            lot = 0.40
            thresh = 0.65
            max_op = 4
        elif "LONDON" in session_name:
            lot = 0.30
            thresh = 0.68
            max_op = 4
        else: # NEW YORK
            lot = 0.20
            thresh = 0.72
            max_op = 3
            
        # Override with Qwen AI dynamic outputs if available
        qwen_thresh = getattr(self, "optimal_confidence_threshold", None)
        qwen_max_op = getattr(self, "optimal_max_op", None)
        
        if qwen_thresh is not None:
            thresh = float(qwen_thresh)
            
        # Adaptive Threshold Adjustment based on active positions to prevent over-trading
        active_ops = 0
        re = getattr(self.decision_engine, "risk_engine", None) if hasattr(self, "decision_engine") and self.decision_engine else None
        if re:
            try:
                import MetaTrader5 as mt5
                pos = mt5.positions_get(symbol="XAUUSD") or mt5.positions_get(symbol="GOLD")
                active_ops = len(pos) if pos else 0
            except Exception:
                pass
                
        if active_ops > 0:
            # Prevent over-trading: Raise threshold by +0.04 per active position, capped at 0.80
            penalty = min(0.12, active_ops * 0.04)
            thresh = min(0.80, thresh + penalty)
            self.logger.info(f"Adaptive Sizing: {active_ops} active positions found. Raising threshold to {thresh:.2f} to prevent over-trading.")
        else:
            # Capture opportunities: Lower threshold by -0.04 to make it easier to enter trades, floor at 0.60
            thresh = max(0.60, thresh - 0.04)
            self.logger.info(f"Adaptive Sizing: No active positions. Lowering threshold to {thresh:.2f} to ease entry.")
            
        if qwen_max_op is not None:
            max_op = int(qwen_max_op)
            self.logger.info(f"Auto LOT Override: Using Qwen AI dynamically calculated Max OP: {max_op}")
            
        # Update engines in real-time
        if hasattr(self, "decision_engine") and self.decision_engine:
            self.decision_engine.confidence_threshold = thresh
            re = getattr(self.decision_engine, "risk_engine", None)
            if re:
                re.config["lot_size"] = lot
                re.max_positions = max_op
                # Push the updated settings to os.environ so they persist in child threads
                os.environ["BASE_LOT_SIZE"] = str(lot)
                os.environ["AVERAGING_MAX_POSITIONS"] = str(max_op)
                
        self.logger.info(f"Auto LOT Applied: Session={session_name}, Lot={lot}, Threshold={thresh}, Max OP={max_op}")

    def _get_recent_mae_mfe(self) -> dict:
        import MetaTrader5 as mt5
        import pandas as pd
        from datetime import datetime, timedelta
        
        try:
            if not mt5.initialize():
                return {}
                
            # Get history deals for the last 24 hours to prevent timezone discrepancies with broker server
            from_date = datetime.now() - timedelta(hours=24)
            to_date = datetime.now() + timedelta(hours=2)
            
            # Fetch history deals
            history_deals = mt5.history_deals_get(from_date, to_date)
            if history_deals is None or len(history_deals) == 0:
                return {"message": "No recent closed trades found to calculate MAE/MFE."}
                
            # Group by position ID to reconstruct trades
            df_deals = pd.DataFrame([d._asdict() for d in history_deals])
            if df_deals.empty:
                return {}
                
            positions = df_deals.groupby('position_id')
            trades_metrics = []
            
            for pos_id, group in positions:
                # Need at least an entry and exit deal
                if len(group) >= 2:
                    sorted_group = group.sort_values('time')
                    entry_deal = sorted_group.iloc[0]
                    exit_deal = sorted_group.iloc[-1]
                    
                    entry_price = float(entry_deal['price'])
                    close_price = float(exit_deal['price'])
                    entry_time = int(entry_deal['time'])
                    close_time = int(exit_deal['time'])
                    p_type = int(entry_deal['type']) # 0 = BUY, 1 = SELL
                    symbol = entry_deal['symbol']
                    
                    # Fetch M1 rates during this trade's lifetime to get high/low
                    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, entry_time - 60, close_time + 60)
                    if rates is not None and len(rates) > 0:
                        highs = [r[2] for r in rates]
                        lows = [r[3] for r in rates]
                        
                        max_price = max(highs)
                        min_price = min(lows)
                        
                        if p_type == 0: # BUY
                            mfe = max_price - entry_price
                            mae = entry_price - min_price
                        else: # SELL
                            mfe = entry_price - min_price
                            mae = max_price - entry_price
                            
                        # Calculate time-decay weight (4-hour half-life)
                        import time
                        import math
                        age_hours = (time.time() - close_time) / 3600.0
                        weight = math.pow(2.0, -age_hours / 4.0)
                        weight = max(0.1, weight)  # Minimum 10% weight for older trades
                        
                        trades_metrics.append({
                            "ticket": int(pos_id),
                            "type": "BUY" if p_type == 0 else "SELL",
                            "profit": float(group['profit'].sum()),
                            "entry_price": entry_price,
                            "close_price": close_price,
                            "MAE_points": round(mae, 2),
                            "MFE_points": round(mfe, 2),
                            "weight": round(weight, 3)
                        })
            
            if trades_metrics:
                # Calculate time-decay weighted averages of the last 3 trades (optimized to save Qwen token usage)
                recent_metrics = trades_metrics[-3:]
                total_weight = sum(t["weight"] for t in recent_metrics)
                
                if total_weight > 0:
                    weighted_mae = sum(t["MAE_points"] * t["weight"] for t in recent_metrics) / total_weight
                    weighted_mfe = sum(t["MFE_points"] * t["weight"] for t in recent_metrics) / total_weight
                else:
                    weighted_mae = sum(t["MAE_points"] for t in recent_metrics) / len(recent_metrics)
                    weighted_mfe = sum(t["MFE_points"] for t in recent_metrics) / len(recent_metrics)
                
                return {
                    "average_mae_points": round(weighted_mae, 2),
                    "average_mfe_points": round(weighted_mfe, 2),
                    "recent_trades_summary": recent_metrics
                }
        except Exception as e:
            self.logger.error(f"Error calculating MAE/MFE: {e}")
        return {}

    def _get_current_session_info(self) -> tuple:
        """
        Returns (session_name, polling_interval_seconds) based on current UTC hour.
        Slow hours (Asia) are polled less frequently to minimize token/VRAM consumption.
        Active hours (London, New York) are polled every 10 minutes for fast updates.
        """
        import datetime
        utc_hour = datetime.datetime.utcnow().hour
        
        # Asia Session (Quiet: UTC 22:00 to 08:00)
        if utc_hour >= 22 or utc_hour < 8:
            return "ASIA (Tokyo/Sydney)", 1800  # Poll every 30 minutes
        # London Session (Active: UTC 08:00 to 13:00)
        elif utc_hour >= 8 and utc_hour < 13:
            return "LONDON (Europe)", 600       # Poll every 10 minutes
        # New York Session (Highly Active/Volatile: UTC 13:00 to 22:00)
        else:
            return "NEW YORK (USA)", 300        # Poll every 5 minutes (300 seconds) for ultra-fast reaction
