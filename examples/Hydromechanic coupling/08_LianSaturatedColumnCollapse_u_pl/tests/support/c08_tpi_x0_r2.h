// Private CPU-only X0 prototype. No public class, XML, ABI or restart extension.
#ifndef C08_TPI_X0_R2_H
#define C08_TPI_X0_R2_H
#include "DualSphDef.h"
#include <algorithm>
#include <cfloat>
#include <climits>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace c08x0 {
constexpr unsigned Fixed=40,Soil=1000,Total=1040;
constexpr double Dt=5e-6,Alpha=.5;
inline void Need(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
inline bool Bits(double a,double b){return std::memcmp(&a,&b,sizeof(a))==0;}
inline bool Bits(float a,float b){return std::memcmp(&a,&b,sizeof(a))==0;}
inline bool Requested(){
  // Absent is the only OFF spelling. No State allocation or file open on OFF.
  static const bool enabled=[](){const char* p=std::getenv("C08_TPI_X0");
    if(!p || !*p)return false;
    Need(std::strcmp(p,"1")==0,"C08_TPI_X0 must be absent or exactly 1");return true;}();
  return enabled;
}
struct State {
  const void* owner=nullptr;
  bool ready=false,pending=false,temporary=false,endpoint=false;
  unsigned sourceStep=0,commits=0,preCalls=0,corrCalls=0,jCalls=0,endpointCalls=0,rows=0,saves=0;
  unsigned rowError=0,rowErrorId=UINT_MAX;
  double sourceTime=0,dt=0,lastEnd=0;
  std::vector<unsigned> slots,seen,drained,commitDrained;
  std::vector<float> previous,previousUsed,pn,half,guess,raw,finalP;
  std::vector<double> S,R,thetaH,thetaEndpoint,Jn,Jhalf,Jfull;
  std::ofstream* csv=nullptr;
  std::string directory;
  ~State(){delete csv;}
};
extern State state; // Defined only by the JSphCpu.cpp overlay.

inline void Map(unsigned np,const unsigned* id,const typecode* code){
  State& s=state;std::fill(s.slots.begin(),s.slots.end(),UINT_MAX);unsigned count=0;
  for(unsigned p=0;p<np;p++){
    Need(id[p]<Total,"X0 ID outside original 1040-ID contract");
    if(!CODE_IsNormal(code[p]))continue;
    const unsigned k=id[p];Need(s.slots[k]==UINT_MAX,"X0 duplicate normal native ID");
    Need((k<Fixed && CODE_IsFixed(code[p])) || (k>=Fixed && CODE_IsFluid(code[p])),"X0 original native role changed");
    s.slots[k]=p;count++;
  }
  Need(count==Total,"X0 original native IDs missing/excluded");
  for(unsigned k=0;k<Total;k++)Need(s.slots[k]!=UINT_MAX,"X0 native ID map incomplete");
}
inline void Init(const void* owner,const std::string& directory,unsigned np,const unsigned* id,const typecode* code,
  const float* p,const float* p0,const double* j,const float* kappa){
  State& s=state;Need(Requested()&&!s.ready&&!s.owner,"X0 private State initialized twice");
  Need(p&&p0&&j&&kappa,"X0 initial arrays absent");s.owner=owner;s.directory=directory;
  s.slots.resize(Total);s.seen.resize(Total);s.drained.resize(Total);s.commitDrained.resize(Total);
  s.previous.resize(Total);s.previousUsed.resize(Total);s.pn.resize(Total);s.half.resize(Total);s.guess.resize(Total);s.raw.resize(Total);s.finalP.resize(Total);
  s.S.resize(Total);s.R.resize(Total);s.thetaH.resize(Total);s.thetaEndpoint.resize(Total);s.Jn.resize(Total);s.Jhalf.resize(Total);s.Jfull.resize(Total);
  Map(np,id,code);
  for(unsigned k=Fixed;k<Total;k++){
    const unsigned a=s.slots[k];Need(p[a]==0.f&&p0[a]==0.f&&j[a]==1.&&kappa[a]==0.f,"X0 requires fresh zero-pressure/J1/zero-kappa soil");
    s.previous[k]=p[a];s.previousUsed[k]=p[a];s.pn[k]=p[a];s.half[k]=p[a];s.guess[k]=p[a];s.raw[k]=p[a];s.finalP[k]=p[a];
    s.Jn[k]=j[a];s.Jhalf[k]=j[a];s.Jfull[k]=j[a];
  }
  const std::string path=directory+"C02TpiX0.csv";
  Need(!std::ifstream(path.c_str()).good(),"X0 sidecar already exists; no overwrite");
  Need(!std::ifstream((directory+"C02TpiX0.summary.json").c_str()).good(),"X0 summary already exists; no overwrite");
  s.csv=new std::ofstream(path.c_str(),std::ios::out|std::ios::trunc);Need(bool(*s.csv),"X0 sidecar open failed");
  *s.csv<<std::setprecision(17)<<"part,kind,native_id,source_time_s,actual_save_time_s,source_step_zero_based,completed_step,dt_s,pn_Pa,previous_Pa,half_Pa,guess_Pa,raw_final_Pa,final_Pa,S_1_per_m_s,Rgamma_Pa_per_m_s,theta_h_for_J_1_per_s,theta_endpoint_1_per_s,Jn,Jhalf,Jfull,endpoint_drained,commit_drained,commits,endpoint_calls\n";
  s.ready=true;
}
inline void Begin(const void* owner,unsigned np,const unsigned* id,const typecode* code,const float* pn,
  const double* j,double time,unsigned step,double dt){
  State& s=state;Need(s.ready&&s.owner==owner&&!s.pending&&!s.temporary&&!s.endpoint,"X0 predictor lifecycle invalid");
  Need(step==s.commits&&dt==Dt&&std::isfinite(time)&&(step==0?time==0.:Bits(time,s.lastEnd)),"X0 scalar clock/step/fixed dt differs");
  Map(np,id,code);s.sourceTime=time;s.sourceStep=step;s.dt=dt;s.rows=0;s.rowError=0;s.rowErrorId=UINT_MAX;
  std::fill(s.seen.begin(),s.seen.end(),0);std::fill(s.drained.begin(),s.drained.end(),0);std::fill(s.commitDrained.begin(),s.commitDrained.end(),0);
  for(unsigned k=Fixed;k<Total;k++){
    const unsigned a=s.slots[k];Need(std::isfinite(pn[a])&&std::isfinite(j[a])&&j[a]>0.,"X0 predictor source not finite");
    s.pn[k]=pn[a];s.previousUsed[k]=s.previous[k];s.Jn[k]=j[a];
    const double h=double(pn[a])+.5*(double(pn[a])-double(s.previous[k]));
    Need(std::isfinite(h)&&std::fabs(h)<=FLT_MAX,"X0 history half/guess overflow");
    s.half[k]=float(h);s.guess[k]=float(h);
  }
  s.pending=true;s.preCalls++;
}
inline float Half(unsigned id){Need(id>=Fixed&&id<Total&&state.pending,"X0 half ID/lifecycle invalid");return state.half[id];}
inline void HalfActual(unsigned id,float p){Need(id>=Fixed&&id<Total&&state.pending,"X0 half actual ID invalid");state.half[id]=p;}
inline void Corr(const void* owner,unsigned np,const unsigned* id,const typecode* code,const float* phalf,const double* jhalf,const double* theta){
  State& s=state;Need(s.ready&&s.owner==owner&&s.pending&&!s.temporary&&!s.endpoint&&s.corrCalls+1==s.preCalls,"X0 corrector lifecycle invalid");Map(np,id,code);
  for(unsigned k=Fixed;k<Total;k++){
    const unsigned a=s.slots[k];Need(std::isfinite(phalf[a])&&std::isfinite(jhalf[a])&&jhalf[a]>0&&std::isfinite(theta[a]),"X0 actual p-half/J-half/theta-half invalid");
    s.half[k]=phalf[a];s.Jhalf[k]=jhalf[a];s.thetaH[k]=theta[a];
  }
  s.corrCalls++;s.temporary=true;
}
inline float Guess(unsigned id){Need(id>=Fixed&&id<Total&&state.pending&&state.temporary,"X0 guess ID/lifecycle invalid");return state.guess[id];}
inline void CaptureJ(const void* owner,unsigned np,const unsigned* id,const typecode* code,const double* j){
  State& s=state;Need(s.owner==owner&&s.pending&&s.temporary&&s.jCalls+1==s.corrCalls,"X0 J corrector capture lifecycle invalid");Map(np,id,code);
  for(unsigned k=Fixed;k<Total;k++){const double v=j[s.slots[k]];Need(std::isfinite(v)&&v>0.,"X0 completed J invalid");s.Jfull[k]=v;}
  s.jCalls++;
}
inline void Endpoint(const void* owner,unsigned np,const unsigned* id,const typecode* code,const float* p,const double* j,
  double time,unsigned step,double dt){
  State& s=state;Need(s.owner==owner&&s.pending&&s.temporary&&!s.endpoint&&s.jCalls==s.preCalls,"X0 endpoint lifecycle invalid");
  Need(Bits(time,s.sourceTime)&&step==s.sourceStep&&dt==s.dt,"X0 endpoint advanced the original source clock");Map(np,id,code);
  for(unsigned k=Fixed;k<Total;k++){
    const unsigned a=s.slots[k];Need(Bits(j[a],s.Jfull[k]),"X0 J changed before endpoint force");
    Need(std::isfinite(p[a]),"X0 endpoint actual guess not finite");s.guess[k]=p[a];
  }
  s.endpoint=true;s.endpointCalls++;
}
inline void Row(unsigned id,bool drained,double diagonal,double residual,double theta,float actualGuess){
  // This hook is inside the original OMP region. CPU1 is enforced, so a first-error
  // latch suffices; throw only at the later serial PrepareFinal point.
  State& s=state;
  unsigned error=0;
  if(!s.endpoint || !s.pending || id<Fixed || id>=Total)error=1;
  else if(s.seen[id])error=2;
  else if(!std::isfinite(theta) || !std::isfinite(actualGuess))error=3;
  else if(!drained && (!std::isfinite(diagonal) || !(diagonal>0.) || !std::isfinite(residual)))error=4;
  if(error){if(!s.rowError){s.rowError=error;s.rowErrorId=id;}return;}
  s.seen[id]=1;s.rows++;s.drained[id]=unsigned(drained);s.thetaEndpoint[id]=theta;s.guess[id]=actualGuess;
  if(drained){s.S[id]=0.;s.R[id]=0.;return;}
  s.S[id]=diagonal;s.R[id]=residual;
}
inline void PrepareFinal(const void* owner,unsigned np,const unsigned* id,const typecode* code,const double* j){
  State& s=state;
  if(s.rowError)throw std::runtime_error("X0 endpoint row rejected: code="+std::to_string(s.rowError)+" native_id="+std::to_string(s.rowErrorId)+" (1 lifecycle/ID,2 duplicate,3 theta/guess,4 nonfinite/S<=0); no regularization/history commit");
  Need(s.owner==owner&&s.endpoint&&s.rows==Soil,"X0 incomplete endpoint pressure rows");Map(np,id,code);
  for(unsigned k=Fixed;k<Total;k++){
    Need(s.seen[k]&&Bits(j[s.slots[k]],s.Jfull[k]),"X0 endpoint force altered J or missed a native row");
    const double v=s.drained[k]?0.:double(s.guess[k])+s.R[k]/s.S[k];
    Need(std::isfinite(v)&&std::fabs(v)<=FLT_MAX,"X0 final pressure overflow; history not committed");s.raw[k]=float(v);
  }
}
inline void WriteFinal(unsigned np,unsigned npb,const unsigned* id,const typecode* code,float* p){
  State& s=state;Need(s.endpoint&&s.pending&&s.rows==Soil,"X0 final write lifecycle invalid");
  // Same native owner value for every periodic copy. Fixed wall pressure is reconstructed by the original boundary policy.
  for(unsigned a=npb;a<np;a++)if(CODE_IsFluid(code[a])){Need(id[a]>=Fixed&&id[a]<Total,"X0 final periodic owner ID invalid");p[a]=s.raw[id[a]];}
}
inline void Commit(const void* owner,unsigned np,const unsigned* id,const typecode* code,const float* p,const double* j){
  State& s=state;Need(s.owner==owner&&s.pending&&!s.temporary&&!s.endpoint&&s.rows==Soil,"X0 history commit lifecycle invalid");Map(np,id,code);
  // Validate every native receiver before rotating any full-step history.
  for(unsigned k=Fixed;k<Total;k++){
    const unsigned a=s.slots[k];Need(std::isfinite(p[a])&&Bits(j[a],s.Jfull[k]),"X0 final boundary altered J or nonfinite p");
    if(s.commitDrained[k])Need(p[a]==0.f,"X0 original Dirichlet pressure not zero");
  }
  for(unsigned k=Fixed;k<Total;k++){s.finalP[k]=p[s.slots[k]];s.previous[k]=s.pn[k];}
  s.lastEnd=s.sourceTime+s.dt;s.commits++;s.pending=false;
}
inline void Saved(const void* owner,unsigned part,double actualTime,unsigned step,unsigned np,const unsigned* id,const typecode* code,
  const float* p,const double* j){
  State& s=state;Need(s.ready&&s.owner==owner&&!s.pending&&!s.temporary&&!s.endpoint&&s.csv,"X0 save before valid full commit");Map(np,id,code);
  const bool initial=s.commits==0;Need(initial?(actualTime==0.&&step==0):(Bits(actualTime,s.lastEnd)&&step+1==s.commits),"X0 saved scalar clock differs");
  for(unsigned k=Fixed;k<Total;k++){
    const unsigned a=s.slots[k];Need(Bits(j[a],s.Jfull[k])&&Bits(p[a],s.finalP[k]),"X0 native save changed completed p/J");
    *s.csv<<part<<','<<(initial?"initial":"committed")<<','<<k<<','<<s.sourceTime<<','<<actualTime<<','<<s.sourceStep<<','<<s.commits<<','<<(initial?0.:s.dt)<<','
      <<s.pn[k]<<','<<s.previousUsed[k]<<','<<s.half[k]<<','<<s.guess[k]<<','<<s.raw[k]<<','<<p[a]<<',';
    if(!initial)*s.csv<<s.S[k]<<','<<s.R[k];else *s.csv<<',';
    *s.csv<<','<<s.thetaH[k]<<','<<s.thetaEndpoint[k]<<','<<s.Jn[k]<<','<<s.Jhalf[k]<<','<<s.Jfull[k]<<','<<s.drained[k]<<','<<s.commitDrained[k]<<','<<s.commits<<','<<s.endpointCalls<<'\n';
  }
  s.csv->flush();Need(bool(*s.csv),"X0 sidecar flush failed");s.saves++;
}
inline void Finish(const void* owner,unsigned step,double time){
  State& s=state;Need(s.ready&&s.owner==owner&&!s.pending&&!s.temporary&&!s.endpoint&&s.commits==step&&Bits(time,s.lastEnd),"X0 final counters/lifecycle invalid");
  Need(s.preCalls==step&&s.corrCalls==step&&s.jCalls==step&&s.endpointCalls==step,"X0 missing/duplicate pressure/J/endpoint/history step");
  std::ofstream out((s.directory+"C02TpiX0.summary.json").c_str(),std::ios::out|std::ios::trunc);Need(bool(out),"X0 summary open failed");
  out<<std::setprecision(17)<<"{\"stage\":\"c08_tpi_x0_r2\",\"completed\":true,\"alpha\":0.5,\"beta\":0,\"dt_s\":"<<Dt<<",\"commits\":"<<s.commits
    <<",\"pre_calls\":"<<s.preCalls<<",\"corr_calls\":"<<s.corrCalls<<",\"J_corrector_captures\":"<<s.jCalls<<",\"endpoint_calls\":"<<s.endpointCalls
    <<",\"native_save_events\":"<<s.saves<<",\"sidecar_native_ids_per_save\":1000,\"actual_end_s\":"<<time
    <<",\"finite_Kw_pressure_update_skipped\":true,\"J_solid_update_unchanged\":true,\"endpoint_source_clock_is_original_n\":true,\"endpoint_theta_is_not_J_integration_theta\":true,\"history_cold_start\":true,\"full_restart_supported\":false,\"paper_literal_LF\":false,\"true_implicit_solution\":false,\"physical_acceptance\":false}\n";
  out.flush();Need(bool(out),"X0 summary write failed");
}
} // namespace c08x0
#endif
