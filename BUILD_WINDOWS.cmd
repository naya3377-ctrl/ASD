@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .build-venv
if errorlevel 1 goto failed
".build-venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller==6.16.0
if errorlevel 1 goto failed
".build-venv\Scripts\python.exe" -m unittest tests.test_document -v
if errorlevel 1 goto failed
".build-venv\Scripts\python.exe" -m PyInstaller --noconfirm YoonDF.spec
if errorlevel 1 goto failed
echo.
echo Build complete: dist\YoonDF\YoonDF.exe
echo Keep the entire dist\YoonDF folder together.
echo To make an installer, compile packaging\windows.iss with Inno Setup 6.
pause
exit /b 0
:failed
echo Build failed. Review the error above.
pause
exit /b 1
