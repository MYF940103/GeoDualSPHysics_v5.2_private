# Lian 有界非周期 HG 候选（2026-10-27）

前置：独立SPR 3 s粗/半复核通过，见`lian_spr_half_review_r1.md`；已保存本地/远端9f8bbac。此处仅执行用户授权的有限HG兼容性工作，不准入100 s。

## 代码改动与数值范围

- `JSphHourglassCpu.cpp/.h`：内部period=0表示真实有界邻居；X网格按原生土粒子xmin/xmax分箱，越界列跳过，不跨左右墙、不做最小镜像。原正周期路径的分箱/遍历/累加顺序保持。
- `JSphHourglassGpu.cpp`、`JSphHourglassGpu_ker.cu/.h`：归约增加xmin/xmax，GPU网格/邻列/粒子距离同样增加有界分支。
- `JSphCpuSingle.cpp`、`JSphGpuSingle.cpp`：允许无周期域传period=0；仍拒绝y/z周期及斜向x周期。不移除其余适用范围或运行时检查。
- XML指南同步候选范围。无新参数，SoilHourglassXi默认0、关闭路径不创建HG对象。正式输入不改。

不改matched-LS残差、沙漏力、Xi定义、双精度历史、预测/校正更新及缓存规则，不改mDBC/SPR、加载、Darcy、孔压/应力精度或阻尼。仍限二维弹性、小转动、固定原生粒子、Wendland/Symplectic、全新启动；不支持塑性、运动墙、重启、一般大转动或3D HG。只支持这些情形不是新增防御性设计，而是保留原限制。

## 验证顺序与标准

1. 旧控制代码/程序在`tests/outputs/lian_hg_np_control_r1`保留并逐文件哈希。测试复用已验收的G3算子伴随程序，在Lian tests新增`lian_hg_np_test.cpp`，不是另写GPU物理实现。新旧周期算子逐值快照必须完全一致（0 ULP）；CPU/GPU、dense全对数学参考仍使用原1e-8相对加绝对容差，实际float加速度64eps。
2. 新有界测试：完整二维仿射零响应、平移、交错模式恢复、真实非周期负原点/窄网格/分离块/非规则粒子，稠密O(N²)参考不使用生产网格。检查严格支持域粒子对、合力、虚功恒等式与冻结几何能量；不把它们当作耦合稳定性证明。
3. 默认CPU Debug、GPU Debug/Release构建；GPU Debug内存检查。HG关闭的真实Lian短窗与冻结同物理对照原生字段0 ULP。通过前不运行HG开启的长窗。
4. 通过后仅有限真实Lian短窗，再3 s方案/独立半步长比较，沿用原5 Pa/0.005 mm保存样本阈值、有限/弹性/无排除/自然步长/几何/全向排水及13节点合力检查。侧壁FreeSlip/底部NoSlip不变；无1D均匀应力阈值。失败保留证据，不放宽限制、不提高阻尼或伪造周期边界。

旧正式100 s在10.90001 s主动停止，保持退役和保护。已验收case02不重跑或改写，旧KEEP/u-pl/TPI/Yao/滑坡不重开。完成Lian后Cryer，再01自重。

## 已完成的算子阶段

CPU Debug、GPU Debug/Release实际VS工程构建通过。新旧Release伴随程序的周期CPU/GPU原生ID率/历史/加速度快照SHA均为`56ce8a2e3623091d6a716997e962177567d51aa77e9fe69a138c23b8fcc197ec`，逐值0 ULP。原42项及新增16项有界算子测试在GPU Debug/Release各58项通过；测试同时调用实际CPU/GPU算子与独立dense参考。二维仿射场残余率3.25424e-21，稠密参考GPU率误差最大1.73472e-18。Debug memcheck真实检查零错误、零泄漏。日志中的预期HG异常用于确认塑性/坏ID/奇异矩阵/非法步长/阶段/转动限制仍拒绝，不是求解失败。

单独96粒子冻结几何振子以真实HG线性刚度、另写的velocity-Verlet积分器验证128步能量有界：总能量比0.99993975284–1.00000000463，原定0.999–1.001界内。CPU/GPU率差最大2.03288e-20，合力残量3.46945e-18。**不是生产SPH或历史积分器的能量证明**。能量图和CSV已检查，`lian_hg_np_review_r1.check.json`记载来源；真实Lian动态检查尚待执行。

仅新离线复核曾遇到两项记录格式适配：PowerShell构建清单只有SHA没有bytes，Tee日志为UTF-16。复核脚本已按实际格式读取并完成哈希/数值检查，未改动冻结旧清单或重跑求解器。第一次memcheck命令误指CUDA bin，未启动程序；实际工具位于CUDA11.7/compute-sanitizer，成功记录另存`lian_hg_np_debug_r2.memcheck.log`，失败尝试保留。
