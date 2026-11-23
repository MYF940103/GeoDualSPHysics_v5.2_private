# 水力算例入口的干净检出和恢复

正式根现已完成安装。四个真实根 BAT 的准备检查均通过，原输入的备份、旧服务器包、正式图表和计算输出已核对。[安装实测](hydro_frozen_install_r2.json)

用同一个临时 Git 树分别检出 Windows CRLF 与 LF 工作目录，均从零重建了 59 个已审核的发布文件，共 492206 字节，逐件与发布清单吻合。两份检出初始没有 `tests/outputs/hfe1`、归档 ZIP、冻结程序和预载。原 35 个输入及启动组件均来自 `d41fae94c1244301f6c915b0e3743da48f833136`：18 份直接使用 Git blob，17 份恢复 CRLF 后与登记的原始字节完全一致。另从同一节点读取 18 个保留的 C08 BAT。该测试只修改临时仓库索引，真实根、索引和原有服务器包均保持原样。[独立检出实测](hydro_frozen_clean_checkout_r2.json)

**已迁移的干净检出可直接使用其 59 份跟踪文件。** 若需独立重建，维护者在 `src` 运行以下两条。第一条只读指定 Git 节点和[已确认的旧包元数据](hydro_frozen_clean_inputs_r2.json)，输出到本检出的本地测试目录；第二条默认只读。Git 检出须带上述历史节点，浅克隆先获取该节点。维护者需要 Git 和 Python 3.9 或以上；使用已发布的原 BAT 按原环境要求执行。

```powershell
$v = '../examples/Hydromechanic coupling/validation'
python -B "$v/hydro_frozen_git_rebuild_r2.py"
python -B "$v/hydro_frozen_entry_apply_r1.py"
```

### 实际计算所需的外部附件

| 根入口 | Git 外的实际依赖 | 如何恢复 |
|---|---|---|
| C01 FreshPR | `support/bin` 内 8 份运行附件，包括 GenCase、GPU、PartVTK、ReadSelfWeightNative、XML 配置和 DLL。完整后处理需要 NumPy、Pandas、Matplotlib。 | 保留或复制同一发布版的完整 `support/bin`；程序身份可参考已跟踪的 `support/selfweight_freshpr_r2.manifest.json` 和对应运行收据。|
| C04 八个旧入口 | 5 个原服务器 ZIP，共 78414842 字节；文件名、字节数、原包 SHA、8 个原 XML 成员分别登记在[元数据](hydro_frozen_clean_inputs_r2.json)。 | 原包放在 C04 根目录，新的 Windows 入口会在独立工作区调用相应原程序。原 ZIP 也可继续单独展开使用。P3 全程还须满足原峰窗资格及其真正的返回文件；checkout 不生成该批准。|
| C05 条带 | `support/bin` 的 9 个原程序、DLL 及配置。 | 从原 `Lian_HGSPR_Windows_RTXA6000.zip` 取 `support/bin`。整包亦可在独立目录按原方式执行。不要用包中旧 XML 覆盖已迁移根 XML。|
| C08 r3–r6 | 按组、版本和后端使用 `support/runtime_r3..r6`。本机记录 46 个版本化运行文件，另有真实 r2 GPU `Run.csv` 与 `data/Part_1000.bi4`。 | 保留同版运行目录、已认证 PRE 及既有调度证据。旧 r1–r3 服务器包独立有效，包内只有其原版本的 GenCase、CPU、GPU；单用这些包不能恢复新根 r3–r6 后处理所要求的 C08Native、PartVTK 或新版本程序。r3/r4 CPU 接收取同后端真实 PRE；此次本机缺该数据，入口仍按原条件拒绝。|

上表的本地实际路径、字节数和 Git 跟踪情况逐项列在[运行附件清单](hydro_frozen_clean_checkout_r2.json)。清理时应保留这些原包、工作目录中的同版程序、原始 PRE 和重启链。Git 中的小元数据不能代替外部运行附件。五份 C04 ZIP 的原内容、各自原 BAT 和既有输出不因入口迁移而改写。

### 精确的待提交路径

两份清单均使用仓库根相对路径和 NUL 分隔。维护清单共 28 项，包括真实根安装核验脚本及验收记录。正式输入、BAT、模板和计划表共 59 项。两组路径均通过 `git check-ignore --no-index`。既有的 `upl_xml_gencase_r1.py`、原后处理和原 C08 根 BAT 已在基线跟踪。

```powershell
# 从仓库根目录运行。
$val = 'examples/Hydromechanic coupling/validation'
git add --pathspec-file-nul --pathspec-from-file="$val/hydro_frozen_maintenance_r2.pathspec"
git add --pathspec-file-nul --pathspec-from-file="$val/hydro_frozen_formals_r2.pathspec"
git diff --cached --stat
```

[28 项维护清单](hydro_frozen_maintenance_r2.pathspec) · [59 项正式清单](hydro_frozen_formals_r2.pathspec) · [当前发布说明](hydro_frozen_entry_release_r2.md)

