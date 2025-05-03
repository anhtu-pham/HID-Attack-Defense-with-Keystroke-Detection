#!/usr/bin/env python3
"""
HID Keyboard Disabler
unbind_device() to disable device
create_udev_rule() to permanently disable 
"""

import os
import subprocess
import time
import logging
from datetime import datetime
import platform
import sys 
import threading
DEVCON_PATH = os.path.join(os.getcwd(), "devcon.exe")  # Adjust path if needed

latest_active_device = None

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

if IS_LINUX:
    try:
        import pyudev
    except ImportError:
        logging.info("pyudev not found. Please install it via pip.")
        exit(1)
        
# Determine log path
log_path = (
    "/var/log/keyboard-disabler.log" if IS_LINUX
    else os.path.join(os.getenv("TEMP") or ".", "keyboard-disabler.log")
)

# Ensure parent directory exists
log_dir = os.path.dirname(log_path)
if not os.path.exists(log_dir):
    logging.info("Parent Directory Doesnt Exist, Creating")
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception as e:
        logging.info(f"Failed to create log directory: {log_dir}\n{e}")
        log_path = "keyboard-disabler.log"  # fallback to current dir

# Now set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=log_path
)

logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

# Keep track of recently disabled devices to avoid duplicates
# Format: {(vendor_id, product_id): timestamp}
recently_disabled = {}
# Timeout in seconds to consider a device the same (5 seconds should be enough)
DUPLICATE_TIMEOUT = 5

def is_keyboard(device):
    """Check if the device is a keyboard"""
    if device.get('ID_INPUT_KEYBOARD') == '1':
        return True
    
    # Additional check for keyboard-like devices
    if device.device_node and 'event' in device.device_node:
        try:
            input_info = subprocess.run(
                ['input_keymap', '--device', device.device_node],
                capture_output=True, text=True, check=False
            )
            return 'keyboard' in input_info.stdout.lower()
        except (FileNotFoundError, subprocess.SubprocessError):
            pass
    
    return False

def get_device_info(device):
    """Extract device path and identification"""
    vendor_id = device.get('ID_VENDOR_ID', '')
    product_id = device.get('ID_MODEL_ID', '')
    device_path = device.get('DEVPATH', '')
    name = device.get('NAME', device.get('ID_MODEL', 'Unknown Keyboard'))
    serial = device.get('ID_SERIAL', '')
    
    # For devices with missing vendor/product IDs, try to extract from sysfs path
    if not vendor_id or not product_id:
        try:
            # Extract from HID path if possible
            for part in device_path.split('/'):
                if part.startswith('0003:'):
                    parts = part.split(':')
                    if len(parts) >= 3:
                        if not vendor_id:
                            vendor_id = parts[1]
                        if not product_id:
                            product_id = parts[2].split('.')[0]
                        break
        except Exception as e:
            logging.warning(f"Failed to extract vendor/product from path: {e}")
    
    # Generate a unique device identifier
    usb_path = None
    try:
        # Get the USB path (to identify different ports)
        for part in device_path.split('/'):
            if part.startswith('usb') and ':' in part:
                usb_path = part
                break
    except Exception:
        pass
    
    return {
        'vendor_id': vendor_id,
        'product_id': product_id,
        'device_path': device_path,
        'name': name,
        'serial': serial,
        'usb_path': usb_path,
        # Create a device fingerprint for deduplication
        'fingerprint': f"{vendor_id}:{product_id}:{usb_path}"
    }

def unbind_device(device_info):
    """Unbind the device from its driver using sysfs"""
    try:
        # Get HID device path
        device_path = device_info['device_path']
        
        # Try multiple methods to find and unbind the device
        
        # Method 1: Directly find HID device path components
        hid_device = None
        path_parts = device_path.split('/')
        for i, part in enumerate(path_parts):
            if part.startswith('0003:'):
                hid_device = part
                break
        
        if hid_device:
            # Find the driver (usually hid-generic or apple for Apple keyboards)
            driver_paths = [
                "/sys/bus/hid/drivers/hid-generic",
                "/sys/bus/hid/drivers/apple",
                "/sys/bus/hid/drivers/usbhid"
            ]
            
            for driver_path in driver_paths:
                unbind_path = f"{driver_path}/unbind"
                if os.path.exists(unbind_path) and os.path.exists(f"{driver_path}/{hid_device}"):
                    try:
                        with open(unbind_path, 'w') as f:
                            f.write(hid_device)
                        logging.info(f"Successfully unbound keyboard device: {hid_device}")
                        return True
                    except (IOError, OSError) as e:
                        logging.error(f"Failed to write to {unbind_path}: {e}")
        
        # Method 2: Use the uevent approach
        syspath = f"/sys{device_path}"
        if os.path.exists(f"{syspath}/uevent"):
            try:
                with open(f"{syspath}/uevent", 'w') as f:
                    f.write("remove")
                logging.info(f"Removed device using uevent: {device_info['name']}")
                return True
            except (IOError, OSError) as e:
                logging.error(f"Failed to remove device using uevent: {e}")
        
        # Method 3: Search for associated HID devices
        if device_info['vendor_id'] and device_info['product_id']:
            # Find all HID devices with matching vendor/product ID
            try:
                hid_devices = []
                for dev in os.listdir("/sys/bus/hid/devices"):
                    if dev.startswith(f"0003:{device_info['vendor_id']}:{device_info['product_id']}"):
                        hid_devices.append(dev)
                
                if hid_devices:
                    success = False
                    for dev in hid_devices:
                        for driver in ["hid-generic", "apple", "usbhid"]:
                            unbind_path = f"/sys/bus/hid/drivers/{driver}/unbind"
                            if os.path.exists(unbind_path) and os.path.exists(f"/sys/bus/hid/drivers/{driver}/{dev}"):
                                try:
                                    with open(unbind_path, 'w') as f:
                                        f.write(dev)
                                    logging.info(f"Successfully unbound related HID device: {dev}")
                                    success = True
                                except (IOError, OSError) as e:
                                    logging.error(f"Failed to unbind related HID device {dev}: {e}")
                    
                    return success
            except Exception as e:
                logging.error(f"Error searching for related HID devices: {e}")
        
        return False
    except Exception as e:
        logging.error(f"Error unbinding device: {e}")
        return False

def create_udev_rule(device_info):
    """Create a udev rule to disable this keyboard permanently"""
    vendor_id = device_info['vendor_id']
    product_id = device_info['product_id']
    
    if not vendor_id or not product_id:
        logging.warning("Missing vendor or product ID, cannot create udev rule")
        return False
    
    rule = f"""# Disable keyboard {device_info['name']} (created by keyboard-disabler)
SUBSYSTEM=="input", ACTION=="add", ATTRS{{idVendor}}=="{vendor_id}", ATTRS{{idProduct}}=="{product_id}", RUN+="/bin/sh -c 'echo remove > /sys$env{{DEVPATH}}/uevent'"
ACTION=="add", ATTRS{{idVendor}}=="{vendor_id}", ATTRS{{idProduct}}=="{product_id}", RUN+="/bin/sh -c 'echo 0 > /sys$env{{DEVPATH}}/../authorized'"
"""
    
    try:
        rule_path = "/etc/udev/rules.d/99-disable-keyboard.rules"
        # Check if rule already exists
        if os.path.exists(rule_path):
            with open(rule_path, 'r') as f:
                content = f.read()
                if f'idVendor}}=="{vendor_id}", ATTRS{{idProduct}}=="{product_id}"' in content:
                    logging.info(f"Rule for {vendor_id}:{product_id} already exists")
                    return True
        
        # Append rule
        with open(rule_path, 'a') as f:
            f.write(rule)
        
        # Reload udev rules
        subprocess.run(['udevadm', 'control', '--reload'], check=False)
        logging.info(f"Created udev rule for {vendor_id}:{product_id}")
        return True
    except (IOError, OSError) as e:
        logging.error(f"Failed to create udev rule: {e}")
        return False
    
def is_duplicate_device(device_info):
    """Check if this device was recently disabled to avoid duplicates"""
    fingerprint = device_info['fingerprint']
    current_time = time.time()
    
    # Clean up old entries
    for key in list(recently_disabled.keys()):
        if current_time - recently_disabled[key] > DUPLICATE_TIMEOUT:
            del recently_disabled[key]
    
    # Check if this is a duplicate
    if fingerprint in recently_disabled:
        return True
    
    # Not a duplicate, add to recently disabled
    recently_disabled[fingerprint] = current_time
    return False

def extract_vendor_id(device_id):
    # Extracts VID_1234
    import re
    match = re.search(r'VID_([0-9A-F]{4})', device_id, re.IGNORECASE)
    return match.group(1) if match else "0000"

def extract_product_id(device_id):
    # Extracts PID_5678
    import re
    match = re.search(r'PID_([0-9A-F]{4})', device_id, re.IGNORECASE)
    return match.group(1) if match else "0000"

def detect_keyboards_and_callback(callback_function=None, stop_on_detection=False):
    """
    Detect and return the device currently sending keystrokes (interrupt-like behavior).
    Maintains the latest active device in global `latest_active_device`.
    """
    global latest_active_device

    if IS_LINUX:
        try:
            from evdev import InputDevice, categorize, ecodes, list_devices
        except ImportError:
            logging.error("Please install evdev: pip install evdev")
            return

        devices = [InputDevice(path) for path in list_devices()]
        keyboards = [dev for dev in devices if 'keyboard' in dev.name.lower()]

        logging.info("Monitoring active keyboards for keystroke input...")

        for dev in keyboards:
            def monitor_device(device):
                global latest_active_device
                for event in device.read_loop():
                    if event.type == ecodes.EV_KEY and event.value == 1:  # key down
                        device_info = {
                            'name': device.name,
                            'vendor_id': '0000',  # not available via evdev
                            'product_id': '0000',
                            'device_path': device.path,
                            'serial': '',
                            'fingerprint': device.path,
                        }
                        latest_active_device = device_info  # update latest device
                        logging.info(f"Key press detected from: {device.path}")
                        if callback_function:
                            callback_function(device_info)
                        if stop_on_detection:
                            return

            threading.Thread(target=monitor_device, args=(dev,), daemon=True).start()

    elif IS_WINDOWS:
        logging.warning("Active device keystroke detection is limited on Windows. Using polling fallback.")
        known_devices = set()

        while True:
            try:
                result = subprocess.run(
                    ['powershell', '-Command',
                     'Get-PnpDevice -Class Keyboard | Select-Object -ExpandProperty InstanceId'],
                    capture_output=True, text=True
                )

                device_ids = set(result.stdout.strip().splitlines())
                new_devices = device_ids - known_devices
                for device_id in new_devices:
                    device_info = {
                        'name': device_id,
                        'vendor_id': extract_vendor_id(device_id),
                        'product_id': extract_product_id(device_id),
                        'device_path': '',
                        'serial': '',
                        'fingerprint': device_id,
                    }
                    latest_active_device = device_info
                    logging.info(f"Detected input from: {device_id}")
                    if callback_function:
                        callback_function(device_info)
                    known_devices.add(device_id)
                    if stop_on_detection:
                        return
                time.sleep(2)
            except Exception as e:
                logging.error(f"Error polling keyboards on Windows: {e}")
                time.sleep(5)

def get_latest_active_device():
    """Returns the most recently active HID device (even if now disconnected)."""
    global latest_active_device
    return latest_active_device

                         
def blacklist_hid_device(device_info):
    logging.info(f"Attempting to blacklist keyboard: {device_info.get('name', 'Unknown')}")

    if IS_LINUX:
        # Try to disable it by unbinding
        if unbind_device(device_info):
            logging.info(f"Keyboard successfully disabled")
            if create_udev_rule(device_info):
                logging.info(f"Permanent udev rule created to block this device")
            else:
                logging.info(f"Failed to create permanent udev rule")
            return True
        else:
            logging.info(f"Failed to disable keyboard")
            return False

    elif IS_WINDOWS:
        try:
            vendor_id = device_info.get("vendor_id", "")
            product_id = device_info.get("product_id", "")
            device_id = f"HID\\VID_{vendor_id}&PID_{product_id}"

            logging.info(f"Trying to disable device using DevCon: {device_id}")
            result = subprocess.run([DEVCON_PATH, 'disable', device_id], capture_output=True, text=True)

            if "disabled" in result.stdout.lower():
                logging.info("Device successfully disabled.")
                return True
            else:
                logging.warning("DevCon output:\n" + result.stdout)
                logging.error("Failed Wto disable device via devcon.")
                return False
        except FileNotFoundError:
            logging.error("devcon.exe not found. Make sure it's in the working directory or system PATH.")
            return False
        except Exception as e:
            logging.error(f"Error disabling HID device on Windows: {e}")
            return False
# if IS_LINUX:
#     subprocess.run(['udevadm', 'control', '--reload'], check=False)
# elif IS_WINDOWS:
#     subprocess.run(['devcon', 'disable', device_id], check=False)   