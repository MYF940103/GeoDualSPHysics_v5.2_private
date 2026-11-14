# C08 零推进功检查：编译兼容修复 r2

原数学、范围、输出和限制均见 `c08_h18_work_conjugacy_r1.md`，该原件及首次失败全部保留。r1 编译因 Windows 的 max 宏解析 `std::max({…})` 失败，真实编译退出 2、外层 1，尚未链接或调用 force。

新 r2 仅新增同名 C++、builder 和本说明。对 r1 的变化：

- `std::max(…)/std::min(…)` 写成 `(std::max)(…)/(std::min)(…)`，绕开宏展开。
- 诊断 stage/path 的 `c08_h18_work_conjugacy_r1` 改为 `c08_h18_work_conjugacy_r2`；原输入 full301、PRE、86 个物理对象不变。

这些替换已反向恢复逐字符检查，全部原数值表达式与检查预算保持不变。没有重用或覆盖失败 r1 输出。新 builder 只编译 r2 入口，链接原 86 个对象，旧公共程序/源码及 CUDA 不变。通过 build 后仍需根单独决定一次零推进组件，不自动推进任何 solver、native、VTK 或其他 ψ。

唯一结果目录改为 `tests/outputs/c08_h18_work_conjugacy_r2`，程序为其 `_build/C08H18WorkConjugacyR1.exe`（保留程序 basename），新 build/运行收据标签 r2。CLI、原 4 个真实保存态、4 次 baseline force、20000 soil / 40000 group / 7220 wall / 8 summary / 16 virtual 行不变。

原 virtual CSV 的 `symLraw_over_u_s_1`、`symLC_over_u_s_1` 是保留的字段名；实际量纲为 1/m，后处理图和说明须明确该量纲，不能将其误称时间增长率。健康参照仍按预声明间距/支撑规则逐态选取。所有虚探针仅针对 soil 子算子，不闭合墙边界；功差不是已证明的团聚根因或完整能量误差。
