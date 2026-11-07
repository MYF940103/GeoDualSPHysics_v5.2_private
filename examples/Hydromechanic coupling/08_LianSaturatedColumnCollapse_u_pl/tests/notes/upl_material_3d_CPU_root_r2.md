# 三维DP材料点候选：CPU第一阶段

本轮不改生产源码、旧默认、服务器r2程序/XML/BAT/ZIP；没有空间求解、半步链或物理验收。候选仅把固定φ返回核的系数选择拓展至已有DP_C/DP_MC，保留原DP_PS表达式；没有新增XML接口。

41点：21径向返回、12弹性/卸载、3预期不支持顶点、5非法输入。14个DP_PS点与当前FunSoilMaterial逐成员完全一致；9个三维旋转、14组固定应力屈服/剪胀系数/F导数有限差分通过。所有普通点采用六个非零应力分量。连续κ下最大屈服残差8.27380518e-7Pa，保存floatκ后最大5.55141580e-5Pa；这是局部代数残差，不是空间孔压误差。有限差分最大误差/事先解析预算比0.182137。

首个测试工具编译遇到独立Invariant辅助函数与候选同名函数的C++ ADL冲突；r1源码/日志/failed检查保留。r2只把独立审计函数改名ReferenceInvariant；候选公式和门槛未改。r2实际CL/link/运行退出均0；沿用闭合CPU Debug的85个非main对象，没有重建或覆盖生产程序。

实际结果：outputs/upl_material_3d_CPU_result_r2/points.csv及completion.json；闭合记录logs/upl_material_3d_probe_r2.check.json。下一步为同核GPU材料点和实际Pre/Cor适配检查；公共三维塑性u-pl/mDBC、摩擦软化、顶点返回与重启仍未由本轮解锁。
