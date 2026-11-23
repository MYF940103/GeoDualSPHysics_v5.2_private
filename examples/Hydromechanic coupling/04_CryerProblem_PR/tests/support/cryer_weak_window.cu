// Private fixed-geometry candidate. The original solver and its exported ABI remain intact.
#include "cryer_pair_window.cu"

struct WeakContext {
  Csr stiffness;
#ifdef CRYER_VORONOI_WINDOW
  Csr hydraulicAcceleration;
#endif
  double *volume,*diagonal,*blockSum,*correction;
  V *halfBase,*halfPressure,*endBase,*trial;
  double closedResponse;
};
static WeakContext weak={};
static bool weakStarted=false;
static constexpr int reductionSize=256;
static int reductionBlocks(){return (ctx.n+reductionSize-1)/reductionSize;}

API int uploadWeak(int nz,const int* row,const int* col,const double* value,
                   const double* volume,const double* diagonal){BEGIN_API
  const int n=ctx.n;
  if(!ctx.x||completed||failed||weak.stiffness.row||nz<=0||!row||!col||!value||!volume||!diagonal
    ||row[0]!=0||row[n]!=nz)throw std::runtime_error("Invalid or duplicate weak operator upload");
  std::vector<V> traction(n);std::vector<double> mass(n);
  ck(cudaMemcpy(traction.data(),ctx.traction,n*sizeof(V),cudaMemcpyDeviceToHost));
  ck(cudaMemcpy(mass.data(),ctx.mass,n*sizeof(double),cudaMemcpyDeviceToHost));
  double response=0.;
  for(int i=0;i<n;i++){
    if(row[i]>=row[i+1]||!(volume[i]>0.)||!std::isfinite(volume[i])||!(diagonal[i]>0.)||!std::isfinite(diagonal[i]))
      throw std::runtime_error("Invalid weak row volume/denominator");
    const V f=traction[i];response+=(f.x*f.x+f.y*f.y+f.z*f.z)/mass[i];
  }
  for(int k=0;k<nz;k++)if(col[k]<0||col[k]>=n||!std::isfinite(value[k]))
    throw std::runtime_error("Invalid weak stiffness entry");
  if(!(response>0.)||!std::isfinite(response))throw std::runtime_error("Missing closed-volume pressure response");
  weak.closedResponse=response;
  upload(weak.stiffness.row,row,n+1);upload(weak.stiffness.col,col,nz);upload(weak.stiffness.scalar,value,nz);
  upload(weak.volume,volume,n);upload(weak.diagonal,diagonal,n);
  allocate(weak.blockSum,reductionBlocks());allocate(weak.correction,1);
  allocate(weak.halfBase,n);allocate(weak.halfPressure,n);allocate(weak.endBase,n);allocate(weak.trial,n);END_API}

API int startWeak(){BEGIN_API
#ifdef CRYER_VORONOI_WINDOW
  if(!weak.hydraulicAcceleration.row)throw std::runtime_error("Missing Voronoi acceleration flux");
#endif
  if(weakStarted||failed||completed||!ctx.x||!ctx.gradient.row||!ctx.transpose.row||!ctx.av.row||!weak.stiffness.row)
    throw std::runtime_error("Incomplete or duplicate weak initialization");
  if(!started){initJ<<<grid(),128>>>(ctx.now,ctx.n);ck(cudaDeviceSynchronize());started=true;}
  weakStarted=true;END_API}

__global__ void weakLocalRows(Context c,WeakContext w,const double* q,double* output,bool drain,bool roundFloat,int update,int phase){
  const int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=c.n)return;
  if(drain&&c.surface[i]){output[i]=0.;return;}
  double stiffness=0.,accFlux=0.;
  for(int k=w.stiffness.row[i];k<w.stiffness.row[i+1];k++)
    stiffness+=w.stiffness.scalar[k]*q[w.stiffness.col[k]];
#ifdef CRYER_VORONOI_WINDOW
  const Csr flux=w.hydraulicAcceleration;
#else
  const Csr flux=c.transpose;
#endif
  for(int k=flux.row[i];k<flux.row[i+1];k++)
    accFlux+=dot(flux.vector[k],c.acc[flux.col[k]]);
  const double beta=(1000.*9.80665)/double(1.e-5f);
  const double next=q[i]-(stiffness+1000.*accFlux+beta*w.volume[i]*c.theta[i])/w.diagonal[i];
  output[i]=roundFloat?double(float(next)):next;
  if(!isfinite(output[i]))recordFault(c,i,update,phase);
}

// The surface API stores inward force for positive external compression. Its
// negative is b=G*1, the nodal force of a spatially constant pore pressure.
__global__ void weakPartial(Context c,WeakContext w,const V* value,const V* additional,double scaleValue,double scaleAdditional){
  __shared__ double s[reductionSize];
  const int i=blockIdx.x*blockDim.x+threadIdx.x,lane=threadIdx.x;
  double v=0.;
  if(i<c.n){
    v=-scaleValue*dot(c.traction[i],value[i]);
    if(additional)v-=scaleAdditional*dot(c.traction[i],additional[i]);
  }
  s[lane]=v;__syncthreads();
  for(int shift=reductionSize/2;shift;shift/=2){if(lane<shift)s[lane]+=s[lane+shift];__syncthreads();}
  if(!lane)w.blockSum[blockIdx.x]=s[0];
}

__global__ void weakScalar(WeakContext w,int blocks,double target){
  __shared__ double s[reductionSize];const int lane=threadIdx.x;
  double v=0.;for(int k=lane;k<blocks;k+=blockDim.x)v+=w.blockSum[k];
  s[lane]=v;__syncthreads();
  for(int shift=reductionSize/2;shift;shift/=2){if(lane<shift)s[lane]+=s[lane+shift];__syncthreads();}
  if(!lane)w.correction[0]=(target-s[0])/w.closedResponse;
}

__global__ void weakApply(Context c,WeakContext w,double* q,int update,int phase){
  const int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=c.n)return;
  q[i]=float(q[i]+w.correction[0]);if(!isfinite(q[i]))recordFault(c,i,update,phase);
}

static void weakProject(double* q,const V* v,double factor,const V* add,double factorAdd,double target,int phase){
  weakPartial<<<reductionBlocks(),reductionSize>>>(ctx,weak,v,add,factor,factorAdd);
  weakScalar<<<1,reductionSize>>>(weak,reductionBlocks(),target);
  weakApply<<<grid(),128>>>(ctx,weak,q,completed+1,phase);
}

static void copyDevice(void* to,const void* from,size_t bytes){
  ck(cudaMemcpyAsync(to,from,bytes,cudaMemcpyDeviceToDevice));
}
static void weakMechanicalPressure(double* q,double dt,bool drain,int phase){
  totalForce<<<grid(),128>>>(ctx,q);
  if(!drain){
    // Force drives a new velocity v_n+dt*a. Correct its geometric-volume derivative.
    weakProject(q,ctx.acc,1.,ctx.now.v,1./dt,0.,phase);
    totalForce<<<grid(),128>>>(ctx,q);
  }
}
__global__ void weakTrial(Context c,WeakContext w,bool writeAcceleration){
  int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=c.n)return;
  const V dv=scale(minusV(c.pressureAcc[i],w.halfPressure[i]),c.dt);
  w.trial[i]=plus(c.end.v[i],dv);
  // AV and stress are frozen at the provisional endpoint. Damping uses this trial velocity.
  if(writeAcceleration)c.acc[i]=minusV(plus(w.endBase[i],c.pressureAcc[i]),scale(dv,c.damping));
}
__global__ void weakDivergence(Context c,WeakContext w){
  int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=c.n)return;
  double theta=0.;
  for(int k=c.gradient.row[i];k<c.gradient.row[i+1];k++)theta+=dot(c.gradient.vector[k],w.trial[c.gradient.col[k]]);
  c.theta[i]=theta;
}
static void checkWeakFailure(){
  int bad[3]={};ck(cudaMemcpy(bad,ctx.bad,sizeof(bad),cudaMemcpyDeviceToHost));
  if(bad[0]){
    failed=true;throw std::runtime_error("First invalid weak update "+std::to_string(bad[1])+", phase "+
      std::to_string(bad[2])+", native ID "+std::to_string(bad[0]+7));
  }
}

API int advanceWeak(int count){BEGIN_API
  if(!weakStarted||failed||count<1||count>INT_MAX-completed)throw std::runtime_error("Invalid weak update request");
  const size_t nv=ctx.n*sizeof(V),np=ctx.n*sizeof(double);
  for(int it=0;it<count;it++){
    const bool drain=completed>=4096;
    const double load=10000.*std::min(1.,double(completed)/2048.);
    if(drain)clampCurrentPressure<<<grid(),128>>>(ctx);
    predictPressure<<<grid(),128>>>(ctx,drain);
    // Use an independent stage pressure, preserving the actual source history for extrapolation.
    copyDevice(ctx.next,ctx.pressure,np);base(ctx.now,load);
    weakMechanicalPressure(ctx.next,.5*ctx.dt,drain,10);
    mechanicalUpdate<<<grid(),128>>>(ctx,ctx.now,ctx.half,false,completed+1);
    base(ctx.half,load);copyDevice(weak.halfBase,ctx.base,nv);
    weakMechanicalPressure(ctx.guess,ctx.dt,drain,11);
    copyDevice(weak.halfPressure,ctx.pressureAcc,nv);
    mechanicalUpdate<<<grid(),128>>>(ctx,ctx.half,ctx.end,true,completed+1);
    base(ctx.end,load);copyDevice(weak.endBase,ctx.base,nv);
    for(int k=0;k<3;k++){
      totalForce<<<grid(),128>>>(ctx,ctx.guess);
      weakTrial<<<grid(),128>>>(ctx,weak,true);weakDivergence<<<grid(),128>>>(ctx,weak);
      weakLocalRows<<<grid(),128>>>(ctx,weak,ctx.guess,ctx.next,drain,drain,completed+1,20+k);
      if(!drain){
        // Project the integrated impermeable-volume constraint on v(q_new)
        // before its single float write. No extra pressure sweep or new solver.
        totalForce<<<grid(),128>>>(ctx,ctx.next);weakTrial<<<grid(),128>>>(ctx,weak,false);
        weakProject(ctx.next,weak.trial,1./ctx.dt,nullptr,0.,0.,30+k);
      }
      std::swap(ctx.next,ctx.guess);
    }
    // Use the corrected pressure in the midpoint force. Recomputing the original
    // half strain/J rates leaves stress and J tied to their initial midpoint.
    copyDevice(ctx.base,weak.halfBase,nv);totalForce<<<grid(),128>>>(ctx,ctx.guess);
    mechanicalUpdate<<<grid(),128>>>(ctx,ctx.half,ctx.end,true,completed+1);
    commit<<<grid(),128>>>(ctx);std::swap(ctx.now,ctx.end);completed++;
  }
  checkWeakFailure();END_API}

API int weakFixture(const double* p,const double* a,const double* theta,int drain,double* out){BEGIN_API
  if(!weakStarted||failed||completed||!p||!a||!theta||!out)throw std::runtime_error("Invalid weak row fixture");
  const size_t n=ctx.n;
  ck(cudaMemcpy(ctx.next,p,n*sizeof(double),cudaMemcpyHostToDevice));ck(cudaMemcpy(ctx.acc,a,n*sizeof(V),cudaMemcpyHostToDevice));
  ck(cudaMemcpy(ctx.theta,theta,n*sizeof(double),cudaMemcpyHostToDevice));
  weakLocalRows<<<grid(),128>>>(ctx,weak,ctx.next,ctx.guess,drain!=0,true,0,99);
  ck(cudaMemcpy(out,ctx.guess,n*sizeof(double),cudaMemcpyDeviceToHost));checkWeakFailure();END_API}

API int weakClosedFixture(const double* p,const double* baseAcceleration,double target,double* out){BEGIN_API
  if(!weakStarted||failed||completed||!p||!baseAcceleration||!out||!std::isfinite(target))
    throw std::runtime_error("Invalid closed-volume fixture");
  const size_t n=ctx.n;ck(cudaMemcpy(ctx.next,p,n*sizeof(double),cudaMemcpyHostToDevice));
  ck(cudaMemcpy(ctx.base,baseAcceleration,n*sizeof(V),cudaMemcpyHostToDevice));
  totalForce<<<grid(),128>>>(ctx,ctx.next);
  weakProject(ctx.next,ctx.acc,1.,nullptr,0.,target,98);
  ck(cudaMemcpy(out,ctx.next,n*sizeof(double),cudaMemcpyDeviceToHost));checkWeakFailure();END_API}
API int releaseWeak(){int ret=release();if(!ret){weak={};weakStarted=false;}return ret;}

