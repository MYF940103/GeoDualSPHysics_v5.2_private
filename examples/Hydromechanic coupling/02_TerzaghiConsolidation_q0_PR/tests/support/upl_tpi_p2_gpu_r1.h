// Private frozen-C02 GPU Symplectic TPI-neighbour prediction/one leading-LP
// correction variant. It is not literal paper LF, implicit, or second order.
#ifndef UPL_TPI_GPU_R1_H
#define UPL_TPI_GPU_R1_H
#include "DualSphDef.h"
#include <cuda_runtime.h>
#include <cstdint>
#include <string>

class JSphHourglassGpu;
namespace upl_tpi_gpu_r1 {
struct View {
  unsigned np,npb; const unsigned *id,*fstype; const typecode* code;
  double2* xy; double* z; float4* vr; tsymatrix3d* sigma;
  float *kappa,*p0,*p; double *J,*theta;
};
struct Core {
  double2 xy; double z; float4 vr; tsymatrix3d sigma;
  float kappa,p0,q; double J;
};
struct Observation {
  float pn,previous,half,q,raw,finalP;
  double prediction,S,R,thetaH,thetaEnd,Jn,Jhalf,Jfull;
  unsigned sourceDrained,drained,commitDrained;
};
struct Error { unsigned bits,firstId; };
// Shared role predicate; the eight host boolean fixtures below are not claimed
// as a GPU execution/memcheck result. The real Map kernel calls this same law.
__host__ __device__ inline bool OwnerRole(unsigned id,unsigned fixed,unsigned total,
  bool normal,bool periodic,bool isfixed,bool isfluid){
  return id<total && (normal||periodic) && (id<fixed?isfixed:isfluid);
}
struct DeviceState {
  unsigned total,fixed; unsigned *slots,*seen; float* previous;
  Observation* rows; Core* core; Error* error;
  double2 *hgHistory,*hgRate;
};
// Defined only in the private .cuh appended to the original CUDA TU.
void ResetError(DeviceState d);
Error GetError(DeviceState d);
void Map(View v,DeviceState d);
void Initialize(View v,DeviceState d);
void BeginDevice(View v,const float* pn,const double2* sourcexy,float* out,
  DeviceState d,bool drain,unsigned loadmode,double alpha);
void CorrDevice(View v,DeviceState d);
void CaptureJDevice(View v,DeviceState d);
void GuessDevice(View v,const float* pn,DeviceState d,bool drain,unsigned loadmode);
void SnapshotCoreDevice(View v,DeviceState d);
void PrepareDevice(View v,DeviceState d,const double2* h,const double2* rate);
void WriteDevice(View v,DeviceState d);
void ValidateCommitDevice(View v,DeviceState d,bool drain,unsigned loadmode);
void CommitDevice(View v,DeviceState d);
void CollectDevice(View v,DeviceState d,Observation* output);
void PublishEndpoint(DeviceState d,const unsigned* id,bool active);
bool CaptureEndpointHost();
#ifdef __CUDACC__
__device__ void CaptureRow(unsigned slot,bool drained,double diagonal,double residual,
  double theta,float actualQ);
#endif
bool Enabled();
bool EndpointActive();
void Require(bool okay,const char* message);
void Init(const void* owner,const std::string& directory,View v,double time,
  unsigned long long step,double dt);
void Begin(const void* owner,View v,const float* pn,const double2* sourcexy,float* out,
  double time,unsigned long long step,double dt,bool drain,unsigned loadmode);
void Corr(const void* owner,View v);
void CaptureJ(const void* owner,View v);
void Guess(View v,const float* pn,bool drain,unsigned loadmode);
void StartEndpoint(const void* owner,View v,double time,unsigned long long step,
  double dt,const JSphHourglassGpu* hg);
void AddReadonlyHG(View v,float3* ace,const JSphHourglassGpu* hg,double mass,
  double rho0,double rhow);
void PrepareFinal(const void* owner,View v,const JSphHourglassGpu* hg);
void WriteFinal(View v);
void Commit(const void* owner,View v,bool drain,unsigned loadmode);
void AbortEndpoint() noexcept;
void Saved(const void* owner,unsigned part,double time,unsigned long long savedstep,View v);
void Finish(const void* owner,unsigned long long completed,double time);
void FreeOwner(const void* owner) noexcept;
}

#ifndef __CUDACC__
#define UPL_TPI_GPU_OWNER static_cast<JSphGpu*>(this)
#define UPL_TPI_GPU_VIEW upl_tpi_gpu_r1::View{Np,Npb,Idpg,FSTypeg,Codeg,Posxyg,Poszg,Velrhopg,Sigmag,Kplasticg,PorePress0g,PorePressg,PoroJg,PoroThetag}
#endif

// P2_HOST_API_R1_BEGIN
#ifndef __CUDACC__
namespace upl_tpi_gpu_r1 {
void ValidateFirstEndpoint(const void* owner,View v,bool drain,unsigned loadmode);
void SecondEndpoint(const void* owner,View v,double time,unsigned long long step,
  double dt,const JSphHourglassGpu* hg);
unsigned EndpointPhase();
}
#endif
// P2_HOST_API_R1_END
#ifdef UPL_TPI_GPU_R1_IMPLEMENTATION
#include "upl_tpi_m0_dt_r2.h"
#include "JSphHourglassGpu.h"
#include <climits>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
namespace upl_tpi_gpu_r1 {
static void Need(bool q,const char* s){if(!q)throw std::runtime_error(s);}
void Require(bool q,const char* s){Need(q,s);}
static void Cuda(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
template<class T> static bool Bits(const T& a,const T& b){return !std::memcmp(&a,&b,sizeof(T));}
static unsigned Scheme(){static const unsigned s=[](){const char* p=std::getenv("UPL_TPI_GPU_R1");
  if(!p||!*p||!std::strcmp(p,"A"))return 0u;
  Need(!std::strcmp(p,"B"),"GPU P2 supports only default A or admitted B");
  const char* q=std::getenv("UPL_TPI_P2_ROWS_R1");Need(q&&!std::strcmp(q,"2"),"GPU P2 B requires exact UPL_TPI_P2_ROWS_R1=2");return 1u;}();return s;}
bool Enabled(){return Scheme()!=0;}
static double Alpha(){return Scheme()==1?.5:0.;}
static const char* Name(){return "B_TPI_alpha_0p5_beta0_two_complete_endpoint_defects";}
struct State {
  const void* owner=nullptr; bool ready=false,pending=false,endpoint=false,prepared=false;
  DeviceState d={}; std::vector<void*> allocations;
  unsigned *hgSlots=nullptr,*hgError=nullptr; cuhg::StReduce *hgPartial=nullptr,*hgResult=nullptr;
  Observation* collected=nullptr; Observation* firstRows=nullptr;
  unsigned endpointRound=0;bool firstValidated=false,secondTransitionReady=false,roundWritten=false;
  unsigned long long firstValidations=0,firstRowCopies=0,initialFirstRowCopies=0,secondTransitions=0,saves=0,endpointWrites=0;
  unsigned long long commits=0,pre=0,cor=0,j=0,endpointCalls=0,coreChecks=0,hgChecks=0,sourceStep=0;
  double sourceTime=0,lastEnd=0,dt=0; std::string directory;
  std::vector<double> stats,rateInfo; std::ofstream* csv=nullptr;std::ofstream* csvFirst=nullptr;
  ~State(){delete csv;delete csvFirst;} // Host cleanup ONLY. CUDA is freed before JSphGpu::cudaDeviceReset.
};
static State state;
bool EndpointActive(){return state.endpoint;}
unsigned EndpointPhase(){Need(state.endpoint&&(state.endpointRound==1||state.endpointRound==2),"GPU P2 endpoint phase queried outside a real force");return state.endpointRound+1;}
template<class T> static T* Take(unsigned n){T* p=nullptr;Cuda(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*n));
  try{state.allocations.push_back(p);}catch(...){cudaFree(p);throw;}
  Cuda(cudaMemset(p,0,sizeof(T)*n));return p;}
static void HostRoleFixtures(){
  Need(OwnerRole(0,1,2,true,false,true,false)&&OwnerRole(1,1,2,true,false,false,true)
    &&OwnerRole(0,1,2,false,true,true,false)&&OwnerRole(1,1,2,false,true,false,true)
    &&!OwnerRole(0,1,2,false,true,false,true)&&!OwnerRole(1,1,2,false,true,true,false)
    &&!OwnerRole(0,1,2,false,false,true,false)&&!OwnerRole(1,1,2,false,false,false,true),
    "Private normal/periodic dual-owner role fixtures failed");
}
static void Check(){const Error e=GetError(state.d);if(e.bits)throw std::runtime_error(
  "Private GPU TPI rejected native_id="+std::to_string(e.firstId)+" bits="+std::to_string(e.bits));}
static void MapCheck(View v){ResetError(state.d);Map(v,state.d);Check();}
static std::vector<double> Stats(const JSphHourglassGpu& hg){const auto& x=hg.GetStats();return {
  double(x.forcecalls),double(x.predictorupdates),double(x.correctorupdates),double(x.ratecalls),double(x.predictorrates),double(x.endpointrates),double(x.firstpairs),double(x.minpairs),double(x.maxpairs),x.maxnetforce,x.maxactualnetforce,x.maxnetrate,x.maxrelativeforce,x.maxrelativerate,x.maxhistory,x.maxcondition,x.maxpoweridentityerror,x.maxskew,x.spinbound,x.maxtauratio,x.mintau,x.maxlambda,double(x.ratecalculations),double(x.ratecachehits)};}
static std::vector<double> RateInfo(const JSphHourglassGpu& hg){const auto& x=hg.GetRateInfo();return {
  x.netx,x.netz,x.condition,x.skew,x.form,x.lambda,x.tau,x.ratepower,x.workerror,x.rmax,x.sumrate,x.meandxx,x.rmsdxx,x.meandiv,x.rmsdiv};}
void FreeOwner(const void* owner) noexcept {
  State& s=state;if(s.owner!=owner||!s.owner)return;
  // No HG dereference: the derived destructor may already have deleted it.
  try{PublishEndpoint(DeviceState{},nullptr,false);}catch(...){}
  for(void* p:s.allocations)if(p)cudaFree(p);
  s.allocations.clear();s.d=DeviceState{};s.hgSlots=s.hgError=nullptr;
  s.hgPartial=s.hgResult=nullptr;s.collected=s.firstRows=nullptr;
  delete s.csv;delete s.csvFirst;s.csv=s.csvFirst=nullptr;s.owner=nullptr;s.ready=s.pending=s.endpoint=s.prepared=false;
  s.firstValidated=s.secondTransitionReady=s.roundWritten=false;s.endpointRound=0;
}
void Init(const void* owner,const std::string& directory,View v,double time,unsigned long long step,double dt){
  State& s=state;Need(Enabled()&&!s.owner&&owner&&time==0.&&step==0&&(upl_tpi_m0_dt_r2::Enabled(Enabled())?upl_tpi_m0_dt_r2::AllowedDt(dt,.0100002288818359375):dt==6.2501430511474609e-6),
    "GPU P2 requires a fresh fixed-dt owner");
  Need(Scheme()==1&&upl_tpi_m0_dt_r2::Enabled(Enabled())&&Bits(dt,.0100002288818359375/1000.),"GPU P2 requires original-source-clock B10us with its four-phase M0 policy");
  HostRoleFixtures(); // Pure shared-predicate fixtures; not an additional GPU/solver phase.
  s.owner=owner; // Set before allocations, so the original destructor cleans partial initialization.
  s.directory=directory;s.sourceTime=s.lastEnd=time;s.sourceStep=step;s.dt=dt;
  s.d.total=1040;s.d.fixed=40;s.d.slots=Take<unsigned>(1040);s.d.seen=Take<unsigned>(1040);
  s.d.previous=Take<float>(1040);s.d.rows=Take<Observation>(1040);s.d.core=Take<Core>(1040);s.d.error=Take<Error>(1);
  s.d.hgHistory=Take<double2>(1000);s.d.hgRate=Take<double2>(1000);
  s.hgSlots=Take<unsigned>(1000);s.hgError=Take<unsigned>(1);
  s.hgPartial=Take<cuhg::StReduce>(cuhg::PartialCount(1000));s.hgResult=Take<cuhg::StReduce>(1);
  s.collected=Take<Observation>(1000);s.firstRows=Take<Observation>(1040);MapCheck(v);Initialize(v,s.d);Check();
  Cuda(cudaMemcpy(s.firstRows,s.d.rows,sizeof(Observation)*1040,cudaMemcpyDeviceToDevice));s.initialFirstRowCopies=1;
  const std::string policy=directory+"UplTpiP2GpuR1.policy.json",csv1=directory+"UplTpiP2GpuR1.round1.csv",csv2=directory+"UplTpiP2GpuR1.round2.csv";
  Need(!std::ifstream(policy).good()&&!std::ifstream(csv1).good()&&!std::ifstream(csv2).good(),"GPU P2 sidecar exists");
  s.csvFirst=new std::ofstream(csv1);s.csv=new std::ofstream(csv2);Need(bool(*s.csvFirst)&&bool(*s.csv),"GPU P2 sidecar open failed");
  const char* columns="part,native_id,source_step_zero_based,completed_step,source_time_s,actual_save_time_s,dt_s,pn_Pa,previous_Pa,prediction_double_Pa,half_actual_float_Pa,endpoint_q_actual_float_Pa,S_1_per_m_s,Rgamma_Pa_per_m_s,raw_final_float_Pa,final_field_float_Pa,theta_half_for_J_1_per_s,theta_endpoint_1_per_s,Jn,Jhalf,Jfull,source_drained,endpoint_drained,commit_drained,commits,endpoint_calls,core_field_bit_checks,hg_snapshot_checks,round,has_endpoint_observation,final_field_is_previous_step,validated_BC_value_float_Pa\n";
  *s.csvFirst<<std::setprecision(17)<<columns;*s.csv<<std::setprecision(17)<<columns;
  std::ofstream p(policy);p<<"{\"stage\":\"upl_tpi_p2_gpu_r1\",\"scheme\":\""<<Name()<<"\",\"alpha\":0.5,\"beta\":0,\"M0\":true,\"endpoint_defect_rounds\":2,\"native_count\":1040,\"soil_count\":1000,\"history_ID_owned\":true,\"history_cold_start\":true,\"full_restart_supported\":false,\"endpoint_source_clock_is_original_n\":true,\"staged_load_clock\":false,\"first_commit_rotates_history\":false,\"first_finalP_is_stale_previous_step\":true,\"first_BC_value_is_validated_rule_not_extra_native_save\":true,\"second_q_is_actual_first_BC_float\":true,\"first_rows_D2D_before_second_overwrite\":true,\"new_per_ID_D2H_in_step\":false,\"first_lap_observed\":false,\"first_legacy_rate_observed\":false,\"paper_literal_LF\":false,\"second_order_claimed\":false,\"true_implicit_solution\":false,\"physical_acceptance\":false}\n";
  p.flush();Need(bool(p),"GPU P2 policy write failed");s.ready=true;
}

void Begin(const void* owner,View v,const float* pn,const double2* sourcexy,float* out,double time,unsigned long long step,double dt,bool drain,unsigned loadmode){
  State& s=state;Need(s.ready&&s.owner==owner&&!s.pending&&!s.endpoint&&step==s.commits&&dt==s.dt&&Bits(time,s.lastEnd),"GPU predictor lifecycle/clock differs");
  Check();MapCheck(v);s.sourceTime=time;s.sourceStep=step;s.prepared=false;
  s.endpointRound=0;s.firstValidated=s.secondTransitionReady=s.roundWritten=false;
  BeginDevice(v,pn,sourcexy,out,s.d,drain,loadmode,Alpha());Check();s.pending=true;s.pre++;
}
void Corr(const void* owner,View v){State& s=state;Need(s.owner==owner&&s.pending&&!s.endpoint&&s.cor+1==s.pre,"GPU half capture lifecycle differs");
  MapCheck(v);CorrDevice(v,s.d);Check();s.cor++;}
void CaptureJ(const void* owner,View v){State& s=state;Need(s.owner==owner&&s.j+1==s.cor,"GPU J lifecycle differs");
  MapCheck(v);CaptureJDevice(v,s.d);Check();s.j++;}
void Guess(View v,const float* pn,bool drain,unsigned loadmode){ResetError(state.d);GuessDevice(v,pn,state.d,drain,loadmode);Check();}
void StartEndpoint(const void* owner,View v,double time,unsigned long long step,double dt,const JSphHourglassGpu* hg){
  State& s=state;Need(s.owner==owner&&s.pending&&!s.endpoint&&!s.prepared&&s.j==s.pre&&Bits(time,s.sourceTime)&&step==s.sourceStep&&dt==s.dt,
    "GPU P2 endpoint lifecycle/clock differs");Need(hg&&hg->GetFirstId()==40&&hg->GetCount()==1000,"GPU P2 requires original elastic HG owners");
  if(s.endpointRound==0){Need(!s.firstValidated&&s.endpointCalls==2*s.commits,"GPU P2 first round duplicated or incomplete");s.endpointRound=1;}
  else Need(s.endpointRound==2&&s.firstValidated&&s.secondTransitionReady&&s.endpointCalls==2*s.commits+1,"GPU P2 second round requires its validated transition");
  s.roundWritten=false;s.secondTransitionReady=false;Check();MapCheck(v);SnapshotCoreDevice(v,s.d);Check();s.stats=Stats(*hg);s.rateInfo=RateInfo(*hg);
  Cuda(cudaMemcpy(s.d.hgHistory,hg->GetHistoryDeviceReadonly(),sizeof(double2)*1000,cudaMemcpyDeviceToDevice));
  Cuda(cudaMemcpy(s.d.hgRate,hg->GetRateDeviceReadonly(),sizeof(double2)*1000,cudaMemcpyDeviceToDevice));
  PublishEndpoint(s.d,v.id,true);s.endpoint=true;s.endpointCalls++;
}
void AddReadonlyHG(View v,float3* ace,const JSphHourglassGpu* hg,double mass,double rho0,double rhow){
  State& s=state;Need(s.endpoint&&hg&&hg->GetFirstId()==40&&hg->GetCount()==1000,"GPU readonly HG owners differ");
  cuhg::MapNative(v.np,v.npb,40,1000,v.id,v.code,s.hgSlots,s.hgError);
  Cuda(cudaGetLastError());
  cuhg::AddHistory(1000,mass,s.hgSlots,s.hgError,hg->GetHistoryDeviceReadonly(),ace,s.hgPartial,v.J,rho0,rhow);
  Cuda(cudaGetLastError());
  cuhg::Reduce(cuhg::PartialCount(1000),s.hgPartial,s.hgResult);Cuda(cudaGetLastError());cuhg::StReduce r;
  Cuda(cudaMemcpy(&r,s.hgResult,sizeof(r),cudaMemcpyDeviceToHost));
  Need(!r.errors&&std::isfinite(r.netx)&&std::isfinite(r.netz)&&std::isfinite(r.actualx)&&std::isfinite(r.actualz)
    &&std::isfinite(r.sumforce)&&r.sumforce>=0&&std::isfinite(r.hmax),"GPU original readonly HG force validation failed");
}
void PrepareFinal(const void* owner,View v,const JSphHourglassGpu* hg){
  State& s=state;Need(s.owner==owner&&s.endpoint&&s.pending&&!s.prepared&&hg&&(s.endpointRound==1||s.endpointRound==2)
    &&(s.endpointRound==1||s.firstValidated),"GPU P2 preparation lifecycle differs");
  const auto a=Stats(*hg),r=RateInfo(*hg);Need(a.size()==24&&r.size()==15&&s.stats.size()==24&&s.rateInfo.size()==15,"HG observation layout differs");
  for(unsigned n=0;n<24;n++)Need(Bits(a[n],s.stats[n]),"GPU extra endpoint mutated HG statistics");
  for(unsigned n=0;n<15;n++)Need(Bits(r[n],s.rateInfo[n]),"GPU extra endpoint mutated HG rate info");
  PrepareDevice(v,s.d,hg->GetHistoryDeviceReadonly(),hg->GetRateDeviceReadonly());Check();
  s.coreChecks+=7000;s.hgChecks+=2000;s.prepared=true;
}
void WriteFinal(View v){State& s=state;Need(s.pending&&s.endpoint&&s.prepared&&!s.roundWritten&&(s.endpointRound==1||s.endpointRound==2)
    &&s.endpointWrites==2*s.commits+s.endpointRound-1,"GPU P2 pressure was not prepared for one actual round write");
  WriteDevice(v,s.d);Check();s.roundWritten=true;s.endpointWrites++;
  PublishEndpoint(DeviceState{},nullptr,false);s.endpoint=false;}
void ValidateFirstEndpoint(const void* owner,View v,bool drain,unsigned loadmode){State& s=state;
  Need(s.owner==owner&&s.ready&&s.pending&&s.prepared&&!s.endpoint&&s.endpointRound==1&&!s.firstValidated
    &&s.roundWritten&&s.endpointWrites==2*s.commits+1&&s.firstValidations==s.commits&&s.endpointCalls==2*s.commits+1,"GPU P2 first validation lifecycle differs");
  Check();MapCheck(v);ValidateCommitDevice(v,s.d,drain,loadmode);Check(); // Validates real p1/J/P0 but does NOT rotate history.
  Cuda(cudaMemcpy(s.firstRows,s.d.rows,sizeof(Observation)*1040,cudaMemcpyDeviceToDevice));
  s.firstValidations++;s.firstRowCopies++;s.firstValidated=true; // Observe success before a later Map resets errors.
}
void SecondEndpoint(const void* owner,View v,double time,unsigned long long step,double dt,const JSphHourglassGpu* hg){State& s=state;
  Need(s.owner==owner&&s.pending&&s.prepared&&!s.endpoint&&s.endpointRound==1&&s.firstValidated
    &&s.roundWritten&&s.endpointWrites==2*s.commits+1&&s.firstValidations==s.commits+1&&s.secondTransitions==s.commits,"GPU P2 second transition duplicated or first round invalid");
  Check();s.prepared=false;s.endpointRound=2;s.secondTransitionReady=true;
  StartEndpoint(owner,v,time,step,dt,hg);s.secondTransitions++;
}
void Commit(const void* owner,View v,bool drain,unsigned loadmode){State& s=state;Need(s.owner==owner&&s.pending&&s.prepared&&!s.endpoint
    &&s.endpointRound==2&&s.firstValidated&&s.roundWritten&&s.endpointWrites==2*(s.commits+1)&&s.secondTransitions==s.commits+1&&s.endpointCalls==2*(s.commits+1),"GPU P2 final commit requires two complete rounds");
  Check();MapCheck(v);ValidateCommitDevice(v,s.d,drain,loadmode);Check();CommitDevice(v,s.d);Check();
  s.lastEnd=s.sourceTime+s.dt;s.commits++;s.pending=false;
}
void AbortEndpoint() noexcept {try{PublishEndpoint(DeviceState{},nullptr,false);}catch(...){}state.endpoint=false;}
static void WriteObservation(std::ofstream& csv,const Observation& r,unsigned part,unsigned id,double time,unsigned round,float bc){const State& s=state;
  const bool observed=s.commits!=0;
  csv<<part<<','<<id<<','<<s.sourceStep<<','<<s.commits<<','<<s.sourceTime<<','<<time<<','<<s.dt<<','<<r.pn<<','<<r.previous<<','<<r.prediction<<','<<r.half<<','<<r.q<<','<<r.S<<','<<r.R<<','<<r.raw<<','<<r.finalP<<','<<r.thetaH<<','<<r.thetaEnd<<','<<r.Jn<<','<<r.Jhalf<<','<<r.Jfull<<','<<r.sourceDrained<<','<<r.drained<<','<<r.commitDrained<<','<<s.commits<<','<<s.endpointCalls<<','<<s.coreChecks<<','<<s.hgChecks<<','<<round<<','<<unsigned(observed)<<','<<unsigned(observed&&round==1)<<','<<bc<<'\n';
}
void Saved(const void* owner,unsigned part,double time,unsigned long long savedstep,View v){State& s=state;
  Need(s.ready&&s.owner==owner&&!s.pending&&!s.endpoint&&Bits(time,s.lastEnd)&&(s.commits?savedstep+1==s.commits:savedstep==0),"GPU P2 actual saved clock/history differs");
  Need(!s.commits||(s.endpointRound==2&&s.firstValidated&&s.firstRowCopies==s.commits&&s.secondTransitions==s.commits),"GPU P2 saved step lacks two validated rounds");
  Check();MapCheck(v);CollectDevice(v,s.d,s.collected);Check();std::vector<Observation> rows(1000),first(1040);
  Cuda(cudaMemcpy(rows.data(),s.collected,sizeof(Observation)*1000,cudaMemcpyDeviceToHost));
  Cuda(cudaMemcpy(first.data(),s.firstRows,sizeof(Observation)*1040,cudaMemcpyDeviceToHost)); // New row data leaves device only at SaveData.
  for(unsigned n=0;n<1000;n++){const auto& r=rows[n];const auto& f=first[n+40];const float p1=f.commitDrained?0.f:f.raw;
    if(s.commits){Need(Bits(r.q,p1),"GPU P2 actual second q differs from validated first BC float");
      Need(Bits(r.pn,f.pn)&&Bits(r.previous,f.previous)&&Bits(r.prediction,f.prediction)&&Bits(r.half,f.half)
        &&Bits(r.Jn,f.Jn)&&Bits(r.Jhalf,f.Jhalf)&&Bits(r.Jfull,f.Jfull)&&Bits(r.thetaH,f.thetaH)&&r.sourceDrained==f.sourceDrained,"GPU P2 source/J history changed between endpoint rounds");}
    WriteObservation(*s.csvFirst,f,part,n+40,time,1,p1);WriteObservation(*s.csv,r,part,n+40,time,2,r.finalP);
  }
  s.csvFirst->flush();s.csv->flush();Need(bool(*s.csvFirst)&&bool(*s.csv),"GPU P2 saved sidecar write failed");s.saves++;
}
void Finish(const void* owner,unsigned long long completed,double time){State& s=state;
  Need(s.ready&&s.owner==owner&&!s.pending&&!s.endpoint&&completed==s.commits&&Bits(time,s.lastEnd)
    &&s.pre==s.commits&&s.cor==s.commits&&s.j==s.commits&&s.endpointCalls==2*s.commits
    &&s.endpointWrites==2*s.commits&&s.coreChecks==14000*s.commits&&s.hgChecks==4000*s.commits&&s.firstValidations==s.commits
    &&s.firstRowCopies==s.commits&&s.initialFirstRowCopies==1&&s.secondTransitions==s.commits,"GPU P2 complete lifecycle differs");
  const std::string path=s.directory+"UplTpiP2GpuR1.summary.json";Need(!std::ifstream(path).good(),"GPU P2 summary already exists");
  std::ofstream f(path);f<<std::setprecision(17)<<"{\"stage\":\"upl_tpi_p2_gpu_r1\",\"completed\":true,\"scheme\":\""<<Name()<<"\",\"alpha\":0.5,\"beta\":0,\"endpoint_defect_rounds\":2,\"commits\":"<<s.commits
    <<",\"pre_calls\":"<<s.pre<<",\"cor_calls\":"<<s.cor<<",\"J_calls\":"<<s.j<<",\"endpoint_calls\":"<<s.endpointCalls<<",\"endpoint_writes\":"<<s.endpointWrites<<",\"first_validations\":"<<s.firstValidations<<",\"first_row_D2D_copies\":"<<s.firstRowCopies<<",\"initial_first_row_D2D_copies\":"<<s.initialFirstRowCopies<<",\"second_transitions\":"<<s.secondTransitions
    <<",\"core_field_bit_checks\":"<<s.coreChecks<<",\"HG_readonly_snapshot_checks\":"<<s.hgChecks<<",\"saved_records_per_round\":"<<1000*s.saves<<",\"actual_end\":"<<time
    <<",\"history_cold_start\":true,\"history_rotates_once_per_step\":true,\"first_finalP_is_stale_previous_step\":true,\"first_BC_value_is_validated_rule_not_extra_native_save\":true,\"first_lap_observed\":false,\"first_legacy_rate_observed\":false,\"full_restart_supported\":false,\"PorePressRate_is_last_round_scaled_residual_not_dpdt\":true,\"paper_literal_LF\":false,\"second_order_claimed\":false,\"true_implicit_solution\":false,\"physical_acceptance\":false}\n";
  f.flush();Need(bool(f),"GPU P2 summary write failed");
}
}
#endif
#endif
