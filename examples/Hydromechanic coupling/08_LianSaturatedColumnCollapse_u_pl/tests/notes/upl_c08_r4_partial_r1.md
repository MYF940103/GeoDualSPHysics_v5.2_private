# C08 r4正式失败43帧原生只读审查（author-only）

新增 `support/upl_c08_r4_partial_r1.cpp`、`_build.py`、`_run.py` 与本说明；尚未构建、解码、求解或queue。新读取结果仅 `tests/outputs/upl_c08_r4_partial_r1`，程序在同级 `_build`，收据在logs；旧r4正式失败、公共15帧回归、原r2/PRE、旧reader和正式运行包均只读保留。

原r4正式owner已封口：wrapper实际1、GenCase句柄退出0、唯一solver句柄退出1、ownership_errors为空，status所有owned进程退出，未执行native/后处理。确切异常诊断是本次stage0/native823、step_start10.43789250051325/step4175157；这是当前force阶段source-clock，**不是已保存post-time**。共有43个真实Part0000..0042，无成功Run.csv，最后BI4必须原savedStep4171999/completed4172000；精确最后保存时间由新reader直接读取，不把console10.430000当精确时钟。

CPP从已passed partial11机械派生：只改入口43帧/4172000/最终Step，并复用已passed生产NoPen reader的逐帧typed `DynamicNoPenetrationPolicy=LegacyOperatorSplitReleaseOnly`、`Active=true`、`ReactionClosed=false` 门。所有43×6800 IDs×22typed原数组、P0/κ单调/J/n/V/rho/k/FS、scalar+=dt及signed dterror<=1e-14原门保留；无新的物理门、无成功Run.csv依赖。completion明确partial/runtime_success=false/physical_acceptance=false，未保存异常阶段不由reader重现。旧sourcePRE仍只按原qualifiedElastic通道读取，不重算或改metadata，不泛化generic PART/full restart。

新helper独立复用原封口的6个Release BI4 utility对象＋冻结头，7对象链接，无JSph ABI/solver对象，旧对象不写入。owner必须先核真实r4 run/call/status、GenCase0/solver1、完整实际exe/argv/parent/冻结程序及输入/PREstat、43连续PART、已通过公共15帧native；没有活动/已有读取器时仅解码一次。

成功读取后严格比较与 `outputs/upl_c08_nopen_public_reg_r1/native` 的**真实共有前15条记录**：每条double actual time＋全部22 SoA数组逐字节、clock CSV header＋15行含原signed dterror逐字节。43/15原header各自保留，剩28帧只核真实完整性，不改header/count/metadata、不叫prefix bitproof。layout也必须相同，输出 `common_public_prefix.json`。43帧需215000 ledger、77400 fixed、292400 P0、215000κ/rho cache检查，43个非空signed区间。若solver完成而读取/比较失败，只保留新exports离线修，不重复求解或解码。

复制原失败root的真实 `CfgInit_NormalsGhost.vtk` 到新目录，逐字节确认仅复制；其POINTS是墙B、Normal为真实wall normal/mirror offset，不是FSNormal。供后续几何审查，不利用保存帧虚构未保存故障状态。

根全文审后显式命令（本稿未执行）：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_r4_partial_r1_build.py --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_r4_partial_r1_run.py --execution-authorized
```

失败/部分结果存在即保护，不覆盖、不重跑、不重新布防；无half、长solver、Git、清理或SHA扫描。NoPen reaction/J/Darcy仍未闭合，原生安全与prefix通过不等于塌陷物理验收。
