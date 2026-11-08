# n3/n4相同保存几何上的成对符号shadow

仅新增同名Python和本说明，事前确认不存在且未跟踪。作者不import/执行、不读payload，不运行BI4读取器、求解器、构建、VTK或dense分析；旧helper、旧90/66分析和所有既有证据不改。根全文审阅后一次运行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_asn34_pair_shadow_r1.py --execution-authorized
```

消费已通过 `upl_c08_asn4_partial_compare_r1.check.json` 的实际cohorts和绑定，以及同scope原native收据。复用其n3真实r6 full300定位与n4真实failed66定位/门：每组只在共同66保存时刻、全部5000soil中选最小rNN/dp对应的态（并列选最早part），另选actual part65/τ≈.66；若重合去重，每组至多两条native记录，总计至多四次seek读取。n3原300头和n4原66头不变，不扫描n3余下3s，不重新解码。选态理由明确为 `common66_window_min_NN`，没有暗用完整3s最小值。

每个选定几何的所有唯一 `r<.7dp` soil对均分别评估AS指数3和4，ε=.2。CSV严格分开 `snapshot_source`、`snapshot_AS_exp` 与 `evaluated_exp`；后者只是冻结几何/应力上的局部反事实shadow，绝非新轨迹。无近对的真实态如实输出count0，不捏造pair。

数学沿用 `upl_c08_as_pair_sign_r1` 的 `tensor/cubic/sign`，正谱部与32FLT_EPS screening保持该helper原main的同一表达式，不另实现GPU特征分解。原native总应力为 `S=SigmaState_eff−pI`；`S+`保留正特征值，`F=.2*[w((r/dp)/1.2)/w(1/1.2)]^evaluated_exp`，ε只计一次。表列原总应力法向 `e'(Si+Sj)e`、AS法向 `−F e'(Si+ + Sj+)e`、净和，以及原速度给出的 `dr/dt=(vi−vj)·e`。保留实际ID、坐标、原有符号的p/P0/excess、J、κ、FS、速度和谱rank。

符号完全沿原helper：Cubic近对radial梯度为负、体积/惯性因子为正，正net normal shadow标attractive，负为repulsive；dr/dt负是当前接近。float-scale unresolved筛选仍为 `32 FLT_EPS (1+F) max(1,sum spectral scales)`，只作近零尺度观察，不是认证GPU误差界或新物理阈值。双精度eigh/核比shadow不复刻GPU的float转换、Jacobi迭代、powf、FMA或累加bits。

新前缀 `tests/figures/upl_c08_asn34_pair_shadow_r1_pairs.csv` 输出全部pair×两个evaluated_exp，`_frames.csv`按source/实际态/evaluated_exp汇总最近对和符号计数。检查为 `logs/upl_c08_asn34_pair_shadow_r1.check.json`，新鲜拒覆盖并核必要stat，无SHA。仅凭一对shadow符号与当前dr/dt不能判因果：惯性、其他邻居和真实变形可使净repulsive对继续接近。本脚本不算力幅值、完整加速度、全stencil、dense阶段或新时间积分，n4仍失败、物理验收false。
