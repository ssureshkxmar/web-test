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
    # 1. Convert PCA (Input size 3060)
    print("Converting PCA...")
    pca = joblib.load('engine/models/PCA_ECG (1).pkl')
    initial_type_pca = [('float_input', FloatTensorType([None, 3060]))]
    onx_pca = convert_sklearn(pca, initial_types=initial_type_pca, target_opset=12)
    with open("engine/models/pca.onnx", "wb") as f:
        f.write(onx_pca.SerializeToString())
        
    # 2. Convert Classifier (Input size 400)
    print("Converting Classifier...")
    search = joblib.load('engine/models/Heart_Disease_Prediction_using_ECG.pkl')
    classifier = search.best_estimator_
    initial_type_clf = [('float_input', FloatTensorType([None, 400]))]
    onx_clf = convert_sklearn(classifier, initial_types=initial_type_clf, target_opset=12)
    with open("engine/models/classifier.onnx", "wb") as f:
        f.write(onx_clf.SerializeToString())
        
    print("SUCCESS: Generated engine/models/pca.onnx and classifier.onnx")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")
