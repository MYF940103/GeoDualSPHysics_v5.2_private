# ReleasedSubstages 的真实 half 投影检查器

仅新增同名 `tests/support/upl_c08_stage_ponding_review_r1.py` 和本说明；事前两个目标不存在且未受 Git 跟踪。旧 window checker、输入、程序、CSV 和收据不修改。作者仅做 AST / 机械差异检查，不执行或 import 检查器，不启动 solver / reader / build / queue。

原 `row_checks` 位于旧 `review` 闭包，故采用机械派生，保留原 parse、57 列 / 三 ID / hits、有限值 / float32 bits、正压投影与不变 rate、RHS 分项、128eps 实际操作数量级预算、C 的二维布局及描述性条件数、标量 `+=dt` 时钟和原始 p_n 基值检查。负孔压保持原位；原 NaN / Inf 拒绝规则不变，不用新阈值容纳非有限状态。

唯一事件状态机变化：每个被采样 step 必须为 `RHS2 → UPDATE2 → PONDING2 → RHS3 → UPDATE3 → 完成 ponding`；其中 mandatory half PONDING 恰好一次，位于两组原 RHS/update 之间且 interstep=2。未知插入位置、重复 half 或缺 half 一律拒绝。真实 leading 及 repeated trailing ponding 仍逐条读取、关联和计数，不删行或硬写总行数。正常每 step 6 events × 3 IDs；额外真实事件以原 CSV 为准。

half 的输入压力 / rate 必须逐 float 位接续 predictor UPDATE；half 本身只将 FS2/3 的有限正 p 归零，rate 不变。corrector RHS 必须读取该投影后的 half p，且其 FSType 与 half 相同；corrector overwrite 前的旧 rate 也须连续。原 `UPDATE2.p_before == UPDATE3.p_before` 位检查继续独立保留，确保 full update 仍以保存的 p_n 为基值，不能误用投影后的 half p。四个 core RHS/update 的顺序、operator_dt 和实际更新表达式均不变。

`window` 保留 4000000..4239999 每 40 步、4240000..4263999 每步，30000 个真实采样 step / 66 个原生保存帧的 trace 范围。root 现已明确新增固定 `smoke2ms`：源 4000000 步、dt=2.5µs、结束 4000800 步，实际 trace 预期 `range(4000000,4000800,40)` 共 20 个采样 step；计划输出 .001s、两帧 completed=4000400/4000800。只是局部 profile end，window 原全局常数、完整列表及预算不变。两种 profile 的检查器均不读取 PART 或证明帧数；本计划尚未实际求解。正常结束不自动准入下一阶段，native 与 trace 必须独立审阅。新增 half 计数只描述真实记录，不是新物理门。

root 全文审阅并确认真实 run 封口后，可一次显式执行（路径由实际新 owner 决定）：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_stage_ponding_review_r1.py --profile window --csv tests/outputs/ACTUAL_NEW_RUN/C08StageTrace.csv --check tests/logs/upl_c08_stage_trace_ponding_window_r1.check.json --execution-authorized
```

只写全新 check，保留首因，不改 CSV；程序 / 输入 / PRE / 退出与所有权仍由实际 owner 收据及 root 负责。`runtime_binding_proven_by_this_check=false`、`physical_acceptance=false` 保留。无 SHA、额外 half-step 求解链或自动后续工作。
