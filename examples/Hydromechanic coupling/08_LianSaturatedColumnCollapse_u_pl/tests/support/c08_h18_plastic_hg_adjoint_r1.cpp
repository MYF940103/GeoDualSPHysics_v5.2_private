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
using Basis=std::vector<std::vector<V>>;
Basis BuildBasisP(const Graph& g){Basis p;for(unsigned col=0;col<2*N;col++){
  std::vector<V> v(N);if(col%2)v[col/2].z=B(1);else v[col/2].x=B(1);p.push_back(ApplyP(g,v).residual);}return p;}
std::vector<V> BasisPT(const Basis& p,const std::vector<V>& y){std::vector<V> out(N);
  for(unsigned col=0;col<2*N;col++){B sum;for(size_t k=0;k<y.size();k++)sum=sum+Dot(p[col][k],y[k]);
    if(col%2)out[col/2].z=sum;else out[col/2].x=sum;}return out;}
std::vector<B> Gamma(const Graph& g,unsigned mode){std::vector<B> node(N),out;
  for(unsigned i=0;i<N;i++)node[i]=B(mode==0?1:mode==1?0:(i%11==0?1:i%7==0?0:double(i%5)/4));
  for(const auto& r:g.rows)out.push_back((node[r.i]+node[r.j])/B(2));return out;}
std::vector<V> Weighted(const Graph& g,const std::vector<B>& gamma,const std::vector<V>& r){
  std::vector<V> out;for(size_t k=0;k<r.size();k++)out.push_back((g.rows[k].D*gamma[k])*r[k]);return out;}
std::vector<V> Negative(std::vector<V> f){for(auto& v:f)v=-v;return f;}
B Inner(const std::vector<V>& a,const std::vector<V>& b){Need(a.size()==b.size(),"Inner extent");B out;
  for(size_t i=0;i<a.size();i++)out=out+Dot(a[i],b[i]);return out;}
std::vector<V> OldRateForce(const Graph& g,const Forward& p){
  std::vector<V> out(N);for(size_t k=0;k<g.rows.size();k+=2){const auto& r=g.rows[k];
    // Natural reversed directed residual is -r_j in the canonical i-j direction.
    const V f=-(r.D*(p.residual[k]-p.residual[k+1]));
    out[r.i]=out[r.i]+f;out[r.j]=out[r.j]-f;}return out;
}
struct Group{std::string name,cloud,gamma,field;uint64_t tests=0;
  double max_actual=0,budget_at_max=0,max_ratio=0;};
Group active;uint64_t certificates=0;std::vector<Group> groups;
void Begin(const std::string& name,const std::string& cloud,const std::string& gamma,const std::string& field){
  active=Group{name,cloud,gamma,field};}
void Check(B delta,const std::string& what){const double a=std::abs(delta.v);
  const double ratio=delta.e>0?a/delta.e:(a==0?0:Inf);Need(std::isfinite(ratio),"Undefined certificate ratio: "+what);
  active.tests++;certificates++;if(a>active.max_actual){active.max_actual=a;active.budget_at_max=delta.e;}
  active.max_ratio=std::max(active.max_ratio,ratio);Need(a<=delta.e,"Arithmetic certificate failed: "+what);}
void CheckV(V v,const std::string& what){Check(v.x,what+".x");Check(v.z,what+".z");}
void CheckVectors(const std::vector<V>& a,const std::vector<V>& b,const std::string& what){
  Need(a.size()==b.size(),"Check extent");for(size_t i=0;i<a.size();i++)CheckV(a[i]-b[i],what);}
void End(){Need(active.tests>0,"Empty certificate group");groups.push_back(active);}
std::vector<V> Field(const Graph& g,unsigned kind){std::vector<V> v;for(unsigned i=0;i<N;i++){
  const V x=g.x[i];if(kind==0)v.push_back({B(.3),B(-.2)});
  else if(kind==1)v.push_back(Mul(M{B(.7),B(-.4),B(.2),B(-.1)},x)+V{B(.3),B(-.2)});
  else if(kind==2)v.push_back(Mul(M{B(0),B(-.8),B(.8),B(0)},x));
  else if(kind==3)v.push_back(B(-.6)*x);
  else if(kind==4)v.push_back(Mul(M{B(0),B(.7),B(0),B(0)},x));
  else if(kind==5)v.push_back({B(std::sin(double(i)*.37)),B(std::cos(double(i)*.21))});
  else v.push_back({B(std::cos(double(i)*.19+.4)),B(std::sin(double(i)*.43-.2))});}return v;}
void Balance(const Graph& g,const std::vector<V>& force){V net;B torque;for(unsigned i=0;i<N;i++){
  net=net+force[i];torque=torque+Cross(g.x[i],force[i]);}CheckV(net,"net force/rate");Check(torque,"net torque/rate");}
void TestGraph(const Graph& g,const std::string& cloud,std::ofstream& graphs){
  const Basis basis=BuildBasisP(g);graphs<<cloud<<','<<N<<','<<g.rows.size()<<','<<g.condition<<'\n';
  const std::array<std::string,3> names={{"one","zero","nonuniform"}};
  const std::array<std::string,6> fields={{"translation","full_affine","rotation","compression","shear","nonaffine"}};
  for(unsigned gm=0;gm<3;gm++){const auto gamma=Gamma(g,gm);
    for(unsigned kind=0;kind<6;kind++){
      Begin("stiffness_force_rate",cloud,names[gm],fields[kind]);const auto v=Field(g,kind);const auto p=ApplyP(g,v);
      const auto y=Weighted(g,gamma,p.residual),force=Negative(ApplyPT(g,y));
      CheckVectors(force,Negative(BasisPT(basis,y)),"matrix-free vs independent basis adjoint");
      Check(Inner(v,force)+Inner(p.residual,y),"negative quadratic work identity");
      const B quadratic=Inner(p.residual,y);Need(std::nextafter(quadratic.v+quadratic.e,Inf)>=0,"PSD quadratic violated");
      Balance(g,force);std::vector<V> rate;for(unsigned i=0;i<N;i++)rate.push_back(force[i]/g.mass[i]);
      B inertial;for(unsigned i=0;i<N;i++)inertial=inertial+g.mass[i]*Dot(v[i],rate[i]);
      Check(inertial-Inner(v,force),"current synthetic mass conversion");
      if(kind<5){for(const auto& rr:p.residual)CheckV(rr,"complete affine null");
        for(const auto& ff:force)CheckV(ff,"affine force-rate null");}
      if(gm==0)CheckVectors(force,OldRateForce(g,p),"gamma1 original Rate mathematical law");
      if(gm==1)for(const auto& ff:force)Need(ff.x.v==0&&ff.z.v==0,"gamma0 numerical response not zero");
      // Independent bilinear symmetry, without forming a stiffness matrix.
      const auto z=Field(g,6);const auto pz=ApplyP(g,z);const auto kz=ApplyPT(g,Weighted(g,gamma,pz.residual));
      Check(Inner(z,Negative(force))-Inner(v,kz),"symmetric K bilinear form");End();
    }
    Begin("arbitrary_history_balance",cloud,names[gm],"nonzero_h");
    std::vector<V> hist;for(size_t k=0;k<g.rows.size();k++)hist.push_back({B(std::sin(.13*k)+.2),B(std::cos(.17*k)-.1)});
    std::vector<B> one(g.rows.size(),B(1));const auto force=Negative(ApplyPT(g,Weighted(g,one,hist)));
    Balance(g,force);CheckVectors(force,Negative(BasisPT(basis,Weighted(g,one,hist))),"history basis adjoint");
    // Gamma is deliberately absent from the old memory force; changing gamma=0
    // only stops future driving and cannot erase existing nonzero h.
    End();
  }
}
std::vector<V> Cloud(bool perturb){std::vector<V> x;for(unsigned iz=0;iz<7;iz++)for(unsigned ix=0;ix<7;ix++){
  const unsigned i=iz*7+ix;const double dx=perturb?.002*std::sin(.73*i):0,dz=perturb?.002*std::cos(.51*i):0;
  x.push_back({B((int(ix)-3)*.04+dx),B((int(iz)-3)*.04+dz)});}return x;}
void Rotation(const Graph& base,const Graph& rotated,const M& R){
  Need(base.rows.size()==rotated.rows.size(),"Rotation changed graph size");
  for(size_t k=0;k<base.rows.size();k++)Need(base.rows[k].i==rotated.rows[k].i&&base.rows[k].j==rotated.rows[k].j,"Rotation changed edge identities");
  Begin("objective_algebra", "perturbed_to_rotated","nonuniform","superposed_rigid_velocity");
  const auto v=Field(base,5);const M omega{B(0),-B(2)/B(3),B(2)/B(3),B(0)};
  std::vector<V> transformed;for(unsigned i=0;i<N;i++)transformed.push_back(Mul(R,v[i])+Mul(omega,rotated.x[i])+V{B(.4),B(-.3)});
  const auto p=ApplyP(base,v),q=ApplyP(rotated,transformed);std::vector<V> rh;
  for(size_t k=0;k<base.rows.size();k++){
    CheckV(q.residual[k]-Mul(R,p.residual[k]),"superposed time-dependent rigid velocity null");
    const V h{B(std::sin(.13*k)+.2),B(std::cos(.17*k)-.1)};rh.push_back(Mul(R,h));
    Check(rotated.rows[k].D-base.rows[k].D,"radial D rotation invariance");}
  std::vector<V> h;for(size_t k=0;k<base.rows.size();k++)h.push_back({B(std::sin(.13*k)+.2),B(std::cos(.17*k)-.1)});
  std::vector<B> one(base.rows.size(),B(1));const auto f=Negative(ApplyPT(base,Weighted(base,one,h)));
  const auto fr=Negative(ApplyPT(rotated,Weighted(rotated,one,rh)));
  for(unsigned i=0;i<N;i++)CheckV(fr[i]-Mul(R,f[i]),"nonzero history force covariance");
  Balance(rotated,fr);
  // Candidate local skew-L transport transforms as Omega'=R Omega R^T+Omega_super.
  // This only certifies its algebra; no ODE/integrator is run or selected.
  for(unsigned i=0;i<N;i++){
    const B wb=(p.L[i].zx-p.L[i].xz)/B(2),wr=(q.L[i].zx-q.L[i].xz)/B(2);
    const M lhs{B(0),-wr,wr,B(0)},rhs=Mul(Mul(R,M{B(0),-wb,wb,B(0)}),Transpose(R))+omega;
    Check(lhs.xx-rhs.xx,"spin covariance xx");Check(lhs.xz-rhs.xz,"spin covariance xz");
    Check(lhs.zx-rhs.zx,"spin covariance zx");Check(lhs.zz-rhs.zz,"spin covariance zz");}
  End();
}
std::string Escape(const std::string& s){std::string o;for(char c:s){if(c=='"'||c=='\\')o+='\\';if(c=='\n'){o+="\\n";continue;}o+=c;}return o;}
} // namespace phg
int main(int argc,char** argv){using namespace phg;std::filesystem::path out;bool created=false;
  try{Need(argc==2,"Usage: C08H18PlasticHgAdjointR1.exe FRESHOUT");
    Need(std::numeric_limits<double>::is_iec559&&std::numeric_limits<double>::digits==53&&std::fegetround()==FE_TONEAREST,
      "IEEE binary64 round-to-nearest environment required");
    Need((_mm_getcsr()&((1u<<15)|(1u<<6)))==0,"Gradual underflow required: FTZ/DAZ must be off");out=std::filesystem::absolute(argv[1]);
    Need(!std::filesystem::exists(out),"Existing complete/partial output protected");
    Need(std::filesystem::create_directory(out),"Cannot create exclusive output");created=true;
    std::ofstream graphcsv(out/"graphs.csv");Need(bool(graphcsv),"Cannot write graph CSV");graphcsv<<std::setprecision(17)<<"cloud,nodes,directed_rows,max_LS_condition\n";
    const auto uniform=MakeGraph(Cloud(false)),perturbed=MakeGraph(Cloud(true));
    // Exact 3/5,4/5 rotation is enclosed, including floating coordinate/weight evaluation.
    const B c=B(3)/B(5),s=B(4)/B(5);const M rot{c,-s,s,c};std::vector<V> xr;
    for(const auto& x:perturbed.x)xr.push_back(Mul(rot,x));const auto rotated=MakeGraph(xr);
    TestGraph(uniform,"structured",graphcsv);TestGraph(perturbed,"perturbed",graphcsv);TestGraph(rotated,"rotated",graphcsv);
    Rotation(perturbed,rotated,rot);
    Begin("history_unloading_counterexample","scalar_row","gamma_half","h_minus_Pv");
    const B pv(-1),h(1),D(1),gamma(.5);const B power=-(pv*D*h),edot=h*D*gamma*pv;
    const B excess=power+edot,formula=h*D*(gamma-B(1))*pv;
    Check(excess-formula,"memory total-power identity");Need(std::nextafter(excess.v-excess.e,-Inf)>0,"Required unloading counterexample absent");End();
    std::ofstream csv(out/"certificates.csv");Need(bool(csv),"Cannot write certificate CSV");
    csv<<std::setprecision(17)<<"group,cloud,gamma,field,scalar_checks,max_actual_abs,budget_at_max_actual,max_error_over_budget\n";
    double maxratio=0;for(const auto& g:groups){csv<<g.name<<','<<g.cloud<<','<<g.gamma<<','<<g.field<<','<<g.tests<<','<<g.max_actual<<','<<g.budget_at_max<<','<<g.max_ratio<<'\n';maxratio=std::max(maxratio,g.max_ratio);}
    csv.flush();graphcsv.flush();Need(bool(csv)&&bool(graphcsv),"CSV write failure");
    std::ofstream done(out/"completion.json");Need(bool(done),"Cannot write completion");done<<std::setprecision(17)
      <<"{\n  \"stage\": \"c08_h18_plastic_hg_adjoint_r1\",\n  \"passed\": true,\n  \"clouds\": 3,\n  \"nodes_per_cloud\": 49,\n  \"gamma_modes\": 3,\n  \"velocity_fields_per_gamma\": 6,\n  \"certificate_groups\": "<<groups.size()<<",\n  \"scalar_certificates\": "<<certificates
      <<",\n  \"maximum_error_over_budget\": "<<maxratio<<",\n  \"value_add_sub_operations\": "<<count.add<<",\n  \"value_multiply_operations\": "<<count.mul<<",\n  \"value_divide_operations\": "<<count.div<<",\n  \"value_sqrt_operations\": "<<count.sqrt
      <<",\n  \"history_passive\": false,\n  \"unloading_counterexample_observed\": true,\n  \"counterexample_mechanical_power\": "<<power.v<<",\n  \"counterexample_memory_energy_rate\": "<<edot.v<<",\n  \"counterexample_total_power\": "<<excess.v
      <<",\n  \"actual_adjoint_contains_LS_backpropagation\": true,\n  \"basis_P_is_reference_only\": true,\n  \"gamma1_mathematical_not_bit_equivalence\": true,\n  \"mass_conversion_is_manufactured_not_native_ledger\": true,\n  \"physical_source_objects_linked\": 0,\n  \"physical_steps\": 0,\n  \"material_calls\": 0,\n  \"Darcy_calls\": 0,\n  \"solver_invocations\": 0,\n  \"native_invocations\": 0,\n  \"history_ODE_integrated\": false,\n  \"finite_rotation_integration_qualified\": false,\n  \"C08_compatibility_qualified\": false,\n  \"physical_acceptance\": false\n}\n";
    done.flush();Need(bool(done),"Completion write failure");std::cout<<"Pure adjoint algebra passed; history_passive=false; physical_acceptance=false\n";return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';if(created){std::ofstream d(out/"failure.json");d<<"{\"stage\":\"c08_h18_plastic_hg_adjoint_r1\",\"passed\":false,\"first_failure\":\""<<Escape(e.what())<<"\",\"partial_outputs_preserved\":true,\"physical_acceptance\":false}\n";}return 1;}
}
