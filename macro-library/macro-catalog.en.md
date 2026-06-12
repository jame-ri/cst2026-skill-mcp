# CST Macro Library Catalog

## Overview

The current index was generated from `D:\CST\Library\Macros` and records 414 macro-library files, including scripts such as `.mcr`, `.mcs`, `.bas`, `.cls`, and `.py`, plus companion resources such as images, PDFs, presentations, text files, and example projects. When only executable script patterns are needed, filter `extension` to `mcr`, `mcs`, `bas`, `cls`, or `py`.

See `macro-category-summary.csv` for counts by category:

- `Calculate`: calculators for lines, waveguides, materials, heat transfer, and related utilities.
- `Construct`: geometry construction, demo examples, ports, coils, FastHenry, reflectors, and discrete ports.
- `Converter` / `File`: ADS, Gerber, GDSII, DXF, SPICE, Touchstone, and file conversion helpers.
- `Matching Circuits`: matching circuits, Optenni, and Mini Match workflows.
- `Materials`: Drude, Cole-Cole, Graphene, Tensor, Biological tissue, and Tabulated Surface Impedance materials.
- `Parameters`: parameter copying, solid participation switches, and mesh preservation on parameter changes.
- `Results`: S-parameters, Touchstone, Farfield, EMC, TDR/Eye, tables, and 2D/3D post-processing.
- `Solver`: A/F/I/T/M solvers, ports, mesh, sources, monitors, optimization, and HPC.
- `Wizard`: 5G tools, data import, solver comparison, archive tools, and Via Wizard.

## High-Value Entry Points For Antenna/EM Automation

### Modeling Examples

Search:

```powershell
rg -n "Dipole|Horn|Waveguide|Microstrip|Reflector|Filter" D:\CSTapi\macro-library\macro-inventory.csv
```

Useful examples:

- `Construct\Demo Examples\Dipole Antenna^+MWS.mcs`
- `Construct\Demo Examples\Horn antenna^+MWS.mcs`
- `Construct\Demo Examples\Waveguide Array^+MWS.mcs`
- `Construct\Demo Examples\Waveguide Iris Filter^+MWS.mcs`
- `Construct\Demo Examples\Microstrip with Bondwire^+MWS.mcs`
- `Construct\Parts\Reflector dish^+MWS.mcs`

Use them to learn parameterized modeling, `StoreParameter`, `Component.New`, `Brick`, `Cylinder`, `Transform`, `WCS`, `Pick`, `DiscreteFacePort`, boundaries, monitors, mesh, and solver setup.

### Ports And Feeds

Search:

```powershell
rg -n "DiscretePort|DiscreteFacePort|WaveguidePort|Port Mode|Target Cut Off" D:\CSTapi\macro-library\macro-inventory.csv
```

Entry points:

- `Construct\Discrete Ports\Discrete port with lumped element^+MWS.mcr`
- `Construct\Discrete Ports\Multiple discrete Ports^+MWS.mcr`
- `Construct\Discrete Ports\Convert Discrete Edge Port to Discrete Face Port^+MWS.mcs`
- `Solver\Ports\Set Port Mode Evaluation Frequency^+MWS+PS.mcr`
- `Solver\Ports\Set Port Target Cut Off Frequency^+MWS+PS.mcr`
- `Solver\Ports\Set S-parameter symmetries - discrete ports^+MWS.mcr`

Use them to learn discrete ports, discrete face ports, waveguide ports, and port-mode settings.

### Monitors And Farfields

Search:

```powershell
rg -n "Farfield|Monitor|Probe|Broadband|TRP|TIS" D:\CSTapi\macro-library\macro-inventory.csv
```

Entry points:

- `Solver\Monitors and Probes\Broadband Field Monitors^+MWS+PS.mcr`
- `Solver\Monitors and Probes\Farfield Monitors - Activate fast Combine Results^+MWS.mcr`
- `Results\Farfield\Show Total Radiated Power (TRP)^+MWS.mcr`
- `Results\Farfield\Show Total Isotropic Sensitivity (TIS)^+MWS.mcr`
- `Results\Farfield\Generate 3D Radar Range Pattern^+MWS.mcr`
- `Results\- Import and Export\Export Farfield in GRASP format^+MWS.mcr`
- `Results\- Import and Export\Import Farfield from HFSS^+MWS.mcr`
- `Results\- Import and Export\Import Farfield from FEKO^+MWS.mcr`

Use them to set up farfield monitors, broadband monitors, TRP/TIS post-processing, and farfield import/export.

### S-Parameters And Results

Search:

```powershell
rg -n "S-Parameter|Touchstone|ResultTree|Result1D|Q-values|MDIF" D:\CSTapi\macro-library\macro-inventory.csv
```

Entry points:

- `Results\1D Results\Measure Resonances and Q-values from frq-data^+MWS.mcs`
- `Results\1D Results\Recalculate S-Parameter with new Frq-Sampling^+MWS.mcr`
- `Results\- Import and Export\Import Touchstone File^+MWS+DS.mcr`
- `Results\- Import and Export\Export MDIF File (for AWR and ADS)^+MWS.mcr`
- `Results\- Import and Export\Export S-Parameters to Modelica^+MWS+DS.mcr`
- `Results\Tables\Get Min Max Value of 0D Table^-DS.mcr`
- `Results\Tables\Parametric xy Plot from 0D Tables.mcr`

Use them to learn result-tree traversal, S-parameter processing, Touchstone import/export, resonance and Q-value detection, and table handling. For automated metric extraction, prefer `cst.results` when possible.

### Solver, Mesh, Optimization

Search:

```powershell
rg -n "Solver|Mesh|Optimizer|Broad Band Sweep|GPU|HPC|Unitcell" D:\CSTapi\macro-library\macro-inventory.csv
```

Entry points:

- `Solver\A-Solver\Activate Broad Band Sweep^+MWS.mcr`
- `Solver\F-Solver\Change settings from Full Array to Unitcell^+MWS.mcr`
- `Solver\Mesh\TET Meshing - Robust Volume Meshing^-DS.mcr`
- `Solver\Mesh\Surface Meshing - Enable accurate Wire meshing^+MWS.mcr`
- `Solver\Optimization\DOE (Design of Experiments)^-DS.mcr`
- `Solver\Optimization\Non-Parametric Optimizer Settings^+MWS+EMS.mcr`
- `Solver\High Performance Computing\Check GPU Computing Setup^+MWS+PS.mcr`
- `Wizard\Compare Solvers^+DS.mcr`

Use them to learn solver switching, mesh settings, optimizer settings, and HPC checks. Long simulations and optimizations must use copied projects and recorded trials.

### Materials

Search:

```powershell
rg -n "Drude|Graphene|Tensor|Cole-Cole|Tissue|Surface Impedance|Material" D:\CSTapi\macro-library\macro-inventory.csv
```

Entry points:

- `Materials\Create Drude Material for Optical Applications^+MWS+PS.mcr`
- `Materials\Create Drude Material for Plasma Applications^+MWS+PS.mcr`
- `Materials\Create Graphene Material for Optical Applications^+MWS+PS.mcr`
- `Materials\Create Full Tensor Material^+MWS.mcr`
- `Materials\Create Cole-Cole Model Material^+MWS+PS.mcr`
- `Materials\Create Tabulated Surface Impedance Material^+MWS+PS.mcr`
- `Materials\Define Human Material Properties^-DS.mcs`
- `Materials\Import Biological Tissue Properties^-DS.mcr`

Use them to learn complex and dispersive material definitions for loaded antennas, metamaterials, biological tissue, and lossy media.

## Relationship To Existing Guides

- `official-docs/`: authoritative CST API definitions.
- `macro-library/`: installed CST macro examples and practical script patterns.
- `domain-guides/`: antenna evolution, diagnosis, optimization, and data recording.
- Implementation should confirm objects in official docs, extract practical patterns from macros, and record design decisions using the domain guides.
