# C04 GPU source prepare r2：区分源依赖与项目元数据

仅新增 `support/upl_tpi_cryer_gpu_r2_prepare.py` 和本文，作者稿未执行。原 r1 prepare 失败收据保留；原 OUT 未创建，不能覆盖、重跑或伪改为成功。本修复不构建、不运行任何程序、不解码、不生成VTK、不做hash或Git写入。

## 原实际失败与唯一修复

r1 的真实首因是 `Old GPU local dependency path is absent from complete C04 source`。旧 Debug/Release CUDA read tlog 除257个 `R/src/source` 下源/头路径，还记载唯一 `R/src/VS/DualSPHysics5Re.vcxproj`。该文件是项目元数据，不属于265个源/头；原脚本误将其basename加入source集合。

r2逐完整规范路径明确分类：

- `R/src/source/` 子树：必须恰好257个唯一源/头路径，全部basename被C04完整265源涵盖。
- 唯一 `R/src/VS/DualSPHysics5Re.vcxproj`：单独记为1个项目元数据依赖，不能标成header或追认其历史内容。
- 任何其他仓库内路径：继续拒绝，不扩大允许集。

采用的项目内容仍只从明确Git提交 `de2492afb5be33e9077f8e4a96bfe755b0ffc7ed` 恢复，并核实际97CL/14CUDA/111链接basename闭包（含两个`.h.obj`）。tlog证明历史访问路径，不证明当时项目文件内容；r2不读取当前公共VS项目来代替历史blob。

## 数值资产保持原样

继续使用原作者 `upl_tpi_cryer_gpu_r1.h`、`upl_tpi_cryer_gpu_r1.cuh` 两文件，未修改其字节、namespace、环境接口、source/role16个device fixtures或侧车格式。三TU的18个局部hook也原样保留；不整TU搬C02，无原header/class ABI/公共kernel签名变化。

依然是C04真正XYZ/freebody/HG0、37181 IDs（8 fixed＋37173 soil）、dt2^-20、NstepsBreak1–128；完整double XYZ/Taylor/ρwDa、bodycentre/bodyradius2参数与原separation门、原force/AV/grad/材料/source-clock保持。B/C为α.5/0、β0单次leading-LP defect，A缺省不进入；不宣称paper literal LF/二阶/全隐式或物理验收。

HG0无alloc/snapshot/Stats/RateInfo/getter/第四TU，core七类检查保留、HG计数0；原CUDA RN/fast-math/FTZ不变。28列侧车仍 `UplTpiCryerGpuR1.*`、stage `upl_tpi_cryer_gpu_r1`，marker仍CryerSourceRoleFixtureR1的真实stdout。原两个helper和完整数值说明见保留的 `notes/upl_tpi_cryer_gpu_r1.md`，r2不赋予它们新的物理通过状态。

## 新独立准入与输出

新stage为 `upl_tpi_cryer_gpu_r2.prepare_admission`，要求 `passed=true,prepare_only=true,inputs=[stat...]`。输入在r1清单基础上改用r2作者Python/note，继续绑定原r1 h/cuh、C04完整source prepare/manifest/265源/两docs、旧Debug/Release build/call及真实 `CL.read.1.tlog`、`CudaCompile.read.1u.tlog`、`link.command.1.tlog`，以及C02冻结r2数学/guard helper来源。

另绑定实际 `logs/upl_tpi_cryer_gpu_r1.prepare.json`；它必须仍passed=false、上述精确first_error、partial_output_preserved=false，原r1 OUT仍不存在。此条件只证明该次source-only前置失败，不恢复旧执行，不启动求解。

输出为全新：

- `outputs/upl_tpi_cryer_gpu_r2_source/source/`：265基线源＋原字节r1 h/cuh。
- 同新root的VS/docs/base_manifest/source_diff。
- `logs/upl_tpi_cryer_gpu_r2.prepare.json`。

已有任一新root/receipt拒绝，失败保留first_error和新partial，不自动重试。成功receipt继续提供 `source_root/files/source_diff/changed_sources/new_private_helpers/class_or_header_ABI_changed/HG_adapters_called` 等原schema。`old_GPU_closure`把总本地路径258分列为source/header257和project metadata1，并明确历史project字节未获证明；`prior_failed_prepare`绑定原失败。

后续未执行的full111 GPU Debug builder只需改消费的新prepare路径，沿用原构建tag/真实SDK10.0.22000/CUDA11.7/v14314.36 recipe。全111必须重新编译，不混旧对象。所有现C02/C04程序/源码/archive、活动CPU/GPU、暂停C08及正式结果不变；本稿不运行这些后续动作。
