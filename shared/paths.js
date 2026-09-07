import fs from "node:fs";
import path from "node:path";

export function relativePath(value) {
  if (typeof value !== "string" || !value || value.length > 1024) throw new Error("Expected a relative path.");
  const normalized = value.replaceAll("\\", "/");
  if (path.posix.isAbsolute(normalized) || path.win32.isAbsolute(value) ||
      /[:\x00-\x1f]/.test(value) || normalized.startsWith("~") ||
      normalized.split("/").some((part) => !part || part === "." || part === ".." || /[. ]$/.test(part) ||
        /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(part))) {
    throw new Error("Only contained relative paths are allowed.");
  }
  return normalized;
}

export function containedPath(root, requested) {
  const relative = relativePath(requested);
  let current = fs.realpathSync(root);
  for (const part of relative.split("/")) {
    current = path.join(current, part);
    try {
      if (fs.lstatSync(current).isSymbolicLink()) throw new Error("Symlinks and junctions are not allowed in knowledge paths.");
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
  }
  return current;
}
