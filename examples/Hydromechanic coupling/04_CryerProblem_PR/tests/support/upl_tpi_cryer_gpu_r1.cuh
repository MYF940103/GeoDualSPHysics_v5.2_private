// Included once at the END of frozen JSphGpu_ker.cu, outside namespace cusph.
// Reuses its genuine drainage predicate; no second spatial Darcy operator.
#ifndef UPL_TPI_CRYER_GPU_R1_CUH
#define UPL_TPI_CRYER_GPU_R1_CUH
#include "upl_tpi_cryer_gpu_r1.h"
#include <cfloat>
#include <climits>
#include <stdexcept>
#include <cstring>
#include <cstdio>
namespace upl_tpi_cryer_gpu_r1 {
struct RowContext { DeviceState d; const unsigned* id; unsigned active; };
__constant__ RowContext RowContextg;
static bool CaptureHost=false;
static void CheckCuda(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
__device__ static void Bad(DeviceState d,unsigned flag,unsigned id){atomicOr(&d.error->bits,flag);atomicMin(&d.error->firstId,id);}
__device__ static bool Same(double x,double y){return __double_as_longlong(x)==__double_as_longlong(y);}
__device__ static bool Same(float x,float y){return __float_as_uint(x)==__float_as_uint(y);}

// Used by the real source stage AND the independently uploaded device fixtures.
// A newly opened owner may have any finite oldFinal, but its actual pn must be
// positive zero. An unconstrained owner must retain every oldFinal float bit.
__device__ static bool SourceStateValid(float pn,float oldFinal,bool drained){
  return isfinite(pn)&&isfinite(oldFinal)&&(drained?Same(pn,0.f):Same(pn,oldFinal));
}
__device__ static bool Soil(DeviceState d,unsigned id){return id>=d.fixed&&id<d.total;}
// The actual per-stage FSType pointer is explicit; never infer it from ID/depth.
__device__ static bool IsDrained(View v,unsigned p,bool drain,unsigned mode,const double2* xy){
  return drain&&cusph::KerHydroMechIsDrainedParticle(p,mode,xy,v.code,v.fstype);
}
__device__ void CaptureRow(unsigned p,bool drained,double diagonal,double residual,double theta,float actualQ){
  const RowContext c=RowContextg;if(!c.active||!c.id||!c.d.error)return; // Missing rows reject in Prepare, never dereference a cleared descriptor.
  const unsigned id=c.id[p];if(!Soil(c.d,id)){Bad(c.d,1,id);return;}
  if(atomicAdd(c.d.seen+id,1u))Bad(c.d,2,id);
  if(!isfinite(theta)||!isfinite(actualQ)||(!drained&&(!isfinite(diagonal)||diagonal<=0||!isfinite(residual))))Bad(c.d,4,id);
  Observation& o=c.d.rows[id];o.drained=drained?1u:0u;o.S=drained?0.:diagonal;o.R=drained?0.:residual;o.thetaEnd=theta;o.q=actualQ;
}
void PublishEndpoint(DeviceState d,const unsigned* id,bool active){RowContext c={d,id,active?1u:0u};
  CheckCuda(cudaMemcpyToSymbol(RowContextg,&c,sizeof(c)));CaptureHost=active;}
bool CaptureEndpointHost(){return CaptureHost;}
void ResetError(DeviceState d){const Error e={0,UINT_MAX};CheckCuda(cudaMemcpy(d.error,&e,sizeof(e),cudaMemcpyHostToDevice));}
Error GetError(DeviceState d){Error e;CheckCuda(cudaMemcpy(&e,d.error,sizeof(e),cudaMemcpyDeviceToHost));return e;}
__global__ void MapKernel(View v,DeviceState d){unsigned p=blockIdx.x*blockDim.x+threadIdx.x;if(p>=v.np)return;
  const unsigned id=v.id[p];if(id>=d.total){Bad(d,8,id);return;}
  const bool normal=CODE_IsNormal(v.code[p]);
  if(!OwnerRole(id,d.fixed,d.total,normal,CODE_IsPeriodic(v.code[p]),CODE_IsFixed(v.code[p]),CODE_IsFluid(v.code[p]))){Bad(d,32,id);return;}
  if(normal&&atomicCAS(d.slots+id,UINT_MAX,p)!=UINT_MAX)Bad(d,16,id);
}
__global__ void CheckMapKernel(DeviceState d){unsigned id=blockIdx.x*blockDim.x+threadIdx.x;if(id<d.total&&d.slots[id]==UINT_MAX)Bad(d,64,id);}
void Map(View v,DeviceState d){CheckCuda(cudaMemset(d.slots,255,sizeof(unsigned)*d.total));
  MapKernel<<<(v.np+127)/128,128>>>(v,d);CheckMapKernel<<<(d.total+127)/128,128>>>(d);CheckCuda(cudaGetLastError());}
__global__ void InitializeKernel(View v,DeviceState d){unsigned id=blockIdx.x*blockDim.x+threadIdx.x;if(id>=d.total)return;
  const unsigned p=d.slots[id];if(p==UINT_MAX)return;
  if(!isfinite(v.p[p])||v.p[p]!=0.f||v.p0[p]!=0.f||v.J[p]!=1.||v.kappa[p]!=0.f){Bad(d,128,id);return;}
  Observation o={};o.pn=o.previous=o.half=o.q=o.raw=o.finalP=v.p[p];o.prediction=v.p[p];o.Jn=o.Jhalf=o.Jfull=v.J[p];d.rows[id]=o;d.previous[id]=v.p[p];
}

// These fixtures have their own allocations/error packet, no View, DeviceState,
// history/force pointer, physical counter or material array. Uploaded data keeps
// the predicate inputs as real device memory values, not folded literal tests.
struct SourceFixtureInputR2 {float pn,oldFinal;unsigned drained,expected;};
struct RoleFixtureInputR2 {unsigned id,fixed,total,normal,periodic,isfixed,isfluid,expected;};
struct SourceRoleFixtureResultR2 {unsigned bits,firstId,checked;};
__global__ void SourceRoleFixtureKernelR2(const SourceFixtureInputR2* source,
  const RoleFixtureInputR2* roles,SourceRoleFixtureResultR2* error){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;bool actual=false,wanted=false;
  if(i<8){const auto x=source[i];actual=SourceStateValid(x.pn,x.oldFinal,x.drained!=0);wanted=x.expected!=0;}
  else if(i<16){const auto x=roles[i-8];actual=OwnerRole(x.id,x.fixed,x.total,x.normal!=0,x.periodic!=0,x.isfixed!=0,x.isfluid!=0);wanted=x.expected!=0;}
  else return;
  atomicAdd(&error->checked,1u);
  if(actual!=wanted){atomicOr(&error->bits,1u);atomicMin(&error->firstId,i);}
}
static void SourceRoleDeviceFixturesR2(){
  float negativeZero;const unsigned negativeZeroBits=0x80000000u;
  std::memcpy(&negativeZero,&negativeZeroBits,sizeof(negativeZero));
  const SourceFixtureInputR2 source[8]={
    {10.f,10.f,1,0}, // Actual regression: drained/nonzero==oldFinal must reject.
    {negativeZero,negativeZero,1,0}, // A drained negative zero must reject.
    {0.f,10.f,1,1}, {0.f,0.f,1,1},
    {10.f,10.f,0,1}, {11.f,10.f,0,0},
    {negativeZero,0.f,0,0}, {negativeZero,negativeZero,0,1}
  };
  const RoleFixtureInputR2 roles[8]={
    {0,8,37181,1,0,1,0,1}, {8,8,37181,1,0,0,1,1},
    {0,8,37181,0,1,1,0,1}, {8,8,37181,0,1,0,1,1},
    {0,8,37181,0,1,0,1,0}, {8,8,37181,0,1,1,0,0},
    {0,8,37181,0,0,1,0,0}, {8,8,37181,0,0,0,1,0}
  };
  SourceFixtureInputR2* sg=nullptr;RoleFixtureInputR2* rg=nullptr;SourceRoleFixtureResultR2* eg=nullptr;
  try{
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&sg),sizeof(source)));
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&rg),sizeof(roles)));
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&eg),sizeof(SourceRoleFixtureResultR2)));
    const SourceRoleFixtureResultR2 initial={0,UINT_MAX,0};
    CheckCuda(cudaMemcpy(sg,source,sizeof(source),cudaMemcpyHostToDevice));
    CheckCuda(cudaMemcpy(rg,roles,sizeof(roles),cudaMemcpyHostToDevice));
    CheckCuda(cudaMemcpy(eg,&initial,sizeof(initial),cudaMemcpyHostToDevice));
    SourceRoleFixtureKernelR2<<<1,32>>>(sg,rg,eg);CheckCuda(cudaGetLastError());
    SourceRoleFixtureResultR2 actual;CheckCuda(cudaMemcpy(&actual,eg,sizeof(actual),cudaMemcpyDeviceToHost));
    if(actual.bits||actual.firstId!=UINT_MAX||actual.checked!=16)throw std::runtime_error(
      "GPU source/owner-role device fixture rejected case="+std::to_string(actual.firstId));
    {auto p=sg;sg=nullptr;CheckCuda(cudaFree(p));}
    {auto p=rg;rg=nullptr;CheckCuda(cudaFree(p));}
    {auto p=eg;eg=nullptr;CheckCuda(cudaFree(p));}
    std::fprintf(stdout,"UplTpiCryerGpuSourceRoleFixtureR1: source_cases=8 owner_role_cases=8 device_cases_checked=%u device_kernel_completed=true private_error_bits=0\n",actual.checked);
    std::fflush(stdout);
  }catch(...){if(sg)cudaFree(sg);if(rg)cudaFree(rg);if(eg)cudaFree(eg);throw;}
}

void Initialize(View v,DeviceState d){SourceRoleDeviceFixturesR2();InitializeKernel<<<(d.total+127)/128,128>>>(v,d);CheckCuda(cudaGetLastError());}
__global__ void BeginRowsKernel(View v,const float* pn,const double2* xy,DeviceState d,bool drain,unsigned mode,double alpha){
  unsigned id=blockIdx.x*blockDim.x+threadIdx.x;if(!Soil(d,id))return;const unsigned p=d.slots[id];
  Observation& o=d.rows[id];const bool drained=IsDrained(v,p,drain,mode,xy);
  if(!SourceStateValid(pn[p],o.finalP,drained)||!isfinite(v.J[p])||v.J[p]<=0.){Bad(d,256,id);return;}
  o.pn=pn[p];o.previous=d.previous[id];o.Jn=v.J[p];o.sourceDrained=drained?1u:0u;o.drained=o.commitDrained=0;
  o.prediction=alpha==0.?double(o.pn):__dadd_rn(double(o.pn),__dmul_rn(alpha,__dsub_rn(double(o.pn),double(o.previous))));
  if(!isfinite(o.prediction)||fabs(o.prediction)>FLT_MAX){Bad(d,512,id);return;}
  o.half=drained?0.f:__double2float_rn(o.prediction);o.q=o.half;
}
__global__ void WriteHalfKernel(View v,const float* pn,float* out,DeviceState d){unsigned p=blockIdx.x*blockDim.x+threadIdx.x;if(p>=v.np)return;
  if(p<v.npb||!CODE_IsFluid(v.code[p]))out[p]=pn[p];else{const unsigned id=v.id[p];if(!Soil(d,id)){Bad(d,1024,id);return;}out[p]=d.rows[id].half;}}
void BeginDevice(View v,const float* pn,const double2* xy,float* out,DeviceState d,bool drain,unsigned mode,double alpha){
  BeginRowsKernel<<<(d.total+127)/128,128>>>(v,pn,xy,d,drain,mode,alpha);
  WriteHalfKernel<<<(v.np+127)/128,128>>>(v,pn,out,d);CheckCuda(cudaGetLastError());}
__global__ void CorrKernel(View v,DeviceState d){unsigned id=blockIdx.x*blockDim.x+threadIdx.x;if(!Soil(d,id))return;unsigned p=d.slots[id];
  if(!isfinite(v.p[p])||!isfinite(v.J[p])||v.J[p]<=0||!isfinite(v.theta[p])){Bad(d,2048,id);return;}
  Observation& o=d.rows[id];o.half=v.p[p];o.Jhalf=v.J[p];o.thetaH=v.theta[p];}
void CorrDevice(View v,DeviceState d){CorrKernel<<<(d.total+127)/128,128>>>(v,d);CheckCuda(cudaGetLastError());}
__global__ void CaptureJKernel(View v,DeviceState d){unsigned id=blockIdx.x*blockDim.x+threadIdx.x;if(Soil(d,id)){unsigned p=d.slots[id];
  if(!isfinite(v.J[p])||v.J[p]<=0)Bad(d,4096,id);else d.rows[id].Jfull=v.J[p];}}
void CaptureJDevice(View v,DeviceState d){CaptureJKernel<<<(d.total+127)/128,128>>>(v,d);CheckCuda(cudaGetLastError());}
__global__ void GuessKernel(View v,const float* pn,DeviceState d,bool drain,unsigned mode){unsigned p=blockIdx.x*blockDim.x+threadIdx.x;if(p>=v.np)return;
  if(p<v.npb||!CODE_IsFluid(v.code[p]))v.p[p]=pn[p];else{const unsigned id=v.id[p];if(!Soil(d,id)){Bad(d,8192,id);return;}
    v.p[p]=IsDrained(v,p,drain,mode,v.xy)?0.f:__double2float_rn(d.rows[id].prediction);}}
void GuessDevice(View v,const float* pn,DeviceState d,bool drain,unsigned mode){GuessKernel<<<(v.np+127)/128,128>>>(v,pn,d,drain,mode);CheckCuda(cudaGetLastError());}
__global__ void SnapshotKernel(View v,DeviceState d){unsigned id=blockIdx.x*blockDim.x+threadIdx.x;if(Soil(d,id)){unsigned p=d.slots[id];
  d.core[id]={v.xy[p],v.z[p],v.vr[p],v.sigma[p],v.kappa[p],v.p0[p],v.p[p],v.J[p]};d.rows[id].q=v.p[p];d.seen[id]=0;}}
void SnapshotCoreDevice(View v,DeviceState d){SnapshotKernel<<<(d.total+127)/128,128>>>(v,d);CheckCuda(cudaGetLastError());}
__device__ static bool CoreSame(View v,unsigned p,const Core& c){const float4 r=v.vr[p];const auto s=v.sigma[p];
  return Same(v.xy[p].x,c.xy.x)&&Same(v.xy[p].y,c.xy.y)&&Same(v.z[p],c.z)
    &&Same(r.x,c.vr.x)&&Same(r.y,c.vr.y)&&Same(r.z,c.vr.z)&&Same(r.w,c.vr.w)
    &&Same(s.xx,c.sigma.xx)&&Same(s.xy,c.sigma.xy)&&Same(s.xz,c.sigma.xz)&&Same(s.yy,c.sigma.yy)&&Same(s.yz,c.sigma.yz)&&Same(s.zz,c.sigma.zz)
    &&Same(v.kappa[p],c.kappa)&&Same(v.p0[p],c.p0)&&Same(v.p[p],c.q)&&Same(v.J[p],c.J);}
__global__ void PrepareKernel(View v,DeviceState d){unsigned id=blockIdx.x*blockDim.x+threadIdx.x;if(!Soil(d,id))return;
  const unsigned p=d.slots[id];Observation& o=d.rows[id];
  if(d.seen[id]!=1||!CoreSame(v,p,d.core[id])){Bad(d,16384,id);return;}
  double raw=0.;if(!o.drained){if(!isfinite(o.S)||o.S<=0||!isfinite(o.R)||!isfinite(o.q)){Bad(d,32768,id);return;}
    raw=__dadd_rn(double(o.q),__ddiv_rn(o.R,o.S));}
  if(!isfinite(raw)||fabs(raw)>FLT_MAX){Bad(d,65536,id);return;}o.raw=__double2float_rn(raw);
}
void PrepareDevice(View v,DeviceState d){PrepareKernel<<<(d.total+127)/128,128>>>(v,d);CheckCuda(cudaGetLastError());}
__global__ void WriteRawKernel(View v,DeviceState d){unsigned p=blockIdx.x*blockDim.x+threadIdx.x;if(p<v.np&&p>=v.npb&&CODE_IsFluid(v.code[p])){
  const unsigned id=v.id[p];if(!Soil(d,id))Bad(d,131072,id);else v.p[p]=d.rows[id].raw;}}
void WriteDevice(View v,DeviceState d){WriteRawKernel<<<(v.np+127)/128,128>>>(v,d);CheckCuda(cudaGetLastError());}
__global__ void ValidateCommitKernel(View v,DeviceState d,bool drain,unsigned mode){unsigned id=blockIdx.x*blockDim.x+threadIdx.x;if(!Soil(d,id))return;
  const unsigned p=d.slots[id];Observation& o=d.rows[id];const bool constrained=IsDrained(v,p,drain,mode,v.xy);o.commitDrained=constrained?1u:0u;
  if(!isfinite(v.p[p])||!Same(v.J[p],o.Jfull)||!Same(v.p0[p],d.core[id].p0)
    ||(constrained?!Same(v.p[p],0.f):!Same(v.p[p],o.raw)))Bad(d,262144,id);}
void ValidateCommitDevice(View v,DeviceState d,bool drain,unsigned mode){ValidateCommitKernel<<<(d.total+127)/128,128>>>(v,d,drain,mode);CheckCuda(cudaGetLastError());}
__global__ void CommitKernel(View v,DeviceState d){unsigned id=blockIdx.x*blockDim.x+threadIdx.x;if(Soil(d,id)){
  d.rows[id].finalP=v.p[d.slots[id]];d.previous[id]=d.rows[id].pn;}}
void CommitDevice(View v,DeviceState d){CommitKernel<<<(d.total+127)/128,128>>>(v,d);CheckCuda(cudaGetLastError());}
__global__ void CollectKernel(View v,DeviceState d,Observation* output){unsigned n=blockIdx.x*blockDim.x+threadIdx.x;if(n>=d.total-d.fixed)return;
  const unsigned id=n+d.fixed,p=d.slots[id];if(!Same(v.p[p],d.rows[id].finalP)||!Same(v.J[p],d.rows[id].Jfull)){Bad(d,524288,id);return;}output[n]=d.rows[id];}
void CollectDevice(View v,DeviceState d,Observation* output){CollectKernel<<<(d.total-d.fixed+127)/128,128>>>(v,d,output);CheckCuda(cudaGetLastError());}
}
#endif
