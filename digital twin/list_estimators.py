import joblib
import sys
import sklearn.metrics._scorer

def _passthrough_scorer(*args, **kwargs): return 0.0
if not hasattr(sklearn.metrics._scorer, '_passthrough_scorer'):
    sklearn.metrics._scorer._passthrough_scorer = _passthrough_scorer
setattr(sys.modules['__main__'], '_passthrough_scorer', _passthrough_scorer)

try:
    search = joblib.load('engine/models/Heart_Disease_Prediction_using_ECG.pkl')
    voting = search.best_estimator_
    print(f"Voting: {type(voting)}")
    for i, est in enumerate(voting.estimators_):
        print(f"Est {i}: {type(est)}")
except Exception as e:
    print(f"Error: {e}")
