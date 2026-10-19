// G3 device-operator fixture, not a coupled SPH trajectory or physical acceptance.
// Link real CPU/GPU objects and real JObject exceptions. The additional dense
// directed-pair oracle follows hourglass_check.py::endpoint_rate, not GPU code.
#include "JSphHourglassCpu.h"
#include "JSphHourglassGpu.h"
#include "JAppInfo.h"
#include "JException.h"
#include <cuda_runtime.h>
#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

JAppInfo AppInfo("HgGpuHourglassTest","G3-prepared","17-10-2026");
namespace{
constexpr unsigned First=40,Npb=2;
constexpr double Dt=1e-5,DoubleTolerance=1e-8,FloatTolerance=64.*FLT_EPSILON;
void Require(bool b,const std::string& s){if(!b)throw std::runtime_error(s);}
void Cuda(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
void Sync(){Cuda(cudaGetLastError());Cuda(cudaDeviceSynchronize());}
template<class T> bool Same(const T& a,const T& b){return std::memcmp(&a,&b,sizeof(T))==0;}
struct Metric{unsigned checks=0;double error=0,ratio=0;};
std::map<std::string,Metric> Metrics;
std::vector<std::string> Passed;
double CpuActualFloatNet=0,GpuActualFloatNet=0,ActualFloatNetDifference=0;
void Near(const std::string& name,double error,double limit){
  auto& m=Metrics[name];m.checks++;m.error=(std::max)(m.error,error);
  m.ratio=(std::max)(m.ratio,error/limit);
  std::ostringstream s;s<<std::setprecision(17)<<name<<" error="<<error<<" limit="<<limit;
  Require(std::isfinite(error)&&error<=limit,s.str());
}
void Scalar(const std::string& name,double a,double b){Near(name,std::abs(a-b),DoubleTolerance*(1+std::abs(a)));}
template<class T> void Exact(const T& a,const T& b,const std::string& s){Require(Same(a,b),"Cache bit mismatch: "+s);}
template<class T> struct Device{
  T* p=nullptr;unsigned n;
  explicit Device(unsigned count):n(count){Cuda(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*n));}
  ~Device(){if(p)cudaFree(p);}
  Device(const Device&)=delete;Device& operator=(const Device&)=delete;
  void Put(const std::vector<T>& v){Require(v.size()<=n,"Fixture device capacity");Cuda(cudaMemcpy(p,v.data(),sizeof(T)*v.size(),cudaMemcpyHostToDevice));}
  std::vector<T> Get(unsigned count)const{Require(count<=n,"Fixture download capacity");std::vector<T> v(count);Cuda(cudaMemcpy(v.data(),p,sizeof(T)*count,cudaMemcpyDeviceToHost));return v;}
};
struct State{
  unsigned nx,nz;double dp=.125,period,h=.1625,support=.325,mass=20,xi=.1,shear=1e5,bwen=-1;
  std::vector<unsigned> id;std::vector<typecode> code;std::vector<tdouble3> pos;
  std::vector<tfloat4> vel;std::vector<float> plastic;std::vector<tfloat3> ace;
  explicit State(unsigned x=10,unsigned z=20):nx(x),nz(z),period(x*dp){
    for(unsigned i=0;i<Npb;i++)Append(i,CODE_TYPE_FIXED,TDouble3(0),TFloat4(0,0,0,2000));
    for(unsigned j=0;j<nz;j++)for(unsigned i=0;i<nx;i++){
      const unsigned k=j*nx+i;
      Append(First+k,CODE_TYPE_FLUID,TDouble3((i+.5)*dp,0,(j+.5)*dp),
        TFloat4(float(1e-4*std::sin(.17*k)),0,float(2e-4*std::cos(.11*k)),float(2000+k%3)));
    }
    for(unsigned i=0;i<4;i++)Append(First+i,CODE_SetPeriodic(CODE_TYPE_FLUID),TDouble3(-10-i,0,20),TFloat4(1,0,2,2000));
    Append(7,CODE_TYPE_FIXED,TDouble3(-99),TFloat4(0,0,0,1));
    Append(8,CODE_TYPE_FLOATING,TDouble3(-98),TFloat4(0,0,0,1));
    Append(First,CODE_SetOutIgnore(CODE_TYPE_FLUID),TDouble3(-97),TFloat4(0,0,0,1));
  }
  unsigned Count()const{return nx*nz;}unsigned Size()const{return unsigned(id.size());}
  void Append(unsigned i,typecode c,tdouble3 x,tfloat4 v){id.push_back(i);code.push_back(c);pos.push_back(x);vel.push_back(v);plastic.push_back(0);ace.push_back(TFloat3(.125f,.0625f,-.25f));}
  unsigned Slot(unsigned native)const{for(unsigned p=Npb;p<Size();p++)if(CODE_IsNormal(code[p])&&CODE_IsFluid(code[p])&&id[p]==native)return p;throw std::runtime_error("Fixture missing ID");}
  void ResetAce(){std::fill(ace.begin(),ace.end(),TFloat3(.125f,.0625f,-.25f));}
  void Reverse(){const auto f=[&](auto& v){std::reverse(v.begin()+Npb,v.begin()+Npb+Count());};f(id);f(code);f(pos);f(vel);f(plastic);f(ace);}
};
template<class H> void Configure(H& h,const State& s,double xi=-1){h.Config(First,s.Count(),xi<0?s.xi:xi,s.mass,s.period,s.h,s.support,s.bwen,s.shear);}
struct Gpu{
  JSphHourglassGpu h;Device<unsigned> id;Device<typecode> code;Device<double2> xy;
  Device<double> z;Device<float4> vel;Device<float> plastic;Device<float3> ace;
  explicit Gpu(const State& s,bool cache):id(s.Size()+8),code(s.Size()+8),xy(s.Size()+8),z(s.Size()+8),vel(s.Size()+8),plastic(s.Size()+8),ace(s.Size()+8){Configure(h,s);h.SetRateCacheEnabled(cache);}
  void Put(const State& s){
    std::vector<double2> a;std::vector<double> b;std::vector<float4> v;std::vector<float3> q;
    for(unsigned p=0;p<s.Size();p++){a.push_back(make_double2(s.pos[p].x,s.pos[p].y));b.push_back(s.pos[p].z);v.push_back(make_float4(s.vel[p].x,s.vel[p].y,s.vel[p].z,s.vel[p].w));q.push_back(make_float3(s.ace[p].x,s.ace[p].y,s.ace[p].z));}
    id.Put(s.id);code.Put(s.code);xy.Put(a);z.Put(b);vel.Put(v);plastic.Put(s.plastic);ace.Put(q);
  }
  void Predictor(const State& s,double dt){Put(s);h.PredictorForce(s.Size(),Npb,id.p,code.p,xy.p,z.p,vel.p,plastic.p,ace.p,dt);Sync();}
  void Corrector(const State& s){Put(s);h.CorrectorForce(s.Size(),Npb,id.p,code.p,ace.p);Sync();}
  void Endpoint(const State& s,double dt){Put(s);h.CorrectorUpdate(s.Size(),Npb,id.p,code.p,xy.p,z.p,vel.p,plastic.p,dt);Sync();}
};
void Predictor(JSphHourglassCpu& h,State& s,double dt){h.PredictorForce(s.Size(),Npb,s.id.data(),s.code.data(),s.pos.data(),s.vel.data(),s.plastic.data(),s.ace.data(),dt);}
void Corrector(JSphHourglassCpu& h,State& s){h.CorrectorForce(s.Size(),Npb,s.id.data(),s.code.data(),s.ace.data());}
void Endpoint(JSphHourglassCpu& h,const State& s,double dt){h.CorrectorUpdate(s.Size(),Npb,s.id.data(),s.code.data(),s.pos.data(),s.vel.data(),s.plastic.data(),dt);}

// Dense directed O(N^2) mathematical reference: no cell list, GPU ordering,
// copied production pair traversal, or cached endpoint. The inverse is an
// explicit independent 2x2 matrix solve; accumulation is by ascending j.
struct Oracle{std::vector<tdouble3> rate;unsigned pairs=0;double form=0,power=0,netx=0,netz=0,sum=0;};
Oracle Dense(const State& s){
  const unsigned n=s.Count();Oracle o;o.rate.assign(n,TDouble3(0));
  struct N{double x,z,vx,vz,vol,g[4];};std::vector<N> a(n);
  for(unsigned i=0;i<n;i++){const unsigned p=s.Slot(First+i);a[i]={s.pos[p].x,s.pos[p].z,s.vel[p].x,s.vel[p].z,s.mass/s.vel[p].w,{0,0,0,0}};}
  const auto edge=[&](unsigned i,unsigned j,double& dx,double& dz){dx=a[i].x-a[j].x;dx-=s.period*std::floor(dx/s.period+.5);dz=a[i].z-a[j].z;const double rr=dx*dx+dz*dz;if(i==j||rr>=s.support*s.support)return 0.;Require(rr>0,"Oracle coincident");const double t=(std::max)(0.,1.-std::sqrt(rr)/(2*s.h));return -s.bwen/s.h*t*t*t;};
  for(unsigned i=0;i<n;i++){
    double m[4]={},b[4]={};
    for(unsigned j=0;j<n;j++)if(i!=j){double dx,dz;const double w=edge(i,j,dx,dz)*a[j].vol;const double d[2]={dx,dz},v[2]={a[i].vx-a[j].vx,a[i].vz-a[j].vz};
      for(unsigned r=0;r<2;r++)for(unsigned c=0;c<2;c++){m[2*r+c]+=w*d[r]*d[c];b[2*r+c]+=w*v[r]*d[c];}
      if(j>i && dx*dx+dz*dz<s.support*s.support)o.pairs++;
    }
    const double det=m[0]*m[3]-m[1]*m[2];Require(det>0,"Oracle rank");const double inv[4]={m[3]/det,-m[1]/det,-m[2]/det,m[0]/det};
    for(unsigned r=0;r<2;r++)for(unsigned c=0;c<2;c++)for(unsigned k=0;k<2;k++)a[i].g[2*r+c]+=b[2*r+k]*inv[2*k+c];
  }
  for(unsigned i=0;i<n;i++)for(unsigned j=0;j<n;j++)if(i!=j){double dx,dz;const double w=edge(i,j,dx,dz);if(!w)continue;
    const double v[2]={a[i].vx-a[j].vx,a[i].vz-a[j].vz},d[2]={dx,dz};double residual[2],ri[2],rj[2];
    for(unsigned r=0;r<2;r++){ri[r]=v[r];rj[r]=v[r];for(unsigned c=0;c<2;c++){ri[r]-=a[i].g[2*r+c]*d[c];rj[r]-=a[j].g[2*r+c]*d[c];}residual[r]=.5*(ri[r]+rj[r]);}
    const double beta=s.xi*s.shear*a[i].vol*a[j].vol*w;
    o.rate[i].x-=beta*residual[0]/s.mass;o.rate[i].z-=beta*residual[1]/s.mass;
    o.form+=.25*beta*(ri[0]*ri[0]+ri[1]*ri[1]);
  }
  for(unsigned i=0;i<n;i++){o.netx+=s.mass*o.rate[i].x;o.netz+=s.mass*o.rate[i].z;o.sum+=s.mass*std::hypot(o.rate[i].x,o.rate[i].z);o.power+=s.mass*(a[i].vx*o.rate[i].x+a[i].vz*o.rate[i].z);}
  return o;
}
void OracleCheck(const State& s,const JSphHourglassCpu& c,const JSphHourglassGpu& g){
  const auto o=Dense(s);double scale=0,ce=0,ge=0;
  for(unsigned i=0;i<s.Count();i++){auto a=c.GetRate(First+i),b=g.GetRate(First+i);scale=(std::max)({scale,std::abs(o.rate[i].x),std::abs(o.rate[i].z)});ce=(std::max)({ce,std::abs(a.x-o.rate[i].x),std::abs(a.z-o.rate[i].z)});ge=(std::max)({ge,std::abs(b.x-o.rate[i].x),std::abs(b.z-o.rate[i].z)});}
  Near("dense_cpu_rate",ce,DoubleTolerance*(1+scale));Near("dense_gpu_rate",ge,DoubleTolerance*(1+scale));
  Require(c.GetPairCount()==o.pairs&&g.GetPairCount()==o.pairs,"Canonical pairs differ from independent dense strict-support count");
  Near("dense_net_rate",std::hypot(o.netx,o.netz),1e-9*(1+o.sum));
  Near("dense_virtual_work",std::abs(o.power+2*o.form),1e-9*(1+std::abs(o.power)+2*o.form));
  Scalar("dense_gpu_form",o.form,g.GetRateInfo().form);Scalar("dense_gpu_power",o.power,g.GetRateInfo().ratepower);
}
void Compare(const JSphHourglassCpu& cpu,const Gpu& on,const Gpu& off,const State& cpuState,const State& before){
  double re=0,he=0,rs=0,hs=0;
  for(unsigned i=First;i<First+before.Count();i++){
    const auto cr=cpu.GetRate(i),ch=cpu.GetHistory(i),gr=on.h.GetRate(i),gh=on.h.GetHistory(i),fr=off.h.GetRate(i),fh=off.h.GetHistory(i);
    Exact(gr.x,fr.x,"rate.x");Exact(gr.z,fr.z,"rate.z");Exact(gh.x,fh.x,"history.x");Exact(gh.z,fh.z,"history.z");
    re=(std::max)({re,std::abs(cr.x-gr.x),std::abs(cr.z-gr.z)});he=(std::max)({he,std::abs(ch.x-gh.x),std::abs(ch.z-gh.z)});
    rs=(std::max)({rs,std::abs(cr.x),std::abs(cr.z)});hs=(std::max)({hs,std::abs(ch.x),std::abs(ch.z)});
  }
  Near("cpu_gpu_rate",re,DoubleTolerance*(1+rs));Near("cpu_gpu_history",he,DoubleTolerance*(1+hs));
  const auto ga=on.ace.Get(before.Size()),fa=off.ace.Get(before.Size());
  for(unsigned p=0;p<before.Size();p++){
    Exact(ga[p].x,fa[p].x,"Ace.x");Exact(ga[p].y,fa[p].y,"Ace.y");Exact(ga[p].z,fa[p].z,"Ace.z");
    const double cv[3]={cpuState.ace[p].x,cpuState.ace[p].y,cpuState.ace[p].z},gv[3]={ga[p].x,ga[p].y,ga[p].z};
    for(unsigned k=0;k<3;k++)Near("cpu_gpu_float_ace",std::abs(cv[k]-gv[k]),FloatTolerance*(std::max)(1.,std::abs(cv[k])));
    Exact(ga[p].y,before.ace[p].y,"Ace.y untouched");
    if(p<Npb||!CODE_IsNormal(before.code[p])||!CODE_IsFluid(before.code[p])){Exact(ga[p].x,before.ace[p].x,"non-native Ace.x");Exact(ga[p].z,before.ace[p].z,"non-native Ace.z");}
  }
  const auto& a=cpu.GetRateInfo();const auto& b=on.h.GetRateInfo();const auto& d=off.h.GetRateInfo();
#define RI(f) Scalar("RateInfo." #f,a.f,b.f);Exact(b.f,d.f,"RateInfo." #f)
  RI(netx);RI(netz);RI(condition);RI(skew);RI(form);RI(lambda);RI(tau);RI(ratepower);RI(workerror);RI(rmax);RI(sumrate);RI(meandxx);RI(rmsdxx);RI(meandiv);RI(rmsdiv);
#undef RI
  const auto& u=cpu.GetStats();const auto& v=on.h.GetStats();const auto& w=off.h.GetStats();
#define CNT(f) Require(u.f==v.f&&v.f==w.f,"Logical count " #f)
  CNT(forcecalls);CNT(predictorupdates);CNT(correctorupdates);CNT(ratecalls);CNT(predictorrates);CNT(endpointrates);CNT(firstpairs);CNT(minpairs);CNT(maxpairs);
#undef CNT
#define ST(f) Scalar("Stats." #f,u.f,v.f);Exact(v.f,w.f,"Stats." #f)
  ST(maxnetforce);ST(maxnetrate);ST(maxrelativeforce);ST(maxrelativerate);ST(maxhistory);ST(maxcondition);ST(maxpoweridentityerror);ST(maxskew);ST(spinbound);ST(maxtauratio);ST(mintau);ST(maxlambda);
#undef ST
  // This diagnostic is formed AFTER float Ace rounding, so its cross-backend
  // difference is reported, not incorrectly tested against a double-state
  // tolerance. The actual per-particle Ace gate above remains mandatory.
  Exact(v.maxactualnetforce,w.maxactualnetforce,"Stats.maxactualnetforce");
  CpuActualFloatNet=(std::max)(CpuActualFloatNet,u.maxactualnetforce);
  GpuActualFloatNet=(std::max)(GpuActualFloatNet,v.maxactualnetforce);
  ActualFloatNetDifference=(std::max)(ActualFloatNetDifference,std::abs(u.maxactualnetforce-v.maxactualnetforce));
  Require(v.ratecalculations+v.ratecachehits==v.ratecalls&&w.ratecalculations==w.ratecalls&&!w.ratecachehits,"Actual/logical cache counts");
  Require(cpu.GetPairCount()==on.h.GetPairCount()&&on.h.GetPairCount()==off.h.GetPairCount(),"Pair count mismatch");
}
void Mutate(State& s,const std::string& mode){
  const unsigned p=s.Slot(First+37);
  if(mode=="reorder")s.Reverse();
  else if(mode=="periodic"){s.pos[s.Count()+Npb]=TDouble3(999);s.vel[s.Count()+Npb]=TFloat4(99,0,99,1);s.plastic[s.Count()+Npb]=1;s.Append(First+37,CODE_SetPeriodic(CODE_TYPE_FLUID),TDouble3(-5,0,1),TFloat4(0,0,0,1));}
  else if(mode=="position_x")s.pos[p].x+=1e-6;
  else if(mode=="position_z")s.pos[p].z-=1e-6;
  else if(mode=="velocity_x")s.vel[p].x+=1e-6f;
  else if(mode=="velocity_z")s.vel[p].z-=1e-6f;
  else if(mode=="density")s.vel[p].w=std::nextafter(s.vel[p].w,std::numeric_limits<float>::infinity());
  else if(mode=="signed_zero")s.vel[s.Slot(First)].x=-0.f;
}
void Scenario(const std::string& name,State s){
  JSphHourglassCpu cpu;Configure(cpu,s);Gpu on(s,true),off(s,false);
  for(unsigned step=0;step<4;step++){
    if(step==1)Mutate(s,name);const double dt=name=="changed_dt"&&step%2?Dt*.5:Dt;
    s.ResetAce();State c=s;const unsigned hits=on.h.GetStats().ratecachehits;
    Predictor(cpu,c,dt);on.Predictor(s,dt);off.Predictor(s,dt);Compare(cpu,on,off,c,s);
    const bool invalidated=step==1&&(name=="position_x"||name=="position_z"||name=="velocity_x"||name=="velocity_z"||name=="density"||name=="signed_zero");
    Require(on.h.GetStats().ratecachehits-hits==unsigned(step>0&&!invalidated),"Unexpected cache decision: "+name);
    cpu.PredictorUpdate(dt);on.h.PredictorUpdate(dt);off.h.PredictorUpdate(dt);Sync();Compare(cpu,on,off,c,s);
    s.ResetAce();c=s;Corrector(cpu,c);on.Corrector(s);off.Corrector(s);Compare(cpu,on,off,c,s);
    if(name=="evolving_endpoint"){s.pos[s.Slot(First+23)].z-=.04;s.vel[s.Slot(First+17)].z+=1e-6f;}
    const unsigned calc=on.h.GetStats().ratecalculations;
    // Endpoint does not add acceleration; its fixture upload is deliberate and
    // compared against the identical untouched CPU state, not prior force Ace.
    c=s;Endpoint(cpu,c,dt);on.Endpoint(s,dt);off.Endpoint(s,dt);Compare(cpu,on,off,c,s);
    Require(on.h.GetStats().ratecalculations==calc+1,"Endpoint rate was cached");
    OracleCheck(s,cpu,on.h);
  }
  Configure(cpu,s);Configure(on.h,s);Configure(off.h,s);off.h.SetRateCacheEnabled(false);
  s.ResetAce();State c=s;Predictor(cpu,c,Dt);on.Predictor(s,Dt);off.Predictor(s,Dt);Compare(cpu,on,off,c,s);
  Require(on.h.GetStats().ratecalculations==1&&!on.h.GetStats().ratecachehits,"Config retained stale cache");
  Passed.push_back(name);std::cout<<"PASS "<<name<<'\n';
}
void Analytic(const std::string& name){
  State s;
  for(unsigned i=0;i<s.Count();i++){const unsigned p=s.Slot(First+i);s.vel[p].w=2000;
    if(name=="translation")s.vel[p]=TFloat4(.03125f,0,-.015625f,2000);
    else if(name=="periodic_z_affine")s.vel[p]=TFloat4(float(s.pos[p].z/1024.),0,float(-s.pos[p].z/2048.),2000);
    else s.vel[p]=TFloat4(0,0,(i%s.nx+i/s.nx)%2?.01f:-.01f,2000);
  }
  JSphHourglassCpu cpu;Configure(cpu,s);Gpu on(s,true),off(s,false);State c=s;
  Predictor(cpu,c,Dt);on.Predictor(s,Dt);off.Predictor(s,Dt);Compare(cpu,on,off,c,s);OracleCheck(s,cpu,on.h);
  if(name!="checkerboard")Near(name+"_zero_rate",on.h.GetRateInfo().rmax,1e-10);
  else Require(on.h.GetRateInfo().form>0&&on.h.GetRateInfo().ratepower<0,"Checkerboard does not oppose velocity residual");
  cpu.PredictorUpdate(Dt);on.h.PredictorUpdate(Dt);off.h.PredictorUpdate(Dt);s.ResetAce();c=s;
  Corrector(cpu,c);on.Corrector(s);off.Corrector(s);Compare(cpu,on,off,c,s);
  double netx=0,netz=0,sum=0,power=0;
  for(unsigned i=0;i<s.Count();i++){const auto a=on.h.GetHistory(First+i);const auto v=s.vel[s.Slot(First+i)];netx+=s.mass*a.x;netz+=s.mass*a.z;sum+=s.mass*std::hypot(a.x,a.z);power+=s.mass*(v.x*a.x+v.z*a.z);}
  Near("history_net",std::hypot(netx,netz),1e-9*(1+sum));if(name=="checkerboard")Require(power<0,"Checkerboard history power not restoring");
  Passed.push_back(name);std::cout<<"PASS "<<name<<'\n';
}
void BadState(State& s,const std::string& name){
  const unsigned p=s.Slot(First+37);const auto nan=std::numeric_limits<float>::quiet_NaN();
  if(name=="elastic")s.plastic[p]=1e-10f;
  else if(name=="plastic_nan")s.plastic[p]=nan;
  else if(name=="duplicate_id")s.id[p]=First;
  else if(name=="unexpected_id")s.id[p]=First+s.Count();
  else if(name=="missing_native")s.code[p]=CODE_SetOutIgnore(s.code[p]);
  else if(name=="bad_density")s.vel[p].w=0;
  else if(name=="density_nan")s.vel[p].w=nan;
  else if(name=="position_nan")s.pos[p].x=std::numeric_limits<double>::quiet_NaN();
  else if(name=="velocity_nan")s.vel[p].z=nan;
  else if(name=="coincident")s.pos[p]=s.pos[s.Slot(First)];
  else if(name=="rank")for(unsigned i=0;i<s.Count();i++){auto& x=s.pos[s.Slot(First+i)];x.x=(i+.5)*s.period/s.Count();x.z=0;}
}
template<class F> void Rejected(F f,const std::string& name,const std::string& expected=""){bool rejected=false;try{f();}catch(const JException& e){const std::string msg=e.what();Require(msg.find("HG")!=std::string::npos,"Unexpected non-HG exception: "+msg);Require(expected.empty()||msg.find(expected)!=std::string::npos,"Wrong HG guard for "+name+": "+msg);rejected=true;}Require(rejected,"Missing HG rejection: "+name);}
void Guards(const std::string& name){
  State s;JSphHourglassCpu cpu;Configure(cpu,s);Gpu gpu(s,true);
  // Populate an endpoint first: invalid inputs must not hide behind a cache hit.
  State c=s;Predictor(cpu,c,Dt);gpu.Predictor(s,Dt);cpu.PredictorUpdate(Dt);gpu.h.PredictorUpdate(Dt);Corrector(cpu,c);gpu.Corrector(s);Endpoint(cpu,s,Dt);gpu.Endpoint(s,Dt);
  BadState(s,name);double dt=Dt;
  if(name=="dt_guard_cached")dt=(std::max)(cpu.GetDtLimit(),gpu.h.GetDtLimit())*1.01;
  if(name=="dt_nan")dt=std::numeric_limits<double>::quiet_NaN();if(name=="dt_zero")dt=0;
  const std::string expected=name=="dt_guard_cached"?"dt":"";
  Rejected([&]{Predictor(cpu,s,dt);},"CPU "+name,expected);Rejected([&]{gpu.Predictor(s,dt);},"GPU "+name,expected);Sync();
  Passed.push_back("reject_"+name);std::cout<<"PASS reject "<<name<<'\n';
}
void PhaseGuards(){
  const std::vector<std::string> names={"update_before_force","corrector_before_update","endpoint_before_corrector","predictor_twice","wrong_predictor_dt","wrong_endpoint_dt"};
  for(const auto& name:names){State s;JSphHourglassCpu cpu;Configure(cpu,s);Gpu g(s,true);
    if(name!="update_before_force"&&name!="corrector_before_update"&&name!="endpoint_before_corrector"){State c=s;Predictor(cpu,c,Dt);g.Predictor(s,Dt);}
    if(name=="wrong_endpoint_dt"){cpu.PredictorUpdate(Dt);g.h.PredictorUpdate(Dt);Corrector(cpu,s);g.Corrector(s);}
    const auto cp=[&]{if(name=="update_before_force")cpu.PredictorUpdate(Dt);else if(name=="corrector_before_update")Corrector(cpu,s);else if(name=="endpoint_before_corrector")Endpoint(cpu,s,Dt);else if(name=="predictor_twice")Predictor(cpu,s,Dt);else if(name=="wrong_predictor_dt")cpu.PredictorUpdate(Dt*.5);else Endpoint(cpu,s,Dt*.5);};
    const auto gp=[&]{if(name=="update_before_force")g.h.PredictorUpdate(Dt);else if(name=="corrector_before_update")g.Corrector(s);else if(name=="endpoint_before_corrector")g.Endpoint(s,Dt);else if(name=="predictor_twice")g.Predictor(s,Dt);else if(name=="wrong_predictor_dt")g.h.PredictorUpdate(Dt*.5);else g.Endpoint(s,Dt*.5);};
    Rejected(cp,"CPU "+name);Rejected(gp,"GPU "+name);Passed.push_back("reject_"+name);
  }
  State s;JSphHourglassCpu cpu;Gpu g(s,true);Rejected([&]{Configure(cpu,s,0);},"CPU xi0");Rejected([&]{Configure(g.h,s,0);},"GPU xi0");Passed.push_back("reject_xi_zero");
}
void SpinGuard(){
  State s;s.shear=1;const double dt=.1;
  for(unsigned i=0;i<s.Count();i++){const unsigned p=s.Slot(First+i);s.vel[p]=TFloat4(float(s.pos[p].z/2),0,0,2000);}
  JSphHourglassCpu cpu;Configure(cpu,s);Gpu g(s,true);State c=s;
  Predictor(cpu,c,dt);g.Predictor(s,dt);cpu.PredictorUpdate(dt);g.h.PredictorUpdate(dt);
  Corrector(cpu,c);g.Corrector(s);
  // x-periodic-compatible shear has skew=.25; one endpoint accumulates .025
  // rad, exceeding the unchanged .01 guard. Low G keeps the dt guard separate.
  Rejected([&]{Endpoint(cpu,s,dt);},"CPU accumulated spin","spin");Rejected([&]{g.Endpoint(s,dt);},"GPU accumulated spin","spin");
  Passed.push_back("reject_accumulated_spin");
}
std::string Json(const std::string& s){std::string r="\"";for(char c:s){if(c=='\\'||c=='\"')r+='\\';if(c=='\n'){r+="\\n";continue;}if(c=='\r'){r+="\\r";continue;}r+=c;}return r+'\"';}
}
int main(int argc,char** argv){
  if(argc!=3||std::string(argv[1])!="--json"){std::cerr<<"Use hg_gpu_hourglass_test --json NEW_CHECK_JSON\n";return 2;}
  const std::filesystem::path path=argv[2];if(std::filesystem::exists(path)){std::cerr<<"Refusing existing result\n";return 2;}
  bool passed=false;std::string reason,device;
  try{
    AppInfo.LogInit("");Cuda(cudaSetDevice(0));cudaDeviceProp prop;Cuda(cudaGetDeviceProperties(&prop,0));device=prop.name;
    for(const std::string name:{"unchanged","reorder","periodic","position_x","position_z","velocity_x","velocity_z","density","signed_zero","changed_dt","evolving_endpoint"})Scenario(name,State());
    Scenario("multiblock_520",State(20,26));
    State seam;for(unsigned i=0;i<seam.Count();i++)seam.pos[seam.Slot(First+i)].x-=1.75*seam.period;Scenario("negative_x_periodic_seam",seam);
    State two(6,20);two.h=.15625;two.support=.3125;Require(std::floor(two.period/two.support)==2,"Fixture nx2 setup");Scenario("nx2_distinct_neighbor_columns",two);
    for(int k=-1;k<=1;k++){State edge;edge.h=.125;edge.support=k<0?std::nextafter(.25,0.):k>0?std::nextafter(.25,1.):.25;Scenario("strict_support_"+std::to_string(k),edge);}
    Analytic("translation");Analytic("periodic_z_affine");Analytic("checkerboard");
    for(const std::string name:{"elastic","plastic_nan","duplicate_id","unexpected_id","missing_native","bad_density","density_nan","position_nan","velocity_nan","coincident","rank","dt_guard_cached","dt_nan","dt_zero"})Guards(name);
    PhaseGuards();SpinGuard();Sync();passed=true;
  }catch(const std::exception& e){reason=e.what();std::cerr<<reason<<'\n';}catch(...){reason="Non-standard fixture exception";}
  std::ofstream f(path);f<<std::setprecision(17)<<"{\"passed\":"<<(passed?"true":"false")<<",\"status\":"<<Json(passed?"device_hg_operator_verified_not_physical_acceptance":"device_hg_operator_failed")<<",\"reason\":"<<Json(reason)<<",\"device\":"<<Json(device)
    <<",\"double_relative_plus_absolute_tolerance\":"<<DoubleTolerance<<",\"float_acceleration_epsilon_multiplier\":64,\"gpu_cache_required_max_ulp\":0,\"physical_acceptance\":false,\"passed_cases\":[";
  for(size_t i=0;i<Passed.size();i++)f<<(i?",":"")<<Json(Passed[i]);f<<"],\"metrics\":{";bool first=true;
  for(const auto& p:Metrics){f<<(first?"":",")<<Json(p.first)<<":{\"checks\":"<<p.second.checks<<",\"max_abs_error\":"<<p.second.error<<",\"max_error_over_limit\":"<<p.second.ratio<<'}';first=false;}
  f<<"},\"actual_float_net_force_cross_backend\":{\"cpu_max\":"<<CpuActualFloatNet<<",\"gpu_max\":"<<GpuActualFloatNet<<",\"max_difference\":"<<ActualFloatNetDifference<<",\"scope\":\"Reported diagnostic; actual float Ace uses the mandatory per-particle 64eps gate, GPU cache variants remain bit-identical\"}"
    <<",\"limitations\":[\"Real CPU/GPU operators, not main-loop integration or 2Tv verification\",\"Dense pair formula is independent of production cell/pair traversal\",\"Cache exactness is within GPU only; CPU/GPU tolerances fixed before execution\",\"Elastic small-rotation 2D x-periodic native particles only\",\"No solver boundary, pore-pressure, restart or GPU speedup claim\"]}\n";f.flush();if(!f){std::cerr<<"Result write failed\n";return 2;}
  return passed?0:1;
}
