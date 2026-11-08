# ReleasedSubstages 的三个独立 2 ms smoke 入口

仅新增同名 support Python 和本说明，两个新名事前不存在 / 未跟踪；作者未运行、import、构建、GenCase 或解码。root 规划依次审阅 CPU Debug、GPU Debug memcheck、GPU Release，每次 CLI 只选一个任务，不自动串联，不通知 queue，不自动进入 .66s。

固定从已有 `configs/upl_c08_asn3_window_GPU_r1_Def.xml` 只替换 TimeMax=10.002、TimeOut=.001，CLI 全局上限 `-nsteps:4000800`。dt=2.5µs、AS=.2 / 指数3、keep5 / retire255、固定平面 NoPen、材料、源 r2 GPU PRE 全部不变。GenCase 仅在被 root 显式选择的该任务中一次生成 fresh seed；实际生成输入除声明的计时 / 文件名 / date 外逐树核对 n3 既有 seed。原注释可能仍记 .66s，但数值仅上面两项变化，未借注释修改任何物理参数。

原 PRE 实际源时钟从 loader 日志提取，不写成10或0；800次新增更新，计划两帧 completed=4000400/4000800。GPU trace 每40步的计划采样为20个 step；运行收据仅绑定实际 trace 文件，原57列 / half投影 / float/RHS 代数由独立 `upl_c08_stage_ponding_review_r1.py --profile smoke2ms` 审查。CPU Debug 未定义 GPU trace 宏，不能声称有 CPU trace 证据。

只接受新构建 `logs/upl_c08_stage_ponding_{DebugCPU,Debug,Release}_r2.build.json`，对应新 `source_r2/source.json`。不采用失败的 r1 CPU 程序或旧 objects。runtime_r5 的必要 DLL/config 只 copy2 到新构建目录、逐 stat 比对，原 runtime 不改。真实 Popen / Win32 / 子 solver 句柄和30s状态复用已闭合 bedkeep owned helper；GPU Debug 同一调用包装 memcheck，必须错误 / leak 均0。CPU为原8线程，不作性能比较或把跨后端旧 PRE 接收称0ULP。

root 完整阅读并逐个明确选择后，独立入口如下；本作者均未执行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_stage_ponding_smoke_r1.py CPUdebug --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_stage_ponding_smoke_r1.py GPUdebug --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_stage_ponding_smoke_r1.py Release --execution-authorized
```

每组新浅目录 / 收据 tag 为 `upl_c08_stage_ponding_smoke_<选项>_r1`；拒绝已有或部分输出，失败保留真实出口和最后原始 console PART 行，不重算、补写停止时刻或覆盖证据。正常退出仅 native/trace pending；没有 reader/VTK/后处理或 .66s action。独立 native 安全及实际 trace 均通过且 root 审阅后，才可另行准入窗口；没有自动物理验收。无 SHA 或半步长求解链。
