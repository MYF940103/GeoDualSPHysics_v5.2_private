// Private GPU zero-step normal-head manufacture; no JSph loading or integrator.
// Small 81-fluid/2-wall patch, not the CPU1280 geometry or a matched-ID control.
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
JAppInfo AppInfo("GravityWallGpuComponent","r1","06-11-2026");
namespace fs=std::filesystem;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static void Cu(cudaError_t e){Need(e==cudaSuccess,cudaGetErrorString(e));}
template<class T>struct Device{T* p=nullptr;explicit Device(unsigned n){Cu(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*n));}~Device(){if(p)cudaFree(p);}Device(const Device&)=delete;Device& operator=(const Device&)=delete;};
template<class T>static void Up(T* p,const std::vector<T>& a){Cu(cudaMemcpy(p,a.data(),a.size()*sizeof(T),cudaMemcpyHostToDevice));}
template<class T>static std::vector<T> Down(const T* p,unsigned n){std::vector<T>a(n);Cu(cudaMemcpy(a.data(),p,n*sizeof(T),cudaMemcpyDeviceToHost));return a;}
template<class T>static bool Same(const std::vector<T>& a,const std::vector<T>& b){return a.size()==b.size()&&(a.empty()||!std::memcmp(a.data(),b.data(),a.size()*sizeof(T)));}
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static double Norm(tdouble3 a){return std::sqrt(Dot(a,a));}
static tdouble3 Vec(float3 v){return TDouble3(v.x,v.y,v.z);}
static tdouble3 Mul(const tmatrix3d& m,tdouble3 x){return TDouble3(m.a11*x.x+m.a12*x.y+m.a13*x.z,m.a21*x.x+m.a22*x.y+m.a23*x.z,m.a31*x.x+m.a32*x.y+m.a33*x.z);}
static double Inf(const tmatrix3d& a){return (std::max)({fabs(a.a11)+fabs(a.a12)+fabs(a.a13),fabs(a.a21)+fabs(a.a22)+fabs(a.a23),fabs(a.a31)+fabs(a.a32)+fabs(a.a33)});}
struct Ref{double rate,budget,pressure,acceleration;};
struct Face{double pressure;tdouble3 grad,ace;double vn,condition,limit,qn;};
struct Counts{unsigned good=0,walls=0,faces=0,rates=0,negative=0,skipped=0,overflow=0;double maxstate=0,maxflux=0,maxrate=0,minmissing=DBL_MAX,minwrong=DBL_MAX;};

class Patch{
  static constexpr unsigned Fixed=2,Fluid=81,N=Fixed+Fluid,Cap=N+2;
  static constexpr double Dp=.125,V0=Dp*Dp,Solid=.75,Kw=67108864.,Rhow=1000.,Head=128.;
  static constexpr float Sentinel=1234567.f;
  const double K=double(float(.0001));TpKernel tk;float gn,h=1.2f*float(Dp);bool offgrid;
  StCteSph sph=CteSphNull();StCteInteraction ct={};StDivDataGpu dvd;
  Device<int2> cells{4};Device<unsigned> dc{Cap},fsg{Cap},invalid{2};Device<typecode> codeg{Cap};
  Device<double2> xyg{Cap};Device<double> zg{Cap},jg{Cap},thg{Cap};Device<float4> posg{Cap},vg{Cap};
  Device<float> pg{Cap},rg{Cap},pdg{Cap};Device<tmatrix3d> cg{Cap};Device<tsymatrix3d> sg{Cap};
  Device<float3> ag{Cap},bng{Cap},dvg{Cap},tvg{Cap},fng{Cap};Device<byte> modeg{Cap};
  std::vector<double2> xy=std::vector<double2>(Cap);std::vector<double> z=std::vector<double>(Cap),j=std::vector<double>(Cap,1.),theta=std::vector<double>(Cap);
  std::vector<float> p=std::vector<float>(Cap);std::vector<float4> vel=std::vector<float4>(Cap);
  std::vector<float3> ace=std::vector<float3>(Cap),bn=std::vector<float3>(Cap),derivative,tangent;
  std::vector<typecode> code=std::vector<typecode>(Cap,CODE_TYPE_FIXED);std::vector<tmatrix3d> c=std::vector<tmatrix3d>(Cap);
  std::vector<tsymatrix3d> sigma=std::vector<tsymatrix3d>(Cap);std::vector<byte> mode=std::vector<byte>(Cap,BMODE_MDBC2);
  float Fac(float rr)const{return tk==KERNEL_Wendland?fsph::GetKernel_Fac<KERNEL_Wendland>(sph,rr):fsph::GetKernel_Fac<KERNEL_Cubic>(sph,rr);}
  float Wab(float rr)const{return tk==KERNEL_Wendland?fsph::GetKernel_Wab<KERNEL_Wendland>(sph,rr):fsph::GetKernel_Wab<KERNEL_Cubic>(sph,rr);}
  double WabFac(float rr,float& f)const{if(rr==0){f=0;return Wab(rr);}return tk==KERNEL_Wendland?fsph::GetKernel_WabFac<KERNEL_Wendland>(sph,rr,f):fsph::GetKernel_WabFac<KERNEL_Cubic>(sph,rr,f);}
  tdouble3 Pos(unsigned a)const{return TDouble3(xy[a].x,xy[a].y,z[a]);}
  const char* Name()const{return tk==KERNEL_Wendland?"Wendland":"Cubic";}
  void Upload(){Up(xyg.p,xy);Up(zg.p,z);Up(jg.p,j);Up(thg.p,theta);Up(pg.p,p);Up(vg.p,vel);Up(ag.p,ace);Up(cg.p,c);Up(sg.p,sigma);Up(bng.p,bn);Up(codeg.p,code);Up(modeg.p,mode);}
  void Download(){j=Down(jg.p,Cap);theta=Down(thg.p,Cap);p=Down(pg.p,Cap);vel=Down(vg.p,Cap);ace=Down(ag.p,Cap);c=Down(cg.p,Cap);sigma=Down(sg.p,Cap);derivative=Down(dvg.p,Cap);tangent=Down(tvg.p,Cap);}
  void Wall(unsigned stage){Up(invalid.p,std::vector<unsigned>{N,0x1234abcd});
    cusph::DynamicPoreWall(stage,N,Fixed,.05f,dvd,xyg.p,zg.p,codeg.p,bng.p,modeg.p,tvg.p,dvg.p,vg.p,sg.p,pg.p,jg.p,thg.p,cg.p,ag.p,Solid,invalid.p,tk);
    Cu(cudaDeviceSynchronize());Need(Down(invalid.p,2)==std::vector<unsigned>({N,0x1234abcd}),"Good wall condition was rejected");}
  void Rate(){Up(invalid.p,std::vector<unsigned>{N,0x1234abcd});Up(rg.p,std::vector<float>(Cap,Sentinel));
    cusph::ComputeDynamicPorePressureRate(N,Fixed,dvd,dc.p,xyg.p,zg.p,codeg.p,cg.p,ag.p,jg.p,thg.p,pg.p,rg.p,Solid,Kw,Rhow,K,Rhow*9.80665,V0,invalid.p,
      false,0.,nullptr,true,modeg.p,nullptr,nullptr,false,false,HMLOAD_None,TDouble3(0),0.,tk);
    Cu(cudaDeviceSynchronize());Need(Down(invalid.p,2)==std::vector<unsigned>({N,0x1234abcd}),"Good complete rate was rejected");}
  void Condition(unsigned wall,double& condition,double& distance)const{
    const auto target=Pos(wall)+Vec(bn[wall]);tmatrix3d raw=TMatrix3d(0),scaled=TMatrix3d(0);distance=DBL_MAX;
    for(unsigned q=Fixed;q<N;q++){const auto d=target-Pos(q);const float rr=float(Dot(d,d));if(rr>sph.kernelsize2)continue;float fac=0;const double w=WabFac(rr,fac)*V0*j[q],fx=V0*j[q]*fac*d.x,fz=V0*j[q]*fac*d.z;
      raw.a11+=w;raw.a12+=d.x*w;raw.a13+=d.z*w;raw.a21+=fx;raw.a22+=d.x*fx;raw.a23+=d.z*fx;raw.a31+=fz;raw.a32+=d.x*fz;raw.a33+=d.z*fz;
      const double x=-d.x/h,zz=-d.z/h;scaled.a11+=w;scaled.a12+=w*x;scaled.a13+=w*zz;scaled.a21+=w*x;scaled.a22+=w*x*x;scaled.a23+=w*x*zz;scaled.a31+=w*zz;scaled.a32+=w*x*zz;scaled.a33+=w*zz*zz;
      distance=(std::min)(distance,Dot(d,d));}
    const double det=fmath::Determinant3x3(scaled);Need(det>0&&fabs(fmath::Determinant3x3(raw))>=1e-3&&distance<DBL_MAX,"Mirror support singular");
    condition=(std::max)(1.,Inf(scaled)*Inf(fmath::InverseMatrix3x3(scaled,det)));distance=sqrt(distance);
  }
  Ref Reference(unsigned i)const{ // Original small-patch raw-sum reference, constant-k/law=false specialization.
    double lp=0,da=0,alp=0,ada=0;tdouble3 lx=TDouble3(0),gp=TDouble3(0),alx=TDouble3(0),agp=TDouble3(0);
    for(unsigned q=0;q<N;q++){const auto d=Pos(i)-Pos(q);const double rr=Dot(d,d);if(rr>double(sph.kernelsize2)||rr<ALMOSTZERO)continue;
      const auto g=d*double(Fac(float(rr))),gi=Mul(c[i],g),gq=Mul(c[q],g);const double v=V0*j[q],dp=double(p[i])-p[q],w=v*Dot(d,gi+gq)/(rr+double(sph.eta2));
      lp+=w*dp;alp+=fabs(w*dp);lx=lx+d*w;gp=gp-gi*(v*dp);alx=alx+TDouble3(fabs(d.x*w),fabs(d.y*w),fabs(d.z*w));agp=agp+TDouble3(fabs(gi.x*v*dp),fabs(gi.y*v*dp),fabs(gi.z*v*dp));
      const auto a=Vec(ace[q])-Vec(ace[i]);da+=v*Dot(a,gi);ada+=v*(fabs(a.x*gi.x)+fabs(a.y*gi.y)+fabs(a.z*gi.z));}
    const double B=Kw/(1.-Solid/j[i]),gamma=Rhow*9.80665,raw=B*(fabs(theta[i])+K/gamma*(alp+Dot(agp,alx)+Rhow*ada));
    return {B*(-theta[i]+K/gamma*(lp-Dot(gp,lx)+Rhow*da)),64.*FLT_EPSILON*raw+256.*DBL_EPSILON*(std::max)(1.,fabs(B*theta[i]))+1e-6,B*K/gamma*(lp-Dot(gp,lx)),B*K/gamma*Rhow*da};
  }
  Face PhysicalFace(unsigned wall,unsigned negative)const{
    const auto at=Pos(wall)+Vec(bn[wall])*.5;tmatrix3d m=TMatrix3d(0);tdouble3 bp=TDouble3(0),bv=TDouble3(0),ba[3]={TDouble3(0),TDouble3(0),TDouble3(0)};
    for(unsigned q=0;q<N;q++){const auto d=Pos(q)-at;const double rr=Dot(d,d);if(rr>double(sph.kernelsize2))continue;const double w=V0*j[q]*Wab(float(rr)),x=d.x/h,zz=d.z/h;const auto basis=TDouble3(1,x,zz);
      m.a11+=w;m.a12+=w*x;m.a13+=w*zz;m.a21+=w*x;m.a22+=w*x*x;m.a23+=w*x*zz;m.a31+=w*zz;m.a32+=w*x*zz;m.a33+=w*zz*zz;
      double pressure=p[q];auto a=Vec(ace[q]);if(q<Fixed){if(negative==1)pressure=float(Head+Rhow*double(gn)*(Pos(q).x+bn[q].x));if(negative==2)a.x=-a.x;}
      bp=bp+basis*(w*pressure);bv=bv+basis*(w*(q<Fixed?derivative[q].x:vel[q].x));ba[0]=ba[0]+basis*(w*a.x);ba[1]=ba[1]+basis*(w*a.y);ba[2]=ba[2]+basis*(w*a.z);}
    const double det=fmath::Determinant3x3(m);Need(std::isfinite(det)&&det>0,"Physical-face support singular");const auto inv=fmath::InverseMatrix3x3(m,det);
    const auto pc=Mul(inv,bp),ax=Mul(inv,ba[0]),ay=Mul(inv,ba[1]),az=Mul(inv,ba[2]);const auto grad=TDouble3(pc.y/h,0,pc.z/h),a=TDouble3(ax.x,ay.x,az.x);
    const double condition=(std::max)(1.,Inf(m)*Inf(inv)),td=32768.*DBL_EPSILON*condition,tf=64.*FLT_EPSILON*condition,inward=bn[wall].x>0?1.:-1.;
    const double limit=K/(Rhow*9.80665)*(tf*(Rhow*fabs(double(gn))+Rhow)+td*256./h); // gt=2 NEVER enlarges this original propagated bound.
    return {pc.x,grad,a,Mul(inv,bv).x*inward,condition,limit,-K/(Rhow*9.80665)*(grad.x+Rhow*a.x)*inward};
  }
public:
  Patch(TpKernel kernel,float normal_g,bool offset):tk(kernel),gn(normal_g),offgrid(offset){
    sph.kernelh=h;sph.kernelsize=2*h;sph.kernelsize2=sph.kernelsize*sph.kernelsize;sph.eta2=(h*.1f)*(h*.1f);sph.kwend=fsph::GetKernelWendland_Ctes(true,h);sph.kcubic=fsph::GetKernelCubic_Ctes(true,h);
    ct.simulate2d=1;ct.nbound=Fixed;ct.kernelh=h;ct.kernelsize=sph.kernelsize;ct.kernelsize2=sph.kernelsize2;ct.poscellsize=4;ct.scell=4;ct.dp=float(Dp);
    ct.rhopzero=2048;ct.massf=ct.massb=32;ct.gamma=7;ct.cs0=40;ct.eta2=sph.eta2;ct.axis=MGDIV_Z;ct.cellcode=DCEL_GetCode(1,1,1);ct.tboundary=BC_MDBC;ct.slipmode=SLIP_FreeSlip;
    ct.gravityx=gn;ct.gravityy=0;ct.gravityz=2;ct.modulus_K=89478488.f;ct.modulus_G=134217728.f;ct.hydromech=1;ct.porewaterbulkmodulus=float(Kw);ct.porewaterrho=float(Rhow);ct.porosity=float(1.-Solid);ct.porekwn=float(Kw/(1.-Solid));ct.porecompgradcorr=ct.soilstressrategradcorr=1;
    ct.awen=sph.kwend.awen;ct.bwen=sph.kwend.bwen;const auto kc=sph.kcubic;ct.cubic_a1=kc.a1;ct.cubic_a2=kc.a2;ct.cubic_aa=kc.aa;ct.cubic_a24=kc.a24;ct.cubic_c1=kc.c1;ct.cubic_d1=kc.d1;ct.cubic_c2=kc.c2;ct.cubic_odwdeltap=kc.od_wdeltap;cusph::CteInteractionUp(&ct);
    for(unsigned q=Fixed;q<N;q++){const unsigned id=q-Fixed;xy[q]=make_double2(.5+(id%9)*Dp,0);z[q]=.5+(id/9)*Dp;code[q]=CODE_TYPE_FLUID;}
    for(unsigned w=0;w<Fixed;w++){const unsigned q=Fixed+36+8*w;const float shift=w?-.25f:.25f;xy[w]=make_double2(xy[q].x-shift,0);z[w]=z[q];bn[w]=make_float3(shift+(offset?(shift>0?1.f:-1.f)*float(Dp/8.):0.f),0,0);}
    for(unsigned q=0;q<N;q++){vel[q]=make_float4(0,0,0,2048);p[q]=q<Fixed?0.f:float(Head+Rhow*double(gn)*xy[q].x);ace[q]=make_float3(-gn,0,0);Need(fabs(Head+Rhow*double(gn)*xy[q].x)<256.,"Good manufacture exceeds original256 pressure scale");}
    std::vector<float4> position(Cap);for(unsigned q=0;q<Cap;q++)position[q]=make_float4(float(xy[q].x),0,float(z[q]),0);
    Up(posg.p,position);Up(dc.p,std::vector<unsigned>(Cap,0));Up(cells.p,std::vector<int2>{make_int2(0,Fixed),make_int2(0,0),make_int2(Fixed,N),make_int2(0,0)});
    dvd=MakeDivDataGpu(1,TUint3(1,1,1),TUint3(0),cells.p,4,ct.cellcode,TDouble3(0),sph.kernelsize2,4);Upload();Cu(cudaMemset(dvg.p,0,Cap*sizeof(float3)));Cu(cudaMemset(tvg.p,0,Cap*sizeof(float3)));
  }
  void Run(std::ostream& wall,std::ostream& face,std::ostream& rate,Counts& totals){
    const auto oldj=j,oldtheta=theta;const auto oldp=p;const auto oldvel=vel;const auto olda=ace;const auto olds=sigma;
    cusph::ComputeFreeSurfaceTracking(tk,true,N,Fixed,dvd,dc.p,posg.p,vg.p,codeg.p,cg.p,fsg.p,fng.p,pdg.p,false,jg.p);Cu(cudaDeviceSynchronize());const auto fsc=Down(cg.p,Cap);
    Wall(0);Wall(1);Wall(2);Download();const auto gotmode=Down(modeg.p,Cap);
    for(unsigned q=Fixed;q<N;q++)Need(j[q]==oldj[q]&&theta[q]==oldtheta[q]&&p[q]==oldp[q]&&!memcmp(&vel[q],&oldvel[q],sizeof(float4))&&!memcmp(&ace[q],&olda[q],sizeof(float3))&&!memcmp(&sigma[q],&olds[q],sizeof(tsymatrix3d))&&!memcmp(&c[q],&fsc[q],sizeof(tmatrix3d)),"Wall stages changed native physical state or FS C");
    Need(Same(xy,Down(xyg.p,Cap))&&Same(z,Down(zg.p,Cap))&&Same(code,Down(codeg.p,Cap))&&Same(bn,Down(bng.p,Cap)),"Geometry/code/normal bytes changed");
    for(unsigned w=0;w<Fixed;w++){double condition=0,distance=0;Condition(w,condition,distance);const double td=32768.*DBL_EPSILON*condition,tf=64.*FLT_EPSILON*condition,expected=float(Head+Rhow*double(gn)*Pos(w).x);
      const double ep=fabs(p[w]-expected),ej=fabs(j[w]-1.),ea=Norm(Vec(ace[w])+TDouble3(gn,0,0));const auto s=sigma[w];const double es=(std::max)({fabs(s.xx),fabs(s.yy),fabs(s.zz),fabs(s.xy),fabs(s.yz),fabs(s.xz)});
      Need(ep<=256*tf&&ej<=2*td&&ea<=tf&&es==0&&theta[w]==0,"Original p/J/Ace or zero-state budget failed");
      Need(vel[w].x==0&&vel[w].y==0&&vel[w].z==0&&vel[w].w==2048&&gotmode[w]==BMODE_MDBC2&&Norm(Vec(derivative[w]))==0&&Norm(Vec(tangent[w]))==0,"Fixed/derivative/tangent zero-state semantics changed");
      Need((offgrid?distance>0:distance==0)&&std::isfinite(c[w].a11*c[w].a33-c[w].a13*c[w].a31)&&c[w].a11*c[w].a33-c[w].a13*c[w].a31>0,"Mirror/conditional wall C invalid");
      totals.maxstate=(std::max)({totals.maxstate,ep/(256*tf),ej/(2*td),ea/tf});wall<<Name()<<','<<gn<<",2,"<<offgrid<<','<<w<<','<<Pos(w).x<<','<<Pos(w).x+bn[w].x<<','<<expected<<','<<p[w]<<','<<ep<<','<<ej<<','<<ea<<','<<condition<<','<<distance<<','<<td<<','<<tf<<'\n';totals.walls++;
      const auto f=PhysicalFace(w,0);const auto at=Pos(w)+Vec(bn[w])*.5;const double ftd=32768.*DBL_EPSILON*f.condition,ftf=64.*FLT_EPSILON*f.condition;
      Need(fabs(f.pressure-(Head+Rhow*double(gn)*at.x))<=256*ftf&&Norm(f.grad-TDouble3(Rhow*double(gn),0,0))<=ftf*Rhow*fabs(double(gn))+ftd*256./h&&Norm(f.ace+TDouble3(gn,0,0))<=ftf,"Independent actual-plane p/gradient/Ace budget failed");
      Need(f.vn==0&&std::isfinite(f.qn)&&fabs(f.qn)<=f.limit,"Actual physical-face normal flux budget failed");totals.maxflux=(std::max)(totals.maxflux,fabs(f.qn)/f.limit);
      face<<Name()<<','<<gn<<",2,"<<offgrid<<','<<w<<','<<at.x<<','<<at.z<<','<<f.pressure<<','<<f.grad.x<<','<<f.grad.z<<','<<f.ace.x<<','<<f.ace.z<<','<<f.vn<<','<<f.qn<<','<<f.limit<<','<<f.condition<<',';
      if(gn!=0){const auto missing=PhysicalFace(w,1),wrong=PhysicalFace(w,2);const double mh=fabs(missing.qn)/f.limit,wa=fabs(wrong.qn)/f.limit;Need(mh>1&&wa>1,"Normal-head/Ace negative witness empty under original good bound");totals.minmissing=(std::min)(totals.minmissing,mh);totals.minwrong=(std::min)(totals.minwrong,wa);totals.negative++;face<<missing.qn<<','<<wrong.qn<<','<<mh<<','<<wa<<",1\n";}
      else{totals.skipped++;face<<",,,,0\n";} // Blank counterfactual fields mean skipped, never a passed gn=0 negative.
      totals.faces++;
    }
    Rate();const auto actual=Down(rg.p,Cap);Need(actual[0]==Sentinel&&actual[1]==Sentinel&&actual[N]==Sentinel&&actual[N+1]==Sentinel,"Rate prefix/tail canary changed");
    for(unsigned q=Fixed;q<N;q++){const auto ref=Reference(q);const double error=fabs(double(actual[q])-ref.rate);Need(std::isfinite(actual[q])&&error<=ref.budget,"Original raw-sum rate budget failed");rate<<Name()<<','<<gn<<",2,"<<offgrid<<','<<q<<','<<actual[q]<<','<<ref.rate<<','<<error<<','<<ref.budget<<','<<error/ref.budget<<','<<ref.pressure<<','<<ref.acceleration<<'\n';totals.rates++;totals.maxrate=(std::max)(totals.maxrate,error/ref.budget);}
    Need(Same(p,Down(pg.p,Cap))&&Same(j,Down(jg.p,Cap))&&Same(theta,Down(thg.p,Cap))&&Same(c,Down(cg.p,Cap))&&Same(ace,Down(ag.p,Cap))&&Same(vel,Down(vg.p,Cap))&&Same(sigma,Down(sg.p,Cap))&&Same(derivative,Down(dvg.p,Cap))&&Same(tangent,Down(tvg.p,Cap)),"Rate changed frozen input state");totals.good++;
  }
  void Overflow(std::ostream& out,Counts& totals){ // One additional Cubic stage0 launch only; no FS/rate/reference condition.
    Need(tk==KERNEL_Cubic,"Overflow witness is Cubic only");ct.gravityx=FLT_MAX/4.f;ct.gravityz=2;cusph::CteInteractionUp(&ct);std::fill(p.begin(),p.end(),0.f);std::fill(ace.begin(),ace.end(),make_float3(0,0,0));Upload();
    Up(invalid.p,std::vector<unsigned>{N,0x1234abcd});cusph::DynamicPoreWall(0,N,Fixed,.05f,dvd,xyg.p,zg.p,codeg.p,bng.p,modeg.p,tvg.p,dvg.p,vg.p,sg.p,pg.p,jg.p,thg.p,cg.p,ag.p,Solid,invalid.p,tk);Cu(cudaDeviceSynchronize());const auto bad=Down(invalid.p,2);
    Need(std::isfinite(ct.gravityx)&&bad[0]<Fixed&&bad[1]==0x1234abcd,"Finite normal-head overflow did not report a real wall index");Need(Same(p,Down(pg.p,Cap))&&Same(j,Down(jg.p,Cap))&&Same(theta,Down(thg.p,Cap))&&Same(vel,Down(vg.p,Cap))&&Same(sigma,Down(sg.p,Cap)),"Rejected stage0 changed input state");
    out<<"Cubic,0,"<<ct.gravityx<<",0,"<<bad[0]<<",1,1\n";totals.overflow++;
  }
};
int main(int argc,char** argv){try{
  Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_OUTPUT_DIRECTORY");const fs::path out=argv[2];Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh output/existing parent required");Need(fs::create_directory(out),"Cannot claim fresh output");Cu(cudaSetDevice(0));
  std::ofstream wall(out/"wall.csv"),face(out/"face.csv"),rate(out/"rates.csv"),overflow(out/"overflow.csv");Need(wall&&face&&rate&&overflow,"Cannot create CSVs");for(auto* s:{&wall,&face,&rate,&overflow})*s<<std::setprecision(17);
  wall<<"kernel,normal_g_x,tangent_g_z,offgrid,wall_slot,wall_x,mirror_x,expected_p,actual_p,p_error,J_error,Ace_error,condition,nearest_distance_m,double_base_bound,float_base_bound\n";
  face<<"kernel,normal_g_x,tangent_g_z,offgrid,wall_slot,physical_plane_x,z,p_fit,gradp_x,gradp_z,Ace_fit_x,Ace_fit_z,vn,normal_flux,flux_bound,condition,missing_head_flux,wrong_Ace_flux,missing_over_good_bound,wrong_over_good_bound,negative_controls_evaluated\n";
  rate<<"kernel,normal_g_x,tangent_g_z,offgrid,fluid_slot,actual_Pa_s,reference_Pa_s,error,budget,error_over_budget,pressure_source,acceleration_source\n";
  overflow<<"kernel,stage,normal_g_x,fluid_pressure,invalid_wall_slot,expected_reject,canary_preserved\n";Counts n;
  for(TpKernel kernel:{KERNEL_Wendland,KERNEL_Cubic})for(float gn:{-1.f/16.f,0.f,1.f/16.f})for(bool offset:{false,true}){Patch p(kernel,gn,offset);p.Run(wall,face,rate,n);}
  {Patch p(KERNEL_Cubic,0.f,false);p.Overflow(overflow,n);}
  Need(n.good==12&&n.walls==24&&n.faces==24&&n.rates==972&&n.negative==16&&n.skipped==8&&n.overflow==1,"Declared component counts incomplete");for(auto* s:{&wall,&face,&rate,&overflow}){s->flush();Need(bool(*s),"CSV write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_gravity_wall_gpu_component_r1\",\"passed\":true,\"good_conditions\":"<<n.good<<",\"wall_rows\":"<<n.walls<<",\"physical_face_rows\":"<<n.faces<<",\"rate_rows\":"<<n.rates<<",\"negative_face_probes\":"<<n.negative<<",\"negative_counterfactual_evaluations\":"<<2*n.negative<<",\"zero_normal_g_skipped_face_probes\":"<<n.skipped<<",\"zero_normal_g_skipped_counterfactuals\":"<<2*n.skipped<<",\"separate_expected_stage0_overflow_rejections\":"<<n.overflow
    <<",\"max_wall_state_over_original_budget\":"<<n.maxstate<<",\"max_face_flux_over_propagated_budget\":"<<n.maxflux<<",\"max_rate_over_original_budget\":"<<n.maxrate<<",\"min_missing_head_flux_over_good_budget\":"<<n.minmissing<<",\"min_wrong_Ace_flux_over_good_budget\":"<<n.minwrong<<",\"fluid_slots\":81,\"fixed_slots\":2,\"dp\":0.125,\"h_over_dp\":1.2,\"actual_GPU_FS_three_wall_stages_Darcy\":true,\"independent_host_raw_sum_and_physical_face_MLS\":true,\"reference_uses_actual_conditional_C\":true,\"native_input_and_FS_C_unchanged_by_wall\":true,\"rate_input_state_unchanged\":true,\"normal_head_only_not_full_gravity_pressure\":true,\"native_Ace_minus_gn_true_as_gt\":true,\"negative_controls_are_host_counterfactuals\":true,\"CPU1280_geometry_or_same_ID_comparison\":false,\"JSph_loading_or_periodic_or_force_solver\":false,\"completed_physical_steps\":0,\"public_gravity_admission\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}}
