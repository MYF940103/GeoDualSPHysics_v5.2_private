// Author-only fixture: frozen-geometry adjoint algebra, never a solver or HG integration.
#include <algorithm>
#include <array>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
#include <xmmintrin.h>

namespace phg {
void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
void Need(bool b,const std::string& s){if(!b)throw std::runtime_error(s);}
const double U=std::numeric_limits<double>::epsilon()/2;
const double Inf=std::numeric_limits<double>::infinity();
struct Counts{uint64_t add=0,mul=0,div=0,sqrt=0;} count;
double Up(double x){Need(std::isfinite(x)&&x>=0,"Nonfinite arithmetic error bound");return std::nextafter(x,Inf);}
double EA(double a,double b){return Up(a+b);} double EM(double a,double b){return Up(a*b);}
double ED(double a,double b){Need(b>0,"Undefined error-bound divisor");return Up(a/b);}
double Round(double x){return EA(EM(Up(U/(1-U)),std::abs(x)),std::numeric_limits<double>::denorm_min());}
// Values are the actual ordered double computations. e encloses their absolute
// error relative to the same exact algebra on declared inputs; bound arithmetic
// itself is rounded outward. This small type is local to this fixed fixture.
struct B{double v=0,e=0;B()=default;B(double x):v(x){Need(std::isfinite(x),"Nonfinite input");}
  B(double x,double err):v(x),e(err){Need(std::isfinite(v)&&std::isfinite(e)&&e>=0,"Nonfinite value/bound");}};
B operator+(B a,B b){count.add++;const double v=a.v+b.v;return B(v,EA(EA(a.e,b.e),Round(v)));}
B operator-(B a,B b){count.add++;const double v=a.v-b.v;return B(v,EA(EA(a.e,b.e),Round(v)));}
B operator-(B a){return B(-a.v,a.e);}
B operator*(B a,B b){count.mul++;const double v=a.v*b.v;
  return B(v,EA(EA(EA(EM(std::abs(a.v),b.e),EM(std::abs(b.v),a.e)),EM(a.e,b.e)),Round(v)));}
B operator/(B a,B b){count.div++;const double low=std::nextafter(std::abs(b.v)-b.e,-Inf);
  Need(low>0,"Division interval includes zero; no regularization");const double v=a.v/b.v,r=Round(v);
  return B(v,EA(ED(EA(a.e,EM(EA(std::abs(v),r),b.e)),low),r));}
B Sqrt(B a){count.sqrt++;const double lo=std::nextafter(a.v-a.e,-Inf);
  Need(lo>0,"Square-root interval not strictly positive");const double v=std::sqrt(a.v),r=Round(v);
  const double sl=std::nextafter(std::sqrt(lo),-Inf),sv=std::nextafter(v-r,-Inf);
  const double den=std::nextafter(sl+sv,-Inf);Need(den>0,"Undefined sqrt error bound");
  return B(v,EA(ED(a.e,den),r));}
struct V{B x,z;};
V operator+(V a,V b){return {a.x+b.x,a.z+b.z};} V operator-(V a,V b){return {a.x-b.x,a.z-b.z};}
V operator-(V a){return {-a.x,-a.z};} V operator*(B s,V a){return {s*a.x,s*a.z};}
V operator/(V a,B s){return {a.x/s,a.z/s};}
B Dot(V a,V b){return a.x*b.x+a.z*b.z;} B Cross(V a,V b){return a.x*b.z-a.z*b.x;}
struct M{B xx,xz,zx,zz;};
M operator+(M a,M b){return {a.xx+b.xx,a.xz+b.xz,a.zx+b.zx,a.zz+b.zz};}
M operator*(B s,M a){return {s*a.xx,s*a.xz,s*a.zx,s*a.zz};}
V Mul(M a,V b){return {a.xx*b.x+a.xz*b.z,a.zx*b.x+a.zz*b.z};}
M Outer(V a,V b){return {a.x*b.x,a.x*b.z,a.z*b.x,a.z*b.z};}
M Mul(M a,M b){return {a.xx*b.xx+a.xz*b.zx,a.xx*b.xz+a.xz*b.zz,
  a.zx*b.xx+a.zz*b.zx,a.zx*b.xz+a.zz*b.zz};}
M Transpose(M a){return {a.xx,a.zx,a.xz,a.zz};}
struct Moment{B xx,xz,zz,det;double condition=0;};
M RightInverse(M n,const Moment& m){return {(n.xx*m.zz-n.xz*m.xz)/m.det,
  (n.xz*m.xx-n.xx*m.xz)/m.det,(n.zx*m.zz-n.zz*m.xz)/m.det,(n.zz*m.xx-n.zx*m.xz)/m.det};}
struct Row{unsigned i,j;V d;B a,D;};
struct Graph{std::vector<V> x;std::vector<B> volume,mass;std::vector<Row> rows;
  std::vector<Moment> moment;double condition=0;};
const unsigned N=49;
// Original 2D Wendland HG pair weight from JSphHourglassCpu::BuildPairs.
// The float source constants are declared numerical inputs, not fitted values.
const double H=double(float(.072));
const double Bwen=double(float(-2.7852/(H*H*H)));
Graph MakeGraph(const std::vector<V>& x){
  Need(x.size()==N,"Exactly 49 manufactured points required");Graph g;g.x=x;
  g.volume.resize(N);g.mass.resize(N);g.moment.resize(N);
  const B v0(.04*.04),rho0(2072.5),rhow(1000),xi(.2),shear(7.5e6),h(H),support(2*H);
  for(unsigned i=0;i<N;i++){
    // Prescribed J/mass variation tests inertia conversion only, not a u-pl ledger.
    const B j(1+.04*std::sin(double(i)*.31));g.volume[i]=v0*j;
    g.mass[i]=g.volume[i]*(rhow+(rho0-rhow)/j);Need(std::nextafter(g.mass[i].v-g.mass[i].e,-Inf)>0,"Positive synthetic mass required");
  }
  for(unsigned i=0;i<N;i++)for(unsigned j=i+1;j<N;j++){
    const V d=x[i]-x[j];const B rr=Dot(d,d),cut=support*support;
    const double rrlo=std::nextafter(rr.v-rr.e,-Inf),rrhi=std::nextafter(rr.v+rr.e,Inf);
    const double cutlo=std::nextafter(cut.v-cut.e,-Inf),cuthi=std::nextafter(cut.v+cut.e,Inf);
    Need(rrhi<cutlo||rrlo>cuthi,"Support membership arithmetically ambiguous");
    if(rrlo>cuthi)continue;
    Need(rrlo>0,"Coincident/uncertified points");const B s=B(1)-Sqrt(rr)/(B(2)*h);
    Need(std::nextafter(s.v-s.e,-Inf)>0,"Nonpositive interior kernel weight");const B w=-(B(Bwen)/h)*s*s*s;
    const B beta=xi*shear*g.volume[i]*g.volume[j]*w;
    g.rows.push_back({i,j,d,g.volume[j]*w,beta/B(2)});
    g.rows.push_back({j,i,-d,g.volume[i]*w,beta/B(2)});
  }
  for(const auto& r:g.rows){auto& m=g.moment[r.i];m.xx=m.xx+r.a*r.d.x*r.d.x;
    m.xz=m.xz+r.a*r.d.x*r.d.z;m.zz=m.zz+r.a*r.d.z*r.d.z;}
  for(auto& m:g.moment){m.det=m.xx*m.zz-m.xz*m.xz;
    const double tr=m.xx.v+m.zz.v,hi=.5*(tr+std::hypot(m.xx.v-m.zz.v,2*m.xz.v)),lo=m.det.v/hi;
    Need(std::isfinite(m.det.v)&&lo>0&&hi/lo<1e8,"Original HG rank/condition guard");
    Need(std::nextafter(m.det.v-m.det.e,-Inf)>0,"Uncertified positive moment determinant; no ridge");
    m.condition=hi/lo;g.condition=std::max(g.condition,m.condition);}
  return g;
}
struct Forward{std::vector<M> L;std::vector<V> residual;};
Forward ApplyP(const Graph& g,const std::vector<V>& v){
  Need(v.size()==N,"P input extent");Forward f;f.L.resize(N);f.residual.reserve(g.rows.size());
  std::vector<M> n(N);
  for(const auto& r:g.rows)n[r.i]=n[r.i]+r.a*Outer(v[r.i]-v[r.j],r.d);
  for(unsigned i=0;i<N;i++)f.L[i]=RightInverse(n[i],g.moment[i]);
  for(const auto& r:g.rows)f.residual.push_back(v[r.i]-v[r.j]-Mul(f.L[r.i],r.d));
  return f;
}
// Actual matrix-free adjoint. The LS term is differentiated through every donor;
// no explicit/basis P is read by this implementation.
std::vector<V> ApplyPT(const Graph& g,const std::vector<V>& y){
  Need(y.size()==g.rows.size(),"PT input extent");std::vector<M> z(N),t(N);std::vector<V> out(N);
  for(size_t k=0;k<g.rows.size();k++){const auto& r=g.rows[k];z[r.i]=z[r.i]+Outer(y[k],r.d);}
  for(unsigned i=0;i<N;i++)t[i]=RightInverse(z[i],g.moment[i]);
  for(size_t k=0;k<g.rows.size();k++){const auto& r=g.rows[k];const V q=y[k]-r.a*Mul(t[r.i],r.d);
    out[r.i]=out[r.i]+q;out[r.j]=out[r.j]-q;}
  return out;
}

// New fixed-input contract below; the preceding P/PT prefix is byte-exactly
// copied from the already passed adjoint fixture, and is not an integration hook.
double Lo(B b){return std::nextafter(b.v-b.e,-Inf);} double Hi(B b){return std::nextafter(b.v+b.e,Inf);}
uint64_t event_interval_overlaps=0,scalar_checks=0;double max_ratio=0;
void Close(B d,const char* what){const double r=d.e>0?std::abs(d.v)/d.e:(d.v==0?0:Inf);
  Need(std::isfinite(r)&&r<=1,std::string("Arithmetic identity failed: ")+what);scalar_checks++;max_ratio=std::max(max_ratio,r);}
void CloseV(V d,const char* what){Close(d.x,what);Close(d.z,what);}
B ClipTime(B q,B t){
  // clamp is monotone in both arguments; these bounds enclose either event branch.
  const double low=std::max(0.,std::min(Lo(t),Lo(q))),high=std::max(0.,std::min(Hi(t),Hi(q)));
  const double v=std::max(0.,std::min(t.v,q.v));
  if((Lo(q)<=0&&Hi(q)>=0)||(Lo(q)<=Hi(t)&&Hi(q)>=Lo(t)))event_interval_overlaps++;
  return B(v,Up(std::max(std::max(0.,v-low),std::max(0.,high-v))));
}
struct Step{V h,I;B A,Z,t1,t2,de,work,loss,total;std::string branch;};
Step ExactStep(V h0,V z,B d,B g,B t){
  Need(t.v>0&&Lo(t)>0&&g.e==0&&g.v>=0&&g.v<=1,"Positive interval and prescribed exact gamma in [0,1] required");
  Need(d.v>=0,"PSD scalar D required");Step o;o.A=Dot(h0,d*z);o.Z=Dot(z,d*z);
  const bool zeroD=d.v==0&&d.e==0,zeroZ=z.x.v==0&&z.x.e==0&&z.z.v==0&&z.z.e==0;
  if(zeroD||zeroZ){o.t1=B(0);o.branch=zeroD?"zero_weight":"zero_velocity";
    Close(o.A,"PSD null row A=0");Close(o.Z,"PSD null row Z=0");}
  else{Need(Lo(d)>0&&Lo(o.Z)>0,"Nonzero row Z cannot be arithmetically certified; no threshold/regularization");
    const B crossing=-o.A/o.Z;o.t1=ClipTime(crossing,t);
    o.branch=crossing.v<=0?"loading":crossing.v<t.v?"crossing":crossing.v==t.v?"at_event_end":"unloading_only";}
  o.t2=t-o.t1;const B drive=o.t1+g*o.t2;
  o.h=h0+drive*z;
  o.I=t*h0+(B(.5)*o.t1*o.t1+o.t1*o.t2+B(.5)*g*o.t2*o.t2)*z;
  o.de=B(.5)*d*(Dot(o.h,o.h)-Dot(h0,h0));o.work=-Dot(z,d*o.I);
  // loss >=0 analytically; retain any tiny signed computed value, never clip it.
  o.loss=(B(1)-g)*(o.t2*(o.A+o.Z*o.t1)+B(.5)*g*o.Z*o.t2*o.t2);
  o.total=o.de+o.work;Close(o.total+o.loss,"energy+work+loading dissipation");
  Need(Hi(o.loss)>=0&&o.total.v<=o.total.e,"Fixed-input passive contract violated beyond arithmetic budget");return o;
}

// New model: active directed-ID rows own e, not raw h. No dormant state exists.
using Key=uint64_t;
struct Mem{Key key;V e;};using Memory=std::vector<Mem>;
struct Record{unsigned id;V x,v;double g;};
struct RowData{Key key;V e,u,I;B S;};
struct State{Memory memory;std::vector<Key> ever;M frame{B(1),B(0),B(0),B(1)};B work,loading,death;};
struct Leg{Memory memory;std::vector<RowData> rows;std::vector<V> force;B oldE,mappedE,keptE,deadE,newE,rowW,nodeW,loss,ledger,frameDelta;
  uint64_t births=0,deaths=0,kept=0,returning=0;Key born_sample=0,dead_sample=0,kept_sample=0;
  double condition=0,minD=Inf,maxD=0,maxForce=0;};
Key PairKey(unsigned i,unsigned j){Need(i!=j,"Distinct native row IDs required");return (Key(i)<<32)|Key(j);}
const Mem* Find(const Memory& a,Key k){const auto i=std::lower_bound(a.begin(),a.end(),k,[](const Mem& m,Key q){return m.key<q;});return i!=a.end()&&i->key==k?&*i:nullptr;}
B Energy(const Memory& a){B e;for(const auto& m:a)e=e+B(.5)*Dot(m.e,m.e);return e;}
std::vector<Record> Records(unsigned step,const M& frame,bool rotated){
  const double scales[8]={1,1.12,1.25,1.05,.92,1.18,1,.97};
  const double shears[8]={0,.12,-.08,.22,-.12,.08,0,.15};
  const M shape{B(scales[step]),B(scales[step]*shears[step]),B(0),B(scales[step])};
  const B spin(.125*(int(step%3)-1));const M omega{B(0),-spin,spin,B(0)};
  std::vector<Record> a;
  for(unsigned iz=0;iz<7;iz++)for(unsigned ix=0;ix<7;ix++){
    const unsigned i=iz*7+ix;const V initial{B((int(ix)-3)*.04+.002*std::sin(.73*i)),B((int(iz)-3)*.04+.002*std::cos(.51*i))};
    const V baseX=Mul(shape,initial),baseV{B(std::sin(.37*i+.13*step)),B(std::cos(.21*i-.07*step))};
    const V x=Mul(frame,baseX);V v=Mul(frame,baseV);
    if(rotated)v=v+Mul(omega,x)+V{B(.2),B(-.3)}; // annihilated rigid addition, not an Omega integrator.
    const double g=i%11==0?1:i%7==0?0:double(i%5)/4;
    a.push_back({1000+3*i,x,v,g});
  }return a;
}
std::vector<Record> PermuteAndCanonical(const std::vector<Record>& expected,unsigned step,bool rotated){
  auto a=expected;const unsigned shift=(step*(rotated?7:5)+(rotated?13:3))%N;
  std::rotate(a.begin(),a.begin()+shift,a.end());if(step%2)std::reverse(a.begin(),a.end());
  std::sort(a.begin(),a.end(),[](const Record& x,const Record& y){return x.id<y.id;});
  Need(a.size()==N,"Exactly 49 unique manufactured native IDs required");
  for(unsigned i=0;i<N;i++){Need(a[i].id==1000+3*i&&a[i].id==expected[i].id&&a[i].g==expected[i].g,
      "Canonical native ID/gamma ownership differs after input permutation");
    CloseV(a[i].x-expected[i].x,"permuted coordinates by native ID");CloseV(a[i].v-expected[i].v,"permuted velocity by native ID");}
  return a;
}
void SampleKey(std::ostream& s,Key k){if(k)s<<unsigned(k>>32)<<','<<unsigned(k&0xffffffffu);else s<<',';}
Leg Advance(State& state,const std::vector<Record>& input,const M& frame,B t,unsigned step,const char* label,std::ofstream& csv){
  const auto a=PermuteAndCanonical(input,step,std::string(label)=="rotated");std::vector<V> x,v;
  for(const auto& r:a){x.push_back(r.x);v.push_back(r.v);}const auto graph=MakeGraph(x);const auto p=ApplyP(graph,v);
  Leg out;out.condition=graph.condition;out.oldE=Energy(state.memory);Memory mapped=state.memory;
  const M map=Mul(frame,Transpose(state.frame));for(auto& m:mapped)m.e=Mul(map,m.e);
  out.mappedE=Energy(mapped);out.frameDelta=out.mappedE-out.oldE;Close(out.frameDelta,"known frame rotation preserves e energy");
  std::vector<Key> active,newEver;for(const auto& row:graph.rows)active.push_back(PairKey(a[row.i].id,a[row.j].id));
  std::sort(active.begin(),active.end());Need(std::adjacent_find(active.begin(),active.end())==active.end(),"Duplicate directed material row key");
  for(const auto& m:mapped)if(!std::binary_search(active.begin(),active.end(),m.key)){
    out.deadE=out.deadE+B(.5)*Dot(m.e,m.e);out.deaths++;if(!out.dead_sample)out.dead_sample=m.key;}
  B rowDE;std::vector<V> weightedAverage;
  for(size_t k=0;k<graph.rows.size();k++){
    const auto& row=graph.rows[k];const Key key=PairKey(a[row.i].id,a[row.j].id);const Mem* old=Find(mapped,key);
    V e0;if(old){e0=old->e;out.kept++;if(!out.kept_sample)out.kept_sample=key;}
    else{out.births++;newEver.push_back(key);if(!out.born_sample)out.born_sample=key;
      if(std::binary_search(state.ever.begin(),state.ever.end(),key))out.returning++;
      Need(e0.x.v==0&&e0.x.e==0&&e0.z.v==0&&e0.z.e==0,"Born row must have new exact zero e");}
    out.keptE=out.keptE+B(.5)*Dot(e0,e0);
    Need(Lo(row.D)>0,"Active row requires certified positive D; no epsilon weight floor");
    const B S=Sqrt(row.D);out.minD=std::min(out.minD,row.D.v);out.maxD=std::max(out.maxD,row.D.v);
    const V drive=S*p.residual[k];const B g(.5*(a[row.i].g+a[row.j].g));
    const auto local=ExactStep(e0,drive,B(1),g,t); // e energy is Euclidean: Dlocal=1.
    out.memory.push_back({key,local.h});out.rows.push_back({key,local.h,drive,local.I,S});
    weightedAverage.push_back(S*(local.I/t));rowDE=rowDE+local.de;out.rowW=out.rowW+local.work;out.loss=out.loss+local.loss;
  }
  const auto byKey=[](const auto& a,const auto& b){return a.key<b.key;};
  std::sort(out.memory.begin(),out.memory.end(),byKey);std::sort(out.rows.begin(),out.rows.end(),byKey);
  Need(out.memory.size()==active.size()&&out.kept+out.births==active.size(),"Active-only memory coverage differs");
  for(size_t k=0;k<active.size();k++)Need(out.memory[k].key==active[k],"New memory includes an inactive/wrong row ID");
  Close(out.mappedE-out.keptE-out.deadE,"kept plus deleted energy partition");
  out.newE=Energy(out.memory);Close(out.newE-out.keptE-rowDE,"independent endpoint memory energy sum");
  out.force=ApplyPT(graph,weightedAverage);V net;B torque;
  for(unsigned i=0;i<N;i++){out.force[i]=-out.force[i];net=net+out.force[i];torque=torque+Cross(graph.x[i],out.force[i]);
    out.nodeW=out.nodeW+t*Dot(v[i],out.force[i]);out.maxForce=std::max(out.maxForce,std::hypot(out.force[i].x.v,out.force[i].z.v));}
  CloseV(net,"average HG force net balance");Close(torque,"average HG force torque balance");Close(out.nodeW-out.rowW,"same P/S node work versus row integral work");
  out.ledger=out.newE-out.oldE+out.nodeW+out.loss+out.deadE;Close(out.ledger,"step energy including deleted-row numerical dissipation");
  Need(Hi(out.deadE)>=0&&Hi(out.loss)>=0,"Negative dissipation beyond arithmetic enclosure");
  state.work=state.work+out.nodeW;state.loading=state.loading+out.loss;state.death=state.death+out.deadE;
  const B cumulative=out.newE+state.work+state.loading+state.death;Close(cumulative,"cumulative energy/death ledger from initial zero memory");
  csv<<step<<','<<label<<','<<graph.rows.size()<<','<<out.kept<<','<<out.births<<','<<out.deaths<<','<<out.returning<<','<<graph.condition<<','<<out.minD<<','<<out.maxD<<','<<t.v<<','
    <<out.oldE.v<<','<<out.mappedE.v<<','<<out.keptE.v<<','<<out.deadE.v<<','<<out.newE.v<<','<<out.rowW.v<<','<<out.nodeW.v<<','<<out.loss.v<<','<<out.ledger.v<<','<<out.ledger.e<<','
    <<out.frameDelta.v<<','<<out.frameDelta.e<<','<<cumulative.v<<','<<cumulative.e<<','<<net.x.v<<','<<net.x.e<<','<<net.z.v<<','<<net.z.e<<','<<torque.v<<','<<torque.e<<','<<out.maxForce<<',';
  SampleKey(csv,out.born_sample);csv<<',';SampleKey(csv,out.dead_sample);csv<<',';SampleKey(csv,out.kept_sample);csv<<'\n';
  state.memory=out.memory;state.frame=frame;state.ever.insert(state.ever.end(),newEver.begin(),newEver.end());
  std::sort(state.ever.begin(),state.ever.end());state.ever.erase(std::unique(state.ever.begin(),state.ever.end()),state.ever.end());return out;
}
void CompareFrame(const Leg& a,const Leg& b,const M& R,unsigned step,std::ofstream& csv){
  Need(a.rows.size()==b.rows.size()&&a.births==b.births&&a.deaths==b.deaths&&a.returning==b.returning&&a.kept==b.kept,
    "Frame variants differ in directed ID graph/lifecycle");double emax=0,ebound=0,fmax=0,fbound=0;
  for(size_t k=0;k<a.rows.size();k++){Need(a.rows[k].key==b.rows[k].key,"Cross-frame material row IDs differ");
    const V de=b.rows[k].e-Mul(R,a.rows[k].e),du=b.rows[k].u-Mul(R,a.rows[k].u),di=b.rows[k].I-Mul(R,a.rows[k].I);
    CloseV(de,"keyed nonzero e frame covariance");CloseV(du,"same P/S drive plus superposed rigid velocity");CloseV(di,"exact e integral frame covariance");
    Close(b.rows[k].S-a.rows[k].S,"current scalar weight rotation invariance");
    if(std::abs(de.x.v)>emax){emax=std::abs(de.x.v);ebound=de.x.e;}if(std::abs(de.z.v)>emax){emax=std::abs(de.z.v);ebound=de.z.e;}}
  for(unsigned i=0;i<N;i++){const V df=b.force[i]-Mul(R,a.force[i]);CloseV(df,"current native-ID nodal force covariance");
    if(std::abs(df.x.v)>fmax){fmax=std::abs(df.x.v);fbound=df.x.e;}if(std::abs(df.z.v)>fmax){fmax=std::abs(df.z.v);fbound=df.z.e;}}
  const B de=b.newE-a.newE,dw=b.nodeW-a.nodeW,dd=b.deadE-a.deadE,dl=b.loss-a.loss;
  Close(de,"frame memory energy");Close(dw,"frame mechanical work");Close(dd,"frame discarded energy");Close(dl,"frame loading dissipation");
  csv<<step<<','<<a.rows.size()<<','<<emax<<','<<ebound<<','<<fmax<<','<<fbound<<','<<de.v<<','<<de.e<<','<<dw.v<<','<<dw.e<<','<<dd.v<<','<<dd.e<<','<<dl.v<<','<<dl.e<<'\n';
}
std::string Escape(const std::string& s){std::string out;for(char c:s){if(c=='"'||c=='\\')out+='\\';if(c=='\n'){out+="\\n";continue;}out+=c;}return out;}
} // namespace phg
int main(int argc,char** argv){using namespace phg;std::filesystem::path out;bool created=false;
  try{Need(argc==2,"Usage: C08H18HgEnergyMemoryR1.exe FRESHOUT");Need(std::numeric_limits<double>::is_iec559&&std::numeric_limits<double>::digits==53&&std::fegetround()==FE_TONEAREST,"IEEE binary64 round-to-nearest required");
    Need((_mm_getcsr()&((1u<<15)|(1u<<6)))==0,"FTZ/DAZ must be off");out=std::filesystem::absolute(argv[1]);Need(!std::filesystem::exists(out),"Existing complete/partial output protected");
    Need(std::filesystem::create_directory(out),"Cannot create exclusive output");created=true;
    std::ofstream steps(out/"steps.csv"),frames(out/"frame_covariance.csv");Need(bool(steps)&&bool(frames),"Cannot create fresh CSVs");steps<<std::setprecision(17);frames<<std::setprecision(17);
    steps<<"manufactured_step,frame,directed_rows,kept_rows,born_rows,dead_rows,returning_zero_births,max_LS_condition,D_min,D_max,interval_T,old_E,mapped_old_E,kept_initial_E,deleted_numerical_loss,new_E,W_rows,W_nodes,loading_loss,step_ledger_residual,step_ledger_bound,frame_energy_delta,frame_energy_bound,cumulative_ledger_residual,cumulative_ledger_bound,net_Fx,net_Fx_bound,net_Fz,net_Fz_bound,torque,torque_bound,max_nodal_force,born_sample_i,born_sample_j,dead_sample_i,dead_sample_j,kept_sample_i,kept_sample_j\n";
    frames<<"manufactured_step,directed_rows,max_e_covariance_error,bound_at_max_e,max_F_covariance_error,bound_at_max_F,delta_frame_E,delta_frame_E_bound,delta_frame_W,delta_frame_W_bound,delta_frame_deleted_E,delta_frame_deleted_E_bound,delta_frame_loading_loss,delta_frame_loading_loss_bound\n";
    const M identity{B(1),B(0),B(0),B(1)};const B c=B(3)/B(5),s=B(4)/B(5);const M turn{c,-s,s,c};M R=identity;
    State baseline,rotated;uint64_t born=0,dead=0,returning=0,totalRows=0;B totalDiscarded;
    for(unsigned step=0;step<8;step++){
      const auto a=Advance(baseline,Records(step,identity,false),identity,B(.125),step,"baseline",steps);
      const auto b=Advance(rotated,Records(step,R,true),R,B(.125),step,"rotated",steps);
      CompareFrame(a,b,R,step,frames);born+=a.births;dead+=a.deaths;returning+=a.returning;totalRows+=a.rows.size();totalDiscarded=totalDiscarded+a.deadE;R=Mul(turn,R);
    }
    Need(dead>0&&returning>0&&Lo(totalDiscarded)>0,"Manufactured sequence failed to exercise finite-energy death and zero rebirth");
    steps.flush();frames.flush();Need(bool(steps)&&bool(frames),"CSV write failed");
    std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\n  \"stage\": \"c08_h18_hg_energy_memory_r1\",\n  \"passed\": true,\n  \"manufactured_steps\": 8,\n  \"frames\": 2,\n  \"nodes\": 49,\n  \"step_rows\": 16,\n  \"frame_covariance_rows\": 8,\n  \"baseline_directed_row_updates\": "<<totalRows<<",\n  \"baseline_births\": "<<born<<",\n  \"baseline_deaths\": "<<dead<<",\n  \"baseline_returning_zero_births\": "<<returning<<",\n  \"baseline_deleted_numerical_energy\": "<<totalDiscarded.v<<",\n  \"baseline_deleted_energy_bound\": "<<totalDiscarded.e<<",\n  \"scalar_certificates\": "<<scalar_checks<<",\n  \"max_error_over_budget\": "<<max_ratio<<",\n  \"event_interval_overlaps\": "<<event_interval_overlaps<<",\n  \"value_add_sub_operations\": "<<count.add<<",\n  \"value_multiply_operations\": "<<count.mul<<",\n  \"value_divide_operations\": "<<count.div<<",\n  \"value_sqrt_operations\": "<<count.sqrt
      <<",\n  \"active_edge_only_energy_state_new_model\": true,\n  \"raw_variable_D_GNOG_equivalent\": false,\n  \"same_current_P_S_in_drive_and_force\": true,\n  \"fixed_interval_contract_and_lifecycle_ledger\": true,\n  \"dormant_edge_reawakening\": false,\n  \"ID_permutations_canonicalized\": true,\n  \"known_frame_mapping_only\": true,\n  \"Omega_ODE_integration_qualified\": false,\n  \"dynamic_J_qualified\": false,\n  \"DP_producer_qualified\": false,\n  \"actual_Symplectic_qualified\": false,\n  \"same_stage_Darcy_qualified\": false,\n  \"C08_qualified\": false,\n  \"history_restart_qualified\": false,\n  \"physical_steps\": 0,\n  \"material_calls\": 0,\n  \"Darcy_calls\": 0,\n  \"solver_invocations\": 0,\n  \"native_invocations\": 0,\n  \"physical_source_objects_linked\": 0,\n  \"physical_acceptance\": false\n}\n";
    done.flush();Need(bool(done),"Completion write failed");std::cout<<"New active-edge e-model toy ledger passed; physical_acceptance=false\n";return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';if(created){std::ofstream d(out/"failure.json");d<<"{\"stage\":\"c08_h18_hg_energy_memory_r1\",\"passed\":false,\"first_failure\":\""<<Escape(e.what())<<"\",\"partial_outputs_preserved\":true,\"physical_acceptance\":false}\n";}return 1;}
}
