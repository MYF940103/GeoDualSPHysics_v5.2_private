// Reuse the retained production-step harness; never copy its integrator.
#define main RetainedProductionMergeMain
#include "hg_merge_harness.cpp"
#undef main

class ReleaseIntegrationCheck:public ProductionMergeCheck{
public:
  void WriteReleaseInfo()const{
    const auto stats=(HourglassCpu? HourglassCpu->GetStats(): JSphHourglassCpu::StStats{});
    const fs::path path=fs::path(CfgRun->DirOut)/"release_integration.json";
    std::ofstream out(path);out<<std::setprecision(17)
      <<"{\"spr_enabled\":"<<(SoilBoundaryDerivativeSPR?"true":"false")
      <<",\"fixed_grid_drainage\":"<<(HydroMechDrainageFixedGrid?"true":"false")
      <<",\"rate_logical_calls\":"<<stats.ratecalls
      <<",\"rate_calculations\":"<<stats.ratecalculations
      <<",\"rate_cache_hits\":"<<stats.ratecachehits
      <<",\"actual_final_time_s\":"<<TimeStep
      <<",\"production_step_used\":true,\"physical_acceptance_claimed\":false}\n";
    out.flush();Check(bool(out),"Release integration metadata write failed");
  }
};

int main(int argc,char** argv){
  try{
    Check(argc>=8,"Usage: hg_release STEPS STRIDE SAVE then ordinary solver arguments");
    const unsigned steps=unsigned(std::stoul(argv[1])),stride=unsigned(std::stoul(argv[2]));
    const int save=std::stoi(argv[3]);
    Check(steps>0&&steps<=15000000&&stride>0&&(save==0||save==1),"Invalid step, stride, or save flag");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};
    for(int i=4;i<argc;i++)args.push_back(argv[i]);
    JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());cfg.Cpu=true;
    cfg.Sv_Binx=cfg.Sv_Info=(save!=0);cfg.Sv_Csv=cfg.Sv_Vtk=false;if(save)cfg.SvExtraParts="1";
    Check(!fs::exists(cfg.DirOut),"Output exists; choose a new label");
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);
    AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    ReleaseIntegrationCheck fixture;fixture.Execute(&cfg,AppInfo.LogPtr(),steps,stride,save!=0);
    fixture.WriteReleaseInfo();return 0;
  }
  catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Production exception; inspect Run.out\n";return 2;}
}
