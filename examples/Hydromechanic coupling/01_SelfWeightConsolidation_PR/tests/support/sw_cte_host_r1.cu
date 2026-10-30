// Isolated reproduction of the host-side CTE.poscellsize launch argument.
// No particles, production solver, or physical integration are used.
#include <cuda_runtime.h>
#include <iomanip>
#include <iostream>
#include <stdexcept>
struct ProbeConstants{float poscellsize;};
__constant__ ProbeConstants CTE;
static void Check(cudaError_t error){if(error!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(error));}
__global__ void Observe(float argument,float *values){values[0]=argument;values[1]=CTE.poscellsize;}
int main(){
  try{
    ProbeConstants configured={0.036f},copied={0};
    Check(cudaMemcpyToSymbol(CTE,&configured,sizeof(configured)));
    Check(cudaMemcpyFromSymbol(&copied,CTE,sizeof(copied)));
    float *device=nullptr,values[2]={0,0};
    Check(cudaMalloc(&device,sizeof(values)));
    Observe<<<1,1>>>(CTE.poscellsize,device);
    Check(cudaGetLastError());Check(cudaDeviceSynchronize());
    Check(cudaMemcpy(values,device,sizeof(values),cudaMemcpyDeviceToHost));Check(cudaFree(device));
    cudaDeviceProp properties;Check(cudaGetDeviceProperties(&properties,0));
    std::cout<<"gpu="<<properties.name<<'\n'<<std::setprecision(17)
      <<"configured_host,device_constant,api_symbol_copy,host_launch_argument\n"
      <<configured.poscellsize<<','<<values[1]<<','<<copied.poscellsize<<','<<values[0]<<'\n';
    Check(cudaDeviceReset());return 0;
  }catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}
}
