// Unified candidate material paths only; no legacy material calls. Reuse the closed CPU link fixture.
#include "upl_material_unified_candidate_r1.h"
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
namespace g=fsoil_unified_candidate_r1;namespace fs=std::filesystem;
static void Need(bool valid,const char* text){if(!valid)throw std::runtime_error(text);}
template<class T> static bool Bits(T a,T b){return std::memcmp(&a,&b,sizeof(T))==0;}
static double NaN(){return std::numeric_limits<double>::quiet_NaN();}
struct RefInv{double I,q;};
static RefInv ReferenceInvariants(const g::Stress& s){return {s.xx+s.yy+s.zz,std::sqrt(((s.xx-s.yy)*(s.xx-s.yy)+(s.yy-s.zz)*(s.yy-s.zz)+(s.zz-s.xx)*(s.zz-s.xx))/6.+s.xy*s.xy+s.yz*s.yz+s.xz*s.xz)};}
static double RefYield(const g::Stress& s,const g::Material& m,double k,TpDPCtes fit){const auto v=ReferenceInvariants(s);const auto DP=g::UpdateDPvars(m,k,fit);return v.q+DP.DP_phi*v.I-DP.DP_kc;}
static bool FiniteState(const g::State& x){return g::Finite(x.stress)&&g::Finite(x.kappa)&&x.kappa>=0.f;}
static const char* Name(g::Status s){switch(s){case g::Status::Invalid:return "Invalid";case g::Status::Elastic:return "Elastic";case g::Status::Smooth:return "Smooth";case g::Status::Apex:return "Apex";case g::Status::TensionRepair:return "TensionRepair";case g::Status::NoAdmissibleFlow:return "NoAdmissibleFlow";case g::Status::NonConverged:return "NonConverged";default:return "UnresolvedPath";}}
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
    Need(r.method=="candidate_general","Only the unchanged candidate subset is admitted");
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
  const auto a=g::ConsRelationEPsft(trial,r.m,r.fit);
  Update u{};u.state=a.state;u.status=Name(a.status);u.accepted=g::CommitAllowed(a.status);
  u.continuous_known=u.lambda_known=u.ftrial_known=true;u.continuous=a.kappa_continuous;
  u.lambda=a.lambda_shear;u.ftrial=a.trial_yield;u.root_residual=a.root_residual;u.root_budget=a.root_budget;
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
    csv<<"model,method,N,step,segment,delta_diag,fit,K,G,phi_p,phi_r,n_p,coh_p,coh_r,n_c,psi0,sf,initial_I,initial_q,status,advanced,path_valid,old_kappa,saved_kappa,continuous_known,local_continuous_kappa,lambda_known,delta_lambda,solver_ftrial_known,solver_ftrial_Pa,reference_ftrial_Pa,root_residual_Pa,root_budget_Pa,old_xx,old_yy,old_zz,old_xy,old_yz,old_xz,trial_xx,trial_yy,trial_zz,trial_xy,trial_yz,trial_xz,new_xx,new_yy,new_zz,new_xy,new_yz,new_xz,plastic_xx,plastic_yy,plastic_zz,plastic_xy,plastic_yz,plastic_xz,plastic_dev_increment,plastic_vol_increment,plastic_dev_accumulated,plastic_vol_accumulated,strain_diag_accumulated,yield_new_saved_ref_Pa,yield_new_local_continuous_ref_Pa,strain_closure_xx,strain_closure_yy,strain_closure_zz,legacy_material_invoked\n";
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
    std::ofstream done(completion);done<<"{\"stage\":\"upl_material_unified_path_probe_r1\",\"passed\":"<<(failures==0?"true":"false")<<",\"rows\":"<<rownumber<<",\"expected_rows\":"<<rows.size()<<",\"path_groups\":"<<groups<<",\"accepted_rows\":"<<accepted<<",\"expected_smooth_failures\":"<<failures<<",\"skipped_after_failure\":"<<skipped<<",\"material_entry\":\"unified::ConsRelationEPsft\",\"all_updates_have_local_continuous_kappa\":true,\"legacy_material_invoked\":false,\"yield_residual_is_observation_not_early_failure_gate\":true,\"spatial_solver\":false,\"SHA_scans\":0}\n";done.flush();Need(bool(done),"Completion write failed");return failures?1:0;
  }catch(const std::exception& e){std::cerr<<"row="<<rownumber<<" : "<<e.what()<<'\n';return 1;}
}
