// Three-dimensional transient observer: uses the unchanged production step.
#ifdef _WITHGPU
#define main RetainedSprGpuPlanesMain
#include "spr_gpu_planes_test.cpp"
#undef main
using PulseBase=JSphGpuSingle;
#else
#define main RetainedSprCpuPlanesMain
#include "spr_planes_test.cpp"
#undef main
using PulseBase=JSphCpuSingle;
#endif
#include "JDsFixedDt.h"

class Spr3dPulse:public PulseBase{
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,unsigned steps,unsigned stride){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;
#ifdef _WITHGPU
    SelecDevice(cfg->GpuId);Timersg->Config(false);Timersg->TmStart(TMG_Init,false);
#else
    Timersc->Config(false);Timersc->TmStart(TMC_Init);
#endif
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();
#ifdef _WITHGPU
    InitRunGpu();
    Check(!HourglassGpu,"HG must remain off");
#else
    InitRunCpu();
    Check(!HourglassCpu,"HG must remain off");
#endif
    FreePartsInit();
    Check(HydroMech&&!Simulate2D&&FixedDt&&!PeriActive&&!NoPenetration&&!SoilDamping
      &&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None,"Unexpected 3-D pulse controls");
    const unsigned count=Np;
#ifdef _WITHGPU
    const auto xy=Down(Posxyg,Np);const auto zz=Down(Poszg,Np);const auto code=Down(Codeg,Np);
    std::vector<float4> field(Np);
    for(unsigned p=0;p<Np;p++)field[p]=CODE_IsFluid(code[p])?make_float4(float(-.001*xy[p].x),float(-.0007*xy[p].y),float(-.0013*zz[p]),RhopZero):make_float4(0,0,0,RhopZero);
    Up(Velrhopg,field);Cu(cudaMemset(PorePressg,0,Np*sizeof(float)));Cu(cudaMemset(PorePress0g,0,Np*sizeof(float)));
    Cu(cudaMemset(Sigmag,0,Np*sizeof(tsymatrix3d)));Cu(cudaMemset(Kplasticg,0,Np*sizeof(float)));
#else
    for(unsigned p=0;p<Np;p++){
      if(CODE_IsFluid(Codec[p]))Velrhopc[p]=TFloat4(float(-.001*Posc[p].x),float(-.0007*Posc[p].y),float(-.0013*Posc[p].z),RhopZero);
      PorePressc[p]=PorePress0c[p]=0;Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;
    }
#endif
    std::ofstream rows(fs::path(cfg->DirOut)/"pulse.csv"),history(fs::path(cfg->DirOut)/"energy.csv");
    rows<<std::setprecision(17)<<"time_s,step,id,x,y,z,vx,vy,vz,rho,pressure,sxx,syy,szz,sxy,syz,sxz,kplastic\n";
    history<<std::setprecision(17)<<"time_s,step,kinetic_J,elastic_J,pore_J,total_J\n";
    auto sample=[&](){
      Check(Np==count,"Native particle excluded");
#ifdef _WITHGPU
      const auto id=Down(Idpg,Np);const auto code=Down(Codeg,Np);const auto xy=Down(Posxyg,Np);const auto z=Down(Poszg,Np);
      const auto velocity=Down(Velrhopg,Np);const auto sigma=Down(Sigmag,Np);const auto pressure=Down(PorePressg,Np),plastic=Down(Kplasticg,Np);
#endif
      double kinetic=0,elastic=0,water=0;
      for(unsigned p=Npb;p<Np;p++){
#ifdef _WITHGPU
        const unsigned pid=id[p];const tdouble3 pos=TDouble3(xy[p].x,xy[p].y,z[p]);
        const auto v=velocity[p];const auto s=sigma[p];const double pw=pressure[p],kp=plastic[p];const bool normal=CODE_IsNormal(code[p]);
#else
        const unsigned pid=Idpc[p];const tdouble3 pos=Posc[p];const auto v=Velrhopc[p];const auto s=Sigmac[p];
        const double pw=PorePressc[p],kp=Kplasticc[p];const bool normal=CODE_IsNormal(Codec[p]);
#endif
        Check(normal&&std::isfinite(pw)&&std::isfinite(v.w)&&v.w>0&&kp==0,"Invalid 3-D native state");
        rows<<TimeStep<<','<<Nstep<<','<<pid<<','<<pos.x<<','<<pos.y<<','<<pos.z<<','<<v.x<<','<<v.y<<','<<v.z<<','<<v.w<<','<<pw<<','
          <<s.xx<<','<<s.yy<<','<<s.zz<<','<<s.xy<<','<<s.yz<<','<<s.xz<<','<<kp<<'\n';
        const double vol=MassFluid/double(v.w),trace=s.xx+s.yy+s.zz;
        kinetic+=.5*MassFluid*(double(v.x)*v.x+double(v.y)*v.y+double(v.z)*v.z);
        const double square=s.xx*s.xx+s.yy*s.yy+s.zz*s.zz+2*(s.xy*s.xy+s.yz*s.yz+s.xz*s.xz);
        elastic+=vol*((1+SoilCte.PRvs)*square-SoilCte.PRvs*trace*trace)/(2*SoilCte.ModulusE);
        water+=vol*SoilCte.Porosity*pw*pw/(2*SoilCte.PoreWaterBulkModulus);
      }
      history<<TimeStep<<','<<Nstep<<','<<kinetic<<','<<elastic<<','<<water<<','<<kinetic+elastic+water<<'\n';
    };
    const double fixed=FixedDt->GetFixedValue();FixedDt->GetDtError(true);
    const double poredt=double(PoreDtSafety)*(double(SoilCte.PoreWaterRho)*9.80665*double(SoilCte.Porosity)/double(SoilCte.PoreWaterBulkModulus))*double(KernelH)*double(KernelH)/double(SoilCte.HydraulicConductivity);
    Check(fixed<=poredt,"Fixed step exceeds pore diffusion limit");sample();
    for(unsigned i=0;i<steps;i++){
      InterStep=INTERSTEP_SymPredictor;const double dt=ComputeStep_Sym();
      Check(dt==fixed&&FixedDt->GetDtError(false)<=0,"Step exceeds natural mechanical limit");
      RunGaugeSystem(TimeStep+dt);RunCellDivide(true);TimeStep+=dt;LastDt=dt;Nstep++;
      if((i+1)%stride==0||i+1==steps)sample();
    }
    std::ofstream done(fs::path(cfg->DirOut)/"pulse_complete.json");
    done<<std::setprecision(17)<<"{\"completed\":true,\"steps\":"<<steps<<",\"actual_time_s\":"<<TimeStep<<",\"dt_s\":"<<fixed<<",\"native_count\":"<<count
      <<",\"pore_dt_limit_s\":"<<poredt<<",\"max_fixed_dt_minus_mechanical_limit_s\":"<<FixedDt->GetDtError(false)<<",\"production_integrator\":true,\"physical_acceptance\":false}\n";
    done.flush();rows.flush();history.flush();Check(bool(done)&&bool(rows)&&bool(history),"Output failed");
  }
};

int main(int argc,char** argv){
  try{
    Check(argc>4,"Usage: spr_3d STEPS STRIDE then ordinary solver arguments");
    const unsigned steps=std::stoul(argv[1]),stride=std::stoul(argv[2]);Check(steps&&stride&&steps<=4000,"Invalid bounded pulse duration");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=3;i<argc;i++)args.push_back(argv[i]);
    JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());
#ifdef _WITHGPU
    cfg.Cpu=false;
#else
    cfg.Cpu=true;
#endif
    cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;Check(!fs::exists(cfg.DirOut),"Choose fresh output");
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    Spr3dPulse test;test.Execute(&cfg,AppInfo.LogPtr(),steps,stride);return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Production exception; inspect Run.out\n";return 2;}
}
