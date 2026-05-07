@echo off
setlocal
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 run.py
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        python run.py
    ) else (
        echo Python was not found. Install the latest stable Python and run: python -m pip install -r requirements.txt
        exit /b 1
    )
)
pause
