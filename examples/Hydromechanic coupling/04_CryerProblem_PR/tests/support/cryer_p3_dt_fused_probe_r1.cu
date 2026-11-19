// Build-only candidate; host preserves legacy-before-skeleton failure precedence.
// Output must be initialized to {0,0,0,np,np}. Launch with a power-of-two block.
#include "DualSphDef.h"
#include "cryer_p3_dt_fused_r1.h"

namespace cryer_p3_dt {
__global__ void CollectScales(unsigned np,unsigned npb,const typecode* code,const double* J,
  Params params,Summary* result){
  extern __shared__ double scratch[];
  const unsigned t=threadIdx.x,i=blockIdx.x*blockDim.x+t,w=blockDim.x;
  Value v={0.,0.,0.,true,true};
  if(i>=npb && i<np && CODE_IsNormal(code[i]) && CODE_IsFluid(code[i])){
    v=Evaluate(J[i],params);
    if(!v.legacy_valid)atomicMin(&result->invalid_legacy,i);
    if(!v.skeleton_valid)atomicMin(&result->invalid_skeleton,i);
  }
  scratch[t]=v.legacy2;scratch[w+t]=v.skeleton2;scratch[2*w+t]=v.diffusion;
  __syncthreads();
  for(unsigned stride=w/2;stride;stride>>=1){
    if(t<stride){
      for(unsigned lane=0;lane<3;lane++){
        double* values=scratch+lane*w;
        if(values[t]<values[t+stride])values[t]=values[t+stride];
      }
    }
    __syncthreads();
  }
  if(t==0){
    atomicMax((unsigned long long*)&result->legacy2,(unsigned long long)__double_as_longlong(scratch[0]));
    atomicMax((unsigned long long*)&result->skeleton2,(unsigned long long)__double_as_longlong(scratch[w]));
    atomicMax((unsigned long long*)&result->diffusion,(unsigned long long)__double_as_longlong(scratch[2*w]));
  }
}
void Launch(unsigned np,unsigned npb,const typecode* code,const double* J,Params p,Summary* out){
  constexpr unsigned w=128;
  if(np)CollectScales<<<(np+w-1)/w,w,3*w*sizeof(double)>>>(np,npb,code,J,p,out);
}
}

