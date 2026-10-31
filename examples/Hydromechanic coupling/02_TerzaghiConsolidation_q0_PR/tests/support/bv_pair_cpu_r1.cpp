// Real CPU fused-interaction consumer contract, not an MLS or integrated case.
#include "JSphCpuSingle.h"
#include "FunSphKernel.h"
#include "JDsDcellDef.h"
#include "JAppInfo.h"
#include <omp.h>
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
JAppInfo AppInfo("BoundaryVelocityPairCpu","r1","01-11-2026");
namespace fs=std::filesystem;
static void Check(bool ok,const char* m){if(!ok)throw std::runtime_error(m);}
struct Row{
  unsigned dim,slip;std::string trial;bool auxiliary,passed;
  float auxx,auxz,soilvz,gz,Lxz,Lzz,ar,pw,visc;
  tfloat3 ace;tsymatrix3f stress;
};
static bool Near(double a,double b,unsigned group){
  const double floor=(group==0?20.:(group==1?2000.:.02));
  return std::isfinite(a)&&std::isfinite(b)&&fabs(a-b)<=floor+2e-5*fabs(b);
}
static bool SameNonShear(const Row& a,const Row& b){
  const auto x=a.stress,y=b.stress;
  return a.ar==b.ar&&a.pw==b.pw&&a.visc==b.visc&&a.ace==b.ace
    &&x.xx==y.xx&&x.yy==y.yy&&x.zz==y.zz&&x.xy==y.xy&&x.yz==y.yz;
}
class Pair:public JSphCpuSingle{
  byte modes[2]={BMODE_MDBC2,BMODE_DBC};
  tfloat3 tangents[2]={},auxiliary[2]={};
public:
  Pair(){
    OmpThreads=1;omp_set_num_threads(1);Np=2;Npb=1;NpbOk=0;
    TKernel=KERNEL_Wendland;TVisco=VISCO_Artificial;TDensity=DDT_None;
    FtMode=FTMODE_None;UseDEM=false;Symmetry=false;ArtificialStress=false;
    TBoundary=BC_MDBC;TMdbc2=MDBC2_Std;
    HydroMech=true;HydroMechDrainage=false;HydroMechTopLoadMode=HMLOAD_None;
    SoilStressRateGradCorr=true;PoreCompressionGradCorr=true;PoreCompressionSourceMode=0;
    SoilCte={};SoilCte.ModulusK=16;SoilCte.ModulusG=8;
    SoilCte.PoreWaterBulkModulus=128;SoilCte.Porosity=.5f;SoilCte.PoreWaterRho=1;
    Dp=.125;KernelH=.25f;KernelSize=.5f;KernelSize2=.25f;
    MassFluid=MassBound=1;RhopZero=2;Cs0=4;Eta2=(.1f*KernelH)*(.1f*KernelH);
    Gravity=TFloat3(0);Visco=.125f;ViscoBoundFactor=1;
    BoundModec=modes;TangenVelc=tangents;
  }
  ~Pair(){BoundModec=nullptr;TangenVelc=nullptr;BoundDerivativeVelc=nullptr;}
  Row run(unsigned dim,unsigned slip,const char* trial,bool useaux,float ax,float az,float vz){
    Simulate2D=dim==2;SlipMode=TpSlipMode(slip);modes[0]=(slip==1?BMODE_DBC:BMODE_MDBC2);
    CSP=CteSphNull();CSP.simulate2d=Simulate2D;CSP.tkernel=TKernel;
    CSP.kwend=fsph::GetKernelWendland_Ctes(Simulate2D,KernelH);CSP.kernelh=KernelH;
    CSP.massbound=MassBound;CSP.massfluid=MassFluid;CSP.rhopzero=RhopZero;
    auxiliary[0]=TFloat3(ax,0,az);BoundDerivativeVelc=(useaux?auxiliary:nullptr);
    const unsigned begin[4]={0,1,1,2},dcell[2]={0,0},id[2]={0,1};
    const unsigned fst[2]={FST_Boundary,FST_Inner};
    const typecode code[2]={CODE_TYPE_FIXED,CODE_TYPE_FLUID};
    const tdouble3 pos[2]={TDouble3(.25),TDouble3(.25,.25,.375)};
    const tfloat4 velocity[2]={TFloat4(0,0,0,2),TFloat4(0,0,vz,2)};
    const float pressure[2]={0,0},pore[2]={0,0};float rate[2]={0,0},ar[2]={0,0};
    tfloat3 ace[2]={},normal[2]={};tsymatrix3d sigma[2]={};tsymatrix3f stress[2]={};
    tmatrix3d I={};I.a11=I.a22=I.a33=1;tmatrix3d corr[2]={I,I};
    const StDivDataCpu dvd=MakeDivDataCpu(1,TUint3(1,1,1),TUint3(0),begin,.5f,DCEL_GetCode(1,1,1),TDouble3(0));
    const auto parms=StInterparmsc(2,1,0,dvd,dcell,pos,velocity,id,code,pressure,pore,rate,fst,normal,nullptr,corr,
      ar,ace,nullptr,SHIFT_None,nullptr,nullptr,nullptr,sigma,stress,nullptr);
    StInterResultc result={0};Interaction_Forces_ct(parms,result);
    Row r={dim,slip,trial,useaux,true,ax,az,vz,
      fsph::GetKernelWendland_Fac(CSP.kwend,.25f,.125f*.125f)*.125f,0,0,ar[1],rate[1],result.viscdt,ace[1],stress[1]};
    r.Lxz=(useaux?ax:0)*.5f*r.gz;r.Lzz=((useaux?az:0)-vz)*.5f*r.gz;
    const auto s=r.stress;const double lambda=16.-16./3.;
    const double expected[6]={lambda*r.Lzz,lambda*r.Lzz,(16.+32./3.)*r.Lzz,0,0,8.*r.Lxz};
    const double actual[6]={s.xx,s.yy,s.zz,s.xy,s.yz,s.xz};
    for(unsigned j=0;j<6;j++)r.passed=r.passed&&(expected[j]==0?actual[j]==0:Near(actual[j],expected[j],0));
    r.passed=r.passed&&Near(r.ar,-2.*r.Lzz,2)&&Near(r.pw,-256.*r.Lzz,1);
    const double trace=(double(s.xx)+s.yy+s.zz)/48.;
    r.passed=r.passed&&fabs(double(r.pw)+256.*trace)<=2e-5*(std::max)(1.,fabs(double(r.pw)));
    if(vz==0&&az==0)r.passed=r.passed&&r.ar==0&&r.pw==0&&r.visc==0&&r.ace==TFloat3(0);
    if(r.Lxz!=0)r.passed=r.passed&&s.xz!=0&&double(s.xz)*r.Lxz>0;
    if(r.Lzz!=0)r.passed=r.passed&&r.ar!=0&&r.pw!=0;
    Check(ar[0]==0&&rate[0]==0&&ace[0]==TFloat3(0),"Unexpected wall-receiver write");
    return r;
  }
};
int main(int argc,char** argv){
  try{
    if(argc==1||std::string(argv[1])=="--help"){
      std::cout<<"bv_pair_cpu_r1 --out NEW_DIRECTORY\nActual CPU fused interaction; no MLS/integration.\n";return 0;}
    Check(argc==3&&std::string(argv[1])=="--out","Expected --out NEW_DIRECTORY");
    const fs::path out=argv[2];Check(!fs::exists(out),"Refusing overwrite");fs::create_directories(out);
    std::vector<Row> rows;bool passed=true;
    for(unsigned dim:{2u,3u})for(unsigned slip:{1u,2u,3u}){
      Pair p;std::vector<Row> r;
      r.push_back(p.run(dim,slip,"aux_off",false,0,0,0));r.push_back(p.run(dim,slip,"aux_zero",true,0,0,0));
      r.push_back(p.run(dim,slip,"aux_shear",true,.5f,0,0));r.push_back(p.run(dim,slip,"aux_shear_negative",true,-.5f,0,0));
      r.push_back(p.run(dim,slip,"aux_normal",true,0,.5f,0));r.push_back(p.run(dim,slip,"aux_normal_shear",true,.5f,.5f,0));
      r.push_back(p.run(dim,slip,"approach_aux0",true,0,0,-.25f));r.push_back(p.run(dim,slip,"approach_aux_shear",true,.5f,0,-.25f));
      r.push_back(p.run(dim,slip,"recede_aux0",true,0,0,.25f));r.push_back(p.run(dim,slip,"recede_aux_shear",true,.5f,0,.25f));
      r.push_back(p.run(dim,slip,"aux_normal_negative",true,0,-.5f,0));r.push_back(p.run(dim,slip,"aux_normal_shear_negative",true,.5f,-.5f,0));
      r[3].passed=r[3].passed&&r[3].stress.xz==-r[2].stress.xz;
      r[5].passed=r[5].passed&&SameNonShear(r[4],r[5]);
      r[7].passed=r[7].passed&&SameNonShear(r[6],r[7])&&r[6].ace.z!=0&&r[6].visc==0;
      r[9].passed=r[9].passed&&SameNonShear(r[8],r[9])&&r[8].ace.z==0&&r[8].visc>0;
      r[11].passed=r[11].passed&&SameNonShear(r[10],r[11]);
      for(const auto& x:r){passed=passed&&x.passed;rows.push_back(x);}
    }
    std::ofstream csv(out/"pairs.csv");csv<<std::setprecision(17)
      <<"dimension,slip,trial,auxiliary,aux_x,aux_z,soil_vz,g_z,Lxz_reference,Lzz_reference,soil_ar,soil_pore_rate,soil_viscdt,ace_x,ace_y,ace_z,rsigma_xx,rsigma_yy,rsigma_zz,rsigma_xy,rsigma_yz,rsigma_xz,passed\n";
    for(const auto& r:rows){const auto s=r.stress;csv<<r.dim<<','<<r.slip<<','<<r.trial<<','<<r.auxiliary<<','<<r.auxx<<','<<r.auxz<<','<<r.soilvz<<','
      <<r.gz<<','<<r.Lxz<<','<<r.Lzz<<','<<r.ar<<','<<r.pw<<','<<r.visc<<','<<r.ace.x<<','<<r.ace.y<<','<<r.ace.z<<','
      <<s.xx<<','<<s.yy<<','<<s.zz<<','<<s.xy<<','<<s.yz<<','<<s.xz<<','<<r.passed<<'\n';}
    csv.flush();Check(bool(csv),"CSV write failed");
    std::ofstream done(out/"completion.json");done<<"{\"diagnostic_completed\":true,\"passed\":"<<(passed?"true":"false")
      <<",\"kernel_calls\":"<<rows.size()<<",\"particles\":2,\"time_integrated\":false,\"mls_tested\":false,\"physical_acceptance\":false}\n";
    done.flush();Check(bool(done),"Completion write failed");
    std::cout<<"Actual CPU calls="<<rows.size()<<" passed="<<passed<<'\n';return passed?0:2;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"CPU fixture failed; no acceptance\n";return 1;}
}
