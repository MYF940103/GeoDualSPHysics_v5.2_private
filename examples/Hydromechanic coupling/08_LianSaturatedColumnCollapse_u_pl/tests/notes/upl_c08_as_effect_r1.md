# C08 AS OFF/ON 11帧离线对比绘图（author-only）

新增唯一绘图脚本 `support/upl_c08_as_effect_r1.py` 和本说明，目前未运行。不启动reader/solver/工具，不修改BI4、原读取器输出或生产源码。根全文审后：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_as_effect_r1.py --execution-authorized
```

脚本要求 `logs/upl_c08_as_short_r1_off.native.check.json` 和 `logs/upl_c08_as_on_partial_r1.check.json` 均实际passed，仅消费各自11帧22数组/typed布局/真实时钟及history。所有6800原IDs逐帧固定；5000土粒固定为2060..7059。时间使用actual native time减真实source_actual_time，OFF/ON实际保存时间配对<=1e-14，不插值、不平滑、不重选材料点、不加新的物理门或half门。

输出使用 `tests/figures/upl_c08_as_effect_r1` 前缀，新文件已存在则拒绝覆盖：

- `_particle7010.png/.csv`：固定native7010的z、三分量速度/速度模、κ、native绝对孔压p、J；不把7010当新中心或代表全部土粒。
- `_history.png/.csv`：全部5000土粒的z<0几何计数/最小z、孔压RMS/mean/min/max、固定初始顶底层沉降、原生真实PRE平均沉降、总应力Frobenius RMS、速度RMS/max、J范围及κmax。z<0仅是已保存位置相对几何平面0的描述，不替代mDBC支持/投影/穿透判据或新增验收阈值。
- `_walls.png/.csv`：固定墙IDs783/787/791的原p、有效σzz及总σzz=double SigmaState_kk.z−native PorePress，保留p本身，不把FSNormal作墙法向或重建未保存故障阶段。
- `_material_layers.csv`：顶底层实际ID列表、初始与PRE参考坐标、存储类型，供复查。
- `.check.json`：实际材料层IDs、消耗stat、图CSV名单和明确的范围限制，无SHA扫描。

固定初始材料层来自现成 `CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/particles/PartFluid_0000.vtk` 的初始z极值ID，之后始终跟踪这些ID；层沉降基准来自同目录实际PartFluid_1000.vtk（真实10秒PRE），绝不使用首个post帧冒充PRE。现成VTK POINTS是float，故这两层的绝对沉降有PRE坐标转float的基准舍入误差；post位置使用native Posd double。全部土粒平均沉降则直接使用native history从真实double PRE算出的值，精度范围不同，CSV分别命名。这次不新增PRE解码/程序。

OFF新程序在τ.11上限正常结束，其11帧与原失败AS0保存前缀exact；ON在更晚的真实force stage失败，11保存帧通过原native安全门。绘图不把ON失败改称成功，不把AS效果当half误差、理论误差或全程物理验收，也不能由已保存帧再现未保存的墙重构异常。
