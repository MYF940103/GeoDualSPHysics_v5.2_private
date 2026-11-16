// Author-only P1 component. No solver, native reader or process launch.
// Compile against the final-A frozen DualSphDef/HG headers and the actual
// upl_tpi_cpu_r1.h. Root independently admits compilation and execution.
#include "upl_tpi_cpu_r1.h"
#include "JSphHourglassCpu.h"
#include <cerrno>
#include <direct.h>
#include <functional>
#include <io.h>
#include <iostream>
#include <limits>
#include <new>
#include <sstream>
#include <utility>

namespace upl_tpi_cpu_r1 { State state; }
namespace component {
namespace tpi=upl_tpi_cpu_r1;
static_assert(sizeof(tfloat3)==3*sizeof(float),"Fixture float acceleration contains unexpected padding");
unsigned assertions=0,expectedRejections=0,fixtures=0;
std::vector<std::string> fixtureNames;
std::string root;
void Check(bool condition,const std::string& label){
  assertions++;if(!condition)throw std::runtime_error("COMPONENT ASSERTION: "+label);
}
template<class Fn> void Reject(Fn fn,const std::string& label,const std::string& required=""){
  bool rejected=false;std::string message;
  try{fn();}catch(const std::exception& e){rejected=true;message=e.what();}
  Check(rejected,label+" must reject");
  if(!required.empty())Check(message.find(required)!=std::string::npos,label+" has the expected first cause: "+message);
  expectedRejections++;
}
void FreshDirectory(const std::string& path){
  Check(_access(path.c_str(),0)!=0,"new directory must not exist: "+path);
  Check(_mkdir(path.c_str())==0,"new directory creation: "+path);
}
void ResetState(){tpi::state.~State();new(&tpi::state)tpi::State();}
template<class T> void SameBits(const T& a,const T& b,const std::string& label){Check(tpi::Bits(a,b),label);}

struct Frame{
  unsigned npb=1;
  std::vector<unsigned> id,fs;
  std::vector<typecode> code;
  std::vector<tdouble3> pos;
  std::vector<tfloat4> vel;
  std::vector<tsymatrix3d> sigma;
  std::vector<float> p,p0,kappa;
  std::vector<double> j,theta;
  Frame(){
    id={3,11,29,44,29};
    code={typecode(CODE_TYPE_FIXED),typecode(CODE_TYPE_FLUID),typecode(CODE_TYPE_FLUID),typecode(CODE_TYPE_FLUID),typecode(CODE_SetPeriodic(CODE_TYPE_FLUID))};
    fs={0,0,0,0,0};
    for(unsigned a=0;a<id.size();a++){
      pos.push_back(TDouble3(.1*a,0.,.2*a));vel.push_back(TFloat4(.01f*a,0.f,-.02f*a,2100.f));
      sigma.push_back(TSymMatrix3d(-10.-a,.125,.25,-20.-a,.5,-30.-a));
      p.push_back(id[a]==11?5.f:(id[a]==29?-2.25f:(id[a]==44?1.125f:0.f)));
      p0.push_back(float(id[a])*.125f);kappa.push_back(0.f);j.push_back(id[a]==11?.8:(id[a]==29?1.125:1.01));theta.push_back(.001*(a+1));
    }
  }
  unsigned N()const{return unsigned(id.size());}
  unsigned Slot(unsigned k)const{
    for(unsigned a=0;a<N();a++)if(id[a]==k&&CODE_IsNormal(code[a]))return a;
    throw std::runtime_error("fixture native owner absent");
  }
  template<class V> static V Reordered(const V& x,const std::vector<unsigned>& order){V y;for(unsigned a:order)y.push_back(x[a]);return y;}
  void Reorder(const std::vector<unsigned>& order){
    Check(order.size()==id.size(),"fixture permutation length");
    id=Reordered(id,order);fs=Reordered(fs,order);code=Reordered(code,order);pos=Reordered(pos,order);vel=Reordered(vel,order);sigma=Reordered(sigma,order);
    p=Reordered(p,order);p0=Reordered(p0,order);kappa=Reordered(kappa,order);j=Reordered(j,order);theta=Reordered(theta,order);
  }
};
struct Fixture{
  int owner=0;
  Frame f;
  std::string path;
  const double dt=.015625; // Exactly binary fixture clock; not a solver dt.
  const double initialTime=.125;
  const unsigned long long initialStep=7;
  Fixture(const std::string& name){
    ResetState();path=root+"/"+name;FreshDirectory(path);path+="/";
    fixtureNames.push_back(name);fixtures++;
    tpi::Init(&owner,path,f.N(),f.id.data(),f.code.data(),f.p.data(),f.p0.data(),f.j.data(),f.kappa.data(),initialTime,initialStep,dt);
  }
  template<class Pred> void Begin(Pred pred){
    const double time=tpi::state.lastEnd;const auto step=initialStep+tpi::state.commits;
    tpi::Begin(&owner,f.N(),f.id.data(),f.code.data(),f.p.data(),f.j.data(),time,step,dt,pred);
    for(unsigned a=f.npb;a<f.N();a++)if(CODE_IsFluid(f.code[a])){
      f.p[a]=pred(a)?0.f:tpi::Half(f.id[a]);
      if(CODE_IsNormal(f.code[a]))tpi::HalfActual(f.id[a],f.p[a]);
    }
  }
  void Begin(){Begin([](unsigned){return false;});}
  void ThroughEndpoint(){
    tpi::Corr(&owner,f.N(),f.id.data(),f.code.data(),f.p.data(),f.j.data(),f.theta.data());
    for(unsigned a=f.npb;a<f.N();a++)if(CODE_IsFluid(f.code[a]))f.p[a]=tpi::state.sourceDrained[f.id[a]]?0.f:tpi::Guess(f.id[a]);
    // A constructed fixture full J, not a second solver/material advance.
    for(unsigned a=f.npb;a<f.N();a++)if(CODE_IsNormal(f.code[a]))f.j[a]+=dt*.0001;
    tpi::CaptureJ(&owner,f.N(),f.id.data(),f.code.data(),f.j.data());
    tpi::Endpoint(&owner,f.N(),f.id.data(),f.code.data(),f.pos.data(),f.vel.data(),f.sigma.data(),f.kappa.data(),f.p0.data(),f.p.data(),f.j.data(),tpi::state.sourceTime,tpi::state.sourceStep,dt);
  }
  void Endpoint(){Begin();ThroughEndpoint();}
  template<class Pred> void Rows(Pred drained){
    for(unsigned k:tpi::state.soilIds){unsigned a=f.Slot(k);tpi::Row(k,drained(a),2.,.5+double(k)*.01,f.theta[a],f.p[a]);}
  }
  void Rows(){Rows([](unsigned){return false;});}
  void Prepare(){tpi::PrepareFinal(&owner,f.N(),f.id.data(),f.code.data(),f.pos.data(),f.vel.data(),f.sigma.data(),f.kappa.data(),f.p0.data(),f.p.data(),f.j.data());}
  template<class Pred> void WriteCommit(Pred drained){
    tpi::WriteFinal(f.N(),f.npb,f.id.data(),f.code.data(),f.p.data());
    tpi::state.endpoint=false;tpi::state.temporary=false;
    // Fixture caller applies the same independently declared Dirichlet mask.
    for(unsigned k:tpi::state.soilIds){unsigned a=f.Slot(k);if(drained(a))f.p[a]=0.f;tpi::SetCommitDrained(k,drained(a));}
    tpi::Commit(&owner,f.N(),f.id.data(),f.code.data(),f.p.data(),f.p0.data(),f.j.data());
  }
  void WriteCommit(){WriteCommit([](unsigned){return false;});}
  void Save(unsigned part){tpi::Saved(&owner,part,tpi::state.lastEnd,tpi::state.commits?initialStep+tpi::state.commits-1:initialStep,f.N(),f.id.data(),f.code.data(),f.p.data(),f.j.data());}
  void Finish(){tpi::Finish(&owner,initialStep+tpi::state.commits,tpi::state.lastEnd);}
};

void PredictionAndRows(){
  const double nan=std::numeric_limits<double>::quiet_NaN();
  SameBits(tpi::Predict(7.,3.,.5),9.,"B true full-history extrapolation");
  SameBits(tpi::Predict(7.,nan,0.),7.,"C ignores NaN previous");
  Reject([&](){tpi::Predict(7.,nan,.5);},"B invalid previous","previous");
  Reject([&](){tpi::Predict(nan,3.,0.);},"C invalid pn","prediction");
  Reject([&](){tpi::Predict(7.,3.,.25);},"unadmitted alpha","prediction");
  Reject([&](){tpi::Predict(double(FLT_MAX),-double(FLT_MAX),.5);},"prediction float overflow","overflows");
  SameBits(tpi::SolveBeta0(false,3.,2.,4.),5.,"single beta0 defect correction");
  SameBits(tpi::SolveBeta0(false,-3.25,2.,0.),-3.25,"nonzero-S fixed point has R=0");
  SameBits(tpi::SolveBeta0(true,nan,nan,nan),0.,"Dirichlet has priority over all inactive row inputs");
  Reject([&](){tpi::SolveBeta0(false,3.,0.,4.);},"zero S","Invalid beta0 row");
  Reject([&](){tpi::SolveBeta0(false,3.,-2.,4.);},"negative S","Invalid beta0 row");
  Reject([&](){tpi::SolveBeta0(false,3.,nan,4.);},"NaN S","Invalid beta0 row");
  Reject([&](){tpi::SolveBeta0(false,3.,2.,nan);},"NaN residual","Invalid beta0 row");
  Reject([&](){tpi::SolveBeta0(false,nan,2.,4.);},"NaN actual q","Invalid beta0 row");
  Reject([&](){tpi::SolveBeta0(false,double(FLT_MAX),1.,double(FLT_MAX));},"row float overflow","overflows");
}
void IdentityCases(){
  {Fixture x("identity_reorder_periodic");const auto initial=tpi::state.previous;x.f.Reorder({0,3,1,4,2});
    tpi::Map(x.f.N(),x.f.id.data(),x.f.code.data());
    Check(tpi::state.nativeCount==4&&tpi::state.soilCount==3&&tpi::state.fixedCount==1,"periodic clone has no independent owner");
    for(unsigned k:tpi::state.soilIds){Check(tpi::state.slot[k]==x.f.Slot(k),"ID remap after permutation");SameBits(tpi::state.previous[k],initial[k],"reordering retains full history by native ID");}
    x.Begin();for(unsigned a=1;a<x.f.N();a++)SameBits(x.f.p[a],tpi::Half(x.f.id[a]),"periodic pressure resolves original owner");}
  {Fixture x("identity_lost");x.f.code[x.f.Slot(29)]=typecode(CODE_SetOutPos(CODE_TYPE_FLUID));Reject([&](){tpi::Map(x.f.N(),x.f.id.data(),x.f.code.data());},"lost native owner","Native set changed");}
  {Fixture x("identity_duplicate");x.f.id[x.f.Slot(44)]=11;Reject([&](){tpi::Map(x.f.N(),x.f.id.data(),x.f.code.data());},"duplicated normal ID","duplicated");}
  {Fixture x("identity_role");x.f.code[x.f.Slot(29)]=typecode(CODE_TYPE_FIXED);Reject([&](){tpi::Map(x.f.N(),x.f.id.data(),x.f.code.data());},"changed native role","role changed");}
  {Fixture x("identity_unowned_copy");x.f.id.back()=100;Reject([&](){tpi::Map(x.f.N(),x.f.id.data(),x.f.code.data());},"unowned periodic clone","periodic copies");}
  {Fixture x("identity_periodic_soil_to_fixed");x.f.code.back()=typecode(CODE_SetPeriodic(CODE_TYPE_FIXED));Reject([&](){tpi::Map(x.f.N(),x.f.id.data(),x.f.code.data());},"soil periodic clone changed to fixed","Periodic copy material role");}
  {Fixture x("identity_periodic_fixed_to_soil");x.f.id.back()=3;Reject([&](){tpi::Map(x.f.N(),x.f.id.data(),x.f.code.data());},"fixed owner periodic clone changed to soil","Periodic copy material role");}
  {Fixture x("identity_periodic_fixed_valid");x.f.id.back()=3;x.f.code.back()=typecode(CODE_SetPeriodic(CODE_TYPE_FIXED));tpi::Map(x.f.N(),x.f.id.data(),x.f.code.data());Check(tpi::state.fixedCount==1,"legitimate fixed clone is not an independent fixed owner");}
}
void CompleteTransaction(){
  Fixture x("complete_two_steps");const auto firstPn=x.f.p;const auto ids=tpi::state.soilIds;std::vector<float> p0ById(tpi::state.role.size());
  for(unsigned k:tpi::state.nativeIds)p0ById[k]=x.f.p0[x.f.Slot(k)];
  x.Save(0);x.Endpoint();x.Rows();x.Prepare();x.WriteCommit();x.Save(1);
  Check(tpi::state.commits==1&&tpi::state.preCalls==1&&tpi::state.corCalls==1&&tpi::state.jCalls==1&&tpi::state.endpointCalls==1,"one complete lifecycle");
  for(unsigned k:ids)SameBits(tpi::state.previous[k],firstPn[x.f.Slot(k)],"first history rotation uses actual pn");
  const auto oldPrevious=tpi::state.previous;const auto commitCount=tpi::state.commits;
  Reject([&](){tpi::Commit(&x.owner,x.f.N(),x.f.id.data(),x.f.code.data(),x.f.p.data(),x.f.p0.data(),x.f.j.data());},"duplicate commit","lifecycle");
  Check(tpi::state.commits==commitCount,"duplicate commit does not increment");
  for(unsigned k:ids)SameBits(tpi::state.previous[k],oldPrevious[k],"duplicate commit does not rotate history");
  x.f.Reorder({0,3,4,2,1});x.Begin();
  for(unsigned k:ids){const auto a=x.f.Slot(k);
    const double manual=tpi::RequestedScheme()==tpi::B_Tpi?double(tpi::state.pn[k])+.5*(double(tpi::state.pn[k])-double(oldPrevious[k])):double(tpi::state.pn[k]);
    SameBits(x.f.p[a],float(manual),"second step actual full-history prediction");}
  x.ThroughEndpoint();x.Rows();x.Prepare();x.WriteCommit();x.Save(2);x.Finish();
  Check(tpi::state.commits==2&&tpi::state.coreFieldChecks==7ull*ids.size()*2,"two whole-step commits and all core fields");
  for(unsigned a=0;a<x.f.N();a++)SameBits(x.f.p0[a],p0ById[x.f.id[a]],"P0 untouched after sorting/periodic lookup");
}
void RejectedEndpointCases(){
  for(unsigned mode=0;mode<6;mode++){
    Fixture x("reject_row_"+std::to_string(mode));x.Endpoint();const auto pressure=x.f.p,previous=tpi::state.previous;const auto commits=tpi::state.commits;
    for(unsigned k:tpi::state.soilIds){const auto a=x.f.Slot(k);if(k!=29)tpi::Row(k,false,2.,1.,x.f.theta[a],x.f.p[a]);}
    const auto a=x.f.Slot(29);const double nan=std::numeric_limits<double>::quiet_NaN();
    if(mode==0)tpi::Row(29,false,0.,1.,x.f.theta[a],x.f.p[a]);
    if(mode==1)tpi::Row(29,false,-1.,1.,x.f.theta[a],x.f.p[a]);
    if(mode==2)tpi::Row(29,false,2.,nan,x.f.theta[a],x.f.p[a]);
    if(mode==3){tpi::Row(29,false,2.,1.,x.f.theta[a],x.f.p[a]);tpi::Row(29,false,2.,1.,x.f.theta[a],x.f.p[a]);}
    if(mode==4)tpi::Row(29,false,1.,double(FLT_MAX)*2.,x.f.theta[a],x.f.p[a]);
    // mode5 intentionally has no row for native29.
    Reject([&](){x.Prepare();},"failed row must reject before pressure write");
    for(unsigned k:tpi::state.soilIds)SameBits(tpi::state.previous[k],previous[k],"row failure preserves previous history");
    for(unsigned p=0;p<x.f.N();p++)SameBits(x.f.p[p],pressure[p],"row failure does not write physical pressure");
    Check(tpi::state.commits==commits&&!tpi::state.prepared,"row failure has no commit/prepared stage");
    Reject([&](){tpi::WriteFinal(x.f.N(),x.f.npb,x.f.id.data(),x.f.code.data(),x.f.p.data());},"write before successful row preparation","lifecycle");
  }
  {Fixture x("reject_core_P0");x.Endpoint();x.Rows();const auto previous=tpi::state.previous;const auto pressure=x.f.p;x.f.p0[x.f.Slot(29)]+=1.f;
    Reject([&](){x.Prepare();},"extra endpoint P0 advance","committed soil field");
    Check(tpi::state.commits==0,"P0 rejection no commit");for(unsigned k:tpi::state.soilIds)SameBits(tpi::state.previous[k],previous[k],"P0 rejection no history rotation");
    for(unsigned p=0;p<x.f.N();p++)SameBits(x.f.p[p],pressure[p],"P0 rejection no final pressure write");}
  {Fixture x("reject_finite_pressure_replacement");x.Endpoint();x.Rows();x.Prepare();tpi::WriteFinal(x.f.N(),x.f.npb,x.f.id.data(),x.f.code.data(),x.f.p.data());
    tpi::state.endpoint=false;tpi::state.temporary=false;const auto previous=tpi::state.previous;const auto commits=tpi::state.commits;x.f.p[x.f.Slot(29)]=-123.5f;
    Reject([&](){tpi::Commit(&x.owner,x.f.N(),x.f.id.data(),x.f.code.data(),x.f.p.data(),x.f.p0.data(),x.f.j.data());},"finite unauthorized post-row replacement","exact raw row");
    Check(tpi::state.commits==commits,"finite replacement no whole-step commit");for(unsigned k:tpi::state.soilIds)SameBits(tpi::state.previous[k],previous[k],"finite replacement no history rotation");}
  {Fixture x("reject_true_drained_minus_zero");x.Endpoint();const unsigned a=x.f.Slot(11);x.Rows([&](unsigned p){return p==a;});x.Prepare();tpi::WriteFinal(x.f.N(),x.f.npb,x.f.id.data(),x.f.code.data(),x.f.p.data());
    tpi::state.endpoint=false;tpi::state.temporary=false;tpi::SetCommitDrained(11,true);x.f.p[a]=-0.f;const auto previous=tpi::state.previous;
    Reject([&](){tpi::Commit(&x.owner,x.f.N(),x.f.id.data(),x.f.code.data(),x.f.p.data(),x.f.p0.data(),x.f.j.data());},"true drained requires positive zero bits","true-Dirichlet +0");
    Check(tpi::state.commits==0,"minus-zero rejection no commit");for(unsigned k:tpi::state.soilIds)SameBits(tpi::state.previous[k],previous[k],"minus-zero rejection no history rotation");}
  {Fixture x("prediction_previous_nan");tpi::state.previous[29]=std::numeric_limits<float>::quiet_NaN();
    if(tpi::RequestedScheme()==tpi::B_Tpi)Reject([&](){x.Begin();},"B Begin reads and validates previous","previous");
    else{x.Begin();SameBits(x.f.p[x.f.Slot(29)],tpi::state.pn[29],"C Begin uses pn and does not numerically read previous NaN");}}
}
// This is an explicit fixture of the original policy, not a new time test in
// the helper: tD itself is pre-open; strictly later FS2/FS3 is true drained.
bool OriginalFixtureDrain(double time,double tD,unsigned fs){return time>tD&&(fs==2||fs==3);}
void SourceClockBoundaryCases(){
  Check(!OriginalFixtureDrain(.125,.125,2),"fixture FS2 at tD is pre-open");
  Check(OriginalFixtureDrain(.140625,.125,2),"fixture FS2 after tD is drained");
  Check(OriginalFixtureDrain(.140625,.125,3),"fixture FS3 after tD is drained");
  Check(!OriginalFixtureDrain(.140625,.125,0),"fixture FS0 after tD is not drained");
  {Fixture x("source_tD_preopen");x.f.fs[x.f.Slot(11)]=2;const double tD=x.initialTime;
    const auto pred=[&](unsigned a){return OriginalFixtureDrain(x.initialTime,tD,x.f.fs[a]);};
    Check(!pred(x.f.Slot(11)),"tD remains pre-open");const auto pn=x.f.p;x.Begin(pred);
    SameBits(tpi::state.pn[11],pn[x.f.Slot(11)],"pre-open retains pn");Check(!tpi::state.sourceDrained[11],"pre-open source mask is false");}
  {Fixture x("source_open_FS_change");x.Endpoint();x.Rows();x.Prepare();x.WriteCommit();x.Save(1);
    const auto savedFinal=x.f.p;const auto oldPrevious=tpi::state.previous;const auto oldP0=x.f.p0;const unsigned a=x.f.Slot(11);const double time=tpi::state.lastEnd,tD=x.initialTime;
    x.f.fs[a]=3;const auto pred=[&](unsigned slot){return OriginalFixtureDrain(time,tD,x.f.fs[slot]);};
    Check(pred(a),"later FS3 newly becomes true drained");Check(savedFinal[a]!=0.f,"saved final contains pre-projection pressure");x.f.p[a]=0.f;x.Begin(pred);
    SameBits(tpi::state.pn[11],0.f,"actual source-clock projected pn captured");Check(tpi::state.sourceDrained[11]==1,"source projection recorded");
    SameBits(tpi::state.finalP[11],savedFinal[a],"saved prior final is not rewritten");
    SameBits(tpi::state.previous[11],oldPrevious[11],"prior history is not rewritten at Begin");
    for(unsigned p=0;p<x.f.N();p++)SameBits(x.f.p0[p],oldP0[p],"source BC does not rewrite P0");
    x.ThroughEndpoint();x.Rows(pred);x.Prepare();x.WriteCommit(pred);x.Save(2);x.Finish();
    SameBits(tpi::state.previous[11],0.f,"only successful whole step rotates actual post-BC pn");}
  {Fixture x("source_unauthorized_change");x.Endpoint();x.Rows();x.Prepare();x.WriteCommit();const auto previous=tpi::state.previous;const auto commits=tpi::state.commits;x.f.p[x.f.Slot(29)]+=1.f;
    Reject([&](){x.Begin();},"non-Dirichlet change before Begin","Non-Dirichlet");Check(tpi::state.commits==commits,"unauthorized source change no commit");for(unsigned k:tpi::state.soilIds)SameBits(tpi::state.previous[k],previous[k],"unauthorized source change no history rotation");}
}

struct FixtureHG{
  using Stats=JSphHourglassCpu::StStats;
  using RateInfo=JSphHourglassCpu::StRateInfo;
  Stats stats{};RateInfo rateInfo{};
  std::vector<tdouble3> history,rate;
  explicit FixtureHG(unsigned extent):history(extent,TDouble3(0)),rate(extent,TDouble3(0)){
    for(unsigned k:tpi::state.soilIds){history[k]=TDouble3(.125*k,0.,-.0625*k);rate[k]=TDouble3(-.001*k,0.,.002*k);}
    stats.forcecalls=12;stats.predictorupdates=6;stats.correctorupdates=6;stats.ratecalls=12;stats.predictorrates=6;stats.endpointrates=6;
    stats.firstpairs=4;stats.minpairs=3;stats.maxpairs=5;stats.maxnetforce=.01;stats.maxactualnetforce=.02;stats.maxnetrate=.03;stats.maxrelativeforce=.04;stats.maxrelativerate=.05;stats.maxhistory=.06;stats.maxcondition=.07;stats.maxpoweridentityerror=.08;stats.maxskew=.09;stats.spinbound=.001;stats.maxtauratio=.1;stats.mintau=2.;stats.maxlambda=3.;stats.ratecalculations=7;stats.ratecachehits=5;
    rateInfo.netx=.1;rateInfo.netz=.2;rateInfo.condition=.3;rateInfo.skew=.4;rateInfo.form=.5;rateInfo.lambda=.6;rateInfo.tau=.7;rateInfo.ratepower=.8;rateInfo.workerror=.9;rateInfo.rmax=1.;rateInfo.sumrate=1.1;rateInfo.meandxx=1.2;rateInfo.rmsdxx=1.3;rateInfo.meandiv=1.4;rateInfo.rmsdiv=1.5;
  }
  unsigned GetCount()const{return unsigned(tpi::state.soilIds.size());}
  const Stats& GetStats()const{return stats;}
  const RateInfo& GetRateInfo()const{return rateInfo;}
  tdouble3 GetHistory(unsigned id)const{return history.at(id);}
  tdouble3 GetRate(unsigned id)const{return rate.at(id);}
};
// Independent transcription of the frozen ParticleMass/AddHistory operations.
// It is not computed through AddReadonlyHG or simplified into a ratio of rho.
double FrozenParticleMass(double Mass,double RhopZero,double WaterRho,double j){
  const double mass=(Mass/RhopZero)*(RhopZero-WaterRho+WaterRho*j);return mass;
}
tfloat3 FrozenAdd(tfloat3 ace,tdouble3 h,double J,double Mass,double RhopZero,double WaterRho){
  const double ax=ace.x,az=ace.z;
  const double mass=FrozenParticleMass(Mass,RhopZero,WaterRho,J),scale=Mass/mass;
  ace.x=float(ax+scale*h.x);ace.z=float(az+scale*h.z);return ace;
}
void ReadonlyHGCases(){
  Fixture x("readonly_HG");x.Endpoint();FixtureHG hg(unsigned(tpi::state.role.size()));
  std::vector<tfloat3> ace(x.f.N());for(unsigned a=0;a<x.f.N();a++)ace[a]=TFloat3(float(-100.125+a),float(.25*a),float(50.375-a));
  const auto originalAce=ace;std::vector<tfloat3> expected=ace;const double Mass=21.,RhopZero=2100.,WaterRho=1000.;
  bool currentJHasEffect=false;
  for(unsigned a=x.f.npb;a<x.f.N();a++)if(CODE_IsNormal(x.f.code[a])&&CODE_IsFluid(x.f.code[a])){
    expected[a]=FrozenAdd(expected[a],hg.GetHistory(x.f.id[a]),x.f.j[a],Mass,RhopZero,WaterRho);
    const auto unitJ=FrozenAdd(originalAce[a],hg.GetHistory(x.f.id[a]),1.,Mass,RhopZero,WaterRho);if(!tpi::Bits(expected[a],unitJ))currentJHasEffect=true;
  }
  tpi::CaptureHG(&hg);tpi::AddReadonlyHG(&hg,x.f.N(),x.f.npb,x.f.id.data(),x.f.code.data(),ace.data(),x.f.j.data(),Mass,RhopZero,WaterRho);tpi::CheckHG(&hg);
  for(unsigned a=0;a<x.f.N();a++)SameBits(ace[a],expected[a],"readonly HG frozen double/add/float current-J result");
  Check(currentJHasEffect,"fixture distinguishes current J from unit/reference J");
  Check(tpi::state.hgSnapshotChecks==2ull*tpi::state.soilCount,"history and rate each checked per owner");
  const unsigned k=tpi::state.soilIds.front();hg.history[k].x+=.001;Reject([&](){tpi::CheckHG(&hg);},"changed HG history","history/rate");
  // Restore by exact prior capture, not by relying on subtract to recover bits.
  hg.history[k]=tpi::state.hg[k].history;hg.rate[k].z+=.001;Reject([&](){tpi::CheckHG(&hg);},"changed HG rate","history/rate");hg.rate[k]=tpi::state.hg[k].rate;
  using S=FixtureHG::Stats;using R=FixtureHG::RateInfo;
  const std::pair<const char*,unsigned S::*> uintFields[]={{"forcecalls",&S::forcecalls},{"predictorupdates",&S::predictorupdates},{"correctorupdates",&S::correctorupdates},{"ratecalls",&S::ratecalls},{"predictorrates",&S::predictorrates},{"endpointrates",&S::endpointrates},{"firstpairs",&S::firstpairs},{"minpairs",&S::minpairs},{"maxpairs",&S::maxpairs},{"ratecalculations",&S::ratecalculations},{"ratecachehits",&S::ratecachehits}};
  const std::pair<const char*,double S::*> statFields[]={{"maxnetforce",&S::maxnetforce},{"maxactualnetforce",&S::maxactualnetforce},{"maxnetrate",&S::maxnetrate},{"maxrelativeforce",&S::maxrelativeforce},{"maxrelativerate",&S::maxrelativerate},{"maxhistory",&S::maxhistory},{"maxcondition",&S::maxcondition},{"maxpoweridentityerror",&S::maxpoweridentityerror},{"maxskew",&S::maxskew},{"spinbound",&S::spinbound},{"maxtauratio",&S::maxtauratio},{"mintau",&S::mintau},{"maxlambda",&S::maxlambda}};
  const std::pair<const char*,double R::*> rateFields[]={{"netx",&R::netx},{"netz",&R::netz},{"condition",&R::condition},{"skew",&R::skew},{"form",&R::form},{"lambda",&R::lambda},{"tau",&R::tau},{"ratepower",&R::ratepower},{"workerror",&R::workerror},{"rmax",&R::rmax},{"sumrate",&R::sumrate},{"meandxx",&R::meandxx},{"rmsdxx",&R::rmsdxx},{"meandiv",&R::meandiv},{"rmsdiv",&R::rmsdiv}};
  for(const auto& field:uintFields){const auto old=hg.stats.*field.second;hg.stats.*field.second=old+1;Reject([&](){tpi::CheckHG(&hg);},std::string("HG stats ")+field.first,"statistics");hg.stats.*field.second=old;}
  for(const auto& field:statFields){const auto old=hg.stats.*field.second;hg.stats.*field.second=old+.125;Reject([&](){tpi::CheckHG(&hg);},std::string("HG stats ")+field.first,"statistics");hg.stats.*field.second=old;}
  for(const auto& field:rateFields){const auto old=hg.rateInfo.*field.second;hg.rateInfo.*field.second=old+.125;Reject([&](){tpi::CheckHG(&hg);},std::string("HG rate-info ")+field.first,"rate-info");hg.rateInfo.*field.second=old;}
  tpi::CheckHG(&hg);x.Rows();x.Prepare();x.WriteCommit();x.Save(1);x.Finish();
}
void Summary(const std::string& mode){
  const std::string path=root+"/component.summary.json";Check(_access(path.c_str(),0)!=0,"summary must not exist");std::ofstream out(path);Check(bool(out),"summary open");
  out<<"{\"stage\":\"upl_tpi_cpu_component_r1\",\"scheme\":\""<<mode<<"\",\"passed\":true,\"fixtures\":"<<fixtures<<",\"assertions\":"<<assertions<<",\"expected_rejections\":"<<expectedRejections<<",\"actual_helper_used\":true,\"frozen_HG_structures_used\":true,\"HG_fixture_is_not_real_HG_solver\":true,\"solver_invocations\":0,\"native_invocations\":0,\"physical_acceptance\":false,\"fixture_names\":[";
  for(size_t a=0;a<fixtureNames.size();a++){if(a)out<<',';out<<'"'<<fixtureNames[a]<<'"';}out<<"]}\n";out.flush();if(!out)throw std::runtime_error("summary flush failed");
}
} // namespace component

int main(int argc,char** argv){
  try{
    if(argc!=5||std::string(argv[1])!="--scheme"||std::string(argv[3])!="--output")throw std::runtime_error("Usage: component.exe --scheme B|C --output FRESH_DIRECTORY");
    const std::string mode=argv[2];if(mode!="B"&&mode!="C")throw std::runtime_error("One B or C process is required");
    if(_putenv_s("UPL_TPI_CPU_R1",mode.c_str())!=0)throw std::runtime_error("Private scheme environment could not be set");
    component::root=argv[4];component::FreshDirectory(component::root);
    component::Check(upl_tpi_cpu_r1::RequestedScheme()==(mode=="B"?upl_tpi_cpu_r1::B_Tpi:upl_tpi_cpu_r1::C_PpeT),"process-isolated scheme selector");
    component::PredictionAndRows();component::IdentityCases();component::CompleteTransaction();component::RejectedEndpointCases();component::SourceClockBoundaryCases();component::ReadonlyHGCases();component::Summary(mode);
    std::cout<<"P1 component passed scheme="<<mode<<" fixtures="<<component::fixtures<<" assertions="<<component::assertions<<" expected_rejections="<<component::expectedRejections<<'\n';return 0;
  }catch(const std::exception& e){std::cerr<<"P1 component failed: "<<e.what()<<'\n';return 1;}
}
