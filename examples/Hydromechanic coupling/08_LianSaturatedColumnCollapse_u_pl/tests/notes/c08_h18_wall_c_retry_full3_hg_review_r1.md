# C08 candidate full301：own-prefix4 与 HG 阶段离线审查

本阶段仅作者化 `support/c08_h18_wall_c_retry_full3_hg_review_r1.py` 与本文，未导入或执行新脚本。脚本不调用reader、BI4解码、solver、GPU、构建、VTK、Git、SHA或通知；导入只定义函数/常量。根线程全读并单独建立离线准入后，只能运行一次fresh审查。

固定目标是正常完成的 `c08_h18_wall_c_retry_full3_GPU_r2`（301帧/global2600000），其 own短控为相同candidate程序的 `c08_h18_wall_c_retry_prefix4_GPU_r1`（4帧/global2006001）。原 `hg_opt_full3_GPU_r1` 与host replay的failed99保持失败，本脚本不消费、改名或覆写其数据。

## 唯一原生读取和快照身份

完整301 native已经由根线程独立读取一次。脚本只消费 `logs/c08_h18_wall_c_retry_full3_GPU_r2.native_r1.check.json`、实际原call、completion/metadata，以及后续 `native_r1.exports.json`。后者明确是根在reader完成后建立的stat快照，不能倒称为原reader历史seal。验证已存在的22数组、6805 IDs、原全部native安全门通过，不重新读BI4、不重新生成导出。

根准入为 `logs/c08_h18_wall_c_retry_full3_hg_review_r1.root_admission.json`，至少包含 `authorized=true`、`offline_only=true`、当前root_thread_id，及精确stat绑定 `execution_script`、`note`、`run`、`native_check`、`own_prefix_check`、`native_exports`。必要的小型源/收据、typed导出及HG sidecar只stat；不递归扫描旧依赖或原BI4。完整HG政策/CSV的当前stat明确是本离线阶段首次观察，不伪造早先封存时间。

## 原301/4头与真正首4 payload

保留两个原始12字节头 `[6805,22,301]` 和 `[6805,22,4]`，要求各自原长度，不把帧数改成相同。每个实际记录包含8字节native time，再包含6805粒子×212字节的全部22数组，因此record=1442668字节。首4完整记录逐字节比较，包含初个真实post-release样本、实际时间payload和所有数组；不掩盖初始/非初始字段，不重写header、Step或stage。

原layout CSV逐字节相同，clock CSV首4全部原始行连同header逐字节相同，signed dterror没有例外。完整301 clock逐行核原计划、Step/completed、scalar `+=5us`时钟、22导出实际time payload及每条非空signed interval的原 `<=1e-14` 门，不用 `n*dt` 或绝对值替代。此比较是同程序同dt的own-prefix，不是half误差、旧HG0对照或完整物理精度。

## HG60 的602真实阶段行

从实际优化HG build绑定的冻结CUDA source提取原60列表头，并核能量账本、adjoint与memory swap原源码锚点。完整/短控schema2政策必须一致且仍为 `PrivateC08SingleProducerOptPlasticHG`、ReleaseOnly/xi.1、单producer、cold-zero HG、未宣称独立旧material返回或coupled passivity。HG header及首8实际数据行必须逐字节对own-prefix4。

602行按每个原实际保存时刻的Pre/Cor成对审查；最后pre_calls、cor_calls、commits各为600000。保留原N5000材料状态计数、输入13×5000=65000与commit7×5000=35000的cache coherence门，以及全部rank、dt/0.2、gamma、spin、graph、有限与正能量域门。Pre和Cor从同一committed e出发，要求每对Eold位相同，不能把两次trial相加当连续accepted功。

沿旧 `c08_h18_hg_cached_phase_review_r1.py` 的原方法，用独立fsum核 `Enew-Eold+node_work+loading_loss+Edead` 与源码ledger的标量算术余量，并核node-row work的adjoint差。保留冷初态、accepted born/dead、discarded energy、累计旋转历史的原整数/单调约束。不新增half、不改变任何预算，也不把old material root ratio、局部负loading_loss或聚合预算比>1升级成原不存在的新0门。保留其原有描述性计数、undefined比率与极值，报告不隐藏。

`loading_loss` 是现有HG loading projection观察，rotation单列。60列未捕获NoPen投影的独立反力功，不能补造其能量门；NoPenReactionClosed仍false。cache输入/写回位检查只证明一个producer与consumer一致，不是独立旧材料solve。内部每步guard由原程序控制流与完成收据提供证据；602稀疏保存行不是1200000个force stage逐行导出，也不是外包误差界或完整耦合能量证明。

## fresh输出与结论范围

只生成新 `logs/<tag>.check.json`、`figures/<tag>_phases.csv`、`_extrema.csv`、`_history.png`。CSV含全部602原阶段量及派生诊断、分阶段极值；PNG保留有符号work/loss/rotation，展示dt/spin/gamma/cache相关历史，不拟合、不平滑、不裁掉启动。任何已存在结果都保护；失败写新失败收据并保留部分派生，不能重跑solver/reader。根线程还须实际查看PNG/CSV完成视觉审查。

实现/原生审查通过仍不自动接受论文精度、塌陷形态、另两组ψ、同阶段Darcy反力闭合、exact HG restart或完整物理结果。原PRE、程序、BI4、所有失败与正式结果保持原样。
