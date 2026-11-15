# C08 私有塑性 HG：GPU 实施边界

2026-11-15，只读工程审查；尚无GPU实现、构建或新物理窗口准入。CPU八更新组件已通过，不能替代GPU结果。生产源码、旧HG限制和原PRE保持。

最小候选可沿RV的冻结GPU对象/头文件/构建配方：113个原库存中替换JSphGpuSingle.obj，保留112个物理对象，新增私有Single及HG CUDA对象，共114个。原Simpleker材料返回、物理force、Darcy和loader无需改写。实际对象/编译选项须在实施时重新按原收据确认，不能仅以此数量当来源证明。

- 在原GPU Single完整force/AS/AV/load之后、dynamic Darcy之前加入HG/current-mass加速度。原Darcy和AceMax各只跑一次。
- n阶段试应力为Sigma_n+(dt/2)Rsigma_n；h阶段用SigmaPreg_n+dt Rsigma_h，κ仍为步首旧值。Sigma三个double2依次(xx,xy)、(xz,yy)、(yz,zz)，Rsigma三个float2同布局。
- 重复EvaluateMaterial的shadow提供Γ；原Pre返回后核六σ和旧κ，原Corr返回后核六σ和完整κ。h的shadow须提前保留，因为Corr后SigmaPreg已释放。不可跨TU依赖原__constant__材料符号，显式传原StSoilCte/fit/soft/trigger。
- n和h均由同一已提交e_n试算。完整更新、completed divide和实际时钟通过后才提交full.next；预测试算不提交。

图限定5000个原soil native IDs、二维、非周期、无增删流体。历史以有向材料ID键保存，当前sorted粒子slot每stage重新映射。当前约18万有向边；可用持久receiver-local有界哈希和邻居表，满容量必须明确失败，不能截邻居。旧键缺失记删除能量，新键零历史。不能用哈希桶顺序进行浮点求和。

完整伴随至少需要拟合M/L、边积分及Zi/Ti、反向汇聚三类依赖遍历。最终 qij=yij-aij Ti dij，Fi=-sum(qij)+sum(qji)；必须存在真实reverse slot，不能用旧RV的平均残差力代替。receiver gather避免double atomic累加。加映射/材料/必要门/实际提交检查，预估每force约7–10个小kernel、50–150MB级缓冲；这不是实测速度。缓冲一次分配，异常/正常都在cudaDeviceReset之前释放。

GPU材料shadow若与旧Simpleker的FMA/fast-math选项不同，不能凭共享header声称逐位相同。优先保留原NVCC材料算术约定，HG值路径的RN/FMA约定单独明确；真实更新输出必须实际核对。CPU的逐运算误差证书也不能自动当GPU证书。

后续顺序：必要的Audit/Fast数值等价和纯旋转实现范围检查 → 私有GPU OFF一帧回归 → Debug实际短步/材料检查/memcheck → 根据实际证据决定一个Release物理窗口。不增加半步链或PRE重算。新e模型若扩有限旋转范围，需明确其新客观输运政策，生产旧弹性HG的0.01rad门不动；纯旋转helper通过不证明全耦合大转动精度。其他ψ仍等待团聚物理证据，不由本说明解锁。
