# ε=.2与.5的66帧窗口离线对比（作者稿，未执行）

仅新增本note及同名support脚本。固定两组：基线 `upl_c08_stage_trace_window_GPU_r1` 和实际采用r1 prepared目录的 `upl_c08_as05_window_GPU_r2`。只有各自真实run/native check均通过、原66/6805/22及安全计数满足时才分析；实际native目录从receipt的completion Entry取得，不猜文件夹名（基线原目录为native，新组拟为native_r1）。不解码BI4、不调用旧固定profile主入口，只复用原SCHEMA/TYPES。

每份typed22只顺序读取一遍：保留原12B头，66个实际record各读一次进入小内存buffer；逐帧核全部22字段有限、6805完整ID与5000土粒、真实clock/Step精确配对及P0 bits。每帧统计p的min/max/mean/RMS、速度、κ/J/n/k、总应力RMS/zz范围及前缘x/高度（均粒心坐标）。压力与总应力只统计原5000土粒ID2060..7059，不混1805个墙点。σtotal使用原double σeff−pI，材料统计按ID，不按空间重新选点。

原reader history提供真实double PRE参考下的全局平均沉降和位移RMS/max；不新增PRE读取。固定材料点5809/4956/4959/7010/7011保存原位置、速度、p/κ/J/FS，以及相对各自首个τ≈.01保存态的位移。该局部参考明确不是τ=0或PRE，不能把首帧已有4000更新的位移漏失称作完整沉降。组间另报同一5000材料点的压力RMS/最大差、XYZ/位移向量最大差与速度差，仅描述参数影响。

实际窗口为τ≈.01–.66，共66个0.01秒保存态。只比较精确共同时钟，不插值或拟合，不扫描dense trace；图中保存态极值绝不称为真实连续/高频峰。参数差异不是半步长误差或理论误差，不设置跨ε的5Pa/.005mm门。原solver/native安全预算保持，不因图像改善宣称physical acceptance。

输出fresh `tests/figures/upl_c08_as05_compare_r1_{history,option_pairs,material_points}.csv` 与overview.png，check在同名logs JSON。9面板包括p、真实PRE全局位移、速度、κ、J/n/k范围、总应力及前缘/高度；p的symlog阈值仅显示设置，所有原数据不裁剪。PNG需root视觉审查。执行仅在根全文审后：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_as05_compare_r1.py --execution-authorized
```

无SHA、solver/reader/build/VTK/queue、下一任务或覆盖旧分析；本作者稿未import/运行。
