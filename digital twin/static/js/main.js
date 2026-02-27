class SoundPipe {
    constructor(src) {
        this.pipe = null;
        this.active = false;
        this.data = null;
        this.uri = src;
        this.absent = false;
        this.tempo = 72;
    }

    async bootstrap() {
        if (this.pipe) return;
        const Context = window.AudioContext || window.webkitAudioContext;
        this.pipe = new Context();
        this.active = true;

        try {
            const raw = await fetch(this.uri);
            const array = await raw.arrayBuffer();
            this.data = await this.pipe.decodeAudioData(array);
        } catch (e) {
            console.error("Pipe Load Error:", e);
        }
    }

    setTempo(val) {
        this.tempo = val;
    }

    mute() {
        this.absent = !this.absent;
        if (this.pipe) {
            if (this.absent) this.pipe.suspend();
            else this.pipe.resume();
        }
        return this.absent;
    }

    emit() {
        if (this.absent || !this.pipe || !this.data || this.pipe.state === 'suspended') return;
        const node = this.pipe.createBufferSource();
        node.buffer = this.data;
        node.connect(this.pipe.destination);
        node.start(0);
    }
}

class PulseVisualizer {
    constructor(id) {
        this.stage = document.getElementById(id);
        if (!this.stage) return;
        this.pen = this.stage.getContext('2d');
        this.audio = new SoundPipe('./assets/sounds/heartbeat-clean.wav');

        this.fpsTarget = document.getElementById('speed');
        this.temSlider = document.getElementById('bpm-input');
        this.temDisplay = document.getElementById('bpm-display');
        this.audioTrigger = document.getElementById('mute-btn');

        this.pulse = 72;

        if (this.audioTrigger) {
            this.audioTrigger.addEventListener('click', () => {
                const isSilent = this.audio.mute();
                this.audioTrigger.classList.toggle('off', isSilent);
                if (!this.audio.active) this.audio.bootstrap();
            });
        }

        if (this.temSlider) {
            this.pulse = parseFloat(this.temSlider.value);
            this.audio.setTempo(this.pulse);

            this.temSlider.addEventListener('input', (e) => {
                const n = parseFloat(e.target.value);
                this.pulse = n;
                this.audio.setTempo(n);
                if (this.temDisplay) this.temDisplay.innerText = n;
                if (this.fpsTarget) {
                    this.fpsTarget.value = n / 90;
                    this.fpsTarget.dispatchEvent(new Event('input', { bubbles: true }));
                }
                if (!this.audio.active) this.audio.bootstrap();
            });
        }

        this.scanSpeed = 2;
        this.pointer = 0;
        this.toneA = '#3b82f6';
        this.toneB = '#00d1ff';

        this.lastHit = 0;
        this.activeHit = false;

        this.baseA = 0;
        this.baseB = 0;
        this.amp = 1;

        this.prevA = 0;
        this.prevB = 0;

        this.resize();
        window.addEventListener('resize', () => this.resize());
        this.engine();
    }

    resize() {
        const dpr = window.devicePixelRatio || 1;
        const box = this.stage.getBoundingClientRect();
        this.stage.width = box.width * dpr;
        this.stage.height = box.height * dpr;
        this.pen.scale(dpr, dpr);
        this.dim = box;
        this.baseA = box.height * 0.35;
        this.baseB = box.height * 0.75;
        this.amp = -(box.height * 0.25);
        this.pen.clearRect(0, 0, box.width, box.height);
        this.prevA = this.baseA;
        this.prevB = this.baseB;
    }

    gauss(t, c, w, h) {
        return h * Math.exp(-Math.pow(t - c, 2) / (2 * Math.pow(w, 2)));
    }

    getWave(t) {
        let s = 0;
        s += this.gauss(t, 0.15, 0.02, 0.15);
        s -= this.gauss(t, 0.28, 0.005, 0.1);
        s += this.gauss(t, 0.30, 0.005, 1.2);
        s -= this.gauss(t, 0.32, 0.005, 0.2);
        s += this.gauss(t, 0.60, 0.04, 0.3);
        s += (Math.random() - 0.5) * 0.02;
        return s;
    }

    getMech(t) {
        let s = 0;
        if (t > 0.35 && t < 0.65) {
            let p = (t - 0.35) / 0.30;
            s = Math.sin(p * Math.PI) * 0.8;
            if (p > 0.7) s += 0.1;
        }
        s += this.gauss(t, 0.68, 0.03, 0.15);
        return s * 0.6;
    }

    engine() {
        requestAnimationFrame(() => this.engine());
        const now = Date.now();
        const gap = 60000 / this.pulse;

        if (!this.activeHit && now - this.lastHit > gap) {
            this.activeHit = true;
            this.lastHit = now;
            const obj = document.getElementById('ecg-bpm-val');
            if (obj) obj.innerText = Math.round(this.pulse);
            if (this.audio) this.audio.emit();
        }

        let progress = 0;
        if (this.activeHit) {
            const span = now - this.lastHit;
            const limit = 800 * (72 / this.pulse);
            progress = span / limit;
            if (progress > 1) {
                this.activeHit = false;
                progress = 0;
            }
        }

        const yA = this.baseA + (this.getWave(progress) * this.amp);
        const yB = this.baseB + (this.getMech(progress) * this.amp);

        const gapSize = 5;
        this.pen.clearRect(this.pointer, 0, gapSize, this.dim.height);
        this.pen.fillStyle = 'rgba(255, 255, 255, 0.1)';
        this.pen.fillRect(this.pointer + gapSize - 2, 0, 2, this.dim.height);

        if (this.pointer > this.scanSpeed) {
            this.pen.beginPath();
            this.pen.strokeStyle = this.toneA;
            this.pen.lineWidth = 2;
            this.pen.moveTo(this.pointer - this.scanSpeed, this.prevA);
            this.pen.lineTo(this.pointer, yA);
            this.pen.stroke();

            this.pen.beginPath();
            this.pen.strokeStyle = this.toneB;
            this.pen.lineWidth = 2;
            this.pen.moveTo(this.pointer - this.scanSpeed, this.prevB);
            this.pen.lineTo(this.pointer, yB);
            this.pen.stroke();
        }

        this.prevA = yA;
        this.prevB = yB;
        this.pointer += this.scanSpeed;
        if (this.pointer > this.dim.width) this.pointer = 0;
    }
}

// User State
const UserState = {
    email: null,
    name: null,
    picture: null
};

// --- Google Auth & History Logic ---
function setupGoogleAuth() {
    window.handleCredentialResponse = (response) => {
        try {
            const base64Url = response.credential.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function (c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));

            const payload = JSON.parse(jsonPayload);
            UserState.email = payload.email;
            UserState.name = payload.name;
            UserState.picture = payload.picture;

            updateAuthUI(true);
            loadHistory();
        } catch (e) {
            console.error("Auth Error", e);
        }
    };

    // If Google Auth fails due to origin mismatch, we allow Guest Mode
    if (window.google && window.google.accounts) {
        try {
            google.accounts.id.initialize({
                client_id: "1001831003943-eqr8jof0hgto4ns1in822f8qgu8e74mp.apps.googleusercontent.com",
                callback: window.handleCredentialResponse,
                auto_select: false
            });

            google.accounts.id.renderButton(
                document.getElementById("google-login-btn"),
                { theme: "outline", size: "medium" }
            );
        } catch (err) {
            console.warn("Clinical Engine: Google Auth restricted on this origin. Falling back to Local Session.");
            useGuestMode();
        }
    } else {
        useGuestMode();
    }
}

function useGuestMode() {
    console.log("Initializing in Local Medical Mode (Guest).");
    const container = document.getElementById("google-login-btn");
    if (container) {
        container.innerHTML = `<button class="core-btn" style="background: #1e293b; color: #94a3b8; font-size: 0.75rem;" onclick="activateGuestSession()">ENTER AS GUEST MD</button>`;
    }
}

window.activateGuestSession = () => {
    UserState.email = "guest.md@clinical.view";
    UserState.name = "Guest Medical Officer";
    UserState.picture = "https://img.icons8.com/ios-filled/50/3b82f6/user-male-circle.png";
    updateAuthUI(true);
    loadHistory();
};

function updateAuthUI(isLoggedIn) {
    const loginBtn = document.getElementById('google-login-btn');
    const profile = document.getElementById('user-profile-section');

    if (isLoggedIn) {
        if (loginBtn) loginBtn.style.display = 'none';
        if (profile) {
            profile.style.display = 'flex';
            document.getElementById('user-name-disp').innerText = UserState.name;
            document.getElementById('user-email-disp').innerText = UserState.email;
            document.getElementById('user-avatar').src = UserState.picture;
        }
    } else {
        if (loginBtn) loginBtn.style.display = 'block';
        if (profile) profile.style.display = 'none';
    }
}

function setupHistoryUI() {
    const toggle = document.getElementById('history-toggle-btn');
    const sidebar = document.getElementById('history-sidebar');
    const close = document.getElementById('close-history-btn');

    if (toggle && sidebar) {
        toggle.onclick = () => {
            sidebar.classList.toggle('active');
            if (sidebar.classList.contains('active') && UserState.email) loadHistory();
        };
    }

    if (close && sidebar) {
        close.onclick = () => sidebar.classList.remove('active');
    }

    const signOut = document.getElementById('sign-out-btn');
    if (signOut) {
        signOut.onclick = () => {
            UserState.email = null;
            UserState.name = null;
            UserState.picture = null;
            updateAuthUI(false);
            if (sidebar) sidebar.classList.remove('active');
            google.accounts.id.disableAutoSelect();
        };
    }
}

async function loadHistory() {
    if (!UserState.email) return;

    const list = document.getElementById('history-list');
    list.innerHTML = '<div style="padding:20px; text-align:center;">Loading...</div>';

    try {
        const res = await fetch(`/history/${UserState.email}`);
        const data = await res.json();
        renderHistory(data);
    } catch (e) {
        console.error("History fetch error", e);
        list.innerText = "Error loading history.";
    }
}

function renderHistory(items) {
    const list = document.getElementById('history-list');
    list.innerHTML = '';

    if (!items || items.length === 0) {
        list.innerHTML = '<div style="padding: 20px; text-align: center; color: rgba(255,255,255,0.3); font-size: 0.8rem;">No analysis history found.</div>';
        return;
    }

    items.forEach(item => {
        const div = document.createElement('div');
        div.className = 'history-item';

        const date = new Date(item.timestamp).toLocaleString();

        div.innerHTML = `
            <div class="history-date">${date}</div>
            <div class="history-diagnosis">${item.prediction}</div>
            <div class="history-bpm">❤️ ${item.bpm} BPM</div>
        `;

        div.onclick = () => loadHistoryItem(item.id);
        list.appendChild(div);
    });
}

async function loadHistoryItem(id) {
    try {
        const res = await fetch(`/history/item/${id}`);
        if (!res.ok) throw new Error("Not found");
        const data = await res.json();

        // Populate specific UI
        document.getElementById('ecg-modal').classList.add('active');
        document.getElementById('ecg-loading').style.display = 'none';
        document.getElementById('ecg-results').style.display = 'block';

        // Populate Fields
        document.getElementById('prediction-text').innerText = data.prediction;
        document.getElementById('monitor-diagnosis-text').innerText = data.prediction;

        document.getElementById('res-original').src = data.images.original;
        document.getElementById('res-grayscale').src = data.images.grayscale;
        document.getElementById('res-leads').src = data.images.leads;
        document.getElementById('res-long-lead').src = data.images.long_lead;
        document.getElementById('res-processed').src = data.images.preprocessed;
        document.getElementById('res-processed-long').src = data.images.preprocessed_long;
        document.getElementById('res-contours').src = data.images.contours;

        document.getElementById('res-signal-data').innerText = JSON.stringify(data.signal_1d, null, 2);
        document.getElementById('res-dimensionality').innerText = JSON.stringify(data.dimensional_reduction, null, 2);

        // Re-init Twin Bridge if available
        const twin = document.getElementById('digital-twin-bridge');
        const trigger = document.getElementById('approve-digital-twin');
        const sync = document.getElementById('advanced-analysis-section');

        if (data.rhythm) {
            twin.style.display = 'block';
            trigger.onclick = () => {
                sync.style.display = 'block';
                renderAdvancedCharts(data.rhythm);
                document.getElementById('adv-bpm').innerText = data.bpm;
                document.getElementById('adv-peaks').innerText = data.rhythm.peak_count;
                document.getElementById('adv-hrv').innerText = data.rhythm.hrv;
                document.getElementById('adv-duration').innerText = data.rhythm.duration + 's';
                sync.scrollIntoView({ behavior: 'smooth' });
            }
        }

    } catch (e) {
        console.error("Load item error", e);
        alert("Failed to load historical data.");
    }
}

function renderMiniCharts(bpm) {
    const tBox = document.getElementById('live-analysis-charts');
    if (!tBox) return;
    tBox.style.display = 'block';

    const tach = document.getElementById('live-tachogram');
    const dist = document.getElementById('live-distribution');
    if (!tach || !dist) return;

    const ctxT = tach.getContext('2d');
    const ctxD = dist.getContext('2d');

    const dpr = window.devicePixelRatio || 1;
    const w = tach.clientWidth * dpr;
    const h = tach.clientHeight * dpr;

    tach.width = w; tach.height = h;
    dist.width = w; dist.height = h;

    ctxT.scale(dpr, dpr);
    ctxD.scale(dpr, dpr);

    const sw = tach.clientWidth;
    const sh = tach.clientHeight;

    const baseInterval = 60000 / bpm;
    const intervals = Array.from({ length: 12 }, () => baseInterval + (Math.random() - 0.5) * 40);

    ctxT.clearRect(0, 0, sw, sh);
    ctxT.strokeStyle = '#facc15';
    ctxT.lineWidth = 1.5;
    ctxT.beginPath();
    intervals.forEach((val, i) => {
        const x = (i / (intervals.length - 1)) * sw;
        const y = sh - ((val - 600) / 400) * sh;
        if (i === 0) ctxT.moveTo(x, y);
        else ctxT.lineTo(x, y);

        ctxT.fillStyle = '#facc15';
        ctxT.beginPath();
        ctxT.arc(x, y, 2.5, 0, Math.PI * 2);
        ctxT.fill();
    });
    ctxT.stroke();

    ctxD.clearRect(0, 0, sw, sh);
    ctxD.fillStyle = '#00d1ff';
    const bars = 10;
    for (let i = 0; i < bars; i++) {
        const bh = Math.random() * sh * 0.7 + (sh * 0.2);
        ctxD.fillRect((i * sw / bars) + 1.5, sh - bh, (sw / bars) - 3, bh);
    }
}

function renderAdvancedCharts(rhythm) {
    const sync = document.getElementById('advanced-analysis-section');
    if (!sync) return;
    sync.style.display = 'block';

    document.getElementById('adv-bpm').innerText = rhythm.bpm;
    document.getElementById('adv-peaks').innerText = rhythm.peak_count;
    document.getElementById('adv-hrv').innerText = rhythm.hrv;
    document.getElementById('adv-duration').innerText = rhythm.duration;

    const trace = document.getElementById('main-signal-trace');
    const tach = document.getElementById('main-tachogram');
    const dist = document.getElementById('main-distribution');
    if (!trace || !tach || !dist) return;

    const ctxS = trace.getContext('2d');
    const ctxT = tach.getContext('2d');
    const ctxD = dist.getContext('2d');

    const dpr = window.devicePixelRatio || 1;
    [trace, tach, dist].forEach(c => {
        c.width = c.clientWidth * dpr;
        c.height = c.clientHeight * dpr;
    });

    [ctxS, ctxT, ctxD].forEach(c => c.scale(dpr, dpr));

    const sw = trace.clientWidth;
    const sh = trace.clientHeight;

    // 1. ECG Signal Trace
    ctxS.clearRect(0, 0, sw, sh);

    // Grid lines
    ctxS.strokeStyle = 'rgba(255,255,255,0.05)';
    ctxS.lineWidth = 1;
    for (let i = 0; i < 10; i++) {
        const y = (i / 10) * sh;
        ctxS.beginPath(); ctxS.moveTo(0, y); ctxS.lineTo(sw, y); ctxS.stroke();
    }

    // The Signal
    ctxS.strokeStyle = '#00d1ff';
    ctxS.lineWidth = 2;
    ctxS.beginPath();
    rhythm.signal.forEach((val, i) => {
        const x = (i / (rhythm.signal.length - 1)) * sw;
        const y = sh - (val * (sh * 0.8) + (sh * 0.1));
        if (i === 0) ctxS.moveTo(x, y);
        else ctxS.lineTo(x, y);
    });
    ctxS.stroke();

    // R-Peaks (Red circles)
    ctxS.fillStyle = '#ef4444';
    rhythm.peaks.forEach(idx => {
        const x = (idx / (rhythm.signal.length - 1)) * sw;
        const val = rhythm.signal[idx];
        const y = sh - (val * (sh * 0.8) + (sh * 0.1));
        ctxS.beginPath();
        ctxS.arc(x, y, 6, 0, Math.PI * 2);
        ctxS.fill();
        // Glow effect
        ctxS.shadowBlur = 10; ctxS.shadowColor = '#ef4444';
        ctxS.fill();
        ctxS.shadowBlur = 0;
    });

    // 2. Plot Tachogram
    const tw = tach.clientWidth;
    const th = tach.clientHeight;
    ctxT.clearRect(0, 0, tw, th);

    if (rhythm.intervals.length > 0) {
        const minVal = Math.min(...rhythm.intervals);
        const maxVal = Math.max(...rhythm.intervals);
        const rangeVal = (maxVal - minVal) || 200;
        const pad = rangeVal * 0.3;

        ctxT.strokeStyle = '#facc15';
        ctxT.lineWidth = 2;
        ctxT.beginPath();
        rhythm.intervals.forEach((val, i) => {
            const x = (rhythm.intervals.length > 1) ? (i / (rhythm.intervals.length - 1)) * tw : tw / 2;
            const y = th - ((val - (minVal - pad)) / (rangeVal + 2 * pad)) * th;
            if (i === 0) ctxT.moveTo(x, y);
            else ctxT.lineTo(x, y);

            ctxT.fillStyle = '#facc15';
            ctxT.beginPath(); ctxT.arc(x, y, 4, 0, Math.PI * 2); ctxT.fill();
        });
        ctxT.stroke();
    }

    // 3. Plot Distribution (Histogram)
    const dw = dist.clientWidth;
    const dh = dist.clientHeight;
    ctxD.clearRect(0, 0, dw, dh);
    ctxD.fillStyle = '#3b82f6';

    if (rhythm.intervals.length > 0) {
        const bins = 15;
        const hist = new Array(bins).fill(0);
        const minDist = Math.min(...rhythm.intervals);
        const maxDist = Math.max(...rhythm.intervals);
        const rangeDist = (maxDist - minDist) || 100;

        rhythm.intervals.forEach(v => {
            const b = Math.min(bins - 1, Math.floor(((v - minDist) / rangeDist) * bins));
            hist[b]++;
        });

        const maxH = Math.max(...hist) || 1;
        hist.forEach((h, i) => {
            const bw = (dw / bins) - 8;
            const bh = (h / maxH) * (dh * 0.8);
            const x = (i * (dw / bins)) + 4;
            const y = dh - bh;
            ctxD.fillRect(x, y, bw, bh);
        });
    }
}

// --- Global Registry ---
const TISSUE_MAP = {
    'Heartmuscles': 'Myocardium', 'sanvan': 'Conduction Nodes', 'internal': 'Interior Lattice',
    'Largevessels': 'Aortic Arc', 'Smallvessels': 'Micro-vessel', 'SVenaCava': 'Sup. Vena Cava', 'IVenaCava': 'Inf. Vena Cava', 'Pulmonaryvessels': 'Pulmonary Trunk',
    'la': 'Atrial Left', 'ra': 'Atrial Right', 'lv': 'Ventricle Left', 'rv': 'Ventricle Right',
    'bicuspid': 'Mitral Valve', 'tricuspid': 'Tricuspid Valve', 'valves': 'General Valves'
};

function setTissueVisibility(id, value) {
    const el = document.getElementById(id);
    if (!el) return;

    el.value = value;
    // Dispatch both events to ensure engine catches the change
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));

    // Update any associated eye toggles (Left Sidebar)
    const eye = document.querySelector(`.eye-toggle[data-target="${id}"]`);
    if (eye) {
        eye.classList.toggle('active', value > 0);
    }
}

let lastAnalysisResult = null;

const AssistantState = {
    isListening: false,
    selectedLang: 'en-US'
};

function speak(text) {
    if (!text) return;
    window.speechSynthesis.cancel();
    const ut = new SpeechSynthesisUtterance(text);
    ut.lang = AssistantState.selectedLang;
    ut.rate = 1.0;
    ut.pitch = 1.1;
    window.speechSynthesis.speak(ut);
}

// Simple Markdown Renderer for Chat
function md(text) {
    if (!text) return "";
    if (text.includes('|')) {
        const lines = text.trim().split('\n');
        let html = '<div class="table-container"><table>';
        let hasStarted = false;
        lines.forEach((line) => {
            if (line.includes('---')) return;
            if (!line.includes('|')) return;
            const cells = line.split('|').map(c => c.trim()).filter((c, i, a) => !(i === 0 && c === '') && !(i === a.length - 1 && c === ''));
            if (cells.length === 0) return;
            const tag = !hasStarted ? 'th' : 'td';
            html += '<tr>' + cells.map(c => `<${tag}>${c}</${tag}>`).join('') + '</tr>';
            hasStarted = true;
        });
        html += '</table></div>';
        return html;
    }
    return text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');
}

function setupAIChat() {
    const fab = document.getElementById('chat-fab');
    const windowEl = document.getElementById('chat-window');
    const closeBtn = document.getElementById('close-chat');
    const sendBtn = document.getElementById('chat-send');
    const micBtn = document.getElementById('chat-voice-btn');
    const langSelect = document.getElementById('chat-lang');
    const input = document.getElementById('chat-input');
    const messages = document.getElementById('chat-messages');

    // Action Bar Elements
    const reviewBtn = document.getElementById('chat-review-btn');
    const uploadTrigger = document.getElementById('chat-upload-btn');
    const fileInput = document.getElementById('chat-file-input');

    if (!fab || !windowEl) return;

    fab.onclick = () => windowEl.classList.toggle('active');
    closeBtn.onclick = () => windowEl.classList.remove('active');

    // Action Bar Elements
    const chatReviewBtn = document.getElementById('chat-review-btn');
    const chatUploadBtn = document.getElementById('chat-upload-btn');
    const chatFileInput = document.getElementById('chat-file-input');

    if (chatReviewBtn) {
        chatReviewBtn.onclick = () => {
            if (!lastAnalysisResult) {
                appendMessage("I don't have a heartbeat record to analyze. Please upload an ECG frame first.", "bot");
                return;
            }
            const lang = AssistantState.selectedLang;
            let report = (lang === 'ta-IN') ?
                `**முழுமையான இதய ஆய்வு அறிக்கை:**\n\nநாடி துடிப்பு: ${lastAnalysisResult.bpm} BPM.\nமுடிவு: ${lastAnalysisResult.prediction}.\nநிலை: பதிவு செய்யப்பட்டது.` :
                `**COMPREHENSIVE NEURAL SCAN REVIEW**\n\n**Vital Metrics:**\n- Analyzed Heart Rate: ${lastAnalysisResult.bpm} BPM\n- Systemic Conclusion: ${lastAnalysisResult.prediction}\n- Synchronized Peaks: ${lastAnalysisResult.peak_count}\n\n**Observation:**\nThe digitized pulse stream indicates **${lastAnalysisResult.prediction}**. All telemetry data has been committed to your clinical record.`;
            appendMessage(report, 'bot');
        };
    }

    if (chatUploadBtn && chatFileInput) {
        chatUploadBtn.onclick = () => chatFileInput.click();
        chatFileInput.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                appendMessage(`**Targeting Frame:** \`${file.name}\``, 'user');
                const mainInput = document.getElementById('ecg-upload-input');
                if (mainInput) {
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    mainInput.files = dt.files;
                    mainInput.dispatchEvent(new Event('change', { bubbles: true }));
                    appendMessage("Initializing medical-grade pulse digitization...", "bot");
                }
            }
        };
    }

    if (langSelect) {
        langSelect.onchange = (e) => {
            AssistantState.selectedLang = e.target.value;
            speak(AssistantState.selectedLang === 'en-US' ? "Language changed to English" : "Language updated");
        };
    }

    // Action: Review Last Analysis
    const performReview = () => {
        if (!lastAnalysisResult) {
            appendMessage("I don't have a recent heartbeat scan in my neural buffer. Please upload an ECG frame for processing.", "bot");
            return;
        }
        const lang = AssistantState.selectedLang;
        let report = (lang === 'ta-IN') ?
            `**முழுமையான இதய ஆய்வு அறிக்கை:**\n\nநாடி துடிப்பு: ${lastAnalysisResult.bpm} BPM.\nமுடிவு: ${lastAnalysisResult.prediction}.` :
            `**NEURAL SCAN REVIEW**\n- Heart Rate: ${lastAnalysisResult.bpm} BPM\n- Conclusion: ${lastAnalysisResult.prediction}\n- Peaks: ${lastAnalysisResult.peak_count}\n\nWaveform digitization complete. Findings committed to profile.`;
        appendMessage(report, 'bot');
    };
    if (reviewBtn) reviewBtn.onclick = performReview;

    // Action: Upload Image
    if (uploadTrigger && fileInput) {
        uploadTrigger.onclick = () => fileInput.click();
        fileInput.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                appendMessage(`**Importing Frame:** \`${file.name}\``, 'user');
                const mainInput = document.getElementById('ecg-upload-input');
                if (mainInput) {
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    mainInput.files = dt.files;
                    mainInput.dispatchEvent(new Event('change', { bubbles: true }));
                    appendMessage("Initializing neural scanning gateway...", "bot");
                }
            }
        };
    }

    const appendMessage = (text, type, isImage = false) => {
        const div = document.createElement('div');
        div.className = `message ${type}`;
        if (isImage) {
            div.innerHTML = `<img src="${text}" alt="Generated Image">`;
            speak("I have generated the medical reference image as requested.");
        } else {
            div.innerHTML = md(text);
        }
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
        if (type === 'bot' && !isImage) speak(text.replace(/\*\*|#|\|/g, ' '));
    };

    const processCommand = (text) => {
        const cmd = text.toLowerCase();
        if (cmd.includes('sign out') || cmd.includes('logout')) {
            document.getElementById('sign-out-btn')?.click();
            appendMessage("Session terminated.", "bot");
            return true;
        }
        if (cmd.includes('history')) {
            document.getElementById('history-toggle-btn')?.click();
            appendMessage("Opening history.", "bot");
            return true;
        }
        if (cmd.includes('review') || cmd.includes('last analysis')) {
            performReview();
            return true;
        }
        return false;
    };

    const sendMessage = async (manualText) => {
        const text = manualText || input.value.trim();
        if (!text) return;

        if (!manualText) input.value = '';
        appendMessage(text, 'user');

        if (processCommand(text)) return;

        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot';
        loadingDiv.innerText = 'Consulting Neural Network...';
        loadingDiv.id = 'temp-loading';
        messages.appendChild(loadingDiv);
        messages.scrollTop = messages.scrollHeight;

        try {
            const res = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, context: lastAnalysisResult || {} })
            });
            const data = await res.json();
            document.getElementById('temp-loading')?.remove();

            if (data.image) {
                appendMessage(data.response, 'bot');
                appendMessage(data.image, 'bot', true);
            } else {
                appendMessage(data.response, 'bot');
            }
        } catch (e) {
            document.getElementById('temp-loading')?.remove();
            appendMessage("I'm having trouble connecting to the neural network right now.", 'bot');
        }
    };

    // Voice Recognition (STT) Setup
    if ('webkitSpeechRecognition' in window) {
        const recognition = new webkitSpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = false;

        recognition.onstart = () => {
            AssistantState.isListening = true;
            micBtn?.classList.add('listening');
        };

        recognition.onresult = (event) => {
            const transcript = event.results[event.results.length - 1][0].transcript.trim();
            console.log("Speech:", transcript);

            if (transcript.toLowerCase().includes("hey doc") || transcript.toLowerCase().includes("hey dog")) {
                const cleaned = transcript.toLowerCase().replace(/hey doc|hey dog/g, '').trim();
                windowEl.classList.add('active');
                if (cleaned) sendMessage(cleaned);
                else speak("Yes? I am listening.");
            } else if (windowEl.classList.contains('active')) {
                sendMessage(transcript);
            }
        };

        recognition.onerror = () => micBtn?.classList.remove('listening');
        recognition.onend = () => {
            AssistantState.isListening = false;
            micBtn?.classList.remove('listening');
            // Auto-restart for wake-word support
            recognition.start();
        };

        micBtn.onclick = () => {
            if (!AssistantState.isListening) recognition.start();
            else recognition.stop();
        };

        // Initial Start for Wake-word
        recognition.start();
    }

    sendBtn.onclick = () => sendMessage();
    input.onkeypress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

}

function updateAnalysisContext(data) {
    lastAnalysisResult = {
        prediction: data.prediction,
        bpm: data.bpm,
        peak_count: data.rhythm ? data.rhythm.peak_count : 0,
        affected_region: data.affected_region,
        affected_model: data.affected_model
    };
}

function setupTelemetry() {
    const btn = document.getElementById('upload-ecg-btn');
    const input = document.getElementById('ecg-upload-input');
    const modal = document.getElementById('ecg-modal');
    const exit = document.getElementById('close-ecg-modal');
    const spin = document.getElementById('ecg-loading');
    const view = document.getElementById('ecg-results');
    const diag = document.getElementById('prediction-text');

    if (!btn || !input || !modal) return;

    btn.onclick = () => input.click();
    exit.onclick = () => modal.classList.remove('active');

    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        modal.classList.add('active');
        spin.style.display = 'flex';
        view.style.display = 'none';

        // Reset and start animation
        const steps = document.querySelectorAll('.step-item');
        const progressFill = document.getElementById('analysis-progress-fill');
        const percentText = document.getElementById('analysis-percentage');

        steps.forEach(s => s.classList.remove('active', 'complete'));

        let currentStep = 0;
        const totalSteps = steps.length;

        const updateProgress = (stepIdx) => {
            steps.forEach((s, i) => {
                if (i < stepIdx) {
                    s.classList.add('complete');
                    s.classList.remove('active');
                } else if (i === stepIdx) {
                    s.classList.add('active');
                } else {
                    s.classList.remove('active', 'complete');
                }
            });
            const p = Math.floor((stepIdx / totalSteps) * 100);
            if (progressFill) progressFill.style.width = `${p}%`;
            if (percentText) percentText.innerText = `${p}%`;
        };

        const runAnimation = async () => {
            for (let i = 0; i < totalSteps; i++) {
                updateProgress(i);
                // Simulate variable processing time for "professional" feel
                const delay = 400 + Math.random() * 600;
                await new Promise(r => setTimeout(r, delay));
            }
            if (progressFill) progressFill.style.width = `100%`;
            if (percentText) percentText.innerText = `100%`;
        };

        const animationPromise = runAnimation();

        const data = new FormData();
        data.append('file', file);
        if (UserState.email) data.append('email', UserState.email);

        try {
            const [raw, _] = await Promise.all([
                fetch('/predict-ecg', {
                    method: 'POST',
                    body: data
                }),
                animationPromise // Wait for animation to at least start/run
            ]);

            if (!raw.ok) throw new Error('Bridge unreachable');

            const res = await raw.json();

            // Refresh history if logged in
            if (UserState.email) loadHistory();

            // Update AI Context
            updateAnalysisContext(res);

            diag.innerText = res.prediction;
            // ... (rest of function)


            document.getElementById('res-original').src = res.images.original;
            document.getElementById('res-grayscale').src = res.images.grayscale;
            document.getElementById('res-leads').src = res.images.leads;
            document.getElementById('res-long-lead').src = res.images.long_lead;
            document.getElementById('res-processed').src = res.images.preprocessed;
            document.getElementById('res-processed-long').src = res.images.preprocessed_long;
            document.getElementById('res-contours').src = res.images.contours;

            document.getElementById('res-signal-data').innerText = JSON.stringify(res.signal_1d, null, 2);
            document.getElementById('res-dimensionality').innerText = JSON.stringify(res.dimensional_reduction, null, 2);

            const lab = document.getElementById('monitor-diagnosis');
            const txt = document.getElementById('monitor-diagnosis-text');
            const mon = document.getElementById('monitor-summary-box');
            const rep = document.getElementById('summary-text');

            if (lab && txt) {
                lab.style.display = 'block';
                txt.innerText = res.prediction;
                txt.style.color = res.prediction.toLowerCase().includes('healthy') ? '#00d1ff' : '#ef4444';
            }

            if (mon && rep) {
                mon.style.display = 'block';
                const update = () => {
                    const l = document.getElementById('summary-lang').value;
                    const b = res.bpm || 72;
                    const d = res.prediction;
                    const h = res.rhythm.hrv || 0;
                    const tmpl = {
                        'en-US': `CARDIAC SCAN SUCCESSFUL.\nAnalyzed Heart Rate: ${b} BPM.\nDiagnostic Conclusion: ${d}.\nPulse Variability (HRV): ${h} ms.\nStatus: Neural signal digitized and committed to patient record. Continuous monitoring active. Recommend reviewing advanced R-R tachogram for further rhythm insights.`,
                        'hi-IN': `कार्डियक स्कैन सफल रहा।\nविश्लेषित हृदय गति: ${b} बीपीएम।\nनैदानिक निष्कर्ष: ${d}।\nपल्स वेरिएबिलिटी (HRV): ${h} एमएस।\nस्थिति: तंत्रिका संकेत डिजीटल और रोगी रिकॉर्ड में सहेजा गया। निरंतर निगरानी सक्रिय है।`,
                        'ta-IN': `இதய ஸ்கேன் வெற்றிகரமாக முடிந்தது.\nஇதயத் துடிப்பு: ${b} பிபிஎம்.\nகண்டறியப்பட்ட நிலை: ${d}.\nதுடிப்பு மாறுபாடு (HRV): ${h} மி.செ.\nநிலை: நரம்பு சிக்னல் டிஜிட்டல் மயமாக்கப்பட்டது. தொடர்ச்சியான கண்காணிப்பு செயலில் உள்ளது.`
                    };
                    rep.innerText = tmpl[l] || tmpl['en-US'];
                };
                update();
                document.getElementById('summary-lang').onchange = update;
                document.getElementById('summary-speak-btn').onclick = () => {
                    const ut = new SpeechSynthesisUtterance(rep.innerText);
                    ut.lang = document.getElementById('summary-lang').value;
                    window.speechSynthesis.speak(ut);
                };
            }

            const twin = document.getElementById('digital-twin-bridge');
            const trigger = document.getElementById('approve-digital-twin');
            const sync = document.getElementById('advanced-analysis-section');
            const commit = document.getElementById('apply-to-simulation');

            if (twin) {
                twin.style.display = 'block';
                trigger.onclick = () => {
                    if (sync && res.rhythm) {
                        sync.style.display = 'block';
                        renderAdvancedCharts(res.rhythm);
                        document.getElementById('adv-bpm').innerText = res.bpm;
                        document.getElementById('adv-peaks').innerText = res.rhythm.peak_count;
                        document.getElementById('adv-hrv').innerText = res.rhythm.hrv;
                        document.getElementById('adv-duration').innerText = res.rhythm.duration + 's';

                        commit.onclick = () => {
                            const ctrl = document.getElementById('bpm-input');
                            if (ctrl) {
                                ctrl.value = res.bpm || 72;
                                ctrl.dispatchEvent(new Event('input', { bubbles: true }));
                                renderMiniCharts(res.bpm || 72);
                                modal.classList.remove('active');
                            }
                        };
                        sync.scrollIntoView({ behavior: 'smooth' });
                    }
                };
            }

            spin.style.display = 'none';
            view.style.display = 'block';

            // AUTO-HIGHLIGHT AFFECTED PART
            if (res.affected_region) {
                const regionToId = {
                    'Septal': 'lv',
                    'Anterior': 'lv',
                    'Lateral': 'la',
                    'Inferior': 'rv'
                };
                const id = regionToId[res.affected_region];
                Object.keys(TISSUE_MAP).forEach(pid => {
                    setTissueVisibility(pid, (pid === id) ? 1.0 : 0.25);
                });
            }

        } catch (err) {
            console.error(err);
            modal.classList.remove('active');
        } finally {
            input.value = '';
        }
    };
}



function setupHeartViewerMode() {
    const selector = document.getElementById('heartview-mode');
    const container = document.getElementById('canvas-container');
    const opacityCtrl = document.getElementById('opacitySlider');

    if (!selector || !container) return;

    selector.addEventListener('change', (e) => {
        const mode = e.target.value;
        const targetCanvas = container.querySelector('canvas');

        // Reset styles on both container and internal canvas
        container.style.filter = 'none';
        container.style.background = '#000'; // Force black background

        if (targetCanvas) {
            targetCanvas.style.filter = 'none';
        }

        const applyOpacity = (val) => {
            if (opacityCtrl) {
                opacityCtrl.value = val;
                opacityCtrl.dispatchEvent(new Event('change', { bubbles: true }));
            }
        };

        const activeTarget = targetCanvas || container;

        switch (mode) {
            case 'solid':
                // RESET ALL LAYERS TO FULL VISIBILITY
                Object.keys(TISSUE_MAP).forEach(id => {
                    const el = document.getElementById(id);
                    if (el) {
                        el.value = 1.0;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                });
                applyOpacity(1);
                break;
            case 'wire':
                // REVEAL ALL LAYERS
                Object.keys(TISSUE_MAP).forEach(id => {
                    const el = document.getElementById(id);
                    if (el) {
                        el.value = 0.7; // Higher visibility for better shape
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                });
                // Cleaner Technical Wireframe Look
                if (targetCanvas) {
                    targetCanvas.style.filter = 'grayscale(1) contrast(4) brightness(1.2) sepia(1) hue-rotate(180deg) saturate(3)';
                }
                applyOpacity(0.7);
                break;
            case 'xray':
                activeTarget.style.filter = 'opacity(0.15) brightness(2) saturate(0) contrast(1.5)';
                applyOpacity(0.15);
                break;
            case 'blueprint':
                activeTarget.style.filter = 'hue-rotate(195deg) brightness(1.5) contrast(1.2) saturate(3) opacity(0.8)';
                applyOpacity(0.8);
                break;
            case 'thermal':
                activeTarget.style.filter = 'contrast(2) saturate(3) hue-rotate(260deg)';
                applyOpacity(1);
                break;
            case 'contrast':
                activeTarget.style.filter = 'grayscale(1) contrast(10) brightness(0.7)';
                applyOpacity(1);
                break;
        }
    });
}

// Main Initialization
function init() {
    // 1. Core Systems
    new PulseVisualizer('ecg-canvas');
    setupHistoryUI();

    // 2. Loading Screen Logic
    const ws = document.getElementById('wait-screen');
    if (ws) {
        setTimeout(() => {
            ws.style.opacity = '0';
            setTimeout(() => ws.style.display = 'none', 500);
        }, 1000);
    }

    // 3. Functional Modules
    setupTelemetry();
    setupAIChat();
    setupHeartViewerMode();

    // 4. Legacy/Engine Hooks
    window.opacitySlider = document.getElementById('opacitySlider');
    window.speed = document.getElementById('speed');

    // Restore Sidebar Eye Toggles
    document.querySelectorAll('.eye-toggle').forEach(eye => {
        const id = eye.getAttribute('data-target');
        eye.onclick = (e) => {
            const el = document.getElementById(id);
            if (el) {
                const isOff = parseFloat(el.value) === 0;
                setTissueVisibility(id, isOff ? 1 : 0);
            }
            e.stopPropagation();
        };
    });

    // Default audio state
    const vol = document.getElementById('mute-btn');
    if (vol) vol.classList.add('off');

    setupAnatomicalExplorer();
}

// Detailed clinical impact notes: explains HOW each part is affected
const CLINICAL_NOTES = {
    'la': 'Posterior wall shows elevated hemodynamic stress. Dilation risk detected — reduced compliance may impair ventricular filling and promote stasis, increasing thromboembolic risk.',
    'ra': 'Atrial remodeling detected near SA node region. Altered electrical conduction may predispose to arrhythmogenic foci and impaired sinus rhythm generation.',
    'lv': 'Myocardial strain indicates reduced ejection fraction potential. Wall motion abnormality suggests ischemic insult — systolic dysfunction risk elevated.',
    'rv': 'Right ventricular outflow tract shows pressure overload markers. Elevated pulmonary resistance may cause progressive dilation and tricuspid regurgitation.',
    'Largevessels': 'Aortic arch exhibits elevated wall shear stress (TAWSS). Endothelial damage risk elevated — potential atherogenic zone with plaque formation susceptibility.',
    'Smallvessels': 'Micro-vessel network shows TAWSS stress concentrations. Capillary perfusion deficit identified — localized tissue ischemia may develop in affected territories.',
    'SVenaCava': 'Superior vena cava shows flow turbulence at junction. Altered venous return dynamics may indicate right-sided pressure elevation.',
    'IVenaCava': 'Inferior vena cava diameter variability detected. Reduced compliance suggests elevated right atrial pressure and possible fluid overload.',
    'Pulmonaryvessels': 'Pulmonary vasculature shows resistance elevation. Flow impedance may indicate early pulmonary hypertension — right heart workload increased.',
    'Heartmuscles': 'Myocardial tissue shows fibrosis markers (image-derived). Scar tissue reduces contractile function and may serve as substrate for re-entrant arrhythmias.',
    'sanvan': 'Conduction pathway delay detected. AV node remodeling may impair synchronization between atrial and ventricular contractions.',
    'internal': 'Structural lattice shows calcification markers. Increased stiffness may impair diastolic relaxation and elevate filling pressures.',
    'bicuspid': 'Mitral valve leaflet shows thickening. Possible stenosis or prolapse — regurgitant jet may cause left atrial volume overload.',
    'tricuspid': 'Tricuspid annular dilation detected. Incomplete leaflet coaptation may result in regurgitation and atrial volume overload.',
    'valves': 'Semilunar valve apparatus shows calcific deposits. Narrowed orifice area restricts outflow — pressure gradient across valve elevated.'
};

// Severity icon based on percentage
function _getSeverityIcon(sev) {
    if (sev >= 0.85) return '🔴';
    if (sev >= 0.65) return '🟠';
    if (sev >= 0.45) return '🟡';
    return '🟢';
}

function _getSeverityLabel(sev) {
    if (sev >= 0.85) return 'CRITICAL';
    if (sev >= 0.65) return 'HIGH';
    if (sev >= 0.45) return 'MODERATE';
    return 'LOW';
}

function setupAnatomicalExplorer() {
    const list = document.getElementById('parts-explorer-list');
    const details = document.getElementById('part-details-box');
    const partNameEl = document.getElementById('selected-part-name');
    const notesEl = document.getElementById('part-notes-text');
    const closeBtn = document.getElementById('close-details-btn');
    const separateBtn = document.getElementById('mode-separate');
    const fullBtn = document.getElementById('mode-full');
    if (!list) return;

    // ── Initial state: show a waiting placeholder ──
    _showWaitingState();

    // Check if data already arrived before we were ready
    if (LAUSM_AFFECTED_PARTS && LAUSM_AFFECTED_PARTS.parts) {
        const d = LAUSM_AFFECTED_PARTS;
        setTimeout(() => window._explorerSetAffected(d.parts, d.severity, d.labels || {}), 100);
    }

    function _showWaitingState() {
        list.innerHTML = `
            <div style="padding:20px 12px; text-align:center; color:#4b5563;">
                <div style="font-size:1.8rem; margin-bottom:8px;">🫀</div>
                <div style="font-size:0.8rem; font-weight:600; color:#6366f1; margin-bottom:4px;">LAUSM Analysis Pending</div>
                <div style="font-size:0.72rem; color:#374151; line-height:1.5;">Affected regions will be highlighted here once LAUSM data is loaded from the API key.</div>
            </div>`;
    }

    // ── Called by _rebuildExplorerForAffected (from postMessage) ──
    window._explorerSetAffected = function (ap, sv, labels) {
        if (!list) return;

        // Also hide the old static details box — we render inline now
        if (details) details.style.display = 'none';

        list.innerHTML = '';

        // Header with count
        const hdr = document.createElement('div');
        hdr.style.cssText = 'padding:8px 10px 10px; font-size:0.62rem; font-weight:800; letter-spacing:0.12em; text-transform:uppercase; color:#ef4444; display:flex; align-items:center; gap:6px; border-bottom:1px solid rgba(239,68,68,0.18); margin-bottom:6px;';
        hdr.innerHTML = `<span style="width:6px;height:6px;border-radius:50%;background:#ef4444;display:inline-block;animation:pulse-fade 1.2s infinite;"></span> ${ap.length} Affected Region${ap.length > 1 ? 's' : ''} Detected`;
        list.appendChild(hdr);

        let openTid = null;   // which item is currently expanded

        ap.forEach(tid => {
            if (!TISSUE_MAP[tid]) return;
            const name = TISSUE_MAP[tid];
            const label = labels[tid] || name;
            const sev = sv[tid] || 0;
            const sevPct = Math.round(sev * 100);
            const sevColor = sev >= 0.85 ? '#ef4444' : sev >= 0.65 ? '#f59e0b' : '#10b981';
            const sevIcon = _getSeverityIcon(sev);
            const sevLabel = _getSeverityLabel(sev);

            // ── Row item with severity icon ──
            const row = document.createElement('div');
            row.className = 'explorer-item';
            row.dataset.id = tid;
            row.style.cssText = `
                border-left: 3px solid ${sevColor};
                padding: 10px 12px 10px 10px;
                cursor: pointer;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-radius: 8px;
                transition: background 0.15s, transform 0.15s;
                flex-wrap: nowrap;
                gap: 6px;
                margin-bottom: 2px;
            `;
            row.innerHTML = `
                <div style="display:flex; align-items:center; gap:8px; flex:1; min-width:0;">
                    <span style="font-size:1rem; flex-shrink:0;" title="${sevLabel} — ${sevPct}% affected">${sevIcon}</span>
                    <div style="min-width:0;">
                        <div style="font-weight:700; color:#f1f5f9; font-size:0.82rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${name}</div>
                        <div style="font-size:0.62rem; color:#64748b; margin-top:1px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${label}</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:6px; flex-shrink:0;">
                    <div style="text-align:right;">
                        <div style="font-size:0.78rem; font-weight:800; color:${sevColor}; line-height:1;">${sevPct}%</div>
                        <div style="font-size:0.52rem; font-weight:700; color:${sevColor}; opacity:0.7; text-transform:uppercase; letter-spacing:0.05em;">${sevLabel}</div>
                    </div>
                    <span class="expand-arrow" style="font-size:0.7rem; color:#475569; transition:transform 0.2s;">▼</span>
                </div>
            `;

            // ── Inline detail card (hidden initially) ──
            const card = document.createElement('div');
            card.style.cssText = `
                display: none;
                flex-direction: column;
                gap: 8px;
                margin: -2px 0 6px 0;
                padding: 14px;
                background: rgba(0,0,0,0.4);
                border: 1px solid ${sevColor}30;
                border-top: none;
                border-radius: 0 0 10px 10px;
                animation: slideUp 0.2s ease-out;
            `;

            // Clinical impact note with icon marker
            const clinicalNote = CLINICAL_NOTES[tid] || 'Hemodynamic stress detected in this anatomical region.';

            card.innerHTML = `
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:2px;">
                    <div style="width:28px; height:28px; border-radius:8px; background:${sevColor}18; border:1px solid ${sevColor}40; display:flex; align-items:center; justify-content:center; font-size:0.9rem; flex-shrink:0;">${sevIcon}</div>
                    <div>
                        <div style="font-size:0.7rem; font-weight:800; letter-spacing:0.08em; text-transform:uppercase; color:${sevColor};">${sevLabel} INVOLVEMENT — ${sevPct}%</div>
                        <div style="font-size:0.58rem; color:#475569; margin-top:1px;">Stress index: ${(sev).toFixed(2)} | Region: ${name}</div>
                    </div>
                </div>
                <div style="height:5px; border-radius:3px; background:rgba(255,255,255,0.06); overflow:hidden;">
                    <div style="height:100%; width:${sevPct}%; background:linear-gradient(90deg,${sevColor}aa,${sevColor}); border-radius:3px; transition:width 0.6s;"></div>
                </div>
                <div style="display:flex; gap:8px; align-items:flex-start; padding:8px 10px; background:rgba(255,255,255,0.02); border-radius:8px; border:1px solid rgba(255,255,255,0.05);">
                    <span style="flex-shrink:0; font-size:0.85rem; margin-top:1px;">📋</span>
                    <div style="font-size:0.72rem; color:#94a3b8; line-height:1.55;">
                        ${clinicalNote}
                    </div>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-top:2px;">
                    <button data-mode="separate" style="
                        padding:8px 4px; font-size:0.62rem; font-weight:700; text-transform:uppercase;
                        border-radius:6px; cursor:pointer; border:1px solid rgba(59,130,246,0.3);
                        background:rgba(59,130,246,0.08); color:#93c5fd; transition:0.18s;
                        letter-spacing:0.05em;
                    " onmouseover="this.style.background='rgba(59,130,246,0.22)'" 
                       onmouseout="if(!this.classList.contains('active-mode'))this.style.background='rgba(59,130,246,0.08)'">
                        ⊡ Separate Mode
                    </button>
                    <button data-mode="full" style="
                        padding:8px 4px; font-size:0.62rem; font-weight:700; text-transform:uppercase;
                        border-radius:6px; cursor:pointer; border:1px solid rgba(0,209,255,0.3);
                        background:rgba(0,209,255,0.12); color:#67e8f9; transition:0.18s;
                        letter-spacing:0.05em;
                    " onmouseover="this.style.background='rgba(0,209,255,0.22)'"
                       onmouseout="if(!this.classList.contains('active-mode'))this.style.background='rgba(0,209,255,0.12)'">
                        ⊞ Full Mode
                    </button>
                </div>
            `;

            // Wire mode buttons inside the inline card
            const [sepBtn, fullBtnInline] = card.querySelectorAll('button[data-mode]');

            function setModeActive(mode) {
                if (sepBtn) {
                    sepBtn.classList.toggle('active-mode', mode === 'separate');
                    sepBtn.style.background = mode === 'separate' ? 'rgba(59,130,246,0.28)' : 'rgba(59,130,246,0.08)';
                }
                if (fullBtnInline) {
                    fullBtnInline.classList.toggle('active-mode', mode === 'full');
                    fullBtnInline.style.background = mode === 'full' ? 'rgba(0,209,255,0.28)' : 'rgba(0,209,255,0.12)';
                }
                _syncGlobalModeButtons(mode);
            }

            sepBtn.onclick = (e) => {
                e.stopPropagation();
                _applyAffectedParts([tid], { [tid]: sev }, 'separate');
                setModeActive('separate');
            };
            fullBtnInline.onclick = (e) => {
                e.stopPropagation();
                _applyAffectedParts(ap, sv, 'full');
                setModeActive('full');
            };

            // ── Toggle row click ──
            row.onclick = () => {
                const isOpen = openTid === tid;

                // Close any open card
                list.querySelectorAll('.inline-detail-card').forEach(c => {
                    c.style.display = 'none';
                });
                list.querySelectorAll('.explorer-item .expand-arrow').forEach(a => {
                    a.style.transform = '';
                });
                list.querySelectorAll('.explorer-item').forEach(r => r.classList.remove('active'));

                if (isOpen) {
                    // Clicked again → collapse, reset heart
                    openTid = null;
                    _applyAffectedParts(ap, sv, 'full');
                    if (separateBtn) separateBtn.classList.remove('active');
                    if (fullBtn) fullBtn.classList.add('active');
                } else {
                    // Open this one
                    openTid = tid;
                    row.classList.add('active');
                    row.querySelector('.expand-arrow').style.transform = 'rotate(180deg)';
                    card.style.display = 'flex';
                    // Default = Full Mode on open
                    _applyAffectedParts([tid], { [tid]: sev }, 'full');
                    setModeActive('full');
                    // Scroll card into view
                    setTimeout(() => card.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 50);
                }
            };

            list.appendChild(row);
            card.classList.add('inline-detail-card');
            list.appendChild(card);
        });

        // ── Render Floating 3D Markers ──
        _renderFloatingMarkers(ap, sv, labels);

        // ── Global Mode Sync Logic ──
        function _syncGlobalModeButtons(mode) {

            if (separateBtn) separateBtn.classList.toggle('active', mode === 'separate');
            if (fullBtn) fullBtn.classList.toggle('active', mode === 'full');
        }

        // --- Global Button Wiring (OUTSIDE the loop) ---
        if (separateBtn) {
            separateBtn.onclick = () => {
                _applyAffectedParts(ap, sv, 'separate');
                _syncGlobalModeButtons('separate');
                list.querySelectorAll('.inline-detail-card').forEach(c => c.style.display = 'none');
            };
        }
        if (fullBtn) {
            fullBtn.onclick = () => {
                _applyAffectedParts(ap, sv, 'full');
                _syncGlobalModeButtons('full');
                list.querySelectorAll('.inline-detail-card').forEach(c => c.style.display = 'none');
            };
        }
    };
}

// Fixed rough screen positions for standard frontal heart view
const ANATOMY_POSITIONS = {
    'la': { top: '35%', left: '55%' },
    'ra': { top: '48%', left: '42%' },
    'lv': { top: '65%', left: '56%' },
    'rv': { top: '65%', left: '45%' },
    'Heartmuscles': { top: '55%', left: '50%' },
    'Largevessels': { top: '22%', left: '48%' },
    'Smallvessels': { top: '65%', left: '38%' },
    'Pulmonaryvessels': { top: '38%', left: '58%' },
    'SVenaCava': { top: '25%', left: '41%' },
    'IVenaCava': { top: '78%', left: '40%' },
    'bicuspid': { top: '45%', left: '52%' },
    'tricuspid': { top: '50%', left: '48%' },
    'sanvan': { top: '40%', left: '46%' },
    'internal': { top: '50%', left: '50%' }
};

function _renderFloatingMarkers(ap, sv, labels) {
    let container = document.getElementById('viewport-container');
    if (!container) return;

    // Clear old markers if any
    document.querySelectorAll('.anatomical-marker').forEach(el => el.remove());

    container.style.position = 'relative';

    ap.forEach((tid, index) => {
        if (!ANATOMY_POSITIONS[tid]) return;

        const pos = ANATOMY_POSITIONS[tid];
        const sev = sv[tid] || 0;
        const sevPct = Math.round(sev * 100);
        const name = TISSUE_MAP[tid];
        const sevColor = sev >= 0.85 ? '#ef4444' : sev >= 0.65 ? '#f59e0b' : '#10b981';

        const marker = document.createElement('div');
        marker.className = 'anatomical-marker';
        marker.style.top = pos.top;
        marker.style.left = pos.left;
        marker.style.setProperty('--marker-color', sevColor);
        // Stagger animation
        marker.style.animationDelay = `${index * 0.15}s`;

        marker.innerHTML = `
            <div class="marker-dot-wrapper">
                <div class="marker-pulse"></div>
                <div class="marker-dot"></div>
            </div>
            <div class="marker-label">
                <span class="pct">${sevPct}%</span> ${name}
            </div>
        `;

        container.appendChild(marker);
    });
}

window.onload = init;

// Remote highlight bridge
let LAUSM_AFFECTED_PARTS = null; // persisted across mode switches
let LAUSM_CURRENT_MODE = 'full';

window.addEventListener('message', (e) => {
    if (!e.data) return;

    // --- Single-part highlight (legacy) ---
    if (e.data.type === 'highlight') {
        const p = e.data.part;
        const v = e.data.intensity || 1.0;
        if (p && TISSUE_MAP[p]) {
            setTissueVisibility(p, v);
            console.log("Highlighting tissue:", p);
        }
        return;
    }

    // --- Multi-part highlight from LAUSM affected_parts analysis ---
    if (e.data.type === 'highlight_affected') {
        const ap = e.data.affected_parts || [];       // ["la", "bicuspid", …]
        const sv = e.data.severity || {};       // {"la": 0.90, …}
        const mode = e.data.mode || 'full';   // 'full' | 'separate'

        if (ap.length === 0) return;

        LAUSM_AFFECTED_PARTS = { parts: ap, severity: sv };
        LAUSM_CURRENT_MODE = mode;

        _applyAffectedParts(ap, sv, mode);

        // Rebuild the Anatomical Explorer to show ONLY affected parts
        _rebuildExplorerForAffected(e.data);
        return;
    }

    // --- Mode switch from parent (e.g. Analyze dashboard sends 'switch_mode') ---
    if (e.data.type === 'switch_mode' && LAUSM_AFFECTED_PARTS) {
        LAUSM_CURRENT_MODE = e.data.mode || 'full';
        _applyAffectedParts(
            LAUSM_AFFECTED_PARTS.parts,
            LAUSM_AFFECTED_PARTS.severity,
            LAUSM_CURRENT_MODE
        );
    }
});

function _applyAffectedParts(parts, severity, mode) {
    Object.keys(TISSUE_MAP).forEach(id => {
        const isAffected = parts.includes(id);
        let vis;
        if (mode === 'separate') {
            vis = isAffected ? Math.max(0.8, severity[id] || 1.0) : 0.0;
        } else { // 'full'
            // Highlight affected (min 0.8), ghost others at 0.2 for high contrast
            vis = isAffected ? Math.max(0.8, severity[id] || 1.0) : 0.2;
        }
        setTissueVisibility(id, vis);
    });
}

function _rebuildExplorerForAffected(data) {
    const ap = data.affected_parts || [];
    const sv = data.severity || {};
    const labels = data.labels || {};
    if (typeof window._explorerSetAffected === 'function') {
        window._explorerSetAffected(ap, sv, labels);
    }
}

// ─── Auto-fetch LAUSM data from server if not received via postMessage ───
// Wait a few seconds after page load; if no data arrived from parent iframe,
// attempt to fetch the latest LAUSM affected parts analysis from the server.
setTimeout(() => {
    if (LAUSM_AFFECTED_PARTS) return; // Data already received via postMessage

    fetch('/api/latest-lausm-affected')
        .then(res => {
            if (!res.ok) throw new Error('No LAUSM data');
            return res.json();
        })
        .then(data => {
            if (!data.affected_parts || data.affected_parts.length === 0) return;

            console.log('[Digital Twin] Auto-loaded LAUSM affected parts from server:', data);

            LAUSM_AFFECTED_PARTS = {
                parts: data.affected_parts,
                severity: data.severity
            };
            LAUSM_CURRENT_MODE = 'full';

            _applyAffectedParts(data.affected_parts, data.severity, 'full');
            _rebuildExplorerForAffected(data);
        })
        .catch(err => {
            console.log('[Digital Twin] No LAUSM data available from server:', err.message);
        });
}, 2500);
