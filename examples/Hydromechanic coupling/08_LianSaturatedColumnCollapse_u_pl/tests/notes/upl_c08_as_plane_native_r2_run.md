# AS＋plane r2 native单次owner（author-only）

新 `support/upl_c08_as_plane_native_r2_run.py`，机械复用r1 wrapper；r1未执行、所有旧源码/程序/结果不改。本note独立于已经构建绑定的r2 adapter note，避免修改冻结依赖。未启动任何reader/solver。

CLI action按已审物理owner `upl_c08_asplane_run_r1.SPECS`：CPUdebug/GPUdebug/OFF/SHORT/WINDOW，每次只一个。import其SPECS和check_input，不调用物理main/summary，不新增链条。当前CPU原solver0但summary失败，优先消费 `logs/upl_c08_asplane_smoke_CPU_r1.adopted_run.json`，必须该文件实际passed、actualexit0等原success字段且`original_run` Entry绑定原failed记录；原run/CSV/source不可改。其余future原run实际passed时直接消费原run；不以解析失败自动重跑或自动修source。

先核真实start/call/run（或adopted＋原run）、call所指真实admission（可能.owner_admission）、实际program/exe/argv/创建/parent及tool/solver0；GPUdebug另核SAN目标记录与零错误。program/build/runtime/input/output/原计划/PRE必要stat全部绑定，实际配置Material/NoPen1/AS期望/步长输出由原check_input核。原solver或exactreader活动、已有任何native/receipt/call/partial均拒绝，不覆盖不重启。

调用已root构建的 `outputs/upl_c08_as_plane_native_r2_build/C08NativeASPlane_win64.exe`，保持原CLI参数＋EXPECT_AS；build仅派生RunSamples parser识别Configuration已知AS分号，旧core与raw CSV不改。物理SPECS原nopen/ason/updates/cadence对齐，core全22/6800/ledger/P0/κ/FS/planes/clock/signed覆盖逐项核；AS_metadata核实际EXPECT_AS、每帧header与唯一core decode声明。header-only额外结构扫不重复解码22数组。

产物 `outputs/<job>/native` 与 `logs/<job>.native.json`，收据键：passed, expected_AS, original_native_guards_passed, source_run（selected regular/adopted Entry）, original_run Entry, actual_call, completion（原core completion）, AS_metadata（r2 adapter annotation）, outputs[stat], consumed, consumed_stats_unchanged。raw core completion.stage仍upl_c08_plane_native_r1，AS_metadata.stage为upl_c08_as_plane_native_r2。物理接受始终false，无queue/自动下个solver/half/SHA。

根完整审后示例（本作者未执行）：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_as_plane_native_r2_run.py CPUdebug --execution-authorized
# 每一其它action只在其实际solver和adoption/normal closure审过后单独调用。
```

helper/metadata写失败保留所有已生成core outputs与真实call，不重复解码；只允许根决定新离线修复证据。已完成CPU不得因post失败重跑。
