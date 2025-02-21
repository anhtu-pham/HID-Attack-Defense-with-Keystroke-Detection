from pynput import keyboard
import time

key_events = []

def on_press(key):
    keyValue = None
    try:
        keyValue = key.char
    except AttributeError:
        keyValue = str(key)
    timestamp = time.time()
    print(f"\nKey: {keyValue} Timestamp: {timestamp}")
    key_events.append({"Key": keyValue, "Timestamp": timestamp})

def on_release(key):
    if key == keyboard.Key.esc:
        return False

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()