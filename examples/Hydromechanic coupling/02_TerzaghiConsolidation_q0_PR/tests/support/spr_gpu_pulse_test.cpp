// Same nonzero pulse as the CPU companion; sole production GPU integration.
#define main RetainedGpuPlanesDiagnosticMain
#include "spr_gpu_planes_test.cpp"
#undef main
#include "JDsFixedDt.h"

class SprGpuPulse:public JSphGpuSingle{
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,unsigned steps,unsigned stride){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;SelecDevice(cfg->GpuId);Timersg->Config(false);Timersg->TmStart(TMG_Init,false);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunGpu();FreePartsInit();
    Check(HydroMech&&Simulate2D&&FixedDt&&!HourglassGpu&&!PeriActive,"Unexpected pulse configuration");
    const unsigned count=Np;const auto xy=Down(Posxyg,Np);const auto z=Down(Poszg,Np);const auto code=Down(Codeg,Np);
    std::vector<float4> field(Np);
    for(unsigned p=0;p<Np;p++)field[p]=(CODE_IsFluid(code[p])?make_float4(float(-.001*xy[p].x),0,float(-.001*z[p]),RhopZero):make_float4(0,0,0,RhopZero));
    Up(Velrhopg,field);Cu(cudaMemset(PorePressg,0,Np*sizeof(float)));Cu(cudaMemset(PorePress0g,0,Np*sizeof(float)));
    Cu(cudaMemset(Sigmag,0,Np*sizeof(tsymatrix3d)));Cu(cudaMemset(Kplasticg,0,Np*sizeof(float)));
    std::ofstream rows(fs::path(cfg->DirOut)/"pulse.csv"),history(fs::path(cfg->DirOut)/"energy.csv");
    rows<<std::setprecision(17)<<"time_s,step,id,x,z,vx,vz,rho,pressure,sxx,syy,szz,sxy,syz,sxz,kplastic\n";
    history<<std::setprecision(17)<<"time_s,step,kinetic_J_m,elastic_J_m,pore_J_m,total_J_m\n";
    auto sample=[&](){
      Check(Np==count,"Pulse excluded a native particle");
      const auto id=Down(Idpg,Np);const auto codes=Down(Codeg,Np);const auto x=Down(Posxyg,Np);const auto zz=Down(Poszg,Np);
      const auto v=Down(Velrhopg,Np);const auto s=Down(Sigmag,Np);const auto pw=Down(PorePressg,Np),kp=Down(Kplasticg,Np);
      double kinetic=0,elastic=0,water=0;
      for(unsigned p=Npb;p<Np;p++){
        Check(CODE_IsNormal(codes[p])&&std::isfinite(pw[p])&&std::isfinite(v[p].w)&&v[p].w>0&&kp[p]==0,"Invalid pulse state");
        rows<<TimeStep<<','<<Nstep<<','<<id[p]<<','<<x[p].x<<','<<zz[p]<<','<<v[p].x<<','<<v[p].z<<','<<v[p].w<<','<<pw[p]<<','
          <<s[p].xx<<','<<s[p].yy<<','<<s[p].zz<<','<<s[p].xy<<','<<s[p].yz<<','<<s[p].xz<<','<<kp[p]<<'\n';
        const double vol=MassFluid/double(v[p].w);
        kinetic+=.5*MassFluid*(double(v[p].x)*v[p].x+double(v[p].z)*v[p].z);
        const double square=s[p].xx*s[p].xx+s[p].yy*s[p].yy+s[p].zz*s[p].zz+2*(s[p].xy*s[p].xy+s[p].yz*s[p].yz+s[p].xz*s[p].xz),trace=s[p].xx+s[p].yy+s[p].zz;
        elastic+=vol*((1+SoilCte.PRvs)*square-SoilCte.PRvs*trace*trace)/(2*SoilCte.ModulusE);
        water+=vol*SoilCte.Porosity*double(pw[p])*pw[p]/(2*SoilCte.PoreWaterBulkModulus);
      }
      history<<TimeStep<<','<<Nstep<<','<<kinetic<<','<<elastic<<','<<water<<','<<kinetic+elastic+water<<'\n';
    };
    const double fixed=FixedDt->GetFixedValue();FixedDt->GetDtError(true);sample();
    const double poredt=double(PoreDtSafety)*(double(SoilCte.PoreWaterRho)*9.80665*double(SoilCte.Porosity)/double(SoilCte.PoreWaterBulkModulus))*double(KernelH)*double(KernelH)/double(SoilCte.HydraulicConductivity);
    Check(fixed<=poredt,"Pulse fixed step exceeds pore diffusion limit");
    for(unsigned i=0;i<steps;i++){
      InterStep=INTERSTEP_SymPredictor;const double dt=ComputeStep_Sym();
      Check(dt==fixed&&FixedDt->GetDtError(false)<=0,"Pulse step exceeds natural mechanical limit");
      RunGaugeSystem(TimeStep+dt);RunCellDivide(true);TimeStep+=dt;LastDt=dt;Nstep++;
      if((i+1)%stride==0||i+1==steps)sample();
    }
    std::ofstream done(fs::path(cfg->DirOut)/"pulse_complete.json");
    done<<std::setprecision(17)<<"{\"completed\":true,\"steps\":"<<steps<<",\"actual_time_s\":"<<TimeStep<<",\"dt_s\":"<<fixed<<",\"native_count\":"<<count
      <<",\"pore_dt_limit_s\":"<<poredt<<",\"max_fixed_dt_minus_mechanical_limit_s\":"<<FixedDt->GetDtError(false)<<",\"production_integrator\":true,\"physical_acceptance\":false}\n";
    done.flush();rows.flush();history.flush();Check(bool(done)&&bool(rows)&&bool(history),"Pulse output failed");
  }
};

int main(int argc,char** argv){
  try{
    Check(argc>4,"Usage: spr_gpu_pulse STEPS STRIDE then ordinary GPU arguments");
    const unsigned steps=std::stoul(argv[1]),stride=std::stoul(argv[2]);Check(steps&&stride,"Invalid pulse sampling");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=3;i<argc;i++)args.push_back(argv[i]);
    JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());cfg.Cpu=false;cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;
    Check(!fs::exists(cfg.DirOut),"Choose a new pulse label");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    SprGpuPulse fixture;fixture.Execute(&cfg,AppInfo.LogPtr(),steps,stride);return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Production exception; inspect Run.out\n";return 2;}
}
