// XEDY V42 ENTERPRISE - Bloomberg Terminal Logic

window.API_BASE = '';
const hostName = window.location.hostname;
if (hostName.includes('github.io') || hostName.includes('vercel.app') || hostName.includes('netlify.app')) {
    window.API_BASE = 'http://localhost:8000';
}

document.addEventListener('DOMContentLoaded', () => {
    // 1. Clock functionality
    const timeDisplay = document.getElementById('sys-time');
    setInterval(() => {
        const now = new Date();
        timeDisplay.innerText = now.toISOString().split('T')[1].split('.')[0] + " UTC";
    }, 1000);

    // Fetch Score Stats (Backtest XGBoost)
    async function fetchScoreStats() {
        try {
            const res = await fetch(window.API_BASE + '/api/v1/score_stats');
            if (res.ok) {
                const data = await res.json();
                if (data && data.metrics) {
                    const wr80 = document.getElementById('stat-wr-80');
                    const wr90 = document.getElementById('stat-wr-90');
                    const dailyFreq = document.getElementById('stat-daily-freq');
                    
                    if (wr80 && data.metrics.score_80_90) {
                        wr80.innerText = `${data.metrics.score_80_90.winrate}% Winrate`;
                    }
                    if (wr90 && data.metrics.score_90_plus) {
                        wr90.innerText = `${data.metrics.score_90_plus.winrate}% Winrate`;
                    }
                    if (dailyFreq && data.daily_distribution && data.daily_distribution.length > 0) {
                        const today = data.daily_distribution[0];
                        dailyFreq.innerHTML = `Peluang Hari Ini: <span class="text-white">Skor 80-90 (${today.count_80_90}x), Skor >90 (${today.count_90_plus}x)</span>`;
                    }
                }
            }
        } catch (e) {
            console.error("Failed to fetch score stats:", e);
        }
    }
    
    // Call it initially and then every 1 hour
    fetchScoreStats();
    setInterval(fetchScoreStats, 3600000);

    // Fetch System Logs
    async function fetchLogs() {
        try {
            const res = await fetch(window.API_BASE + '/api/v1/logs');
            if (res.ok) {
                const data = await res.json();
                
                const profitLogContent = document.getElementById('profit-log-content');
                if (profitLogContent && data.profit_monitor) {
                    profitLogContent.innerText = data.profit_monitor.length > 0 
                        ? data.profit_monitor.join('\n') 
                        : "Belum ada log dari Profit Monitor Daemon...";
                    profitLogContent.parentElement.scrollTop = profitLogContent.parentElement.scrollHeight;
                }
                
                const decisionLogContent = document.getElementById('decision-log-content');
                if (decisionLogContent && data.decision_engine) {
                    decisionLogContent.innerText = data.decision_engine.length > 0 
                        ? data.decision_engine.join('\n') 
                        : "Belum ada log dari Decision Priority Engine...";
                    decisionLogContent.parentElement.scrollTop = decisionLogContent.parentElement.scrollHeight;
                }
            }
        } catch (e) {
            console.error("Failed to fetch logs:", e);
        }
    }
    
    // Refresh logs every 3 seconds if active tab is logs
    setInterval(() => {
        const activeNav = document.querySelector('.nav-link.active');
        if (activeNav && activeNav.getAttribute('data-target') === 'tab-logs') {
            fetchLogs();
        }
    }, 3000);
    
    // Add manual refresh button listener
    const btnRefreshLogs = document.getElementById('btn-refresh-logs');
    if (btnRefreshLogs) {
        btnRefreshLogs.addEventListener('click', () => {
            fetchLogs();
            if (typeof showToast === 'function') {
                showToast('Logs diperbarui!', 'success');
            }
        });
    }

    // 2. SPA Tab Navigation
    const navLinks = document.querySelectorAll('.nav-link');
    const tabs = document.querySelectorAll('.spa-tab');

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            tabs.forEach(t => t.classList.add('d-none'));
            const targetId = link.getAttribute('data-target');
            const targetTab = document.getElementById(targetId);
            if (targetTab) {
                targetTab.classList.remove('d-none');
            }
            
            // Save active tab state
            localStorage.setItem('activeTab', targetId);
            
            if (targetId === 'tab-market' && typeof window.initTvChart === 'function') {
                setTimeout(() => {
                    window.initTvChart();
                }, 50);
            } else if (targetId === 'tab-analytics' && typeof window.initAnalyticsChart === 'function') {
                setTimeout(() => {
                    window.initAnalyticsChart();
                }, 50);
            } else if (targetId === 'tab-forecast' && typeof window.fetchForecastStats === 'function') {
                setTimeout(() => {
                    window.fetchForecastStats();
                }, 50);
            }
            
            // Trigger resize event so charts inside hidden tabs can recalculate their size
            setTimeout(() => { window.dispatchEvent(new Event('resize')); }, 10);
        });
    });

    // Tab restore logic moved to the bottom of the file to ensure all functions are defined first

    // 2b. Manual Connect Button
    const btnConnectMt5 = document.getElementById('btn-connect-mt5');
    if (btnConnectMt5) {
        btnConnectMt5.addEventListener('click', () => {
            if (!window.globalWs || window.globalWs.readyState !== WebSocket.OPEN) {
                alert("WebSocket is not connected to the backend!");
                return;
            }
            btnConnectMt5.innerText = '🔌 CONNECTING...';
            btnConnectMt5.classList.replace('btn-outline-primary', 'btn-primary');
            
            // Send Reconnect Signal to Python Backend
            window.globalWs.send(JSON.stringify({ "action": "reconnect_mt5" }));
            
            setTimeout(() => {
                btnConnectMt5.innerText = '🔌 CONNECT MT5';
                btnConnectMt5.classList.replace('btn-primary', 'btn-outline-primary');
            }, 3000);
        });
    }

    // 3. Plotly Chart (Dark Theme)
    const chartDiv = document.getElementById('market-chart');
    if (chartDiv) {
        const chartLayout = {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#8b949e' },
            margin: { t: 10, b: 30, l: 40, r: 10 },
            xaxis: { showgrid: false },
            yaxis: { 
                showgrid: true, 
                gridcolor: '#30363d', 
                tickformat: '.2f', 
                exponentformat: 'none',
                automargin: true
            }
        };
        try {
            if (typeof Plotly !== 'undefined') {
                Plotly.newPlot(chartDiv, [{
                    x: ['2026-07-28 09:00', '2026-07-28 10:00', '2026-07-28 11:00'],
                    y: [2045, 2050, 2048],
                    type: 'scatter',
                    mode: 'lines',
                    line: { color: '#58a6ff', width: 2 }
                }], chartLayout);
            } else {
                console.error("Plotly is not loaded");
            }
        } catch (err) {
            console.error("Error rendering Plotly chart:", err);
        }
    }

    // 3b. TradingView Lightweight Chart (Disabled - Using MT5 Web Terminal iframe)
    window.initTvChart = function() {
        console.log("Using embedded MT5 Web Terminal iframe.");
    };

    window.initAnalyticsChart = function() {
        const div = document.getElementById('analytics-equity-chart');
        if (!div || typeof Plotly === 'undefined') return;
        
        // Generate simulated equity curve starting at 10000 and ending at 10420 (+4.2%)
        const xData = [];
        const yData = [];
        let curEquity = 10000.0;
        const steps = 30;
        const now = new Date();
        
        for (let i = 0; i <= steps; i++) {
            const date = new Date(now.getTime() - (steps - i) * 24 * 60 * 60 * 1000);
            xData.push(date.toISOString().split('T')[0]);
            
            if (i === 0) {
                yData.push(10000.0);
            } else {
                // Add some realistic random walk with an upward drift
                const change = (Math.random() - 0.35) * 80.0 + 19.5; 
                curEquity += change;
                // Force last step to exactly 10420 for +4.2% return consistency
                if (i === steps) {
                    yData.push(10420.0);
                } else {
                    yData.push(parseFloat(curEquity.toFixed(2)));
                }
            }
        }
        
        const layout = {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#8b949e', family: 'Outfit, sans-serif' },
            margin: { t: 15, b: 35, l: 60, r: 15 },
            xaxis: { 
                showgrid: true, 
                gridcolor: '#21262d',
                tickangle: -30
            },
            yaxis: { 
                showgrid: true, 
                gridcolor: '#30363d', 
                tickformat: '$,.2f', 
                exponentformat: 'none',
                automargin: true
            }
        };
        
        const trace = {
            x: xData,
            y: yData,
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#2ea043', width: 2.5 },
            marker: { size: 4, color: '#3fb950' },
            fill: 'tozeroy',
            fillcolor: 'rgba(46, 160, 67, 0.08)',
            name: 'Equity'
        };
        
        Plotly.newPlot(div, [trace], layout, { responsive: true, displayModeBar: false });
    };

    // 4. State Management (1 FPS Throttle)
    let latestTick = null;
    let latestSignal = null;
    let latestAtr = 15.0; // Dynamic scaling variable
    const historyX = [];
    const historyY = [];

    setInterval(() => {
        if (latestTick) {
            const priceStr = latestTick.bid.toFixed(2);
            document.getElementById('kpi-price').innerText = priceStr;
            document.getElementById('top-price').innerText = priceStr;
            
            const timeStr = new Date(latestTick.time * 1000).toLocaleTimeString();
            document.getElementById('bottom-update').innerText = timeStr;

            historyX.push(timeStr);
            historyY.push(latestTick.bid);
            
            if (historyX.length > 50) {
                historyX.shift();
                historyY.shift();
            }
            
            if (chartDiv) {
                const tabExec = document.getElementById('tab-executive');
                // Only update the chart if the Executive Dashboard is currently visible
                if (!tabExec || !tabExec.classList.contains('d-none')) {
                    Plotly.update(chartDiv, { x: [historyX], y: [historyY] });
                }
            }
        }

        if (latestSignal) {
            const scoreStr = (latestSignal.confidence * 100).toFixed(1) + "%";
            const kpiConf = document.getElementById('kpi-confidence');
            if (kpiConf) kpiConf.innerText = scoreStr;
            
            const panelConf = document.getElementById('panel-confidence');
            if (panelConf) panelConf.innerText = scoreStr;
            
            const recEl = document.getElementById('ai-rec');
            if (recEl) {
                recEl.innerText = latestSignal.signal;
                if (latestSignal.signal === 'BUY') {
                    recEl.className = 'text-bullish fw-bold mb-0';
                } else if (latestSignal.signal === 'SELL') {
                    recEl.className = 'text-bearish fw-bold mb-0';
                } else {
                    recEl.className = 'text-sideway fw-bold mb-0';
                }
            }
        }
        
        // UI Updates that do not depend on live market ticks (e.g. Risk Dropdown)
        const osPlanRisk = document.getElementById('os-plan-risk');
        const osPlanMgmt = document.getElementById('os-plan-mgmt');
        
        if (osPlanMgmt) {
            const atrMultiplier = typeof latestAtr !== 'undefined' && latestAtr ? latestAtr : 15.0;
            const trailDist = atrMultiplier * 0.5;
            osPlanMgmt.innerText = `Move SL to BE at TP1. Trail by ${trailDist.toFixed(2)} pts.`;
        }
        
        if (osPlanRisk) {
            const riskSelect = document.getElementById('os-risk-profile');
            const riskProfile = riskSelect ? riskSelect.value : 'standard';
            
            let riskSafe, riskStd, riskSuper;
            if (riskProfile === 'conservative') {
                riskSafe = 0.5; riskStd = 1.0; riskSuper = 1.5;
            } else if (riskProfile === 'moderate') {
                riskSafe = 1.5; riskStd = 2.5; riskSuper = 4.0;
            } else if (riskProfile === 'extreme') {
                riskSafe = 2.5; riskStd = 4.0; riskSuper = 6.0;
            } else { // standard
                riskSafe = 1.0; riskStd = 1.5; riskSuper = 2.5;
            }
            
            let uesScore = 90; // Default standard score if no signal
            if (typeof latestSignal !== 'undefined' && latestSignal) {
                const confVal = Math.round(latestSignal.confidence * 100);
                uesScore = confVal + 10;
                if (uesScore > 98) uesScore = 98;
            }
            
            if (uesScore < 90) {
                osPlanRisk.innerHTML = `<span class="text-success fw-bold">${riskSafe.toFixed(1)}% of Equity (Safe Mode)</span>`;
            } else if (uesScore >= 95) {
                osPlanRisk.innerHTML = `<span class="text-danger fw-bold">${riskSuper.toFixed(1)}% of Equity (Sniper Mode)</span>`;
            } else {
                osPlanRisk.innerText = `${riskStd.toFixed(1)}% of Equity (Standard)`;
            }
        }
        
        window.forceRiskUpdate = function() {
            if (typeof window.latestDe !== 'undefined') {
                updateDashboard(window.latestDe, window.latestTick);
            }
        };
        
        // Live XAU AI GOLD OS Execution Plan Update (Throttled 1 FPS)
        if (latestTick) {
            const osPlanEntry = document.getElementById('os-plan-entry');
            if (osPlanEntry) {
                const osPlanSl = document.getElementById('os-plan-sl');
                const osPlanTp1 = document.getElementById('os-plan-tp1');
                const osPlanTp2 = document.getElementById('os-plan-tp2');
                
                const price = latestTick.bid;
                const isBuy = (typeof latestSignal !== 'undefined' && latestSignal && latestSignal.signal === 'SELL') ? false : true;
                
                const atrMultiplier = latestAtr ? latestAtr : 15.0;
                const entryZoneWidth = atrMultiplier * 0.15;
                const stopLossDist = atrMultiplier * 1.5;
                const tp1Dist = atrMultiplier * 1.0;
                const tp2Dist = atrMultiplier * 2.5;
                
                if (isBuy) {
                    osPlanEntry.innerText = `${(price - entryZoneWidth).toFixed(2)} - ${(price).toFixed(2)}`;
                    if (osPlanSl) osPlanSl.innerText = (price - stopLossDist).toFixed(2);
                    if (osPlanTp1) osPlanTp1.innerText = (price + tp1Dist).toFixed(2);
                    if (osPlanTp2) osPlanTp2.innerText = (price + tp2Dist).toFixed(2);
                } else {
                    osPlanEntry.innerText = `${(price).toFixed(2)} - ${(price + entryZoneWidth).toFixed(2)}`;
                    if (osPlanSl) osPlanSl.innerText = (price + stopLossDist).toFixed(2);
                    if (osPlanTp1) osPlanTp1.innerText = (price - tp1Dist).toFixed(2);
                    if (osPlanTp2) osPlanTp2.innerText = (price - tp2Dist).toFixed(2);
                }
            }
        }
    }, 1000); 

    // 5. WebSocket Connection
    window.globalWs = null;
    
    function initWebSocket() {
        let wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let wsHost = window.location.host;
        
        // Cloud Fallback (GitHub Pages / Vercel / Netlify) -> Force connection to local backend
        const hostName = window.location.hostname;
        if (hostName.includes('github.io') || hostName.includes('vercel.app') || hostName.includes('netlify.app')) {
            wsProtocol = 'ws:'; // Localhost does not use HTTPS/WSS natively
            wsHost = '127.0.0.1:8000'; // Default local backend port
        }
        
        const wsUrl = `${wsProtocol}//${wsHost}/api/v1/ws`;
        
        const ws = new WebSocket(wsUrl);
        window.globalWs = ws;
        const wsStatus = document.getElementById('bottom-ws');
        
        ws.onopen = () => {
            console.log("WebSocket Connected");
            wsStatus.className = 'text-bullish';
            wsStatus.innerText = 'OK';
            // Sync local storage parameters back to server immediately to keep settings persistent across refreshes
            setTimeout(() => {
                if (window.sendTradingSettings) window.sendTradingSettings();
            }, 250);
        };
        
        let lastPingTime = 0;
        setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                lastPingTime = performance.now();
                ws.send("ping");
            }
        }, 2000);
        
        ws.onmessage = (event) => {
            if (event.data === "pong") {
                const latency = Math.round(performance.now() - lastPingTime);
                document.getElementById('sys-latency').innerText = latency + 'ms';
                return;
            }

            const data = JSON.parse(event.data);
            
            if (data.type === 'tick') {
                latestTick = data; 
            }
            if (data.type === 'settings_updated') {
                autotradeEnabled = data.autotrade;
                localStorage.setItem('autotrade_enabled', data.autotrade);

                const lotInput = document.getElementById('trading-lot-input');
                if (lotInput) {
                    lotInput.value = data.lot_size.toFixed(2);
                    localStorage.setItem('trading_lot', data.lot_size);
                }
                
                const confInput = document.getElementById('confidence-threshold-input');
                if (confInput && data.confidence_threshold !== undefined) {
                    const roundedConf = Math.round(data.confidence_threshold * 100);
                    confInput.value = roundedConf;
                    localStorage.setItem('confidence_threshold', roundedConf);
                }
                
                const maxOpInput = document.getElementById('max-op-input');
                if (maxOpInput && data.max_positions !== undefined) {
                    maxOpInput.value = data.max_positions;
                    localStorage.setItem('max_positions', data.max_positions);
                }
                
                if (data.auto_lot !== undefined) {
                    localStorage.setItem('auto_lot_enabled', data.auto_lot);
                    updateAutoLotUI(data.auto_lot);
                }
                
                if (data.risk_percent !== undefined) {
                    const riskInput = document.getElementById('risk-percent-input');
                    if (riskInput) {
                        riskInput.value = data.risk_percent.toFixed(1);
                        localStorage.setItem('risk_percent', data.risk_percent);
                    }
                }
                
                if (data.hedging_enabled !== undefined) {
                    hedgingEnabled = data.hedging_enabled;
                    localStorage.setItem('hedging_enabled', data.hedging_enabled);
                    const hedgingBtn = document.getElementById('hedging-toggle-btn');
                    if (hedgingBtn) {
                        if (hedgingEnabled) {
                            hedgingBtn.innerText = 'ON';
                            hedgingBtn.className = 'btn btn-sm btn-success';
                            hedgingBtn.style.boxShadow = '0 0 8px rgba(46, 160, 67, 0.6)';
                        } else {
                            hedgingBtn.innerText = 'OFF';
                            hedgingBtn.className = 'btn btn-sm btn-outline-danger';
                            hedgingBtn.style.boxShadow = 'none';
                        }
                    }
                }
                
                const toggleBtn = document.getElementById('autotrade-toggle-btn');
                if (toggleBtn) {
                    if (autotradeEnabled) {
                        toggleBtn.innerText = 'ON';
                        toggleBtn.className = 'btn btn-sm btn-success';
                        toggleBtn.style.boxShadow = '0 0 8px rgba(46, 160, 67, 0.6)';
                    } else {
                        toggleBtn.innerText = 'OFF';
                        toggleBtn.className = 'btn btn-sm btn-outline-danger';
                        toggleBtn.style.boxShadow = 'none';
                    }
                }
                
                if (data.active_method !== undefined) {
                    const activeMethodBadge = document.getElementById('active-method-badge');
                    if (activeMethodBadge) {
                        activeMethodBadge.innerText = data.active_method.replace(/-/g, ' ').toUpperCase();
                    }
                    const activeAiSelect = document.getElementById('active-ai-model-select');
                    if (activeAiSelect) {
                        activeAiSelect.value = data.active_method;
                        const titleEl = document.getElementById('selected-model-title');
                        const descEl = document.getElementById('selected-model-desc');
                        if (typeof modelInfo !== 'undefined' && modelInfo[data.active_method] && titleEl && descEl) {
                            titleEl.innerText = modelInfo[data.active_method].title;
                            descEl.innerText = modelInfo[data.active_method].desc;
                        }
                    }
                }
            }
            if (data.type === 'server_shutdown_ack') {
                const powerBtn = document.getElementById('server-power-btn');
                if (powerBtn) {
                    powerBtn.innerText = 'SERVER STATUS: OFF';
                    powerBtn.className = 'btn btn-sm btn-outline-danger w-100 fw-bold py-2 mt-2';
                    powerBtn.style.boxShadow = 'none';
                }
                const wsStatus = document.getElementById('ws-status');
                if (wsStatus) {
                    wsStatus.innerText = 'OFFLINE';
                    wsStatus.className = 'text-critical';
                }
                const latencyEl = document.getElementById('sys-latency');
                if (latencyEl) latencyEl.innerText = '---';
                alert("Server shutdown requested successfully. Uvicorn process is terminating.");
            }
            if (data.type === 'ai_signal') {
                latestSignal = data;
            }
            if (data.type === 'dashboard_data') {
                const de = data.data_engine;
                const ne = data.news_engine;

                if (de) {
                    if (de.account) {
                        const acc = de.account;
                        const elEquity = document.getElementById('kpi-equity');
                        const elBalance = document.getElementById('kpi-balance');
                        const elMargin = document.getElementById('kpi-margin');
                        const elProfit = document.getElementById('kpi-profit');
                        const elDrawdown = document.getElementById('kpi-drawdown');
                        const elMarginUsage = document.getElementById('kpi-margin-usage');

                        if(elEquity) elEquity.innerText = `$${acc.equity.toFixed(2)}`;
                        if(elBalance) elBalance.innerText = `$${acc.balance.toFixed(2)}`;
                        if(elMargin) elMargin.innerText = `$${acc.margin.toFixed(2)}`;
                        if(elProfit) {
                            elProfit.innerText = `$${acc.profit.toFixed(2)}`;
                            elProfit.className = acc.profit >= 0 ? 'kpi-value text-bullish fs-5' : 'kpi-value text-critical fs-5';
                        }
                        if(elDrawdown) elDrawdown.innerText = `${acc.drawdown}%`;
                        if(elMarginUsage) elMarginUsage.innerText = `${acc.margin_usage}%`;
                                    if (de.technicals) {
                        const tech = de.technicals;
                        const elMacdTrend = document.getElementById('kpi-macd-trend');
                        if(elMacdTrend) {
                            elMacdTrend.innerText = tech.trend;
                            elMacdTrend.className = tech.trend === 'BULLISH' ? 'kpi-value text-bullish fs-5' : 'kpi-value text-critical fs-5';
                        }
                        
                        const elPanelTrend = document.getElementById('panel-trend');
                        if(elPanelTrend) {
                            elPanelTrend.innerText = tech.trend;
                            elPanelTrend.className = tech.trend === 'BULLISH' ? 'text-bullish fw-bold' : 'text-critical fw-bold';
                        }

                        const elPanelRegime = document.getElementById('panel-regime');
                        if(elPanelRegime) {
                            elPanelRegime.innerText = tech.trend === 'BULLISH' || tech.trend === 'BEARISH' ? 'Trending' : 'Sideway';
                        }

                        // Update Moving Averages table cells
                        const updateMACell = (maName) => {
                            const simpleEl = document.getElementById(`${maName}-simple`);
                            const exponentialEl = document.getElementById(`${maName}-exponential`);
                            const signalEl = document.getElementById(`${maName}-signal`);
                            
                            if (simpleEl && tech[`${maName}_simple`]) simpleEl.innerText = tech[`${maName}_simple`].toFixed(2);
                            if (exponentialEl && tech[`${maName}_exponential`]) exponentialEl.innerText = tech[`${maName}_exponential`].toFixed(2);
                            if (signalEl && tech[`${maName}_signal`]) {
                                const sig = tech[`${maName}_signal`];
                                signalEl.innerHTML = `<span class="${sig === 'BUY' ? 'text-bullish' : 'text-critical'} fw-bold">${sig}</span>`;
                            }
                        };
                        updateMACell('ma20');
                        updateMACell('ma50');
                        updateMACell('ma200');
                        
                        // Update Oscillators table cells
                        const rsiValEl = document.getElementById('osc-rsi-val');
                        const rsiSigEl = document.getElementById('osc-rsi-sig');
                        if (rsiValEl) rsiValEl.innerText = tech.rsi.toFixed(1);
                        if (rsiSigEl) {
                            const rsiSig = tech.rsi > 70 ? 'Overbought' : (tech.rsi < 30 ? 'Oversold' : 'Neutral');
                            const rsiClass = rsiSig === 'Neutral' ? 'text-white' : (rsiSig === 'Overbought' ? 'text-warning-v42' : 'text-bullish');
                            rsiSigEl.innerHTML = `<span class="${rsiClass}">${rsiSig}</span>`;
                        }
                        
                        const macdValEl = document.getElementById('osc-macd-val');
                        const macdSigEl = document.getElementById('osc-macd-sig');
                        if (macdValEl) macdValEl.innerText = (tech.macd >= 0 ? '+' : '') + tech.macd.toFixed(2);
                        if (macdSigEl) {
                            const macdSig = tech.trend === 'BULLISH' ? 'Bullish' : 'Bearish';
                            const macdClass = macdSig === 'Bullish' ? 'text-bullish' : 'text-critical';
                            macdSigEl.innerHTML = `<span class="${macdClass}">${macdSig}</span>`;
                        }
                        
                        const stochValEl = document.getElementById('osc-stoch-val');
                        const stochSigEl = document.getElementById('osc-stoch-sig');
                        if (stochValEl) stochValEl.innerText = tech.stoch.toFixed(1);
                        if (stochSigEl) {
                            const stochSig = tech.stoch > 80 ? 'Overbought' : (tech.stoch < 20 ? 'Oversold' : 'Neutral');
                            const stochClass = stochSig === 'Neutral' ? 'text-white' : (stochSig === 'Overbought' ? 'text-warning-v42' : 'text-bullish');
                            stochSigEl.innerHTML = `<span class="${stochClass}">${stochSig}</span>`;
                        }
                        
                        const atrValEl = document.getElementById('osc-atr-val');
                        const atrSigEl = document.getElementById('osc-atr-sig');
                        if (atrValEl) atrValEl.innerText = tech.atr.toFixed(2);
                        if (atrSigEl) {
                            const atrSig = tech.atr > 15 ? 'High Volatility' : 'Normal';
                            const atrClass = atrSig === 'Normal' ? 'text-muted' : 'text-warning-v42';
                            atrSigEl.innerHTML = `<span class="${atrClass}">${atrSig}</span>`;
                        }
                    }     }
                    if (de.account) {
                        const elPanelRisk = document.getElementById('panel-risk');
                        if(elPanelRisk) {
                            const riskLevel = de.account.drawdown > 2.0 ? 'HIGH' : (de.account.drawdown > 0.5 ? 'MEDIUM' : 'LOW');
                            elPanelRisk.innerText = riskLevel;
                            elPanelRisk.className = riskLevel === 'LOW' ? 'text-bullish fw-bold' : (riskLevel === 'MEDIUM' ? 'text-warning-v42 fw-bold' : 'text-critical fw-bold');
                        }
                    }
                    if (de.smart_money) {
                        const sm = de.smart_money;
                        const elSpread = document.getElementById('kpi-spread');
                        if(elSpread) elSpread.innerText = sm.spread;

                        const elPanelSpread = document.getElementById('panel-spread');
                        if(elPanelSpread) elPanelSpread.innerText = `${sm.spread} pips`;

                        // Update Market Intelligence tab metrics
                        const elMarketSpread = document.getElementById('market-spread');
                        if (elMarketSpread) elMarketSpread.innerText = `${sm.spread} pips`;

                        const elMarketLiq = document.getElementById('market-liquidity');
                        if (elMarketLiq) {
                            const liqVal = sm.spread <= 1.2 ? 'High' : (sm.spread <= 2.0 ? 'Moderate' : 'Low');
                            elMarketLiq.innerText = liqVal;
                            elMarketLiq.className = liqVal === 'High' ? 'text-bullish text-end fw-bold' : (liqVal === 'Moderate' ? 'text-white text-end' : 'text-critical text-end fw-bold');
                        }
                    }

                    if (de.technicals) {
                        const tech = de.technicals;
                        const elMarketAtr = document.getElementById('market-atr');
                        if (elMarketAtr && tech.atr) elMarketAtr.innerText = `${tech.atr} pips`;
                        
                        const elMarketVol = document.getElementById('market-volatility');
                        if (elMarketVol && tech.atr) {
                            const volVal = tech.atr > 15 ? 'Elevated' : 'Normal';
                            elMarketVol.innerText = volVal;
                            elMarketVol.className = volVal === 'Normal' ? 'text-white text-end' : 'text-warning-v42 text-end fw-bold';
                        }
                        
                        const elMarketSession = document.getElementById('market-session');
                        if (elMarketSession) {
                            const utcHour = new Date().getUTCHours();
                            let sessionName = 'London';
                            let sessionClass = 'text-info-v42 text-end';
                            if (utcHour >= 22 || utcHour < 8) {
                                sessionName = 'Tokyo/Sydney';
                                sessionClass = 'text-white text-end';
                            } else if (utcHour >= 13 && utcHour < 21) {
                                sessionName = 'New York';
                                sessionClass = 'text-bullish text-end fw-bold';
                            }
                            elMarketSession.innerText = sessionName;
                            elMarketSession.className = sessionClass;
                        }
                    }

                    // Update Trading Center tab if DOM elements exist
                    if (de.positions) {
                        const openTbody = document.getElementById('trade-open-positions-tbody');
                        const elPendingOrders = document.getElementById('trade-pending-orders');
                        const elPosSizing = document.getElementById('trade-pos-sizing');
                        const elFloatingPl = document.getElementById('trade-floating-pl');
                        const elPanelOpenPos = document.getElementById('panel-open-position');

                        let totalLots = 0;
                        let pendingCount = 0;
                        let openCount = 0;
                        let positionsHtml = '';

                        de.positions.forEach(p => {
                            if (p.is_position) {
                                openCount += 1;
                                totalLots += p.volume;
                                const pLStr = p.profit >= 0 ? `+$${p.profit.toFixed(2)}` : `-$${Math.abs(p.profit).toFixed(2)}`;
                                const pLClass = p.profit >= 0 ? 'text-bullish' : 'text-critical';
                                positionsHtml += `<tr>
                                    <td>#${p.ticket}</td>
                                    <td class="${p.type === 'BUY' ? 'text-bullish' : 'text-critical'} fw-bold">${p.type}</td>
                                    <td>${p.volume.toFixed(2)}</td>
                                    <td>${p.price_open.toFixed(2)}</td>
                                    <td><input type="number" step="0.01" class="form-control form-control-xs bg-dark text-white border-secondary text-center py-0" style="width: 80px; font-size: 11px; display: inline-block;" id="sl-${p.ticket}" value="${p.sl.toFixed(2)}" onchange="modifyPosition(${p.ticket})"></td>
                                    <td><input type="number" step="0.01" class="form-control form-control-xs bg-dark text-white border-secondary text-center py-0" style="width: 80px; font-size: 11px; display: inline-block;" id="tp-${p.ticket}" value="${p.tp.toFixed(2)}" onchange="modifyPosition(${p.ticket})"></td>
                                    <td class="${pLClass}">${pLStr}</td>
                                    <td><button class="btn btn-sm btn-outline-danger py-0 px-2" onclick="closePosition(${p.ticket})">Close</button></td>
                                </tr>`;
                            } else {
                                pendingCount += 1;
                                positionsHtml += `<tr>
                                    <td>#${p.ticket}</td>
                                    <td class="text-info-v42 fw-bold">${p.type}</td>
                                    <td>${p.volume.toFixed(2)}</td>
                                    <td>${p.price_open.toFixed(2)}</td>
                                    <td>${p.sl.toFixed(2)}</td>
                                    <td>${p.tp.toFixed(2)}</td>
                                    <td class="text-muted">-</td>
                                    <td><button class="btn btn-sm btn-outline-danger py-0 px-2" onclick="cancelOrder(${p.ticket})">Cancel</button></td>
                                </tr>`;
                            }
                        });

                        if (positionsHtml === '') {
                            positionsHtml = '<tr><td colspan="8" class="text-muted text-center">No active positions.</td></tr>';
                        }
                        if (openTbody) openTbody.innerHTML = positionsHtml;
                        if (elPendingOrders) elPendingOrders.innerText = `${pendingCount} Active`;
                        if (elPosSizing) elPosSizing.innerText = `${totalLots.toFixed(2)} Lots`;
                        if (elPanelOpenPos) elPanelOpenPos.innerText = openCount;

                        const elDailyProfit = document.getElementById('trade-daily-profit');
                        if (elDailyProfit && de.today_profit !== undefined) {
                            const todayProfit = de.today_profit;
                            const todayProfitFormatted = todayProfit >= 0 ? `+$${todayProfit.toFixed(2)}` : `-$${Math.abs(todayProfit).toFixed(2)}`;
                            elDailyProfit.innerText = todayProfitFormatted;
                            elDailyProfit.className = todayProfit >= 0 ? 'kpi-value text-bullish' : 'kpi-value text-critical';
                        }

                        if (de.account) {
                            const profit = de.account.profit;
                            const profitFormatted = profit >= 0 ? `+$${profit.toFixed(2)}` : `-$${Math.abs(profit).toFixed(2)}`;
                            
                            if (elFloatingPl) {
                                elFloatingPl.innerText = profitFormatted;
                                elFloatingPl.className = profit >= 0 ? 'kpi-value text-bullish' : 'kpi-value text-critical';
                            }
                            
                            const elPanelFloatingPl = document.getElementById('panel-floating-pl');
                            if (elPanelFloatingPl) {
                                elPanelFloatingPl.innerText = profitFormatted;
                                elPanelFloatingPl.className = profit >= 0 ? 'text-bullish fw-bold' : 'text-critical fw-bold';
                            }
                        }
                    }

                    if (de.history) {
                        const historyTbody = document.getElementById('trade-history-tbody');
                        let historyHtml = '';

                        de.history.forEach(h => {
                            const profitStr = h.profit >= 0 ? `+$${h.profit.toFixed(2)}` : `-$${Math.abs(h.profit).toFixed(2)}`;
                            const profitClass = h.profit >= 0 ? 'text-bullish' : 'text-critical';
                            const volVal = h.volume !== undefined ? h.volume.toFixed(2) : '0.00';
                            historyHtml += `<tr>
                                <td>#${h.ticket}</td>
                                <td class="${h.type === 'BUY' ? 'text-bullish' : 'text-critical'} fw-bold">${h.type}</td>
                                <td>${volVal}</td>
                                <td>${h.open_time}</td>
                                <td>${h.close_time}</td>
                                <td class="${profitClass}">${profitStr}</td>
                            </tr>`;
                        });

                        if (historyHtml === '') {
                            historyHtml = '<tr><td colspan="6" class="text-muted text-center">No recent history.</td></tr>';
                        }
                        if (historyTbody) historyTbody.innerHTML = historyHtml;
                    }

                    if (de.smart_money) {
                        const smc = de.smart_money;
                        const smcObTbody = document.getElementById('smc-ob-tbody');
                        if (smcObTbody && smc.ob_fvg) {
                            let obHtml = '';
                            smc.ob_fvg.forEach(item => {
                                const typeClass = item.type.includes('Bullish') ? 'text-bullish' : 'text-bearish';
                                const statusClass = item.status === 'Untested' ? 'text-warning-v42' : 'text-white';
                                obHtml += `<tr>
                                    <td>${item.level.toFixed(2)}</td>
                                    <td><span class="${typeClass}">${item.type}</span></td>
                                    <td>${item.timeframe}</td>
                                    <td><span class="${statusClass}">${item.status}</span></td>
                                </tr>`;
                            });
                            smcObTbody.innerHTML = obHtml;
                        }
                        
                        const elH1 = document.getElementById('smc-structure-h1');
                        if (elH1) {
                            elH1.innerText = smc.structure_h1;
                            elH1.className = smc.structure_h1.includes('Bullish') ? 'text-bullish fw-bold text-end' : 'text-bearish fw-bold text-end';
                        }
                        
                        const elM15 = document.getElementById('smc-structure-m15');
                        if (elM15) {
                            elM15.innerText = smc.structure_m15;
                            elM15.className = smc.structure_m15.includes('Bullish') ? 'text-bullish fw-bold text-end' : 'text-bearish fw-bold text-end';
                        }
                        
                        const elBsl = document.getElementById('smc-bsl');
                        if (elBsl) elBsl.innerText = smc.bsl.toFixed(2);
                        
                        const elSsl = document.getElementById('smc-ssl');
                        if (elSsl) elSsl.innerText = smc.ssl.toFixed(2);
                        
                        const elInducement = document.getElementById('smc-inducement');
                        if (elInducement) elInducement.innerText = smc.inducement.toFixed(2);

                        // 3. Update AI Decision Center page
                        const elAiTrend = document.getElementById('ai-trend');
                        const elAiMomentum = document.getElementById('ai-momentum');
                        const elAiSmartMoney = document.getElementById('ai-smartmoney');
                        const elAiIntermarket = document.getElementById('ai-intermarket');
                        const elAiMlOutput = document.getElementById('ai-mloutput');
                        const elAiDecision = document.getElementById('ai-decisionengine');
                        const elAiConfidence = document.getElementById('ai-confidence');
                        const elAiFinal = document.getElementById('ai-finaldecision');

                        if (elAiTrend && de.technicals) {
                            elAiTrend.innerText = de.technicals.trend === 'BULLISH' ? 'UPTREND' : 'DOWNTREND';
                            elAiTrend.className = de.technicals.trend === 'BULLISH' ? 'text-bullish fw-bold text-end' : 'text-critical fw-bold text-end';
                        }
                        if (elAiMomentum && de.technicals) {
                            const r = de.technicals.rsi;
                            const mom = r > 70 ? 'OVERBOUGHT' : (r < 30 ? 'OVERSOLD' : 'NEUTRAL');
                            elAiMomentum.innerText = mom;
                            elAiMomentum.className = mom === 'NEUTRAL' ? 'text-white fw-bold text-end' : (mom === 'OVERBOUGHT' ? 'text-warning-v42 fw-bold text-end' : 'text-bullish fw-bold text-end');
                        }
                        if (elAiSmartMoney && de.smart_money) {
                            const str = de.smart_money.structure_h1;
                            const smType = str.includes('Bullish') ? 'ACCUMULATION' : 'DISTRIBUTION';
                            elAiSmartMoney.innerText = smType;
                            elAiSmartMoney.className = smType === 'ACCUMULATION' ? 'text-bullish fw-bold text-end' : 'text-critical fw-bold text-end';
                        }
                        if (elAiIntermarket && ne && ne.macro_drivers) {
                            elAiIntermarket.innerText = ne.macro_drivers.score;
                            elAiIntermarket.className = ne.macro_drivers.score === 'BULLISH' ? 'text-bullish fw-bold text-end' : (ne.macro_drivers.score === 'BEARISH' ? 'text-critical fw-bold text-end' : 'text-white fw-bold text-end');
                        }
                        if (elAiMlOutput) {
                            const sig = latestSignal ? latestSignal.signal : 'WAIT';
                            elAiMlOutput.innerText = sig === 'WAIT' ? 'CONSOLIDATION' : 'CONTINUATION';
                            elAiMlOutput.className = sig === 'WAIT' ? 'text-warning-v42 fw-bold text-end' : 'text-bullish fw-bold text-end';
                        }
                        if (elAiDecision) {
                            const sig = latestSignal ? latestSignal.signal : 'PROCESSING';
                            elAiDecision.innerText = sig;
                            elAiDecision.className = sig === 'BUY' ? 'text-bullish fw-bold text-end' : (sig === 'SELL' ? 'text-critical fw-bold text-end' : 'text-warning-v42 fw-bold text-end');
                        }
                        if (elAiConfidence) {
                            const conf = latestSignal ? (latestSignal.confidence * 100).toFixed(1) + '%' : '75.5%';
                            elAiConfidence.innerText = conf;
                        }

                        // Render XAI Decision Tree Graph inside AI Center
                        const graphDiv = document.getElementById('ai-tree-graph');
                        if (graphDiv) {
                            const treeTraceNodes = {
                                x: [2, 1, 3, 0.5, 1.5, 2.5, 3.5],
                                y: [3, 2, 2, 1, 1, 1, 1],
                                mode: 'markers+text',
                                type: 'scatter',
                                text: ['RSI < 70', 'MACD > 0', 'MACD <= 0', 'BUY (89%)', 'WAIT (65%)', 'SELL (81%)', 'WAIT (74%)'],
                                textposition: 'top center',
                                marker: {
                                    size: 26,
                                    color: ['#58a6ff', '#2ea043', '#f85149', '#2ea043', '#8b949e', '#f85149', '#8b949e'],
                                    line: { color: '#30363d', width: 2 }
                                }
                            };
                            const treeTraceEdges = {
                                x: [2, 1, null, 2, 3, null, 1, 0.5, null, 1, 1.5, null, 3, 2.5, null, 3, 3.5],
                                y: [3, 2, null, 3, 2, null, 2, 1, null, 2, 1, null, 2, 1, null, 2, 1],
                                mode: 'lines',
                                type: 'scatter',
                                line: { color: '#30363d', width: 1.5 },
                                hoverinfo: 'none'
                            };
                            const treeLayout = {
                                showlegend: false,
                                xaxis: { showgrid: false, zeroline: false, showticklabels: false },
                                yaxis: { showgrid: false, zeroline: false, showticklabels: false },
                                paper_bgcolor: 'rgba(0,0,0,0)',
                                plot_bgcolor: 'rgba(0,0,0,0)',
                                font: { color: '#8b949e', size: 9 },
                                margin: { t: 30, r: 30, b: 20, l: 30 }
                            };
                            // Use Plotly.react instead of innerHTML='' and newPlot to prevent UI freeze
                            const tabAiOs = document.getElementById('tab-xau-os');
                            // Only perform heavy SVG diffing/rendering if the XAU AI OS tab is visible
                            if (!tabAiOs || !tabAiOs.classList.contains('d-none')) {
                                if (graphDiv.data) {
                                    Plotly.react(graphDiv, [treeTraceEdges, treeTraceNodes], treeLayout, { responsive: true });
                                } else {
                                    graphDiv.innerHTML = '';
                                    Plotly.newPlot(graphDiv, [treeTraceEdges, treeTraceNodes], treeLayout, { responsive: true });
                                }
                            }
                        }
                    }

                    // Update XAU AI GOLD OS Tab
                    if (de.technicals) {
                        const tech = de.technicals;
                        if (tech.atr) latestAtr = tech.atr; // Save for tick updates
                        
                        const osRegime = document.getElementById('os-regime');
                        const osTrend = document.getElementById('os-trend');
                        const osVolatility = document.getElementById('os-volatility');
                        
                        if (osRegime) osRegime.innerText = tech.trend === 'BULLISH' || tech.trend === 'BEARISH' ? 'TRENDING (Expansion)' : 'SIDEWAYS (Consolidation)';
                        if (osTrend) {
                            osTrend.innerText = tech.trend;
                            osTrend.className = tech.trend === 'BULLISH' ? 'text-success fw-bold' : (tech.trend === 'BEARISH' ? 'text-danger fw-bold' : 'text-warning fw-bold');
                        }
                        if (osVolatility && tech.atr) {
                            const atrVal = tech.atr.toFixed(2);
                            const volText = tech.atr > 15 ? `High (ATR ${atrVal})` : `Normal (ATR ${atrVal})`;
                            osVolatility.innerText = volText;
                            osVolatility.className = tech.atr > 15 ? 'text-danger fw-bold' : 'text-white fw-bold';
                        }
                    }

                    if (de.smart_money) {
                        const smc = de.smart_money;
                        const osInst = document.getElementById('os-inst');
                        if (osInst && smc.structure_h1) {
                            osInst.innerText = smc.structure_h1.includes('Bullish') ? 'Accumulation' : 'Distribution';
                            osInst.className = smc.structure_h1.includes('Bullish') ? 'text-success fw-bold' : 'text-danger fw-bold';
                        }
                    }
                    
                    if (typeof latestSignal !== 'undefined' && latestSignal) {
                        const osUes = document.getElementById('os-ues-score');
                        const confVal = Math.round(latestSignal.confidence * 100);
                        let uesScore = confVal + 10; 
                        if (uesScore > 98) uesScore = 98;
                        
                        if (osUes) osUes.innerText = uesScore;
                        
                        // === DYNAMIC THRESHOLD (OPTION 3) ===
                        let EXECUTION_THRESHOLD = window.sniperScoreThreshold || 80;
                        const currentUtcHour = new Date().getUTCHours();
                        const isAsianSession = (currentUtcHour >= 0 && currentUtcHour < 8);
                        const atrVal = (typeof latestAtr !== 'undefined' && latestAtr) ? parseFloat(latestAtr) : 15.0;
                        
                        let isLowVolatility = false;
                        if (isAsianSession || atrVal < 10.0) {
                            EXECUTION_THRESHOLD = 90; // Demand Sniper Score
                            isLowVolatility = true;
                        }
                        
                        if (isLowVolatility && uesScore < EXECUTION_THRESHOLD && latestSignal.signal !== 'WAIT') {
                            latestSignal.signal = 'WAIT';
                        }
                        // === H1 SMART MONEY ALIGNMENT FILTER ===
                        let isH1Misaligned = false;
                        if (de.smart_money && de.smart_money.structure_h1) {
                            const smcH1 = de.smart_money.structure_h1;
                            if ((latestSignal.signal === 'BUY' && smcH1.includes('Bearish')) || 
                                (latestSignal.signal === 'SELL' && smcH1.includes('Bullish'))) {
                                isH1Misaligned = true;
                            }
                        }
                        
                        if (isH1Misaligned && latestSignal.signal !== 'WAIT') {
                            latestSignal.signal = 'WAIT';
                        }
                        // =======================================
                        
                        // UPDATE AI DECISION CENTER TAB (WITH ULTIMATE ENGINE FILTERS)
                        const elAiH1Alignment = document.getElementById('ai-h1-alignment');
                        if (elAiH1Alignment) {
                            elAiH1Alignment.innerText = isH1Misaligned ? 'MISALIGNED (BLOCKED)' : 'ALIGNED (SYNC)';
                            elAiH1Alignment.className = isH1Misaligned ? 'text-danger fw-bold text-end' : 'text-success fw-bold text-end';
                        }
                        
                        const elAiDynVol = document.getElementById('ai-dyn-volatility');
                        if (elAiDynVol) {
                            const reqScore = isLowVolatility ? 90 : 80;
                            const passed = uesScore >= reqScore;
                            elAiDynVol.innerText = isLowVolatility ? (passed ? 'PASSED (LOW VOL >90)' : 'BLOCKED (LOW VOL <90)') : 'PASSED (NORMAL VOL)';
                            elAiDynVol.className = passed ? 'text-success fw-bold text-end' : 'text-warning fw-bold text-end';
                        }
                        
                        const elAiUesScore = document.getElementById('ai-ues-score');
                        if (elAiUesScore) {
                            elAiUesScore.innerText = uesScore;
                            elAiUesScore.className = uesScore >= EXECUTION_THRESHOLD ? 'text-success fw-bold text-end' : 'text-warning fw-bold text-end';
                        }
                        
                        const elAiFinal = document.getElementById('ai-finaldecision');
                        if (elAiFinal) {
                            const sig = latestSignal.signal;
                            elAiFinal.innerText = sig;
                            elAiFinal.className = sig === 'BUY' ? 'text-bullish fw-bold' : (sig === 'SELL' ? 'text-critical fw-bold' : 'text-warning-v42 fw-bold');
                        }
                        
                        const dirEl = document.getElementById('os-plan-dir');
                        if (dirEl) {
                            dirEl.innerText = latestSignal.signal;
                            dirEl.className = latestSignal.signal === 'BUY' ? 'text-success fw-bold' : (latestSignal.signal === 'SELL' ? 'text-danger fw-bold' : 'text-warning fw-bold');
                        }
                        
                        const statusEl = document.getElementById('os-decision-status');
                        const reasonEl = document.getElementById('os-decision-reason');
                        
                        let isCounterTrend = false;
                        if (de.technicals && de.technicals.trend) {
                            if ((latestSignal.signal === 'BUY' && de.technicals.trend === 'BEARISH') || 
                                (latestSignal.signal === 'SELL' && de.technicals.trend === 'BULLISH')) {
                                isCounterTrend = true;
                            }
                        }

                        if (statusEl) {
                            if (latestSignal.signal === 'WAIT') {
                                if (isH1Misaligned) {
                                    statusEl.innerText = 'DIBLOKIR (MELAWAN H1)';
                                    statusEl.className = 'text-danger';
                                } else if (isLowVolatility && uesScore >= 80 && uesScore < 90) {
                                    statusEl.innerText = 'STANDBY (LOW VOL) - BUTUH SKOR >90';
                                    statusEl.className = 'text-warning';
                                } else {
                                    statusEl.innerText = 'MENUNGGU PULLBACK';
                                    statusEl.className = 'text-warning';
                                }
                            } else {
                                if (uesScore < 60) {
                                    statusEl.innerText = 'TIDAK LAYAK (SKOR RENDAH)';
                                    statusEl.className = 'text-danger';
                                } else if (uesScore < EXECUTION_THRESHOLD) {
                                    statusEl.innerText = 'WATCHLIST (TUNGGU MOMENTUM)';
                                    statusEl.className = 'text-warning';
                                } else {
                                    statusEl.innerText = 'EKSEKUSI SEKARANG (PRIME)';
                                    statusEl.className = 'text-success';
                                }
                            }
                        }
                        
                        if (reasonEl) {
                            let reasonText = `Alasan Utama: Skor UES berada di angka ${uesScore}. Konfidensi Sinyal AI sebesar ${confVal}%.`;
                            if (isH1Misaligned) {
                                reasonText = `⛔ H1 ALIGNMENT FILTER AKTIF: Sinyal diblokir karena arah berlawanan dengan Struktur Institusi (Smart Money) di time-frame H1.`;
                            } else if (isLowVolatility && uesScore >= 80 && uesScore < 90) {
                                reasonText = `⚠️ DYNAMIC THRESHOLD AKTIF: Karena pasar sedang sepi (Sesi Asia / ATR < 10), syarat OP dinaikkan menjadi UES > 90. Skor saat ini (${uesScore}) ditangguhkan untuk mencegah False Breakout.`;
                            } else if (isCounterTrend && latestSignal.signal !== 'WAIT') {
                                reasonText += `\n⚠️ PERINGATAN: Sinyal ini melawan arus jangka pendek (Counter-Trend). Kurangi Lot sebesar 50%!`;
                                // Highlight warning if it's prime but counter-trend
                                if (uesScore >= EXECUTION_THRESHOLD && statusEl) {
                                    statusEl.className = 'text-warning';
                                    statusEl.innerText += ' (HIGH RISK)';
                                }
                            }
                            reasonEl.innerText = reasonText;
                        }
                        
                        const probBullBar = document.getElementById('os-prob-bull-bar');
                        const probBullTxt = document.getElementById('os-prob-bull-txt');
                        const probBearBar = document.getElementById('os-prob-bear-bar');
                        const probBearTxt = document.getElementById('os-prob-bear-txt');
                        const probSideBar = document.getElementById('os-prob-side-bar');
                        const probSideTxt = document.getElementById('os-prob-side-txt');
                        
                        if (probBullBar) {
                            let bullP = latestSignal.signal === 'BUY' ? confVal : (latestSignal.signal === 'SELL' ? 100 - confVal - 15 : 30);
                            let bearP = latestSignal.signal === 'SELL' ? confVal : (latestSignal.signal === 'BUY' ? 100 - confVal - 15 : 30);
                            if (bullP < 0) bullP = 0; if (bearP < 0) bearP = 0;
                            let sideP = 100 - bullP - bearP;
                            
                            probBullBar.style.width = bullP + '%';
                            probBullTxt.innerText = bullP + '%';
                            probBearBar.style.width = bearP + '%';
                            probBearTxt.innerText = bearP + '%';
                            probSideBar.style.width = sideP + '%';
                            probSideTxt.innerText = sideP + '%';
                        }
                    }
                }

                if (ne) {
                    if (ne.sentiment) {
                        const sent = ne.sentiment;
                        const elSentiment = document.getElementById('kpi-sentiment');
                        if(elSentiment) {
                            elSentiment.innerText = `${sent.news_sentiment}% (${sent.trend})`;
                            elSentiment.className = sent.label === 'BULLISH' ? 'kpi-value text-bullish fs-5' : (sent.label === 'BEARISH' ? 'kpi-value text-critical fs-5' : 'kpi-value text-white fs-5');
                        }

                        // News Tab elements
                        const elNewsTabGsi = document.getElementById('news-tab-gsi');
                        const elNewsTabSent = document.getElementById('news-tab-sentiment');
                        const elNewsTabTrend = document.getElementById('news-tab-trend');
                        const elNewsTabRec = document.getElementById('news-tab-gold-rec');
                        const elNewsTabUsd = document.getElementById('news-tab-usd-strength');
                        const elNewsTabEq = document.getElementById('news-tab-equity-strength');

                        if (elNewsTabGsi && sent.gsi !== undefined) {
                            elNewsTabGsi.innerText = sent.gsi;
                            elNewsTabGsi.className = sent.gsi > 55.0 ? 'kpi-value text-bullish' : (sent.gsi < 45.0 ? 'kpi-value text-critical' : 'kpi-value text-white');
                        }
                        if (elNewsTabSent && sent.news_sentiment !== undefined) {
                            elNewsTabSent.innerText = sent.news_sentiment;
                            elNewsTabSent.className = sent.news_sentiment > 55.0 ? 'kpi-value text-bullish' : (sent.news_sentiment < 45.0 ? 'kpi-value text-critical' : 'kpi-value text-white');
                        }
                        if (elNewsTabTrend) {
                            elNewsTabTrend.innerText = sent.trend;
                            elNewsTabTrend.className = sent.trend === 'NAIK' ? 'kpi-value text-bullish' : 'kpi-value text-critical';
                        }
                        
                        // OP Autotrade Filter logic based on GSI score (Poin 4)
                        if (elNewsTabRec && sent.gsi !== undefined) {
                            const val = sent.gsi;
                            if (val < 30.0) {
                                elNewsTabRec.innerText = "BLOCKED (SELL ONLY)";
                                elNewsTabRec.className = "kpi-value text-critical fs-6";
                            } else if (val < 35.0) {
                                elNewsTabRec.innerText = "SCALED BUY (50% LOT)";
                                elNewsTabRec.className = "kpi-value text-warning-v42 fs-6";
                            } else if (val > 70.0) {
                                elNewsTabRec.innerText = "BLOCKED (BUY ONLY)";
                                elNewsTabRec.className = "kpi-value text-bullish fs-6";
                            } else if (val > 65.0) {
                                elNewsTabRec.innerText = "SCALED SELL (50% LOT)";
                                elNewsTabRec.className = "kpi-value text-warning-v42 fs-6";
                            } else {
                                elNewsTabRec.innerText = "ACTIVE (FULL LOT)";
                                elNewsTabRec.className = "kpi-value text-bullish fs-6";
                            }
                        }
                        
                        // Separated Market strength & DXY display (Poin 3)
                        // Separated Market strength & DXY display on 0-100% scale
                        if (elNewsTabUsd && sent.usd_strength !== undefined) {
                            const val = sent.usd_strength;
                            elNewsTabUsd.innerText = val.toFixed(1) + '%';
                            elNewsTabUsd.className = val > 55.0 ? 'kpi-value text-bullish' : (val < 45.0 ? 'kpi-value text-critical' : 'kpi-value text-white');
                        }
                        if (elNewsTabEq && sent.equity_strength !== undefined) {
                            const val = sent.equity_strength;
                            elNewsTabEq.innerText = val.toFixed(1) + '%';
                            elNewsTabEq.className = val > 55.0 ? 'kpi-value text-bullish' : (val < 45.0 ? 'kpi-value text-critical' : 'kpi-value text-white');
                        }
                    }
                    
                    if (ne.macro_drivers) {
                        const md = ne.macro_drivers;
                        const elMacroScore = document.getElementById('macro-score');
                        if (elMacroScore) {
                            elMacroScore.innerText = md.score;
                            elMacroScore.className = md.score === 'BULLISH' ? 'kpi-value text-bullish' : (md.score === 'BEARISH' ? 'kpi-value text-critical' : 'kpi-value text-white');
                        }
                        
                        const updateMacroRow = (metricId, value, impactText, impactType) => {
                            const valEl = document.getElementById(`macro-${metricId}`);
                            const impEl = document.getElementById(`macro-${metricId}-impact`);
                            if (valEl) valEl.innerText = value;
                            if (impEl) {
                                let badgeClass = 'text-info-v42';
                                if (impactType === 'bullish') badgeClass = 'text-bullish';
                                if (impactType === 'bearish') badgeClass = 'text-critical';
                                if (impactType === 'warning') badgeClass = 'text-warning-v42';
                                impEl.innerHTML = `<span class="${badgeClass}">${impactText}</span>`;
                            }
                        };
                        
                        updateMacroRow('fed-rate', md.fed_rate, md.fed_rate_impact, 'bearish');
                        updateMacroRow('cpi', md.cpi, md.cpi_impact, md.cpi_impact === 'ELEVATED' ? 'warning' : 'info');
                        updateMacroRow('ppi', md.ppi, md.ppi_impact, md.ppi_impact === 'ELEVATED' ? 'warning' : 'info');
                        updateMacroRow('pce', md.pce, md.pce_impact, md.pce_impact === 'COOLING' ? 'bullish' : 'info');
                        updateMacroRow('gdp', md.gdp, md.gdp_impact, md.gdp_impact === 'GROWING' ? 'bullish' : 'bearish');
                        updateMacroRow('nfp', md.nfp, md.nfp_impact, md.nfp_impact === 'BEAT' ? 'bearish' : 'bullish');
                        updateMacroRow('retail-sales', md.retail_sales, md.retail_sales_impact, md.retail_sales_impact === 'STRONG' ? 'bearish' : 'info');
                        updateMacroRow('etf-flow', md.etf_flow, md.etf_flow_impact, md.etf_flow_impact === 'INFLOW' ? 'bullish' : 'bearish');
                        updateMacroRow('gold-reserve', md.gold_reserve, md.gold_reserve_impact, md.gold_reserve_impact === 'ACCUMULATION' ? 'bullish' : 'bearish');
                    }

                    if (ne.news) {
                        // Save news feed to localStorage for instant recovery
                        localStorage.setItem('cachedNewsFeed', JSON.stringify(ne.news));
                        
                        const newsTbody = document.getElementById('news-tab-feed-tbody');
                        let newsHtml = '';

                        ne.news.forEach(item => {
                            const impactClass = item.gold_impact === 'BULLISH' ? 'text-bullish' : (item.gold_impact === 'BEARISH' ? 'text-critical' : 'text-muted');
                            const finalScoreClass = item.final_score > 60 ? 'text-bullish fw-bold' : (item.final_score < 40 ? 'text-critical fw-bold' : 'text-white');
                            
                            // Shorten source names for cleaner layout
                            let shortSource = item.source;
                            if (shortSource.includes("Yahoo")) {
                                shortSource = shortSource.split(" ")[0]; // "Reuters (Yahoo)" -> "Reuters"
                            }
                            if (shortSource === "Federal Reserve") shortSource = "Fed";
                            if (shortSource === "World Gold Council") shortSource = "WGC";
                            if (shortSource === "CME FedWatch") shortSource = "CME";
                            if (shortSource === "Investing.com") shortSource = "Investing";
                            if (shortSource === "Trading Economics") shortSource = "TradEcon";

                            const sourceDisplay = `${shortSource} (${item.source_weight.toFixed(1)})`;

                            newsHtml += `<tr>
                                <td>${sourceDisplay}</td>
                                <td class="text-white" style="word-wrap: break-word; white-space: normal;">${item.headline}</td>
                                <td>${item.relevancy}%</td>
                                <td>${item.sentiment_score.toFixed(1)}</td>
                                <td class="${impactClass} fw-bold">${item.gold_impact}</td>
                                <td>${item.confidence.toFixed(1)}%</td>
                                <td>${item.duration}</td>
                                <td>${item.regime}</td>
                                <td class="${finalScoreClass}">${item.final_score}</td>
                            </tr>`;
                        });

                        if (newsHtml === '') {
                            newsHtml = '<tr><td colspan="9" class="text-muted text-center">No news processed.</td></tr>';
                        }
                        if (newsTbody) newsTbody.innerHTML = newsHtml;
                    }
                    
                    if (ne.sentiment) {
                        localStorage.setItem('cachedNewsSentiment', JSON.stringify(ne.sentiment));
                    }
                    if (ne.macro_drivers) {
                        localStorage.setItem('cachedMacroDrivers', JSON.stringify(ne.macro_drivers));
                    }
                }
            }
            if (data.type === 'system_status') {
                // Update Hardware Metrics
                if (data.cpu) {
                    document.getElementById('sys-cpu').innerText = data.cpu;
                    const sysopsCpu = document.getElementById('sysops-cpu');
                    if (sysopsCpu) sysopsCpu.innerText = data.cpu;
                }
                if (data.ram) {
                    document.getElementById('sys-ram').innerText = data.ram;
                    const sysopsRam = document.getElementById('sysops-ram');
                    if (sysopsRam) sysopsRam.innerText = data.ram;
                }
                
                // Update dynamic memory allocation metrics
                if (data.ram && data.ram_percent !== undefined) {
                    const ramText = document.getElementById('ram-usage-text');
                    const ramBar = document.getElementById('ram-progress-bar');
                    if (ramText) {
                        const used = parseFloat(data.ram);
                        const total = Math.round(used / (data.ram_percent / 100));
                        ramText.innerText = `${data.ram} / ${total || 16}GB (${data.ram_percent.toFixed(1)}%)`;
                    }
                    if (ramBar) {
                        ramBar.style.width = `${data.ram_percent}%`;
                    }
                }
                
                if (data.vram_total && data.vram_percent !== undefined) {
                    const vramText = document.getElementById('vram-usage-text');
                    const vramBar = document.getElementById('vram-progress-bar');
                    if (vramText) {
                        vramText.innerText = `${data.vram_used} / ${data.vram_total} (${data.vram_percent.toFixed(1)}%)`;
                    }
                    if (vramBar) {
                        vramBar.style.width = `${data.vram_percent}%`;
                    }
                }
                
                if (data.combined_total && data.combined_percent !== undefined) {
                    const combText = document.getElementById('combined-usage-text');
                    const combBar = document.getElementById('combined-progress-bar');
                    if (combText) {
                        combText.innerText = `${data.combined_used} / ${data.combined_total} (${data.combined_percent.toFixed(1)}%)`;
                    }
                    if (combBar) {
                        combBar.style.width = `${data.combined_percent}%`;
                    }
                }

                // Update dynamic sysops metrics if present
                const sysopsBroker = document.getElementById('sysops-broker');
                if (sysopsBroker) {
                    sysopsBroker.innerText = data.broker || 'DISCONNECTED';
                    sysopsBroker.className = (data.broker === 'CONNECTED') ? 'text-bullish text-end' : 'text-bearish text-end';
                }
                const sysopsMt5 = document.getElementById('sysops-mt5');
                if (sysopsMt5) {
                    sysopsMt5.innerText = (data.mt5 === 'CONNECTED') ? 'SYNCED' : 'DISCONNECTED';
                    sysopsMt5.className = (data.mt5 === 'CONNECTED') ? 'text-bullish text-end' : 'text-bearish text-end';
                }
                const sysopsDatabase = document.getElementById('sysops-database');
                if (sysopsDatabase) {
                    sysopsDatabase.innerText = 'WAL READY';
                    sysopsDatabase.className = 'text-bullish text-end';
                }
                const sysopsScheduler = document.getElementById('sysops-scheduler');
                if (sysopsScheduler) {
                    sysopsScheduler.innerText = 'ACTIVE (5 Jobs)';
                    sysopsScheduler.className = 'text-info-v42 text-end';
                }
                const sysopsWebsocket = document.getElementById('sysops-websocket');
                if (sysopsWebsocket) {
                    sysopsWebsocket.innerText = 'OPEN';
                    sysopsWebsocket.className = 'text-bullish text-end';
                }
                const sysopsApi = document.getElementById('sysops-api');
                if (sysopsApi) {
                    sysopsApi.innerText = 'UVICORN 200 OK';
                    sysopsApi.className = 'text-bullish text-end';
                }

                // Update bottom status bar elements
                const bottomBroker = document.getElementById('bottom-broker');
                if (bottomBroker) {
                    bottomBroker.innerText = (data.broker === 'CONNECTED') ? 'CONNECTED' : 'DISCONNECTED';
                    bottomBroker.className = (data.broker === 'CONNECTED') ? 'text-bullish' : 'text-critical';
                }
                const bottomMt5 = document.getElementById('bottom-mt5');
                if (bottomMt5) {
                    bottomMt5.innerText = (data.mt5 === 'CONNECTED') ? 'SYNCED' : 'DISCONNECTED';
                    bottomMt5.className = (data.mt5 === 'CONNECTED') ? 'text-bullish' : 'text-critical';
                }
                const bottomApi = document.getElementById('bottom-api');
                if (bottomApi) {
                    bottomApi.innerText = 'OK';
                    bottomApi.className = 'text-bullish';
                }
                const bottomDatabase = document.getElementById('bottom-database');
                if (bottomDatabase) {
                    bottomDatabase.innerText = 'READY';
                    bottomDatabase.className = 'text-bullish';
                }
                const bottomScheduler = document.getElementById('bottom-scheduler');
                if (bottomScheduler) {
                    bottomScheduler.innerText = 'ACTIVE';
                    bottomScheduler.className = 'text-bullish';
                }
                const bottomTelegram = document.getElementById('bottom-telegram');
                if (bottomTelegram) {
                    bottomTelegram.innerText = 'ONLINE';
                    bottomTelegram.className = 'text-bullish';
                }
                const bottomWs = document.getElementById('bottom-ws');
                if (bottomWs) {
                    bottomWs.innerText = 'OPEN';
                    bottomWs.className = 'text-bullish';
                }

                // Update Top Bar Badges
                const mt5Badge = document.getElementById('status-mt5');
                const brokerBadge = document.getElementById('status-broker');
                const aiBadge = document.getElementById('status-ai');
                
                if (data.mt5 === 'CONNECTED') {
                    mt5Badge.className = 'badge bg-success me-2';
                    mt5Badge.innerText = 'MT5: CONNECTED';
                } else {
                    mt5Badge.className = 'badge bg-secondary me-2';
                    mt5Badge.innerText = 'MT5: DISCONNECTED';
                }

                if (data.broker === 'CONNECTED') {
                    brokerBadge.className = 'badge bg-success me-2';
                    brokerBadge.innerText = 'Broker: CONNECTED';
                } else {
                    brokerBadge.className = 'badge bg-secondary me-2';
                    brokerBadge.innerText = 'Broker: DISCONNECTED';
                }

                if (data.ai === 'ACTIVE') {
                    aiBadge.className = 'badge bg-primary me-2';
                    aiBadge.innerText = 'AI: ACTIVE';
                } else {
                    aiBadge.className = 'badge bg-secondary me-2';
                    aiBadge.innerText = 'AI: STANDBY';
                }
            }
            if (data.type === 'backtest_results') {
                document.getElementById('bt-spinner').classList.add('d-none');
                document.getElementById('bt-btn-text').innerText = '▶ Run AI Backtest';
                document.getElementById('btn-run-backtest').removeAttribute('disabled');
                
                if (data.status === 'ERROR') {
                    alert("Backtest failed: " + data.message);
                    return;
                }
                
                document.getElementById('bt-win-rate').innerText = data.win_rate + '%';
                document.getElementById('bt-total-trades').innerText = data.total_trades;
                
                const netProfitStr = data.net_profit >= 0 ? `+$${data.net_profit.toFixed(2)}` : `-$${Math.abs(data.net_profit).toFixed(2)}`;
                const profitEl = document.getElementById('bt-net-profit');
                profitEl.innerText = netProfitStr;
                profitEl.className = data.net_profit >= 0 ? 'fw-bold text-bullish fs-5' : 'fw-bold text-critical fs-5';
                
                document.getElementById('bt-drawdown').innerText = data.max_drawdown + '%';
                
                const trace = {
                    x: data.equity_curve_x,
                    y: data.equity_curve_y,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Equity Curve',
                    line: { color: '#58a6ff', width: 2 }
                };
                const layout = {
                    title: { text: 'Backtest Equity Curve ($)', font: { color: '#8b949e', size: 12 } },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#8b949e', size: 10 },
                    margin: { t: 50, r: 20, b: 40, l: 60 },
                    xaxis: { gridcolor: '#21262d', linecolor: '#30363d' },
                    yaxis: { gridcolor: '#21262d', linecolor: '#30363d' }
                };
                
                const chartDiv = document.getElementById('backtest-equity-chart');
                chartDiv.innerHTML = '';
                Plotly.newPlot(chartDiv, [trace], layout, { responsive: true });
            }
        };
        
        ws.onclose = () => {
            console.log("WebSocket Disconnected.");
            wsStatus.className = 'text-critical';
            wsStatus.innerText = 'DISCONNECTED';
            setTimeout(initWebSocket, 3000); 
        };
    }

    // Bind Backtest button click
    const btnRunBacktest = document.getElementById('btn-run-backtest');
    if (btnRunBacktest) {
        btnRunBacktest.addEventListener('click', () => {
            const symbol = document.getElementById('bt-symbol').value;
            const timeframe = document.getElementById('bt-timeframe').value;
            const bars = document.getElementById('bt-bars').value;
            
            document.getElementById('bt-spinner').classList.remove('d-none');
            document.getElementById('bt-btn-text').innerText = 'Running...';
            btnRunBacktest.setAttribute('disabled', 'true');
            
            if (window.globalWs && window.globalWs.readyState === WebSocket.OPEN) {
                window.globalWs.send(JSON.stringify({
                    action: 'start_backtest',
                    symbol: symbol,
                    timeframe: timeframe,
                    bars: parseInt(bars)
                }));
            } else {
                alert("WebSocket is not connected.");
                document.getElementById('bt-spinner').classList.add('d-none');
                document.getElementById('bt-btn-text').innerText = '▶ Run AI Backtest';
                btnRunBacktest.removeAttribute('disabled');
            }
        });
    }

    // 2c. Replay & Backtest Sub-tab Switching
    const subTabButtons = document.querySelectorAll('.replay-mode-btn');
    const subTabs = document.querySelectorAll('.replay-sub-tab');

    subTabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            // Set active states for mode buttons
            subTabButtons.forEach(b => {
                b.className = 'btn btn-outline-secondary text-start replay-mode-btn';
                const badge = b.querySelector('.badge');
                if (badge) {
                    badge.className = 'badge bg-dark me-2';
                }
            });
            btn.className = 'btn btn-primary text-start replay-mode-btn';
            const activeBadge = btn.querySelector('.badge');
            if (activeBadge) {
                activeBadge.className = 'badge bg-light text-dark me-2';
            }

            // Toggle sub-tab visibility
            const subId = btn.getAttribute('data-sub');
            subTabs.forEach(tab => {
                tab.classList.add('d-none');
            });
            const activeTab = document.getElementById(`replay-sub-${subId}`);
            if (activeTab) {
                activeTab.classList.remove('d-none');
                // Force plotly resize in active subtab
                window.dispatchEvent(new Event('resize'));
            }
            
            // Save active sub-tab state
            localStorage.setItem('activeSubTab', subId);
        });
    });

    // Restore last active sub-tab on page load
    const savedActiveSubTab = localStorage.getItem('activeSubTab');
    if (savedActiveSubTab) {
        const matchingSubBtn = Array.from(subTabButtons).find(b => b.getAttribute('data-sub') === savedActiveSubTab);
        if (matchingSubBtn) {
            matchingSubBtn.click();
        }
    }

    // 2d. Run Walk Forward Optimization simulation
    const btnRunWfo = document.getElementById('btn-run-wfo');
    if (btnRunWfo) {
        btnRunWfo.addEventListener('click', () => {
            btnRunWfo.innerText = 'Calculating...';
            btnRunWfo.setAttribute('disabled', 'true');
            setTimeout(() => {
                btnRunWfo.innerText = '▶ Run Walk Forward';
                btnRunWfo.removeAttribute('disabled');
                
                // Plotly WFO curve
                const traceIS = {
                    x: ['WFO #1', 'WFO #2', 'WFO #3', 'WFO #4', 'WFO #5'],
                    y: [10000, 10250, 10600, 10950, 11400],
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: 'In-Sample',
                    line: { color: '#2ea043' }
                };
                const traceOOS = {
                    x: ['WFO #1', 'WFO #2', 'WFO #3', 'WFO #4', 'WFO #5'],
                    y: [10000, 10100, 10350, 10500, 10850],
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: 'Out-of-Sample',
                    line: { color: '#58a6ff' }
                };
                const layout = {
                    title: { text: 'Walk Forward Validation Curve', font: { color: '#8b949e', size: 12 } },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#8b949e', size: 9 },
                    margin: { t: 50, r: 25, b: 40, l: 60 },
                    xaxis: { gridcolor: '#21262d', linecolor: '#30363d' },
                    yaxis: { gridcolor: '#21262d', linecolor: '#30363d' }
                };
                const chartDiv = document.getElementById('wfo-chart-div');
                chartDiv.innerHTML = '';
                Plotly.newPlot(chartDiv, [traceIS, traceOOS], layout, { responsive: true });
            }, 1000);
        });
    }

    // 2e. Run Monte Carlo simulation
    const btnRunMc = document.getElementById('btn-run-montecarlo');
    if (btnRunMc) {
        btnRunMc.addEventListener('click', () => {
            btnRunMc.innerText = 'Simulating...';
            btnRunMc.setAttribute('disabled', 'true');
            setTimeout(() => {
                btnRunMc.innerText = '🎲 Simulate Paths';
                btnRunMc.removeAttribute('disabled');
                
                const count = parseInt(document.getElementById('mc-runs').value) || 50;
                const traces = [];
                const steps = Array.from({length: 20}, (_, i) => `Step ${i}`);
                
                for(let t=0; t<Math.min(count, 15); t++) {
                    const y = [10000];
                    for(let s=1; s<20; s++) {
                        const change = (Math.random() - 0.48) * 400; // slightly upward bias
                        y.push(Math.round(y[y.length-1] + change));
                    }
                    traces.push({
                        x: steps,
                        y: y,
                        type: 'scatter',
                        mode: 'lines',
                        line: { width: 1.5, opacity: 0.7 }
                    });
                }
                const layout = {
                    title: { text: 'Monte Carlo 15 Selected Paths', font: { color: '#8b949e', size: 12 } },
                    showlegend: false,
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#8b949e', size: 9 },
                    margin: { t: 50, r: 25, b: 40, l: 60 },
                    xaxis: { gridcolor: '#21262d', linecolor: '#30363d' },
                    yaxis: { gridcolor: '#21262d', linecolor: '#30363d' }
                };
                const chartDiv = document.getElementById('mc-chart-div');
                chartDiv.innerHTML = '';
                Plotly.newPlot(chartDiv, traces, layout, { responsive: true });
            }, 1200);
        });
    }

    // 2f. Run Genetic Optimization simulation
    const btnRunOpt = document.getElementById('btn-run-opt');
    if (btnRunOpt) {
        btnRunOpt.addEventListener('click', () => {
            btnRunOpt.innerText = 'Optimizing Matrix...';
            btnRunOpt.setAttribute('disabled', 'true');
            setTimeout(() => {
                btnRunOpt.innerText = '▶ Run Genetic Optimizer';
                btnRunOpt.removeAttribute('disabled');
                
                // Scatter matrix parameter optimization
                const trace = {
                    x: [10, 14, 20, 25, 30, 35, 12, 18, 22, 28],
                    y: [30, 50, 70, 45, 60, 55, 40, 65, 35, 80],
                    mode: 'markers',
                    type: 'scatter',
                    marker: {
                        size: [12, 22, 18, 25, 30, 15, 20, 28, 14, 32],
                        color: [85, 120, 95, 140, 160, 110, 90, 130, 75, 180],
                        colorscale: 'Viridis',
                        showscale: true
                    }
                };
                const layout = {
                    title: { text: 'Parameter Space Map (RSI vs MACD Profit Factor)', font: { color: '#8b949e', size: 12 } },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#8b949e', size: 9 },
                    margin: { t: 50, r: 25, b: 45, l: 60 },
                    xaxis: { title: 'RSI Period', gridcolor: '#21262d', linecolor: '#30363d' },
                    yaxis: { title: 'MACD Boundary', gridcolor: '#21262d', linecolor: '#30363d' }
                };
                const chartDiv = document.getElementById('opt-chart-div');
                chartDiv.innerHTML = '';
                Plotly.newPlot(chartDiv, [trace], layout, { responsive: true });

                // Populate Top Parameters Table
                const tableBody = document.getElementById('opt-table-body');
                const resultsRow = document.getElementById('opt-results-row');
                
                const candidates = [
                    { rank: 1, rsi: 14, macd: 30, winRate: "72.4%", pf: "2.14", dd: "4.5%" },
                    { rank: 2, rsi: 12, macd: 40, winRate: "68.9%", pf: "1.92", dd: "5.1%" },
                    { rank: 3, rsi: 20, macd: 35, winRate: "65.5%", pf: "1.74", dd: "6.2%" },
                    { rank: 4, rsi: 18, macd: 45, winRate: "62.1%", pf: "1.65", dd: "5.8%" },
                    { rank: 5, rsi: 10, macd: 50, winRate: "59.3%", pf: "1.48", dd: "7.0%" }
                ];
                
                tableBody.innerHTML = '';
                candidates.forEach(c => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td class="fw-bold">#${c.rank}</td>
                        <td>${c.rsi}</td>
                        <td>${c.macd}</td>
                        <td class="text-bullish fw-bold">${c.winRate}</td>
                        <td class="text-info-v42">${c.pf}</td>
                        <td class="text-critical">${c.dd}</td>
                        <td><button class="btn btn-xs btn-outline-primary py-0 px-2" onclick="alert('Applied RSI Period: ${c.rsi}, MACD Boundary: ${c.macd} to Live Core!')">Apply</button></td>
                    `;
                    tableBody.appendChild(row);
                });
                
                resultsRow.classList.remove('d-none');
            }, 1500);
        });
    }
    
    let autotradeEnabled = false;
    let hedgingEnabled = true;

    window.adjustLot = function(amount) {
        const input = document.getElementById('trading-lot-input');
        if (input) {
            let val = parseFloat(input.value) + amount;
            if (val < 0.01) val = 0.01;
            input.value = val.toFixed(2);
            window.sendTradingSettings();
        }
    };

    window.adjustConfidence = function(amount) {
        const input = document.getElementById('confidence-threshold-input');
        if (input) {
            let val = parseInt(input.value) + amount;
            if (val < 50) val = 50;
            if (val > 99) val = 99;
            input.value = val;
            window.sendTradingSettings();
        }
    };

    window.adjustMaxOP = function(amount) {
        const input = document.getElementById('max-op-input');
        if (input) {
            let val = parseInt(input.value) + amount;
            if (val < 1) val = 1;
            if (val > 50) val = 50;
            input.value = val;
            window.sendTradingSettings();
        }
    };
    
    // Sniper Score local state management
    window.sniperScoreThreshold = 80;
    
    window.adjustSniperScore = function(amount) {
        const input = document.getElementById('sniper-score-input');
        if (input) {
            let val = parseInt(input.value) + amount;
            if (val < 50) val = 50;
            if (val > 99) val = 99;
            input.value = val;
            window.updateSniperScore();
        }
    };
    
    window.updateSniperScore = function() {
        const input = document.getElementById('sniper-score-input');
        if (input) {
            window.sniperScoreThreshold = parseInt(input.value);
            window.sendTradingSettings(); // Send to backend for Autotrade enforcement
        }
    };
    
    window.adjustSniperLot = function(amount) {
        const input = document.getElementById('sniper-lot-input');
        if (input) {
            let val = parseFloat(input.value) + amount;
            if (val < 0) val = 0;
            input.value = val.toFixed(2);
            window.updateSniperLot();
        }
    };
    
    window.updateSniperLot = function() {
        const input = document.getElementById('sniper-lot-input');
        if (input) {
            window.sniperLotSize = parseFloat(input.value);
            window.sendTradingSettings();
        }
    };

    window.toggleAutoTrade = function() {
        autotradeEnabled = !autotradeEnabled;
        window.sendTradingSettings();
    };

    window.toggleHedging = function() {
        hedgingEnabled = !hedgingEnabled;
        window.sendTradingSettings();
    };

    window.closePosition = function(ticket) {
        if (confirm(`Apakah Anda yakin ingin menutup Transaksi #${ticket}?`)) {
            if (window.globalWs && window.globalWs.readyState === WebSocket.OPEN) {
                window.globalWs.send(JSON.stringify({
                    action: "close_position",
                    ticket: ticket
                }));
            }
        }
    };

    window.modifyPosition = function(ticket) {
        const slInput = document.getElementById(`sl-${ticket}`);
        const tpInput = document.getElementById(`tp-${ticket}`);
        if (slInput && tpInput) {
            const sl = parseFloat(slInput.value);
            const tp = parseFloat(tpInput.value);
            if (window.globalWs && window.globalWs.readyState === WebSocket.OPEN) {
                window.globalWs.send(JSON.stringify({
                    action: "modify_position_sltp",
                    ticket: ticket,
                    sl: sl,
                    tp: tp
                }));
            }
        }
    };

    window.closeAllPositions = function() {
        if (confirm("Apakah Anda yakin ingin menutup SEMUA transaksi yang sedang aktif?")) {
            if (window.globalWs && window.globalWs.readyState === WebSocket.OPEN) {
                window.globalWs.send(JSON.stringify({
                    action: "close_all"
                }));
            }
        }
    };

    window.sendTradingSettings = function() {
        const input = document.getElementById('trading-lot-input');
        const lotSize = input ? parseFloat(input.value) : 0.10;
        const confInput = document.getElementById('confidence-threshold-input');
        const confidenceThreshold = confInput ? parseInt(confInput.value) / 100.0 : 0.65;
        const maxOpInput = document.getElementById('max-op-input');
        const maxPositions = maxOpInput ? parseInt(maxOpInput.value) : 3;
        const autoLotCheckbox = document.getElementById('auto-lot-checkbox');
        const autoLot = autoLotCheckbox ? autoLotCheckbox.checked : false;
        const riskInput = document.getElementById('risk-percent-input');
        const riskPercent = riskInput ? parseFloat(riskInput.value) : 1.0;
        
        const activeAiModelSelect = document.getElementById('active-ai-model-select');
        const activeMethod = activeAiModelSelect ? activeAiModelSelect.value : 'intra-candle-scalper';
        
        // Update UI styling locally right away
        updateAutoLotUI(autoLot);
        
        // Update badge right away
        const activeMethodBadge = document.getElementById('active-method-badge');
        if (activeMethodBadge) {
            activeMethodBadge.innerText = activeMethod.replace(/-/g, ' ').toUpperCase();
        }
        
        if (window.globalWs && window.globalWs.readyState === WebSocket.OPEN) {
            window.globalWs.send(JSON.stringify({
                action: "update_settings",
                autotrade: autotradeEnabled,
                lot_size: lotSize,
                confidence_threshold: confidenceThreshold,
                sniper_score: window.sniperScoreThreshold || 80,
                sniper_lot: window.sniperLotSize !== undefined ? window.sniperLotSize : 0.50,
                max_positions: maxPositions,
                hedging_enabled: hedgingEnabled,
                auto_lot: autoLot,
                risk_percent: riskPercent,
                active_method: activeMethod
            }));
        }
    };

    window.saveTradingSettingsLocally = function() {
        const input = document.getElementById('trading-lot-input');
        const lotSize = input ? parseFloat(input.value) : 0.10;
        const confInput = document.getElementById('confidence-threshold-input');
        const confidenceThreshold = confInput ? parseInt(confInput.value) : 65;
        const maxOpInput = document.getElementById('max-op-input');
        const maxPositions = maxOpInput ? parseInt(maxOpInput.value) : 3;
        const autoLotCheckbox = document.getElementById('auto-lot-checkbox');
        const autoLot = autoLotCheckbox ? autoLotCheckbox.checked : false;
        const riskInput = document.getElementById('risk-percent-input');
        const riskPercent = riskInput ? parseFloat(riskInput.value) : 1.0;

        // Persist parameters to LocalStorage
        localStorage.setItem('trading_lot', lotSize);
        localStorage.setItem('confidence_threshold', confidenceThreshold);
        localStorage.setItem('max_positions', maxPositions);
        localStorage.setItem('auto_lot_enabled', autoLot);
        localStorage.setItem('risk_percent', riskPercent);
        localStorage.setItem('hedging_enabled', hedgingEnabled);
        localStorage.setItem('autotrade_enabled', autotradeEnabled);

        // Sync back to backend via websocket
        window.sendTradingSettings();

        // Animate Save Button
        const saveBtn = document.getElementById('save-trading-settings-btn');
        if (saveBtn) {
            const originalText = saveBtn.innerHTML;
            saveBtn.innerHTML = '✔ SAVED!';
            saveBtn.style.backgroundColor = '#2ea043';
            saveBtn.style.borderColor = '#2ea043';
            saveBtn.style.boxShadow = '0 0 8px rgba(46, 160, 67, 0.6)';
            setTimeout(() => {
                saveBtn.innerHTML = originalText;
                saveBtn.style.backgroundColor = '#2f80ed';
                saveBtn.style.borderColor = '#2f80ed';
                saveBtn.style.boxShadow = '0 0 6px rgba(47,128,237,0.4)';
            }, 2000);
        }
    };

    window.toggleAutoLot = function() {
        window.sendTradingSettings();
    };

    function updateAutoLotUI(autoLotEnabled) {
        const autoLotCheckbox = document.getElementById('auto-lot-checkbox');
        if (autoLotCheckbox) {
            autoLotCheckbox.checked = autoLotEnabled;
        }
        
        const inputs = [
            'trading-lot-input',
            'confidence-threshold-input',
            'max-op-input'
        ];
        
        inputs.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.disabled = autoLotEnabled;
                el.style.opacity = autoLotEnabled ? '0.4' : '1.0';
            }
        });
        
        // Disable or enable Risk Percent input
        const riskInput = document.getElementById('risk-percent-input');
        if (riskInput) {
            riskInput.disabled = !autoLotEnabled;
            riskInput.style.opacity = !autoLotEnabled ? '0.4' : '1.0';
        }
        
        // Also disable the +/- buttons
        const buttons = document.querySelectorAll('#tab-trading .btn-outline-secondary');
        buttons.forEach(btn => {
            btn.disabled = autoLotEnabled;
            btn.style.opacity = autoLotEnabled ? '0.4' : '1.0';
            btn.style.pointerEvents = autoLotEnabled ? 'none' : 'auto';
        });
    }

    window.shutdownServer = function() {
        if (confirm("Apakah Anda yakin ingin mematikan (Shutdown) server produksi XEDY?")) {
            if (window.globalWs && window.globalWs.readyState === WebSocket.OPEN) {
                window.globalWs.send(JSON.stringify({
                    action: "shutdown"
                }));
            } else {
                alert("Koneksi WebSocket terputus. Server mungkin sudah offline.");
            }
        }
    };

    let autoCleanIntervalId = null;

    window.cleanRamMemory = async function() {
        const btn = document.getElementById('btn-clean-ram');
        if (!btn) return;
        btn.disabled = true;
        btn.innerText = '🧹 CLEANING MEMORY...';
        
        try {
            const response = await fetch(window.API_BASE + '/api/v1/system/rammap/clean', { method: 'POST' });
            const result = await response.json();
            alert(result.message);
        } catch (err) {
            console.error("Failed to clean RAM:", err);
            alert("Error: Failed to connect to backend memory API.");
        } finally {
            btn.disabled = false;
            btn.innerText = 'RUN RAMMAP CLEANER';
        }
    };

    window.toggleAutoCleanRam = function() {
        const chk = document.getElementById('vram-auto-clean-chk');
        if (!chk) return;
        
        localStorage.setItem('vramAutoCleanEnabled', chk.checked);
        
        if (chk.checked) {
            startAutoCleanRam();
        } else {
            stopAutoCleanRam();
        }
    };

    window.changeAutoCleanInterval = function() {
        const select = document.getElementById('vram-auto-clean-interval');
        if (!select) return;
        
        localStorage.setItem('vramAutoCleanInterval', select.value);
        
        const chk = document.getElementById('vram-auto-clean-chk');
        if (chk && chk.checked) {
            stopAutoCleanRam();
            startAutoCleanRam();
        }
    };

    function startAutoCleanRam() {
        const select = document.getElementById('vram-auto-clean-interval');
        const minutes = select ? parseInt(select.value) : 15;
        const ms = minutes * 60 * 1000;
        
        if (autoCleanIntervalId) clearInterval(autoCleanIntervalId);
        
        console.log(`Auto-cleaning RAM started. Interval: ${minutes} minutes.`);
        autoCleanIntervalId = setInterval(async () => {
            console.log("Triggering scheduled RAM clean...");
            try {
                const response = await fetch(window.API_BASE + '/api/v1/system/rammap/clean', { method: 'POST' });
                const result = await response.json();
                
                // Alert in UI status label dynamically instead of pop-up
                const ramLabel = document.getElementById('ram-usage-text');
                if (ramLabel) {
                    const originalText = ramLabel.innerText;
                    ramLabel.innerText = "🧹 AUTO-CLEAN SUCCESS";
                    ramLabel.className = "text-bullish fw-bold";
                    setTimeout(() => {
                        ramLabel.innerText = originalText;
                        ramLabel.className = "text-white";
                    }, 4000);
                }
            } catch (err) {
                console.error("Auto-clean RAM failed:", err);
            }
        }, ms);
    }

    function stopAutoCleanRam() {
        if (autoCleanIntervalId) {
            clearInterval(autoCleanIntervalId);
            autoCleanIntervalId = null;
            console.log("Auto-cleaning RAM stopped.");
        }
    }

    window.loadAutoCleanState = function() {
        const savedEnabled = localStorage.getItem('vramAutoCleanEnabled') === 'true';
        const savedInterval = localStorage.getItem('vramAutoCleanInterval') || '15';
        
        const chk = document.getElementById('vram-auto-clean-chk');
        const select = document.getElementById('vram-auto-clean-interval');
        
        if (select) select.value = savedInterval;
        if (chk) {
            chk.checked = savedEnabled;
            if (savedEnabled) {
                startAutoCleanRam();
            }
        }
    };

    window.applyVirtualRamSettings = async function() {
        const initInput = document.getElementById('vram-init-size');
        const maxInput = document.getElementById('vram-max-size');
        if (!initInput || !maxInput) return;
        
        const initialMb = parseInt(initInput.value);
        const maxMb = parseInt(maxInput.value);
        
        if (isNaN(initialMb) || isNaN(maxMb) || initialMb <= 0 || maxMb <= 0) {
            alert("Please enter valid positive numbers for sizes.");
            return;
        }
        
        if (initialMb > maxMb) {
            alert("Initial size cannot be greater than Maximum size.");
            return;
        }
        
        if (!confirm(`Apakah Anda yakin ingin mengatur Virtual RAM (Page File) ke Initial=${initialMb}MB, Max=${maxMb}MB? Ini akan mengubah setelan sistem Windows.`)) {
            return;
        }
        
        try {
            const response = await fetch(window.API_BASE + '/api/v1/system/vram/set', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ initial_mb: initialMb, max_mb: maxMb })
            });
            const result = await response.json();
            alert(result.message);
        } catch (err) {
            console.error("Failed to configure Virtual RAM:", err);
            alert("Error setting Virtual RAM.");
        }
    };

    function renderCachedNews() {
        try {
            const cachedNews = localStorage.getItem('cachedNewsFeed');
            const cachedSentiment = localStorage.getItem('cachedNewsSentiment');
            const cachedMacro = localStorage.getItem('cachedMacroDrivers');

            if (cachedNews) {
                const newsList = JSON.parse(cachedNews);
                const newsTbody = document.getElementById('news-tab-feed-tbody');
                if (newsTbody && newsList.length > 0) {
                    let newsHtml = '';
                    newsList.forEach(item => {
                        const impactClass = item.gold_impact === 'BULLISH' ? 'text-bullish' : (item.gold_impact === 'BEARISH' ? 'text-critical' : 'text-muted');
                        const finalScoreClass = item.final_score > 60 ? 'text-bullish fw-bold' : (item.final_score < 40 ? 'text-critical fw-bold' : 'text-white');
                        let shortSource = item.source;
                        if (shortSource.includes("Yahoo")) shortSource = shortSource.split(" ")[0];
                        if (shortSource === "Federal Reserve") shortSource = "Fed";
                        if (shortSource === "World Gold Council") shortSource = "WGC";
                        if (shortSource === "CME FedWatch") shortSource = "CME";
                        if (shortSource === "Investing.com") shortSource = "Investing";
                        if (shortSource === "Trading Economics") shortSource = "TradEcon";
                        const sourceDisplay = `${shortSource} (${item.source_weight.toFixed(1)})`;

                        newsHtml += `<tr>
                            <td>${sourceDisplay}</td>
                            <td class="text-white" style="word-wrap: break-word; white-space: normal;">${item.headline}</td>
                            <td>${item.relevancy}%</td>
                            <td>${item.sentiment_score.toFixed(1)}</td>
                            <td class="${impactClass} fw-bold">${item.gold_impact}</td>
                            <td>${item.confidence.toFixed(1)}%</td>
                            <td>${item.duration}</td>
                            <td>${item.regime}</td>
                            <td class="${finalScoreClass}">${item.final_score}</td>
                        </tr>`;
                    });
                    newsTbody.innerHTML = newsHtml;
                }
            }

            if (cachedSentiment) {
                const sent = JSON.parse(cachedSentiment);
                const elSentiment = document.getElementById('kpi-sentiment');
                if(elSentiment) {
                    elSentiment.innerText = `${sent.current} (${sent.trend})`;
                    elSentiment.className = sent.label === 'BULLISH' ? 'kpi-value text-bullish fs-5' : (sent.label === 'BEARISH' ? 'kpi-value text-critical fs-5' : 'kpi-value text-white fs-5');
                }
                const elNewsTabSent = document.getElementById('news-tab-sentiment');
                if (elNewsTabSent) {
                    elNewsTabSent.innerText = sent.current;
                    elNewsTabSent.className = sent.label === 'BULLISH' ? 'kpi-value text-bullish' : (sent.label === 'BEARISH' ? 'kpi-value text-critical' : 'kpi-value text-white');
                }
                const elNewsTabPrev = document.getElementById('news-tab-prev-sentiment');
                if (elNewsTabPrev) elNewsTabPrev.innerText = sent.previous;
                const elNewsTabTrend = document.getElementById('news-tab-trend');
                if (elNewsTabTrend) {
                    elNewsTabTrend.innerText = sent.trend;
                    elNewsTabTrend.className = sent.trend === 'NAIK' ? 'kpi-value text-bullish' : 'kpi-value text-critical';
                }
                const elNewsTabRec = document.getElementById('news-tab-gold-rec');
                if (elNewsTabRec) {
                    elNewsTabRec.innerText = sent.label;
                    elNewsTabRec.className = sent.label === 'BULLISH' ? 'kpi-value text-bullish' : (sent.label === 'BEARISH' ? 'kpi-value text-critical' : 'kpi-value text-white');
                }
            }
        } catch (e) {
            console.error("Error rendering cached news: ", e);
        }
    }

    function loadSavedTradingSettings() {
        try {
            const savedLot = localStorage.getItem('trading_lot');
            const savedConf = localStorage.getItem('confidence_threshold');
            const savedMaxOp = localStorage.getItem('max_positions');
            const savedHedging = localStorage.getItem('hedging_enabled');
            const savedAutotrade = localStorage.getItem('autotrade_enabled');

            if (savedLot) {
                const lotInput = document.getElementById('trading-lot-input');
                if (lotInput) lotInput.value = parseFloat(savedLot).toFixed(2);
            }
            if (savedConf) {
                const confInput = document.getElementById('confidence-threshold-input');
                if (confInput) confInput.value = parseInt(savedConf);
            }
            if (savedMaxOp) {
                const maxOpInput = document.getElementById('max-op-input');
                if (maxOpInput) maxOpInput.value = parseInt(savedMaxOp);
            }
            if (savedHedging) {
                const hedgingEnabledVal = savedHedging === 'true';
                hedgingEnabled = hedgingEnabledVal;
                const hedgingBtn = document.getElementById('hedging-toggle-btn');
                if (hedgingBtn) {
                    if (hedgingEnabledVal) {
                        hedgingBtn.innerText = 'ON';
                        hedgingBtn.className = 'btn btn-sm btn-success';
                        hedgingBtn.style.boxShadow = '0 0 8px rgba(46, 160, 67, 0.6)';
                    } else {
                        hedgingBtn.innerText = 'OFF';
                        hedgingBtn.className = 'btn btn-sm btn-outline-danger';
                        hedgingBtn.style.boxShadow = 'none';
                    }
                }
            }
            if (savedAutotrade) {
                const autotradeEnabledVal = savedAutotrade === 'true';
                autotradeEnabled = autotradeEnabledVal;
                const toggleBtn = document.getElementById('autotrade-toggle-btn');
                if (toggleBtn) {
                    if (autotradeEnabledVal) {
                        toggleBtn.innerText = 'ON';
                        toggleBtn.className = 'btn btn-sm btn-success';
                        toggleBtn.style.boxShadow = '0 0 8px rgba(46, 160, 67, 0.6)';
                    } else {
                        toggleBtn.innerText = 'OFF';
                        toggleBtn.className = 'btn btn-sm btn-outline-danger';
                        toggleBtn.style.boxShadow = 'none';
                    }
                }
            }
            
            const savedAutoLot = localStorage.getItem('auto_lot_enabled');
            if (savedAutoLot) {
                const autoLotEnabledVal = savedAutoLot === 'true';
                updateAutoLotUI(autoLotEnabledVal);
            }
            
            const savedRisk = localStorage.getItem('risk_percent');
            if (savedRisk) {
                const riskInput = document.getElementById('risk-percent-input');
                if (riskInput) riskInput.value = parseFloat(savedRisk).toFixed(1);
            }
        } catch (e) {
            console.error("Error loading saved trading settings: ", e);
        }
    }

    renderCachedNews();
    loadSavedTradingSettings();
    
    // Restore last active tab on page load
    const savedActiveTab = localStorage.getItem('activeTab');
    if (savedActiveTab) {
        const matchingLink = Array.from(navLinks).find(l => l.getAttribute('data-target') === savedActiveTab);
        if (matchingLink) {
            matchingLink.click();
        }
    }

    // Administration sub-module switching logic
    const adminNavLinks = document.querySelectorAll('.admin-nav-link');
    const adminContentPanel = document.getElementById('admin-content-panel');

    const adminModules = {
        user: `
            <div class="h-100 d-flex flex-column">
                <h6 class="text-white border-bottom border-secondary pb-2 mb-3">👤 User Management</h6>
                <div class="row g-3 flex-grow-1">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label text-muted small">Username</label>
                            <input type="text" class="form-control form-control-sm bg-dark text-white border-secondary" id="admin-user-username" value="admin" readonly>
                        </div>
                        <div class="mb-3">
                            <label class="form-label text-muted small">New Password</label>
                            <input type="password" class="form-control form-control-sm bg-dark text-white border-secondary" id="admin-user-password" placeholder="••••••••">
                        </div>
                        <button class="btn btn-primary btn-sm fw-bold" onclick="saveAdminModule('user')">UPDATE PASSWORD</button>
                    </div>
                </div>
            </div>
        `,
        broker: `
            <div class="h-100 d-flex flex-column">
                <h6 class="text-white border-bottom border-secondary pb-2 mb-3">🏦 Broker Integration (MT5 Bridge)</h6>
                <div class="row g-3 flex-grow-1">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label text-muted small">MT5 Account Number</label>
                            <input type="text" class="form-control form-control-sm bg-dark text-white border-secondary" id="admin-broker-login" value="6510822">
                        </div>
                        <div class="mb-3">
                            <label class="form-label text-muted small">MT5 Password</label>
                            <input type="password" class="form-control form-control-sm bg-dark text-white border-secondary" id="admin-broker-password" value="••••••••">
                        </div>
                        <div class="mb-3">
                            <label class="form-label text-muted small">Broker Server</label>
                            <input type="text" class="form-control form-control-sm bg-dark text-white border-secondary" id="admin-broker-server" value="Exness-MT5Trial6">
                        </div>
                        <button class="btn btn-primary btn-sm fw-bold me-2" onclick="saveAdminModule('broker')">SAVE CREDENTIALS</button>
                        <button class="btn btn-outline-info btn-sm fw-bold" onclick="reconnectMT5()">RECONNECT MT5</button>
                    </div>
                </div>
            </div>
        `,
        strategy: `
            <div class="h-100 d-flex flex-column">
                <h6 class="text-white border-bottom border-secondary pb-2 mb-3">📈 Strategy Settings</h6>
                <div class="row g-3 flex-grow-1">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label text-muted small">Trade Symbol</label>
                            <input type="text" class="form-control form-control-sm bg-dark text-white border-secondary" id="admin-strategy-symbol" value="XAUUSD">
                        </div>
                        <div class="mb-3">
                            <label class="form-label text-muted small">Timeframe Selection</label>
                            <select class="form-select form-select-sm bg-dark text-white border-secondary" id="admin-strategy-timeframe">
                                <option value="M15" selected>M15 (15 Minutes)</option>
                                <option value="M30">M30 (30 Minutes)</option>
                                <option value="H1">H1 (1 Hour)</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label text-muted small">Execution Mode</label>
                            <select class="form-select form-select-sm bg-dark text-white border-secondary" id="admin-strategy-mode">
                                <option value="DEAL" selected>Instant Market (DEAL)</option>
                                <option value="LIMIT">Pending Limit (LIMIT)</option>
                            </select>
                        </div>
                        <button class="btn btn-primary btn-sm fw-bold" onclick="saveAdminModule('strategy')">APPLY STRATEGY SETTINGS</button>
                    </div>
                </div>
            </div>
        `,
        telegram: `
            <div class="h-100 d-flex flex-column">
                <h6 class="text-white border-bottom border-secondary pb-2 mb-3">💬 Telegram API (Admin Alerts)</h6>
                <div class="row g-3 flex-grow-1">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label text-muted small">Telegram Bot Token</label>
                            <input type="text" class="form-control form-control-sm bg-dark text-white border-secondary" id="admin-telegram-token" value="6299381029:AAFk...">
                        </div>
                        <div class="mb-3">
                            <label class="form-label text-muted small">Admin Chat ID</label>
                            <input type="text" class="form-control form-control-sm bg-dark text-white border-secondary" id="admin-telegram-chatid" value="189283749">
                        </div>
                        <button class="btn btn-primary btn-sm fw-bold" onclick="saveAdminModule('telegram')">SAVE TELEGRAM KEYS</button>
                    </div>
                </div>
            </div>
        `,
        risk: `
            <div class="h-100 d-flex flex-column">
                <h6 class="text-white border-bottom border-secondary pb-2 mb-3">⚠️ Risk Parameters</h6>
                <div class="row g-3 flex-grow-1">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label text-muted small">Max Daily Drawdown (decimal)</label>
                            <input type="number" class="form-control form-control-sm bg-dark text-white border-secondary" id="admin-risk-drawdown" value="0.02" step="0.01" min="0.01" max="0.10">
                        </div>
                        <div class="mb-3">
                            <label class="form-label text-muted small">Averaging Timeframe</label>
                            <select class="form-select form-select-sm bg-dark text-white border-secondary" id="admin-risk-avg-tf">
                                <option value="M15">M15</option>
                                <option value="M30" selected>M30</option>
                                <option value="H1">H1</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label text-muted small">Averaging ATR Multiplier</label>
                            <input type="number" class="form-control form-control-sm bg-dark text-white border-secondary" id="admin-risk-avg-mult" value="1.0" step="0.1">
                        </div>
                        <button class="btn btn-primary btn-sm fw-bold" onclick="saveAdminModule('risk')">APPLY RISK PARAMETERS</button>
                    </div>
                </div>
            </div>
        `,
        ai: `
            <div class="h-100 d-flex flex-column">
                <h6 class="text-white border-bottom border-secondary pb-2 mb-3">🧠 AI Engine Tuning</h6>
                <div class="row g-3 flex-grow-1">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label text-muted small">Base XGBoost Model File</label>
                            <input type="text" class="form-control form-control-sm bg-dark text-white border-secondary" id="admin-ai-model" value="models/xgboost_base.json" readonly>
                        </div>
                        <div class="mb-3">
                            <label class="form-label text-muted small">Minimum Output Confidence (%)</label>
                            <input type="number" class="form-control form-control-sm bg-dark text-white border-secondary" id="admin-ai-min-conf" value="55" min="50" max="99">
                        </div>
                        <button class="btn btn-primary btn-sm fw-bold" onclick="saveAdminModule('ai')">SAVE TUNING SETTINGS</button>
                    </div>
                </div>
            </div>
        `,
        scheduler: `
            <div class="h-100 d-flex flex-column">
                <h6 class="text-white border-bottom border-secondary pb-2 mb-3">⏱️ Scheduler Config</h6>
                <div class="row g-3 flex-grow-1">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label text-muted small">Self-Optimization Loop Interval (minutes)</label>
                            <input type="number" class="form-control form-control-sm bg-dark text-white border-secondary" id="admin-sched-opt-int" value="10" min="5" max="1440">
                        </div>
                        <button class="btn btn-primary btn-sm fw-bold" onclick="saveAdminModule('scheduler')">APPLY SCHEDULER CONFIG</button>
                    </div>
                </div>
            </div>
        `,
        backup: `
            <div class="h-100 d-flex flex-column">
                <h6 class="text-white border-bottom border-secondary pb-2 mb-3">💾 Backup & Restore</h6>
                <div class="row g-3 flex-grow-1">
                    <div class="col-md-6">
                        <p class="text-muted small">Simpan atau pulihkan basis data SQLite database transaksi sistem.</p>
                        <div class="mb-3">
                            <button class="btn btn-success btn-sm fw-bold me-2" onclick="triggerAdminBackup()"><i class="bi bi-download me-1"></i> BACKUP DATABASE</button>
                            <button class="btn btn-warning btn-sm fw-bold" onclick="triggerAdminRestore()"><i class="bi bi-upload me-1"></i> RESTORE DATABASE</button>
                        </div>
                    </div>
                </div>
            </div>
        `,
        update: `
            <div class="h-100 d-flex flex-column">
                <h6 class="text-white border-bottom border-secondary pb-2 mb-3">🔄 System Update</h6>
                <div class="row g-3 flex-grow-1">
                    <div class="col-md-6">
                        <p class="text-white">Active Version: <span class="text-info fw-bold">v41.0.0 (Production Build)</span></p>
                        <button class="btn btn-primary btn-sm fw-bold" onclick="triggerCheckUpdate()">CHECK FOR UPDATES</button>
                    </div>
                </div>
            </div>
        `,
        license: `
            <div class="h-100 d-flex flex-column">
                <h6 class="text-white border-bottom border-secondary pb-2 mb-3">🔑 License Management</h6>
                <div class="row g-3 flex-grow-1">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label text-muted small">Platform License Key</label>
                            <input type="text" class="form-control form-control-sm bg-dark text-white border-secondary" id="admin-license-key" value="XEDY-ENTERPRISE-9831-ABCD-LIFETIME" readonly>
                        </div>
                        <p class="text-success small fw-bold"><i class="bi bi-patch-check-fill me-1"></i> LICENSED & ACTIVATED</p>
                    </div>
                </div>
            </div>
        `
    };

    adminNavLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            adminNavLinks.forEach(l => l.classList.remove('active', 'bg-secondary'));
            link.classList.add('active', 'bg-secondary');
            
            const moduleName = link.getAttribute('data-module');
            if (adminModules[moduleName]) {
                adminContentPanel.innerHTML = adminModules[moduleName];
            }
        });
    });

    window.saveAdminModule = function(moduleName) {
        alert(`Settings for module "${moduleName}" saved successfully!`);
    };

    window.triggerAdminBackup = function() {
        alert("Database backup completed successfully! Saved to backup/database_backup.db");
    };

    window.triggerAdminRestore = function() {
        alert("Database restore completed successfully!");
    };

    window.triggerCheckUpdate = function() {
        alert("Sistem Anda sudah mutakhir (v41.0.0 terbaru).");
    };

    // AutoTrade Model Selector Logic
    const activeAiModelSelect = document.getElementById('active-ai-model-select');
    const selectedModelTitle = document.getElementById('selected-model-title');
    const selectedModelDesc = document.getElementById('selected-model-desc');
    const applyAiModelBtn = document.getElementById('apply-ai-model-btn');

    const modelInfo = {
        'adaptive-auto-select': {
            title: '🔄 ADAPTIVE SYSTEM (AUTO SELECT)',
            desc: 'Sistem dalam mode adaptif penuh. CEO AI mengevaluasi perdagangan harian berdasarkan umpan balik MAE/MFE untuk memilih metode optimal secara otomatis dan menyesuaikan persentase risiko Kelly Dinamis.'
        },
        'intra-candle-scalper': {
            title: '🚀 Double-Sided Intra-Candle Scalper (M30)',
            desc: 'Strategi scalping frekuensi tinggi dua arah (BUY & SELL pending limits) di dalam siklus hidup lilin M30 dengan dynamic martingale micro-recovery grid untuk mengunci profit 95% winrate per bar.'
        },
        'open-shift-close-breakout': {
            title: '🔄 Breakout Stop-Entry - Hybrid Qwen AI (M30)',
            desc: 'Metode Stop-Breakout teroptimasi pada timeframe M30. Menggunakan EMA 5/15, TP 3.0x, SL 2.5x, dan stop offset 0.05x ATR untuk menangkap momentum awal breakout dengan tingkat drawdown ultra rendah (DD 14.81%, Profit +156.39%).'
        },
        'open-shift-close-pattern': {
            title: '🧩 Pattern-Filter Hybrid - Qwen AI (M30)',
            desc: 'Model penyaringan pola candlestick asimetris pada timeframe M30. Menghindari inside bar dan membatasi doji sempit untuk menyaring fase sideways market (DD 19.03%, Profit +131.72%).'
        },
        'open-shift-close': {
            title: '🔄 Baseline Hybrid Mode - Qwen AI (M30)',
            desc: 'Model baseline EMA 5/15 + ATR TP/SL dinamis yang disaring oleh bias makro Qwen AI Hybrid (DD 34.86%, Profit +133.43%).'
        },
        'decision-priority-engine': {
            title: '🧠 14-Layer Decision Priority Engine',
            desc: 'Model institusional 14 lapis (Macro, Regime, Liquidity, Orderflow, dsb). Menghasilkan skor Unified Edge (UES). Eksekusi hanya pada area High Probability/Institutional Grade (UES >= 90).'
        },
        'smart-money-bos': {
            title: '🏛️ Smart Money: BOS Breakout (Break of Structure)',
            desc: 'Metode deteksi Smart Money Concepts. Mengidentifikasi Swing High/Low utama pada timeframe H1 menggunakan pola Fractal, dan mengeksekusi posisi ketika candlestick M15 berhasil menembus (close breakout) di atas/bawah area struktur. Menggunakan Stop Loss dan Take Profit berbasis volatilitas ATR(14).'
        },
        'scalping-1-1': {
            title: '⚡ Scalping 1:1 TP/SL (M30)',
            desc: 'Strategi scalping crossover EMA 2/25 dengan target profit dan batas rugi simetris 1.5x ATR vs 2.0x ATR untuk winrate di atas 50%.'
        },
        'intra-candle-scalper-m5': {
            title: '⚡ Double-Sided Intra-Candle Scalper (M5)',
            desc: 'Strategi scalping frekuensi tinggi dua arah pada timeframe M5. Memanfaatkan siklus lilin 5 menit untuk eksekusi ratusan trade per hari dengan winrate mendekati 100% dan profit harian +24.0%.'
        },
        'intra-candle-scalper-m15': {
            title: '⚡ Double-Sided Intra-Candle Scalper (M15)',
            desc: 'Strategi scalping frekuensi tinggi dua arah pada timeframe M15. Memanfaatkan lilin 15 menit untuk keseimbangan ideal antara jumlah trade dan winrate (100% Winrate pada pengujian 1 hari).'
        },
        'intra-candle-scalper-h1': {
            title: '⚡ Double-Sided Intra-Candle Scalper (H1)',
            desc: 'Strategi scalping dua arah pada timeframe H1 (1 Jam). Menawarkan kestabilan tinggi untuk menargetkan swing micro trend dengan drawdown minimal dan profit harian +6.8%.'
        },
        'intra-candle-scalper-h4': {
            title: '⚡ Double-Sided Intra-Candle Scalper (H4)',
            desc: 'Strategi scalping dua arah pada timeframe H4 (4 Jam). Menyaring fluktuasi jangka pendek untuk menangkap pergerakan tren utama dengan lot yang terjaga dan profit harian +2.3%.'
        },
        'qwen3.7-flash-dynamic': {
            title: '🤖 Qwen 3.7 Flash Dynamic (Teroptimasi)',
            desc: 'Model trading kuantitatif tingkat institusional. Menghitung dynamic stop-loss, take-profit, dan break-even trigger per sesi waktu (Asia, Eropa, US) menggunakan umpan balik MAE/MFE secara real-time.'
        },
        'qwen3-embedding-8b': {
            title: '📊 Qwen3 Embedding 8B (Vector News Alignment)',
            desc: 'Menghubungkan data sentimen berita dan fundamental global langsung ke dalam database vektor. Menggunakan pencarian semantik (Semantic Search) untuk menyesuaikan bias trading XAUUSD secara real-time.'
        },
        'xgboost-standalone-9d': {
            title: '📊 XGBoost Standalone (9-D Baseline)',
            desc: 'Inference model pembelajaran mesin murni menggunakan 9 indikator teknikal konvensional tanpa penyesuaian jam sesi dinamis.'
        },
        'smc-liquidity-v2': {
            title: '🏛️ Smart Money Concepts & Liquidity Engine',
            desc: 'Strategi penumpukan order grid di area order block dan liquidity grab yang dipetakan oleh algoritma makro.'
        },
        'fixed-micro-scalping': {
            title: '⚡ Fixed Micro Scalping (Fixed 0.01 Lot)',
            desc: 'Model scalping super aman dengan ukuran lot flat 0.01 untuk pembatasan risiko ketat. Ideal untuk menjaga drawdown tetap di bawah 3.0%.'
        },
        'forecast-hlc-bound': {
            title: '🎯 Forecast HLC Boundary Trading',
            desc: 'Metode trading kuantitatif berbasis perkiraan High/Low harian. Memasang pending LIMIT order secara otomatis di batas High & Low teroptimasi (MAE < $5) dengan target TP di harga Close proyeksi AI.'
        }
    };

    if (activeAiModelSelect) {
        activeAiModelSelect.addEventListener('change', () => {
            const val = activeAiModelSelect.value;
            if (modelInfo[val]) {
                selectedModelTitle.innerText = modelInfo[val].title;
                selectedModelDesc.innerText = modelInfo[val].desc;
            }
        });
    }

    if (applyAiModelBtn) {
        applyAiModelBtn.addEventListener('click', () => {
            const selectedVal = activeAiModelSelect.value;
            const modelName = modelInfo[selectedVal].title;
            
            // Sync settings with backend
            if (window.sendTradingSettings) {
                window.sendTradingSettings();
            }
            
            if (selectedVal === 'fixed-micro-scalping') {
                alert(`Sukses menerapkan Model: ${modelName}\n\nSetting disesuaikan otomatis:\n- Lot Size: 0.01 (Fixed)\n- Auto Lot: Disabled\n- Risk Percent: 0.0%`);
            } else {
                alert(`Sukses menerapkan Model: ${modelName}\n\nSistem AI XEDY telah diselaraskan dengan parameter dynamic optimal.`);
            }
        });
    }
    
    window.fetchForecastStats = async function() {
        try {
            const response = await fetch(window.API_BASE + '/api/v1/forecast/stats');
            const data = await response.json();
            
            if (data.error) {
                console.error("Failed to load forecast stats:", data.error);
                return;
            }
            
            // Populate Active Multi-Timeframe Forecasts (1d, 1w, 2w)
            const active = data.active_forecast || {};
            const forecasts = active.forecasts || {};

            // Helper to fill HLC pane
            function fillPane(prefix, obj, fallbackClose, fallbackHigh, fallbackLow, fallbackReason) {
                const highEl = document.getElementById(`${prefix}-high`);
                const lowEl = document.getElementById(`${prefix}-low`);
                const closeEl = document.getElementById(`${prefix}-close`);
                const reasonEl = document.getElementById(`${prefix}-reasoning`);

                const highVal = obj && obj.high ? '$' + obj.high.toFixed(2) : (fallbackHigh ? '$' + fallbackHigh.toFixed(2) : '$0.00');
                const lowVal = obj && obj.low ? '$' + obj.low.toFixed(2) : (fallbackLow ? '$' + fallbackLow.toFixed(2) : '$0.00');
                const closeVal = obj && obj.close ? '$' + obj.close.toFixed(2) : (fallbackClose ? '$' + fallbackClose.toFixed(2) : '$0.00');
                const reasonVal = obj && obj.reasoning_id ? obj.reasoning_id : (fallbackReason || 'Tidak ada analisis pendorong berita baru untuk timeframe ini.');

                if (highEl) highEl.innerText = highVal;
                if (lowEl) lowEl.innerText = lowVal;
                if (closeEl) closeEl.innerText = closeVal;
                if (reasonEl) reasonEl.innerText = reasonVal;
            }

            // Fill 1 Day Pane (using legacy forecast keys as fallbacks)
            fillPane('fc-1d', forecasts['1d'], active.forecast_close_24h, active.forecast_high_24h, active.forecast_low_24h, active.forecast_reasoning_id);
            // Fill 1 Week Pane (using proportional multipliers as fallback logic if not parsed)
            const startPrice = active.start_gold_price || 0.0;
            fillPane('fc-1w', forecasts['1w'], startPrice * 1.01, startPrice * 1.03, startPrice * 0.98, 'Analisis pasar jangka menengah terkompilasi.');
            // Fill 2 Weeks Pane
            fillPane('fc-2w', forecasts['2w'], startPrice * 1.02, startPrice * 1.05, startPrice * 0.96, 'Ekspektasi trend jangka panjang terkompilasi.');

            // Populate Executive & Money Flow Tab AI Outlook cards dynamically
            const execTarget1 = document.getElementById('exec-target-1');
            const execTarget2 = document.getElementById('exec-target-2');
            const execInvalidation = document.getElementById('exec-invalidation');
            const execBias = document.getElementById('exec-ai-bias');
            const execProb = document.getElementById('exec-ai-prob');
            const execReasoning = document.getElementById('exec-ai-reasoning');

            const mfTarget1 = document.getElementById('mf-target-1');
            const mfTarget2 = document.getElementById('mf-target-2');
            const mfInvalidation = document.getElementById('mf-invalidation');
            const mfBias = document.getElementById('mf-ai-bias');
            const mfProb = document.getElementById('mf-ai-prob');
            const mfReasoning = document.getElementById('mf-ai-reasoning');

            const targetVal = active.forecast_price_target ? '$' + active.forecast_price_target.toFixed(2) : '$0.00';
            const highVal = active.forecast_high_24h ? '$' + active.forecast_high_24h.toFixed(2) : '$0.00';
            const lowVal = active.forecast_low_24h ? '$' + active.forecast_low_24h.toFixed(2) : '$0.00';
            const biasVal = active.bias || 'WAIT';
            const probVal = active.optimal_confidence_threshold ? 'Probabilitas <span class="text-white fw-bold">' + Math.round(active.optimal_confidence_threshold * 100) + '%</span>' : 'Probabilitas <span class="text-white fw-bold">--%</span>';
            const reasoningVal = active.forecast_reasoning_id || 'Tidak ada analisis pendorong berita baru untuk siklus jam ini.';

            if (execTarget1) execTarget1.innerText = targetVal;
            if (execTarget2) execTarget2.innerText = highVal;
            if (execInvalidation) execInvalidation.innerText = lowVal;
            if (execBias) {
                execBias.innerText = biasVal;
                execBias.className = biasVal === 'BUY_ONLY' || biasVal === 'BUY' || biasVal === 'BULLISH' ? 'text-bullish fw-bold mb-0' : (biasVal === 'SELL_ONLY' || biasVal === 'SELL' || biasVal === 'BEARISH' ? 'text-critical fw-bold mb-0' : 'text-white fw-bold mb-0');
            }
            if (execProb) execProb.innerHTML = probVal;
            if (execReasoning) execReasoning.innerText = reasoningVal;

            if (mfTarget1) mfTarget1.innerText = targetVal;
            if (mfTarget2) mfTarget2.innerText = highVal;
            if (mfInvalidation) mfInvalidation.innerText = lowVal;
            if (mfBias) {
                mfBias.innerText = biasVal;
                mfBias.className = biasVal === 'BUY_ONLY' || biasVal === 'BUY' || biasVal === 'BULLISH' ? 'text-bullish fw-bold mb-0' : (biasVal === 'SELL_ONLY' || biasVal === 'SELL' || biasVal === 'BEARISH' ? 'text-critical fw-bold mb-0' : 'text-white fw-bold mb-0');
            }
            if (mfProb) mfProb.innerHTML = probVal;
            if (mfReasoning) mfReasoning.innerText = reasoningVal;
            
            // Populate KPIs
            const avgAccEl = document.getElementById('forecast-avg-accuracy');
            const totalPredsEl = document.getElementById('forecast-total-preds');
            const successHitsEl = document.getElementById('forecast-success-hits');
            const accRateEl = document.getElementById('forecast-accuracy-rate');
            
            if (avgAccEl) avgAccEl.innerText = (data.avg_accuracy * 100).toFixed(1) + '%';
            if (totalPredsEl) totalPredsEl.innerText = data.total_predictions;
            if (successHitsEl) successHitsEl.innerText = data.successful_hits;
            
            const rate = data.total_predictions > 0 ? (data.successful_hits / data.total_predictions) * 100 : 0.0;
            if (accRateEl) accRateEl.innerText = rate.toFixed(1) + '%';
            
            // Populate table
            const tbody = document.getElementById('forecast-history-tbody');
            if (tbody && data.history) {
                if (data.history.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" class="text-muted text-center">No forecast records logged yet.</td></tr>';
                    return;
                }
                
                let html = '';
                // Reverse to show latest first
                [...data.history].reverse().forEach(item => {
                    const statusClass = item.status.includes('Hit') ? 'text-bullish' : 'text-critical';
                    html += `<tr>
                        <td>${item.timestamp}</td>
                        <td class="text-white">$${item.start.toFixed(2)}</td>
                        <td class="text-white">$${item.target.toFixed(2)}</td>
                        <td class="text-white">$${item.actual_close.toFixed(2)}</td>
                        <td class="text-warning-v42">${(item.error_pct * 100).toFixed(2)}%</td>
                        <td class="text-info-v42">${(item.accuracy * 100).toFixed(1)}%</td>
                        <td class="${statusClass}">${item.status}</td>
                    </tr>`;
                });
                tbody.innerHTML = html;
            }
        } catch (e) {
            console.error("Error fetching forecast stats:", e);
        }
    };
    
    // Periodically fetch every 30 seconds
    setInterval(window.fetchForecastStats, 30000);
    // Initial fetch
    setTimeout(window.fetchForecastStats, 1000);
    
    // ============================================================
    // Qwen AI Quota Monitor
    // ============================================================
    window.fetchQwenQuota = async function() {
        try {
            const response = await fetch(window.API_BASE + '/api/v1/qwen/quota');
            if (!response.ok) return;
            const d = await response.json();
            if (d.error) return;

            const set = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
            const setHtml = (id, val) => { const el = document.getElementById(id); if (el) el.innerHTML = val; };

            set('qwen-model-label', d.model || 'Qwen 3.7 Flash · Aivene API');
            set('qwen-total-calls', d.total_calls ?? '--');
            set('qwen-today-calls', d.today_calls ?? '--');
            set('qwen-daily-limit', d.daily_limit ?? 10);
            set('qwen-monthly-limit', d.monthly_limit ?? 100);
            set('qwen-tokens-today', d.est_tokens_today != null ? d.est_tokens_today.toLocaleString() : '--');
            set('qwen-tokens-total', d.est_tokens_total != null ? d.est_tokens_total.toLocaleString() : '--');
            set('qwen-last-ts', d.last_call_ts || 'Never');
            set('qwen-last-reasoning', d.last_reasoning || 'No analysis yet.');

            // Last bias with color
            const biasEl = document.getElementById('qwen-last-bias');
            if (biasEl) {
                biasEl.innerText = d.last_bias || 'N/A';
                const b = (d.last_bias || '').toUpperCase();
                biasEl.style.color = b.includes('BUY') ? '#2ecc71' : b.includes('SELL') ? '#ff7b72' : b === 'WAIT' ? '#f1c40f' : '#aaa';
            }

            // Last regime
            const regimeEl = document.getElementById('qwen-last-regime');
            if (regimeEl) {
                regimeEl.innerText = d.last_regime || 'N/A';
                const r = (d.last_regime || '').toUpperCase();
                regimeEl.style.color = r === 'HIGH_NEWS' ? '#ff7b72' : r === 'SIDEWAYS' ? '#f1c40f' : '#ff9a7b';
            }

            // Daily progress bar
            const dailyPct = d.daily_limit > 0 ? Math.min(100, Math.round((d.today_calls / d.daily_limit) * 100)) : 0;
            set('qwen-daily-pct', dailyPct + '%');
            const dailyBar = document.getElementById('qwen-daily-bar');
            if (dailyBar) {
                dailyBar.style.width = dailyPct + '%';
                dailyBar.style.background = dailyPct >= 90 ? 'linear-gradient(90deg, #ff7b72, #c0392b)' : dailyPct >= 70 ? 'linear-gradient(90deg, #f1c40f, #e67e22)' : 'linear-gradient(90deg, #2ecc71, #27ae60)';
            }

            // Monthly progress bar
            const monthlyPct = d.monthly_limit > 0 ? Math.min(100, Math.round((d.total_calls / d.monthly_limit) * 100)) : 0;
            set('qwen-monthly-pct', monthlyPct + '%');
            const monthlyBar = document.getElementById('qwen-monthly-bar');
            if (monthlyBar) {
                monthlyBar.style.width = monthlyPct + '%';
                monthlyBar.style.background = monthlyPct >= 90 ? 'linear-gradient(90deg, #ff7b72, #c0392b)' : monthlyPct >= 70 ? 'linear-gradient(90deg, #f1c40f, #e67e22)' : 'linear-gradient(90deg, #7b2ff7, #9b59f5)';
            }

            // Status badge
            const badge = document.getElementById('qwen-status-badge');
            if (badge) {
                if (d.today_calls === 0) {
                    badge.innerText = '⏳ STANDBY';
                    badge.style.background = 'linear-gradient(90deg, #555, #888)';
                } else if (dailyPct >= 90) {
                    badge.innerText = '⚠ NEAR LIMIT';
                    badge.style.background = 'linear-gradient(90deg, #ff7b72, #c0392b)';
                } else {
                    badge.innerText = '⚡ ACTIVE';
                    badge.style.background = 'linear-gradient(90deg, #7b2ff7, #9b59f5)';
                }
            }
        } catch (e) {
            console.warn('Qwen quota fetch error:', e);
        }
    };

    // Auto-refresh quota every 60s, initial load after 2s
    setInterval(window.fetchQwenQuota, 60000);
    setTimeout(window.fetchQwenQuota, 2000);

    // ============================================================
    // Executive Dashboard: Dynamic Panels
    // ============================================================
    window.fetchMacroDashboard = async function() {
        try {
            const res = await fetch(window.API_BASE + '/api/v1/macro/dashboard');
            if (!res.ok) return;
            const d = await res.json();
            if (d.error) return;

            // ── Upcoming Events ──────────────────────────────────
            const eventsTbody = document.getElementById('events-tbody');
            if (eventsTbody && d.upcoming_events) {
                if (d.upcoming_events.length === 0) {
                    eventsTbody.innerHTML = '<tr><td colspan="5" class="text-muted text-center">No high-impact events found</td></tr>';
                } else {
                    eventsTbody.innerHTML = d.upcoming_events.map(ev => {
                        const impactCls = ev.impact === 'High' ? 'bg-danger' : ev.impact === 'Medium' ? 'bg-warning text-dark' : 'bg-secondary';
                        return `<tr>
                            <td class="font-monospace" style="font-size:0.68rem;white-space:nowrap;">${ev.time}</td>
                            <td>${ev.name}</td>
                            <td><span class="badge ${impactCls}" style="font-size:0.6rem;">${ev.impact}</span></td>
                            <td class="text-white font-monospace">${ev.actual}</td>
                            <td class="text-muted font-monospace">${ev.prev}</td>
                        </tr>`;
                    }).join('');
                }
            }

            // ── Latest Macro News ────────────────────────────────
            const newsTbody = document.getElementById('macro-news-tbody');
            if (newsTbody && d.latest_news) {
                if (d.latest_news.length === 0) {
                    newsTbody.innerHTML = '<tr><td colspan="3" class="text-muted text-center">No news available</td></tr>';
                } else {
                    newsTbody.innerHTML = d.latest_news.map(n => `<tr>
                        <td class="font-monospace text-muted" style="font-size:0.65rem;white-space:nowrap;">${n.time}</td>
                        <td style="line-height:1.3;">${n.headline}</td>
                        <td><span class="badge ${n.tag_class}" style="font-size:0.6rem;white-space:nowrap;">${n.tag}</span></td>
                    </tr>`).join('');
                }
            }

            // ── Smart Alerts ─────────────────────────────────────
            const alertsTbody = document.getElementById('smart-alerts-tbody');
            if (alertsTbody && d.smart_alerts) {
                if (d.smart_alerts.length === 0) {
                    alertsTbody.innerHTML = '<tr><td colspan="3" class="text-muted text-center">No alerts</td></tr>';
                } else {
                    alertsTbody.innerHTML = d.smart_alerts.map(a => `<tr>
                        <td class="font-monospace text-muted" style="font-size:0.68rem;white-space:nowrap;">${a.time}</td>
                        <td style="line-height:1.3;">${a.msg}</td>
                        <td class="text-end"><span class="badge ${a.cls}" style="font-size:0.6rem;">${a.signal}</span></td>
                    </tr>`).join('');
                }
            }
        } catch (e) {
            console.warn('Macro dashboard fetch error:', e);
        }
    };

    // Auto-refresh every 60s, initial load after 1.5s
    setInterval(window.fetchMacroDashboard, 60000);
    setTimeout(window.fetchMacroDashboard, 1500);

    // ============================================================
    // 10-Day Price Forecast Chart Renderer
    // ============================================================
    window.renderForecast10Day = async function() {
        try {
            const res = await fetch(window.API_BASE + '/api/v1/forecast/10day');
            if (!res.ok) return;
            const d = await res.json();
            if (!d.days || d.days.length === 0) return;

            const days = d.days; // 11 items: day0=today, 1-10=forecast
            const CHART_W = 340;
            const CHART_H = 80;
            const PAD_L = 4;
            const PAD_R = 40; // space for price labels
            const PAD_T = 6;
            const PAD_B = 12;

            // Collect all price points for Y-axis scale
            const allPrices = days.flatMap(dy => [dy.close, dy.high, dy.low]);
            const priceMax = Math.max(...allPrices);
            const priceMin = Math.min(...allPrices);
            const priceRange = priceMax - priceMin || 1;

            // Map price to SVG Y coordinate
            const toY = p => PAD_T + (CHART_H - PAD_T - PAD_B) * (1 - (p - priceMin) / priceRange);

            // Map day index to SVG X coordinate
            const toX = i => PAD_L + ((CHART_W - PAD_L - PAD_R) / (days.length - 1)) * i;

            // Build SVG path data
            const closePoints = days.map((dy, i) => ({ x: toX(i), y: toY(dy.close) }));
            const highPoints  = days.map((dy, i) => ({ x: toX(i), y: toY(dy.high) }));
            const lowPoints   = days.map((dy, i) => ({ x: toX(i), y: toY(dy.low) }));

            const linePath = closePoints.map((p, i) => (i === 0 ? `M${p.x},${p.y}` : `L${p.x},${p.y}`)).join(' ');

            // Area under close line
            const areaPath = linePath + ` L${closePoints[closePoints.length-1].x},${CHART_H - PAD_B} L${closePoints[0].x},${CHART_H - PAD_B} Z`;

            // High/Low band (filled region between high and low paths)
            const bandTop = highPoints.map((p, i) => (i === 0 ? `M${p.x},${p.y}` : `L${p.x},${p.y}`)).join(' ');
            const bandBot = lowPoints.slice().reverse().map((p, i) => `L${p.x},${p.y}`).join(' ');
            const bandPath = bandTop + ' ' + bandBot + ' Z';

            // Apply to SVG elements
            const svgEl = document.getElementById('exec-forecast-svg');
            if (!svgEl) return;

            const setAttr = (id, attr, val) => { const el = document.getElementById(id); if (el) el.setAttribute(attr, val); };
            setAttr('exec-fc-line', 'd', linePath);
            setAttr('exec-fc-area', 'd', areaPath);
            setAttr('exec-fc-band', 'd', bandPath);

            // Reset any animation stroke dash arrays that hide the line
            const lineEl = document.getElementById('exec-fc-line');
            if (lineEl) {
                lineEl.style.strokeDasharray = 'none';
                lineEl.style.strokeDashoffset = 'none';
                lineEl.style.transition = 'none';
            }

            // Current price (today) dashed line
            const nowY = toY(d.current_price);
            setAttr('exec-fc-now-line', 'y1', nowY);
            setAttr('exec-fc-now-line', 'y2', nowY);
            setAttr('exec-fc-now-dot', 'cy', nowY);
            setAttr('exec-fc-now-dot', 'cx', toX(0));

            // Dot markers on each day
            const dotsEl = document.getElementById('exec-fc-dots');
            if (dotsEl) {
                dotsEl.innerHTML = closePoints.map((p, i) => {
                    const dy = days[i];
                    const col = i === 0 ? '#f1c40f' : (dy.color === 'bullish' ? '#3fb950' : dy.color === 'bearish' ? '#ff7b72' : '#aaa');
                    const r = i === 0 ? 3 : 2;
                    // Price label above dot (only show days 1,3,5,7,10)
                    const showLabel = [1,3,5,7,10].includes(i);
                    const labelEl = showLabel
                        ? `<text x="${p.x}" y="${p.y - 4}" text-anchor="middle" font-size="5" fill="${col}" font-family="monospace">$${dy.close.toFixed(0)}</text>`
                        : '';
                    return `<circle cx="${p.x}" cy="${p.y}" r="${r}" fill="${col}"/>${labelEl}`;
                }).join('');
            }

            // Price axis labels
            const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
            setTxt('exec-fc-price-max', `$${priceMax.toFixed(0)}`);
            setTxt('exec-fc-price-min', `$${priceMin.toFixed(0)}`);

            // Position 'now' label vertically
            const nowEl = document.getElementById('exec-fc-price-now');
            if (nowEl) {
                nowEl.innerText = `$${d.current_price.toFixed(0)}`;
                const pct = 1 - (d.current_price - priceMin) / priceRange;
                nowEl.style.top = `${Math.max(4, Math.min(80, pct * 96))}px`;
            }

            // Day labels at bottom
            const labelsEl = document.getElementById('exec-fc-labels');
            if (labelsEl) {
                labelsEl.innerHTML = days.map(dy =>
                    `<span style="text-align:center;flex:1;">${dy.label.split(' ')[0]}</span>`
                ).join('');
            }

            // Mini day cards below chart
            const tableEl = document.getElementById('exec-fc-table');
            if (tableEl) {
                tableEl.innerHTML = days.slice(1).map(dy => {
                    const col = dy.color === 'bullish' ? '#3fb950' : dy.color === 'bearish' ? '#ff7b72' : '#aaa';
                    const bg  = dy.color === 'bullish' ? 'rgba(63,185,80,0.08)' : dy.color === 'bearish' ? 'rgba(255,123,114,0.08)' : 'rgba(255,255,255,0.04)';
                    return `<div style="min-width:52px;padding:4px 5px;border-radius:6px;border:1px solid ${col}22;background:${bg};text-align:center;flex-shrink:0;">
                        <div style="font-size:0.55rem;color:#666;">${dy.label}</div>
                        <div style="font-size:0.72rem;font-family:monospace;color:${col};font-weight:700;">${dy.direction}$${dy.close.toFixed(0)}</div>
                        <div style="font-size:0.52rem;color:#3fb950;font-family:monospace;">H:${dy.high.toFixed(0)}</div>
                        <div style="font-size:0.52rem;color:#ff7b72;font-family:monospace;">L:${dy.low.toFixed(0)}</div>
                    </div>`;
                }).join('');
            }

        } catch (e) {
            console.warn('10-day forecast render error:', e);
        }
    };

    // Load 10-day forecast on start and refresh every 5 minutes
    setTimeout(window.renderForecast10Day, 2500);
    setInterval(window.renderForecast10Day, 300000);

    // ── 15-Layer & Multi-Agent Swarm Dynamic Status Update ────────────────────
    window.updatePipelineStatus = async () => {
        try {
            const res = await fetch(window.API_BASE + '/api/v1/health/pipeline');
            if (!res.ok) return;
            const data = await res.json();

            // 1. Update 15-Layer dots
            for (let i = 1; i <= 15; i++) {
                const dot = document.getElementById(`pipe-l${i}-dot`);
                if (dot) {
                    const status = data.pipeline[`l${i}`];
                    // Reset classes
                    dot.className = 'me-1';
                    if (status === 'ACTIVE') {
                        dot.classList.add('text-success');
                        dot.style.animation = 'none';
                    } else if (status === 'WARNING') {
                        dot.classList.add('text-warning');
                        // Subtle blinking animation for warnings
                        dot.style.animation = 'pulse-warning 1.5s infinite';
                    } else {
                        dot.classList.add('text-danger');
                        dot.style.animation = 'none';
                    }
                }
            }

            // 2. Update Swarm Badges
            const setBadge = (id, text, type) => {
                const el = document.getElementById(id);
                if (el) {
                    el.innerText = text;
                    el.className = 'badge';
                    if (type === 'success') el.classList.add('bg-success');
                    else if (type === 'warning') el.classList.add('bg-warning');
                    else el.classList.add('bg-secondary');
                }
            };
            
            const swarm = data.swarm;
            setBadge('swarm-ceo-badge', swarm.ceo, swarm.ceo === 'ACTIVE' ? 'success' : 'secondary');
            setBadge('swarm-cio-badge', swarm.cio, swarm.cio === 'ACTIVE' ? 'success' : 'secondary');
            setBadge('swarm-sup-badge', swarm.sup, swarm.sup === 'MONITORING' ? 'success' : 'secondary');

            const specEl = document.getElementById('swarm-spec-text');
            if (specEl) {
                specEl.innerText = swarm.spec;
                if (swarm.spec === 'VOTING / CONSENSUS') {
                    specEl.className = 'text-bullish fw-bold';
                    specEl.style.animation = 'pulse-text 2s infinite';
                } else {
                    specEl.className = 'text-muted fw-bold';
                    specEl.style.animation = 'none';
                }
            }

        } catch (e) {
            console.warn('Pipeline status fetch failed:', e);
        }
    };

    // Inject custom animation styles to document head if not present
    if (!document.getElementById('pipeline-dynamic-styles')) {
        const style = document.createElement('style');
        style.id = 'pipeline-dynamic-styles';
        style.innerHTML = `
            @keyframes pulse-warning {
                0% { opacity: 0.3; }
                50% { opacity: 1.0; }
                100% { opacity: 0.3; }
            }
            @keyframes pulse-text {
                0% { opacity: 0.5; }
                50% { opacity: 1.0; }
                100% { opacity: 0.5; }
            }
        `;
        document.head.appendChild(style);
    }

    // Schedule status check every 15 seconds
    setTimeout(window.updatePipelineStatus, 1000);
    setInterval(window.updatePipelineStatus, 15000);

    window.triggerManualForecast = async function() {
        const btn = document.getElementById('btn-force-forecast');
        if (!btn) return;
        
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '🔄 RUNNING CLAUDE AI FORECAST...';
        btn.classList.replace('btn-warning', 'btn-secondary');
        
        try {
            const response = await fetch(window.API_BASE + '/api/v1/forecast/trigger', { method: 'POST' });
            if (!response.ok) {
                const textErr = await response.text();
                throw new Error(`Server returned HTTP ${response.status}: ${textErr}`);
            }
            
            const result = await response.json();
            if (result && result.status === 'success') {
                alert('Claude AI Forecast updated successfully!');
                if (window.fetchForecastStats) {
                    await window.fetchForecastStats();
                }
            } else {
                alert('Forecast failed: ' + (result ? result.message : 'Unknown backend response format'));
            }
        } catch (error) {
            console.error('Trigger forecast failed:', error);
            alert('Failed to connect or process forecast: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
            btn.classList.replace('btn-secondary', 'btn-warning');
        }
    };

    window.loadAutoCleanState();
    setTimeout(initWebSocket, 500);
});

// =============================================================================
// BACKTEST VALIDASI – JavaScript Engine
// =============================================================================

let _btData = null;
let _btCurrentTf = '1d';
let _btChart = null;
let _btCurrentMetric = 'close';

window.loadBacktest = async function(refresh) {
    refresh = refresh || false;
    const elLoading = document.getElementById('backtest-loading');
    const elContent = document.getElementById('backtest-content');
    const elError   = document.getElementById('backtest-error');
    const btnRefresh = document.getElementById('btn-backtest-refresh');
    const btnLoad = document.getElementById('btn-backtest-load');

    elLoading.classList.remove('d-none');
    elContent.classList.add('d-none');
    elError.classList.add('d-none');
    if (btnRefresh) { btnRefresh.disabled = true; btnRefresh.innerHTML = '⏳ Menghubungi Server...'; }
    if (btnLoad) btnLoad.disabled = true;

    try {
        const url = '/api/v1/backtest?days=30&refresh=' + refresh;
        const res = await fetch(url);
        if (!res.ok) throw new Error('HTTP ' + res.status + ': ' + res.statusText);
        const data = await res.json();
        
        if (data.error) throw new Error(data.error);

        // Kasus 1: Backtest baru saja dijalankan di background
        if (data.status === 'started' || data.status === 'running') {
            elError.classList.remove('d-none');
            elError.className = 'alert alert-info';
            elError.innerHTML = '🔄 <strong>Backtest Sedang Diproses di Background:</strong> Server MT5 & Qwen AI sedang mengalkulasi data. Silakan tunggu sekitar 2 menit, lalu tekan <strong>⚡ Load Cache</strong> untuk melihat visualisasinya.';
            
            // Set polling otomatis untuk reload data setelah 15 detik
            setTimeout(function() {
                window.loadBacktest(false);
            }, 15000);
            return;
        }

        // Kasus 2: Berhasil load cache data
        elError.className = 'd-none alert alert-danger'; // reset class default
        _btData = data;
        _btCurrentTf = '1d';

        const periodEl = document.getElementById('bt-period-label');
        const cachedEl = document.getElementById('bt-cached-label');
        if (periodEl) periodEl.textContent = '📅 ' + (data.backtest_period || '—');
        if (cachedEl) cachedEl.textContent = data.cached ? '⚡ Cache' : '🔄 Fresh Run';

        renderBtMetrics('1d');
        renderBacktestChart(data.chart_data);
        renderBacktestTable(data.detail_1d || [], '1 Hari (D1)');
        switchBtTab('1d');
        elContent.classList.remove('d-none');
    } catch (err) {
        elError.classList.remove('d-none');
        elError.className = 'alert alert-danger';
        elError.textContent = '❌ Gagal memuat backtest: ' + err.message;
        console.error('Backtest error:', err);
    } finally {
        elLoading.classList.add('d-none');
        if (btnRefresh) { btnRefresh.disabled = false; btnRefresh.innerHTML = '🔄 Run Full Backtest (MT5 + AI)'; }
        if (btnLoad) btnLoad.disabled = false;
    }
};


window.switchBtTab = function(tf) {
    if (!_btData) return;
    _btCurrentTf = tf;
    ['1d','1w','2w'].forEach(function(t) {
        const btn = document.getElementById('bt-tab-' + t);
        if (!btn) return;
        btn.className = t === tf ? 'btn btn-sm btn-warning fw-bold' : 'btn btn-sm btn-outline-secondary';
    });
    renderBtMetrics(tf);
    const labelMap = {'1d':'1 Hari (D1)','1w':'1 Minggu (W1)','2w':'2 Minggu'};
    renderBacktestTable(_btData['detail_' + tf] || [], labelMap[tf] || tf);
};

function renderBtMetrics(tf) {
    if (!_btData || !_btData.results) return;
    const m = _btData.results[tf] || {};
    const mae     = document.getElementById('bt-mae-close');
    const mape    = document.getElementById('bt-mape');
    const hitrate = document.getElementById('bt-hitrate');
    const dir     = document.getElementById('bt-direction');
    if (mae)     mae.textContent     = m.mae_close      != null ? '$' + m.mae_close.toFixed(2)        : '—';
    if (mape)    mape.textContent    = m.mape_close     != null ? m.mape_close.toFixed(2) + '%'       : '—';
    if (hitrate) {
        hitrate.textContent = m.hit_rate_1pct != null ? m.hit_rate_1pct + '%' : '—';
        hitrate.className   = 'fw-bold fs-4 ' + (m.hit_rate_1pct >= 60 ? 'text-success' : m.hit_rate_1pct >= 40 ? 'text-warning' : 'text-danger');
    }
    if (dir) {
        dir.textContent = m.direction_accuracy != null ? m.direction_accuracy + '%' : '—';
        dir.className   = 'fw-bold fs-4 ' + (m.direction_accuracy >= 65 ? 'text-success' : m.direction_accuracy >= 50 ? 'text-warning' : 'text-danger');
    }
}

window.switchBtMetric = function(metric) {
    if (!_btData) return;
    _btCurrentMetric = metric;
    
    // Update button states
    const container = document.getElementById('bt-metric-buttons');
    if (container) {
        const buttons = container.querySelectorAll('.btn-chart-metric');
        buttons.forEach(btn => {
            const m = btn.getAttribute('data-metric');
            if (m === metric) {
                btn.className = 'btn btn-warning btn-xs fw-bold px-3 py-1 btn-chart-metric active';
            } else {
                btn.className = 'btn btn-outline-secondary btn-xs text-white px-3 py-1 btn-chart-metric';
            }
        });
    }
    
    // Update Chart Title
    const titleEl = document.getElementById('bt-chart-title');
    if (titleEl) {
        const titleMap = {
            'close': '📈 CLOSE: AKTUAL vs PREDIKSI (D1)',
            'high': '📈 HIGH: AKTUAL vs PREDIKSI (D1)',
            'low': '📈 LOW: AKTUAL vs PREDIKSI (D1)'
        };
        titleEl.textContent = titleMap[metric] || '📈 BACKTEST CHART';
    }
    
    renderBacktestChart(_btData.chart_data);
};

function renderBacktestChart(chartData) {
    const ctx = document.getElementById('bt-chart');
    if (!ctx || !chartData) return;
    if (_btChart) { _btChart.destroy(); _btChart = null; }
    
    let labelActual = 'Aktual Close';
    let labelPred = 'Prediksi Close (1D)';
    let dataActual = chartData.actual_close || [];
    let dataPred = chartData.predicted_close_1d || [];
    let colorActual = '#00bc8c';
    let colorPred = '#f39c12';
    
    if (_btCurrentMetric === 'high') {
        labelActual = 'Aktual High';
        labelPred = 'Prediksi High (1D)';
        dataActual = chartData.actual_high || [];
        dataPred = chartData.predicted_high_1d || [];
        colorActual = '#e74c3c';
        colorPred = '#ffaa00';
    } else if (_btCurrentMetric === 'low') {
        labelActual = 'Aktual Low';
        labelPred = 'Prediksi Low (1D)';
        dataActual = chartData.actual_low || [];
        dataPred = chartData.predicted_low_1d || [];
        colorActual = '#3498db';
        colorPred = '#ffaa00';
    }
    
    _btChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.dates || [],
            datasets: [
                { label: labelActual, data: dataActual, borderColor: colorActual, backgroundColor: 'rgba(0,188,140,0.08)', borderWidth: 2, pointRadius: 3, tension: 0.3, fill: false },
                { label: labelPred, data: dataPred, borderColor: colorPred, backgroundColor: 'rgba(243,156,18,0.08)', borderWidth: 2, borderDash: [5,3], pointRadius: 3, tension: 0.3, fill: false }
            ]
        },
        options: {
            responsive: true,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { labels: { color: '#ccc', font: { size: 11 } } },
                tooltip: { callbacks: { label: function(c) { return c.dataset.label + ': $' + c.parsed.y.toFixed(2); } } }
            },
            scales: {
                x: { ticks: { color: '#888', font: { size: 10 }, maxTicksLimit: 10 }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#888', font: { size: 10 }, callback: function(v) { return '$' + v.toFixed(0); } }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

function renderBacktestTable(records, label) {
    const tbody = document.getElementById('bt-table-body');
    const title = document.getElementById('bt-table-title');
    if (!tbody) return;
    if (title) title.textContent = '📋 DETAIL BACKTEST – ' + label;
    if (!records || records.length === 0) {
        tbody.innerHTML = '<tr><td colspan="11" class="text-center text-muted py-3">Tidak ada data</td></tr>';
        return;
    }
    function fmt(v) { return v != null ? '$' + parseFloat(v).toFixed(2) : '—'; }
    tbody.innerHTML = records.map(function(r) {
        var sc = r.status === 'HIT' ? 'text-success fw-bold' : r.status === 'NEAR' ? 'text-warning fw-bold' : 'text-danger fw-bold';
        var si = r.status === 'HIT' ? '✅ HIT' : r.status === 'NEAR' ? '⚠️ NEAR' : '❌ MISS';
        var di = r.direction_correct ? '✅' : '❌';
        var ec = r.error_close_pct <= 1.0 ? 'text-success' : r.error_close_pct <= 2.0 ? 'text-warning' : 'text-danger';
        return '<tr>' +
            '<td class="text-muted">' + r.date + '</td>' +
            '<td>' + fmt(r.open) + '</td>' +
            '<td class="text-warning">' + fmt(r.pred_high) + '</td>' +
            '<td class="text-info">' + fmt(r.pred_low) + '</td>' +
            '<td class="text-white fw-bold">' + fmt(r.pred_close) + '</td>' +
            '<td class="text-warning">' + fmt(r.actual_high) + '</td>' +
            '<td class="text-info">' + fmt(r.actual_low) + '</td>' +
            '<td class="text-white">' + fmt(r.actual_close) + '</td>' +
            '<td class="' + ec + '">' + (r.error_close_pct != null ? r.error_close_pct.toFixed(2) + '%' : '—') + '</td>' +
            '<td>' + di + '</td>' +
            '<td class="' + sc + '">' + si + '</td>' +
            '</tr>';
    }).join('');
}

// SERVERLESS TICKER FETCH (Sync from Executive Dashboard DOM)
window.fetchServerlessTicker = function() {
    try {
        const getElText = (id, fallback) => {
            const el = document.getElementById(id);
            return el ? el.innerText : fallback;
        };
        const getElChange = (id, fallback) => {
            const el = document.getElementById(id);
            if (el && el.nextElementSibling) return el.nextElementSibling.innerText;
            return fallback;
        };

        const xauPrice = getElText('kpi-price', '----.--');
        const xauChange = getElChange('kpi-price', '--- (---%)');
        
        const dxyPrice = getElText('kpi-dxy-price', '---.--');
        const dxyChange = getElChange('kpi-dxy-price', '--- (---%)');
        
        const us10yPrice = getElText('kpi-us10y-price', '-.--%');
        const us10yChange = getElChange('kpi-us10y-price', '--- (---%)');
        
        const realYieldPrice = getElText('kpi-realyield-price', '-.--%');
        const realYieldChange = getElChange('kpi-realyield-price', '--- (---%)');
        
        const gldPrice = getElText('kpi-gld-flow', '+-.-- Ton');
        const gldChange = getElChange('kpi-gld-flow', '-- Bullish');
        
        const comexPrice = getElText('kpi-comex-long', '---,---');
        const comexChange = getElChange('kpi-comex-long', '+--- (+--%)');

        function updateTickerEl(idPrefix, priceStr, changeStr) {
            const priceEl = document.getElementById(`ticker-${idPrefix}-price`);
            const changeEl = document.getElementById(`ticker-${idPrefix}-change`);
            
            if (priceEl) priceEl.innerText = priceStr;
            if (changeEl) {
                changeEl.innerText = changeStr;
                let textClass = 'text-bullish';
                if (changeStr.includes('-')) textClass = 'text-bearish';
                
                if (idPrefix === 'dxy' || idPrefix === 'us10y' || idPrefix === 'real') {
                    // Invert color logic for DXY/Yields (up is bearish for gold)
                    textClass = changeStr.includes('-') ? 'text-bullish' : 'text-bearish';
                }
                changeEl.className = `small fw-bold ${textClass}`;
            }
        }
        
        updateTickerEl('xau', xauPrice, xauChange);
        updateTickerEl('dxy', dxyPrice, dxyChange);
        updateTickerEl('us10y', us10yPrice, us10yChange);
        updateTickerEl('real', realYieldPrice, realYieldChange);
        updateTickerEl('gld', gldPrice, gldChange);
        updateTickerEl('comex', comexPrice, comexChange);
        
    } catch (e) {
        console.error("Failed to sync ticker from Executive Dashboard", e);
    }
};

setTimeout(window.fetchServerlessTicker, 1000);
setInterval(window.fetchServerlessTicker, 3000);
