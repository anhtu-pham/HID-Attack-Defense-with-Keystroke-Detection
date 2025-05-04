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
temp_training_filepath = os.path.join(script_dir, 'data', 'new_data', 'temp_data.csv')
new_training_real_filepath = os.path.join(script_dir, 'data', 'new_data', 'new_real.csv')
new_training_fake_filepath = os.path.join(script_dir, 'data', 'new_data', 'new_fake.csv')
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

def finalize_training_data(label="real"):
    target_path = new_training_real_filepath# if label == "real" else new_training_fake_filepath

    if not os.path.exists(temp_training_filepath):
        logging.warning("⚠️ Temp training file does not exist. Skipping finalize.")
        return

    # with open(temp_training_filepath, mode='r', newline='') as src_file, \
    #      open(target_path, mode='a', newline='') as dest_file:

    #     reader = csv.DictReader(src_file)
    #     writer = csv.DictWriter(dest_file, fieldnames=fieldnames)

    #     if dest_file.tell() == 0:
    #         writer.writeheader()

    #     for row in reader:
    #         writer.writerow(row)

    os.remove(temp_training_filepath)
    logging.info(f"✅ Released training data to: {new_training_real_filepath}")
    
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
    with open(temp_training_filepath, mode='a', newline='') as file:
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

run_monitor = False
monitor_thread = None
listener = None

def listen_for_commands(release_type):
    global run_monitor
    for line in sys.stdin:
        logging.info("std in")
        cmd = line.strip().lower()
        if cmd == "release":
            logging.info(f"Releasing {release_type} training data")
            finalize_training_data(release_type)
        elif cmd == "stop monitoring":
            stop_monitoring()
        elif cmd == "start training":
            start_monitoring("training")
        elif cmd == "start demo":
            start_monitoring("demo")
        else:
            logging.warning(f"Unknown command: {cmd}")

# Move keyboard monitoring to a background thread instead

def start_monitoring(mode="demo"):
    global run_monitor, monitor_thread
    if monitor_thread is None or not monitor_thread.is_alive():
        run_monitor = True
        monitor_thread = threading.Thread(target=monitor_keyboard_continuous, args=(mode,), daemon=True)
        monitor_thread.start()
        logging.info("Keyboard monitoring thread started")

def stop_monitoring():
    global run_monitor, listener
    run_monitor = False
    logging.info("Stopping keyboard monitor...")

    # If listener is running, stop it cleanly
    if listener is not None:
        try:
            listener.stop()
        except Exception as e:
            logging.error(f"Failed to stop listener: {e}")

def monitor_keyboard_continuous(mode="demo"):
    global key_events, listener
    key_events = []

    logging.info(f"Starting keyboard monitoring in {mode.upper()} mode...")

    while run_monitor:
        try:
            if mode == "training":
                listener = keyboard.Listener(on_press=on_press, on_release=on_release_for_training)
            else:
                listener = keyboard.Listener(on_press=on_press, on_release=on_release_for_demo)

            listener.start()
            listener.join()  
        except Exception as e:
            logging.error(f"Listener error: {e}")
        finally:
            listener = None

if __name__ == "__main__":
    mode = "demo"
    label = "real"
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip().lower()
        if arg in ["training", "demo"]:
            mode = arg
    if len(sys.argv) > 2:
        label_arg = sys.argv[2].strip().lower()
        if label_arg in ["real", "fake"]:
            label = label_arg
    
    logging.info(f"Starting keyboard attack detection system in {mode.upper()} mode...")
        
    # Start the thread
    threading.Thread(target=listen_for_commands, args=(label,), daemon=True).start()
        

    start_monitoring(mode)

    detect_keyboards_and_callback(
        callback_function=lambda device_info: globals().update(added_device_info=device_info),
        stop_on_detection=False
    )
    
    
