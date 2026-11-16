// Private reconstructed-C04 XYZ GPU Symplectic TPI-neighbour prediction/one leading-LP
// correction variant. It is not literal paper LF, implicit, or second order.
#ifndef UPL_TPI_CRYER_GPU_R1_H
#define UPL_TPI_CRYER_GPU_R1_H
#include "DualSphDef.h"
#include <cuda_runtime.h>
#include <cstdint>
#include <string>

class JSphHourglassGpu;
namespace upl_tpi_cryer_gpu_r1 {
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
void PrepareDevice(View v,DeviceState d);
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
void PrepareFinal(const void* owner,View v,const JSphHourglassGpu* hg);
void WriteFinal(View v);
void Commit(const void* owner,View v,bool drain,unsigned loadmode);
void AbortEndpoint() noexcept;
void Saved(const void* owner,unsigned part,double time,unsigned long long savedstep,View v);
void Finish(const void* owner,unsigned long long completed,double time);
void FreeOwner(const void* owner) noexcept;
}

#ifndef __CUDACC__
#define UPL_TPI_CRYER_GPU_OWNER static_cast<JSphGpu*>(this)
#define UPL_TPI_CRYER_GPU_VIEW upl_tpi_cryer_gpu_r1::View{Np,Npb,Idpg,FSTypeg,Codeg,Posxyg,Poszg,Velrhopg,Sigmag,Kplasticg,PorePress0g,PorePressg,PoroJg,PoroThetag}
#endif

#ifdef UPL_TPI_CRYER_GPU_R1_IMPLEMENTATION
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
namespace upl_tpi_cryer_gpu_r1 {
static void Need(bool q,const char* s){if(!q)throw std::runtime_error(s);}
void Require(bool q,const char* s){Need(q,s);}
static void Cuda(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
template<class T> static bool Bits(const T& a,const T& b){return !std::memcmp(&a,&b,sizeof(T));}
static unsigned Scheme(){static const unsigned s=[](){const char* p=std::getenv("UPL_TPI_GPU_R1");
  if(!p||!*p||!std::strcmp(p,"A"))return 0u;if(!std::strcmp(p,"B"))return 1u;
  Need(!std::strcmp(p,"C"),"UPL_TPI_GPU_R1 must be absent or A/B/C");return 2u;}();return s;}
bool Enabled(){return Scheme()!=0;}
static double Alpha(){return Scheme()==1?.5:0.;}
static const char* Name(){return Scheme()==1?"B_TPI_alpha_0p5_beta0":"C_PPE_t_alpha0_beta0";}
struct State {
  const void* owner=nullptr; bool ready=false,pending=false,endpoint=false,prepared=false;
  DeviceState d={}; std::vector<void*> allocations;
  Observation* collected=nullptr;
  unsigned long long commits=0,pre=0,cor=0,j=0,endpointCalls=0,coreChecks=0,hgChecks=0,sourceStep=0;
  double sourceTime=0,lastEnd=0,dt=0; std::string directory;
  std::ofstream* csv=nullptr;
  ~State(){delete csv;} // Host cleanup ONLY. CUDA is freed before JSphGpu::cudaDeviceReset.
};
static State state;
bool EndpointActive(){return state.endpoint;}
template<class T> static T* Take(unsigned n){T* p=nullptr;Cuda(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*n));
  try{state.allocations.push_back(p);}catch(...){cudaFree(p);throw;}
  Cuda(cudaMemset(p,0,sizeof(T)*n));return p;}
static void HostRoleFixtures(){
  Need(OwnerRole(0,8,37181,true,false,true,false)&&OwnerRole(8,8,37181,true,false,false,true)
    &&OwnerRole(0,8,37181,false,true,true,false)&&OwnerRole(8,8,37181,false,true,false,true)
    &&!OwnerRole(0,8,37181,false,true,false,true)&&!OwnerRole(8,8,37181,false,true,true,false)
    &&!OwnerRole(0,8,37181,false,false,true,false)&&!OwnerRole(8,8,37181,false,false,false,true),
    "Private normal/periodic dual-owner role fixtures failed");
}
static void Check(){const Error e=GetError(state.d);if(e.bits)throw std::runtime_error(
  "Private GPU TPI rejected native_id="+std::to_string(e.firstId)+" bits="+std::to_string(e.bits));}
static void MapCheck(View v){ResetError(state.d);Map(v,state.d);Check();}
void FreeOwner(const void* owner) noexcept {
  State& s=state;if(s.owner!=owner||!s.owner)return;
  // No HG dereference: the derived destructor may already have deleted it.
  try{PublishEndpoint(DeviceState{},nullptr,false);}catch(...){}
  for(void* p:s.allocations)if(p)cudaFree(p);
  s.allocations.clear();s.d=DeviceState{};s.collected=nullptr;
  delete s.csv;s.csv=nullptr;s.owner=nullptr;s.ready=s.pending=s.endpoint=s.prepared=false;
}
void Init(const void* owner,const std::string& directory,View v,double time,unsigned long long step,double dt){
  State& s=state;Need(Enabled()&&!s.owner&&owner&&time==0.&&step==0&&dt==0.00000095367431640625,
    "C04 GPU P3 requires a fresh 2^-20 fixed-dt owner");
  HostRoleFixtures(); // Pure shared-predicate fixtures; not an additional GPU/solver phase.
  s.owner=owner; // Set before allocations, so the original destructor cleans partial initialization.
  s.directory=directory;s.sourceTime=s.lastEnd=time;s.sourceStep=step;s.dt=dt;
  Need(v.np==37181&&v.npb==8,"C04 GPU P3 requires the complete native body and remote fixed set");
  s.d.total=37181;s.d.fixed=8;s.d.slots=Take<unsigned>(37181);s.d.seen=Take<unsigned>(37181);
  s.d.previous=Take<float>(37181);s.d.rows=Take<Observation>(37181);s.d.core=Take<Core>(37181);s.d.error=Take<Error>(1);
  s.collected=Take<Observation>(37173);MapCheck(v);Initialize(v,s.d);Check();
  const std::string policy=directory+"UplTpiCryerGpuR1.policy.json",csv=directory+"UplTpiCryerGpuR1.csv";
  Need(!std::ifstream(policy).good()&&!std::ifstream(csv).good(),"GPU TPI sidecar exists");
  s.csv=new std::ofstream(csv);Need(bool(*s.csv),"GPU TPI sidecar open failed");
  *s.csv<<std::setprecision(17)<<"part,native_id,source_step_zero_based,completed_step,source_time_s,actual_save_time_s,dt_s,pn_Pa,previous_Pa,prediction_double_Pa,half_actual_float_Pa,endpoint_q_actual_float_Pa,S_1_per_m_s,Rgamma_Pa_per_m_s,raw_final_float_Pa,final_float_Pa,theta_half_for_J_1_per_s,theta_endpoint_1_per_s,Jn,Jhalf,Jfull,source_drained,endpoint_drained,commit_drained,commits,endpoint_calls,core_field_bit_checks,hg_snapshot_checks\n";
  std::ofstream p(policy);p<<"{\"stage\":\"upl_tpi_cryer_gpu_r1\",\"scheme\":\""<<Name()<<"\",\"alpha\":"<<Alpha()
    <<",\"beta\":0,\"M0\":true,\"native_count\":37181,\"soil_count\":37173,\"history_ID_owned\":true,\"history_cold_start\":true,\"full_restart_supported\":false,\"half_equals_endpoint_history_guess\":true,\"endpoint_source_clock_is_original_n\":true,\"paper_literal_LF\":false,\"second_order_claimed\":false,\"true_implicit_solution\":false,\"physical_acceptance\":false}\n";
  p.flush();Need(bool(p),"GPU policy write failed");s.ready=true;
}
void Begin(const void* owner,View v,const float* pn,const double2* sourcexy,float* out,double time,unsigned long long step,double dt,bool drain,unsigned loadmode){
  State& s=state;Need(s.ready&&s.owner==owner&&!s.pending&&!s.endpoint&&step==s.commits&&dt==s.dt&&Bits(time,s.lastEnd),"GPU predictor lifecycle/clock differs");
  MapCheck(v);s.sourceTime=time;s.sourceStep=step;s.prepared=false;
  BeginDevice(v,pn,sourcexy,out,s.d,drain,loadmode,Alpha());Check();s.pending=true;s.pre++;
}
void Corr(const void* owner,View v){State& s=state;Need(s.owner==owner&&s.pending&&!s.endpoint&&s.cor+1==s.pre,"GPU half capture lifecycle differs");
  MapCheck(v);CorrDevice(v,s.d);Check();s.cor++;}
void CaptureJ(const void* owner,View v){State& s=state;Need(s.owner==owner&&s.j+1==s.cor,"GPU J lifecycle differs");
  MapCheck(v);CaptureJDevice(v,s.d);Check();s.j++;}
void Guess(View v,const float* pn,bool drain,unsigned loadmode){ResetError(state.d);GuessDevice(v,pn,state.d,drain,loadmode);Check();}
void StartEndpoint(const void* owner,View v,double time,unsigned long long step,double dt,const JSphHourglassGpu* hg){
  State& s=state;Need(s.owner==owner&&s.pending&&!s.endpoint&&s.j==s.pre&&Bits(time,s.sourceTime)&&step==s.sourceStep&&dt==s.dt,
    "GPU endpoint lifecycle/clock differs");Need(!hg,"C04 GPU P3 requires HG0 without an HG object");
  MapCheck(v);SnapshotCoreDevice(v,s.d);Check();
  PublishEndpoint(s.d,v.id,true);s.endpoint=true;s.endpointCalls++;
}
void PrepareFinal(const void* owner,View v,const JSphHourglassGpu* hg){
  State& s=state;Need(s.owner==owner&&s.endpoint&&s.pending&&!s.prepared&&!hg,"C04 GPU HG0 final preparation lifecycle differs");
  PrepareDevice(v,s.d);Check();s.coreChecks+=7ull*37173;s.prepared=true;
}
void WriteFinal(View v){Need(state.endpoint&&state.prepared,"GPU pressure was not completely prepared");WriteDevice(v,state.d);Check();
  PublishEndpoint(DeviceState{},nullptr,false);state.endpoint=false;}
void Commit(const void* owner,View v,bool drain,unsigned loadmode){State& s=state;Need(s.owner==owner&&s.pending&&s.prepared&&!s.endpoint,"GPU commit lifecycle differs");
  MapCheck(v);ValidateCommitDevice(v,s.d,drain,loadmode);Check();CommitDevice(v,s.d);Check();
  s.lastEnd=s.sourceTime+s.dt;s.commits++;s.pending=false;}
void AbortEndpoint() noexcept {try{PublishEndpoint(DeviceState{},nullptr,false);}catch(...){}state.endpoint=false;}
void Saved(const void* owner,unsigned part,double time,unsigned long long savedstep,View v){State& s=state;
  Need(s.ready&&s.owner==owner&&!s.pending&&Bits(time,s.lastEnd)&&(s.commits?savedstep+1==s.commits:savedstep==0),"GPU actual saved clock/history differs");
  MapCheck(v);CollectDevice(v,s.d,s.collected);Check();std::vector<Observation> rows(37173);
  Cuda(cudaMemcpy(rows.data(),s.collected,sizeof(Observation)*37173,cudaMemcpyDeviceToHost));
  for(unsigned n=0;n<37173;n++){const auto& r=rows[n];*s.csv<<part<<','<<8+n<<','<<s.sourceStep<<','<<s.commits<<','<<s.sourceTime<<','<<time<<','<<s.dt<<','<<r.pn<<','<<r.previous<<','<<r.prediction<<','<<r.half<<','<<r.q<<','<<r.S<<','<<r.R<<','<<r.raw<<','<<r.finalP<<','<<r.thetaH<<','<<r.thetaEnd<<','<<r.Jn<<','<<r.Jhalf<<','<<r.Jfull<<','<<r.sourceDrained<<','<<r.drained<<','<<r.commitDrained<<','<<s.commits<<','<<s.endpointCalls<<','<<s.coreChecks<<','<<s.hgChecks<<'\n';}
  s.csv->flush();Need(bool(*s.csv),"GPU saved sidecar write failed");
}
void Finish(const void* owner,unsigned long long completed,double time){State& s=state;
  Need(s.ready&&s.owner==owner&&!s.pending&&completed==s.commits&&Bits(time,s.lastEnd)
    &&s.pre==s.commits&&s.cor==s.commits&&s.j==s.commits&&s.endpointCalls==s.commits
    &&s.coreChecks==7ull*37173*s.commits&&s.hgChecks==0,"GPU complete lifecycle differs");
  const std::string path=s.directory+"UplTpiCryerGpuR1.summary.json";Need(!std::ifstream(path).good(),"GPU summary already exists");
  std::ofstream f(path);f<<std::setprecision(17)<<"{\"stage\":\"upl_tpi_cryer_gpu_r1\",\"completed\":true,\"scheme\":\""<<Name()<<"\",\"alpha\":"<<Alpha()
    <<",\"beta\":0,\"commits\":"<<s.commits<<",\"endpoint_calls\":"<<s.endpointCalls<<",\"core_field_bit_checks\":"<<s.coreChecks<<",\"HG_readonly_snapshot_checks\":"<<s.hgChecks<<",\"actual_end\":"<<time
    <<",\"history_cold_start\":true,\"full_restart_supported\":false,\"theta_endpoint_is_not_J_integration_theta\":true,\"PorePressRate_is_legacy_scaled_residual_not_dpdt\":true,\"paper_literal_LF\":false,\"second_order_claimed\":false,\"true_implicit_solution\":false,\"physical_acceptance\":false}\n";
  f.flush();Need(bool(f),"GPU summary write failed");
}
}
#endif
#endif
