// Predicate regression through the actual GPU Darcy wrapper; no copied rate kernel.
// One fixed source and one fluid receiver share an actual search cell. No wall-state fit.
#include "JSphGpu_ker.h"
#include "FunSphKernel.h"
#include "JDsDcellDef.h"
#include "JAppInfo.h"
#include <cuda_runtime.h>
#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>
JAppInfo AppInfo("UplInactiveCutoffGpu","r1","06-11-2026");
namespace fs=std::filesystem;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static void Cu(cudaError_t e){Need(e==cudaSuccess,cudaGetErrorString(e));}
template<class T>struct Device{T* p=nullptr;explicit Device(unsigned n){Cu(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*n));}~Device(){if(p)cudaFree(p);}Device(const Device&)=delete;Device& operator=(const Device&)=delete;};
template<class T>static void Up(T* p,const std::vector<T>& a){Cu(cudaMemcpy(p,a.data(),a.size()*sizeof(T),cudaMemcpyHostToDevice));}
template<class T>static std::vector<T> Down(const T* p,unsigned n){std::vector<T>a(n);Cu(cudaMemcpy(a.data(),p,n*sizeof(T),cudaMemcpyDeviceToHost));return a;}
template<class T>static bool Same(const std::vector<T>& a,const std::vector<T>& b){return a.size()==b.size()&&(a.empty()||!memcmp(a.data(),b.data(),a.size()*sizeof(T)));}
static constexpr unsigned N=2,Fixed=1,Cap=4,Canary=0x1234abcd;
static constexpr double Solid=.75,Kw=65536.,Rhow=1000.,V0=1./64.,Gamma=Rhow*9.80665;
static constexpr float Sentinel=1234567.f;
struct Scenario{const char* name;double distance;byte mode;bool poison,selector,reject;};
class Patch{
  TpKernel tk;StCteSph sph=CteSphNull();StDivDataGpu dvd;
  Device<int2> cells{4};Device<unsigned> dc{Cap},invalid{2};Device<typecode> codeg{Cap};Device<byte> modeg{Cap};
  Device<double2> xy{Cap};Device<double> z{Cap},j{Cap},theta{Cap};Device<tmatrix3d> c{Cap};Device<float3> ace{Cap};Device<float> p{Cap},rate{Cap};
public:
  explicit Patch(TpKernel kernel):tk(kernel){
    sph.kernelh=.125f;sph.kernelsize=.25f;sph.kernelsize2=.0625f;sph.eta2=1.f/65536.;
    sph.kwend=fsph::GetKernelWendland_Ctes(true,sph.kernelh);sph.kcubic=fsph::GetKernelCubic_Ctes(true,sph.kernelh);
    StCteInteraction ct={};ct.simulate2d=1;ct.nbound=Fixed;ct.kernelh=sph.kernelh;ct.kernelsize=sph.kernelsize;ct.kernelsize2=sph.kernelsize2;ct.eta2=sph.eta2;ct.poscellsize=ct.scell=1;ct.axis=MGDIV_Z;ct.cellcode=DCEL_GetCode(1,1,1);
    ct.awen=sph.kwend.awen;ct.bwen=sph.kwend.bwen;const auto kc=sph.kcubic;ct.cubic_a1=kc.a1;ct.cubic_a2=kc.a2;ct.cubic_aa=kc.aa;ct.cubic_a24=kc.a24;ct.cubic_c1=kc.c1;ct.cubic_d1=kc.d1;ct.cubic_c2=kc.c2;ct.cubic_odwdeltap=kc.od_wdeltap;cusph::CteInteractionUp(&ct);
    Up(cells.p,std::vector<int2>{make_int2(0,1),make_int2(0,0),make_int2(1,2),make_int2(0,0)});Up(dc.p,std::vector<unsigned>(Cap,0));
    dvd=MakeDivDataGpu(1,TUint3(1,1,1),TUint3(0),cells.p,4,ct.cellcode,TDouble3(0),sph.kernelsize2,1);
  }
  double Execute(const Scenario& s,std::ostream& out){
    std::vector<double2> positions(Cap,make_double2(.5,0));positions[0].x+=s.distance;std::vector<double> heights(Cap,.5),js(Cap,1.),th(Cap,0.);th[1]=-.125;
    std::vector<tmatrix3d> matrices(Cap,TMatrix3d(1,0,0,0,0,0,0,0,1));std::vector<float3> accelerations(Cap,make_float3(0,0,0));accelerations[0].x=.125f;
    std::vector<float> pressures(Cap,4.f);pressures[0]=2.f;std::vector<typecode> codes(Cap,CODE_TYPE_FIXED);codes[1]=CODE_TYPE_FLUID;std::vector<byte> modes(Cap,s.mode);
    if(s.poison){const double nan=std::numeric_limits<double>::quiet_NaN();const float fnan=std::numeric_limits<float>::quiet_NaN();js[0]=nan;pressures[0]=fnan;accelerations[0]=make_float3(fnan,fnan,fnan);matrices[0]=TMatrix3d(nan);}
    Up(xy.p,positions);Up(z.p,heights);Up(j.p,js);Up(theta.p,th);Up(c.p,matrices);Up(ace.p,accelerations);Up(p.p,pressures);Up(codeg.p,codes);Up(modeg.p,modes);Up(rate.p,std::vector<float>(Cap,Sentinel));Up(invalid.p,std::vector<unsigned>{N,Canary});
    const double khyd=double(float(.0001));
    cusph::ComputeDynamicPorePressureRate(N,Fixed,dvd,dc.p,xy.p,z.p,codeg.p,c.p,ace.p,j.p,theta.p,p.p,rate.p,Solid,Kw,Rhow,khyd,Gamma,V0,invalid.p,false,0.,nullptr,true,s.selector?modeg.p:nullptr,nullptr,nullptr,false,false,HMLOAD_None,TDouble3(0),0.,tk);
    Cu(cudaDeviceSynchronize());const auto bad=Down(invalid.p,2);const auto result=Down(rate.p,Cap);
    Need(bad[0]==(s.reject?1u:N)&&bad[1]==Canary,"Actual stored-radius inactive predicate mismatch or invalid canary changed");
    Need(result[0]==Sentinel&&result[2]==Sentinel&&result[3]==Sentinel,"Fixed/tail rate canary changed");
    Need(Same(positions,Down(xy.p,Cap))&&Same(heights,Down(z.p,Cap))&&Same(js,Down(j.p,Cap))&&Same(th,Down(theta.p,Cap))&&Same(matrices,Down(c.p,Cap))&&Same(accelerations,Down(ace.p,Cap))&&Same(pressures,Down(p.p,Cap))&&Same(codes,Down(codeg.p,Cap))&&Same(modes,Down(modeg.p,Cap)),"Rate predicate changed physical inputs");
    double reference=0,budget=0,ratio=0;
    if(!s.reject){
      const double B=Kw/(1.-Solid),compression=-B*th[1];reference=compression;
      if(s.mode==BMODE_MDBC2&&s.selector){
        // Independent single-pair expression, not a second neighbor traversal/kernel.
        const double d=-s.distance,rr=d*d,fac=(tk==KERNEL_Cubic?fsph::GetKernel_Fac<KERNEL_Cubic>(sph,float(rr)):fsph::GetKernel_Fac<KERNEL_Wendland>(sph,float(rr)));
        const double g=d*fac,dp=double(pressures[1])-pressures[0],w=V0*d*(2*g)/(rr+double(sph.eta2)),lp=w*dp,lx=d*w,gp=-g*V0*dp,da=V0*accelerations[0].x*g;
        reference=B*(-th[1]+khyd/Gamma*(lp-gp*lx+Rhow*da));
        const double propagated=B*(fabs(th[1])+khyd/Gamma*(fabs(lp)+fabs(gp)*fabs(lx)+Rhow*fabs(da)));
        budget=64.*FLT_EPSILON*propagated+256.*DBL_EPSILON*(std::max)(1.,fabs(B*th[1]))+1e-6;
        Need(fabs(reference-compression)>10*budget,"Active in-support source witness is empty");
        Need(std::isfinite(result[1])&&fabs(double(result[1])-reference)<=budget,"Original complete-rate propagated budget failed");ratio=fabs(double(result[1])-reference)/budget;
      }else Need(result[1]==float(compression),"Out-of-support or coincident poison was consumed");
    }
    // Invalid receivers may already have partial/complete rates: no unchanged-rate promise.
    out<<(tk==KERNEL_Cubic?"Cubic":"Wendland")<<','<<s.name<<','<<s.distance<<','<<s.distance*s.distance<<','<<sph.kernelsize2<<','<<unsigned(s.mode)<<','<<s.selector<<','<<s.poison<<','<<bad[0]<<','<<result[1]<<','<<s.reject<<',';
    if(!s.reject)out<<reference;out<<',';if(budget)out<<budget;out<<',';if(budget)out<<ratio;out<<'\n';return ratio;
  }
};
int main(int argc,char** argv){try{
  Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_RESULT");const fs::path out=argv[2];Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh result/existing parent required");fs::create_directory(out);Cu(cudaSetDevice(0));
  std::ofstream csv(out/"predicates.csv");csv<<std::setprecision(17)<<"kernel,case,distance_m,rr2,stored_R2,mode,selector_present,poisoned_fixed,invalid_index,rate_Pa_s,rejected,reference_Pa_s,original_budget,error_over_budget\n";
  const Scenario cases[]={{"active_IN",.125,BMODE_MDBC2,false,true,false},{"OFF_OUT_poison",.375,BMODE_MDBC2OFF,true,true,false},{"OFF_IN",.125,BMODE_MDBC2OFF,false,true,true},{"OFF_at_R",.25,BMODE_MDBC2OFF,false,true,true},{"OFF_zero_poison",0.,BMODE_MDBC2OFF,true,true,false},{"NULL_OUT_poison",.375,BMODE_MDBC2OFF,true,false,false},{"NULL_IN",.125,BMODE_MDBC2OFF,false,false,true}};
  unsigned rows=0,rejections=0;double maxratio=0;for(TpKernel tk:{KERNEL_Wendland,KERNEL_Cubic}){Patch patch(tk);for(const auto& s:cases){maxratio=(std::max)(maxratio,patch.Execute(s,csv));rows++;rejections+=unsigned(s.reject);}}
  Need(rows==14&&rejections==6,"Predicate coverage incomplete");csv.flush();Need(bool(csv),"Predicate CSV write failed");std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_inactive_cutoff_gpu_r1\",\"passed\":true,\"kernel_conditions\":2,\"predicate_rows\":14,\"required_rejections\":6,\"max_active_error_over_original_budget\":"<<maxratio<<",\"actual_GPU_wrapper\":true,\"same_search_cell\":true,\"poison_ignored_only_outside_or_zero\":true,\"invalid_rate_unchanged_claimed\":false,\"physical_steps\":0,\"public_wall_or_physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}}
