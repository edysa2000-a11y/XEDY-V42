import sys

app_path = r'C:\Antigravity\Project\XEDY Mission Control\frontend\js\app.js'
with open(app_path, 'r', encoding='utf-8') as f:
    text = f.read()

old_updater = """                // Smart DOM Updater to prevent flicker
                const updateTxt = (id, txt) => {
                    const el = document.getElementById(id);
                    if (el && el.innerText !== String(txt)) el.innerText = txt;
                };
                const updateCls = (id, cls) => {
                    const el = document.getElementById(id);
                    if (el && el.className !== cls) el.className = cls;
                };"""

new_updater = """                // Smart DOM Updater to prevent flicker (using textContent to avoid layout thrashing)
                const updateTxt = (id, txt) => {
                    const el = document.getElementById(id);
                    if (el && el.textContent !== String(txt)) el.textContent = txt;
                };
                const updateCls = (id, cls) => {
                    const el = document.getElementById(id);
                    if (el && el.className !== cls) el.className = cls;
                };
                
                // Throttle DOM updates to max 5 times per second (200ms) for visual stability
                if (!window.lastTickDomUpdate) window.lastTickDomUpdate = 0;
                const shouldUpdateDom = (now - window.lastTickDomUpdate) > 200;"""

text = text.replace(old_updater, new_updater)

# Now wrap the DOM updates in if(shouldUpdateDom)
old_dom_updates = """                updateTxt('scalp-bid', data.bid.toFixed(2));
                updateTxt('scalp-ask', data.ask.toFixed(2));
                
                const spread = Math.round((data.ask - data.bid) * 100);
                updateTxt('scalp-spread', spread);
                updateTxt('scalp-total-tick', window.scalpTickHistory.length);
                
                updateTxt('scalp-tick-up', tickUp);
                updateTxt('scalp-tick-down', tickDown);
                
                const totalMov = tickUp + tickDown;
                let velPct = 50;
                if (totalMov > 0) velPct = Math.round((tickUp / totalMov) * 100);
                
                const bar = document.getElementById('scalp-velocity-bar');
                if (bar) {
                    const newWidth = velPct + '%';
                    if (bar.style.width !== newWidth) bar.style.width = newWidth;
                }
                
                if (velPct > 60) {
                    updateTxt('scalp-velocity-text', "BULLISH (" + velPct + "%)");
                    updateCls('scalp-velocity-text', "text-success fw-bold");
                    updateCls('scalp-velocity-bar', "progress-bar bg-success");
                } else if (velPct < 40) {
                    updateTxt('scalp-velocity-text', "BEARISH (" + (100 - velPct) + "%)");
                    updateCls('scalp-velocity-text', "text-danger fw-bold");
                    updateCls('scalp-velocity-bar', "progress-bar bg-danger");
                } else {
                    updateTxt('scalp-velocity-text', "NEUTRAL");
                    updateCls('scalp-velocity-text', "text-warning fw-bold");
                    updateCls('scalp-velocity-bar', "progress-bar bg-warning");
                }"""

new_dom_updates = """                const totalMov = tickUp + tickDown;
                let velPct = 50;
                if (totalMov > 0) velPct = Math.round((tickUp / totalMov) * 100);
                
                if (shouldUpdateDom) {
                    window.lastTickDomUpdate = now;
                    updateTxt('scalp-bid', data.bid.toFixed(2));
                    updateTxt('scalp-ask', data.ask.toFixed(2));
                    
                    const spread = Math.round((data.ask - data.bid) * 100);
                    updateTxt('scalp-spread', spread);
                    updateTxt('scalp-total-tick', window.scalpTickHistory.length);
                    
                    updateTxt('scalp-tick-up', tickUp);
                    updateTxt('scalp-tick-down', tickDown);
                    
                    const bar = document.getElementById('scalp-velocity-bar');
                    if (bar) {
                        const newWidth = velPct + '%';
                        if (bar.style.width !== newWidth) bar.style.width = newWidth;
                    }
                    
                    if (velPct > 60) {
                        updateTxt('scalp-velocity-text', "BULLISH (" + velPct + "%)");
                        updateCls('scalp-velocity-text', "text-success fw-bold");
                        updateCls('scalp-velocity-bar', "progress-bar bg-success");
                    } else if (velPct < 40) {
                        updateTxt('scalp-velocity-text', "BEARISH (" + (100 - velPct) + "%)");
                        updateCls('scalp-velocity-text', "text-danger fw-bold");
                        updateCls('scalp-velocity-bar', "progress-bar bg-danger");
                    } else {
                        updateTxt('scalp-velocity-text', "NEUTRAL");
                        updateCls('scalp-velocity-text', "text-warning fw-bold");
                        updateCls('scalp-velocity-bar', "progress-bar bg-warning");
                    }
                }"""
text = text.replace(old_dom_updates, new_dom_updates)

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Added throttle and textContent to app.js!")
