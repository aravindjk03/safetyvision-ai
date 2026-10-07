@echo off
title SafetyVision AI - Industrial Safety Inspection Platform
echo ===============================================================
echo Starting SafetyVision AI Dashboard...
echo ===============================================================
cd /d "%~dp0"
call ".\venv\Scripts\activate.bat"
start "" "http://localhost:8501"
streamlit run app/main.py --server.port 8501
pause
