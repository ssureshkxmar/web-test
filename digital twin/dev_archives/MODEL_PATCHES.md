# Model Compatibility Fixes Summary

## Issue Description
The project failed to run because the pre-trained machine learning models (`PCA_ECG (1).pkl` and `Heart_Disease_Prediction_using_ECG.pkl`) were trained using older versions of `scikit-learn` (v1.0.2 and v1.2.2), which are binary-incompatible with the newer `scikit-learn` (v1.6+) installed in the current Python 3.12 environment.

Symptoms included:
- `AttributeError: 'PCA' object has no attribute 'power_iteration_normalizer'`
- `ValueError: node array from the pickle has an incompatible dtype`
- `AttributeError: '_passthrough_scorer' not found`
- `ValueError: buffer source array is read-only`

## Applied Fixes

### 1. PCA Model Patching
- **Problem**: Missing `power_iteration_normalizer` attribute.
- **Fix**: Loaded the model, monkeypatched the missing attribute, and re-saved the model.

### 2. Diagnosis Model (VotingClassifier) Patching
- **Problem**: The internal binary structure of the Decision Trees (`sklearn.tree._tree.Tree`) changed between versions. The node array format (dtypes) and internal state structure were different.
- **Fix**: Created a robust patching script (`patch_diagnosis.py`) that:
    - Uses a `DummyTree` to intercept the raw binary state during unpickling.
    - Recursively walks through the complex `VotingClassifier` -> `GridSearchCV` -> `Estimator` hierarchy.
    - Converts the old node array binary format to the new format expected by the installed `scikit-learn` version.
    - Infers missing attributes like `n_features`, `max_depth`, and `monotonic_cst`.
    - Re-constructs valid `DecisionTree` objects and injects them back into the model.

### 3. Runtime Compatibility Patches
- **Problem**: `sklearn.metrics._scorer._passthrough_scorer` was removed in recent versions but referenced by the model's `GridSearchCV` state.
- **Fix**: Injected a mock `_passthrough_scorer` into `sklearn.metrics._scorer` and `sys.modules['__main__']` in `api/index.py` to ensure successful unpickling at runtime.

### 4. Read-Only Buffer Fix
- **Problem**: `joblib.load(..., mmap_mode='r')` created read-only memory maps, causing failures when the patched models needed to write/update their internal state during prediction.
- **Fix**: Changed to standard loading (removed `mmap_mode='r'`) in `engine/heartbeat.py`.

## Verification
- The server successfully started.
- The `/predict-ecg` endpoint processed a test request and returned a `200 OK` status with a valid prediction result.
