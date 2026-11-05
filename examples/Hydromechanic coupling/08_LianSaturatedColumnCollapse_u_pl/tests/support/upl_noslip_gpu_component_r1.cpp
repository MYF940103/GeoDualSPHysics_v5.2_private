// Actual GPU wall wrappers on the retained synthetic 81-fluid/2-fixed patch.
// No solver/host admission, force kernel, Darcy-rate repeat, integration or CPU-ID equivalence.
#include "JSphGpu_ker.h"
#include "FunSphKernel.h"
#include "FunctionsMath.h"
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
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("UplNoSlipGpuComponent","r1","06-11-2026");
namespace fs=std::filesystem;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static void Cu(cudaError_t e){Need(e==cudaSuccess,cudaGetErrorString(e));}
template<class T>struct Device{T* p=nullptr;explicit Device(unsigned n){Cu(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*n));}~Device(){if(p)cudaFree(p);}Device(const Device&)=delete;Device& operator=(const Device&)=delete;};
template<class T>static void Up(T* p,const std::vector<T>& a){Cu(cudaMemcpy(p,a.data(),a.size()*sizeof(T),cudaMemcpyHostToDevice));}
template<class T>static std::vector<T> Down(const T* p,unsigned n){std::vector<T>a(n);Cu(cudaMemcpy(a.data(),p,n*sizeof(T),cudaMemcpyDeviceToHost));return a;}
template<class T>static bool Same(const std::vector<T>& a,const std::vector<T>& b){return a.size()==b.size()&&(a.empty()||!memcmp(a.data(),b.data(),a.size()*sizeof(T)));}
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static double Norm(tdouble3 a){return sqrt(Dot(a,a));}
static tdouble3 Vec(float3 a){return TDouble3(a.x,a.y,a.z);}
static double Inf(tmatrix3d a){return (std::max)({fabs(a.a11)+fabs(a.a12)+fabs(a.a13),fabs(a.a21)+fabs(a.a22)+fabs(a.a23),fabs(a.a31)+fabs(a.a32)+fabs(a.a33)});}
struct Counts{unsigned cases=0,rows=0,noslip=0,freeslip=0,offgrid=0;double maxratio=0,minwrongsign=DBL_MAX,minmissing=DBL_MAX;};
class Patch{
  static constexpr unsigned Fixed=2,Fluid=81,N=Fixed+Fluid,Cap=N+2;
  static constexpr double Dp=.125,V0=Dp*Dp,Solid=.75;
  TpKernel tk;float h=1.8f*float(Dp);StCteSph sph=CteSphNull();StCteInteraction ct={};StDivDataGpu dvd;
  Device<int2> cells{4};Device<unsigned> invalid{2};Device<typecode> codeg{Cap};Device<byte> modeg{Cap},slipg{Cap};
  Device<double2> xyg{Cap};Device<double> zg{Cap},jg{Cap},thg{Cap};Device<float> pg{Cap};Device<float4> vg{Cap};
  Device<tmatrix3d> cg{Cap};Device<tsymatrix3d> sg{Cap};Device<float3> ag{Cap},bng{Cap},dvg{Cap},tvg{Cap};
  std::vector<double2> xy=std::vector<double2>(Cap);std::vector<double> z=std::vector<double>(Cap),j=std::vector<double>(Cap,1.25),theta=std::vector<double>(Cap,.5);
  std::vector<float> p=std::vector<float>(Cap,12345.f);std::vector<float4> vel=std::vector<float4>(Cap,make_float4(17,19,23,29));
  std::vector<float3> ace=std::vector<float3>(Cap,make_float3(31,37,41)),bn=std::vector<float3>(Cap),originalbn;
  std::vector<typecode> code=std::vector<typecode>(Cap,CODE_TYPE_FIXED);std::vector<byte> mode=std::vector<byte>(Cap,0x5a),slips=std::vector<byte>(Cap,0x5c);
  std::vector<tmatrix3d> c=std::vector<tmatrix3d>(Cap,TMatrix3d(3));std::vector<tsymatrix3d> sigma=std::vector<tsymatrix3d>(Cap,TSymMatrix3d(43,47,53,59,61,67));
  const char* Name()const{return tk==KERNEL_Wendland?"Wendland":"Cubic";}
  tdouble3 Pos(unsigned q)const{return TDouble3(xy[q].x,xy[q].y,z[q]);}
  double WabFac(float rr,float& fac)const{if(rr==0){fac=0;return tk==KERNEL_Wendland?fsph::GetKernel_Wab<KERNEL_Wendland>(sph,rr):fsph::GetKernel_Wab<KERNEL_Cubic>(sph,rr);}return tk==KERNEL_Wendland?fsph::GetKernel_WabFac<KERNEL_Wendland>(sph,rr,fac):fsph::GetKernel_WabFac<KERNEL_Cubic>(sph,rr,fac);}
  double Condition(unsigned wall,double& distance)const{
    const auto target=Pos(wall)+Vec(bn[wall]);tmatrix3d raw=TMatrix3d(0),scaled=TMatrix3d(0);distance=DBL_MAX;
    for(unsigned q=Fixed;q<N;q++){const auto d=target-Pos(q);const float rr=float(Dot(d,d));if(rr>sph.kernelsize2)continue;float fac=0;
      const double w=WabFac(rr,fac)*V0*j[q],fx=V0*j[q]*fac*d.x,fz=V0*j[q]*fac*d.z,x=-d.x/h,zz=-d.z/h;
      raw.a11+=w;raw.a12+=d.x*w;raw.a13+=d.z*w;raw.a21+=fx;raw.a22+=d.x*fx;raw.a23+=d.z*fx;raw.a31+=fz;raw.a32+=d.x*fz;raw.a33+=d.z*fz;
      scaled.a11+=w;scaled.a12+=w*x;scaled.a13+=w*zz;scaled.a21+=w*x;scaled.a22+=w*x*x;scaled.a23+=w*x*zz;scaled.a31+=w*zz;scaled.a32+=w*x*zz;scaled.a33+=w*zz*zz;
      distance=(std::min)(distance,Dot(d,d));}
    const double det=fmath::Determinant3x3(scaled);Need(det>0&&fabs(fmath::Determinant3x3(raw))>=1e-3&&distance<DBL_MAX,"Independent supported MLS patch changed");distance=sqrt(distance);
    return (std::max)(1.,Inf(scaled)*Inf(fmath::InverseMatrix3x3(scaled,det)));
  }
  void Upload(){Up(xyg.p,xy);Up(zg.p,z);Up(jg.p,j);Up(thg.p,theta);Up(pg.p,p);Up(vg.p,vel);Up(ag.p,ace);Up(cg.p,c);Up(sg.p,sigma);Up(bng.p,bn);Up(codeg.p,code);Up(modeg.p,mode);Up(slipg.p,slips);}
  void Wall(unsigned stage,const byte* selector){
    Up(invalid.p,std::vector<unsigned>{N,0x1234abcd});
    cusph::DynamicPoreWall(stage,N,Fixed,.05f,dvd,xyg.p,zg.p,codeg.p,bng.p,modeg.p,tvg.p,dvg.p,vg.p,sg.p,pg.p,jg.p,thg.p,cg.p,ag.p,Solid,invalid.p,tk,selector);
    Cu(cudaDeviceSynchronize());Need(Down(invalid.p,2)==std::vector<unsigned>({N,0x1234abcd}),"Actual GPU wall rejected supported NoSlip fixture or changed invalid canary");
  }
public:
  explicit Patch(TpKernel kernel):tk(kernel){
    sph.kernelh=h;sph.kernelsize=2*h;sph.kernelsize2=sph.kernelsize*sph.kernelsize;sph.eta2=(h*.1f)*(h*.1f);sph.kwend=fsph::GetKernelWendland_Ctes(true,h);sph.kcubic=fsph::GetKernelCubic_Ctes(true,h);
    ct.simulate2d=1;ct.nbound=Fixed;ct.kernelh=h;ct.kernelsize=sph.kernelsize;ct.kernelsize2=sph.kernelsize2;ct.poscellsize=4;ct.scell=4;ct.dp=float(Dp);ct.rhopzero=2048;ct.massf=ct.massb=32;ct.gamma=7;ct.cs0=40;ct.eta2=sph.eta2;ct.axis=MGDIV_Z;ct.cellcode=DCEL_GetCode(1,1,1);ct.tboundary=BC_MDBC;ct.slipmode=SLIP_FreeSlip;
    ct.modulus_K=89478488.f;ct.modulus_G=134217728.f;ct.hydromech=1;ct.porewaterbulkmodulus=67108864.f;ct.porewaterrho=1000;ct.porosity=.25f;
    ct.awen=sph.kwend.awen;ct.bwen=sph.kwend.bwen;const auto kc=sph.kcubic;ct.cubic_a1=kc.a1;ct.cubic_a2=kc.a2;ct.cubic_aa=kc.aa;ct.cubic_a24=kc.a24;ct.cubic_c1=kc.c1;ct.cubic_d1=kc.d1;ct.cubic_c2=kc.c2;ct.cubic_odwdeltap=kc.od_wdeltap;
    for(unsigned q=Fixed;q<N;q++){const unsigned k=q-Fixed;xy[q]=make_double2(.5+(k%9)*Dp,0);z[q]=.5+(k/9)*Dp;code[q]=CODE_TYPE_FLUID;}
    for(unsigned w=0;w<Fixed;w++){const unsigned q=Fixed+36+8*w;const float shift=(w?-.25f:.25f);xy[w]=make_double2(xy[q].x-shift,0);z[w]=z[q];bn[w]=make_float3(shift,0,0);}
    for(unsigned q=N;q<Cap;q++){xy[q]=make_double2(-101.-q,-103.-q);z[q]=-107.-q;bn[q]=make_float3(71,73,79);}
    originalbn=bn;Up(cells.p,std::vector<int2>{make_int2(0,Fixed),make_int2(0,0),make_int2(Fixed,N),make_int2(0,0)});
    dvd=MakeDivDataGpu(1,TUint3(1,1,1),TUint3(0),cells.p,4,ct.cellcode,TDouble3(0),sph.kernelsize2,4);
  }
  void Check(unsigned option,bool offgrid,std::ostream& out,Counts& totals){
    Need(option<3,"Unknown slip test");const bool useoverride=(option==2);ct.slipmode=(option==0?SLIP_FreeSlip:SLIP_NoSlip);cusph::CteInteractionUp(&ct); // Real constant-memory fallback, not only a host label.
    bn=originalbn;if(offgrid)for(unsigned w=0;w<Fixed;w++)bn[w].x+=(bn[w].x>0?1.f:-1.f)*float(Dp/8.);
    mode.assign(Cap,0x5a);for(unsigned w=0;w<Fixed;w++){mode[w]=BMODE_DBC;slips[w]=byte(w?SLIP_FreeSlip:SLIP_NoSlip);}
    for(unsigned q=Fixed;q<N;q++){const double x=xy[q].x,zz=z[q];j[q]=1.+x/1024.;theta[q]=0;p[q]=float(128.+256.*x+64.*zz);vel[q]=make_float4(float(.125+.5*x),float(.0625-.25*x),float(-.25+.125*zz),2048);
      sigma[q]={16.+x,4.+8*x,8.+32*x,32.+2*zz,2.+16*zz,64.+4*x};c[q]=TMatrix3d(1.+x,.0625+.125*x,.125+.5*x,.0625+.125*x,1.5+.5*x,.03125+.0625*x,.125+.5*x,.03125+.0625*x,2.+x);ace[q]=make_float3(float(.25+.5*x),float(.0625+.125*x),float(-.125+.25*zz));}
    const auto oldj=j;const auto oldtheta=theta;const auto oldp=p;const auto oldvel=vel;const auto oldace=ace;const auto oldc=c;const auto olds=sigma;const auto oldmode=mode;
    const std::vector<float3> scratch(Cap,make_float3(7,11,13));Upload();Up(dvg.p,scratch);Up(tvg.p,scratch);const byte* selector=(useoverride?slipg.p:nullptr);Wall(0,selector);Wall(1,selector);Wall(2,selector);
    j=Down(jg.p,Cap);theta=Down(thg.p,Cap);p=Down(pg.p,Cap);vel=Down(vg.p,Cap);ace=Down(ag.p,Cap);c=Down(cg.p,Cap);sigma=Down(sg.p,Cap);
    const auto derivative=Down(dvg.p,Cap);const auto tangent=Down(tvg.p,Cap);const auto gotmode=Down(modeg.p,Cap);
    Need(Same(xy,Down(xyg.p,Cap))&&Same(z,Down(zg.p,Cap))&&Same(code,Down(codeg.p,Cap))&&Same(bn,Down(bng.p,Cap))&&Same(slips,Down(slipg.p,Cap)),"Const geometry/code/selector buffer changed");
    for(unsigned q=Fixed;q<Cap;q++)Need(j[q]==oldj[q]&&theta[q]==oldtheta[q]&&p[q]==oldp[q]&&!memcmp(&vel[q],&oldvel[q],sizeof(float4))&&!memcmp(&ace[q],&oldace[q],sizeof(float3))&&!memcmp(&c[q],&oldc[q],sizeof(tmatrix3d))&&!memcmp(&sigma[q],&olds[q],sizeof(tsymatrix3d))&&!memcmp(&derivative[q],&scratch[q],sizeof(float3))&&!memcmp(&tangent[q],&scratch[q],sizeof(float3))&&gotmode[q]==oldmode[q],"Native/tail or scratch canary changed");
    for(unsigned w=0;w<Fixed;w++){
      const bool noslip=(useoverride?(slips[w]==SLIP_NoSlip):(ct.slipmode==SLIP_NoSlip));const auto x=Pos(w)+Vec(bn[w]);const double sx=(noslip?xy[w].x:x.x),sgn=(noslip?-1.:1.);double distance=0;const double condition=Condition(w,distance),td=32768*DBL_EPSILON*condition,tf=64*FLT_EPSILON*condition;
      Need(distance==(offgrid?Dp/8.:0.),"Declared exact coincident/offgrid target not exercised");
      const auto dv=TDouble3(float(-(.125+.5*x.x)),float(sgn*(.0625-.25*x.x)),float(sgn*(-.25+.125*x.z)));
      const auto tv=TDouble3(0,dv.y,dv.z);const auto a=TDouble3(float(-(.25+.5*x.x)),float(.0625+.125*x.x),float(-.125+.25*x.z));
      const double shear=(noslip?1.:-1.);const tsymatrix3d expected={16.+sx,shear*(4.+8*sx),shear*(8.+32*sx),32.+2*x.z,2.+16*x.z,64.+4*sx};
      const tmatrix3d cm={1.+x.x,-(.0625+.125*x.x),-(.125+.5*x.x),-(.0625+.125*x.x),1.5+.5*x.x,.03125+.0625*x.x,-(.125+.5*x.x),.03125+.0625*x.x,2.+x.x};const auto s=sigma[w];const auto m=c[w];
      for(double v:{s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,m.a11,m.a12,m.a13,m.a21,m.a22,m.a23,m.a31,m.a32,m.a33})Need(std::isfinite(v),"Nonfinite wall stress/matrix");
      const double ej=fabs(j[w]-(1.+x.x/1024.)),ep=fabs(p[w]-float(128.+256*x.x+64*x.z)),ev=Norm(Vec(derivative[w])-dv),et=Norm(Vec(tangent[w])-tv),ea=Norm(Vec(ace[w])-a);
      const double es=(std::max)({fabs(s.xx-expected.xx),fabs(s.xy-expected.xy),fabs(s.xz-expected.xz),fabs(s.yy-expected.yy),fabs(s.yz-expected.yz),fabs(s.zz-expected.zz)});
      const double ec=(std::max)({fabs(m.a11-cm.a11),fabs(m.a12-cm.a12),fabs(m.a13-cm.a13),fabs(m.a21-cm.a21),fabs(m.a22-cm.a22),fabs(m.a23-cm.a23),fabs(m.a31-cm.a31),fabs(m.a32-cm.a32),fabs(m.a33-cm.a33)});
      Need(ej<=2*td&&ep<=256*tf&&ev<=tf&&et<=tf&&ea<=tf&&es<=128*td&&ec<=4*td,"Original state/C/Ace budgets failed");Need(theta[w]==0&&vel[w].x==0&&vel[w].y==0&&vel[w].z==0&&vel[w].w==2048&&gotmode[w]==BMODE_MDBC2,"Physical wall/mode rule failed");
      Need(derivative[w].x!=0&&derivative[w].y!=0&&derivative[w].z!=0&&ace[w].y!=0&&ace[w].z!=0,"Vector/separate Darcy-Ace witness vacuous");
      double wrongsign=0,missing=0;if(noslip){Need(s.xz>0,"NoSlip nonzero wall shear lost");wrongsign=fabs(s.xz+(8.+32*xy[w].x));missing=fabs(s.xz-(8.+32*x.x));Need(wrongsign>100*128*td&&missing>100*128*td,"Wrong sign/missing B extrapolation not separated");totals.minwrongsign=(std::min)(totals.minwrongsign,wrongsign/(128*td));totals.minmissing=(std::min)(totals.minmissing,missing/(128*td));totals.noslip++;}else{Need(s.xz<0,"FreeSlip shear reflection lost");totals.freeslip++;}
      out<<Name()<<','<<option<<','<<ct.slipmode<<','<<useoverride<<','<<offgrid<<','<<w<<','<<noslip<<','<<xy[w].x<<','<<x.x<<','<<sx<<','<<condition<<','<<distance<<','<<ej<<','<<ep<<','<<ev<<','<<et<<','<<es<<','<<ec<<','<<ea<<','<<s.xz<<','<<expected.xz<<','<<wrongsign<<','<<missing<<','<<td<<','<<tf<<'\n';totals.rows++;totals.offgrid+=unsigned(offgrid);
      totals.maxratio=(std::max)({totals.maxratio,ej/(2*td),ep/(256*tf),ev/tf,et/tf,es/(128*td),ec/(4*td),ea/tf});
    }totals.cases++;
  }
};
int main(int argc,char** argv){try{
  Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_OUTPUT_DIRECTORY");const fs::path out=argv[2];Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh output/existing parent required");fs::create_directory(out);Cu(cudaSetDevice(0));
  std::ofstream csv(out/"walls.csv");Need(bool(csv),"Cannot create component CSV");csv<<std::setprecision(17)<<"kernel,option,actual_CTE_global_mode,override_pointer,offgrid,wall,noslip,wall_x,mirror_x,stress_sample_x,condition,nearest_distance,J_error,p_error,derivative_error,tangent_error,stress_error,C_error,DarcyAce_error,sigma_xz,expected_xz,wrong_sign_separation,missing_extrapolation_separation,td,tf\n";Counts count;
  for(TpKernel kernel:{KERNEL_Wendland,KERNEL_Cubic}){Patch p(kernel);for(unsigned option=0;option<3;option++)for(bool offgrid:{false,true})p.Check(option,offgrid,csv,count);}
  Need(count.cases==12&&count.rows==24&&count.noslip==12&&count.freeslip==12&&count.offgrid==12,"Declared NoSlip GPU coverage incomplete");csv.flush();Need(bool(csv),"Component CSV write failed");
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_noslip_gpu_component_r1\",\"passed\":true,\"conditions\":"<<count.cases<<",\"wall_rows\":"<<count.rows<<",\"NoSlip_rows\":"<<count.noslip<<",\"FreeSlip_rows\":"<<count.freeslip<<",\"offgrid_rows\":"<<count.offgrid<<",\"nominal_h_over_dp\":1.8,\"synthetic_fluid\":81,\"synthetic_fixed\":2,\"tail_slots\":2,\"max_error_over_original_budget\":"<<count.maxratio<<",\"min_wrong_sign_over_stress_budget\":"<<count.minwrongsign<<",\"min_missing_extrapolation_over_stress_budget\":"<<count.minmissing<<",\"actual_CTE_global_selector_uploaded\":true,\"override_conflicts_with_global_on_right_wall\":true,\"actual_GPU_wall_stages\":36,\"native_geometry_selector_scratch_tail_unchanged\":true,\"CPU_same_ID_geometry_comparison\":false,\"CPU_production_called\":false,\"host_geometry_admission_tested\":false,\"force_or_Darcy_rate_called\":false,\"completed_physical_steps\":0,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}}
