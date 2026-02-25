import os
import shutil
import base64
import sys
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Add root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.heartbeat import CardioPulseEngine
import matplotlib
import matplotlib.image
import numpy as np
from skimage import color, measure
from skimage.filters import gaussian, threshold_otsu
from skimage.transform import resize

matplotlib.use('Agg')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

processor = CardioPulseEngine()
OUTPUT_CACHE = "results"
if not os.path.exists(OUTPUT_CACHE):
    os.makedirs(OUTPUT_CACHE)

@app.post("/predict-ecg")
async def process_pulse(file: UploadFile = File(...)):
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
        matplotlib.image.imsave(gray_path, mono, cmap='gray')

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

        for f in os.listdir(OUTPUT_CACHE):
            if f.startswith("raw_trace_") and f.endswith(".csv"):
                try: os.remove(os.path.join(OUTPUT_CACHE, f))
                except: pass

        
        # Generate digital twin file for Streamlit
        MATLAB_STORE = r"c:\2ndapp\results\history"
        if not os.path.exists(MATLAB_STORE): os.makedirs(MATLAB_STORE)
        mat_file, twin_bpm = processor.generate_digital_twin(channels, MATLAB_STORE)

        # Re-calculating rhythm for the response with safety checks
        rhythm_data = {
            "bpm": 72.0, "hrv": 0, "intervals": [], "peaks": [], 
            "peak_count": 0, "duration": 0, "signal": []
        }
        
        try:
            mono_m = color.rgb2gray(channels[-1])
            sh_m = gaussian(mono_m, sigma=0.7)
            th_m = threshold_otsu(sh_m)
            bn_m = sh_m < th_m
            ct_m = measure.find_contours(bn_m, 0.8)
            if ct_m:
                # Find the longest contour (likely the main ECG trace)
                c = max(ct_m, key=lambda x: len(x))
                
                # Sort points by column (x-axis / time) to ensure it's a valid time-series
                c = c[c[:, 1].argsort()]
                
                # Resample to 2500 points using linear interpolation
                xp = c[:, 1]
                fp = c[:, 0]
                x_new = np.linspace(xp.min(), xp.max(), 2500)
                y_new = np.interp(x_new, xp, fp)
                
                # Correct normalization: (Max - val) / Range ensures top of image is 1.0 (peak)
                v_max = np.max(y_new)
                v_min = np.min(y_new)
                v_range = max(1, v_max - v_min)
                sig_m = (v_max - y_new) / v_range
                
                rhythm_data = processor.analyze_rhythm(sig_m)
        except Exception as re:
            print(f"Rhythm Extraction Failure: {re}")

        # Cleanup CSV artifacts immediately
        for f in os.listdir(OUTPUT_CACHE):
            if f.startswith("raw_trace_") and f.endswith(".csv"):
                try: os.remove(os.path.join(OUTPUT_CACHE, f))
                except: pass

        return {
            "prediction": diagnosis,
            "images": visuals,
            "signal_1d": features.head(5).to_dict(orient='records'),
            "dimensional_reduction": compressed.head(5).to_dict(orient='records'),
            "bpm": rhythm_data['bpm'],
            "rhythm": rhythm_data,
            "mat_file_generated": mat_file
        }

    except Exception as e:
        print(f"Module Failure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def read_index():
    return FileResponse(r"c:\2ndapp\static\index.html")

# Mount static files at root AFTER routes to serve assets correctly
app.mount("/", StaticFiles(directory=r"c:\2ndapp\static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
