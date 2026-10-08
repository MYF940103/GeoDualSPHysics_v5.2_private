// Host fixture: all device integration/sorting code is linked production code.
#include "JSphGpu_ker.h"
#include "JCellDivGpu_ker.h"
#include "JDsDcellDef.h"
#include "JAppInfo.h"
#include <cuda_runtime.h>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("PoreDoubleGpuAcceptance","v1","09-09-2026");
static void Require(bool ok,const std::string& s){if(!ok)throw std::runtime_error(s);}
static void Cuda(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
static void Sync(){Cuda(cudaGetLastError());Cuda(cudaDeviceSynchronize());}
static bool Same(double a,double b){return std::memcmp(&a,&b,sizeof(double))==0;}
template<class T> class Device{
  unsigned n;T* p;
public:
  Device(unsigned size):n(size),p(NULL){Cuda(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*n));}
  ~Device(){if(p)cudaFree(p);}
  Device(const Device&)=delete;Device& operator=(const Device&)=delete;
  T* Ptr()const{return p;}
  void Put(const std::vector<T>& v){Require(v.size()==n,"Wrong upload size");Cuda(cudaMemcpy(p,v.data(),sizeof(T)*n,cudaMemcpyHostToDevice));}
  std::vector<T> Get()const{std::vector<T> v(n);Cuda(cudaMemcpy(v.data(),p,sizeof(T)*n,cudaMemcpyDeviceToHost));return v;}
};
class Fixture{
  Device<double> a,b,c;Device<float> rate;Device<typecode> code;
  double *p[3];unsigned current=0,pre=1,history=2,phase=0;
public:
  const unsigned np;unsigned npb=0;
  Fixture(const std::vector<double>& initial,const std::vector<float>& source):a(unsigned(initial.size())),b(unsigned(initial.size())),c(unsigned(initial.size())),rate(unsigned(initial.size())),code(unsigned(initial.size())),np(unsigned(initial.size())){
    p[0]=a.Ptr();p[1]=b.Ptr();p[2]=c.Ptr();a.Put(initial);b.Put(initial);c.Put(initial);rate.Put(source);code.Put(std::vector<typecode>(np,CODE_TYPE_FLUID));
  }
  std::vector<double> Read()const{std::vector<double> v(np);Cuda(cudaMemcpy(v.data(),p[current],sizeof(double)*np,cudaMemcpyDeviceToHost));return v;}
  void SeedHistory(const std::vector<double>& initial,const std::vector<float>& source,double dt){auto v=initial;for(unsigned i=0;i<np;i++)v[i]-=dt*double(source[i]);c.Put(v);}
  void Predictor(double dt){Cuda(cudaMemcpy(p[pre],p[current],sizeof(double)*np,cudaMemcpyDeviceToDevice));cusph::UpdatePorePressureSymplectic(np,npb,dt*.5,code.Ptr(),p[pre],rate.Ptr(),p[current]);Sync();}
  void Corrector(double dt){cusph::UpdatePorePressureSymplectic(np,npb,dt,code.Ptr(),p[pre],rate.Ptr(),p[current]);Sync();}
  void Verlet(double dt){phase++;const unsigned old=phase<40?history:current;cusph::UpdatePorePressureVerlet(np,npb,phase<40?dt+dt:dt,code.Ptr(),p[old],rate.Ptr(),p[history]);Sync();if(phase>=40)phase=0;std::swap(current,history);}
  void Step(double dt,bool verlet){if(verlet)Verlet(dt);else{Predictor(dt);Corrector(dt);}}
  void Restore(const Fixture& other){phase=other.phase;Cuda(cudaMemcpy(p[current],other.p[other.current],sizeof(double)*np,cudaMemcpyDeviceToDevice));Cuda(cudaMemcpy(p[history],other.p[other.history],sizeof(double)*np,cudaMemcpyDeviceToDevice));}
  void Boundary(bool byindex){npb=byindex?np:0;code.Put(std::vector<typecode>(np,byindex?CODE_TYPE_FLUID:CODE_TYPE_FIXED));}
  void Poison(){Cuda(cudaMemset(p[current],0,sizeof(double)*np));}
};
struct Result{std::string scheme;double initial,dt,value=0,analytic=0,pre_error=0,full_error=0,tolerance=0;float rate;unsigned steps,mismatches=0;bool pass=false;};
static std::vector<Result> Evaluate(unsigned d,bool verlet,unsigned stepLimit=0){
  const double dts[]={625e-9,250e-9,125e-9,62.5e-9};const unsigned counts[]={800,2000,4000,8000};
  const double dt=dts[d];const unsigned steps=(stepLimit?stepLimit:counts[d]);std::vector<double> initial;std::vector<float> rates;
  for(double p:{0.,10000.,20000.})for(float r:{0.f,1.f,-1.f,1e3f,-1e3f,1e4f,-1e4f,1e7f,-1e7f}){initial.push_back(p);rates.push_back(r);}
  if(d==3){initial.push_back(20000.0003);rates.push_back(0);}
  Fixture run(initial,rates),resume(initial,rates);if(verlet)run.SeedHistory(initial,rates,dt);
  const unsigned np=unsigned(initial.size());std::vector<Result> result(np);
  for(unsigned p=0;p<np;p++){auto& r=result[p];r.scheme=verlet?"Verlet_valid_history":"Symplectic";r.initial=initial[p];r.rate=rates[p];r.dt=dt;r.steps=steps;}
  for(unsigned step=1;step<=steps;step++){
    if(verlet)run.Verlet(dt);
    else{run.Predictor(dt);const auto pred=run.Read();for(unsigned p=0;p<np;p++)result[p].pre_error=(std::max)(result[p].pre_error,std::abs(pred[p]-(initial[p]+(step-.5)*dt*double(rates[p]))));run.Corrector(dt);}
    const auto value=run.Read();
    for(unsigned p=0;p<np;p++){result[p].value=value[p];result[p].full_error=(std::max)(result[p].full_error,std::abs(value[p]-(initial[p]+step*dt*double(rates[p]))));}
    if(step==steps/2)resume.Restore(run);
    else if(step>steps/2){resume.Step(dt,verlet);const auto restored=resume.Read();for(unsigned p=0;p<np;p++)if(!Same(value[p],restored[p]))result[p].mismatches++;}
  }
  for(auto& r:result){r.analytic=r.initial+steps*dt*double(r.rate);const double scale=(std::max)(1.,(std::max)(std::abs(r.initial),std::abs(r.analytic)));r.tolerance=(std::max)(1e-10,16.*steps*std::numeric_limits<double>::epsilon()*scale);r.pass=std::isfinite(r.value)&&!r.mismatches&&r.pre_error<=r.tolerance&&r.full_error<=r.tolerance;}
  return result;
}
struct Check{std::string name;bool pass;};
static void Test(std::vector<Check>& checks,const std::string& name,const std::function<void()>& action){try{action();checks.push_back({name,true});}catch(const std::exception& e){checks.push_back({name,false});std::cerr<<name<<": "<<e.what()<<'\n';}}
static void MixedChecks(std::vector<Check>& checks){
  for(bool verlet:{false,true})for(bool alias:{false,true})Test(checks,
    std::string(verlet?"Verlet":"Symplectic")+(alias?"_mixed_alias_guard":"_mixed_copy_guard"),[&](){
      const unsigned np=1031,nb=3,size=np+5;
      Device<double> old(size),output(size);Device<float> rate(size);Device<typecode> code(size);
      std::vector<double> initial(size),sentinel(size,-999.123456789);
      std::vector<float> source(size);std::vector<typecode> codes(size,CODE_TYPE_FLUID);
      for(unsigned p=0;p<size;p++){
        initial[p]=20000.+.125*p+.000001*double(p+1);source[p]=(p%2?-1.f:1.f)*10000.f;
        if(p>=nb){
          switch(p%5){case 0:codes[p]=CODE_TYPE_FIXED;break;case 1:codes[p]=CODE_TYPE_MOVING;break;
            case 2:codes[p]=CODE_TYPE_FLOATING;break;case 3:codes[p]=CODE_SetPeriodic(CODE_TYPE_FLUID);break;}
        }
      }
      old.Put(initial);output.Put(sentinel);rate.Put(source);code.Put(codes);
      const double dt=62.5e-9;
      double* dest=(alias?old.Ptr():output.Ptr());
      if(verlet)cusph::UpdatePorePressureVerlet(np,nb,dt,code.Ptr(),old.Ptr(),rate.Ptr(),dest);
      else cusph::UpdatePorePressureSymplectic(np,nb,dt,code.Ptr(),old.Ptr(),rate.Ptr(),dest);
      Sync();const auto actual=(alias?old.Get():output.Get());
      for(unsigned p=0;p<size;p++){
        const double expected=(p>=np?(alias?initial[p]:sentinel[p]):
          p<nb || !CODE_IsFluid(codes[p])?initial[p]:initial[p]+dt*double(source[p]));
        Require(Same(actual[p],expected),"Mixed index/type filtering, alias update or tail guard differs");
      }
      if(!alias){const auto unchanged=old.Get();for(unsigned p=0;p<size;p++)Require(Same(unchanged[p],initial[p]),"Source overwritten");}
    });
}
static void PeriodicChecks(std::vector<Check>& checks){
  StCteInteraction cte={};cte.scell=1.f;cte.axis=MGDIV_Z;cte.cellcode=DCEL_GetCode(10,10,11);
  cusph::CteInteractionUp(&cte);Sync();
  for(unsigned mode=0;mode<3;mode++)for(bool hydro:{false,true})Test(checks,
    std::string(mode==0?"Verlet":mode==1?"Symplectic_pre":"Symplectic_no_pre")+(hydro?"_periodic_double":"_periodic_null_pore"),[&](){
      const unsigned size=9,pini=4,n=3;
      Device<unsigned> ids(size),cells(size),list(n);Device<typecode> codes(size);
      Device<double2> xy(size),xypre(size);Device<double> z(size),zpre(size),pore(size),reference(size),history(size);
      Device<float4> vel(size),velpre(size);Device<float> rate(size);
      Device<tsymatrix3f> sigma(size),sigmapre(size);
      std::vector<unsigned> hi(size),hcells(size,0);
      std::vector<typecode> hcode(size,CODE_TYPE_FLUID);
      std::vector<double2> hxy(size),hxypre(size);
      std::vector<double> hz(size),hzpre(size),hpore(size),hreference(size),hhistory(size);
      std::vector<float> hrate(size);std::vector<float4> hvel(size),hvelpre(size);
      std::vector<tsymatrix3f> hsigma(size),hsigmapre(size);
      for(unsigned p=0;p<size;p++){
        hi[p]=10+p;hxy[p]=make_double2(2.+3.*p,3.+3.*p);hz[p]=4.+3.*p;
        hxypre[p]=make_double2(hxy[p].x-.25,hxy[p].y-.5);hzpre[p]=hz[p]-.75;
        hpore[p]=20000.+.125*p+.000001*double(p+1);hreference[p]=15000.+.125*p+.000003*double(p+1);
        hhistory[p]=hpore[p]-.000625;hrate[p]=float(p+1);
        hvel[p]=make_float4(float(p),2,3,2100);hvelpre[p]=make_float4(float(p),-2,-3,2099);
        hsigma[p]={};hsigma[p].xx=float(p+1);hsigma[p].xz=float(p+2);
        hsigmapre[p]={};hsigmapre[p].xx=float(p+3);hsigmapre[p].xz=float(p+4);
      }
      hcode[1]=CODE_TYPE_FIXED;
      ids.Put(hi);cells.Put(hcells);codes.Put(hcode);list.Put({0,0x80000002u,1});
      xy.Put(hxy);z.Put(hz);xypre.Put(hxypre);zpre.Put(hzpre);vel.Put(hvel);velpre.Put(hvelpre);
      pore.Put(hpore);reference.Put(hreference);history.Put(hhistory);rate.Put(hrate);sigma.Put(hsigma);sigmapre.Put(hsigmapre);
      if(mode==0)cusph::PeriodicDuplicateVerlet(n,pini,TUint3(16),TDouble3(1,.5,2),list.Ptr(),ids.Ptr(),codes.Ptr(),cells.Ptr(),
        xy.Ptr(),z.Ptr(),vel.Ptr(),NULL,velpre.Ptr(),sigma.Ptr(),sigmapre.Ptr(),hydro?pore.Ptr():NULL,
        hydro?reference.Ptr():NULL,hydro?rate.Ptr():NULL,hydro?history.Ptr():NULL);
      else cusph::PeriodicDuplicateSymplectic(n,pini,TUint3(16),TDouble3(1,.5,2),list.Ptr(),ids.Ptr(),codes.Ptr(),cells.Ptr(),
        xy.Ptr(),z.Ptr(),vel.Ptr(),NULL,mode==1?xypre.Ptr():NULL,mode==1?zpre.Ptr():NULL,mode==1?velpre.Ptr():NULL,
        sigma.Ptr(),mode==1?sigmapre.Ptr():NULL,hydro?pore.Ptr():NULL,hydro?reference.Ptr():NULL,
        hydro?rate.Ptr():NULL,hydro?history.Ptr():NULL);
      Sync();const auto op=pore.Get(),oref=reference.Get(),oh=history.Get(),oz=z.Get(),ozpre=zpre.Get();
      const auto oi=ids.Get(),ocell=cells.Get();const auto oc=codes.Get();const auto ox=xy.Get(),oxpre=xypre.Get();const auto orate=rate.Get();
      const auto ov=vel.Get(),ovpre=velpre.Get();const auto os=sigma.Get(),ospre=sigmapre.Get();
      const unsigned from[3]={0,2,1};
      for(unsigned p=0;p<size;p++){
        const bool copied=(p>=pini && p<pini+n);const unsigned src=copied?from[p-pini]:p;
        const double sign=(p==pini+1?-1.:1.);
        Require(Same(op[p],hpore[hydro?src:p]) && Same(oref[p],hreference[hydro?src:p]),"Periodic current/reference state lost bits");
        Require(Same(oh[p],hhistory[hydro && mode!=2?src:p]),"Periodic history state lost bits or no-pre branch wrote history");
        Require(orate[p]==hrate[hydro?src:p],"Periodic float rate copied incorrectly");
        Require(oi[p]==hi[src] && oc[p]==(copied?CODE_SetPeriodic(hcode[src]):hcode[p]),"Periodic ID/code mapping differs");
        Require(Same(ox[p].x,hxy[src].x+(copied?sign:0.)) && Same(ox[p].y,hxy[src].y+(copied?sign*.5:0.))
          && Same(oz[p],hz[src]+(copied?sign*2.:0.)),"Periodic forward/inverse position differs");
        const unsigned expectedcell=copied?DCEL_Cell(cte.cellcode,unsigned(ox[p].x),unsigned(ox[p].y),unsigned(oz[p])):hcells[p];
        Require(ocell[p]==expectedcell,"Periodic cell mapping differs");
        Require(std::memcmp(&ov[p],&hvel[src],sizeof(float4))==0 && std::memcmp(&os[p],&hsigma[src],sizeof(tsymatrix3f))==0,"Periodic mechanical state copy changed");
        const unsigned oldsrc=(mode!=2?src:p);
        Require(std::memcmp(&ovpre[p],&hvelpre[oldsrc],sizeof(float4))==0 && std::memcmp(&ospre[p],&hsigmapre[oldsrc],sizeof(tsymatrix3f))==0,"Periodic mechanical history copy changed");
        const unsigned possrc=(mode==1?src:p);
        Require(Same(oxpre[p].x,hxypre[possrc].x) && Same(oxpre[p].y,hxypre[possrc].y) && Same(ozpre[p],hzpre[possrc]),"Periodic position history copy changed");
      }
    });
}
int main(int argc,char** argv){
  try{
    Require((argc==3 || argc==4)&&std::string(argv[1])=="--json"&&(argc==3 || std::string(argv[3])=="--memory-smoke"),"Usage: gpu_state_harness --json NEW.json [--memory-smoke]");
    const bool memorySmoke=(argc==4);
    Require(!std::filesystem::exists(argv[2]),"Refusing overwrite");Cuda(cudaSetDevice(0));
    cudaDeviceProp properties;Cuda(cudaGetDeviceProperties(&properties,0));
    std::vector<Result> results;std::vector<Check> checks;
    for(bool verlet:{false,true})for(unsigned d=0;d<4;d++)if(!memorySmoke || d==3){auto batch=Evaluate(d,verlet,memorySmoke?4u:0u);results.insert(results.end(),batch.begin(),batch.end());std::cout<<"BATCH "<<(verlet?"Verlet":"Symplectic")<<" dt_index="<<d<<std::endl;}
    for(bool verlet:{false,true})for(bool byindex:{false,true})Test(checks,std::string(verlet?"Verlet":"Symplectic")+(byindex?"_boundary_copy":"_nonfluid_copy"),[&](){Fixture f({20000.0003},{1e7f});f.Boundary(byindex);f.Step(62.5e-9,verlet);Require(Same(f.Read()[0],20000.0003),"Copy lost double state");});
    Test(checks,"corrector_uses_Pre_not_predictor",[&](){Fixture f({20000.0003},{1e7f});f.Predictor(250e-9);f.Poison();f.Corrector(250e-9);Require(Same(f.Read()[0],20002.5003),"Wrong correction time layer");});
    for(unsigned pini:{0u,2u,6u})Test(checks,"double_sort_pini_"+std::to_string(pini),[&](){
      Device<unsigned> order(6);Device<double> source(6),dest(6);const std::vector<double> values={20000.000001,21000.000002,22000.000003,23000.000004,24000.000005,25000.000006};
      const std::vector<unsigned> ids=pini?std::vector<unsigned>{0,1,5,2,4,3}:std::vector<unsigned>{5,2,0,4,1,3};order.Put(ids);source.Put(values);dest.Put(std::vector<double>(6,-1.));
      cudiv::SortDataParticles(6,pini,order.Ptr(),source.Ptr(),dest.Ptr());Sync();const auto actual=dest.Get();
      for(unsigned i=0;i<6;i++)Require(Same(actual[i],values[i<pini?i:ids[i]]),"Double sort lost precision or mapping");
    });
    MixedChecks(checks);PeriodicChecks(checks);
    unsigned failures=0;for(const auto& r:results)if(!r.pass)failures++;for(const auto& c:checks){if(!c.pass)failures++;std::cout<<(c.pass?"PASS ":"FAIL ")<<c.name<<'\n';}
    std::ofstream out(argv[2]);Require(bool(out),"Cannot create result");out<<std::setprecision(17)<<"{\"completed\":true,\"passed\":"<<(failures?"false":"true")<<",\"failure_count\":"<<failures<<",\"memory_smoke\":"<<(memorySmoke?"true":"false")<<",\"integration_case_count\":"<<results.size()<<",\"check_count\":"<<checks.size()<<",\"device\":\""<<properties.name<<"\",\"scope\":\"Actual GPU pressure kernels, double scalar sort and periodic state copies, frozen float rates; not coupled convergence or full solver restart equivalence. Memory-smoke mode keeps all mapping/guard checks but limits integration to four steps at the smallest timestep.\",\"cases\":[";
    for(size_t i=0;i<results.size();i++){const auto& r=results[i];if(i)out<<',';out<<"{\"scheme\":\""<<r.scheme<<"\",\"initial_pa\":"<<r.initial<<",\"rate_pa_s\":"<<r.rate<<",\"dt_s\":"<<r.dt<<",\"steps\":"<<r.steps<<",\"value_pa\":"<<r.value<<",\"analytic_pa\":"<<r.analytic<<",\"error_pa\":"<<r.value-r.analytic<<",\"max_predictor_error_pa\":"<<r.pre_error<<",\"max_full_error_pa\":"<<r.full_error<<",\"tolerance_pa\":"<<r.tolerance<<",\"resume_bit_mismatches\":"<<r.mismatches<<",\"pass\":"<<(r.pass?"true":"false")<<'}';}
    out<<"],\"checks\":[";for(size_t i=0;i<checks.size();i++){if(i)out<<',';out<<"{\"name\":\""<<checks[i].name<<"\",\"pass\":"<<(checks[i].pass?"true":"false")<<'}';}out<<"]}\n";out.flush();Require(bool(out),"JSON write failed");
    std::cout<<"COMPLETE cases="<<results.size()<<" checks="<<checks.size()<<" failures="<<failures<<'\n';return failures?1:0;
  }catch(const std::exception& e){std::cerr<<"HARNESS ERROR: "<<e.what()<<'\n';return 2;}
}
