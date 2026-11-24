# 变渗透率 TPI 和使用初始渗透系数的扩散步长

显式 u-pl（`HydroMechModel=1`）和三轮 TPI（`HydroMechModel=2`）共用下列渗透系数配置。`HydraulicConductivity` 给出初始值 $k_0$。省略 `HydroMechConductivityModel` 时为常渗透率；设为 1 并指定正值 `HydroMechConductivityCk` 时，每个粒子使用 $k_i=k_0\exp[(J_i-1)/((1-n_0)C_k)]$。$C_k$ 是材料参数。

两种积分的扩散步长估计均为 `PoreDtSafety × h² / max_i[Kw k0 / (n_i γw)]`。TPI 在这个估计上乘 `HydroMechTpiR`。波速仍使用当前材料状态，渗透系数梯度仍独立限步。如果局部渗透系数大幅超过初值，此估计可能高于用实际最大扩散率得到的步长，需要检查该工况的稳定性。

对光滑的变渗透率场，三轮 TPI 各自用当前的 $k_i$ 乘主扩散项，并在残差中计入 `grad(k) · (grad(p) + rho_w a)`。迭代对角系数也使用接收粒子的 $k_i$。此实现沿用已有的光滑场展开；渗透率跃变的材料界面需要独立处理。

## 实现验证

- 在 VS x64 开发环境中运行 `tests/support/tpi_k0_step.py`。8 组步长算例直接调用 Release 求解器代码。在同一变形场中，CPU/GPU 显式扩散上限均为 8.201925 µs，TPI 取 $R=2$ 时为 16.403850 µs。强梯度把两者都限制为 0.800000 µs，两端共拒绝 4 次超限固定步长。[步长结果](../logs/tpi_k0_step_r1.json)
- `tests/support/tpi_variable_k_rows.py` 用已知压力、加速度和体积比场逐行核对实际 CPU/GPU 压力算子。端点压力最大误差分别为 0.00000743 Pa 和 0.00003138 Pa。省略梯度项在针对该项构造的算例中至少产生 0.7556 Pa 误差。[逐行结果](../logs/tpi_variable_k_rows.json)
- `tests/support/tpi_variable_k.py` 在 C02 周期加载柱和 C04 Cryer 围压球体上测试实际程序。记录包含常渗透率归档回归、局部渗透率与材料体积比的一致性、三轮压力历史和同一物理模型的 CPU/GPU 对照。[算例结果](../logs/tpi_variable_k_r1.check.json)
- C08 显式 u-pl 撤墙回放了 2001 步。CPU、GPU 各自的 6 帧、6805 个粒子的全部 22 个原生数组与同后端归档逐字节一致，末帧有 174 个土粒子的累积塑性量大于零。`dterror` 记录新的步长裕度。此回放覆盖已有显式预载交接及塑性路径。[CPU 记录](../../../08_LianSaturatedColumnCollapse_u_pl/tests/logs/k0_step_explicit_r1_cpu.json) · [GPU 记录](../../../08_LianSaturatedColumnCollapse_u_pl/tests/logs/k0_step_explicit_r1_gpu.json)

| 变渗透率 TPI 算例 | 原生保存范围 | CPU/GPU 最大逐帧孔压 RMS 差 | CPU/GPU 最大材料点位移差 |
| --- | --- | ---: | ---: |
| C02 加载柱 | 2004 步、131 帧，至 0.01002022934 s，含排水开启后的 4 帧 | 0.00555723 Pa | 6.79258 × 10⁻⁸ mm |
| C04 Cryer 启动 | 32 步、5 帧，至 0.00006103515625 s | 0.000007275 Pa | 9.97437 × 10⁻¹³ mm |

C02 短窗中，同一后端 TPI 的常、变渗透率孔压 RMS 差最大为 0.00691 Pa（CPU）和 0.00850 Pa（GPU）。在相同的变渗透率输入下，三轮 TPI 与有限储水显式 u-pl 的启动孔压 RMS 差最大约 1308.30 Pa。此值比较了两种压力方程。原常渗透率 TPI 在 C02 的 25 步和 C04 的 4 步均复现了各自后端归档的全部 22 个数组、时钟和压力历史。[逐帧保存时钟](../logs/tpi_variable_k_r1.clocks.csv)
