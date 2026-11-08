// Test-only C08 genuine-stage telemetry. No code/API exists without this macro.
#pragma once
#ifdef C08_STAGE_TRACE
#pragma message("C08_STAGE_TRACE enabled")
struct C08StageTraceContext{
  unsigned enabled,phase,nstep,interstep;
  double time,dt_state,dt_operator;
  const unsigned *idp,*fstype;
  const float *rate;
};
struct C08StageTraceRecord{
  C08StageTraceContext context;
  unsigned native_id,hits,fstype,raw_fs,drainfs,closedfs,freeseepage,projected;
  double p_before,p_after,rate_before,rate_after;
  double J,n,theta,ki,lp,da,lap,chain,value;
  double pos[3],fsnormal[3],C[9],Ace[3],lx[3],gp[3],gpcorr[3],gJ[3];
};
enum{C08_TRACE_RHS=1,C08_TRACE_UPDATE=2,C08_TRACE_PONDING=3};
namespace cusph{
  bool C08StageTraceStart(const C08StageTraceContext& context);
  bool C08StageTraceRead(C08StageTraceRecord records[3]);
}
#endif
