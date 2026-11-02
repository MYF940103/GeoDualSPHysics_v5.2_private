// Manufactured component scratch only. No Run, ComputeStep, host Pre/Corr or SaveData.
#define main RetainedColumnObserverMain
#include "upl_gpu_observer_native_r1.cpp"
#undef main
#include "JSphGpu_ker.h"
#include "JDsTimersGpu.h"
#include "JDsFixedDt.h"
#include "JXml.h"
#include "JException.h"
#include "FunSphKernel.h"
#include <cuda_runtime_api.h>
#include <vector_functions.h>
#include <cfloat>
#include <climits>
#include <limits>
namespace columncomponent {
constexpr unsigned Fixed=40,Soil=1000,Total=1040;
static void Cu(cudaError_t e){Check(e==cudaSuccess,cudaGetErrorString(e));}
template<class T>static std::vector<T> Down(const T* p,unsigned n){Check(p!=nullptr,"Required GPU array missing");std::vector<T> v(n);if(n)Cu(cudaMemcpy(v.data(),p,sizeof(T)*n,cudaMemcpyDeviceToHost));return v;}
template<class T>static void Up(T* p,const std::vector<T>& v){Check(p!=nullptr,"Required GPU upload missing");if(!v.empty())Cu(cudaMemcpy(p,v.data(),sizeof(T)*v.size(),cudaMemcpyHostToDevice));}
template<class T>static bool Same(const std::vector<T>& a,const std::vector<T>& b){return a.size()==b.size()&&(a.empty()||!memcmp(a.data(),b.data(),sizeof(T)*a.size()));}
template<class T>struct Device {T* p=nullptr;explicit Device(unsigned n){Cu(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*n));}~Device(){if(p)cudaFree(p);}Device(const Device&)=delete;Device& operator=(const Device&)=delete;};
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static tdouble3 Abs(tdouble3 a){return TDouble3(fabs(a.x),fabs(a.y),fabs(a.z));}
static tdouble3 Vec(float3 a){return TDouble3(a.x,a.y,a.z);}
static tdouble3 Product(const tmatrix3d& c,tdouble3 g){return TDouble3(c.a11*g.x+c.a12*g.y+c.a13*g.z,c.a21*g.x+c.a22*g.y+c.a23*g.z,c.a31*g.x+c.a32*g.y+c.a33*g.z);}
static bool Surface(unsigned f){return f==FST_FreeSurface||f==FST_Isolated;}
static double ForceBudget(double absolute,double target){return 64.*FLT_EPSILON*absolute+256.*DBL_EPSILON*(std::max)(1.,fabs(target))+1e-6;}
struct State {
  std::vector<unsigned> id,cell,fs;std::vector<typecode> code;std::vector<double2> xy;std::vector<double> z,j,theta;
  std::vector<float> p,p0,rate,plastic,raw;std::vector<float4> vel;std::vector<tsymatrix3d> sigma;std::vector<float3> normal,ace,load;std::vector<tmatrix3d> c;
};
struct Snapshot {
  struct Block{void* p;std::vector<byte> bytes;};std::vector<Block> blocks;double cache=0;
  template<class T>void Add(T* p,unsigned n){if(p){Block b{p,std::vector<byte>(sizeof(T)*n)};Cu(cudaMemcpy(b.bytes.data(),p,b.bytes.size(),cudaMemcpyDeviceToHost));blocks.push_back(std::move(b));}}
  void Restore()const{for(const auto& b:blocks)Cu(cudaMemcpy(b.p,b.bytes.data(),b.bytes.size(),cudaMemcpyHostToDevice));}
  bool Exact()const{for(const auto& b:blocks){std::vector<byte> v(b.bytes.size());Cu(cudaMemcpy(v.data(),b.p,v.size(),cudaMemcpyDeviceToHost));if(v!=b.bytes)return false;}return true;}
};
struct Reference {double rate,old,raw,budget,oldbudget;tdouble3 gp,agp;};
struct Totals {unsigned force=0,rate=0,rows=0,owner=0,restores=0,pressure_api=0;double ratio=0,invariance=0,signal=0,loadratio=0,aceratio=0,wrong=DBL_MAX;};
// This object is never an actual-Run wrapper. Only its named scratch is manufactured.
class ComponentScratch:public JSphGpuSingle {
  double Locked=0,Last=0,Error0=0;
  State Capture(bool live=false)const{
    State a;a.id=Down(Idpg,Np);a.cell=Down(Dcellg,Np);a.code=Down(Codeg,Np);a.xy=Down(Posxyg,Np);a.z=Down(Poszg,Np);a.j=Down(PoroJg,Np);a.theta=Down(PoroThetag,Np);a.p=Down(PorePressg,Np);a.p0=Down(PorePress0g,Np);a.rate=Down(PorePressRateg,Np);a.vel=Down(Velrhopg,Np);a.sigma=Down(Sigmag,Np);a.plastic=Down(Kplasticg,Np);a.fs=Down(FSTypeg,Np);a.normal=Down(FSNormalg,Np);a.c=Down(CorrMatg,Np);a.load=Down(HydroMechLoadAceg,Np);if(live){a.ace=Down(Aceg,Np);a.raw=Down(HydroMechTopLoadRawg,Np);}return a;
  }
  std::vector<unsigned> Owners(const State& a)const{
    std::vector<unsigned> map(Total,UINT_MAX);unsigned ns=0,nf=0,ghost=0;
    for(unsigned p=0;p<Np;p++){Check(a.id[p]<Total&&(CODE_IsNormal(a.code[p])||CODE_IsPeriodic(a.code[p])),"Unexpected/excluded GPU slot");if(CODE_IsNormal(a.code[p])){Check(map[a.id[p]]==UINT_MAX,"Duplicate native ID");map[a.id[p]]=p;if(a.id[p]<Fixed){Check(CODE_IsFixed(a.code[p]),"Fixed ID/type differs");nf++;}else{Check(CODE_IsFluid(a.code[p]),"Soil ID/type differs");ns++;}}else if(CODE_IsFluid(a.code[p]))ghost++;}
    Check(ns==Soil&&nf==Fixed&&ghost>0&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"1000soil40fixed and nonempty X images required");return map;
  }
  void Clock()const{Check(!TimeStep&&!Nstep&&SymplecticDtPre==Locked&&LastDt==Last&&FixedDt->GetDtError(false)==Error0&&!PosxyPreg&&!PoszPreg&&!VelrhopPreg&&!SigmaPreg&&!PorePressPreg&&!PoroJPreg,"Component advanced clock/history");}
  Snapshot Save()const{
    Snapshot s;s.cache=DynamicConductivitySpeedMax;s.Add(Idpg,Np);s.Add(Codeg,Np);s.Add(Dcellg,Np);s.Add(Posxyg,Np);s.Add(Poszg,Np);s.Add(Velrhopg,Np);s.Add(Sigmag,Np);s.Add(Kplasticg,Np);s.Add(PorePressg,Np);s.Add(PorePress0g,Np);s.Add(PorePressRateg,Np);s.Add(PoroJg,Np);s.Add(PoroThetag,Np);s.Add(CorrMatg,Np);s.Add(FSTypeg,Np);s.Add(FSNormalg,Np);s.Add(HydroMechLoadAceg,Np);s.Add(Aceg,Np);s.Add(Arg,Np);s.Add(Rsigmag,Np);s.Add(HydroMechTopLoadRawg,Np);s.Add(BoundDerivativeVelg,Np);s.Add(TangenVelg,Np);s.Add(BoundModeg,Np);return s;
  }
  void Restore(const Snapshot& s,Totals& t){TimeStep=0;Nstep=0;s.Restore();DynamicConductivitySpeedMax=s.cache;Check(s.Exact()&&DynamicConductivitySpeedMax==s.cache,"Named scratch rollback differs");Clock();t.restores++;}
  void Rate(Totals& t){t.rate++;ComputeDynamicPorePressureRateGpu(PrepareDynamicPorePeriodicGpu());Cu(cudaDeviceSynchronize());}
  Reference Ref(const State& a,unsigned i)const{
    double lp=0,alp=0,da=0,ada=0;tdouble3 gp=TDouble3(0),lx=TDouble3(0),agp=TDouble3(0),alx=TDouble3(0);
    const double v0=double(MassFluid)/RhopZero,rhow=SoilCte.PoreWaterRho,B=double(SoilCte.PoreWaterBulkModulus)/(1.-(1.-double(SoilCte.Porosity))/a.j[i]),k=SoilCte.HydraulicConductivity,gamma=rhow*9.80665;
    // Independent host all-slot support; never calls the device rate or its cell list.
    for(unsigned q=0;q<Np;q++)if(CODE_IsFluid(a.code[q])||CODE_IsFixed(a.code[q])){
      const tdouble3 d=TDouble3(a.xy[i].x-a.xy[q].x,0,a.z[i]-a.z[q]);const double rr=Dot(d,d);if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;
      const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr))),gi=Product(a.c[i],g),gj=Product(a.c[q],g);const double v=v0*a.j[q],dp=double(a.p[i])-a.p[q],w=v*Dot(d,gi+gj)/(rr+double(Eta2));const auto delta=Vec(a.ace[q])-Vec(a.ace[i]);
      lp+=w*dp;alp+=fabs(w*dp);lx=lx+d*w;alx=alx+Abs(d*w);gp=gp-gi*(v*dp);agp=agp+Abs(gi*(v*dp));da+=v*Dot(delta,gi);ada+=v*Dot(Abs(delta),Abs(gi));
    }
    tdouble3 gc=gp,agc=agp;const auto ace=Vec(a.ace[i]);if(Surface(a.fs[i])){const auto normal=Vec(a.normal[i]);const double n2=Dot(normal,normal);Check(std::isfinite(n2)&&n2>0,"Independent normal invalid");const double r=Dot(normal,gp+ace*rhow)/n2,ar=Dot(Abs(normal),agp+Abs(ace)*rhow)/n2;gc=gp-normal*r;agc=agp+Abs(normal)*ar;}
    const double old=B*(-a.theta[i]+k/gamma*(lp-Dot(gp,lx)+rhow*da)),value=B*(-a.theta[i]+k/gamma*(lp-Dot(gc,lx)+rhow*da));
    const double raw=B*(fabs(a.theta[i])+k/gamma*(alp+Dot(agc,alx)+rhow*ada)),oldraw=B*(fabs(a.theta[i])+k/gamma*(alp+Dot(agp,alx)+rhow*ada)),tail=256.*DBL_EPSILON*(std::max)(1.,fabs(B*a.theta[i]))+1e-6;
    Check(std::isfinite(value)&&std::isfinite(raw),"Independent reference nonfinite");return{value,old,raw,64.*FLT_EPSILON*raw+tail,64.*FLT_EPSILON*oldraw+tail,gp,agp};
  }
  unsigned Copies(const State& a,const std::vector<unsigned>& owner,bool pressure)const{
    unsigned n=0;for(unsigned p=Npb;p<Np;p++)if(CODE_IsPeriodic(a.code[p])&&CODE_IsFluid(a.code[p])){const unsigned q=owner[a.id[p]];if(pressure)Check(!memcmp(&a.p[p],&a.p[q],sizeof(float)),"Periodic pressure owner differs");else Check(!memcmp(&a.rate[p],&a.rate[q],sizeof(float))&&!memcmp(&a.ace[p],&a.ace[q],sizeof(float3))&&!memcmp(&a.theta[p],&a.theta[q],sizeof(double))&&!memcmp(&a.c[p],&a.c[q],sizeof(tmatrix3d)),"Complete-rate owner fields differ");n++;}Check(n>0,"Empty periodic witness");return n;
  }
  std::vector<byte> Physical(const State& a,const std::vector<unsigned>& owner)const{
    std::vector<byte> b;auto add=[&](const auto& x){const auto p=reinterpret_cast<const byte*>(&x);b.insert(b.end(),p,p+sizeof(x));};for(unsigned id=Fixed;id<Total;id++){const auto p=owner[id];add(a.id[p]);add(a.code[p]);add(a.cell[p]);add(a.xy[p]);add(a.z[p]);add(a.vel[p]);add(a.sigma[p]);add(a.plastic[p]);add(a.p[p]);add(a.p0[p]);add(a.j[p]);}return b;
  }
public:
  ComponentScratch(){PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;DynamicPoreConductivity=false;DynamicPoreConductivityCk=0;}
  void Init(const JSphCfgRun* cfg,JLog2* log){
    JXml xml;xml.LoadFile(cfg->CaseName+".xml");const auto* h=xml.GetNodeError("case.execution.special.hydromechanics");Check(xml.ReadElementDouble(h,"HydroMechDynamicSeepage","value")==0&&xml.ReadElementDouble(h,"HydroMechConductivityModel","value")==0&&xml.ReadElementDouble(h,"HydroMechConductivityCk","value")==0,"Public master/law must remain0");
    for(const char* path:{"case.execution.constants","case.casedef.constantsdef"})Check(xml.GetAttributeDouble3(xml.GetFirstElement(xml.GetNodeError(path),"gravity"))==TDouble3(0),"Both XML gravity values must be0");
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;SelecDevice(cfg->GpuId);Timersg->Config(false);Timersg->TmStart(TMG_Init,false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunGpu();FreePartsInit();RunCellDivide(true);
    Check(HydroMech&&Simulate2D&&CaseNp==Total&&CaseNpb==Fixed&&CaseNfluid==Soil&&!PartBegin&&!CaseNmoving&&!CaseNfloat&&TStep==STEP_Symplectic&&TKernel==KERNEL_Wendland&&PeriX&&!PeriY&&!PeriZ&&PeriXinc.y==0&&PeriXinc.z==0&&fabs(fabs(PeriXinc.x)-.1)<=1e-14&&Gravity==TFloat3(0)&&CSP.gravity==Gravity,"Original private column geometry differs");
    Check(!HydroMechDynamicSeepage&&HydroMechConductivityModel==0&&HydroMechConductivityCk==0&&!DynamicPoreConductivity&&TBoundary==BC_MDBC&&SlipMode==SLIP_FreeSlip&&HydroMechInitMode==HMINIT_None&&HydroMechTopLoadMode==HMLOAD_TopKernelBand&&HydroMechTopLoadQ0==10000.f&&HydroMechTopLoadRampTime==.01&&HydroMechDrainage&&HydroMechDrainageStartTime==.01&&HydroMechDrainageFixedGrid&&!IsHydroMechDrainageActive(),"Private constant-k load/drain options differ");
    Check(JSph::Dp==.01&&KernelH==float(.018)&&RhopZero==2100.f&&MassFluid==float(.21)&&MassBound==MassFluid&&SoilCte.Porosity==float(.3)&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==2e8f&&SoilCte.HydraulicConductivity==float(.0001)&&SoilCte.ModulusK==1666666.75f&&SoilCte.ModulusG==769230.8125f&&PoreDtSafety==1,"Original float material differs");
    Check(!HourglassGpu&&!Visco&&!SoilDamping&&!Damping&&!RelaxZones&&!Shifting&&!InOut&&!AccInput&&!NoPenetration&&!SoilBoundaryDerivativeSPR&&!ArtificialStress&&!PoreShepardRegularization&&TDensity==DDT_None&&!StrainSoftening&&PoreCompressionGradCorr&&!PoreCompressionSourceMode&&SoilStressRateGradCorr&&FixedDt,"Auxiliary physics not admitted");
    Locked=SymplecticDtPre;Last=LastDt;Error0=FixedDt->GetDtError(false);Clock();const auto a=Capture();const auto owner=Owners(a);
    for(unsigned id=Fixed;id<Total;id++){const unsigned p=owner[id];Check(a.j[p]==1&&a.theta[p]==0&&a.p[p]==0&&a.p0[p]==0&&a.plastic[p]==0&&a.vel[p].x==0&&a.vel[p].y==0&&a.vel[p].z==0&&a.vel[p].w==RhopZero&&a.sigma[p].xx==0&&a.sigma[p].yy==0&&a.sigma[p].zz==0&&a.sigma[p].xy==0&&a.sigma[p].xz==0&&a.sigma[p].yz==0,"Natural input is not original strict rest");}
  }
  void Operators(const JSphCfgRun* cfg,Totals& t,std::ofstream& rates,std::ofstream& affine,std::ofstream& probes){
    Interaction_Forces(INTERSTEP_SymPredictor);t.force++;const auto natural=Capture(true);const auto owner=Owners(natural);unsigned top=UINT_MAX,topcount=0;
    for(unsigned id=Fixed;id<Total;id++){const auto p=owner[id];Check(natural.ace[p].x==0&&natural.ace[p].y==0&&natural.ace[p].z==0&&natural.theta[p]==0&&natural.rate[p]==0,"Natural rest force/rate not strictly0");if(Surface(natural.fs[p])){Check(natural.z[p]>.98,"Unexpected free boundary");top=p;topcount++;}}
    Check(topcount==10&&top!=UINT_MAX,"Ten actual top receivers required");const auto base=Save();
    try{
      std::vector<double> baseline(Soil),budgets(Soil);const float factors[3]={1,-1,2};
      for(unsigned field=0;field<3;field++){Restore(base,t);auto p=natural.p;auto ace=natural.ace;for(unsigned q=0;q<Np;q++)if(CODE_IsFluid(natural.code[q]))p[q]=float(2000.+(field==2?0.:1000.*natural.z[q]));Up(PorePressg,p);ComputeDynamicPoreWallStateGpu();ComputeDynamicPoreWallMatrixGpu();
        for(unsigned id=Fixed;id<Total;id++)ace[owner[id]]=(field==0?make_float3(0,0,-1):(field==1?make_float3(0,0,1):make_float3(1,0,0)));Up(Aceg,ace);
        for(unsigned variant=0;variant<3;variant++){auto normals=natural.normal;for(unsigned id=Fixed;id<Total;id++){auto& n=normals[owner[id]];n=make_float3(n.x*factors[variant],n.y*factors[variant],n.z*factors[variant]);}Up(FSNormalg,normals);Rate(t);const auto a=Capture(true);t.owner+=Copies(a,owner,false);double mr=0,mi=0,signal=0;unsigned upper=0,tops=0;
          for(unsigned id=Fixed;id<Total;id++){const unsigned q=owner[id];const auto r=Ref(a,q);const double actual=a.rate[q],error=fabs(actual-r.rate);Check(std::isfinite(actual)&&error<=r.budget,"Original raw-term rate budget failed");mr=(std::max)(mr,error/r.budget);if(!variant){baseline[id-Fixed]=actual;budgets[id-Fixed]=r.budget;}const double ib=(std::max)(budgets[id-Fixed],r.budget),ie=fabs(actual-baseline[id-Fixed]);Check(ie<=ib,"Normal flip/scale exceeds original budget");mi=(std::max)(mi,ie/ib);
            if(a.z[q]>.5){const double expected=(field==2?0.:1000.);Check(fabs(r.gp.z-expected)<=64.*FLT_EPSILON*(std::max)(1.,r.agp.z)+1e-6&&fabs(r.gp.x)<=64.*FLT_EPSILON*(std::max)(1.,r.agp.x)+1e-6,"Independent upper affine gradient failed");if(field!=1)Check(fabs(actual)<=r.budget,"Compatible/tangential upper rate not0 within original budget");upper++;}
            const double sig=fabs(actual-r.old)/(std::max)(r.budget,r.oldbudget);if(!Surface(a.fs[q])||field!=1)Check(fabs(actual-r.old)<=(std::max)(r.budget,r.oldbudget),"Unmasked/compatible old action differs");if(Surface(a.fs[q])){tops++;signal=(std::max)(signal,sig);}rates<<field<<','<<variant<<','<<id<<','<<a.z[q]<<','<<a.fs[q]<<','<<actual<<','<<r.rate<<','<<r.old<<','<<r.raw<<','<<r.budget<<','<<r.oldbudget<<','<<error/r.budget<<','<<ie<<','<<ib<<','<<sig<<'\n';t.rows++;
          }Check(upper==500&&tops==10,"Upper/top coverage differs");if(field==1)Check(signal>100,"Closed correction empty against100 original budgets");t.ratio=(std::max)(t.ratio,mr);t.invariance=(std::max)(t.invariance,mi);t.signal=(std::max)(t.signal,signal);affine<<field<<','<<variant<<','<<Soil<<','<<upper<<','<<tops<<','<<mr<<','<<mi<<','<<signal<<'\n';Clock();
        }
      }
      // Invalid-normal probes use an otherwise finite manufactured affine scratch field.
      const auto good=Save();for(unsigned bad=0;bad<2;bad++){good.Restore();auto n=Down(FSNormalg,Np);n[top]=(bad?make_float3(std::numeric_limits<float>::quiet_NaN(),0,1):make_float3(0,0,0));Up(FSNormalg,n);bool matched=false;
        try{Rate(t);}catch(const JException& e){const auto text=e.ToStr();matched=text.find("::ComputeDynamicPorePressureRateGpu)")!=std::string::npos&&text.find("GPU dynamic pore pressure requires valid periodic owners and finite saturated pressure rates.")!=std::string::npos;}good.Restore();DynamicConductivitySpeedMax=good.cache;Check(good.Exact()&&matched,"Exact complete-rate normal guard/rollback failed");probes<<(bad?"NaN_normal":"zero_normal")<<",true,0\n";t.restores++;
      }
      Restore(base,t);PressureApis(natural,owner,top,t,probes);Restore(base,t);Check(t.rows==9000,"Rate row count differs");
    }catch(...){Restore(base,t);PosInteraction_Forces();throw;}
    PosInteraction_Forces();Clock();Check(!Aceg&&!Arg&&!Rsigmag&&!BoundDerivativeVelg&&!HydroMechTopLoadRawg,"Force scratch not freed");(void)cfg;
  }
  void PressureApis(const State& initial,const std::vector<unsigned>& owner,unsigned top,Totals& t,std::ofstream& probes){
    // Independent, initialized buffers: these are pressure update APIs, not host integration.
    Device<float> old(Np),rate(Np),result(Np);Device<double2> preGeometry(Np),corrGeometry(Np);Up(old.p,std::vector<float>(Np,7));Up(rate.p,std::vector<float>(Np,3));Up(preGeometry.p,initial.xy);Up(corrGeometry.p,initial.xy);
    for(unsigned stage=0;stage<2;stage++)for(unsigned active=0;active<2;active++){Up(result.p,std::vector<float>(Np,-123.25f));const double dt=FixedDt->GetFixedValue()*(stage?1.:.5);Check(std::isfinite(dt)&&dt>0,"Invalid retained pressure API dt");cusph::UpdatePorePressureSymplectic(Np,Npb,dt,Codeg,old.p,rate.p,result.p,active!=0,HydroMechTopLoadMode,stage?corrGeometry.p:preGeometry.p,FSTypeg);const auto actual=Down(result.p,Np);for(unsigned q=0;q<Np;q++){const float expected=(q<Npb||!CODE_IsFluid(initial.code[q])?7.f:(active&&Surface(initial.fs[q])?0.f:float(7.+dt*3.)));Check(!memcmp(&actual[q],&expected,sizeof(float)),"Pressure Pre/Corr API constraint/history differs");}t.pressure_api++;}
    auto p=initial.p,rr=initial.rate;auto theta=initial.theta;for(unsigned q=0;q<Np;q++)if(CODE_IsFluid(initial.code[q])){p[q]=CODE_IsNormal(initial.code[q])?7.f:-123.25f;rr[q]=3.f;theta[q]=.125;}Up(PorePressg,p);Up(PorePressRateg,rr);Up(PoroThetag,theta);
    TimeStep=HydroMechDrainageStartTime;Check(IsHydroMechDrainageActive(),"Actual event API not active");ApplyFreeSurfacePorePressure();auto a=Capture(true);t.owner+=Copies(a,owner,true);unsigned zeros=0;for(unsigned id=Fixed;id<Total;id++){const auto q=owner[id];Check(a.j[q]==initial.j[q]&&a.theta[q]==.125,"Drain projection froze/changed J or theta");if(Surface(a.fs[q])){Check(a.p[q]==0&&a.rate[q]==0,"Active host projection p/rate not0");zeros++;}}Check(zeros==10&&a.p[top]==0,"Active projection empty");Rate(t);a=Capture(true);t.owner+=Copies(a,owner,false);for(unsigned id=Fixed;id<Total;id++){const auto q=owner[id];Check(std::isfinite(a.rate[q])&&(!Surface(a.fs[q])||a.rate[q]==0),"Active complete rate not Dirichlet0");}probes<<"active_host_p_rate_and_owner,true,"<<zeros<<'\n';TimeStep=0;
    // Actual owner-copy kernel, independently allocated map/pressure/invalid buffers.
    Device<unsigned> map(Soil),invalid(1);Device<float> pressure(Np);cusph::CalcRidp(true,Np-Npb,Npb,Fixed,Total,Codeg,Idpg,map.p);auto mapping=Down(map.p,Soil);for(unsigned id=Fixed;id<Total;id++)Check(mapping[id-Fixed]==owner[id],"Actual owner map differs from independent ID map");
    auto testp=initial.p;unsigned first=UINT_MAX;for(unsigned q=0;q<Np;q++)if(CODE_IsFluid(initial.code[q])){testp[q]=CODE_IsNormal(initial.code[q])?float(initial.id[q]):-123.25f;if(CODE_IsPeriodic(initial.code[q]))first=(std::min)(first,q);}Check(first!=UINT_MAX,"No periodic bad-owner target");Up(pressure.p,testp);Up(invalid.p,std::vector<unsigned>{Np});cusph::ExtendDynamicPorePeriodic(Np,Npb,Fixed,Total,Codeg,Idpg,map.p,nullptr,nullptr,nullptr,nullptr,invalid.p,pressure.p);Check(Down(invalid.p,1)[0]==Np,"Positive pressure owner kernel invalid");const auto copied=Down(pressure.p,Np);unsigned ghosts=0;
    for(unsigned q=Npb;q<Np;q++)if(CODE_IsPeriodic(initial.code[q])&&CODE_IsFluid(initial.code[q])){Check(copied[q]==float(initial.id[q]),"Actual periodic pressure extension differs");ghosts++;}Check(ghosts>0,"Owner kernel witness empty");t.owner+=ghosts;
    const unsigned badid=initial.id[first];mapping[badid-Fixed]=owner[0];Up(map.p,mapping);Up(pressure.p,testp);Up(invalid.p,std::vector<unsigned>{Np});cusph::ExtendDynamicPorePeriodic(Np,Npb,Fixed,Total,Codeg,Idpg,map.p,nullptr,nullptr,nullptr,nullptr,invalid.p,pressure.p);unsigned wanted=UINT_MAX;for(unsigned q=Npb;q<Np;q++)if(CODE_IsPeriodic(initial.code[q])&&CODE_IsFluid(initial.code[q])&&initial.id[q]==badid)wanted=(std::min)(wanted,q);Check(Down(invalid.p,1)[0]==wanted&&wanted<Np,"Bad owner not rejected by exact invalid-index API");probes<<"bad_owner_kernel_invalid_index,true,"<<wanted<<'\n';Clock();
  }
  void Load(unsigned trial,Totals& t,std::ofstream& rows,std::ofstream& summary){
    auto before=Capture();const auto owner=Owners(before);for(unsigned q=0;q<Np;q++)if(CODE_IsFluid(before.code[q]))before.j[q]=(trial<2?1.:(trial==2?1.+1./256.:1.+(2.*before.z[q]-1.)/256.));Up(PoroJg,before.j);const auto physical=Physical(before,owner);TimeStep=(trial?.005:0.);const double clock=TimeStep;
    Check(!IsHydroMechDrainageActive(),"Load source-clock must remain pre-open");try{Interaction_Forces(INTERSTEP_SymPredictor);t.force++;const auto a=Capture(true);Check(Physical(a,Owners(a))==physical&&TimeStep==clock&&!Nstep,"Real force changed named native inputs/clock");
      const double q=(trial?5000.:0.),rhow=SoilCte.PoreWaterRho,v0=double(MassFluid)/RhopZero;const float provisional=float(q/(double(RhopZero)*double(JSph::Dp)));double zmax=-DBL_MAX;for(unsigned id=Fixed;id<Total;id++)zmax=(std::max)(zmax,a.z[owner[id]]);
      double target=0,raw=0,load=0,force=0,wrong=0,al=0,af=0;unsigned ntop=0,band=0;
      for(unsigned id=Fixed;id<Total;id++){const auto p=owner[id];const auto n=Vec(a.normal[p]);const double norm=sqrt(Dot(n,n));const bool top=Surface(a.fs[p])&&norm>1e-12&&n.z/norm>.35,inband=a.z[p]>zmax-double(KernelSize);if(top){target-=double(MassFluid)*provisional;ntop++;}band+=unsigned(inband);const double por=1.-(1.-double(SoilCte.Porosity))/a.j[p],V=v0*a.j[p],rho=rhow+(double(RhopZero)-rhow)/a.j[p],mass=rho*V,mref=v0*(double(RhopZero)-rhow+rhow*a.j[p]);Check(std::isfinite(por)&&por>0&&por<1&&fabs(mass-mref)<=5e-13*fabs(mref),"Mixture rhoV ledger differs");
        Check(std::isfinite(a.raw[p])&&std::isfinite(a.load[p].z)&&std::isfinite(a.ace[p].z)&&std::isfinite(a.rate[p])&&a.theta[p]==0&&a.ace[p].x==0&&a.ace[p].y==0&&a.load[p].x==0&&a.load[p].y==0&&(inband||a.load[p].z==0),"Invalid same-stage load output");if(inband)raw+=mass*a.raw[p];load+=mass*a.load[p].z;force+=mass*a.ace[p].z;wrong+=double(MassFluid)*a.load[p].z;al+=fabs(mass*a.load[p].z);af+=fabs(mass*a.ace[p].z);if(!trial)Check(a.raw[p]==0&&a.load[p].z==0&&a.ace[p].z==0&&a.rate[p]==0,"Natural zero-q stage not strictly0");rows<<trial<<','<<clock<<','<<id<<','<<a.z[p]<<','<<a.j[p]<<','<<por<<','<<V<<','<<rho<<','<<mass<<','<<a.fs[p]<<','<<inband<<','<<a.raw[p]<<','<<a.load[p].z<<','<<a.ace[p].z<<','<<a.theta[p]<<','<<a.rate[p]<<'\n';}
      const double analytic=-q*.1,lb=ForceBudget(al,target),fb=ForceBudget(af,target),lr=(std::max)(fabs(load-target),fabs(load-analytic))/lb,fr=(std::max)(fabs(force-target),fabs(force-analytic))/fb,wr=fabs(wrong-target)/(std::max)(lb,fb);Check(std::isfinite(raw)&&std::isfinite(load)&&std::isfinite(force)&&std::isfinite(wrong)&&lr<=1&&fr<=1,"Original same-stage force budget failed");if(trial)Check(ntop>0&&band>0&&target<0&&raw<0,"Empty/downward target/raw load");else Check(target==0&&raw==0&&load==0&&force==0,"Zero-q resultant differs");if(trial>=2){Check(wr>100,"Wrong reference mass empty against100 force budgets");t.wrong=(std::min)(t.wrong,wr);}t.loadratio=(std::max)(t.loadratio,lr);t.aceratio=(std::max)(t.aceratio,fr);summary<<trial<<','<<clock<<','<<q<<','<<ntop<<','<<band<<','<<target<<','<<analytic<<','<<raw<<','<<load<<','<<force<<','<<wrong<<','<<al<<','<<af<<','<<lb<<','<<fb<<','<<lr<<','<<fr<<','<<wr<<'\n';
    }catch(...){TimeStep=0;if(Aceg)PosInteraction_Forces();throw;}TimeStep=0;PosInteraction_Forces();Clock();Check(!Aceg&&!Arg&&!Rsigmag&&!BoundDerivativeVelg&&!HydroMechTopLoadRawg,"Load force scratch not freed");
  }
};
}
int main(int argc,char** argv){try{
  Check(argc==5&&std::string(argv[1])=="--input"&&std::string(argv[3])=="--out","Use --input RETAINED_CASE02_PRIVATE_XML --out FRESH_DIR");const fs::path xml=argv[2],out=argv[4];auto prefix=xml;prefix.replace_extension();Check(fs::is_regular_file(xml)&&fs::is_regular_file(prefix.string()+".bi4")&&fs::is_regular_file(prefix.string()+"_Normals.nbi4")&&!fs::exists(out),"Retained XML/BI4/Normals and fresh output required");
  AppInfo.ConfigRunPaths(argv[0]);std::vector<std::string> args={argv[0],"-gpu:0","-stable","-mdbc_freeslip",prefix.string(),out.string(),"-dirdataout","data","-svres"};std::vector<char*> a;for(auto& s:args)a.push_back(s.data());JSphCfgRun cfg;cfg.LoadArgv(int(a.size()),a.data());Check(!cfg.Cpu&&cfg.Stable&&!cfg.PrintInfo&&!cfg.PartBegin&&!cfg.NstepsBreak&&cfg.TimeMax<0&&cfg.TimePart<0&&!cfg.SvAllSteps,"No solver/restart/clock override");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
  std::ofstream rates(out/"rates.csv"),affine(out/"affine.csv"),probes(out/"probes.csv"),loads(out/"loads.csv"),summary(out/"load_summary.csv");for(auto* s:{&rates,&affine,&probes,&loads,&summary})*s<<std::setprecision(17);
  rates<<"field,normal_variant,id,z,FSType,actual_rate,independent_rate,old_rate,raw_abs_rate,budget,old_budget,error_ratio,invariance_error,invariance_budget,signal_ratio\n";affine<<"field,normal_variant,rows,upper_rows,top_rows,max_error_ratio,max_invariance_ratio,max_signal_ratio\n";probes<<"probe,passed,witness_count_or_invalid_index\n";loads<<"case,manufactured_clock_s,id,z,J,n,V,rho,mass,FSType,in_actual_band,raw_band_az,LoadAce_z,Ace_z,theta,rate\n";summary<<"case,manufactured_clock_s,q_Pa,top_count,band_count,retained_target_N,analytic_qA0_N,raw_weighted_N,rhoV_LoadAce_N,rhoV_Ace_N,wrong_MassFluid_N,abs_load_N,abs_force_N,load_budget_N,force_budget_N,load_error_ratio,force_error_ratio,wrong_weight_ratio\n";
  columncomponent::Totals total;{columncomponent::ComponentScratch scratch;scratch.Init(&cfg,AppInfo.LogPtr());scratch.Operators(&cfg,total,rates,affine,probes);}for(unsigned trial=0;trial<4;trial++){columncomponent::ComponentScratch scratch;scratch.Init(&cfg,AppInfo.LogPtr());scratch.Load(trial,total,loads,summary);}
  for(auto* s:{&rates,&affine,&probes,&loads,&summary}){s->flush();Check(bool(*s),"Component CSV write failed");}Check(total.force==5&&total.rate==12&&total.rows==9000&&total.pressure_api==4&&total.owner>0&&total.wrong>100,"Declared component coverage differs");
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_gpu_column_component_r1\",\"passed\":true,\"native_count\":1000,\"fixed_count\":40,\"actual_force_calls\":5,\"explicit_complete_rate_calls\":"<<total.rate<<",\"rate_rows\":9000,\"affine_summary_rows\":9,\"load_rows\":4000,\"load_summary_rows\":4,\"pressure_API_calls\":4,\"normal_exact_method_rejections\":2,\"bad_owner_invalid_index_rejections\":1,\"periodic_owner_checks\":"<<total.owner<<",\"named_scratch_restores\":"<<total.restores<<",\"max_rate_error_over_original_budget\":"<<total.ratio<<",\"max_normal_invariance_over_original_budget\":"<<total.invariance<<",\"incompatible_signal_over_original_budget\":"<<total.signal<<",\"max_load_resultant_over_original_budget\":"<<total.loadratio<<",\"max_finished_force_over_original_budget\":"<<total.aceratio<<",\"minimum_wrong_mass_over_original_budget\":"<<total.wrong<<",\"manufactured_component_scratch_only\":true,\"reference_conditioned_on_actual_C_wall_Ace\":true,\"host_PreCorr_or_Run_or_ComputeStep_or_SaveData_called\":false,\"actualRun_initial_field_overwritten\":false,\"physical_steps_advanced\":0,\"source_SHA_checked_by_component\":false,\"public_master\":0,\"physical_acceptance\":false}\n";done.flush();Check(bool(done),"Component completion write failed");return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"GPU column component rejected; retain partial evidence\n";return 2;}}
