@echo off
setlocal

echo ==========================================
echo   DesFlyer Email Automation - EXE Build
echo ==========================================

echo.
echo [1/4] Creating/updating virtual environment...
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat

python -m pip install --upgrade pip
python -m pip install -r requirements-desktop.txt

if errorlevel 1 (
  echo.
  echo Dependency installation failed. Check your Internet connection.
  exit /b 1
)

echo.
echo [2/4] Running compile check...
python -m compileall -q .
if errorlevel 1 exit /b 1

echo.
echo [3/4] Building Windows executable...
python -m PyInstaller --clean --noconfirm DesFlyer.spec
if errorlevel 1 exit /b 1

echo.
echo [4/4] Build complete.
echo EXE: dist\DesFlyer-Email-Automation.exe
echo.
echo IMPORTANT: Configure SMTP sender settings in the application before sending.
echo For real campaigns, set CAMPAIGN_UNSUBSCRIBE_BASE_URL to a public HTTPS URL.
endlocal
