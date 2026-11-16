// Private C08 M0/TPI endpoint extension. Not a public XML interface or literal paper LF.
#pragma once
#include "DualSphDef.h"
#include <algorithm>
#include <cfloat>
#include <climits>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <string>
#include <vector>
namespace c08negative {
constexpr unsigned Fixed=1805,SoilFirst=2060,Soil=5000,Total=7060,Active=6805,SourceStep=2000000,MaxNewUpdates=600000;
constexpr double Dt=5e-6,Alpha=.5;
inline void Need(bool ok,const char* msg){if(!ok)throw std::runtime_error(msg);}
template<class V> inline bool Bits(const V& a,const V& b){return std::memcmp(&a,&b,sizeof(V))==0;}
inline bool Requested(){static const bool on=[](){const char* e=std::getenv("C08_TPI_NEGATIVE");
  if(!e||!*e)return false;Need(std::strcmp(e,"1")==0,"C08_TPI_NEGATIVE must be absent or exact 1");return true;}();return on;}
inline double RequestedBeta(){const char* b=std::getenv("C08_TPI_NEGATIVE_BETA");
  Need(b&&(std::strcmp(b,"0")==0||std::strcmp(b,"0.04")==0),"Active private beta requires exact 0 or 0.04 [1/m]");return std::strcmp(b,"0")==0?0.:.04;}
inline void RejectHGEnvironment(){const char* e=std::getenv("C08_HG_OPT_H18");const char* cached=std::getenv("C08_HG_CACHED_H18");const char* old=std::getenv("C08_HG_H18");
  Need(!e&&!cached&&!old,"HG environments must be absent for the C08 TPI candidate");}
struct Core{tdouble3 pos;tfloat4 velrhop;tsymatrix3d sigma;float kappa,p0,guess;double j;};
static_assert(sizeof(tdouble3)==3*sizeof(double)&&sizeof(tfloat4)==4*sizeof(float)&&sizeof(tsymatrix3d)==6*sizeof(double),"Private core snapshot ABI differs");
struct State{
  const void* owner=nullptr;bool ready=false,pending=false,temporary=false,endpoint=false;
  unsigned preCalls=0,corCalls=0,jCalls=0,endpointCalls=0,commits=0,rows=0,rowError=0,rowErrorId=UINT_MAX;
  unsigned sourceStep=0,negativeRows=0,betaRows=0;double initialTime=0,sourceTime=0,lastEnd=0,dt=0,beta=0;
  unsigned long long coreFieldChecks=0;
  std::vector<unsigned> slot,seen,drained,commitDrained;
  std::vector<float> previous,previousUsed,pn,half,guess,raw,finalP,initialP0;
  std::vector<double> pAlpha,S,R,denominator,Jn,Jhalf,Jfull,thetaH,thetaEndpoint;
  std::vector<Core> core;std::ofstream* csv=nullptr;std::string directory;
  ~State(){delete csv;}
};
extern State state;
inline bool IsSoil(unsigned id){return id>=SoilFirst&&id<Total;}
inline void Map(unsigned np,const unsigned* id,const typecode* code){
  State& s=state;Need(np==Active&&id&&code&&s.slot.size()==Total,"C08 negative map count/storage invalid");
  std::fill(s.slot.begin(),s.slot.end(),UINT_MAX);unsigned fixed=0,soil=0;
  for(unsigned p=0;p<np;p++){unsigned k=id[p];Need(k<Total&&(k<Fixed||IsSoil(k))&&s.slot[k]==UINT_MAX&&CODE_IsNormal(code[p]),"C08 negative native ownership changed");
    Need(k<Fixed?CODE_IsFixed(code[p]):CODE_IsFluid(code[p]),"C08 negative native material type changed");s.slot[k]=p;if(k<Fixed)fixed++;else soil++;}
  Need(fixed==Fixed&&soil==Soil,"C08 negative lost fixed or soil IDs");
}
inline void Init(const void* owner,const std::string& dir,unsigned np,unsigned npb,const unsigned* id,const typecode* code,
  const float* p,const float* p0,const double* j,const float* kappa,double time,unsigned step,double dt){
  State& s=state;Need(Requested()&&!s.ready&&!s.owner&&npb==Fixed&&step==SourceStep&&dt==Dt&&std::isfinite(time),"C08 TPI requires one actual released schema2 handoff");
  RejectHGEnvironment();s.owner=owner;s.directory=dir;s.initialTime=s.lastEnd=time;s.beta=RequestedBeta();
  s.slot.resize(Total);s.seen.resize(Total);s.drained.resize(Total);s.commitDrained.resize(Total);
  s.previous.resize(Total);s.previousUsed.resize(Total);s.pn.resize(Total);s.half.resize(Total);s.guess.resize(Total);s.raw.resize(Total);s.finalP.resize(Total);s.initialP0.resize(Total);
  s.pAlpha.resize(Total);s.S.resize(Total);s.R.resize(Total);s.denominator.resize(Total);s.Jn.resize(Total);s.Jhalf.resize(Total);s.Jfull.resize(Total);s.thetaH.resize(Total);s.thetaEndpoint.resize(Total);s.core.resize(Total);
  Map(np,id,code);Need(p&&p0&&j&&kappa,"C08 TPI source fields absent");
  for(unsigned k=SoilFirst;k<Total;k++){const unsigned a=s.slot[k];Need(std::isfinite(p[a])&&std::isfinite(p0[a])&&std::isfinite(j[a])&&j[a]>0&&std::isfinite(kappa[a])&&kappa[a]>=0,"C08 TPI source state invalid");
    s.previous[k]=p[a];s.previousUsed[k]=p[a];s.pn[k]=p[a];s.half[k]=p[a];s.guess[k]=p[a];s.raw[k]=p[a];s.finalP[k]=p[a];s.initialP0[k]=p0[a];s.pAlpha[k]=double(p[a]);s.Jn[k]=s.Jhalf[k]=s.Jfull[k]=j[a];}
  const std::string csv=dir+"C08TpiNegative.csv",policy=dir+"C08TpiNegativePolicy.json";
  Need(!std::ifstream(csv).good()&&!std::ifstream(policy).good(),"C08 TPI sidecar exists; never overwrite");
  s.csv=new std::ofstream(csv,std::ios::out|std::ios::trunc);Need(bool(*s.csv),"C08 TPI CSV open failed");
  *s.csv<<std::setprecision(17)<<"part,native_id,source_step_zero_based,completed_step,source_time_s,actual_save_time_s,dt_s,pn_Pa,previous_Pa,pAlpha_double_Pa,half_actual_float_Pa,q_actual_float_Pa,S_LP_1_per_m_s,Rgamma_double_Pa_per_m_s,beta_effective_1_per_m,beta_active,denominator_1_per_m_s,raw_final_float_Pa,final_float_Pa,theta_h_for_J_1_per_s,theta_endpoint_1_per_s,Jn,Jhalf,Jfull,endpoint_drained,commit_drained,commits,endpoint_calls,core_field_bit_checks\n";
  std::ofstream out(policy);Need(bool(out),"C08 TPI policy open failed");out<<std::setprecision(17)<<"{\"stage\":\"c08_tpi_negative_r1\",\"scheme\":\"M0_TPI_original_space_Symplectic_endpoint_extension\",\"alpha\":0.5,\"beta_1_per_m\":"<<s.beta<<",\"branch\":\"old_total_pn<0 in admitted plastic case; zero uses beta0\",\"history_cold_start\":true,\"previous_initialized_from_actual_pn\":true,\"full_restart_supported\":false,\"finite_Kw_pressure_update_skipped\":true,\"paper_literal_LF\":false,\"true_implicit_solution\":false,\"negative_pressure_clipped\":false,\"HG_active\":false,\"ReactionClosed\":false,\"physical_acceptance\":false}\n";
  out.flush();Need(bool(out),"C08 TPI policy write failed");s.ready=true;
}
inline void Begin(const void* owner,unsigned np,const unsigned* id,const typecode* code,const float* pn,const double* j,double time,unsigned step,double dt){
  State& s=state;Need(s.ready&&s.owner==owner&&!s.pending&&!s.temporary&&!s.endpoint,"C08 TPI predictor lifecycle invalid");
  Need(step==SourceStep+s.commits&&s.commits<MaxNewUpdates&&dt==Dt&&Bits(time,s.lastEnd),"C08 TPI actual scalar clock/step/dt changed");
  Map(np,id,code);s.sourceTime=time;s.sourceStep=step;s.dt=dt;s.rows=0;s.rowError=0;s.rowErrorId=UINT_MAX;s.negativeRows=s.betaRows=0;
  std::fill(s.seen.begin(),s.seen.end(),0);std::fill(s.drained.begin(),s.drained.end(),0);std::fill(s.commitDrained.begin(),s.commitDrained.end(),0);
  for(unsigned k=SoilFirst;k<Total;k++){const unsigned a=s.slot[k];Need(std::isfinite(pn[a])&&std::isfinite(j[a])&&j[a]>0,"C08 TPI predictor state invalid");
    s.pn[k]=pn[a];s.previousUsed[k]=s.previous[k];s.Jn[k]=j[a];s.pAlpha[k]=double(pn[a])+Alpha*(double(pn[a])-double(s.previous[k]));
    Need(std::isfinite(s.pAlpha[k])&&std::fabs(s.pAlpha[k])<=FLT_MAX,"C08 TPI pressure extrapolation overflow");s.half[k]=float(s.pAlpha[k]);s.guess[k]=s.half[k];}
  s.pending=true;s.preCalls++;
}
inline float Half(unsigned id){Need(IsSoil(id)&&state.pending,"C08 TPI half ID invalid");return state.half[id];}
inline void HalfActual(unsigned id,float p){Need(IsSoil(id)&&state.pending,"C08 TPI half actual ID invalid");state.half[id]=p;}
inline void Corr(const void* owner,unsigned np,const unsigned* id,const typecode* code,const float* phalf,const double* jhalf,const double* theta){
  State& s=state;Need(s.owner==owner&&s.pending&&!s.temporary&&!s.endpoint&&s.corCalls+1==s.preCalls,"C08 TPI corrector lifecycle invalid");Map(np,id,code);
  for(unsigned k=SoilFirst;k<Total;k++){unsigned a=s.slot[k];Need(std::isfinite(phalf[a])&&std::isfinite(jhalf[a])&&jhalf[a]>0&&std::isfinite(theta[a]),"C08 TPI actual half state invalid");s.half[k]=phalf[a];s.Jhalf[k]=jhalf[a];s.thetaH[k]=theta[a];}
  s.corCalls++;s.temporary=true;
}
inline float Guess(unsigned id){Need(IsSoil(id)&&state.pending&&state.temporary,"C08 TPI guess lifecycle invalid");return state.guess[id];}
inline void CaptureJ(const void* owner,unsigned np,const unsigned* id,const typecode* code,const double* j){
  State& s=state;Need(s.owner==owner&&s.pending&&s.temporary&&s.jCalls+1==s.corCalls,"C08 TPI J capture lifecycle invalid");Map(np,id,code);
  for(unsigned k=SoilFirst;k<Total;k++){double v=j[s.slot[k]];Need(std::isfinite(v)&&v>0,"C08 TPI full J invalid");s.Jfull[k]=v;}s.jCalls++;
}
inline void Endpoint(const void* owner,unsigned np,const unsigned* id,const typecode* code,const tdouble3* pos,const tfloat4* velrhop,
  const tsymatrix3d* sigma,const float* kappa,const float* p0,const float* q,const double* j,double time,unsigned step,double dt){
  State& s=state;Need(s.owner==owner&&s.pending&&s.temporary&&!s.endpoint&&s.jCalls==s.preCalls&&Bits(time,s.sourceTime)&&step==s.sourceStep&&dt==s.dt,"C08 TPI endpoint clock/lifecycle invalid");Map(np,id,code);
  for(unsigned k=SoilFirst;k<Total;k++){unsigned a=s.slot[k];Need(Bits(j[a],s.Jfull[k])&&Bits(p0[a],s.initialP0[k])&&std::isfinite(q[a]),"C08 TPI endpoint state or P0 changed");
    s.core[k]={pos[a],velrhop[a],sigma[a],kappa[a],p0[a],q[a],j[a]};s.guess[k]=q[a];}
  s.endpoint=true;s.endpointCalls++;
}
inline void Row(unsigned id,bool drained,double S,double R,double theta,float q){
  State& s=state;unsigned error=0;
  if(!s.endpoint||!s.pending||!IsSoil(id))error=1;else if(s.seen[id])error=2;
  else if(!std::isfinite(theta)||!std::isfinite(q))error=3;else if(!drained&&(!std::isfinite(S)||S<=0||!std::isfinite(R)))error=4;
  if(error){if(!s.rowError){s.rowError=error;s.rowErrorId=id;}return;}
  s.seen[id]=1;s.rows++;s.drained[id]=unsigned(drained);s.thetaEndpoint[id]=theta;s.guess[id]=q;s.S[id]=drained?0.:S;s.R[id]=drained?0.:R;
}
inline void PrepareFinal(const void* owner,unsigned np,const unsigned* id,const typecode* code,const tdouble3* pos,const tfloat4* velrhop,
  const tsymatrix3d* sigma,const float* kappa,const float* p0,const float* q,const double* j){
  State& s=state;if(s.rowError)throw std::runtime_error("C08 TPI endpoint row rejected code="+std::to_string(s.rowError)+" native_id="+std::to_string(s.rowErrorId));
  Need(s.owner==owner&&s.endpoint&&s.rows==Soil,"C08 TPI endpoint rows incomplete");Map(np,id,code);
  for(unsigned k=SoilFirst;k<Total;k++){unsigned a=s.slot[k];const Core& c=s.core[k];
    Need(s.seen[k]&&Bits(pos[a],c.pos)&&Bits(velrhop[a],c.velrhop)&&Bits(sigma[a],c.sigma)&&Bits(kappa[a],c.kappa)&&Bits(p0[a],c.p0)&&Bits(j[a],c.j)&&Bits(q[a],c.guess),"Extra TPI force changed a committed soil field");s.coreFieldChecks+=7;
    const double beta=(!s.drained[k]&&s.pn[k]<0.f?s.beta:0.),b=beta/s.dt,den=s.S[k]+b;
    if(s.pn[k]<0.f)s.negativeRows++;if(beta>0)s.betaRows++;
    const double actualQ=double(s.guess[k]);
    // Retain compensation when float/source-BC q differs from the true double history extrapolate.
    Need(s.drained[k]||(std::isfinite(den)&&den>0.),"C08 TPI invalid row denominator; no epsilon or row removal");
    const double value=s.drained[k]?0.:actualQ+(s.R[k]+b*(s.pAlpha[k]-actualQ))/den;
    Need(std::isfinite(value)&&std::fabs(value)<=FLT_MAX,"C08 TPI final pressure overflow; no history commit");s.denominator[k]=s.drained[k]?0.:den;s.raw[k]=float(value);
  }
}
inline void WriteFinal(unsigned np,unsigned npb,const unsigned* id,const typecode* code,float* p){
  State& s=state;Need(s.endpoint&&s.pending&&s.rows==Soil&&npb==Fixed,"C08 TPI final write lifecycle invalid");
  for(unsigned a=npb;a<np;a++)if(CODE_IsFluid(code[a])){Need(IsSoil(id[a]),"C08 TPI final ID invalid");p[a]=s.raw[id[a]];}
}
inline void Commit(const void* owner,unsigned np,const unsigned* id,const typecode* code,const unsigned* fs,const float* p,const float* p0,const double* j){
  State& s=state;Need(s.owner==owner&&s.pending&&!s.temporary&&!s.endpoint&&s.rows==Soil,"C08 TPI history commit lifecycle invalid");Map(np,id,code);
  for(unsigned k=SoilFirst;k<Total;k++){unsigned a=s.slot[k];Need(std::isfinite(p[a])&&Bits(j[a],s.Jfull[k])&&Bits(p0[a],s.initialP0[k]),"C08 TPI final BC changed J/P0 or nonfinite p");
    Need(!s.commitDrained[k]||p[a]==0.f,"C08 TPI true Dirichlet pressure not zero");Need((fs[a]!=2&&fs[a]!=3)||p[a]<=0.f,"C08 TPI original completed free-seepage cap missing");}
  for(unsigned k=SoilFirst;k<Total;k++){s.finalP[k]=p[s.slot[k]];s.previous[k]=s.pn[k];}s.lastEnd=s.sourceTime+s.dt;s.commits++;s.pending=false;
}
inline void Saved(const void* owner,unsigned part,double time,unsigned step,unsigned np,const unsigned* id,const typecode* code,const float* p,const double* j){
  State& s=state;Need(s.owner==owner&&s.ready&&!s.pending&&s.commits&&Bits(time,s.lastEnd)&&step+1==SourceStep+s.commits,"C08 TPI saved clock/commit differs");Map(np,id,code);
  for(unsigned k=SoilFirst;k<Total;k++){unsigned a=s.slot[k];Need(Bits(p[a],s.finalP[k])&&Bits(j[a],s.Jfull[k]),"C08 TPI saved pressure/J differs from committed value");
    *s.csv<<part<<','<<k<<','<<s.sourceStep<<','<<step+1<<','<<s.sourceTime<<','<<time<<','<<s.dt<<','<<s.pn[k]<<','<<s.previousUsed[k]<<','<<s.pAlpha[k]<<','<<s.half[k]<<','<<s.guess[k]<<','<<s.S[k]<<','<<s.R[k]<<','<<(!s.drained[k]&&s.pn[k]<0.f?s.beta:0.)<<','<<unsigned(!s.drained[k]&&s.pn[k]<0.f&&s.beta>0.)<<','<<s.denominator[k]<<','<<s.raw[k]<<','<<p[a]<<','<<s.thetaH[k]<<','<<s.thetaEndpoint[k]<<','<<s.Jn[k]<<','<<s.Jhalf[k]<<','<<s.Jfull[k]<<','<<s.drained[k]<<','<<s.commitDrained[k]<<','<<s.commits<<','<<s.endpointCalls<<','<<s.coreFieldChecks<<'\n';}
  s.csv->flush();Need(bool(*s.csv),"C08 TPI saved sidecar write failed");
}
inline void Finish(const void* owner,unsigned step,double time){
  State& s=state;Need(s.owner==owner&&s.ready&&!s.pending&&step==SourceStep+s.commits&&Bits(time,s.lastEnd),"C08 TPI finish clock/history differs");
  Need(s.preCalls==s.commits&&s.corCalls==s.commits&&s.jCalls==s.commits&&s.endpointCalls==s.commits,"C08 TPI missing or duplicate stage/history");
  Need(s.coreFieldChecks==7ull*Soil*s.commits,"C08 TPI missing or duplicate endpoint core-field bit checks");
  const std::string path=s.directory+"C08TpiNegative.summary.json";Need(!std::ifstream(path).good(),"C08 TPI summary exists");std::ofstream out(path);Need(bool(out),"C08 TPI summary open failed");
  out<<std::setprecision(17)<<"{\"stage\":\"c08_tpi_negative_r1\",\"completed\":true,\"alpha\":0.5,\"beta_1_per_m\":"<<s.beta<<",\"commits\":"<<s.commits<<",\"endpoint_calls\":"<<s.endpointCalls<<",\"core_field_bit_checks\":"<<s.coreFieldChecks<<",\"actual_end\":"<<time<<",\"M0\":true,\"history_cold_start\":true,\"full_restart_supported\":false,\"J_solid_update_unchanged\":true,\"endpoint_source_clock_is_original_n\":true,\"theta_endpoint_is_not_J_integration_theta\":true,\"paper_literal_LF\":false,\"true_implicit_solution\":false,\"ReactionClosed\":false,\"physical_acceptance\":false}\n";
  out.flush();Need(bool(out),"C08 TPI summary write failed");
}
} // namespace c08negative
