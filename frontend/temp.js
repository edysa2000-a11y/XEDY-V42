
function setup(c){let r=c.getBoundingClientRect(),d=devicePixelRatio||1;c.width=r.width*d;c.height=r.height*d;let x=c.getContext('2d');x.scale(d,d);return [x,r.width,r.height]}

// Chart State
let priceCtx, priceW, priceH;
let indCtx, indW, indH;
let tickHistory = []; // store {time, bid, ask}

function initCharts() {
    [priceCtx, priceW, priceH] = setup(document.getElementById('price'));
    [indCtx, indW, indH] = setup(document.getElementById('ind'));
}

function updatePriceChart() {
    if(!priceCtx) return;
    priceCtx.clearRect(0,0,priceW,priceH);
    priceCtx.strokeStyle='#1d2a36';
    priceCtx.lineWidth=1;
    for(let i=0;i<6;i++){
        let y=20+i*(priceH-38)/5;
        priceCtx.beginPath();priceCtx.moveTo(0,y);priceCtx.lineTo(priceW,y);priceCtx.stroke();
    }
    
    if (tickHistory.length < 2) return;
    
    // Find min/max for scaling
    let minPrice = Infinity, maxPrice = -Infinity;
    tickHistory.forEach(t => {
        if (t.bid < minPrice) minPrice = t.bid;
        if (t.ask > maxPrice) maxPrice = t.ask;
    });
    let range = maxPrice - minPrice;
    if (range === 0) range = 1;
    
    // Draw Ask
    priceCtx.beginPath();
    priceCtx.strokeStyle='#ff174f';
    priceCtx.lineWidth=1.4;
    for(let i=0; i<tickHistory.length; i++) {
        let px = 10 + (i / Math.max(1, tickHistory.length-1)) * (priceW-20);
        let py = 20 + (1 - (tickHistory[i].ask - minPrice)/range) * (priceH-38);
        i===0 ? priceCtx.moveTo(px,py) : priceCtx.lineTo(px,py);
    }
    priceCtx.stroke();
    
    // Draw Bid
    priceCtx.beginPath();
    priceCtx.strokeStyle='#19e59b';
    priceCtx.lineWidth=1.4;
    for(let i=0; i<tickHistory.length; i++) {
        let px = 10 + (i / Math.max(1, tickHistory.length-1)) * (priceW-20);
        let py = 20 + (1 - (tickHistory[i].bid - minPrice)/range) * (priceH-38);
        i===0 ? priceCtx.moveTo(px,py) : priceCtx.lineTo(px,py);
    }
    priceCtx.stroke();
    
    priceCtx.fillStyle='#7e8b97';
    priceCtx.font='10px Segoe UI';
    let step = range/5;
    for(let i=0; i<6; i++){
        let val = (maxPrice - i*step).toFixed(2);
        priceCtx.fillText(val, priceW-43, 20+i*(priceH-32)/5);
    }
}

let indPhase = 0;
function updateIndChart() {
    if(!indCtx) return;
    indCtx.clearRect(0,0,indW,indH);
    indCtx.strokeStyle='#1d2a36';
    for(let i=0;i<5;i++){
        let y=25+i*39;
        indCtx.beginPath();indCtx.moveTo(0,y);indCtx.lineTo(indW,y);indCtx.stroke();
    }
    
    // Animate phases based on real-time netVelocity
    indPhase += 0.05 + (Math.abs(prevVelocity) * 0.005);
    
    function drawOsc(base, amp, f, col, offset, noise) {
        indCtx.beginPath();
        for(let i=0;i<120;i++){
            let px=7+i*(indW-14)/119;
            // use tickHistory if available for the first oscillator
            let val = Math.sin(i*f + indPhase*offset) * amp;
            if (noise && tickHistory.length > 0) {
                let histIdx = Math.floor(i * (tickHistory.length/120));
                let t = tickHistory[histIdx];
                if(t) val += (t.ask - t.bid) * 10 * noise;
            }
            let py=base + val;
            i?indCtx.lineTo(px,py):indCtx.moveTo(px,py);
        }
        indCtx.strokeStyle=col;
        indCtx.lineWidth=1.3;
        indCtx.stroke();
    }
    
    // 5 Oscillators
    drawOsc(32, 12, 0.15, '#19e59b', 1, 0.5); // Tick Velocity Osc
    drawOsc(70, 8, 0.12, '#a980ff', 0.8, 0);  // RSI
    drawOsc(108, 10, 0.1, '#42b8ff', 1.2, 0); // MACD
    drawOsc(146, 6, 0.08, '#ffd23f', 0.5, 0); // ADX
    drawOsc(184, 5, 0.05, '#ff5261', 2, 0);   // ATR

    indCtx.fillStyle='#81909d';
    indCtx.font='9px Segoe UI';
    ['TICK VELOCITY OSCILLATOR','RSI (14)','MACD (12,26,9)','ADX (14)','ATR (14)'].forEach((t,i)=>indCtx.fillText(t,7,13+i*39));
}

function clock(){
    let s=new Date().toLocaleTimeString('en-GB',{hour12:false});
    document.getElementById('clock').textContent=s;
    document.getElementById('update').textContent='UPDATE: '+s+' UTC+7';
}

initCharts();
clock();
setInterval(clock,1000);
addEventListener('resize',()=>{initCharts();updatePriceChart();updateIndChart()});

// --- WEBSOCKET CLIENT-SIDE ENGINE ---
let prevVelocity = 0;
let appStartTime = Date.now();

function connectWS() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host || 'localhost:8000'}/ws`;
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'tick_data' && data.symbol === 'XAUUSD') {
            const now = Date.now();
            tickHistory.push({ time: now, bid: data.bid, ask: data.ask });
            
            // Keep last 60 seconds of ticks
            tickHistory = tickHistory.filter(t => now - t.time <= 60000);
            
            // Calculate UI Metrics
            let spread = Math.round((data.ask - data.bid) * 100);
            let upVel = 0, downVel = 0;
            
            for(let i=1; i<tickHistory.length; i++) {
                let delta = tickHistory[i].bid - tickHistory[i-1].bid;
                if (delta > 0) upVel++;
                else if (delta < 0) downVel++;
            }
            
            let netVel = upVel - downVel;
            let totalVel = upVel + downVel;
            let accel = netVel - prevVelocity;
            prevVelocity = netVel;
            
            let imb = 0;
            if (totalVel > 0) imb = Math.round((netVel / totalVel) * 100);
            let score = Math.round((netVel / Math.max(1, totalVel)) * 100);
            let absScore = Math.abs(score);
            let isBull = score > 0;
            
            // Helpers
            const setCol = (id, val, thres, clsPos, clsNeg) => {
                let el = document.getElementById(id);
                if(!el) return;
                el.innerText = val;
                el.className = (val > thres) ? clsPos : (val < -thres ? clsNeg : '');
            };
            const setTxtCol = (id, txt, isPos) => {
                let el = document.getElementById(id);
                if(!el) return;
                el.innerText = txt;
                el.className = isPos ? 'green' : 'red';
            };
            
            // Top KPIs
            document.getElementById('val-spread').innerText = spread;
            document.getElementById('val-up').innerText = upVel;
            document.getElementById('val-down').innerText = downVel;
            
            setCol('val-net', netVel, 0, 'val green', 'val red');
            setCol('val-accel', accel > 0 ? '+'+accel : accel, 0, 'val green', 'val red');
            
            let imbEl = document.getElementById('val-imb');
            imbEl.innerText = imb + '%';
            imbEl.className = 'val ' + (imb > 0 ? 'green' : (imb < 0 ? 'red' : ''));
            document.getElementById('unit-imb').innerText = imb > 0 ? 'UP DOMINANT' : (imb < 0 ? 'DOWN DOMINANT' : 'BALANCED');
            
            let scoreEl = document.getElementById('val-score');
            scoreEl.innerText = score;
            scoreEl.className = 'val ' + (score > 0 ? 'green' : (score < 0 ? 'red' : ''));
            document.getElementById('unit-score').innerText = '/100 · ' + (score > 20 ? 'BULLISH' : (score < -20 ? 'BEARISH' : 'NEUTRAL'));
            
            // Trend Direction
            let dirEl = document.getElementById('val-dir');
            dirEl.innerText = score > 20 ? 'BULLISH ↑' : (score < -20 ? 'BEARISH ↓' : 'NEUTRAL ↔');
            dirEl.className = 'direction ' + (score > 20 ? 'green' : (score < -20 ? 'red' : 'yellow'));
            
            let conf = Math.min(100, absScore + 15);
            document.getElementById('val-conf').innerText = conf + '%';
            document.getElementById('bar-conf').style.width = conf + '%';
            document.getElementById('bar-conf').style.background = score > 20 ? 'var(--g)' : (score < -20 ? 'var(--r)' : 'var(--y)');
            
            // S&R Current
            document.getElementById('sr-cur').innerText = data.bid.toFixed(2);
            document.getElementById('sr-r1').innerText = (data.bid + 3.5).toFixed(2);
            document.getElementById('sr-r2').innerText = (data.bid + 6.2).toFixed(2);
            document.getElementById('sr-s1').innerText = (data.bid - 3.2).toFixed(2);
            document.getElementById('sr-s2').innerText = (data.bid - 5.8).toFixed(2);
            document.getElementById('sr-vwap').innerText = (data.bid - (score*0.01)).toFixed(2);
            
            // --- FULL DYNAMIC SIMULATION ---
            
            // 1. Trend Engine Multi-Factor
            setCol('fac-tv-v', score + '%', 0, 'green', 'red');
            setCol('fac-tv-s', Math.round(score * 0.3), 0, 'green', 'red');
            setTxtCol('fac-ema-v', isBull ? 'Bullish' : 'Bearish', isBull);
            setCol('fac-ema-s', isBull ? 12 : -12, 0, 'green', 'red');
            document.getElementById('fac-adx-v').innerText = (20 + (absScore * 0.4)).toFixed(1);
            setCol('fac-adx-s', Math.round(absScore * 0.2) * (isBull?1:-1), 0, 'green', 'red');
            setTxtCol('fac-ms-v', isBull ? 'Higher High' : 'Lower Low', isBull);
            setCol('fac-ms-s', isBull ? 11 : -11, 0, 'green', 'red');
            setTxtCol('fac-vwap-v', isBull ? 'Above' : 'Below', isBull);
            setCol('fac-vwap-s', isBull ? 6 : -6, 0, 'green', 'red');
            document.getElementById('fac-rsi-v').innerText = (50 + (score * 0.4)).toFixed(1);
            setCol('fac-rsi-s', Math.round(score * 0.1), 0, 'green', 'red');
            setTxtCol('fac-macd-v', isBull ? 'Bullish' : 'Bearish', isBull);
            setCol('fac-macd-s', isBull ? 4 : -4, 0, 'green', 'red');
            document.getElementById('fac-atr-v').innerText = (0.5 + (spread * 0.01)).toFixed(2);
            setCol('fac-atr-s', spread > 30 ? -3 : 3, 0, 'green', 'red');
            setTxtCol('fac-of-v', isBull ? 'Positive' : 'Negative', isBull);
            setCol('fac-of-s', isBull ? 5 : -5, 0, 'green', 'red');

            // 2. Trend Duration Engine
            let ageSecs = Math.floor((now - appStartTime) / 1000);
            let mins = Math.floor(ageSecs / 60);
            let hrs = Math.floor(mins / 60);
            document.getElementById('td-age').innerText = `${hrs.toString().padStart(2,'0')}:${(mins%60).toString().padStart(2,'0')}:${(ageSecs%60).toString().padStart(2,'0')}`;
            
            let estMax = Math.max(30, 120 - absScore);
            document.getElementById('td-est').innerText = `${Math.floor(estMax*0.5)}–${estMax} MIN`;
            document.getElementById('td-rem').innerText = `${Math.max(0, Math.floor(estMax*0.5) - mins)}–${Math.max(0, estMax - mins)} MIN`;
            
            let matStr = ageSecs < 300 ? 'EARLY' : (ageSecs < 1800 ? 'DEVELOPING' : 'MATURE');
            setTxtCol('td-mat', matStr, matStr !== 'MATURE');
            setTxtCol('td-per', absScore > 50 ? 'HIGH' : 'LOW', absScore > 50);
            
            let phaseIdx = ageSecs < 60 ? 0 : (absScore > 60 ? 2 : (absScore > 30 ? 1 : (absScore < 10 ? 4 : 3)));
            document.getElementById('td-phase').innerHTML = [0,1,2,3,4].map(i => `<i class="${i===phaseIdx ? 'on':''}"></i>`).join('');
            
            setCol('ta-now', netVel, 0, 'green', 'red');
            setCol('ta-prev', netVel - accel, 0, '', '');
            setCol('ta-acc', accel > 0 ? '+'+accel : accel, 0, 'green', 'red');
            setTxtCol('ta-stat', accel > 0 ? (isBull?'ACCELERATING BULLISH':'DECELERATING BEARISH') : (isBull?'DECELERATING BULLISH':'ACCELERATING BEARISH'), accel > 0 === isBull);

            // 3. Multi-Timeframe Matrix
            const updateTF = (id, bias) => {
                let s = Math.min(100, Math.max(0, Math.abs(score + bias) + 20));
                let tBull = (score + bias) > 0;
                let txt = Math.abs(score+bias) < 10 ? '→ RANGE' : (tBull ? '↑ BULLISH' : '↓ BEARISH');
                document.getElementById(`tf-${id}-t`).innerText = txt;
                document.getElementById(`tf-${id}-t`).className = Math.abs(score+bias) < 10 ? 'yellow' : (tBull ? 'green' : 'red');
                document.getElementById(`tf-${id}-s`).innerText = Math.round(s) + '%';
                let ph = s > 70 ? 'TRENDING' : (s > 40 ? 'EXPANSION' : 'RANGE');
                document.getElementById(`tf-${id}-p`).innerText = ph;
                document.getElementById(`tf-${id}-p`).className = ph === 'RANGE' ? 'cyan' : (ph==='TRENDING' ? (tBull?'green':'red') : 'yellow');
            };
            updateTF('t', 0);
            updateTF('m1', -10);
            updateTF('m5', 10);
            updateTF('m15', 5);
            updateTF('m30', -5);
            updateTF('h1', 15);

            // 4. Forecast Probabilities
            const updateFc = (id, base) => {
                let p = Math.min(95, Math.max(5, base + (score*0.3)));
                document.getElementById(`fc-${id}-p`).innerText = Math.round(p) + '%';
                document.getElementById(`fc-${id}-t`).innerText = isBull ? 'BULLISH' : 'BEARISH';
                document.getElementById(`fc-${id}-t`).className = isBull ? 'green' : 'red';
                document.getElementById(`fc-${id}-o`).innerText = Math.round(100-p) + (isBull ? '% BEAR' : '% BULL');
                document.getElementById(`fc-${id}-o`).className = isBull ? 'red' : 'green';
            };
            updateFc('5', 60);
            updateFc('30', 55);
            updateFc('60', 52);

            // 5. Market Regime & Reversal
            setTxtCol('mr-sig', isBull ? 'TRENDING ↑' : 'TRENDING ↓', isBull);
            document.getElementById('mr-conf').innerText = conf + '%';
            setTxtCol('mr-vol', spread > 25 ? 'HIGH' : 'NORMAL', spread < 25);
            setTxtCol('mr-state', totalVel > 60 ? 'ACTIVE' : 'CHOPPY', totalVel > 60);
            
            let revRisk = Math.max(5, 100 - conf - (accel > 0 ? 10 : -10));
            document.getElementById('rr-total').innerText = revRisk + '%';
            document.getElementById('rr-total').className = revRisk > 40 ? 'red' : (revRisk > 20 ? 'yellow' : 'green');
            document.getElementById('rr-1').innerText = Math.round(revRisk * 0.3) + '%';
            document.getElementById('rr-2').innerText = Math.round(revRisk * 0.25) + '%';
            document.getElementById('rr-3').innerText = Math.round(revRisk * 0.2) + '%';
            document.getElementById('rr-4').innerText = Math.round(revRisk * 0.15) + '%';
            document.getElementById('rr-5').innerText = Math.round(revRisk * 0.1) + '%';
            
            // 6. Smart Signal & Entry
            document.getElementById('eq-title').innerText = isBull ? 'Entry Quality — BUY' : 'Entry Quality — SELL';
            let eq = Math.min(100, Math.max(0, conf - revRisk + (accel*2)));
            document.getElementById('eq-total').innerText = eq + '/100';
            document.getElementById('eq-total').className = eq > 70 ? 'green' : (eq > 40 ? 'yellow' : 'red');
            document.getElementById('eq-1').innerText = conf + '%';
            document.getElementById('eq-2').innerText = Math.min(100, absScore + 20) + '%';
            document.getElementById('eq-3').innerText = Math.min(100, ageSecs > 300 ? 80 : 40) + '%';
            document.getElementById('eq-4').innerText = Math.max(10, 80 - revRisk) + '%';
            document.getElementById('eq-5').innerText = revRisk + '%';
            document.getElementById('eq-5').className = revRisk > 40 ? 'red' : 'green';

            document.getElementById('ss-sig').innerText = isBull ? 'BUY WATCH ↑' : 'SELL WATCH ↓';
            document.getElementById('ss-sig').className = 'signal ' + (isBull ? 'green' : 'red');
            document.getElementById('ss-conf').innerText = isBull ? (data.bid + 0.5).toFixed(2) : (data.bid - 0.5).toFixed(2);
            document.getElementById('ss-bias').innerText = isBull ? 'BULLISH' : 'BEARISH';
            document.getElementById('ss-bias').className = isBull ? 'green' : 'red';
            document.getElementById('ss-conf-pct').innerText = conf + '%';
            document.getElementById('ss-dur').innerText = document.getElementById('td-est').innerText;
            document.getElementById('ss-inv').innerText = isBull ? (data.bid - 2.5).toFixed(2) : (data.bid + 2.5).toFixed(2);

            // Redraw Chart
            updatePriceChart();
            updateIndChart();
        }
    };
    
    ws.onclose = () => setTimeout(connectWS, 2000);
}
connectWS();
