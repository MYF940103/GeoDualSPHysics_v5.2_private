# effective-AS 单定义干预的终态离线对照（作者稿，未执行）

只新增同名support Python与本UTF-8说明。新CPU4000步依赖、原total-AS结果、生产源码/输入/runtime/PRE一律不改；不读取活动CSV。执行必须等新 `upl_c08_as_effective_cpu_r1.check.json` 实际passed、4000步/16000 focus完整、target真实退出0且AS_definition_probe_passed后。直接消费原AS_probe.json中有效应力匹配和至少1点区别total的通过结果，不重算eigh或重复物理试验。

原CPU total与新CPU effective保留相同n4 part64起点、2.5us/4000updates及相同基底源码，仅私有AS定义不同。核两端原62/23列、全部真实completed step/time/tau和scalar+=dt；signed dterror仍按原signed≤1e−14与非空门，不取绝对值。无重采样/插值/时移/半步链。未正常到4000或probe未通过时脚本拒绝，不自动追加任何求解。

三份配套CSV：matched_history含4000对实际clocks、图中各全局指标及其argmin/argmax native IDs；matched_focus含4固定ID每步两定义的p/J/速度/κ/应力迹/FS和存留Cor量；endpoint_pairs含5000原材料ID的初始/两端点原字段、非self NN及CPUeffective−GPUtotal端点位置差。原完整62/23列源文件仍保留，派生CSV不重写它们。

四PNG：

- global：全部5000的p极值/RMS、speed、J、κ、effective/total stress trace，并专列全局pmin/speedmax **ID迁移**。JSON另记13字段全部采样全局极值ID/时刻、极值占用ID与切换次数，不只看4focus。
- focus：固定7013/7015/6963/7014的完整4000点p/J/speed/κ/total trace/FS；颜色按ID、线型按定义。Cor rate/θ在CSV明确是存留的上一Cor观察，不当完成态即时RHS，也不精确倒因果到材料/接触步骤。
- endpoint_spacing：两端点所有5000点NN/dp空间图、包括继承初态的经验CDF及近对小表。
- endpoint_fields：原GPU_total part65与新CPU_effective endpoint的全部原p/κ/J，逐字段共享完整raw范围，无平滑/拟合/裁切。signed symlog只用于时间曲线显示，阈值1kPa不是物理门。

为了不把继承的团聚算作新AS产生，只从**同一已封口原typed22** seek part64和65两个record：initial_n4 .65、GPU_total .66。新endpoint_soil.csv来自本次真实CPU4000步末只读导出。NN在全部5000土坐标上求非self最近点；FS0/FS2/3仅分接收点统计，邻点仍全土。严格<.5dp/.7dp点数/唯一近对数只是几何描述，非合格阈值、非mDBC/SPH力邻域或张拉因果证明。KDTree避免N×N矩阵。

5000端点点值比较是**跨后端且定义/轨迹不同**的CPUeffective与原GPUtotal描述；旧CPUtotal只有global和4focus，没有全5000端点，不能补造或声称same-CPU全场等价。原GPU n4稍后失败身份保留；已保存part65仅作该实际时刻参考。两原生record与CPU端点必须step/time匹配，不插值、不新BI4解码/reader/VTK。

当前干预只在继承的n4 .65状态切换AS输入，绝非从撤墙起的新鲜同算子算例。峰值缩小或4focus脉冲消失不证明精度；要一起看全局ID迁移、应力/J/κ、近对/间隙和初态遗留影响。无论文唯一正确、完整耦合根因、物理验收或其他ψ准入结论。

新前缀 `tests/figures/upl_c08_as_effective_review_r1_*`，独立check `tests/logs/upl_c08_as_effective_review_r1.check.json`。拒覆盖/重试，无旧数据/对象/源码递归hash。旧 `coupled_decision_r1.md` 编码损坏记录不修写；本note作者阶段用UTF-8静态读回核对。根全文审后才唯一离线执行；当前未import或运行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_as_effective_review_r1.py --execution-authorized
```

四图执行后由根视觉QA，作者不伪称已看新结果。
