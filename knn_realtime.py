import pandas as pd
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import BaggingClassifier
from pynput import keyboard
import time
import threading
from collections import deque
from knn import CustomKNN

class RealTimeHIDDetector:
    def __init__(self, model_path=None, n_neighbors=5, window_size=20, overlap=5):
        # Configuration
        self.window_size = window_size  # Number of events to process at once
        self.overlap = overlap  # Number of events to overlap between windows
        self.n_neighbors = n_neighbors
        
        # Data structures
        self.keystroke_buffer = deque(maxlen=window_size*2)
        self.timestamps = deque(maxlen=window_size*2)
        self.detection_history = deque(maxlen=10)  # Store recent detection results
        
        # Model
        self.knn_model = None
        self.running = False
        
        # Either load an existing model or train a new one
        if model_path:
            self.load_model(model_path)
        else:
            self.knn_model = KNeighborsClassifier(n_neighbors=self.n_neighbors)
            # You'll need to train this with sample data
    
    def train_model(self, real_filepath, fake_filepath):
        # Reuse most of the training code from CustomKNN
        custom_knn = CustomKNN(n_neighbors=self.n_neighbors)
        self.bagging_model = custom_knn.train(real_filepath, fake_filepath)
        self.knn_model = custom_knn.knn_model
        return self.knn_model
    
    def save_model(self, filepath):
        import joblib
        joblib.dump(self.knn_model, filepath)
    
    def load_model(self, filepath):
        import joblib
        self.knn_model = joblib.load(filepath)
    
    def on_key_press(self, key):
        # Record keystroke and timestamp
        try:
            # Store key data - could be expanded to include more info
            key_data = str(key)
            current_time = time.time()
            
            self.keystroke_buffer.append(key_data)
            self.timestamps.append(current_time)
        except Exception as e:
            print(f"Error recording keystroke: {e}")
    
    def process_window(self):
        """Process a window of keystroke data and detect potential attacks"""
        if len(self.timestamps) < self.window_size:
            return False  # Not enough data
        
        # Create a dataframe with the current window of data
        data = []
        timestamps = list(self.timestamps)
        
        for i in range(len(timestamps)-1):
            # Calculate time between keystrokes (duration)
            duration = timestamps[i+1] - timestamps[i]
            data.append({
                'Key': list(self.keystroke_buffer)[i],
                'Timestamp': timestamps[i],
                'Duration': duration
            })
        
        df = pd.DataFrame(data)
        
        # Apply feature extraction similar to the original code
        # Calculate z-scores for durations
        df['Z_Score'] = (df['Duration'] - df['Duration'].median()) / df['Duration'].std() if df['Duration'].std() > 0 else 0
        
        # Extract the standard deviation as the feature
        # This simplifies the feature extraction from the original code
        feature = np.std(df['Duration'].values)
        feature = np.array([feature]).reshape(-1, 1)
        
        # Make prediction
        if self.knn_model is not None:
            result = self.knn_model.predict(feature)
            self.detection_history.append(result[0])
            
            # Alert if several consecutive windows show attack patterns
            attack_ratio = sum(self.detection_history) / len(self.detection_history)
            if attack_ratio > 0.6 and len(self.detection_history) >= 3:
                print("⚠️ ALERT: Abnormal typing pattern detected! Possible HID attack.")
                return True
        
        return False
    
    def detection_loop(self):
        """Main loop that processes windows of data periodically"""
        while self.running:
            self.process_window()
            # Sleep briefly to avoid excessive CPU usage
            time.sleep(0.1)
    
    def start(self):
        """Start keyboard listener and detection thread"""
        self.running = True
        
        # Start keyboard listener
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()
        
        # Start detection thread
        self.detection_thread = threading.Thread(target=self.detection_loop)
        self.detection_thread.daemon = True
        self.detection_thread.start()
        
        print("HID attack detection started. Monitoring keystrokes...")
    
    def stop(self):
        """Stop the detector"""
        self.running = False
        if hasattr(self, 'keyboard_listener'):
            self.keyboard_listener.stop()
        print("HID attack detection stopped.")


# Example usage
if __name__ == "__main__":
    # First train the model with existing data
    detector = RealTimeHIDDetector(n_neighbors=5)
    
    # Train with existing data files
    print("Training model with sample data...")
    detector.train_model("data/real.csv", "data/fake.csv")
    
    # Start real-time detection
    detector.start()
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        detector.stop()
        print("Detector stopped by user.")