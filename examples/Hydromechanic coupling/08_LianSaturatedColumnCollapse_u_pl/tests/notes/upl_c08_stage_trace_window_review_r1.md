# C08 .66 s真实stage CSV窗口检查器（author-only）

新增 `tests/support/upl_c08_stage_trace_window_review_r1.py`。两个新名事前Test-Path为false，精确git ls-files为空。未执行/import/AST检查或启动solver/reader/build；旧 `upl_c08_stage_trace_review_r1.py` 和已通过短窗证据不改。

从已通过的旧checker机械复制，仅5处替换：docstring、TAG/窗口常量、expected_steps、采样step资格、CLI profile。其余57列、float32 bits、binary64分项闭合预算、stage关联、clock与首因封存代码原样保留；不新增物理阈值。

采样资格与当前 `JSphGpu.cpp::C08TraceBegin` 一致：4000000<=Nstep<4240000每40步；4240000<=Nstep<4264000逐步。expected为6000个coarse+24000个dense，共30000个真实step_start；step资格用O(1)条件判断，最终仍严格比对完整顺序，避免30k列表逐次搜索。它不是264000更新都被记录。边界4264000排除；最后一更新的完成几何ponding仍属于step_start4263999。

每个采样step保留RHS2→UPDATE2→RHS3→UPDATE3，之后至少一个完成几何ponding；真实leading/repeated trailing ponding均保留，不将原CSV改写或硬裁成450000行。正常5events×3IDs为450000行，release等extra事件由实际记录决定。每event必须顺序含5809/4956/4959三行、hits1和同一context，完整header/writer57列；事件无RHS字段必须为空。

clock以真实step_start记录为起点，跨coarse gap逐次`+=.0000025`，dense gap亦同；不使用Nstep*dt构造时间。检查器不自行证明首clock等于PRE、程序真实退出或源/输入绑定；这些仍由实际owned run/native收据与root审阅负责，JSON保留`runtime_binding_proven_by_this_check=false`和`owner_review_required=true`。

按原checker核：half/full operator_dt；UPDATE的float32实际表达式与原p_n基态；RHS→UPDATE压力/rate关联；positive-only ponding与不变rate；RHS float(value_double)；n(J)、lap、variable-k chain和完整Kw/n RHS。binary64分项仍用原128eps×实际绝对操作数尺度，未据结果修改；更新bits若受FMA等影响会诚实封存首因，不重跑solver或放宽预算。C条件数只报告，不新增门。

与HG owner对齐：run tag `upl_c08_stage_trace_window_GPU_r1`，264000次新更新/global end4264000/预期66个保存PART，owner只run不自动native或review。本checker只消费已封口CSV；不读取BI4/typed22，也不自动触发后续工作。

根全文审阅、确认唯一run实际封口后，可显式调用一次：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_stage_trace_window_review_r1.py --profile window --csv tests/outputs/upl_c08_stage_trace_window_GPU_r1/C08StageTrace.csv --check tests/logs/upl_c08_stage_trace_window_GPU_r1.trace.check.json --execution-authorized
```

只写该全新check，拒已有目标，不覆盖CSV，失败保留首因。后续科学分析可直接从同一已封口CSV分三ID/真实predictor-corrector阶段比较compression、LP/defect、divAce、FS-Ace-lx与chain，再关联实际p更新和ponding；另产图/CSV应独立标记为派生，不把观察器当完整AS/AV/应力分解或物理验收。本次未作者这些分析或图。
