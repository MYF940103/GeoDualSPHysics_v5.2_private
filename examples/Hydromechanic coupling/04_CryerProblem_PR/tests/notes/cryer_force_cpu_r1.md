# Cryer：CPU 实际算子的静态制造场 companion

## 本阶段范围

准备 `tests/support/cryer_force_cpu_r1.cpp` 与 `cryer_force_cpu_build_r1.ps1`，由主代理审阅后才构建、运行。它通过 `JSphCpuSingle` 子类调用实际初始化、`PreInteraction_Forces`、`ComputeFreeSurfaceTracking` 和 `Interaction_Forces_ct`，不调用时间积分，不构造新的物理求解器，不修改 canonical CPP/头文件、正式输入或 GPU 程序/DLL。

先完成 authoritative 默认 CPU Debug 构建，再以项目列出的全部当前 CPU 对象文件（仅排除原 main）链接 companion。构建脚本仅创建自己的新输出目录，拒绝覆盖；沿用 Lian `lian_spr_mix_cpu_build.ps1` 的编译器、静态库、头文件及对象绑定方法。脚本不启动任何求解器。

实际依据文献为：

- `src/papers/PDF/a-coupled-u-p-sph-formulation-for-hydromechanical-modeling-of-retrogressive-landslides-and-comparison-with-a-penalty-based-approach.pdf`：当前 u-pw 动量项，分别为 `sigma_i/rho_i²+sigma_j/rho_j²` 与 `-(p_i+p_j)/(rho_i rho_j)I`。
- `src/papers/PDF/2019 - Zhao - A generic approach to modelling flexible confined boundary conditions in SPH and.pdf`：柔性围压与接收点修正的来源，不把其干土式当作已经验证的 u-pw 改写。

这两份原 PDF、当前源码/headers/objs/链接库、companion 文件、前轮离线收据都进入新构建 manifest。前轮已封存收据未改写；其绑定的另一个 `An SPH framework...` 不是这里当前 u-pw 主文，不混称。

## 六个冻结场与真实输出

使用原 Cryer 生成初态的37173个土粒子和远端 dummy boundary，不移动粒子，不改 cell/邻居布置。完整原生 ID 必须唯一齐全。以下仅在 companion 内暂置：`HydroMechDrainage=false`、重力/黏性/SoilDamping 为0，原有 SPR/HG 关闭；不改变正式初始化。

1. 静止，初始均匀密度，`sigma=-qI,p=0`。
2. 同上，平滑人为密度 `rho=rho0[1+0.01(x+0.3y+0.2z)/0.05]`。
3. 静止，初始均匀密度，`sigma=-0.4qI,p=0.6q`。
4. 同上，平滑人为密度。
5. `v=Lx`，`sigma=p=0`，初始密度，应力率梯度修正关闭。
6. 同一仿射场，应力率梯度修正打开。

`q` 从该初态 XML 读入，不新增生产参数。仿射场在 harness 内暂置 q=0，隔离导数消费者，不作为零外载实际 Cryer 测试。L=[[.7,-.3,.2],[.4,-.5,.1],[-.2,.6,.9]]，包含各向异性、非零XYZ、剪切、旋转和非零散度；应力为0，所以 Jaumann 的当前应力旋转贡献为0。

完整调用始终传入真实 `PorePressc/PorePressRatec`，不禁用孔压反馈；当前 `stinterparmsc` 没有 load 字段，生产函数直接写成员 `HydroMechLoadAcec`，harness 检查其非空并直接读取，不能虚构传参。

生产函数把 load 遥测写回放在非零总力/密度率/黏性等条件中。因此总力精确抵消时，full-call 的 load 遥测可能为0而真实外载非0。每个静止场额外作一次同几何/同密度 `sigma=p=0` 的真实 load-only 调用，取得独立 load；随后恢复原应力、孔压。summary/CSV 保留 full-call 遥测与独立 probe 的差，不修改生产写回逻辑，也不把遥测盲区误称为零外载。

每粒 CSV 给出 ID、坐标、密度、孔压、制造应力、真实总 Ace、两组 load、离线 A 的 double 算术参考、真实六分量 Rsigma、PoreRate、Arc 和目标值。静止场参考在同一 cell 邻居列表中计算 double Wendland 三项，并独立累加；不是生产 float 核与累加顺序的0ULP复制。真实总力/参考差、净力/矩、各率与目标 RMS 都实际计算，不把残差硬赋0，不人为设置新的物理通过阈值。

仿射场目标为 `2G sym(L)+lambda tr(L)I`、`-Kw/n tr(L)`、`-rho tr(L)`。Arc 是原始连续性离散，不要求它自动达到修正梯度精度。原始/修正应力率与孔压率的差异只是瞬时算子诊断，不是时间步收敛、解析精度或完整 Cryer 验收。

## 待审阅后的命令示例

```powershell
# 默认 CPU Debug authoritative solution 已单独构建后：
powershell -NoProfile -ExecutionPolicy Bypass -File tests/support/cryer_force_cpu_build_r1.ps1 -Configuration DebugCPU -Label dbg -ProductionBuildConfirmed

# 另选未占用的 run 输出目录；这里只调用静态 companion，无时间推进：
tests/outputs/cryer_force_cpu_r1_dbg/cryer_force_cpu_r1.exe -cpu -ompthreads:8 tests/outputs/cryer_start_r1/cryer_start_r1 tests/outputs/cryer_force_cpu_r1_run -dirdataout data
```

第二条使用保留的 startup 生成初态，不从其1ms最终状态重启。先由主代理绑定该生成 XML、初态 BI4、程序与运行命令；输出包含 `Run.out`、六个 CSV 和 `force_summary.json`。当前仅准备，尚未构建或运行。所有结果保留，若失败只报告并定位，不改守卫/源码、不重复运行覆盖。
