@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  py -m venv .venv
  if errorlevel 1 (
    echo Python launcher 'py' was not found. Install Python 3.11+ and retry.
    pause
    exit /b 1
  )
)
echo Installing project dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed. Check your internet connection.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\setup_credentials.py
if errorlevel 1 (
  echo Credentials setup failed.
  pause
  exit /b 1
)
echo.
echo Login URL: http://127.0.0.1:5000/login
echo If the password still fails, ensure that no previous Flask server is running on port 5000.
echo.
".venv\Scripts\python.exe" app.py
pause
