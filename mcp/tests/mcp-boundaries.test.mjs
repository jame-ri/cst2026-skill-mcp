import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { MessageReader } from "../src/mcp-protocol.js";

const root = fileURLToPath(new URL("../../", import.meta.url));

test("resource bounds and recovery identity fail before execution", async () => {
  const dir = fs.mkdtempSync(path.join(root, "design-records", "boundary-test-"));
  const manifest = path.relative(root, path.join(dir, "job.json")).replaceAll("\\", "/");
  const child = spawn(process.execPath, [path.join(root, "mcp/src/server.js")], { cwd: root, windowsHide: true, stdio: ["pipe", "pipe", "pipe"] });
  let sequence = 0;
  let diagnostics = "";
  const pending = new Map();
  const reader = new MessageReader(reply => {
    const item = pending.get(reply.id);
    if (item) { clearTimeout(item.timer); pending.delete(reply.id); item.resolve(reply); }
  }, () => {});
  child.stdout.on("data", chunk => reader.feed(chunk));
  child.stderr.on("data", chunk => { diagnostics += chunk; });
  function call(name, args) {
    return new Promise((resolve, reject) => {
      const id = ++sequence;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error("Timed out: " + diagnostics)); }, 5000);
      pending.set(id, { resolve, timer });
      child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method: "tools/call", params: { name, arguments: args } }) + "\n");
    });
  }
  try {
    for (const field of ["min_free_memory_gb", "min_free_disk_gb", "max_single_cst_memory_gb"]) {
      for (const value of [-1, 100001]) {
        const result = await call("cst.preflight_resources", { execute: false, [field]: value });
        assert.equal(result.error?.code, -32602, field + "=" + value);
      }
    }
    const valid = await call("cst.preflight_resources", { execute: false, min_free_memory_gb: 0 });
    assert.equal(valid.result.structuredContent.status, "planned");
    assert.equal((await call("cst.result_sanity", { project_path: "models/a.cst", run_id: 1000001 })).error?.code, -32602);
    assert.equal((await call("cst.recover_job", {})).error?.code, -32602);
    fs.writeFileSync(path.join(root, manifest), JSON.stringify({ job_id: "original", checkpoints: [] }));
    assert.equal((await call("cst.recover_job", { manifest_path: manifest, job_id: "wrong" })).error?.code, -32602);
    assert.equal((await call("cst.recover_job", { manifest_path: manifest, job_id: "original" })).result.structuredContent.job_id, "original");
    assert.equal((await call("cst.job_checkpoint", { manifest_path: manifest, job_id: "wrong", stage: "inspect", status: "pending" })).error?.code, -32602);
    assert.equal(JSON.parse(fs.readFileSync(path.join(root, manifest), "utf8")).checkpoints.length, 0);
  } finally {
    const closed = new Promise(resolve => child.once("close", resolve));
    child.stdin.end();
    await closed;
    for (const item of pending.values()) clearTimeout(item.timer);
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
