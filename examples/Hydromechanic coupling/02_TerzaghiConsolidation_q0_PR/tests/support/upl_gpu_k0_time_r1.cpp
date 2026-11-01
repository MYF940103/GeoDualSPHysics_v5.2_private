// Private GPU k=0 necessary time-policy components. No completed physical step.
// Three modes are separate owned processes: Scale, FirstCurrent, FirstRequested.
#include "JSphGpuSingle.h"
#include "JSphCfgRun.h"
#include "JSphGpu_ker.h"
#include "JAppInfo.h"
#include "JCellDivGpuSingle.h"
#include "JDsFixedDt.h"
#include "JDsTimersGpu.h"
#include "JLog2.h"
#include <cuda_runtime_api.h>
#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("GpuK0TimeComponent","r1","02-11-2026");
namespace fs=std::filesystem;
static void Need(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
static void Cu(cudaError_t e){Need(e==cudaSuccess,cudaGetErrorString(e));}
template<class T>static std::vector<T> Down(const T* p,unsigned n){
  Need(p!=nullptr,"Missing actual device array");std::vector<T> v(n);
  if(n)Cu(cudaMemcpy(v.data(),p,sizeof(T)*n,cudaMemcpyDeviceToHost));return v;
}
template<class T>static void Up(T* p,const std::vector<T>& v){
  Need(p!=nullptr,"Missing upload device array");if(!v.empty())Cu(cudaMemcpy(p,v.data(),sizeof(T)*v.size(),cudaMemcpyHostToDevice));
}
template<class T>static bool Bits(const T& a,const T& b){return !memcmp(&a,&b,sizeof(T));}
template<class T>static bool Same(const std::vector<T>& a,const std::vector<T>& b){return a.size()==b.size()&&(a.empty()||!memcmp(a.data(),b.data(),sizeof(T)*a.size()));}
static bool Close(double a,double b){return std::isfinite(a)&&std::isfinite(b)&&fabs(a-b)<=64.*DBL_EPSILON*(std::max)(1.,fabs(b));}
template<class T>struct Device{
  T* p=nullptr;explicit Device(unsigned n){Cu(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*n));}
  ~Device(){if(p)cudaFree(p);}Device(const Device&)=delete;Device& operator=(const Device&)=delete;
};
struct Counts{unsigned kernel=0,scale=0,domain=0,request=0,init=0,first=0;};
class TimeFixture:public JSphGpuSingle{
  struct Physical{
    std::vector<unsigned> id;std::vector<typecode> code;std::vector<double2> xy;
    std::vector<double> z,j;std::vector<float4> vr;std::vector<float> p,p0,plastic;
    std::vector<tsymatrix3d> sigma;
  };
  Physical seed;
  Physical Capture()const{return {Down(Idpg,Np),Down(Codeg,Np),Down(Posxyg,Np),Down(Poszg,Np),Down(PoroJg,Np),Down(Velrhopg,Np),Down(PorePressg,Np),Down(PorePress0g,Np),Down(Kplasticg,Np),Down(Sigmag,Np)};}
  static bool SamePhysical(const Physical& a,const Physical& b){
    return Same(a.id,b.id)&&Same(a.code,b.code)&&Same(a.xy,b.xy)&&Same(a.z,b.z)&&Same(a.j,b.j)&&Same(a.vr,b.vr)&&Same(a.p,b.p)&&Same(a.p0,b.p0)&&Same(a.plastic,b.plastic)&&Same(a.sigma,b.sigma);
  }
  void RestoreSeed(){
    Up(Idpg,seed.id);Up(Codeg,seed.code);Up(Posxyg,seed.xy);Up(Poszg,seed.z);Up(PoroJg,seed.j);Up(Velrhopg,seed.vr);
    Up(PorePressg,seed.p);Up(PorePress0g,seed.p0);Up(Kplasticg,seed.plastic);Up(Sigmag,seed.sigma);
  }
  unsigned NativeCount(const Physical& a)const{
    std::map<unsigned,unsigned> ids;unsigned periodic=0;
    for(unsigned p=0;p<Np;p++){
      Need(a.id[p]<512&&CODE_IsFluid(a.code[p]),"Unexpected identity/type");
      if(CODE_IsNormal(a.code[p]))Need(ids.emplace(a.id[p],p).second,"Duplicate native ID");
      else {Need(CODE_IsPeriodic(a.code[p]),"Excluded or abnormal real particle");periodic++;}
    }
    Need(ids.size()==512&&periodic>0&&Npb==0&&CellDivSingle->GetNpfOut()==0,"Native/periodic/exclusion evidence changed");return unsigned(ids.size());
  }
  void SetFixed(double dt){delete FixedDt;FixedDt=dt>0?new JDsFixedDt(dt):nullptr;}
  void SetStats(){AceMax=0.;VelMax=.125;ViscDtMax=.5f;CFLnumber=.2;DtMin=0.;DtModif=0;SymplecticDtPre=1e-12;TimeStep=0.;Nstep=0;SetFixed(0.);}
  double M()const{return double(SoilCte.ModulusK)+4.*double(SoilCte.ModulusG)/3.;}
  double Cu2(double j,bool constituent)const{
    const double n0=SoilCte.Porosity,rho0=RhopZero,rhow=SoilCte.PoreWaterRho,kw=SoilCte.PoreWaterBulkModulus;
    const double n=1.-(1.-n0)/j,rhos=(rho0-n0*rhow)/(1.-n0);
    const double rho=constituent?(1.-n)*rhos+n*rhow:rhow+(rho0-rhow)/j;
    return (M()+kw/n)/rho;
  }
  double MaxCu2(bool constituent)const{
    const auto j=Down(PoroJg,Np);const auto code=Down(Codeg,Np);double result=0.;
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(code[p])&&CODE_IsFluid(code[p]))result=(std::max)(result,Cu2(j[p],constituent));return result;
  }
  double ReferenceWave(bool constituent)const{return double(KernelH)/((std::max)(sqrt(MaxCu2(constituent)),10.*VelMax)+double(KernelH)*double(ViscDtMax));}
  double Bound() {return CFLnumber*(std::min)(AceMax?sqrt(double(KernelH)/AceMax):DBL_MAX,GetPorosityStepWaveGpu());}
  bool NoPre()const{return !PosxyPreg&&!PoszPreg&&!VelrhopPreg&&!SigmaPreg&&!PorePressPreg&&!PoroJPreg;}
  void WritePhysical(std::ostream& out,const char* phase,const Physical& a)const{
    for(unsigned p=0;p<Np;p++){
      const auto s=a.sigma[p];out<<phase<<','<<p<<','<<a.id[p]<<','<<unsigned(a.code[p])<<','<<a.xy[p].x<<','<<a.xy[p].y<<','<<a.z[p]
        <<','<<a.vr[p].x<<','<<a.vr[p].y<<','<<a.vr[p].z<<','<<a.vr[p].w<<','<<a.j[p]<<','<<a.p[p]<<','<<a.p0[p]
        <<','<<s.xx<<','<<s.xy<<','<<s.xz<<','<<s.yy<<','<<s.yz<<','<<s.zz<<','<<a.plastic[p]<<'\n';
    }
  }
  void Initialize(const JSphCfgRun* cfg,JLog2* log){
    PorosityObserver=PorosityFeedback=true;AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;
    SelecDevice(cfg->GpuId);Timersg->Config(false);Timersg->TmStart(TMG_Init,false);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunGpu();FreePartsInit();
    Need(HydroMech&&!HydroMechDynamicSeepage&&Simulate2D&&CaseNfluid==512&&!CaseNpb&&!CaseNfloat&&PeriX&&PeriZ&&!PeriY,"Only retained private k0 periodic512 seed admitted");
    Need(SoilCte.HydraulicConductivity==0&&TStep==STEP_Symplectic&&TimeStep==0.&&Nstep==0&&NoPre(),"Not a fresh private k0 initialization");
    seed=Capture();NativeCount(seed);for(unsigned p=0;p<Np;p++)Need(seed.j[p]==1.,"Fresh J is not exactly one");
    // No force maxima are read here: the real first Interaction_Forces creates them.
  }
  void KernelChecks(const fs::path& folder,Counts& count){
    constexpr unsigned cap=514;Device<typecode> codes(cap);Device<double> jg(cap),maximum(2);Device<unsigned> invalid(2);
    std::ofstream rows(folder/"kernel.csv");rows<<std::setprecision(17)<<"case,np,npb,native_valid,expected_invalid,actual_invalid,maxcu2_actual,maxcu2_production_expression,maxcu2_constituent_reference,production_max_bits_exact,input_arrays_exact,output_tail_exact\n";
    const char* labels[]={"empty","one","127","128","129","257","513","prefix_and_ghost_poison","all_non_native","bad_native_min_index","nextafter_solid_legal","huge_J_rounds_n_to_one"};
    const unsigned sizes[]={0,1,127,128,129,257,513,257,129,513,129,129};
    for(unsigned trial=0;trial<12;trial++){
      const unsigned np=sizes[trial],npb=trial==7?2:0;std::vector<typecode> code(cap,CODE_TYPE_FLUID);std::vector<double> j(cap,1.);
      for(unsigned p=0;p<np;p++)j[p]=.9375+double(p%5)/32.;
      if(trial==7){code[2]=CODE_SetPeriodic(CODE_TYPE_FLUID);code[3]=CODE_SetOutIgnore(CODE_TYPE_FLUID);code[4]=CODE_TYPE_FIXED;code[5]=CODE_TYPE_FLOATING;j[0]=j[1]=j[2]=j[3]=j[4]=j[5]=std::numeric_limits<double>::quiet_NaN();}
      if(trial==8)for(unsigned p=0;p<np;p++){code[p]=CODE_SetPeriodic(CODE_TYPE_FLUID);j[p]=std::numeric_limits<double>::infinity();}
      if(trial==9){j[4]=1.-double(SoilCte.Porosity);j[300]=std::numeric_limits<double>::quiet_NaN();j[400]=std::numeric_limits<double>::infinity();}
      if(trial==10)j[7]=std::nextafter(1.-double(SoilCte.Porosity),DBL_MAX);
      if(trial==11)j[7]=DBL_MAX;
      unsigned expectedInvalid=np,valid=0;double expected=0.,reference=0.;
      for(unsigned p=npb;p<np;p++)if(CODE_IsNormal(code[p])&&CODE_IsFluid(code[p])){
        const double n=1.-(1.-double(SoilCte.Porosity))/j[p],rho=double(SoilCte.PoreWaterRho)+(double(RhopZero)-double(SoilCte.PoreWaterRho))/j[p];
        const double value=Cu2(j[p],false);
        if(!std::isfinite(j[p])||!(j[p]>1.-double(SoilCte.Porosity))||!std::isfinite(n)||!(n>0&&n<1)||!std::isfinite(rho)||!(rho>0)||!std::isfinite(value)||!(value>0))expectedInvalid=(std::min)(expectedInvalid,p);
        else {valid++;expected=(std::max)(expected,value);reference=(std::max)(reference,Cu2(j[p],true));}
      }
      Up(codes.p,code);Up(jg.p,j);Up(maximum.p,std::vector<double>{0.,-123.25});Up(invalid.p,std::vector<unsigned>{np,0x1234abcd});
      cusph::ComputePorosityWaveSpeed2(np,npb,1.-double(SoilCte.Porosity),double(RhopZero),double(SoilCte.PoreWaterRho),M(),double(SoilCte.PoreWaterBulkModulus),codes.p,jg.p,maximum.p,invalid.p);
      Cu(cudaDeviceSynchronize());Cu(cudaGetLastError());const auto got=Down(maximum.p,2);const auto bad=Down(invalid.p,2);
      Need(bad[0]==expectedInvalid&&Bits(got[0],expected)&&Close(got[0],reference),"Actual native reduction disagrees with independent domain/max reference");
      Need(got[1]==-123.25&&bad[1]==0x1234abcd&&Same(code,Down(codes.p,cap))&&Same(j,Down(jg.p,cap)),"Reduction changed its inputs or output tail");
      rows<<labels[trial]<<','<<np<<','<<npb<<','<<valid<<','<<expectedInvalid<<','<<bad[0]<<','<<got[0]<<','<<expected<<','<<reference<<",true,true,true\n";count.kernel++;
    }
    rows.flush();Need(bool(rows),"Kernel CSV failed");
  }
  void ScaleChecks(const fs::path& folder,Counts& count){
    std::ofstream rows(folder/"scales.csv"),nodes(folder/"scale_nodes.csv");rows<<std::setprecision(17);nodes<<std::setprecision(17);
    rows<<"case,wave_actual_s,wave_production_reference_s,wave_constituent_reference_s,maxcu2,positive_legacy_rho_or_ghost_poison_bits_exact\n";
    nodes<<"slot,native_id,normal,J,n,rho_compact,rho_constituents,cu2\n";
    RestoreSeed();SetStats();auto j=seed.j;for(unsigned p=0;p<Np;p++)j[p]=.9375+double(seed.id[p]%5)/32.;Up(PoroJg,j);
    double baseline=0.;for(unsigned trial=0;trial<4;trial++){
      const char* labels[]={"current_J","positive_legacy_rho_poison","non_native_J_poison","velocity_dominated"};
      if(trial==1){auto vr=seed.vr;for(unsigned p=0;p<Np;p++)vr[p].w=1000.f+float(seed.id[p]%31);Up(Velrhopg,vr);}
      if(trial==2){for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(seed.code[p]))j[p]=std::numeric_limits<double>::quiet_NaN();Up(PoroJg,j);}
      if(trial==3)VelMax=1024.;const double actual=GetPorosityStepWaveGpu(),direct=ReferenceWave(false),reference=ReferenceWave(true);
      Need(Bits(actual,direct)&&Close(actual,reference),"Actual class wave scale differs from current-J reference");
      if(!trial)baseline=actual;if(trial==1||trial==2)Need(Bits(actual,baseline),"Positive old-rho or non-native J changed acoustic bound");
      rows<<labels[trial]<<','<<actual<<','<<direct<<','<<reference<<','<<MaxCu2(false)<<",true\n";count.scale++;
    }
    Need(Same(j,Down(PoroJg,Np)),"Scale node CSV no longer describes the observed J state");
    for(unsigned p=0;p<Np;p++){
      const double n0=SoilCte.Porosity,n=1.-(1.-n0)/j[p],rhos=(double(RhopZero)-n0*SoilCte.PoreWaterRho)/(1.-n0);
      if(CODE_IsNormal(seed.code[p])){
        const double compact=double(SoilCte.PoreWaterRho)+(double(RhopZero)-double(SoilCte.PoreWaterRho))/j[p],constituents=(1.-n)*rhos+n*double(SoilCte.PoreWaterRho);
        Need(Close(compact,constituents),"Independent constituent inertia closure differs");nodes<<p<<','<<seed.id[p]<<",1,"<<j[p]<<','<<n<<','<<compact<<','<<constituents<<','<<Cu2(j[p],false)<<'\n';
      }
    }
    RestoreSeed();SetStats();rows.flush();nodes.flush();Need(bool(rows)&&bool(nodes),"Scale CSV failed");
  }
  void DomainChecks(const fs::path& folder,Counts& count){
    std::ofstream rows(folder/"domain.csv");rows<<"case,rejected,expected_message,predictor_histories_absent\n";
    unsigned native=0;while(native<Np&&!CODE_IsNormal(seed.code[native]))native++;Need(native<Np,"Native domain witness absent");
    const char* labels[]={"solid_limit","native_nan","native_inf","J_rounds_n_to_one","no_native","AceMax_nan","VelMax_inf","ViscDtMax_negative"};
    for(unsigned trial=0;trial<8;trial++){
      RestoreSeed();SetStats();auto j=seed.j;auto code=seed.code;
      if(trial<4){const double bad[]={1.-double(SoilCte.Porosity),std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),DBL_MAX};j[native]=bad[trial];Up(PoroJg,j);}
      if(trial==4){for(auto& c:code)c=CODE_SetPeriodic(c);Up(Codeg,code);}
      if(trial==5)AceMax=std::numeric_limits<double>::quiet_NaN();if(trial==6)VelMax=std::numeric_limits<double>::infinity();if(trial==7)ViscDtMax=-1.f;
      const auto before=Capture();bool caught=false;std::string message;
      try{GetPorosityStepWaveGpu();}catch(const std::exception& e){caught=true;message=e.what();}
      Need(caught&&message.find(trial>=5?"finite nonnegative force-stage maxima":"finite saturated native J")!=std::string::npos,"Unrelated or missing class domain rejection");
      Need(SamePhysical(before,Capture())&&NoPre(),"Rejected class scale changed physical state/PRE");rows<<labels[trial]<<",true,true,true\n";count.domain++;
    }
    RestoreSeed();SetStats();rows.flush();Need(bool(rows),"Domain CSV failed");
  }
  void RequestChecks(const fs::path& folder,Counts& count){
    std::ofstream rows(folder/"requests.csv");rows<<std::setprecision(17)<<"case,bound_s,constituent_reference_bound_s,current_locked_s,fixed_s,DtMin_s,expected_rejection,actual_rejection,selected_dt_s,signed_fixed_error_s,physical_arrays_exact,DtModif\n";
    const char* labels[]={"variable_safe","fixed_safe","fixed_at_bound","locked_at_bound","locked_nextafter_above","fixed_nextafter_above","DtMin_nextafter_above","DtMin_above_fixed","force_dominated","velocity_dominated","current_zero","current_nan"};
    for(unsigned trial=0;trial<12;trial++){
      RestoreSeed();SetStats();if(trial==8)AceMax=1e12;if(trial==9)VelMax=1024.;
      const double bound=Bound(),reference=CFLnumber*(std::min)(AceMax?sqrt(double(KernelH)/AceMax):DBL_MAX,ReferenceWave(true));Need(Close(bound,reference),"Necessary combined bound differs from independent reference");
      SymplecticDtPre=bound*.25;double expected=bound;bool reject=false;
      if(trial==1){SetFixed(bound*.75);DtMin=bound*.5;expected=bound*.75;}
      if(trial==2)SetFixed(bound);if(trial==3)SymplecticDtPre=bound;
      if(trial==4){SymplecticDtPre=std::nextafter(bound,DBL_MAX);reject=true;}
      if(trial==5){SetFixed(std::nextafter(bound,DBL_MAX));reject=true;}
      if(trial==6){DtMin=std::nextafter(bound,DBL_MAX);reject=true;}
      if(trial==7){DtMin=bound*.75;SetFixed(bound*.5);reject=true;}
      if(trial==10){SymplecticDtPre=0.;reject=true;}if(trial==11){SymplecticDtPre=std::numeric_limits<double>::quiet_NaN();reject=true;}
      const auto before=Capture();const double locked=SymplecticDtPre,minimum=DtMin,fixed=FixedDt?FixedDt->GetFixedValue():0.;bool caught=false;std::string message;double selected=0.;
      try{selected=DtVariable(false);}catch(const std::exception& e){caught=true;message=e.what();}
      Need(caught==reject,"Requested step did not follow exact/nextafter contract");
      if(caught)Need(message.find(trial==5||trial==7?"GPU porosity requested step":"GPU porosity current step")!=std::string::npos,"Unrelated requested-step exception");
      else Need(Bits(selected,expected)&&selected<=bound&&selected>=DtMin,"Accepted request was clipped/uplifted or selected incorrectly");
      const double error=FixedDt?FixedDt->GetDtError(false):0.;if(FixedDt)Need(Bits(error,fixed-bound),"FixedDt did not receive full necessary bound");
      Need(DtModif==0&&SamePhysical(before,Capture())&&NoPre(),"DtVariable changed physical state or uplifted DtMin");
      rows<<labels[trial]<<','<<bound<<','<<reference<<','<<locked<<','<<fixed<<','<<minimum<<','<<reject<<','<<caught<<','<<selected<<','<<error<<",true,"<<DtModif<<'\n';count.request++;
    }
    RestoreSeed();SetStats();rows.flush();Need(bool(rows),"Request CSV failed");
  }
  void InitChecks(const fs::path& folder,Counts& count){
    std::ofstream rows(folder/"init_negatives.csv");rows<<"case,rejected,guard_family,physical_arrays_exact\n";
    const auto soil=SoilCte;const float rho=RhopZero,mass=MassFluid,h=KernelH;const double cfl=CFLnumber,minimum=DtMin;const bool px=PeriX,pz=PeriZ;const unsigned floating=CaseNfloat;
    const char* labels[]={"Kw_inf","rhow_inf","rho0_inf","K_inf","G_inf","h_inf","CFL_inf","DtMin_inf","mass_inf","PeriX_missing","PeriZ_missing","floating_present","k_positive","CFL_nan","DtMin_nan","DtMin_negative","K_zero","G_negative"};
    for(unsigned trial=0;trial<18;trial++){
      SoilCte=soil;RhopZero=rho;MassFluid=mass;KernelH=h;CFLnumber=cfl;DtMin=minimum;PeriX=px;PeriZ=pz;CaseNfloat=floating;
      const float inf=std::numeric_limits<float>::infinity();
      switch(trial){case 0:SoilCte.PoreWaterBulkModulus=inf;break;case 1:SoilCte.PoreWaterRho=inf;break;case 2:RhopZero=inf;break;case 3:SoilCte.ModulusK=inf;break;case 4:SoilCte.ModulusG=inf;break;case 5:KernelH=inf;break;case 6:CFLnumber=std::numeric_limits<double>::infinity();break;case 7:DtMin=std::numeric_limits<double>::infinity();break;case 8:MassFluid=inf;break;case 9:PeriX=false;break;case 10:PeriZ=false;break;case 11:CaseNfloat=1;break;case 12:SoilCte.HydraulicConductivity=1e-5f;break;case 13:CFLnumber=std::numeric_limits<double>::quiet_NaN();break;case 14:DtMin=std::numeric_limits<double>::quiet_NaN();break;case 15:DtMin=-1.;break;case 16:SoilCte.ModulusK=0.;break;case 17:SoilCte.ModulusG=-1.f;break;}
      const auto before=Capture();bool caught=false;std::string message;try{InitPorosityObserverGpu();}catch(const std::exception& e){caught=true;message=e.what();}
      SoilCte=soil;RhopZero=rho;MassFluid=mass;KernelH=h;CFLnumber=cfl;DtMin=minimum;PeriX=px;PeriZ=pz;CaseNfloat=floating;
      const bool privateGuard=trial==1||trial==12;Need(caught&&message.find(privateGuard?"GPU porosity feedback requires a private k=0":"GPU porosity feedback requires finite saturated elastic")!=std::string::npos,"Missing or unrelated actual initialization-hook rejection");
      Need(SamePhysical(before,Capture())&&NoPre(),"Rejected initialization hook changed physical state/PRE");rows<<labels[trial]<<",true,"<<(privateGuard?"private_k0":"finite_material_step_scope")<<",true\n";count.init++;
    }
    rows.flush();Need(bool(rows),"Initialization negative CSV failed");
  }
  void FirstCheck(const fs::path& folder,bool request,Counts& count){
    Need(NoPre()&&TimeStep==0.&&Nstep==0,"Actual first step not fresh");
    const double safe=std::ldexp(1.,-24);SymplecticDtPre=request?safe:1.;SetFixed(request?1.:safe);DtMin=0.;DtModif=0;
    Up(PorePressRateg,std::vector<float>(Np,1234567.f));const auto before=Capture();const unsigned natives=NativeCount(before);
    bool caught=false;std::string message;try{ComputeStep_Sym();}catch(const std::exception& e){caught=true;message=e.what();}
    Need(caught&&message.find(request?"GPU porosity requested step":"GPU porosity current step")!=std::string::npos,"Actual first ComputeStep_Sym missed intended guard");
    const auto after=Capture();Need(SamePhysical(before,after)&&NoPre()&&TimeStep==0.&&Nstep==0&&DtModif==0,"Rejected first step advanced physical state/clock or reached PRE");
    Need(Arg&&Aceg&&Rsigmag&&std::isfinite(AceMax)&&std::isfinite(VelMax)&&std::isfinite(ViscDtMax),"Real initial predictor force did not finish");
    const auto theta=Down(PoroThetag,Np);const auto rate=Down(PorePressRateg,Np);double maxTheta=0.,maxRate=0.;unsigned assigned=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(after.code[p])){maxTheta=(std::max)(maxTheta,fabs(theta[p]));maxRate=(std::max)(maxRate,fabs(double(rate[p])));if(rate[p]!=1234567.f)assigned++;}
    Need(maxTheta>1e-5&&maxRate>1.&&assigned==natives,"Real predictor theta/compression-rate evidence is empty");
    const double bound=Bound();Need(SymplecticDtPre==(request?safe:1.)&&bound<1.&&(!request||safe<=bound),"Wrong initial current/requested witness");
    std::ofstream state(folder/"first_step_states.csv"),rows(folder/"first_step.csv");state<<std::setprecision(17);rows<<std::setprecision(17);
    state<<"phase,slot,native_id,code,x,y,z,vx,vy,vz,passive_rho,J,p,p0,sxx,sxy,sxz,syy,syz,szz,kplastic\n";WritePhysical(state,"before",before);WritePhysical(state,"after",after);
    rows<<"case,total_slots,native_ids,current_locked_s,fixed_s,actual_force_bound_s,AceMax_magnitude,VelMax,ViscDtMax,max_native_absolute_theta,max_native_absolute_pore_rate,assigned_native_rates,rejected,physical_arrays_exact,predictor_histories_absent,actual_time_s,Nstep\n"
      <<(request?"safe_current_unsafe_requested":"unsafe_current")<<','<<Np<<','<<natives<<','<<SymplecticDtPre<<','<<FixedDt->GetFixedValue()<<','<<bound<<','<<AceMax<<','<<VelMax<<','<<ViscDtMax<<','<<maxTheta<<','<<maxRate<<','<<assigned<<",true,true,true,"<<TimeStep<<','<<Nstep<<'\n';
    state.flush();rows.flush();Need(bool(state)&&bool(rows),"First-step CSV failed");PosInteraction_Forces();count.first++;
  }
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,const std::string& mode){
    Initialize(cfg,log);const fs::path out(cfg->DirOut);Counts count;
    if(mode=="Scale"){KernelChecks(out,count);ScaleChecks(out,count);DomainChecks(out,count);RequestChecks(out,count);InitChecks(out,count);}
    else FirstCheck(out,mode=="FirstRequested",count);
    Need(NoPre()&&TimeStep==0.&&Nstep==0,"Component completed a physical step or leaked PRE");
    int device=0;Cu(cudaGetDevice(&device));cudaDeviceProp props{};Cu(cudaGetDeviceProperties(&props,device));
    std::ofstream complete(out/"completion.json");complete<<std::setprecision(17)<<"{\"passed\":true,\"mode\":\""<<mode<<"\",\"native_count\":512,\"fixed_count\":0,\"kernel_cases\":"<<count.kernel
      <<",\"class_scale_cases\":"<<count.scale<<",\"class_domain_rejections\":"<<count.domain<<",\"requested_step_cases\":"<<count.request<<",\"initialization_hook_rejections\":"<<count.init<<",\"actual_first_step_rejections\":"<<count.first
      <<",\"actual_maxcu2_kernel\":"<<(mode=="Scale"?"true":"false")<<",\"actual_DtVariable\":true,\"first_force_precedes_rejection\":"<<(mode=="Scale"?"false":"true")
      <<",\"predictor_histories_absent\":true,\"completed_physical_steps\":0,\"actual_time_s\":"<<TimeStep<<",\"Nstep\":"<<Nstep<<",\"device_name\":\""<<props.name
      <<"\",\"public_GPU_dynamic_mode\":false,\"nonzero_k\":false,\"necessary_scale_not_sufficient_stability\":true,\"physical_acceptance\":false}\n";
    complete.flush();Need(bool(complete),"Time completion write failed");
  }
};
int main(int argc,char** argv){
  try{
    Need(argc>=7&&std::string(argv[1])=="--time","Use --time Scale|FirstCurrent|FirstRequested followed by ordinary -gpu input/output arguments");const std::string mode=argv[2];
    Need(mode=="Scale"||mode=="FirstCurrent"||mode=="FirstRequested","Unknown time component mode");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=3;i<argc;i++)args.push_back(argv[i]);
    JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(!cfg.Cpu&&!cfg.PrintInfo,"Only GPU component arguments admitted");Need(!fs::exists(cfg.DirOut),"Retained output protected");
    cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    TimeFixture fixture;fixture.Execute(&cfg,AppInfo.LogPtr(),mode);return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"GPU k0 time component rejected; preserve all evidence\n";return 2;}
}
