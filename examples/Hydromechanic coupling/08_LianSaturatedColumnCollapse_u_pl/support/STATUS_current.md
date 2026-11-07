# 当前发包状态

使用support/LianCollapse_upl_win64_r2.zip及README_server_r2.md。r1独立预载包保留作历史方案，不作为当前共享预载入口。

r2先用选定CPU/GPU后端运行shared_preload_r2 BAT，实际预载10秒；源通过两阶段弹性资格后，同后端三组shared_r2 BAT读取同一PRE状态，分别继续到13秒。已有输出会拒绝覆盖。

已通过四种构建、CPU/GPU源与接收短窗的全部22数组及带符号时钟精确连续性、旧默认回归、三个材料短承接、塑性源拒绝及新路径解压/四份GenCase输入检查。源码及说明见tests/notes/upl_preload_handoff_root_r1.md。

实际10秒源及三组完整塌陷尚未运行/验收，不能把短窗交接结果当作平衡或论文精度；通用塑性/HG/任意PART重启仍不在本次窄范围内。所有旧包、程序和原始结果均保留。
