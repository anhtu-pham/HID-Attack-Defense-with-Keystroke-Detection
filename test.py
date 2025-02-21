import evdev
import csv

fieldnames = ['Timestamp', 'Key', 'KeyState']
for dev in evdev.list_devices():
    print(evdev.InputDevice(dev))

device = evdev.InputDevice('/dev/input/event4')
# event_list = []
with open('Log.csv', mode='a', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    if csvfile.tell() == 0:
        writer.writeheader()


    for event in device.read_loop():
        if event.type == evdev.ecodes.EV_KEY:
            key_event = evdev.categorize(event)
            entry = {'Timestamp': key_event.event.timestamp(), 'Key': key_event.keycode, 'KeyState' : key_event.keystate}
            # event_list.append(entry)
            writer.writerow(entry)


