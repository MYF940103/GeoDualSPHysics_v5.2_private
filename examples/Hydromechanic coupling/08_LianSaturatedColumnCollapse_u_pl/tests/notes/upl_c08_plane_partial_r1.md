# C08 fixed-plane失败54帧只读诊断（author-only）

仅新增 `support/upl_c08_plane_partial_r1.cpp`、`_build.py`、`_run.py`、本说明与相对基线 `notes/upl_c08_plane_partial_r1.diff`。尚未构建、读取、求解或queue，原failed ON/原60行计划/BI4/PRE及所有既有读取器不改。独立新输出 `tests/outputs/upl_c08_plane_partial_r1`，helper同级 `_build`。

真实ON run/tool均1、无ownership错误，54个标准Part0000..0053已保存，最后console10.540000/completed4216000。首因是原必要步长检查：`GPU porosity current step or DtMin exceeds its necessary bound: step=4218523 current=2.5e-06 bound=2.49899e-06 DtMin=1e-08.`，不是DynamicPoreWall MLS错误。这个step是实际打印值，未打印的故障时间/状态不由步数推造；最后精确保存时间只从BI4读。完整目标.6秒未完成，不伪造Run.csv正常结束或60帧。

CPP机械派生已审 `upl_c08_plane_native_r1.cpp`：限定本次psi0/GPU/54帧/最后completed4216000/NoPen1，删除正常RunSamples依赖；继续对**原启动前60行计划**调用 `Planned(plan,60,4240000)`，只使用其前54项，且第53项必须4216000。不会截短、复制或改写为54行计划，更不根据读取后Step回填计划。owner把这个plan的原stat与真实admission绑定。

所有54×6800IDs×22typed数组、P0 bit、κ单调、J/n/V/rho/k ledger5e-13、固定墙、FS、真实clock1e-14、nonempty signed dterror<=1e-14和固定plane4e-8原门保持；NoPenPolicy必须FixedPlaneStageProjectionReleaseOnly/Active true/Reaction false。最后原savedStep应4215999。completion明确partial=true/runtime_success=false/Run_csv_checked=false/unsaved_state_reconstructed=false、原计划60/4240000及所用prefix54未改；无需也不信任何成功Run.csv（存在仅记录，不作为成功证明）。

owner必须实际run.failed、direct owner/tool/solver三退出1、原identity/exe/argv/parent/admission一致、真实GenCase0、source程序/配置/PRE与30项consumed stat未变；当前原solver或exactreader仍活动则拒绝。无已有普通native/partial读取时，才一次新reader，54帧覆盖必须270000ledger/κ/rho、97200fixed、367200P0、54signed区间、540000plane检查。失败保留partial/收据，原门不放宽，不重复读取或求解。

helper独立只链接封口6个Release BI4 utility对象与自己的main，使用对应只读冻结头，不用正在增长的工程obj，不写旧对象或生产源码。根可先全文读diff及owner，再一次执行：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_plane_partial_r1_build.py --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_plane_partial_r1_run.py --execution-authorized
```

所有产物fresh拒覆盖，无solver/half/autofull/queue/Git/清理/SHA。原54保存状态安全门通过也不代表完整.6窗或塌陷物理验收，更不证明reaction/J/Darcy闭合。
