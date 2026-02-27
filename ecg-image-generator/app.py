import os
import subprocess
import shutil
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Default paths
DEFAULT_INPUT = os.path.join(BASE_DIR, 'SampleData', 'PTB_XL_data')
DEFAULT_OUTPUT = os.path.join(BASE_DIR, 'static', 'output')

# Ensure output directory exists
os.makedirs(DEFAULT_OUTPUT, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html', default_input=DEFAULT_INPUT)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    input_dir = data.get('inputDir', DEFAULT_INPUT)
    
    # We always output to our static folder so we can serve them easily
    output_dir = DEFAULT_OUTPUT

    # Clear previous outputs
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    cmd = ["python3", "gen_ecg_images_from_data_batch.py", "-i", input_dir, "-o", output_dir]

    # Flags
    if data.get('printHeader'): cmd.append('--print_header')
    if data.get('addQrCode'): cmd.append('--add_qr_code')
    if data.get('randomResolution'): cmd.append('--random_resolution')
    if data.get('maskUnplotted'): cmd.append('--mask_unplotted_samples')
    
    # Text distortions
    if data.get('hwText'): 
        cmd.extend(['--hw_text', '-n', '2', '--x_offset', '30', '--y_offset', '30'])
    
    # Wrinkles
    if data.get('wrinkles'): 
        cmd.extend(['--wrinkles', '-ca', '45'])
        
    # Augment
    if data.get('augment'): 
        cmd.extend(['--augment', '-rot', '5', '-noise', '40'])

    # Standard configs for demo speed (deterministic output logic allows for cached generation speeds if needed, but we don't cache in script)
    cmd.extend(['-se', '42'])
    cmd.extend(['--max_num_images', '1']) # Just do one image for speed in preview

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=BASE_DIR)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            return jsonify({"success": False, "error": stderr}), 500

        # Find generated images
        generated_images = sorted([f for f in os.listdir(output_dir) if f.endswith('.png')])
        image_urls = [f'/static/output/{img}' for img in generated_images]

        return jsonify({"success": True, "images": image_urls, "logs": stdout})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
