# Cryer 旧版入口演练副本归档

三个旧副本位于 C04 的 `tests/outputs/hfe1`。WinPS 正式安装从 `winrelease` 读取；从固定 Git 记录重建 59 份输入的工具不读取这三个副本。第一份 `overlay` 仍是历史演练检查器的默认输入，原位保留。各 `*_entries.json`、BAT／GenCase 实际运行、源程序、已有归档、正式根、预载和回退备份均原位保留。

| 原相对目录 | 文件数 | 原逻辑字节 | 原 NTFS 分配字节 |
|---|---:|---:|---:|
| overlay2 | 58 | 502103 | 645184 |
| overlay3 | 58 | 502648 | 645184 |
| overlay4 | 58 | 502978 | 645184 |

恢复包内有 174 个原文件、36 个目录项和一份 `recovery_filetimes.csv`。已从刚写入的 ZIP 逐个解压到内存，与源文件直接比较全部字节，并核对全部相对路径和目录。原文件共分配 1,935,552 B，ZIP 逻辑 484,501 B、分配 487,424 B。测量使用单硬链接文件的 `FileStandardInfo.AllocationSize`。文件数据流分配差为 1,448,128 B，此数值不包含目录、MFT、此索引和其他同时进行的任务。[可恢复 ZIP](../outputs/hfe1/retired_overlay2_4_r1.zip)

## 恢复

先将 ZIP 解压至独立空目录，确认原目标不存在，再将所需 `overlay2`、`overlay3` 或 `overlay4` 目录放回 `tests/outputs/hfe1`。若需精确重现修改时间，`recovery_filetimes.csv` 中每条 `Name` 对应相对文件路径，`Ticks` 对应 UTC FILETIME，可用 `DateTime.FromFileTimeUtc` 与 `File.SetLastWriteTimeUtc` 恢复。

## 实际磁盘状态

自动审批拒绝了移除这三个旧文本树的 PowerShell 操作（`blocked by policy`）。所有原件原位保留，已回收 **0 B**。当前原文件与 ZIP 的数据分配共 2,422,976 B，较归档前增加 487,424 B，另有本索引的开销。上列 1,448,128 B 仅为未来允许清除原副本后的文件分配差。
