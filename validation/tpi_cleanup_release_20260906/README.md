# TPI 清理后的 CPU / GPU Release 回归检查

日期：2026-09-06（日本时间）。本轮未修改求解器源码或 Visual Studio 工程。

## 结论

新 CPU/GPU Release 均完整重建成功，0 错误、0 警告。对于下面两个 Symplectic 自重固结重启工况，新版与清理前源码重建版的全部已保存粒子字段逐位一致：4 组对照、每组 11 个时刻、每时刻 1040 个粒子，最大绝对差为 0。

这证明本次 TPI 删除未改变所测试的 PR/Symplectic 输出，不代表所有积分方式、算例及长期数值精度均已验证。

另有两个必须保留的限制：原有旧 CPU Release 在 DensityRate 工况不完全一致；将重启场切换为 Verlet:40 的试跑在清理前后均出现大量粒子被排除，不能计作回归通过。

## 新可执行文件与构建

| 后端 | 可执行文件 | 完整重建配置 | 构建结果 |
|---|---|---|---|
| CPU | [DualSPHysics5.2CPU_win64.exe](../../bin/windows/DualSPHysics5.2CPU_win64.exe) | `DualSPHysics5ReCpu_vs2022.sln` / `ReleaseCPU` / `x64` | 0 警告，0 错误 |
| GPU | [DualSPHysics5.2_GEO_win64.exe](../../bin/windows/DualSPHysics5.2_GEO_win64.exe) | `DualSPHysics5Re.sln` / `Release` / `x64` | 0 警告，0 错误 |

使用 `/t:Rebuild`，没有复用旧增量对象。日志：[CPU](logs/new_cpu_build.log)、[GPU](logs/new_gpu_build.log)。GPU 使用本机 NVIDIA GeForce RTX 3050，CUDA 11.7，编译目标 sm_86；CPU 对照使用固定 1 个 OpenMP 线程。

新 CPU SHA-256：`71B20060BE8C8AED4EE604AC1B4FE41FE4E6D6042E2E20DE9CAA1CE28C113F04`。

新 GPU SHA-256：`3594F0A60841A59657E9F2D64CABAD47BA5ABC6FCD1219ABD1ADB47EE4CCED0C`。

## “之前”的两个基准

- `previous_release/`：生成新程序前保存的原有 EXE、DLL、DsphConfig.xml。原 CPU 编译时间为 2026-07-31 15:56，原 GPU 为同日 18:21，不能默认视作同一源码版本。
- `precleanup_rebuilt/`：使用 TPI 清理前的 18 个源码备份，在隔离目录恢复后，用相同 MSVC、CUDA、库及工程配置重新构建。与当前源码仅预期的 10 个 TPI 清理文件不同；全部 30 个库文件及 7 个工程文件逐字节一致。此组用于隔离本次代码清理的影响。

隔离构建目录：`C:\Users\syosh\AppData\Local\Temp\GeoDualSPHysics_TPI_cleanup_20260906_215542\release_baseline`。未向当前源码恢复旧文件。基准构建均成功，只有临时目录 MSB8029 警告，详见 [CPU 基准日志](logs/baseline_cpu_build.log)、[GPU 基准日志](logs/baseline_gpu_build.log)。

每次运行的 `run_metadata.json` 保存了执行命令、程序及输入 SHA-256、退出码、步数、粒子排除数和转换命令；运行前后核对输入未变化。

## 工况与方法

共同设置：1000 土粒子 + 40 边界粒子，X 周期边界、mDBC no-slip、边界 corrector 开启、非零孔压重启场、固定步长 `1e-6 s`、2000 步、模拟时长 `0.002 s`、输出间隔 `0.0002 s`，含初始场共 11 帧。开启 `-stable`；同一后端的前后版本使用完全相同输入，不以 CPU 和 GPU 相互逐位一致为标准。

| 标识 | 输入与重启 | 实际孔压配置 |
|---|---|---|
| `pair_symplectic` | `CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out/CaseSWSc2_MLSDirect_Tv2`；从 `CaseSWSt1_MLSDirect_GPU_out/data` 的 PART 56 重启并将时间重置为 0 | PairDivergence，梯度修正开启，边界孔压 ZeroOrder |
| `density_symplectic` | `CaseSWSc2_PR_Dens_p300_out/CaseSWSc2_PR_Dens_p300`；从上一行长时输出的 PART 300 重启并将时间重置为 0 | DensityRate，梯度修正开启，边界孔压 MLSDirect |

输入位于 `examples/Hydromechanic coupling/01_SelfWeightConsolidation_PR/tests/outputs/`。第一组的文件名虽然含 MLSDirect，实际 XML 未设置该选项，故采用默认 ZeroOrder；本报告以实际配置为准。

用相同 PartVTK 将 BI4 转为二进制 VTK，然后按完整 Idp 集对齐，严格校验重复/缺失粒子、帧索引、字段集、类型、非有限值、日志物理时间和积分步数。比较字段为：`Pos`、`Idp`、`Vel`、`Rhop`、`Sigma_kk`、`Sigma_ij`、`PorePress`、`PorePress0`、`ExcessPorePress`、`FSType`。

默认 `rtol=atol=0`，另要求存储字节一致。输出物理时间按 Run.out 的打印精度（1e-6 s）核验，并核验步数；不是从 BI4 读取完整双精度时间。本算例 SavePosDouble=0，位置及物理浮点字段为 float32，结论限于实际保存精度。现有输出没有 `PorePressRate`，没有直接比较内部瞬时孔压率或未保存的双精度状态。

不是平凡零场测试：基础组初始最大孔压约 20.398 kPa，0.002 s 内最大孔压变化约 1.543 kPa；DensityRate 组初始最大孔压约 10.677 kPa，最大孔压变化 CPU 约 0.121 Pa、GPU 约 0.140 Pa。

## 对照结果

下表比较的是所有字段、所有输出帧；“逐位一致”并非只比较孔压。

| 新版对照对象 | CPU 基础组 | GPU 基础组 | CPU DensityRate | GPU DensityRate |
|---|---|---|---|---|
| 清理前源码重建版 | 逐位一致 | 逐位一致 | 逐位一致 | 逐位一致 |
| 原有旧 Release | 逐位一致 | 逐位一致 | **不完全一致** | 逐位一致 |

全部 12 次有效 Symplectic 运行均退出码 0，2000 步，排除粒子 0。8 份详细对照 JSON 位于 [comparisons](comparisons/)；4 份清理前源码对照全部通过，共 44 对输出帧。

旧 CPU DensityRate 例外的所有输出帧最大差值：

| 字段 | 最大绝对差 |
|---|---:|
| 孔压 / 超静孔压 | 0.1171875 Pa |
| 位置分量 | 5.960464477539063e-8 m |
| 速度分量 | 2.0363222574815154e-7 m/s |
| 密度 | 0 |
| 正应力分量 | 0.05322265625 Pa |
| 剪应力分量 | 0.00354766845703125 Pa |

旧 CPU 的运行日志不显示 PoreCompressionSourceMode，其 EXE 中也没有 `PoreCompressionSourceMode` / `DensityRate` 参数字符串；而清理前重建版和新版都明确读取 DensityRate，且输出逐位一致。因此不能把该历史 EXE 的差异归因于本次 TPI 删除，也没有通过放宽容差把此项标记为通过。详见 [旧 CPU 对照](comparisons/previous_release__cpu__density_symplectic.json)。

## 未通过的 Verlet 诊断

直接将基础重启工况改为 `-verlet:40`，同样推进 2000 步，日志报告排除粒子：清理前重建 CPU 为 1789，新 CPU 为 1815，原旧 GPU 为 1000。前两个计数可能含周期副本，不能直接当作唯一土粒子个数。程序仍返回 0，但验证脚本因粒子丢失明确判定失败；原始日志和元数据均保留。

只读检查发现 CPU 在清理前已存在 `SigmaM1c` 未初始化即可能读入的历史问题，GPU 则有该初始化，因此不能用单一原因解释全部失败。另外此工况固定步长绕过孔压扩散步长限制，积分方式改变后需重新验证稳定性。本轮未修复这些独立问题，也未把这些试跑当成数值等价证据。当前不能宣布水土耦合 Verlet:40 已通过回归。

## 重现与文件范围

验证脚本：[run_regression.py](run_regression.py)、[compare_particle_fields.py](compare_particle_fields.py)。默认只运行两个有效 Symplectic 工况；`pair_verlet` 作为显式选择的失败诊断保留。运行器拒绝覆盖现有输出；再次运行需使用新的验证目录或另行归档现有目录，不要覆盖本次证据。

示例（在仓库 src 目录执行；已有输出时会拒绝重跑）：

```powershell
py -3 ..\validation\tpi_cleanup_release_20260906\run_regression.py --backend cpu --version new_release --scenario pair_symplectic
py -3 ..\validation\tpi_cleanup_release_20260906\compare_particle_fields.py ..\validation\tpi_cleanup_release_20260906\runs\precleanup_rebuilt__cpu__pair_symplectic\vtk ..\validation\tpi_cleanup_release_20260906\runs\new_release__cpu__pair_symplectic\vtk --initial-time 0 --require-bitwise
```

本轮更新了标准 bin/windows 下的两个 Release 程序及正常构建产物；新增此 validation 目录（程序备份、基准程序、脚本、日志和结果）。未修改求解器源码、VS 工程、原始算例输入或原有仿真输出；未提交或推送 Git。

## Git 归档范围（2026-09-07）

代码检查点保存本报告、验证脚本、构建日志、8 份对照 JSON，以及各次运行的 Run.out 和 run_metadata.json。EXE/DLL 备份、原始 BI4/VTK 数据及 Python 缓存仅保留本地，由本目录 .gitignore 排除。上文“未提交或推送”描述的是 2026-09-06 构建验证结束时的状态。

本报告中指向 EXE、VTK 和本机临时目录的链接属于本地证据，云端代码仓库不包含这些二进制材料；重跑还需要本报告列出的原始算例和重启文件，不能仅凭此检查点在全新环境中直接复现。JSON 已保留输入和程序哈希以便核对。
