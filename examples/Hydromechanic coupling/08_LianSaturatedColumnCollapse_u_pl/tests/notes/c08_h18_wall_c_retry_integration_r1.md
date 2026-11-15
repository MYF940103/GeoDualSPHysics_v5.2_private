# C08 C 重构候选：集成通过，3 s 诊断运行中

2026-11-16。源码和十项 GPU 定点测试证据已在本地/远程 `upl-dev` 提交 `46fc573f08d3a083d57e43ada008b0b9a87ae96f` 保存。本记录补充后续集成证据，不是物理或论文验收。

## 已完成

- 新 GPU 候选的四帧真实塑性/HG 启动回归完成，共 6001 个新更新。6805 IDs、22 原生数组、layout、真实 clock、全部 signed 间隔及八行 HG/policy 均与已保留修改前控制逐字节相同。实际末时刻 10.030004999704872 s。每组 native 只读取一次。
- CPU before 基线只替换同一新 Debug 闭包中的一个 mDBC 对象，保留其余 86 对象。编译实际使用的唯一头文件集合为原 270 个；sourceDependencies 的 339 条包含重复路径。没有缺失或新增头。保留 SDK8.1 API＋UCRT10240，未以新 SDK 冒充原依赖。原 MSBuild 的 CL host 架构未捕获，此限制仍保留。
- before/after 各完成两步、三帧 CPU public-column 回归；每帧 1040 IDs、22 数组，每组土体 ledger 3000 行、固定 marker 120 行。五份完整 bin 加实际 PosDiv/V/rho/k 等 CSV 共 12 个导出逐字节相同；包括初始和两个非初始 signed clock 记录。求解器和 reader 各两次均真实退出 0。
- CPU 短窗未跨排水事件，也未触发新的失败 C 重试分支；该分支由单独 GPU 故障包组件覆盖。不宣称 CPU 新拒绝分支、一般 SPD、力阶段或非空排水验收。

## 准备脚本的两处实施错误

full3 r1 仅准备审查失败：错误假定旧 HG0 preparation 含 `passed`。未启动 solver/GenCase/reader，未生成其输出或计划。r2 按旧记录真实 stage/prepared_only/exact_inverse 与有效 consumed_stats 字段，并交叉绑定原程序/PRE/计划/材料后通过准备。原失败保留，未改物理门槛。

CPU before r1 的 cmd 环境调用因 list 参数内引号转义而真实退出 1；CL/link 未启动。r2 改为无空格 TEMP 中的固定 env.cmd，保持原头/库/编译逻辑后构建成功。原调用及 partial 保留，没有替换历史结果。

## 当前长算

唯一活动 GPU 任务为 `c08_h18_wall_c_retry_full3_GPU_r2`。原同材料 schema2 Wendland PRE 复用，cold-zero HG；AS .3/n2.55、AV .1、hdp 1.8、5 µs、keepfalse、fixed-plane/CompletedOnly 保持。目标撤墙后 3 s、600000 新更新、全局 2600000、301 帧；scalar 末时刻计划为 12.999999999592434 s。启动后的实际 owner/child 身份已核对。按四帧实测成本估计约 5 小时，不是受控性能基准。

此任务尚待终态、唯一完整 native 读取、HG 阶段/功/历史、孔压/应力/运动/间距和论文图审查。NoPen ReactionClosed=false；其他两组 ψ 尚未启动。原 full3/host replay 失败仍保持失败。

只有同一直接运行 owner 的一次终态队列作为完成机制；不增加 watcher、自测、重发、半步链或自动其他 ψ。所有 BI4、PRE、程序、对象及 source 归档继续原位保护，本阶段 SHA 扫描数为 0。
