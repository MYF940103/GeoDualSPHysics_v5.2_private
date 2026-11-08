# C08_STAGE_TRACE作者补丁：尚未apply/构建/运行

唯一patch=`tests/support/upl_c08_stage_trace_r1.patch`，新增source/C08StageTrace.h，只在JSphGpu.cpp/JSphGpu_ker.cu插入同一个宏的ifdef。默认undef时，静态剥离全部新ifdef后两原文件文本逐字相等；git apply --check通过但未应用。无公共XML/CTE/类布局或主力AS/AV/σ分解；实际代码和本note取代此前designnote中大end-buffer/早期宏名。

实际sampler：Nstep[4000000,4264000)中，4240000之前每40步，4240000..4263999每一步，覆盖τ≈.60.. .66压力峰段而不以100µs稀采样声称解析最快波动。范围只选记录，不替代真实clock。实际step_start=TimeStep，Nstep/InterStep/stored_dt直接复制；operator_dt仅压力update为真实half/full dt，RHS/ponding为0。按三个native IDs5809/4956/4959各独立槽，每event先清hits，结束后3槽必须各一hit；缺失/重复是observation error，不替换原物理守卫。一般5events/采样step，对全.66窗约450000 CSV行。

事件1=真实Darcy RHS，原wall-Ace闭合后复制已有LP/Lx/Gp/GpCorr/GJ/divAce/lap/ki/chain/θ/J/n/C/FS/finishedAce、原double value和实际float rate。chain只在原scope另存副本，不改变原value/+=/cast路径。host收取放在既有CUDA/invalid/speed门后，避免观测缺hit掩盖先发生的物理rate失败。事件2=原predictor/corrector pressure update，p_before是该更新真实poreold（不读未初始化new buffer），after为实际pnew，rate是实际输入。事件3=完成几何positive-only ponding的pre/post p/rate及当时FS；入口刷新当前Idpg避免sort后旧指针。

小fixed device symbol仅3记录；每个capture D2H后关闭context，再由CPU写DirOut/C08StageTrace.csv并flush。仅新tests/outputs路径允许，拒已有CSV；无notifier或自动solver。57列，C0..8行优先，其余vector0/1/2为XYZ；事件2/3的RHS专有量留空，ponding_changed仅事件3有效。finishedAce不含body gravity，不应在离线Darcy分项重复补gravity。核内不重跑第二邻域循环、不求C条件数、不改主变量。

宏可能改变register/spill/FMA或增加D2H/I/O时间，不能先验承诺0ULP或性能不变。下一次物理窗须根独立准入：原r2 PRE、r5同物理、最多.66，无half/新PRE；已有前60真保存state可做同dt/cadence对照，非自动下一阶段。根本轮只review/隔离build，本作者未apply/build/运行。
