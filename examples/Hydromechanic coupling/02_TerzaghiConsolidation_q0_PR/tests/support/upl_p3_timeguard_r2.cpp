// Necessary private-P3 step guards; actual helper, DtVariable and rejected first step.
#define main RetainedP2FeedbackMain
#include "upl_p2_feedback_harness_r1.cpp"
#undef main
#include "JDsFixedDt.h"
#include <limits>
struct StepScales{double wave,pore,cu2max,dmax,margin;};
class TimeGuard:public Feedback{
  unsigned Dimension;
  struct Physical{
    std::vector<tdouble3> x;std::vector<tfloat4> vr;std::vector<double> j;
    std::vector<float> p,p0,kplastic;std::vector<tsymatrix3d> sigma;
    std::vector<unsigned> id;std::vector<typecode> code;
  };
  template<class T> static bool Same(const std::vector<T>& a,const std::vector<T>& b){return a.size()==b.size()&&!memcmp(a.data(),b.data(),sizeof(T)*a.size());}
  Physical Capture()const{return {{Posc,Posc+Np},{Velrhopc,Velrhopc+Np},{PoroJc,PoroJc+Np},{PorePressc,PorePressc+Np},{PorePress0c,PorePress0c+Np},{Kplasticc,Kplasticc+Np},{Sigmac,Sigmac+Np},{Idpc,Idpc+Np},{Codec,Codec+Np}};}
  static bool Same(const Physical& a,const Physical& b){return Same(a.x,b.x)&&Same(a.vr,b.vr)&&Same(a.j,b.j)&&Same(a.p,b.p)&&Same(a.p0,b.p0)&&Same(a.kplastic,b.kplastic)&&Same(a.sigma,b.sigma)&&Same(a.id,b.id)&&Same(a.code,b.code);}
  void SetFixed(double dt){delete FixedDt;FixedDt=dt>0?new JDsFixedDt(dt):nullptr;}
  void Reset(float k=1e-4f,float gravity=0){
    SetFixed(0);SoilCte.HydraulicConductivity=k;Gravity=TFloat3(0,0,gravity);CSP.gravity=Gravity;
    CFLnumber=.2;PoreDtSafety=.1f;VelMax=.125;ViscDtMax=.5f;AceMax=0;DtMin=0;DtModif=0;TimeStep=0;Nstep=0;SymplecticDtPre=1e-10;
    for(unsigned p=0;p<Np;p++){Codec[p]=CODE_TYPE_FLUID;PoroJc[p]=.9375+.03125*(p%5);PoroThetac[p]=0;Velrhopc[p]=TFloat4(0,0,0,RhopZero);PorePressc[p]=PorePress0c[p]=0;Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;}
  }
  StepScales Independent(std::ostream* layers=nullptr,const char* tag="")const{
    const double n0=SoilCte.Porosity,kw=SoilCte.PoreWaterBulkModulus,rhow=SoilCte.PoreWaterRho;
    const double rhos=(double(RhopZero)-n0*rhow)/(1-n0),m=double(SoilCte.ModulusK)+4*double(SoilCte.ModulusG)/3;
    const double normg=sqrt(double(Gravity.x)*Gravity.x+double(Gravity.y)*Gravity.y+double(Gravity.z)*Gravity.z),gamma=rhow*(normg>0?normg:9.80665);
    StepScales s{0,DBL_MAX,0,0,DBL_MAX};
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])&&CODE_IsFluid(Codec[p])){
      const double j=PoroJc[p],n=1-(1-n0)/j,rho=(1-n)*rhos+n*rhow,b=kw/n,cu2=(m+b)/rho,d=b*SoilCte.HydraulicConductivity/gamma,margin=rho*b/(m+b)-rhow;
      s.cu2max=(std::max)(s.cu2max,cu2);s.dmax=(std::max)(s.dmax,d);s.margin=(std::min)(s.margin,margin);
      if(layers)*layers<<Dimension<<','<<tag<<','<<Idpc[p]<<','<<j<<','<<n<<','<<rho<<','<<cu2<<','<<d<<','<<margin<<'\n';
    }
    s.wave=KernelH/((std::max)(sqrt(s.cu2max),10*VelMax)+KernelH*double(ViscDtMax));
    if(s.dmax>0)s.pore=PoreDtSafety*double(KernelH)*KernelH/s.dmax;return s;
  }
  static bool Scaled(double actual,double wanted){return std::isfinite(actual)&&std::isfinite(wanted)&&fabs(actual-wanted)<=256*DBL_EPSILON*(std::max)(fabs(wanted),DBL_MIN);}
  double ActualBound()const{double w,d;GetDynamicStepScalesCpu(w,d);const double force=AceMax?sqrt(KernelH/AceMax):DBL_MAX;return (std::min)(CFLnumber*(std::min)(force,w),d);}
  void WritePhysical(const Physical& a,const char* scenario,const char* phase,std::ostream& out)const{
    for(unsigned p=0;p<a.x.size();p++){const auto x=a.x[p];const auto v=a.vr[p];const auto s=a.sigma[p];out<<Dimension<<','<<scenario<<','<<phase<<','<<a.id[p]<<','<<x.x<<','<<x.y<<','<<x.z<<','<<v.x<<','<<v.y<<','<<v.z<<','<<v.w<<','<<a.j[p]<<','<<a.p[p]<<','<<a.p0[p]<<','<<s.xx<<','<<s.xy<<','<<s.xz<<','<<s.yy<<','<<s.yz<<','<<s.zz<<','<<a.kplastic[p]<<'\n';}
  }
public:
  TimeGuard(unsigned dim):Feedback(dim,dim==2?9:27),Dimension(dim){DynamicPorePressure=true;Reset();InitPorosityObserverCpu();Reset();}
  unsigned ScaleChecks(std::ostream& out,std::ostream& layers){
    unsigned count=0;
    auto run=[&](const char* tag){
      const auto ref=Independent(&layers,tag);double w=0,d=0;GetDynamicStepScalesCpu(w,d);
      Require(Scaled(w,ref.wave)&&(d==DBL_MAX?ref.pore==DBL_MAX:Scaled(d,ref.pore)),"Current J-derived step scale differs from independent constituent formula");
      for(unsigned p=0;p<Np;p++)Velrhopc[p].w=float(1200+37*p);double wp=0,dp=0;GetDynamicStepScalesCpu(wp,dp);
      Require(!memcmp(&w,&wp,sizeof(double))&&!memcmp(&d,&dp,sizeof(double)),"Positive passive-rho poison affected physical step scale");
      out<<Dimension<<','<<tag<<','<<SoilCte.HydraulicConductivity<<','<<Gravity.z<<','<<w<<','<<ref.wave<<','<<d<<','<<ref.pore<<','<<ref.cu2max<<','<<ref.dmax<<",true\n";count++;
    };
    for(float k:{0.f,1e-4f})for(float g:{0.f,-8.f}){Reset(k,g);run(k==0?(g==0?"k0_g0":"k0_g8"):(g==0?"kpositive_g0":"kpositive_g8"));}
    Reset();VelMax=1024;run("velocity_dominated");Reset();ViscDtMax=1e6f;run("viscosity_dominated");Reset(.1f);run("diffusion_dominated");
    Reset();Codec[Np-1]=CODE_SetPeriodic(CODE_TYPE_FLUID);PoroJc[Np-1]=1000;run("ignore_non_normal_image");return count;
  }
  unsigned DomainChecks(std::ostream& out){
    const double m=double(SoilCte.ModulusK)+4*double(SoilCte.ModulusG)/3,solid=1.-double(SoilCte.Porosity);
    const double critical=solid+(double(RhopZero)-SoilCte.PoreWaterRho)*SoilCte.PoreWaterBulkModulus/(double(SoilCte.PoreWaterRho)*m);
    unsigned count=0;
    auto run=[&](const char* tag,double j,float k,bool reject){
      Reset(k);PoroJc[0]=j;double w=0,d=0;bool caught=false;std::string message;
      try{GetDynamicStepScalesCpu(w,d);}catch(const std::exception& e){caught=true;message=e.what();}
      Require(caught==reject,"Continuous-domain boundary rejection disagrees with declaration");
      if(caught)Require(message.find("Dynamic step scales")!=std::string::npos||message.find("Dynamic continuous decay domain failed: id=")!=std::string::npos,"Wrong exception admitted as domain guard");
      if(!reject){Require(std::isfinite(w)&&w>0,"Legal domain produced invalid wave scale");if(k==0)Require(d==DBL_MAX,"k0 incorrectly received a Darcy/RH restriction");}
      out<<Dimension<<','<<tag<<','<<j<<','<<critical<<','<<k<<','<<reject<<','<<caught<<','<<(caught?0:w)<<','<<(caught?0:d)<<'\n';count++;
    };
    run("below_critical_legal",critical*(1-1e-6),1e-4f,false);run("at_critical_rejected",critical,1e-4f,true);run("above_critical_rejected",critical*(1+1e-6),1e-4f,true);
    run("above_critical_k0_legal",critical*(1+1e-6),0,false);run("solid_volume_limit_rejected",solid,1e-4f,true);run("nextafter_solid_limit_legal",std::nextafter(solid,DBL_MAX),1e-4f,false);return count;
  }
  unsigned RequestedChecks(std::ostream& out){
    unsigned count=0;
    for(unsigned which=0;which<10;which++){
      Reset(which==8?.1f:1e-4f);if(which==7)AceMax=1e12;if(which==9)VelMax=1024;
      const auto ref=Independent();const double force=AceMax?sqrt(KernelH/AceMax):DBL_MAX,reference=(std::min)(CFLnumber*(std::min)(force,ref.wave),ref.pore),bound=ActualBound();
      Require(Scaled(bound,reference),"Combined necessary limit differs from independent reference");
      SymplecticDtPre=bound*.25;double expected=bound;bool reject=false;
      const char* tag[]={"variable_safe","fixed_safe","fixed_at_bound","locked_above_bound","fixed_above_bound","DtMin_above_bound","DtMin_above_fixed","force_limit","pore_limit","velocity_limit"};
      if(which==1){SetFixed(bound*.75);DtMin=bound*.5;expected=bound*.75;}
      if(which==2){SetFixed(bound);expected=bound;}
      if(which==3){SymplecticDtPre=std::nextafter(bound,DBL_MAX);reject=true;}
      if(which==4){SetFixed(std::nextafter(bound,DBL_MAX));reject=true;}
      if(which==5){DtMin=std::nextafter(bound,DBL_MAX);reject=true;}
      if(which==6){DtMin=bound*.75;SetFixed(bound*.5);reject=true;}
      const auto before=Capture();const double locked=SymplecticDtPre,minimum=DtMin,fixed=FixedDt?FixedDt->GetFixedValue():0;bool caught=false;double dt=0;std::string message;
      try{dt=DtVariable(false);}catch(const std::exception& e){caught=true;message=e.what();}
      Require(caught==reject,"Requested step rejection disagrees with strict bound declaration");
      if(caught)Require(message.find("Dynamic current step")!=std::string::npos||message.find("Dynamic requested step")!=std::string::npos,"Unrelated exception mistaken for requested-step guard");
      else Require(Scaled(dt,expected)&&dt<=bound&&dt>=DtMin,"Safe request clipped, uplifted or differs from selected fixed/variable step");
      Require(DtModif==0&&Same(before,Capture()),"Time guard uplifted DtMin or changed physical arrays");
      out<<Dimension<<','<<tag[which]<<','<<bound<<','<<reference<<','<<locked<<','<<fixed<<','<<minimum<<','<<reject<<','<<caught<<','<<dt<<",true\n";count++;
    }
    return count;
  }
  unsigned FirstStepChecks(std::ostream& out,std::ostream& states){
    unsigned count=0;
    for(unsigned which=0;which<2;which++){
      Reset(0);SymplecticDtPre=which?1e-10:1.;if(which)SetFixed(1.);
      for(unsigned p=0;p<Np;p++){const auto x=Posc[p];Velrhopc[p].x=float(-x.x/32.);Velrhopc[p].z=float(-x.z/32.);if(Dimension==3)Velrhopc[p].y=float(-x.y/32.);PorePressc[p]=float(128+8*x.x);Sigmac[p]=TSymMatrix3d(100,Dimension==3?3:0,5,200,Dimension==3?7:0,300);PorePressRatec[p]=1234567;}
      const auto before=Capture();const char* tag=which?"safe_locked_unsafe_fixed":"unsafe_locked_DtIni";WritePhysical(before,tag,"before",states);
      Require(!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Initial predictor history unexpectedly exists");
      bool caught=false;std::string message;try{ComputeStep_Sym();}catch(const std::exception& e){caught=true;message=e.what();}
      Require(caught&&message.find(which?"Dynamic requested step":"Dynamic current step")!=std::string::npos,"Actual first step did not reject through the intended guard");
      const auto after=Capture();Require(Same(before,after)&&TimeStep==0&&Nstep==0,"Rejected first step advanced a physical field or clock");
      Require(!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Actual ComputeSymplecticPre was reached before first-step rejection");
      Require(Arc&&Acec&&Rsigmac,"Actual first predictor force was not evaluated");double maxTheta=0;unsigned assigned=0;
      for(unsigned p=0;p<Np;p++){maxTheta=(std::max)(maxTheta,fabs(PoroThetac[p]));if(PorePressRatec[p]!=1234567)assigned++;}
      Require(maxTheta>.01&&assigned==Np,"Actual predictor/helper evidence is empty");WritePhysical(after,tag,"after",states);
      out<<Dimension<<','<<tag<<','<<Np<<','<<maxTheta<<','<<assigned<<",true,true,true\n";PosInteraction_Forces();count++;
    }
    return count;
  }
};
int main(int argc,char** argv){
  try{
    Require(argc==3&&std::string(argv[1])=="--out","Use --out NEW_DIRECTORY");const fs::path folder(argv[2]);Require(!fs::exists(folder),"Retained output protected");
    AppInfo.ConfigRunPaths(argv[0]);AppInfo.ConfigOutput(true,false,folder.string(),"data");AppInfo.LogInit((folder/"Run.out").string());
    std::ofstream scales(folder/"scales.csv"),layers(folder/"state_scales.csv"),domain(folder/"domain.csv"),requests(folder/"requests.csv"),first(folder/"first_step.csv"),states(folder/"first_step_states.csv");
    for(auto* f:{&scales,&layers,&domain,&requests,&first,&states})*f<<std::setprecision(17);
    scales<<"dimension,case,k,gravity_z,wave_actual_s,wave_reference_s,pore_actual_s,pore_reference_s,cu2max_reference,dmax_reference,positive_legacy_rho_poison_0ULP\n";
    layers<<"dimension,case,native_id,J,n,rho_t,cu2,D,RH_margin\n";domain<<"dimension,case,J_test,J_critical,k,expected_rejection,actual_rejection,wave_s,pore_s\n";
    requests<<"dimension,case,bound_s,reference_bound_s,current_locked_s,fixed_s,DtMin_s,expected_rejection,actual_rejection,selected_dt_s,physical_arrays_unchanged\n";
    first<<"dimension,case,native_ids,max_absolute_theta,assigned_native_rates,rejected,physical_arrays_0ULP,predictor_histories_absent\n";
    states<<"dimension,case,phase,native_id,x,y,z,vx,vy,vz,passive_rho,J,p,p0,sxx,sxy,sxz,syy,syz,szz,kplastic\n";
    unsigned scaleCount=0,domainCount=0,requestsCount=0,firstCount=0;
    for(unsigned dim:{2u,3u}){TimeGuard a(dim);scaleCount+=a.ScaleChecks(scales,layers);domainCount+=a.DomainChecks(domain);requestsCount+=a.RequestedChecks(requests);firstCount+=a.FirstStepChecks(first,states);}
    for(auto* f:{&scales,&layers,&domain,&requests,&first,&states}){f->flush();Require(bool(*f),"Timeguard diagnostic write failed");}
    std::ofstream done(folder/"complete.json");done<<"{\"passed\":true,\"scale_cases\":"<<scaleCount<<",\"domain_cases\":"<<domainCount<<",\"requested_step_cases\":"<<requestsCount<<",\"actual_first_step_rejections\":"<<firstCount<<",\"actual_scale_helper\":true,\"actual_DtVariable\":true,\"actual_ComputeStep_Sym_rejected_before_Pre\":true,\"physical_trajectory_completed\":false,\"new_production_hook\":false,\"physical_acceptance\":false}\n";done.flush();Require(bool(done),"Completion write failed");std::cout<<"Private P3 necessary timeguard component passed; no physical trajectory acceptance.\n";return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Timeguard fixture failed; preserve outputs\n";return 2;}
}
