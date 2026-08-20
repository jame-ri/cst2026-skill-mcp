@echo off
REM Cross-platform CST2026 MCP server launcher (Windows)
REM Node.js must be on PATH or pointed to by NODE_EXE.
REM Agent-agnostic: works with Codex, Claude, Cursor, or any MCP client.

set "NODE_EXE=node"
if defined NODE_PATH (
  set "NODE_EXE=%NODE_PATH%"
)

REM Auto-detect common CST 2026 install paths when env vars are unset.
if not defined CST_INSTALL_DIR (
  if exist "C:\Program Files\CST Studio Suite 2026\CST DESIGN ENVIRONMENT.exe" set "CST_INSTALL_DIR=C:\Program Files\CST Studio Suite 2026"
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
