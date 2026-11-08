# 团聚诊断绘图的派生修复（作者稿，未执行）

原r1实际tool session58097退出1，已完成366态计算与2196行CSV，随后第87行用错`tau`键造成KeyError；真实context为`tau_s`。原异常保留于 `logs/upl_c08_clustering_r1.failure.json`，没有捕获旧Win32句柄出口或准确启动时间，不能补造。原script/CSV及其failure-audit stat不改；原末尾输入stat验证确实尚未执行，r2不倒填旧成功。

仅新增本note和同名support finish。先核旧CSV仍同一份，2196行必须有真实300/66各态×6cohort、精确actual clock/Step、全soil计数5000、κ高/低分组总数5000和有限数值。CSV未保存每cohort逐ID清单，全程ID证据继续来自原native收据，不冒称CSV可独立证明全部逐IDmembership。重新验证原66/300逐位prefix、真实PRE和所有当前sealed input bindings。

只seek原定5个records：ε.2 part22/65/119/299及ε.5 part65。原300/66头原样核验，复用旧measures和summarize，只重算这5态并将30个cohort行全部字段逐值核已有CSV；其余361态几何不再计算，无solver/BI4 reader/VTK/build。所有5000材料ID/22数组的选定帧检查沿旧inspect。

绘图定义、公共NN色标、物理窗口、标记/阈值全部机械沿原r1，仅标签改为`tau_s`。唯一PNG仍是原尚不存在的 `tests/figures/upl_c08_clustering_r1_neighbors.png`；旧history CSV只读，不覆盖，新收据为 `logs/upl_c08_clustering_plot_r2.check.json`。r2的passed表示完整旧CSV上下文验证和派生图完成，physical_acceptance=false；不会把r1 exit1改写为0，NN/团聚proxy的科学局限保持。

root全文审后执行本派生修复一次（作者稿未import/运行）：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_clustering_plot_r2.py --execution-authorized
```
