import asyncio
import logging
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

logger = logging.getLogger("xedy.data")

class DataEngine:
    """
    Advanced Data Engine for fetching Account Status, Risk Metrics,
    and calculating Technical Indicators using standard Pandas.
    """
    def __init__(self, symbols=None):
        self.symbols = symbols if symbols else ["XAUUSD"]
        self._running = False
        
        # State Data
        self.account_info = {}
        self.positions = []
        self.history = []
        self.today_profit = 0.0
        self.technicals = {s: {} for s in self.symbols}
        self.smart_money = {s: {} for s in self.symbols}

    async def start(self):
        logger.info("Memulai Data Engine (Account & Technicals)...")
        self._running = True
        asyncio.create_task(self._data_loop())

    async def stop(self):
        self._running = False
        logger.info("Data Engine dihentikan.")

    async def _data_loop(self):
        while self._running:
            try:
                await self._update_account_data()
                await self._update_technical_data()
                await self._update_smart_money_data()
            except Exception as e:
                logger.error(f"Error di Data Engine: {e}")
                
            await asyncio.sleep(5)  # Update every 5 seconds

    async def _update_account_data(self):
        # Fetch Account Info
        account = mt5.account_info()
        if account:
            acc_dict = account._asdict()
            # Calculate Risk / Drawdown safely
            balance = acc_dict.get('balance', 0)
            equity = acc_dict.get('equity', 0)
            margin = acc_dict.get('margin', 0)
            
            drawdown = 0.0
            if balance > 0 and equity < balance:
                drawdown = ((balance - equity) / balance) * 100
                
            margin_usage = 0.0
            if equity > 0:
                margin_usage = (margin / equity) * 100
                
            self.account_info = {
                "balance": balance,
                "equity": equity,
                "margin": margin,
                "drawdown": round(drawdown, 2),
                "margin_usage": round(margin_usage, 2),
                "profit": acc_dict.get('profit', 0)
            }
            
        # Fetch Positions (All symbols for MT5-like view)
        positions = mt5.positions_get()
        self.positions = []
        if positions:
            for p in positions:
                p_dict = p._asdict()
                from datetime import datetime
                time_str = datetime.fromtimestamp(p_dict.get('time', 0)).strftime('%Y.%m.%d %H:%M:%S')
                # Type: 0 = BUY, 1 = SELL
                self.positions.append({
                    "symbol": p_dict.get('symbol', ''),
                    "ticket": p_dict.get('ticket'),
                    "time": time_str,
                    "type": "buy" if p_dict.get('type') == 0 else "sell",
                    "volume": p_dict.get('volume'),
                    "price_open": p_dict.get('price_open'),
                    "sl": p_dict.get('sl'),
                    "tp": p_dict.get('tp'),
                    "price_current": p_dict.get('price_current', 0.0),
                    "profit": p_dict.get('profit', 0.0),
                    "is_position": True
                })

        # Fetch Pending Orders (All symbols)
        orders = mt5.orders_get()
        if orders:
            for o in orders:
                o_dict = o._asdict()
                from datetime import datetime
                time_str = datetime.fromtimestamp(o_dict.get('time_setup', 0)).strftime('%Y.%m.%d %H:%M:%S')
                # Type mapping: 2=BUY LIMIT, 3=SELL LIMIT, 4=BUY STOP, 5=SELL STOP
                types = {2: "buy limit", 3: "sell limit", 4: "buy stop", 5: "sell stop", 0: "buy", 1: "sell"}
                self.positions.append({
                    "symbol": o_dict.get('symbol', ''),
                    "ticket": o_dict.get('ticket'),
                    "time": time_str,
                    "type": types.get(o_dict.get('type'), "pending"),
                    "volume": o_dict.get('volume_initial'),
                    "price_open": o_dict.get('price_open'),
                    "sl": o_dict.get('sl'),
                    "tp": o_dict.get('tp'),
                    "price_current": o_dict.get('price_current', 0.0),
                    "profit": 0.0,
                    "is_position": False
                })

        # Fetch recent 24h trade history deals (using timezone-safe range)
        from datetime import datetime, timedelta
        from_date = datetime.now() - timedelta(days=2)
        to_date = datetime.now() + timedelta(days=1)
        deals = mt5.history_deals_get(from_date, to_date)
        
        self.history = []
        if deals:
            pos_map = {}
            for d in deals:
                d_dict = d._asdict()
                pos_id = d_dict.get('position_id')
                if not pos_id:
                    continue
                deal_symbol = d_dict.get('symbol', '')
                symbols_upper = [s.upper() for s in self.symbols] + [s.upper() + "." for s in self.symbols]
                if deal_symbol and deal_symbol.upper() not in symbols_upper:
                    continue
                if pos_id not in pos_map:
                    pos_map[pos_id] = {
                        "ticket": pos_id,
                        "type": "BUY" if d_dict.get('type') == 0 else "SELL",
                        "volume": d_dict.get('volume', 0.0),
                        "open_time": "--",
                        "close_time": "--",
                        "profit": 0.0,
                        "closed": False
                    }
                
                # Entry IN
                if d_dict.get('entry') == 0:
                    dt_open = datetime.fromtimestamp(d_dict.get('time'))
                    pos_map[pos_id]["open_time"] = dt_open.strftime('%H:%M:%S')
                    pos_map[pos_id]["type"] = "BUY" if d_dict.get('type') == 0 else "SELL"
                    pos_map[pos_id]["volume"] = d_dict.get('volume', pos_map[pos_id].get("volume", 0.0))
                    
                # Entry OUT
                elif d_dict.get('entry') == 1:
                    dt_close = datetime.fromtimestamp(d_dict.get('time'))
                    pos_map[pos_id]["close_time"] = dt_close.strftime('%H:%M:%S')
                    pos_map[pos_id]["profit"] += d_dict.get('profit', 0)
                    pos_map[pos_id]["closed"] = True
                    
            closed_positions = [v for v in pos_map.values() if v["closed"]]
            closed_positions = sorted(closed_positions, key=lambda x: x["ticket"], reverse=True)
            
            for cp in closed_positions:
                self.history.append({
                    "ticket": cp["ticket"],
                    "type": cp["type"],
                    "volume": cp.get("volume", 0.0),
                    "open_time": cp["open_time"],
                    "close_time": cp["close_time"],
                    "profit": round(cp["profit"], 2)
                })
                
            # Calculate today's profit (from 00:00:00 local time today)
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_profit = 0.0
            for d in deals:
                d_dict = d._asdict()
                if d_dict.get('entry') == 1:
                    dt_close = datetime.fromtimestamp(d_dict.get('time'))
                    if dt_close >= today_start:
                        today_profit += d_dict.get('profit', 0.0) + d_dict.get('commission', 0.0) + d_dict.get('swap', 0.0)
            self.today_profit = round(today_profit, 2)

    async def _update_technical_data(self):
        for symbol in self.symbols:
            # Fetch M15 historical rates (last 250 candles to allow MA 200 calculation)
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 250)
            if rates is None or len(rates) < 200:
                continue
                
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            close = df['close']
            
            # Calculate Moving Averages
            ma20_sma = close.rolling(window=20).mean().iloc[-1]
            ma20_ema = close.ewm(span=20, adjust=False).mean().iloc[-1]
            
            ma50_sma = close.rolling(window=50).mean().iloc[-1]
            ma50_ema = close.ewm(span=50, adjust=False).mean().iloc[-1]
            
            ma200_sma = close.rolling(window=200).mean().iloc[-1]
            ma200_ema = close.ewm(span=200, adjust=False).mean().iloc[-1]
            
            # Calculate Stochastic Oscillator (14, 3)
            low_14 = df['low'].rolling(window=14).min()
            high_14 = df['high'].rolling(window=14).max()
            stoch_k = 100 * ((close - low_14) / (high_14 - low_14))
            current_stoch = stoch_k.iloc[-1]
            if np.isnan(current_stoch):
                current_stoch = 50.0
                
            # Calculate RSI (14)
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # Calculate MACD (12, 26, 9)
            exp1 = close.ewm(span=12, adjust=False).mean()
            exp2 = close.ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            hist = macd - signal
            current_macd = macd.iloc[-1]
            current_macdsignal = signal.iloc[-1]
            
            # Calculate ATR (14)
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - close.shift())
            low_close = np.abs(df['low'] - close.shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = np.max(ranges, axis=1)
            atr = true_range.rolling(14).mean()
            current_atr = atr.iloc[-1]
            
            current_close = float(close.iloc[-1])
            
            self.technicals[symbol] = {
                "rsi": round(current_rsi, 1) if not np.isnan(current_rsi) else 50.0,
                "macd": round(current_macd, 2) if not np.isnan(current_macd) else 0.0,
                "macd_signal": round(current_macdsignal, 2) if not np.isnan(current_macdsignal) else 0.0,
                "atr": round(current_atr, 2) if not np.isnan(current_atr) else 0.0,
                "stoch": round(current_stoch, 1),
                "trend": "BULLISH" if current_macd > current_macdsignal else "BEARISH",
                "ma20_simple": round(ma20_sma, 2),
                "ma20_exponential": round(ma20_ema, 2),
                "ma20_signal": "BUY" if current_close > ma20_sma else "SELL",
                "ma50_simple": round(ma50_sma, 2),
                "ma50_exponential": round(ma50_ema, 2),
                "ma50_signal": "BUY" if current_close > ma50_sma else "SELL",
                "ma200_simple": round(ma200_sma, 2),
                "ma200_exponential": round(ma200_ema, 2),
                "ma200_signal": "BUY" if current_close > ma200_sma else "SELL",
            }

    async def _update_smart_money_data(self):
        for symbol in self.symbols:
            # Fetch historical rates for M15 & H1 to calculate real SMC levels
            rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 50)
            rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 50)
            
            if rates_m15 is None or len(rates_m15) < 10 or rates_h1 is None or len(rates_h1) < 10:
                continue
                
            df_m15 = pd.DataFrame(rates_m15)
            df_h1 = pd.DataFrame(rates_h1)
            
            # 1. Calculate BSL (Buy-Side Liquidity) & SSL (Sell-Side Liquidity) based on H1 Swing High/Low
            h1_highs = df_h1['high']
            h1_lows = df_h1['low']
            
            bsl = float(h1_highs.max())
            ssl = float(h1_lows.min())
            
            # Inducement Level is pullbacks on M15
            inducement = float(df_m15['high'].iloc[-10:].max() * 0.4 + df_m15['low'].iloc[-10:].min() * 0.6)
            
            # 2. Identify Order Blocks (OB) & Fair Value Gaps (FVG)
            ob_fvg_list = []
            
            # Check for FVGs on M15
            for i in range(2, len(df_m15)):
                # Bullish FVG
                if df_m15['high'].iloc[i-2] < df_m15['low'].iloc[i]:
                    level = (df_m15['high'].iloc[i-2] + df_m15['low'].iloc[i]) / 2.0
                    ob_fvg_list.append({
                        "level": round(level, 2),
                        "type": "Bullish FVG",
                        "timeframe": "M15",
                        "status": "Untested" if df_m15['close'].iloc[-1] > level else "Mitigated"
                    })
                # Bearish FVG
                elif df_m15['low'].iloc[i-2] > df_m15['high'].iloc[i]:
                    level = (df_m15['low'].iloc[i-2] + df_m15['high'].iloc[i]) / 2.0
                    ob_fvg_list.append({
                        "level": round(level, 2),
                        "type": "Bearish FVG",
                        "timeframe": "M15",
                        "status": "Untested" if df_m15['close'].iloc[-1] < level else "Mitigated"
                    })

            # Check for Order Blocks (OB)
            for i in range(1, len(df_h1) - 1):
                body_size = abs(df_h1['close'].iloc[i] - df_h1['open'].iloc[i])
                next_body_size = df_h1['close'].iloc[i+1] - df_h1['open'].iloc[i+1]
                
                # Strong upward move after down candle
                if df_h1['close'].iloc[i] < df_h1['open'].iloc[i] and next_body_size > body_size * 1.5:
                    level = df_h1['low'].iloc[i]
                    ob_fvg_list.append({
                        "level": round(level, 2),
                        "type": "Bullish OB",
                        "timeframe": "H1",
                        "status": "Untested"
                    })
                # Strong downward move after up candle
                elif df_h1['close'].iloc[i] > df_h1['open'].iloc[i] and next_body_size < -body_size * 1.5:
                    level = df_h1['high'].iloc[i]
                    ob_fvg_list.append({
                        "level": round(level, 2),
                        "type": "Bearish OB",
                        "timeframe": "H1",
                        "status": "Untested"
                    })
                    
            # Sort by distance to current price and limit to 4
            current_close = float(df_m15['close'].iloc[-1])
            ob_fvg_list.sort(key=lambda x: abs(x["level"] - current_close))
            ob_fvg_list = ob_fvg_list[:4]
            
            # Fallbacks if not enough detected
            while len(ob_fvg_list) < 4:
                ob_fvg_list.append({
                    "level": round(current_close * (1.0 + (len(ob_fvg_list) - 2) * 0.002), 2),
                    "type": "Bullish OB" if len(ob_fvg_list) % 2 == 0 else "Bearish OB",
                    "timeframe": "H1",
                    "status": "Untested"
                })
                
            # 3. Market Structure (BOS / CHoCH) estimation
            prev_close = df_h1['close'].iloc[-10]
            structure_h1 = "BOS (Bullish)" if current_close > prev_close else "CHOCH (Bearish)"
            structure_m15 = "CHOCH (Bullish)" if df_m15['close'].iloc[-1] > df_m15['close'].iloc[-10] else "CHOCH (Bearish)"
            
            # Fetch live spread (Pips = Points / 10 for standard gold pricing)
            spread = 1.5
            tick = mt5.symbol_info_tick(symbol)
            info = mt5.symbol_info(symbol)
            if tick and info:
                spread = round((tick.ask - tick.bid) / (info.point * 10), 1)
                if spread < 0:
                    spread = 1.5
                    
            self.smart_money[symbol] = {
                "ob_fvg": ob_fvg_list,
                "structure_h1": structure_h1,
                "structure_m15": structure_m15,
                "bsl": round(bsl, 2),
                "ssl": round(ssl, 2),
                "inducement": round(inducement, 2),
                "spread": spread
            }

    def get_dashboard_data(self):
        return {
            "account": self.account_info,
            "positions": self.positions,
            "history": self.history,
            "today_profit": self.today_profit,
            "technicals": self.technicals,
            "smart_money": self.smart_money
        }
