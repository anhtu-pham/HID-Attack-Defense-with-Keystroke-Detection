#!/usr/bin/env python3
"""
HID Keyboard Disabler
unbind_device() to disable device
create_udev_rule() to permanently disable 
"""

import os
import subprocess
import time
import pyudev
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='/var/log/keyboard-disabler.log'
)

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

def detect_keyboards_and_callback(callback_function=None, stop_on_detection=False):
    """
    Monitor for new keyboard connections with optional callback
    
    Args:
        callback_function (callable, optional): Function to call when a new keyboard is detected.
                                               This function will receive the device_info dictionary.
        stop_on_detection (bool, optional): If True, stop monitoring after first detection and callback
    
    Returns:
        None
    """
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='input')
    
    # Enable monitoring
    monitor.start()
    logging.info("Starting keyboard monitoring service")
    print("Keyboard disabler service started. Monitoring for new keyboard devices...")
    
    # Monitor for new devices
    for device in iter(monitor.poll, None):
        if device.action == 'add' and is_keyboard(device):
            device_info = get_device_info(device)
            
            # Skip if this is a duplicate detection
            if is_duplicate_device(device_info):
                logging.info(f"Skipping duplicate device: {device_info['name']} ({device_info['fingerprint']})")
                continue
            
            logging.warning(f"New keyboard detected: {device_info['name']} ({device_info['vendor_id']}:{device_info['product_id']})")
            print(f"New keyboard detected - {device_info['name']}")
            
            # If callback is provided, call it with the device info
            if callback_function:
                callback_function(device_info)
                
                # If stop_on_detection is True, break the loop after first detection
                if stop_on_detection:
                    break

def blacklist_hid_device(device_info):
    """Disable and blacklist a keyboard based on its device info"""
    print(f"Attempting to blacklist keyboard: {device_info['name']}")
    # Try to disable it by unbinding
    if unbind_device(device_info):
        print(f"Keyboard successfully disabled")
        # Create persistent rule
        if create_udev_rule(device_info):
            print(f"Permanent udev rule created to block this device")
        else:
            print(f"Failed to create permanent udev rule")
        return True
    else:
        print(f"Failed to disable keyboard")
        return False
