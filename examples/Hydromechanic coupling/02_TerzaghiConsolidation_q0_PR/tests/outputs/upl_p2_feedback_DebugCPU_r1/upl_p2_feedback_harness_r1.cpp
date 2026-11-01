// Bounded P2 feedback component fixture: actual FS/ct and actual p/J helpers.
// Affine kinematics are prescribed, not a physical free/periodic-body trajectory.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JArraysCpu.h"
#include "JDsTimersCpu.h"
#include "JDsDcellDef.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "FunSphKernel.h"
#include <omp.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cfloat>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
JAppInfo AppInfo("PorosityFeedbackCpu","r1","01-11-2026");
namespace fs=std::filesystem;
static void Require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
static bool Close(double a,double b,double relative=5e-13){return std::isfinite(a)&&std::isfinite(b)&&fabs(a-b)<=relative*(std::max)(1.,fabs(b));}
struct LocalState{double n,V,rho;};
struct Rates{
  std::vector<double> theta;std::vector<float> pressure;
  std::vector<tfloat3> acceleration;std::vector<tsymatrix3f> stress;
  std::vector<tmatrix3d> correction;
};
struct Frame{double time;std::vector<double> j;std::vector<float> p;};
struct Series{std::vector<Frame> frames;double max_pressure_error=0,max_j_log_error=0,max_null_pressure=0;};
class Feedback:public JSphCpuSingle{
  unsigned Dimension;std::vector<tdouble3> Reference;
  unsigned Begin[4]={};
  static const char* FieldName(unsigned kind){return kind==0?"compression":kind==1?"dilation":kind==2?"shear":"rotation";}
  double Theta(unsigned kind)const{return kind==0?-1./32.:(kind==1?1./32.:0.);}
  void Kinematics(unsigned kind,double t){
    const double rate=1./32.,theta=Theta(kind),stretch=exp(theta*t/double(Dimension));
    for(unsigned p=0;p<Np;p++){
      const auto a=Reference[p];tdouble3 x=a,v=TDouble3(0);
      if(kind<2){x=x*stretch;v=x*(theta/double(Dimension));}
      else if(kind==2){x.x+=rate*t*a.z;v.x=rate*a.z;}
      else{x.x=cos(rate*t)*a.x-sin(rate*t)*a.z;x.z=sin(rate*t)*a.x+cos(rate*t)*a.z;v.x=-rate*x.z;v.z=rate*x.x;}
      Posc[p]=x+TDouble3(.5,Dimension==3?.5:0.,.5);
      Velrhopc[p].x=float(v.x);Velrhopc[p].y=float(v.y);Velrhopc[p].z=float(v.z);
    }
  }
public:
  Feedback(unsigned dimension,unsigned count):Dimension(dimension){
    Log=AppInfo.LogPtr();Timersc->Config(false);OmpThreads=1;omp_set_num_threads(1);
    Np=count;Npb=NpbOk=0;CaseNp=count;CaseNpb=CaseNfixed=0;CaseNfluid=count;
    TKernel=KERNEL_Wendland;TVisco=VISCO_Artificial;TDensity=DDT_None;TStep=STEP_Symplectic;
    Simulate2D=dimension==2;TBoundary=BC_DBC;TMdbc2=MDBC2_None;SlipMode=SLIP_Vel0;
    HydroMech=true;HydroMechDrainage=false;HydroMechTopLoadMode=HMLOAD_None;HydroMechTopLoadQ0=0;
    SoilBoundaryDerivativeSPR=false;SoilStressRateGradCorr=true;PoreCompressionGradCorr=true;PoreCompressionSourceMode=0;
    PorosityObserver=true;PorosityFeedback=true;SoilHourglassXi=0;SoilDamping=false;Visco=0;ArtificialStress=false;PoreShepardRegularization=false;
    ShiftingMode=SHIFT_None;Gravity=TFloat3(0);UseNormals=false;Symmetry=false;UseDEM=false;
    SoilCte={};SoilCte.ModulusK=1666666.75f;SoilCte.ModulusG=769230.8125f;
    SoilCte.PoreWaterBulkModulus=2e8f;SoilCte.PoreWaterRho=1000;SoilCte.Porosity=.3f;SoilCte.HydraulicConductivity=0;
    RhopZero=2100;Dp=.25;KernelH=.5f;KernelSize=1;KernelSize2=1;Eta2=.0025f;Cs0=40;
    MassFluid=MassBound=float(double(RhopZero)*pow(Dp,Dimension));
    CSP=CteSphNull();CSP.simulate2d=Simulate2D;CSP.tkernel=TKernel;CSP.kernelh=KernelH;
    CSP.kwend=fsph::GetKernelWendland_Ctes(Simulate2D,KernelH);CSP.massfluid=MassFluid;CSP.massbound=MassBound;CSP.rhopzero=RhopZero;CSP.cteb=0;CSP.gamma=7;
    CSP.dp=Dp;CSP.kernelsize=KernelSize;CSP.kernelsize2=KernelSize2;CSP.cs0=Cs0;CSP.eta2=Eta2;CSP.gravity=Gravity;
    AllocCpuMemoryParticles(Np,0);ReserveBasicArraysCpu();
    Begin[0]=Begin[1]=Begin[2]=0;Begin[3]=Np;
    DivData=MakeDivDataCpu(1,TUint3(1),TUint3(0),Begin,2,DCEL_GetCode(1,1,1),TDouble3(0));
    for(unsigned p=0;p<Np;p++){
      Idpc[p]=p;Codec[p]=CODE_TYPE_FLUID;Dcellc[p]=0;
      Velrhopc[p]=TFloat4(0,0,0,RhopZero);Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;
      PorePressc[p]=PorePress0c[p]=PorePressRatec[p]=0;
      CorrMatc[p]=TMatrix3d();FSNormalc[p]=TFloat3(0);FSTypec[p]=FST_Inner;PosDivc[p]=0;
      HydroMechLoadAcec[p]=TFloat3(0);
    }
    InitPorosityObserverCpu();
    if(count==2){Reference={TDouble3(-.0625,dimension==3?-.03125:0.,-.046875),TDouble3(.0625,dimension==3?.03125:0.,.046875)};}
    else{
      for(int y=(dimension==3?-1:0);y<=(dimension==3?1:0);y++)for(int z=-1;z<=1;z++)for(int x=-1;x<=1;x++)Reference.push_back(TDouble3(x*Dp,y*Dp,z*Dp));
    }
    Require(Reference.size()==Np,"Unexpected manufactured grid");Kinematics(0,0);
  }
  LocalState State(unsigned p)const{LocalState a{};GetPorosityFeedbackStateCpu(p,a.n,a.V,a.rho);return a;}
  unsigned ScopeGuards(std::ostream& out){
    unsigned count=0;
    auto rejected=[&](const char* field){
      bool caught=false;try{InitPorosityObserverCpu();}catch(const std::exception&){caught=true;}
      Require(caught,"Unsupported feedback configuration was not rejected");out<<Dimension<<','<<field<<",rejected\n";count++;
    };
    PorosityObserver=false;rejected("observer_missing");PorosityObserver=true;
    CaseNpb=1;rejected("physical_wall");CaseNpb=0;
    SoilCte.HydraulicConductivity=1e-5f;rejected("nonzero_k");SoilCte.HydraulicConductivity=0;
    Gravity.z=-9.81f;rejected("gravity");Gravity=TFloat3(0);
    HydroMechDrainage=true;rejected("drainage");HydroMechDrainage=false;
    HydroMechTopLoadMode=HMLOAD_TopVertical;rejected("load");HydroMechTopLoadMode=HMLOAD_None;
    SoilHourglassXi=.1f;rejected("hourglass");SoilHourglassXi=0;
    SoilDamping=true;rejected("soil_damping");SoilDamping=false;
    Visco=.1f;rejected("viscosity");Visco=0;
    TDensity=DDT_DDT;rejected("density_diffusion");TDensity=DDT_None;
    ArtificialStress=true;rejected("artificial_stress");ArtificialStress=false;
    SoilBoundaryDerivativeSPR=true;rejected("boundary_SPR");SoilBoundaryDerivativeSPR=false;
    SoilStressRateGradCorr=false;rejected("uncorrected_stress_gradient");SoilStressRateGradCorr=true;
    PoreShepardRegularization=true;rejected("Shepard");PoreShepardRegularization=false;
    RhopZero=100;rejected("invalid_reference_mixture");RhopZero=2100;
    InitPorosityObserverCpu();return count;
  }
  Rates Evaluate(bool actualCorrection=true){
    PreInteraction_Forces();memset(PorePressRatec,0,sizeof(float)*Np);
    if(actualCorrection)ComputeFreeSurfaceTracking();
    else for(unsigned p=0;p<Np;p++){CorrMatc[p]=TMatrix3d();FSTypec[p]=FST_Inner;}
    const auto parameters=StInterparmsc(Np,Npb,NpbOk,DivData,Dcellc,Posc,Velrhopc,Idpc,Codec,Pressc,
      PorePressc,PorePressRatec,FSTypec,FSNormalc,nullptr,CorrMatc,Arc,Acec,nullptr,SHIFT_None,nullptr,nullptr,nullptr,Sigmac,Rsigmac,nullptr);
    StInterResultc result{};Interaction_Forces_ct(parameters,result);
    Rates r={{PoroThetac,PoroThetac+Np},{PorePressRatec,PorePressRatec+Np},{Acec,Acec+Np},{Rsigmac,Rsigmac+Np},{CorrMatc,CorrMatc+Np}};
    for(unsigned p=0;p<Np;p++)Require(std::isfinite(r.theta[p])&&std::isfinite(r.pressure[p])&&std::isfinite(r.acceleration[p].x)&&std::isfinite(r.acceleration[p].y)&&std::isfinite(r.acceleration[p].z),"Nonfinite ct result");
    PosInteraction_Forces();return r;
  }
  void LedgerAndPoison(std::ostream& out){
    Require(Np>2,"Need full-rank patch");Kinematics(1,0);
    const double n0=double(SoilCte.Porosity),rho0=RhopZero,rhow=SoilCte.PoreWaterRho,V0=double(MassFluid)/rho0,rhos=(rho0-n0*rhow)/(1.-n0);
    for(unsigned p=0;p<Np;p++){
      PoroJc[p]=.95+.025*(p%5);PorePressc[p]=128.f+float(p);Sigmac[p]=TSymMatrix3d(1234,Dimension==3?111:0,222,2345,Dimension==3?333:0,3456);
      const auto a=State(p);const double j=PoroJc[p];
      Require(Close(a.n,1.-(1.-n0)/j)&&Close(a.V,V0*j)&&Close(a.rho,(1.-a.n)*rhos+a.n*rhow),"Actual closure helper mismatch");
      Require(Close((1.-a.n)*a.V*rhos,(1.-n0)*V0*rhos),"Actual solid mass/volume closure mismatch");
    }
    const auto normal=Evaluate();
    for(unsigned p=0;p<Np;p++)Velrhopc[p].w=float(1000+37*p);
    const auto poisoned=Evaluate();
    for(unsigned p=0;p<Np;p++){
      const auto a=State(p);const double wanted=-double(SoilCte.PoreWaterBulkModulus)/a.n*Theta(1);
      const double thetaTolerance=64*FLT_EPSILON*fabs(Theta(1));
      Require(fabs(normal.theta[p]-Theta(1))<=thetaTolerance,"Actual J-volume C fails affine reproduction");
      Require(fabs(double(normal.pressure[p])-wanted)<=64*FLT_EPSILON*fabs(wanted),"Storage did not use receiver porosity");
      Require(!memcmp(&normal.theta[p],&poisoned.theta[p],sizeof(double))&&!memcmp(&normal.pressure[p],&poisoned.pressure[p],sizeof(float))
        &&!memcmp(&normal.acceleration[p],&poisoned.acceleration[p],sizeof(tfloat3))&&!memcmp(&normal.stress[p],&poisoned.stress[p],sizeof(tsymatrix3f))
        &&!memcmp(&normal.correction[p],&poisoned.correction[p],sizeof(tmatrix3d)),"Positive old-rho poison changed new physical operators");
      const double g=double(SoilCte.ModulusG),lambda=double(SoilCte.ModulusK)-2.*g/3.,theta=Theta(1),d=theta/Dimension;
      const double stressReference[6]={2.*g*d+lambda*theta,0,0,(Dimension==3?2.*g*d:0.)+lambda*theta,0,2.*g*d+lambda*theta};
      const auto s=normal.stress[p];const double stressActual[6]={s.xx,s.xy,s.xz,s.yy,s.yz,s.zz};double stressMaxError=0;
      for(unsigned i=0;i<6;i++){
        const double error=fabs(stressActual[i]-stressReference[i]);
        Require(error<=64*FLT_EPSILON*(std::max)(fabs(stressReference[i]),fabs(g*theta))+1e-6,"Actual J-volume stress gradient fails affine elastic rate reference");
        stressMaxError=(std::max)(stressMaxError,error);
      }
      out<<Dimension<<','<<p<<','<<PoroJc[p]<<','<<a.n<<','<<a.V<<','<<a.rho<<','<<normal.theta[p]<<','<<normal.pressure[p]<<','<<wanted<<','<<stressMaxError;
      for(unsigned i=0;i<6;i++)out<<','<<stressActual[i]<<','<<stressReference[i];out<<'\n';
    }
  }
  void PairMomentum(std::ostream& out){
    Require(Np==2,"Pair fixture expected");PoroJc[0]=.9;PoroJc[1]=1.2;
    PorePressc[0]=2000;PorePressc[1]=7000;
    Sigmac[0]=TSymMatrix3d(12345,Dimension==3?321:0,432,23456,Dimension==3?543:0,34567);
    Sigmac[1]=TSymMatrix3d(2468,Dimension==3?-123:0,234,3579,Dimension==3?-345:0,4680);
    for(unsigned p=0;p<Np;p++)Velrhopc[p]=TFloat4(0,0,0,float(1100+333*p));
    const auto result=Evaluate(false);const auto a=State(0),b=State(1);
    const tfloat3 dr=ToTFloat3(Posc[0]-Posc[1]);const float rr=dr.x*dr.x+dr.y*dr.y+dr.z*dr.z;
    const float fac=fsph::GetKernelWendland_Fac(CSP,rr);const tfloat3 g=dr*fac;
    const auto s0=ToTSymMatrix3f(Sigmac[0]),s1=ToTSymMatrix3f(Sigmac[1]);
    const double p=double(PorePressc[0])+PorePressc[1];
    const double xx=double(s0.xx)+s1.xx-p,yy=double(s0.yy)+s1.yy-p,zz=double(s0.zz)+s1.zz-p;
    const double xy=double(s0.xy)+s1.xy,xz=double(s0.xz)+s1.xz,yz=double(s0.yz)+s1.yz;
    const tdouble3 f=TDouble3(xx*g.x+xy*g.y+xz*g.z,xy*g.x+yy*g.y+yz*g.z,xz*g.x+yz*g.y+zz*g.z);
    const tdouble3 ref0=f*(b.V/a.rho),ref1=f*(-a.V/b.rho);
    const auto observed0=ToTDouble3(result.acceleration[0]),observed1=ToTDouble3(result.acceleration[1]);
    const tdouble3 net=observed0*(a.rho*a.V)+observed1*(b.rho*b.V);
    const double reference[6]={ref0.x,ref0.y,ref0.z,ref1.x,ref1.y,ref1.z};
    const double observed[6]={observed0.x,observed0.y,observed0.z,observed1.x,observed1.y,observed1.z};
    for(unsigned i=0;i<6;i++)Require(fabs(observed[i]-reference[i])<=64*FLT_EPSILON*(std::max)(1e-6,fabs(reference[i]))+1e-9,"Actual feedback momentum differs from declared volume/inertia equation");
    const double scale=a.rho*a.V*(fabs(observed0.x)+fabs(observed0.y)+fabs(observed0.z))+b.rho*b.V*(fabs(observed1.x)+fabs(observed1.y)+fabs(observed1.z));
    Require(fabs(net.x)+fabs(net.y)+fabs(net.z)<=64*FLT_EPSILON*scale+1e-9,"Actual pair internal force does not balance");
    out<<Dimension<<','<<net.x<<','<<net.y<<','<<net.z<<','<<scale<<'\n';
  }
  Series Integrate(unsigned kind,unsigned steps,std::ostream& out){
    const double end=1./1024.,dt=end/steps,n0=double(SoilCte.Porosity),kw=double(SoilCte.PoreWaterBulkModulus),theta=Theta(kind);
    Series series;
    auto save=[&](double t){
      Frame frame{t,{PoroJc,PoroJc+Np},{PorePressc,PorePressc+Np}};
      for(unsigned p=0;p<Np;p++){
        const auto a=State(p);const double j=PoroJc[p];
        const double referenceJ=-kw*log((j-1.+n0)/n0),analyticJ=exp(theta*t),referenceTime=-kw*log((analyticJ-1.+n0)/n0);
        const double pe=fabs(double(PorePressc[p])-referenceJ),je=fabs(log(j)-theta*t);
        Require(std::isfinite(a.n)&&a.n>0&&a.n<1&&Close((1.-a.n)*j,1.-n0),"Integrated porosity/volume domain or invariant failure");
        Require(pe<=1.,"Actual p/J integration exceeds 1Pa logarithmic-storage reference");
        Require(je<=64*FLT_EPSILON*fabs(theta*t)+512*DBL_EPSILON,"Actual J integration exceeds analytic affine deformation bound");
        if(kind>=2)Require(fabs(double(PorePressc[p]))<=.02&&fabs(j-1.)<=5e-13,"Trace-free shear/rotation generated excessive storage");
        series.max_pressure_error=(std::max)(series.max_pressure_error,pe);series.max_j_log_error=(std::max)(series.max_j_log_error,je);
        if(kind>=2)series.max_null_pressure=(std::max)(series.max_null_pressure,fabs(double(PorePressc[p])));
        out<<Dimension<<','<<FieldName(kind)<<','<<steps<<','<<t<<','<<p<<','<<j<<','<<a.n<<','<<a.V<<','<<a.rho<<','<<PorePressc[p]<<','<<referenceJ<<','<<referenceTime<<','<<PoroThetac[p]<<'\n';
      }
      series.frames.push_back(std::move(frame));
    };
    save(0);
    for(unsigned step=0;step<steps;step++){
      const double tn=step*dt;Kinematics(kind,tn);Evaluate();
      PorePressPrec=ArraysCpu->ReserveFloat();std::swap(PorePressPrec,PorePressc);
      ComputeSymplecticPrePorePressure(dt);ComputeSymplecticPrePorosity(dt);
      Kinematics(kind,tn+.5*dt);Evaluate();
      ComputeSymplecticCorrPorePressure(dt);ComputeSymplecticCorrPorosity(dt);
      ArraysCpu->Free(PorePressPrec);PorePressPrec=nullptr;
      TimeStep=(step+1)*dt;Nstep=step+1;save(TimeStep);
    }
    Require(!PoroJPrec&&!PorePressPrec,"Stage history leaked after component integration");return series;
  }
};
int main(int argc,char** argv){
  try{
    Require(argc==3&&std::string(argv[1])=="--out","Use --out NEW_DIRECTORY");const fs::path folder(argv[2]);Require(!fs::exists(folder),"Retained output protected");
    AppInfo.ConfigRunPaths(argv[0]);AppInfo.ConfigOutput(true,false,folder.string(),"data");AppInfo.LogInit((folder/"Run.out").string());
    std::ofstream ledger(folder/"ledger.csv"),momentum(folder/"momentum.csv"),history(folder/"history.csv"),halves(folder/"halves.csv"),guards(folder/"guards.csv");
    for(auto* s:{&ledger,&momentum,&history,&halves,&guards})*s<<std::setprecision(17);
    ledger<<"dimension,id,J,n,V,rho_t,theta,pdot,pdot_reference,stress_rate_absmax_error,sxx,sxx_ref,sxy,sxy_ref,sxz,sxz_ref,syy,syy_ref,syz,syz_ref,szz,szz_ref\n";momentum<<"dimension,net_force_x,net_force_y,net_force_z,absolute_force_scale\n";
    history<<"dimension,field,steps,time_s,id,J,n,V,rho_t,p,p_reference_actual_J,p_reference_analytic_J,theta_last_stage\n";
    halves<<"dimension,field,time_s,pressure_absmax_pa,J_absmax\n";
    guards<<"dimension,unsupported_field,result\n";
    double maxPressure=0,maxHalf=0,maxJ=0,maxNull=0;unsigned pairs=0,guardCount=0;
    for(unsigned dim:{2u,3u}){
      {Feedback pair(dim,2);guardCount+=pair.ScopeGuards(guards);pair.PairMomentum(momentum);}
      {Feedback cloud(dim,dim==2?9:27);cloud.LedgerAndPoison(ledger);}
      for(unsigned kind=0;kind<4;kind++){
        Series c,h;{Feedback a(dim,dim==2?9:27);c=a.Integrate(kind,64,history);}{Feedback a(dim,dim==2?9:27);h=a.Integrate(kind,128,history);}
        Require(c.frames.size()==65&&h.frames.size()==129,"Half-step coverage missing");
        for(unsigned i=0;i<c.frames.size();i++){
          const auto& a=c.frames[i];const auto& b=h.frames[2*i];Require(a.time==b.time&&a.j.size()==b.j.size(),"Actual dyadic half clocks differ");
          double pe=0,je=0;for(unsigned p=0;p<a.j.size();p++){pe=(std::max)(pe,fabs(double(a.p[p])-b.p[p]));je=(std::max)(je,fabs(a.j[p]-b.j[p]));}
          Require(pe<=.5&&je<=5e-11,"Independent component half-step bound failed");maxHalf=(std::max)(maxHalf,pe);pairs++;
          halves<<dim<<','<<kind<<','<<a.time<<','<<pe<<','<<je<<'\n';
        }
        maxPressure=(std::max)({maxPressure,c.max_pressure_error,h.max_pressure_error});maxJ=(std::max)({maxJ,c.max_j_log_error,h.max_j_log_error});maxNull=(std::max)({maxNull,c.max_null_pressure,h.max_null_pressure});
      }
    }
    for(auto* s:{&ledger,&momentum,&history,&halves,&guards}){s->flush();Require(bool(*s),"Diagnostic CSV failed");}
    std::ofstream done(folder/"complete.json");done<<std::setprecision(17)
      <<"{\"passed\":true,\"actual_feedback_ct_and_state_helpers\":true,\"old_positive_rho_poison_0ULP\":true,\"scope_guards\":"<<guardCount<<",\"half_pairs\":"<<pairs
      <<",\"max_pressure_log_reference_error_pa\":"<<maxPressure<<",\"max_half_pressure_difference_pa\":"<<maxHalf<<",\"max_analytic_J_log_error\":"<<maxJ<<",\"max_null_pressure_pa\":"<<maxNull
      <<",\"prescribed_kinematics\":true,\"physical_outer_loop_used\":false,\"periodic_affine_claimed\":false,\"dynamic_Darcy_implemented\":false,\"physical_acceptance\":false}\n";
    done.flush();Require(bool(done),"Completion write failed");std::cout<<"P2 feedback component tests passed; not a coupled physical trajectory.\n";return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Feedback fixture failed; preserve outputs and Run.out\n";return 2;}
}
