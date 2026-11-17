// Private P1 host-only staged load clock. Pressure, BC and global clocks are untouched.
#pragma once
#ifdef __CUDACC__
#error The load-clock observer must not enter a CUDA closure.
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
namespace upl_tpi_p1_loadclock_r1 {
inline void Need(bool q,const char* m){if(!q)throw std::runtime_error(m);}
template<class T> inline bool Bits(const T& a,const T& b){return !std::memcmp(&a,&b,sizeof(T));}
inline bool Enabled(bool pressureEnabled){
 if(!pressureEnabled)return false; // A does not inspect this selector/context.
 static const bool enabled=[](){const char* p=std::getenv("UPL_TPI_P1_LOADCLOCK_R1");
  if(!p||!*p)return false;Need(!std::strcmp(p,"STAGED"),"Private P1 loadclock must be absent or exact STAGED");return true;}();return enabled;
}
enum Phase{OldFull=0,MechanicalHalf=1,PressureEndpoint=2};
enum Site{DirectTop=0,RawBand=1};
struct Counts{
 unsigned long long force[3]={0,0,0},eval[3][2]={{0,0},{0,0},{0,0}};
 double minTime[3]={DBL_MAX,DBL_MAX,DBL_MAX},maxTime[3]={-DBL_MAX,-DBL_MAX,-DBL_MAX};
 double minQ[3]={DBL_MAX,DBL_MAX,DBL_MAX},maxQ[3]={-DBL_MAX,-DBL_MAX,-DBL_MAX};
};
struct State{
 const void* owner=nullptr;bool ready=false,active=false,finished=false;
 unsigned expected=0,phase=0;unsigned long long completed=0,saves=0,coldEvaluations=0;
 unsigned long long currentSites[2]={0,0};double dt=0,sourceTime=0,lastEnd=0,lastSaved=0,evalTime=0;
 double lastTimes[3]={0,0,0},lastQ[3]={0,0,0};Counts interval,total;
 std::string directory,backend;std::ofstream csv;
};
inline State& Get(){static State s;return s;}
inline double Ramp(double time,double q0,double ramp){return ramp>0&&time<ramp?q0*(std::max)(0.,time)/ramp:q0;}
inline void Init(const void* owner,const std::string& directory,const char* backend,const char* scheme,
 double time,unsigned long long step,double dt,double event){
 State& s=Get();Need(owner&&!s.owner&&time==0.&&step==0&&event==.0100002288818359375&&Bits(dt,event/1000.),"P1 loadclock requires fresh admitted 10us owner");
 Need(backend&&(!std::strcmp(backend,"CPU")||!std::strcmp(backend,"GPU"))&&scheme&&!std::strcmp(scheme,"B"),"P1 loadclock supports only admitted B CPU/GPU");
 s.owner=owner;s.directory=directory;s.backend=backend;s.dt=dt;
 const std::string policy=directory+"UplTpiP1LoadClockR1.policy.json",csv=directory+"UplTpiP1LoadClockR1.csv";
 Need(!std::ifstream(policy).good()&&!std::ifstream(csv).good(),"P1 loadclock sidecar already exists");s.csv.open(csv);Need(bool(s.csv),"P1 loadclock CSV open failed");s.csv<<std::setprecision(17);
 s.csv<<"part,actual_save_time_s,saved_step,completed_updates,dt_s,last_source_time_s,last_old_eval_time_s,last_half_eval_time_s,last_endpoint_eval_time_s,last_old_q_double_Pa,last_half_q_double_Pa,last_endpoint_q_double_Pa,interval_old_forces,interval_half_forces,interval_endpoint_forces,total_old_forces,total_half_forces,total_endpoint_forces,interval_old_direct_evals,interval_old_raw_evals,interval_half_direct_evals,interval_half_raw_evals,interval_endpoint_direct_evals,interval_endpoint_raw_evals,total_old_direct_evals,total_old_raw_evals,total_half_direct_evals,total_half_raw_evals,total_endpoint_direct_evals,total_endpoint_raw_evals,interval_empty,min_old_eval_time_s,max_old_eval_time_s,min_half_eval_time_s,max_half_eval_time_s,min_endpoint_eval_time_s,max_endpoint_eval_time_s,min_old_q_double_Pa,max_old_q_double_Pa,min_half_q_double_Pa,max_half_q_double_Pa,min_endpoint_q_double_Pa,max_endpoint_q_double_Pa,cold_nonforce_eval_calls\n";
 std::ofstream f(policy);f<<std::setprecision(17)<<"{\"stage\":\"upl_tpi_p1_loadclock_r1\",\"backend\":\""<<backend
  <<"\",\"scheme\":\"B\",\"old_half_endpoint_load_fractions\":[0,0.5,1],\"fixed_dt_s\":"<<dt<<",\"ramp_and_drainage_time_s\":"<<event
  <<",\"global_TimeStep_or_Nstep_changed\":false,\"Dirichlet_source_policy_changed\":false,\"original_P1_pressure_HG_J_order_retained\":true,\"original_pressure_schema_retained\":true,\"paired_load_sites_record_actual_calls\":true,\"sufficient_stability_or_physical_acceptance\":false}\n";
 f.flush();Need(bool(f),"P1 loadclock policy write failed");s.ready=true;
}
inline void Enter(const void* owner,unsigned phase,double time,unsigned long long step,double dt){
 State& s=Get();Need(s.ready&&!s.finished&&s.owner==owner&&!s.active&&phase<=2&&phase==s.expected&&step==s.completed&&Bits(dt,s.dt),"P1 loadclock force owner/phase/step invalid");
 if(phase==0){Need(Bits(time,s.lastEnd),"P1 loadclock actual scalar source clock changed");s.sourceTime=time;}
 else Need(Bits(time,s.sourceTime),"P1 loadclock half/endpoint mutated source clock");
 s.phase=phase;s.active=true;s.currentSites[0]=s.currentSites[1]=0;
 s.evalTime=(phase==0?time:phase==1?time+.5*dt:time+dt);
 Need(std::isfinite(s.evalTime)&&s.evalTime>=time,"P1 loadclock stage time invalid");
}
inline double Evaluate(const void* owner,double actualSourceTime,double q0,double ramp,unsigned site){
 State& s=Get();Need(site<=1&&std::isfinite(q0)&&q0==10000.&&ramp==.0100002288818359375,"P1 loadclock original load parameters changed");
 if(!s.ready||!s.active){
  Need(actualSourceTime==0.&&!s.finished&&(!s.owner||s.owner==owner)&&s.completed==0,"P1 loadclock nonforce evaluation outside initial t0");s.coldEvaluations++;return Ramp(actualSourceTime,q0,ramp);
 }
 Need(s.owner==owner&&Bits(actualSourceTime,s.sourceTime),"P1 loadclock force site owner/source clock changed");
 const double q=Ramp(s.evalTime,q0,ramp);Need(std::isfinite(q)&&q>=0.&&q<=q0,"P1 loadclock stage ramp invalid");
 if(s.currentSites[0]||s.currentSites[1])Need(Bits(s.lastQ[s.phase],q),"P1 paired sites evaluated different q");
 s.currentSites[site]++;s.interval.eval[s.phase][site]++;s.total.eval[s.phase][site]++;
 s.lastTimes[s.phase]=s.evalTime;s.lastQ[s.phase]=q;
 s.interval.minTime[s.phase]=(std::min)(s.interval.minTime[s.phase],s.evalTime);s.interval.maxTime[s.phase]=(std::max)(s.interval.maxTime[s.phase],s.evalTime);
 s.interval.minQ[s.phase]=(std::min)(s.interval.minQ[s.phase],q);s.interval.maxQ[s.phase]=(std::max)(s.interval.maxQ[s.phase],q);
 return q;
}
inline void Leave(const void* owner,unsigned phase,double time,unsigned long long step,double dt){
 State& s=Get();Need(s.ready&&s.owner==owner&&s.active&&phase==s.phase&&phase==s.expected&&step==s.completed&&Bits(time,s.sourceTime)&&Bits(dt,s.dt),"P1 loadclock leave lifecycle invalid");
 Need(s.currentSites[DirectTop]==1&&s.currentSites[RawBand]==1,"P1 loadclock missing or duplicated direct/paired raw load site");
 s.interval.force[phase]++;s.total.force[phase]++;s.active=false;s.expected=(phase+1)%3;
 if(phase==2){s.completed++;s.lastEnd=time+dt;}
}
inline void Saved(const void* owner,unsigned part,double time,unsigned long long savedstep){
 State& s=Get();Need(s.ready&&s.owner==owner&&!s.active&&s.expected==0&&Bits(time,s.lastEnd)&&(s.completed?savedstep+1==s.completed:savedstep==0),"P1 loadclock saved clock/phase invalid");
 const Counts& x=s.interval;Need(x.force[0]==x.force[1]&&x.force[1]==x.force[2],"P1 loadclock incomplete saved interval");
 s.csv<<part<<','<<time<<','<<savedstep<<','<<s.completed<<','<<s.dt<<','<<s.sourceTime;
 for(double v:s.lastTimes)s.csv<<','<<v;for(double q:s.lastQ)s.csv<<','<<q;
 for(auto n:x.force)s.csv<<','<<n;for(auto n:s.total.force)s.csv<<','<<n;
 for(unsigned i=0;i<3;i++)for(unsigned k=0;k<2;k++)s.csv<<','<<x.eval[i][k];
 for(unsigned i=0;i<3;i++)for(unsigned k=0;k<2;k++)s.csv<<','<<s.total.eval[i][k];
 s.csv<<','<<unsigned(x.force[0]==0);for(unsigned i=0;i<3;i++)s.csv<<','<<x.minTime[i]<<','<<x.maxTime[i];for(unsigned i=0;i<3;i++)s.csv<<','<<x.minQ[i]<<','<<x.maxQ[i];
 s.csv<<','<<s.coldEvaluations<<'\n';s.csv.flush();Need(bool(s.csv),"P1 loadclock saved output failed");s.interval=Counts{};s.saves++;s.lastSaved=time;
}
inline void Finish(const void* owner,unsigned long long completed,double time){
 State& s=Get();Need(s.ready&&s.owner==owner&&!s.active&&s.expected==0&&s.completed==completed&&Bits(time,s.lastEnd)&&Bits(time,s.lastSaved),"P1 loadclock final clock differs");
 for(unsigned i=0;i<3;i++)Need(s.total.force[i]==completed&&s.total.eval[i][0]==completed&&s.total.eval[i][1]==completed,"P1 loadclock final stage/site counts differ");
 const std::string path=s.directory+"UplTpiP1LoadClockR1.summary.json";Need(!std::ifstream(path).good(),"P1 loadclock summary exists");std::ofstream f(path);
 f<<std::setprecision(17)<<"{\"stage\":\"upl_tpi_p1_loadclock_r1\",\"completed\":true,\"updates\":"<<completed<<",\"actual_end_s\":"<<time<<",\"old_half_endpoint_force_calls\":["<<s.total.force[0]<<','<<s.total.force[1]<<','<<s.total.force[2]<<"],\"site_evaluation_counts\":[";
 for(unsigned i=0;i<3;i++)for(unsigned k=0;k<2;k++){if(i||k)f<<',';f<<s.total.eval[i][k];}
 f<<"],\"cold_nonforce_eval_calls\":"<<s.coldEvaluations<<",\"global_clock_changed\":false,\"pressure_schema_changed\":false,\"physical_acceptance\":false}\n";
 f.flush();Need(bool(f),"P1 loadclock summary write failed");s.finished=true;
}
} // namespace upl_tpi_p1_loadclock_r1
