#include <cuda_runtime.h>
#include "TpiPressureRow.h"
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <vector>

struct Sample {
  double predicted,diagonal,residual;
  float pn,previous,iterated,written,half;
  unsigned sourceDrained,endpointDrained,padding;
};
static_assert(sizeof(Sample)==56,"Sample layout changed");

template<class T> __host__ __device__ bool Identical(T a,T b) {
  const unsigned char* x=reinterpret_cast<const unsigned char*>(&a);
  const unsigned char* y=reinterpret_cast<const unsigned char*>(&b);
  for(unsigned i=0;i<sizeof(T);i++) if(x[i]!=y[i])return false;
  return true;
}
__host__ __device__ unsigned Check(const Sample& row) {
  double predicted=0.;
  float pressure=0.f;
  if(!tpi_pressure::Predict(tpi_pressure::Predictor::Linear,row.pn,row.previous,predicted)) return 1;
  if(!Identical(predicted,row.predicted)) return 2;
  if(!Identical(row.sourceDrained?0.f:tpi_pressure::WritePressure(predicted),row.half)) return 3;
  if(!tpi_pressure::Endpoint(row.endpointDrained!=0,row.iterated,row.diagonal,row.residual,pressure)) return 4;
  if(!Identical(pressure,row.written)) return 5;
  return 0;
}
__host__ __device__ unsigned Fixtures(double nan) {
  double predicted=77.;
  float pressure=17.f;
  if(!tpi_pressure::Predict(tpi_pressure::Predictor::Current,-0.f,float(nan),predicted) || !Identical(predicted,-0.0))return 1;
  if(tpi_pressure::Predict(tpi_pressure::Predictor::Linear,1.f,float(nan),predicted))return 2;
  if(tpi_pressure::Predict(tpi_pressure::Predictor::Linear,FLT_MAX,-FLT_MAX,predicted))return 3;
  if(tpi_pressure::Endpoint(false,1.f,0.,2.,pressure) || !Identical(pressure,17.f))return 4;
  if(tpi_pressure::Endpoint(false,1.f,-1.,2.,pressure) || tpi_pressure::Endpoint(false,1.f,1.,nan,pressure))return 5;
  if(tpi_pressure::Endpoint(false,FLT_MAX,1.,double(FLT_MAX),pressure))return 6;
  if(!tpi_pressure::Endpoint(true,1.f,0.,nan,pressure) || !Identical(pressure,+0.f))return 7;
  if(!tpi_pressure::Endpoint(false,1.f,1.,0x1p-24,pressure) || !Identical(pressure,1.f))return 8;
  // Second midpoint has an odd lower significand, and rounds to the upper float.
  if(!tpi_pressure::Endpoint(false,1.f,1.,3.*0x1p-24,pressure) || !Identical(pressure,1.0000002384185791015625f))return 9;
  return 0;
}
__global__ void Replay(const Sample* rows,unsigned count,unsigned* result,double nan) {
  unsigned i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i<count)result[i]=Check(rows[i]);
  if(!i)result[count]=Fixtures(nan);
}
void Checked(cudaError_t err) {if(err!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(err));}

int main(int argc,char** argv) {
  try {
    if(argc!=2)throw std::runtime_error("Expected one native row fixture");
    std::ifstream in(argv[1],std::ios::binary|std::ios::ate);
    const std::streamoff bytes=in.tellg();
    if(bytes<=0 || bytes%sizeof(Sample))throw std::runtime_error("Invalid fixture extent");
    std::vector<Sample> rows(size_t(bytes)/sizeof(Sample));
    in.seekg(0);in.read(reinterpret_cast<char*>(rows.data()),bytes);
    if(!in || rows.size()>0xffffffffull)throw std::runtime_error("Invalid fixture I/O");
    unsigned count=unsigned(rows.size());
    const double nan=std::numeric_limits<double>::quiet_NaN();
    if(Fixtures(nan))throw std::runtime_error("CPU arithmetic edge fixture failed");
    for(unsigned i=0;i<count;i++)if(const auto code=Check(rows[i])){
      std::fprintf(stderr,"CPU row=%u code=%u\n",i,code);return 2;
    }
    Sample* deviceRows=nullptr;unsigned* deviceResult=nullptr;
    std::vector<unsigned> results(count+1);
    Checked(cudaMalloc(&deviceRows,size_t(bytes)));
    Checked(cudaMalloc(&deviceResult,results.size()*sizeof(unsigned)));
    Checked(cudaMemcpy(deviceRows,rows.data(),size_t(bytes),cudaMemcpyHostToDevice));
    Replay<<<(count+127)/128,128>>>(deviceRows,count,deviceResult,nan);
    Checked(cudaGetLastError());
    Checked(cudaMemcpy(results.data(),deviceResult,results.size()*sizeof(unsigned),cudaMemcpyDeviceToHost));
    Checked(cudaFree(deviceResult));Checked(cudaFree(deviceRows));
    for(unsigned i=0;i<results.size();i++)if(results[i]){
      std::fprintf(stderr,"GPU row=%u code=%u\n",i,results[i]);return 3;
    }
    std::printf("{\"passed\":true,\"rows_per_backend\":%u,\"host_and_device_mismatches\":0,\"edge_tests_per_backend\":9}\n",count);
    return 0;
  }catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}
}
