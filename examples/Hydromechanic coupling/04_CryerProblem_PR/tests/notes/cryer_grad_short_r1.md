# Cryer 原有应力率梯度开关的0.5ms对照（2026-10-27）

本轮默认仅准备；主代理审查后才以`python -B tests/support/cryer_grad_short_r1.py --run`执行。
CPU制造场`outputs/cryer_force_cpu_r1_run/force_summary.json`已发现：原外载和常压缩应力的真实
均匀密度静态残差为0，smooth-rho残差主要为float算术量级；仿射三维速度场的应力率误差在原
`SoilStressRateGradCorr=1`后大幅降低。它是瞬时制造场证据，不是已耦合积分的物理验收。

## 唯一差异与入口

从已保留的`configs/cryer_dt_short_r1_{c,h}_Def.xml`复制两个新标签
`cryer_grad_short_r1_c`、`cryer_grad_short_r1_h`，唯一物理差异为现有参数
`SoilStressRateGradCorr:0→1`（同步其说明注释）；BAT仅更换标签。不是新增源码、API或默认值。
实际作用为应变/自旋/应力率前对三维速度梯度应用现有矩阵，不改原动量/外载/孔压力/Darcy。

两组CPU Release固定步长2.5/1.25us，终点.0005s、输出间隔.000125s，各200/400步及5帧。
原球几何R=.05m、dp=.0025m、k=1e-5m/s、q=10kPa、t=0加载和排水、阻尼=.02、float孔压/率、
double持久应力及保存位置全部不变。SPR、HG仍关；孔压体积源梯度仍沿原默认开启。
不写D克隆、不编译新算子、不调整外载或阻尼以拟合峰值。

## 验证顺序与口径

先c组通过原`cryer_dt_short_r1.inspect`全部原生安全检查，再启动h组。核验原生37173个土ID、
有限/正密度/零塑性/无排除、非空真FSType2/3排水严格零、机械自然步长及原孔压扩散步长。
检查当前canonicalCPURelease、原构建/输入和两条旧轨迹哈希；程序仍为
`dc4e2a1feb2245e5a9c567d1bc1877e774a6b70b1058e805f4c6d61aa063ca9c`。

新c/h所有5个实际时刻配对，不插值，使用原5Pa逐粒子孔压RMS/.005mm材料位移最大差阈值。
旧c/h各单组运行通过，但旧半步配对最大56.3807372399Pa未通过；本轮不修改或掩盖此结论。
另将每条新grad1轨迹与同dt旧grad0的5帧比较，记录孔压、总应力、速度、密度、材料位移、
外载、FSType/排水掩码及每个原生字段差异。跨开关变化不套半步门，也不叫理论误差或精度提升。
中心值始终使用初始r<=dp+1e-12的固定材料ID，不动态重选粒子。

如原半步门未通过，保留两条完整短窗及所有配对/原因，不放宽阈值，不自动进入峰值或长算。
只管理自身CPU wrapper子树；启动前拒绝其他Cryer CPU。允许既有GPU Debug诊断并行且不停止它，
记录并行进程，耗时不能称隔离性能比较。无通知或长驻监控。

## 记录位置

脚本在`tests/support`，输入在`tests/configs`，准备/运行/完成清单及命令输出在`tests/logs`，
原生输出在`tests/outputs/cryer_grad_short_r1_{c,h}`，summary/half/options/native_differences
四份CSV在`tests/figures`。本阶段不绘图；后续主代理据实际结果绘制必要图并作审查。
没有生产源码、正式XML/BAT或Git修改，不因切换已有参数重复构建。
