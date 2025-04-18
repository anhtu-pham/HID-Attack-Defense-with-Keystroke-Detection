# HID-Attack-Defense-with-Keystroke-Detection

How to flash ESP 8266 board

Install driver from https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers

Choose NodeMCU as board in Adruino IDE

Python version: 3.12

Install pip: https://pip.pypa.io/en/stable/installation/

Install through pip: pandas, matplotlib, scikit-learn, pynput, pyudev

# Edit the udev rule file
sudo nano /etc/udev/rules.d/99-disable-keyboard.rules

# Comment out or remove the lines for your keyboard
# Save and exit

# Reload udev rules
sudo udevadm control --reload-rules && sudo udevadm trigger

# Unplug and reconnect your keyboard make sure the cursor is focused away from the terminal