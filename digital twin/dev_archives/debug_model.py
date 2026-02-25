import joblib
import numpy as np
import pandas as pd
import sklearn.decomposition

model_path = 'engine/models/PCA_ECG (1).pkl'

try:
    print("Loading model...")
    pca = joblib.load(model_path)
    print("Model loaded.")
    
    n_features = pca.n_features_in_
    print(f"Expecting {n_features} features.")
    
    # Create dummy data
    dummy_data = pd.DataFrame(np.random.rand(5, n_features))
    
    try:
        print("Attempting transform...")
        pca.transform(dummy_data)
        print("Transform successful!")
    except AttributeError as e:
        print(f"Transform failed as expected: {e}")
        if 'power_iteration_normalizer' in str(e):
            print("Patching model...")
            pca.power_iteration_normalizer = 'auto'
            print("Retrying transform...")
            pca.transform(dummy_data)
            print("Transform successful after patch!")
            
            print("Saving patched model...")
            joblib.dump(pca, model_path)
            print("Patched model saved.")
            
except Exception as e:
    print(f"An error occurred: {e}")
