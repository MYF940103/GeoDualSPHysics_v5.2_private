// Frozen Part60 polynomial shadows; exactly one original CPU force, no step.
#define main c08_storage_rhs_unused_main
#include "../outputs/c08_h18_quadratic_r1_build/shared.inc"
#undef main

static const char* Basis[8]={"1","x","z","half_x2","xz","half_z2","half_x2_minus_z2","native_pressure"};
static const char* Regions[4]={"all","interior_no_fixed","wall_adjacent","FS"};
static const char* Metrics[12]={"pairC_Eta2_L","receiverC_Eta2_L","receiverC_bare_L","Eq23_Hxx","Eq23_Hxz","Eq23_Hzz","Eq23_exact_gp_trace_diagnostic","Eq23_exact_gp_Hxx_diagnostic","Eq23_exact_gp_Hxz_diagnostic","Eq23_exact_gp_Hzz_diagnostic","Eq22_gpx","Eq22_gpz"};
static double Polynomial(unsigned b,tdouble3 r){switch(b){case 0:return 1.;case 1:return r.x;case 2:return r.z;case 3:return .5*r.x*r.x;case 4:return r.x*r.z;case 5:return .5*r.z*r.z;default:return .5*(r.x*r.x-r.z*r.z);}}
static tdouble3 ExactGradient(unsigned b){return TDouble3(b==1?1.:0.,0,b==2?1.:0.);}
static std::array<double,3> ExactHessian(unsigned b){return {{b==3||b==6?1.:0.,b==4?1.:0.,b==5?1.:b==6?-1.:0.}};}
struct QuadDonor{tdouble3 r,gi;double v,rr,p;std::array<double,3> w;};
struct QuadStats{unsigned count=0;double sum=0,sq=0,max=0;void Add(double value,double exact){const double e=value-exact;Need(Finite(value)&&Finite(e),"Nonfinite polynomial response");count++;sum+=value;sq+=e*e;max=(std::max)(max,fabs(e));}};
class QuadraticProbe:public Probe{
  std::vector<QuadDonor> Stencil(unsigned i,unsigned& fixed,unsigned& almost)const{
    std::vector<QuadDonor> out;fixed=almost=0;const double v0=double(MassFluid)/double(RhopZero);const auto ci=CorrMatc[i];
    for(unsigned group=0;group<2;group++){const bool boundary=group==1;const StNgSearch ngs=nsearch::Init(Dcellc[i],boundary,DivData);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){const tuint2 range=nsearch::ParticleRange(y,z,ngs,DivData);
        for(unsigned j=range.x;j<range.y;j++)if(CODE_IsFluid(Codec[j])||(boundary&&CODE_IsFixed(Codec[j]))){
          const tdouble3 d=TDouble3(Posc[i].x-Posc[j].x,0,Posc[i].z-Posc[j].z);const double rr=d.x*d.x+d.y*d.y+d.z*d.z;
          Need(Finite(rr)&&rr>=0,"Invalid squared donor distance");if(rr>double(KernelSize2))continue;if(rr<ALMOSTZERO){almost++;continue;}Need(rr>0,"Bare denominator must be positive");
          Need(!boundary||BoundModec[j]!=BMODE_MDBC2OFF,"Actual stencil contains disabled fixed donor");
          const double fac=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr));const tdouble3 g=d*fac,gi=Product(ci,g),gj=Product(CorrMatc[j],g);const double v=v0*PoroJc[j];
          Need(Finite(v)&&v>0&&Finite(gi)&&Finite(gj),"Invalid actual force donor volume/C/kernel");
          // r=xj-xi; weights use delta=qj-qi, hence minus the native dp weight.
          QuadDonor a;a.r=d*(-1.);a.gi=gi;a.v=v;a.rr=rr;a.p=PorePressc[j];
          a.w={{-v*Dot(d,gi+gj)/(rr+double(Eta2)),-2.*v*Dot(d,gi)/(rr+double(Eta2)),-2.*v*Dot(d,gi)/rr}};out.push_back(a);fixed+=boundary;
        }
      }
    }Need(!out.empty(),"Empty actual force stencil");return out;
  }
public:
  void ExecuteQuadratic(const JSphCfgRun* cfg,JLog2* log,const Snapshot& a){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();RunGravityPreloadHandoffCpu();FreePartsInit();
    Need(IsGravityPreloadHandoff()&&GravityPreload&&!GravityPreloadElasticSource&&!GravityPreloadReleased&&unsigned(Nstep)==2000000&&!GravityPreloadKeepBedOverlap&&GravityPreloadBedIds.empty(),"Original schema2 PRE/bedroles handoff differs");RunGravityPreloadRelease();Map();
    Need(GravityPreloadReleased&&GravityPreloadActualStep==2000000&&GravityPreloadIdBegin==1805&&GravityPreloadIdCount==255&&DynamicPorePressure&&PorosityFeedback&&DynamicPoreWall&&DynamicPoreConductivity&&DynamicPoreConductivityCk==2.&&HydroMechFreeSeepage&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilDamping&&!PoreShepardRegularization,"Original released controls differ");
    Need(Simulate2D&&!PeriActive&&OmpThreads==1&&TKernel==KERNEL_Wendland&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundSlipModec&&SoilStressRateGradCorr&&!SoilBoundaryDerivativeSPR&&!HourglassCpu&&!SoilHourglassXi&&!WithFloating&&!UseDEM&&!AccInput&&!Shifting&&!Damping&&TDensity==DDT_None&&NoPenetration&&TMdbc2==MDBC2_NoPen&&UseDynamicPorePlaneContact(),"Original force scope differs");
    Need(ArtificialStress&&ArtificialStressCoef==.5f&&ArtificialStressExp==2.55f&&TVisco==VISCO_Artificial&&Visco==.1f&&!ViscoTime&&Dp==.04&&KernelH==.072f&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==.0002f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&Gravity==TFloat3(0,0,-9.81f)&&FixedDt&&FixedDt->GetFixedValue()==.000005&&SymplecticDtPre==.000005,"Original material/AS/AV/dt differs");
    code.resize(Original);wallnormal.resize(Original);slip.resize(Original);for(unsigned q=0;q<Np;q++){code[Idpc[q]]=Codec[q];if(q<Npb){wallnormal[Idpc[q]]=BoundNormalc[q];slip[Idpc[q]]=BoundSlipModec[q];}}Roles();Restore(a);Need(a.part==60&&a.completed==2120001,"Only original Part60 admitted");Unchanged(a);
    std::ofstream response(pf::path(cfg->DirOut)/"quadratic.csv"),summary(pf::path(cfg->DirOut)/"summary.csv"),walls(pf::path(cfg->DirOut)/"walls.csv");for(auto f:{&response,&summary,&walls}){Need(bool(*f),"Fresh CSV open failed");*f<<std::setprecision(17);}
    response<<"part,time_s,tau_s,completed_step,native_id,region,FS,neighbors,fixed_neighbors,almostzero_excluded,x_m,z_m,J,V_m2,Cxx,Cxz,Czx,Czz,basis,exact_L,exact_Hxx,exact_Hxz,exact_Hzz,exact_gpx,exact_gpz";for(const char* m:Metrics)response<<','<<m;response<<",Eq23_trace,trace_minus_receiver_bare_L,trace_arithmetic_budget,pairC_Eta2_LP,pairC_Eta2_Lxx,pairC_Eta2_Lxz,receiverC_Eta2_LP,receiverC_Eta2_Lxx,receiverC_Eta2_Lxz,receiverC_bare_LP,receiverC_bare_Lxx,receiverC_bare_Lxz\n";
    walls<<"part,time_s,completed_step,native_id,x_m,z_m,J,V_m2,mode,active,normalx,normalz,slip,Cxx,Cxz,Czx,Czz\n";
    summary<<"region,basis,metric,IDs,exact_response,mean_response,rms_error,max_abs_error\n";
    std::array<std::array<std::array<QuadStats,12>,7>,4> stats;std::array<unsigned,4> receivers{};unsigned calls=0,rows=0,wallRows=0,summaryRows=0;bool scratch=true;
    try{
      Interaction_Forces(INTERSTEP_SymCorrector);calls++;Need(Acec&&Rsigmac&&PorePressRatec&&BoundDerivativeVelc&&ArtificialStressc&&CorrMatc,"Original full-force scratch missing");Unchanged(a);Map();
      for(unsigned j=0;j<Npb;j++){const bool active=BoundModec[j]!=BMODE_MDBC2OFF;walls<<a.part<<','<<TimeStep<<','<<unsigned(Nstep)<<','<<Idpc[j]<<','<<Posc[j].x<<','<<Posc[j].z<<','<<PoroJc[j]<<','<<double(MassFluid)/double(RhopZero)*PoroJc[j]<<','<<unsigned(BoundModec[j])<<','<<active<<','<<BoundNormalc[j].x<<','<<BoundNormalc[j].z<<','<<unsigned(BoundSlipModec[j]);if(active){const auto c=CorrMatc[j];walls<<','<<c.a11<<','<<c.a13<<','<<c.a31<<','<<c.a33;}else walls<<",,,,";walls<<'\n';wallRows++;}
      for(unsigned i=Npb;i<Np;i++){
        unsigned fixed,almost;const auto donors=Stencil(i,fixed,almost);const bool sf=IsFreeSurfaceParticle(i,Codec,FSTypec);const unsigned region=sf?3u:fixed?2u:1u;receivers[0]++;receivers[region]++;const auto c=CorrMatc[i];double n,V,rho;GetPorosityFeedbackStateCpu(i,n,V,rho);
        for(unsigned b=0;b<8;b++){
          const bool manufactured=b<7;const tdouble3 exactgp=ExactGradient(b);const auto exacth=ExactHessian(b);const double exactlap=exacth[0]+exacth[2],qi=manufactured?Polynomial(b,TDouble3(0)):double(PorePressc[i]);tdouble3 gp=TDouble3(0);std::array<double,3> lp{},lpabs{};std::array<tdouble3,3> lx{{TDouble3(0),TDouble3(0),TDouble3(0)}},lxabs=lx;
          // Eq22 is evaluated once and shared by all three scalar shadows and Eq23.
          for(const auto& d:donors){const double dp=qi-(manufactured?Polynomial(b,d.r):d.p);gp=gp-d.gi*(d.v*dp);for(unsigned op=0;op<3;op++){const double term=d.w[op]*(-dp);const auto moment=d.r*d.w[op];lp[op]+=term;lpabs[op]+=fabs(term);lx[op]=lx[op]+moment;lxabs[op]=lxabs[op]+Abs(moment);}}
          std::array<double,3> h{},hexact{};double traceMagnitude=0;
          for(const auto& d:donors){const double delta=(manufactured?Polynomial(b,d.r):d.p)-qi,F=Dot(d.r,d.gi)/d.rr,rem=delta-Dot(gp,d.r);const std::array<double,3> D{{4.*d.r.x*d.r.x/d.rr-1.,4.*d.r.x*d.r.z/d.rr,4.*d.r.z*d.r.z/d.rr-1.}};for(unsigned k=0;k<3;k++){h[k]+=d.v*rem*D[k]*F;if(manufactured)hexact[k]+=d.v*(delta-Dot(exactgp,d.r))*D[k]*F;}traceMagnitude+=fabs(d.v*rem*D[0]*F)+fabs(d.v*rem*D[2]*F);}
          std::array<double,12> values{{lp[0]-Dot(gp,lx[0]),lp[1]-Dot(gp,lx[1]),lp[2]-Dot(gp,lx[2]),h[0],h[1],h[2],hexact[0]+hexact[2],hexact[0],hexact[1],hexact[2],gp.x,gp.z}};
          const std::array<double,12> exact{{exactlap,exactlap,exactlap,exacth[0],exacth[1],exacth[2],exactlap,exacth[0],exacth[1],exacth[2],exactgp.x,exactgp.z}};
          const double trace=h[0]+h[2],traceError=trace-values[2],budget=RoundoffGamma(128*unsigned(donors.size()+1))*(traceMagnitude+lpabs[2]+Dot(Abs(gp),lxabs[2]))+128.*std::numeric_limits<double>::denorm_min();Need(Finite(traceError)&&Finite(budget)&&fabs(traceError)<=budget,"Eq23 trace arithmetic identity failed");
          response<<a.part<<','<<TimeStep<<','<<TimeStep-GravityPreloadActualTime<<','<<unsigned(Nstep)<<','<<Idpc[i]<<','<<Regions[region]<<','<<FSTypec[i]<<','<<donors.size()<<','<<fixed<<','<<almost<<','<<Posc[i].x<<','<<Posc[i].z<<','<<PoroJc[i]<<','<<V<<','<<c.a11<<','<<c.a13<<','<<c.a31<<','<<c.a33<<','<<Basis[b];if(manufactured)response<<','<<exactlap<<','<<exacth[0]<<','<<exacth[1]<<','<<exacth[2]<<','<<exactgp.x<<','<<exactgp.z;else response<<",,,,,,";
          for(unsigned m=0;m<12;m++){response<<',';if(manufactured||m<6||m>=10){Need(Finite(values[m]),"Nonfinite shadow response");response<<values[m];}}response<<','<<trace<<','<<traceError<<','<<budget;for(unsigned op=0;op<3;op++)response<<','<<lp[op]<<','<<lx[op].x<<','<<lx[op].z;response<<'\n';rows++;
          if(manufactured)for(unsigned group:{0u,region})for(unsigned m=0;m<12;m++)stats[group][b][m].Add(values[m],exact[m]);
        }
      }
      Unchanged(a);Map();PosInteraction_Forces();scratch=false;Need(!Acec&&!Rsigmac&&!ArtificialStressc&&!BoundDerivativeVelc,"Force scratch cleanup differs");Unchanged(a);Map();
    }catch(...){if(scratch)PosInteraction_Forces();throw;}
    for(unsigned g=0;g<4;g++)for(unsigned b=0;b<7;b++){const auto h=ExactHessian(b);const auto gp=ExactGradient(b);const double lap=h[0]+h[2];const std::array<double,12> exact{{lap,lap,lap,h[0],h[1],h[2],lap,h[0],h[1],h[2],gp.x,gp.z}};for(unsigned m=0;m<12;m++){const auto& z=stats[g][b][m];Need(z.count==receivers[g],"Summary receiver coverage differs");summary<<Regions[g]<<','<<Basis[b]<<','<<Metrics[m]<<','<<z.count<<','<<exact[m]<<',';if(z.count)summary<<z.sum/z.count<<','<<sqrt(z.sq/z.count)<<','<<z.max;else summary<<",,";summary<<'\n';summaryRows++;}}
    Need(calls==1&&receivers[0]==Soil&&receivers[1]+receivers[2]+receivers[3]==Soil&&rows==8*Soil&&wallRows==Fixed&&summaryRows==336,"Exact frozen-geometry coverage differs");for(auto f:{&response,&summary,&walls}){f->flush();Need(bool(*f),"Complete CSV write failed");}Unchanged(a);Map();
    std::ofstream done(pf::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"c08_h18_quadratic_r1\",\"passed\":true,\"source_part\":60,\"source_completed_step\":"<<a.completed<<",\"source_time_s\":"<<a.time<<",\"actual_time_s\":"<<TimeStep<<",\"actual_completed_step\":"<<unsigned(Nstep)<<",\"actual_force_calls\":1,\"actual_Darcy_calls\":1,\"physical_steps\":0,\"material_return_calls\":0,\"extra_Darcy_calls\":0,\"quadratic_rows\":"<<rows<<",\"wall_rows\":"<<wallRows<<",\"summary_rows\":"<<summaryRows<<",\"all5000_primary_bits_unchanged\":true,\"all6805_normal_IDs_and_roles_unchanged\":true,\"shared_Eq22_polynomial_gp\":true,\"analytic_wall_continuation\":true,\"constant_isotropic_K_omitted\":true,\"boundary_accuracy_claim\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=9&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--native","Use --check --native CLOSED_N255_NATIVE -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 ORIGINAL_N255_SEED FRESH_OUT");
  const pf::path tests=pf::path(__FILE__).parent_path().parent_path(),native=pf::absolute(argv[3]),seed=tests/"outputs/c08_h18_as05_n255_r1/c08_h18_as05_n255_r1",pre=tests/"outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4";Need(pf::equivalent(native,tests/"outputs/c08_h18_as05_n255_r1/native_r1"),"Only sealed original N255 native admitted");
  std::vector<Stamp> protectedFiles;for(const char* leaf:{"typed22.bin","typed22_layout.csv","clocks.csv","completion.json","bedkeep_metadata.json"})protectedFiles.emplace_back(native/leaf);for(const char* suffix:{".xml",".bi4","_Normals.nbi4"})protectedFiles.emplace_back(pf::path(seed.string()+suffix));protectedFiles.emplace_back(pre);
  for(const char* leaf:{"c08_h18_as05_n255_r1.run.json","c08_h18_as05_n255_r1.call.json","c08_h18_n255_native_run_r1.check.json","c08_h18_n255_review_r1.check.json","c08_h18_storage_rhs_r2.check.json","c08_h18_step_balance_r1.check.json","c08_h18_quadratic_r1.build.json"})protectedFiles.emplace_back(tests/"logs"/leaf);
  protectedFiles.emplace_back(pf::absolute(argv[0]));for(const char* leaf:{"DsphConfig.xml","ChronoEngine.dll","dsphchrono.dll","vcomp140.dll","msvcp140.dll","vcruntime140.dll","vcruntime140_1.dll"})protectedFiles.emplace_back(pf::absolute(argv[0]).parent_path()/leaf);
  const Snapshot state(native,1);AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&pf::absolute(cfg.CaseName)==pf::absolute(seed)&&pf::absolute(cfg.DirOut)==pf::absolute(tests/"outputs/c08_h18_quadratic_r1")&&!pf::exists(cfg.DirOut),"Original seed and fresh exact frozen-geometry output required");
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");QuadraticProbe probe;probe.ExecuteQuadratic(&cfg,AppInfo.LogPtr(),state);for(const auto& q:protectedFiles)q.Check();return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Frozen quadratic diagnostic failed; preserve outputs\n";return 2;}}
