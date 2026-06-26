import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const mcpRoot = path.resolve(__dirname, "..");
const serverPath = path.join(mcpRoot, "src", "server.js");

function startServer() {
  const child = spawn(process.execPath, [serverPath], {
    cwd: mcpRoot,
    stdio: ["pipe", "pipe", "pipe"],
    windowsHide: true
  });

  let stdout = "";
  let stderr = "";
  const waiters = [];

  child.stdout.on("data", (chunk) => {
    stdout += chunk.toString("utf8");
    flushWaiters();
  });
  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString("utf8");
  });

  function flushWaiters() {
    while (waiters.length > 0) {
      const newline = stdout.indexOf("\n");
      if (newline < 0) return;
      const line = stdout.slice(0, newline);
      stdout = stdout.slice(newline + 1);
      waiters.shift().resolve(JSON.parse(line));
    }
  }

  function readMessage(timeoutMs = 3000) {
    return new Promise((resolve, reject) => {
      const newline = stdout.indexOf("\n");
      if (newline >= 0) {
        const line = stdout.slice(0, newline);
        stdout = stdout.slice(newline + 1);
        resolve(JSON.parse(line));
        return;
      }
      const timer = setTimeout(() => {
        reject(new Error(`Timed out waiting for MCP response. stderr=${stderr}`));
      }, timeoutMs);
      waiters.push({
        resolve: (value) => {
          clearTimeout(timer);
          resolve(value);
        }
      });
    });
  }

  async function request(method, params = {}) {
    const id = request.nextId++;
    child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id, method, params })}\n`);
    const message = await readMessage();
    assert.equal(message.id, id);
    assert.equal(message.error, undefined, message.error?.message);
    return message.result;
  }
  request.nextId = 1;

  return {
    request,
    stop: () => {
      child.stdin.end();
      child.kill();
    }
  };
}

function parseToolText(result) {
  assert.equal(result.content?.[0]?.type, "text");
  return JSON.parse(result.content[0].text);
}

const server = startServer();
try {
  const list = await server.request("tools/list");
  const names = list.tools.map((tool) => tool.name);
  assert(names.includes("knowledge.list_categories"));
  assert(names.includes("knowledge.get_recipe"));
  assert(names.includes("knowledge.search_lessons"));

  const categories = parseToolText(
    await server.request("tools/call", {
      name: "knowledge.list_categories",
      arguments: {}
    })
  );
  assert(categories.categories.includes("ports"));
  assert(categories.categories.includes("boolean"));

  const recipe = parseToolText(
    await server.request("tools/call", {
      name: "knowledge.get_recipe",
      arguments: { category: "ports" }
    })
  );
  assert.match(recipe.text, /waveguide Port/i);
  assert.match(recipe.text, /DiscretePort/);

  const lessons = parseToolText(
    await server.request("tools/call", {
      name: "knowledge.search_lessons",
      arguments: { query: "Untitled modal close Project.close" }
    })
  );
  assert(lessons.matches.some((match) => /Project\.close/.test(match.text)));
} finally {
  server.stop();
}
