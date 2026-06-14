@echo off
echo Welcome to Wavly 2.0 Setup

python --version >nul 2>&1
if %errorlevel% neq 0 goto :nopython

python --version 2>&1 | findstr "3.12" >nul
if %errorlevel% neq 0 goto :nopython

goto :haspython

:nopython
echo Python 3.12 is required. Opening download page...
start https://www.python.org/downloads/release/python-31210/
pause
exit /b

:haspython
echo Setting up Wavly... please wait
python -m venv venv
call venv\Scripts\activate
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt

echo Setup complete!

powershell -Command "$wshell = New-Object -ComObject WScript.Shell; $path = (Get-Location).Path; $shortcut = $wshell.CreateShortcut(\"$env:USERPROFILE\Desktop\Wavly 2.0.lnk\"); $shortcut.TargetPath = \"$path\run.bat\"; $shortcut.WorkingDirectory = \"$path\"; $shortcut.IconLocation = \"$path\"; $shortcut.Save()"

echo Wavly 2.0 shortcut created on your Desktop!
echo You can now close this window and launch Wavly from your Desktop.
pause
