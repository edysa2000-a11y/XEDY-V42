import re

js_path = "frontend/js/app.js"
with open(js_path, "r", encoding="utf-8") as f:
    content = f.read()

scalping_js_code = """
                // --- ⚡ TAB SCALPING ENGINE LOGIC (60s Rolling & Market Structure) ---
                if (!window.scalp60sHistory) window.scalp60sHistory = [];
                if (!window.scalpSpreadHistory) window.scalpSpreadHistory = [];
                
                window.scalp60sHistory.push({ bid: data.bid, ask: data.ask, time: now });
                window.scalp60sHistory = window.scalp60sHistory.filter(t => (now - t.time) <= 60000);

                const currentSpreadPts = Math.round((data.ask - data.bid) * 100);
                window.scalpSpreadHistory.push({ spread: currentSpreadPts, time: now });
                window.scalpSpreadHistory = window.scalpSpreadHistory.filter(s => (now - s.time) <= 300000);

                let minSpreadPts = currentSpreadPts;
                let maxSpreadPts = currentSpreadPts;
                for (let s of window.scalpSpreadHistory) {
                    if (s.spread < minSpreadPts) minSpreadPts = s.spread;
                    if (s.spread > maxSpreadPts) maxSpreadPts = s.spread;
                }

                let buyTicks60s = 0;
                let sellTicks60s = 0;
                for (let i = 1; i < window.scalp60sHistory.length; i++) {
                    const diff = window.scalp60sHistory[i].bid - window.scalp60sHistory[i-1].bid;
                    if (diff > 0) buyTicks60s++;
                    else if (diff < 0) sellTicks60s++;
                }

                const totalTicks60s = window.scalp60sHistory.length;
                const netTickDelta = buyTicks60s - sellTicks60s;
                const totalTickMov = buyTicks60s + sellTicks60s;
                const buyPct60s = totalTickMov > 0 ? Math.round((buyTicks60s / totalTickMov) * 100) : 50;

                let maxBid60s = data.bid;
                let minBid60s = data.bid;
                let maxTime60s = now;
                let minTime60s = now;

                for (let t of window.scalp60sHistory) {
                    if (t.bid > maxBid60s) { maxBid60s = t.bid; maxTime60s = t.time; }
                    if (t.bid < minBid60s) { minBid60s = t.bid; minTime60s = t.time; }
                }

                if (!window.prevStructureHigh || maxBid60s > window.prevStructureHigh.bid) {
                    window.prevStructureHigh = { bid: maxBid60s, time: maxTime60s };
                }
                if (!window.prevStructureLow || minBid60s < window.prevStructureLow.bid) {
                    window.prevStructureLow = { bid: minBid60s, time: minTime60s };
                }

                let hhVal = maxBid60s;
                let llVal = minBid60s;
                let hlVal = window.prevStructureLow ? (minBid60s > window.prevStructureLow.bid ? minBid60s : window.prevStructureLow.bid) : minBid60s;
                let lhVal = window.prevStructureHigh ? (maxBid60s < window.prevStructureHigh.bid ? maxBid60s : window.prevStructureHigh.bid) : maxBid60s;

                if (shouldUpdateDom) {
                    updateTxt('scalp-eng-bid', data.bid.toFixed(2));
                    updateTxt('scalp-eng-ask', data.ask.toFixed(2));
                    updateTxt('scalp-eng-spread-live', currentSpreadPts + " pts");
                    updateTxt('scalp-eng-spread-pips', "(" + (currentSpreadPts / 10).toFixed(1) + " pips)");
                    updateTxt('scalp-eng-spread-range', minSpreadPts + " / " + maxSpreadPts + " pts");
                    updateTxt('scalp-eng-total-ticks-min', totalTicks60s);
                    
                    updateTxt('scalp-eng-buy-min', buyTicks60s);
                    updateTxt('scalp-eng-sell-min', sellTicks60s);
                    
                    const buyBar = document.getElementById('scalp-eng-buy-bar');
                    const sellBar = document.getElementById('scalp-eng-sell-bar');
                    if (buyBar) { buyBar.style.width = buyPct60s + '%'; buyBar.innerText = buyPct60s + '%'; }
                    if (sellBar) { sellBar.style.width = (100 - buyPct60s) + '%'; sellBar.innerText = (100 - buyPct60s) + '%'; }
                    
                    updateTxt('scalp-eng-net-delta', (netTickDelta >= 0 ? "+" : "") + netTickDelta);
                    updateTxt('scalp-eng-buy-pct', buyPct60s + "%");
                    
                    const titleEl = document.getElementById('scalp-eng-trend-title');
                    const subEl = document.getElementById('scalp-eng-trend-sub');
                    const badgeEl = document.getElementById('scalp-eng-trend-badge');
                    
                    if (buyPct60s >= 60) {
                        if (titleEl) { titleEl.innerText = "BULLISH SCALP"; titleEl.style.color = "#00ffcc"; }
                        if (subEl) subEl.innerText = "Strong Buyer Pressure (Momentum: " + buyPct60s + "%)";
                        if (badgeEl) { badgeEl.innerText = "BULLISH"; badgeEl.className = "badge bg-success"; }
                    } else if (buyPct60s <= 40) {
                        if (titleEl) { titleEl.innerText = "BEARISH SCALP"; titleEl.style.color = "#ff3366"; }
                        if (subEl) subEl.innerText = "Strong Seller Pressure (Momentum: " + (100 - buyPct60s) + "%)";
                        if (badgeEl) { badgeEl.innerText = "BEARISH"; badgeEl.className = "badge bg-danger"; }
                    } else {
                        if (titleEl) { titleEl.innerText = "SIDEWAYS RANGE"; titleEl.style.color = "#ffcc00"; }
                        if (subEl) subEl.innerText = "Balanced Order Flow (Momentum: " + buyPct60s + "%)";
                        if (badgeEl) { badgeEl.innerText = "NEUTRAL"; badgeEl.className = "badge bg-warning text-dark"; }
                    }
                    
                    const fmtTime = (t) => new Date(t).toLocaleTimeString();
                    updateTxt('scalp-eng-hh', hhVal.toFixed(2));
                    updateTxt('scalp-eng-hh-time', fmtTime(maxTime60s));
                    updateTxt('scalp-eng-ll', llVal.toFixed(2));
                    updateTxt('scalp-eng-ll-time', fmtTime(minTime60s));
                    updateTxt('scalp-eng-hl', hlVal.toFixed(2));
                    updateTxt('scalp-eng-lh', lhVal.toFixed(2));
                    
                    const descEl = document.getElementById('scalp-eng-struct-desc');
                    const stateEl = document.getElementById('scalp-eng-struct-state');
                    
                    if (data.bid >= maxBid60s && buyPct60s > 55) {
                        if (descEl) { descEl.innerText = "🟢 HIGHER HIGH BROKEN (BULLISH BREAKOUT)"; descEl.style.color = "#00ffcc"; }
                        if (stateEl) { stateEl.innerText = "BULLISH BREAKOUT"; stateEl.className = "badge bg-success"; }
                    } else if (data.bid <= minBid60s && buyPct60s < 45) {
                        if (descEl) { descEl.innerText = "🔴 LOWER LOW BROKEN (BEARISH BREAKOUT)"; descEl.style.color = "#ff3366"; }
                        if (stateEl) { stateEl.innerText = "BEARISH BREAKOUT"; stateEl.className = "badge bg-danger"; }
                    } else {
                        if (descEl) { descEl.innerText = "🟢 HIGHER HIGH & HIGHER LOW (BULLISH STRUCTURE)"; descEl.style.color = "#00ffcc"; }
                        if (stateEl) { stateEl.innerText = "STRUCTURE OK"; stateEl.className = "badge bg-secondary"; }
                    }
                }
"""

marker = "// Manual Scalping Tick Logic (30s Rolling)"
if 'TAB SCALPING ENGINE LOGIC' not in content:
    content = content.replace(marker, scalping_js_code + "\n                " + marker)
    print("Injected Scalping Engine JS logic into app.js.")

with open(js_path, "w", encoding="utf-8") as f:
    f.write(content)

print("app.js updated.")
