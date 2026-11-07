# ψ0根目录r5三秒正式诊断的6805原生读取器

本版仅准入ψ0、global completed5200000、300个保存帧。源为原7060点/2060固定点、completed4000000的认证弹性PRE；原释放目标仍1800–2059共260点，显式保留1800/1852/1904/1956/2008，实际非连续退休255点，输出6805=1805固定点+5000土粒。不是其他ψ组/全状态PART重启/物理精度验收。

CLI与旧根后处理相同8参：

```text
C08Native_win64.exe --read psi0 CPU|GPU DATA CERTIFIED_PRE 5200000 FRESHOUT
```

reader内部严格使用300×4000更新的已声明正式保存节拍，并核每个原生Step、signed dterror与scalar+=dt真实时钟；这不是来自外部启动前plan，不生成或修改plan/原生metadata。根正式BAT依原TimeMax13与dt2.5us运行，实际Run.csv必须为Steps5200000/PartFiles300，registry7060/2060/no exclusions；继续使用已审严格AS_Bui2008(.2;2.55) Configuration分号解析，不改raw CSV。

新build在fresh builddir中先应用已通过 `upl_c08_bedkeep_native_r1_build.derive_core` 的6805派生，再仅改正式8参/ψ0/300/5200000固定profile，保存真实unified diff及stat。原PRE认证/5点半dp几何、22数组/all-ID/P0/κ/FS/单J ledger/4e-8m平面门及signed和clock预算全部保持；没有第23数组。thin adapter每帧另扫lazy metadata，保持typed KeepBedOverlap/明确Kept5/Retire255和AS ReleaseOnly/Active/.2f/2.55f；唯一字段数组decode仍在core。源PRE本身不套已释放active门。

输出leaf不变：typed22.bin/layout、clocks.csv、history.csv、plane_gaps.csv、completion.json和bedkeep_metadata.json。completion stage=`upl_c08_bedkeep_formal_native_r1`；metadata stage=`upl_c08_bedkeep_formal_native_r1.metadata`，计数300；actual_native_IDs6805、fixed1805、soil5000，source target260与actual retired255分别记录。末帧真实zero-based saved Step5199999；没有强行将真实绝对时间改成13或tau改成3。

唯一待构建程序路径为 `tests/outputs/upl_c08_bedkeep_formal_native_r1_build/C08Native_win64.exe`，收据为 `tests/logs/upl_c08_bedkeep_formal_native_r1.build.json`。只链接六个已封口Release utility objects和自身main，不重编solver、不改旧reader/runtime。root审核后单次build：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_bedkeep_formal_native_r1_build.py --execution-authorized
```

正式r5 BAT的postprocess owns唯一解码，不另设会重复读取的自动owner。正常求解退出仍须物理审图；0.34s局部负孔压脉冲和后期负孔压区扩展是3s应分析的现象，不能因guard通过宣称已物理验收。
