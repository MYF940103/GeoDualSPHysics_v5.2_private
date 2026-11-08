# ReleaseShepard失败窗口72帧原生读取器（作者稿）

只新增 `tests/support/upl_c08_shepard_partial_r1.cpp`、`_build.py`和本说明。生成时尚未构建、解码、运行求解器或VTK。新目标名未存在且不在Git历史文件清单，未发现同名活动reader；旧normal reader、输出、90行plan和程序均不修改。

目标仅为 `upl_c08_shepard_window_GPU_r1` 的真实失败窗口：Part_0000..0071，共72帧；最后保存Step=4287999、completed=4288000（τ约.72s）。原计划仍是90帧至4360000。engine reported step4289868不是已保存状态，不推导其未保存时钟或场。正常读取保存态通过也不代表运行成功、完整0.90s或物理验收。

构建从本轮已封口 `upl_c08_shepard_native_r1.build.json` 所绑定 `shepard_core_r1.cpp` 派生，仅三项：正常Run.csv摘要调用替换为固定72/4288000与完整90计划的前72；唯一stage；completion明确partial。保存diff与逆归一化相等证明，原PRE Load至22数组导出主体逐字不变。RunSamples函数保留但不调用，不需要、生成或伪造正常Run.csv，也不解析失败Run.out来制造最终保存状态。

adapter核完整90行plan（4004000..4360000，cadence4000），只消费真实前72行；不截写计划，不改原文件头。导出真实 `(6805,22,72)`。Shepard ON/damping OFF门来自原sealed核心；keep5/255退休、AS ReleaseOnly/.2f/3f、CompletedOnly两实验键缺失及原5000土/1805固定ID/P0/κ/FS/J/n/V/rho/k/cache/plane/实际scalar时钟/signed dterror门全部保留。预期360000 ledger/cache/κ检查、129960固定检查、489960 P0检查、720000平面检查及72个非空signed区间。Shepard计量CSV不由此工具读取，不能从72保存态推断全部滤波调用或未保存失败阶段。

根在唯一读取前独立核有效失败owner/start/call/run、真实出口1及无活动子进程、执行程序/源码/输入/PRE/完整plan/72个PART stat绑定。AS空间、实际后端及被调用程序仍由owner/build证据证明，native不自证。目标元数据与保存原始数组全部保留；completion和bedkeep_metadata明确 `partial=true`、`runtime_success_claimed=false`、`failure_unsaved_state_reconstructed=false`、`physical_acceptance=false`。

根完整审阅后，分别至多一次构建与一次读取；以下路径从case根解释：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_shepard_partial_r1_build.py --execution-authorized
# DATA/PRE/ORIGINAL90PLAN use the sealed failed-job bindings.
C08ShepardPartial_win64.exe --read psi0 GPU DATA PRE 4288000 72 1 ORIGINAL90PLAN FRESHOUT
```

新程序预期 `tests/outputs/upl_c08_shepard_partial_r1_build/C08ShepardPartial_win64.exe`；构建收据 `tests/logs/upl_c08_shepard_partial_r1.build.json`。六个封口Release utility对象加新main，共7对象，不链接solver。建议唯一fresh导出 `tests/outputs/upl_c08_shepard_partial_r1`：completion/bedkeep_metadata、typed22.bin/layout、clocks/history/plane_gaps。实际调用收据由根独立封口；build通过不能替代解码通过。已有或部分结果保留，不重复读取。不新增SHA、solver、半步链、通知器或自动后续任务。
