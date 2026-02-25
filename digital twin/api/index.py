import json
import uuid
import sys
import os
import shutil
import requests
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from PIL import Image
import numpy as np

# Add root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.heartbeat import CardioPulseEngine

app = FastAPI()
processor = CardioPulseEngine()

import base64

# Cloudflare Configuration
CLOUDFLARE_API_TOKEN = "Zf4KQzWy821avREP7gMGU-T1g0qgWoV2mHSlJC1k"
CLOUDFLARE_ACCOUNT_ID = "beb7787ed2562d195ccdd4d66f8c4e70"

def run_ml_task(model, input_data):
    if CLOUDFLARE_ACCOUNT_ID.startswith("Please"):
        return {"error": "Missing Cloudflare Account ID. Please update api/index.py"}
        
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{model}"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    try:
        print(f"DEBUG: Calling CF AI Model {model}")
        response = requests.post(url, headers=headers, json=input_data)
        print(f"DEBUG: CF Status {response.status_code}")
        if response.status_code != 200:
            print(f"DEBUG: CF Error Body: {response.text}")
        return response.json()
    except Exception as e:
        print(f"DEBUG: CF Exception: {e}")
        return {"error": str(e)}

@app.post("/chat")
async def chat_endpoint(payload: dict):
    message = payload.get("message", "")
    context = payload.get("context", {})
    
    # 1. Image Generation Intent
    if any(k in message.lower() for k in ["generate image", "create an image", "draw", "visualize"]):
        prompt = message.replace("generate image", "").replace("create an image", "").strip()
        # Use context to enhance prompt if available
        if context and context.get("prediction"):
             prompt = f"{prompt}, medical illustration style, {context.get('prediction')} heart condition"
             
        res = run_ml_task("@cf/bytedance/stable-diffusion-xl-lightning", {"prompt": prompt})
        
        if res.get("success") and res.get("result"):
            url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/bytedance/stable-diffusion-xl-lightning"
            headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
            img_res = requests.post(url, headers=headers, json={"prompt": prompt})
            if img_res.status_code == 200:
                b64 = base64.b64encode(img_res.content).decode("utf-8")
                return {"response": f"Generated image for: {prompt}", "image": f"data:image/png;base64,{b64}"}
            else:
                 return {"response": "Failed to generate image via Cloudflare."}
        else:
             return {"response": "Image generation service unavailable or configured incorrectly."}

    # 2. Text Chat
    system_prompt = "You are Doc, a specialized Medical Assistant for Cardiac Analysis developed by SURESHKUMAR S. Use the provided patient data to answer questions. If asked about your developer, creator, or who made you, always credit SURESHKUMAR S."
    if context:
        system_prompt += f"\n\nCurrent Patient Analysis:\nDiagnosis: {context.get('prediction')}\nBPM: {context.get('bpm')}\nPeaks Detected: {context.get('peak_count', 'N/A')}\n"
    
    inputs = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
    }
    
    res = run_ml_task("@cf/meta/llama-3-8b-instruct", inputs)
    
    if res.get("success") and "result" in res:
        return {"response": res["result"]["response"]}
    
    err = res.get("error", "Unknown Error")
    if "Missing Cloudflare Account ID" in str(err):
        return {"response": "⚠️ SYSTEM CONFIG ERROR: Cloudflare Account ID is missing. Open `api/index.py` and set `CLOUDFLARE_ACCOUNT_ID`."}
        
    return {"response": "I'm having trouble connecting to the neural network right now.", "debug": res}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    # Security Headers
    response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    # Simplified single-line CSP to avoid h11 validation errors
    response.headers["Content-Security-Policy"] = "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; font-src * data:; frame-src 'self' https://accounts.google.com http://localhost:8501; img-src * data: blob:; script-src * 'unsafe-inline' 'unsafe-eval';"
    return response

# Vercel's only writable directory is /tmp
if os.name == 'posix':
    OUTPUT_CACHE = "/tmp/results"
else:
    OUTPUT_CACHE = os.path.join(os.getcwd(), "results")

HISTORY_DB = os.path.join(OUTPUT_CACHE, "history_db.json")

if not os.path.exists(OUTPUT_CACHE):
    os.makedirs(OUTPUT_CACHE, exist_ok=True)

if not os.path.exists(HISTORY_DB):
    with open(HISTORY_DB, 'w') as f:
        json.dump({}, f)

def save_history(email, entry):
    if not email: return
    try:
        db = {}
        if os.path.exists(HISTORY_DB):
            with open(HISTORY_DB, 'r') as f:
                try: db = json.load(f)
                except: db = {}
        
        if email not in db: db[email] = []
        
        # Add timestamp and ID
        entry['id'] = str(uuid.uuid4())
        entry['timestamp'] = datetime.now().isoformat()
        
        # We don't want to store huge base64 strings in the main DB list for performance
        # So we save the full result to a separate file and just keep metadata in the list
        details_file = os.path.join(OUTPUT_CACHE, f"analysis_{entry['id']}.json")
        with open(details_file, 'w') as f:
            json.dump(entry, f)
            
        summary = {
            'id': entry['id'],
            'timestamp': entry['timestamp'],
            'prediction': entry.get('prediction', 'Unknown'),
            'bpm': entry.get('bpm', 0),
            'filename': entry.get('filename', 'scan.png')
        }
        
        db[email].insert(0, summary) # Prepend to show newest first
        
        with open(HISTORY_DB, 'w') as f:
            json.dump(db, f)
    except Exception as e:
        print(f"History Save Error: {e}")

@app.get("/history/{user_email}")
async def get_history(user_email: str):
    try:
        if os.path.exists(HISTORY_DB):
            with open(HISTORY_DB, 'r') as f:
                db = json.load(f)
                return db.get(user_email, [])
        return []
    except Exception as e:
        print(f"History Read Error: {e}")
        return []

@app.get("/history/item/{item_id}")
async def get_history_item(item_id: str):
    rect_path = os.path.join(OUTPUT_CACHE, f"analysis_{item_id}.json")
    if os.path.exists(rect_path):
        with open(rect_path, 'r') as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Analysis not found")

@app.post("/predict-ecg")
async def process_pulse(file: UploadFile = File(...), email: str = Form(None)):
    try:
        temp_input = os.path.join(OUTPUT_CACHE, file.filename)
        with open(temp_input, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        raw = processor.load_frame(temp_input)
        mono = processor.to_monochrome(raw)
        channels = processor.segment_leads(raw, output_path=OUTPUT_CACHE)
        processor.clean_signals(channels, output_path=OUTPUT_CACHE)
        processor.trace_contours(channels, output_path=OUTPUT_CACHE)
        
        features = processor.aggregate_features(work_dir=OUTPUT_CACHE)
        compressed = processor.compress_data(features)
        diagnosis = processor.diagnose_condition(compressed)

        gray_path = os.path.join(OUTPUT_CACHE, "mono_preview.png")
        Image.fromarray((mono * 255).astype(np.uint8)).save(gray_path)

        def to_b64(name):
            p = os.path.join(OUTPUT_CACHE, name)
            if os.path.exists(p):
                with open(p, "rb") as f:
                    return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
            return None

        visuals = {
            "original": to_b64(file.filename),
            "grayscale": to_b64("mono_preview.png"),
            "leads": to_b64("leads_map.png"),
            "long_lead": to_b64("master_lead.png"),
            "preprocessed": to_b64("processed_leads.png"),
            "preprocessed_long": to_b64("processed_master.png"),
            "contours": to_b64("traced_contours.png")
        }

        # Cleanup artifacts
        for f in os.listdir(OUTPUT_CACHE):
            if f.startswith("raw_trace_") and f.endswith(".csv"):
                try: os.remove(os.path.join(OUTPUT_CACHE, f))
                except: pass

        rhythm_data = {
            "bpm": 72.0, "hrv": 0, "intervals": [], "peaks": [], 
            "peak_count": 0, "duration": 0, "signal": []
        }
        
        # 1. Localization (Run ALWAYS)
        affected_region, affected_model = processor.localize_infarction(work_dir=OUTPUT_CACHE, diagnosis=diagnosis)
        
        # 2. Generate Digital Twin Data (pass affected region)
        mat_file, twin_bpm = processor.generate_digital_twin(channels, OUTPUT_CACHE, affected_region)
        
        try:
            # Simple rhythmic analysis on master lead (using native trace logic)
            master = channels[-1]
            mono_m = np.dot(master[...,:3], [0.2989, 0.5870, 0.1140]) if len(master.shape) == 3 else master
            mono_m = mono_m.astype(float) / 255.0
            
            # Simple trace extraction
            from engine.heartbeat import custom_otsu
            th_m = custom_otsu(mono_m)
            bn_m = (mono_m < th_m)
            
            trace_m = []
            for col in range(bn_m.shape[1]):
                black = np.where(bn_m[:, col])[0]
                if len(black) > 0: trace_m.append([np.mean(black), col])
            
            if trace_m:
                trace_m = np.array(trace_m)
                xp, fp = trace_m[:, 1], trace_m[:, 0]
                x_new = np.linspace(xp.min(), xp.max(), 2500)
                y_new = np.interp(x_new, xp, fp)
                v_max, v_min = np.max(y_new), np.min(y_new)
                v_range = max(1, v_max - v_min)
                sig_m = (v_max - y_new) / v_range
                rhythm_data = processor.analyze_rhythm(sig_m)
                if twin_bpm: rhythm_data['bpm'] = twin_bpm
        except Exception as re:
            print(f"Rhythm Extraction Failure: {re}")

        # Build results payload (Numpy compatible)
        result_payload = {
            "prediction": diagnosis,
            "affected_region": affected_region,
            "affected_model": affected_model,
            "images": visuals,
            "signal_1d": features[:5].tolist(), # Numpy to list
            "dimensional_reduction": compressed[:5].tolist(), # Numpy to list
            "bpm": rhythm_data['bpm'],
            "rhythm": rhythm_data,
            "mat_file_generated": mat_file,
            "filename": file.filename
        }
        
        if email:
            save_history(email, result_payload.copy())

        return result_payload

    except Exception as e:
        print(f"Module Failure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
