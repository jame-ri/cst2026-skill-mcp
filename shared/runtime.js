import fs from "node:fs";
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { setTimeout as delay } from "node:timers/promises";

export class InputError extends Error {}

export function validateArguments(value, schema, at = "arguments", depth = 0) {
  const fail = (reason) => { throw new InputError(at + ": " + reason); };
  if (depth > 32) fail("nesting exceeds 32 levels");
  const kinds = Array.isArray(schema.type) ? schema.type : [schema.type];
  const actual = value === null ? "null" : Array.isArray(value) ? "array" : typeof value;
  if (schema.type && !kinds.some((kind) => kind === actual ||
      (kind === "integer" && actual === "number" && Number.isInteger(value)))) fail("wrong value type");
  if (schema.enum && !schema.enum.includes(value)) fail("value is not in the allowed enum");
  if (typeof value === "number") {
    if (!Number.isFinite(value)) fail("number must be finite");
    if (schema.minimum !== undefined && value < schema.minimum) fail("below minimum");
    if (schema.maximum !== undefined && value > schema.maximum) fail("above maximum");
  }
  if (typeof value === "string") {
    if (value.length < (schema.minLength ?? 0) || value.length > (schema.maxLength ?? 65536)) fail("invalid string length");
    if (schema.pattern && !new RegExp(schema.pattern).test(value)) fail("invalid string format");
  }
  if (Array.isArray(value)) {
    if (value.length < (schema.minItems ?? 0) || value.length > (schema.maxItems ?? 1000)) fail("invalid array length");
    for (const [index, item] of value.entries()) validateArguments(item, schema.items ?? {}, at + "[" + index + "]", depth + 1);
  } else if (actual === "object") {
    if (Object.keys(value).length > 128) fail("too many object fields");
    for (const key of schema.required ?? []) {
      if (!Object.hasOwn(value, key) || (typeof value[key] === "string" && !value[key].trim())) fail("missing " + key);
    }
    for (const [key, item] of Object.entries(value)) {
      if (["__proto__", "prototype", "constructor"].includes(key)) fail("unsafe object key");
      const property = schema.properties?.[key];
      if (!property && schema.additionalProperties === false) fail("unknown field " + key);
      validateArguments(item, property ?? {}, at + "." + key, depth + 1);
    }
  }
}

export function atomicJson(file, data) {
  const temporary = file + "." + randomUUID() + ".tmp";
  let fd;
  try {
    fd = fs.openSync(temporary, "wx", 0o600);
    fs.writeFileSync(fd, JSON.stringify(data, null, 2) + "\n", "utf8");
    fs.fsyncSync(fd);
    fs.closeSync(fd);
    fd = undefined;
    fs.renameSync(temporary, file);
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
}

export async function withRecordLock(file, callback, waitMs = 2000) {
  const lock = file + ".lock";
  const deadline = Date.now() + waitMs;
  let fd;
  while (fd === undefined) {
    try {
      fd = fs.openSync(lock, "wx", 0o600);
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      if (Date.now() >= deadline) throw new Error("Record is busy or has a stale lock. Retry the record only; inspect the lock owner before removing a stale lock.");
      await delay(25);
    }
  }
  try {
    fs.writeFileSync(fd, JSON.stringify({ pid: process.pid, created_at: new Date().toISOString() }));
    return await callback();
  } finally {
    fs.closeSync(fd);
    fs.unlinkSync(lock);
  }
}

export function runHelper(argv, { cwd, timeoutMs, maxOutputBytes = 8 * 1024 * 1024 } = {}) {
  return new Promise((resolve) => {
    const started = Date.now();
    let child, timeout, forceTimer, settleTimer;
    let timedOut = false, truncated = false, finished = false, bytes = 0;
    const stdout = [], stderr = [];
    const finish = (code, signal, error, cleanupRequired = false) => {
      if (finished) return;
      finished = true;
      clearTimeout(timeout);
      clearTimeout(forceTimer);
      clearTimeout(settleTimer);
      const out = Buffer.concat(stdout).toString("utf8");
      const err = Buffer.concat(stderr).toString("utf8");
      let helperResult = null;
      try { helperResult = JSON.parse(out); } catch { /* Preserve raw diagnostics below. */ }
      const valid = helperResult !== null && typeof helperResult === "object" &&
        !Array.isArray(helperResult) && typeof helperResult.ok === "boolean";
      const ok = code === 0 && !signal && !error && !timedOut && !truncated && valid && helperResult.ok;
      resolve({
        execute: true, ok: Boolean(ok), status: ok ? "succeeded" : "failed",
        command: argv, helper_pid: child?.pid ?? null, exit_code: code, signal,
        timed_out: timedOut, output_truncated: truncated, cleanup_required: cleanupRequired,
        elapsed_ms: Date.now() - started, stdout: out, stderr: err, helper_result: helperResult,
        error: error || (timedOut ? "helper_timeout" : truncated ? "helper_output_limit" :
          !valid ? "invalid_helper_json" : !ok ? "helper_failed" : null)
      });
    };
    const terminate = () => {
      // Only this owned helper is signalled, never CST processes by name.
      child.kill();
      forceTimer ??= setTimeout(() => child.kill("SIGKILL"), 250);
      settleTimer ??= setTimeout(() => finish(null, null, "helper_did_not_close", true), 1500);
    };
    const collect = (target, chunk) => {
      if (finished) return;
      const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
      const remaining = Math.max(0, maxOutputBytes - bytes);
      target.push(buffer.subarray(0, remaining));
      bytes += Math.min(remaining, buffer.length);
      if (buffer.length > remaining && !truncated) {
        truncated = true;
        terminate();
      }
    };
    try {
      child = spawn(argv[0], argv.slice(1), { cwd, windowsHide: true, shell: false, stdio: ["ignore", "pipe", "pipe"] });
      child.stdout.on("data", (chunk) => collect(stdout, chunk));
      child.stderr.on("data", (chunk) => collect(stderr, chunk));
      child.once("error", (error) => finish(null, null, error.code || "spawn_failed"));
      child.once("close", (code, signal) => finish(code, signal, null));
      timeout = setTimeout(() => { timedOut = true; terminate(); }, timeoutMs ?? 300000);
    } catch (error) {
      finish(null, null, error.code || "spawn_failed");
    }
  });
}
