with open(r'C:\Antigravity\Project\XEDY Mission Control\frontend\js\app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(560, 580):
    print(f"{i+1}: {lines[i].strip()}")
