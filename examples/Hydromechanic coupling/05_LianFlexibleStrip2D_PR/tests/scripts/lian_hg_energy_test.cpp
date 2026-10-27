// Frozen-geometry HG stiffness energy, NOT the coupled SPH integrator/history.
// Feed manufactured displacement through the real linear rate operator, then
// integrate an isolated oscillator with velocity Verlet. No pore/load/BC claim.
#include "JSphHourglassCpu.h"
#include "JSphHourglassGpu.h"
#include "JAppInfo.h"
#include <cuda_runtime.h>
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>

JAppInfo AppInfo("LianHgEnergy","bounded-r1","27-10-2026");
namespace{
const unsigned First=40,Nx=8,Nz=12,N=Nx*Nz;
const double Mass=20;
void Require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
void Cuda(cudaError_t e){Require(e==cudaSuccess,cudaGetErrorString(e));}
template<class T> struct Device{
  T* p=nullptr;
  Device(){Cuda(cudaMalloc(reinterpret_cast<void**>(&p),N*sizeof(T)));}
  ~Device(){cudaFree(p);}
  void Put(const std::vector<T>& v){Cuda(cudaMemcpy(p,v.data(),N*sizeof(T),cudaMemcpyHostToDevice));}
};
struct Operator{
  JSphHourglassCpu cpu;JSphHourglassGpu gpu;
  std::vector<unsigned> id;std::vector<typecode> code;std::vector<tdouble3> pos;
  std::vector<tfloat4> vel;std::vector<float> plastic;std::vector<tfloat3> ace;
  Device<unsigned> di;Device<typecode> dc;Device<double2> dx;Device<double> dz;
  Device<float4> dv;Device<float> dp;Device<float3> da;
  double maxrateerror=0,maxformerror=0,maxnet=0,maxwork=0;
  Operator():id(N),code(N,CODE_TYPE_FLUID),pos(N),vel(N),plastic(N,0),ace(N,TFloat3(0)){
    std::vector<double2> xy(N);std::vector<double> z(N);
    for(unsigned i=0;i<N;i++){
      id[i]=First+i;pos[i]=TDouble3((i%Nx+.5)*.125-1.25,0,(i/Nx+.5)*.125-.75);
      xy[i]=make_double2(pos[i].x,0);z[i]=pos[i].z;
    }
    di.Put(id);dc.Put(code);dx.Put(xy);dz.Put(z);dp.Put(plastic);
    std::vector<float3> zero(N,make_float3(0,0,0));da.Put(zero);
  }
  std::vector<tdouble3> Apply(const std::vector<tdouble3>& q,double dt){
    cpu.Config(First,N,.1,Mass,0,.1625,.325,-1,1e5);
    gpu.Config(First,N,.1,Mass,0,.1625,.325,-1,1e5);
    std::vector<float4> v(N);
    for(unsigned i=0;i<N;i++){vel[i]=TFloat4(float(q[i].x),0,float(q[i].z),2000);v[i]=make_float4(vel[i].x,0,vel[i].z,2000);}
    dv.Put(v);
    cpu.PredictorForce(N,0,id.data(),code.data(),pos.data(),vel.data(),plastic.data(),ace.data(),dt);
    gpu.PredictorForce(N,0,di.p,dc.p,dx.p,dz.p,dv.p,dp.p,da.p,dt);
    Cuda(cudaGetLastError());Cuda(cudaDeviceSynchronize());
    std::vector<tdouble3> result(N);
    for(unsigned i=0;i<N;i++){
      result[i]=cpu.GetRate(First+i);const auto r=gpu.GetRate(First+i);
      const double error=std::hypot(r.x-result[i].x,r.z-result[i].z);
      maxrateerror=(std::max)(maxrateerror,error);
      Require(error<=1e-8*(1+std::hypot(result[i].x,result[i].z)),"CPU/GPU stiffness mismatch");
    }
    const auto a=cpu.GetRateInfo(),b=gpu.GetRateInfo();
    maxformerror=(std::max)(maxformerror,std::abs(a.form-b.form));
    Require(std::abs(a.form-b.form)<=1e-8*(1+std::abs(a.form)),"CPU/GPU potential mismatch");
    maxnet=(std::max)({maxnet,std::hypot(a.netx,a.netz),std::hypot(b.netx,b.netz)});
    maxwork=(std::max)({maxwork,a.workerror,b.workerror});
    Require(std::hypot(a.netx,a.netz)<=1e-9*(1+a.sumrate),"CPU stiffness net force");
    Require(std::hypot(b.netx,b.netz)<=1e-9*(1+b.sumrate),"GPU stiffness net force");
    return result;
  }
};
}
int main(int argc,char** argv){
  if(argc!=2||std::filesystem::exists(argv[1])){std::cerr<<"Use lian_hg_energy NEW_CSV\n";return 2;}
  try{
    AppInfo.LogInit("");Cuda(cudaSetDevice(0));Operator op;
    std::vector<tdouble3> q(N,TDouble3(0)),v(N,TDouble3(0));
    for(unsigned i=0;i<N;i++)q[i].z=((i%Nx+i/Nx)%2?1:-1)*1e-4;
    auto a=op.Apply(q,1e-5);const double dt=.02*op.cpu.GetRateInfo().tau;
    const double initial=op.cpu.GetRateInfo().form;Require(initial>0,"Zero initial oscillator energy");
    std::ofstream f(argv[1]);f<<std::setprecision(17)<<"step,time_s,kinetic,potential,total_energy,energy_ratio\n";
    double minratio=1,maxratio=1;
    for(unsigned step=0;step<=128;step++){
      double kinetic=0;for(const auto& u:v)kinetic+=.5*Mass*(u.x*u.x+u.z*u.z);
      const double potential=op.cpu.GetRateInfo().form,total=kinetic+potential,ratio=total/initial;
      minratio=(std::min)(minratio,ratio);maxratio=(std::max)(maxratio,ratio);
      Require(std::isfinite(ratio)&&ratio>=.999&&ratio<=1.001,"Frozen oscillator energy exceeds original +/-0.1% bound");
      f<<step<<','<<step*dt<<','<<kinetic<<','<<potential<<','<<total<<','<<ratio<<'\n';
      if(step==128)break;
      for(unsigned i=0;i<N;i++){v[i].x+=.5*dt*a[i].x;v[i].z+=.5*dt*a[i].z;q[i].x+=dt*v[i].x;q[i].z+=dt*v[i].z;}
      a=op.Apply(q,dt);
      for(unsigned i=0;i<N;i++){v[i].x+=.5*dt*a[i].x;v[i].z+=.5*dt*a[i].z;}
    }
    f.flush();Require(bool(f),"Energy CSV write failed");
    std::cout<<std::setprecision(17)<<"PASS frozen bounded oscillator: minratio="<<minratio<<" maxratio="<<maxratio
      <<" maxrateerror="<<op.maxrateerror<<" maxformerror="<<op.maxformerror<<" maxnet="<<op.maxnet<<" maxwork="<<op.maxwork<<'\n';
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
