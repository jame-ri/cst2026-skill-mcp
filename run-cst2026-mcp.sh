#!/usr/bin/env sh
# Cross-platform CST2026 MCP server launcher (macOS / Linux)
# Node.js must be on PATH or pointed to by NODE_PATH.
# Agent-agnostic: works with Codex, Claude, Cursor, or any MCP client.

NODE_EXE="${NODE_PATH:-node}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

exec "$NODE_EXE" "$SCRIPT_DIR/mcp/src/server.js"
