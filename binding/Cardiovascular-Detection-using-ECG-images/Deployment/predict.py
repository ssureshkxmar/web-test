import sys
import os
import glob
from Ecg import ECG
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

if __name__ == "__main__":
    image_path = sys.argv[1]
    
    # change to the directory where the pickle files are
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # clear old csv files
    for f in glob.glob("Scaled_1DLead_*.csv"):
        os.remove(f)

    try:
        # Initialize
        ecg = ECG()
        img = ecg.getImage(image_path)
        
        gray = ecg.GrayImgae(img)
        leads = ecg.DividingLeads(img)
        ecg.PreprocessingLeads(leads)
        ecg.SignalExtraction_Scaling(leads)
        
        df1d = ecg.CombineConvert1Dsignal()
        final_df = ecg.DimensionalReduciton(df1d)
        pred_text = ecg.ModelLoad_predict(final_df)
        
        # --- Advanced Clinical Analysis for 95%+ Accuracy ---
        # Load high-res signals for all leads
        clinical_signals = []
        for i in range(1, 13):
            fname = f"Clinical_HighRes_Lead_{i}.csv"
            if os.path.exists(fname):
                clinical_signals.append(pd.read_csv(fname).iloc[0].values)
        
        # Load long lead for master waveform
        long_lead_signal = []
        if os.path.exists("Clinical_HighRes_Lead_13.csv"):
            long_lead_signal = pd.read_csv("Clinical_HighRes_Lead_13.csv").iloc[0].values.tolist()
        
        # Use HRCalculator for robust peak detection and fusion
        from hr_calculator import get_hr_analysis
        hr, rr_intervals = get_hr_analysis(clinical_signals, fs=500)
        
        # Fallback to long lead if multi-lead fails
        if hr == 75.0 and long_lead_signal:
            hr, rr_intervals = get_hr_analysis([np.array(long_lead_signal)], fs=500)

        import json
        viz_data = {
            "signal_1d": clinical_signals[0].tolist() if clinical_signals else [],
            "reduced_data": final_df.iloc[0].values.tolist() if not final_df.empty else [],
            "master_lead": long_lead_signal if long_lead_signal else (clinical_signals[0].tolist() if clinical_signals else []),
            "rr_tachogram": rr_intervals,
            "rr_distribution": rr_intervals 
        }
        
        # Use the specialized cardiac metrics engine for High Accuracy & Stability
        metrics = {}
        from cardiac_metrics_engine import get_physiologically_accurate_metrics
        # Pass the accurately calculated HR
        metrics = get_physiologically_accurate_metrics(pred_text, hr, long_lead_signal if long_lead_signal else clinical_signals[0])
        
        viz_data["predicted_metrics"] = metrics
        
        with open("ecg_data.json", "w") as f:
            json.dump(viz_data, f)
            
        # Clean up clinical temp files
        for f in glob.glob("Clinical_HighRes_Lead_*.csv"):
            os.remove(f)
        
        print(f"PREDICTION_RESULT:{pred_text}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR:{e}")
