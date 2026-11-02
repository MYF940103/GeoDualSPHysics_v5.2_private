// Private GPU case02 true Run; no field initialization or integration override.
#define main RetainedGpuColumnObserverDeclarationsMain
#include "upl_gpu_observer_native_r1.cpp"
#undef main
#include "JDsFixedDt.h"
#include "JXml.h"
#include "JException.h"
#include <cuda_runtime_api.h>
#include <cfloat>

namespace column {
static void Require(bool ok,const std::string& text){if(!ok)throw std::runtime_error(text);}
template<class T>static std::vector<T> Down(const T* device,unsigned n){
  Require(device!=nullptr,"Missing persistent GPU array");std::vector<T> v(n);
  const auto e=cudaMemcpy(v.data(),device,sizeof(T)*n,cudaMemcpyDeviceToHost);Require(e==cudaSuccess,cudaGetErrorString(e));return v;
}
constexpr unsigned Soil=1000,Fixed=40,Total=1040;
constexpr double Dp=.01,Width=.1,Height=1.,End=.025,Drain=.01;
constexpr double Rho=2100.,Water=1000.,WaterBulk=2e8;
struct Window {const char* name;double dt,end;unsigned steps;bool smoke;};
static Window Select(const std::string& name){
  if(name=="smoke")return{"smoke",2.5e-6,5e-6,2,true};
  if(name=="coarse")return{"coarse",2.5e-6,End,10000,false};
  if(name=="half")return{"half",1.25e-6,End,20000,false};
  throw std::runtime_error("Use only the declared smoke|coarse|half window");
}
static void Runtime(const fs::path& path,const Window& w){
  JXml x;x.LoadFile(path.string());const auto* h=x.GetNodeError("case.execution.special.hydromechanics");
  const auto* c=x.GetNodeError("case.execution.constants");const auto* s=x.GetNodeError("case.execution.special.soils");
  auto hv=[&](const char* key,double value){Require(x.ReadElementDouble(h,key,"value")==value,"Case02 hydromechanics differs: "+std::string(key));};
  hv("HydroMech",1);hv("PoreWaterRho",Water);hv("PoreWaterBulkModulus",WaterBulk);hv("Porosity",.3);hv("HydraulicConductivity",.0001);hv("PoreDtSafety",1);
  hv("HydroMechInitMode",0);hv("HydroMechTopLoadQ0",10000);hv("HydroMechTopLoadRampTime",Drain);hv("HydroMechDrainage",1);hv("HydroMechDrainageStartTime",Drain);hv("HydroMechDrainageFixedGrid",1);hv("PoreShepardRegularization",0);
  hv("HydroMechDynamicSeepage",0);hv("HydroMechConductivityModel",0);hv("HydroMechConductivityCk",0);
  Require(x.ReadElementStr(h,"HydroMechTopLoadMode","value")=="TopKernelBand","Only the retained TopKernelBand load is admitted");
  Require(x.ReadElementDouble(h,"PoreCompressionGradCorr","value",true,1)==1&&x.ReadElementDouble(h,"PoreCompressionSourceMode","value",true,0)==0,"Corrected pair-divergence compression required");
  Require(x.GetAttributeDouble3(x.GetFirstElement(c,"gravity"))==TDouble3(0)&&x.GetAttributeDouble3(x.GetFirstElement(x.GetNodeError("case.casedef.constantsdef"),"gravity"))==TDouble3(0),"Both case02 gravity declarations must remain zero");
  Require(x.ReadElementDouble(c,"rhop0","value")==Rho&&x.ReadElementDouble(c,"dp","value")==Dp&&x.ReadElementDouble(c,"h","value")==.018&&x.ReadElementDouble(c,"massfluid","value")==.21&&x.ReadElementDouble(c,"massbound","value")==.21&&x.ReadElementDouble(c,"cflnumber","value")==.2,"Retained geometry/material constants differ");
  Require(x.ReadElementDouble(s,"ModulusE","value")==2e6&&x.ReadElementDouble(s,"PRvs","value")==.3&&x.ReadElementDouble(s,"phi","value")==33&&x.ReadElementDouble(s,"coh","value")==100e3&&x.ReadElementDouble(s,"dlt","value")==0,"Retained elastic-test material differs");
  const auto* particles=x.GetNodeError("case.execution.particles");
  Require(x.GetAttributeUnsigned(x.GetFirstElement(particles,"fixed"),"begin")==0&&x.GetAttributeUnsigned(x.GetFirstElement(particles,"fixed"),"count")==Fixed&&x.GetAttributeUnsigned(x.GetFirstElement(particles,"fluid"),"begin")==Fixed&&x.GetAttributeUnsigned(x.GetFirstElement(particles,"fluid"),"count")==Soil,"Retained 40 fixed/1000 soil initial blocks differ");
  Require(!x.GetNode("case.execution.special.initialize"),"No new particle-field initialization is admitted");
  std::map<std::string,double> p;for(auto* e=x.GetNodeError("case.execution.parameters")->FirstChildElement("parameter");e;e=e->NextSiblingElement("parameter"))Require(p.emplace(x.GetAttributeStr(e,"key"),x.GetAttributeDouble(e,"value")).second,"Duplicate runtime parameter");
  auto pv=[&](const char* key,double value){Require(p.count(key)&&p.at(key)==value,"Case02 option/clock differs: "+std::string(key));};
  pv("SavePosDouble",1);pv("Boundary",2);pv("SlipMode",3);pv("StepAlgorithm",2);pv("Kernel",2);pv("ViscoTreatment",1);pv("Visco",0);pv("ArtificialStress",0);pv("SoilStressRateGradCorr",1);pv("SoilHourglassXi",0);pv("SoilBoundaryDerivativeSPR",0);pv("SoilDamping",0);pv("DensityDT",0);pv("Shifting",0);pv("XPeriodicIncZ",0);
  pv("DtIni",w.dt);pv("DtFixed",w.dt);pv("TimeMax",w.end);
  Require(p.count("TimeOut")&&std::isfinite(p.at("TimeOut"))&&p.at("TimeOut")>0&&p.at("TimeOut")<=w.end,"Positive bounded XML output cadence required");
  if(w.smoke)pv("TimeOut",w.dt);
  for(const char* key:{"XZPeriodic","YPeriodicIncX","YPeriodicIncZ","ZPeriodicIncX","ZPeriodicIncY"})Require(!p.count(key),"Only rectangular X periodicity is admitted");
}
class Actual:public JSphGpuSingle{
public:
  Actual(){PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;DynamicPoreConductivity=false;DynamicPoreConductivityCk=0.;}
  void Finish(const fs::path& out,const column::Window& w){
    Require(PorosityObserver&&PorosityFeedback&&DynamicPorePressure&&DynamicPoreWall&&!DynamicPoreConductivity&&DynamicPoreConductivityCk==0&&!HydroMechDynamicSeepage&&HydroMechConductivityModel==0&&HydroMechConductivityCk==0,"Run left the private constant-k model");
    Require(HydroMech&&Simulate2D&&TStep==STEP_Symplectic&&!PartBegin&&CaseNpb==column::Fixed&&CaseNfluid==column::Soil&&CaseNp==column::Total&&!CaseNmoving&&!CaseNfloat&&PeriX&&!PeriY&&!PeriZ&&PeriXinc.x!=0&&std::fabs(std::fabs(PeriXinc.x)-column::Width)<=64.*DBL_EPSILON*column::Width&&PeriXinc.y==0&&PeriXinc.z==0&&Gravity==TFloat3(0)&&CSP.gravity==Gravity,"Actual GPU column backend/geometry/gravity differs");
    Require(TBoundary==BC_MDBC&&SlipMode==SLIP_FreeSlip&&UseNormals&&BoundNormalg&&BoundModeg&&HydroMechInitMode==HMINIT_None&&HydroMechTopLoadMode==HMLOAD_TopKernelBand&&HydroMechTopLoadQ0==10000.f&&HydroMechTopLoadRampTime==column::Drain&&HydroMechDrainage&&HydroMechDrainageStartTime==column::Drain&&HydroMechDrainageFixedGrid,"Actual one-bottom FreeSlip/load/drain scope differs");
    Require(SoilHourglassXi==0&&!SoilBoundaryDerivativeSPR&&!SoilDamping&&!Visco&&TVisco==VISCO_Artificial&&!Damping&&!RelaxZones&&!InOut&&!AccInput&&!Shifting&&!NoPenetration&&!ArtificialStress&&TDensity==DDT_None&&!StrainSoftening&&!UseDEM&&!Symmetry&&!PoreShepardRegularization&&PoreCompressionGradCorr&&PoreCompressionSourceMode==0&&SoilStressRateGradCorr,"Unsupported auxiliary physics/compression path");
    Require(RhopZero==column::Rho&&MassFluid==float(.21)&&MassBound==MassFluid&&JSph::Dp==column::Dp&&KernelH==float(.018)&&SoilCte.Porosity==float(.3)&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==2e8f&&SoilCte.HydraulicConductivity==float(.0001)&&SoilCte.ModulusK==1666666.75f&&SoilCte.ModulusG==769230.8125f&&PoreDtSafety==1.f,"Actual loaded GPU material differs");
    Require(std::isfinite(TimeStep)&&std::fabs(TimeStep-w.end)<=1e-14&&Nstep==w.steps&&NstepsBreak==int(w.steps)&&SymplecticDtPre==w.dt&&LastDt==w.dt&&FixedDt&&FixedDt->GetFixedValue()==w.dt,"Actual decimal-clock end/locked step/count differs");
    Require(!PosxyPreg&&!PoszPreg&&!VelrhopPreg&&!SigmaPreg&&!PorePressPreg&&!PoroJPreg&&!Aceg&&!Arg&&!ViscDtg&&!Rsigmag&&!BoundDerivativeVelg&&!HydroMechTopLoadRawg,"Predictor/force scratch not released");
    Require(Idpg&&Codeg&&PoroJg&&PoroThetag&&HydroMechLoadAceg&&PorePressg&&PorePress0g&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Missing persistent state or excluded particles");
    const double signedError=FixedDt->GetDtError(false);Require(std::isfinite(signedError)&&signedError<=1e-14&&DynamicConductivitySpeedMax==0,"Signed fixed-step diagnostic or constant-law cache invalid");
    // Preserve all-slot ordering: BoundNormal/Slip are downloaded separately, not compacted.
    Require(ParticlesDataDown(Np,0,true,false)==Np&&Idp&&Code&&AuxPos&&Velrhop&&Sigma&&Kplastic&&PorePress&&PorePress0&&PoroJ&&PoroTheta&&AuxHydroMechLoadAce,"Incomplete final production GPU download");
    const auto normals=Down(BoundNormalg,Np);const auto slips=(BoundSlipModeg?Down(BoundSlipModeg,Np):std::vector<byte>());
    std::vector<unsigned> order(column::Total,~0u);unsigned nf=0,ns=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Code[p])){
      const unsigned id=Idp[p];Require(id<column::Total&&order[id]==~0u,"Invalid/duplicate final normal ID");order[id]=p;
      if(id<column::Fixed){const auto b=normals[p];const auto v=Velrhop[p];Require(CODE_IsFixed(Code[p])&&Finite(AuxPos[p])&&std::isfinite(b.x)&&std::isfinite(b.y)&&std::isfinite(b.z)&&v.x==0&&v.y==0&&v.z==0&&v.w==column::Rho&&(slips.empty()?SlipMode:TpSlipMode(slips[p]))==SLIP_FreeSlip&&b.x==0&&b.y==0&&b.z>0&&std::fabs(AuxPos[p].z+.5*double(b.z))<=1e-6*column::Dp,"Fixed bottom owner/normal/velocity differs");nf++;}
      else{Require(CODE_IsFluid(Code[p]),"Soil owner is not fluid");ns++;}
    }
    Require(nf==column::Fixed&&ns==column::Soil,"Final normal native counts differ");Fresh(out/"live_final.csv");Fresh(out/"actual_complete.json");
    std::ofstream live(out/"live_final.csv");live<<std::setprecision(17)<<"id,J,n,theta\n";
    double minJ=DBL_MAX,maxJ=-DBL_MAX,solidVolume=0,mixtureMass=0,maxSolidRoundoff=0,minFixedN=DBL_MAX,maxFixedN=-DBL_MAX;tdouble3 weighted=TDouble3(0),referenceWeighted=TDouble3(0);
    const double n0=double(SoilCte.Porosity),v0=double(MassFluid)/double(RhopZero);
    for(unsigned id=0;id<column::Total;id++){
      Require(order[id]!=~0u,"Final native ID missing");const unsigned p=order[id];const double j=PoroJ[p],theta=PoroTheta[p],n=1.-(1.-n0)/j,V=v0*j,rho=column::Water+(column::Rho-column::Water)/j;
      Require(std::isfinite(j)&&j>1.-n0&&std::isfinite(theta)&&std::isfinite(n)&&n>0&&n<1&&std::isfinite(V)&&V>0&&std::isfinite(rho)&&rho>0,"Final single-J saturated domain failed");
      const double roundoff=std::fabs((1.-n)*j-(1.-n0));Require(roundoff<=5e-13,"Final solid-fraction identity failed");maxSolidRoundoff=(std::max)(maxSolidRoundoff,roundoff);
      if(id<column::Fixed){Require(theta==0,"Fixed wall theta must remain zero");minFixedN=(std::min)(minFixedN,n);maxFixedN=(std::max)(maxFixedN,n);continue;}
      const auto x=AuxPos[p];const auto v=Velrhop[p];const auto s=Sigma[p];const auto load=AuxHydroMechLoadAce[p];
      Require(Finite(x)&&Finite(TFloat3(v.x,v.y,v.z))&&std::isfinite(v.w)&&v.w>0&&std::isfinite(PorePress[p])&&PorePress0[p]==0&&Kplastic[p]==0&&Finite(load),"Nonfinite/elastic/p0 final soil state");
      Require(std::isfinite(s.xx)&&std::isfinite(s.xy)&&std::isfinite(s.xz)&&std::isfinite(s.yy)&&std::isfinite(s.yz)&&std::isfinite(s.zz)&&x.y==0&&x.z>0,"Final stress/2D/no-bottom-crossing state invalid");
      minJ=(std::min)(minJ,j);maxJ=(std::max)(maxJ,j);solidVolume+=(1.-n)*V;mixtureMass+=rho*V;
      weighted=weighted+ToTDouble3(load)*(rho*V);referenceWeighted=referenceWeighted+ToTDouble3(load)*double(MassFluid);live<<id<<','<<j<<','<<n<<','<<theta<<'\n';
    }
    live.flush();Require(bool(live),"Final live ledger write failed");Require(Part==(w.smoke?3:769),"Declared window saved-frame count differs");
    // LoadAce is persistent last-corrector data; endpoint J reweighting is descriptive only.
    std::ofstream done(out/"actual_complete.json");done<<std::setprecision(17)
      <<"{\"passed\":true,\"stage\":\"upl_gpu_column_actual_r1\",\"backend\":\"GPU\",\"window\":\""<<w.name<<"\",\"model\":\"constant\",\"actual_production_Run\":true,\"live_GPU_download\":true,\"public_master\":false,\"private_feedback_complete_rate_wall\":true,\"physical_fields_rewritten_by_fixture\":false,\"integrator_overridden\":false,\"native_count\":1000,\"fixed_count\":40,\"total_native_count\":1040,\"completed_steps\":"<<Nstep<<",\"actual_end_s\":"<<TimeStep<<",\"planned_end_s\":"<<w.end<<",\"end_absolute_tolerance_s\":1e-14,\"dt_s\":"<<SymplecticDtPre<<",\"saved_parts\":"<<Part<<",\"max_signed_dterror_s\":"<<signedError<<",\"dterror_interval_empty_sentinel\":"<<(signedError==-DBL_MAX?"true":"false")
      <<",\"predictor_histories_released\":true,\"force_scratch_released\":true,\"J_theta_downloaded_from_GPU\":true,\"n_V_rho_k_derived_not_independent_device_arrays\":true,\"final_ledger_rows\":1000,\"fixed_J_derived_n_samples\":40,\"fixed_n_is_not_CPU_zero_marker\":true,\"min_fixed_sample_n\":"<<minFixedN<<",\"max_fixed_sample_n\":"<<maxFixedN<<",\"max_solid_fraction_roundoff\":"<<maxSolidRoundoff<<",\"min_final_J\":"<<minJ<<",\"max_final_J\":"<<maxJ<<",\"conductivity_m_s\":"<<double(SoilCte.HydraulicConductivity)<<",\"final_solid_volume_m2\":"<<solidVolume<<",\"final_mixture_mass_kg_per_m\":"<<mixtureMass<<",\"reference_volume_m2\":"<<v0<<",\"final_J_weighted_retained_load_N_per_m\":["<<weighted.x<<','<<weighted.y<<','<<weighted.z<<"],\"reference_mass_weighted_retained_load_N_per_m\":["<<referenceWeighted.x<<','<<referenceWeighted.y<<','<<referenceWeighted.z<<"],\"load_acceleration_state\":\"last_corrector_force\",\"load_inertia_state\":\"final_endpoint_J\",\"same_force_stage_load_budget_verified\":false,\"drainage_event_s\":0.01,\"event_saved_state_is_pre_open\":true,\"all_saved_native_fields_reviewed\":false,\"endpoint_force_audit_performed\":false,\"independent_half_performed\":false,\"physical_acceptance\":false}\n";
    done.flush();Require(bool(done),"Actual completion write failed");
  }
};
}
int main(int argc,char** argv){try{
  column::Require(argc>=6&&std::string(argv[1])=="--solver","Use --solver smoke|coarse|half ordinaryGPUargs");const auto w=column::Select(argv[2]);
  AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=3;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());
  column::Require(!cfg.Cpu&&cfg.GpuId==0&&cfg.Stable&&!cfg.PrintInfo&&!fs::exists(cfg.DirOut)&&!cfg.PartBegin&&cfg.NstepsBreak==int(w.steps)&&cfg.TimeMax<0&&cfg.TimePart<0&&!cfg.SvAllSteps,"Fresh GPU0 stable Run with matching explicit -nsteps and XML clocks required");
  column::Runtime(cfg.CaseName+".xml",w);AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
  column::Actual fixture;fixture.Run(AppInfo.GetFullName(),&cfg,AppInfo.LogPtr());fixture.Finish(cfg.DirOut,w);return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Private GPU column Run rejected; preserve completed or partial outputs\n";return 2;}}

