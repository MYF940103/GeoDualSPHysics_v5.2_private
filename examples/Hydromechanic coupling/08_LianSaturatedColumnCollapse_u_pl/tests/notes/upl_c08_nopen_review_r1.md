# C08 legacy NoPen 已保存状态离线分析（作者稿）

本稿尚未导入或执行。仅新增 `tests/support/upl_c08_nopen_review_r1.py` 及本说明；不启动solver、reader、构建、哈希或自动完整运行。根全文审阅且实际新native通过后，才可单次执行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_nopen_review_r1.py --execution-authorized
```

输入固定为 `outputs/upl_c08_nopen_native_r1` 的15帧，以及 `outputs/upl_c08_as_short_r1_off_native` 的11帧OFF控制，绑定各自实际native check；NoPen要求原生guard与消耗stat通过。只依赖封闭native/check，不假设物理owner的r1/r2标签：首个r1因XML writer在GenCase前失败并保留，实际owner为r2。真实bounded退出/输入NoPen1且AS0资格由其原run/native链确认，本分析不从22数组猜出该开关。这是隔离legacy投影诊断，不是生产准入或闭合反力/J/Darcy算法。

读取原始typed22布局、6800原ID（1800固定+5000土体）、double Posd/有效应力和实际clock/history，不重解码、不改header或时间。15帧应为实际全局completed4004000至4060000、每4000步保存；仅前11时刻与OFF配对，误差不超过原1e-14s，不插值，不把OFF延长至0.15s。

所有新派生输出均用 `tests/figures/upl_c08_nopen_review_r1*` 前缀，已有任一结果即拒绝覆盖：

- `_particle7010.csv/.png`：固定原ID7010的实际x/y/z、速度三分量与模、κ、绝对孔压p、J和总σzz；图显示z、vz、κ、p、J、速度模。
- `_history.csv/.png`：全部5000土体的minz、z<0、minx、x<0计数，p均值/RMS/范围、总应力Frobenius RMS、速度RMS/max、κmax/非零ID数、J范围，以及固定初始顶底层沉降。均为按粒子算术统计，非体积加权或连续理论误差。几何零平面计数是描述，不是新验收门。
- `_material_layers.csv`：复用已审AS脚本的`vtk_positions`读取真实源PartFluid0000/1000，只以初始z极值选择固定材料ID，再跟踪这些ID。PRE VTK坐标为float，层沉降有该参考舍入误差；post位置是native double。全土体平均沉降另保留原native history相对double PRE的值，不混为同精度。
- `_local_bed.csv/.png`：取实际保存parts8/10/14，即约τ0.09/0.11/0.15，固定窗口x=[3.5,4.5]m、z=[−0.16,0.24]m。保留窗口内所有土/固定ID、坐标、速度、p、总σzz、κ、J、FSType；7010即使在窗口外仍保留CSV。图固定窗口，不按结果拟合视界，以共同κ色标画土体、灰色方块画固定样本。OFF无part14，面板明确标记不可用。
- `_prefix_comparison.csv`：前11个相同时刻的time+22数组整record及各数组payload是否逐字节相同，并记录原signed-dterror字符串是否相同；只描述，不设相同/不同的验收门。15vs11真实header不修改或纳入错误的整文件等价声称。
- `.check.json`：材料层IDs、实际前缀时钟、输入stat、CSV/PNG名单及范围限制；不重写原始native/history、PRE或物理输出。

原22数组没有每步NoPenShift或触发计数。位移变化或未穿底不能用来声称投影触发次数、反力、修正功、J与投影运动学一致性或严格不穿透已通过。κ是标量历史，不是完整塑性应变张量。正常bounded退出和新图均不等于平衡、完整塌陷或论文精度验收，也不自动启动后续full、half或对照运行。
