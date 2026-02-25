import joblib
import sys
import sklearn.metrics._scorer
import numpy as np
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

def _passthrough_scorer(*args, **kwargs): return 0.0
if not hasattr(sklearn.metrics._scorer, '_passthrough_scorer'):
    sklearn.metrics._scorer._passthrough_scorer = _passthrough_scorer
setattr(sys.modules['__main__'], '_passthrough_scorer', _passthrough_scorer)

try:
    # 1. Convert PCA
    print("Converting PCA...")
    pca = joblib.load('engine/models/PCA_ECG (1).pkl')
    initial_type_pca = [('float_input', FloatTensorType([None, 3060]))]
    onx_pca = convert_sklearn(pca, initial_types=initial_type_pca, target_opset=12)
    with open("engine/models/pca.onnx", "wb") as f:
        f.write(onx_pca.SerializeToString())
        
    # 2. Convert Classifier Estimators individually
    print("Loading VotingClassifier...")
    search = joblib.load('engine/models/Heart_Disease_Prediction_using_ECG.pkl')
    voting = search.best_estimator_
    
    for i, est in enumerate(voting.estimators_):
        print(f"Converting Estimator {i} ({type(est)})...")
        initial_type = [('float_input', FloatTensorType([None, 400]))]
        onx = convert_sklearn(est, initial_types=initial_type, target_opset=12)
        with open(f"engine/models/est_{i}.onnx", "wb") as f:
            f.write(onx.SerializeToString())
            
    print("SUCCESS: Generated ONNX models for all components.")

except Exception as e:
    import traceback
    traceback.print_exc()
