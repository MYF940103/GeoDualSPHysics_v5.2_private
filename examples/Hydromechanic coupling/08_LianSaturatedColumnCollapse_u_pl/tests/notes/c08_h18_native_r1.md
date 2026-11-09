# C08 H1.8 共用原生读取器（作者稿，未构建/未读取）

只新增 `support/c08_h18_native_r1.cpp`、`support/c08_h18_native_r1_build.py` 和本说明。旧reader、root输入/程序/PRE/输出及生产源码均不改。源派生封存 hdp15 PRE r3纯22读取/DP观察；接收派生原plane+已审keep5核心。原数组数学、5e−13 ledger、signed≤1e−14、scalar clock≤1e−14、接触tol=1e−6dp=4e−8等预算不放宽。

唯一utility构建入口（须Root全文审后）为 `D:/anaconda3/python.exe -B tests/support/c08_h18_native_r1_build.py --profiles tests/configs/c08_h18_profiles_r2.json --execution-authorized`。实际profiles路径显式传入，不硬编码source job/r1。程序 `outputs/c08_h18_native_r1_build/C08H18Native_win64.exe`，收据 `logs/c08_h18_native_r1.build.json`。只1次CL+1次link，原六个Release BI4 utility对象+本main共7对象，无JSph/solver对象；使用既有MSVC14.36/O2/MT/fp:precise/GL−权威闭包。归档header先全局include，派生的source/receiver循环放不同namespace，避免重复定义；静态文本替换可逐项逆还原，实际builddir另存两份diff/derivation。尚未执行构建。

固定新物理资格为Cubic、dp=.04、H=double(.072f)、dt=5e−6、源event2M/10s。源material CSV沿原11个 `key,value` 键：DPCtes,phi,phi_r,n_phi,coh,coh_r,n_coh,dlt,DilationDecay,SoilTriggerFos,fresh_trigger_active，必须由实际generated XML提取；固定source5000/1000/cohesion decay5、phi25固定、ψ0/sf0、fresh_trigger_active0。DP系数继续用生产float角度分组和FunSoilMaterial，不复制替代公式。

源CLI：`--source partial|full DATA MATERIAL_CSV COMPLETE_SOURCE_PLAN FRESHOUT`。plan必须是原五列 `part,completed_step,saved_step,time_s,dt_s`，完整1001行到2M；每一时间用scalar+=dt复核。partial枚举实际连续PART并只取原完整plan前缀，不截写plan、不伪造完整runtime或未保存状态；full要求1001、末event2M、真实typed ElasticSource/schema/contract/cohesion证书以及全部22/κ0/P0/固定markers/ledger等，末帧再核既有handoff的ρ范围/FS非空与非正压资格。partial的saved FS符号仍只观察，不能套release的所有帧门。全源输出7060=2060fixed+5000soil，summary/layers/snapshots保留原DP f观察；full的certified_PRE=true仅指原生证书与数组资格，不是平衡或target合同独立证明，runtime_success_claimed始终false，调用者仍须绑定真实source run0/owner/program/XML。

源r2 TimeMax13配合-nsteps2M；先前r1 TimeMax10在LoadConfig拒绝且无PART，应完整保留，不是物理失败。本工具不猜source job、也不重跑source。新dt下source Part1真实completed2001；PRE实际9.999999999706008，绝不能用part×2000或n×dt替代。

接收CLI：`--receiver window|formal GROUP DATA PRE COMPLETE_PLAN PROFILE_CSV FRESHOUT`。window读取实际91帧/end2180000，formal实际301帧/end2600000；二者首post均completed2000001（实际τ约5µs），末时间约10.899999999671936/12.999999999592434。完整原五列plan逐scalar复核；不drop首帧、不改91/301头、不合成t0。正常Run.csv的真实Steps/count/注册/no-loss仍严格检查，只对已选AS_Bui2008系数的唯一嵌入分号作结构化还原，不改raw CSV。

PROFILE_CSV为同样 `key,value`，exact14键：上述11个material键，加group,ArtificialStressCoef,ArtificialStressExp。闭合groups：psi0=(coh5000,dlt0,sf0)，psi2p5=(5000,2.5,.2)，psim5=(7500,−5,.2)；余phi/coh_r/n_coh等与原材料一致。ε只允许.3/.5/.7；指数只允许3.825/3/5，不为每参数重编。读取器不选择followup或启动矩阵；最多两次followup等准入仍由Root/owner控制。CSV必须绑定实际XML；BI4本身没有完整ψ/φ/coh元数据，不能以reader成功冒称这些由header独立证明。

接收6805=1805fixed+5000soil，原target260/实际非连续退休255/kept IDs1800,1852,1904,1956,2008及source五点几何检查不变。每帧typed AS ReleaseOnly/active/实际float ε与指数、KeepBedOverlap、FixedPlaneStageProjectionReleaseOnly/ReactionClosed=false、CompletedOnly两实验键缺失、原AV无override均核；原源PRE使用新H/dt/2M/law2资格，仅加载一次数组。完成阶段 `c08_h18_native_r1.receiver`；`bedkeep_metadata.json` stage=`c08_h18_native_r1.metadata`，含profile/window或formal、实际count/end/AS/group、firstpost step/time。原22 leaf/layout/history/clocks/plane_gaps不加第23数组。

所有FRESHOUT拒已有完整/partial；异常保留原始输出。utility不证明backend、程序/输入/实际退出或全平衡；owner必须真实绑定，原target合同仍由solver强制。没有SHA、物理数组回写、solver/build自动串、VTK、half、重新预载、额外短窗或queue。源码/AST与纯文本逆还原静态检查已做；实际编译、读取、视觉和物理审查尚待Root独立执行。
