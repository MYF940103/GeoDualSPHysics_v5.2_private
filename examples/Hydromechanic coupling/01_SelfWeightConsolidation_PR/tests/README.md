# 01 测试文件索引

整理日期：2026-10-08。测试材料按用途分类，已有路径原位保留，不因“计算完成”删除重启数据。

## 目录约定

| 位置 | 内容 |
|---|---|
| `tests/` | 测试入口 BAT 和本索引 |
| `configs/` | 测试 XML；必要时只增加一层清楚命名的试验族 |
| `support/` | 测试脚本或辅助源码 |
| `outputs/<试验名>/` | 独立计算输出及程序必需的 `data` / `particles` |
| `logs/` | 构建、运行和转换日志 |
| `figures/` | 测试图和统计表 |
| `notes/` | 结论、来源和清理记录 |

新一轮实验先确定名称和以上输出位置，不在 case 根目录放临时文件，不再叠加多层 run/date/debug 目录。XML/BAT 从同类现有示例复制最小修改，格式规范参考仓库 `doc/xml_format/_FmtXML_ElastoplasticSoil.xml`；未经验收不替换正式入口或结果。

## 保留的 PR 对照与依赖

- `configs/CaseSWSt1_{HeadN,MLSDirect}_Def.xml`、`CaseSWSc2_{HeadN,MLSDirect}_Tv2_Def.xml` 及对应 BAT、输出和图件：历史边界方法比较，保留，不等同于根目录正式验证全部通过。
- `outputs/CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out/data`：旧 TPI 的 Part300 参考来源。
- `outputs/CaseSWSt1_MLSDirect_GPU_out/data`：既有重启链的 Part56 来源，还被 02 的历史 double 短测引用。
- 其他 PR、密度率、孔压率分量、加速度及边界诊断原位保留；各自结论在 `notes`，不作为新模型的默认配置。

## 原位退役：旧 TPI

同组材料不得拆散或误标为有效结果：

- 两份配置：`configs/CaseSWSc2_TPI_alpha05_from_MLSDirect_p0300_onestep_Def.xml`、`..._window_Def.xml`。
- 十一个运行/转换日志：`logs/CaseSWSc2_TPI*`。
- 三个输出：`outputs/CaseSWSc2_TPI_alpha05_from_MLSDirect_p0300_onestep_XMLBC_GPU_out`、`..._window_GPU_out`、`..._window_XMLBC_GPU_out`。

三组从上述 PR Part300 续算。window 两组分别排除 999 / 1000 个粒子，不能因日志末尾 `code=0` 就认为验收通过；onestep 仅一步，不证明稳定性或效率。旧配置含当前求解器不支持的 `PorePressureIntegrationMode` / `PoreTpiAlpha`，仅作为历史证据保留。

现有材料已经按用途分类；此次不搬迁输出，不重写旧结论，不删去失败记录。以后如需压缩退役实验，应成组保存相对路径、校验值和依赖说明，再决定是否移除展开副本。
