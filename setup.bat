@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
pushd "%ROOT%"

echo Installing backend dependencies...
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m venv backend\.venv
) else (
  python -m venv backend\.venv
)
if errorlevel 1 (
  echo Failed to create the backend virtual environment.
  popd
  exit /b 1
)

"%ROOT%backend\.venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo Failed to upgrade pip.
  popd
  exit /b 1
)

"%ROOT%backend\.venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
if errorlevel 1 (
  echo Failed to install backend requirements.
  popd
  exit /b 1
)

echo Installing frontend dependencies...
cd /d "%ROOT%frontend"
npm install
if errorlevel 1 (
  echo Failed to install frontend dependencies.
  popd
  exit /b 1
)

popd
echo Setup complete.
endlocal
