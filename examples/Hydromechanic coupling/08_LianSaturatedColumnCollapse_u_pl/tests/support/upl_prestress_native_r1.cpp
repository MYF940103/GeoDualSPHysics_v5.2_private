// Decimal-time C08 prestress native profile; actual saves, no solver or equilibrium claim.
#define main RetainedNeutralPublicReaderMain
#include "../../../02_TerzaghiConsolidation_q0_PR/tests/support/upl_cpu_public_native_r1.cpp"
#undef main
namespace c08free {
constexpr unsigned Soil=5000,Fixed=2060,Total=7060;
struct Window{unsigned steps;double end,output;};
static Window Scope(const std::string& name){Need(name=="check"||name=="check_release"||name=="extended","Use check, check_release or extended window");return(name=="extended"?Window{2000000,5.,.01}:Window{400,.001,.0001});}
constexpr double Dt=.0000025,Dp=.04,Rho=2072.5,Water=1000.,Surface=2.;
static const double Por=double(float(.35)),Mass=double(float(3.316)),K0Case=double(float(.0002)),H=double(float(.048));
static unsigned currentPart=~0u,currentId=~0u;static double currentJ=0,currentRhop=0,currentP=0;
static bool Bits(double a,double b){return !std::memcmp(&a,&b,8);}
static bool Bits(float a,float b){return !std::memcmp(&a,&b,4);}
static std::vector<std::string> Tokens(std::string line,char sep){
  if(!line.empty()&&line.back()=='\r')line.pop_back();std::vector<std::string> v;std::size_t b=0;
  for(;;){const auto p=line.find(sep,b);v.push_back(line.substr(b,p==std::string::npos?p:p-b));if(p==std::string::npos)break;b=p+1;}return v;
}
static std::map<std::string,std::string> RunCsv(const fs::path& p,const Window& w){
  std::ifstream f(p);std::string h,d,x;Need(bool(std::getline(f,h))&&bool(std::getline(f,d))&&!std::getline(f,x),"Actual completed two-line Run.csv required");
  const char sep=h.find(';')==std::string::npos?',':';';const auto a=Tokens(h,sep),b=Tokens(d,sep);Need(a.size()==b.size(),"Run.csv width differs");std::map<std::string,std::string> r;
  for(unsigned n=0;n<a.size();n++)Need(r.emplace(a[n],b[n]).second,"Repeated Run.csv key");
  const unsigned steps=unsigned(std::stoul(r.at("Steps"))),samples=unsigned(std::stoul(r.at("PartFiles")));
  Need(steps>=w.steps&&steps<=w.steps+1&&samples>=2&&r.at("Np")=="7060"&&r.at("Nfixed")=="2060"&&r.at("Nbound")=="2060"&&r.at("PartsOut")=="0"&&r.at("PartsOutRhop")=="0"&&r.at("PartsOutVel")=="0","Actual completed prestress step range/ID/no-exclusion summary differs");return r;
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
static void Read(const std::string& window,const std::string& backend,const fs::path& dir,const fs::path& out){
  const Window declared=Scope(window);Need(window!="check_release"||backend=="CPU","check_release admits the declared ReleaseCPU run only");const std::string tag="upl_prestress_"+window+"_"+backend+"_r1";
  const auto tests=fs::path(__FILE__).parent_path().parent_path();Need(tests.is_absolute(),"Compile this source by absolute path");
  Need(fs::is_directory(dir)&&fs::equivalent(dir,tests/"outputs"/tag/"data"),"Only the corresponding declared decimal prestress CPU/GPU DATA is admitted");
  Need(!fs::exists(out),"Retained reader output protected");const auto run=RunCsv(dir.parent_path()/"Run.csv",declared);
  const unsigned Steps=unsigned(std::stoul(run.at("Steps"))),Samples=unsigned(std::stoul(run.at("PartFiles")));Sequence(dir,Samples);
  const auto x0=InitialCoordinates(tests/"outputs/upl_c08_global_CPU_r1/ids.csv");
  std::vector<float> initialP0(Total);const double gamma=Water*double(float(9.81));
  for(unsigned id=0;id<Total;id++)initialP0[id]=float(gamma*(Surface-x0[id].z)); // Fixed-wall baseline stays affine above H.
  double xmin=DBL_MAX,xmax=-DBL_MAX,zmin=DBL_MAX,zmax=-DBL_MAX;
  for(unsigned id=Fixed;id<Total;id++){xmin=(std::min)(xmin,x0[id].x);xmax=(std::max)(xmax,x0[id].x);zmin=(std::min)(zmin,x0[id].z);zmax=(std::max)(zmax,x0[id].z);}
  Need(fs::create_directory(out),"Cannot create fresh native output");
  std::ofstream raw(out/"typed22.bin",std::ios::binary),layout(out/"typed22_layout.csv"),clock(out/"clocks.csv"),ids(out/"native_ids.csv"),history(out/"history.csv");
  static_assert(sizeof(unsigned)==4&&sizeof(float)==4&&sizeof(double)==8&&sizeof(tfloat3)==12&&sizeof(tdouble3)==24,"Original typed x64 layout differs");
  const unsigned header[]={Total,22,Samples};raw.write(reinterpret_cast<const char*>(header),12);
  for(auto* f:{&clock,&ids,&history})*f<<std::setprecision(17);
  layout<<"array,type,components,bytes_per_particle\nIdp,uint32,1,4\nPosd,float64,3,24\nVel,float32,3,12\nSigma_kk,float32,3,12\nSigma_ij,float32,3,12\nFSNormal,float32,3,12\nHydroMechLoadAce,float32,3,12\nnative_Rhop,float32,1,4\nKplastic,float32,1,4\nPorePress,float32,1,4\nPorePress0,float32,1,4\nExcessPorePress,float32,1,4\nSigmaState_kk,float64,3,24\nSigmaState_ij,float64,3,24\nFSType,uint32,1,4\nPoroVolumeRatio,float64,1,8\nPoroPorosity,float64,1,8\nPoroThetaLastStage,float64,1,8\nPoroCurrentVolume,float64,1,8\nPoroMixtureDensity,float64,1,8\nPoroHydraulicConductivity,float64,1,8\nPosDiv,float32,1,4\n";
  clock<<"part,file,time_s,completed_step,saved_step,dt_s,signed_dterror_s,dterror_interval_empty\n";
  ids<<"id,is_fixed,x0,y0,z0,initial_hydrostatic_p0_float_Pa\n";for(unsigned id=0;id<Total;id++)ids<<id<<','<<(id<Fixed)<<','<<x0[id].x<<','<<x0[id].y<<','<<x0[id].z<<','<<initialP0[id]<<'\n';
  history<<"part,time_s,initial_material_band,count,p_mean_Pa,p_RMS_Pa,p_min_Pa,p_max_Pa,sigma_eff_xx_mean_Pa,sigma_eff_yy_mean_Pa,sigma_eff_zz_mean_Pa,sigma_eff_xy_mean_Pa,sigma_eff_yz_mean_Pa,sigma_eff_xz_mean_Pa,sigma_eff_Frobenius_RMS_Pa,mean_dx_m,mean_dy_m,mean_dz_m,displacement_RMS_mm,max_displacement_mm,mean_vx_m_s,mean_vy_m_s,mean_vz_m_s,velocity_XYZ_RMS_m_s,theta_mean_s_inv,theta_RMS_s_inv,min_J,max_J,min_n,max_n,current_soil_mixture_mass_kg_per_m,kinetic_J_per_m,native_excess_mean_Pa,native_excess_RMS_Pa,native_excess_min_Pa,native_excess_max_Pa\n";
  volatile double scalar=0.;unsigned previous=0,lastSavedStep=0,intervals=0,initialEmpty=0,soilRows=0,fixedRows=0,cacheChecks=0,metadataChecks=0,freeSurfaceRows=0,p0Checks=0;double minError=DBL_MAX,maxError=-DBL_MAX,maxLedger=0,maxClockError=0,nativeEnd=0;std::array<unsigned,5> bandCounts{};std::vector<unsigned> freeCounts(Samples,0);
  std::vector<float> previousKappa(Total,0.f);unsigned monotoneChecks=0,finalNonzeroKappa=0;double maxKappa=0;
  for(unsigned part=0;part<Samples;part++){
    currentPart=part;currentId=~0u;JPartDataBi4 f;f.LoadFilePart(dir.string(),part,0,1);
    Need(f.GetNpiece()==1&&f.Get_Npok()==Total&&!f.Get_Nout()&&f.Get_CaseNp()==Total&&f.Get_CaseNfluid()==Soil&&f.Get_CaseNfixed()==Fixed&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat(),"Native ID/count/exclusion differs");
    Need(f.Get_Data2d()&&f.Get_Data2dPosY()==0&&!f.Get_Symmetry()&&!f.Get_NpDynamic()&&!f.Get_ReuseIds()&&f.Get_PeriMode()==PERI_None,"Outside fresh static nonperiodic C08 startup scope");
    Need(f.Get_Dp()==Dp&&f.Get_H()==H&&f.Get_Rhop0()==Rho&&f.Get_MassFluid()==Mass&&f.Get_MassBound()==Mass,"Actual float mass/h/reference material differs");
    const unsigned step=f.Get_Step(),completed=part?step+1:0;Need((!part?step==0:completed>previous&&completed<=Steps),"Native completed Step is not strictly increasing/in actual Run range");
    for(unsigned n=previous;n<completed;n++)scalar+=Dt;previous=completed;lastSavedStep=step;const double time=f.Get_TimeStep(),clockError=std::fabs(time-double(scalar));
    Need(std::isfinite(time)&&clockError<=1e-14,"Actual decimal scalar+=dt clock differs");maxClockError=(std::max)(maxClockError,clockError);nativeEnd=time;
    const auto* info=f.GetPart();Need(info->ExistsValue("SymplecticDtPre",DatDouble)&&Bits(info->GetvDouble("SymplecticDtPre"),Dt)&&info->ExistsValue("dterror",DatDouble),"Typed locked dt/signed diagnostic missing");
    Need(info->ExistsValue("HydroMechFreeSeepage",DatBool)&&info->GetvBool("HydroMechFreeSeepage"),"Free-seepage candidate metadata is not bool true");metadataChecks++;
    Need(info->ExistsValue("MaterialReturn",DatUint)&&info->GetvUint("MaterialReturn")==1
      &&info->ExistsValue("DilationDecay",DatFloat)&&info->GetvFloat("DilationDecay")==0.f,"Explicit material selector/decay typed metadata differs");
    const double error=info->GetvDouble("dterror");const bool empty=error==-DBL_MAX;Need(std::isfinite(error),"Nonfinite signed diagnostic");
    if(part){Need(!empty&&error<=1e-14,"Original noninitial signed necessary-step guard failed/empty");intervals++;minError=(std::min)(minError,error);maxError=(std::max)(maxError,error);}
    else{Need(empty||error<=1e-14,"Initial signed diagnostic failed");initialEmpty+=unsigned(empty);}
    Need(f.ArraysCount()==22,"Exactly22 public typed arrays required");Metadata(f,0);const Native a=Load(f,Total,0);Summary bands[5];const double v0=f.Get_MassFluid()/f.Get_Rhop0();
    for(unsigned id=0;id<Total;id++){
      currentId=id;const unsigned q=a.slot[id];const auto x=a.pos[q];const auto s=a.sk[q],t=a.si[q];currentJ=a.j[q];currentRhop=a.rhop[q];currentP=a.p[q];
      Need(a.rhop[q]>0&&a.plastic[q]>=0&&Bits(a.p0[q],initialP0[id])&&a.excess[q]==float(a.p[q]-a.p0[q])&&a.fstype[q]<=4&&Norm2(a.load[q])==0&&x.y==0,"Positive density/nonnegative history/p0/excess/FSType/no-prescribed-load/2D guard failed");
      Need(a.legacykk[q].x==float(s.x)&&a.legacykk[q].y==float(s.y)&&a.legacykk[q].z==float(s.z)&&a.legacyij[q].x==float(t.x)&&a.legacyij[q].y==float(t.y)&&a.legacyij[q].z==float(t.z),"Float display no longer rounds native double stress");
      p0Checks++;if(!part)Need(!std::memcmp(&x,&x0[id],sizeof(x))&&a.plastic[q]==0&&Norm2(s)==0&&Norm2(t)==0,"Initial coordinates/kappa/zero effective stress differ");
      double V=0,rho=0,k=0;
      if(id<Fixed){Need(a.plastic[q]==0&&!std::memcmp(&x,&x0[id],sizeof(x))&&Norm2(a.vel[q])==0&&a.j[q]>1.-Por&&a.theta[q]==0&&a.n[q]==0&&a.volume[q]==0&&a.rho[q]==0&&a.k[q]==0,"Original fixed geometry/velocity/J/theta/zero marker differs");fixedRows++;}
      else{
        const float kap=a.plastic[q];Need(kap>=previousKappa[id],"Saved soil kappa decreased by original ID");if(part)monotoneChecks++;if(part+1==Samples)finalNonzeroKappa+=unsigned(kap>0);maxKappa=(std::max)(maxKappa,double(kap));previousKappa[id]=kap;
        if(a.fstype[q]==2||a.fstype[q]==3){Need(a.p[q]<=0,"Saved native free-surface soil pressure is positive");freeSurfaceRows++;freeCounts[part]++;}
        const double j=a.j[q],n=1.-(1.-Por)/j;V=v0*j;rho=Water+(Rho-Water)/j;k=K0Case;
        Need(j>1.-Por&&n>0&&n<1&&V>0&&rho>0&&std::fabs((1.-a.n[q])*j-(1.-Por))<=5e-13,"Saturated single-J ledger failed");
        const double got[]={a.n[q],a.volume[q],a.rho[q],a.k[q]},ref[]={n,V,rho,k};for(unsigned z=0;z<4;z++){Need(Close(got[z],ref[z]),"Native n/V/rho/k differs from same actual J");maxLedger=(std::max)(maxLedger,std::fabs(got[z]-ref[z])/(std::max)(std::fabs(ref[z]),DBL_MIN));}
        const float cached=float(rho);Need(Bits(a.rhop[q],cached),"Native soil Rhop float cache differs from actual saved J");cacheChecks++;soilRows++;
        if(!part){const bool surface=(a.fstype[q]==2||a.fstype[q]==3);const float expected=(surface&&initialP0[id]>0.f?0.f:initialP0[id]);Need(a.j[q]==1&&a.n[q]==Por&&a.theta[q]==0&&a.rhop[q]==Rho&&Norm2(a.vel[q])==0&&Bits(a.p[q],expected),"Initial soil J1/rest or static-p0/true-FS positive-pressure projection differs");}
        bands[0].add(a,q,x0[id]);if(x0[id].z>=zmax-2*H)bands[1].add(a,q,x0[id]);if(x0[id].z<=zmin+2*H)bands[2].add(a,q,x0[id]);if(x0[id].x<=xmin+2*H)bands[3].add(a,q,x0[id]);if(x0[id].x>=xmax-2*H)bands[4].add(a,q,x0[id]);
      }
    }
    Need(freeCounts[part]>0,"Saved free-seepage surface mask is empty");
    raw.write(reinterpret_cast<const char*>(&time),8);Typed22(raw,a);clock<<part<<','<<JPartDataBi4::GetFileNamePart(part)<<','<<time<<','<<completed<<','<<step<<','<<Dt<<','<<error<<','<<empty<<'\n';
    const char* names[]={"all","top_2h","bottom_2h","left_2h","right_2h"};for(unsigned z=0;z<5;z++){if(!part)bandCounts[z]=bands[z].count;Need(bands[z].count==bandCounts[z],"Initial material band IDs changed");bands[z].write(history,part,time,names[z]);}
  }
  Need(previous==Steps&&intervals==Samples-1&&soilRows==Soil*Samples&&fixedRows==Fixed*Samples&&cacheChecks==Soil*Samples&&metadataChecks==Samples&&monotoneChecks==Soil*(Samples-1),"Incomplete actual-Run frame/ledger/history/free-metadata coverage");
  Need(p0Checks==Total*Samples&&nativeEnd>=declared.end-Dt-1e-14&&nativeEnd<=declared.end+Dt+1e-14,"Incomplete frozen p0 coverage or actual end is outside the admitted one-step window");
  for(auto* f:{&raw,&layout,&clock,&ids,&history}){f->flush();Need(bool(*f),"Native export write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_prestress_native_r1\",\"input_run_tag\":\""<<tag<<"\",\"passed\":true,\"backend_argument\":\""<<backend<<"\",\"backend_proven_by_reader\":false,\"window\":\""<<window<<"\",\"samples\":"<<Samples<<",\"completed_steps\":"<<previous<<",\"last_saved_step\":"<<lastSavedStep<<",\"actual_end_s\":"<<nativeEnd
    <<",\"scalar_reference_end_s\":"<<double(scalar)<<",\"dt_s\":"<<Dt<<",\"declared_requested_end_s\":"<<declared.end<<",\"declared_output_interval_s\":"<<declared.output<<",\"actual_Run_PartFiles_used\":true,\"framecount_or_integer_save_step_assumption\":false,\"max_scalar_clock_error_s\":"<<maxClockError<<",\"all_ID_p0_float_bits_checks\":"<<p0Checks<<",\"p0_is_fixed_initial_material_hydrostatic_baseline\":true,\"initial_effective_stress_zero\":true,\"initial_free_surface_projection_preserves_negative_excess\":true,\"large_per_ID_derived_CSV_written\":false,\"total_native_IDs\":7060,\"soil_IDs\":5000,\"fixed_IDs\":2060,\"typed_arrays\":22,\"typed_bytes_per_particle\":212,\"soil_ledger_checks\":"<<soilRows<<",\"fixed_marker_checks\":"<<fixedRows<<",\"soil_cache_float_bits_checks\":"<<cacheChecks<<",\"max_ledger_relative_error\":"<<maxLedger
    <<",\"free_seepage_candidate\":true,\"free_seepage_metadata_checks\":"<<metadataChecks<<",\"saved_FS23_soil_checks\":"<<freeSurfaceRows<<",\"saved_FS23_soil_checks_by_part\":[";
  for(unsigned part=0;part<Samples;part++)done<<(part?",":"")<<freeCounts[part];
  done<<']'
    <<",\"noninitial_signed_intervals\":"<<intervals<<",\"initial_empty_intervals\":"<<initialEmpty<<",\"min_noninitial_signed_dterror_s\":"<<minError<<",\"max_noninitial_signed_dterror_s\":"<<maxError<<",\"initial_material_band_counts\":["<<bandCounts[0]<<','<<bandCounts[1]<<','<<bandCounts[2]<<','<<bandCounts[3]<<','<<bandCounts[4]<<']'
    <<",\"soil_noninitial_kappa_monotonic_checks\":"<<monotoneChecks<<",\"max_kappa\":"<<maxKappa<<",\"final_kappa_nonzero_IDs\":"<<finalNonzeroKappa<<",\"initial_soil_and_fixed_kappa_zero_verified\":true,\"final_nonzero_kappa_required\":false"
    <<",\"all22_arrays_finite_and_ID_aligned\":true,\"actual_scalar_clock_verified\":true,\"no_exclusions\":true,\"constant_conductivity_model\":0,\"CODE_native_array_present\":false,\"total_Ace_or_wall_reaction_native_array_present\":false,\"active_wall_count_inferred\":false,\"legacy_HydroMechDrainage_declared_zero_by_owner_XML\":true,\"saved_FS23_soil_pressure_nonpositive\":true,\"pressure_data_modified_by_reader\":false,\"pore_pressure_stage_rate_zero_required\":false,\"FS_pressure_forced_zero_by_reader\":false,\"closed_normal_flux_projection_claimed\":false,\"energy_ratio_gate_applied\":false,\"water_mass_conservation_claimed\":false,\"owned_solver_exit_verified_by_reader\":false,\"physical_acceptance\":false}\n";
  done.flush();Need(bool(done),"Completion write failed");
}
}
int main(int argc,char** argv){try{
  Need(argc==6&&std::string(argv[1])=="--read"&&(std::string(argv[3])=="CPU"||std::string(argv[3])=="GPU"),"Use --read check|check_release|extended CPU|GPU DATA FRESHOUT");c08free::Read(argv[2],argv[3],argv[4],argv[5]);return 0;
}catch(const std::exception& e){std::cerr<<"part="<<c08free::currentPart<<" id="<<c08free::currentId;
  if(c08free::currentId<c08free::Total)std::cerr<<" J="<<c08free::currentJ<<" native_Rhop="<<c08free::currentRhop<<" p="<<c08free::currentP;
  std::cerr<<" : "<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"C08 decimal prestress native review rejected; preserve partial output\n";return 2;}}
