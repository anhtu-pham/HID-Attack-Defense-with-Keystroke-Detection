import sys
# import termios
from pynput import keyboard
import time
import csv
import detect_hid_window
from knn import CustomKNN
from detect_hid_window import detect_devices
from blacklist_window import disable_hid_device 

fieldnames = ["Key", "Timestamp"]
key_events = []
training_real_filepath = 'data/real.csv'
training_fake_filepath = 'data/fake.csv'
demo_filepath = 'data/demo.csv'
has_new_device = True
device_list = detect_devices()

def clear_stdin():
    """Flush any pending input so the terminal does not execute the last typed command."""
    # termios.tcflush(sys.stdin, termios.TCIOFLUSH)

def on_press(key):
    global has_new_device
    key_event = {fieldnames[0]: str(key), fieldnames[1]: time.time()}
    print(f'\n{key_event}')
    key_events.append(key_event)
    if has_new_device:
        new_device_list = detect_devices()
        added_devices = list(set(new_device_list) - set(device_list))
        if added_devices:
            for device in added_devices:
                print(f"New HID Device Detected: {device}")
        has_new_device = False

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
    if stop_key == keyboard.Key.esc:
        with open(demo_filepath, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0:
                writer.writeheader()
            for key_event in key_events:
                writer.writerow(key_event)
        model = CustomKNN(n_neighbors=3, n_bagging=9)
        model.train(training_real_filepath, training_fake_filepath)
        if model.predict("bagging", demo_filepath):
            suspicious_device = detect_new_device()
            if suspicious_device is not None:
                disable_hid_device(suspicious_device)
        clear_stdin()
        return False

with keyboard.Listener(on_press=on_press, on_release=on_release_for_demo) as listener:
    listener.join()