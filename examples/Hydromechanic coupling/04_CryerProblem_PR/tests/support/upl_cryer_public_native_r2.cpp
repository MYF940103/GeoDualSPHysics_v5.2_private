// Pure 3-D Cryer public-array decoder; never a solver or backend provenance proof.
// Only neutral typed-array/metadata/sequence helpers are reused from this fully
// read source. Its old wave/column Read, Physical, Half and main are not called.
#define main RetainedPublicArrayHelpersMain
#include "../../../02_TerzaghiConsolidation_q0_PR/tests/support/upl_cpu_public_native_r1.cpp"
#undef main
#include <sstream>

namespace cryerpublic {
constexpr unsigned Fixed=8,Soil=37173,Total=37181,Columns=26;
constexpr double Dt=1./1048576.,Drain=1./128.,Radius=.05,Dp=.0025,RhoCase=2100.,WaterCase=1000.;
const double NCase=double(float(.3)),KCase=double(float(.00001)),MassCase=double(float(.0000328125));
const unsigned Center[]={17338,17343,17769,17770,17771,17772,18412,18443,18592,18755,18756,18757,18758,19403,19460,19553,19554,19979};
const char* Fields[Columns]={"x","y","z","vx","vy","vz","PorePress","PorePress0","J","theta","sigma_xx","sigma_xy","sigma_xz","sigma_yy","sigma_yz","sigma_zz","Kplastic","FSType","FSNormal_x","FSNormal_y","FSNormal_z","ExcessPorePress","LoadAce_x","LoadAce_y","LoadAce_z","legacy_Rhop"};
struct Tick{unsigned part,completed,saved;double time,dt;};
static std::vector<std::string> Split(const std::string& line){std::vector<std::string> values;std::stringstream stream(line);std::string value;while(std::getline(stream,value,','))values.push_back(value);return values;}
static unsigned Uint(const std::string& s){Need(!s.empty()&&s.find_first_not_of("0123456789")==std::string::npos,"Noninteger clock CSV field");const auto n=std::stoul(s);Need(n<=73728,"Clock integer outside declared peak window");return unsigned(n);}
static double Number(const std::string& s){size_t end=0;const double v=std::stod(s,&end);Need(end==s.size()&&std::isfinite(v),"Nonfinite/partial clock CSV number");return v;}
static std::vector<Tick> Clocks(const fs::path& path){
  std::ifstream in(path);Need(bool(in),"Declared clock CSV missing");std::string line;std::getline(in,line);if(!line.empty()&&line.back()=='\r')line.pop_back();
  Need(line=="part,time_s,completed_step,saved_step,dt_s","Wrong five-column clock schema");std::vector<Tick> rows;
  while(std::getline(in,line)){if(!line.empty()&&line.back()=='\r')line.pop_back();const auto v=Split(line);Need(v.size()==5,"Clock row field count differs");rows.push_back({Uint(v[0]),Uint(v[2]),Uint(v[3]),Number(v[1]),Number(v[4])});}
  Need(rows.size()==2||rows.size()==69||rows.size()==577,"Only a two-frame prefix, 8704-step short or 73728-step peak window admitted");Need(rows[0].completed==0&&(rows.size()!=2||rows[1].completed>0),"Prefix must start at zero and advance");double scalar=0;unsigned previous=0;
  for(unsigned p=0;p<rows.size();p++){const auto r=rows[p];const unsigned expected=rows.size()==2?r.completed:128*p;
    Need(r.part==p&&r.completed==expected&&r.saved==(expected?expected-1:0)&&r.dt==Dt,"Declared part/completed/saved/dt differs");
    for(unsigned n=previous;n<r.completed;n++)scalar+=Dt;previous=r.completed;Need(r.time==scalar,"Clock CSV differs from scalar += dt");
  }return rows;
}
static std::array<double,Columns> Common(const Native& a,unsigned p){
  const auto x=a.pos[p],s=a.sk[p],q=a.si[p];const auto v=a.vel[p],n=a.normal[p],l=a.load[p];
  // Native SigmaState_ij ordering is xy,yz,xz. Col21 is actual ExcessPorePress.
  return {x.x,x.y,x.z,double(v.x),double(v.y),double(v.z),double(a.p[p]),double(a.p0[p]),a.j[p],a.theta[p],s.x,q.x,q.z,s.y,q.y,s.z,double(a.plastic[p]),double(a.fstype[p]),double(n.x),double(n.y),double(n.z),double(a.excess[p]),double(l.x),double(l.y),double(l.z),double(a.rhop[p])};
}
static void Header(JPartDataBi4& f,const Tick& r){
  Need(f.GetNpiece()==1&&f.Get_Npok()==Total&&f.Get_CaseNp()==Total&&f.Get_CaseNfixed()==Fixed&&f.Get_CaseNfluid()==Soil&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat()&&!f.Get_Nout(),"Cryer native count/piece/exclusion differs");
  Need(!f.Get_Data2d()&&!f.Get_Symmetry()&&!f.Get_NpDynamic()&&!f.Get_ReuseIds()&&f.Get_PeriMode()==PERI_None,"Only fixed 3-D nonperiodic Cryer admitted");
  Need(f.Get_Dp()==Dp&&f.Get_H()==double(float(.0045))&&f.Get_Rhop0()==RhoCase&&f.Get_MassFluid()==MassCase&&f.Get_MassBound()==MassCase,"Native Cryer geometry/reference mass differs");
  Need(f.Get_TimeStep()==r.time&&f.Get_Step()==r.saved,"Native actual time/zero-based saved Step differs");
  Need(f.GetPart()->ExistsValue("SymplecticDtPre",DatDouble)&&f.GetPart()->GetvDouble("SymplecticDtPre")==Dt&&f.GetPart()->ExistsValue("dterror",DatDouble),"Typed native dt/signed dterror missing");
  Need(f.ArraysCount()==22,"Exactly original15 plus six public doubles and float PosDiv required");Metadata(f,0);
}
static void Read(const std::string& backend,const fs::path& dir,const fs::path& table,const fs::path& out){
  const auto ticks=Clocks(table);Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh output directory required; retained data protected");Sequence(dir,unsigned(ticks.size()));fs::create_directory(out);
  std::ofstream common(out/"common26.bin",std::ios::binary),clock(out/"clock.bin",std::ios::binary),ids(out/"native_ids.csv"),columns(out/"columns.csv"),summary(out/"summary.csv"),center(out/"center18.csv");
  Need(common&&clock&&ids&&columns&&summary&&center,"Cannot create fresh Cryer exports");
  const unsigned h[]={Total,Columns,unsigned(ticks.size())},ch[]={unsigned(ticks.size()),28};common.write(reinterpret_cast<const char*>(h),12);clock.write(reinterpret_cast<const char*>(ch),8);
  for(auto* stream:{&ids,&columns,&summary,&center})*stream<<std::setprecision(17);
  ids<<"id,is_soil,x0,y0,z0,r0_m,initial_native_volume_m3,center18,shell_r0_ge_a_minus_2h\n";columns<<"column,name\n";for(unsigned c=0;c<Columns;c++)columns<<c<<','<<Fields[c]<<'\n';
  summary<<"part,time_s,tau_s,completed_step,saved_step,dt_s,signed_dterror_s,post_open,center_count,center_pressure_Pa,center_pressure_std_Pa,pressure_arithmetic_mean_Pa,pressure_initial_V_mean_Pa,pressure_current_V_mean_Pa,pressure_min_Pa,pressure_max_Pa,shell_inward_initial_V_mm,material_inward_initial_V_mm,material_displacement_max_mm,effective_mean_compression_initial_V_Pa,total_mean_compression_initial_V_Pa,legacy_Rhop_initial_V_mean_kg_m3,rho_native_initial_V_mean_kg_m3,rho_native_min_kg_m3,rho_native_max_kg_m3,radius_max_m,speed_max_m_s,J_min,J_initial_V_mean,J_max,n_min,n_initial_V_mean,n_max,current_native_volume_sum_m3,saved_J_mixture_mass_proxy_kg,k_min_m_s,k_max_m_s,theta_absmax_s_inv,PosDiv_absmax,FS2_count,FS3_count,surface_pressure_absmax_Pa,activeDrainCount,FSNormal_surface_nonzero_count,FSNormal_other_nonzero_count,FSNormal_norm_max,LoadAce_norm_max_m_s2,saved_J_load_proxy_inward_N,saved_J_load_proxy_net_x_N,saved_J_load_proxy_net_y_N,saved_J_load_proxy_net_z_N,saved_J_load_proxy_virial_N_m,max_ledger_relative_error\n";
  center<<"part,time_s,tau_s,completed_step,saved_step,id,x0,y0,z0,r0_m";for(const char* name:Fields)center<<','<<name;center<<",n_native,V_native_m3,rho_native_kg_m3,k_native_m_s,PosDiv_native,current_radius_m,inward_mm,total_mean_compression_Pa\n";
  std::vector<tdouble3> initial(Total);std::vector<double> r0(Total),weight(Total);double initialVolume=0,shellVolume=0,minError=DBL_MAX,maxError=-DBL_MAX,maxLedger=0,maxRadius=0;
  unsigned ledgerChecks=0,fixedChecks=0,drainChecks=0,postFrames=0,emptyInitial=0,intervals=0;
  for(const auto tick:ticks){
    JPartDataBi4 f;f.LoadFilePart(dir.string(),tick.part,0,1);Header(f,tick);const Native a=Load(f,Total,0);const double time=f.Get_TimeStep(),error=f.GetPart()->GetvDouble("dterror"),v0=f.Get_MassFluid()/f.Get_Rhop0();
    const bool empty=error==-DBL_MAX,post=time>Drain;Need(std::isfinite(error)&&error<=1e-14,"Original signed dterror guard failed");
    if(tick.part){Need(!empty,"Noninitial dterror interval empty");minError=(std::min)(minError,error);maxError=(std::max)(maxError,error);intervals++;}else emptyInitial=unsigned(empty);
    if(!tick.part){
      std::vector<unsigned> observed;
      for(unsigned id=0;id<Total;id++){const unsigned p=a.slot[id];initial[id]=a.pos[p];r0[id]=std::sqrt(Norm2(initial[id]));
        Need(Norm2(a.vel[p])==0&&a.p[p]==0&&a.p0[p]==0&&a.excess[p]==0&&Norm2(a.sk[p])==0&&Norm2(a.si[p])==0&&a.plastic[p]==0&&a.j[p]==1&&a.theta[p]==0&&Norm2(a.load[p])==0,"Fresh native initial rest/J/stress/pressure/load differs");
        const bool soil=id>=Fixed,selected=soil&&r0[id]<=.0025+1e-12,shell=soil&&r0[id]>=Radius-2*f.Get_H();
        if(soil){Need(r0[id]>0&&r0[id]<=.0525&&Close(a.volume[p],v0),"Initial native material geometry/volume invalid");weight[id]=a.volume[p];initialVolume+=weight[id];if(shell)shellVolume+=weight[id];if(selected)observed.push_back(id);}
        ids<<id<<','<<soil<<','<<initial[id].x<<','<<initial[id].y<<','<<initial[id].z<<','<<r0[id]<<','<<a.volume[p]<<','<<selected<<','<<shell<<'\n';
      }
      Need(observed==std::vector<unsigned>(std::begin(Center),std::end(Center))&&shellVolume>0&&initialVolume>0,"Fixed initial center18 IDs/shell differ from contract");
      for(unsigned id:Center)Need(std::fabs(r0[id]-.0025)<1e-15,"Contract center18 is not at initial r/a=.05");
    }
    common.write(reinterpret_cast<const char*>(&time),8);clock.write(reinterpret_cast<const char*>(&time),8);clock.write(reinterpret_cast<const char*>(&tick.saved),4);clock.write(reinterpret_cast<const char*>(&tick.dt),8);clock.write(reinterpret_cast<const char*>(&error),8);
    double ps=0,pw=0,pc=0,pmin=DBL_MAX,pmax=-DBL_MAX,shell=0,inward=0,umax=0,effective=0,total=0,legacy=0,rhobar=0,rholo=DBL_MAX,rhohi=0,rmax=0,speed=0,jlo=DBL_MAX,jhi=0,jbar=0,nlo=DBL_MAX,nhi=0,nbar=0,volume=0,mass=0,klo=DBL_MAX,khi=0,theta=0,posdiv=0,surfaceP=0,normMax=0,loadMax=0,radialProxy=0,virialProxy=0,frameLedger=0;tdouble3 netProxy=TDouble3(0);
    unsigned fs2=0,fs3=0,active=0,normalSurface=0,normalOther=0;
    for(unsigned id=0;id<Total;id++){
      const unsigned p=a.slot[id];const auto x=a.pos[p],s=a.sk[p],q=a.si[p];const auto row=Common(a,p);common.write(reinterpret_cast<const char*>(row.data()),Columns*8);
      Need(a.rhop[p]>=700&&a.rhop[p]<=3000&&a.plastic[p]==0&&a.p0[p]==0&&a.excess[p]==float(a.p[p]-a.p0[p])&&a.fstype[p]<=4,"Elastic/passive-rho/p0/float-excess/FSType guard failed");
      Need(a.legacykk[p].x==float(s.x)&&a.legacykk[p].y==float(s.y)&&a.legacykk[p].z==float(s.z)&&a.legacyij[p].x==float(q.x)&&a.legacyij[p].y==float(q.y)&&a.legacyij[p].z==float(q.z),"Legacy float stress does not display double native stress");
      if(id<Fixed){Need(!std::memcmp(&x,&initial[id],sizeof(tdouble3))&&Norm2(a.vel[p])==0&&a.j[p]==1&&a.theta[p]==0&&a.n[p]==0&&a.volume[p]==0&&a.rho[p]==0&&a.k[p]==0,"Fixed physical state/public zero markers differ");fixedChecks++;continue;}
      const double j=a.j[p],n=1.-(1.-NCase)/j,V=v0*j,rho=WaterCase+(RhoCase-WaterCase)/j,w=weight[id],r=std::sqrt(Norm2(x));
      Need(j>1.-NCase&&n>0&&n<1&&std::isfinite(V)&&V>0&&std::isfinite(rho)&&rho>0&&r>0&&r<=.0525,"Positive saturated ledger/radius safety failed");
      const double got[]={a.n[p],a.volume[p],a.rho[p],a.k[p]},ref[]={n,V,rho,KCase};
      for(unsigned c=0;c<4;c++){Need(Close(got[c],ref[c]),"Native n/V/rho/k differs from same saved J");frameLedger=(std::max)(frameLedger,std::fabs(got[c]-ref[c])/(std::max)(std::fabs(ref[c]),DBL_MIN));}
      Need(std::fabs((1.-a.n[p])*j-(1.-NCase))<=5e-13,"Solid-volume identity failed");ledgerChecks++;
      const bool surface=a.fstype[p]==2||a.fstype[p]==3;fs2+=unsigned(a.fstype[p]==2);fs3+=unsigned(a.fstype[p]==3);
      if(surface){surfaceP=(std::max)(surfaceP,std::fabs(double(a.p[p])));if(post){Need(a.p[p]==0,"Post-open actual FS2/3 pressure is not zero");active++;drainChecks++;}}
      const double nn=std::sqrt(Norm2(a.normal[p]));normMax=(std::max)(normMax,nn);if(nn>0){if(surface)normalSurface++;else normalOther++;}
      const double pval=a.p[p],u=(r0[id]-r)*1000,mean=(s.x+s.y+s.z)/3.;ps+=pval;pw+=w*pval;pc+=a.volume[p]*pval;pmin=(std::min)(pmin,pval);pmax=(std::max)(pmax,pval);
      inward+=w*u;if(r0[id]>=Radius-2*f.Get_H())shell+=w*u;umax=(std::max)(umax,1000*std::sqrt(Norm2(x-initial[id])));effective-=w*mean;total+=w*(pval-mean);legacy+=w*a.rhop[p];rhobar+=w*a.rho[p];
      rholo=(std::min)(rholo,a.rho[p]);rhohi=(std::max)(rhohi,a.rho[p]);rmax=(std::max)(rmax,r);speed=(std::max)(speed,std::sqrt(Norm2(a.vel[p])));jlo=(std::min)(jlo,j);jhi=(std::max)(jhi,j);jbar+=w*j;nlo=(std::min)(nlo,a.n[p]);nhi=(std::max)(nhi,a.n[p]);nbar+=w*a.n[p];
      volume+=a.volume[p];const double mi=a.rho[p]*a.volume[p];mass+=mi;klo=(std::min)(klo,a.k[p]);khi=(std::max)(khi,a.k[p]);theta=(std::max)(theta,std::fabs(a.theta[p]));posdiv=(std::max)(posdiv,std::fabs(double(a.posdiv[p])));loadMax=(std::max)(loadMax,std::sqrt(Norm2(a.load[p])));
      // Descriptive retained-load proxy at SAVED J. This is not the load stage's
      // actual total force and does not test its .001 conservation tolerance.
      const auto proxy=ToTDouble3(a.load[p])*mi;netProxy=netProxy+proxy;const double dot=proxy.x*x.x+proxy.y*x.y+proxy.z*x.z;radialProxy-=dot/r;virialProxy-=dot;
    }
    Need(fs2+fs3>0&&(!post||active>0),"Actual true free surface/drainage is empty");postFrames+=unsigned(post);maxLedger=(std::max)(maxLedger,frameLedger);maxRadius=(std::max)(maxRadius,rmax);
    double cp=0,variance=0;for(unsigned id:Center)cp+=a.p[a.slot[id]]/18.;for(unsigned id:Center){const double d=a.p[a.slot[id]]-cp;variance+=d*d/18.;}
    summary<<tick.part<<','<<time<<','<<time-Drain<<','<<tick.completed<<','<<tick.saved<<','<<Dt<<','<<error<<','<<post<<",18,"<<cp<<','<<std::sqrt(variance)<<','<<ps/Soil<<','<<pw/initialVolume<<','<<pc/volume<<','<<pmin<<','<<pmax<<','<<shell/shellVolume<<','<<inward/initialVolume<<','<<umax<<','<<effective/initialVolume<<','<<total/initialVolume<<','<<legacy/initialVolume<<','<<rhobar/initialVolume<<','<<rholo<<','<<rhohi<<','<<rmax<<','<<speed<<','<<jlo<<','<<jbar/initialVolume<<','<<jhi<<','<<nlo<<','<<nbar/initialVolume<<','<<nhi<<','<<volume<<','<<mass<<','<<klo<<','<<khi<<','<<theta<<','<<posdiv<<','<<fs2<<','<<fs3<<','<<surfaceP<<','<<active<<','<<normalSurface<<','<<normalOther<<','<<normMax<<','<<loadMax<<','<<radialProxy<<','<<netProxy.x<<','<<netProxy.y<<','<<netProxy.z<<','<<virialProxy<<','<<frameLedger<<'\n';
    for(unsigned id:Center){const unsigned p=a.slot[id];const auto row=Common(a,p);center<<tick.part<<','<<time<<','<<time-Drain<<','<<tick.completed<<','<<tick.saved<<','<<id<<','<<initial[id].x<<','<<initial[id].y<<','<<initial[id].z<<','<<r0[id];for(double value:row)center<<','<<value;const double r=std::sqrt(Norm2(a.pos[p]));center<<','<<a.n[p]<<','<<a.volume[p]<<','<<a.rho[p]<<','<<a.k[p]<<','<<a.posdiv[p]<<','<<r<<','<<(r0[id]-r)*1000<<','<<a.p[p]-(a.sk[p].x+a.sk[p].y+a.sk[p].z)/3.<<'\n';}
  }
  const unsigned expectedPost=unsigned(std::count_if(ticks.begin(),ticks.end(),[](const Tick& r){return r.time>Drain;}));
  Need(ledgerChecks==Soil*ticks.size()&&fixedChecks==Fixed*ticks.size()&&intervals+1==ticks.size()&&postFrames==expectedPost&&(ticks.size()!=69||postFrames==4)&&(ticks.size()!=577||postFrames==512),"Incomplete declared native/clock/drain coverage");
  for(auto* stream:{&common,&clock,&ids,&columns,&summary,&center}){stream->flush();Need(bool(*stream),"Cryer native export write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_cryer_public_native_r2\",\"passed\":true,\"declared_backend\":\""<<backend<<"\",\"backend_proven_by_reader\":false,\"window\":\""<<(ticks.size()==2?"prefix_completed_plan":(ticks.size()==69?"short_8704":"peak_73728"))<<"\",\"samples\":"<<ticks.size()<<",\"completed_steps\":"<<ticks.back().completed<<",\"actual_end_s\":"<<ticks.back().time<<",\"dt_s\":"<<Dt<<",\"ramp_s\":0.00390625,\"drainage_s\":"<<Drain<<",\"total_native_ids\":37181,\"soil_ids\":37173,\"fixed_ids\":8,\"center_material_ids\":18,\"native_typed_arrays\":22,\"common26_all_native_ids\":true,\"common26_col21_actual_ExcessPorePress\":true,\"native_auxiliary_arrays_preserved_in_raw_BI4\":true,\"soil_ledger_checks\":"<<ledgerChecks<<",\"fixed_marker_checks\":"<<fixedChecks<<",\"post_open_frames\":"<<postFrames<<",\"post_open_FS23_zero_pressure_checks\":"<<drainChecks<<",\"noninitial_signed_dterror_intervals\":"<<intervals<<",\"initial_empty_dterror\":"<<(emptyInitial?"true":"false")<<",\"min_noninitial_signed_dterror_s\":"<<minError<<",\"max_noninitial_signed_dterror_s\":"<<maxError<<",\"max_ledger_relative_error\":"<<maxLedger<<",\"max_radius_m\":"<<maxRadius<<",\"center_statistic\":\"fixed18_arithmetic_mean_at_initial_r_over_a_0.05_not_exact_origin\",\"FSNormal_finite_not_cross_backend_identity_gate\":true,\"saved_J_load_is_proxy_not_force_stage_budget\":true,\"signed_dterror_is_original_necessary_step_guard\":true,\"raw_BI4_modified\":false,\"source_or_runtime_or_owned_exit_proven_by_reader\":false,\"theory_or_cross_model_accuracy_tested\":false,\"physical_acceptance\":false}\n";
  done.flush();Need(bool(done),"Cryer native completion write failed");
}
}
int main(int argc,char** argv){try{
  Need(argc==6&&std::string(argv[1])=="--read","Use --read CPU|GPU DATA CLOCK_CSV FRESHOUT");const std::string backend=argv[2];Need(backend=="CPU"||backend=="GPU","Backend label must be CPU or GPU");cryerpublic::Read(backend,argv[3],argv[4],argv[5]);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Pure Cryer native read rejected; retain raw BI4 and partial exports\n";return 2;}}
