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
struct Fixture{const char* name;V h,z;B d,t;};
std::vector<Fixture> Fixtures(){return {
  {"loading",{B(1),B(0)},{B(1),B(0)},B(1),B(3)},
  {"before_cross",{B(-1),B(0)},{B(1),B(0)},B(1),B(.5)},
  {"at_cross",{B(-1),B(0)},{B(1),B(0)},B(1),B(1)},
  {"after_cross",{B(-1),B(0)},{B(1),B(0)},B(1),B(3)},
  {"cold",{B(0),B(0)},{B(1),B(0)},B(1),B(2)},
  {"zero_z",{B(2),B(-3)},{B(0),B(0)},B(1),B(1)},
  {"zero_D",{B(1),B(2)},{B(-1),B(.5)},B(0),B(1)},
  {"vector_transverse",{B(-1),B(2)},{B(1),B(0)},B(1),B(3)},
  {"oblique",{B(1),B(-2)},{B(.5),B(1)},B(2),B(2)}
};}
void RunFixtures(std::ofstream& csv){
  csv<<std::setprecision(17)<<"fixture,gamma,branch,D,T,A0,Z,t1,t2,hnew_x,hnew_z,Ih_x,Ih_z,delta_E,W_mechanical,loading_loss,total_energy_work,total_roundoff_bound,balance_residual,balance_bound,semigroup_h_error,semigroup_h_bound,semigroup_I_error,semigroup_I_bound\n";
  const B c=B(3)/B(5),s=B(4)/B(5);const M R{c,-s,s,c};
  for(const auto& f:Fixtures())for(double gg:{0.,.5,1.}){
    const B g(gg);const auto a=ExactStep(f.h,f.z,f.d,g,f.t);
    const auto first=ExactStep(f.h,f.z,f.d,g,f.t/B(2));
    const auto second=ExactStep(first.h,f.z,f.d,g,f.t/B(2));
    const V dh=second.h-a.h,dI=first.I+second.I-a.I;CloseV(dh,"one/two step history semigroup");CloseV(dI,"one/two step history integral semigroup");
    Close(first.de+second.de-a.de,"semigroup energy telescopes");Close(first.work+second.work-a.work,"semigroup mechanical work");
    Close(first.loss+second.loss-a.loss,"semigroup loading dissipation");
    const bool exactZeroZ=f.z.x.v==0&&f.z.x.e==0&&f.z.z.v==0&&f.z.z.e==0;
    // R*exact zero is exactly zero; retain this identity instead of an interval
    // overestimate masquerading as a nonzero, uncertifiable velocity row.
    if(exactZeroZ)CloseV(Mul(R,f.z),"exact zero manufactured field rotation");
    const V rz=exactZeroZ?V{}:Mul(R,f.z);const auto rotated=ExactStep(Mul(R,f.h),rz,f.d,g,f.t);
    CloseV(rotated.h-Mul(R,a.h),"fixed scalar D history rotation");CloseV(rotated.I-Mul(R,a.I),"fixed scalar D integral rotation");
    Close(rotated.de-a.de,"rotation energy");Close(rotated.work-a.work,"rotation work");Close(rotated.loss-a.loss,"rotation dissipation");
    if(gg==1){CloseV(a.h-(f.h+f.t*f.z),"gamma1 fixed-input elastic ODE history");
      CloseV(a.I-(f.t*f.h+(B(.5)*f.t*f.t)*f.z),"gamma1 fixed-input elastic ODE integral");Close(a.total,"gamma1 conservative exchange");}
    if(std::string(f.name)=="vector_transverse")Close(a.h.z-f.h.z,"transverse memory retained");
    const B balance=a.total+a.loss;
    csv<<f.name<<','<<gg<<','<<a.branch<<','<<f.d.v<<','<<f.t.v<<','<<a.A.v<<','<<a.Z.v<<','<<a.t1.v<<','<<a.t2.v<<','<<a.h.x.v<<','<<a.h.z.v<<','<<a.I.x.v<<','<<a.I.z.v<<','<<a.de.v<<','<<a.work.v<<','<<a.loss.v<<','<<a.total.v<<','<<a.total.e<<','<<balance.v<<','<<balance.e<<','
       <<std::max(std::abs(dh.x.v),std::abs(dh.z.v))<<','<<std::max(dh.x.e,dh.z.e)<<','<<std::max(std::abs(dI.x.v),std::abs(dI.z.v))<<','<<std::max(dI.x.e,dI.z.e)<<'\n';
  }
}
void RunGraph(std::ofstream& csv){
  std::vector<V> x;for(unsigned iz=0;iz<7;iz++)for(unsigned ix=0;ix<7;ix++){const unsigned i=iz*7+ix;
    x.push_back({B((int(ix)-3)*.04+.002*std::sin(.73*i)),B((int(iz)-3)*.04+.002*std::cos(.51*i))});}
  const auto graph=MakeGraph(x);std::vector<V> v;
  for(unsigned i=0;i<N;i++)v.push_back({B(std::sin(.37*i)),B(std::cos(.21*i))});
  const auto forward=ApplyP(graph,v);const B t(.5);std::vector<V> average_weighted;
  B de,work,loss;uint64_t crossings=0,loadings=0,unloadings=0;
  for(size_t k=0;k<graph.rows.size();k++){
    const auto& row=graph.rows[k];const V z=forward.residual[k];
    const double ni=row.i%11==0?1:row.i%7==0?0:double(row.i%5)/4;
    const double nj=row.j%11==0?1:row.j%7==0?0:double(row.j%5)/4;
    const B g(.5*(ni+nj)); // Prescribed binary dyadic average; not a DP producer.
    const V transverse{-z.z,z.x};const V h=B((int(k%3)-1)*.25)*z+B(.125)*transverse;
    const auto a=ExactStep(h,z,row.D,g,t);de=de+a.de;work=work+a.work;loss=loss+a.loss;
    average_weighted.push_back(row.D*(a.I/t));
    if(a.branch=="crossing")crossings++;else if(a.branch=="loading")loadings++;else unloadings++;
  }
  auto force=ApplyPT(graph,average_weighted);for(auto& f:force)f=-f;
  V net;B torque,node_work;for(unsigned i=0;i<N;i++){net=net+force[i];torque=torque+Cross(graph.x[i],force[i]);node_work=node_work+t*Dot(v[i],force[i]);}
  CloseV(net,"graph average force net balance");Close(torque,"graph average force torque balance");
  Close(node_work-work,"node average-force work equals directed-row integral work");
  const B total=de+node_work,balance=total+loss;Close(balance,"whole graph fixed-input energy");
  Need(Hi(loss)>=0&&total.v<=total.e,"Whole graph passive contract violated");
  csv<<std::setprecision(17)<<"nodes,directed_rows,max_LS_condition,T,crossing_rows,loading_rows,other_rows,delta_E,W_rows,W_nodes,loading_loss,total_energy_work,total_roundoff_bound,balance_residual,balance_bound,net_Fx,net_Fx_bound,net_Fz,net_Fz_bound,torque,torque_bound,node_minus_row_work,node_minus_row_work_bound\n"
    <<N<<','<<graph.rows.size()<<','<<graph.condition<<','<<t.v<<','<<crossings<<','<<loadings<<','<<unloadings<<','<<de.v<<','<<work.v<<','<<node_work.v<<','<<loss.v<<','<<total.v<<','<<total.e<<','<<balance.v<<','<<balance.e<<','<<net.x.v<<','<<net.x.e<<','<<net.z.v<<','<<net.z.e<<','<<torque.v<<','<<torque.e<<','<<(node_work-work).v<<','<<(node_work-work).e<<'\n';
}
std::string Escape(const std::string& s){std::string out;for(char c:s){if(c=='"'||c=='\\')out+='\\';if(c=='\n'){out+="\\n";continue;}out+=c;}return out;}
} // namespace phg
int main(int argc,char** argv){using namespace phg;std::filesystem::path out;bool created=false;
  try{Need(argc==2,"Usage: C08H18HgUnloadContractR1.exe FRESHOUT");
    Need(std::numeric_limits<double>::is_iec559&&std::numeric_limits<double>::digits==53&&std::fegetround()==FE_TONEAREST,
      "IEEE binary64 round-to-nearest required");Need((_mm_getcsr()&((1u<<15)|(1u<<6)))==0,"FTZ/DAZ must be off");
    out=std::filesystem::absolute(argv[1]);Need(!std::filesystem::exists(out),"Existing complete/partial output protected");
    Need(std::filesystem::create_directory(out),"Cannot create exclusive output");created=true;
    std::ofstream fixtures(out/"contracts.csv"),graph(out/"graph.csv"),counter(out/"midpoint_comparison.csv");
    Need(bool(fixtures)&&bool(graph)&&bool(counter),"Cannot create fresh CSVs");RunFixtures(fixtures);RunGraph(graph);
    const V h{B(1),B(0)},z{B(-1),B(0)};const B d(1),g(0),t(3);
    const auto exact=ExactStep(h,z,d,g,t);const B A=Dot(h,d*z),Bhalf=B(.5)*t*Dot(z,d*z),a=-A/Bhalf;
    const V reflected=h+(t*a)*z,midavg=B(.5)*(h+reflected);const B midwork=-t*Dot(z,d*midavg);
    const B midde=B(.5)*d*(Dot(reflected,reflected)-Dot(h,h));
    Close(reflected.x+B(1),"midpoint reflected memory is -1");Close(exact.h.x,"exact unloading ends at zero");
    Close(exact.de+B(.5),"exact released memory energy");Close(exact.work-B(.5),"exact released mechanical work");Close(midde+midwork,"midpoint energy neutrality not selection criterion");
    counter<<std::setprecision(17)<<"contract,hnew_x,Ih_x,delta_E,W_mechanical,total_energy_work,bound,fixed_input_contract_under_test\n"
      <<"midpoint_reflection,"<<reflected.x.v<<','<<(t*midavg).x.v<<','<<midde.v<<','<<midwork.v<<','<<(midde+midwork).v<<','<<(midde+midwork).e<<",false\n"
      <<"exact_piecewise,"<<exact.h.x.v<<','<<exact.I.x.v<<','<<exact.de.v<<','<<exact.work.v<<','<<exact.total.v<<','<<exact.total.e<<",true\n";
    fixtures.flush();graph.flush();counter.flush();Need(bool(fixtures)&&bool(graph)&&bool(counter),"CSV write failed");
    std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\n  \"stage\": \"c08_h18_hg_unload_contract_r1\",\n  \"passed\": true,\n  \"fixtures\": 9,\n  \"gamma_values\": 3,\n  \"fixture_rows\": 27,\n  \"graph_clouds\": 1,\n  \"graph_nodes\": 49,\n  \"scalar_certificates\": "<<scalar_checks<<",\n  \"max_error_over_budget\": "<<max_ratio<<",\n  \"event_interval_overlaps\": "<<event_interval_overlaps<<",\n  \"value_add_sub_operations\": "<<count.add<<",\n  \"value_multiply_operations\": "<<count.mul<<",\n  \"value_divide_operations\": "<<count.div<<",\n  \"value_sqrt_operations\": "<<count.sqrt
      <<",\n  \"fixed_input_energy_contract\": true,\n  \"contract_scope\": \"fixed_P_D_z_g_and_prescribed_vbar\",\n  \"midpoint_reflection_selected\": false,\n  \"gamma1_mathematical_not_bit_recovery\": true,\n  \"actual_Symplectic_qualified\": false,\n  \"same_stage_Darcy_qualified\": false,\n  \"dynamic_D_graph_gamma_qualified\": false,\n  \"DP_producer_qualified\": false,\n  \"finite_rotation_integration_qualified\": false,\n  \"history_restart_qualified\": false,\n  \"physical_steps\": 0,\n  \"material_calls\": 0,\n  \"Darcy_calls\": 0,\n  \"solver_invocations\": 0,\n  \"native_invocations\": 0,\n  \"physical_source_objects_linked\": 0,\n  \"physical_acceptance\": false\n}\n";
    done.flush();Need(bool(done),"Completion write failure");std::cout<<"Fixed-input exact unload contract passed; actual_Symplectic_qualified=false\n";return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';if(created){std::ofstream d(out/"failure.json");d<<"{\"stage\":\"c08_h18_hg_unload_contract_r1\",\"passed\":false,\"first_failure\":\""<<Escape(e.what())<<"\",\"partial_outputs_preserved\":true,\"physical_acceptance\":false}\n";}return 1;}
}
