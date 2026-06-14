@echo off
call venv\Scripts\activate
echo Starting Wavly 2.0...
echo Make sure your webcam and microphone are connected.
echo Internet connection required for voice commands.
python main.py
if errorlevel 1 (
    echo Something went wrong. Please re-run install.bat
    pause
)
