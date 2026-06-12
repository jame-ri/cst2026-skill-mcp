# CST 宏库目录导览

## 总览

当前索引来自 `D:\CST\Library\Macros`，共记录 414 个宏库文件，包含 `.mcr`、`.mcs`、`.bas`、`.cls`、`.py` 等脚本，也包含图片、PDF、PPT、TXT、示例工程等配套资源。使用时如果只想查可执行脚本，先过滤 `extension` 为 `mcr`、`mcs`、`bas`、`cls` 或 `py`。

分类概览见 `macro-category-summary.csv`：

- `Calculate`：计算器、传输线、波导、材料附加信息、热对流等。
- `Construct`：几何构造、Demo Examples、端口、线圈、FastHenry、反射面、离散端口等。
- `Converter` / `File`：ADS、Gerber、GDSII、DXF、SPICE、Touchstone 等导入转换辅助。
- `Matching Circuits`：匹配电路、Optenni、Mini Match。
- `Materials`：Drude、Cole-Cole、Graphene、Tensor、Biological tissue、Tabulated Surface Impedance 等材料。
- `Parameters`：参数复制、参数控制 solid 是否参与仿真、参数变化保留 mesh。
- `Results`：S 参数、Touchstone、Farfield、EMC、TDR/Eye、表格、2D/3D 后处理。
- `Solver`：A/F/I/T/M Solver、Ports、Mesh、Sources、Monitors、Optimization、HPC。
- `Wizard`：5G 工具、数据导入、比较求解器、归档、Via Wizard。

## 对天线/电磁自动化最有价值的入口

### 建模示例

检索：

```powershell
rg -n "Dipole|Horn|Waveguide|Microstrip|Reflector|Filter" D:\CSTapi\macro-library\macro-inventory.csv
```

高价值示例：

- `Construct\Demo Examples\Dipole Antenna^+MWS.mcs`
- `Construct\Demo Examples\Horn antenna^+MWS.mcs`
- `Construct\Demo Examples\Waveguide Array^+MWS.mcs`
- `Construct\Demo Examples\Waveguide Iris Filter^+MWS.mcs`
- `Construct\Demo Examples\Microstrip with Bondwire^+MWS.mcs`
- `Construct\Parts\Reflector dish^+MWS.mcs`

用途：

- 学习参数化建模、`StoreParameter`、`Component.New`。
- 学习 `Brick`、`Cylinder`、`Transform`、`WCS`、`Pick`、`DiscreteFacePort`。
- 学习边界、监视器、频率范围、mesh、solver 的完整 History 组织方式。

### 端口和馈电

检索：

```powershell
rg -n "DiscretePort|DiscreteFacePort|WaveguidePort|Port Mode|Target Cut Off" D:\CSTapi\macro-library\macro-inventory.csv
```

入口：

- `Construct\Discrete Ports\Discrete port with lumped element^+MWS.mcr`
- `Construct\Discrete Ports\Multiple discrete Ports^+MWS.mcr`
- `Construct\Discrete Ports\Convert Discrete Edge Port to Discrete Face Port^+MWS.mcs`
- `Solver\Ports\Set Port Mode Evaluation Frequency^+MWS+PS.mcr`
- `Solver\Ports\Set Port Target Cut Off Frequency^+MWS+PS.mcr`
- `Solver\Ports\Set S-parameter symmetries - discrete ports^+MWS.mcr`

用途：

- 学习离散端口、离散面端口、波导端口和端口模式设置。
- 修改天线馈电时，先查这些宏的端口创建和验证逻辑。

### 监视器和远场

检索：

```powershell
rg -n "Farfield|Monitor|Probe|Broadband|TRP|TIS" D:\CSTapi\macro-library\macro-inventory.csv
```

入口：

- `Solver\Monitors and Probes\Broadband Field Monitors^+MWS+PS.mcr`
- `Solver\Monitors and Probes\Farfield Monitors - Activate fast Combine Results^+MWS.mcr`
- `Results\Farfield\Show Total Radiated Power (TRP)^+MWS.mcr`
- `Results\Farfield\Show Total Isotropic Sensitivity (TIS)^+MWS.mcr`
- `Results\Farfield\Generate 3D Radar Range Pattern^+MWS.mcr`
- `Results\- Import and Export\Export Farfield in GRASP format^+MWS.mcr`
- `Results\- Import and Export\Import Farfield from HFSS^+MWS.mcr`
- `Results\- Import and Export\Import Farfield from FEKO^+MWS.mcr`

用途：

- 建立远场监视器、宽带监视器、TRP/TIS 后处理。
- 将外部远场导入 CST 或导出给外部工具。

### S 参数和结果读取

检索：

```powershell
rg -n "S-Parameter|Touchstone|ResultTree|Result1D|Q-values|MDIF" D:\CSTapi\macro-library\macro-inventory.csv
```

入口：

- `Results\1D Results\Measure Resonances and Q-values from frq-data^+MWS.mcs`
- `Results\1D Results\Recalculate S-Parameter with new Frq-Sampling^+MWS.mcr`
- `Results\- Import and Export\Import Touchstone File^+MWS+DS.mcr`
- `Results\- Import and Export\Export MDIF File (for AWR and ADS)^+MWS.mcr`
- `Results\- Import and Export\Export S-Parameters to Modelica^+MWS+DS.mcr`
- `Results\Tables\Get Min Max Value of 0D Table^-DS.mcr`
- `Results\Tables\Parametric xy Plot from 0D Tables.mcr`

用途：

- 学习 `ResultTree` 路径发现、S 参数结果处理、Touchstone 导入导出。
- 做优化时可借鉴 resonance/Q 值和表格处理逻辑，但指标读取优先使用 `cst.results`。

### Solver、Mesh、优化

检索：

```powershell
rg -n "Solver|Mesh|Optimizer|Broad Band Sweep|GPU|HPC|Unitcell" D:\CSTapi\macro-library\macro-inventory.csv
```

入口：

- `Solver\A-Solver\Activate Broad Band Sweep^+MWS.mcr`
- `Solver\F-Solver\Change settings from Full Array to Unitcell^+MWS.mcr`
- `Solver\Mesh\TET Meshing - Robust Volume Meshing^-DS.mcr`
- `Solver\Mesh\Surface Meshing - Enable accurate Wire meshing^+MWS.mcr`
- `Solver\Optimization\DOE (Design of Experiments)^-DS.mcr`
- `Solver\Optimization\Non-Parametric Optimizer Settings^+MWS+EMS.mcr`
- `Solver\High Performance Computing\Check GPU Computing Setup^+MWS+PS.mcr`
- `Wizard\Compare Solvers^+DS.mcr`

用途：

- 学习求解器切换、mesh 设置、优化器设置、HPC 检查。
- 长仿真和优化必须复制工程并记录 trial。

### 材料

检索：

```powershell
rg -n "Drude|Graphene|Tensor|Cole-Cole|Tissue|Surface Impedance|Material" D:\CSTapi\macro-library\macro-inventory.csv
```

入口：

- `Materials\Create Drude Material for Optical Applications^+MWS+PS.mcr`
- `Materials\Create Drude Material for Plasma Applications^+MWS+PS.mcr`
- `Materials\Create Graphene Material for Optical Applications^+MWS+PS.mcr`
- `Materials\Create Full Tensor Material^+MWS.mcr`
- `Materials\Create Cole-Cole Model Material^+MWS+PS.mcr`
- `Materials\Create Tabulated Surface Impedance Material^+MWS+PS.mcr`
- `Materials\Define Human Material Properties^-DS.mcs`
- `Materials\Import Biological Tissue Properties^-DS.mcr`

用途：

- 学习复杂材料定义和色散材料参数写法。
- 天线加载材料、超材料、人体组织和损耗介质建模可先查这些宏。

## 宏库和现有 skill 的关系

- `official-docs/` 负责查 CST API 的权威定义。
- `macro-library/` 负责查 CST 安装宏中的实际脚本写法。
- `domain-guides/` 负责天线设计演化、诊断、优化和数据记录。
- 自动化实现时，优先用官方 API 文档确认对象，再从宏库抽取可运行模式，最后按 domain guide 做安全记录。
