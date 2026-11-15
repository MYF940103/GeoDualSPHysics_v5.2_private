# C08 ψ0 优化缓存 HG：独立新 3 s 诊断

本轮仅新增 `tests/support/c08_h18_hg_opt_full3_r1.py` 和本文，机械派生自冻结的 `c08_h18_hg_opt_jobs_r1.py`。作者不 import、prepare、build、运行求解器、reader、VTK、Git 或哈希扫描。本文和脚本均不授予启动权限；root 须分别审阅、准入 prepare 和 run。旧 HG0、旧失败、cached .90 s、opt 短回归、原认证 PRE 及全部程序/源码/原生数据保持原样。

唯一 profile 为 `full3`，唯一运行标签 `c08_h18_hg_opt_full3_GPU_r1`。它采用已通过的 opt Release 构建和 `C08_HG_OPT_H18=1`：原 Wendland H/dp=1.8、dp=.04、固定 5 μs、AS .3/n2.55、AV .1、原材料及动态渗流、keepfalse、固定平面 NoPen、CompletedOnly 不变。NoPen 的同阶段 Darcy 反力未闭合，`ReactionClosed=false`；这是诊断候选，不是物理或论文验收。

复用 `c08_h18_as03n255_full3_r1` 已完成且原生审查通过的生成 XML/BI4/Normals 三件套及 17-key profile，逐 byte 复制到新目录，不重新 GenCase，也不重新预载。原 basename 保留。定义副本位于 `tests/configs/<tag>_Def.xml`，生成输入和未来输出位于 `tests/outputs/<tag>/`，计划为 `tests/configs/<tag>.steps.csv`，owner/start/call/run/status/solver seal 及两个 root admission 位于 `tests/logs/<tag>.*`。已有完成或 partial 一律拒绝，不覆盖或重试。

该输入的 `TimeMax=13.0`、`TimeOut=.01` 已由旧 3 s 生成阶段准备；本轮不再修改输入数值。仍从原 Wendland schema2 同材料 ψ0 PRE `Part_1000` 的实际时刻 `9.9999999997060076`、global2000000 开始，600000 次新更新，绝对 cap2600000。HG 内存从原未含本候选 HG 历史的 PRE 冷启动为零；这不是 HG PART 重启。保存 301 帧，完整末态实际时刻为 `12.999999999592434`，不得以 `13.0` 替代原生时钟。

时间计划完全消费旧 `c08_h18_release_full3_r2.steps.csv` 的 301 行。前300行 completed step 为 `2000001+2000*part`，末行为2600000，saved step 均为 completed−1。脚本从实际 PRE 时刻逐步 `clock += .000005`，检查每行整数 step、保存时刻与原表完全一致，不插值、不用 n×dt、不改写实际元数据。旧 cached .90 s 的强制末态2180000与新 3 s 的 Part0090=2180001不同，因此后续同参数前缀只能比较旧/new 的前90帧 Part0000–0089；91/301原始头必须保持，不能删记录或改头制造整文件相等。

prepare 和 run 都独立要求三项 opt 实施回归的原始 `.run.json` 与 root `.check.json` 已通过：OFF1 的22数组/完整 signed-clock/layout逐 byte 与无 HG 对照一致且无 HG 侧车；Debug2 的原生两帧、四行60列 HG、policy仅family标签变化、907392字节 first-n 全快照及配置一致、实际 memcheck零错误和泄漏；Release prefix4 的22数组四帧、完整时钟/layout/signed、八行60列 HG逐 byte一致，且确有保存的塑性阶段。每项必须有真实工具/求解器退出、所有权、完整原生 completion、未变化程序及源码绑定。缓存输入/写回相等是单 producer 一致性，首力参考是保留快照的传递，不冒称新增独立旧材料求解或新 CPU component。

脚本仍保留原111个物理对象加三个私有对象的构建检查、精确当前 root `CODEX_THREAD_ID=01a07683-bc64-7463-8db7-9ee6243967d8`、实际 owner PID/创建时间/exe/argv/parent、句柄 Win32/Popen 出口与 surviving-process 观察。prepare/run admission 必须绑定本脚本、本文、实际 Release build；run另绑定精确准备收据。运行前拒绝同私有程序已有进程。先独立封存求解器正常完成，再审 Run.csv 的真实 global step/301帧/无排除/舍入终点；保存原异常首因、最后原始 console PART行和 partial，不重建未保存故障时刻。求解器完成但派生失败只允许离线修派生，不能重跑求解器。

本脚本沿用 `c08_h18_hg_cached_window_r1.py` 的单一直接 owner 终态队列，不另挂 watcher。两个 admission 均须明确 `single_full3_only=true`、`terminal_queue_once=true`，绑定原已核验当前 Codex EXE stat、同 root thread 和物理决策收据。只有真实调用产生终态并先写好 run/status 后才调用一次 `codex queue --thread ...`，45秒超时只记 `delivery_uncertain`，绝不重试、重发或重新布防；prepare不会投递。没有自动 native、VTK、下一组、half、PRE 或正式发布。每个 phase 仅执行 `python -X utf8 -B tests/support/c08_h18_hg_opt_full3_r1.py prepare|run --profile full3 --execution-authorized`。

正常退出仅表示待独立原生和物理审查。后续只在 root 明确准入后复用现有 full301 原生工具，核22数组、6805IDs、P0、J/ρ/κ/ledger、FS/plane、真实 clock及signed诊断，并审 HG全部 phase/work/history、孔压尖峰、土体位移/速度/塑性/间距/非仿射形态、早停和论文参考。局部 HG 预算不等于外向或耦合能量证书；.90 s 无序减轻也不能证明3 s张拉稳定或论文精度。其他ψ仍锁定，只有本组完整审查后的独立root判断才能决定后续。
