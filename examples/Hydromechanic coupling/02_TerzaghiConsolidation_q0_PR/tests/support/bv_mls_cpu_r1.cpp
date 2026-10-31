// Additional real mDBC/SPR consumers and force-stage observation; no integration.
// Reuse the frozen fixture's public utility types, never copy its MLS/neighbours.
#define main RetainedMdbcVectorDiagnosticMain
#include "mdbc_vector_test.cpp"
#undef main

struct BvRates{std::vector<float> rho,pore;std::vector<tsymatrix3f> sigma;};
struct BvPhysical{
  std::vector<tdouble3> pos;std::vector<tfloat4> velocity;std::vector<tsymatrix3d> sigma;
  std::vector<float> pressure,reference;std::vector<unsigned> ids;
};
class BvMlsCheck:public JSphCpuSingle{
  unsigned Dim;std::ofstream Aux,Consumers,Stages;double MaxAux=0,MaxSPTrace=0;
  std::array<double,3> MaxCompare{},MaxAnalytic{};unsigned WallChecks=0,ConsumerChecks=0,StageChecks=0;
  bool WallROI(unsigned p)const{return fabs(Posc[p].x)<=.035+1e-9&&(Dim==2||fabs(Posc[p].y)<=.035+1e-9);}
  bool SoilROI(unsigned p)const{return fabs(Posc[p].x)<=.015+1e-9&&(Dim==2||fabs(Posc[p].y)<=.015+1e-9)&&Posc[p].z>0&&Posc[p].z<=.025+1e-9;}
  Vec Field(tdouble3 x,unsigned kind,double amplitude=1)const{
    if(kind==0)return{{.5*amplitude,(Dim==3?.25*amplitude:0),0}};
    if(kind==1)return{{-.4*amplitude*x.y,.4*amplitude*x.x,0}};
    return{{.2*amplitude*x.x,(Dim==3?.3*amplitude*x.y:0),0}};
  }
  tfloat3 Oracle(unsigned p,unsigned kind,double amplitude=1)const{
    if(BoundModec[p]==BMODE_MDBC2OFF)return TFloat3(Velrhopc[p].x,Velrhopc[p].y,Velrhopc[p].z);
    Vec v=Field(Posc[p]+ToTDouble3(BoundNormalc[p]),kind,amplitude);v[2]=-v[2];return F(v);
  }
  void SetField(unsigned kind,double amplitude=1){
    for(unsigned p=0;p<Np;p++){
      if(CODE_IsFluid(Codec[p])){const Vec v=Field(Posc[p],kind,amplitude);Velrhopc[p]=TFloat4(float(v[0]),float(v[1]),float(v[2]),RhopZero);}
      PorePressc[p]=PorePress0c[p]=0;Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;
    }
  }
  BvPhysical Physical()const{return{{Posc,Posc+Np},{Velrhopc,Velrhopc+Np},{Sigmac,Sigmac+Np},{PorePressc,PorePressc+Np},{PorePress0c,PorePress0c+Np},{Idpc,Idpc+Np}};}
  void Unchanged(const BvPhysical& s)const{
    Check(Same(s.pos,Posc)&&Same(s.velocity,Velrhopc)&&Same(s.sigma,Sigmac)&&Same(s.pressure,PorePressc)&&Same(s.reference,PorePress0c)&&Same(s.ids,Idpc),"SPR/observer altered physical state or IDs");
  }
  void Stage(TpInterStep stage){
    // Same condition/order as JSphCpuSingle::Interaction_Forces, without force/integration.
    if(MdbcCorrector||stage!=INTERSTEP_SymCorrector)MdbcBoundCorrection();
    InterStep=stage;PreInteraction_Forces();const BvPhysical before=Physical();
    ComputeBoundaryDerivativeVelocity();Unchanged(before);ComputeFreeSurfaceTracking();
  }
  void CheckAux(const char* label,unsigned kind,double amplitude=1){
    unsigned count=0;
    for(unsigned p=0;p<Npb;p++)if(WallROI(p)){
      count++;Check(BoundModec[p]==BMODE_MDBC2,"Actual mDBC ROI wall is inactive");
      const Vec actual=V(BoundDerivativeVelc[p]),exact=V(Oracle(p,kind,amplitude));
      for(unsigned j=0;j<3;j++){
        const double error=fabs(actual[j]-exact[j]),tol=32.*FLT_EPSILON*(std::max)(.125,fabs(exact[j]));
        Aux<<label<<','<<Idpc[p]<<','<<j<<','<<actual[j]<<','<<exact[j]<<','<<error<<','<<tol<<'\n';
        Check(std::isfinite(actual[j])&&error<=tol,"Additional compatible-field MLS reflection failed");MaxAux=(std::max)(MaxAux,error);WallChecks++;
      }
    }
    Check(count==(Dim==2?24u:192u),"Wall ROI changed");
  }
  BvRates Fused(){
    memset(Arc,0,Np*sizeof(float));memset(PorePressRatec,0,Np*sizeof(float));
    memset(Rsigmac,0,Np*sizeof(tsymatrix3f));memset(Acec,0,Np*sizeof(tfloat3));
    const BvPhysical before=Physical();
    const stinterparmsc p=StInterparmsc(Np,Npb,NpbOk,DivData,Dcellc,Posc,Velrhopc,Idpc,Codec,Pressc,
      PorePressc,PorePressRatec,FSTypec,FSNormalc,NULL,CorrMatc,Arc,Acec,Deltac,ShiftingMode,ShiftPosfsc,
      SpsTauc,SpsGradvelc,Sigmac,Rsigmac,ArtificialStressc);
    StInterResultc r;r.viscdt=0;JSphCpu::Interaction_Forces_ct(p,r);Unchanged(before);
    return{{Arc,Arc+Np},{PorePressRatec,PorePressRatec+Np},{Rsigmac,Rsigmac+Np}};
  }
  void CheckConsumers(const char* label,unsigned kind){
    const auto mls=Fused();const std::vector<tfloat3> aux(BoundDerivativeVelc,BoundDerivativeVelc+Npb);
    for(unsigned p=0;p<Npb;p++)BoundDerivativeVelc[p]=Oracle(p,kind);
    const auto exactAux=Fused();std::copy(aux.begin(),aux.end(),BoundDerivativeVelc);
    const double K=SoilCte.ModulusK,mf=double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity;
    unsigned count=0;
    for(unsigned p=Npb;p<Np;p++)if(SoilROI(p)){
      count++;const auto sm=Stress(mls.sigma[p]),so=Stress(exactAux.sigma[p]);
      const double ds=(sm[0]+sm[1]+sm[2])/(3*K),dp=-double(mls.pore[p])/mf;
      const double defect=ds-dp;MaxSPTrace=(std::max)(MaxSPTrace,fabs(defect));
      for(unsigned j=0;j<8;j++){
        const unsigned group=(j<6?0:(j==6?1:2));
        const double m=(j<6?sm[j]:(j==6?mls.pore[p]:mls.rho[p]));
        const double o=(j<6?so[j]:(j==6?exactAux.pore[p]:exactAux.rho[p]));
        const double floor=(group==0?20.:(group==1?2000.:.02)),tol=floor+2e-5*fabs(o);
        // Both fields are trace-free, zero-prestress and zero-pressure; S/P truth is zero.
        Consumers<<label<<','<<Idpc[p]<<','<<j<<','<<m<<','<<o<<",0,"<<fabs(m-o)<<','<<fabs(m)<<','<<tol<<','<<defect<<'\n';
        Check(std::isfinite(m)&&std::isfinite(o)&&fabs(m-o)<=tol,"Additional actual ct MLS/oracle mismatch");
        if(group<2)Check(fabs(m)<=floor,"Compatible rigid-motion corrected S/P analytic mismatch");
        MaxCompare[group]=(std::max)(MaxCompare[group],fabs(m-o));MaxAnalytic[group]=(std::max)(MaxAnalytic[group],fabs(m));ConsumerChecks++;
      }
    }
    Check(count==(Dim==2?12u:48u),"Soil ROI changed");
  }
  void StageObserver(bool corrector){
    MdbcCorrector=corrector;SetField(2);Stage(INTERSTEP_SymPredictor);CheckAux(corrector?"mdbc1_tn":"mdbc0_tn",2);
    const std::vector<tfloat3> tangent(TangenVelc,TangenVelc+Npb),aux(BoundDerivativeVelc,BoundDerivativeVelc+Npb);
    const std::vector<byte> mode(BoundModec,BoundModec+Npb);PosInteraction_Forces();
    SetField(2,2);Stage(INTERSTEP_SymCorrector);CheckAux(corrector?"mdbc1_half":"mdbc0_half",2,2);
    for(unsigned p=0;p<Npb;p++)if(WallROI(p)){
      const Vec old=V(tangent[p]),now=V(TangenVelc[p]),oldaux=V(aux[p]),nowaux=V(BoundDerivativeVelc[p]);
      Check(BoundModec[p]==mode[p],"Fixed geometry changed BoundMode across stage observation");
      if(!corrector)Check(!memcmp(&tangent[p],TangenVelc+p,sizeof(tfloat3)),"mDBC-Corrector OFF unexpectedly refreshed tangential ghost");
      for(unsigned j=0;j<3;j++){
        const double expected=(corrector?2*old[j]:old[j]),tol=32.*FLT_EPSILON*(std::max)(.125,fabs(expected));
        Check(std::isfinite(now[j])&&fabs(now[j]-expected)<=tol,"Stage tangential ghost routing mismatch");
        Stages<<corrector<<','<<Idpc[p]<<','<<j<<','<<old[j]<<','<<now[j]<<','<<expected<<','<<oldaux[j]<<','<<nowaux[j]<<','<<unsigned(mode[p])<<','<<unsigned(BoundModec[p])<<'\n';StageChecks++;
      }
    }
    PosInteraction_Forces();
  }
public:
  explicit BvMlsCheck(unsigned dim):Dim(dim){}
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(cfg->SvTimers);Timersc->TmStart(TMC_Init);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunCpu();FreePartsInit();
    Check(HydroMech&&SoilBoundaryDerivativeSPR&&SoilStressRateGradCorr&&PoreCompressionGradCorr&&PoreCompressionSourceMode==0,"Expected corrected SPR pressure/stress consumers");
    Check(TBoundary==BC_MDBC&&SlipMode==SLIP_FreeSlip&&!MdbcSlipModeByMk&&!NoPenetration&&TKernel==KERNEL_Wendland&&TStep==STEP_Symplectic,"Only uniform fixed horizontal FreeSlip admitted");
    Check(Simulate2D==(Dim==2)&&Np==(Dim==2?208u:3328u)&&Npb==(Dim==2?48u:768u),"Prepared native geometry/count mismatch");
    Check(!PartBegin&&!CaseNmoving&&!CaseNfloat&&!PeriActive&&!HourglassCpu&&!SoilDamping&&!Shifting&&TDensity==DDT_None&&!ArtificialStress&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None,"Unexpected fixture physics");
    Check(Gravity.x==0&&Gravity.y==0&&Gravity.z==0,"Fixture requires zero gravity/head term");
    std::set<unsigned> ids;
    for(unsigned p=0;p<Np;p++){Check(CODE_IsNormal(Codec[p])&&ids.insert(Idpc[p]).second,"Native IDs invalid");
      if(p<Npb)Check(CODE_IsFixed(Codec[p])&&Velrhopc[p].x==0&&Velrhopc[p].y==0&&Velrhopc[p].z==0&&BoundNormalc[p].x==0&&BoundNormalc[p].y==0&&BoundNormalc[p].z>0&&fabs(Posc[p].z+.5*BoundNormalc[p].z)<=1e-7,"Expected stationary horizontal plane");}
    Check(*ids.begin()==0&&*ids.rbegin()==Np-1&&TimeStep==0,"Native identity/time changed");
    const fs::path out(cfg->DirOut);Aux.open(out/"aux_rows.csv");Consumers.open(out/"consumer_rows.csv");Stages.open(out/"stage_rows.csv");
    Aux<<std::setprecision(17)<<"field,id,component,mls,analytic_ghost,error,tolerance\n";
    Consumers<<std::setprecision(17)<<"field,id,component_0to5_sigma_6_pore_7_rho,mls,oracle,analytic,mls_oracle_error,analytic_error,tolerance,corrected_trace_defect_per_s\n";
    Stages<<std::setprecision(17)<<"mdbc_corrector,id,component,tn_tangent,half_tangent,expected_half_tangent,tn_aux,half_aux,tn_mode,half_mode\n";
    const bool configured=MdbcCorrector;
    for(unsigned kind=0;kind<(Dim==3?2u:1u);kind++){
      const char* name=(kind?"normal_axis_rigid_rotation":"tangential_translation");MdbcCorrector=true;SetField(kind);Stage(INTERSTEP_SymPredictor);
      CheckAux(name,kind);CheckConsumers(name,kind);PosInteraction_Forces();
    }
    StageObserver(false);StageObserver(true);MdbcCorrector=configured;
    Check(TimeStep==0&&Nstep==0,"Observer advanced the physical clock");
    std::ofstream done(out/"bv_mls_complete.json");done<<std::setprecision(17)
      <<"{\"passed\":true,\"dimension\":"<<Dim<<",\"native_count\":"<<Np<<",\"wall_count\":"<<Npb
      <<",\"velocity_component_checks\":"<<WallChecks<<",\"consumer_component_checks\":"<<ConsumerChecks<<",\"stage_component_checks\":"<<StageChecks
      <<",\"max_aux_error\":"<<MaxAux<<",\"max_corrected_trace_defect_per_s\":"<<MaxSPTrace
      <<",\"consumer_mls_oracle_max\":["<<MaxCompare[0]<<','<<MaxCompare[1]<<','<<MaxCompare[2]
      <<"],\"consumer_analytic_max\":["<<MaxAnalytic[0]<<','<<MaxAnalytic[1]<<','<<MaxAnalytic[2]
      <<"],\"raw_density_analytic_bias_is_diagnostic\":true,\"stage_mdbc_corrector_off_mixed_time_observed\":true,\"physical_fields_unchanged_by_spr_and_ct\":true"
      <<",\"copied_mls_or_neighbor_algorithm\":false,\"time_integrated\":false,\"physical_acceptance\":false}\n";
    done.flush();Aux.flush();Consumers.flush();Stages.flush();Check(bool(done)&&bool(Aux)&&bool(Consumers)&&bool(Stages),"Observer output failure");
  }
};
int main(int argc,char** argv){
  try{
    Check(argc>=5,"Usage: bv_mls_cpu_r1 DIM then ordinary CPU arguments and fresh output");
    const unsigned dim=std::stoul(argv[1]);Check(dim==2||dim==3,"Only dimension 2/3 admitted");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=2;i<argc;i++)args.push_back(argv[i]);
    JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());cfg.Cpu=true;cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;
    Check(!fs::exists(cfg.DirOut),"Output exists; never overwrite retained evidence");
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    BvMlsCheck fixture(dim);fixture.Execute(&cfg,AppInfo.LogPtr());return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Production exception; retain observer output and Run.out\n";return 2;}
}
