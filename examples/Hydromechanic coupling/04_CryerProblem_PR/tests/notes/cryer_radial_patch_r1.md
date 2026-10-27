# Cryer：非均匀球对称静态场离线筛查

## 范围和产物

仅新增 `tests/support/cryer_radial_patch_r1.py` 与本说明，先供审阅；默认调用只显示帮助，不读取原生数据或生成结果。经审阅后显式使用 `--run`，输出新的 `tests/logs/cryer_radial_patch_r1.check.json` 和 `tests/figures/cryer_radial_patch_r1_metrics.csv`，拒绝覆盖同名证据。没有求解器、编译、生产代码、正式 XML/BAT、已有结果或 Git 操作。

几何只取已完成 `cryer_grad_peak_r1` 的 Part0：double 保存坐标、原生质量、初始 rho=2100 kg/m³、h 和全部37173土粒子ID。中心是初始 `r<=dp+1e-12 m` 的固定18个ID；其余分区为 `r<R-2h` 内区、互补外壳以及真实初始 FSType2/3 表面。中心没有 r=0 原生节点；连续场在原点仍用光滑极限定义。所有组使用完全相同邻居、质量、密度、h，不改布局、求积或总力归一化。

复用已封存 `cryer_load_pair_r1.py` 的分批邻居、矩阵、A/C/D三项分别累加及力/功统计；不修改旧 helper。绑定本脚本、说明、helper、跨case Lian reader及源码、Part0、峰窗身份记录/配置、当前程序和相关生产源码、当前实际 u-pw 原文和 Zhao2019 PDF/MD 的SHA256。当前程序只作身份绑定，不在本阶段执行。

## 独立推导的连续静态场

拉应力为正，总应力 `T=S-pI`，球半径 a=R=.05 m，外部压力 q=10000 Pa。材料 E=2e6 Pa、nu=.3，`K=E/[3(1-2nu)]`，`G=E/[2(1+nu)]`，`lambda=K-2G/3`，`M=K+4G/3=lambda+2G`。

对 `P/q=0,.6,1.2`：

```text
p(r) = P(1-r²/a²)
C = [-3 M q+(8/5) G P]/(3 K)
u/r = (C+P)/(3 M)-P r²/(5 M a²)
u'  = (C+P)/(3 M)-3 P r²/(5 M a²)
eps_v = (C+P-P r²/a²)/M = u'+2u/r
Srr = 2G u'+lambda eps_v
Stt = 2G u/r+lambda eps_v
```

令 `H=4GP/(5M)`，直接化简得到 `Trr=-q-H+H r²/a²`、`Ttt=-q-H+2H r²/a²`。故 `dTrr/dr+2(Trr-Ttt)/r=0`、`Trr(a)=-q`、`p(a)=0`。在笛卡尔坐标，`u=[(C+P)/(3M)-P|x|²/(5Ma²)]x`，`T=[-q-H+2H|x|²/a²]I-H xxᵀ/a²`，原点光滑，没有除r奇异性。场对P线性；P=0退化为 `p=0,S=T=-qI,u=-qx/(3K)`。

脚本分别按位移应变/Hooke公式构造S，并与上述独立多项式核对，检查边界牵引、迹、P线性及P=0常应力极限。这些浮点代数自检不是离散力精度门槛。

## 四种离线力定义与观测

沿用旧 helper 的A原始力、B只修正外载、C三项接收点C一致扩展、D成对负伴随扩展，定义未改。每个变体均独立累加应力、外载、负孔压，再实际求和，包括P=0；不把应当为零的连续或均匀结果直接赋0。

每个P/变体/分区输出分量RMS、粒子向量RMS、体积加权向量RMS和向量最大残余加速度，以及该分区原生半径和制造孔压范围。初始FSType2/3只定义一个统计分组，不把其中所有节点的制造孔压硬设为0；连续排水面在r=a，若原生检测表面包含更内层节点，强制改写孔压会破坏本静态解析场，这项差别应单独辨认。连续真加速度为0，但二次应力场不必被离散SPH在截断/非均匀邻域上精确重现；不设一个使D自动通过的新零误差门槛。CSV中的D/A等比率用来判断局部残差是否真的降低，而不能仅凭全局净力/矩小就判为改善。

JSON另保留总残余及独立外载的净力、力矩、径向量、仿射功和内核体积权重比例；几何球体积与原生 `sum(m/rho)` 的归一化并列。D对 `Ttilde=S+(q-p)I` 的离散仿射功应与 `-sum(V Ttilde:L)`比较，独立外载预期为 `-q tr(L) sum(V)`；不能强制换成理想几何球体积。功差仅如实记录，不替代局部误差或连续牵引检查。

C不是Zhao干土原文的完整复现，D也不是已实现/验收的方法。离线全double和舍入Wendland常数不等同生产float核、邻居次序或瞬时耦合实跑0ULP；不据此宣布新物理方案通过。

## 审阅后执行

```powershell
D:/Anaconda3/python.exe -B tests/support/cryer_radial_patch_r1.py --run
```

只进行一次约340万邻居对的分批离线累加，无每粒子大输出、图、时间积分或后续自动任务。分析自检通过仅表明本脚本按声明完成，`physical_acceptance`始终为false。
