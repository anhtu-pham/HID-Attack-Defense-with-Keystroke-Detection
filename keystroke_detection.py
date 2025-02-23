from pynput import keyboard
import time
import csv

fieldnames = ["Key", "Timestamp"]
key_events = []
log_file = 'real.csv'

def on_press(key):
    keyValue = None
    try:
        keyValue = key.char
    except AttributeError:
        keyValue = str(key)
    key_event = {fieldnames[0]: str(key), fieldnames[1]: time.time()}
    print(f'\n{key_event}')
    key_events.append(key_event)

def on_release(key):
    if key == keyboard.Key.esc:
        with open(log_file, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0:
                writer.writeheader()
            for key_event in key_events:
                writer.writerow(key_event)
        return False

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()