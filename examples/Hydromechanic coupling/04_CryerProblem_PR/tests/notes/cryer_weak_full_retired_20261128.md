# Cryer 弱式试验终止与显式 u-pl 收尾

2026-11-28 按用户要求停止固定参考 weak-full 试验。先终止批处理所有者，再终止该所有者启动的 GPU 求解器，并确认两者均已退出。ν=0.20 最后保存的真实状态为第 475,670 步，物理时刻 0.90726852416992188 s，排水相对 (T_vapprox0.815)。全程目标为第 582,714 步。原同线程完成队列尚未发送。[停止记录](../logs/cryer_weak_nu_sweep_r1.user_stop_r1.json)

根目录的四份 XML、两个 BAT 和四个结果目录，以及正式区的 weak-full 专用图表已移到 `tests/outputs/retired_weakfull_20261128`。归档中保留 ν=0.30、0.45、0.10 的完整结果和 ν=0.20 的部分状态，并保留原文件名。原运行收据中的路径记录的是运行时位置。封存研究程序与历史测试证据留在原支持目录。

C04 采用既有显式 u-pl `upl_cryer_freebody_peak_GPU_r1` 作为收尾基准。ν=0.30，固定步长 (2^{-20}) s，73728 步、577 帧，覆盖排水后 0.0625 s。其各自参考下的峰幅误差为 −1.4931%、峰时误差为 +2.4708%，与三轮 TPI/P3 同一组 475 个时刻的孔压 RMS 分别为 186.71 Pa 和 190.12 Pa。现有项目 u-pl 已审查结果的适用范围为该峰窗；旧四组 u-pw 全周期结果作为独立参考。[实算峰窗](upl_cryer_freebody_peak_root_r1.md) · [同时间窗对比](cryer_peak_iteration_and_support_r1.md) · [孔压图](../figures/upl_cryer_freebody_peak_review_r1_pressure.png) · [原时间序列](../figures/upl_cryer_freebody_peak_review_r1_history.csv)
