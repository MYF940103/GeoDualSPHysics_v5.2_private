# H1.8 bedroles 共用原生工具（作者稿，未构建/未读取）

仅新增 `support/c08_h18_bedroles_native_r1.cpp`（薄入口）、`support/c08_h18_bedroles_native_r1_build.py` 和本说明。旧H1.8工具、中央profiles/plan、source r1/r2记录及frozen compare不变；不启动build/reader/solver，不写任何旧runtime或结果。

本profile是明确的新边界角色分割：初始注册仍7060=2060fixed+5000soil；mk0 IDs0..254，mk1 IDs255..1804，mk2/释放目标IDs1805..2059共255。撤墙keep=false，实际保留固定IDs0..1804连续1805，active6805；不存在“保留五点”的身份或role-change事件。source实际typed TargetIdBegin必须1805、TargetIdCount255。receiver Retired谓词仅为[1805,2060)，Seen覆盖/固定位置/P0/J/κ等原逐ID门仍完整。原五ID专用几何资格由明确的新连续profile替代，不放宽全固定位置验证。

构建CLI仍为 `D:/anaconda3/python.exe -B tests/support/c08_h18_bedroles_native_r1_build.py --profiles tests/configs/c08_h18_profiles_r2.json --execution-authorized`，须Root全文审后才执行。profiles仅复用H/dt/标量调度资格，**其source_job字段不代表新source身份**；新source预定为c08_h18_bedroles_pre_r1，必须由真实owner/program/XML/新证书绑定，绝不能用旧源冒充。原五列plans不改，partial只消费完整source plan的实际连续前缀，source full1001/end2M；receiver window91/end2180000、formal301/end2600000，保留firstpost5µs，不重写header或drop首条。

新程序为 `outputs/c08_h18_bedroles_native_r1_build/C08H18BedrolesNative_win64.exe`，build收据 `logs/c08_h18_bedroles_native_r1.build.json`。一个新main+原6个封口utility对象，共7对象，沿MSVC14.36/O2/MT/fp:precise/GL−，不链接或重编JSph/物理对象。builddir由旧H1.8纯函数生成source/receiver core和entry，分别存diff与可逆替换证据；没有复制或覆盖旧工具源码。

CLI与旧共享工具一致：`--source partial|full DATA MATERIAL_CSV COMPLETE_PLAN FRESHOUT`；`--receiver window|formal GROUP DATA PRE COMPLETE_PLAN PROFILE_CSV FRESHOUT`。source11键/receiver14键actualXML CSV、闭合AS ε.3/.5/.7、指数3.825/3/5及三组材料保持同原共享工具。H=.072f、dt5µs、2M event、Cubic、κ0弹性PRE、source7060/target6805、22数组/212bytes、ledger≤5e−13、signed≤1e−14（非abs）、clock≤1e−14、plane tol4e−8等所有数值预算不变。source full仍需末帧真实证书及既有handoff数组资格；partial不宣称证书、runtime成功、平衡或未保存失败状态。

新stage分别为 `c08_h18_bedroles_native_r1.source`、`c08_h18_bedroles_native_r1.receiver`，`bedkeep_metadata.json` leaf沿旧接口但stage为 `c08_h18_bedroles_native_r1.metadata`。JSON明确geometry_profile=bedroles、keep_bed_overlap=false、targetBegin1805/Count255、retainedFixedBegin0/Count1805、actualRetired255连续。**不生成kept_bed_IDs/KeepBedOverlap policy**；每个receiver原生header必须没有GravityPreloadKeepBedOverlap/ReleasePolicy/KeptBedIds/KeptBedCount/ActualRetiredCount这五个旧keep专用字段。原固定平面NoPen、AS ReleaseOnly/实际float参数、CompletedOnly、原AV资格照旧。

旧frozen compare的stage/receiver ExpectedIDs属于旧keep5 profile；本任务不改它。审旧63帧继续用旧工具，未来新geometry分析应显式准备派生profile。没有新物理方程、PRE赋应力、合同绕过、SHA、VTK、通知或后续自动任务。AST及纯文本逆还原静态检查已通过；实际编译、读取及物理审查均尚未执行。
