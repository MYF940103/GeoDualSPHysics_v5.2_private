# Full3快照CSV剪应力标签修正

根线程核对冻结的JSphGpuSingle.cpp发现，原生SigmaState_ij顺序是(xy,yz,xz)，而新full3后处理snapshot_rows错误地按(xy,xz,yz)命名。只影响`c08_h18_n255_full3_review_r1_snapshots.csv`的两个剪切分量列；源BI4/typed22、真实计算、同前缀比较、孔压/沉降、对角应力迹、Frobenius RMS和既有图中p/κ/J均不受影响。原CPU诊断恢复张量使用正确的ij.x/ij.z/ij.y映射。

保留原CSV及它的不可变分析记录。新脚本只读取已绑定原CSV及冻结源码归档中的字面导出顺序，交换派生列`effective_and_total_xz_Pa`、`effective_and_total_yz_Pa`的值，生成`tests/figures/c08_h18_n255_snapshots_r2.csv`。六个时刻30000行的其他字段字符串逐项保持相同。后续应使用这份修正版快照表；原表的两列不可用于剪切分量解释。

这不是求解器或数值模型修复。不重复原生读取/VTK/分析，不覆盖已有结果，不扫描SHA。唯一派生命令：`D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_n255_snapshots_r2.py`。新检查位于同名logs/*.check.json。
