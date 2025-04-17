import sys
import os
# import termios
from pynput import keyboard
import time
import csv
from knn import CustomKNN
from blacklist_linux import detect_keyboards_and_callback, blacklist_hid_device

fieldnames = ["Key", "Timestamp"]
key_events = []
training_real_filepath = 'data/real.csv'
training_fake_filepath = 'data/fake.csv'
demo_filepath = 'data/demo.csv'
prev_timestamp = None
max_iter = 4
added_device_info = None
session_threshold = 3

fieldnames = ["Key", "Timestamp"]
key_events = []
training_real_filepath = 'data/real.csv'
training_fake_filepath = 'data/fake.csv'
demo_filepath = 'data/demo.csv'
prev_timestamp = None
max_iter = 4
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
    print(f'\n{key_event}')
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
        model = CustomKNN(n_neighbors=3, n_bagging=2)
        flag = False
        num_iter = 0
        while not flag and num_iter < max_iter:
            model.train(training_real_filepath, training_fake_filepath)
            flag = model.predict("bagging", demo_filepath)
            num_iter += 1
        if flag:
            print("Abnormal behavior detected. Possible HID attack.")
            if added_device_info is not None:
                print(f"Blacklisting device: {added_device_info['name']} ({added_device_info['vendor_id']}:{added_device_info['product_id']})")
                blacklist_hid_device(added_device_info)
            else:
                print("Device info not found, cannot blacklist device")
        else:
            print("Abnormal behavior not detected yet.")
        clear_stdin()
        return False

def monitor_keyboard(device_info):
    """
    Helper method to monitor keystrokes from a specific keyboard
    
    Args:
        device_info (dict): Dictionary containing information about the keyboard device
    """
    global added_device_info, key_events
    added_device_info = device_info
    key_events = []  # Reset key events for the new device
    
    print(f"Starting keystroke monitoring for {device_info['name']}...")
    print(f"Press ESC to stop monitoring and analyze keystrokes")
    
    # Start a keyboard listener to monitor keystrokes
    with keyboard.Listener(on_press=on_press, on_release=on_release_for_demo) as listener:
        listener.join()

#IMPORTANT: run sudo
if __name__ == "__main__":
    try:    
        print("Starting keyboard attack detection system...")
        
        # Use monitor_keyboards from blacklist_linux.py with our callback function
        detect_keyboards_and_callback(monitor_keyboard)
    except KeyboardInterrupt:
        print("\nKeyboard monitoring service stopped")
    except Exception as e:
        print(f"An error occurred: {e}")