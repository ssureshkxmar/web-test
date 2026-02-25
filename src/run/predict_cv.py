import sys
import os
import shutil
import argparse

# Add the cardiovascular ML deployment folder to our path so we can import Ecg
# Project root is 3 levels up from src/run/predict_cv.py
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# The module lives under binding/ inside the project root
deployment_dir = os.path.join(base_dir, 'binding', 'Cardiovascular-Detection-using-ECG-images', 'Deployment')
sys.path.append(deployment_dir)

try:
    from Ecg import ECG
except ImportError as e:
    print(f"Failed to import ECG from deployment directory: {e}")
    sys.exit(1)

def run_prediction(image_path, output_folder):
    """
    Safely executes the provided Cardiovascular ML models in a clean 
    temporary directory to prevent root folder clutter from its CSV generation.
    """
    abs_image_path = os.path.abspath(image_path)
    abs_output_folder = os.path.abspath(output_folder)
    
    # We will create a strictly isolated temp dir for CV ML execution
    temp_dir = os.path.join(abs_output_folder, 'cv_temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # Store original cwd
    original_cwd = os.getcwd()
    
    try:
        # Ecg.py loads exactly these two files from its cwd. We must copy them identically.
        shutil.copy(os.path.join(deployment_dir, 'PCA_ECG (1).pkl'), temp_dir)
        shutil.copy(os.path.join(deployment_dir, 'Heart_Disease_Prediction_using_ECG (4).pkl'), temp_dir)
        
        # Change securely into the scratch space
        os.chdir(temp_dir)
        
        print("Starting Cardiovascular ML Pipeline...")
        # Since Ecg.py heavily relies on matplotlib and skimage which are not thread-safe and hang often 
        # when imported globally in a Flask background thread, we instantiate and run it isolated here
        ecg = ECG()
        
        # 1. Image Read
        image_data = ecg.getImage(abs_image_path)
        
        # Ensure image is resized to match the hardcoded CV coordinate expectations
        from skimage.transform import resize
        image_data = resize(image_data[:, :, :3], (1572, 2213))
        
        # 2. Divide Leads (the model relies on hardcoded split coordinates)
        leads = ecg.DividingLeads(image_data)
        
        # 3. Preprocess Leads for plotting output 
        ecg.PreprocessingLeads(leads)
        
        # 3. Extract Signals mathematically to create 'Scaled_1DLead_X.csv' files in cwd
        import matplotlib
        matplotlib.use('Agg') # Force backend again right before the loop
        ecg.SignalExtraction_Scaling(leads)
        
        # 4. Collapse CSV parts into a single DataFrame
        df_1d = ecg.CombineConvert1Dsignal()
        with open(os.path.join(abs_output_folder, '1dsignal.html'), 'w') as f:
            f.write(df_1d.head(10).to_html(classes="table table-sm table-striped table-bordered", index=False))
        
        # 5. Execute its PCA Dimensionality Drop
        df_final = ecg.DimensionalReduciton(df_1d)
        with open(os.path.join(abs_output_folder, 'pca.html'), 'w') as f:
            f.write(df_final.head(10).to_html(classes="table table-sm table-striped table-bordered", index=False))
        
        # 6. Execute Voting Classifier ML prediction
        prediction_text = ecg.ModelLoad_predict(df_final)
        
        # 7. Rescue intermediate visualization assets before temp dir is purged
        figures_to_rescue = [
            'Leads_1-12_figure.png',
            'Long_Lead_13_figure.png',
            'Preprossed_Leads_1-12_figure.png',
            'Preprossed_Leads_13_figure.png',
            'Contour_Leads_1-12_figure.png'
        ]
        
        for fig in figures_to_rescue:
            if os.path.exists(fig):
                shutil.copy(fig, abs_output_folder)
        
        # Clean the string if it contains "You ECG corresponds to " 
        # to make it look punchier for the dashboard
        if "You ECG corresponds to " in prediction_text:
            prediction_text = prediction_text.replace("You ECG corresponds to ", "")
        if "Your ECG is " in prediction_text:
            prediction_text = prediction_text.replace("Your ECG is ", "")
            
        print(f"Cardiovascular Prediction complete: {prediction_text}")
        
        # Pass payload back to main server via txt hook
        prediction_file = os.path.join(abs_output_folder, 'cv_prediction.txt')
        with open(prediction_file, 'w') as f:
            f.write(prediction_text)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"An error occurred during CV ML prediction: {e}")
        error_file = os.path.join(abs_output_folder, 'cv_prediction.txt')
        with open(error_file, 'w') as f:
            f.write('Prediction Failed')
            
    finally:
        # Always restore environment securely & purge the scratch CSV files
        os.chdir(original_cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Secure cardiovascular disease prediction wrapper.")
    parser.add_argument('-i', '--image', required=True, help='Path to the uploaded ECG image')
    parser.add_argument('-o', '--output', required=True, help='Path to the final output directory')
    args = parser.parse_args()
    
    run_prediction(args.image, args.output)
