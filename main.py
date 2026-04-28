mport pyudev
import os
import subprocess
import serial
import time

context = pyudev.Context()

SERIAL_PORT = "/dev/ttyACM0"
BAUDRATE = 115200

esp = None

def connect_esp():
    global esp
    try:
        esp = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
        time.sleep(2)
        return True
    except Exception as e:
        print("ESP Verbindung fehlgeschlagen:", e)
        esp = None
        return False


def send_to_esp(text: str):
    global esp
    if esp is None or not esp.is_open:
        if not connect_esp():
            return
    try:
        esp.write((text + "\n").encode("utf-8", errors="replace"))
        esp.flush()
    except Exception as e:
        print("Senden an ESP fehlgeschlagen:", e)


def printConnectedUsbHubs():
    devices = context.list_devices(subsystem="usb")
    text = ""
    for device in devices:
        maxchild = int(device.attributes.get('maxchild', 0))
        model = device.get('ID_MODEL')

        if model is None:
            continue
        if maxchild == 0 or "Hub" not in model:
            continue

        names = []

        def createChildName(port: int, model: str):
            return f"port {port}: {model}"

        for i in range(maxchild):
            names.append(createChildName(i + 1, "Empty"))

        for child in device.children:
            if child.subsystem == "usb" and child.device_type == "usb_device":
                sys_name = child.sys_name

                if '.' in sys_name:
                    port = sys_name.split('.')[-1]
                else:
                    port = sys_name.split('-')[-1]

                child_model = child.get('ID_MODEL') or "Unknown"
                try:
                    names[int(port) - 1] = createChildName(port, child_model)
                except:
                    pass

        text += f"\n{device.get('ID_MODEL')} -> {maxchild}"
        for name in names:
            text += "\n    " + name
    return text.strip()


def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def createMountDir(dev_node: str):
    script_dir = get_script_dir()
    base = os.path.join(script_dir, "mounts")
    name = dev_node.replace("/dev/", "")
    path = os.path.join(base, name)
    os.makedirs(path, exist_ok=True)
    return path


def mountDevice(dev_node: str, mount_point: str):
    try:
        subprocess.run(["mount", dev_node, mount_point], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print("Mount failed:", e)
        return False


def startObserver():
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem="block")

    def log_event(action, device):
        if action not in ("add", "remove"):
            return
        if device.device_type != "partition":
            return
        if device.get('ID_BUS') != 'usb':
            return

        hub_text = printConnectedUsbHubs()
        dev_node = device.device_node

        if action == "add":
            mount_dir = createMountDir(dev_node)
            if not mountDevice(dev_node, mount_dir):
                msg = f"USB erkannt: {dev_node}\nMount fehlgeschlagen"
                print(msg)
                send_to_esp(msg)
                return

            files = os.listdir(mount_dir)
            file_text = "\n".join([f"File: {f}" for f in files[:15]])
            msg = f"USB erkannt: {dev_node}\n\nHubs:\n{hub_text}\n\nDateien:\n{file_text}"
            print(msg)
            send_to_esp(msg)

        elif action == "remove":
            msg = f"USB entfernt: {dev_node}"
            print(msg)
            send_to_esp(msg)

    observer = pyudev.MonitorObserver(monitor, log_event)
    observer.start()
    return observer


if __name__ == "__main__":
    connect_esp()
    start_text = printConnectedUsbHubs()
    print(start_text)
    send_to_esp("USB Monitor gestartet\n\n" + start_text)

    observer = startObserver()
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("Stopping USB monitor...")
        observer.stop()
        if esp and esp.is_open:
            esp.close()