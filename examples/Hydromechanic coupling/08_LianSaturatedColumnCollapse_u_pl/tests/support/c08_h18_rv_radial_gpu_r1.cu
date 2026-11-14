// Private standalone CUDA candidate; original physical CUDA objects stay unchanged.
#include "c08_h18_rv_radial_gpu_r1.h"
#include <cfloat>
#include <cmath>
#include <cstddef>
#include <math_constants.h>
// No CTE_AVAILABLE: there is no new shared device constant or device-link ABI.
namespace c08h18radial {
#include "FunctionsBasic_iker.h"
#include "FunSphKernel_iker.h"
#include "JCellSearch_iker.h"
enum Error {Input=1u,Coincident=2u,Weight=4u,Rank=8u,Fit=16u,Neighbor=32u,Force=64u,Bound=128u,Certificate=256u,Manufactured=512u,Exchange=1024u};
constexpr unsigned Nodes=5000,Block=256;
struct Params {double solid0,rho0,rhow,vol0,dt;float h,bwen,G;unsigned mode;};
struct Node {double2 x,v;double V,rho,tau,fieldError;};
struct FitData {double4 L;double condition,degree,lsRatio,forward;unsigned count,reverse;};
struct Edge {unsigned lo,hi;Node a,b;double2 d,dv,n,force;double beta,s,q,amplitude,c,qBudget,normalRatio;};
struct NodeResult {
 float3 ace; // Only these first12 bytes may be committed, after every acceptance gate.
 double2 force,committedForce;
 double D,pairTorque,centralBudget,pairPowerScale,forceScale,torqueMapScale;
 double power,nodePowerScale,torque,nodeTorqueScale,Q,maxQ,degreeUpper,nodeForceBudget,maxQBudget;
 double normalRatio,exchangeError,commitError,commitRatio,commitB,commitPB,commitTB,commitEB;
 double committedPower,committedTorque,committedQ,maxAddedAccel;
 unsigned active,closingPositive;
};
struct Summary {Result r;double2 net,committedNet;double pairPowerScale,nodePowerScale,forceScale,torqueMapScale,nodeTorqueScale,Q,committedQ,commitB,commitPB,commitTB,commitEB;};
static __device__ double Gamma(unsigned long long n){const double t=double(n)*(.5*DBL_EPSILON);return t<1.?t/(1.-t):CUDART_INF;}
static __device__ double Len(double2 a){return sqrt(a.x*a.x+a.y*a.y);}
static __device__ double L1(double2 a){return fabs(a.x)+fabs(a.y);}
static __device__ double Inf(double2 a){return fmax(fabs(a.x),fabs(a.y));}
static __device__ double Dot(double2 a,double2 b){return a.x*b.x+a.y*b.y;}
static __device__ double2 Mul(double4 l,double2 d){return make_double2(l.x*d.x+l.y*d.y,l.z*d.x+l.w*d.y);}
static __device__ double MatInf(double4 l){return fmax(fabs(l.x)+fabs(l.y),fabs(l.z)+fabs(l.w));}
static __device__ double ProductScale(double4 l,double2 d){return fmax(fabs(l.x*d.x)+fabs(l.y*d.y),fabs(l.z*d.x)+fabs(l.w*d.y));}
static __device__ double Ratio(double x,double b){return b>0?x/b:(x==0?0:CUDART_INF);}
static __device__ double Limiter(double s,double q){if(!(s<0&&q<0))return 0.;return fmin(-s,-q);}
static __device__ bool Bits(double a,double b){return __double_as_longlong(a)==__double_as_longlong(b);}
static __device__ double4 Affine(unsigned mode){
 if(mode==2)return make_double4(.07,-.04,.03,.02);
 if(mode==3)return make_double4(-.1,0,0,-.1);
 if(mode==4)return make_double4(0,.08,.08,0);
 if(mode==5)return make_double4(0,.08,-.08,0);
 return make_double4(0,0,0,0);
}
static __device__ bool GetNode(unsigned p,unsigned np,unsigned npb,const unsigned* idp,const double2* xy,const double* z,
 const float4* v,const typecode* code,const double* J,const Params& c,Node& a){
 if(p<npb||p>=np||!CODE_IsNormal(code[p])||!CODE_IsFluid(code[p])||idp[p]<2060||idp[p]>=7060)return false;
 a.x=make_double2(xy[p].x,z[p]);a.fieldError=0;
 if(c.mode){const double4 A=Affine(c.mode);const double2 b=c.mode<=2?make_double2(.25,-.125):make_double2(0,0);
  a.v=make_double2(A.x*a.x.x+A.y*a.x.y+b.x,A.z*a.x.x+A.w*a.x.y+b.y);
  a.fieldError=Gamma(4)*fmax(fabs(A.x*a.x.x)+fabs(A.y*a.x.y)+fabs(b.x),fabs(A.z*a.x.x)+fabs(A.w*a.x.y)+fabs(b.y));
 }else a.v=make_double2(double(v[p].x),double(v[p].z));
 const double j=J[p];a.V=c.vol0*j;a.rho=c.rhow+(c.rho0-c.rhow)/j;a.tau=double(c.h)/sqrt(double(c.G)/a.rho);
 return isfinite(j)&&j>c.solid0&&isfinite(a.V)&&a.V>0&&isfinite(a.rho)&&a.rho>0&&isfinite(a.tau)&&a.tau>0
  &&isfinite(a.x.x)&&isfinite(a.x.y)&&xy[p].y==0&&v[p].y==0&&isfinite(a.v.x)&&isfinite(a.v.y)&&isfinite(a.fieldError);
}
static __device__ bool ReverseMember(unsigned i,unsigned j,const StDivDataGpu& d,const unsigned* cell){
 int i1,f1,i2,f2,i3,f3;cunsearch::Initsp(cell[j],unsigned(d.axis),d.domcellcode,d.scelldiv,d.nc,d.cellzero,i1,f1,i2,f2,i3,f3);
 for(int c3=i3;c3<f3;c3+=d.nc.w)for(int c2=i2;c2<f2;c2+=d.nc.x){unsigned b,e=0;cunsearch::ParticleRange(c2,c3,i1,f1,d.beginendcell+d.cellfluid,b,e);if(e&&i>=b&&i<e)return true;}return false;
}
// Local LS uses the real directed cell graph. Canonical beta multiplication is
// identical at both endpoints, while momentWeight intentionally uses donor Vj.
static __device__ bool Geometry(unsigned i,unsigned j,unsigned np,unsigned npb,const unsigned* idp,const double2* xy,const double* z,
 const float4* v,const typecode* code,const double* J,const Params& c,const Node& a,double2& d,double2& dv,double& w,double& beta,unsigned& error){
 Node b;if(!GetNode(j,np,npb,idp,xy,z,v,code,J,c,b)||idp[i]==idp[j]){error|=Input;return false;}
 d=make_double2(a.x.x-b.x.x,a.x.y-b.x.y);const double r2=Dot(d,d);if(!isfinite(r2)){error|=Input;return false;}if(r2==0){error|=Coincident;return false;}
 if(r2>=4.*double(c.h)*double(c.h))return false;
 const double weight=-double(cufsph::GetKernel_Fac<KERNEL_Wendland>(float(r2),c.h,c.bwen));if(weight==0)return false;if(!(weight>0)||!isfinite(weight)){error|=Weight;return false;}
 const double eta=double(c.G)*.5*(a.tau+b.tau);w=eta*b.V*weight;
 beta=idp[i]<idp[j]?eta*a.V*b.V*weight:eta*b.V*a.V*weight;dv=make_double2(a.v.x-b.v.x,a.v.y-b.v.y);
 if(!isfinite(w)||!isfinite(beta)||!(w>0)||!(beta>0)){error|=Weight;return false;}return true;
}
__global__ void FitKernel(unsigned np,unsigned npb,StDivDataGpu dvd,const unsigned* cell,const unsigned* idp,const double2* xy,
 const double* z,const float4* v,const typecode* code,const double* J,Params c,FitData* fit,unsigned* errors){
 const unsigned p=npb+blockIdx.x*blockDim.x+threadIdx.x;if(p>=np)return;const unsigned row=p-npb;FitData o={};unsigned error=0;Node a;
 if(!GetNode(p,np,npb,idp,xy,z,v,code,J,c,a)){fit[row]=o;errors[row]=Input;return;}
 double4 M=make_double4(0,0,0,0),N=M,absM=M,absN=M;double target=0;
 const double an=MatInf(Affine(c.mode));
 int i1,f1,i2,f2,i3,f3;cunsearch::Initsp(cell[p],unsigned(dvd.axis),dvd.domcellcode,dvd.scelldiv,dvd.nc,dvd.cellzero,i1,f1,i2,f2,i3,f3);
 for(int c3=i3;c3<f3;c3+=dvd.nc.w)for(int c2=i2;c2<f2;c2+=dvd.nc.x){unsigned b,e=0;cunsearch::ParticleRange(c2,c3,i1,f1,dvd.beginendcell+dvd.cellfluid,b,e);
  if(e)for(unsigned j=b;j<e;j++){if(j==p)continue;double2 d,dv;double w,beta;if(!Geometry(p,j,np,npb,idp,xy,z,v,code,J,c,a,d,dv,w,beta,error))continue;
   o.count++;if(ReverseMember(p,j,dvd,cell))o.reverse++;else error|=Neighbor;o.degree+=beta;
   M.x+=w*d.x*d.x;M.y+=w*d.x*d.y;M.w+=w*d.y*d.y;
   N.x+=w*dv.x*d.x;N.y+=w*dv.x*d.y;N.z+=w*dv.y*d.x;N.w+=w*dv.y*d.y;
   absM.x+=fabs(w*d.x*d.x);absM.y+=fabs(w*d.x*d.y);absM.w+=fabs(w*d.y*d.y);
   absN.x+=fabs(w*dv.x*d.x);absN.y+=fabs(w*dv.x*d.y);absN.z+=fabs(w*dv.y*d.x);absN.w+=fabs(w*dv.y*d.y);
   if(c.mode){Node q;if(!GetNode(j,np,npb,idp,xy,z,v,code,J,c,q)){error|=Input;continue;}
    const double formed=a.fieldError+q.fieldError+.5*DBL_EPSILON*(Inf(a.v)+Inf(q.v)+an*(L1(a.x)+L1(q.x)));
    const double2 ad=Mul(Affine(c.mode),d);const double check=formed+Gamma(4)*(Inf(dv)+Inf(ad));
    if(!isfinite(formed)||!isfinite(check)||Inf(make_double2(dv.x-ad.x,dv.y-ad.y))>check)error|=Manufactured;
    target+=w*formed*L1(d);
   }
  }}M.z=M.y;absM.z=absM.y;
 const double scale=fmax(fmax(fabs(M.x),fabs(M.y)),fabs(M.w));if(!(scale>0)||!isfinite(scale))error|=Rank;
 if(!error){const double aa=M.x/scale,b=M.y/scale,cc=M.w/scale,det=aa*cc-b*b;
  if(!(aa>0&&cc>0&&det>128.*DBL_EPSILON*(aa*cc+b*b)))error|=Rank;
  else{const double den=scale*det;o.L=make_double4((N.x*cc-N.y*b)/den,(-N.x*b+N.y*aa)/den,(N.z*cc-N.w*b)/den,(-N.z*b+N.w*aa)/den);
   const double large=.5*(aa+cc+hypot(aa-cc,2*b));o.condition=large/(det/large);
   const double vals[4]={o.L.x*M.x+o.L.y*M.z-N.x,o.L.x*M.y+o.L.y*M.w-N.y,o.L.z*M.x+o.L.w*M.z-N.z,o.L.z*M.y+o.L.w*M.w-N.w};
   const double scales[4]={fabs(o.L.x*M.x)+fabs(o.L.y*M.z)+fabs(N.x),fabs(o.L.x*M.y)+fabs(o.L.y*M.w)+fabs(N.y),fabs(o.L.z*M.x)+fabs(o.L.w*M.z)+fabs(N.z),fabs(o.L.z*M.y)+fabs(o.L.w*M.w)+fabs(N.w)};
   double rb=0;for(unsigned k=0;k<4;k++){const double budget=Gamma(20)*scales[k];if(!isfinite(budget)||!isfinite(vals[k])||fabs(vals[k])>budget)error|=Fit;o.lsRatio=fmax(o.lsRatio,Ratio(fabs(vals[k]),budget));rb=fmax(rb,budget);}
   const double inverse=fmax(fabs(cc)+fabs(b),fabs(aa)+fabs(b))/(scale*det),uncertainty=Gamma(12)*(1.+o.condition);
   if(!isfinite(MatInf(o.L))||!isfinite(o.condition)||!(o.condition>=1.)||!isfinite(inverse)||!(inverse>0)||!isfinite(uncertainty)||!(uncertainty<1.)||!isfinite(o.degree)||!(o.degree>0))error|=Fit;
   else if(c.mode){const double acc=Gamma(3ull*o.count),tg=Gamma(8ull*o.count);
    const double targetBudget=target/(1.-tg)+acc*(MatInf(absN)+an*MatInf(absM))+Gamma(4)*(MatInf(N)+an*MatInf(M));
    o.forward=inverse/(1.-uncertainty)*(2.*rb+targetBudget)*(1.+Gamma(8));const double4 A=Affine(c.mode),dl=make_double4(o.L.x-A.x,o.L.y-A.y,o.L.z-A.z,o.L.w-A.w);
    if(!isfinite(o.forward)||!isfinite(targetBudget)||!(tg<1.)||MatInf(dl)>o.forward)error|=Manufactured;
   }
  }}fit[row]=o;errors[row]=error;
}
__global__ void FitSummary(unsigned npb,const unsigned* idp,const FitData* fit,const unsigned* errors,Params c,Summary* out){
 if(blockIdx.x||threadIdx.x)return;Summary s={};auto&r=s.r;r.invalid_sorted=r.invalid_native_id=~0u;r.mode=c.mode;unsigned degree=0;
 for(unsigned i=0;i<Nodes;i++){const auto f=fit[i];if(errors[i]){r.error_bits|=errors[i];if(r.invalid_sorted==~0u){r.invalid_sorted=npb+i;r.invalid_native_id=idp[npb+i];}}
  r.directed_edges+=f.count;r.reverse_memberships+=f.reverse;degree=max(degree,f.count);r.value[max_condition]=fmax(r.value[max_condition],f.condition);r.value[LS_backward_max_ratio]=fmax(r.value[LS_backward_max_ratio],f.lsRatio);r.value[affine_LS_forward_budget]=fmax(r.value[affine_LS_forward_budget],f.forward);
 }
 if(!r.directed_edges||(r.directed_edges&1u)||r.reverse_memberships!=r.directed_edges)r.error_bits|=Neighbor;
 r.value[edges]=r.directed_edges*.5;r.value[max_degree]=degree;const double gd=Gamma(degree);
 for(unsigned i=0;i<Nodes;i++){
  // beta/mass is the actual positive weighted degree, not a neighbor count.
  // mass reconstruction is done in ForceKernel; this degree is retained there.
  if(!isfinite(fit[i].degree))r.error_bits|=Fit;
 }
 r.value[net_gamma]=Gamma((unsigned long long)degree+Nodes);
 r.value[power_gamma]=Gamma(16ull*r.directed_edges+7ull*Nodes+1);
 r.value[torque_gamma]=Gamma(16ull*r.directed_edges+6ull*Nodes+1);
 if(!isfinite(gd)||!(gd<1.)||!isfinite(r.value[net_gamma])||!isfinite(r.value[power_gamma])||!isfinite(r.value[torque_gamma]))r.error_bits|=Fit;
 if(!r.error_bits)r.validated_soil=Nodes;*out=s;
}
// Every invocation loads the original arrays in canonical native-ID order.
// The caller cannot supply a precomputed/reordered d, residual, beta, or velocity.
static __device__ __noinline__ bool Canonical(unsigned i,unsigned j,unsigned np,unsigned npb,const unsigned* idp,const double2* xy,const double* z,
 const float4* v,const typecode* code,const double* J,const Params& c,const FitData* fit,Edge& e,double2& target,unsigned& error){
 e.lo=idp[i]<idp[j]?i:j;e.hi=e.lo==i?j:i;
 if(idp[e.lo]>=idp[e.hi]||!GetNode(e.lo,np,npb,idp,xy,z,v,code,J,c,e.a)||!GetNode(e.hi,np,npb,idp,xy,z,v,code,J,c,e.b)){error|=Input;return false;}
 e.d=make_double2(e.a.x.x-e.b.x.x,e.a.x.y-e.b.x.y);const double r2=Dot(e.d,e.d);if(!isfinite(r2)){error|=Input;return false;}if(r2==0){error|=Coincident;return false;}if(r2>=4.*double(c.h)*double(c.h))return false;
 const double weight=-double(cufsph::GetKernel_Fac<KERNEL_Wendland>(float(r2),c.h,c.bwen));if(weight==0)return false;if(!(weight>0)||!isfinite(weight)){error|=Weight;return false;}
 const double eta=double(c.G)*.5*(e.a.tau+e.b.tau);e.beta=eta*e.a.V*e.b.V*weight;const double distance=sqrt(r2);e.n=make_double2(e.d.x/distance,e.d.y/distance);e.dv=make_double2(e.a.v.x-e.b.v.x,e.a.v.y-e.b.v.y);
 const double4 li=fit[e.lo-npb].L,lj=fit[e.hi-npb].L;const double2 pi=Mul(li,e.d),pj=Mul(lj,e.d),rb=make_double2(e.dv.x-(pi.x+pj.x)*.5,e.dv.y-(pi.y+pj.y)*.5);
 e.s=Dot(e.dv,e.n);e.q=Dot(rb,e.n);if(!isfinite(e.s)||!isfinite(e.q)){error|=Force;return false;}
 e.amplitude=Limiter(e.s,e.q);e.c=(Alpha*e.beta)*e.amplitude;e.force=make_double2(e.n.x*e.c,e.n.y*e.c);target=i==e.lo?e.force:make_double2(-e.force.x,-e.force.y);
 const double normal=fabs(Dot(e.n,e.n)-1.);e.normalRatio=Ratio(normal,Gamma(16));e.qBudget=0;
 if(!(e.beta>0)||!isfinite(e.beta)||!isfinite(e.c)||!isfinite(target.x)||!isfinite(target.y)||!isfinite(e.normalRatio)||normal>Gamma(16)||!(e.amplitude>=0)||e.amplitude>fmax(-e.s,0.))error|=Force;
 if(c.mode){const double an=MatInf(Affine(c.mode));const double formed=e.a.fieldError+e.b.fieldError+.5*DBL_EPSILON*(Inf(e.a.v)+Inf(e.b.v)+an*(L1(e.a.x)+L1(e.b.x)));
  e.qBudget=L1(e.n)*(formed+.5*(fit[e.lo-npb].forward+fit[e.hi-npb].forward)*L1(e.d)+Gamma(12)*(Inf(e.dv)+.5*(ProductScale(li,e.d)+ProductScale(lj,e.d))));
  if(!isfinite(e.qBudget)||fabs(e.q)>e.qBudget)error|=Manufactured;
 }return true;
}
__global__ void ForceKernel(unsigned np,unsigned npb,StDivDataGpu dvd,const unsigned* cell,const unsigned* idp,const double2* xy,
 const double* z,const float4* v,const typecode* code,const double* J,Params c,const FitData* fit,const unsigned* fiterrors,
 const float3* ace,const Summary* summary,NodeResult* nodes,unsigned* errors){
 const unsigned p=npb+blockIdx.x*blockDim.x+threadIdx.x;if(p>=np)return;const unsigned row=p-npb;NodeResult o={};unsigned error=fiterrors[row];Node a;
 if(!GetNode(p,np,npb,idp,xy,z,v,code,J,c,a))error|=Input;if(error){nodes[row]=o;errors[row]=error;return;}
 int i1,f1,i2,f2,i3,f3;cunsearch::Initsp(cell[p],unsigned(dvd.axis),dvd.domcellcode,dvd.scelldiv,dvd.nc,dvd.cellzero,i1,f1,i2,f2,i3,f3);
 unsigned count=0;
 for(int c3=i3;c3<f3;c3+=dvd.nc.w)for(int c2=i2;c2<f2;c2+=dvd.nc.x){unsigned b,end=0;cunsearch::ParticleRange(c2,c3,i1,f1,dvd.beginendcell+dvd.cellfluid,b,end);
  if(end)for(unsigned j=b;j<end;j++){if(j==p)continue;Edge e={};double2 f;if(!Canonical(p,j,np,npb,idp,xy,z,v,code,J,c,fit,e,f,error))continue;
   count++;if(fiterrors[j-npb]){error|=Neighbor;continue;}
   // Independently invoke the reverse directed helper, not an algebraic reuse.
   Edge er={};double2 reverse;if(!Canonical(j,p,np,npb,idp,xy,z,v,code,J,c,fit,er,reverse,error)){error|=Exchange;continue;}
   if(!Bits(f.x,-reverse.x)||!Bits(f.y,-reverse.y)||!Bits(e.beta,er.beta)||!Bits(e.s,er.s)||!Bits(e.q,er.q)||!Bits(e.c,er.c))error|=Exchange;
   o.exchangeError=fmax(o.exchangeError,Len(make_double2(f.x+reverse.x,f.y+reverse.y)));
   o.force.x+=f.x;o.force.y+=f.y;o.D+=e.c*(-e.s);if(e.amplitude>0)o.active++;if(e.s<0&&e.q>0)o.closingPositive++;
   o.pairTorque+=e.d.y*e.force.x-e.d.x*e.force.y;o.centralBudget+=Gamma(16)*e.c*(fabs(e.d.y*e.n.x)+fabs(e.d.x*e.n.y));
   o.forceScale+=L1(f);o.pairPowerScale+=e.c*((fabs(e.a.v.x)+fabs(e.b.v.x))*fabs(e.n.x)+(fabs(e.a.v.y)+fabs(e.b.v.y))*fabs(e.n.y));
   o.torqueMapScale+=(fabs(e.a.x.y)+fabs(e.b.x.y))*fabs(e.force.x)+(fabs(e.a.x.x)+fabs(e.b.x.x))*fabs(e.force.y);
   o.normalRatio=fmax(o.normalRatio,e.normalRatio);o.maxQ=fmax(o.maxQ,fabs(e.q));o.maxQBudget=fmax(o.maxQBudget,e.qBudget);
   if(c.mode)o.nodeForceBudget+=Alpha*e.beta*e.qBudget*Len(e.n)*(1.+Gamma(10));
  }}
 if(count!=fit[row].count)error|=Neighbor;
 const double mass=a.rho*a.V,degreeError=Gamma(fit[row].count);
 const double upper=Alpha*(fit[row].degree/mass)*(1.+Gamma(2))*(1.+Gamma(16))/(1.-degreeError);
 const double2 da=make_double2(o.force.x/mass,o.force.y/mass);o.maxAddedAccel=Len(da);o.Q=Dot(o.force,o.force)/mass;
 o.power=Dot(a.v,o.force);o.nodePowerScale=fabs(a.v.x*o.force.x)+fabs(a.v.y*o.force.y);o.torque=a.x.y*o.force.x-a.x.x*o.force.y;o.nodeTorqueScale=fabs(a.x.y*o.force.x)+fabs(a.x.x*o.force.y);
 o.degreeUpper=upper;
 if(!isfinite(upper)||!(upper>0)||!(degreeError<1.)||c.dt*upper>1.)error|=Bound;
 const float3 old=ace[p];if(old.y!=0||!isfinite(old.x)||!isfinite(old.z))error|=Input;
 o.ace=make_float3(float(double(old.x)+da.x),old.y,float(double(old.z)+da.y));o.committedForce=make_double2((double(o.ace.x)-old.x)*mass,(double(o.ace.z)-old.z)*mass);
 o.commitError=Len(make_double2(o.committedForce.x-o.force.x,o.committedForce.y-o.force.y));const double oldNorm=sqrt(double(old.x)*old.x+double(old.y)*old.y+double(old.z)*old.z);
 o.commitB=2.*FLT_EPSILON*mass*(oldNorm+Len(da));o.commitRatio=Ratio(o.commitError,o.commitB);if(o.commitError>o.commitB)error|=Certificate;
 o.committedPower=Dot(a.v,o.committedForce);o.committedTorque=a.x.y*o.committedForce.x-a.x.x*o.committedForce.y;o.committedQ=Dot(o.committedForce,o.committedForce)/mass;
 o.commitPB=Len(a.v)*o.commitB;o.commitTB=Len(a.x)*o.commitB;o.commitEB=c.dt*Len(a.v)*o.commitB+.5*c.dt*c.dt*(2.*Len(o.force)*o.commitB+o.commitB*o.commitB)/mass;
 if(c.mode){const double ng=Gamma((unsigned long long)fit[row].count+8);o.nodeForceBudget*= (1.+ng)/(1.-ng);if(!(ng<1.)||Len(o.force)>o.nodeForceBudget)error|=Manufactured;}
 const double checks[]={o.force.x,o.force.y,o.D,o.pairTorque,o.centralBudget,o.pairPowerScale,o.forceScale,o.torqueMapScale,o.power,o.nodePowerScale,o.torque,o.nodeTorqueScale,o.Q,o.maxQ,o.nodeForceBudget,o.maxQBudget,o.normalRatio,o.exchangeError,o.commitError,o.commitRatio,o.commitB,o.commitPB,o.commitTB,o.commitEB,o.committedPower,o.committedTorque,o.committedQ,o.maxAddedAccel};
 for(double q:checks)if(!isfinite(q))error|=Force;if(!isfinite(o.ace.x)||!isfinite(o.ace.y)||!isfinite(o.ace.z)||o.D<0)error|=Force;
 nodes[row]=o;errors[row]=error;
}
__global__ void ForceSummary(unsigned npb,const unsigned* idp,const NodeResult* nodes,const unsigned* errors,Params c,Summary* out){
 if(blockIdx.x||threadIdx.x)return;Summary s=*out;auto&r=s.r;auto*m=r.value;
 for(unsigned i=0;i<Nodes;i++){const auto&a=nodes[i];if(errors[i]){r.error_bits|=errors[i];if(r.invalid_sorted==~0u){r.invalid_sorted=npb+i;r.invalid_native_id=idp[npb+i];}}
  s.net.x+=a.force.x;s.net.y+=a.force.y;s.committedNet.x+=a.committedForce.x;s.committedNet.y+=a.committedForce.y;
  m[active_edges]+=a.active;m[closing_positive_residual_edges]+=a.closingPositive;m[dissipation_D]+=a.D;m[pair_torque]+=a.pairTorque;m[central_budget]+=a.centralBudget;m[node_power]+=a.power;m[node_torque]+=a.torque;
  s.pairPowerScale+=a.pairPowerScale;s.nodePowerScale+=a.nodePowerScale;s.forceScale+=a.forceScale;s.torqueMapScale+=a.torqueMapScale;s.nodeTorqueScale+=a.nodeTorqueScale;s.Q+=a.Q;
  m[normalization_max_ratio]=fmax(m[normalization_max_ratio],a.normalRatio);m[exchange_error]=fmax(m[exchange_error],a.exchangeError);m[float_commit_budget_ratio]=fmax(m[float_commit_budget_ratio],a.commitRatio);
  m[max_q]=fmax(m[max_q],a.maxQ);m[max_force]=fmax(m[max_force],Len(a.force));m[max_added_accel]=fmax(m[max_added_accel],a.maxAddedAccel);m[degree_upper]=fmax(m[degree_upper],a.degreeUpper);
  m[max_float_commit_error]=fmax(m[max_float_commit_error],a.commitError);m[affine_q_budget]=fmax(m[affine_q_budget],a.maxQBudget);m[affine_force_budget]=fmax(m[affine_force_budget],a.nodeForceBudget);
  m[committed_power]+=a.committedPower;m[committed_torque]+=a.committedTorque;s.committedQ+=a.committedQ;s.commitB+=a.commitB;s.commitPB+=a.commitPB;s.commitTB+=a.commitTB;s.commitEB+=a.commitEB;
 }
 // D, canonical pair torque and their unique-edge scales have appeared twice.
 m[active_edges]*=.5;m[closing_positive_residual_edges]*=.5;m[dissipation_D]*=.5;m[pair_torque]*=.5;m[central_budget]*=.5;s.pairPowerScale*=.5;s.torqueMapScale*=.5;
 // Node P/net/torque and sum_directed |F| are deliberately NOT halved.
 const double gn=m[net_gamma],gp=m[power_gamma],gt=m[torque_gamma];
 m[lambda_upper]=2.*m[degree_upper];m[dt_lambda_half]=c.dt*m[degree_upper];
 m[power_error]=fabs(m[node_power]+m[dissipation_D]);m[power_budget]=gp*(s.pairPowerScale+s.nodePowerScale)/(1.-gp);
 m[net_norm]=Len(s.net);m[net_budget]=gn*s.forceScale/(1.-Gamma(4ull*r.directed_edges+Nodes+1));
 m[central_budget]/=1.-Gamma(8ull*r.directed_edges+Nodes+1);
 m[torque_reduce_error]=fabs(m[node_torque]-m[pair_torque]);m[torque_reduce_budget]=gt*(s.torqueMapScale+s.nodeTorqueScale+fabs(m[pair_torque]))/(1.-gt);m[torque_budget]=m[central_budget]+m[torque_reduce_budget];
 m[frozen_Euler_deltaE]=c.dt*m[node_power]+.5*c.dt*c.dt*s.Q;
 m[frozen_Euler_budget]=c.dt*m[power_budget]+Gamma(7ull*Nodes+8)*(c.dt*fabs(m[node_power])+.5*c.dt*c.dt*s.Q);
 m[committed_power_budget]=m[power_budget]+s.commitPB;m[committed_net_norm]=Len(s.committedNet);m[committed_net_budget]=m[net_budget]+s.commitB;m[committed_torque_budget]=m[torque_budget]+s.commitTB;
 m[committed_Euler_deltaE]=c.dt*m[committed_power]+.5*c.dt*c.dt*s.committedQ;
 m[committed_Euler_budget]=m[frozen_Euler_budget]+s.commitEB+Gamma(7ull*Nodes+8)*(c.dt*fabs(m[committed_power])+.5*c.dt*c.dt*s.committedQ);
 // Exchange is exact sign reproduction, not a user-chosen force tolerance.
 m[exchange_budget]=0;
 for(unsigned k=0;k<MetricCount;k++)if(!isfinite(m[k]))r.error_bits|=Force;
 if(!isfinite(s.Q)||!isfinite(s.committedQ)||m[dissipation_D]<0||m[dt_lambda_half]>1.)r.error_bits|=Bound;
 if(!(m[power_error]<=m[power_budget]&&m[node_power]<=m[power_budget]&&m[net_norm]<=m[net_budget]&&fabs(m[pair_torque])<=m[central_budget]
  &&m[torque_reduce_error]<=m[torque_reduce_budget]&&fabs(m[node_torque])<=m[torque_budget]&&m[frozen_Euler_deltaE]<=m[frozen_Euler_budget]
  &&m[committed_power]<=m[committed_power_budget]&&m[committed_net_norm]<=m[committed_net_budget]&&fabs(m[committed_torque])<=m[committed_torque_budget]
  &&m[committed_Euler_deltaE]<=m[committed_Euler_budget]&&m[exchange_error]==0))r.error_bits|=Certificate;
 if(!r.error_bits)r.certificates_passed=true;
 if(c.mode&&!r.error_bits){r.manufactured_passed=m[max_q]<=m[affine_q_budget]&&m[max_force]<=m[affine_force_budget];if(!r.manufactured_passed)r.error_bits|=Manufactured;}
 *out=s;
}
__global__ void FixtureKernel(FixtureResult* out){if(blockIdx.x||threadIdx.x)return;FixtureResult r={};
 const double v[8][3]={{-1,-2,1},{-1,2,0},{1,-2,0},{1,2,0},{-1e-12,-1,1e-12},{-1,-1e-12,1e-12},{0,-1,0},{-1,0,0}};
 for(unsigned k=0;k<8;k++){r.s[k]=v[k][0];r.q[k]=v[k][1];r.expected[k]=v[k][2];r.a[k]=Limiter(r.s[k],r.q[k]);r.power[k]=r.a[k]*r.s[k];
  if(!isfinite(r.s[k])||!isfinite(r.q[k])||!Bits(r.a[k],r.expected[k])||r.a[k]<0||r.a[k]>fmax(-r.s[k],0.)||r.power[k]>0)r.errors|=1u<<k;}*out=r;
}
struct Scratch {FitData*fit=nullptr;unsigned*fiterrors=nullptr;NodeResult*nodes=nullptr;unsigned*errors=nullptr;Summary*summary=nullptr;
 ~Scratch(){cudaFree(summary);cudaFree(errors);cudaFree(nodes);cudaFree(fiterrors);cudaFree(fit);}};
cudaError_t Fixtures(FixtureResult& r){FixtureResult*p=nullptr;cudaError_t s=cudaMalloc((void**)&p,sizeof(FixtureResult));if(s!=cudaSuccess)return s;
 FixtureKernel<<<1,1>>>(p);s=cudaGetLastError();if(s==cudaSuccess)s=cudaMemcpy(&r,p,sizeof(r),cudaMemcpyDeviceToHost);const cudaError_t f=cudaFree(p);return s==cudaSuccess?f:s;
}
cudaError_t Add(unsigned np,unsigned npb,const StDivDataGpu& dvd,const unsigned* cell,const unsigned* idp,const double2* xy,const double* z,
 const float4* v,const typecode* code,const double* J,double solid0,double rho0,double rhow,double vol0,float h,float bwen,float G,double dt,unsigned mode,bool commit,float3* ace,Result& result){
 result=Result();result.invalid_sorted=result.invalid_native_id=~0u;result.mode=mode;
 if(np!=6805||npb!=1805||!cell||!idp||!xy||!z||!v||!code||!J||!ace||mode>5||(mode&&commit)
  ||!std::isfinite(solid0)||!(solid0>0&&solid0<1)||!std::isfinite(rho0)||!(rho0>0)||!std::isfinite(rhow)||!(rhow>0)||!std::isfinite(vol0)||!(vol0>0)
  ||!std::isfinite(dt)||dt!=.000005||h!=.072f||!std::isfinite(bwen)||!(bwen<0)||!std::isfinite(G)||!(G>0)
  ||!dvd.beginendcell||dvd.axis!=MGDIV_Z||(dvd.scelldiv!=1&&dvd.scelldiv!=2)||dvd.nc.x<=0||dvd.nc.y<=0||dvd.nc.z<=0||dvd.nc.w!=dvd.nc.x*dvd.nc.y||!dvd.cellfluid)return cudaErrorInvalidValue;
 const Params c={solid0,rho0,rhow,vol0,dt,h,bwen,G,mode};Scratch a;cudaError_t status;Summary host={};
 #define RVR_CALL(call) do{status=(call);if(status!=cudaSuccess)return status;}while(0)
 RVR_CALL(cudaMalloc((void**)&a.fit,Nodes*sizeof(FitData)));RVR_CALL(cudaMalloc((void**)&a.fiterrors,Nodes*sizeof(unsigned)));RVR_CALL(cudaMalloc((void**)&a.nodes,Nodes*sizeof(NodeResult)));RVR_CALL(cudaMalloc((void**)&a.errors,Nodes*sizeof(unsigned)));RVR_CALL(cudaMalloc((void**)&a.summary,sizeof(Summary)));
 FitKernel<<<(Nodes+Block-1)/Block,Block>>>(np,npb,dvd,cell,idp,xy,z,v,code,J,c,a.fit,a.fiterrors);RVR_CALL(cudaGetLastError());FitSummary<<<1,1>>>(npb,idp,a.fit,a.fiterrors,c,a.summary);RVR_CALL(cudaGetLastError());
 RVR_CALL(cudaMemcpy(&host,a.summary,sizeof(Summary),cudaMemcpyDeviceToHost));result=host.r;if(result.error_bits)return cudaSuccess;
 ForceKernel<<<(Nodes+Block-1)/Block,Block>>>(np,npb,dvd,cell,idp,xy,z,v,code,J,c,a.fit,a.fiterrors,ace,a.summary,a.nodes,a.errors);RVR_CALL(cudaGetLastError());ForceSummary<<<1,1>>>(npb,idp,a.nodes,a.errors,c,a.summary);RVR_CALL(cudaGetLastError());
 RVR_CALL(cudaMemcpy(&host,a.summary,sizeof(Summary),cudaMemcpyDeviceToHost));result=host.r;if(result.error_bits||!commit)return cudaSuccess;
 static_assert(offsetof(NodeResult,ace)==0,"Candidate Ace must be first, no pointer/stride alias");
 RVR_CALL(cudaMemcpy2D(ace+npb,sizeof(float3),a.nodes,sizeof(NodeResult),sizeof(float3),Nodes,cudaMemcpyDeviceToDevice));result.committed=true;
 #undef RVR_CALL
 return cudaSuccess;
}
}
