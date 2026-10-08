# 阶段 1 对比图约定

- 问题：孔压从当前高低位补丁迁移为 double 状态后，在相同输入、时间步、粒子 ID 下，短程压力历史有多大差异？
- 结论口径：只据实报告状态迁移差异；不是理论误差、长期平台修复或效率结论。
- 形式：静态 Matplotlib 折线小多图；每图 CPU/GPU 两列、平均孔压/逐粒子差值两行。输出 PNG 和 PDF，正式图片在 case/figures。
- 数据：tests/logs/pore_double_stage1/regression_history.csv，由实际 PART/PartVTK 同 ID、同时刻匹配形成。平均值和 RMS 使用 1000 个土粒子，不含 40 个边界粒子。
- 图一：q0 k=1e-4，dt=1e-5 s，0–0.2 s，21 个计划输出点。
- 图二：自重旧 PART 重启 k=1e-3，dt=6.25e-8 s，0–500 us，11 个计划输出点；图只示最细步长，完整三档与 Shepard 验收见日志。
- 最少数据：每后端至少 8 个时间点，缺失则报错而非补点或连造曲线。使用实际输出时间，不把输出序号冒充时间。
- 比较定义：旧权威压力 double(PorePress)+double(PorePressRes)，新压力 double(PorePress)。需先核验转换器保留类型，重启初始时刻一致。
- 上排双序列：基线蓝色实线，新状态橙色虚线与空心点；下排：RMS 蓝色实线、最大绝对差橙色虚线。最多蓝/橙两色根，白底、深灰字、浅灰网格，不依赖颜色独立辨认。
- 单位：平均孔压 kPa，差值 Pa；q0 横轴 s，自重横轴 us。均注明短程回归不代表完整 2Tv。
- 文件：figures/pore_double_stage1_q0_history.{png,pdf} 和 figures/pore_double_stage1_selfweight_history.{png,pdf}。
- QA：主代理必须打开 PNG 检查标题/单位/图例/脚注可读性、差值正负/零线与坐标范围；数值对应来源 CSV，不能视觉推断性能或理论精度。
