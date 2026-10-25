# 三维测试发现的GPU退出资源释放问题

2026-10-25。CPU edge3 FreeSlip 2 ms粗/半步已完成，所有201样本通过；压力RMS最大差0.014859332 Pa、三维材料点位移差8.70660243e-10 mm，能量最大约1.02024倍。它不受本GPU退出问题影响。

GPU新伴随与真实正式Debug程序各20步均完成，但compute-sanitizer分别报1个CUDA API错误：JGaugeSystem::Reset中cudaFree无效。调用链是JSphGpu析构先cudaDeviceReset，随后JSph基类析构再delete GaugeSystem；RunGaugeSystem即使没有测点也可能分配其AuxMemoryg。没有观察到该20步中的核内存越界，但不能把有退出错误的memcheck写为通过。

最小生产补丁：src/source/JSphGpu.cpp的JSphGpu::~JSphGpu，在释放GPU数组和cudaDeviceReset之前delete GaugeSystem并置NULL。基类再删除NULL安全。没有改任何计算循环、边界映射、物理状态、方程、时间积分、内存布局或参数。

修改前JSphGpu.cpp、三维运行脚本和两份真实GPU执行程序已复制到tests/outputs/spr_3d_precleanup_r1，逐字节哈希见logs/spr_3d_precleanup_r1.snapshot.json。旧build/status/失败memcheck保持原样。CPU已完成收据绑定的旧spr_3d_run.py通过该快照核验，不能要求一个有版本演进的工作路径永远保留旧字节，也不改写历史哈希。

新运行脚本仅增加GPU构建标签选择（默认新r2），并在启动下一子进程时重置顶层owned_exited=False，避免该摘要遗留前一个已退出子进程的状态。逐run退出记录原本即独立保存。复核脚本仅对明确列出的原路径/原SHA用对应快照解析旧输入，不泛化忽略哈希错误。

接下来重建默认CPU Debug、GPU Debug/Release及新标签伴随；相同20步真实程序和非零三维伴随应为0个memcheck错误，修复前后已保存的原生物理字段应逐位相同。通过后继续GPU 2 ms粗/半步、同dt CPU/GPU比较；不能以退出清理修复为三维物理验收。
