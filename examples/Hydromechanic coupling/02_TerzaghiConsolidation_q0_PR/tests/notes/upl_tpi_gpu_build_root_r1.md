# GPU首版构建与CPU默认精确回归记录

2026-11-17。GPU首版私有Debug实际构建通过：3次CL、1次NVCC、1次link及环境调用真实Popen/Win32出口均为0，111对象由4个新对象和107个原配置对象组成。未执行help、求解器、memcheck或GPU原生检查。公开源码、项目、正式程序未安装改变。

保留原构建选项带来3条D9035（旧/Gm弃用）、52条第三方Debug库PDB缺失LNK4099和1条LIBCMT冲突LNK4098。LNK4098在原GPU Debug基座日志中同样存在；本阶段未为消除警告而更换运行库或数值编译选项。真实日志和所有私有对象/程序均保留。

独立代码审查在任何GPU物理运行前发现源边界检查缺口：旧GPU候选仅在pn不同于上一finalP时验证排水零压，因此已排水但仍保留旧非零pn可能被放行；pn=-0也会被后续写回掩盖。CPU已测路径有独立源状态要求。首版冻结源码与成功构建记录保持原样，但不得据此准入物理运行。下一新标签只补source-valid谓词和实际device负向夹具，不改变S/R、J更新、机械、HG或边界方程；不重启或覆盖首版。

其余GPU数学/生命周期独立审查未发现新阻断项：完整double Rγ保留Taylor和rho_w Da，S仍为leading-LP预条件，真实半步J/theta在原corrector入口捕获，额外端点不推进材料/J，HG读取原当前质量缩放贡献并保护历史/缓存与39个统计字段。此为源码审查结论，不是GPU执行或精度证明。

CPU默认A另完成一次纯离线原始typed数据比较。旧1682帧与新344帧仅前343帧真正共享：全部1040 IDs的22数组共75624640字节及clock28共9604字节逐位相同，7889个逐数组/时钟差异行均为0。新强制末步24000与旧下一保存步24004不共享，保留原计数和计划。未生成重复fullnative导出、未扫描SHA、未启动求解器。此证据补齐此前五个紧凑二进制导出之外PosDiv/V/rho/k等字段的实施回归缺口，不改变A的旧105.390 Pa科学门失败或物理验收状态。

入口：`logs/upl_tpi_gpu_Debug_r1.build.json`；`logs/upl_tpi_raw22_cpu_root_r1.review.json`；`outputs/upl_tpi_raw22_compare_r1_CPU_A_startup015_r1/{completion.json,arrays.csv}`。原始BI4、源码快照、程序和所有失败证据继续保留。C08暂停源不恢复、不终止、不改依赖。
