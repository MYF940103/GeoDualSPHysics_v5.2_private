# mDBC 标量重构接口整理

2026-10-17。本轮先消除孔压参数名承载速度的歧义，不改变物理模型、离散表达式或支持范围。沿用用户暂时接受的一维精度结论；不恢复 KEEP 密度诊断。三模式、二维／三维向量推广是下一项独立工作，不在本轮声称支持。

## 修改及冻结基线

| 位置 | 功能和目的 |
| --- | --- |
| `src/source/JSphCpu.h`，`InterpolateBoundaryGhostScalarT` 声明 | 新增中性标量插值辅助入口；孔压模板移除 `wallvelocity` 参数。不新增成员、数组或运行时开关。 |
| `src/source/JSphCpu.cpp`，`InterpolateBoundaryGhostScalarT` | 原邻域循环改为标量命名，采样和写回由局部模板回调给出；保留累加次序、精度、矩阵、有效判据和零阶回退。 |
| 同文件，`InteractionPorePressureMdbcCorrectionT` | 独立孔压入口，读取 `p-p0`，写回 `float(p0+excess)`。 |
| 同文件，`ComputeBoundaryDerivativeVelocity` | 独立速度入口，读取 `vz`，写回 `-float(0.0+velocity)`；原边界初始化及更新时刻不变。 |

修改前版本保存在 `outputs/mdbc_base`，459 个文件，哈希收据为 `logs/mdbc_base.snapshot.json`。含源码、VS 工程、CPU Debug/Release 对象和执行程序。旧输入及轨迹仍在原位，没有覆盖。

本轮不改变 `MassFluid/rho` 先 float 除法再转 double 的计算，也不改变速度最终 float 转换和负号的次序；是否保持逐位一致由真实生产轨迹检查，不仅凭代码审阅判断。

## 测试安排

| 标签 | 检查 | 状态 |
| --- | --- | --- |
| `mdbc_scalar_cpu_debug_r1` | CPU Debug 全量 Rebuild | 通过，0 错误；53 条旧选项及第三方库调试符号警告 |
| `mdbc_scalar_cpu_release_r1` | CPU Release 全量 Rebuild | 通过，0 错误、0 警告 |
| `mdbc_scalar_dbg03` | Debug 0.03 s 真实积分、安全及缓存计数 | 通过，3000步、31帧；离线收据 `mdbc_scalar_dbg03_r2.smoke.check.json` |
| `mdbc_scalar_015_c` | Release 0.15 s；dt=1e-5；与冻结生产粗步轨迹逐位比较 | 通过；151帧，物理／原生ID／HG／drained及完成计数全部一致 |
| `mdbc_scalar_015_h` | Release 0.15 s；dt=5e-6；与冻结生产半步轨迹逐位比较 | 通过；151帧，物理／原生ID／HG／drained及完成计数全部一致 |
| `mdbc_scalar_off01` | HG、SPR、事件对齐关闭，0.1 s | 通过；11帧，全部字段及初末态逐位一致 |
| `mdbc_field_dbg_on_r2` / `mdbc_field_rel_on_r2` | Debug/Release 真实函数的常量／线性 vz、超孔压及字段隔离 | 通过；每种构建4项、40原生及32周期墙粒子 |
| `mdbc_field_dbg_off` / `mdbc_field_rel_off` | SPR 关闭无操作 | 通过，两种构建均未分配或修改辅助速度 |

开启积分配置保持 xi=0.1、阻尼系数0.04、SPR和固定格点排水事件开启，1 ms采样。关闭回归保持原参考的 xi=0、阻尼系数0.02、SPR/事件关闭，10 ms采样。原生粒子ID、物理字段、初末二进制及HG历史都必须相同；本轮两侧都是生产代码，`drained` 显示列也必须完全相同，不再借用旧0.01 s显示例外。短窗不是新的2Tv物理验收。

03:53 JST两条开启路径均完成严格回归，粗步实际终时0.15000000000000924 s，半步0.15000000000007963 s，各15000／30000步。旧半步误差可经这两条完整同dt等价轨迹继承，并非重新计算新的半步物理指标。此版将冻结为 `outputs/mdbc_scalar_base` 后再进行向量扩展；后续旧制造场源码使用冻结头文件／对象，不能拿旧标量成员名直接编译新的向量类。

制造场两种构建的最大速度误差均为1.9110739213346051e-8 m/s、孔压误差3.3560395280574085e-6 Pa，满足事先规定的 `32*FLT_EPSILON*max(1,abs(expected))`。它检验重构算子，不是时间积分或二维／三维推广验收。

首次制造场的两条ON记录因PowerShell未取得极短进程退出码而失败；数值输出已通过，但没有把空退出码当成功。修复runner后以r2新标签重新执行并确认exit=0。Debug首次离线检查在组装收据时引用了错误模块的LIMITS；检查器引用改正后以新r2标签复核，未改安全阈值。旧失败收据和输出均保留。

新支持文件：`support/mdbc_snapshot.ps1`、`mdbc_refactor_check.py`、`mdbc_scalar_test.cpp`、`mdbc_scalar_build.ps1`、`mdbc_scalar_run.ps1`。短窗入口为 `configs/xCaseTCq0_mdbc_scalar_win64_CPU.bat`；已有输出时拒绝重跑，不删除结果。配置、日志及输出分别沿用 `configs`、`logs`、`outputs` 浅层位置。未修改正式XML/BAT、VS工程或Git提交。
