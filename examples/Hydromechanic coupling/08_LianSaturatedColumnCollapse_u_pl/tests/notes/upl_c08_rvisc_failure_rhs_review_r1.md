# 六次冻结RHS的离线解释

只读已完成且通过的r2检查、30000行soil输出及三条已解码原生记录（旧90的part13/51、失败53的part51）。不调用求解器、组件或BI4 reader，不积分或重构未保存Cor状态。原90/53头和原始数据保留。

同一状态的ON-OFF实际rate差隔离残差加速度经原wallAce/Darcy的即时通道；theta/C/应力率/FS主变量相同由原组件已检查。跨轨迹.52绝对值还含几何、压力、历史变化，不能当纯算子对照。输出summary3行、固定8ID×3态focus24行及共用色标的delta-rate/added-acceleration云图。

条件压力储存功变化为sum((nV/Kw)*p*delta_rate)，机械功为sum(rho*V*v dot delta_a)。前者并非总耦合能量或稳定性证明，正值不能单独证明增长模态。raw compression为原体积率分项，非所有FS处理后的完整rate预算。dt*delta_rate只是量级，不是Symplectic一步预测。

只创建新标签产物，拒覆盖。没有新数值门、半步、SHA扫描或下一物理工况。绘图的symlog阈值仅为显示参数。Root审阅脚本后单次离线执行，图需目视检查。
