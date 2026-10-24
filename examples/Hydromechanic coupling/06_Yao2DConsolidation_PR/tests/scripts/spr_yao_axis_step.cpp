// Axis-NoPen Yao companion. Only save/stop scheduling differs from production.
#ifdef _WITHGPU
#include "JSphGpuSingle.h"
#include "JDsTimersGpu.h"
using SphBase=JSphGpuSingle;
#else
#include "JSphCpuSingle.h"
#include "JDsTimersCpu.h"
using SphBase=JSphCpuSingle;
#endif
#include "JSphCfgRun.h"
#include "JDsFixedDt.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>

JAppInfo AppInfo("YaoAxisNoPenStepCheck","v1","24-10-2026");
namespace fs=std::filesystem;
static void Check(bool okay,const char* message){if(!okay)throw std::runtime_error(message);}

class YaoAxisCheck:public SphBase{
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,unsigned steps,unsigned stride){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;
#ifdef _WITHGPU
    SelecDevice(cfg->GpuId);Timersg->Config(cfg->SvTimers);Timersg->TmStart(TMG_Init,false);
#else
    Timersc->Config(cfg->SvTimers);Timersc->TmStart(TMC_Init);
#endif
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();
#ifdef _WITHGPU
    InitRunGpu();Check(!HourglassGpu,"HG must be off");
#else
    InitRunCpu();Check(!HourglassCpu,"HG must be off");
#endif
    Check(TStep==STEP_Symplectic&&HydroMech&&Simulate2D&&!PartBegin&&TimeStep==0,"Requires fresh 2D hydromechanical Symplectic run");
    Check(!CaseNmoving&&!CaseNfloat&&!InOut&&!ViscoTime&&!DDTRamp.x&&!Shifting&&!Damping&&!RelaxZones&&!PeriActive,"Unsupported diagnostic outer-loop branch");
    Check(NoPenetration&&SoilBoundaryDerivativeSPR&&FixedDt&&HydroMechTopLoadMode==HMLOAD_TopStripVertical,"Requires Yao strip load, SPR and existing axis-NoPen");
    const double fixed=FixedDt->GetFixedValue();
    Check(SymplecticDtPre==fixed&&steps*fixed<=TimeMax+1e-12,"Initial dt or requested duration mismatch");
    const double poredt=double(PoreDtSafety)*(double(SoilCte.PoreWaterRho)*9.80665*double(SoilCte.Porosity)/double(SoilCte.PoreWaterBulkModulus))*double(KernelH)*double(KernelH)/double(SoilCte.HydraulicConductivity);
    Check(std::isfinite(poredt)&&fixed<=poredt,"Fixed step exceeds pore diffusion limit");
    RunGaugeSystem(TimeStep,true);FreePartsInit();UpdateMaxValues();SaveData();
    const unsigned count=Np;unsigned saved=1;
#ifdef _WITHGPU
    Timersg->ResetTimes();Timersg->TmStop(TMG_Init,false);
#else
    Timersc->ResetTimes();Timersc->TmStop(TMC_Init);
#endif
    PartNstep=-1;Part++;FixedDt->GetDtError(true);TimerSim.Start();TimerPart.Start();
    for(unsigned i=0;i<steps;i++){
      InterStep=INTERSTEP_SymPredictor;const double dt=ComputeStep();
      Check(dt==fixed&&FixedDt->GetDtError(false)<=0,"Changed dt or mechanical natural-step limit exceeded");
      RunGaugeSystem(TimeStep+dt);RunCellDivide(true);TimeStep+=dt;LastDt=dt;
      Check(Np==count,"Native particle excluded during diagnostic");
      const unsigned completed=i+1;
      if(completed%stride==0||completed==steps){
        SaveData();saved++;Part++;PartNstep=Nstep;TimeStepM1=TimeStep;
        TimePartNext=TimeStep+stride*fixed;TimerPart.Start();
      }
      UpdateMaxValues();Nstep++;
      if(completed%stride==0||completed==steps){std::cout<<"PROGRESS steps="<<completed<<" time="<<std::setprecision(17)<<TimeStep<<'\n';std::cout.flush();}
    }
    TimerSim.Stop();std::ofstream done(fs::path(cfg->DirOut)/"step_complete.json");
    done<<std::setprecision(17)<<"{\"completed\":true,\"production_integrator\":true,\"integer_step_save_only\":true,\"no_penetration\":true,\"spr\":true,\"steps\":"<<steps
      <<",\"stride\":"<<stride<<",\"dt_s\":"<<fixed<<",\"actual_time_s\":"<<TimeStep<<",\"native_count\":"<<count
      <<",\"saved_frames\":"<<saved<<",\"pore_dt_limit_s\":"<<poredt<<",\"loop_seconds\":"<<TimerSim.GetElapsedTimeD()/1000.<<",\"physical_acceptance\":false}\n";
    done.flush();Check(bool(done),"Completion receipt write failed");
  }
};

int main(int argc,char** argv){
  try{
    Check(argc>=6,"Usage: axis_step STEPS STRIDE then ordinary solver arguments");
    const unsigned steps=unsigned(std::stoul(argv[1])),stride=unsigned(std::stoul(argv[2]));
    Check(steps&&stride&&steps<=1000000,"Invalid bounded diagnostic duration");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=3;i<argc;i++)args.push_back(argv[i]);
    JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());
#ifdef _WITHGPU
    cfg.Cpu=false;
#else
    cfg.Cpu=true;
#endif
    cfg.Sv_Binx=cfg.Sv_Info=true;cfg.Sv_Csv=cfg.Sv_Vtk=false;cfg.SvExtraParts="1";
    Check(!fs::exists(cfg.DirOut),"Output exists; choose a fresh label");
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    YaoAxisCheck fixture;fixture.Execute(&cfg,AppInfo.LogPtr(),steps,stride);return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Production exception; inspect Run.out\n";return 2;}
}
