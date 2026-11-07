# C08 ψ0 r4真实根BAT单次正式owner（author-only）

新 `tests/support/upl_c08_formal_psi0_r4_r1.py` 机械派生已审 `upl_c08_formal_psi0_r1.py`。保留原Popen/Win32句柄、真实wrapper/GenCase/solver识别、每30s状态、异常继续观察/不杀进程、失败partial保存、BAT后处理检查和终态一次通知流程。本作者未启动solver、reader、post或codex CLI；当前0.15实际回归只读，不改其文件/依赖。

新scope：只调用真实根 `xCaseLianSaturatedColumnCollapse_psi0_shared_r4_win64_GPU.bat --unattended`，正式输出 `CaseLianSaturatedColumnCollapse_psi0_shared_r4_GPU_out`，运行时 `support/runtime_r4`。GenCase＋单GPU目标由BAT实际发生，owner不另生成输入、不重复GenCase/solver。准确目标CLI为`-gpu:0 -stable -mdbc_freeslip:1 ... -svres`；原TimeMax13/dt2.5us/out.01，原r2 GPU Part1000认证弹性PRE，撤墙260一次、global5200000约3秒新更新。AS0，NoPen正式策略`LegacyOperatorSplitReleaseOnly`，反力/J/Darcy未闭合；不是同源算子PRE或全程物理验收声明。

唯一新准入为 `logs/upl_c08_nopen_public_review_r1.check.json`＋对应public_reg run/call、`upl_c08_nopen_public_Release_r1.build.json`。必须实际GPU目标rc0/无ownership错误、4060000/15帧、typed22及完整signed clocks相对隔离控制byteexact、r4 native15全门通过、实际一次native/Fluid/Bound/PNG/CSV后处理通过。context绑定这一回归、真实程序/源PRE/根配置BAT/post脚本/tools、readonly准入产物的stat，不重跑旧.1短链、不SHA。

BAT成功时自动一次C08Native＋分别PartFluid5000/PartBound1800全帧＋r4图/CSV。owner在wrapper结束后核实际solver0与5200000/无排除/原source累计clock/一次release，随后核`postprocess_r4.json`、新native policy和3个post-tool实际退出/manifest、全程history及τ.1/.5/1/2/3场图CSV。若solver0而post失败，保存solver_completed=true/failed_stage=postprocess，后续只修派生，绝不重复长算。若真实runtime失败，只保存actual Win32退出、最后原样console PART行和首因，不虚构未保存停止时间、不改旧结果。

线程说明：本作者子线程ENV是另一UUID，不能拿它投根通知。根已独立核其实际ENV仍为`01a07683-bc64-7463-8db7-9ee6243967d8`。owner从**实际launch ENV**读取THREAD，`--notify`时必须等于该已核ROOT_THREAD；start写actual ENV/expected root线程，queue使用这份已冻结THREAD。此作者未调用CLI；不是把子线程UUID或过期推测ID写死冒用。

根完整审阅且public_review实际passed后，由**根工具环境**一次显式启动：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_formal_psi0_r4_r1.py --execution-authorized --notify
```

只有终态run封口后，才45s尝试一次`codex queue --thread THREAD --message ...`。timeout可能已送达，禁止重发、rearm、connectivity test。中文消息指向本组r4records/已完成一次后处理，继续原授权物理图/论文审查及其余ψ阶段；通知本身不启动新solver/decoder/half。existing输出/owner/partial存在即拒绝本owner再启。
