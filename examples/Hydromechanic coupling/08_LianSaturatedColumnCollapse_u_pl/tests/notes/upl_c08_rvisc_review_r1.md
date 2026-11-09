# Residual viscosity .30s：原生保存态物理比较（作者稿）

生成本稿时未执行。仅新增 `support/upl_c08_rvisc_review_r1.py`。未来只在新Window run/native真passed、独立侧车审核已封口后读取新30帧，与保留true causal90的前30条实际记录逐时对齐。原90/30头不改；不用OFF.01控制冒充.30基线，不读BI4或大trace、不调用solver/reader/build，也不重新循环审核26列侧车。原22数组/6805ID/ledger/P0/κ/FS/plane/clock/signed门由各自native保留，本分析再逐帧核全部22有限、完整ID、精确实际clock/step及共同P0位。

复用已审 `upl_c08_as05_compare_r1.inspect/quantities` 的纯函数与原SCHEMA，不调用旧main或固定66帧load；明确新30与原90计数。仅TimeMax运行长度在输入物理签名比较中归一；其他XML材料、AS.2/n3、原AV.1、PRE/keep5/fixed-plane/CompletedOnly等保持。新算子来自私有程序与已验证sidecar收据，不冒称原BI4字段证明residual alpha。不同程序身份不是数值等价门，ON/OFF是不同算子，不做5Pa/half/理论误差验收。

输出浅 `figures/upl_c08_rvisc_review_r1_history.csv`（每组30行）、`_matched30.csv`、`_extrema.csv`、`_spatial.csv`及两PNG；另独立 `logs/upl_c08_rvisc_review_r1.check.json`。字段包括绝对p/负压范围及数量、有效/总应力Frobenius RMS与六分量全场极值ID/位置、速度、κ/J/n/rho/k、前缘/高度、原native PRE位移、7011/7012距离与相对径向速度。KE=.5Σrho_current*V_current*|v|²为单位厚度当前混合惯性的瞬时动能二次量，不是完整u-pl能量定理或恒定粒子质量假设。

最近邻和无序近对用完整5000土粒实际xz坐标，r/dp<.7固定作描述，无拟合/遮罩/位移矫正；压缩、剪切、自由面与团聚均可能影响该指标，不能直接证明张拉根因。压力峰均为真实10ms保存采样，不宣称稠密stage峰或未保存首因。

全土平均沉降采用native history里真实double认证PRE的mean_dz。固定初始top/bottom各100个材料ID及其真实PRE坐标复用已通过 `upl_c08_asplane_partial_review_r1_material_layers.csv`，绑定原PartFluid_0000/1000 VTK来源stat；这里PRE坐标原存储是float。分层绝对沉降明确标 `_PRE_VTK_float_mm`，不冒称double精度，不新增PRE解码。ON−OFF同ID位移及层平均差直接从两套当前double位置相减，参考误差相消。

Fig1九面板显示p、首近对距离/速度、速度/KE、κ、平均与层沉降、近对数及J。Fig2为.15/.30各ON/OFF的原5000点p、总sigma_zz、κ、J散点；每个field行四图共用所有真实点min/max，颜色不分位裁剪、不平滑；同等比视窗覆盖四状态全部土粒，固定marker仅灰色背景。所有图表使用实际τ而非合成t0，不把小于等于.30s的暂时改善说成后期停滞已修复。

根全文审后一次显式运行：`D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_rvisc_review_r1.py --execution-authorized`。拒覆盖旧结果，分析passed不构成物理验收或自动长窗/其他psi准入。
