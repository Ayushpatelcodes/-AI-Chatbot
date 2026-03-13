@echo off
echo ============================================
echo   BUILDING BADERIA AI EXE (modern_chat_ui2)
echo ============================================

:: Activate virtual environment
call "%~dp0vsdk\Scripts\activate.bat"

:: Clean old builds
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo Building EXE using venv python...

"%~dp0vsdk\Scripts\python.exe" -m PyInstaller ^
 --name "BaderiaAI" ^
 --icon "assets\app_icon.ico" ^
 --windowed ^
 --noconfirm ^
 --clean ^
 --log-level=DEBUG ^
 --add-data "assets;assets" ^
 --add-data "generated;generated" ^
 --add-data "model;model" ^
 --add-data "data;data" ^
 --add-data "history;history" ^
 --add-data "users.json;." ^
 --collect-all customtkinter ^
 --collect-all cv2 ^
 --collect-all sklearn ^
 --hidden-import "requests" ^
 --hidden-import "pkgutil" ^
 --hidden-import "PIL" ^
 --hidden-import "urllib3" ^
 --hidden-import "certifi" ^
 --hidden-import "speech_recognition" ^
 --hidden-import "wikipediaapi" ^
 --hidden-import "google.generativeai" ^
 --hidden-import "flask" ^
 modern_chat_ui2.py

echo.
echo ********** BUILD FINISHED **********
echo Check: dist\BaderiaAI\BaderiaAI.exe
echo.
pause
