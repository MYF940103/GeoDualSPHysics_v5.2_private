# Stage 1：q0 短回归差异的补充审查

日期：2026-09-09。范围：只读源码复审及隔离诊断方案评估；本记录不新增物理模型、不修改生产源码、不启动新的计算变体。

## 结论与证据边界

此次按保存的源码 ZIP 对照当前实现，未发现 q0 实际执行路径中额外改变的排水条件、外载、孔压 rate 时序或遗漏的旧 float 算子投影。这个结论是静态检查结果，不等于已经证明所有运行差异仅来自数值表示。

Stage 1 的 q0 短回归仍未通过预设的严格孔压差异门槛（全帧 RMS 0.01 Pa、最大值 0.1 Pa）。CPU 已观测到全帧 RMS 约 0.0245894 Pa、最大值约 0.125927 Pa；GPU 约 0.0330 Pa、0.1149 Pa。权威数值及其他指标以 `../logs/pore_double_stage1/regression_comparison.json` 和本目录的 `pore_double_stage1_acceptance.md` 为准。

旧高低位表示与单一 double 表示存在已可构造验证的舍入差异，旧积分与新积分也存在浮点结合次序差异。这些是值得进一步隔离的候选机制；**下面的二进制例子不是这次约 0.126 Pa 差异的已证明原因**。本轮没有统计真实 q0 运行中的半 ULP 事件，也没有实施表示模拟变体。

CPU 基线重复运行已完成：21 帧、每帧 1040 粒子，保存的高位、残差、重构孔压及参考孔压全部为 0 bit mismatch，时间和步数相同。记录见 `../logs/pore_double_stage1/q0_baseline_cpu_repeat.json`。这排除了此次重复检查所覆盖字段的基线非确定性；不能由此推断所有后端和所有条件均确定。

## 基线与测试设置

- 源码基线是本目录的 `pore_double_stage1_baseline_sources.zip`，即迁移前保留补偿精度补丁的工作源码；不是 Git HEAD，也不是未打补丁的旧 u-pw。
- 回归脚本是 `../support/pore_double_stage1/run_regression.py`。基线执行程序保存在 `../outputs/pore_double_baseline`；当前程序来自仓库 `bin/windows`。
- q0 配对均采用相同初始几何和参数，计算 0.2 s，固定步长 1e-5 s，20000 步，输出间隔 0.01 s，共 21 帧；CPU 为 4 个 OpenMP 线程。
- 配对都指定 `-mdbc_noslip -stable -symplectic`。No-slip 与正式案例原有 Vel0 设置不能混为一谈；这一短回归内部仍是同设置的基线/当前比较，不是原正式 2Tv 结果的替代。
- 此组初始孔压为零，无残差重启；TopVertical 外载为 10000 Pa，加载 ramp 为 0.01 s，排水从 0.01 s 开启，Shepard 关闭。
- 比较通过原生 BI4 读取权威孔压。旧程序的参考量是重构后的 `double(high)+double(low)`，不是只比较旧输出的 float 高位或 VTK 显示值。

## q0 源码复审路线

下列行号对应本次审查时的文件，后续编辑可能移动行号；函数名是主要定位依据。

| 路径/位置（相对仓库 src） | 检查内容与结果 |
| --- | --- |
| `source/JSphCpu.cpp:1151`，`IsHydroMechDrainageActive` | 排水条件仍由模型启用、排水配置及 `TimeStep >= HydroMechDrainageStartTime` 决定，未改开启时刻。 |
| `source/JSphCpu.cpp:1336`，`ApplyFreeSurfacePorePressure` | 排水前不强制自由面零孔压；排水后置零。基线 high=0、low=0 与当前 double=0 对应，未增加截断或提前排水。 |
| `source/JSphCpu.cpp:1395`，`ApplyYaoTopStripPorePressureExtrapolation` | 只处理相应条形载荷模式；本组 TopVertical 不进入该外推分支，不能把 Yao 改动作为本组已确认原因。 |
| `source/JSphCpuSingle.cpp:621`，`Interaction_Forces` | mDBC、交互准备、自由面识别、外载加速度、自由面孔压处理、主相互作用的先后关系保持基线；未将动态阶段互换。 |
| `source/JSphCpu.cpp:2856` 附近，集成 mDBC 孔压外推 | 邻居和参考孔压进入旧公式前仍作 float 投影，边界结果仍按旧 float 舍入后提升为 double；本组参考孔压为零。 |
| `source/JSphCpu.cpp:2179`、`:2263`、`:2332` 附近，主相互作用 | 粒子孔压、压力力两操作数及 Darcy 邻居孔压均在旧 float 算术前投影；rate 数组仍为 float。 |
| `source/JSphCpu.cpp:3912`、`:3930`、`:3949`，三个孔压积分函数 | 历史状态、预测半步与校正整步来源及调用顺序不变；当前保存方式改为 double，移除 high/low 分解。Verlet 原位更新右侧按粒子先读取，未发现别名覆盖问题。 |
| `source/JSphCpuSingle.cpp:555`，`RunCellDivide` 末尾 | 孔压边界处理仍位于同一阶段；Shepard 由原开关控制，本组关闭。 |

还对照检查了 GPU 对应的主相互作用、mDBC、积分和边界写回：空间公式保留旧 float 投影，rate 保留 float，强制边界值仍保留旧 float 舍入。CPU/GPU 的 state、历史、排序、周期复制与输出改为 double 属于本次 Stage 1 表示迁移；不应把这项静态审查表述为逐指令或位级等价证明。

## 旧积分结合次序与新积分的区别

基线补偿写回的核心次序可概括为：

```cpp
const double next = double(oldhigh) +
                    (double(oldlow) + dt * double(rate));
const float high = float(next);
const float low = float(next - double(high));
```

当前 double 状态的核心为：

```cpp
const double next = oldstate + dt * double(rate);
```

即便把 `oldstate` 初始化为 `double(oldhigh)+double(oldlow)`，`high+(low+increment)` 与 `(high+low)+increment` 的有限精度结合次序也不同。另外，基线每次把残差舍入为 float，当前不再执行这一步。它们数学上表达相同的状态更新，不保证浮点逐步完全相同。q0 使用 Symplectic；同时检查 Verlet 是为了覆盖迁移实现，不表示本组执行了 Verlet。

## 已验证的半 ULP 二进制例子

在常见 IEEE 754 round-to-nearest、ties-to-even 条件下，取可由 double 表示的值：

```text
x           = 10000 + 2^-11 + 2^-39
            = 10000.000488281252
high        = float(x)                    = 10000.0009765625
low         = float(x - double(high))     = -0.00048828125
packed      = double(high) + double(low)  = 10000.00048828125
float(packed)                            = 10000
```

该数值例子已用二进制单精度舍入运算验证。`low` 的单精度舍入丢掉了原始 double 中跨过中点的微小部分，使重构后的 `packed` 恰好位于两个 float 之间。ties-to-even 再投影选择 10000，而基线保存的 `high` 是 10000.0009765625，相差一个 float ULP（0.0009765625 Pa）。

同一个 `packed` 也可以由另一组高低位表示得到：`high=10000`、`low=+0.00048828125`。因此，**仅凭精确的数值和 `packed` 不能唯一区分基线先前保存的是哪一个 high**；这不是说 double 一般不能表示该精度，而是求和操作没有保留原二元表示的分解信息。

这证明“旧 high+low 重构成 double 后再 float 投影一定得到旧 high”不是普遍成立的。它允许稀少的空间算子输入差一 float ULP，但本轮尚未证明 q0 实際轨迹发生了这种情况，更未证明其放大到本次最大差异。

## 后续隔离方案（仅评估，本轮未实施）

1. 若只在新积分后执行 high/low roundtrip，可检查每步残差量化的影响，但不能单独排除结合次序和上述中点歧义，因此不宜称为严格旧实现模拟。
2. 更有针对性的诊断应复现 `oldhigh+(oldlow+increment)` 次序和旧 high/low 舍入，并记录中点事件。若必须用一个 double 作为测试状态，可在重构后投影不等于目标 high 时，使用 `std::nextafter(packed, double(high))` 移动一个 double ULP，以保留旧 high 投影。此为待验证的诊断编码策略，不是已验收的通用算法；应先对分解恢复、边界及极值作定向测试，不应放入正式求解器。
3. 隔离构建可把当前 `JSphCpu.cpp` 的副本放在 `tests/support/pore_double_stage1/JSphCpu_roundtrip.cpp`，仅替换三个积分写回。私有对象、PDB、执行程序及结果放在 `tests/outputs/pore_double_stage1/q0_roundtrip_cpu`，日志仍放在 `tests/logs/pore_double_stage1`，不改生产源码、正式案例或原结果。
4. 单独编译该副本，复用当前 ReleaseCPU 的已启用生产对象和库，包含 `main.obj`、排除原 `JSphCpu.obj`，插入私有对象。编译/链接参数须以权威工程和当前 tlog 为准，尤其保留 `/fp:precise`、优化、OpenMP 和运行库设置，不覆盖原对象、PDB 或 `bin/windows` 程序。
5. 使用同一 q0 配置、步数、后端及比较器，只换私有执行程序和新的输出目录。若差异明显缩小，才形成支持表示机制的运行证据；若不能缩小，应继续核查其他路径或编译因素，而不是事先认定原因。

本轮到此停止：仅保存审查记录，不构建上述变体，不放宽预设验收阈值，不把短回归差异解释为实际固结精度已经改善或已经恶化。
