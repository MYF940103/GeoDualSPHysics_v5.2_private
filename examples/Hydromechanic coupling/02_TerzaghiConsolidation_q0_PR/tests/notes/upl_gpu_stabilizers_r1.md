# GPU 动态渗流稳定项对接：Debug阶段结论

2026-11-05。当前恒k、零重力、弹性、X周期、单向上固定FreeSlip底面的新鲜启动列柱已完成GPU实现检查。没有新增物理方程、镜像定律、时间积分或时间步限制，也没有修改CPU完整2Tv所用数值源码。

八个生产文件及用途：`JSph.cpp`限定公开组合范围；`JSphGpu.cpp`复用动态边界同阶段SPR速度并传递当前状态；`JSphGpuSingle.cpp`传递预测/校正J；`JSphGpu_ker.cu`按当前J计算AV密度和邻粒子惯性；`JSphHourglassGpu.h/.cpp/_ker.h/_ker.cu`使用当前体积/质量、参考质量历史和当前阶段J缓存。阻尼、归一化2h加载带、HG和完整Darcy的原顺序保留。2h支持带不是固定五层，初始粒距下约四层。

- CPU Debug与GPU Debug构建通过；未改写规范发行程序。
- 当前J分量16组及非法输入36组通过；原空J分量42组通过；真实GPU memcheck为零错误。
- 真实GPU Debug短窗1632步、150帧、1040 IDs、22数组、149个有符号时钟间隔及320个真排水接收检查通过。实际终点0.010200233459472378 s。
- 同时刻保留CPU Release对照：孔压RMS差最大0.0020815333 Pa，逐材料XYZ位移差最大4.6307822e-8 mm，六应力RMS差最大0.0001580035 Pa。原5 Pa/.005 mm/1e-14 s比较界限保留。Debug/Release不是逐位控制。
- 默认关闭动态渗流且HG=0、显式关闭动态渗流且HG=.1，各自旧新GPU Debug主程序391步/21帧：15个原生数组、全部IDs、有符号时钟和数值元数据均无差异。旧控制还有更早的动态阻尼接线差别，不能称单补丁隔离实验；这些差别在主开关关闭时保留旧路径。

保留的失败与修复：分量r1的仿射零解被独立密集逆矩阵舍入残差1.059e-25触发1e-25门；r2对严格仿射场采用解析零历史，原预算和非仿射密集参考检查均未放宽，旧超限残差仍单独记录。短窗cross r1错误地把力计算阶段的总力门用于保存状态代理量；归一化用Jhalf，保存质量用Jnew。两后端代理量均偏约.0044 N/m，后端代理量差最大6.8164e-5 N/m。cross r2只认可后端一致性，不宣称未直接观测的真实力阶段.001 N/m门已通过。原失败记录保留。

短窗图和CSV已人工审阅，三条物理历史几乎重合，误差远低于原比较界限；当前只接受这一有界实现检查。尚无GPU Release效率、全周期GPU、半步长新结果或通用边界/塑性/变k HG/重启验收，不替换服务器包。CPU完整2Tv的底部总应力与位移偏差仍存在。

下一步采用同一源码做GPU Release构建、短窗精度及同物理CPU/GPU耗时比较，再决定后续case测试；不重新启动半步长验证链。例行数值审查复用已封存来源记录，仅在新程序封存、交付或身份存疑时做必要SHA校验。

关键记录：`logs/upl_gpu_stabilizers_component_r2.check.json`、`logs/upl_gpu_stabilizers_short_r1.native.json`、`logs/upl_gpu_stabilizers_short_r1.cross_r2.json`、`logs/upl_gpu_stabilizers_legacy_main_r1.check.json`。图和匹配CSV为`figures/upl_gpu_stabilizers_short_r1_CPU_GPU.*`。
