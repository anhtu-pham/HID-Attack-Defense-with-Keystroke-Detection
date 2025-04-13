import sys
# import termios
from pynput import keyboard
import time
import csv
from knn import CustomKNN
from hid_handling import detect_hid_devices, blacklist_hid_devices

fieldnames = ["Key", "Timestamp"]
key_events = []
training_real_filepath = 'data/real.csv'
training_fake_filepath = 'data/fake.csv'
demo_filepath = 'data/demo.csv'
max_iter = 4
check_new_device = True
hid_ids = detect_hid_devices()
added_hid_ids = None

def clear_stdin():
    """Flush any pending input so the terminal does not execute the last typed command."""
    # termios.tcflush(sys.stdin, termios.TCIOFLUSH)

def on_press(key):
    global check_new_device, added_hid_ids
    key_event = {fieldnames[0]: str(key), fieldnames[1]: time.time()}
    print(f'\n{key_event}')
    key_events.append(key_event)
    if check_new_device:
        new_hid_ids = detect_hid_devices()
        added_hid_ids = list(set(new_hid_ids) - set(hid_ids))
        print("ADDED", added_hid_ids)
        check_new_device = False

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
    global added_hid_ids
    if stop_key == keyboard.Key.esc:
        with open(demo_filepath, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0:
                writer.writeheader()
            for key_event in key_events:
                writer.writerow(key_event)
        model = CustomKNN(n_neighbors=3, n_bagging=9)
        flag = False
        num_iter = 0
        while not flag and num_iter < max_iter:
            model.train(training_real_filepath, training_fake_filepath)
            flag = model.predict("bagging", demo_filepath)
            num_iter += 1
        if flag:
            print("Abnormal behavior detected. Possible HID attack.")
            if added_hid_ids is not None:
                print("Can blacklist now")
                # blacklist_hid_devices(added_hid_ids)
        else:
            print("Abnormal behavior not detected yet.")
        clear_stdin()
        return False

if __name__ == "__main__":
    with keyboard.Listener(on_press=on_press, on_release=on_release_for_demo) as listener:
        listener.join()