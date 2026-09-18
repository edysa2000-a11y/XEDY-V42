import sys

app_path = r'C:\Antigravity\Project\XEDY Mission Control\frontend\scalper.html'
with open(app_path, 'r', encoding='utf-8') as f:
    text = f.read()

mock_logic = """
let scalpTicketCounter = 1000;
let activePositions = [];
let historyPositions = [];

function sendOrder(type) {
    const lotInput = document.getElementById('manual-lot');
    let lot = 0.01;
    if (lotInput) lot = parseFloat(lotInput.value);
    
    const bidEl = document.getElementById('v-bid');
    const askEl = document.getElementById('v-ask');
    let currentPrice = 0;
    if (type === 'BUY' && askEl) currentPrice = parseFloat(askEl.textContent);
    else if (type === 'SELL' && bidEl) currentPrice = parseFloat(bidEl.textContent);
    
    if (currentPrice === 0 || isNaN(currentPrice)) return;
    
    const ticket = scalpTicketCounter++;
    activePositions.push({
        ticket: ticket,
        type: type,
        lot: lot,
        open: currentPrice,
        current: currentPrice,
        profit: 0 - (Math.round((parseFloat(askEl.textContent) - parseFloat(bidEl.textContent)) * 100) * 0.1)
    });
    
    updateScalpTables();
}

function closeOrder(ticket) {
    const idx = activePositions.findIndex(p => p.ticket === ticket);
    if (idx !== -1) {
        const pos = activePositions[idx];
        activePositions.splice(idx, 1);
        
        historyPositions.unshift({
            time: new Date().toLocaleTimeString(),
            ticket: pos.ticket,
            type: pos.type,
            lot: pos.lot,
            closePrice: pos.current,
            profit: pos.profit
        });
        
        if (historyPositions.length > 50) historyPositions.pop();
        
        updateScalpTables();
    }
}

function closeAll() {
    const active = [...activePositions];
    for (let pos of active) {
        closeOrder(pos.ticket);
    }
}

function updateScalpTables() {
    const liveTable = document.getElementById('v-live-table');
    
    if (activePositions.length === 0) {
        if (liveTable.innerHTML.indexOf("No active") === -1) {
            liveTable.innerHTML = '<tr class="empty-row"><td colspan="7">No active manual trades</td></tr>';
        }
    } else {
        let html = '';
        for (let p of activePositions) {
            const color = p.profit >= 0 ? 'text-success' : 'text-danger';
            html += <tr>
                <td>#</td>
                <td style="color:var(--);font-weight:700;"></td>
                <td></td>
                <td></td>
                <td></td>
                <td style="color:var(--);font-weight:700;">{p.profit.toFixed(2)}</td>
                <td><button class="btn-ghost" style="padding:4px 8px;border-radius:4px;color:var(--red);border-color:var(--red);cursor:pointer;" onclick="closeOrder()">X</button></td>
            </tr>;
        }
        liveTable.innerHTML = html;
    }
}
"""

text = text.replace("function sendOrder(type) {", mock_logic + "\nfunction sendOrderOld(type) {")

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Added mock execution logic to scalper.html")
