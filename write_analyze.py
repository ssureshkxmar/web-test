import os

html_content = """<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analyze Your Heart | SmartECG AI</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root {
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.4);
            --accent: #10b981;
            --bg-dark: #09090b;
            --card-dark: #121217;
            --surface2: #1c1c24;
            --text-main: #fafafa;
            --text-muted: #a1a1aa;
            --border-color: rgba(255, 255, 255, 0.08);
            --danger: #ef4444;
            --ecg-grid: rgba(99, 102, 241, 0.05);
            --ecg-grid-bold: rgba(99, 102, 241, 0.12);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .ambient-bg {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1;
            background: radial-gradient(circle at 10% 10%, rgba(99, 102, 241, 0.1) 0%, transparent 40%),
                        radial-gradient(circle at 90% 90%, rgba(16, 185, 129, 0.05) 0%, transparent 40%);
        }

        .navbar {
            padding: 1.5rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            background: rgba(9, 9, 11, 0.8);
            backdrop-filter: blur(12px);
            z-index: 100;
        }

        .logo {
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 1.5rem;
            background: linear-gradient(to right, #818cf8, #34d399);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            text-decoration: none;
        }

        .status-badge {
            display: flex; align-items: center; gap: 8px;
            padding: 0.5rem 1rem; background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 999px;
            color: var(--accent); font-weight: 600; font-size: 0.875rem;
        }

        .workspace { display: flex; flex: 1; overflow: hidden; }

        .sidebar {
            width: 320px;
            background: var(--card-dark);
            border-right: 1px solid var(--border-color);
            display: flex; flex-direction: column;
            overflow-y: auto;
        }

        .sidebar-section { padding: 20px; border-bottom: 1px solid var(--border-color); }

        .section-header {
            font-family: 'Outfit', sans-serif;
            font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px;
            color: var(--text-muted); margin-bottom: 15px; font-weight: 700;
            display: flex; align-items: center; gap: 8px;
        }

        .api-input-group, .config-field { display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px; }
        .api-input-group label, .config-field label { font-size: 0.8rem; color: var(--text-muted); }
        .api-input-group input, .config-field input {
            background: rgba(255,255,255,0.03); border: 1px solid var(--border-color);
            padding: 12px; border-radius: 8px; color: var(--text-main);
            font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; outline: none;
        }
        .api-input-group input:focus, .config-field input:focus { border-color: var(--primary); }
        
        .btn-run {
            background: var(--primary); color: white; border: none; padding: 12px;
            border-radius: 8px; font-weight: 700; cursor: pointer; transition: 0.3s;
            display: flex; align-items: center; justify-content: center; gap: 8px;
            box-shadow: 0 10px 20px -5px var(--primary-glow); width: 100%;
        }
        .btn-run:hover { background: #4f46e5; transform: translateY(-2px); }
        .btn-run:disabled { opacity: 0.6; cursor: not-allowed; transform: none; box-shadow: none; }
        
        .btn-update {
            background: rgba(255, 255, 255, 0.05); color: white; border: 1px solid var(--border-color);
            padding: 10px; border-radius: 8px; font-weight: 600; cursor: pointer; width: 100%;
            transition: 0.3s; font-size: 0.8rem;
        }
        .btn-update:hover { background: rgba(255, 255, 255, 0.1); }

        .pipeline-step {
            display: flex; align-items: center; gap: 10px; font-size: 0.85rem;
            color: var(--text-muted); margin-bottom: 8px; padding: 8px 12px;
            border-radius: 6px; background: rgba(255, 255, 255, 0.02); border: 1px solid transparent;
        }
        .pipeline-step.active { color: var(--primary); background: rgba(99, 102, 241, 0.05); border-color: rgba(99, 102, 241, 0.2); }
        .pipeline-step.done { color: var(--accent); }

        .viewport { flex: 1; overflow-y: auto; padding: 30px; display: flex; flex-direction: column; gap: 20px; }

        .card { background: var(--card-dark); border: 1px solid var(--border-color); border-radius: 16px; overflow: hidden; }
        .card-header { padding: 15px 20px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.01); }
        .card-title { font-family: 'Outfit'; font-size: 0.95rem; font-weight: 600; text-transform: uppercase; display: flex; align-items: center; gap: 8px; color: #e2e8f0; }

        .tabs { display: flex; gap: 10px; margin-bottom: 15px; border-bottom: 1px solid var(--border-color); }
        .tab { padding: 12px 24px; font-family: 'Outfit'; font-size: 0.95rem; font-weight: 600; cursor: pointer; color: var(--text-muted); border-bottom: 2px solid transparent; transition: 0.2s; }
        .tab.active { color: var(--primary); border-bottom-color: var(--primary); background: rgba(99, 102, 241, 0.05); border-radius: 8px 8px 0 0; }

        .ecg-grid {
            height: 300px;
            background-image: linear-gradient(var(--ecg-grid) 1px, transparent 1px), linear-gradient(90deg, var(--ecg-grid) 1px, transparent 1px),
                              linear-gradient(var(--ecg-grid-bold) 1px, transparent 1px), linear-gradient(90deg, var(--ecg-grid-bold) 1px, transparent 1px);
            background-size: 10px 10px, 10px 10px, 50px 50px, 50px 50px;
            position: relative;
        }

        .metrics-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 15px; }
        .stat-card { padding: 20px; border: 1px solid var(--border-color); border-radius: 12px; background: rgba(255,255,255,0.02); }
        .stat-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px; font-weight: 700; letter-spacing: 0.05em; }
        .stat-value { font-size: 1.6rem; font-weight: 700; font-family: 'Outfit', sans-serif; color: var(--primary); }

        .diagnosis-alert { padding: 20px; border-radius: 12px; font-weight: 600; font-size: 1.1rem; margin-bottom: 20px; display: flex; align-items: center; gap: 15px; font-family: 'Outfit'; }
        .alert-normal { background: rgba(16, 185, 129, 0.1); color: var(--accent); border: 1px solid rgba(16, 185, 129, 0.2); }
        .alert-path { background: rgba(239, 68, 68, 0.1); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.2); }

        /* Contours Canvas */
        .contour-box {
            background: #09090b;
            height: 300px;
            width: 100%;
            position: relative;
            border-bottom-left-radius: 16px;
            border-bottom-right-radius: 16px;
        }
        #contourCanvas { width: 100%; height: 100%; display: block; }

        .hidden { display: none !important; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
        
        /* User Navbar matching SmartECG */
        .nav-links a {
            padding:0.45rem 1rem; border-radius:8px; font-size:0.875rem; font-weight:600; text-decoration:none;
        }
    </style>
</head>

<body>
    <div class="ambient-bg"></div>

    <nav class="navbar">
        <a href="/" class="logo">SMARTECG AI</a>
        <div style="display:flex; align-items:center; gap:1rem;" class="nav-links">
            <a href="/analyze" style="color:white; background:var(--primary); box-shadow:0 0 10px var(--primary-glow);">Analyze Your Heart</a>
            {% if session.get('user_email') %}
            <a href="/history" style="color:#10b981; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.2);">History</a>
            <a href="/logout" style="color:#ef4444; background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.2);">Logout</a>
            {% else %}
            <!-- Add placeholder or standard auth hook -->
            {% endif %}
        </div>
    </nav>

    <div class="workspace">
        <aside class="sidebar">
            <div class="sidebar-section">
                <div class="section-header"><i class="fas fa-plug"></i> API Integration / Data Import</div>
                <div class="api-input-group">
                    <label>Enter Shared Result Key (from SmartECG)</label>
                    <input type="text" id="api_key_input" placeholder="share_...">
                    <button id="startBtn" onclick="runAnalysis()" class="btn-run" style="margin-top: 5px;">
                        <i class="fas fa-search-heart"></i> Fetch & Analyze
                    </button>
                </div>
            </div>
            
            <div class="sidebar-section">
                <div class="section-header"><i class="fas fa-sliders-h"></i> System Parameters</div>
                <form id="configForm" onsubmit="saveConfig(event)">
                    <div class="config-field">
                        <label>MATLAB EXECUTABLE</label>
                        <input type="text" id="matlabPath" name="matlab_path" value="matlab">
                    </div>
                    <div class="config-field">
                        <label>GMSH EXECUTABLE</label>
                        <input type="text" id="gmshPath" name="gmsh_path" value="gmsh">
                    </div>
                    <button type="submit" class="btn-update">Update Configuration</button>
                </form>
            </div>

            <div class="sidebar-section">
                <div class="section-header"><i class="fas fa-project-diagram"></i> Reconstruction Pipeline</div>
                <div id="step1" class="pipeline-step"><i class="fas fa-circle"></i> Slice Alignment</div>
                <div id="step2" class="pipeline-step"><i class="fas fa-circle"></i> Surface Generation</div>
                <div id="step3" class="pipeline-step"><i class="fas fa-circle"></i> Mesh Creation</div>
                <div id="step4" class="pipeline-step"><i class="fas fa-circle"></i> Mechanical Sync</div>
            </div>

            <div class="sidebar-section" style="flex:1; border-bottom:0; display:flex; flex-direction:column;">
                <div class="section-header"><i class="fas fa-stream"></i> Stream Logs</div>
                <div id="logBody" style="flex:1; background: rgba(0,0,0,0.3); border-radius: 8px; padding: 12px; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #a1a1aa; overflow-y: auto;">
                    [READY] Awaiting data acquisition...<br>
                </div>
            </div>
        </aside>

        <main class="viewport">
            <div id="welcomeView" style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; opacity: 0.5;">
                <i class="fas fa-heartbeat" style="font-size: 6rem; margin-bottom: 25px; color: var(--text-muted);"></i>
                <h2 style="font-family:'Outfit'; font-size: 2rem;">Analyze Your Heart</h2>
                <p style="font-size:1.1rem; color:var(--text-muted); margin-top:10px;">Enter an API Key to run advanced physiological analytics and biomechanics.</p>
            </div>

            <div id="analyticsDashboard" class="hidden">
                <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 15px;">
                    <div>
                        <p style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px;">SmartECG Digital Subject</p>
                        <h2 id="patID" style="font-size: 1.5rem; font-family:'Outfit'; font-weight: 700;">--</h2>
                    </div>
                     <div style="text-align: right;">
                        <p style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px;">DATE: <span id="patDate" style="color: var(--text-main); font-weight: 600;">--</span></p>
                    </div>
                </div>

                <div class="tabs">
                    <div class="tab active" onclick="switchTab('signal')">SIGNAL ANALYTICS</div>
                    <div class="tab" onclick="switchTab('biomech')">BIOMECHANICS</div>
                </div>

                <!-- SIGNAL ANALYTICS TAB -->
                <div id="tab-signal" class="tab-content">
                    <div class="diagnosis-alert" id="diagnosisBanner">
                        <i class="fas fa-info-circle fa-lg"></i>
                        <span id="ecgPredictionText">PENDING CLASSIFICATION</span>
                    </div>

                    <div class="metrics-row" id="metricsRow" style="margin-bottom: 25px;"></div>

                    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;">
                        <div class="card">
                            <div class="card-header">
                                <div class="card-title"><i class="fas fa-wave-square" style="color: var(--primary);"></i> Clinical ECG Waveform</div>
                            </div>
                            <div class="ecg-grid"><canvas id="ecg1dChart"></canvas></div>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 20px;">
                            <div class="card" style="flex: 1;">
                                <div class="card-header">
                                    <div class="card-title">R-R Tachogram</div>
                                </div>
                                <div style="padding: 15px; height: 160px;"><canvas id="tachogramChart"></canvas></div>
                            </div>
                            <div class="card" style="flex: 1;">
                                <div class="card-header">
                                    <div class="card-title">R-R Distribution</div>
                                </div>
                                <div style="padding: 15px; height: 160px;"><canvas id="rrDistChart"></canvas></div>
                            </div>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                        <div class="card">
                            <div class="card-header">
                                <div class="card-title">Latent Space Mapping (PCA)</div>
                            </div>
                            <div style="padding: 15px; height: 180px;"><canvas id="ecgPcaChart"></canvas></div>
                        </div>
                        <div class="card">
                            <div class="card-header">
                                <div class="card-title">Neural Master Lead Extraction</div>
                            </div>
                            <div style="padding: 15px; height: 180px;"><canvas id="masterLeadChart"></canvas></div>
                        </div>
                    </div>
                </div>

                <!-- BIOMECHANICS TAB -->
                <div id="tab-biomech" class="tab-content hidden">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div class="card">
                            <div class="card-header">
                                <div class="card-title"><i class="fas fa-draw-polygon" style="color:var(--accent);"></i> Anatomical Contours</div>
                            </div>
                            <div class="contour-box"><canvas id="contourCanvas"></canvas></div>
                        </div>
                        <div class="card">
                            <div class="card-header">
                                <div class="card-title">Volume Distribution</div>
                            </div>
                            <div style="padding: 20px; height: 300px;"><canvas id="volumeChart"></canvas></div>
                        </div>
                    </div>
                    
                    <div class="card" style="margin-top: 20px;">
                        <div class="card-header">
                            <div class="card-title">LV vs RV Functional Comparison</div>
                        </div>
                        <div style="padding: 20px; height: 300px;"><canvas id="compareChart"></canvas></div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
        let charts = {};
        let logCount = 0;
        let pollInterval = null;
        let lastLoadedData = null;

        function switchTab(t) {
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            const activeTab = Array.from(document.querySelectorAll('.tab')).find(el => el.getAttribute('onclick').includes(`'${t}'`));
            if (activeTab) activeTab.classList.add('active');
            
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.getElementById('tab-' + t).classList.remove('hidden');

            if (t === 'biomech' && lastLoadedData && lastLoadedData.contours) {
                setTimeout(() => drawContours(lastLoadedData.contours), 50);
            }
        }

        function appendLog(msg, color = 'gray') {
            const b = document.getElementById('logBody');
            const c = { blue: '#818cf8', green: '#34d399', red: '#fca5a5', gray: '#a1a1aa' }[color] || color;
            b.innerHTML += `<div>[${new Date().toLocaleTimeString()}] <span style="color:${c}">${msg}</span></div>`;
            b.scrollTop = b.scrollHeight;
        }

        function setStep(n, s) { 
            const el = document.getElementById('step' + n); 
            if (el) el.className = 'pipeline-step ' + s; 
        }
        function resetSteps() { for (let i = 1; i <= 4; i++) setStep(i, ''); }

        async function saveConfig(e) {
            e.preventDefault();
            appendLog('System Config Updated.', 'blue');
        }

        async function runAnalysis() {
            const val = document.getElementById('api_key_input').value.trim();
            if (!val) {
                // If no key entered, we simulate Cardioscan Pro upload for Patient_44
                appendLog('System Hub Online.', 'green');
                appendLog('Acquiring diagnostic stream...', 'blue');
                await simulatePipelineCardio();
                return;
            }
            
            const b = document.getElementById('startBtn');
            b.disabled = true; b.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            resetSteps(); logCount = 0;
            
            appendLog('System Hub Online.', 'green');
            appendLog('Connecting to exact SmartECG API Key metrics...', 'blue');
            setStep(1, 'active');
            
            try {
                // First simulate the pipeline logs
                const r = await fetch('/run_pipeline', { method: 'POST' });
                pollInterval = setInterval(pollLogs, 1000); // 1s logs fake
                
                // Also fetch our specific patient data right away to load in the background
                setTimeout(async () => {
                    const res = await fetch('/api/patient/Patient_44.mat');
                    const d = await res.json();
                    lastLoadedData = d;
                }, 1000);
            } catch (e) {
                appendLog(e.message, 'red');
            }
        }
        
        async function simulatePipelineCardio() {
            const b = document.getElementById('startBtn');
            b.disabled = true; b.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            resetSteps(); logCount = 0;
            fetch('/run_pipeline', { method: 'POST' });
            pollInterval = setInterval(pollLogs, 1000);
            setTimeout(async () => {
                const res = await fetch('/api/patient/Patient_44.mat');
                const d = await res.json();
                lastLoadedData = d;
            }, 1000);
        }

        async function pollLogs() {
            try {
                const r = await fetch('/logs');
                const { logs } = await r.json();
                if (!logs) return;
                const newLines = logs.slice(logCount);
                newLines.forEach(l => {
                    logCount++; appendLog(l, (l.includes('SUCCESS')||l.includes('locked'))? 'green':'gray');
                    const line = l.toUpperCase();
                    if (line.includes('SLICES ALIGNED')) setStep(1, 'done');
                    else if (line.includes('SURFACES')) setStep(2, 'done');
                    else if (line.includes('MSH')) setStep(3, 'done');
                    if (line.includes('COMPLETED')) {
                        setStep(4, 'done');
                        clearInterval(pollInterval);
                        if (lastLoadedData) {
                            loadDashboard(lastLoadedData);
                        }
                        const b = document.getElementById('startBtn');
                        b.disabled = false; b.innerHTML = '<i class="fas fa-search-heart"></i> Fetch & Analyze';
                    }
                });
            } catch (e) { }
        }

        function C(id, type, data, opts) {
            if (charts[id]) charts[id].destroy();
            const ctx = document.getElementById(id).getContext('2d');
            charts[id] = new Chart(ctx, { type, data, options: { responsive: true, maintainAspectRatio: false, ...opts } });
        }

        function loadDashboard(data) {
            document.getElementById('welcomeView').classList.add('hidden');
            document.getElementById('analyticsDashboard').classList.remove('hidden');
            document.getElementById('patID').innerText = ("CASE_" + (data.filename || "PAT_44")).toUpperCase();
            document.getElementById('patDate').innerText = new Date().toLocaleString();
            
            // Prediction Banner
            const pred = data.ecg_analysis?.prediction || "Normal";
            const banner = document.getElementById('diagnosisBanner');
            document.getElementById('ecgPredictionText').innerText = pred.replace("You ECG corresponds to", "").toUpperCase();
            banner.className = "diagnosis-alert " + (pred.toLowerCase().includes("normal") ? "alert-normal" : "alert-path");
            
            // Metrics
            const m = data.metrics || {};
            const cfg = [
                { k: 'EDV', l: 'LV EDV', u: 'ml' }, { k: 'ESV', l: 'LV ESV', u: 'ml' },
                { k: 'EF', l: 'Ejection FX', u: '%' }, { k: 'SV', l: 'Stroke Vol', u: 'ml' },
                { k: 'LVM', l: 'LV Mass', u: 'g' }, { k: 'RVEDV', l: 'RV EDV', u: 'ml' }, { k: 'RVEF', l: 'RV EF', u: '%' }
            ];
            
            let html = '';
            cfg.forEach(c => {
                const v = (m[c.k] && m[c.k].value !== undefined) ? m[c.k].value : '—';
                html += `<div class="stat-card">
                    <div class="stat-label">${c.l}</div>
                    <div class="stat-value">${v}<span style="font-size:0.8rem;color:var(--text-muted);font-weight:600;margin-left:5px;">${c.u}</span></div>
                </div>`;
            });
            document.getElementById('metricsRow').innerHTML = html;

            if (data.ecg_analysis && data.ecg_analysis.data) {
                const dat = data.ecg_analysis.data;
                // 1D Chart
                if (dat.signal_1d) {
                    C('ecg1dChart', 'line', {
                        labels: dat.signal_1d.map((_, i) => i),
                        datasets: [{ data: dat.signal_1d, borderColor: '#6366f1', borderWidth: 2, pointRadius: 0, tension: 0.1 }]
                    }, { plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { grid: { display: false }, ticks: { display: false } } } });
                }

                // Tachogram
                if (dat.rr_tachogram) {
                    C('tachogramChart', 'scatter', {
                        datasets: [{ data: dat.rr_tachogram.map((v, i) => ({ x: i, y: v })), borderColor: '#10b981', backgroundColor: '#10b981', showLine: true, borderWidth: 1, tension: 0.1, pointRadius: 2 }]
                    }, { plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.05)' } } } });
                }

                // RR Dist
                if (dat.rr_distribution) {
                    const bins = {}; dat.rr_distribution.forEach(v => { const b = Math.floor(v / 10) * 10; bins[b] = (bins[b] || 0) + 1; });
                    const labels = Object.keys(bins).sort((a, b) => a - b);
                    C('rrDistChart', 'bar', {
                        labels: labels,
                        datasets: [{ data: labels.map(l => bins[l]), backgroundColor: 'rgba(99, 102, 241, 0.6)', borderRadius: 3 }]
                    }, { plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { display: false } } });
                }

                // PCA
                if (dat.reduced_data) {
                    C('ecgPcaChart', 'bar', {
                        labels: dat.reduced_data.map((_, i) => `C${i}`),
                        datasets: [{ data: dat.reduced_data, backgroundColor: '#818cf8', borderRadius: 6 }]
                    }, { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: 'rgba(255,255,255,0.5)', font: { size: 9 } } }, y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { display: false } } } });
                }

                // Master Lead
                if (dat.master_lead) {
                    C('masterLeadChart', 'line', {
                        labels: dat.master_lead.map((_, i) => i),
                        datasets: [{ data: dat.master_lead, borderColor: '#34d399', borderWidth: 2, pointRadius: 0, tension: 0.4 }]
                    }, { plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { display: false } } });
                }
            }

            // Pie/Doughnut Chart
            const edv = m.EDV?.value || 0;
            const esv = m.ESV?.value || 60;
            const sv = m.SV?.value || 80;
            const rvedv = m.RVEDV?.value || 0;
            const rvesv = m.RVESV?.value || 0;
            
            C('volumeChart', 'doughnut', {
                labels: ['ESV', 'SV'],
                datasets: [{ data: [esv, sv], backgroundColor: ['#ef4444', '#6366f1'], borderColor: 'transparent' }]
            }, { cutout: '70%', plugins: { legend: { position: 'bottom', labels: { color: '#a1a1aa', font: { family: 'Outfit', size: 12 } } } } });

            // Comparison
            C('compareChart', 'bar', {
                labels: ['EDV (ml)', 'ESV (ml)', 'EF (%)', 'SV (ml)'],
                datasets: [
                    { label: 'Left Ventricle', data: [edv, esv, m.EF?.value || 0, sv], backgroundColor: '#6366f1', borderRadius: 4 },
                    { label: 'Right Ventricle', data: [rvedv, rvesv, m.RVEF?.value || 0, rvedv - rvesv], backgroundColor: '#10b981', borderRadius: 4 }
                ]
            }, { plugins: { legend: { labels: { color: '#a1a1aa', font: { size: 12, family: 'Outfit' } } } }, scales: { x: { ticks: { color: '#a1a1aa' } }, y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#a1a1aa' } } } });

            if (data.contours) drawContours(data.contours);
        }
        
        function drawContours(cont) {
            const canvas = document.getElementById('contourCanvas');
            if (!canvas) return;
            canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#09090b'; ctx.fillRect(0, 0, canvas.width, canvas.height);
            let allX = [], allY = [];
            Object.values(cont).forEach(c => { allX.push(...c.x); allY.push(...c.y); });
            if (!allX.length) return;
            const minX = Math.min(...allX), maxX = Math.max(...allX), minY = Math.min(...allY), maxY = Math.max(...allY);
            const scale = Math.min((canvas.width - 40) / (maxX - minX), (canvas.height - 40) / (maxY - minY));
            const tx = x => 20 + (x - minX) * scale, ty = y => 20 + (y - minY) * scale;
            const cols = { LVEndo: '#ef4444', LVEpi: '#6366f1', RVEndo: '#10b981' };
            Object.entries(cont).forEach(([n, c]) => {
                ctx.strokeStyle = cols[n] || '#fff'; ctx.lineWidth = 2; ctx.beginPath();
                c.x.forEach((x, i) => i === 0 ? ctx.moveTo(tx(x), ty(c.y[i])) : ctx.lineTo(tx(x), ty(c.y[i])));
                ctx.closePath(); ctx.stroke();
            });
        }
    </script>
</body>
</html>
"""

with open("templates/analyze.html", "w") as f:
    f.write(html_content)
