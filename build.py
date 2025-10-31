import os
import sys
import shutil
import PyInstaller.__main__ as pim
import subprocess as sp


def is_on_path(exe_name) -> bool:
    for folder in os.environ["PATH"].split(";"):
        if (os.path.isdir(folder) and
            exe_name in os.listdir(folder)):
            return True
    return False 


def cleanup(build_failed = False) -> None:
    if (os.path.isdir("build")):
        shutil.rmtree("build")
    if (os.path.isdir("dist")):
        if (build_failed):
            shutil.rmtree("dist")
        else:
            os.rename("dist", "build")
            shutil.copy2("build/bloff-gui/bloff-gui.exe",
                         "build/bloff/bloff-gui.exe")
            shutil.rmtree("build/bloff-gui")
    for file in os.listdir():
        if (file.endswith(".spec")):
            os.remove(file)


def main() -> None:
    print ("Checking Python is on PATH...  ", end = "", flush = True)
    if (not is_on_path("python.exe")):
        print ("NO")
        print ("ERROR: Build cannot proceed. Please add Python to PATH.")
        sys.exit(1)
    print ("YES")

    print ("Checking Python >= 3.12...  ", end = "", flush = True)
    pyver: tuple = sys.version_info[0: 3]
    if (pyver[0] < 3 or pyver[1] < 12):
        print ("NO")
        print ("ERROR: Build cannot proceed. Please upgrade your Python to >= 3.12.")
        sys.exit(1)
    print ("YES")

    print ("Checking Pyinstaller is on PATH...  ", end = "", flush = True)
    if (not is_on_path("pyinstaller.exe")):
        print ("NO")
        print ("ERROR: Build cannot proceed. Please add pyinstaller to PATH.")
        sys.exit(1)
    print ("YES")

    print ("Checking if build script running from source root...  ", end = "", flush = True)
    if (os.getcwd() != os.path.dirname(__file__)):
        print ("NO")
        print ("ERROR: Build cannot proceed. Please run the build script from source root.")
        sys.exit(1)
    print ("YES")

    print ("Removing previous builds...  ", end = "", flush = "")
    if (os.path.isdir("build")):
        shutil.rmtree("build")
        print ("DONE")
    else:
        print ("SKIPPED")

    print ("\nRunning build...")

    print ("Building the CLI...")
    try:
        pim.run(["bloff.py", "--icon=bloff.ico", "--version-file=bloff_vinfo.txt",
                 "--name=bloff", "--noconfirm"])
    except SystemExit as exp:
        print ("ERROR: Build failed. See above for reasons.")
        print ("Cleaning up...  ", end = "", flush = True)
        cleanup(build_failed = True)
        print ("DONE")
        sys.exit(1)

    print ("\nBuilding the GUI...")
    try:
        pim.run(["bloff.py", "--icon=bloff.ico", "--version-file=bloff-gui_vinfo.txt",
                 "--name=bloff-gui", "--noconfirm", "--windowed"])
    except SystemExit as exp:
        print ("ERROR: Build failed. See above for reasons.")
        print ("Cleaning up...  ", end = "", flush = True)
        cleanup(build_failed = True)
        print ("DONE")
        sys.exit(1)

    print ("Cleaning up...  ", end = "", flush = True)
    cleanup()
    print ("DONE")
    print ("\nFinished build successfully. Final build is available at: "
           f"{os.path.dirname(__file__)}\\build")


if (__name__ == "__main__"):
    main()
