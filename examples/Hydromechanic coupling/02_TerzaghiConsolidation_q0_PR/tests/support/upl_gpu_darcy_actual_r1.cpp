// Actual private complete constant-k GPU Run and an explicit k-aware CPU/GPU native reader.
// Include only the immutable typed utilities: the nested main macros in k0_actual_r2 are not reused.
#define main RetainedDarcyObserverNativeMain
#include "upl_gpu_observer_native_r1.cpp"
#undef main
#include "JXml.h"
#include <array>
#include <cfloat>
namespace darcy {
using TpData=JBinaryDataDef::TpData;
constexpr auto U=JBinaryDataDef::DatUint,F=JBinaryDataDef::DatFloat,D=JBinaryDataDef::DatDouble,
  F3=JBinaryDataDef::DatFloat3,D3=JBinaryDataDef::DatDouble3;
constexpr unsigned Count=512,Samples=257,Columns=33;
constexpr double DtC=1./16777216.,DtH=1./33554432.,Cadence=1./8388608.,End=1./32768.;
constexpr double Dp=1./256.,Lx=1./8.,Lz=1./16.,A=1./512.,N0=.25,Rho0=2048.,Rhow=1000.,Kw=67108864.,Bulk=89478488.,Shear=134217728.;
constexpr double V0=Dp*Dp;
enum class Model{K0,Constant};
static Model ParseModel(const std::string& s){Check(s=="k0"||s=="constant","Model must be k0 or constant");return s=="k0"?Model::K0:Model::Constant;}
static const char* Name(Model m){return m==Model::K0?"k0":"constant";}
static double K(Model m){return m==Model::K0?0.:double(float(1e-4));}
static double Cu0(){return std::sqrt((Bulk+4.*Shear/3.+Kw/N0)/Rho0);}
static bool Ok(double x){return std::isfinite(x);}static bool Ok(float x){return std::isfinite(x);}static bool Ok(unsigned){return true;}
static bool Ok(tfloat3 x){return Ok(x.x)&&Ok(x.y)&&Ok(x.z);}static bool Ok(tdouble3 x){return Ok(x.x)&&Ok(x.y)&&Ok(x.z);}
static double Norm2(tdouble3 x){return x.x*x.x+x.y*x.y+x.z*x.z;}static double Norm2(tfloat3 x){return double(x.x)*x.x+double(x.y)*x.y+double(x.z)*x.z;}
static bool Close(double x,double y){return Ok(x)&&Ok(y)&&(y==0?x==0:std::fabs(x-y)<=5e-13*std::fabs(y));}
template<class T>static std::vector<T> Array(JPartDataBi4& file,const char* key,TpData type){auto a=NativeArray<T>(file,key,Count,type);for(const auto& v:a)Check(Ok(v),key);return a;}
struct Native{
  std::vector<unsigned> id,order,type;std::vector<tdouble3> x,s,t;std::vector<tfloat3> v,sk,si,normal,load;
  std::vector<float> passive,plastic,p,p0,excess,posdiv;std::vector<double> j,n,theta,V,rho,k;
};
static Native Load(JPartDataBi4& file,bool cpu){
  Native a;a.id=Array<unsigned>(file,"Idp",U);a.order=Order(a.id);a.type=Array<unsigned>(file,"FSType",U);
  a.x=Array<tdouble3>(file,"Posd",D3);Check(!file.ArrayExists("Pos"),"Expected native double positions");
  a.s=Array<tdouble3>(file,"SigmaState_kk",D3);a.t=Array<tdouble3>(file,"SigmaState_ij",D3);
  a.v=Array<tfloat3>(file,"Vel",F3);a.sk=Array<tfloat3>(file,"Sigma_kk",F3);a.si=Array<tfloat3>(file,"Sigma_ij",F3);
  a.normal=Array<tfloat3>(file,"FSNormal",F3);a.load=Array<tfloat3>(file,"HydroMechLoadAce",F3);
  a.passive=Array<float>(file,"Rhop",F);a.plastic=Array<float>(file,"Kplastic",F);a.p=Array<float>(file,"PorePress",F);
  a.p0=Array<float>(file,"PorePress0",F);a.excess=Array<float>(file,"ExcessPorePress",F);
  a.j=Array<double>(file,"PoroVolumeRatio",D);a.n=Array<double>(file,"PoroPorosity",D);a.theta=Array<double>(file,"PoroThetaLastStage",D);
  for(const char* key:{"PoroCurrentVolume","PoroMixtureDensity","PoroHydraulicConductivity","PosDiv"})Check(file.ArrayExists(key)==cpu,"Backend native-derived field presence differs");
  if(cpu){a.V=Array<double>(file,"PoroCurrentVolume",D);a.rho=Array<double>(file,"PoroMixtureDensity",D);a.k=Array<double>(file,"PoroHydraulicConductivity",D);a.posdiv=Array<float>(file,"PosDiv",F);}return a;
}
static void Metadata(JPartDataBi4& file,bool cpu){
  const auto* p=file.GetPart();const char* key[]={"HydroMechDynamicSeepage","DynamicSeepageSchema","HydroMechConductivityModel","HydroMechConductivityCk"};
  for(const char* k:key)Check(p->ExistsValue(k)==cpu,"Private GPU/public CPU metadata presence differs");
  if(cpu){Check(p->ExistsValue(key[0],JBinaryDataDef::DatBool)&&p->GetvBool(key[0]),"CPU native public master not true");
    Check(p->ExistsValue(key[1],U)&&p->GetvUint(key[1])==1&&p->ExistsValue(key[2],U)&&p->GetvUint(key[2])==0,"CPU native schema/model mismatch");
    Check(p->ExistsValue(key[3],D)&&p->GetvDouble(key[3])==0.,"CPU constant-law Ck is not typed double0");}
}
static double Runtime(const fs::path& path,Model model,bool cpu,bool smoke,double dt){
  Check(fs::is_regular_file(path),"Bound runtime XML missing");JXml xml;xml.LoadFile(path.string());
  const auto* h=xml.GetNodeError("case.execution.special.hydromechanics");const auto* s=xml.GetNodeError("case.execution.special.soils");const auto* c=xml.GetNodeError("case.execution.constants");
  auto hv=[&](const char* key,double value,bool optional=false){Check(xml.ReadElementDouble(h,key,"value",optional,0.)==value,"Runtime hydromechanics differs from declared model/material");};
  hv("HydroMech",1);hv("PoreWaterRho",Rhow);hv("PoreWaterBulkModulus",Kw);hv("Porosity",N0);hv("HydraulicConductivity",model==Model::K0?0.:1e-4);
  hv("PoreShepardRegularization",0);hv("PoreCompressionGradCorr",1);hv("PoreCompressionSourceMode",0);hv("HydroMechInitMode",0);hv("HydroMechTopLoadMode",0);hv("HydroMechDrainage",0);
  Check(xml.ReadElementBool(h,"HydroMechDynamicSeepage","value",true,false)==cpu,"Runtime public master must be CPU true/GPU false");
  Check(xml.ReadElementUnsigned(h,"HydroMechConductivityModel","value",true,0)==0&&xml.ReadElementDouble(h,"HydroMechConductivityCk","value",true,0.)==0.,"Only constant conductivity model0/Ck0 admitted");
  const double safety=double(float(xml.ReadElementDouble(h,"PoreDtSafety","value")));Check(safety==double(float(.1)),"Original pore safety must remain .1");
  Check(xml.ReadElementDouble(s,"ModulusE","value")==268435456.&&xml.ReadElementDouble(s,"PRvs","value")==0.&&xml.ReadElementDouble(s,"phi","value")==0.&&xml.ReadElementDouble(s,"coh","value")==1e12&&xml.ReadElementDouble(s,"dlt","value")==0.,"Runtime elastic soil material differs");
  const auto g=xml.GetAttributeDouble3(xml.GetFirstElement(c,"gravity"));Check(Norm2(g)==0.,"Only zero gravity admitted");
  Check(xml.ReadElementDouble(c,"rhop0","value")==Rho0&&xml.ReadElementDouble(c,"dp","value")==Dp&&double(float(xml.ReadElementDouble(c,"h","value")))==double(float(1.8*Dp))&&xml.ReadElementDouble(c,"massfluid","value")==Rho0*V0,"Runtime native geometry/inertia constants differ");
  std::map<std::string,double> p;const auto* parameters=xml.GetNodeError("case.execution.parameters");
  for(auto* e=parameters->FirstChildElement("parameter");e;e=e->NextSiblingElement("parameter")){const auto key=xml.GetAttributeStr(e,"key");Check(p.emplace(key,xml.GetAttributeDouble(e,"value")).second,"Duplicate runtime parameter");}
  auto pv=[&](const char* key,double value){Check(p.count(key)&&p.at(key)==value,"Runtime option or clock differs");};
  pv("SavePosDouble",1);pv("StepAlgorithm",2);pv("Kernel",2);pv("ViscoTreatment",1);pv("Visco",0);pv("ArtificialStress",0);pv("SoilStressRateGradCorr",1);pv("SoilHourglassXi",0);pv("SoilBoundaryDerivativeSPR",0);pv("SoilDamping",0);pv("DensityDT",0);pv("Shifting",0);pv("PartsOutMax",0);pv("RhopOutMin",700);pv("RhopOutMax",3000);pv("XZPeriodic",1);
  Check(dt==DtC||(!smoke&&dt==DtH),"Only declared coarse/half clock admitted");pv("DtFixed",dt);pv("DtIni",dt);pv("TimeMax",smoke?2.*DtC:End);pv("TimeOut",smoke?DtC:Cadence);return dt;
}
static double RuntimeDt(const fs::path& path){JXml xml;xml.LoadFile(path.string());const auto* p=xml.GetNodeError("case.execution.parameters");unsigned n=0;double value=0.;for(auto* e=p->FirstChildElement("parameter");e;e=e->NextSiblingElement("parameter"))if(xml.GetAttributeStr(e,"key")=="DtFixed"){value=xml.GetAttributeDouble(e,"value");n++;}Check(n==1,"One runtime DtFixed required");return value;}
static void Sequence(const fs::path& dir,unsigned samples){unsigned found=0;Check(fs::is_directory(dir),"Native data directory missing");for(const auto& e:fs::directory_iterator(dir))if(e.is_regular_file()&&e.path().extension()==".bi4"&&e.path().filename().string().rfind("Part_",0)==0)found++;Check(found==samples,"Extra/missing PART or piece files");for(unsigned p=0;p<samples;p++)Check(fs::is_regular_file(dir/JPartDataBi4::GetFileNamePart(p)),"Missing declared PART");}
static void Read(Model model,const char* backend,const fs::path& dir,double dt,const fs::path& runtime,const fs::path& target,bool smoke){
  const bool cpu=std::string(backend)=="CPU";Check(cpu||std::string(backend)=="GPU","Backend must be CPU or GPU");Check(!smoke||(!cpu&&dt==DtC),"Smoke is GPU coarse only");Runtime(runtime,model,cpu,smoke,dt);
  const unsigned samples=smoke?3:Samples;const double cadence=smoke?DtC:Cadence,end=smoke?2.*DtC:End,khyd=K(model),h=double(float(1.8*Dp));
  Fresh(target);Sequence(dir,samples);fs::create_directory(target);std::ofstream binary(target/"physical.bin",std::ios::binary),ids(target/"native_ids.csv"),history(target/"history.csv"),last(target/"last_poro.csv"),posdiv;
  if(cpu)posdiv.open(target/"cpu_posdiv.csv");const unsigned header[]={Count,Columns,samples};binary.write(reinterpret_cast<const char*>(header),sizeof(header));
  ids<<std::setprecision(17)<<"row,id,x0,y0,z0\n";history<<std::setprecision(17)<<"part,time_s,saved_step,dt_s,dterror_s,energy_ratio,pressure_RMS_Pa,max_material_displacement_mm,max_abs_J_minus_1,min_n,max_n,max_coupled_CFL,max_Ddt_h2,min_continuous_margin_kg_m3\n";
  last<<std::setprecision(17)<<"id,J,n,theta\n";if(cpu)posdiv<<std::setprecision(17)<<"part,id,actual_native_PosDiv\n";
  std::vector<tdouble3> initial(Count);double energy0=0.,maxEnergy=0.,maxJ=0.,maxCfl=0.,maxDiff=0.,maxLedger=0.,minError=DBL_MAX,maxError=-DBL_MAX,minMargin=DBL_MAX;unsigned ledgerChecks=0;
  for(unsigned part=0;part<samples;part++){
    JPartDataBi4 file;file.LoadFilePart(dir.string(),part,0,1);NativeSet(file,Count);Metadata(file,cpu);
    Check(file.Get_Dp()==Dp&&file.Get_H()==h&&file.Get_Rhop0()==Rho0&&file.Get_MassFluid()/Rho0==V0&&file.Get_PeriMode()==PERI_XZ,"Native geometry/material differs");
    const double time=file.Get_TimeStep(),error=Error(file);const unsigned step=part?unsigned(std::llround(part*cadence/dt))-1:0;
    Check(time==part*cadence&&file.Get_Step()==step&&file.GetPart()->ExistsValue("SymplecticDtPre",D)&&file.GetPart()->GetvDouble("SymplecticDtPre")==dt,"Actual saved clock/zero-based step/locked dt differs");
    minError=(std::min)(minError,error);maxError=(std::max)(maxError,error);const Native a=Load(file,cpu);double energy=0.,pressure2=0.,umax=0.,jn=0.,nmin=DBL_MAX,nmax=0.,cflmax=0.,diffmax=0.,marginmin=DBL_MAX;binary.write(reinterpret_cast<const char*>(&time),sizeof(time));
    for(unsigned id=0;id<Count;id++){
      const unsigned p=a.order[id];const auto x=a.x[p],s=a.s[p],t=a.t[p];const auto v=a.v[p];const double j=a.j[p],n=1.-(1.-N0)/j,V=V0*j,rho=Rhow+(Rho0-Rhow)/j;
      Check(j>1.-N0&&std::fabs(j-1.)<=1e-4&&n>0&&n<1&&Ok(rho)&&rho>0&&Ok(V)&&V>0,"Original weak saturated ledger domain failed");
      Check(Close(a.n[p],n)&&std::fabs((1.-a.n[p])*j-(1.-N0))<=5e-13,"Actual saved n/solid-volume ledger failed");maxLedger=(std::max)(maxLedger,std::fabs(a.n[p]-n)/n);
      if(cpu){Check(Close(a.V[p],V)&&Close(a.rho[p],rho)&&a.k[p]==khyd,"CPU native V/rho/constant-k ledger mismatch");maxLedger=(std::max)(maxLedger,(std::max)(std::fabs(a.V[p]-V)/V,std::fabs(a.rho[p]-rho)/rho));posdiv<<part<<','<<id<<','<<a.posdiv[p]<<'\n';}
      Check(a.plastic[p]==0&&a.passive[p]>=700&&a.passive[p]<=3000&&a.p0[p]==0&&Norm2(a.load[p])==0.,"Elastic/passive-density/p0/no-load guard failed");Check(a.excess[p]==float(a.p[p]-a.p0[p]),"Native excess must be actual float p-p0");
      Check(a.sk[p].x==float(s.x)&&a.sk[p].y==float(s.y)&&a.sk[p].z==float(s.z)&&a.si[p].x==float(t.x)&&a.si[p].y==float(t.y)&&a.si[p].z==float(t.z),"Legacy display stress is not rounded stored double stress");
      Check(x.y==0&&x.x>0&&x.x<Lx&&x.z>0&&x.z<Lz,"Weak material points left primary periodic domain");
      if(!part){initial[id]=x;const double ix=x.x/Dp-.5,iz=x.z/Dp-.5;Check(ix==std::round(ix)&&iz==std::round(iz)&&ix>=0&&ix<32&&iz>=0&&iz<16,"Initial lattice differs");const float vx=float(A*std::sin(2.*std::acos(-1.)*x.x/Lx));Check(v.x==vx&&v.y==0&&v.z==0&&a.p[p]==0&&Norm2(s)==0&&Norm2(t)==0&&j==1.&&a.n[p]==N0&&a.theta[p]==0.,"Initial native sine/p/stress/J differs");ids<<id<<','<<id<<','<<x.x<<','<<x.y<<','<<x.z<<'\n';}
      const tdouble3 u=TDouble3(x.x-initial[id].x,x.y-initial[id].y,x.z-initial[id].z);const double tr=s.x+s.y+s.z,mean=tr/3.,dev=(s.x-mean)*(s.x-mean)+(s.y-mean)*(s.y-mean)+(s.z-mean)*(s.z-mean)+2.*Norm2(t);
      energy+=V*(.5*rho*Norm2(v)+dev/(4.*Shear)+tr*tr/(18.*Bulk)+n*double(a.p[p])*double(a.p[p])/(2.*Kw));
      const double B=Kw/n,coupled=std::sqrt((Bulk+4.*Shear/3.+B)/rho)*dt/h,diffusion=B*khyd/(Rhow*9.80665)*dt/(h*h);
      Check(Ok(coupled)&&coupled<=.01&&Ok(diffusion)&&diffusion<=.01,"Original saved necessary acoustic/diffusion screens failed");
      if(khyd>0){const double margin=rho*B/(Bulk+4.*Shear/3.+B)-Rhow;Check(Ok(margin)&&margin>64.*DBL_EPSILON*(std::max)(rho,Rhow),"Saved positive-k continuous domain failed; dt cannot repair it");marginmin=(std::min)(marginmin,margin);}
      // Native SigmaState_ij=(xy,yz,xz); common shear columns are (xy,xz,yz). No fake PosDiv column.
      const std::array<double,Columns> row={x.x,x.y,x.z,double(v.x),double(v.y),double(v.z),double(a.p[p]),double(a.p0[p]),j,a.theta[p],s.x,t.x,t.z,s.y,t.y,s.z,double(a.plastic[p]),double(a.type[p]),double(a.normal[p].x),double(a.normal[p].y),double(a.normal[p].z),double(a.load[p].x),double(a.load[p].y),double(a.load[p].z),double(a.passive[p]),u.x,u.y,u.z,double(a.excess[p]),a.n[p],cpu?a.V[p]:V,cpu?a.rho[p]:rho,cpu?a.k[p]:khyd};
      binary.write(reinterpret_cast<const char*>(row.data()),sizeof(double)*Columns);ledgerChecks++;pressure2+=double(a.p[p])*a.p[p];umax=(std::max)(umax,1000.*std::sqrt(Norm2(u)));jn=(std::max)(jn,std::fabs(j-1.));nmin=(std::min)(nmin,n);nmax=(std::max)(nmax,n);cflmax=(std::max)(cflmax,coupled);diffmax=(std::max)(diffmax,diffusion);
      if(part+1==samples)last<<id<<','<<j<<','<<a.n[p]<<','<<a.theta[p]<<'\n';
    }
    if(!part){energy0=energy;Check(Ok(energy0)&&energy0>0.,"Initial energy is empty");}const double ratio=energy/energy0;Check(Ok(ratio)&&ratio<=1.1,"Original all-history energy guard failed");maxEnergy=(std::max)(maxEnergy,ratio);maxJ=(std::max)(maxJ,jn);maxCfl=(std::max)(maxCfl,cflmax);maxDiff=(std::max)(maxDiff,diffmax);minMargin=(std::min)(minMargin,marginmin);
    history<<part<<','<<time<<','<<step<<','<<dt<<','<<error<<','<<ratio<<','<<std::sqrt(pressure2/Count)<<','<<umax<<','<<jn<<','<<nmin<<','<<nmax<<','<<cflmax<<','<<diffmax<<','<<(khyd>0?marginmin:0.)<<'\n';
  }
  Check(ledgerChecks==Count*samples&&maxJ>(smoke?0.:1e-8),"Declared full ledger/nonempty natural J evolution failed");binary.flush();ids.flush();history.flush();last.flush();if(cpu)posdiv.flush();Check(bool(binary)&&bool(ids)&&bool(history)&&bool(last)&&(!cpu||bool(posdiv)),"Native export write failed");
  std::ofstream done(target/"completion.json");done<<std::setprecision(17)<<"{\"passed\":true,\"model\":\""<<Name(model)<<"\",\"backend\":\""<<backend<<"\",\"smoke\":"<<(smoke?"true":"false")<<",\"native_count\":512,\"fixed_count\":0,\"samples\":"<<samples<<",\"common_columns\":33,\"dt_s\":"<<dt<<",\"cadence_s\":"<<cadence<<",\"actual_end_s\":"<<end<<",\"conductivity_m_s\":"<<khyd
    <<",\"native_ledger_checks\":"<<ledgerChecks<<",\"original_arrays\":15,\"native_J_arrays\":"<<(cpu?6:3)<<",\"native_PosDiv_observed\":"<<(cpu?"true":"false")<<",\"GPU_V_rho_k_derived_not_native_arrays\":"<<(cpu?"false":"true")<<",\"public_dynamic_metadata\":"<<(cpu?"true":"false")<<",\"runtime_XML_exact_model_material_and_clock_checked\":true,\"max_energy_ratio\":"<<maxEnergy<<",\"max_abs_J_minus_1\":"<<maxJ
    <<",\"max_saved_coupled_CFL\":"<<maxCfl<<",\"max_saved_Ddt_h2\":"<<maxDiff<<",\"min_positive_k_continuous_margin_kg_m3\":"<<(khyd>0?minMargin:0.)<<",\"max_ledger_relative_error\":"<<maxLedger<<",\"min_signed_dterror_s\":"<<minError<<",\"max_signed_dterror_s\":"<<maxError<<",\"Pstar_Pa\":"<<(Kw/N0)*A/Cu0()<<",\"Ustar_m\":"<<A/(Cu0()*2.*std::acos(-1.)/Lx)<<",\"velocity_A_m_s\":"<<A
    <<",\"saved_clock_step_exact\":true,\"native_ID_aligned\":true,\"no_exclusions\":true,\"full_program_exit_verified_by_reader\":false,\"full_force_stage_scales_independently_observed\":false,\"physical_acceptance\":false}\n";done.flush();Check(bool(done),"Native completion write failed");
}
class ActualGpu:public JSphGpuSingle{
public:
  void Enable(){PorosityObserver=PorosityFeedback=DynamicPorePressure=true;}
  void Finish(const fs::path& out,Model model,bool smoke){
    Check(PorosityObserver&&PorosityFeedback&&DynamicPorePressure&&!HydroMechDynamicSeepage&&HydroMech&&Simulate2D&&!CaseNpb&&!CaseNfloat&&CaseNfluid==Count&&double(SoilCte.HydraulicConductivity)==K(model)&&HydroMechConductivityModel==0,"Actual Run left private complete constant-k scope");
    Check(TimeStep==(smoke?2.*DtC:End)&&(smoke?Nstep==2:(Nstep==512||Nstep==1024))&&!PosxyPreg&&!PoszPreg&&!VelrhopPreg&&!SigmaPreg&&!PorePressPreg&&!PoroJPreg,"Actual Run failed declared end/steps/PRE release");
    Check(smoke?(SymplecticDtPre==DtC&&Nstep==2):((SymplecticDtPre==DtC&&Nstep==512)||(SymplecticDtPre==DtH&&Nstep==1024)),"Actual locked step differs");
    Check(double(SoilCte.Porosity)==N0&&double(RhopZero)==Rho0&&double(SoilCte.PoreWaterRho)==Rhow&&double(SoilCte.PoreWaterBulkModulus)==Kw&&double(SoilCte.ModulusK)==Bulk&&double(SoilCte.ModulusG)==Shear,"Actual loaded material differs");
    const unsigned normal=ParticlesDataDown(Np,0,true,PeriActive!=0);Check(normal==Count,"Actual final native download count differs");const std::vector<unsigned> ids(Idp,Idp+normal);const auto order=Order(ids);Fresh(out/"live_final.csv");Fresh(out/"actual_complete.json");
    std::ofstream csv(out/"live_final.csv");csv<<std::setprecision(17)<<"id,J,n,theta\n";for(unsigned id=0;id<Count;id++){const unsigned p=order[id];const double j=PoroJ[p],n=1.-(1.-N0)/j;Check(CODE_IsNormal(Code[p])&&CODE_IsFluid(Code[p])&&Ok(j)&&Ok(n)&&Ok(PoroTheta[p])&&j>1.-N0&&n>0&&n<1,"Invalid actual live final J/n/theta");csv<<id<<','<<j<<','<<n<<','<<PoroTheta[p]<<'\n';}csv.flush();Check(bool(csv),"Live final export failed");
    std::ofstream done(out/"actual_complete.json");done<<std::setprecision(17)<<"{\"passed\":true,\"model\":\""<<Name(model)<<"\",\"smoke\":"<<(smoke?"true":"false")<<",\"actual_production_Run\":true,\"private_feedback\":true,\"private_complete_dynamic_rate\":true,\"conductivity_m_s\":"<<K(model)<<",\"public_GPU_dynamic_mode\":false,\"physical_fields_rewritten_by_fixture\":false,\"native_count\":512,\"actual_end_s\":"<<TimeStep<<",\"completed_steps\":"<<Nstep<<",\"dt_s\":"<<SymplecticDtPre<<",\"predictor_histories_released\":true,\"live_GPU_download\":true,\"physical_acceptance\":false}\n";done.flush();Check(bool(done),"Actual completion write failed");
  }
};
}
int main(int argc,char** argv){
  try{
    Check(argc>=2,"Use --solver-k0|--solver-constant [--smoke] GPUargs or --read MODEL BACKEND DATA DT RUNTIME_XML NEWDIR [--smoke]");const std::string mode=argv[1];
    if(mode=="--read"){Check(argc==8||(argc==9&&std::string(argv[8])=="--smoke"),"Reader requires explicit model/backend/native-data/clock/runtime-XML/output");darcy::Read(darcy::ParseModel(argv[2]),argv[3],argv[4],std::stod(argv[5]),argv[6],argv[7],argc==9);return 0;}
    Check(mode=="--solver-k0"||mode=="--solver-constant","Exactly one explicit solver model required");const auto model=mode=="--solver-k0"?darcy::Model::K0:darcy::Model::Constant;const bool smoke=argc>2&&std::string(argv[2])=="--smoke";const int first=smoke?3:2;Check(argc>=first+3,"Ordinary explicit GPU arguments required");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=first;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());
    Check(!cfg.Cpu&&!cfg.PrintInfo&&!fs::exists(cfg.DirOut)&&cfg.PartBegin==0&&cfg.NstepsBreak==0&&cfg.TimeMax<0&&cfg.TimePart<0&&!cfg.SvAllSteps,"Only fresh XML-clock actual GPU Run without CLI time/restart overrides admitted");
    const fs::path runtime=cfg.CaseName+".xml";darcy::Runtime(runtime,model,false,smoke,darcy::RuntimeDt(runtime));
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");darcy::ActualGpu fixture;fixture.Enable();fixture.Run(AppInfo.GetFullName(),&cfg,AppInfo.LogPtr());fixture.Finish(cfg.DirOut,model,smoke);return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Private complete GPU Darcy actual fixture rejected; preserve evidence\n";return 2;}
}
