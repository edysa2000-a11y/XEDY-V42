import os
import re

base_dir = "backend/engines/v39_causal"

# Rename files
renames = {
    "1_event_engine.py": "event_engine.py",
    "2_macro_yield_engine.py": "macro_yield_engine.py",
    "3_money_flow_engine.py": "money_flow_engine.py",
    "4_divergence_engine.py": "divergence_engine.py",
    "5_consensus_gate.py": "consensus_gate.py"
}

for old, new in renames.items():
    old_path = os.path.join(base_dir, old)
    new_path = os.path.join(base_dir, new)
    if os.path.exists(old_path):
        os.rename(old_path, new_path)

# Update main.py
main_path = "backend/main.py"
with open(main_path, "r", encoding="utf-8") as f:
    main_content = f.read()
    
main_content = main_content.replace("v39_causal.1_event_engine", "v39_causal.event_engine")
main_content = main_content.replace("v39_causal.2_macro_yield_engine", "v39_causal.macro_yield_engine")
main_content = main_content.replace("v39_causal.3_money_flow_engine", "v39_causal.money_flow_engine")
main_content = main_content.replace("v39_causal.4_divergence_engine", "v39_causal.divergence_engine")
main_content = main_content.replace("v39_causal.5_consensus_gate", "v39_causal.consensus_gate")

with open(main_path, "w", encoding="utf-8") as f:
    f.write(main_content)
    
print("Fixed invalid decimal literal in module names.")
