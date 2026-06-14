@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=%USERPROFILE%\anaconda3\envs\smartled\python.exe"
set "BACKEND_URL=http://127.0.0.1:5000"
set "FRONTEND_URL=http://127.0.0.1:5173"
set "NPM=%ProgramFiles%\nodejs\npm.cmd"

if not exist "%PYTHON%" (
  echo Python not found: %PYTHON%
  echo Please update PYTHON in start_smartlamp.cmd.
  pause
  exit /b 1
)

if not exist "%NPM%" (
  echo npm not found: %NPM%
  echo Please install Node.js or update NPM in start_smartlamp.cmd.
  pause
  exit /b 1
)

echo Starting StudyPilot backend...
start "StudyPilot Backend" cmd /k "cd /d ""%ROOT%"" && ""%PYTHON%"" backend\run_local.py"

echo Waiting for backend...
timeout /t 4 /nobreak > nul

if not exist "%ROOT%frontend\node_modules" (
  echo Installing frontend dependencies...
  pushd "%ROOT%frontend"
  "%NPM%" install --cache .\.npm-cache
  if errorlevel 1 (
    echo Frontend dependency installation failed.
    pause
    exit /b 1
  )
  popd
)

echo Starting Vue frontend...
start "StudyPilot Frontend" cmd /k ""%ROOT%run_frontend.cmd""

echo Starting YOLO vision worker...
start "StudyPilot Vision Worker" cmd /k "call ""%ROOT%run_vision.cmd"" %*"

echo Opening dashboard...
timeout /t 2 /nobreak > nul
start "" "%FRONTEND_URL%"

echo Done. Keep backend, frontend, and vision worker windows open while testing.
endlocal
