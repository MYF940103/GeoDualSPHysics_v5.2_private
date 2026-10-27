# Cryer有限水体积模量：独立准静态线性参考

只新增本说明及 `logs/cryer_finite_storage_r1.check.json`。未修改旧理论脚本、曲线、求解器、正式输入或验收门；未运行物理求解器或Git。本记录给出可供新分析标签使用的数学参考，不是动态SPH程序的精确真值，不自动验证预载或准入长计算。

## 1. 假设、符号和源码对应

均匀、各向同性、小应变线弹性球，半径a；固体颗粒不可压、Biot alpha=1、固定孔隙率n和参考水密度，储水模量 `Mf=Kw/n`。拉应力/体积膨胀为正，总应力 `T=S-pI`，表面恒定压牵引 `Tn=-q n`；排水开始后 `p(a,tau)=0`。忽略惯性、人工黏性、数值阻尼、有限变形和离散误差。

主文MD的有限Kw假设与式11–12保留 `n/Kw` 储水，4.2的式46–47则明确采用不可压流体/固体极限；不能把后者不加说明地当作有限Kw精确参考。CPU `JSphCpu.cpp` 2449–2488及GPU `JSphGpu_ker.cu` 1826–1836在无重力、默认压缩源下对应 `pdot=Mf(-div v+k/(rho_w g) lap p)`。这里的Laplacian是连续算子，不把SPH离散求积等同其精确实现。

## 2. 平衡、储水和初值的独立推导

定义 `K=E/[3(1-2nu)]`、`G=E/[2(1+nu)]`、`H=K+4G/3`、`beta=4G/(3K)`、`kappa=k/(rho_w g)`。球对称平衡及正则原点给出

```text
H eps_v=p+C(tau),
u(r)=r^(-2) integral_0^r eps_v(s) s² ds,
Trr=C-4G u/r.
```

令 `pbar=3/a³ integral_0^a p r²dr`，利用 `Trr(a)=-q` 可得

```text
C=-Hq/K+beta pbar.
```

有限储水质量守恒是 `pdot/Mf+eps_v_dot=kappa lap p`。一般加载历程满足

```text
A pdot+beta pbardot=Cv0 lap p+(H/K) qdot,
A=1+H/Mf, Cv0=H k/(rho_w g).
```

因此保持q恒定后，准确约化为

```text
pdot+beta_eff pbardot=Cv_eff lap p,
beta_eff=beta/A, Cv_eff=Cv0/A.
```

封闭均匀预载时lap p=0，故 `(A+beta)pdot=(H/K)qdot`，给出

```text
Ku=K+Mf, B=Mf/(K+Mf),
p(0-)=Bq, eps_v(0-)=-q/Ku,
S(0-)=-(1-B)q I, T(0-)=-q I.
```

这也由总体fluid content `zeta=eps_v+p/Mf` 为0直接得到。排水开启后的初值是在内部 `p(r,0+)=Bq (r<a)`，但边界 `p(a,tau)=0 (tau>0)`；角点初边值不相容是经典扩散启动，不应把native初始0孔压或已排水ramp后的非均匀场替换成这个初值。

## 3. 模态、根和闭式系数

取 `s=r/a`、`theta=Cv_eff tau/a²`、`sinc(z)=sin(z)/z`且sinc(0)=1。每个正根满足

```text
(1-eta_eff xi²/2) sin(xi)=xi cos(xi),
eta_eff=2(1+beta_eff)/(3 beta_eff)=H/(2GB).
```

模态 `f_j(s)=sinc(xi_j s)-sinc(xi_j)`，而不是单独sinc；后者不满足表面零孔压。令 `m_j=bar f_j`，广义储水内积为

```text
<f,g>_B=3 integral_0^1 f(s)g(s)s²ds+beta_eff bar f bar g,
m_j=3[sin(xi)-xi cos(xi)]/xi³-sinc(xi)=sinc(xi)/beta_eff,
N_j=<f_j,f_j>_B
   =3/(2xi²)-3sin(2xi)/(4xi³)-(1+1/beta_eff)sinc(xi)².
```

均匀初值Bq投影系数 `a_j=B(1+beta_eff)m_j/N_j`。其中心幅值独立化简为

```text
c_j=a_j f_j(0)
   =B eta_eff [sin(xi_j)-xi_j]
     /[eta_eff xi_j cos(xi_j)/2+(eta_eff-1)sin(xi_j)].

p(r,tau)/q=sum_j c_j
  [sinc(xi_j r/a)-sinc(xi_j)]/[1-sinc(xi_j)]
  exp(-xi_j² theta).
```

所以“旧同形中心系数将eta换为eta_eff，再整体乘B”确实成立；但Cv也必须换为Cv_eff。不能只缩放初始孔压或只换一个参数。

## 4. 物理参数与峰值

本次按指定物理常量计算，不冒称GPU float常数逐位相同：E=2e6Pa、nu=.3、Kw=2e8Pa、n=.3、k=1e-5m/s、rho_w=1000kg/m³、a=.05m、q=10000Pa、g=9.80665m/s²。

```text
K=1666666.6666666665 Pa, G=769230.7692307692 Pa,
H=2692307.692307692 Pa, Mf=666666666.6666667 Pa,
B=.9975062344139651, A=1.0040384615384614,
beta_eff=.6129094043286728, eta_eff=1.754375,
Cv0=.0027453898041713454 m²/s,
Cv_eff=.00273434724797759 m²/s.
```

360根、连续时间数值优化（末位会受优化容差影响）：

| 观察位置 | 峰p/q | 峰p/(Bq) | 峰theta | 峰tau/s |
| --- | ---: | ---: | ---: | ---: |
| 真中心r=0 | 1.245080884762 | 1.248193586973 | .046338262232 | .042366841178 |
| r=.05a | 1.243917595969 | 1.247027389959 | .045993691656 | .042051802025 |

对应原Cv0尺度 `Tv0=Cv0 tau/a²=A theta` 分别为 .046525397522、.046179435411。新图应明确theta/Tv0定义，不能无说明更换横轴或把第一个已开排水保存帧再平移成tau=0。固定18个中心材料ID初始r/a=.05，对比其平均应使用有限半径参考，真正r0可同时显示。

## 5. 独立自检与极限

直接使用广义储水内积、240点Gauss积分重建前12个系数，与闭式中心系数最大差6.84e-12；前360根的缩放根残差<=2.62e-13，模态储水约束差<=1.64e-14。另已做一次独立球对称P1质量/刚度矩阵广义特征值数学核对（400/800单元、80模态，未创建FEM或求解器文件，非SPH物理运行）；峰误差随加倍网格约4倍收敛，800单元对级数中心峰差.02923Pa、r=.05a差.01680Pa。没有额外开展新case或物理求解。

短时必须增大根数：16384根时theta=1e-6/1e-7/1e-8的中心p/q分别约.998789545195/.997912018729/.997634551243，趋向B=.997506234414；表面始终0。有限根数直接代theta=0不代表初值极限。长时首根xi=2.671733348716主导，全部内部压力衰减至0，无理论平台。Mf趋于无穷时B→1、A→1、eta_eff→H/(2G)=1.75、Cv_eff→Cv0；用Mf放大1e9数值核对，中心峰与不可压级数差约3.96e-12（p/q）。

## 6. 必须保留的g与适用范围区别

旧 `support/plot_cryer_poisson_sweep.py` 使用 `G_REF=9.81`，其Cv0=.0027444522857366896m²/s，所有旧文件保持原样。本次新参考按生产zero-gravity hydraulic fallback9.80665（CPU double、GPU常数最后float舍入）使用Cv0=.0027453898041713454，增加约.03416%；这只改变物理时间尺度，不改变峰p/q。有限储水导致的变化必须与这项g差异分开说明，不能暗改旧理论或旧验收记录。

此参考假设预载已达到相应均匀有限储水平衡且以后q恒定，后续实际native初态仍须独立核验。它忽略真实惯性、阻尼、离散表面层、几何/体积求积和写回误差。压力储水变量由真实体积应变及Mf定义，不等同于SPH float密度：密度没变既不能直接否定这条参考，也不能证明质量或Darcy算子正确。不能把“参考推导自检通过”写成动态程序、Cryer峰值或完整物理验收通过。
