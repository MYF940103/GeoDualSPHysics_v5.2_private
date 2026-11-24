# C08 饱和土柱塌陷 · 显式 u-pl 三组验证

在 Windows x64、NVIDIA GPU 上双击 [三组完整流程](xCaseLianCollapse_all_win64_GPU.bat)。也可以在下表选择单组。每组用 GenCase 生成粒子，闭墙重力预载到 10 s，从本组末帧继承材料历史，撤掉右墙后再计算 3 s。最后导出粒子、绘图并生成匹配的 CSV。时间单位均为物理秒。

| 初始剪胀角 | 峰值黏聚力 | 剪胀衰减系数 | 运行 | 输入 |
|---|---:|---:|---|---|
| 0° | 5 kPa | 0 | [GPU BAT](xCaseLianCollapse_psi0_win64_GPU.bat) | [预载 XML](CaseLianCollapse_psi0_pre_Def.xml) · [撤墙 XML](CaseLianCollapse_psi0_Def.xml) |
| +2.5° | 5 kPa | 0.2 | [GPU BAT](xCaseLianCollapse_psi2p5_win64_GPU.bat) | [预载 XML](CaseLianCollapse_psi2p5_pre_Def.xml) · [撤墙 XML](CaseLianCollapse_psi2p5_Def.xml) |
| −5° | 7.5 kPa | 0.2 | [GPU BAT](xCaseLianCollapse_psim5_win64_GPU.bat) | [预载 XML](CaseLianCollapse_psim5_pre_Def.xml) · [撤墙 XML](CaseLianCollapse_psim5_Def.xml) |

三组采用相同的空间与时间离散。Wendland 核，粒子间距 0.04 m，核长 0.072 m，固定积分步长 5 µs，常规输出间隔 0.01 s。模型选 `HydroMechModel=1`，水的体积模量为 1 GPa，初始水力传导系数为 2×10⁻⁴ m/s，传导系数随孔隙比演化（模型 1，Ck=2）。三组关闭沙漏控制。撤墙阶段人工黏性系数为 0.1，人工应力系数为 0.3、指数为 2.55。预载阶段使用阻尼 0.03，每 40 步对孔压进行 Shepard 正则化，撤墙后关闭这两项。左墙和右墙为自由滑移，床面为无滑移。撤墙按初始边界编号移除 255 个右墙粒子。

三组的材料参数见上表；三组之间的运动差异同时包含材料差异。每组自己的 `Part_1000.bi4` 保存应力、孔压、塑性历史及体积变化。撤墙首帧已经过一个积分步。使用历史中的真实时间和固定材料 ID 比较，时间零点取该组原生预载末帧。

## 输出和复现

- 根目录 `CaseLianCollapse_<group>_pre_GPU_out` 与 `CaseLianCollapse_<group>_GPU_out` 分别保存预载与撤墙结果。每组预载含 5,000 个土粒和 2,060 个固定粒子；撤墙后固定粒子有 1,805 个。可视化分别加载 `PartFluid` 和 `PartBound` 序列；完整精度字段保存在原生 BI4。
- [本版图和数据](figures/validation_explicit/) 包含各组孔压、形态、运动历史及按论文图 14–17 时刻整理的前缘对比。按组的 `history.csv` 保留实际保存时间。总孔压与固定材料的超孔压 `p−p₀` 单列。
- 本机已有同方案的零度组完整预载和撤墙结果，以及正角组完整预载。本版复用时记录来源；换到缺少历史数据的机器时，从各自 XML 生成并计算。负角旧预载最后保存于 9.670005 s，完整流程需要本组 10 s 的末态。
- 文献给出数值模拟的可见外形和场图。论文前缘取填色主体边缘，本算例取土粒中心的最大横坐标。滑带局部团聚、孔压尖峰、滑移终止过早等误差均随结果保存。固定平面接触使用分步投影，接触反力与同一子步 Darcy 方程尚未闭合。

旧版本的配置、运行方式和证据分别见 [r5 说明](README_server_r5.md)、[r6 说明](README_server_r6.md) 和 [历史运行记录](support/STATUS_current.md)。这些版本使用各自的程序和预载。论文参考范围及已有数字化方法见 [图 14–17 对照说明](tests/notes/c08_h18_paper_comparison_scope_r1.md)。

运行环境为 Windows x64、支持 CUDA 的 NVIDIA GPU 和带 NumPy、SciPy、Matplotlib 的 Python。入口默认使用仓库 `bin/windows` 中的 GenCase 和 GPU 程序。迁移时可用 `C08_BIN` 指定含程序、DLL 和配置的运行目录，用 `C08_PYTHON` 指定解释器。命令行加 `--postprocess-only` 可从完整输出单独生成派生数据；脚本调用可设置 `C08_BATCH_MODE=1` 跳过窗口暂停。

退役的 16 个历史 BAT 及恢复方法见 [清理记录](tests/notes/c08_root_legacy_cleanup.md)。文献前缘的数字化来源和读图核验见 [参考数据说明](figures/validation_explicit/reference/README.md)。
