# HID-Attack-Defense-with-Keystroke-Detection

How to flash ESP 8266 board

Install driver from https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers

Choose NodeMCU as board in Adruino IDE

Python version: 3.12

Libraries and modules needed: numpy, pandas, scikit-learn, pynput, pyudev, matplotlib, subprocess, csv, time, datetime

## How to unblock device after demo
### Edit the udev rule file
1. sudo nano /etc/udev/rules.d/99-disable-keyboard.rules

2. Comment out or remove the lines for your keyboard

3. Save and exit

### Reload udev rules
sudo udevadm control --reload-rules && sudo udevadm trigger

### Unplug and reconnect your keyboard
