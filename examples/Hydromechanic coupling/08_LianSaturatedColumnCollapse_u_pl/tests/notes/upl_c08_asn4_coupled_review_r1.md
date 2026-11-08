# 新CPU coupled短窗的终态离线审查（作者稿，未执行）

只新增同名Python和本note，不改活动/已冻结owner、CPP、程序、输入或输出。脚本仅消费 `logs/upl_c08_asn4_coupled_cpu_r1.check.json` 已封存的终态和匹配actual_call；目标真实Popen/Win32退出必须一致、ownership无错误。正常4000步成功或非零退出的真实failure.json完成态前缀分别验证，保留source passed/失败phase/原异常/最后原CSV行；review passed只表示派生完成，不把求解失败改成成功。

按冻结CPP核实：states **62列=10头字段+13字段各min/ID/max/ID**，focus **23列**，四原材料ID7013/7015/6963/7014，每个completed step四行。初态是n4 part64/completed4260000的已保存完整态，输出从其后第1个真实完整步开始，不伪造t0。使用已封口native clocks的真实part64时间与PRE实际时间，每行scalar+=2.5us核time/globalstep/tau；signed dterror按原signed≤1e−14和非空门，不取绝对值。

只接受完整、带终止换行、states/focus计数一致的flush行，不丢掉坏尾行伪装partial。失败只读取Failure缓存声明的最后成功flush行；不访问/推断失败substage的主场、时间或Ace/Rσ。若没有任何完成行则拒绝科学图表，不伪造空结果。normal端4000/16000行、partial真实N/4N行分别核终态缓存。所有min/max ID须是2060..7059土ID；focus P0 floatbits不变与κ非回退保留。

输出3CSV：`_history.csv`保留全部62列并加actual elapsed ms；`_focus.csv`保留全部23列并加从存储速度求speed及trace恒等式roundoff；`_events_extrema.csv`包含全部13字段global sampled min/max及对应ID/time/step，以及首次**采到**pmin<−100/−300kPa和speedmax>2/10m/s。四个数字仅描述事件，不是新安全/物理验收门，也不等于已证明真正起始时刻。

两PNG显示全completed范围：`_global.png`含p极值/RMS、speed、J、κ、effective/total trace和存留Cor rate/θ；`_focus.png`含四ID的p/J/speed/κ/FS/存留Corθ。横轴为真实time−part64时间的ms，明确offset、不重时移；原负压/尖峰保留、不平滑拟合或裁切。**last_cor_rate/last_cor_theta是上一Cor RHS存留观察，不是完成态即时RHS**；不从它们精确倒推材料return/contact投影先后或净反力。

只有源正常完成4000步、completed4264000且actualclock逐bit等于原GPU part65时，才只读原封口typed22的**一条part65记录**和固定四ID，不新native/BI4解码、不扫66帧。比较p/J/κ/三速度/speed和effective/total stress **trace**；CPU focus没有六分量σ，不能伪造完整张量比较。记录在review JSON，纯描述，不设5Pa/.005mm或0ULP物理门。partial未到此时刻则不读该raw端点、不插值、不伪造终点。

这是从保存场重新起算的新CPU短轨迹，与原GPU的中间缓存/排序/FP历史不同；即使端点可比也不是精确GPU重启/重演。原n4失败仍在，其他ψ不自动准入。本脚本不启动solver/reader/VTK/build/后续任务或hash扫描；2图需根执行后亲看，作者不宣称QA完成。

新前缀 `tests/figures/upl_c08_asn4_coupled_review_r1_*`，独立check `tests/logs/upl_c08_asn4_coupled_review_r1.check.json`，拒已有/部分派生输出。根全文读后唯一离线调用；当前仅作者和AST静态核查，未import/执行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_asn4_coupled_review_r1.py --execution-authorized
```
