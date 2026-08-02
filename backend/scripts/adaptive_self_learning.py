import os
import json
import time
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def run_self_learning():
    print("Starting Adaptive Self-Learning feedback loop...")
    
    # Paths
    log_path = "data/qwen_decisions_log.jsonl"
    feedback_path = "data/self_learning_feedback.json"
    
    if not os.path.exists(log_path):
        print("No Qwen decisions log found. Skipping self-learning until log accumulates entries.")
        return
        
    # Read Qwen decisions log
    decisions = []
    with open(log_path, "r") as f:
        for line in f:
            if line.strip():
                decisions.append(json.loads(line.strip()))
                
    print(f"Loaded {len(decisions)} historical Qwen decisions.")
    
    # Initialize MT5
    if not mt5.initialize():
        print("MT5 Init failed. Cannot fetch trade history for feedback.")
        return
        
    # Fetch trade history for the last 30 days
    from_date = time.time() - 30 * 24 * 60 * 60
    deals = mt5.history_deals_get(from_date, time.time())
    
    trades = []
    if deals:
        for d in deals:
            if d.entry == 1:  # Out deals (trade closed)
                trades.append({
                    "time": d.time,
                    "profit": d.profit,
                    "symbol": d.symbol,
                    "volume": d.volume
                })
    
    print(f"Loaded {len(trades)} recent closed trades.")
    
    feedback_results = {
        "analyzed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_decisions": len(decisions),
        "total_trades": len(trades),
        "best_performing_regimes": {},
        "kelly_multiplier_feedback": 0.25, # defaults
        "recommended_adjustment": "Maintain current fractional Kelly sizing of 0.25."
    }
    
    if trades and decisions:
        df_decisions = pd.DataFrame(decisions)
        df_decisions['timestamp'] = pd.to_datetime(df_decisions['timestamp'])
        
        df_trades = pd.DataFrame(trades)
        df_trades['time'] = pd.to_datetime(df_trades['time'], unit='s')
        
        # Correlate trades with active decisions at trade close time
        correlated = []
        for idx, t in df_trades.iterrows():
            # Find the most recent decision before trade time
            past_decisions = df_decisions[df_decisions['timestamp'] <= t['time']]
            if not past_decisions.empty:
                last_dec = past_decisions.iloc[-1]
                correlated.append({
                    "profit": t['profit'],
                    "bias": last_dec['bias'],
                    "regime": last_dec['regime'],
                    "method": last_dec['optimal_method']
                })
                
        if correlated:
            df_corr = pd.DataFrame(correlated)
            # Group by regime
            regime_stats = df_corr.groupby('regime')['profit'].agg(['sum', 'count', lambda x: sum(1 for p in x if p > 0) / len(x) if len(x) > 0 else 0.0])
            regime_stats.columns = ['net_profit', 'trade_count', 'winrate']
            
            feedback_results["regime_performance"] = regime_stats.to_dict(orient='index')
            
            # Calculate global winrate to adjust Kelly multiplier
            global_winrate = sum(1 for t in trades if t['profit'] > 0) / len(trades)
            if global_winrate > 0.60:
                feedback_results["kelly_multiplier_feedback"] = 0.30
                feedback_results["recommended_adjustment"] = "High performance winrate (>60%). Adjusting fractional Kelly multiplier to 0.30 for aggressive capitalization."
            elif global_winrate < 0.40:
                feedback_results["kelly_multiplier_feedback"] = 0.15
                feedback_results["recommended_adjustment"] = "Low performance winrate (<40%). Adjusting fractional Kelly multiplier to 0.15 to preserve capital."
                
    # Save self-learning feedback
    with open(feedback_path, "w") as f:
        json.dump(feedback_results, f, indent=2)
        
    print("Self-Learning feedback saved successfully to data/self_learning_feedback.json")
    mt5.shutdown()

if __name__ == "__main__":
    run_self_learning()
