import sys

app_path = r'C:\Antigravity\Project\XEDY Mission Control\frontend\js\app.js'

with open(app_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    new_lines.append(line)
    if "if (data.type === 'v39_data') {" in line:
        new_lines.append("""
                // Auto Update Narrative Dashboard
                if (v39.narrative) {
                    const narasiContentEl = document.getElementById('narasi-content');
                    if (narasiContentEl) {
                        narasiContentEl.innerText = v39.narrative;
                    }
                }
""")
        
with open(app_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Injected JS!")
