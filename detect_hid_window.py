import time
import pyudev
import win32api
import win32con
import win32gui
import win32file


def get_connected_hid_devices():
    """Fetches currently connected HID device instance IDs."""
    device_list = []
    
    key_path = r"SYSTEM\CurrentControlSet\Enum\HID"
    try:
        key = win32api.RegOpenKey(win32con.HKEY_LOCAL_MACHINE, key_path, 0, win32con.KEY_READ)
        
        i = 0
        while True:
            try:
                device = win32api.RegEnumKey(key, i)
                device_list.append(f"HID\\{device}")
                i += 1
            except OSError:
                break

        win32api.RegCloseKey(key)
    except Exception as e:
        print(f"Error accessing registry: {e}")

    return device_list


def detect_new_device():
    """Monitors for newly connected HID devices."""
    print("Monitoring for new HID devices...")
    
    # Initialize udev context for monitoring devices
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='hidraw')  # Listen for HID devices

    for device in iter(monitor.poll, None):
        if device.action == 'add':
            print(f"New HID device connected: {device.device_path}")


if __name__ == "__main__":
    existing_devices = set(get_connected_hid_devices())  # Store current devices

    while True:
        time.sleep(5)  # Check every 5 seconds
        new_devices = set(get_connected_hid_devices())
        
        added_devices = new_devices - existing_devices  # Detect newly connected devices
        if added_devices:
            for dev in added_devices:
                print(f"New HID Device Detected: {dev}")

            existing_devices = new_devices  # Update the known devices
