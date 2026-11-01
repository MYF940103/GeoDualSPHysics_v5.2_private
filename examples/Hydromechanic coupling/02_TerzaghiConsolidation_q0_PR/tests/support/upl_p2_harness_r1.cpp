// P2 CPU observer diagnostics. Reuse actual project interactions and integrator.
// No dynamic Darcy, volume/inertia feedback, XML model option or physical claim.
#define main RetainedBoundaryPairMain
#include "bv_pair_cpu_r1.cpp"
#undef main
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JLog2.h"
#include "JArraysCpu.h"
#include "JPartDataBi4.h"
#include <map>

class ObserverPair:public Pair{
  double theta[2]={};
public:
  ObserverPair(){PorosityObserver=true;PoroThetac=theta;}
  ~ObserverPair(){PoroThetac=nullptr;PorosityObserver=false;}
  void CheckRates(std::ostream& out){
    for(unsigned dim:{2u,3u})for(unsigned slip:{1u,2u,3u}){
      for(unsigned trial=0;trial<4;trial++){
        theta[0]=theta[1]=0;
        const float ax=(trial==2?.5f:0),az=(trial==0?.5f:(trial==1?-.5f:0));
        const auto r=run(dim,slip,"observer_pair",true,ax,az,0);
        const double exact=r.Lzz,tol=64*FLT_EPSILON*(std::max)(1.,fabs(exact));
        Check(std::isfinite(theta[1])&&fabs(theta[1]-exact)<=tol,"Actual ct theta differs from corrected divergence");
        Check(theta[0]==0,"Observer wrote a wall receiver");
        if(trial>=2)Check(theta[1]==0,"Pure shear/zero theta is not exactly null");
        out<<dim<<','<<slip<<','<<trial<<','<<theta[1]<<','<<exact<<','<<tol<<'\n';
      }
    }
  }
};

class ObserverFixture:public JSphCpuSingle{
  bool Normal(unsigned p)const{return CODE_IsNormal(Codec[p]);}
  bool Soil(unsigned p)const{return Normal(p)&&CODE_IsFluid(Codec[p]);}
  static double Tag(unsigned id){return id<40?1.:1.+double(id)*1e-6;}
  static double Rate(unsigned id){return id<40?0.:(int(id%7)-3)*.125;}
  void Initialize(const JSphCfgRun* cfg,JLog2* log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(cfg->SvTimers);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunCpu();FreePartsInit();
    Check(HydroMech&&Simulate2D&&TStep==STEP_Symplectic&&CaseNfluid==1000&&CaseNpb==40,"Only retained case02 fresh geometry admitted");
    Check(PeriX&&!PeriY&&!PeriZ&&PoroJc&&PoroThetac&&!PoroJPrec,"Expected initialized periodic observer");
  }
  void Tagged(bool predicted,double dt)const{
    unsigned normal=0,periodic=0;
    for(unsigned p=0;p<Np;p++){
      Check(Idpc[p]<1040,"Unexpected observer identity");
      const bool soil=CODE_IsFluid(Codec[p]);
      const double base=Tag(Idpc[p]),rate=Rate(Idpc[p]);
      const double expected=predicted&&soil?base+(dt*.5)*base*rate:base;
      Check(PoroJc[p]==expected&&PoroThetac[p]==rate,"J/theta identity lost in sorting/periodic/resize");
      if(predicted)Check(PoroJPrec&&PoroJPrec[p]==base,"Saved full J identity lost");
      if(Normal(p))normal++;else if(CODE_IsPeriodic(Codec[p]))periodic++;
    }
    Check(normal==1040&&periodic>0,"Native/periodic identity coverage missing");
  }
public:
  void Enable(bool enabled){PorosityObserver=enabled;}
  void Final(const fs::path& out)const{
    Check(!PoroJPrec,"Predictor state survived full-step completion");
    std::ofstream csv(out/"observer_final.csv");csv<<std::setprecision(17)<<"id,J,n,theta\n";
    std::map<unsigned,unsigned> order;
    for(unsigned p=0;p<Np;p++)if(Normal(p))Check(order.emplace(Idpc[p],p).second,"Duplicate normal ID");
    Check(order.size()==1040,"Final native count changed");
    if(PorosityObserver)for(const auto& a:order){const unsigned p=a.second;const double j=PoroJc[p],n=1.-(1.-double(SoilCte.Porosity))/j;
      Check(std::isfinite(j)&&std::isfinite(n)&&j>1.-double(SoilCte.Porosity),"Invalid final observer state");
      csv<<a.first<<','<<j<<','<<(CODE_IsFluid(Codec[p])?n:0.)<<','<<PoroThetac[p]<<'\n';}
    else Check(!PoroJc&&!PoroThetac,"OFF unexpectedly allocated observer arrays");
    csv.flush();Check(bool(csv),"Observer export failed");
    std::ofstream done(out/"observer_complete.json");done<<std::setprecision(17)
      <<"{\"observer\":"<<(PorosityObserver?"true":"false")<<",\"actual_time_s\":"<<TimeStep<<",\"completed_steps\":"<<Nstep
      <<",\"actual_production_Run\":true,\"feedback\":false,\"physical_acceptance\":false}\n";
    done.flush();Check(bool(done),"Observer completion export failed");
  }
  void State(const JSphCfgRun* cfg,JLog2* log){
    Enable(true);Initialize(cfg,log);
    for(unsigned p=0;p<Np;p++)Check(PoroJc[p]==1.&&PoroThetac[p]==0.,"Fresh observer initialization wrong");
    // An actual active drainage stage must still expose volume divergence.
    TimeStep=.02;
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsFluid(Codec[p]))Velrhopc[p].z=float(-.02*Posc[p].z);
    InterStep=INTERSTEP_SymPredictor;Interaction_Forces(INTERSTEP_SymPredictor);
    unsigned drained=0;
    for(unsigned p=Npb;p<Np;p++)if(Soil(p)&&IsHydroMechDrainedParticle(p,Posc,Codec,FSTypec)){
      Check(std::isfinite(PoroThetac[p])&&fabs(PoroThetac[p])>1e-8&&PorePressRatec[p]==0,"Drained theta was suppressed with pressure rate");drained++;
    }
    Check(drained==10,"Active drainage coverage must be ten true top native particles");
    PosInteraction_Forces();TimeStep=0;
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsFluid(Codec[p]))Velrhopc[p].z=0;
    Interaction_Forces(INTERSTEP_SymPredictor);
    for(unsigned p=0;p<Np;p++){PoroJc[p]=Tag(Idpc[p]);PoroThetac[p]=Rate(Idpc[p]);}
    const double dt=1./1024.;ComputeSymplecticPre(dt);PosInteraction_Forces();
    // Exchange two distant native positions/cells only to force a real cell reorder.
    unsigned first=~0u,last=~0u;
    for(unsigned p=Npb;p<Np;p++)if(Soil(p)){if(first==~0u)first=p;last=p;}
    Check(first!=~0u&&first!=last&&Dcellc[first]!=Dcellc[last],"No distinct cells available");
    std::swap(Posc[first],Posc[last]);std::swap(Dcellc[first],Dcellc[last]);
    const std::vector<unsigned> before(Idpc,Idpc+Np);RunCellDivide(true);Tagged(true,dt);
    Check(before.size()!=Np||!std::equal(before.begin(),before.end(),Idpc),"Cell reorder was not exercised");
    RunCellDivide(true);Tagged(true,dt); // Periodic J and saved J both need copying.
    const unsigned oldsize=CpuParticlesSize;ResizeCpuMemoryParticles(oldsize+1);
    Check(CpuParticlesSize>oldsize,"Resize did not grow storage");Tagged(true,dt);
    for(unsigned p=0;p<Np;p++){
      PoroThetac[p]=-Rate(Idpc[p])*.75;
      if(CODE_IsPeriodic(Codec[p]))Kplasticc[p]=123.f; // Not a maintained native plastic state.
    }
    ComputeSymplecticCorrPorosity(dt);Check(!PoroJPrec,"Corrector did not release saved J");
    unsigned checked=0;
    for(unsigned p=0;p<Np;p++)if(Normal(p)){
      const double base=Tag(Idpc[p]),mid=base+(dt*.5)*base*Rate(Idpc[p]);
      const double expected=CODE_IsFluid(Codec[p])?base+dt*mid*(-Rate(Idpc[p])*.75):base;
      Check(PoroJc[p]==expected,"Corrector recurrence/base-stage identity failed");
      const double n=1.-(1.-double(SoilCte.Porosity))/PoroJc[p];
      Check(fabs((1.-n)*PoroJc[p]-(1.-double(SoilCte.Porosity)))<=5e-13,"Solid-volume invariant failed");checked++;
    }
    Check(checked==1040,"Incomplete recurrence coverage");
    unsigned native=~0u;for(unsigned p=Npb;p<Np;p++)if(Soil(p)){native=p;break;}
    Check(native!=~0u,"No native soil for rejection test");
    for(unsigned p=0;p<Np;p++)PoroThetac[p]=0;
    ComputeSymplecticPrePorosity(dt);Kplasticc[native]=1;
    bool plasticRejected=false;
    try{ComputeSymplecticCorrPorosity(dt);}catch(const std::exception& e){plasticRejected=std::string(e.what()).find("finite saturated elastic")!=std::string::npos;}
    Check(plasticRejected,"Nonzero normal-native plastic state was not rejected");Kplasticc[native]=0;
    ArraysCpu->Free(PoroJc);PoroJc=PoroJPrec;PoroJPrec=nullptr;
    unsigned domainRejected=0;
    for(double bad:{.5,std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity()}){
      PoroJc[native]=bad;bool rejected=false;
      try{ComputeSymplecticPrePorosity(dt);}catch(const std::exception& e){rejected=std::string(e.what()).find("saturated incompressible-grain")!=std::string::npos;}
      Check(rejected,"Nonphysical/nonfinite J was not rejected");domainRejected++;
      ArraysCpu->Free(PoroJc);PoroJc=PoroJPrec;PoroJPrec=nullptr;PoroJc[native]=1.;
    }
    // One real predictor is exercised, not a completed coupled physical trajectory.
    std::ofstream done(fs::path(cfg->DirOut)/"state_complete.json");done
      <<"{\"passed\":true,\"native_checks\":1040,\"active_drained_theta_checks\":10,\"actual_cell_reorder\":true,\"periodic_full_and_predictor\":true,\"actual_resize\":true,\"periodic_plastic_poison_ignored\":true,\"native_plastic_rejected\":true,\"invalid_J_rejections\":"<<domainRejected<<",\"production_J_methods\":true,\"coupled_physics_accepted\":false}\n";
    done.flush();Check(bool(done),"State completion write failed");
  }
};

template<class T>static std::vector<T> NativeArray(JPartDataBi4& p,const char* name,unsigned n,JBinaryDataDef::TpData type){
  const auto* a=p.GetArray(name,type);Check((a->DataInPointer()?a->GetCount():a->GetFileDataCount())==n,"Wrong native array count");
  std::vector<T> v(n);a->GetDataCopy(n,v.data());return v;
}
static void ReadPoro(const char* dir,unsigned part,const fs::path& target){
  Check(!fs::exists(target),"Native observer export already exists");JPartDataBi4 p;p.LoadFilePart(dir,part,0,1);
  const unsigned n=p.Get_Npok();Check(n==1040&&!p.Get_Nout(),"Native particle set changed");
  const auto id=NativeArray<unsigned>(p,"Idp",n,JBinaryDataDef::DatUint);
  const auto j=NativeArray<double>(p,"PoroVolumeRatio",n,JBinaryDataDef::DatDouble),pn=NativeArray<double>(p,"PoroPorosity",n,JBinaryDataDef::DatDouble),theta=NativeArray<double>(p,"PoroThetaLastStage",n,JBinaryDataDef::DatDouble);
  std::map<unsigned,unsigned> order;for(unsigned i=0;i<n;i++)Check(order.emplace(id[i],i).second,"Duplicate native ID");
  std::ofstream out(target);out<<std::setprecision(17)<<"id,J,n,theta\n";
  for(const auto& a:order){const auto i=a.second;Check(std::isfinite(j[i])&&std::isfinite(pn[i])&&std::isfinite(theta[i]),"Nonfinite native observer");
    const double expected=(a.first<40?0.:1.-(1.-double(float(.3)))/j[i]);
    Check(pn[i]==expected&&j[i]>1.-double(float(.3)),"Native derived porosity does not match J");
    if(a.first<40)Check(j[i]==1.&&theta[i]==0.,"Native wall marker changed");
    out<<a.first<<','<<j[i]<<','<<pn[i]<<','<<theta[i]<<'\n';}
  out.flush();Check(bool(out),"Native observer CSV failed");
}
static bool Finite(unsigned){return true;}
static bool Finite(float x){return std::isfinite(x);}
static bool Finite(tfloat3 x){return std::isfinite(x.x)&&std::isfinite(x.y)&&std::isfinite(x.z);}
static bool Finite(tdouble3 x){return std::isfinite(x.x)&&std::isfinite(x.y)&&std::isfinite(x.z);}
template<class T>static void ExactArray(JPartDataBi4& a,JPartDataBi4& b,const char* name,JBinaryDataDef::TpData type,const std::vector<unsigned>& ia,const std::vector<unsigned>& ib){
  const unsigned n=unsigned(ia.size());const auto x=NativeArray<T>(a,name,n,type),y=NativeArray<T>(b,name,n,type);
  std::vector<unsigned> order(n,~0u);
  for(unsigned i=0;i<n;i++)Check(ib[i]<n&&order[ib[i]]==~0u,"Invalid comparison ID"),order[ib[i]]=i;
  for(unsigned i=0;i<n;i++)Check(ia[i]<n&&order[ia[i]]!=~0u&&Finite(x[i])&&Finite(y[order[ia[i]]])&&!memcmp(&x[i],&y[order[ia[i]]],sizeof(T)),name);
}
static void Compare(const char* da,const char* db,unsigned part,const fs::path& target){
  Check(!fs::exists(target),"Comparison receipt exists");JPartDataBi4 a,b;a.LoadFilePart(da,part,0,1);b.LoadFilePart(db,part,0,1);
  Check(a.Get_Npok()==1040&&b.Get_Npok()==1040&&!a.Get_Nout()&&!b.Get_Nout(),"Native set/exclusion changed");
  const double ta=a.Get_TimeStep(),tb=b.Get_TimeStep();Check(!memcmp(&ta,&tb,sizeof(double))&&a.Get_Step()==b.Get_Step(),"Saved time/step changed");
  const auto ia=NativeArray<unsigned>(a,"Idp",1040,JBinaryDataDef::DatUint),ib=NativeArray<unsigned>(b,"Idp",1040,JBinaryDataDef::DatUint);
  ExactArray<unsigned>(a,b,"Idp",JBinaryDataDef::DatUint,ia,ib);
  ExactArray<tdouble3>(a,b,"Posd",JBinaryDataDef::DatDouble3,ia,ib);
  for(const char* name:{"Vel","Sigma_kk","Sigma_ij","FSNormal","HydroMechLoadAce"})ExactArray<tfloat3>(a,b,name,JBinaryDataDef::DatFloat3,ia,ib);
  for(const char* name:{"Rhop","Kplastic","PorePress","PorePress0","ExcessPorePress"})ExactArray<float>(a,b,name,JBinaryDataDef::DatFloat,ia,ib);
  for(const char* name:{"SigmaState_kk","SigmaState_ij"})ExactArray<tdouble3>(a,b,name,JBinaryDataDef::DatDouble3,ia,ib);
  ExactArray<unsigned>(a,b,"FSType",JBinaryDataDef::DatUint,ia,ib);
  const auto rho=NativeArray<float>(a,"Rhop",1040,JBinaryDataDef::DatFloat),kp=NativeArray<float>(a,"Kplastic",1040,JBinaryDataDef::DatFloat);
  for(unsigned i=0;i<1040;i++)Check(rho[i]>0&&kp[i]==0,"Nonpositive density or plastic state");
  const auto* pa=a.GetPart();const auto* pb=b.GetPart();
  Check(pa->ExistsValue("dterror")==pb->ExistsValue("dterror"),"dterror presence changed");
  const double ea=pa->GetvDouble("dterror",true,0),eb=pb->GetvDouble("dterror",true,0);
  Check(!memcmp(&ea,&eb,sizeof(double))&&ea<=1e-14&&eb<=1e-14,"dterror changed/exceeds original safety");
  std::ofstream out(target);out<<"{\"passed\":true,\"native_count\":1040,\"arrays\":15,\"native_ID_aligned\":true,\"all_original_physical_array_bits_identical\":true,\"saved_time_step_dterror_exact\":true,\"no_exclusions\":true,\"physical_acceptance\":false}\n";
  out.flush();Check(bool(out),"Comparison receipt failed");
}
int main(int argc,char** argv){
  try{
    Check(argc>=2,"Use --pair OUT, --state solverargs, --solver 0|1 solverargs, --read-poro DATA PART CSV");
    const std::string mode=argv[1];
    if(mode=="--pair"){
      Check(argc==3&&!fs::exists(argv[2]),"Expected fresh pair output");fs::create_directories(argv[2]);
      std::ofstream out(fs::path(argv[2])/"theta_pairs.csv");out<<std::setprecision(17)<<"dimension,slip,trial,theta,reference,tolerance\n";
      {ObserverPair p;p.CheckRates(out);}out.flush();Check(bool(out),"Pair output failed");return 0;
    }
    if(mode=="--read-poro"){Check(argc==5,"Expected DATA PART CSV");ReadPoro(argv[2],unsigned(std::stoul(argv[3])),argv[4]);return 0;}
    if(mode=="--compare"){Check(argc==6,"Expected DATA1 DATA2 PART NEW_JSON");Compare(argv[2],argv[3],unsigned(std::stoul(argv[4])),argv[5]);return 0;}
    const bool solver=mode=="--solver";Check(solver||mode=="--state","Unknown fixture mode");
    const unsigned start=solver?3:2;Check(argc>int(start+2),"Missing solver arguments");
    const bool enabled=solver?std::string(argv[2])=="1":true;Check(!solver||std::string(argv[2])=="0"||enabled,"Observer must be0or1");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=int(start);i<argc;i++)args.push_back(argv[i]);
    JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());cfg.Cpu=true;
    Check(!fs::exists(cfg.DirOut),"Retained output protected");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);
    AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");ObserverFixture fixture;fixture.Enable(enabled);
    if(solver){fixture.Run(AppInfo.GetFullName(),&cfg,AppInfo.LogPtr());fixture.Final(cfg.DirOut);}
    else fixture.State(&cfg,AppInfo.LogPtr());return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"P2 fixture failed; preserve Run.out and partial evidence\n";return 2;}
}
