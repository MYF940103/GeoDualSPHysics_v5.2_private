# 单底面 SPR：2 ms 实现与短窗筛查

本轮只在已封存的 G1/ShepardOFF 输入上添加 SoilBoundaryDerivativeSPR=1。SlipMode=1、NoPen 关闭、k=0、阻尼 .02、材料、Wendland/Symplectic、黏性路径、float 孔压/密度与 double 应力不变。没有改 C++/CUDA、正式 XML/BAT、程序、旧数据或 Cryer 服务器。

CPU8、GPU 同步长 1 us（2000 步）和独立 GPU 半步长 .5 us（4000 步）顺序完成，各保存 5 个对齐实际状态。TimeOut=.0004999 仅用于避开浮点输出门槛导致的错时，不改变积分步长。全部原 1040 ID/38 字段安全、p0、float32 excess、排水、几何、时钟和自然步裕量检查通过，进程正常退出；后序作业均在前序通过后启动。

| 独立比较 | 全 5 样本最大孔压 RMS 差 / Pa | 最大材料位移差 / mm |
| --- | ---: | ---: |
| 同 dt CPU/GPU | .007416669124 | 1.411889362e-8 |
| GPU 粗/半步长 | .067502915697 | 1.381744549e-8 |

原 5 Pa/.005 mm 门槛未变。每组对自身保留的 G1/SPR0、同后端同 dt 的 5 个状态作描述性比较；全部初始 38 字段逐位一致，后续开关差异不应用半步长门槛。没有插值、重写保存步号或重复计算旧控制组。

独立审计复读 15 个新状态和 15 个保留控制状态，逐个重算 1500 行 profile、25 对比较及 1750 行差值；485 个去重文件共 210784274 B 的 SHA/大小均一致。三组退出码为 0，无自有残留进程。

GPU 粗组在实际 2 ms 的描述性差异：

| 量 | G1 / SPR0 | G1 / SPR1 |
| --- | ---: | ---: |
| 底部材料沉降 / mm | .000895593645 | .000579237721 |
| 顶部材料沉降 / mm | .010326483787 | .010273650993 |
| 底层平均孔压 / Pa | 21926.23359 | 22120.61426 |
| 非顶层 990 粒子 R RMS / Pa | .0205710244 | .0201432090 |

底部启动位移减小，但这不是静力理论精度改善的证明；2 ms 仍是强启动瞬态。R=q_native+Mf trace(sigma)/(3K) 继续保持小值，不等于理论孔压误差。所有 100 层都在每组 500 行 profile CSV 中保留；没有删除顶排水层以美化物理解。

实际日志同时确认 MirroredWallDerivatives、一个固定墙平面、DBC vel=0、NoPen=False 和 G1。这里没有把 vel=0 改成 FreeSlip；水平固定底面的导数速度为 (0,0,-vghost_z)，黏性仍使用原 dv_visc。SPR 会改变连续性、应力率和孔压压缩项；本短窗 rho 仍观测为 2100，但未将其强制设为验收条件或承诺未来不变。

Simulation Runtime 为 CPU8 3.451617 s、GPU 粗组 6.081688 s、GPU 半组 12.257405 s。仅为短窗实测，不能代替受控长程基准。下一轮采用同 GPU 是为隔离 SPR 选项，而不是声称 GPU 更快。

证据：logs/sw_spr_short_r1.check.json、三份 job receipt/completion、configs 中 XML/BAT、figures 中每组 frames/history/profiles/pairs/differences CSV。生产程序和 BI4 本地保留，不将清单称为原始数据的云备份。

下一步只准入一个 fresh GPU .3 s SPR1 比较；控制组使用已完成的 sw_grad_stage1_r1_g1_off（SPR0/G1/ShepardOFF）。先检查同实际时刻的底部柔度、全部材料层交错与末窗变化，再决定是否继续固结阶段。现有 SPR 禁止 PartBegin，本轮不绕过此限制，不自动许可一般重启、HG 历史、塑性或正式长程。
