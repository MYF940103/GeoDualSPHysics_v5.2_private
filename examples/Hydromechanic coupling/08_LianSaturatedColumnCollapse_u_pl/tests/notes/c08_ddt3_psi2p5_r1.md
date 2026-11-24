# C08 正剪胀角 +2.5° 的 DensityDT=3 单因素对照

2026-11-24。基准为根目录无 HG 显式 u-pl 的同组预载及完整三秒撤墙结果。候选的预载和撤墙 XML 均保留该组材料、几何、步长、输出时刻和其余选项，`DensityDT` 由 0 改为 3，`DensityDTvalue` 沿用解析器默认 0.1。接收配置使用候选预载自己的输出路径。此选择器在土体路径控制六个有效应力分量的数值扩散。

| 阶段 | 输入（tests/configs） | 对应预定输出（tests/outputs） |
|---|---|---|
| 10 s 同材料预载 | c08_ddt3_psi2p5_pre_r1_Def.xml | c08_ddt3_psi2p5_pre_r1 |
| 撤墙后 3 s | c08_ddt3_psi2p5_r1_Def.xml | c08_ddt3_psi2p5_r1 |

原始版本的配置兼容性测试单独放在 `tests/outputs/c08_ddt3_psi2p5_preflight_r1`。两份定义均由项目 GenCase 生成成功（退出 0）。公共 CPU Release 使用 `-cpu -ompthreads:1 -stable -mdbc_freeslip -nsteps:1` 启动候选预载，实际退出 1，在 `JSphCpuSingle::LoadConfig` 报出 `Drainage mode=freeSeepage requires the supported fresh dynamic gravity container.`。生成的原生 PART 为 0，无法据此测量塌陷表现。该公共程序编译时的 `IsDynamicPoreContainerConfig()` 要求 `TDensity==DDT_None`；交接状态的生成程序、选项及接收端合同须一致。所有实际 argv、退出、可执行文件大小、修改时间、源码节点和日志路径见[启动收据](../logs/c08_ddt3_psi2p5_preflight_r1.json)。

后续物理比较沿用同一组已完成的 DensityDT=0 基准和论文图 15。按原始保存时钟读取撤墙后 0.3、0.6、1.2 s 的材料前缘，基准相对文献可见边缘的差分别为 −0.0663、−0.3277、−1.1645 m。重点看 1.2 s 明显偏短的前缘与缺失的滑块运动，同时比较早段外形、材料沉降、孔压极值和异常近邻；注意色块读图的不确定度约 0.032 m，且文献超孔压参考与数值材料 p−p₀ 未证实完全等同。全部 5,000 个土粒及固定边界身份、排水条件、材料状态及 (J,n,k,\rho) 一致性保留原有核验。

修改后，显式 u-pl 能按原有算例和边界条件启用 DDT3 应力扩散。C08 的同材料预载和撤墙采用一致的扩散选项。已有 SPR 的显式 u-pl 算例也可组合 DDT3，SPR 处理墙面导数速度，DDT3 只取土粒间的应力差。CPU `InteractionForcesFluid` 与 GPU `KerInteractionForcesFluidBox` 使用土粒邻居计算六分量应力扩散。法向应力采用原有重力参考修正，再将扩散率并入弹性应力率。预测步使用半步长，校正步使用整步长，随后执行原有材料返回。动态混合密度继续由当前 J 计算。静止时即便合力恰为零，新的 DDT3 路径也写回应力扩散率。这是源码审查结果，实际的 CPU/GPU 输出和论文对照另行记录。

## 运行核验

CPU Debug 的 40 步预载短测覆盖 5 个实际保存时刻。关闭扩散时，新旧程序的全部 22 个原生数组、实际时刻及带符号的步长诊断逐字节一致。开启后，第 40 步全体 5,000 个土粒的竖向有效应力差 RMS 为 12.80 Pa，最大值为 60.94 Pa，孔压差最大值为 21.63 Pa。程序正确拒绝用旧 OFF 预载启动 ON 撤墙。[CPU 短测](../figures/c08_ddt3_smoke_CPU_r1.csv)

在旧预载末帧，同一内区的有效竖向应力梯度为 10.432 kPa/m，总竖向应力梯度为 20.431 kPa/m。现有应力扩散使用的背景量值为 20.331 kPa/m。新运行保留原公式，检查这一差异对上下边界和撤墙后运动的实际影响。[预载梯度](../figures/c08_ddt3_prestress_review.csv)

旧 OFF 基准采用已核验的归档同材料预载及随后新算的撤墙。DDT3 对照采用独立构建的 GPU Release，重新计算预载和撤墙。GPU 短测及完整计算跟随本机原 −5° 基线进程，阶段记录在 tests/logs/c08_ddt3_after_baseline_r1.*。对照结束后，根据前缘、场分布及材料历史决定是否推广至其他剪胀角。
