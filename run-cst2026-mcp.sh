#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
exec "${CST_NODE_EXE:-node}" mcp/src/server.js
