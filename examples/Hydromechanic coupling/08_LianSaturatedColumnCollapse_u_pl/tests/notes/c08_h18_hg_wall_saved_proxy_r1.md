# C08 墙894：保存态校正矩阵代理分析（作者稿）

只新增 `tests/support/c08_h18_hg_wall_saved_proxy_r1.py` 和本文，作者不 import/执行分析、不构建、读取BI4、启动求解器、VTK、Git或SHA扫描。root完整审阅后可独立执行一次 `D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_hg_wall_saved_proxy_r1.py --execution-authorized`。已有完成或partial拒绝覆盖、重试；所有旧失败和PRE保持原样。

只消费真正通过失败前缀认证的 `outputs/c08_h18_hg_opt_full3_GPU_r1/native_failed99_r1`，绑定其 `.native_failed99_r1.check.json` 的 `diagnostic_passed=true`、原生completion的partial/saved-prefix标记，**不要求或改写原运行passed=false**。复用现有 `storage_review_r2.typed` 和 `compare_r2.read22`，保留99/6805/22真实头、原生时钟、signed及IDs；仅访问Part89–98的十个保存态，不生成新原生文件。

唯一墙点为原生ID894，其真实保存坐标必须为B≈(4.9,−.02)。镜像向量取实际故障行所报告的float32(0,0,.04)，不拟合或移动查询点。原日志报告的是未保存source time10.983389999668779/step2196678/stage1；最后原生状态仍是10.980004999668907。两者绝不混同。

每帧为6805个真实节点建立cKDTree，只计算镜像支持域所需土粒donor的局部几何C。土粒C按原FS核的正体积邻居累积 `L=−Σ Vj r⊗∇W` 后取xz逆；邻居包括实际保存的soil和fixed，使用其原生J。原代码det=0时的identity分支保留并记录，不作为建议修复。树的8个float32 eps候选padding只防止预选丢掉最终float支撑内的点，实际贡献仍应用原radius²/ALMOSTZERO判据。每个土粒C按原生ID顺序累积，仅求所需donor并缓存，不作全5000×6805遍历。

常数按实际代码：H=float32(.072)，radius=float32(2H)，radius²为float32平方；awen=float32(.557/H²)，bwen=float32(−2.7852/H³)。**不替换为解析7/(4π)常数**。V0=double(float32(3.316))/double(float32(2072.5))，不直接替换为名义dp²。float32 sqrt、q、wqq及乘除次序按各自FS `Fac` 与墙面 `WabFac` 源码展开，后者rr²=0时fac=0；不化简为bwen/H。实际CUDA fast sqrt/FMA仍不被复现。

墙面MLS以double保存坐标算dx/dz，再cast rr²为float32，仿原代码累积原M、sum/gx/gz、ΣW/submerged。原阈值为mDBC-Threshold=0以及|detM|≥.001；只在该原geometry条件失败时执行一次原nearest-source recenter，继续在原镜像点求值。**C外推后非正定不会擅自触发另一次重心/nearest修复**。NumPy逆和归约仅是独立代理，不伪称设备cumath逐位结果。

对每个原C分量使用同一anchored线性重构。附加导出有效系数 `αi=δi,nearest+(shiftx−nearx)Gxi+(shiftz−nearz)Gzi`，报告负系数数量、L1、和以及anchored与α点积的数值差。原C从不对称化或裁剪；对称部分特征值只作诊断，xz反射Q C Q保留。报告donor C和重构C的行列式、对称缺陷、对称部分特征值，不据这些代理值宣称已确认实际拒绝分支。

未来只写 `tests/figures/c08_h18_hg_wall_saved_proxy_r1_attempts.csv`（10至20行）、`_donors.csv`、`_trends.png` 和新check JSON。记录真实part/clock/ID、原几何矩阵、donor C/权重、拟合C、原identity分支及全部代理标签。图内原阈值线是现有代码值，不是新增验收门。

主要限制：22数组没有PosCell/CorrMat/BoundMode；FS位移只能取float32(double位置差)，原GPU cell/sorted归约顺序也丢失；保存的fixed J不是下一次force刚重构的stage0 J；保存full-step不是被拒绝的未保存stage1；原生22未提供实际故障时的donor状态。因此此分析只能排序原因和发现保存态趋势，**不能证明当前GPU故障来自秩、源C或外推失正定，也不能替代必要的failure-only实际诊断**。正常分析、原生安全或某个代理det为负均不构成物理、完整3秒或另外两组准入。
