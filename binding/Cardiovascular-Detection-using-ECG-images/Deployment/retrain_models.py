import pandas as pd
import numpy as np
import os
from natsort import natsorted
import joblib
from sklearn.decomposition import PCA
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split

# 1. Load and concatenate data
data_dir = '/home/sureshkumar-s/Downloads/Cardiovascular-Detection-using-ECG-images/Combined1d_csv'
leads = []
target = None

for i in range(1, 13):
    file_path = os.path.join(data_dir, f'Combined_IDLead_{i}.csv')
    print(f"Loading {file_path}...")
    df = pd.read_csv(file_path)
    if i == 1:
        # Get target from the first file
        target = df['Target']
    
    # Drop index column and Target
    current_lead_features = df.drop(columns=[df.columns[0], 'Target'])
    leads.append(current_lead_features)

# Concatenate leads horizontally
X = pd.concat(leads, axis=1)
print(f"Data shape after concatenation: {X.shape}")

# 2. Encode target
# HB -> 0, MI -> 1, No -> 2, PM -> 3 (alphabetical)
y = target.astype('category').cat.codes
print("Target counts:")
print(target.value_counts())
print("Encoded counts:")
print(pd.Series(y).value_counts())

# 3. PCA
print("Training PCA...")
pca = PCA(n_components=400)
X_pca = pca.fit_transform(X)
print(f"PCA shape: {X_pca.shape}")

# 4. Train Classifier
print("Training VotingClassifier...")
# Using the best params found in the notebook if available, 
# otherwise reasonable defaults based on the notebook output
eclf = VotingClassifier(estimators=[ 
    ('SVM', SVC(C=1, gamma=0.1, probability=True)),
    ('knn', KNeighborsClassifier(n_neighbors=1)),
    ('rf', RandomForestClassifier(n_estimators=300)),
    ('bayes', GaussianNB()),
    ('logistic', LogisticRegression(max_iter=1000)),
    ], voting='soft')

eclf.fit(X_pca, y)
print("Training complete.")

# 5. Save models
pca_path = 'PCA_ECG (1).pkl'
clf_path = 'Heart_Disease_Prediction_using_ECG (4).pkl'

joblib.dump(pca, pca_path)
joblib.dump(eclf, clf_path)

print(f"Saved models to {pca_path} and {clf_path}")
