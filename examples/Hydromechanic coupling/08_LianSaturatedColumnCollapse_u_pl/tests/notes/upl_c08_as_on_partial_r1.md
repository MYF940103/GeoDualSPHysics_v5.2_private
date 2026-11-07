# C08 AS-on失败11帧只读诊断（author-only）

新增 `support/upl_c08_as_on_partial_r1.cpp`、`_build.py`、`_run.py` 和本说明；未构建/读取/求解/queue。不改任何旧读取器、旧AS0/失败结果、BI4元数据、生产源码或正式文件。新输出仅 `outputs/upl_c08_as_on_partial_r1`，reader build在同级 `_build`，收据在logs。

已封口的AS短序列OFF真实exit0且11帧typed22/time/signedclock逐byte复现原失败保存前缀；ON真实Popen/Win32均1、ownership_errors为空，未调用30帧读取器。新诊断实际报告stage0/native791/step_start10.118450000411855/step4047380。这是本次当前force stage source-clock，不是最后保存post-time，也不重写原AS0故障时刻。ON真实仅11帧、无成功Run.csv；最后BI4必须savedStep4043999/completed4044000，精确time由本新读取器实际读取。

CPP机械派生已passed的partial11 reader，仅新增AS ReleaseOnly/text、Active/bool true、Coef/float .2f、Exp/float2.55f门以及新tag/AS诊断completion标签。22 typed数组、6800完整ID、5000soil、固定1800墙、P0/κ/J/n/V/rho/k/FS及scalar+=dt与signed dterror门原样保留；不依赖伪造成功Run.csv。build复用同冻结头和6个Release utility对象，不链接JSph或任何solver。

owner先核实际ASon run/call/sequence/status失败、真实program/exe/argv/parent/退出、GenCase退出、原PRE和实际生成输入AS参数、全部11PART及stat绑定，确认无已有ON解码。原FAILED/AS0/control只读。新helper仅decode一次，正常exit0与全11原生门通过后，输出 `AS_option_fields.csv`（11×22个全材料字段差异）、`AS_option_pairs.csv`（孔压RMS、固定材料XYZ位移、总字段/时钟/signed telemetry）。每帧所有native IDs/actual clock配对，二者signed dterror独立检查且原值写出不掩盖。AS0/ON差异仅描述不同算子影响，不采用5Pa/.005mm作为option等价门，不是half、理论或全塌陷验收。

根全文审后显式命令（本稿未执行）：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_as_on_partial_r1_build.py --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_as_on_partial_r1_run.py --execution-authorized
```

失败或部分读取只保留首因/已有文件，不覆盖、不重复解码、不重跑solver、不重新布防。completion明确runtime_success_claimed=false、failure_stage_reproduced=false、unsaved_failure_time_known=false、physical_acceptance=false；读取已保存状态不能再现未保存异常阶段。
