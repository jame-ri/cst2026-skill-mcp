import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";

export class CstWorkerClient {
  constructor(repoRoot, pythonExecutable) {
    this.repoRoot = repoRoot;
    this.pythonExecutable = pythonExecutable;
    this.child = null;
    this.closing = null;
    this.pending = null;
    this.buffer = Buffer.alloc(0);
    this.stderr = "";
  }
  start() {
    if (this.closing) throw new Error("The previous worker is still releasing its session. Wait before reconnecting.");
    const child = spawn(this.pythonExecutable(), ["-u", "-B", "-m", "cst_api.worker"], {
      cwd: this.repoRoot, windowsHide: true, shell: false,
      env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONUNBUFFERED: "1" },
      stdio: ["pipe", "pipe", "pipe"]
    });
    this.child = child;
    this.buffer = Buffer.alloc(0);
    this.stderr = "";
    child.stdout.on("data", chunk => {
      if (this.child !== child) return;
      this.buffer = Buffer.concat([this.buffer, chunk]);
      if (this.buffer.length > 8 * 1024 * 1024) return this.stop("Worker output exceeded its limit; session invalidated.", true);
      let end;
      while ((end = this.buffer.indexOf("\n")) >= 0) {
        const line = this.buffer.subarray(0, end);
        this.buffer = this.buffer.subarray(end + 1);
        if (!line.length) continue;
        let response;
        try { response = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(line)); }
        catch { return this.stop("Invalid worker response; session invalidated.", true); }
        const pending = this.pending;
        if (!pending || response.id !== pending.id || typeof response.result?.ok !== "boolean") {
          return this.stop("Unexpected worker response; session invalidated.", true);
        }
        this.pending = null;
        clearTimeout(pending.timer);
        pending.resolve(response.result);
      }
    });
    child.stderr.on("data", chunk => {
      if (this.child === child) this.stderr = (this.stderr + chunk.toString("utf8")).slice(-8192);
    });
    child.stdin.on("error", error => {
      if (this.child === child) this.stop("CST worker input failed: " + error.code, true);
    });
    child.once("error", error => {
      if (this.child === child) this.stop("Cannot start CST Python: " + (error.code || error.message), true);
    });
    child.once("close", (code, signal) => {
      if (this.child !== child) return;
      this.child = null;
      this.fail("CST worker exited (" + code + ", " + signal + "). Reconnect explicitly; do not repeat uncertain actions. " + this.stderr);
    });
  }
  fail(message) {
    const pending = this.pending;
    this.pending = null;
    if (pending) { clearTimeout(pending.timer); pending.reject(new Error(message)); }
  }
  stop(message = "MCP connection closed. CST itself was not terminated.", force = false) {
    const child = this.child;
    this.child = null;
    this.fail(message);
    if (!child) return;
    this.closing = child;
    let terminateTimer;
    let forceTimer;
    const terminate = () => {
      if (child.exitCode !== null || child.signalCode !== null) return;
      child.kill();
      forceTimer = setTimeout(() => {
        if (child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
      }, 500);
      forceTimer.unref();
    };
    child.once("close", () => {
      clearTimeout(terminateTimer);
      clearTimeout(forceTimer);
      if (this.closing === child) this.closing = null;
    });
    if (force) {
      child.stdin.destroy();
      terminate();
    } else {
      // EOF lets Python's finally release the cooperating-controller lease.
      child.stdin.end();
      terminateTimer = setTimeout(terminate, 2000);
      terminateTimer.unref();
    }
  }
  call(method, args, timeoutMs) {
    if (this.pending) return Promise.reject(new Error("Another CST request is in flight."));
    if (!this.child && method !== "cst.connect") return Promise.reject(new Error("No live worker. Connect explicitly; previous session IDs are invalid."));
    if (!this.child) this.start();
    return new Promise((resolve, reject) => {
      const id = randomUUID();
      const timer = setTimeout(() => this.stop(
        "CST request timed out; session invalidated. CST may still be running and the action outcome is unknown.", true), timeoutMs);
      this.pending = { id, timer, resolve, reject };
      try { this.child.stdin.write(JSON.stringify({ id, method, args }) + "\n"); }
      catch (error) { this.stop("Cannot dispatch CST request: " + error.message, true); }
    });
  }
}
