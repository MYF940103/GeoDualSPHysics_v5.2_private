# AS=.2/.5 原始阶段 trace 比较（author-only）

新脚本与本 note 同名查重不存在后作者；未执行科学比较、求解、构建或解码，不修改旧工具/结果。现有 `upl_c08_as05_compare_r1.py` 只比较66个原生保存态；`stage_trace_frequency_r1.py` 只读baseline派生steps并固定单组，不能直接回答双组dense峰。本稿因此新增最小原CSV比较，不复跑terms、windowchecker或原生读取器。

固定真实run：`.2= upl_c08_stage_trace_window_GPU_r1`，`.5= upl_c08_as05_window_GPU_r2`。AS05的实际输出仍采用r1目录，不从run标签猜路径；读取各自通过的代数check的trace Entry，并与其run.trace_file逐stat相等。baseline check固定原路径；新的AS05 check由`--candidate-check`显式传入。要求两个正常run实际退出0、4264000/66、封口stat、同program/source_build/PRE/真实loader时钟，以及实际XML除epsilon/comment外相同。trace checker仍是原57列/float bits/128eps传播预算；本比较不扩大或再次执行其代数门。

每份450003row原CSV只做一次完整读取，只选必要列，保留3ID的全部30000个被采样step（前6000点每40step；后24000点逐step）。按真正RHS2→UPDATE2→RHS3→UPDATE3及实际尾PONDING抽取p_n/half/full-prepond/full-postpond，额外启动或重复ponding另导CSV，初始step全部事件另导；不把多余真实事件丢掉或当作常规rhs。时间轴为各job实际step_start减相同实际PREtime，不减整数10，不使用n*dt或把half强行平移到t+dt/2。两组只精确共step/time配对。

输出fresh `tests/figures/upl_c08_as05_trace_compare_r1_*`：完整被采样steps CSV、extra_ponding、initial_events、逐ID/阶段all-recorded与dense极值、frequency_windows、growth、FS_transitions、cast_rounding CSV，以及pressure PNG和check.json。正常每step最后ponding压值保留在steps；所有其他ponding原记录保留在extra_ponding。初始CSV的J/n/位置仅RHS有值，非RHS空白不填造。初始3ID p_n是否逐bit相同只报告，不冒称全场或所有状态初值已由本工具独立验证。FS跨采样转变标明前后实际step；非连续early40step之间不称精确切换时刻。

同一次CSV读取还取LP/lap/chain/ki四列，额外RHS_windows.csv只作小表：三ID、stage2/3，启动tau<=.25、停滞(.25,.35]、late[.60,.66]；B=Kw/n，四分项是−B*theta、B*ki/gamma*LP、B*ki/gamma*(lap−LP)、B/gamma*chain。分别报signed mean/RMS/maxabs/min/max与实际首末tau/样本数/FS23数量。第三项**包含该branch的Taylor defect及Ace项**，不是单独测得的加速度源；不能把项幅度排序直接叫增长因果。窗口不强制名义端点样本数，不再扫trace或另跑旧terms。all-recorded表的RMS明确是样本RMS，因早/late采样密度不同，不充当全程时间加权RMS。

频率严格沿旧审阅口径：各ID取实际tau [.619,.621)、[.625,.627)、[.635,.637) 的完整步投影前压力，原连续step验证，真实平均间隔；RMS为原数值去均值且不加窗，频率为去均值后Hann谱窗最大非零rFFT格点，不补零、不插值、不强迫落在5–6kHz。约500Hz格点分辨率必须随输出报告。窗口RMS对数比按真实中心间距，仅描述变化，非拟合特征值或根因。全程表的极值只限实际记录样本；.6前未记录的39个step峰无法由本工具排除。绝不以.01秒原生保存态峰代替dense峰。

启动段每40step的实际采样间隔约.0001s，Nyquist约5kHz，不能由它确认早期5–6kHz波形或真实连续峰；AS=.5若在.3后已停滞，其late频率与RMS也只能描述该实际轨迹，不能假设仍为与baseline相同模态。late RMS很小但非零时仍原样报告频率和幅度，不造新噪声阈值。

cast_rounding记录原rate_float与value_double的dt加权差、full压力最终float舍入量、FS2/3正half/full-prepond数量及ponding次数；原代数预算/实际最大预算占比从两个已通过check原样旁引，不增新的数值阈值、不把绝对舍入变大直接叫精度变差。原负压不裁剪；plot仅连接真实记录、线性压力轴，不平滑/滤波/相位对齐。

root全文读且AS05代数检查通过后，唯一离线入口：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_as05_trace_compare_r1.py --candidate-check tests/logs/upl_c08_stage_trace_as05_window_r1.check.json --execution-authorized
```

命令采用root已提供的真实passed AS05窗口check；脚本仍逐stat绑定它与实际run.trace_file，不把文件名当通过证据。所有输出拒绝覆盖，失败保留；无SHA、solver/reader/build/VTK/queue或自动后续。本参数比较没有5Pa/half/理论/物理验收门，也不把3ID或频率相近判为全场因果证明。
