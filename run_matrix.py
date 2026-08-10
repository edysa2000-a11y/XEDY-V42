import json
from backend.scripts.matrix_backtest import run_matrix_simulation

# The 4 pairs
pairs = ["XAUUSD", "AUDUSD", "USDCAD", "NZDUSD"]

print("Starting matrix backtest for 1 month...")
results = run_matrix_simulation(months=1, capital=10000, pairs=pairs)

with open('matrix_backtest_output.json', 'w') as f:
    json.dump(results, f, indent=4)

print("Done. Saved to matrix_backtest_output.json")
