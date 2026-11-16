# C02 TPI B 完整 2Tv 离线科学审查作者稿

新增 `support/upl_tpi_gpu_full2tv_review_r1.py` 和本说明。作者没有执行脚本、分析数据、
解码、构建、求解、哈希或 Git；不操作任何活动进程及冻结依赖。

本稿只在 `upl_tpi_gpu_Release_B_full2tv_r1.native_review_full_r1.json` 实际 passed 后，
由根完整阅读并给出唯一离线准入才可执行。原 native/read/review 各自证据继续保留。
正常求解退出、native 成功或本科学脚本成功均不自动代表物理、公共源码或正式发行验收。

## 来源与输出

- 新 B 为原单一 GPU full2tv，1682 保存状态、1040 原生 IDs，其中1000 soil/40 fixed，
  22 typed arrays，11661219 更新，dt=6.250143051147461e-6 s，实际末时刻
  72.88428689946836 s。事件 completed1600/part117 仍 preopen，之后1564帧/15640排水检查。
- A 仅复用已经完成的 CPU1/FreeSlip 有限 Kw full 原生导出与成功的原生/描述性审查，
  不重跑、不重解码、不调用旧分析，不把其旧100Pa超限当作物理通过。
- B 原审查已实测343个真实同dt短窗共享记录，包含5个完整二进制 record 和 signed clock。
  本稿只继承该 passed 事实，不重做证明，不冒称所有22 raw arrays逐字节相同。
- 旧 u-pw 仅用已有 `upl_full_upw_compare_r1.check.json` 及其两个轻量CSV。
  历史7290帧和10个100层孔压剖面保留各自实际时间，无新旧 native 读取。
  旧 u-pw 是 GPU/Vel0、legacy density、dt1e-5/tD.01；A为CPU1/FreeSlip，
  B为GPU/FreeSlip且M0，不能作隔离算法或后端速度归因。

所有新产品在 `tests/figures/upl_tpi_gpu_full2tv_review_r1.*`，不覆盖根正式图表：

1. `history.csv`：A/B所有1682实际时刻的孔压/固定材料顶部和底部沉降、J/n/实际rho、
   六分量有效与总应力、Q、速度、全100层交替X模态汇总及各自适用参照。
   匹配图中旧u-pw背景曲线的7290个源点也以明确context标签保存，其他量为空而非伪造。
2. `layers.csv`：只新增B全部168200行100层历史，含压力范围、沉降、J/n/实际rho、
   六有效/总应力层均值以及各自六分量交替模态。A同类历史已保留，避免再次复制大CSV。
   A热图直接消费已保留 `upl_bigstep_full_r1.layers.csv`，逐行核真实part/time/材料层及原定义，
   作为该热图匹配CSV；B热图匹配本轮layers.csv。两者不借图像推断完整原生字段逐bit一致。
3. `profiles.csv` 与 `profile_times.csv`：10个指定legacy Tv附近实际最近保存状态，
   A/B各100层、实际时间/Step、目标误差、各自理论和旧u-pw实际时间差。
4. `cross.csv`：每个真实共同保存时刻的A/B差，明确跨物理模型/后端，非half或5Pa等价门。
5. `noninferiority.csv`：10个目标的每条原计划预算、数值和通过/失败，不隐藏失败项。
6. `metrics.json`、`history.png`、`profiles.png`、`settlement_profiles.png`、`modes.png`。
   全启动状态保留，不平滑、不裁掉负压/波动、不移动起点、不拟合H/时间/荷载。A/B同类模态热图使用共同的对称色标范围，避免独立自动缩放掩盖幅值差；原始值和CSV不变。

读取器已经验证了真实scalar +=dt和全部22原生门；本稿用其实际clock/Step/plan互核，
不再重复11M步时钟重放，更不把n*dt或Run.csv圆整PhysicalTime当时钟。
原1681个非空signed dterror仍按 <=1e-14检查，不绝对值化、删初态或改符号。
实际rho从各自已经通过的ledger单次顺序读取并以ID/time/J/n绑定，不把由J计算值冒作原生输出。

## 应力、参考与时刻

保存六分量 `sigma` 是骨架有效应力 `sigma'`。总应力为 `sigma=sigma'-pI`，
只在三个对角减p，剪切不变；代码和CSV分别命名。Q保留原定义：100材料层平均
总sigma_zz的98个二阶差分RMS。交替X模态是每层去均值后乘原X列的正负交替投影，
不是Q，也不是只看顶部或某个极端粒子。

主参照直接复用原startup science_r2与bigstep full中的未拟合H=1级数定义：
E=2e6 Pa、nu=.3、n0=.3、Kw=2e8 Pa、k=1e-4 m/s、q0=10000 Pa，参考g=9.81，
512模态。M=E(1-nu)/[(1+nu)(1-2nu)]、Cv=kM/(rho_w*g)。
A容量Bf=1/(1+n0*M/Kw)，其压力幅值和Cv都乘Bf；TPI B按M0参照。
材料沉降参照在原z0=.995/.005评估，非表面/底面；S∞预算分母仍为q0*H/M。
它们是闭载后单顶排水的准静态伴随，不是有限ramp/核带外载/惯性/J-n演化的启动精确解。
无H=.995拟合或任何选择使模拟更接近的参考变更。

原benchmark保存与声明Tv沿用legacy M0-Cv口径，目标为
.005/.05/.1/.25/.4/.5/.7/1/1.5/2；使用实际最近保存时刻，输出时间与Tv误差。
同时报告每个模型适用的Cv*实际tau/H²；oldA末态legacy Tv约2，但有限Kw适用Tv约1.99196，
不能称它覆盖有限Kw Tv=2。本稿保留该覆盖限制并报告同数字适用Tv目标是否在保存范围内，
不额外插值、外推或启动A参考计算。A/B误差都在各自正确参照的实际保存时刻求取。

## 原门与预先固定的非劣预算

从 `validation/upl_tpi_three_scheme_plan_r1.md` 原样采用：

- 每个 t>=.1-1e-7 保存状态：100材料层总竖向应力最大误差 <=100Pa，顶部两层gap<=100Pa。
  A所有原超限单独列出；A失败不豁免B，也不抬高至110.6Pa。
- 每个声明Tv：主孔压误差为100层材料均值剖面RMS，除q0；B误差增量<=.10个百分点。
  声明Tv>=1另外要求B压力RMS误差<=A+5Pa。全部原生点RMS/最大误差/极值和列模态仍另报。
- 顶部绝对沉降误差/S∞：B<=A+.10个百分点。底部用绝对误差<=.005mm，且<=A+.002mm。
  不用接近零分母夸大百分比。此5μm是指定参照时刻的物理误差预算，不是全启动动态真解门。
- Q与全部交替X模态保留原诊断，无事后新增阈值、half链或跨模型5Pa门。

科学check.passed仅表示B上述原100Pa门和10个非劣预算均满足；无论其结果如何，
`physical_acceptance=false`，根仍须查看图、误差/局限及是否有共同空间误差，独立作最终决定。
长期衰减按legacy Tv>=1全部保存状态报告均值增量、首末压力、晚期RMS等，
不从正常退出推断无平台或严格无模态增长。PorePressRate保留为legacy scaled endpoint residual，
不被当作M0实际dp/dt。观测TSimul/TTotal/steps/s明确包含非隔离、侧车及不同后端影响。

## 唯一执行准入

根JSON须 `stage=upl_tpi_gpu_full2tv_review_r1.admission,passed=true,offline_only=true`，
`inputs`提供所有实际消费文件的path/bytes/mtime_ns：本脚本/note、XML、原计划与三个定义源，
B full原生review/read/完整导出叶中实际消费部分/plan/Run.csv，A原生review/read/run/
completion/physical/soil_n/clock/IDs/columns/history/ledger/plan/Run.csv，以及旧u-pw check和两个CSV。
另需保留A既有 `tests/figures/upl_bigstep_full_r1.layers.csv`，不重写/另存一份A大层表。
所有读入逐一stat绑定，结尾核消费stat未变；不扫SHA，不读取旧原始BI4/对象/源码树。

命令仅在根完整读稿后使用：

`python -B tests/support/upl_tpi_gpu_full2tv_review_r1.py --execution-authorized --admission ROOT_JSON`

输出/收据/partial任一存在即拒绝，失败保留首因与所有派生partial，不自动重跑分析、读取或求解。
日志收据为 `tests/logs/upl_tpi_gpu_full2tv_review_r1.check.json`，没有任何自动后续动作。

## 根线程预审记录

2026-11-17：根线程已完整阅读作者及说明，独立peer核对原科学定义、实际A轻量元数据和原计划预算，未发现执行阻断。根只将未来A/B同类模态热图改为共同对称色标，未改数值或预算。代码尚未执行；完整B仍在计算，原生/物理结果均待验收。此记录用于避免对未变作者反复全文重审，最终执行仍须绑定实际完成收据及输入身份。
