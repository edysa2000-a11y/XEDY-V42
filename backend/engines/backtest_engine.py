from .base_engine import BaseEngine
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import os
import xgboost as xgb
import logging
from datetime import datetime

logger = logging.getLogger("xedy.backtest")

class BacktestEngine(BaseEngine):
    """
    Historical Backtesting Engine for XEDY V41.
    Runs simulations on historical candles from MT5 using the XGBoost model.
    """
    @property
    def engine_name(self) -> str:
        return "BacktestEngine"

    def __init__(self, config=None):
        super().__init__(config)
        self.model = None
        self._load_model_local()

    def _load_model_local(self):
        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
            model_path = os.path.join(project_root, 'models', 'xgboost_base.json')
            if os.path.exists(model_path):
                self.model = xgb.XGBClassifier()
                self.model.load_model(model_path)
                logger.info(f"Backtest Model loaded from {model_path}")
            else:
                logger.warning("Backtest Model file not found.")
        except Exception as e:
            logger.error(f"Error loading model in BacktestEngine: {e}")

    async def run_backtest(self, symbol="XAUUSD", timeframe_str="M15", bars_count=1000):
        """Runs the historical backtest asynchronously."""
        symbol = symbol.upper()
        # Map timeframe string to MT5 constants
        tf_map = {
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        tf = tf_map.get(timeframe_str, mt5.TIMEFRAME_M15)

        logger.info(f"Running backtest for {symbol} ({timeframe_str}) on {bars_count} bars...")
        
        # Pull rates from MT5
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, int(bars_count))
        if rates is None or len(rates) < 50:
            return {
                "status": "ERROR",
                "message": f"Not enough historical rates for {symbol} on timeframe {timeframe_str}."
            }

        df = pd.DataFrame(rates)
        df['time_str'] = pd.to_datetime(df['time'], unit='s').dt.strftime('%Y-%m-%d %H:%M')
        
        # Calculate RSI (14)
        close = df['close']
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi'] = df['rsi'].fillna(50.0)

        # Calculate MACD (12, 26, 9)
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd'] = df['macd'].fillna(0.0)

        # Drop first 30 rows where indicators are stabilizing
        df = df.iloc[30:].reset_index(drop=True)

        # Backtest Simulation parameters
        initial_balance = 10000.0
        balance = initial_balance
        equity = initial_balance
        peak_equity = initial_balance
        max_drawdown = 0.0
        
        position = None  # None, "BUY", "SELL"
        entry_price = 0.0
        
        total_trades = 0
        winning_trades = 0
        total_profit = 0.0
        total_loss = 0.0
        
        equity_curve_x = []
        equity_curve_y = []

        # Convert DF to records for fast iteration
        records = df.to_dict('records')

        for idx, bar in enumerate(records):
            price = bar['close']
            
            # 1. Evaluate open position vs current bar
            if position:
                pips_gain = (price - entry_price) if position == "BUY" else (entry_price - price)
                # For gold / forex, calculate simplified USD profit
                multiplier = 100.0 if "XAU" in symbol else 10000.0
                trade_profit = pips_gain * multiplier * 0.1 # 0.1 Lot size simulation
                
                # Check opposite signal to close/reverse
                rsi_val = bar['rsi']
                macd_val = bar['macd']
                
                # Model inference
                confidence = 0.5
                if self.model:
                    X = np.array([[rsi_val, macd_val]])
                    try:
                        probs = self.model.predict_proba(X)
                        confidence = float(probs[0][1])
                    except:
                        pass
                
                # Close conditions
                should_close = False
                if position == "BUY" and confidence <= 0.30:
                    should_close = True
                elif position == "SELL" and confidence >= 0.70:
                    should_close = True
                
                # Stop Loss (1.5% capital protection) or Take Profit (3% target)
                if trade_profit <= -150.0 or trade_profit >= 300.0:
                    should_close = True

                if should_close:
                    balance += trade_profit
                    equity = balance
                    if trade_profit >= 0:
                        winning_trades += 1
                        total_profit += trade_profit
                    else:
                        total_loss += abs(trade_profit)
                    
                    total_trades += 1
                    position = None
            
            # 2. Trigger new trade entries
            if not position:
                rsi_val = bar['rsi']
                macd_val = bar['macd']
                confidence = 0.5
                if self.model:
                    X = np.array([[rsi_val, macd_val]])
                    try:
                        probs = self.model.predict_proba(X)
                        confidence = float(probs[0][1])
                    except:
                        pass
                
                if confidence >= 0.70:
                    position = "BUY"
                    entry_price = price
                elif confidence <= 0.30:
                    position = "SELL"
                    entry_price = price

            # Track current equity & drawdown
            current_equity = balance
            if position:
                pips_gain = (price - entry_price) if position == "BUY" else (entry_price - price)
                multiplier = 100.0 if "XAU" in symbol else 10000.0
                current_equity += pips_gain * multiplier * 0.1
                
            peak_equity = max(peak_equity, current_equity)
            dd = ((peak_equity - current_equity) / peak_equity) * 100
            max_drawdown = max(max_drawdown, dd)
            
            # Record Equity Curve every 5 bars
            if idx % 5 == 0 or idx == len(records) - 1:
                equity_curve_x.append(bar['time_str'])
                equity_curve_y.append(round(current_equity, 2))

        # Close final position at end of backtest
        if position:
            pips_gain = (df['close'].iloc[-1] - entry_price) if position == "BUY" else (entry_price - df['close'].iloc[-1])
            multiplier = 100.0 if "XAU" in symbol else 10000.0
            trade_profit = pips_gain * multiplier * 0.1
            balance += trade_profit
            if trade_profit >= 0:
                winning_trades += 1
                total_profit += trade_profit
            else:
                total_loss += abs(trade_profit)
            total_trades += 1

        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0
        profit_factor = (total_profit / total_loss) if total_loss > 0 else total_profit
        net_profit = balance - initial_balance

        return {
            "status": "SUCCESS",
            "symbol": symbol,
            "timeframe": timeframe_str,
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "net_profit": round(net_profit, 2),
            "max_drawdown": round(max_drawdown, 2),
            "profit_factor": round(profit_factor, 2),
            "equity_curve_x": equity_curve_x,
            "equity_curve_y": equity_curve_y
        }
