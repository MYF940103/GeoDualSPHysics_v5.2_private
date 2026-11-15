# C08 缓存 HG 同步调度优化：三项独立短测试

仅作者阶段。本轮只新增 `tests/support/c08_h18_hg_opt_jobs_r1.py` 和本文；脚本从旧 `c08_h18_hg_cached_jobs_r1.py` 机械派生。保留旧缓存候选、失败 partial、首错、完成的 .90s 窗口及旧数据。本文件没有授予执行权限；作者不 import 测试脚本、不 prepare、不 build、不运行求解器、reader、VTK、Git 或哈希扫描。root 完整审阅冻结资产后另行分别决定每次 prepare/run。

三个 profile 使用独立新标签，且 prepare 与 run 分别需要当前 root 的明确准入。没有队列、通知器、watcher、自动 native、自动下一项或自动重试。

| profile | 标签 | 构建 / HG | PRE 后更新 | 真实保存 completed step |
| --- | --- | --- | --- | --- |
| off1 | `c08_h18_hg_opt_off1_r1` | Release / 环境变量缺省 | 1 | 2000001 |
| debug2 | `c08_h18_hg_opt_debug2_r1` | Debug / `C08_HG_OPT_H18=1` | 2 | 2000001、2000002 |
| prefix4 | `c08_h18_hg_opt_prefix4_r1` | Release / `C08_HG_OPT_H18=1` | 6001 | 2000001、2002001、2004001、2006001 |

准备后的新定义和五列时间计划位于 `tests/configs/<tag>_Def.xml`、`tests/configs/<tag>.steps.csv`；输入副本与未来求解器输出位于 `tests/outputs/<tag>/`；两个 root admission、准备、真实 owner/start/call、日志、完成 seal、运行和状态收据位于 `tests/logs/<tag>.*`。任何已有完成或 partial 直接拒绝，不能覆盖或继续重跑。原生成输入三件套的 basename 固定为 `c08_h18_as03_n255_r1`，原 XML、BI4、Normals 与 17-key material profile 逐 byte 复制，不调用 GenCase 或重新预载。

旧认证的 schema2 同材料 ψ0 Wendland PRE 必须已完成 global2000000、1001 帧，实际 binary64 末时刻为 `9.9999999997060076`。保留原 AS .3/n2.55、AV .1、dp .04、H/dp1.8、H .072、5us、keepfalse、固定平面、CompletedOnly、5000 土粒/2060 原固定粒及255目标释放。原输入 `TimeMax=10.9`、`TimeOut=.01` 保持原字节；profile 仅通过绝对 `-nsteps` 上限缩短执行。

时间计划沿用原函数，从实际 PRE 时刻逐步 `clock += DT`，不以 `n*dt` 替代，也不改写实际元数据。`prefix4` 的四行还必须匹配原 91 行计划的真实前四行。其末保存约为 τ=.030005s，global cap2006001；6001 次更新和四帧分别由原 `.01s` 输出节奏及绝对上限产生，不把它称为恰好 .03s。

三项只接受 `c08_h18_hg_opt_{Release|Debug}_r1.build.json` 的实际 passed 收据：111 个旧对象、两个私有 host 加一个私有 CUDA，114 个链接对象，五个私有源文件、九文件 runtime，实际三次编译和一次链接。原物理 CUDA/Simpleker 对象、schema2、单材料 producer 与 OFF 旧编译积分核保持原约束。新构建还必须绑定旧 cached capture，并证明优化范围仅为 `block_error_snapshot_and_summary_reuse`：九个非 Node kernel 的每 block 首错快照、越界 return 前同步，以及 StageForce 的 Ace 观察/只读 summary/错误字段复用调度。`NodeKernel` 源字节、数值公式、拓扑、native ID 顺序与每 stage launch 数保持原样；失败仍读取完整 ErrorNow。源逆变证明不是新机器码等价证明，构建保留 `new_binary_equivalence_not_yet_proven`。

`off1` 的环境变量必须不存在，运行前清除同名大小写变体。OFF 不分配 HG/cache、不启动 HG kernel、不生成 HG 侧车；后续独立原生审查仍须比较全部22数组、真实时间、layout 与 signed-clock 完整行逐 byte。`debug2` 由 compute-sanitizer 实际包裹目标程序，绑定其真实子进程与目标 Win32 身份/退出值，随后要求零错误、零泄漏；材料、快照和 HG 原生侧车审查仍另行进行。新 ON 侧车名称为 `C08OptPlasticHG.csv`、`C08OptPlasticHGPolicy.json`，Debug 快照为 `C08OptPlasticHGDebugFirstN.csv/.json`；保持 policy schema2、60 列和 `PrivateC08SingleProducerOptPlasticHG` 身份。

`prefix4` 绑定已完成的 `c08_h18_hg_cached_window_GPU_r1` .90s 真窗口（global2180000、91帧），后续独立原生读取与逐 byte 比较只能使用其真实 Part0000–0003 与新四帧的共同 step/time：22数组、layout、完整 signed-clock 行及实际 HG/cache 证据。它是相同5us的优化前缀回归，不是 half-step 比较；4/91 原始记录数头保持原值，不重写头或时钟来制造整文件相等。旧91末帧的强制上限2180000不属于该四帧比较。

prepare/run admission 必须分别绑定本脚本、本文、实际已通过构建收据及唯一 profile，run 还绑定确切准备收据，且 `CODEX_THREAD_ID` 必须等于 root `01a07683-bc64-7463-8db7-9ee6243967d8`。没有自由 cap、输入或目标路径参数。运行前检查确切私有 EXE 已有进程；真实 owner、Popen/Win32 solver 与工具退出、父子身份和 argv 收据仍由原 helper 获取。先独立封存正常 schema2 `solver_completed`，随后才检查 summary、覆盖、memcheck 与派生证据。原 Run.csv AS 内嵌分号解析、异常 `*** Exception(exc):`/`Text:` 提取及首错保留保持不变；派生失败不允许重跑已完成求解器。

执行形式为 `python -X utf8 -B tests/support/c08_h18_hg_opt_jobs_r1.py prepare|run --profile off1|debug2|prefix4 --execution-authorized`，每次只运行一个显式 profile/phase。正常退出和这三项实现回归均不声明物理通过、塑性路径通过或独立旧材料返回0 ULP等价；旧1 ULP失败及全部原生安全门保留。作者验证只做静态 AST/差异审查，没有当前新增执行事实。
