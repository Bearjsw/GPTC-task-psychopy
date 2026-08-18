@echo off
cd /d "%~dp0"
title GPTC task 0818 - stim_0818 (21 categories, 42 trials)
python GPTC_task_0818.py %*
echo.
echo ---- finished. press any key to close ----
pause >nul
