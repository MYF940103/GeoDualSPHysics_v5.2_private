# C08 可恢复清理结果（2026-11-16）

本轮只处理已完成、无依赖绑定的增量链接缓存 ILK；不是数值验收，不改变源码、物理方程或配置。

- 删除83个缓存，原逻辑长度3,151,632,856 B；对应唯一普通NTFS文件流占用3,151,822,848 B。
- 删除前已归档并完整读回验证全部83项的CRC32/长度，ZIP实际占用529,895,424 B。
- 文件流占用减去恢复包后净减少2,621,927,424 B（2.622 GB，2.442 GiB）。此值不计少量清单/日志，不是精确卷空闲增量。
- 另8个已绑定缓存及146个证据不足缓存原位保留；清理后逐项stat不变。
- 原始BI4/NBI4、PRE、typed native、重启链、程序/PDB/obj、源码归档、历史日志、图CSV及所有Fluid/Bound VTK均保留。
- 活动ψ−5预载PID43828/owner36608及未来HG0依赖未更改；未调用求解器、读取器、VTK或构建。

清单：`../logs/c08_cache_cleanup_r1.inventory.json`。本次成功检查与83项恢复清单位于 `../outputs/c08_cache_cleanup_r2/{check.json,archive_verified.json,deletions.jsonl}`，独立复核为 `../logs/c08_cache_cleanup_r2.final_review.json`。

恢复包：`../outputs/c08_cache_cleanup_r2/cache.zip`（529,892,525逻辑字节），保留在本机，不声称已上传云端。每项原路径/CRC/长度/mtime见archive_verified.json；需要恢复某个ILK时，在case根执行：

`D:/anaconda3/python.exe -X utf8 -B tests/support/c08_cache_cleanup_r2.py restore --entry INDEX --execution-authorized`

INDEX取恢复清单的原索引。恢复拒绝覆盖已有文件，恢复原字节和时间戳，不承诺原FileID/ACL。不要重新执行apply。

原r1预检因psutil的Registry/MemCompression虚拟进程名被误作相对路径而拒绝，未建立归档、未删除；失败脚本及收据保留。r2仅修正这两个精确虚拟进程项并兼容历史child字段schema，归档/删除门槛未变。

此前case02/Cryer已经完成的回收不重复计入本轮。少量旧VTK仍有历史回归绑定，本轮不动。数值结果与必要复现资料未按日期或体积删除。
