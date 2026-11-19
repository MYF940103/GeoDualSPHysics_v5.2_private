# 三轮 TPI 孔压历史的原生保存与读回

私有 CPU Debug 与 GPU Release 求解器现在可在真实保存路径写入上一完整步的材料孔压。取值来自边界处理成功后提交的持久缓冲区，以材料 ID 存入该帧的 `TpiPressureHistory` 子项。原有 22 个粒子数组保持原格式。显式模型和 TPI 冷启动首帧不产生此子项。当前验证使用 Cryer 固定步长、单片、固定材料集合，每帧含 37,173 个土粒及 8 个固定粒子。

两个后端分别跑了显式两步、TPI 两步、TPI 连续四步和读回后续算四步。每一组与该后端的原始对照比较，并按真实 ID、步号、时钟检查压力历史。对于连续四步的每一个后端，四个完整步共检查 148,692 个历史值。第 2 步结束时，若将上一压力换成当前压力，全部 37,173 个材料点的下一步预测都会改变。

在独立的读回程序中，第 2 步写出并关闭原生 PART 后，求解器通过原生库重新打开文件，按材料 ID 检查压力和时钟，再装入 CPU 历史数组或复制到 GPU 的持久设备数组。原有力学状态继续推进两步。五帧共 22 个原生字段、真实时钟和有符号步长差，在各自后端均与连续运行逐位相同。CPU 的三轮孔压和五阶段步长记录逐字节一致；GPU 逐字节核对了三份全材料压力轮次表、全体统计和五阶段步长记录。

此次测试覆盖同进程压力历史往返。跨进程完整续算仍需恢复其他力学、边界和求解器状态；各后端此处的算例限固定步长、无粒子退出。几何复用候选有单独的程序和回归记录。

[CPU 保存](../logs/cryer_livehist_cpu_r1.history_review.json) · [GPU 保存](../logs/cryer_livehist_gpu_r1.history_review.json) · [CPU 读回后续算](../logs/cryer_hist_restore_cpu_r1.history_review.json) · [GPU 读回后续算](../logs/cryer_hist_restore_gpu_r1.history_review.json)

[原生子项写入](../support/CryerTpiPartHistory.h) · [原生子项读回](../support/CryerTpiLoadHistory.h) · [逐字段对照](../support/cryer_live_history_review.py) · [缺失或错误历史的较早检查](cryer_history_io_r3.md)
