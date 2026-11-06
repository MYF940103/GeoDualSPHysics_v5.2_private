// Private actual GPU stage/lifetime diagnostic. No force, position kernel or trajectory.
#include "JSphGpuSimple_ker.h"
#include "JSphGpu_ker.h"
#include "JAppInfo.h"
#include <cuda_runtime.h>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
JAppInfo AppInfo("UplDensityCacheGpu","r1","06-11-2026");
namespace fs=std::filesystem;
constexpr unsigned N=4,NB=1;constexpr double DT=.125;
constexpr float RHO0=2072.5f,RHOW=1000.f,N0=.35f;
static void Need(bool v,const char* s){if(!v)throw std::runtime_error(s);}
static void Cu(cudaError_t e){Need(e==cudaSuccess,cudaGetErrorString(e));}
template<class T,unsigned C=N> struct Device{
  T* p=nullptr;Device(){Cu(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*C));clear();}
  ~Device(){if(p)cudaFree(p);}Device(const Device&)=delete;Device& operator=(const Device&)=delete;
  void clear(){Cu(cudaMemset(p,0,sizeof(T)*C));}
  void put(const std::array<T,C>& x){Cu(cudaMemcpy(p,x.data(),sizeof(T)*C,cudaMemcpyHostToDevice));}
  std::array<T,C> get()const{std::array<T,C> x;Cu(cudaMemcpy(x.data(),p,sizeof(T)*C,cudaMemcpyDeviceToHost));return x;}
};
template<class T> static void Raw(std::ostream& f,const T& x){f.write(reinterpret_cast<const char*>(&x),sizeof(x));}
static uint32_t Bits(float x){uint32_t b;memcpy(&b,&x,sizeof(b));return b;}
static bool DoubleBits(double a,double b){return memcmp(&a,&b,sizeof(a))==0;}
struct Counts{unsigned pre=0,cor=0,j=0,records=0,rows=0,rejected=0;};
class Stage{
public:
  Device<typecode> code;Device<float4> pre,vel;Device<float3> ace;
  Device<tsymatrix3d> spre,sigma;Device<tsymatrix3f> rsigma;
  Device<float> kpre,k,ar;Device<double2> movxy;Device<double> movz,jn,j,theta;
  Device<unsigned,1> invalid;
  std::array<float4,N> input{};std::array<float,N> arc{};Counts& count;
  explicit Stage(Counts& c):count(c){}
  void reset(const std::array<double,N>& J,const std::array<double,N>& th,float oldw,bool legacy=false){
    code.put({typecode(CODE_TYPE_FIXED),typecode(CODE_TYPE_FLUID),typecode(CODE_TYPE_FLUID),typecode(CODE_TYPE_FLUID)});
    for(unsigned p=0;p<N;p++)input[p]=make_float4(p?.125f*p:0.f,p?-.25f:0.f,p?.5f:0.f,p?oldw+float(p-1)*16.f:2100.f);
    if(legacy){input[1].w=699.f;input[2].w=RHO0;input[3].w=3001.f;}
    arc={16.f,legacy?0.f:std::numeric_limits<float>::quiet_NaN(),legacy?8.f:std::numeric_limits<float>::quiet_NaN(),legacy?0.f:std::numeric_limits<float>::quiet_NaN()};
    pre.put(input);vel.clear();ar.put(arc);jn.put(J);j.put(J);theta.put(th);
    std::array<float3,N> a;std::array<tsymatrix3d,N> s;std::array<tsymatrix3f,N> r;
    for(unsigned p=0;p<N;p++){a[p]=make_float3(.25f,-.125f,-.5f);s[p]=TSymMatrix3d(-4.,.125,.25,-5.,.375,-6.);r[p]={.25f,.125f,0.f,-.25f,.0625f,.5f};}
    ace.put(a);spre.put(s);rsigma.put(r);sigma.clear();kpre.clear();k.clear();movxy.clear();movz.clear();
  }
  unsigned commit(bool cor){
    invalid.put({N});cusph::UpdatePorosityObserver(N,NB,cor,cor?DT:DT*.5,1.-double(N0),code.p,k.p,jn.p,theta.p,j.p,invalid.p);
    count.j++;Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());return invalid.get()[0];
  }
  void update(bool cor,bool feedback,float lo=700.f,float hi=3000.f){
#ifndef UPL_DENSITY_CACHE_LEGACY_ONLY
    if(feedback){
      const cusphs::StPorosityRhopState state{j.p,jn.p,theta.p};
      if(cor)cusphs::ComputeStepSymplecticCor(false,false,false,DP_C,MDBC2_None,N,NB,pre.p,ar.p,ace.p,nullptr,spre.p,kpre.p,rsigma.p,nullptr,nullptr,DT*.5,DT,RHO0,lo,hi,TFloat3(0,0,-.25f),code.p,movxy.p,movz.p,vel.p,sigma.p,k.p,nullptr,nullptr,state);
      else cusphs::ComputeStepSymplecticPre(false,false,false,DP_C,N,NB,pre.p,ar.p,ace.p,nullptr,spre.p,kpre.p,rsigma.p,nullptr,DT*.5,RHO0,lo,hi,TFloat3(0,0,-.25f),code.p,movxy.p,movz.p,vel.p,sigma.p,k.p,nullptr,nullptr,state);
    }
    else
#endif
    {
      Need(!feedback,"Legacy-only binary cannot request the new cache state");
      // Intentionally omit the new optional state: the old source signature is callable here.
      if(cor)cusphs::ComputeStepSymplecticCor(false,false,false,DP_C,MDBC2_None,N,NB,pre.p,ar.p,ace.p,nullptr,spre.p,kpre.p,rsigma.p,nullptr,nullptr,DT*.5,DT,RHO0,lo,hi,TFloat3(0,0,-.25f),code.p,movxy.p,movz.p,vel.p,sigma.p,k.p,nullptr,nullptr);
      else cusphs::ComputeStepSymplecticPre(false,false,false,DP_C,N,NB,pre.p,ar.p,ace.p,nullptr,spre.p,kpre.p,rsigma.p,nullptr,DT*.5,RHO0,lo,hi,TFloat3(0,0,-.25f),code.p,movxy.p,movz.p,vel.p,sigma.p,k.p,nullptr,nullptr);
    }
    if(cor)count.cor++;else count.pre++;Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());
  }
  void snapshot(std::ostream& bin){
    const auto c=code.get();const auto v=vel.get();const auto s=sigma.get();const auto kp=k.get();const auto z=movz.get(),J=j.get();const auto xy=movxy.get();
    for(unsigned p=0;p<N;p++){Raw(bin,uint32_t(c[p]));Raw(bin,v[p]);Raw(bin,s[p]);Raw(bin,kp[p]);Raw(bin,xy[p]);Raw(bin,z[p]);Raw(bin,J[p]);}
  }
  void nullrow(std::ostream& csv,const char* test,bool cor){
    const auto c=code.get();const auto v=vel.get();const auto s=sigma.get();const auto kp=k.get();const auto z=movz.get(),J=j.get();const auto xy=movxy.get();
    bool ok=Bits(v[0].w)==Bits(RHO0);
    for(unsigned p=NB;p<N;p++){
      const float expected=float(double(input[p].w)+(cor?DT:DT*.5)*arc[p]);
      ok=ok&&Bits(v[p].w)==Bits(expected)&&bool(CODE_IsOutRhop(c[p]))==(expected<700.f||expected>3000.f);
      csv<<test<<','<<(cor?"cor":"pre")<<','<<p<<','<<uint32_t(c[p])<<','<<v[p].x<<','<<v[p].y<<','<<v[p].z<<','<<v[p].w<<','<<Bits(v[p].w)<<','<<expected<<','<<Bits(expected)
         <<','<<s[p].xx<<','<<s[p].yy<<','<<s[p].zz<<','<<s[p].xy<<','<<s[p].yz<<','<<s[p].xz<<','<<kp[p]<<','<<xy[p].x<<','<<xy[p].y<<','<<z[p]<<','<<J[p]<<','<<v[0].w<<','<<ok<<'\n';
    }
    csv.flush();Need(bool(csv)&&ok,"NULL-state literal density/Code mismatch");
  }
  void row(std::ostream& csv,const char* test,bool cor,bool written,unsigned bad,unsigned expectedBad,float lo,float hi,const std::array<double,N>& preview={}){
    const auto c=code.get();const auto J=j.get(),Jn=jn.get(),th=theta.get();
    std::array<float4,N> v{};if(written)v=vel.get(); // No velout read before a successful wrapper launch.
    bool ok=bad==expectedBad;if(written)ok=ok&&Bits(v[0].w)==Bits(RHO0);
    for(unsigned p=NB;p<N;p++){
      const bool valid=std::isfinite(J[p])&&J[p]>1.-double(N0);
      const double rho=valid?double(RHOW)+(double(RHO0)-double(RHOW))/J[p]:std::numeric_limits<double>::quiet_NaN();
      const float expected=float(rho);bool pass=ok;
      if(written){
        const bool out=(!valid||!std::isfinite(rho)||rho<=0||rho<lo||rho>hi||!std::isfinite(expected)||expected<=0);
        pass=pass&&(bool(CODE_IsOutRhop(c[p]))==out);
        if(valid)pass=pass&&Bits(v[p].w)==Bits(expected);
      }
      if(cor&&valid)pass=pass&&DoubleBits(preview[p],J[p]);
      csv<<test<<','<<(cor?"cor":"pre")<<','<<p<<','<<written<<','<<uint32_t(c[p])<<','<<Jn[p]<<','<<J[p]<<','<<th[p]<<',';
      if(cor)csv<<preview[p];csv<<','<<input[p].w<<','<<lo<<','<<hi<<','<<bad<<',';
      if(written){csv<<v[p].w<<','<<Bits(v[p].w)<<',';if(valid)csv<<rho<<','<<expected<<','<<Bits(expected);else csv<<",,";csv<<','<<v[0].w;}
      else csv<<",,,,,";
      csv<<','<<pass<<'\n';ok=ok&&pass;count.rows++;
    }
    count.records++;if(expectedBad<N)count.rejected++;csv.flush();Need(bool(csv)&&ok,"GPU cache/J-stage/Code identity failed; see written rows");
  }
  std::array<double,N> preview()const{auto a=jn.get();const auto h=j.get(),th=theta.get();for(unsigned p=NB;p<N;p++)a[p]+=DT*h[p]*th[p];return a;}
};
static void Completion(const fs::path& out,const Counts& c,bool passed,const std::string& error=""){
  if(out.empty()||!fs::is_directory(out)||fs::exists(out/"completion.json"))return;
  std::ofstream f(out/"completion.json");f<<"{\"stage\":\"upl_density_cache_gpu_r1\",\"passed\":"<<(passed?"true":"false")
#ifdef UPL_DENSITY_CACHE_LEGACY_ONLY
    <<",\"legacy_only\":true"
#else
    <<",\"legacy_only\":false"
#endif
    <<",\"fixture_particles\":4,\"fixed_slots\":1,\"soil_slots\":3,\"pre_calls\":"<<c.pre<<",\"cor_calls\":"<<c.cor<<",\"J_commit_calls\":"<<c.j
    <<",\"ON_stage_records\":"<<c.records<<",\"ON_soil_rows\":"<<c.rows<<",\"expected_J_rejections\":"<<c.rejected
    <<",\"physical_trajectory_steps\":0,\"private_stage_only\":true,\"spatial_solver_run\":false,\"force_or_Arc_producer_tested\":false,\"sort_or_periodic_tested\":false,\"physical_acceptance\":false,\"failure\":"<<std::quoted(error)<<"}\n";
  f.flush();Need(bool(f),"completion write failed");
}
int main(int argc,char** argv){
  fs::path out;Counts terminal;
  try{
    Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_DIRECTORY");
    out=argv[2];Need(!fs::exists(out),"Refusing existing output");Need(fs::create_directories(out),"Cannot create fresh output");
    Cu(cudaSetDevice(0));StSoilCte soil{};soil.ModulusK=16.f;soil.ModulusG=8.f;soil.ModulusE=20.f;soil.coh=1.e6f;soil.Porosity=N0;soil.PoreWaterRho=RHOW;
    cusphs::CteInteractionUpTStep(&soil,0,0);Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());Stage q(terminal);
    std::ofstream nullcsv(out/"null.csv"),bin(out/"null_stage.bin",std::ios::binary);
    nullcsv<<std::setprecision(17)<<"test,phase,slot,CODE,vx,vy,vz,w,w_bits,literal_w,literal_bits,sxx,syy,szz,sxy,syz,sxz,kplastic,dx,dy,dz,J,wall_w,passed\n";
    Raw(bin,uint32_t(0x4a4e5531));Raw(bin,uint32_t(N));Raw(bin,uint32_t(4));
    for(bool observer:{false,true}){
      q.reset({1.125,1.,1.,1.},{16.,.25,.25,.25},RHO0,true);
      if(observer)Need(q.commit(false)==N,"NULL observer predictor rejected");
      q.update(false,false);q.nullrow(nullcsv,observer?"observer":"OFF",false);q.snapshot(bin);
      q.theta.put({16.,-.25,-.25,-.25});q.update(true,false);
      if(observer)Need(q.commit(true)==N,"NULL observer corrector rejected");
      q.nullrow(nullcsv,observer?"observer":"OFF",true);q.snapshot(bin);
    }
    nullcsv.flush();bin.flush();Need(bool(nullcsv)&&bool(bin),"NULL export failed");
#ifndef UPL_DENSITY_CACHE_LEGACY_ONLY
    std::ofstream csv(out/"cache.csv");csv<<std::setprecision(17)<<"test,phase,slot,density_stage_written,CODE,Jn,committed_J,theta,preview_Jfull,input_legacy_w,range_min,range_max,invalid_index,w,w_bits,physical_rho_double,expected_w,expected_bits,wall_w,passed\n";
    for(unsigned test=0;test<2;test++){
      const char* name=test?"nonuniform":"J068";
      q.reset(test?std::array<double,N>{1.125,.75,1.,1.125}:std::array<double,N>{1.125,.68,.68,.68},test?std::array<double,N>{16.,-1.5,0.,.5}:std::array<double,N>{16.,0.,0.,0.},float(double(RHO0)/.68));
      auto bad=q.commit(false);Need(bad==N,"Valid predictor J rejected");q.update(false,true);q.row(csv,name,false,true,bad,N,700,3000);
      q.theta.put(test?std::array<double,N>{16.,.125,0.,-.25}:std::array<double,N>{16.,0.,0.,0.});
      const auto preview=q.preview();q.update(true,true);bad=q.commit(true);q.row(csv,name,true,true,bad,N,700,3000,preview);
    }
    for(bool cor:{false,true})for(double t:{-4.,8.}){
      const char* name=t<0?"range_high":"range_low";q.reset({1.125,1.,1.,1.},{16.,cor?0.:t,cor?0.:t,cor?0.:t},RHO0);
      auto bad=q.commit(false);Need(bad==N,"Range predictor J rejected");q.update(false,true,1800,2400);
      q.row(csv,cor?"range_setup":name,false,true,bad,N,1800,2400);
      if(cor){const double tc=t<0?-2.:4.;q.theta.put({16.,tc,tc,tc});const auto preview=q.preview();q.update(true,true,1800,2400);bad=q.commit(true);q.row(csv,name,true,true,bad,N,1800,2400,preview);}
    }
    for(bool cor:{false,true})for(unsigned b=0;b<3;b++){
      const char* name=b==0?"bad_nan":b==1?"bad_inf":"bad_solid";
      const double th=b==0?std::numeric_limits<double>::quiet_NaN():b==1?std::numeric_limits<double>::infinity():((1.-double(N0))-1.)/(cor?DT:DT*.5);
      q.reset({1.125,1.,1.,1.},{16.,cor?0.:th,0.,0.},RHO0);
      auto bad=q.commit(false);
      if(!cor)q.row(csv,name,false,false,bad,1,700,3000);
      else{
        Need(bad==N,"Bad-corrector setup rejected");q.update(false,true);q.row(csv,"bad_setup",false,true,bad,N,700,3000);
        q.theta.put({16.,th,0.,0.});const auto preview=q.preview();q.update(true,true);bad=q.commit(true);q.row(csv,name,true,true,bad,1,700,3000,preview);
      }
    }
#endif
    terminal=q.count;Completion(out,terminal,true);std::cout<<"GPU stage diagnostic passed; pre="<<terminal.pre<<" cor="<<terminal.cor<<" J="<<terminal.j<<'\n';return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';Completion(out,terminal,false,e.what());return 1;}
  catch(const char* e){std::cerr<<e<<'\n';Completion(out,terminal,false,e);return 1;}
}
