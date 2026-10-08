# u-pl C/D/E：本轮实现与验收结论

2026-09-07。本轮已交付受限 CPU/Symplectic 的变孔隙率/变渗透系数、PR、时间步保护、输出及水力状态恢复实现；**不能将其称为完整 C/D/E 研究级验收通过，TPI 的精度和有效加速尚未通过验收。** 原 retrogressive landslide 算例所用的非平行墙/NoPen 等边界尚未扩展，不能只改总开关后直接用于该算例。

主要文件均在本目录第一层，不需要进入原始运行目录找结论：

- [01_修改位置.md](01_修改位置.md)：本轮 11 个生产文件逐函数、行号、功能和数值影响；以此前精度修复快照为增量基线，不把旧修改重复计入。
- [孔压对比图](final_r2_01_孔压比较.png)：PR、变 k PR、两档 TPI 步长的孔压过程及全土体 RMS 差值。
- [孔隙率、渗透系数与体积一致性图](final_r2_02_孔隙率渗透率与体积.png)：n/k 演化及代数/参考密度一致性。
- [README.md](README.md)：开关、配置示例、公式与使用限制。两张图均附同名 SVG，已实际查看导出结果，无标题/坐标重叠；r1 排版探索图保留，正式引用 r2。

## 1. 已接入什么

| 阶段 | 本轮实现 | 验收边界 |
|---|---|---|
| A 补充 | 新总开关 `HydroMechUpl`，默认关闭；原 `PoreDynamicDarcy` 单独使用仍为旧 A/B 常 n/k 动态项 | 两个开关同时显式配置且冲突则报错，不静默切换模型 |
| C | double `logJ` 状态、n 演化、Ck 指数 k 律、上下限拒绝、参考体积与真实混合密度区分 | 标量/实际算子及短时耦合测试通过；不等于大变形滑坡的物理标定完成 |
| D | 完整 `D(k*a_s)`、当前水力势扩散、PR、当前/历史零阶墙 ghost、一致 Shepard；显式选择的实验性 TPI | 固定平行平墙范围内局部检查通过；TPI 精度未过，多墙/NoPen/MLS 等未开发 |
| E | 当步 predictor/corrector 限步，ID 索引历史、双精度状态输出、带材料/模式元数据的 PART 加载与校验 | 水力状态恢复通过；现有机械冷重启不是完整精确热重启 |

新 k 律为 `k=k0*exp((e-e0)/Ck)`，不是 Kozeny–Carman 律。Ck=0 表示 k 恒定，**不表示 n 恒定**；k0=0 在 PR 下保持严格为零。n/k 越界、非有限或不支持的组合明确报错，不做静默裁剪。

体积使用 `J=exp(logJ)`、`V=V0*J`、`n=1-(1-n0)/J`。现有 `Rhop` 在新路径中为几何参考密度 `rho0/J`，真实惯性密度独立为 `(1-n)*rho_s+n*rho_w`。内力加速度按两密度之比缩放；原土体本构、屈服/软化规律不改。保留原对称机械 SPH 离散，不宣称逐式复现 Lian 全部动量离散。

TPI 去掉有限水压缩性储水项，采用整步压力历史的 Symplectic 适配，并非论文原 Leapfrog，也不是收敛的隐式 PPE 求解。它与有限 Kw 的 PR 不属于仅替换计算算法而保持完全相同物理方程的比较。

## 2. 编译与向后兼容

本轮最终生产源码已通过 CPU Debug、CPU Release 和 GPU Release：

| 构建 | 最终日志 | 结果 |
|---|---|---|
| CPU Debug | [cpu_DebugCPU_shepard_r1.log](cpu_DebugCPU_shepard_r1.log) | 0 错误，1 条既有 `/Gm` 弃用警告；早期全量链接还有第三方 PDB 缺失警告 |
| CPU Release | [cpu_ReleaseCPU_shepard_r1.log](cpu_ReleaseCPU_shepard_r1.log) | 0 错误、0 警告 |
| GPU Release | [gpu_release_final.log](gpu_release_final.log) | 0 错误、0 警告；仅验证关闭路径，未实现 GPU u-pl kernel |

未修改 CUDA kernel，本轮没有重新生成 GPU Debug，不能把此前 GPU Debug 当成本轮开启路径验证。

关闭回归与相邻 `00_upl_precision/precision_baseline` 中的精度修复后 CPU/GPU Release 分别比较。最终 CPU、GPU 各运行 **2000 步、dt=250 ns、Shepard 间隔 40、11 帧**；同输入、同物理时刻、按粒子 ID 对齐，全部导出 VTK 字段逐位一致，零排出、零 DtMin 调整。字段包括位置、速度、密度、应力、孔压/初始孔压/超孔压、自由面标签。此结论限已比较字段及该算例，不冒充任意算例或全部原始 BI4 数组的穷尽证明。

证据：[CPU 关闭回归](cpu_off_final_results.json)、[GPU 关闭回归](gpu_off_final_results.json)。最终 Release CPU SHA256 为 `a0ceb385e04684891c554e651e006d852240b368a86c6addf46e5e94c9ab6835`，与下述最终耦合试验及独立性能测试一致。

## 3. 最小数值验收

| 测试 | Debug / Release | 能说明的范围 |
|---|---|---|
| 标量材料闭合与非法状态 | 各 102/102 | 变 n、指数 k、零 k、小变形精度、固体体积/质量恒等式、TPI 标量公式 |
| 真实 BI4 写入/加载与生命周期 | 各 223/223 | 新旧格式、单/多 piece、类型/长度/有限值/参数一致性、排序与移除边界；只读 inspector CLI 另有 16/16 检查 |
| 实际 CPU 水力算子 | 各 72/72 | 2D/3D、Wendland/Cubic、反序 ID、仿射速度、常 a/线性 k、线性 a/常 k、零 k、旋转重力、静水与 Shepard |

三类最终 Debug/Release 结果各自相同。测试不是只重写公式在另一脚本里自证：空间算子 harness 链接真实 CPU 对象并调用生产 `InteractionUplRate()`。其非零制造场最大相对偏差约 `4.35e-8`。真实 Shepard 连续 20 次过滤，在任意 `PorePress0` 的当前静水场中，合成孔压最大漂移 `7.28e-11 Pa`，后续最大静水压力率 `2.87e-8 Pa/s`。

详细证据：[标量 Release](bin/upl_math_ReleaseCPU.results.json)、[加载器 Release](bin/upl_loader_ReleaseCPU_r2.results.json)、[实际算子 Release](upl_operator_ReleaseCPU_r2.json)。这些局部检查不能替代整场时间收敛、长时滑坡、任意边界或 TPI 稳定性验收。

最终 CPU/GPU Release 还重跑了 9 项预期拒绝测试：固定 dt 超限、初始 n 越界、初始 k 越界、开关冲突、TPI 零 k、关闭 u-pl 却选 TPI、GPU 开启、MLS 水力 ghost、未闭合不排水自由面。`guard_*_final_results.json` 均取得非零退出并匹配指定错误信息；不是把程序失败当作正常算例成功。

## 4. 真实耦合场与时间步比较

复用归档 `pair_symplectic` 的自重固结状态作为**新阶段初始条件**，不改归档原件。1000 土粒子 + 40 固定底墙，X 周期，初始 n=0.3、k0=1e-3 m/s、Kw=2e8 Pa；实际计算读取这些原参数的既有 float 值。五个最终案例均到 500 µs、11 个物理时刻、CPU 单线程，无粒子排出或 DtMin 抬步。

| 比较 | 步长 / 步数 | 500 µs 全土体孔压差 RMS | 同时刻最大单粒子差 |
|---|---|---:|---:|
| PR Ck=0，62.5 ns 对 31.25 ns | 8000 / 16000 | 0.00367516 Pa | 0.0121043 Pa |
| PR Ck=2 对 Ck=0 | 均 62.5 ns / 8000 | 0.000131473 Pa | 0.000416801 Pa |
| TPI Ck=0，125 ns 对 PR Ck=0，62.5 ns | 4000 / 8000 | 3117.49 Pa | 见逐帧 JSON |
| TPI Ck=0，250 ns 对 PR Ck=0，62.5 ns | 2000 / 8000 | 2140.67 Pa | 见逐帧 JSON |
| 同一 TPI 模型，125 ns 对 250 ns | 4000 / 2000 | 979.714 Pa | 1290.23 Pa |

压力均采用真实 PART 中 `PorePress+PorePressRes`，按相同土粒子 ID 和保存物理时刻比较，不能把 high-only 输出当成全部孔压。两档 TPI 的 α 均为 0.5，R 分别为 2、4；R 在代码中仅影响步长上限，不进入压力更新公式。

PR 两步长的孔压差在 11 个时刻的最大 RMS 也是 0.00367516 Pa；位置向量 RMS 的全时窗最大值为 `1.18e-10 m`，速度向量 RMS 最大值为 `7.32e-9 m/s`。这是同模型的两档步长一致性证据，不是解析误差，也不足以估计收敛阶数。

TPI 两步长在 11 个时刻中最大孔压 RMS 差为 **1348.35 Pa**。减小步长未让 TPI 自动贴近此处的 PR 解；模型储水假设与时间离散影响不能混为一谈。因此目前不通过 TPI 的“精度可控”验收，也不能根据位移很小就忽略孔压差。证据：[四模型完整分析](final_r2_分析.json)、[PR 步长减半分析](pr_refinement_r1_分析.json)。

还有一项单列的稳定性反例：冻结的两节点正权连接矩阵，每行邻接权重 0.9、排水参考权重 0.1，在 α=0.5 下存在约 -1.62664 的增长根。该反例不代表上述真实算例已经发散，但足以否定“正系数 + 排水锚点就保证外推 TPI 无条件稳定”。它没有被计入准确性通过数。

本短窗 PR Ck=2 的平均 k/k0−1 在末帧仅约 `1.36e-8`，单粒子范围约 `[-3.31e-6,9.26e-7]`。Ck 改变引起的孔压解差比 PR 自身两档步长解差还小，**不能用这个短时弱变形案例宣称变 k 已产生显著物理效应**。图中 `(1-n)J` 恒等式最大残差 `3.33e-16` 是代数一致性；结合原始 float Rhop 的参考体积残差约 `5.81e-8`，不是独立的全域守恒证明。强变形材料响应仍需后续专门测试。

## 5. 时间步、输出和重启

此案例新 PR 行对角限步约 `7.83e-8 s`，因此原 250 ns 被拒绝，62.5 ns/31.25 ns 通过。固定 dt 不能静默覆盖限制；自适应步长在当前 predictor 限制，corrector 再校核同一实际 dt。当前还没有 midpoint 超限的回滚重试，因此这种情况会明确停止，不会偷偷接受该步。

PART 保存三项 double 状态 `UplLogJ/UplPressurePrev/UplPreviousDt`、四项诊断字段和九项 schema/材料/模式元数据。原 PartVTK 不暴露所有新增字段，本轮另用真实 BI4 读取器校验，未修改或伪装旧 PartVTK 导出结果。

已直接读取四组最终 500 µs 计算的 44 帧，检查 **183,040 个实际存储诊断值**的字段存在、double 类型、长度、有限性、ID/元数据，并用独立公式复算。n/k/V/混合密度最大绝对偏差分别为 `2.22e-16`、`4.34e-19 m/s`、`0`、`9.09e-13 kg/m³`；全部输入及读取依赖前后哈希不变。V 为 `(MassById/rho0)*exp(logJ)`，不是无量纲 J；2D 按单位厚度约定。证据：[实际 BI4 诊断字段验收](diagnostics_stored_final_r2/result.json)。新独立工具首次 r1 因 VS 环境初始化失败未读到数据，失败证据保留，修正调用后使用 r2 完成验证；未改生产代码或旧 helper。

注意输出语义：**土粒子的 n/k/V/混合密度是状态诊断；墙粒子输出的是其 ID 参考状态，不等于当前水力遍历中插值的 ghost k，也不等于 MassBound/当前 mDBC 密度的数值体积。** 不应拿墙诊断值推断实际墙通量或把它当土体材料分布。两张主图仅统计土粒子。

PR 与 TPI 均完成实际 PART 重启：1000 土粒子的 `PorePress/PorePress0/PorePressRes/UplLogJ/UplPressurePrev/UplPreviousDt` 在源 PART 与重启初帧按 ID 精确数值相等，并继续完成后续步。这里比较的是 JSON 数值，不是区分 +0/-0 的原始字节。更改 Ck 或 TPI 旧步长的重启被拒绝。证据：[PR 恢复](restart_pr_r2_restart.json)、[TPI 恢复](restart_tpi_r2_restart.json)、[拒绝材料不一致](restart_bad_ck_r1_restart.json)、[拒绝 TPI 历史步长改变](restart_bad_dt_r1_restart.json)。

**mDBC 重启源必须设置 `SaveExtraParts=1` 并保留 PartExtra 法向。** 初次两项测试因旧输出不含附加法向失败，r1 失败报告保留；补足测试源输出配置后才通过 r2。旧 u-pw PART 无新状态时仍可启动新阶段，但会重置 J=1 和零斜率压力历史并提示；旧机械塑性历史等初始化规则未被本轮改为精确热重启。

## 6. 独立效率验收：有测量，没有等精度加速结论

使用最终 Release 与精度快照 Release，1040 粒子、CPU 单线程、同一 50 µs 窗口；每种预热一次，再按 ABC/CBA/ABC 顺序测三组配对，共 12 次。禁止同时运行求解器/构建，记录 Windows 进程时间/峰值内存，关闭粒子时序输出和转换。仅有求解器自带的四个小型初始化诊断 VTK，名称、大小和哈希均记录。所有测量零排出、零 DtMin 调整。

| 配置 | dt / 步数 | 3 次进程 wall 中位数（范围） | 求解器计量常驻数组 |
|---|---|---:|---:|
| A：精度修复后 u-pw | 62.5 ns / 800 | 8.894 s（8.875–9.019） | 1,526,483 B |
| B：u-pl PR、Ck=0 | 62.5 ns / 800 | 13.472 s（13.140–13.833） | 1,593,043 B |
| C：u-pl TPI、α=0.5、R=4 | 250 ns / 200 | 2.018 s（1.986–2.019） | 1,593,043 B |

同组配对耗时比的中位数：**PR/u-pw=1.518，即增加约 51.8%**；TPI/PR=0.1474。后者仅是不同模型/步数的原始耗时比，不是等精度有效加速；统计文件中 `accuracy_accepted` 与 `effective_tpi_speedup_accepted` 明确为 false。

常驻状态数组增加 66,560 B，即本案例 1040×64 B。每次新水力遍历还有临时数组，不计入该常驻数组数字；进程峰值工作集的中位数分别约 14.49/14.75/14.68 MB。新水力邻域遍历目前串行，不能将这项小规模单线程结果推广到大规模 OpenMP/GPU 滑坡。后续可复用临时缓冲区、减少重复材料派生和并行独立粒子行，但需要另做大粒子数/线程数扫描。

证据：[独立性能测量](perf_idle_r2/benchmark.json)、[复现脚本](benchmark_cde.py)。首个批次 `perf_idle_r1` 因脚本把初始化诊断 VTK 也误判成粒子输出而停止；确认只有四个初始化 VTK 后收紧判据，使用新标签 r2 重跑，旧失败证据未覆盖。

## 7. 本轮不宣称完成的内容

- 当前开启路径仅 CPU 单机 Symplectic；GPU 只验收关闭路径。
- 非平行墙/角点/曲壁/NoPen、MLS 水力插值、移动/浮体/DEM、额外压力荷载、shifting、density diffusion、非等势周期、不排水自由面闭合仍不在支持范围，由配置或运行检查拒绝。
- 原本构未修改，但新孔压与惯性会影响应力演化；未校准 retrogressive landslide 材料，也未完成整场滑坡验证。
- 没有宣称严格全域守恒、全状态机械热重启、PR 收敛阶数或 TPI 长时稳定；TPI 缺少同一物理问题的解析/PPE 参考和精度阈值验收。

后续应先让 TPI 的一致初始压力、冻结算子稳定性和同物理固结参考过关，再评估有效加速；不能只增大 R 或偷偷换成另一种松弛/隐式算法就宣称原方案成功。研究算例所需 NoPen/多墙边界与大变形 n/k 检查仍是独立开发任务。当前默认 PR 与关闭路径保留可用，TPI 明确保持实验性。

本轮未提交或推送 Git；未清理、覆盖原精度快照、归档算例及失败原始证据。图按数据可视化技能的要求对齐同时间/同 ID、保留差值单位与模型假设说明，并实际检查 PNG；没有把图形代数残差用作物理准确性的替代证明。

最终证据核验入口为 [verify_cde.py](verify_cde.py)：默认只读检查，`--write --label 新标签` 才保存新清单；核对生产增量、测试源码/二进制、原始 PART、关闭比较与上述结果，不覆盖旧清单。最终 [acceptance_final_r2.json](acceptance_final_r2.json) 共 151 项证据检查通过，包含修改位置文档行号校正后的最终哈希；r1 保留。`evidence_checks_passed` 仅表示证据核验通过，`full_cde_research_acceptance` 和 `tpi_accuracy_accepted` 保持 false。
