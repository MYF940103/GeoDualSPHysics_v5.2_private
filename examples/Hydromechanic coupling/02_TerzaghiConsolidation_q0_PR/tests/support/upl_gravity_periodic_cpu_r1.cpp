// Private CPU true-Run entry and separately invoked, read-only native review.
// Public gravity remains rejected. No solver fields or integration stages are overridden.
#define main RetainedGravityPeriodicNativeMain
#include "upl_cpu_public_native_r1.cpp"
#undef main
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JXml.h"
#include "JLog2.h"

namespace gravityperiodic {
constexpr unsigned Count=512,Columns=33;
constexpr double Dp=1./256.,V0=Dp*Dp,Gx=-8.,DtC=1./16777216.,DtH=1./33554432.,End=1./32768.,Cadence=1./8388608.;
struct Window{const char* name;double dt,end,cadence;unsigned steps,samples;};
static Window Select(const std::string& name){
  if(name=="smoke")return{"smoke",DtC,2.*DtC,DtC,2,3};
  if(name=="coarse")return{"coarse",DtC,End,Cadence,512,257};
  if(name=="half")return{"half",DtH,End,Cadence,1024,257};
  throw std::runtime_error("Use the declared smoke|coarse|half window");
}
static void Fresh(const fs::path& p){Need(!fs::exists(p),"Retained output protected: "+p.string());}
static void Runtime(const fs::path& path,const Window& w){
  JXml x;x.LoadFile(path.string());const auto* h=x.GetNodeError("case.execution.special.hydromechanics");
  const auto* c=x.GetNodeError("case.execution.constants");const auto* s=x.GetNodeError("case.execution.special.soils");
  auto hv=[&](const char* key,double value){Need(x.ReadElementDouble(h,key,"value")==value,"Runtime hydromechanics differs: "+std::string(key));};
  hv("HydroMech",1);hv("PoreWaterRho",Rhow);hv("PoreWaterBulkModulus",Kw);hv("Porosity",N0);hv("HydraulicConductivity",.0001);
  hv("PoreDtSafety",.1);hv("PoreShepardRegularization",0);hv("PoreCompressionGradCorr",1);hv("PoreCompressionSourceMode",0);
  hv("HydroMechInitMode",0);hv("HydroMechTopLoadMode",0);hv("HydroMechDrainage",0);
  hv("HydroMechDynamicSeepage",0);hv("HydroMechConductivityModel",0);hv("HydroMechConductivityCk",0);
  Need(x.GetAttributeDouble3(x.GetFirstElement(c,"gravity"))==TDouble3(Gx,0,0),"Real runtime body gravity must be (-8,0,0)");
  Need(x.GetAttributeDouble3(x.GetFirstElement(x.GetNodeError("case.casedef.constantsdef"),"gravity"))==TDouble3(Gx,0,0),"Casedef/execution gravity differs");
  Need(x.ReadElementDouble(c,"rhop0","value")==Rho0&&x.ReadElementDouble(c,"dp","value")==Dp&&x.ReadElementDouble(c,"h","value")==1.8*Dp&&x.ReadElementDouble(c,"massfluid","value")==Rho0*V0,"Runtime geometry/material differs");
  Need(x.ReadElementDouble(s,"ModulusE","value")==268435456.&&x.ReadElementDouble(s,"PRvs","value")==0&&x.ReadElementDouble(s,"phi","value")==0&&x.ReadElementDouble(s,"coh","value")==1e12&&x.ReadElementDouble(s,"dlt","value")==0,"Runtime elastic material differs");
  std::map<std::string,double> p;for(auto* e=x.GetNodeError("case.execution.parameters")->FirstChildElement("parameter");e;e=e->NextSiblingElement("parameter"))Need(p.emplace(x.GetAttributeStr(e,"key"),x.GetAttributeDouble(e,"value")).second,"Duplicate runtime parameter");
  auto pv=[&](const char* key,double v){Need(p.count(key)&&p.at(key)==v,"Runtime option/clock differs: "+std::string(key));};
  pv("SavePosDouble",1);pv("DPCtes",3);pv("Boundary",1);pv("StepAlgorithm",2);pv("Kernel",2);pv("ViscoTreatment",1);pv("Visco",0);pv("ArtificialStress",0);
  pv("SoilStressRateGradCorr",1);pv("SoilHourglassXi",0);pv("SoilBoundaryDerivativeSPR",0);pv("SoilDamping",0);pv("DensityDT",0);pv("Shifting",0);
  pv("DtIni",w.dt);pv("DtFixed",w.dt);pv("DtMin",1e-10);pv("TimeMax",w.end);pv("TimeOut",w.cadence);pv("PartsOutMax",0);pv("RhopOutMin",700);pv("RhopOutMax",3000);pv("XZPeriodic",1);
}
// Reuse only backend-neutral typed extraction/sequence/metadata helpers from the
// immutable reader. Its public Load/Read/Energy/26-column exporter are never called.
static Native LoadPrivate(JPartDataBi4& f){
  Metadata(f,-1);Native a;a.ids=NativeArray<unsigned>(f,"Idp",Count,DatUint);a.pos=NativeArray<tdouble3>(f,"Posd",Count,DatDouble3);Need(!f.ArrayExists("Pos"),"Double saved positions required");
  a.vel=NativeArray<tfloat3>(f,"Vel",Count,DatFloat3);a.rhop=NativeArray<float>(f,"Rhop",Count,DatFloat);
  a.legacykk=NativeArray<tfloat3>(f,"Sigma_kk",Count,DatFloat3);a.legacyij=NativeArray<tfloat3>(f,"Sigma_ij",Count,DatFloat3);
  a.sk=NativeArray<tdouble3>(f,"SigmaState_kk",Count,DatDouble3);a.si=NativeArray<tdouble3>(f,"SigmaState_ij",Count,DatDouble3);
  a.plastic=NativeArray<float>(f,"Kplastic",Count,DatFloat);a.fstype=NativeArray<unsigned>(f,"FSType",Count,DatUint);
  a.normal=NativeArray<tfloat3>(f,"FSNormal",Count,DatFloat3);a.load=NativeArray<tfloat3>(f,"HydroMechLoadAce",Count,DatFloat3);
  a.p=NativeArray<float>(f,"PorePress",Count,DatFloat);a.p0=NativeArray<float>(f,"PorePress0",Count,DatFloat);a.excess=NativeArray<float>(f,"ExcessPorePress",Count,DatFloat);
  a.j=NativeArray<double>(f,"PoroVolumeRatio",Count,DatDouble);a.n=NativeArray<double>(f,"PoroPorosity",Count,DatDouble);a.theta=NativeArray<double>(f,"PoroThetaLastStage",Count,DatDouble);
  for(const char* name:{"PoroCurrentVolume","PoroMixtureDensity","PoroHydraulicConductivity","PosDiv"})Need(!f.ArrayExists(name),"Private CPU output must not pretend public extra arrays");
  a.slot.assign(Count,~0u);for(unsigned p=0;p<Count;p++){Need(a.ids[p]<Count&&a.slot[a.ids[p]]==~0u,"Invalid/duplicate native ID");a.slot[a.ids[p]]=p;}for(unsigned p:a.slot)Need(p!=~0u,"Missing native ID");return a;
}
static void Read(const Window& w,const fs::path& dir,const fs::path& xml,const fs::path& target){
  Runtime(xml,w);Fresh(target);Sequence(dir,w.samples);fs::create_directory(target);
  std::ofstream inertial(target/"physical.bin",std::ios::binary),accelerated(target/"frame.bin",std::ios::binary),history(target/"history.csv"),ids(target/"native_ids.csv"),last(target/"last_poro.csv");
  const unsigned head[]={Count,Columns,w.samples};inertial.write(reinterpret_cast<const char*>(head),12);accelerated.write(reinterpret_cast<const char*>(head),12);
  for(auto* o:{&history,&ids,&last})*o<<std::setprecision(17);
  ids<<"row,id,x0,y0,z0\n";last<<"id,J,n,theta\n";
  history<<"part,time_s,saved_step,dt_s,signed_dterror_s,accelerating_frame_energy_ratio,inertial_energy_ratio,pressure_RMS_Pa,frame_material_displacement_max_mm,max_abs_J_minus_1,min_n,max_n,min_current_k_m_s,max_current_k_m_s,k_span_over_k0,max_coupled_CFL,max_Ddt_h2,min_continuous_margin_kg_m3,unweighted_mean_vx,unweighted_mean_frame_vx,expected_uniform_body_velocity_shift\n";
  std::vector<tdouble3> initial(Count);double e0=0,maxEnergy=0,maxJ=0,maxSpan=0,maxCfl=0,maxDiff=0,minMargin=DBL_MAX,maxError=-DBL_MAX,minError=DBL_MAX,maxLedger=0;unsigned rows=0;
  const double h=double(float(1.8*Dp)),gamma=Rhow*9.80665;
  for(unsigned part=0;part<w.samples;part++){
    JPartDataBi4 file;file.LoadFilePart(dir.string(),part,0,1);
    Need(file.GetNpiece()==1&&file.Get_Npok()==Count&&!file.Get_Nout()&&file.Get_CaseNp()==Count&&file.Get_CaseNfluid()==Count&&!file.Get_CaseNfixed()&&!file.Get_CaseNmoving()&&!file.Get_CaseNfloat(),"Native particle set/exclusions changed");
    Need(file.Get_Data2d()&&!file.Get_Symmetry()&&!file.Get_NpDynamic()&&!file.Get_ReuseIds()&&file.Get_PeriMode()==PERI_XZ,"Native periodic/2D scope differs");
    Need(file.Get_Dp()==Dp&&file.Get_H()==h&&file.Get_Rhop0()==Rho0&&file.Get_MassFluid()/Rho0==V0,"Native geometry/inertia differs");
    const double time=file.Get_TimeStep();const unsigned step=part?unsigned(std::llround(part*w.cadence/w.dt))-1:0;
    Need(time==part*w.cadence&&file.Get_Step()==step&&file.GetPart()->ExistsValue("SymplecticDtPre",DatDouble)&&file.GetPart()->GetvDouble("SymplecticDtPre")==w.dt,"Native actual clock/zero-based step/locked dt differs");
    Need(file.GetPart()->ExistsValue("dterror",DatDouble),"Native signed dterror missing");const double error=file.GetPart()->GetvDouble("dterror");Need(std::isfinite(error)&&error<=1e-14,"Original signed fixed-step guard failed");minError=(std::min)(minError,error);maxError=(std::max)(maxError,error);
    const Native a=LoadPrivate(file);double energy=0,labEnergy=0,p2=0,umax=0,jn=0,nlo=DBL_MAX,nhi=0,klo=DBL_MAX,khi=0,cflmax=0,diffmax=0,marginmin=DBL_MAX,meanVx=0,meanFrameVx=0;
    inertial.write(reinterpret_cast<const char*>(&time),8);accelerated.write(reinterpret_cast<const char*>(&time),8);
    for(unsigned id=0;id<Count;id++){
      const unsigned p=a.slot[id];const auto x=a.pos[p],s=a.sk[p],q=a.si[p];const auto v=a.vel[p];const double j=a.j[p],n=1.-(1.-N0)/j,V=V0*j,rho=Rhow+(Rho0-Rhow)/j,k=K0*std::exp((j-1.)/((1.-N0)*Ck));
      Need(j>1.-N0&&std::fabs(j-1.)<=1e-4&&n>0&&n<1&&std::isfinite(V)&&V>0&&std::isfinite(rho)&&rho>0&&std::isfinite(k)&&k>0,"Original weak saturated/current-k domain failed");
      Need(Close(a.n[p],n)&&std::fabs((1.-a.n[p])*j-(1.-N0))<=5e-13,"Native solid-volume ledger failed");maxLedger=(std::max)(maxLedger,std::fabs(a.n[p]-n)/n);
      Need(a.plastic[p]==0&&a.rhop[p]>=700&&a.rhop[p]<=3000&&a.p0[p]==0&&Norm2(a.load[p])==0&&a.excess[p]==float(a.p[p]-a.p0[p]),"Elastic/passive-rho/p0/load/native-excess guard failed");
      Need(a.legacykk[p].x==float(s.x)&&a.legacykk[p].y==float(s.y)&&a.legacykk[p].z==float(s.z)&&a.legacyij[p].x==float(q.x)&&a.legacyij[p].y==float(q.y)&&a.legacyij[p].z==float(q.z),"Display stress does not round actual double state");
      Need(x.y==0&&x.x>0&&x.x<Lx&&x.z>0&&x.z<Lz,"This short declared window must not cross a primary periodic boundary");
      if(!part){initial[id]=x;const double ix=x.x/Dp-.5,iz=x.z/Dp-.5;Need(ix==std::round(ix)&&iz==std::round(iz)&&ix>=0&&ix<32&&iz>=0&&iz<16,"Initial lattice differs");Need(v.x==float(A*std::sin(2.*std::acos(-1.)*x.x/Lx))&&v.y==0&&v.z==0&&a.p[p]==0&&Norm2(s)==0&&Norm2(q)==0&&j==1.&&a.n[p]==N0&&a.theta[p]==0,"Initial true-Run sine/p0/J state differs");ids<<id<<','<<id<<','<<x.x<<','<<x.y<<','<<x.z<<'\n';}
      const tdouble3 u=x-initial[id],xf=TDouble3(x.x-.5*Gx*time*time,x.y,x.z),vf=TDouble3(double(v.x)-Gx*time,v.y,v.z),uf=TDouble3(u.x-.5*Gx*time*time,u.y,u.z);
      const double tr=s.x+s.y+s.z,mean=tr/3.,dev=(s.x-mean)*(s.x-mean)+(s.y-mean)*(s.y-mean)+(s.z-mean)*(s.z-mean)+2.*Norm2(q);
      const double stored=dev/(4.*Shear)+tr*tr/(18.*Bulk)+n*double(a.p[p])*a.p[p]/(2.*Kw);energy+=V*(.5*rho*Norm2(vf)+stored);labEnergy+=V*(.5*rho*Norm2(v)+stored);
      const double B=Kw/n,cfl=std::sqrt((Bulk+4.*Shear/3.+B)/rho)*w.dt/h,diff=B*k/gamma*w.dt/(h*h),margin=rho*B/(Bulk+4.*Shear/3.+B)-Rhow;
      Need(std::isfinite(cfl)&&cfl<=.01&&std::isfinite(diff)&&diff<=.01&&margin>64.*DBL_EPSILON*(std::max)(rho,Rhow),"Original necessary saved acoustic/diffusion/continuous-domain screen failed");
      std::array<double,Columns> row={x.x,x.y,x.z,double(v.x),double(v.y),double(v.z),double(a.p[p]),double(a.p0[p]),j,a.theta[p],s.x,q.x,q.z,s.y,q.y,s.z,double(a.plastic[p]),double(a.fstype[p]),double(a.normal[p].x),double(a.normal[p].y),double(a.normal[p].z),double(a.load[p].x),double(a.load[p].y),double(a.load[p].z),double(a.rhop[p]),u.x,u.y,u.z,double(a.excess[p]),a.n[p],V,rho,k};
      inertial.write(reinterpret_cast<const char*>(row.data()),Columns*8);row[0]=xf.x;row[1]=xf.y;row[2]=xf.z;row[3]=vf.x;row[4]=vf.y;row[5]=vf.z;row[25]=uf.x;row[26]=uf.y;row[27]=uf.z;accelerated.write(reinterpret_cast<const char*>(row.data()),Columns*8);
      p2+=double(a.p[p])*a.p[p];meanVx+=v.x;meanFrameVx+=vf.x;umax=(std::max)(umax,1000.*std::sqrt(Norm2(uf)));jn=(std::max)(jn,std::fabs(j-1.));nlo=(std::min)(nlo,n);nhi=(std::max)(nhi,n);klo=(std::min)(klo,k);khi=(std::max)(khi,k);cflmax=(std::max)(cflmax,cfl);diffmax=(std::max)(diffmax,diff);marginmin=(std::min)(marginmin,margin);rows++;
      if(part+1==w.samples)last<<id<<','<<j<<','<<a.n[p]<<','<<a.theta[p]<<'\n';
    }
    if(!part){e0=energy;Need(std::isfinite(e0)&&e0>0,"Initial wave energy is empty");}const double ratio=energy/e0;Need(std::isfinite(ratio)&&ratio<=1.1,"Original wave energy budget failed in accelerating frame");
    maxEnergy=(std::max)(maxEnergy,ratio);maxJ=(std::max)(maxJ,jn);maxSpan=(std::max)(maxSpan,(khi-klo)/K0);maxCfl=(std::max)(maxCfl,cflmax);maxDiff=(std::max)(maxDiff,diffmax);minMargin=(std::min)(minMargin,marginmin);
    history<<part<<','<<time<<','<<step<<','<<w.dt<<','<<error<<','<<ratio<<','<<labEnergy/e0<<','<<std::sqrt(p2/Count)<<','<<umax<<','<<jn<<','<<nlo<<','<<nhi<<','<<klo<<','<<khi<<','<<(khi-klo)/K0<<','<<cflmax<<','<<diffmax<<','<<marginmin<<','<<meanVx/Count<<','<<meanFrameVx/Count<<','<<Gx*time<<'\n';
  }
  Need(rows==Count*w.samples&&maxJ>(w.samples==3?0.:1e-8)&&(w.samples==3||maxSpan>=.005),"Original nonempty J/k evolution/full native coverage failed");
  for(auto* o:{&inertial,&accelerated,&history,&ids,&last}){o->flush();Need(bool(*o),"Native review write failed");}
  std::ofstream done(target/"completion.json");done<<std::setprecision(17)<<"{\"passed\":true,\"stage\":\"upl_gravity_periodic_cpu_r1\",\"window\":\""<<w.name<<"\",\"backend\":\"CPU_private\",\"samples\":"<<w.samples<<",\"native_count\":512,\"fixed_count\":0,\"common_columns\":33,\"dt_s\":"<<w.dt<<",\"cadence_s\":"<<w.cadence<<",\"actual_end_s\":"<<w.end<<",\"native_rows\":"<<rows<<",\"gravity_x_m_s2\":-8,\"private_Ck\":"<<Ck<<",\"native_J_arrays\":3,\"V_rho_k_derived_not_native\":true,\"native_PosDiv_available\":false,\"public_dynamic_metadata\":false,\"max_frame_energy_ratio\":"<<maxEnergy<<",\"max_abs_J_minus_1\":"<<maxJ<<",\"max_k_span_over_k0\":"<<maxSpan<<",\"max_saved_coupled_CFL\":"<<maxCfl<<",\"max_saved_Ddt_h2\":"<<maxDiff<<",\"min_continuous_margin\":"<<minMargin<<",\"max_ledger_relative_error\":"<<maxLedger<<",\"min_signed_dterror_s\":"<<minError<<",\"max_signed_dterror_s\":"<<maxError<<",\"half_comparison_performed\":false,\"g0_frame_comparison_performed\":false,\"force_stage_gradient_independently_observed\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Native completion write failed");
}
class PeriodicGravityCpu:public JSphCpuSingle{
public:
  PeriodicGravityCpu(){PorosityObserver=PorosityFeedback=DynamicPorePressure=true;DynamicPoreConductivity=true;DynamicPoreConductivityCk=Ck;}
  void Finish(const fs::path& out,const Window& w){
    Need(PorosityObserver&&PorosityFeedback&&DynamicPorePressure&&DynamicPoreConductivity&&!DynamicPoreWall&&!HydroMechDynamicSeepage&&HydroMechConductivityModel==0&&HydroMechConductivityCk==0&&DynamicPoreConductivityCk==Ck,"Actual Run left its explicit private model");
    Need(HydroMech&&Simulate2D&&TStep==STEP_Symplectic&&!PartBegin&&!CaseNpb&&!CaseNfloat&&!CaseNmoving&&CaseNp==Count&&CaseNfluid==Count&&PeriX&&PeriZ&&!PeriY&&OmpThreads==1&&Gravity==TFloat3(Gx,0,0)&&CSP.gravity==Gravity,"Actual Run geometry/gravity/backend scope differs");
    Need(TimeStep==w.end&&Nstep==w.steps&&SymplecticDtPre==w.dt&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Actual Run end/steps/locked clock/PRE release differs");
    Need(double(SoilCte.HydraulicConductivity)==K0&&double(SoilCte.Porosity)==N0&&double(RhopZero)==Rho0&&double(SoilCte.PoreWaterRho)==Rhow&&double(SoilCte.PoreWaterBulkModulus)==Kw&&double(SoilCte.ModulusK)==Bulk&&double(SoilCte.ModulusG)==Shear,"Actual Run loaded material differs");
    Need(std::isfinite(DynamicConductivitySpeedMax)&&DynamicConductivitySpeedMax>=0,"Actual last-force cache invalid");std::vector<unsigned> order(Count,~0u);
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){Need(CODE_IsFluid(Codec[p])&&Idpc[p]<Count&&order[Idpc[p]]==~0u,"Actual final native ID/code differs");order[Idpc[p]]=p;}
    Fresh(out/"live_final.csv");Fresh(out/"actual_complete.json");std::ofstream live(out/"live_final.csv");live<<std::setprecision(17)<<"id,J,n,theta\n";
    for(unsigned id=0;id<Count;id++){Need(order[id]!=~0u,"Final native missing");const unsigned p=order[id];double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);Need(std::isfinite(PoroJc[p])&&PoroJc[p]>1.-N0&&std::isfinite(PoroThetac[p])&&n>0&&n<1&&Kplasticc[p]==0,"Actual final ledger/elastic state invalid");live<<id<<','<<PoroJc[p]<<','<<n<<','<<PoroThetac[p]<<'\n';}live.flush();Need(bool(live),"Final live export failed");
    std::ofstream done(out/"actual_complete.json");done<<std::setprecision(17)<<"{\"passed\":true,\"stage\":\"upl_gravity_periodic_cpu_r1\",\"window\":\""<<w.name<<"\",\"actual_production_Run\":true,\"private_feedback\":true,\"private_complete_dynamic_rate\":true,\"private_conductivity_Ck\":"<<Ck<<",\"public_master\":false,\"physical_fields_rewritten_by_fixture\":false,\"native_count\":512,\"completed_steps\":"<<Nstep<<",\"actual_end_s\":"<<TimeStep<<",\"dt_s\":"<<SymplecticDtPre<<",\"gravity_x_m_s2\":-8,\"predictor_histories_released\":true,\"last_force_gradient_speed_m_s\":"<<DynamicConductivitySpeedMax<<",\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Actual completion write failed");
  }
};
}
int main(int argc,char** argv){try{
  Need(argc>=3,"Use --solver WINDOW ordinaryCPUargs or --read WINDOW DATA XML NEWREVIEW");const std::string mode=argv[1];const auto w=gravityperiodic::Select(argv[2]);
  if(mode=="--read"){Need(argc==6,"Reader requires WINDOW DATA XML NEWREVIEW");gravityperiodic::Read(w,argv[3],argv[4],argv[5]);return 0;}
  Need(mode=="--solver"&&argc>=6,"Solver requires WINDOW and ordinary explicit CPU arguments");AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=3;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());
  Need(cfg.Cpu&&cfg.OmpThreads==1&&!cfg.PrintInfo&&!fs::exists(cfg.DirOut)&&cfg.PartBegin==0&&cfg.NstepsBreak==0&&cfg.TimeMax<0&&cfg.TimePart<0&&!cfg.SvAllSteps,"Fresh CPU OMP1 actual Run with XML clocks and no CLI override/restart required");gravityperiodic::Runtime(cfg.CaseName+".xml",w);
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");gravityperiodic::PeriodicGravityCpu fixture;fixture.Run(AppInfo.GetFullName(),&cfg,AppInfo.LogPtr());fixture.Finish(cfg.DirOut,w);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Private CPU gravity actual Run/read rejected; preserve evidence\n";return 2;}}
