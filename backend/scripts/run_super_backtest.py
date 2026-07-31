import MetaTrader5 as mt5
import datetime
import xgboost as xgb
import numpy as np
import pandas as pd

def calculate_adx(high, low, close, n=14):
    cs = pd.Series(close)
    hs = pd.Series(high)
    ls = pd.Series(low)
    tr = pd.concat([hs - ls, (hs - cs.shift(1)).abs(), (ls - cs.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/n, adjust=False).mean()
    up_move = hs - hs.shift(1)
    down_move = ls.shift(1) - ls
    pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    pos_di = 100 * pd.Series(pos_dm).ewm(alpha=1/n, adjust=False).mean() / atr
    neg_di = 100 * pd.Series(neg_dm).ewm(alpha=1/n, adjust=False).mean() / atr
    dx = 100 * (pos_di - neg_di).abs() / (pos_di + neg_di)
    adx = dx.ewm(alpha=1/n, adjust=False).mean()
    return adx.fillna(0.0).values

def main():
    print("Connecting to MetaTrader 5...")
    if not mt5.initialize():
        print("MT5 Init failed")
        return
        
    # Load newly trained XGBoost model
    model = xgb.XGBClassifier()
    model.load_model("models/xgboost_base.json")
    print("Loaded xgboost_base.json super-model.")
    
    # Fetch 30 days of data
    symbol = "XAUUSD"
    tf = mt5.TIMEFRAME_M15
    end_dt = datetime.datetime.now(datetime.timezone.utc)
    start_dt = end_dt - datetime.timedelta(days=30)
    
    print(f"Fetching 30 days of M15 XAUUSD data from {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}...")
    rates = mt5.copy_rates_range(symbol, tf, start_dt, end_dt)
    if rates is None or len(rates) == 0:
        print("Failed to pull rates.")
        mt5.shutdown()
        return
        
    print(f"Successfully pulled {len(rates)} bars.")
    
    # Calculate indicators
    highs = np.array([r[2] for r in rates])
    lows = np.array([r[3] for r in rates])
    closes = np.array([r[4] for r in rates])
    
    # Technicals
    delta = pd.Series(closes).diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = (100 - (100 / (1 + rs))).fillna(50.0).values
    
    exp1 = pd.Series(closes).ewm(span=12, adjust=False).mean()
    exp2 = pd.Series(closes).ewm(span=26, adjust=False).mean()
    macd = (exp1 - exp2).values
    
    adx_values = calculate_adx(highs, lows, closes, n=14)
    
    tr_list = []
    for i in range(1, len(rates)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_list.append(tr)
    atr = float(np.mean(tr_list[-14:])) if tr_list else 1.5
    
    # Run backtest simulation
    balance = 10000.0
    equity = 10000.0
    max_dd = 0.0
    peak_equity = 10000.0
    
    positions = [] # {"type": "BUY"/"SELL", "price": float, "volume": float, "highest_profit": float}
    closed_trades = []
    
    # Simulated index / macro correlations (fixed variables matching collector defaults)
    nfp_surprise = 0.0
    cpi_surprise = 0.0
    fed_rate = 5.25
    for idx in range(30, len(rates)):
        price = closes[idx]
        curr_rsi = rsi[idx]
        curr_macd = macd[idx]
        curr_adx = adx_values[idx]
        
        # Calculate dynamic DXY and Yield correlation matching training distribution
        mean_close = float(np.mean(closes))
        dxy_trend = 104.0 - (price - mean_close) * 0.05
        yield_trend = 4.25 - (price - mean_close) * 0.01
        
        # Calculate floating profit & check trailing/BE exits
        floating_profit = 0.0
        active_positions = []
        for p in positions:
            pips = (price - p["price"]) if p["type"] == "BUY" else (p["price"] - price)
            prof = pips * 100.0 * p["volume"]
            floating_profit += prof
            
            if prof > p["highest_profit"]:
                p["highest_profit"] = prof
                
            # Method 10 Hybrid rules:
            should_exit = False
            if p["highest_profit"] >= 60.0 and prof < (p["highest_profit"] * 0.5):
                should_exit = True
            elif p["highest_profit"] >= 30.0 and prof <= 0.0:
                should_exit = True
                
            if should_exit:
                balance += prof
                closed_trades.append(prof)
            else:
                active_positions.append(p)
        positions = active_positions
        
        equity = balance + floating_profit
        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity * 100.0
        if dd > max_dd:
            max_dd = dd
            
        # Check Basket TP
        if len(positions) >= 2:
            total_vol = sum(p["volume"] for p in positions)
            basket_tp = max(5.0, (total_vol / 0.10) * 15.00)
            if floating_profit >= basket_tp:
                balance += floating_profit
                for p in positions:
                    pips = (price - p["price"]) if p["type"] == "BUY" else (p["price"] - price)
                    closed_trades.append(pips * 100.0 * p["volume"])
                positions = []
                floating_profit = 0.0
                continue
                
        # Spacing check
        can_open_buy = True
        can_open_sell = True
        
        required_dist = atr * 1.0
        buy_positions = [p for p in positions if p["type"] == "BUY"]
        sell_positions = [p for p in positions if p["type"] == "SELL"]
        if buy_positions:
            last_buy = max(buy_positions, key=lambda p: p["price"])
            if abs(price - last_buy["price"]) < required_dist:
                can_open_buy = False
        if sell_positions:
            last_sell = min(sell_positions, key=lambda p: p["price"])
            if abs(price - last_sell["price"]) < required_dist:
                can_open_sell = False
                
        if len(positions) >= 4:
            can_open_buy = False
            can_open_sell = False
            
        # Calculate session features
        dt = datetime.datetime.fromtimestamp(rates[idx][0], datetime.timezone.utc)
        hour = dt.hour
        session_asia = 1.0 if (hour >= 0 and hour < 8) else 0.0
        session_europe = 1.0 if (hour >= 8 and hour < 13) else 0.0
        session_america = 1.0 if (hour >= 13 and hour < 21) else 0.0
        session_overlap = 1.0 if (hour >= 13 and hour < 17) else 0.0
        
        # ML Inference with 13 features
        X = np.array([[
            curr_rsi, curr_macd, curr_adx, atr, 
            nfp_surprise, cpi_surprise, fed_rate, 
            dxy_trend, yield_trend,
            session_asia, session_europe, session_america, session_overlap
        ]])
        probs = model.predict_proba(X)
        prob_buy = float(probs[0][1])
        prob_sell = float(probs[0][0])
        
        # Check Drawdown Halt (3.0% Kill Switch)
        if max_dd >= 3.0:
            can_open_buy = False
            can_open_sell = False
            
        # Trigger on High Confidence
        if prob_buy >= 0.80 and can_open_buy:
            positions.append({"type": "BUY", "price": price, "volume": 0.10, "highest_profit": 0.0})
        elif prob_sell >= 0.80 and can_open_sell:
            positions.append({"type": "SELL", "price": price, "volume": 0.10, "highest_profit": 0.0})
            
        # Hard SL protection (Tightened to cap DD at 1.5% per basket failure)
        if floating_profit <= -150.0:
            balance += floating_profit
            for p in positions:
                pips = (price - p["price"]) if p["type"] == "BUY" else (p["price"] - price)
                closed_trades.append(pips * 100.0 * p["volume"])
            positions = []
            floating_profit = 0.0
            
    # Close any remaining
    if positions:
        balance += floating_profit
        for p in positions:
            pips = (closes[-1] - p["price"]) if p["type"] == "BUY" else (p["price"] - closes[-1])
            closed_trades.append(pips * 100.0 * p["volume"])
            
    # Calculate performance metrics
    win_trades = [t for t in closed_trades if t > 0]
    loss_trades = [t for t in closed_trades if t <= 0]
    winrate = (len(win_trades) / len(closed_trades) * 100.0) if closed_trades else 0.0
    
    print("\n==============================================")
    print("     XEDY SUPER-MODEL 30-DAY BACKTEST REPORT")
    print("==============================================")
    print(f"Total Net Profit: ${balance - 10000.0:.2f}")
    print(f"Max Drawdown: {max_dd:.2f}%")
    print(f"Total Executed Positions: {len(closed_trades)}")
    print(f"Winning Positions: {len(win_trades)} | Losing Positions: {len(loss_trades)}")
    print(f"Winrate: {winrate:.1f}%")
    print("==============================================")
    
    mt5.shutdown()

if __name__ == "__main__":
    main()
