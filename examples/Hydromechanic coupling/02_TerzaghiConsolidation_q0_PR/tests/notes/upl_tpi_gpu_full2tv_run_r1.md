# C02 GPU唯一fresh B完整2Tv runner作者稿

新增`support/upl_tpi_gpu_full2tv_run_r1.py`与本说明，尚未执行。
仅tag=`upl_tpi_gpu_Release_B_full2tv_r1`、Release/B/full2tv，fresh pressure-history cold0。
没有新A/C、half、reference、GenCase、PART restart、自动解码/VTK/Git/下一solver。
旧A完整控制及所有旧owner/source/program/output保持原样。

## 必要前置

实际passed window-only source269和one-host Release构建，只有一处TimeMax guard扩展。
需要精确`upl_tpi_gpu_full2tv_r1.prepare.json`与
`upl_tpi_gpu_full2tv_Release_r1.build.json`，实际1CL+1link/111objects/retain110/noCUDA。
程序source/runtime只核必要stat，不重新hash；原h/cuh/kernel/物理不变。
B原GPU .15 native_review_r5必须passed，实际science_r2 B两项post-.1s100Pa门通过。
现有science整体因A已知105.3948Pa状态false不被隐藏，也不伪称整体通过；只准入已通过B。
root还须显式列required_passed_checks，不能把exit0当作独立物理准入。

## 复用原A完整时钟与seed

读取保留`upl_bigstep_2tv_CPU1_r1.run.json`和135463B原
`logs/upl_bigstep_full_r1.clock.csv`。逐行核8列与原run.saved_clock_table一致，
按原字节复制为新唯一tag.clock.csv，不重新积分11M次、不n*dt或重排格式/改写时钟。
同一seed XML/BI4/NBI4、dt6.250143051147461e-6、XML TimeMax72.88428690075874。
仅`-gpu -stable -mdbc_freeslip SEED OUT -dirdataout data -svres -nsteps:11661219`，
不提供float CLI-tmax覆盖。实际原scalar endpoint72.88428689946836，1682帧。
第117帧completed1600仍preopen，118帧1601；1564 post帧/15640真排水检查待native。
保存末态在step cap触发，原last target73.05247434779575，forced_final1保持原样。

## 真所有权和唯一完成

复用已实际通过的gpu_run_r3.run_owned，不复制/修改该流程：真实directGPU child、
Popen及Win32原生句柄出口、creation/exe/argv/parent、实际环境UPL_TPI_GPU_R1=B。
先检查活动求解器；只允许root精确pid/creation/exe/argv认证且仍stopped的旧GPU，
不停止/恢复/改旧任务。任何其它活动GPU拒绝，本runner不启动duplicate。
单一owner只负责这一个求解，末态封存同tag start/tool.start/call/run/status/log/plan，
输出一个terminal JSON。若wrapper/check失败，保留真实handle出口与最后原始console
PART/首因，不推断未保存native时间；已有路径/partial即拒绝，不换名重试。

可选--notify及独立--notify-admission把唯一完成机制放在这个directowner内，
不新增watcher。rootrunad若notification_required=true则必须启用。当前根线程固定
01a07683-bc64-7463-8db7-9ee6243967d8，启动前与发送前都核实际CODEX_THREAD_ID。
使用已有真实成功C08 directowner queue协议：codex.exe queue --thread ROOT --message TEXT。
绝不运行连通性测试、不重布旧owner，不以终端文本代替native验收。
封存run/status后先写terminal，再seal queue_attempt（attempt1/max1/timeout45），
才调用一次实际queue。timeout标记delivery_uncertain、可能已经送达，任何结果不重发。
queue_result保留真实returncode/output或异常；求解和通知结果分别记录，通知不启动求解器。
无自动native/后处理/Git/Cfull/half/ref/下一任务。

## 完成检查及64位counter

采用实际Pos-Cell模式和Hardware case-insensitive gpu检测；完整steps/1682文件存在/
1040/0exclusion，原HG force/rate=23322438，pre/cor=11661219，
ratecalculations11661220/cache11661218，finite/net/stiffness dt/tau<=.2/spin<.01不变。
实际16case device marker从console恰1次。B summary须complete/coldhistory，
commits/endpointcalls=11661219、core=7000*N、HGsnapshot=2000*N，按整数解析64位字段。
sidecar只按1000 soil*1682 save写约1682000行，非每update；本runner不扫描大CSV。
所有22typed数组、真实native时间/IDs、signed intervals、ledger/drain/HG/sidecar逐行、
理论/压力/沉降/模态与旧u-pw比较都仍pending；exit0不等于physical acceptance。

root admission：stage=`upl_tpi_gpu_full2tv_run_r1.run_admission`，passed/one_job_only=true，
job精确tag/Release/B/full2tv，inputs列本script/note、gpu_run_r3/note/CPUhelper、psutil模块、
fullsource/build及269源/sourceDiff/base来源、newprogram/runtime、原seed三文件、oldA run/plan、
B.native_review_r5/science_r2.metrics及所有required_passed_checks。
allowed_paused_gpu_processes只能列真实原stopped身份。入口需--execution-authorized --admission。
当前作者只做静态审阅，未执行任何runner/程序/原生读取或新hash。

## 独立通知准入与已验证实际接口

新notify_admission stage=`upl_tpi_gpu_full2tv_run_r1.notify_admission`，passed/notify_only=true，
tag=本唯一B标签，root_thread_id为上述根ID，run_admission_path为本次root runadmission绝对路径，
max_attempts=1/timeout_s=45/watcher=false/automatic_retry=false。
包含codex stat及successful_queue_attempt/result stat，且都由runadmission.inputs冻结。
不互相循环绑定两个admission内容：runadmission绑定notifyadmission stat，notifyadmission
只绑定已知runadmission路径；actual terminal随后引用真正run/status stat。

只读成功proof为C08 tests/logs/c08_h18_hg_psi2p5_full3_r1.queue_attempt.json和
.queue_result.json，真实statusqueued/actual_exit0/同根线程。其exe
C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1106.51428-win32-x64/bin/windows-x86_64/codex.exe
当前仍存在，373698352B/mtime1794391544005116300，与实际成功attempt.program精确stat一致。
旧bigstep的26.1021 exe已不存在，不能采用它或猜新服务；本稿没有调用queue测试。

新路径另加<tag>.terminal.json/.queue_attempt.json/.queue_result.json，启动前均须不存在。
通知由同一个物理runner owner在原child终态之后发出；原run/status不因通知结果改写。
任何旧/本标签已有attempt均不能自动重试。本机制可在后台等待原实际child，不另起轮询进程。
root最终命令只有在全读后才加--notify --notify-admission NOTIFY_JSON，作者未执行。
