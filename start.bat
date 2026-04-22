@echo off
cd /d "%~dp0"

echo Starting Backend (FastAPI) on http://127.0.0.1:8000 ...
start "Backend :8000" cmd /k "python main.py"

echo Starting Multilix (Flask) on http://127.0.0.1:5001 ...
start "Multilix :5001" cmd /k "cd modules\multilix && python app_with_model_and_loading.py"

echo Starting Frontend (React) on http://127.0.0.1:5173 ...
start "Frontend :5173" cmd /k "cd frontend && npm run dev"

echo All services started. Press any key to exit this window.
pause >nul
