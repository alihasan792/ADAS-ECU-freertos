@echo off
rem ADAS ECU Automated Test Harness Windows Wrapper
rem Dispatches commands to Python entrypoint

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 "%~dp0cli\adas_test.py" %*
    exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python "%~dp0cli\adas_test.py" %*
    exit /b %ERRORLEVEL%
)

echo [ERROR] Python was not found in PATH or via 'py' launcher.
exit /b 3
