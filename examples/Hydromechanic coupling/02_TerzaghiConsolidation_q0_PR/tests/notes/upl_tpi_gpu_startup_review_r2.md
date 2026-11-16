# GPU A/B/C startup science r2：只消费已通过的独立审查

本稿新增`support/upl_tpi_gpu_startup_review_r2.py`及本note，未执行。
冻结/Git保留的science_r1不改。相对r1只有本版stage/note/products身份与load的
review版本选择：A读实际`.native_review_r4.json`，B/C读`.native_review_r5.json`。
三个物理job标签仍GPU_Release_A/B/C_startup015_r1，原生导出全部保持`_native_r4`。

B/C r5是纯review的RN-f32/FTZ重放修正，不重跑native或solver；它保留r4 failed
作为诊断，并以实际Release PTX证明原编译指令的转换语义。science不重新运行该
审查、不添加新FTZ/half/theory门，只要求原已passed的准确review身份及原门不变标志。
A的native_review仅提供五导出的实际时刻join；22rawbit证据仍须独立raw22compare，
不能由五导出或common26替代，本科学脚本不新增该门。

references/describe/figures/science与r1逐字相同，仍继承CPU已测数学定义。
全部344帧/1040IDs/22数组资格、100层真实时钟/ledger/Jnρ、孔压/材料顶部底部沉降、
六分量总应力/Q/交替X模态和原post-.1s100Pa最大层/顶部gap门均保留。
只改load路径来源；runtime分类使用实际Hardware的gpu casefold和Pos-Cell模式。
finiteKw(A)/M0(B/C)未拟合准静态伴随曲线仍不代表精确动态真值；不引入新精度阈值。

root独立准入为stage=`upl_tpi_gpu_startup_review_r2.admission`、passed/offline_only=true。
inputs沿r1全部实际消费stat，但本script/note、A-r4/B-C-r5 reviews必须准确列入；
每组completion/columns/native_ids/physical.bin/soil_n.bin/clock.bin/history/ledger/plan/
Run.csv及原XML/两definition源文件均原样。无需BI4或旧objects/hash扫描。

只写新`figures/upl_tpi_gpu_startup_review_r2.*`对应history/profiles/modes/cross CSV、
metrics.json及三PNG，新check为`logs/upl_tpi_gpu_startup_review_r2.check.json`。
已有任何输出(含partial/failure)拒绝覆盖。只有三组真实review passed后才可执行。
物理、完整周期、重启、GPU性能基准仍不自动验收；无solver/native/build/VTK/下一任务。
