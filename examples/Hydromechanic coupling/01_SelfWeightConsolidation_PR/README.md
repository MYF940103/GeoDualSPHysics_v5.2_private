# 01 自重固结：入口与文件索引

整理日期：2026-10-08。当前求解器基线为无孔压精度补偿的 float u-pw PR；旧 TPI、u-pl 和精度试验不属于当前正式模型。本次仅补充索引，不改 XML、计算结果或历史结论。

## 正式入口和受保护结果

| 工况 | 根目录 XML | 根目录 BAT |
|---|---|---|
| Stage1 自重初始化 | `CaseSelfWeightConsolidation_Stage1_Def.xml` | `xCaseSelfWeightConsolidation_Stage1_win64_CPU.bat` / `..._GPU.bat` |
| Scenario2 从 Stage1 续算消散 | `CaseSelfWeightConsolidation_Scenario2_Def.xml` | `xCaseSelfWeightConsolidation_Scenario2_win64_CPU.bat` / `..._GPU.bat` |
| Scenario1 解析初始场消散 | `CaseSelfWeightConsolidation_Scenario1_Def.xml` | `xCaseSelfWeightConsolidation_Scenario1_win64_CPU.bat` |

根目录 `xCaseSelfWeightConsolidation_win64_CPU.bat` / `..._GPU.bat` 串联 Stage1 和 Scenario2。对应三个 `CaseSelfWeightConsolidation_*_out` 均为受保护结果，保持原位；已有结果的程序版本以各自 `Run.out` 为准，不因当前程序更新而重新归属。

**重跑前注意：现有部分 BAT 会删除同名输出，GPU 总流程还传入 `-force`。本次未改变这些既有行为，不要用正式入口试跑或覆盖现存结果。新实验须在 `tests` 使用独立名称与输出路径。**

## 必须保留的重启依赖

- 正式 Scenario2 默认读取 `CaseSelfWeightConsolidation_Stage1_out/data` 的 `Part_0060.bi4`、`PartExtra_0060.bi4` 及相应头文件；完成 Stage1 不等于可以删除它。
- 旧 TPI 诊断从 `tests/outputs/CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out/data` 的 Part300 启动，该 PR 参考结果不属于待删除的 TPI 输出。
- `02_TerzaghiConsolidation_q0_PR/tests/support/pore_double_stage1/run_regression.py` 的历史自重短测，还引用本算例的 `tests/outputs/CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out` 生成输入，以及 `tests/outputs/CaseSWSt1_MLSDirect_GPU_out/data` 的 Part56。保留这些跨算例依赖。

## 文件放置

- 根目录：正式 XML、BAT 及对应正式 `_out`。
- `figures`：正式图表；沿用现有目录名，不另外建立 `figure`。
- `support`：正式后处理和说明；`videos`：已有视频。
- `tests`：临时配置、计算、图表和实验记录，见 [tests/README.md](tests/README.md)。
- `support/diagnostics`：既有历史诊断，保留原路径和记录，新试验不再写入此处。
- `figures/figures`：历史混合材料，含 PPTX、TIFF 和 q0 图件，暂保留原位待确认归属。q0 同名图/CSV 与 02 当前版本并非已确认的重复件，不按重名删除。

## 历史试验状态

`tests` 中 `CaseSWSc2_TPI_alpha05*` 为退役诊断，不是可用 TPI 方案：两组 window 运行虽正常退出，却分别排除了 999 和 1000 个粒子；onestep 仅运行一步。当前求解器明确拒绝旧 TPI 参数，不应删去参数后冒充 TPI 重跑。

原记录保留，不把历史“建议继续开发”的文字当作当前已实现功能。当前文件状态以本索引和 [tests/README.md](tests/README.md) 为入口，数值证据仍以原始日志和历史记录为准。
