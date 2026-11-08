# C08团聚/张拉相关的定量几何诊断（作者稿，未执行）

仅新增同名support脚本和本note。ε=.2使用r5真实300帧，ε=.5使用已封口66帧；不重新读另一份ε=.2窗口payload。明确核 `stage_trace_window_GPU_r1.prefix_r1.check.json` 的66/300原头、全部22/time/signed/layout逐位一致及其真实输入绑定，利用r5前66帧代表同一ε=.2窗口，不重写header/count。两份实际payload分别顺序读取300/66帧，复用原22 schema及ID/finite/真实时钟检查；全5000材料ID2060..7059，ROI始终全域，不挑点或重选好看区域。

每帧cKDTree只查soil xz的最近两个非self邻居，报告rNN/dp及rNN/(dp√J)的min/q05/median/q95/max。后者仅2D等厚、局部各向同性spacing proxy，未使用真实F，不能消除剪切各向异性。r1/r2亦报分位数，r2=0单列并保留未定义ratio，不填零。唯一过近对数用严格r<.5dp/.7dp；另报互为最近邻对，以及r1<.7dp且两端r1/r2<.5的“孤立近对”。这些都是固定描述阈值，绝非物理验收门。

低连通proxy为1.5dp内soil邻居数<4，另记录nearest gap>1.5dp。称“geometric interior”前同时要求非FS2/3、距真实FS2/3点和fixed B markers均至少kernel R；近FS和近墙另分组，避免把外包络/截断邻域当内部裂缝。不使用Delaunay/Voronoi长边。已有FS可能同时包含外表和新内表，不能据这些proxy断言内部裂缝，也不能因内区无计数排除裂缝。

固定κ阈值.1f分高/低组，membership随实际保存κ演化；另有all/interior/FS-zone/wall-zone组。每组记录p/J/n/κ、总应力最大主值的范围/均值，以及与NN和√J-spacing proxy的Pearson相关；常量或空组相关记未定义。张拉量取原double σeff−pI的最大主值>0，非GPU float AS谱位真值。负p与总张拉部分关联由该代数定义产生，NN小也可能来自真实压缩/剪切，因此相关、κ高或颜色都不能直接证明张拉根因。

输出history CSV与一张raw neighbor图：ε=.2实际约.23/.66/1.2/3s，ε=.5仅.66，共5态；完整原点、原FS三角、灰fixed标记、红色过近对、κ高薄圈及仅内区的稀疏叉标。NN色标由五态全soil实际范围确定、不裁剪；全soil共同物理视窗加2dp墙层，远长床可在视窗外。无平滑、拟合、接触反力或裂缝识别声称。

root全文审后唯一离线调用（作者稿未import/运行）：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_clustering_r1.py --execution-authorized
```

fresh输出 `tests/figures/upl_c08_clustering_r1_history.csv`、`_neighbors.png` 与同名logs check。无BI4解码、solver/VTK/build/通知/自动后续/SHA，不改旧代码或分析；passed仅诊断完成、physical_acceptance=false，PNG仍需根视觉审查。
