# 局部材料切线的真实非对称声学张量：离线审阅 r1

作者阶段仅新增 `support/c08_h18_material_tangent_review_r1.py` 和本说明，不运行/import、构建或调用材料、force、solver、native reader、VTK、Git。原材料组件已一次通过；根线程全文审读并单独准入后可运行：

```powershell
D:/anaconda3/python.exe -B tests/support/c08_h18_material_tangent_review_r1.py --execution-authorized
```

只消费 `logs/c08_h18_material_tangent_r1.check.json` 原绑定的实际call/build/program、completion和五份CSV。原组件10000个真实full trial的六应力、κ和分类等位门已通过；本轮不重复材料返回或原生校验。五份表应有 points14、branches1176、tangents7056、acoustic35476、summary196行。

## 完整保留与对照含义

两Part38/76、每态七个预先声明材料点、两law、七个strain scale `10^-5...10^-11` 共196个case全部保留。每case保留六列扰动、36个切线元素、0–180°共181个原始角度，以及原 `available` 和 `all_12_perturbations_same_branch`。不删除跨分支case、不因负数择优，也不将不可用case替换为弹性值。不可用输出仍为NaN/空派生栏并有显式flag。

`original_softening`是原演化材料；`frozen_strength_at_kappa_n`仅在相同κ_n冻结完整double DP系数，再使用原BasicValues和原apex/张拉政策。后者不是全程去掉软化的collapse对照；它的base状态也可能与原演化律不同。这里使用原试应力和固定历史，只是在材料骨架上作有限差分，不含邻域、AS、AV、孔压、Darcy、自由表面投影、接触或时间推进。

工程剪应变列为γ=2εij；原离线扰动使用Δσij=Gγij。xz平面声学张量原行列按实际Qxx/Qxz/Qzx/Qzz读取，不再构造新材料或连续模型。

## sym(Q) 与真正非对称 Q 必须区分

令 `Q=[[a,b],[c,d]]`，各项单位Pa，直接用原CSV复算：

```
t = a+d                                      [Pa]
det = a*d-b*c                                [Pa²]
Delta = (a-d)^2+4*b*c                        [Pa²]
```

`Delta>=0`时真实特征值为 `(t±sqrt(Delta))/2`；`Delta<0`时为复共轭对，实部均为 `t/2`、虚部绝对值 `sqrt(-Delta)/2`。不对Delta加epsilon、不夹成0、不把复数强行当实数。另保留 `t²−4det` 与上述Delta的浮点差，便于检查近零判别式的舍入敏感性；其符号仍是实际计算符号，不新增物理或稳定性门。

每case导出最小实部及角度、纯实负特征值数量（最多362个，181角各两个）、有纯实负值的角数、复共轭角数（最多181）、纯实特征值中的最小值，以及trace/det/Delta的极值和最大虚部。原 `minimum_symmetric_acoustic_Pa` 仍单独保留，绝不能把约−0.74MPa的sym(Q)值称为约−0.2MPa的真实Q特征值。

尺度比较只描述相邻十倍scale间的最小实部变化、以原正弹性G归一的绝对变化，以及完整6×6切线Frobenius变化/G。相邻两case的可用/同分支flags一并导出；不设自动收敛阈值，不宣称某个scale最优，不因branch跳变跳过记录。

## 当前ψ0 Smooth分支的条件性解释

本轮不增加材料调用、解析切线程序或新参数；以下仅解释固定φ、ψ0、同一Smooth分支且 `q_t>0` 的现有模型。令 `s_t=dev(σ_trial)`、`q_t=sqrt(s_t:s_t/2)`、`b=1−Gλ/q_t`，原返回为 `I_r=I_t, s_r=b s_t`。在不跨branch/endpoint的局部微分中，

```
dq_t = [s_t/(2q_t)] : dσ_trial
dλ = (dq_t + α dI_t) / [G + kc'(κ_end)/sqrt(3)]
dσ_r = (dI_t/3) I + b dev(dσ_trial)
       + s_t [-G dλ/q_t + Gλ dq_t/q_t²]
```

原软化使用返回末态κ的 `kc'`，冻结系数对照该导数为0。双点积中的非对角stress项应双计数；与工程γ扰动的 `Δσij=Gγij` 一起使用，不能混为少一个2的六维Euclidean点积。α不为0而ψ为0时，本来就是非关联流动，局部切线不必对称；冻结强度也不会自动变成关联材料。这一解释不适用于TensionRepair、apex或跨分支的有限差分，不证明负特征值是全耦合团聚原因，也不构成修改φ/ψ的建议。

## 两图、两份配套CSV

新目录 `tests/figures/c08_h18_material_tangent_review_r1`；检查为同名 `tests/logs/*.check.json`。已有完整或失败目录/收据均拒绝覆盖。

- `scales.csv`：全部196行，保留原summary各列、真实源时间、新真实Q谱统计及相邻尺度变化；原五表完整保留。
- `scales.png`：两Part×两law全部七点/七scale；实线是真实非对称Q最小实部，点线为sym(Q)最小值，下方flag面板保留每个点/scale的可用和同分支情况。symlog线性区1e−6MPa仅为显示，不是判断阈值。
- `focus_angles_e8.csv`：四focus IDs4953/4954/6767/6865、两Part、两law×181角，共2896行；记录原Q、sym(Q)、真实谱、trace/det/Delta、分支flags。`1e−8`是作者前预声明的展示切片，绝非自动择优；全部scale仍在196行表中。
- `focus_angles_e8.png`：2×4panel，原/冻结law的真实最小实部与sym(Q)分开画，另给原弹性G参照；复数角标x。symlog线性区0.01MPa仅显示，完整幅值不裁切。

有负真实特征值与仅有sym(Q)负值是不同结果；复谱也须另列。即使冻结强度后仍有负值，也只能说明“软化系数演化不是该局部条件信号唯一来源”，不能认定整个耦合系统失椭圆、物理张拉失稳或团聚的根因，更不能据此删除张拉cap或修改J/p。有限差分跨分支与小scale舍入需要一起审阅。本轮不引入undrained假设、TPI、β或新的连续扩散模型，也不自动启动任何新物理窗口。
