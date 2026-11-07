# Retrogressive 算例塑性／软化实现历史定向审计

本记录只读核对 Git 对象、现存 XML、文字诊断和小型汇总 CSV；未运行／构建／解码／修改旧证据，未重新计算 SHA，也未遍历原始粒子输出。源码行号是本次读取时的位置；历史行号以指定 commit 的文件为准。本文不是对旧逆向滑坡或当前统一材料候选的物理验收。

## 结论

用户记忆的修改确实发生在 retrogressive 工作期间。最关键的详细记录在 `examples/Elastoplastic_basic/14_RetrogressiveSlopeFailure/diagnostic_records/`，而不是仅在现在的水土耦合 `03_RetrogressiveSlopeFailure_u_pw`。`79982b3` 虽名为 “Save state before yield trigger diagnostics”，实际还修改了软化历史范数、重启历史和应力散度，不能视为纯诊断提交。

旧 `ConsRelationEP_fast` 的 κ 使用偏塑性应变范数；软化 `ConsRelationEPsft_fast` 在 `79982b3` 后改成含体积塑性部分的流动范数。分母的 `+dfdk*h` 早在仓库初始提交就存在，并不是这次新引入或已通过一般一致性验证的符号。详细逆向滑坡诊断使用 `phi=dlt=0`，此时两个范数退化相同，不能用这些结果验证非零 ψ 下的历史选择。

## 可定位的提交链

| commit／日期 | 实际变化 | 精确定位与可靠范围 |
| --- | --- | --- |
| `1446112` / 2026-05-03，Initial working GeoDualSPHysics VS Code configuration | 已含 basic、soft 两个 fast 函数、指数 φ/c 演化、正号软化分母及 tensile/volumetric shift。此节点是本仓库可见起点，不证明这些公式由此作者原创。 | `src/source/JSphCpu.cpp@1446112`: `Updatedfdk` 1930；soft 函数 2061；`extra` 2117、`G+9Kαβ+extra` 2119。两个函数当时均从顺应性恢复塑性应变并去体积后积累 κ。`DualSphDef.h@1446112` 302–305 已有 `phi_r/coh_r/n_phi/n_coh`；365–368 是 DP_PS=3、DP_MC=2、DP_C=1。 |
| `a698ce5` / 2026-05-15，Align softened DP mapping with DPCtes | 软化系数原来固定使用 middle-circumscribed 映射，而导数使用 plane-strain 表达；改成 CPU/GPU 的系数和导数都按实际 `DPCtes` 分派，并把类型传入 soft 函数。没有改变加号分母。 | `JSphCpu.cpp@a698ce5` 2042–2089，特别 2068–2089 的 φ/c 导数；2268–2270 仍 `+extra`。同提交 `JSphGpuSimple_ker.cu` 同步。它修复的是系数／导数映射一致性，不是三维材料路径已验证。 |
| `5d9fd84` / 2026-05-22，Add CPU soil softening and artificial stress controls | CPU Verlet、Symplectic Pre/Cor 从无条件 basic 改为 `StrainSoftening ? soft : basic`。只有存在相应 residual 节点且 `n_phi>0` 或 `n_coh>0` 才启用 soft。`dlt` 从 XML 度转换为弧度；新增 `SoilTriggerFos`，重启 soft 阶段把 peak cohesion 除以该值（不同比例缩放 residual）。加入 Sigma/Kplastic PART 继承。 | `JSph.cpp@5d9fd84` 3337、3342–3347；`DualSphDef.h` 新增 `SoilTriggerFos`。`JSphCpu.cpp` diff 的 Verlet、Pre、Cor 三个调用；Pre 仍恢复旧 κ，仅 Cor 正式更新。`JPartsLoad4.cpp` / `JSphCpuSingle.cpp` 负责读取和复制旧状态。 |
| `0d70118` / 2026-05-22，Sync GPU soil softening restart path | GPU 常量增加 soft/restart 标志，三个积分调用接入实际 soft；GPU 重启复制 Sigma/Kplastic。 | `JSphGpu.cpp::ConstantDataUp`，`JSphGpuSimple_ker.cu` 三个 dispatch 与 `CteInteractionUpTStep`，`JSphGpuSingle.cpp::ConfigDomain`。此时函数存在和路径真正启用是两个不同历史节点。 |
| `79982b3` / 2026-05-24，Save state before yield trigger diagnostics | soft 的 κ 更新从显式恢复的 dev 范数改为 `dlambda*dkflowcoef`；CPU/GPU 同步。basic 仍保留 dev。重启从继承 κ 改为清零 κ、只继承 Sigma。另有应力散度、mDBC 调度／默认值及诊断输出修改。 | `JSphCpu.cpp@79982b3`: basic 2769–2776；soft 2859–2862、2886；GPU 同文件函数段 353–356、380。`JSphCpuSingle.cpp` / `JSphGpuSingle.cpp::ConfigDomain` 的 `memcpy(Kplastic,...)` 改 `memset(...,0)`。不能把此整个提交的场结果差异只归因于 κ 范数。 |
| `e8e6fab` / 2026-10-20，Verify CPU/GPU double-stress, band-load and HG/SPR 2Tv delivery | 应力／部分局部算术改 double，材料常数、DP 系数与持久 κ 仍 float；soft 的 full 范数、正号分母、旧 κ 系数投影均保留。 | `JSphCpu.cpp` 和 GPU simple diff 可直接看见 `float extra/dlambda` 改 double、`tk=float(double(tk)+dk)`；不能把后来差异统称全 double 材料模型。 |
| `369e244` / 2026-11-06，Add opt-in consistent plane-strain material return with dilation decay | 新增显式选择的 ConsistentDev 路径；它与上述旧 MR0 实现是独立算法／模型约定，不是此前 retrogressive soft 函数的简单改名。 | 当前 `FunSoilMaterial.h`；当前 `JSph.cpp` 3972 附近的 selector 和 4076–4085 的窄准入。后续统一候选仍须分别验证，不能借旧 dry 结果代替。 |

## 数学含义与现存代码

记 `f=q+αI−kc`、`g=q+βI`，`q=sqrt(J2)>0`。当前旧函数位置：CPU `JSphCpu.cpp` 3812–3859（系数／导数）、3861–3981（basic）、3983–4091（soft）；GPU `JSphGpuSimple_ker.cu` 130 附近至 182、185–306、308–416。对规则塑性方向：

- dev 历史：`dκ=sqrt(2/3 dep_dev:dep_dev)=dλ/sqrt(3)`；basic 的 CPU 3940–3948／GPU 265–273 确实先去体积。
- `79982b3` 后 soft：`h_full=sqrt(1/3+2β²)`，`dκ=dλ*h_full`；当前 CPU 4031–4034、4058–4059／GPU 356–359、383–384。这不是仅消除一次逆弹性计算的代数优化：ψ≠0 时改变了历史变量及指数率的标定含义。两者之比 `sqrt(1+6β²)`；ψ随历史改变时也不能一般靠一个固定 `n_coh` 比例等价换算。
- 当前 `Updatedfdk` 的实际定义是 `fκ=I*ακ−kcκ`（CPU 3859、GPU 182），并没有把它命名为负导数。固定 φ、cohesion 递减时 `fκ>0`。按相同 dλ、正的历史增量，从一阶一致性 `0=ftrial−(G+9Kαβ)dλ+fκ*h*dλ` 得分母 `G+9Kαβ−fκ*h`。历史代码却用 `+fκ*h`。这是可直接复核的约定差别，不能用“softening modulus 自带负号”消掉；也不能据此把所有空间局部化都单因归于该符号。
- φ/c 旧律分别是 `φr+(φp−φr)exp(−n_phi κ)`、`cr+(cp−cr)exp(−n_coh κ)`。ψ旧 fast 内为常量 `MC_psi`，没有 `sf` 衰减输入。`n_phi` 与 `n_coh` 不是同一个率；`SoilTriggerFos` 是重启 peak 强度降低，不是软化率。
- 映射：DP_PS 使用 `α=tanφ/sqrt(9+12tan²φ)`、`kc=3c/sqrt(9+12tan²φ)`，β对ψ同式；DP_MC 用 `2sinφ/[sqrt(3)(3+sinφ)]`、`6c cosφ/[sqrt(3)(3+sinφ)]`；DP_C 把分母改为 `3−sinφ`。旧实现的 `sqrt(3)` 为 `1.732f`。φ=0 时 PS 的 kc=c，而两种3D映射约为 `2c/sqrt(3)`，所以旧 notes 的约1.1547倍强度效应确有代码依据；这不等于改变映射是合适的本构校准。
- 旧后处理投影在 κ更新之后，仍用进入函数时按旧κ计算的 α/kc：CPU basic 3952–3969、soft 4062–4079；GPU 277–294、387–404。先将 `I>kc/α` 的 mean 拉回 tip，再径向缩放 dev；额外修正没有一致回写塑性历史。它不是一般非关联 DP 顶点返回算法。`79982b3` 只是给 `fscale` 的 `J2=0` 除法加条件，未消除 `kc/α` 在α=0时的退化问题；φ=0、c>0 的旧检查不覆盖有限摩擦锥 apex。

## 历史实算究竟支持什么

1. `14_RetrogressiveSlopeFailure/diagnostic_records/SensitivityNotes_RetroSlope_Bui2021.md` 已完整读取。84–133 行：旧 GPU 5s、11275 soil 的参数敏感性，baseline `n_coh=5/cr=1500`：κ>1 为15.46785%、κp99=9.19623、最大 tensile principal stress=75068.10Pa；n_coh2 降到11.02439%、8.35518、61430.55Pa，cr3000 的κp99=7.67464。其 `SofteningRegularization_summary.csv` 与表相符，但 notes 131–133 和366–380明确很多 XML/BAT/log/output 及诊断 hooks 后来已删除，不能假装完整程序／输入身份仍可复现。
2. 同 notes 135–208 与 `ReturnMappingDiagnostics_summary.csv`：5s 的1901/11275个低J2高κ粒子，median trial J2=5690008.5、final=2250019.75Pa²，median trial f=805.06885Pa、当次 dκ=5.540496e−5；所存 cap/scale 计数为0。它支持当时这些残余带不是由记录到的 tensile cap／最后scale直接触发，不支持一般 apex 算法正确。其初次 residual crossings CSV 保留原 Idp，notes 186–195 给出的1901个ID排名关系是历史后处理结果，本审计没有重读原VTK复算。
3. `SoilDk_diagnostic_2026-05-24.md` 11–14 定义的 SoilDk 是**输出间隔内**正 κ增量累计；39–46 的0.346–0.472跨0.1s，不能与上条单步5.54e−5直接比较。`79982b3` GPU simple 545／932行只在实际 Verlet／Cor 累加，Pre 703行恢复旧κ；SaveData之后清零累计。这个文件“does not alter stress update”只描述诊断量自身，不能证明整个79982b3是无数值变化提交。
4. `yield_trigger_diag/README.md` 18–32：2.4–3.5s active median old f≈3.33e−5Pa、trial f≈2.07kPa、corrected f≈2.31e−5Pa，两个 dλ估计最大差约4.3e−10；`stressrate_diag/stressrate_diag_summary.md` 19–21提出局部应力率／转动噪声假说。这些是诊断解释，并非具有路径真值的材料积分验证。尤其φ=ψ=0、许多热点已到cr附近使 `fκ≈0`：不能据其“分母没有明显过放大”推论所有软化率、剪胀、摩擦软化或 fκ符号均正确。
5. 同 SensitivityNotes 281–308 的 gradient correction 5s排除22粒子，382–412 另一 mDBC调度试验排除17（全RhopOut）；不能把这些方案写成通过。Dk cap／soft-rate scale虽然曾无排除，视觉检查后未解决逆向裂带，hooks被移除（310–380）。文字仍有早期“保留”与后续“删除”的迭代描述，应以后续cleanup为准。
6. `CHANGES.txt` 15–16、29–41仍写“继承Sigma和Kplastic”、4s CPU/GPU一致性及删除临时对照。这是较早阶段的摘要；已被79982b3的**清零κ重启**源码改动覆盖，不能用它描述当前generic restart，也不构成对非零ψ的full/dev历史比较。该提交还同时把应力散度从 `mj(σi+σj)/(ρiρj)` 改为 `mj(σi/ρi²+σj/ρj²)`，当前全流程差异有额外混杂。

## 当前 H03 与后续工作边界

`03_RetrogressiveSlopeFailure_u_pw/README.md` 7–16、20–24、71–76清楚记录：当前coupled prestress/failure两阶段、φ=ψ=0、cp25000/cr1500/n_coh5/FOS1.65；prestress h/dp1.5 与failure2.16不一致尚未核物理。现存 XML failure 90–104行亦证实没有摩擦／剪胀软化试验。它和5月 dry case14不能冒称同一完整物理设置。

H03 `tests/logs/stress_r1_03failure_cpu.json` 记的是200步、11帧至0.00019999999999999955s、solver/reader各exit0、无排除，`stress_r1_03failure_cpu.compare.json` 明示 `physical_verdict=not_assigned`、CPU导出不逐位相同；`bc_r1_03failure_gpu.compare.json` 的11帧已导出字段相同也同样不指定物理结论。`rotation_r2_03failure_cpu_after.json` 明示 short execution passed / physical acceptance pending。这些是边界、转动／精度修改的短回归，不是旧软化、本构标定、hot restart或全程坡体失稳验证。

因此此次材料统一应保留历史事实：之前已经做过大量空间敏感性诊断，不需为确认其存在而重跑；但那些证据不能决定非零ψ下full/dev κ谁更物理，也没有证明一般φ软化／顶点路径。后续同一模型的时间积分对比与模型／标定选择应分开，和本次已闭合的 `upl_material_path_r1` 一样明确真实 legacy sft 与 production basic 的区别；不把更小局部屈服残差自动写成更高物理精度。
