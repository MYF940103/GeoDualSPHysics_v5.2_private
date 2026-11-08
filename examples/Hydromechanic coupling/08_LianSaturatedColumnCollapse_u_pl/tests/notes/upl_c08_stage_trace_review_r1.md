# C08真实stage CSV的离线小检查器（作者稿）

仅standard-library csv/math/struct，无NumPy/BLAS初始化；未执行。`--profile smoke`核40更新1帧的采样起点，`short`核12000更新3帧的300个40-step采样起点；它不读native或证明程序退出/后端/物理验收，这些仍由root owner/native收据负责。CSV及check均不得覆盖。

严格57列、每event三连续原ID5809/4956/4959/hits1、实际context一致；核RHS2→UPDATE2→RHS3→UPDATE3顺序。每step可保留initial release的leading ponding及save等额外trailing ponding，不将总行数硬写成samples×15，不删除额外原行。实际clock从每event记录取；不同stage同step应同clock，跨采样gap只从前一真实clock逐次+=dt核，不将n×dt当事实。

UPDATE按原表达式float(double(p_before)+operator_dt*rate_before)核p_after float32 bits，RHS->UPDATE的rate及source-p亦逐bit检查；corrector p_before必须是原full-step old p，不是predicted half当前p。PONDING仅FS2/3且正p归0，其余压力bits保持，rate不变。RHS rate_after必须float(value_double) bits；C的2D y块为0，矩阵有限，XZ条件数仅报告不加物理门。

按原free-seepage/interior分支从记录LP/Lx/GpCorr/Ace/divAce核lap，按GJ/ki/solid0/Ck核chain，再核Kw/n(-theta+ki/gamma*lap+chain/gamma)。Kw1e9、solid0=1−float(.35)、gamma1000×9.80665、Ck2。binary64分项闭合使用128eps×操作数绝对尺度的明确舍入预算；关联重排不能承诺逐bit，不能以此改原物理门。若pressure-update bits因FMA等有差异，现稿会诚实失败交root审查，不重跑solver或自动放宽。

根全文审后显式调用示例：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_stage_trace_review_r1.py --profile smoke --csv tests/outputs/ACTUAL_JOB/C08StageTrace.csv --check tests/logs/upl_c08_stage_trace_smoke_review_r1.check.json --execution-authorized
```

只写一份小check JSON，保留实际额外events计数、残差及首因；无solver/build/reader/queue/图，passed只表示CSV内观测一致性。
