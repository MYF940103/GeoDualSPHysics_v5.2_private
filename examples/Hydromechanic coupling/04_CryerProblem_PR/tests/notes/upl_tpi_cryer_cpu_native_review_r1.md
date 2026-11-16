# C04 CPU 128 步：独立唯一 native 与离线侧车审查作者稿

尚未执行，只新增同名 support Python 和本文。使用已经真实成功读取原
C04 CPU128 的 `upl_cryer_public_native_DebugCPU_r1/reader.exe`，不创建
新的 reader/compiler/linker。没有 solver、VTK、half、峰窗、PRE 或后续
计算自动接续，也不运行 Git/SHA。

两阶段分别 root 准入：

- `--phase native`：至多一次旧 reader 读取当前新 job 的两个 native 帧，
  输出 `tests/outputs/<tag>_native_r1/` 和 `logs/<tag>.native_r1.json`。
- `--phase review`：只消费已有成功唯一解码，写
  `logs/<tag>.native_review_r1.json`，不再调用 reader。

tag 只允许 `upl_tpi_cryer_cpu_DebugCPU_[A|B|C]_startup128_rN`。
admission 的 stage 分别为
`upl_tpi_cryer_cpu_native_review_r1.native_admission` 或
`upl_tpi_cryer_cpu_native_review_r1.review_admission`，`passed=true`，
同一精确 tag；native 需 `one_native_read_only=true`，review 需
`offline_only=true`。全部实际消费 inputs 以 path/bytes/mtime_ns 绑定。
B/C review 还需 `reference_A_review` 指向真实已通过的新 A review。

已有 native 目录/读取器 call/log/完成或部分输出时，不重新解码。先检查
该 reader 的活动 argv 是否已指向当前 data 或新 native 输出；有则拒绝。
已有成功解码仅进入独立 review，失败/部分解码保留并诊断，不自动重跑。
任何新 receipt 已存在即拒绝，不覆盖或另换标签。

## 运行身份及原生门

消费真实新 job 的 run/start/call，核其 owned child PID/creation/exe/
argv/parent、原始 Popen/Win32 出口均 0，以及实际 A/B/C 环境变量。
明确采用新的 build_review_r2 passed，同时保留原 build false，不追认
旧 build 成功。绑定真正运行 exe 新副本、其原程序来源和必要 runtime；
不重复扫描旧源树或 BI4 SHA。

该 job 必为 fresh DebugCPU、完整 37181 IDs（8 fixed＋37173 soil）、
实际 dt=2^-20、128 updates、2 保存帧。只接受原 5 列时钟：初始 Step0
和 completed128/savedStep127/actual t=2^-13。时钟用 scalar +=dt 重建，
不改原 saved metadata。原始 native 文件、Run.out/Run.csv、计划全部绑定。

旧 reader 原样执行：22 typed arrays、全 IDs、XYZ几何/有限/弹性/无排除、
P0/float excess、fixed marker、同 J 的 n/V/rho/k ledger、原 radius .0525、
FS、signed dterror<=1e-14及非初始 interval 非空。该窗口 t<drain，
post-open 帧和真实 drained receiver 检查数必须是 0，明确不把零检查数
叫作排水后验收。实际来源/solver退出由根 wrapper 核，不由 reader 自证。

原 reader 会输出 common26、真实 clock（含 signed dterror）、完整材料
身份、summary/center18 CSV；它验证全部22 typed arrays，但没有输出每个
raw22数组用于逐字节比较。本稿始终保留这一区分。

## A 与 B/C 的实际检查

A 没有 private policy/csv/summary，应与原 CPU128 的 common26、clock
和 native_ids.csv 原字节一致，包括原 signed 初始/非初始值。不得忽略
FSNormal或 signed 字段。原控制只有真实 solver call/native call，不
存在可追认的独立 old run/start。本门不冒称全部 raw22 bit identity。

B/C 的实际 policy 必须是 α=.5/0、β=0、M0、正确 37181/37173 数量、
ID-owned cold history；summary 必须有128 commits/endpoint calls、
33307008 个原7 committed-soil-field bit checks、HG checks0和真实终点。

逐一审查两帧共74346个真实 soil-ID 侧车行：initial和completed128，
source_step=127、真实 source/save clock、cold initial、source/endpoint/
commit drained 全0、policy对应的 prediction、实际 half/endpoint guess、
S>0、double `q+Rγ/S` 后的原 float raw/final write、原 Jfull corrector
算序及其与保存 common26 的 J/p 对应。C 的 prediction 不使用历史；
β或额外 relaxation 不在此稿内。原 Jcorrector 检查使用
`Jn + ((dt*Jhalf)*thetaHalf)`，不把 endpoint theta 当 J 积分源。

所有128步的执行次数由真实生命周期summary检查；只有真实保存的两帧
有逐材料侧车，不声称已经导出或独立重算每一步的所有 Rγ 行。
leading-LP 的 S 不是完整 Jacobian；旧 PorePressRate 仍是原 finite-Kw
legacy residual，不把它当作 M0 dp/dt。

B/C 对实际已通过的新 A 仅报告末态 pressure RMS 和固定材料 XYZ位移
差，属于跨模型描述，不能套 5Pa half gate、等价或精度优劣结论。
此窗口在启动 ramp 内，尚未排水、无 Mandel峰窗或完整理论精度验收。
所有原始输出/源/程序/旧失败及暂停 C08 owner/GPU 保持原状。
