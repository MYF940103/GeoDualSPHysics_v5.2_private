# Cryer CPU Debug 启动基线（准备状态，尚未执行）

本轮只准备一个独立的 1 ms 启动检查，不修改生产源码、正式 XML/BAT、物理方程、外载离散或已保留的结果。先等 Lian 服务器便携包核验完成，再由主任务启动；本脚本不建立 worker/notifier，也不自动接入长算。

## 唯一输入差异

复制 case 根目录 `CaseCryerProblem_PR_Def.xml`，保留 `dp=.0025 m`、`R=.05 m`、`k=1e-5 m/s`、原 `FlexibleConfinement` 模式 2、`q=10 kPa`、无斜坡、t=0 排水、eta=.02、DBC、5 μs 固定步长、原球体及远处 dummy boundary。

仅改 `SavePosDouble=1`（输出精度），`TimeMax=.001 s`、`TimeOut=.00025 s`（预期含初态共 5 帧），显式声明原默认 `SPR=0 / HG xi=0 / stress-gradient correction=0`，并同步这两个时间设置的注释。持续应力状态保存为 double，孔压状态及孔压率仍为 float，不是全双精度 u-pw。

新文件为 `tests/configs/cryer_start_r1_Def.xml`、`xcryer_start_r1_win64_CPU.bat`、`tests/support/cryer_start_r1.py` 及本说明。BAT 沿用正式程序变量与错误处理，固定使用 CPU Debug、8 线程，拒绝已存在输出且不调用 PartVTK。

## 启动与证据

主任务确认后，从 case 根目录运行：

```powershell
D:\Anaconda3\python.exe -B tests/support/cryer_start_r1.py
```

程序仅 hidden 启动一次标准 GenCase＋CPU Debug BAT。启动前检查本地 Cryer 求解器及同名结果；绑定源码、工程、程序及 DLL、正式与测试 XML、BAT、旧载荷审计和原生 reader 的 SHA256。输出 `tests/outputs/cryer_start_r1`，日志和运行／检查清单在 `tests/logs`，小型汇总 CSV 在 `tests/figures`。失败记录准确时间、原错误、traceback、所属停止结果，并保留所有原始输出，绝不覆盖重跑。

跨 case 只读依赖为 `05_LianFlexibleStrip2D_PR/tests/outputs/hydro_native_r1/ReadHydroNative.exe` 及其 `tests/scripts/read_hydro_native.cpp`。reader 哈希固定为 `5d8fbeadc5f5b953eff85457c1bff690e22afc06a345d6d752113a1fa8f52502`；它按原生 ID 输出孔压 `DatFloat`、持久应力 `DatDouble3` 和保存位置类型。不得清理该 reader 依赖。

## 原安全检查与诊断边界

逐帧要求有限值、无排除、37173 个原生土粒子 ID 一致、正密度、零塑性应变、double 位置／应力标志和真实 `HydroMechLoadAce` 数组存在。非零时刻独立保留 `has_dterror=1` 及 `max(DtFixed-DtVariable)<=1e-14 s`；这是每个保存区间的机械候选步长统计，不是累计时间舍入误差，也不证明孔压扩散安全。若失败，报告具体值／帧／时间，不调阈值。

`JSphCpu::DtVariable` 先计算 `dtw=PoreDtSafety*rho_w*g_h*n/Kw*h^2/k`，但 `FixedDt` 分支不执行 `min(dt,dtw)`。本 case 的 h≈.0045 m、Kw=2e8 Pa、n=.3、k=1e-5 m/s 给出 dtw≈2.9788 μs，原 5 μs 为其约 1.678 倍。这里只保留 5 μs／约 200 步用于复现诊断，不伪称满足 PoreDtSafety；每帧和最终检查单独报告 `poreDiffusionDt_s`、步长比和 `configured_pore_limit_respected=false`，明确不自动准入更长计算。此事实可能关联旧启动震荡，但单凭此项不是因果证明；本轮不改步长、阈值或源码。

真实排水集合为全部 `FSType=2 OR 3`，每帧必须非空且孔压严格为 0。记录初始 FSType 数量、各帧数量以及相对初态的 ID 分类变化。代码动态追踪自由面；短窗实际未发生分类变化也要如实记录，不能把动态算法称作固定集合。

柔性球形围压是原有成对核支持分布外力，不是仅在 `FSType2/3` 上施力。全部实际载荷求和后记录径向外力、合力、转矩及归一化一阶矩，并另列真实自由面与其余粒子的载荷数量。初态数组为第一轮相互作用前的零值，不等于物理压力为零。非零帧要求实际向内载荷非零，不把几何球面面积或均匀应力当作逐粒子精确真值，不套用一维 100 Pa 阈值。

旧 `cryer_load_audit_r1.json` 已表明：只修正外载而不修正内部算子会破坏均匀应力抵消；本轮不合入任何该类修正。保留旧 37173 点球体和其 native 体积／几何球体比值，仅记录，不假定质量错误或擅自归一化，也不重复 KDTree 网格扫描。记录初始最小／最大半径及 r≤1e-10 m 的 native 数量；GenCase 球壳分布不一定存在 r=0 粒子，后续中心孔压必须声明固定材料球平均或插值，不能预设某个 native ID 就是球心。

1 ms／约 200 步检查不比较理论曲线、不绘图、不等于 Cryer 完整时长或半步长验证通过。下一步依据真实启动结果再决定，不因正常退出直接宣称物理验收。
