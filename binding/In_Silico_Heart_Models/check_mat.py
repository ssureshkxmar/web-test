import scipy.io
import os

path = 'seg/Patient_1.mat'
if os.path.exists(path):
    data = scipy.io.loadmat(path)
    s = data['setstruct']
    print("Keys found in Patient_1.mat:")
    print(s.dtype.names)
else:
    print("Patient_1.mat not found")
