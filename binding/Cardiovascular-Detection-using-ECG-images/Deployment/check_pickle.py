import joblib
import sklearn
print(f"Current sklearn version: {sklearn.__version__}")
try:
    pca = joblib.load('PCA_ECG (1).pkl')
    print("PCA loaded successfully")
    print(dir(pca))
except Exception as e:
    print(f"Error loading PCA: {e}")
try:
    clf = joblib.load('Heart_Disease_Prediction_using_ECG (4).pkl')
    print("Classifier loaded successfully")
    print(dir(clf))
except Exception as e:
    print(f"Error loading Classifier: {e}")
