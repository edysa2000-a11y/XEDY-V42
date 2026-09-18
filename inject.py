import sys

index_path = r'C:\Antigravity\Project\XEDY Mission Control\frontend\index.html'

with open('narasi_block.txt', 'r', encoding='utf-8') as f:
    narasi = f.read()
with open('tick_block.txt', 'r', encoding='utf-8') as f:
    tick = f.read()

with open(index_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for idx, line in enumerate(lines):
    if '<div id="tab-forecast"' in line:
        new_lines.append(tick + "\n")
        new_lines.append(narasi + "\n")
    new_lines.append(line)

with open(index_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Injected successfully!")
