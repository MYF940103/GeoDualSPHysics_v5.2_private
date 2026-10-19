//HEAD_DSPH
/*
 <DUALSPHYSICS> Copyright (c) 2020 by Dr Jose M. Dominguez et al.
 This file is part of DualSPHysics, distributed under the GNU Lesser General
 Public License, version 2.1 or (at your option) any later version.
*/
/// \file JSphHourglassGpu_ker.cu \brief Native-ID matched-LS elastic HG kernels.
#include "JSphHourglassGpu_ker.h"
#include <cuda_runtime.h>
#include <cfloat>
#include <climits>
#include <cmath>

namespace cuhg{
static const unsigned BLOCK=128;

__device__ StReduce Empty(){
  StReduce r={};r.zmin=DBL_MAX;r.zmax=-DBL_MAX;return(r);
}
__device__ StReduce Join(StReduce a,const StReduce& b){
  a.zmin=fmin(a.zmin,b.zmin);a.zmax=fmax(a.zmax,b.zmax);
  a.netx+=b.netx;a.netz+=b.netz;a.actualx+=b.actualx;a.actualz+=b.actualz;
  a.sumforce+=b.sumforce;a.hmax=fmax(a.hmax,b.hmax);
  a.condition=fmax(a.condition,b.condition);a.skew=fmax(a.skew,b.skew);
  a.form+=b.form;a.lambda=fmax(a.lambda,b.lambda);a.ratepower+=b.ratepower;
  a.rmax=fmax(a.rmax,b.rmax);a.sumrate+=b.sumrate;
  a.meandxx+=b.meandxx;a.rmsdxx+=b.rmsdxx;a.meandiv+=b.meandiv;a.rmsdiv+=b.rmsdiv;
  a.errors|=b.errors;a.changed|=b.changed;a.pairs+=b.pairs;return(a);
}
__device__ void BlockReduce(StReduce value,StReduce* partial){
  __shared__ StReduce shared[BLOCK];
  const unsigned tid=threadIdx.x;shared[tid]=value;__syncthreads();
  for(unsigned stride=BLOCK/2;stride;stride>>=1){
    if(tid<stride)shared[tid]=Join(shared[tid],shared[tid+stride]);
    __syncthreads();
  }
  if(!tid)partial[blockIdx.x]=shared[0];
}
__global__ void KerReduce(unsigned n,const StReduce* partial,StReduce* result){
  StReduce value=Empty();
  for(unsigned i=threadIdx.x;i<n;i+=BLOCK)value=Join(value,partial[i]);
  BlockReduce(value,result);
}
void Reduce(unsigned count,const StReduce* partial,StReduce* result){
  KerReduce<<<1,BLOCK>>>(count,partial,result);
}

__global__ void KerMapNative(unsigned np,unsigned npb,unsigned firstid,unsigned count,
  const unsigned* idp,const typecode* code,unsigned* slots,unsigned* errors)
{
  const unsigned p=blockIdx.x*blockDim.x+threadIdx.x+npb;
  if(p<np && CODE_IsNormal(code[p]) && CODE_IsFluid(code[p])){
    const unsigned id=idp[p];
    if(id<firstid || id-firstid>=count)atomicOr(errors,unsigned(ERR_Id));
    else if(atomicCAS(slots+(id-firstid),UINT_MAX,p)!=UINT_MAX)
      atomicOr(errors,unsigned(ERR_Duplicate));
  }
}
void MapNative(unsigned np,unsigned npb,unsigned firstid,unsigned count,
  const unsigned* idp,const typecode* code,unsigned* slots,unsigned* errors)
{
  cudaMemset(slots,0xff,sizeof(unsigned)*count);cudaMemset(errors,0,sizeof(unsigned));
  if(np>npb)KerMapNative<<<PartialCount(np-npb),BLOCK>>>(np,npb,firstid,count,idp,code,slots,errors);
}
__device__ bool SameDouble(double a,double b){ return(__double_as_longlong(a)==__double_as_longlong(b)); }
__global__ void KerGather(unsigned count,double mass,const unsigned* slots,const unsigned* errors,
  const double2* posxy,const double* posz,const float4* velrhop,const float* kplastic,
  StNode* nodes,StReduce* partial)
{
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;StReduce r=Empty();r.errors=*errors;
  if(i<count){
    const unsigned p=slots[i];
    if(p==UINT_MAX)r.errors|=ERR_Missing;
    else{
      const float4 v=velrhop[p];
      const double x=posxy[p].x,z=posz[p],vx=v.x,vz=v.z;
      if(!(v.w>0 && isfinite(v.w)))r.errors|=ERR_Density;
      if(kplastic[p]!=0)r.errors|=ERR_Plastic;
      if(!(isfinite(x) && isfinite(z) && isfinite(vx) && isfinite(vz)))r.errors|=ERR_State;
      if(!r.errors){
        const double vol=mass/double(v.w);StNode& n=nodes[i];
        r.changed=!(SameDouble(n.x,x) && SameDouble(n.z,z) && SameDouble(n.vx,vx)
          && SameDouble(n.vz,vz) && SameDouble(n.vol,vol));
        n.x=x;n.z=z;n.vx=vx;n.vz=vz;n.vol=vol;r.zmin=z;r.zmax=z;
      }
    }
  }
  BlockReduce(r,partial);
}
void Gather(unsigned count,double mass,const unsigned* slots,const unsigned* errors,
  const double2* posxy,const double* posz,const float4* velrhop,const float* kplastic,
  StNode* nodes,StReduce* partial)
{
  KerGather<<<PartialCount(count),BLOCK>>>(count,mass,slots,errors,posxy,posz,velrhop,kplastic,nodes,partial);
}

__device__ int CellX(const StNode& n,const StGrid& g){
  const double x=n.x-g.period*floor(n.x/g.period);
  return(min(int(g.nx)-1,int(x/g.cellx)));
}
__device__ int CellZ(const StNode& n,const StGrid& g){
  // Clamp only the last-cell index against host/device division rounding.
  return(min(int(g.nz)-1,int((n.z-g.zmin)/g.support)));
}
__global__ void KerCellKeys(unsigned count,StGrid grid,const StNode* nodes,unsigned* keys,unsigned* order){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i<count){keys[i]=unsigned(CellZ(nodes[i],grid))*grid.nx+unsigned(CellX(nodes[i],grid));order[i]=i;}
}
void CellKeys(unsigned count,StGrid grid,const StNode* nodes,unsigned* keys,unsigned* order){
  KerCellKeys<<<PartialCount(count),BLOCK>>>(count,grid,nodes,keys,order);
}
__device__ int Columns(int cx,int nx,int* cols){
  int n=0;
  for(int dx=-1;dx<=1;dx++){
    const int c=(cx+dx+nx)%nx;bool seen=false;
    for(int k=0;k<n;k++)seen|=cols[k]==c;
    if(!seen)cols[n++]=c;
  }
  return(n);
}
// Always form the pair from lower to higher native ID, including both endpoint
// gathers. Opposite forces therefore reuse the same sign and product order.
__device__ bool Pair(unsigned i,unsigned j,const StNode* nodes,const StGrid& g,
  double& dx,double& dz,double& w,double& vx,double& vz,bool& coincident)
{
  if(i==j)return(false);
  const unsigned lo=min(i,j),hi=max(i,j);const StNode& a=nodes[lo];const StNode& b=nodes[hi];
  dx=a.x-b.x;dx-=g.period*floor(dx/g.period+.5);dz=a.z-b.z;
  const double rr=dx*dx+dz*dz;
  if(rr>=g.support*g.support)return(false);
  if(!(rr>0)){coincident=true;return(false);}
  const double s=fmax(0.,1.-sqrt(rr)/(2*g.h));w=-g.bwen/g.h*s*s*s;
  vx=a.vx-b.vx;vz=a.vz-b.vz;return(true);
}
__global__ void KerMoments(unsigned count,StGrid g,const unsigned* order,const int2* ranges,
  StNode* nodes,unsigned* errors)
{
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i>=count)return;
  StNode& a=nodes[i];const int cx=CellX(a,g),cz=CellZ(a,g);
  int cols[3];const int ncols=Columns(cx,int(g.nx),cols);bool coincident=false;
  double mxx=0,mxz=0,mzz=0,nxx=0,nxz=0,nzx=0,nzz=0;
  for(int z=max(0,cz-1);z<=min(int(g.nz)-1,cz+1);z++)for(int c=0;c<ncols;c++){
    const int2 range=ranges[z*g.nx+cols[c]];
    for(int k=range.x;k<range.y;k++){
      const unsigned j=order[k];double dx,dz,w,vx,vz;
      if(Pair(i,j,nodes,g,dx,dz,w,vx,vz,coincident)){
        w*=nodes[j].vol;
        mxx+=w*dx*dx;mxz+=w*dx*dz;mzz+=w*dz*dz;
        nxx+=w*vx*dx;nxz+=w*vx*dz;nzx+=w*vz*dx;nzz+=w*vz*dz;
      }
    }
  }
  if(coincident)atomicOr(errors,unsigned(ERR_Coincident));
  const double det=mxx*mzz-mxz*mxz,tr=mxx+mzz;
  const double hi=.5*(tr+hypot(mxx-mzz,2*mxz)),lo=det/hi;
  if(!(isfinite(det) && lo>0 && hi/lo<1e8)){
    atomicOr(errors,unsigned(ERR_Rank));a.lxx=a.lxz=a.lzx=a.lzz=0;a.condition=a.skew=0;
  }
  else{
    a.lxx=(nxx*mzz-nxz*mxz)/det;a.lxz=(nxz*mxx-nxx*mxz)/det;
    a.lzx=(nzx*mzz-nzz*mxz)/det;a.lzz=(nzz*mxx-nzx*mxz)/det;
    a.condition=hi/lo;a.skew=.5*fabs(a.lxz-a.lzx);
  }
}
void Moments(unsigned count,StGrid grid,const unsigned* order,const int2* ranges,
  StNode* nodes,unsigned* errors)
{
  KerMoments<<<PartialCount(count),BLOCK>>>(count,grid,order,ranges,nodes,errors);
}
__global__ void KerRates(unsigned count,StGrid g,const unsigned* order,const int2* ranges,
  const StNode* nodes,const unsigned* errors,double2* rates,StReduce* partial)
{
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;StReduce r=Empty();r.errors=*errors;
  if(i<count && !r.errors){
    const StNode& a=nodes[i];const int cx=CellX(a,g),cz=CellZ(a,g);
    int cols[3];const int ncols=Columns(cx,int(g.nx),cols);bool coincident=false;
    double rx=0,rz=0,betasum=0;
    for(int z=max(0,cz-1);z<=min(int(g.nz)-1,cz+1);z++)for(int c=0;c<ncols;c++){
      const int2 range=ranges[z*g.nx+cols[c]];
      for(int k=range.x;k<range.y;k++){
        const unsigned j=order[k];double dx,dz,w,vx,vz;
        if(Pair(i,j,nodes,g,dx,dz,w,vx,vz,coincident)){
          const StNode& lo=nodes[min(i,j)];const StNode& hi=nodes[max(i,j)];
          const double aix=vx-lo.lxx*dx-lo.lxz*dz,aiz=vz-lo.lzx*dx-lo.lzz*dz;
          const double bjx=vx-hi.lxx*dx-hi.lxz*dz,bjz=vz-hi.lzx*dx-hi.lzz*dz;
          const double beta=g.xi*g.shear*lo.vol*hi.vol*w;
          const double x=-beta*.5*(aix+bjx)/g.mass,zrate=-beta*.5*(aiz+bjz)/g.mass;
          if(i<j){rx+=x;rz+=zrate;r.pairs++;r.form+=.25*beta*(aix*aix+aiz*aiz+bjx*bjx+bjz*bjz);}
          else{rx-=x;rz-=zrate;}
          betasum+=beta;
        }
      }
    }
    rates[i]=make_double2(rx,rz);
    if(coincident)r.errors|=ERR_Coincident;
    if(!(isfinite(rx) && isfinite(rz)))r.errors|=ERR_Rate;
    r.condition=a.condition;r.skew=a.skew;r.lambda=2*betasum/g.mass;
    r.netx=g.mass*rx;r.netz=g.mass*rz;r.rmax=hypot(rx,rz);r.sumrate=g.mass*r.rmax;
    r.ratepower=g.mass*(a.vx*rx+a.vz*rz);
    const double div=a.lxx+a.lzz;r.meandxx=a.lxx;r.rmsdxx=a.lxx*a.lxx;r.meandiv=div;r.rmsdiv=div*div;
  }
  BlockReduce(r,partial);
}
void Rates(unsigned count,StGrid grid,const unsigned* order,const int2* ranges,
  const StNode* nodes,const unsigned* errors,double2* rates,StReduce* partial)
{
  KerRates<<<PartialCount(count),BLOCK>>>(count,grid,order,ranges,nodes,errors,rates,partial);
}

__global__ void KerAddHistory(unsigned count,double mass,const unsigned* slots,const unsigned* errors,
  const double2* history,float3* ace,StReduce* partial)
{
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;StReduce r=Empty();r.errors=*errors;
  if(i<count){
    const unsigned p=slots[i];
    if(p==UINT_MAX)r.errors|=ERR_Missing;
    else if(!r.errors){
      const double2 h=history[i];
      if(!(isfinite(h.x) && isfinite(h.y)))r.errors|=ERR_History;
      else{
        const double ax=ace[p].x,az=ace[p].z;
        const float x=float(ax+h.x),z=float(az+h.y);ace[p].x=x;ace[p].z=z;
        r.actualx=mass*(double(x)-ax);r.actualz=mass*(double(z)-az);
        r.netx=mass*h.x;r.netz=mass*h.y;r.hmax=hypot(h.x,h.y);r.sumforce=mass*r.hmax;
      }
    }
  }
  BlockReduce(r,partial);
}
void AddHistory(unsigned count,double mass,const unsigned* slots,const unsigned* errors,
  const double2* history,float3* ace,StReduce* partial)
{
  KerAddHistory<<<PartialCount(count),BLOCK>>>(count,mass,slots,errors,history,ace,partial);
}
__global__ void KerUpdateHistory(unsigned count,double dt,const double2* rates,double2* history,StReduce* partial){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;StReduce r=Empty();
  if(i<count){
    double2 h=history[i];const double2 rate=rates[i];const double halfdt=__dmul_rn(.5,dt);
    // Match the two CPU writebacks; do not contract the history add into FMA.
    h.x=__dadd_rn(h.x,__dmul_rn(halfdt,rate.x));h.y=__dadd_rn(h.y,__dmul_rn(halfdt,rate.y));
    history[i]=h;r.hmax=hypot(h.x,h.y);
    if(!(isfinite(h.x) && isfinite(h.y)))r.errors|=ERR_History;
  }
  BlockReduce(r,partial);
}
void UpdateHistory(unsigned count,double dt,const double2* rates,double2* history,StReduce* partial){
  KerUpdateHistory<<<PartialCount(count),BLOCK>>>(count,dt,rates,history,partial);
}
}
