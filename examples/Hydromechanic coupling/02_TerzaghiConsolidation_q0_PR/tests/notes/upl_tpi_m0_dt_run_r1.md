# 单项 M0 时步资格运行器（作者稿）

只新增同名support脚本和本文，不执行构建/求解/读取。
四个互斥模式：一次Release A约2ms原dt控制；一次GPU Debug B两步memcheck；
CPU Debug B约2ms；另行准入的一次GPU Release B约2s大步长窗。
不自动启动后继、half、C、细步reference、完整2Tv、解码或VTK。
根线程每次完整读审后，用独立run_admission显式选一个job。

新B固定dt=tD/1000；只有window2s在之后独立审查准入时可选tD/500。
tD=.010000228881835938s保持原物理值；全XML只改私有拷贝的DtIni/DtFixed/TimeMax三项。
BI4及法向文件由原初态复制到独立seed目录，同basename；不运行GenCase、不重启PART。
正式输入和旧seed都不改。A沿用原dt和CLI .002上限；B私有XML TimeMax=2。

输出目标沿用旧特殊cadence；真实时间逐步binary64 +=dt生成plan，保存Step=completed-1。
10us窗nominal2s因TimeMax先于nsteps上限结束：199996updates，
actualend2.00000577545594s，1263帧，1000为preopen，1159post帧/11590真排水接收检查待native。
20us为99998updates/actual2.0000057754538254/1238帧/1146post；不能把上限200000/100000冒作实际步数。
每个独立启动前仅写自己的plan，不改原计划/数据，不插值重写时钟。

程序只接受真实passed新build与root列出的已通过前置；原source/build identity以stat核对，
具体限定新stage=`upl_tpi_m0_dt_build_r2`及对应CPU/GPU `upl_tpi_m0_dt_r2.prepare`，
不能用旧同configuration程序冒作新默认回归。生成seed三文件和plan在启动前、终态各核stat。
不重复旧源码/对象/BI4 SHA。GPU直接复用既有真实原生句柄owner流程；CPU同义。
真实child creation/exe/argv/parent、Popen/Win32出口、最后原始console与首因封存。
只允许root精确列出的原paused GPU保持stopped；绝不恢复/停止/替换旧任务。
新M0环境在调用时显式设EQ40_RH1，A清除此变量；原runner生成的start.actual_environment仅记原scheme，
本run.policy_environment和实际M0 typed policy/CSV/summary共同证明所用新策略，不能只看启动文本。

必要门：实际steps/frames/1040/无排除/原HG calls-cache-dt/tau<=.2/spin<.01，
实际GPU Hardware/RunMode和B独立16-case device fixture恰一次（A零次），CPU单core原模式，
B真实三phase时步计数及max(dt-bound)<=1e-14；A不得创建M0 sidecars。
R2删除了基类不可访问派生HG对象的额外诊断读取，HG_limit_reference_available必须false；
该列DBL_MAX只作不可观测sentinel，HG实际安全仍由原derived积分器及摘要独立检查。
signed dterror含初态、22typed/IDs/P0/J/ledger/排水、每interval和物理图仍待独立native/离线审查。
正常exit不等于完整物理验收，选择大步长需比较精度和实际成本。

admission stage=``upl_tpi_m0_dt_run_r1.run_admission``，passed/one_job_only=true。
job含mode/configuration/scheme/tag/build、可选event_divisor及Debug memcheck_program；
inputs列实际消费脚本/note/共享runner/Python/psutil/seed/build/program/runtime和required_passed_checks。
已有任何该tag结果、call、partial、seed即拒绝，不覆盖/重跑。

仅window2s可由独立`--notify-admission`启用同一个directowner终态一次通知，不加watcher。
使用原C08实际成功的codex queue接口，绑定当前root ID及真实已通过attempt/result/program stat；
不运行连通性测试、不重复hash。先封存run/status/terminal，写attempt，再仅调用一次45秒queue。
超时可能已投递，所有结果均不重发或重新布防。通知不会启动求解/读取/后续任务。
若root runadmission.notification_required=true而没有独立通知准入则拒绝启动。
