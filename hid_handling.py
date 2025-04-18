# import subprocess

# # Replace with your device's hardware ID (Find it in Device Manager)
HID_HARDWARE_ID = "USB\\VID_2341&PID_8036&MI_02\\6&1b780c72&0&0002"

# def disable_hid_device(hardware_id):
#     try:
#         # Run devcon command to disable the HID device
#         result = subprocess.run(["devcon", "disable", f"@{hardware_id}"], capture_output=True, text=True, shell=True)
#         if "disabled" in result.stdout.lower():
#             print(f"Successfully disabled HID device: {hardware_id}")
#         else:
#             print(f"Failed to disable HID device. Output: {result.stdout}")
#     except Exception as e:
#         print(f"Error: {e}")


import subprocess

def detect_hid_devices():
    command = subprocess.run(["pnputil", "/enum-devices", "/connected"], capture_output=True, text=True, shell=True)
    hid_ids = []
    for line in command.stdout.splitlines():
        if "Instance ID:" in line:
            id = line.split(":", 1)[1].strip()
            hid_ids.append(id)
    return hid_ids

def blacklist_hid_devices(ids):
    try:
        for id in ids:
            print(f"Attempt to blacklist device with ID {id} ...")
            command = subprocess.run(["pnputil", "/disable-device", id], capture_output=True, text=True, shell=True)
            if "successfully" in command.stdout.lower():
                print(f"Successfully blacklist device with ID {id}")
            else:
                print(f"Cannot blacklist device with ID {id}. Output message: {command.stdout}")

    except Exception as e:
        print(f"Message: {e}")
