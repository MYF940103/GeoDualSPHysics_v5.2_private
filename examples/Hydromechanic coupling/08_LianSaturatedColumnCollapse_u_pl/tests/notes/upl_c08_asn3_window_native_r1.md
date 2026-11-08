# ε=.2 / exponent3 的66帧原生 adapter（author-only）

仅新增同名CPP、build.py和本note；先查新名不存在/git ls-files为空。直接从原 `upl_c08_stage_trace_window_native_r1`（ε=.2、exponent2.55）派生，**不使用AS05/.5版本**。旧adapter/helpers/derivedcores、source/项目、程序/输入/数据不修改；只AST和内存字符串归一化核验，未build、solver、reader或VTK。

## 精确差异

- 新CPP只改指数预期 `2.55f`→`3.f` 两处（header Bits、JSON exponent float reference）；ε的`.2f`两处保留。另改include leaf1处为`asn3_window_core_r1.cpp`，metadata stage1处为新TAG，以及首行说明。所有66/4264000/CLI/KeepBed/NoPen header条件不变。
- derive_core调用**旧window.derive_core**后，只替换三锚，各1次：`rightpart="2.55)"`→`rightpart="3)"`、`marker="AS_Bui2008(0.2;2.55)"`→`marker="AS_Bui2008(0.2;3)"`、completion旧window stage→新stage。已知CSV内嵌分号仍只合并唯一Configuration的两片；left=`AS_Bui2008(0.2`、宽度+1、Nbound/Nfixed位置、marker唯一性和所有数字列检查保持，不泛化repair或改raw Run.csv。
- builder会在全新builddir生成原plane→新core完整diff、旧window派生core→新core三锚diff和core_derivation.json；严格计数并反向归一化证明除此相同。只是adapter预期/作用域标签变化，不是运行时数组数值被改写。

原66个真实post-PRE保存态、6805=1805fixed+5000soil、22数组、global4264000/new264000、首4004000/末零基Step4263999、旧PRE资格/只读取一个PRE、原ID/keep5/实际退休255均保留。原signed dterror<=1e-14且非空、从实际PREtime逐次scalar+=dt的clock<=1e-14、P0 bits、J/n/rho/k ledger5e-13、rho cache、κ有限/非回退、非空FS2/3 p<=0、4e-8m固定平面门及所有有限/类型/计数检查完全不改。adapter只lazy header scan，core只解码字段数组一次。

## root审阅后的单次构建（此处未执行）

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_asn3_window_native_r1_build.py --execution-authorized
```

新TAG=`upl_c08_asn3_window_native_r1`，程序 `tests/outputs/upl_c08_asn3_window_native_r1_build/C08ASN3WindowNative_win64.exe`，收据 `tests/logs/upl_c08_asn3_window_native_r1.build.json`。复用 `mdbc_partition_ReleaseCPU_r1.build.json` 六个封口Release utility objects：JPartDataBi4/JPartDataHead/JBinaryData/JObject/JException/Functions；加新main共7，不链接JSph或CPU/GPU solver对象。头来自同source archive；MSVC14.36、C++17、`/O2 /MT /fp:precise /GL-`、wmainCRTStartup，与原recipe相同；无全工程build/Debug CRT/SHA扫描。

原8参接口保留：

```text
C08ASN3WindowNative_win64.exe --read psi0 CPU|GPU DATA CERTIFIED_PRE 4264000 FRESHOUT
```

FRESHOUT必须不存在，失败保留不覆盖/不自动重试。输出叶名仍typed22.bin/typed22_layout.csv/clocks.csv/history.csv/plane_gaps.csv/completion.json/bedkeep_metadata.json；completion stage为新TAG，metadata stage为TAG+`.metadata`。每帧要求AS ReleaseOnly/Active、`.2f`/`3.f`。backend_proven_by_reader=false、ReactionClosed=false、physical_acceptance=false保留；未来真实run/输入/程序/ε与指数/实际退出绑定仍由root独立owner负责。本作者准备不准入新的物理窗口或其他ψ。
