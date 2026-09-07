import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { spawn } from "node:child_process";
import { Worker } from "node:worker_threads";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { KnowledgeStore, relativePath } from "../src/knowledge-store.js";

const repo = fileURLToPath(new URL("../../", import.meta.url));
const moduleURL = new URL("../src/knowledge-store.js", import.meta.url).href;

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "cst-knowledge-test-"));
  t.after(() => {
    assert.equal(path.dirname(root), path.resolve(os.tmpdir()));
    assert.match(path.basename(root), /^cst-knowledge-test-/);
    fs.rmSync(root, { recursive: true, force: true });
  });
  fs.writeFileSync(path.join(root, "check.json"), '{"passed":true}');
  const store = new KnowledgeStore(root, {});
  return { root, store };
}

function operation(overrides = {}) {
  return {
    title: "Reusable parameter workflow",
    category: "harness-reuse",
    steps: ["Define the parameter", "Add dependent History", "Inspect rebuild evidence"],
    preconditions: ["Working copy is selected"],
    parameters: ["parameter_name"],
    applicability: { cst_version: "2026" },
    status: "done",
    executed: true,
    verification: { status: "pass", summary: "Expected parameter and History were inspected",
      evidence: [{ path: "check.json" }] },
    ...overrides
  };
}

function source(root, name, operations, collection = "operations") {
  fs.writeFileSync(path.join(root, name), JSON.stringify({
    created_at: "2026-09-06T00:00:00Z",
    [collection]: operations
  }));
  return { manifest_path: name, collection };
}

test("verified workflow survives restart, deduplicates capture, and becomes stable across source manifests", (t) => {
  const { root, store } = fixture(t);
  const a = source(root, "a.json", [operation()]);
  const first = store.capture(a);
  assert.equal(first.entry_status, "verified");
  assert.equal(store.capture(a).created, false);
  const restarted = new KnowledgeStore(root, {});
  assert.equal(restarted.sections().length, 1);
  assert.equal(restarted.get(first.id).observations.length, 1);
  const b = source(root, "b.json", [operation()]);
  assert.equal(restarted.capture(b).entry_status, "stable");
  assert.equal(restarted.get(first.id).independent_successes, 2);
});

test("multiple operations in one manifest do not count as independent success", (t) => {
  const { root, store } = fixture(t);
  const args = source(root, "a.json", [operation(), operation()]);
  store.capture({ ...args, index: 0 });
  const result = store.capture({ ...args, index: 1 });
  assert.equal(result.entry_status, "verified");
  assert.equal(store.get(result.id).observations.length, 2);
});

test("dry runs, missing execution, and incomplete operations remain candidates", (t) => {
  const { root, store } = fixture(t);
  for (const [index, overrides] of [{ execute: false }, { executed: false }, { status: "running" }, { verification: undefined }].entries()) {
    const args = source(root, "candidate-" + index + ".json", [operation(overrides)]);
    assert.equal(store.capture(args).entry_status, "candidate");
  }
  assert.equal(store.sections().length, 0);
  assert.equal(store.sections({ includeCandidates: true }).length, 1);
});

test("failed reuse makes a definition disputed; a changed recipe gets a separate identity", (t) => {
  const { root, store } = fixture(t);
  const first = store.capture(source(root, "a.json", [operation()]));
  const failed = operation({ status: "failed", verification: { status: "fail", summary: "Rebuild failed" } });
  assert.equal(store.capture(source(root, "b.json", [failed])).entry_status, "disputed");
  assert.equal(store.sections().length, 0);
  assert.equal(store.get(first.id).observations.length, 2);
  const fixed = store.capture(source(root, "c.json", [operation({ steps: ["Inspect units", ...operation().steps] })]));
  assert.notEqual(fixed.id, first.id);
  assert.equal(fixed.entry_status, "verified");
});

test("legacy repair fields are captured as lessons and ordinary metrics are skipped", (t) => {
  const { root, store } = fixture(t);
  const repair = operation({ title: undefined, steps: undefined, error_signature: "Undefined parameter",
    error_class: "cst_command_error", diagnosis: "Dependent History ran first", repair_action: "Define parameter before History" });
  const result = store.capture(source(root, "repair.json", [repair]));
  assert.equal(store.get(result.id).kind, "lesson");
  assert.equal(store.capture(source(root, "metrics.json", [{ metrics: { s11: -20 } }])).status, "skipped");
});

test("checkpoint status controls promotion and historical capture reads persisted source", (t) => {
  const { root, store } = fixture(t);
  const args = source(root, "job.json", [{ status: "done", operation: operation({ status: undefined }) }], "checkpoints");
  assert.equal(store.capture(args).entry_status, "verified");
  assert.throws(() => store.capture({ ...args, index: 4 }), /not found/);
  assert.throws(() => store.capture({ ...args, collection: "other" }), /collection/);
});

test("evidence is required, hashed, bounded, and digest mismatches fail capture", (t) => {
  const { root, store } = fixture(t);
  const result = store.capture(source(root, "a.json", [operation()]));
  assert.match(store.get(result.id).observations[0].verification.evidence[0].sha256, /^[a-f0-9]{64}$/);
  for (const evidence of [[], [{ path: "missing.json" }], [{ path: "check.json", sha256: "wrong" }]]) {
    assert.throws(() => store.capture(source(root, "bad.json", [operation({
      verification: { status: "pass", summary: "Reported success", evidence }
    })])));
  }
});

test("automatic capture failures preserve the source and can be retried without execution", (t) => {
  const { root, store } = fixture(t);
  const args = source(root, "a.json", [operation({ verification: {
    status: "pass", summary: "Checked", evidence: [{ path: "later.json" }]
  } })]);
  assert.equal(store.captureAutomatically(args).status, "error");
  assert.equal(JSON.parse(fs.readFileSync(path.join(root, "a.json"))).operations.length, 1);
  fs.writeFileSync(path.join(root, "later.json"), "{}");
  assert.equal(store.capture(args).entry_status, "verified");
});

test("absolute, traversal, device, stream and symlink paths are rejected", (t) => {
  const { root, store } = fixture(t);
  const drivePath = "Z:" + "\\machine\\file.json";
  for (const value of [drivePath, "/" + "tmp/file", "..\\escape", "C:relative", "\\\\host\\share",
    "x/../y", "~/.cache", "safe/file:stream", "NUL.txt", "x./file"]) {
    assert.throws(() => relativePath(value));
  }
  const outside = fs.mkdtempSync(path.join(os.tmpdir(), "cst-knowledge-outside-"));
  const link = path.join(root, "linked");
  t.after(() => {
    assert.equal(path.dirname(outside), path.resolve(os.tmpdir()));
    assert.match(path.basename(outside), /^cst-knowledge-outside-/);
    fs.rmSync(outside, { recursive: true, force: true });
  });
  fs.symlinkSync(outside, link, process.platform === "win32" ? "junction" : "dir");
  assert.throws(() => store.capture({ manifest_path: "linked/a.json" }), /Symlinks/);
  assert.throws(() => new KnowledgeStore(root, { CST_KNOWLEDGE_DIR: drivePath }));
  assert.throws(() => store.capture(source(root, "a.json", [operation({ steps: ["Read " + drivePath] })])), /absolute/);
});

test("disable switches, custom store, and stable threshold are configurable", (t) => {
  const { root } = fixture(t);
  const args = source(root, "a.json", [operation()]);
  const disabled = new KnowledgeStore(root, { CST_KNOWLEDGE_ENABLED: "0" });
  assert.equal(disabled.capture(args).status, "disabled");
  assert.deepEqual(disabled.sections(), []);
  const manual = new KnowledgeStore(root, { CST_KNOWLEDGE_AUTO_CAPTURE: "0", CST_KNOWLEDGE_DIR: "local-memory" });
  assert.equal(manual.captureAutomatically(args).status, "disabled");
  assert.equal(manual.capture(args).status, "stored");
  assert.throws(() => new KnowledgeStore(root, { CST_KNOWLEDGE_STABLE_RUNS: "NaN" }));
});

test("concurrent processes publish duplicate and independent observations without overwriting", async (t) => {
  const { root } = fixture(t);
  source(root, "a.json", [operation()]);
  source(root, "b.json", [operation()]);
  const results = await Promise.all(["a.json", "a.json", "b.json"].map((manifest) =>
    new Promise((resolve, reject) => {
      const worker = new Worker(
        "const {parentPort,workerData}=require('node:worker_threads');" +
        "import(workerData.moduleURL).then(({KnowledgeStore})=>{" +
        "parentPort.postMessage(new KnowledgeStore(workerData.root,{}).capture({manifest_path:workerData.manifest}));" +
        "}).catch(e=>{throw e;});",
        { eval: true, workerData: { root, manifest, moduleURL } });
      worker.on("message", resolve);
      worker.on("error", reject);
      worker.on("exit", (code) => { if (code) reject(new Error("Worker failed: " + code)); });
    })));
  assert.equal(new Set(results.map((item) => item.id)).size, 1);
  const entry = new KnowledgeStore(root, {}).get(results[0].id);
  assert.equal(entry.observations.length, 2);
  assert.equal(entry.status, "stable");
});

function server(env) {
  const child = spawn(process.execPath, [path.join(repo, "mcp/src/server.js")], {
    cwd: repo, env: { ...process.env, ...env }, windowsHide: true,
    stdio: ["pipe", "pipe", "pipe"]
  });
  let buffer = "", stderr = "", id = 0;
  const pending = new Map();
  child.stderr.on("data", (data) => { stderr += data; });
  child.stdout.setEncoding("utf8");
  child.stdout.on("data", (data) => {
    buffer += data;
    let at;
    while ((at = buffer.indexOf("\n")) >= 0) {
      const reply = JSON.parse(buffer.slice(0, at));
      buffer = buffer.slice(at + 1);
      const waiter = pending.get(reply.id);
      if (!waiter) continue;
      pending.delete(reply.id);
      clearTimeout(waiter.timer);
      if (reply.error) waiter.reject(new Error(reply.error.message));
      else waiter.resolve(reply.result);
    }
  });
  child.on("error", (error) => {
    for (const waiter of pending.values()) { clearTimeout(waiter.timer); waiter.reject(error); }
    pending.clear();
  });
  function request(method, params = {}) {
    return new Promise((resolve, reject) => {
      const requestId = ++id;
      const timer = setTimeout(() => {
        pending.delete(requestId);
        reject(new Error("MCP timeout: " + stderr));
      }, 5000);
      pending.set(requestId, { resolve, reject, timer });
      child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id: requestId, method, params }) + "\n");
    });
  }
  return {
    request,
    async call(name, args) {
      const response = await request("tools/call", { name, arguments: args });
      return JSON.parse(response.content[0].text);
    },
    async stop() {
      if (child.exitCode !== null) return;
      await new Promise((resolve) => {
        const timer = setTimeout(() => child.kill(), 2000);
        child.once("close", () => { clearTimeout(timer); resolve(); });
        child.stdin.end();
      });
    }
  };
}

test("original MCP hooks capture, restart retrieval, Chinese search, recipe integration, and storage retry", async (t) => {
  const relative = "design-records/memory-test-" + randomUUID();
  const dir = path.resolve(repo, relative);
  fs.mkdirSync(dir, { recursive: true });
  const env = { CST_KNOWLEDGE_DIR: relative + "/knowledge", CST_KNOWLEDGE_ENABLED: "1", CST_KNOWLEDGE_AUTO_CAPTURE: "1" };
  let client = server(env);
  t.after(async () => {
    await client.stop();
    assert.equal(path.dirname(dir), path.resolve(repo, "design-records"));
    assert.match(path.basename(dir), /^memory-test-/);
    fs.rmSync(dir, { recursive: true, force: true });
  });
  const list = await client.request("tools/list");
  assert(list.tools.some((item) => item.name === "knowledge.capture_operation"));
  const variant = await client.call("records.create_variant", {
    project_path: "projects/example.cst", objective: "Memory integration", output_dir: relative
  });
  assert.equal(path.isAbsolute(variant.manifest_path), false);
  fs.writeFileSync(path.join(dir, "evidence.json"), '{"postconditions":"passed"}');
  const op = operation({ title: "参数化重建流程", verification: {
    status: "pass", summary: "Rebuild observed", evidence: [{ path: relative + "/evidence.json" }]
  } });
  const appended = await client.call("records.append_operation", { manifest_path: variant.manifest_path, operation: op });
  assert.equal(appended.knowledge.entry_status, "verified");
  assert.equal((await client.call("knowledge.capture_operation", { manifest_path: variant.manifest_path })).created, false);
  await client.stop();
  client = server(env);
  const workflows = await client.call("knowledge.search_workflows", { query: "参数化重建流程" });
  assert.equal(workflows.matches[0].id, appended.knowledge.id);
  const lessons = await client.call("knowledge.search_lessons", { query: "参数化重建流程" });
  assert(lessons.matches.some((match) => match.id === appended.knowledge.id));
  const recipe = await client.call("knowledge.get_recipe", { category: "harness-reuse" });
  assert.equal(recipe.found, true);
  assert.equal(recipe.learned[0].id, appended.knowledge.id);
  const categories = await client.call("knowledge.list_categories", {});
  assert(categories.categories.includes("harness-reuse"));
  const checkpoint = await client.call("cst.job_checkpoint", {
    manifest_path: relative + "/job.json", stage: "rebuild", status: "done", operation: op
  });
  assert.equal(checkpoint.knowledge.entry_status, "stable");
  const bad = await client.call("records.append_operation", {
    manifest_path: variant.manifest_path,
    operation: operation({ title: "Missing evidence workflow", verification: {
      status: "pass", summary: "Checked", evidence: [{ path: relative + "/later.json" }]
    } })
  });
  assert.equal(bad.knowledge.status, "error");
  assert.equal(bad.manifest.operations.length, 2);
  fs.writeFileSync(path.join(dir, "later.json"), "{}");
  assert.equal((await client.call("knowledge.capture_operation", {
    manifest_path: variant.manifest_path, index: 1
  })).entry_status, "verified");
  await assert.rejects(client.call("records.append_operation", {
    manifest_path: path.resolve(repo, variant.manifest_path), operation: {}
  }), /relative/);
});
