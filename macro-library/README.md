# CST Macro Library Index

This directory is a model-readable index for the installed CST macro library at:

`D:\CST\Library\Macros`

It does not duplicate the full macro source tree. Instead, it records metadata and usage guidance so an agent can quickly find relevant CST VBA/History examples, open the original macro only when needed, and adapt safe snippets into Python-driven CST automation.

## Generated Index Files

- `macro-inventory.csv`: Searchable table of CST macro-library files, including scripts and companion resources.
- `macro-inventory.json`: Same inventory in JSON form.
- `macro-category-summary.csv`: Counts by top-level macro category.

Important columns in `macro-inventory.csv`:

- `category`: Top-level CST macro folder, such as `Construct`, `Solver`, `Results`.
- `subcategory`: Nested folder path inside the category.
- `title`: Macro title parsed from the filename before the `^` suffix.
- `applications`: Parsed CST module hints such as `MWS`, `DS`, `EMS`, `PS`, `MPS`, `WIN`.
- `visibility`: `menu-visible` for `^+...`, `hidden/internal` for `^-...`.
- `keywords`: Detected CST API objects and concepts, such as `Brick`, `DiscretePort`, `Farfield`, `ResultTree`, `Solver`.
- `first_comment`: First useful comment line from the macro.
- `source_path`: Original macro path under `D:\CST\Library\Macros`.

When searching for executable script patterns, filter `extension` to `mcr`, `mcs`, `bas`, `cls`, or `py`. Other rows such as `bmp`, `pdf`, `ppt`, `txt`, and `cst` are companion resources that explain or support the macros.

## Human/Agent Guides

- Chinese usage guide: `cst-macro-usage.zh-CN.md`
- English usage guide: `cst-macro-usage.en.md`
- Chinese catalog: `macro-catalog.zh-CN.md`
- English catalog: `macro-catalog.en.md`

## Recommended Search Flow

1. Search `macro-inventory.csv` for the desired CST operation, module, keyword, or macro title.
2. Open the original macro from `source_path`.
3. Prefer reusable History/VBA blocks such as `With Brick`, `With Monitor`, `With DiscretePort`, `With Solver`, `With ResultTree`.
4. Avoid copying full interactive macros into automation unless the task explicitly needs the original CST dialog workflow.
5. Convert extracted snippets into parameterized Python strings and inject them with `project.model3d.add_to_history()`.
6. Record the source macro path and adapted operation in the design/trial manifest.
