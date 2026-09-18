import sys

app_path = r'C:\Antigravity\Project\XEDY Mission Control\frontend\js\app.js'
with open(app_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the placement of const now = Date.now();
text = text.replace(
"""                // Throttle DOM updates to max 5 times per second (200ms) for visual stability
                if (!window.lastTickDomUpdate) window.lastTickDomUpdate = 0;
                const shouldUpdateDom = (now - window.lastTickDomUpdate) > 200;
                
                // Manual Scalping Tick Logic (30s Rolling)
                if (!window.scalpTickHistory) window.scalpTickHistory = [];
                const now = Date.now();""",
"""                // Manual Scalping Tick Logic (30s Rolling)
                if (!window.scalpTickHistory) window.scalpTickHistory = [];
                const now = Date.now();
                
                // Throttle DOM updates to max 5 times per second (200ms) for visual stability
                if (!window.lastTickDomUpdate) window.lastTickDomUpdate = 0;
                const shouldUpdateDom = (now - window.lastTickDomUpdate) > 200;"""
)

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Fixed ReferenceError for 'now'!")
