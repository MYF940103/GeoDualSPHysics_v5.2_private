// Manufactured same-stage band-load normalization only; no physical trajectory or integration.
#define main RetainedFluxLoadNativeMain
#include "upl_cpu_public_native_r1.cpp"
#undef main
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JDsFixedDt.h"
#include "JLog2.h"
#include "JException.h"
namespace loadstage {
constexpr unsigned Soil=1000,Fixed=40,Total=1040;
constexpr double Delta=1./256.,Clock=0.005,Area0=0.1;
struct Result {double loadratio=0,aceratio=0,wrongratio=0,ledger=0;unsigned band=0,top=0;};
class Audit:public JSphCpuSingle {
  std::vector<unsigned> Owners()const{
    std::vector<unsigned> a(Total,~0u);unsigned ns=0,nf=0;
    for(unsigned p=0;p<Np;p++){Need(Idpc[p]<Total&&(CODE_IsNormal(Codec[p])||CODE_IsPeriodic(Codec[p])),"Unexpected slot/ID/exclusion");if(CODE_IsNormal(Codec[p])){Need(a[Idpc[p]]==~0u,"Duplicate native ID");a[Idpc[p]]=p;if(Idpc[p]<Fixed){Need(CODE_IsFixed(Codec[p]),"Fixed type differs");nf++;}else{Need(CODE_IsFluid(Codec[p]),"Soil type differs");ns++;}}}
    Need(ns==Soil&&nf==Fixed&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Original1000soil40fixed native scope required");return a;
  }
  std::vector<byte> Physical(const std::vector<unsigned>& owner)const{
    std::vector<byte> b;auto add=[&](const auto& x){const auto p=reinterpret_cast<const byte*>(&x);b.insert(b.end(),p,p+sizeof(x));};
    for(unsigned id=Fixed;id<Total;id++){const unsigned p=owner[id];add(Idpc[p]);add(Codec[p]);add(Dcellc[p]);add(Posc[p]);add(Velrhopc[p]);add(Sigmac[p]);add(Kplasticc[p]);add(PorePressc[p]);add(PorePress0c[p]);add(PoroJc[p]);}return b;
  }
  static double Field(unsigned trial,double z){return trial<2?1.:(trial==2?1.+Delta:1.+Delta*(2.*z-1.));}
  static double Budget(double absolute,double target){return 64.*FLT_EPSILON*absolute+256.*DBL_EPSILON*(std::max)(1.,std::fabs(target))+1e-6;}
public:
  Audit(){PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;DynamicPoreConductivity=false;DynamicPoreConductivityCk=0.;}
  Result Execute(const JSphCfgRun* cfg,JLog2* log,unsigned trial,std::ofstream& rows,std::ofstream& summary){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();RunCellDivide(true);
    Need(HydroMech&&Simulate2D&&CaseNp==Total&&CaseNpb==Fixed&&CaseNfluid==Soil&&!PartBegin&&!CaseNmoving&&!CaseNfloat&&TStep==STEP_Symplectic&&TKernel==KERNEL_Wendland&&PeriX&&!PeriY&&!PeriZ&&PeriXinc.y==0&&PeriXinc.z==0&&std::fabs(std::fabs(PeriXinc.x)-.1)<=1e-14&&Gravity==TFloat3(0)&&CSP.gravity==Gravity&&OmpThreads==1,"Only original g0/X-periodic case02 scope");
    Need(!HydroMechDynamicSeepage&&HydroMechConductivityModel==0&&!DynamicPoreConductivity&&PorosityObserver&&PorosityFeedback&&DynamicPorePressure&&DynamicPoreWall&&TBoundary==BC_MDBC&&SlipMode==SLIP_FreeSlip&&HydroMechTopLoadMode==HMLOAD_TopKernelBand&&HydroMechTopLoadQ0==10000.f&&HydroMechTopLoadRampTime==.01&&HydroMechDrainage&&HydroMechDrainageStartTime==.01&&HydroMechDrainageFixedGrid,"Only the private constant-k loaded column");
    Need(JSph::Dp==.01&&KernelH==float(.018)&&RhopZero==2100.f&&MassFluid==float(.21)&&MassBound==MassFluid&&SoilCte.Porosity==float(.3)&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==2e8f&&SoilCte.HydraulicConductivity==float(.0001)&&SoilCte.ModulusK==1666666.75f&&SoilCte.ModulusG==769230.8125f&&PoreDtSafety==1,"Original float material required");
    Need(!HourglassCpu&&!Visco&&!SoilDamping&&!Damping&&!RelaxZones&&!Shifting&&!InOut&&!AccInput&&!NoPenetration&&!SoilBoundaryDerivativeSPR&&!ArtificialStress&&!PoreShepardRegularization&&TDensity==DDT_None&&!StrainSoftening&&PoreCompressionGradCorr&&!PoreCompressionSourceMode&&SoilStressRateGradCorr&&HydroMechInitMode==HMINIT_None,"Extra physics not admitted");
    Need(!TimeStep&&!Nstep&&FixedDt&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Init advanced time/history");
    const auto owner=Owners();const double locked=SymplecticDtPre,last=LastDt,error=FixedDt->GetDtError(false);const unsigned np=Np;
    for(unsigned id=Fixed;id<Total;id++){const unsigned p=owner[id];Need(PoroJc[p]==1&&PoroThetac[p]==0&&PorePressc[p]==0&&PorePress0c[p]==0&&Kplasticc[p]==0&&Velrhopc[p].x==0&&Velrhopc[p].y==0&&Velrhopc[p].z==0&&Velrhopc[p].w==RhopZero&&Sigmac[p].xx==0&&Sigmac[p].yy==0&&Sigmac[p].zz==0&&Sigmac[p].xy==0&&Sigmac[p].xz==0&&Sigmac[p].yz==0,"Original rest field differs");}
    // Explicit manufactured field on all actual fluid slots; X images have the same z. Not a periodic-copy claim.
    for(unsigned p=0;p<Np;p++)if(CODE_IsFluid(Codec[p])){PoroJc[p]=Field(trial,Posc[p].z);PoroThetac[p]=0;}
    const auto physical=Physical(owner);TimeStep=(trial?Clock:0.);const double clock=TimeStep;
    Need(!IsHydroMechDrainageActive(),"Manufactured clock must remain pre-open");
    Interaction_Forces(INTERSTEP_SymPredictor);
    Need(Np==np&&Physical(Owners())==physical&&TimeStep==clock&&!Nstep&&SymplecticDtPre==locked&&LastDt==last&&FixedDt->GetDtError(false)==error&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Force changed covered native inputs/clock/history");
    Need(Acec&&HydroMechLoadAcec&&HydroMechTopLoadRawc,"Finished force-stage arrays must be live");
    Result result;double zmax=-DBL_MAX;
    for(unsigned id=Fixed;id<Total;id++)zmax=(std::max)(zmax,Posc[owner[id]].z);
    const double q0=HydroMechTopLoadQ0,q=(HydroMechTopLoadRampTime>0&&clock<HydroMechTopLoadRampTime?q0*clock/HydroMechTopLoadRampTime:q0);
    const double por=SoilCte.Porosity,rhow=SoilCte.PoreWaterRho,rhos=(double(RhopZero)-por*rhow)/(1.-por),rhomix=(1.-por)*rhos+por*rhow;
    const float provisional=float(q/(rhomix*double(JSph::Dp)));double target=0,raw=0,force=0,load=0,wrong=0,absforce=0,absload=0,maxAceLoad=0;
    for(unsigned id=Fixed;id<Total;id++){const unsigned p=owner[id];const auto normal=FSNormalc[p];const double length=std::sqrt(double(normal.x)*normal.x+double(normal.y)*normal.y+double(normal.z)*normal.z);
      const bool top=(FSTypec[p]==FST_FreeSurface||FSTypec[p]==FST_Isolated)&&length>1e-12&&double(normal.z)/length>.35;
      const bool band=Posc[p].z>zmax-double(KernelSize);result.top+=unsigned(top);result.band+=unsigned(band);if(top)target-=double(MassFluid)*provisional;
      double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);const double mass=rho*V,mref=double(MassFluid)/RhopZero*(double(RhopZero)-rhow+rhow*PoroJc[p]);
      Need(std::isfinite(n)&&n>0&&n<1&&V>0&&rho>0&&std::isfinite(mass)&&PoroJc[p]>1.-por&&std::fabs(mass-mref)<=5e-13*std::fabs(mref),"Current mixture ledger differs");
      result.ledger=(std::max)(result.ledger,std::fabs(mass-mref)/std::fabs(mref));Need(std::isfinite(HydroMechTopLoadRawc[p])&&std::isfinite(HydroMechLoadAcec[p].z)&&std::isfinite(Acec[p].z)&&std::isfinite(PorePressRatec[p])&&PoroThetac[p]==0,"Nonfinite live output/nonzero rest theta");
      Need(Acec[p].x==0&&Acec[p].y==0&&HydroMechLoadAcec[p].x==0&&HydroMechLoadAcec[p].y==0&&(band||HydroMechLoadAcec[p].z==0),"Unexpected tangential/out-of-band loading");
      if(band)raw+=mass*HydroMechTopLoadRawc[p];load+=mass*HydroMechLoadAcec[p].z;force+=mass*Acec[p].z;wrong+=double(MassFluid)*HydroMechLoadAcec[p].z;
      absload+=std::fabs(mass*HydroMechLoadAcec[p].z);absforce+=std::fabs(mass*Acec[p].z);maxAceLoad=(std::max)(maxAceLoad,std::fabs(double(Acec[p].z)-HydroMechLoadAcec[p].z));
      if(!trial)Need(Acec[p].z==0&&HydroMechLoadAcec[p].z==0&&HydroMechTopLoadRawc[p]==0&&PorePressRatec[p]==0,"Natural zero-q source not strictly zero");
    }
    const double analytic=-q*Area0,lb=Budget(absload,target),ab=Budget(absforce,target);
    Need(std::isfinite(raw)&&std::isfinite(load)&&std::isfinite(force)&&std::isfinite(target)&&std::isfinite(wrong),"Nonfinite force resultant");
    if(trial)Need(result.top>0&&result.band>0&&target<0&&raw<0,"Nonempty downward source/raw band required");else Need(target==0&&raw==0&&load==0&&force==0,"Zero-q resultant differs");
    const double scale=(trial?target/raw:0.);result.loadratio=(std::max)(std::fabs(load-target),std::fabs(load-analytic))/lb;result.aceratio=(std::max)(std::fabs(force-target),std::fabs(force-analytic))/ab;
    result.wrongratio=std::fabs(wrong-target)/(std::max)(lb,ab);
    Need(result.loadratio<=1&&result.aceratio<=1,"Actual same-stage resultant outside predeclared force budget");
    if(trial>=2)Need(result.wrongratio>100,"Incorrect MassFluid weighting not nonempty against100 force budgets");
    for(unsigned id=Fixed;id<Total;id++){const unsigned p=owner[id];double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);const bool band=Posc[p].z>zmax-double(KernelSize);const float predicted=(band?float(HydroMechTopLoadRawc[p]*scale):0.f);
      rows<<trial<<','<<clock<<','<<id<<','<<Posc[p].x<<','<<Posc[p].z<<','<<PoroJc[p]<<','<<n<<','<<V<<','<<rho<<','<<rho*V<<','<<FSTypec[p]<<','<<band<<','<<HydroMechTopLoadRawc[p]<<','<<HydroMechLoadAcec[p].z<<','<<predicted<<','<<Acec[p].z<<','<<PoroThetac[p]<<','<<PorePressRatec[p]<<'\n';
    }
    summary<<trial<<','<<clock<<','<<q<<','<<result.top<<','<<result.band<<','<<target<<','<<analytic<<','<<raw<<','<<scale<<','<<load<<','<<force<<','<<wrong<<','<<absload<<','<<absforce<<','<<lb<<','<<ab<<','<<result.loadratio<<','<<result.aceratio<<','<<result.wrongratio<<','<<maxAceLoad<<','<<result.ledger<<'\n';
    PosInteraction_Forces();Need(!Acec&&!Arc&&!Rsigmac&&!BoundDerivativeVelc&&!HydroMechTopLoadRawc,"Force scratch not released");
    TimeStep=0.;Need(!TimeStep&&!Nstep&&SymplecticDtPre==locked&&LastDt==last&&FixedDt->GetDtError(false)==error,"Manufactured clock restore differs");return result;
  }
};
}
int main(int argc,char** argv){try{
  Need(argc==5&&std::string(argv[1])=="--input"&&std::string(argv[3])=="--out","Use --input EXISTING_CASE02_PRIVATE_XML --out FRESH_DIR");const fs::path xml=argv[2],out=argv[4];auto prefix=xml;prefix.replace_extension();Need(fs::is_regular_file(xml)&&fs::is_regular_file(prefix.string()+".bi4")&&!fs::exists(out),"Existing unchanged seed and fresh output required");
  AppInfo.ConfigRunPaths(argv[0]);std::vector<std::string> args={argv[0],"-cpu","-ompthreads:1","-stable","-mdbc_freeslip",prefix.string(),out.string(),"-dirdataout","data","-svres"};std::vector<char*> a;for(auto& s:args)a.push_back(s.data());JSphCfgRun cfg;cfg.LoadArgv(int(a.size()),a.data());Need(cfg.Cpu&&cfg.OmpThreads==1&&cfg.Stable&&!cfg.PrintInfo&&!cfg.PartBegin&&!cfg.NstepsBreak&&cfg.TimeMax<0&&cfg.TimePart<0&&!cfg.SvAllSteps,"No integration/restart/clock override");
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
  std::ofstream rows(fs::path(cfg.DirOut)/"loads.csv"),summary(fs::path(cfg.DirOut)/"summary.csv");rows<<std::setprecision(17);summary<<std::setprecision(17);
  rows<<"case,manufactured_clock_s,id,x,z,J,n,V,rho,mass,FSType,in_actual_band,raw_band_load_az,actual_LoadAce_z,reference_normalized_az,finished_Ace_z,theta,complete_rate\n";
  summary<<"case,manufactured_clock_s,q_Pa,actual_top_count,actual_band_count,retained_float_target_N,analytic_qA0_N,raw_weighted_N,scale,actual_rhoV_LoadAce_N,actual_rhoV_Ace_N,wrong_MassFluid_LoadAce_N,absolute_load_N,absolute_force_N,load_budget_N,force_budget_N,load_error_ratio,finished_force_error_ratio,wrong_weight_error_ratio,max_Ace_minus_LoadAce_m_s2,max_ledger_relative_error\n";
  double ml=0,ma=0,mr=0;for(unsigned trial=0;trial<4;trial++){loadstage::Audit audit;const auto r=audit.Execute(&cfg,AppInfo.LogPtr(),trial,rows,summary);ml=(std::max)(ml,r.loadratio);ma=(std::max)(ma,r.aceratio);if(trial>=2)mr=(mr?((std::min)(mr,r.wrongratio)):r.wrongratio);}
  rows.flush();summary.flush();Need(bool(rows)&&bool(summary),"Force-stage CSV write failed");
  std::ofstream done(fs::path(cfg.DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_case02_flux_load_r1\",\"passed\":true,\"cases\":4,\"actual_force_calls\":4,\"native_count\":1000,\"fixed_count\":40,\"load_rows\":4000,\"summary_rows\":4,\"nonempty_wrong_weight_cases\":2,\"minimum_wrong_weight_over_original_force_budget\":"<<mr<<",\"max_load_resultant_over_original_force_budget\":"<<ml<<",\"max_finished_force_over_original_force_budget\":"<<ma<<",\"normal_soil_physical_inputs_byte_unchanged\":true,\"force_stage_scratch_read_before_release\":true,\"all_force_scratch_released\":true,\"source_clock_manufactured_not_integrated\":true,\"manufactured_not_constitutive_trajectory\":true,\"periodic_J_field_assigned_not_copy_proof\":true,\"finished_Normalize_called_again\":false,\"Run_ComputeStep_SaveData_called\":false,\"physical_time_advanced_s\":0,\"completed_physical_steps\":0,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Load completion write failed");return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Frozen load component rejected; preserve partials\n";return 2;}}
