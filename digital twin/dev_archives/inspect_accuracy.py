import joblib
import pandas as pd
import numpy as np
import sklearn
import sklearn.metrics._scorer

# Patching for compatibility
if not hasattr(sklearn.metrics._scorer, '_passthrough_scorer'):
    def _passthrough_scorer(*args, **kwargs):
        return 0.0
    sklearn.metrics._scorer._passthrough_scorer = _passthrough_scorer

diagnosis_path = 'engine/models/Heart_Disease_Prediction_using_ECG.pkl'

try:
    print(f"Loading {diagnosis_path}...")
    model = joblib.load(diagnosis_path)
    print(f"Model Type: {type(model)}")
    print("-" * 30)

    # Check for Cross-Validation scores (GridSearchCV / RandomizedSearchCV)
    if hasattr(model, 'best_score_'):
        print(f"Best CV Score (Accuracy during training): {model.best_score_ * 100:.2f}%")
    
    if hasattr(model, 'cv_results_'):
        print(f"CV Results available keys: {model.cv_results_.keys()}")
        if 'mean_test_score' in model.cv_results_:
            scores = model.cv_results_['mean_test_score']
            print(f"Mean Test Scores: {scores}")
            print(f"Max Mean Test Score: {np.max(scores) * 100:.2f}%")

    # Check for Out-of-Bag score (RandomForest / Bagging)
    if hasattr(model, 'oob_score_'):
        print(f"OOB Score: {model.oob_score_ * 100:.2f}%")

    # Check if it's a direct classifier and if we can find anything else
    if hasattr(model, 'score'):
        print("Model has a .score() method (requires test data to evaluate)")

    # List all attributes to see if there's anything custom
    print("-" * 30)
    print("All Attributes:")
    for attr in dir(model):
        if not attr.startswith('__') and not callable(getattr(model, attr)):
            # print(f"{attr}") # Too verbose, maybe just check specific ones
            pass

except Exception as e:
    print(f"Error: {e}")
