// Isolated C04 reduction replay. The driver extracts the original kernels from the retained solver source.
#include <cuda_runtime.h>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
#include "JSphGpu_ker.h"
#include "FunctionsBasic_iker.h"
#include "cryer_dt_original.cuh"
#include "cryer_p3_dt_fused_probe_r1.cu"

using cryer_p3_dt::Params;
using cryer_p3_dt::Summary;
using cryer_p3_dt::Value;
static_assert(sizeof(typecode)==2 && sizeof(Params)==56 && sizeof(Summary)==32,"input layout");
static_assert(SPHBSIZE==256,"original launch width");
static void check(cudaError_t status){
  if(status!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(status));
}
template<class T> struct Device{
  T* ptr=nullptr;
  explicit Device(size_t n){check(cudaMalloc((void**)&ptr,n*sizeof(T)));}
  ~Device(){cudaFree(ptr);}
  void put(const T* src,size_t n){check(cudaMemcpy(ptr,src,n*sizeof(T),cudaMemcpyHostToDevice));}
  void get(T* dst,size_t n){check(cudaMemcpy(dst,ptr,n*sizeof(T),cudaMemcpyDeviceToHost));}
};
struct Event{
  cudaEvent_t handle;
  Event(){check(cudaEventCreate(&handle));}
  ~Event(){cudaEventDestroy(handle);}
};
struct State{
  unsigned n,npb; const typecode* code; const double* j; Params p;
};
static Summary empty(unsigned n){return {0.,0.,0.,n,n};}
static void original(const State& s,Summary* out,bool legacy){
  original_dt::ComputePorosityWaveSpeed2(s.n,s.npb,s.p.solid0,s.p.rho0,s.p.rhow,s.p.modulus,legacy?s.p.kw:0.,
    s.code,s.j,legacy?&out->legacy2:&out->skeleton2,legacy?&out->invalid_legacy:&out->invalid_skeleton,
    legacy?s.p.conductivity:0.,legacy?s.p.gamma:1.,legacy?&out->diffusion:nullptr,false,0.);
}
static void fused(const State& s,Summary* out){
  cryer_p3_dt::Launch(s.n,s.npb,s.code,s.j,s.p,out);
}
// Copies the original pass's two consecutive maxima together, matching its actual host/device transfers.
static unsigned guarded(const State& s,Summary* workspace,bool use_fused,Summary& out,unsigned& launches){
  out=empty(s.n); launches=1;
  if(use_fused){
    check(cudaMemcpy(workspace,&out,sizeof(out),cudaMemcpyHostToDevice));
    fused(s,workspace);
    check(cudaMemcpy(&out,workspace,sizeof(out),cudaMemcpyDeviceToHost));
    return cryer_p3_dt::FirstFailure(out,s.n);
  }
  // The reference uses two adjacent doubles for legacy wave/diffusion and a separate invalid word.
  double* maxima=(double*)workspace; unsigned* invalid=&workspace->invalid_legacy;
  double host[2]={0,0};
  check(cudaMemset(maxima,0,sizeof(host)));
  check(cudaMemcpy(invalid,&out.invalid_legacy,sizeof(unsigned),cudaMemcpyHostToDevice));
  original_dt::ComputePorosityWaveSpeed2(s.n,s.npb,s.p.solid0,s.p.rho0,s.p.rhow,s.p.modulus,s.p.kw,
    s.code,s.j,maxima,invalid,s.p.conductivity,s.p.gamma,maxima+1,false,0.);
  check(cudaMemcpy(host,maxima,sizeof(host),cudaMemcpyDeviceToHost));
  check(cudaMemcpy(&out.invalid_legacy,invalid,sizeof(unsigned),cudaMemcpyDeviceToHost));
  out.legacy2=host[0]; out.diffusion=host[1];
  if(out.invalid_legacy<s.n || !std::isfinite(host[0]) || !(host[0]>0.) || !std::isfinite(host[1]) || host[1]<0.)return 1;
  launches++;
  check(cudaMemset(maxima,0,sizeof(double)));
  check(cudaMemcpy(invalid,&out.invalid_skeleton,sizeof(unsigned),cudaMemcpyHostToDevice));
  original_dt::ComputePorosityWaveSpeed2(s.n,s.npb,s.p.solid0,s.p.rho0,s.p.rhow,s.p.modulus,0.,
    s.code,s.j,maxima,invalid,0.,1.,nullptr,false,0.);
  check(cudaMemcpy(&out.skeleton2,maxima,sizeof(double),cudaMemcpyDeviceToHost));
  check(cudaMemcpy(&out.invalid_skeleton,invalid,sizeof(unsigned),cudaMemcpyDeviceToHost));
  return out.invalid_skeleton==s.n && std::isfinite(out.skeleton2) && out.skeleton2>0.?0:2;
}
__global__ void capture_fused(State s,double* values,unsigned char* errors){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i>=s.n)return;
  Value v={0.,0.,0.,true,true};
  if(i>=s.npb && CODE_IsNormal(s.code[i]) && CODE_IsFluid(s.code[i]))v=cryer_p3_dt::Evaluate(s.j[i],s.p);
  values[i]=v.legacy2;values[s.n+i]=v.skeleton2;values[2*s.n+i]=v.diffusion;
  errors[i]=!v.legacy_valid;errors[s.n+i]=!v.skeleton_valid;
}
static void capture_original(const State& s,Summary* out,double* v,unsigned char* err,bool legacy){
  const unsigned w=SPHBSIZE;
  original_dt::CapturedWave<<<GetSimpleGridSize(s.n,w),w,w*sizeof(double)*(legacy?2:1)>>>(s.n,s.npb,
    s.p.solid0,s.p.rho0,s.p.rhow,s.p.modulus,legacy?s.p.kw:0.,s.code,s.j,
    legacy?&out->legacy2:&out->skeleton2,legacy?&out->invalid_legacy:&out->invalid_skeleton,
    legacy?s.p.conductivity:0.,legacy?s.p.gamma:1.,legacy?&out->diffusion:nullptr,false,0.,
    legacy?v:v+s.n,legacy?v+2*s.n:nullptr,legacy?err:err+s.n);
}
static uint64_t bits(double x){uint64_t b;std::memcpy(&b,&x,8);return b;}
static std::vector<uint64_t> host_bounds(const Summary& e){
  // Frozen J does not retain stage AceMax / ViscDtMax. These fixed fixtures exercise the downstream expressions.
  const double h=float(.0045),safety=float(.1),cfl=.2,dt=1.9073486328125e-6;
  std::vector<uint64_t> result;
  const double mechanics[][3]={{0.,0.,0.},{1.1e4,100.,.75},{1.e10,1.e-4,500.}};
  for(const auto& m:mechanics){
    const double dt1=m[0]?std::sqrt(h/m[0]):DBL_MAX;
    const double sk=h/(std::max(std::sqrt(e.skeleton2),m[1]*10.)+h*m[2]);
    const double old=h/(std::max(std::sqrt(e.legacy2),m[1]*10.)+h*m[2]);
    const double pore=e.diffusion>0.?safety*h*h/e.diffusion:DBL_MAX;
    const double bound=std::min(std::min(cfl*dt1,cfl*sk),pore);
    for(double value:{cfl*dt1,cfl*sk,pore,cfl*old,bound,dt-bound})result.push_back(bits(value));
    result.push_back(dt>bound);
  }
  return result;
}
static constexpr unsigned batch=16, groups=11, wall_batch=2;
static void measure(const State& s,const std::string& name,std::ostream& times){
  Device<Summary> d(batch);
  std::vector<Summary> init(batch,empty(s.n));
  Event before,after;
  for(int g=-2;g<int(groups);g++){
    for(int order=0;order<2;order++){
      const bool one=(unsigned(g+2)+unsigned(order))%2!=0;
      d.put(init.data(),batch);
      check(cudaDeviceSynchronize());
      check(cudaEventRecord(before.handle));
      for(unsigned i=0;i<batch;i++){
        if(one)fused(s,d.ptr+i);
        else {original(s,d.ptr+i,true);original(s,d.ptr+i,false);}
      }
      check(cudaEventRecord(after.handle));
      check(cudaEventSynchronize(after.handle));
      float ms=0;check(cudaEventElapsedTime(&ms,before.handle,after.handle));
      // Independently time the production-order synchronizing transfers and guard; input arrays are already resident.
      const auto t0=std::chrono::steady_clock::now();
      for(unsigned i=0;i<wall_batch;i++){
        Summary x;unsigned launches;
        if(guarded(s,d.ptr,one,x,launches))throw std::runtime_error("timing sample failed");
      }
      const double wall=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-t0).count();
      if(g>=0)times<<name<<','<<g<<','<<order<<','<<(one?"fused":"old")<<','<<batch<<','<<ms*1000./batch
                     <<','<<wall_batch<<','<<wall/wall_batch<<'\n';
    }
  }
}
struct Header{
  char name[64];unsigned n,npb,expected,invalid_legacy,invalid_skeleton,timed;
  Params p;
};
static_assert(sizeof(Header)==144,"fixture header layout");
static void sample(std::ifstream& data,const Header& a,std::ostream& report,std::ostream& times){
  std::vector<double> j(a.n);std::vector<typecode> code(a.n);
  data.read((char*)j.data(),a.n*sizeof(double));data.read((char*)code.data(),a.n*sizeof(typecode));
  if(!data || !a.n || a.n>1000000)throw std::runtime_error("invalid fixture");
  Device<double> dj(a.n);Device<typecode> dc(a.n);dj.put(j.data(),a.n);dc.put(code.data(),a.n);
  State s={a.n,a.npb,dc.ptr,dj.ptr,a.p};
  Device<Summary> d(1);Summary ref,fus,old_guard,fused_guard;const auto initial=empty(a.n);
  d.put(&initial,1);original(s,d.ptr,true);original(s,d.ptr,false);d.get(&ref,1);
  d.put(&initial,1);fused(s,d.ptr);d.get(&fus,1);
  unsigned oc,fc;
  const unsigned old_fail=guarded(s,d.ptr,false,old_guard,oc), fused_fail=guarded(s,d.ptr,true,fused_guard,fc);
  Device<double> v(3*a.n);Device<unsigned char> e(2*a.n);
  std::vector<double> original_v(3*a.n),fused_v(3*a.n);
  std::vector<unsigned char> original_e(2*a.n),fused_e(2*a.n);
  d.put(&initial,1);capture_original(s,d.ptr,v.ptr,e.ptr,true);capture_original(s,d.ptr,v.ptr,e.ptr,false);
  v.get(original_v.data(),3*a.n);e.get(original_e.data(),2*a.n);
  capture_fused<<<(a.n+127)/128,128>>>(s,v.ptr,e.ptr);
  v.get(fused_v.data(),3*a.n);e.get(fused_e.data(),2*a.n);
  unsigned bad_values=0,bad_flags=0;
  for(size_t i=0;i<original_v.size();i++)bad_values+=bits(original_v[i])!=bits(fused_v[i]);
  for(size_t i=0;i<original_e.size();i++)bad_flags+=original_e[i]!=fused_e[i];
  const bool same_summary=!std::memcmp(&ref,&fus,sizeof(ref));
  const bool same_guard=old_fail==fused_fail && old_fail==a.expected && oc==(old_fail==1?1u:2u) && fc==1
    && ref.invalid_legacy==a.invalid_legacy && ref.invalid_skeleton==a.invalid_skeleton
    && bits(old_guard.legacy2)==bits(fused_guard.legacy2) && bits(old_guard.diffusion)==bits(fused_guard.diffusion)
    && old_guard.invalid_legacy==fused_guard.invalid_legacy
    && (old_fail==1 || !std::memcmp(&old_guard,&fused_guard,sizeof(ref)));
  const bool same_bound=old_fail || host_bounds(old_guard)==host_bounds(fused_guard);
  report<<a.name<<','<<a.n<<','<<a.npb<<','<<a.expected<<','<<old_fail<<','<<fused_fail<<','<<oc<<','<<fc<<','
    <<ref.invalid_legacy<<','<<ref.invalid_skeleton<<','<<ref.legacy2<<','<<ref.skeleton2<<','<<ref.diffusion<<','
    <<bad_values<<','<<bad_flags<<','<<same_summary<<','<<same_guard<<','<<(old_fail?0:21)<<','<<same_bound<<'\n';
  report.flush();
  if(bad_values || bad_flags || !same_summary || !same_guard || !same_bound)throw std::runtime_error(a.name);
  if(a.timed)measure(s,a.name,times);
}
int main(int argc,char** argv){
  try{
    if(argc!=4)throw std::runtime_error("expected fixture.bin results.csv timings.csv");
    std::ifstream data(argv[1],std::ios::binary);std::ofstream rows(argv[2]),times(argv[3]);
    if(!data || !rows || !times)throw std::runtime_error("open failed");
    cudaDeviceProp prop;check(cudaGetDeviceProperties(&prop,0));
    std::cout<<prop.name<<" sm"<<prop.major<<prop.minor<<" runtime "<<CUDART_VERSION<<"\n";
    rows<<std::setprecision(17)<<"sample,lanes,npb,expected,old_failure,fused_failure,guarded_old_launches,guarded_fused_launches,invalid_legacy,invalid_skeleton,max_legacy_c2,max_skeleton_c2,max_diffusivity,lane_value_mismatches,lane_flag_mismatches,same_summary,same_guard,derived_checks,same_derived\n";
    times<<std::setprecision(10)<<"sample,paired_group,order,path,event_batch,kernel_us_per_eval,transaction_batch,transaction_us_per_eval\n";
    Header a;while(data.peek()!=EOF){
      data.read((char*)&a,sizeof(a));if(!data)throw std::runtime_error("short header");
      sample(data,a,rows,times);
    }
    check(cudaDeviceSynchronize());return 0;
  }catch(const std::exception& ex){std::cerr<<"FAILED "<<ex.what()<<"\n";return 1;}
}
