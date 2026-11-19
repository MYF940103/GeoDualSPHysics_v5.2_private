// Fixed-reference three-dimensional Cryer research integrator. All arrays are ordered by material ID.
#include <cuda_runtime.h>
#include <algorithm>
#include <cmath>
#include <climits>
#include <cstdio>
#include <stdexcept>
#include <string>
#include <vector>
#include <cstring>

struct V { double x,y,z; };
struct Stress { double xx,yy,zz,xy,yz,xz; };
struct Csr { int *row,*col; double *scalar; V *vector; };
struct State { V *u,*v; Stress *s; double *J; };
struct Context {
  int n; double dt,mu,lambda,damping;
  Csr gradient,transpose,opened,closed,av;
  V *x,*traction,*normalTerm,*base,*acc,*avAcc,*pressureAcc;
  double *mass,*invSum,*theta,*pressure,*previous,*guess,*next;
  unsigned char *surface;
  int *bad; // first invalid material slot + 1, update number, phase
  State now,half,end;
};
static Context ctx={};
static int completed=0;
static bool started=false,failed=false;
static char errstr[1024]={};
static std::vector<void*> allocations;
#define API extern "C" __declspec(dllexport)
static void ck(cudaError_t result){if(result!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(result));}
template<class T> static void allocate(T*& dest,size_t n){
  ck(cudaMalloc((void**)&dest,n*sizeof(T))); allocations.push_back(dest);ck(cudaMemset(dest,0,n*sizeof(T)));
}
template<class T> static void upload(T*& dest,const void* src,size_t n){
  allocate(dest,n);ck(cudaMemcpy(dest,src,n*sizeof(T),cudaMemcpyHostToDevice));
}
static void allocState(State& t,int n){allocate(t.u,n);allocate(t.v,n);allocate(t.s,n);allocate(t.J,n);}
#define BEGIN_API try{
#define END_API ck(cudaGetLastError()); return 0;}catch(const std::exception& e){std::snprintf(errstr,sizeof(errstr),"%s",e.what());return 1;}
API const char* errorText(){return errstr;}
API int currentStep(){return started&&!failed?completed:-1;}
API int init(int n,double dt,double mu,double lambda,double damping){BEGIN_API
  if(ctx.n||n!=37173||!(dt>0.)||!(mu>0.)||!(lambda>=0.)||!(damping>=0.))
    throw std::runtime_error("Invalid setup, material count or duplicate context");
  ctx.n=n;ctx.dt=dt;ctx.mu=mu;ctx.lambda=lambda;ctx.damping=damping;completed=0;started=failed=false;
  allocState(ctx.now,n);allocState(ctx.half,n);allocState(ctx.end,n);
  allocate(ctx.pressure,n);allocate(ctx.previous,n);allocate(ctx.guess,n);allocate(ctx.next,n);
  allocate(ctx.base,n);allocate(ctx.acc,n);allocate(ctx.avAcc,n);allocate(ctx.pressureAcc,n);
  allocate(ctx.theta,n);allocate(ctx.bad,3);END_API}
API int setCsr(int key,int nz,const int* row,const int* col,const double* values){BEGIN_API
  if(!ctx.n||started||key<0||key>4||nz<=0||!row||!col||!values||row[0]!=0||row[ctx.n]!=nz)
    throw std::runtime_error("Invalid CSR");
  for(int i=0;i<ctx.n;i++)if(row[i]<0||row[i]>row[i+1])throw std::runtime_error("Invalid CSR offsets");
  for(int k=0;k<nz;k++)if(col[k]<0||col[k]>=ctx.n)throw std::runtime_error("Invalid CSR column");
  Csr* m[]={&ctx.gradient,&ctx.transpose,&ctx.opened,&ctx.closed,&ctx.av};Csr& a=*m[key];
  if(a.row)throw std::runtime_error("Duplicate CSR");
  upload(a.row,row,ctx.n+1);upload(a.col,col,nz);
  if(key<2)upload(a.vector,values,nz);else upload(a.scalar,values,nz);
  END_API}
API int setGeometry(const double* x,const double* mass,const double* traction,const double* invSum,
                    const double* normalTerm,const unsigned char* surface){BEGIN_API
  const int n=ctx.n;if(n<=0||started||ctx.x||!x||!mass||!traction||!invSum||!normalTerm||!surface)
    throw std::runtime_error("Invalid or duplicate geometry");
  for(int i=0;i<n;i++)if(!(mass[i]>0.)||!(invSum[i]>0.)||surface[i]>1)
    throw std::runtime_error("Invalid nodal inertia, pressure denominator or surface flag");
  upload(ctx.x,x,n);upload(ctx.mass,mass,n);upload(ctx.traction,traction,n);upload(ctx.invSum,invSum,n);
  upload(ctx.normalTerm,normalTerm,n);upload(ctx.surface,surface,n);END_API}
__device__ inline V plus(V a,V b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
__device__ inline V minusV(V a,V b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
__device__ inline V scale(V a,double k){return {k*a.x,k*a.y,k*a.z};}
__device__ inline double dot(V a,V b){return a.x*b.x+a.y*b.y+a.z*b.z;}
__device__ inline V publicV(V a){return {float(a.x),float(a.y),float(a.z)};}
__device__ inline bool valid(V a){return isfinite(a.x)&&isfinite(a.y)&&isfinite(a.z);}
__device__ inline V contract(Stress s,V g){
  return {s.xx*g.x+s.xy*g.y+s.xz*g.z,s.xy*g.x+s.yy*g.y+s.yz*g.z,s.xz*g.x+s.yz*g.y+s.zz*g.z};
}
__global__ void initJ(State a,int n){int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)a.J[i]=1.;}
__global__ void clampCurrentPressure(Context c){
  int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<c.n&&c.surface[i])c.pressure[i]=0.;
}
__device__ inline void recordFault(Context c,int i,int update,int phase){
  if(atomicCAS(c.bad,0,i+1)==0){c.bad[1]=update;c.bad[2]=phase;}
}
__global__ void predictPressure(Context c,bool drain){
  int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=c.n)return;
  bool active=drain&&c.surface[i];
  c.guess[i]=active?0.:float(c.pressure[i]+.5*(c.pressure[i]-c.previous[i]));
}
__global__ void viscosity(Context c,const V* velocity){
  const int lane=threadIdx.x%32,i=(blockIdx.x*blockDim.x+threadIdx.x)/32;
  if(i>=c.n)return;
  V a={};V x=c.x[i],v=velocity[i];
  for(int k=c.av.row[i]+lane;k<c.av.row[i+1];k+=32){
    int j=c.av.col[k];V dx=minusV(x,c.x[j]);double compression=dot(dx,minusV(v,velocity[j]));
    if(compression<0.)a=plus(a,scale(dx,c.av.scalar[k]*compression));
  }
  for(int offset=16;offset>0;offset/=2){
    a.x+=__shfl_down_sync(0xffffffff,a.x,offset);a.y+=__shfl_down_sync(0xffffffff,a.y,offset);
    a.z+=__shfl_down_sync(0xffffffff,a.z,offset);
  }
  if(!lane)c.avAcc[i]=a;
}
__global__ void fixedForce(Context c,State a,double load){
  int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=c.n)return;V f=scale(c.traction[i],load);
  for(int k=c.transpose.row[i];k<c.transpose.row[i+1];k++)
    f=minusV(f,contract(a.s[c.transpose.col[k]],c.transpose.vector[k]));
  c.base[i]=plus(scale(f,1./c.mass[i]),minusV(c.avAcc[i],scale(a.v[i],c.damping)));
}
__global__ void totalForce(Context c,const double* p){
  int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=c.n)return;V f={};
  for(int k=c.transpose.row[i];k<c.transpose.row[i+1];k++)
    f=plus(f,scale(c.transpose.vector[k],p[c.transpose.col[k]]));
  c.pressureAcc[i]=scale(f,1./c.mass[i]);
  c.acc[i]=plus(c.base[i],c.pressureAcc[i]);
}
__global__ void mechanicalUpdate(Context c,State stage,State dest,bool correct,int update){
  int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=c.n)return;
  V gx={},gy={},gz={};
  for(int k=c.gradient.row[i];k<c.gradient.row[i+1];k++){
    const V g=c.gradient.vector[k],v=stage.v[c.gradient.col[k]];
    gx=plus(gx,scale(v,g.x));gy=plus(gy,scale(v,g.y));gz=plus(gz,scale(v,g.z));
  }
  const double theta=gx.x+gy.y+gz.z,ds=correct?c.dt:c.dt*.5;
  const double l=c.lambda*theta;
  const V vn=c.now.v[i],nextV=publicV(plus(vn,scale(publicV(c.acc[i]),ds)));
  dest.v[i]=nextV;
  dest.u[i]=plus(c.now.u[i],correct?scale(plus(vn,nextV),c.dt*.5):scale(vn,ds));
  dest.J[i]=c.now.J[i]+ds*stage.J[i]*theta;
  Stress s=c.now.s[i];
  // Small-strain elastic law with public stress rate rounded to float, stress state retained in double.
  s.xx+=ds*float(2*c.mu*gx.x+l); s.yy+=ds*float(2*c.mu*gy.y+l); s.zz+=ds*float(2*c.mu*gz.z+l);
  s.xy+=ds*float(c.mu*(gx.y+gy.x));s.yz+=ds*float(c.mu*(gy.z+gz.y));s.xz+=ds*float(c.mu*(gx.z+gz.x));
  dest.s[i]=s;
  const V pos=plus(c.x[i],dest.u[i]); const double n=1.-(1.-double(.3f))/dest.J[i];
  if(!valid(nextV)||!valid(pos)||!isfinite(dest.J[i])||!(n>0.&&n<1.)||dot(pos,pos)>=.0525*.0525
    ||!isfinite(s.xx+s.yy+s.zz+s.xy+s.yz+s.xz))recordFault(c,i,update,correct?2:1);
}
__global__ void divVelocity(Context c,State a){
  int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=c.n)return;double theta=0;
  for(int k=c.gradient.row[i];k<c.gradient.row[i+1];k++)theta+=dot(c.gradient.vector[k],a.v[c.gradient.col[k]]);
  c.theta[i]=theta;
}
__global__ void pressureRound(Context c,bool drain,const double* p,double* target,int update,int phase){
  const int lane=threadIdx.x%32,i=(blockIdx.x*blockDim.x+threadIdx.x)/32;if(i>=c.n)return;
  if(drain&&c.surface[i]){if(!lane)target[i]=0.;return;}
  Csr E=drain?c.opened:c.closed;double propagation=0.,da=0.;
  for(int k=E.row[i]+lane;k<E.row[i+1];k+=32)propagation+=E.scalar[k]*p[E.col[k]];
  for(int k=c.gradient.row[i]+lane;k<c.gradient.row[i+1];k+=32)
    da+=dot(c.gradient.vector[k],publicV(c.acc[c.gradient.col[k]]));
  for(int offset=16;offset>0;offset/=2){
    propagation+=__shfl_down_sync(0xffffffff,propagation,offset);da+=__shfl_down_sync(0xffffffff,da,offset);
  }
  if(!lane){
    if(!drain)da+=dot(c.normalTerm[i],publicV(c.acc[i]));
    const double gamma=1000.*9.80665;
    target[i]=float(propagation+c.invSum[i]*(1000.*da-gamma/double(1.e-5f)*c.theta[i]));
    if(!isfinite(target[i]))recordFault(c,i,update,phase);
  }
}
__global__ void commit(Context c){
  int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<c.n){c.previous[i]=c.pressure[i];c.pressure[i]=c.guess[i];}
}
static int grid(){return (ctx.n+127)/128;}
static int warps(){return (ctx.n+3)/4;}
static void base(State s,double q){
  viscosity<<<warps(),128>>>(ctx,s.v);fixedForce<<<grid(),128>>>(ctx,s,q);
}
API int start(){BEGIN_API
  if(started||!ctx.x||!ctx.gradient.row||!ctx.transpose.row||!ctx.opened.row||!ctx.closed.row||!ctx.av.row)
    throw std::runtime_error("Duplicate start or incomplete operators");
  initJ<<<grid(),128>>>(ctx.now,ctx.n);ck(cudaDeviceSynchronize());started=true;END_API}
API int advance(int count){BEGIN_API
  if(!started||failed||count<1||count>INT_MAX-completed)throw std::runtime_error("Invalid state or update count");
  for(int it=0;it<count;it++){
    bool drain=completed>=4096;
    double q=10000.*std::min(1.,double(completed)/2048.);
    // Part at completed=4096 is pre-open. On the NEXT update the real FS is
    // clamped before every force, including base(now). Keep the clamped p_n in history.
    if(drain)clampCurrentPressure<<<grid(),128>>>(ctx);
    predictPressure<<<grid(),128>>>(ctx,drain);
    base(ctx.now,q);totalForce<<<grid(),128>>>(ctx,ctx.pressure);
    mechanicalUpdate<<<grid(),128>>>(ctx,ctx.now,ctx.half,false,completed+1);
    base(ctx.half,q);totalForce<<<grid(),128>>>(ctx,ctx.guess);
    mechanicalUpdate<<<grid(),128>>>(ctx,ctx.half,ctx.end,true,completed+1);
    base(ctx.end,q);divVelocity<<<grid(),128>>>(ctx,ctx.end);
    for(int round=0;round<3;round++){
      totalForce<<<grid(),128>>>(ctx,ctx.guess);pressureRound<<<warps(),128>>>(ctx,drain,ctx.guess,ctx.next,completed+1,3+round);
      std::swap(ctx.guess,ctx.next);
    }
    commit<<<grid(),128>>>(ctx);std::swap(ctx.end,ctx.now);completed++;
  }
  int bad[3]={};ck(cudaMemcpy(bad,ctx.bad,sizeof(bad),cudaMemcpyDeviceToHost));
  if(bad[0]){
    failed=true;throw std::runtime_error("First invalid update "+std::to_string(bad[1])+
      ", phase "+std::to_string(bad[2])+" (1 predictor, 2 corrector, 3/4/5 pressure), slot "+
      std::to_string(bad[0]-1)+", native ID "+std::to_string(bad[0]+7));}
  END_API}
API int readState(double* p,double* u,double* v,double* stress,double* J){BEGIN_API
  if(!started||failed)throw std::runtime_error("No readable valid completed state");
  const size_t n=ctx.n;ck(cudaMemcpy(p,ctx.pressure,n*sizeof(double),cudaMemcpyDeviceToHost));
  ck(cudaMemcpy(u,ctx.now.u,n*sizeof(V),cudaMemcpyDeviceToHost));ck(cudaMemcpy(v,ctx.now.v,n*sizeof(V),cudaMemcpyDeviceToHost));
  ck(cudaMemcpy(stress,ctx.now.s,n*sizeof(Stress),cudaMemcpyDeviceToHost));ck(cudaMemcpy(J,ctx.now.J,n*sizeof(double),cudaMemcpyDeviceToHost));
  END_API}
API int readPrevious(double* previous){BEGIN_API
  if(!started||failed||!previous)throw std::runtime_error("No readable valid pressure history");
  ck(cudaMemcpy(previous,ctx.previous,ctx.n*sizeof(double),cudaMemcpyDeviceToHost));END_API}
API int restore(int step,const double* p,const double* previous,const double* u,const double* v,
                const double* stress,const double* J){BEGIN_API
  if(!started||step<0||!p||!previous||!u||!v||!stress||!J)throw std::runtime_error("Invalid restore arguments");
  const int n=ctx.n;std::vector<unsigned char> fs(n);std::vector<V> x(n);
  ck(cudaMemcpy(fs.data(),ctx.surface,n*sizeof(unsigned char),cudaMemcpyDeviceToHost));
  ck(cudaMemcpy(x.data(),ctx.x,n*sizeof(V),cudaMemcpyDeviceToHost));
  for(int i=0;i<n;i++){
    if(!std::isfinite(p[i])||!std::isfinite(previous[i])||!std::isfinite(J[i])||
       !(J[i]>1.-double(.3f))||!(1.-(1.-double(.3f))/J[i]<1.))
      throw std::runtime_error("Invalid pressure or J in restart at slot "+std::to_string(i));
    if(step>4096&&fs[i]&&(p[i]!=0.||previous[i]!=0.))throw std::runtime_error("Released surface pressure history differs");
    for(int k=0;k<3;k++)if(!std::isfinite(u[3*i+k])||!std::isfinite(v[3*i+k]))throw std::runtime_error("Invalid restored kinematics");
    for(int k=0;k<6;k++)if(!std::isfinite(stress[6*i+k]))throw std::runtime_error("Invalid restored stress");
    double rx=x[i].x+u[3*i],ry=x[i].y+u[3*i+1],rz=x[i].z+u[3*i+2];
    if(!(rx*rx+ry*ry+rz*rz<.0525*.0525))throw std::runtime_error("Restored sphere envelope exceeded");
  }
  // Mark the old state unavailable if a transfer fails partway through the restore.
  failed=true;
  ck(cudaMemcpy(ctx.pressure,p,n*sizeof(double),cudaMemcpyHostToDevice));
  ck(cudaMemcpy(ctx.previous,previous,n*sizeof(double),cudaMemcpyHostToDevice));
  ck(cudaMemcpy(ctx.now.u,u,n*sizeof(V),cudaMemcpyHostToDevice));ck(cudaMemcpy(ctx.now.v,v,n*sizeof(V),cudaMemcpyHostToDevice));
  ck(cudaMemcpy(ctx.now.s,stress,n*sizeof(Stress),cudaMemcpyHostToDevice));ck(cudaMemcpy(ctx.now.J,J,n*sizeof(double),cudaMemcpyHostToDevice));
  ck(cudaMemset(ctx.bad,0,3*sizeof(int)));ck(cudaDeviceSynchronize());completed=step;failed=false;END_API}
API int forceFixture(const double* v,const double* s,const double* p,double q,double* av,double* pa,double* accel){BEGIN_API
  const size_t n=ctx.n;ck(cudaMemcpy(ctx.half.v,v,n*sizeof(V),cudaMemcpyHostToDevice));
  ck(cudaMemcpy(ctx.half.s,s,n*sizeof(Stress),cudaMemcpyHostToDevice));
  ck(cudaMemcpy(ctx.next,p,n*sizeof(double),cudaMemcpyHostToDevice));base(ctx.half,q);totalForce<<<grid(),128>>>(ctx,ctx.next);
  ck(cudaMemcpy(av,ctx.avAcc,n*sizeof(V),cudaMemcpyDeviceToHost));ck(cudaMemcpy(pa,ctx.pressureAcc,n*sizeof(V),cudaMemcpyDeviceToHost));
  ck(cudaMemcpy(accel,ctx.acc,n*sizeof(V),cudaMemcpyDeviceToHost));END_API}
API int pressureFixture(const double* p,const double* a,const double* theta,int drain,double* out){BEGIN_API
  const size_t n=ctx.n;ck(cudaMemcpy(ctx.next,p,n*sizeof(double),cudaMemcpyHostToDevice));ck(cudaMemcpy(ctx.acc,a,n*sizeof(V),cudaMemcpyHostToDevice));
  ck(cudaMemcpy(ctx.theta,theta,n*sizeof(double),cudaMemcpyHostToDevice));pressureRound<<<warps(),128>>>(ctx,drain!=0,ctx.next,ctx.guess,completed,6);
  ck(cudaMemcpy(out,ctx.guess,n*sizeof(double),cudaMemcpyDeviceToHost));END_API}
API int release(){BEGIN_API
  ck(cudaDeviceSynchronize());for(auto ptr:allocations)ck(cudaFree(ptr));allocations.clear();ctx=Context{};completed=0;started=failed=false;END_API}
