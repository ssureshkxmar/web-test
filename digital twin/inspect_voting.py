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
    voting = search.best_estimator_
    print(f"Estimators: {[type(e) for n, e in voting.estimators_]}")
    
    for name, est in voting.estimators_:
        print(f"--- {name} ---")
        if hasattr(est, 'coef_'):
            print(f"Coef: {est.coef_.shape}")
        elif hasattr(est, 'feature_importances_'):
            print(f"Tree based model")
        else:
            print(f"Other: {type(est)}")

except Exception as e:
    print(f"Error: {e}")
