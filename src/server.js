#!/usr/bin/env node

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const SERVER_NAME = "cst2026";
const SERVER_VERSION = "0.1.0";
const PROTOCOL_VERSION = "2024-11-05";
const DEFAULT_CST_ROOT = "D:\\CST";

const tools = [
  {
    name: "cst2026_ping",
    description: "Check whether the CST2026 MCP server is running.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false
    }
  },
  {
    name: "cst2026_project_info",
    description: "Return basic information about the CST2026 MCP server.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false
    }
  },
  {
    name: "cst2026_cst_info",
    description: "Inspect the local CST Studio Suite installation configured for this computer.",
    inputSchema: {
      type: "object",
      properties: {
        cstRoot: {
          type: "string",
          description: "Optional CST installation root. Defaults to D:\\CST."
        }
      },
      additionalProperties: false
    }
  },
  {
    name: "cst2026_echo",
    description: "Echo a message to verify MCP tool calls.",
    inputSchema: {
      type: "object",
      properties: {
        message: {
          type: "string",
          description: "Message to echo."
        }
      },
      required: ["message"],
      additionalProperties: false
    }
  }
];

let inputBuffer = "";

process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  inputBuffer += chunk;
  processInputBuffer();
});

process.stdin.on("end", () => {
  process.exit(0);
});

function processInputBuffer() {
  while (true) {
    const separatorIndex = inputBuffer.indexOf("\r\n\r\n");
    if (separatorIndex === -1) {
      return;
    }

    const headerBlock = inputBuffer.slice(0, separatorIndex);
    const contentLength = getContentLength(headerBlock);

    if (contentLength === null) {
      inputBuffer = inputBuffer.slice(separatorIndex + 4);
      continue;
    }

    const messageStart = separatorIndex + 4;
    const messageEnd = messageStart + contentLength;

    if (inputBuffer.length < messageEnd) {
      return;
    }

    const payload = inputBuffer.slice(messageStart, messageEnd);
    inputBuffer = inputBuffer.slice(messageEnd);
    handlePayload(payload);
  }
}

function getContentLength(headerBlock) {
  for (const line of headerBlock.split("\r\n")) {
    const [rawName, rawValue] = line.split(":");
    if (rawName?.toLowerCase() === "content-length") {
      const parsed = Number.parseInt(rawValue.trim(), 10);
      return Number.isFinite(parsed) ? parsed : null;
    }
  }

  return null;
}

function handlePayload(payload) {
  let request;

  try {
    request = JSON.parse(payload);
  } catch (error) {
    sendError(null, -32700, "Parse error", error.message);
    return;
  }

  if (request.id === undefined) {
    return;
  }

  try {
    sendResponse(request.id, routeRequest(request));
  } catch (error) {
    sendError(request.id, error.code ?? -32603, error.message, error.data);
  }
}

function routeRequest(request) {
  switch (request.method) {
    case "initialize":
      return {
        protocolVersion: PROTOCOL_VERSION,
        capabilities: {
          tools: {}
        },
        serverInfo: {
          name: SERVER_NAME,
          version: SERVER_VERSION
        }
      };

    case "tools/list":
      return {
        tools
      };

    case "tools/call":
      return callTool(request.params ?? {});

    default:
      throw jsonRpcError(-32601, `Method not found: ${request.method}`);
  }
}

function callTool(params) {
  const args = params.arguments ?? {};

  switch (params.name) {
    case "cst2026_ping":
      return textResult("cst2026 MCP is running.");

    case "cst2026_project_info":
      return textResult(
        JSON.stringify(
          {
            name: SERVER_NAME,
            version: SERVER_VERSION,
            cwd: process.cwd(),
            node: process.version
          },
          null,
          2
        )
      );

    case "cst2026_cst_info":
      return textResult(JSON.stringify(getCstInfo(args.cstRoot), null, 2));

    case "cst2026_echo":
      if (typeof args.message !== "string") {
        throw jsonRpcError(-32602, "Invalid params: message must be a string.");
      }

      return textResult(args.message);

    default:
      throw jsonRpcError(-32602, `Unknown tool: ${params.name}`);
  }
}

function getCstInfo(cstRoot = DEFAULT_CST_ROOT) {
  if (typeof cstRoot !== "string" || cstRoot.trim() === "") {
    throw jsonRpcError(-32602, "Invalid params: cstRoot must be a non-empty string.");
  }

  const root = cstRoot.trim();
  const executable = join(root, "CST DESIGN ENVIRONMENT.exe");
  const imageVersionPath = join(root, "Image_Version");
  const patchVersionPath = join(root, "Patch_Version");
  const licensePath = join(root, "license.dat");

  return {
    cstRoot: root,
    installed: existsSync(root),
    executable,
    executableExists: existsSync(executable),
    imageVersion: readSmallTextFile(imageVersionPath),
    patchVersion: readSmallTextFile(patchVersionPath),
    licenseFileExists: existsSync(licensePath)
  };
}

function readSmallTextFile(path) {
  if (!existsSync(path)) {
    return null;
  }

  return readFileSync(path, "utf8").trim();
}

function textResult(text) {
  return {
    content: [
      {
        type: "text",
        text
      }
    ]
  };
}

function sendResponse(id, result) {
  sendMessage({
    jsonrpc: "2.0",
    id,
    result
  });
}

function sendError(id, code, message, data) {
  sendMessage({
    jsonrpc: "2.0",
    id,
    error: {
      code,
      message,
      ...(data === undefined ? {} : { data })
    }
  });
}

function sendMessage(message) {
  const payload = JSON.stringify(message);
  const byteLength = Buffer.byteLength(payload, "utf8");
  process.stdout.write(`Content-Length: ${byteLength}\r\n\r\n${payload}`);
}

function jsonRpcError(code, message, data) {
  const error = new Error(message);
  error.code = code;
  error.data = data;
  return error;
}
