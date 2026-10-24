// Observe the existing NoPen production operator, without enabling SPR.
#define main RetainedSprPlanesDiagnosticMain
#include "spr_planes_test.cpp"
#undef main

class NoPenOperatorCheck:public JSphCpuSingle{
public:
  void Execute(const JSphCfgRun *cfg,JLog2 *log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(cfg->SvTimers);Timersc->TmStart(TMC_Init);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunCpu();FreePartsInit();
    Check(NoPenetration&&TMdbc2==MDBC2_NoPen&&!HourglassCpu,"Expected original NoPen");
    const tdouble3 raw=ToTDouble3(BoundNormalc[0]);
    const tdouble3 normal=raw/sqrt(raw.x*raw.x+raw.y*raw.y+raw.z*raw.z);
    const tdouble3 tangent=TDouble3(normal.z,0,-normal.x);
    // Move the nearest soil layer from .005 to .002 m, still inside the wall,
    // so the existing proximity guard actually activates. Rebuild real cells.
    for(unsigned p=Npb;p<Np;p++)Posc[p]=Posc[p]-normal*.003;
    LoadDcellParticles(Np,Codec,Posc,Dcellc);RunCellDivide(true);
    std::ofstream rows(fs::path(cfg->DirOut)/"nopen.csv");
    rows<<std::setprecision(17)<<"trial,id,vn,shift_x,shift_z,shift_n,active\n";
    double tangentshift=0,normalshift=0;unsigned active=0;
    for(unsigned trial=0;trial<2;trial++){
      const tdouble3 velocity=(trial?normal*(-.01):tangent*.01);
      for(unsigned p=0;p<Np;p++){
        Velrhopc[p]=TFloat4(p<Npb?0:float(velocity.x),0,p<Npb?0:float(velocity.z),RhopZero);
        Sigmac[p]=tsymatrix3d{};PorePressc[p]=PorePress0c[p]=0;Kplasticc[p]=0;
      }
      InterStep=INTERSTEP_SymPredictor;MdbcBoundCorrection();PreInteraction_Forces();ComputeFreeSurfaceTracking();
      ComputeBoundaryDerivativeVelocity();
      const stinterparmsc parms=StInterparmsc(Np,Npb,NpbOk,DivData,Dcellc,Posc,Velrhopc,Idpc,Codec,Pressc,
        PorePressc,PorePressRatec,FSTypec,FSNormalc,NULL,CorrMatc,Arc,Acec,Deltac,ShiftingMode,ShiftPosfsc,
        SpsTauc,SpsGradvelc,Sigmac,Rsigmac,ArtificialStressc);
      StInterResultc result;result.viscdt=0;JSphCpu::Interaction_Forces_ct(parms,result);
      for(unsigned p=Npb;p<Np;p++){
        const tfloat4 s=NoPenShiftc[p];const double vn=normal.x*Velrhopc[p].x+normal.z*Velrhopc[p].z,sn=normal.x*s.x+normal.z*s.z;
        rows<<trial<<','<<Idpc[p]<<','<<vn<<','<<s.x<<','<<s.z<<','<<sn<<','<<(s.w>5)<<'\n';
        if(!trial){tangentshift=(std::max)(tangentshift,fabs(sn));if(s.w>5)active++;}
        else normalshift=(std::max)(normalshift,fabs(sn));
      }
      PosInteraction_Forces();
    }
    std::ofstream done(fs::path(cfg->DirOut)/"nopen_complete.json");done<<std::setprecision(17)
      <<"{\"completed\":true,\"spr_enabled\":"<<(SoilBoundaryDerivativeSPR?"true":"false")<<",\"max_pure_tangent_normal_shift_m_s\":"<<tangentshift
      <<",\"pure_tangent_active_count\":"<<active<<",\"max_inward_normal_shift_m_s\":"<<normalshift<<",\"normal\":["<<normal.x<<','<<normal.y<<','<<normal.z<<"]}\n";
  }
};
int main(int argc,char** argv){
  try{
    AppInfo.ConfigRunPaths(argv[0]);JSphCfgRun cfg;cfg.LoadArgv(argc,argv);cfg.Cpu=true;cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;
    Check(!fs::exists(cfg.DirOut),"Choose a fresh NoPen observation label");
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    NoPenOperatorCheck test;test.Execute(&cfg,AppInfo.LogPtr());return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Production exception; inspect Run.out\n";return 2;}
}
