// Offline C08 shared-PRE source/receiver profile. No native metadata or array is rewritten.
#define main RetainedNeutralPublicReaderMain
#include "../../../02_TerzaghiConsolidation_q0_PR/tests/support/upl_cpu_public_native_r1.cpp"
#undef main
#include "JGravityPreloadState.h"
namespace c08releasegravity {
constexpr unsigned Soil=5000,Fixed=2060,Total=7060;
struct Window{unsigned steps;double end,output;};
static Window Scope(const std::string& name){Need(name=="on","Only the Ck2 on800 window is admitted");return Window{800,.002,.0001};}
constexpr double Dt=.0000025,Dp=.04,Rho=2072.5,Water=1000.,Surface=2.,CkCase=2.;
static const double Por=double(float(.35)),Mass=double(float(3.316)),K0Case=double(float(.0002)),H=double(float(.048));
static unsigned currentPart=~0u,currentId=~0u;static double currentJ=0,currentRhop=0,currentP=0;
static bool Bits(double a,double b){return !std::memcmp(&a,&b,8);}
static bool Bits(float a,float b){return !std::memcmp(&a,&b,4);}
static void MetadataCk2(JPartDataBi4& file){
  const auto* part=file.GetPart();const char* keys[]={"HydroMechDynamicSeepage","DynamicSeepageSchema","HydroMechConductivityModel","HydroMechConductivityCk"};
  for(const char* name:keys)Need(part->ExistsValue(name),"Missing native Ck2 model metadata: "+std::string(name));
  Need(part->ExistsValue(keys[0],DatBool)&&part->GetvBool(keys[0]),"Native total switch is not bool true");
  Need(part->ExistsValue(keys[1],DatUint)&&part->GetvUint(keys[1])==1,"Native schema is not uint1");
  Need(part->ExistsValue(keys[2],DatUint)&&part->GetvUint(keys[2])==1,"Native conductivity model is not uint1");
  Need(part->ExistsValue(keys[3],DatDouble)&&Bits(part->GetvDouble(keys[3]),CkCase),"Native conductivity Ck is not exact double2");
}
static std::vector<std::string> Tokens(std::string line,char sep){
  if(!line.empty()&&line.back()=='\r')line.pop_back();std::vector<std::string> v;std::size_t b=0;
  for(;;){const auto p=line.find(sep,b);v.push_back(line.substr(b,p==std::string::npos?p:p-b));if(p==std::string::npos)break;b=p+1;}return v;
}
static std::map<std::string,std::string> RunCsv(const fs::path& p,const Window& w){
  std::ifstream f(p);std::string h,d,x;Need(bool(std::getline(f,h))&&bool(std::getline(f,d))&&!std::getline(f,x),"Actual completed two-line Run.csv required");
  const char sep=h.find(';')==std::string::npos?',':';';const auto a=Tokens(h,sep),b=Tokens(d,sep);Need(a.size()==b.size(),"Run.csv width differs");std::map<std::string,std::string> r;
  for(unsigned n=0;n<a.size();n++)Need(r.emplace(a[n],b[n]).second,"Repeated Run.csv key");
  const unsigned steps=unsigned(std::stoul(r.at("Steps"))),samples=unsigned(std::stoul(r.at("PartFiles")));
  Need(steps==w.steps&&samples>=2&&r.at("Np")=="7060"&&r.at("Nfixed")=="2060"&&r.at("Nbound")=="2060"&&r.at("PartsOut")=="0"&&r.at("PartsOutRhop")=="0"&&r.at("PartsOutVel")=="0","Actual owner-capped release/control steps/original registry/no-fluid-exclusion summary differs");return r;
}
static std::vector<tdouble3> InitialCoordinates(const fs::path& p){
  std::ifstream f(p);std::string line;Need(bool(std::getline(f,line)),"Closed initial coordinate CSV missing");
  Need(Tokens(line,',')==std::vector<std::string>{"native_id","sorted_slot","is_fluid","x","y","z","original_mode","in_original_NpbOk"},"Closed coordinate header differs");
  std::vector<tdouble3> x(Total);std::vector<bool> seen(Total,false);unsigned count=0;
  while(std::getline(f,line)){
    const auto v=Tokens(line,',');Need(v.size()==8,"Initial coordinate CSV width differs");const unsigned id=unsigned(std::stoul(v[0]));
    Need(id<Total&&!seen[id]&&v[2]==(id<Fixed?"0":"1"),"Initial coordinate ID/classification differs");
    x[id]=TDouble3(std::stod(v[3]),std::stod(v[4]),std::stod(v[5]));Need(Finite(x[id])&&x[id].y==0,"Nonfinite/off-plane initial coordinate");seen[id]=true;count++;
  }Need(f.eof()&&count==Total,"Incomplete initial coordinate IDs");return x;
}
struct Summary{
  unsigned count=0;double excess=0,excess2=0,excesslo=DBL_MAX,excesshi=-DBL_MAX,p=0,p2=0,plo=DBL_MAX,phi=-DBL_MAX,u2=0,umax=0,v2=0,theta=0,theta2=0,jlo=DBL_MAX,jhi=-DBL_MAX,nlo=DBL_MAX,nhi=-DBL_MAX,mass=0,kinetic=0,s2=0;
  tdouble3 du=TDouble3(0),velocity=TDouble3(0);std::array<double,6> sigma{};
  void add(const Native& a,unsigned q,tdouble3 x0){
    const auto u=a.pos[q]-x0;const auto v=ToTDouble3(a.vel[q]);const auto s=a.sk[q],t=a.si[q];const double mi=a.rho[q]*a.volume[q],vv=Norm2(v),uu=Norm2(u);
    count++;p+=a.p[q];p2+=double(a.p[q])*a.p[q];plo=(std::min)(plo,double(a.p[q]));phi=(std::max)(phi,double(a.p[q]));
    excess+=a.excess[q];excess2+=double(a.excess[q])*a.excess[q];excesslo=(std::min)(excesslo,double(a.excess[q]));excesshi=(std::max)(excesshi,double(a.excess[q]));
    u2+=uu;umax=(std::max)(umax,std::sqrt(uu));du=du+u;velocity=velocity+v;v2+=vv;theta+=a.theta[q];theta2+=a.theta[q]*a.theta[q];
    jlo=(std::min)(jlo,a.j[q]);jhi=(std::max)(jhi,a.j[q]);nlo=(std::min)(nlo,a.n[q]);nhi=(std::max)(nhi,a.n[q]);mass+=mi;kinetic+=.5*mi*vv;s2+=Norm2(s)+2*Norm2(t);
    const double ss[]={s.x,s.y,s.z,t.x,t.y,t.z};for(unsigned k=0;k<6;k++)sigma[k]+=ss[k];
  }
  void write(std::ofstream& out,unsigned part,double time,const char* band)const{
    Need(count>0,"Empty initial-material band");const double n=count;
    const double values[]={p/n,std::sqrt(p2/n),plo,phi,sigma[0]/n,sigma[1]/n,sigma[2]/n,sigma[3]/n,sigma[4]/n,sigma[5]/n,std::sqrt(s2/n),du.x/n,du.y/n,du.z/n,1000*std::sqrt(u2/n),1000*umax,velocity.x/n,velocity.y/n,velocity.z/n,std::sqrt(v2/n),theta/n,std::sqrt(theta2/n),jlo,jhi,nlo,nhi,mass,kinetic,excess/n,std::sqrt(excess2/n),excesslo,excesshi};
    out<<part<<','<<time<<','<<band<<','<<count;for(double x:values){Need(std::isfinite(x),"Nonfinite descriptive history");out<<','<<x;}out<<'\n';
  }
};
static void Typed22(std::ofstream& out,const Native& a){
  Original15(out,a);for(const auto* v:{&a.j,&a.n,&a.theta,&a.volume,&a.rho,&a.k})WriteTyped(out,*v,a.slot);WriteTyped(out,a.posdiv,a.slot);
}

constexpr unsigned EventStep=380,RetireBegin=1800,RetireCount=260;
constexpr double EventTime=.00095;
static bool Retired(unsigned id){return id>=RetireBegin&&id<RetireBegin+RetireCount;}
static unsigned Phase(JPartDataBi4& f,bool enabled,bool preSeen,double preTime){
  const auto* p=f.GetPart();const char* keys[]={"GravityPreloadPhase","GravityPreloadRequestedTime","GravityPreloadEventCompletedStep","GravityPreloadReleaseMkBound","GravityPreloadTargetIdBegin","GravityPreloadTargetIdCount","GravityPreloadActualTime","GravityPreloadActualCompletedStep","SoilDampingActive","PoreShepardActive"};
  if(!enabled){for(const char* key:keys)Need(!p->ExistsValue(key),"Absent-object control gained phase metadata");return 0;}
  Need(p->ExistsValue(keys[0],DatUint)&&p->GetvUint(keys[0])<=1,"Typed actual release phase missing/invalid");const unsigned phase=p->GetvUint(keys[0]);
  Need(p->ExistsValue(keys[1],DatDouble)&&Bits(p->GetvDouble(keys[1]),EventTime)&&p->ExistsValue(keys[2],DatUint)&&p->GetvUint(keys[2])==EventStep,"Typed requested event time/completed count differs");
  Need(p->ExistsValue(keys[3],DatUint)&&p->GetvUint(keys[3])==2&&p->ExistsValue(keys[4],DatUint)&&p->GetvUint(keys[4])==RetireBegin&&p->ExistsValue(keys[5],DatUint)&&p->GetvUint(keys[5])==RetireCount,"Typed target MK/original ID interval differs");
  Need(p->ExistsValue(keys[8],DatBool)&&p->GetvBool(keys[8])==(phase==0)&&p->ExistsValue(keys[9],DatBool)&&p->GetvBool(keys[9])==(phase==0),"Actual phase damping/Shepard flags differ");
  if(phase)Need(preSeen&&p->ExistsValue(keys[6],DatDouble)&&Bits(p->GetvDouble(keys[6]),preTime)&&p->ExistsValue(keys[7],DatUint)&&p->GetvUint(keys[7])==EventStep,"Actual release time/count differs from genuine pre-event save");
  else Need(!p->ExistsValue(keys[6])&&!p->ExistsValue(keys[7]),"Pre-event record invented actual release metadata");return phase;
}
struct Sample{Native a;std::vector<unsigned> byid;};
// Reuse native typed readers, with original ID domain independent of current array length.
static Sample LoadActual(JPartDataBi4& f,unsigned phase){
  Sample s;Native& a=s.a;const unsigned n=Total-phase*RetireCount;
  a.ids=NativeArray<unsigned>(f,"Idp",n,DatUint);a.pos=NativeArray<tdouble3>(f,"Posd",n,DatDouble3);Need(!f.ArrayExists("Pos"),"Single position is outside this profile");
  a.vel=NativeArray<tfloat3>(f,"Vel",n,DatFloat3);a.rhop=NativeArray<float>(f,"Rhop",n,DatFloat);a.legacykk=NativeArray<tfloat3>(f,"Sigma_kk",n,DatFloat3);a.legacyij=NativeArray<tfloat3>(f,"Sigma_ij",n,DatFloat3);
  a.sk=NativeArray<tdouble3>(f,"SigmaState_kk",n,DatDouble3);a.si=NativeArray<tdouble3>(f,"SigmaState_ij",n,DatDouble3);a.plastic=NativeArray<float>(f,"Kplastic",n,DatFloat);a.fstype=NativeArray<unsigned>(f,"FSType",n,DatUint);
  a.normal=NativeArray<tfloat3>(f,"FSNormal",n,DatFloat3);a.load=NativeArray<tfloat3>(f,"HydroMechLoadAce",n,DatFloat3);a.p=NativeArray<float>(f,"PorePress",n,DatFloat);a.p0=NativeArray<float>(f,"PorePress0",n,DatFloat);a.excess=NativeArray<float>(f,"ExcessPorePress",n,DatFloat);
  a.j=NativeArray<double>(f,"PoroVolumeRatio",n,DatDouble);a.n=NativeArray<double>(f,"PoroPorosity",n,DatDouble);a.theta=NativeArray<double>(f,"PoroThetaLastStage",n,DatDouble);a.volume=NativeArray<double>(f,"PoroCurrentVolume",n,DatDouble);a.rho=NativeArray<double>(f,"PoroMixtureDensity",n,DatDouble);a.k=NativeArray<double>(f,"PoroHydraulicConductivity",n,DatDouble);a.posdiv=NativeArray<float>(f,"PosDiv",n,DatFloat);
  s.byid.assign(Total,~0u);for(unsigned q=0;q<n;q++){const unsigned id=a.ids[q];Need(id<Total&&s.byid[id]==~0u,"Unknown/duplicate original native ID");s.byid[id]=q;}
  for(unsigned id=0;id<Total;id++){const bool absent=(phase&&Retired(id));Need((s.byid[id]==~0u)==absent,"Missing unselected original ID or surviving retired ID");if(!absent)a.slot.push_back(s.byid[id]);}
  Need(a.slot.size()==n,"Actual original-ID-sorted export length differs");return s;
}
static void Read(const std::string& window,const std::string& backend,const fs::path& dir,const fs::path& pre,const fs::path& out){
  Need(window=="source"||window=="alias0"||window=="receive_old"||window=="receive_new","Use source, alias0, receive_old or receive_new");const bool source=window=="source"||window=="alias0",enabled=true;const Window w{800,.002,.0001};const std::string tag="upl_material_release_native_r1_"+window+"_"+backend;
  const auto tests=fs::path(__FILE__).parent_path().parent_path();Need(tests.is_absolute(),"Compile profile by absolute source path");Need(fs::is_directory(dir)&&fs::equivalent(dir,tests/"outputs"/tag/"data"),"Only exact declared handoff source/receive DATA is admitted");Need(!fs::exists(out),"Retained reader output protected");
  const auto run=RunCsv(dir.parent_path()/"Run.csv",w);const unsigned Steps=unsigned(std::stoul(run.at("Steps"))),Samples=unsigned(std::stoul(run.at("PartFiles")));Sequence(dir,Samples);
  std::vector<unsigned> phases(Samples),completedSaved(Samples);std::vector<double> times(Samples);std::array<unsigned,2> counts{};bool preSeen=!source,postSeen=false;double preTime=0.;unsigned prePart=~0u;fs::path certifiedPre;std::string certifiedContract;JGravityPreloadState certified;
  const auto certify=[&](const fs::path& path){JPartDataBi4 pf;const auto stem=path.stem().string();const unsigned pp=unsigned(std::stoul(stem.substr(5)));pf.LoadFilePart(path.parent_path().string(),pp,0,1);const auto* meta=pf.GetPart();Need(meta->ExistsValue("GravityPreloadHandoffContract",JBinaryDataDef::DatText),"Certified PRE contract missing");certifiedContract=meta->GetvText("GravityPreloadHandoffContract");certified.Load(path.string(),certifiedContract,Total,Fixed,EventStep,EventTime,Dt,5000.f,Por,Rho,Water,Mass,K0Case,CkCase);certifiedPre=path;prePart=pp;preTime=certified.Time;Need(certified.MaterialLawVersion==(window=="receive_old"?1u:2u),"Certified source material-law version differs from the explicit test profile");};
  if(!source){Need(pre!="-"&&fs::is_regular_file(pre),"Receiver needs the genuine source PRE file");certify(pre);}
  // Actual small metadata pass precedes every phase header; no padding/rewrites or assumed21 frames.
  for(unsigned part=0;part<Samples;part++){
    JPartDataBi4 f;f.LoadFilePart(dir.string(),part,0,1);const unsigned completed=(part||!source)?f.Get_Step()+1:0,phase=Phase(f,enabled,preSeen,preTime);const double time=f.Get_TimeStep();
    Need(f.GetNpiece()==1&&f.Get_Npok()==Total-phase*RetireCount&&!f.Get_Nout()&&f.Get_CaseNp()==Total&&f.Get_CaseNfluid()==Soil&&f.Get_CaseNfixed()==Fixed&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat(),"Actual phase size/original registry/unplanned exclusions differ");
    Need(phase==0?!postSeen:true,"Actual native release phase reverted");if(enabled){Need(phase?(completed>EventStep):(completed<=EventStep),"Saved phase disagrees with actual completed step");if(completed==EventStep){Need(source&&!phase&&!preSeen,"Duplicate/invalid forced pre-event save");preSeen=true;preTime=time;prePart=part;certify(dir/JPartDataBi4::GetFileNamePart(part));}if(phase)postSeen=true;}
    phases[part]=phase;completedSaved[part]=completed;times[part]=time;counts[phase]++;
  }
  Need(preSeen&&postSeen&&counts[1]>0&&(source?counts[0]>0:counts[0]==0),"Missing genuine source PRE/post or receiver post witness");Need(source?pre=="-":true,"Source discovers its own genuine certified PRE; pass -");
  const auto x0=InitialCoordinates(tests/"outputs/upl_c08_global_CPU_r1/ids.csv");std::vector<float> initialP0(Total);const double gamma=Water*double(float(9.81));
  for(unsigned id=0;id<Total;id++)initialP0[id]=float(gamma*(Surface-x0[id].z));
  double xmin=DBL_MAX,xmax=-DBL_MAX,zmin=DBL_MAX,zmax=-DBL_MAX;for(unsigned id=Fixed;id<Total;id++){xmin=(std::min)(xmin,x0[id].x);xmax=(std::max)(xmax,x0[id].x);zmin=(std::min)(zmin,x0[id].z);zmax=(std::max)(zmax,x0[id].z);}
  Need(fs::create_directory(out),"Cannot create fresh native output");std::ofstream raw[2],layout(out/"typed22_layout.csv"),clock(out/"clocks.csv"),ids(out/"native_ids.csv"),history(out/"history.csv"),manifest(out/"phases.csv");std::vector<std::ofstream*> streams{&layout,&clock,&ids,&history,&manifest};
  static_assert(sizeof(unsigned)==4&&sizeof(float)==4&&sizeof(double)==8&&sizeof(tfloat3)==12&&sizeof(tdouble3)==24,"Original typed x64 layout differs");
  manifest<<"phase,filename,actual_native_IDs,actual_saved_frames\n";for(unsigned phase=0;phase<2;phase++)if(counts[phase]){const std::string name="phase"+std::to_string(phase)+"_typed22.bin";raw[phase].open(out/name,std::ios::binary);const unsigned h[]={Total-phase*RetireCount,22,counts[phase]};raw[phase].write(reinterpret_cast<const char*>(h),12);manifest<<phase<<','<<name<<','<<h[0]<<','<<h[2]<<'\n';streams.push_back(&raw[phase]);}
  for(auto* f:{&clock,&ids,&history})*f<<std::setprecision(17);
  layout<<"array,type,components,bytes_per_particle\nIdp,uint32,1,4\nPosd,float64,3,24\nVel,float32,3,12\nSigma_kk,float32,3,12\nSigma_ij,float32,3,12\nFSNormal,float32,3,12\nHydroMechLoadAce,float32,3,12\nnative_Rhop,float32,1,4\nKplastic,float32,1,4\nPorePress,float32,1,4\nPorePress0,float32,1,4\nExcessPorePress,float32,1,4\nSigmaState_kk,float64,3,24\nSigmaState_ij,float64,3,24\nFSType,uint32,1,4\nPoroVolumeRatio,float64,1,8\nPoroPorosity,float64,1,8\nPoroThetaLastStage,float64,1,8\nPoroCurrentVolume,float64,1,8\nPoroMixtureDensity,float64,1,8\nPoroHydraulicConductivity,float64,1,8\nPosDiv,float32,1,4\n";
  clock<<"part,file,time_s,completed_step,saved_step,dt_s,signed_dterror_s,dterror_interval_empty,phase,phase_local_index,actual_native_IDs\n";
  ids<<"id,is_fixed,x0,y0,z0,initial_hydrostatic_p0_float_Pa,release_target\n";for(unsigned id=0;id<Total;id++)ids<<id<<','<<(id<Fixed)<<','<<x0[id].x<<','<<x0[id].y<<','<<x0[id].z<<','<<initialP0[id]<<','<<Retired(id)<<'\n';
  history<<"part,time_s,initial_material_band,count,p_mean_Pa,p_RMS_Pa,p_min_Pa,p_max_Pa,sigma_eff_xx_mean_Pa,sigma_eff_yy_mean_Pa,sigma_eff_zz_mean_Pa,sigma_eff_xy_mean_Pa,sigma_eff_yz_mean_Pa,sigma_eff_xz_mean_Pa,sigma_eff_Frobenius_RMS_Pa,mean_dx_m,mean_dy_m,mean_dz_m,displacement_RMS_mm,max_displacement_mm,mean_vx_m_s,mean_vy_m_s,mean_vz_m_s,velocity_XYZ_RMS_m_s,theta_mean_s_inv,theta_RMS_s_inv,min_J,max_J,min_n,max_n,current_soil_mixture_mass_kg_per_m,kinetic_J_per_m,native_excess_mean_Pa,native_excess_RMS_Pa,native_excess_min_Pa,native_excess_max_Pa\n";
  volatile double scalar=0.;unsigned previous=0,lastSaved=0,intervals=0,initialEmpty=0,soilChecks=0,fixedChecks=0,p0Checks=0,cacheChecks=0,monotoneChecks=0,fsChecks=0;double minError=DBL_MAX,maxError=-DBL_MAX,maxLedger=0,maxClockError=0,maxKappa=0;std::array<unsigned,2> local{};std::array<unsigned,5> bandCounts{};std::vector<unsigned> freeCounts(Samples,0);std::vector<float> previousKappa(Total,0.f);unsigned finalNonzeroKappa=0,conductivityChecks=0,conductivityMetadataChecks=0,j1ExactK0Checks=0;double minConductivity=DBL_MAX,maxConductivity=0;
  for(unsigned part=0;part<Samples;part++){
    currentPart=part;currentId=~0u;JPartDataBi4 f;f.LoadFilePart(dir.string(),part,0,1);const unsigned phase=Phase(f,enabled,preSeen,preTime),n=Total-phase*RetireCount,step=f.Get_Step(),completed=(part||!source)?step+1:0;
    Need(phase==phases[part]&&completed==completedSaved[part]&&Bits(f.Get_TimeStep(),times[part])&&f.Get_Npok()==n,"Raw phase metadata changed between counting and export");
    Need(f.Get_Data2d()&&f.Get_Data2dPosY()==0&&!f.Get_Symmetry()&&!f.Get_NpDynamic()&&!f.Get_ReuseIds()&&f.Get_PeriMode()==PERI_None,"Outside fresh static nonperiodic C08 scope");
    Need(f.Get_Dp()==Dp&&f.Get_H()==H&&f.Get_Rhop0()==Rho&&f.Get_MassFluid()==Mass&&f.Get_MassBound()==Mass,"Actual original geometry/material differs");
    Need(!part&&source?step==0:(completed>previous&&completed<=Steps),"Native saved Step is not its actual strictly increasing zero-based count");for(unsigned k=previous;k<completed;k++)scalar+=Dt;previous=completed;lastSaved=step;const double time=f.Get_TimeStep(),clockError=std::fabs(time-double(scalar));Need(std::isfinite(time)&&clockError<=1e-14,"Actual scalar+=dt clock differs");maxClockError=(std::max)(maxClockError,clockError);
    const auto* info=f.GetPart();Need(info->ExistsValue("SymplecticDtPre",DatDouble)&&Bits(info->GetvDouble("SymplecticDtPre"),Dt)&&info->ExistsValue("dterror",DatDouble),"Typed locked dt/signed diagnostic missing");
    const double error=info->GetvDouble("dterror");const bool empty=error==-DBL_MAX;Need(std::isfinite(error),"Nonfinite signed diagnostic");if(part||!source){Need(!empty&&error<=1e-14,"Original noninitial signed necessary-step guard failed/empty");intervals++;minError=(std::min)(minError,error);maxError=(std::max)(maxError,error);}else{Need(empty||error<=1e-14,"Initial signed diagnostic failed");initialEmpty+=unsigned(empty);}
    Need(info->ExistsValue("HydroMechFreeSeepage",DatBool)&&info->GetvBool("HydroMechFreeSeepage")&&info->ExistsValue("MaterialLawVersion",DatUint)&&info->GetvUint("MaterialLawVersion")==2&&!info->ExistsValue("MaterialReturn")&&info->ExistsValue("DilationDecay",DatFloat)&&info->GetvFloat("DilationDecay")==0.f,"Actual free-seepage/material metadata differs");
    const bool eligible=source&&completed==EventStep;
    Need(info->ExistsValue("GravityPreloadHandoffSchema")==eligible&&info->ExistsValue("GravityPreloadElasticSource")==eligible&&info->ExistsValue("GravityPreloadHandoffContract")==eligible&&info->ExistsValue("GravityPreloadSourceCohesion")==eligible,"Certification appeared outside the sole genuine PRE state");
    if(eligible)Need(info->GetvUint("GravityPreloadHandoffSchema")==1&&info->GetvBool("GravityPreloadElasticSource")&&info->GetvText("GravityPreloadHandoffContract")==certifiedContract&&info->GetvFloat("GravityPreloadSourceCohesion")==5000.f,"Native certification differs");
    Need(info->ExistsValue("GravityPreloadStateFile")==!source,"Receiver statefile metadata differs");
    if(!source)Need(fs::equivalent(fs::path(info->GetvText("GravityPreloadStateFile")),certifiedPre),"Receiver imported source path differs");
    Need(f.ArraysCount()==22,"Exactly22 public typed arrays required");MetadataCk2(f);conductivityMetadataChecks++;const Sample sample=LoadActual(f,phase);const Native& a=sample.a;Summary bands[5];const double v0=f.Get_MassFluid()/f.Get_Rhop0();
    for(unsigned id=0;id<Total;id++){
      if(phase&&Retired(id))continue;currentId=id;const unsigned q=sample.byid[id];const auto x=a.pos[q],s=a.sk[q],t=a.si[q];currentJ=a.j[q];currentRhop=a.rhop[q];currentP=a.p[q];
      Need(a.rhop[q]>=700.f&&a.rhop[q]<=3000.f&&a.plastic[q]>=0&&Bits(a.p0[q],initialP0[id])&&a.excess[q]==float(a.p[q]-a.p0[q])&&a.fstype[q]<=4&&Norm2(a.load[q])==0&&x.y==0,"Original density/nonnegative history/p0/excess/FSType/no-load/2D guard failed");
      Need(a.legacykk[q].x==float(s.x)&&a.legacykk[q].y==float(s.y)&&a.legacykk[q].z==float(s.z)&&a.legacyij[q].x==float(t.x)&&a.legacyij[q].y==float(t.y)&&a.legacyij[q].z==float(t.z),"Float display does not round native double stress");p0Checks++;
      if(!part&&source)Need(!std::memcmp(&x,&x0[id],sizeof(x))&&a.plastic[q]==0&&Norm2(s)==0&&Norm2(t)==0,"Initial native geometry/kappa/zero effective stress differs");
      if(id<Fixed){Need(a.plastic[q]==0&&!std::memcmp(&x,&x0[id],sizeof(x))&&Norm2(a.vel[q])==0&&a.j[q]>1.-Por&&a.theta[q]==0&&a.n[q]==0&&a.volume[q]==0&&a.rho[q]==0&&a.k[q]==0,"Original retained fixed geometry/velocity/J/theta/zero marker differs");fixedChecks++;}
      else{
        Need(a.plastic[q]>=previousKappa[id],"Soil kappa decreased by original native ID");if(part)monotoneChecks++;previousKappa[id]=a.plastic[q];maxKappa=(std::max)(maxKappa,double(a.plastic[q]));if(part+1==Samples)finalNonzeroKappa+=unsigned(a.plastic[q]>0);
        if(a.fstype[q]==2||a.fstype[q]==3){Need(a.p[q]<=0,"Actual native free-surface soil pressure is positive");fsChecks++;freeCounts[part]++;}
        const double j=a.j[q],pn=1.-(1.-Por)/j,V=v0*j,rho=Water+(Rho-Water)/j,k=(j==1.?K0Case:K0Case*std::exp((j-1.)/((1.-Por)*CkCase)));Need(j>1.-Por&&pn>0&&pn<1&&V>0&&rho>0&&std::fabs((1.-a.n[q])*j-(1.-Por))<=5e-13,"Original single-J solid-volume ledger failed");
        Need(std::isfinite(k)&&k>0&&a.k[q]>0,"Actual/reference Ck2 conductivity is not finite positive");if(j==1.){Need(Bits(a.k[q],K0Case),"J1 conductivity is not exact original float k0");j1ExactK0Checks++;}conductivityChecks++;minConductivity=(std::min)(minConductivity,a.k[q]);maxConductivity=(std::max)(maxConductivity,a.k[q]);
        const double got[]={a.n[q],a.volume[q],a.rho[q],a.k[q]},ref[]={pn,V,rho,k};for(unsigned z=0;z<4;z++){Need(Close(got[z],ref[z]),"Native n/V/rho/k differs from actual J");maxLedger=(std::max)(maxLedger,std::fabs(got[z]-ref[z])/(std::max)(std::fabs(ref[z]),DBL_MIN));}
        Need(Bits(a.rhop[q],float(rho)),"Native float density cache differs from actual saved J");cacheChecks++;soilChecks++;
        if(!part&&source){const bool sf=a.fstype[q]==2||a.fstype[q]==3;const float p=sf&&initialP0[id]>0.f?0.f:initialP0[id];Need(a.j[q]==1&&a.n[q]==Por&&a.theta[q]==0&&a.rhop[q]==Rho&&Norm2(a.vel[q])==0&&Bits(a.p[q],p),"Initial J1/rest/static p0 and true-FS projection differ");}
        bands[0].add(a,q,x0[id]);if(x0[id].z>=zmax-2*H)bands[1].add(a,q,x0[id]);if(x0[id].z<=zmin+2*H)bands[2].add(a,q,x0[id]);if(x0[id].x<=xmin+2*H)bands[3].add(a,q,x0[id]);if(x0[id].x>=xmax-2*H)bands[4].add(a,q,x0[id]);
      }
    }
    Need(freeCounts[part]>0,"Actual saved free-seepage mask empty");raw[phase].write(reinterpret_cast<const char*>(&time),8);Typed22(raw[phase],a);clock<<part<<','<<JPartDataBi4::GetFileNamePart(part)<<','<<time<<','<<completed<<','<<step<<','<<Dt<<','<<error<<','<<empty<<','<<phase<<','<<local[phase]++<<','<<n<<'\n';
    const char* names[]={"all","top_2h","bottom_2h","left_2h","right_2h"};for(unsigned z=0;z<5;z++){if(!part)bandCounts[z]=bands[z].count;Need(bands[z].count==bandCounts[z],"Initial material band IDs changed");bands[z].write(history,part,time,names[z]);}
  }
  const unsigned expectedFixed=Fixed*counts[0]+(Fixed-RetireCount)*counts[1],expectedP0=Total*counts[0]+(Total-RetireCount)*counts[1];
  Need(previous==Steps&&intervals==Samples-(source?1u:0u)&&soilChecks==Soil*Samples&&fixedChecks==expectedFixed&&p0Checks==expectedP0&&cacheChecks==Soil*Samples&&monotoneChecks==Soil*(Samples-1)&&local==counts&&conductivityChecks==Soil*Samples&&conductivityMetadataChecks==Samples,"Incomplete actual phase/ID/ledger/p0/cache/clock/Ck2 coverage");Need(std::fabs(times.back()-w.end)<=Dt+1e-14,"Actual owner-capped final time differs");
  for(auto* f:streams){f->flush();Need(bool(*f),"Phase/native export write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_material_release_native_r1\",\"input_run_tag\":\""<<tag<<"\",\"passed\":true,\"backend_argument\":\""<<backend<<"\",\"backend_proven_by_reader\":false,\"window\":\""<<window<<"\",\"samples\":"<<Samples<<",\"completed_steps\":"<<previous<<",\"last_saved_step\":"<<lastSaved<<",\"actual_end_s\":"<<times.back()<<",\"scalar_reference_end_s\":"<<double(scalar)<<",\"dt_s\":"<<Dt<<",\"declared_output_interval_s\":"<<w.output<<",\"phase_saved_frames\":["<<counts[0]<<','<<counts[1]<<"],\"phase0_native_IDs\":7060,\"phase1_native_IDs\":6800,\"phase1_export_written\":"<<(counts[1]?"true":"false")<<",\"original_case_ID_domain\":7060,\"soil_IDs\":5000,\"original_fixed_IDs\":2060,\"typed_arrays\":22,\"typed_bytes_per_particle\":212,\"max_scalar_clock_error_s\":"<<maxClockError;
  done<<",\"qualified_PRE_read_by_current_helper\":true,\"import_schema\":1,\"source_contract_validated_against_self_only\":true,\"fresh_target_contract_enforced_by_solver_not_reader\":true,\"receiver_part0_is_not_t0\":"<<(source?"false":"true")<<",\"source_PRE_completed_step\":"<<certified.CompletedStep<<",\"source_material_law_version\":"<<certified.MaterialLawVersion<<",\"source_PRE_actual_time_s\":"<<certified.Time<<",\"certified_pre_filename\":\""<<certifiedPre.filename().string()<<"\"";
  if(enabled)done<<",\"genuine_pre_event_part\":"<<prePart<<",\"genuine_pre_event_time_s\":"<<preTime<<",\"event_completed_step\":"<<EventStep<<",\"retired_native_begin\":1800,\"retired_native_count\":260";
  done<<",\"soil_ledger_checks\":"<<soilChecks<<",\"fixed_marker_checks\":"<<fixedChecks<<",\"all_present_ID_p0_float_bits_checks\":"<<p0Checks<<",\"soil_cache_float_bits_checks\":"<<cacheChecks<<",\"soil_noninitial_kappa_monotonic_checks\":"<<monotoneChecks<<",\"max_ledger_relative_error\":"<<maxLedger<<",\"max_kappa\":"<<maxKappa<<",\"final_kappa_nonzero_IDs\":"<<finalNonzeroKappa<<",\"saved_FS23_soil_checks\":"<<fsChecks<<",\"saved_FS23_soil_checks_by_part\":[";for(unsigned p=0;p<Samples;p++)done<<(p?",":"")<<freeCounts[p];
  done<<"],\"HydroMechConductivityModel\":1,\"HydroMechConductivityCk\":2,\"conductivity_model_metadata_checks\":"<<conductivityMetadataChecks<<",\"soil_conductivity_J_law_checks\":"<<conductivityChecks<<",\"soil_J1_exact_k0_checks\":"<<j1ExactK0Checks<<",\"soil_conductivity_min_m_s\":"<<minConductivity<<",\"soil_conductivity_max_m_s\":"<<maxConductivity<<",\"noninitial_signed_intervals\":"<<intervals<<",\"initial_empty_intervals\":"<<initialEmpty<<",\"min_noninitial_signed_dterror_s\":"<<minError<<",\"max_noninitial_signed_dterror_s\":"<<maxError<<",\"all22_arrays_finite_and_original_ID_aligned\":true,\"actual_scalar_clock_verified\":true,\"actual_metadata_counted_before_export_headers\":true,\"original_case_registry_unchanged\":true,\"only_declared_fixed_ID_retirement_allowed\":true,\"unplanned_or_fluid_exclusions\":0,\"OFF_metadata_absence_checked\":"<<(enabled?"false":"true")<<",\"native_saved_steps_or_arrays_rewritten\":false,\"initial_effective_stress_zero\":"<<(source?"true":"false")<<",\"p0_fixed_initial_material_baseline\":true,\"saved_FS23_soil_pressure_nonpositive\":true,\"same_backend_prefix_0ULP_proven_by_reader\":false,\"CODE_or_total_Ace_or_wall_reaction_native_array_present\":false,\"restart_or_material_force_or_physical_acceptance_claimed\":false,\"owned_solver_exit_verified_by_reader\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
}
}
namespace releaseplastic {
constexpr unsigned Total=1024,Rows=32,Steps=256,Samples=5;
constexpr double Dt=.000001,Dp=.04,Length=1.28,Rho=2072.5,Water=1000.,WaterBulk=1e9;
static const double Por=double(float(.35)),Mass=double(float(3.316)),H=double(float(.048)),Kcase=double(float(.0002));
static unsigned currentPart=~0u,currentId=~0u;
static bool Bits(float a,float b){return !std::memcmp(&a,&b,4);}
static bool Bits(double a,double b){return !std::memcmp(&a,&b,8);}
static std::vector<std::string> Tokens(std::string s,char sep){
  if(!s.empty()&&s.back()=='\r')s.pop_back();std::vector<std::string> v;std::size_t b=0;
  for(;;){const auto p=s.find(sep,b);v.push_back(s.substr(b,p==std::string::npos?p:p-b));if(p==std::string::npos)break;b=p+1;}return v;
}
struct VelocityRow{double z,lo,hi;float vx;};
static std::array<VelocityRow,Rows> Velocity(const fs::path& p){
  std::ifstream f(p);std::string line;Need(bool(std::getline(f,line)),"Declared velocity CSV missing");
  Need(Tokens(line,',')==std::vector<std::string>{"row","z","vx_float","vx_float_bits_hex","z_min","z_max"},"Declared velocity CSV schema differs");
  std::array<VelocityRow,Rows> rows{};std::array<bool,Rows> seen{};unsigned count=0;
  while(std::getline(f,line)){
    const auto t=Tokens(line,',');Need(t.size()==6,"Velocity CSV width differs");const unsigned row=unsigned(std::stoul(t[0]));Need(row<Rows&&!seen[row],"Duplicate/invalid velocity row");
    const double v=std::stod(t[2]);const float vf=float(v);unsigned bits=0;std::memcpy(&bits,&vf,4);
    rows[row]={std::stod(t[1]),std::stod(t[4]),std::stod(t[5]),vf};const auto& a=rows[row];
    Need(std::isfinite(a.z)&&std::isfinite(a.lo)&&std::isfinite(a.hi)&&std::isfinite(v)&&double(vf)==v&&bits==unsigned(std::stoul(t[3],nullptr,16)),"Velocity literal/pre-rounded float bits differ");
    Need(a.lo<a.z&&a.z<a.hi&&std::fabs(a.z-(row+.5)*Dp)<=64*DBL_EPSILON*Length,"Declared velocity row location differs");seen[row]=true;count++;
  }Need(f.eof()&&count==Rows,"Exactly32 velocity rows required");return rows;
}
static void RunCsv(const fs::path& p){
  std::ifstream f(p);std::string h,d,x;Need(bool(std::getline(f,h))&&bool(std::getline(f,d))&&!std::getline(f,x),"Actual completed two-line Run.csv required");
  const char sep=h.find(';')==std::string::npos?',':';';const auto names=Tokens(h,sep),values=Tokens(d,sep);Need(names.size()==values.size(),"Run.csv width differs");std::map<std::string,std::string> r;
  for(unsigned i=0;i<names.size();i++)Need(r.emplace(names[i],values[i]).second,"Repeated Run.csv column");
  for(const auto& kv:std::vector<std::pair<std::string,unsigned>>{{"Steps",256},{"PartFiles",5},{"Np",1024},{"Nfixed",0},{"Nbound",0},{"PartsOut",0},{"PartsOutRhop",0},{"PartsOutVel",0}})
    Need(unsigned(std::stoul(r.at(kv.first)))==kv.second,"Actual native count/exclusion differs: "+kv.first);
}
static void Typed22(std::ofstream& out,const Native& a){
  Original15(out,a);for(const auto* v:{&a.j,&a.n,&a.theta,&a.volume,&a.rho,&a.k})WriteTyped(out,*v,a.slot);WriteTyped(out,a.posdiv,a.slot);
}
static void Read(const std::string& backend,const fs::path& dir,const fs::path& out){
  const auto tests=fs::path(__FILE__).parent_path().parent_path();Need(tests.is_absolute(),"Compile this profile by absolute path");const std::string tag="upl_material_release_native_r1_plastic_"+backend;
  Need(fs::is_directory(dir)&&fs::equivalent(dir,tests/"outputs"/tag/"data"),"Only the declared periodic-shear CPU/GPU r1 DATA is admitted");
  Need(!fs::exists(out),"Retained native output protected");RunCsv(dir.parent_path()/"Run.csv");Sequence(dir,Samples);
  const auto velocity=Velocity(tests/"support/upl_material_periodic_shear_r1_velocity.csv");
  Need(fs::create_directory(out),"Cannot create fresh native output");std::ofstream raw(out/"typed22.bin",std::ios::binary),layout(out/"typed22_layout.csv"),clock(out/"clocks.csv"),ids(out/"native_ids.csv"),ledger(out/"ledger.csv"),history(out/"history.csv");
  static_assert(sizeof(unsigned)==4&&sizeof(float)==4&&sizeof(double)==8&&sizeof(tfloat3)==12&&sizeof(tdouble3)==24,"Original typed x64 layout differs");
  const unsigned header[]={Total,22,Samples};raw.write(reinterpret_cast<const char*>(header),12);
  for(auto* f:{&clock,&ids,&ledger,&history})*f<<std::setprecision(17);
  layout<<"array,type,components,bytes_per_particle\nIdp,uint32,1,4\nPosd,float64,3,24\nVel,float32,3,12\nSigma_kk,float32,3,12\nSigma_ij,float32,3,12\nFSNormal,float32,3,12\nHydroMechLoadAce,float32,3,12\nnative_Rhop,float32,1,4\nKplastic,float32,1,4\nPorePress,float32,1,4\nPorePress0,float32,1,4\nExcessPorePress,float32,1,4\nSigmaState_kk,float64,3,24\nSigmaState_ij,float64,3,24\nFSType,uint32,1,4\nPoroVolumeRatio,float64,1,8\nPoroPorosity,float64,1,8\nPoroThetaLastStage,float64,1,8\nPoroCurrentVolume,float64,1,8\nPoroMixtureDensity,float64,1,8\nPoroHydraulicConductivity,float64,1,8\nPosDiv,float32,1,4\n";
  clock<<"part,file,time_s,completed_step,saved_step,dt_s,signed_dterror_s,dterror_interval_empty\n";
  ids<<"id,x0,y0,z0,x_lattice_index,z_velocity_row,declared_vx_float\n";
  ledger<<"part,time_s,id,J,n_native,theta_native,V_native_m2,rho_native_kg_m3,k_native_m_s,native_Rhop,V_reference_m2,rho_reference_kg_m3,k_reference_m_s,kappa_previous_float,kappa_native_float,kappa_increment_float,effective_DP_PS_yield_Pa_descriptive\n";
  history<<"part,time_s,p_mean_Pa,p_RMS_Pa,p_min_Pa,p_max_Pa,kappa_min,kappa_max,kappa_RMS,kappa_nonzero_IDs,kappa_increased_IDs,FS0,FS1,FS2,FS3,FS4,min_J,max_J,min_n,max_n,theta_RMS_s_inv,velocity_XYZ_RMS_m_s,min_image_displacement_RMS_mm,min_image_displacement_max_mm,sigma_eff_Frobenius_RMS_Pa,total_sigma_Frobenius_RMS_Pa,max_effective_DP_PS_yield_Pa_descriptive,current_mixture_mass_kg_per_m,kinetic_J_per_m,max_reference_wave_Courant,max_Ddt_h2\n";
  std::vector<tdouble3> initial(Total);std::vector<float> previousKappa(Total,0.f);std::array<bool,Total> gridSeen{};std::array<unsigned,Rows> rowCounts{};
  volatile double scalar=0.;unsigned previousStep=0,intervals=0,initialEmpty=0,ledgerChecks=0,cacheChecks=0,metadataChecks=0,monotoneChecks=0,initialVelocityChecks=0,finalNonzero=0;
  double minError=DBL_MAX,maxError=-DBL_MAX,maxLedger=0,maxKappa=0,maxPlasticDecrease=0;std::array<unsigned,Samples> freeCounts{};
  const float E=20000000.f,nu=.33f,phi=float(25.*3.1415926535897932384626433832795/180.);
  const double G=double(E/(2.f*(1.f+nu))),K=double(E/(3.f*(1.f-2.f*nu))),M=K+4.*G/3.,tp=std::tan(double(phi)),den=std::sqrt(9.+12.*tp*tp),alpha=tp/den,kc=3.*5000./den;
  for(unsigned part=0;part<Samples;part++){
    currentPart=part;currentId=~0u;JPartDataBi4 f;f.LoadFilePart(dir.string(),part,0,1);
    Need(f.GetNpiece()==1&&f.Get_Npok()==Total&&!f.Get_Nout()&&f.Get_CaseNp()==Total&&f.Get_CaseNfluid()==Total&&!f.Get_CaseNfixed()&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat(),"Native owner IDs/counts/exclusions differ");
    Need(f.Get_Data2d()&&f.Get_Data2dPosY()==0&&!f.Get_Symmetry()&&!f.Get_NpDynamic()&&!f.Get_ReuseIds()&&f.Get_PeriMode()==PERI_XZ,"Outside declared fixed-set XZ-periodic2D scope");
    Need(f.Get_Dp()==Dp&&f.Get_H()==H&&f.Get_Rhop0()==Rho&&f.Get_MassFluid()==Mass,"Actual float h/mass/reference density differs");
    const unsigned step=f.Get_Step(),completed=part?step+1:0;Need(!part?step==0:(completed>previousStep&&completed<=Steps),"Actual saved Step is not strictly increasing within the declared 256 updates");
    for(unsigned n=previousStep;n<completed;n++)scalar+=Dt;previousStep=completed;const double time=f.Get_TimeStep();Need(Bits(time,scalar),"Actual decimal scalar+=dt clock differs");
    const auto* info=f.GetPart();Need(info->ExistsValue("SymplecticDtPre",DatDouble)&&Bits(info->GetvDouble("SymplecticDtPre"),Dt)&&info->ExistsValue("dterror",DatDouble),"Typed locked dt/signed diagnostic missing");
    Need(info->ExistsValue("MaterialLawVersion",DatUint)&&info->GetvUint("MaterialLawVersion")==2&&!info->ExistsValue("MaterialReturn")&&info->ExistsValue("DilationDecay",DatFloat)&&info->GetvFloat("DilationDecay")==0.f,"Explicit radial material metadata differs");
    Need(!info->ExistsValue("HydroMechFreeSeepage"),"Free-seepage true-only metadata must remain absent in the periodic fixture");Metadata(f,0);metadataChecks++;
    const double error=info->GetvDouble("dterror");const bool empty=error==-DBL_MAX;Need(std::isfinite(error),"Nonfinite signed diagnostic");
    if(part){Need(!empty&&error<=1e-14,"Original noninitial signed necessary-step guard failed/empty");intervals++;minError=(std::min)(minError,error);maxError=(std::max)(maxError,error);}
    else{Need(empty||error<=1e-14,"Initial signed diagnostic failed");initialEmpty+=unsigned(empty);}
    Need(f.ArraysCount()==22,"Exactly22 public typed arrays required");const Native a=Load(f,Total,0);const double v0=f.Get_MassFluid()/f.Get_Rhop0();
    double ps=0,p2=0,pmin=DBL_MAX,pmax=-DBL_MAX,kmin=DBL_MAX,kmax=0,k2=0,jmin=DBL_MAX,jmax=-DBL_MAX,nmin=DBL_MAX,nmax=-DBL_MAX,theta2=0,v2=0,u2=0,umax=0,s2=0,total2=0,fmax=-DBL_MAX,mass=0,kinetic=0,wave=0,diff=0;
    unsigned nonzero=0,increased=0;std::array<unsigned,5> types{};
    for(unsigned id=0;id<Total;id++){
      currentId=id;const unsigned q=a.slot[id];const auto x=a.pos[q],s=a.sk[q],t=a.si[q];const float kap=a.plastic[q],old=previousKappa[id];
      Need(a.rhop[q]>=700&&a.rhop[q]<=3000&&kap>=0.f&&kap>=old&&a.p0[q]==0&&a.excess[q]==float(a.p[q]-a.p0[q])&&a.fstype[q]<5&&Norm2(a.load[q])==0&&x.y==0,"Density/plastic history/p0/excess/FSType/no-load/2D guard failed");
      Need(a.legacykk[q].x==float(s.x)&&a.legacykk[q].y==float(s.y)&&a.legacykk[q].z==float(s.z)&&a.legacyij[q].x==float(t.x)&&a.legacyij[q].y==float(t.y)&&a.legacyij[q].z==float(t.z),"Float display no longer rounds native double stress");
      if(!part){
        const long ix=std::lround(x.x/Dp-.5),iz=std::lround(x.z/Dp-.5);Need(ix>=0&&ix<long(Rows)&&iz>=0&&iz<long(Rows),"Initial owner outside32x32 lattice");
        const unsigned cell=unsigned(iz)*Rows+unsigned(ix);const auto& vr=velocity[unsigned(iz)];
        Need(!gridSeen[cell]&&std::fabs(x.x-(ix+.5)*Dp)<=64*DBL_EPSILON*Length&&std::fabs(x.z-vr.z)<=64*DBL_EPSILON*Length&&x.z>=vr.lo&&x.z<=vr.hi,"Initial owner grid/declared onlypos row differs");
        Need(Bits(a.vel[q].x,vr.vx)&&a.vel[q].y==0&&a.vel[q].z==0&&kap==0&&a.p[q]==0&&Norm2(s)==0&&Norm2(t)==0&&a.j[q]==1&&a.n[q]==Por&&a.theta[q]==0&&a.rhop[q]==Rho,"Initial actual declared velocity/J1/p/stress/history differs");
        initial[id]=x;gridSeen[cell]=true;rowCounts[unsigned(iz)]++;initialVelocityChecks++;ids<<id<<','<<x.x<<','<<x.y<<','<<x.z<<','<<ix<<','<<iz<<','<<vr.vx<<'\n';
      }else{monotoneChecks++;maxPlasticDecrease=(std::max)(maxPlasticDecrease,double(old)-kap);}
      const double j=a.j[q],n=1.-(1.-Por)/j,V=v0*j,rho=Water+(Rho-Water)/j,k=Kcase,mi=a.rho[q]*a.volume[q];
      Need(j>1.-Por&&n>0&&n<1&&V>0&&rho>0&&std::fabs((1.-a.n[q])*j-(1.-Por))<=5e-13,"Saturated single-J ledger failed");
      const double got[]={a.n[q],a.volume[q],a.rho[q],a.k[q]},ref[]={n,V,rho,k};for(unsigned z=0;z<4;z++){Need(Close(got[z],ref[z]),"Native n/V/rho/k differs from actual J");maxLedger=(std::max)(maxLedger,std::fabs(got[z]-ref[z])/(std::max)(std::fabs(ref[z]),DBL_MIN));}
      Need(Bits(a.rhop[q],float(rho)),"Native Rhop cache differs from actual saved J");cacheChecks++;ledgerChecks++;
      const double I=s.x+s.y+s.z,qeff=std::sqrt(((s.x-s.y)*(s.x-s.y)+(s.x-s.z)*(s.x-s.z)+(s.y-s.z)*(s.y-s.z))/6.+Norm2(t)),yield=qeff+alpha*I-kc;
      auto u=x-initial[id];u.x-=Length*std::round(u.x/Length);u.z-=Length*std::round(u.z/Length);const double uu=Norm2(u),vv=Norm2(a.vel[q]);
      ps+=a.p[q];p2+=double(a.p[q])*a.p[q];pmin=(std::min)(pmin,double(a.p[q]));pmax=(std::max)(pmax,double(a.p[q]));kmin=(std::min)(kmin,double(kap));kmax=(std::max)(kmax,double(kap));k2+=double(kap)*kap;
      nonzero+=unsigned(kap>0);increased+=unsigned(kap>old);types[a.fstype[q]]++;jmin=(std::min)(jmin,j);jmax=(std::max)(jmax,j);nmin=(std::min)(nmin,n);nmax=(std::max)(nmax,n);theta2+=a.theta[q]*a.theta[q];v2+=vv;u2+=uu;umax=(std::max)(umax,std::sqrt(uu));
      s2+=Norm2(s)+2*Norm2(t);const auto total=s-TDouble3(a.p[q]);total2+=Norm2(total)+2*Norm2(t);fmax=(std::max)(fmax,yield);mass+=mi;kinetic+=.5*mi*vv;
      const double D=WaterBulk/n*k/(Water*9.80665),cu=std::sqrt((M+WaterBulk/n)/rho);wave=(std::max)(wave,cu*Dt/H);diff=(std::max)(diff,D*Dt/(H*H));
      ledger<<part<<','<<time<<','<<id<<','<<j<<','<<a.n[q]<<','<<a.theta[q]<<','<<a.volume[q]<<','<<a.rho[q]<<','<<a.k[q]<<','<<a.rhop[q]<<','<<V<<','<<rho<<','<<k<<','<<old<<','<<kap<<','<<float(kap-old)<<','<<yield<<'\n';previousKappa[id]=kap;
    }
    if(!part)for(unsigned n:rowCounts)Need(n==Rows,"Initial velocity row lacks32 unique native owners");
    freeCounts[part]=types[2]+types[3];maxKappa=(std::max)(maxKappa,kmax);if(part+1==Samples)finalNonzero=nonzero;
    const double values[]={ps/Total,std::sqrt(p2/Total),pmin,pmax,kmin,kmax,std::sqrt(k2/Total),jmin,jmax,nmin,nmax,std::sqrt(theta2/Total),std::sqrt(v2/Total),1000*std::sqrt(u2/Total),1000*umax,std::sqrt(s2/Total),std::sqrt(total2/Total),fmax,mass,kinetic,wave,diff};for(double v:values)Need(std::isfinite(v),"Nonfinite descriptive periodic history");
    history<<part<<','<<time;for(unsigned n=0;n<7;n++)history<<','<<values[n];history<<','<<nonzero<<','<<increased;for(unsigned n:types)history<<','<<n;for(unsigned n=7;n<22;n++)history<<','<<values[n];history<<'\n';
    raw.write(reinterpret_cast<const char*>(&time),8);Typed22(raw,a);clock<<part<<','<<JPartDataBi4::GetFileNamePart(part)<<','<<time<<','<<completed<<','<<step<<','<<Dt<<','<<error<<','<<empty<<'\n';
  }
  Need(previousStep==Steps&&intervals==4&&ledgerChecks==5120&&cacheChecks==5120&&metadataChecks==5&&initialVelocityChecks==1024&&monotoneChecks==4096&&finalNonzero>0,"Incomplete256-step periodic/plastic witness");
  for(auto* f:{&raw,&layout,&clock,&ids,&ledger,&history}){f->flush();Need(bool(*f),"Native export write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_material_release_native_r1_plastic\",\"input_run_tag\":\""<<tag<<"\",\"passed\":true,\"backend_argument\":\""<<backend<<"\",\"backend_proven_by_reader\":false,\"samples\":5,\"completed_steps\":256,\"actual_end_s\":"<<double(scalar)<<",\"dt_s\":"<<Dt<<",\"total_native_IDs\":1024,\"soil_IDs\":1024,\"fixed_IDs\":0,\"fixed_marker_rows\":0,\"fixed_marker_policy\":\"not applicable\",\"typed_arrays\":22,\"typed_bytes_per_particle\":212,\"ledger_checks\":"<<ledgerChecks<<",\"native_Rhop_float_cache_checks\":"<<cacheChecks<<",\"initial_velocity_bits_checks\":"<<initialVelocityChecks<<",\"noninitial_kappa_monotonic_ID_checks\":"<<monotoneChecks<<",\"final_kappa_nonzero_IDs\":"<<finalNonzero<<",\"max_kappa\":"<<maxKappa<<",\"max_kappa_decrease\":"<<maxPlasticDecrease<<",\"max_ledger_relative_error\":"<<maxLedger<<",\"noninitial_signed_intervals\":"<<intervals<<",\"initial_empty_intervals\":"<<initialEmpty<<",\"min_noninitial_signed_dterror_s\":"<<minError<<",\"max_noninitial_signed_dterror_s\":"<<maxError<<",\"FS23_counts_by_part\":["<<freeCounts[0]<<','<<freeCounts[1]<<','<<freeCounts[2]<<','<<freeCounts[3]<<','<<freeCounts[4]<<"],\"all22_arrays_finite_and_ID_aligned\":true,\"actual_scalar_clock_verified\":true,\"later_pressure_J_theta_forced_zero\":false,\"yield_and_wave_diagnostics_are_descriptive\":true,\"energy_or_water_mass_gate_applied\":false,\"half_or_cross_backend_error_gate\":false,\"physical_acceptance\":false}\n";
  done.flush();Need(bool(done),"Completion write failed");
}
}
namespace releasefluid {
constexpr unsigned Total=1024,Steps=4;constexpr double Dt=.000001;
static void Read(const std::string& backend,const fs::path& dir,const fs::path& out){
  const auto tests=fs::path(__FILE__).parent_path().parent_path();const std::string tag="upl_material_release_native_r1_fluid_"+backend;
  Need(tests.is_absolute()&&fs::equivalent(dir,tests/"outputs"/tag/"data")&&!fs::exists(out),"Only the fresh declared pure-fluid profile is admitted");
  std::ifstream run(dir.parent_path()/"Run.csv");std::string h,d,x;Need(bool(std::getline(run,h))&&bool(std::getline(run,d))&&!std::getline(run,x),"Completed fluid Run.csv required");
  const auto names=c08releasegravity::Tokens(h,';'),values=c08releasegravity::Tokens(d,';');Need(names.size()==values.size(),"Fluid summary width differs");std::map<std::string,std::string> r;for(unsigned n=0;n<names.size();n++)r[names[n]]=values[n];
  Need(std::stoul(r.at("Steps"))==Steps&&std::stoul(r.at("Np"))==Total&&!std::stoul(r.at("Nfixed"))&&!std::stoul(r.at("PartsOut"))&&!std::stoul(r.at("PartsOutRhop"))&&!std::stoul(r.at("PartsOutVel")),"Fluid actual updates/registry/exclusions differ");
  const unsigned samples=unsigned(std::stoul(r.at("PartFiles")));Need(samples>=2&&samples<=6,"Fluid saves outside bounded four-update profile");Sequence(dir,samples);Need(fs::create_directory(out),"Fresh fluid output required");
  std::ofstream raw(out/"typed7.bin",std::ios::binary),clock(out/"clocks.csv"),history(out/"history.csv"),layout(out/"typed7_layout.csv");
  const unsigned header[]={Total,7,samples};raw.write(reinterpret_cast<const char*>(header),12);clock<<std::setprecision(17)<<"part,file,time_s,completed_step,saved_step,dt_s,signed_dterror_s,dterror_interval_empty\n";history<<std::setprecision(17)<<"part,time_s,native_IDs,kappa_nonzero_IDs,max_speed_m_s,min_rho,max_rho\n";
  layout<<"array,type,components,bytes_per_particle\nIdp,uint32,1,4\nPosd,float64,3,24\nVel,float32,3,12\nnative_Rhop,float32,1,4\nKplastic,float32,1,4\nSigmaState_kk,float64,3,24\nSigmaState_ij,float64,3,24\n";
  volatile double scalar=0.;unsigned previous=0,intervals=0,checks=0;double maxClock=0.,maxError=-DBL_MAX;
  for(unsigned part=0;part<samples;part++){
    JPartDataBi4 f;f.LoadFilePart(dir.string(),part,0,1);Need(f.GetNpiece()==1&&f.Get_Npok()==Total&&!f.Get_Nout()&&f.Get_CaseNp()==Total&&f.Get_CaseNfluid()==Total&&!f.Get_CaseNfixed()&&f.Get_PeriMode()==PERI_XZ&&f.Get_Data2d(),"Fluid native registry/domain differs");
    const unsigned step=f.Get_Step(),completed=part?step+1:0;Need(!part?step==0:(completed>previous&&completed<=Steps),"Fluid actual saved Step differs");for(unsigned k=previous;k<completed;k++)scalar+=Dt;previous=completed;
    const double time=f.Get_TimeStep(),ce=std::fabs(time-double(scalar));Need(std::isfinite(time)&&ce<=1e-14,"Fluid actual scalar clock differs");maxClock=(std::max)(maxClock,ce);const auto* meta=f.GetPart();
    Need(!meta->ExistsValue("MaterialLawVersion")&&!meta->ExistsValue("MaterialReturn")&&!meta->ExistsValue("DilationDecay")&&!meta->ExistsValue("HydroMechDynamicSeepage"),"Pure fluid gained soil/dynamic metadata");
    Need(meta->ExistsValue("SymplecticDtPre",DatDouble)&&c08releasegravity::Bits(meta->GetvDouble("SymplecticDtPre"),Dt)&&meta->ExistsValue("dterror",DatDouble),"Fluid typed dt/diagnostic missing");const double er=meta->GetvDouble("dterror");const bool empty=er==-DBL_MAX;
    Need(std::isfinite(er)&&(!part?(empty||er<=1e-14):(!empty&&er<=1e-14)),"Fluid signed necessary-step diagnostic failed");if(part){intervals++;maxError=(std::max)(maxError,er);}
    const auto id=NativeArray<unsigned>(f,"Idp",Total,DatUint);const auto pos=NativeArray<tdouble3>(f,"Posd",Total,DatDouble3);const auto vel=NativeArray<tfloat3>(f,"Vel",Total,DatFloat3);const auto rho=NativeArray<float>(f,"Rhop",Total,DatFloat);const auto kap=NativeArray<float>(f,"Kplastic",Total,DatFloat);const auto kk=NativeArray<tdouble3>(f,"SigmaState_kk",Total,DatDouble3);const auto ij=NativeArray<tdouble3>(f,"SigmaState_ij",Total,DatDouble3);
    std::vector<unsigned> byid(Total,~0u);double speed=0.,rmin=DBL_MAX,rmax=-DBL_MAX;for(unsigned q=0;q<Total;q++){Need(id[q]<Total&&byid[id[q]]==~0u,"Fluid duplicate/unknown native ID");byid[id[q]]=q;Need(Finite(pos[q])&&Finite(vel[q])&&Finite(kk[q])&&Finite(ij[q])&&std::isfinite(rho[q])&&rho[q]>=700&&rho[q]<=3000&&kap[q]==0.f,"Fluid finite/rho/zero-history guard failed");speed=(std::max)(speed,std::sqrt(Norm2(vel[q])));rmin=(std::min)(rmin,double(rho[q]));rmax=(std::max)(rmax,double(rho[q]));checks++;}
    for(unsigned q:byid)Need(q!=~0u,"Fluid missing original native ID");raw.write(reinterpret_cast<const char*>(&time),8);WriteTyped(raw,id,byid);WriteTyped(raw,pos,byid);WriteTyped(raw,vel,byid);WriteTyped(raw,rho,byid);WriteTyped(raw,kap,byid);WriteTyped(raw,kk,byid);WriteTyped(raw,ij,byid);
    clock<<part<<','<<JPartDataBi4::GetFileNamePart(part)<<','<<time<<','<<completed<<','<<step<<','<<Dt<<','<<er<<','<<empty<<'\n';history<<part<<','<<time<<','<<Total<<",0,"<<speed<<','<<rmin<<','<<rmax<<'\n';
  }
  Need(previous==Steps&&intervals==samples-1&&checks==Total*samples,"Fluid four-update coverage incomplete");for(auto* f:{&raw,&clock,&history,&layout}){f->flush();Need(bool(*f),"Fluid export failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_material_release_native_r1_fluid\",\"passed\":true,\"input_run_tag\":\""<<tag<<"\",\"samples\":"<<samples<<",\"completed_steps\":4,\"actual_end_s\":"<<double(scalar)<<",\"native_IDs\":1024,\"typed_subset_arrays\":7,\"typed_subset_bytes_per_ID\":96,\"native_finite_zero_kappa_checks\":"<<checks<<",\"all_original_IDs_present\":true,\"soil_version_metadata_absent\":true,\"actual_scalar_clock_verified\":true,\"max_scalar_clock_error_s\":"<<maxClock<<",\"max_noninitial_signed_dterror_s\":"<<maxError<<",\"full_22_array_schema_claimed\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Fluid completion failed");
}
}
int main(int argc,char** argv){try{
  Need(argc==7&&std::string(argv[1])=="--read"&&(std::string(argv[3])=="CPU"||std::string(argv[3])=="GPU"),"Use --read source|alias0|receive_old|receive_new|plastic|fluid CPU|GPU DATA PRE|- FRESHOUT");
  const std::string mode=argv[2];if(mode=="plastic"){Need(std::string(argv[5])=="-","Plastic has no PRE");releaseplastic::Read(argv[3],argv[4],argv[6]);}
  else if(mode=="fluid"){Need(std::string(argv[5])=="-","Fluid has no PRE");releasefluid::Read(argv[3],argv[4],argv[6]);}
  else c08releasegravity::Read(mode,argv[3],argv[4],argv[5],argv[6]);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Unified native review rejected; preserve partial output\n";return 2;}}
