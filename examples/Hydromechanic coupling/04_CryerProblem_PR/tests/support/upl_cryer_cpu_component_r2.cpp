// Non-advancing private CPU3D component. Observer allocation is valid; feedback INIT admission is BYPASSED.
#define main RetainedCryerComponentNativeMain
#include "../../../02_TerzaghiConsolidation_q0_PR/tests/support/upl_cpu_public_native_r1.cpp"
#undef main
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JDsFixedDt.h"
#include "JLog2.h"
#include "JCellSearch_inline.h"
#include "FunSphKernel.h"

namespace cryercomponent {
constexpr unsigned Fixed=8,Soil=37173,Total=37181,Probes=6;
const unsigned Samples[8]={8,100,1000,10000,20000,30000,37179,37180};
const char* Names[Probes]={"constant_p_totalstress0","affine_XYZ_p_totalstress0","affine_compression","cyclic_tracefree_shear","raw_confinement_only","raw_confinement_cancel"};
struct Mat {double a[3][3]={};};
static tdouble3 Apply(const tmatrix3d& c,tdouble3 g){return TDouble3(c.a11*g.x+c.a12*g.y+c.a13*g.z,c.a21*g.x+c.a22*g.y+c.a23*g.z,c.a31*g.x+c.a32*g.y+c.a33*g.z);}
static double FPgamma(unsigned n,double u){Need(n*u<.5,"Declared arithmetic operation bound exhausted");return n*u/(1.-n*u);}
static double RoundBudget(unsigned n,double raw,bool single){return FPgamma(n,(single?FLT_EPSILON:DBL_EPSILON)*.5)*raw+256.*DBL_EPSILON*(std::max)(1.,raw);}
struct Reference {
  double theta=0,thetaBudget=0,rate=0,rateBudget=0,cmRatio=0,rawRatio=0,loadRatio=0,loadBudget=0;
  std::array<double,6> stress{},stressBudget{};
  tdouble3 rawLoad=TDouble3(0),rawBudget=TDouble3(0);bool storeGate=false;
  unsigned neighbors=0;
};
struct Stats {
  double theta=0,rate=0,pmin=DBL_MAX,pmax=-DBL_MAX,thetaRatio=0,rateRatio=0,stressRatio=0,cmRatio=0,rawRatio=0,loadRatio=0;
  double aceMax=0,loadMax=0,loadResultant[3]={},stress[6]={},rateAbsMax=0;unsigned surface[4]={},storeOpen=0,storeClosed=0;
};
class Component:public JSphCpuSingle {
  std::vector<tdouble3> X0;std::vector<tmatrix3d> BaselineC;std::vector<unsigned> BaselineFS;
  std::vector<tfloat3> BaselineNormal;std::ofstream Summary,Sample;
  double Locked=0,OriginalLast=0,OriginalError=0,MinimumDummyDistance=DBL_MAX;
  unsigned Calls=0,SoilChecks=0,SampleRows=0;bool HaveC=false;
  std::vector<unsigned> Owners()const{
    std::vector<unsigned> map(Total,~0u);unsigned fixed=0,soil=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){
      Need(Idpc[p]<Total&&map[Idpc[p]]==~0u,"Duplicate/unknown normal Cryer ID");map[Idpc[p]]=p;
      if(Idpc[p]<Fixed){Need(CODE_IsFixed(Codec[p]),"Dummy ID is not fixed");fixed++;}
      else{Need(CODE_IsFluid(Codec[p]),"Soil ID is not fluid");soil++;}
    }
    Need(fixed==Fixed&&soil==Soil&&Np==Total&&Npb==Fixed&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Cryer owner/exclusion closure failed");return map;
  }
  void Clock()const{
    Need(!TimeStep&&!Nstep&&SymplecticDtPre==Locked&&LastDt==OriginalLast&&FixedDt->GetDtError(false)==OriginalError
      &&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Non-advancing component changed clock/history");
  }
  std::vector<byte> Inputs()const{
    std::vector<byte> out;auto add=[&](const auto& v){const byte* p=reinterpret_cast<const byte*>(&v);out.insert(out.end(),p,p+sizeof(v));};
    const auto map=Owners();
    for(unsigned id=0;id<Total;id++){const unsigned p=map[id];Need(!std::memcmp(Posc+p,&X0[id],sizeof(tdouble3)),"Seed geometry moved");add(Idpc[p]);add(Codec[p]);add(Dcellc[p]);add(Posc[p]);
      if(id>=Fixed){add(Velrhopc[p]);add(Sigmac[p]);add(PoroJc[p]);add(PorePressc[p]);add(PorePress0c[p]);add(Kplasticc[p]);}}
    return out;
  }
  void Reset(unsigned probe){
    Clock();Need(!Acec&&!Arc&&!Rsigmac&&!BoundDerivativeVelc&&!HydroMechTopLoadRawc,"Previous force scratch still live");
    HydroMechTopLoadMode=(probe==4||probe==5?HMLOAD_FlexibleConfinement:HMLOAD_None);
    HydroMechTopLoadQ0=10000.f;HydroMechTopLoadRampTime=0.; // Manufactured instantaneous source at t=0 ONLY, never an actual ramp/initial state.
    const auto map=Owners();
    for(unsigned id=0;id<Total;id++){const unsigned p=map[id];const tdouble3 x=Posc[p];
      float pressure=0;tfloat3 v=TFloat3(0);
      if(id>=Fixed){if(probe==0)pressure=1.f;if(probe==1)pressure=float(1.+16.*x.x-8.*x.y+4.*x.z);if(probe==5)pressure=10000.f;
        if(probe==2)v=TFloat3(float(-.001*x.x),float(-.001*x.y),float(-.001*x.z));
        if(probe==3)v=TFloat3(float(.001*x.y),float(.001*x.z),float(.001*x.x));}
      Velrhopc[p]=TFloat4(v.x,v.y,v.z,RhopZero);PorePressc[p]=pressure;PorePress0c[p]=0;PoroJc[p]=1.;PoroThetac[p]=0.;PorePressRatec[p]=123.25f;Kplasticc[p]=0;
      const double s=(probe==0||probe==1?double(pressure):0.);Sigmac[p]=TSymMatrix3d(s,0,0,s,0,s);HydroMechLoadAcec[p]=TFloat3(0);
    }
    RunCellDivide(true);Clock(); // No periodic particles, but real sorting and boundary path are retained.
  }
  Reference Ref(unsigned i,unsigned probe)const{
    Reference r;const tmatrix3d ci=CorrMatc[i];const double volume=double(MassFluid)/double(RhopZero),rho=RhopZero,kw=SoilCte.PoreWaterBulkModulus,n0=SoilCte.Porosity;
    Mat moment,rawgrad,gradabs;double thetaAbs=0,lp=0,lpAbs=0,da=0,daAbs=0;tdouble3 gp=TDouble3(0),gpa=TDouble3(0),lx=TDouble3(0),lxa=TDouble3(0);
    double rawAbs[3]={},loadAbs[3]={};unsigned forceNeighbors=0;
    const StNgSearch ngs=nsearch::Init(Dcellc[i],false,DivData);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 range=nsearch::ParticleRange(y,z,ngs,DivData);
      for(unsigned j=range.x;j<range.y;j++)if(CODE_IsFluid(Codec[j])){
        const tdouble3 d=Posc[i]-Posc[j];const double rr=Norm2(d);const float dx=float(d.x),dy=float(d.y),dz=float(d.z),rf=dx*dx+dy*dy+dz*dz;
        // Actual FS correction uses double d, float rr2/kernel factor and J-derived double quadrature.
        if(float(rr)<=KernelSize2&&float(rr)>=ALMOSTZERO){const double f=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr));const double a[3]={d.x,d.y,d.z},g[3]={f*d.x,f*d.y,f*d.z};
          for(int u=0;u<3;u++)for(int v=0;v<3;v++)moment.a[u][v]-=a[u]*g[v]*volume;}
        // Complete Darcy rate uses double geometry; it is independently assembled with observed C/Ace.
        if(rr<=double(KernelSize2)&&rr>=ALMOSTZERO){
          r.neighbors++;const double f=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr));const tdouble3 g=d*f,gi=Apply(ci,g),gj=Apply(CorrMatc[j],g);
          const double dp=double(PorePressc[i])-double(PorePressc[j]),w=volume*(d.x*(gi.x+gj.x)+d.y*(gi.y+gj.y)+d.z*(gi.z+gj.z))/(rr+double(Eta2));
          const double l=w*dp;lp+=l;lpAbs+=std::fabs(l);lx=lx+d*w;lxa=lxa+TDouble3(std::fabs(d.x*w),std::fabs(d.y*w),std::fabs(d.z*w));
          gp=gp-gi*(volume*dp);gpa=gpa+TDouble3(std::fabs(gi.x*volume*dp),std::fabs(gi.y*volume*dp),std::fabs(gi.z*volume*dp));
          const double a=volume*((double(Acec[j].x)-Acec[i].x)*gi.x+(double(Acec[j].y)-Acec[i].y)*gi.y+(double(Acec[j].z)-Acec[i].z)*gi.z);da+=a;daAbs+=std::fabs(a);
        }
        if(rf>KernelSize2||rf<ALMOSTZERO)continue;
        forceNeighbors++;const float fac=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,rf),fr[3]={fac*dx,fac*dy,fac*dz};
        const float dv[3]={Velrhopc[i].x-Velrhopc[j].x,Velrhopc[i].y-Velrhopc[j].y,Velrhopc[i].z-Velrhopc[j].z};
        for(int a=0;a<3;a++){const float t=dv[a]*(-float(volume));for(int b=0;b<3;b++){const double term=double(float(t*fr[b]));rawgrad.a[a][b]+=term;gradabs.a[a][b]+=std::fabs(term);}}
        const double rt=double(dx)*dx+double(dy)*dy+double(dz)*dz;
        if(rt<=double(KernelSize2)&&rt>=ALMOSTZERO){const double fac2=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rt));const tdouble3 gc=Apply(ci,TDouble3(double(dx)*fac2,double(dy)*fac2,double(dz)*fac2));
          const double t=volume*(-double(dv[0])*gc.x-double(dv[1])*gc.y-double(dv[2])*gc.z);r.theta+=t;thetaAbs+=std::fabs(t);}
        if(probe==4||probe==5){const double coeff=volume/rho;const float pc=float(2.*10000.*volume/rho);
          for(int a=0;a<3;a++){const double solid=(probe==5?double(float(coeff*(-20000.*double(fr[a])))):0.),load=double(float(pc*fr[a]));rawAbs[a]+=std::fabs(solid)+std::fabs(load);loadAbs[a]+=std::fabs(load);
            if(a==0)r.rawLoad.x+=load;if(a==1)r.rawLoad.y+=load;if(a==2)r.rawLoad.z+=load;}
        }
      }
    }
    Need(r.neighbors>0&&forceNeighbors>0,"Missing actual 3-D support");
    const double c[3][3]={{ci.a11,ci.a12,ci.a13},{ci.a21,ci.a22,ci.a23},{ci.a31,ci.a32,ci.a33}};Mat grad,err;
    for(int a=0;a<3;a++)for(int b=0;b<3;b++){
      double cm=0,absCM=0;for(int k=0;k<3;k++){cm+=c[a][k]*moment.a[k][b];absCM+=std::fabs(c[a][k]*moment.a[k][b]);}
      const double cmb=RoundBudget(32*r.neighbors+128,(std::max)(1.,absCM),false);Need(std::isfinite(cm)&&std::isfinite(cmb)&&cmb>0,"Nonfinite C-moment reference");r.cmRatio=(std::max)(r.cmRatio,std::fabs(cm-(a==b?1.:0.))/cmb);
      double mag=0;for(int k=0;k<3;k++){grad.a[a][b]+=rawgrad.a[a][k]*c[b][k];mag+=std::fabs(c[b][k])*gradabs.a[a][k];}
      err.a[a][b]=FPgamma(forceNeighbors,FLT_EPSILON*.5)*mag+64.*DBL_EPSILON*(std::max)(1.,mag)+4.*FLT_EPSILON*(std::fabs(grad.a[a][b])+FPgamma(forceNeighbors,FLT_EPSILON*.5)*mag);
    }
    const double diag=float(SoilCte.ModulusK+4.*SoilCte.ModulusG/3.),off=float(SoilCte.ModulusK-2.*SoilCte.ModulusG/3.),shear=SoilCte.ModulusG;
    const int u[6]={0,0,0,1,1,2},v[6]={0,1,2,1,2,2};
    for(unsigned s=0;s<6;s++){const int a=u[s],b=v[s];double mag=0,bound=0;
      if(a==b){for(int k=0;k<3;k++){const double stiffness=(k==a?diag:off);r.stress[s]+=stiffness*grad.a[k][k];mag+=std::fabs(stiffness*grad.a[k][k]);bound+=std::fabs(stiffness)*err.a[k][k];}}
      else{r.stress[s]=shear*(grad.a[a][b]+grad.a[b][a]);mag=std::fabs(shear)*(std::fabs(grad.a[a][b])+std::fabs(grad.a[b][a]));bound=std::fabs(shear)*(err.a[a][b]+err.a[b][a]);}
      r.stressBudget[s]=bound+64.*FLT_EPSILON*(std::max)(1.,mag)+256.*DBL_EPSILON*(std::max)(1.,mag)+1e-6;
    }
    r.thetaBudget=RoundBudget(32*forceNeighbors+128,thetaAbs,false);
    const double raw=lpAbs+gpa.x*lxa.x+gpa.y*lxa.y+gpa.z*lxa.z+double(SoilCte.PoreWaterRho)*daAbs;
    const double lap=lp-gp.x*lx.x-gp.y*lx.y-gp.z*lx.z+double(SoilCte.PoreWaterRho)*da;
    const double mobility=double(SoilCte.HydraulicConductivity)/(double(SoilCte.PoreWaterRho)*9.80665);
    r.rate=kw/n0*(-r.theta+mobility*lap);
    const double rateMag=kw/n0*(thetaAbs+mobility*raw);
    r.rateBudget=kw/n0*(r.thetaBudget+mobility*RoundBudget(64*r.neighbors+256,raw,false))+64.*FLT_EPSILON*(std::max)(1.,rateMag)+256.*DBL_EPSILON*(std::max)(1.,rateMag)+1e-6;
    if(probe==4||probe==5){const double ac[3]={Acec[i].x,Acec[i].y,Acec[i].z},actual[3]={HydroMechLoadAcec[i].x,HydroMechLoadAcec[i].y,HydroMechLoadAcec[i].z},ref[3]={r.rawLoad.x,r.rawLoad.y,r.rawLoad.z};
      Need(Arc[i]==0&&!Shifting&&ViscDtMax==0,"Raw-load telemetry gate needs zero density rate/shift/viscous diagnostic");r.storeGate=(ac[0]!=0||ac[1]!=0||ac[2]!=0); // Current CPU2771 skips retained LoadAce when finished pair Ace,ar,visc are all zero.
      double* rb[3]={&r.rawBudget.x,&r.rawBudget.y,&r.rawBudget.z};
      for(int a=0;a<3;a++){const double b=RoundBudget(2*forceNeighbors+128,rawAbs[a],true)+64.*FLT_EPSILON*(std::max)(1.,rawAbs[a])+1e-6;*rb[a]=b;
        const double lb=RoundBudget(forceNeighbors+64,loadAbs[a],true)+64.*FLT_EPSILON*(std::max)(1.,loadAbs[a])+1e-6;
        r.rawRatio=(std::max)(r.rawRatio,std::fabs(ac[a]-(probe==4?ref[a]:0.))/b);
        r.loadRatio=(std::max)(r.loadRatio,std::fabs(actual[a]-(r.storeGate?ref[a]:0.))/lb);r.loadBudget=(std::max)(r.loadBudget,lb);}}
    return r;
  }
  void Force(unsigned probe){
    Reset(probe);const auto before=Inputs();Interaction_Forces(INTERSTEP_SymPredictor);Calls++;Clock();Need(Inputs()==before,"Actual force altered manufactured soil input bytes");
    const auto map=Owners();Stats s;const double v0=double(MassFluid)/double(RhopZero);
    for(unsigned id=Fixed;id<Total;id++){const unsigned i=map[id];Need(PoroJc[i]==1.&&Velrhopc[i].w==RhopZero&&PorePress0c[i]==0&&Kplasticc[i]==0&&FSTypec[i]<4,"Native elastic/J/FS guard failed");
      if(HaveC)Need(!std::memcmp(CorrMatc+i,&BaselineC[id-Fixed],sizeof(tmatrix3d))&&FSTypec[i]==BaselineFS[id-Fixed]&&!std::memcmp(FSNormalc+i,&BaselineNormal[id-Fixed],sizeof(tfloat3)),"Frozen J1 geometry changed actual C/FS");
      else{BaselineC[id-Fixed]=CorrMatc[i];BaselineFS[id-Fixed]=FSTypec[i];BaselineNormal[id-Fixed]=FSNormalc[i];}
      const Reference r=Ref(i,probe);const double actual[6]={Rsigmac[i].xx,Rsigmac[i].xy,Rsigmac[i].xz,Rsigmac[i].yy,Rsigmac[i].yz,Rsigmac[i].zz};
      const double tr=std::fabs(PoroThetac[i]-r.theta)/r.thetaBudget,pr=std::fabs(double(PorePressRatec[i])-r.rate)/r.rateBudget;
      Need(Finite(Acec[i])&&Finite(PoroThetac[i])&&Finite(PorePressRatec[i])&&Finite(HydroMechLoadAcec[i])&&r.cmRatio<=1&&tr<=1&&pr<=1,"Conditional C/theta/complete-rate propagation guard failed");
      s.cmRatio=(std::max)(s.cmRatio,r.cmRatio);s.thetaRatio=(std::max)(s.thetaRatio,tr);s.rateRatio=(std::max)(s.rateRatio,pr);
      for(unsigned k=0;k<6;k++){const double ratio=std::fabs(actual[k]-r.stress[k])/r.stressBudget[k];Need(std::isfinite(actual[k])&&ratio<=1,"Actual six-component stress-rate propagation guard failed");s.stress[k]+=actual[k];s.stressRatio=(std::max)(s.stressRatio,ratio);}
      if(probe<4)Need(Acec[i].x==0&&Acec[i].y==0&&Acec[i].z==0&&HydroMechLoadAcec[i].x==0&&HydroMechLoadAcec[i].y==0&&HydroMechLoadAcec[i].z==0,"Zero total stress generated momentum/source");
      if(probe<2||probe>=4)Need(PoroThetac[i]==0&&std::all_of(actual,actual+6,[](double a){return a==0;}),"Static input generated a strain/stress rate");
      if(probe==0)Need(PorePressRatec[i]==0,"Nonzero-constant pressure and zero-total-stress source must remain strict zero");
      Need(r.rawRatio<=1&&r.loadRatio<=1,"Raw uniform total-stress/confinement cancellation propagation guard failed");s.rawRatio=(std::max)(s.rawRatio,r.rawRatio);s.loadRatio=(std::max)(s.loadRatio,r.loadRatio);
      s.theta+=PoroThetac[i];s.rate+=PorePressRatec[i];s.rateAbsMax=(std::max)(s.rateAbsMax,std::fabs(double(PorePressRatec[i])));s.pmin=(std::min)(s.pmin,double(PorePressc[i]));s.pmax=(std::max)(s.pmax,double(PorePressc[i]));s.aceMax=(std::max)(s.aceMax,std::sqrt(Norm2(Acec[i])));s.surface[FSTypec[i]]++;s.loadMax=(std::max)(s.loadMax,std::sqrt(Norm2(HydroMechLoadAcec[i])));if(probe>=4){if(r.storeGate)s.storeOpen++;else s.storeClosed++;}
      s.loadResultant[0]+=RhopZero*v0*HydroMechLoadAcec[i].x;s.loadResultant[1]+=RhopZero*v0*HydroMechLoadAcec[i].y;s.loadResultant[2]+=RhopZero*v0*HydroMechLoadAcec[i].z;SoilChecks++;
      if(std::find(std::begin(Samples),std::end(Samples),id)!=std::end(Samples)){Sample<<probe<<','<<Names[probe]<<','<<id<<','<<Posc[i].x<<','<<Posc[i].y<<','<<Posc[i].z<<','<<PorePressc[i]<<','<<Velrhopc[i].x<<','<<Velrhopc[i].y<<','<<Velrhopc[i].z<<','<<PoroThetac[i]<<','<<r.theta<<','<<r.thetaBudget;
        for(unsigned k=0;k<6;k++)Sample<<','<<actual[k]<<','<<r.stress[k]<<','<<r.stressBudget[k];
        Sample<<','<<PorePressRatec[i]<<','<<r.rate<<','<<r.rateBudget<<','<<Acec[i].x<<','<<Acec[i].y<<','<<Acec[i].z<<','<<HydroMechLoadAcec[i].x<<','<<HydroMechLoadAcec[i].y<<','<<HydroMechLoadAcec[i].z<<','<<r.cmRatio<<','<<r.rawRatio<<','<<r.loadRatio<<','<<r.storeGate<<','<<r.rawLoad.x<<','<<r.rawLoad.y<<','<<r.rawLoad.z<<','<<r.rawBudget.x<<','<<r.rawBudget.y<<','<<r.rawBudget.z;
        const auto cm=CorrMatc[i];for(double a:{cm.a11,cm.a12,cm.a13,cm.a21,cm.a22,cm.a23,cm.a31,cm.a32,cm.a33})Sample<<','<<a;Sample<<'\n';SampleRows++;}
    }
    if(probe==4)Need(s.aceMax>0&&s.loadMax>0,"Actual confinement-only force/source did not activate");
    HaveC=true;double wave,pore;GetDynamicStepScalesCpu(wave,pore);Need(std::isfinite(wave)&&wave>0&&std::isfinite(pore)&&pore>0&&DynamicConductivitySpeedMax==0,"Constant-law scales/cache invalid");
    Summary<<probe<<','<<Names[probe]<<','<<Soil<<','<<s.pmin<<','<<s.pmax<<','<<s.theta/Soil<<','<<s.rate/Soil<<','<<s.rateAbsMax<<','<<s.aceMax<<','<<s.cmRatio<<','<<s.thetaRatio<<','<<s.rateRatio<<','<<s.stressRatio<<','<<s.rawRatio<<','<<s.loadRatio;
    for(double a:s.stress)Summary<<','<<a/Soil;for(unsigned a:s.surface)Summary<<','<<a;for(double a:s.loadResultant)Summary<<','<<a;Summary<<','<<wave<<','<<pore<<','<<s.loadMax<<','<<s.storeOpen<<','<<s.storeClosed<<','<<(probe==2?-.003:0.);
    const double md=float(SoilCte.ModulusK+4.*SoilCte.ModulusG/3.),mo=float(SoilCte.ModulusK-2.*SoilCte.ModulusG/3.);
    for(unsigned k=0;k<6;k++)Summary<<','<<(probe==2&&(k==0||k==3||k==5)?-.001*(md+2*mo):(probe==3&&(k==1||k==2||k==4)?double(SoilCte.ModulusG)*.001:0.));Summary<<'\n';
    PosInteraction_Forces();Need(!Acec&&!Arc&&!Rsigmac&&!BoundDerivativeVelc&&!HydroMechTopLoadRawc,"Actual PostInteraction failed to release scratch");Clock();
  }
public:
  Component(){PorosityObserver=true;PorosityFeedback=DynamicPorePressure=DynamicPoreWall=DynamicPoreConductivity=false;DynamicPoreConductivityCk=0;}
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);
    Need(HydroMech&&!HydroMechDynamicSeepage&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&HydroMechInitMode==HMINIT_None,"Observer-only retained startup required");
    // Explicit TEST OBJECT overrides, no XML/production change and NOT equivalent to the formal stabilized trajectory.
    HydroMechTopLoadMode=HMLOAD_None;HydroMechDrainage=false;SoilDamping=false;Visco=0;SoilHourglassXi=0;SoilBoundaryDerivativeSPR=false;PoreShepardRegularization=false;
    LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();RunCellDivide(true);
    Need(!Simulate2D&&CaseNp==Total&&CaseNpb==Fixed&&CaseNfluid==Soil&&!CaseNmoving&&!CaseNfloat&&!PartBegin&&!PeriActive&&TStep==STEP_Symplectic&&TKernel==KERNEL_Wendland&&TBoundary==BC_DBC,"Only original3D sphere and8 remote DBC dummies");
    Need(Gravity==TFloat3(0)&&CSP.gravity==Gravity&&!AccInput&&!Damping&&!RelaxZones&&!InOut&&!Shifting&&!NoPenetration&&!ArtificialStress&&!StrainSoftening&&!UseDEM&&!Symmetry&&TDensity==DDT_None&&TVisco==VISCO_Artificial&&!HourglassCpu&&!SoilHourglassXi&&!SoilBoundaryDerivativeSPR&&!SoilDamping&&!Visco&&!PoreShepardRegularization&&PoreCompressionGradCorr&&!PoreCompressionSourceMode&&SoilStressRateGradCorr,"Unsupported coupled/auxiliary path");
    Need(JSph::Dp==.0025&&KernelH==float(.0045)&&RhopZero==2100.f&&SoilCte.Porosity==float(.3)&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==2e8f&&SoilCte.HydraulicConductivity==float(.00001)&&SoilCte.ModulusK>0&&SoilCte.ModulusG>0,"Retained nu.3 material/geometry changed");
    Need(PoroJc&&PoroThetac&&PorePressc&&PorePressRatec&&HydroMechLoadAcec&&CorrMatc&&FSTypec&&FSNormalc&&FixedDt,"Observer/hydromechanical arrays not actually allocated");
    Locked=SymplecticDtPre;OriginalLast=LastDt;OriginalError=FixedDt->GetDtError(false);Clock();X0.resize(Total);BaselineC.resize(Soil);BaselineFS.resize(Soil);BaselineNormal.resize(Soil);
    const auto map=Owners();for(unsigned id=0;id<Total;id++){const unsigned i=map[id];X0[id]=Posc[i];const auto s=Sigmac[i];
      Need(Finite(Posc[i])&&Velrhopc[i].x==0&&Velrhopc[i].y==0&&Velrhopc[i].z==0&&Velrhopc[i].w==RhopZero&&PorePressc[i]==0&&PorePress0c[i]==0&&PoroJc[i]==1&&PoroThetac[i]==0&&s.xx==0&&s.xy==0&&s.xz==0&&s.yy==0&&s.yz==0&&s.zz==0&&Kplasticc[i]==0,"Actual retained seed is not natural J1/rest/zero-stress initialization");}
    for(unsigned b=0;b<Fixed;b++)for(unsigned id=Fixed;id<Total;id++)MinimumDummyDistance=(std::min)(MinimumDummyDistance,std::sqrt(Norm2(X0[b]-X0[id])));
    Need(MinimumDummyDistance>KernelSize,"A retained dummy actually interacts with the sphere");
    const auto initial=Inputs();
    // Deliberately BYPASS feedback Init admission AFTER valid observer allocation. Never call InitPorosityObserverCpu again.
    PorosityFeedback=DynamicPorePressure=true;DynamicPoreWall=DynamicPoreConductivity=false;DynamicPoreConductivityCk=0;
    Summary.open(fs::path(cfg->DirOut)/"summary.csv");Sample.open(fs::path(cfg->DirOut)/"samples.csv");Need(bool(Summary)&&bool(Sample),"Fresh component CSV unavailable");Summary<<std::setprecision(17);Sample<<std::setprecision(17);
    Summary<<"probe,name,soil_count,p_min_Pa,p_max_Pa,theta_mean_s_inv,pdot_mean_Pa_s,pdot_abs_max_Pa_s,Ace_norm_max_m_s2,C_moment_max_ratio,theta_max_ratio,rate_max_ratio,stress6_max_ratio,raw_cancel_max_ratio,load_reference_max_ratio,Rxx_mean_Pa_s,Rxy_mean_Pa_s,Rxz_mean_Pa_s,Ryy_mean_Pa_s,Ryz_mean_Pa_s,Rzz_mean_Pa_s,FS0,FS1,FS2,FS3,load_resultant_x_N,load_resultant_y_N,load_resultant_z_N,wave_scale_s,pore_scale_s,load_norm_max_m_s2,raw_LoadAce_store_gate_open,raw_LoadAce_store_gate_closed,declared_affine_theta_descriptive_s_inv,declared_Rxx,declared_Rxy,declared_Rxz,declared_Ryy,declared_Ryz,declared_Rzz\n";
    Sample<<"probe,name,id,x,y,z,p_Pa,vx,vy,vz,theta_s_inv,theta_ref,theta_budget";for(const char* s:{"xx","xy","xz","yy","yz","zz"})Sample<<",R"<<s<<"_Pa_s,R"<<s<<"_ref,R"<<s<<"_budget";Sample<<",pdot_Pa_s,pdot_ref,pdot_budget,Ace_x,Ace_y,Ace_z,LoadAce_x,LoadAce_y,LoadAce_z,C_ratio,raw_force_ratio,load_ref_ratio,raw_LoadAce_store_gate,raw_load_ref_x,raw_load_ref_y,raw_load_ref_z,raw_force_budget_x,raw_force_budget_y,raw_force_budget_z,C11,C12,C13,C21,C22,C23,C31,C32,C33\n";
    for(unsigned probe=0;probe<Probes;probe++)Force(probe);
    // Inputs() restores all native ID/Code/Dcell/Pos and SOIL Vel/rho/sigma/J/p/p0/plastic only.
    // Not whole-object restoration: fixed physical fields, derived C/FS and rate outputs are excluded;
    // theta is reset to zero, while PorePressRate deliberately remains the finite reset sentinel123.25.
    Reset(Probes);Need(Inputs()==initial,"Declared input bytes did not restore original natural rest");PorosityFeedback=DynamicPorePressure=false;Clock();Summary.flush();Sample.flush();Need(bool(Summary)&&bool(Sample)&&Calls==6&&SoilChecks==6*Soil&&SampleRows==48,"Declared bounded component coverage differs");
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_cryer_cpu_component_r2\",\"passed\":true,\"physical_acceptance\":false,\"public_3D_admitted\":false,\"feedback_Init_guard_bypassed_by_fixture\":true,\"observer_only_initialization_validated\":true,\"feedback_initialization_validated\":false,\"native_count\":37173,\"fixed_dummy_count\":8,\"total_native_count\":37181,\"actual_force_calls\":6,\"complete_rate_calls_from_force\":6,\"explicit_complete_rate_calls\":0,\"soil_reference_checks\":"<<SoilChecks<<",\"sample_rows\":48,\"summary_rows\":6,\"minimum_dummy_soil_distance_m\":"<<MinimumDummyDistance<<",\"original_dummy_count_not_changed\":true,\"actual_physical_steps\":0,\"actual_time_s\":0,\"input_fields_manufactured_only_after_actual_init\":true,\"soil_inputs_force_byte_unchanged\":true,\"frozen_actual_J1_C_and_FS\":true,\"pressure_inputs_float_not_P1_double\":true,\"all_soil_conditional_reference_checked\":true,\"neighbor_search_independently_reimplemented\":false,\"no_Run_ComputeStep_SaveData_restart\":true,\"initial_natural_rest_asserted_before_manufacture\":true,\"nonzero_constant_totalstress0_strict_zero\":true,\"declared_input_bytes_restored\":true,\"whole_object_restored\":false,\"raw_LoadAce_telemetry_gate_explicitly_accounted\":true,\"legacy_PoreDarcySymmetricCorr_value\":"<<(PoreDarcySymmetricCorr?"true":"false")<<",\"legacy_selector_unused_by_dynamic_completeRate\":true,\"standalone_rigid_rotation_tested\":false,\"formal_Visco0p1_and_damping_not_matched\":true,\"raw_load_is_instantaneous_manufactured_not_formal_ramp\":true,\"global_flux_conservation_or_integrator_stability_proved\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
} // namespace cryercomponent
int main(int argc,char** argv){try{
  Need(argc==5&&std::string(argv[1])=="--input"&&std::string(argv[3])=="--out","Use --input RETAINED_CRYER_RUNTIME_XML --out FRESH_DIRECTORY");
  const fs::path xml=argv[2],out=argv[4];auto prefix=xml;prefix.replace_extension();Need(fs::is_regular_file(xml)&&fs::is_regular_file(prefix.string()+".bi4")&&!fs::exists(out),"Existing retained seed/runtime and fresh output required");
  AppInfo.ConfigRunPaths(argv[0]);std::vector<std::string> args={argv[0],"-cpu","-ompthreads:1","-stable",prefix.string(),out.string(),"-dirdataout","data","-svres"};std::vector<char*> pointers;for(auto& a:args)pointers.push_back(a.data());JSphCfgRun cfg;cfg.LoadArgv(int(pointers.size()),pointers.data());
  Need(cfg.Cpu&&cfg.OmpThreads==1&&cfg.Stable&&!cfg.PrintInfo&&!cfg.PartBegin&&!cfg.NstepsBreak&&cfg.TimeMax<0&&cfg.TimePart<0&&!cfg.SvAllSteps,"No execution-window/restart override admitted");
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");cryercomponent::Component fixture;fixture.Execute(&cfg,AppInfo.LogPtr());return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Private non-advancing CPU3D component rejected; retain partial output\n";return 2;}}
