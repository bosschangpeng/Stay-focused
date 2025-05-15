import os
import sys
import shutil
from distutils.core import setup
import PyInstaller.__main__

print("Starting to package Focus Timer application...")

# Ensure necessary folders exist
for folder in ["sounds", "icons"]:
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"Created {folder} folder")

# Check if sound files exist, error if missing
sound_files = [
    ("sounds/ding.mp3", "Missing notification sound file"),
    ("sounds/break.mp3", "Missing break notification sound file"),
]

missing_files = False
for sound_file, error_msg in sound_files:
    if not os.path.exists(sound_file):
        print(f"ERROR: {error_msg} {sound_file}")
        missing_files = True

# Check if icon files exist
icon_file_ico = "icons/clock.ico"
icon_file_png = "icons/clock.png"

# Use .ico file as priority for application icon
if os.path.exists(icon_file_ico):
    print(f"Using icon file: {icon_file_ico}")
    icon_file = icon_file_ico
elif os.path.exists(icon_file_png):
    print(f"Using icon file: {icon_file_png} (PNG format)")
    # PyInstaller works better with .ico format on Windows
    # but can also try with .png if no .ico available
    icon_file = icon_file_png
else:
    print(f"ERROR: Missing icon file. Need either {icon_file_ico} or {icon_file_png}")
    missing_files = True

if missing_files:
    print("\nMissing resource files! Please ensure the following files exist:")
    print("- sounds/ding.mp3")
    print("- sounds/break.mp3")
    print("- icons/clock.png or icons/clock.ico")
    sys.exit(1)

# Use Windows optimized version of the script
main_script = "pomodoro_timer_windows.py"
if not os.path.exists(main_script):
    print(f"Error: Main script file {main_script} not found")
    sys.exit(1)

# Determine the correct separator for --add-data based on the platform
separator = ';' if sys.platform.startswith('win') else ':'

# Print current directory structure for debugging
print("\nCurrent working directory structure:")
print(f"Working directory: {os.getcwd()}")
print("sounds/ directory contents:")
if os.path.exists("sounds"):
    print(os.listdir("sounds"))
print("icons/ directory contents:")
if os.path.exists("icons"):
    print(os.listdir("icons"))

# Build command arguments list
args = [
    main_script,
    '--name=FocusTimer',
    '--onefile',
    '--windowed',
    f'--add-data=sounds/ding.mp3{separator}sounds',
    f'--add-data=sounds/break.mp3{separator}sounds',
    f'--add-data=icons/clock.png{separator}icons',
]

# Add icon parameter if .ico file exists
if os.path.exists(icon_file_ico):
    args.append(f'--icon={icon_file_ico}')
elif os.path.exists(icon_file_png):
    args.append(f'--icon={icon_file_png}')

# Run PyInstaller packaging
print("\nStarting PyInstaller packaging process...")
print(f"Command arguments: {args}")
PyInstaller.__main__.run(args)

print("\nPackaging complete! Executable file is located at dist/FocusTimer.exe") 