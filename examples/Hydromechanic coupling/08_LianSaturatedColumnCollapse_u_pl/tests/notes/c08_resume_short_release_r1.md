# C08 本地r3撤墙短窗与正式入口准备

服务器r2 ψ0在最后保存10.05s之后报status bits8；冻结旧源码将其映射为ApexNeeded。r3统一材料算法已包含相应顶点/张拉处理。本报告为该短窗与后处理入口的记录，不把后来失败的完整运行称为通过。

实际r2 GPU PRE保持原目录和实际时钟，r3 loader认证旧MR1 ElasticV1后仅一次退去右墙260点。三个GPU入口显式共用该PRE，不重跑10s、不使用塑性PART重启。旧21份根XML/BAT可恢复归档于tests/outputs/retired_root_inputs_r4；旧输出、包和程序保留。

ψ0新短窗实际到10.100000000405998s/global4040000，新增40000步，dt2.5µs、输出.01s、10帧。实际RTX3050程序和独立native正常退出；6800 IDs、22数组及原J/n/V/rho/k、P0/κ/FS/time守卫通过。正式读取器与独立短窗读取器四份二进制/CSV导出逐字节相同。

末平均孔压5830.804Pa、RMS8537.427Pa；平均PRE相对Δz=-3.35040mm，位移RMS7.99493mm、最大39.94348mm，速度RMS.148046m/s，最大κ=.64613086。τ=.09s的-29738.135Pa负压原样保留；本短窗不是论文精度或全程稳定验收。

正式后处理在已完成短窗实跑：native、Fluid/Bound各10帧、history与τ=.1s场图及匹配CSV；命名修复仅离线绘图并复用native/VTK。修正图在tests/figures/c08_release_short_r1，早期命名测试图另留c08_resume_short_r1。检查为tests/logs/c08_release_pipeline_short_r1.check.json。

预载Fluid/Bound各1001帧（5000/2060点）已完成，路径为原source_out/particles。PartVTK位置float，原BI4/native位置double，SigmaState与六Poro字段double，κ不是完整塑性应变张量。

三组coh为5/5/7.5kPa，不能将全部差异归于ψ。后续正式ψ0运行在10.11s后失败，见upl_c08_wall_failure_review_r1.md；本短窗结果保持真实有效但不替代其后故障诊断。
