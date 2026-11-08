# 三ID真实stage RHS分项与压力更新（author-only）

新增脚本 `tests/support/upl_c08_stage_trace_terms_r1.py`。两新名先检查不存在、精确git ls-files为空；只作者，未执行/import/AST检查、分析、求解、解码或绘图。未修改已冻结的window checker/owner/native/helper/源程序；未读活动window CSV，仅读已封口Release .03 s CSV前两行核对列名。

仅两个固定profile：`window`消费 `upl_c08_stage_trace_window_GPU_r1` 的passed run、passed window trace check和实际CSV；`short`消费已封口 `upl_c08_stage_trace_smoke_Release_r1` 对应三份文件，用于新派生程序验证，明确不含.6 s压力脉冲。不读BI4/typed22或旧objects/archives，不重复native/owner审计；run实际exit0、步骤/帧数和CSVstat须匹配。所有tau减同job `run.actual_source_time_from_loader`，并核第一4M-step context等于该真实clock；不用整数10、Nstep*dt或拟合/平移。当前真实PRE时间为10.000000000374257 s，代码不拿此常数替换实际run字段。

Kw=1e9、rho_w=1000、gamma_w=1000*9.80665来自当前C08固定输入。对每个真实RHS记录，以记录的n/ki/LP/GpCorr/Lx/Ace/divAce/chain拆为：

1. compression=−Kw/n*theta；
2. LP=Kw/n*ki/gamma_w*LP；
3. interior_defect=−Kw/n*ki/gamma_w*(GpCorr dot Lx)，仅实际raw_FS_branch=false；
4. FS_Ace_L=Kw/n*ki/gamma_w*rho_w*(Ace dot Lx)，仅实际raw_FS_branch=true；
5. divAce=Kw/n*ki/gamma_w*rho_w*divAce；
6. k_chain=Kw/n/gamma_w*原记录chain。

不以保存FSType猜另一个分支，不把未启用项混入当前总率；六项之和及其与原value_double的重排残差只记录，不加新的物理门/阈值。passed trace checker已负责原57列、floatbits和分项舍入预算。输出全部原始events的context/压力pre-post/rate与RHS派生字段；非RHS专有字段保持空。所有leading/repeated trailing ponding单独保留，不删除clipped事件，也不把总行数硬裁为samples*15。

对每个**已采样**step和ID，另存predictor/corrector实际RHS、p_n/half/full-before-ponding/full-after-ponding、J/n/theta/divAce/FS、六个corrector项乘该update真实operator_dt，以及真实压力增量。分别报告rate_float−value_double的cast增量、最终p存储舍入增量、六项重组残差；不把稀疏的前.6 s记录积分或补齐为全部264000步。正负计数与极值按实际值逐项报告，不设物理容差或筛掉异常值。

数据流式读CSV、派生CSV流式写；绘图仅保留数值array缓冲，不装载所有57列大字典，也不触发求解/reader。横轴始终是实际context的**step-start tau**：predictor/corrector分栏，不擅自把half记录平移半dt与峰值拟合。window密窗按Nstep>=4240000选择，避免实际scalarclock偏差漏掉.60边界。

每profile独立全新输出前缀，互不阻挡：`tests/figures/upl_c08_stage_trace_terms_r1_window*` 或 `..._short_verify*`。三份CSV：`_events.csv`（所有实际event）、`_steps.csv`（每个采样step的3ID增量/分项）、`_extrema.csv`（符号/极值）；一份 `.check.json`。window四图为 `_rhs_full/_rhs_dense/_state_full/_state_dense.png`，short只有两张full图并显式标记不含.6脉冲。图显示total p阶段pre/post、各实际RHS来源、J/n、theta/divAce、FS及ponding实际delta p。所有原值不裁剪、不平滑/插值、不改时序；symlog的.1 kPa与1 Pa/s或对应状态单位只是显示尺度，不是物理门。折线只连接原采样点，不制造新数据。

根全文审阅后可单次验证已封口短数据（不会接触活动window）：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_stage_trace_terms_r1.py --profile short --execution-authorized
```

未来window run与trace check均真正封口passed后，另一次显式 `--profile window --execution-authorized`；本脚本不自动调用它。拒已有本profile输出，失败保留partial/first_failure，不重算solver。passed仅指派生完成；3ID/局部分项不能证明全场因果、精度或物理验收。finishedAce已含当时AS/AV/σ等，但观察器未拆这些力来源，不能据本图单独归因于某项；仍需root独立科学审阅和图QA。
