import sys
import os
# import termios
from pynput import keyboard
import time
import csv
import time
import threading
from ML_model import CustomMLModel
import logging, sys
import json
from blacklist_linux import detect_keyboards_and_callback, blacklist_hid_device


handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.flush = sys.stdout.flush
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout  # just use stream directly
)

script_dir = os.path.dirname(os.path.abspath(__file__))

fieldnames = ["Key", "Timestamp"]
key_events = []
training_real_filepath = os.path.join(script_dir, 'data', 'real.csv')
training_fake_filepath =  os.path.join(script_dir, 'data', 'fake.csv')
demo_filepath = os.path.join(script_dir, 'data', 'demo.csv')
prev_timestamp = None
added_device_info = None
session_threshold = 3


check_flag = False


def set_condition_every_x_ms(interval_ms):
    global check_flag
    while True:
        time.sleep(interval_ms / 1000.0)  # convert ms to seconds
        check_flag = True


threading.Thread(target=set_condition_every_x_ms, args=(5000,), daemon=True).start()

def clear_stdin():
    """Flush any pending input so the terminal does not execute the last typed command."""
    # termios.tcflush(sys.stdin, termios.TCIOFLUSH)

def on_press(key):
    global prev_timestamp
    current_timestamp = time.time()
    if (prev_timestamp == None or current_timestamp - prev_timestamp > session_threshold):
        key_events.append({fieldnames[0]: None, fieldnames[1]: -1})
    key_event = {fieldnames[0]: str(key), fieldnames[1]: current_timestamp}
    logging.info(json.dumps({fieldnames[0]: str(key), fieldnames[1]: int(time.time() * 1000)}))
    key_events.append(key_event)
    prev_timestamp = current_timestamp

def on_release_for_training(stop_key):
    if stop_key == keyboard.Key.esc:
        with open(training_real_filepath, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0:
                writer.writeheader()
            for key_event in key_events:
                writer.writerow(key_event)
        clear_stdin()
        return False
    
def on_release_for_demo(stop_key):
    global added_device_info
    global check_flag
    if len(key_events) >= 500 or check_flag:
        if(check_flag):
            check_flag = False #Reset
        with open(demo_filepath, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0:
                writer.writeheader()
            for key_event in key_events:
                writer.writerow(key_event)
        
        if len(key_events) < 5:
            logging.info("Not enough keystrokes for analysis. Continue monitoring...")
            return True
            
        model = CustomMLModel(model_name="bagging", n_neighbors=1, n_bagging=5)
        model.train(training_real_filepath, training_fake_filepath)
        flag = model.predict(demo_filepath)
        
        if flag:
            logging.info("Suspicious behavior is detected. Examine if there is actual HID attack...")
            if added_device_info is not None:
                logging.info(f"HID attack is detected. Blacklisting device: {added_device_info['name']} ({added_device_info['vendor_id']}:{added_device_info['product_id']})")
                blacklist_hid_device(added_device_info)
            else:
                logging.info("HID attack is not yet detected. Continue monitoring...")
        else:
            logging.info("Suspicious behavior is not yet detected. Continue monitoring...")
        
        # Reset key events for next session
        key_events.clear()
        return True  # Don't stop listener

def monitor_keyboard_continuous():
    """
    Continuously monitor keystrokes while allowing device detection to happen in parallel
    """
    global key_events
    key_events = []  # Initialize key events list
    
    logging.info("Starting continuous keystroke monitoring...")
    #logging.info("Press ESC to analyze current keystroke patterns")
    
    # Start a keyboard listener that doesn't block]
    
    with keyboard.Listener(on_press=on_press, on_release=on_release_for_demo) as listener:
        listener.join()
        listener.daemon = True  # Make the listener a daemon thread
        listener.start()
    
    return listener

# Move keyboard monitoring to a background thread instead

def start_keyboard_monitoring_thread():
    threading.Thread(target=monitor_keyboard_continuous, daemon=True).start()

if __name__ == "__main__":
    logging.info("Starting keyboard attack detection system...")

    # Start keyboard monitoring in background
    start_keyboard_monitoring_thread()

    # Then begin HID device detection interrupt-style
    detect_keyboards_and_callback(
        callback_function=lambda device_info: globals().update(added_device_info=device_info),
        stop_on_detection=False
    )
    
    
