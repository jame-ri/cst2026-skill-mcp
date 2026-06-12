# CST 宏库调用指南

## 目标

`D:\CST\Library\Macros` 是 CST 安装自带的宏脚本库，里面包含大量可学习的 VBA/History 示例。模型使用它时，不应直接把完整宏当黑盒运行，而应把它当作“官方脚本模式库”：检索相关宏，打开源文件，提取可靠的命令片段，参数化后注入到当前工程。

## 什么时候查宏库

在以下场景优先查 `macro-library/macro-inventory.csv`：

- 不确定某个 CST 对象的 VBA 写法，例如 `DiscreteFacePort`、`FarfieldArray`、`MeshSettings`、`ResultTree`。
- 需要复杂几何示例，例如偶极子、喇叭、波导阵列、滤波器、螺旋线圈、反射面。
- 需要端口、监视器、远场、S 参数导入导出、Touchstone、结果树操作示例。
- 需要 solver、mesh、HPC、optimization、broadband monitor 的官方宏写法。
- 需要把 CST GUI 里某个 Macro 功能转成 Python 自动化。

## 索引检索方法

推荐命令：

```powershell
Import-Csv D:\CSTapi\macro-library\macro-inventory.csv |
  Where-Object { $_.keywords -match 'Farfield|Monitor|DiscretePort' } |
  Select-Object category,subcategory,title,applications,source_path
```

或用 `rg`：

```powershell
rg -n "Farfield|DiscretePort|WaveguidePort|S-Parameter|Optimizer" D:\CSTapi\macro-library\macro-inventory.csv
```

找到候选宏后再打开原文件：

```powershell
Get-Content -Encoding Default -Path "D:\CST\Library\Macros\Construct\Demo Examples\Dipole Antenna^+MWS.mcs" -TotalCount 220
```

## 文件后缀理解

宏名常见格式：

```text
Macro Title^+MWS+DS.mcr
Macro Title^-DS.mcs
```

解释：

- `^+...`：通常表示在 CST 宏菜单中可见。
- `^-...`：通常表示隐藏或内部宏，但仍可作为写法参考。
- `MWS`：Microwave Studio / 3D 高频电磁相关。
- `DS`：Design Studio / schematic。
- `EMS`：低频/电磁场相关。
- `PS`：Particle Studio。
- `MPS`：Multiphysics Studio。
- `WIN`：Windows/外部工具相关。

不要只按后缀决定是否可用。最终仍要看宏内容和当前工程模块。

## 推荐调用策略

### 优先策略：提取 History/VBA 片段

适合建模、端口、材料、边界、监视器、求解器设置。

流程：

1. 打开相关 `.mcr` 或 `.mcs`。
2. 找到 `With ... End With`、`AddToHistory`、`StoreParameter`、`ResultTree` 等片段。
3. 删除交互式 `Dialog`、`MsgBox`、`GetFilePath` 等不适合自动化的部分。
4. 把常数改成参数表达式。
5. 用 `project.model3d.add_to_history(caption, vba_code)` 注入。
6. 记录 `source_macro`、`adapted_caption`、参数和变更目的。

Python 模式：

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

### 次选策略：运行安装宏

适合用户明确要求运行 CST 自带宏功能，或宏本身做复杂导入导出/向导操作。

VBA 模式：

```vb
RunScript GetInstallPath + "\Library\Macros\Results\- Import and Export\Import Touchstone File^+MWS+DS.mcr"
```

注意：

- 许多安装宏依赖 GUI 对话框，不适合无人值守优化。
- 许多宏会读写当前工程或结果目录，运行前必须使用工程副本。
- 运行前记录 `source_path` 和预期输出。

## 宏源码常见结构

- `Sub Main()`：宏入口。
- `BeginHide ... EndHide`：隐藏历史记录中的初始化或 GUI 处理。
- `Begin Dialog UserDialog ...`：交互式窗口，自动化时通常需要移除或替换为参数。
- `assign "var"`：把变量写入历史，便于 CST rebuild 重放。
- `StoreParameter` / `StoreParameterWithDescription`：写 CST 参数。
- `AddToHistory "caption", sCommand`：把命令追加到 History。
- `With Brick` / `With Cylinder` / `With Transform`：几何建模。
- `With DiscretePort` / `With DiscreteFacePort` / `With WaveguidePort`：端口。
- `With Monitor`：场/远场/功率流监视器。
- `ResultTree` / `DSResultTree`：结果树查询和新增。

## 自动化安全规则

- 默认不直接运行宏修改用户原工程；先复制 job project。
- 不把带 GUI Dialog 的宏直接放进批量优化。
- 不复制整段宏中与目标无关的操作，避免带入隐藏副作用。
- 不直接使用 `GetFilePath`、`MsgBox`、剪贴板、外部 exe 调用，除非用户明确需要。
- 改结构前记录 `design_id`、`parent_design_id`、`mutation_id`。
- 每次引用宏库都记录 `source_macro`，例如 `D:\CST\Library\Macros\Solver\Ports\Set Port Mode Evaluation Frequency^+MWS+PS.mcr`。

## 输出记录模板

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

