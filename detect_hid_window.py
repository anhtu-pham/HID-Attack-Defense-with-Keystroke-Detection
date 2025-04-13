import hid
import time

def detect_devices():
    devices = hid.enumerate()
    device_paths = [device["path"] for device in devices]
    return device_paths
        
        

if __name__ == "__main__":
    # Get a list of all connected HID devices
    devices = hid.enumerate()
    
    print(f"Found {len(devices)} HID device(s)")
    
    # Print information about each device
    for device in devices:
        print("\nDevice Information:")
        print(f"  Vendor ID: {device['vendor_id']:#06x}")
        print(f"  Product ID: {device['product_id']:#06x}")
        print(f"  Product Name: {device['product_string']}")
        print(f"  Manufacturer: {device['manufacturer_string']}")
        print(f"  Serial Number: {device['serial_number']}")
        print(f"  Path: {device['path']}")
        print(f"  Interface Number: {device['interface_number']}")

if __name__ == "__main__":
    main()