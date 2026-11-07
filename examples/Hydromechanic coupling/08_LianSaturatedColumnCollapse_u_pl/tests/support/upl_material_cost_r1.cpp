// Standalone Release CPU cost/accuracy protocol: existing dev-kappa Taylor versus production endpoint.
#include "FunSoilMaterial.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <climits>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace M=fsoil;namespace fs=std::filesystem;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
template<class T>static bool Bits(T a,T b){return std::memcmp(&a,&b,sizeof(T))==0;}
struct Increment{unsigned step,segment;double delta;};
struct Path{std::string model;unsigned N;TpDPCtes fit;M::Material material;M::State initial;std::vector<Increment> increments;};
struct Update{M::State state;M::Status status;double continuous,lambda;unsigned iterations;};
using Function=Update(*)(const M::State&,const M::Material&,TpDPCtes);
__declspec(noinline) static Update Endpoint(const M::State& input,const M::Material& m,TpDPCtes fit){const auto r=M::ConsRelationEPsft(input,m,fit);return {r.state,r.status,r.kappa_continuous,r.lambda_shear,r.iterations};}
// The previously tested linearized_dev protocol: Taylor at lambda=0, trial I in
// f_kappa, old beta frozen, identical deviatoric history, no final hidden projection.
__declspec(noinline) static Update Taylor(const M::State& input,const M::Material& m,TpDPCtes fit){
  Update r{input,M::Status::Invalid,input.kappa,0.,0};
  if(!M::KnownFit(fit)||!M::Finite(input.stress)||!M::Finite(input.kappa)||input.kappa<0.f
    ||!M::Finite(m.ModulusK)||!M::Finite(m.ModulusG)||!(m.ModulusK>0.f&&m.ModulusG>0.f)
    ||!M::Finite(m.phi_p)||!M::Finite(m.phi_r)||!M::Finite(m.n_p)||!M::Finite(m.coh_p)||!M::Finite(m.coh_r)||!M::Finite(m.n_c)||!M::Finite(m.psi0)||!M::Finite(m.sf)
    ||!(m.phi_r>=0.f&&m.phi_p>=m.phi_r&&double(m.phi_p)<1.57079632679489661923)
    ||m.n_p<0.f||m.coh_r<0.f||m.coh_p<m.coh_r||m.n_c<0.f||m.sf<0.f||!(std::abs(double(m.psi0))<1.57079632679489661923))return r;
  const auto tr=M::GetInvariants(input.stress);const auto d=M::UpdateDPvars(m,input.kappa,fit);const double f=tr.q+d.DP_phi*tr.I-d.DP_kc;
  if(!M::Finite(d)||!std::isfinite(f))return r;if(f<1e-5){r.status=M::Status::Elastic;return r;}
  const double denominator=m.ModulusG+9.*m.ModulusK*d.DP_phi*d.DP_psi-M::Updatedfdk(d,tr.I)/std::sqrt(3.);
  if(!(std::isfinite(denominator)&&denominator>0.&&tr.q>0.)){r.status=M::Status::UnresolvedPath;return r;}
  const double lambda=f/denominator,scale=1.-m.ModulusG*lambda/tr.q;
  if(!(std::isfinite(lambda)&&lambda>=0.&&scale>=0.&&scale<=1.)){r.status=M::Status::NoAdmissibleFlow;return r;}
  const double I=tr.I-9.*m.ModulusK*d.DP_psi*lambda,mean=I/3.,oldmean=tr.I/3.;const auto& s=input.stress;
  r.continuous=double(input.kappa)+lambda/std::sqrt(3.);r.lambda=lambda;
  r.state={{mean+scale*(s.xx-oldmean),mean+scale*(s.yy-oldmean),mean+scale*(s.zz-oldmean),scale*s.xy,scale*s.yz,scale*s.xz},float(r.continuous)};r.status=M::Status::Smooth;return r;
}
static std::vector<std::string> Split(std::string line){if(!line.empty()&&line.back()=='\r')line.pop_back();Need(line.find('"')==std::string::npos,"Only the retained unquoted CSV schema is supported");std::stringstream stream(line);std::string s;std::vector<std::string> row;while(std::getline(stream,s,','))row.push_back(s);return row;}
static double Number(const std::string& s){std::size_t used=0;const double x=std::stod(s,&used);Need(used==s.size()&&std::isfinite(x),"Invalid finite input number");return x;}
static float Float(const std::string& s){const double x=Number(s);const float f=float(x);Need(std::isfinite(f)&&double(f)==x,"Retained material input is not the exact printed float");return f;}
static unsigned Integer(const std::string& s){Need(!s.empty()&&s[0]!='-',"Negative unsigned input");std::size_t used=0;const auto n=std::stoul(s,&used);Need(used==s.size()&&n<=UINT_MAX,"Invalid unsigned input");return unsigned(n);}
static std::array<float,10> Fields(const M::Material& m){return {m.ModulusK,m.ModulusG,m.phi_p,m.phi_r,m.n_p,m.coh_p,m.coh_r,m.n_c,m.psi0,m.sf};}
static std::vector<Path> Load(const fs::path& file){std::ifstream in(file);std::string line;Need(bool(std::getline(in,line)),"Input CSV missing");if(line.compare(0,3,"\xef\xbb\xbf")==0)line.erase(0,3);
  Need(Split(line)==Split("model,method,N,step,segment,delta_diag,fit,K,G,phi_p,phi_r,n_p,coh_p,coh_r,n_c,psi0,sf,initial_I,initial_q"),"Retained path schema changed");std::vector<Path> paths;std::set<std::string> seen;unsigned total=0,selected=0;std::string previous;
  while(std::getline(in,line)){const auto r=Split(line);Need(r.size()==19,"Retained input width differs");total++;if(r[1]!="candidate_general")continue;
    const unsigned N=Integer(r[2]),step=Integer(r[3]),segment=Integer(r[4]);const double delta=Number(r[5]),I=Number(r[17]),q=Number(r[18]);const auto fit=TpDPCtes(Integer(r[6]));Need(N>0&&M::KnownFit(fit)&&q>0.&&segment<3,"Invalid canonical path");
    const M::Material material={Float(r[7]),Float(r[8]),Float(r[9]),Float(r[10]),Float(r[11]),Float(r[12]),Float(r[13]),Float(r[14]),Float(r[15]),Float(r[16])};const M::State initial={{I/3.+q,I/3.-q,I/3.,0.,0.,0.},0.f};const std::string key=r[0]+"|"+r[2];
    if(key!=previous){Need(seen.insert(key).second,"Canonical path group repeated");paths.push_back({r[0],N,fit,material,initial,{}});previous=key;}
    auto& path=paths.back();const auto x=Fields(path.material),y=Fields(material);for(unsigned i=0;i<10;i++)Need(Bits(x[i],y[i]),"Material changed within a canonical path");
    Need(path.fit==fit&&path.N==N&&Bits(path.initial.stress.xx,initial.stress.xx)&&Bits(path.initial.stress.yy,initial.stress.yy)&&Bits(path.initial.stress.zz,initial.stress.zz)&&step==path.increments.size()+1,"Canonical path initial state/step changed");
    path.increments.push_back({step,segment,delta});selected++;
  }
  Need(in.eof()&&total==22680&&selected==7560&&paths.size()==84,"Expected retained 22680 rows, 84 canonical paths and 7560 increments");for(const auto& p:paths)Need(p.increments.size()==3*p.N,"Expected three complete load/unload segments");return paths;
}
static bool Accepted(const Update& r){return (r.status==M::Status::Elastic||r.status==M::Status::Smooth)&&M::Finite(r.state.stress)&&M::Finite(r.state.kappa)&&r.state.stress.xx>r.state.stress.yy;}
static M::State Trial(M::State state,const M::Material& m,double delta){state.stress.xx+=2.*m.ModulusG*delta;state.stress.yy-=2.*m.ModulusG*delta;return state;}
struct Common{M::State trial;M::Material material;TpDPCtes fit;};
static std::vector<Common> CommonInputs(const std::vector<Path>& paths){std::vector<Common> common;common.reserve(7560);
  for(const auto& p:paths){auto state=p.initial;for(const auto& step:p.increments){const auto trial=Trial(state,p.material,step.delta);common.push_back({trial,p.material,p.fit});const auto r=Endpoint(trial,p.material,p.fit);Need(Accepted(r),"Endpoint corpus preparation left declared smooth/elastic scope");state=r.state;}}return common;
}
static M::Stress Compliance(const M::Stress& trial,const M::Stress& state,double K,double G){const double x=trial.xx-state.xx,y=trial.yy-state.yy,z=trial.zz-state.zz,mean=(x+y+z)/3.;return {(x-mean)/(2.*G)+mean/(3.*K),(y-mean)/(2.*G)+mean/(3.*K),(z-mean)/(2.*G)+mean/(3.*K),(trial.xy-state.xy)/(2.*G),(trial.yz-state.yz)/(2.*G),(trial.xz-state.xz)/(2.*G)};}
static void Accuracy(const fs::path& out,const std::vector<Path>& paths){std::ofstream csv(out/"path_states.csv");csv<<std::setprecision(17)<<"model,method,N,step,segment,I_Pa,q_Pa,saved_kappa,local_continuous_kappa,delta_lambda,status,iterations,yield_saved_Pa,yield_continuous_Pa,plastic_dev_accumulated,plastic_vol_accumulated,closure_xx,closure_yy,closure_zz,new_xx,new_yy,new_zz,new_xy,new_yz,new_xz\n";
  const Function methods[]={Taylor,Endpoint};const char* names[]={"linearized_dev","endpoint"};unsigned rows=0;
  for(unsigned method=0;method<2;method++)for(const auto& p:paths){auto state=p.initial;M::Stress plastic{};double strain=0.,dev=0.;for(const auto& step:p.increments){const auto old=state,trial=Trial(old,p.material,step.delta);const auto r=methods[method](trial,p.material,p.fit);Need(Accepted(r)&&r.state.kappa>=old.kappa,"Accuracy path failed; no fallback or substituted method");state=r.state;
    const auto dp=Compliance(trial.stress,state.stress,p.material.ModulusK,p.material.ModulusG);plastic.xx+=dp.xx;plastic.yy+=dp.yy;plastic.zz+=dp.zz;plastic.xy+=dp.xy;plastic.yz+=dp.yz;plastic.xz+=dp.xz;const auto d=M::GetInvariants(dp);dev+=2.*d.q/std::sqrt(3.);strain+=step.delta;
    const auto elastic=Compliance(state.stress,p.initial.stress,p.material.ModulusK,p.material.ModulusG);const double cx=strain-elastic.xx-plastic.xx,cy=-strain-elastic.yy-plastic.yy,cz=-elastic.zz-plastic.zz;const double eb=2e-12+2e-10*std::abs(strain);Need((std::max)({std::abs(cx),std::abs(cy),std::abs(cz)})<=eb,"Independent strain/compliance closure failed");
    const auto v=M::GetInvariants(state.stress);const auto cs=M::UpdateDPvars(p.material,state.kappa,p.fit),cc=M::UpdateDPvars(p.material,r.continuous,p.fit);const double ys=v.q+cs.DP_phi*v.I-cs.DP_kc,yc=v.q+cc.DP_phi*v.I-cc.DP_kc;
    csv<<p.model<<','<<names[method]<<','<<p.N<<','<<step.step<<','<<step.segment<<','<<v.I<<','<<v.q<<','<<state.kappa<<','<<r.continuous<<','<<r.lambda<<','<<unsigned(r.status)<<','<<r.iterations<<','<<ys<<','<<yc<<','<<dev<<','<<plastic.xx+plastic.yy+plastic.zz<<','<<cx<<','<<cy<<','<<cz<<','<<state.stress.xx<<','<<state.stress.yy<<','<<state.stress.zz<<','<<state.stress.xy<<','<<state.stress.yz<<','<<state.stress.xz<<'\n';rows++;
  }}csv.flush();Need(bool(csv)&&rows==15120,"Accuracy output incomplete");
}
struct Stats{double checksum=0.;unsigned long long calls=0,elastic=0,smooth=0,iterations=0;};
static double Checksum(const M::State& s){return s.stress.xx+2.*s.stress.yy+3.*s.stress.zz+4.*s.stress.xy+5.*s.stress.yz+6.*s.stress.xz+1024.*s.kappa;}
static void Add(Stats& s,const Update& r){if(!Accepted(r))throw std::runtime_error("Timed method failed; failed returns are not speed samples");s.checksum+=Checksum(r.state);s.calls++;s.elastic+=r.status==M::Status::Elastic;s.smooth+=r.status==M::Status::Smooth;s.iterations+=r.iterations;}
// The volatile function pointer and noinline boundary prevent replacing repeated
// independent calls by a cached return. Both methods pay the same driver overhead.
__declspec(noinline) static Stats RunFixed(Function function,const std::vector<Common>& input,unsigned repeats){Function volatile call=function;Stats s;
  for(unsigned n=0;n<repeats;n++)for(const auto& p:input)Add(s,call(p.trial,p.material,p.fit));return s;
}
__declspec(noinline) static Stats RunPaths(Function function,const std::vector<Path>& paths,unsigned repeats){Function volatile call=function;Stats s;
  for(unsigned n=0;n<repeats;n++)for(const auto& p:paths){auto state=p.initial;for(const auto& step:p.increments){const auto r=call(Trial(state,p.material,step.delta),p.material,p.fit);Add(s,r);state=r.state;}}return s;
}
static volatile double ObservedChecksum=0.;
static double Seconds(std::chrono::steady_clock::time_point a){return std::chrono::duration<double>(std::chrono::steady_clock::now()-a).count();}
int main(int argc,char** argv){try{
  Need(argc==5&&std::string(argv[1])=="--input"&&std::string(argv[3])=="--out","Use --input RETAINED_INPUT.csv --out FRESH_DIR");const fs::path file=argv[2],out=argv[4];Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh output required");const auto paths=Load(file);const auto common=CommonInputs(paths);Need(common.size()==7560&&fs::create_directory(out),"Common corpus/fresh output failed");Accuracy(out,paths);
  const Function methods[]={Taylor,Endpoint};const char* names[]={"linearized_dev","endpoint"};std::ofstream csv(out/"timings.csv");csv<<std::setprecision(17)<<"phase,round,execution_order,method,repeats,calls,elapsed_s,ns_per_return,elastic_calls,smooth_calls,endpoint_iterations,checksum\n";unsigned batches=0;double minSeconds=1e100;std::array<unsigned,2> repetitions{};
  for(unsigned phase=0;phase<2;phase++){
    std::array<double,2> warm{};for(unsigned method=0;method<2;method++){const auto t=std::chrono::steady_clock::now();const auto s=phase?RunPaths(methods[method],paths,1):RunFixed(methods[method],common,1);warm[method]=Seconds(t);ObservedChecksum=s.checksum;Need(std::isfinite(s.checksum)&&s.calls==7560&&warm[method]>0.,"Warmup/counter failed");}
    const double faster=(std::min)(warm[0],warm[1]);const unsigned repeats=(std::max)(1u,unsigned(std::ceil(.03/faster)));Need(repeats<=10000,"Unexpected timer resolution/calibration; do not run unbounded");repetitions[phase]=repeats;std::array<Stats,2> first{};
    for(unsigned round=0;round<7;round++)for(unsigned order=0;order<2;order++){const unsigned method=(round+order)%2;const auto t=std::chrono::steady_clock::now();const auto s=phase?RunPaths(methods[method],paths,repeats):RunFixed(methods[method],common,repeats);const double seconds=Seconds(t);ObservedChecksum=s.checksum;
      Need(std::isfinite(s.checksum)&&s.calls==7560ull*repeats&&seconds>0.,"Timed result/counter failed");if(round==0)first[method]=s;else Need(Bits(s.checksum,first[method].checksum)&&s.elastic==first[method].elastic&&s.smooth==first[method].smooth&&s.iterations==first[method].iterations,"Repeated valid results changed within one method/corpus");
      csv<<(phase?"independent_paths":"fixed_common_incoming")<<','<<round<<','<<order<<','<<names[method]<<','<<repeats<<','<<s.calls<<','<<seconds<<','<<seconds*1e9/s.calls<<','<<s.elastic<<','<<s.smooth<<','<<s.iterations<<','<<s.checksum<<'\n';batches++;minSeconds=(std::min)(minSeconds,seconds);
    }
  }
  csv.flush();Need(bool(csv)&&batches==28,"Timing output incomplete");std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_material_cost_r1\",\"passed\":true,\"canonical_paths\":84,\"increments_per_method\":7560,\"accuracy_rows\":15120,\"timing_batches\":28,\"rounds_per_phase_method\":7,\"fixed_repeats\":"<<repetitions[0]<<",\"path_repeats\":"<<repetitions[1]<<",\"minimum_observed_batch_s\":"<<minSeconds<<",\"target_fast_batch_s\":0.03,\"fixed_corpus_origin\":\"endpoint-generated incoming states before timing\",\"I_O_and_compliance_outside_timer\":true,\"old_actual_sft_included\":false,\"native_material_and_kappa_float\":true,\"local_arithmetic_double\":true,\"all_timed_returns_valid_smooth_or_elastic\":true,\"spatial_solver\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
