// Manufactured spectral/phase component only: no geometry, force pair, or integration.
#ifdef _WITHGPU
#include "JSphGpuSingle.h"
#include "JSphGpu_ker.h"
#include <cuda_runtime.h>
#else
#include "JSphCpuSingle.h"
#include "JSphCpu.cpp" // Real static legacy function; exclude JSphCpu.obj and main.obj when linking.
#include <omp.h>
#endif
#include "JAppInfo.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
JAppInfo AppInfo("UplC08ArtificialStressUnit","r1","08-11-2026");
namespace fs=std::filesystem;
static constexpr unsigned Count=6,Cap=7;
static constexpr float Coef=.25f,Poison=12345.f;
static void AsNeed(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static tsymatrix3d Tensor(double xx,double yy,double zz,double xy=0,double yz=0,double xz=0){tsymatrix3d a{};a.xx=xx;a.yy=yy;a.zz=zz;a.xy=xy;a.yz=yz;a.xz=xz;return a;}
static tsymatrix3f RTensor(float xx,float yy,float zz,float xy=0,float yz=0,float xz=0){tsymatrix3f a{};a.xx=xx;a.yy=yy;a.zz=zz;a.xy=xy;a.yz=yz;a.xz=xz;return a;}
static std::array<double,6> Values(const tsymatrix3f& a){return {a.xx,a.yy,a.zz,a.xy,a.yz,a.xz};}
static double Scale(const tsymatrix3d& a,double p){return (std::max)({1.,fabs(a.xx-p),fabs(a.yy-p),fabs(a.zz-p),fabs(a.xy),fabs(a.yz),fabs(a.xz)});}
struct Case{const char* name;tsymatrix3d effective;float pore;tsymatrix3f raw,legacy_raw;bool floating;};
static const std::array<Case,Count> Cases={{
  {"compression",Tensor(-4096,-8192,-2048),0,RTensor(0,0,0),RTensor(0,0,0),false},
  {"uniaxial_tension",Tensor(4096,-2048,-1024),0,RTensor(-1024,0,0),RTensor(-1024,0,0),false},
  {"rotated_xz",Tensor(0,-2048,0,0,0,4096),0,RTensor(-512,0,-512,0,0,-512),RTensor(-512,0,-512,0,0,-512),false},
  {"negative_p_total_tension",Tensor(-4096,-4096,-4096),-8192,RTensor(-1024,-1024,-1024),RTensor(0,0,0),false},
  {"zero",Tensor(0,0,0),0,RTensor(0,0,0),RTensor(0,0,0),false},
  {"floating_excluded",Tensor(4096,4096,4096),0,RTensor(0,0,0),RTensor(0,0,0),true}
}};
enum class Mode{Legacy,Raw,Epsilon0,PreloadClear};
static const char* ModeName(Mode m){return m==Mode::Legacy?"legacy":m==Mode::Raw?"raw":m==Mode::Epsilon0?"epsilon0":"preload_clear";}
#ifdef _WITHGPU
using AsVelocity=float4;
static AsVelocity Velocity(){return make_float4(0,0,0,1024);}
static void AsCu(cudaError_t e){AsNeed(e==cudaSuccess,cudaGetErrorString(e));}
template<class T>struct AsDevice{
  T* p=nullptr;AsDevice(){AsCu(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*Cap));}
  ~AsDevice(){if(p)cudaFree(p);}AsDevice(const AsDevice&)=delete;AsDevice& operator=(const AsDevice&)=delete;
  void Put(const std::array<T,Cap>& a){AsCu(cudaMemcpy(p,a.data(),sizeof(a),cudaMemcpyHostToDevice));}
  std::array<T,Cap> Get()const{std::array<T,Cap>a{};AsCu(cudaMemcpy(a.data(),p,sizeof(a),cudaMemcpyDeviceToHost));return a;}
};
class Probe:public JSphGpuSingle{
  AsDevice<typecode> codes;AsDevice<AsVelocity> velocity;AsDevice<tsymatrix3d> sigma;AsDevice<float> pore;AsDevice<tsymatrix3f> result;
public:
  Probe(){Np=Count;Npb=NpbOk=0;Codeg=codes.p;Velrhopg=velocity.p;Sigmag=sigma.p;PorePressg=pore.p;ArtificialStressg=result.p;ArtificialStress=true;}
  ~Probe(){Codeg=nullptr;Velrhopg=nullptr;Sigmag=nullptr;PorePressg=nullptr;ArtificialStressg=nullptr;}
  std::array<tsymatrix3f,Cap> Run(Mode mode,const std::array<typecode,Cap>& c,const std::array<AsVelocity,Cap>& v,const std::array<tsymatrix3d,Cap>& s,const std::array<float,Cap>& p){
    codes.Put(c);velocity.Put(v);sigma.Put(s);pore.Put(p);std::array<tsymatrix3f,Cap> poisoned;poisoned.fill(RTensor(Poison,Poison,Poison,Poison,Poison,Poison));result.Put(poisoned);
    StCteInteraction constants{};constants.artificialstress=1;constants.artificialstresscoef=mode==Mode::Epsilon0?0:Coef;cusph::CteInteractionUp(&constants);AsCu(cudaGetLastError());
    PorosityFeedback=mode!=Mode::Legacy;GravityPreload=true;GravityPreloadReleased=mode!=Mode::PreloadClear;
    if(mode==Mode::Legacy)cusph::ComputeArtificialStress(Np,Npb,Codeg,Velrhopg,Sigmag,ArtificialStressg);
    else PrepareArtificialStress();
    AsCu(cudaGetLastError());AsCu(cudaDeviceSynchronize());
    AsNeed(c==codes.Get(),"GPU spectral input codes changed");const auto vv=velocity.Get();const auto ss=sigma.Get();const auto pp=pore.Get();
    AsNeed(!memcmp(v.data(),vv.data(),sizeof(v))&&!memcmp(s.data(),ss.data(),sizeof(s))&&!memcmp(p.data(),pp.data(),sizeof(p)),"GPU spectral physical inputs changed");return result.Get();
  }
};
static constexpr const char* Backend="GPU";
#else
using AsVelocity=tfloat4;
static AsVelocity Velocity(){return TFloat4(0,0,0,1024);}
class Probe:public JSphCpuSingle{
public:
  Probe(){OmpThreads=1;omp_set_num_threads(1);Np=Count;Npb=NpbOk=0;ArtificialStress=true;}
  ~Probe(){Codec=nullptr;Velrhopc=nullptr;Sigmac=nullptr;PorePressc=nullptr;ArtificialStressc=nullptr;}
  std::array<tsymatrix3f,Cap> Run(Mode mode,const std::array<typecode,Cap>& c,const std::array<AsVelocity,Cap>& v,const std::array<tsymatrix3d,Cap>& s,const std::array<float,Cap>& p){
    auto cc=c;auto vv=v;auto ss=s;auto pp=p;std::array<tsymatrix3f,Cap> result;result.fill(RTensor(Poison,Poison,Poison,Poison,Poison,Poison));
    Codec=cc.data();Velrhopc=vv.data();Sigmac=ss.data();PorePressc=pp.data();ArtificialStressc=result.data();ArtificialStressCoef=mode==Mode::Epsilon0?0:Coef;
    PorosityFeedback=mode!=Mode::Legacy;GravityPreload=true;GravityPreloadReleased=mode!=Mode::PreloadClear;PrepareArtificialStress();
    if(mode==Mode::Legacy){std::array<tsymatrix3f,Cap> direct;direct.fill(RTensor(Poison,Poison,Poison,Poison,Poison,Poison));ComputeArtificialStressArray(Count,cc.data(),vv.data(),ss.data(),Coef,direct.data());AsNeed(!memcmp(direct.data(),result.data(),sizeof(result)),"Actual CPU legacy static/member wiring differs");}
    AsNeed(c==cc&&!memcmp(v.data(),vv.data(),sizeof(v))&&!memcmp(s.data(),ss.data(),sizeof(s))&&!memcmp(p.data(),pp.data(),sizeof(p)),"CPU spectral physical inputs changed");
    Codec=nullptr;Velrhopc=nullptr;Sigmac=nullptr;PorePressc=nullptr;ArtificialStressc=nullptr;return result;
  }
};
static constexpr const char* Backend="CPU";
#endif
int main(int argc,char** argv){try{
  AsNeed(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_DIRECTORY");const fs::path out=argv[2];AsNeed(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh output and existing parent required");fs::create_directory(out);
#ifdef _WITHGPU
  AsCu(cudaSetDevice(0));
#endif
  std::array<typecode,Cap> code{};std::array<AsVelocity,Cap> vel{};std::array<tsymatrix3d,Cap> sigma{};std::array<float,Cap> pore{};
  for(unsigned i=0;i<Count;i++){code[i]=typecode(Cases[i].floating?CODE_TYPE_FLOATING:CODE_TYPE_FLUID);vel[i]=Velocity();sigma[i]=Cases[i].effective;pore[i]=Cases[i].pore;}
  Probe probe;std::ofstream csv(out/"spectral.csv");AsNeed(bool(csv),"CSV creation failed");csv<<std::setprecision(17)<<"mode,case,component,actual,reference,error,budget,effective_xx,effective_yy,effective_zz,effective_xy,effective_yz,effective_xz,pore_Pa,rhop,epsilon\n";
  unsigned rows=0,tailchecks=0;double maxratio=0;
  for(Mode m:{Mode::Legacy,Mode::Raw,Mode::Epsilon0,Mode::PreloadClear}){
    const auto actual=probe.Run(m,code,vel,sigma,pore);for(double x:Values(actual[Count]))AsNeed(x==Poison,"Spectral output tail canary changed");tailchecks++;
    for(unsigned i=0;i<Count;i++){
      const bool zero=m==Mode::Epsilon0||m==Mode::PreloadClear;auto ref=Values(zero?RTensor(0,0,0):m==Mode::Legacy?Cases[i].legacy_raw:Cases[i].raw);
      const double normalization=m==Mode::Legacy?1./(1024.*1024.):1.;if(m==Mode::Legacy)for(auto& x:ref)x*=normalization;
      const double budget=32.*FLT_EPSILON*Scale(sigma[i],m==Mode::Legacy?0.:pore[i])*normalization;const auto r=Values(actual[i]);
      for(unsigned a=0;a<6;a++){const double error=fabs(r[a]-ref[a]);AsNeed(std::isfinite(r[a])&&error<=budget,"Analytic spectral roundoff budget exceeded");if(zero||i==0||i==4||i==5)AsNeed(r[a]==0.,"Required zero spectral/phase output is nonzero");
        maxratio=(std::max)(maxratio,error/budget);csv<<ModeName(m)<<','<<Cases[i].name<<','<<a<<','<<r[a]<<','<<ref[a]<<','<<error<<','<<budget<<','<<sigma[i].xx<<','<<sigma[i].yy<<','<<sigma[i].zz<<','<<sigma[i].xy<<','<<sigma[i].yz<<','<<sigma[i].xz<<','<<pore[i]<<",1024,"<<(m==Mode::Epsilon0?0:Coef)<<'\n';rows++;}
    }
  }
  AsNeed(rows==144&&tailchecks==4,"Declared spectral/phase coverage incomplete");csv.flush();AsNeed(bool(csv),"CSV write failed");
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_c08_as_unit_r1\",\"backend\":\""<<Backend<<"\",\"passed\":true,\"tensor_cases\":6,\"modes\":4,\"scalar_rows\":"<<rows<<",\"tail_checks\":"<<tailchecks<<",\"max_error_over_budget\":"<<maxratio<<",\"physical_inputs_unchanged\":true,\"actual_Prepare_member\":true,\"legacy_normalized_analytic_reference\":true,\"old_new_runtime_bit_comparison\":false,\"pair_force_tested\":false,\"physical_steps\":0,\"geometry_or_contact_tested\":false,\"physical_acceptance\":false}\n";done.flush();AsNeed(bool(done),"Completion write failed");std::cout<<Backend<<" spectral/phase rows="<<rows<<" pair_force_tested=false\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Artificial-stress unit failed\n";return 1;}}
