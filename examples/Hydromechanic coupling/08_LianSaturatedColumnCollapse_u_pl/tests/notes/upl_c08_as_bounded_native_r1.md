# C08 AS-on 0.30s bounded native reader（author-only）

`support/upl_c08_as_bounded_native_r1.cpp` 机械派生已通过的 `upl_c08_partial_native_r1.cpp`；只改入口为psi0/GPU/global4120000、实际枚举30个连续Part文件、最终savedStep4119999，并添加typed ReleaseOnly/Active/ε.2f/exp2.55f检查。原22数组、6800IDs、ledger/P0/κ/FS/actual clock/signed dterror等数学不变。没有成功Run.csv依赖；owner单独证明真实solver exit0和global cap/PartFiles。它不是任意失败PART reader，不把预期30当失败时已有30。

输出 `typed22.bin` / layout / clocks / history / completion 与既有布局相同；completion另明示bounded_saved_state_review=true、runtime_success_proven_by_reader=false、physical_acceptance=false、same_operator_PRE_contract_claimed=false。真实actual_end_s来自最后BI4，独立scalar replay另列。固定source PRE是既有r2 certifiedElastic MR1，旧六个Release BI4 utility对象/冻结头只读源码兼容，不链接JSph对象，不构建求解器。build新目录 `outputs/upl_c08_as_bounded_native_r1_build`，命令见序列说明。

CLI：`C08NativeASBounded_win64.exe --read psi0 GPU DATA CERTIFIED_PRE 4120000 FRESHOUT`。FRESHOUT不可存在。只供根审后正常完成ON的30帧一次读取；失败partial需另行实际审阅，不能伪造成功summary或改旧reader。
