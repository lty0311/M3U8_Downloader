chcp 65001
@echo off
SETLOCAL

cd /d "%~dp0%"

if not exist "venv" (
    python -m venv venv
)

call ./venv/Scripts/activate.bat

:: 检查 requests 包是否已安装
pip show requests >nul 2>&1
if %ERRORLEVEL%==0 (
    set REQUESTS_INSTALLED=true
) else (
    set REQUESTS_INSTALLED=false
)

:: 检查 natsort 包是否已安装
pip show natsort >nul 2>&1
if %ERRORLEVEL%==0 (
    set NATSORT_INSTALLED=true
) else (
    set NATSORT_INSTALLED=false
)

:: 判断是否两个包都未安装
if "%REQUESTS_INSTALLED%"=="false" if "%NATSORT_INSTALLED%"=="false" (
    pip install -r requirements.txt
)

:: 检查是否安装了PyInstaller
pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo "正在安装PyInstaller..."
    pip install pyinstaller
)

:: 打包程序
pyinstaller --windowed ^
    --icon=favicon.ico ^
    --add-data "config.ini;." ^
    --add-data "favicon.ico;." ^
    --add-data "ffmpeg/ffmpeg.exe;ffmpeg" ^
    --distpath buildDist ^
    --workpath build ^
    --name M3U8_Downloader ^
    m3u8_downloader.py

:: 复制必要文件到dist目录
xcopy /Y config.ini buildDist\
xcopy /E /I /Y ffmpeg buildDist\ffmpeg\
xcopy /E /I /Y downloads buildDist\downloads\

echo "打包完成! 程序在 buildDist 目录中"
