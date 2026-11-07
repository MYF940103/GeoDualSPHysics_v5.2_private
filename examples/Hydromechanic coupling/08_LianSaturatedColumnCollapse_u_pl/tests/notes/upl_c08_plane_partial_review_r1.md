# 固定平面54帧与legacy43帧离线审查稿

仅作者，尚未import/AST/执行，也未读新growing native。直接复用已审`upl_c08_plane_window_review_r1.py`的`load/total/series`及stat/read/need，不改旧文件、旧常量或MonkeyPatch。新CSV writer只写本次浅prefix；全部同前缀产物不存在才允许运行。

新输入唯一`outputs/upl_c08_plane_partial_r1`及`logs/upl_c08_plane_partial_r1.check.json`；它是必要dt门失败后真实保存的54帧/6800 IDs/22数组，末global4216000、总时刻约10.54 s，不是原计划60帧/.6s正常完成。新收据必须passed/original_saved_native_guards_passed/consumed保持且runtime_success_claimed=false；实际原run/call exit1、step4218523/current2.5us/bound2.49899us的失败证据独立保留。旧输入是`outputs/upl_c08_r4_partial_r1`与其同tag check，43帧/4172000，原失败为MLS；不把两种failure混称或从最后保存态重建未保存first cause。

新54帧原守卫保持：270000 ledger/rho-cache/κ，97200fixed，367200 P0，54非空signed区间，540000 plane checks；原clock1e−14/ledger5e−13/signed1e−14不改。原60行launch plan及使用54行prefix的事实保持，不重写header/计划/时钟。新policy为FixedPlaneStageProjectionReleaseOnly、Active=true、ReactionClosed=false；旧policy和原43帧数据保留。新旧实际PRE时钟相同，共有43个actual time/globalStep和全部材料IDs直接匹配，不插值、不重标时间，也不采用5Pa跨算子等价门。

全部5000土体、全54/43帧保留p mean/RMS/min/max及ID、有效/总应力Frobenius RMS和六分量范围、三维速度RMS/max及ID、κ mean/range/极值ID、J/n/physicalrho/k/native-rhop完整范围。每帧Jmin/max保存实际native ID及并列数量（代表ID为原排序最低者）。总应力通过复用`total`计算σeff−pI；native应力ij顺序xy,yz,xz，Vel为float32×3而非Velrhop。

先从每数据集最终/全窗的pmin/pmax/Jmin/Jmax/vmax/κmax选择真实材料ID，记录选择来源、part/time/value；再对其并集及固定7010/7011，在两数据集所有可用帧导出位置、全部XYZ速度、p/κ/J/n/rho/k、有效/总应力各6分量。另一数据集中的同ID轨迹只是原ID跟踪，不能改称该数据集的极值。由此完整保留全场负压峰粒子轨迹，不能只观察7010/11。

几何仍用原`TOL=4e−8 m`：同时记录原始x/z<0计数和超过−TOL计数；约1nm原始法向float偏移不计越界。近面/超限点数是几何观察，不是NoPen触发数、反力、冲量或耗功，typed22也未导出这些数据。

GPU审计agent给出的最小纯函数`native_step_scales`只用已验证native soil n/rho/k和ID：M=19607844+4×7518796.5/3 Pa，cu²=(M+Kw/n)/rho，D=(Kw/n)k/(1000×9.80665)，Kw=1e9；h=float(.048)、PoreSafety=float(.1)、CFL=.2。每帧输出maxD/maxcu²及真实ID、diffusion-only dt=safety*h²/maxD和quiescent-wave upper scale=CFL*h/sqrt(maxcu²)。实际波限制还含velocity/ViscDt，故实际wave dt≤该去掉项后的尺度；typed22缺force-stage C/gradJ、ViscDt和half-stage极值，不能重演实际guard、反推唯一原因或据此断言必须降低dt。此函数不改求解器参数，不加新门，不建立σ-J理论验收（软化/apex/小应变等影响须单独考虑）。

输出均为`tests/figures/upl_c08_plane_partial_review_r1*`：history、selected_IDs、material_tracks、matched43、两份morph CSV，及history/material/pressure-morph/κ-morph共4PNG和check JSON。散点按真实global4040000/4080000/4120000/4172000/4216000取样（约τ.1/.2/.3/.43/.54）；旧缺少.54明确空缺，全5000原粒子共用各field实际色域，不平滑、拟合或裁色。所有源stat前后不变，无SHA。

根完整审阅且新partial真封口后，才可一次`python tests/support/upl_c08_plane_partial_review_r1.py --execution-authorized`。本脚本不调用solver/reader/build/通知，不自动full/half或接受完整塌陷；正常写出分析check仅表示离线处理完成。
