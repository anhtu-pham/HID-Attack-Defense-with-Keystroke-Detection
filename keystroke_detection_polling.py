import sys
import os
# import termios
from pynput import keyboard
import time
import csv
from ML_model import CustomMLModel
from blacklist_linux import detect_keyboards_and_callback, blacklist_hid_device

fieldnames = ["Key", "Timestamp"]
key_events = []
training_real_filepath = 'data/real.csv'
training_fake_filepath = 'data/fake.csv'
demo_filepath = 'data/demo.csv'
prev_timestamp = None
added_device_info = None
session_threshold = 3

def clear_stdin():
    """Flush any pending input so the terminal does not execute the last typed command."""
    # termios.tcflush(sys.stdin, termios.TCIOFLUSH)

def on_press(key):
    global prev_timestamp
    current_timestamp = time.time()
    if (prev_timestamp == None or current_timestamp - prev_timestamp > session_threshold):
        key_events.append({fieldnames[0]: None, fieldnames[1]: -1})
    key_event = {fieldnames[0]: str(key), fieldnames[1]: current_timestamp}
    print(f'{fieldnames[0]}: {str(key)}, {fieldnames[1]}: {current_timestamp}')
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
    if stop_key == keyboard.Key.esc:
        with open(demo_filepath, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0:
                writer.writeheader()
            for key_event in key_events:
                writer.writerow(key_event)
        
        if len(key_events) < 5:
            print("Not enough keystrokes for analysis. Continue monitoring...")
            return True
            
        model = CustomMLModel(model_name="bagging", n_neighbors=5, n_bagging=1)
        model.train(training_real_filepath, training_fake_filepath)
        flag = model.predict(demo_filepath)
        
        print("________________________________________")
        if flag:
            print("Suspicious behavior is detected. Examine if there is actual HID attack...")
            if added_device_info is not None:
                print(f"HID attack is detected. Blacklisting device: {added_device_info['name']} ({added_device_info['vendor_id']}:{added_device_info['product_id']})")
                # blacklist_hid_device(added_device_info)
            else:
                print("HID attack is not yet detected. Continue monitoring...")
        else:
            print("Suspicious behavior is not yet detected. Continue monitoring...")
        
        # Reset key events for next session
        key_events.clear()
        return True  # Don't stop listener

def monitor_keyboard_continuous():
    """
    Continuously monitor keystrokes while allowing device detection to happen in parallel
    """
    global key_events
    key_events = []  # Initialize key events list
    
    print("Starting continuous keystroke monitoring...")
    print("Press ESC to analyze current keystroke patterns")
    
    # Start a keyboard listener that doesn't block
    listener = keyboard.Listener(on_press=on_press, on_release=on_release_for_demo)
    listener.daemon = True  # Make the listener a daemon thread
    listener.start()
    
    return listener

if __name__ == "__main__":
    try:    
        print("Starting keyboard attack detection system...")
        
        # Start keystroke monitoring in a non-blocking way
        keyboard_listener = monitor_keyboard_continuous()
        
        # Start device monitoring in the main thread
        # The callback will set the added_device_info whenever a new keyboard is detected
        detect_keyboards_and_callback(lambda device_info: globals().update(added_device_info=device_info), stop_on_detection=False)
        
    except KeyboardInterrupt:
        print("\nKeyboard monitoring service stopped")
    except Exception as e:
        print(f"An error occurred: {e}")