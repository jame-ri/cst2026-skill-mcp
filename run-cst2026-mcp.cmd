@echo off
setlocal
if not defined CST_NODE_EXE set "CST_NODE_EXE=node"
pushd "%~dp0" || exit /b 1
"%CST_NODE_EXE%" "mcp\src\server.js"
set "CST_MCP_EXIT=%ERRORLEVEL%"
popd
exit /b %CST_MCP_EXIT%
