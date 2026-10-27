# Cryer CPU Release：满足原孔压步长的有界启动对照

仅两次 fresh 启动：2.5 μs／1.25 μs，TimeMax=.0005 s，TimeOut=.000125 s，各含初态 5 帧，约 200／400 步。先常规 ReleaseCPU 构建，日志 `tests/logs/cryer_dt_short_r1_release.build.log`。不改源码、正式输入、外载离散、几何、质量、排水或任何已冻结脚本，也不运行峰窗／长程。

输入由已验收 `cryer_start_r1_Def.xml` 派生，仅改 DtIni、DtFixed、TimeMax、TimeOut 及对应 Release 注释；BAT 仅改 tag 和 CPU Release 后端，保留 8 线程。脚本复用原只读 reader／哈希／pore_dt 函数，但独立实现明确接收 dt 的检查，不修改 `cryer_start_r1.DT`，也不调用其带旧 DT 的 inspect。

配置与材料仍为 dp=.0025 m、R=.05 m、k=1e-5 m/s、q=10 kPa、mode2、无 ramp、t=0 排水、eta=.02、DBC、SPR/HG/grad=0、float 孔压／double 应力及保存位置。原孔压扩散限值约 2.97877 μs，两步分别约为限值的 .8393／.4196；机械 dterror 与该孔压限值独立检查。

执行前 binary64 累加预算给出两边保存时刻差最大约 4.34e-19 s。运行后仍必须逐对验证真实 native 时间差 <1e-12 s；若不匹配，拒绝配对、不插值。每次运行全 5 帧检查 37173 原生 ID、有限值、无排除、零塑性、真实 FSType2/3 非空且 p=0、实际载荷遥测、精度标志及原两类步长限制；第一组失败不得启动第二组。

中心定义为初始 r<=dp+1e-12 m 的固定材料 ID 集合，记录其完整 ID 和数量，并在全时段复用；不假设存在 r=0 native。记录场孔压 RMS／极值、中心材料平均孔压及径向位移、全材料位移、应力、速度、实际外载的径向和／净力／转矩／一阶矩。载荷和矩只作诊断，不以几何球面积或一维 100 Pa 阈值强加修正。

本轮预声明保守实现筛查：全部 5 对严格实际时间匹配样本，孔压场 RMS 差 <=5 Pa、同材料三维位移差最大 <=.005 mm。初始阶跃外载的声学瞬态差异单独报告；这些限值不是解析准确度阈值。正常退出或此短窗通过都不自动准入峰窗。若任一检查失败，保留结果、准确报原因，不调阈值、不再自动缩步或重跑。

从 case 根目录执行 `D:\Anaconda3\python.exe -B tests/support/cryer_dt_short_r1.py`。输出为 `tests/outputs/cryer_dt_short_r1_c`／`_h`；日志和清单在 `tests/logs`，汇总及配对 CSV 在 `tests/figures`。无 worker、notifier、Git 或自动后续计算。
