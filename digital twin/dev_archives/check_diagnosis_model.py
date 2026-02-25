import joblib
import numpy as np
import pandas as pd
import sklearn
import os

import sklearn.metrics._scorer

if not hasattr(sklearn.metrics._scorer, '_passthrough_scorer'):
    def _passthrough_scorer(*args, **kwargs):
        return 0.0
    sklearn.metrics._scorer._passthrough_scorer = _passthrough_scorer

pca_path = 'engine/models/PCA_ECG (1).pkl'
diagnosis_path = 'engine/models/Heart_Disease_Prediction_using_ECG.pkl'

print("Loading PCA...")
pca = joblib.load(pca_path)
n_components = pca.n_components_
print(f"PCA components: {n_components}")

print("Loading Diagnosis Model...")
try:
    model = joblib.load(diagnosis_path)
    print(f"Model type: {type(model)}")
    
    # Create dummy input based on PCA output
    dummy_input = pd.DataFrame(np.random.rand(5, n_components))
    
    print("Attempting prediction...")
    try:
        model.predict(dummy_input)
        print("Prediction successful!")
    except Exception as e:
        print(f"Prediction failed: {e}")
        # Try to identify missing attributes if any?
        # Common sklearn failures often relate to unexpected or missing attributes
except Exception as e:
    print(f"Failed to load diagnosis model: {e}")
