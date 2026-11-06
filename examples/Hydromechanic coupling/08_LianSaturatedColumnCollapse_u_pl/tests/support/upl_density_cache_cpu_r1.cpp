// Actual CPU Pre/Corr entries on the retained observer geometry; manufactured stage tests only.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JArraysCpu.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "JException.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("UplDensityCacheCpu","r1","06-11-2026");
namespace fs=std::filesystem;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
template<class T>struct Copy{
  T*& p;std::vector<T> data;
  Copy(T*& a,unsigned n):p(a){if(a)data.assign(a,a+n);}
  void Restore(){if(!data.empty()){Need(p!=nullptr,"Restore target absent");std::copy(data.begin(),data.end(),p);}}
};
class Probe:public JSphCpuSingle{
  unsigned soil=~0u,wall=~0u,preCalls=0,corrCalls=0,rejections=0,cacheChecks=0,rangeChecks=0;
  bool Feedback;
  float InputLegacyW=0;
  static constexpr double Dt=.125; // Manufactured arithmetic interval, NOT a stable physical time step.
  template<class T>static void Append(std::vector<char>& b,const T& a){const char* p=reinterpret_cast<const char*>(&a);b.insert(b.end(),p,p+sizeof(T));}
  std::vector<char> PhysicalBytes()const{
    std::vector<unsigned> order(7060,~0u);for(unsigned q=0;q<Np;q++){Need(Idpc[q]<7060&&order[Idpc[q]]==~0u,"Duplicate/unknown ID");order[Idpc[q]]=q;}
    std::vector<char> b;Append(b,Np);Append(b,Npb);Append(b,PorosityObserver);
    for(unsigned id=0;id<7060;id++){const unsigned q=order[id];Need(q!=~0u,"Missing original ID");Append(b,id);Append(b,Codec[q]);Append(b,Dcellc[q]);Append(b,Posc[q]);Append(b,Velrhopc[q]);Append(b,Sigmac[q]);Append(b,Kplasticc[q]);Append(b,PorePressc[q]);Append(b,PorePress0c[q]);Append(b,PorePressRatec[q]);if(PorosityObserver){Append(b,PoroJc[q]);Append(b,PoroThetac[q]);}Append(b,CorrMatc[q]);Append(b,FSTypec[q]);Append(b,FSNormalc[q]);Append(b,PosDivc[q]);Append(b,HydroMechLoadAcec[q]);Append(b,BoundNormalc[q]);Append(b,TangenVelc[q]);Append(b,BoundModec[q]);Append(b,BoundSlipModec[q]);}
    return b;
  }
  template<class T>void DropPre(T*& current,T*& previous){if(previous){ArraysCpu->Free(current);current=previous;previous=nullptr;}}
  void RecoverPre(){ // Expected J exceptions occur before mov allocation, or after its normal free.
    DropPre(Posc,PosPrec);DropPre(Velrhopc,VelrhopPrec);DropPre(Sigmac,SigmaPrec);DropPre(PorePressc,PorePressPrec);DropPre(PoroJc,PoroJPrec);
    Timersc->TmStop(TMC_SuComputeStep);
  }
  void NoPending()const{Need(!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec&&!Acec&&!Arc&&!Rsigmac&&TimeStep==0&&Nstep==0,"Stage buffers/scratch/time not restored");}
  void Scratch(bool corrector,double theta,bool poisonArc){
    PorosityFeedback=false;InterStep=(corrector?INTERSTEP_SymCorrector:INTERSTEP_SymPredictor);PreInteraction_Forces();
    Need(Arc&&Acec&&Rsigmac&&!BoundDerivativeVelc,"Unexpected ordinary observer scratch");
    for(unsigned q=0;q<Np;q++){const bool fluid=q>=Npb&&CODE_IsFluid(Codec[q]);Arc[q]=(fluid?(poisonArc?std::numeric_limits<float>::quiet_NaN():32.f):16.f);Acec[q]=TFloat3(-Gravity.x,-Gravity.y,-Gravity.z);Rsigmac[q]=tsymatrix3f{};PorePressRatec[q]=16.f;if(PorosityObserver)PoroThetac[q]=(fluid?theta:0.);}
    PorosityFeedback=Feedback;
  }
  void CheckCache() {
    const double solid=1.-double(SoilCte.Porosity),rw=SoilCte.PoreWaterRho;
    for(unsigned q=Npb;q<Np;q++)if(CODE_IsFluid(Codec[q])){const double j=PoroJc[q],rho=rw+(double(RhopZero)-rw)/j;const float expected=float(rho);Need(std::isfinite(j)&&j>solid&&std::isfinite(rho)&&rho>0&&!memcmp(&expected,&Velrhopc[q].w,sizeof(float)),"Cache differs from actual committed stage J");cacheChecks++;}
  }
  void Row(std::ostream& out,const std::string& test,const char* phase,const char* result,double preview=0){
    const double rho=(PoroJc?double(SoilCte.PoreWaterRho)+(double(RhopZero)-double(SoilCte.PoreWaterRho))/PoroJc[soil]:0.);
    out<<test<<','<<phase<<','<<result<<','<<Idpc[soil]<<','<<unsigned(Codec[soil])<<','<<(PoroJPrec?PoroJPrec[soil]:0)<<','<<(PoroJc?PoroJc[soil]:0)<<','<<(PoroThetac?PoroThetac[soil]:0)<<','<<preview<<','<<InputLegacyW<<','<<rho<<','<<Velrhopc[soil].w<<','<<Idpc[wall]<<','<<Velrhopc[wall].w<<','<<RhopOutMin<<','<<RhopOutMax<<'\n';out.flush();Need(bool(out),"Stage CSV write failed");
  }
  void Dump(const fs::path& out,const char* phase)const{const auto b=PhysicalBytes();std::ofstream f(out/(std::string(phase)+".bin"),std::ios::binary);f.write(b.data(),std::streamsize(b.size()));f.flush();Need(bool(f),"Stage byte export failed");}
public:
  Probe(bool observer,bool feedback):Feedback(feedback){PorosityObserver=observer;}
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Need(HydroMech&&Simulate2D&&TStep==STEP_Symplectic&&TKernel==KERNEL_Cubic&&!PeriActive&&Np==7060&&Npb==2060&&TimeMax==0&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&!StrainSoftening&&!WithFloating&&!InOut&&!Shifting&&!NoPenetration&&TMdbc2!=MDBC2_NoPen,"Retained observer stage scope changed");
    Need(RhopZero==2072.5f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.Porosity==.35f&&RhopOutMin==700&&RhopOutMax==3000&&!HydroMechDrainage&&!HourglassCpu,"Material/range/scope changed");
    Need((PorosityObserver&&PoroJc&&PoroThetac)||(!PorosityObserver&&!PoroJc&&!PoroThetac),"Observer allocation mismatch");
    for(unsigned q=0;q<Np;q++){if(Idpc[q]==2060)soil=q;if(Idpc[q]==0)wall=q;}Need(soil>=Npb&&wall<Npb,"Native witness IDs absent");NoPending();
    const auto original=PhysicalBytes();std::array<unsigned char,sizeof(SoilCte)> material;memcpy(material.data(),&SoilCte,sizeof(SoilCte));const auto oldInter=InterStep;const float oldMin=RhopOutMin,oldMax=RhopOutMax;const double oldSpeed=DynamicConductivitySpeedMax,oldVel=VelMax;const float oldVisc=ViscDtMax;
    Copy pos(Posc,Np);Copy vr(Velrhopc,Np);Copy sigma(Sigmac,Np);Copy kp(Kplasticc,Np);Copy code(Codec,Np);Copy cell(Dcellc,Np);Copy p(PorePressc,Np);Copy p0(PorePress0c,Np);Copy pr(PorePressRatec,Np);Copy j(PoroJc,Np);Copy theta(PoroThetac,Np);
    auto restore=[&](){PorosityFeedback=false;RecoverPre();if(Acec||Arc||Rsigmac)PosInteraction_Forces();pos.Restore();vr.Restore();sigma.Restore();kp.Restore();code.Restore();cell.Restore();p.Restore();p0.Restore();pr.Restore();j.Restore();theta.Restore();RhopOutMin=oldMin;RhopOutMax=oldMax;InterStep=oldInter;DynamicConductivitySpeedMax=oldSpeed;VelMax=oldVel;ViscDtMax=oldVisc;NoPending();Need(PhysicalBytes()==original&&!memcmp(material.data(),&SoilCte,sizeof(SoilCte)),"Original state/material not restored after actual stage/exception");};
    auto initial=[&](double jn,bool moving){restore();for(unsigned q=0;q<Np;q++){const bool fluid=q>=Npb&&CODE_IsFluid(Codec[q]);Velrhopc[q]=TFloat4(moving&&fluid?1.f/1024:0,0,moving&&fluid?-1.f/2048:0,RhopZero);Sigmac[q]=tsymatrix3d{};Kplasticc[q]=0;PorePressc[q]=128;PorePress0c[q]=0;PorePressRatec[q]=0;if(PorosityObserver){PoroJc[q]=1;PoroThetac[q]=0;}}if(PorosityObserver)PoroJc[soil]=jn;InputLegacyW=Velrhopc[soil].w;};
    std::ofstream csv(fs::path(cfg->DirOut)/"stages.csv");csv<<std::setprecision(17)<<"test,phase,result,native_id,CODE,Jn,current_J,theta,preview_Jfull,input_legacy_w,physical_rho_double,native_w,wall_id,wall_w,range_min,range_max\n";
    std::ofstream rejected(fs::path(cfg->DirOut)/"rejections.txt");Need(bool(rejected),"Cannot open actual checkpoint log");
    auto pre=[&](double t,bool poison){InputLegacyW=Velrhopc[soil].w;Scratch(false,t,poison);preCalls++;ComputeSymplecticPre(Dt);};
    auto corr=[&](double t,bool poison){PorosityFeedback=false;PosInteraction_Forces();Scratch(true,t,poison);corrCalls++;ComputeSymplecticCorr(Dt);};
    try{
      if(!Feedback){
        initial(1.,true);const float wall0=Velrhopc[wall].w;pre(.125,false);const float whalf=Velrhopc[wall].w;Need(whalf==std::max(RhopZero,float(double(wall0)+Dt*.5*16.)),"Legacy boundary predictor changed");Row(csv,"legacy","pre","completed");Dump(cfg->DirOut,"pre");
        corr(-.25,false);const double e=(-16./double(whalf))*Dt;Need(Velrhopc[wall].w==std::max(RhopZero,float(double(wall0)*(2.-e)/(2.+e))),"Legacy boundary corrector changed");Row(csv,"legacy","full","completed");Dump(cfg->DirOut,"full");restore();
      }else{
        for(unsigned test=0;test<2;test++){
          initial(test?.75:.68,false);Velrhopc[soil].w=float(double(RhopZero)/.68);const float wall0=Velrhopc[wall].w;pre(test?-1.5:0.,true);const double half=PoroJc[soil];const float whalf=Velrhopc[wall].w;CheckCache();Need(CODE_IsNormal(Codec[soil])&&Velrhopc[soil].w<3000&&float(double(RhopZero)/.68)>3000,"Valid-J/legacy-outside witness was excluded");Need(whalf==std::max(RhopZero,float(double(wall0)+Dt*.5*16.)),"Feedback changed boundary predictor");Row(csv,test?"changing_J":"J_0p68","pre","completed");
          const double rate=(test?.125:0.);double preview=PoroJPrec[soil];preview+=Dt*half*rate;corr(rate,true);CheckCache();Need(!memcmp(&preview,PoroJc+soil,sizeof(double)),"Corrector preview and real full-J commit differ");const double e=(-16./double(whalf))*Dt;Need(Velrhopc[wall].w==std::max(RhopZero,float(double(wall0)*(2.-e)/(2.+e))),"Feedback changed boundary corrector");Row(csv,test?"changing_J":"J_0p68","full","completed",preview);restore();
        }
        for(unsigned test=0;test<4;test++){
          initial(1.,false);RhopOutMin=1800;RhopOutMax=2400;const bool full=test>=2;pre(full?0.:(test?-4.:8.),true);if(full)corr(test==2?-2.:4.,true);CheckCache();Need(CODE_IsOutRhop(Codec[soil]),"Fixture physical-density range failure was not tagged");rangeChecks++;Row(csv,"fixture_range_"+std::to_string(test),full?"full":"pre","out_rhop");restore();
        }
        for(unsigned full=0;full<2;full++)for(unsigned bad=0;bad<3;bad++){
          initial(1.,false);const double solid=1.-double(SoilCte.Porosity);if(full){pre(0.,true);PorosityFeedback=false;PosInteraction_Forces();Scratch(true,0.,true);PoroThetac[soil]=(bad==0?std::numeric_limits<double>::quiet_NaN():(bad==1?std::numeric_limits<double>::infinity():(solid-1.)/Dt));}
          else{PoroJc[soil]=(bad==0?std::numeric_limits<double>::quiet_NaN():(bad==1?std::numeric_limits<double>::infinity():solid));Scratch(false,0.,true);}
          std::string error;try{if(full){corrCalls++;ComputeSymplecticCorr(Dt);}else{preCalls++;ComputeSymplecticPre(Dt);}}catch(const JException& e){error=e.ToStr();}catch(const std::exception& e){error=e.what();}
          rejected<<(full?"corrector":"predictor")<<" badJ="<<bad<<'\n'<<error<<'\n';rejected.flush();Need(bool(rejected),"Actual checkpoint log write failed");const bool expected=error.find(full?"finite saturated elastic":"saturated incompressible-grain")!=std::string::npos;Row(csv,"bad_J_"+std::to_string(bad),full?"full":"pre",expected?"expected_rejection":"unexpected_checkpoint");Need(expected,"Original invalid-J checkpoint not observed");rejections++;restore();
        }
      }
      Need(Feedback?(preCalls==12&&corrCalls==7&&cacheChecks==40000&&rangeChecks==4&&rejections==6):(preCalls==1&&corrCalls==1&&!cacheChecks&&!rangeChecks&&!rejections),"Actual stage/check count changed");restore();
    }catch(...){restore();throw;}
    csv.flush();Need(bool(csv),"Stage CSV final write failed");std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<"{\"stage\":\"upl_density_cache_cpu_r1\",\"passed\":true,\"feedback\":"<<(Feedback?"true":"false")<<",\"observer\":"<<(PorosityObserver?"true":"false")<<",\"native_ids\":7060,\"actual_Pre_calls\":"<<preCalls<<",\"actual_Corr_calls\":"<<corrCalls<<",\"cache_checks\":"<<cacheChecks<<",\"custom_range_rejections\":"<<rangeChecks<<",\"invalid_J_rejections\":"<<rejections<<",\"all_original_state_restored\":true,\"Pre_and_scratch_pointers_released\":true,\"global_TimeStep_and_Nstep_unadvanced\":true,\"manufactured_dt_is_not_stability_evidence\":true,\"native_Arc_NaN_is_field_lifecycle_only\":true,\"old_new_OFF_bits_compared_by_this_program\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=3,"Use --feedback|--observer|--off -cpu -ompthreads:1 -stable -mdbc_freeslip SAME_OBSERVER_SEED FRESH_OUT");const std::string mode=argv[1];Need(mode=="--feedback"||mode=="--observer"||mode=="--off","Unknown stage mode");AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=2;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&cfg.Stable&&!cfg.PrintInfo&&!cfg.PartBegin&&!fs::exists(cfg.DirOut),"Require fresh stable CPU component output");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe(mode!="--off",mode=="--feedback");probe.Execute(&cfg,AppInfo.LogPtr());return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Actual density stage failed; preserve output\n";return 2;}}
