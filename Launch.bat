@echo off
title LuminaDx - Launcher

echo Starting backend...
start "Backend (FastAPI)" /D "%~dp0backend" cmd /k "set "PYTHONPATH=" && set "VIRTUAL_ENV=" && .venv\Scripts\python.exe -m uvicorn main:app --port 8000"

echo Starting frontend...
start "Frontend (Vite)" /D "%~dp0frontend" cmd /k "npm run dev"

echo Waiting for servers to start...
timeout /t 5 /nobreak >nul

start "" "http://localhost:5173"

echo.
echo Both servers are running.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo.
echo Close the Backend and Frontend windows to stop.
pause
