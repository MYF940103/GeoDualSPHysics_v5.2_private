// Case-02 GPU companion: call the production integrator and sample integer steps.
#include "JSphGpuSingle.h"
#include "JSphHourglassGpu.h"
#include "JSphCfgRun.h"
#include "JDsFixedDt.h"
#include "JDsTimersGpu.h"
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

JAppInfo AppInfo("GpuCoupledCheck","v1","18-10-2026");
namespace fs=std::filesystem;
static void Check(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
class GpuCoupledCheck:public JSphGpuSingle{
  std::ofstream State,Hg;
  unsigned Samples=0;
  double Dt=0;
  void Sample(){
    const unsigned count=ParticlesDataDown(Np,0,true,true);
    Check(count==1040,"Missing/excluded native particles");std::map<unsigned,unsigned> order;
    for(unsigned p=0;p<count;p++)Check(order.emplace(Idp[p],p).second,"Duplicate native ID");
    Check(order.size()==1040&&order.begin()->first==0&&order.rbegin()->first==1039,"Native set changed");
    unsigned soil=0;
    for(const auto& item:order)if(item.first>=40){
      soil++;const unsigned p=item.second;const auto x=AuxPos[p];const auto v=AuxVel[p];const auto s=Sigma[p];
      const std::array<double,6> stress{{s.xx,s.yy,s.zz,s.xy,s.yz,s.xz}};
      Check(CODE_IsFluid(Code[p])&&std::isfinite(x.x)&&std::isfinite(x.y)&&std::isfinite(x.z)
        &&std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z)&&std::isfinite(AuxRhop[p])&&AuxRhop[p]>0
        &&std::isfinite(PorePress[p])&&Kplastic[p]==0,"Nonfinite or nonelastic soil");
      State<<TimeStep<<','<<Nstep<<",full_step,"<<item.first<<','<<x.x<<','<<x.y<<','<<x.z<<','<<v.x<<','<<v.y<<','<<v.z<<','<<AuxRhop[p]<<','<<PorePress[p];
      for(double a:stress){Check(std::isfinite(a),"Nonfinite double stress");State<<','<<a;}
      State<<','<<Kplastic[p]<<','<<(Nstep?AuxHydroMechLoadAce[p].z:0.f)<<','<<AuxFSType[p]<<','<<AuxFSNormal[p].z
        <<','<<(IsHydroMechDrainageActive()&&(AuxFSType[p]==FST_FreeSurface||AuxFSType[p]==FST_Isolated)?1:0)
        <<','<<((item.first-40)%100==99&&TimeStep>0?1:0)<<'\n';
    }
    Check(soil==1000,"Soil population changed");State.flush();Check(bool(State),"State output failed");Samples++;
    if(Nstep){
      const auto& r=HourglassGpu->GetRateInfo();const auto& s=HourglassGpu->GetStats();
      Hg<<TimeStep<<','<<Nstep<<','<<r.ratepower<<','<<r.form<<','<<r.workerror<<','<<r.rmax<<','<<r.condition<<','<<r.skew
        <<','<<r.meandxx/1000<<','<<sqrt(r.rmsdxx/1000)<<','<<r.meandiv/1000<<','<<sqrt(r.rmsdiv/1000)
        <<','<<r.lambda<<','<<r.tau<<','<<Dt/r.tau<<','<<s.spinbound<<','<<s.maxhistory<<','<<s.maxnetforce<<','<<s.maxactualnetforce<<'\n';
      Hg.flush();Check(bool(Hg),"HG sample output failed");
    }
  }
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,unsigned steps,unsigned stride,bool save){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;SelecDevice(cfg->GpuId);Timersg->Config(cfg->SvTimers);Timersg->TmStart(TMG_Init,false);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunGpu();
    Check(Simulate2D&&HydroMech&&!PartBegin&&HourglassGpu&&SoilBoundaryDerivativeSPR&&HydroMechDrainageFixedGrid,"Wrong coupled configuration");
    Check(!CaseNmoving&&!CaseNfloat&&!InOut&&!Shifting&&!Damping&&!RelaxZones&&HydroMechTopLoadMode==HMLOAD_TopKernelBand,"Unsupported outer-loop branch");
    Check(Gravity.x==0&&Gravity.y==0&&Gravity.z==0&&HydroMechTopLoadQ0==10000,"Wrong loading");
    Check(FixedDt&&(FixedDt->GetFixedValue()==1e-5||FixedDt->GetFixedValue()==5e-6),"Wrong fixed dt");
    Dt=FixedDt->GetFixedValue();Check(SymplecticDtPre==Dt&&steps*Dt<=TimeMax+Dt,"Initial dt/duration mismatch");
    RunGaugeSystem(TimeStep,true);FreePartsInit();UpdateMaxValues();
    if(save){SaveData();Part++;}PartNstep=-1;FixedDt->GetDtError(true);
    const fs::path out(cfg->DirOut);State.open(out/"state.csv");State<<std::setprecision(17)
      <<"time_s,step,stage,id,x,y,z,vx,vy,vz,rho,pressure,sigma_xx,sigma_yy,sigma_zz,sigma_xy,sigma_yz,sigma_xz,kplastic,load_az,fstype,normal_z,drained,single_loaded\n";
    Hg.open(out/"hourglass.csv");Hg<<std::setprecision(17)
      <<"time_s,step,rate_power,rate_form,work_identity_error,max_rate_m_s3,ls_condition,max_skew_s_1,hg_ls_mean_dxx_s_1,hg_ls_rms_dxx_s_1,hg_ls_mean_div_s_1,hg_ls_rms_div_s_1,lambda_bound_s_2,tau_s,dt_over_tau,integrated_max_skew_rad,max_history_accel_m_s2,max_net_hg_force_N_m,max_actual_float_add_net_force_N_m\n";
    Sample();TimerSim.Start();
    for(unsigned step=0;step<steps;step++){
      InterStep=INTERSTEP_SymPredictor;
      const double dt=ComputeStep_Sym();
      Check(dt==Dt&&FixedDt->GetDtError(false)<=0,"Fixed dt exceeds natural limit or changed");
      RunGaugeSystem(TimeStep+dt);RunCellDivide(true);TimeStep+=dt;LastDt=dt;UpdateMaxValues();
      if((step+1)%stride==0||step+1==steps){
        if(save){SaveData();Part++;PartNstep=Nstep;TimeStepM1=TimeStep;TimePartNext=TimeStep+stride*Dt;}
      }
      Nstep++;
      if((step+1)%stride==0||step+1==steps){
        Sample();std::cout<<"PROGRESS steps="<<Nstep<<" time="<<std::setprecision(17)<<TimeStep<<'\n';std::cout.flush();
      }
    }
    TimerSim.Stop();const auto& s=HourglassGpu->GetStats();
    Check(s.forcecalls==2*steps&&s.ratecalls==2*steps&&s.predictorupdates==steps&&s.correctorupdates==steps,"Incomplete GPU HG lifecycle");
    std::ofstream hist(out/"hourglass_final.csv");hist<<std::setprecision(17)<<"id,hg_ax_m_s2,hg_az_m_s2,last_rate_x_m_s3,last_rate_z_m_s3\n";
    for(unsigned id=40;id<1040;id++){const auto h=HourglassGpu->GetHistory(id),r=HourglassGpu->GetRate(id);hist<<id<<','<<h.x<<','<<h.z<<','<<r.x<<','<<r.z<<'\n';}
    std::ofstream done(out/"complete.json");done<<std::setprecision(17)
      <<"{\"completed\":true,\"steps\":"<<steps<<",\"dt\":"<<Dt<<",\"stride\":"<<stride<<",\"sampled_frames\":"<<Samples
      <<",\"final_time\":"<<TimeStep<<",\"elapsed_seconds\":"<<TimerSim.GetElapsedTimeD()/1000.
      <<",\"max_fixed_dt_minus_mechanical_limit_s\":"<<FixedDt->GetDtError(false)<<",\"force_calls\":"<<s.forcecalls
      <<",\"rate_calls\":"<<s.ratecalls<<",\"rate_calculations\":"<<s.ratecalculations<<",\"rate_cache_hits\":"<<s.ratecachehits
      <<",\"max_dt_over_tau\":"<<s.maxtauratio<<",\"spin_bound\":"<<s.spinbound<<",\"max_net_hg_force\":"<<s.maxnetforce
      <<",\"max_actual_net_hg_force\":"<<s.maxactualnetforce<<",\"production_step_used\":true,\"physical_acceptance\":false}\n";
    hist.flush();done.flush();Check(bool(hist)&&bool(done),"Completion output failed");
  }
};
int main(int argc,char** argv){
  try{
    Check(argc>=8,"Use STEPS STRIDE SAVE then ordinary solver arguments");
    const unsigned steps=std::stoul(argv[1]),stride=std::stoul(argv[2]);const bool save=std::stoi(argv[3])!=0;
    Check(steps>0&&stride>0,"Positive step counts required");AppInfo.ConfigRunPaths(argv[0]);
    std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);
    JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());cfg.Cpu=false;cfg.Sv_Binx=cfg.Sv_Info=save;cfg.Sv_Csv=cfg.Sv_Vtk=false;
    Check(!fs::exists(cfg.DirOut),"Output already exists");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    GpuCoupledCheck check;check.Execute(&cfg,AppInfo.LogPtr(),steps,stride,save);return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Production exception, inspect Run.out\n";return 2;}
}
