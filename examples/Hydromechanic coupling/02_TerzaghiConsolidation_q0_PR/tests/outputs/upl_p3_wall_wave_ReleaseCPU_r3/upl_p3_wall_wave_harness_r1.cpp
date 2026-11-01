// Private actual fixed-wall standing wave. No public switch or formal-case entry.
// Additional saved-point force audits are rolled back byte-exactly; they are not integrator stages.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JDsFixedDt.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "FunSphKernel.h"
#include "FunctionsMath.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <vector>
#include <stdexcept>
JAppInfo AppInfo("DynamicPoreWallWaveCpu","r1","01-11-2026");
namespace fs=std::filesystem;
static void Need(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
static constexpr unsigned Native=1024,Fixed=256,Columns=26;
static constexpr double Dp0=1./512.,Width=1./16.,Lz=1./16.,FullLx=1./8.,A=1./512.,End=1./32768.;
using Row=std::array<double,Columns>;
struct Frame{double time=0;std::vector<Row> rows;};
static void Write(std::ofstream& out,const Frame& f){out.write(reinterpret_cast<const char*>(&f.time),8);for(const auto& r:f.rows)out.write(reinterpret_cast<const char*>(r.data()),8*Columns);Need(bool(out),"Physical write failed");}
static Frame Read(std::ifstream& in){Frame f;f.rows.resize(Native);in.read(reinterpret_cast<char*>(&f.time),8);for(auto& r:f.rows)in.read(reinterpret_cast<char*>(r.data()),8*Columns);Need(bool(in),"Truncated physical frame");return f;}
template<class T> struct Copy{
  T* pointer;std::vector<T> value;
  Copy(T* p,unsigned n):pointer(p){Need(p||!n,"Missing persistent audit array");if(n)value.assign(p,p+n);}
  void Restore()const{if(!value.empty())memcpy(pointer,value.data(),value.size()*sizeof(T));}
  bool Equal()const{return value.empty()||!memcmp(pointer,value.data(),value.size()*sizeof(T));}
};
class WallWave:public JSphCpuSingle{
  std::vector<unsigned> Soil,Wall;
  std::vector<tdouble3> X0,WallX0;
  double Cu=0,Pstar=0,Ustar=0,E0=0,MaxEnergy=0,MaxCfl=0,MaxDiffusion=0,MinBound=DBL_MAX;
  double MaxP=0,MaxV=0,MaxU=0,MaxBandP=0,MaxBandV=0,MaxBandU=0,EndpointP=0;
  double MaxFaceQ=0,MaxFaceV=0,MaxFaceQRatio=0,MaxFaceVRatio=0,MaxForceRatio=0;
  unsigned WrongZeroDetected=0,WrongCopyDetected=0;double MaxWrongZeroRatio=0,MaxWrongCopyRatio=0;
  unsigned ExplicitInit=0,ExplicitState=0,ExplicitMatrix=0,ExplicitAce=0,AuditForces=0,RollbackFrames=0,BandCount=0;
  bool ForceStatsDefined=false;
  using Linear=std::array<double,4>; // u,v,sigma_xx,p.
  struct Op{double kr,ks,ksig,ka,ell;};
  Op Discrete{},Continuum{};
  Linear DR{0,A,0,0},DF=DR,CR=DR;
  double RefTime=0;
  std::ofstream Policy,Diagnostics;
  static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
  static double Norm(tdouble3 a){return sqrt(Dot(a,a));}
  std::vector<unsigned> Map()const{
    std::vector<unsigned> m(CaseNp,UINT_MAX);unsigned soil=0,wall=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){
      Need(Idpc[p]<CaseNp&&m[Idpc[p]]==UINT_MAX,"Duplicate or unknown native ID");m[Idpc[p]]=p;
      if(CODE_IsFluid(Codec[p]))soil++;else{Need(CODE_IsFixed(Codec[p]),"Nonfixed boundary");wall++;}
    }
    Need(soil==Native&&wall==Fixed&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Native identity/exclusion changed");
    return m;
  }
  bool InBand(unsigned row)const{return (std::min)(X0[row].x,Width-X0[row].x)<=double(KernelSize);}
  tdouble3 Delta(unsigned p,unsigned q)const{auto d=Posc[p]-Posc[q];d.y=0;d.z-=Lz*std::round(d.z/Lz);return d;}
  void Reset(){
    for(unsigned p=0;p<Np;p++){
      const bool fluid=CODE_IsFluid(Codec[p]);
      Velrhopc[p]=TFloat4(fluid?float(A*sin(2*acos(-1.)*Posc[p].x/FullLx)):0.f,0,0,RhopZero);
      PorePressc[p]=PorePress0c[p]=PorePressRatec[p]=0;Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;PoroJc[p]=1;PoroThetac[p]=0;CorrMatc[p]=TMatrix3d(0);
      if(TangenVelc)TangenVelc[p]=TFloat3(0);
    }
  }
  double ComponentCondition(tdouble3 at)const{
    tmatrix3d mom=TMatrix3d(0);
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsFluid(Codec[p])){
      const auto d=Posc[p]-at;const double rr=d.x*d.x+d.z*d.z;if(rr>double(KernelSize2))continue;
      float fac;const double wab=fsph::GetKernel_WabFac<KERNEL_Wendland>(CSP,float(rr),fac);if(wab<=0)continue;
      const double w=double(MassFluid)/RhopZero*PoroJc[p]*wab,x=d.x/KernelH,z=d.z/KernelH;
      mom.a11+=w;mom.a12+=w*x;mom.a13+=w*z;mom.a21+=w*x;mom.a22+=w*x*x;mom.a23+=w*x*z;mom.a31+=w*z;mom.a32+=w*x*z;mom.a33+=w*z*z;
    }
    const double det=fmath::Determinant3x3(mom);Need(det>0,"Independent component fit support singular");const auto inv=fmath::InverseMatrix3x3(mom,det);
    const auto inf=[](const tmatrix3d& a){return (std::max)({fabs(a.a11)+fabs(a.a12)+fabs(a.a13),fabs(a.a21)+fabs(a.a22)+fabs(a.a23),fabs(a.a31)+fabs(a.a32)+fabs(a.a33)});};
    return (std::max)(1.,inf(mom)*inf(inv));
  }
  Frame Snapshot()const{
    const auto m=Map();Frame f;f.time=TimeStep;f.rows.resize(Native);
    for(unsigned row=0;row<Native;row++){
      const unsigned p=m[Soil[row]];const auto x=Posc[p];const auto v=Velrhopc[p];const auto s=Sigmac[p];const auto n=FSNormalc[p];const auto l=HydroMechLoadAcec[p];
      f.rows[row]={x.x,x.y,x.z,double(v.x),double(v.y),double(v.z),double(PorePressc[p]),double(PorePress0c[p]),PoroJc[p],PoroThetac[p],s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,double(Kplasticc[p]),double(FSTypec[p]),double(n.x),double(n.y),double(n.z),double(PosDivc[p]),double(l.x),double(l.y),double(l.z),double(v.w)};
      for(double z:f.rows[row])Need(std::isfinite(z),"Nonfinite snapshot");
    }return f;
  }
  void InitReference(){
    const auto m=Map();unsigned p=m[Soil[0]];double best=DBL_MAX;
    for(unsigned id:Soil){const unsigned q=m[id];const double r=pow(Posc[q].x-Width*.5,2)+pow(Posc[q].z-Lz*.5,2);if(r<best){best=r;p=q;}}
    const double k=2*acos(-1.)/FullLx,V=double(MassFluid)/RhopZero;double xx=0,xz=0,zz=0,kr=0,kd=0,kz=0,ell=0;unsigned count=0;
    for(unsigned id:Soil){const unsigned q=m[id];const auto d=Delta(p,q);const double r=Dot(d,d);if(r<ALMOSTZERO||r>double(KernelSize2))continue;
      const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(r)));
      xx-=V*d.x*g.x;xz-=V*d.x*g.z;zz-=V*d.z*g.z;kd-=V*sin(k*d.x)*g.x;kz-=V*sin(k*d.x)*g.z;
      const float dx=float(d.x),dz=float(d.z),fac=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,dx*dx+dz*dz);kr-=V*sin(k*d.x)*double(fac*dx);count++;
    }
    const double det=xx*zz-xz*xz;Need(count==36&&det>0,"Interior initial symbol support changed");
    const double cxx=zz/det,cxz=-xz/det,czz=xx/det;
    for(unsigned id:Soil){const auto d=Delta(p,m[id]);const double r=Dot(d,d);if(r<ALMOSTZERO||r>double(KernelSize2))continue;
      const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(r)));
      const auto cg=TDouble3(cxx*g.x+cxz*g.z,0,cxz*g.x+czz*g.z);ell-=2*V*Dot(d,cg)/(r+double(Eta2))*(1-cos(k*d.x));
    }
    const double ks=cxx*kd+cxz*kz;Discrete={kr,ks,cxx*kr,ks,ell};Continuum={k,k,k,k,k*k};
    Cu=sqrt((double(SoilCte.ModulusK)+4.*SoilCte.ModulusG/3.+double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity)/RhopZero);
    Pstar=double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity*A/Cu;Ustar=A/(Cu*k);
  }
  Linear Derivative(const Linear& y,Op op)const{
    const double B=double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity,M=double(SoilCte.ModulusK)+4.*SoilCte.ModulusG/3.;
    const double D=B*double(SoilCte.HydraulicConductivity)/(double(SoilCte.PoreWaterRho)*9.80665),a=op.kr*(y[3]-y[2])/RhopZero;
    return {y[1],a,M*op.ksig*y[1],-B*op.ks*y[1]-D*op.ell*y[3]+D*SoilCte.PoreWaterRho*op.ka*a};
  }
  Linear Advance(Linear x,Op op,double interval,unsigned pieces)const{
    const double h=interval/pieces;
    for(unsigned i=0;i<pieces;i++){const auto a=Derivative(x,op);auto y=x;for(unsigned j=0;j<4;j++)y[j]+=h*.5*a[j];const auto b=Derivative(y,op);
      y=x;for(unsigned j=0;j<4;j++)y[j]+=h*.5*b[j];const auto c=Derivative(y,op);y=x;for(unsigned j=0;j<4;j++)y[j]+=h*c[j];const auto d=Derivative(y,op);
      for(unsigned j=0;j<4;j++)x[j]+=h*(a[j]+2*b[j]+2*c[j]+d[j])/6.;
    }return x;
  }
  double Energy()const{
    double e=0;const auto m=Map();
    for(unsigned id:Soil){const unsigned p=m[id];double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);const auto s=Sigmac[p];const auto v=Velrhopc[p];const double tr=s.xx+s.yy+s.zz,mean=tr/3.;
      const double dev=pow(s.xx-mean,2)+pow(s.yy-mean,2)+pow(s.zz-mean,2)+2*(s.xy*s.xy+s.xz*s.xz+s.yz*s.yz);
      e+=V*(.5*rho*(double(v.x)*v.x+double(v.y)*v.y+double(v.z)*v.z)+dev/(4*SoilCte.ModulusG)+tr*tr/(18*SoilCte.ModulusK)+n*double(PorePressc[p])*PorePressc[p]/(2*SoilCte.PoreWaterBulkModulus));
    }return e;
  }
  void Guard(double dt,bool forces){
    const auto m=Map();double cu2max=0,dmax=0,marginmin=DBL_MAX;
    for(unsigned row=0;row<Native;row++){const unsigned p=m[Soil[row]];double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);const double j=PoroJc[p],B=double(SoilCte.PoreWaterBulkModulus)/n,M=double(SoilCte.ModulusK)+4.*SoilCte.ModulusG/3.,cu2=(M+B)/rho,D=B*SoilCte.HydraulicConductivity/(double(SoilCte.PoreWaterRho)*9.80665),margin=rho*B/(M+B)-SoilCte.PoreWaterRho;
      Need(std::isfinite(j)&&j>1-SoilCte.Porosity&&fabs(j-1)<=1e-4&&n>0&&n<1&&V>0&&rho>0&&fabs((1-n)*j-(1-SoilCte.Porosity))<=5e-13,"Invalid saturated ledger");
      Need(Posc[p].x>0&&Posc[p].x<Width&&Kplasticc[p]==0&&PorePress0c[p]==0&&Velrhopc[p].w>=RhopOutMin&&Velrhopc[p].w<=RhopOutMax,"Physical/elastic/passive-density guard failed");
      if(SoilCte.HydraulicConductivity>0)Need(margin>64*DBL_EPSILON*(std::max)(rho,double(SoilCte.PoreWaterRho)),"Outside positive-k RH domain");
      cu2max=(std::max)(cu2max,cu2);dmax=(std::max)(dmax,D);marginmin=(std::min)(marginmin,margin);
      MaxCfl=(std::max)(MaxCfl,sqrt(cu2)*dt/KernelH);MaxDiffusion=(std::max)(MaxDiffusion,D*dt/(double(KernelH)*KernelH));
      Need(sqrt(cu2)*dt/KernelH<=.01&&D*dt/(double(KernelH)*KernelH)<=.01&&(D==0||dt<=double(PoreDtSafety)*KernelH*KernelH/D),"Coupled CFL/diffusion limits failed");
    }
    for(unsigned row=0;row<Fixed;row++){const unsigned p=m[Wall[row]];Need(!memcmp(Posc+p,WallX0.data()+row,sizeof(tdouble3))&&Velrhopc[p].x==0&&Velrhopc[p].y==0&&Velrhopc[p].z==0&&Velrhopc[p].w==RhopZero,"Real fixed-wall position/physical velocity changed");}
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){Need(Idpc[p]<CaseNp&&m[Idpc[p]]!=UINT_MAX,"Periodic owner absent");const unsigned q=m[Idpc[p]];
      Need(PoroJc[p]==PoroJc[q]&&PoroThetac[p]==PoroThetac[q]&&PorePressc[p]==PorePressc[q]&&PorePress0c[p]==PorePress0c[q]&&PorePressRatec[p]==PorePressRatec[q],"Periodic scalar owner mismatch");
      Need(!memcmp(Velrhopc+p,Velrhopc+q,sizeof(tfloat4))&&!memcmp(Sigmac+p,Sigmac+q,sizeof(tsymatrix3d)),"Periodic velocity/stress owner mismatch");
    }
    const double ratio=Energy()/E0;Need(std::isfinite(ratio)&&ratio<=1.1,"Original energy1.1 bound failed");MaxEnergy=(std::max)(MaxEnergy,ratio);
    if(forces){double wave,pore;GetDynamicStepScalesCpu(wave,pore);const double wr=double(KernelH)/((std::max)(sqrt(cu2max),VelMax*10.)+double(KernelH)*ViscDtMax),pr=(dmax?double(PoreDtSafety)*KernelH*KernelH/dmax:DBL_MAX);
      Need(wave==wr&&pore==pr,"Endpoint necessary-scale reference failed");const double force=AceMax?sqrt(double(KernelH)/AceMax):DBL_MAX,bound=(std::min)(double(CFLnumber)*(std::min)(force,wave),pore);
      Need(dt<=bound&&DtMin<=bound&&fabs(FixedDt->GetDtError(false))<=1e-14,"Actual complete step bound failed");MinBound=(std::min)(MinBound,bound);
      Policy<<Nstep<<','<<TimeStep<<','<<dt<<','<<wave<<','<<pore<<','<<bound<<','<<marginmin<<','<<ratio<<','<<FixedDt->GetDtError(false)<<'\n';
    }
    Snapshot();
  }
  void Modes(std::ofstream& out){
    const double interval=TimeStep-RefTime,k=2*acos(-1.)/FullLx;if(interval){DR=Advance(DR,Discrete,interval,16);DF=Advance(DF,Discrete,interval,32);CR=Advance(CR,Continuum,interval,16);RefTime=TimeStep;}
    Need(fabs(DR[3]-DF[3])<=1e-8,"Independent reference self-check failed");
    const auto m=Map();double pm=0,vm=0,um=0,sm=0;std::array<double,3> e{},b{},ed{};
    for(unsigned row=0;row<Native;row++){const unsigned p=m[Soil[row]];const double sn=sin(k*X0[row].x),cs=cos(k*X0[row].x);const auto u=Posc[p]-X0[row];const auto v=Velrhopc[p];
      pm+=2*PorePressc[p]*cs/Native;vm+=2*v.x*sn/Native;um+=2*u.x*sn/Native;sm+=2*Sigmac[p].xx*cs/Native;
      const double pe=pow((PorePressc[p]-CR[3]*cs)/Pstar,2),ve=(pow(v.x-CR[1]*sn,2)+double(v.y)*v.y+double(v.z)*v.z)/(A*A),ue=(pow(u.x-CR[0]*sn,2)+u.y*u.y+u.z*u.z)/(Ustar*Ustar);
      e[0]+=pe;e[1]+=ve;e[2]+=ue;if(InBand(row)){b[0]+=pe;b[1]+=ve;b[2]+=ue;}
      ed[0]+=pow(PorePressc[p]-DR[3]*cs,2);ed[1]+=(pow(v.x-DR[1]*sn,2)+double(v.y)*v.y+double(v.z)*v.z)/(A*A);ed[2]+=(pow(u.x-DR[0]*sn,2)+u.y*u.y+u.z*u.z)/(Ustar*Ustar);
    }
    for(unsigned j=0;j<3;j++){e[j]=sqrt(e[j]/Native);b[j]=sqrt(b[j]/BandCount);ed[j]=sqrt(ed[j]/Native);Need(e[j]<=.01&&b[j]<=.01,"Predeclared full-field or material-wall-band1% objective failed");}
    MaxP=(std::max)(MaxP,e[0]);MaxV=(std::max)(MaxV,e[1]);MaxU=(std::max)(MaxU,e[2]);MaxBandP=(std::max)(MaxBandP,b[0]);MaxBandV=(std::max)(MaxBandV,b[1]);MaxBandU=(std::max)(MaxBandU,b[2]);
    if(TimeStep>0)EndpointP=pm/CR[3]-1.;
    out<<Nstep<<','<<TimeStep<<','<<Cu<<','<<vm<<','<<DR[1]<<','<<CR[1]<<','<<pm<<','<<DR[3]<<','<<CR[3]<<','<<um<<','<<DR[0]<<','<<CR[0]<<','<<sm<<','<<DR[2]<<','<<CR[2];
    for(double z:ed)out<<','<<z;for(double z:e)out<<','<<z;for(double z:b)out<<','<<z;out<<','<<Energy()/E0<<'\n';
  }
  void Component(const fs::path& folder){
    InitDynamicPoreWallCpu();ExplicitInit++;const auto m=Map();
    for(unsigned p=0;p<Np;p++)if(CODE_IsFluid(Codec[p])){const double x=Posc[p].x;
      Velrhopc[p]=TFloat4(float(.125+.5*x),0,float(-.25+.125*x),RhopZero);PoroJc[p]=1.+x/1024.;PoroThetac[p]=0;
      PorePressc[p]=float(128.+256*x);PorePress0c[p]=0;Sigmac[p]={16.+x,0,8.+32*x,32.+2*x,0,64.+4*x};Kplasticc[p]=0;
    }
    InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();
    for(unsigned p=0;p<Np;p++)if(CODE_IsFluid(Codec[p])){
      const double x=Posc[p].x;Acec[p]=TFloat3(float(.25+.5*x),0,float(-.125+.25*x));
      CorrMatc[p]={1.+x,0,.125+.5*x,0,0,0,.125+.5*x,0,2.+x};
    }
    const auto before=Snapshot();ComputeDynamicPoreWallStateCpu();ExplicitState++;ComputeDynamicPoreWallMatrixCpu();ExplicitMatrix++;ComputeDynamicPoreWallAccelerationCpu();ExplicitAce++;
    const auto after=Snapshot();Need(!memcmp(before.rows.data(),after.rows.data(),Native*sizeof(Row)),"Wall helper component modified native physical fields");
    std::ofstream csv(folder/"component.csv");csv<<std::setprecision(17)<<"id,target_x,J_error,p_error,v_error,sigma_error,C_error,ace_error,condition,double_base_tol,float_base_tol\n";
    unsigned nonzero=0;double maxj=0,maxp=0,maxv=0,maxs=0,maxc=0,maxa=0;
    for(unsigned id:Wall){const unsigned p=m[id];const auto target=Posc[p]+ToTDouble3(BoundNormalc[p]);const double x=target.x;
      const auto vm=TFloat3(float(-(.125+.5*x)),0,float(-.25+.125*x)),am=TFloat3(float(-(.25+.5*x)),0,float(-.125+.25*x));
      const tsymatrix3d s={16.+x,0,-(8.+32*x),32.+2*x,0,64.+4*x};
      const tmatrix3d c={1.+x,0,-(.125+.5*x),0,0,0,-(.125+.5*x),0,2.+x};
      const double ej=fabs(PoroJc[p]-(1.+x/1024.)),ep=fabs(PorePressc[p]-float(128.+256*x));
      const double ev=Norm(ToTDouble3(BoundDerivativeVelc[p])-ToTDouble3(vm)),ea=Norm(ToTDouble3(Acec[p])-ToTDouble3(am));
      const auto sc=Sigmac[p];const auto cc=CorrMatc[p];
      const double es=(std::max)({fabs(sc.xx-s.xx),fabs(sc.xy-s.xy),fabs(sc.xz-s.xz),fabs(sc.yy-s.yy),fabs(sc.yz-s.yz),fabs(sc.zz-s.zz)});
      const double ec=(std::max)({fabs(cc.a11-c.a11),fabs(cc.a12-c.a12),fabs(cc.a13-c.a13),fabs(cc.a21-c.a21),fabs(cc.a22-c.a22),fabs(cc.a23-c.a23),fabs(cc.a31-c.a31),fabs(cc.a32-c.a32),fabs(cc.a33-c.a33)});
      const double condition=ComponentCondition(target),td=32768*DBL_EPSILON*condition,tf=64*FLT_EPSILON*condition;
      Need(ej<=td*2&&ep<=tf*256&&ev<=tf&&ea<=tf&&es<=td*128&&ec<=td*4,"Explicit affine wall-closure component failed");
      Need(Velrhopc[p].x==0&&Velrhopc[p].y==0&&Velrhopc[p].z==0&&Velrhopc[p].w==RhopZero,"Wall reconstruction changed physical fixed velocity");
      nonzero+=unsigned(BoundDerivativeVelc[p].x!=0&&Acec[p].x!=0&&CorrMatc[p].a13!=0&&PoroJc[p]!=1.);
      maxj=(std::max)(maxj,ej);maxp=(std::max)(maxp,ep);maxv=(std::max)(maxv,ev);maxs=(std::max)(maxs,es);maxc=(std::max)(maxc,ec);maxa=(std::max)(maxa,ea);
      csv<<id<<','<<x<<','<<ej<<','<<ep<<','<<ev<<','<<es<<','<<ec<<','<<ea<<','<<condition<<','<<td<<','<<tf<<'\n';
    }
    Need(nonzero==Fixed,"Wall closure component was vacuous");PosInteraction_Forces();Reset();
    std::ofstream done(folder/"component.check.json");done<<std::setprecision(17)<<"{\"passed\":true,\"fixed_native\":"<<Fixed<<",\"nonvacuous\":"<<nonzero<<",\"explicit_Init_calls\":"<<ExplicitInit<<",\"explicit_State_calls\":"<<ExplicitState<<",\"explicit_Matrix_calls\":"<<ExplicitMatrix<<",\"explicit_Acceleration_calls\":"<<ExplicitAce<<",\"max_J_error\":"<<maxj<<",\"max_p_error\":"<<maxp<<",\"max_v_error\":"<<maxv<<",\"max_sigma_error\":"<<maxs<<",\"max_C_error\":"<<maxc<<",\"max_ace_error\":"<<maxa<<",\"physical_acceptance\":false}\n";
  }
  void FaceAndForce(); // Defined below; all-actual-support MLS, not a prescribed mirror average.
  void Audit(){
    const unsigned np=Np,npb=Npb;const Frame before=Snapshot();const double tm=TimeStep,sd=SymplecticDtPre,ld=LastDt;const unsigned step=Nstep;const auto stage=InterStep;const double fe=FixedDt->GetDtError(false);
    struct ForceStats{double velocity,acceleration;float visc;};ForceStats previous{};
    // Never read pre-force AceMax. First audit retains its real computed statistics;
    // later audits restore every previously defined force statistic exactly.
    if(ForceStatsDefined)previous={VelMax,AceMax,ViscDtMax};
    const Copy<tdouble3> pos(Posc,np);
    const Copy<unsigned> ids(Idpc,np),fs(FSTypec,np);const Copy<typecode> code(Codec,np);
    const Copy<tfloat4> vel(Velrhopc,np);const Copy<tsymatrix3d> sigma(Sigmac,np);const Copy<tmatrix3d> corr(CorrMatc,np);
    const Copy<float> p(PorePressc,np),p0(PorePress0c,np),rate(PorePressRatec,np),plastic(Kplasticc,np),pd(PosDivc,np);
    const Copy<double> j(PoroJc,np),theta(PoroThetac,np);const Copy<tfloat3> fn(FSNormalc,np),load(HydroMechLoadAcec,np),tangent(TangenVelc,np),bn(BoundNormalc,np);const Copy<byte> mode(BoundModec,np);
    Interaction_Forces(INTERSTEP_SymPredictor);AuditForces++;FaceAndForce();PosInteraction_Forces();
    Need(Np==np&&Npb==npb&&Nstep==step&&TimeStep==tm&&SymplecticDtPre==sd&&LastDt==ld&&pos.Equal()&&ids.Equal()&&code.Equal()&&bn.Equal(),"Extra force audit changed immutable clock/identity/geometry");
    vel.Restore();sigma.Restore();corr.Restore();p.Restore();p0.Restore();rate.Restore();plastic.Restore();pd.Restore();j.Restore();theta.Restore();fn.Restore();load.Restore();tangent.Restore();mode.Restore();fs.Restore();
    InterStep=stage;if(ForceStatsDefined){VelMax=previous.velocity;AceMax=previous.acceleration;ViscDtMax=previous.visc;}else ForceStatsDefined=true;
    Need(FixedDt->GetDtError(false)==fe,"Extra force changed fixed-step error telemetry");
    const auto after=Snapshot();Need(before.time==after.time&&!memcmp(before.rows.data(),after.rows.data(),Native*sizeof(Row)),"Extra force rollback changed26 native physical columns");RollbackFrames++;
  }
public:
  WallWave(){PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log,unsigned steps,bool smoke,bool k0){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);
    Need(SoilCte.HydraulicConductivity==float(.0001),"Original input conductivity changed");if(k0)SoilCte.HydraulicConductivity=0;
    Log->Printf("Private wall fixture actual k=%.17g (K0 CLI=%u)",double(SoilCte.HydraulicConductivity),unsigned(k0));
    LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Need(HydroMech&&Simulate2D&&TStep==STEP_Symplectic&&CaseNpb==Fixed&&CaseNfluid==Native&&CaseNp==Native+Fixed&&TBoundary==BC_MDBC&&SlipMode==SLIP_FreeSlip&&MdbcCorrector&&!PeriX&&!PeriY&&PeriZ,"Wrong real fixed-wall geometry/options");
    Need(!CaseNmoving&&!CaseNfloat&&!HourglassCpu&&!Shifting&&!Damping&&!RelaxZones&&!InOut&&!AccInput&&!NoPenetration&&!SoilBoundaryDerivativeSPR,"Auxiliary path outside scope");
    Need(Dp==Dp0&&MapRealPosMin.x==-4*Dp0&&MapRealPosMax.x==Width+4*Dp0&&MapRealPosMin.z==0&&MapRealSize.z==Lz&&TimeStep==0&&FixedDt&&TangenVelc&&BoundModec,"Wrong map/spacing/clock/mDBC arrays");
    Need(SoilCte.ModulusK==89478488.f&&SoilCte.ModulusG==134217728.f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==67108864.f&&SoilCte.Porosity==.25f&&RhopZero==2048&&double(MassFluid)/RhopZero==Dp0*Dp0&&KernelH==float(1.8*Dp0),"Changed actual fixed material");
    const auto m=Map();for(unsigned id=0;id<CaseNp;id++)if(CODE_IsFluid(Codec[m[id]]))Soil.push_back(id);else Wall.push_back(id);
    X0.resize(Native);WallX0.resize(Fixed);std::vector<bool> lattice(Native,false);unsigned left=0,right=0;
    std::ofstream nativecsv(fs::path(cfg->DirOut)/"native_ids.csv"),fixedcsv(fs::path(cfg->DirOut)/"fixed_ids.csv");nativecsv<<std::setprecision(17)<<"row,native_id,x0,y0,z0,wall_band\n";fixedcsv<<std::setprecision(17)<<"row,native_id,x0,y0,z0,plane_x\n";
    for(unsigned row=0;row<Native;row++){X0[row]=Posc[m[Soil[row]]];const auto x=X0[row];const double ix=x.x/Dp0-.5,iz=x.z/Dp0-.5;
      Need(ix==round(ix)&&iz==round(iz)&&ix>=0&&ix<32&&iz>=0&&iz<32&&x.y==0,"Wrong native soil lattice");const unsigned key=unsigned(ix)+32*unsigned(iz);Need(!lattice[key],"Duplicate soil coordinate");lattice[key]=true;BandCount+=unsigned(InBand(row));
      nativecsv<<row<<','<<Soil[row]<<','<<x.x<<','<<x.y<<','<<x.z<<','<<InBand(row)<<'\n';
    }
    Need(BandCount==256,"Material wall band changed");
    for(unsigned row=0;row<Fixed;row++){const unsigned p=m[Wall[row]];WallX0[row]=Posc[p];const auto n=ToTDouble3(BoundNormalc[p]);const double xp=Posc[p].x+n.x*.5;
      Need(n.y==0&&n.z==0&&n.x!=0&&((n.x>0&&xp==0)||(n.x<0&&xp==Width)),"Wall normal/plane invalid");if(n.x>0)left++;else right++;
      fixedcsv<<row<<','<<Wall[row]<<','<<Posc[p].x<<','<<Posc[p].y<<','<<Posc[p].z<<','<<xp<<'\n';
    }Need(left==128&&right==128,"Missing true fixed-wall face");
    const double dt=SymplecticDtPre;Need(dt==pow(2.,-25)||dt==pow(2.,-26),"Undeclared actual dt");
    const bool half=dt==pow(2.,-26);Need(smoke?steps==2:(k0?steps==(half?32u:16u):steps==(half?2048u:1024u)),"Undeclared duration/steps");
    const unsigned samples=smoke?3:(k0?17:257),stride=smoke?1:steps/(samples-1);const double stop=dt*steps;
    Reset();InitReference();Component(fs::path(cfg->DirOut));E0=Energy();Need(E0>0,"Zero initial energy");
    Policy.open(fs::path(cfg->DirOut)/"endpoint_policy.csv");Policy<<std::setprecision(17)<<"step,time_s,used_dt_s,wave_scale_s,pore_safety_scale_s,complete_bound_s,min_RH_margin,energy_ratio,cumulative_fixed_error_s\n";
    Diagnostics.open(fs::path(cfg->DirOut)/"wall_audit.csv");Diagnostics<<std::setprecision(17)<<"step,time_s,plane_x,face_vn,vn_bound,face_qn,qn_bound,fit_condition,neighbors,fluid_force_x,fluid_force_z,wall_reaction_x,wall_reaction_z,force_residual,force_bound,wrong_zero_mirror_ace_face_qn,wrong_copy_mirror_ace_face_qn\n";
    std::ofstream binary(fs::path(cfg->DirOut)/"physical.bin",std::ios::binary),modes(fs::path(cfg->DirOut)/"modes.csv");const unsigned header[3]={Native,Columns,samples};binary.write(reinterpret_cast<const char*>(header),sizeof(header));
    modes<<std::setprecision(17)<<"step,time_s,cu_actual,v_sine,v_discrete,v_continuum,p_cosine,p_discrete,p_continuum,u_sine,u_discrete,u_continuum,sigma_cosine,sigma_discrete,sigma_continuum,p_discrete_RMS_Pa,v_discrete_RMS_over_A,u_discrete_RMS_over_Ustar,p_continuum_RMS_over_Pstar,v_continuum_RMS_over_A,u_continuum_RMS_over_Ustar,p_band_RMS_over_Pstar,v_band_RMS_over_A,u_band_RMS_over_Ustar,energy_ratio\n";
    Guard(dt,false);Write(binary,Snapshot());Modes(modes);Audit();unsigned saved=1;
    for(unsigned it=0;it<steps;it++){InterStep=INTERSTEP_SymPredictor;const double used=ComputeStep_Sym();Need(used==dt,"Actual locked dt changed");RunCellDivide(true);TimeStep+=used;LastDt=used;UpdateMaxValues();Nstep++;Guard(dt,true);
      if((it+1)%stride==0){Write(binary,Snapshot());Modes(modes);Audit();saved++;}
    }
    Need(TimeStep==stop&&Nstep==steps&&saved==samples&&!PoroJPrec&&AuditForces==samples&&RollbackFrames==samples,"Incomplete actual/audit trajectory");
    if(!smoke&&!k0){Need(fabs(EndpointP)<=.01,"Predeclared endpoint pressure-mode1% failed");Need(WrongZeroDetected&&WrongCopyDetected,"Wall acceleration negative diagnostic was vacuous over the full window");}
    binary.flush();modes.flush();Policy.flush();Diagnostics.flush();nativecsv.flush();fixedcsv.flush();Need(binary&&modes&&Policy&&Diagnostics&&nativecsv&&fixedcsv,"Output write failure");
    std::ofstream done(fs::path(cfg->DirOut)/"complete.json");done<<std::setprecision(17)<<"{\"passed\":true,\"actual_ComputeStep_Sym\":true,\"Nx\":32,\"Nz\":32,\"native_ids\":"<<Native<<",\"fixed_ids\":"<<Fixed<<",\"band_native\":"<<BandCount<<",\"steps\":"<<steps<<",\"samples\":"<<samples<<",\"dt_actual\":"<<dt<<",\"actual_end_s\":"<<TimeStep<<",\"smoke\":"<<(smoke?"true":"false")<<",\"k0\":"<<(k0?"true":"false")<<",\"hydraulic_conductivity\":"<<double(SoilCte.HydraulicConductivity)<<",\"cu\":"<<Cu<<",\"Pstar\":"<<Pstar<<",\"Ustar\":"<<Ustar<<",\"max_energy_ratio\":"<<MaxEnergy<<",\"max_coupled_CFL\":"<<MaxCfl<<",\"max_Ddt_h2\":"<<MaxDiffusion<<",\"min_endpoint_bound_s\":"<<MinBound<<",\"max_continuum_p_RMS_normalized\":"<<MaxP<<",\"max_continuum_v_RMS_normalized\":"<<MaxV<<",\"max_continuum_u_RMS_normalized\":"<<MaxU<<",\"max_band_p_RMS_normalized\":"<<MaxBandP<<",\"max_band_v_RMS_normalized\":"<<MaxBandV<<",\"max_band_u_RMS_normalized\":"<<MaxBandU<<",\"endpoint_p_relative_error\":"<<EndpointP<<",\"max_face_qn\":"<<MaxFaceQ<<",\"max_face_vn\":"<<MaxFaceV<<",\"max_qn_bound_ratio\":"<<MaxFaceQRatio<<",\"max_vn_bound_ratio\":"<<MaxFaceVRatio<<",\"max_force_budget_ratio\":"<<MaxForceRatio<<",\"additional_saved_point_force_audits\":"<<AuditForces<<",\"rollback26_exact_frames\":"<<RollbackFrames<<",\"first_audit_initialized_force_statistics\":true,\"wrong_zero_mirror_ace_detected\":"<<WrongZeroDetected<<",\"wrong_copy_mirror_ace_detected\":"<<WrongCopyDetected<<",\"max_wrong_zero_face_bound_ratio\":"<<MaxWrongZeroRatio<<",\"max_wrong_copy_face_bound_ratio\":"<<MaxWrongCopyRatio<<",\"automatic_integrator_wall_helper_calls_directly_observed\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
void WallWave::FaceAndForce(){
  const auto m=Map();tdouble3 fluid=TDouble3(0),reaction=TDouble3(0);double pairabs=0;
  for(unsigned id:Soil){const unsigned i=m[id];double ni,Vi,rhoi;GetPorosityFeedbackStateCpu(i,ni,Vi,rhoi);fluid=fluid+ToTDouble3(Acec[i])*(rhoi*Vi);
    for(unsigned j=0;j<Np;j++){if(j==i)continue;const float dx=float(Posc[i].x-Posc[j].x),dz=float(Posc[i].z-Posc[j].z),r=dx*dx+dz*dz;if(r<ALMOSTZERO||r>KernelSize2)continue;
      if(j<Npb)Need(BoundModec[j]!=BMODE_MDBC2OFF,"Inactive mDBC wall participates in feedback quadrature");
      const float f=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,r),gx=f*dx,gz=f*dz;double nj,Vj,rhoj;GetPorosityFeedbackStateCpu(j,nj,Vj,rhoj);
      const auto si=ToTSymMatrix3f(Sigmac[i]),sj=ToTSymMatrix3f(Sigmac[j]);const double pw=double(PorePressc[i])+PorePressc[j];
      const auto force=TDouble3(Vi*Vj*((double(si.xx)+sj.xx-pw)*gx+(double(si.xz)+sj.xz)*gz),0,Vi*Vj*((double(si.zz)+sj.zz-pw)*gz+(double(si.xz)+sj.xz)*gx));
      pairabs+=Norm(force);if(j<Npb)reaction=reaction-force;
    }
  }
  const double residual=Norm(fluid+reaction),fb=128*FLT_EPSILON*pairabs+4096*DBL_EPSILON*(std::max)(1.,pairabs);Need(residual<=fb,"Fluid/wall reaction budget failed");MaxForceRatio=(std::max)(MaxForceRatio,residual/fb);
  for(unsigned side=0;side<2;side++){
    const auto face=TDouble3(side?Width:0,0,Lz*.5);tmatrix3d mom=TMatrix3d(0);tdouble3 rp=TDouble3(0),rv=TDouble3(0),ra=TDouble3(0);
    struct Sample{double w,bx,bz,p,v,a;bool wall;};std::vector<Sample> points;double pmax=1,vmax=A,amax=A*Cu*2*acos(-1.)/FullLx;
    for(unsigned j=0;j<Np;j++){const auto d=Posc[j]-face;const double rr=d.x*d.x+d.z*d.z;if(rr>double(KernelSize2))continue;float fac;const float wab=fsph::GetKernel_WabFac<KERNEL_Wendland>(CSP,float(rr),fac);if(wab<=0)continue;
      double n,V,rho;GetPorosityFeedbackStateCpu(j,n,V,rho);const double w=V*wab,bx=d.x/KernelH,bz=d.z/KernelH,p=PorePressc[j],v=(j<Npb?BoundDerivativeVelc[j].x:Velrhopc[j].x),a=Acec[j].x;
      points.push_back({w,bx,bz,p,v,a,j<Npb});mom.a11+=w;mom.a12+=w*bx;mom.a13+=w*bz;mom.a21+=w*bx;mom.a22+=w*bx*bx;mom.a23+=w*bx*bz;mom.a31+=w*bz;mom.a32+=w*bx*bz;mom.a33+=w*bz*bz;
      rp=rp+TDouble3(1,bx,bz)*(w*p);rv=rv+TDouble3(1,bx,bz)*(w*v);ra=ra+TDouble3(1,bx,bz)*(w*a);
      pmax=(std::max)(pmax,fabs(p));vmax=(std::max)(vmax,fabs(v));amax=(std::max)(amax,fabs(a));
    }
    const double determinant=fmath::Determinant3x3(mom);Need(points.size()>6&&determinant>0,"Independent face MLS support is singular");
    const auto inv=fmath::InverseMatrix3x3(mom,determinant);const auto inf=[](const tmatrix3d& a){return (std::max)({fabs(a.a11)+fabs(a.a12)+fabs(a.a13),fabs(a.a21)+fabs(a.a22)+fabs(a.a23),fabs(a.a31)+fabs(a.a32)+fabs(a.a33)});};
    const double condition=(std::max)(1.,inf(mom)*inf(inv)),vp=inv.a11*rv.x+inv.a12*rv.y+inv.a13*rv.z,ap=inv.a11*ra.x+inv.a12*ra.y+inv.a13*ra.z,gp=(inv.a21*rp.x+inv.a22*rp.y+inv.a23*rp.z)/KernelH;
    double sb=0,sa=0,gscale=0,bad0=0,badcopy=0;for(const auto& s:points){const double beta=s.w*(inv.a11+inv.a12*s.bx+inv.a13*s.bz),alpha=s.w*(inv.a21+inv.a22*s.bx+inv.a23*s.bz)/KernelH;sb+=fabs(beta);sa+=fabs(alpha);gscale+=fabs(alpha*s.p);bad0+=beta*(s.wall?0:s.a);badcopy+=beta*(s.wall?-s.a:s.a);}
    const double norm=(side?-1.:1.),kh=SoilCte.HydraulicConductivity,gamma=double(SoilCte.PoreWaterRho)*9.80665,rhow=SoilCte.PoreWaterRho,q=-kh/gamma*(gp+rhow*ap)*norm,vn=vp*norm;
    const double qstar=kh/gamma*(2*acos(-1.)/FullLx*Pstar+rhow*A*Cu*2*acos(-1.)/FullLx);
    // Explicit boundary truncation budget1e-4*characteristic is NOT a pure roundoff proof.
    const double bv=4*FLT_EPSILON*vmax*sb+4096*DBL_EPSILON*condition*vmax+1e-4*A;
    const double bq=kh/gamma*(2*FLT_EPSILON*pmax*sa+4*rhow*FLT_EPSILON*amax*sb+4096*DBL_EPSILON*condition*(gscale+rhow*amax))+1e-4*qstar;
    Need(bv<.01*A&&fabs(vn)<=bv,"Independent physical-plane normal velocity bound failed");
    if(kh>0)Need(bq<.01*qstar&&fabs(q)<=bq,"Independent physical-plane Darcy flux bound failed");else Need(q==0,"k0 face flux is nonzero");
    const double qbad0=-kh/gamma*(gp+rhow*bad0)*norm,qbadcopy=-kh/gamma*(gp+rhow*badcopy)*norm;
    if(kh>0&&Nstep){WrongZeroDetected+=unsigned(fabs(qbad0)>bq);WrongCopyDetected+=unsigned(fabs(qbadcopy)>bq);MaxWrongZeroRatio=(std::max)(MaxWrongZeroRatio,fabs(qbad0)/bq);MaxWrongCopyRatio=(std::max)(MaxWrongCopyRatio,fabs(qbadcopy)/bq);}
    MaxFaceV=(std::max)(MaxFaceV,fabs(vn));MaxFaceQ=(std::max)(MaxFaceQ,fabs(q));MaxFaceVRatio=(std::max)(MaxFaceVRatio,fabs(vn)/bv);if(kh>0)MaxFaceQRatio=(std::max)(MaxFaceQRatio,fabs(q)/bq);
    Diagnostics<<Nstep<<','<<TimeStep<<','<<face.x<<','<<vn<<','<<bv<<','<<q<<','<<bq<<','<<condition<<','<<points.size()<<','<<fluid.x<<','<<fluid.z<<','<<reaction.x<<','<<reaction.z<<','<<residual<<','<<fb<<','<<qbad0<<','<<qbadcopy<<'\n';
  }
}
static void Half(const fs::path& a,const fs::path& b,const fs::path& target){
  Need(!fs::exists(target),"Retained half check protected");std::ifstream x(a,std::ios::binary),y(b,std::ios::binary);unsigned hx[3],hy[3];x.read(reinterpret_cast<char*>(hx),12);y.read(reinterpret_cast<char*>(hy),12);
  Need(x&&y&&!memcmp(hx,hy,12)&&hx[0]==Native&&hx[1]==Columns&&(hx[2]==17||hx[2]==257),"Wrong half schema");
  for(const char* name:{"native_ids.csv","fixed_ids.csv"}){std::ifstream ia(a.parent_path()/name,std::ios::binary),ib(b.parent_path()/name,std::ios::binary);Need(ia.is_open()&&ib.is_open(),"Missing real ID ledger");const std::string sa((std::istreambuf_iterator<char>(ia)),std::istreambuf_iterator<char>()),sb((std::istreambuf_iterator<char>(ib)),std::istreambuf_iterator<char>());Need(!sa.empty()&&sa==sb,"Half native/fixed ID ledgers differ");}
  const double cu=sqrt((89478488.+4.*134217728./3.+67108864./.25)/2048.),ps=(67108864./.25)*A/cu,us=A/(cu*2*acos(-1.)/FullLx);
  double mp=0,mu=0,np=0,nv=0,nu=0,mj=0;
  for(unsigned it=0;it<hx[2];it++){const auto p=Read(x),q=Read(y);const double cadence=(hx[2]==17?pow(2.,-25):pow(2.,-23));Need(p.time==q.time&&p.time==it*cadence,"Half actual clocks differ");double pe=0,ve=0,ue=0;
    for(unsigned row=0;row<Native;row++){if(!it)Need(!memcmp(p.rows[row].data(),q.rows[row].data(),8*Columns),"Half initial material fields differ");const auto& u=p.rows[row];const auto& v=q.rows[row];pe+=pow(u[6]-v[6],2);double du=0;for(unsigned j=0;j<3;j++){du+=pow(u[j]-v[j],2);ve+=pow(u[3+j]-v[3+j],2);}ue+=du;mu=(std::max)(mu,1000*sqrt(du));mj=(std::max)(mj,fabs(u[8]-v[8]));}
    const double pr=sqrt(pe/Native),vr=sqrt(ve/Native)/A,ur=sqrt(ue/Native)/us;mp=(std::max)(mp,pr);np=(std::max)(np,pr/ps);nv=(std::max)(nv,vr);nu=(std::max)(nu,ur);
    Need(pr<=5&&mu<=.005&&pr/ps<=1e-4&&vr<=1e-4&&ur<=1e-4,"Original absolute/normalized independent half limit failed");
  }Need(x.peek()==std::char_traits<char>::eof()&&y.peek()==std::char_traits<char>::eof(),"Unreviewed trailing frames");
  std::ofstream out(target);out<<std::setprecision(17)<<"{\"passed\":true,\"samples\":"<<hx[2]<<",\"native_ids\":"<<Native<<",\"columns\":"<<Columns<<",\"max_pressure_RMS_Pa\":"<<mp<<",\"max_material_displacement_mm\":"<<mu<<",\"max_pressure_RMS_over_Pstar\":"<<np<<",\"max_velocity_vector_RMS_over_A\":"<<nv<<",\"max_displacement_vector_RMS_over_Ustar\":"<<nu<<",\"max_J_difference\":"<<mj<<",\"physical_acceptance\":false}\n";out.flush();Need(bool(out),"Half receipt write failed");
}
int main(int argc,char** argv){try{
  if(argc==5&&std::string(argv[1])=="--half"){Half(argv[2],argv[3],argv[4]);return 0;}
  Need(argc>8&&std::string(argv[1])=="--job","Use --job STEPS SMOKE K0 solverargs or --half A B NEWJSON");
  const unsigned steps=unsigned(std::stoul(argv[2]));const bool smoke=std::string(argv[3])=="1",k0=std::string(argv[4])=="1";Need((smoke||std::string(argv[3])=="0")&&(k0||std::string(argv[4])=="0"),"Invalid smoke/k0 flags");
  AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=5;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());cfg.Cpu=true;Need(!fs::exists(cfg.DirOut),"Retained output protected");
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");WallWave wave;wave.Execute(&cfg,AppInfo.LogPtr(),steps,smoke,k0);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Wall wave rejected; preserve output and Run.out\n";return 2;}}
