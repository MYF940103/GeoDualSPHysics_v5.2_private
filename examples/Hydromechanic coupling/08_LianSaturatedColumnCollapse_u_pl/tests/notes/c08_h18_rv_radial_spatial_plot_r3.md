# C08 P76/P90 空间图固定矩形排版 r3

仅作者资产，未执行。新增 `support/c08_h18_rv_radial_spatial_plot_r3.py` 和本说明；r1/r2 图片、脚本、CSV和所有收据均保留，不覆盖。r2绘图生成通过不等于视觉通过：总标题裁切已消除，但第一根colorbar标签与右列轴ylabel仍重叠。

本薄脚本导入 r2 已审的纯绑定、`load_spatial`、`fixed_positions` 函数，并按 r2 原check封存的helper stat核其未变；不调用r2.main/render、不触发任何科学分析或外部程序。仍只读取原45000行空间CSV，选择P76/P90原30000行；固定边界仍来自已封存三native的6个 time/Idp/Posd记录，原5000土坐标与CSV逐字节核对。既有r1和r2PNG输入seal均在前后保持。

变化只有排版：18×12英寸画布；六个独立axes的左/右x=.055/.565、w=.335，三行y=.65/.37/.09、h=.22；两colorbar独立x=.435/.925、w=.012，y=.09、h=.78。固定真实横向留白隔开第一根colorbar标签与右列ylabel，不再使用GridSpec或constrained-layout。标题换行，右边距保留；实际t/tau仍用17位有效数字，行标题tau6位明确为rounded label。

全部原物理数据、点数、marker面积/颜色、坐标域、共同完整线性色限保持，与r2 check的每张图数值metadata必须完全相同才可生成成功收据；不重新计算孔压、NN或历史，不平滑、clip、拟合或删除点。原 r2 视觉缺陷不改变既有径向RV物理诊断结论。

未来根独立准入后仅产生两个新图 `figures/c08_h18_rv_radial_spatial_plot_r3_P76.png`、`_P90.png` 和独立 `logs/c08_h18_rv_radial_spatial_plot_r3.check.json`。失败保留partial，不重试或覆盖。check仅绘图/seal结果，仍 `physical_acceptance=false`、`visual_QA_pending=true`；根需实际目检后另记视觉结果。

作者未运行此命令：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_rv_radial_spatial_plot_r3.py --execution-authorized
```

无求解器、native reader/BI4解码、VTK、构建、SHA、Git或通知调用，不改当前/旧计算依赖。
