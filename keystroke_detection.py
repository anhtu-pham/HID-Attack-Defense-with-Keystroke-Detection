import sys
# import termios
from pynput import keyboard
import time
import json
import csv
from ML_model import CustomMLModel
import logging, sys
print("Key pressed", flush=True)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.flush = sys.stdout.flush
logging.basicConfig(level=logging.INFO, handlers=[handler])


fieldnames = ["Key", "Timestamp"]
key_events = []
training_real_filepath = 'data/real1.csv'
training_fake_filepath = 'data/fake.csv'
demo_filepath = 'data/demo.csv'
prev_timestamp = None
max_iter = 4
added_hid_ids = None
session_threshold = 3

def clear_stdin():
    """Flush any pending input so the terminal does not execute the last typed command."""
    # termios.tcflush(sys.stdin, termios.TCIOFLUSH)

def on_press(key):
    global check_new_device, added_hid_ids, prev_timestamp
    current_timestamp = time.time()
    if (prev_timestamp == None or current_timestamp - prev_timestamp > session_threshold):
        key_events.append({fieldnames[0]: None, fieldnames[1]: -1})
    key_event = {fieldnames[0]: str(key), fieldnames[1]: current_timestamp}
    logging.info(json.dumps({'Key': str(key), 'Timestamp': int(time.time() * 1000)}))
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
    global added_hid_ids
    if stop_key == keyboard.Key.esc:
        with open(demo_filepath, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0:
                writer.writeheader()
            for key_event in key_events:
                writer.writerow(key_event)
        model = CustomMLModel(model_name="bagging", n_neighbors=3, n_bagging=2)
        flag = False
        num_iter = 0
        while not flag and num_iter < max_iter:
            model.train(training_real_filepath, training_fake_filepath)
            flag = model.predict(demo_filepath)
            num_iter += 1
        if flag:
            logging.info("Abnormal behavior detected. Possible HID attack.")
            if added_hid_ids is not None:
                logging.info("Can blacklist now")
                # blacklist_hid_devices(added_hid_ids)
        else:
            logging.info("Abnormal behavior not detected yet.")
        clear_stdin()
        return False

if __name__ == "__main__":
    logging.info("PROGRAM STARTING")
    with keyboard.Listener(on_press=on_press, on_release=on_release_for_training) as listener:
        listener.join()