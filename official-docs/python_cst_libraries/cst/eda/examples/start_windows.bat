echo off

set cstinst=%~dp0..\..\..\..\..

set PATH=%cstinst%\AMD64;%PATH%
set PYTHONPATH=%cstinst%\AMD64\python_cst_libraries
cd /D "%~dp0"
"%cstinst%\AMD64\python\python" example_starter.py
pause
