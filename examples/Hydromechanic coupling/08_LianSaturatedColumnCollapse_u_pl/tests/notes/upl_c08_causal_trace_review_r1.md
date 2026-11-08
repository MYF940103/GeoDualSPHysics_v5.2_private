# C08 causal CSV 独立检查器（作者稿，未执行）

只新增 `tests/support/upl_c08_causal_trace_review_r1.py` 与本说明。既有源码、构建、输入、PRE、reader 和结果均不修改；本脚本不运行求解器、reader、VTK、构建、队列或 SHA。它消费同一 job 已通过的真实 run/native 收据及程序/双宏源码捕获绑定，逐份 CSV 只顺序读取一次，不再读 BI4/typed22。

根线程完整审阅后才可分别执行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_causal_trace_review_r1.py smoke --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_causal_trace_review_r1.py window --execution-authorized
```

固定 job 为 `upl_c08_causal_smoke_GPU_r1`、`upl_c08_causal_window_GPU_r1`。输出各自 `tests/logs/<job>.trace_review_r1.json`；已存在成功或失败检查均拒绝覆盖，不自动重试或启动后续计算。成功收据提供 `passed`、`trace`、`totals`、`source_run`、`native_receipt`、`consumed`，其中路径对象均为实际 stat Entry。异常保留 `first_failure`，不删除原始 CSV。

## 实际范围及检查

严格要求主表97列、累计表56列及三 ID 固定顺序 **7017,5944,6814**；不适用字段必须为空。主表按真实 global step `[4000000,4360000)` 每40步采样，并在 `[4316000,4324000)`、`[4332000,4340000)` 每步采样。smoke 只覆盖10次更新中的真实首采样 step4000000，累计表末四种 count 各为10；window 24600个采样 step，90个累计快照末 count 各360000。时钟从真实 PRE loader 时钟逐次 `+=dt` 核对，不能用 `n*dt` 当保存时钟。

正常核心顺序为 `RHS2 → UPDATE2 → MATERIAL2 → PLANE2 → RHS3 → MATERIAL3 → PLANE3 → UPDATE3 → completed PONDING`。保留实际额外 leading/trailing ponding，不硬写总行数，不允许把半步投影混入 CompletedOnly。原57列 RHS 的128eps二进制64运算量级预算、孔压 float32 更新逐位检查、正压 FS2/3 才归零且 rate 不变的规则机械保留。负孔压不截断。Cor UPDATE 基值继续逐位等于原 `p_n`；Cor MATERIAL/PLANE 的当前孔压仍是 half，不能将它误当 Cor UPDATE 基值。

新材料检查包含真实允许 status1–4、Pre κ候选后恢复旧 κ、Cor 保存候选 κ、相同 RHS 的六分量应力率/K/θ、真实 Ibase/Itrial 恒等式及已声明的局部 gamma16 前向预算。实际 K 直接采用记录的 float（本例19607844Pa），不以理想 E/ν 值替代。J 使用真实 `Jn/Jhalf/Jnew` 链与原显式更新式检查，不能拿指数积分替换。plane 只独立核已记录的命中/负速度清零逻辑、未命中位移不变及切向不变；实际 plane/base 坐标未导出，不能从 CSV 独立重建几何命中，也不声称反力/J/Darcy闭合。

累计表要求每快照三 ID、四种 Pre/Cor/Plane count、status 总数、errors0 与投影计数真实完整；所有 Cor 累计有限，actual dt 仅按 Cor 累加，log(Jnew/Jbase) 不假定等于 dtθ。按原公式重算迹累计预算与端点恒等式；`base_trace_changes=0` 时检查已声明端点前向预算，非零时明确记录未观测 base 迹改变，不能将差值全部归于舍入。不把稀疏主表冒充全步累计。

## 证据边界

`pending_valid` **没有 CSV 列**。其为零只由实际绑定的正常程序 writer 在输出前的 host gate 证明；JSON明确标记不是独立 CSV 观测。局部预算中的完整对角运算数没有全部导出，检查器核记录的恒等式与声明预算，不能冒称独立重建所有 operand scale。gamma5 迹相减预算仅是相应加减运算预算，**不是完整 DP/root 返回误差界**，不据此强制所有 Smooth 返回严格保迹。

原 MaterialError 等检查先于 host TraceEnd；材料拒绝的失败子阶段可能没有落盘，因此不能宣称完整捕获失败过程。本检查仅认证三 ID 已写出的阶段/累计一致性，不代表全场因果、理论精度、半步收敛或物理验收。原生22数组及其安全门由独立 native 收据负责；这里不重做解码，也不新增物理阈值。
