// Private output-only module. The original JSphGpu_ker.cu object remains linked unchanged.
#include "JSphGpu_ker.h"
#include "C08StorageTrace.h"
#include <cfloat>
#include <cmath>
#include <cuda_runtime.h>
#ifndef C08_STORAGE_TRACE
#error This private observer requires C08_STORAGE_TRACE explicitly.
#endif
namespace cusph{
namespace{
  const unsigned Count=5000,First=2060,BaseStep=2000000,LastStep=2180000;
  struct Record{
    C08StorageRow out;
    double last_p,last_j,last_w;
    double pn,jn,jh,theta,rate,comp,darcy,time,dt;
    double cap_p,cap_j,cap_w;
    unsigned pending,pending_step,cap_pending,cap_release;
  };
  __device__ Record records[Count];
  __device__ C08StorageRow exported[Count];
  __device__ unsigned global_errors;
  __device__ void Error(unsigned bit){atomicOr(&global_errors,bit);}
  __device__ Record* Find(unsigned p,unsigned np,unsigned npb,const unsigned* idp,const typecode* code){
    if(p>=np||p<npb)return NULL;
    if(!CODE_IsNormal(code[p])||!CODE_IsFluid(code[p])){Error(1u);return NULL;}
    const unsigned id=idp[p];if(id<First||id-First>=Count){Error(2u);return NULL;}
    return records+(id-First);
  }
  __device__ double Weight(double j,double v0,double solid0,double kw){return (1.-solid0/j)*(v0*j)/kw;}
  __device__ bool Same(double a,double b){return __double_as_longlong(a)==__double_as_longlong(b);}
  __device__ void Add(Record& r,double& total,double value){
    if(!isfinite(value)){r.out.errors|=1u;return;}
    total+=value;r.out.abs_increments+=fabs(value);
  }
  __global__ void Zero(){const unsigned s=blockIdx.x*blockDim.x+threadIdx.x;if(s<Count){Record r={};r.out.native_id=First+s;records[s]=r;}if(!s)global_errors=0;}
  __global__ void Init(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,const double* j,const float* p,double v0,double solid0,double kw,unsigned step,double time){
    const unsigned q=blockIdx.x*blockDim.x+threadIdx.x;Record* target=Find(q,np,npb,idp,code);if(!target)return;Record& r=*target;
    if(atomicAdd(&r.out.inits,1u)!=0){r.out.errors|=2u;return;}
    const double w=Weight(j[q],v0,solid0,kw);
    if(step!=BaseStep||!isfinite(time)||!isfinite(j[q])||j[q]<=solid0||!isfinite(p[q])||!isfinite(w)||w<=0){r.out.errors|=4u;return;}
    r.last_p=p[q];r.last_j=j[q];r.last_w=w;r.out.last_step=step;r.out.last_time=time;r.out.initial_S=r.out.last_S=w*double(p[q]);
  }
  __global__ void Rhs(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,const double* jn,const double* jh,const float* pn,const double* theta,const float* rate,double v0,double solid0,double kw,unsigned step,double time,double dt){
    const unsigned q=blockIdx.x*blockDim.x+threadIdx.x;Record* target=Find(q,np,npb,idp,code);if(!target)return;Record& r=*target;
    if(r.out.inits!=1||r.pending||r.cap_pending||step!=r.out.last_step||step>=LastStep||!Same(time,r.out.last_time)||dt!=.000005||!Same(double(pn[q]),r.last_p)||!Same(jn[q],r.last_j)){r.out.errors|=8u;return;}
    const double n=1.-solid0/jh[q],comp=kw/n*(-theta[q]),darcy=double(rate[q])-comp;
    if(!isfinite(jn[q])||!isfinite(jh[q])||jn[q]<=solid0||jh[q]<=solid0||!isfinite(n)||n<=0||n>=1||!isfinite(theta[q])||!isfinite(rate[q])||!isfinite(comp)||!isfinite(darcy)||!Same(Weight(jn[q],v0,solid0,kw),r.last_w)){r.out.errors|=16u;return;}
    r.pn=pn[q];r.jn=jn[q];r.jh=jh[q];r.theta=theta[q];r.rate=rate[q];r.comp=comp;r.darcy=darcy;r.time=time;r.dt=dt;r.pending=1;r.pending_step=step;r.out.rhs_h++;
  }
  __global__ void Update(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,const float* pn,const double* jnew,const float* praw,double v0,double solid0,double kw,unsigned step,double time,double dt){
    const unsigned q=blockIdx.x*blockDim.x+threadIdx.x;Record* target=Find(q,np,npb,idp,code);if(!target)return;Record& r=*target;
    if(r.out.inits!=1||r.pending!=1||r.cap_pending||step!=r.pending_step||step!=r.out.last_step||!Same(time,r.time)||!Same(dt,r.dt)||!Same(double(pn[q]),r.pn)||!Same(r.last_p,r.pn)||!Same(r.last_j,r.jn)){r.out.errors|=32u;return;}
    const double wn=Weight(r.jn,v0,solid0,kw),wnew=Weight(jnew[q],v0,solid0,kw),pr=praw[q],dp=pr-r.pn;
    const double c=wn*dt*r.comp,d=wn*dt*r.darcy,split=wn*dt*(r.rate-(r.comp+r.darcy)),write=wn*(dp-dt*r.rate),jw=pr*(wnew-wn),actual=wn*dp;
    if(!isfinite(jnew[q])||jnew[q]<=solid0||!isfinite(pr)||!isfinite(wnew)||wnew<=0){r.out.errors|=64u;return;}
    Add(r,r.out.compression,c);Add(r,r.out.Darcy_remainder,d);Add(r,r.out.source_split_roundoff,split);Add(r,r.out.pressure_commit_roundoff,write);Add(r,r.out.weight_change,jw);r.out.weighted_pressure_delta+=actual;
    // Bound only: the original double pre-cast rate is deliberately not observed. FLT_MIN covers possible FTZ/subnormal conversion.
    r.out.rate_quantization_bound+=fabs(wn*dt)*(double(FLT_EPSILON)*fabs(r.rate)+double(FLT_MIN));
    const double u=.5*DBL_EPSILON,g=128.*u/(1.-128.*u);
    r.out.local_budget_sum+=g*(fabs(wn)*(fabs(pr)+fabs(r.pn))+fabs(pr)*(fabs(wnew)+fabs(wn))+fabs(c)+fabs(d)+fabs(split)+fabs(write)+fabs(jw)+fabs(wnew*pr)+fabs(r.out.last_S));
    r.last_p=pr;r.last_j=jnew[q];r.last_w=wnew;r.out.last_S=wnew*pr;r.out.last_time=time+dt;r.out.last_step=step+1;r.out.sum_dt+=dt;r.out.updates++;r.pending=0;
  }
  __global__ void CapBefore(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,const double* j,const float* p,unsigned step,double time,bool release_phase){
    const unsigned q=blockIdx.x*blockDim.x+threadIdx.x;Record* target=Find(q,np,npb,idp,code);if(!target)return;Record& r=*target;
    if(r.out.inits!=1||r.pending||r.cap_pending||!Same(double(p[q]),r.last_p)||!Same(j[q],r.last_j)||!isfinite(time)||(release_phase&&(step!=BaseStep||r.out.updates))){r.out.errors|=128u;return;}
    r.cap_p=p[q];r.cap_j=j[q];r.cap_w=r.last_w;r.cap_pending=1;r.cap_release=(release_phase?1u:0u);r.out.cap_calls++;if(release_phase)r.out.release_cap_calls++;
  }
  __global__ void CapAfter(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,const double* j,const float* p,const unsigned* fs,double v0,double solid0,double kw){
    const unsigned q=blockIdx.x*blockDim.x+threadIdx.x;Record* target=Find(q,np,npb,idp,code);if(!target)return;Record& r=*target;
    const double after=p[q],w=Weight(j[q],v0,solid0,kw);
    if(r.out.inits!=1||r.cap_pending!=1||r.pending||!Same(j[q],r.cap_j)||!Same(w,r.cap_w)||!isfinite(after)){r.out.errors|=256u;return;}
    const double change=w*(after-r.cap_p);
    if(after!=r.cap_p){r.out.cap_changes++;if(r.cap_release)r.out.release_cap_changes++;if(!(r.cap_p>0&&after==0&&(fs[q]==2||fs[q]==3)))r.out.errors|=512u;}
    Add(r,r.out.cap_change,change);const double u=.5*DBL_EPSILON,g=64.*u/(1.-64.*u);
    r.out.local_budget_sum+=g*(fabs(w)*(fabs(after)+fabs(r.cap_p))+fabs(change)+fabs(w*after)+fabs(r.out.last_S));
    r.last_p=after;r.out.last_S=w*after;r.cap_pending=0;
  }
  __global__ void Export(){const unsigned s=blockIdx.x*blockDim.x+threadIdx.x;if(s<Count){Record& r=records[s];if(r.out.inits!=1||r.pending||r.cap_pending||r.out.rhs_h!=r.out.updates)r.out.errors|=1024u;exported[s]=r.out;}}
  static dim3 Grid(unsigned n){return dim3((n+127)/128);}
  static bool Launched(){return cudaGetLastError()==cudaSuccess;}
}
bool C08StorageInit(unsigned n,unsigned b,const unsigned* ids,const typecode* code,const double* j,const float* p,double v,double s,double k,unsigned step,double t){Zero<<<Grid(Count),128>>>();if(!Launched())return false;Init<<<Grid(n),128>>>(n,b,ids,code,j,p,v,s,k,step,t);return Launched();}
bool C08StorageRhs(unsigned n,unsigned b,const unsigned* ids,const typecode* code,const double* jn,const double* jh,const float* pn,const double* theta,const float* rate,double v,double s,double k,unsigned step,double t,double dt){Rhs<<<Grid(n),128>>>(n,b,ids,code,jn,jh,pn,theta,rate,v,s,k,step,t,dt);return Launched();}
bool C08StorageUpdate(unsigned n,unsigned b,const unsigned* ids,const typecode* code,const float* pn,const double* j,const float* p,double v,double s,double k,unsigned step,double t,double dt){Update<<<Grid(n),128>>>(n,b,ids,code,pn,j,p,v,s,k,step,t,dt);return Launched();}
bool C08StorageCapBefore(unsigned n,unsigned b,const unsigned* ids,const typecode* code,const double* j,const float* p,unsigned step,double t,bool release_phase){CapBefore<<<Grid(n),128>>>(n,b,ids,code,j,p,step,t,release_phase);return Launched();}
bool C08StorageCapAfter(unsigned n,unsigned b,const unsigned* ids,const typecode* code,const double* j,const float* p,const unsigned* fs,double v,double s,double k){CapAfter<<<Grid(n),128>>>(n,b,ids,code,j,p,fs,v,s,k);return Launched();}
bool C08StorageRead(C08StorageRow* rows,unsigned* errors){Export<<<Grid(Count),128>>>();return Launched()&&cudaMemcpyFromSymbol(rows,exported,sizeof(C08StorageRow)*Count)==cudaSuccess&&cudaMemcpyFromSymbol(errors,global_errors,sizeof(unsigned))==cudaSuccess;}
}
