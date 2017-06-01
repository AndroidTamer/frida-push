#!/usr/bin/env python3

""" This script aims to automate the process of starting frida-server
on an Android device (for now). The script is a part of AndroidTamer
project and is based on this issue: 
https://github.com/AndroidTamer/Tools_Repository/issues/234.

This script performs following things:
1. Try to determine the device architecture
2. Download the frida-server and extract it
3. Push it to the device and execute it
4. Save the PID of the process and write it to 'frida.pid' file.

#Todo:
* Better exception handling.
* Implement better/robust architecture detection code
* Implement for more devices
* Implement the feature to kill frida-server afterwards
"""

import sys
import subprocess
import os
import lzma
import requests

try:
    from frida import __version__ as FRIDA_VERSION
except ImportError:
    print("[-] Frida not found. Please run `pip install frida` to proceed.")
    sys.exit(1)

__version__ = 0.1
__author__ = "c0dist@Garage4Hackers"

# Just put "adb" below, if adb exists in your system path.
adb_path = "adb"

def device_exists():
    """ This functions checks if any device is connected or not.
    """
    cmd = '{} devices -l | grep -v "List of devices attached"'.format(adb_path)
    # We know shell=True is bad, but should be fine here.
    output = str(subprocess.check_output(cmd, shell=True).strip(), "utf-8")
    if output:
        print("\t[+] Found following device:")
        print("\t{}".format(output))
        return True
    return False


def get_device_arch():
    """ This function tries to determine the architecture of the device, so that
    the correct version of Frida-server can be downloaded. The function, first, 
    tries to get the output of `uname -m` and then it tries to matches it against
    some known values. If not, then it tries `getprop ro.product.cpu.abi`.

    This function is probably the weakest part of the code. If you know of more
    Arch names from uname output, please contribute.

    :returns either "arch" that Frida release page understands or None.
    """
    arch = None

    uname_cmd = "{} shell uname -m".format(adb_path)
    uname_archs = ["i386", "i686", "arm64", "arm", "x86_64"]
    # We know shell=True is bad, but should be fine here.
    output = str(subprocess.check_output(uname_cmd, shell=True).lower().strip(), "utf-8")

    if output in uname_archs:
        if output in ["i386", "i686"]:
            arch = "i386"
        else:
            arch = output
    else:
        getprop_cmd = "{} shell getprop ro.product.cpu.abi".format(adb_path)
        getprop_archs = ["armeabi", "armeabi-v7a", "arm64-v8a", "x86", "x86_64"]
        # We know shell=True is bad, but should be fine here.
        output = str(subprocess.check_output(getprop_cmd, shell=True).lower().strip(), "utf-8")

        if output in getprop_archs:
            if output in ["armeabi", "armeabi-v7a"]:
                arch = "arm"
            elif output == "arm64-v8a":
                arch = "arm64"
            elif output == "x86":
                arch = "i386"
            else:
                arch = output
    return arch

def prepare_download_url(arch):
    """ Depending upon the arch provided, the function returns the download URL.
    """
    base_url = "https://github.com/frida/frida/releases/download/{}/frida-server-{}-android-{}.xz"
    return base_url.format(FRIDA_VERSION, FRIDA_VERSION, arch)

def download_and_extract(url, fname):
    """ This function downloads the given URL, extracts .xz archive 
    as given file name.

    :returns True if successful, else False.
    """
    data = None

    print("\t[+] Downloading: {}".format(url))
    req = requests.get(url, stream=True)
    if req.status_code == 200:
        # Downloading and writing the archive.
        archive_name = fname + ".xz"

        req.raw.decode_content = True
        with open(archive_name, "wb") as fh:
            for chunk in req.iter_content(1024):
                fh.write(chunk)

        with lzma.open(archive_name ) as fh:
            data = fh.read()
    else:
        print("\t[-] Error downloading frida-server.")
        print("\t[-] Got HTTP status code {} from server.".format(req.status_code))

    if data:
        print("\t[+] Writing file as: {}.".format(fname))
        with open(fname, "wb") as frida_server:
            frida_server.write(data)
        return True
    return False

def push_and_execute(fname):
    """This function pushes the file to device, makes it executable,
    and then finally runs the binary. The function also saves the PID 
    of process in 'frida.pid' file.
    """
    push_cmd = "{} push {} /data/local/tmp/frida-server".format(adb_path, fname)
    chmod_cmd = "{} shell chmod 0755 /data/local/tmp/frida-server".format(adb_path)
    execute_cmd = "{} shell su 0 '/data/local/tmp/frida-server' &".format(adb_path)
    ps_cmd = "%s shell 'su 0 ps' | grep frida-server | awk '{print $2}' > frida.pid" % (adb_path)

    status_code = os.system(push_cmd)
    if status_code == 0:
        print("\t[+] File pushed to device successfully.")
        os.system(chmod_cmd)
        print("\t[+] Executing frida-server on device.")
        os.system(execute_cmd)
        print("\t[+] Fetching the PID of frida-server and saving it to file.")
        os.system(ps_cmd)

    else:
        print("[-] Could not push the binary to device.")

def main():
    """ This function is where the magic happens.
    """
    if not device_exists():
        print("[-] No device found. Exiting.")
        sys.exit(1)

    print("[*] Current installed Frida version: {}".format(FRIDA_VERSION))
    print("[*] Trying to determine device's arch.")
    arch = get_device_arch()
    if arch:
        print("\t[+] Found arch: {}".format(arch))
        url = prepare_download_url(arch)
        fname = "frida-server-{}-android-{}".format(FRIDA_VERSION, arch)
        if download_and_extract(url, fname):
            push_and_execute(fname)
    else:
        print("\t[-] Could not determine device's arch. Exiting.")

if __name__ == "__main__":
    main()
