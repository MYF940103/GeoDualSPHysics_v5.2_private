# C08近床梯度组件离线科学审查 r1

仅作者准备support/c08_h18_bed_gradient_review_r1.py及本note，未执行/import该脚本、未启动component/native/solver/build/VTK/Git。根全文审阅后独立准入唯一离线入口 python -B support/c08_h18_bed_gradient_review_r1.py --execution-authorized。已有同tag check或partial派生文件即拒绝；分析失败只修新派生，不重跑真实组件/原生读取/物理轨迹。

## 闭合事实与输入

必须先有logs/c08_h18_bed_gradient_probe_r1.check.json passed、completion passed及实际Win32/Popen call0；source build为86旧物理对象+1入口，无时间推进/材料返回/filter。计数保持14state、14force、28Darcy、70000gradient/soil、70000原θ内部位复现、420000原Rσ分量内部位复现、84pair、168端点。离线另核70000行实际/literalθ导出double bits；不声称420000应力计算在离线独立重演。

当前组件check没有CSV files清单。脚本明确内嵌**组件已passed后作者首次观察**的7个CSV size/mtime seals；并不倒称工具退出时已存在该seal。运行先bind，再单遍stream gradient87列/soil54/pairs30/focus33/walls31/selected原clock；metrics仅stat保护。原始输出不写，不做SHA或重审86对象链。

各态仅original/radial、P28–34；严格实际time/completed/saved clock、signed dterror<=1e-14，全部5000 ID唯一齐全。全土、当前z<=2*H_float且有真实bound支持、κ>0历史集合、四固定ID四种口径同时报告；κ>0绝不称本步plastic-active。near-bed是描述性分组，不是修改物理边界。

## 求值差及量级

逐态统计G1 corrected trace−double θ、tr(Rσ)/(3K)−θ、fresh CPU θ−saved prior-stage θ的RMS/绝对最大值，保留原native savedθ独立时层含义。支持计数/θ二次support拒绝/Fac float位差/体积float cast绝对误差/full-vs-tangent镜像差均直接取原输出，不发明容差吞差。

单步压力换算shadow为 (Kw/n)*fixed5us*(G1trace−theta)，n来自同一原soil ledger join。它只是当前冻结CPU场中两个空间求值差的单位换算，不运行压力更新，不是新轨迹、全程累计误差界或物理修复。

Ci平面矩阵(C11,C13;C31,C33)由现有9矩阵批量SVD，报告最大奇异值/condition2和真实零最小奇异值数。零分母condition用N/A且保留计数，不截值、不添加物理门。非1不判错误。

## 条件性梯度场功差

只memmap已封存原AS03/新radial typed22的这14个保存态，按实际ID/time对齐；原soilσ在组件中已经证明不变，采用保存的double effectiveσ先float32 cast再double，匹配原force输入；ij顺序xy,yz,xz。无需reader或PRE1001帧。

对每个fluid/bound pass，L0为真实raw float梯度，L1为真实G1修正后float梯度，D0/1=sym L0/1，θf为该pass原doubleθ。按实际V/p分别累加signed和Σabs：

- effective_gradient_correction_work_delta = Σ V σeff:(D1−D0)。
- pressure_gradient_correction_delta = −Σ V p*(trL1−trL0)。
- pressure_theta_gradient_gap = Σ V p*(trL1−θf)。
- combined = 上三项之和 = effective−ΣVp*(θf−trL0)。

同时给ΣV|σ:D0|、ΣV|σ:D1|、ΣV|pθf|描述尺度，0分母如实N/A。单位W/m（2D单位厚度）。它是当前CPU梯度场的条件性功差，**不是actual stress-only Ace功、不是GPU能量注入，也不构成完整耦合能量/稳定性证明**。wall pass仅镜像应变内功变化，缺fresh ghostσ及完整墙反力账，不能当真实墙功闭合。

## 输出与图

仅tests/figures/c08_h18_bed_gradient_review_r1_*：history56行(14态×4region)、focus56个唯一材料-state、pairs84条含两端p/有效与总应力/AS/静态CPU相对加速度/曲率及七Darcy渠道和数值余项、wall_summary56行。原31列wall支持逐行核actual active mode/index/NpbOk，并汇总真实full-vs-tangent/physical镜像差与wall Ace；不读ignored scratch，不将native wall零速度当ghost。

三幅PNG：operators的三口径误差RMS/max与独立saved时层差；四ID的真实保存p/κ/J/XZ轨迹；六pair真实距离及fluid条件性功差。均只连接7个真实保存采样，不平滑/拟合或裁掉负值。每图有CSV数据；静态CPU force/candidate只作冻结场响应，不能冒称过去GPU半stage或新的积分轨迹。

check成功仅analysis_complete=true、physical_acceptance=false、visual_QA_pending=true。无新物理验收界、半步链、全程或其它ψ准入，根须检查图CSV后据量级进入下一开发阶段。
