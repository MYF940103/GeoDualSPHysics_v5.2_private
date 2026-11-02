// Frozen saved-endpoint operator component. No Run, ComputeStep or PART restart.
#define main RetainedGravityEndpointNativeMain
#include "upl_cpu_public_native_r1.cpp"
#undef main
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JXml.h"
#include "JLog2.h"
#include "FunSphKernel.h"
namespace endpoint {
constexpr unsigned Count=512,Part=256;
constexpr double Dp=1./256.,V0=Dp*Dp,End=1./32768.,Dt=1./16777216.;
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static tdouble3 Mul(const tmatrix3d& c,tdouble3 g){return TDouble3(c.a11*g.x+c.a12*g.y+c.a13*g.z,c.a21*g.x+c.a22*g.y+c.a23*g.z,c.a31*g.x+c.a32*g.y+c.a33*g.z);}
static Native Load(JPartDataBi4& f){
  Need(f.GetNpiece()==1&&f.Get_Npok()==Count&&f.Get_CaseNp()==Count&&f.Get_CaseNfluid()==Count&&!f.Get_CaseNfixed()&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat()&&!f.Get_Nout(),"Sealed native512 scope required");
  Need(f.Get_Data2d()&&f.Get_PeriMode()==PERI_XZ&&!f.Get_NpDynamic()&&!f.Get_ReuseIds()&&!f.Get_Symmetry()&&f.Get_TimeStep()==End&&f.Get_Step()==511,"Only sealed coarse last native PART256 admitted");
  Need(f.Get_Dp()==Dp&&f.Get_H()==double(float(1.8*Dp))&&f.Get_Rhop0()==Rho0&&f.Get_MassFluid()/Rho0==V0,"Sealed native geometry/inertia differs");
  Need(f.GetPart()->ExistsValue("dterror",DatDouble)&&std::isfinite(f.GetPart()->GetvDouble("dterror"))&&f.GetPart()->GetvDouble("dterror")<=1e-14&&f.GetPart()->ExistsValue("SymplecticDtPre",DatDouble)&&f.GetPart()->GetvDouble("SymplecticDtPre")==Dt,"Original saved signed-error/locked-step guard failed");
  Metadata(f,-1);Native a;a.ids=NativeArray<unsigned>(f,"Idp",Count,DatUint);a.pos=NativeArray<tdouble3>(f,"Posd",Count,DatDouble3);a.vel=NativeArray<tfloat3>(f,"Vel",Count,DatFloat3);
  a.sk=NativeArray<tdouble3>(f,"SigmaState_kk",Count,DatDouble3);a.si=NativeArray<tdouble3>(f,"SigmaState_ij",Count,DatDouble3);a.rhop=NativeArray<float>(f,"Rhop",Count,DatFloat);a.plastic=NativeArray<float>(f,"Kplastic",Count,DatFloat);
  a.p=NativeArray<float>(f,"PorePress",Count,DatFloat);a.p0=NativeArray<float>(f,"PorePress0",Count,DatFloat);a.excess=NativeArray<float>(f,"ExcessPorePress",Count,DatFloat);a.fstype=NativeArray<unsigned>(f,"FSType",Count,DatUint);
  a.normal=NativeArray<tfloat3>(f,"FSNormal",Count,DatFloat3);a.load=NativeArray<tfloat3>(f,"HydroMechLoadAce",Count,DatFloat3);a.j=NativeArray<double>(f,"PoroVolumeRatio",Count,DatDouble);a.n=NativeArray<double>(f,"PoroPorosity",Count,DatDouble);a.theta=NativeArray<double>(f,"PoroThetaLastStage",Count,DatDouble);
  const auto sk=NativeArray<tfloat3>(f,"Sigma_kk",Count,DatFloat3),si=NativeArray<tfloat3>(f,"Sigma_ij",Count,DatFloat3);a.slot.assign(Count,~0u);
  for(unsigned p=0;p<Count;p++){Need(a.ids[p]<Count&&a.slot[a.ids[p]]==~0u,"Native ID duplicate/outside512");a.slot[a.ids[p]]=p;Need(a.plastic[p]==0&&a.rhop[p]>=700&&a.rhop[p]<=3000&&a.p0[p]==0&&Norm2(a.load[p])==0&&a.excess[p]==float(a.p[p]-a.p0[p]),"Original native physical guards failed");
    Need(a.j[p]>1.-N0&&std::fabs(a.j[p]-1.)<=1e-4&&Close(a.n[p],1.-(1.-N0)/a.j[p]),"Saved native J/n ledger failed");Need(sk[p].x==float(a.sk[p].x)&&sk[p].y==float(a.sk[p].y)&&sk[p].z==float(a.sk[p].z)&&si[p].x==float(a.si[p].x)&&si[p].y==float(a.si[p].y)&&si[p].z==float(a.si[p].z),"Native display/double stress mismatch");}
  for(unsigned p:a.slot)Need(p!=~0u,"Native ID missing");for(const char* key:{"PoroCurrentVolume","PoroMixtureDensity","PoroHydraulicConductivity","PosDiv"})Need(!f.ArrayExists(key),"Private endpoint has unexpected public-only field");return a;
}
struct Ref{double rate=0,raw=0,budget=0,B=0,k=0;tdouble3 gj=TDouble3(0),gp=TDouble3(0);};
class Audit:public JSphCpuSingle{
  std::vector<unsigned> Owners()const{
    std::vector<unsigned> map(Count,~0u);unsigned native=0,ghosts=0;
    for(unsigned p=0;p<Np;p++){Need(CODE_IsFluid(Codec[p])&&Idpc[p]<Count,"Unexpected endpoint particle type/ID");if(CODE_IsNormal(Codec[p])){Need(map[Idpc[p]]==~0u,"Duplicate native owner");map[Idpc[p]]=p;native++;}else{Need(CODE_IsPeriodic(Codec[p]),"Excluded/unknown endpoint code");ghosts++;}}
    Need(native==Count&&ghosts>0&&!Npb&&!NpbOk&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Actual native/periodic/exclusion witnesses incomplete");return map;
  }
  std::vector<byte> Physical()const{
    std::vector<byte> bytes;const auto map=Owners();auto add=[&](const auto& x){const byte* p=reinterpret_cast<const byte*>(&x);bytes.insert(bytes.end(),p,p+sizeof(x));};
    for(unsigned p:map){add(Idpc[p]);add(Codec[p]);add(Posc[p]);add(Velrhopc[p]);add(Sigmac[p]);add(Kplasticc[p]);add(PorePressc[p]);add(PorePress0c[p]);add(PoroJc[p]);add(HydroMechLoadAcec[p]);}return bytes;
  }
  Ref Reference(unsigned i)const{
    Ref r;double lp=0,lpabs=0,da=0,daabs=0;tdouble3 lx=TDouble3(0);const double alpha=1./((1.-N0)*Ck),gamma=Rhow*9.80665;
    for(unsigned j=0;j<Np;j++)if(CODE_IsFluid(Codec[j])){
      const auto d=TDouble3(Posc[i].x-Posc[j].x,0,Posc[i].z-Posc[j].z);const double rr=Dot(d,d);if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;
      const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr))),gi=Mul(CorrMatc[i],g),gj=Mul(CorrMatc[j],g);const double V=V0*PoroJc[j],dp=double(PorePressc[i])-PorePressc[j],w=V*Dot(d,gi+gj)/(rr+double(Eta2));
      lp+=w*dp;lpabs+=std::fabs(w*dp);lx=lx+d*w;r.gp=r.gp-gi*(V*dp);r.gj=r.gj+gi*(V*(PoroJc[j]-PoroJc[i]));const auto delta=ToTDouble3(Acec[j])-ToTDouble3(Acec[i]);da+=V*Dot(delta,gi);daabs+=V*(std::fabs(delta.x*gi.x)+std::fabs(delta.y*gi.y)+std::fabs(delta.z*gi.z));
    }
    r.B=Kw/(1.-(1.-N0)/PoroJc[i]);r.k=K0*std::exp((PoroJc[i]-1.)/((1.-N0)*Ck));const double chain=alpha*r.k*Dot(r.gj,r.gp+ToTDouble3(Acec[i])*Rhow);
    r.rate=r.B*(-PoroThetac[i]+(r.k*(lp-Dot(r.gp,lx)+Rhow*da)+chain)/gamma);
    r.raw=r.B*(std::fabs(PoroThetac[i])+(r.k*(lpabs+std::fabs(r.gp.x*lx.x)+std::fabs(r.gp.y*lx.y)+std::fabs(r.gp.z*lx.z)+Rhow*daabs)+std::fabs(chain))/gamma);
    r.budget=(32.*FLT_EPSILON+4096.*DBL_EPSILON)*(std::max)(1.,r.raw);Need(std::isfinite(r.rate)&&std::isfinite(r.raw)&&r.budget>0,"Invalid independent raw-term reference");return r;
  }
  double DeltaReference(unsigned i,const std::vector<tfloat3>& base,const Ref& r)const{
    const auto di=ToTDouble3(Acec[i])-ToTDouble3(base[i]);double div=0;
    for(unsigned j=0;j<Np;j++)if(CODE_IsFluid(Codec[j])){const auto d=TDouble3(Posc[i].x-Posc[j].x,0,Posc[i].z-Posc[j].z);const double rr=Dot(d,d);if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;const auto gi=Mul(CorrMatc[i],d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr))));div+=V0*PoroJc[j]*Dot((ToTDouble3(Acec[j])-ToTDouble3(base[j]))-di,gi);}
    return r.B*Rhow/(Rhow*9.80665)*(r.k*div+r.k/((1.-N0)*Ck)*Dot(r.gj,di));
  }
public:
  Audit(){PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreConductivity=true;DynamicPoreConductivityCk=Ck;}
  void Execute(const JSphCfgRun* cfg,JLog2* log,const fs::path& data){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Need(!HydroMechDynamicSeepage&&HydroMechConductivityModel==0&&HydroMechConductivityCk==0&&HydroMech&&Simulate2D&&TStep==STEP_Symplectic&&!PartBegin&&CaseNp==Count&&!CaseNpb&&!CaseNfloat&&!CaseNmoving&&PeriX&&PeriZ&&!PeriY&&OmpThreads==1&&!DynamicPoreWall&&Gravity==TFloat3(-8,0,0)&&CSP.gravity==Gravity,"Actual private endpoint scope differs");
    Need(Dp==endpoint::Dp&&double(KernelH)==double(float(1.8*endpoint::Dp))&&double(RhopZero)==Rho0&&double(MassFluid)/RhopZero==V0&&double(SoilCte.PoreWaterRho)==Rhow&&double(SoilCte.PoreWaterBulkModulus)==Kw&&double(SoilCte.ModulusK)==Bulk&&double(SoilCte.ModulusG)==Shear&&double(SoilCte.Porosity)==N0&&double(SoilCte.HydraulicConductivity)==K0&&SymplecticDtPre==Dt,"Original material/volume/clock differs");
    Need(!HourglassCpu&&!SoilDamping&&!Damping&&!RelaxZones&&!InOut&&!AccInput&&!Shifting&&!SoilBoundaryDerivativeSPR&&!Visco&&!ArtificialStress&&!PoreShepardRegularization&&!HydroMechDrainage&&!HydroMechInitMode&&!HydroMechTopLoadMode,"Unsupported endpoint physics");
    JPartDataBi4 file;file.LoadFilePart(data.string(),endpoint::Part,0,1);const Native source=Load(file);const auto seed=Owners();
    for(unsigned id=0;id<Count;id++){const unsigned p=seed[id],q=source.slot[id];const auto v=source.vel[q];const auto s=source.sk[q],t=source.si[q];Posc[p]=source.pos[q];Velrhopc[p]=TFloat4(v.x,v.y,v.z,source.rhop[q]);Sigmac[p]={s.x,t.x,t.z,s.y,t.y,s.z};Kplasticc[p]=source.plastic[q];PorePressc[p]=source.p[q];PorePress0c[p]=source.p0[q];PoroJc[p]=source.j[q];PoroThetac[p]=source.theta[q];FSTypec[p]=source.fstype[q];FSNormalc[p]=source.normal[q];HydroMechLoadAcec[p]=source.load[q];LoadDcellParticles(1,Codec+p,Posc+p,Dcellc+p);}
    RunCellDivide(true);const auto map=Owners();for(unsigned id=0;id<Count;id++){const unsigned p=map[id],q=source.slot[id];Need(!std::memcmp(Posc+p,&source.pos[q],sizeof(tdouble3))&&PoroJc[p]==source.j[q]&&PorePressc[p]==source.p[q],"Native import/rebuild differs");}
    TimeStep=file.Get_TimeStep();Nstep=file.Get_Step();LastDt=Dt;const double time=TimeStep;const unsigned step=Nstep;const auto physical=Physical();
    Interaction_Forces(INTERSTEP_SymPredictor);Need(Physical()==physical&&TimeStep==time&&Nstep==step&&!PoroJPrec&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec,"Endpoint force advanced physical state or histories");
    const std::vector<tfloat3> ace(Acec,Acec+Np);const std::vector<float> rate(PorePressRatec,PorePressRatec+Np);const double cache=DynamicConductivitySpeedMax;const unsigned np=Np;std::vector<Ref> baseline;for(unsigned p:map)baseline.push_back(Reference(p));
    std::ofstream rows(fs::path(cfg->DirOut)/"rates.csv"),delta(fs::path(cfg->DirOut)/"delta.csv"),summary(fs::path(cfg->DirOut)/"summary.csv");for(auto* o:{&rows,&delta,&summary})*o<<std::setprecision(17);
    rows<<"side,id,saved_last_stage_theta,endpoint_theta,actual_rate,independent_rate,raw_abs_rate,budget,error,ratio,GJ_x,GJ_y,GJ_z\n";delta<<"sign,id,actual_delta_Ax,actual_delta_Ay,actual_delta_Az,actual_rate_difference,independent_delta_rate,ideal_GJ_dot_g_rate,float_quantization_correction,combined_budget,error,ratio,derived_conditional_delta_qx,derived_conditional_delta_qy,derived_conditional_delta_qz\n";summary<<"sign,actual_rate_difference_RMS,ideal_GJ_dot_g_rate_RMS,combined_budget_RMS,actual_signal_over_budget,ideal_signal_over_budget\n";
    double maxRatio=0,maxDeltaRatio=0;unsigned rateRows=0,deltaRows=0;
    auto write=[&](int side,unsigned id,const Ref& r){const unsigned p=map[id];const double error=std::fabs(double(PorePressRatec[p])-r.rate);Need(std::isfinite(PorePressRatec[p])&&error<=r.budget,"Actual complete rate exceeds inherited32FLT raw-term budget");maxRatio=(std::max)(maxRatio,error/r.budget);rows<<side<<','<<id<<','<<source.theta[source.slot[id]]<<','<<PoroThetac[p]<<','<<PorePressRatec[p]<<','<<r.rate<<','<<r.raw<<','<<r.budget<<','<<error<<','<<error/r.budget<<','<<r.gj.x<<','<<r.gj.y<<','<<r.gj.z<<'\n';rateRows++;};
    for(unsigned id=0;id<Count;id++)write(0,id,baseline[id]);
    for(int sign:{-1,1}){
      std::memcpy(Acec,ace.data(),np*sizeof(tfloat3));for(unsigned p:map)Acec[p]=ToTFloat3(ToTDouble3(ace[p])+ToTDouble3(Gravity)*double(sign));ComputeDynamicPorePressureRateCpu();double sd=0,si=0,sb=0;
      for(unsigned id=0;id<Count;id++){const unsigned p=map[id];const Ref r=Reference(p);write(sign,id,r);const auto da=ToTDouble3(Acec[p])-ToTDouble3(ace[p]);const double observed=double(PorePressRatec[p])-rate[p],reference=DeltaReference(p,ace,baseline[id]),ideal=sign*baseline[id].B*Rhow/(Rhow*9.80665)*baseline[id].k/((1.-N0)*Ck)*Dot(baseline[id].gj,ToTDouble3(Gravity)),budget=baseline[id].budget+r.budget,error=std::fabs(observed-reference);const auto dq=da*(-baseline[id].k*Rhow/(Rhow*9.80665));Need(error<=budget,"Actual delta rate exceeds sum of unchanged side budgets");maxDeltaRatio=(std::max)(maxDeltaRatio,error/budget);sd+=observed*observed;si+=ideal*ideal;sb+=budget*budget;delta<<sign<<','<<id<<','<<da.x<<','<<da.y<<','<<da.z<<','<<observed<<','<<reference<<','<<ideal<<','<<reference-ideal<<','<<budget<<','<<error<<','<<error/budget<<','<<dq.x<<','<<dq.y<<','<<dq.z<<'\n';deltaRows++;}
      const double signal=std::sqrt(sd/Count),ideal=std::sqrt(si/Count),budget=std::sqrt(sb/Count);Need(signal>10*budget&&ideal>10*budget,"Wrong explicit-g / GJ-dot-g endpoint signal is empty against prior combined budget");summary<<sign<<','<<signal<<','<<ideal<<','<<budget<<','<<signal/budget<<','<<ideal/budget<<'\n';
    }
    std::memcpy(Acec,ace.data(),np*sizeof(tfloat3));std::memcpy(PorePressRatec,rate.data(),np*sizeof(float));DynamicConductivitySpeedMax=cache;Need(Np==np&&Physical()==physical&&TimeStep==time&&Nstep==step&&!std::memcmp(Acec,ace.data(),np*sizeof(tfloat3))&&!std::memcmp(PorePressRatec,rate.data(),np*sizeof(float))&&DynamicConductivitySpeedMax==cache,"Covered state / temporary Ace-rate-cache restoration failed");PosInteraction_Forces();
    Need(rateRows==1536&&deltaRows==1024&&!Acec&&!Arc&&!PoroJPrec&&!PosPrec,"Endpoint component coverage or scratch release failed");for(auto* o:{&rows,&delta,&summary}){o->flush();Need(bool(*o),"Endpoint CSV write failed");}
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"passed\":true,\"stage\":\"upl_gravity_endpoint_cpu_r1\",\"native_count\":512,\"source_part\":256,\"source_time_s\":"<<time<<",\"source_saved_step\":"<<step<<",\"actual_endpoint_force_calls\":1,\"additional_complete_rate_calls\":2,\"rate_rows\":"<<rateRows<<",\"delta_rows\":"<<deltaRows<<",\"max_single_rate_error_over_original_budget\":"<<maxRatio<<",\"max_delta_error_over_combined_budget\":"<<maxDeltaRatio<<",\"wrong_g_both_signals_over_10_RMS_budget\":true,\"same_state_covered_physical_bytes_unchanged\":true,\"temporary_Ace_rate_cache_restored\":true,\"saved_theta_not_endpoint_theta\":true,\"actual_C_conditioned_reference\":true,\"q_difference_is_derived_conditional_not_native\":true,\"Run_or_ComputeStep_called\":false,\"PART_restart\":false,\"completed_physical_steps\":0,\"input_SHA_before_after_checked_by_component\":false,\"public_gravity_accepted\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Endpoint completion write failed");
  }
};
}
int main(int argc,char** argv){try{
  Need(argc==5&&std::string(argv[1])=="--audit","Use --audit SEALED_COARSE_DATA_DIR EXACT_CASEGRAVITY_C_XML NEW_OUT");const fs::path data=argv[2],xml=argv[3],out=argv[4];Need(fs::is_regular_file(xml)&&fs::is_regular_file(data/JPartDataBi4::GetFileNamePart(256))&&!fs::exists(out),"Sealed endpoint input/fresh output required");
  JXml x;x.LoadFile(xml.string());const auto h=x.GetNodeError("case.execution.special.hydromechanics");Need(!x.ReadElementBool(h,"HydroMechDynamicSeepage","value")&&x.ReadElementUnsigned(h,"HydroMechConductivityModel","value")==0&&x.ReadElementDouble(h,"HydroMechConductivityCk","value")==0,"Only explicit private XML/masterOFF admitted");
  AppInfo.ConfigRunPaths(argv[0]);auto prefix=xml;prefix.replace_extension();std::vector<std::string> args={argv[0],"-cpu","-ompthreads:1","-stable",prefix.string(),out.string(),"-dirdataout","data","-svres"};std::vector<char*> pointers;for(auto& a:args)pointers.push_back(a.data());JSphCfgRun cfg;cfg.LoadArgv(int(pointers.size()),pointers.data());Need(cfg.Cpu&&cfg.OmpThreads==1&&!cfg.PrintInfo&&!cfg.PartBegin&&!cfg.NstepsBreak&&cfg.TimeMax<0&&cfg.TimePart<0&&!cfg.SvAllSteps,"No restart/Run/clock override allowed");
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");endpoint::Audit fixture;fixture.Execute(&cfg,AppInfo.LogPtr(),data);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Frozen endpoint component rejected; preserve all evidence\n";return 2;}}
