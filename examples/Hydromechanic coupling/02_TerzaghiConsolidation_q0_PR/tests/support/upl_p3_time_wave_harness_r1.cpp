// Immutable derivative of upl_p3_wave_harness_r1.cpp: only read-only time-policy audits added.
// Same equations, steps, samples, 26 physical columns and original numerical gates.
// The audited replay must match ComputeStep_Sym before its stage audit is used.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JDsFixedDt.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "FunSphKernel.h"
#include <limits>
#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <vector>
JAppInfo AppInfo("DynamicPoreTimeWaveCpu","r1","01-11-2026");
namespace fs=std::filesystem;
static void Check(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
static constexpr unsigned Native=128,Columns=26,Samples=257;
static constexpr double End=1./32768.,Lx=.125,Lz=.0625,Amplitude=1./512.;
using Row=std::array<double,Columns>;
struct Frame{double time;std::array<Row,Native> rows;};
static void WriteFrame(std::ofstream& file,const Frame& f){file.write(reinterpret_cast<const char*>(&f.time),sizeof(double));for(const auto& r:f.rows)file.write(reinterpret_cast<const char*>(r.data()),sizeof(double)*Columns);Check(bool(file),"Frame write failed");}
static Frame ReadFrame(std::ifstream& file){Frame f{};file.read(reinterpret_cast<char*>(&f.time),sizeof(double));for(auto& r:f.rows)file.read(reinterpret_cast<char*>(r.data()),sizeof(double)*Columns);Check(bool(file),"Frame read failed");return f;}
class Wave:public JSphCpuSingle{
  std::array<tdouble3,Native> Initial;
  double InitialEnergy=0,MaxCfl=0,MaxEos=0,MaxEnergy=0,MaxForce=0;
  unsigned StageCount=0;
  bool Auditing=false;
  std::array<double,Native> DarcyImpulse{};
  double MaxRateResidual=0,MaxRateTolerance=0,MaxThetaResidual=0,MaxFlowLog=0,MaxDiffusion=0;
  double MaxModeP=0,MaxModeV=0,MaxModeU=0,MinBudget=0,MaxBudget=0;
  std::ofstream Detail,Policy;
  unsigned PolicyCalls=0;
  double ExpectedFixedError=-DBL_MAX,MinPolicyBound=DBL_MAX,MinRhMargin=DBL_MAX;
  using Linear=std::array<double,4>; // U,V,Sxx,P modal coefficients.
  struct LinearOperator{double kr,ks,ksig,ka,ell;};
  LinearOperator Discrete{},Continuum{};
  Linear DiscreteRef{0,Amplitude,0,0},FineRef=DiscreteRef,ContinuumRef=DiscreteRef;
  double RefTime=0,Cu0=0;
  static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
  static tdouble3 Mul(const tmatrix3d& m,tdouble3 v){return TDouble3(m.a11*v.x+m.a12*v.y+m.a13*v.z,m.a21*v.x+m.a22*v.y+m.a23*v.z,m.a31*v.x+m.a32*v.y+m.a33*v.z);}
  tdouble3 Delta(unsigned p,unsigned q)const{
    auto d=Posc[p]-Posc[q];d.y=0;d.x-=Lx*std::round(d.x/Lx);d.z-=Lz*std::round(d.z/Lz);return d;
  }
  void InitReference(){
    const double k=2*acos(-1.)/Lx,V0=double(MassFluid)/RhopZero;
    double mxx=0,mxz=0,mzz=0,kr=0,kd=0,rawz=0,ell=0;
    const auto ids=Indices();const unsigned p=ids[0];
    for(unsigned q:ids)if(q!=p){
      const auto d=Delta(p,q);const double r2=Dot(d,d);if(r2>double(KernelSize2)||r2<ALMOSTZERO)continue;
      const double fac=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(r2));const auto g=d*fac;
      mxx-=V0*d.x*g.x;mxz-=V0*d.x*g.z;mzz-=V0*d.z*g.z;
      kd-=V0*sin(k*d.x)*g.x;rawz-=V0*sin(k*d.x)*g.z;
      const float dx=float(d.x),dz=float(d.z),rf=dx*dx+dz*dz;
      const float ff=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,rf);
      kr-=V0*sin(k*d.x)*double(ff*dx);
    }
    const double det=mxx*mzz-mxz*mxz,cxx=mzz/det,cxz=-mxz/det,czz=mxx/det;
    for(unsigned q:ids)if(q!=p){
      const auto d=Delta(p,q);const double r2=Dot(d,d);if(r2>double(KernelSize2)||r2<ALMOSTZERO)continue;
      const double fac=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(r2));const auto g=d*fac;
      const auto cg=TDouble3(cxx*g.x+cxz*g.z,0,cxz*g.x+czz*g.z);
      const double beta=Dot(d,cg)/(r2+double(Eta2));
      ell-=2*V0*beta*(1-cos(k*d.x));
    }
    const double ks=cxx*kd+cxz*rawz;
    Discrete={kr,ks,cxx*kr,ks,ell};Continuum={k,k,k,k,k*k};
    Cu0=sqrt((double(SoilCte.ModulusK)+4*double(SoilCte.ModulusG)/3+double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity)/RhopZero);
  }
  Linear Derivative(const Linear& x,const LinearOperator& op)const{
    const double B=double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity,M=double(SoilCte.ModulusK)+4*double(SoilCte.ModulusG)/3;
    const double D=B*double(SoilCte.HydraulicConductivity)/(double(SoilCte.PoreWaterRho)*9.80665);
    const double a=op.kr*(x[3]-x[2])/RhopZero;
    return {x[1],a,M*op.ksig*x[1],-B*op.ks*x[1]-D*op.ell*x[3]+D*SoilCte.PoreWaterRho*op.ka*a};
  }
  Linear Advance(Linear x,const LinearOperator& op,double interval,unsigned parts)const{
    const double h=interval/parts;
    for(unsigned it=0;it<parts;it++){
      const auto a=Derivative(x,op);auto y=x;for(unsigned j=0;j<4;j++)y[j]+=h*.5*a[j];const auto b=Derivative(y,op);
      y=x;for(unsigned j=0;j<4;j++)y[j]+=h*.5*b[j];const auto d=Derivative(y,op);
      y=x;for(unsigned j=0;j<4;j++)y[j]+=h*d[j];const auto e=Derivative(y,op);
      for(unsigned j=0;j<4;j++)x[j]+=h*(a[j]+2*b[j]+2*d[j]+e[j])/6;
    }return x;
  }
  std::array<unsigned,Native> Indices()const{
    std::array<unsigned,Native> ids;ids.fill(~0u);unsigned count=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){
      Check(CODE_IsFluid(Codec[p])&&Idpc[p]<Native&&ids[Idpc[p]]==~0u,"Wrong native identity");ids[Idpc[p]]=p;count++;
    }
    Check(count==Native&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Native exclusion/count changed");return ids;
  }
  double Energy()const{
    double energy=0;
    for(unsigned p:Indices()){
      double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);const auto s=Sigmac[p];const auto v=Velrhopc[p];
      const double tr=s.xx+s.yy+s.zz,mean=tr/3.;
      const double dev=(s.xx-mean)*(s.xx-mean)+(s.yy-mean)*(s.yy-mean)+(s.zz-mean)*(s.zz-mean)+2*(s.xy*s.xy+s.xz*s.xz+s.yz*s.yz);
      energy+=V*(.5*rho*(double(v.x)*v.x+double(v.y)*v.y+double(v.z)*v.z)+dev/(4*SoilCte.ModulusG)+tr*tr/(18*SoilCte.ModulusK)+n*double(PorePressc[p])*PorePressc[p]/(2*SoilCte.PoreWaterBulkModulus));
    }
    return energy;
  }
  void StateGuard(double dt,bool endpoint=true){
    const double n0=SoilCte.Porosity,kw=SoilCte.PoreWaterBulkModulus;
    const auto ids=Indices();
    for(unsigned p:ids){
      double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);const double j=PoroJc[p];
      Check(std::isfinite(j)&&std::isfinite(n)&&std::isfinite(V)&&std::isfinite(rho)&&j>1-n0&&V>0&&rho>0&&fabs(j-1)<=1e-4,"Invalid or out-of-window physical ledger");
      Check(fabs((1-n)*j-(1-n0))<=5e-13,"Solid-volume invariant failed");
      Check(std::isfinite(Velrhopc[p].w)&&Velrhopc[p].w>=RhopOutMin&&Velrhopc[p].w<=RhopOutMax,"Passive legacy rho left numerical-validity range");
      Check(Kplasticc[p]==0&&PorePress0c[p]==0,"Plasticity/reference pressure changed");
      const auto s=Sigmac[p];for(double x:{s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,double(Velrhopc[p].x),double(Velrhopc[p].y),double(Velrhopc[p].z),Posc[p].x,Posc[p].y,Posc[p].z,PoroThetac[p]})Check(std::isfinite(x),"Nonfinite physical state");
      const double eos=fabs(double(PorePressc[p])+kw*log((j-1+n0)/n0));if(SoilCte.HydraulicConductivity==0){MaxEos=(std::max)(MaxEos,eos);Check(eos<=.5,"Local k=0 storage/log consistency exceeded .5 Pa");}
      if(Auditing&&endpoint&&SoilCte.HydraulicConductivity>0){
        const double flow=fabs(double(PorePressc[p])+kw*log((j-1+n0)/n0)-DarcyImpulse[Idpc[p]]);
        MaxFlowLog=(std::max)(MaxFlowLog,flow);Check(flow<=.5,"Flow-adjusted storage/log residual exceeds .5 Pa");
      }
      const double D=kw/n*double(SoilCte.HydraulicConductivity)/(double(SoilCte.PoreWaterRho)*9.80665);
      const double diffusion=D*dt/(double(KernelH)*KernelH);
      MaxDiffusion=(std::max)(MaxDiffusion,diffusion);
      Check(diffusion<=.01&&(!D||dt<=double(PoreDtSafety)*KernelH*KernelH/D),"Manual current-porosity diffusion-step guard failed");
      const double cu=sqrt((double(SoilCte.ModulusK)+4*double(SoilCte.ModulusG)/3+kw/n)/rho),cfl=cu*dt/KernelH;
      MaxCfl=(std::max)(MaxCfl,cfl);Check(std::isfinite(cfl)&&cfl<=.01,"Manual coupled wave CFL exceeds .01");
    }
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){
      Check(Idpc[p]<Native&&PoroJc[p]==PoroJc[ids[Idpc[p]]],"Periodic J differs from owner at audited geometry");
      if(PoroJPrec)Check(PoroJPrec[p]==PoroJPrec[ids[Idpc[p]]],"Periodic Jpre differs from owner");
    }
    const double e=Energy()/InitialEnergy;MaxEnergy=(std::max)(MaxEnergy,e);Check(std::isfinite(e)&&e<=1.1,"Perturbation energy exceeds 1.1 initial");
  }
  void ForceGuard(double dt,const char* stage,std::ofstream& out){
    StateGuard(dt,false);double fx=0,fy=0,fz=0,scale=0,budget=0,compBudget=0,lapBudget=0,dynBudget=0,qpower=0,ratePower=0,maxerr=0,maxtol=0;
    const auto ids=Indices();const double kw=SoilCte.PoreWaterBulkModulus,rhow=SoilCte.PoreWaterRho,kh=SoilCte.HydraulicConductivity;
    const double gamma=rhow*9.80665,V0=double(MassFluid)/RhopZero;
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){
      const unsigned owner=ids[Idpc[p]];
      Check(!memcmp(CorrMatc+p,CorrMatc+owner,sizeof(tmatrix3d)),"Stage periodic C not copied from owner");
      Check(!memcmp(Acec+p,Acec+owner,sizeof(tfloat3))&&PoroThetac[p]==PoroThetac[owner]&&PorePressRatec[p]==PorePressRatec[owner],"Stage periodic Ace/theta/rate not copied from owner");
    }
    for(unsigned p:ids){
      double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);const auto a=Acec[p];const auto ci=CorrMatc[p];
      Check(std::isfinite(a.x)&&std::isfinite(a.y)&&std::isfinite(a.z)&&std::isfinite(PorePressRatec[p]),"Nonfinite force/rate");
      const double mass=rho*V;fx+=mass*a.x;fy+=mass*a.y;fz+=mass*a.z;scale+=mass*sqrt(double(a.x)*a.x+double(a.y)*a.y+double(a.z)*a.z);
      double lp=0,da=0,theta=0,thetaScale=0,assemblyScale=0;tdouble3 lx=TDouble3(0),gp=TDouble3(0);
      for(unsigned q:ids)if(q!=p){
        const auto d=Delta(p,q);const double rr=Dot(d,d);if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;
        const double fac=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr));const auto g=d*fac,gi=Mul(ci,g),gj=Mul(CorrMatc[q],g);
        const double vol=V0*PoroJc[q],dp=double(PorePressc[p])-PorePressc[q];
        const double w=vol*Dot(d,gi+gj)/(rr+double(Eta2));
        lp+=w*dp;lx=lx+d*w;gp=gp-gi*(vol*dp);
        da+=vol*((double(Acec[q].x)-a.x)*gi.x+(double(Acec[q].y)-a.y)*gi.y+(double(Acec[q].z)-a.z)*gi.z);
        assemblyScale+=fabs(w*dp)+fabs(vol*(double(Acec[q].x)-a.x)*gi.x*rhow)+fabs(vol*(double(Acec[q].z)-a.z)*gi.z*rhow);
        // Independent theta follows the admitted fused ct float displacement/dv path.
        const auto df=TDouble3(double(float(d.x)),0,double(float(d.z)));
        const double rrf=Dot(df,df),ff=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rrf));const auto gc=Mul(ci,df*ff);
        const double vx=-double(float(Velrhopc[p].x-Velrhopc[q].x)),vz=-double(float(Velrhopc[p].z-Velrhopc[q].z));
        const double term=vol*(vx*gc.x+vz*gc.z);theta+=term;thetaScale+=fabs(term);
      }
      const double terr=fabs(theta-PoroThetac[p]);MaxThetaResidual=(std::max)(MaxThetaResidual,terr);
      Check(terr<=4096*DBL_EPSILON*(std::max)(1.,thetaScale)+1e-10,"Independent full theta assembly differs");
      const double B=kw/n,star=lp-Dot(gp,lx),compression=-B*PoroThetac[p],diffusion=B*kh/gamma*star,dynamic=B*kh/gamma*rhow*da;
      const double reference=B*(-PoroThetac[p]+kh/gamma*(star+rhow*da));
      const float rounded=float(reference);const double ulp=(std::max)(fabs(double(std::nextafter(rounded,std::numeric_limits<float>::infinity()))-rounded),fabs(double(std::nextafter(rounded,-std::numeric_limits<float>::infinity()))-rounded));
      const double tolerance=2*ulp+4096*DBL_EPSILON*(std::max)(1.,fabs(compression)+B*kh/gamma*(assemblyScale+fabs(Dot(gp,lx))))+1e-7;
      const double err=fabs(double(PorePressRatec[p])-reference);maxerr=(std::max)(maxerr,err);maxtol=(std::max)(maxtol,tolerance);
      MaxRateResidual=(std::max)(MaxRateResidual,err);MaxRateTolerance=(std::max)(MaxRateTolerance,tolerance);Check(err<=tolerance,"Independent complete dynamic rate assembly differs; no duplicate/omitted term allowed");
      const auto qflux=(gp+TDouble3(a.x,a.y,a.z)*rhow)*(-kh/gamma);
      const double weight=V*n/kw;budget+=weight*PorePressRatec[p]+V*PoroThetac[p];compBudget+=weight*compression;lapBudget+=weight*diffusion;dynBudget+=weight*dynamic;
      ratePower+=weight*PorePressc[p]*PorePressRatec[p];if(kh>0)qpower+=V*gamma/kh*Dot(qflux,qflux);
      if(std::string(stage)=="corrector")DarcyImpulse[Idpc[p]]+=dt*(diffusion+dynamic);
      const unsigned id=Idpc[p];if(id==0||id==4||id==8||id==12||id==64||id==127){
        Detail<<Nstep<<','<<TimeStep<<','<<stage<<','<<id<<','<<Posc[p].x<<','<<Posc[p].z<<','<<Velrhopc[p].x<<','<<Velrhopc[p].z<<','<<PorePressc[p]<<','<<PoroJc[p]<<','<<n<<','<<V<<','<<rho<<','<<ci.a11<<','<<ci.a13<<','<<ci.a31<<','<<ci.a33<<','<<gp.x<<','<<gp.z<<','<<lp<<','<<lx.x<<','<<lx.z<<','<<star<<','<<a.x<<','<<a.y<<','<<a.z<<','<<da<<','<<qflux.x<<','<<qflux.z<<','<<compression<<','<<diffusion<<','<<dynamic<<','<<PorePressRatec[p]<<','<<reference<<','<<err<<','<<tolerance<<','<<theta<<','<<PoroThetac[p]<<','<<dt<<'\n';
      }
    }
    const double relative=sqrt(fx*fx+fy*fy+fz*fz)/(std::max)(1.,scale);MaxForce=(std::max)(MaxForce,relative);Check(relative<=256*FLT_EPSILON,"Instantaneous internal force budget failed");
    const double natural=CFLnumber*(std::min)(AceMax?sqrt(double(KernelH)/AceMax):DBL_MAX,double(KernelH)/((std::max)(Cs0,VelMax*10.)+double(KernelH)*ViscDtMax));
    Check(dt<=natural,"Fixed step exceeds separately audited legacy natural limit");
    MinBudget=(std::min)(MinBudget,budget);MaxBudget=(std::max)(MaxBudget,budget);
    out<<Nstep<<','<<TimeStep<<','<<stage<<','<<Np<<','<<relative<<','<<Energy()/InitialEnergy<<','<<MaxCfl<<','<<MaxDiffusion<<','<<natural<<','<<maxerr<<','<<maxtol<<','<<budget<<','<<compBudget<<','<<lapBudget<<','<<dynBudget<<','<<ratePower<<','<<qpower<<'\n';StageCount++;
  }
  void PolicyGuard(double used,double returned,const char* phase){
    const auto ids=Indices();const double M=double(SoilCte.ModulusK)+4.*double(SoilCte.ModulusG)/3.;
    const double kw=SoilCte.PoreWaterBulkModulus,rhow=SoilCte.PoreWaterRho,kh=SoilCte.HydraulicConductivity,n0=SoilCte.Porosity;
    const double gn=sqrt(double(Gravity.x)*Gravity.x+double(Gravity.y)*Gravity.y+double(Gravity.z)*Gravity.z),gamma=rhow*(gn>0?gn:9.80665);
    double maxcu2=0,maxD=0,marginmin=DBL_MAX;
    for(unsigned p:ids){
      const double J=PoroJc[p],n=1.-(1.-n0)/J,rho=rhow+(double(RhopZero)-rhow)/J,B=kw/n;
      const double cu2=(M+B)/rho,D=B*kh/gamma,margin=rho*B/(M+B)-rhow;
      Check(std::isfinite(cu2)&&cu2>0&&n>0&&n<1&&rho>0,"Independent time-policy state invalid");
      if(kh>0)Check(margin>64*DBL_EPSILON*(std::max)(rho,rhow),"Independent strict continuous decay-domain guard failed");
      maxcu2=(std::max)(maxcu2,cu2);maxD=(std::max)(maxD,D);marginmin=(std::min)(marginmin,margin);
    }
    const double wave=double(KernelH)/((std::max)(sqrt(maxcu2),VelMax*10.)+double(KernelH)*ViscDtMax);
    const double pore=maxD>0?double(PoreDtSafety)*double(KernelH)*KernelH/maxD:DBL_MAX;
    double actualwave,actualpore;GetDynamicStepScalesCpu(actualwave,actualpore);
    Check(actualwave==wave&&actualpore==pore,"Production current-state scales differ from independent assembly");
    const double force=AceMax?sqrt(double(KernelH)/AceMax):DBL_MAX,bound=(std::min)(double(CFLnumber)*(std::min)(force,wave),pore);
    Check(used<=bound&&returned==used&&double(DtMin)<=bound&&returned>=double(DtMin),"Fixed dyadic step changed or exceeded complete current-state bound");
    ExpectedFixedError=(std::max)(ExpectedFixedError,used-bound);
    const double observed=FixedDt->GetDtError(false);
    Check(observed==ExpectedFixedError,"FixedDt error telemetry did not use the complete bound");
    MinPolicyBound=(std::min)(MinPolicyBound,bound);MinRhMargin=(std::min)(MinRhMargin,marginmin);PolicyCalls++;
    Policy<<Nstep<<','<<TimeStep<<','<<phase<<','<<used<<','<<returned<<','<<wave<<','<<pore<<','<<force<<','<<bound<<','<<actualwave<<','<<actualpore<<','<<sqrt(maxcu2)<<','<<maxD<<','<<marginmin<<','<<double(DtMin)<<','<<observed<<','<<ExpectedFixedError<<'\n';
  }
  double AuditedStep(std::ofstream& out){
    const double dt=SymplecticDtPre;
    DemDtForce=dt*.5;Interaction_Forces(INTERSTEP_SymPredictor);ForceGuard(dt,"predictor",out);const double dp=DtVariable(false);PolicyGuard(dt,dp,"predictor");
    ComputeSymplecticPre(dt);PosInteraction_Forces();RunCellDivide(true);
    DemDtForce=dt;Interaction_Forces(INTERSTEP_SymCorrector);ForceGuard(dt,"corrector",out);const double dc=DtVariable(true);PolicyGuard(dt,dc,"corrector");
    ComputeSymplecticCorr(dt);PosInteraction_Forces();SymplecticDtPre=(std::min)(dp,dc);return dt;
  }
  Frame Snapshot()const{
    Frame f{};f.time=TimeStep;const auto ids=Indices();
    for(unsigned id=0;id<Native;id++){
      const unsigned p=ids[id];const auto x=Posc[p];const auto v=Velrhopc[p];const auto s=Sigmac[p];const auto n=FSNormalc[p];const auto load=HydroMechLoadAcec[p];
      f.rows[id]={x.x,x.y,x.z,double(v.x),double(v.y),double(v.z),double(PorePressc[p]),double(PorePress0c[p]),PoroJc[p],PoroThetac[p],s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,double(Kplasticc[p]),double(FSTypec[p]),double(n.x),double(n.y),double(n.z),double(PosDivc[p]),double(load.x),double(load.y),double(load.z),double(v.w)};
      for(double q:f.rows[id])Check(std::isfinite(q),"Nonfinite serialized state");
    }
    return f;
  }
  void Modes(std::ofstream& out){
    const double interval=TimeStep-RefTime,k=2*acos(-1.)/Lx;
    if(interval){DiscreteRef=Advance(DiscreteRef,Discrete,interval,16);FineRef=Advance(FineRef,Discrete,interval,32);ContinuumRef=Advance(ContinuumRef,Continuum,interval,16);RefTime=TimeStep;}
    Check(fabs(DiscreteRef[3]-FineRef[3])<=1e-8,"Offline coupled linear RK4 reference self-check failed");
    double vs=0,pc=0,us=0,sc=0,ep=0,ev=0,eu=0,eosmass=0;
    const auto ids=Indices();for(unsigned id=0;id<Native;id++){
      const unsigned p=ids[id];const double phase=k*Initial[id].x,sn=sin(phase),cs=cos(phase),u=Posc[p].x-Initial[id].x;
      vs+=2.*Velrhopc[p].x*sn/Native;pc+=2.*PorePressc[p]*cs/Native;us+=2.*u*sn/Native;sc+=2.*Sigmac[p].xx*cs/Native;
      ep+=pow(PorePressc[p]-DiscreteRef[3]*cs,2);ev+=pow(Velrhopc[p].x-DiscreteRef[1]*sn,2);eu+=pow(u-DiscreteRef[0]*sn,2);
      double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);eosmass+=SoilCte.PoreWaterRho*exp(double(PorePressc[p])/SoilCte.PoreWaterBulkModulus)*n*V;
    }
    ep=sqrt(ep/Native);ev=sqrt(ev/Native)/Amplitude;eu=sqrt(eu/Native)/(Amplitude/(Cu0*k));
    MaxModeP=(std::max)(MaxModeP,ep);MaxModeV=(std::max)(MaxModeV,ev);MaxModeU=(std::max)(MaxModeU,eu);
    Check(ep<=1&&ev<=1e-3&&eu<=1e-3,"Predeclared coupled discrete-mode reference bound failed");
    out<<Nstep<<','<<TimeStep<<','<<Cu0<<','<<vs<<','<<DiscreteRef[1]<<','<<ContinuumRef[1]<<','<<pc<<','<<DiscreteRef[3]<<','<<ContinuumRef[3]<<','<<us<<','<<DiscreteRef[0]<<','<<ContinuumRef[0]<<','<<sc<<','<<DiscreteRef[2]<<','<<ContinuumRef[2]<<','<<ep<<','<<ev<<','<<eu<<','<<Energy()/InitialEnergy<<','<<eosmass<<'\n';
  }
public:
  Wave(){PorosityObserver=true;PorosityFeedback=true;DynamicPorePressure=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log,bool audit,bool poison,unsigned steps){
    Auditing=audit;AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Check(HydroMech&&Simulate2D&&TStep==STEP_Symplectic&&!CaseNpb&&CaseNfluid==Native&&PeriX&&PeriZ&&!PeriY,"Expected 16x8 no-wall periodic 2D geometry");
    Check(!CaseNmoving&&!CaseNfloat&&!HourglassCpu&&!Shifting&&!Damping&&!RelaxZones&&!InOut&&!AccInput,"Audited replay does not admit auxiliary paths");
    Check(MapRealSize.x==Lx&&MapRealSize.z==Lz&&Dp==1./128.&&TimeStep==0&&FixedDt,"Unexpected geometry/clock/fixed-step input");
    const double dt=End/steps;Check(SymplecticDtPre==dt&&(steps==256||steps==512),"Only the declared dyadic coarse/half step admitted");
    auto ids=Indices();for(unsigned id=0;id<Native;id++)Initial[id]=Posc[ids[id]];
    for(unsigned p=0;p<Np;p++){
      Velrhopc[p].x=float(Amplitude*sin(2*acos(-1.)*Initial[Idpc[p]].x/Lx));Velrhopc[p].y=Velrhopc[p].z=0;
      if(poison)Velrhopc[p].w=float(1400+100*(Idpc[p]%7));
      Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;PorePressc[p]=PorePress0c[p]=0;PoroJc[p]=1;PoroThetac[p]=0;
    }
    ExpectedFixedError=FixedDt->GetDtError(false);
    Policy.open(fs::path(cfg->DirOut)/"time_policy.csv");Policy<<std::setprecision(17)<<"step,source_clock_s,phase,used_dt_s,returned_dt_s,wave_scale_s,pore_safety_scale_s,force_scale_s,complete_bound_s,actual_wave_scale_s,actual_pore_scale_s,max_cu,max_D,min_RH_margin,DtMin_s,fixed_error_s,independent_max_fixed_error_s\n";
    InitReference();InitialEnergy=Energy();Check(InitialEnergy>0,"Zero initial wave energy");StateGuard(dt);
    std::ofstream binary(fs::path(cfg->DirOut)/"physical.bin",std::ios::binary),mode(fs::path(cfg->DirOut)/"modes.csv"),stage(fs::path(cfg->DirOut)/"stages.csv");
    const unsigned header[3]={Native,Columns,Samples};binary.write(reinterpret_cast<const char*>(header),sizeof(header));
    mode<<std::setprecision(17)<<"step,time_s,cu_actual,v_sine,v_discrete,v_continuum,p_cosine,p_discrete,p_continuum,u_sine,u_discrete,u_continuum,sigma_cosine,sigma_discrete,sigma_continuum,p_discrete_RMS_Pa,v_discrete_RMS_over_A,u_discrete_RMS_over_A_omega,energy_ratio,EOS_water_mass_diagnostic\n";
    stage<<std::setprecision(17)<<"step,source_clock_s,force_stage,np_with_clones,force_budget_relative,energy_ratio,max_coupled_CFL,max_Ddt_h2,legacy_natural_dt_s,max_rate_error_Pa_s,max_rate_tolerance_Pa_s,linear_storage_budget,compression_budget,lap_budget,dynamic_budget,pressure_power,positive_q_power\n";
    Detail.open(fs::path(cfg->DirOut)/"stage_detail.csv");Detail<<std::setprecision(17)<<"step,source_clock_s,stage,id,x,z,vx,vz,p,J,n,V,rho_t,Cxx,Cxz,Czx,Czz,Gpx,Gpz,Lpair,Lx,Lz,Lstar,Acex,Acey,Acez,divAce,qx,qz,compression,diffusion,dynamic,total_float_rate,independent_rate,error,tolerance,independent_theta,theta,dt\n";
    WriteFrame(binary,Snapshot());Modes(mode);unsigned samples=1;
    for(unsigned it=0;it<steps;it++){
      InterStep=INTERSTEP_SymPredictor;
      const double used=audit?AuditedStep(stage):ComputeStep_Sym();Check(used==dt,"Fixed step unexpectedly changed");
      RunCellDivide(true);TimeStep+=used;LastDt=used;UpdateMaxValues();Nstep++;StateGuard(dt);
      if((it+1)%(steps/256)==0){WriteFrame(binary,Snapshot());Modes(mode);samples++;}
    }
    Check(TimeStep==End&&Nstep==steps&&samples==Samples&&!PoroJPrec,"Incomplete dyadic trajectory");
    Check(StageCount==(audit?2*steps:0)&&PolicyCalls==(audit?2*steps:0),"Unexpected stage or policy audit count");binary.flush();mode.flush();stage.flush();Detail.flush();Policy.flush();Check(bool(binary)&&bool(mode)&&bool(stage)&&bool(Detail)&&bool(Policy),"Diagnostic output failed");
    std::ofstream done(fs::path(cfg->DirOut)/"complete.json");done<<std::setprecision(17)<<"{\"passed\":true,\"native_ids\":128,\"samples\":257,\"steps\":"<<steps<<",\"actual_end_s\":"<<TimeStep<<",\"audited_replay\":"<<(audit?"true":"false")<<",\"actual_ComputeStep_Sym\":"<<(audit?"false":"true")<<",\"rho_poison\":"<<(poison?"true":"false")<<",\"force_stage_audits\":"<<StageCount<<",\"max_coupled_CFL\":"<<MaxCfl<<",\"max_EOS_error_Pa\":"<<MaxEos<<",\"max_energy_ratio\":"<<MaxEnergy<<",\"max_force_budget_relative\":"<<MaxForce<<",\"max_rate_residual_Pa_s\":"<<MaxRateResidual<<",\"max_rate_tolerance_Pa_s\":"<<MaxRateTolerance<<",\"max_theta_residual\":"<<MaxThetaResidual<<",\"max_flow_adjusted_log_error_Pa\":"<<MaxFlowLog<<",\"max_Ddt_h2\":"<<MaxDiffusion<<",\"max_discrete_pressure_RMS_Pa\":"<<MaxModeP<<",\"max_discrete_v_RMS_normalized\":"<<MaxModeV<<",\"max_discrete_u_RMS_normalized\":"<<MaxModeU<<",\"storage_budget_min\":"<<MinBudget<<",\"storage_budget_max\":"<<MaxBudget<<",\"hydraulic_conductivity\":"<<SoilCte.HydraulicConductivity<<",\"discrete_Kr\":"<<Discrete.kr<<",\"discrete_Ks\":"<<Discrete.ks<<",\"discrete_Ksig\":"<<Discrete.ksig<<",\"discrete_ell\":"<<Discrete.ell<<",\"time_policy_calls\":"<<PolicyCalls<<",\"min_time_policy_bound_s\":"<<(audit?MinPolicyBound:0)<<",\"min_RH_margin\":"<<(audit?MinRhMargin:0)<<",\"max_fixed_dt_error_s\":"<<FixedDt->GetDtError(false)<<",\"physical_acceptance\":false}\n";
    done.flush();Check(bool(done),"Completion write failed");
  }
};
static void Compare(const fs::path& left,const fs::path& right,const std::string& comparison,const fs::path& target){
  const bool half=comparison=="half",rhoTwin=comparison=="rho",p2=comparison=="p2";
  Check(!fs::exists(target),"Retained comparison protected");std::ifstream a(left,std::ios::binary),b(right,std::ios::binary);unsigned ha[3],hb[3];a.read(reinterpret_cast<char*>(ha),sizeof(ha));b.read(reinterpret_cast<char*>(hb),sizeof(hb));
  Check(a&&b&&!memcmp(ha,hb,sizeof(ha))&&ha[0]==Native&&ha[1]==Columns&&ha[2]==Samples,"Snapshot header mismatch");double maxp=0,maxu=0,maxj=0;std::array<unsigned long long,Columns> maxulp{},changed{};
  for(unsigned sample=0;sample<Samples;sample++){
    const Frame x=ReadFrame(a),y=ReadFrame(b);Check(!memcmp(&x.time,&y.time,sizeof(double)),"Actual sample clocks differ");double sum=0;
    for(unsigned id=0;id<Native;id++){
      if(!half&&!p2)Check(!memcmp(x.rows[id].data(),y.rows[id].data(),sizeof(double)*(rhoTwin?Columns-1:Columns)),"Same-dt state differs");
      if(rhoTwin)Check(memcmp(&x.rows[id][25],&y.rows[id][25],sizeof(double))!=0,"Legacy-rho twin did not actually perturb density");
      if(p2)for(unsigned col=0;col<Columns;col++){
        const double a=x.rows[id][col],b=y.rows[id][col];unsigned long long ua=0,ub=0;
        memcpy(&ua,&a,8);memcpy(&ub,&b,8);if(ua!=ub)changed[col]++;
        ua=(ua>>63)?~ua:ua|(1ull<<63);ub=(ub>>63)?~ub:ub|(1ull<<63);
        maxulp[col]=(std::max)(maxulp[col],ua>ub?ua-ub:ub-ua);
      }
      const auto& p=x.rows[id];const auto& q=y.rows[id];const double dp=p[6]-q[6];sum+=dp*dp;
      const double du=1000*sqrt((p[0]-q[0])*(p[0]-q[0])+(p[1]-q[1])*(p[1]-q[1])+(p[2]-q[2])*(p[2]-q[2]));
      maxu=(std::max)(maxu,du);maxj=(std::max)(maxj,fabs(p[8]-q[8]));Check(du<=.005,"Half material displacement exceeds .005 mm");
    }
    const double rms=sqrt(sum/Native);maxp=(std::max)(maxp,rms);Check(rms<=5,"Half pressure RMS exceeds5 Pa");
  }
  Check(a.peek()==std::char_traits<char>::eof()&&b.peek()==std::char_traits<char>::eof(),"Extra unreviewed samples");
  std::ofstream out(target);out<<std::setprecision(17)<<"{\"passed\":true,\"samples\":257,\"native_ids\":128,\"columns\":26,\"half_comparison\":"<<(half?"true":"false")<<",\"legacy_rho_excluded\":"<<(rhoTwin?"true":"false")<<",\"same_dt_bitwise_equal_except_declared_rho\":"<<((half||p2)?"false":"true")<<",\"max_pressure_RMS_Pa\":"<<maxp<<",\"max_material_displacement_mm\":"<<maxu<<",\"max_J_difference\":"<<maxj<<",\"p2_descriptive_comparison\":"<<(p2?"true":"false")<<",\"max_binary64_ulp_by_column\":[";for(unsigned col=0;col<Columns;col++){if(col)out<<',';out<<maxulp[col];}out<<"],\"changed_records_by_column\":[";for(unsigned col=0;col<Columns;col++){if(col)out<<',';out<<changed[col];}out<<"],\"physical_acceptance\":false}\n";out.flush();Check(bool(out),"Comparison write failed");
}
int main(int argc,char** argv){
  try{
    Check(argc>=2,"Use --job audit|actual POISON STEPS solverargs or --compare A B exact|rho|half NEW_JSON");
    if(std::string(argv[1])=="--compare"){Check(argc==6,"Missing comparison arguments");Check(std::string(argv[4])=="exact"||std::string(argv[4])=="rho"||std::string(argv[4])=="half"||std::string(argv[4])=="p2","Invalid comparison mode");Compare(argv[2],argv[3],argv[4],argv[5]);return 0;}
    Check(std::string(argv[1])=="--job"&&argc>8,"Missing wave job arguments");const bool audit=std::string(argv[2])=="audit";Check(audit||std::string(argv[2])=="actual","Invalid step engine");
    const bool poison=std::string(argv[3])=="1";Check(poison||std::string(argv[3])=="0","Invalid poison flag");const unsigned steps=unsigned(std::stoul(argv[4]));Check(steps==256||steps==512,"Invalid bounded step count");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> arguments{argv[0]};for(int i=5;i<argc;i++)arguments.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(arguments.size()),arguments.data());cfg.Cpu=true;
    Check(!fs::exists(cfg.DirOut),"Retained job output protected");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Wave wave;wave.Execute(&cfg,AppInfo.LogPtr(),audit,poison,steps);return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Wave rejected; preserve partial outputs and Run.out\n";return 2;}
}


