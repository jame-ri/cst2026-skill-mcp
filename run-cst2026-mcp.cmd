@echo off
set "NODE_EXE=node"
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" (
  set "NODE_EXE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
)

if not defined CST_INSTALL_DIR (
  if exist "D:\CST\CST DESIGN ENVIRONMENT.exe" set "CST_INSTALL_DIR=D:\CST"
  if not defined CST_INSTALL_DIR if exist "C:\CST\CST DESIGN ENVIRONMENT.exe" set "CST_INSTALL_DIR=C:\CST"
  if not defined CST_INSTALL_DIR if exist "C:\Program Files\CST Studio Suite 2026\CST DESIGN ENVIRONMENT.exe" set "CST_INSTALL_DIR=C:\Program Files\CST Studio Suite 2026"
  if not defined CST_INSTALL_DIR if exist "C:\Program Files\Dassault Systemes\CST Studio Suite 2026\CST DESIGN ENVIRONMENT.exe" set "CST_INSTALL_DIR=C:\Program Files\Dassault Systemes\CST Studio Suite 2026"
  if not defined CST_INSTALL_DIR if exist "C:\Program Files\SIMULIA\CST Studio Suite 2026\CST DESIGN ENVIRONMENT.exe" set "CST_INSTALL_DIR=C:\Program Files\SIMULIA\CST Studio Suite 2026"
)

if defined CST_INSTALL_DIR (
  if not defined CST_PYTHON_EXE if exist "%CST_INSTALL_DIR%\Python\python.exe" set "CST_PYTHON_EXE=%CST_INSTALL_DIR%\Python\python.exe"
  if not defined CST_PYTHON_EXE if exist "%CST_INSTALL_DIR%\AMD64\python.exe" set "CST_PYTHON_EXE=%CST_INSTALL_DIR%\AMD64\python.exe"
  if not defined CST_PYTHON_EXE if exist "%CST_INSTALL_DIR%\AMD64\python\python.exe" set "CST_PYTHON_EXE=%CST_INSTALL_DIR%\AMD64\python\python.exe"
  if not defined CST_MACRO_ROOT if exist "%CST_INSTALL_DIR%\Library\Macros" set "CST_MACRO_ROOT=%CST_INSTALL_DIR%\Library\Macros"
  if not defined CST_DESIGN_ENV_EXE if exist "%CST_INSTALL_DIR%\CST DESIGN ENVIRONMENT.exe" set "CST_DESIGN_ENV_EXE=%CST_INSTALL_DIR%\CST DESIGN ENVIRONMENT.exe"
  if not defined CST_DESIGN_ENV_EXE if exist "%CST_INSTALL_DIR%\AMD64\CST DESIGN ENVIRONMENT_AMD64.exe" set "CST_DESIGN_ENV_EXE=%CST_INSTALL_DIR%\AMD64\CST DESIGN ENVIRONMENT_AMD64.exe"
)

"%NODE_EXE%" "%~dp0mcp\src\server.js"
