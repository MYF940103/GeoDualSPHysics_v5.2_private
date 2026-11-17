# TPI 加速度源项时间层：文献审计 r1

状态：只读文献研究；2026-11-17。没有修改或执行源码、组件、构建、求解器、原生读取器或通知器。H3-Z05 保持 HOLD。本说明不构成新积分方案的实施或物理准入。

## 结论

Lian 2023 明确将 Eq. (37) 的右端视为在当前时刻已知，并由已知的两层邻压外推 Eq. (39)。但该文 **没有逐项写出 Eq. (36) 中固体加速度源项的离散时间层**：不能从已读正文确定它是上一步缓存加速度、LF 整步上的加速度、半步预测加速度，或去掉未知压力反馈后的预测加速度。也不能把该源项默认认作已经由新孔压得到的 `a(p_new)`。

其前驱显式 ISPH 文献能明确证明“先构造已知预测状态，再解压力，再修正速度”的算法谱系；它没有 Lian 单层 u-pl 方程的固体惯性渗流源项，因此不能替 Lian 填补这一时间层缺口。

## 本地原文的明确内容

主来源：`src/papers/PDF/Lian 2023 u-pl.pdf`，配套转录 `src/papers/u-pw/Lian 2023 u-pl.md`。已核 PDF 正文第 7–10 页及相应公式/流程图。

| 位置 | 原文可以确定的内容 | 原文仍未确定的内容 |
|---|---|---|
| Eq. (27)、§3.3 | 孔隙率、孔压、有效应力及速度采用 LF 半步层；位置在整步层更新。 | §3.4 随后写的整数 `t/t+1` 如何逐一映射到这些半步层。 |
| Eq. (29)–(31) | 去掉水比储水项，保留速度散度、重力及 `rho_l div(k_l a_s)`；没有去掉惯性渗流项。 | Eq. (31) 右端的 `v_s` 和 `a_s=D_s v_s/Dt` 没有时间上标。 |
| Eq. (33)、(36) | `A_ij` 是压力二阶算子的成对权重；`B_ij` 包括速度散度、重力、固体加速度散度与压力 Taylor 误差项 `E_i`。 | `A/E/v/a/k/geometry` 各自的精确时间层，以及 `E_i` 的压力梯度用哪一层，没有列成逐步算法。 |
| Eq. (37) 之后正文 | 右端两项被说明为当前时刻已知；未知邻压以旧邻压近似。 | “已知”并未说明这些量由何种预测、缓存或子阶段产生。 |
| Eq. (38)–(39) | 只明确更改邻压估计：`p_j^t + alpha*(p_j^t-p_j^(t-1))`；常用 alpha=0.5。 | 没有规定将外推邻压重新注入动量方程后，再计算同一压力方程的 `a_source`。 |
| Fig. 1、§3.4 末段 | 图示顺序为邻居/孔隙率率 → 压力 → 应变率/应力 → 总应力/加速度 → 速度/孔隙率/位置；其他变量继续标准 LF。 | 图没有展开历史加速度、启动初始化、源项子阶段、压力与加速度之间的内迭代。 |

Fig. 1 支持“本轮压力早于本轮新总应力加速度”的顺序判断。这是顺序证据，**不是**某一具体 `a^(n-1/2)` 或 `a^n` 公式的直接证据。

Eq. (38) 附近曾将 alpha=1 与全隐式式 (35) 联系起来；紧接着正文又明确指出，外推并未直接求得目标时刻的压力，TPI 只近似隐式解，仍有稳定性限制。不能据 alpha=1 或这段措辞宣称全局隐式求解或无条件稳定。

## 引用链核查

Lian 自身把 Eq. (39) 称为本文提出的 TPI 核心；[1,59–61] 是旧邻压近似及 ISPH 的背景来源，[62] 是真正全隐式时间积分的对照，不是一份可直接照抄的 Lian TPI 完整算法。

1. **[61] Barcarolo 2013 博士论文**，HAL 官方完整 PDF，印刷页 31–32、41–43（PDF 页 52–53、62–64）已读。Eq. (6.1) 先由旧速度、黏性和重力构造无压力的中间速度 `u*`；Eq. (6.4) 的压力源为 `div(u*)/dt`；Eq. (7.3) 由一次 Jacobi 更新使用旧邻压，算子在预测位置上评价；Algorithm 1 明确预测 → 压力 → 速度修正。它证明源是已知中间状态，但没有固体 `rho_l div(k_l a_s)`，不能给出本问题的加速度时间层。
2. **[1] Bui & Nguyen 2017**，本地 PDF/MD 的 §2.6、§3.8 已读。该文是两层流固相：先忽略水压力梯度预测水速度，再压力投影、再修正水速度；固体用 LF。它同样不是当前单层 u-pl 加速度源项的逐步说明。
3. **[59] Shao & Lo 2003**，出版社可访问摘要说明了预测–校正分步法；没有取得其可读全文，故不据摘要推定 Lian 的固体源项时间层。
4. **[60] Nomeritae et al. 2016**，作者机构及出版社页面核实为显式 ISPH/迭代 EISPH 比较；未取得完整算法全文，故不补写其细节。
5. **[62] Hopp-Hirschler & Nieken 2019**，作者机构书目及官方会议摘要核实为真正隐式的速度/位置/PPE 方法。它不能证明仅外推邻压就成为同一种全隐式算法。

本地 Lian PDF 没有附录或展开的伪代码；Data availability 段没有提供代码。已检查出版社 DOI/机构书目及 Elsevier 官方 API 元数据，没有获得进一步的补充算法。**这是当前检索未获得，不是证明不存在任何补充文件。** 未使用博客、聚合摘要或非原作者推导填补算法。

## 对当前候选的边界与下一步含义

- 当前 P1 是在既有 Symplectic 时层上实现的邻压外推和单次 leading-LP 修正；它不是已完整复现并证明等价于原文 LF 的实现。
- 如果源中的 `a_s` 由正在试解的压力 `q` 产生，那么该压力依赖属于耦合方程的一部分。把它放在右端作为已知值是一个明确的滞后/分裂选择；`S=-sum(A_ij)` 只含 leading-LP 对角项，不能称完整耦合 Jacobian。
- 反之，若选择缓存或去压预测的加速度，也必须写清其时间层、重力/外载/骨架力组成及启动值。现有文献不足以证明其中某个选择就是 Lian 原始代码。
- 应优先将当前实现的 `p/v/a/geometry/load` 时层逐项列明，再在不改变空间算子与既有历史更新的前提下研究低风险的时间反馈修正。外载时钟对齐可以作为独立假设测试，不能借文献审计把它预先判为修复。
- H3 的纸面模式风险及其 HOLD 状态保持；这里没有准入任何半步链、参考求解或完整长算。

## 可复查的主要来源

- [Lian et al. 2023, DOI](https://doi.org/10.1016/j.cma.2023.115967)；[作者机构书目](https://research.monash.edu/en/publications/an-effective-and-stabilised-upsublsub-sph-framework-for-large-def/)；本地完整 PDF 如上。
- [Barcarolo 2013，HAL 原始论文](https://theses.hal.science/tel-00904198)；[官方完整 PDF](https://theses.hal.science/tel-00904198/document)。
- [Bui & Nguyen 2017, DOI](https://doi.org/10.1016/j.ijsolstr.2017.06.022)；本地 `src/papers/PDF/Bui 2017 A coupled fluid-solid SPH approach tomodelling flow through deformable porousmedia.pdf`。
- [Shao & Lo 2003，出版社](https://www.sciencedirect.com/science/article/pii/S0309170803000307)。
- [Nomeritae et al. 2016，作者机构](https://research.monash.edu/en/publications/explicit-incompressible-sph-algorithm-for-free-surface-flow-model/)。
- [Hopp-Hirschler & Nieken 2019，作者机构](https://fis.uni-stuttgart.de/converis/portal/detail/Publication/45217540?lang=en_US)；[官方会议摘要](https://congress.cimne.com/particles2019/admin/files/fileabstract/a50.pdf)。
