import sys
# import tty
import termios
from pynput import keyboard
import time
import csv
from knn import CustomKNN

fieldnames = ["Key", "Timestamp"]
key_events = []
training_filepath = 'data/real.csv'
demo_filepath = 'data/demo.csv'

def clear_stdin():
    """Flush any pending input so the terminal does not execute the last typed command."""
    termios.tcflush(sys.stdin, termios.TCIOFLUSH)

def on_press(key):
    key_event = {fieldnames[0]: str(key), fieldnames[1]: time.time()}
    print(f'\n{key_event}')
    key_events.append(key_event)

def on_release_for_training(key):
    if key == keyboard.Key.esc:
        with open(training_filepath, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0:
                writer.writeheader()
            for key_event in key_events:
                writer.writerow(key_event)
        clear_stdin()
        return False
    
def on_release_for_demo(key):
    if key == keyboard.Key.esc:
        with open(demo_filepath, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0:
                writer.writeheader()
            for key_event in key_events:
                writer.writerow(key_event)
        clear_stdin()
        custom_knn = CustomKNN()
        custom_knn.predict(demo_filepath)
        return False

with keyboard.Listener(on_press=on_press, on_release=on_release_for_demo) as listener:
    listener.join()