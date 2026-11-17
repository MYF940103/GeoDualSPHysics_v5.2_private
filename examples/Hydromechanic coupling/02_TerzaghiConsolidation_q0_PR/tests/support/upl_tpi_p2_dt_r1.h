// Private, host-only P2 Eq40 necessary timestep audit; no public XML or ABI.
#pragma once
#ifdef __CUDACC__
#error The P2 timestep policy is host-only and must not change a CUDA closure.
#endif
#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <string>

// Intentional source substitution for the original M0 dt header, never co-include it.
namespace upl_tpi_m0_dt_r2 {
inline void Need(bool q,const char* m){if(!q)throw std::runtime_error(m);}
inline bool Bits(double a,double b){return !std::memcmp(&a,&b,sizeof(a));}
inline bool Enabled(bool pressureBC){
  if(!pressureBC)return false; // A does not inspect or initialise either private policy.
  static const bool yes=[](){const char* rows=std::getenv("UPL_TPI_P2_ROWS_R1");
    if(!rows||!*rows)return false;
    Need(!std::strcmp(rows,"2"),"Private P2 rows must be absent or exactly 2");
    const char* p=std::getenv("UPL_TPI_M0_DT_R1");
    Need(p&&!std::strcmp(p,"EQ40_RH1"),"Private P2 dt requires EQ40_RH1");return true;}();
  return yes;
}
inline bool AllowedDt(double dt,double event){
  return std::isfinite(dt)&&dt>0.&&event==.0100002288818359375&&Bits(dt,event/1000.);
}
struct Extrema {
  unsigned long long pre=0,cor=0,endpoint1=0,endpoint2=0;
  double force=DBL_MAX,wave=DBL_MAX,hydro=DBL_MAX,legacyWave=DBL_MAX,hg=DBL_MAX,bound=DBL_MAX,error=-DBL_MAX;
};
struct State {
  const void* owner=nullptr;std::string directory,backend,scheme;
  double dt=0,sourceTime=0,lastEnd=0,lastSaved=0;unsigned phase=0;
  unsigned long long completed=0,saves=0;Extrema interval,total;std::ofstream csv;
};
inline State& Get(){static State s;return s;}
inline void Init(const void* owner,const std::string& directory,const char* backend,const char* scheme,
  double time,unsigned long long step,double dt,double event){
  // Check B before reading private environment; the default A path never calls Init.
  Need(scheme&&!std::strcmp(scheme,"B"),"Private P2 dt admits only scheme B");
  Need(Enabled(true),"Private P2 dt requires explicit rows=2");
  State& s=Get();Need(owner&&!s.owner&&time==0.&&step==0&&AllowedDt(dt,event),"P2 dt requires a fresh admitted fixed grid");
  Need(backend&&(!std::strcmp(backend,"CPU")||!std::strcmp(backend,"GPU")),"P2 dt backend absent");
  s.owner=owner;s.directory=directory;s.backend=backend;s.scheme=scheme;s.dt=dt;
  const std::string policy=directory+"UplTpiP2DtR1.policy.json",csv=directory+"UplTpiP2DtR1.csv";
  Need(!std::ifstream(policy).good()&&!std::ifstream(csv).good(),"P2 dt sidecar already exists");
  s.csv.open(csv);Need(bool(s.csv),"P2 dt interval output failed");s.csv<<std::setprecision(17);
  s.csv<<"part,actual_save_time_s,saved_step,completed_updates,dt_s,interval_pre,interval_cor,interval_endpoint1,interval_endpoint2,total_pre,total_cor,total_endpoint1,total_endpoint2,interval_empty,min_force_CFL_s,min_skeleton_wave_AV_CFL_s,min_Rh_hydro_s,min_legacy_Kw_wave_CFL_reference_s,min_HG_limit_reference_s,min_selected_bound_s,max_dt_minus_bound_s\n";
  std::ofstream p(policy);p<<std::setprecision(17)<<"{\"stage\":\"upl_tpi_p2_dt_r1\",\"backend\":\""<<backend
    <<"\",\"pressure_scheme\":\""<<scheme<<"\",\"endpoint_defect_rounds\":2,\"force_phases_per_update\":4,\"dt_policy\":\"M0_Eq40_Rh1\",\"R_h\":1,\"fixed_dt_s\":"<<dt
    <<",\"drainage_event_s\":"<<event<<",\"source_clock_policy\":\"original_TimeStep_all_four_phases\",\"force_and_AV_retained\":true,\"hydro_is_true_Kw_explicit_reference\":true,\"legacy_Kw_wave_is_reference_only\":true,\"HG_independent_guard_retained\":true,\"HG_limit_reference_available\":false,\"signed_dterror_is_method_specific\":true,\"initial_dterror_not_rewritten\":true,\"sufficient_stability_claimed\":false,\"physical_acceptance\":false}\n";
  p.flush();Need(bool(p),"P2 dt policy write failed");
}
inline void Add(Extrema& x,unsigned phase,double force,double wave,double hydro,double oldwave,double hg,double bound,double error){
  Need(phase<=3,"P2 dt phase outside four-phase audit");
  if(phase==0)x.pre++;else if(phase==1)x.cor++;else if(phase==2)x.endpoint1++;else x.endpoint2++;
  x.force=(std::min)(x.force,force);x.wave=(std::min)(x.wave,wave);x.hydro=(std::min)(x.hydro,hydro);
  x.legacyWave=(std::min)(x.legacyWave,oldwave);x.hg=(std::min)(x.hg,hg);
  x.bound=(std::min)(x.bound,bound);x.error=(std::max)(x.error,error);
}
// Query only: callers pass the backend pressure helper's independent actual round.
inline unsigned EndpointPhase(){
  const State& s=Get();Need(s.owner&&(s.phase==2||s.phase==3),"P2 dt is not at an expected endpoint phase");return s.phase;
}
// Eq40 necessary bound only: R_h is fixed to one in this candidate.
// The old true-Kw wave is diagnostic; HG retains its independent original gate.
inline double Record(const void* owner,unsigned phase,double time,unsigned long long step,double dt,
  double forceCFL,double skeletonWaveAVCFL,double hydro,double legacyWaveCFL,double hgLimit){
  State& s=Get();Need(s.owner==owner&&phase<=3&&phase==s.phase&&step==s.completed&&Bits(dt,s.dt),"P2 dt phase/owner/step changed");
  if(phase==0){Need(Bits(time,s.lastEnd),"P2 dt predictor clock changed");s.sourceTime=time;}
  else Need(Bits(time,s.sourceTime),"P2 dt stage source clock changed");
  const double values[]={forceCFL,skeletonWaveAVCFL,hydro,legacyWaveCFL,hgLimit};
  for(double x:values)Need(std::isfinite(x)&&x>0.,"P2 dt necessary scale must be finite and positive");
  const double bound=(std::min)((std::min)(forceCFL,skeletonWaveAVCFL),hydro),error=dt-bound;
  Need(std::isfinite(bound)&&bound>0.&&std::isfinite(error),"P2 dt combined necessary bound invalid");
  Add(s.interval,phase,forceCFL,skeletonWaveAVCFL,hydro,legacyWaveCFL,hgLimit,bound,error);
  Add(s.total,phase,forceCFL,skeletonWaveAVCFL,hydro,legacyWaveCFL,hgLimit,bound,error);
  s.phase=(phase+1)%4;if(phase==3){s.completed++;s.lastEnd=time+dt;}
  return bound; // Original DtVariable still rejects an already locked excess step.
}
inline void Saved(const void* owner,unsigned part,double time,unsigned long long savedstep){
  State& s=Get();Need(s.owner==owner&&s.phase==0&&Bits(time,s.lastEnd)
    &&(s.completed?savedstep+1==s.completed:savedstep==0),"P2 dt genuine saved clock changed");
  Need(s.interval.pre==s.interval.cor&&s.interval.cor==s.interval.endpoint1&&s.interval.endpoint1==s.interval.endpoint2,"P2 dt saved interval has missing stages");
  const auto& x=s.interval;const bool empty=x.pre==0;
  s.csv<<part<<','<<time<<','<<savedstep<<','<<s.completed<<','<<s.dt<<','<<x.pre<<','<<x.cor<<','<<x.endpoint1<<','<<x.endpoint2
    <<','<<s.total.pre<<','<<s.total.cor<<','<<s.total.endpoint1<<','<<s.total.endpoint2<<','<<unsigned(empty)<<','<<x.force<<','<<x.wave<<','<<x.hydro
    <<','<<x.legacyWave<<','<<x.hg<<','<<x.bound<<','<<x.error<<'\n';
  s.csv.flush();Need(bool(s.csv),"P2 dt saved interval write failed");s.interval=Extrema{};s.saves++;s.lastSaved=time;
}
inline void Finish(const void* owner,unsigned long long completed,double time){
  State& s=Get();Need(s.owner==owner&&s.phase==0&&s.completed==completed&&Bits(time,s.lastEnd)&&Bits(time,s.lastSaved)
    &&s.total.pre==completed&&s.total.cor==completed&&s.total.endpoint1==completed&&s.total.endpoint2==completed,"P2 dt complete stage/save counts differ");
  const std::string path=s.directory+"UplTpiP2DtR1.summary.json";Need(!std::ifstream(path).good(),"P2 dt summary exists");
  std::ofstream f(path);f<<std::setprecision(17)<<"{\"stage\":\"upl_tpi_p2_dt_r1\",\"completed\":true,\"endpoint_defect_rounds\":2,\"force_phases_per_update\":4,\"dt_policy\":\"M0_Eq40_Rh1\",\"R_h\":1,\"updates\":"<<completed
    <<",\"pre\":"<<s.total.pre<<",\"cor\":"<<s.total.cor<<",\"endpoint1\":"<<s.total.endpoint1<<",\"endpoint2\":"<<s.total.endpoint2<<",\"saved_intervals_including_initial\":"<<s.saves
    <<",\"actual_end_s\":"<<time<<",\"fixed_dt_s\":"<<s.dt<<",\"min_selected_bound_s\":"<<s.total.bound<<",\"max_dt_minus_bound_s\":"<<s.total.error
    <<",\"min_force_CFL_s\":"<<s.total.force<<",\"min_skeleton_wave_AV_CFL_s\":"<<s.total.wave<<",\"min_Rh_hydro_s\":"<<s.total.hydro
    <<",\"min_legacy_Kw_wave_CFL_reference_s\":"<<s.total.legacyWave<<",\"HG_limit_reference_available\":false,\"min_HG_limit_reference_s\":"<<s.total.hg
    <<",\"source_clock_policy\":\"original_TimeStep_all_four_phases\",\"signed_dterror_is_method_specific\":true,\"initial_dterror_not_rewritten\":true,\"sufficient_stability_claimed\":false,\"physical_acceptance\":false}\n";
  f.flush();Need(bool(f),"P2 dt summary write failed");
}
} // namespace upl_tpi_m0_dt_r2
