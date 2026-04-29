import pyudev
import os
import subprocess

context = pyudev.Context()


def printConnectedUsbHubs():
    devices = context.list_devices(subsystem="usb")
    text = ""
    for device in devices:
        maxchild = int(device.attributes.get('maxchild', 0))
        model = device.get('ID_MODEL')

        if (maxchild == 0 or model.find("Hub") < 0):
            continue
        names = []

        def createChildName(port: int, model: str):
            return "port %s: %s" % (port, model)

        for i in range(maxchild):
            names.append(createChildName(i + 1, "Empty"))
        for child in device.children:
            if child.subsystem == "usb" and child.device_type == "usb_device":
                sys_name = child.sys_name  # e.g. "1-2.3.4"

                # Extract the port number (last segment after '.')
                if '.' in sys_name:
                    port = sys_name.split('.')[-1]
                else:
                    # Directly connected to root hub (no dot case like "1-2")
                    port = sys_name.split('-')[-1]

                model = child.get('ID_MODEL')
                names[int(port) - 1] = createChildName(port, model)

        text = text + "\n%s -> %s" % (device.get('ID_MODEL'), maxchild)
        for name in names:
            text = text + "\n" + " " * 4 + name
    return text


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
        subprocess.run(
            ["mount", dev_node, mount_point],
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print("Mount failed: ", e)
        return False


def startObserver():
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem="block")

    def log_event(action, device):
        if (action != "add" and action != "remove"):
            return
        if device.device_type != "partition":
            return
        if device.get('ID_BUS') != 'usb':
            return

        text = printConnectedUsbHubs()
        os.system('cls' if os.name == 'nt' else 'clear')
        print(action, device, text)
        dev_node = device.device_node
        if (action == "add"):
            print(dev_node)
            mountDir = createMountDir(dev_node)
            if (not mountDevice(dev_node, mountDir)):
                return
            for f in os.listdir(mountDir):
                print("File: %s" % f)

    observer = pyudev.MonitorObserver(monitor, log_event)
    observer.start()
    return observer


# Keep the main thread alive to allow the monitoring to continue
if (__name__ == "__main__"):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(printConnectedUsbHubs())
    observer = startObserver()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Stopping USB monitor...")
        observer.stop()