@echo off
cd /d "%~dp0"
title GPTC task - stim (8 categories, 36 trials)
python GPTC_task.py %*
echo.
echo ---- finished. press any key to close ----
pause >nul
