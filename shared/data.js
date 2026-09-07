import fs from "node:fs";
import { createHash } from "node:crypto";
import { InputError } from "./runtime.js";

export function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") return Object.fromEntries(
    Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  return value;
}
export const digest = value => createHash("sha256").update(
  typeof value === "string" || Buffer.isBuffer(value) ? value : JSON.stringify(canonical(value))).digest("hex");

export function readJson(file, maxBytes = 2 * 1024 * 1024) {
  if (fs.statSync(file).size > maxBytes) throw new InputError("Stored JSON exceeds its size limit.");
  return JSON.parse(fs.readFileSync(file, "utf8"));
}
export function writeOnce(file, value) {
  const bytes = Buffer.isBuffer(value) ? value : Buffer.from(
    typeof value === "string" ? value : JSON.stringify(value, null, 2) + "\n", "utf8");
  let fd;
  try { fd = fs.openSync(file, "wx", 0o600); }
  catch (error) {
    if (error.code !== "EEXIST") throw error;
    if (!fs.readFileSync(file).equals(bytes)) throw new InputError("An immutable artifact already exists with different content.");
    return;
  }
  try { fs.writeFileSync(fd, bytes); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
}
export function assertPortable(value, at = "value", depth = 0) {
  if (depth > 32) throw new InputError("Input nesting exceeds its limit.");
  if (typeof value === "string" && (/(?:^|\s)[a-z]:[\\/]/i.test(value) || /^(?:[\\/]|~[\\/])/.test(value))) {
    throw new InputError(at + " must not contain an absolute filesystem path.");
  }
  if (Array.isArray(value)) value.forEach((item, index) => assertPortable(item, at + "[" + index + "]", depth + 1));
  else if (value && typeof value === "object") for (const [key, item] of Object.entries(value)) assertPortable(item, at + "." + key, depth + 1);
}
export function portableRecord(root, value) {
  const bindings = [[root, "."], ...["CST_INSTALL_DIR", "CST_HOME", "CST_ROOT", "CST_PYTHON_LIB_DIR", "CST_PYTHON_EXE"]
    .filter(key => process.env[key] && /[\\/]/.test(process.env[key]))
    .map(key => [process.env[key], "<" + key + ">"])]
    .flatMap(([source, label]) => [[source, label], [source.replaceAll("\\", "/"), label]])
    .sort((a, b) => b[0].length - a[0].length);
  const visit = item => {
    if (typeof item === "string") {
      for (const [source, label] of bindings) item = item.split(source).join(label);
      return item;
    }
    if (Array.isArray(item)) return item.map(visit);
    if (item && typeof item === "object") return Object.fromEntries(Object.entries(item).map(([key, data]) => [key, visit(data)]));
    return item;
  };
  return visit(value);
}
