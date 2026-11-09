# 首近对的完整邻域零步力观察（作者稿）

本说明生成时只完成作者准备，尚未构建或运行。新同stem CPP/build/run与本说明，未改生产源码、旧物理程序、任何输入、PRE或结果。根全文审后再分别决定一次build/run；无通知器或自动后续。

固定输入为已通过的 true total-AS ε=.2/n3、Shepard/damping OFF、CompletedOnly、keep5/fixed-plane causal90 native 的 part13/14（实际τ≈.14/.15），只 seek这两条原90头的22数组记录，不读BI4或改header。run/native及原causal90对r6全22/实际clock/signed前缀证明绑定；同一个冻结bedkeep DebugCPU86个non-main物理对象加本helper，87链接，原归档头/MSVC14.36 flags/runtime不变。实际认证原r2GPU PRE导入与唯一keep5释放后，逐ID恢复两保存态、真实cell排序/再恢复；墙normal/NoSlip与ID角色沿原static guards，不把FSNormal当墙法向，也不宣称GPU bit replay或正式重启。

每态三次独立完整 `Interaction_Forces(INTERSTEP_SymCorrector)`：baseline AS=.2/n3、AV=.1；仅 `ArtificialStress=false`；仅 `Visco=0`（仍为原Artificial AV模式）。原无ViscoTime。每次先独立Restore，包含真实动态墙状态/C/Ace重建与Darcy，原primary/ledger/P0/J/κ/固定角色守卫保留。关闭AS时其scratch必须为空，AVoff实际传给fluid/fluid与fluid/wall原Visco系数均0。开关由局部RAII恢复，force后原Pos释放scratch，再还原输入primary与首次baseline实际5000Rate bits。共6 force/6 Darcy、0时间推进/材料返回/滤波/PRE求解；原engine源数组/元数据不修改。

对7011/7012采用 `n=(xi−xj)/r`、`dv=vi−vj`、`dv_t=dv−dot(dv,n)*n`，导出完整邻域实际 `a=Ace+实际Gravity`，

`r''=dot(n,ai−aj)+|dv_t|²/r`。

直接算切向向量范数，不用两个接近平方相减或额外clamp。两点相同重力在相对投影中抵消，但CSV仍明确实际加重力的量。它是当前冻结状态的瞬时间距曲率，包含全部邻居/墙/原AV/AS等assembled force；不是单pair tensor proxy。积分后的独立plane投影不在此force中，ReactionClosed仍false。ASoff/AVoff同时可经finishedAce改变Darcy与壁重建，这些差是算子开关反事实，不是严格逐邻/可加力分解。

`soil_force.csv` 6×5000行：actual Ace/总a、off−baseline的Ace与Rate、实际θ、saved/actual/baseline FS；`focus.csv` 12行：两个ID的p/P0、double有效σ6、κ/J/n/V/rho/k、actual C9/θ/σrate6/Ace及FS等；`pairs.csv` 6行；`calls.csv` 6行，含原实际 `DtVariable(false)` 返回、原force/wave-visc/pore/k-gradient必要尺度及FS变化。原DtVariable正常守卫照常，false不记录输出区间/推进时间；不存在的持久完整∇v不伪造，不复制新的梯度或五项shadow算法。只记录FS变化，不固定或抹掉分类。

目标 `tests/outputs/upl_c08_pair_force_cpu_r1`，check `tests/logs/upl_c08_pair_force_cpu_r1.check.json`。wrapper核实际Popen/Win32出口、全部输入stat、6call/30000soil/12focus/6pair覆盖及真实clock；仅核少量CSV差值/r''读回代数，不加物理验收阈值。失败保留首因与最后完成call及partial，不解读未完成半步指针。无需任何新Jacobian、多幅扰动、half、长窗、AS参数或public XML选项。

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_pair_force_cpu_r1_build.py --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_pair_force_cpu_r1_run.py --execution-authorized
```

两入口独立拒绝既有或活动同helper，不运行GenCase/native/VTK/solver或下一任务；`physical_acceptance=false`。
