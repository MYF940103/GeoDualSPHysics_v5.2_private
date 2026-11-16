# Cryer CPU XYZ：两个 TU 的极短 TPI 接入作者稿

状态：仅作者准备，尚未执行 overlay prepare、编译、程序或原生读取。
本阶段不提供 solver/128 步 runner/native 脚本，也不准入正式计算。

新增文件：

- `tests/support/upl_tpi_cryer_cpu_overlay_r1_prepare.py`
- 本说明。

根线程完整审读后可独立准入一次 prepare；它只在新标签复制文件：

- `tests/outputs/upl_tpi_cryer_cpu_overlay_r1_source/`
- `tests/logs/upl_tpi_cryer_cpu_overlay_r1.prepare.json`

根 prepare-only admission 的 `stage` 为
`upl_tpi_cryer_cpu_overlay_r1.prepare_admission`，`passed=true`、
`prepare_only=true`；`inputs` 用实际路径/长度/mtime_ns 绑定全部所消费文件。
作者稿、本文、完整 C04 prepare 收据/manifest、266 个源/私有 helper、
两份 VS 文件、两份 docs、保留短窗 XML、C02 已测/作者 helper 和 C02
原挂接作者稿均须列入。脚本不运行 Git 或 SHA；不导入/执行 C02 prepare。
新目录或新 receipt 已存在即拒绝；任何失败保留部分新文件和真实第一原因。

## 采用的完整源码家族

输入是已由根线程实际准备并通过的
`upl_tpi_cryer_cpu_r1_source`，不是当前公共源码，也不是 C02 的旧 84 个
对象。完整来源为 253 上游档案原字节＋8 freebody ZIP 原字节＋4 Git
GPU-HG 基线 blob；这仍是明确的新恢复源树，不追认旧 DebugCPU 全部
201 个依赖的编译时内容捕获。

新目录原样复制其 VS、docs、generic helper 和其他 263 源文件，仅改
`source/JSphCpu.cpp` 与 `source/JSphCpuSingle.cpp`。原 manifest 作为
`base_source_diff.json` 保留，新 manifest 另写 `source_diff.json`，不会
覆写原树。两个改动 TU 统一为 UTF-8/LF，其他文件逐字节复制核对。

后续必须新编译完整 DebugCPU 86 TU；本 prepare 不构建、不混用任何旧
对象、不安装程序、不改现有 C02 CPU/GPU freeze 或原 C04 结果/PRE。

## 真实程序的窄资格

默认 A（环境变量缺省或精确 `A`）的所有新数值分支均不进入，不创建
TPI sidecar、不调用额外力/压力步骤。仍须后续真实 A/native 比较来证明
无反馈，不能把代码审阅当作位相等证明。

私有 B/C 仍使用既有 `UPL_TPI_CPU_R1=B/C`；没有新增 XML 开关。它们
只在新的 C04 三维 freebody 原条件下允许：

- fresh、无 restart，所有 37181 native IDs：8 fixed＋37173 soil；
- Symplectic、实际 `dt=2^-20 s`，明确 `NstepsBreak` 为 1–128；
- 原 Wendland H/dp=1.8、dp=.0025、H=.0045，非周期、原远端 DBC；
- k=1e-5、n0=.3、Kw=2e8、ρw=1000、ρ0=2100、E=2e6、ν=.3，
  原高黏聚力 elastic 材料，grad1，原 corrected divergence；
- 原始 FlexibleConfinement q0=10000、ramp=2^-8、drain=2^-7，
  原 fixed-grid/source-clock 策略不变；
- HG0、SPR0、AS0、AV=.1、η=.00004，Shepard0、constant-k，无新增稳态技术。

`ConfigDynamicPoreFreeBody` 的原始 rest/ID/几何/远端 DBC support clearance
检查仍完整执行；动态 Rate 中逐 receiver 的 separation envelope 检查也
不修改。没有从其他案例搬入新 body radius 或重新拟合球面/荷载。
本上限只覆盖原 A 的 128 步启动资格；不能声称排水后峰值、完整周期或
精度验收。原 XML TimeMax 可以保留，但 B/C 必须有显式 at-most-128 cap。

## 数学和实际时间层

复用 C02 已测 generic helper 原字节：B 的 α=.5、C 的 α=0、β=0。
同一个 history prediction 同时给机械 half 和 endpoint 初猜：

`q = pn + α (pn - pPrevious)`。

C 数值路径不读取历史值，B 使用 native-ID-owned 完成步历史，冷启动
`pPrevious=pn`。在现有 Symplectic 内这是单次邻压预测/defect correction
变体，不是原文 literal LF、全局隐式解、二阶或无条件稳定算法。

`S = -k Σ w` 仅是原 leading-LP 的正预条件，不冒充完整 Jacobian。
`Rγ = -γ θ + k [LP - gradPcorr·Lx + ρw Da]` 在原三维 Rate receiver
循环内直接以 double 捕获，`w`、Taylor/closed-FS Neumann defect 和
XYZ 加速度散度全部保持原算序；不从 float `PorePressRate` 反算 residual。
旧 rate 仍正常计算并保留其原 finite/必要时步检查，它不是 M0 的 `dp/dt`。

原 `ComputeSymplecticCorrPorosity` 和六应力/塑性 corrector 仍各更新一次。
extra endpoint 位于原 actual geometry/cell divide 之后、原 scalar
`TimeStep += stepdt` 之前，只重算 force/rate。helper 对真实 XYZ 位置、
四分量 vel/rhop、六分量 stress、κ、P0、J、pressure guess 做 bit 检查，
禁止额外 force 改写这些已提交 soil 状态。Jhalf/θhalf 从原 corrector 前
捕获，Jfull 从唯一原 porosity corrector 后捕获；endpoint θ 不替代 J 积分。

随后先完成全部 row 验证，才写最终压力，再调用原
`ApplyPorePressureBoundaries`，按原真实 drained receiver 提交 +0 和 history。
失败不旋转历史，不自动保存 rejected endpoint 或重试。

HG 在本阶段必为零且没有对象：不挂 C02 readonly HG adapter，不调用
CaptureHG/CheckHG，不虚增 HG 检查数。generic helper 的 HG 模板保留
原字节但不实例化/调用，summary 的 HG checks 应为 0。

## 后续必要而尚未执行的资格

根线程独立 full DebugCPU 86 TU 构建后，才可考虑真实 A/B/C 128 步。
先验证新 A 对保留原 C04 CPU 128 步的真实共同 clocks/IDs/22 typed
数组与原 safety，再分别检验 B/C 生命周期、完整 XYZ Rγ、P0/J/κ、
真实 native save 和 sidecar。无任何新的 half 链或 CPU 长峰窗被本稿准入。
128 步均在 drainage 开启前，所以已有/后续独立实际 row/BC 小组件的
覆盖不能省略；不能以此启动区替代排水后或理论精度验收。

所有原程序、原 8 文件 ZIP、raw BI4/NBI4、旧图 CSV、服务器数据及暂停
C08 的 owner/GPU 均原位保护。本稿不接触它们的依赖或进程。
