// Independent first-n GPU HG force reference; one cold Audit evaluation, no physical update.
#include "c08_h18_hg_gpu_forcecheck_r1_core.hpp"
#include <cfenv>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <chrono>
#include <xmmintrin.h>
namespace path=std::filesystem;
using C=c08gpucheck::detail::Core<true>;
static void Need(bool b,const std::string& s){if(!b)throw std::runtime_error("HG GPU forcecheck: "+s);}
static bool Bits(double a,double b){return std::memcmp(&a,&b,sizeof(double))==0;}
static void Mode(){const unsigned c=_mm_getcsr();Need(std::fegetround()==FE_TONEAREST&&(c&((1u<<15)|(1u<<6)|(3u<<13)))==0,"requires unchanged RN/gradual-underflow FP environment");}
static std::vector<std::string> Split(const std::string& s){std::vector<std::string> c;std::string t;std::istringstream f(s);while(std::getline(f,t,','))c.push_back(t);return c;}
static double Number(const std::string& text){size_t n=0;const double v=std::stod(text,&n);Need(n==text.size()&&std::isfinite(v),"nonfinite/non-numeric scalar: "+text);return v;}
struct Stamp{path::path p;uintmax_t bytes;path::file_time_type mtime;explicit Stamp(path::path q):p(path::weakly_canonical(q)),bytes(path::file_size(p)),mtime(path::last_write_time(p)){}void Check()const{Need(path::file_size(p)==bytes&&path::last_write_time(p)==mtime,"input changed during reference: "+p.string());}};
struct Data{std::vector<c08gpucheck::Input> nodes;std::vector<std::array<double,2>> force;};
static Data Load(const path::path& file){
  std::ifstream f(file);Need(bool(f),"snapshot cannot be opened");std::string line;Need(bool(std::getline(f,line)),"empty snapshot");if(!line.empty()&&line.back()=='\r')line.pop_back();
  Need(line=="native_id,x,z,vx,vz,volume,mass,gamma,HG_Fx,HG_Fz","exact actual Debug snapshot schema differs");Data d;d.nodes.reserve(5000);d.force.reserve(5000);
  while(std::getline(f,line)){if(!line.empty()&&line.back()=='\r')line.pop_back();Need(!line.empty(),"empty snapshot row");auto a=Split(line);Need(a.size()==10,"snapshot row is not ten fields");const unsigned id=unsigned(Number(a[0]));Need(id==2060+d.nodes.size()&&Number(a[0])==double(id),"snapshot material IDs are not actual canonical5000");
    c08gpucheck::Input q{id,Number(a[1]),Number(a[2]),Number(a[3]),Number(a[4]),Number(a[5]),Number(a[6]),Number(a[7])};
    Need(q.volume>0&&q.mass>0&&q.gamma>=0&&q.gamma<=1,"nonpositive volume/inertia or invalid actual gamma at ID "+std::to_string(id));d.nodes.push_back(q);d.force.push_back({Number(a[8]),Number(a[9])});}
  Need(f.eof()&&d.nodes.size()==5000,"snapshot is not exactly5000 real input nodes");return d;
}
int main(int argc,char** argv){
  path::path out;bool createdOutput=false;
  try{
    Need(argc==13&&std::string(argv[1])=="--check","closed CLI: --check CSV CONFIG_JSON OUT h bwen G xi dt width source_time source_step");Mode();
    const path::path csv=path::weakly_canonical(argv[2]),config=path::weakly_canonical(argv[3]);out=path::weakly_canonical(argv[4]);
    const auto expected=path::weakly_canonical(path::path(__FILE__).parent_path().parent_path()/"outputs");
    Need(csv==expected/"c08_h18_hg_gpu_debug2_r1/C08PlasticHGDebugFirstN.csv"&&config==expected/"c08_h18_hg_gpu_debug2_r1/C08PlasticHGDebugFirstN.json"&&out==expected/"c08_h18_hg_gpu_forcecheck_r1","only the separately bound genuine Debug first-n input and fresh fixed output are accepted");
    const Stamp csvStat(csv),configStat(config);const double h=Number(argv[5]),bwen=Number(argv[6]),G=Number(argv[7]),xi=Number(argv[8]),dt=Number(argv[9]),width=Number(argv[10]),sourceTime=Number(argv[11]),sourceStep=Number(argv[12]);
    Need(h==double(.072f)&&bwen<0&&G==double(float(20e6f/(2.f*(1.f+.33f))))&&xi==.1&&dt==.000005&&width==dt*.5&&sourceTime==9.9999999997060076&&sourceStep==2000000.,"Config values are not the original actual closed first-n contract");
    const Data data=Load(csv);csvStat.Check();configStat.Check();Need(!path::exists(out)&&path::create_directory(out),"existing complete/partial reference output protected");createdOutput=true;
    const c08gpucheck::Config c{h,2*h,bwen,G,xi,dt,2060,5000};c08gpucheck::State<true> state(c);
    const auto started=std::chrono::steady_clock::now();const auto trial=state.Evaluate(data.nodes,width,false);const double wall=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();Mode();
    Need(trial.force.size()==5000&&trial.stats.rows>0&&trial.stats.born==trial.stats.rows&&trial.stats.kept==0&&trial.stats.dead==0&&state.Generation()==0&&state.MemorySize()==0,"not one actual cold first-n uncommitted reference");
    std::ofstream f(out/"force_comparison.csv");f<<std::setprecision(17)<<"native_id,GPU_Fx,GPU_Fz,CPU_reference_Fx,CPU_reference_Fz,CPU_bound_x,CPU_bound_z,abs_difference_x,abs_difference_z,comparison_budget_x,comparison_budget_z,ratio_x,ratio_z,bits_x,bits_z\n";
    uint64_t bitCount=0,failed=0;double maxDifference=0,maxBudget=0,maxRatio=0;std::string first;
    for(unsigned i=0;i<5000;i++){
      const auto& r=trial.force[i];Need(r.id==2060+i,"reference force ID differs");const double gpu[2]={data.force[i][0],data.force[i][1]},ref[2]={r.x,r.z},err[2]={r.error_x,r.error_z};double difference[2],budget[2],ratio[2];bool equal[2];
      for(unsigned k=0;k<2;k++){
        Need(std::isfinite(err[k])&&err[k]>=0,"nonfinite Audit reference enclosure");const double raw=gpu[k]-ref[k];difference[k]=std::abs(raw);
        // Predetermined same-RN-ordered scalar-model comparison: two evaluation
        // enclosures plus the subtraction's own rounding. No fitted physical tolerance.
        budget[k]=C::EA(C::EA(err[k],err[k]),C::Round(raw));Need(std::isfinite(budget[k])&&budget[k]>0,"undefined arithmetic comparison budget");ratio[k]=difference[k]/budget[k];equal[k]=Bits(gpu[k],ref[k]);bitCount+=equal[k];
        maxDifference=(std::max)(maxDifference,difference[k]);maxBudget=(std::max)(maxBudget,budget[k]);maxRatio=(std::max)(maxRatio,ratio[k]);
        if(!(ratio[k]<=1)){failed++;if(first.empty()){std::ostringstream z;z<<std::setprecision(17)<<"first force mismatch native_id="<<r.id<<" component="<<(k?"z":"x")<<" GPU="<<gpu[k]<<" CPU="<<ref[k]<<" abs_difference="<<difference[k]<<" budget="<<budget[k]<<" ratio="<<ratio[k];first=z.str();}}
      }
      f<<r.id<<','<<gpu[0]<<','<<gpu[1]<<','<<ref[0]<<','<<ref[1]<<','<<err[0]<<','<<err[1]<<','<<difference[0]<<','<<difference[1]<<','<<budget[0]<<','<<budget[1]<<','<<ratio[0]<<','<<ratio[1]<<','<<equal[0]<<','<<equal[1]<<'\n';
    }
    f.flush();Need(bool(f),"reference comparison write failed");csvStat.Check();configStat.Check();Mode();
    std::ofstream result(out/"completion.json");result<<std::setprecision(17)
      <<"{\"stage\":\"c08_h18_hg_gpu_forcecheck_r1\",\"passed\":"<<(failed?"false":"true")<<",\"nodes\":5000,\"scalar_comparisons\":10000,\"actual_equal_bits\":"<<bitCount<<",\"failed_scalars\":"<<failed<<",\"max_abs_difference\":"<<maxDifference<<",\"max_budget\":"<<maxBudget<<",\"max_ratio\":"<<maxRatio
      <<",\"source_step\":2000000,\"source_time\":"<<sourceTime<<",\"width\":"<<width<<",\"reference_directed_rows\":"<<trial.stats.rows<<",\"reference_condition\":"<<trial.stats.condition<<",\"reference_dt_ratio\":"<<trial.stats.dt_ratio<<",\"Audit_certificates\":"<<trial.stats.certificates<<",\"Audit_max_ratio\":"<<trial.stats.max_error_ratio<<",\"reference_wall_s\":"<<wall
      <<",\"same_RN_order_error_model_assumed\":true,\"budget_is_physical_tolerance\":false,\"cross_backend_0ULP_required\":false,\"material_calls\":0,\"physical_updates\":0,\"Darcy_calls\":0,\"reader_invocations\":0,\"solver_invocations\":0,\"physical_acceptance\":false}\n";result.flush();Need(bool(result),"reference completion write failed");Need(!failed,first);std::cout<<"C08_H18_GPU_FIRST_N_FORCE_REFERENCE_PASSED bits="<<bitCount<<"/10000 max_ratio="<<std::setprecision(17)<<maxRatio<<'\n';return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';if(createdOutput){std::ofstream f(out/"failure.txt",std::ios::out|std::ios::app);f<<e.what()<<'\n';}return 1;}
}
