# Environment and portable paths

This file defines configuration rules, not a cache of one machine's paths.

## Roots

The existing MCP server locates the repository from its own package location.
Repository-relative references are anchored there, not to the agent's current
shell directory. Documentation links are relative to the document containing them.
The installed skill can live elsewhere; connect it to the intended MCP repository.

Use projects/example.cst, design-records/run/manifest.json, or official-docs/...
as portable references. Do not copy absolute paths into skills, shared records,
examples, or reusable procedures. The filesystem adapter may resolve absolute
paths internally when the operating system or CST API requires them.

Installation Help references may use a source_root of cst_install and a path
relative to that installation. Repository evidence uses the repository root.
Do not confuse a source's root label with a physical folder in the repository.

## Configuration consumed by the existing server

| Variable | Meaning |
| --- | --- |
| CST_INSTALL_DIR | Machine-local CST installation binding |
| CST_PYTHON_EXE | Machine-local interpreter capable of importing CST libraries |
| CST_MACRO_ROOT | Machine-local installed macro library binding |
| CST_DESIGN_ENV_EXE | Machine-local CST executable binding for discovery/diagnostics |
| CST_KNOWLEDGE_DIR | Repository-relative learned store, default design-records/knowledge |
| CST_KNOWLEDGE_ENABLED | Set 0 to disable learned storage and retrieval |
| CST_KNOWLEDGE_AUTO_CAPTURE | Set 0 to require explicit capture |
| CST_KNOWLEDGE_STABLE_RUNS | Stable threshold, integer 2-100; default 2 |

Keep installation bindings in the agent/server's local environment, outside
versioned skill content. Do not assume shell interpolation works in MCP JSON or
that every agent accepts the same configuration format. Use its supported
configuration adapter and discover the resulting tools.

Legacy CST_API_ROOT, CST_MCP_ROOT, CST_OFFICIAL_DOCS and CST_MACRO_LIBRARY aliases
do not relocate the current server's repository or override its knowledge roots.
Use the supported bindings above instead of inventing a configuration field.

## Path or startup failure

1. Check the active server/interpreter configuration and the specific missing path.
2. Prefer a task-local correction. Change persistent user settings only when asked.
3. Restart the MCP server after changing its startup environment or code.
4. Check tool availability and whether a returned inspection was actually executed.

Do not fall back to cached paths from another machine, recursively scan disks, or
report a successful CST import without evidence. The Node knowledge/reference
tools can run without CST; live simulation still requires a supported installation.
