@echo off
echo 开始构建专注时钟应用...

REM 检查Python是否已安装
python --version 2>NUL
if errorlevel 1 (
    echo 错误: 未检测到Python，请安装Python 3.6或更高版本
    pause
    exit /b 1
)

REM 安装所需依赖
echo 安装依赖...
pip install -r requirements.txt

REM 运行打包脚本
echo 开始打包应用...
python build.py

if exist dist\专注时钟.exe (
    echo.
    echo 构建成功! 可执行文件位于 dist\专注时钟.exe
    echo.
    echo 是否要立即运行应用? (Y/N)
    set /p run=
    if /i "%run%"=="Y" (
        start dist\专注时钟.exe
    )
) else (
    echo 构建过程似乎出现问题，请检查错误信息
)

pause 