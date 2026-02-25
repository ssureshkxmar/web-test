import joblib
import sys
import sklearn.metrics._scorer
import m2cgen as m2c
import numpy as np

def _passthrough_scorer(*args, **kwargs):
    return 0.0

if not hasattr(sklearn.metrics._scorer, '_passthrough_scorer'):
    sklearn.metrics._scorer._passthrough_scorer = _passthrough_scorer

setattr(sys.modules['__main__'], '_passthrough_scorer', _passthrough_scorer)

try:
    # 1. Convert Classifier
    search = joblib.load('engine/models/Heart_Disease_Prediction_using_ECG.pkl')
    # Use the best estimator directly
    code = m2c.export_to_python(search.best_estimator_)
    with open('engine/models/prediction_logic.py', 'w') as f:
        f.write(code)
    print("Exported engine/models/prediction_logic.py")
    
    # 2. Extract PCA components for Numpy
    pca = joblib.load('engine/models/PCA_ECG (1).pkl')
    np.savez('engine/models/pca_weights.npz', 
             components=pca.components_, 
             mean=pca.mean_)
    print("Exported engine/models/pca_weights.npz")

except Exception as e:
    print(f"Error: {e}")
