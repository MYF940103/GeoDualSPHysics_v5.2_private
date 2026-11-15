# C08 十项 C质量重试组件：仅host构建

仅新增 support/c08_h18_hg_wall_retry_component_r1_build.py 与本文。组件 main 及十项参数/门由另一作者的 support/c08_h18_hg_wall_retry_component_r1.cpp 和 notes/c08_h18_hg_wall_retry_component_r1.md 定义；builder 不修改它们，也不生成或选择新的参数。作者阶段只文本/AST审阅，无import、copy、decode、CL、link或组件执行。

## 精确来源

新候选CUDA必须来自已通过的 logs/c08_h18_wall_c_retry_GPU_r1.build.json，消费其中 replacement_physical_object 的实际path/stat、真实owned NVCC/link出口和完整frozen276源。原 schema2非main对象/权威host recipe来自既有 opt Release真实build/tlog。新候选必须替换这同一个原 JSphGpu_ker.cu.obj，不能使用旧核、Debug核、被拒printf核或另一个未封存对象。

同时绑定根已应用 c08_h18_wall_c_retry_r1.source.json 的两份source inverse证明、当前public/candidate及原kernel A/I因果组件 memcheck check。这里只消费已完成准入，不再次调用source transformation，也不把参数组件等同于新物理算例。原root公开改动和所有旧r1/r2失败/成功组件输出不被覆盖。

## fixture只复制，不再解码

从通过的 c08_h18_hg_wall_packet_component_r2.build.json 采用其902394字节fixture.bin和fixture_metadata。该r2 fixture本来采用r1已封存的唯一rawhex解码，r2 raw_hex_input_calls=0；此轮继续为0。builder不导入fault reviewer、不读取11份原始CSV、不重新pack rawhex，仅复制整个bin并逐byte确认等于原文件；新的fixture.json记录原fixture/描述/来源和新的目标stat。

组件仍自行严格读原magic/版本/typed extents。所有十项fixture的常量、仿射场、target-only选择与拒绝期望只存在已审CPP；builder不生成第二套参数定义、插值或修订原packet。

## 链接闭包与编译

原schema2权威link共113对象；剔除main后为112 non-main。将其中唯一原CUDA对象换成已完成的candidate CUDA对象，得到111个原non-main +1candidate CUDA，再加本轮新host main1，仍113。builder逐项保持原对象顺序与全部库，只替换main、该CUDA对象和四类输出路径。新完整物理GPU程序的114对象闭包在它自身builder封存；此独立组件故意采用原schema2的113闭包，不误称包含opt HG三对象或执行了完整GPU程序。

使用原MSVC14.36 Release host /MT /Zi /fp:precise、无PCH的GPU host recipe编译组件main，改私有include根、source、Fo/Fd和sourceDependencies。默认AppInfo全局定义已由新main包含，保留原3参构造。环境统一key大写并固定原cl目录优先，不增加CUDA编译或device-link；实际只有CL1次/link1次。compile完成后封存新host obj，再进行link，并核对所有消费stat不变。

头文件取新候选frozen276源，sourceDependencies中该根下include必须在完整封存清单；实际物理CUDA仍是新candidate同一对象，不换Debug版本。九个runtime伙伴独立按原bytes复制，canonical程序、原程序/PRE/归档均保护。成功build receipt记录113对象、原/新CUDA、host recipe和actual calls；失败保留真实工具出口和partial，不自动重试。

## 准入与后续

根线程需完整审阅builder和CPP/两份note后，单独创建 logs/c08_h18_hg_wall_retry_component_r1.root_build_admission.json：authorized=true、allowed_stage=标签、execution_script/component_source/component_note/note当前stat、source_build=opt Release、candidate_build=新GPU候选build、candidate_source=根source.json、original_component_build=r2组件build、original_kernel_proof=r2.memcheck.check、当前root_thread_id、pack_and_build_only=true、automatic_component=false、automatic_solver=false、automatic_reader=false。

构建命令为 D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_hg_wall_retry_component_r1_build.py --execution-authorized。输出位于 tests/outputs/c08_h18_hg_wall_retry_component_r1_build；host对象位于无空格TEMP同tag，真实CL/link calls及check位于tests/logs。所有新输出必须不存在，既有partial也不能覆盖。

构建不调用program/help、compute-sanitizer、native、VTK或solver。后续只有根单独准入的一次组件运行；十项全部通过也仅为这组输入的实施/安全证据，不证明一般SPD保持、物理修复或完整塌陷验收，不自动接full3、其他ψ、half或PRE。常量/仿射/拒绝门详见组件note，builder不放宽它们。
