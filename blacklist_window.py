import subprocess

# Replace with your device's hardware ID (Find it in Device Manager)
HID_HARDWARE_ID = "HID\\VID_1234&PID_5678"

def disable_hid_device(hardware_id):
    try:
        # Run devcon command to disable the HID device
        result = subprocess.run(["devcon", "disable", f"@{hardware_id}"], capture_output=True, text=True, shell=True)
        if "disabled" in result.stdout.lower():
            print(f"Successfully disabled HID device: {hardware_id}")
        else:
            print(f"Failed to disable HID device. Output: {result.stdout}")
    except Exception as e:
        print(f"Error: {e}")

disable_hid_device(HID_HARDWARE_ID)
