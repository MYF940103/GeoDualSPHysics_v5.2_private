# ψ0完整3s诊断的可视化导出

仅对已完成且已独立native检查的 `c08_h18_wall_c_retry_full3_GPU_r2` 执行两次PartVTK工具：分别输出301帧PartFluid（每帧5000点）和PartBound（每帧1805点），不混合两类粒子。输出目录为原运行目录下新的 `particles/`，已有目录或工具调用记录均拒绝重复启动。输入BI4、原native、原程序、旧VTK和PRE不修改。

沿用已审的PartVTK与原完整变量列表（含孔压/P0/应力/κ/J/n/速度/FS等）。VTK位置是工具的可视化float输出，精度分析继续使用原double typed22及CSV和实际时钟。602个真实VTK逐一核对点数；导出成功不等于物理验收，也不启动solver/native读取器/下一组。此Python脚本由根线程完整阅读后以 `--execution-authorized` 单独执行一次，零SHA扫描。
