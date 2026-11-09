# 真实 n3 保存态的条件压力 Jacobian（作者稿）

本说明生成时尚未构建或执行。只新增同 stem 的 CPP、`_build.py`、`_run.py` 与本说明，不改物理源码、旧程序、输入或输出。由根全文审阅后分别决定一次 build/run；无自动后续。

源只允许已封口的 `upl_c08_causal_window_GPU_r1/native` 原90帧中的 part71，actual time≈10.72s、completed=4288000，total-AS ε=.2/n3、Shepard/damping OFF、CompletedOnly、keep5/fixed-plane。run/native 与既有 causal90 对 r6 原300头前90记录全部22字段/actual clock/signed clock 的 byte-prefix 证明分开绑定；CPU 使用冻结 bedkeep DebugCPU86个 non-main 物理对象加新 helper（87链接），同归档头与原 flags/runtime。不把 observer GPU 程序与 CPU 程序宣称同 binary，也不把原 n4 态的 AS3 反事实正模态转称此真实 n3 态结果。

CPP 从已通过 `upl_c08_asn4_pressure_cpu_r1.cpp` 机械派生，初始化→真实认证 PRE→唯一 keep5 释放→逐 native ID Restore/cell sort→真实 `Interaction_Forces(INTERSTEP_SymCorrector)`→原 Pos cleanup 生命周期和五项 `Sum` 原式/预算保留。仅更换原生90/part71绑定、AS3单值/16Pa单幅度、固定41行列与调用计数，并增加恢复/输出观测。41 ID及顺序取自原 passed330 completion，原样写入新 CPP；不在新几何重新挑选或截邻域。已在作者准备中小 seek 保留 typed22 的这41点 p/FS：全部压力负且 ±16Pa 不接近零，两个 savedFS2 点仍保负压。实际 force 重新分类结果由 baseline 定义，变体全5000 FSType、全部1805 fixed wall activity mask 必须与实际 baseline 一致；保存态 FS 的变化另保留原列，不改 mask 或 clamp 初态。

仅 baseline 1次，加41列各 ±16Pa 共82次，合计83 force+83 Darcy、0积分/材料返回/Shepard，不做AS4/第二幅度/半步/长轨迹。每列只改选定 float p，实际 double(float changed)−double(float original) 及原/新 float bits输出；P0、σ、J、κ、位置/速度及区外压力固定，excess只是 p−P0派生缓存。墙的实际 p/σ/J/C/Ace 每次按原 operator 重新响应，不是冻结错误墙。全5000 soil 主字段对明确 incoming state 位校验；force结束后 `CopySaved(base)` 恢复原输入主场，再逐ID恢复首次实际 baseline 的5000 Rate bits，83×5000=415000次，并保留 ledger/墙 Code/normal/NoSlip。native本身不导出Rate，因此这指本组件 baseline actual Rate，不冒称GPU保存态Rate；下一次 force 仍全量重算。

新输出 `tests/outputs/upl_c08_pressure_jacobian_n3_r1`，新 check 为 `tests/logs/upl_c08_pressure_jacobian_n3_r1.check.json`。`calls.csv` 沿原22列，83行；`rates.csv` 83×41=3403行，沿原25列只在 `n` 后增加 `volume_m3`（26列）。后者使用已有 `GetPorosityFeedbackStateCpu` 的实际 n/V；每次 Ledger 已核与保存态位同。completion 输出实际 `pore_water_bulk_modulus_Pa`，因此后续 `W=n_saved V_saved/Kw` 不需猜 dp² 或再读原生字段。FS baseline比对410000次、wall mode比对148010次；全部原 shadow预算/finite/ID/clock/P0/J/cache/角色门保留，无谱正性门。

各行含 actual float rate，另保留 compression/LP/defect/divAce/chain 的 test-side shadow及原预算，不能把 shadow当原GPU率或未保存阶段重放。后续41×41 central matrix按每列 `rate_plus−rate_minus` 除以该列实际 float pressure span；单16Pa只是一条有限精度/有限幅度斜率，不能证明收敛或跨AS谱 kink 的经典导数。区外 soil 扰动为0、墙正常响应，是此保存态条件压力块，不是实际Pre/Cor全状态谱、能量定理、接触反力闭合或物理验收。source的真实scalar clock一直保留，没有 synthetic t0。

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_pressure_jacobian_n3_r1_build.py --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_pressure_jacobian_n3_r1_run.py --execution-authorized
```

两个入口均保护既有完整/失败产物；真实 Popen/Win32 出口在后检查前封口，异常只保留首因与 partial，不重试、不调用新 solver/GenCase/native/VTK/queue，`physical_acceptance=false`。
