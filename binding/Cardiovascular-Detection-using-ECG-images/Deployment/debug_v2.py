try:
    import joblib
    import sklearn
    from skimage.io import imread
    print(f"sklearn: {sklearn.__version__}")
    pca = joblib.load('PCA_ECG (1).pkl')
    print("Loaded PCA")
except Exception as e:
    print(f"Error: {e}")
