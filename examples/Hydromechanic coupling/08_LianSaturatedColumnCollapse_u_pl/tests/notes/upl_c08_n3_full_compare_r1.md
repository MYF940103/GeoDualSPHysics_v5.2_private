# r5 AS.2/n2.55 与 r6 AS.2/n3：完整3秒对照（作者稿）

仅新增同名support/note，尚未 import 或执行。两组都必须正常退出、正式300 native 与原后处理通过后，由 root 全文审阅再唯一离线执行。两组是同一原r2 GPU PRE、原冻结 bedkeep Release 程序的 runtime 拷贝、同材料/核/NoPen/CompletedOnly，仅 AS 指数2.55→3；不混入已撤回的半步投影候选。新唯一 native stage 是 upl_c08_n3_formal_native_r1，原 r5 stage 保留；新300头严格缺少两实验 ponding key。原 fixed-plane NoPen reaction/J/Darcy 未闭合限制不变。

采用 root 明确选择的对称完整口径：旧、新 typed22 各顺序读取一次300记录（共约865MB），不额外seek，不再调用任何 C++ reader/BI4/VTK/solver/build。每帧 c.inspect 保留全部原6805 IDs/22 finite/真实clock/signed语义，计算所有5000原土体ID。复用冻结 c.quantities 与 cluster.measures/summarize 的原六cohort、同NN/近对/几何内部定义，不从有限分位缓存反推全分布。已有旧缓存不作为未覆盖字段的替代物；无重复全遍历。

body600行保留各自全300历史和真实匹配时刻/步数：原孔压均值/范围/RMS、全材料PRE沉降/位移、前缘/高度、速度、总σ RMS、κ、J/n/k 等。cohorts3600行记录六组原定义，differences只是同保存时刻 n3−n2.55 描述，不套5Pa/half/理论精度门。全记录 extrema 对 p/固定P0 excess、κ/J/n/rho/k/last-stage theta、三速度分量/speed、六effective与六total应力分量及NN/间距差记录最小/最大值、真实ID/坐标/时间/FS和关联状态，并保留该点最近土邻居ID/距离、距固定B标记距离及有效/总应力迹，方便一次遍历后选观察点；B距离不是接触平面gap。完全相等时保留最早part、最低ID（等距邻居沿原helper选择）。保存态 extrema 不是未保存积分阶段的极值。

遍历中收集实际共同τ=.3/.6/1.2/2/3（原part29/59/119/199/299），不插值、不从float VTK取坐标。每个时刻三行两列为原p/κ/NN；全5000土点、真实固定标记、FS2/3三角，左右同物理轴。每行色标统一使用两组全部300保存态范围，压力为signed symlog（1kPa线性区，仅显示），不截正负峰；matching spatial CSV只导两组五态共50000土点的ID/x/z/p/κ/NN/FS，不导全22数据。所选时间覆盖早期滑动、原窗口、论文常见1.2秒比较点及晚期2/3秒，不能借图暗示论文吻合。

spacing histogram 使用全部300×5000每组1.5M土点-保存时刻观测，同一60个原范围线性bin包含所有值；同时显示 rNN/dp 与 rNN−dp(mm)，计数逐组总和必须1.5M。后者只是相同最近邻数据减名义初始dp，不是裂缝宽度/渗透间隙或实际粒子接触重叠；真实压缩、剪切、整体变形也会改变它。近对门只描述，不宣称classic pairing根因。对数计数轴保留CSV中的零计数，不丢弃尾部观测。

fresh浅层前缀 tests/figures/upl_c08_n3_full_compare_r1：body/cohorts/differences/extrema/spacing_hist/spatial 六CSV、history/spacing两PNG与五个时刻空间PNG；同名 logs check。严格拒绝覆盖任何已有完整或partial产物，size/mtime闭环，无SHA/旧tree扫描。无自动下一求解/其他ψ准入。正常退出、峰值变小、κ/速度降低、前缘更远或近对减少均不能自动证明修复/稳定/更准；root仍需独立看全程形态、压力增长和原科学参照后再作决定。
