# GPU零步右墙退休审查

组件仅执行一次，置于compute-sanitizer内。实际工具与目标Win32退出均0，memcheck零错误/泄漏，实际本机RTX3050。260个右墙原生ID退休，剩6800=5000土体+1800固定点；逐ID土体持久状态位保持，GPU额外κ增量诊断数组也检查5000次。新的有限正自由面压力按实际分类投影，其余历史不重置。所有真实边界cell查询均无退休ID，剩余墙闭包可刷新。

GPU通过一次性下载当前Npb的Id/Code并上传标记后的Code，再调用原有完整divide完成退休，没有新生产CUDA核或接口。制造字段是传输测试，不是五秒初态、物理赋σ、动量或渗流求解。两端零步结果不等于实际15/10秒撤墙时间积分或塌陷物理接受；生产事件尚待接入。

CPU与GPU的5000共同土体ID制造主字段最大绝对差及分类差记录如下（描述性对照，不是半步长或理论门槛）：

{
  "primary_max_abs": {
    "p_before": 0.0,
    "p_after_divide": 0.0,
    "p_after_projection": 0.0,
    "p0": 0.0,
    "J": 0.0,
    "kappa": 0.0,
    "sigma_xx": 0.0,
    "sigma_zz": 0.0
  },
  "classification_difference_counts": {
    "initial_FS": 0,
    "after_retire_FS": 0,
    "positive_projection": 0
  },
  "actual_GPU_completion": {
    "stage": "upl_wall_retire_gpu_r1",
    "passed": true,
    "retired_native_begin": 1800,
    "retired_native_count": 260,
    "active_native_count": 6800,
    "remaining_fixed": 1800,
    "remaining_NpbOk": 309,
    "preserved_soil_IDs": 5000,
    "GPU_kappa_dk_transport_checks": 5000,
    "remaining_wall_rows": 1800,
    "active_remaining_wall_closures": 306,
    "positive_projection_rows": 149,
    "new_surface_positive_projection_rows": 49,
    "actual_boundary_cell_candidates": 6366,
    "retired_boundary_candidates": 0,
    "boundary_Id_Code_download_mark_Code_upload": true,
    "new_production_CUDA_kernel_or_interface": false,
    "original_case_ID_registry_unchanged": true,
    "typed_member_bits_not_State_padding_compared": true,
    "geometry_compacted_not_restored": true,
    "borrowed_derivative_NULL_before_free_Pos": true,
    "prescribed_Ace_not_actual_force": true,
    "physical_steps": 0,
    "production_release_event_tested": false,
    "prestress_or_restart_claimed": false,
    "new_numerical_tolerance": false,
    "physical_acceptance": false
  }
}
