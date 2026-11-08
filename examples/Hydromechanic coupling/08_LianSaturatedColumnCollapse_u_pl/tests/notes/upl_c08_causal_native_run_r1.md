# causal observer 的两个独立 native 入口

仅新增同名 support Python / 本说明，事前不存在且未跟踪。作者不执行或import，不改变已构建reader、物理程序、原PRE、输入、source capture或旧结果，不调用solver / GenCase / VTK / queue。

入口 action 只能 smoke / window，均须由root先明确审阅对应真实run已经passed、实际工具/solver退出0、start/call/admission身份、程序/构建/source/PRE/执行XML/原计划和原PART绑定不变，且无活动或既有/部分native消费。输出分别 `tests/outputs/upl_c08_causal_smoke_GPU_r1/native` 或 `...window_GPU_r1/native`，只用已闭合工具一次 e.invoke：

```text
C08CausalNative_win64.exe --read psi0 GPU DATA PRE END SAMPLES 1 PLAN FRESHOUT
```

smoke为GPU Debug memcheck、10次更新、global4000010、一个真实末态PART0000/Step4000009；window为GPU Release、.90s、global4360000、90帧每4000步。实际scalar clock从认证PRE逐步继承；smoke末态不与根full .01s帧共时。全部22/6805/keep5/1805fixed/5000soil、P0/κ/J/ledger/FS/signed/plane预算沿原core，AS ReleaseOnly .2f/3f、CompletedOnly两新policy keys均ABSENT。CausalTrace/total CSV只stat绑定（如果owner记录），不扫描或用作原生guard替代。

root 全文审阅、对应任务真封口后只选一项（作者未执行）：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_causal_native_run_r1.py smoke --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_causal_native_run_r1.py window --execution-authorized
```

唯一收据为 `logs/upl_c08_causal_smoke_GPU_r1.native_r1.json` / `...window_GPU_r1.native_r1.json`，包含 source_run / actual_call / completion / metadata / outputs / consumed 等实际Entry与原native门结果。失败或部分解码保留，不重复调用、覆盖、重跑求解或自动进入后续。window与根r6前90帧的typed22/time/clock/signed精确前缀留独立后续审查，不能以5Pa跨模型门替代。无SHA、额外half链，physical_acceptance=false。
