@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" goto run
echo Setting up Bichaek PDF. Internet is needed only for this first setup.
py -3.12 -c "import sys; assert sys.version_info[:2] == (3,12)" >nul 2>&1
if errorlevel 1 goto nopython
py -3.12 -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
:run
".venv\Scripts\python.exe" -c "import PySide6, pymupdf" >nul 2>&1
if errorlevel 1 goto failed
start "Bichaek PDF" ".venv\Scripts\pythonw.exe" main.py %*
exit /b 0
:nopython
echo.
echo Python 3.12 is required for this source preview.
echo Install Python 3.12 from https://www.python.org/downloads/windows/
echo Include the Python launcher, then run this file again.
echo A prebuilt EXE is not included in this source package.
pause
exit /b 1
:failed
echo.
echo Setup failed. Remove the .venv folder and retry, or read README.md.
pause
exit /b 1
