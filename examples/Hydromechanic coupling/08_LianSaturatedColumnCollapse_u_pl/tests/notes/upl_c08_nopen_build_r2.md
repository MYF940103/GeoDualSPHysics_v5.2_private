# NoPen overlay r2：仅修MSBuild顶层item选择（author-only）

r1的DebugCPU/GPU Release求值均真实MSBuild exit1/MSB4190，未进入ClCompile、链接或求解。原 `overlay.props` 的顶层ItemGroup Condition引用 `%(ClCompile.Filename)` 不合法。r1源码准备、完整baselineAS ZIP、3CPP overlay与three_files.diff已审阅且不改；r1失败求值/日志/收据全部保留。根在求值前已补的 `C=T.parent` 常量不在本r2重复处理。

只新增：

- `outputs/upl_c08_nopen_source_r1/overlay_r2.props`：仅三个顶层选择改成 `@(ClCompile->WithMetadataValue('Filename','JSph'))`（另两文件同理），删除那三处Condition。原ClCompile Remove/Include transform、显式per-file metadata、source include与target内的核验/报告完全保持。
- `support/upl_c08_nopen_build_r2.py`：复用已审r1工具的纯辅助函数/metadata报告核验；同一原权威vcxproj求值、同一solution Build，仅改import为overlay_r2、产物/日志/收据/无空格Temp中间目录为r2，并额外stat绑定r1 helper与新props。没有prepare，不重新生成源码，不用旧r1失败receipt冒充通过。
- 本说明。

根全文审后先各一次evaluate；核实际三项metadata后再按需build，本作者未运行任何MSBuild或程序：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_nopen_build_r2.py evaluate --configuration DebugCPU --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_nopen_build_r2.py evaluate --configuration Release --execution-authorized
# 两求值实际通过且root审报告后才build
D:/anaconda3/python.exe -B tests/support/upl_c08_nopen_build_r2.py build --configuration DebugCPU --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_nopen_build_r2.py build --configuration Release --execution-authorized
```

数值/原guard/PRE合同候选不发生额外修改；依然AS0、legacy NoPen projection diagnostic、reaction/J/Darcy未闭合，不正式发布、不half、不启动solver/reader。所有旧结果/原生/正式runtime/objects受原stat保护，不扫描SHA、不Git、不重布通知。
