#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const macroInventoryPath = path.join(repoRoot, "macro-library", "macro-inventory.csv");
const officialDocsRoot = path.join(repoRoot, "official-docs");
const recordsRoot = path.join(repoRoot, "design-records");
const cstHelperPath = path.join(repoRoot, "mcp", "python", "cst_ops.py");

let macroRowsCache = null;
let inputBuffer = "";
let framedTransport = false;

const textExtensions = new Set([".htm", ".html", ".md", ".py", ".txt", ".bas", ".cls", ".mcr", ".mcs"]);

const cstPaths = detectCstPaths();

const tools = [
  {
    name: "docs.search_macros",
    description: "Search the indexed CST installed macro library for VBA/History command examples.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Search terms such as Brick, DiscretePort, Farfield, S-Parameter, Horn, Monitor." },
        category: { type: "string", description: "Optional top-level macro category, for example Construct, Solver, Results." },
        application: { type: "string", description: "Optional CST module hint, for example MWS, DS, EMS, PS, MPS." },
        script_only: { type: "boolean", default: true, description: "If true, only return mcr/mcs/bas/cls/py rows." },
        limit: { type: "integer", minimum: 1, maximum: 100, default: 20 }
      },
      required: ["query"]
    }
  },
  {
    name: "docs.read_macro",
    description: "Read a CST installed macro source file referenced by macro inventory source_path or relative_path.",
    inputSchema: {
      type: "object",
      properties: {
        source_path: { type: "string", description: "Absolute original macro path under the detected CST macro root." },
        relative_path: { type: "string", description: "Inventory relative_path, for example Solver\\Ports\\Set Port Mode Evaluation Frequency^+MWS+PS.mcr." },
        max_chars: { type: "integer", minimum: 500, maximum: 100000, default: 12000 }
      }
    }
  },
  {
    name: "docs.search_official_docs",
    description: "Search copied CST official Python/VBA documentation in official-docs.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Search terms such as add_to_history, ResultTree, FarfieldPlot, StoreParameter." },
        scope: { type: "string", description: "Optional scope under official-docs: python, python_cst_libraries, vba-3d, vba-des, advanced." },
        limit: { type: "integer", minimum: 1, maximum: 50, default: 15 }
      },
      required: ["query"]
    }
  },
  {
    name: "docs.read_official_doc",
    description: "Read a copied CST official documentation file under official-docs.",
    inputSchema: {
      type: "object",
      properties: {
        relative_path: { type: "string", description: "Path relative to official-docs, or a path starting with official-docs/." },
        max_chars: { type: "integer", minimum: 500, maximum: 200000, default: 20000 }
      },
      required: ["relative_path"]
    }
  },
  {
    name: "history.extract_pattern",
    description: "Extract compact VBA/History blocks from CST macros for safe parameterized add_to_history use.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Command/object terms to prioritize, for example Brick, DiscretePort, Monitor, Solver." },
        source_path: { type: "string" },
        relative_path: { type: "string" },
        max_blocks: { type: "integer", minimum: 1, maximum: 20, default: 5 }
      },
      required: ["query"]
    }
  },
  {
    name: "records.create_variant",
    description: "Create a versioned CST design manifest for optimization, structure evolution, or ML data collection.",
    inputSchema: {
      type: "object",
      properties: {
        project_path: { type: "string" },
        design_id: { type: "string" },
        parent_design_id: { type: ["string", "null"] },
        objective: { type: "string" },
        save_policy: { type: "string", enum: ["no_save", "save_copy", "save_original"], default: "no_save" },
        output_dir: { type: "string", description: "Optional repo-relative output directory. Defaults to design-records." }
      },
      required: ["project_path", "objective"]
    }
  },
  {
    name: "records.append_operation",
    description: "Append an operation, metric set, source macro list, or artifact record to an existing design manifest.",
    inputSchema: {
      type: "object",
      properties: {
        manifest_path: { type: "string" },
        operation: { type: "object" }
      },
      required: ["manifest_path", "operation"]
    }
  },
  {
    name: "cst.closed_start",
    description: "Standard CST helper for closed-CST startup: connect/start CST and open a project using CST Python.",
    inputSchema: {
      type: "object",
      properties: {
        project_path: { type: "string" },
        python_executable: { type: "string", description: "CST Python executable. Defaults to CST_PYTHON_EXE, then auto-detected CST Python." },
        execute: { type: "boolean", default: false, description: "False returns the planned command; true actually runs CST Python." },
        timeout_sec: { type: "integer", minimum: 5, maximum: 3600, default: 180 }
      },
      required: ["project_path"]
    }
  },
  {
    name: "cst.live_modify_parameter",
    description: "Standard CST helper for live project parameter modification and restore without saving the original project.",
    inputSchema: {
      type: "object",
      properties: {
        project_path: { type: "string" },
        parameter: { type: "string" },
        test_value: { type: ["string", "number"] },
        pause_after_set: { type: "number", minimum: 0, maximum: 3600, default: 5 },
        restore: { type: "boolean", default: true },
        require_open: { type: "boolean", default: true },
        python_executable: { type: "string" },
        execute: { type: "boolean", default: false },
        timeout_sec: { type: "integer", minimum: 5, maximum: 7200, default: 300 }
      },
      required: ["project_path", "parameter", "test_value"]
    }
  }
];

function nowIso() {
  return new Date().toISOString();
}

function normalizeSlashes(value) {
  return String(value ?? "").replaceAll("/", "\\");
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function firstExisting(paths) {
  return paths.find((candidate) => candidate && fs.existsSync(candidate)) ?? null;
}

function detectCstInstallDir() {
  const envRoot = process.env.CST_INSTALL_DIR || process.env.CST_HOME || process.env.CST_ROOT;
  const candidates = unique([
    envRoot,
    "D:\\CST",
    "C:\\CST",
    "C:\\Program Files\\CST Studio Suite 2026",
    "C:\\Program Files\\Dassault Systemes\\CST Studio Suite 2026",
    "C:\\Program Files\\SIMULIA\\CST Studio Suite 2026"
  ]);
  return firstExisting(candidates);
}

function detectCstPaths() {
  const installDir = detectCstInstallDir();
  const pythonCandidates = unique([
    process.env.CST_PYTHON_EXE,
    installDir ? path.join(installDir, "Python", "python.exe") : null,
    installDir ? path.join(installDir, "AMD64", "python.exe") : null,
    installDir ? path.join(installDir, "AMD64", "python", "python.exe") : null
  ]);
  const macroCandidates = unique([
    process.env.CST_MACRO_ROOT,
    installDir ? path.join(installDir, "Library", "Macros") : null,
    "D:\\CST\\Library\\Macros"
  ]);
  const designEnvironmentCandidates = unique([
    process.env.CST_DESIGN_ENV_EXE,
    installDir ? path.join(installDir, "CST DESIGN ENVIRONMENT.exe") : null,
    installDir ? path.join(installDir, "AMD64", "CST DESIGN ENVIRONMENT_AMD64.exe") : null
  ]);
  return {
    installDir,
    pythonExecutable: firstExisting(pythonCandidates),
    macroRoot: firstExisting(macroCandidates) || macroCandidates[0],
    designEnvironmentExecutable: firstExisting(designEnvironmentCandidates),
    pythonCandidates,
    macroCandidates,
    designEnvironmentCandidates
  };
}

function safeNumber(value, fallback, min, max) {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(min, Math.min(max, n));
}

function splitTerms(query) {
  return String(query ?? "")
    .toLowerCase()
    .split(/[^a-z0-9_+\-.]+/i)
    .filter(Boolean);
}

function parseCsvLine(line) {
  const cells = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (quoted && line[i + 1] === '"') {
        cell += '"';
        i += 1;
      } else {
        quoted = !quoted;
      }
    } else if (ch === "," && !quoted) {
      cells.push(cell);
      cell = "";
    } else {
      cell += ch;
    }
  }
  cells.push(cell);
  return cells;
}

function loadMacroRows() {
  if (macroRowsCache) return macroRowsCache;
  const raw = fs.readFileSync(macroInventoryPath, "utf8").replace(/^\uFEFF/, "");
  const lines = raw.split(/\r?\n/).filter(Boolean);
  const headers = parseCsvLine(lines.shift());
  macroRowsCache = lines.map((line) => {
    const values = parseCsvLine(line);
    return Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]));
  });
  return macroRowsCache;
}

function scoreText(haystack, terms) {
  const text = haystack.toLowerCase();
  let score = 0;
  for (const term of terms) {
    if (!term) continue;
    const first = text.indexOf(term);
    if (first >= 0) {
      score += 10;
      score += Math.max(0, 5 - Math.floor(first / 80));
    }
  }
  return score;
}

function searchMacros(args) {
  const query = String(args.query ?? "").trim();
  const terms = splitTerms(query);
  const limit = safeNumber(args.limit, 20, 1, 100);
  const scriptOnly = args.script_only !== false;
  const category = String(args.category ?? "").toLowerCase();
  const application = String(args.application ?? "").toLowerCase();
  const scriptExt = new Set(["mcr", "mcs", "bas", "cls", "py"]);

  const matches = loadMacroRows()
    .filter((row) => !scriptOnly || scriptExt.has(String(row.extension).toLowerCase()))
    .filter((row) => !category || String(row.category).toLowerCase() === category)
    .filter((row) => !application || String(row.applications).toLowerCase().split(";").includes(application))
    .map((row) => {
      const haystack = [
        row.category,
        row.subcategory,
        row.title,
        row.file_name,
        row.applications,
        row.keywords,
        row.first_comment,
        row.relative_path
      ].join(" ");
      return { row, score: scoreText(haystack, terms) };
    })
    .filter((item) => item.score > 0 || query === "*")
    .sort((a, b) => b.score - a.score || a.row.relative_path.localeCompare(b.row.relative_path))
    .slice(0, limit)
    .map(({ row, score }) => ({
      score,
      title: row.title,
      category: row.category,
      subcategory: row.subcategory,
      extension: row.extension,
      applications: row.applications,
      visibility: row.visibility,
      keywords: row.keywords,
      relative_path: row.relative_path,
      source_path: row.source_path,
      first_comment: row.first_comment
    }));

  return {
    query,
    count: matches.length,
    matches
  };
}

function pathInside(child, parent) {
  const relative = path.relative(path.resolve(parent), path.resolve(child));
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

function findMacroPath(args) {
  const rows = loadMacroRows();
  if (args.relative_path) {
    const requested = normalizeSlashes(args.relative_path).toLowerCase();
    const row = rows.find((item) => normalizeSlashes(item.relative_path).toLowerCase() === requested);
    if (!row) throw new Error(`Macro relative_path not found in inventory: ${args.relative_path}`);
    const detectedPath = path.join(cstPaths.macroRoot, normalizeSlashes(row.relative_path));
    return fs.existsSync(detectedPath) ? detectedPath : row.source_path;
  }
  if (args.source_path) {
    const requested = normalizeSlashes(args.source_path);
    const row = rows.find((item) => normalizeSlashes(item.source_path).toLowerCase() === requested.toLowerCase());
    if (row) {
      const detectedPath = path.join(cstPaths.macroRoot, normalizeSlashes(row.relative_path));
      return fs.existsSync(detectedPath) ? detectedPath : row.source_path;
    }
    if (!normalizeSlashes(requested).toLowerCase().startsWith(normalizeSlashes(cstPaths.macroRoot).toLowerCase() + "\\")) {
      throw new Error(`source_path must be under ${cstPaths.macroRoot}`);
    }
    return requested;
  }
  throw new Error("Provide source_path or relative_path.");
}

function readTextFile(filePath, maxChars) {
  if (!fs.existsSync(filePath)) throw new Error(`File not found: ${filePath}`);
  const raw = fs.readFileSync(filePath);
  let text = raw.toString("utf8");
  if (text.includes("\uFFFD")) {
    text = raw.toString("latin1");
  }
  const truncated = text.length > maxChars;
  return {
    path: filePath,
    chars: text.length,
    truncated,
    text: truncated ? text.slice(0, maxChars) : text
  };
}

function readMacro(args) {
  const maxChars = safeNumber(args.max_chars, 12000, 500, 100000);
  const filePath = findMacroPath(args);
  const data = readTextFile(filePath, maxChars);
  const row = loadMacroRows().find((item) => normalizeSlashes(item.source_path).toLowerCase() === normalizeSlashes(filePath).toLowerCase());
  return {
    source_path: filePath,
    relative_path: row?.relative_path ?? null,
    title: row?.title ?? path.basename(filePath),
    extension: path.extname(filePath).slice(1),
    chars: data.chars,
    truncated: data.truncated,
    text: data.text
  };
}

function walkFiles(root, output = []) {
  if (!fs.existsSync(root)) return output;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const full = path.join(root, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === ".git" || entry.name === "MathJax") continue;
      walkFiles(full, output);
    } else if (textExtensions.has(path.extname(entry.name).toLowerCase())) {
      output.push(full);
    }
  }
  return output;
}

function stripHtml(text) {
  return text
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function searchOfficialDocs(args) {
  const query = String(args.query ?? "").trim();
  const terms = splitTerms(query);
  const limit = safeNumber(args.limit, 15, 1, 50);
  const scope = String(args.scope ?? "").replace(/^official-docs[\\/]/i, "");
  const root = scope ? path.join(officialDocsRoot, scope) : officialDocsRoot;
  if (!pathInside(root, officialDocsRoot)) throw new Error("scope must stay under official-docs.");

  const matches = [];
  for (const filePath of walkFiles(root)) {
    const stats = fs.statSync(filePath);
    if (stats.size > 2_500_000) continue;
    const raw = readTextFile(filePath, 2_500_000).text;
    const searchable = path.extname(filePath).toLowerCase().startsWith(".htm") ? stripHtml(raw) : raw;
    const haystack = `${path.relative(officialDocsRoot, filePath)} ${searchable.slice(0, 200000)}`;
    const score = scoreText(haystack, terms);
    if (score <= 0 && query !== "*") continue;
    const lower = searchable.toLowerCase();
    let first = terms.map((term) => lower.indexOf(term)).filter((idx) => idx >= 0).sort((a, b) => a - b)[0] ?? 0;
    first = Math.max(0, first - 160);
    matches.push({
      score,
      relative_path: path.relative(officialDocsRoot, filePath),
      size_bytes: stats.size,
      snippet: searchable.slice(first, first + 420)
    });
  }
  matches.sort((a, b) => b.score - a.score || a.relative_path.localeCompare(b.relative_path));
  return { query, scope: scope || null, count: Math.min(matches.length, limit), matches: matches.slice(0, limit) };
}

function readOfficialDoc(args) {
  const maxChars = safeNumber(args.max_chars, 20000, 500, 200000);
  const cleaned = String(args.relative_path ?? "").replace(/^official-docs[\\/]/i, "");
  const full = path.join(officialDocsRoot, cleaned);
  if (!pathInside(full, officialDocsRoot)) throw new Error("relative_path must stay under official-docs.");
  const data = readTextFile(full, maxChars);
  return {
    relative_path: path.relative(officialDocsRoot, full),
    chars: data.chars,
    truncated: data.truncated,
    text: path.extname(full).toLowerCase().startsWith(".htm") ? stripHtml(data.text) : data.text
  };
}

function extractHistoryPattern(args) {
  const query = String(args.query ?? "").trim();
  const terms = splitTerms(query);
  const maxBlocks = safeNumber(args.max_blocks, 5, 1, 20);
  const sources = [];
  if (args.source_path || args.relative_path) {
    sources.push(readMacro({ ...args, max_chars: 100000 }));
  } else {
    const candidates = searchMacros({ query, script_only: true, limit: 30 }).matches;
    if (candidates.length === 0) throw new Error(`No macro found for query: ${query}`);
    for (const candidate of candidates) {
      try {
        sources.push(readMacro({ relative_path: candidate.relative_path, max_chars: 100000 }));
      } catch {
        // Keep scanning other candidates.
      }
    }
  }

  const blocks = [];
  for (const source of sources) {
    blocks.push(...extractBlocksFromSource(source, terms, query));
  }
  const selected = blocks
    .sort((a, b) => b.score - a.score)
    .slice(0, maxBlocks);

  return {
    query,
    blocks: selected.map((item, index) => ({
      index: index + 1,
      score: item.score,
      source_macro: item.source.source_path,
      relative_path: item.source.relative_path,
      start_line: item.start_line,
      vba_block: item.block,
      python_add_to_history_template: [
        "project.model3d.add_to_history(",
        `    \"Adapted from ${item.source.relative_path ?? item.source.source_path}\",`,
        "    r'''",
        item.block,
        "    '''",
        ")"
      ].join("\n")
    }))
  };
}

function extractBlocksFromSource(source, terms, query) {
  const text = source.text.replace(/\r\n/g, "\n");
  const blocks = [];
  const regex = /^[ \t]*With[ \t]+[^\n]+[\s\S]*?^[ \t]*End With[ \t]*$/gim;
  let match;
  while ((match = regex.exec(text)) !== null) {
    const block = match[0];
    let score = scoreText(block, terms);
    if (/^[ \t]*With[ \t]+(Brick|Cylinder|Cone|Sphere|Wire|DiscretePort|WaveguidePort|Monitor|FarfieldPlot|Solver|Boundary|Mesh|Transform|Material|ResultTree)\b/im.test(block)) {
      score += 15;
    }
    if (score > 0 || query === "*") {
      blocks.push({
        source,
        score,
        start_line: lineNumberAt(text, match.index),
        block
      });
    }
  }
  if (blocks.length === 0) {
    const lines = text.split("\n");
    for (let i = 0; i < lines.length; i += 1) {
      if (scoreText(lines[i], terms) > 0) {
        const start = Math.max(0, i - 6);
        const end = Math.min(lines.length, i + 14);
        blocks.push({
          source,
          score: scoreText(lines.slice(start, end).join("\n"), terms),
          start_line: start + 1,
          block: lines.slice(start, end).join("\n")
        });
      }
    }
  }
  return blocks.filter((item) => !/Begin Dialog|End Dialog|UserDialog/i.test(item.block) || blocks.length === 1);
}

function lineNumberAt(text, index) {
  return text.slice(0, index).split("\n").length;
}

function safeRepoPath(requested, defaultRoot = repoRoot) {
  const full = path.isAbsolute(requested) ? path.resolve(requested) : path.resolve(defaultRoot, requested);
  if (!pathInside(full, repoRoot)) throw new Error(`Path must stay under repository root: ${repoRoot}`);
  return full;
}

function slug(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48) || "design";
}

function createVariant(args) {
  const savePolicy = args.save_policy ?? "no_save";
  if (!["no_save", "save_copy", "save_original"].includes(savePolicy)) throw new Error("Invalid save_policy.");
  const timestamp = nowIso().replace(/[:.]/g, "-");
  const designId = args.design_id || `design-${timestamp}`;
  const outputBase = args.output_dir ? safeRepoPath(args.output_dir) : recordsRoot;
  const dir = path.join(outputBase, `${timestamp}_${slug(designId)}`);
  if (!pathInside(dir, repoRoot)) throw new Error("output_dir must stay under repository root.");
  fs.mkdirSync(dir, { recursive: true });
  const manifest = {
    schema_version: "cstapi.design-manifest.v1",
    created_at: nowIso(),
    updated_at: nowIso(),
    project_path: args.project_path,
    save_policy: savePolicy,
    design_id: designId,
    parent_design_id: args.parent_design_id ?? null,
    objective: args.objective,
    operations: [],
    metrics: {},
    logs: [],
    artifacts: [],
    source_macros: [],
    warnings: [],
    errors: []
  };
  const manifestPath = path.join(dir, "manifest.json");
  fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  return { manifest_path: manifestPath, manifest };
}

function appendOperation(args) {
  const manifestPath = safeRepoPath(args.manifest_path);
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const operation = {
    recorded_at: nowIso(),
    ...args.operation
  };
  manifest.operations = Array.isArray(manifest.operations) ? manifest.operations : [];
  manifest.operations.push(operation);
  if (Array.isArray(operation.source_macros)) {
    const existing = new Set(Array.isArray(manifest.source_macros) ? manifest.source_macros : []);
    for (const item of operation.source_macros) existing.add(item);
    manifest.source_macros = [...existing];
  }
  if (operation.metrics && typeof operation.metrics === "object") {
    manifest.metrics = { ...(manifest.metrics ?? {}), ...operation.metrics };
  }
  if (operation.artifacts && Array.isArray(operation.artifacts)) {
    manifest.artifacts = [...(manifest.artifacts ?? []), ...operation.artifacts];
  }
  manifest.updated_at = nowIso();
  fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  return { manifest_path: manifestPath, appended: operation, manifest };
}

function defaultCstPython(args) {
  return args.python_executable || cstPaths.pythonExecutable || "python.exe";
}

function buildCstCommand(kind, args) {
  const python = defaultCstPython(args);
  const base = [python, cstHelperPath, kind, "--project", args.project_path];
  if (kind === "live-modify") {
    base.push("--parameter", args.parameter);
    base.push("--test-value", String(args.test_value));
    base.push("--pause-after-set", String(args.pause_after_set ?? 5));
    if (args.restore !== false) base.push("--restore");
    if (args.require_open !== false) base.push("--require-open");
  }
  return base;
}

function runProcess(argv, timeoutSec) {
  return new Promise((resolve) => {
    const started = Date.now();
    const child = spawn(argv[0], argv.slice(1), { cwd: repoRoot, windowsHide: true });
    let stdout = "";
    let stderr = "";
    const timeout = setTimeout(() => {
      child.kill();
    }, timeoutSec * 1000);
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("close", (code, signal) => {
      clearTimeout(timeout);
      resolve({
        command: argv,
        exit_code: code,
        signal,
        elapsed_ms: Date.now() - started,
        stdout,
        stderr
      });
    });
  });
}

async function cstClosedStart(args) {
  const command = buildCstCommand("closed-start", args);
  if (!args.execute) {
    return {
      execute: false,
      command,
      note: "Set execute=true to launch/connect CST and open the project. The helper does not save the project."
    };
  }
  return runProcess(command, safeNumber(args.timeout_sec, 180, 5, 3600));
}

async function cstLiveModify(args) {
  const command = buildCstCommand("live-modify", args);
  if (!args.execute) {
    return {
      execute: false,
      command,
      save_policy: "no_save",
      note: "Set execute=true to modify the live open CST project. The helper restores by default and does not save."
    };
  }
  return runProcess(command, safeNumber(args.timeout_sec, 300, 5, 7200));
}

async function callTool(name, args) {
  switch (name) {
    case "docs.search_macros":
      return searchMacros(args);
    case "docs.read_macro":
      return readMacro(args);
    case "docs.search_official_docs":
      return searchOfficialDocs(args);
    case "docs.read_official_doc":
      return readOfficialDoc(args);
    case "history.extract_pattern":
      return extractHistoryPattern(args);
    case "records.create_variant":
      return createVariant(args);
    case "records.append_operation":
      return appendOperation(args);
    case "cst.closed_start":
      return cstClosedStart(args);
    case "cst.live_modify_parameter":
      return cstLiveModify(args);
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}

function jsonContent(data) {
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(data, null, 2)
      }
    ]
  };
}

async function handleMessage(message) {
  if (!message || typeof message !== "object") return null;
  if (message.method?.startsWith("notifications/")) return null;

  try {
    if (message.method === "initialize") {
      return {
        jsonrpc: "2.0",
        id: message.id,
        result: {
          protocolVersion: "2024-11-05",
          capabilities: { tools: {} },
          serverInfo: { name: "cst2026-mcp", version: "0.1.0" }
        }
      };
    }
    if (message.method === "tools/list") {
      return { jsonrpc: "2.0", id: message.id, result: { tools } };
    }
    if (message.method === "tools/call") {
      const result = await callTool(message.params?.name, message.params?.arguments ?? {});
      return { jsonrpc: "2.0", id: message.id, result: jsonContent(result) };
    }
    return {
      jsonrpc: "2.0",
      id: message.id,
      error: { code: -32601, message: `Method not found: ${message.method}` }
    };
  } catch (error) {
    return {
      jsonrpc: "2.0",
      id: message.id,
      error: {
        code: -32000,
        message: error instanceof Error ? error.message : String(error)
      }
    };
  }
}

function sendMessage(message) {
  if (!message) return;
  const payload = JSON.stringify(message);
  if (framedTransport) {
    process.stdout.write(`Content-Length: ${Buffer.byteLength(payload, "utf8")}\r\n\r\n${payload}`);
  } else {
    process.stdout.write(`${payload}\n`);
  }
}

async function dispatch(raw) {
  if (!raw.trim()) return;
  const message = JSON.parse(raw);
  sendMessage(await handleMessage(message));
}

async function processInput() {
  while (inputBuffer.length > 0) {
    if (inputBuffer.startsWith("Content-Length:")) {
      framedTransport = true;
      const headerEnd = inputBuffer.indexOf("\r\n\r\n");
      if (headerEnd < 0) return;
      const header = inputBuffer.slice(0, headerEnd);
      const match = header.match(/Content-Length:\s*(\d+)/i);
      if (!match) throw new Error("Invalid Content-Length header.");
      const length = Number(match[1]);
      const start = headerEnd + 4;
      if (inputBuffer.length < start + length) return;
      const raw = inputBuffer.slice(start, start + length);
      inputBuffer = inputBuffer.slice(start + length);
      await dispatch(raw);
    } else {
      const newline = inputBuffer.indexOf("\n");
      if (newline < 0) return;
      const raw = inputBuffer.slice(0, newline);
      inputBuffer = inputBuffer.slice(newline + 1);
      await dispatch(raw);
    }
  }
}

process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  inputBuffer += chunk;
  processInput().catch((error) => {
    console.error(error);
  });
});
