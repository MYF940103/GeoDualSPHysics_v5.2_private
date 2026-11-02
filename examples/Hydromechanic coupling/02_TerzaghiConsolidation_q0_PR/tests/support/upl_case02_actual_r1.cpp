// Private case02 constant-k true Run. No particle-field or integration override.
#define main RetainedCase02NativeDeclarationsMain
#include "upl_cpu_public_native_r1.cpp"
#undef main
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsFixedDt.h"
#include "JXml.h"
#include "JLog2.h"

namespace case02 {
constexpr unsigned Soil=1000,Fixed=40,Total=1040;
constexpr double Dp=.01,Width=.1,Height=1.,End=.0125,Drain=.01;
constexpr double Rho=2100.,Water=1000.,WaterBulk=2e8;
struct Window {const char* name;double dt,end;unsigned steps;bool smoke;};
static Window Select(const std::string& name){
  if(name=="smoke")return{"smoke",2.5e-6,5e-6,2,true};
  if(name=="coarse")return{"coarse",2.5e-6,End,5000,false};
  if(name=="half")return{"half",1.25e-6,End,10000,false};
  throw std::runtime_error("Use only the declared smoke|coarse|half window");
}
static void Runtime(const fs::path& path,const Window& w){
  JXml x;x.LoadFile(path.string());const auto* h=x.GetNodeError("case.execution.special.hydromechanics");
  const auto* c=x.GetNodeError("case.execution.constants");const auto* s=x.GetNodeError("case.execution.special.soils");
  auto hv=[&](const char* key,double value){Need(x.ReadElementDouble(h,key,"value")==value,"Case02 hydromechanics differs: "+std::string(key));};
  hv("HydroMech",1);hv("PoreWaterRho",Water);hv("PoreWaterBulkModulus",WaterBulk);hv("Porosity",.3);hv("HydraulicConductivity",.0001);hv("PoreDtSafety",1);
  hv("HydroMechInitMode",0);hv("HydroMechTopLoadQ0",10000);hv("HydroMechTopLoadRampTime",Drain);hv("HydroMechDrainage",1);hv("HydroMechDrainageStartTime",Drain);hv("HydroMechDrainageFixedGrid",1);hv("PoreShepardRegularization",0);
  hv("HydroMechDynamicSeepage",0);hv("HydroMechConductivityModel",0);hv("HydroMechConductivityCk",0);
  Need(x.ReadElementStr(h,"HydroMechTopLoadMode","value")=="TopKernelBand","Only the retained TopKernelBand load is admitted");
  Need(x.ReadElementDouble(h,"PoreCompressionGradCorr","value",true,1)==1&&x.ReadElementDouble(h,"PoreCompressionSourceMode","value",true,0)==0,"Corrected pair-divergence compression required");
  Need(x.GetAttributeDouble3(x.GetFirstElement(c,"gravity"))==TDouble3(0)&&x.GetAttributeDouble3(x.GetFirstElement(x.GetNodeError("case.casedef.constantsdef"),"gravity"))==TDouble3(0),"Both case02 gravity declarations must remain zero");
  Need(x.ReadElementDouble(c,"rhop0","value")==Rho&&x.ReadElementDouble(c,"dp","value")==Dp&&x.ReadElementDouble(c,"h","value")==.018&&x.ReadElementDouble(c,"massfluid","value")==.21&&x.ReadElementDouble(c,"massbound","value")==.21&&x.ReadElementDouble(c,"cflnumber","value")==.2,"Retained geometry/material constants differ");
  Need(x.ReadElementDouble(s,"ModulusE","value")==2e6&&x.ReadElementDouble(s,"PRvs","value")==.3&&x.ReadElementDouble(s,"phi","value")==33&&x.ReadElementDouble(s,"coh","value")==100e3&&x.ReadElementDouble(s,"dlt","value")==0,"Retained elastic-test material differs");
  const auto* particles=x.GetNodeError("case.execution.particles");
  Need(x.GetAttributeUnsigned(x.GetFirstElement(particles,"fixed"),"begin")==0&&x.GetAttributeUnsigned(x.GetFirstElement(particles,"fixed"),"count")==Fixed&&x.GetAttributeUnsigned(x.GetFirstElement(particles,"fluid"),"begin")==Fixed&&x.GetAttributeUnsigned(x.GetFirstElement(particles,"fluid"),"count")==Soil,"Retained 40 fixed/1000 soil initial blocks differ");
  Need(!x.GetNode("case.execution.special.initialize"),"No new particle-field initialization is admitted");
  std::map<std::string,double> p;for(auto* e=x.GetNodeError("case.execution.parameters")->FirstChildElement("parameter");e;e=e->NextSiblingElement("parameter"))Need(p.emplace(x.GetAttributeStr(e,"key"),x.GetAttributeDouble(e,"value")).second,"Duplicate runtime parameter");
  auto pv=[&](const char* key,double value){Need(p.count(key)&&p.at(key)==value,"Case02 option/clock differs: "+std::string(key));};
  pv("SavePosDouble",1);pv("Boundary",2);pv("SlipMode",3);pv("StepAlgorithm",2);pv("Kernel",2);pv("ViscoTreatment",1);pv("Visco",0);pv("ArtificialStress",0);pv("SoilStressRateGradCorr",1);pv("SoilHourglassXi",0);pv("SoilBoundaryDerivativeSPR",0);pv("SoilDamping",0);pv("DensityDT",0);pv("Shifting",0);pv("XPeriodicIncZ",0);
  pv("DtIni",w.dt);pv("DtFixed",w.dt);pv("TimeMax",w.end);
  Need(p.count("TimeOut")&&std::isfinite(p.at("TimeOut"))&&p.at("TimeOut")>0&&p.at("TimeOut")<=w.end,"Positive bounded XML output cadence required");
  if(w.smoke)pv("TimeOut",w.dt);
  for(const char* key:{"XZPeriodic","YPeriodicIncX","YPeriodicIncZ","ZPeriodicIncX","ZPeriodicIncY"})Need(!p.count(key),"Only rectangular X periodicity is admitted");
}
class Actual:public JSphCpuSingle{
public:
  Actual(){PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;DynamicPoreConductivity=false;DynamicPoreConductivityCk=0.;}
  void Finish(const fs::path& out,const case02::Window& w){
    Need(PorosityObserver&&PorosityFeedback&&DynamicPorePressure&&DynamicPoreWall&&!DynamicPoreConductivity&&DynamicPoreConductivityCk==0&&!HydroMechDynamicSeepage&&HydroMechConductivityModel==0&&HydroMechConductivityCk==0,"Run left the declared private constant-k model");
    Need(HydroMech&&Simulate2D&&TStep==STEP_Symplectic&&!PartBegin&&CaseNpb==case02::Fixed&&CaseNfluid==case02::Soil&&CaseNp==case02::Total&&!CaseNmoving&&!CaseNfloat&&PeriX&&!PeriY&&!PeriZ&&PeriXinc.x!=0&&std::fabs(std::fabs(PeriXinc.x)-case02::Width)<=64.*DBL_EPSILON*case02::Width&&PeriXinc.y==0&&PeriXinc.z==0&&Gravity==TFloat3(0)&&CSP.gravity==Gravity&&OmpThreads==1,"Actual case02 backend/geometry/gravity differs");
    Need(TBoundary==BC_MDBC&&SlipMode==SLIP_FreeSlip&&UseNormals&&BoundNormalc&&BoundModec&&HydroMechInitMode==HMINIT_None&&HydroMechTopLoadMode==HMLOAD_TopKernelBand&&HydroMechTopLoadQ0==10000.f&&HydroMechTopLoadRampTime==case02::Drain&&HydroMechDrainage&&HydroMechDrainageStartTime==case02::Drain&&HydroMechDrainageFixedGrid,"Actual one-bottom FreeSlip/load/drain scope differs");
    Need(!HourglassCpu&&SoilHourglassXi==0&&!SoilBoundaryDerivativeSPR&&!SoilDamping&&!Visco&&TVisco==VISCO_Artificial&&!Damping&&!RelaxZones&&!InOut&&!AccInput&&!Shifting&&!NoPenetration&&!ArtificialStress&&TDensity==DDT_None&&!StrainSoftening&&!UseDEM&&!Symmetry&&!PoreShepardRegularization&&PoreCompressionGradCorr&&PoreCompressionSourceMode==0&&SoilStressRateGradCorr,"Unsupported auxiliary physics/compression path");
    Need(RhopZero==case02::Rho&&MassFluid==float(.21)&&MassBound==MassFluid&&JSph::Dp==case02::Dp&&KernelH==float(.018)&&SoilCte.Porosity==float(.3)&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==2e8f&&SoilCte.HydraulicConductivity==float(.0001)&&SoilCte.ModulusK==1666666.75f&&SoilCte.ModulusG==769230.8125f&&PoreDtSafety==1.f,"Actual loaded material differs");
    Need(std::isfinite(TimeStep)&&std::fabs(TimeStep-w.end)<=1e-14&&Nstep==w.steps&&NstepsBreak==w.steps&&SymplecticDtPre==w.dt&&LastDt==w.dt&&FixedDt&&FixedDt->GetFixedValue()==w.dt,"Actual decimal-clock end/locked step/count differs");
    Need(!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec&&!Acec&&!Arc&&!BoundDerivativeVelc&&!HydroMechTopLoadRawc,"Predictor/force scratch not released");
    Need(Idpc&&Codec&&Posc&&Velrhopc&&Sigmac&&Kplasticc&&PorePressc&&PorePress0c&&PoroJc&&PoroThetac&&HydroMechLoadAcec&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Missing persistent state or excluded particles");
    const double signedError=FixedDt->GetDtError(false);Need(std::isfinite(signedError)&&signedError<=1e-14&&DynamicConductivitySpeedMax==0,"Signed fixed-step diagnostic or constant-law cache invalid");
    std::vector<unsigned> order(case02::Total,~0u);unsigned nf=0,ns=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){
      const unsigned id=Idpc[p];Need(id<case02::Total&&order[id]==~0u,"Invalid/duplicate final normal ID");order[id]=p;
      if(id<case02::Fixed){const auto b=BoundNormalc[p];Need(CODE_IsFixed(Codec[p])&&Velrhopc[p].x==0&&Velrhopc[p].y==0&&Velrhopc[p].z==0&&Velrhopc[p].w==case02::Rho&&(BoundSlipModec?TpSlipMode(BoundSlipModec[p]):SlipMode)==SLIP_FreeSlip&&b.x==0&&b.y==0&&b.z>0&&std::fabs(Posc[p].z+.5*double(b.z))<=1e-6*case02::Dp,"Fixed bottom owner/normal/velocity differs");nf++;}
      else{Need(CODE_IsFluid(Codec[p]),"Soil owner is not fluid");ns++;}
    }
    Need(nf==case02::Fixed&&ns==case02::Soil,"Final normal native counts differ");
    Need(!fs::exists(out/"live_final.csv")&&!fs::exists(out/"actual_complete.json"),"Retained fixture outputs protected");
    std::ofstream live(out/"live_final.csv");live<<std::setprecision(17)<<"id,J,n,theta\n";
    double maxLedger=0,minJ=DBL_MAX,maxJ=-DBL_MAX,solidVolume=0,mixtureMass=0;tdouble3 weighted=TDouble3(0),referenceWeighted=TDouble3(0);
    const double n0=double(SoilCte.Porosity),v0=double(MassFluid)/double(RhopZero);
    for(unsigned id=0;id<case02::Total;id++){
      Need(order[id]!=~0u,"Final normal native ID missing");if(id<case02::Fixed)continue;const unsigned p=order[id];const auto x=Posc[p];const auto v=Velrhopc[p];const auto s=Sigmac[p];const auto load=HydroMechLoadAcec[p];
      double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);const double j=PoroJc[p],nr=1.-(1.-n0)/j,Vr=v0*j,rr=case02::Water+(case02::Rho-case02::Water)/j;
      Need(Finite(x)&&Finite(TFloat3(v.x,v.y,v.z))&&std::isfinite(v.w)&&v.w>0&&std::isfinite(PorePressc[p])&&PorePress0c[p]==0&&Kplasticc[p]==0&&std::isfinite(PoroThetac[p])&&Finite(load),"Nonfinite/elastic/p0 final soil state");
      Need(std::isfinite(s.xx)&&std::isfinite(s.xy)&&std::isfinite(s.xz)&&std::isfinite(s.yy)&&std::isfinite(s.yz)&&std::isfinite(s.zz)&&x.y==0&&x.z>0,"Final stress/2D/no-bottom-crossing state invalid");
      Need(std::isfinite(j)&&j>1.-n0&&n>0&&n<1&&V>0&&rho>0&&Close(n,nr)&&Close(V,Vr)&&Close(rho,rr)&&std::fabs((1.-n)*j-(1.-n0))<=5e-13,"Final single-J saturated ledger failed");
      maxLedger=(std::max)({maxLedger,std::fabs(n-nr)/n,std::fabs(V-Vr)/V,std::fabs(rho-rr)/rho});minJ=(std::min)(minJ,j);maxJ=(std::max)(maxJ,j);solidVolume+=(1.-n)*V;mixtureMass+=rho*V;
      weighted=weighted+ToTDouble3(load)*(rho*V);referenceWeighted=referenceWeighted+ToTDouble3(load)*double(MassFluid);live<<id<<','<<j<<','<<n<<','<<PoroThetac[p]<<'\n';
    }live.flush();Need(bool(live),"Final live ledger write failed");if(w.smoke)Need(Part==3,"Declared two-step smoke must save three frames");
    // Persistent load is from the last corrector force; J is the final endpoint.
    // This final-inertia reweighting is descriptive, not a same-force-stage budget.
    std::ofstream done(out/"actual_complete.json");done<<std::setprecision(17)
      <<"{\"passed\":true,\"stage\":\"upl_case02_actual_r1\",\"window\":\""<<w.name<<"\",\"model\":\"constant\",\"actual_production_Run\":true,\"public_master\":false,\"private_feedback_complete_rate_wall\":true,\"physical_fields_rewritten_by_fixture\":false,\"integrator_overridden\":false,\"native_count\":1000,\"fixed_count\":40,\"total_native_count\":1040,\"completed_steps\":"<<Nstep<<",\"actual_end_s\":"<<TimeStep<<",\"planned_end_s\":"<<w.end<<",\"end_absolute_tolerance_s\":1e-14,\"dt_s\":"<<SymplecticDtPre<<",\"saved_parts\":"<<Part<<",\"max_signed_dterror_s\":"<<signedError<<",\"predictor_histories_released\":true,\"force_scratch_released\":true,\"final_ledger_rows\":1000,\"max_final_ledger_relative_error\":"<<maxLedger<<",\"min_final_J\":"<<minJ<<",\"max_final_J\":"<<maxJ<<",\"final_solid_volume_m2\":"<<solidVolume<<",\"final_mixture_mass_kg_per_m\":"<<mixtureMass<<",\"reference_volume_m2\":"<<v0<<",\"final_J_weighted_retained_load_N_per_m\":["<<weighted.x<<','<<weighted.y<<','<<weighted.z<<"],\"reference_mass_weighted_retained_load_N_per_m\":["<<referenceWeighted.x<<','<<referenceWeighted.y<<','<<referenceWeighted.z<<"],\"load_acceleration_state\":\"last_corrector_force\",\"load_inertia_state\":\"final_endpoint_J\",\"same_force_stage_load_budget_verified\":false,\"drainage_event_s\":0.01,\"event_saved_state_is_pre_open\":true,\"all_saved_native_fields_reviewed\":false,\"independent_half_performed\":false,\"physical_acceptance\":false}\n";
    done.flush();Need(bool(done),"Actual completion write failed");
  }
};
}
int main(int argc,char** argv){try{
  Need(argc>=6&&std::string(argv[1])=="--solver","Use --solver smoke|coarse|half ordinaryCPUargs");const auto w=case02::Select(argv[2]);
  AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=3;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());
  Need(cfg.Cpu&&cfg.OmpThreads==1&&cfg.Stable&&!cfg.PrintInfo&&!fs::exists(cfg.DirOut)&&!cfg.PartBegin&&cfg.NstepsBreak==int(w.steps)&&cfg.TimeMax<0&&cfg.TimePart<0&&!cfg.SvAllSteps,"Fresh CPU OMP1 stable Run with matching explicit -nsteps and XML clocks required");
  case02::Runtime(cfg.CaseName+".xml",w);AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
  case02::Actual fixture;fixture.Run(AppInfo.GetFullName(),&cfg,AppInfo.LogPtr());fixture.Finish(cfg.DirOut,w);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Private case02 actual Run rejected; preserve completed or partial outputs\n";return 2;}}

