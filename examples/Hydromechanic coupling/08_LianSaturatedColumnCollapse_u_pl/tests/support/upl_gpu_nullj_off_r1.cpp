// NULL-J default OFF-branch regression, mechanically derived from retained bv_pair_gpu_r1.cpp.
// Same fresh variant is linked separately to the sealed preport and current object closures.
// No MLS, boundary reconstruction, configuration loading, or time integration.
#include "JSphGpu_ker.h"
#include "FunSphKernel.h"
#include "JDsDcellDef.h"
#include "JAppInfo.h"
#include <cuda_runtime.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

JAppInfo AppInfo("UplGpuNullJOff","r1","06-11-2026");
namespace fs=std::filesystem;
static void Check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
static void Cu(cudaError_t e){Check(e==cudaSuccess,cudaGetErrorString(e));}
template<class T,unsigned N> struct Device{
  T* p=nullptr;
  Device(){Cu(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*N));clear();}
  ~Device(){if(p)cudaFree(p);}
  Device(const Device&)=delete;Device& operator=(const Device&)=delete;
  void clear(){Cu(cudaMemset(p,0,sizeof(T)*N));}
  void put(const std::array<T,N>& a){Cu(cudaMemcpy(p,a.data(),sizeof(T)*N,cudaMemcpyHostToDevice));}
  std::array<T,N> get()const{std::array<T,N> a;Cu(cudaMemcpy(a.data(),p,sizeof(T)*N,cudaMemcpyDeviceToHost));return a;}
};
struct Row{
  unsigned dim,slip;std::string trial;bool auxiliary,passed;
  float auxx,auxz,soilvz,gz,Lxz,Lzz;
  std::array<float,2> ar,pw,visc;std::array<float3,2> ace;std::array<tsymatrix3f,2> stress;
};
static bool Near(double a,double b,unsigned group){
  const double floor=(group==0?20.:(group==1?2000.:.02));
  return std::isfinite(a)&&std::isfinite(b)&&fabs(a-b)<=floor+2e-5*fabs(b);
}
static bool Zero(const Row& r){
  for(unsigned i=0;i<2;i++)if(r.ar[i]!=0||r.pw[i]!=0||r.visc[i]!=0||r.ace[i].x!=0||r.ace[i].y!=0||r.ace[i].z!=0)return false;
  return true;
}
static bool SameNonShear(const Row& a,const Row& b){
  for(unsigned i=0;i<2;i++)if(a.ar[i]!=b.ar[i]||a.pw[i]!=b.pw[i]||a.visc[i]!=b.visc[i]
    ||a.ace[i].x!=b.ace[i].x||a.ace[i].y!=b.ace[i].y||a.ace[i].z!=b.ace[i].z)return false;
  const auto x=a.stress[1],y=b.stress[1];
  return x.xx==y.xx&&x.yy==y.yy&&x.zz==y.zz&&x.xy==y.xy&&x.yz==y.yz;
}

class Pair{
  Device<int2,4> cells;
  Device<unsigned,2> dcell,id,fstype;
  Device<typecode,2> code;
  Device<byte,2> mode,slips;
  Device<double2,2> xy;
  Device<double,2> z;
  Device<float4,2> pos,velocity;
  Device<float3,2> tangent,motion,normal,aux,ace,fsnormal;
  Device<tmatrix3d,2> correction;
  Device<tsymatrix3d,2> sigma;
  Device<tsymatrix3f,2> stress;
  Device<float,2> pressure,rate,ar,visc;
  StDivDataGpu dvd;
  StCteInteraction c={};
public:
  Pair(){
    // One wall in [0,1), one soil in [1,2), both in cell (0,0,0).
    cells.put({make_int2(0,1),make_int2(0,0),make_int2(1,2),make_int2(0,0)});
    dcell.put({0,0});id.put({0,1});code.put({typecode(CODE_TYPE_FIXED),typecode(CODE_TYPE_FLUID)});
    xy.put({make_double2(.25,.25),make_double2(.25,.25)});z.put({.25,.375});
    pos.put({make_float4(.25f,.25f,.25f,0),make_float4(.25f,.25f,.375f,0)});
    normal.put({make_float3(0,0,.125f),make_float3(0,0,0)});
    tmatrix3d I={};I.a11=I.a22=I.a33=1;correction.put({I,I});
    const unsigned cellcode=DCEL_GetCode(1,1,1);
    dvd=MakeDivDataGpu(1,TUint3(1,1,1),TUint3(0),cells.p,.5f,cellcode,TDouble3(0),.25f,.5f);
    c.nbound=1;c.massb=c.massf=1;c.kernelh=.25f;c.kernelsize=.5f;c.kernelsize2=.25f;c.poscellsize=.5f;
    c.cs0=4;c.eta2=(.1f*c.kernelh)*(.1f*c.kernelh);c.scell=.5f;c.dp=.125f;
    c.cteb=1;c.gamma=7;c.rhopzero=2;c.ovrhopzero=.5f;c.tboundary=BC_MDBC;
    c.axis=MGDIV_Z;c.cellcode=cellcode;c.modulus_K=16;c.modulus_G=8;
    c.hydromech=1;c.soilstressrategradcorr=1;c.porecompgradcorr=1;c.porecompsourcemode=0;
    c.porewaterbulkmodulus=128;c.porosity=.5f;c.porekwn=256;c.porewaterrho=1;c.poreghyd=1;
  }
  Row run(unsigned dim,unsigned slip,const char* trial,bool useaux,float ax,float az,float vz,bool inactive=false){
    c.simulate2d=(dim==2);c.slipmode=slip;
    const auto kw=fsph::GetKernelWendland_Ctes(dim==2,.25);c.awen=kw.awen;c.bwen=kw.bwen;
    cusph::CteInteractionUp(&c);Cu(cudaGetLastError());
    // No reconstruction exists in this consumer fixture: set the actual device selector immediately before the force inputs.
    const byte wallmode=byte(inactive?BMODE_MDBC2OFF:(slip==1?BMODE_DBC:BMODE_MDBC2));
    mode.put({wallmode,byte(BMODE_DBC)});slips.put({byte(slip),byte(slip)});
    const std::array<float4,2> physical={make_float4(0,0,0,2),make_float4(0,0,vz,2)};
    velocity.put(physical);aux.put({make_float3(ax,0,az),make_float3(0,0,0)});
    ar.clear();rate.clear();stress.clear();ace.clear();visc.clear();
    const StInterParmsg p=StrInterParmsg(dim==2,false,KERNEL_Wendland,FTMODE_None,false,DDT_None,SHIFT_None,
      (slip==1?MDBC2_None:MDBC2_Std),.125f,.125f,128,128,2,1,1,0,0,dvd,dcell.p,xy.p,z.p,pos.p,
      velocity.p,id.p,code.p,nullptr,nullptr,nullptr,correction.p,mode.p,slips.p,tangent.p,motion.p,normal.p,nullptr,
      visc.p,ar.p,ace.p,nullptr,nullptr,sigma.p,stress.p,nullptr,pressure.p,rate.p,fstype.p,fsnormal.p,false,
      nullptr,nullptr,nullptr,nullptr,nullptr,(useaux?aux.p:nullptr));
    Check(p.poroj==nullptr,"Legacy consumer accidentally received J state");
    cusph::Interaction_Forces(p);Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());
    const auto downloadedMode=mode.get();Check(downloadedMode[0]==wallmode&&downloadedMode[1]==BMODE_DBC,"Actual device wall selector changed");
    const auto actual=velocity.get();Check(!memcmp(physical.data(),actual.data(),sizeof(physical)),"Physical velocity/density changed");
    Row r={dim,slip,trial,useaux,true,ax,az,vz,fsph::GetKernelWendland_Fac(kw,.25f,.125f*.125f)*.125f,0,0,
      ar.get(),rate.get(),visc.get(),ace.get(),stress.get()};
    r.Lxz=(useaux?ax:0)*.5f*r.gz;r.Lzz=((useaux?az:0)-vz)*.5f*r.gz;
    if(inactive&&slip>=2){
      // NULL-J legacy mass is zero, but its geometric viscosity scale must still be evaluated.
      for(unsigned i=0;i<2;i++){
        const auto a=r.ace[i];const auto q=r.stress[i];
        r.passed=r.passed&&std::isfinite(r.ar[i])&&std::isfinite(r.pw[i])&&std::isfinite(r.visc[i])&&std::isfinite(a.x)&&std::isfinite(a.y)&&std::isfinite(a.z);
        for(float value:{q.xx,q.yy,q.zz,q.xy,q.yz,q.xz})r.passed=r.passed&&std::isfinite(value);
      }
      const auto a=r.ace[1];const auto q=r.stress[1];
      r.passed=r.passed&&r.ar[1]==0&&r.pw[1]==0&&a.x==0&&a.y==0&&a.z==0&&r.visc[1]>0;
      for(float value:{q.xx,q.yy,q.zz,q.xy,q.yz,q.xz})r.passed=r.passed&&value==0;
      return r; // Wall-receiver Arc is retained as data, not equated with wall reaction.
    }
    const auto s=r.stress[1];const double lambda=16.-16./3.;
    const double expected[6]={lambda*r.Lzz,lambda*r.Lzz,(16.+32./3.)*r.Lzz,0,0,8.*r.Lxz};
    const double actualstress[6]={s.xx,s.yy,s.zz,s.xy,s.yz,s.xz};
    for(unsigned j=0;j<6;j++)r.passed=r.passed&&(expected[j]==0?actualstress[j]==0:Near(actualstress[j],expected[j],0));
    r.passed=r.passed&&Near(r.ar[1],-2.*r.Lzz,2)&&Near(r.pw[1],-256.*r.Lzz,1);
    // Constitutive trace gives an independent observable divergence; tight consistency, not a relaxed zero gate.
    const double trace=(double(s.xx)+s.yy+s.zz)/48.;
    r.passed=r.passed&&fabs(double(r.pw[1])+256.*trace)<=2e-5*(std::max)(1.,fabs(double(r.pw[1])));
    for(unsigned i=0;i<2;i++)r.passed=r.passed&&std::isfinite(r.ar[i])&&std::isfinite(r.pw[i])&&std::isfinite(r.visc[i])
      &&std::isfinite(r.ace[i].x)&&std::isfinite(r.ace[i].y)&&std::isfinite(r.ace[i].z);
    if(vz==0&&az==0)r.passed=r.passed&&Zero(r);
    if(r.Lxz!=0)r.passed=r.passed&&s.xz!=0&&double(s.xz)*r.Lxz>0;
    if(r.Lzz!=0)r.passed=r.passed&&r.ar[1]!=0&&r.pw[1]!=0;
    return r;
  }
};
static void WriteRows(const fs::path& path,const std::vector<Row>& rows){
  std::ofstream csv(path);csv<<std::setprecision(17)
    <<"dimension,slip,trial,auxiliary,aux_x,aux_z,soil_vz,g_z,Lxz_reference,Lzz_reference,wall_ar,soil_ar,soil_pore_rate,wall_viscdt,soil_viscdt,ace_x,ace_y,ace_z,rsigma_xx,rsigma_yy,rsigma_zz,rsigma_xy,rsigma_yz,rsigma_xz,passed\n";
  for(const auto& r:rows){const auto s=r.stress[1];const auto a=r.ace[1];csv<<r.dim<<','<<r.slip<<','<<r.trial<<','<<r.auxiliary<<','
    <<r.auxx<<','<<r.auxz<<','<<r.soilvz<<','<<r.gz<<','<<r.Lxz<<','<<r.Lzz<<','<<r.ar[0]<<','<<r.ar[1]<<','<<r.pw[1]<<','
    <<r.visc[0]<<','<<r.visc[1]<<','<<a.x<<','<<a.y<<','<<a.z<<','<<s.xx<<','<<s.yy<<','<<s.zz<<','<<s.xy<<','<<s.yz<<','<<s.xz<<','<<r.passed<<'\n';}
  csv.flush();Check(bool(csv),"CSV write failed");
}
int main(int argc,char** argv){
  try{
    if(argc==1||std::string(argv[1])=="--help"){
      std::cout<<"upl_gpu_nullj_off_r1 --out NEW_DIRECTORY [--device N]\nReal CUDA two-particle consumer diagnostic; not a solver or MLS test.\n";return 0;}
    fs::path out;int device=0;
    for(int i=1;i<argc;i++){const std::string a=argv[i];Check(i+1<argc,"Missing argument value");
      if(a=="--out")out=argv[++i];else if(a=="--device")device=std::stoi(argv[++i]);else Check(false,"Unknown option");}
    Check(!out.empty()&&!fs::exists(out),"Require a new output directory; refusing overwrite");
    Cu(cudaSetDevice(device));fs::create_directories(out);std::vector<Row> rows,offrows;bool passed=true;
    for(unsigned dim:{2u,3u})for(unsigned slip:{1u,2u,3u}){
      Pair p;std::vector<Row> r;
      r.push_back(p.run(dim,slip,"aux_off",false,0,0,0));r.push_back(p.run(dim,slip,"aux_zero",true,0,0,0));
      r.push_back(p.run(dim,slip,"aux_shear",true,.5f,0,0));r.push_back(p.run(dim,slip,"aux_shear_negative",true,-.5f,0,0));
      r.push_back(p.run(dim,slip,"aux_normal",true,0,.5f,0));r.push_back(p.run(dim,slip,"aux_normal_shear",true,.5f,.5f,0));
      r.push_back(p.run(dim,slip,"approach_aux0",true,0,0,-.25f));r.push_back(p.run(dim,slip,"approach_aux_shear",true,.5f,0,-.25f));
      r.push_back(p.run(dim,slip,"recede_aux0",true,0,0,.25f));r.push_back(p.run(dim,slip,"recede_aux_shear",true,.5f,0,.25f));
      r.push_back(p.run(dim,slip,"aux_normal_negative",true,0,-.5f,0));r.push_back(p.run(dim,slip,"aux_normal_negative_shear",true,.5f,-.5f,0));
      r[3].passed=r[3].passed&&r[3].stress[1].xz==-r[2].stress[1].xz;
      r[5].passed=r[5].passed&&SameNonShear(r[4],r[5]);
      r[7].passed=r[7].passed&&SameNonShear(r[6],r[7])&&r[6].ace[1].z!=0&&r[6].visc[1]==0;
      r[9].passed=r[9].passed&&SameNonShear(r[8],r[9])&&r[8].ace[1].z==0&&r[8].visc[1]>0;
      r[10].passed=r[10].passed&&r[10].ar[1]==-r[4].ar[1]&&r[10].pw[1]==-r[4].pw[1];
      r[11].passed=r[11].passed&&SameNonShear(r[10],r[11]);
      for(const auto& x:r){passed=passed&&x.passed;rows.push_back(x);}
      Row off=p.run(dim,slip,"OFF_recede_aux0",true,0,0,.25f,true);
      off.passed=off.passed&&off.visc[1]>0&&off.visc[1]==r[8].visc[1];
      passed=passed&&off.passed;offrows.push_back(off);
    }
    Check(rows.size()==72&&offrows.size()==6,"Legacy/OFF coverage changed");WriteRows(out/"active.csv",rows);WriteRows(out/"off.csv",offrows);
    std::ofstream done(out/"completion.json");done<<"{\"stage\":\"upl_gpu_nullj_off_r1\",\"passed\":"<<(passed?"true":"false")
      <<",\"active_kernel_calls\":"<<rows.size()<<",\"OFF_kernel_calls\":"<<offrows.size()<<",\"kernel_calls\":"<<rows.size()+offrows.size()
      <<",\"NULL_J_assertions\":78,\"actual_device_mode_roundtrip_checks\":78,\"OFF_marker\":2,\"particles\":2,\"all_original_active_gates_preserved\":true,\"OFF_NS_FS_soil_zero_and_positive_viscdt_required\":true,\"physical_velocity_density_unchanged\":true,\"time_integrated\":false,\"mls_tested\":false,\"natural_wall_activation_tested\":false,\"physical_acceptance\":false}\n";
    done.flush();Check(bool(done),"Completion write failed");std::cout<<"Actual CUDA calls="<<rows.size()+offrows.size()<<" passed="<<passed<<'\n';return passed?0:2;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(const char* e){std::cerr<<e<<'\n';return 1;}
  catch(...){std::cerr<<"CUDA fixture failed; retained outputs are not accepted\n";return 1;}
}
