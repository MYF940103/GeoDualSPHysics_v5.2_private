// Private C08 GPU implementation candidate; original CUDA/material objects stay linked.
// This file is author-only until a separately reviewed build/run admission.
#include "c08_h18_hg_gpu_r1.hpp"
#include "FunSoilMaterial.h"
#include <cuda_runtime.h>
#include <math_constants.h>
#include <cfloat>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <utility>
#include <vector>

// No CTE_AVAILABLE, extern device constant, or cross-TU device call is used.
namespace c08hg {
#include "FunctionsBasic_iker.h"
#include "JCellSearch_iker.h"
namespace {
constexpr unsigned Block=128,Original=FirstId+Nodes,Fixed=1805,Slots=Nodes*Neighbors;
// Certified Part1000 scalar +=dt clock; deliberately not nominal 10 or n*dt.
constexpr double ActualSourceTime=9.9999999997060076;
static_assert(sizeof(tsymatrix3d)==6*sizeof(double)&&sizeof(tsymatrix3f)==6*sizeof(float),"Original six-component native tensor extent required");
enum Error:unsigned {Identity=1u,Input=2u,Overflow=4u,Duplicate=8u,Distance=16u,
  Weight=32u,Rank=64u,Reverse=128u,Memory=256u,Local=512u,MaterialReject=1024u,
  MaterialMismatch=2048u,ForceReject=4096u,Clock=8192u};
struct Failure {unsigned bits,id,slot,detail,claimed;double value[4];};
__device__ void Fail(Failure* e,unsigned bit,unsigned id,unsigned slot,unsigned detail=0,double a=0,double b=0,double c=0,double d=0){
  atomicOr(&e->bits,bit);
  if(atomicCAS(&e->claimed,0u,1u)==0u){e->id=id;e->slot=slot;e->detail=detail;e->value[0]=a;e->value[1]=b;e->value[2]=c;e->value[3]=d;}
}
// HG value arithmetic is explicitly RN even though this TU inherits the original
// material fast-math/FMA compilation contract. Material trial literals below
// deliberately do NOT pass through these wrappers.
struct R {double v;__device__ R(double x=0):v(x){}};
__device__ R operator+(R a,R b){return R(__dadd_rn(a.v,b.v));}
__device__ R operator-(R a,R b){return R(__dsub_rn(a.v,b.v));}
__device__ R operator-(R a){return R(-a.v);}
__device__ R operator*(R a,R b){return R(__dmul_rn(a.v,b.v));}
__device__ R operator/(R a,R b){return R(__ddiv_rn(a.v,b.v));}
__device__ R Root(R a){return R(__dsqrt_rn(a.v));}
struct V {R x,z;};
__device__ V Vec(double x=0,double z=0){return {R(x),R(z)};}
__device__ V operator+(V a,V b){return {a.x+b.x,a.z+b.z};}
__device__ V operator-(V a,V b){return {a.x-b.x,a.z-b.z};}
__device__ V operator-(V a){return {-a.x,-a.z};}
__device__ V operator*(R a,V b){return {a*b.x,a*b.z};}
__device__ V operator/(V a,R b){return {a.x/b,a.z/b};}
__device__ R Dot(V a,V b){return a.x*b.x+a.z*b.z;}
__device__ R Cross(V a,V b){return a.x*b.z-a.z*b.x;}
struct M {R xx,xz,zx,zz;};
__device__ M ZeroM(){return {R(0),R(0),R(0),R(0)};}
__device__ M operator+(M a,M b){return {a.xx+b.xx,a.xz+b.xz,a.zx+b.zx,a.zz+b.zz};}
__device__ M operator*(R a,M b){return {a*b.xx,a*b.xz,a*b.zx,a*b.zz};}
__device__ M Outer(V a,V b){return {a.x*b.x,a.x*b.z,a.z*b.x,a.z*b.z};}
__device__ V Mul(M a,V b){return {a.xx*b.x+a.xz*b.z,a.zx*b.x+a.zz*b.z};}
struct Moment {R xx,xz,zz,det;};
__device__ M RightInverse(M n,const Moment& m){return {
  (n.xx*m.zz-n.xz*m.xz)/m.det,(n.xz*m.xx-n.xx*m.xz)/m.det,
  (n.zx*m.zz-n.zz*m.xz)/m.det,(n.zz*m.xx-n.zx*m.xz)/m.det};}
__device__ bool Fin(double x){return isfinite(x);}
__device__ bool Fin(V a){return Fin(a.x.v)&&Fin(a.z.v);}
__device__ bool Fin(M a){return Fin(a.xx.v)&&Fin(a.xz.v)&&Fin(a.zx.v)&&Fin(a.zz.v);}
__device__ bool Bits(double a,double b){return __double_as_longlong(a)==__double_as_longlong(b);}
__device__ bool Bits(float a,float b){return __float_as_uint(a)==__float_as_uint(b);}
struct Node {
  unsigned slot,status,degree,known_constant,checked;
  V x,v,force;
  R volume,mass,gamma,omega;
  Moment moment;M L,T;
  double condition,lambda,qtrial,qreturn,root_ratio;
  tsymatrix3d expected;
  float old_kappa,new_kappa;
  float3 old_ace,new_ace;
  double force_abs,torque_scale,node_work,work_scale,commit_error,commit_budget,delta_ace;
};
#ifdef C08_HG_DEBUG_SNAPSHOT
struct DebugNode {unsigned id;double x,z,vx,vz,volume,mass,gamma,fx,fz;};
__global__ void DebugSnapshotKernel(const Node* nodes,DebugNode* snapshot){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=Nodes)return;const Node& n=nodes[i];
  snapshot[i]={FirstId+i,n.x.x.v,n.x.z.v,n.v.x.v,n.v.z.v,n.volume.v,n.mass.v,n.gamma.v,n.force.x.v,n.force.z.v};
}
#endif
struct Row {
  unsigned j,reverse,kept,known_constant,branch;
  V d,old_e,next_e,middle,q;
  R r,a,D,S;
  double Eold,Enew,work,loss,rotation,ledger,abs_work,angle;
};
struct Graph {unsigned* count;unsigned* ids;V* next_e;Row* row;};
struct MemoryView {unsigned* count;unsigned* ids;V* e;};
__device__ int Find(const unsigned* ids,unsigned count,unsigned value){
  unsigned lo=0,hi=count;while(lo<hi){const unsigned m=(lo+hi)/2;if(ids[m]<value)lo=m+1;else hi=m;}
  return lo<count&&ids[lo]==value?int(lo):-1;
}
__global__ void MapKernel(unsigned np,unsigned npb,const unsigned* id,const typecode* code,unsigned* map,Failure* fail){
  const unsigned p=blockIdx.x*blockDim.x+threadIdx.x;if(p>=np)return;
  const unsigned n=id[p];const bool soil=p>=npb&&CODE_IsNormal(code[p])&&CODE_IsFluid(code[p])&&n>=FirstId&&n<Original;
  const bool fixed=p<npb&&!CODE_IsFluid(code[p])&&n<Fixed;
  if(!soil&&!fixed){Fail(fail,Identity,n,p,1);return;}
  if(atomicCAS(map+n,~0u,p)!=~0u)Fail(fail,Duplicate,n,p,2);
}
__global__ void NodeKernel(Config c,Material material,Stage s,const unsigned* map,Node* node,Failure* fail){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=Nodes||atomicAdd(&fail->bits,0u))return;
  const unsigned id=FirstId+i,p=map[id];if(p==~0u||p>=s.np||s.id[p]!=id){Fail(fail,Identity,id,p,3);return;}
  Node n={};n.slot=p;n.x=Vec(s.xy[p].x,s.z[p]);n.v=Vec(double(s.velocity[p].x),double(s.velocity[p].z));
  const double j=s.J[p];
  n.volume=R(c.vol0)*R(j);n.mass=R(c.vol0)*(R(c.rho0)-R(c.rhow)+R(c.rhow)*R(j));
  if(!Fin(n.x)||!Fin(n.v)||s.xy[p].y!=0.||s.velocity[p].y!=0.f
    ||!Fin(j)||!(j>c.solid0)||!Fin(n.volume.v)||!(n.volume.v>0)||!Fin(n.mass.v)||!(n.mass.v>0)){
    Fail(fail,Input,id,p,4);return;
  }
  // Literal order and types match the original Simpleker predictor/corrector.
  // The compiler's original material FMA policy is retained here.
  const double2* sigma=reinterpret_cast<const double2*>(s.sigma_base);
  const float2* rsigma=reinterpret_cast<const float2*>(s.sigma_rate);
  const double2 sigmapre_xx_xy=sigma[p*3],sigmapre_xz_yy=sigma[p*3+1],sigmapre_yz_zz=sigma[p*3+2];
  const float2 rsigma_xx_xy=rsigma[p*3],rsigma_xz_yy=rsigma[p*3+1],rsigma_yz_zz=rsigma[p*3+2];
  const double width=s.corrector?s.dt:s.dt*.5;
  tsymatrix3d trial={};
  trial.xx=double(sigmapre_xx_xy.x)+double(rsigma_xx_xy.x)*width;
  trial.yy=double(sigmapre_xz_yy.y)+double(rsigma_xz_yy.y)*width;
  trial.zz=double(sigmapre_yz_zz.y)+double(rsigma_yz_zz.y)*width;
  trial.xy=double(sigmapre_xx_xy.y)+double(rsigma_xx_xy.y)*width;
  trial.yz=double(sigmapre_yz_zz.x)+double(rsigma_yz_zz.x)*width;
  trial.xz=double(sigmapre_xz_yy.x)+double(rsigma_xz_yy.x)*width;
  n.old_kappa=s.kappa[p];
  const fsoil::State in={{trial.xx,trial.yy,trial.zz,trial.xy,trial.yz,trial.xz},n.old_kappa};
  const auto m=fsoil::EvaluateMaterial(in,material.soil,material.fit,material.soft,material.trigger);
  n.status=unsigned(m.status);n.qtrial=m.trial_q;n.qreturn=m.returned_q;
  if(!Fin(n.old_kappa)||n.old_kappa<0||!fsoil::CommitAllowed(m.status)
    ||(material.require_elastic&&m.status!=fsoil::Status::Elastic)||!Fin(m.trial_q)||!Fin(m.returned_q)){
    Fail(fail,MaterialReject,id,p,n.status,double(n.old_kappa),double(m.state.kappa),m.trial_q,m.returned_q);return;
  }
  double gamma=0;
  switch(m.status){
    case fsoil::Status::Elastic:gamma=1;break;
    case fsoil::Status::Smooth:if(!(m.trial_q>0)){Fail(fail,MaterialReject,id,p,10);return;}gamma=m.returned_q/m.trial_q;break;
    case fsoil::Status::Apex:case fsoil::Status::TensionRepair:gamma=0;break;
    default:Fail(fail,MaterialReject,id,p,n.status);return;
  }
  if(!Fin(gamma)||gamma<0||gamma>1){Fail(fail,MaterialReject,id,p,11,gamma,m.trial_q,m.returned_q,double(n.status));return;}
  n.gamma=R(gamma);n.new_kappa=m.state.kappa;
  n.expected={m.state.stress.xx,m.state.stress.xy,m.state.stress.xz,m.state.stress.yy,m.state.stress.yz,m.state.stress.zz};
  const double ex[6]={n.expected.xx,n.expected.xy,n.expected.xz,n.expected.yy,n.expected.yz,n.expected.zz};for(unsigned k=0;k<6;k++)if(!Fin(ex[k])){Fail(fail,MaterialReject,id,p,20+k);return;}
  if(!Fin(n.new_kappa)||n.new_kappa<n.old_kappa){Fail(fail,MaterialReject,id,p,12);return;}
  const double rr=fabs(m.root_residual),rb=m.root_budget;
  if(!Fin(rr)||!Fin(rb)||rb<0||(rb==0&&rr!=0)){Fail(fail,MaterialReject,id,p,13);return;}
  n.root_ratio=rb>0?rr/rb:0;
  if(!Fin(n.root_ratio)){Fail(fail,MaterialReject,id,p,14);return;}
  n.old_ace=s.ace[p];if(!Fin(n.old_ace.x)||!Fin(n.old_ace.y)||!Fin(n.old_ace.z)||n.old_ace.y!=0.f){
    Fail(fail,Input,id,p,5);return;
  }
  node[i]=n;
}
__global__ void NeighborKernel(Config c,Stage s,const unsigned* map,const Node* nodes,Graph g,Failure* fail){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=Nodes||atomicAdd(&fail->bits,0u))return;
  const Node a=nodes[i];unsigned ids[Neighbors],count=0;
  int i1,f1,i2,f2,i3,f3;
  cunsearch::Initsp(s.cell[a.slot],unsigned(s.cells.axis),s.cells.domcellcode,s.cells.scelldiv,s.cells.nc,s.cells.cellzero,i1,f1,i2,f2,i3,f3);
  const R cut=R(2)*R(double(c.h));const R cut2=cut*cut;
  for(int c3=i3;c3<f3;c3+=s.cells.nc.w)for(int c2=i2;c2<f2;c2+=s.cells.nc.x){
    unsigned begin=0,end=0;cunsearch::ParticleRange(c2,c3,i1,f1,s.cells.beginendcell+s.cells.cellfluid,begin,end);
    if(end>s.np||begin>end){Fail(fail,Identity,FirstId+i,a.slot,6);return;}
    for(unsigned p=begin;p<end;p++){
      if(p==a.slot)continue;
      if(p<s.npb||!CODE_IsNormal(s.code[p])||!CODE_IsFluid(s.code[p])||s.id[p]<FirstId||s.id[p]>=Original){
        Fail(fail,Identity,s.id[p],p,7);return;
      }
      const unsigned j=s.id[p]-FirstId;if(map[s.id[p]]!=p){Fail(fail,Identity,s.id[p],p,8);return;}
      const V d=a.x-nodes[j].x;const R rr=Dot(d,d);
      if(!Fin(rr.v)||rr.v<=0){Fail(fail,Distance,FirstId+i,a.slot,s.id[p],rr.v,cut2.v,d.x.v,d.z.v);return;}
      if(rr.v>=cut2.v)continue;
      if(count==Neighbors){Fail(fail,Overflow,FirstId+i,a.slot,count+1,double(count+1),double(Neighbors));return;}
      ids[count++]=j;
    }
  }
  for(unsigned k=1;k<count;k++){const unsigned v=ids[k];unsigned q=k;while(q&&ids[q-1]>v){ids[q]=ids[q-1];q--;}ids[q]=v;}
  if(count<2){Fail(fail,Rank,FirstId+i,a.slot,count);return;}
  for(unsigned k=0;k<count;k++){if(k&&ids[k-1]==ids[k]){Fail(fail,Duplicate,FirstId+i,a.slot,FirstId+ids[k]);return;}g.ids[i*Neighbors+k]=ids[k];}
  g.count[i]=count;
}
__global__ void FitKernel(Config c,Node* nodes,Graph g,Failure* fail){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=Nodes||atomicAdd(&fail->bits,0u))return;
  Node n=nodes[i];Moment m={};M numerator=ZeroM();R degree(0);bool same=true;
  for(unsigned k=0;k<g.count[i];k++){
    const unsigned at=i*Neighbors+k,j=g.ids[at];const Node& b=nodes[j];Row r={};r.j=j;r.d=n.x-b.x;r.r=Root(Dot(r.d,r.d));
    const R h(double(c.h)),s=R(1)-r.r/(R(2)*h);
    const R w=-(R(double(c.bwen))/h)*s*s*s;
    // Canonical native-ID order makes beta and D identical for both directions.
    const R vlo=i<j?n.volume:b.volume,vhi=i<j?b.volume:n.volume;
    const R beta=R(Xi)*R(double(c.G))*vlo*vhi*w;
    r.a=b.volume*w;r.D=beta/R(2);r.S=Root(r.D);
    if(!(s.v>0)||!(w.v>0)||!(r.a.v>0)||!(r.D.v>0)||!Fin(r.r.v)||!Fin(r.a.v)||!Fin(r.D.v)||!Fin(r.S.v)){
      Fail(fail,Weight,FirstId+i,n.slot,FirstId+j,s.v,w.v,r.a.v,r.D.v);return;
    }
    m.xx=m.xx+r.a*r.d.x*r.d.x;m.xz=m.xz+r.a*r.d.x*r.d.z;m.zz=m.zz+r.a*r.d.z*r.d.z;
    numerator=numerator+r.a*Outer(n.v-b.v,r.d);degree=degree+beta;
    if(!Bits(n.v.x.v,b.v.x.v)||!Bits(n.v.z.v,b.v.z.v))same=false;
    g.row[at]=r;
  }
  m.det=m.xx*m.zz-m.xz*m.xz;
  const R tr=m.xx+m.zz,diff=m.xx-m.zz,twice=R(2)*m.xz;
  const R high=R(.5)*(tr+Root(diff*diff+twice*twice));const R low=m.det/high;
  const R condition=high/low;
  if(!Fin(m.det.v)||!(m.det.v>0)||!Fin(low.v)||!(low.v>0)||!Fin(condition.v)||!(condition.v<1e8)){
    Fail(fail,Rank,FirstId+i,n.slot,0,m.det.v,low.v,condition.v,high.v);return;
  }
  n.moment=m;n.L=RightInverse(numerator,m);n.omega=R(.5)*(n.L.zx-n.L.xz);
  n.condition=condition.v;n.lambda=(R(2)*degree/n.mass).v;n.degree=g.count[i];n.known_constant=unsigned(same);
  if(!Fin(n.L)||!Fin(n.omega.v)||!Fin(n.lambda)||!(n.lambda>0)||!((R(StepDt)*Root(R(n.lambda))).v<=.2)){
    Fail(fail,Rank,FirstId+i,n.slot,1,n.lambda,n.condition,n.omega.v,n.mass.v);return;
  }
  // Only fit fields are written: donors simultaneously read immutable x/v/V.
  nodes[i].moment=n.moment;nodes[i].L=n.L;nodes[i].omega=n.omega;
  nodes[i].condition=n.condition;nodes[i].lambda=n.lambda;nodes[i].degree=n.degree;nodes[i].known_constant=n.known_constant;
}
__device__ V Rotate(V a,R angle){
  const R q=angle*angle;
  const R co=R(1)+q*(R(-.5)+q*(R(1)/R(24)+q*(-R(1)/R(720)+q*(R(1)/R(40320)))));
  const R si=angle*(R(1)+q*(-R(1)/R(6)+q*(R(1)/R(120)+q*(-R(1)/R(5040)+q*(R(1)/R(362880))))));
  return {co*a.x-si*a.z,si*a.x+co*a.z};
}
struct LocalStep {V h,I;R work,loss;};
__device__ bool ExactStep(V h0,V u,R gamma,R width,bool known,LocalStep& o){
  const R A=Dot(h0,u),Z=Dot(u,u);R t1(0);
  if(known){if(u.x.v!=0||u.z.v!=0)return false;}
  else{if(!Fin(Z.v)||!(Z.v>0))return false;const R crossing=-A/Z;
    if(!Fin(crossing.v))return false;t1=R(fmax(0.,fmin(width.v,crossing.v)));}
  const R t2=width-t1,drive=t1+gamma*t2;
  o.h=h0+drive*u;
  o.I=width*h0+(R(.5)*t1*t1+t1*t2+R(.5)*gamma*t2*t2)*u;
  o.work=-Dot(u,o.I);
  o.loss=(R(1)-gamma)*(t2*(A+Z*t1)+R(.5)*gamma*Z*t2*t2);
  return Fin(o.h)&&Fin(o.I)&&Fin(o.work.v)&&Fin(o.loss.v);
}
__global__ void RowKernel(Stage s,Node* nodes,Graph g,MemoryView memory,Failure* fail){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=Nodes||atomicAdd(&fail->bits,0u))return;
  const Node n=nodes[i];const R width(s.corrector?s.dt:s.dt*.5),angle=n.omega*R(width.v*.5);
  if(!Fin(angle.v)||!(fabs(angle.v)<.005)){Fail(fail,Local,FirstId+i,n.slot,1,angle.v,n.omega.v,width.v,.005);return;}
  for(unsigned k=0;k<g.count[i];k++){
    const unsigned at=i*Neighbors+k,j=g.ids[at];Row r=g.row[at];
    const int reverse=Find(g.ids+j*Neighbors,g.count[j],i);
    if(reverse<0){Fail(fail,Reverse,FirstId+i,n.slot,FirstId+j);return;}
    r.reverse=unsigned(reverse);
    const int old=Find(memory.ids+i*Neighbors,memory.count[i],j);
    r.kept=unsigned(old>=0);r.old_e=old>=0?memory.e[i*Neighbors+unsigned(old)]:Vec();
    if(!Fin(r.old_e)){Fail(fail,Memory,FirstId+i,n.slot,FirstId+j);return;}
    const V er=Rotate(r.old_e,angle);
    const V residual=n.v-nodes[j].v-Mul(n.L,r.d);
    V u=r.S*residual;if(n.known_constant)u=Vec();
    const R gamma=R(.5)*n.gamma+R(.5)*nodes[j].gamma;
    LocalStep local={};if(!Fin(u)||!ExactStep(er,u,gamma,width,n.known_constant!=0,local)){
      Fail(fail,Local,FirstId+i,n.slot,FirstId+j,u.x.v,u.z.v,gamma.v,width.v);return;
    }
    r.next_e=Rotate(local.h,angle);r.middle=r.S*(local.I/width);
    const R e0=R(.5)*Dot(r.old_e,r.old_e),e1=R(.5)*Dot(r.next_e,r.next_e);
    const R rotation=(R(.5)*Dot(er,er)-e0)+(e1-R(.5)*Dot(local.h,local.h));
    r.Eold=e0.v;r.Enew=e1.v;r.work=local.work.v;r.loss=local.loss.v;r.rotation=rotation.v;
    r.ledger=(e1-e0+local.work+local.loss).v;r.abs_work=fabs(local.work.v);r.angle=fabs(angle.v);
    r.known_constant=n.known_constant;
    if(!Fin(r.next_e)||!Fin(r.middle)||!Fin(r.Eold)||!Fin(r.Enew)||!Fin(r.ledger)||!Fin(r.rotation)){
      Fail(fail,Local,FirstId+i,n.slot,FirstId+j);return;
    }
    g.next_e[at]=r.next_e;g.row[at]=r;
  }
}
__global__ void AdjointFitKernel(Node* nodes,Graph g,Failure* fail){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=Nodes||atomicAdd(&fail->bits,0u))return;
  M z=ZeroM();for(unsigned k=0;k<g.count[i];k++){const Row r=g.row[i*Neighbors+k];z=z+Outer(r.middle,r.d);}
  Node n=nodes[i];n.T=RightInverse(z,n.moment);if(!Fin(n.T)){Fail(fail,ForceReject,FirstId+i,n.slot,1);return;}nodes[i]=n;
}
__global__ void AdjointRowKernel(const Node* nodes,Graph g,Failure* fail){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=Nodes||atomicAdd(&fail->bits,0u))return;
  for(unsigned k=0;k<g.count[i];k++){const unsigned at=i*Neighbors+k;Row r=g.row[at];r.q=r.middle-r.a*Mul(nodes[i].T,r.d);
    if(!Fin(r.q)){Fail(fail,ForceReject,FirstId+i,nodes[i].slot,2);return;}g.row[at]=r;}
}
__device__ double Gamma(unsigned long long n){const double u=DBL_EPSILON*.5,nu=double(n)*u;return nu<1?nu/(1-nu):CUDART_INF;}
__global__ void ForceKernel(Stage s,Node* nodes,Graph g,Failure* fail){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=Nodes||atomicAdd(&fail->bits,0u))return;
  Node n=nodes[i];V f=Vec();R pairScale(0);
  for(unsigned k=0;k<g.count[i];k++){const Row r=g.row[i*Neighbors+k],rev=g.row[r.j*Neighbors+r.reverse];
    f=f-r.q+rev.q;pairScale=pairScale+R(fabs(r.q.x.v))+R(fabs(r.q.z.v))+R(fabs(rev.q.x.v))+R(fabs(rev.q.z.v));}
  n.force=f;
  const R ax=R(double(n.old_ace.x))+f.x/n.mass,az=R(double(n.old_ace.z))+f.z/n.mass;
  n.new_ace=make_float3(__double2float_rn(ax.v),n.old_ace.y,__double2float_rn(az.v));
  const R cx=n.mass*(R(double(n.new_ace.x))-R(double(n.old_ace.x))),cz=n.mass*(R(double(n.new_ace.z))-R(double(n.old_ace.z)));
  const double bx=__dmul_rn(n.mass.v,__dadd_rn(__dmul_rn(1./16777216.,fabs(ax.v)),double(FLT_MIN)));
  const double bz=__dmul_rn(n.mass.v,__dadd_rn(__dmul_rn(1./16777216.,fabs(az.v)),double(FLT_MIN)));
  n.commit_error=fmax(fabs((cx-f.x).v),fabs((cz-f.z).v));
  n.commit_budget=fmax(bx,bz)+Gamma(16)*(fabs(cx.v)+fabs(cz.v)+fabs(f.x.v)+fabs(f.z.v)
    +n.mass.v*(fabs(double(n.new_ace.x))+fabs(double(n.new_ace.z))+fabs(double(n.old_ace.x))+fabs(double(n.old_ace.z))));
  n.delta_ace=fmax(fabs(double(n.new_ace.x)-double(n.old_ace.x)),fabs(double(n.new_ace.z)-double(n.old_ace.z)));
  const R width(s.corrector?s.dt:s.dt*.5);n.node_work=(width*Dot(n.v,f)).v;
  n.work_scale=(width*R(fabs((n.v.x*f.x).v)+fabs((n.v.z*f.z).v))).v;
  n.force_abs=pairScale.v;n.torque_scale=fabs((n.x.x*f.z).v)+fabs((n.x.z*f.x).v);
  if(!Fin(f)||!Fin(n.new_ace.x)||!Fin(n.new_ace.z)||!Fin(n.node_work)||!Fin(n.commit_budget)
    ||n.commit_error>n.commit_budget){Fail(fail,ForceReject,FirstId+i,n.slot,3,n.commit_error,n.commit_budget,f.x.v,f.z.v);return;}
  nodes[i]=n;
}
// One bounded receiver-local reduction; no thread scans the complete edge graph.
struct PartialSummary {
  Summary value;
  double work_scale,force_scale,torque_scale,lever_scale,energy_scale;
  unsigned long long terms;
};
__global__ void LocalSummaryKernel(const Node* nodes,Graph g,MemoryView memory,const Failure* fail,PartialSummary* output){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=Nodes||fail->bits)return;
  const Node n=nodes[i];PartialSummary p={};Summary& o=p.value;
  o.max_degree=g.count[i];o.condition=n.condition;o.lambda=n.lambda;
  o.gamma_min=n.gamma.v;o.gamma_max=n.gamma.v;o.material_root_ratio=n.root_ratio;
  if(n.status==unsigned(fsoil::Status::Elastic))o.elastic=1;else if(n.status==unsigned(fsoil::Status::Smooth))o.smooth=1;
  else if(n.status==unsigned(fsoil::Status::Apex))o.apex=1;else if(n.status==unsigned(fsoil::Status::TensionRepair))o.tension=1;
  o.max_force=__dsqrt_rn((Dot(n.force,n.force)).v);o.max_delta_ace=n.delta_ace;
  o.max_commit_error=n.commit_error;o.commit_budget=n.commit_budget;
  o.node_work=n.node_work;o.net_x=n.force.x.v;o.net_z=n.force.z.v;o.torque=Cross(n.x,n.force).v;
  p.work_scale=n.work_scale;p.force_scale=n.force_abs;p.torque_scale=n.torque_scale;
  p.lever_scale=(fabs(n.x.x.v)+fabs(n.x.z.v))*n.force_abs;
  R oldE(0),keptE(0),deadE(0),newE(0),rowWork(0),loss(0),rotation(0);
  for(unsigned k=0;k<memory.count[i];k++){
    const V e=memory.e[i*Neighbors+k];const R E=R(.5)*Dot(e,e);oldE=oldE+E;
    if(Find(g.ids+i*Neighbors,g.count[i],memory.ids[i*Neighbors+k])<0){deadE=deadE+E;o.dead++;}
  }
  for(unsigned k=0;k<g.count[i];k++){
    const Row r=g.row[i*Neighbors+k];o.rows++;o.kept+=r.kept;o.born+=!r.kept;o.known_constant_rows+=r.known_constant;
    keptE=keptE+R(r.Eold);newE=newE+R(r.Enew);rowWork=rowWork+R(r.work);loss=loss+R(r.loss);rotation=rotation+R(r.rotation);
    o.max_local_angle=fmax(o.max_local_angle,r.angle);o.min_r=o.min_r>0?fmin(o.min_r,r.r.v):r.r.v;
    p.energy_scale+=fabs(r.Eold)+fabs(r.Enew)+fabs(r.loss)+fabs(r.rotation);p.work_scale+=r.abs_work;p.terms+=48;
  }
  o.Eold=oldE.v;o.Ekept=keptE.v;o.Edead=deadE.v;o.Enew=newE.v;o.row_work=rowWork.v;
  o.loading_loss=loss.v;o.rotation_change=rotation.v;
  p.terms+=32;output[i]=p;
}
// The final serial pass is O(5000) small summaries, not O(all directed rows).
__global__ void SummaryKernel(Stage s,const PartialSummary* partial,const Failure* fail,Summary* output){
  if(blockIdx.x||threadIdx.x)return;Summary o={};o.np=s.np;o.source_time=s.time;o.dt=s.dt;o.gamma_min=CUDART_INF;
  o.invalid_id=fail->id;o.invalid_slot=fail->slot;o.error=fail->bits;
  if(fail->bits){*output=o;return;}
  R oldE(0),keptE(0),deadE(0),newE(0),rowWork(0),nodeWork(0),loss(0),rotation(0),nx(0),nz(0),torque(0);
  double workScale=0,forceScale=0,torqueScale=0,leverScale=0,energyScale=0;unsigned long long terms=64;
  for(unsigned i=0;i<Nodes;i++){
    const PartialSummary p=partial[i];const Summary& q=p.value;
    o.max_degree=max(o.max_degree,q.max_degree);o.condition=fmax(o.condition,q.condition);o.lambda=fmax(o.lambda,q.lambda);
    o.gamma_min=fmin(o.gamma_min,q.gamma_min);o.gamma_max=fmax(o.gamma_max,q.gamma_max);
    o.material_root_ratio=fmax(o.material_root_ratio,q.material_root_ratio);
    o.elastic+=q.elastic;o.smooth+=q.smooth;o.apex+=q.apex;o.tension+=q.tension;
    o.max_force=fmax(o.max_force,q.max_force);o.max_delta_ace=fmax(o.max_delta_ace,q.max_delta_ace);
    o.max_commit_error=fmax(o.max_commit_error,q.max_commit_error);o.commit_budget=fmax(o.commit_budget,q.commit_budget);
    o.rows+=q.rows;o.kept+=q.kept;o.born+=q.born;o.dead+=q.dead;o.known_constant_rows+=q.known_constant_rows;
    o.max_local_angle=fmax(o.max_local_angle,q.max_local_angle);o.min_r=o.min_r>0?fmin(o.min_r,q.min_r):q.min_r;
    oldE=oldE+R(q.Eold);keptE=keptE+R(q.Ekept);deadE=deadE+R(q.Edead);newE=newE+R(q.Enew);
    rowWork=rowWork+R(q.row_work);nodeWork=nodeWork+R(q.node_work);loss=loss+R(q.loading_loss);rotation=rotation+R(q.rotation_change);
    nx=nx+R(q.net_x);nz=nz+R(q.net_z);torque=torque+R(q.torque);
    workScale+=p.work_scale;forceScale+=p.force_scale;torqueScale+=p.torque_scale;leverScale+=p.lever_scale;energyScale+=p.energy_scale;
    terms+=p.terms+32; // Includes the added receiver-to-final scalar reductions.
  }
  o.dt_over_limit=(R(s.dt)*Root(R(o.lambda))/R(.2)).v;
  o.Eold=oldE.v;o.Ekept=keptE.v;o.Edead=deadE.v;o.Enew=newE.v;o.row_work=rowWork.v;o.node_work=nodeWork.v;
  o.loading_loss=loss.v;o.rotation_change=rotation.v;o.ledger=(newE-oldE+nodeWork+loss+deadE).v;
  o.adjoint_defect=(nodeWork-rowWork).v;o.net_x=nx.v;o.net_z=nz.v;o.torque=torque.v;
  // Diagnostic roundoff scales, NOT outward CPU certificates or physical gates.
  // The partial/final reduction changes only these observations' summation order.
  const double gsum=Gamma(terms),conditioning=fmax(1.,o.condition);
  o.adjoint_budget=gsum*conditioning*workScale;
  o.net_budget=gsum*conditioning*forceScale;o.torque_budget=gsum*conditioning*(torqueScale+leverScale);
  o.ledger_budget=gsum*conditioning*(energyScale+workScale+fabs(oldE.v)+fabs(deadE.v));
  *output=o;
}
__global__ void AceUnchangedKernel(const Node* nodes,const float3* ace,Failure* fail){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=Nodes||atomicAdd(&fail->bits,0u))return;
  const Node n=nodes[i];const float3 a=ace[n.slot];
  if(!Bits(a.x,n.old_ace.x)||!Bits(a.y,n.old_ace.y)||!Bits(a.z,n.old_ace.z))Fail(fail,ForceReject,FirstId+i,n.slot,4);
}
__global__ void CommitAceKernel(const Node* nodes,float3* ace){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=Nodes)return;const Node n=nodes[i];
  // y is deliberately untouched; this is exactly one actual x/z float commit.
  ace[n.slot].x=n.new_ace.x;ace[n.slot].z=n.new_ace.z;
}
__global__ void CheckMaterialKernel(unsigned np,const unsigned* id,const unsigned* map,const tsymatrix3d* sigma,
  const float* kappa,bool corrector,Node* nodes,Failure* fail){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=Nodes||atomicAdd(&fail->bits,0u))return;
  const unsigned p=map[FirstId+i];if(p==~0u||p>=np||id[p]!=FirstId+i){Fail(fail,Identity,FirstId+i,p,20);return;}
  Node n=nodes[i];const double2* native=reinterpret_cast<const double2*>(sigma);
  const double2 a0=native[p*3],a1=native[p*3+1],a2=native[p*3+2];
  const double a[6]={a0.x,a0.y,a1.x,a1.y,a2.x,a2.y};
  const double e[6]={n.expected.xx,n.expected.xy,n.expected.xz,n.expected.yy,n.expected.yz,n.expected.zz};
  for(unsigned k=0;k<6;k++)if(!Bits(a[k],e[k])){Fail(fail,MaterialMismatch,FirstId+i,p,k,a[k],e[k],double(n.old_kappa),double(n.new_kappa));return;}
  const float expected=corrector?n.new_kappa:n.old_kappa;
  if(!Bits(kappa[p],expected)){Fail(fail,MaterialMismatch,FirstId+i,p,6,double(kappa[p]),double(expected),double(n.old_kappa),double(n.new_kappa));return;}
  n.checked=1;nodes[i]=n;
}

void Need(bool b,const std::string& s){if(!b)throw std::runtime_error("Private C08 HG: "+s);}
void Cuda(cudaError_t status,const char* where){
  if(status!=cudaSuccess)throw std::runtime_error(std::string("Private C08 HG CUDA ")+where+": "+cudaGetErrorString(status));
}
bool Same(double a,double b){return std::memcmp(&a,&b,sizeof(double))==0;}
bool Same(float a,float b){return std::memcmp(&a,&b,sizeof(float))==0;}
template<class A> void Alloc(A*& p,size_t n){Cuda(cudaMalloc(reinterpret_cast<void**>(&p),n*sizeof(A)),"persistent allocation");}
template<class A> void Release(A*& p)noexcept{if(p)cudaFree(p);p=nullptr;}
struct Impl{
  unsigned* map=nullptr;Node* node=nullptr;Failure* failure=nullptr;Summary* device_summary=nullptr;PartialSummary* partial_summary=nullptr;
  Graph graph={};MemoryView memory={};Summary latest={},pre={},cor={};Config config={};
  unsigned step=0,accepted_step=0,last_saved=~0u;double time=0,accepted_time=0,accumulated_angle=0;bool initialized=false,have_pre=false,pre_checked=false,have_cor=false,cor_checked=false,have_accept=false,wrote=false;
  unsigned long long pre_calls=0,cor_calls=0,commits=0,accepted_born=0,accepted_dead=0;double accepted_discarded_energy=0;std::string directory,error_phase="uninitialized";
#ifdef C08_HG_DEBUG_SNAPSHOT
  DebugNode* debug_snapshot=nullptr;bool debug_ready=false,debug_written=false;unsigned debug_step=0;double debug_time=0,debug_width=0;
#endif
  ~Impl()noexcept{
    Release(map);Release(node);Release(failure);Release(device_summary);Release(partial_summary);Release(graph.count);Release(graph.ids);Release(graph.next_e);Release(graph.row);
    Release(memory.count);Release(memory.ids);Release(memory.e);
#ifdef C08_HG_DEBUG_SNAPSHOT
    Release(debug_snapshot);
#endif
  }
  void Allocate(){
    Alloc(map,Original);Alloc(node,Nodes);Alloc(failure,1);Alloc(device_summary,1);Alloc(partial_summary,Nodes);
    Alloc(graph.count,Nodes);Alloc(graph.ids,Slots);Alloc(graph.next_e,Slots);Alloc(graph.row,Slots);
    Alloc(memory.count,Nodes);Alloc(memory.ids,Slots);Alloc(memory.e,Slots);
    Cuda(cudaMemset(memory.count,0,Nodes*sizeof(unsigned)),"cold edge memory");
#ifdef C08_HG_DEBUG_SNAPSHOT
    Alloc(debug_snapshot,Nodes);
#endif
  }
  void ClearError(){
    const Failure empty={0,~0u,~0u,0,0,{0,0,0,0}};Cuda(cudaMemcpy(failure,&empty,sizeof(empty),cudaMemcpyHostToDevice),"clear error");
    Cuda(cudaMemset(map,0xff,Original*sizeof(unsigned)),"clear ID map");
  }
  Failure ErrorNow(){
    Failure f={};Cuda(cudaMemcpy(&f,failure,sizeof(f),cudaMemcpyDeviceToHost),"error download");
    latest.error=f.bits;latest.invalid_id=f.id;latest.invalid_slot=f.slot;
    if(f.bits){std::ostringstream s;s<<"stage rejected bits="<<f.bits<<" native_id="<<f.id<<" sorted_slot="<<f.slot<<" detail="<<f.detail<<" step="<<step<<" phase="<<error_phase<<" source_time="<<std::setprecision(17)<<time<<" values=["<<f.value[0]<<","<<f.value[1]<<","<<f.value[2]<<","<<f.value[3]<<"]";throw std::runtime_error("Private C08 HG: "+s.str());}
    return f;
  }
  void Counts(Summary& s){s.pre_calls=pre_calls;s.cor_calls=cor_calls;s.commits=commits;}
  void Map(unsigned np,unsigned npb,const unsigned* id,const typecode* code){
    ClearError();MapKernel<<<(np+Block-1)/Block,Block>>>(np,npb,id,code,map,failure);Cuda(cudaGetLastError(),"ID map launch");
  }
};
void CheckConfig(const Config& c,const Stage& s){
  Need(s.np==Fixed+Nodes&&s.npb==Fixed&&s.dt==StepDt&&std::isfinite(s.time)&&s.time>=0.,"released complete-body 5us extent/finite clock differs");
  Need(c.h==.072f&&std::isfinite(c.bwen)&&c.bwen<0&&std::isfinite(c.G)&&c.G>0
    &&std::isfinite(c.vol0)&&c.vol0>0&&std::isfinite(c.rho0)&&c.rho0>0
    &&std::isfinite(c.rhow)&&c.rhow>0&&c.rho0>c.rhow&&c.solid0>0&&c.solid0<1,"positive H1.8 ledger/kernel constants differ");
  Need(s.cell&&s.id&&s.code&&s.xy&&s.z&&s.velocity&&s.J&&s.sigma_base&&s.sigma_rate&&s.kappa&&s.ace
    &&s.cells.beginendcell&&s.cells.axis==MGDIV_Z&&s.cells.nc.x>0&&s.cells.nc.y>0&&s.cells.nc.z>0&&s.cells.nc.w>0
    &&(s.cells.scelldiv==1||s.cells.scelldiv==2),"actual stage arrays/cell grid invalid");
}
bool SameConfig(const Config& a,const Config& b){return Same(a.vol0,b.vol0)&&Same(a.rho0,b.rho0)&&Same(a.rhow,b.rhow)&&Same(a.solid0,b.solid0)&&Same(a.h,b.h)&&Same(a.bwen,b.bwen)&&Same(a.G,b.G);}
void Csv(std::ostream& o,const char* phase,const Summary& s,unsigned completed,double saved,unsigned long long acceptedBorn,unsigned long long acceptedDead,double discarded,double angle){
  o<<std::setprecision(17)<<phase<<','<<completed<<','<<saved<<','<<s.source_time<<','<<s.dt<<','<<s.pre_calls<<','<<s.cor_calls<<','<<s.commits
    <<','<<s.error<<','<<s.invalid_id<<','<<s.invalid_slot<<','<<s.np<<','<<s.rows<<','<<s.max_degree<<','<<s.known_constant_rows
    <<','<<s.elastic<<','<<s.smooth<<','<<s.apex<<','<<s.tension<<','<<s.material_checked<<','<<s.gamma_min<<','<<s.gamma_max<<','<<s.material_root_ratio
    <<','<<s.kept<<','<<s.born<<','<<s.dead<<','<<s.condition<<','<<s.lambda<<','<<s.dt_over_limit<<','<<s.min_r<<','<<s.max_local_angle
    <<','<<s.Eold<<','<<s.Ekept<<','<<s.Edead<<','<<s.Enew<<','<<s.row_work<<','<<s.node_work<<','<<s.loading_loss<<','<<s.rotation_change<<','<<s.ledger<<','<<s.ledger_budget
    <<','<<s.adjoint_defect<<','<<s.adjoint_budget<<','<<s.net_x<<','<<s.net_z<<','<<s.net_budget<<','<<s.torque<<','<<s.torque_budget
    <<','<<s.max_force<<','<<s.max_delta_ace<<','<<s.max_commit_error<<','<<s.commit_budget<<','<<acceptedBorn<<','<<acceptedDead<<','<<discarded<<','<<angle<<'\n';
}

// Failure-only Pre raw observation. Actual material status/returned kappa are NOT observed.
std::string MatProbeQuoted(const std::string& text){
  std::ostringstream out;out<<'"';
  for(unsigned char c:text){
    if(c=='"'||c=='\\')out<<'\\'<<char(c);
    else if(c=='\n')out<<"\\n";else if(c=='\r')out<<"\\r";else if(c=='\t')out<<"\\t";
    else if(c<32)out<<"\\u00"<<std::hex<<std::setw(2)<<std::setfill('0')<<unsigned(c)<<std::dec;
    else out<<char(c);
  }out<<'"';return out.str();
}
template<class F> void MatProbeValue(std::ostream& out,const std::string& name,F value,bool& comma){
  static_assert(sizeof(F)==4||sizeof(F)==8,"Only native float/double raw values");
  uint64_t bits=0;std::memcpy(&bits,&value,sizeof(F));
  std::ostringstream decimal,hex;decimal<<std::setprecision(17)<<double(value);
  hex<<std::hex<<std::setw(unsigned(sizeof(F)*2))<<std::setfill('0')<<bits;
  if(comma)out<<",\n";comma=true;
  out<<"    {\"name\":"<<MatProbeQuoted(name)<<",\"storage\":\"binary"<<sizeof(F)*8
     <<"\",\"decimal17\":"<<MatProbeQuoted(decimal.str())<<",\"ieee_hex\":"<<MatProbeQuoted(hex.str())<<'}';
}
void CapturePreMismatch(Impl& p,unsigned np,const unsigned* id,const tsymatrix3d* actual_sigma,
  const float* actual_kappa,const tsymatrix3d* base_sigma,const tsymatrix3f* rate,
  const std::string& directory,const std::string& first_error){
  // Preserve the genuinely observed first cause BEFORE any further CUDA read.
  std::string dir=directory;if(!dir.empty()&&dir.back()!='/'&&dir.back()!='\\')dir+='/';
  const std::string first=dir+"C08HGMatProbeFirstError.json",raw=dir+"C08HGMatProbePreRaw.json";
  Need(!std::ifstream(first).good()&&!std::ifstream(raw).good(),"existing material raw evidence protected");
  std::ofstream cause(first);cause<<std::setprecision(17)
    <<"{\"schema\":1,\"phase\":\"PreMaterial\",\"first_error\":"<<MatProbeQuoted(first_error)
    <<",\"source_step\":"<<p.step
    <<",\"reported_clock_is_not_saved_native_state\":true,\"strict_rejection_retained\":true,\"values\":[\n";
  bool first_comma=false;MatProbeValue(cause,"source_time_s",p.time,first_comma);cause<<"\n]}\n";
  cause.flush();Need(bool(cause),"cannot preserve original material first error");
  Failure f={};Cuda(cudaMemcpy(&f,p.failure,sizeof(f),cudaMemcpyDeviceToHost),"failure-only first mismatch download");
  Need(f.bits==MaterialMismatch&&f.claimed&&f.id>=FirstId&&f.id<Original&&f.slot<np&&f.detail<=6,
    "raw capture requires the genuinely claimed isolated material mismatch");
  Need(base_sigma&&rate&&id&&actual_sigma&&actual_kappa,"Pre live base/rate/context missing");
  unsigned actual_id=~0u,mapped=~0u;
  Cuda(cudaMemcpy(&actual_id,id+f.slot,sizeof(actual_id),cudaMemcpyDeviceToHost),"failure-only actual native ID");
  Cuda(cudaMemcpy(&mapped,p.map+f.id,sizeof(mapped),cudaMemcpyDeviceToHost),"failure-only native map");
  Need(actual_id==f.id&&mapped==f.slot,"failure raw ID/map/slot differs");
  Node shadow={};double2 base[3]={},actual[3]={};float2 rsigma[3]={};float actual_old_kappa=0;
  Cuda(cudaMemcpy(&shadow,p.node+(f.id-FirstId),sizeof(shadow),cudaMemcpyDeviceToHost),"failure-only shadow node");
  Cuda(cudaMemcpy(base,reinterpret_cast<const double2*>(base_sigma)+size_t(f.slot)*3,sizeof(base),cudaMemcpyDeviceToHost),"failure-only live SigmaPreg");
  Cuda(cudaMemcpy(rsigma,reinterpret_cast<const float2*>(rate)+size_t(f.slot)*3,sizeof(rsigma),cudaMemcpyDeviceToHost),"failure-only live Rsigma");
  Cuda(cudaMemcpy(actual,reinterpret_cast<const double2*>(actual_sigma)+size_t(f.slot)*3,sizeof(actual),cudaMemcpyDeviceToHost),"failure-only actual half sigma");
  Cuda(cudaMemcpy(&actual_old_kappa,actual_kappa+f.slot,sizeof(actual_old_kappa),cudaMemcpyDeviceToHost),"failure-only predictor old kappa");
  Need(shadow.slot==f.slot,"material shadow and actual Pre slot differ");
  const double b[6]={base[0].x,base[0].y,base[1].x,base[1].y,base[2].x,base[2].y};
  const float r[6]={rsigma[0].x,rsigma[0].y,rsigma[1].x,rsigma[1].y,rsigma[2].x,rsigma[2].y};
  const double a[6]={actual[0].x,actual[0].y,actual[1].x,actual[1].y,actual[2].x,actual[2].y};
  const double e[6]={shadow.expected.xx,shadow.expected.xy,shadow.expected.xz,shadow.expected.yy,shadow.expected.yz,shadow.expected.zz};
  const char* component[6]={"xx","xy","xz","yy","yz","zz"};
  std::ofstream out(raw);out<<"{\n  \"schema\":1,\"capture\":\"failure_only_PreMaterial\",\"native_id\":"<<f.id
    <<",\"sorted_slot\":"<<f.slot<<",\"failure_bits\":"<<f.bits<<",\"failure_component\":"<<f.detail
    <<",\"source_step\":"<<p.step<<",\"shadow_status\":"<<shadow.status
    <<",\"shadow_status_is_actual_status\":false,\"actual_material_status_observed\":false"
    <<",\"actual_returned_kappa_observed\":false,\"actual_Pre_kappa_array_still_old\":true"
    <<",\"packed_order\":\"(xx,xy)/(xz,yy)/(yz,zz)\",\"base_is_live_SigmaPreg\":true"
    <<",\"strict_rejection_retained\":true,\"saved_native_failure_state_claimed\":false"
    <<",\"first_error\":"<<MatProbeQuoted(first_error)<<",\n  \"values\":[\n";
  bool comma=false;
  MatProbeValue(out,"source_time_s",p.time,comma);MatProbeValue(out,"operator_width_s",StepDt*.5,comma);
  for(unsigned k=0;k<6;k++)MatProbeValue(out,std::string("base_sigma.")+component[k],b[k],comma);
  for(unsigned k=0;k<6;k++)MatProbeValue(out,std::string("sigma_rate.")+component[k],r[k],comma);
  for(unsigned k=0;k<6;k++)MatProbeValue(out,std::string("actual_half_sigma.")+component[k],a[k],comma);
  for(unsigned k=0;k<6;k++)MatProbeValue(out,std::string("shadow_expected_sigma.")+component[k],e[k],comma);
  MatProbeValue(out,"actual_Pre_kappa_array_old",actual_old_kappa,comma);
  MatProbeValue(out,"shadow_old_kappa",shadow.old_kappa,comma);MatProbeValue(out,"shadow_returned_kappa",shadow.new_kappa,comma);
  MatProbeValue(out,"shadow_qtrial",shadow.qtrial,comma);MatProbeValue(out,"shadow_qreturn",shadow.qreturn,comma);
  MatProbeValue(out,"shadow_gamma",shadow.gamma.v,comma);MatProbeValue(out,"shadow_root_ratio",shadow.root_ratio,comma);
  for(unsigned k=0;k<4;k++)MatProbeValue(out,"failure_reported_value_"+std::to_string(k),f.value[k],comma);
  out<<"\n  ]\n}\n";out.flush();Need(bool(out),"failure-only material raw write failed");
}
} // anonymous namespace

State::State():impl_(nullptr){}
State::~State()noexcept{delete static_cast<Impl*>(impl_);impl_=nullptr;}
void State::StageForce(const Config& c,const Material& material,const Stage& s){
  CheckConfig(c,s);
  if(!impl_){std::unique_ptr<Impl> p(new Impl);p->Allocate();impl_=p.release();}
  auto& p=*static_cast<Impl*>(impl_);
  if(!p.initialized){Need(!s.corrector&&s.nstep==2000000&&Same(s.time,ActualSourceTime),"first HG force must be original certified 2M scalar-clock release predictor");p.config=c;p.initialized=true;}
  Need(SameConfig(p.config,c),"actual kernel/ledger configuration changed");
  if(!s.corrector){
    Need(!p.have_pre&&!p.have_cor&&p.commits<=std::numeric_limits<unsigned>::max()-2000000&&s.nstep==2000000+unsigned(p.commits),"predictor called before full acceptance or at nonoriginal release step");
    Need(!p.have_accept||(s.nstep==p.accepted_step&&Same(s.time,p.accepted_time)),"predictor source clock is not last accepted scalar clock");
    p.step=s.nstep;p.time=s.time;p.pre_checked=p.cor_checked=false;
  }else Need(p.have_pre&&p.pre_checked&&!p.have_cor&&s.nstep==p.step&&Same(s.time,p.time),"corrector lacks checked same-step predictor");
  p.error_phase=s.corrector?"CorForce":"PreForce";p.Map(s.np,s.npb,s.id,s.code);
  NodeKernel<<<(Nodes+Block-1)/Block,Block>>>(c,material,s,p.map,p.node,p.failure);Cuda(cudaGetLastError(),"material/map launch");
  NeighborKernel<<<(Nodes+Block-1)/Block,Block>>>(c,s,p.map,p.node,p.graph,p.failure);Cuda(cudaGetLastError(),"neighbor launch");
  FitKernel<<<(Nodes+Block-1)/Block,Block>>>(c,p.node,p.graph,p.failure);Cuda(cudaGetLastError(),"LS launch");
  RowKernel<<<(Nodes+Block-1)/Block,Block>>>(s,p.node,p.graph,p.memory,p.failure);Cuda(cudaGetLastError(),"memory/local advance launch");
  AdjointFitKernel<<<(Nodes+Block-1)/Block,Block>>>(p.node,p.graph,p.failure);Cuda(cudaGetLastError(),"adjoint fit launch");
  AdjointRowKernel<<<(Nodes+Block-1)/Block,Block>>>(p.node,p.graph,p.failure);Cuda(cudaGetLastError(),"adjoint row launch");
  ForceKernel<<<(Nodes+Block-1)/Block,Block>>>(s,p.node,p.graph,p.failure);Cuda(cudaGetLastError(),"force gather launch");
  LocalSummaryKernel<<<(Nodes+Block-1)/Block,Block>>>(p.node,p.graph,p.memory,p.failure,p.partial_summary);Cuda(cudaGetLastError(),"bounded receiver summary launch");
  SummaryKernel<<<1,1>>>(s,p.partial_summary,p.failure,p.device_summary);Cuda(cudaGetLastError(),"5000-summary final reduction launch");
  Cuda(cudaMemcpy(&p.latest,p.device_summary,sizeof(Summary),cudaMemcpyDeviceToHost),"small summary download");p.ErrorNow();
  Need(p.latest.elastic+p.latest.smooth+p.latest.apex+p.latest.tension==Nodes&&p.latest.rows>0&&p.latest.rows<=Slots
    &&p.latest.kept+p.latest.born==p.latest.rows&&std::isfinite(p.latest.condition)&&p.latest.condition<1e8
    &&std::isfinite(p.latest.dt_over_limit)&&p.latest.dt_over_limit<=1&&p.latest.gamma_min>=0&&p.latest.gamma_max<=1
    &&std::isfinite(p.latest.max_local_angle)&&p.latest.max_local_angle<.005,"actual summary coverage/positive/rank/dt/rotation/gamma domain differs");
  const double observed[]={p.latest.Eold,p.latest.Ekept,p.latest.Edead,p.latest.Enew,p.latest.row_work,p.latest.node_work,p.latest.loading_loss,p.latest.rotation_change,p.latest.ledger,p.latest.ledger_budget,p.latest.adjoint_defect,p.latest.adjoint_budget,p.latest.net_x,p.latest.net_z,p.latest.net_budget,p.latest.torque,p.latest.torque_budget,p.latest.max_force,p.latest.max_delta_ace,p.latest.max_commit_error,p.latest.commit_budget,p.latest.material_root_ratio};
  for(double v:observed)Need(std::isfinite(v),"nonfinite actual phase observation/budget");
  AceUnchangedKernel<<<(Nodes+Block-1)/Block,Block>>>(p.node,s.ace,p.failure);Cuda(cudaGetLastError(),"precommit Ace check launch");p.ErrorNow();
  CommitAceKernel<<<(Nodes+Block-1)/Block,Block>>>(p.node,s.ace);Cuda(cudaGetLastError(),"single Ace commit launch");
#ifdef C08_HG_DEBUG_SNAPSHOT
  if(!s.corrector&&!p.debug_ready){
    Need(s.nstep==2000000&&p.commits==0&&p.pre_calls==0,"Debug snapshot must be original cold first n stage");
    DebugSnapshotKernel<<<(Nodes+Block-1)/Block,Block>>>(p.node,p.debug_snapshot);Cuda(cudaGetLastError(),"Debug first-n output-only snapshot launch");
    p.debug_ready=true;p.debug_step=s.nstep;p.debug_time=s.time;p.debug_width=s.dt*.5;
  }
#endif
  if(s.corrector){p.have_cor=true;p.cor_calls++;p.Counts(p.latest);p.cor=p.latest;}
  else{p.have_pre=true;p.pre_calls++;p.Counts(p.latest);p.pre=p.latest;}
}
void State::CheckMaterial(unsigned np,unsigned npb,const unsigned* id,const typecode* code,const tsymatrix3d* sigma,const float* kappa,bool corrector,const tsymatrix3d* diagnostic_base,const tsymatrix3f* diagnostic_rate,const std::string& diagnostic_dir){
  Need(impl_&&np==Fixed+Nodes&&npb==Fixed&&id&&code&&sigma&&kappa,"material-check extent/state invalid");
  auto& p=*static_cast<Impl*>(impl_);
  Need(corrector?(p.have_cor&&!p.cor_checked):(p.have_pre&&!p.pre_checked&&!p.have_cor),"material-check phase/order differs");
  p.error_phase=corrector?"CorMaterial":"PreMaterial";p.Map(np,npb,id,code);
  CheckMaterialKernel<<<(Nodes+Block-1)/Block,Block>>>(np,id,p.map,sigma,kappa,corrector,p.node,p.failure);Cuda(cudaGetLastError(),"actual material bit check launch");
  try{p.ErrorNow();}
  catch(const std::exception& original){
    if(!corrector&&p.latest.error==MaterialMismatch){
      try{CapturePreMismatch(p,np,id,sigma,kappa,diagnostic_base,diagnostic_rate,diagnostic_dir,original.what());}
      catch(const std::exception& dump){std::ostringstream note;note<<"\nPrivate HG matprobe capture failed: "<<dump.what()
        <<"; original strict first error retained: "<<original.what()<<"\n";const std::string text=note.str();std::fwrite(text.data(),1,text.size(),stderr);}
    }
    throw;
  }

  p.latest.material_checked=Nodes;
  if(corrector){p.cor_checked=true;p.cor=p.latest;}else{p.pre_checked=true;p.pre=p.latest;}
}
void State::Accept(unsigned np,unsigned npb,const unsigned* id,const typecode* code,unsigned completed,double saved_time,double dt){
  Need(impl_&&np==Fixed+Nodes&&npb==Fixed&&id&&code&&dt==StepDt,"accept extent/state/dt invalid");auto& p=*static_cast<Impl*>(impl_);
  Need(p.have_pre&&p.pre_checked&&p.have_cor&&p.cor_checked&&completed==p.step+1,"accept requires both checked material stages and one completed update");
  double expected=p.time;expected+=dt;Need(Same(saved_time,expected),"accepted scalar +=dt clock differs");
  p.error_phase="Accept";p.Map(np,npb,id,code);p.ErrorNow();
  const double acceptedAngle=p.accumulated_angle+2.*fmax(p.pre.max_local_angle,p.cor.max_local_angle);
  Need(std::isfinite(acceptedAngle),"private objective accumulated angle is nonfinite");
  const double discarded=p.accepted_discarded_energy+p.cor.Edead;Need(std::isfinite(discarded),"accepted discarded energy is nonfinite");
  std::swap(p.memory.count,p.graph.count);std::swap(p.memory.ids,p.graph.ids);std::swap(p.memory.e,p.graph.next_e);
  p.accumulated_angle=acceptedAngle;p.accepted_born+=p.cor.born;p.accepted_dead+=p.cor.dead;p.accepted_discarded_energy=discarded;
  p.commits++;p.have_accept=true;p.accepted_step=completed;p.accepted_time=saved_time;
  p.have_pre=p.have_cor=false;p.Counts(p.latest);p.Counts(p.pre);p.Counts(p.cor);
}
void State::Save(const std::string& directory,unsigned completed,double saved_time){
  Need(impl_,"save called before explicitly ON stage");auto& p=*static_cast<Impl*>(impl_);
  Need(p.have_accept&&completed==p.accepted_step&&Same(saved_time,p.accepted_time)&&p.last_saved!=completed,"save is not the unique actual last accepted update");
  std::string dir=directory;if(!dir.empty()&&dir.back()!='/'&&dir.back()!='\\')dir+='/';
  Need(!p.wrote||dir==p.directory,"private sidecar output directory changed");
  const std::string csv=dir+"C08PlasticHG.csv",policy=dir+"C08PlasticHGPolicy.json";
#ifdef C08_HG_DEBUG_SNAPSHOT
  if(!p.debug_written){
    Need(p.debug_ready&&p.debug_step==2000000&&p.debug_width==StepDt*.5,"Debug first-n snapshot missing or wrong clock");
    const std::string nodecsv=dir+"C08PlasticHGDebugFirstN.csv",nodepolicy=dir+"C08PlasticHGDebugFirstN.json";
    Need(!std::ifstream(nodecsv).good()&&!std::ifstream(nodepolicy).good(),"existing Debug first-n snapshot protected");
    std::vector<DebugNode> snapshot(Nodes);Cuda(cudaMemcpy(snapshot.data(),p.debug_snapshot,Nodes*sizeof(DebugNode),cudaMemcpyDeviceToHost),"one Debug first-n snapshot download");
    std::ofstream policyout(nodepolicy);policyout<<std::setprecision(17)
      <<"{\"schema\":1,\"observation_only\":true,\"macro\":\"C08_HG_DEBUG_SNAPSHOT\",\"stage\":\"first_n\",\"step\":"<<p.debug_step<<",\"source_time_s\":"<<p.debug_time
      <<",\"nodes\":5000,\"first_id\":2060,\"h\":"<<double(p.config.h)<<",\"bwen\":"<<double(p.config.bwen)<<",\"G\":"<<double(p.config.G)<<",\"xi\":0.1,\"full_dt\":0.000005,\"width\":"<<p.debug_width
      <<",\"e0_exact_zero\":true,\"force_before_float_commit\":true,\"neighbor_order\":\"native_ID_per_receiver\",\"CPU_force_bits_claimed\":false}\n";
    policyout.flush();Need(bool(policyout),"Debug snapshot policy write failed");
    std::ofstream data(nodecsv);data<<std::setprecision(17)<<"native_id,x,z,vx,vz,volume,mass,gamma,HG_Fx,HG_Fz\n";
    for(unsigned i=0;i<Nodes;i++){const auto& q=snapshot[i];Need(q.id==FirstId+i,"Debug native input snapshot ID differs");data<<q.id<<','<<q.x<<','<<q.z<<','<<q.vx<<','<<q.vz<<','<<q.volume<<','<<q.mass<<','<<q.gamma<<','<<q.fx<<','<<q.fz<<'\n';}
    data.flush();Need(bool(data),"Debug snapshot CSV write failed");p.debug_written=true;
  }
#endif
  if(!p.wrote){
    Need(!std::ifstream(csv).good()&&!std::ifstream(policy).good(),"existing private sidecars protected");
    std::ofstream f(policy);f<<std::setprecision(17)
      <<"{\"schema\":1,\"policy\":\"PrivateC08EnergyNormalizedPlasticHG\",\"phase\":\"ReleaseOnly\",\"active\":true,\"xi\":0.1,\"nodes\":5000,\"first_id\":2060,\"neighbor_capacity\":128,"
      <<"\"kernel\":\"Wendland\",\"h\":"<<double(p.config.h)<<",\"dt\":0.000005,\"old_public_HG_unchanged\":true,\"same_stage_material_shadow\":true,\"material_bits_checked\":true,"
      <<"\"n_h_start_same_committed_e\":true,\"active_only_memory\":true,\"trial_edge_counts_per_phase\":true,\"cumulative_deletion_only_at_full_accept\":true,\"new_edge_zero\":true,\"removed_energy_recorded\":true,\"full_LS_adjoint\":true,\"HG_value_RN\":true,"
      <<"\"material_original_fast_math\":true,\"observer_budget_is_outward_certificate\":false,\"coupled_passivity_claimed\":false,\"same_stage_Darcy_required_by_host\":true,\"native_22_layout_changed\":false,\"physical_acceptance\":false}\n";
    f.flush();Need(bool(f),"policy write failed");
    std::ofstream h(csv);h<<"phase,completed_step,saved_time_s,source_time_s,dt_s,pre_calls,cor_calls,commits,error,invalid_id,invalid_slot,np,rows,max_degree,known_constant_rows,elastic,smooth,apex,tension,material_checked,gamma_min,gamma_max,material_root_ratio,kept,born,dead,condition,lambda_s2,dt_over_0p2_limit,min_r,max_half_angle,Eold,Ekept,Edead,Enew,row_work,node_work,loading_loss,rotation_change,ledger,ledger_budget,adjoint_defect,adjoint_budget,net_x,net_z,net_budget,torque,torque_budget,max_force,max_delta_ace,max_commit_error,commit_budget,accepted_born,accepted_dead,accepted_discarded_energy,objective_accumulated_angle\n";h.flush();Need(bool(h),"CSV header write failed");
    p.wrote=true;p.directory=dir;
  }
  std::ofstream f(csv,std::ios::out|std::ios::app);Csv(f,"Pre",p.pre,completed,saved_time,p.accepted_born,p.accepted_dead,p.accepted_discarded_energy,p.accumulated_angle);Csv(f,"Cor",p.cor,completed,saved_time,p.accepted_born,p.accepted_dead,p.accepted_discarded_energy,p.accumulated_angle);f.flush();Need(bool(f),"actual phase CSV append failed");p.last_saved=completed;
}
const Summary& State::Latest()const{static const Summary empty={};return impl_?static_cast<const Impl*>(impl_)->latest:empty;}
} // namespace c08hg

