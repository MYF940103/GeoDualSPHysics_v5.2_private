# AS0.5 / AS0.3、指数2.55：完成后的离线适配器

仅新增`tests/support/c08_h18_as03n255_review_r1.py`、同名`tests/configs/*.json`与本文。不修改正在运行的owner/config/note依赖、原生工具或旧结果。编写不运行或导入这些模块，不构建、求解、解码、导出VTK、操作Git、扫描SHA或投递通知。只有新窗口和独立唯一原生读取真实完成后，根线程完整阅读并单独准入本离线分析。

参考是已完成`c08_h18_as05_n255_r1`，候选是新`c08_h18_as03_n255_r1`；两者相同指数2.55，仅AS系数0.5/0.3不同。不能用n3.825结果、旧3 s Part90或失败片段替代91帧对照。AS0.5使用它实际的`c08_h18_n255_native_r1.build.json`与`c08_h18_n255_native_run_r1.call.json`，AS0.3使用已有完整AS255工具的`c08_h18_as255_native_r1.build.json`及计划唯一call `c08_h18_as03_n255_native_r1.call.json`。后者工具本体支持0.3/0.5/0.7和2.55，不重建。每次调用原receiver loader前只选择当前case的真实reader build/profile回调，finally恢复；原生call的program、DATA/PRE/plan/profile/output、退出及完整计数由原loader核对。

新profile函数保留原完整17-key CSV检查、实际生成XML所有材料参数检查、与同材料Wendland source的逐参数比较；按准确tag限定AS0.5/0.3及2.55，并非简单放宽一条AS硬码。source仍采用既有1001帧认证结果及原source reader，不重解码。原receiver的所有6805 IDs/22数组/P0/κ/ledger/FS/plane/时钟/有符号dterror、源/目标schema2材料合同、真实程序/输入及完整退出门保持不变。失败或不足91帧的新窗口不能进入本完成分析。

两个91帧窗口必须逐帧具有相同实际completed step和scalar time。全部91个实际匹配时刻作描述性差值，不插值、不重写元数据；不要求不同AS物理字段或signed dterror跨组逐位相同，也不套用5 Pa/0.005 mm半步或理论等价门。首帧保留PRE+1，不制造撤墙t=0点；沉降继续使用初始固定材料层、相对真实PRE与另列包含预载的定义。`p-P0`是固定原始材料参考差值，不是论文的塑性体积超孔压。

数值分析/CSV继续采用已审`c08_h18_wend_receiver_review_r1`及其原analyze_case。只替换显示：短标签AS=0.5/0.3的九面板历史图、六面板选项图，以及实际约0.18/0.3/0.6/0.9 s各一张四字段双列图。孔压、p-P0、κ、J各字段跨两组及全部选定时刻共享完整范围；保留全部土粒子、负压及实际时钟，无平滑、色值截断、拟合或纸面调色。只有soil字段图，不执行particle/VTK。CSV字段包括压力/有效和总应力RMS、J/n/rho/k、材料沉降、速度/能量、近距/对数、κ及实际时刻；继承的field CSV仅含p/p-P0/κ/J，不含曾有剪切标签错误的额外快照导出。

唯一待根线程准入的命令：

`D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_as03n255_review_r1.py --manifest tests/configs/c08_h18_as03n255_review_r1.json --execution-authorized`

产物为新`tests/figures/c08_h18_as03n255_review_r1_*` PNG/CSV、`tests/logs/c08_h18_as03n255_review_r1.check.json`及独立adapter记录。已有完整或partial输出拒绝覆盖。core的描述性stage/note标记临时指向本tag，所有覆盖全在finally恢复。错误保留core和adapter各自失败记录/partial，不重跑求解或原生读取。根线程须检查图表与实际结果后再判断；低速度或某一个间距指标不自动选胜者。本工具不解锁另外ψ，不启动half/PRE/下一参数/正式计算，也不把正常退出视为物理验收。
