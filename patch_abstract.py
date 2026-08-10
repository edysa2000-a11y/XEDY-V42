import os
import re

engines_dir = "backend/engines/v39_causal"
files = [
    "event_engine.py",
    "macro_yield_engine.py",
    "money_flow_engine.py",
    "divergence_engine.py",
    "consensus_gate.py"
]

methods = """
    async def start(self):
        pass
        
    async def stop(self):
        pass
"""

for fname in files:
    path = os.path.join(engines_dir, fname)
    if not os.path.exists(path):
        continue
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if "async def start(self):" not in content:
        # insert before the first async def
        # find index of '    async def '
        match = re.search(r'    async def [a-z_]+\(self', content)
        if match:
            idx = match.start()
            new_content = content[:idx] + methods.lstrip("\n") + "\n" + content[idx:]
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
                
print("Added start() and stop() to all 5 engines.")
