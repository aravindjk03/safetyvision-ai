@echo off
title SafetyVision AI - REST API Service
echo ===============================================================
echo Starting SafetyVision AI REST API on port 8080...
echo ===============================================================
cd /d "%~dp0"
call ".\venv\Scripts\activate.bat"
start "" "http://127.0.0.1:8080/docs"
python -m uvicorn app.api:app --host 0.0.0.0 --port 8080
pause
