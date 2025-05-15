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

# Check if sound files exist
sound_files = [
    ("sounds/ding.mp3", "Missing notification sound file"),
    ("sounds/break.mp3", "Missing break notification sound file"),
]

for sound_file, error_msg in sound_files:
    if not os.path.exists(sound_file):
        print(f"Warning: {error_msg} {sound_file}")
        print("Creating simple default sound files...")
        # Create empty MP3 files, should be replaced with real sound files in actual project
        with open(sound_file, 'w') as f:
            f.write("PLACEHOLDER_FOR_SOUND_FILE")

# Check if icon file exists
icon_file = "icons/clock.ico"
if not os.path.exists(icon_file):
    print(f"Warning: Missing icon file {icon_file}")
    print("Using default icon...")
    # Should be replaced with real icon in actual project
    with open(icon_file.replace(".ico", ".png"), 'w') as f:
        f.write("PLACEHOLDER_FOR_ICON_FILE")

# Use Windows optimized version of the script
main_script = "pomodoro_timer_windows.py"
if not os.path.exists(main_script):
    print(f"Error: Main script file {main_script} not found")
    sys.exit(1)

# Run PyInstaller packaging
print("Starting PyInstaller packaging process...")
PyInstaller.__main__.run([
    main_script,
    '--name=FocusTimer',
    '--onefile',
    '--windowed',
    '--add-data=sounds;sounds',
    '--add-data=icons;icons',
    f'--icon={icon_file}' if os.path.exists(icon_file) else '',
])

print("Packaging complete! Executable file is located at dist/FocusTimer.exe") 