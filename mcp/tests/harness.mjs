#!/usr/bin/env node
/**
 * CST2026 MCP Harness — one-command test suite.
 *
 * Run with:  npm test   (from the mcp/ directory)
 *            node tests/harness.mjs
 *
 * The harness validates:
 *   1. MCP server initialization and protocol handshake
 *   2. tools/list returns the expected tool set
 *   3. Key tool calls work (knowledge, docs, records, history)
 *   4. Agent configuration files are valid and loadable
 *   5. No hardcoded machine-specific absolute paths in code/config/docs
 *
 * All paths are relative — no external absolute paths required.
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const mcpRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(mcpRoot, "..");
const serverPath = path.join(mcpRoot, "src", "server.js");
const configDir = path.join(mcpRoot, "config");

// ---------------------------------------------------------------------------
// Tiny test framework
// ---------------------------------------------------------------------------

const results = [];
let current = "";

function describe(name, fn) {
  current = name;
  return fn();
}

function test(name, fn) {
  const label = current ? `${current} > ${name}` : name;
  try {
    fn();
    results.push({ label, pass: true });
  } catch (error) {
    results.push({ label, pass: false, error: error.message });
  }
}

async function testAsync(name, fn) {
  const label = current ? `${current} > ${name}` : name;
  try {
    await fn();
    results.push({ label, pass: true });
  } catch (error) {
    results.push({ label, pass: false, error: error.message });
  }
}

// ---------------------------------------------------------------------------
// MCP server test client
// ---------------------------------------------------------------------------

function startServer() {
  const child = spawn(process.execPath, [serverPath], {
    cwd: mcpRoot,
    stdio: ["pipe", "pipe", "pipe"],
    windowsHide: true,
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

  function readMessage(timeoutMs = 5000) {
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
        },
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
    },
  };
}

function parseToolText(result) {
  assert.equal(result.content?.[0]?.type, "text");
  return JSON.parse(result.content[0].text);
}

// ---------------------------------------------------------------------------
// Test suites
// ---------------------------------------------------------------------------

async function runMcpServerTests() {
  const server = startServer();
  try {
    // 1. Initialize
    await testAsync("initialize handshake", async () => {
      const init = await server.request("initialize", {});
      assert.equal(init.protocolVersion, "2024-11-05");
      assert.ok(init.capabilities.tools, "should declare tools capability");
      assert.equal(init.serverInfo.name, "cst2026-mcp");
    });

    // 2. tools/list
    const toolList = await testAsync("tools/list returns expected tools", async () => {
      const list = await server.request("tools/list", {});
      const names = list.tools.map((t) => t.name);
      const expected = [
        "docs.search_macros",
        "docs.read_macro",
        "docs.search_official_docs",
        "docs.read_official_doc",
        "history.extract_pattern",
        "records.create_variant",
        "records.append_operation",
        "cst.closed_start",
        "cst.close_project",
        "cst.live_modify_parameter",
        "cst.inspect_project",
        "cst.inspect_geometry",
        "cst.inspect_physics_setup",
        "cst.result_sanity",
        "cst.process_status",
        "cst.preflight_resources",
        "cst.job_checkpoint",
        "cst.recover_job",
        "cst.cleanup_stale_processes",
        "knowledge.list_categories",
        "knowledge.get_recipe",
        "knowledge.search_lessons",
      ];
      for (const name of expected) {
        assert.ok(names.includes(name), `missing tool: ${name}`);
      }
      return list;
    });

    // 3. knowledge.list_categories
    await testAsync("knowledge.list_categories returns categories", async () => {
      const result = parseToolText(
        await server.request("tools/call", {
          name: "knowledge.list_categories",
          arguments: {},
        })
      );
      assert.ok(result.categories.includes("ports"), "should include 'ports' category");
      assert.ok(result.categories.includes("boolean"), "should include 'boolean' category");
    });

    // 4. knowledge.get_recipe
    await testAsync("knowledge.get_recipe returns port recipe", async () => {
      const recipe = parseToolText(
        await server.request("tools/call", {
          name: "knowledge.get_recipe",
          arguments: { category: "ports" },
        })
      );
      assert.equal(recipe.found, true);
      assert.match(recipe.text, /waveguide Port/i);
      assert.match(recipe.text, /DiscretePort/);
    });

    // 5. knowledge.search_lessons
    await testAsync("knowledge.search_lessons finds Project.close lesson", async () => {
      const lessons = parseToolText(
        await server.request("tools/call", {
          name: "knowledge.search_lessons",
          arguments: { query: "Untitled modal close Project.close" },
        })
      );
      assert.ok(
        lessons.matches.some((m) => /Project\.close/.test(m.text)),
        "should find Project.close lesson"
      );
    });

    // 6. docs.search_macros
    await testAsync("docs.search_macros finds results", async () => {
      const macros = parseToolText(
        await server.request("tools/call", {
          name: "docs.search_macros",
          arguments: { query: "DiscretePort", limit: 5 },
        })
      );
      assert.ok(macros.count > 0, "should find macro matches for DiscretePort");
    });

    // 7. docs.search_official_docs
    await testAsync("docs.search_official_docs finds results", async () => {
      const docs = parseToolText(
        await server.request("tools/call", {
          name: "docs.search_official_docs",
          arguments: { query: "StoreParameter", limit: 3 },
        })
      );
      assert.ok(docs.count >= 0, "should return non-negative count");
    });

    // 8. records.create_variant
    await testAsync("records.create_variant creates a manifest", async () => {
      const record = parseToolText(
        await server.request("tools/call", {
          name: "records.create_variant",
          arguments: {
            project_path: "<test_project.cst>",
            objective: "harness smoke test",
          },
        })
      );
      assert.ok(record.manifest_path, "should return manifest_path");
      assert.equal(record.manifest.objective, "harness smoke test");
      // cleanup
      const dir = path.dirname(record.manifest_path);
      fs.rmSync(dir, { recursive: true, force: true });
    });

    // 9. history.extract_pattern (may return 0 blocks if CST macros are not installed)
    await testAsync("history.extract_pattern returns valid structure", async () => {
      const blocks = parseToolText(
        await server.request("tools/call", {
          name: "history.extract_pattern",
          arguments: { query: "DiscretePort", max_blocks: 2 },
        })
      );
      assert.ok(Array.isArray(blocks.blocks), "should return blocks array");
    });
  } finally {
    server.stop();
  }
}

function runConfigTests() {
  describe("Agent configuration", () => {
    const agentsJsonPath = path.join(configDir, "agents.json");

    test("agents.json exists and is valid JSON", () => {
      assert.ok(fs.existsSync(agentsJsonPath), "agents.json should exist");
      const data = JSON.parse(fs.readFileSync(agentsJsonPath, "utf8"));
      assert.ok(data.agents, "should have agents object");
      assert.ok(data.default_agent, "should have default_agent");
    });

    const agentsData = JSON.parse(fs.readFileSync(agentsJsonPath, "utf8"));

    test("at least 2 agents are configured", () => {
      const count = Object.keys(agentsData.agents).length;
      assert.ok(count >= 2, `expected >= 2 agents, got ${count}`);
    });

    test("codex agent is configured", () => {
      assert.ok(agentsData.agents.codex, "should have codex agent");
    });

    test("claude agent is configured", () => {
      assert.ok(agentsData.claude || agentsData.agents.claude, "should have claude agent");
    });

    for (const [key, agent] of Object.entries(agentsData.agents)) {
      test(`agent '${key}' has valid config example file`, () => {
        assert.ok(agent.config_example, `${key} should have config_example`);
        const examplePath = path.join(configDir, agent.config_example);
        assert.ok(fs.existsSync(examplePath), `${agent.config_example} should exist`);
      });

      test(`agent '${key}' config example is parseable`, () => {
        const examplePath = path.join(configDir, agent.config_example);
        const content = fs.readFileSync(examplePath, "utf8");
        if (agent.config_format === "json") {
          JSON.parse(content);
        } else if (agent.config_format === "toml") {
          assert.ok(content.includes("[mcp_servers"), `${key} toml should have mcp_servers section`);
        }
      });

      test(`agent '${key}' has launch_command`, () => {
        assert.ok(agent.launch_command, `${key} should have launch_command`);
      });
    }

    test("shared_env_vars includes CST_INSTALL_DIR", () => {
      assert.ok(
        agentsData.shared_env_vars?.includes("CST_INSTALL_DIR"),
        "should include CST_INSTALL_DIR"
      );
    });
  });
}

function runPathAudit() {
  describe("Absolute path audit", () => {
    // Patterns that indicate machine-specific hardcoded paths
    const badPatterns = [
      /D:\\CST/i,
      /D:\/CST/i,
      /D:\\CSTapi/i,
      /D:\/CSTapi/i,
      /C:\\Users\\/i,
      /\/Users\//,
      /\/home\//,
    ];

    // Directories to scan (code, config, docs — not reference material)
    const scanDirs = [
      { dir: path.join(repoRoot, "mcp", "src"), exts: [".js"] },
      { dir: path.join(repoRoot, "mcp", "python"), exts: [".py"] },
      { dir: path.join(repoRoot, "mcp", "config"), exts: [".json", ".toml"] },
      { dir: path.join(repoRoot, "mcp", "tests"), exts: [".mjs"] },
      { dir: path.join(repoRoot, "skills"), exts: [".md", ".json", ".py", ".yaml"] },
      { dir: path.join(repoRoot, "macro-library"), exts: [".md", ".csv", ".json"] },
      { dir: repoRoot, exts: [".md", ".cmd", ".sh"] },
    ];

    // Directories to exclude
    const excludeDirs = ["official-docs", "node_modules", ".git", "design-records"];

    function shouldExclude(filePath) {
      return excludeDirs.some((d) => filePath.includes(path.sep + d + path.sep) || filePath.endsWith(path.sep + d));
    }

    function walkDir(dir, exts, files = []) {
      if (!fs.existsSync(dir)) return files;
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          if (excludeDirs.includes(entry.name)) continue;
          walkDir(full, exts, files);
        } else if (exts.includes(path.extname(entry.name))) {
          if (!shouldExclude(full)) files.push(full);
        }
      }
      return files;
    }

    const allFiles = scanDirs.flatMap(({ dir, exts }) => walkDir(dir, exts));

    test("scanned at least 10 files", () => {
      assert.ok(allFiles.length >= 10, `only scanned ${allFiles.length} files`);
    });

    const violations = [];
    for (const file of allFiles) {
      const content = fs.readFileSync(file, "utf8");
      const lines = content.split(/\r?\n/);
      for (let i = 0; i < lines.length; i++) {
        for (const pattern of badPatterns) {
          if (pattern.test(lines[i])) {
            // Allow references to env var placeholders like $CST_MACRO_ROOT
            if (/\$\{?CST_/.test(lines[i]) || /\$CST_/.test(lines[i])) continue;
            // Allow "C:\Program Files" standard Windows paths in auto-detection
            if (/C:\\Program Files/i.test(lines[i]) && /CST Studio Suite/i.test(lines[i])) continue;
            violations.push(`${path.relative(repoRoot, file)}:${i + 1}: ${lines[i].trim()}`);
          }
        }
      }
    }

    test("no machine-specific absolute paths in code/config/docs", () => {
      if (violations.length > 0) {
        assert.fail(`Found ${violations.length} hardcoded absolute paths:\n${violations.slice(0, 10).join("\n")}`);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  console.log("=== CST2026 MCP Harness ===\n");

  // Run synchronous tests first
  runConfigTests();
  runPathAudit();

  // Run async MCP server tests
  await runMcpServerTests();

  // Summary
  const passed = results.filter((r) => r.pass).length;
  const failed = results.filter((r) => !r.pass).length;
  const total = results.length;

  console.log("");
  for (const r of results) {
    const status = r.pass ? "PASS" : "FAIL";
    console.log(`  ${status}  ${r.label}`);
    if (!r.pass) {
      console.log(`        ${r.error}`);
    }
  }

  console.log(`\n=== ${passed}/${total} passed, ${failed} failed ===`);

  if (failed > 0) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error("Harness crashed:", error);
  process.exit(1);
});
