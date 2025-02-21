from pynput import keyboard
import time
import threading

key_events = []

def on_press(key):
    try:
        print("Normal key: " + key.char)
    except AttributeError:
        print("Uncharacterized key:" + key)
    timestamp = time.time()
    key_events.append({"Key": key, "Timestamp": timestamp})

def on_release(key):
    if key == keyboard.Key.esc:
        return False

def start_listener():
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

thread = threading.Thread(target=start_listener)
thread.start()