# X0 私有 CPU 构建

仅构建，不运行help、solver、reader、VTK或新通知器。默认关闭回归和开启原型必须另外审阅及准入。公开源码、正式输入、原对象目录、程序和全部原始数据不改。

读取原schema2的权威VS生成CL/link命令，使用MSVC14.36.32532、原DebugCPU或ReleaseCPU ABI与浮点选项。只编译两个新overlay，85个旧对象含原main保留，总87个。不覆盖旧obj/PDB/iobj。头文件取已冻结的160份私有归档头，不从当前公开source读取。额外C++17只用于私有辅助类型；实际默认OFF回归仍是必要条件。

输入：`c08_tpi_x0_prepare_r1.check.json`、`outputs/c08_tpi_x0_r1_build/`的CPU/Single/helper/diff；输出：独立`outputs/c08_tpi_x0_build_r1_DebugCPU/`或`_ReleaseCPU/`，同标签logs保存真实工具出口、依赖与stat。已有失败/部分产物禁止覆盖重跑。stat身份不明才补必要哈希，不扫原源码/对象/BI4。编译成功不等于默认关闭等价、算子、积分或物理验收。
