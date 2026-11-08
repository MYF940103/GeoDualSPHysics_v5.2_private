# 仅测试的 causal observer 原生读取器

仅新增同名 support CPP / `_build.py` / 本说明；三个目标事前不存在且未跟踪。作者不执行构建、reader、solver、VTK或import，不改任何原core / 程序 / 元数据 / runtime。新工具仅给观察器实施测试，原物理仍 AS=.2 / exp3 / CompletedOnly / KeepBedOverlap / fixed-plane split；不加入公共XML接口。

沿已审 planned-CSV 通用core，冻结两个明确 GPU profile：

- smoke：源4000000之后10次更新，global4000010，仅 final PART0000；planned CSV只一行 part0 / completed4000010，cadence字段为10。
- window：源之后360000次更新，global4360000，90帧，每4000步 / .01s；planned CSV为4004000..4360000。不接受其他end/count组合或其他后端。

`JSphGpuSingle` 认证handoff后跳过初始 SaveData / Part递增，主循环在 TimeMax 或 NstepsBreak 强制保存末态；因此smoke的唯一文件应为真实10次更新之后，native saved Step=4000009，实际τ约25µs，不是PRE / t0。reader必须见正常Run.csv Steps4000010 / PartFiles1及原plan后才接受；它不把强制末态改成原 .01s调度。这个smoke与根full第一帧 .01s没有共享时刻，不准伪称full-prefix；window90与根r6前90的真实逐位比较留后续另一步。

实际时间从认证PRE开始逐次 `+=2.5µs`，不使用Nstep×dt。原22 typed数组 / 全6805 ID / 1805 fixed / 5000 soil、P0固定材料位校验、κ不减、J饱和域与n/V/ρ/k单J ledger、FS2/3完成态p≤0、1e-6dp平面门、非空signed dterror和全部原预算不变。smoke覆盖5000 ledger / 6805 P0 / 1805 fixed / 10000 planes / 1signed；window为450000 / 612450 / 162450 / 900000 / 90。反力 / J / Darcy闭合和物理验收仍false。

适配器只lazy读取目标PART的keep5 / retire255、AS ReleaseOnly Active .2f / 3f及两experimental ponding keys均ABSENT；字段数组只由core一次读取，PRE只由原认证helper加载一次。`C08CausalTrace.csv` / totals等观察器CSV不进BI4 reader，也不增加第23数组。metadata stage为 `upl_c08_causal_native_r1.metadata`，profile smoke/window、smoke_final_only、计划cadence及计数如上；completion stage为 `upl_c08_causal_native_r1`，原generic数值字段不变。

root全文审阅后可一次独立构建（作者未执行）：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_causal_native_r1_build.py --execution-authorized
```

复用已封口六个Release utility对象、独立编译/链接main，不构建或链接solver。fresh程序 `tests/outputs/upl_c08_causal_native_r1_build/C08CausalNative_win64.exe`，build收据 `tests/logs/upl_c08_causal_native_r1.build.json`。builder保存原generic core完整及小diff，逆向归一相等只允许AS CSV期望2.55→3和stage变化；profile与CompletedOnly门只在新adapter冻结，不改变core数学。

未来独立显式读取接口：`--read psi0 GPU DATA PRE END SAMPLES 1 PLAN FRESHOUT`；smoke用4000010/1、window用4360000/90，实际owner/run/程序/输入绑定由独立root审阅和wrapper负责。当前无自动解码、下一solver、half链、queue、SHA扫描或正式发布。
