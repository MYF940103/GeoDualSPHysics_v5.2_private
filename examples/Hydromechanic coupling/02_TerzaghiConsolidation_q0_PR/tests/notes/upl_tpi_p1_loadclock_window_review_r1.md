# P1 staged-load B10us 2s 离线科学审查 r1

作者稿，尚未执行。仅新增 `tests/support/upl_tpi_p1_loadclock_window_review_r1.py` 和本说明；不修改冻结的 runner/native/旧科学脚本，不构建、解码、启动或重跑任何 solver。

## 固定范围和真实来源

新唯一 tag：`upl_tpi_p1_loadclock_B10us_window2s_GPU_r1`。必须先真实完成 run、一次原生 read 和新 native review，且全部原 22 数组/1040 IDs/时钟/signed/ledger/排水/HG 与 44 列 loadclock 审查 passed，才可独立准入本脚本。

固定 199996 更新、1263 帧、dt=`tD/1000=1.0000228881835938e-5 s`、actual end=`2.00000577545594 s`；completed 1000 仍 pre-open，1159 个 post-open 帧。对照为已经解码的旧 `upl_tpi_m0_dt_B10us_window2s_GPU_r1`，复用其 native binary/ledger，不重新读 BI4，不启动新 reference。两个 B 的全部 1263 个 actual time/Step/dt 和所有材料 ID 必须精确相同；此处不需要 nearest、不插值，signed interval 仍各自独立守门，不要求数值相等。

旧有限 Kw A 仅消费已经通过的 causal 分析的轻量 history/profiles/targets/metrics/events。**不重新加载 A 的大 binary/ledger 或重算 A 大表**。原 A 的 100Pa 越界和原 B10 的沉降预算失败均保留，不因已有结果被叫作 baseline 而免检新 B。

## 数学与预算原样

直接复用 `upl_tpi_m0_dt_causal_r1.references/describe` 及纯 binary/stat/write 工具，不执行其 main。新/旧 B 都用原 512 模态、H=1m 的 M0 未拟合伴随参考；旧 A 保留其自身 actual time 的 finite-Kw 参考及实际采样。没有调整半径、荷载、时间原点或参考常数；这些静力伴随解不冒称有限 ramp、核带加载、惯性或 current-J 启动过程的精确解。

原预算保留：

1. 新 B 每一个 `t>=.1-1e-7 s` 保存态：100 层均值总竖向应力最大偏差和顶部两层 gap 各自不超过 100Pa。完整历史检查，不用 late-only 隐藏早期失败。
2. 本 2s 能覆盖的两个原 target `legacy Tv=.005/.05`：压力层均值剖面 RMS 不超过原 A 相应 actual-time 误差 +10Pa。
3. 顶部材料点绝对沉降误差不超过原 A + `.001*S_infinity`（原 .1 个百分点；不是拟合增量）。
4. 底部绝对误差不超过 .005mm，且不超过原 A +.002mm。

更晚完整周期 targets 不在本窗覆盖，不能称验收。新 B 与旧 B10 的差异是同 dt 的外载时层干预结果，不施加半步 5Pa 或 .005mm 等价门。没有新增宽松预算。

保存的六应力为有效应力；总应力始终 `saved_sigma - p*I`，剪应力不变。Q 是 100 层总 sigma_zz 均值的 98 个二阶差分 RMS，不是交替 X 模态。层中心梯形积分和 J-1 的贡献分解沿用旧说明，仅是小应变诊断，不是精确能量、质量或力闭合。

## 产品

新产品统一为 `tests/figures/upl_tpi_p1_loadclock_window_review_r1.*`，任何已有或 partial 产品均拒绝覆盖。

- `history.csv`：旧 A 1292 行背景、旧 B10 和新 B 各 1263 行，共 3818 行；所有实际时间、压力、固定原始顶部/底部 10 材料点沉降、有效/总应力、Q、J/n/rho、速度及交替 X 模态。
- `layers.csv`：新 B 每帧全部 100 个固定材料层，共 126300 行，附同钟旧 B10 的压力/沉降/J/n/rho/交替 Uz 和六总应力均值及差值。该大派生 CSV 本地保留，不必放 Git。
- `profiles.csv`：两个 target、A/旧 B10/新 B、每组 100 层，共 600 行。A 直接使用旧 lightweight profiles；B 采用各自真实当前材料状态和同钟 M0 参考。
- `targets.csv`：新 B 的两个原预算、旧 A 的原误差和旧 B10 的误差/失败状态，以及新减旧的误差增量。所有 actual times 和 target gap 明列。
- `differences.csv`：1263 对同钟逐材料压力 RMS/最大差、周期最小像 XYZ 位移最大差、顶底沉降、应力 Q、J/n/rho、交替模态和贡献分解差异。
- `events.csv`：A/旧 B10/新 B 的初始、pre-open、首次 post-open、近 .15、近 1.5 及最后态，共 18 行；原 A/旧 B10 事件直接复用已保存轻量数据。
- `loadclock.csv`：1263 行真实 44 列 saved loadclock，加原 P1 在同 source time 的预期 q、half/endpoint q 改变量。其 phase counters 和 double q/time 已由 native review 逐 bit 验证。
- `metrics.json`：原预算、完整 100Pa 失败清单、实际三力阶段与原 HG 计数、误差增量及边界。另报告各阶段 `sum(q_stage*dt)` 的标量诊断；这不是实际外力冲量、能量或流体质量，三个 force 求值也不是三次独立机械更新。
- 六张 PNG：history、startup、late、profiles、modes、differences。所有图有匹配 CSV；模式图两组共用 colorbar 范围，无平滑或裁剪。startup 显示未过滤 mean p/J、原 drainage 事件和真实 last phase q；late 限定真实 1.5–2s 保存态。

`logs/upl_tpi_p1_loadclock_window_review_r1.check.json` 的 `passed/analysis_complete` 表示分析完整。原预算结果另列 `planned_budgets_passed`、`all_original_target_budgets_passed`、`all_new_post01_100Pa_guards_passed`，不会把预算失败转换成物理成功。始终 `physical_acceptance=false`、`partial2s_only=true`、`source_full_completed=false`。

## 独立执行接口

`D:/anaconda3/python.exe -B tests/support/upl_tpi_p1_loadclock_window_review_r1.py --admission PATH --execution-authorized`。

admission stage=`upl_tpi_p1_loadclock_window_review_r1.admission`，`passed=true, offline_only=true`。inputs 是根按实际消费列出的去重 stat（path/bytes/mtime_ns）：新脚本/note、原 causal/纯数学及必要 reader wrapper 源稿、原 BASE_XML/计划说明；新 run/read/review、完成声明、columns/IDs/physical/n/clock/history/ledger、原 8 列 plan 和真实 loadclock CSV；旧 B10 现有 run/read/review/check/native 同类输入；旧 causal check/metrics 和 history/profiles/targets/events 四份轻量表。

实际数学前将 NumPy/BLAS 线程设为 1，保护并行开发和计算资源。该脚本不 import 后执行任何旧 main，不创建 A 大表，不调用 build/solver/native/VTK/queue/Git，不重复 hash 原 BI4/对象。完成后仍由根查看 PNG/CSV，再决定下一阶段。
