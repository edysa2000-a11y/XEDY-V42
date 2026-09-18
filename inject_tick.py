import sys

app_path = r'C:\Antigravity\Project\XEDY Mission Control\frontend\js\app.js'

with open(app_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if "if (data.type === 'tick' && (data.symbol === 'XAUUSD' || !data.symbol)) {" in line:
        skip = True
        new_lines.append("""
            if (data.type === 'tick_data' || data.type === 'tick') {
                latestTick = data; 
                
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
                
                const scalpBidEl = document.getElementById('scalp-bid');
                if (scalpBidEl) {
                    scalpBidEl.innerText = data.bid.toFixed(2);
                    document.getElementById('scalp-ask').innerText = data.ask.toFixed(2);
                    const spread = Math.round((data.ask - data.bid) * 100);
                    document.getElementById('scalp-spread').innerText = spread;
                    document.getElementById('scalp-total-tick').innerText = window.scalpTickHistory.length;
                    
                    document.getElementById('scalp-tick-up').innerText = tickUp;
                    document.getElementById('scalp-tick-down').innerText = tickDown;
                    
                    const totalMov = tickUp + tickDown;
                    let velPct = 50;
                    if (totalMov > 0) velPct = Math.round((tickUp / totalMov) * 100);
                    
                    const bar = document.getElementById('scalp-velocity-bar');
                    bar.style.width = velPct + '%';
                    
                    const vText = document.getElementById('scalp-velocity-text');
                    if (velPct > 60) {
                        vText.innerText = "BULLISH (" + velPct + "%)";
                        vText.className = "text-success fw-bold";
                        bar.className = "progress-bar bg-success";
                    } else if (velPct < 40) {
                        vText.innerText = "BEARISH (" + (100 - velPct) + "%)";
                        vText.className = "text-danger fw-bold";
                        bar.className = "progress-bar bg-danger";
                    } else {
                        vText.innerText = "NEUTRAL";
                        vText.className = "text-warning fw-bold";
                        bar.className = "progress-bar bg-warning";
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
                    
                    const elAiStatus = document.getElementById('scalp-ai-learning-status');
                    if (elAiStatus) {
                        elAiStatus.innerText = 🧠 AI Adaptive Range: [ -  Ticks] (Winrate: %);
                    }
                    
                    // --- AUTO SCALPER LOGIC ---
                    if (window.autoScalpEnabled && window.scalpTickHistory.length >= window.scalperLearning.optimalMin && window.scalpTickHistory.length <= window.scalperLearning.optimalMax) {
                        const now = Date.now();
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
            }
""")
        continue
        
    if skip and "if (data.type === 'settings_updated') {" in line:
        skip = False
        
    if not skip:
        new_lines.append(line)

new_lines.append("""
window.autoScalpEnabled = false;
window.toggleAutoScalp = function(el) {
    window.autoScalpEnabled = el.checked;
    const badge = document.getElementById('scalp-ai-learning-status');
    if (el.checked) {
        badge.innerHTML = "🧠 AI Adaptive Range Active";
        badge.classList.remove('text-muted');
        badge.classList.add('text-success');
    } else {
        if (window.scalperLearning) {
            badge.innerHTML = 🧠 AI Adaptive Range: [ -  Ticks] (Winrate: %);
        } else {
            badge.innerHTML = "Auto Scalping Disabled";
        }
        badge.classList.remove('text-success');
        badge.classList.add('text-muted');
    }
}
""")

with open(app_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Injected tick logic and toggleAutoScalp!")
