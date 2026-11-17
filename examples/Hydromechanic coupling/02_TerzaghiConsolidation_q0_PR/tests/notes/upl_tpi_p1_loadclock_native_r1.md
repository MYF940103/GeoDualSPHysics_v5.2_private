# P1 staged-load 原生 reuse / review r1

作者稿；不执行、不构建 reader。唯一新增 `tests/support/upl_tpi_p1_loadclock_native_r1.py`，仅有独立 `read` / `review` actions。

## 原读取器与科学门保持

直接调用已实际通过的 `upl_tpi_m0_dt_native_r1.py` 的 `read_native`，使用原 `outputs/upl_tpi_m0_dt_native_r1_build/upl_tpi_m0_dt_native_r1.exe` 和其完整四 profiles。不复制、不重编原 C++，不改变 22 数组/1040 IDs、ledger、真实 clock/Step/dt、signed dterror、排水、geometry、P0/J/native 类型谓词。

绑定实际原 build/program/runtime 和 `logs/upl_tpi_m0_dt_native_identity_root_r1.review.json`，核对实际 build stage、路径、三字段程序 stat、原真实工具 calls；没有重新 SHA sweep。旧 completion 的 stage/backend/profile 仍是原 reader 协议，不能把这个标签当新 loadclock 源码或新物理实现证明。

新外层 get_job 逐项绑定真正的新 run stage、原 start/call、真实 tool/target 出口和创建/argv/parent、新 host-only build/preparation/program/runtime、复用输入/plan 与原 reference。不得将旧 M0 run/build receipt 改名；新 root job.build 的额外哈希字段允许存在，但以三字段 stat 正确比较，避免 dict schema 附加字段导致误判。

新 review 直接复用原 `intervals`、`sidecar_cpu` / `sidecar_gpu`、`hg_run`，Release B 复用真实原 CUDA object/PTX 绑定。压力 double/float FTZ、J 的原 CPU/GPU 算式、HG 位检与 signed interval 全部原样；`PorePressRate` 仍是旧缩放 residual 诊断，不是实际 dp/dt。

支持的真实 profiles：CPU Debug B 200/18，GPU Debug B 2/2，GPU Release A 320/18，以及随后唯一 B10us 2s 199996/1263。它们与原 C++ 参数字面完全吻合。B .15 不在该工具的 profiles 中，不伪装成 2s profile。

## 独立新 loadclock 记录

`UplTpiP1LoadClockR1.policy.json/.csv/.summary.json` 在 B 必须存在，在 A 必须全 absent。policy 明确 F0/F1/F2 的外载求值比例 `[0,.5,1]`，global clock、Dirichlet、原 P1 pressure/HG/J 顺序和 native schema 没有变化。

CSV 精确 44 列、每真实保存帧一行。全部帧审查，不用 zip 吞尾。基于 scalar `clock[n-1]` 独立重放 old/half/endpoint 求值时刻和原 double ramp 运算，逐 bit 比较 last time/q、各区间 min/max，以及每阶段一 direct/一 raw 的实际计数。初态 min/max 为原显式 ±DBL_MAX sentinel；不混入物理统计。CPU 无配置求值，GPU 初始 ConstantDataUp 有一次 t0 非 force 求值，分别要求 cold count=0/1，且 CSV/summary 一致。

三 force 和六 phase/site interval 与 cumulative counts、全部 native actual time/Step/dt、最后 source time、summary update/end 都严格核对。该记录证明实际 host 求值时层，不证明新的时间方案稳定或达到理论精度。

A 对照使用真正已 passed 的 `upl_tpi_m0_dt_Acontrol_GPU_r1_native_m0_r1`：两份独立 18 帧 header 保持，全部 18 条实际记录，包括 forced-final 320，在五份 original15/physical/J-theta/n/clock 导出中逐字节比较。signed clock 包含在内；不误用旧 344 帧控制只有 17 个共有状态的比较，也不称此为全 22 原始数组 bit 证明。

## 入口和新输出

入口为 `...python.exe -B tests/support/upl_tpi_p1_loadclock_native_r1.py read|review --admission PATH --execution-authorized`。admission stage 分别是 `upl_tpi_p1_loadclock_native_r1.read_admission` / `.review_admission`，`passed=true, action_only=true, job={tag}`；每项须根分别审阅准入，禁止自动串联。

`inputs` 按实际消费 stat 绑定新脚本/note/runner/note、原 M0 Python/CPP/note/shared helper、真实新 run 链和 source/header/runtime、原 reader identity/build/program/runtime/工具 calls、原 seed/plan/reference，以及该 action 实际读取的 sidecars/native 产品/旧 A18 对照。read 需要实际 psutil 模块。review 需要原 PTX proof/call/log/object 的 stat（Release B）和 reader call/completion/产品。不要求重复 hash 原输出。

新导出目录为 `outputs/<tag>_native_loadclock_r1`；新 read/review 收据分别为 `logs/<tag>.native_loadclock_r1.json` / `.native_review_loadclock_r1.json`，外层 stage 明确为本适配器。真正 reader 的 call/log 沿用 body 自身 `<tag>.native_m0_r1.call.json/.log` 名称和原 completion stage，说明原实现复用而非假造新工具。所有既有或 partial 路径拒绝覆盖；真实 reader/数据目录无活动读取才可至多一次读取。

review 仅使用已有唯一 read 的产品，不重解码。成功是实现/native/新 sidecar 资格，不是新 reference、5Pa half、理论或完整周期物理验收。没有 build/solver/VTK/Git/下一阶段/queue 调用。
