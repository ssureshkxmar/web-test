import os
import shutil
import pandas as pd
import numpy as np
import sys

# Ensure we can import engine
sys.path.append(os.getcwd())
from engine.heartbeat import CardioPulseEngine

def test_localization():
    # Setup
    test_dir = "test_localization_tmp"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    pass_score = True
    
    try:
        # Create dummy traces
        # 12 leads. 
        # Scenario: Anterior Infarction (V3, V4 elevation)
        # V3 is index 10, V4 is index 3 (in our mapping: 0, 1, 2, 3... wait)
        
        # Mapping from heartbeat.py
        # leads_map = {
        #    'I': 0, 'aVR': 1, 'V1': 2, 'V4': 3,
        #    'II': 4, 'aVL': 5, 'V2': 6, 'V5': 7,
        #    'III': 8, 'aVF': 9, 'V3': 10, 'V6': 11
        # }
        
        for i in range(12):
            # Normal baseline
            data = np.random.normal(0.2, 0.05, 100)
            
            # Elevate V3 (idx 10) and V4 (idx 3)
            if i == 10 or i == 3:
                data = np.random.normal(0.8, 0.05, 100) # Simulating ST elevation (high values)
                
            df = pd.DataFrame(data).T # transposed to match shape expected if any
            # Code reads df.values, percentile 75.
            # csv structure in trace_contours was: df = pd.DataFrame(norm[:, 0]).T -> single row?
            # Let's check trace_contours:
            # df = pd.DataFrame(norm[:, 0]).T
            # df.to_csv(..., index=False)
            # So it's a CSV with 1 row and N columns (samples).
            
            df = pd.DataFrame(data).T
            df.to_csv(os.path.join(test_dir, f'raw_trace_{i+1}.csv'), index=False)
            
        # Test
        engine = CardioPulseEngine()
        region, model = engine.localize_infarction(work_dir=test_dir)
        
        print(f"Detected Region: {region}")
        print(f"Detected Model: {model}")
        
        if region == "Anterior" and model == "leftventricle.glb":
            print("TEST PASSED: Correctly identified Anterior Infarction")
        else:
            print(f"TEST FAILED: Expected Anterior/leftventricle.glb, got {region}/{model}")
            pass_score = False
            
    except Exception as e:
        print(f"TEST ERROR: {e}")
        pass_score = False
    finally:
        # Cleanup
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            
    if not pass_score:
        sys.exit(1)

if __name__ == "__main__":
    test_localization()
