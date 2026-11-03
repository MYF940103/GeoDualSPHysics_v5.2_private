// Actual legacy CPU class versus the untouched frozen pre-cache class.
// Both consume identical deterministic states; no SPH solver or JObject stub.
#include "JSphHourglassCpu.h"
#include "JAppInfo.h"
#include "JException.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

JAppInfo AppInfo("UplHgCpuLegacy","r1","03-11-2026");

#undef _JSphHourglassCpu_
#define JSphHourglassCpu JSphHourglassCpuReference
#include "../outputs/hg_release_base/source/JSphHourglassCpu.h"
#undef JSphHourglassCpu

namespace{
constexpr unsigned First=40,Nx=20,Nz=50,Count=Nx*Nz,Npb=2;
constexpr double Dp=.1,Dt=1e-5;
unsigned BitChecks=0,RealGuardExceptions=0;
void Require(bool okay,const std::string& message){if(!okay)throw std::runtime_error(message);}
template<class T> void Bits(const T& a,const T& b,const std::string& name){
  Require(std::memcmp(&a,&b,sizeof(T))==0,"Bit mismatch: "+name);BitChecks++;
}
// Compare only the actual JException Text line. Class/source/line presentation
// differs for the separately compiled frozen class and is not a guard meaning.
static std::string Error(const JException& error){
  const std::string text=error.ToStr(),key="\nText: ";
  const auto begin=text.find(key);Require(begin!=std::string::npos,"Actual JException has no Text line");
  const auto first=begin+key.size(),end=text.find('\n',first);
  Require(end!=std::string::npos&&end>first,"Actual JException has an incomplete Text line");
  return text.substr(first,end-first);
}
template<class F> std::string Rejected(F call){
  try{call();}
  catch(const JException& error){RealGuardExceptions++;return Error(error);}
  catch(const std::exception& error){throw std::runtime_error("Expected actual JException, received: "+std::string(error.what()));}
  throw std::runtime_error("Missing expected actual HG rejection");
}
struct State{
  std::vector<unsigned> id;
  std::vector<typecode> code;
  std::vector<tdouble3> pos;
  std::vector<tfloat4> vel;
  std::vector<float> plastic;
  std::vector<tfloat3> ace;
  State(){
    for(unsigned p=0;p<Npb;p++)Append(p,CODE_TYPE_FIXED,TDouble3(0),TFloat4(0,0,0,2000));
    for(unsigned j=0;j<Nz;j++)for(unsigned i=0;i<Nx;i++){
      const unsigned k=j*Nx+i;
      Append(First+k,CODE_TYPE_FLUID,TDouble3((i+.5)*Dp,0,(j+.5)*Dp),
        TFloat4(float(1e-4*std::sin(.17*k)),0,float(2e-4*std::cos(.11*k)),float(2000+(k%3))));
    }
    for(unsigned i=0;i<4;i++)Append(First+i,CODE_SetPeriodic(CODE_TYPE_FLUID),
      TDouble3(-10-i,0,20),TFloat4(1,0,2,2000));
  }
  void Append(unsigned i,typecode c,tdouble3 x,tfloat4 v){
    id.push_back(i);code.push_back(c);pos.push_back(x);vel.push_back(v);
    plastic.push_back(0);ace.push_back(TFloat3(.125f,0,-.25f));
  }
  unsigned Size()const{return unsigned(id.size());}
  unsigned Slot(unsigned i)const{
    for(unsigned p=Npb;p<Size();p++)if(CODE_IsNormal(code[p])&&id[p]==i)return p;
    throw std::runtime_error("Test native ID missing");
  }
  void Reverse(){
    const auto reverse=[](auto& a){std::reverse(a.begin()+Npb,a.begin()+Npb+Count);};
    reverse(id);reverse(code);reverse(pos);reverse(vel);reverse(plastic);reverse(ace);
  }
  void ResetAce(){std::fill(ace.begin(),ace.end(),TFloat3(.125f,0,-.25f));}
};
template<class H> void Config(H& h,double xi=.1){
  // Nine arguments deliberately select the unchanged default legacy branch.
  h.Config(First,Count,xi,20,Nx*Dp,1.3*Dp,2.6*Dp,-1,1e5);
}
template<class H> void Predictor(H& h,State& s,double dt){
  h.PredictorForce(s.Size(),Npb,s.id.data(),s.code.data(),s.pos.data(),s.vel.data(),
    s.plastic.data(),s.ace.data(),dt);
}
template<class H> void Corrector(H& h,State& s){
  h.CorrectorForce(s.Size(),Npb,s.id.data(),s.code.data(),s.ace.data());
}
template<class H> void Endpoint(H& h,const State& s,double dt){
  h.CorrectorUpdate(s.Size(),Npb,s.id.data(),s.code.data(),s.pos.data(),s.vel.data(),s.plastic.data(),dt);
}
template<class H> void Step(H& h,State& s,double dt){
  s.ResetAce();Predictor(h,s,dt);h.PredictorUpdate(dt);Corrector(h,s);Endpoint(h,s,dt);
}
void Compare(const JSphHourglassCpuReference& a,const JSphHourglassCpu& b,const State& x,const State& y){
  Require(x.Size()==y.Size(),"Compared acceleration slot counts differ");
  for(unsigned i=First;i<First+Count;i++){
    const auto ah=a.GetHistory(i),bh=b.GetHistory(i),ar=a.GetRate(i),br=b.GetRate(i);
    Bits(ah.x,bh.x,"history.x");Bits(ah.y,bh.y,"history.y");Bits(ah.z,bh.z,"history.z");
    Bits(ar.x,br.x,"rate.x");Bits(ar.y,br.y,"rate.y");Bits(ar.z,br.z,"rate.z");
  }
  for(unsigned i=0;i<x.Size();i++){
    Bits(x.ace[i].x,y.ace[i].x,"ace.x");Bits(x.ace[i].y,y.ace[i].y,"ace.y");Bits(x.ace[i].z,y.ace[i].z,"ace.z");
  }
  const auto& r=a.GetRateInfo();const auto& s=b.GetRateInfo();
#define RATE(f) Bits(r.f,s.f,"RateInfo." #f)
  RATE(netx);RATE(netz);RATE(condition);RATE(skew);RATE(form);RATE(lambda);RATE(tau);
  RATE(ratepower);RATE(workerror);RATE(rmax);RATE(sumrate);RATE(meandxx);RATE(rmsdxx);RATE(meandiv);RATE(rmsdiv);
#undef RATE
  const auto& u=a.GetStats();const auto& v=b.GetStats();
#define STAT(f) Bits(u.f,v.f,"Stats." #f)
  STAT(forcecalls);STAT(predictorupdates);STAT(correctorupdates);STAT(ratecalls);STAT(predictorrates);STAT(endpointrates);
  STAT(firstpairs);STAT(minpairs);STAT(maxpairs);STAT(maxnetforce);STAT(maxactualnetforce);STAT(maxnetrate);
  STAT(maxrelativeforce);STAT(maxrelativerate);STAT(maxhistory);STAT(maxcondition);STAT(maxpoweridentityerror);
  STAT(maxskew);STAT(spinbound);STAT(maxtauratio);STAT(mintau);STAT(maxlambda);
#undef STAT
  Bits(a.GetFirstId(),b.GetFirstId(),"first native ID");Bits(a.GetCount(),b.GetCount(),"native count");
  Bits(a.GetPairCount(),b.GetPairCount(),"pair count");Bits(a.GetDtLimit(),b.GetDtLimit(),"dt limit");
  // The frozen class predates these two fields. Validate current cache counters
  // independently instead of comparing a different struct layout or padding.
  Require(v.ratecalculations+v.ratecachehits==v.ratecalls,"Logical/actual rate counts inconsistent");
}
void Mutate(State& s,const std::string& mode){
  const unsigned p=s.Slot(First+37);
  if(mode=="reorder")s.Reverse();
  else if(mode=="periodic"){
    s.pos.back()=TDouble3(999,0,999);s.vel.back()=TFloat4(99,0,99,1);s.plastic.back()=1;
    s.Append(First+37,CODE_SetPeriodic(CODE_TYPE_FLUID),TDouble3(-5,0,1),TFloat4(0,0,0,1));
  }
  else if(mode=="position_x")s.pos[p].x+=1e-6;
  else if(mode=="position_z")s.pos[p].z-=1e-6;
  else if(mode=="velocity_x")s.vel[p].x+=1e-6f;
  else if(mode=="velocity_z")s.vel[p].z-=1e-6f;
  else if(mode=="density")s.vel[p].w=std::nextafter(s.vel[p].w,std::numeric_limits<float>::infinity());
  else if(mode=="signed_zero")s.vel[s.Slot(First)].x=-0.f;
}
void Scenario(const std::string& mode){
  JSphHourglassCpuReference a;JSphHourglassCpu b;Config(a);Config(b);State x,y;
  for(unsigned step=0;step<8;step++){
    if(step==1){Mutate(x,mode);Mutate(y,mode);}
    const double dt=(mode=="changed_dt" && step%2?Dt*.5:Dt);
    x.ResetAce();y.ResetAce();const unsigned before=b.GetStats().ratecachehits;
    Predictor(a,x,dt);Predictor(b,y,dt);Compare(a,b,x,y);
    const bool changed=step==1 && (mode=="position_x" || mode=="position_z" || mode=="velocity_x"
      || mode=="velocity_z" || mode=="density" || mode=="signed_zero");
    Require(b.GetStats().ratecachehits-before==unsigned(step>0&&!changed),"Unexpected cache decision: "+mode);
    a.PredictorUpdate(dt);b.PredictorUpdate(dt);Compare(a,b,x,y);
    Corrector(a,x);Corrector(b,y);Compare(a,b,x,y);
    if(mode=="evolving_endpoint"){
      x.pos[x.Slot(First+23)].z-=1e-8;y.pos[y.Slot(First+23)].z-=1e-8;
      x.vel[x.Slot(First+17)].z+=1e-8f;y.vel[y.Slot(First+17)].z+=1e-8f;
    }
    const unsigned calculated=b.GetStats().ratecalculations;
    Endpoint(a,x,dt);Endpoint(b,y,dt);Compare(a,b,x,y);
    Require(b.GetStats().ratecalculations==calculated+1,"Endpoint did not recalculate");
  }
  Config(a);Config(b);x=State();y=x;Step(a,x,Dt);Step(b,y,Dt);Compare(a,b,x,y);
  Require(b.GetStats().ratecalculations==2 && !b.GetStats().ratecachehits,"Config did not invalidate cache");
}
struct Guard{const char* name;const char* message;};
template<class H> std::string Rejection(const std::string& name){
  H h;Config(h);State s;Step(h,s,Dt);const unsigned p=s.Slot(First+37);double dt=Dt;
  if(name=="elastic")s.plastic[p]=1e-10f;
  else if(name=="plastic_nan")s.plastic[p]=std::numeric_limits<float>::quiet_NaN();
  else if(name=="duplicate_id")s.id[p]=First;
  else if(name=="unexpected_id")s.id[p]=First+Count;
  else if(name=="missing_native")s.code[p]=CODE_SetOutIgnore(s.code[p]);
  else if(name=="bad_density")s.vel[p].w=0;
  else if(name=="density_nan")s.vel[p].w=std::numeric_limits<float>::quiet_NaN();
  else if(name=="position_nan")s.pos[p].x=std::numeric_limits<double>::quiet_NaN();
  else if(name=="velocity_nan")s.vel[p].z=std::numeric_limits<float>::quiet_NaN();
  else if(name=="coincident")s.pos[p]=s.pos[s.Slot(First)];
  else if(name=="dt_guard_cached")dt=h.GetDtLimit()*1.01;
  else throw std::runtime_error("Unknown guard fixture: "+name);
  return Rejected([&]{Predictor(h,s,dt);});
}
template<class H> std::string DisabledConfig(){
  H h;return Rejected([&]{Config(h,0);});
}
template<class H> double Timed(H& h,State& s,unsigned repeat){
  Config(h);for(unsigned i=0;i<10;i++)Step(h,s,Dt);
  const auto start=std::chrono::steady_clock::now();
  for(unsigned i=0;i<repeat;i++)Step(h,s,Dt);
  return std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
}
}

int main(int argc,char** argv){
  try{
    Require(argc==2 || argc==3,"Use upl_hg_cpu_legacy_r1.exe NEW_CHECK_JSON [repetitions=200]");
    const std::filesystem::path output=argv[1];Require(!std::filesystem::exists(output),"Refusing existing result");
    size_t used=0;const unsigned long parsed=(argc==3?std::stoul(argv[2],&used):200);
    Require((argc!=3||used==std::strlen(argv[2]))&&parsed>=20&&parsed<=10000,"Use 20..10000 repetitions");
    const unsigned repeat=unsigned(parsed);
    const std::vector<std::string> cases={"unchanged","reorder","periodic","position_x","position_z",
      "velocity_x","velocity_z","density","signed_zero","changed_dt","evolving_endpoint"};
    for(const auto& name:cases){Scenario(name);std::cout<<"PASS "<<name<<'\n';}
    const std::vector<Guard> rejects={
      {"elastic","HG currently supports elastic states only."},
      {"plastic_nan","HG currently supports elastic states only."},
      {"duplicate_id","HG duplicate native soil ID."},
      {"unexpected_id","HG unexpected native soil ID."},
      {"missing_native","HG native soil particle set changed."},
      {"bad_density","HG invalid density."},
      {"density_nan","HG invalid density."},
      {"position_nan","HG nonfinite particle state."},
      {"velocity_nan","HG nonfinite particle state."},
      {"coincident","HG coincident native particles."},
      {"dt_guard_cached","HG dt exceeds 0.2 frozen stiffness time scale."}};
    for(const auto& guard:rejects){
      const auto old=Rejection<JSphHourglassCpuReference>(guard.name),now=Rejection<JSphHourglassCpu>(guard.name);
      Require(old==guard.message&&now==guard.message,"Changed original guard meaning: "+std::string(guard.name));
      std::cout<<"PASS reject "<<guard.name<<'\n';
    }
    // Bounded-neighbor support predates this test. Its sole known wording
    // change does not alter the fixed xi=0 rejection tested here.
    Require(DisabledConfig<JSphHourglassCpuReference>()=="HG invalid particle, elastic, kernel or periodic configuration.","Frozen xi=0 guard meaning differs");
    Require(DisabledConfig<JSphHourglassCpu>()=="HG invalid particle, elastic, kernel or neighbor configuration.","Current xi=0 guard meaning differs");
    Require(RealGuardExceptions==2*(unsigned(rejects.size())+1),"Actual JObject/JException guard coverage incomplete");
    std::vector<double> oldtime(3),newtime(3);unsigned calculations=0,hits=0,logical=0;
    for(unsigned batch=0;batch<3;batch++){
      JSphHourglassCpuReference a;JSphHourglassCpu b;State x,y;
      if(batch%2){newtime[batch]=Timed(b,y,repeat);oldtime[batch]=Timed(a,x,repeat);}
      else{oldtime[batch]=Timed(a,x,repeat);newtime[batch]=Timed(b,y,repeat);}
      Compare(a,b,x,y);const auto& stats=b.GetStats();calculations=stats.ratecalculations;hits=stats.ratecachehits;logical=stats.ratecalls;
      Require(calculations==repeat+11 && hits==repeat+9 && logical==2*(repeat+10),"Benchmark count mismatch");
    }
    auto olds=oldtime,news=newtime;std::sort(olds.begin(),olds.end());std::sort(news.begin(),news.end());
    std::ofstream record(output);record<<std::setprecision(17);
    record<<"{\"passed\":true,\"stage\":\"upl_hg_cpu_legacy_r1\",\"status\":\"actual_legacy_frozen_class_bitwise_passed_not_physical_acceptance\","
      <<"\"required_max_ulp\":0,\"differing_field_bytes\":0,\"native_particles\":"<<Count
      <<",\"scalar_bit_checks\":"<<BitChecks<<",\"actual_JObject_JException\":true,\"JObject_stub\":false"
      <<",\"default_legacy_Config_arguments\":9,\"J_state_passed\":false,\"reference_compiled_separately\":true"
      <<",\"scenarios\":[";
    for(size_t i=0;i<cases.size();i++)record<<(i?",":"")<<'"'<<cases[i]<<'"';
    record<<"],\"original_guard_meanings\":[";
    for(size_t i=0;i<rejects.size();i++)record<<(i?",":"")<<'"'<<rejects[i].name<<'"';
    record<<"],\"actual_guard_exceptions\":"<<RealGuardExceptions
      <<",\"xi_zero_class_rejection_meaning_compatible\":true,\"xi_zero_known_periodic_to_neighbor_wording_verified\":true"
      <<",\"source_location_in_guard_comparison\":false,\"all_shared_Stats_members_compared\":true"
      <<",\"precache_reference_has_no_cache_counters\":true,\"current_cache_counters_independently_verified\":true"
      <<",\"repeat_per_batch\":"<<repeat<<",\"warmup_steps_per_path\":10,\"batches\":3,\"logical_rate_calls\":"<<logical
      <<",\"actual_rate_calculations\":"<<calculations<<",\"endpoint_cache_hits\":"<<hits
      <<",\"old_batch_seconds\":["<<oldtime[0]<<','<<oldtime[1]<<','<<oldtime[2]
      <<"],\"new_batch_seconds\":["<<newtime[0]<<','<<newtime[1]<<','<<newtime[2]
      <<"],\"old_median_seconds\":"<<olds[1]<<",\"new_median_seconds\":"<<news[1]
      <<",\"timing_has_acceptance_threshold\":false,\"solver_run\":false,\"physical_acceptance\":false,"
      <<"\"limitations\":[\"Manufactured actual-class default-legacy regression, not an SPH trajectory\","
      <<"\"The frozen pre-cache Stats has no ratecalculations/ratecachehits fields; shared members compare bitwise\","
      <<"\"Guard Text is fixed and compared; actual source/class/line presentation is deliberately excluded\","
      <<"\"Xi=0 tests actual class rejection only; solver-disabled allocation/pass/clock/field compatibility is separate\","
      <<"\"No coupled J, constitutive stress, pore pressure, boundary, transport or physical acceptance\"]}\n";
    record.flush();Require(bool(record),"Cannot write check JSON");
    std::cout<<"LEGACY TEST PASSED, scalar bit checks="<<BitChecks<<'\n';return 0;
  }catch(const JException& error){std::cerr<<error.ToStr()<<'\n';return 1;}
  catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Actual legacy HG regression rejected; retain partial outputs\n";return 2;}
}
