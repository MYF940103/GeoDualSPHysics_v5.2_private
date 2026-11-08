# n4保存态起步的一条新CPU耦合短轨迹

新增同名CPP、build.py、run.py及本说明，事前确认路径不存在。生成时只作者/静态检查，未构建、运行或读活动数据。根完整审阅并显式准入后才分开各一次：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_asn4_coupled_cpu_r1_build.py --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_asn4_coupled_cpu_r1_run.py --execution-authorized
```

这是 **1条新CPU物理轨迹**，不是零步或没有计算；最大4000次真实更新（.01s），不是自动AS3/half/长程/其他ψ。build沿通过的zero_cpu_r2机械派生，链接同一frozen bedkeep DebugCPU87闭包的86非main对象与新main，使用该source.zip私有头、真实sourceDependencies和匹配Debug runtime。生产源/项目/旧程序不改。

合法InitRunCpu→真实certified PRE handoff→keep5一次撤墙后，按ID仅Restore原n4 partial part64一次：真实time约10.65、completed4260000，全部6805含5000土的J/σdouble/κ/p/P0/pos/vel/rhop恢复。初始化主场bits与原n4态核对后再开始推进；不是重算PRE/GenCase、generic PART或GPU精确restart。原fixed dt实例只核2.5µs、不改值；显式设 `SymplecticDtPre=LastDt=2.5µs` 匹配固定步。仅把新诊断窗口的**输出统计**error interval清空一次，之后每步读取该新窗口累计signed error；不改GetDt/bound，不继承/声称原GPU4000步输出区间。snapshot真实时钟原样保留。

每次按正式外循环次序：设置predictor阶段→真实 `ComputeStep_Sym`（原predictor/corrector各自DtVariable完整必要bound守卫、原材料返回/NoPen投影/时间积分）→RunCellDivide(true)→TimeStep+=返回dt→LastDt=dt→输出completed=Nstep+1→Nstep++。不复制积分器、不调用正式Run、不在步间Restore。HG/SPR、damping/Shepard、moving/floating/periodic等history路径由实际冻结scope拒绝；原AS4/.2、Cubic hdp1.2、Ck2和所有原物理参数不变。

每个完整步只输出 `states.csv` 一行global extrema（p、last Cor rate/θ、J/n/rho/k/κ、速度、有效/总σ迹、x/z的min/max与实际ID、RMS和FS数）及 `focus.csv` 四行7013/7015/6963/7014。检查所有nativeID/Code/固定坐标与床点+DpZ/NoSlip、所有P0bits、饱和J/n/rho/k ledger≤5e−13及rho-cache float bits、κ逐步非减、原完成态FS2/3 p≤0、原plane tol4e−8、非空signed error≤1e−14。rate/θ明确为上个Cor阶段存留值，不当作完成态即时RHS；Ace/Rσ已释放，绝不访问或调用Sum伪造五项。

异常立即停止。只用预先缓存的最后已flush完整行写failure.json；不读取可能处于半步的主数组/指针，不重建未保存状态、时间或ID。stdout保留每个真实完成step/time，wrapper先保存实际Popen/Win32出口和原call，再记录首因、最后原始CSV行及实际已完成数量；4000仅是计划，不冒充失败后的实际更新数。根保持实际tool session，本工具无watcher/通知/自动重试。输出为新 `tests/outputs/upl_c08_asn4_coupled_cpu_r1`，check同名；失败数据与旧r1/r2/原GPU结果均保护。

run仅消费通过的zero_r2与pressure离线review以及原partial66收据/seed/PRE绑定；不重解码/VTK/SHA。实际CPU重新建cells和墙重建，已有同输入零步率也与旧CPU值存在数十Pa/s舍入差；本轨迹不宣称GPU/未保存阶段精确重放、局部Jac是全耦合稳定谱或因果解释。任何正常4000步完成也只属于此新短诊断，物理验收false。
