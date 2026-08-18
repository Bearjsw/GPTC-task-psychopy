@echo off
cd /d "%~dp0web"
title GPTC web - 0818 list (21 categories, 42 trials)
start "" /b cmd /c "timeout /t 2 > NUL & start "" http://127.0.0.1:8732/GPTC_task_0818.html"
echo.
echo Serving http://127.0.0.1:8732/GPTC_task_0818.html
echo Close this window to stop the server.
echo.
python -m http.server 8732 --bind 127.0.0.1
