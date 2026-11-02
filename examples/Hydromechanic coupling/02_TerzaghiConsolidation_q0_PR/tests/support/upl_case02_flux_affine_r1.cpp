// Conditional manufactured affine flux action, not a mechanical trajectory or integration.
#define main RetainedFluxAffineNativeMain
#include "upl_cpu_public_native_r1.cpp"
#undef main
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JDsFixedDt.h"
#include "JLog2.h"
#include "JException.h"
#include "FunSphKernel.h"
#include <limits>
namespace fluxaffine {
constexpr unsigned Soil=1000,Fixed=40,Total=1040;
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static tdouble3 Abs(tdouble3 a){return TDouble3(std::fabs(a.x),std::fabs(a.y),std::fabs(a.z));}
static tdouble3 Product(const tmatrix3d& c,tdouble3 g){return TDouble3(c.a11*g.x+c.a12*g.y+c.a13*g.z,c.a21*g.x+c.a22*g.y+c.a23*g.z,c.a31*g.x+c.a32*g.y+c.a33*g.z);}
struct Block {void* pointer;std::vector<byte> bytes;};
struct Snapshot {
  std::vector<Block> blocks;double cache;
  template<class T>void Add(T* p,unsigned n){if(p){Block b{p,std::vector<byte>(sizeof(T)*n)};memcpy(b.bytes.data(),p,b.bytes.size());blocks.push_back(std::move(b));}}
  void Restore()const{for(const auto& b:blocks)memcpy(b.pointer,b.bytes.data(),b.bytes.size());}
  bool Exact()const{for(const auto& b:blocks)if(std::memcmp(b.pointer,b.bytes.data(),b.bytes.size()))return false;return true;}
};
struct Ref {double rate,old,raw,budget,oldbudget,lp,da,flux,target,delta;tdouble3 gp,lx,gc,agp;};
class Affine:public JSphCpuSingle {
  unsigned Calls=0,Rows=0,Ghosts=0,Restores=0;
  double Locked=0,Last=0,Error0=0,MaxRatio=0,MaxInvariant=0,Signal=0;
  std::vector<unsigned> Owners()const{
    std::vector<unsigned> map(Total,~0u);unsigned ns=0,nf=0;
    for(unsigned p=0;p<Np;p++){Need(Idpc[p]<Total&&(CODE_IsNormal(Codec[p])||CODE_IsPeriodic(Codec[p])),"Unknown/excluded slot");
      if(CODE_IsNormal(Codec[p])){Need(map[Idpc[p]]==~0u,"Duplicate native ID");map[Idpc[p]]=p;if(Idpc[p]<Fixed){Need(CODE_IsFixed(Codec[p]),"Fixed type differs");nf++;}else{Need(CODE_IsFluid(Codec[p]),"Soil type differs");ns++;}}}
    Need(ns==Soil&&nf==Fixed&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Native scope/exclusion differs");return map;
  }
  void Clock()const{Need(!TimeStep&&!Nstep&&SymplecticDtPre==Locked&&LastDt==Last&&FixedDt->GetDtError(false)==Error0&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Frozen audit advanced time/history");}
  Snapshot Save()const{
    Snapshot s;s.cache=DynamicConductivitySpeedMax;s.Add(Posc,Np);s.Add(Codec,Np);s.Add(Idpc,Np);s.Add(Dcellc,Np);s.Add(Velrhopc,Np);s.Add(Sigmac,Np);
    s.Add(PorePressc,Np);s.Add(PorePress0c,Np);s.Add(PorePressRatec,Np);s.Add(PoroJc,Np);s.Add(PoroThetac,Np);s.Add(CorrMatc,Np);s.Add(FSTypec,Np);s.Add(FSNormalc,Np);
    s.Add(HydroMechLoadAcec,Np);s.Add(Acec,Np);s.Add(Arc,Np);s.Add(Rsigmac,Np);s.Add(BoundDerivativeVelc,Np);s.Add(TangenVelc,Np);s.Add(BoundModec,Np);return s;
  }
  void Restore(const Snapshot& s){s.Restore();DynamicConductivitySpeedMax=s.cache;Need(s.Exact()&&DynamicConductivitySpeedMax==s.cache,"Covered state/scratch rollback differs");Restores++;Clock();}
  void Copies() {
    const auto owner=Owners();
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){const unsigned q=owner[Idpc[p]];
      Need(!std::memcmp(PoroJc+p,PoroJc+q,sizeof(double))&&!std::memcmp(CorrMatc+p,CorrMatc+q,sizeof(tmatrix3d))&&!std::memcmp(Acec+p,Acec+q,sizeof(tfloat3))&&!std::memcmp(PoroThetac+p,PoroThetac+q,sizeof(double))&&!std::memcmp(PorePressRatec+p,PorePressRatec+q,sizeof(float)),"Actual periodic complete-rate extension differs");Ghosts++;}
  }
  Ref Reference(unsigned i)const {
    double lp=0,alp=0,da=0,ada=0;tdouble3 gp=TDouble3(0),lx=TDouble3(0),agp=TDouble3(0),alx=TDouble3(0);
    const double V0=double(MassFluid)/RhopZero,rhow=SoilCte.PoreWaterRho,B=double(SoilCte.PoreWaterBulkModulus)/(1.-(1.-double(SoilCte.Porosity))/PoroJc[i]),k=SoilCte.HydraulicConductivity,gamma=rhow*9.80665;
    // Independent all-slot loop; no production cell list, no fitted/coarsened support.
    for(unsigned j=0;j<Np;j++)if(CODE_IsFluid(Codec[j])||CODE_IsFixed(Codec[j])){
      const auto d=TDouble3(Posc[i].x-Posc[j].x,0,Posc[i].z-Posc[j].z);const double rr=Dot(d,d);if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;
      if(CODE_IsFixed(Codec[j]))Need(BoundModec[j]!=BMODE_MDBC2OFF,"Inactive wall enters independent support");
      const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr))),gi=Product(CorrMatc[i],g),gj=Product(CorrMatc[j],g);
      const double V=V0*PoroJc[j],dp=double(PorePressc[i])-PorePressc[j],w=V*Dot(d,gi+gj)/(rr+double(Eta2));const auto delta=ToTDouble3(Acec[j])-ToTDouble3(Acec[i]);
      lp+=w*dp;alp+=std::fabs(w*dp);lx=lx+d*w;alx=alx+Abs(d*w);gp=gp-gi*(V*dp);agp=agp+Abs(gi*(V*dp));da+=V*Dot(delta,gi);ada+=V*Dot(Abs(delta),Abs(gi));
    }
    tdouble3 gc=gp,agc=agp;double flux=0,target=0,correction=0;const auto a=ToTDouble3(Acec[i]);
    if(FSTypec[i]==FST_FreeSurface||FSTypec[i]==FST_Isolated){const auto n=ToTDouble3(FSNormalc[i]);const double n2=Dot(n,n);Need(std::isfinite(n2)&&n2>0,"Invalid reference surface normal");
      const double r=Dot(n,gp+a*rhow)/n2,ar=Dot(Abs(n),agp+Abs(a)*rhow)/n2;gc=gp-n*r;agc=agp+Abs(n)*ar;
      flux=Dot(n,gp+a*rhow)/std::sqrt(n2);target=Dot(n,gc+a*rhow)/std::sqrt(n2);correction=B*k/gamma*r*Dot(n,lx);
      Need(std::fabs(target)<=256.*DBL_EPSILON*(std::max)(1.,Dot(Abs(n),Abs(gc)+Abs(a)*rhow)/std::sqrt(n2)),"Constructed normal-gradient substitution algebra failed");
    }
    const double old=B*(-PoroThetac[i]+k/gamma*(lp-Dot(gp,lx)+rhow*da)),rate=B*(-PoroThetac[i]+k/gamma*(lp-Dot(gc,lx)+rhow*da));
    const double raw=B*(std::fabs(PoroThetac[i])+k/gamma*(alp+Dot(agc,alx)+rhow*ada)),oldraw=B*(std::fabs(PoroThetac[i])+k/gamma*(alp+Dot(agp,alx)+rhow*ada));
    const double tail=256.*DBL_EPSILON*(std::max)(1.,std::fabs(B*PoroThetac[i]))+1e-6;
    Need(std::isfinite(rate)&&std::isfinite(raw)&&raw>=0&&std::fabs((rate-old)-correction)<=64.*FLT_EPSILON*(raw+oldraw)+tail,"Independent correction identity/reference nonfinite");
    return{rate,old,raw,64.*FLT_EPSILON*raw+tail,64.*FLT_EPSILON*oldraw+tail,lp,da,flux,target,correction,gp,lx,gc,agp};
  }
public:
  Affine(){PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;DynamicPoreConductivity=false;DynamicPoreConductivityCk=0.;}
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();RunCellDivide(true);
    Need(HydroMech&&Simulate2D&&CaseNp==Total&&CaseNpb==Fixed&&CaseNfluid==Soil&&!PartBegin&&!CaseNmoving&&!CaseNfloat&&TStep==STEP_Symplectic&&TKernel==KERNEL_Wendland&&PeriX&&!PeriY&&!PeriZ&&PeriXinc.y==0&&PeriXinc.z==0&&std::fabs(std::fabs(PeriXinc.x)-.1)<=1e-14&&Gravity==TFloat3(0)&&CSP.gravity==Gravity&&OmpThreads==1,"Only actual initial case02 g0/X-periodic scope");
    Need(!HydroMechDynamicSeepage&&HydroMechConductivityModel==0&&!DynamicPoreConductivity&&PorosityObserver&&PorosityFeedback&&DynamicPorePressure&&DynamicPoreWall&&TBoundary==BC_MDBC&&SlipMode==SLIP_FreeSlip&&HydroMechTopLoadMode==HMLOAD_TopKernelBand&&HydroMechTopLoadQ0==10000.f&&HydroMechTopLoadRampTime==.01&&HydroMechDrainage&&HydroMechDrainageStartTime==.01&&HydroMechDrainageFixedGrid&&!IsHydroMechDrainageActive(),"Only closed private case02 constant-k boundary candidate");
    Need(JSph::Dp==.01&&KernelH==float(.018)&&RhopZero==2100.f&&MassFluid==float(.21)&&MassBound==MassFluid&&SoilCte.Porosity==float(.3)&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==2e8f&&SoilCte.HydraulicConductivity==float(.0001)&&SoilCte.ModulusK==1666666.75f&&SoilCte.ModulusG==769230.8125f&&PoreDtSafety==1,"Original material differs");
    Need(!HourglassCpu&&!Visco&&!SoilDamping&&!Damping&&!RelaxZones&&!Shifting&&!InOut&&!AccInput&&!NoPenetration&&!SoilBoundaryDerivativeSPR&&!ArtificialStress&&!PoreShepardRegularization&&TDensity==DDT_None&&!StrainSoftening&&PoreCompressionGradCorr&&!PoreCompressionSourceMode&&SoilStressRateGradCorr&&HydroMechInitMode==HMINIT_None,"Unsupported auxiliary physics");
    Need(!TimeStep&&!Nstep&&FixedDt&&!PosPrec&&!PoroJPrec,"Init advanced state");Locked=SymplecticDtPre;Last=LastDt;Error0=FixedDt->GetDtError(false);
    const auto initial=Owners();for(unsigned id=Fixed;id<Total;id++){const unsigned p=initial[id];Need(PoroJc[p]==1&&PoroThetac[p]==0&&PorePressc[p]==0&&PorePress0c[p]==0&&Kplasticc[p]==0&&Velrhopc[p].x==0&&Velrhopc[p].y==0&&Velrhopc[p].z==0,"Original rest input required");}
    Interaction_Forces(INTERSTEP_SymPredictor);const unsigned count=Np;const auto owner=Owners();unsigned top=~0u,mask=0;
    for(unsigned id=Fixed;id<Total;id++){const unsigned p=owner[id];Need(Acec[p].x==0&&Acec[p].y==0&&Acec[p].z==0&&PorePressRatec[p]==0&&PoroThetac[p]==0,"Natural rest force/rate not zero");if(FSTypec[p]==2||FSTypec[p]==3){Need(Posc[p].z>.98,"Unexpected initial free boundary");top=p;mask++;}}
    Need(mask==10&&top!=~0u,"Initial top receiver mask differs");const Snapshot original=Save();std::ofstream rates(fs::path(cfg->DirOut)/"rates.csv"),summary(fs::path(cfg->DirOut)/"summary.csv"),guards(fs::path(cfg->DirOut)/"guards.csv");
    rates<<std::setprecision(17);summary<<std::setprecision(17);rates<<"field_case,normal_variant,id,z,FSType,actual_rate,reference_rate,old_reference_rate,error,raw_abs_rate,budget,error_over_budget,invariance_difference,invariance_budget,lp,DA,Gp_x,Gp_z,Lx_x,Lx_z,gpcorr_x,gpcorr_z,raw_normal_gradient,projected_normal_gradient,reference_correction,correction_over_max_old_new_budget\n";
    summary<<"field_case,normal_variant,native_rows,upper_affine_rows,top_rows,max_rate_error_over_budget,max_invariance_over_budget,max_signal_over_old_new_budget\n";guards<<"probe,expected_method_message_matched,all_covered_bytes_restored\n";
    std::vector<double> baseline(Soil),budgets(Soil);Snapshot good;const double factors[3]={1.,-1.,2.};
    for(unsigned field=0;field<3;field++){Restore(original);
      // Manufactured pressure is defined analytically at all actual fluid slots, including X images; no pressure-copy API claim.
      for(unsigned p=0;p<Np;p++)if(CODE_IsFluid(Codec[p])){PorePressc[p]=float(2000.+(field==2?0.:1000.*Posc[p].z));PoroJc[p]=1.;PoroThetac[p]=0.;}
      ComputeDynamicPoreWallStateCpu();ComputeDynamicPoreWallMatrixCpu(); // Actual MLS, not hand-written bottom values.
      for(unsigned id=Fixed;id<Total;id++)Acec[owner[id]]=(field==0?TFloat3(0,0,-1):(field==1?TFloat3(0,0,1):TFloat3(1,0,0)));
      const auto normal=std::vector<tfloat3>(FSNormalc,FSNormalc+Np);
      for(unsigned variant=0;variant<3;variant++){for(unsigned id=Fixed;id<Total;id++){const unsigned p=owner[id];FSNormalc[p]=normal[p]*float(factors[variant]);}
        ComputeDynamicPorePressureRateCpu();Calls++;Copies();unsigned upper=0,tops=0;double mr=0,mi=0,signal=0;
        for(unsigned id=Fixed;id<Total;id++){const unsigned p=owner[id];const Ref r=Reference(p);const double actual=PorePressRatec[p],error=std::fabs(actual-r.rate),ratio=error/r.budget;
          Need(std::isfinite(actual)&&error<=r.budget,"Actual candidate complete-rate/raw-term budget failed");mr=(std::max)(mr,ratio);MaxRatio=(std::max)(MaxRatio,ratio);
          if(!variant){baseline[id-Fixed]=actual;budgets[id-Fixed]=r.budget;}const double ib=(std::max)(budgets[id-Fixed],r.budget),ie=std::fabs(actual-baseline[id-Fixed]);Need(ie<=ib,"Normal flip/scale action changed outside original rate budget");mi=(std::max)(mi,ie/ib);MaxInvariant=(std::max)(MaxInvariant,ie/ib);
          if(Posc[p].z>.5){const double wanted=(field==2?0.:1000.);Need(std::fabs(r.gp.z-wanted)<=64.*FLT_EPSILON*(std::max)(1.,r.agp.z)+1e-6&&std::fabs(r.gp.x)<=64.*FLT_EPSILON*(std::max)(1.,r.agp.x)+1e-6,"Upper affine gradient witness failed");if(field!=1)Need(std::fabs(actual)<=r.budget,"Compatible/tangential upper affine rate not zero within prior budget");upper++;}
          const bool surface=FSTypec[p]==2||FSTypec[p]==3;const double sig=std::fabs(actual-r.old)/(std::max)(r.budget,r.oldbudget);if(!surface||field!=1)Need(std::fabs(actual-r.old)<=(std::max)(r.budget,r.oldbudget),"Unmasked/compatible old action differs outside original budget");if(surface){tops++;signal=(std::max)(signal,sig);}if(field==1&&surface)Signal=(std::max)(Signal,sig);
          rates<<field<<','<<variant<<','<<id<<','<<Posc[p].z<<','<<FSTypec[p]<<','<<actual<<','<<r.rate<<','<<r.old<<','<<error<<','<<r.raw<<','<<r.budget<<','<<ratio<<','<<ie<<','<<ib<<','<<r.lp<<','<<r.da<<','<<r.gp.x<<','<<r.gp.z<<','<<r.lx.x<<','<<r.lx.z<<','<<r.gc.x<<','<<r.gc.z<<','<<r.flux<<','<<r.target<<','<<r.delta<<','<<sig<<'\n';Rows++;
        }Need(upper==500&&tops==10,"Affine/top coverage differs");if(field==1)Need(signal>100,"Incompatible normal flux correction empty against100 original old/new budgets");summary<<field<<','<<variant<<','<<Soil<<','<<upper<<','<<tops<<','<<mr<<','<<mi<<','<<signal<<'\n';Clock();if(field==2&&variant==2)good=Save();
      }
    }
    // All other conditions already passed actual positive calls; change only one valid top normal for each exact-method rejection.
    Need(!good.blocks.empty(),"Missing actual-positive normal-guard baseline");
    for(unsigned bad=0;bad<2;bad++){Restore(good);FSNormalc[top]=(bad?TFloat3(std::numeric_limits<float>::quiet_NaN(),0,1):TFloat3(0));bool rejected=false,matched=false;
      try{ComputeDynamicPorePressureRateCpu();Calls++;}catch(const JException& e){Calls++;rejected=true;const auto text=e.ToStr();matched=text.find("::ComputeDynamicPorePressureRateCpu)")!=std::string::npos&&text.find("Dynamic Darcy fixture produced a nonfinite pressure rate or conductivity-gradient speed.")!=std::string::npos;}catch(...){Restore(good);throw;}
      Restore(good);guards<<(bad?"NaN":"zero")<<','<<matched<<",true\n";guards.flush();Need(rejected&&matched,"Only the exact complete-rate guard is an accepted normal rejection");
    }
    Restore(original);Need(original.Exact()&&Np==count&&Calls==11&&Rows==9000&&Ghosts>0&&Signal>100,"Declared coverage/rollback differs");PosInteraction_Forces();Clock();Need(!Acec&&!Arc&&!Rsigmac&&!BoundDerivativeVelc&&!HydroMechTopLoadRawc,"Force scratch not released");
    for(auto* s:{&rates,&summary,&guards}){s->flush();Need(bool(*s),"Affine audit CSV write failed");}
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_case02_flux_affine_r1\",\"passed\":true,\"native_count\":1000,\"fixed_count\":40,\"field_cases\":3,\"normal_variants\":3,\"actual_force_calls\":1,\"explicit_complete_rate_calls\":11,\"expected_exact_method_rejections\":2,\"rate_rows\":9000,\"max_rate_error_over_original_budget\":"<<MaxRatio<<",\"max_normal_invariance_over_original_budget\":"<<MaxInvariant<<",\"incompatible_correction_over_old_new_budget\":"<<Signal<<",\"periodic_owner_checks\":"<<Ghosts<<",\"covered_snapshot_restores\":"<<Restores<<",\"covered_state_and_scratch_bytes_restored\":true,\"actual_wall_MLS_and_Ace_periodic_extension\":true,\"reference_conditioned_on_actual_C_and_Ace\":true,\"constructed_normal_gradient_not_actual_face_flux\":true,\"manufactured_not_mechanical_trajectory\":true,\"Run_ComputeStep_SaveData_called\":false,\"actual_time_s\":0,\"completed_physical_steps\":0,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Affine audit completion write failed");
  }
};
}
int main(int argc,char** argv){try{
  Need(argc==5&&std::string(argv[1])=="--input"&&std::string(argv[3])=="--out","Use --input EXISTING_CASE02_XML --out FRESH_DIR");const fs::path xml=argv[2],out=argv[4];auto prefix=xml;prefix.replace_extension();Need(fs::is_regular_file(xml)&&fs::is_regular_file(prefix.string()+".bi4")&&!fs::exists(out),"Existing unchanged seed and fresh output required");
  AppInfo.ConfigRunPaths(argv[0]);std::vector<std::string> args={argv[0],"-cpu","-ompthreads:1","-stable","-mdbc_freeslip",prefix.string(),out.string(),"-dirdataout","data","-svres"};std::vector<char*> a;for(auto& s:args)a.push_back(s.data());JSphCfgRun cfg;cfg.LoadArgv(int(a.size()),a.data());Need(cfg.Cpu&&cfg.OmpThreads==1&&cfg.Stable&&!cfg.PrintInfo&&!cfg.PartBegin&&!cfg.NstepsBreak&&cfg.TimeMax<0&&cfg.TimePart<0&&!cfg.SvAllSteps,"No integration/restart/clock override");
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");fluxaffine::Affine fixture;fixture.Execute(&cfg,AppInfo.LogPtr());return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Affine conditional flux audit rejected; preserve original outputs\n";return 2;}}

