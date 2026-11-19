# Cryer 三维固定参考几何的 CPU 力学组件

私有模块 `tests/support/cryer_tet_mechanics.py` 读取已经过守恒核验的 `tests/outputs/cryer_tet_reference_r1.npz`。位移和速度以 37173×3 的土粒子数组输入，槽位与 `ids` 一一对应。以几何对偶体积 W 计算各点应变，惯性除数使用原生质量。三个一阶 CSR 矩阵 D 的每个条目都是邻接四面体形函数梯度的体积加权平均。应变及应力力共享同一个算子，分别为 B 和 −BᵀW。孔压作为 −pI 进入总应力；外载在真实边界三角形上积分。

```python
from cryer_tet_mechanics import TetMechanics
m = TetMechanics("tests/outputs/cryer_tet_reference_r1.npz")
eps = m.strain(u)
sigma = m.elastic_stress(eps)
fixed = m.internal_stress(sigma) + m.surface_force(q)
a = (fixed + m.pressure_force(p)) / m.mass[:, None]
theta = m.divergence(v)
```

`eps` 的顺序是 xx、yy、zz、xy、yz、xz，后三项为工程剪应变。应力相同顺序，后三项取物理剪应力。几何体积为 `m.volume`，原生体积为 `m.native_volume`。真实压力子步若固定端点位移、应力和外载，可以复用上述 `fixed`。给定加速度的散度可用 `m.divergence(a)` 计算，但实际 u-pl 压力源项使用哪种离散导数须由该项的定义决定。

## 验证结果

- 三个刚体平移和三个刚体旋转的最大绝对应变为 1.85×10⁻¹³，六个仿射应变制造场误差最大为 1.07×10⁻¹⁴。随机场的应力、孔压虚功误差分别为 4.00×10⁻¹⁵ 和 8.88×10⁻¹⁶ W。10 kPa 施加在闭合外表面，对单位膨胀速度场做功 −15.69026080 W，与 −3qV 一致；闭态平衡最大结点加速度 1.27×10⁻¹² m/s²。
- 对原生质量归一化的弹性刚度，以逐元绝对值构成的行和上界证得中心差分允许步长至少 46.810 µs。实际 1.90735 µs 为此值的 4.07%。第 17–18 壳的径向和角向交替位移，按势能与质量范数所得等效频率分别为 1616.1 与 1517.8 Hz。128 步无载角向自由脉冲的保存能量最大相对偏差为 0.01363%。这些检验仅覆盖线弹性组件，实际三轮压力反馈仍需另外校验。[守恒、稳定界与计时](../logs/cryer_tet_mechanics_component_r1.check.json) · [三个试验形态](../figures/cryer_tet_mechanics_component_r1_modes.csv) · [自由脉冲](../figures/cryer_tet_mechanics_component_r1_free_pulse.csv)
- CPU 单线程建稀疏矩阵耗时 2.73 s。预热后每次压力力约 1.41 ms、散度约 1.35 ms、弹性力约 13.41 ms。仅记录组件本机耗时；完整 CPU/GPU 求解还含压力、人工粘性和输出等工作。

## CUDA 对照用的单力阶段

`tests/support/cryer_tet_av_reference.py` 生成 `tests/outputs/cryer_tet_step_reference_r1.npz`，包含固定 q=10 kPa 的三维制造孔压、位移、速度、形变、应力、各项结点力以及总加速度。人工粘性按原压缩对处理，声速 35.8057440856 m/s、系数 0.1、Wendland H=0.0045 m、分母正则项 0.01H²。实际参考以双精度无序粒子对累加；生产 CUDA 中 float 路径和邻点累加顺序需通过量值对照。平移和纯膨胀为严格零力。混合速度场包含 1655519 对相互接近的粒子，总功 −0.0014579109355 W，净力模 2.73×10⁻¹⁶ N、净力矩模 9.61×10⁻²⁰ N·m。[人工粘性与基准索引](../logs/cryer_tet_step_reference_r1.check.json)

在 C04 根目录的无同名输出工作副本中执行下列检查可重新生成小型表格和可再生的 CPU 基准。

```powershell
& 'D:/anaconda3/python.exe' -B tests/support/cryer_tet_mechanics_verify.py tests/outputs/cryer_tet_reference_r1.npz
& 'D:/anaconda3/python.exe' -B tests/support/cryer_tet_av_reference.py tests/outputs/cryer_tet_reference_r1.npz
```
