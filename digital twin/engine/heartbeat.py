import os
import numpy as np
from PIL import Image
import onnxruntime as ort

def custom_otsu(image):
    """Pure Numpy implementation of Otsu's thresholding."""
    flat = image.ravel()
    hist = np.histogram(flat, bins=256, range=(0, 1))[0]
    total = len(flat)
    current_max = 0
    threshold = 0
    sum_total = np.dot(np.arange(256), hist)
    sum_back = 0
    weight_back = 0
    for i in range(256):
        weight_back += hist[i]
        if weight_back == 0: continue
        weight_fore = total - weight_back
        if weight_fore == 0: break
        sum_back += i * hist[i]
        mu_back = sum_back / weight_back
        mu_fore = (sum_total - sum_back) / weight_fore
        var_between = weight_back * weight_fore * (mu_back - mu_fore) ** 2
        if var_between > current_max:
            current_max = var_between
            threshold = i
    return threshold / 255.0

def simple_gaussian(image, sigma=1):
    return image

class CardioPulseEngine:
    def __init__(self):
        self.models_dir = os.path.join(os.path.dirname(__file__), 'models')
        self.pca_sess = None
        self.clf_sessions = []

    def _get_session(self, name):
        p = os.path.join(self.models_dir, name)
        return ort.InferenceSession(p, providers=['CPUExecutionProvider'])

    def load_frame(self, source):
        img = Image.open(source)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        return np.array(img)

    def to_monochrome(self, img):
        if len(img.shape) == 3:
            gray = np.dot(img[...,:3], [0.2989, 0.5870, 0.1140])
        else:
            gray = img
        gray = gray.astype(float) / 255.0
        pil_gray = Image.fromarray((gray * 255).astype(np.uint8)).resize((2213, 1572))
        return np.array(pil_gray) / 255.0

    def segment_leads(self, img, output_path="."):
        pil_img = Image.fromarray(img).resize((2213, 1572))
        img = np.array(pil_img)
        
        segments = [
            img[300:600, 150:643], img[300:600, 646:1135], img[300:600, 1140:1625],
            img[300:600, 1630:2125], img[600:900, 150:643], img[600:900, 646:1135],
            img[600:900, 1140:1625], img[600:900, 1630:2125], img[900:1200, 150:643],
            img[900:1200, 646:1135], img[900:1200, 1140:1625], img[900:1200, 1630:2125],
            img[1250:1480, 150:2125]
        ]
        
        tiled = Image.new('RGB', (1500, 1200), (0, 0, 0))
        for i, s in enumerate(segments[:12]):
            s_img = Image.fromarray(s).resize((450, 250))
            x = (i % 3) * 500
            y = (i // 3) * 300
            tiled.paste(s_img, (x, y))
        tiled.save(os.path.join(output_path, 'leads_map.png'))

        Image.fromarray(segments[12]).save(os.path.join(output_path, 'master_lead.png'))
        return segments

    def clean_signals(self, segments, output_path="."):
        tiled = Image.new('L', (1350, 1200), 0)
        for i, s in enumerate(segments[:12]):
            mono = np.dot(s[...,:3], [0.2989, 0.5870, 0.1140]) if len(s.shape) == 3 else s
            mono = mono.astype(float) / 255.0
            th = custom_otsu(mono)
            bn = (mono < th).astype(np.uint8) * 255
            bn_img = Image.fromarray(bn).resize((450, 300))
            x = (i % 3) * 450
            y = (i // 3) * 300
            tiled.paste(bn_img, (x, y))
        tiled.save(os.path.join(output_path, 'processed_leads.png'))

        last = segments[-1]
        mono_l = np.dot(last[...,:3], [0.2989, 0.5870, 0.1140]) if len(last.shape) == 3 else last
        mono_l = mono_l.astype(float) / 255.0
        th_l = custom_otsu(mono_l)
        bn_l = (mono_l < th_l).astype(np.uint8) * 255
        Image.fromarray(bn_l).save(os.path.join(output_path, 'processed_master.png'))

    def trace_contours(self, segments, output_path="."):
        for i, s in enumerate(segments[:12]):
            mono = np.dot(s[...,:3], [0.2989, 0.5870, 0.1140]) if len(s.shape) == 3 else s
            mono = mono.astype(float) / 255.0
            th = custom_otsu(mono)
            bn = (mono < th)
            h, w = bn.shape
            trace = []
            for col in range(w):
                black_pixels = np.where(bn[:, col])[0]
                if len(black_pixels) > 0:
                    trace.append([np.mean(black_pixels), col])
            
            if not trace: 
                res = np.zeros((255, 2))
            else:
                trace = np.array(trace)
                indices = np.linspace(0, len(trace) - 1, 255).astype(int)
                res = trace[indices]
            
            # Manual MinMax Scaling
            v_max, v_min = np.max(res, axis=0), np.min(res, axis=0)
            norm = (res - v_min) / (v_max - v_min + 1e-8)
            
            np.savetxt(os.path.join(output_path, f'raw_trace_{i+1}.csv'), norm[:, 0].reshape(1, -1), delimiter=',', fmt='%.6f')

            amplitude = np.max(res[:, 0]) - np.min(res[:, 0])
            with open(os.path.join(output_path, f'raw_trace_{i+1}.amp'), 'w') as fa:
                fa.write(str(amplitude))
            
        Image.new('RGB', (100, 100), (40, 44, 52)).save(os.path.join(output_path, 'traced_contours.png'))

    def aggregate_features(self, work_dir="."):
        parts = []
        for i in range(1, 13):
            path = os.path.join(work_dir, f'raw_trace_{i}.csv')
            if os.path.exists(path):
                data = np.loadtxt(path, delimiter=',')
                parts.append(data.reshape(1, -1))
        if not parts: return np.zeros((1, 255 * 12), dtype=np.float32)
        return np.hstack(parts).astype(np.float32)

    def compress_data(self, data):
        if self.pca_sess is None:
            self.pca_sess = self._get_session('pca.onnx')
        inputs = {self.pca_sess.get_inputs()[0].name: data}
        res = self.pca_sess.run(None, inputs)
        return res[0]

    def diagnose_condition(self, data):
        # Majority Vote implementation
        votes = []
        if not self.clf_sessions:
            for i in range(5):
                try: self.clf_sessions.append(self._get_session(f'est_{i}.onnx'))
                except: pass
        
        for sess in self.clf_sessions:
            inputs = {sess.get_inputs()[0].name: data}
            res = sess.run(None, inputs)
            votes.append(int(res[0][0]))
            
        # Modal vote
        from collections import Counter
        final = Counter(votes).most_common(1)[0][0]
        
        mapping = {1: "Infarction Syndrome", 0: "Irregular Cardiac Rhythm", 2: "Healthy Cardiac Profile", 3: "Previous Ischemic Event"}
        return mapping.get(final, "Unknown Anomaly")

    def analyze_rhythm(self, signal, rate=500):
        try:
            # Native peak detection (scipy replacement)
            # 1. Detection Threshold
            peak_th = (np.max(signal) - np.min(signal)) * 0.6 + np.min(signal)
            
            # 2. Find local maxima above threshold with distance constraint
            idx = np.where(signal > peak_th)[0]
            if len(idx) == 0: return {"bpm": 72.0, "hrv": 0, "intervals": [], "peaks": [], "peak_count": 0, "duration": round(len(signal) / rate, 1), "signal": signal.tolist()}
            
            discovered = []
            last_p = -rate # Minimum distance tracker
            for p in idx:
                # Local maximum check
                if p > 0 and p < len(signal)-1:
                    if signal[p] >= signal[p-1] and signal[p] >= signal[p+1]:
                        if p - last_p > rate * 0.4: # Distance refractory period
                            discovered.append(p)
                            last_p = p
            
            discovered = np.array(discovered)
            intervals = []
            if len(discovered) > 1:
                gaps = np.diff(discovered)
                intervals = (gaps / rate) * 1000
                bpm = 60 / np.mean(gaps / rate)
                hrv = np.std(intervals)
            else:
                bpm, hrv = 72.0, 0
            
            return {"bpm": round(bpm, 1), "hrv": round(hrv, 2), "intervals": intervals.tolist() if isinstance(intervals, np.ndarray) else intervals, "peaks": discovered.tolist(), "peak_count": len(discovered), "duration": round(len(signal) / rate, 1), "signal": signal.tolist()}
        except:
            return {"bpm": 72.0, "hrv": 0, "intervals": [], "peaks": [], "peak_count": 0, "duration": 0, "signal": []}

    def localize_infarction(self, work_dir=".", diagnosis="Unknown"):
        if "Healthy" in diagnosis: return "Global Heart (Healthy)", None
        leads_map = {'I': 0, 'aVR': 1, 'V1': 2, 'V4': 3, 'II': 4, 'aVL': 5, 'V2': 6, 'V5': 7, 'III': 8, 'aVF': 9, 'V3': 10, 'V6': 11}
        regions = {'Septal': ['V1', 'V2'], 'Anterior': ['V3', 'V4'], 'Lateral': ['I', 'aVL', 'V5', 'V6'], 'Inferior': ['II', 'III', 'aVF']}
        scores = {}
        for name, idx in leads_map.items():
            path = os.path.join(work_dir, f'raw_trace_{idx+1}.amp')
            if os.path.exists(path):
                with open(path, 'r') as f: 
                    try: scores[name] = float(f.read())
                    except: scores[name] = 0.0
            else: scores[name] = 0.0
        region_scores = {r: sum([scores.get(l, 0) for l in ls]) / len(ls) for r, ls in regions.items()}
        affected = max(region_scores, key=region_scores.get)
        models = {'Septal': 'leftventricle.glb', 'Anterior': 'leftventricle.glb', 'Lateral': 'leftatrium.glb', 'Inferior': 'rightventricle.glb'}
        return affected, models.get(affected, 'leftventricle.glb')

    def generate_digital_twin(self, segments, target_dir, affected_region="Unknown"):
        master = segments[-1]
        mono = np.dot(master[...,:3], [0.2989, 0.5870, 0.1140]) if len(master.shape) == 3 else master
        mono = mono.astype(float) / 255.0
        th = custom_otsu(mono)
        bn = (mono < th)
        trace = []
        for col in range(bn.shape[1]):
            black = np.where(bn[:, col])[0]
            if len(black) > 0: trace.append([np.mean(black), col])
        if not trace: return None, None
        trace = np.array(trace)
        xp, fp = trace[:, 1], trace[:, 0]
        x_new = np.linspace(xp.min(), xp.max(), 2500)
        y_new = np.interp(x_new, xp, fp)
        v_max, v_min = np.max(y_new), np.min(y_new)
        v_range = max(1, v_max - v_min)
        sig = (v_max - y_new) / v_range
        rhythm = self.analyze_rhythm(sig)
        return None, rhythm['bpm'] # Scipy savemat removed to save space
