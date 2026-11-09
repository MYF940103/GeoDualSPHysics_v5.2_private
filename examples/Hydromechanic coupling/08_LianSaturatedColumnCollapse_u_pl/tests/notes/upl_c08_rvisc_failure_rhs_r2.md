# RHS检查旧记录格式兼容修复

r1 runner在启动组件之前因旧baseline90记录不存在`solver_completed`字段而退出。原失败check保留，实际call=null、没有组件输出目录，未执行force/Darcy或物理积分。

r2仅修runner：实际baseline已保存`passed=true, actual_steps=4360000, saved_frames=90`以及Popen/Win32/solver退出0、ownership_errors空，原normal native收据也通过。用这些真实字段替代不存在的字段，不写回旧记录、不发明成功标记。其余安全、原必要dt、原控制逐位门均不改。

沿用已通过r1 helper构建及相同三态/六call输出目录；新调用与check标签为upl_c08_rvisc_failure_rhs_r2。原r1检查失败不覆盖，不重编对象。Root审阅后仅执行r2一次；仍无物理轨迹、native decoder、PRE求解或下一窗口。
