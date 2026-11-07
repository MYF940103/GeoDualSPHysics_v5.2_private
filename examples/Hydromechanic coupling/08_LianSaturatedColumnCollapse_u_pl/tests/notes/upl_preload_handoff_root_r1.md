# 共享弹性预载交接：实现与短窗结果

r1独立包每组从头计算，不依赖PART，原样保留；本次按用户要求补共享预载后再发布r2。

生产变更：

- JSph.h/.cpp：已有gravitypreload增加默认关闭elastic_source和默认空statefile；公共数值/几何/原ID法向合同、唯一完整PRE认证、实际时钟恢复。
- JGravityPreloadState.h：读取新认证PRE的22数组、双精度应力/孔压/P0/J/θ/κ/自由面，保留原始ID及符号时间步检查。
- JSphCpu.cpp、JSphGpu.cpp、JSphGpuSimple_ker.h/.cu：源预载的Pre/Cor两阶段必须Elastic；默认false保持旧算法。
- JSphCpuSingle.h/.cpp、JSphGpuSingle.h/.cpp：完整步状态导入、真实单元重建、按ID恢复，跳过伪t0；首循环复用一次性撤墙。
- XML指导同步默认值及受限支持范围。

四种配置构建均通过；canonical bin没有覆盖。Debug的第三方缺PDB链接警告保留在原日志，无编译错误。原方程、默认路径、通用PART拒绝条件未改变。

实测是dt2.5µs、源800步/22帧、完成380步的真实PRE→接收420新步/11帧；5000土和260指定墙退休。CPU/GPU各自后续11帧全部22数组及带符号时钟逐字节一致；新连续源与旧同后端22帧也逐字节一致。跨CPU/GPU最大孔压RMS差0.0034028006Pa，XYZ差6.92025e-8mm，总应力Frobenius RMS差0.00690807Pa，时钟差0；全部原安全门及GPU memcheck通过。

图及对应CSV见figures/upl_preload_handoff_review_r1；详见logs/upl_preload_handoff_review_r1.check.json。不是10秒预载平衡、三组塌陷精度或通用精确重启验收。原始BI4/typed及源码程序归档留本地，不以Git记录冒充原始数据云端备份。r2源的真实10秒所有trial仍必须在服务器完成并保持Elastic，旧常k10秒不能追认成新源。

两组附加CPU材料承接亦通过：+2.5°/cp5kPa及−5°/cp7.5kPa，各11后续帧22字段及带符号时钟与共同源完全相同。低强度源coh=coh_r=.1Pa仅改变强度，实际predictor Radial mask4、退出1；保存的只有Step0/Time0，κ0、22数组类型数量/7060 IDs及四认证字段缺失已独立核验。实际异常发生时间未保存，未冒称0秒。发包门记录为logs/upl_preload_handoff_delivery_r2.check.json。
