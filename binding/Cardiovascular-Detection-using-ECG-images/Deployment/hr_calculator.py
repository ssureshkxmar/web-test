import numpy as np
from scipy.signal import find_peaks, butter, lfilter

class HRCalculator:
    def __init__(self, sampling_rate=500):
        self.fs = sampling_rate

    def butter_bandpass(self, lowcut, highcut, order=5):
        nyq = 0.5 * self.fs
        low = lowcut / nyq
        high = highcut / nyq
        b, a = butter(order, [low, high], btype='bandpass')
        return b, a

    def bandpass_filter(self, data, lowcut=5, highcut=15, order=5):
        b, a = self.butter_bandpass(lowcut, highcut, order=order)
        y = lfilter(b, a, data)
        return y

    def detect_r_peaks(self, signal):
        """
        Detect R-peaks using a Pan-Tompkins-like approach.
        """
        # 1. Bandpass filter (5-15 Hz) to highlight QRS
        filtered = self.bandpass_filter(signal)
        
        # 2. Derivative (to emphasize slopes)
        diff = np.diff(filtered)
        
        # 3. Squaring (to emphasize R-peaks, eliminate negative components)
        squared = diff ** 2
        
        # 4. Moving window integration (to find QRS complex energy)
        window_size = int(0.12 * self.fs)
        integrated = np.convolve(squared, np.ones(window_size)/window_size, mode='same')
        
        # 5. Peak picking with constraints
        distance = int(0.4 * self.fs) # Max heart rate of ~150 bpm (400ms interval)
        peaks, _ = find_peaks(integrated, distance=distance, height=np.mean(integrated)*1.5)
        
        return peaks

    def calculate_hr(self, signal_list):
        """
        Calculates Heart Rate from multiple leads and performs fusion.
        """
        hrs = []
        all_intervals = []
        
        for signal in signal_list:
            peaks = self.detect_r_peaks(signal)
            if len(peaks) > 1:
                intervals = np.diff(peaks) / self.fs # in seconds
                # Outlier removal (physiological range: 30bpm to 220bpm)
                # 0.27s (220bpm) to 2.0s (30bpm)
                valid_intervals = intervals[(intervals > 0.27) & (intervals < 2.0)]
                if len(valid_intervals) > 0:
                    lead_hr = 60 / np.mean(valid_intervals)
                    hrs.append(lead_hr)
                    all_intervals.extend(valid_intervals.tolist())
        
        if not hrs:
            return 75.0, [] # Default
        
        # Fusion: Weighted average or Robust Median
        final_hr = np.median(hrs)
        
        # Convert intervals back to ms for tachogram
        ms_intervals = [float(i * 1000) for i in all_intervals]
        
        return float(final_hr), ms_intervals

def get_hr_analysis(signals, fs=500):
    calc = HRCalculator(sampling_rate=fs)
    return calc.calculate_hr(signals)
