# Shared preload CSV postcheck hotfix r1

此补丁修复 r2/r3 启动器的**完成后检查**，不改变 XML、程序、物理参数、预加载、接收或输出数据。旧 ZIP/manifest 保留原样；补丁需另行分发并覆盖两个对应 launcher，同时放入新检查脚本和根目录检查 BAT。

服务器若已显示 `Finished execution (code=0).`，随后出现日语 `メンバー "7060" は既に存在します。`（成员 7060 已存在），这是旧 PowerShell `Import-Csv` 把 `#RunName;...` 首行当成注释，继而把含重复数字的第一条数据当作表头造成的检查异常，不能据此判断求解失败。**不要重跑已完成的 10 s 预加载，不删除或改写 source output。**

截图中的两条 warning 均不是本次后检查失败的原因：

- `The execution will be cancelled after 4000000 simulation steps.` 是原 BAT 的 `-nsteps:4000000` 计划停止：在 10 s PRE 事件保存后结束 source。
- `The kernel Cubic Spline is not available in GaugeSystem, so kernel Wendland is used.` 表示 GaugeSystem 测量核使用 Wendland 后备；不表示主动力学核被切换。

把补丁文件放到 case08 原位置后，双击根目录 `xCheckLianSaturatedColumnCollapse_preload_win64.bat`。它只枚举已存在的 r2/r3、CPU/GPU source output，读取 Run.csv，并检查原 `Steps=4000000`、`PartFiles=1001`、`PartsOut=0` 及 `data/Part_1000.bi4` 文件存在；不运行 GenCase/solver/receiver，不创建或覆盖检查记录。没有对应目录或任何一组失败会返回非零。

检查通过后，按**同版本、同后端**的三个 receiver BAT 依次运行。r2 source 配 r2 receivers，r3 source 配 r3 receivers；GPU0 不要并行乱点。专用 native loader 仍须读取真实 PRE，验证 schema、材料版本、elastic source 资格、完整状态与 source clock。CSV/文件存在检查不代表 PRE 物理认证、10 s 平衡或完整塌陷验收已经通过。

命令行只读检查（默认使用正式源计数）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File support/check_lian_preload_schedule_r1.ps1 -SourceOut CaseLianSaturatedColumnCollapse_shared_preload_r3_GPU_out
```

`-ExpectedSteps`、`-ExpectedPartFiles`、`-ExpectedPartsOut` 和 `-ExpectedPrePart` 仅供独立局部 fixture 测试使用；正式 launcher 不覆盖默认值。脚本只接受首行 `#RunName;` / `RunName;`，也自动识别逗号形式；仅去掉表头的单个 `#` 后调用 `ConvertFrom-Csv`。无法识别、缺字段、多行、非整数或不符计数均严格失败并保留数据。
