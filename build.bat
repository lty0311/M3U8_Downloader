chcp 65001
@echo off
SETLOCAL

cd /d "%~dp0%"

if not exist "venv" (
    python -m venv venv
)

call ./venv/Scripts/activate.bat

:: ��� requests ���Ƿ��Ѱ�װ
pip show requests >nul 2>&1
if %ERRORLEVEL%==0 (
    set REQUESTS_INSTALLED=true
) else (
    set REQUESTS_INSTALLED=false
)

:: ��� natsort ���Ƿ��Ѱ�װ
pip show natsort >nul 2>&1
if %ERRORLEVEL%==0 (
    set NATSORT_INSTALLED=true
) else (
    set NATSORT_INSTALLED=false
)

:: �ж��Ƿ���������δ��װ
if "%REQUESTS_INSTALLED%"=="false" if "%NATSORT_INSTALLED%"=="false" (
    pip install -r requirements.txt
)

:: ����Ƿ�װ��PyInstaller
pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo "���ڰ�װPyInstaller..."
    pip install pyinstaller
)

:: �������
pyinstaller --onefile --windowed ^
    --icon=favicon.ico ^
    --add-data "config.ini;." ^
    --add-data "favicon.ico;." ^
    --add-data "ffmpeg/ffmpeg.exe;ffmpeg" ^
    --distpath buildDist ^
    --workpath build ^
    --name M3U8_Downloader ^
    m3u8_downloader.py

:: ���Ʊ�Ҫ�ļ���distĿ¼
xcopy /Y config.ini buildDist\
xcopy /E /I /Y ffmpeg buildDist\ffmpeg\
xcopy /E /I /Y downloads buildDist\downloads\

echo "������! ������ buildDist Ŀ¼��"
