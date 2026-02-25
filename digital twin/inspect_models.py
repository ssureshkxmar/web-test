import joblib
import sys
import sklearn.metrics._scorer

def _passthrough_scorer(*args, **kwargs):
    return 0.0

if not hasattr(sklearn.metrics._scorer, '_passthrough_scorer'):
    sklearn.metrics._scorer._passthrough_scorer = _passthrough_scorer

setattr(sys.modules['__main__'], '_passthrough_scorer', _passthrough_scorer)

# Now load
try:
    classifier = joblib.load('engine/models/Heart_Disease_Prediction_using_ECG.pkl')
    print(f"Classifier Type: {type(classifier)}")
    if hasattr(classifier, 'n_features_in_'):
        print(f"Features in: {classifier.n_features_in_}")
    
    pca = joblib.load('engine/models/PCA_ECG (1).pkl')
    print(f"PCA Type: {type(pca)}")
    if hasattr(pca, 'n_components_'):
        print(f"PCA Components: {pca.n_components_}")
    if hasattr(pca, 'components_'):
        print(f"PCA Matrix Shape: {pca.components_.shape}")
        
except Exception as e:
    print(f"Error: {e}")
