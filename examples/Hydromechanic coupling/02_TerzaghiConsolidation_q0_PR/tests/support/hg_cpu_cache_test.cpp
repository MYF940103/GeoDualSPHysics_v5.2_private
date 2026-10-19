// Standalone arithmetic/validation regression against the frozen pre-cache class.
// Both classes consume identical deterministic states. This is not an SPH run.
#include "JSphHourglassCpu.h"
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

// Only the exception presentation is stubbed; retain the original guard texts.
// The production Debug/full-solver tests exercise the real JObject exception.
void JObject::RunExceptioon(const std::string&,int,const std::string&,
  const std::string&,const std::string& message,const std::string&)const{
  throw std::runtime_error(message);
}

#undef _JSphHourglassCpu_
#define JSphHourglassCpu JSphHourglassCpuReference
#include "../outputs/hg_release_base/source/JSphHourglassCpu.h"
#undef JSphHourglassCpu

namespace{
constexpr unsigned First=40,Nx=20,Nz=50,Count=Nx*Nz,Npb=2;
constexpr double Dp=.1,Dt=1e-5;
void Require(bool okay,const std::string& message){if(!okay)throw std::runtime_error(message);}
template<class T> void Bits(const T& a,const T& b,const std::string& name){
  Require(std::memcmp(&a,&b,sizeof(T))==0,"Bit mismatch: "+name);
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
  for(unsigned i=First;i<First+Count;i++){
    const auto ah=a.GetHistory(i),bh=b.GetHistory(i),ar=a.GetRate(i),br=b.GetRate(i);
    Bits(ah.x,bh.x,"history.x");Bits(ah.z,bh.z,"history.z");
    Bits(ar.x,br.x,"rate.x");Bits(ar.z,br.z,"rate.z");
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
  Bits(a.GetPairCount(),b.GetPairCount(),"pair count");Bits(a.GetDtLimit(),b.GetDtLimit(),"dt limit");
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
  try{Predictor(h,s,dt);}catch(const std::exception& e){return e.what();}
  throw std::runtime_error("Missing expected rejection: "+name);
}
template<class H> std::string DisabledConfig(){
  H h;try{Config(h,0);}catch(const std::exception& e){return e.what();}
  throw std::runtime_error("Xi=0 unexpectedly constructs an enabled class");
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
    Require(argc==2 || argc==3,"Use hg_cpu_cache_test.exe NEW_CHECK_JSON [repetitions=200]");
    const std::filesystem::path output=argv[1];Require(!std::filesystem::exists(output),"Refusing existing result");
    const unsigned repeat=(argc==3?unsigned(std::stoul(argv[2])):200);
    Require(repeat>=20 && repeat<=10000,"Use 20..10000 repetitions");
    const std::vector<std::string> cases={"unchanged","reorder","periodic","position_x","position_z",
      "velocity_x","velocity_z","density","signed_zero","changed_dt","evolving_endpoint"};
    for(const auto& name:cases){Scenario(name);std::cout<<"PASS "<<name<<'\n';}
    const std::vector<std::string> rejects={"elastic","plastic_nan","duplicate_id","unexpected_id","missing_native",
      "bad_density","density_nan","position_nan","velocity_nan","coincident","dt_guard_cached"};
    for(const auto& name:rejects){
      Require(Rejection<JSphHourglassCpuReference>(name)==Rejection<JSphHourglassCpu>(name),"Changed rejection: "+name);
      std::cout<<"PASS reject "<<name<<'\n';
    }
    Require(DisabledConfig<JSphHourglassCpuReference>()==DisabledConfig<JSphHourglassCpu>(),"Changed disabled class guard");
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
    record<<"{\"passed\":true,\"status\":\"standalone_frozen_class_bitwise_passed_not_physical_acceptance\","
      <<"\"required_max_ulp\":0,\"differing_field_bytes\":0,\"native_particles\":"<<Count
      <<",\"scenarios\":[";
    for(size_t i=0;i<cases.size();i++)record<<(i?",":"")<<'"'<<cases[i]<<'"';
    record<<"],\"unchanged_rejections\":[";
    for(size_t i=0;i<rejects.size();i++)record<<(i?",":"")<<'"'<<rejects[i]<<'"';
    record<<"],\"xi_zero_class_rejection_unchanged\":true,\"repeat_per_batch\":"<<repeat
      <<",\"warmup_steps_per_path\":10,\"batches\":3,\"logical_rate_calls\":"<<logical
      <<",\"actual_rate_calculations\":"<<calculations<<",\"endpoint_cache_hits\":"<<hits
      <<",\"old_batch_seconds\":["<<oldtime[0]<<','<<oldtime[1]<<','<<oldtime[2]
      <<"],\"new_batch_seconds\":["<<newtime[0]<<','<<newtime[1]<<','<<newtime[2]
      <<"],\"old_median_seconds\":"<<olds[1]<<",\"new_median_seconds\":"<<news[1]
      <<",\"hg_region_speedup\":"<<olds[1]/news[1]<<",\"hg_region_reduction_fraction\":"<<1-news[1]/olds[1]
      <<",\"timed_region\":\"HG full stage cycle plus common acceleration reset, deterministic unchanged endpoints\","
      <<"\"limitations\":[\"Standalone frozen-class comparison, not an SPH trajectory or whole-run speedup\","
      <<"\"JObject exception presentation replaced by runtime_error; original guard texts compared\","
      <<"\"Xi=0 tests class rejection only; solver-disabled path belongs to full solver regression\","
      <<"\"No constitutive stress, pore pressure, boundary or transport integration in this fixture\"]}\n";
    record.flush();Require(bool(record),"Cannot write check JSON");
    std::cout<<"CACHE TEST PASSED, HG-region median speedup="<<olds[1]/news[1]<<'\n';return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
