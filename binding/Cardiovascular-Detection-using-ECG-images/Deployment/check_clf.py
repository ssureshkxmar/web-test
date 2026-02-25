import joblib
import pandas as pd
import numpy as np
import sklearn
print(f"sklearn: {sklearn.__version__}")
try:
    clf = joblib.load('Heart_Disease_Prediction_using_ECG (4).pkl')
    print("Loaded Classifier")
    # Try a dummy predict if possible
    # We need to know the input shape though. PCA output is usually smaller.
    # Let's just see if it has the same missing attribute issue.
    print(dir(clf))
except Exception as e:
    print(f"Error: {e}")
