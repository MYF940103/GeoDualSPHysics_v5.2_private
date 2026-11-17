# P2 GPU 两次完整 endpoint defect：私有 helper 作者稿

2026-11-17。新增 `tests/support/upl_tpi_p2_gpu_r1.h` 与本说明；**仅作者，未接入源树、prepare、build、fixture、求解、读取器、VTK 或 Git**。完整基座是 `outputs/upl_tpi_m0_dt_GPU_r2_source/upl_tpi_gpu_r1.h`，不是 staged-load 树；不引入 H3、反射、负压裁剪或 C08 状态。

已读 `upl_tpi_p2_reuse_contract_r1.md` 和 `upl_tpi_endpoint_defect_scalar_fixture_r1.md`。标量规格只提供数学与实现检查方向，不是实际完整 Rgamma kernel、GPU RN/FTZ 或物理改善的认证。

## CUDA 可见闭包与默认路径

namespace、include guard 和所有既有 View/Core/Observation/DeviceState/Error、device API、外部函数签名原样保留。原 `UPL_TPI_GPU_R1_IMPLEMENTATION` 前缀仅新增一个 host-only 声明块，以唯一的 `// P2_HOST_API_R1_BEGIN` / `// P2_HOST_API_R1_END` 包围，内部 `#ifndef __CUDACC__`。移除这个块后，其余 prefix 字节应与原文件完全一致；作者已作纯字节自查，不冒充 NVCC 编译或执行结果。

新的资产供根后续 overlay 成原 `upl_tpi_gpu_r1.h` 文件名，不能混用旧三阶段 M0 header；它需要 math agent 的 P2 四阶段 `upl_tpi_m0_dt_r2` 实现保留原 namespace/API。公开 src、旧私有树、CUDA `.cu/.cuh`、旧对象和 class ABI 均未修改。原 CUDA-visible tokens 不变时可由根审计后采用旧 CUDA objects；作者不自行宣布整个链接闭包通过。

`UPL_TPI_GPU_R1` absent/A 最先返回 OFF，不解析新 selector、不分配 firstRows、不开侧车、不新增 force。此候选只允许 B 且 `UPL_TPI_P2_ROWS_R1=2`；选择器在原 Scheme 静态初始化内检查，避免每次 Enabled 反复读取环境。C、B 缺新 selector 或其他值拒绝，不静默落回 P1。Init 另要求原 M0 policy 和 dt=tD/1000（10us）。alpha=.5、beta=0，原 source clock 外载/排水保持；默认 A 真实回归仍待根独立准入。

## 新 host API 和必须的 outer 次序

原 API 保持签名，新增三项：

```cpp
void ValidateFirstEndpoint(const void* owner, View v, bool drain, unsigned loadmode);
void SecondEndpoint(const void* owner, View v, double time,
  unsigned long long step, double dt, const JSphHourglassGpu* hg);
unsigned EndpointPhase();
```

`EndpointPhase()` 仅在实际 endpoint active 且 round=1/2 时可调用，分别返回四阶段 writer 的 phase2/3。outer `DtVariable` 应使用 `final?1:(EndpointActive()?EndpointPhase():0)`；不能继续把两个 endpoint 都标 phase2。原 predictor/corrector、sigma/kappa/J/position 和 HG history 更新仍各一次。

根后续在原 full-geometry endpoint 位置接入以下流程（这里只描述，不改 outer）：

1. 原 `StartEndpoint → Interaction_Forces(SymCorrector) → DtVariable(false) → PrepareFinal → PosInteraction_Forces → WriteFinal → 原 ApplyPorePressureBoundaries`。
2. `ValidateFirstEndpoint`：先观察既有 error，再 Map/原 `ValidateCommitDevice`/Check，逐 native soil 验真实 p1 是首 raw 或真排水 +0，同时核 P0/Jfull。**不调用 CommitDevice、不改 previous、不推进 commits**。验证后同步 D2D 复制整个 1040-slot Observation 到 firstRows；其中 finalP 仍是旧 accepted final，不将其改名为 p1。任何错误先抛出，不能被下一次 Reset/Map 掩盖。
3. `SecondEndpoint`：只允许刚验证的首轮，prepared 从 true 清为 false；原 pending/source time/step 和 history 保持。它内部调用原 `StartEndpoint`，所以 outer 不要再重复一次。原 Snapshot/Core/HG snapshot 在实际 BC 后的 p1 上重新抓取并重置 seen，然后再次真实 Interaction/DtVariable/Prepare/Pos/Write/实际 BC。
4. 原签名 `Commit` 现在只允许 round2 完成、两轮计数匹配时执行。它用原 ValidateCommitDevice 再核最终真实 BC/P0/J，最后仅一次 CommitDevice，previous=本步实际 pn，finalP=p2，commits/lastEnd 前进一步。outer 再按原方式推进 scalar TimeStep/Nstep。

每轮 StartEndpoint 清除 `roundWritten`；WriteFinal 必须 pending、该轮 active/prepared 且尚未写回，并核先前累计写数。只有真实 WriteDevice/Check 成功后才置 written 并增加 `endpointWrites`。首验证和第二轮入口要求累计 `2*commits+1`；最终 Commit 要求 `2*(commits+1)`。因此 prepared 后 Abort、未真正写回的零残差路径不能被后续 BC 验证当作完成，也不能重复写同一轮。该修复只补 host 事务门，不改变 CUDA 操作或32列侧车。

每轮有自己的真实 Pre/Pos scratch 生命周期；不重用第一轮 Ace/Rsigma/R，不增加 RunCellDivide，不把第一轮未舍入 double 输入第二轮。第二次原 Snapshot 记录实际 p1；在保存时另逐 ID 核 second q 与首轮经过真实 Validate 的 raw/+0 规则位一致。source pn/previous/prediction/half/Jn/Jhalf/Jfull/thetaHalf 也逐字段位核，首轮/次轮 drainage masks 独立保留，不先假设它们相等。

任何失败后都不轮转 pressure history，不自动 retry/rollback/restart；机械状态已完成或 p1 已临时写入时，不承诺回滚。AbortEndpoint 只清自身 descriptor，保留失败状态供真实终态处理。所有 owner API 使用同一个 JSphGpu 基类 owner pointer。

## HG、内存和计数

首轮和次轮都复用原 AddReadonlyHG，保持实际 full-J 惯性缩放、原 double add/float-store 顺序、slots/partial reduction 和有限性检查。各轮独立捕获并位核原 Stats24、RateInfo15、device HG history/rate D2D snapshots；不额外执行 HG 的 force/history/rate 更新或材料返回。

新增的唯一物理行 device allocation 是 host State 的 `firstRows[1040]`，不加入 DeviceState。通过原 Take/allocations 清理链管理，在 base destructor 的 cudaDeviceReset 前由幂等 noexcept FreeOwner 释放；不读取可能已由 derived destructor 删除的 HG 对象。static State 析构只删除 host streams，无 CUDA 调用。

Init 在实际 Initialize/Check 后作一次 D2D 初态 Observation 拷贝，计 `initial_first_row_D2D_copies=1`，仅为初态输出；它不算 endpoint 观察。每个成功步首验证后再一份 D2D，计 first_row_D2D_copies=N。新增 row 数据不在求解循环逐 ID D2H；只有 Saved 时 bulk D2H 首轮1040和次轮1000记录。原小 error packet/HG reduction 的既有读回不改。

N 成功步必须满足：pre/cor/J/pressure commits=N，endpoint_calls=endpoint_writes=2N，first_validations=first_row_D2D_copies=second_transitions=N，core checks=14000N、HG readonly snapshot checks=4000N。Finish 强制实际成功写数并以 `endpoint_writes` 单独保存到 summary。原物理 HG 仍 force/rate2N、predictor/corrector updates N、原 cache/stiffness/spin 门不变；四 force audit 和六现场量没有伪装为旧三阶段成功。全部大计数用 unsigned long long。

## 独立双轮输出和观测局限

新 policy/summary stage 为 `upl_tpi_p2_gpu_r1`，新文件 `UplTpiP2GpuR1.policy.json`、`.summary.json`、`.round1.csv`、`.round2.csv`；不使用旧 one-round P1 的文件名让旧 reviewer 静默通过。两个 CSV 每 native save 各1000行，共32列，前28个字段保持旧含义，只有 final 列明确命名 `final_field_float_Pa`，末尾新增：

`round, has_endpoint_observation, final_field_is_previous_step, validated_BC_value_float_Pa`。

- 初态两文件都来自真实 Initialize 记录，`has_endpoint_observation=0`，不声称有已执行端点。
- 非初态 round1 的 final 字段保持真实旧 committed final，`final_field_is_previous_step=1`，可能因本步 drainage source 投影而与 pn_used 不同。首轮 BC 值由已成功真实 device Validate 的 `commitDrained?+0:raw` 规则表达，metadata 明确不是额外 native 保存态；不从 stale finalP 伪造 p1。
- round2 的 q 是实际第二 force 输入，final 字段是唯一 CommitDevice 抓取的实际 p2；其 BC 值是这个实际 final。两轮 q/S/Rgamma/theta/raw/三个 J/源 history 和独立 masks 原样保留，不能用最终结果倒造第一轮记录。

Observation 没有 lap 或 legacy rate，View 也没有其指针；本范围不扩 device structs/API。因此 **没有额外观测 first lap/first legacy rate**，不由 float rate 或 Rgamma 反推 double lap。原 native PorePressRate 是第二轮输入 q2=p1 上最后真实计算的 Kw/n 缩放 residual，不是 p2 上未算的 rate，也不是实际 dp/dt；本侧车不宣称完整非 dyadic rate bit oracle。

两个 CSV 的 header/count 和真实 source/save clock 独立保留，第一轮不是另一个完成时间步。这个新协议需要根后续独立 native/two-round/four-phase reviewer，旧 P1 成功不能自动认证。尚无新 GPU fixture、memcheck、Debug/Release 或物理运行；scalar、host 结构或正常退出均不证明两轮会改善顶部沉降，也不自动准入完整2Tv、公共XML、负压正则化或 C08。
