# 单帧、单次受限shifting位移/运输缺项组件

作者稿，未执行。只新增同名support脚本与本note；不修改生产、输入、原生数据或旧脚本，不运行旧r5四态main、solver、reader、VTK、build、queue或SHA。root全文审后才可显式调用：`D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_shift_component_r1.py --execution-authorized`。

唯一输入为已封口 `upl_c08_causal_window_GPU_r1/native` total-AS/n3的part50，实际completed4204000、名义tau .51。复用已审partial-review的load/inspect，保留原6805/22/90文件头、原全部ID/有限值/clock/signed门和source/stat绑定，仅访问这一条record。该state与完整r6的身份已有prefix证据；不读BI4、PRE或其他payload。实际tau来自原scalar time减认证PRE time，不用名义标签代替。

复用 `shift_frozen_r1.cloud` 的V0J proposal第0行：`delta=dt*(-2)*h*|v|*sum(V0*J*gradW)`，dt2.5us、float h.048、原每分量float cap.1dp；没有放大dt、调整系数或重复位移。其完整内部资格已冻结true FS2/3及其2H halo、全saved-fixed的2H带、低支持/坏moment以及有fixed/FS源的stencil；再保守叠加物理x,z必须严格大于2H。只有临时坐标copy加一次delta，所有固定粒子、原FS、原坐标和22字段均保持原样。近对/NN与FS gap仍以全5000土为邻居，cohort membership在移动前固定。

soil-only核体积覆盖为含self的 `sum_soil V0J W`，在原/临时坐标各算一次，使用原float-Cubic核和实际R2 cutoff。它不含墙，不能叫完整力邻域或全域体积。位置不动/字段不动的原J ledger并不证明新几何守恒；同时报告eligible receiver的div(delta)、det(I+grad(delta))-1、按V加权的局部几何缺项和全5000的sum(V delta)/sum(V)漂移。此处为2D xz面积、即每单位出平面厚度的体积，几何缺项记m²。边界/冻结带receiver的divergence未重建，这些subset积分不能冒称全域守恒或严格边界通量闭合。

仅对完整内部eligible receiver，用同一个全部fluid stencil、原V0J和float距离/核梯度重建moment及Ci=moment^-1；同一Ci用于native p、J、有效应力六分量(xx,yy,zz,xy,yz,xz)、kappa和固定材料P0的梯度，以及位移梯度。报 `Taylor_needed=grad(f) dot delta`；这是将携带值解释为在新空间位置取值时缺少的一阶尺度，不是实际数值误差、真实塑性增量或已实现的运输。kappa的负Taylor项可能与不可逆材料历史冲突，P0的非零项可能与当前原ID/P0 bit合同冲突，二者只记录风险，绝不真的更改。material-map几何体积变化与Eulerian remesh字段运输是两种不同解释，此组件不替它们作选择。

同full-fluid stencil独立用常量和坐标仿射场作梯度检查，精确参考分别为0和单位阵；报实际残差、32*float_epsilon*max(cond(moment),1)舍入尺度及描述性是否处于该尺度，不把它变成物理验收门。native double位置差到float核距离有量化，Ci不是原生导出；没有GPU packed cell/FMA/累加顺序，不宣称CUDA bit回放。真实p/J/应力/历史梯度的Taylor估计未包含高阶余项，不能用其小证明position-only u-pl安全。

fresh三CSV位于 `tests/figures/upl_c08_shift_component_r1_{points,summary,transport}.csv`：5000原ID点表、before/after几何与核覆盖、10个native字段的运输缺项统计；一张同物理轴PNG比较NN、位移/h和div(delta)。check为 `tests/logs/upl_c08_shift_component_r1.check.json`，任何完整/partial派生输出已存在均拒绝，不覆盖/重试。原state逐字节及输入/helper的前后stat不变才标记组件执行完成；physical_acceptance和physical_shift_admitted始终false。结果用于决定是否继续这一受限组件路线，不自动放行生产shifting或追加任何物理任务。
