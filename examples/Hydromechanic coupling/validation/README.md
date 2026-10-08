# 水土耦合历史验证资料迁移

目录已再次上移至 `examples/Hydromechanic coupling/validation/`，不再经过 `tests/`。下表为当前位置；原始迁移清单保留第一次迁移时的路径，不改写证据。第二次纯移动的 2346 个文件（含后来增加的迁移记录等）哈希全部相同，详见[目录调整记录](../00_upl_precision/目录调整记录.md)。

2026-09-07 按用户要求，把以下三个目录从仓库根 `validation/` 完整迁入本目录。没有删除、覆盖或重新生成历史仿真结果，也没有在迁移工作中编译或运行求解器。

仓库绝对根为 `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b`。下表路径均相对于该根，逐文件旧/新绝对路径可由清单中的 `old_path` / `new_path` 与 `relative_path` 拼接得到。

| 原路径 | 新路径 | 文件数 | 原始总字节数 |
|---|---|---:|---:|
| `validation/tpi_cleanup_release_20260906` | `examples/Hydromechanic coupling/validation/tpi_cleanup_release_20260906` | 503 | 87200800 |
| `validation/u_pl_stage_ab_20260907` | `examples/Hydromechanic coupling/validation/u_pl_stage_ab_20260907` | 1352 | 159659614 |
| `validation/u_pl_time_accuracy_perf_20260907` | `examples/Hydromechanic coupling/validation/u_pl_time_accuracy_perf_20260907` | 484 | 129396903 |

## 完整性与重定位

- [迁移前清单](migration_20260907_before.json)：2339 个文件的相对路径、字节数和 SHA256，以及目录树、完整旧/新根路径。
- [纯移动核验](migration_20260907_move_verified.json)：逐目录 `Move-Item -LiteralPath` 后、修改任何脚本之前，全部文件 SHA256 和目录树一致。
- `migration_20260907_final_verified.json`：路径适配完成后的核验；只允许列出的脚本和 README 内容变化，历史 JSON、日志、输入、源码观测副本和二进制内容仍须全部匹配迁移前清单。
- [运行时重定位助手](relocated_evidence.py)：读取清单中的路径映射，把需要重新读取的历史绝对路径映射到本目录的实际位置。`run_trace_diagnostics.py` 在重放命令时重定位整个路径参数，`analyze_pressure_trace.py` 在读取历史 `reference` 时重定位；都不改写原 JSON。

历史 JSON 内的命令、时间戳、程序/源码/数据哈希及其相互引用是原始 provenance，故保留旧绝对路径。不要批量替换这些 JSON 的路径或哈希。历史日志中的旧位置同样不改。路径重定位仅解决文件访问，不会把历史结果变成当前版本的新验收结果。

仓库根 `validation/` 迁移后为空，已保留该空目录，没有删除。没有创建目录联接或符号链接。

本目录 `.gitignore` 仅补充历史 `Run.out` 的反忽略规则，防止仓库通用 `examples/**/Run.out` 规则使迁移后的日志无法归档；各子目录原有二进制和原始粒子输出排除规则保持不变。其余 `examples` 通用规则仍适用，文件本地保留不等同于已上传云端。本次未暂存、提交或推送 Git。

## 脚本使用与历史版本限制

Python 和 PowerShell 构建工具现在向上查找 `src/VS/DualSPHysics5ReCpu_vs2022.sln` 来定位仓库，而不是假设固定的两级父目录。三个历史目录仍互为兄弟目录，所以相互引用的比较器和旧数据目录结构不变。路径含空格，命令中的脚本和 EXE 路径必须加引号；PowerShell 调用带引号的 EXE 路径须使用 `&`。

三个子目录 README 的可复用命令已更新。再次运行必须采用新标签/新输出文件，现有成果不可覆盖。构建脚本仍复用权威 CPU 对象，运行前应确保对象与拟测试的源码、头文件一致。

特别注意：`generated/JSphCpu_trace.cpp` 是原诊断时刻的源码观测副本，不随生产修改自动更新。不要将它与后续不兼容的生产头文件/对象混用并声称复现原试验。`verify_evidence.py` 原本要求当前生产源码/程序匹配阶段 A/B 的历史哈希；后续生产修复后，该检查预期会拒绝通过，应保留此限制，而不是更新历史哈希。

本次只做迁移和路径适配。数值修复、新试验与对比图应放在新的测试目录中，避免混入上述历史记录。
