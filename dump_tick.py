with open(r'C:\Antigravity\Project\XEDY Mission Control\frontend\js\app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = 0
for i, line in enumerate(lines):
    if "if (data.type === 'tick_data') {" in line:
        start_idx = i
        break

print("".join(lines[start_idx:start_idx+150]))
