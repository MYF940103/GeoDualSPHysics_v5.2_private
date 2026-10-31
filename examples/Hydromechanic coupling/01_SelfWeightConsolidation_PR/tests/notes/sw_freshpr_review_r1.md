# 自重固结FreshPR：全程与分析完成，保留精度局限后转Cryer

2026-11-01，按用户最新安排及`validation/poromech_next_r6/r7.json`执行。状态为 **completed_with_limitations**：完成计算、分析和绘图，记录剩余误差；进一步自重精度修复暂缓，下一项为Cryer。不是把尚未满足的物理门改写为通过。

## 完整计算与数据身份

- 根目录输出：`CaseSelfWeightConsolidation_Scenario2_FreshPR_out`，全新计算，无PART重启。
- GPU为RTX3050；dt=3×2^-23 s=0.35762786865234375 μs；20459420步，403帧，1040个原生ID（40边界、1000土粒子）。
- 实际末时刻7.316858768463135 s，对应有限Kw Tv=2.0000001673、legacy Tv=2.0080770918。不是把名义2Tv或旧帧号代入实际时钟。
- solver于2026-11-01 01:41:42（UTC+9）封存正常退出；后处理于01:45:58完成。计算循环89751.171875 s，约24小时55分51秒。当前无所属求解/后处理存活进程。
- mode3解析自重初态、重力开启、k=1e-3、dp=0.01、应力double/孔压与密度float、G1/SPR1/HGxi0.1、阻尼0.02、Shepard关闭；保留原float u-pw与receiver-C Darcy。

独立核查403×1040×38=15926560个原生数值，原有有限/弹性/无排除/p0逐位固定/float32 excess/真排水10ID/几何/自然与孔隙步长/计划时钟检查全部通过。4025条显式文件绑定按Windows路径去重为2298文件、996795687字节，大小和SHA全部一致，无缺失或冲突。覆盖已引用清单与依赖，不声称扫描整个仓库。

HG实际force/rate调用各40918840；预测/校正各20459420；rate计算20459421加缓存复用20459419=2N。最大dt/tau=0.000285374，spin=1.09098e-5，原限制通过。与旧longwin仅初态38列逐位相等，**没有完整prefix或全程半步验证，也没有精确HG重启验收**。

## 与旧结果比较：改善明显，但不是孤立双精度A/B

旧控制为`tests/outputs/CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out`，本轮已完整读取401个原生状态。新旧均按各自Part0的同ID坐标计算材料沉降；旧初态已变形且带速度，与FreshPR初态不同。不能把全部差异归于double应力。

以下取各自Part400：新7.2874288558959961 s，旧7.2874290006647175 s，相差−0.144769 μs。是近同时刻描述性比较，不是严格相等的验证对；不外推旧数据到有限Kw Tv=2。

| 指标 | 旧MLS | FreshPR | 数值变化 |
| --- | ---: | ---: | ---: |
| 底部当前排水面静水基准超压/Pa | 582.8764 | 92.3526 | −84.16% |
| 底部固定p0原生excess/Pa | 562.0382 | 23.9927 | −95.73% |
| 顶层材料沉降增量/mm | 2.184632 | 1.990518 | −8.89% |
| 顶−底材料相对沉降/mm | 2.112567 | 1.968410 | −6.82% |
| 内部层沉降交错指标RMS/mm | 0.001394865 | 0.000327758 | −76.50% |
| 内部层有效σzz交错指标RMS/Pa | 19.9033 | 11.0537 | −44.46% |
| bulk层10–89有效σzz交错指标RMS/Pa | 18.2332 | 0.03742 | −99.79% |

这些百分比是相应数值/诊断指标的变化，不是各物理误差的单因素因果分解。层二阶差分也不等同于已证明唯一沙漏模式来源。

旧根`figures/self_weight_consolidation_summary.csv`来自另一组根Scenario2 VTK，其末固定excess为511.759 Pa，**不是**本表旧MLS原生控制的562.038 Pa；不能混用两者或把旧图表当作本次控制。旧组常数没有由本后处理独立从旧配置解析，当前常数只用于明确标注的描述性轴/指标；不反追旧组当前HG/孔隙步长门。

## 新结果末态：沉降接近参考，仍有边界与晚期偏置

有限Kw Tv约2：

| 量 | FreshPR | H1有限Kw参考/差异 |
| --- | ---: | ---: |
| 顶层沉降增量/mm | 1.990814409 | 1.981117772；+0.009696637 mm，+0.48945% |
| 底层沉降增量/mm | 0.022110825 | 0.019793567 |
| 顶−底相对沉降/mm | 1.968703584 | 1.961324205 |
| 全层沉降参考RMS误差/mm | 0.00415144 | — |
| 底部绝对孔压/Pa | 9783.6602 | 9823.6018；差−39.9416 Pa |
| 底部当前静水基准超压/Pa | 91.0727 | 内禀超压62.6514；差+28.4213 Pa |
| 全层绝对孔压参考RMS误差/Pa | 40.8757 | — |
| 顶层有效σzz/Pa | −184.1074 | −53.4629；边界附近仍有偏差 |
| 全层有效σzz参考RMS误差/Pa | 43.7985 | — |

原生固定p0定义下末态底部excess只有22.70996 Pa；但当前排水面/粒子位置定义下超压为91.07272 Pa，静水基准差为−68.36276 Pa。**不能混用基准，不能因固定excess接近零就宣布压力残差消失。**

原有5 Pa晚期预算保持不变。按实际有限Tv约1.499到2的两点“一阶模态指数衰减＋常数”诊断：底部常数估计28.45288 Pa，均值14.76370 Pa，首模态均匀等效18.71993 Pa，均不满足5 Pa。该诊断并非无穷时间平台的严格证明；绝对总压误差约−40 Pa还包含几何/静水基准差，不属于这个5 Pa预算。原`residual_floor_budget_diagnostic_met=false`保留。

403个保存点中，H1孔压RMS误差最大105.4355 Pa，位于Part1、t=0.0182186365 s。它不能作为未保存启动波峰的上界；已有短窗及近顶部约178 Pa应力偏差仍作为局限保留，不增加自重测试消除它。H1为指定1 m域有限Kw准静态参考，不是完整惯性启动真值；HD是不同排水域的敏感性参考，不事后选取较贴合的参考替代H1。

图中的直接R定义为`q_fixed + Mf*trace(S)/(3K)`，未扣累计Darcy渗流量。排水过程中其非零/增长不能单独当作数值误差、力平衡残差或新的失败门。

## 图、数据与可视化

已逐张人工查看四张正式PNG，图例/单位/实际Tv口径与CSV一致，没有重写原生时间、插值制造相同状态或裁掉晚期偏置：

- [全Tv孔压、沉降、应力剖面](../../figures/CaseSelfWeightConsolidation_Scenario2_FreshPR_nativepr_profiles.png)，含实际legacy Tv1.5/2及最终有限Kw Tv2；对应`_selected_profiles.csv`与全量`_profiles.csv`。
- [全程历史与晚期残差](../../figures/CaseSelfWeightConsolidation_Scenario2_FreshPR_nativepr_history.png)，对应`_history.csv`、`_late_history.csv`及`_floor_estimates.csv`。
- [沉降/应力交错指标](../../figures/CaseSelfWeightConsolidation_Scenario2_FreshPR_nativepr_staggering.png)，对应history与全量profiles。
- [旧MLS原生结果对照](../../figures/CaseSelfWeightConsolidation_Scenario2_FreshPR_nativepr_legacy_comparison.png)，两个末态不同有限Tv已明确标注，不伪造同终点。

根输出`particles/PartFluid_0000.vtk`至`PartFluid_0402.vtk`共403文件已生成，约46.6 MB。孔压、p0、excess、有效应力、塑性应变等变量供ParaView检查；VTK应力显示数组为float，不替代原生binary64 SigmaState精度证据。

## 交付决定与下一步

独立[最终复核记录](../logs/sw_freshpr_review_r1.check.json)区分安全、后处理、精度和用户暂缓决定。按r6/r7：**本case计算与分析交付完成，剩余误差已记录，精度修复暂缓，直接进入Cryer保留状态的一致性审计。**不改旧physical/formal标志，不追加自重参数扫描/全程求解，不重启旧worker或监控。

本地与远端Git选择性保存检查/收据、四图、history/选定剖面/末端点/晚期与floor精简CSV及说明。67.97 MB全量profiles、原始BI4、VTK和EXE保留本地并由清单记录身份，不声称已随Git上云。原有正式/历史输出均未覆盖。
