# Cryer grad1：单一 GPU 峰窗，尚未启动

## 输入及位置

仅新增本说明、`tests/support/cryer_grad_peak_r1.py`、`tests/configs/cryer_grad_peak_r1_Def.xml` 和 `xcryer_grad_peak_r1_win64_GPU.bat`。本轮单一新输出为 `tests/outputs/cryer_grad_peak_r1`，日志/封存证据在 `tests/logs`，小型历史表在 `tests/figures/cryer_grad_peak_r1_summary.csv`。不改正式输入、源码或已封存记录。

XML沿用已验证 GPU fine coarse，仅将 TimeMax 改为0.0625=2^-4s、TimeOut改为0.00048828125=2^-11s，并同步更新这两条参数的comment，明确GPU峰窗/129帧；差异严格限于2个数值和2条说明。其余包括原围压模式2/q10kPa、dp.0025、半径.05、k1e-5、eta.02、原float孔压/double应力、grad1、SPR/HG/Shifting关闭均不变。dt=2^-21s，共131072步、129帧；BAT仅替换本轮标签，使用canonical GPU Release。

准备阶段必须先看到 GPU fine最终check通过、两run正常退出/原独立半步与跨后端检查通过，以及CPU fine独立review的证据一致性和独立半步筛查通过。否则不封 inputs。此次只由主代理静态审阅文件；未执行默认prepare或--run。

## 执行、封存与安全

主代理审阅并明确授权后，先默认运行脚本仅封存输入，再以--run启动这一个新GPU任务。启动前禁止任何存活DualSPHysics GPU求解器；独立CPU工作不被停止。只记录并控制自己创建的cmd wrapper进程树，不通过名称批量停止进程。不覆盖已有output/log/status/check/completion，也不重启旧worker。

```powershell
D:/Anaconda3/python.exe -B tests/support/cryer_grad_peak_r1.py
D:/Anaconda3/python.exe -B tests/support/cryer_grad_peak_r1.py --run
```

求解器退出后先独立写completion和输出哈希，再做原生分析；完成求解后若新分析失败，只允许修复分析，不重跑物理计算。run/status采用临时文件+原子替换。原生分析只在整轮输出封存后读取，逐帧保持原 finite、37173完整ID、elastic/no-exclusion、所有FSType2/3非空且排水p=0、double保存位置/应力、真实外载、半径<=.0525m、机械dterror<=1e-14及原poreDtSafety检查。没有套用1D均匀应力门槛，也不降低原安全要求。

与GPU fine coarse只有两个完全相同的时刻/步号：新Part0对旧Part0，及新Part1(t=2^-11s,step1023)对旧Part4。复用已冻结Lian `lian_hg_prefix_r2.py` 的严格34字段bitwise对照，唯一单列的是输出区间统计dterror_s；两组仍分别执行原机械步长守卫。不能称全fine前缀或35字段全部0ULP，不能插值或增加其他例外。该跨case helper和原生reader均绑定哈希。

## 历史表与理论

中心集合是新初态r<=dp+1e-12m的固定18个原生ID，不逐帧重新选点。历史表保留全部129帧，包括惯性启动；分中心/内区(r_initial<R-2h)/外壳统计孔压、有效与总平均压应力、径向/切向总应力、径向材料沉降、速度和外载/力矩描述。应力为拉正，总应力为sigma_effective-pI，不能将p/q解释成承载比例。

理论复用正式support/plot_cryer_poisson_sweep.py的material_values和theory_function(360根)。E、nu、k、R、q、rho_water显式从本轮XML读取，并显式复核Cv=k E(1-nu)/[(1+nu)(1-2nu)rho_water*9.81]，重力参考值为9.81。原PoreDtSafety实现的9.80665保持不变，不以理论参数替代步长守卫。

理论t=0的准静态p/q极限为1，而原生初态p/q为0，必须明确记录且不删除启动数据。点中心理论与18粒子有限球平均不是完全相同的观测。分别报告全历史中心最大值、全粒子启动最大值及预声明Tv>=.005窗内保存时刻的中心Mandel峰/理论采样峰，不平滑、不为了匹配论文过滤数据或订新的准确率硬门槛。窗末若仍在上升，不能声称峰已完整捕获。

本轮不是完整Cryer或峰窗独立半步验收。旧float正式历史含其他模型/时间步差异，不是隔离应力写回精度的A/B真值。D型伴随算子、shifting和阻尼新变体均未加入；后续按结果审阅再决定有界阻尼/一致性测试和最终准入。

## 一次完成回报

按OpenAI Docs官方页面 https://learn.chatgpt.com/docs/cli/reference （另有 https://learn.chatgpt.com/docs/developer-commands 的queue段）核对现有会话命令：`codex queue --thread <SESSION_ID> --message ...`。复用已核实的本机CLI绝对路径；CODEX_THREAD_ID必须与CODEX_SESSION_ID一致，并与封存输入中的thread一致。只在本轮终态用x独占创建queue_attempt，调用一次并记录CLI退出码/返回信息；无连通性自检、重试、旧watcher重启或递归通知。通知要求同线程继续离线复核及授权后续工作，不把正常退出当物理验收。
