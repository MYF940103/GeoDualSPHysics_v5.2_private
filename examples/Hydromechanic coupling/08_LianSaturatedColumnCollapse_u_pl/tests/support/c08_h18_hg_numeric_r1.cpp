// Frozen-input numeric implementation comparison and pure-spin helper range only.
#include "c08_h18_hg_numeric_r1.hpp"
#include <cfenv>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <cstring>
#include <xmmintrin.h>
namespace pf=std::filesystem;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
struct D3{double x,y,z;};struct F3{float x,y,z;};
static_assert(sizeof(D3)==24&&sizeof(F3)==12&&sizeof(unsigned)==4,"Original typed export ABI");
static bool Bits(double a,double b){return std::memcmp(&a,&b,8)==0;}
static void Mode(){const unsigned q=_mm_getcsr();Need(std::numeric_limits<double>::is_iec559&&std::fegetround()==FE_TONEAREST&&(q&((1u<<15)|(1u<<6)|(3u<<13)))==0,"Binary64 RN/gradual-underflow required; never reset physical flags");}
struct Stamp{pf::path path;std::uintmax_t bytes;pf::file_time_type time;explicit Stamp(pf::path p):path(p),bytes(pf::file_size(p)),time(pf::last_write_time(p)){}void Check()const{Need(pf::file_size(path)==bytes&&pf::last_write_time(path)==time,"Consumed input changed during component");}};
static std::vector<std::string> Split(std::string line){if(!line.empty()&&line.back()=='\r')line.pop_back();std::vector<std::string> out;std::stringstream s(line);std::string x;while(std::getline(s,x,','))out.push_back(x);return out;}
static unsigned Col(const std::vector<std::string>& h,const char* key){const auto q=std::find(h.begin(),h.end(),key);Need(q!=h.end(),"Required CSV field missing");return unsigned(q-h.begin());}
template<class X>static std::vector<X> Array(std::ifstream& f){std::vector<X> a(6805);f.read(reinterpret_cast<char*>(a.data()),sizeof(X)*a.size());Need(bool(f),"Truncated sealed typed input");return a;}
struct Gamma{bool found=false;double value=0,mass=0,time=0,fx=0,fz=0;unsigned step=0,status=0;};
static std::array<std::vector<Gamma>,2> LoadGamma(const pf::path& file){
  std::array<std::vector<Gamma>,2> out;for(auto& a:out)a.resize(7060);std::ifstream f(file);std::string l;Need(bool(std::getline(f,l)),"Missing sealed stage_nodes");const auto h=Split(l);
  const auto cp=Col(h,"source_part"),cm=Col(h,"mode"),cu=Col(h,"update"),cf=Col(h,"force_stage"),ci=Col(h,"native_id"),cg=Col(h,"gamma"),ct=Col(h,"source_time_s"),cs=Col(h,"source_completed_step"),ca=Col(h,"actual_sigma_kappa_match"),co=Col(h,"HG_on"),cc=Col(h,"same_input_shadow_status"),cw=Col(h,"stage_mass"),cfx=Col(h,"HG_Fx"),cfz=Col(h,"HG_Fz");unsigned rows=0,selected=0;
  while(std::getline(f,l)){const auto c=Split(l);Need(c.size()==h.size(),"Stage-node CSV schema differs");rows++;const unsigned part=std::stoul(c[cp]);if((part!=38&&part!=76)||c[cm]!="ON"||c[cu]!="0"||c[cf]!="n")continue;
    const unsigned id=std::stoul(c[ci]);Need(id>=2060&&id<7060,"Gamma ID is not original soil");auto& q=out[part==38?0:1][id];Need(!q.found&&c[ca]=="1"&&c[co]=="1","Actual same-input matched ON n0 gamma required");q.found=true;q.value=std::stod(c[cg]);q.mass=std::stod(c[cw]);q.time=std::stod(c[ct]);q.step=std::stoul(c[cs]);q.status=std::stoul(c[cc]);q.fx=std::stod(c[cfx]);q.fz=std::stod(c[cfz]);Need(std::isfinite(q.value)&&q.value>=0&&q.value<=1&&q.mass>0&&q.status>=1&&q.status<=4,"Saved gamma/status/mass domain differs");selected++;}
  Need(rows==60000&&selected==10000,"Closed 60k stage rows/10k n0 gamma coverage differs");return out;
}
struct Frozen{unsigned part=0,step=0;double time=0;std::vector<c08num::Input> nodes;std::vector<std::array<double,2>> retainedForce;};
static Frozen LoadState(const pf::path& root,unsigned which,const std::vector<Gamma>& gamma){
  Frozen out;out.part=which?76:38;out.step=which?2152001:2076001;std::ifstream clocks(root/"clocks.csv");std::string line;Need(bool(std::getline(clocks,line)),"Missing original clocks");unsigned rows=0;bool found=false;
  while(std::getline(clocks,line)){const auto c=Split(line);Need(c.size()==11,"Actual11-column clocks required");if(std::stoul(c[0])==out.part){Need(!found&&std::stoul(c[4])==out.step&&std::stod(c[6])==.000005&&std::stod(c[7])<=1e-14&&c[8]=="0","Exact saved source clock/signed guard differs");out.time=std::stod(c[2]);found=true;}rows++;}Need(found&&rows==301,"Full301 clock header/coverage changed");
  std::ifstream f(root/"typed22.bin",std::ios::binary);unsigned h[3]={};f.read(reinterpret_cast<char*>(h),12);const std::uintmax_t stride=8+std::uintmax_t(6805)*212;Need(bool(f)&&h[0]==6805&&h[1]==22&&h[2]==301&&pf::file_size(root/"typed22.bin")==12+301*stride,"Original301/22 payload extent changed");f.seekg(std::streamoff(12+out.part*stride));double time=0;f.read(reinterpret_cast<char*>(&time),8);Need(Bits(time,out.time),"Native and clock actual time differ");
  const auto id=Array<unsigned>(f);const auto pos=Array<D3>(f);const auto vel=Array<F3>(f);
  Array<F3>(f);Array<F3>(f);Array<F3>(f);Array<F3>(f); // legacy stress, FSnormal, loadAce
  Array<float>(f);Array<float>(f);Array<float>(f);Array<float>(f);Array<float>(f); // cache,kappa,p,P0,excess
  Array<D3>(f);Array<D3>(f);Array<unsigned>(f);const auto J=Array<double>(f);Array<double>(f);Array<double>(f);const auto V=Array<double>(f);Array<double>(f);Array<double>(f);Array<float>(f);
  std::vector<bool> seen(7060,false);unsigned fixed=0;out.nodes.reserve(5000);out.retainedForce.resize(7060);
  for(unsigned i=0;i<6805;i++){Need(id[i]<7060&&!seen[id[i]]&&(id[i]<1805||id[i]>=2060),"Original native ID/retirement domain differs");seen[id[i]]=true;if(id[i]<1805){fixed++;continue;}
    const auto& g=gamma[id[i]];const double m=(double(3.316f)/double(2072.5f))*(double(2072.5f)-1000.+1000.*J[i]);
    Need(g.found&&g.step==out.step&&Bits(g.time,out.time)&&Bits(g.mass,m),"Gamma does not match actual n0 ID/clock/inertia");
    Need(std::isfinite(J[i])&&J[i]>1.-double(.35f)&&std::isfinite(V[i])&&V[i]>0&&m>0&&pos[i].y==0&&vel[i].y==0,"Original current-J/2D positive domain differs");
    out.nodes.push_back({id[i],pos[i].x,pos[i].z,double(vel[i].x),double(vel[i].z),V[i],m,g.value});out.retainedForce[id[i]]={g.fx,g.fz};}
  Need(fixed==1805&&out.nodes.size()==5000,"All5000 original soil IDs required");std::sort(out.nodes.begin(),out.nodes.end(),[](const auto& a,const auto& b){return a.id<b.id;});for(unsigned i=0;i<5000;i++)Need(out.nodes[i].id==2060+i,"Native ordered soil ID coverage differs");return out;
}
struct Counts{uint64_t node=0,row=0,force=0,history=0,branch=0,meta=0,retained=0,local=0;} counts;
[[noreturn]]static void Mismatch(unsigned part,unsigned generation,const char* phase,uint64_t key,const char* field){std::ostringstream s;s<<"Audit/Fast first mismatch part="<<part<<" generation="<<generation<<" phase="<<phase<<" key/ID="<<key<<" field="<<field;throw std::runtime_error(s.str());}
static void Eq(double a,double b,unsigned part,unsigned gen,const char* phase,uint64_t key,const char* field){if(!Bits(a,b))Mismatch(part,gen,phase,key,field);}
template<class A,class B>static void Compare(const A& a,const B& b,unsigned part,unsigned generation,const char* phase){
  Need(a.full==b.full&&a.generation==b.generation&&a.force.size()==b.force.size()&&a.next.size()==b.next.size()&&a.node_trace.size()==b.node_trace.size()&&a.row_trace.size()==b.row_trace.size(),"Audit/Fast extents/generation differ");
  for(size_t i=0;i<a.node_trace.size();i++){const auto& x=a.node_trace[i];const auto& y=b.node_trace[i];if(x.id!=y.id)Mismatch(part,generation,phase,x.id,"node ownership");if(std::memcmp(x.values.data(),y.values.data(),sizeof(x.values)))for(size_t j=0;j<x.values.size();j++)Eq(x.values[j],y.values[j],part,generation,phase,x.id,c08num::NodeTraceNames[j]);counts.node+=x.values.size();}
  for(size_t i=0;i<a.row_trace.size();i++){const auto& x=a.row_trace[i];const auto& y=b.row_trace[i];if(x.key!=y.key)Mismatch(part,generation,phase,x.key,"row ownership");if(x.branch!=y.branch||x.knownconstant!=y.knownconstant)Mismatch(part,generation,phase,x.key,"event/knownconstant branch");counts.branch+=2;if(std::memcmp(x.values.data(),y.values.data(),sizeof(x.values)))for(size_t j=0;j<x.values.size();j++)Eq(x.values[j],y.values[j],part,generation,phase,x.key,c08num::RowTraceNames[j]);counts.row+=x.values.size();}
  for(size_t i=0;i<a.force.size();i++){if(a.force[i].id!=b.force[i].id)Mismatch(part,generation,phase,a.force[i].id,"force ownership");Eq(a.force[i].x,b.force[i].x,part,generation,phase,a.force[i].id,"Fx");Eq(a.force[i].z,b.force[i].z,part,generation,phase,a.force[i].id,"Fz");counts.force+=2;}
  for(size_t i=0;i<a.next.size();i++){if(a.next[i].key!=b.next[i].key)Mismatch(part,generation,phase,a.next[i].key,"history ownership");Eq(a.next[i].e.x.v,b.next[i].e.x.v,part,generation,phase,a.next[i].key,"e.x");Eq(a.next[i].e.z.v,b.next[i].e.z.v,part,generation,phase,a.next[i].key,"e.z");counts.history+=2;}
  const auto& x=a.stats;const auto& y=b.stats;
  Need(x.pairs==y.pairs&&x.rows==y.rows&&x.kept==y.kept&&x.born==y.born&&x.dead==y.dead&&x.returning==y.returning&&x.known_constant_receivers==y.known_constant_receivers&&x.known_constant_rows==y.known_constant_rows,"Audit/Fast physical lifecycle branch/count differs");
#define SAME_META(f) Eq(x.f,y.f,part,generation,phase,0,#f);counts.meta++
  SAME_META(Eold);SAME_META(Ekept);SAME_META(Edead);SAME_META(Enew);SAME_META(work_rows);SAME_META(work_nodes);SAME_META(loading_loss);SAME_META(rotation_change);SAME_META(ledger);SAME_META(adjoint_work);SAME_META(net_x);SAME_META(net_z);SAME_META(torque);SAME_META(condition);SAME_META(lambda_raw);SAME_META(dt_ratio_raw);SAME_META(spin_raw);SAME_META(D_min);SAME_META(D_max);SAME_META(max_force);SAME_META(max_omega);SAME_META(min_r);
#undef SAME_META
}
template<class F>static auto Timed(F f,double& seconds){const auto start=std::chrono::steady_clock::now();auto out=f();seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();return out;}
static void Numeric(const Frozen& f,std::ofstream& csv){
  c08num::Config c{double(.072f),double(2*.072f),double(float(-2.7852/(double(.072f)*double(.072f)*double(.072f)))),double(float(20e6f/(2.f*(1.f+.33f)))),.1,.000005,2060,5000};
  c08num::State<true> audit(c);c08num::State<false> fast(c);
  for(unsigned gen=0;gen<2;gen++){double ap=0,fp=0,af=0,ff=0;
    Mode();auto pa=Timed([&](){return audit.Evaluate(f.nodes,.0000025,false);},ap);Mode();auto pf=Timed([&](){return fast.Evaluate(f.nodes,.0000025,false);},fp);Mode();Compare(pa,pf,f.part,gen,"predictor");
    if(gen==0)for(const auto& z:pa.force){Eq(z.x,f.retainedForce[z.id][0],f.part,gen,"retained_actual_n0",z.id,"HG_Fx");Eq(z.z,f.retainedForce[z.id][1],f.part,gen,"retained_actual_n0",z.id,"HG_Fz");counts.retained+=2;}
    auto ca=Timed([&](){return audit.Evaluate(f.nodes,.000005,true);},af);Mode();auto cf=Timed([&](){return fast.Evaluate(f.nodes,.000005,true);},ff);Mode();Compare(ca,cf,f.part,gen,"full");
    audit.Commit(ca,pa);fast.Commit(cf,pf);Need(audit.Generation()==fast.Generation()&&audit.Generation()==gen+1&&audit.MemorySize()==fast.MemorySize(),"Audit/Fast accepted history generation differs");
    Need(ca.stats.Enew>0&&ca.stats.rows>0,"Frozen input did not produce nonzero history");
    csv<<f.part<<','<<f.time<<','<<f.step<<','<<gen<<",predictor,"<<pa.stats.rows<<','<<ap<<','<<fp<<','<<pa.stats.Enew<<','<<pa.stats.work_nodes<<','<<pa.stats.ledger<<','<<pa.stats.ledger_bound<<','<<pa.stats.max_error_ratio<<",1\n";
    csv<<f.part<<','<<f.time<<','<<f.step<<','<<gen<<",full,"<<ca.stats.rows<<','<<af<<','<<ff<<','<<ca.stats.Enew<<','<<ca.stats.work_nodes<<','<<ca.stats.ledger<<','<<ca.stats.ledger_bound<<','<<ca.stats.max_error_ratio<<",1\n";
  }
}
static void LocalUnloading(std::ofstream& csv){
  using A=c08num::detail::Core<true>;using F=c08num::detail::Core<false>;using AB=typename A::B;using FB=typename F::B;
  csv<<std::setprecision(17)<<"gamma,branch,t1,t2,hnew_x,Ih_x,delta_E,work,loss,total,balance_residual,balance_bound,all_values_bit_equal\n";
  const char* names[12]={"hx","hz","Ix","Iz","A","Z","t1","t2","de","work","loss","total"};
  for(double g:{0.,.5}){const typename A::V h{AB(1),AB(0)},z{AB(-1),AB(0)};const typename F::V hf{FB(1),FB(0)},zf{FB(-1),FB(0)};
    const auto a=A::ExactStep(h,z,AB(1),AB(g),AB(3),false);const auto f=F::ExactStep(hf,zf,FB(1),FB(g),FB(3),false);
    const double av[12]={a.h.x.v,a.h.z.v,a.I.x.v,a.I.z.v,a.A.v,a.Z.v,a.t1.v,a.t2.v,a.de.v,a.work.v,a.loss.v,a.total.v};
    const double fv[12]={f.h.x.v,f.h.z.v,f.I.x.v,f.I.z.v,f.A.v,f.Z.v,f.t1.v,f.t2.v,f.de.v,f.work.v,f.loss.v,f.total.v};
    for(unsigned i=0;i<12;i++){Eq(av[i],fv[i],0,0,"local_unloading",0,names[i]);counts.local++;}Need(a.branch==f.branch,"Local unloading branch differs");counts.local++;
    const AB balance=a.total+a.loss;A::Close(balance,"fixed unloading contract preserved");
    csv<<g<<','<<a.branch<<','<<a.t1.v<<','<<a.t2.v<<','<<a.h.x.v<<','<<a.I.x.v<<','<<a.de.v<<','<<a.work.v<<','<<a.loss.v<<','<<a.total.v<<','<<balance.v<<','<<balance.e<<",1\n";
  }
}
struct Reference{std::string name,total,quarter;unsigned steps=0,period=0;std::array<double,4> angle{};double x=0,z=0,xe=0,ze=0,qx=0,qz=0,qxe=0,qze=0;};
static double FromHexBits(const std::string& s){const uint64_t bits=std::stoull(s,nullptr,16);double x;std::memcpy(&x,&bits,8);return x;}
static std::vector<Reference> LoadReferences(const pf::path& path){std::ifstream f(path);std::string line;Need(bool(std::getline(f,line)),"Missing high-precision reference");const auto h=Split(line);std::vector<Reference> out;
  while(std::getline(f,line)){const auto c=Split(line);Need(c.size()==h.size(),"Reference schema differs");Reference q;q.name=c[Col(h,"sequence")];q.steps=std::stoul(c[Col(h,"steps")]);q.period=std::stoul(c[Col(h,"period")]);q.total=c[Col(h,"exact_double_angle_sum_decimal")];q.x=std::stod(c[Col(h,"x_reference")]);q.z=std::stod(c[Col(h,"z_reference")]);q.xe=std::stod(c[Col(h,"x_reference_error")]);q.ze=std::stod(c[Col(h,"z_reference_error")]);q.quarter=c[Col(h,"quarter_exact_double_angle_sum_decimal")];q.qx=std::stod(c[Col(h,"quarter_x_reference")]);q.qz=std::stod(c[Col(h,"quarter_z_reference")]);q.qxe=std::stod(c[Col(h,"quarter_x_reference_error")]);q.qze=std::stod(c[Col(h,"quarter_z_reference_error")]);
    Need(q.steps==1024&&(q.name=="constant"?q.period==1:q.name=="variable_reverse"&&q.period==4),"Only the two closed1024-angle sequences admitted");const double base=std::ldexp(6.283185307179586,-10),scale[4]={-.25,1.25,1.5,1.5};
    for(unsigned i=0;i<q.period;i++){q.angle[i]=FromHexBits(c[Col(h,("angle"+std::to_string(i)+"_bits").c_str())]);const double expected=q.name=="constant"?base:base*scale[i];Need(Bits(q.angle[i],expected)&&fabs(q.angle[i]*.5)<.005,"Actual closed double angle/half-range differs");}
    Need(q.xe>=0&&q.ze>=0&&q.qxe>=0&&q.qze>=0&&std::isfinite(q.qx)&&std::isfinite(q.qz)&&std::isfinite(q.qxe)&&std::isfinite(q.qze)&&std::isfinite(q.x)&&std::isfinite(q.z)&&std::isfinite(q.xe)&&std::isfinite(q.ze),"Invalid high-precision interval reference");out.push_back(q);}
  Need(out.size()==2&&out[0].name=="constant"&&out[1].name=="variable_reverse","Closed reference count/order differs");return out;
}
static void Spin(const Reference& ref,std::ofstream& csv){
  c08num::VecInput a{.125,-.25,0,0},f=a;double sum=0,maxdrift=0,qx=0,qz=0,qdx=0,qdz=0,qbx=0,qbz=0;uint64_t compared=0;
  for(unsigned i=0;i<ref.steps;i++){const double w=ref.angle[i%ref.period];const auto aa=c08num::Spin<true>(a,w,1.,.5),ff=c08num::Spin<false>(f,w,1.,.5);
    Eq(aa.e.x,ff.e.x,0,i,"pure_spin",0,"e.x");Eq(aa.e.z,ff.e.z,0,i,"pure_spin",0,"e.z");Need(aa.branch==ff.branch,"Spin zero-drive branch differs");compared+=3;
    a=aa.e;f=ff.e;sum+=w;
    if(i+1==256){using C=c08num::detail::Core<true>;using B=typename C::B;const B dx=B(a.x,a.error_x)-B(ref.qx,ref.qxe),dz=B(a.z,a.error_z)-B(ref.qz,ref.qze);C::Close(dx,"quarter-turn spin sign/reference x");C::Close(dz,"quarter-turn spin sign/reference z");qx=a.x;qz=a.z;qdx=dx.v;qdz=dz.v;qbx=dx.e;qbz=dz.e;}
    maxdrift=std::max(maxdrift,std::abs((a.x*a.x+a.z*a.z)-(.125*.125+.25*.25)));
  }
  using Core=c08num::detail::Core<true>;using B=typename Core::B;
  const B dx=B(a.x,a.error_x)-B(ref.x,ref.xe),dz=B(a.z,a.error_z)-B(ref.z,ref.ze);
  Core::Close(dx,"actual-angle high-precision spin x");Core::Close(dz,"actual-angle high-precision spin z");
  const B energy=B(.5)*(B(a.x,a.error_x)*B(a.x,a.error_x)+B(a.z,a.error_z)*B(a.z,a.error_z))-B(.5*(.125*.125+.25*.25));Core::Close(energy,"full accumulated pure-spin energy");
  csv<<ref.name<<','<<ref.steps<<','<<ref.total<<','<<sum<<','<<a.x<<','<<a.z<<','<<a.error_x<<','<<a.error_z<<','<<ref.x<<','<<ref.z<<','<<ref.xe<<','<<ref.ze<<','<<dx.v<<','<<dx.e<<','<<dz.v<<','<<dz.e<<','<<energy.v<<','<<energy.e<<','<<maxdrift<<','<<ref.quarter<<','<<qx<<','<<qz<<','<<qdx<<','<<qbx<<','<<qdz<<','<<qbz<<','<<compared<<",1\n";
}
int main(int argc,char** argv){pf::path out;bool created=false;try{
  Need(argc==6&&std::string(argv[1])=="--check","Use --check SEALED_FULL301_NATIVE SEALED_STAGE_NODES SEALED_ROTATION_REFERENCE FRESHOUT");Mode();const pf::path tests=pf::path(__FILE__).parent_path().parent_path();
  const pf::path native=pf::absolute(argv[2]),gammafile=pf::absolute(argv[3]),reference=pf::absolute(argv[4]);out=pf::absolute(argv[5]);
  Need(pf::equivalent(native,tests/"outputs/c08_h18_as03n255_full3_r1/native_r1")&&pf::equivalent(gammafile,tests/"outputs/c08_h18_plastic_hg_stage_r1/stage_nodes.csv")&&pf::equivalent(reference,tests/"outputs/c08_h18_hg_numeric_r1_build/rotation_reference.csv")&&out==pf::absolute(tests/"outputs/c08_h18_hg_numeric_r1")&&!pf::exists(out),"Only original closed inputs and fresh output admitted");
  std::vector<Stamp> protectedFiles;for(const char* leaf:{"typed22.bin","typed22_layout.csv","clocks.csv","completion.json"})protectedFiles.emplace_back(native/leaf);protectedFiles.emplace_back(gammafile);protectedFiles.emplace_back(reference);protectedFiles.emplace_back(pf::absolute(argv[0]));
  for(const char* leaf:{"c08_h18_as03n255_full3_native_r1.check.json","c08_h18_as03n255_full3_review_r1.check.json","c08_h18_plastic_hg_stage_r1.check.json","c08_h18_plastic_hg_stage_r1.component.call.json","c08_h18_hg_numeric_r1.build.json"})protectedFiles.emplace_back(tests/"logs"/leaf);
  Need(pf::create_directory(out),"Cannot create fresh component output");created=true;const auto gamma=LoadGamma(gammafile);const auto refs=LoadReferences(reference);
  std::ofstream values(out/"value_comparison.csv"),spin(out/"spin.csv"),local(out/"unloading.csv");Need(bool(values)&&bool(spin)&&bool(local),"Fresh output unavailable");values<<std::setprecision(17);spin<<std::setprecision(17);
  values<<"part,actual_time_s,actual_completed_step,frozen_generation,trial,directed_rows,audit_wall_s,fast_wall_s,Enew,work_nodes,audit_ledger,audit_ledger_bound,audit_max_error_ratio,all_common_values_bit_equal\n";
  spin<<"sequence,steps,exact_double_angle_sum_decimal,ordinary_double_angle_sum,actual_x,actual_z,audit_x_bound,audit_z_bound,reference_x,reference_z,reference_x_bound,reference_z_bound,x_error,x_error_bound,z_error,z_error_bound,energy_drift,energy_drift_bound,max_squared_norm_drift,quarter_exact_angle_sum_decimal,quarter_actual_x,quarter_actual_z,quarter_x_error,quarter_x_bound,quarter_z_error,quarter_z_bound,bit_comparisons,Audit_Fast_bit_equal\n";
  for(unsigned i=0;i<2;i++)Numeric(LoadState(native,i,gamma[i]),values);for(const auto& q:refs)Spin(q,spin);LocalUnloading(local);Mode();Need(counts.retained==20000&&counts.local==26,"Both original n0 force fields must be checked");for(const auto& q:protectedFiles)q.Check();values.flush();spin.flush();local.flush();Need(bool(values)&&bool(spin)&&bool(local),"Output write failed");
  std::ofstream done(out/"completion.json");done<<"{\"stage\":\"c08_h18_hg_numeric_r1\",\"passed\":true,\"frozen_source_parts\":[38,76],\"frozen_generations_per_case\":2,\"value_comparison_rows\":8,\"spin_sequences\":2,\"spin_steps_per_sequence\":1024,\"node_scalar_bits\":"<<counts.node<<",\"row_scalar_bits\":"<<counts.row<<",\"force_scalar_bits\":"<<counts.force<<",\"history_scalar_bits\":"<<counts.history<<",\"branch_checks\":"<<counts.branch<<",\"common_metadata_scalar_bits\":"<<counts.meta<<",\"retained_actual_n0_force_scalar_bits\":"<<counts.retained<<",\"local_unloading_value_and_branch_bits\":"<<counts.local<<",\"quarter_turn_reference_checks\":4,\"all_common_values_bit_equal\":true,\"Audit_only_error_and_Hi_metadata_compared_as_equal\":false,\"fixed_native_gamma_inputs_not_redecoded\":true,\"private_State_spin_guard_retained\":true,\"public_source_changed\":false,\"rotation_helper_range_only\":true,\"coupled_large_rotation_qualified\":false,\"C08_performance_inferred\":false,\"physical_updates\":0,\"material_calls\":0,\"Darcy_calls\":0,\"solver_invocations\":0,\"reader_invocations\":0,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';if(created){std::ofstream f(out/"failure.txt");f<<e.what()<<'\n';}return 1;}}
