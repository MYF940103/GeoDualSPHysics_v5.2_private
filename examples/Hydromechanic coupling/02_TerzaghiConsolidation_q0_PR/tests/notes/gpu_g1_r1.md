# GPU G1：应力状态双精度同步

2026-10-17。接续已通过的 CPU 合入和边界接口回归；这是分步实现验证，不是新的固结物理验收。G2 核支持带加载、G3 设备端 HG、GPU 导数边界和事件对齐另行实施。当前阶段不开放它们，不改正式 XML/BAT 或 Git。

## 修改范围和目的

- `JArraysGpu.h/.cpp`：新增 48B 应力状态池；24B 率、SPS 和人工应力池保留。
- `JCellDivGpu.h/.cpp`、`JCellDivGpu_ker.h/.cu`：完整六分量 double 排序，保留固定边界前缀和原索引语义。
- `JSphGpu.h/.cpp`、`JSphGpuSingle.cpp`：主应力、预测/Verlet 历史、CPU 下载缓冲改为 double；覆盖分配、扩容、排序、上传下载、初始化和 PART。双精度状态新增 `SigmaState_kk/ij`；旧 float 显示字段继续保留。保存顺序与已有 CPU/loader 一致。
- `JSphGpuSimple_ker.h/.cu`：积分累加及本构应力变量采用与已接受 CPU 相同的 double 精度；应力率、材料常数及塑性历史参数仍为 float。不改变本构公式或积分时序。
- `JSphGpu_ker.h/.cu`：所有应力消费者使用正确的 48B 类型；力学和边界局部算术先显式转为原 float，周期复制则完整保留 double 位。
- `JDsGaugeItem.h/.cpp`、`JDsGaugeSystem.h/.cpp`、`JDsGauge_ker.h/.cu`：测力输入同步 double 类型，但局部力运算仍为 float，禁止沿用旧 float2 指针强转。
- `doc/xml_format/_FmtXML_ElastoplasticSoil.xml`：同步精度范围及尚未完成的 GPU 验收状态；没有新增参数。

准备补丁为 `support/gpu_g1_{storage,host,steps,forces,gauges}.patch`。旧 CPU/源码证据冻结为 `mdbc_vector_base`；旧已安装 GPU 二进制和Intermediate目录C++对象额外保存为 `gpu_g1_base`，不包含VS/x64目录CUDA对象，后者不是新构建或物理基线。

## 预先确定的分步验证

1. 生产构建：默认 CPU Debug，以及 GPU Debug/Release；类布局/类型变化全量 Rebuild，不替换权威 VS 工程。
2. `hg_gpu_stress_test.cpp` 调用实际 GPU wrapper：小于 float ULP 的应力增量在 10000 步后保留；预测/校正与 Verlet 历史；零率低位不丢失；混合粒子类型和尾端越界保护；48B 池、排序、周期复制、真实扩容/下载。
3. CPU 实际本构函数为独立参考。非线性 CPU/GPU 比较限额在测试前固定为 `32*FLT_EPS*scale`；不能把跨架构舍入差异要求为 0 ULP。状态复制及零率保真要求逐位一致。
4. 实际测力 kernel 的三轴手算矩阵列比较：`16*FLT_EPS*max(1,abs(expected))`；原生 ID 重排、周期副本排除、不同 mk 排除及 float 投影不变的 double 低位扰动要求逐位一致。该微测不代表总力归约或耦合验证。
5. 复用正式 k1e-4 的生成输入，只读；HG/SPR/带载荷关闭，以新输出 `tests/outputs/hg_gpu_io_r1` 运行 20 步、每步保存 PART。已有 `stress_io_r2/stress_io.exe inspect <data> 20` 检查实际 GPU 保存及实际 loader、原生 ID、六分量 double 精确回读和 float 显示投影，并要求至少一个土粒子有非 float 低位。没有覆盖到低位则记录为覆盖不足，以新标签增加步数，不调低检查要求。
6. G1 微测/PART 通过不代表 GPU HG、带载荷、SPR、完整重启轨迹或完整 2Tv 通过。后续仍按原计划逐步接入及同条件验证。

所有输出使用新标签，失败日志保留。当前本记录仅为应用前范围与门槛说明，尚未宣称 G1 构建或执行通过。

## 应用与构建进展

五份补丁已经应用，静态逐文件比较确认19份源码为冻结版本加上述补丁。随后GPU Debug r1实际构建在 `JSphGpu_ker.cu:2162,2174` 的核信息查询函数指针发现两处遗漏：匿名参数中的应力类型仍为`const float2*`。这是同两处类型错误在模板实例中的重复报错，不是101种数值问题。主线程另作两行`const tsymatrix3d*`修复，保留r1失败日志，重启全量Debug Rebuild r2；因此最终源码还包含这两行补充，不伪称全部只来自五份原补丁。

CPU Debug r1已正常退出0。尚未进行实际GPU微测或PART验收；G2/G3与生产GPU功能开放仍等待G1完成。

### 实际验收结果（后续更新）

- CPU Debug r1：退出0，53条既有Gm/第三方PDB警告；CPU Release r1：退出0，零警告。
- GPU Debug r2：全量Rebuild退出0，54条警告（含第三方PDB/Gm及静态CRT冲突提示）；GPU Release r1：全量Rebuild退出0，零警告。原r1编译失败记录保留。
- RTX 3050上的 `hg_gpu_stress_Debug_r1`、`hg_gpu_stress_Release_r1` 均实际执行并退出0，各11类检查、2145项数值记录通过。不是只编译。每次执行前后均核验全部build输入及程序哈希。
- 给定小应力率10000步的最大累计误差两配置均为 `6.572008715e-9 Pa`；零率/复制/排序/周期/扩容低位保真门通过。CPU实际本构参考最大绝对应力差Debug `0.003567224 Pa`、Release `0.003701297 Pa`，均在预定32 float eps尺度门内。测力手算最大差 `1.192092896e-7 m/s²`，重排/低位投影不变门为0 ULP。
- `hg_gpu_io_r1`：实际GPU程序20步、终时 `0.00020000000000000001 s`、21个PART、1040个原生粒子（1000土粒子）、零排除。真实PART20中720个土粒子的2842个应力分量含非float低位；实际loader六分量精确回读、原生ID、旧float字段投影全通过。相应最大float舍入差 `5.908966072e-8 Pa` 是该短窗字段尺度下的值，不是长期精度收益。
- 收据在 `logs/hg_gpu_stress_{Debug,Release}_r1.check.json`、`logs/hg_gpu_io_r1.check.json` 及相邻build/run记录。`hg_gpu_io_run.ps1` 只读复用了正式生成输入，没有修改或覆盖其旧结果。

结论：G1实现级检查通过，可继续G2；未声称GPU完整固结、HG、SPR、塑性大变形或通用精确重启验收。为后续改动保持可审查基线，现有 `mdbc_snapshot.ps1` 仅增可选 `-IncludeGpu`，把GPU的C++及CUDA对象、两端程序和G1支持脚本一起冻结；此前各快照含各自原脚本，不改写旧收据。

### G1 源码位置（本阶段应用后）

行号用于定位本阶段版本；后续G2/G3可能使行号移动，函数名为稳定定位依据。

| 文件 | 位置/功能 |
| --- | --- |
| `JArraysGpu.h` | 95 SIZE_48B；111 GetArrays；149 ReserveSymatrix3d；170 Free |
| `JArraysGpu.cpp` | 150/167 构造析构；184 Reset；201内存计数；221 SetArraySize |
| `JCellDivGpu.h` | 160 double SortDataArrays声明 |
| `JCellDivGpu.cpp` | 355 double SortDataArrays实现 |
| `JCellDivGpu_ker.h` | 58 double SortDataParticles声明 |
| `JCellDivGpu_ker.cu` | 623 double排序核；726 wrapper |
| `JSphGpu.h` | 108/157主应力；172/178历史；255/268保存恢复重载 |
| `JSphGpu.cpp` | 307主机分配；385/396/403池槽；437扩容；618 Reserve；776上传；810下载；1063历史初始化；1183自重；1433预测器 |
| `JSphGpuSingle.cpp` | 159重启读取；408/444/466三类状态排序；1092–1100双精度PART字段 |
| `JSphGpu_ker.h` | 156交互状态；270Bui；300/310边界；376/380周期接口 |
| `JSphGpu_ker.cu` | 52/56转换；668/687Bui；1427/1732及1914/2057力核；2162/2174核信息指针修复；2347/2677mDBC；3085cDBC；4635/4689周期复制 |
| `JSphGpuSimple_ker.h` | 46/54/61积分接口 |
| `JSphGpuSimple_ker.cu` | 124/130不变量及屈服；154导数；184/307本构；428/605Verlet；637/791预测；825/1006校正 |
| `JDsGaugeItem.h` | 172基类GPU接口；236/313/382/462派生类接口 |
| `JDsGaugeItem.cpp` | 388/618/827/1072四类GPU测量入口 |
| `JDsGaugeSystem.h` | 195 CalculeGpu声明 |
| `JDsGaugeSystem.cpp` | 478 CalculeGpu实现 |
| `JDsGauge_ker.h` | 49测力wrapper声明 |
| `JDsGauge_ker.cu` | 311测力kernel；392 wrapper |

新增测试支持仅在本case的`tests/support`：`hg_gpu_stress_test.cpp`及其build脚本、`hg_gpu_io_run.ps1`、`gpu_g1_snapshot.ps1`及五份准备patch；结果在`tests/outputs`，构建/运行/检查记录在`tests/logs`。未改正式输入、未提交Git。旧快照/失败记录保留。
