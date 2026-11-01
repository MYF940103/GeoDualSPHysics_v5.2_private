// Actual private GPU k=0 Run entry and offline CPU/GPU common native export.
// Reuse the sealed typed-array/ID/telemetry utilities, not its observer-only entry.
#define main RetainedObserverNativeMain
#include "upl_gpu_observer_native_r1.cpp"
#undef main
#include <array>
#include <cfloat>
namespace k0 {
using TpData=JBinaryDataDef::TpData;
static constexpr TpData DatBool=JBinaryDataDef::DatBool,DatUint=JBinaryDataDef::DatUint,DatFloat=JBinaryDataDef::DatFloat,
  DatDouble=JBinaryDataDef::DatDouble,DatFloat3=JBinaryDataDef::DatFloat3,DatDouble3=JBinaryDataDef::DatDouble3;
constexpr unsigned Count=512,Samples=257,Columns=33;
constexpr double DtC=1./16777216.,DtH=1./33554432.,Cadence=1./8388608.,End=1./32768.;
constexpr double Dp=1./256.,Lx=1./8.,Lz=1./16.,A=1./512.,N0=.25,Rho0=2048.,Rhow=1000.,Kw=67108864.;
constexpr double Bulk=89478488.,Shear=134217728.,V0=Dp*Dp;
static double Cu0(){return std::sqrt((Bulk+4.*Shear/3.+Kw/N0)/Rho0);}
static double Pstar(){return (Kw/N0)*A/Cu0();}
static double Ustar(){return A/(Cu0()*2.*std::acos(-1.)/Lx);}
static bool Finite(double x){return std::isfinite(x);}
static bool Finite(float x){return std::isfinite(x);}
static bool Finite(unsigned){return true;}
static bool Finite(tfloat3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}
static bool Finite(tdouble3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}
static double Norm2(tdouble3 x){return x.x*x.x+x.y*x.y+x.z*x.z;}
static double Norm2(tfloat3 x){return double(x.x)*x.x+double(x.y)*x.y+double(x.z)*x.z;}
static bool LedgerClose(double x,double y){return Finite(x)&&Finite(y)&&(y==0?x==0:std::fabs(x-y)<=5e-13*std::fabs(y));}
template<class T>static std::vector<T> ReadArray(JPartDataBi4& file,const char* name,JBinaryDataDef::TpData type){
  auto v=NativeArray<T>(file,name,Count,type);for(const auto& a:v)Check(k0::Finite(a),name);return v;
}
struct Native{
  std::vector<unsigned> id,type,order;
  std::vector<tdouble3> x,sk,si;
  std::vector<tfloat3> v,legacykk,legacyij,normal,load;
  std::vector<float> rho,plastic,p,p0,excess,posdiv;
  std::vector<double> j,n,theta,volume,inertia,conductivity;
};
static Native Load(JPartDataBi4& file,bool cpu){
  Native a;
  a.id=ReadArray<unsigned>(file,"Idp",DatUint);a.order=Order(a.id);a.type=ReadArray<unsigned>(file,"FSType",DatUint);
  a.x=ReadArray<tdouble3>(file,"Posd",DatDouble3);Check(!file.ArrayExists("Pos"),"Expected native double position storage");
  a.sk=ReadArray<tdouble3>(file,"SigmaState_kk",DatDouble3);a.si=ReadArray<tdouble3>(file,"SigmaState_ij",DatDouble3);
  a.v=ReadArray<tfloat3>(file,"Vel",DatFloat3);a.legacykk=ReadArray<tfloat3>(file,"Sigma_kk",DatFloat3);a.legacyij=ReadArray<tfloat3>(file,"Sigma_ij",DatFloat3);
  a.normal=ReadArray<tfloat3>(file,"FSNormal",DatFloat3);a.load=ReadArray<tfloat3>(file,"HydroMechLoadAce",DatFloat3);
  a.rho=ReadArray<float>(file,"Rhop",DatFloat);a.plastic=ReadArray<float>(file,"Kplastic",DatFloat);a.p=ReadArray<float>(file,"PorePress",DatFloat);
  a.p0=ReadArray<float>(file,"PorePress0",DatFloat);a.excess=ReadArray<float>(file,"ExcessPorePress",DatFloat);
  a.j=ReadArray<double>(file,"PoroVolumeRatio",DatDouble);a.n=ReadArray<double>(file,"PoroPorosity",DatDouble);a.theta=ReadArray<double>(file,"PoroThetaLastStage",DatDouble);
  const char* derived[]={"PoroCurrentVolume","PoroMixtureDensity","PoroHydraulicConductivity"};
  for(const char* key:derived)Check(file.ArrayExists(key)==cpu,"Wrong backend native derived-array presence");
  Check(file.ArrayExists("PosDiv")==cpu,"GPU PosDiv is absent, not a fabricated common zero column");
  if(cpu){
    a.volume=ReadArray<double>(file,derived[0],DatDouble);a.inertia=ReadArray<double>(file,derived[1],DatDouble);a.conductivity=ReadArray<double>(file,derived[2],DatDouble);
    a.posdiv=ReadArray<float>(file,"PosDiv",DatFloat);
  }return a;
}
static void Metadata(JPartDataBi4& file,bool cpu){
  const auto* part=file.GetPart();
  const char* keys[]={"HydroMechDynamicSeepage","DynamicSeepageSchema","HydroMechConductivityModel","HydroMechConductivityCk"};
  for(const char* key:keys)Check(part->ExistsValue(key)==cpu,"Wrong private-GPU/public-CPU metadata presence");
  if(cpu){
    Check(part->ExistsValue(keys[0],DatBool)&&part->GetvBool(keys[0]),"CPU public master must be true");
    Check(part->ExistsValue(keys[1],DatUint)&&part->GetvUint(keys[1])==1,"CPU schema must be uint1");
    Check(part->ExistsValue(keys[2],DatUint)&&part->GetvUint(keys[2])==0,"CPU conductivity model must be constant0");
    Check(part->ExistsValue(keys[3],DatDouble)&&part->GetvDouble(keys[3])==0.,"CPU constant model Ck must be double0");
  }
}
static void Sequence(const fs::path& dir,unsigned samples){
  unsigned found=0;Check(fs::is_directory(dir),"Native data directory missing");
  for(const auto& entry:fs::directory_iterator(dir))if(entry.is_regular_file()&&entry.path().extension()==".bi4"&&entry.path().filename().string().rfind("Part_",0)==0)found++;
  Check(found==samples,"Extra/missing PART or piece files");
  for(unsigned p=0;p<samples;p++)Check(fs::is_regular_file(dir/JPartDataBi4::GetFileNamePart(p)),"Missing expected PART");
}
static void Read(const char* backend,const fs::path& dir,double dt,const fs::path& target,bool smoke){
  const bool cpu=std::string(backend)=="CPU";Check(cpu||std::string(backend)=="GPU","Backend must be CPU or GPU");
  Check(smoke?(!cpu&&dt==DtC):(dt==DtC||dt==DtH),"Only declared GPU smoke or full coarse/half admitted");
  const unsigned samples=smoke?3:Samples;const double cadence=smoke?DtC:Cadence,end=smoke?2.*DtC:End;
  Fresh(target);Sequence(dir,samples);fs::create_directory(target);
  std::ofstream binary(target/"physical.bin",std::ios::binary),ids(target/"native_ids.csv"),history(target/"history.csv"),posdiv;
  if(cpu)posdiv.open(target/"cpu_posdiv.csv");const unsigned header[]={Count,Columns,samples};binary.write(reinterpret_cast<const char*>(header),sizeof(header));
  ids<<std::setprecision(17);history<<std::setprecision(17);if(cpu)posdiv<<std::setprecision(17)<<"part,id,actual_native_PosDiv\n";
  ids<<"row,id,x0,y0,z0\n";history<<"part,time_s,saved_step,dt_s,dterror_s,energy_ratio,pressure_RMS_Pa,max_material_displacement_mm,max_abs_J_minus_1,min_n,max_n,max_coupled_CFL\n";
  std::vector<tdouble3> initial(Count);double energy0=0.,maxEnergy=0.,maxJ=0.,maxCfl=0.,maxLedger=0.,minError=DBL_MAX,maxError=-DBL_MAX;unsigned ledgerChecks=0;
  const double h=double(float(1.8*Dp));
  for(unsigned part=0;part<samples;part++){
    JPartDataBi4 file;file.LoadFilePart(dir.string(),part,0,1);NativeSet(file,Count);Metadata(file,cpu);
    Check(file.Get_Dp()==Dp&&file.Get_H()==h&&file.Get_Rhop0()==Rho0&&file.Get_MassFluid()/Rho0==V0&&file.Get_PeriMode()==PERI_XZ,"Native geometry/material differs from declared seed");
    const double time=file.Get_TimeStep(),error=Error(file);const unsigned step=part?unsigned(std::llround(part*cadence/dt))-1:0;
    Check(time==part*cadence&&file.Get_Step()==step,"Actual saved clock/zero-based step mismatch");
    Check(file.GetPart()->ExistsValue("SymplecticDtPre",JBinaryDataDef::DatDouble)&&file.GetPart()->GetvDouble("SymplecticDtPre")==dt,"Saved locked step mismatch");
    minError=(std::min)(minError,error);maxError=(std::max)(maxError,error);const Native a=Load(file,cpu);
    double energy=0.,pressure2=0.,materialMax=0.,jn=0.,nmin=DBL_MAX,nmax=0.,cflmax=0.;binary.write(reinterpret_cast<const char*>(&time),sizeof(time));
    for(unsigned id=0;id<Count;id++){
      const unsigned p=a.order[id];const auto x=a.x[p],s=a.sk[p],t=a.si[p];const auto v=a.v[p];const double j=a.j[p],n=1.-(1.-N0)/j,V=V0*j,rho=Rhow+(Rho0-Rhow)/j;
      Check(j>1.-N0&&std::fabs(j-1.)<=1e-4&&n>0&&n<1&&Finite(rho)&&rho>0&&Finite(V)&&V>0,"Weak saturated J/n/inertia domain failed");
      Check(LedgerClose(a.n[p],n)&&std::fabs((1.-a.n[p])*j-(1.-N0))<=5e-13,"Actual saved porosity/solid-volume ledger failed");
      maxLedger=(std::max)(maxLedger,std::fabs(a.n[p]-n)/n);
      if(cpu){
        Check(LedgerClose(a.volume[p],V)&&LedgerClose(a.inertia[p],rho)&&a.conductivity[p]==0.,"CPU native derived V/rho/k0 mismatch");
        maxLedger=(std::max)(maxLedger,(std::max)(std::fabs(a.volume[p]-V)/V,std::fabs(a.inertia[p]-rho)/rho));posdiv<<part<<','<<id<<','<<a.posdiv[p]<<'\n';
      }
      Check(a.plastic[p]==0&&a.rho[p]>=700&&a.rho[p]<=3000&&a.p0[p]==0&&Norm2(a.load[p])==0.,"Elastic/passive-density/p0/no-load guard failed");
      Check(a.excess[p]==float(a.p[p]-a.p0[p]),"Actual excess is not float p-p0");
      Check(a.legacykk[p].x==float(s.x)&&a.legacykk[p].y==float(s.y)&&a.legacykk[p].z==float(s.z)
        &&a.legacyij[p].x==float(t.x)&&a.legacyij[p].y==float(t.y)&&a.legacyij[p].z==float(t.z),"Legacy display stress does not round from actual double state");
      Check(x.y==0&&x.x>0&&x.x<Lx&&x.z>0&&x.z<Lz,"Native weak wave left fixed periodic geometry");
      if(!part){
        initial[id]=x;const double ix=x.x/Dp-.5,iz=x.z/Dp-.5;Check(ix==std::round(ix)&&iz==std::round(iz)&&ix>=0&&ix<32&&iz>=0&&iz<16,"Initial native lattice mismatch");
        const float vx=float(A*std::sin(2.*std::acos(-1.)*x.x/Lx));Check(v.x==vx&&v.y==0&&v.z==0&&a.p[p]==0&&Norm2(s)==0&&Norm2(t)==0&&j==1.&&a.n[p]==N0&&a.theta[p]==0.,"Initial native sine/p/stress/J/diagnostic differs");
        ids<<id<<','<<id<<','<<x.x<<','<<x.y<<','<<x.z<<'\n';
      }
      const tdouble3 u=TDouble3(x.x-initial[id].x,x.y-initial[id].y,x.z-initial[id].z);
      const double tr=s.x+s.y+s.z,mean=tr/3.,dev=(s.x-mean)*(s.x-mean)+(s.y-mean)*(s.y-mean)+(s.z-mean)*(s.z-mean)+2.*Norm2(t);
      energy+=V*(.5*rho*Norm2(v)+dev/(4.*Shear)+tr*tr/(18.*Bulk)+n*double(a.p[p])*double(a.p[p])/(2.*Kw));
      const double coupled=std::sqrt((Bulk+4.*Shear/3.+Kw/n)/rho)*dt/h;Check(Finite(coupled)&&coupled<=.01,"Original saved necessary coupled-CFL screen failed");
      // Native shear storage order is xy,yz,xz. Common schema deliberately has no PosDiv.
      const std::array<double,Columns> row={x.x,x.y,x.z,double(v.x),double(v.y),double(v.z),double(a.p[p]),double(a.p0[p]),j,a.theta[p],
        s.x,t.x,t.z,s.y,t.y,s.z,double(a.plastic[p]),double(a.type[p]),double(a.normal[p].x),double(a.normal[p].y),double(a.normal[p].z),
        double(a.load[p].x),double(a.load[p].y),double(a.load[p].z),double(a.rho[p]),u.x,u.y,u.z,double(a.excess[p]),a.n[p],cpu?a.volume[p]:V,cpu?a.inertia[p]:rho,0.};
      binary.write(reinterpret_cast<const char*>(row.data()),sizeof(double)*Columns);ledgerChecks++;pressure2+=double(a.p[p])*a.p[p];
      materialMax=(std::max)(materialMax,1000.*std::sqrt(Norm2(u)));jn=(std::max)(jn,std::fabs(j-1.));nmin=(std::min)(nmin,n);nmax=(std::max)(nmax,n);cflmax=(std::max)(cflmax,coupled);
    }
    if(!part){energy0=energy;Check(Finite(energy0)&&energy0>0.,"Initial energy is empty");}
    const double ratio=energy/energy0;Check(Finite(ratio)&&ratio<=1.1,"Original full-history energy bound failed");
    maxEnergy=(std::max)(maxEnergy,ratio);maxJ=(std::max)(maxJ,jn);maxCfl=(std::max)(maxCfl,cflmax);
    history<<part<<','<<time<<','<<step<<','<<dt<<','<<error<<','<<ratio<<','<<std::sqrt(pressure2/Count)<<','<<materialMax<<','<<jn<<','<<nmin<<','<<nmax<<','<<cflmax<<'\n';
  }
  Check(ledgerChecks==Count*samples&&maxJ>(smoke?0.:1e-8),"Declared native ledger coverage or natural J evolution empty");
  binary.flush();ids.flush();history.flush();if(cpu)posdiv.flush();Check(bool(binary)&&bool(ids)&&bool(history)&&(!cpu||bool(posdiv)),"Native export write failed");
  std::ofstream done(target/"completion.json");done<<std::setprecision(17)<<"{\"passed\":true,\"backend\":\""<<backend<<"\",\"smoke\":"<<(smoke?"true":"false")<<",\"native_count\":512,\"fixed_count\":0,\"samples\":"<<samples<<",\"common_columns\":33,\"dt_s\":"<<dt
    <<",\"cadence_s\":"<<cadence<<",\"actual_end_s\":"<<end<<",\"native_ledger_checks\":"<<ledgerChecks<<",\"original_arrays\":15,\"native_J_arrays\":"<<(cpu?6:3)<<",\"native_PosDiv_observed\":"<<(cpu?"true":"false")
    <<",\"GPU_V_rho_k_derived_not_native_arrays\":"<<(cpu?"false":"true")<<",\"public_dynamic_metadata\":"<<(cpu?"true":"false")<<",\"max_energy_ratio\":"<<maxEnergy<<",\"max_abs_J_minus_1\":"<<maxJ
    <<",\"max_saved_coupled_CFL\":"<<maxCfl<<",\"max_ledger_relative_error\":"<<maxLedger<<",\"min_signed_dterror_s\":"<<minError<<",\"max_signed_dterror_s\":"<<maxError
    <<",\"Pstar_Pa\":"<<Pstar()<<",\"Ustar_m\":"<<Ustar()<<",\"velocity_A_m_s\":"<<A<<",\"saved_clock_step_exact\":true,\"native_ID_aligned\":true,\"no_exclusions\":true,\"full_program_exit_verified_by_reader\":false,\"physical_acceptance\":false}\n";
  done.flush();Check(bool(done),"Native completion write failed");
}
class ActualGpu:public JSphGpuSingle{
public:
  void Enable(){PorosityObserver=PorosityFeedback=true;}
  void Finish(const fs::path& out,bool smoke){
    Check(PorosityObserver&&PorosityFeedback&&!HydroMechDynamicSeepage&&HydroMech&&Simulate2D&&!CaseNpb&&!CaseNfloat&&CaseNfluid==Count&&SoilCte.HydraulicConductivity==0,"Actual Run left private periodic k0 scope");
    Check(TimeStep==(smoke?2.*DtC:End)&&(smoke?Nstep==2:(Nstep==512||Nstep==1024))&&!PosxyPreg&&!PoszPreg&&!VelrhopPreg&&!SigmaPreg&&!PorePressPreg&&!PoroJPreg,"Actual Run did not complete declared window/release PRE");
    Check(smoke?(SymplecticDtPre==DtC&&Nstep==2):((SymplecticDtPre==DtC&&Nstep==512)||(SymplecticDtPre==DtH&&Nstep==1024)),"Actual final locked step mismatch");
    Check(double(SoilCte.Porosity)==N0&&double(RhopZero)==Rho0&&double(SoilCte.PoreWaterRho)==Rhow&&double(SoilCte.PoreWaterBulkModulus)==Kw&&double(SoilCte.ModulusK)==Bulk&&double(SoilCte.ModulusG)==Shear,"Actual loaded material differs from frozen recipe");
    const unsigned normal=ParticlesDataDown(Np,0,true,PeriActive!=0);Check(normal==Count,"Actual final download lost native particles");
    const std::vector<unsigned> id(Idp,Idp+normal);const auto order=Order(id);Fresh(out/"live_final.csv");Fresh(out/"actual_complete.json");
    std::ofstream csv(out/"live_final.csv");csv<<std::setprecision(17)<<"id,J,n,theta\n";
    for(unsigned native=0;native<Count;native++){const unsigned p=order[native];const double j=PoroJ[p],n=1.-(1.-N0)/j;
      Check(CODE_IsNormal(Code[p])&&CODE_IsFluid(Code[p])&&Finite(j)&&Finite(n)&&Finite(PoroTheta[p])&&j>1.-N0&&n>0&&n<1,"Invalid actual final native J state");csv<<native<<','<<j<<','<<n<<','<<PoroTheta[p]<<'\n';}
    csv.flush();Check(bool(csv),"Actual live final export failed");std::ofstream done(out/"actual_complete.json");done<<std::setprecision(17)
      <<"{\"passed\":true,\"smoke\":"<<(smoke?"true":"false")<<",\"actual_production_Run\":true,\"private_feedback\":true,\"public_GPU_dynamic_mode\":false,\"physical_fields_rewritten_by_fixture\":false,\"native_count\":512,\"actual_end_s\":"<<TimeStep
      <<",\"completed_steps\":"<<Nstep<<",\"dt_s\":"<<SymplecticDtPre<<",\"predictor_histories_released\":true,\"live_GPU_download\":true,\"physical_acceptance\":false}\n";done.flush();Check(bool(done),"Actual completion write failed");
  }
};
}
int main(int argc,char** argv){
  try{
    Check(argc>=2,"Use --solver[-smoke] normalGPUargs or --read[-smoke] GPU|CPU DATA_DIR DT NEW_REVIEW_DIR");const std::string mode=argv[1];
    if(mode=="--read"||mode=="--read-smoke"){Check(argc==6,"Use --read[-smoke] GPU|CPU DATA_DIR DT NEW_REVIEW_DIR");k0::Read(argv[2],argv[3],std::stod(argv[4]),argv[5],mode=="--read-smoke");return 0;}
    Check((mode=="--solver"||mode=="--solver-smoke")&&argc>=6,"Use --solver[-smoke] followed by ordinary GPU arguments");AppInfo.ConfigRunPaths(argv[0]);
    std::vector<char*> args{argv[0]};for(int i=2;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());
    Check(!cfg.Cpu&&!cfg.PrintInfo&&!fs::exists(cfg.DirOut),"Only actual GPU Run with fresh output admitted");
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    k0::ActualGpu fixture;fixture.Enable();fixture.Run(AppInfo.GetFullName(),&cfg,AppInfo.LogPtr());fixture.Finish(cfg.DirOut,mode=="--solver-smoke");return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Private GPU k0 actual stage rejected; retain all evidence\n";return 2;}
}
