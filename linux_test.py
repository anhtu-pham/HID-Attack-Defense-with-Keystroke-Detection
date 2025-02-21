import evdev
import csv

# Keystroke information
fieldnames = ['Timestamp', 'Key', 'KeyState']
for dev in evdev.list_devices():
    print(evdev.InputDevice(dev))

device = evdev.InputDevice('/dev/input/event4')
key_events = []

with open('Log.csv', mode='a', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    # Add header
    if csvfile.tell() == 0:
        writer.writeheader()

    # Add each keystroke information
    for event in device.read_loop():
        if event.type == evdev.ecodes.EV_KEY:
            key_event = evdev.categorize(event)
            key_event_info = {fieldnames[0]: key_event.event.timestamp(), fieldnames[1]: key_event.keycode, fieldnames[2]: key_event.keystate}
            key_events.append(key_event_info)
            writer.writerow(key_event_info)
