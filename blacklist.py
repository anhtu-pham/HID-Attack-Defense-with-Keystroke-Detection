import evdev
import time

def block_input_device(device_path):
    try:
        device = evdev.InputDevice(device_path)
        print(f"Grabbing device: {device.name}")
        device.grab()  # Prevents other processes from reading input events
        print("Device blocked. Press Ctrl+C to release.")
        
        # Keep the script running to maintain the grab
        while True:
            pass

    except PermissionError:
        print("Permission denied. Run the script as root.")
    except FileNotFoundError:
        print("Device not found. Check the device path.")

if __name__ == "__main__":
    while(True):
        time.sleep(1)
        current_devices = set(evdev.list_devices())

        new_devices = current_devices - known_devices
        if new_devices:
            for device in new_devices:
                dev = evdev.InputDevice(device)

