# Storage observer：只读sidecar审查器

仅作者新增`support/c08_h18_storage_review_r1.py`和本文。未导入、运行或生成任何审查结果/图片；没有build、solver、reader、GPU动作、Git或SHA扫描。根全文读完后分别决定一次明确profile的离线审查。源observer代码、已有native结果和其他作者文件不改。

接口为：

```
python -B tests/support/c08_h18_storage_review_r1.py --profile debug2|short3|window --run-receipt ACTUAL.run.json --native-receipt ACTUAL.native.json --execution-authorized
```

支持的原计划只有Debug的debug2（2帧，end2000002）、Release的short3（3帧，end2004001）和后续另行准入的window（91帧，end2180000）。参数不触发任何producer。程序从真实run绑定的`observer_sidecar`、planned_steps、source_pre_file、source_native、input_xml、program/build/source、actual_call与Run_out取身份；native收据须绑定本次新run、实际一次reader call、native completion/metadata/reader build。可接受completion与native_completion同义字段，但若同时提供必须完全同值，不凭路径猜已存在的收据。

## 原门与流式读取

每个新profile必须已有正常owned solver和单次native读取。检查原6805 IDs/5000soil/1805fixed/22数组、J/ledger/P0覆盖及原1e−14 scalar/signed-clock与5e−13 ledger相对误差门。signed dterror保留原**带符号上界**，不改成绝对值。storage判据不替代这些门。新reader metadata必须说明压力预算不是由reader证明，并记录原AV private键不存在、backend=GPU。

只复用既有`c08_h18_compare_r2`的typed22 `SCHEMA/TYPES`、dtype/memmap读取规则及`read22`原始帧检查；不调用其load/analyze_case/绘图或几何分析。每个新保存帧读其原22数组；原PRE的1001帧文件仅mmap后取Part1000单记录，不扫描全程payload。原始BI4/NBI4不读、不重解码，文件在当前审查前后只作必要stat一致性检查，无hash。PRE initial_S及接收last_S分别用原native的`n*V/Kw*p`独立计算，与observer端点作`gamma32*(|S_a|+|S_b|)+32*DBL_MIN`的预定纯算术比较；这是相同状态标量表达式的roundoff核对，不是新物理误差容限。

`C08StorageTrace.csv`只流式读取一次，要求精确26列，逐保存状态恰5000 ID、原ID顺序2060–7059，没有删点或重复。实际time逐bit等于该原生保存time，step等于原planned/native completed step；inits=1、errors=0、rhs_h=updates=completed−2000000。sum_dt按逐次`+=5e−6`独立复核，不用`n*dt`替代实际clock。读取实际plan时沿原1e−14容差核clock，绝不插值。

每IDrelease_cap_calls预注册为原退墙RunCellDivide的单次首cap；release changes为0或1且后续固定。每保存态所有ID cap_calls应一致，cap_calls至少覆盖release及每个completed-step cap；允许真实额外重复cap（Δp=0），不把它误计为新corrector。cap变化数不能超调用数、负cap累计不能反增。绝对项和/局部预算/量化bound应有限、非负、不回退。saved/fresh FS没有被另设相等门，也不删除负压点。

## 预算及分区

逐行重新按observer原字面结合顺序计算六分区和、端点residual及原`gamma_(16updates+8cap_calls+128)`预算，要求它们与sidecar的实际double值逐bit一致，并沿**同一原预算**通过；不增加Pa/位移或经验倍率。实际weighted-pressure-delta小计也须与compression+Darcy remainder+source-split+pressure-commit在同一原预算内一致。

每保存状态另按原ID顺序作全域有符号累加。全域允许预算为逐ID原预算之和，再加host `gamma_(16*5000+128)`乘所有相关绝对项和；同时检查全域残差与逐ID残差之和。不会凭正负抵消后接近0就宣称通过。

S=sum(nVp/Kw)仍是条件storage proxy，不是流体质量。Darcy remainder包含stored float rate量化；rate_quantization_bound_only只是未测原double率的保守非signed bound，不当作一个实测signed项加入恒等式。端点闭合不能证明界面通量、饱和/cavitation条件、FS物理正确或团聚问题已修复。

## 无反馈字节证明和产物

debug2明确不与Release旧轨迹声称bit truth。short3另对保留`outputs/c08_h18_as03_n255_r1/native_r1`做实际前3帧字节比较：保留新3/旧91真实header，各自从12字节后读共同记录，全部22数组与time payload、整份layout及前3行原clock（含signed dterror、interval-empty与phase）逐byte一致，不能重写count/header或筛列。若后续window被独立准入，同样核完整91帧无反馈。没有新control或reference求解。

每profile只生成`logs/c08_h18_storage_PROFILE_review_r1.check.json`和`figures/c08_h18_storage_PROFILE_review_r1_summary.csv`；没有图或后续执行。summary保留实际time/step、signed分区/初末S/全域预算与实际cap计数。已有成功/失败产物均拒绝覆盖；失败仅保留新分析首因和partial，不自动重跑producer/reader/checker，不重置旧状态，不排队通知。
