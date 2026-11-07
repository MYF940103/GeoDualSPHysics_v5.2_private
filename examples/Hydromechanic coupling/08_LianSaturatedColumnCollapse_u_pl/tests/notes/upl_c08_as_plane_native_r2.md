# AS＋plane native r2：只修既有Run.csv的已识别Configuration分隔符（author-only）

新 `support/upl_c08_as_plane_native_r2.cpp` / `_build.py` 和本说明。未构建/运行/解码，不改r1 adapter/原core/原CPU runreceipt/原Run.csv或任何生产源码；CPU solver已实际0，不因summary解析错误重跑。r1 native wrapper稿未执行，后续需先消费根的独立adopted_run证明，不把原failed owner改称passed。

实际封口CPU CSV header43列、row44tokens，Configuration在index18，右侧24个header列；唯一额外token来自 `AS_Bui2008(0.2;2.55)` 未转义分号。r2 builder只在**新build目录**从stat绑定的 `upl_c08_plane_native_r1.cpp` 生成 `as_plane_core_r2.cpp`，仅替换RunSamples的row解析片段，保存relative `as_plane_core_r2.diff` / `core_derivation.json`。旧core与numeric列门完全不动。

严格修复规则：正常width不变；异常只允许sep分号且row比header恰多1列；必须存在唯一Configuration header，按其headerindex以及右侧列数定位恰2个片段，右侧首两个header必须Nbound/Nfixed；第一个片段必须以`AS_Bui2008(0.2`结尾，第二必须以`2.55)`开头，合并后这个已识别marker恰一次。仅在内存恢复一个完整Configuration字段，row缩回header宽度。其它额外分号/字段位置/marker/宽度不符合一律拒绝，不能静默丢列。原Steps/Np/Nbound/Nfixed/PartsOut等数值列检查全部保留。**不写、重排或覆盖raw CSV**。

r2 adapter仍27行，include生成core、AS metadata header-only preflight不变，核心只唯一解码22数组。CLI与r1一样：

`C08NativeASPlane_win64.exe --read psi0 CPU|GPU DATA PRE END SAMPLES 1 PLAN EXPECT_AS FRESHOUT`

原core completion.stage仍upl_c08_plane_native_r1；AS_metadata.stage改为upl_c08_as_plane_native_r2。fixed-plane/ledger/P0/κ/FS/clock/signed/AS比特门一概不变。新六utility helper不链接正在增长的工程obj；只加`/I newbuilddir`让adapter找到生成core。程序在 `outputs/upl_c08_as_plane_native_r2_build`，build收据保存生成core/diff/derivation及原corestat，编译前后全部stat不变；不扫描SHA。

根全文审后才显式一次build（本作者未执行）：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_as_plane_native_r2_build.py --execution-authorized
```

root将单独离线审查/采纳已完成CPU结果，future物理owner summary可另修，但必须保护原r1 owner源码stat及旧failed记录；本工具不自动修Run、不启动solver、decoder、queue或retry，也不代表物理验收。
