# Darcy denominator 的最小真实耦合 A/B（author-only）

本工具尚未编译或执行。仅新增本 note、`support/upl_darcy_eta_wave_r1.cpp` 和同名 Python owner；不编辑生产源码、VS 工程、正式 XML/BAT、canonical 程序或服务器 r2/r3 包。

## 比较及范围

复用已通过的 `upl_p3_spatial_wave_harness_r2.cpp` 及 `outputs/upl_p3_spatial_seed_r1_n32_c/CaseUplSpatial_n32_c.{xml,bi4}`。两组都是 32×16、512 原生材料 ID，XZ 周期、无墙、无加载/排水、常 k=1e-4、原材料/初态/全局 Eta、真实 `ComputeStep_Sym`，512 updates，dt=2^-24 s，终点 2^-15 s，257 个实际保存时刻。无 half、额外参考 solver、长算、PART 导入。

baseline 链接 `mdbc_partition_DebugCPU_r1.build.json` 真实 87 个对象中的 86 个非 main 对象。candidate 仅将其中 `JSphCpu.obj` 替换为私有对象：从当前且与原 source capture stat 一致的 `src/source/JSphCpu.cpp` 复制到新 `outputs/upl_darcy_eta_wave_r1_build/JSphCpu_eta0.cpp`，唯一将 Darcy 率内 `/(rr2+double(Eta2))` 改成 `/rr2`。原成员 Eta2 不写入；力学、AV、C、墙、动态加速度和积分方法均不改。

两 helper 使用同一 CPP，仅 `/DUPL_DARCY_BARE=0/1` 不同。宏只影响独立初始离散参考符号 ell 的 Darcy 分母及完成标签，不选择生产方程。原单组 IDs/无排除、ledger、有限性、κ=0、p0=0、周期复制、energy≤1.1、耦合 CFL/扩散限、自然步长、signed FixedDt error、原压力/速度/位移离散参考门保留。移除原 Half 实现和 CLI，锁定单一 coarse。

## 只在根线程全文审查并授权后逐项执行

下列命令每项只做一个明确动作，不自动接续：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_darcy_eta_wave_r1.py build --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_darcy_eta_wave_r1.py limits --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_darcy_eta_wave_r1.py baseline --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_darcy_eta_wave_r1.py candidate --execution-authorized
```

命令从 case02 根目录执行。build 重用原 MSBuild DebugCPU 的 CL/link tlog 命令及真实对象；仅改隔离输出参数，私有源码加原 source include 路径，helper 再加 C++17 和测试宏。使用相同 MSVC 14.36.32532。runtime DLL/配置从真实隔离 DebugCPU 程序目录复制，逐字节确认一次，不做 SHA 扫描。

每个动作拒绝已存在输出、日志或 receipt。直接 Popen 保留真实进程句柄，捕获 PID、Win32 创建时间、真实 exe 路径、确切 argv、wait exit 和 Win32 exit。采用 source/object/input/program stat 绑定；不存在通知器、自重启或自动清理。失败保留原样输出；完成退出只表示待离线审查。

`--limits` 是独立实际 CPU Cubic/Wendland `GetKernel_Fac` 数值探针：包含零、原 ALMOSTZERO 守卫下/等/上以及若干正距离；被原 `rr2<ALMOSTZERO` 排除的项不调用 Fac，其他项要求实际 Fac 和零-Eta 径向权重有限。它不是 solver、重合粒子修复或任意无序场证明。

## 输出及根线程离线评审

build 在 `tests/outputs/upl_darcy_eta_wave_r1_build`；其他输出在同级 `..._limits`、`..._baseline`、`..._candidate`；过程和完成收据在 `tests/logs`。每个真实积分输出 `physical.bin`（12-byte uint header [512,26,257]，随后每帧 double actual time + 512×26 doubles）、`modes.csv`、`endpoint_policy.csv`、`complete.json`。

根线程离线审查需核两组257个实际时钟、全部512 IDs隐式有序槽、初帧26字段逐位一致、单组原门，以及每字段后续差异；A/B是不同算子，不能套5 Pa跨算子等价门。比较相同连续耦合方程的独立 4×4 matrix exponential 与全历程 p/u/v/stress、J、energy；沿用原材料、初始正弦振幅和未拟合的 k=2π/L，不用各自 ell 拟合连续理论。helper 的离散 RK4参考是独立初始晶格线性符号，与当前随 J/C 轻微演化的非线性求解不完全相同；保留其原预算而不声称精确非线性真解。

旧 Nx32 Release 同窗口实际耗时 2.687 s；当前 Debug 预计仍为短窗，但本轮不预先宣称耗时或提速。该平整周期场未覆盖自由表面 raw-head、实际墙、可变 k、大变形或完整塌陷；不能仅凭通过就替换生产 Eta 或完整 Eq23 张量。后续是否需要 C08 局部验证由本轮实测收益与代价决定。
