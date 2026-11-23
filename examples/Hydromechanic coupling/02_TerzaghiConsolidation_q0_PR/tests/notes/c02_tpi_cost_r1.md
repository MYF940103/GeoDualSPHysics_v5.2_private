# C02 高渗透率的同机精度与成本比较

准备日期为 2026-11-23。五个输入及 CPU/GPU 共用离线审查器已准备，尚无这五组的真实运行结果。优先完成 C08 大变形证据，再在同一块 GPU 上依次单独计算。CPU 单线程可用同一输入重复整套比较。跨设备结果分开报告。

## 第二轮独立显式参考

原先显式 2.5 和 4 µs 两组 GPU 都在排水前触发力学限值，分别为程序步号 20 和 11，退出码均为 1，最后保存文件均为 Part_0000.bi4。1.444 µs 是旧内域离散谱的显式中点界，用于选择更细的试验步长。运行证据和配置保留。新增组单独记录于 `tests/configs/c02_tpi_cost_ref_r1.json`。

| 组 | 模型 | 计算步长 | 更新数 | 终点实际标量时钟 |
|---|---|---:|---:|---:|
| kw10 | 显式有限 Kw | 1 µs | 192,186 | 0.19218600000017153 s |
| kw125 | 显式有限 Kw | 1.25 µs | 153,749 | 0.19218625000020062 s |

两组的初态、k、材料、加载／排水、保存计划都沿用原算例。输出分别取初始、事件前、事件后首步，以及 ΔTv=.005 的十个目标。新独立锚点为 kw10。kw125 须先直接满足相对 kw10 的原门槛，才有资格作更快显式基准。TPI 同时直接对 kw10 及选定参考组评定，误差带不叠加。之后的正式汇总使用本段规则。下方先期五组表和基于 kw25 的说明保留原方案的历史含义。

单组原生审查仍使用 `support/c02_tpi_cost_review_r1.py <cpu|gpu> <组名>`。已有原生收据后使用 `support/c02_tpi_cost_ref_review_r1.py <cpu|gpu> <候选> --reference kw10` 或 `kw125` 可独立复核精度，无需重新读取 BI4。汇总脚本不带参数时只列出现有实际状态；全部测试或诊断收尾后用 `--publish` 输出正式汇总和 status.csv。缺少运行证据的后端标为未测；非零退出保留首个原始异常、退出码、最后实际保存记录，排除其用时比。两个合格完成组才能比较耗时。

### 可选的单一中间步长

只有经同端审查确认三轮 TPI 的 4 µs 组满足原精度门、10 µs 组未满足，且确需 R>1 的方案时，才考虑 `tpi625`。候选固定取 6.25 µs、R=1.4，其余材料、加载、边界、输出、门槛与三轮 TPI 原样。初态未放大水力上限为 4.76603 µs，6.25 µs 对应需求 1.31136；1.4 给出的初始水力界为 6.67244 µs。其后逐阶段仍由求解器检查实际限制。该组包含 30,750 步，事件前和首后保存步为 1,600 和 1,601，终点为 0.19218750000012905 s。默认准备列表及未实际选择时的汇总均不纳入该组。手动运行会先读取已验收参考和两条 TPI 轨迹的实际收据；筛选依据写入启动记录。

## 现有可用基线

高渗 GPU 显式 1 µs 和 1.25 µs 在 Tv=0.005/0.05 的孔压 RMS 分别为 179.314/84.544 Pa 和 179.333/84.539 Pa。二者均覆盖 13 帧；1.25 µs 通过相对 1 µs 的原精度条件，实际耗时 1176.02 s，1 µs 为 1493.81 s。TPI 的 2.5、4、10 µs 在最后目标的压力增量及两个目标的顶部沉降条件上均未达到显式参考。原定 6.25 µs 的前提在 GPU 上未满足。

为了区分真实积分步长与积分方法的作用，两端显式检查完成后，在仍缺少合格 TPI 组的情况下，将三轮 TPI 固定为同端最快合格显式参考的步长，R=1，复用同一材料、加载和粒子。先核第一个精度目标 Tv=0.005，与显式参考按相同保存步、同一材料 ID 对照；独立的 1 µs 锚仍参与判断。此处早于 0.1 s，后段应力限制须在全窗中检查。只有本端第一目标合格才扩展至 Tv=0.05。首目标的实测耗时和 13 帧全窗用时分别记录。[同一步长对照](../support/c02_tpi_same_dt_r1.py)

- 正式 k=10⁻³ m/s 的 u-pw 是 Vel0 底壁、1 µs 步长。RTX 3050 的原始 2 Tv 计算为 7,297,429 步、7,299 帧，主循环 34,651.480 s。根目录当前正式 XML 已改为 ΔTv=0.005。原始完整场和正式图表作为 u-pw 物理背景保留。
- 另有同机、同窗口的 5/10 µs 旧 u-pw 证据。k=10⁻⁴，15 s 生产积分窗口各 15,001 帧，5/10 µs 记载的积分时间分别为 13,853.219/9,162.136 s，实际进程壁钟为 13,855.808/9,164.119 s。跨步长孔压 RMS 的逐帧最大差为 4.17837 Pa，顶部沉降差的最大值为 0.000290012 mm。该旧方法可以说明实测用时比约 1.512 与步数比 2 不同，不能据此预测有限 Kw 与三轮 M0 的成本。原始记录在 `tests/logs/gpu_spr_15_{c,h}_r1.run.json` 和 `gpu_spr_15_pair_review_r1.check.json`。
- k=10⁻⁴ 的动态有限 Kw 和三轮 M0 使用同一 FreeSlip 加载柱。2 Tv 终点分别为孔压 RMS 0.57051 和 0.41443 Pa，顶沉降 3.68385 和 3.68412 mm。有限 Kw 在 CPU1 运行 148,603.906 s，三轮 M0 在 RTX 3050 运行 148,738.234 s。独立的后端和观察开销影响了两者耗时。
- 公共 Model0 的 CPU/GPU Release 各自与同后端旧程序 6 步 4 帧，15/15 原生数组逐位相等；Model1 在 C04 的对应回归为 22/22。C02 公共 Model2 与原私有程序的压力、坐标和应力等 21/22 数组逐位相同，公共 Rhop 按当前 J 回写。两个公共后端的真实共同短帧按 ID/时钟直接比较，C02 Model2 三帧最大孔压 RMS 5.965×10⁻⁶ Pa、位移差最大 8.239×10⁻¹² mm；C04 Model2 五帧分别为 8.352×10⁻⁷ Pa 和 2.194×10⁻¹⁴ mm。证据在 C02/C04 的 public_tpi_column 和 public_tpi_sphere4hist 输出。
- 已回传的 C04 私有峰窗有 577 帧、36,864 步，服务器 A6000 主循环 6,257.600 s。公共 C04 的 1 Tv 尚缺对应回传目录，入口及预期输出见 C04 根目录 README_Cryer_TPI_nu030_1Tv.md。

### 直接证据

以下位置以 `examples/Hydromechanic coupling` 为起点，2026-11-23 查阅。文件名中的 CPU/GPU 表示记录实际运行的后端。

| 结论 | 可核查文件 |
|---|---|
| 高 k 的正式 Model0，1 µs 原始密集输出与当前 ΔTv=.005 配置 | `02_TerzaghiConsolidation_q0_PR/CaseTerzaghiConsolidation_q0_PR_full_k1em3_release_GPU_out/Run.csv`、同 case 的 `CaseTerzaghiConsolidation_q0_PR_full_k1em3_Def.xml` 和 `figures/full_validation_release_k1em3_GPU.check.json` |
| 同机旧 Model0 的 10/5 µs、15 s 实耗和精度 | `02_TerzaghiConsolidation_q0_PR/tests/logs/gpu_spr_15_c_r1.run.json`、`gpu_spr_15_h_r1.run.json`、`gpu_spr_15_pair_review_r1.check.json` |
| k=10⁻⁴ 的整程 A/P3 终点指标、步数及不同设备主循环实耗 | `02_TerzaghiConsolidation_q0_PR/tests/logs/upl_tpi_p3_full_physics_r1.check.json` 和同 case 下 `tests/outputs/upl_bigstep_2tv_CPU1_r1/Run.csv`、`tests/outputs/upl_tpi_p3_B10us_full2tv_GPU_r1/Run.csv` |
| 新旧程序同后端的逐位回归 | `04_CryerProblem_PR/tests/logs/public_tpi_regression_r1.json` 的 `final_checks`。Model0 的实际前后对照为 C02 `public_tpi_upw_cpu_final1` 与 `public_tpi_upw_gpu_final1`，Model1 为 C04 `public_tpi_upl_cpu_final1` 与 `public_tpi_upl_gpu_final1`，两者各自的五个时钟字段均逐位匹配。 |
| 公共 Model2 两端之间的真实场差 | C02 的 `tests/outputs/public_tpi_column25_cpu_hist1/result/data` 与 `tests/outputs/public_tpi_column_gpu_hist1/result/data` 有 0、13、25 已完成步的三个同钟原生帧。C04 的 `tests/outputs/public_tpi_sphere4hist_cpu_hist1/result/data` 与 `tests/outputs/public_tpi_sphere4hist_gpu_hist1/result/data` 有 0–4 步五帧。先按原材料 ID 排序，再计算同一帧的孔压 RMS 及 XYZ 位置差模长的最大值，最后在共同帧间取最大。 |
| Cryer 峰窗、正式包和待回传结果的区别 | 实际服务器峰窗 `04_CryerProblem_PR/CaseCryer_TPI_P3_nu030_peak_r1_GPU_out/CaseCryer_TPI_P3_nu030_peak_r1_GPU_out/Run.csv`。公共 `Cryer_public_SPH_TPI_nu030_1Tv_Windows_RTXA6000.zip`、`CaseCryer_TPI_nu030_1Tv_Def.xml`、`xCaseCryer_TPI_nu030_1Tv_win64_GPU.bat` 已在 C04 根目录；截至本次核查，本地缺少其 `CaseCryer_TPI_nu030_1Tv_GPU_out` 输出。 |

## 本次共同输入和门槛

固定使用真实公共 FreeSlip 土柱的初始粒子、法向、材料和全部 40 个固定边界及 1000 个土体 ID。取 k=10⁻³ m/s、Kw=2×10⁸ Pa、n0=0.3、H=1 m、q₀=10 kPa、h=0.018 m，加载和开排水定在 t=0.01 s。解析无量纲时间采用既有 g=9.81 m/s²，三轮 M0 和有限 Kw 各取未拟合的相应解析解。参照模型 A=Model1、B=Model2。每组从同一初态独立启动。

| 组 | 计算时间步长 | 水力 R | 步数 | 用途 |
|---|---:|---:|---:|---|
| kw25 | 2.5 µs | 原有限 Kw | 76,875 | 显式参考 |
| kw40 | 4 µs | 原有限 Kw | 48,047 | 比较显式模型允许的较大步 |
| tpi25 | 2.5 µs | 1 | 76,875 | 同步长模型开销 |
| tpi40 | 4 µs | 1 | 48,047 | 同步长模型开销 |
| tpi100 | 10 µs | 2.25 | 19,219 | 扩大水力限制后的短窗精度和成本 |

R 只乘水力 dt_l。以 γw=9806.65 N/m³ 计算，初始限制 dt_l≈4.766 µs，R=2.25 时为约 10.72 µs。每一实际力学和孔压阶段仍要独立检查力、波速/黏性、水力与 HG 限制；步长恰好能进入初始窗口不能替代全窗检查。R>1 必须使用已经通过实际 R 配置回归的新程序，不能借改 PoreDtSafety 实现。原有完整解的最小界来自 k=10⁻⁴；不能当作高 k 真实轨迹的数值。

每组 13 帧，包括初始、事件前闭态、开排水后第一步和 ΔTv=0.005 的十个时刻。末帧目标 Tv=0.05，按实际保存步重新计算真实 Tv。每个目标在自身实际时钟上应用 512 项理论，按初始材料层聚合。原十个理论验收时刻中，本窗覆盖 Tv=.005 和 .05。两者要求层孔压 RMS ≤ 显式同机参考 +10 Pa、顶部绝对沉降误差 ≤ 参考 +0.001 S∞、底部绝对误差同时 ≤0.005 mm 及参考 +0.002 mm。t≥0.1 s 的每个已保存时刻仍检验竖向总应力和顶两层差各 ≤100 Pa。对中间 ΔTv 输出同时给出精度历史。各时间层输出压力、位置、真实 signed 步长、排水/载荷、固定标记、J/n/V/ρ/k、应力/弹性、HG phase/cache/dt/旋转等应通过原守护。参考及候选各自通过后，才按同等精度比较耗时。

## 运行和记录

成本报告中的 `predeclared_target_noninferiority_pass` 只回答两个预先规定的时刻（Tv=.005、.05）是否达到孔压与沉降误差带，同时检查 t≥.1 s 的全部保存应力。模型 1 用有限 Kw 的解析参考，模型 2 用 M0 参考。两者的归一化时钟沿用原方案，各自在实际保存时间评价。相对 kw40 计时时，kw40 和候选必须分别直接满足 kw25 的误差带，候选还须满足相对 kw40 的误差带。参考和候选两端都检查底部绝对误差 ≤.005 mm。通过只支持该短窗的成本对照，不能外推到 2 Tv。

同一组 CPU 与 GPU 都有完整结果后，用 `python -B support/c02_tpi_cost_cross_r1.py tpi100`（或其他组名）作独立跨后端检查。报告保存在 `tests/logs/c02_tpi_cost_r1_<组名>_cpu_gpu.json`。每组的两个后端共用同一 XML。离线预查的 13 个时钟在 2.5、4、10 µs 三个步长下分别结束于 0.19218749999978404、0.19218800000010958、0.19219000000005143 s。原生结论要求每一帧两端实际时刻、步号、dt 和 1,040 个 ID 均对应；各端各保留自身的有符号 dterror。1,000 个材料点全体孔压 RMS ≤5 Pa、单点 XYZ 位移差模长最大值 ≤.005 mm 是跨后端重复性指标。报告另列 22 个原生字段在土体和边界上的逐分量差，以及张量次序 xx、yy、zz、xy、yz、xz 的有效应力和总应力差。不同模型相对解析解的精度仍按上段的两个预设时刻评估。

审查器在每帧检查原生配置与迭代历史。显式有限 Kw 沿用没有 `HydroMechModel` 字段的旧输出格式，其动态渗流与 schema 字段标识了求解路径。公共 TPI 在 R=1 时保持原布局，在 R>1 时每帧必须包含可核对的双精度 `HydroMechTpiR`。运行器记录主机、所用程序、实际命令与墙钟，审查器逐项核对启动、结束和实际 XML；只比较同主机、同设备、同程序的测量。主循环包含正常保存开销，同时单列原生字节数与求解器保存计时。

在 case 的 tests 目录中使用以下命令。prepare 只校核或创建 XML。run 只运行指定的一组，遇到已有输出路径即退出。保留旧日志、输入和输出。GPU 各组串行运行并保持同一显卡、驱动、程序和输出配置；CPU 比较时一律使用 CPU1。

```powershell
python -B support/c02_tpi_cost_r1.py prepare
python -B support/c02_tpi_cost_r1.py run --lane kw25 --backend gpu
python -B support/c02_tpi_cost_review_r1.py gpu kw25
```

缺省使用项目 bin/windows 的正式程序。所有组也可显式传入同一个 `--exe D:/path/to/candidate.exe`，使用该隔离构建和紧邻可执行文件的 DLL；记录实际绝对路径、大小、修改时间与命令行。不同程序或不同设备的结果只能描述，审查器拒绝将它们作为同机同程序效率对照。

其余组依照同一方式。比较使用例如 `python -B support/c02_tpi_cost_review_r1.py gpu tpi100 --reference kw40`。先比较 kw40 对 kw25 的精度，选择合格的最高效显式结果作为等精度参考。报告分别列出进程壁钟、求解主循环、Run.csv 中总耗时、SU-SavePart 秒数及原生输出字节数。GenCase 种子已冻结复用，独立后处理耗时另计。单次观测用于选择下一步；若差异处于系统背景波动范围，记为未分出优劣。原有正式结果不重跑。

两端五组运行及各自原生、跨端审查结束后，执行 `python -B support/c02_tpi_cost_summary_r1.py --publish`。工具读取既有收据，在 `tests/figures/c02_tpi_cost_r1` 一次发布两张图、三张配套表和中文小结。history.csv 保存每个实际时刻、目标 Tv 及三个理论误差；timing.csv 同时给出参考组、实测耗时比和通过验收后的耗时比。某组速度更快但超出误差带时，后者留空并记录原因。
