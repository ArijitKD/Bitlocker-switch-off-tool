import ctypes
import sys
import subprocess as sp
import os
import time
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox as mbox


errno: int = 0
errdesc: str = ""


## CONSTANTS
APPNAME = "BitLocker Switch Off Tool"
VERSION = "1.0"
COPYRIGHT = "Copyright (c) 2025-Present Arijit Kumar Das " \
            "<arijitkdgit.official@gmail.com>.\n" \
            "This free software is provided to you under " \
            "the terms of the GNU General Public License " \
            "(Version 3.0+).\nA full copy of the license " \
            "text can be found at https://www.gnu.org/lic" \
            "enses/gpl.html."


## ERRORCODES
ERR_CLEARKEYS_FAIL = -2


def get_last_error() -> tuple:
    return (errno, errdesc)


def set_error(cur_errno: int, cur_errdesc: str) -> None:
    global errno, errdesc
    errno = cur_errno
    errdesc = cur_errdesc

    
def is_admin() -> bool:
    return bool(ctypes.windll.shell32.IsUserAnAdmin())


def get_drives() -> list:
    bitmask: int = ctypes.windll.kernel32.GetLogicalDrives()
    drives: list = []
    for i in range(26):
        if (bitmask & (1 << i)):
            drives.append(f"{chr(65 + i)}:")
    return drives


def get_encrypted_drives() -> dict:
    drives: list = get_drives()
    encr_drives: dict = {}

    for drive in drives:
        manage_bde = sp.run(["manage-bde", "-status", drive],
                    text = True,
                    stdout = sp.PIPE,
                    stderr = sp.PIPE,
                    creationflags=sp.CREATE_NO_WINDOW)

        if (manage_bde.returncode == 0):
            output_lines: list = manage_bde.stdout.split("\n")
            encr_percent: float = 0.0
            suspect_line: str = output_lines[9].strip().lower()
            if (suspect_line.startswith("percentage encrypted")):
                encr_percent = float(suspect_line.split(":")[1][:-1])
            else:
                for line in output_lines:
                    line = line.strip().lower()
                    if (line.startswith("percentage encrypted")):
                        encr_percent = float(line.split(":")[1][:-1])
            if (encr_percent > 0.0):
                encr_drives[drive] = encr_percent

    return encr_drives


def os_drive() -> str:
    return os.environ["SYSTEMROOT"].split(":")[0]+":"


def clear_autounlock_keys() -> int:
    manage_bde = sp.run(["manage-bde", "-autounlock", "-ClearAllKeys", os_drive()],
                text = True,
                stdout = sp.PIPE,
                stderr = sp.PIPE,
                creationflags=sp.CREATE_NO_WINDOW)
    if (manage_bde.returncode != 0):
        set_error(ERR_CLEARKEYS_FAIL, manage_bde.stdout)
        return -1
    return 0


def is_system_plugged_in() -> int:
    buf = (ctypes.c_byte * 6)()  # int8_t buf[6]; SYSTEM_POWER_STATUS is 6 bytes
    if (not ctypes.windll.kernel32.GetSystemPowerStatus(buf)):
        return -1
    return int(buf[0] == 1)  # ACLineStatus is the first byte


def init_decryption(encr_drives) -> None:
    for drive in encr_drives:
        manage_bde = sp.run(["manage-bde", "-off", drive], text = True,
                            stdout = sp.PIPE, stderr = sp.PIPE)


def stage2_updates(root, stage2stat_label, bottom_label) -> None:
    encr_drives: dict = get_encrypted_drives()
    encr_percents: tuple = tuple(encr_drives.values())
    encr_drivenames: tuple = tuple(encr_drives.keys())
    percent_decrypted: float = 100.0

    if (encr_drivenames != ()):
        percent_decrypted = sum([(100.0 - x) for x in encr_percents]) / len(encr_drivenames)

    print ("\r[STAGE-2]: Decrypting drives: %d%% complete"%(percent_decrypted,), end = "")

    if (percent_decrypted < 100):
        if (root is not None):
            stage2stat_label.configure(text = "RUNNING (%d%% complete)"%(percent_decrypted,))
            root.after(5000,
                       lambda : stage2_updates(root, stage2stat_label, bottom_label))
        else:
            time.sleep(5)
            stage2_updates(root, stage2stat_label, bottom_label)
    else:
        if (root is not None):
            root.protocol("WM_DELETE_WINDOW", lambda: root.destroy())
            stage2stat_label.configure(text = "SUCCESS", foreground = "green")
            bottom_label.configure(text = "BitLocker is now turned off. "
                                   "You may safely exit this window.", foreground = "black")
        print ("\n\nThe operation completed successfully. BitLocker is now turned off.")
        mbox.showinfo(APPNAME,
                      "BitLocker has been turned off completely. "
                      "All encrypted drives have been successfully decrypted.",
                      detail = "You may now try installing Linux in a "
                      "multi-boot configuration.") if root is not None else None


def main() -> None:
    gui_enabled: bool = False
    if (sys.executable.endswith("pythonw.exe")):
        gui_enabled: bool = True
    print (APPNAME + "\n", "Version: %s"%(VERSION) + "\n", COPYRIGHT + "\n", sep = "")

    if (not is_admin()):
        ret_val: int = ctypes.windll.shell32.ShellExecuteW(None, "runas",
                                                           sys.executable,
                                                           " ".join(sys.argv), None,
                                                           0) if gui_enabled else -1
        if (ret_val > 32):
            sys.exit(0)

        else:
            print ("ERROR: Cannot continue, non-privileged mode detected. "
                   "Please run the program as administrator.")
            mbox.showwarning(APPNAME,
                             "Please run the program as an administrator. This is "
                             "required to turn off BitLocker.",
                             detail = "Right-click on the program shortcut and click "
                             "\"Run as administrator\". On Windows 11, you might "
                             "also need to click on \"Show more options\" before "
                             "that shows up.") if gui_enabled else None
            sys.exit(1)

    plugged_in_status: int = is_system_plugged_in()

    if (plugged_in_status == 0):
        if (mbox.askretrycancel(APPNAME,
                                "Please plug in your device before continuing.",
                                detail = "Power loss while the program is running "
                                "may cause data corruption.") if gui_enabled else None):
            print ("Restarting program...\n\n")
            main()
        print ("ERROR: Cannot continue, system is not plugged in. "
               "Please connect your device to an external power source.")
        sys.exit(1)

    elif (plugged_in_status == -1):
        print ("WARNING: Could not determine system power status. Device may not be plugged in.\n")
        if ((not mbox.askokcancel(APPNAME,
                                "We couldn\'t determine if your device is plugged in. "
                                "Please plug in your device before continuing. Power loss "
                                "while the program is running may cause data corruption.",
                                detail = "By clicking on \'OK\', you confirm that the device "
                                "is plugged in.")) if gui_enabled else None):
            print ("Operation aborted by user.")
            sys.exit(1)

    encr_drives: dict = get_encrypted_drives()

    if (sum(encr_drives.values()) == 0.0):
        print ("No drives are encrypted by BitLocker.")
        mbox.showinfo(APPNAME,
                      "BitLocker is turned off. All drives on this system "
                      "are fully decrypted. No further action is required.",
                      detail = "You may try installing Linux in a "
                      "multi-boot configuration.") if gui_enabled else None
        sys.exit(0)

    print ("WARNING: Turning off power or attempting to shutdown "
           "the computer while the decryption process is running can lead to\n"
           "irrecoverable data loss and may prevent the system from booting. "
           "Please make sure that the computer doesn\'t lose power.\n"
           "Additionally, do not disconnect any storage devices until the "
           "process is complete.\n")

    print ("[STAGE-1]: Clear automatic unlock keys for data volumes: Running...",
               end = "", flush = True)

    if (gui_enabled):
        root = tk.Tk()
        root_dim: tuple = (480, 200)
        center_x: int = int((root.winfo_screenwidth()/2) - (root_dim[0]/2))
        center_y: int = int((root.winfo_screenheight()/2) - (root_dim[1]/2))
        root.geometry("%dx%d+%d+%d" % (root_dim + (center_x, center_y)))
        root.resizable(0, 0)
        root.title(APPNAME)
        root.protocol("WM_DELETE_WINDOW",
                      lambda: mbox.showwarning(APPNAME,
                                               "You cannot close the program at this point. "
                                               "Please wait for the decryption process to finish."))

        stage1 = tk.Frame(root)
        stage1_label = ttk.Label(stage1, text = "STAGE 1: Clear automatic unlock keys for data volumes")
        stage1stat_label = ttk.Label(stage1, text = "RUNNING", foreground = "blue")
        stage1.pack(side = tk.TOP, fill = tk.BOTH, pady = (20, 0))
        stage1_label.pack(side = tk.LEFT, padx = 20)
        stage1stat_label.pack(side = tk.RIGHT, padx = 20)

        stage2 = tk.Frame(root)
        stage2_label = ttk.Label(stage2, text = "STAGE 2: Decrypt all BitLocker encrypted drives")
        stage2stat_label = ttk.Label(stage2, text = "PENDING", foreground = "blue")
        stage2.pack(side = tk.TOP, fill = tk.BOTH, pady = (20, 0))
        stage2_label.pack(side = tk.LEFT, padx = 20)
        stage2stat_label.pack(side = tk.RIGHT, padx = 20)

        bottom_label = ttk.Label(root, text = "WARNING: Turning off power or attempting to shutdown "
                                  "the computer while the\ndecryption process is running can lead to "
                                  "irrecoverable data loss and may prevent\nthe system from booting. "
                                  "Please make sure that the computer doesn\'t lose power.\n"
                                  "Additionally, do not disconnect any storage devices until the "
                                  "process is complete.",
                                  foreground = "red")
        bottom_label.pack(side = tk.BOTTOM, pady = 30, padx = 20)

        root.update()
        root.after(1000)

    else:
        time.sleep(1)

    if (clear_autounlock_keys() == -1):
        if (gui_enabled):
            stage1stat_label.configure(text = "FAILED", foreground = "red")
            stage2stat_label.configure(text = "ABORTED", foreground = "red")
            bottom_label.configure(text = "Your system has not been modified. "
                                   "You may exit this window now.", foreground = "black")

        error: tuple = get_last_error()
        print ("\r[STAGE-1]: Clear automatic unlock keys for data volumes: Failed    \n")
        print ("Reason for failure:\n" + error[1].strip())

        if (gui_enabled):
            mbox.showerror(APPNAME,
                           "Failed to clear automatic unlock keys for data volumes. "
                           "The following information may be useful for error "
                           "diagnosis.\n",
                           detail = error[1].strip())
            root.protocol("WM_DELETE_WINDOW", lambda: root.destroy())

    else:
        print ("\r[STAGE-1]: Clear automatic unlock keys for data volumes: Completed ")
        if (gui_enabled):
            stage1stat_label.configure(text = "SUCCESS", foreground = "green")
            stage2stat_label.configure(text = "RUNNING", foreground = "blue")
            init_decryption(encr_drives.keys())
            stage2_updates(root, stage2stat_label, bottom_label)
        else:
            init_decryption(encr_drives.keys())
            stage2_updates(None, None, None)

    root.mainloop() if gui_enabled else None


if (__name__ == "__main__"):
    main()
