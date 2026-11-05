// Actual GPU wrappers versus a CPU all-particle expression reference, not a solver.
#include "JSphGpu_ker.h"
#include "FunSphKernel.h"
#include "FunctionsMath.h"
#include "JDsDcellDef.h"
#include "JAppInfo.h"
#include <cuda_runtime.h>
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
#include <vector>
JAppInfo AppInfo("UplCubicComponent","r1","06-11-2026");
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
struct Ref{double rate,budget,pressure,acceleration,chain;};
struct Coverage{unsigned conditions=0,affine_rows=0,anchor_rows=0,rate_rows=0,negative_rows=0;double maxrate=0,maxwall=0;};

class Patch{
  static constexpr unsigned Fixed=2,Fluid=81,N=Fixed+Fluid,Cap=N+2;
  static constexpr double Dp=.125,V0=Dp*Dp,Solid=.75,Kw=67108864.,Rhow=1000.,Ck=.125;
  static constexpr float Sentinel=1234567.f;
  TpKernel tk;bool jitter;float h;StCteSph sph=CteSphNull();StDivDataGpu dvd;
  Device<int2> cells{4};Device<unsigned> dc{Cap},fs{Cap},invalid{2};Device<typecode> codeg{Cap};
  Device<double2> xyg{Cap};Device<double> zg{Cap},jg{Cap},thg{Cap};Device<float4> posg{Cap},vg{Cap};
  Device<float> pg{Cap},rg{Cap},pdg{Cap};Device<tmatrix3d> cg{Cap};Device<tsymatrix3d> sg{Cap};
  Device<float3> ag{Cap},bng{Cap},dvg{Cap},tvg{Cap},fng{Cap};Device<byte> modeg{Cap};
  std::vector<double2> xy=std::vector<double2>(Cap);std::vector<double> z=std::vector<double>(Cap),j=std::vector<double>(Cap,1.),theta=std::vector<double>(Cap);
  std::vector<float> p=std::vector<float>(Cap);std::vector<float4> vel=std::vector<float4>(Cap);
  std::vector<float3> ace=std::vector<float3>(Cap),bn=std::vector<float3>(Cap),originalbn;
  std::vector<typecode> code=std::vector<typecode>(Cap,CODE_TYPE_FIXED);std::vector<tmatrix3d> c=std::vector<tmatrix3d>(Cap);
  std::vector<tsymatrix3d> sigma=std::vector<tsymatrix3d>(Cap);std::vector<byte> mode=std::vector<byte>(Cap,BMODE_MDBC2);
  float Fac(float rr)const{return tk==KERNEL_Wendland?fsph::GetKernel_Fac<KERNEL_Wendland>(sph,rr):fsph::GetKernel_Fac<KERNEL_Cubic>(sph,rr);}
  float Wab(float rr)const{return tk==KERNEL_Wendland?fsph::GetKernel_Wab<KERNEL_Wendland>(sph,rr):fsph::GetKernel_Wab<KERNEL_Cubic>(sph,rr);}
  double WabFac(float rr,float& f)const{if(rr==0){f=0;return Wab(rr);}return tk==KERNEL_Wendland?fsph::GetKernel_WabFac<KERNEL_Wendland>(sph,rr,f):fsph::GetKernel_WabFac<KERNEL_Cubic>(sph,rr,f);}
  tdouble3 Pos(unsigned a)const{return TDouble3(xy[a].x,xy[a].y,z[a]);}
  const char* Name()const{return tk==KERNEL_Wendland?"Wendland":"Cubic";}
  void Upload(){Up(xyg.p,xy);Up(zg.p,z);Up(jg.p,j);Up(thg.p,theta);Up(pg.p,p);Up(vg.p,vel);Up(ag.p,ace);Up(cg.p,c);Up(sg.p,sigma);Up(bng.p,bn);Up(codeg.p,code);Up(modeg.p,mode);}
  void Wall(unsigned stage){Up(invalid.p,std::vector<unsigned>{N,0x1234abcd});
    cusph::DynamicPoreWall(stage,N,Fixed,.05f,dvd,xyg.p,zg.p,codeg.p,bng.p,modeg.p,tvg.p,dvg.p,vg.p,sg.p,pg.p,jg.p,thg.p,cg.p,ag.p,Solid,invalid.p,tk);
    Cu(cudaDeviceSynchronize());Need(Down(invalid.p,2)==std::vector<unsigned>({N,0x1234abcd}),"Actual wall wrapper rejected a declared supported patch");}
  void Rate(bool law,double k){Up(invalid.p,std::vector<unsigned>{N,0x1234abcd});Up(rg.p,std::vector<float>(Cap,Sentinel));
    cusph::ComputeDynamicPorePressureRate(N,Fixed,dvd,dc.p,xyg.p,zg.p,codeg.p,cg.p,ag.p,jg.p,thg.p,pg.p,rg.p,Solid,Kw,Rhow,k,Rhow*9.80665,V0,invalid.p,
      law,law?Ck:0.,nullptr,true,modeg.p,nullptr,nullptr,false,false,HMLOAD_None,TDouble3(0),0.,tk);
    Cu(cudaDeviceSynchronize());Need(Down(invalid.p,2)==std::vector<unsigned>({N,0x1234abcd}),"Actual complete-rate wrapper rejected a declared supported patch");}
  void Condition(unsigned wall,double& cond,double& distance)const{
    const auto target=Pos(wall)+ToTDouble3(bn[wall]);tmatrix3d raw=TMatrix3d(0),scaled=TMatrix3d(0);distance=DBL_MAX;
    for(unsigned q=Fixed;q<N;q++){const auto d=target-Pos(q);const float rr=float(Dot(d,d));if(rr>sph.kernelsize2)continue;float fac=0;const double w=WabFac(rr,fac)*V0*j[q],fx=V0*j[q]*fac*d.x,fz=V0*j[q]*fac*d.z;
      raw.a11+=w;raw.a12+=d.x*w;raw.a13+=d.z*w;raw.a21+=fx;raw.a22+=d.x*fx;raw.a23+=d.z*fx;raw.a31+=fz;raw.a32+=d.x*fz;raw.a33+=d.z*fz;
      const double x=-d.x/h,zz=-d.z/h;scaled.a11+=w;scaled.a12+=w*x;scaled.a13+=w*zz;scaled.a21+=w*x;scaled.a22+=w*x*x;scaled.a23+=w*x*zz;scaled.a31+=w*zz;scaled.a32+=w*x*zz;scaled.a33+=w*zz*zz;
      distance=(std::min)(distance,Dot(d,d));}
    const double det=fmath::Determinant3x3(scaled);Need(det>0&&fabs(fmath::Determinant3x3(raw))>=1e-3&&distance<DBL_MAX,"Independent affine-fit support is singular");
    cond=(std::max)(1.,Inf(scaled)*Inf(fmath::InverseMatrix3x3(scaled,det)));distance=sqrt(distance);
  }
  Ref Reference(unsigned i,bool law,double k)const{
    double lp=0,da=0,alp=0,ada=0;tdouble3 lx=TDouble3(0),gp=TDouble3(0),gj=TDouble3(0),alx=TDouble3(0),agp=TDouble3(0),agj=TDouble3(0);
    if(k>0)for(unsigned q=0;q<N;q++){const auto d=Pos(i)-Pos(q);const double rr=Dot(d,d);if(rr>double(sph.kernelsize2)||rr<ALMOSTZERO)continue;
      const auto g=d*double(Fac(float(rr))),gi=Mul(c[i],g),gq=Mul(c[q],g);const double v=V0*j[q],dp=double(p[i])-p[q],w=v*Dot(d,gi+gq)/(rr+double(sph.eta2));
      lp+=w*dp;alp+=fabs(w*dp);lx=lx+d*w;gp=gp-gi*(v*dp);gj=gj+gi*(v*(j[q]-j[i]));
      alx=alx+TDouble3(fabs(d.x*w),fabs(d.y*w),fabs(d.z*w));agp=agp+TDouble3(fabs(gi.x*v*dp),fabs(gi.y*v*dp),fabs(gi.z*v*dp));
      agj=agj+TDouble3(fabs(gi.x*v*(j[q]-j[i])),fabs(gi.y*v*(j[q]-j[i])),fabs(gi.z*v*(j[q]-j[i])));
      const auto a=Vec(ace[q])-Vec(ace[i]);da+=v*Dot(a,gi);ada+=v*(fabs(a.x*gi.x)+fabs(a.y*gi.y)+fabs(a.z*gi.z));}
    const double B=Kw/(1.-Solid/j[i]),gamma=Rhow*9.80665,ki=law?k*exp((j[i]-1.)/(Solid*Ck)):k,scale=law?ki/(Solid*Ck):0.;
    const double chain=scale*Dot(gj,gp+Vec(ace[i])*Rhow),raw=B*(fabs(theta[i])+ki/gamma*(alp+Dot(agp,alx)+Rhow*ada)+fabs(scale)/gamma*Dot(agj,agp+TDouble3(fabs(ace[i].x),fabs(ace[i].y),fabs(ace[i].z))*Rhow));
    return {B*(-theta[i]+ki/gamma*(lp-Dot(gp,lx)+Rhow*da)+chain/gamma),64.*FLT_EPSILON*raw+256.*DBL_EPSILON*(std::max)(1.,fabs(B*theta[i]))+1e-6,B*ki/gamma*(lp-Dot(gp,lx)),B*ki/gamma*Rhow*da,B/gamma*chain};
  }
  void Download(){j=Down(jg.p,Cap);theta=Down(thg.p,Cap);p=Down(pg.p,Cap);vel=Down(vg.p,Cap);ace=Down(ag.p,Cap);c=Down(cg.p,Cap);sigma=Down(sg.p,Cap);}
public:
  Patch(TpKernel kernel,bool disturbed,float ratio):tk(kernel),jitter(disturbed),h(ratio*float(Dp)){
    sph.kernelh=h;sph.kernelsize=2*h;sph.kernelsize2=sph.kernelsize*sph.kernelsize;sph.eta2=(h*.1f)*(h*.1f);sph.kwend=fsph::GetKernelWendland_Ctes(true,h);sph.kcubic=fsph::GetKernelCubic_Ctes(true,h);
    StCteInteraction ct={};ct.simulate2d=1;ct.nbound=Fixed;ct.kernelh=h;ct.kernelsize=sph.kernelsize;ct.kernelsize2=sph.kernelsize2;ct.poscellsize=4;ct.scell=4;ct.dp=float(Dp);
    ct.rhopzero=2048;ct.massf=ct.massb=32;ct.gamma=7;ct.cs0=40;ct.eta2=sph.eta2;ct.axis=MGDIV_Z;ct.cellcode=DCEL_GetCode(1,1,1);ct.tboundary=BC_MDBC;ct.slipmode=SLIP_FreeSlip;
    ct.modulus_K=89478488.f;ct.modulus_G=134217728.f;ct.hydromech=1;ct.porewaterbulkmodulus=float(Kw);ct.porewaterrho=float(Rhow);ct.porosity=float(1.-Solid);ct.porekwn=float(Kw/(1.-Solid));ct.porecompgradcorr=ct.soilstressrategradcorr=1;
    ct.awen=sph.kwend.awen;ct.bwen=sph.kwend.bwen;const auto kc=sph.kcubic;ct.cubic_a1=kc.a1;ct.cubic_a2=kc.a2;ct.cubic_aa=kc.aa;ct.cubic_a24=kc.a24;ct.cubic_c1=kc.c1;ct.cubic_d1=kc.d1;ct.cubic_c2=kc.c2;ct.cubic_odwdeltap=kc.od_wdeltap;cusph::CteInteractionUp(&ct);
    for(unsigned q=Fixed;q<N;q++){const unsigned id=q-Fixed;double x=.5+(id%9)*Dp,zz=.5+(id/9)*Dp;if(jitter){if(id%2)x+=(id%3?1.:-1.)*Dp/16.;else zz+=(id%3?1.:-1.)*Dp/16.;}xy[q]=make_double2(x,0);z[q]=zz;code[q]=CODE_TYPE_FLUID;vel[q]=make_float4(0,0,0,2048);}
    for(unsigned w=0;w<Fixed;w++){const unsigned q=Fixed+36+8*w;const float shift=w?-.25f:.25f;xy[w]=make_double2(xy[q].x-shift,0);z[w]=z[q];bn[w]=make_float3(shift,0,0);vel[w]=make_float4(0,0,0,2048);}originalbn=bn;
    std::vector<float4> position(Cap);for(unsigned q=0;q<Cap;q++)position[q]=make_float4(float(xy[q].x),0,float(z[q]),0);
    Up(posg.p,position);Up(dc.p,std::vector<unsigned>(Cap,0));Up(cells.p,std::vector<int2>{make_int2(0,Fixed),make_int2(0,0),make_int2(Fixed,N),make_int2(0,0)});
    dvd=MakeDivDataGpu(1,TUint3(1,1,1),TUint3(0),cells.p,4,ct.cellcode,TDouble3(0),sph.kernelsize2,4);Upload();
    Cu(cudaMemset(dvg.p,0,Cap*sizeof(float3)));Cu(cudaMemset(tvg.p,0,Cap*sizeof(float3)));
  }
  void Affine(std::ostream& out,Coverage& totals,bool offset){
    bn=originalbn;if(offset)for(unsigned w=0;w<Fixed;w++)bn[w].x+=(bn[w].x>0?1.f:-1.f)*float(Dp/8.);
    for(unsigned q=Fixed;q<N;q++){const double x=xy[q].x,zz=z[q];j[q]=1.+x/1024.;p[q]=float(128.+256.*x+64.*zz);theta[q]=0;vel[q]=make_float4(float(.125+.5*x),0,float(-.25+.125*zz),2048);
      sigma[q]={16.+x,0,8.+32.*x,32.+2.*zz,0,64.+4.*x};c[q]=TMatrix3d(1.+x,0,.125+.5*x,0,0,0,.25+.125*zz,0,2.+zz);ace[q]=make_float3(float(.25+.5*x),0,float(-.125+.25*zz));}
    const auto oldj=j,oldtheta=theta;const auto oldp=p;const auto oldvel=vel;const auto olda=ace;const auto oldc=c;const auto olds=sigma;Upload();Wall(0);Wall(1);Wall(2);Download();
    const auto derivative=Down(dvg.p,Cap),tangent=Down(tvg.p,Cap);const auto gotmode=Down(modeg.p,Cap);
    for(unsigned q=Fixed;q<N;q++)Need(j[q]==oldj[q]&&theta[q]==oldtheta[q]&&p[q]==oldp[q]&&!memcmp(&vel[q],&oldvel[q],sizeof(float4))&&!memcmp(&ace[q],&olda[q],sizeof(float3))&&!memcmp(&c[q],&oldc[q],sizeof(tmatrix3d))&&!memcmp(&sigma[q],&olds[q],sizeof(tsymatrix3d)),"Wall kernels changed a native fluid input");
    for(unsigned w=0;w<Fixed;w++){const auto x=Pos(w)+ToTDouble3(bn[w]);double condition=0,distance=0;Condition(w,condition,distance);const double td=32768.*DBL_EPSILON*condition,tf=64.*FLT_EPSILON*condition;
      const double ej=fabs(j[w]-(1.+x.x/1024.)),ep=fabs(p[w]-float(128.+256.*x.x+64.*x.z));
      const double ev=Norm(Vec(derivative[w])-TDouble3(float(-(.125+.5*x.x)),0,float(-.25+.125*x.z))),ea=Norm(Vec(ace[w])-TDouble3(float(-(.25+.5*x.x)),0,float(-.125+.25*x.z)));
      const auto s=sigma[w];const double es=(std::max)({fabs(s.xx-(16.+x.x)),fabs(s.yy-(32.+2.*x.z)),fabs(s.zz-(64.+4.*x.x)),fabs(s.xz+(8.+32.*x.x)),fabs(s.xy),fabs(s.yz)});
      const auto m=c[w];const double ec=(std::max)({fabs(m.a11-(1.+x.x)),fabs(m.a33-(2.+x.z)),fabs(m.a13+(.125+.5*x.x)),fabs(m.a31+(.25+.125*x.z)),fabs(m.a12),fabs(m.a21),fabs(m.a22),fabs(m.a23),fabs(m.a32)});
      Need(ej<=2*td&&ep<=256*tf&&ev<=tf&&ea<=tf&&es<=128*td&&ec<=4*td,"Original affine state/C/Ace budget failed");
      Need(vel[w].x==0&&vel[w].y==0&&vel[w].z==0&&vel[w].w==2048&&gotmode[w]==BMODE_MDBC2&&tangent[w].x==0&&fabs(tangent[w].z-(-.25+.125*x.z))<=tf,"Fixed versus derivative/tangent velocity semantics changed");
      Need((offset?distance>0:distance==0)&&2.*fabs(.125+.5*x.x)>4*td&&2.*fabs(.25+.5*x.x)>tf,"Coincident/offgrid or reflection-negative witness empty");
      out<<Name()<<','<<h/Dp<<','<<jitter<<','<<offset<<','<<w<<','<<condition<<','<<distance<<','<<ej<<','<<ep<<','<<ev<<','<<es<<','<<ec<<','<<ea<<','<<td<<','<<tf<<'\n';totals.affine_rows++;
      totals.maxwall=(std::max)(totals.maxwall,(std::max)({ej/(2*td),ep/(256*tf),ev/tf,es/(128*td),ec/(4*td),ea/tf}));}
    if(!offset){for(unsigned q=Fixed;q<N;q++)p[q]=float(128.+32768.*xy[q].x*xy[q].x);Upload();Wall(0);const auto actual=Down(pg.p,Cap);
      for(unsigned w=0;w<Fixed;w++){const auto target=Pos(w)+ToTDouble3(bn[w]);unsigned nearest=Fixed;double best=DBL_MAX;for(unsigned q=Fixed;q<N;q++){const double d=Dot(target-Pos(q),target-Pos(q));if(d<best){best=d;nearest=q;}}Need(best==0&&actual[w]==p[nearest],"Coincident nonlinear pressure anchor lost original float value");totals.anchor_rows++;}}
    bn=originalbn;
  }
  void Rates(std::ostream& out,std::ostream& neg,Coverage& totals){
    for(unsigned f=0;f<7;f++){const bool law=f==6;const double k=f==0?0.:double(float(.0001));
      for(unsigned q=Fixed;q<N;q++){const double x=xy[q].x,zz=z[q];j[q]=1.+x/1024.;theta[q]=f==0?-1./32.:f>=5?.03125+x/16.:0.;p[q]=128;ace[q]=make_float3(0,0,0);vel[q]=make_float4(0,0,0,2048);sigma[q]={};
        if(f==2){p[q]=float(128.+125*x+500*zz);ace[q]=make_float3(-.125f,0,-.5f);}if(f==3)ace[q]=make_float3(0,0,.5f);
        if(f>=4){p[q]=float(128.+32*x*x+16*zz*zz);ace[q]=make_float3(float(x/8.),0,float(zz/16.));}}
      Upload();cusph::ComputeFreeSurfaceTracking(tk,true,N,Fixed,dvd,dc.p,posg.p,vg.p,codeg.p,cg.p,fs.p,fng.p,pdg.p,false,jg.p);Wall(0);Wall(1);Wall(2);Download();
      const auto beforep=p;const auto beforej=j,beforetheta=theta;const auto beforec=c;const auto beforea=ace;Rate(law,k);const auto actual=Down(rg.p,Cap);double ps=0,as=0;
      Need(actual[0]==Sentinel&&actual[1]==Sentinel&&actual[N]==Sentinel&&actual[N+1]==Sentinel,"Rate fixed-prefix/tail canary changed");
      for(unsigned q=Fixed;q<N;q++){const auto ref=Reference(q,law,k);const double e=fabs(double(actual[q])-ref.rate);Need(std::isfinite(actual[q])&&e<=ref.budget,"Original complete-rate propagated budget failed");
        if(f==1||f==3)Need(actual[q]==0,"Constant p/constant Ace rate is not exactly zero");if(f==0)Need(actual[q]==float(ref.rate),"k0 compression overwrite differs");
        out<<Name()<<','<<h/Dp<<','<<jitter<<','<<f<<','<<q<<','<<actual[q]<<','<<ref.rate<<','<<e<<','<<ref.budget<<','<<e/ref.budget<<','<<ref.pressure<<','<<ref.acceleration<<','<<ref.chain<<'\n';totals.rate_rows++;totals.maxrate=(std::max)(totals.maxrate,e/ref.budget);ps=(std::max)(ps,fabs(ref.pressure));as=(std::max)(as,fabs(ref.acceleration));}
      if(f==4)Need(ps>10*Reference(Fixed,false,k).budget&&as>10*Reference(Fixed,false,k).budget,"Separate pressure/Ace sources are empty");
      Need(Same(beforep,Down(pg.p,Cap))&&Same(beforej,Down(jg.p,Cap))&&Same(beforetheta,Down(thg.p,Cap))&&Same(beforec,Down(cg.p,Cap))&&Same(beforea,Down(ag.p,Cap)),"Rate kernel modified frozen physical inputs");
      if(f==4){std::vector<Ref> good(N);for(unsigned q=Fixed;q<N;q++)good[q]=Reference(q,false,k);
        for(unsigned bad=0;bad<3;bad++){const auto goodc=c;const auto gooda=ace;for(unsigned w=0;w<Fixed;w++){if(bad==0)c[w]=TMatrix3d(0);else if(bad==1)ace[w]=make_float3(0,0,0);else ace[w].x=-ace[w].x;}Up(cg.p,c);Up(ag.p,ace);Rate(false,k);const auto wrong=Down(rg.p,Cap);unsigned changed=0;double ratio=0;
          for(unsigned q=Fixed;q<N;q++){const auto r=Reference(q,false,k);Need(fabs(double(wrong[q])-r.rate)<=r.budget,"Negative-control kernel/reference budget failed");const double delta=fabs(double(wrong[q])-actual[q]);ratio=(std::max)(ratio,delta/(r.budget+good[q].budget));changed+=unsigned(delta>r.budget+good[q].budget);}
          Need(changed>0&&ratio>1.,"Wrong wall C/Ace rate witness empty");neg<<Name()<<','<<h/Dp<<','<<jitter<<','<<bad<<','<<changed<<','<<ratio<<'\n';totals.negative_rows++;c=goodc;ace=gooda;Up(cg.p,c);Up(ag.p,ace);}}
    }totals.conditions++;
  }
};

int main(int argc,char** argv){try{
  Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_OUTPUT_DIRECTORY");const fs::path out=argv[2];Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh output/existing parent required");fs::create_directory(out);Cu(cudaSetDevice(0));
  std::ofstream walls(out/"walls.csv"),rates(out/"rates.csv"),neg(out/"negative.csv");Need(walls&&rates&&neg,"Cannot create fresh component CSVs");for(auto* s:{&walls,&rates,&neg})*s<<std::setprecision(17);
  walls<<"kernel,h_over_dp,jitter,offgrid,wall,condition,nearest_distance_m,J_error,p_error,v_error,sigma_error,C_error,Ace_error,double_base_bound,float_base_bound\n";
  rates<<"kernel,h_over_dp,jitter,field,slot,actual_Pa_s,reference_Pa_s,error,budget,error_over_budget,pressure_source,acceleration_source,chain_source\n";
  neg<<"kernel,h_over_dp,jitter,wrong_wall_case,changed_receivers,max_effect_over_combined_budget\n";Coverage counts;
  for(TpKernel kernel:{KERNEL_Wendland,KERNEL_Cubic})for(float ratio:{1.8f,1.2f})for(bool jitter:{false,true}){Patch p(kernel,jitter,ratio);p.Affine(walls,counts,false);p.Affine(walls,counts,true);p.Rates(rates,neg,counts);}
  Need(counts.conditions==8&&counts.affine_rows==32&&counts.anchor_rows==16&&counts.rate_rows==4536&&counts.negative_rows==24,"Declared component coverage incomplete");
  for(auto* s:{&walls,&rates,&neg}){s->flush();Need(bool(*s),"Component CSV write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_cubic_component_r1\",\"passed\":true,\"kernel_conditions\":"<<counts.conditions<<",\"affine_wall_rows\":"<<counts.affine_rows<<",\"coincident_anchor_rows\":"<<counts.anchor_rows<<",\"rate_rows\":"<<counts.rate_rows<<",\"negative_rows\":"<<counts.negative_rows<<",\"max_rate_error_over_original_budget\":"<<counts.maxrate<<",\"max_wall_error_over_original_budget\":"<<counts.maxwall<<",\"actual_GPU_FS_wall_Darcy_wrappers\":true,\"CPU_direct_sum_reference\":true,\"CPU_production_Darcy_called\":false,\"physical_steps\":0,\"host_geometry_admission_tested\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}}
