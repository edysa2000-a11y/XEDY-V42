import sys

app_path = r'C:\Antigravity\Project\XEDY Mission Control\frontend\js\app.js'
with open(app_path, 'r', encoding='utf-8') as f:
    text = f.read()

manual_logic = """
// --- MANUAL SCALPING LOGIC ---
window.scalpActivePositions = [];
window.scalpHistoryPositions = [];
window.scalpTicketCounter = 1000;

window.executeScalping = function(type) {
    const lotInput = document.getElementById('scalp-lot');
    let lot = 0.01;
    if (lotInput) lot = parseFloat(lotInput.value);
    
    const bidEl = document.getElementById('scalp-bid');
    const askEl = document.getElementById('scalp-ask');
    let currentPrice = 0;
    if (type === 'BUY' && askEl) currentPrice = parseFloat(askEl.innerText);
    else if (type === 'SELL' && bidEl) currentPrice = parseFloat(bidEl.innerText);
    
    if (currentPrice === 0) return; // No price yet
    
    const ticket = window.scalpTicketCounter++;
    window.scalpActivePositions.push({
        ticket: ticket,
        type: type,
        lot: lot,
        open: currentPrice,
        current: currentPrice,
        profit: 0 - (Math.round((parseFloat(askEl.innerText) - parseFloat(bidEl.innerText)) * 100) * 0.1) // Initial spread cost approx
    });
    
    window.updateScalpTables();
};

window.closeScalping = function(ticket) {
    const idx = window.scalpActivePositions.findIndex(p => p.ticket === ticket);
    if (idx !== -1) {
        const pos = window.scalpActivePositions[idx];
        window.scalpActivePositions.splice(idx, 1);
        
        // Add to history
        window.scalpHistoryPositions.unshift({
            time: new Date().toLocaleTimeString(),
            ticket: pos.ticket,
            type: pos.type,
            lot: pos.lot,
            closePrice: pos.current,
            profit: pos.profit
        });
        
        // Keep history at 50 max
        if (window.scalpHistoryPositions.length > 50) window.scalpHistoryPositions.pop();
        
        window.updateScalpTables();
    }
};

window.closeAllManual = function() {
    const active = [...window.scalpActivePositions];
    for (let pos of active) {
        window.closeScalping(pos.ticket);
    }
};

window.updateScalpTables = function() {
    const liveTbody = document.getElementById('scalp-live-table');
    const histTbody = document.getElementById('scalp-history-table');
    
    if (liveTbody) {
        if (window.scalpActivePositions.length === 0) {
            if (liveTbody.innerHTML !== '<tr><td colspan="7" class="text-muted py-3">No active manual trades</td></tr>') {
                liveTbody.innerHTML = '<tr><td colspan="7" class="text-muted py-3">No active manual trades</td></tr>';
            }
        } else {
            let html = '';
            for (let p of window.scalpActivePositions) {
                const color = p.profit >= 0 ? 'text-success' : 'text-danger';
                html += <tr>
                    <td>#</td>
                    <td class=" fw-bold"></td>
                    <td></td>
                    <td></td>
                    <td></td>
                    <td class=" fw-bold">{p.profit.toFixed(2)}</td>
                    <td><button class="btn btn-sm btn-outline-danger py-0" onclick="closeScalping()">X</button></td>
                </tr>;
            }
            if (liveTbody.innerHTML !== html) liveTbody.innerHTML = html;
        }
    }
    
    if (histTbody) {
        if (window.scalpHistoryPositions.length === 0) {
            if (histTbody.innerHTML !== '<tr><td colspan="6" class="text-muted py-3">No trade history</td></tr>') {
                histTbody.innerHTML = '<tr><td colspan="6" class="text-muted py-3">No trade history</td></tr>';
            }
        } else {
            let html = '';
            for (let p of window.scalpHistoryPositions) {
                const color = p.profit >= 0 ? 'text-success' : 'text-danger';
                html += <tr>
                    <td></td>
                    <td>#</td>
                    <td class=" fw-bold"></td>
                    <td></td>
                    <td></td>
                    <td class=" fw-bold">{p.profit.toFixed(2)}</td>
                </tr>;
            }
            if (histTbody.innerHTML !== html) histTbody.innerHTML = html;
        }
    }
};
"""

text += "\n" + manual_logic
with open(app_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Injected manual scalping logic!")
