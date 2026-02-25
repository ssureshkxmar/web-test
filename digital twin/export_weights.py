import joblib
import sys
import sklearn.metrics._scorer
import numpy as np

def _passthrough_scorer(*args, **kwargs):
    return 0.0

if not hasattr(sklearn.metrics._scorer, '_passthrough_scorer'):
    sklearn.metrics._scorer._passthrough_scorer = _passthrough_scorer

setattr(sys.modules['__main__'], '_passthrough_scorer', _passthrough_scorer)

try:
    search = joblib.load('engine/models/Heart_Disease_Prediction_using_ECG.pkl')
    model = search.best_estimator_
    print(f"Internal Model: {type(model)}")
    
    # Save weights if it's a simple model
    weights = {}
    if hasattr(model, 'coef_'):
        weights['coef'] = model.coef_
        weights['intercept'] = model.intercept_
        weights['classes'] = model.classes_
        print("Success: Extracted linear weights")
    elif hasattr(model, 'feature_importances_'):
         print("Model is Tree-based. Harder to port manually, but possible.")

    # Save PCA as weights
    pca = joblib.load('engine/models/PCA_ECG (1).pkl')
    weights['pca_components'] = pca.components_
    weights['pca_mean'] = pca.mean_
    
    # Save the consolidated weights to a single numpy file
    np.savez('engine/models/weights.npz', **weights)
    print("Exported engine/models/weights.npz")
        
except Exception as e:
    print(f"Error: {e}")
