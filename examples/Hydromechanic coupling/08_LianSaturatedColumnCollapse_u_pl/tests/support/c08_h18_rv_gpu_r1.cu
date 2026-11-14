// Private standalone CUDA TU: original physical CUDA objects are not recompiled.
#include "c08_h18_rv_gpu_r1.h"
#include <cfloat>
#include <cmath>
#include <cstddef>
#include <math_constants.h>
// Deliberately no CTE_AVAILABLE and no external/device-link constant dependency.
namespace c08h18rv {
#include "FunctionsBasic_iker.h"
#include "FunSphKernel_iker.h"
#include "JCellSearch_iker.h"
enum Error {Input=1u,Coincident=2u,Weight=4u,Rank=8u,Fit=16u,Neighbor=32u,Force=64u,Bound=128u,Certificate=256u,Manufactured=512u};
constexpr unsigned Nodes=5000,Block=256;
struct Params {double solid0,rho0,rhow,vol0,dt;float h,bwen,G;unsigned mode;};
struct Node {double2 x,v;double V,rho,tau;};
struct FitData {double4 L;double condition,lambda;unsigned count,reverse;};
struct NodeResult {
  float3 ace; // cudaMemcpy2D commits exactly these first12 bytes, only after acceptance.
  double2 force,committedForce;
  double work,torque,nodePower,torqueScale,forcePairs,rawScale,form,contraction,normalWorkBudget,normalTorqueBudget;
  double torquePrediction,maxResidual,forceBudget,forceNorm,edgeVelocity,normalRatio,commitRatio;
  double committedWork,committedTorque,commitForceBudget,commitTorqueBudget,commitWorkBudget;
};
struct Summary {Result result;double2 net,committedNet;double rawScale,nodePower,torqueScale,forcePairs,contraction,normalWorkBudget,normalTorqueBudget;
  double edgeVelocity,commitForceBudget,commitTorqueBudget,commitWorkBudget;};
static __device__ double Len(double2 a){return sqrt(a.x*a.x+a.y*a.y);}
static __device__ double Dot(double2 a,double2 b){return a.x*b.x+a.y*b.y;}
static __device__ double2 Mul(double4 l,double2 d){return make_double2(l.x*d.x+l.y*d.y,l.z*d.x+l.w*d.y);}
static __device__ double Norm(double4 a){return sqrt(a.x*a.x+a.y*a.y+a.z*a.z+a.w*a.w);}
static __device__ double Ratio(double x,double b){return b>0?x/b:(x==0?0:CUDART_INF);}
static __device__ double2 Synthetic(unsigned mode,double2 x){
  // Explicit global-coordinate fields. Centering changes only a constant mode;
  // no claim of bit-identical input to the old centered CPU manufactured test.
  if(mode==1)return make_double2(.25,-.125);
  if(mode==2)return make_double2(.07*x.x-.04*x.y+.2,.03*x.x+.02*x.y-.1);
  return make_double2(.08*x.y,-.08*x.x);
}
static __device__ bool GetNode(unsigned p,unsigned np,unsigned npb,const unsigned* idp,const double2* xy,const double* z,
 const float4* velocity,const typecode* code,const double* J,const Params& c,Node& a){
  if(p<npb||p>=np||!CODE_IsNormal(code[p])||!CODE_IsFluid(code[p])||idp[p]<2060||idp[p]>=7060)return false;
  const double j=J[p],g=double(c.G);a.x=make_double2(xy[p].x,z[p]);
  a.v=c.mode?Synthetic(c.mode,a.x):make_double2(double(velocity[p].x),double(velocity[p].z));
  a.V=c.vol0*j;a.rho=c.rhow+(c.rho0-c.rhow)/j;a.tau=double(c.h)/sqrt(g/a.rho);
  return isfinite(g)&&g>0&&isfinite(j)&&j>c.solid0&&isfinite(a.V)&&a.V>0&&isfinite(a.rho)&&a.rho>0
    &&isfinite(a.tau)&&a.tau>0&&isfinite(a.x.x)&&isfinite(a.x.y)&&xy[p].y==0&&velocity[p].y==0
    &&isfinite(a.v.x)&&isfinite(a.v.y);
}
static __device__ bool ReverseMember(unsigned i,unsigned j,const StDivDataGpu& d,const unsigned* cell){
  int i1,f1,i2,f2,i3,f3;cunsearch::Initsp(cell[j],unsigned(d.axis),d.domcellcode,d.scelldiv,d.nc,d.cellzero,i1,f1,i2,f2,i3,f3);
  for(int c3=i3;c3<f3;c3+=d.nc.w)for(int c2=i2;c2<f2;c2+=d.nc.x){unsigned b,e=0;
    cunsearch::ParticleRange(c2,c3,i1,f1,d.beginendcell+d.cellfluid,b,e);if(e&&i>=b&&i<e)return true;}
  return false;
}
static __device__ bool Pair(unsigned i,unsigned j,unsigned np,unsigned npb,const unsigned* idp,const double2* xy,const double* z,
 const float4* velocity,const typecode* code,const double* J,const Params& c,const Node& a,
 double2& d,double2& dv,double& momentWeight,double& beta,unsigned& error){
  Node b;if(!GetNode(j,np,npb,idp,xy,z,velocity,code,J,c,b)||idp[i]==idp[j]){error|=Input;return false;}
  d=make_double2(a.x.x-b.x.x,a.x.y-b.x.y);const double r2=Dot(d,d);
  if(!isfinite(r2)){error|=Input;return false;}if(r2==0){error|=Coincident;return false;}
  if(r2>=4.*double(c.h)*double(c.h))return false;
  const double w=-double(cufsph::GetKernel_Fac<KERNEL_Wendland>(float(r2),c.h,c.bwen));
  if(w==0)return false;if(!(w>0)||!isfinite(w)){error|=Weight;return false;}
  const double eta=double(c.G)*.5*(a.tau+b.tau);
  momentWeight=eta*b.V*w;
  beta=idp[i]<idp[j]?eta*a.V*b.V*w:eta*b.V*a.V*w;
  dv=make_double2(a.v.x-b.v.x,a.v.y-b.v.y);
  if(!isfinite(momentWeight)||!isfinite(beta)||!(momentWeight>0)||!(beta>0)){error|=Weight;return false;}
  return true;
}
__global__ void FitKernel(unsigned np,unsigned npb,StDivDataGpu dvd,const unsigned* cell,const unsigned* idp,const double2* xy,
 const double* z,const float4* v,const typecode* code,const double* J,Params c,FitData* fit,unsigned* errors){
  const unsigned p=npb+blockIdx.x*blockDim.x+threadIdx.x;if(p>=np)return;const unsigned row=p-npb;
  FitData out={};unsigned error=0;Node a;if(!GetNode(p,np,npb,idp,xy,z,v,code,J,c,a)){errors[row]=Input;fit[row]=out;return;}
  double mxx=0,mxz=0,mzz=0,nxx=0,nxz=0,nzx=0,nzz=0,degree=0;
  int i1,f1,i2,f2,i3,f3;cunsearch::Initsp(cell[p],unsigned(dvd.axis),dvd.domcellcode,dvd.scelldiv,dvd.nc,dvd.cellzero,i1,f1,i2,f2,i3,f3);
  for(int c3=i3;c3<f3;c3+=dvd.nc.w)for(int c2=i2;c2<f2;c2+=dvd.nc.x){unsigned begin,end=0;
    cunsearch::ParticleRange(c2,c3,i1,f1,dvd.beginendcell+dvd.cellfluid,begin,end);
    if(end)for(unsigned j=begin;j<end;j++){if(j==p)continue;double2 d,dv;double w,beta;
      if(!Pair(p,j,np,npb,idp,xy,z,v,code,J,c,a,d,dv,w,beta,error))continue;
      out.count++;if(ReverseMember(p,j,dvd,cell))out.reverse++;else error|=Neighbor;
      mxx+=w*d.x*d.x;mxz+=w*d.x*d.y;mzz+=w*d.y*d.y;
      nxx+=w*dv.x*d.x;nxz+=w*dv.x*d.y;nzx+=w*dv.y*d.x;nzz+=w*dv.y*d.y;degree+=beta;
    }}
  const double scale=fmax(fmax(fabs(mxx),fabs(mxz)),fabs(mzz));
  if(!(scale>0)||!isfinite(scale))error|=Rank;
  if(!error){const double aa=mxx/scale,b=mxz/scale,cc=mzz/scale,det=aa*cc-b*b;
    if(!(aa>0&&cc>0&&det>128.*DBL_EPSILON*(aa*cc+b*b)))error|=Rank;
    else{const double den=scale*det;
      out.L=make_double4((nxx*cc-nxz*b)/den,(-nxx*b+nxz*aa)/den,(nzx*cc-nzz*b)/den,(-nzx*b+nzz*aa)/den);
      const double large=.5*(aa+cc+hypot(aa-cc,2*b));out.condition=large/(det/large);
      out.lambda=2.*Alpha*degree/(a.rho*a.V);
      if(!isfinite(Norm(out.L))||!isfinite(out.condition)||!(out.condition>=1.)||!isfinite(out.lambda)||!(out.lambda>0))error|=Fit;
    }}fit[row]=out;errors[row]=error;
}
// Bounded O(N) serial summaries are deliberate first-port diagnostics, not an
// efficiency claim. Neither scans all pairs nor changes the original CUDA body.
__global__ void FitSummary(unsigned npb,const unsigned* idp,const FitData* fit,const unsigned* errors,Params c,Summary* out){
  if(blockIdx.x||threadIdx.x)return;Summary s={};s.result.invalid_sorted=s.result.invalid_native_id=~0u;s.result.mode=c.mode;
  for(unsigned row=0;row<Nodes;row++){const auto a=fit[row];const unsigned error=errors[row];
    if(error){s.result.error_bits|=error;if(s.result.invalid_sorted==~0u){s.result.invalid_sorted=npb+row;s.result.invalid_native_id=idp[npb+row];}}
    s.result.directed_edges+=a.count;s.result.reverse_memberships+=a.reverse;s.result.max_degree=max(s.result.max_degree,a.count);
    s.result.lambda_max=fmax(s.result.lambda_max,a.lambda);s.result.max_condition=fmax(s.result.max_condition,a.condition);
  }
  if(!s.result.directed_edges||(s.result.directed_edges&1u)||s.result.reverse_memberships!=s.result.directed_edges)s.result.error_bits|=Neighbor;
  const double ne=64.*double(Nodes+s.result.directed_edges/2+s.result.max_degree+1)*DBL_EPSILON;
  if(!isfinite(ne)||!(ne<1.))s.result.error_bits|=Fit;else s.result.gamma64=ne/(1.-ne);
  s.result.isolated_bound=c.dt*s.result.lambda_max*.5;
  if(!isfinite(s.result.isolated_bound)||s.result.isolated_bound>1.)s.result.error_bits|=Bound;
  if(!s.result.error_bits)s.result.validated_soil=Nodes;*out=s;
}
__global__ void ForceKernel(unsigned np,unsigned npb,StDivDataGpu dvd,const unsigned* cell,const unsigned* idp,const double2* xy,
 const double* z,const float4* v,const typecode* code,const double* J,Params c,const FitData* fit,const unsigned* fiterrors,
 const float3* ace,const Summary* summary,NodeResult* nodes,unsigned* errors){
  const unsigned p=npb+blockIdx.x*blockDim.x+threadIdx.x;if(p>=np)return;const unsigned row=p-npb;
  NodeResult o={};unsigned error=fiterrors[row];Node a;
  if(!GetNode(p,np,npb,idp,xy,z,v,code,J,c,a))error|=Input;
  if(error){nodes[row]=o;errors[row]=error;return;}
  const double4 li=fit[row].L;double4 defect=make_double4(0,0,0,0);double normalScale=0,forceScale=0;
  int i1,f1,i2,f2,i3,f3;cunsearch::Initsp(cell[p],unsigned(dvd.axis),dvd.domcellcode,dvd.scelldiv,dvd.nc,dvd.cellzero,i1,f1,i2,f2,i3,f3);
  for(int c3=i3;c3<f3;c3+=dvd.nc.w)for(int c2=i2;c2<f2;c2+=dvd.nc.x){unsigned begin,end=0;
    cunsearch::ParticleRange(c2,c3,i1,f1,dvd.beginendcell+dvd.cellfluid,begin,end);
    if(end)for(unsigned j=begin;j<end;j++){if(j==p)continue;double2 d,dv;double w,beta;
      if(!Pair(p,j,np,npb,idp,xy,z,v,code,J,c,a,d,dv,w,beta,error))continue;
      if(fiterrors[j-npb]){error|=Neighbor;continue;}
      const auto pi=Mul(li,d),pj=Mul(fit[j-npb].L,d);
      const auto ri=make_double2(dv.x-pi.x,dv.y-pi.y),rj=make_double2(dv.x-pj.x,dv.y-pj.y);
      const double f=-.5*Alpha*beta;const double2 pair=make_double2((ri.x+rj.x)*f,(ri.y+rj.y)*f);
      o.force.x+=pair.x;o.force.y+=pair.y;
      defect.x+=beta*ri.x*d.x;defect.y+=beta*ri.x*d.y;defect.z+=beta*ri.y*d.x;defect.w+=beta*ri.y*d.y;
      const double vv=Len(dv),l1=Len(pi),l2=Len(pj),distance=Len(d);
      normalScale+=beta*(vv+l1)*distance;forceScale+=Alpha*beta*(vv+l1+l2);
      // Each unordered edge appears twice globally; rawScale/form are halved in ForceSummary.
      o.rawScale+=Alpha*beta*(Dot(dv,dv)+Dot(pi,pi)+Dot(pj,pj));
      o.form+=.25*Alpha*beta*(Dot(ri,ri)+Dot(rj,rj));o.forcePairs+=Len(pair);
      o.maxResidual=fmax(o.maxResidual,fmax(Len(ri),Len(rj)));o.edgeVelocity=fmax(o.edgeVelocity,vv+l1+l2);
    }}
  const double gamma=summary->result.gamma64,normalBudget=4.*gamma*(1.+fit[row].condition)*normalScale;
  o.normalRatio=Ratio(Norm(defect),normalBudget);if(Norm(defect)>normalBudget)error|=Certificate;
  o.contraction=li.x*defect.x+li.y*defect.y+li.z*defect.z+li.w*defect.w;
  o.normalWorkBudget=.5*Alpha*Norm(li)*normalBudget;o.normalTorqueBudget=Alpha*normalBudget;
  o.torquePrediction=-.5*Alpha*(defect.y-defect.z);
  o.forceNorm=Len(o.force);o.forceBudget=4.*gamma*(1.+fit[row].condition)*forceScale;
  o.work=Dot(a.v,o.force);o.torque=a.x.y*o.force.x-a.x.x*o.force.y;
  o.nodePower=fabs(a.v.x*o.force.x)+fabs(a.v.y*o.force.y);
  o.torqueScale=fabs(a.x.y*o.force.x)+fabs(a.x.x*o.force.y);
  const double mass=a.rho*a.V;const double2 da=make_double2(o.force.x/mass,o.force.y/mass);const float3 old=ace[p];
  o.ace=make_float3(float(double(old.x)+da.x),old.y,float(double(old.z)+da.y));
  o.committedForce=make_double2((double(o.ace.x)-old.x)*mass,(double(o.ace.z)-old.z)*mass);
  const double2 errorForce=make_double2(o.committedForce.x-o.force.x,o.committedForce.y-o.force.y);
  const double oldNorm=sqrt(double(old.x)*old.x+double(old.y)*old.y+double(old.z)*old.z);
  o.commitForceBudget=2.*FLT_EPSILON*mass*(oldNorm+Len(da));o.commitRatio=Ratio(Len(errorForce),o.commitForceBudget);
  if(Len(errorForce)>o.commitForceBudget)error|=Certificate;
  o.committedWork=Dot(a.v,o.committedForce);o.committedTorque=a.x.y*o.committedForce.x-a.x.x*o.committedForce.y;
  o.commitTorqueBudget=Len(a.x)*o.commitForceBudget;o.commitWorkBudget=Len(a.v)*o.commitForceBudget;
  if(!isfinite(o.ace.x)||!isfinite(o.ace.y)||!isfinite(o.ace.z)||!isfinite(o.work)||!isfinite(o.form)
    ||!isfinite(o.normalRatio)||!isfinite(o.commitRatio)||!isfinite(o.forceBudget))error|=Force;
  nodes[row]=o;errors[row]=error;
}
__global__ void ForceSummary(unsigned npb,const unsigned* idp,const NodeResult* nodes,const unsigned* errors,Summary* out){
  if(blockIdx.x||threadIdx.x)return;Summary s=*out;auto& r=s.result;
  for(unsigned i=0;i<Nodes;i++){const auto& a=nodes[i];if(errors[i]){r.error_bits|=errors[i];if(r.invalid_sorted==~0u){r.invalid_sorted=npb+i;r.invalid_native_id=idp[npb+i];}}
    s.net.x+=a.force.x;s.net.y+=a.force.y;s.committedNet.x+=a.committedForce.x;s.committedNet.y+=a.committedForce.y;
    r.work+=a.work;r.torque+=a.torque;r.form+=a.form;s.rawScale+=a.rawScale;s.nodePower+=a.nodePower;s.torqueScale+=a.torqueScale;
    s.forcePairs+=a.forcePairs;s.contraction+=a.contraction;s.normalWorkBudget+=a.normalWorkBudget;s.normalTorqueBudget+=a.normalTorqueBudget;
    r.torque_defect_prediction+=a.torquePrediction;r.max_residual=fmax(r.max_residual,a.maxResidual);r.max_force=fmax(r.max_force,a.forceNorm);
    r.force_budget=fmax(r.force_budget,a.forceBudget);s.edgeVelocity=fmax(s.edgeVelocity,a.edgeVelocity);
    r.max_normal_budget_ratio=fmax(r.max_normal_budget_ratio,a.normalRatio);r.max_commit_budget_ratio=fmax(r.max_commit_budget_ratio,a.commitRatio);
    r.committed_work+=a.committedWork;r.committed_torque+=a.committedTorque;
    s.commitForceBudget+=a.commitForceBudget;s.commitTorqueBudget+=a.commitTorqueBudget;s.commitWorkBudget+=a.commitWorkBudget;
  }
  r.form*=.5;s.rawScale*=.5;
  r.work_defect_prediction=-.5*Alpha*s.contraction;
  r.work_certificate_error=r.work+2*r.form-r.work_defect_prediction;
  r.work_certificate_budget=r.gamma64*(s.rawScale+s.nodePower+2*r.form);
  r.work_budget=r.work_certificate_budget+s.normalWorkBudget;
  r.net_force_norm=Len(s.net);r.net_force_budget=r.gamma64*s.forcePairs;
  r.torque_certificate_error=r.torque-r.torque_defect_prediction;
  r.torque_certificate_budget=r.gamma64*(s.torqueScale+fabs(r.torque_defect_prediction));
  r.torque_budget=r.gamma64*s.torqueScale+s.normalTorqueBudget;
  r.committed_work_budget=r.work_budget+s.commitWorkBudget;
  r.committed_net_force_norm=Len(s.committedNet);r.committed_net_force_budget=r.net_force_budget+s.commitForceBudget;
  r.committed_torque_budget=r.torque_budget+s.commitTorqueBudget;
  r.residual_budget=4*r.gamma64*(1+r.max_condition)*s.edgeVelocity;
  *out=s;
}
struct Scratch {FitData* fit=nullptr;unsigned* fiterrors=nullptr;NodeResult* nodes=nullptr;unsigned* errors=nullptr;Summary* summary=nullptr;
 ~Scratch(){cudaFree(summary);cudaFree(errors);cudaFree(nodes);cudaFree(fiterrors);cudaFree(fit);}};
static bool FiniteResult(const Result& r){
  const double q[]={r.lambda_max,r.isolated_bound,r.gamma64,r.max_condition,r.work,r.form,r.work_defect_prediction,r.work_certificate_error,r.work_certificate_budget,r.work_budget,
    r.net_force_norm,r.net_force_budget,r.torque,r.torque_defect_prediction,r.torque_certificate_error,r.torque_certificate_budget,r.torque_budget,
    r.committed_work,r.committed_work_budget,r.committed_net_force_norm,r.committed_net_force_budget,r.committed_torque,r.committed_torque_budget,
    r.max_normal_budget_ratio,r.max_commit_budget_ratio,r.max_residual,r.residual_budget,r.max_force,r.force_budget};
  for(double x:q)if(!std::isfinite(x))return false;return true;
}
cudaError_t Add(unsigned np,unsigned npb,const StDivDataGpu& dvd,const unsigned* cell,const unsigned* idp,const double2* xy,const double* z,
 const float4* v,const typecode* code,const double* J,double solid0,double rho0,double rhow,double vol0,float h,float bwen,float G,double dt,
 unsigned mode,bool commit,float3* ace,Result& result){
  result=Result();result.invalid_sorted=result.invalid_native_id=~0u;result.mode=mode;
  if(np!=6805||npb!=1805||!cell||!idp||!xy||!z||!v||!code||!J||!ace||mode>3||(mode&&commit)
    ||!std::isfinite(solid0)||!(solid0>0&&solid0<1)||!std::isfinite(rho0)||!(rho0>0)||!std::isfinite(rhow)||!(rhow>0)
    ||!std::isfinite(vol0)||!(vol0>0)||!std::isfinite(dt)||dt!=.000005||h!=.072f||!std::isfinite(bwen)||!(bwen<0)||G<=0||!std::isfinite(G)
    ||!dvd.beginendcell||dvd.axis!=MGDIV_Z||(dvd.scelldiv!=1&&dvd.scelldiv!=2)
    ||dvd.nc.x<=0||dvd.nc.y<=0||dvd.nc.z<=0||dvd.nc.w!=dvd.nc.x*dvd.nc.y||!dvd.cellfluid)return cudaErrorInvalidValue;
  const Params c={solid0,rho0,rhow,vol0,dt,h,bwen,G,mode};Scratch a;cudaError_t status;Summary host={};
  #define RV_CALL(call) do{status=(call);if(status!=cudaSuccess)return status;}while(0)
  RV_CALL(cudaMalloc((void**)&a.fit,Nodes*sizeof(FitData)));RV_CALL(cudaMalloc((void**)&a.fiterrors,Nodes*sizeof(unsigned)));
  RV_CALL(cudaMalloc((void**)&a.nodes,Nodes*sizeof(NodeResult)));RV_CALL(cudaMalloc((void**)&a.errors,Nodes*sizeof(unsigned)));
  RV_CALL(cudaMalloc((void**)&a.summary,sizeof(Summary)));
  FitKernel<<<(Nodes+Block-1)/Block,Block>>>(np,npb,dvd,cell,idp,xy,z,v,code,J,c,a.fit,a.fiterrors);RV_CALL(cudaGetLastError());
  FitSummary<<<1,1>>>(npb,idp,a.fit,a.fiterrors,c,a.summary);RV_CALL(cudaGetLastError());
  RV_CALL(cudaMemcpy(&host,a.summary,sizeof(Summary),cudaMemcpyDeviceToHost));result=host.result;
  if(result.error_bits)return cudaSuccess;
  ForceKernel<<<(Nodes+Block-1)/Block,Block>>>(np,npb,dvd,cell,idp,xy,z,v,code,J,c,a.fit,a.fiterrors,ace,a.summary,a.nodes,a.errors);RV_CALL(cudaGetLastError());
  ForceSummary<<<1,1>>>(npb,idp,a.nodes,a.errors,a.summary);RV_CALL(cudaGetLastError());
  RV_CALL(cudaMemcpy(&host,a.summary,sizeof(Summary),cudaMemcpyDeviceToHost));result=host.result;
  if(!FiniteResult(result))result.error_bits|=Force;
  if(!result.error_bits){
    const bool valid=fabs(result.work_certificate_error)<=result.work_certificate_budget
      &&fabs(result.torque_certificate_error)<=result.torque_certificate_budget
      &&fabs(result.work+2*result.form)<=result.work_budget&&result.work<=result.work_budget
      &&result.net_force_norm<=result.net_force_budget&&fabs(result.torque)<=result.torque_budget
      &&result.committed_work<=result.committed_work_budget&&result.committed_net_force_norm<=result.committed_net_force_budget
      &&fabs(result.committed_torque)<=result.committed_torque_budget;
    if(!valid)result.error_bits|=Certificate;else result.certificates_passed=true;
  }
  if(mode&&!result.error_bits){
    result.manufactured_passed=result.max_residual<=result.residual_budget&&result.max_force<=result.force_budget;
    if(!result.manufactured_passed)result.error_bits|=Manufactured;
  }
  if(result.error_bits||!commit)return cudaSuccess;
  static_assert(offsetof(NodeResult,ace)==0,"Candidate Ace must be first, no pointer/stride alias");
  RV_CALL(cudaMemcpy2D(ace+npb,sizeof(float3),a.nodes,sizeof(NodeResult),sizeof(float3),Nodes,cudaMemcpyDeviceToDevice));
  result.committed=true;
  #undef RV_CALL
  return cudaSuccess;
}
}
