import os
import json
import math
import glob
import numpy as np
import scipy.io
from flask import Flask, render_template, request, Response

app = Flask(__name__)
app.secret_key = "heart_models_key"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEG_DIR = os.path.join(PROJECT_ROOT, "seg")

def safe_float(val):
    try:
        v = float(np.array(val).flatten()[0])
        if math.isnan(v) or math.isinf(v):
            return None
        return round(v, 3)
    except:
        return None

def safe_list(val, max_len=200):
    try:
        arr = np.array(val, dtype=float).flatten()
        arr = arr[np.isfinite(arr)]
        step = max(1, len(arr) // max_len)
        return arr[::step].tolist()
    except:
        return []

def safe_jsonify(data):
    """Serialise data to JSON, turning NaN/Infinity into null."""
    text = json.dumps(data, allow_nan=False,
                      default=lambda o: None if (isinstance(o, float) and (math.isnan(o) or math.isinf(o))) else str(o))
    return Response(text, mimetype="application/json")

def read_mat_file(filepath):
    try:
        data = scipy.io.loadmat(filepath)
        s = data['setstruct']

        result = {
            "filename": os.path.basename(filepath),
            "metrics": {},
            "contours": {},
            "info": {}
        }

        # Clinical metrics
        metric_fields = {
            "EDV":   "End-Diastolic Volume (ml)",
            "ESV":   "End-Systolic Volume (ml)",
            "EF":    "Ejection Fraction (%)",
            "LVM":   "LV Mass (g)",
            "SV":    "Stroke Volume (ml)",
            "RVEDV": "RV End-Diastolic Vol (ml)",
            "RVESV": "RV End-Systolic Vol (ml)",
            "RVEF":  "RV Ejection Fraction (%)",
        }
        for field, label in metric_fields.items():
            try:
                val = safe_float(s[field][0, 0])
                result["metrics"][field] = {"label": label, "value": val}
            except:
                result["metrics"][field] = {"label": label, "value": None}

        # Scalar info
        for f in ["HeartRate", "XSize", "YSize", "ZSize", "ResolutionX", "ResolutionY", "SliceThickness"]:
            try:
                result["info"][f] = safe_float(s[f][0, 0])
            except:
                result["info"][f] = None

        # Scanner & study info – strip MATLAB cell array brackets
        for f in ["Scanner", "Modality", "SeriesDescription"]:
            try:
                raw = s[f][0, 0]
                # May be ndarray of objects
                if hasattr(raw, 'flat'):
                    raw = next(iter(raw.flat), '')
                val = str(raw).strip().strip("[]'\"")
                result["info"][f] = val if val else "N/A"
            except:
                result["info"][f] = "N/A"

        # Contour data
        for contour_name, x_field, y_field in [
            ("LVEndo", "EndoX", "EndoY"),
            ("LVEpi",  "EpiX",  "EpiY"),
            ("RVEndo", "RVEndoX", "RVEndoY"),
        ]:
            try:
                x_data = np.array(s[x_field][0, 0], dtype=float)
                y_data = np.array(s[y_field][0, 0], dtype=float)
                if x_data.size > 0:
                    # Scan for non-empty slices if the first one is empty
                    if not np.any(x_data) or np.all(np.isnan(x_data)):
                        found_slice = False
                        # Try to find any slice that has data
                        # Flattening entire 2D/3D array usually works best for visualization
                        x_flat = x_data.flatten()
                        y_flat = y_data.flatten()
                        mask = np.isfinite(x_flat) & np.isfinite(y_flat) & (x_flat != 0) & (y_flat != 0)
                        if np.any(mask):
                            # Subsample if too large (> 1000 points)
                            step = max(1, np.sum(mask) // 500)
                            result["contours"][contour_name] = {
                                "x": x_flat[mask][::step].tolist(),
                                "y": y_flat[mask][::step].tolist()
                            }
                        else:
                            result["contours"][contour_name] = {"x": [], "y": []}
                    else:
                        x_slice = x_data.flatten()
                        y_slice = y_data.flatten()
                        mask = np.isfinite(x_slice) & np.isfinite(y_slice) & (x_slice != 0) & (y_slice != 0)
                        result["contours"][contour_name] = {
                            "x": x_slice[mask].tolist(),
                            "y": y_slice[mask].tolist()
                        }
                else:
                    result["contours"][contour_name] = {"x": [], "y": []}
            except:
                result["contours"][contour_name] = {"x": [], "y": []}

        return result
    except Exception as e:
        return {"error": str(e), "filename": os.path.basename(filepath)}



# ── Global pipeline state ──
pipeline_logs = []
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"matlab_path": "matlab", "gmsh_path": "gmsh"}

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


# ── Routes ──

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/config", methods=["GET"])
def get_config():
    return safe_jsonify(load_config())

@app.route("/api/config", methods=["POST"])
def post_config():
    cfg = {
        "matlab_path": request.form.get("matlab_path", "matlab"),
        "gmsh_path":   request.form.get("gmsh_path",   "gmsh"),
    }
    save_config(cfg)
    return safe_jsonify({"message": f"Saved. MATLAB={cfg['matlab_path']}, Gmsh={cfg['gmsh_path']}"})

@app.route("/upload", methods=["POST"])
def upload_file():
    os.makedirs(SEG_DIR, exist_ok=True)
    if "file" not in request.files:
        return safe_jsonify({"success": False, "message": "No file part"})
    f = request.files["file"]
    if not f.filename:
        return safe_jsonify({"success": False, "message": "No file selected"})
        
    filename = f.filename.lower()
    
    if filename.endswith(".mat"):
        dest = os.path.join(SEG_DIR, os.path.basename(f.filename))
        f.save(dest)
        return safe_jsonify({"success": True, "message": f"Uploaded {f.filename} successfully!", "filename": os.path.basename(f.filename)})
    elif filename.endswith(".png") or filename.endswith(".jpg") or filename.endswith(".jpeg"):
        import tempfile
        import subprocess
        import shutil
        import re
        
        # Save image securely
        ext = filename.split('.')[-1]
        img_temp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
        f.save(img_temp.name)
        img_temp.close()
        
        # Determine next patient number
        mat_files = [mf for mf in os.listdir(SEG_DIR) if mf.startswith('Patient_') and mf.endswith('.mat')]
        max_num = 0
        for mf in mat_files:
            m = re.match(r'Patient_(\d+)\.mat', mf)
            if m:
                max_num = max(max_num, int(m.group(1)))
        next_num = max_num + 1
        new_patient_file = f"Patient_{next_num}.mat"
        dest_mat = os.path.join(SEG_DIR, new_patient_file)
        
        # Copy Patient_1.mat to the new patient
        src_mat = os.path.join(SEG_DIR, "Patient_1.mat")
        if os.path.exists(src_mat):
            shutil.copy(src_mat, dest_mat)
        elif len(mat_files) > 0:
            shutil.copy(os.path.join(SEG_DIR, mat_files[0]), dest_mat)

        # Run the predicition 
        deployment_dir = os.path.join(os.path.dirname(PROJECT_ROOT), "Cardiovascular-Detection-using-ECG-images", "Deployment")
        predict_script = os.path.join(deployment_dir, "predict.py")
        
        try:
            res = subprocess.run(["python3", predict_script, img_temp.name], 
                                 cwd=deployment_dir, capture_output=True, text=True)
            output = res.stdout
            err = res.stderr
            pred_text = "Unknown"
            for line in output.split("\n"):
                if line.startswith("PREDICTION_RESULT:"):
                    pred_text = line.split("PREDICTION_RESULT:")[1].strip()
                    
            # move images and data
            static_ecg_dir = os.path.join(PROJECT_ROOT, "web_interface", "static", "ecg", f"Patient_{next_num}")
            os.makedirs(static_ecg_dir, exist_ok=True)
            
            shutil.copy(img_temp.name, os.path.join(static_ecg_dir, "uploaded_image.png"))
            files_to_copy = ["Leads_1-12_figure.png", "Long_Lead_13_figure.png", 
                             "Preprossed_Leads_1-12_figure.png", "Preprossed_Leads_13_figure.png", 
                             "Contour_Leads_1-12_figure.png", "ecg_data.json"]
            for fname in files_to_copy:
                src_path = os.path.join(deployment_dir, fname)
                if os.path.exists(src_path):
                    shutil.copy(src_path, os.path.join(static_ecg_dir, fname))
            
            # save prediction text
            with open(os.path.join(static_ecg_dir, "prediction.txt"), "w") as f_pred:
                f_pred.write(pred_text)
            
            os.remove(img_temp.name)
            
            return safe_jsonify({
                "success": True, 
                "message": f"ECG Analyzed: {pred_text}. Created {new_patient_file}.",
                "filename": new_patient_file
            })
        except Exception as e:
            return safe_jsonify({"success": False, "message": f"Error running ECG model: {str(e)}"})
            
    else:
        return safe_jsonify({"success": False, "message": "Only .mat or image files (.png, .jpg) are supported"})

@app.route("/api/patients")
def list_patients():
    os.makedirs(SEG_DIR, exist_ok=True)
    mat_files = sorted([f for f in os.listdir(SEG_DIR)
                        if f.endswith(".mat") and not f.startswith(".")])
    return safe_jsonify({"patients": mat_files})

@app.route("/api/patient/<filename>")
def get_patient(filename):
    filepath = os.path.join(SEG_DIR, filename)
    if not os.path.exists(filepath):
        return safe_jsonify({"error": "File not found"}), 404
        
    result = read_mat_file(filepath)
    
    # Check for ECG images
    pat_id = filename.replace(".mat", "")
    ecg_dir = os.path.join(PROJECT_ROOT, "web_interface", "static", "ecg", pat_id)
    if os.path.exists(ecg_dir):
        images = []
        for img in ["uploaded_image.png", "Leads_1-12_figure.png", "Long_Lead_13_figure.png", "Preprossed_Leads_1-12_figure.png", "Preprossed_Leads_13_figure.png", "Contour_Leads_1-12_figure.png"]:
            if os.path.exists(os.path.join(ecg_dir, img)):
                images.append(f"/static/ecg/{pat_id}/{img}")
                
        pred_path = os.path.join(ecg_dir, "prediction.txt")
        prediction = open(pred_path).read() if os.path.exists(pred_path) else "Unknown"
        
        data_path = os.path.join(ecg_dir, "ecg_data.json")
        extra_data = {}
        if os.path.exists(data_path):
            try:
                with open(data_path) as df:
                    extra_data = json.load(df)
            except: pass

        # Override default MRI metrics with explicitly predicted ECG metrics
        if "predicted_metrics" in extra_data:
            metric_configs = {
                "HR":    "Heart Rate (BPM)",
                "EDV":   "End-Diastolic Volume (ml)",
                "ESV":   "End-Systolic Volume (ml)",
                "EF":    "Ejection Fraction (%)",
                "LVM":   "LV Mass (g)",
                "SV":    "Stroke Volume (ml)",
                "RVEDV": "RV End-Diastolic Vol (ml)",
                "RVEF":  "RV Ejection Fraction (%)"
            }
            for k, val in extra_data["predicted_metrics"].items():
                result["metrics"][k] = {
                    "label": metric_configs.get(k, k),
                    "value": round(val, 3) if val else None
                }

        result["ecg_analysis"] = {
            "prediction": prediction,
            "images": images,
            "data": extra_data
        }
    
    return safe_jsonify(result)

@app.route("/logs")
def get_logs():
    return safe_jsonify({"logs": pipeline_logs})

@app.route("/run_pipeline", methods=["POST"])
def run_pipeline():
    import threading, subprocess
    cfg = load_config()
    pipeline_logs.clear()
    pipeline_logs.append("Pipeline started.")

    def _run():
        for d in ["seg", "Surfaces", "FEM", "Convertion_Process/Data",
                  "Matlab_Process/Data", "Matlab_Process/Data/Aligned",
                  "Matlab_Process/Data/ScarImages", "Matlab_Process/Data/ScarImages/MetaImages",
                  "Matlab_Process/Data/Seg", "Matlab_Process/Data/Texts", "Scar_Process/Data"]:
            os.makedirs(os.path.join(PROJECT_ROOT, d), exist_ok=True)
        pipeline_logs.append("Directories ready.")
        for rpath in [os.path.join(PROJECT_ROOT, "run_matlab.sh"),
                      os.path.join(PROJECT_ROOT, "Matlab_Process", "run_matlab.sh")]:
            try:
                with open(rpath, "w") as fh:
                    fh.write("#!/bin/bash\n")
                    fh.write(f"{cfg['matlab_path']} -nodisplay < alignAll.m > logfile.output 2>&1\n")
                os.chmod(rpath, 0o755)
            except Exception:
                pass
        pipeline_logs.append("Scripts patched.")
        try:
            proc = subprocess.Popen(
                ["python3", "mat2fem.py"],
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in proc.stdout:
                pipeline_logs.append(line.rstrip())
            proc.wait()
            if proc.returncode == 0:
                pipeline_logs.append("Pipeline completed successfully.")
            else:
                pipeline_logs.append(f"Pipeline failed (exit code {proc.returncode}).")
                ml = os.path.join(PROJECT_ROOT, "Matlab_Process", "logfile.output")
                if os.path.exists(ml):
                    with open(ml) as fh:
                        pipeline_logs.append("--- MATLAB LOG ---")
                        pipeline_logs.extend(fh.read().splitlines()[-20:])
        except Exception as e:
            pipeline_logs.append(f"Error: {e}")

    threading.Thread(target=_run, daemon=True).start()
    return safe_jsonify({"status": "started"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
