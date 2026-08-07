import asyncio
import time
import random
import os
import sys

# Ensure backend module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.engines.ml_engine import MLEngine

async def run_stress_test():
    print("=========================================")
    print("XEDY XGBOOST AI - SEVERE STRESS TEST")
    print("=========================================")
    
    engine = MLEngine()
    await engine.start()
    
    num_requests = 10000
    print(f"\nGenerating {num_requests} extreme market ticks...")
    
    # Generate random extreme data
    requests = []
    for _ in range(num_requests):
        req = {
            "rsi": random.uniform(5.0, 95.0),
            "macd": random.uniform(-2.0, 2.0),
            "adx": random.uniform(10.0, 60.0),
            "atr": random.uniform(5.0, 30.0),
            "nfp_surprise": random.choice([-1.5, 0.0, 2.5]),
            "cpi_surprise": random.choice([-0.5, 0.0, 0.8]),
            "fed_rate": 5.25,
            "dxy_trend": random.uniform(-1.0, 1.0),
            "yield_trend": random.uniform(-1.0, 1.0),
            "price": random.uniform(2300, 2500)
        }
        requests.append(req)
        
    print("Firing payload into MLEngine (Thread Pool)...")
    
    start_time = time.time()
    
    # We will bypass the decision engine callback by mocking it 
    # so we strictly measure XGBoost inference overhead
    class MockDecisionEngine:
        def __init__(self):
            self.predictions = []
        async def evaluate_market_state(self, confidence, rsi, macd, price, atr):
            self.predictions.append(confidence)
            
    mock_de = MockDecisionEngine()
    engine.decision_engine = mock_de
    
    # Fire all concurrently
    tasks = [
        engine.process_features(**req) for req in requests
    ]
    
    await asyncio.gather(*tasks)
    
    end_time = time.time()
    duration = end_time - start_time
    throughput = num_requests / duration
    
    print("\n=== STRESS TEST RESULTS ===")
    print(f"Total Requests Processed : {len(mock_de.predictions)}")
    print(f"Total Time Taken       : {duration:.3f} seconds")
    print(f"Throughput             : {throughput:.0f} predictions / second")
    print(f"Avg Latency per tick   : {(duration/num_requests)*1000:.3f} ms")
    
    # Calculate distribution
    buys = sum(1 for p in mock_de.predictions if p > 0.65)
    sells = sum(1 for p in mock_de.predictions if p < 0.35)
    neutrals = num_requests - buys - sells
    
    print("\n=== SIGNAL DISTRIBUTION ===")
    print(f"BUY Signals (>65%)     : {buys} ({(buys/num_requests)*100:.1f}%)")
    print(f"SELL Signals (<35%)    : {sells} ({(sells/num_requests)*100:.1f}%)")
    print(f"NEUTRAL Signals        : {neutrals} ({(neutrals/num_requests)*100:.1f}%)")
    print("=========================================\n")
    
    await engine.stop()

if __name__ == "__main__":
    asyncio.run(run_stress_test())
