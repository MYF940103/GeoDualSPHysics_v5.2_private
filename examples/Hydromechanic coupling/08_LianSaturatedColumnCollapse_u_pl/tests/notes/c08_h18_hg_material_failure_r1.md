# C08 GPU材料影子逐位拒绝：取证与下一步

## 实际失败与保存范围

原单窗 c08_h18_hg_window_GPU_r1 的真实solver/Popen/Win32退出为1，所有权无异常。仅保存Part_0000，原控制台时刻约10.000005秒；没有完成0.9秒。日志在起始步2000731、PreMaterial、ID7011报告σxx差1ULP；报告的source clock10.003654999705869不是已保存的失败状态。旧owner/solver已退出，唯一终态通知已成功投递一次，没有重新布防或补发。

对失败结果的原始run不作改写；新的failure审查记录补充了旧summary正则未摘取的原样Exception(exc)首因。不能把这一新影子producer资格失败称作土体物理发散或团聚修复。

## 只读指令审查和一次定点取证

原Pre与新Node的六试应力及末端径向返回都确实使用融合运算。仅凭fast_math标志不能把原因归为“某侧少用FMA”。原fit是编译期DP_PS，Node是动态fit/fullResult；内联和中间表达式的首次差异仍未被定位。

只进行了一条新标签的最多800更新诊断，复用原PRE，未重跑10秒或整个0.9秒。导出仅发生在真实PreMaterial不匹配后：读取仍存活的SigmaPreg/Rsigma和这一粒子的actual/shadow数据，之后仍抛出原严格异常，solver退出仍为1。它没有生成新的接续通知。

该诊断完全复现相同原始首因。37个浮点字段的17位十进制与IEEE位模式逐项一致：实际与影子的oldκ相同；actual/shadow的xx差9.094947017729282e-13Pa、xz差4.547473508864641e-13Pa，均为1ULP；其余四个分量同。实际Pre的κ数组仍为old，actual returnedκ及actual内部Status未观测，不能用shadow值冒充它们。

失败导出前的Node源定义保持不变；独立只读二进制审查进一步确认其201088字节机器数值体及关联constant/relocation/info均与原Node相同。完整PTX仅kernel名哈希归一后相同。该证明仅涉及Node，不宣称整个程序或整条轨迹逐位相同；没有把未保存的全场重建为原生状态。

## 工程决定

停止为两个独立内联副本无限追逐全历程0ULP，也不以放松材料/物理门来绕过拒绝。下一私有候选采用一次材料producer和typed cache：沙漏Γ与实际接受的六σ/κ来自同一个返回结果；ON积分消费者沿用原速度/密度/位置积分字面并严格核对缓存ID/step/phase/width及一次消费，正确保留Pre κold、Cor κ及κ增量历史。

默认OFF继续调用原已编译的Pre/Cor物理CUDA核；原材料方程、root/commit预算、5Pa/.005mm等已有精度门不变。ON的浮点舍入归属新的唯一producer，不宣称与旧独立内联返回副本全历程位一致。缓存并不代表物理精度提高；仍须OFF回归、Debug实际积分/缓存/显存检查，再进入真实塑性0.9秒和团聚/压力/展开比较。

该修正尚处作者阶段，未改变生产源码、正式文件或旧结果，也未启动其他ψ。旧HG候选及失败、raw和程序源码继续本地保护。证据入口为logs/c08_h18_hg_window_failure_r1.check.json、c08_h18_hg_matprobe_raw_r1.check.json和c08_h18_hg_material_ptx_r1.matprobe_compare.json。所有新动作SHA扫描0次。
