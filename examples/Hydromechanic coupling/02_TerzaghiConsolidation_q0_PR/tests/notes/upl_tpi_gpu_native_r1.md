# P1 GPU 独立原生适配与离线审查

本组三个新作者资产是 `support/upl_tpi_gpu_native_r1.cpp`、`support/upl_tpi_gpu_native_r1.py` 与本 note。只提供分别准入的 `build`、`read`、`review`；动作之间无自动串接，不运行 solver、GenCase、VTK、half 或正式 full。作者稿不是任何运行结果。

## 读器来源与 backend

C++ 主体来自真实 `upl_gpu_stabilizers_native_r1.cpp` 的已审 GPU 路径，保留其全部 22 typed arrays、原 1040 IDs、fixed 标记、恒 k、J/n/V/rho ledger、弹性、几何、signed dterror 与排水谓词。`upl_cpu_public_native_r1.cpp` 的历史文件名只是中立 BI4/type loader；未把 CPU 求解器输出改名成 GPU。新完成声明为 `stage=upl_tpi_gpu_native_r1, backend=GPU_P1_private`。

Backend 由真实 owner/start/call、GPU executable/argv、Popen 与 Win32 双 tool/target 退出、Run.out GPU 模式及 `UPL_TPI_GPU_R1` 选择证明；C++ CLI 字符串本身不证明 backend 或时间算法。A 无 TPI sidecar；B/C 有实际 ID-owned 历史 sidecar。

## 两个精确 profile

| window | update | 帧 | scalar actual end s | event/post |
|---|---:|---:|---:|---|
| debug2steps | 2 | 2 | .000012500286102294922 | 无 event，无 post |
| startup015 | 24000 | 344 | .1500034332275618 | part117=completed1600 pre-open；part118=1601 post |

调用为 `PROGRAM --read GPU DATA CLOCK_CSV WINDOW FRESH_NATIVE_OUTPUT`。计划 8 列和 dt 与原 owner 完全相同；逐次 binary64 `+=dt` 重播，不替换 native Step，不用 `n*dt` 充当实际时钟。Debug 初始 dterror 保留真实值，可是原 empty sentinel，也可原有限 signed 值；不套 CPU 的初始空区间，也不改成零。所有非初始区间必须非空且原 signed<=1e-14。

Debug 只有初始和第 2 update forced-final，无开排水覆盖，event/first-post JSON 为 null；不虚称检查 event。Release 226 post 帧各核全部 10 个真实 FS2/3 接收者，共 2260 次。completed1600 的 10 个真实 FS2/3 独立计数并确认其中 abs(p) 最大>0，证明该保存态仍 pre-open；没有新增压力幅值门。1601 之后真实接收者逐个零压。原 fs、p0、float excess、材料位置及固定标记均保留。

## 单独 build

读取既有 `upl_bigstep_native_r1.build.json`、Compile/Link 原 recipe 和冻结中立 loader，只替换新 reader TU/object；原第三方 BI4 对象、库及 ABI 参数保留。所有新 exe/PDB/ILK/object/runtime 位于 `outputs/upl_tpi_gpu_native_r1_build`，不会修改旧 reader 或源码。权威工具仍 MSVC14.36，环境以独立 literal CMD batch 加载并保留 vcvars LIB；无 shell quote 复现或旧失败重跑。

输出 `logs/upl_tpi_gpu_native_r1.build.json`。该纯原生读器 build 使用 CPU 编译器不代表读取的数据 backend 为 CPU。任何 build 失败原样封存，不能自动再次构建同标签。

## 每个动作独立 root admission

共同字段：`stage=upl_tpi_gpu_native_r1.<build|read|review>_admission`、`passed=true`、`action_only=true`、`inputs=[stat...]`。输入必须包括三作者文件、原冻结 loader/helper/recipe，以及本动作消费的实际文件；stat 使用路径/大小/mtime，不扫描旧 BI4/source/object SHA。

read/review 的 job：

```text
tag: 真实 GPU owner tag
configuration: Debug | Release
scheme: A | B | C
window: debug2steps | startup015
run_receipt, call, program, plan, run_out: 原记录 stat
output_directory, data: 原实际输出路径字符串
```

只允许 Debug/B/debug2steps 或 Release/A|B|C/startup015。实际新 build/prepare 链从原 run 消费绑定，新 source 必须具 r2 `base_prepare` 与 `host_h_API_and_other_268_files_byte_identical=true`，拒绝未补 source-role guard 的 r1 作为物理基座。不是硬锁 r1 build 文件名。

Debug 的真实 sanitizer log、target 句柄创建时间、原参数和三个退出码均须匹配。r2 device marker 实际由 `fprintf(stdout)` 输出：从原 call 的 fresh console `.log` 统计完整 marker，B/C 恰好一次，A 零次；不在 Run.out 查该 stdout 文本，也不从源码或构建推断 fixture 执行。

read 先检查已有 native receipt/output 与活动 reader（包括同 DATA 的其他 `--read`），有则拒绝重复。只创建一次 `<tag>_native_r1` 及 `<tag>.native_r1.json`；失败保留 partial。review 只消费已有通过的原生结果，不再调用读器，写 `<tag>.native_review_r1.json`。

## 28 列 sidecar 与时间公式

GPU 三文件名为 `UplTpiGpuR1.policy.json/.csv/.summary.json`；stage 仍 `upl_tpi_gpu_r1`，r2 没有改 host API/schema。CSV 28 列与已审 CPU 相同，每保存态 1000 土体行，以原 ID40..1039 校核、不按当前排序猜测。

逐行核实际 source/commit step、scalar time、dt、三个 BC 旗标、commit/endpoint/core/HG 计数，以及 native 最终 pressure/J bit 一致。B：`prediction=pn+.5*(pn-previous)`；C：`prediction=pn`。qhalf 与 endpoint q 各在原实际 source/endpoint BC 后写 float；`pnew_float=float(q+Rgamma/S)`，原最终 Dirichlet 只允许真实 constrained ID 写正零，其余必须 raw。S 仅 leading-LP 正预条件；这是 single defect correction，不是完整离散 diagonal 或收敛隐式求解。无非正 S 限幅、额外正则或迭代。

GPU 私有压力 helper 用显式 rn intrinsics，因此预测和 single-defect 写回仍精确逐位重算。**原 GPU J** 没有换算子，原 nvcc `-use_fast_math/fmad` 保留；原表达式是 `Jn + dt*Jhalf*thetaH`，左结合第一乘积先 binary64 舍入。核两种合法最终路径：分离 multiply/add；或将该已舍入第一乘积与 thetaH、Jn 作最终 FMA。用 `Fraction.from_float` 精确构成后者并以标准 ties-even 转 binary64；没有任意 ULP 容差。报告 nonfused/fused/both 精确匹配计数，native J 与 sidecar J 始终 bit 等。若实际出现未审第三种编译表达式，先失败诊断，不能扩容。

`theta_endpoint` 仅残差诊断，J 只用原机械 half theta 积分一次。native `PorePressRate` 保留旧 Kw/n 缩放 endpoint residual，**不是 B/C 实际 dp/dt**，不能据它验收时间导数。逐保存行/程序内 counters 不是 unsaved 历史独立观测，也不宣称二阶、paper literal LF、完整重启或物理验收。

## A 同 backend 无反馈与 B/C 跨 backend

A 对原真实 GPU150 短控制的五 exports，按 **实际时间 bit 与 native saved Step** 交集 join，保留旧/新声明头。不预定共享计数、不先判 forced-final 是否共享；实际旧控制最后一帧也可能是普通保存态。逐匹配记录比较所有导出字节含 clock/signed，但五 exports **不构成全部 22 raw arrays 的 bit 证明**。独立 raw22 比较由另一个已审工具承担，不重新 full decode 或伪造字段覆盖。

B/C Release 的 review 额外要求 `cpu_control={review,native,completion}` 三份实际 stat。必须是同 scheme、ReleaseCPU、startup015 的既有 passed 控制，原生 ID/初始坐标一致、344 个实际 time/Step/dt 精确匹配；不插值，不把 signed/backend FSNormal 差异改造成新等价门。

每一匹配态计算土体 pressure RMS<=5 Pa 与每个初始材料 ID 的 XYZ 位移向量差最大<=.005 mm；X 差按原 x-periodic 长度 .1 m 取 minimum image：`dx-=.1*floor(dx/.1+.5)`，Y/Z 直接相减。记录全部 344 行和最大值及 `minimum_image_x_period_m=.1`。该门仅同算法 CPU/GPU，不用于 A/B/C 不同算子之间，也不是独立 half 或理论真值。Debug 不充作 Release bit 真值。

HG 原 logical/rate/cache/stiffness/spin 门在离线再核，额外 endpoint 的 readonly snapshot 计数来自真实 sidecar，不能替代独立 HG 能量证明。所有正常短窗都不是 2Tv、完整固结、理论、通用边界或正式物理验收。
