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

# 检查声音文件是否存在，不存在则报错
sound_files = [
    ("sounds/ding.mp3", "Missing notification sound file"),
    ("sounds/break.mp3", "Missing break notification sound file"),
]

missing_files = False
for sound_file, error_msg in sound_files:
    if not os.path.exists(sound_file):
        print(f"ERROR: {error_msg} {sound_file}")
        missing_files = True

# 检查图标文件是否存在
icon_file_ico = "icons/clock.ico"
icon_file_png = "icons/clock.png"

# 优先使用 .ico 文件作为应用图标
if os.path.exists(icon_file_ico):
    print(f"Using icon file: {icon_file_ico}")
    icon_file = icon_file_ico
elif os.path.exists(icon_file_png):
    print(f"Using icon file: {icon_file_png} (PNG format)")
    # PyInstaller 在 Windows 上打包时最好使用 .ico 格式
    # 但如果没有 .ico 文件，也可以尝试使用 .png
    icon_file = icon_file_png
else:
    print(f"ERROR: Missing icon file. Need either {icon_file_ico} or {icon_file_png}")
    missing_files = True

if missing_files:
    print("\n资源文件缺失！请确保以下文件存在：")
    print("- sounds/ding.mp3")
    print("- sounds/break.mp3")
    print("- icons/clock.png 或 icons/clock.ico")
    sys.exit(1)

# Use Windows optimized version of the script
main_script = "pomodoro_timer_windows.py"
if not os.path.exists(main_script):
    print(f"Error: Main script file {main_script} not found")
    sys.exit(1)

# Determine the correct separator for --add-data based on the platform
separator = ';' if sys.platform.startswith('win') else ':'

# 打印当前目录结构，便于调试
print("\n当前工作目录结构:")
print(f"工作目录: {os.getcwd()}")
print("sounds/ 目录内容:")
if os.path.exists("sounds"):
    print(os.listdir("sounds"))
print("icons/ 目录内容:")
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

# 如果有 .ico 文件，添加图标参数
if os.path.exists(icon_file_ico):
    args.append(f'--icon={icon_file_ico}')
elif os.path.exists(icon_file_png):
    args.append(f'--icon={icon_file_png}')

# Run PyInstaller packaging
print("\nStarting PyInstaller packaging process...")
print(f"Command arguments: {args}")
PyInstaller.__main__.run(args)

print("\nPackaging complete! Executable file is located at dist/FocusTimer.exe") 