# C08 H1.8 shifting 兼容性只读审计

本记录检查当前工作树的既有 CPU/GPU shifting 与 u-pl 状态更新，不修改源码、正式输入或冻结程序。它不是一个新的 shifting 试验，也不证明现有团聚或自由表面 gap 的因果来源。根线程已授权仅新增本记录；未运行求解器、原生读取器、分析、构建、VTK 或 Git，未扫描 SHA。

## 当前结论

不能直接在 C08 XML 打开旧 shifting，也不应通过删除兼容性 guard 强行运行。旧实现把额外位置位移加入 corrector，但没有配套的孔压、J、速度、应力或塑性历史输运。当前 u-pl 和 C08 container 两层准入明确排除 shifting。这些限制有实际数值含义，不能视为尚未清理的无用接口。

本审计针对的 C08 背景为 Wendland、dp=0.04 m、hdp=1.8、固定 5 us、已有真实 schema2 PRE、释放后变 J/n/k、AS 与固定平面 NoPen。RV 的运行及物理结论由其独立 run/native/review 记录承担；本记录不重新验收或替代它们。

## 旧 shifting 的实际计算

以下行号是本次只读审查时的当前工作树行号，未把当前源码冒认为旧冻结二进制的完整编译来源证明。

- CPU 邻居累加在 `src/source/JSphCpu.cpp:2511–2517`；GPU 对应在 `src/source/JSphGpu_ker.cu:2035–2042`。
- 最终缩放和裁剪在 `src/source/JSphShifting.cpp:388–416`；GPU 对应在 `src/source/JSphShifting_ker.cu:123–149`，主机参数在 `JSphShifting.cpp:461–467`。

令代码的 `dr=r_i-r_j`、`fr=grad_i W_ij`，则累计量为

```
g_i = sum_j (m_j/rho_j) grad_i W_ij
s_i = -sum_j (m_j/rho_j) (r_i-r_j) dot grad_i W_ij
delta_r_i = C_shift * dt * h * |v_i| * g_i
```

`ShiftCoef` 默认值为 -2。若 `ShiftTFS=T` 非零，`s_i<T` 时将缩放置零，否则再乘 `(s_i-T)/(d-T)`，其中 d=2 或 3。这里没有额外将该因子截到 [0,1]。最后 **每个坐标分量** 独立限制在 `[-0.1dp,+0.1dp]`，不是向量范数限制。

### 自由表面和墙面

这条路径没有读取 `FSType` 或 `FSNormal`，没有把位移投影到自由表面切平面，也没有统一的墙面切向投影。

`SHIFT_NoBound` 或 `SHIFT_NoFixed` 遇到相应的边界邻居后，用 `FLT_MAX` 停止该目标粒子的整个 shifting。`SHIFT_Full` 则仍累计边界项。它们不是“仅移除墙面法向分量”。浮体还存在明确停移逻辑。参见 CPU `JSphCpu.cpp:2229,2291,2511–2517` 和 GPU `JSphGpu_ker.cu:1815,2035–2042`。

因此，自由表面附近被标量支持度停移或弱化，而内部继续移动，以及近固定墙整片停移与内部继续移动，均可能造成相对法向重排或过渡层间距问题。这说明用户观察到 gap 有需要检查的代码机制，**不等于已经证明当前 gap 正是由该机制引起**；C08 当前运行中 shifting 关闭。

## 加入时间积分的位置和缺失的输运

CPU/GPU 的 Symplectic 总流程分别在 `JSphCpuSingle.cpp:897–925` 和 `JSphGpuSingle.cpp:807–836` 附近：predictor 和 corrector 的力计算后会计算 shift scratch。但实际 predictor 的局部开关固定为 `shift=false`，见 `JSphCpu.cpp:3419`、`JSphGpu.cpp:1748`。

Corrector 则直接执行

```
dx += ShiftPosfs[p].x;
dy += ShiftPosfs[p].y;
dz += ShiftPosfs[p].z;
```

位置见 CPU `JSphCpu.cpp:3660–3663`、GPU `JSphGpuSimple_ker.cu:736–741`。该额外位移并未成为所提交物理速度的一部分，也没有对应的速度 Taylor/ALE 输运修正。应力仍使用原 force-stage `R_sigma` 完成材料返回，塑性历史仍由该返回提交；孔压仍按原孔压率更新。

J 的 predictor/corrector 仍只有 `Jdot=J*theta`，其中 theta 来自物理速度散度，见 CPU `JSphCpu.cpp:3295–3327`，GPU `JSphGpu.cpp:1990–2000` 的共享更新调用。n、体积、混合密度和变 k 从该 J 派生；它们没有因为额外重排位移得到统一输运修正。因此仅打开位置 shift 会改变邻域与几何，同时保留原材料场和历史，不能自动解释为一致的 u-pl 离散。

### 体积权重还存在一处非同一性

旧 shift 的权重为固定原质量 `m0/rho(J)`，而当前 u-pl 的积分体积为 `V0*J`。在当前混合密度关系

```
rho(J) = rho_w + (rho0-rho_w)/J
m0 = rho0*V0
```

下，二者之比为

```
(m0/rho(J)) / (V0*J) = rho0 / (rho_w*J + rho0-rho_w)
```

一般不严格等于 1。当前 J 波动较小时差别可能不大，但兼容扩展时仍须明确使用哪一套体积规则；这不是当前团聚的已证主因。

## 现有明确 guard

1. CPU `JSphCpu.cpp:3110–3113` 的 `InitPorosityObserverCpu()` 因 `Shifting` 拒绝进入；GPU `JSphGpu.cpp:1941–1948` 的 `InitPorosityObserverGpu()` 对应拒绝。
2. `JSph.cpp:3829–3844` 的 `IsDynamicPoreContainerConfig()` 自身要求 `!Shifting`。它参与 C08 动态塑性/container 能力准入；因此只删除 observer 中的拒绝仍不能形成完整支持。

当前共享 PRE/receiver 契约和原生审查不能证明一个绕过上述 guard 的位移重排方案正确。新 release-only 重排若被开发，必须有明确的新能力范围、状态继承与接收契约，不能改写旧 PRE 标签、旧材料 ID 或历史来伪造兼容性。

## 干粘性土参照的实际范围

`examples/Elastoplastic_basic/08_CohesiveGranularCollapse` 的 `CaseCohesiveGranCollapse2D_ASCoef03/05/07_Def.xml` 和对应 3D AS 比较配置均为 `Shifting=0`。这些 AS 对比的良好形态不能作为“动态孔压/变孔隙/变 k 下 shifting 已验证”的依据。

该目录旧通用 `CaseCohesiveGranCollapse3D_Def.xml` 有 `Shifting=3`；这只说明旧基础干土入口存在启用示例，不能替代本 C08 的 u-pl 兼容性和历史输运验证。本次未把任何旧案例重跑。

## 下一步最小信息和完整候选合同

无需新求解即可先在现有保存态计算旧 shift 候选位移，特别是团聚反转前后的 0.40–0.45 s 和后期保存点，记录：

- 全部固定材料 ID 的位移及其对真实新近对距离的一阶改变；
- 真实自由表面点的法向位移、近墙位移以及由停移/弱移形成的相对间距变化；
- 原 `m0/rho` 与 `V0J` 体积权重的差别；
- 位移散度所暗示的几何体积变化与未改变 J 的差别。

这只是冻结保存态上的候选响应，不是未保存子步的重演或重排后的真实物理轨迹，不能据此宣称修复成功。

若上述诊断支持继续开发，最小完整方案至少须明确定义：

1. 重排速度/位移与物理速度的关系，墙面和自由表面的允许方向及有界过渡，避免只用硬停移造成新的间距断层。
2. 位置重排所对应的场输运。若粒子改为以 `v+w` 移动，则一般场的导数包含相应的 `w dot grad(field)`，不能只给位置加位移；离散方式和符号须按最终重映射定义一致推导。
3. J/n/rho/k 的一致性，以及压力、速度、六分量有效应力和塑性历史的有界、守恒或明确误差预算的重映射。塑性不可逆性不能靠重置 kappa 或只加一个无约束 Taylor 项替代。
4. 固定 P0、初始参考场、材料 ID 和“固定材料点历史”的解释。重排后若 ID 不再代表同一物质点，应明确改变分析语义；不能仍把重排轨迹当原拉格朗日材料轨迹。
5. PRE→receiver 的 release-only 能力契约、CPU/GPU 对接、默认 OFF 回归、必要 native/ledger/边界/时步门和可观察的输运误差。

本记录不放宽任何现有 guard，不选择新的 shift 参数，不启动下一求解器或解锁另外两组 psi。
