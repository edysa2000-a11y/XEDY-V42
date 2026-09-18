import sys

app_path = r'C:\Antigravity\Project\XEDY Mission Control\frontend\js\app.js'

with open(app_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if "if (data.type === 'tick_data' || data.type === 'tick') {" in line:
        skip = True
        new_lines.append("""
            if (data.type === 'tick_data' || data.type === 'tick') {
                latestTick = data; 
                
                // Smart DOM Updater to prevent flicker
                const updateTxt = (id, txt) => {
                    const el = document.getElementById(id);
                    if (el && el.innerText !== String(txt)) el.innerText = txt;
                };
                const updateCls = (id, cls) => {
                    const el = document.getElementById(id);
                    if (el && el.className !== cls) el.className = cls;
                };
                
                // Manual Scalping Tick Logic (30s Rolling)
                if (!window.scalpTickHistory) window.scalpTickHistory = [];
                const now = Date.now();
                window.scalpTickHistory.push({ bid: data.bid, ask: data.ask, time: now });
                
                // Filter ticks older than 30s
                window.scalpTickHistory = window.scalpTickHistory.filter(t => (now - t.time) <= 30000);
                
                // Calculate Scalp Metrics
                let tickUp = 0;
                let tickDown = 0;
                for (let i = 1; i < window.scalpTickHistory.length; i++) {
                    const diff = window.scalpTickHistory[i].bid - window.scalpTickHistory[i-1].bid;
                    if (diff > 0) tickUp++;
                    else if (diff < 0) tickDown++;
                }
                
                updateTxt('scalp-bid', data.bid.toFixed(2));
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
                }
                
                // --- ADAPTIVE AI LEARNING INIT ---
                if (!window.scalperLearning) {
                    try {
                        window.scalperLearning = JSON.parse(localStorage.getItem('scalperLearning')) || {
                            history: [],
                            optimalMin: 40,
                            optimalMax: 80,
                            winrate: 0
                        };
                    } catch(e) {
                        window.scalperLearning = { history: [], optimalMin: 40, optimalMax: 80, winrate: 0 };
                    }
                }
                
                if (window.autoScalpEnabled) {
                    updateTxt('scalp-ai-learning-status', 🧠 AI Adaptive Range: [ -  Ticks] (Winrate: %));
                }
                
                // --- AUTO SCALPER LOGIC ---
                if (window.autoScalpEnabled && window.scalpTickHistory.length >= window.scalperLearning.optimalMin && window.scalpTickHistory.length <= window.scalperLearning.optimalMax) {
                    if (!window.lastAutoScalpTime || (now - window.lastAutoScalpTime > 3000)) { // 3s cooldown
                        // Check max 1 position
                        if (window.scalpActivePositions && window.scalpActivePositions.length === 0) {
                            if (velPct >= 85) {
                                window.lastAutoScalpTime = now;
                                window.currentEntryTickVol = window.scalpTickHistory.length;
                                if(typeof window.executeScalping === 'function') window.executeScalping('BUY');
                            } else if (velPct <= 15) {
                                window.lastAutoScalpTime = now;
                                window.currentEntryTickVol = window.scalpTickHistory.length;
                                if(typeof window.executeScalping === 'function') window.executeScalping('SELL');
                            }
                        }
                    }
                }
                
                // --- DYNAMIC EXIT LOGIC ---
                if (window.autoScalpEnabled && window.scalpActivePositions && window.scalpActivePositions.length > 0) {
                    const pos = window.scalpActivePositions[0]; // Hanya 1 posisi
                    const currentProfit = pos.profit || 0;
                    
                    if (currentProfit > 0) {
                        if (pos.type === 'BUY' && velPct < 50) {
                            if(typeof window.closeScalping === 'function') window.closeScalping(pos.ticket);
                        } else if (pos.type === 'SELL' && velPct > 50) {
                            if(typeof window.closeScalping === 'function') window.closeScalping(pos.ticket);
                        } else if (currentProfit >= 2.0) { // Small TP target .00 / 20 pips
                            if(typeof window.closeScalping === 'function') window.closeScalping(pos.ticket);
                        }
                    } else if (currentProfit <= -2.0) { // 20 pips hard SL
                        if(typeof window.closeScalping === 'function') window.closeScalping(pos.ticket);
                    } else {
                        // Momentum cut-loss
                        if (pos.type === 'BUY' && velPct < 20) {
                            if(typeof window.closeScalping === 'function') window.closeScalping(pos.ticket);
                        } else if (pos.type === 'SELL' && velPct > 80) {
                            if(typeof window.closeScalping === 'function') window.closeScalping(pos.ticket);
                        }
                    }
                }
            }
""")
        continue
        
    if skip and "if (data.type === 'settings_updated') {" in line:
        skip = False
        
    if not skip:
        new_lines.append(line)

with open(app_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Injected smart DOM updater!")
