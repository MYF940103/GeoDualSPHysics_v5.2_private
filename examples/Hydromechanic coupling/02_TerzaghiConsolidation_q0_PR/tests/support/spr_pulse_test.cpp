// Nonzero short transient using the sole production Symplectic step.
#define main RetainedSprPlanesDiagnosticMain
#include "spr_planes_test.cpp"
#undef main
#include "JDsFixedDt.h"

class SprPulseCheck:public JSphCpuSingle{
public:
  void Execute(const JSphCfgRun *cfg,JLog2 *log,unsigned steps,unsigned stride){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(cfg->SvTimers);Timersc->TmStart(TMC_Init);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunCpu();FreePartsInit();
    Check(HydroMech&&Simulate2D&&FixedDt&&!HourglassCpu&&!PeriActive,"Unexpected pulse configuration");
    if(NoPenetration){
      for(unsigned p=Npb;p<Np;p++)Posc[p]=Posc[p]-TDouble3(.003,0,.003);
      LoadDcellParticles(Np,Codec,Posc,Dcellc);RunCellDivide(true);
    }
    const unsigned count=Np;
    for(unsigned p=0;p<Np;p++){
      if(CODE_IsFluid(Codec[p]))Velrhopc[p]=TFloat4(float(-.001*Posc[p].x),0,float(-.001*Posc[p].z),RhopZero);
      PorePressc[p]=PorePress0c[p]=0;Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;
    }
    std::ofstream rows(fs::path(cfg->DirOut)/"pulse.csv"),history(fs::path(cfg->DirOut)/"energy.csv");
    rows<<std::setprecision(17)<<"time_s,step,id,x,z,vx,vz,rho,pressure,sxx,syy,szz,sxy,syz,sxz,kplastic\n";
    history<<std::setprecision(17)<<"time_s,step,kinetic_J_m,elastic_J_m,pore_J_m,total_J_m\n";
    auto sample=[&](){
      Check(Np==count,"Pulse excluded a native particle");
      double kinetic=0,elastic=0,water=0;
      for(unsigned p=Npb;p<Np;p++){
        const tfloat4 v=Velrhopc[p];const tsymatrix3d s=Sigmac[p];const double pw=PorePressc[p],vol=MassFluid/double(v.w);
        Check(CODE_IsNormal(Codec[p])&&std::isfinite(pw)&&std::isfinite(v.w)&&v.w>0&&Kplasticc[p]==0,"Invalid pulse state");
        rows<<TimeStep<<','<<Nstep<<','<<Idpc[p]<<','<<Posc[p].x<<','<<Posc[p].z<<','<<v.x<<','<<v.z<<','<<v.w<<','<<pw<<','<<s.xx<<','<<s.yy<<','<<s.zz<<','<<s.xy<<','<<s.yz<<','<<s.xz<<','<<Kplasticc[p]<<'\n';
        kinetic+=.5*MassFluid*(double(v.x)*v.x+double(v.z)*v.z);
        const double square=s.xx*s.xx+s.yy*s.yy+s.zz*s.zz+2*(s.xy*s.xy+s.yz*s.yz+s.xz*s.xz),trace=s.xx+s.yy+s.zz;
        elastic+=vol*((1+SoilCte.PRvs)*square-SoilCte.PRvs*trace*trace)/(2*SoilCte.ModulusE);
        water+=vol*SoilCte.Porosity*pw*pw/(2*SoilCte.PoreWaterBulkModulus);
      }
      history<<TimeStep<<','<<Nstep<<','<<kinetic<<','<<elastic<<','<<water<<','<<kinetic+elastic+water<<'\n';
    };
    const double fixed=FixedDt->GetFixedValue();FixedDt->GetDtError(true);sample();
    for(unsigned i=0;i<steps;i++){
      InterStep=INTERSTEP_SymPredictor;const double dt=ComputeStep_Sym();
      Check(dt==fixed&&FixedDt->GetDtError(false)<=0,"Pulse step violates natural mechanical limit");
      RunGaugeSystem(TimeStep+dt);RunCellDivide(true);TimeStep+=dt;LastDt=dt;Nstep++;
      if((i+1)%stride==0||i+1==steps)sample();
    }
    std::ofstream done(fs::path(cfg->DirOut)/"pulse_complete.json");
    done<<std::setprecision(17)<<"{\"completed\":true,\"steps\":"<<steps<<",\"actual_time_s\":"<<TimeStep
      <<",\"dt_s\":"<<fixed<<",\"native_count\":"<<count<<",\"production_integrator\":true,\"physical_acceptance\":false}\n";
  }
};

int main(int argc,char** argv){
  try{
    Check(argc>4,"Usage: pulse STEPS STRIDE then ordinary CPU arguments");
    const unsigned steps=std::stoul(argv[1]),stride=std::stoul(argv[2]);Check(steps&&stride,"Invalid pulse sampling");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> arguments{argv[0]};for(int i=3;i<argc;i++)arguments.push_back(argv[i]);
    JSphCfgRun cfg;cfg.LoadArgv(int(arguments.size()),arguments.data());cfg.Cpu=true;cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;
    Check(!fs::exists(cfg.DirOut),"Choose a new pulse label");
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    SprPulseCheck fixture;fixture.Execute(&cfg,AppInfo.LogPtr(),steps,stride);return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Production exception; inspect Run.out\n";return 2;}
}
