# 恢复原始 u-pw float：回退、清理与后续计划

日期：2026-09-09。用户要求停止 double 长程验证，撤销孔压 double 状态和此前的高低位累计补偿，并检查冗余代码。本轮不开发 TPI、压力—加速度迭代或 u-pl。

## 已停止并保留的计算

本机时间 15:26:27，核实进程命令行后先停止正式 BAT（PID 37460），再停止对应 CPU 求解器（PID 22108），避免继续后处理或另开流程。最后完整输出为 PART 0084，t=15.303610 s、1,530,361 步；这不是完整 2Tv 验证，不用于平台改善或完整效率结论。

原目录 `CaseTerzaghiConsolidation_q0_PR_full_k1em4_double_out`、旧 precision/原始 float 结果以及所有既有测试记录保持不变，未删除、覆盖或伪造“成功结束”标记。后续不得将该 partial double 检查点直接交给 float 程序续算。

## 可恢复性和范围

回退前 17 个有实质差异的源文件及 CPU/GPU Debug/Release 四个执行程序保存在 `upw_float_restore_before.zip`，归档内保留仓库相对路径。SHA256：`E6E8E1D2B8FF4AAC23B6E5B3A49272B8A3DBC38867C89B080D02F89642C6D1FD`。此前高低位补丁另有 `pore_double_stage1_baseline_sources.zip`，本次没有把它当作无补丁基线。

原始 float 源码基线为 Git `fe72537f8b61616e98134535bfaf0535a4269855`。只定点回退精度相关文件；未 reset 工作区、未切换分支、未改动用户其他算例，未提交或推送 Git。除下述读取器安全检查外，恢复的生产文件内容与该节点一致。

“原始 float”指孔压当前值、参考值、积分历史和输出恢复 float，不是将原代码已有的 double 时间步、粒子位置、Darcy 中间量或修正矩阵全部降精度。原始逐步 float 写回会重新具备小增量舍入风险；用户是在已有验证未显示显著收益的情况下选择撤销精度试验，不代表该风险不存在。

## 本轮实际修改的生产文件

以下均位于 `src/source`；行号对应回退后的版本，可结合函数名定位。

| 文件 | 主要位置/函数 | 修改功能与目的 |
|---|---|---|
| JSphCpu.h | 41、158–169、246；孔压相互作用/边界声明 | 状态、参考及历史恢复 `float*`；同步参数类型。 |
| JSphCpu.cpp | AllocCpuMemoryParticles、ResizeCpuMemoryParticles、ReserveBasicArraysCpu、GetParticlesData | 恢复 4B float 孔压内存池、拷贝及输出暂存。 |
| JSphCpu.cpp | InteractionPorePressureRateT、InteractionForcesFluid、mDBC、Shepard | 撤除 double 状态投影和过渡说明；恢复原始邻域输入与 float Shepard 结果。 |
| JSphCpu.cpp | 3905、3921、3938：三种孔压更新入口 | 恢复 `float(double(old)+dt*double(rate))` 写回；无余量数组。 |
| JSphCpuSingle.h | PeriodicDuplicateVerlet/Symplectic | 周期复制接口恢复 float 状态/历史。 |
| JSphCpuSingle.cpp | 134 ConfigDomain；PeriodicDuplicate*；SaveData | 重启、初始化、周期拷贝、暂存和 PART 孔压输出恢复 float。 |
| JCellDivCpu.h / JCellDivCpu.cpp | SortArray | 删除仅为本次 double 孔压新增的标量 double 排序重载；保留原始位置排序。 |
| JSphGpu.h | 115、160、173、179；函数声明 | 主机、设备、参考和历史孔压统一恢复 float。 |
| JSphGpu.cpp | 324、390；ParticlesDataUp/Down；Shepard；积分调用 | 恢复 float 字节数、内存池、上传下载和历史交换，撤销 double 配套代码。 |
| JSphGpuSingle.cpp | 172 载入、420 排序、1095 输出 | 恢复 float 重启、粒子重排及 float PART 输出。 |
| JSphGpu_ker.h / JSphGpu_ker.cu | 159/283 声明；1173/1178 更新；1340/1364/1369 Shepard | CUDA 参数、写回、边界和 Shepard 恢复原始 float；移除过渡投影。 |
| JCellDivGpu.h / JCellDivGpu.cpp | 161 / 364 附近 SortDataArrays | 移除为 double 孔压单独增加的标量 double 排序入口。 |
| JCellDivGpu_ker.h / JCellDivGpu_ker.cu | 59 / 635/725 附近排序核及包装 | 同步移除专用 double 标量核，保留原始 float 与位置排序。 |
| JPartsLoad4.h | PorePress/PorePress0 和 getter | 恢复 float 指针，内容与 fe72537 一致。 |
| JPartsLoad4.cpp | 92 分配、114 大小统计、295 数据读取 | 恢复 float 分配及直接读取，删除 double/高低位重构。 |

上述为 17 个既有文件。`JSph.h/.cpp`、`DualSphDef.h`、`JSphGpuSimple_ker.cu` 和 VS 两工程没有本轮实质修改；部分 Git 状态可能仍显示历史行尾差异，不等于物理代码差异。

### 读取器刻意保留的安全差异

`JPartsLoad4.cpp` 相对 fe72537 仅剩 35 行增加、3 行删除：

- 27 行：有限值校验所需 `<cmath>`。
- 160 行：孔压与参考孔压随粒子 ID 同步排序。
- 217、247 行：成对存在、分片存在性一致性。
- 230 行：总粒子数按每片 `pd2.Get_Npok()` 正确相加，避免重复使用首片数量。
- 249–265 行：明确拒绝补偿版 `PorePressRes` 和 double 孔压检查点；仅接受长度正确的 float 数组，不自动转换。
- 298 行：拒绝非有限孔压。
- 356、364、373 行：移除边界时同步保存、复制和释放 float 孔压。

这些是输入和粒子数据完整性保护，不是累计精度补丁。排序/RemoveBoundary 的原方法目前没有有效主流程调用；保留同步保护不改变当前正常计算路径，也不在本轮扩大 Sigma/Kplastic 的历史载入语义。

## 冗余代码检查

已撤除精度试验新增的 double 状态类型、8B 孔压池配置、double 孔压排序、专用拷贝、输出改造及 float 投影说明；高低位运行数组和 `FunPorePressure.h` 均不再存在，VS 工程没有该头文件引用。

刻意不删：

- `JSph.cpp:3548` 对 `PorePressureIntegrationMode/PoreTpiAlpha` 的拒绝：这是 fe72537 已有护栏，防止失效 TPI 参数被忽略后误跑 PR。
- `JPartsLoad4.cpp:250` 对 `PorePressRes` 的拒绝：这是不兼容格式提示，不是仍在使用补偿状态。
- 原始 double 位置、时间步、通用数组、修正矩阵及局部中间运算。
- 历史实验脚本、XML/BAT、图片、数据和归档：作为记录保留，不重新接入生产路径。double 专用 BAT 会由既有输出检查/冻结版本检查拦截当前 float 执行程序。

不进行无证据的全仓库死代码删除。真正未被调用的旧功能仍需独立确认配置和编译分支后再处理。

## 验收与文件组织

- 本轮支持脚本仅放 `tests/support/upw_float_restore`：`loader_float_harness.cpp`、`run_loader_float.ps1`、`run_smoke.py`。
- 构建和检查记录放 `tests/logs/upw_float_restore`；短算例新输出放 `tests/outputs/upw_float_restore`，不覆盖历史基线。
- 实际 BI4/实际 loader 的 Debug 测试 34/34 通过：正常 float、ID 排序/边界搬移、不等及空分片；非法 double/res、坏类型/长度/存在性、NaN/Inf 均正确拒绝。
- CPU Debug、CPU Release、GPU Debug、GPU Release 均已重新构建成功，四个构建进程均退出 0；日志为 `cpu_debug.log`、`cpu_release.log`、`gpu_debug.log`、`gpu_release.log`。Debug 构建存在 Gm 选项弃用、第三方库 PDB 缺失以及 GPU 的 LNK4098 运行库冲突警告，未更改项目编译配置；两种 Release 构建未报告警告。
- 短算例对照选用 `validation/tpi_cleanup_release_20260906` 的原始 float `new_release` 保存结果，不使用后来高低位补丁当参考。按原命令复现 CPU/GPU 的 pair 与 density 模式，每组 2000 步、2 ms、11 帧，并核对实际时间、粒子 ID 和原生数值。
- 本轮只验证恢复一致性，不宣称解决孔压平台。若原生结果完全一致，不再绘制重复重合曲线；如有差异再定位并出图。

### 最终验收结果

四组短计算均退出 0，每组 2000 步、11 帧、每帧 1040 个完整粒子 ID；与同后端原始 float 基线的原生时间完全一致，末时刻为 0.001999999999999941 s。孔压、参考孔压、位置、速度、密度、应力和 FSType 逐值及解码位差均为零；零排除、零 DtMin 调整。这里不是指带有运行元数据的整个 BI4 文件逐字节相同，也不代表尚未保存的内部状态全部已检查。

| 后端 | 压缩源配置 | 原生保存字段比较 | 记录 |
|---|---|---|---|
| CPU | PairDivergence | 全部零差 | r1_cpu_pair_symplectic.json |
| CPU | DensityRate | 全部零差 | r1_cpu_density_symplectic.json |
| GPU | PairDivergence | 全部零差 | r1_gpu_pair_symplectic.json |
| GPU | DensityRate | 全部零差 | r1_gpu_density_symplectic.json |

汇总：`tests/logs/upw_float_restore/r1_summary.json`，共 44 个匹配帧对；loader 34 项结果：同目录 `loader_debug.json`。完整性检查、输入/旧输出/执行程序/读器哈希及详细指标均在这些记录中。结果完全一致，本轮不额外绘制重合曲线。回退和最小恢复验收已完成，最终检查没有遗留运行中的上述求解器进程。

当前 `bin/windows` 下已更新的执行程序与 SHA256：

| 执行程序 | SHA256 |
|---|---|
| DualSPHysics5.2CPU_win64.exe | 1B34475434B4B2D21669027F020B74F959F9C99F097A9B624A8C6E7124865CDC |
| DualSPHysics5.2CPU_win64_debug.exe | B658C28D556810002D668B31479DE8BBC598C63E0337EA5A2C3E42B06392F6D5 |
| DualSPHysics5.2_GEO_win64.exe | F699E18623D915866F0905C3C0F8F5CD76823981183C488D50768A0C0176DD2A |
| DualSPHysics5.2_win64_debug.exe | 97D27ACEB60B1FBDC8CBCC5978DC55C26A7DC4999CC183C782137C3C8111ECDA |

最后生产源码 `git diff --check` 通过；`git diff --name-only -- source VS` 仅列 `JPartsLoad4.cpp`，其 SHA256 为 `2DCF4561BC9DF4695A732359A5307305DDDFE506C191B16F0966A1A5542B3C20`。该差异仅包含上文逐项列明的安全处理。

## 后续算法开发顺序（仅规划，未实施）

1. **先明确压力问题和参考方程。** 保持原始 float PR 基线，先在固定几何、常 n/k、非零受控源项上构建同离散算子、同边界的充分收敛压力参考；同时记录质量/压力方程残差、边界通量和压力相关加速度。有限 Kw 的 PR 与不可压缩水的 PPE 不能直接互当真值。
2. **单独验证 TPI。** 先确定历史压力、第一步初始化、预测/校正、变步长历史处理、边界更新与输出时序，再比较同物理 PPE 的收敛解。按 1、2、5、10 倍候选步长逐级试验，每档都受力学稳定限制；以满足误差目标后的总耗时衡量收益，不只统计一步快慢或“未发散”。TPI 历史外推不是充分收敛的压力迭代。
3. **再设计压力—加速度迭代。** 明确采用有限 Kw 的耦合残差还是不可压缩 PPE；在固定本步起点下反复更新压力、力/加速度及必要的边界值。压力残差和力学残差需分别归一化并同时收敛，设迭代上限及不收敛的回退/缩步规则；试探迭代不能重复累计塑性应变、损伤或时间，收敛后才提交状态。先验证线性弹性受控问题，再接入弹塑性、NoPen、非平行墙和墙角。
4. **u-pl 作为独立物理扩展。** 在求解算法验收之后再引入动态 Darcy 项；先常 n/k，随后单独检验孔隙率和渗透率演化。默认关闭的新模型必须复现此 float PR 基线，不将物理扩展和求解算法变化捆绑验收。
5. **最后用于 retrogressive landslide。** 预先约定失稳时刻、后退距离/速度、分次破坏、孔压历史、滑移范围以及总耗时的容许差异；先短段与步长敏感性，再决定完整大算例。若收益不足或残差不可控，停止该实验分支，不持续向正式求解器堆入临时接口。

规划依据为本地文献：`src/papers/u-pw/Lian 2023 u-pl.md` 第 3.4 节（TPI 由去除水压储存项后的方程推导，历史外推近似隐式压力，仍需稳定性约束），以及 `a-coupled-u-p-sph-formulation-for-hydromechanical-modeling-of-retrogressive-landslides-and-comparison-with-a-penalty-based-approach.md` 第 2.1/2.2 节（PPE 与有限 Kw PR 假设不同）。本计划没有将文献中的具体 alpha 或倍增步长直接承诺为当前代码可用值。
