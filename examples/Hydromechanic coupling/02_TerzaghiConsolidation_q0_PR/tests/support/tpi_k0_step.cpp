#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <cstdio>
#include <stdexcept>
#include <string>
#include <cuda_runtime.h>
#include "JAppInfo.h"
#include "JArraysGpu.h"
#include "JSphCpuSingle.h"
#include "JSphGpuSingle.h"

JAppInfo AppInfo("HydraulicStepTest","1","");

namespace {
const unsigned count=6;
const std::array<typecode,count> codes={CODE_TYPE_FIXED,CODE_TYPE_FLUID,CODE_TYPE_FLUID,
  CODE_TYPE_FLUID,CODE_TYPE_FLUID,CODE_SetPeriodic(CODE_TYPE_FLUID)};
const std::array<double,count> volumeRatios={0.,.88,1.,1.1,1.22,0.};
const float h=.08f,safety=.1f,n0=.35f,baseK=2.e-4f,waterBulk=1.e9f;
const float bulk=1.e8f,shear=3.e7f,density0=2072.5f,waterDensity=1000.f;
const double gravity=9.80665,cfl=.2;

void require(bool passed,const char* reason){
  if(!passed)throw std::runtime_error(reason);
}
void checkCuda(cudaError_t e){
  if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));
}
void checkClose(double got,double expected,const char* name){
  if(got==expected)return;
  if(!std::isfinite(got) || !std::isfinite(expected)
    || std::abs(got-expected)>2.e-12*std::abs(expected))throw std::runtime_error(name);
}

template<class Base> class Fixture:public Base{
public:
  void prepare(){
    this->Np=count;this->Npb=1;
    this->HydroMech=this->PorosityFeedback=this->DynamicPorePressure=true;
    this->SoilCte.ModulusK=bulk;this->SoilCte.ModulusG=shear;
    this->SoilCte.PoreWaterBulkModulus=waterBulk;this->SoilCte.PoreWaterRho=waterDensity;
    this->SoilCte.Porosity=n0;this->RhopZero=density0;this->MassFluid=1.f;
    this->KernelH=h;this->PoreDtSafety=safety;this->CFLnumber=cfl;this->HydroMechTpiR=2.;
    this->VelMax=.25;this->ViscDtMax=.25f;this->AceMax=0.;
    this->DtMin=0.;this->SymplecticDtPre=1.e-9;
  }
  void configure(bool tpi,bool evolving,float k,double gradientSpeed){
    this->HydroMechTpi=tpi;this->DynamicPoreConductivity=evolving;
    this->DynamicPoreConductivityCk=evolving?.25:0.;
    this->SoilCte.HydraulicConductivity=k;this->DynamicConductivitySpeedMax=gradientSpeed;
  }
  double step(){return this->DtVariable(false);}
  bool rejectsLockedStep(double dt){
    this->SymplecticDtPre=dt;
    try{step();}
    catch(const std::exception& error){
      this->SymplecticDtPre=1.e-9;
      return std::string(error.what()).find("current step or DtMin exceeds")!=std::string::npos;
    }
    this->SymplecticDtPre=1.e-9;
    return false;
  }
};
class Cpu:public Fixture<JSphCpuSingle>{
  std::array<typecode,count> c=codes;
  std::array<double,count> j=volumeRatios;
public:
  Cpu(){prepare();Codec=c.data();PoroJc=j.data();}
  ~Cpu(){Codec=nullptr;PoroJc=nullptr;}
  void scales(double& wave,double& pore){GetDynamicStepScalesCpu(wave,pore);}
};
class Gpu:public Fixture<JSphGpuSingle>{
public:
  Gpu(){
    prepare();GpuParticlesSize=count;ArraysGpu->SetArraySize(count);
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_4B);ArraysGpu->AddArrayCount(JArraysGpu::SIZE_8B);
    checkCuda(cudaMalloc(&Codeg,count*sizeof(typecode)));checkCuda(cudaMalloc(&PoroJg,count*sizeof(double)));
    checkCuda(cudaMemcpy(Codeg,codes.data(),count*sizeof(typecode),cudaMemcpyHostToDevice));
    checkCuda(cudaMemcpy(PoroJg,volumeRatios.data(),count*sizeof(double),cudaMemcpyHostToDevice));
  }
  ~Gpu(){cudaFree(Codeg);cudaFree(PoroJg);Codeg=nullptr;PoroJg=nullptr;}
  void scales(double& wave,double& pore){GetDynamicStepScalesGpu(wave,pore);}
};
} // namespace

int main(){
  try{
    Cpu cpu; Gpu gpu;
    std::puts("tpi,evolving_k,k0_m_s,gradient_speed_m_s,expected_wave_s,expected_diffusion_s,cpu_step_s,gpu_step_s");
    // Native slots 0 and 5 intentionally have invalid J; the reduction must exclude both.
    for(bool tpi:{false,true})for(bool evolving:{false,true})for(float k:{0.f,baseK})for(double speed:{0.,10000.}){
      if(tpi && k==0.f)continue; // TPI Jacobi rows require positive mobility.
      if((!evolving || k==0.f) && speed>0.)continue;
      double maxWave2=0.,maxD=0.,maxLiveD=0.;
      const double M=double(bulk)+4.*double(shear)/3.,gamma=double(waterDensity)*gravity;
      for(unsigned i=1;i+1<count;i++){
        const double j=volumeRatios[i],n=1.-(1.-double(n0))/j;
        const double rho=waterDensity+(density0-waterDensity)/j;
        maxWave2=(std::max)(maxWave2,(M+(tpi?0.:waterBulk/n))/rho);
        maxD=(std::max)(maxD,double(waterBulk)*k/n/gamma);
        const double ki=k*std::exp((j-1.)/((1.-double(n0))*.25));
        maxLiveD=(std::max)(maxLiveD,waterBulk*ki/n/gamma);
      }
      if(k>0.)require(maxLiveD>1.05*maxD,"Fixture did not distinguish live-k from k0");
      const double wave=double(h)/((std::max)(std::sqrt(maxWave2),2.5)+double(h)*.25);
      const double pore=k>0.?double(safety)*h*h/maxD:DBL_MAX;
      const double gradient=speed>0.?double(safety)*h/speed:DBL_MAX;
      const double expected=(std::min)(cfl*wave,(std::min)(pore*(tpi?2.:1.),gradient));
      cpu.configure(tpi,evolving,k,speed);gpu.configure(tpi,evolving,k,speed);
      double cw,cp,gw,gp;cpu.scales(cw,cp);gpu.scales(gw,gp);
      checkClose(cw,wave,"CPU wave");checkClose(gw,wave,"GPU wave");checkClose(cp,pore,"CPU diffusion");checkClose(gp,pore,"GPU diffusion");
      const double cpuStep=cpu.step(),gpuStep=gpu.step();
      checkClose(cpuStep,expected,"CPU selected dt");checkClose(gpuStep,expected,"GPU selected dt");
      if(speed>0.){
        require(cpu.rejectsLockedStep(1.5*gradient),"CPU accepted an excessive gradient-limited step");
        require(gpu.rejectsLockedStep(1.5*gradient),"GPU accepted an excessive gradient-limited step");
      }
      std::printf("%d,%d,%.9g,%.9g,%.17g,%.17g,%.17g,%.17g\n",int(tpi),int(evolving),k,speed,wave,pore,cpuStep,gpuStep);
    }
    return 0;
  }catch(const std::exception& e){std::fprintf(stderr,"FAIL %s\n",e.what());return 1;}
}
