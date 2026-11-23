#include <cuda_runtime.h>
#include "c08_m0_pressure_row.cuh"

// Device replay of assembled physical rows. Each input is an independent row;
// no history rotation, neighbour search or free-surface decision is inferred.
struct PressureRow {
  double diagonal,compression,darcy,conductivityGradient,beta,dt;
  float pn,previous,iterate;
  int dirichlet;
};
struct Result {
  double residual;
  float next;
  int valid;
};

__global__ void Evaluate(int count,const PressureRow* rows,Result* results) {
  const int i=int(blockDim.x*blockIdx.x+threadIdx.x);
  if(i>=count) return;
  const PressureRow r=rows[i];
  Result out={};
  out.residual=r.compression+r.darcy+r.conductivityGradient;
  out.valid=c08_m0::Correct(r.dirichlet!=0,r.pn,r.previous,r.iterate,
    r.diagonal,out.residual,r.beta,r.dt,out.next);
  results[i]=out;
}

extern "C" __declspec(dllexport) int C08PressureRows(
    int count,const PressureRow* input,Result* output) {
  if(count<=0 || !input || !output) return int(cudaErrorInvalidValue);
  PressureRow* rows=nullptr;
  Result* results=nullptr;
  cudaError_t rc=cudaMalloc(&rows,sizeof(PressureRow)*count);
  if(rc==cudaSuccess) rc=cudaMalloc(&results,sizeof(Result)*count);
  if(rc==cudaSuccess) rc=cudaMemcpy(rows,input,sizeof(PressureRow)*count,cudaMemcpyHostToDevice);
  if(rc==cudaSuccess) {
    Evaluate<<<(count+127)/128,128>>>(count,rows,results);
    rc=cudaGetLastError();
  }
  if(rc==cudaSuccess) rc=cudaMemcpy(output,results,sizeof(Result)*count,cudaMemcpyDeviceToHost);
  const cudaError_t releaseResults=cudaFree(results),releaseRows=cudaFree(rows);
  if(rc==cudaSuccess) rc=releaseResults;
  return int(rc==cudaSuccess? releaseRows: rc);
}
