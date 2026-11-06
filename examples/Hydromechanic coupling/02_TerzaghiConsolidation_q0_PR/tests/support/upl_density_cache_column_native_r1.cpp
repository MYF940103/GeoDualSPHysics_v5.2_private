// Pure offline 128-update column reader. Retained hardcoded readers are never invoked.
#define main RetainedPublicNativeMain
#include "upl_cpu_public_native_r1.cpp"
#undef main
namespace columncache {
constexpr unsigned Soil=1000,Fixed=40,Total=1040,Steps=128,DrainStep=1600;
constexpr double Dt=6.2501430511474609e-6,Dp=.01,Rho=2100.,Water=1000.;
static const double Por=double(float(.3)),Conductivity=double(float(.0001)),Mass=double(float(.21));
static bool Bits(double a,double b){return !std::memcmp(&a,&b,8);}
static std::vector<std::string> Split(std::string line,char delimiter){
  if(!line.empty()&&line.back()=='\r')line.pop_back();std::vector<std::string> out;std::size_t begin=0;
  for(;;){const auto p=line.find(delimiter,begin);out.push_back(line.substr(begin,p==std::string::npos?p:p-begin));if(p==std::string::npos)break;begin=p+1;}return out;
}
static std::map<std::string,std::string> RunCsv(const fs::path& file){
  std::ifstream f(file);std::string h,d,extra;Need(bool(std::getline(f,h))&&bool(std::getline(f,d))&&!std::getline(f,extra),"Require the actual two-line Run.csv");
  const char sep=h.find(';')==std::string::npos?',':';';const auto a=Split(h,sep),b=Split(d,sep);Need(a.size()==b.size(),"Run.csv width differs");std::map<std::string,std::string> r;
  for(unsigned i=0;i<a.size();i++)Need(r.emplace(a[i],b[i]).second,"Repeated Run.csv column");
  Need(r.at("Steps")=="128"&&r.at("Np")=="1040"&&r.at("Nbound")=="40"&&r.at("Nfixed")=="40"&&r.at("PartsOut")=="0"&&r.at("PartsOutRhop")=="0"&&r.at("PartsOutVel")=="0","Actual run step/ID/exclusion summary differs");return r;
}
static unsigned Samples(const fs::path& dir){
  Need(fs::is_directory(dir),"Native data directory missing");unsigned n=0;
  for(const auto& p:fs::directory_iterator(dir))if(p.is_regular_file()&&p.path().filename().string().rfind("Part_",0)==0&&p.path().extension()==".bi4")n++;
  Need(n>=2&&n<=Steps+1,"Undeclared native frame count");Sequence(dir,n);return n;
}
static void Initial(const Native& a,std::vector<tdouble3>& x0,std::ofstream& ids){
  std::array<bool,Soil> soil{};std::array<bool,Fixed> fixed{};x0.resize(Total);
  for(unsigned id=0;id<Total;id++){
    const unsigned p=a.slot[id];const auto x=a.pos[p];x0[id]=x;
    const long ix=std::llround(x.x/Dp-.5),iz=std::llround(x.z/Dp-.5);
    Need(x.y==0&&ix>=0&&ix<10&&std::fabs(x.x-(double(ix)+.5)*Dp)<=64*DBL_EPSILON&&std::fabs(x.z-(double(iz)+.5)*Dp)<=64*DBL_EPSILON,"Initial decimal lattice differs");
    Need(Norm2(a.vel[p])==0&&a.rhop[p]==Rho&&a.p[p]==0&&a.p0[p]==0&&a.excess[p]==0&&Norm2(a.sk[p])==0&&Norm2(a.si[p])==0&&a.plastic[p]==0&&Norm2(a.load[p])==0&&a.j[p]==1&&a.theta[p]==0,"Initial rest/J1 state differs");
    if(id<Fixed){Need(iz>=-4&&iz<0&&a.n[p]==0,"Initial fixed geometry/marker differs");const unsigned key=unsigned(ix)*4+unsigned(iz+4);Need(!fixed[key],"Repeated fixed coordinate");fixed[key]=true;}
    else{Need(iz>=0&&iz<100&&a.n[p]==Por,"Initial soil geometry/porosity differs");const unsigned key=unsigned(ix)+10*unsigned(iz);Need(!soil[key],"Repeated soil coordinate");soil[key]=true;}
    ids<<id<<','<<(id<Fixed)<<','<<x.x<<','<<x.y<<','<<x.z<<'\n';
  }
}
static void Typed22(std::ofstream& out,const Native& a){
  Original15(out,a);
  for(const auto* v:{&a.j,&a.n,&a.theta,&a.volume,&a.rho,&a.k})WriteTyped(out,*v,a.slot);
  WriteTyped(out,a.posdiv,a.slot);
}
static void Read(const fs::path& dir,const fs::path& out){
  const fs::path tests=fs::path(__FILE__).parent_path().parent_path();Need(tests.is_absolute(),"Compile this source by its absolute path");
  bool admitted=false;
  for(const char* name:{"upl_density_cache_column_old_CPU_r1","upl_density_cache_column_new_CPU_r1"}){
    const auto wanted=tests/"outputs"/name/"data";if(fs::is_directory(wanted)&&fs::equivalent(dir,wanted))admitted=true;
  }
  Need(admitted,"Only this owned old/new column pair is admitted");Need(!fs::exists(out),"Retained native review protected");
  const auto run=RunCsv(dir.parent_path()/"Run.csv");const unsigned samples=Samples(dir);
  Need(run.at("PartFiles")==std::to_string(samples),"Run.csv and actual PART manifest disagree");
  Need(fs::create_directory(out),"Cannot create fresh native output");
  std::ofstream raw(out/"typed22.bin",std::ios::binary),clock(out/"clocks.csv"),ids(out/"native_ids.csv"),ledger(out/"ledger.csv"),history(out/"history.csv"),layout(out/"typed22_layout.csv");
  static_assert(sizeof(unsigned)==4&&sizeof(float)==4&&sizeof(double)==8&&sizeof(tfloat3)==12&&sizeof(tdouble3)==24,"Typed x64 layout differs");
  const unsigned header[]={Total,22,samples};raw.write(reinterpret_cast<const char*>(header),12);
  for(auto* f:{&clock,&ids,&ledger,&history})*f<<std::setprecision(17);
  clock<<"part,file,time_s,completed_step,saved_step,dt_s,signed_dterror_s,dterror_interval_empty,activeDrainCount\n";
  ids<<"id,is_fixed,x0,y0,z0\n";
  ledger<<"part,time_s,id,J,n_native,theta_native,V_native,rho_native,k_native,PosDiv_native,native_Rhop,V_reference,rho_reference,k_reference\n";
  history<<"part,time_s,completed_step,pressure_mean_Pa,pressure_RMS_Pa,max_material_displacement_mm,min_J,max_J,max_ledger_relative_error,saved_J_mass_weighted_LoadAce_proxy_x_N_per_m,saved_J_mass_weighted_LoadAce_proxy_y_N_per_m,saved_J_mass_weighted_LoadAce_proxy_z_N_per_m,activeDrainCount\n";
  layout<<"array,type,components,bytes_per_particle\nIdp,uint32,1,4\nPosd,float64,3,24\nVel,float32,3,12\nSigma_kk,float32,3,12\nSigma_ij,float32,3,12\nFSNormal,float32,3,12\nHydroMechLoadAce,float32,3,12\nnative_Rhop,float32,1,4\nKplastic,float32,1,4\nPorePress,float32,1,4\nPorePress0,float32,1,4\nExcessPorePress,float32,1,4\nSigmaState_kk,float64,3,24\nSigmaState_ij,float64,3,24\nFSType,uint32,1,4\nPoroVolumeRatio,float64,1,8\nPoroPorosity,float64,1,8\nPoroThetaLastStage,float64,1,8\nPoroCurrentVolume,float64,1,8\nPoroMixtureDensity,float64,1,8\nPoroHydraulicConductivity,float64,1,8\nPosDiv,float32,1,4\n";
  std::vector<tdouble3> x0;volatile double scalar=0.;unsigned completedBefore=0,intervals=0,initialEmpty=0,soilRows=0,fixedRows=0;
  double minError=DBL_MAX,maxError=-DBL_MAX,maxLedger=0.;
  for(unsigned part=0;part<samples;part++){
    JPartDataBi4 f;f.LoadFilePart(dir.string(),part,0,1);
    Need(f.GetNpiece()==1&&f.Get_Npok()==Total&&!f.Get_Nout()&&f.Get_CaseNp()==Total&&f.Get_CaseNfluid()==Soil&&f.Get_CaseNfixed()==Fixed&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat(),"Actual native ID/count/exclusion differs");
    Need(f.Get_Data2d()&&f.Get_Data2dPosY()==0&&!f.Get_Symmetry()&&!f.Get_NpDynamic()&&!f.Get_ReuseIds()&&f.Get_PeriMode()==PERI_X,"Outside native fixed 2D X-periodic scope");
    Need(f.Get_Dp()==Dp&&f.Get_H()==double(float(.018))&&f.Get_Rhop0()==Rho&&f.Get_MassFluid()==Mass&&f.Get_MassBound()==Mass,"Actual float-mass/reference geometry differs");
    const auto inc=f.Get_PeriXinc();Need(Finite(inc)&&std::fabs(std::fabs(inc.x)-.1)<=64*DBL_EPSILON*.1&&inc.y==0&&inc.z==0,"Native periodic translation differs");
    const unsigned step=f.Get_Step(),completed=part?step+1:0;
    Need((part?(completed>completedBefore&&completed<=Steps):(step==0&&f.Get_TimeStep()==0)),"Actual saved steps do not advance in the128-update window");
    for(unsigned n=completedBefore;n<completed;n++)scalar+=Dt;completedBefore=completed;
    const double time=f.Get_TimeStep();Need(Bits(time,scalar),"Native time differs from binary64 scalar +=dt replay");
    const auto* info=f.GetPart();Need(info->ExistsValue("SymplecticDtPre",DatDouble)&&Bits(info->GetvDouble("SymplecticDtPre"),Dt)&&info->ExistsValue("dterror",DatDouble),"Typed locked-dt/signed diagnostic missing");
    const double error=info->GetvDouble("dterror");const bool empty=error==-DBL_MAX;Need(std::isfinite(error),"Nonfinite signed dterror");
    if(part){Need(!empty&&error<=1e-14,"Noninitial signed necessary-step guard failed/empty");intervals++;minError=(std::min)(minError,error);maxError=(std::max)(maxError,error);}
    else{Need(empty||error<=1e-14,"Initial signed guard failed");initialEmpty+=unsigned(empty);}
    Need(f.ArraysCount()==22,"Exactly22 original typed public arrays required");Metadata(f,0);const Native a=Load(f,Total,0);
    if(!part)Initial(a,x0,ids);
    const double v0=f.Get_MassFluid()/f.Get_Rhop0();double pm=0,p2=0,umax=0,jlo=DBL_MAX,jhi=-DBL_MAX,frameLedger=0;tdouble3 proxy=TDouble3(0);
    for(unsigned id=0;id<Total;id++){
      const unsigned p=a.slot[id];const auto x=a.pos[p];const auto s=a.sk[p],q=a.si[p];
      Need(a.rhop[p]>0&&a.plastic[p]==0&&a.p0[p]==0&&a.excess[p]==float(a.p[p]-a.p0[p])&&a.fstype[p]<=4,"Positive native Rhop/elastic/p0/excess/FSType guard failed");
      Need(a.legacykk[p].x==float(s.x)&&a.legacykk[p].y==float(s.y)&&a.legacykk[p].z==float(s.z)&&a.legacyij[p].x==float(q.x)&&a.legacyij[p].y==float(q.y)&&a.legacyij[p].z==float(q.z),"Float display no longer rounds native double stress");
      double Vref=0,rhoref=0,kref=0;
      if(id<Fixed){
        Need(!std::memcmp(&x,&x0[id],sizeof(x))&&Norm2(a.vel[p])==0&&a.j[p]>1.-Por&&a.theta[p]==0&&a.n[p]==0&&a.volume[p]==0&&a.rho[p]==0&&a.k[p]==0,"Original fixed geometry/velocity/J/theta/public zero marker differs");fixedRows++;
      }else{
        const double j=a.j[p],n=1.-(1.-Por)/j;Vref=v0*j;rhoref=Water+(Rho-Water)/j;kref=Conductivity;
        Need(j>1.-Por&&n>0&&n<1&&Vref>0&&rhoref>0&&x.y==0&&x.z>0&&std::fabs((1.-a.n[p])*j-(1.-Por))<=5e-13,"Saturated J/no-bottom-crossing ledger failed");
        const double got[]={a.n[p],a.volume[p],a.rho[p],a.k[p]},ref[]={n,Vref,rhoref,kref};
        for(unsigned k=0;k<4;k++){Need(Close(got[k],ref[k]),"Actual n/V/rho/k does not match same compacted J");frameLedger=(std::max)(frameLedger,std::fabs(got[k]-ref[k])/(std::max)(std::fabs(ref[k]),DBL_MIN));}
        pm+=double(a.p[p]);p2+=double(a.p[p])*a.p[p];umax=(std::max)(umax,1000*std::sqrt(Norm2(x-x0[id])));jlo=(std::min)(jlo,j);jhi=(std::max)(jhi,j);
        proxy=proxy+ToTDouble3(a.load[p])*(a.rho[p]*a.volume[p]);soilRows++;
      }
      ledger<<part<<','<<time<<','<<id<<','<<a.j[p]<<','<<a.n[p]<<','<<a.theta[p]<<','<<a.volume[p]<<','<<a.rho[p]<<','<<a.k[p]<<','<<a.posdiv[p]<<','<<a.rhop[p]<<','<<Vref<<','<<rhoref<<','<<kref<<'\n';
    }
    Need(completed<DrainStep,"This window must precede drainage; do not assert a nonempty drain check");maxLedger=(std::max)(maxLedger,frameLedger);
    for(double value:{pm,p2,umax,jlo,jhi,frameLedger,proxy.x,proxy.y,proxy.z})Need(std::isfinite(value),"Nonfinite descriptive saved-field summary");
    raw.write(reinterpret_cast<const char*>(&time),8);Typed22(raw,a);
    clock<<part<<','<<JPartDataBi4::GetFileNamePart(part)<<','<<time<<','<<completed<<','<<step<<','<<Dt<<','<<error<<','<<empty<<",0\n";
    history<<part<<','<<time<<','<<completed<<','<<pm/Soil<<','<<std::sqrt(p2/Soil)<<','<<umax<<','<<jlo<<','<<jhi<<','<<frameLedger<<','<<proxy.x<<','<<proxy.y<<','<<proxy.z<<",0\n";
  }
  Need(completedBefore==Steps&&intervals==samples-1&&soilRows==Soil*samples&&fixedRows==Fixed*samples,"Incomplete128-step native/ledger/clock coverage");
  for(auto* f:{&raw,&clock,&ids,&ledger,&history,&layout}){f->flush();Need(bool(*f),"Offline export write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)
    <<"{\"stage\":\"upl_density_cache_column_native_r1\",\"passed\":true,\"backend_argument\":\"CPU\",\"window\":\"128_updates_pre_drain\",\"samples\":"<<samples
    <<",\"completed_steps\":128,\"last_saved_step\":127,\"actual_end_s\":"<<double(scalar)<<",\"dt_s\":"<<Dt<<",\"total_native_IDs\":1040,\"soil_IDs\":1000,\"fixed_IDs\":40,\"typed_arrays\":22,\"typed_bytes_per_particle\":212"
    <<",\"soil_ledger_rows\":"<<soilRows<<",\"fixed_marker_rows\":"<<fixedRows<<",\"max_ledger_relative_error\":"<<maxLedger<<",\"noninitial_signed_intervals\":"<<intervals<<",\"initial_empty_intervals\":"<<initialEmpty
    <<",\"min_noninitial_signed_dterror_s\":"<<minError<<",\"max_noninitial_signed_dterror_s\":"<<maxError<<",\"activeDrainCount\":0,\"drained_receiver_checks\":0,\"post_open_frames\":0"
    <<",\"actual_saved_steps_scalar_clock_verified\":true,\"all22_arrays_finite_and_ID_aligned\":true,\"no_exclusions\":true,\"native_Rhop_semantics\":\"old_continuity_or_new_J_cache_owner_identified\",\"new_cache_float_bits_checked_by_reader\":false"
    <<",\"CODE_native_array_present\":false,\"saved_load_proxy_is_force_stage_budget\":false,\"HG_run_guard_verified_by_reader\":false,\"owned_solver_exit_verified_by_reader\":false,\"physical_acceptance\":false}\n";
  done.flush();Need(bool(done),"Completion write failed");
}
}
int main(int argc,char** argv){try{
  Need(argc==5&&std::string(argv[1])=="--read"&&std::string(argv[2])=="CPU","Use --read CPU DATA FRESHOUT");
  columncache::Read(argv[3],argv[4]);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Offline128-update native read rejected; preserve partial output\n";return 2;}}
