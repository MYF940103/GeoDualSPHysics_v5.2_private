// Shared Audit/Fast numerical core for a frozen-state implementation/cost test only.
#ifndef C08_H18_HG_NUMERIC_R1_HPP
#define C08_H18_HG_NUMERIC_R1_HPP
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <climits>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace c08gpucheck {
struct Config {double h=0,support=0,bwen=0,G=0,xi=0,dt=0;unsigned firstid=0,count=0;};
struct Input {unsigned id=0;double x=0,z=0,vx=0,vz=0,volume=0,mass=0,gamma=0;};
struct Force {unsigned id=0;double x=0,z=0,error_x=0,error_z=0;};
struct Metrics {
  uint64_t pairs=0,rows=0,kept=0,born=0,dead=0,returning=0;
  uint64_t known_constant_receivers=0,known_constant_rows=0;
  uint64_t add_ops=0,mul_ops=0,div_ops=0,sqrt_ops=0,certificates=0,event_overlaps=0;
  double Eold=0,Eold_bound=0,Ekept=0,Ekept_bound=0,Edead=0,Edead_bound=0,Enew=0,Enew_bound=0;
  double work_rows=0,work_rows_bound=0,work_nodes=0,work_nodes_bound=0;
  double loading_loss=0,loading_loss_bound=0,rotation_change=0,rotation_change_bound=0;
  double ledger=0,ledger_bound=0,adjoint_work=0,adjoint_work_bound=0;
  double net_x=0,net_x_bound=0,net_z=0,net_z_bound=0,torque=0,torque_bound=0;
  double condition=0,lambda_raw=0,lambda_upper=0,dt_ratio_raw=0,dt_ratio=0,dt_ratio_bound=0,min_r=0,min_r_bound=0;
  double max_omega=0,max_omega_bound=0,max_omega_upper=0,spin_raw=0,spin_bound=0;
  bool audited_enclosures=false;
  double D_min=0,D_max=0,max_force=0,max_error_ratio=0;
};
struct Focus {
  unsigned id_i=0,id_j=0;
  double D=0,D_bound=0,gamma=0,omega=0,omega_bound=0,r=0,r_bound=0;
  double eold_x=0,eold_z=0,enew_x=0,enew_z=0,u_x=0,u_z=0,I_x=0,I_z=0;
  double eold_x_bound=0,eold_z_bound=0,enew_x_bound=0,enew_z_bound=0,u_x_bound=0,u_z_bound=0,I_x_bound=0,I_z_bound=0;
  double work=0,work_bound=0,loading_loss=0,loading_loss_bound=0;
  double rotation_change=0,rotation_change_bound=0,ledger=0,ledger_bound=0;
};


struct NodeTrace {unsigned id=0;std::array<double,18> values{};};
struct RowTrace {uint64_t key=0;std::array<double,43> values{};unsigned branch=0,knownconstant=0;};
inline constexpr std::array<const char*,18> NodeTraceNames{{"x","z","vx","vz","volume","mass","gamma","Lxx","Lxz","Lzx","Lzz","omega","Mxx","Mxz","Mzz","Mdet","degree","lambda_raw"}};
inline constexpr std::array<const char*,43> RowTraceNames{{"dx","dz","r","a","D","S","gamma","omega","residual_x","residual_z","computed_u_x","computed_u_z","drive_x","drive_z","en_x","en_z","rotated_start_x","rotated_start_z","t1","t2","integral_x","integral_z","after_drive_x","after_drive_z","after_rotation_x","after_rotation_z","weighted_middle_x","weighted_middle_z","A","Z","Eold","Enew","work","loss","rotation_change","ledger","angle","Eafter_first_rotation","Eafter_drive","width","gamma_i","gamma_j","kernel_w"}};
struct VecInput {double x=0,z=0,error_x=0,error_z=0;};
struct SpinResult {VecInput e;double energy_old=0,energy_new=0,energy_delta=0,energy_delta_bound=0;uint64_t certificates=0;double max_error_ratio=0;unsigned branch=0;bool audited_enclosures=false;};
namespace detail {
template<bool Checked> struct Core {

static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static void Need(bool b,const std::string& s){if(!b)throw std::runtime_error(s);}
static bool SameBits(double a,double b){return std::memcmp(&a,&b,sizeof(double))==0;}
static constexpr double U=std::numeric_limits<double>::epsilon()/2;
static constexpr double Inf=std::numeric_limits<double>::infinity();
struct Audit {uint64_t add=0,mul=0,div=0,sqrt=0,checks=0,events=0;double maxratio=0;};
inline static thread_local Audit* audit=nullptr;
struct AuditScope {Audit* old;explicit AuditScope(Audit& a):old(audit){audit=&a;}~AuditScope(){audit=old;}};
static double Up(double x){Need(std::isfinite(x)&&x>=0,"HG nonfinite arithmetic enclosure");return std::nextafter(x,Inf);}
static double EA(double a,double b){return Up(a+b);} static double EM(double a,double b){return Up(a*b);}
static double ED(double a,double b){Need(b>0,"HG error-bound divisor is not positive");return Up(a/b);}
static double Round(double x){return EA(EM(Up(U/(1-U)),std::abs(x)),std::numeric_limits<double>::denorm_min());}
// One ordered binary64 value path. Audit=true additionally carries an outward
// absolute arithmetic-error enclosure; Fast=false claims no such certificates.
// Numerical inputs are the caller's actual stored doubles, not a fitted field.
struct B {double v=0,e=0;B()=default;B(double x):v(x){Need(std::isfinite(x),"HG nonfinite input");}
  B(double x,double error):v(x){Need(std::isfinite(v),"HG nonfinite value");if constexpr(Checked){e=error;Need(std::isfinite(e)&&e>=0,"HG nonfinite arithmetic enclosure");}}};
friend B operator+(B a,B b){const double v=a.v+b.v;if constexpr(Checked){if(audit)audit->add++;return B(v,EA(EA(a.e,b.e),Round(v)));}else return B(v);}
friend B operator-(B a,B b){const double v=a.v-b.v;if constexpr(Checked){if(audit)audit->add++;return B(v,EA(EA(a.e,b.e),Round(v)));}else return B(v);}
friend B operator-(B a){if constexpr(Checked)return B(-a.v,a.e);else return B(-a.v);}
friend B operator*(B a,B b){const double v=a.v*b.v;if constexpr(Checked){if(audit)audit->mul++;return B(v,EA(EA(EA(EM(std::abs(a.v),b.e),EM(std::abs(b.v),a.e)),EM(a.e,b.e)),Round(v)));}else return B(v);}
friend B operator/(B a,B b){Need(b.v!=0,"HG numerical division denominator is zero");const double v=a.v/b.v;
  if constexpr(Checked){if(audit)audit->div++;const double low=std::nextafter(std::abs(b.v)-b.e,-Inf);Need(low>0,"HG division enclosure includes zero; no regularization");const double r=Round(v);return B(v,EA(ED(EA(a.e,EM(EA(std::abs(v),r),b.e)),low),r));}else return B(v);}
static double Lo(B a){if constexpr(Checked)return std::nextafter(a.v-a.e,-Inf);else return a.v;}
static double Hi(B a){if constexpr(Checked)return std::nextafter(a.v+a.e,Inf);else return a.v;}
static double AbsHi(B a){if constexpr(Checked)return Up(std::abs(a.v)+a.e);else return std::abs(a.v);}
static B Sqrt(B a){Need(a.v>0,"HG numerical sqrt argument not positive");const double v=std::sqrt(a.v);
  if constexpr(Checked){if(audit)audit->sqrt++;const double lo=Lo(a);Need(lo>0,"HG sqrt argument not certified positive");const double r=Round(v),sl=std::nextafter(std::sqrt(lo),-Inf),sv=std::nextafter(v-r,-Inf);const double den=std::nextafter(sl+sv,-Inf);Need(den>0,"HG undefined sqrt enclosure");return B(v,EA(ED(a.e,den),r));}else return B(v);}
static void Close(B a,const char* what){if constexpr(Checked){const double r=a.e>0?std::abs(a.v)/a.e:(a.v==0?0:Inf);Need(std::isfinite(r)&&r<=1,std::string("HG arithmetic certificate failed: ")+what);if(audit){audit->checks++;audit->maxratio=(std::max)(audit->maxratio,r);}}}
struct V {B x,z;};
friend V operator+(V a,V b){return {a.x+b.x,a.z+b.z};} friend V operator-(V a,V b){return {a.x-b.x,a.z-b.z};}
friend V operator-(V a){return {-a.x,-a.z};} friend V operator*(B a,V b){return {a*b.x,a*b.z};}
friend V operator/(V a,B b){return {a.x/b,a.z/b};}
static B Dot(V a,V b){return a.x*b.x+a.z*b.z;} static B Cross(V a,V b){return a.x*b.z-a.z*b.x;}
static void CloseV(V a,const char* what){Close(a.x,what);Close(a.z,what);}
struct M {B xx,xz,zx,zz;};
friend M operator+(M a,M b){return {a.xx+b.xx,a.xz+b.xz,a.zx+b.zx,a.zz+b.zz};}
friend M operator*(B a,M b){return {a*b.xx,a*b.xz,a*b.zx,a*b.zz};}
static V Mul(M a,V b){return {a.xx*b.x+a.xz*b.z,a.zx*b.x+a.zz*b.z};}
static M Outer(V a,V b){return {a.x*b.x,a.x*b.z,a.z*b.x,a.z*b.z};}
struct Moment {B xx,xz,zz,det;double condition=0;};
static M RightInverse(M n,const Moment& m){return {(n.xx*m.zz-n.xz*m.xz)/m.det,
  (n.xz*m.xx-n.xx*m.xz)/m.det,(n.zx*m.zz-n.zz*m.xz)/m.det,(n.zz*m.xx-n.zx*m.xz)/m.det};}
struct Row {unsigned i=0,j=0;V d;B a,D,r,w;};
struct Graph {std::vector<V> x,v;std::vector<B> volume,mass,degree,lambda_nodes;std::vector<Moment> moment;std::vector<Row> rows;
  double condition=0,minr=Inf,minrError=0,lambdaRaw=0,lambda=0,Dmin=Inf,Dmax=0,dtRatioRaw=0,dtRatio=0,dtRatioError=0;uint64_t pairs=0;};

static Graph MakeGraph(const Config& c,const std::vector<Input>& a){
  const unsigned n=c.count;Need(a.size()==n,"HG actual soil extent differs");Graph g;
  g.x.resize(n);g.v.resize(n);g.volume.resize(n);g.mass.resize(n);g.moment.resize(n);
  double xmin=Inf,xmax=-Inf,zmin=Inf,zmax=-Inf;
  for(unsigned i=0;i<n;i++){const auto& q=a[i];Need(q.id==c.firstid+i,"HG native IDs must be complete and canonical");
    Need(std::isfinite(q.x)&&std::isfinite(q.z)&&std::isfinite(q.vx)&&std::isfinite(q.vz)
      &&std::isfinite(q.volume)&&q.volume>0&&std::isfinite(q.mass)&&q.mass>0
      &&std::isfinite(q.gamma)&&q.gamma>=0&&q.gamma<=1,"HG invalid actual coordinate/velocity/volume/mass/gamma");
    g.x[i]={B(q.x),B(q.z)};g.v[i]={B(q.vx),B(q.vz)};g.volume[i]=B(q.volume);g.mass[i]=B(q.mass);
    xmin=(std::min)(xmin,q.x);xmax=(std::max)(xmax,q.x);zmin=(std::min)(zmin,q.z);zmax=(std::max)(zmax,q.z);}
  // Same ascending-ID, head/next linked-cell and pair traversal as the original
  // nonperiodic JSphHourglassCpu::BuildPairs. No O(N^2) manufactured-cloud scan.
  const double nxv=std::floor((xmax-xmin)/c.support)+1,nzv=std::floor((zmax-zmin)/c.support)+1;
  Need(nxv>=1&&nzv>=1&&nxv<INT_MAX&&nzv<INT_MAX&&nxv*nzv<INT_MAX,"HG cell grid outside bounded integer domain");
  const int nx=int(nxv),nz=int(nzv);std::vector<int> heads(size_t(nx)*nz,-1),next(n,-1);
  for(unsigned i=0;i<n;i++){const int cx=(std::min)(nx-1,int((a[i].x-xmin)/c.support)),cz=int((a[i].z-zmin)/c.support);
    Need(cx>=0&&cx<nx&&cz>=0&&cz<nz,"HG actual cell index outside grid");next[i]=heads[cz*nx+cx];heads[cz*nx+cx]=int(i);}
  const B h(c.h),cut=B(c.support)*B(c.support);std::vector<B> degree(n);
  g.rows.reserve(size_t(n)*80);
  for(unsigned i=0;i<n;i++){
    const int cx=(std::min)(nx-1,int((a[i].x-xmin)/c.support)),cz=int((a[i].z-zmin)/c.support);
    for(int z=(std::max)(0,cz-1);z<=(std::min)(nz-1,cz+1);z++)for(int x=(std::max)(0,cx-1);x<=(std::min)(nx-1,cx+1);x++)
      for(int jj=heads[z*nx+x];jj>=0;jj=next[jj]){
        const unsigned j=unsigned(jj);if(j<=i)continue;const V d=g.x[i]-g.x[j];const B rr=Dot(d,d);
        if constexpr(Checked)Need(Hi(rr)<Lo(cut)||Lo(rr)>Hi(cut),"HG support membership is arithmetically ambiguous");
        if(rr.v>=cut.v)continue;
        Need(rr.v>0,std::string("HG coincident actual pair IDs ")+std::to_string(a[i].id)+"/"+std::to_string(a[j].id));
        if constexpr(Checked)Need(Lo(rr)>0,"HG actual pair distance is not certified positive");
        const B radius=Sqrt(rr),s=B(1)-radius/(B(2)*h);Need(s.v>0,"HG nonpositive numerical Wendland interior weight");if constexpr(Checked)Need(Lo(s)>0,"HG positive Wendland interior weight not certified");
        const B w=-(B(c.bwen)/h)*s*s*s,beta=B(c.xi)*B(c.G)*g.volume[i]*g.volume[j]*w,D=beta/B(2);
        Need(w.v>0&&D.v>0,"HG numerical weight/energy factor not positive");if constexpr(Checked)Need(Lo(w)>0&&Lo(D)>0,"HG current positive weight/energy factor not certified");
        g.rows.push_back({i,j,d,g.volume[j]*w,D,radius,w});g.rows.push_back({j,i,g.x[j]-g.x[i],g.volume[i]*w,D,radius,w});
        degree[i]=degree[i]+beta;degree[j]=degree[j]+beta;g.pairs++;
        if(radius.v<g.minr){g.minr=radius.v;g.minrError=radius.e;}g.Dmin=(std::min)(g.Dmin,D.v);g.Dmax=(std::max)(g.Dmax,D.v);
      }
  }
  Need(g.pairs>0&&g.rows.size()==2*g.pairs,"HG empty/invalid actual directed graph");
  std::sort(g.rows.begin(),g.rows.end(),[](const Row& a,const Row& b){return a.i<b.i||(a.i==b.i&&a.j<b.j);});
  for(const auto& r:g.rows){auto& m=g.moment[r.i];m.xx=m.xx+r.a*r.d.x*r.d.x;m.xz=m.xz+r.a*r.d.x*r.d.z;m.zz=m.zz+r.a*r.d.z*r.d.z;}
  for(unsigned i=0;i<n;i++){auto& m=g.moment[i];m.det=m.xx*m.zz-m.xz*m.xz;
    const double tr=m.xx.v+m.zz.v,hi=.5*(tr+std::hypot(m.xx.v-m.zz.v,2*m.xz.v)),lo=m.det.v/hi;
    Need(std::isfinite(m.det.v)&&lo>0&&hi/lo<1e8,"HG original soil-only LS rank/condition guard rejected");
    if constexpr(Checked)Need(Lo(m.det)>0,"HG positive LS determinant not arithmetically certified; no ridge");
    m.condition=hi/lo;g.condition=(std::max)(g.condition,m.condition);
    const B lambda=B(2)*degree[i]/g.mass[i];Need(lambda.v>0,"HG frozen stiffness degree/mass not positive");if constexpr(Checked)Need(Lo(lambda)>0,"HG frozen stiffness degree/mass not certified positive");g.lambdaRaw=(std::max)(g.lambdaRaw,lambda.v);g.lambda=(std::max)(g.lambda,Hi(lambda));g.lambda_nodes.push_back(lambda);}
  Need(std::isfinite(g.lambda)&&g.lambda>0,"HG undefined frozen stiffness upper bound");
  g.degree=degree;const B rawRatio=B(c.dt)*Sqrt(B(g.lambdaRaw));Need(rawRatio.v<=.2,"HG full 5us exceeds 0.2 numerical frozen stiffness time scale");g.dtRatioRaw=rawRatio.v;
  const B ratio=B(c.dt)*Sqrt(B(g.lambda));if constexpr(Checked)Need(Hi(ratio)<=.2,"HG full 5us stiffness interval not certified");g.dtRatio=ratio.v;g.dtRatioError=ratio.e;return g;
}
struct Forward {std::vector<M> L;std::vector<V> residual;};
static Forward ApplyP(const Graph& g){const size_t n=g.x.size();Forward f;f.L.resize(n);f.residual.reserve(g.rows.size());std::vector<M> numerator(n);
  for(const auto& r:g.rows)numerator[r.i]=numerator[r.i]+r.a*Outer(g.v[r.i]-g.v[r.j],r.d);
  for(size_t i=0;i<n;i++)f.L[i]=RightInverse(numerator[i],g.moment[i]);
  for(const auto& r:g.rows)f.residual.push_back(g.v[r.i]-g.v[r.j]-Mul(f.L[r.i],r.d));return f;}
static std::vector<V> ApplyPT(const Graph& g,const std::vector<V>& y){
  Need(y.size()==g.rows.size(),"HG adjoint input extent differs");const size_t n=g.x.size();std::vector<M> z(n),t(n);std::vector<V> out(n),q(g.rows.size());std::vector<size_t> begin(n+1,0);
  for(const auto& r:g.rows)begin[r.i+1]++;for(size_t i=0;i<n;i++)begin[i+1]+=begin[i];
  for(size_t k=0;k<g.rows.size();k++){const auto& r=g.rows[k];z[r.i]=z[r.i]+Outer(y[k],r.d);}
  for(size_t i=0;i<n;i++)t[i]=RightInverse(z[i],g.moment[i]);
  for(size_t k=0;k<g.rows.size();k++){const auto& r=g.rows[k];q[k]=y[k]-r.a*Mul(t[r.i],r.d);}
  for(size_t i=0;i<n;i++){V force;for(size_t k=begin[i];k<begin[i+1];k++){const auto& r=g.rows[k];auto at=std::lower_bound(g.rows.begin()+begin[r.j],g.rows.begin()+begin[r.j+1],unsigned(i),[](const Row& row,unsigned j){return row.j<j;});Need(at!=g.rows.begin()+begin[r.j+1]&&at->j==i,"HG reference graph lacks true reverse row");const size_t rev=size_t(at-g.rows.begin());force=force-q[k]+q[rev];}out[i]=-force;}return out;
}
static B ClipTime(B q,B t){const double v=(std::max)(0.,(std::min)(t.v,q.v));if constexpr(Checked){const double low=(std::max)(0.,(std::min)(Lo(t),Lo(q))),high=(std::max)(0.,(std::min)(Hi(t),Hi(q)));if(audit&&((Lo(q)<=0&&Hi(q)>=0)||(Lo(q)<=Hi(t)&&Hi(q)>=Lo(t))))audit->events++;return B(v,Up((std::max)({0.,v-low,high-v})));}else return B(v);}
struct Step {V h,I;B A,Z,t1,t2,de,work,loss,total;unsigned branch=0;};
static Step ExactStep(V h0,V z,B d,B g,B t,bool knownZeroDrive=false){
  Need(t.v>0&&g.v>=0&&g.v<=1,"HG positive interval/gamma domain invalid");Need(d.v>=0,"HG PSD local D required");
  if constexpr(Checked)Need(Lo(t)>0&&g.e==0,"HG prescribed time/gamma enclosure invalid");
  Step o;o.A=Dot(h0,d*z);o.Z=Dot(z,d*z);const bool zeroD=d.v==0;
  if(zeroD||knownZeroDrive){if(knownZeroDrive)Need(z.x.v==0&&z.z.v==0,"HG known-zero drive has nonzero numerical value");
    if constexpr(Checked){if(zeroD)Need(d.e==0,"HG zero D is not analytically certified");if(knownZeroDrive)Need(z.x.e==0&&z.z.e==0,"HG zero-drive declaration has nonzero input enclosure");}
    o.t1=B(0);o.branch=zeroD?5u:0u;Close(o.A,"PSD-null row A");Close(o.Z,"PSD-null row Z");}
  else{Need(d.v>0&&o.Z.v>0,"HG nonconstant drive has nonpositive numerical Z; no threshold/regularization");
    if constexpr(Checked)Need(Lo(d)>0&&Lo(o.Z)>0,"HG nonzero row Z not certified; no threshold/regularization");
    const B crossing=-o.A/o.Z;o.t1=ClipTime(crossing,t);o.branch=crossing.v<=0?1u:crossing.v<t.v?2u:crossing.v==t.v?3u:4u;}
  o.t2=t-o.t1;const B drive=o.t1+g*o.t2;o.h=h0+drive*z;
  o.I=t*h0+(B(.5)*o.t1*o.t1+o.t1*o.t2+B(.5)*g*o.t2*o.t2)*z;
  o.de=B(.5)*d*(Dot(o.h,o.h)-Dot(h0,h0));o.work=-Dot(z,d*o.I);
  o.loss=(B(1)-g)*(o.t2*(o.A+o.Z*o.t1)+B(.5)*g*o.Z*o.t2*o.t2);o.total=o.de+o.work;
  if constexpr(Checked){Close(o.total+o.loss,"exact local energy/work/loading-loss");Need(Hi(o.loss)>=0&&o.total.v<=o.total.e,"HG fixed-input passivity violated beyond arithmetic enclosure");}
  return o;
}
static double PowUp(double a,unsigned p){double r=1.;for(unsigned i=0;i<p;i++)r=EM(r,a);return r;}
static V Rotate(V v,B angle){
  // Actual polynomial values, not an assumed libm-ULP bound. Explicit alternating
  // Taylor remainders enclose exact sin/cos throughout the certified small angle.
  Need(std::abs(angle.v)<.005,"HG numerical half-rotation exceeds bounded small-angle domain");const double radius=AbsHi(angle);if constexpr(Checked)Need(radius<.005,"HG half-rotation interval exceeds bounded small-angle domain");const B q=angle*angle;
  B cosine=B(1)+q*(B(-.5)+q*(B(1)/B(24)+q*(-B(1)/B(720)+q*(B(1)/B(40320)))));
  B sine=angle*(B(1)+q*(-B(1)/B(6)+q*(B(1)/B(120)+q*(-B(1)/B(5040)+q*(B(1)/B(362880))))));
  if constexpr(Checked){cosine.e=EA(cosine.e,ED(PowUp(radius,10),3628800.));sine.e=EA(sine.e,ED(PowUp(radius,11),39916800.));}
  return {cosine*v.x-sine*v.z,sine*v.x+cosine*v.z};
}
using Key=uint64_t;
static Key PairKey(unsigned i,unsigned j){Need(i!=j,"HG directed material pair IDs coincide");return (Key(i)<<32)|Key(j);}
struct Mem {Key key=0;V e;};
using Memory=std::vector<Mem>;
static const Mem* Find(const Memory& a,Key k){const auto i=std::lower_bound(a.begin(),a.end(),k,[](const Mem& m,Key key){return m.key<key;});return i!=a.end()&&i->key==k?&*i:nullptr;}
static B Energy(const Memory& a){B e;for(const auto& m:a)e=e+B(.5)*Dot(m.e,m.e);return e;}
static void Put(B a,double& value,double& error){value=a.v;error=a.e;}

};
} // namespace detail
template<bool Checked> class State;
template<bool Checked> struct Trial {
  std::vector<Force> force;std::vector<Focus> focus;Metrics stats;std::vector<NodeTrace> node_trace;std::vector<RowTrace> row_trace;
  typename detail::Core<Checked>::Memory next;bool full=false;uint64_t generation=0;
private:
  friend class State<Checked>;const State<Checked>* owner=nullptr;double maxOmegaUpper=0,maxOmegaRaw=0;
  std::vector<uint64_t> everNext;
};

template<bool Checked> class State : private detail::Core<Checked> {
  using C=detail::Core<Checked>;using B=typename C::B;using V=typename C::V;using M=typename C::M;using Graph=typename C::Graph;using Forward=typename C::Forward;
  using Memory=typename C::Memory;using Mem=typename C::Mem;using Key=typename C::Key;using Step=typename C::Step;using Audit=typename C::Audit;using AuditScope=typename C::AuditScope;
  using C::Need;using C::EA;using C::EM;using C::Up;using C::AbsHi;using C::Hi;using C::Dot;using C::Cross;using C::Close;using C::CloseV;using C::Put;
  using C::MakeGraph;using C::ApplyP;using C::ApplyPT;using C::Energy;using C::Find;using C::PairKey;using C::Rotate;using C::ExactStep;using C::Sqrt;using C::SameBits;
  Config config_;Memory memory_;std::vector<Key> ever_;uint64_t generation_=0;double spin_=0,spinRaw_=0;
public:
  explicit State(const Config& c):config_(c){
    Need(c.count>=3&&c.count<unsigned(INT_MAX)&&c.firstid<=UINT_MAX-c.count
      &&std::isfinite(c.h)&&c.h>0&&std::isfinite(c.support)&&c.support==2*c.h
      &&std::isfinite(c.bwen)&&c.bwen<0&&std::isfinite(c.G)&&c.G>0
      &&std::isfinite(c.xi)&&c.xi>0&&c.dt==.000005,"HG bounded 5us positive configuration invalid");
  }
  State(const State&)=delete;State& operator=(const State&)=delete;
  uint64_t Generation()const{return generation_;}size_t MemorySize()const{return memory_.size();}double SpinBound()const{return spin_;}double SpinRaw()const{return spinRaw_;}
  // A State is cold only when newly constructed. No API discards live memory.
  Trial<Checked> Evaluate(const std::vector<Input>& input,double width,bool full)const{
    Need(width==(full?config_.dt:config_.dt*.5),"HG trial interval/full flag differs from original stages");
    Audit arithmetic;AuditScope auditScope(arithmetic);auto nodes=input;std::sort(nodes.begin(),nodes.end(),[](const Input& a,const Input& b){return a.id<b.id;});
    const Graph graph=MakeGraph(config_,nodes);const Forward p=ApplyP(graph);Trial<Checked> out;out.stats.audited_enclosures=Checked;out.owner=this;out.full=full;out.generation=generation_;out.stats.pairs=graph.pairs;out.stats.rows=graph.rows.size();
    // Only this exact input certificate permits a zero drive. Every actual donor
    // of the receiver has the same original native velocity bits as the receiver;
    // consequently dv=0, the LS numerator is exactly zero, and this one-sided
    // residual is analytically zero. Computed value==0 or a small residual alone
    // is never a certificate. Keep the original P, moments and PT calculations.
    std::vector<bool> knownConstant(config_.count,true);
    for(const auto& row:graph.rows)if(!SameBits(nodes[row.i].vx,nodes[row.j].vx)||!SameBits(nodes[row.i].vz,nodes[row.j].vz))knownConstant[row.i]=false;
    for(unsigned i=0;i<config_.count;i++)if(knownConstant[i]){
      Close(p.L[i].xx,"exact-input constant receiver LS xx");Close(p.L[i].xz,"exact-input constant receiver LS xz");
      Close(p.L[i].zx,"exact-input constant receiver LS zx");Close(p.L[i].zz,"exact-input constant receiver LS zz");out.stats.known_constant_receivers++;
    }
    out.stats.condition=graph.condition;out.stats.lambda_raw=graph.lambdaRaw;out.stats.lambda_upper=graph.lambda;out.stats.dt_ratio_raw=graph.dtRatioRaw;out.stats.dt_ratio=graph.dtRatio;out.stats.dt_ratio_bound=graph.dtRatioError;
    out.stats.min_r=graph.minr;out.stats.min_r_bound=graph.minrError;out.stats.D_min=graph.Dmin;out.stats.D_max=graph.Dmax;
    std::vector<B> omega(config_.count);for(unsigned i=0;i<config_.count;i++){
      // In (x,z) coordinates exp([[0,-omega],[omega,0]]T), hence this sign.
      omega[i]=B(.5)*(p.L[i].zx-p.L[i].xz);out.stats.max_omega=(std::max)(out.stats.max_omega,std::abs(omega[i].v));out.maxOmegaUpper=(std::max)(out.maxOmegaUpper,AbsHi(omega[i]));}
    out.maxOmegaRaw=out.stats.max_omega;out.stats.max_omega_upper=out.maxOmegaUpper;
    out.stats.spin_raw=spinRaw_+config_.dt*out.maxOmegaRaw;Need(out.stats.spin_raw<.01,"HG accumulated numerical n/h spin exceeds 0.01 rad");
    if constexpr(Checked){out.stats.max_omega_bound=Up(out.maxOmegaUpper-out.stats.max_omega);out.stats.spin_bound=EA(spin_,EM(config_.dt,out.maxOmegaUpper));Need(out.stats.spin_bound<.01,"HG accumulated spin enclosure exceeds 0.01 rad");}else out.stats.spin_bound=out.stats.spin_raw;
    for(unsigned i=0;i<config_.count;i++){NodeTrace nt;nt.id=nodes[i].id;nt.values={{nodes[i].x,nodes[i].z,nodes[i].vx,nodes[i].vz,nodes[i].volume,nodes[i].mass,nodes[i].gamma,p.L[i].xx.v,p.L[i].xz.v,p.L[i].zx.v,p.L[i].zz.v,omega[i].v,graph.moment[i].xx.v,graph.moment[i].xz.v,graph.moment[i].zz.v,graph.moment[i].det.v,graph.degree[i].v,graph.lambda_nodes[i].v}};out.node_trace.push_back(nt);}
    B oldEnergy=Energy(memory_),keptEnergy,deadEnergy,newEnergy,rowWork,loss,rotationChange;std::vector<Key> active;active.reserve(graph.rows.size());
    for(const auto& row:graph.rows)active.push_back(PairKey(nodes[row.i].id,nodes[row.j].id));std::sort(active.begin(),active.end());Need(std::adjacent_find(active.begin(),active.end())==active.end(),"HG duplicate actual directed material pair");
    for(const auto& m:memory_)if(!std::binary_search(active.begin(),active.end(),m.key)){deadEnergy=deadEnergy+B(.5)*Dot(m.e,m.e);out.stats.dead++;}
    std::vector<V> y; y.reserve(graph.rows.size());out.next.reserve(graph.rows.size());out.everNext=ever_;
    for(size_t k=0;k<graph.rows.size();k++){
      const auto& row=graph.rows[k];const unsigned idi=nodes[row.i].id,idj=nodes[row.j].id;const Key key=PairKey(idi,idj);const Mem* old=Find(memory_,key);V en;
      if(old){en=old->e;out.stats.kept++;}else{out.stats.born++;if(std::binary_search(ever_.begin(),ever_.end(),key))out.stats.returning++;out.everNext.push_back(key);}
      const B e0=B(.5)*Dot(en,en);keptEnergy=keptEnergy+e0;const B angle=omega[row.i]*B(width*.5);const V er=Rotate(en,angle);
      const B S=Sqrt(row.D);const V computedU=S*p.residual[k];V u=computedU;
      if(knownConstant[row.i]){CloseV(computedU,"exact-input constant one-sided drive versus zero");u=V{};out.stats.known_constant_rows++;}
      const double g=.5*nodes[row.i].gamma+.5*nodes[row.j].gamma;
      const Step local=ExactStep(er,u,B(1),B(g),B(width),knownConstant[row.i]);const V e1=Rotate(local.h,angle);
      const B rotation=(B(.5)*Dot(er,er)-e0)+(B(.5)*Dot(e1,e1)-B(.5)*Dot(local.h,local.h));Close(rotation,"two certified half-rotations preserve row energy");
      const B e1energy=B(.5)*Dot(e1,e1),rowLedger=e1energy-e0+local.work+local.loss;Close(rowLedger,"split-rotation row ledger");
      // Only the unrotated middle integral enters the conjugate current PT.
      const V middle=S*(local.I/B(width));y.push_back(middle);out.next.push_back({key,e1});newEnergy=newEnergy+e1energy;rowWork=rowWork+local.work;loss=loss+local.loss;rotationChange=rotationChange+rotation;
      RowTrace rt;rt.key=key;rt.branch=local.branch;rt.knownconstant=unsigned(knownConstant[row.i]);
      rt.values={{row.d.x.v,row.d.z.v,row.r.v,row.a.v,row.D.v,S.v,g,omega[row.i].v,p.residual[k].x.v,p.residual[k].z.v,computedU.x.v,computedU.z.v,u.x.v,u.z.v,en.x.v,en.z.v,er.x.v,er.z.v,local.t1.v,local.t2.v,local.I.x.v,local.I.z.v,local.h.x.v,local.h.z.v,e1.x.v,e1.z.v,middle.x.v,middle.z.v,local.A.v,local.Z.v,e0.v,e1energy.v,local.work.v,local.loss.v,rotation.v,rowLedger.v,angle.v,(B(.5)*Dot(er,er)).v,(B(.5)*Dot(local.h,local.h)).v,width,nodes[row.i].gamma,nodes[row.j].gamma,row.w.v}};out.row_trace.push_back(rt);
      if(idi==6817||idi==6866||idj==6817||idj==6866){Focus f;f.id_i=idi;f.id_j=idj;f.D=row.D.v;f.D_bound=row.D.e;f.gamma=g;f.omega=omega[row.i].v;f.omega_bound=omega[row.i].e;f.r=row.r.v;f.r_bound=row.r.e;
        f.eold_x=en.x.v;f.eold_z=en.z.v;f.enew_x=e1.x.v;f.enew_z=e1.z.v;f.u_x=u.x.v;f.u_z=u.z.v;f.I_x=local.I.x.v;f.I_z=local.I.z.v;
        f.eold_x_bound=en.x.e;f.eold_z_bound=en.z.e;f.enew_x_bound=e1.x.e;f.enew_z_bound=e1.z.e;
        f.u_x_bound=u.x.e;f.u_z_bound=u.z.e;f.I_x_bound=local.I.x.e;f.I_z_bound=local.I.z.e;
        Put(local.work,f.work,f.work_bound);Put(local.loss,f.loading_loss,f.loading_loss_bound);Put(rotation,f.rotation_change,f.rotation_change_bound);Put(rowLedger,f.ledger,f.ledger_bound);out.focus.push_back(f);}
    }
    std::sort(out.row_trace.begin(),out.row_trace.end(),[](const RowTrace& a,const RowTrace& b){return a.key<b.key;});
    std::sort(out.next.begin(),out.next.end(),[](const Mem& a,const Mem& b){return a.key<b.key;});std::sort(out.everNext.begin(),out.everNext.end());out.everNext.erase(std::unique(out.everNext.begin(),out.everNext.end()),out.everNext.end());
    Need(out.next.size()==active.size()&&out.stats.kept+out.stats.born==active.size(),"HG active-only memory coverage differs");for(size_t k=0;k<active.size();k++)Need(out.next[k].key==active[k],"HG trial memory includes wrong/inactive material pair");
    Close(oldEnergy-keptEnergy-deadEnergy,"active/dead memory energy partition");Close(Energy(out.next)-newEnergy,"independent next-memory energy sum");Close(rotationChange,"total half-rotation energy change");
    const auto adjoint=ApplyPT(graph,y);V net;B torque,nodeWork;
    out.force.reserve(config_.count);for(unsigned i=0;i<config_.count;i++){const V force=-adjoint[i];net=net+force;torque=torque+Cross(graph.x[i],force);nodeWork=nodeWork+B(width)*Dot(graph.v[i],force);
      Need(std::isfinite(force.x.v)&&std::isfinite(force.z.v),"HG nonfinite actual nodal force");out.force.push_back({nodes[i].id,force.x.v,force.z.v,force.x.e,force.z.e});out.stats.max_force=(std::max)(out.stats.max_force,std::hypot(force.x.v,force.z.v));}
    CloseV(net,"complete actual PT net force");Close(torque,"complete actual PT torque");const B adjointWork=nodeWork-rowWork;Close(adjointWork,"actual nodal work versus middle row integral");
    const B ledger=newEnergy-oldEnergy+nodeWork+loss+deadEnergy;Close(ledger,"actual stage active-memory/loading/dead ledger");if constexpr(Checked)Need(Hi(loss)>=0&&Hi(deadEnergy)>=0,"HG numerical loss is negative beyond enclosure");
    Put(oldEnergy,out.stats.Eold,out.stats.Eold_bound);Put(keptEnergy,out.stats.Ekept,out.stats.Ekept_bound);Put(deadEnergy,out.stats.Edead,out.stats.Edead_bound);Put(newEnergy,out.stats.Enew,out.stats.Enew_bound);
    Put(rowWork,out.stats.work_rows,out.stats.work_rows_bound);Put(nodeWork,out.stats.work_nodes,out.stats.work_nodes_bound);Put(loss,out.stats.loading_loss,out.stats.loading_loss_bound);Put(rotationChange,out.stats.rotation_change,out.stats.rotation_change_bound);
    Put(ledger,out.stats.ledger,out.stats.ledger_bound);Put(adjointWork,out.stats.adjoint_work,out.stats.adjoint_work_bound);Put(net.x,out.stats.net_x,out.stats.net_x_bound);Put(net.z,out.stats.net_z,out.stats.net_z_bound);Put(torque,out.stats.torque,out.stats.torque_bound);
    out.stats.add_ops=arithmetic.add;out.stats.mul_ops=arithmetic.mul;out.stats.div_ops=arithmetic.div;out.stats.sqrt_ops=arithmetic.sqrt;out.stats.certificates=arithmetic.checks;out.stats.event_overlaps=arithmetic.events;out.stats.max_error_ratio=arithmetic.maxratio;return out;
  }
  void Commit(const Trial<Checked>& full,const Trial<Checked>& predictor){
    Need(full.owner==this&&predictor.owner==this&&full.full&&!predictor.full
      &&full.generation==generation_&&predictor.generation==generation_,"HG commit requires same-generation full and predictor trials");
    Need(full.next.size()==full.stats.rows&&full.stats.kept+full.stats.born==full.stats.rows,"HG full trial memory coverage invalid before commit");
    const double raw=spinRaw_+config_.dt*(std::max)(full.maxOmegaRaw,predictor.maxOmegaRaw);Need(raw<.01,"HG accepted numerical spin exceeds 0.01 rad");
    double accepted=raw;if constexpr(Checked){accepted=EA(spin_,EM(config_.dt,(std::max)(full.maxOmegaUpper,predictor.maxOmegaUpper)));Need(accepted<.01,"HG accepted spin enclosure exceeds 0.01 rad");}
    memory_=full.next;ever_=full.everNext;spin_=accepted;spinRaw_=raw;generation_++;
  }
};


template<bool Checked> inline SpinResult Spin(VecInput input,double omega,double T,double gamma=.5){
  using C=detail::Core<Checked>;using B=typename C::B;using V=typename C::V;
  typename C::Audit arithmetic;typename C::AuditScope scope(arithmetic);
  C::Need(std::isfinite(omega)&&std::isfinite(T)&&T>0&&std::isfinite(gamma)&&gamma>=0&&gamma<=1,"Spin input domain invalid");
  const V initial{{input.x,input.error_x},{input.z,input.error_z}};const B angle=B(omega)*B(T*.5);
  const V half=C::Rotate(initial,angle);const auto middle=C::ExactStep(half,V{},B(1),B(gamma),B(T),true);const V next=C::Rotate(middle.h,angle);
  const B e0=B(.5)*C::Dot(initial,initial),e1=B(.5)*C::Dot(next,next),delta=e1-e0;
  if constexpr(Checked)C::Close(delta,"standalone repeated split-spin energy");
  SpinResult out;out.e={next.x.v,next.z.v,next.x.e,next.z.e};out.energy_old=e0.v;out.energy_new=e1.v;out.energy_delta=delta.v;out.energy_delta_bound=delta.e;out.certificates=arithmetic.checks;out.max_error_ratio=arithmetic.maxratio;out.branch=middle.branch;out.audited_enclosures=Checked;return out;
}
} // namespace c08gpucheck
#endif

