import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { containedPath } from "../shared/paths.js";
import { digest, readJson, portableRecord } from "../shared/data.js";
import { InputError, atomicJson, withRecordLock } from "../shared/runtime.js";

export class ExecutionJournal {
  constructor(root) { this.root = root; }
  async run(name, args, dispatch) {
    const operationId = args.operation_id ?? randomUUID();
    if (!/^[a-f0-9-]{36}$/.test(operationId)) throw new InputError("Invalid operation_id.");
    const { operation_id, execute, timeout_sec, ...parameters } = args;
    const requestDigest = digest({ name, parameters });
    const relative = "design-records/direct-operations/" + operationId + ".json";
    const file = containedPath(this.root, relative);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    return withRecordLock(file, async () => {
      if (fs.existsSync(file)) {
        const previous = readJson(file, 16 * 1024 * 1024);
        if (previous.request_digest !== requestDigest) throw new InputError("operation_id belongs to a different request.");
        if (previous.result) return { ...previous.result, operation_id: operationId,
          record: { status: "stored", path: relative }, replayed: true };
        return { execute: false, ok: false, blocked: true, status: "unknown_outcome", operation_id: operationId,
          record: { status: "stored", path: relative },
          message: "An intent exists without a recorded outcome. Inspect CST; never replay this operation automatically." };
      }
      const record = { schema_version: "cstapi.direct-operation.v1", operation_id: operationId,
        request_digest: requestDigest, tool: name, arguments: portableRecord(this.root, parameters),
        status: "started", started_at: new Date().toISOString() };
      atomicJson(file, record);
      // Exactly one dispatch after a durable intent. Recording failures never rerun CST.
      const result = portableRecord(this.root, await dispatch({ ...args, operation_id: operationId }));
      try {
        atomicJson(file, { ...record, finished_at: new Date().toISOString(), status: result.status, result });
        return { ...result, operation_id: operationId, record: { status: "stored", path: relative } };
      } catch {
        return { ...result, operation_id: operationId, record: { status: "error", path: relative },
          warning: "CST returned an outcome but its receipt could not be saved. Do not repeat the action to repair recording." };
      }
    });
  }
}
