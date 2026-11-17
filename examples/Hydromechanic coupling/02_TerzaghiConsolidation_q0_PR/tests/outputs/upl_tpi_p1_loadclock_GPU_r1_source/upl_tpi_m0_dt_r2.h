// Private, host-only Eq40 necessary timestep policy; no public XML or ABI.
#pragma once
#ifdef __CUDACC__
#error The M0 timestep policy is host-only and must not change a CUDA closure.
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

namespace upl_tpi_m0_dt_r2 {
inline void Need(bool q,const char* m){if(!q)throw std::runtime_error(m);}
inline bool Bits(double a,double b){return !std::memcmp(&a,&b,sizeof(a));}
inline bool Enabled(bool pressureBC){
  if(!pressureBC)return false; // A does not inspect or initialise this policy.
  static const bool yes=[](){const char* p=std::getenv("UPL_TPI_M0_DT_R1");
    if(!p||!*p)return false;
    Need(!std::strcmp(p,"EQ40_RH1"),"Private M0 dt policy must be absent or EQ40_RH1");return true;}();
  return yes;
}
inline bool AllowedDt(double dt,double event){
  return std::isfinite(dt)&&dt>0.&&event==.0100002288818359375
    &&(Bits(dt,event/1000.)||Bits(dt,event/500.));
}
struct Extrema {
  unsigned long long pre=0,cor=0,endpoint=0;
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
  State& s=Get();Need(owner&&!s.owner&&time==0.&&step==0&&AllowedDt(dt,event),"M0 dt requires a fresh admitted fixed grid");
  Need(backend&&scheme&&(!std::strcmp(backend,"CPU")||!std::strcmp(backend,"GPU")),"M0 dt backend absent");
  s.owner=owner;s.directory=directory;s.backend=backend;s.scheme=scheme;s.dt=dt;
  const std::string policy=directory+"UplTpiM0DtR1.policy.json",csv=directory+"UplTpiM0DtR1.csv";
  Need(!std::ifstream(policy).good()&&!std::ifstream(csv).good(),"M0 dt sidecar already exists");
  s.csv.open(csv);Need(bool(s.csv),"M0 dt interval output failed");s.csv<<std::setprecision(17);
  s.csv<<"part,actual_save_time_s,saved_step,completed_updates,dt_s,interval_pre,interval_cor,interval_endpoint,total_pre,total_cor,total_endpoint,interval_empty,min_force_CFL_s,min_skeleton_wave_AV_CFL_s,min_Rh_hydro_s,min_legacy_Kw_wave_CFL_reference_s,min_HG_limit_reference_s,min_selected_bound_s,max_dt_minus_bound_s\n";
  std::ofstream p(policy);p<<std::setprecision(17)<<"{\"stage\":\"upl_tpi_m0_dt_r2\",\"backend\":\""<<backend
    <<"\",\"pressure_scheme\":\""<<scheme<<"\",\"dt_policy\":\"M0_Eq40_Rh1\",\"R_h\":1,\"fixed_dt_s\":"<<dt
    <<",\"drainage_event_s\":"<<event<<",\"force_and_AV_retained\":true,\"hydro_is_true_Kw_explicit_reference\":true,\"legacy_Kw_wave_is_reference_only\":true,\"HG_independent_guard_retained\":true,\"HG_limit_reference_available\":false,\"signed_dterror_is_method_specific\":true,\"initial_dterror_not_rewritten\":true,\"sufficient_stability_claimed\":false,\"physical_acceptance\":false}\n";
  p.flush();Need(bool(p),"M0 dt policy write failed");
}
inline void Add(Extrema& x,unsigned phase,double force,double wave,double hydro,double oldwave,double hg,double bound,double error){
  if(phase==0)x.pre++;else if(phase==1)x.cor++;else x.endpoint++;
  x.force=(std::min)(x.force,force);x.wave=(std::min)(x.wave,wave);x.hydro=(std::min)(x.hydro,hydro);
  x.legacyWave=(std::min)(x.legacyWave,oldwave);x.hg=(std::min)(x.hg,hg);
  x.bound=(std::min)(x.bound,bound);x.error=(std::max)(x.error,error);
}
// Eq40 necessary bound only: R_h is fixed to one in this candidate.
// The old true-Kw wave is diagnostic; HG retains its independent original gate.
inline double Record(const void* owner,unsigned phase,double time,unsigned long long step,double dt,
  double forceCFL,double skeletonWaveAVCFL,double hydro,double legacyWaveCFL,double hgLimit){
  State& s=Get();Need(s.owner==owner&&phase<=2&&phase==s.phase&&step==s.completed&&Bits(dt,s.dt),"M0 dt phase/owner/step changed");
  if(phase==0){Need(Bits(time,s.lastEnd),"M0 dt predictor clock changed");s.sourceTime=time;}
  else Need(Bits(time,s.sourceTime),"M0 dt stage source clock changed");
  const double values[]={forceCFL,skeletonWaveAVCFL,hydro,legacyWaveCFL,hgLimit};
  for(double x:values)Need(std::isfinite(x)&&x>0.,"M0 dt necessary scale must be finite and positive");
  const double bound=(std::min)((std::min)(forceCFL,skeletonWaveAVCFL),hydro),error=dt-bound;
  Need(std::isfinite(bound)&&bound>0.&&std::isfinite(error),"M0 dt combined necessary bound invalid");
  Add(s.interval,phase,forceCFL,skeletonWaveAVCFL,hydro,legacyWaveCFL,hgLimit,bound,error);
  Add(s.total,phase,forceCFL,skeletonWaveAVCFL,hydro,legacyWaveCFL,hgLimit,bound,error);
  s.phase=(phase+1)%3;if(phase==2){s.completed++;s.lastEnd=time+dt;}
  return bound; // Original DtVariable still rejects an already locked excess step.
}
inline void Saved(const void* owner,unsigned part,double time,unsigned long long savedstep){
  State& s=Get();Need(s.owner==owner&&s.phase==0&&Bits(time,s.lastEnd)
    &&(s.completed?savedstep+1==s.completed:savedstep==0),"M0 dt genuine saved clock changed");
  Need(s.interval.pre==s.interval.cor&&s.interval.cor==s.interval.endpoint,"M0 dt saved interval has missing stages");
  const auto& x=s.interval;const bool empty=x.pre==0;
  s.csv<<part<<','<<time<<','<<savedstep<<','<<s.completed<<','<<s.dt<<','<<x.pre<<','<<x.cor<<','<<x.endpoint
    <<','<<s.total.pre<<','<<s.total.cor<<','<<s.total.endpoint<<','<<unsigned(empty)<<','<<x.force<<','<<x.wave<<','<<x.hydro
    <<','<<x.legacyWave<<','<<x.hg<<','<<x.bound<<','<<x.error<<'\n';
  s.csv.flush();Need(bool(s.csv),"M0 dt saved interval write failed");s.interval=Extrema{};s.saves++;s.lastSaved=time;
}
inline void Finish(const void* owner,unsigned long long completed,double time){
  State& s=Get();Need(s.owner==owner&&s.phase==0&&s.completed==completed&&Bits(time,s.lastEnd)&&Bits(time,s.lastSaved)
    &&s.total.pre==completed&&s.total.cor==completed&&s.total.endpoint==completed,"M0 dt complete stage/save counts differ");
  const std::string path=s.directory+"UplTpiM0DtR1.summary.json";Need(!std::ifstream(path).good(),"M0 dt summary exists");
  std::ofstream f(path);f<<std::setprecision(17)<<"{\"stage\":\"upl_tpi_m0_dt_r2\",\"completed\":true,\"dt_policy\":\"M0_Eq40_Rh1\",\"R_h\":1,\"updates\":"<<completed
    <<",\"pre\":"<<s.total.pre<<",\"cor\":"<<s.total.cor<<",\"endpoint\":"<<s.total.endpoint<<",\"saved_intervals_including_initial\":"<<s.saves
    <<",\"actual_end_s\":"<<time<<",\"fixed_dt_s\":"<<s.dt<<",\"min_selected_bound_s\":"<<s.total.bound<<",\"max_dt_minus_bound_s\":"<<s.total.error
    <<",\"min_force_CFL_s\":"<<s.total.force<<",\"min_skeleton_wave_AV_CFL_s\":"<<s.total.wave<<",\"min_Rh_hydro_s\":"<<s.total.hydro
    <<",\"min_legacy_Kw_wave_CFL_reference_s\":"<<s.total.legacyWave<<",\"HG_limit_reference_available\":false,\"min_HG_limit_reference_s\":"<<s.total.hg
    <<",\"signed_dterror_is_method_specific\":true,\"sufficient_stability_claimed\":false,\"physical_acceptance\":false}\n";
  f.flush();Need(bool(f),"M0 dt summary write failed");
}
} // namespace upl_tpi_m0_dt_r2
