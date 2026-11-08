# 新 ψ0 / n3 / CompletedOnly 3 s 正式诊断 reader

仅新增同名 support CPP / `_build.py` / 本说明；三个新名事前不存在且未跟踪。作者不构建、不解码、不运行 solver、VTK 或旧输出导入，也不修改原 r5 / n3 / ReleasedSubstages reader、源码或任何 runtime。此为 root 已选择的下一次 ψ0 3s诊断准备，不是物理验收或另两组准入。

从既有 r5 formal300 reader 机械派生：8argc CLI、全局5200000 / 300帧 / 4000步保存节拍、6805 IDs、1805 fixed / 5000 soil、源target块260 / 实际非连续退休255 / 保留5个床点、22 typed arrays及所有数值门不变。源PRE仍原r2 GPU Part1000，真实源时钟由认证PRE读取；首PART为真实 .01s post状态，不能改为t0。节拍是原明确formal profile，不伪称外部launch plan。

仅 AS 期望由 .2f / 2.55f 改为 .2f / 3.f：CSV单个嵌入分号的已识别token同步改为 `AS_Bui2008(0.2;3)`；其余 core 只换唯一stage。builder对原r5 formal core做反向归一相等检查，并保存完整diff和小型n3-vs-r5 diff，原RHS/ledger/κ/P0/FS/clock/signed/plane预算没有变动。

策略在此准备时已经冻结为 **CompletedOnly**：每个目标PART必须同时不存在 `FreeSeepagePondingPolicy` 与 `FreeSeepagePondingActive` 两key，任意类型/值的出现均拒绝，不按运行数据自适应、不从旧启动文字推断。PRE认证自身保持原规则，不套目标策略。metadata新增 `expected_ponding_policy="CompletedOnly"`、`ponding_policy_keys_absent_headers=300`；AS / keep旧字段保留、指数3。completion stage为 `upl_c08_n3_formal_native_r1`，metadata stage同名加`.metadata`。

原完整覆盖：1500000 ledger / κ / density cache、2041500 P0、541500 fixed、300非空signed区间、3000000 plane检查及每帧真实FS覆盖。原单J相对误差5e-13、scalar clock / signed dterror≤1e-14、1e-6dp几何容差不放宽；后端仍由实际owner/Run绑定，reader传参不独立证明GPU。反力 / Darcy / J闭合及physical acceptance仍false。

root 全文审阅后可一次显式构建（本作者未执行）：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_n3_formal_native_r1_build.py --execution-authorized
```

仅复用已封口六个 Release utility对象并编译/链接新reader；不链接JSph或构建solver。新程序为 `tests/outputs/upl_c08_n3_formal_native_r1_build/C08Native_win64.exe`，收据为 `tests/logs/upl_c08_n3_formal_native_r1.build.json`。后续由root明确安装到全新 `support/runtime_r6/C08Native_win64.exe`；此builder不安装/覆盖任何runtime。

未来正式postprocess接口保持：`C08Native_win64.exe --read psi0 GPU DATA PRE 5200000 FRESHOUT`（同入口可接受CPU参数，但本轮未准入CPU长算）。唯一数组解码仍在core，wrapper仅lazy header核策略/AS/keep。reader正常通过只是完整native审查；没有自动solver、half、重启、queue或其他组流程。
