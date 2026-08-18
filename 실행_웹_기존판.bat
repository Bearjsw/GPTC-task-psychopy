@echo off
cd /d "%~dp0web"
title GPTC web - classic (8 categories, 42 trials)
start "" /b cmd /c "timeout /t 2 > NUL & start "" http://127.0.0.1:8731/GPTC_task.html"
echo.
echo Serving http://127.0.0.1:8731/GPTC_task.html
echo Close this window to stop the server.
echo.
python -m http.server 8731 --bind 127.0.0.1
