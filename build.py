import os
import sys
import shutil
from distutils.core import setup
import PyInstaller.__main__

print("开始打包专注时钟应用...")

# 确保必要的文件夹存在
for folder in ["sounds", "icons"]:
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"创建 {folder} 文件夹")

# 检查声音文件是否存在
sound_files = [
    ("sounds/ding.wav", "缺少提示音文件"),
    ("sounds/break.wav", "缺少休息提示音文件"),
]

for sound_file, error_msg in sound_files:
    if not os.path.exists(sound_file):
        print(f"警告: {error_msg} {sound_file}")
        print("将创建简单的默认声音文件...")
        # 创建空白的WAV文件，实际项目中应替换为真实的声音文件
        with open(sound_file, 'w') as f:
            f.write("PLACEHOLDER_FOR_SOUND_FILE")

# 检查图标文件是否存在
icon_file = "icons/clock.ico"
if not os.path.exists(icon_file):
    print(f"警告: 缺少图标文件 {icon_file}")
    print("将使用默认图标...")
    # 实际项目中应替换为真实的图标文件
    with open(icon_file.replace(".ico", ".png"), 'w') as f:
        f.write("PLACEHOLDER_FOR_ICON_FILE")

# 使用Windows优化版本的脚本
main_script = "pomodoro_timer_windows.py"
if not os.path.exists(main_script):
    print(f"错误: 找不到主脚本文件 {main_script}")
    sys.exit(1)

# 运行PyInstaller打包
print("开始PyInstaller打包过程...")
PyInstaller.__main__.run([
    main_script,
    '--name=专注时钟',
    '--onefile',
    '--windowed',
    '--add-data=sounds;sounds',
    '--add-data=icons;icons',
    f'--icon={icon_file}' if os.path.exists(icon_file) else '',
])

print("打包完成! 可执行文件位于 dist/专注时钟.exe") 