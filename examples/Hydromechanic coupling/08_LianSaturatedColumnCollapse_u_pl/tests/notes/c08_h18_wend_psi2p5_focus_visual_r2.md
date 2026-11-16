# ψ=+2.5° 预载 focus 图排版修订作者稿

仅读 `logs/c08_h18_wend_psi2p5_source_review_r1.check.json` 与其已绑定的 `figures/c08_h18_wend_psi2p5_source_review_r1_history.csv`。不重新读取 BI4/typed22，不复算原生或物理指标，不调用旧分析器、求解器、VTK或其他外部程序。脚本未执行，根全读后才能以 `--execution-authorized` 单次绘图。

保留原 full、last1s、last0p5s 三时窗，原实际保存时间与原六面板全部序列：绝对孔压RMS/native p−P0 RMS；RMS/最大速度；有效/总应力Frobenius RMS；混合体动能；全体/固定初始顶层/底层材料沉降；最大κ/minJ−1/maxJ−1。仅沿用原 kPa单位缩放和J减1显示，不拟合、平滑、重采样、改变数值或新增验收门。

第六幅标题缩为 `Volume and history`，量纲放ylabel `Dimensionless`；其余标题也缩短，画布增为15×8.5英寸，保留图例和原actual t坐标。新图为 `figures/c08_h18_wend_psi2p5_focus_visual_r2_full.png`、`_last1s.png`、`_last0p5s.png`，新绘图收据为 `logs/c08_h18_wend_psi2p5_focus_visual_r2.check.json`。原图、原CSV和原check不修改；任何新同名partial已存在则拒绝覆盖。成功收据仍标注需要根视觉检查，完成绘图不改变source平衡或物理验收结论。
