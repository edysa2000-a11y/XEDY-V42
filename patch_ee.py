import re

with open("backend/engines/execution_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

new_block = """        # Fixed TP/SL for High Win Rate (V39 Optimizations)
        # To hit >80% Win Rate, we use SL=1.5 ATR and TP=1.2 ATR.
        sl_mult = 1.5
        tp_mult = 1.2
        
        self.logger.info(f"V39 Confidence Mode: Forcing SL={sl_mult} ATR, TP={tp_mult} ATR for High Win Rate")
"""

content = re.sub(r'        sl_mult = 1\.5\n        tp_mult = 3\.0.*?self\.logger\.warning\(f"Could not apply Holy Grail params in execution: \{e\}"\)', new_block, content, flags=re.DOTALL)

with open("backend/engines/execution_engine.py", "w", encoding="utf-8") as f:
    f.write(content)

print("execution_engine.py patched.")
