@echo off
setlocal
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 test.py
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        python test.py
    ) else (
        echo Python was not found. Install the latest stable Python first.
        exit /b 1
    )
)
pause
