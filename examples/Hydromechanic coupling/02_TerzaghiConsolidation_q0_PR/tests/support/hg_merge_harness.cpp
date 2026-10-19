// Case-02 production-path regression. Numerical integration is never copied.
// XML controls all physical parameters and dt; CLI only limits steps and output.
#include "JSphCpuSingle.h"
#include "JSphHourglassCpu.h"
#include "JSphCfgRun.h"
#include "JDsFixedDt.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <vector>

JAppInfo AppInfo("ProductionMergeCheck","v1","12-10-2026");
namespace fs=std::filesystem;
static void Check(bool okay,const char* message){if(!okay)throw std::runtime_error(message);}
static std::array<double,6> Unpack(const tsymatrix3d& s){return{{s.xx,s.yy,s.zz,s.xy,s.yz,s.xz}};}

class ProductionMergeCheck:public JSphCpuSingle{
  std::ofstream state,hglog;
  unsigned Saved=0,Samples=0;
  double TestDt=0,PoreDt=0;
  bool Soil(unsigned p)const{return CODE_IsNormal(Codec[p])&&CODE_IsFluid(Codec[p]);}
  std::map<unsigned,unsigned> Order(bool soilonly)const{
    std::map<unsigned,unsigned> ids;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])&&(!soilonly||Soil(p)))
      Check(ids.emplace(Idpc[p],p).second,"Duplicate normal particle ID");
    Check(ids.size()==(soilonly?1000:1040),"Case-02 native particle count changed");
    return ids;
  }
  void WriteState(const char* stem)const{
    const fs::path out(CfgRun->DirOut);
    std::ofstream csv(out/(std::string(stem)+".csv"));csv<<std::setprecision(17);
    std::ofstream bits(out/(std::string(stem)+".bin"),std::ios::binary);
    csv<<"id,x,y,z,vx,vy,vz,rho,pressure,sigma_xx,sigma_yy,sigma_zz,sigma_xy,sigma_yz,sigma_xz,kplastic\n";
    const auto write=[&bits](auto value){bits.write(reinterpret_cast<const char*>(&value),sizeof(value));};
    for(const auto& item:Order(false)){
      const unsigned p=item.second;const auto x=Posc[p];const auto v=Velrhopc[p];
      csv<<item.first<<','<<x.x<<','<<x.y<<','<<x.z<<','<<v.x<<','<<v.y<<','<<v.z<<','<<v.w<<','<<PorePressc[p];
      for(double s:Unpack(Sigmac[p]))csv<<','<<s;csv<<','<<Kplasticc[p]<<'\n';
      write(item.first);write(x.x);write(x.y);write(x.z);
      write(v.x);write(v.y);write(v.z);write(v.w);write(PorePressc[p]);write(PorePress0c[p]);
      for(double s:Unpack(Sigmac[p]))write(s);write(Kplasticc[p]);
    }
    csv.flush();bits.flush();Check(bool(csv)&&bool(bits),"Native state write failed");
    std::ofstream meta(out/(std::string(stem)+".json"));meta<<std::setprecision(17)
      <<"{\"time_s\":"<<TimeStep<<",\"completed_steps\":"<<Nstep
      <<",\"native_count\":1040,\"soil_count\":1000,\"soil_first_id\":40,\"soil_last_id\":1039"
      <<",\"binary_record_bytes\":104,\"binary_layout\":\"little_endian:uint32_id,3_float64_position,6_float32_vxyz_rho_p_p0,6_float64_sigma_xx_yy_zz_xy_yz_xz,float32_kplastic\"}\n";
    meta.flush();Check(bool(meta),"Native state metadata write failed");
  }
  void Sample(){
    for(const auto& item:Order(true)){
      const unsigned p=item.second;const auto x=Posc[p];const auto v=Velrhopc[p];
      Check(item.first>=40&&item.first<1040,"Unexpected material ID");
      Check(std::isfinite(x.x)&&std::isfinite(x.y)&&std::isfinite(x.z)
        &&std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z)&&std::isfinite(v.w)&&v.w>0
        &&std::isfinite(PorePressc[p])&&Kplasticc[p]==0,"Nonfinite or nonelastic native state");
      state<<TimeStep<<','<<Nstep<<",full_step,"<<item.first<<','<<x.x<<','<<x.y<<','<<x.z
        <<','<<v.x<<','<<v.y<<','<<v.z<<','<<v.w<<','<<PorePressc[p];
      for(double s:Unpack(Sigmac[p])){Check(std::isfinite(s),"Nonfinite stress");state<<','<<s;}
      // These four boundary diagnostics are last-stage fields, not a new force
      // evaluation at this time. SaveData may refresh only free-surface fields.
      state<<','<<Kplasticc[p]<<','<<(Nstep?HydroMechLoadAcec[p].z:0.f)
        <<','<<FSTypec[p]<<','<<FSNormalc[p].z
        <<','<<(IsHydroMechDrainageActive()&&IsHydroMechDrainedParticle(p,Posc,Codec,FSTypec)?1:0)
        <<','<<((item.first-40)%100==99&&TimeStep>0?1:0)<<'\n';
    }
    if(HourglassCpu&&Nstep){
      const auto& r=HourglassCpu->GetRateInfo();const auto& s=HourglassCpu->GetStats();
      const double natural=(std::min)(PoreDt,TestDt-FixedDt->GetDtError(false));
      hglog<<TimeStep<<','<<Nstep<<",corrected_endpoint,"<<SoilHourglassXi<<','<<TestDt
        <<','<<HourglassCpu->GetPairCount()<<','<<r.netx<<','<<r.netz<<','<<r.sumrate
        <<','<<r.ratepower<<','<<r.form<<','<<r.workerror<<','<<r.rmax<<','<<r.condition<<','<<r.skew
        <<','<<r.meandxx/1000<<','<<sqrt(r.rmsdxx/1000)<<','<<r.meandiv/1000<<','<<sqrt(r.rmsdiv/1000)
        <<','<<r.lambda<<','<<r.tau<<','<<TestDt/r.tau<<','<<natural<<','<<s.spinbound<<','<<s.maxhistory
        <<','<<s.maxnetforce<<','<<s.maxactualnetforce<<'\n';
      hglog.flush();Check(bool(hglog),"HG sampled output write failed");
    }
    state.flush();Check(bool(state),"Sampled state write failed");Samples++;
  }
  void WriteHgFinal(unsigned steps)const{
    const fs::path out(CfgRun->DirOut);
    JSphHourglassCpu::StStats s{};
    if(HourglassCpu){
      s=HourglassCpu->GetStats();
      Check(s.forcecalls==2*steps&&s.ratecalls==2*steps&&s.predictorupdates==steps
        &&s.correctorupdates==steps&&s.predictorrates==steps&&s.endpointrates==steps,"Incomplete production HG history");
      std::ofstream csv(out/"hourglass_final.csv");csv<<std::setprecision(17)
        <<"id,hg_ax_m_s2,hg_az_m_s2,last_rate_x_m_s3,last_rate_z_m_s3\n";
      for(unsigned id=40;id<1040;id++){
        const auto h=HourglassCpu->GetHistory(id),r=HourglassCpu->GetRate(id);
        csv<<id<<','<<h.x<<','<<h.z<<','<<r.x<<','<<r.z<<'\n';
      }
      csv.flush();Check(bool(csv),"HG native history write failed");
    }
    std::ofstream done(out/"hourglass_complete.json");done<<std::setprecision(17)
      <<"{\"xi\":"<<SoilHourglassXi<<",\"steps\":"<<steps<<",\"dt\":"<<TestDt
      <<",\"hg_force_calls\":"<<s.forcecalls<<",\"hg_updates\":"<<s.predictorupdates+s.correctorupdates
      <<",\"predictor_updates\":"<<s.predictorupdates<<",\"corrector_updates\":"<<s.correctorupdates
      <<",\"hg_rate_calls\":"<<s.ratecalls<<",\"predictor_rate_calls\":"<<s.predictorrates<<",\"endpoint_rate_calls\":"<<s.endpointrates
      <<",\"first_pair_count\":"<<s.firstpairs<<",\"min_pair_count\":"<<s.minpairs<<",\"max_pair_count\":"<<s.maxpairs
      <<",\"max_net_hg_force_N_m\":"<<s.maxnetforce<<",\"max_actual_float_add_net_force_N_m\":"<<s.maxactualnetforce
      <<",\"max_net_hg_rate_N_m_s\":"<<s.maxnetrate<<",\"max_relative_net_hg_force\":"<<s.maxrelativeforce
      <<",\"max_relative_net_hg_rate\":"<<s.maxrelativerate<<",\"max_history_accel_m_s2\":"<<s.maxhistory
      <<",\"max_ls_condition\":"<<s.maxcondition<<",\"max_rate_work_identity_error\":"<<s.maxpoweridentityerror
      <<",\"max_skew_s_1\":"<<s.maxskew<<",\"integrated_max_skew_rad\":"<<s.spinbound
      <<",\"max_dt_over_hg_tau\":"<<s.maxtauratio<<",\"min_hg_frozen_tau_s\":"<<s.mintau
      <<",\"max_hg_frozen_lambda_bound_s_2\":"<<s.maxlambda
      <<",\"min_natural_dt_limit_s\":"<<(std::min)(PoreDt,TestDt-FixedDt->GetDtError(false))
      <<",\"mass\":"<<double(MassFluid)<<",\"period\":"<<fabs(PeriXinc.x)<<",\"kernel_h\":"<<double(CSP.kernelh)
      <<",\"support\":"<<double(KernelSize)<<",\"bwen\":"<<double(CSP.kwend.bwen)<<",\"shear\":"<<double(SoilCte.ModulusG)
      <<",\"history_integrator\":\"production_endpoint_trapezoidal_r2\",\"last_rate_phase\":\"corrected_endpoint\""
      <<",\"csv_rate_phase\":\"corrected_endpoint\",\"xi_zero_bypasses_hg_allocation\":"<<(!HourglassCpu?"true":"false")
      <<",\"neighbor_audit_performed_in_this_run\":false,\"logged_hg_ls_gradient_is_not_production_stress_or_pore_gradient\":true"
      <<",\"history_rotation_objective\":false,\"coupled_hg_stability_proven\":false,\"physical_accuracy_accepted\":false}\n";
    done.flush();Check(bool(done),"HG completion write failed");
  }
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,unsigned steps,unsigned stride,bool save){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(cfg->SvTimers);Timersc->TmStart(TMC_Init);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunCpu();
    Check(TStep==STEP_Symplectic&&HydroMech&&Simulate2D&&!PartBegin&&TimeStep==0,"Requires fresh case-02 Symplectic run");
    Check(!CaseNmoving&&!CaseNfloat&&!InOut&&!ViscoTime&&!DDTRamp.x&&!Shifting&&!Damping&&!RelaxZones,"Unsupported case-02 outer-loop branch");
    Check(HydroMechTopLoadMode==HMLOAD_TopVertical||HydroMechTopLoadMode==HMLOAD_TopKernelBand,"Requires case-02 top load");
    Check(Gravity.x==0&&Gravity.y==0&&Gravity.z==0&&HydroMechTopLoadQ0==10000,"Requires retained case-02 loading");
    Check(FixedDt&&(FixedDt->GetFixedValue()==1e-5||FixedDt->GetFixedValue()==5e-6),"XML must define constant regression dt");
    TestDt=FixedDt->GetFixedValue();Check(SymplecticDtPre==TestDt&&DtMin<=TestDt,"Initial dt must match fixed dt");
    Check(steps*TestDt<=TimeMax+TestDt,"Requested steps exceed XML TimeMax");
    Check((HourglassCpu!=NULL)==(SoilHourglassXi>0),"HG allocation does not match XML coefficient");
    const double kwn=double(SoilCte.PoreWaterBulkModulus)/double(SoilCte.Porosity);
    PoreDt=double(PoreDtSafety)*(double(SoilCte.PoreWaterRho)*9.80665/kwn)*double(KernelH)*double(KernelH)/double(SoilCte.HydraulicConductivity);
    Check(std::isfinite(PoreDt)&&TestDt<=PoreDt,"Fixed dt exceeds pore diffusion limit");
    RunGaugeSystem(TimeStep,true);FreePartsInit();UpdateMaxValues();
    if(save){SaveData();Saved++;}
    Timersc->ResetTimes();Timersc->TmStop(TMC_Init);PartNstep=-1;Part++;
    FixedDt->GetDtError(true); // Only reset the diagnostic maximum, never dt/state.
    const fs::path out(cfg->DirOut);WriteState("initial_state");
    state.open(out/"state.csv");state<<std::setprecision(17)
      <<"time_s,step,stage,id,x,y,z,vx,vy,vz,rho,pressure,sigma_xx,sigma_yy,sigma_zz,sigma_xy,sigma_yz,sigma_xz,kplastic,load_az,fstype,normal_z,drained,single_loaded\n";
    if(HourglassCpu){hglog.open(out/"hourglass.csv");hglog<<std::setprecision(17)
      <<"time_s,step,stage,xi,dt_s,pairs,net_rate_x_N_m_s,net_rate_z_N_m_s,sum_abs_pair_rate_N_m_s,rate_power,rate_form,work_identity_error,max_rate_m_s3,ls_condition,max_skew_s_1,hg_ls_mean_dxx_s_1,hg_ls_rms_dxx_s_1,hg_ls_mean_div_s_1,hg_ls_rms_div_s_1,lambda_bound_s_2,tau_s,dt_over_tau,min_natural_dt_limit_s,integrated_max_skew_rad,max_history_accel_m_s2,max_net_hg_force_N_m,max_actual_float_add_net_force_N_m\n";}
    Sample();TimerSim.Start();TimerPart.Start();
    for(unsigned step=0;step<steps;step++){
      InterStep=INTERSTEP_SymPredictor;
      const double dt=ComputeStep_Sym(); // The sole numerical step implementation.
      Check(dt==TestDt&&FixedDt->GetDtError(false)<=0,"Changed dt or fixed dt exceeds mechanical natural limit");
      RunGaugeSystem(TimeStep+dt);RunCellDivide(true);TimeStep+=dt;LastDt=dt;
      const unsigned completed=step+1;
      if(completed%stride==0||completed==steps){
        if(save){SaveData();Saved++;Part++;PartNstep=Nstep;TimeStepM1=TimeStep;TimePartNext=TimeStep+stride*TestDt;TimerPart.Start();}
      }
      UpdateMaxValues();Nstep++;
      if(completed%stride==0||completed==steps){
        Sample();std::cout<<"PROGRESS steps="<<completed<<" time="<<std::setprecision(17)<<TimeStep<<'\n';std::cout.flush();
      }
    }
    TimerSim.Stop();WriteState("final_state");WriteHgFinal(steps);
    std::ofstream done(out/"complete.json");done<<std::setprecision(17)
      <<"{\"mode\":\"production_symplectic\",\"steps\":"<<steps<<",\"stride\":"<<stride<<",\"dt\":"<<TestDt
      <<",\"initial_time\":0,\"final_time\":"<<TimeStep<<",\"native_step_calls\":"<<steps
      <<",\"snapshot_part\":0,\"normal_soil\":1000,\"xi\":"<<SoilHourglassXi
      <<",\"stress_grad_corr\":"<<(SoilStressRateGradCorr?"true":"false")<<",\"top_load_mode\":"<<unsigned(HydroMechTopLoadMode)
      <<",\"save_parts\":"<<(save?"true":"false")<<",\"saved_parts\":"<<Saved<<",\"sampled_frames\":"<<Samples
      <<",\"elapsed_seconds\":"<<TimerSim.GetElapsedTimeD()/1000.<<",\"max_fixed_dt_minus_mechanical_limit_s\":"<<FixedDt->GetDtError(false)
      <<",\"pore_dt_limit_s\":"<<PoreDt<<",\"sample_stage\":\"full_step\",\"boundary_diagnostic_phase\":\"last_corrector_or_SaveData_classification_not_fresh_force\""
      <<",\"single_loaded_column\":\"material_top_layer_reference_not_actual_mode5_loaded_set\""
      <<",\"physical_configuration_overridden\":false,\"exact_hot_restart\":false,\"physical_accuracy_accepted\":false}\n";
    done.flush();Check(bool(done),"Production-path completion write failed");
    std::cout<<"COMPLETE production_symplectic steps="<<steps<<" time="<<TimeStep<<'\n';
  }
};

int main(int argc,char** argv){
  try{
    Check(argc>=8,"Usage: hg_merge STEPS STRIDE SAVE then ordinary solver arguments");
    const unsigned steps=unsigned(std::stoul(argv[1])),stride=unsigned(std::stoul(argv[2]));const int save=std::stoi(argv[3]);
    Check(steps>0&&steps<=15000000&&stride>0&&(save==0||save==1),"Invalid step, stride, or save flag");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);
    JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());cfg.Cpu=true;
    cfg.Sv_Binx=cfg.Sv_Info=(save!=0);cfg.Sv_Csv=cfg.Sv_Vtk=false;if(save)cfg.SvExtraParts="1";
    Check(!fs::exists(cfg.DirOut),"Output exists; choose a new label");
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    ProductionMergeCheck fixture;fixture.Execute(&cfg,AppInfo.LogPtr(),steps,stride,save!=0);return 0;
  }
  catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Production exception; inspect Run.out\n";return 2;}
}
