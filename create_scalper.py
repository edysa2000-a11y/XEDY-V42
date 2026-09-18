import sys

html_content = '''<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scalper's Terminal (Manual) — XAUUSD</title>
<style>
  :root{
    --bg:#0a0e17;
    --panel:#131826;
    --panel-border:#232b3d;
    --text:#e8ecf3;
    --muted:#8791a3;
    --green:#1fbf75;
    --green-dim:#0f5c38;
    --red:#e14b5a;
    --red-dim:#5c1f27;
    --amber:#e0a527;
    --cyan:#3ba9e8;
    --purple:#a06be0;
  }
  *{box-sizing:border-box;}
  body{
    margin:0;
    background:var(--bg);
    color:var(--text);
    font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
    padding:24px;
  }
  .wrap{max-width:1420px;margin:0 auto;}
  .header{
    display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;
  }
  .header h1{font-size:28px;font-weight:700;margin:0;letter-spacing:.3px;}
  .badge{
    background:var(--red);color:#fff;font-weight:700;font-size:13px;
    padding:8px 16px;border-radius:6px;
  }
  .badge.off{background:#333c4d;color:var(--muted);}
  .grid{display:grid;gap:18px;}
  .grid-4{grid-template-columns:repeat(4,1fr);}
  .grid-2{grid-template-columns:1fr 1fr;}
  .grid-3{grid-template-columns:1fr 1fr 1fr;}
  .panel{
    background:var(--panel);
    border:1px solid var(--panel-border);
    border-radius:10px;
    padding:22px;
  }
  .panel-title{font-size:16px;font-weight:700;margin:0 0 16px 0;}
  .stat-label{font-size:12px;color:var(--muted);letter-spacing:1px;text-align:center;text-transform:uppercase;margin-bottom:8px;}
  .stat-value{font-size:32px;font-weight:700;text-align:center;}
  .row-4{display:flex;}
  .row-4 > div{flex:1;}
  .sub{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;}
  .big{font-size:38px;font-weight:700;}
  .green{color:var(--green);}
  .red{color:var(--red);}
  .amber{color:var(--amber);}
  .cyan{color:var(--cyan);}
  .purple{color:var(--purple);}
  .muted{color:var(--muted);}
  input[type=text], input[type=number]{
    width:100%;background:#0d1220;border:1px solid var(--panel-border);
    color:var(--text);font-size:18px;font-weight:700;padding:14px 16px;border-radius:8px;
  }
  select{
    width:100%;background:#0d1220;border:1px solid var(--panel-border);
    color:var(--text);font-size:14px;font-weight:600;padding:12px 14px;border-radius:8px;
  }
  label.field-label{font-size:12px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;display:block;margin-bottom:8px;}
  .btn-row{display:flex;gap:14px;margin-top:16px;}
  .btn{
    flex:1;padding:18px;border:none;border-radius:8px;font-size:18px;font-weight:700;
    cursor:pointer;
  }
  .btn-sell{background:var(--red);color:#fff;}
  .btn-buy{background:var(--green);color:#fff;}
  .btn-ghost{background:transparent;border:1px solid var(--panel-border);color:var(--text);}
  .btn:hover{filter:brightness(1.1);}
  .toggle{
    width:52px;height:28px;background:#333c4d;border-radius:14px;position:relative;cursor:pointer;
    transition:.2s;
  }
  .toggle.on{background:var(--green);}
  .toggle::after{
    content:'';position:absolute;top:3px;left:3px;width:22px;height:22px;background:#fff;
    border-radius:50%;transition:.2s;
  }
  .toggle.on::after{left:27px;}
  .flex-between{display:flex;justify-content:space-between;align-items:center;}
  .divider{height:1px;background:var(--panel-border);margin:16px 0;}
  .session-track{
    display:flex;height:40px;border-radius:6px;overflow:hidden;position:relative;margin-top:10px;
  }
  .session-seg{flex:1;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;letter-spacing:.5px;}
  .seg-asia{background:#1b2a3d;color:var(--cyan);}
  .seg-london{background:#2a1b3d;color:var(--purple);}
  .seg-ny{background:#1b3d2a;color:var(--green);}
  .seg-overlap{background:#3d2a1b;color:var(--amber);}
  .now-marker{
    position:absolute;top:-4px;bottom:-4px;width:3px;background:#fff;border-radius:2px;
  }
  .pill{
    display:inline-block;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:700;
  }
  .pill-live{background:var(--red-dim);color:var(--red);}
  .pill-ok{background:var(--green-dim);color:var(--green);}
  .news-item{
    display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--panel-border);
    font-size:13px;
  }
  .news-item:last-child{border-bottom:none;}
  .impact-high{color:var(--red);font-weight:700;}
  .impact-med{color:var(--amber);font-weight:700;}
  table{width:100%;border-collapse:collapse;font-size:14px;}
  th{text-align:left;color:var(--text);font-size:14px;padding:10px 6px;border-bottom:1px solid var(--panel-border);}
  td{padding:12px 6px;color:var(--muted);}
  .empty-row td{text-align:center;padding:24px;color:var(--muted);}
  .footer{
    display:flex;gap:24px;font-size:12px;color:var(--muted);margin-top:20px;flex-wrap:wrap;
  }
  .footer b{color:var(--green);}
  .preset-row{display:flex;gap:10px;margin-top:10px;}
  .preset-btn{
    flex:1;background:#0d1220;border:1px solid var(--panel-border);color:var(--text);
    padding:10px;border-radius:6px;font-size:13px;cursor:pointer;text-align:center;
  }
  .preset-btn.active{border-color:var(--amber);color:var(--amber);}
  .gauge-track{height:10px;background:#0d1220;border-radius:6px;overflow:hidden;margin-top:10px;}
  .gauge-fill{height:100%;background:linear-gradient(90deg,var(--green),var(--amber),var(--red));width:35%;}
  @media (max-width:1100px){
    .grid-4{grid-template-columns:repeat(2,1fr);}
    .grid-2, .grid-3{grid-template-columns:1fr;}
  }
</style>
</head>
<body>
<div class="wrap">

  <div class="header">
    <h1>Scalper's Terminal (Manual)</h1>
    <div class="badge" id="conn-badge">MT5 Disconnected</div>
  </div>

  <!-- TOP PRICE STRIP -->
  <div class="panel grid grid-4" style="margin-bottom:18px;">
    <div>
      <div class="stat-label">XAUUSD Bid</div>
      <div class="stat-value red" id="v-bid">0.00</div>
    </div>
    <div>
      <div class="stat-label">XAUUSD Ask</div>
      <div class="stat-value green" id="v-ask">0.00</div>
    </div>
    <div>
      <div class="stat-label">Spread</div>
      <div class="stat-value amber" id="v-spread">0</div>
    </div>
    <div>
      <div class="stat-label">Tick Vol (30s)</div>
      <div class="stat-value cyan" id="v-tick-vol">0</div>
    </div>
  </div>

  <div class="grid grid-2" style="margin-bottom:18px;">

    <!-- TICK VELOCITY -->
    <div class="panel">
      <div class="flex-between" style="margin-bottom:16px;">
        <div class="panel-title" style="margin-bottom:0;">Tick Velocity (30s Rolling)</div>
        <span class="pill" style="background:#1b2a3d;color:var(--cyan);">TREND: <span style="color:var(--text);" id="v-trend">SIDEWAYS</span></span>
      </div>

      <div class="row-4">
        <div>
          <div class="sub" style="text-align:center;">Tick Up (Naik)</div>
          <div class="big green" style="text-align:center;" id="v-tick-up">0</div>
        </div>
        <div>
          <div class="sub" style="text-align:center;">Tick Down (Turun)</div>
          <div class="big red" style="text-align:center;" id="v-tick-down">0</div>
        </div>
      </div>
      <div class="session-track" style="height:14px;margin-top:18px;" id="v-velocity-track">
        <div style="flex:1;background:var(--green);" id="v-vel-up"></div>
        <div style="flex:1;background:#3a0d12;" id="v-vel-down"></div>
      </div>
      <div class="muted" style="text-align:center;margin-top:10px;font-size:13px;">Momentum Velocity: <b style="color:var(--text);" id="v-velocity-text">Neutral</b></div>
    </div>

    <!-- MANUAL EXECUTION -->
    <div class="panel">
      <div class="panel-title">Manual Execution</div>
      <label class="field-label">Lot Size</label>
      <input type="number" id="manual-lot" value="0.01" step="0.01">
      <div class="preset-row">
        <div class="preset-btn active" title="SL = 1.5x ATR">SL 1.5x ATR</div>
        <div class="preset-btn" title="SL = 2.0x ATR">SL 2.0x ATR</div>
        <div class="preset-btn" title="Custom pips">Custom</div>
      </div>
      <div class="btn-row">
        <button class="btn btn-sell" onclick="sendOrder('SELL')">SELL</button>
        <button class="btn btn-buy" onclick="sendOrder('BUY')">BUY</button>
      </div>
    </div>
  </div>

  <div class="grid grid-2" style="margin-bottom:18px;">

    <!-- SAFE TICK RANGE -->
    <div class="panel" style="border-color:var(--green);">
      <div class="flex-between" style="margin-bottom:6px;">
        <div class="panel-title" style="margin-bottom:0;">Safe Tick Range / 30s (Target Winrate 90%+)</div>
        <span class="pill pill-ok" id="v-safe-zone">SAFE ZONE</span>
      </div>
      <div class="muted" style="font-size:12px;margin-bottom:14px;">
        Threshold di-tune otomatis oleh AI, bukan garansi — angka statis tidak bisa menjamin winrate; ini filter untuk menghindari entry di tick yang terlalu sepi (noise) atau terlalu liar (spike/slippage).
      </div>

      <div class="flex-between">
        <span class="muted" style="font-size:13px;">Current Tick Vol (30s)</span>
        <span style="font-weight:700;" id="v-tick-vol-2">0</span>
      </div>
      <div class="session-track" style="height:16px;margin-top:10px;position:relative;">
        <div style="flex:1;background:#3a0d12;"></div>
        <div style="flex:2;background:var(--green);"></div>
        <div style="flex:1;background:#3d2a1b;"></div>
        <div class="now-marker" id="v-vol-marker" style="left:50%;background:var(--amber);"></div>
      </div>
      <div class="flex-between" style="margin-top:8px;">
        <span class="muted" style="font-size:11px;">&lt;25 (Too Quiet)</span>
        <span class="muted" style="font-size:11px;">45–65 (Safe Zone)</span>
        <span class="muted" style="font-size:11px;">&gt;90 (Overheated)</span>
      </div>
    </div>

    <!-- AI SELF-ADAPTIVE MARKET PROFILE -->
    <div class="panel" style="border-color:var(--amber);">
      <div class="flex-between" style="margin-bottom:6px;">
        <div class="panel-title" style="margin-bottom:0;">AI Self-Adaptive — Market Condition</div>
        <div class="toggle on" id="toggle-ai" onclick="this.classList.toggle('on')"></div>
      </div>
      <div class="muted" style="font-size:12px;margin-bottom:14px;">
        AI otomatis deteksi kondisi market dari tick vol + spread + ATR, lalu adjust tick range, lot, dan SL/TP multiplier.
      </div>

      <table style="font-size:12.5px;">
        <thead>
          <tr>
            <th>Kondisi</th><th>Tick/30s</th><th>Lot Mult</th><th>SL/TP Mult</th><th>Status</th>
          </tr>
        </thead>
        <tbody id="v-ai-table">
          <tr>
            <td style="color:var(--cyan);font-weight:700;">Sepi</td>
            <td>&lt;25</td><td>0.5x</td><td>1.0x</td>
            <td><span class="muted">Standby</span></td>
          </tr>
          <tr>
            <td style="color:var(--green);font-weight:700;">Normal</td>
            <td>25–45</td><td>1.0x</td><td>1.5x</td>
            <td><span class="pill pill-ok">Active</span></td>
          </tr>
          <tr>
            <td style="color:var(--amber);font-weight:700;">Ramai</td>
            <td>45–80</td><td>1.0x</td><td>2.0x</td>
            <td><span class="muted">Standby</span></td>
          </tr>
          <tr>
            <td style="color:var(--red);font-weight:700;">Sangat Ramai (NFP)</td>
            <td>&gt;80</td><td>0.3x</td><td>2.5x</td>
            <td><span class="muted">Standby</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- LIVE TRADES -->
  <div class="panel" style="margin-bottom:18px;">
    <div class="flex-between" style="margin-bottom:16px;">
      <div class="panel-title" style="margin-bottom:0;">Live Trades (MT5 Integrated)</div>
      <button class="btn-ghost" style="padding:8px 16px;border-radius:6px;color:var(--red);border-color:var(--red);cursor:pointer;" onclick="closeAll()">Close All</button>
    </div>
    <table>
      <thead>
        <tr><th>Ticket</th><th>Type</th><th>Lot</th><th>Open</th><th>Current</th><th>Profit</th><th>Action</th></tr>
      </thead>
      <tbody id="v-live-table">
        <tr class="empty-row"><td colspan="7">No active manual trades</td></tr>
      </tbody>
    </table>
  </div>
  
  <div class="footer">
    <div>Database: <b>OK</b></div>
    <div>WebSocket: <b id="ws-status" class="red">DISCONNECTED</b></div>
    <div>Live Ticks: <b id="tick-counter">0</b></div>
  </div>

</div>

<script>
// SCALPER ENGINE & WEBSOCKET

let ws;
let tickHistory = [];
let activePositions = [];

function initWs() {
    ws = new WebSocket('ws://' + window.location.hostname + ':8000/ws');
    
    ws.onopen = () => {
        document.getElementById('ws-status').textContent = 'CONNECTED';
        document.getElementById('ws-status').className = 'green';
        document.getElementById('conn-badge').textContent = 'MT5 Connected (Live)';
        document.getElementById('conn-badge').style.background = 'var(--green)';
    };
    
    ws.onclose = () => {
        document.getElementById('ws-status').textContent = 'DISCONNECTED';
        document.getElementById('ws-status').className = 'red';
        document.getElementById('conn-badge').textContent = 'MT5 Disconnected';
        document.getElementById('conn-badge').style.background = 'var(--red)';
        setTimeout(initWs, 3000);
    };
    
    ws.onmessage = (e) => {
        try {
            const data = JSON.parse(e.data);
            if (data.type === 'tick' || data.type === 'tick_data') {
                processTick(data);
            } else if (data.type === 'v39_data' && data.data && data.data.positions) {
                updatePositions(data.data.positions);
            }
        } catch(err){}
    };
}

let lastUiUpdate = 0;
function processTick(data) {
    const now = Date.now();
    tickHistory.push({ bid: data.bid, ask: data.ask, time: now });
    tickHistory = tickHistory.filter(t => (now - t.time) <= 30000);
    
    let tickUp = 0;
    let tickDown = 0;
    for (let i = 1; i < tickHistory.length; i++) {
        const diff = tickHistory[i].bid - tickHistory[i-1].bid;
        if (diff > 0) tickUp++;
        else if (diff < 0) tickDown++;
    }
    
    document.getElementById('tick-counter').textContent = (parseInt(document.getElementById('tick-counter').textContent) + 1);
    
    // Throttle UI Updates to max 10 FPS
    if (now - lastUiUpdate > 100) {
        lastUiUpdate = now;
        
        document.getElementById('v-bid').textContent = data.bid.toFixed(2);
        document.getElementById('v-ask').textContent = data.ask.toFixed(2);
        document.getElementById('v-spread').textContent = Math.round((data.ask - data.bid) * 100);
        
        const vol = tickHistory.length;
        document.getElementById('v-tick-vol').textContent = vol;
        document.getElementById('v-tick-vol-2').textContent = vol;
        
        document.getElementById('v-tick-up').textContent = tickUp;
        document.getElementById('v-tick-down').textContent = tickDown;
        
        const totalMov = tickUp + tickDown;
        let velPct = 50;
        if (totalMov > 0) velPct = Math.round((tickUp / totalMov) * 100);
        
        document.getElementById('v-vel-up').style.flex = velPct;
        document.getElementById('v-vel-down').style.flex = (100 - velPct);
        
        const vText = document.getElementById('v-velocity-text');
        if (velPct > 60) {
            vText.textContent = "BULLISH (" + velPct + "%)";
            vText.style.color = "var(--green)";
        } else if (velPct < 40) {
            vText.textContent = "BEARISH (" + (100 - velPct) + "%)";
            vText.style.color = "var(--red)";
        } else {
            vText.textContent = "NEUTRAL";
            vText.style.color = "var(--amber)";
        }
        
        let markerPos = Math.min(Math.max((vol / 120) * 100, 0), 100);
        document.getElementById('v-vol-marker').style.left = markerPos + '%';
        
        const safeZone = document.getElementById('v-safe-zone');
        if (vol >= 45 && vol <= 65) {
            safeZone.textContent = "SAFE ZONE";
            safeZone.className = "pill pill-ok";
        } else if (vol < 45) {
            safeZone.textContent = "TOO QUIET";
            safeZone.className = "pill";
            safeZone.style.background = "#333c4d";
        } else {
            safeZone.textContent = "OVERHEATED";
            safeZone.className = "pill pill-live";
        }
    }
}

function updatePositions(positions) {
    // Check if we need to update DOM
    const liveTable = document.getElementById('v-live-table');
    if (!positions || positions.length === 0) {
        if (liveTable.innerHTML.indexOf("No active") === -1) {
            liveTable.innerHTML = '<tr class="empty-row"><td colspan="7">No active manual trades</td></tr>';
        }
        return;
    }
    
    let html = '';
    positions.forEach(p => {
        if (p.symbol === 'XAUUSD') {
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
    });
    
    if (html === '') html = '<tr class="empty-row"><td colspan="7">No active manual trades</td></tr>';
    
    if (liveTable.innerHTML !== html) {
        liveTable.innerHTML = html;
    }
}

function sendOrder(type) {
    const lot = document.getElementById('manual-lot').value;
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: 'trade',
            type: type,
            symbol: 'XAUUSD',
            volume: parseFloat(lot)
        }));
    } else {
        alert("Not connected to MT5!");
    }
}

function closeOrder(ticket) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: 'close',
            ticket: ticket
        }));
    }
}

function closeAll() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: 'close_all',
            symbol: 'XAUUSD'
        }));
    }
}

// Start
initWs();

</script>
</body>
</html>'''

with open(r'C:\Antigravity\Project\XEDY Mission Control\frontend\scalper.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
print("Created scalper.html")
