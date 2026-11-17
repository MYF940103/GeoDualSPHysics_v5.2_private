// Private CPU P2 author: two full endpoint defects, one final history commit. No public XML/restart claim.
#pragma once
#include "DualSphDef.h"
#include <algorithm>
#include <atomic>
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

namespace upl_tpi_cpu_r1 {
inline void Need(bool okay,const char* message){if(!okay)throw std::runtime_error(message);}
template<class T> inline bool Bits(const T& a,const T& b){return std::memcmp(&a,&b,sizeof(T))==0;}
enum Scheme{A_FiniteKw,B_Tpi,C_PpeT};
inline Scheme RequestedScheme(){
  static const Scheme scheme=[](){
    const char* e=std::getenv("UPL_TPI_CPU_R1");
    if(!e || !*e || std::strcmp(e,"A")==0)return A_FiniteKw;
    if(std::strcmp(e,"B")==0)return B_Tpi;
    Need(std::strcmp(e,"C")==0,"UPL_TPI_CPU_R1 must be absent or exact A/B/C");return C_PpeT;
  }();return scheme;
}
inline bool Enabled(){
  if(RequestedScheme()==A_FiniteKw)return false; // A must not inspect the P2 selector.
  Need(RequestedScheme()==B_Tpi,"Private P2 supports only B alpha .5");
  static const bool admitted=[](){const char* e=std::getenv("UPL_TPI_P2_ROWS_R1");
    Need(e&&std::strcmp(e,"2")==0,"Private P2 requires explicit UPL_TPI_P2_ROWS_R1=2");return true;}();return admitted;
}
inline double Alpha(){return RequestedScheme()==B_Tpi?.5:0.;}
inline const char* Name(){return "B_TPI_alpha_0p5_beta0_P2_rows2";}
// The mechanical half and endpoint guess are the same history prediction.
// This is a full pressure-prediction ablation, not merely a last-row change.
inline double Predict(double pn,double previous,double alpha){
  Need(std::isfinite(pn)&&(alpha==0.||alpha==.5),"Invalid beta0 pressure prediction");
  if(alpha==0.)return pn; // C has no numerical dependence on previous.
  Need(std::isfinite(previous),"B previous complete-step pressure is invalid");
  const double q=pn+alpha*(pn-previous);
  Need(std::isfinite(q)&&std::fabs(q)<=FLT_MAX,"Pressure prediction overflows float storage");return q;
}
// S=-k*sum(w) is a positive leading-LP preconditioner, not the complete
// derivative of Taylor/inertial feedback in Rgamma. This is one defect
// correction; for nonzero S its fixed point satisfies Rgamma=0. It is not a
// complete-Jacobian Jacobi step or a converged implicit pressure solve.
inline double SolveBeta0(bool drained,double actualQ,double diagonal,double residual){
  if(drained)return 0.;
  Need(std::isfinite(actualQ)&&std::isfinite(diagonal)&&diagonal>0.&&std::isfinite(residual),"Invalid beta0 row; no epsilon or removed row is permitted");
  const double p=actualQ+residual/diagonal;
  Need(std::isfinite(p)&&std::fabs(p)<=FLT_MAX,"Beta0 row overflows float storage");return p;
}
struct Core{tdouble3 pos;tfloat4 velrhop;tsymatrix3d sigma;float kappa,p0,q;double j;};
static_assert(sizeof(tdouble3)==3*sizeof(double)&&sizeof(tfloat4)==4*sizeof(float)&&sizeof(tsymatrix3d)==6*sizeof(double),"Endpoint core ABI differs");
struct HgRecord{tdouble3 history,rate;};
// A deep host record. priorFinalP is the old committed field, NOT the first solution.
struct FirstEndpointRecord{
  float pn=0,previous=0,half=0,q=0,raw=0,actualBC=0,priorFinalP=0;
  double predicted=0,S=0,R=0,Jn=0,Jhalf=0,Jfull=0,thetaH=0,thetaEndpoint=0;
  unsigned sourceDrained=0,drained=0,commitDrained=0;
};
struct State{
  const void* owner=nullptr;
  bool ready=false,pending=false,temporary=false,endpoint=false,prepared=false;
  bool firstValidated=false,secondStarting=false,roundWritten=false;unsigned endpointRound=0;
  unsigned long long firstValidations=0,secondStarts=0,endpointWrites=0;
  std::vector<FirstEndpointRecord> firstRows;
  unsigned nativeCount=0,fixedCount=0,soilCount=0;
  unsigned long long initialStep=0,sourceStep=0,commits=0;
  unsigned long long preCalls=0,corCalls=0,jCalls=0,endpointCalls=0,coreFieldChecks=0,hgSnapshotChecks=0;
  double initialTime=0,sourceTime=0,lastEnd=0,dt=0;
  std::vector<unsigned> slot,role,nativeIds,soilIds,seen,rowError,sourceDrained,drained,commitDrained;
  std::atomic<unsigned> unexpectedRows{0};
  std::vector<float> previous,previousUsed,pn,half,q,raw,finalP,initialP0;
  std::vector<double> predicted,S,R,Jn,Jhalf,Jfull,thetaH,thetaEndpoint;
  std::vector<Core> core;
  std::vector<HgRecord> hg;
  std::vector<double> hgStats,hgRateInfo;
  std::ofstream* csv=nullptr;std::string directory;
  ~State(){delete csv;}
};
extern State state;
inline bool IsSoil(unsigned id){return id<state.role.size()&&state.role[id]==2;}
// Native identities are captured once; periodic copies resolve through their
// original ID and never get their own history. No case ID range is hard-coded.
inline void Map(unsigned np,const unsigned* id,const typecode* code){
  State& s=state;Need(id&&code&&!s.role.empty(),"Native map is not configured");
  std::fill(s.slot.begin(),s.slot.end(),UINT_MAX);unsigned normal=0,fixed=0,soil=0;
  for(unsigned p=0;p<np;p++)if(CODE_IsNormal(code[p])){
    const unsigned k=id[p];Need(k<s.role.size()&&s.role[k]&&s.slot[k]==UINT_MAX,"Native owner ID missing, new or duplicated");
    Need(s.role[k]==1?CODE_IsFixed(code[p]):CODE_IsFluid(code[p]),"Native material role changed");
    s.slot[k]=p;normal++;if(s.role[k]==1)fixed++;else soil++;
  }
  Need(normal==s.nativeCount&&fixed==s.fixedCount&&soil==s.soilCount,"Native set changed");
  for(unsigned k:s.nativeIds)Need(s.slot[k]!=UINT_MAX,"Native ID was lost");
  for(unsigned p=0;p<np;p++)if(!CODE_IsNormal(code[p])){
    Need(CODE_IsPeriodic(code[p])&&id[p]<s.role.size()&&s.role[id[p]]&&s.slot[id[p]]!=UINT_MAX,"Only owned periodic copies are supported");
    Need(s.role[id[p]]==1?CODE_IsFixed(code[p]):CODE_IsFluid(code[p]),"Periodic copy material role changed");
  }
}
inline void Init(const void* owner,const std::string& directory,unsigned np,const unsigned* id,const typecode* code,
  const float* p,const float* p0,const double* j,const float* kappa,double time,unsigned long long step,double dt){
  State& s=state;Need(Enabled()&&!s.ready&&!s.owner&&owner&&id&&code&&p&&p0&&j&&kappa,"Invalid beta0 initialization");
  Need(std::isfinite(time)&&std::isfinite(dt)&&dt>0.,"Invalid initial clock or fixed dt");
  unsigned last=0;
  for(unsigned a=0;a<np;a++)if(CODE_IsNormal(code[a])){
    Need(CODE_IsFixed(code[a])||CODE_IsFluid(code[a]),"Private beta0 prototype requires fixed or soil native owners");
    Need(id[a]<UINT_MAX,"Native ID extent overflows");last=(std::max)(last,id[a]);s.nativeCount++;
  }
  Need(s.nativeCount&&size_t(last)+1<=size_t(UINT_MAX),"Native ID extent invalid");
  const size_t n=size_t(last)+1;s.role.assign(n,0);s.slot.resize(n);s.seen.resize(n);s.rowError.resize(n);s.sourceDrained.resize(n);s.drained.resize(n);s.commitDrained.resize(n);
  s.previous.resize(n);s.previousUsed.resize(n);s.pn.resize(n);s.half.resize(n);s.q.resize(n);s.raw.resize(n);s.finalP.resize(n);s.initialP0.resize(n);
  s.predicted.resize(n);s.S.resize(n);s.R.resize(n);s.Jn.resize(n);s.Jhalf.resize(n);s.Jfull.resize(n);s.thetaH.resize(n);s.thetaEndpoint.resize(n);s.core.resize(n);s.hg.resize(n);s.firstRows.resize(n);
  for(unsigned a=0;a<np;a++)if(CODE_IsNormal(code[a])){
    const unsigned k=id[a];Need(!s.role[k],"Duplicate initial native ID");s.role[k]=CODE_IsFixed(code[a])?1u:2u;s.nativeIds.push_back(k);
    if(s.role[k]==1)s.fixedCount++;else{s.soilIds.push_back(k);s.soilCount++;}
  }
  Need(s.soilCount,"No soil owners for pressure history");Map(np,id,code);
  s.owner=owner;s.directory=directory;s.initialTime=s.sourceTime=s.lastEnd=time;s.initialStep=s.sourceStep=step;s.dt=dt;
  for(unsigned k:s.soilIds){const unsigned a=s.slot[k];
    Need(std::isfinite(p[a])&&std::isfinite(p0[a])&&std::isfinite(j[a])&&j[a]>0.&&std::isfinite(kappa[a])&&kappa[a]>=0.,"Initial native state invalid");
    s.previous[k]=s.previousUsed[k]=s.pn[k]=s.half[k]=s.q[k]=s.raw[k]=s.finalP[k]=p[a];
    s.initialP0[k]=p0[a];s.predicted[k]=double(p[a]);s.Jn[k]=s.Jhalf[k]=s.Jfull[k]=j[a];
  }
  const std::string csv=directory+"UplTpiP2CpuR1.csv",policy=directory+"UplTpiP2CpuR1.policy.json";
  Need(!std::ifstream(csv).good()&&!std::ifstream(policy).good(),"Private pressure sidecar already exists");
  s.csv=new std::ofstream(csv,std::ios::out|std::ios::trunc);Need(bool(*s.csv),"Pressure sidecar open failed");
  *s.csv<<std::setprecision(17)<<"part,pressure_round,native_id,source_step_zero_based,completed_step,source_time_s,actual_save_time_s,dt_s,pn_Pa,previous_Pa,prediction_double_Pa,mechanical_half_actual_float_Pa,endpoint_q_actual_float_Pa,S_1_per_m_s,Rgamma_Pa_per_m_s,raw_candidate_float_Pa,actual_after_BC_float_Pa,prior_committed_finalP_stale_Pa,theta_half_for_J_1_per_s,theta_endpoint_1_per_s,Jn,Jhalf,Jfull,source_drained,endpoint_drained,provisional_or_final_commit_drained,first_endpoint_validated,commits,endpoint_calls,endpoint_writes,core_field_bit_checks,hg_snapshot_checks\n";
  std::ofstream out(policy);Need(bool(out),"P2 pressure policy open failed");
  out<<std::setprecision(17)<<"{\"stage\":\"upl_tpi_p2_cpu_r1\",\"scheme\":\""<<Name()<<"\",\"alpha\":0.5,\"beta\":0,\"M0\":true,\"endpoint_defects_per_step\":2,\"native_count\":"<<s.nativeCount<<",\"soil_count\":"<<s.soilCount<<",\"history_ID_owned\":true,\"history_cold_start\":true,\"full_restart_supported\":false,\"global_source_clock_unchanged\":true,\"staged_load_clock_enabled\":false,\"first_finalP_field_is_prior_commit_not_p1\":true,\"first_actual_BC_is_directly_captured\":true,\"initial_pressure_round0_is_not_endpoint_observation\":true,\"PorePressRate_is_second_endpoint_scaled_residual_not_dpdt\":true,\"scalar_fixture_is_not_spatial_kernel_proof\":true,\"paper_literal_LF\":false,\"second_order_claimed\":false,\"true_implicit_solution\":false,\"physical_acceptance\":false}\n";
  out.flush();Need(bool(out),"Pressure policy write failed");s.ready=true;
}
template<class SourceDrained> inline void Begin(const void* owner,unsigned np,const unsigned* id,const typecode* code,const float* pn,const double* j,double time,unsigned long long step,double dt,SourceDrained sourceDrained){
  State& s=state;Need(s.ready&&s.owner==owner&&!s.pending&&!s.temporary&&!s.endpoint,"Predictor lifecycle invalid");
  Need(step==s.initialStep+s.commits&&dt==s.dt&&Bits(time,s.lastEnd),"Actual scalar clock, completed step or fixed dt changed");
  Map(np,id,code);s.sourceTime=time;s.sourceStep=step;s.unexpectedRows.store(0);s.prepared=false;
  s.firstValidated=false;s.secondStarting=false;s.roundWritten=false;s.endpointRound=0;
  std::fill(s.seen.begin(),s.seen.end(),0);std::fill(s.rowError.begin(),s.rowError.end(),0);std::fill(s.drained.begin(),s.drained.end(),0);std::fill(s.commitDrained.begin(),s.commitDrained.end(),0);
  for(unsigned k:s.soilIds){const unsigned a=s.slot[k];Need(std::isfinite(pn[a])&&std::isfinite(j[a])&&j[a]>0.,"Predictor native state invalid");
    s.sourceDrained[k]=unsigned(sourceDrained(a));
    Need(!s.sourceDrained[k]||pn[a]==0.f,"Original source-clock Dirichlet projection is absent");
    if(s.commits&&!Bits(pn[a],s.finalP[k]))Need(s.sourceDrained[k]&&pn[a]==0.f,"Non-Dirichlet complete-step pressure changed before history capture");
    s.pn[k]=pn[a];s.previousUsed[k]=s.previous[k];s.Jn[k]=j[a];
    s.predicted[k]=(Alpha()==0.?double(pn[a]):Predict(double(pn[a]),double(s.previous[k]),.5));s.half[k]=float(s.predicted[k]);s.q[k]=s.half[k];
  }
  s.pending=true;s.preCalls++;
}
inline float Half(unsigned id){Need(IsSoil(id)&&state.pending,"Half pressure owner invalid");return state.half[id];}
inline void HalfActual(unsigned id,float p){Need(IsSoil(id)&&state.pending&&std::isfinite(p),"Actual half pressure invalid");state.half[id]=p;}
inline void Corr(const void* owner,unsigned np,const unsigned* id,const typecode* code,const float* half,const double* j,const double* theta){
  State& s=state;Need(s.owner==owner&&s.pending&&!s.temporary&&!s.endpoint&&s.corCalls+1==s.preCalls,"Corrector lifecycle invalid");Map(np,id,code);
  for(unsigned k:s.soilIds){const unsigned a=s.slot[k];Need(std::isfinite(half[a])&&std::isfinite(j[a])&&j[a]>0.&&std::isfinite(theta[a]),"Half stage state invalid");s.half[k]=half[a];s.Jhalf[k]=j[a];s.thetaH[k]=theta[a];}
  s.corCalls++;s.temporary=true;
}
inline float Guess(unsigned id){Need(IsSoil(id)&&state.pending&&state.temporary,"Endpoint history guess owner invalid");return float(state.predicted[id]);}
inline void CaptureJ(const void* owner,unsigned np,const unsigned* id,const typecode* code,const double* j){
  State& s=state;Need(s.owner==owner&&s.pending&&s.temporary&&s.jCalls+1==s.corCalls,"J capture lifecycle invalid");Map(np,id,code);
  for(unsigned k:s.soilIds){const double v=j[s.slot[k]];Need(std::isfinite(v)&&v>0.,"Full J invalid");s.Jfull[k]=v;}s.jCalls++;
}
inline void Endpoint(const void* owner,unsigned np,const unsigned* id,const typecode* code,const tdouble3* pos,const tfloat4* velrhop,
  const tsymatrix3d* sigma,const float* kappa,const float* p0,const float* q,const double* j,double time,unsigned long long step,double dt){
  State& s=state;Need(s.owner==owner&&s.pending&&s.temporary&&!s.endpoint&&s.jCalls==s.preCalls&&Bits(time,s.sourceTime)&&step==s.sourceStep&&dt==s.dt,"Endpoint clock or lifecycle invalid");Map(np,id,code);
  Need(s.endpointRound==0||(s.endpointRound==1&&s.firstValidated&&s.secondStarting&&!s.prepared),"P2 duplicate/unvalidated endpoint round");
  for(unsigned k:s.soilIds){const unsigned a=s.slot[k];Need(Bits(j[a],s.Jfull[k])&&Bits(p0[a],s.initialP0[k])&&std::isfinite(q[a]),"Endpoint J, P0 or pressure changed");s.core[k]={pos[a],velrhop[a],sigma[a],kappa[a],p0[a],q[a],j[a]};s.q[k]=q[a];}
  s.endpointRound++;s.roundWritten=false;s.endpoint=true;s.endpointCalls++;
}
// Calls occur in the existing independent receiver loop. Each native ID has one
// writer. Errors are latched per ID and thrown only after the OMP region.
inline void Row(unsigned id,bool drained,double diagonal,double residual,double theta,float actualQ){
  State& s=state;if(!s.endpoint||!s.pending||s.prepared||!IsSoil(id)){s.unexpectedRows.fetch_add(1);return;}
  unsigned error=s.seen[id]?1u:0u;
  if(!std::isfinite(theta)||!std::isfinite(actualQ))error=2;
  if(!drained&&(!std::isfinite(diagonal)||diagonal<=0.||!std::isfinite(residual)))error=3;
  s.seen[id]++;s.rowError[id]=error;s.drained[id]=unsigned(drained);s.thetaEndpoint[id]=theta;s.q[id]=actualQ;s.S[id]=drained?0.:diagonal;s.R[id]=drained?0.:residual;
}
inline void PrepareFinal(const void* owner,unsigned np,const unsigned* id,const typecode* code,const tdouble3* pos,const tfloat4* velrhop,
  const tsymatrix3d* sigma,const float* kappa,const float* p0,const float* q,const double* j){
  State& s=state;Need(s.owner==owner&&s.endpoint&&s.pending&&!s.unexpectedRows.load(),"Unexpected endpoint pressure row");Map(np,id,code);
  // Validate every row and committed field before writing any pressure/history.
  for(unsigned k:s.soilIds){const unsigned a=s.slot[k];const Core& c=s.core[k];
    if(s.seen[k]!=1||s.rowError[k])throw std::runtime_error("Endpoint row invalid native_id="+std::to_string(k)+" code="+std::to_string(s.rowError[k]));
    Need(Bits(pos[a],c.pos)&&Bits(velrhop[a],c.velrhop)&&Bits(sigma[a],c.sigma)&&Bits(kappa[a],c.kappa)&&Bits(p0[a],c.p0)&&Bits(j[a],c.j)&&Bits(q[a],c.q),"Extra pressure force advanced a committed soil field");
    s.coreFieldChecks+=7;s.raw[k]=float(SolveBeta0(bool(s.drained[k]),double(s.q[k]),s.S[k],s.R[k]));
  }
  s.prepared=true;
}
inline void WriteFinal(unsigned np,unsigned npb,const unsigned* id,const typecode* code,float* p){
  State& s=state;Need(s.endpoint&&s.pending&&s.prepared&&!s.roundWritten&&(s.endpointRound==1||s.endpointRound==2),"P2 pressure write lifecycle invalid");
  for(unsigned a=npb;a<np;a++)if(CODE_IsFluid(code[a])){Need(IsSoil(id[a]),"Final pressure owner invalid");p[a]=s.raw[id[a]];}
  s.roundWritten=true;s.endpointWrites++;
}
inline unsigned EndpointPhase(){const State& s=state;Need(s.endpoint&&s.pending&&(s.endpointRound==1||s.endpointRound==2),"P2 timestep is not inside an endpoint");return s.endpointRound+1;}
template<class Drained> inline void ValidateFirstEndpoint(const void* owner,unsigned np,const unsigned* id,const typecode* code,
  const float* p,const float* p0,const double* j,Drained drained){
  State& s=state;Need(s.owner==owner&&s.pending&&s.temporary&&s.prepared&&s.roundWritten&&s.endpointRound==1&&!s.firstValidated&&!s.secondStarting
    &&s.endpointWrites==2*s.commits+1&&!s.unexpectedRows.load(),"P2 first endpoint seal lifecycle/rows invalid");Map(np,id,code);
  Need(s.coreFieldChecks==7ull*s.soilCount*(2*s.commits+1)&&s.hgSnapshotChecks==2ull*s.soilCount*(2*s.commits+1),"P2 first readonly checks were skipped");
  for(unsigned k:s.soilIds){const unsigned a=s.slot[k];s.commitDrained[k]=unsigned(drained(a));
    Need(std::isfinite(p[a])&&Bits(j[a],s.Jfull[k])&&Bits(p0[a],s.initialP0[k]),"P2 provisional BC changed J/P0 or made p nonfinite");
    Need(s.commitDrained[k]?Bits(p[a],0.f):Bits(p[a],s.raw[k]),"P2 provisional pressure is neither exact first raw nor true-Dirichlet +0");}
  // First actual pressure is read directly after successful BC validation, not reconstructed.
  for(unsigned k:s.soilIds){const unsigned a=s.slot[k];FirstEndpointRecord r;
    r.pn=s.pn[k];r.previous=s.previousUsed[k];r.half=s.half[k];r.q=s.q[k];r.raw=s.raw[k];r.actualBC=p[a];r.priorFinalP=s.finalP[k];
    r.predicted=s.predicted[k];r.S=s.S[k];r.R=s.R[k];r.Jn=s.Jn[k];r.Jhalf=s.Jhalf[k];r.Jfull=s.Jfull[k];r.thetaH=s.thetaH[k];r.thetaEndpoint=s.thetaEndpoint[k];
    r.sourceDrained=s.sourceDrained[k];r.drained=s.drained[k];r.commitDrained=s.commitDrained[k];s.firstRows[k]=r;}
  s.firstValidated=true;s.firstValidations++;s.endpoint=false; // Keep temporary/prepared and original pn/previous intact.
}
inline void SetCommitDrained(unsigned id,bool drained){Need(IsSoil(id),"Commit drainage owner invalid");state.commitDrained[id]=unsigned(drained);}
inline void Commit(const void* owner,unsigned np,const unsigned* id,const typecode* code,const float* p,const float* p0,const double* j){
  State& s=state;Need(s.owner==owner&&s.pending&&s.prepared&&!s.temporary&&!s.endpoint&&s.firstValidated&&s.endpointRound==2&&s.roundWritten
    &&s.endpointWrites==2*(s.commits+1)&&s.firstValidations==s.commits+1&&s.secondStarts==s.commits+1,"P2 final history commit lifecycle invalid");Map(np,id,code);
  Need(s.coreFieldChecks==14ull*s.soilCount*(s.commits+1)&&s.hgSnapshotChecks==4ull*s.soilCount*(s.commits+1),"P2 readonly round checks were skipped");
  for(unsigned k:s.soilIds){const unsigned a=s.slot[k];Need(std::isfinite(p[a])&&Bits(j[a],s.Jfull[k])&&Bits(p0[a],s.initialP0[k]),"Final BC changed J/P0 or made p nonfinite");Need(s.commitDrained[k]?Bits(p[a],0.f):Bits(p[a],s.raw[k]),"Final pressure differs from exact raw row or true-Dirichlet +0");}
  for(unsigned k:s.soilIds){s.finalP[k]=p[s.slot[k]];s.previous[k]=s.pn[k];}s.lastEnd=s.sourceTime+s.dt;s.commits++;s.pending=false;
}
// Read-only endpoint HG adapter. The original two mechanical force/history
// transitions are untouched. Same arithmetic/conversion as frozen AddHistory;
// GetHistory/GetRate are public const accessors, not an HG phase transition.
template<class HG> inline std::vector<double> HgStats(const HG& hg){
  const auto& x=hg.GetStats();return {double(x.forcecalls),double(x.predictorupdates),double(x.correctorupdates),double(x.ratecalls),double(x.predictorrates),double(x.endpointrates),double(x.firstpairs),double(x.minpairs),double(x.maxpairs),x.maxnetforce,x.maxactualnetforce,x.maxnetrate,x.maxrelativeforce,x.maxrelativerate,x.maxhistory,x.maxcondition,x.maxpoweridentityerror,x.maxskew,x.spinbound,x.maxtauratio,x.mintau,x.maxlambda,double(x.ratecalculations),double(x.ratecachehits)};
}
template<class HG> inline std::vector<double> HgRateInfo(const HG& hg){
  const auto& x=hg.GetRateInfo();return {x.netx,x.netz,x.condition,x.skew,x.form,x.lambda,x.tau,x.ratepower,x.workerror,x.rmax,x.sumrate,x.meandxx,x.rmsdxx,x.meandiv,x.rmsdiv};
}
template<class HG> inline void CaptureHG(const HG* hg){
  State& s=state;s.hgStats.clear();s.hgRateInfo.clear();if(!hg)return;Need(hg->GetCount()==s.soilCount,"HG native count differs");s.hgStats=HgStats(*hg);s.hgRateInfo=HgRateInfo(*hg);
  for(unsigned k:s.soilIds)s.hg[k]={hg->GetHistory(k),hg->GetRate(k)};
}
template<class HG> inline void CheckHG(const HG* hg){
  State& s=state;if(!hg){Need(s.hgStats.empty()&&s.hgRateInfo.empty(),"HG presence changed");return;}
  const auto after=HgStats(*hg);Need(after.size()==s.hgStats.size(),"HG stats layout changed");
  for(size_t a=0;a<after.size();a++)Need(Bits(after[a],s.hgStats[a]),"Endpoint mutated HG statistics");
  const auto rateAfter=HgRateInfo(*hg);Need(rateAfter.size()==s.hgRateInfo.size(),"HG rate-info layout changed");
  for(size_t a=0;a<rateAfter.size();a++)Need(Bits(rateAfter[a],s.hgRateInfo[a]),"Endpoint mutated HG rate-info field");
  for(unsigned k:s.soilIds){const auto h=hg->GetHistory(k),r=hg->GetRate(k);Need(Bits(h,s.hg[k].history)&&Bits(r,s.hg[k].rate),"Endpoint mutated HG history/rate");s.hgSnapshotChecks+=2;}
}
template<class HG> inline void AddReadonlyHG(const HG* hg,unsigned np,unsigned npb,const unsigned* id,const typecode* code,
  tfloat3* ace,const double* j,double mass,double rhopZero,double waterRho){
  if(!hg)return;State& s=state;Need(s.endpoint&&j&&mass>0.&&rhopZero>0.,"Readonly single-J HG endpoint invalid");unsigned count=0;
  for(unsigned a=npb;a<np;a++)if(CODE_IsNormal(code[a])&&CODE_IsFluid(code[a])){
    Need(IsSoil(id[a]),"Readonly HG owner invalid");const auto h=hg->GetHistory(id[a]);
    const double actualMass=(mass/rhopZero)*(rhopZero-waterRho+waterRho*j[a]);
    Need(std::isfinite(j[a])&&j[a]>0.&&std::isfinite(actualMass)&&actualMass>0.&&std::isfinite(h.x)&&std::isfinite(h.z),"Readonly HG state invalid");
    const double ax=ace[a].x,az=ace[a].z,scale=mass/actualMass;
    ace[a].x=float(ax+scale*h.x);ace[a].z=float(az+scale*h.z);count++;
  }
  Need(count==s.soilCount,"Readonly HG soil set changed");
}
template<class HG> inline void SecondEndpoint(const void* owner,unsigned np,const unsigned* id,const typecode* code,
  const tdouble3* pos,const tfloat4* velrhop,const tsymatrix3d* sigma,const float* kappa,const float* p0,const float* q,const double* j,
  double time,unsigned long long step,double dt,const HG* hg){
  State& s=state;Need(s.owner==owner&&s.pending&&s.temporary&&!s.endpoint&&s.prepared&&s.roundWritten&&s.firstValidated&&s.endpointRound==1&&!s.secondStarting
    &&s.firstValidations==s.commits+1&&s.secondStarts==s.commits&&!s.unexpectedRows.load(),"P2 second endpoint transition invalid");Map(np,id,code);
  for(unsigned k:s.soilIds){const unsigned a=s.slot[k];Need(Bits(q[a],s.firstRows[k].actualBC)&&Bits(j[a],s.firstRows[k].Jfull)&&Bits(p0[a],s.initialP0[k]),"P2 provisional p1/J/P0 changed before second snapshot");}
  // All first errors were observed and all first records copied above. Only now reset per-round rows.
  std::fill(s.seen.begin(),s.seen.end(),0);std::fill(s.rowError.begin(),s.rowError.end(),0);std::fill(s.drained.begin(),s.drained.end(),0);std::fill(s.commitDrained.begin(),s.commitDrained.end(),0);
  s.prepared=false;s.roundWritten=false;s.secondStarting=true;
  try{Endpoint(owner,np,id,code,pos,velrhop,sigma,kappa,p0,q,j,time,step,dt);CaptureHG(hg);s.secondStarts++;s.secondStarting=false;}
  catch(...){s.secondStarting=false;throw;} // Preserve first failure; never retry or rotate history.
}
inline void Saved(const void* owner,unsigned part,double time,unsigned long long savedstep,unsigned np,const unsigned* id,const typecode* code,const float* p,const double* j){
  State& s=state;Need(s.ready&&s.owner==owner&&!s.pending&&!s.endpoint&&Bits(time,s.lastEnd)&&(s.commits?savedstep+1==s.initialStep+s.commits:savedstep==s.initialStep),"P2 genuine saved clock/history differs");Map(np,id,code);
  const auto emit=[&](unsigned k,unsigned round,const FirstEndpointRecord& r){
    *s.csv<<part<<','<<round<<','<<k<<','<<s.sourceStep<<','<<(s.initialStep+s.commits)<<','<<s.sourceTime<<','<<time<<','<<s.dt<<','<<r.pn<<','<<r.previous<<','<<r.predicted<<','<<r.half<<','<<r.q<<','<<r.S<<','<<r.R<<','<<r.raw<<','<<r.actualBC<<','<<r.priorFinalP<<','<<r.thetaH<<','<<r.thetaEndpoint<<','<<r.Jn<<','<<r.Jhalf<<','<<r.Jfull<<','<<r.sourceDrained<<','<<r.drained<<','<<r.commitDrained<<','<<unsigned(s.firstValidated)<<','<<s.commits<<','<<s.endpointCalls<<','<<s.endpointWrites<<','<<s.coreFieldChecks<<','<<s.hgSnapshotChecks<<'\n';};
  for(unsigned k:s.soilIds){const unsigned a=s.slot[k];Need(Bits(p[a],s.finalP[k])&&Bits(j[a],s.Jfull[k]),"P2 saved field changed after commit");
    FirstEndpointRecord r;r.pn=s.pn[k];r.previous=s.previousUsed[k];r.half=s.half[k];r.q=s.q[k];r.raw=s.raw[k];r.actualBC=s.finalP[k];
    r.priorFinalP=(s.commits?s.firstRows[k].priorFinalP:s.finalP[k]);r.predicted=s.predicted[k];r.S=s.S[k];r.R=s.R[k];r.Jn=s.Jn[k];r.Jhalf=s.Jhalf[k];r.Jfull=s.Jfull[k];r.thetaH=s.thetaH[k];r.thetaEndpoint=s.thetaEndpoint[k];r.sourceDrained=s.sourceDrained[k];r.drained=s.drained[k];r.commitDrained=s.commitDrained[k];
    if(s.commits){Need(s.firstValidated&&s.endpointRound==2&&Bits(s.q[k],s.firstRows[k].actualBC),"P2 actual second q is not validated p1");emit(k,1,s.firstRows[k]);emit(k,2,r);}else emit(k,0,r);}
  s.csv->flush();Need(bool(*s.csv),"P2 pressure sidecar write failed");
}
inline void Finish(const void* owner,unsigned long long step,double time){
  State& s=state;Need(s.owner==owner&&s.ready&&!s.pending&&!s.endpoint&&step==s.initialStep+s.commits&&Bits(time,s.lastEnd),"P2 Finish clock/history differs");
  Need(s.preCalls==s.commits&&s.corCalls==s.commits&&s.jCalls==s.commits&&s.endpointCalls==2*s.commits&&s.endpointWrites==2*s.commits
    &&s.firstValidations==s.commits&&s.secondStarts==s.commits,"P2 missing or duplicate lifecycle round");
  Need(s.coreFieldChecks==14ull*s.soilCount*s.commits&&s.hgSnapshotChecks==4ull*s.soilCount*s.commits,"P2 readonly check totals differ");
  const std::string path=s.directory+"UplTpiP2CpuR1.summary.json";Need(!std::ifstream(path).good(),"P2 summary already exists");std::ofstream out(path);Need(bool(out),"P2 summary open failed");
  out<<std::setprecision(17)<<"{\"stage\":\"upl_tpi_p2_cpu_r1\",\"completed\":true,\"scheme\":\""<<Name()<<"\",\"alpha\":0.5,\"beta\":0,\"endpoint_defects_per_step\":2,\"commits\":"<<s.commits<<",\"endpoint_calls\":"<<s.endpointCalls<<",\"endpoint_writes\":"<<s.endpointWrites<<",\"first_validations\":"<<s.firstValidations<<",\"second_starts\":"<<s.secondStarts<<",\"core_field_bit_checks\":"<<s.coreFieldChecks<<",\"HG_readonly_snapshot_checks\":"<<s.hgSnapshotChecks<<",\"actual_end\":"<<time<<",\"history_cold_start\":true,\"full_restart_supported\":false,\"PorePressRate_is_second_endpoint_scaled_residual_not_actual_dpdt\":true,\"theta_endpoint_is_not_J_integration_theta\":true,\"first_finalP_field_is_prior_commit_not_p1\":true,\"scalar_fixture_is_not_spatial_kernel_proof\":true,\"paper_literal_LF\":false,\"second_order_claimed\":false,\"true_implicit_solution\":false,\"physical_acceptance\":false}\n";
  out.flush();Need(bool(out),"P2 summary write failed");
}
} // namespace upl_tpi_cpu_r1
