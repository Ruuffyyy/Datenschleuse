import pyudev
import os
import subprocess
import zipfile
import tarfile
from datetime import datetime

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
                sys_name = child.sys_name

                if '.' in sys_name:
                    port = sys_name.split('.')[-1]
                else:
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


def archiveMountedDevice(mount_point: str, archive_format: str = "zip", recursive: bool = True):
    script_dir = get_script_dir()
    archive_base_dir = os.path.join(script_dir, "archives")
    os.makedirs(archive_base_dir, exist_ok=True)

    if archive_format not in ("zip", "tar", "gztar"):
        raise ValueError("archive_format muss zip, tar oder gztar sein")

    folder_name = os.path.basename(mount_point.rstrip("/"))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    extension_map = {"zip": ".zip", "tar": ".tar", "gztar": ".tar.gz"}
    archive_name = os.path.join(archive_base_dir, f"{folder_name}_{timestamp}{extension_map[archive_format]}")

    SKIP_PREFIXES = (".", "$", "System Volume Information")

    def should_skip(name: str) -> bool:
        return any(name.startswith(p) for p in SKIP_PREFIXES)

    def collect_files() -> list[tuple[str, str]]:
        files = []
        if recursive:
            for dirpath, dirnames, filenames in os.walk(mount_point):
                dirnames[:] = [d for d in dirnames if not should_skip(d)]
                for filename in filenames:
                    if should_skip(filename):
                        continue
                    full_path = os.path.join(dirpath, filename)
                    arcname = os.path.relpath(full_path, mount_point)
                    files.append((full_path, arcname))
        else:
            for filename in os.listdir(mount_point):
                if should_skip(filename):
                    continue
                full_path = os.path.join(mount_point, filename)
                if os.path.isfile(full_path):
                    files.append((full_path, filename))
        return files

    files = collect_files()

    if archive_format == "zip":
        with zipfile.ZipFile(archive_name, "w", zipfile.ZIP_DEFLATED) as zf:
            for full_path, arcname in files:
                try:
                    zf.write(full_path, arcname)
                except (PermissionError, OSError) as e:
                    print(f"Überspringe {full_path}: {e}")

    elif archive_format in ("tar", "gztar"):
        mode = "w:gz" if archive_format == "gztar" else "w"
        with tarfile.open(archive_name, mode) as tf:
            for full_path, arcname in files:
                try:
                    tf.add(full_path, arcname=arcname)
                except (PermissionError, OSError) as e:
                    print(f"Überspringe {full_path}: {e}")

    return archive_name


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
            for fmt in ("zip", "tar", "gztar"):  # <-- alle drei Formate
                archive_path = archiveMountedDevice(mountDir, fmt)
                print("Archiv erstellt:", archive_path)

    observer = pyudev.MonitorObserver(monitor, log_event)
    observer.start()
    return observer

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