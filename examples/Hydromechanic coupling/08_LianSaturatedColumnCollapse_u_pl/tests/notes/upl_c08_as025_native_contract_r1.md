# AS.25 reader wrapper：实际 owner 接口纠正

根在首次 native 调用前发现原 wrapper 两处继承字段与实际 owner 不符。只修改尚未执行的 `upl_c08_as025_native_r1_run.py`；已通过 utility build 的 CPP/build/旧说明及其收据保持。未运行 reader、求解器或其他工具。

实际 run 没有 `source_backend/target_backend`，GPU 身份改由真实 `Hardware`（与 summary 同且含 `Gpu_`）、Release配置、已绑定的唯一 direct `-gpu:0` argv/实际exe与Win32出口共同核验。PRE仍由 `source_pre_file`、实际生成XML及原native loader验证，不借Hardware推断来源。

实际 run/owner admission 没有 `preparation` Entry。准备来源改绑 root admission 的 `prepared_XML`、`BAT`、`preparation_tool`、`owner` stats；XML必须为 `tests/configs/upl_c08_as025_window_GPU_r1_Def.xml`，BAT为同目录真实GPU入口。核对run/ad的相同 seed/input_xml，原 GenCase程序、preparedXML stem、输出prefix、`-save:all`、parent/creation与实际出口，再核生成XML的原物理signature。before清单不再引用旧prep变量。全部30/6805/22、typed AS.25/n3、CompletedOnly、keep5、ShepardOFF与原数值预算不改；这些接口纠正不需要重编或重算。
