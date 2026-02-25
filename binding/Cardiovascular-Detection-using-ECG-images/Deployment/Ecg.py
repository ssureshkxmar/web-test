from skimage.io import imread
from skimage import color, exposure, measure
from skimage.transform import resize
import matplotlib.pyplot as plt
from skimage.filters import threshold_otsu, gaussian, median
from skimage.morphology import disk
from scipy.signal import savgol_filter, find_peaks
import joblib
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
import numpy as np
import os
from natsort import natsorted
from sklearn import linear_model, tree, ensemble
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression

class ECG:
	def  getImage(self,image):
		"""
		this functions gets user image
		return: user image
		"""
		image=imread(image)
		return image

	def GrayImgae(self,image):
		"""
		This funciton converts the user image to Gray Scale
		return: Gray scale Image
		"""
		image_gray = color.rgb2gray(image)
		image_gray=resize(image_gray,(1572,2213))
		return image_gray

	def DividingLeads(self,image):
		"""
		This Funciton Divides the Ecg image into 13 Leads including long lead. Bipolar limb leads(Leads1,2,3). Augmented unipolar limb leads(aVR,aVF,aVL). Unipolar (+) chest leads(V1,V2,V3,V4,V5,V6)
  		return : List containing all 13 leads divided
		"""
		Lead_1 = image[300:600, 150:643] # Lead 1
		Lead_2 = image[300:600, 646:1135] # Lead aVR
		Lead_3 = image[300:600, 1140:1625] # Lead V1
		Lead_4 = image[300:600, 1630:2125] # Lead V4
		Lead_5 = image[600:900, 150:643] #Lead 2
		Lead_6 = image[600:900, 646:1135] # Lead aVL
		Lead_7 = image[600:900, 1140:1625] # Lead V2
		Lead_8 = image[600:900, 1630:2125] #Lead V5
		Lead_9 = image[900:1200, 150:643] # Lead 3
		Lead_10 = image[900:1200, 646:1135] # Lead aVF
		Lead_11 = image[900:1200, 1140:1625] # Lead V3
		Lead_12 = image[900:1200, 1630:2125] # Lead V6
		Lead_13 = image[1250:1480, 150:2125] # Long Lead

		#All Leads in a list
		Leads=[Lead_1,Lead_2,Lead_3,Lead_4,Lead_5,Lead_6,Lead_7,Lead_8,Lead_9,Lead_10,Lead_11,Lead_12,Lead_13]
		fig , ax = plt.subplots(4,3)
		fig.set_size_inches(10, 10)
		x_counter=0
		y_counter=0

		#Create 12 Lead plot using Matplotlib subplot

		for x,y in enumerate(Leads[:len(Leads)-1]):
			if (x+1)%3==0:
				ax[x_counter][y_counter].imshow(y)
				ax[x_counter][y_counter].axis('off')
				ax[x_counter][y_counter].set_title("Leads {}".format(x+1))
				x_counter+=1
				y_counter=0
			else:
				ax[x_counter][y_counter].imshow(y)
				ax[x_counter][y_counter].axis('off')
				ax[x_counter][y_counter].set_title("Leads {}".format(x+1))
				y_counter+=1
	    
		#save the image
		fig.savefig('Leads_1-12_figure.png')
		fig1 , ax1 = plt.subplots()
		fig1.set_size_inches(10, 10)
		ax1.imshow(Lead_13)
		ax1.set_title("Leads 13")
		ax1.axis('off')
		fig1.savefig('Long_Lead_13_figure.png')

		return Leads

	def ClinicalPreprocessing(self, image_gray):
		"""
		Advanced clinical preprocessing: CLAHE, Noise reduction, Contrast enhancement.
		"""
		# Contrast Enhancement using CLAHE
		img_adapteq = exposure.equalize_adapthist(image_gray, clip_limit=0.03)
		
		# Noise Reduction using Median Filter
		denoised = median(img_adapteq, disk(1))
		
		# Smoothness using Gaussian
		blurred = gaussian(denoised, sigma=0.5)
		
		return blurred

	def PreprocessingLeads(self,Leads):
		"""
		Enhanced Preprocessing using Clinical Standards.
		"""
		fig2 , ax2 = plt.subplots(4,3)
		fig2.set_size_inches(10, 10)
		x_counter=0
		y_counter=0

		for x,y in enumerate(Leads[:len(Leads)-1]):
			grayscale = color.rgb2gray(y)
			
			# Use advanced preprocessing
			processed = self.ClinicalPreprocessing(grayscale)
			
			# Adaptive Thresholding for better peak preservation
			global_thresh = threshold_otsu(processed)
			binary_global = processed < global_thresh
			
			binary_global = resize(binary_global, (300, 450))
			if (x+1)%3==0:
				ax2[x_counter][y_counter].imshow(binary_global,cmap="gray")
				ax2[x_counter][y_counter].axis('off')
				ax2[x_counter][y_counter].set_title("Lead {}".format(x+1))
				x_counter+=1
				y_counter=0
			else:
				ax2[x_counter][y_counter].imshow(binary_global,cmap="gray")
				ax2[x_counter][y_counter].axis('off')
				ax2[x_counter][y_counter].set_title("Lead {}".format(x+1))
				y_counter+=1
		fig2.savefig('Preprossed_Leads_1-12_figure.png')

		# Lead 13 (Long Lead)
		grayscale13 = color.rgb2gray(Leads[-1])
		processed13 = self.ClinicalPreprocessing(grayscale13)
		thresh13 = threshold_otsu(processed13)
		binary13 = processed13 < thresh13
		
		fig3 , ax3 = plt.subplots()
		fig3.set_size_inches(12, 4)
		ax3.imshow(binary13, cmap='gray')
		ax3.set_title("Preprocessed Lead 13")
		ax3.axis('off')
		fig3.savefig('Preprossed_Leads_13_figure.png')

	def ExtractHighResSignal(self, binary_image, target_points=2000):
		"""
		Extracts high-resolution 1D signal from binary lead image.
		Uses column-wise centroid detection for precision.
		"""
		h, w = binary_image.shape
		signal = np.zeros(w)
		for col in range(w):
			pixels = np.where(binary_image[:, col] == 1)[0]
			if len(pixels) > 0:
				# Use median of vertical pixels to stay on the main trace
				signal[col] = np.median(pixels)
			else:
				# Interpolate if column is empty
				signal[col] = signal[col-1] if col > 0 else h/2
		
		# Smooth the signal using Savitzky-Golay
		if len(signal) > 31:
			signal = savgol_filter(signal, 31, 3)
			
		# Resize to common high-resolution scale (e.g. 2000 points for leads 1-12)
		final_signal = resize(signal, (target_points, 1)).flatten()
		
		# Invert so peaks go up (assuming black background/white signal)
		final_signal = h - final_signal
		
		# Scale to 0-1
		scaler = MinMaxScaler()
		final_signal = scaler.fit_transform(final_signal.reshape(-1, 1)).flatten()
		
		return final_signal


	def SignalExtraction_Scaling(self,Leads):
		"""
		Dual-mode extraction: Legacy (255pts) for ML and High-Res (2000pts) for Clinical Analysis.
		"""
		fig4 , ax4 = plt.subplots(4,3)
		fig4.set_size_inches(10, 10)
		x_counter=0
		y_counter=0
		
		for x,y in enumerate(Leads[:len(Leads)-1]):
			grayscale = color.rgb2gray(y)
			processed = self.ClinicalPreprocessing(grayscale)
			thresh = threshold_otsu(processed)
			binary = processed < thresh
			
			# 1. Legacy Scale (255 points) for PCA/Model compatibility
			legacy_signal = self.ExtractHighResSignal(binary, target_points=255)
			
			# 2. High-Res Scale (2000 points) for Clinical HR Analytics
			high_res_signal = self.ExtractHighResSignal(binary, target_points=2000)

			if (x+1)%3==0:
				ax4[x_counter][y_counter].plot(high_res_signal, linewidth=1, color='black')
				ax4[x_counter][y_counter].axis('off')
				ax4[x_counter][y_counter].set_title("Lead {}".format(x+1))
				x_counter+=1
				y_counter=0
			else:
				ax4[x_counter][y_counter].plot(high_res_signal, linewidth=1, color='black')
				ax4[x_counter][y_counter].axis('off')
				ax4[x_counter][y_counter].set_title("Lead {}".format(x+1))
				y_counter+=1
	    
			# Save Legacy to Scaled_1DLead_{}.csv for CombineConvert1Dsignal
			lead_no = x + 1
			pd.DataFrame(legacy_signal).T.to_csv('Scaled_1DLead_{}.csv'.format(lead_no), index=False)
			
			# Save Clinical High-Res separately
			pd.DataFrame(high_res_signal).T.to_csv('Clinical_HighRes_Lead_{}.csv'.format(lead_no), index=False)
	      
		fig4.tight_layout()
		fig4.savefig('Contour_Leads_1-12_figure.png')
		
		# Process Long Lead 13 (6000 points)
		grayscale13 = color.rgb2gray(Leads[-1])
		processed13 = self.ClinicalPreprocessing(grayscale13)
		thresh13 = threshold_otsu(processed13)
		binary13 = processed13 < thresh13
		
		long_signal = self.ExtractHighResSignal(binary13, target_points=6000)
		pd.DataFrame(long_signal).T.to_csv('Clinical_HighRes_Lead_13.csv', index=False)


	def CombineConvert1Dsignal(self):
		"""
		This function combines all 1D signals of 12 Leads into one FIle csv for model input.
		returns the final dataframe
		"""
		#first read the Lead1 1D signal
		test_final=pd.read_csv('Scaled_1DLead_1.csv')
		location= os.getcwd()
		print(location)
		#loop over all the remaining leads (Scaled_1DLead_*.csv)
		for files in natsorted(os.listdir(location)):
			if files.startswith("Scaled_1DLead_") and files.endswith(".csv"):
				if files!='Scaled_1DLead_1.csv' and files!='Scaled_1DLead_13.csv': # Model only uses 12 leads
					df=pd.read_csv('{}'.format(files))
					test_final=pd.concat([test_final,df],axis=1,ignore_index=True)

		return test_final

		return test_final
		
	def DimensionalReduciton(self,test_final):
		"""
		This function reduces the dimensinality of the 1D signal using PCA
		returns the final dataframe
		"""
		#first load the trained pca
		pca_loaded_model = joblib.load('PCA_ECG (1).pkl')
		if not hasattr(pca_loaded_model, 'power_iteration_normalizer'):
			pca_loaded_model.power_iteration_normalizer = 'auto'
		result = pca_loaded_model.transform(test_final)
		final_df = pd.DataFrame(result)
		return final_df

	def ModelLoad_predict(self,final_df):
		"""
		This Function Loads the pretrained model and perfrom ECG classification
		return the classification Type.
		"""
		loaded_model = joblib.load('Heart_Disease_Prediction_using_ECG (4).pkl')
		result = loaded_model.predict(final_df)
		if result[0] == 1:
			return "You ECG corresponds to Myocardial Infarction"
		elif result[0] == 0:
			return "You ECG corresponds to Abnormal Heartbeat"
		elif result[0] == 2:
			return "Your ECG is Normal"
		else:
			return "You ECG corresponds to History of Myocardial Infarction"
