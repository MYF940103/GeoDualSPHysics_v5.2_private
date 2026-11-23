# 冻结水力算例的 Windows 入口

21 份正式定义已在原算例根目录切换到公共 XML 格式，覆盖 28 个历史 CPU/GPU 入口。**运行转换使用 Windows 自带的 PowerShell 5.1 与 .NET Framework**。四个案例复用同一份 `hydro_frozen_runtime_r2.ps1`，各自携带按已有输入生成的配置表。服务器上原已解压的发行包可继续独立运行。

全新检出时，59 个迁移文件可从固定 Git 基线和五份已核验归档的元数据重建。无需复制原本机的 `hfe1`，实际运行所需二进制另见[干净工作树与运行附件清单](hydro_frozen_clean_checkout_r2.md)。

| 原发行版 | 原有运行条件 | 实测 |
|---|---|---|
| C04 的 8 个冻结 GPU 入口 | 读取 5 个真实 ZIP 中的 BAT 和所调用 PS1，原流程仅需随包程序及 Windows。 | 5 个实际 GenCase、1 个直接读取随包旧种子、2 个 P3 原 BAT 的 check-only 全部成功。P3 全程仍有原峰窗返回和物理审查要求。8 个旧根输出保护全部通过。|
| C05 Lian 服务器发行版 | 原根和原 ZIP 均调用 GenCase、GPU，绘图在回传后进行。 | 无 Python 时正常生成 21945 粒子的实际配置。已运行现代 XML 改参检查，实际生成值为输出间隔 0.000123456 s、排水开始 0.0123456 s、条带荷载 9876.5 Pa、加载时间 0.25 s。|
| C01 FreshPR | 原 `-solver-only` 无 Python；全流程中原生数据分析和绘图使用 Python。 | 无 Python 的准备入口通过。已有正式输出受到保护。原后处理参数读取函数对实际求解 XML 和它的来源定义读取结果完全相同。|
| C08 | 根目录现有 r3–r6 在预处理中检查原绘图解释器。更早的服务器 r1、r2、r3 ZIP 仅运行 GenCase/求解器，三个真实包内的执行链均已检查。| 当前 18 个根 BAT 中，8 个 GPU 接收和 2 个预载入口通过，6 个 CPU 接收因无真实 CPU 预载文件按原样拒绝，另外 2 个保留原剪胀角禁用条件。原归档 ZIP 继续独立运行。|

无 Python 测试的子 BAT 仅能从 PATH 找到 Windows 系统目录，`PYTHON` 指向经过检查的不存在路径，并核实搜索路径中找不到 python。共验证 9 个原本无 Python 的完整流程入口及 C01 的独立求解准备入口；仅执行准备阶段，未启动任何求解器。C08 当前的独立闭锁/绘图检查仍使用其原先指定的解释器。

13 份独立旧模板逐个通过 Windows PowerShell 运行时的 CRLF、UTF-8 BOM 和全字节还原检查。Cryer 的另 8 份模板与各自原 ZIP 中成员逐字节核对，P3 另实测添加 CRLF+BOM 后原 BAT 预检正常。C01、C05 将可表达的修改传入原求解器 XML。涉及原清单、固定种子、材料或撤墙合同的 C04/C08 输入更改会明确提示须另发版本。已在真实 Windows 入口核验 C05 不支持的模型、未知属性及 P3 模型更改均被拒绝。[入口核验与清单](hydro_frozen_entry_release_r2.json) · [原 BAT、原 ZIP 与 Windows 运行时检查](hydro_frozen_windows_review_r2.json)

## 发布与恢复

真实根已安装 59 个文件，共 492206 字节。原 35 份文件保存在 C04 的 `tests/outputs/hfe1/original_before_install`，按安装前内容逐字节校验通过。另有 24 个新增文件。C01–C08 的 53 份根定义均已使用公共配置，现有 76 个根 BAT 齐备。实际运行了四个根 BAT 的准备入口，C01、C04、C05、C08 分别核对了 1040、37181、21945、7060 个种子粒子的 ID、初始坐标、速度和密度。C08 同时通过原 10 s GPU 预载的调度与状态文件路径检查。完整入口隔离检查覆盖 28 条路径，其中 20 条完成准备，8 条按已有准入条件退出。[正式安装与实根检查](hydro_frozen_install_r2.json)

从 `src` 目录验证正式根的现状：

```powershell
$v = '../examples/Hydromechanic coupling/validation'
D:/anaconda3/python.exe -B "$v/hydro_frozen_entry_apply_r1.py"
```

该命令可随时复核已安装文件。恢复仍处于原始版本的本地检出时，维护者可加 `--apply`，工具会先保存原文件，再安装已核验的内容。已发包用户可继续双击原包里的 BAT。

新的运行端使用原 BAT 文件名；`--prepare-only` 在单独准备目录生成初态或调用 P3 的原生预检，正常求解仍使用原选项及保护条件。C04 的原包在同一案例的 `cryer_*_run` 下独立展开。新建包工作区如因 I/O 出错而中断，则保留其现状以便检查。历史 C04 根正式/冒烟输出存在时，正常求解入口会提前退出。

可在维护机上使用新标签重做离线生成与准备测试。维护者生成工具使用 Python；服务器用户只需要原运行条件。

```powershell
$w = '../examples/Hydromechanic coupling/04_CryerProblem_PR/tests/outputs/hfe1'
D:/anaconda3/python.exe -B "$v/hydro_frozen_git_rebuild_r2.py" --out "$w/separate_overlay"
D:/anaconda3/python.exe -B "$v/hydro_frozen_xml_review_r1.py"
D:/anaconda3/python.exe -B "$v/hydro_frozen_entry_review_r1.py" --overlay "$w/separate_overlay" --tag separateReview
D:/anaconda3/python.exe -B "$v/hydro_frozen_entry_edits_r1.py" --overlay "$w/separate_overlay" --tag separateEdits
```

