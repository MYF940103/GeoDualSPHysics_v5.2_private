# 本机 r3 接续服务器 r2 弹性 PRE（author-only）

新增 `tests/support/upl_c08_resume_r1.py`，本文与脚本已写好，尚未执行 prepare、GenCase 或 solver。原服务器 source output、全部 BI4、r2/r3 正式模板、runtime、ZIP 和 manifest 不修改。先 ψ=0° GPU 短窗；后续是否做完整阶段和另两组由根线程审核后分别显式启动，不自动接续。

唯一原始源：根目录 `CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4`。已观察源 Run.csv 为4,000,000步、1001份标准PART、零排除，Run.out正常code0；这仅是调度/退出证据。脚本不声称已经读取认证全部原生κ/IDs/ledger；真实 r3专用 loader 必须以新几何契约核验旧MR1 ElasticV1 PRE，不能使用撤墙后塑性PART或改写源元数据。

## 两种独立窗口

- short：源completed4,000,000，CLI `-nsteps:4040000`，只做40,000个新updates（约0.1s）。原XML `TimeMax=13`、dt2.5µs、TimeOut.01s及全部数值保留，只把注释注明短窗全局上限。
- full：仍从同一弹性PRE fresh导入，CLI `-nsteps:5200000`，1,200,000个新updates（约3s）。不是接着short的PART算；short证据原样保留。此脚本full输出仍在tests，不生成根目录正式full入口或启动它。

源实际累计 binary64 时钟由loader导入，不能改为10或0。脚本只读解析真实import/release日志，核completed4M，并用scalar `+=2.5e-6`复算检查导入时钟。预期真实源时钟约10.000000000374257s；实际值只从真实loader日志记录，不用Run.csv的六位小数冒充原生clock。首次循环只允许一条退墙日志，retired260，damping/Shepard OFF，free seepage ON。

## 根线程完整审阅后逐项命令

从case08根目录执行：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_resume_r1.py prepare-short --group psi0 --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_resume_r1.py run-short --group psi0 --execution-authorized
```

prepare只从对应根r3 Def文本替换唯一PRE绝对路径（及short注释），逐节点核所有其他非comment属性不变；一次真实 runtime_r3 GenCase生成fresh XML/BI4/Normals三文件，不复制旧seed、不启动solver。run只启动这一个r3 GPU Release target，无GenCase/decoder/后续solver。每个prepare/run均拒绝旧收据、partial或同名输出；同一runtime程序/输出或另一活动GPU target会拒绝，不停止任何进程。

根线程读完短窗原生结果并明确准入后，才可单独调用：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_resume_r1.py prepare-full --group psi0 --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_resume_r1.py run-full --group psi0 --execution-authorized
```

另两组仅将 `--group` 改为 `psi2p5` 或 `psim5`，使用各自原r3模板和同一源；不能并行乱点GPU0。脚本没有通知器、自动重试、调参、half或下阶段自动运行。

## 文件和收据

新配置：`tests/configs/upl_c08_resume_r1_<group>_GPU_<short|full>_Def.xml`。fresh seed和计算数据同在浅目录 `tests/outputs/upl_c08_resume_r1_<group>_GPU_<short|full>`；GenCase前缀同tag。过程 start/call/log 与 prepare/run.json 在 `tests/logs`。不写根目录正式结果。

owner直接Popen持有真实Win32句柄，记录PID/创建时间/exe/确切argv、wait与Win32实际退出；先封口实际退出，再做退出日志/Run.csv调度检查。必要source/runtime/program/build/input用stat绑定，不做SHA扫描。原源约1001个文件只枚举名称，不重新解码或逐文件哈希。出错保留first_failure、真实call和partial，不凭最后输出行虚构故障时刻。

run.json最低字段与独立reader约定：`passed, actual_exit, actual_Win32_exit, actual_steps`（全局completed）、`saved_frames`（真实Run.csv）、`program, source_build, source_pre_file, input_xml`（均stat）。`input_xml`指实际执行GenCase生成的runtime XML，而非Def；`output`给实际数据目录。ψ0 short为 `tests/logs/upl_c08_resume_r1_psi0_GPU_short.run.json`。成功也保持 `native_review_pending=true, physical_acceptance=false`；原生读取/所有22数组、signedclock、κ/ledger/边界/压力和位移审核由根线程另派reader完成，不能由本脚本的正常退出代替。
