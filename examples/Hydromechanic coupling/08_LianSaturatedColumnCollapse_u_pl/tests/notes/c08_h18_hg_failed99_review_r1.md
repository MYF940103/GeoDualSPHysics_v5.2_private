# C08 HG失效前99保存态：作者稿

仅新增同名support `.py`与本文。作者不import/执行脚本，不解码BI4、不运行solver/native/VTK/build/Git/SHA。root完整审阅后可一次执行 `D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_hg_failed99_review_r1.py --execution-authorized`。保留全部失败、原生收据、原程序/PRE/原始301计划和旧图；已有完成或partial拒覆盖。

候选仍是失败的 `c08_h18_hg_opt_full3_GPU_r1`，不是3s完成态。只消费已完成一次的 `native_failed99_r1`（diagnostic_passed=true、whole_run_passed=false）及原HG0 `c08_h18_as03n255_full3_r1/native_r1` 的前99帧，后者301头不改、后202帧不读。完整301 launch plan的前99行逐帧实际clock/step/dt相同，不插值。候选最后P98为actual10.980004999668907s；后来的source10.983389999668779/stage1/step2196678/wall894拒绝没有可重建的原生数组。

原typed schema/read22、`c08_h18_lstar_window_review_r1.frame_data/aggregate` 科学公式完全复用：每组每帧全部5000材料ID、全部22字段、P0/κ/实际clock/signed及已有native门不放宽。六个cohort定义原样，包括固定初始top/bottom，不能用当前高度重选；源只使用已封存1001-frame typed的first/final两个记录，经原source_reference建立初始/PRE坐标和固定P0/κ。source native不重新解码。σ来自double State六分量，total=effective−pI、剪切不减p，Frobenius含两倍剪切平方；NN是原3D非自身距离，不是空洞面积。J/n/rho/k仍是原字段。原storage和动能项只是描述代理，不是完整流体质量/耦合能量证书。

输出3份CSV和3张PNG：`tests/figures/c08_h18_hg_failed99_review_r1_{history,matched,spatial}.csv`、`_history.png`、`_p.png`、`_wall894.png`；检查在logs同名check。history为99×2×6=1188行，matched99行，空间为selected P89/93/98的两组全部材料共30000行，含总p/nativep−固定P0、位移/速度/κ/J/n/rho/k/NN和double六应力。跨HG算子的差值不是half误差，不套5Pa门。失败Run.csv不存在，所以不构造TSimul、完整loop率或速度比。

压力与NN图每行一个case、每列同一个真实保存part，共用每变量全部所选材料的raw范围、物理轴及equal aspect，无平滑/裁剪/时间拟合。wall894视域固定为x=4.9±4H、z=[−dp,4H]，是报告壁坐标附近的描述框，不是拟合阈值或新物理门；星号来自该保存态真实固定ID894位置，不能当其后拒绝时的流体邻域。matched另保存该固定框内材料数量、压力/NN/J极值及κ最大值，空框明确None。整域统计始终包含全部5000粒子，不由框裁掉异常。

root另行完成前90帧与cached旧91的逐byte前缀检查，本脚本不重复它。原301计划不改头或删行，旧91强制末2180000不是full Part90的2180001。绘图正常和保存态安全成功不表示失败消失、HG正确、论文精度或3s物理验收；其他ψ/PRE/solver不自动启动。root须目检3张新图，派生失败只保留修派生，不重跑物理。
