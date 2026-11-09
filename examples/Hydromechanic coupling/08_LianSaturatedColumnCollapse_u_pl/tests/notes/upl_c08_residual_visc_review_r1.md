# 残差数值黏性：R2零步结果离线评阅（作者稿）

生成本稿时未执行分析。仅新增 `support/upl_c08_residual_visc_review_r1.py`，未来读取已通过 `upl_c08_residual_visc_cpu_r2.check.json` 和其真实CSV，不调用force/原生reader/solver，也不读取BI4或大trace。R2实际为两保存态part13/14（τ≈.14/.15）各独立OFF/alpha=.1，一共4force/4原Darcy、0时间更新/材料返回/过滤；它是额外残差数值黏性的瞬时开关响应，不是原AV参数扫描、GNOG或轨迹改善。

根执行前修正了作者稿的模式键：原CSV使用`OFF/ON`，检查摘要使用`OFF/alpha0.1`。评阅按各自真实字段读取，不修改原CSV标签、时间或数值；图中另显示alpha=.1。该修正发生在首次分析前，未产生失败的数值结果。

R1先成功编译私有Single，随后helper因Windows的`small`宏冲突CL出口2；外层build出口1，无link或数值运行。R2仅修局部变量名与版本，采用封口R1物理对象，实际helper CL1+link1后完成零步组件。旧失败保留，不能把该编译失败混入数值OFF/ON对照。本评阅不重复构建审计。

输出浅路径 `figures/upl_c08_residual_visc_review_r1_{rates,pairs,focus,damping}.csv`、`_response.png`，另 `logs/upl_c08_residual_visc_review_r1.check.json`；拒绝覆盖。rates对全5000土粒和各实际FS类别给粒子等权压力率RMS、范围、ON−OFF RMS/极值ID/位置/正负数量，单位Pa/s，不伪称储能加权或孔压端值。focus保留四ID真实p/P0/κ/J/FS及两压力率、理想与实际float提交的附加加速度；输入p与已保留r6/causal前缀及passed gradient同态记录精确对齐，非p积分后的变化。

独立重核CSV中70000个应力率/θ字段及10000个FS值ON/OFF相同，四focus的C矩阵和主状态相同。全5000输入p不在soil_force.csv中独立重导出；其不变依据是已通过组件的全5000主场位守卫，不能冒称本Python又逐粒读到了ON/OFF全p。四focus的p/P0及其他主字段另有已通过baseline/gradient与原生前缀关联。

damping.csv保留实际double配对力的power/form、法方程/浮点预算、净力/力矩、实际一次每点float提交后的power/net/torque与预算、max提交误差和隔离alpha*dt*dmax。字段名`work`此处是机械瞬时功率W/m，不是已积分功或能量改变；不与先前G-based力率影子的J/(m·s²)混用。预算由真实C++组件封口，本评阅保留全部原值，不新建物理阈值或要求float后0ULP守恒，也不因功率非正宣称压力能量/耦合稳定。

图的上两面板为两对粒子的完整相对法向加速度与含切向曲率的r''，OFF/ON各自来自完整真实邻域，不能当逐邻严格分解。共用对称symlog纵轴（显示过渡1m/s²，无数值门），范围覆盖所有端点并留15%；图例留在面板内。下两面板显示两态全部5000点的真实Δpressure-rate散点，共用全体实际min/max色标，零跨域时使用以零为中性的双色归一化；不分位裁剪/平滑。保存态坐标、孔压和时间不改。

根全文审后才可一次运行：`D:/anaconda3/python.exe -B tests/support/upl_c08_residual_visc_review_r1.py --execution-authorized`。这不准入长窗、半步或新参数试验，也不把瞬时相对加速度改善当作团聚已修复。
