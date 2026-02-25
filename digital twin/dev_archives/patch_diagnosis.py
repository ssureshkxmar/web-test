import joblib
import numpy as np
import sklearn.tree._tree
import sklearn.ensemble
import sys
import sys
import os
import sklearn.metrics._scorer

# Patch missing attribute
if not hasattr(sklearn.metrics._scorer, '_passthrough_scorer'):
    def _passthrough_scorer(*args, **kwargs):
        return 0.0
    sklearn.metrics._scorer._passthrough_scorer = _passthrough_scorer

# 1. Define DummyTree to intercept the loading of sklearn.tree._tree.Tree
class DummyTree:
    def __init__(self, *args, **kwargs):
        self.state = None
        self.init_args = args
        
    def __setstate__(self, state):
        # Capture the state passed by pickle
        self.state = state

# 2. Monkeypatch
RealTree = sklearn.tree._tree.Tree
sklearn.tree._tree.Tree = DummyTree

# 3. Load the model
model_path = 'engine/models/Heart_Disease_Prediction_using_ECG.pkl'
print(f"Loading {model_path} with DummyTree patch...")

try:
    model = joblib.load(model_path)
    print(f"Model loaded with DummyTrees! Type: {type(model)}")
    print(f"Attributes: {list(model.__dict__.keys())}")
except Exception as e:
    print(f"Failed to load even with patch: {e}")
    sys.exit(1)

# 4. Restore RealTree to create correct objects
sklearn.tree._tree.Tree = RealTree

# 5. Helper to convert old node array to new dtype
def convert_node_array(old_nodes):
    # Get the expected dtype from a fresh tree state
    clf = sklearn.tree.DecisionTreeClassifier(max_depth=1, random_state=0)
    clf.fit([[0], [1]], [0, 1])
    
    # helper to find array in fresh state
    # We can use recursive_fix logic but just to find
    state = clf.tree_.__getstate__()
    
    # Unwrap state like we do in recursive_fix
    if isinstance(state, dict):
        # usually {'state': ...} or keys like 'nodes', 'values'
        if 'nodes' in state: # newer sklearn might expose 'nodes' directly in dict?
             pass
        if 'state' in state:
             state = state['state']
    
    # Assuming state is now tuple or contains the array
    expected_dtype = None
    
    def find_dtype(s):
        if isinstance(s, np.ndarray) and s.dtype.names and 'left_child' in s.dtype.names:
            return s.dtype
        elif isinstance(s, (list, tuple)):
            for item in s:
                res = find_dtype(item)
                if res is not None: return res
        elif isinstance(s, dict):
             for v in s.values():
                 res = find_dtype(v)
                 if res is not None: return res
        return None

    expected_dtype = find_dtype(state)
    
    if expected_dtype is None:
        print("Error: Could not determine expected dtype from fresh tree.")
        sys.exit(1)
    
    print(f"Old dtype names: {old_nodes.dtype.names}")
    print(f"New dtype names: {expected_dtype.names}")
    
    # Create new array
    new_nodes = np.zeros(old_nodes.shape, dtype=expected_dtype)
    
    # Copy matching fields
    for name in old_nodes.dtype.names:
        if name in expected_dtype.names:
            new_nodes[name] = old_nodes[name]
        else:
            print(f"Warning: Field {name} in old not in new.")
            
    # Handle new fields
    # usually initialized to 0 by zeros()
    
    return new_nodes

# 6. Walk the model to find and replace DummyTrees
# The model is a VotingClassifier -> estimators_ (list of models)
# Each model (RandomForest, DecisionTree, etc.)
# RandomForest -> estimators_ (list of DecisionTrees) -> tree_
# DecisionTree -> tree_

def recursive_fix(state):
    # Returns (fixed_state, was_modified)
    if isinstance(state, dict):
        modified = False
        new_dict = {}
        for k, v in state.items():
            fixed_v, mod = recursive_fix(v)
            new_dict[k] = fixed_v
            if mod: modified = True
        return new_dict, modified
    elif isinstance(state, (list, tuple)):
        modified = False
        new_list = []
        for item in state:
            fixed_item, mod = recursive_fix(item)
            new_list.append(fixed_item)
            if mod: modified = True
        return (tuple(new_list) if isinstance(state, tuple) else new_list), modified
    elif isinstance(state, np.ndarray):
        if state.dtype.names and 'left_child' in state.dtype.names:
            print("Found node array! Converting...")
            return convert_node_array(state), True
    return state, False

def process_estimator(est):
    # Fix missing attributes for newer sklearn
    if hasattr(est, 'tree_') or isinstance(est, (sklearn.tree.DecisionTreeClassifier, sklearn.ensemble.RandomForestClassifier)):
        if not hasattr(est, 'monotonic_cst'):
            # print(f"Adding monotonic_cst to {type(est).__name__}")
            est.monotonic_cst = None
            
    # Check if it has a tree_ attribute
    if hasattr(est, 'tree_') and isinstance(est.tree_, DummyTree):
        # print(f"Fixing tree in {type(est).__name__}...")
        dummy = est.tree_
        old_state = dummy.state
        
        fixed_state, modified = recursive_fix(old_state)
        
        if modified:
            try:
                # We need to instantiate RealTree.
                # If state is a dict {'state': ...}, RealTree.__setstate__ might expect that.
                # However, RealTree also needs init args (n_features, etc).
                
                # We captured init_args in DummyTree!
                valid_args = getattr(dummy, 'init_args', None)
                
                # Check if init_args are valid?
                # If dummy.init_args is empty, we must rely on __setstate__ to set everything.
                # But we still need to construct the object.
                
                
                # Unwrapping logic
                while isinstance(fixed_state, dict) and 'state' in fixed_state:
                     inner = fixed_state['state']
                     if isinstance(inner, dict) and 'max_depth' in inner:
                         fixed_state = inner
                         break
                     elif isinstance(inner, dict) and 'state' in inner:
                         fixed_state = inner
                         continue
                     else:
                         fixed_state = inner
                         break
                
                # Infer args from state
                n_features = 400 # Default fallback
                n_classes = np.array([1], dtype=np.intp)
                n_outputs = 1
                
                if isinstance(fixed_state, dict):
                    if 'values' in fixed_state:
                        vals = fixed_state['values']
                        # shape: (n_nodes, n_outputs, max_n_classes)
                        if len(vals.shape) == 3:
                            n_outputs = vals.shape[1]
                            max_classes = vals.shape[2]
                            n_classes = np.array([max_classes] * n_outputs, dtype=np.intp)
                    
                    if 'nodes' in fixed_state:
                        nodes = fixed_state['nodes']
                        # Infer n_features from max feature index
                        # Filter out logic (-2 usually means leaf or similar)
                        # features are usually >= 0, special values like -2 exist
                        feats = nodes['feature']
                        max_feat = np.max(feats)
                        if max_feat > 0:
                            n_features = max_feat + 1
                
                # Construct RealTree
                if valid_args:
                    try:
                        rt = RealTree(*valid_args)
                    except:
                        rt = RealTree(n_features, n_classes, n_outputs)
                else:
                    rt = RealTree(n_features, n_classes, n_outputs)
                
                rt.__setstate__(fixed_state)
                est.tree_ = rt
                print("Tree fixed and replaced.")
            except Exception as e:
                print(f"Error setting state on RealTree in {type(est).__name__}: {type(e).__name__}: {e}")
                if isinstance(fixed_state, dict):
                    print(f"State keys: {fixed_state.keys()}")
                else:
                    print(f"State type: {type(fixed_state)}")
        else:
            if isinstance(est, sklearn.tree.DecisionTreeClassifier):
                 # Only warn for DecisionTrees, not random other things
                 print(f"Warning: Could not find node array in {type(est).__name__} state")
                 # print(f"State keys: {old_state.keys() if isinstance(old_state, dict) else 'tuple'}")

# Recursive walker
def walk_and_fix(obj):
    print(f"Visiting {type(obj).__name__}")
    # If list/dict (like estimators_)
    if isinstance(obj, list):
        for item in obj:
            walk_and_fix(item)
    
    if hasattr(obj, 'estimators_'):
        walk_and_fix(obj.estimators_)
        
    if hasattr(obj, 'best_estimator_'):
        walk_and_fix(obj.best_estimator_)
    
    # Process the object itself if it is an estimator
    process_estimator(obj)

# Main execution
print("Starting patches...")
walk_and_fix(model)

print("Patching complete. Saving...")
joblib.dump(model, model_path)
print("Saved patched model.")
