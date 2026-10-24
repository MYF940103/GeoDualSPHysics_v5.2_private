# GPU静止多面SPR同步候选

2026-10-24。接续CPU多面制造场/脉动和Yao .1 s数值准入；不是二维理论/长程验收。旧GPU五文件及Debug/Release程序冻结为`outputs/spr_gpu_planes_base`，见同名snapshot收据。正式三组输入/结果不改，旧通知器不重启。

## 最小同步与数值影响

- `JSphGpuSingle.cpp / ConfigDomain`：与CPU一致的每mk平面/内向半空间及角点拟合中心投影，仅初始化一次；只有多个平面时按原生墙ID上传静态偏移。
- `JSphGpu.h/.cpp`：一个固定GPU double3偏移数组，单平面/开关关闭为NULL；同步初始化、释放、内存统计和调用。按原生ID索引，不参与粒子重排，不能误按当前GPU槽位取值。
- `JSphGpu_ker.h/.cu / BoundaryDerivativeVelocity`：在新拟合中心求一次MLS多项式，回到原ghost求值；零偏移保持旧算术路径，旧调用默认NULL。三分量全部重构，不改标量孔压MLS、Darcy、真实速度/动量/黏性或积分。
- NoPen准入只同步CPU已验证的轴对齐NoSlip/FreeSlip；原NoPen公式不改，斜墙仍拒绝。曲面、运动墙、塑性和大旋转仍未开放，HG独立限制不放宽。

## 先验验证顺序

1. 默认CPU Debug和GPU Release/Debug；GPU类布局变化须完整重建，VS工程仍是编译权威。
2. 两配置各9个CPU同几何的正交角/斜双墙/3D棱边三SlipMode制造场，检查全部墙粒子，不隐藏角点ROI。辅助速度限沿用`32 FLT_EPS max(.125,abs(expected))`；S/P/R对解析辅助速度的差限为20 Pa/s、2000 Pa/s、.02 kg/(m3 s)加`2e-5 abs(reference)`。
3. 原18单平面制造场、SPR关闭/单平面开启的旧GPU短轨迹逐位回归；不能以CPU/GPU接近代替旧路径兼容。
4. 新多面非零短窗/NoPen轴向兼容，再使用同物理Yao短窗；CPU/GPU5 Pa/.005 mm为交付比较，不是理论真值；GPU半步仍独立核验。通过后再决定更长2D窗，不把.1 s或制造场当通用验收。

源码暂未提交；编译/测试失败保留证据，不放宽限额或将失败候选发布。CPU Yao原节点网格两端点再进入严格载荷范围导致载宽5.9→6.1 m；101保存时刻开/关合力相同，但未观测每个内部力阶段。该既有加载离散问题另列，不在此次GPU移植中偷偷修复。

## 首轮结果及载荷观测缺口

GPU Debug/Release均重建通过，默认CPU Debug通过；Debug保留既有第三方LNK4099/LNK4098警告，无新编译错误。首个伴随构建因Windows大小写不敏感的日志名称冲突被保护拒绝，未覆盖文件；op1新标签构建通过。

两配置各9个全部墙制造场、各18个旧单面场通过；辅助速度最大误差3.7253e-9 m/s，消费者差最大约S=.5 Pa/s、P=128 Pa/s、R=.000732422。`spr_gpu_paths_r1`四条SPR/HG关开组合，各31帧×1000原生土粒子相对旧GPU程序全部已输出字段0 ULP。六个普通2-ms脉动半步对通过；第一次NoPen配置准备因已有initials而断言失败，未启动NoPen求解。`spr_gpu_nopen_pulse_r2`仅补缺少的两个轴NoPen半步对，不重跑已完成普通脉动；最大半步差.00775750 Pa / 2.41845e-8 mm。全部16条对CPU的最大压力RMS差3.76261e-5 Pa、材料位移差4.80413e-10 mm；能量/几何/原生ID和自然步长检查通过。该过程没有放宽原门。

case06首批GPU原程序/伴随各三条0.02 s均已完成，但分析被实际载荷诊断全零阻断：压力/位移非零、载荷实际已施加，旧`KerApplyHydroMechTopLoadAcceleration`只给mode5写外载诊断，mode3输出缺项。不是SPR边界计算失败，也不据此把合力门记为通过。

修复前五文件/两程序冻结为`outputs/spr_gpu_planes_preload_verified`。本轮另作GPU **仅输出**修复：外载核给所有实际加载模式写已施加量，邻域载荷诊断累加到已有外载，不覆盖；原Ace写回完全不变。接下来必须证明mode3全部非载荷原生字段对保留0.02 s轨迹0 ULP，并重查原mode5兼容。旧Yao输出/失败收据原位保留，新标签验证，不重写旧零值、不放宽力/半步门。

## 仅输出修复与最终短回归

Release/Debug和默认CPU Debug重新构建退出0（`spr_gpu_load_*_r2.build.log`）。`spr_gpu_paths_r2.check.json`仅新跑当前GPU四条SPR/HG关开组合，对采用的旧程序控制仍为31帧×1000原生土粒子全部字段0 ULP。case06新`spr_yao_gpu_load_grid02_r2.review.json`：三条21帧全部非载荷字段对修复前GPU轨迹0 ULP；实际加载力现在可观测且对CPU相同，未更改物理方程。共同实际时刻原程序/整数保存伴随仍逐位一致（粗步各9帧、半步5帧）。CPU/GPU最大压力RMS差2.01875e-5 Pa、材料位移差6.67728e-9 mm；独立GPU半步差0.0705758 Pa、0.0000113782 mm。原5 Pa/.005 mm限制未改。更长GPU .1 s使用新标签，不由此宣布二维理论验收。

`spr_gpu_delivery_r1.check.json`汇总18 GPU多面、36旧单面、八个脉动半步对、四条旧路径回归；PNG/CSV同前缀。当前Debug三维棱边S2的全部1104墙点经compute-sanitizer memcheck为0 errors，不冒称所有GPU核/输入已查内存。历史MSBuild缓存中两配置的核obj被输出修复重编译覆盖，不能重新核验旧obj；旧构建收据、当时五文件源码快照、链接exe及原始结果哈希保留，清单明确列出缓存证据限度。

`spr_gpu_scope_r1.check.json`由当前真实GPU程序核验曲线/球面、平移/转动墙及斜NoPen NoSlip/FreeSlip共六个预期拒绝，均在产生PART前拒绝。成功制造场和脉动共25个GPU可点击复现BAT已补到configs（`spr_gpu_reproduction_bats_r1.json`）；调用固定的当时伴随exe，手动新输出带`_gpu_manual_r1`，拒绝覆盖。它们不是正式固结BAT，也不会自动生成汇总图。

### 本轮生产源码具体位置

| 文件及入口 | 功能和目的 |
|---|---|
| `JSphCpuSingle.cpp: ConfigDomain` | 每mk平面/公共内域检查；静态计算角点拟合偏移；轴向NoPen准入，斜向拒绝。 |
| `JSphCpu.h: BoundDerivativeFitShift / InterpolateBoundaryGhostFieldT` | CPU原生ID缓存与默认关闭的速度拟合重心选项。 |
| `JSphCpu.cpp: InitVars / GetAllocMemoryCpu / InterpolateBoundaryGhostFieldT` | 清理和内存统计；新中心拟合、原ghost求值，仅速度消费者启用。 |
| `JSphGpuSingle.cpp: ConfigDomain` | GPU同样的静止多平面准入及一次性偏移上传。 |
| `JSphGpu.h/.cpp: BoundDerivativeFitShiftg / InitVars / FreeGpuMemoryFixed / ComputeBoundaryDerivativeVelocity` | 固定数组生命周期/统计与按原生ID传参；单平面保持NULL。 |
| `JSphGpu_ker.h/.cu: BoundaryDerivativeVelocity / KerBoundaryDerivativeVelocity` | 三分量MLS在移入中心拟合、回原ghost求值；不改标量孔压MLS。 |
| `JSphGpu_ker.cu: KerApplyHydroMechTopLoadAcceleration / KerInteractionForcesFluid` | 仅补实际外载诊断、非band邻域诊断累加；Ace计算不变。 |

没有修改`.sln/.vcxproj`，没有新XML参数。XML指导文件同步当前**有界候选**范围；正式case02输入/结果/图表不动。不是塑性、任意曲面/移动墙、大旋转或精确HG重启验收。

## Yao加载后0.3 s与检查点

case06 `spr_yao_gpu_post03_r1`三条GPU完成并经原生/哈希/图表复核：301个半步对最大0.277974 Pa/.000287018 mm，加载后最大0.140043 Pa/.000182407 mm；全部101个各自0.1 s相同步长前缀0 ULP。CPU证据仍仅到0.1 s。原61节点条带满载约30500 N/m，相对理想30000 N/m高1.667%；开/关保存时刻合力相同。详见case06 notes、audit/visual收据及mechanics/fields PNG/CSV，未改正式输入。

本轮据此备份的范围是“已通过算子/脉动/旧路径/0.3 s GPU及0.1 s CPU检查的静止凸多面候选”，不是发布完整二维精度结论；后续1 s CPU/GPU和更长二维物理验证仍另列。未合入任何斜NoPen旋转修复、密度KEEP、动态Darcy或TPI。
