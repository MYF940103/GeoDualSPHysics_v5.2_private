# P1 staged-load 完整 2Tv 准入缺口 r1

2026-11-17，只读规划。仅新增本说明；没有准备 solver 输入、运行 admission、build、reader 或新计算，没有改动任何冻结作者稿/程序/活动依赖，也没有操作 C08。下列项目是条件清单，不是根已批准完整周期。

## 首要分支：先完成当前 2s 的真实审查

当前唯一候选为 `upl_tpi_p1_loadclock_B10us_window2s_GPU_r1`，原定 199996 更新/1263 帧、dt=tD/1000、actual end 2.00000577545594s。正常退出、native passed 或科学分析完整都不自动通过物理预算。

准入完整周期至少需要当前 run/read/review 各自真实通过，并由根检查新 science 的 PNG/CSV：两个已覆盖 Tv=.005/.05 的孔压/顶底材料沉降预算、全部 t>=.1-1e-7 的 100Pa 层总应力/top-gap、startup mean-p/J、1.5–2s 的 Q/100层交替X模态及新减旧 B10 的差异。`analysis_complete/passed` 与 `planned_budgets_passed` 必须区分；旧 A 失败不能豁免新 B。

**若任一原预算失败，不准入完整周期。** 保留当前 solve 和 derived 结果，转向已授权因果诊断：确认误差在闭载建立、排水事件、压力/总应力/应变分解或已有空间误差中的来源，先利用同钟旧 B10/A 证据，不补一串 half/reference，也不通过改参考高度、荷载、Cv、时间原点或阈值使其通过。

## 若 2s 原预算全部通过，仍有的最小实施缺口

| 项目 | 已有内容 | 完整周期前仍需补的最小内容 |
|---|---|---|
| 私有运行窗口 | 当前 source 的 M0 分支只允许 TimeMax<=2s。 | 在新 source 标签中，仅为本 B10us 完整周期增加精确 endpoint/nsteps allowlist；不把任意长时或任意 dt 放开。原压力、Rgamma、history、M0 policy、loadclock helper、CU/cuh/公共类头逐字节保留。 |
| 私有构建 | 现 B10us 程序和原完整 111 对象链已存在。 | 若唯一源差为 `JSphGpuSingle.cpp` 的 Init 窗口 guard，最小是新编这一个 host TU、保留另外 110 个真实对象并按原顺序链接；新 PDB/ILK/out/stat 收据独立。无新 CUDA/ABI 改动就不重新做四套完整构建或 GPU 内存检查链。真实闭包由根审阅后决定，不能只改程序标签。 |
| 新程序短实施回归 | 当前 CPU B200/GPU Debug B2/default A320 已有本轮资格；不是细步物理 reference。 | 只窗口 guard 改动时，可在新程序补一次 Release default-A320/18，沿现有 profile 对当前 A18 全五导出/actual clock/signed 逐记录比较，作为重新链接后的默认行为资格；不重做所有旧组件、CPU控制、half 或物理 reference。若根凭已审单一 guard 差异和完整对象证明采用更小的静态路径，必须明确记录判断，不能声称新程序已实际跑过短回归。 |
| 完整 clock/输入/owner | 当前 immutable seed 的 TimeMax=2；当前 runner 只支持四个 bounded profiles。 | 独立完整 runner/新 seed XML 与 full plan：保持原 BI4/NBI4、材料/几何/边界/k/HG/SPR/AV/damping；只改总时长及相应 nsteps 上限。由 scalar `+=dt` 与原 JDsOutputTime 运算次序产生新完整 plan，先审核再启动。不得复用旧 6.25us 的 1682 行/11661219 步作为新真值。 |
| 一次完成机制 | 已验证 direct-owner 的真实 Win32/Popen 身份/出口与单次同线程 queue。 | 新独立 owner/admission，封存 run/status 后至多一次 45s queue；不重启旧 owner、不重新布防、不做连接测试，不自动 reader/下一 solver。 |
| 全周期 native profile | 现已编 M0 reader 只准入 CPU200/GPU2/A320/B2s 四个 profile。 | 新窄完整 profile/独立 reader 构建和 Python wrapper，完整新 frames/updates/end/event 计数；保持原 Load/Initial/Read 的 22 数组、1040 IDs、ledger、FS、几何、有限性、signed 等全部谓词。不能把完整数据叫作 `window2s`，也不能伪造原 completion。 |
| 全周期 native/review | 当前 B2s 的数值函数与 44 列 loadclock reviewer 已通过短资格。 | 参数化到真实完整 profile，逐帧全部 28 列压力侧车、M0 signed interval、44 列 loadclock 和原 HG summary；先查 existing/active reader，再独立一次读取。复用已有算术/FTZ/PTX，不重新扫旧对象或 BI4 SHA。 |
| 科学交付 | 已有完整 A 和旧 u-pw 的保留产品；当前新 science 只做 2s 两个 targets。 | 新完整科学薄适配，对正确模型参照、全指定 Tv、晚期压力地板/衰减、所有100层/实际材料顶底沉降和模态绘图，输出匹配 PNG/CSV。保留原 A 100Pa 超限及旧 u-pw Vel0 的上下文限制。根实际查看后再作验收判断。 |

这不是自动追加短窗链。必要的新增 physical job 最多是一条根另行准入的 fresh B10us 完整周期；C full、CPU full、half、20us 探索、重算 A/u-pw 均非该清单的默认内容。新短回归如需执行只是新程序资格，不能用于替代完整精度或制造新物理 reference。

## 时步、Rgamma、loadclock 与 HG 不能混为一项

现 M0 `EQ40_RH1` 的必要界仍是三阶段逐次记录的 `min(force_CFL, current-J skeleton-wave+AV_CFL, true-Kw hydraulic_reference*R_h)`，R_h=1；物理 Kw、AV、压力率源及材料方程没有设为零。原含 Kw 的耦合波速界仅作明确标注的旧方法诊断，不再与当前骨架波速界混用。动态 J/n/rho 与 k 的实际状态仍要检查；本 case 常 k 不代表力学/孔隙率尺度不演化。

这些是必要界，不是完整 M0 耦合谱稳定证明；不能从 paper 的 R=17/35 或 2s 安全推断任意长程/任意 dt 稳定。完整运行仍保留固定 dt 超界拒绝、原 natural/pore 限制、finite/ledger/排水门，不通过自动抬界、静默 clipping 或失败后调 dt 重启补齐。

Rgamma 中的真实速度散度、二阶压力/Taylor 项、rho_l 的加速度散度均保留；邻压外推与一次 leading-LP 修正仍是当前 Symplectic P1 变体，并非宣称复现原文 LF 或全局隐式。此次 loadclock 只将三次真实 force 的外载求值改为 tn/tn+dt/2/tn+dt，global TimeStep/Nstep、Dirichlet source clock、唯一机械/J 更新及完整压力 history 不改。其长期精度必须由完整结果检验。

每次更新有三次 force/rate 评估，但第三次 HG 是只读加力，原 HG 的真实计数仍为 forcecalls=2N、ratecalls=2N、predictorupdates=N、correctorupdates=N、ratecalculations=N+1、cache=N-1；不能误要求 HG=3N。M0 三阶段 counts 与 loadclock 三 force/六 site counts 各为 N。HG 独立 stiffness/spin/finite 门保持；`HG_limit_reference_available=false` 的 DBL_MAX 不是实测 HG 允许时步。

TPI core7k*N/HG snapshot2k*N 会超过 uint32；当前 helper 的 commits/coreChecks/hgChecks、M0 phase、loadclock force/site counters 已是 `unsigned long long`。完整 wrapper/JSON/CSV 预期也须用整数/64位，不能在 Python/PowerShell/reader 适配时截成32位。Nstep 本身仍在原32位能力内，但实际 nsteps 必须按新完整计划确定。

## 完整周期输出与真实 prefix 的兼容策略

优先保留当前实际 seed 的五段 schedule：0 起 2^-13s、.009765625 起 2^-19s、.01025390625 起 2^-13s、.0250244140625 起 2^-9s、2.0000457763671875 起 .18218571428571428s。早期保留事件和模式诊断密度，后段间隔对应 M0 legacy ΔTv=.005；TimeOut 目标和实际保存时刻均记录，不把间隔用作求解 dt。

终点须明确采用原授权 M0 legacy Tv=2：名义物理时间 `tD+2/Cv=72.88428571428571s`；具体 runtime TimeMax 和 nsteps cap 由新 scalar plan 的首个跨越及根批准的终态策略决定。可以保持旧 runtime cap 的物理含义，但不能直接抄旧 6.25us 的 actual end 72.88428689946836s。未生成新 plan 前不预填完整 frames/actual end，且不通过 `N*dt` 代替实际时钟。

当前 2s plan 最后三行中，part1261 为 completed199959/1.999635766987311s；part1262 是 forced-final completed199996/2.00000577545594s。完整计划继续运行时，后者不是普通输出目标，不能当共有状态；完整计划应按原 output-target 继续。最初真实共有记录可在未来 full plan 中按 actual time bits + saved Step 验证，预期只有前1262条普通记录。完整原生读取后比较五导出实际记录/clock/signed，分别保留1263/full headers；不篡改 count、不插值、不重跑2s来造前缀。若改变早期 cadence，必须提前披露共有记录减少，不能再称完整前缀。

28 列压力侧车按 1000 soil ×真实保存帧写出，不是每次 update 输出；M0 interval 和 44 列 loadclock 各每保存帧一行。无需全帧 VTK 来通过此 benchmark；先保 BI4/NBI4、原 typed exports、ledger、图/CSV 和可复现入口，再按需要导出 VTK。长程准入前根应检查实际磁盘余量，不能为了空间清理活动依赖或必要原生证据。

## 最终精度规则与发行边界

完整 targets 沿已审方案为 legacy Tv=.005/.05/.1/.25/.4/.5/.7/1/1.5/2，均在各自实际保存时刻使用正确参考。主压力误差预算为 B<=可比 A +10Pa；Tv>=1 另外要求 <=A+5Pa。顶部绝对沉降误差/S∞ 不恶化超过 .1 个百分点；底部 <=.005mm 且 <=A+.002mm。全部 post-.1s 的100Pa层应力/top-gap 原门保持；Q/交替列和晚期压力地板完整报告，不事后加宽或隐藏失败。

A 的有限 Kw 适用 Tv 与 legacy Tv 不相同，旧 A 终点只覆盖约1.99196的有限 Kw Tv；不能称其已有有限 Kw Tv=2 或为此自动新开 A。误差用各自正确参考在各自真实时刻求取，跨模型/跨 dt 比较不套 half 5Pa。旧 u-pw GPU/Vel0 只能作限定上下文，不能当严格同边界算法真值或隔离速度基准。

即使本 C02 完整通过，也只是本私有 B 分支的一维 benchmark 证据；P5 公共源码/XML 和正式发行仍须原计划对应的 Cryer 等资格、兼容范围、重启限制与性能说明。这里不自动发包、不接 beta 负压正则化、不恢复 C08。若完整运行或分析失败，保留实际首因/partial，完成 solver 后只修离线派生，不能重跑已完成求解。
