# C08 radial native r1：复用读取器的单次适配

仅作者资产；未运行、未导入作者 Python、未启动 reader/solver/build/VTK/Git/通知。脚本 support/c08_h18_radial_native_r1.py 必须由根全文审阅及每个 profile 独立准入后才可执行。它不生成新的读取器、不重解码旧控制、不修改物理结果或 PRE。正式/旧失败记录原位保护。

## 三个封闭 profile 和未来入口

未来入口为 python -B support/c08_h18_radial_native_r1.py --profile PROFILE --execution-authorized。本命令在这里仅供审阅，不代表已准入。

| profile | actual run tag | native保存数/最后completed step | 范围 |
|---|---|---|---|
| off1 | c08_h18_rv_radial_off1_GPU_r1 | 1/2000001 | Release默认OFF首更新；全22数组/实际time/layout/signed前缀需逐byte等原AS03 |
| debug2 | c08_h18_rv_radial_debug2_GPU_r1 | 2/2000002 | Debug真实2更新+既有memcheck通过；不是Release位真 |
| window | c08_h18_rv_radial_window_GPU_r1 | 91/2180000 | 仅将来另行根准入，不能因存在入口自动运行 |

每组源 run 必须 passed、solver_completed、原实际 tool/Win32/solver退出0、无所有权故障，且新radial schema3/operator/env/114对象及private host/CU/header、原 schema2 PRE、实际输入、计划和 Run.out/Run.csv 绑定不变。三组不互相自动调用。typed22读取器不证明RV算子；成功只表示这一组原生检查及注明的实施前缀。

复用 logs/c08_h18_rv_native_r1.build.json 指定的 C08H18RvNativeR1_win64.exe，原7-object reader、无JSph对象。原工具支持 off1/debug2/window，输出 metadata stage 仍为 c08_h18_rv_native_r1.metadata，不重标它为radial实现证书。原22-array core和17-key material CSV完全不改，所有argv预先转成str，数字float32比较使用struct.unpack/pack取得数值，不使用返回packed bytes的旧m.f32。

每组 native output 为 outputs/RUN_TAG/native_r1；工具调用标签 RUN_TAG.native_r1；logs下独立 .start.json/.call.json/.log/.check.json。成功新receipt仍用标准 source_run、reader_build、actual_call、native_completion、metadata、files、consumed、consumed_stats_unchanged、reader_invocations1，便于后续离线审查复用。

## 根单独准入合同

logs/RUN_TAG.native_r1.admission.json 必须含：authorized=true、phase='native'、profile、allowed_job=RUN_TAG、execution_script与本note的当前stat、source_run=原passed run stat、reader_build=原reader build stat、root_thread_id=当前原root线程、automatic_solver=false、automatic_next_job=false。脚本不创建或猜测准入；window也需独立文件。

先看已有receipt：仅当通过、绑定相同原run且所有已消费/生成stat仍一致时直接复用并返回，启动次数为0。已有失败receipt、partial native目录或原call/log/start即拒绝；不能覆盖或再解码。真正调用前还检查 exact reader exe 或该专属输出是否已有活动owner。原程序和计划已绑定，但不因owner进程退出就推断reader完成。

唯一调用使用既有 m.invoke，保存工具Popen和Win32句柄退出、实际child exe/argv/parent及owner创建时间。reader_launch_attempts是尝试；只有存在实际child才记reader_invocations。程序正常返回与native core completion分开记录；post-native的字节/时钟审查失败时保留全部原输出，只能新增离线修复派生，不再调用读取器。若缺少有效句柄记录，不声称成功或虚构退出。

## 保留的原生门及覆盖

读取器逐帧检查6805 IDs（5000土/1805固定、retire255/keepfalse）、22 typed数组212 bytes/ID、P0继承位、κ相对PRE非减、固定marker、ρ缓存位、J/n/V/ρ/k ledger、有效FS2/3、NoPen几何和完整material/source契约。适配器核completion的全帧计数：ledger=5000×samples、P0=6805×samples、fixed=1805×samples、ρ/κ=5000×samples；时钟<=1e-14、ledger相对<=5e-13、原signed dterror<=1e-14（不取绝对值）、几何负x/z观测0。原FS条件、NoPen/ReactionClosed=false未改变。

解析只复用 c08_h18_storage_review_r2.typed 的schema/dtype/layout/clock原语，不运行旧完整case分析。每个新native保存时刻还用原 source actual_end 后 scalar +=5us 按真实completed步逐次重放，检查原completed/saved=completed-1、二进制内真实time、clock CSV的11列及全部native IDs。window仍是原91计划：首PRE+1，Part1..89为2000001+2000part，末2180000；绝不用n*dt替代scalar时钟。Part0是真实更新后，不制造PRE/t=0接收save。

输入/输出只必要size/mtime一次绑定；每个新BI4在reader前记录并在结束核不变，不扫描SHA，不重新验证旧源码/对象。旧reader的真实metadata仍明确 backend_argument=GPU但不能仅靠它证明硬件、RV/新candidate、完整coupled稳定性或物理精度；这些依赖真实run/source/其他实施及物理审查。

## OFF1真正字节回归

原控制为已封存 logs/c08_h18_as03_n255_native_r1.check.json 的 genuine91结果。只读取原native schema/layout以及第一记录做比较，不重新reader或完整旧分析。typed22.bin头保留(6805,22,1)与(6805,22,91)各自真实值，比较其后第一个完整记录（8-byte actualtime+全部22数组）；layout原bytes必须相同；clocks.csv原header及第一整行（包含signed dterror）必须相同。无改头、插值、删字段或初始诊断豁免。OFF四个radial侧车应全不存在。

Debug2不与Release作位真要求。ON通过native检查也不等于径向机械证书的独立复核；原新runner已经绑定schema3/87列/5制造/8fixture，但本工具不会用旧vector form/contraction审核替代它，也不把MFG hypothetical committed_*当真实提交。没有5Pa跨模型等价、团聚修复、正式物理验收、全程或其他ψ自动准入。
