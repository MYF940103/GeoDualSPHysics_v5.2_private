# B10us约2s：独立离线物理审查作者稿

仅新增 `support/upl_tpi_m0_B10us_review_r1.py` 及本note，作者未执行。
没有solver、native、build、旧analysis入口、hash或Git，也不改旧science/根正式figures。
根需先完整阅读，并等新B10us唯一read/review实际passed后单次独立准入。

## 真正的唯一目标与接口

目标tag固定 `upl_tpi_m0_dt_B10us_window2s_GPU_r1`，Release/GPU/B/window2s。
沿当前真实adapter接口：目录 `<tag>_native_m0_r1`，收据
`<tag>.native_m0_r1.json` 与 `<tag>.native_review_m0_r1.json`。
不创建另一个口头占位 `_native_r1`，不重复成功的解码。
执行前接口核对已将science收据查询名校正为实际native的 `method_signed_interval_bit_replay`；
只是尚未执行的作者稿字段对接，原signed安全门、全部数值及预算均未改变。

本次是1263保存状态、199996updates、actualend2.00000577545594s，
dt=tD/1000=10.00022888183594us；200000只是nsteps上限，TimeMax2先触发，不能当实际步数。
事件completed1000仍preopen，post从1001起、1159帧/11590真实排水检查。
新native已逐帧核1040IDs/22typed及clock/signed/ledger/FS/HG；science先要求这些收据passed，
再读已有physical/soil_n/clock/IDs/columns/history/ledger，绝不调用读取器。
有符号dterror包含真实初态，并对1262非初始非空区间保留<=1e-14原门。
它是新方法自己的必要步长诊断；旧Kw声速保持诊断，不重新当M0硬门。

## 最小新产物

全部在 `tests/figures/upl_tpi_m0_B10us_review_r1.*`，不动root formal：

- history.csv：B全部1263时刻的pressure/固定初始top10-bottom10沉降、J/n/实际rho、
  六有效/总应力、Q、速度及100层交替X模态汇总。旧A2s前缀与旧B .15s的实际背景点以独立
  context系列加入，没提供的量为空，不伪造旧A完整层模态或匹配clock。
- layers.csv：126300行，每个新B实际时刻的全部100初始材料层，含压力均值/范围、
  沉降、J/n/rho、六分量有效/总应力和各自交替模态、可适用时刻的M0压力/沉降参照。
  该表完整匹配所有新profile/heatmap，不再次输出逐粒子大表。
- history.png、profiles.png、modes.png：保全部启动波动/负压及1.5–2s模式，
  不平滑、不裁掉场、不改色值或拟合H/时间/荷载。profile只看窗内原计划Tv=.005/.05。
- metrics.json和logs同tag.check.json：每条原预算、目标时间gap、失败首因/数量、终态及局限。

当前新B保留HGxi=.1，非HG0试验。无需增加历史HG0对照。
HG真实call/cache/dt/tau/spin和M0三phase interval/pressure history检查继承新passed native review，
不把通用退出或原生字段成功当HG或物理精度的全部证明。

## 应力与正确参照

保存sigma是骨架有效应力；totalSigma=effectiveSigma-pI，只改对角、剪切不变。
Q是100材料层均值总sigma_zz的98个二阶差分RMS，不是X列交替模态。
全部原始X列按固定ID对应，交替模态为去掉每层均值后的(-1)^column投影。

新B用未拟合H1/M0准静态伴随：原E2MPa、nu.3、n.3、k1e-4、q010kPa、ramp/drain原值，
g_reference9.81、512模态；不把运行诊断gamma9.80665改进理论作事后拟合。
它不是有限ramp/核带载荷/惯性/J-n演化的启动精确真解，启动误差全保留但不据此捏造新门。
旧A只消费原已输出的finiteKw参考和actual pressure/settlement，绝不重新求一个A参照轨迹。

Tv=.005/.05各自选择实际最近保存状态。B用自己的actual time和M0，A用旧profile_times的
自己的actual time和finiteKw；报告各自目标gap、实际Tv及B-A时间差，不插值、不重排、
不称sameclock。A末态等coverage问题不被这段2s审查扩张成完整2Tv结论。

原计划预算保持：

1. 所有新B t>=.1-1e-7：100层总竖向应力最大误差<=100Pa、顶部两层gap<=100Pa。
2. 两个声明Tv：100层均值压力剖面RMS误差<=可比A+10Pa（q0归一的.10个百分点）。
3. 顶部绝对沉降误差/S∞<=可比A+.10个百分点，S∞=1000*q0*H/M（mm）。
4. 底部绝对参照误差<=.005mm，并且<=可比A+.002mm。

原A旧100Pa超限仍然保留，不豁免B。不同dt或M0/finiteKw差不套5Pa half等价门。
all-native-point pressure RMS/极差/最大误差、全部列模态另报，不用层均值遮掩团聚或交错。
这些底部参照预算在声明Tv处检验，不把启动伴随曲线冒称全过程动态精确解。

## 已有轻量对照，不重跑

- 旧A：`upl_bigstep_full_r1.review.json`与其history/profiles/profile_times CSV；
  Q/旧层应力摘要来自已核 `upl_full_upw_compare_r1.check.json/history.csv` 的A系列，
  不读取旧A原生二进制/ledger/大层表，也不重做旧分析。
- 旧B：`upl_tpi_gpu_startup_review_r2.check.json/metrics.json/history.csv` 的B系列，
  明确保留该science overall因旧A失败的事实，不把 .15s 拓展为2s参考或half。
- 新B观测Run.csv TSimul/TTotal/steps每秒原样记录；非隔离、有侧车且输出密度不同，
  不能把这些直接命名为受控TPI速度提升。

check.passed仅是新B本窗原门和两个原预算通过；无论结果如何，physical_acceptance=false。
没有自动下一dt/half/reference/full2Tv、公共源码或发行准入。

## 根准入与保护

根JSON：stage=`upl_tpi_m0_B10us_review_r1.admission`, passed/offline_only=true。
inputs为实际消费stat：本script/note、原XML/计划/三个定义源；新run/read/review及实际seedXML、
plan、completion、columns/IDs、physical/soil_n/clock/history/ledger、Run.csv；上列全部旧轻量
review/check/metrics/CSV。只核必要stat，前后确认消费文件未变，不扫原始BI4或旧源码/对象SHA。

根全读后才可单次 `python -B .../upl_tpi_m0_B10us_review_r1.py --execution-authorized --admission ROOT_JSON`。
任何既有产品/partial/check都拒绝覆盖；失败只保留派生与首因，不能重跑已完成solver或解码。
