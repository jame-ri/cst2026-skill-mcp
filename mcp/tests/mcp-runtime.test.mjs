import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { validateArguments, runHelper, atomicJson, withRecordLock } from "../src/mcp-runtime.js";
import { MessageReader } from "../src/mcp-protocol.js";

const root = fileURLToPath(new URL("../../", import.meta.url));
const schema = { type: "object", properties: { execute: { type: "boolean" }, pid: { type: "integer", minimum: 1 } }, additionalProperties: false };
test("strict argument validation rejects coercion and unknown fields", () => {
  for (const value of [null, [], { execute: "false" }, { pid: -1 }, { other: true }]) assert.throws(() => validateArguments(value, schema));
  validateArguments({ execute: false, pid: 1 }, schema);
});
test("JSON parser preserves fragmented UTF-8 in both transports", () => {
  for (const framed of [false, true]) {
    const messages = [], errors = [];
    const reader = new MessageReader((msg) => messages.push(msg), (err) => errors.push(err));
    const payload = JSON.stringify({ text: "\u7aef\u53e3\u6d4b\u8bd5" });
    const wire = Buffer.from(framed ? "Content-Length: " + Buffer.byteLength(payload) + "\r\n\r\n" + payload : payload + "\n");
    for (const byte of wire) reader.feed(Buffer.from([byte]));
    reader.end();
    assert.equal(errors.length, 0);
    assert.deepEqual(messages, [{ text: "\u7aef\u53e3\u6d4b\u8bd5" }]);
  }
});
test("malformed JSON recovers and oversized messages are rejected", () => {
  const messages = [], errors = [];
  const reader = new MessageReader((msg) => messages.push(msg), (err) => errors.push(err), 30);
  reader.feed(Buffer.from('bad\n{"ok":true}\n' + "x".repeat(40) + "\n"));
  assert.equal(errors.length, 2);
  assert.deepEqual(messages, [{ ok: true }]);
});
test("missing helper is a structured failure, not a process crash", async () => {
  const r = await runHelper(["cst-test-missing-" + Date.now()], { timeoutMs: 1000 });
  assert.equal(r.ok, false);
  assert.equal(r.error, "ENOENT");
});
test("helper validates exit status and JSON success separately", async () => {
  for (const [code, ok] of [
    ['console.log(JSON.stringify({ok:true}))', true],
    ['console.log(JSON.stringify({ok:false}))', false],
    ['console.log(JSON.stringify({ok:true}));process.exitCode=2', false],
    ['console.log("not json")', false]
  ]) {
    const r = await runHelper([process.execPath, "-e", code], { timeoutMs: 5000 });
    assert.equal(r.ok, ok);
  }
});
test("helper preserves multi-byte output", async () => {
  const code = 'const b=Buffer.from(JSON.stringify({ok:true,text:"\\u7aef\\u53e3"})); for(const c of b) process.stdout.write(Buffer.from([c]));';
  const r = await runHelper([process.execPath, "-e", code], { timeoutMs: 5000 });
  assert.equal(r.ok, true);
  assert.equal(r.helper_result.text, "\u7aef\u53e3");
});
test("helper bounds execution time and output", async () => {
  const timed = await runHelper([process.execPath, "-e", "setInterval(()=>{},1000)"], { timeoutMs: 150 });
  assert.equal(timed.timed_out, true);
  assert.equal(timed.ok, false);
  const large = await runHelper([process.execPath, "-e", 'process.stdout.write("x".repeat(10000))'], { timeoutMs: 5000, maxOutputBytes: 100 });
  assert.equal(large.output_truncated, true);
  assert.equal(large.ok, false);
});
test("record locks serialize updates and release on failure", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "cst-runtime-"));
  const file = path.join(dir, "record.json");
  try {
    atomicJson(file, { count: 0 });
    await Promise.all(Array.from({length: 12}, () => withRecordLock(file, async () => {
      const r = JSON.parse(fs.readFileSync(file, "utf8"));
      await new Promise(resolve => setTimeout(resolve, 2));
      atomicJson(file, { count: r.count + 1 });
    })));
    assert.equal(JSON.parse(fs.readFileSync(file, "utf8")).count, 12);
    await assert.rejects(withRecordLock(file, () => { throw new Error("expected"); }));
    assert.equal(fs.existsSync(file + ".lock"), false);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("MCP integration: validation, plans, errors, and concurrent records", async () => {
  const dir = fs.mkdtempSync(path.join(root, "design-records", "runtime-test-"));
  const child = spawn(process.execPath, [path.join(root, "mcp/src/server.js")], { cwd: root, windowsHide: true, stdio: ["pipe", "pipe", "pipe"] });
  let next = 0;
  const pending = new Map();
  const reader = new MessageReader(msg => {
    const waiter = pending.get(msg.id);
    if (waiter) { pending.delete(msg.id); clearTimeout(waiter.timer); waiter.resolve(msg); }
  }, error => { throw new Error(error); });
  child.stdout.on("data", chunk => reader.feed(chunk));
  let stderr = "";
  child.stderr.on("data", chunk => { stderr += chunk; });
  const rpc = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++next;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error("RPC timeout: " + stderr)); }, 5000);
    pending.set(id, { resolve, timer });
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
  });
  const call = (name, args) => rpc("tools/call", { name, arguments: args });
  try {
    assert.equal((await rpc("initialize", { protocolVersion: "2024-11-05" })).result.protocolVersion, "2024-11-05");
    assert.deepEqual((await rpc("ping")).result, {});
    for (const args of [{project_path:"models/a.cst",execute:"false"}, {project_path:"../a.cst"}, {project_path:"C:\\a.cst"}, {project_path:"models/a.cst",typo:true}]) {
      assert.equal((await call("cst.inspect_project", args)).error.code, -32602);
    }
    assert.equal((await call("cst.cleanup_stale_processes", {pids:[-1]})).error.code, -32602);
    const plan = (await call("cst.inspect_project", {project_path:"models/a.cst",execute:false})).result;
    assert.equal(plan.isError, false);
    assert.equal(plan.structuredContent.status, "planned");
    assert.equal(JSON.stringify(plan).includes(root.replaceAll("\\", "\\\\")), false);
    const missing = (await call("docs.read_official_doc", {relative_path:"missing-test-file.md"})).result;
    assert.equal(missing.isError, true);
    const blocked = (await call("cst.cleanup_stale_processes", {pids:[123],execute:true})).result;
    assert.equal(blocked.isError, true);
    const created = (await call("records.create_variant", {project_path:"models/a.cst",objective:"test",output_dir:path.relative(root,dir).replaceAll("\\","/")})).result.structuredContent;
    const results = await Promise.all(Array.from({length:8}, (_,i) => call("records.append_operation", {manifest_path:created.manifest_path,operation:{title:"operation "+i}})));
    assert.ok(results.every(r=>r.result?.isError===false));
    assert.equal(JSON.parse(fs.readFileSync(path.join(root, created.manifest_path),"utf8")).operations.length, 8);
  } finally {
    const closed = new Promise(resolve => child.once("close", resolve));
    child.stdin.end();
    await closed;
    for (const waiter of pending.values()) clearTimeout(waiter.timer);
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
