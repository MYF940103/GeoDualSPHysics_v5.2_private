# 真实PRE末态与collapse第一保存帧

只复用服务器回传r2 GPU PRE的已导出 PartFluid_1000.vtk，以及r5已解码typed22，按5000个土粒native ID配对；不重解BI4、不运行求解器。VTK压力等float字段为big-endian，原生导出为little-endian；显式解字节序后比较。VTK坐标只有float32，不能用它声称原Posd逐位继承。

第一collapse PART是实际t=10.010000000377431，减真实PRE末时刻10.000000000374257为约.01秒，已完成4000次新更新。因此其压力差属于PRE→撤墙→4000步演化，不能作为导入瞬间的复制误差。

新脚本保留所有土粒，输出统一色标的PRE/第一帧完整孔压图及逐材料delta，CSV另列固定P0、Excess和FS。P0逐float32位比较5000个ID；完整p的导入瞬间独立观测仅复用现有trace最初三个PONDING记录，明确不是全5000ID的t0实测。Excess定义为p−固定初始P0，不是当前水静压力参考。

根审阅后单次执行：`python -X utf8 -B tests/support/upl_c08_preload_first_frame_compare_r1.py --execution-authorized`。所有新图CSV/check在 tests/figures 同名前缀；拒绝覆盖，不改原字段或名义时钟。没有新增物理验收门或真正零步快照。
