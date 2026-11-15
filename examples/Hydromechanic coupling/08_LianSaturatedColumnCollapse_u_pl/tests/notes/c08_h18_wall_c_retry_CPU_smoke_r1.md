# CPU 旧有效动态路径的两步对照

新增同名 support 脚本与本说明；独立根线程准入后才执行。采用 case02 既有 public-column 输入，不运行 GenCase，不改配置、步长或边界。修改前私有 CPU Debug 仅替换一个 before mDBC 对象，其余 86 对象及同一原头文件集合保留；修改后为本轮默认 Debug 隔离构建。原 MSBuild 的具体 CL host 架构未捕获，不据此宣称完整编译器身份相同，改由实际原生字节比较检验。

两个明确命名的 before/after 作业依次各运行 2 步、保存 3 帧（0、2.5 µs、5 µs），每组正常求解完成后封存，再独立读取一次。裸 `-mdbc_freeslip` 保留 NoPen 关闭；不使用 C08 的 `:1`。无 half、排水事件、力阶段验收或完整固结结论；此窗也不覆盖新的失败 C 重试分支。

原 public reader 检查 1040 IDs、22 数组、真实时钟及 signed 诊断、3000 个土体 ledger 行、120 个固定 marker 和原安全门。对照五个完整二进制导出、材料/固定 IDs，以及 ledger/fixed CSV 中真实 PosDiv、V、rho、k；初始 signed 诊断也逐字节保留。五个 bin 单独不等于全部 22 数组。所有记录必须相同，未设差异例外。

私有运行目录只补足已封存 Release 的七个配置/DLL 伙伴及 MSVC14.36 的 Debug OpenMP DLL，不写 canonical 或活动 GPU 程序目录。reader 的既有 SHA 只作历史记录，本轮不重算 SHA。任何失败保留实际 call、partial 和已完成 solver seal，不重跑或再次解码。

这只是 CPU 有效路径实施回归，不能证明新的 C 失败分支已由 CPU 运行覆盖，也不代表 C08 物理、论文精度、一般 SPD 或后续两组 ψ 验收。
