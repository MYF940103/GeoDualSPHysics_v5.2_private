# GPU double 排序工具阶段范围审查

本记录是发布范围与必要证据清单，不是 GPU 动态渗流、原生求解器或物理验收结论。基线为本地／远端已核验的 CPU checkpoint `25f40dc13b8bfacf698aab3e7668ec2afb252788`。

## 本轮修改

仅 `JCellDivGpu.h/.cpp` 与 `JCellDivGpu_ker.h/.cu` 新增单 double 排序重载。发布时必须从旧4份快照与当前文件核验：原有源码行按顺序完整保留，合计仅新增31行。没有在本阶段加入 GPU J/n 状态数组、压力率、动态渗流或公开 GPU 开关。

冻结的3份作者配方是 `support/upl_gpu_sort_r1.cpp`、`support/upl_gpu_sort_r1.ps1` 和 `notes/upl_gpu_sort_r1.json`；发布脚本不修改或执行它们。

## Seal 必须核验

- Debug、Release 各576个实际组件复制／排序记录通过：直接 CUDA 接口288例，真实类包装288例；包含96个零长度记录、前缀、非恒等映射、17个尾保护槽及旧 float/byte/六double应力对照。源、映射、目标与尾保护均逐字节核验，不使用数值容差。
- Debug 的实际 compute-sanitizer 调用退出0，原始日志明确显示零错误及零字节泄漏；Release 另有独立实际运行收据。
- 两配置都由权威 GPU solution/project 完整重编译，使用隔离 OutDir；这不是替代 CUDA 算法。旧 canonical GPU 程序与归档副本哈希仍相同；不声称这些旧程序由当前共享源码构建。
- 默认 CPU Debug 构建退出0来自主代理 session6934 的工具终态观察及对应日志绑定。Seal 要求显式 `-CpuDebugExitObserved0`；不从日志内容推断退出码，也不把此项当 CPU／GPU 原生轨迹回归。

## 选择性发布

仅4个生产文件、3份冻结作者配方、发布脚本与本说明、明确的 baseline/build/source/check/call/log JSON／文本、两份576行 CSV／complete，以及旧4＋新8份源码文本快照。下一步只备份已完整审读的 `notes/upl_gpu_state_plan_r1.md`，它是计划，不是数组或功能已经实现的证据。

不带 exe/obj/lib/PDB/ILK/binlog、运行库、全部源码文本复制、原始求解器结果或其他未提交修改。原始程序只在本地以哈希绑定；不能称为云端程序备份。

`List` 只读；`Seal` 必须在两配置真实组件检查均通过后生成新清单；`Stage` 另须显式授权和完全一致的清单 SHA，且拒绝夹带无关暂存文件。脚本没有 commit/push、构建、help、求解器或自动后续任务。

## 尚未覆盖

真实 cell divide 生成的排列、GPU J 状态生命周期、动态耦合方程、默认 OFF 原生求解器回归、CPU/GPU 精度／速度比较及物理／正式发行均未由本组件阶段接纳。

