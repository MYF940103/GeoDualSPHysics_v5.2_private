// Test-only C08 genuine-stage telemetry. No code/API exists without this macro.
#pragma once
#ifdef C08_STAGE_TRACE
#pragma message("C08_STAGE_TRACE enabled")
struct C08StageTraceContext{
  unsigned enabled,phase,nstep,interstep;
  double time,dt_state,dt_operator;
  const unsigned *idp,*fstype;
  const float *rate;
#ifdef C08_CAUSAL_TRACE
  const tsymatrix3f *rsigma;
  const float *porepress,*poreold;
  const double *jbase,*jstage,*theta;
  unsigned emit;
#endif
};
#ifdef C08_CAUSAL_TRACE
#pragma message("C08_CAUSAL_TRACE enabled")
struct C08CausalTotals{
  unsigned native_id,material_pre,material_cor,plane_pre,plane_cor,errors,base_trace_changes;
  unsigned status_pre[8],status_cor[8],hit_pre[2],hit_cor[2],velocity_clamp_pre[2],velocity_clamp_cor[2];
  double cor_dt_rsigma_trace,cor_trace_drop,cor_abs_trace_drop,cor_trace_drop_local_budget,cor_dt,last_time,last_dt;
  double initial_I,last_returned_I,modulus_K,cor_trial_update_local_budget,cor_abs_dt_rsigma_trace,cor_trial_update_residual;
  double cor_log_j_ratio,cor_dt_theta,delta_v_pre[3],delta_v_cor[3];
  double pending_jbase,pending_jhalf,pending_theta,pending_dt;
  unsigned pending_step,pending_valid;
};
#endif
struct C08StageTraceRecord{
  C08StageTraceContext context;
  unsigned native_id,hits,fstype,raw_fs,drainfs,closedfs,freeseepage,projected;
  double p_before,p_after,rate_before,rate_after;
  double J,n,theta,ki,lp,da,lap,chain,value;
  double pos[3],fsnormal[3],C[9],Ace[3],lx[3],gp[3],gpcorr[3],gJ[3];
#ifdef C08_CAUSAL_TRACE
  unsigned material_status,material_commit,plane_hit[2],plane_velocity_clamp[2];
  double base_I,trial_I,returned_I,kappa_old,kappa_candidate,kappa_saved,trace_drop_budget,modulus_K,trial_update_budget,trial_update_residual;
  double sigma_rate[6],sigma_rate_trace,jbase,jhalf,jnew,stage_theta,pressure_base;
  double move_before[3],move_after[3],velocity_before[3],velocity_after[3];
  C08CausalTotals cumulative;
#endif
};
enum{C08_TRACE_RHS=1,C08_TRACE_UPDATE=2,C08_TRACE_PONDING=3};
#ifdef C08_CAUSAL_TRACE
enum{C08_TRACE_MATERIAL=4,C08_TRACE_PLANE=5};
namespace cusphs{
  bool C08CausalTraceStart(const C08StageTraceContext& context);
  bool C08CausalTraceRead(C08StageTraceRecord records[3]);
  bool C08CausalTraceTotals(C08CausalTotals totals[3]);
}
#endif
namespace cusph{
  bool C08StageTraceStart(const C08StageTraceContext& context);
  bool C08StageTraceRead(C08StageTraceRecord records[3]);
}
#endif
