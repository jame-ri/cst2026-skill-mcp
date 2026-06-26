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
const skillReferencesRoot = path.join(repoRoot, "skills", "cst-python-automation", "references");
const callRecipesPath = path.join(skillReferencesRoot, "cst-call-recipes.md");
const errorCookbookPath = path.join(skillReferencesRoot, "cst-error-cookbook.md");

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
    name: "cst.close_project",
    description: "Close a specified CST project with an explicit no-save, save-copy, or save-original policy to avoid modal save prompts.",
    inputSchema: {
      type: "object",
      properties: {
        project_path: { type: "string" },
        save_policy: { type: "string", enum: ["no_save", "save_copy", "save_original"], default: "no_save" },
        save_copy_path: { type: "string", description: "Required when save_policy is save_copy." },
        include_results: { type: "boolean", default: false },
        allow_overwrite: { type: "boolean", default: false },
        require_open: { type: "boolean", default: true },
        close_design_environment: { type: "boolean", default: false, description: "Close the DesignEnvironment after the project is closed. Use only for helper-owned hidden sessions." },
        python_executable: { type: "string" },
        execute: { type: "boolean", default: false },
        timeout_sec: { type: "integer", minimum: 5, maximum: 7200, default: 300 }
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
  },
  {
    name: "cst.inspect_project",
    description: "Read-only CST project inspection: open/running projects, project metadata, messages, model tree, and optional result tree.",
    inputSchema: {
      type: "object",
      properties: {
        project_path: { type: "string" },
        require_open: { type: "boolean", default: false, description: "If true, fail unless the target project is already open in CST." },
        include_results: { type: "boolean", default: true, description: "Also inspect saved cst.results result trees when possible." },
        max_tree_items: { type: "integer", minimum: 20, maximum: 5000, default: 300 },
        python_executable: { type: "string" },
        execute: { type: "boolean", default: false },
        timeout_sec: { type: "integer", minimum: 5, maximum: 7200, default: 300 }
      },
      required: ["project_path"]
    }
  },
  {
    name: "cst.inspect_geometry",
    description: "Read-only, tree-derived CST geometry inventory to support the Physical Structure Gate before modeling or mutation.",
    inputSchema: {
      type: "object",
      properties: {
        project_path: { type: "string" },
        require_open: { type: "boolean", default: false },
        max_tree_items: { type: "integer", minimum: 20, maximum: 5000, default: 500 },
        python_executable: { type: "string" },
        execute: { type: "boolean", default: false },
        timeout_sec: { type: "integer", minimum: 5, maximum: 7200, default: 300 }
      },
      required: ["project_path"]
    }
  },
  {
    name: "cst.inspect_physics_setup",
    description: "Read-only CST physics setup checklist for materials, ports, boundaries, mesh, monitors, solver/result paths, and messages.",
    inputSchema: {
      type: "object",
      properties: {
        project_path: { type: "string" },
        require_open: { type: "boolean", default: false },
        max_tree_items: { type: "integer", minimum: 20, maximum: 5000, default: 500 },
        python_executable: { type: "string" },
        execute: { type: "boolean", default: false },
        timeout_sec: { type: "integer", minimum: 5, maximum: 7200, default: 300 }
      },
      required: ["project_path"]
    }
  },
  {
    name: "cst.result_sanity",
    description: "Read saved CST result trees and perform compact sanity checks, especially passive S-parameter magnitude checks.",
    inputSchema: {
      type: "object",
      properties: {
        project_path: { type: "string" },
        tree_path: { type: "string", description: "Optional exact CST result-tree path. If omitted, S-parameter-like paths are auto-selected." },
        run_id: { type: "integer", minimum: 0, default: 0 },
        target_frequency: { type: "number", description: "Optional frequency value in the result item's native x-axis units." },
        passive: { type: "boolean", default: true, description: "Check that selected S-parameter magnitudes are <= 1 for passive structures." },
        max_tree_items: { type: "integer", minimum: 20, maximum: 5000, default: 500 },
        python_executable: { type: "string" },
        execute: { type: "boolean", default: false },
        timeout_sec: { type: "integer", minimum: 5, maximum: 7200, default: 300 }
      },
      required: ["project_path"]
    }
  },
  {
    name: "cst.process_status",
    description: "Inspect CST-related process, memory, and disk status before or during a long CST automation job.",
    inputSchema: {
      type: "object",
      properties: {
        project_path: { type: "string", description: "Optional project path used to choose the disk path for reporting." },
        work_dir: { type: "string", description: "Optional directory used for disk-space reporting." },
        pattern: { type: "array", items: { type: "string" }, description: "Optional process match patterns. Defaults to CST and CST helper patterns." },
        include_commandline: { type: "boolean", default: true },
        python_executable: { type: "string" },
        execute: { type: "boolean", default: false },
        timeout_sec: { type: "integer", minimum: 5, maximum: 300, default: 45 }
      }
    }
  },
  {
    name: "cst.preflight_resources",
    description: "Run a conservative resource gate before launching CST or a long solve: process count, free memory, and free disk.",
    inputSchema: {
      type: "object",
      properties: {
        project_path: { type: "string" },
        work_dir: { type: "string" },
        pattern: { type: "array", items: { type: "string" } },
        include_commandline: { type: "boolean", default: true },
        min_free_memory_gb: { type: "number", default: 8 },
        min_free_disk_gb: { type: "number", default: 10 },
        max_cst_processes: { type: "integer", minimum: 0, maximum: 100, default: 2 },
        max_single_cst_memory_gb: { type: "number", default: 48 },
        python_executable: { type: "string" },
        execute: { type: "boolean", default: false },
        timeout_sec: { type: "integer", minimum: 5, maximum: 300, default: 60 }
      }
    }
  },
  {
    name: "cst.job_checkpoint",
    description: "Create or append a CST job checkpoint for resumable multi-step CST automation.",
    inputSchema: {
      type: "object",
      properties: {
        manifest_path: { type: "string", description: "Existing job manifest path. If omitted, job_id is used under design-records/jobs." },
        job_id: { type: "string" },
        project_path: { type: "string" },
        stage: { type: "string", description: "Current stage, for example preflight, geometry, physics, solve, result_read." },
        status: { type: "string", enum: ["pending", "running", "done", "failed", "interrupted", "recovered"] },
        detail: { type: "string" },
        operation: { type: "object" },
        metrics: { type: "object" },
        artifacts: { type: "array", items: { type: "object" } },
        warnings: { type: "array", items: { type: "string" } },
        errors: { type: "array", items: { type: "string" } },
        resource_snapshot: { type: "object" },
        cst_pids: { type: "array", items: { type: "integer" } }
      },
      required: ["stage", "status"]
    }
  },
  {
    name: "cst.recover_job",
    description: "Read a CST job checkpoint manifest and recommend the safest resume point after interruption or crash.",
    inputSchema: {
      type: "object",
      properties: {
        manifest_path: { type: "string" },
        job_id: { type: "string" }
      }
    }
  },
  {
    name: "cst.cleanup_stale_processes",
    description: "Plan or explicitly terminate stale CST-related PIDs. This never kills by name; PIDs and allow_terminate are required for execution.",
    inputSchema: {
      type: "object",
      properties: {
        pids: { type: "array", items: { type: "integer" }, minItems: 1 },
        allow_terminate: { type: "boolean", default: false },
        force: { type: "boolean", default: false },
        python_executable: { type: "string" },
        execute: { type: "boolean", default: false },
        timeout_sec: { type: "integer", minimum: 5, maximum: 300, default: 60 }
      },
      required: ["pids"]
    }
  },
  {
    name: "knowledge.list_categories",
    description: "List CST automation recipe categories available from the installed skill knowledge base.",
    inputSchema: {
      type: "object",
      properties: {}
    }
  },
  {
    name: "knowledge.get_recipe",
    description: "Read one CST automation call recipe by category before rediscovering macro or History patterns.",
    inputSchema: {
      type: "object",
      properties: {
        category: { type: "string", description: "Recipe category such as ports, boolean, solver, materials, or structure-understanding." },
        max_chars: { type: "integer", minimum: 500, maximum: 50000, default: 12000 }
      },
      required: ["category"]
    }
  },
  {
    name: "knowledge.search_lessons",
    description: "Search CST recipes and error-cookbook lessons for known failure modes and correct call sequences.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Search terms such as Untitled Project.close, DiscretePort waveguide, Update Manager, Boolean, or StoreParameter." },
        limit: { type: "integer", minimum: 1, maximum: 50, default: 10 },
        max_chars: { type: "integer", minimum: 200, maximum: 20000, default: 4000 }
      },
      required: ["query"]
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

function knowledgeFiles() {
  return [
    { source: "cst-call-recipes", path: callRecipesPath },
    { source: "cst-error-cookbook", path: errorCookbookPath }
  ];
}

function markdownSections(filePath, source) {
  if (!pathInside(filePath, skillReferencesRoot)) {
    throw new Error("Knowledge file path must stay under the CST skill references directory.");
  }
  const raw = readTextFile(filePath, 200000).text;
  const lines = raw.split(/\r?\n/);
  const sections = [];
  let current = null;
  for (const line of lines) {
    const match = line.match(/^##\s+(.+?)\s*$/);
    if (match) {
      if (current) sections.push(current);
      current = {
        source,
        heading: match[1].trim(),
        text: `${line}\n`
      };
    } else if (current) {
      current.text += `${line}\n`;
    }
  }
  if (current) sections.push(current);
  return sections;
}

function recipeSections() {
  return markdownSections(callRecipesPath, "cst-call-recipes");
}

function allKnowledgeSections() {
  return knowledgeFiles().flatMap((file) => markdownSections(file.path, file.source));
}

function normalizeHeading(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/^lesson:\s*/, "");
}

function sectionSummary(text) {
  const purpose = text.match(/Purpose:\s*([^\n]+)/i);
  if (purpose) return purpose[1].trim();
  const symptoms = text.match(/Symptoms:\s*\n\s*-\s*([^\n]+)/i);
  if (symptoms) return symptoms[1].trim();
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line && !line.startsWith("#")) ?? "";
}

function listKnowledgeCategories() {
  const categories = recipeSections().map((section) => ({
    category: normalizeHeading(section.heading),
    heading: section.heading,
    summary: sectionSummary(section.text)
  }));
  return {
    source_path: path.relative(repoRoot, callRecipesPath),
    categories: categories.map((item) => item.category),
    entries: categories
  };
}

function getKnowledgeRecipe(args) {
  const category = normalizeHeading(args.category);
  const maxChars = safeNumber(args.max_chars, 12000, 500, 50000);
  const sections = recipeSections();
  const section = sections.find((item) => normalizeHeading(item.heading) === category);
  if (!section) {
    return {
      category,
      found: false,
      available_categories: sections.map((item) => normalizeHeading(item.heading))
    };
  }
  const truncated = section.text.length > maxChars;
  return {
    category,
    found: true,
    source_path: path.relative(repoRoot, callRecipesPath),
    chars: section.text.length,
    truncated,
    text: truncated ? section.text.slice(0, maxChars) : section.text
  };
}

function searchKnowledgeLessons(args) {
  const query = String(args.query ?? "").trim();
  const terms = splitTerms(query);
  const limit = safeNumber(args.limit, 10, 1, 50);
  const maxChars = safeNumber(args.max_chars, 4000, 200, 20000);
  const matches = allKnowledgeSections()
    .map((section) => {
      const haystack = `${section.source} ${section.heading} ${section.text}`;
      return { section, score: scoreText(haystack, terms) };
    })
    .filter((item) => item.score > 0 || query === "*")
    .sort((a, b) => b.score - a.score || a.section.heading.localeCompare(b.section.heading))
    .slice(0, limit)
    .map(({ section, score }) => {
      const truncated = section.text.length > maxChars;
      return {
        score,
        source: section.source,
        heading: section.heading,
        key: normalizeHeading(section.heading),
        text: truncated ? section.text.slice(0, maxChars) : section.text,
        truncated
      };
    });
  return {
    query,
    count: matches.length,
    matches
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
    physical_structure: {},
    physics_setup: {},
    job_status: "new",
    checkpoints: [],
    resource_guard: {},
    recovery: {},
    operations: [],
    metrics: {},
    sanity_checks: {},
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

function jobRoot() {
  const root = path.join(recordsRoot, "jobs");
  fs.mkdirSync(root, { recursive: true });
  return root;
}

function resolveJobManifest(args, createIfMissing = false) {
  if (args.manifest_path) {
    const manifestPath = safeRepoPath(args.manifest_path);
    if (!fs.existsSync(manifestPath) && !createIfMissing) throw new Error(`Job manifest not found: ${manifestPath}`);
    return manifestPath;
  }
  const jobId = args.job_id || `job-${nowIso().replace(/[:.]/g, "-")}`;
  const dir = path.join(jobRoot(), slug(jobId));
  if (!pathInside(dir, repoRoot)) throw new Error("job_id resolved outside repository.");
  if (createIfMissing) fs.mkdirSync(dir, { recursive: true });
  const manifestPath = path.join(dir, "job.json");
  if (!fs.existsSync(manifestPath) && !createIfMissing) throw new Error(`Job manifest not found for job_id: ${jobId}`);
  return manifestPath;
}

function readJsonIfExists(filePath, fallback) {
  if (!fs.existsSync(filePath)) return fallback;
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function cstJobCheckpoint(args) {
  const manifestPath = resolveJobManifest(args, true);
  const manifest = readJsonIfExists(manifestPath, {
    schema_version: "cstapi.job-manifest.v1",
    created_at: nowIso(),
    job_id: args.job_id || path.basename(path.dirname(manifestPath)),
    project_path: args.project_path ?? null,
    checkpoints: [],
    warnings: [],
    errors: []
  });
  const checkpoint = {
    recorded_at: nowIso(),
    stage: args.stage,
    status: args.status,
    project_path: args.project_path ?? manifest.project_path ?? null,
    detail: args.detail ?? null,
    operation: args.operation ?? {},
    metrics: args.metrics ?? {},
    artifacts: Array.isArray(args.artifacts) ? args.artifacts : [],
    warnings: Array.isArray(args.warnings) ? args.warnings : [],
    errors: Array.isArray(args.errors) ? args.errors : [],
    resource_snapshot: args.resource_snapshot ?? {},
    cst_pids: Array.isArray(args.cst_pids) ? args.cst_pids : []
  };
  manifest.project_path = checkpoint.project_path;
  manifest.updated_at = nowIso();
  manifest.current_stage = checkpoint.stage;
  manifest.current_status = checkpoint.status;
  manifest.checkpoints = Array.isArray(manifest.checkpoints) ? manifest.checkpoints : [];
  manifest.checkpoints.push(checkpoint);
  if (checkpoint.status === "done") {
    manifest.last_completed_stage = checkpoint.stage;
    manifest.last_completed_at = checkpoint.recorded_at;
  }
  if (["failed", "interrupted"].includes(checkpoint.status)) {
    manifest.last_failure = checkpoint;
  }
  manifest.warnings = [...(manifest.warnings ?? []), ...checkpoint.warnings];
  manifest.errors = [...(manifest.errors ?? []), ...checkpoint.errors];
  fs.mkdirSync(path.dirname(manifestPath), { recursive: true });
  fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  return { manifest_path: manifestPath, checkpoint, manifest };
}

function cstRecoverJob(args) {
  const manifestPath = resolveJobManifest(args, false);
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const checkpoints = Array.isArray(manifest.checkpoints) ? manifest.checkpoints : [];
  const last = checkpoints.at(-1) ?? null;
  const lastDone = [...checkpoints].reverse().find((item) => item.status === "done") ?? null;
  const failed = [...checkpoints].reverse().find((item) => ["failed", "interrupted"].includes(item.status)) ?? null;
  let recommendation = "No checkpoints exist yet. Start with preflight_resources and record a running checkpoint.";
  if (last) {
    if (last.status === "done") {
      recommendation = `Last checkpoint '${last.stage}' is done. Resume at the next planned stage after verifying resources.`;
    } else if (last.status === "running") {
      recommendation = `Last checkpoint '${last.stage}' was still running. Inspect process_status and CST result/messages before marking it recovered, done, or interrupted.`;
    } else if (["failed", "interrupted"].includes(last.status)) {
      recommendation = lastDone
        ? `Resume from the last completed stage '${lastDone.stage}', then rerun or repair '${last.stage}' after preflight.`
        : `No completed checkpoint exists. Restart from preflight and use a project copy.`;
    } else if (last.status === "recovered") {
      recommendation = `Recovery checkpoint exists for '${last.stage}'. Continue with the next planned stage after sanity checks.`;
    }
  }
  return {
    manifest_path: manifestPath,
    job_id: manifest.job_id ?? null,
    project_path: manifest.project_path ?? null,
    current_stage: manifest.current_stage ?? last?.stage ?? null,
    current_status: manifest.current_status ?? last?.status ?? null,
    last_checkpoint: last,
    last_completed_checkpoint: lastDone,
    last_failure: failed,
    checkpoint_count: checkpoints.length,
    recommendation,
    manifest
  };
}

function defaultCstPython(args) {
  return args.python_executable || cstPaths.pythonExecutable || "python.exe";
}

function buildCstCommand(kind, args) {
  const python = defaultCstPython(args);
  const base = [python, cstHelperPath, kind];
  if (args.project_path) base.push("--project", args.project_path);
  if (kind === "close-project") {
    base.push("--save-policy", args.save_policy ?? "no_save");
    if (args.save_copy_path) base.push("--save-copy-path", String(args.save_copy_path));
    if (args.include_results === true) base.push("--include-results");
    if (args.allow_overwrite === true) base.push("--allow-overwrite");
    if (args.require_open !== false) base.push("--require-open");
    if (args.close_design_environment === true) base.push("--close-design-environment");
  }
  if (kind === "live-modify") {
    base.push("--parameter", args.parameter);
    base.push("--test-value", String(args.test_value));
    base.push("--pause-after-set", String(args.pause_after_set ?? 5));
    if (args.restore !== false) base.push("--restore");
    if (args.require_open !== false) base.push("--require-open");
  }
  if (kind === "inspect-project") {
    if (args.require_open === true) base.push("--require-open");
    if (args.include_results !== false) base.push("--include-results");
    base.push("--max-tree-items", String(safeNumber(args.max_tree_items, 300, 20, 5000)));
  }
  if (kind === "inspect-geometry" || kind === "inspect-physics") {
    if (args.require_open === true) base.push("--require-open");
    base.push("--max-tree-items", String(safeNumber(args.max_tree_items, 500, 20, 5000)));
  }
  if (kind === "result-sanity") {
    if (args.tree_path) base.push("--tree-path", String(args.tree_path));
    if (args.run_id !== undefined) base.push("--run-id", String(safeNumber(args.run_id, 0, 0, 1000000)));
    if (args.target_frequency !== undefined && args.target_frequency !== null) base.push("--target-frequency", String(args.target_frequency));
    if (args.passive !== false) base.push("--passive");
    base.push("--max-tree-items", String(safeNumber(args.max_tree_items, 500, 20, 5000)));
  }
  if (kind === "process-status") {
    if (args.work_dir) base.push("--work-dir", String(args.work_dir));
    if (args.include_commandline !== false) base.push("--include-commandline");
    if (Array.isArray(args.pattern)) {
      for (const pattern of args.pattern) base.push("--pattern", String(pattern));
    }
  }
  if (kind === "preflight-resources") {
    if (args.work_dir) base.push("--work-dir", String(args.work_dir));
    if (args.include_commandline !== false) base.push("--include-commandline");
    if (Array.isArray(args.pattern)) {
      for (const pattern of args.pattern) base.push("--pattern", String(pattern));
    }
    base.push("--min-free-memory-gb", String(safeNumber(args.min_free_memory_gb, 8, 0, 100000)));
    base.push("--min-free-disk-gb", String(safeNumber(args.min_free_disk_gb, 10, 0, 100000)));
    base.push("--max-cst-processes", String(safeNumber(args.max_cst_processes, 2, 0, 100)));
    base.push("--max-single-cst-memory-gb", String(safeNumber(args.max_single_cst_memory_gb, 48, 0, 100000)));
  }
  if (kind === "cleanup-stale-processes") {
    if (Array.isArray(args.pids)) {
      for (const pid of args.pids) base.push("--pid", String(pid));
    }
    if (args.allow_terminate === true) base.push("--allow-terminate");
    if (args.force === true) base.push("--force");
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

async function cstCloseProject(args) {
  const command = buildCstCommand("close-project", args);
  if (!args.execute) {
    return {
      execute: false,
      command,
      save_policy: args.save_policy ?? "no_save",
      note: "Set execute=true to close the specified CST project. save_copy requires save_copy_path; no_save uses Project.close() to avoid GUI save prompts."
    };
  }
  if ((args.save_policy ?? "no_save") === "save_copy" && !args.save_copy_path) {
    return {
      execute: false,
      blocked: true,
      command,
      save_policy: "save_copy",
      note: "Refusing save_copy without save_copy_path."
    };
  }
  return runProcess(command, safeNumber(args.timeout_sec, 300, 5, 7200));
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

async function cstReadOnlyHelper(kind, args, note, timeoutDefault = 300) {
  const command = buildCstCommand(kind, args);
  if (!args.execute) {
    return {
      execute: false,
      command,
      save_policy: "no_save",
      note
    };
  }
  return runProcess(command, safeNumber(args.timeout_sec, timeoutDefault, 5, 7200));
}

async function cstInspectProject(args) {
  return cstReadOnlyHelper(
    "inspect-project",
    args,
    "Set execute=true to perform read-only project inspection. This can open/connect CST but does not save the project."
  );
}

async function cstInspectGeometry(args) {
  return cstReadOnlyHelper(
    "inspect-geometry",
    args,
    "Set execute=true to inspect accessible model-tree evidence before geometry mutation. This helper does not save the project."
  );
}

async function cstInspectPhysics(args) {
  return cstReadOnlyHelper(
    "inspect-physics",
    args,
    "Set execute=true to inspect accessible materials/ports/boundaries/mesh/monitor/result evidence before solving. This helper does not save."
  );
}

async function cstResultSanity(args) {
  return cstReadOnlyHelper(
    "result-sanity",
    args,
    "Set execute=true to read saved CST results and run sanity checks. This helper uses cst.results and does not save the project."
  );
}

async function cstProcessStatus(args) {
  return cstReadOnlyHelper(
    "process-status",
    args,
    "Set execute=true to inspect CST-related process, memory, and disk state. This helper does not modify CST.",
    45
  );
}

async function cstPreflightResources(args) {
  return cstReadOnlyHelper(
    "preflight-resources",
    args,
    "Set execute=true to run the resource gate before starting or resuming a CST job. This helper does not modify CST.",
    60
  );
}

async function cstCleanupStaleProcesses(args) {
  const command = buildCstCommand("cleanup-stale-processes", args);
  if (!args.execute) {
    return {
      execute: false,
      command,
      save_policy: "no_save",
      note: "Set execute=true and allow_terminate=true to terminate only the explicit PIDs listed in pids. This never kills by name."
    };
  }
  if (args.allow_terminate !== true) {
    return {
      execute: false,
      blocked: true,
      command,
      save_policy: "no_save",
      note: "Refusing to terminate processes without allow_terminate=true."
    };
  }
  return runProcess(command, safeNumber(args.timeout_sec, 60, 5, 300));
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
    case "cst.close_project":
      return cstCloseProject(args);
    case "cst.live_modify_parameter":
      return cstLiveModify(args);
    case "cst.inspect_project":
      return cstInspectProject(args);
    case "cst.inspect_geometry":
      return cstInspectGeometry(args);
    case "cst.inspect_physics_setup":
      return cstInspectPhysics(args);
    case "cst.result_sanity":
      return cstResultSanity(args);
    case "cst.process_status":
      return cstProcessStatus(args);
    case "cst.preflight_resources":
      return cstPreflightResources(args);
    case "cst.job_checkpoint":
      return cstJobCheckpoint(args);
    case "cst.recover_job":
      return cstRecoverJob(args);
    case "cst.cleanup_stale_processes":
      return cstCleanupStaleProcesses(args);
    case "knowledge.list_categories":
      return listKnowledgeCategories(args);
    case "knowledge.get_recipe":
      return getKnowledgeRecipe(args);
    case "knowledge.search_lessons":
      return searchKnowledgeLessons(args);
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
