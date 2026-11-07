// CPU material paths only. Real legacy function is linked from the closed85 objects.
#include "upl_material_general_candidate_r1.h"
#include "FunSoilMaterial.h"
#include "JAppInfo.h"
#include <climits>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("UplMaterialPathProbe","r1","CPU material paths only");
void ConsRelationEPsft_fast(tsymatrix3d,float,float,float,float,float,float,float,float,float,TpDPCtes,float,tsymatrix3d&,float&);
namespace g=fsoil_general_candidate_r1;namespace fs=std::filesystem;
static void Need(bool valid,const char* text){if(!valid)throw std::runtime_error(text);}
template<class T> static bool Bits(T a,T b){return std::memcmp(&a,&b,sizeof(T))==0;}
static double NaN(){return std::numeric_limits<double>::quiet_NaN();}
struct RefInv{double I,q;};
static RefInv ReferenceInvariants(const g::Stress& s){return {s.xx+s.yy+s.zz,std::sqrt(((s.xx-s.yy)*(s.xx-s.yy)+(s.yy-s.zz)*(s.yy-s.zz)+(s.zz-s.xx)*(s.zz-s.xx))/6.+s.xy*s.xy+s.yz*s.yz+s.xz*s.xz)};}
static double RefYield(const g::Stress& s,const g::Material& m,double k,TpDPCtes fit){const auto v=ReferenceInvariants(s);const auto DP=g::UpdateDPvars(m,k,fit);return v.q+DP.DP_phi*v.I-DP.DP_kc;}
static bool FiniteState(const g::State& x){return g::Finite(x.stress)&&g::Finite(x.kappa)&&x.kappa>=0.f;}
static const char* Name(g::Status s){switch(s){case g::Status::Invalid:return "Invalid";case g::Status::Elastic:return "Elastic";case g::Status::Radial:return "Radial";case g::Status::ApexNeeded:return "ApexNeeded";case g::Status::NonConverged:return "NonConverged";default:return "UnresolvedPath";}}
struct Row{std::string model,method,segment;unsigned N,step;double delta,initial_I,initial_q;TpDPCtes fit;g::Material m;};
static std::vector<std::string> Split(std::string line){if(!line.empty()&&line.back()=='\r')line.pop_back();Need(line.find('"')==std::string::npos,"Quoted CSV is outside this simple input schema");std::vector<std::string> r;std::stringstream s(line);std::string item;while(std::getline(s,item,','))r.push_back(item);return r;}
static double Number(const std::string& s){std::size_t used=0;const double x=std::stod(s,&used);Need(used==s.size()&&std::isfinite(x),"Nonfinite or malformed CSV number");return x;}
static unsigned Integer(const std::string& s){Need(!s.empty()&&s[0]!='-',"Invalid unsigned CSV field");std::size_t used=0;const auto x=std::stoul(s,&used);Need(used==s.size()&&x<=UINT_MAX,"Unsigned CSV overflow");return unsigned(x);}
static std::string Key(const Row& r){return r.model+"|"+r.method+"|"+std::to_string(r.N);}
static bool SameConfig(const Row& a,const Row& b){
  const float x[]={a.m.ModulusK,a.m.ModulusG,a.m.phi_p,a.m.phi_r,a.m.n_p,a.m.coh_p,a.m.coh_r,a.m.n_c,a.m.psi0,a.m.sf};
  const float y[]={b.m.ModulusK,b.m.ModulusG,b.m.phi_p,b.m.phi_r,b.m.n_p,b.m.coh_p,b.m.coh_r,b.m.n_c,b.m.psi0,b.m.sf};
  for(unsigned i=0;i<10;i++)if(!Bits(x[i],y[i]))return false;
  return a.fit==b.fit&&Bits(a.initial_I,b.initial_I)&&Bits(a.initial_q,b.initial_q);
}
static std::vector<Row> Load(const fs::path& input){
  std::ifstream in(input);Need(bool(in),"Cannot open input CSV");std::string line;Need(bool(std::getline(in,line)),"Empty input CSV");if(line.compare(0,3,"\xef\xbb\xbf")==0)line.erase(0,3);
  Need(Split(line)==Split("model,method,N,step,segment,delta_diag,fit,K,G,phi_p,phi_r,n_p,coh_p,coh_r,n_c,psi0,sf,initial_I,initial_q"),"CSV header differs");
  std::vector<Row> rows;std::set<std::string> closed;std::string current;unsigned expected=0;
  while(std::getline(in,line)){
    Need(!line.empty(),"Empty CSV row");const auto v=Split(line);Need(v.size()==19,"CSV row must have19 fields");Row r{};
    r.model=v[0];r.method=v[1];r.N=Integer(v[2]);r.step=Integer(v[3]);r.segment=v[4];r.delta=Number(v[5]);r.fit=TpDPCtes(Integer(v[6]));
    Need(!r.model.empty()&&!r.segment.empty()&&r.N>0&&r.step>0&&g::KnownFit(r.fit),"Invalid model/resolution/step/fit");
    Need(r.method=="candidate_general"||r.method=="linearized_dev"||r.method=="legacy_actual"||r.method=="currentMR1","Unknown material method");
    r.m={float(Number(v[7])),float(Number(v[8])),float(Number(v[9])),float(Number(v[10])),float(Number(v[11])),float(Number(v[12])),float(Number(v[13])),float(Number(v[14])),float(Number(v[15])),float(Number(v[16]))};
    r.initial_I=Number(v[17]);r.initial_q=Number(v[18]);Need(r.m.ModulusK>0.f&&r.m.ModulusG>0.f&&r.initial_q>0.,"Positive moduli and initial signed q required");
    const std::string key=Key(r);if(key!=current){if(!current.empty())closed.insert(current);Need(!closed.count(key),"Input path groups must be contiguous");current=key;expected=1;}
    else{Need(SameConfig(rows.back(),r),"Material/initial state changed inside one path");expected++;}
    Need(r.step==expected,"Path step must be cumulative1..actual group rows");rows.push_back(r);
  }
  Need(!rows.empty()&&in.eof(),"Input read failed");return rows;
}
struct Update{g::State state;std::string status;bool accepted=false,continuous_known=false,lambda_known=false,ftrial_known=false;
  double continuous=NaN(),lambda=NaN(),ftrial=NaN(),root_residual=NaN(),root_budget=NaN();};
static Update Advance(const Row& r,const g::State& trial){
  Update u{};u.state=trial;const auto& m=r.m;
  if(r.method=="candidate_general"){
    const auto a=g::ConsRelationEPsft(trial,m,r.fit);u.state=a.state;u.status=Name(a.status);u.accepted=g::CommitAllowed(a.status);
    u.continuous_known=u.lambda_known=u.ftrial_known=true;u.continuous=a.kappa_continuous;u.lambda=a.lambda;u.ftrial=a.trial_yield;u.root_residual=a.root_residual;u.root_budget=a.root_budget;
  }
  else if(r.method=="linearized_dev"){
    const auto tr=ReferenceInvariants(trial.stress);const auto DP=g::UpdateDPvars(m,trial.kappa,r.fit);
    const double f=tr.q+DP.DP_phi*tr.I-DP.DP_kc;u.ftrial=f;u.ftrial_known=true;u.continuous=trial.kappa;u.continuous_known=true;u.lambda=0.;u.lambda_known=true;
    if(!g::Finite(DP)||!std::isfinite(f)){u.status="LinearInvalid";return u;}
    if(f<1e-5){u.status="Elastic";u.accepted=true;return u;}
    // Taylor expansion is at lambda0: use trial I here, returned I only in endpoint F'.
    const double denominator=m.ModulusG+9.*m.ModulusK*DP.DP_phi*DP.DP_psi-g::Updatedfdk(DP,tr.I)/std::sqrt(3.);
    if(!(std::isfinite(denominator)&&denominator>0.&&tr.q>0.)){u.status="LinearUnstable";return u;}
    const double lambda=f/denominator,scale=1.-m.ModulusG*lambda/tr.q;
    u.lambda=lambda;if(!(std::isfinite(lambda)&&lambda>=0.&&scale>=0.&&scale<=1.)){u.status="LinearOutsideRadial";return u;}
    const double I=tr.I-9.*m.ModulusK*DP.DP_psi*lambda,mean=I/3.,oldmean=tr.I/3.;const auto& s=trial.stress;
    u.state.stress={mean+scale*(s.xx-oldmean),mean+scale*(s.yy-oldmean),mean+scale*(s.zz-oldmean),scale*s.xy,scale*s.yz,scale*s.xz};
    u.continuous=double(trial.kappa)+lambda/std::sqrt(3.);u.state.kappa=float(u.continuous);u.status="LinearizedRadial";u.accepted=true;
    // Deliberately no hidden final yield projection. Next step uses this actual state.
  }
  else if(r.method=="legacy_actual"){
    const auto& s=trial.stress;const tsymatrix3d old=TSymMatrix3d(s.xx,s.xy,s.xz,s.yy,s.yz,s.zz);tsymatrix3d next{};float k=trial.kappa;
    ConsRelationEPsft_fast(old,m.ModulusK,m.ModulusG,m.phi_p,m.phi_r,m.n_p,m.coh_p,m.coh_r,m.n_c,m.psi0,r.fit,trial.kappa,next,k);
    u.state={{next.xx,next.yy,next.zz,next.xy,next.yz,next.xz},k};u.status="LegacyUnreportedFinite";u.accepted=true;
    // Real legacy interface has no sf, lambda, return status or continuous-kappa output.
  }
  else{
    if(r.fit!=DP_PS||m.n_p!=0.f){u.status="CurrentMR1Ineligible";return u;}
    const auto& s=trial.stress;const fsoil::State p={{s.xx,s.yy,s.zz,s.xy,s.yz,s.xz},trial.kappa};
    const fsoil::Material a={m.ModulusK,m.ModulusG,m.phi_p,m.coh_p,m.coh_r,m.n_c,m.psi0,m.sf};const auto x=fsoil::Return(p,a);
    u.state={{x.state.stress.xx,x.state.stress.yy,x.state.stress.zz,x.state.stress.xy,x.state.stress.yz,x.state.stress.xz},x.state.kappa};
    u.status=Name(g::Status(unsigned(x.status)));u.accepted=fsoil::CommitAllowed(x.status);u.continuous_known=u.lambda_known=u.ftrial_known=true;
    u.continuous=x.kappa_continuous;u.lambda=x.lambda;u.ftrial=x.trial_yield;u.root_residual=x.root_residual;u.root_budget=x.root_budget;
  }
  if(u.accepted&&(!FiniteState(u.state)||u.state.kappa<trial.kappa)){u.accepted=false;u.status="NonfiniteOrDecreasingHistory";}
  if(u.accepted&&!(u.state.stress.xx>u.state.stress.yy)){u.accepted=false;u.status="OutsideDeclaredPositiveSignedQ";}
  return u;
}
static g::Stress Compliance(const g::Stress& trial,const g::Stress& returned,double K,double G){
  const double x=trial.xx-returned.xx,y=trial.yy-returned.yy,z=trial.zz-returned.zz,mean=(x+y+z)/3.;
  return {(x-mean)/(2.*G)+mean/(3.*K),(y-mean)/(2.*G)+mean/(3.*K),(z-mean)/(2.*G)+mean/(3.*K),(trial.xy-returned.xy)/(2.*G),(trial.yz-returned.yz)/(2.*G),(trial.xz-returned.xz)/(2.*G)};
}
static g::Stress Sum(const g::Stress& a,const g::Stress& b){return {a.xx+b.xx,a.yy+b.yy,a.zz+b.zz,a.xy+b.xy,a.yz+b.yz,a.xz+b.xz};}
static void Put(std::ostream& out,const g::Stress& s){out<<','<<s.xx<<','<<s.yy<<','<<s.zz<<','<<s.xy<<','<<s.yz<<','<<s.xz;}
int main(int argc,char** argv){unsigned rownumber=0;
  try{
    Need(argc==5&&std::string(argv[1])=="--input"&&std::string(argv[3])=="--out","Use --input FILE --out FRESHFILE");
    const fs::path input=argv[2],out=argv[4],completion=out.parent_path()/(out.stem().string()+".completion.json");
    Need(fs::is_regular_file(input)&&!fs::exists(out)&&!fs::exists(completion)&&fs::is_directory(out.parent_path()),"Input/fresh output paths invalid");
    const auto bytes=fs::file_size(input);const auto stamp=fs::last_write_time(input);const auto rows=Load(input);
    std::ofstream csv(out);Need(bool(csv),"Cannot create fresh output CSV");csv<<std::setprecision(17);
    csv<<"model,method,N,step,segment,delta_diag,fit,K,G,phi_p,phi_r,n_p,coh_p,coh_r,n_c,psi0,sf,initial_I,initial_q,status,advanced,path_valid,old_kappa,saved_kappa,continuous_known,local_continuous_kappa,lambda_known,delta_lambda,solver_ftrial_known,solver_ftrial_Pa,reference_ftrial_Pa,root_residual_Pa,root_budget_Pa,old_xx,old_yy,old_zz,old_xy,old_yz,old_xz,trial_xx,trial_yy,trial_zz,trial_xy,trial_yz,trial_xz,new_xx,new_yy,new_zz,new_xy,new_yz,new_xz,plastic_xx,plastic_yy,plastic_zz,plastic_xy,plastic_yz,plastic_xz,plastic_dev_increment,plastic_vol_increment,plastic_dev_accumulated,plastic_vol_accumulated,strain_diag_accumulated,yield_new_saved_ref_Pa,yield_new_local_continuous_ref_Pa,strain_closure_xx,strain_closure_yy,strain_closure_zz,legacy_psi_decay_applied\n";
    std::string key;g::State state{};g::Stress initial{},plastic{};bool pathfailed=false;double strain=0.,devaccum=0.;unsigned groups=0,failures=0,skipped=0,accepted=0;
    for(const auto& r:rows){
      if(Key(r)!=key){key=Key(r);const double mean=r.initial_I/3.;initial={mean+r.initial_q,mean-r.initial_q,mean,0.,0.,0.};state={initial,0.f};plastic={};strain=devaccum=0.;pathfailed=false;groups++;}
      const g::State old=state;g::State trial=old;trial.stress.xx+=2.*r.m.ModulusG*r.delta;trial.stress.yy-=2.*r.m.ModulusG*r.delta;strain+=r.delta;
      Update result{};result.state=old;g::Stress dp={NaN(),NaN(),NaN(),NaN(),NaN(),NaN()};double dev=NaN(),vol=NaN(),yield=NaN(),cyield=NaN(),cx=NaN(),cy=NaN(),cz=NaN();
      const double ftrial=RefYield(trial.stress,r.m,old.kappa,r.fit);
      if(pathfailed){result.status="SkippedAfterFailure";skipped++;}
      else{
        result=Advance(r,trial);
        if(!result.accepted){pathfailed=true;failures++;}
        else{
          state=result.state;accepted++;dp=Compliance(trial.stress,state.stress,r.m.ModulusK,r.m.ModulusG);plastic=Sum(plastic,dp);
          const auto iv=ReferenceInvariants(dp);vol=iv.I;dev=2.*iv.q/std::sqrt(3.);devaccum+=dev;
          yield=RefYield(state.stress,r.m,state.kappa,r.fit);if(result.continuous_known)cyield=RefYield(state.stress,r.m,result.continuous,r.fit);
          const auto elastic=Compliance(state.stress,initial,r.m.ModulusK,r.m.ModulusG);cx=strain-elastic.xx-plastic.xx;cy=-strain-elastic.yy-plastic.yy;cz=-elastic.zz-plastic.zz;
        }
      }
      const auto& m=r.m;csv<<r.model<<','<<r.method<<','<<r.N<<','<<r.step<<','<<r.segment<<','<<r.delta<<','<<unsigned(r.fit)<<','<<m.ModulusK<<','<<m.ModulusG<<','<<m.phi_p<<','<<m.phi_r<<','<<m.n_p<<','<<m.coh_p<<','<<m.coh_r<<','<<m.n_c<<','<<m.psi0<<','<<m.sf<<','<<r.initial_I<<','<<r.initial_q<<','<<result.status<<','<<result.accepted<<','<<!pathfailed<<','<<old.kappa<<','<<result.state.kappa<<','<<result.continuous_known<<','<<result.continuous<<','<<result.lambda_known<<','<<result.lambda<<','<<result.ftrial_known<<','<<result.ftrial<<','<<ftrial<<','<<result.root_residual<<','<<result.root_budget;
      Put(csv,old.stress);Put(csv,trial.stress);Put(csv,result.state.stress);Put(csv,dp);
      csv<<','<<dev<<','<<vol<<','<<devaccum<<','<<(plastic.xx+plastic.yy+plastic.zz)<<','<<strain<<','<<yield<<','<<cyield<<','<<cx<<','<<cy<<','<<cz<<",0\n";rownumber++;
    }
    csv.flush();Need(bool(csv)&&rownumber==rows.size(),"CSV write/count failed");Need(fs::file_size(input)==bytes&&fs::last_write_time(input)==stamp,"Input changed during material run");
    std::ofstream done(completion);done<<"{\"stage\":\"upl_material_path_probe_r1\",\"passed\":"<<(failures==0?"true":"false")<<",\"rows\":"<<rownumber<<",\"expected_rows\":"<<rows.size()<<",\"path_groups\":"<<groups<<",\"accepted_rows\":"<<accepted<<",\"expected_smooth_failures\":"<<failures<<",\"skipped_after_failure\":"<<skipped<<",\"legacy_function\":\"ConsRelationEPsft_fast\",\"legacy_continuous_kappa_and_status_unreported\":true,\"legacy_psi_decay_applied\":false,\"yield_residual_is_observation_not_early_failure_gate\":true,\"spatial_solver\":false,\"SHA_scans\":0}\n";done.flush();Need(bool(done),"Completion write failed");return failures?1:0;
  }catch(const std::exception& e){std::cerr<<"row="<<rownumber<<" : "<<e.what()<<'\n';return 1;}
}
