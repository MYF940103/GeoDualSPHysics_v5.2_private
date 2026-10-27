# Cryer：严格Cartesian截球的GenCase-only几何smoke

## 位置与执行边界

只新增 `tests/support/cryer_cartesian_geom_r1.py` 和本说明，先供完整审阅。默认只显示帮助。

- `--prepare`：生成新的 `tests/configs/cryer_cartesian_geom_r1_Def.xml`、`xcryer_cartesian_geom_r1_win64_GenCase.bat` 及 `tests/logs/cryer_cartesian_geom_r1.inputs.json`，不运行任何程序。
- `--run-geometry`：仅执行一次GenCase到 `tests/outputs/cryer_cartesian_geom_r1`，保存新的 `.log`、`.run.json`、`.check.json`。拒绝覆盖/重启已有同名输出或证据，没有队列、watcher或求解器命令。

本轮不会由编写者执行prepare或GenCase，主代理读完后再决定。正式根XML/BAT、原始结果和生产源码不变。

## 唯一几何改变

源输入是已绑定的 `tests/configs/cryer_grad_peak_r1_Def.xml`。仅将原FrDraw的drawsphere块换成显式33401个 `dp*(ix,iy,iz)` 点，`ix,iy,iz=-20..20`，只保留 `r<=.05+1e-12 m`。点列表顺序、shape、little-endian float64预期坐标总bytes和SHA256写入prepare清单；不另存大点云文件。保留dummy8及源XML的全部其余文本，包括所有物理参数、grad1、阻尼、原始外载、排水和时间设置。此测试BAT没有运行这些积分设置的命令。

使用本地已有标签 `<setactive drawpoints="1" drawshapes="0"/>`、`<setfrdrawmode auto="true"/>`、`<drawpoints><point .../></drawpoints>`，结束后恢复FrDraw=false及drawpoints/drawshapes=1。依据为 `doc/xml_format/CaseTemplate.xml` 的drawpoints/FrDraw定义，以及 `examples/Elastoplastic_basic/07_TestPerformanceCoupling/CaseGranularOnBlocksWall_Def.xml` 的自由点与shape分离模式。没有发明clipsphere、修改半径或通过缩放质量补体积。GenCase仍可能对自由点执行重合检查/排序，必须核验输出而非假定它保持所有坐标。

新球R=.05、dp=.0025；相对FrDraw37173个土粒子，节点数变为33401，中心物理球 `r<=dp+1e-12` 从18变为7且包含原点。native体积求积也改变，不能把几何生成成功称为动力等价/精度通过。几何球面点30不等于生产FSType2/3排水粒子数。

## 输出读取和明确限制

现有只读reader使用 `LoadFilePart` 并要求应力、孔压、FSType等求解器数组，不能直接读取GenCase的case BI4。因此本阶段先解析GenCase的原生legacy VTK POINTS（支持其声明的BINARY/ASCII float或double），核验33401唯一坐标、与预期在同VTK保存精度下的逐点集合完全一致、半径/最近邻分布及dummy8完全一致。生成XML必须保留33409总粒子、8固定/33401土粒子及rho=2100、dp=.0025、h=.0045、mass=rho*dp³；这些是XML元数据，不伪称读到了native每粒子数组。

GenCase VTK通常保存float坐标，即使case BI4写为double。预期坐标为double的严格截球；VTK读回与预期float32量化集合做精确比较，另如实报告VTK rmax和量化误差。由于float保存的 .05 自身可能略大于 .05，不能把VTK nm级外突解释成原生double几何外突，也不能据此宣称已经通过严格native double半径门。结果明确 `native_double_coordinates_verified=false`；case BI4、生成XML/VTK/日志全部保留并绑定SHA，后续可新增专用native读取再复核，不扩大本阶段范围。

同样明确 `native_FSType_verified=false`：生产自由面/umbrella分类必须在独立后续阶段检查，不能从30个几何球面节点或GenCase mk推断排水集合。所有结果的 `physical_acceptance=false`。保留GenCase关于自由点功能、零重力和VTK cells的警告。

## 审阅后的命令

从case根目录分别运行，禁止直接启动任何DualSPHysics BAT：

```powershell
D:/Anaconda3/python.exe -B tests/support/cryer_cartesian_geom_r1.py --prepare
D:/Anaconda3/python.exe -B tests/support/cryer_cartesian_geom_r1.py --run-geometry
```

prepare将绑定程序/config、源输入、新XML/BAT、脚本/说明、已有helper及本地XML模板；run前后核对这些身份。若GenCase失败、改点/合并、数量或元数据不符，保留所有输出和具体错误，不调半径、质量、阈值或自动重跑。
