// Actual CPU class versus a dense directed all-pair mathematical reference.
// No solver, CUDA, JObject stub, production-private access, or copied cell walk.
// Frozen-geometry energy is an isolated oscillator check, not u-pl acceptance.
#include "JSphHourglassCpu.h"
#include "JAppInfo.h"
#include "JException.h"
#include <algorithm>
#include <array>
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

JAppInfo AppInfo("UplHgCpuOracle","r1","03-11-2026");
namespace{
constexpr unsigned First=40,Npb=2;
constexpr double Dt=1e-5,DoubleTolerance=1e-8,WorkTolerance=1e-9;
constexpr double HistoryTolerance=1e-10,FloatTolerance=64.*FLT_EPSILON;
struct Metric{unsigned checks=0;double error=0,ratio=0;};
std::map<std::string,Metric> Metrics;
std::vector<std::string> Passed;
double EnergyMin=1,EnergyMax=1;
void Require(bool b,const std::string& text){if(!b)throw std::runtime_error(text);}
void Near(const std::string& name,double error,double limit){
  auto& m=Metrics[name];m.checks++;m.error=(std::max)(m.error,error);
  m.ratio=(std::max)(m.ratio,error/limit);
  std::ostringstream message;message<<std::setprecision(17)<<name<<" error="<<error<<" limit="<<limit;
  Require(std::isfinite(error)&&std::isfinite(limit)&&limit>0&&error<=limit,message.str());
}
void Scalar(const std::string& name,double actual,double expected){
  Near(name,std::abs(actual-expected),DoubleTolerance*(1+std::abs(expected)));
}
double Norm(const tdouble3& a){return std::hypot(a.x,a.z);}
struct State{
  unsigned nx=8,nz=10;double dp=.125,period=1,h=.1625,support=.325;
  double mass=20,rho0=2000,rhow=1000,xi=.1,shear=1e5,bwen=-1;
  std::vector<unsigned> id;std::vector<typecode> code;std::vector<tdouble3> pos;
  std::vector<tfloat4> vel;std::vector<float> plastic;std::vector<tfloat3> ace;
  std::vector<double> j;
  explicit State(bool periodic=true){
    if(!periodic)period=0;
    for(unsigned p=0;p<Npb;p++)Append(p,CODE_TYPE_FIXED,TDouble3(-99),TFloat4(0),0);
    for(unsigned iz=0;iz<nz;iz++)for(unsigned ix=0;ix<nx;ix++){
      const unsigned i=iz*nx+ix;
      Append(First+i,CODE_TYPE_FLUID,TDouble3((ix+.5)*dp,0,(iz+.5)*dp),
        TFloat4(float(.0125*std::sin(.37*i)),0,float(.025*std::cos(.29*i)),2000),1);
    }
    for(unsigned i=0;i<3;i++)Append(First+i,CODE_SetPeriodic(CODE_TYPE_FLUID),
      TDouble3(-5-i,0,7),TFloat4(99,0,-99,0),std::numeric_limits<double>::quiet_NaN());
    Append(First,CODE_SetOutIgnore(CODE_TYPE_FLUID),TDouble3(-97),TFloat4(0),0);
    Append(7,CODE_TYPE_FIXED,TDouble3(-98),TFloat4(0),0);
  }
  void Append(unsigned i,typecode c,tdouble3 x,tfloat4 v,double q){
    id.push_back(i);code.push_back(c);pos.push_back(x);vel.push_back(v);
    plastic.push_back(0);ace.push_back(TFloat3(0));j.push_back(q);
  }
  unsigned Count()const{return nx*nz;}unsigned Size()const{return unsigned(id.size());}
  unsigned Slot(unsigned i)const{
    for(unsigned p=Npb;p<Size();p++)if(CODE_IsNormal(code[p])&&CODE_IsFluid(code[p])&&id[p]==First+i)return p;
    throw std::runtime_error("Fixture native ID missing");
  }
  void J(const std::string& kind){
    for(unsigned i=0;i<Count();i++)j[Slot(i)]=(kind=="J1"?1:kind=="uniform"?.8:.75+.04*((3*(i%nx)+5*(i/nx))%13));
  }
  void Velocity(const std::string& kind){
    for(unsigned i=0;i<Count();i++){
      const unsigned p=Slot(i);const double x=pos[p].x,z=pos[p].z;float vx=0,vz=0;
      if(kind=="translation"){vx=.03125f;vz=-.015625f;}
      else if(kind=="compression"){vx=float(-x/1024.);vz=float(-z/2048.);}
      else if(kind=="shear"){vx=float(z/1024.);vz=float(x/2048.);}
      else if(kind=="rotation"){vx=float(-z/2048.);vz=float(x/2048.);}
      else if(kind=="periodic_affine"){vx=float(z/1024.);vz=float(-z/2048.);}
      else if(kind=="alternating_column")vz=(i%nx)%2?.03125f:-.03125f;
      else if(kind=="checkerboard")vz=((i%nx+i/nx)%2?.03125f:-.03125f);
      else{vx=float(.0125*std::sin(.37*i));vz=float(.025*std::cos(.29*i));}
      vel[p]=TFloat4(vx,0,vz,2000);
    }
  }
  void ResetAce(){std::fill(ace.begin(),ace.end(),TFloat3(0));}
  void Reverse(){
    const auto reverse=[&](auto& v){std::reverse(v.begin()+Npb,v.begin()+Npb+Count());};
    reverse(id);reverse(code);reverse(pos);reverse(vel);reverse(plastic);reverse(ace);reverse(j);
  }
};
// Deliberately derive inertia as V*rho, rather than the production expanded sum.
double Inertia(const State& s,unsigned i){const double j=s.j[s.Slot(i)];return (s.mass/s.rho0*j)*(s.rhow+(s.rho0-s.rhow)/j);}
void Configure(JSphHourglassCpu& h,const State& s){h.Config(First,s.Count(),s.xi,s.mass,s.period,s.h,s.support,s.bwen,s.shear,s.rho0,s.rhow);}
void Predictor(JSphHourglassCpu& h,State& s,double dt=Dt){h.PredictorForce(s.Size(),Npb,s.id.data(),s.code.data(),s.pos.data(),s.vel.data(),s.plastic.data(),s.ace.data(),dt,s.j.data());}
void Corrector(JSphHourglassCpu& h,State& s){h.CorrectorForce(s.Size(),Npb,s.id.data(),s.code.data(),s.ace.data(),s.j.data());}
void Endpoint(JSphHourglassCpu& h,const State& s,double dt=Dt){h.CorrectorUpdate(s.Size(),Npb,s.id.data(),s.code.data(),s.pos.data(),s.vel.data(),s.plastic.data(),dt,s.j.data());}
struct Oracle{
  std::vector<tdouble3> rate;unsigned pairs=0;double form=0,power=0,netx=0,netz=0,sum=0,lambda=0,rayleigh=0;
};
Oracle Dense(const State& s){
  const unsigned count=s.Count();Oracle result;result.rate.assign(count,TDouble3(0));
  struct Node{double x,z,v[2],vol,mass,g[4]={};};std::vector<Node> node(count);
  for(unsigned i=0;i<count;i++){
    const unsigned p=s.Slot(i);node[i]={s.pos[p].x,s.pos[p].z,{s.vel[p].x,s.vel[p].z},s.mass/s.rho0*s.j[p],Inertia(s,i),{0,0,0,0}};
  }
  const auto weight=[&](unsigned i,unsigned k,double d[2]){
    d[0]=node[i].x-node[k].x;d[1]=node[i].z-node[k].z;
    if(s.period)d[0]-=s.period*std::floor(d[0]/s.period+.5);
    const double rr=d[0]*d[0]+d[1]*d[1];
    if(i==k||rr>=s.support*s.support)return 0.;
    Require(rr>0,"Oracle coincident particles");const double t=(std::max)(0.,1-std::sqrt(rr)/(2*s.h));
    return -s.bwen/s.h*t*t*t;
  };
  // Directed all-pair gather by ascending native IDs and generic matrix products.
  for(unsigned i=0;i<count;i++){
    double moment[4]={},rhs[4]={};
    for(unsigned k=0;k<count;k++)if(k!=i){
      double d[2];const double w=weight(i,k,d)*node[k].vol;
      for(unsigned r=0;r<2;r++)for(unsigned c=0;c<2;c++){
        moment[2*r+c]+=w*d[r]*d[c];rhs[2*r+c]+=w*(node[i].v[r]-node[k].v[r])*d[c];
      }
      if(k>i&&w>0)result.pairs++;
    }
    const double determinant=moment[0]*moment[3]-moment[1]*moment[2];
    Require(std::isfinite(determinant)&&determinant>0,"Oracle singular moment");
    const double inverse[4]={moment[3]/determinant,-moment[1]/determinant,-moment[2]/determinant,moment[0]/determinant};
    for(unsigned r=0;r<2;r++)for(unsigned c=0;c<2;c++)for(unsigned k=0;k<2;k++)node[i].g[2*r+c]+=rhs[2*r+k]*inverse[2*k+c];
  }
  for(unsigned i=0;i<count;i++){
    double degree=0;
    for(unsigned k=0;k<count;k++)if(k!=i){
      double d[2];const double w=weight(i,k,d);if(!w)continue;
      const double beta=s.xi*s.shear*node[i].vol*node[k].vol*w;degree+=beta;
      double ri[2],rk[2];
      for(unsigned r=0;r<2;r++){
        ri[r]=rk[r]=node[i].v[r]-node[k].v[r];
        for(unsigned c=0;c<2;c++){ri[r]-=node[i].g[2*r+c]*d[c];rk[r]-=node[k].g[2*r+c]*d[c];}
      }
      result.rate[i].x-=beta*(ri[0]+rk[0])/(2*s.mass);result.rate[i].z-=beta*(ri[1]+rk[1])/(2*s.mass);
      result.form+=.25*beta*(ri[0]*ri[0]+ri[1]*ri[1]);
    }
    result.lambda=(std::max)(result.lambda,2*degree/node[i].mass);
  }
  double inertiaNorm=0;
  for(unsigned i=0;i<count;i++){
    result.netx+=s.mass*result.rate[i].x;result.netz+=s.mass*result.rate[i].z;
    result.sum+=s.mass*Norm(result.rate[i]);
    result.power+=s.mass*(node[i].v[0]*result.rate[i].x+node[i].v[1]*result.rate[i].z);
    inertiaNorm+=node[i].mass*(node[i].v[0]*node[i].v[0]+node[i].v[1]*node[i].v[1]);
  }
  result.rayleigh=(inertiaNorm>0?-result.power/inertiaNorm:0);
  return result;
}
void OracleCheck(const State& s,const JSphHourglassCpu& h,bool null=false){
  const auto o=Dense(s);double scale=0,error=0,actualmax=0;
  for(unsigned i=0;i<s.Count();i++){
    const auto a=h.GetRate(First+i);scale=(std::max)(scale,Norm(o.rate[i]));
    error=(std::max)(error,std::hypot(a.x-o.rate[i].x,a.z-o.rate[i].z));actualmax=(std::max)(actualmax,Norm(a));
  }
  Near("allpair_rate",error,DoubleTolerance*(1+scale));
  Require(h.GetPairCount()==o.pairs,"Independent strict-support pair count differs");
  Scalar("allpair_form",h.GetRateInfo().form,o.form);Scalar("allpair_power",h.GetRateInfo().ratepower,o.power);
  Scalar("generalized_lambda",h.GetRateInfo().lambda,o.lambda);Scalar("tau",h.GetRateInfo().tau,1/std::sqrt(o.lambda));
  Near("allpair_net_pair_force_rate",std::hypot(o.netx,o.netz),WorkTolerance*(1+o.sum));
  Near("allpair_virtual_work",std::abs(o.power+2*o.form),WorkTolerance*(1+std::abs(o.power)+2*o.form));
  Near("class_virtual_work",h.GetRateInfo().workerror,WorkTolerance*(1+std::abs(o.power)+2*o.form));
  Require(o.form>=0&&o.rayleigh>=-1e-12&&o.rayleigh<=o.lambda*(1+1e-10),"Generalized-inertia Rayleigh bound failed");
  if(null)Near("affine_null",actualmax,1e-12);
  else Require(o.form>1e-10&&actualmax>1e-8,"Manufactured non-affine mode has no response");
}
void HistoryCheck(const JSphHourglassCpu& h,const std::vector<tdouble3>& expected){
  double error=0,scale=0,netx=0,netz=0,sum=0;
  for(unsigned i=0;i<expected.size();i++){
    const auto a=h.GetHistory(First+i);error=(std::max)(error,std::hypot(a.x-expected[i].x,a.z-expected[i].z));
    scale=(std::max)(scale,Norm(expected[i]));netx+=20*a.x;netz+=20*a.z;sum+=20*Norm(a);
  }
  Near("reference_force_history",error,HistoryTolerance*(std::max)(1e-15,scale));
  Near("reference_history_net_force",std::hypot(netx,netz),1e-10*(std::max)(1e-15,sum));
}
// Zero base acceleration makes the float gate relative to the HG increment;
// an absolute +1 tolerance would hide the deliberately small half-stage force.
void ForceCheck(const State& before,const State& after,const JSphHourglassCpu& h){
  // Called only for the successive forces of HistoryStages' single object.
  static double maximumActual=0,maximumForceSum=0;
  double netx=0,netz=0,sum=0;
  for(unsigned i=0;i<before.Count();i++){
    const unsigned p=before.Slot(i),q=after.Slot(i);const auto history=h.GetHistory(First+i);
    const double mass=Inertia(after,i),factor=after.mass/mass;
    const double expected[2]={factor*history.x,factor*history.z};
    const double actual[2]={double(after.ace[q].x)-before.ace[p].x,double(after.ace[q].z)-before.ace[p].z};
    for(unsigned c=0;c<2;c++)Near("current_stage_float_acceleration",std::abs(actual[c]-expected[c]),FloatTolerance*(std::max)(1e-30,std::abs(expected[c])));
    Require(after.ace[q].y==before.ace[p].y,"HG modified transverse acceleration");
    netx+=mass*actual[0];netz+=mass*actual[1];sum+=mass*std::hypot(actual[0],actual[1]);
  }
  Near("current_inertia_float_net_force",std::hypot(netx,netz),FloatTolerance*(std::max)(1e-30,sum));
  maximumActual=(std::max)(maximumActual,std::hypot(netx,netz));maximumForceSum=(std::max)(maximumForceSum,sum);
  Near("actual_float_force_diagnostic",std::abs(h.GetStats().maxactualnetforce-maximumActual),
    64*DBL_EPSILON*(std::max)(1e-30,maximumForceSum));
  for(unsigned p=0;p<before.Size();p++)if(!(p>=Npb&&CODE_IsNormal(before.code[p])&&CODE_IsFluid(before.code[p])))
    Require(std::memcmp(&before.ace[p],&after.ace[p],sizeof(tfloat3))==0,"HG modified a non-native slot");
}
void Basic(){
  for(const std::string material:{"J1","uniform","nonuniform"}){
    for(const bool periodic:{false,true}){
      const std::vector<std::string> modes=periodic?std::vector<std::string>{"translation","periodic_affine","alternating_column","checkerboard","random"}:
        std::vector<std::string>{"translation","compression","shear","rotation","alternating_column","checkerboard","random"};
      for(const auto& mode:modes){State s(periodic);s.J(material);s.Velocity(mode);JSphHourglassCpu h;Configure(h,s);Predictor(h,s);
        OracleCheck(s,h,mode=="translation"||mode=="periodic_affine"||mode=="compression"||mode=="shear"||mode=="rotation");
        Passed.push_back(material+"_"+(periodic?"periodic_":"bounded_")+mode);
      }
    }
  }
}
void HistoryStages(){
  State start;start.J("nonuniform");start.Velocity("alternating_column");const auto initial=Dense(start);
  JSphHourglassCpu h;Configure(h,start);Predictor(h,start);h.PredictorUpdate(Dt);
  std::vector<tdouble3> expected(start.Count(),TDouble3(0));
  for(unsigned i=0;i<start.Count();i++){expected[i].x=.5*Dt*initial.rate[i].x;expected[i].z=.5*Dt*initial.rate[i].z;}
  HistoryCheck(h,expected);State half=start;
  // Destroy the previous call's contents; the half force receives another array.
  std::fill(start.j.begin(),start.j.end(),std::numeric_limits<double>::quiet_NaN());
  for(unsigned i=0;i<half.Count();i++)half.j[half.Slot(i)]=.64+.065*(i%11);
  half.Reverse();half.ResetAce();const State before=half;const auto logical=h.GetStats().ratecalls;
  Corrector(h,half);Require(h.GetStats().ratecalls==logical,"Corrector force recalculated a rate");
  ForceCheck(before,half,h);HistoryCheck(h,expected);
  State end=half;end.J("uniform");end.Velocity("random");
  for(unsigned i=0;i<end.Count();i++)end.pos[end.Slot(i)].z+=.0002*std::sin(.31*i);
  const auto final=Dense(end);Endpoint(h,end);OracleCheck(end,h);
  for(unsigned i=0;i<end.Count();i++){expected[i].x+=.5*Dt*final.rate[i].x;expected[i].z+=.5*Dt*final.rate[i].z;}
  HistoryCheck(h,expected);
  const auto calculations=h.GetStats().ratecalculations,hits=h.GetStats().ratecachehits;
  // Reorder every input including J; corrupt only the ignored periodic copies.
  end.Reverse();end.ResetAce();
  for(unsigned p=Npb;p<end.Size();p++)if(CODE_IsPeriodic(end.code[p])){end.j[p]=-99;end.pos[p]=TDouble3(999);end.vel[p]=TFloat4(999);end.plastic[p]=1;}
  const State nextbefore=end;Predictor(h,end);
  Require(h.GetStats().ratecachehits==hits+1&&h.GetStats().ratecalculations==calculations,"Reorder/copy-only input failed exact endpoint reuse");
  ForceCheck(nextbefore,end,h);HistoryCheck(h,expected);OracleCheck(end,h);
  Passed.push_back("nonzero_history_changed_halfJ_separate_array_reorder_endpoint_cache");
}
void OneUlpCache(){
  State s;s.J("uniform");s.Velocity("alternating_column");const unsigned p=s.Slot(13);
  double lower=.8,upper=0;bool collision=false;
  for(unsigned k=0;k<2048;k++){
    upper=std::nextafter(lower,1.);if(s.mass/s.rho0*lower==s.mass/s.rho0*upper){collision=true;break;}lower=upper;
  }
  Require(collision,"Fixture cannot find adjacent J values with equal rounded volume");s.j[p]=lower;
  JSphHourglassCpu h;Configure(h,s);Predictor(h,s);h.PredictorUpdate(Dt);Corrector(h,s);Endpoint(h,s);
  const auto calculated=h.GetStats().ratecalculations,hits=h.GetStats().ratecachehits;s.j[p]=upper;s.ResetAce();Predictor(h,s);
  Require(h.GetStats().ratecalculations==calculated+1&&h.GetStats().ratecachehits==hits,"One-ULP J change hidden by equal rounded volume");
  OracleCheck(s,h);Passed.push_back("one_ulp_J_invalidates_even_when_volume_bits_equal");
}
template<class F> void Reject(const std::string& name,F action,const std::string& text=""){
  bool rejected=false;try{action();}catch(const JException& e){const std::string message=e.what();Require(message.find("HG")!=std::string::npos,"Unexpected non-HG exception");
    Require(text.empty()||message.find(text)!=std::string::npos,"Wrong rejection for "+name+": "+message);rejected=true;}
  Require(rejected,"Missing HG rejection: "+name);Passed.push_back("reject_"+name);
}
void Guards(){
  for(const std::string name:{"J_zero","J_negative","J_nan","J_infinite","plastic","plastic_nan","missing_native","duplicate_native","unexpected_native","position_nan","velocity_nan","coincident","rank","dt_cached","dt_nan","dt_zero","missing_J"}){
    State s;s.J("nonuniform");s.Velocity("alternating_column");JSphHourglassCpu h;Configure(h,s);
    Predictor(h,s);h.PredictorUpdate(Dt);Corrector(h,s);Endpoint(h,s);const unsigned p=s.Slot(13);double dt=Dt;
    if(name=="J_zero")s.j[p]=0;else if(name=="J_negative")s.j[p]=-1;
    else if(name=="J_nan")s.j[p]=std::numeric_limits<double>::quiet_NaN();else if(name=="J_infinite")s.j[p]=std::numeric_limits<double>::infinity();
    else if(name=="plastic")s.plastic[p]=1e-10f;else if(name=="plastic_nan")s.plastic[p]=std::numeric_limits<float>::quiet_NaN();
    else if(name=="missing_native")s.code[p]=CODE_SetOutIgnore(s.code[p]);else if(name=="duplicate_native")s.id[p]=First;
    else if(name=="unexpected_native")s.id[p]=First+s.Count();else if(name=="position_nan")s.pos[p].x=std::numeric_limits<double>::quiet_NaN();
    else if(name=="velocity_nan")s.vel[p].z=std::numeric_limits<float>::quiet_NaN();else if(name=="coincident")s.pos[p]=s.pos[s.Slot(0)];
    else if(name=="rank")for(unsigned i=0;i<s.Count();i++)s.pos[s.Slot(i)]=TDouble3((i+.5)*s.period/s.Count(),0,0);
    else if(name=="dt_cached")dt=h.GetDtLimit()*1.01;else if(name=="dt_nan")dt=std::numeric_limits<double>::quiet_NaN();else if(name=="dt_zero")dt=0;
    Reject(name,[&]{if(name=="missing_J")h.PredictorForce(s.Size(),Npb,s.id.data(),s.code.data(),s.pos.data(),s.vel.data(),s.plastic.data(),s.ace.data(),dt);else Predictor(h,s,dt);});
  }
  for(const std::string name:{"update_before_force","corrector_before_update","endpoint_before_corrector","predictor_twice","wrong_predictor_dt","wrong_endpoint_dt","missing_half_J","bad_half_J","missing_endpoint_J"}){
    State s;s.J("nonuniform");JSphHourglassCpu h;Configure(h,s);
    if(name!="update_before_force"&&name!="corrector_before_update"&&name!="endpoint_before_corrector")Predictor(h,s);
    if(name=="wrong_endpoint_dt"||name=="missing_endpoint_J"){h.PredictorUpdate(Dt);Corrector(h,s);}
    else if(name=="missing_half_J"||name=="bad_half_J")h.PredictorUpdate(Dt);
    Reject(name,[&]{
      if(name=="update_before_force")h.PredictorUpdate(Dt);else if(name=="corrector_before_update")Corrector(h,s);
      else if(name=="endpoint_before_corrector")Endpoint(h,s);else if(name=="predictor_twice")Predictor(h,s);
      else if(name=="wrong_predictor_dt")h.PredictorUpdate(Dt*.5);else if(name=="wrong_endpoint_dt")Endpoint(h,s,Dt*.5);
      else if(name=="missing_half_J")h.CorrectorForce(s.Size(),Npb,s.id.data(),s.code.data(),s.ace.data());
      else if(name=="bad_half_J"){s.j[s.Slot(13)]=0;Corrector(h,s);}
      else h.CorrectorUpdate(s.Size(),Npb,s.id.data(),s.code.data(),s.pos.data(),s.vel.data(),s.plastic.data(),Dt);
    });
  }
  for(const std::string name:{"bad_rho0","bad_rhow","xi_zero"}){State s;JSphHourglassCpu h;Reject(name,[&]{h.Config(First,s.Count(),name=="xi_zero"?0:s.xi,s.mass,s.period,s.h,s.support,s.bwen,s.shear,name=="bad_rho0"?-1:s.rho0,name=="bad_rhow"?-1:s.rhow);});}
  State spin;spin.shear=1;spin.Velocity("periodic_affine");
  for(unsigned i=0;i<spin.Count();i++){const unsigned p=spin.Slot(i);spin.vel[p]=TFloat4(float(spin.pos[p].z/2),0,0,2000);}
  JSphHourglassCpu h;Configure(h,spin);Predictor(h,spin,.1);h.PredictorUpdate(.1);Corrector(h,spin);
  Reject("accumulated_spin",[&]{Endpoint(h,spin,.1);},"spin");
}
void FrozenEnergy(){
  State s(false);s.J("nonuniform");JSphHourglassCpu h;
  std::vector<tdouble3> q(s.Count(),TDouble3(0)),v=q,a=q;
  for(unsigned i=0;i<s.Count();i++)q[i].z=((i%s.nx+i/s.nx)%2?1:-1)*1e-4;
  const auto apply=[&](double dt){
    for(unsigned i=0;i<s.Count();i++){const unsigned p=s.Slot(i);s.vel[p]=TFloat4(float(q[i].x),0,float(q[i].z),2000);}
    s.ResetAce();Configure(h,s);Predictor(h,s,dt);const auto oracle=Dense(s);
    double error=0,scale=0;
    for(unsigned i=0;i<s.Count();i++){const auto rate=h.GetRate(First+i);a[i]=TDouble3(s.mass*rate.x/Inertia(s,i),0,s.mass*rate.z/Inertia(s,i));
      error=(std::max)(error,std::hypot(rate.x-oracle.rate[i].x,rate.z-oracle.rate[i].z));scale=(std::max)(scale,Norm(oracle.rate[i]));}
    Near("oscillator_allpair_rate",error,DoubleTolerance*(1+scale));
    Scalar("oscillator_allpair_potential",h.GetRateInfo().form,oracle.form);
  };
  apply(Dt);const double dt=.02*h.GetRateInfo().tau,initial=h.GetRateInfo().form;Require(initial>0,"Oscillator initial potential is zero");
  for(unsigned step=0;step<=512;step++){
    double kinetic=0;for(unsigned i=0;i<s.Count();i++)kinetic+=.5*Inertia(s,i)*(v[i].x*v[i].x+v[i].z*v[i].z);
    const double ratio=(kinetic+h.GetRateInfo().form)/initial;EnergyMin=(std::min)(EnergyMin,ratio);EnergyMax=(std::max)(EnergyMax,ratio);
    Near("frozen_oscillator_energy_ratio",std::abs(ratio-1),.001);if(step==512)break;
    for(unsigned i=0;i<s.Count();i++){v[i].x+=.5*dt*a[i].x;v[i].z+=.5*dt*a[i].z;q[i].x+=dt*v[i].x;q[i].z+=dt*v[i].z;}
    apply(dt);for(unsigned i=0;i<s.Count();i++){v[i].x+=.5*dt*a[i].x;v[i].z+=.5*dt*a[i].z;}
  }
  Passed.push_back("frozen_nonuniform_J_generalized_inertia_oscillator_512_steps");
}
std::string Json(const std::string& s){std::string r="\"";for(char c:s){if(c=='\\'||c=='\"')r+='\\';if(c=='\n'){r+="\\n";continue;}if(c=='\r'){r+="\\r";continue;}r+=c;}return r+'\"';}
}
int main(int argc,char** argv){
  if(argc!=3||std::string(argv[1])!="--json"||std::filesystem::exists(argv[2])){std::cerr<<"Use upl_hg_cpu_oracle_r2 --json NEW_CHECK_JSON\n";return 2;}
  bool passed=false;std::string reason;
  try{Basic();HistoryStages();OneUlpCache();Guards();FrozenEnergy();passed=true;}
  catch(const std::exception& e){reason=e.what();std::cerr<<reason<<'\n';}catch(...){reason="Non-standard fixture exception";}
  std::ofstream f(argv[2]);f<<std::setprecision(17)<<"{\"passed\":"<<(passed?"true":"false")<<",\"status\":"<<Json(passed?"actual_CPU_operator_verified_not_coupled_acceptance":"actual_CPU_operator_failed")<<",\"reason\":"<<Json(reason)
    <<",\"double_tolerance\":"<<DoubleTolerance<<",\"work_tolerance\":"<<WorkTolerance<<",\"history_relative_tolerance\":"<<HistoryTolerance<<",\"float_epsilon_multiplier\":64,\"physical_acceptance\":false,\"solver_run\":false,\"passed_cases\":[";
  for(size_t i=0;i<Passed.size();i++)f<<(i?",":"")<<Json(Passed[i]);f<<"],\"metrics\":{";bool first=true;
  for(const auto& p:Metrics){f<<(first?"":",")<<Json(p.first)<<":{\"checks\":"<<p.second.checks<<",\"max_abs_error\":"<<p.second.error<<",\"max_error_over_limit\":"<<p.second.ratio<<'}';first=false;}
  f<<"},\"frozen_oscillator\":{\"steps\":512,\"dt_over_tau\":0.02,\"min_energy_ratio\":"<<EnergyMin<<",\"max_energy_ratio\":"<<EnergyMax<<"},\"limitations\":[\"No public dynamic+HG enablement, solver trajectory, GPU, wall, Darcy, load, restart or physical validation\",\"Frozen-J/geometry isolated oscillator and instantaneous internal-force balance do not prove evolving/open-mass coupled energy or momentum conservation\",\"The Rayleigh checks sample manufactured vectors; the analytic projection argument supplies the generalized stiffness bound\",\"The separate legacy frozen-class bit comparison is required; J1 dynamic/legacy bit identity is not claimed\",\"The HG class validates positive J/inertia; the caller retains the saturated J domain guard\"]}\n";
  f.flush();if(!f){std::cerr<<"Cannot write check record\n";return 2;}std::cout<<(passed?"PASS":"FAIL")<<" actual CPU single-J HG oracle: "<<Passed.size()<<" cases\n";return passed?0:1;
}
