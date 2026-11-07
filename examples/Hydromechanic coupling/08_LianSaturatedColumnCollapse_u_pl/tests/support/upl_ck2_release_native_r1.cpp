// C08 Ck2 ON800 release-only profile: actual phase sizes, original IDs, no solver.
#define main RetainedNeutralPublicReaderMain
#include "../../../02_TerzaghiConsolidation_q0_PR/tests/support/upl_cpu_public_native_r1.cpp"
#undef main
namespace c08ck2release {
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
static void Read(const std::string& window,const std::string& backend,const fs::path& dir,const fs::path& out){
  const Window w=Scope(window);const bool enabled=window=="on";const std::string tag="upl_ck2_release_short_"+backend+"_r1";
  const auto tests=fs::path(__FILE__).parent_path().parent_path();Need(tests.is_absolute(),"Compile profile by absolute source path");Need(fs::is_directory(dir)&&fs::equivalent(dir,tests/"outputs"/tag/"data"),"Only exact declared Ck2 short CPU/GPU run DATA is admitted");Need(!fs::exists(out),"Retained reader output protected");
  const auto run=RunCsv(dir.parent_path()/"Run.csv",w);const unsigned Steps=unsigned(std::stoul(run.at("Steps"))),Samples=unsigned(std::stoul(run.at("PartFiles")));Sequence(dir,Samples);
  std::vector<unsigned> phases(Samples),completedSaved(Samples);std::vector<double> times(Samples);std::array<unsigned,2> counts{};bool preSeen=false,postSeen=false;double preTime=0.;unsigned prePart=~0u;
  // Actual small metadata pass precedes every phase header; no padding/rewrites or assumed21 frames.
  for(unsigned part=0;part<Samples;part++){
    JPartDataBi4 f;f.LoadFilePart(dir.string(),part,0,1);const unsigned completed=part?f.Get_Step()+1:0,phase=Phase(f,enabled,preSeen,preTime);const double time=f.Get_TimeStep();
    Need(f.GetNpiece()==1&&f.Get_Npok()==Total-phase*RetireCount&&!f.Get_Nout()&&f.Get_CaseNp()==Total&&f.Get_CaseNfluid()==Soil&&f.Get_CaseNfixed()==Fixed&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat(),"Actual phase size/original registry/unplanned exclusions differ");
    Need(phase==0?!postSeen:true,"Actual native release phase reverted");if(enabled){Need(phase?(completed>EventStep):(completed<=EventStep),"Saved phase disagrees with actual completed step");if(completed==EventStep){Need(!phase&&!preSeen,"Duplicate/invalid forced pre-event save");preSeen=true;preTime=time;prePart=part;}if(phase)postSeen=true;}
    phases[part]=phase;completedSaved[part]=completed;times[part]=time;counts[phase]++;
  }
  Need(counts[0]>0&&(enabled?(preSeen&&postSeen&&counts[1]>0):counts[1]==0),"Missing genuine pre/post phase witness");
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
    currentPart=part;currentId=~0u;JPartDataBi4 f;f.LoadFilePart(dir.string(),part,0,1);const unsigned phase=Phase(f,enabled,preSeen,preTime),n=Total-phase*RetireCount,step=f.Get_Step(),completed=part?step+1:0;
    Need(phase==phases[part]&&completed==completedSaved[part]&&Bits(f.Get_TimeStep(),times[part])&&f.Get_Npok()==n,"Raw phase metadata changed between counting and export");
    Need(f.Get_Data2d()&&f.Get_Data2dPosY()==0&&!f.Get_Symmetry()&&!f.Get_NpDynamic()&&!f.Get_ReuseIds()&&f.Get_PeriMode()==PERI_None,"Outside fresh static nonperiodic C08 scope");
    Need(f.Get_Dp()==Dp&&f.Get_H()==H&&f.Get_Rhop0()==Rho&&f.Get_MassFluid()==Mass&&f.Get_MassBound()==Mass,"Actual original geometry/material differs");
    Need(!part?step==0:(completed>previous&&completed<=Steps),"Native saved Step is not its actual strictly increasing zero-based count");for(unsigned k=previous;k<completed;k++)scalar+=Dt;previous=completed;lastSaved=step;const double time=f.Get_TimeStep(),clockError=std::fabs(time-double(scalar));Need(std::isfinite(time)&&clockError<=1e-14,"Actual scalar+=dt clock differs");maxClockError=(std::max)(maxClockError,clockError);
    const auto* info=f.GetPart();Need(info->ExistsValue("SymplecticDtPre",DatDouble)&&Bits(info->GetvDouble("SymplecticDtPre"),Dt)&&info->ExistsValue("dterror",DatDouble),"Typed locked dt/signed diagnostic missing");
    const double error=info->GetvDouble("dterror");const bool empty=error==-DBL_MAX;Need(std::isfinite(error),"Nonfinite signed diagnostic");if(part){Need(!empty&&error<=1e-14,"Original noninitial signed necessary-step guard failed/empty");intervals++;minError=(std::min)(minError,error);maxError=(std::max)(maxError,error);}else{Need(empty||error<=1e-14,"Initial signed diagnostic failed");initialEmpty+=unsigned(empty);}
    Need(info->ExistsValue("HydroMechFreeSeepage",DatBool)&&info->GetvBool("HydroMechFreeSeepage")&&info->ExistsValue("MaterialReturn",DatUint)&&info->GetvUint("MaterialReturn")==1&&info->ExistsValue("DilationDecay",DatFloat)&&info->GetvFloat("DilationDecay")==0.f,"Actual free-seepage/material metadata differs");
    Need(f.ArraysCount()==22,"Exactly22 public typed arrays required");MetadataCk2(f);conductivityMetadataChecks++;const Sample sample=LoadActual(f,phase);const Native& a=sample.a;Summary bands[5];const double v0=f.Get_MassFluid()/f.Get_Rhop0();
    for(unsigned id=0;id<Total;id++){
      if(phase&&Retired(id))continue;currentId=id;const unsigned q=sample.byid[id];const auto x=a.pos[q],s=a.sk[q],t=a.si[q];currentJ=a.j[q];currentRhop=a.rhop[q];currentP=a.p[q];
      Need(a.rhop[q]>=700.f&&a.rhop[q]<=3000.f&&a.plastic[q]>=0&&Bits(a.p0[q],initialP0[id])&&a.excess[q]==float(a.p[q]-a.p0[q])&&a.fstype[q]<=4&&Norm2(a.load[q])==0&&x.y==0,"Original density/nonnegative history/p0/excess/FSType/no-load/2D guard failed");
      Need(a.legacykk[q].x==float(s.x)&&a.legacykk[q].y==float(s.y)&&a.legacykk[q].z==float(s.z)&&a.legacyij[q].x==float(t.x)&&a.legacyij[q].y==float(t.y)&&a.legacyij[q].z==float(t.z),"Float display does not round native double stress");p0Checks++;
      if(!part)Need(!std::memcmp(&x,&x0[id],sizeof(x))&&a.plastic[q]==0&&Norm2(s)==0&&Norm2(t)==0,"Initial native geometry/kappa/zero effective stress differs");
      if(id<Fixed){Need(a.plastic[q]==0&&!std::memcmp(&x,&x0[id],sizeof(x))&&Norm2(a.vel[q])==0&&a.j[q]>1.-Por&&a.theta[q]==0&&a.n[q]==0&&a.volume[q]==0&&a.rho[q]==0&&a.k[q]==0,"Original retained fixed geometry/velocity/J/theta/zero marker differs");fixedChecks++;}
      else{
        Need(a.plastic[q]>=previousKappa[id],"Soil kappa decreased by original native ID");if(part)monotoneChecks++;previousKappa[id]=a.plastic[q];maxKappa=(std::max)(maxKappa,double(a.plastic[q]));if(part+1==Samples)finalNonzeroKappa+=unsigned(a.plastic[q]>0);
        if(a.fstype[q]==2||a.fstype[q]==3){Need(a.p[q]<=0,"Actual native free-surface soil pressure is positive");fsChecks++;freeCounts[part]++;}
        const double j=a.j[q],pn=1.-(1.-Por)/j,V=v0*j,rho=Water+(Rho-Water)/j,k=(j==1.?K0Case:K0Case*std::exp((j-1.)/((1.-Por)*CkCase)));Need(j>1.-Por&&pn>0&&pn<1&&V>0&&rho>0&&std::fabs((1.-a.n[q])*j-(1.-Por))<=5e-13,"Original single-J solid-volume ledger failed");
        Need(std::isfinite(k)&&k>0&&a.k[q]>0,"Actual/reference Ck2 conductivity is not finite positive");if(j==1.){Need(Bits(a.k[q],K0Case),"J1 conductivity is not exact original float k0");j1ExactK0Checks++;}conductivityChecks++;minConductivity=(std::min)(minConductivity,a.k[q]);maxConductivity=(std::max)(maxConductivity,a.k[q]);
        const double got[]={a.n[q],a.volume[q],a.rho[q],a.k[q]},ref[]={pn,V,rho,k};for(unsigned z=0;z<4;z++){Need(Close(got[z],ref[z]),"Native n/V/rho/k differs from actual J");maxLedger=(std::max)(maxLedger,std::fabs(got[z]-ref[z])/(std::max)(std::fabs(ref[z]),DBL_MIN));}
        Need(Bits(a.rhop[q],float(rho)),"Native float density cache differs from actual saved J");cacheChecks++;soilChecks++;
        if(!part){const bool sf=a.fstype[q]==2||a.fstype[q]==3;const float p=sf&&initialP0[id]>0.f?0.f:initialP0[id];Need(a.j[q]==1&&a.n[q]==Por&&a.theta[q]==0&&a.rhop[q]==Rho&&Norm2(a.vel[q])==0&&Bits(a.p[q],p),"Initial J1/rest/static p0 and true-FS projection differ");}
        bands[0].add(a,q,x0[id]);if(x0[id].z>=zmax-2*H)bands[1].add(a,q,x0[id]);if(x0[id].z<=zmin+2*H)bands[2].add(a,q,x0[id]);if(x0[id].x<=xmin+2*H)bands[3].add(a,q,x0[id]);if(x0[id].x>=xmax-2*H)bands[4].add(a,q,x0[id]);
      }
    }
    Need(freeCounts[part]>0,"Actual saved free-seepage mask empty");raw[phase].write(reinterpret_cast<const char*>(&time),8);Typed22(raw[phase],a);clock<<part<<','<<JPartDataBi4::GetFileNamePart(part)<<','<<time<<','<<completed<<','<<step<<','<<Dt<<','<<error<<','<<empty<<','<<phase<<','<<local[phase]++<<','<<n<<'\n';
    const char* names[]={"all","top_2h","bottom_2h","left_2h","right_2h"};for(unsigned z=0;z<5;z++){if(!part)bandCounts[z]=bands[z].count;Need(bands[z].count==bandCounts[z],"Initial material band IDs changed");bands[z].write(history,part,time,names[z]);}
  }
  const unsigned expectedFixed=Fixed*counts[0]+(Fixed-RetireCount)*counts[1],expectedP0=Total*counts[0]+(Total-RetireCount)*counts[1];
  Need(previous==Steps&&intervals==Samples-1&&soilChecks==Soil*Samples&&fixedChecks==expectedFixed&&p0Checks==expectedP0&&cacheChecks==Soil*Samples&&monotoneChecks==Soil*(Samples-1)&&local==counts&&conductivityChecks==Soil*Samples&&conductivityMetadataChecks==Samples,"Incomplete actual phase/ID/ledger/p0/cache/clock/Ck2 coverage");Need(std::fabs(times.back()-w.end)<=Dt+1e-14,"Actual owner-capped final time differs");
  for(auto* f:streams){f->flush();Need(bool(*f),"Phase/native export write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_ck2_release_native_r1\",\"input_run_tag\":\""<<tag<<"\",\"passed\":true,\"backend_argument\":\""<<backend<<"\",\"backend_proven_by_reader\":false,\"window\":\""<<window<<"\",\"samples\":"<<Samples<<",\"completed_steps\":"<<previous<<",\"last_saved_step\":"<<lastSaved<<",\"actual_end_s\":"<<times.back()<<",\"scalar_reference_end_s\":"<<double(scalar)<<",\"dt_s\":"<<Dt<<",\"declared_output_interval_s\":"<<w.output<<",\"phase_saved_frames\":["<<counts[0]<<','<<counts[1]<<"],\"phase0_native_IDs\":7060,\"phase1_native_IDs\":6800,\"phase1_export_written\":"<<(counts[1]?"true":"false")<<",\"original_case_ID_domain\":7060,\"soil_IDs\":5000,\"original_fixed_IDs\":2060,\"typed_arrays\":22,\"typed_bytes_per_particle\":212,\"max_scalar_clock_error_s\":"<<maxClockError;
  if(enabled)done<<",\"genuine_pre_event_part\":"<<prePart<<",\"genuine_pre_event_time_s\":"<<preTime<<",\"event_completed_step\":"<<EventStep<<",\"retired_native_begin\":1800,\"retired_native_count\":260";
  done<<",\"soil_ledger_checks\":"<<soilChecks<<",\"fixed_marker_checks\":"<<fixedChecks<<",\"all_present_ID_p0_float_bits_checks\":"<<p0Checks<<",\"soil_cache_float_bits_checks\":"<<cacheChecks<<",\"soil_noninitial_kappa_monotonic_checks\":"<<monotoneChecks<<",\"max_ledger_relative_error\":"<<maxLedger<<",\"max_kappa\":"<<maxKappa<<",\"final_kappa_nonzero_IDs\":"<<finalNonzeroKappa<<",\"saved_FS23_soil_checks\":"<<fsChecks<<",\"saved_FS23_soil_checks_by_part\":[";for(unsigned p=0;p<Samples;p++)done<<(p?",":"")<<freeCounts[p];
  done<<"],\"HydroMechConductivityModel\":1,\"HydroMechConductivityCk\":2,\"conductivity_model_metadata_checks\":"<<conductivityMetadataChecks<<",\"soil_conductivity_J_law_checks\":"<<conductivityChecks<<",\"soil_J1_exact_k0_checks\":"<<j1ExactK0Checks<<",\"soil_conductivity_min_m_s\":"<<minConductivity<<",\"soil_conductivity_max_m_s\":"<<maxConductivity<<",\"noninitial_signed_intervals\":"<<intervals<<",\"initial_empty_intervals\":"<<initialEmpty<<",\"min_noninitial_signed_dterror_s\":"<<minError<<",\"max_noninitial_signed_dterror_s\":"<<maxError<<",\"all22_arrays_finite_and_original_ID_aligned\":true,\"actual_scalar_clock_verified\":true,\"actual_metadata_counted_before_export_headers\":true,\"original_case_registry_unchanged\":true,\"only_declared_fixed_ID_retirement_allowed\":true,\"unplanned_or_fluid_exclusions\":0,\"OFF_metadata_absence_checked\":"<<(enabled?"false":"true")<<",\"native_saved_steps_or_arrays_rewritten\":false,\"initial_effective_stress_zero\":true,\"p0_fixed_initial_material_baseline\":true,\"saved_FS23_soil_pressure_nonpositive\":true,\"same_backend_prefix_0ULP_proven_by_reader\":false,\"CODE_or_total_Ace_or_wall_reaction_native_array_present\":false,\"restart_or_material_force_or_physical_acceptance_claimed\":false,\"owned_solver_exit_verified_by_reader\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
}
}
int main(int argc,char** argv){try{
  Need(argc==6&&std::string(argv[1])=="--read"&&(std::string(argv[3])=="CPU"||std::string(argv[3])=="GPU"),"Use --read on CPU|GPU DATA FRESHOUT");c08ck2release::Read(argv[2],argv[3],argv[4],argv[5]);return 0;
}catch(const std::exception& e){std::cerr<<"part="<<c08ck2release::currentPart<<" id="<<c08ck2release::currentId;if(c08ck2release::currentId<c08ck2release::Total)std::cerr<<" J="<<c08ck2release::currentJ<<" native_Rhop="<<c08ck2release::currentRhop<<" p="<<c08ck2release::currentP;std::cerr<<" : "<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Ck2 release native review rejected; preserve partial output\n";return 2;}}
