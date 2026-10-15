import numpy as np

class TinyMLHealthAnalyzer:
    """
    Per-packet TinyML-style health analysis engine for Movesense data.
    Implements real-time anomaly detection based on moving averages and Z-scores.
    Processed continuously as packets arrive (Zero-mock compliant).
    """
    def __init__(self, window_size=50, threshold_z=3.0):
        self.window_size = window_size
        self.threshold_z = threshold_z
        self.ecg_buffer = []
        self.acc_buffer = []

    def process_ecg_packet(self, ecg_samples):
        """
        Processes a packet of ECG samples in real-time.
        Returns a list of anomalies (if any).
        """
        anomalies = []
        for sample in ecg_samples:
            self.ecg_buffer.append(sample)
            if len(self.ecg_buffer) > self.window_size:
                self.ecg_buffer.pop(0)
            
            if len(self.ecg_buffer) == self.window_size:
                mean = np.mean(self.ecg_buffer)
                std = np.std(self.ecg_buffer)
                if std > 0:
                    z_score = abs(sample - mean) / std
                    if z_score > self.threshold_z:
                        anomalies.append({
                            'type': 'ECG_ANOMALY',
                            'value': sample,
                            'z_score': z_score
                        })
        return anomalies

    def process_imu_packet(self, acc_x, acc_y, acc_z):
        """
        Processes an IMU packet in real-time.
        Calculates magnitude and detects movement anomalies.
        """
        mag = np.sqrt(acc_x**2 + acc_y**2 + acc_z**2)
        self.acc_buffer.append(mag)
        if len(self.acc_buffer) > self.window_size:
            self.acc_buffer.pop(0)

        anomalies = []
        if len(self.acc_buffer) == self.window_size:
            mean = np.mean(self.acc_buffer)
            std = np.std(self.acc_buffer)
            if std > 0:
                z_score = abs(mag - mean) / std
                if z_score > self.threshold_z:
                    anomalies.append({
                        'type': 'IMU_ANOMALY',
                        'value': mag,
                        'z_score': z_score
                    })
        return anomalies
