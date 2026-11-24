# C08 历史入口归档

根目录归档了 16 个已退役或已锁定的 BAT，包括 r3 三组 CPU/GPU 和预载入口共 8 个、r4 三组 CPU/GPU 共 6 个，以及 r5 对应 ψ = +2.5°、−5° 的两个锁定入口。r5、r6 的 ψ = 0° GPU 入口保留在根目录。原始 BAT 共 4,077 字节，ZIP 为 6,545 字节。[逐文件清单](../../support/legacy_launchers/manifest.json) · [原始 BAT 归档](../../support/legacy_launchers/launchers.zip)

旧运行器仍按原路径读取根目录的 11 个 XML，对应的原始字节存放在 `support/frozen_xml`。预载、历史求解输出、程序、源码快照、粒子 VTK、图和 CSV 均保留。历史审查如果需要已归档的根入口，请先恢复对应名称，再运行原审查。

在 C08 根目录的 PowerShell 中，第一条命令只检查归档。第二条示范恢复一个历史入口，去掉 `-Name` 及文件名可恢复全部 16 个。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\support\legacy_launchers\Restore-LegacyLaunchers.ps1" -CheckOnly
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\support\legacy_launchers\Restore-LegacyLaunchers.ps1" -Name xCaseLianSaturatedColumnCollapse_psi2p5_shared_r5_win64_GPU.bat
```

[恢复脚本](../../support/legacy_launchers/Restore-LegacyLaunchers.ps1) 在写入前检查 ZIP 和原文件的 SHA-256，遇到同名异内容文件会停止。归档时已在空目录恢复全部 16 个入口，逐个核对原字节和修改时间；第二次恢复写入数为零。

本次另移除了 `tests/support/__pycache__` 中的 8 个可重建 Python 字节码缓存，合计 376,202 个逻辑字节，对应 Python 源文件均已核对存在。此前的增量链接缓存清理单独记录。[此前清理记录](c08_cache_cleanup_outcome_r1.md)
