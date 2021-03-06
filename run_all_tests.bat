@echo off
REM Run all known tests using the IOC Testing Framework

SET CurrentDir=%~dp0

call "%~dp0..\..\..\config_env.bat"

set "PYTHONUNBUFFERED=1"

call %PYTHON3% "%EPICS_KIT_ROOT%\support\IocTestFramework\master\run_tests.py" %*
IF %ERRORLEVEL% NEQ 0 EXIT /b %errorlevel%
