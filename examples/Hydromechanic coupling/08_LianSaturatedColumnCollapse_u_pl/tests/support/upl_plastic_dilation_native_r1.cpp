// Offline native review of two explicit nonzero-dilation periodic plastic startups.
#define main RetainedNeutralPublicReaderMain
#include "../../../02_TerzaghiConsolidation_q0_PR/tests/support/upl_cpu_public_native_r1.cpp"
#undef main
namespace periodicplastic {
constexpr unsigned Total=1024,Rows=32,Steps=128,Samples=5;
constexpr double Dt=1./524288.,Dp=.04,Length=1.28,Rho=2072.5,Water=1000.,WaterBulk=1e9;
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
  for(const auto& kv:std::vector<std::pair<std::string,unsigned>>{{"Steps",128},{"PartFiles",5},{"Np",1024},{"Nfixed",0},{"Nbound",0},{"PartsOut",0},{"PartsOutRhop",0},{"PartsOutVel",0}})
    Need(unsigned(std::stoul(r.at(kv.first)))==kv.second,"Actual native count/exclusion differs: "+kv.first);
}
static void Typed22(std::ofstream& out,const Native& a){
  Original15(out,a);for(const auto* v:{&a.j,&a.n,&a.theta,&a.volume,&a.rho,&a.k})WriteTyped(out,*v,a.slot);WriteTyped(out,a.posdiv,a.slot);
}
static void Read(const std::string& option,const std::string& backend,const fs::path& dir,const fs::path& out){
  Need(option=="POS"||option=="NEG","Use the explicit POS or NEG material selector");const double peak=option=="POS"?5000.:7500.;
  const float psi0=float((option=="POS"?2.5:-5.)*3.1415926535897932384626433832795/180.),decay=.2f;
  const auto tests=fs::path(__FILE__).parent_path().parent_path();Need(tests.is_absolute(),"Compile this profile by absolute path");const std::string tag=(option=="POS"?"upl_plastic_dilative_":"upl_plastic_contractive_")+backend+"_r1";
  Need(fs::is_directory(dir)&&fs::equivalent(dir,tests/"outputs"/tag/"data"),"Only the declared POS/NEG periodic-dilation CPU/GPU r1 DATA is admitted");
  Need(!fs::exists(out),"Retained native output protected");RunCsv(dir.parent_path()/"Run.csv");Sequence(dir,Samples);
  const auto velocity=Velocity(tests/"support/upl_material_periodic_shear_r1_velocity.csv");
  Need(fs::create_directory(out),"Cannot create fresh native output");std::ofstream raw(out/"typed22.bin",std::ios::binary),layout(out/"typed22_layout.csv"),clock(out/"clocks.csv"),ids(out/"native_ids.csv"),ledger(out/"ledger.csv"),history(out/"history.csv");
  static_assert(sizeof(unsigned)==4&&sizeof(float)==4&&sizeof(double)==8&&sizeof(tfloat3)==12&&sizeof(tdouble3)==24,"Original typed x64 layout differs");
  const unsigned header[]={Total,22,Samples};raw.write(reinterpret_cast<const char*>(header),12);
  for(auto* f:{&clock,&ids,&ledger,&history})*f<<std::setprecision(17);
  layout<<"array,type,components,bytes_per_particle\nIdp,uint32,1,4\nPosd,float64,3,24\nVel,float32,3,12\nSigma_kk,float32,3,12\nSigma_ij,float32,3,12\nFSNormal,float32,3,12\nHydroMechLoadAce,float32,3,12\nnative_Rhop,float32,1,4\nKplastic,float32,1,4\nPorePress,float32,1,4\nPorePress0,float32,1,4\nExcessPorePress,float32,1,4\nSigmaState_kk,float64,3,24\nSigmaState_ij,float64,3,24\nFSType,uint32,1,4\nPoroVolumeRatio,float64,1,8\nPoroPorosity,float64,1,8\nPoroThetaLastStage,float64,1,8\nPoroCurrentVolume,float64,1,8\nPoroMixtureDensity,float64,1,8\nPoroHydraulicConductivity,float64,1,8\nPosDiv,float32,1,4\n";
  clock<<"part,file,time_s,completed_step,saved_step,dt_s,signed_dterror_s,dterror_interval_empty\n";
  ids<<"id,x0,y0,z0,x_lattice_index,z_velocity_row,declared_vx_float\n";
  ledger<<"part,time_s,id,J,n_native,theta_native,V_native_m2,rho_native_kg_m3,k_native_m_s,native_Rhop,V_reference_m2,rho_reference_kg_m3,k_reference_m_s,kappa_previous_float,kappa_native_float,kappa_increment_float,cohesion_from_saved_kappa_Pa,psi_radians_from_saved_kappa,effective_DP_PS_yield_Pa_descriptive\n";
  history<<"part,time_s,p_mean_Pa,p_RMS_Pa,p_min_Pa,p_max_Pa,kappa_min,kappa_max,kappa_RMS,kappa_nonzero_IDs,kappa_increased_IDs,FS0,FS1,FS2,FS3,FS4,min_J,max_J,min_n,max_n,theta_RMS_s_inv,velocity_XYZ_RMS_m_s,min_image_displacement_RMS_mm,min_image_displacement_max_mm,sigma_eff_Frobenius_RMS_Pa,total_sigma_Frobenius_RMS_Pa,max_effective_DP_PS_yield_Pa_descriptive,current_mixture_mass_kg_per_m,kinetic_J_per_m,max_reference_wave_Courant,max_Ddt_h2,cohesion_min_from_saved_kappa_Pa,cohesion_max_from_saved_kappa_Pa,psi_min_radians_from_saved_kappa,psi_max_radians_from_saved_kappa\n";
  std::vector<tdouble3> initial(Total);std::vector<float> previousKappa(Total,0.f);std::array<bool,Total> gridSeen{};std::array<unsigned,Rows> rowCounts{};
  volatile double scalar=0.;unsigned previousStep=0,intervals=0,initialEmpty=0,ledgerChecks=0,cacheChecks=0,metadataChecks=0,monotoneChecks=0,initialVelocityChecks=0,finalNonzero=0;
  double minError=DBL_MAX,maxError=-DBL_MAX,maxLedger=0,maxKappa=0,maxPlasticDecrease=0;std::array<unsigned,Samples> freeCounts{};
  const float E=20000000.f,nu=.33f,phi=float(25.*3.1415926535897932384626433832795/180.);
  const double G=double(E/(2.f*(1.f+nu))),K=double(E/(3.f*(1.f-2.f*nu))),M=K+4.*G/3.,tp=std::tan(double(phi)),den=std::sqrt(9.+12.*tp*tp),alpha=tp/den;
  for(unsigned part=0;part<Samples;part++){
    currentPart=part;currentId=~0u;JPartDataBi4 f;f.LoadFilePart(dir.string(),part,0,1);
    Need(f.GetNpiece()==1&&f.Get_Npok()==Total&&!f.Get_Nout()&&f.Get_CaseNp()==Total&&f.Get_CaseNfluid()==Total&&!f.Get_CaseNfixed()&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat(),"Native owner IDs/counts/exclusions differ");
    Need(f.Get_Data2d()&&f.Get_Data2dPosY()==0&&!f.Get_Symmetry()&&!f.Get_NpDynamic()&&!f.Get_ReuseIds()&&f.Get_PeriMode()==PERI_XZ,"Outside declared fixed-set XZ-periodic2D scope");
    Need(f.Get_Dp()==Dp&&f.Get_H()==H&&f.Get_Rhop0()==Rho&&f.Get_MassFluid()==Mass,"Actual float h/mass/reference density differs");
    const unsigned step=f.Get_Step(),completed=part?step+1:0;Need(completed==32*part&&(!part?step==0:completed<=Steps),"Actual planned saved Step differs");
    for(unsigned n=previousStep;n<completed;n++)scalar+=Dt;previousStep=completed;const double time=f.Get_TimeStep();Need(Bits(time,scalar),"Actual dyadic scalar clock differs");
    const auto* info=f.GetPart();Need(info->ExistsValue("SymplecticDtPre",DatDouble)&&Bits(info->GetvDouble("SymplecticDtPre"),Dt)&&info->ExistsValue("dterror",DatDouble),"Typed locked dt/signed diagnostic missing");
    Need(info->ExistsValue("MaterialReturn",DatUint)&&info->GetvUint("MaterialReturn")==1&&info->ExistsValue("DilationDecay",DatFloat)&&info->GetvFloat("DilationDecay")==decay,"Explicit radial material metadata differs");
    Need(!info->ExistsValue("HydroMechFreeSeepage"),"Free-seepage true-only metadata must remain absent in the periodic fixture");Metadata(f,0);metadataChecks++;
    const double error=info->GetvDouble("dterror");const bool empty=error==-DBL_MAX;Need(std::isfinite(error),"Nonfinite signed diagnostic");
    if(part){Need(!empty&&error<=1e-14,"Original noninitial signed necessary-step guard failed/empty");intervals++;minError=(std::min)(minError,error);maxError=(std::max)(maxError,error);}
    else{Need(empty||error<=1e-14,"Initial signed diagnostic failed");initialEmpty+=unsigned(empty);}
    Need(f.ArraysCount()==22,"Exactly22 public typed arrays required");const Native a=Load(f,Total,0);const double v0=f.Get_MassFluid()/f.Get_Rhop0();
    double ps=0,p2=0,pmin=DBL_MAX,pmax=-DBL_MAX,kmin=DBL_MAX,kmax=0,k2=0,jmin=DBL_MAX,jmax=-DBL_MAX,nmin=DBL_MAX,nmax=-DBL_MAX,theta2=0,v2=0,u2=0,umax=0,s2=0,total2=0,fmax=-DBL_MAX,mass=0,kinetic=0,wave=0,diff=0,cmin=DBL_MAX,cmax=0,psimin=DBL_MAX,psimax=-DBL_MAX;
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
      const double I=s.x+s.y+s.z,qeff=std::sqrt(((s.x-s.y)*(s.x-s.y)+(s.x-s.z)*(s.x-s.z)+(s.y-s.z)*(s.y-s.z))/6.+Norm2(t));
      // Descriptive saved-history strength, not the material root's continuous-history residual.
      const double cohesion=1000.+(peak-1000.)*std::exp(-5.*double(kap)),psi=double(psi0)*std::exp(-double(decay)*double(kap)),yield=qeff+alpha*I-3.*cohesion/den;cmin=(std::min)(cmin,cohesion);cmax=(std::max)(cmax,cohesion);psimin=(std::min)(psimin,psi);psimax=(std::max)(psimax,psi);
      auto u=x-initial[id];u.x-=Length*std::round(u.x/Length);u.z-=Length*std::round(u.z/Length);const double uu=Norm2(u),vv=Norm2(a.vel[q]);
      ps+=a.p[q];p2+=double(a.p[q])*a.p[q];pmin=(std::min)(pmin,double(a.p[q]));pmax=(std::max)(pmax,double(a.p[q]));kmin=(std::min)(kmin,double(kap));kmax=(std::max)(kmax,double(kap));k2+=double(kap)*kap;
      nonzero+=unsigned(kap>0);increased+=unsigned(kap>old);types[a.fstype[q]]++;jmin=(std::min)(jmin,j);jmax=(std::max)(jmax,j);nmin=(std::min)(nmin,n);nmax=(std::max)(nmax,n);theta2+=a.theta[q]*a.theta[q];v2+=vv;u2+=uu;umax=(std::max)(umax,std::sqrt(uu));
      s2+=Norm2(s)+2*Norm2(t);const auto total=s-TDouble3(a.p[q]);total2+=Norm2(total)+2*Norm2(t);fmax=(std::max)(fmax,yield);mass+=mi;kinetic+=.5*mi*vv;
      const double D=WaterBulk/n*k/(Water*9.80665),cu=std::sqrt((M+WaterBulk/n)/rho);wave=(std::max)(wave,cu*Dt/H);diff=(std::max)(diff,D*Dt/(H*H));
      ledger<<part<<','<<time<<','<<id<<','<<j<<','<<a.n[q]<<','<<a.theta[q]<<','<<a.volume[q]<<','<<a.rho[q]<<','<<a.k[q]<<','<<a.rhop[q]<<','<<V<<','<<rho<<','<<k<<','<<old<<','<<kap<<','<<float(kap-old)<<','<<cohesion<<','<<psi<<','<<yield<<'\n';previousKappa[id]=kap;
    }
    if(!part)for(unsigned n:rowCounts)Need(n==Rows,"Initial velocity row lacks32 unique native owners");
    freeCounts[part]=types[2]+types[3];maxKappa=(std::max)(maxKappa,kmax);if(part+1==Samples)finalNonzero=nonzero;
    const double values[]={ps/Total,std::sqrt(p2/Total),pmin,pmax,kmin,kmax,std::sqrt(k2/Total),jmin,jmax,nmin,nmax,std::sqrt(theta2/Total),std::sqrt(v2/Total),1000*std::sqrt(u2/Total),1000*umax,std::sqrt(s2/Total),std::sqrt(total2/Total),fmax,mass,kinetic,wave,diff};for(double v:values)Need(std::isfinite(v),"Nonfinite descriptive periodic history");
    history<<part<<','<<time;for(unsigned n=0;n<7;n++)history<<','<<values[n];history<<','<<nonzero<<','<<increased;for(unsigned n:types)history<<','<<n;for(unsigned n=7;n<22;n++)history<<','<<values[n];Need(std::isfinite(cmin)&&std::isfinite(cmax)&&std::isfinite(psimin)&&std::isfinite(psimax),"Nonfinite descriptive cohesion/dilation range");history<<','<<cmin<<','<<cmax<<','<<psimin<<','<<psimax<<'\n';
    raw.write(reinterpret_cast<const char*>(&time),8);Typed22(raw,a);clock<<part<<','<<JPartDataBi4::GetFileNamePart(part)<<','<<time<<','<<completed<<','<<step<<','<<Dt<<','<<error<<','<<empty<<'\n';
  }
  Need(previousStep==Steps&&intervals==4&&ledgerChecks==5120&&cacheChecks==5120&&metadataChecks==5&&initialVelocityChecks==1024&&monotoneChecks==4096&&finalNonzero>0,"Incomplete128-step periodic/plastic witness");
  for(auto* f:{&raw,&layout,&clock,&ids,&ledger,&history}){f->flush();Need(bool(*f),"Native export write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_plastic_dilation_native_r1\",\"input_run_tag\":\""<<tag<<"\",\"passed\":true,\"backend_argument\":\""<<backend<<"\",\"backend_proven_by_reader\":false,\"samples\":5,\"completed_steps\":128,\"actual_end_s\":"<<double(scalar)<<",\"dt_s\":"<<Dt<<",\"total_native_IDs\":1024,\"soil_IDs\":1024,\"fixed_IDs\":0,\"fixed_marker_rows\":0,\"fixed_marker_policy\":\"not applicable\",\"typed_arrays\":22,\"typed_bytes_per_particle\":212,\"ledger_checks\":"<<ledgerChecks<<",\"native_Rhop_float_cache_checks\":"<<cacheChecks<<",\"initial_velocity_bits_checks\":"<<initialVelocityChecks<<",\"noninitial_kappa_monotonic_ID_checks\":"<<monotoneChecks<<",\"final_kappa_nonzero_IDs\":"<<finalNonzero<<",\"max_kappa\":"<<maxKappa<<",\"max_kappa_decrease\":"<<maxPlasticDecrease<<",\"max_ledger_relative_error\":"<<maxLedger<<",\"noninitial_signed_intervals\":"<<intervals<<",\"initial_empty_intervals\":"<<initialEmpty<<",\"min_noninitial_signed_dterror_s\":"<<minError<<",\"max_noninitial_signed_dterror_s\":"<<maxError<<",\"FS23_counts_by_part\":["<<freeCounts[0]<<','<<freeCounts[1]<<','<<freeCounts[2]<<','<<freeCounts[3]<<','<<freeCounts[4]<<"],\"all22_arrays_finite_and_ID_aligned\":true,\"actual_scalar_clock_verified\":true,\"later_pressure_J_theta_forced_zero\":false,\"yield_and_wave_diagnostics_are_descriptive\":true,\"material_selector\":\""<<option<<"\",\"initial_dilation_radians_float\":"<<psi0<<",\"dilation_decay_float\":"<<decay<<",\"cohesion_peak_Pa\":"<<peak<<",\"cohesion_residual_Pa\":1000,\"cohesion_decay\":5,\"cohesion_uses_saved_float_kappa_descriptively\":true,\"energy_or_water_mass_gate_applied\":false,\"half_or_cross_backend_error_gate\":false,\"physical_acceptance\":false}\n";
  done.flush();Need(bool(done),"Completion write failed");
}
}
int main(int argc,char** argv){try{
  Need(argc==6&&std::string(argv[1])=="--read"&&(std::string(argv[3])=="CPU"||std::string(argv[3])=="GPU"),"Use --read POS|NEG CPU|GPU DATA FRESHOUT");periodicplastic::Read(argv[2],argv[3],argv[4],argv[5]);return 0;
}catch(const std::exception& e){std::cerr<<"part="<<periodicplastic::currentPart<<" id="<<periodicplastic::currentId<<" : "<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Periodic plastic native review rejected; preserve output\n";return 2;}}
