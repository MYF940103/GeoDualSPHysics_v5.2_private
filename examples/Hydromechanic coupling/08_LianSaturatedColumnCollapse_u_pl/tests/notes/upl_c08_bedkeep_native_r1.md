# 保留浅床点的6805粒子原生准入

本工具只用于本轮 `keep_bed_overlap=true` 的C08有界接收计算：CPU/GPU Debug40更新1帧、Release12000更新3帧、Release240000更新60帧。原PRE仍是7060/2060、原右墙资格范围1800–2059共260点；不修改PRE/schema1/contract/原时间。明确保留1800,1852,1904,1956,2008，非连续退休255点，输出6805=1805固定点+5000土粒。这是新几何准入，不是放宽旧6800门。

新 support CPP 是KeepBedOverlap与AS的逐帧lazy元数据薄适配器；唯一22数组读取由builddir派生core执行。build脚本先复用冻结 `upl_c08_as_plane_native_r2_build.py` 的严格AS Configuration分号解析修复，再从原 `upl_c08_plane_native_r1.cpp` 机械生成 `bedkeep_core_r1.cpp`，保存实际diff及baseline/generated stat。改变仅为显式6805 ID集合、固定覆盖1805、clock列数、新scope字段及原PRE上5点半dp位置验证；原22字段、P0/κ/FS/单J ledger、signed dterror<=1e-14、真实scalar时钟<=1e-14和4e-8m平面门保持。没有第23数组、无推断法向字段。保留5点的固定坐标/速度/κ/零derivedmarkers由同一原fixed门逐帧检查；壁面法向/滑移的实际源码与日志绑定由owner负责，FSNormal不是壁法向。

逐帧新增typed元数据要求：GravityPreloadKeepBedOverlap=true；GravityPreloadReleasePolicy=KeepBedOverlap；GravityPreloadKeptBedIds精确逗号串；KeptBedCount=5；ActualRetiredCount=255（后两项完整前缀GravityPreload）。既有NoPen fixed-plane/active/ReactionClosed=false与AS ReleaseOnly/active/.2f/2.55f门不变。completion不再声称退休集合是连续260，记录原target260、实际非连续255、5个kept IDs及实际fixed1805。

关闭keep的OFF对照必须使用已构建的旧6800 AS适配器 `upl_c08_as_plane_native_r2`；不得让新reader根据数据自动改变ID门。新wrapper消费 `upl_c08_bedkeep_run_r1` 的明确action与实际start/call/admission/run/program/build/runtime/input/PRE/plan/PART绑定，一次只解码一个sealed正常job；失败partial不能借normalreader伪成功。

根全文审核后才可执行：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_bedkeep_native_r1_build.py --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_bedkeep_native_r1_run.py CPUdebug --execution-authorized
```

第二命令action以已冻结owner SPECS为准，单stage无自动后续；未构建、未运行。工具不是完整塌陷/半步/反力J-Darcy闭合验收，不改server/runtime/正式输入/旧结果。
