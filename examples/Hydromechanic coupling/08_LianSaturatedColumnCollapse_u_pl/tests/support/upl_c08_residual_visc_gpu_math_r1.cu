// Author-only, standalone C08 2-D matched residual-viscosity math component.
// No main, native/CSV reader, solver hook, CTE, wall, periodicity or history.
// The sole host entry point and all array layouts are documented below and in
// tests/notes/upl_c08_residual_visc_gpu_math_r1.md. No production file is included.
#include <cuda_runtime.h>
#include <float.h>
#include <math.h>
#include <stddef.h>

namespace c08_residual_visc_gpu_math_r1 {
enum ErrorBits {
  InvalidInput=1u, CoincidentNodes=2u, InvalidWeight=4u,
  RankFailure=8u, NonfiniteFit=16u, InvalidNeighborFit=32u,
  NonfiniteForce=64u
};
struct Cubic { float h,c1,d1,c2; double support2; };

// FunSphKernel_iker.h::GetKernelCubic_Fac expression/order, without CTE.
// rr2 is the float cast of a double-position squared distance. This candidate
// deliberately uses the CPU candidate's strict double rr2 < (2*h_float)^2.
__device__ static float CubicFac(const Cubic c,const float rr2){
  const float rad=sqrtf(rr2),qq=rad/c.h;
  if(rad>c.h){
    const float wqq1=2.0f-qq,wqq2=wqq1*wqq1;
    return(c.c2*wqq2/rad);
  }
  const float wqq2=qq*qq;
  return((c.c1*qq+c.d1*wqq2)/rad);
}
__device__ static bool Valid(const double2 x,const double2 v,
  const double V,const double rho,const double2 a){
  return(isfinite(x.x)&&isfinite(x.y)&&isfinite(v.x)&&isfinite(v.y)
    &&isfinite(V)&&V>0&&isfinite(rho)&&rho>0
    &&isfinite(a.x)&&isfinite(a.y));
}
__device__ static void BadForce(const unsigned i,double2* da,float2* added){
  da[i]=make_double2(NAN,NAN);added[i]=make_float2(NAN,NAN);
}

// L9 is row-major Cartesian (x,y,z), with the four x/z entries at 0,2,6,8.
// Every receiver uses every other supplied soil node; there is no neighbor cap.
__global__ static void Fit(const unsigned n,const Cubic c,const double G,
  const double alpha,const double2* pos,const double2* vel,const double* V,
  const double* rho,const double2* base,double* L9,double* lambda,
  unsigned* fiterrors){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=n)return;
  double* L=L9+size_t(i)*9;for(unsigned k=0;k<9;k++)L[k]=NAN;
  lambda[i]=NAN;unsigned error=0;
  if(!Valid(pos[i],vel[i],V[i],rho[i],base[i])){
    fiterrors[i]=InvalidInput;return;
  }
  const double taui=double(c.h)/sqrt(G/rho[i]);
  double mxx=0,mxz=0,mzz=0,nxx=0,nxz=0,nzx=0,nzz=0,degree=0;
  for(unsigned j=0;j<n;j++){
    if(j==i)continue;
    if(!Valid(pos[j],vel[j],V[j],rho[j],base[j])){error|=InvalidInput;continue;}
    const double dx=pos[i].x-pos[j].x,dz=pos[i].y-pos[j].y;
    const double rr2=dx*dx+dz*dz;
    if(!isfinite(rr2)){error|=InvalidInput;continue;}
    if(rr2==0){error|=CoincidentNodes;continue;}
    if(rr2>=c.support2)continue;
    const double w=-double(CubicFac(c,float(rr2)));
    if(w==0)continue;
    if(!(w>0)||!isfinite(w)){error|=InvalidWeight;continue;}
    const double eta0=G*.5*(taui+double(c.h)/sqrt(G/rho[j]));
    const double b=eta0*V[j]*w;
    const double dvx=vel[i].x-vel[j].x,dvz=vel[i].y-vel[j].y;
    mxx+=b*dx*dx;mxz+=b*dx*dz;mzz+=b*dz*dz;
    nxx+=b*dvx*dx;nxz+=b*dvx*dz;
    nzx+=b*dvz*dx;nzz+=b*dvz*dz;
    // Same unordered-pair beta0 multiplication order as the CPU component.
    const unsigned lo=(i<j?i:j),hi=(i<j?j:i);
    degree+=eta0*V[lo]*V[hi]*w;
  }
  const double scale=fmax(fmax(fabs(mxx),fabs(mxz)),fabs(mzz));
  if(!(scale>0)||!isfinite(scale)){error|=RankFailure;}
  if(error){fiterrors[i]=error;return;}
  const double a=mxx/scale,b=mxz/scale,d=mzz/scale,det=a*d-b*b;
  // Same scaled, unregularized 2x2 rank predicate as the CPU candidate.
  if(!(a>0&&d>0&&det>128.*DBL_EPSILON*(a*d+b*b))){
    fiterrors[i]=RankFailure;return;
  }
  const double den=scale*det;
  const double lxx=(nxx*d-nxz*b)/den,lxz=(-nxx*b+nxz*a)/den;
  const double lzx=(nzx*d-nzz*b)/den,lzz=(-nzx*b+nzz*a)/den;
  const double bound=2.*alpha*(degree/(rho[i]*V[i]));
  if(!isfinite(lxx)||!isfinite(lxz)||!isfinite(lzx)||!isfinite(lzz)
    ||!isfinite(bound)||bound<0){fiterrors[i]=NonfiniteFit;return;}
  for(unsigned k=0;k<9;k++)L[k]=0;
  L[0]=lxx;L[2]=lxz;L[6]=lzx;L[8]=lzz;
  lambda[i]=bound;fiterrors[i]=0;
}

// Independent gather: no atomics and no cross-thread read/write of error flags.
// fiterrors is immutable here. Neither positions nor any input field is written.
__global__ static void Force(const unsigned n,const Cubic c,const double G,
  const double alpha,const double2* pos,const double2* vel,const double* V,
  const double* rho,const double2* base,const double* L9,
  const unsigned* fiterrors,double2* da,float2* added,unsigned* errors){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=n)return;
  unsigned error=fiterrors[i];if(error){errors[i]=error;BadForce(i,da,added);return;}
  const double* Li=L9+size_t(i)*9;
  const double taui=double(c.h)/sqrt(G/rho[i]);double fx=0,fz=0;
  for(unsigned j=0;j<n;j++){
    if(j==i)continue;
    const double dx=pos[i].x-pos[j].x,dz=pos[i].y-pos[j].y;
    const double rr2=dx*dx+dz*dz;
    if(!isfinite(rr2)){error|=InvalidInput;continue;}
    if(rr2==0){error|=CoincidentNodes;continue;}
    if(rr2>=c.support2)continue;
    const double w=-double(CubicFac(c,float(rr2)));if(w==0)continue;
    if(!(w>0)||!isfinite(w)){error|=InvalidWeight;continue;}
    if(fiterrors[j]){error|=InvalidNeighborFit;continue;}
    const double eta0=G*.5*(taui+double(c.h)/sqrt(G/rho[j]));
    const unsigned lo=(i<j?i:j),hi=(i<j?j:i);
    const double beta0=eta0*V[lo]*V[hi]*w;
    const double* Lj=L9+size_t(j)*9;
    const double dvx=vel[i].x-vel[j].x,dvz=vel[i].y-vel[j].y;
    const double rix=dvx-(Li[0]*dx+Li[2]*dz),riz=dvz-(Li[6]*dx+Li[8]*dz);
    const double rjx=dvx-(Lj[0]*dx+Lj[2]*dz),rjz=dvz-(Lj[6]*dx+Lj[8]*dz);
    const double f=-.5*alpha*beta0;
    fx+=(rix+rjx)*f;fz+=(riz+rjz)*f;
  }
  const double ax=fx/(rho[i]*V[i]),az=fz/(rho[i]*V[i]);
  // One per-node double add and float cast, rather than per-pair float commits.
  // alpha==0 copies the promoted baseline directly, preserving signed zero.
  const float outx=(alpha==0?float(base[i].x):float(base[i].x+ax));
  const float outz=(alpha==0?float(base[i].y):float(base[i].y+az));
  if(!isfinite(ax)||!isfinite(az)||!isfinite(outx)||!isfinite(outz))error|=NonfiniteForce;
  errors[i]=error;if(error){BadForce(i,da,added);return;}
  da[i]=make_double2(ax,az);added[i]=make_float2(outx,outz);
}

struct DeviceArrays {
  double2 *pos=0,*vel=0,*base=0,*da=0;double *V=0,*rho=0,*L9=0,*lambda=0;
  float2* added=0;unsigned *fiterrors=0,*errors=0;
  ~DeviceArrays(){
    cudaFree(errors);cudaFree(fiterrors);cudaFree(added);cudaFree(lambda);
    cudaFree(L9);cudaFree(da);cudaFree(rho);cudaFree(V);
    cudaFree(base);cudaFree(vel);cudaFree(pos);
  }
};
template<class T> static cudaError_t Allocate(T*& p,const size_t n){
  return(cudaMalloc(reinterpret_cast<void**>(&p),n*sizeof(T)));
}
template<class T> static cudaError_t Upload(T* p,const T* h,const size_t n){
  return(cudaMemcpy(p,h,n*sizeof(T),cudaMemcpyHostToDevice));
}
template<class T> static cudaError_t Download(T* h,const T* p,const size_t n){
  return(cudaMemcpy(h,p,n*sizeof(T),cudaMemcpyDeviceToHost));
}
} // namespace c08_residual_visc_gpu_math_r1

// SOLE HOST ENTRY. Host arrays: pos/vel/base/delta/added are (x,z), not (x,y).
// V/rho are actual current V0*J and mixture density. G is actual float soil G,
// h is actual float KernelH; alpha=.1 is a proposed component parameter only.
// L9 has 9*n doubles; all remaining output arrays have n entries. The caller
// must supply separate, nonoverlapping input/output arrays. No file I/O occurs.
// cudaSuccess means API completion, NOT mathematical acceptance: require every
// node_errors[i]==0. On CUDA API failure output arrays may be incomplete.
extern "C" cudaError_t C08ResidualViscGpuMathR1(
  const double2* host_pos_xz,const double2* host_vel_xz,
  const double* host_volume,const double* host_rho,
  const double2* host_baseline_ace_xz,const unsigned n,
  const float h,const float G,const double alpha,
  double* host_L9,double2* host_delta_ace_xz,float2* host_added_ace_xz,
  double* host_lambda_bound_s1,unsigned* host_node_errors){
  using namespace c08_residual_visc_gpu_math_r1;
  if(n<3||n>5000||!host_pos_xz||!host_vel_xz||!host_volume||!host_rho
    ||!host_baseline_ace_xz||!host_L9||!host_delta_ace_xz||!host_added_ace_xz
    ||!host_lambda_bound_s1||!host_node_errors||!isfinite(h)||!(h>0)
    ||!isfinite(G)||!(G>0)||!isfinite(alpha)||alpha<0)return(cudaErrorInvalidValue);
  // FunSphKernel.h::GetKernelCubic_Ctes(true, double(KernelH)).
  const double hd=h,pi=3.141592653589793238462643383279502884;
  const double aa=(10./(pi*7.))/(hd*hd*hd);
  const Cubic c={h,float(-3.*aa),float(9.*aa/4.),float(-3.*aa/4.),4.*hd*hd};
  DeviceArrays d;cudaError_t e;
#define C08_RV_TRY(call) do{e=(call);if(e!=cudaSuccess)return(e);}while(0)
  C08_RV_TRY(Allocate(d.pos,n));C08_RV_TRY(Allocate(d.vel,n));
  C08_RV_TRY(Allocate(d.base,n));C08_RV_TRY(Allocate(d.V,n));
  C08_RV_TRY(Allocate(d.rho,n));C08_RV_TRY(Allocate(d.da,n));
  C08_RV_TRY(Allocate(d.L9,size_t(n)*9));C08_RV_TRY(Allocate(d.lambda,n));
  C08_RV_TRY(Allocate(d.added,n));C08_RV_TRY(Allocate(d.fiterrors,n));
  C08_RV_TRY(Allocate(d.errors,n));
  C08_RV_TRY(Upload(d.pos,host_pos_xz,n));C08_RV_TRY(Upload(d.vel,host_vel_xz,n));
  C08_RV_TRY(Upload(d.base,host_baseline_ace_xz,n));
  C08_RV_TRY(Upload(d.V,host_volume,n));C08_RV_TRY(Upload(d.rho,host_rho,n));
  const unsigned block=128,grid=(n+block-1)/block;
  Fit<<<grid,block>>>(n,c,double(G),alpha,d.pos,d.vel,d.V,d.rho,d.base,d.L9,d.lambda,d.fiterrors);
  C08_RV_TRY(cudaGetLastError());
  Force<<<grid,block>>>(n,c,double(G),alpha,d.pos,d.vel,d.V,d.rho,d.base,d.L9,d.fiterrors,d.da,d.added,d.errors);
  C08_RV_TRY(cudaGetLastError());
  C08_RV_TRY(Download(host_L9,d.L9,size_t(n)*9));
  C08_RV_TRY(Download(host_delta_ace_xz,d.da,n));
  C08_RV_TRY(Download(host_added_ace_xz,d.added,n));
  C08_RV_TRY(Download(host_lambda_bound_s1,d.lambda,n));
  C08_RV_TRY(Download(host_node_errors,d.errors,n));
#undef C08_RV_TRY
  return(cudaSuccess);
}
