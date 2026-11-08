# effective-AS / n3 失败窗口51帧读取器（作者稿）

新增 `tests/support/upl_c08_as_effective_partial_r1.cpp`、`_build.py`。本说明生成时尚未构建或解码，不启动求解器、VTK、通知或后续任务。只针对 `upl_c08_as_effective_window_GPU_r1` 的失败轨迹：Part_0000..0050，共51帧；最后保存Step=4203999 / completed=4204000（约10.51s）。reported step4206206不是保存态，不能据此构造未保存时间或场。

从已通过的 `upl_c08_causal_native_r1.build.json` 所绑定generated core机械派生，仅三处：正常Run.csv调用改为固定partial51和原90行plan前缀；stage新标签；completion明确partial与原计划。build保存完整diff、逆归一化相等证明；原PRE Load至22字段导出及数值检查主体逐字保持。六个封口Release utility对象加新main，共7对象，不链接JSph或重编solver。

原计划必须仍为完整90行（4004000..4360000，每行4000步），adapter核全部90行后消费前51行；不截写CSV，不假造成功Run.csv。导出头为真实 `(6805,22,51)`，时间取BI4并从实际PRE clock按标量 `+=2.5e-6` 核验。原5000soil/1805fixed、keep5/退休255、22typed、P0 bits、κ单调、J/n/V/rho/k ledger、密度cache、FS2/3非正孔压、fixed-plane 4e-8m、时钟及非空signed dterror门均不变。AS元数据严格ReleaseOnly/Active/.2f/3f，CompletedOnly要求两个实验ponding键均缺失。

AS元数据不能识别effective/total谱输入；根在唯一读取前须核真实失败owner/start/call/run、Win32出口1及无活动子进程、私有GPU r2程序及源码收据、实际生成XML/PRE/完整90行plan和51个原始PART绑定。读取器不读取causal trace或Totals，也不承担该owner核验。原r2GPU Part_1000认证PRE不改。新输出只检查保存态，`runtime_success_claimed=false`、`failure_unsaved_state_reconstructed=false`、`physical_acceptance=false`。

根完整审阅后才能分别执行一次构建、一次独立读取；以下路径从case根解释：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_as_effective_partial_r1_build.py --execution-authorized
# DATA/PRE/ORIGINAL90PLAN use the sealed actual failed-job bindings.
C08ASEffectivePartial_win64.exe --read psi0 GPU DATA PRE 4204000 51 1 ORIGINAL90PLAN FRESHOUT
```

程序预期位于 `tests/outputs/upl_c08_as_effective_partial_r1_build/C08ASEffectivePartial_win64.exe`，构建收据 `tests/logs/upl_c08_as_effective_partial_r1.build.json`。建议唯一fresh导出 `tests/outputs/upl_c08_as_effective_partial_r1`，内含completion.json、bedkeep_metadata.json、typed22.bin/layout、clocks/history/plane_gaps CSV。运行收据由根独立一次调用捕获真实出口及绑定，不能将build通过当作解码通过。任何已有或部分导出保留，不重复读取。旧读取器、失败数据、90计划、源码与runtime不修改；不新增SHA或半步链。
