# CST Macro Library Usage Guide

## Purpose

`D:\CST\Library\Macros` is the macro/script library installed with CST. Treat it as an official pattern library for VBA and History commands. Do not blindly run full macros as black boxes. Search for a relevant macro, inspect the source, extract reliable command blocks, parameterize them, and inject them into the current project.

## When To Search The Macro Library

Search `macro-library/macro-inventory.csv` when:

- You do not know the CST VBA syntax for an object such as `DiscreteFacePort`, `FarfieldArray`, `MeshSettings`, or `ResultTree`.
- You need complex geometry examples such as dipoles, horns, waveguide arrays, filters, spiral coils, or reflectors.
- You need examples for ports, monitors, farfields, S-parameter import/export, Touchstone, or result-tree operations.
- You need solver, mesh, HPC, optimization, or broadband-monitor macro patterns.
- You need to convert a CST GUI macro workflow into Python automation.

## Search The Index

PowerShell:

```powershell
Import-Csv D:\CSTapi\macro-library\macro-inventory.csv |
  Where-Object { $_.keywords -match 'Farfield|Monitor|DiscretePort' } |
  Select-Object category,subcategory,title,applications,source_path
```

Or with `rg`:

```powershell
rg -n "Farfield|DiscretePort|WaveguidePort|S-Parameter|Optimizer" D:\CSTapi\macro-library\macro-inventory.csv
```

After finding a candidate, open the original macro:

```powershell
Get-Content -Encoding Default -Path "D:\CST\Library\Macros\Construct\Demo Examples\Dipole Antenna^+MWS.mcs" -TotalCount 220
```

## Filename Suffixes

Common form:

```text
Macro Title^+MWS+DS.mcr
Macro Title^-DS.mcs
```

Meaning:

- `^+...`: usually visible in the CST macro menu.
- `^-...`: usually hidden or internal, but still useful as a syntax reference.
- `MWS`: Microwave Studio / 3D high-frequency EM.
- `DS`: Design Studio / schematic.
- `EMS`: low-frequency/electromagnetic workflows.
- `PS`: Particle Studio.
- `MPS`: Multiphysics Studio.
- `WIN`: Windows/external-tool workflow.

Do not rely only on the suffix. Inspect the macro and the active project module.

## Preferred Calling Strategy

### Preferred: Extract History/VBA Blocks

Best for geometry, ports, materials, boundaries, monitors, mesh, and solver settings.

Workflow:

1. Open the relevant `.mcr` or `.mcs`.
2. Locate `With ... End With`, `AddToHistory`, `StoreParameter`, or `ResultTree` patterns.
3. Remove interactive `Dialog`, `MsgBox`, and `GetFilePath` code unless explicitly needed.
4. Convert constants into parameters.
5. Inject with `project.model3d.add_to_history(caption, vba_code)`.
6. Record `source_macro`, `adapted_caption`, parameters, and design intent.

Python pattern:

```python
def add_history(project, caption, lines):
    project.model3d.add_to_history(caption, "\n".join(lines) + "\n")

add_history(project, "M0007 add farfield monitor from macro pattern", [
    "With Monitor",
    "    .Reset",
    '    .Name "farfield (f=fmon)"',
    '    .Domain "Frequency"',
    '    .FieldType "Farfield"',
    '    .MonitorValue "fmon"',
    "    .Create",
    "End With",
])
```

### Secondary: Run Installed Macros

Use this only when the user explicitly wants the installed CST macro workflow or when the macro performs complex import/export wizard behavior.

VBA pattern:

```vb
RunScript GetInstallPath + "\Library\Macros\Results\- Import and Export\Import Touchstone File^+MWS+DS.mcr"
```

Notes:

- Many installed macros depend on GUI dialogs and are unsuitable for unattended optimization.
- Many macros read/write the current project or result directory; run them only on project copies by default.
- Record `source_path` and expected output before running.

## Common Macro Source Patterns

- `Sub Main()`: macro entry point.
- `BeginHide ... EndHide`: hidden initialization or GUI handling in History.
- `Begin Dialog UserDialog ...`: interactive dialog; usually replace with parameters for automation.
- `assign "var"`: writes variables into History for CST rebuild replay.
- `StoreParameter` / `StoreParameterWithDescription`: writes CST parameters.
- `AddToHistory "caption", sCommand`: appends a command block to History.
- `With Brick` / `With Cylinder` / `With Transform`: geometry modeling.
- `With DiscretePort` / `With DiscreteFacePort` / `With WaveguidePort`: port setup.
- `With Monitor`: field/farfield/powerflow monitors.
- `ResultTree` / `DSResultTree`: result-tree query and insertion.

## Safety Rules

- Do not run macros against the user's original project by default; create a job copy first.
- Do not put GUI-dialog macros directly into batch optimization loops.
- Do not copy unrelated macro sections into an automation block; they may carry hidden side effects.
- Avoid `GetFilePath`, `MsgBox`, clipboard operations, and external `.exe` calls unless the user explicitly needs them.
- Before structural edits, record `design_id`, `parent_design_id`, and `mutation_id`.
- Whenever a macro is used as a reference, record `source_macro`.

## Operation Record Template

```json
{
  "operation": "add_farfield_monitor",
  "source_macro": "D:/CST/Library/Macros/Solver/Monitors and Probes/Broadband Field Monitors^+MWS+PS.mcr",
  "adapted_caption": "M0007 add farfield monitor",
  "method": "extract_history_vba",
  "parameters": {"fmon": "3.5"},
  "target_project": "runs/.../project.cst",
  "rebuild_status": "completed"
}
```

