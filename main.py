from usbmonitor import USBMonitor
from usbmonitor.attributes import ID_MODEL, ID_MODEL_ID, ID_VENDOR_ID

device_info_str = lambda device_info: f"{device_info[ID_MODEL]} ({device_info[ID_MODEL_ID]} - {device_info[ID_VENDOR_ID]})"
# Define the `on_connect` and `on_disconnect` callbacks
on_connect = lambda device_id, device_info: print(f"Connected: {device_info_str(device_info=device_info)}")
on_disconnect = lambda device_id, device_info: print(f"Disconnected: {device_info_str(device_info=device_info)}")

# Create the USBMonitor instance
monitor = USBMonitor()
devices_dict = monitor.get_available_devices()

for device_id, device_info in devices_dict.items():
    print(f"{device_id} -- {device_info['ID_MODEL']} ({device_info['ID_MODEL_ID']} - {device_info['ID_VENDOR_ID']})")

# Start the daemon
monitor.start_monitoring(on_connect=on_connect, on_disconnect=on_disconnect)

# Keep the main thread alive to allow the monitoring to continue
try:
    while True:
        pass
except KeyboardInterrupt:
    print("Stopping USB monitor...")
    monitor.stop_monitoring()


