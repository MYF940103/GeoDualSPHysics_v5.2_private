# GPU G2：核支持带加载（算子和短程移植检查通过，耦合长程待验收）

基线为`outputs/gpu_g1_verified`，清单`logs/gpu_g1_verified.snapshot.json`。不改变CPU加载公式、不混入HG/SPR/事件，不覆盖既有输出。

## 修改范围与数值含义

- `JSphGpu.h/.cpp`：新增仅力阶段存活的float raw权重；mode5才增加池容量、分配/清空/释放。沿用单层目标载荷，主机仅收取24字节总量，负raw检查与CPU一致。
- `JSphGpuSingle.cpp`：mode5刷新斜坡压力，将raw传入主邻域核，阻尼之后、最终AceMax之前归一化。
- `JSphGpu_ker.h/.cu`：mode5复用原柔性载荷邻域权重，只收集z，不提前加到加速度；只有mode5写入原单层loadace。对原生普通土粒子做固定顺序double归约，最终`Ace.z += newLoad - oldLoad`。旧模式0–4保留原路径，包括旧诊断字段行为。
- 首轮保留`JSph.cpp`的GPU mode5保护，微测通过后才移除相应限制并验证真实输入、池生命周期；HG/SPR/事件保护不受影响。参数能力说明随实际验收同步。

## 运行前判据

测试文件在`tests/support/hg_gpu_load_*`，配置在`configs`，新输出在`outputs`，日志在`logs`。主源码每轮更改后执行CPU Debug，CUDA变更另做GPU Debug/Release；类布局变化全量Rebuild，不混用旧对象。

1. 初始相同粒子几何，q分数0、0.5、1、1.5（饱和斜坡），总力依次0、−500、−1000、−1000 N/m，误差<0.001 N/m。
2. 原生ID对齐CPU/GPU raw/load/Ace，预定容差为`64*FLT_EPSILON*max(1,abs(CPU reference))`；不要求CPU/GPU不同累加顺序0 ULP。若不通过先定位，不能事后放宽。
3. 同后端mode1/mode5保持孔压及各导数率不变；合成非零背景加速度检查new−old，周期/边界/浮体/排除粒子不参与全局归一化。
4. 多block/尾部canary、零目标、无负raw的失败处理，以及重复力阶段清空；mode5真实运行另检池生命周期。
5. GPU关闭路径与冻结G1相同输入、实际时间、原生ID的物理字段精确比较。正常退出不等于物理验收。

## 首轮结果与审查中的判据修正

CPU Debug/Release 与 GPU Debug/Release 均已编译通过。GPU Release 0 警告；Debug 的旧库 PDB/CRT 警告保留在日志。

`hg_gpu_load_Debug_r1`、`hg_gpu_load_Release_r1` 的跨后端逐点 raw/load/Ace `64 eps` 工程门**失败**。不得将这些收据改写为通过。Debug 首轮启动脚本另有退出码未捕获问题，stderr 已记录实际比较失败；随后改为等待子进程并保留退出码，Release 明确 exit=1。归一化、合成总力/new−old/类型排除/多块归约检查均先于这个失败执行。

Release 最差 raw 差为约 `1.007e-4 m/s²`，在远离顶部的完整对称邻域；相应最终载荷为零。带内最低一行也有约 `5.08e-5 m/s²` 的小载荷差，不能仅凭全局合力忽略。三个主要承载层相对差小于 `2.6e-6`。初步源码审查：CPU 使用 double 坐标差再转 float，GPU 沿用旧模式2的 float 局部坐标及 fast-math。该解释需真实旧模式2同状态探针验证，尚未逐项区分坐标、乘加和求和的贡献。

在运行新来源探针前，明确以下工程评审规则：

1. 保留原全 raw `64 eps` 的失败标志及越界数量，不增大它的系数，不截断小载荷、不删除第四层，也不为拟合 CPU 近零舍入值改生产公式。
2. 追加同后端原模式2柔性加载与模式5 raw 的逐原生ID**逐位相等**检查。它只能证明 raw 来源没有新增误差，不证明旧算术无误。
3. 两端均继续满足原 `0.001 N/m` 总力门与 new−old 精确替换；追加全部原生土粒子的空间分配门 `sum(m*abs(load_GPU-load_CPU)) < 0.001 N/m`。该绝对差的总和不允许正负抵消，比只比较两端合力更严格。不是把旧 `64 eps` 调大；所有原始失败独立保留。
4. 旧模式0–4依然要求相对于冻结G1的全部输出场0 ULP。PART中的 Step 是保存前的 Nstep，PART1 保存Step0；首轮读取器误将它与PART编号相等，已修读取器约定，实际时间/粒子字段门不变，离线重读保留结果。
5. 只有上述来源、载荷、兼容性与真实mode5生命周期均通过，才可接续 G3 实现。此处修订的是新算子的工程比较尺度，不是物理验收；原后续5 Pa/.005 mm半步门和100 Pa安全门保持不变，仍需实际耦合轨迹检验。

未发布正式XML/BAT或Git节点。

### 来源及旧路径核查结果

- `hg_gpu_load_origin_Debug_r1`、`hg_gpu_load_origin_Release_r1`：每后端5阶段、5200个native记录，模式2的z载荷与模式5 raw逐位相等（0 mismatches）；两端原64 eps门均仍为false。Release完整空间向量力差最大`0.000217337406 N/m`，Debug也小于`0.001 N/m`。模式2原跨后端差与模式5完全相同，支持“继承旧邻域浮点差异”，不等于已隔离每个舍入来源。
- `hg_gpu_g2_off_r2.check.json`：5种旧模式、每种21对PART，1040 native IDs、15数组，共16,161,600比较字节，差异0；1351个去重绑定文件独立复核一致。m0只离线重读旧r1输出，没有重跑。
- 据前述明确记录的工程评审，现仅开放GPU mode5真实输入/生命周期检查。`JSph.cpp`仍拒绝GPU HG、SPR和固定网格事件；不以这次算子核查发布正式三组算例。

### G2源码定位（本阶段行号）

| 文件 | 位置与目的 |
| --- | --- |
| `JSphGpu.h` | 211 raw指针；295归一化入口 |
| `JSphGpu.cpp` | 165初始化；381仅mode5增加float池槽；753加载斜坡常量；1130原目标载荷；1151归一化及raw符号检查；1337清零；1362分配；1400释放 |
| `JSphGpuSingle.cpp` | 558刷新斜坡；592传raw至主邻域；597阻尼后、最终加速度最大值前归一化 |
| `JSphGpu_ker.h` | `StrInterParmsg`的raw参数与赋值；283–286归约/施力声明 |
| `JSphGpu_ker.cu` | 1080/1103 mode5单层目标记录；1120–1218固定顺序归约与new−old施力；1555/1623–1627主邻域收集；1979写raw；2001保护旧loadace行为；两处launch及occupancy函数指针同步参数 |
| `JSph.cpp` | 595只保留HG的GPU限制；3729日志不再误称仅CPU |
| `DualSphDef.h` | 332枚举说明去除过期CPU限定，枚举值不变 |
| `doc/xml_format/_FmtXML_ElastoplasticSoil.xml` | 48附近同步GPU候选范围、旧near-zero差异与尚未完成的耦合验收 |

函数名为稳定定位依据，后续G3可使行号移动。CPU数值公式、正式XML/BAT及旧结果未改。

## 实际 mode5 20 步检查（2026-10-17）

开放mode5之后CPU Debug/Release、GPU Debug/Release再次构建成功；Release零警告，Debug仅旧Gm弃用警告。`hg_gpu_band_run.ps1`以正式已生成输入的副本只替换TopVertical为TopKernelBand，串行运行GPU Debug、GPU Release及CPU Release，各20步、21 PART、1040原生ID，实际终时0.0002 s，正常退出且无排除。证据为`logs/hg_gpu_band_r1.check.json`及各run/parts清单。

- GPU全部保存帧载荷总量最大误差：Debug `1.5993244e-6`、Release `1.4453989e-6 N/m`，低于原`0.001 N/m`；水平及支持带外载荷均为零。PART k保存的载荷对应起点`(k-1)dt`，第20帧为−19 N/m而非−20。
- 所有输出有限，持久应力为double，旧应力字段恰为float投影。支持带归属在此窗口内不变；最小边缘余量0.004000023 m，保存端点最大运动5.96e-8 m。该检查不把保存的校正端点坐标冒充预测力步坐标。
- 21帧同native ID比较：GPU Release/CPU最大孔压差`6.103515625e-5 Pa`、最差帧RMS`5.67458157e-6 Pa`；六分量double应力最大差`2.59399414e-7 Pa`。GPU Debug压力最大差相同、最差帧RMS`4.83555199e-6 Pa`。顶部/底部各10材料点输出沉降差为零，但Pos为float输出，只能作该输出分辨率下的结论。
- CPU PART没有HydroMechLoadAce，不以空字段声称已独立复核CPU实际总外力。原零步64 eps失败原件仍保留；工程准入依据前述显式来源/空间力差规则与旧路径精确回归，不追改旧判据。

这一步准入G3设备HG开发，不是2Tv、半步或物理精度验收。HG/SPR/固定事件与三组正式输入仍未开放发布。原始结果保留；`hg_gpu_band_fields_r1.exe/obj`本轮误放logs且已绑定证据，登记待最终依赖整理，后续编译产物恢复放outputs。
