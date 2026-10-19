// Exercise real CPU/GPU host event predicates, including accumulated time error.
#include "JSphCpuSingle.h"
#include "JSphGpuSingle.h"
#include "JDsFixedDt.h"
#include "JAppInfo.h"
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>

JAppInfo AppInfo("DrainageEventCheck","v1","18-10-2026");
static void Check(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
template<class Base> class Probe:public Base{
public:
  void Configure(double dt,double event){
    delete this->FixedDt;this->FixedDt=new JDsFixedDt(dt);
    this->HydroMech=true;this->HydroMechDrainage=true;this->HydroMechDrainageStartTime=event;
  }
  bool At(unsigned step,double time,bool grid){
    this->Nstep=step;this->TimeStep=time;this->HydroMechDrainageFixedGrid=grid;
    return this->IsHydroMechDrainageActive();
  }
  bool Disabled(bool hydro){this->HydroMech=hydro;this->HydroMechDrainage=!hydro;return this->IsHydroMechDrainageActive();}
};
int main(int argc,char** argv){
  try{
    Check(argc==2,"Use event_check FRESH_RESULT_JSON");
    Probe<JSphCpuSingle> cpu;Probe<JSphGpuSingle> gpu;
    unsigned samples=0,aligned_early_corrections=0;
    for(double dt:{1e-5,5e-6})for(double event:{0.,.001,.01}){
      cpu.Configure(dt,event);gpu.Configure(dt,event);
      const unsigned index=unsigned(std::llround(event/dt));double time=0;
      for(unsigned step=0;step<=index+2;step++){
        const bool raw=time>=event,expected=step>=index;
        Check(cpu.At(step,time,false)==raw&&gpu.At(step,time,false)==raw,"Event-off path changed");
        const bool c=cpu.At(step,time,true),g=gpu.At(step,time,true);
        Check(c==expected&&g==c,"CPU/GPU event alignment differs at actual accumulated time");
        if(c&&!raw)aligned_early_corrections++;
        samples++;time+=dt;
      }
      if(event>0){
        Check(!cpu.At(index,event-1e-4,true)&&!gpu.At(index,event-1e-4,true),"Grid policy concealed a non-roundoff time lag");
        Check(!cpu.At(index-1,event-dt,true)&&!gpu.At(index-1,event-dt,true),"Drainage activated before event step");
      }
      Check(!cpu.Disabled(false)&&!gpu.Disabled(false)&&!cpu.Disabled(true)&&!gpu.Disabled(true),"Disabled hydromechanics/drainage activated");
    }
    std::ifstream old(argv[1]);Check(!old.good(),"Result exists");
    std::ofstream out(argv[1]);out<<"{\"passed\":true,\"samples\":"<<samples<<",\"aligned_roundoff_corrections\":"<<aligned_early_corrections
      <<",\"dt\":[0.00001,0.000005],\"events\":[0,0.001,0.01],\"cpu_gpu_predicates_equal\":true,\"off_path_unchanged\":true,\"coupled_validation\":false}\n";
    out.flush();Check(bool(out),"Result write failed");return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Production exception\n";return 2;}
}
