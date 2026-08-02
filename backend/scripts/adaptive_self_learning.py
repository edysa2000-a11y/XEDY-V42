import os
import json
import time
import pandas as pd
import numpy as np

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

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
    
    trades = []
    
    # Initialize MT5 (Windows Local PC)
    if mt5 and mt5.initialize():
        print("MT5 initialized successfully. Fetching history directly...")
        # Fetch trade history for the last 30 days
        from_date = time.time() - 30 * 24 * 60 * 60
        deals = mt5.history_deals_get(from_date, time.time())
        if deals:
            for d in deals:
                if d.entry == 1:  # Out deals (trade closed)
                    trades.append({
                        "time": int(d.time),
                        "profit": float(d.profit),
                        "symbol": str(d.symbol),
                        "volume": float(d.volume)
                    })
        mt5.shutdown()
    else:
        # Fallback to JSON file (Linux / GitHub Actions cloud)
        print("MT5 not available. Falling back to data/closed_trades.json...")
        trades_path = "data/closed_trades.json"
        if os.path.exists(trades_path):
            try:
                with open(trades_path, "r") as tf:
                    trades = json.load(tf)
            except Exception as e:
                print(f"Failed to read closed_trades.json: {e}")
        else:
            print("No closed_trades.json found. Skipping self-learning.")
            return
            
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
                
        # Build Keyword-Impact Memory
        keyword_memory_path = "data/keyword_impact_memory.json"
        keyword_memory = {}
        if os.path.exists(keyword_memory_path):
            try:
                with open(keyword_memory_path, "r") as kmf:
                    keyword_memory = json.load(kmf)
            except Exception as e:
                print(f"Failed to load keyword memory: {e}")

        # Correlate trades with active economic releases
        for idx, t in df_trades.iterrows():
            past_decisions = df_decisions[df_decisions['timestamp'] <= t['time']]
            if not past_decisions.empty:
                last_dec = past_decisions.iloc[-1]
                releases = last_dec.get('economic_releases', [])
                for rel in releases:
                    # Clean and simplify the release string for matching
                    key_term = rel.split(":")[0].strip() if ":" in rel else rel.strip()
                    if key_term not in keyword_memory:
                        keyword_memory[key_term] = {"net_profit": 0.0, "trade_count": 0, "winrate": 0.0, "wins": 0}
                    
                    keyword_memory[key_term]["net_profit"] += float(t['profit'])
                    keyword_memory[key_term]["trade_count"] += 1
                    if float(t['profit']) > 0:
                        keyword_memory[key_term]["wins"] += 1
                    
                    keyword_memory[key_term]["winrate"] = keyword_memory[key_term]["wins"] / keyword_memory[key_term]["trade_count"]

        # Save updated Keyword-Impact Memory
        try:
            with open(keyword_memory_path, "w") as kmf:
                json.dump(keyword_memory, kmf, indent=2)
            print("Keyword-Impact Memory updated and saved to data/keyword_impact_memory.json")
        except Exception as e:
            print(f"Failed to save keyword memory: {e}")
                
    # Save self-learning feedback
    with open(feedback_path, "w") as f:
        json.dump(feedback_results, f, indent=2)
        
    print("Self-Learning feedback saved successfully to data/self_learning_feedback.json")
    if mt5:
        try:
            mt5.shutdown()
        except:
            pass

if __name__ == "__main__":
    run_self_learning()
