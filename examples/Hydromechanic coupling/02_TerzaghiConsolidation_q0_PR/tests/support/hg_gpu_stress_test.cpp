// G1 preparation: host fixture calling the authoritative GPU project's kernels.
// Requires the planned double stress interfaces; not compilable against float G1.
// No copied CUDA integrator/constitutive algorithm and no coupled solver run.
#include "JSphGpuSingle.h"
#include "JSphGpuSimple_ker.h"
#include "JSphGpu_ker.h"
#include "JArraysGpu.h"
#include "JCellDivGpu.h"
#include "JDsDcellDef.h"
#include "JDsGauge_ker.h"
#include "JAppInfo.h"
#include "JLog2.h"
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
#include <sstream>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

JAppInfo AppInfo("HgGpuStressTest","G1-prepared","16-10-2026");
static_assert(sizeof(tsymatrix3d)==48,"Six double stress components required");
// These are the real CPU functions linked from JSphCpu.obj, not test replicas.
void ConsRelationEP_fast(tsymatrix3d,const float,const float,const float,const float,
  const float,float,tsymatrix3d&,float&);
void ConsRelationEPsft_fast(tsymatrix3d,const float,const float,const float,const float,
  const float,const float,const float,const float,const float,const TpDPCtes,
  float,tsymatrix3d&,float&);
void UpdateDPvars(float&,float&,float&,const float,const float,const float,
  const float,const float,const float,const float,const float,const TpDPCtes);

static void Require(bool ok,const std::string& s){if(!ok)throw std::runtime_error(s);}
static void Cuda(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
static void Sync(){Cuda(cudaGetLastError());Cuda(cudaDeviceSynchronize());}
template<class T> static bool Same(const T& a,const T& b){return std::memcmp(&a,&b,sizeof(T))==0;}
template<class T> static void Put(T* p,const std::vector<T>& v){Cuda(cudaMemcpy(p,v.data(),sizeof(T)*v.size(),cudaMemcpyHostToDevice));}
template<class T> static std::vector<T> Get(const T* p,unsigned n){std::vector<T> v(n);Cuda(cudaMemcpy(v.data(),p,sizeof(T)*n,cudaMemcpyDeviceToHost));return v;}
template<class T> struct Device{
  T* p=nullptr;unsigned n;
  explicit Device(unsigned size):n(size){Cuda(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*n));}
  ~Device(){if(p)cudaFree(p);}
  Device(const Device&)=delete;Device& operator=(const Device&)=delete;
  void Put(const std::vector<T>& v){Require(v.size()==n,"Upload size");::Put(p,v);}
  std::vector<T> Get()const{return ::Get(p,n);}
};
static tsymatrix3d Marker(unsigned id){
  return TSymMatrix3d(-10000.-id-std::ldexp(1.,-20),1000.+id+std::ldexp(1.,-24),
    -2000.-id-std::ldexp(1.,-23),-11000.-id-std::ldexp(1.,-19),
    3000.+id+std::ldexp(1.,-22),-12000.-id-std::ldexp(1.,-21));
}
static std::vector<double> Components(const tsymatrix3d& s){return {s.xx,s.xy,s.xz,s.yy,s.yz,s.zz};}
static double MaxAbs(const tsymatrix3d& s){double m=0;for(double v:Components(s))m=(std::max)(m,std::abs(v));return m;}
struct Metric{std::string name;double error,tolerance;};
static std::vector<Metric> Metrics;
static void Near(const std::string& name,double error,double tolerance){
  Metrics.push_back({name,error,tolerance});
  std::ostringstream s;s<<std::setprecision(17)<<name<<" error="<<error<<" tolerance="<<tolerance;
  Require(std::isfinite(error)&&error<=tolerance,s.str());
}
static void Tensor(const std::string& name,const tsymatrix3d& a,const tsymatrix3d& b,double tolerance){
  double error=0;const auto x=Components(a),y=Components(b);
  for(unsigned c=0;c<6;c++){Require(std::isfinite(x[c])&&std::isfinite(y[c]),name+" nonfinite component");error=(std::max)(error,std::abs(x[c]-y[c]));}
  Near(name,error,tolerance);
}
static StSoilCte Material(bool plastic){
  StSoilCte m={};m.ModulusK=2000000.f;m.ModulusG=750000.f;
  m.phi=.4f;m.phi_r=.2f;m.n_phi=3.f;m.dlt=.1f;
  m.coh=plastic?5000.f:1000000.f;m.coh_r=plastic?1000.f:500000.f;m.n_coh=10.f;m.SoilTriggerFos=1;
  return m;
}

// Only fixture plumbing: all stress evolution below is performed by production
// ComputeStep* wrappers. Rates, zero acceleration/density rate are prescribed.
class StepFixture{
public:
  unsigned n,nb=0;
  Device<float4> velocity,velocityout;
  Device<float> ar,kold,knew,kdelta;
  Device<float3> ace;
  Device<tsymatrix3f> rate;
  Device<typecode> code;
  Device<double2> movxy;Device<double> movz;
  explicit StepFixture(unsigned size):n(size),velocity(n),velocityout(n),ar(n),kold(n),knew(n),kdelta(n),ace(n),rate(n),code(n),movxy(n),movz(n){
    velocity.Put(std::vector<float4>(n,make_float4(0,0,0,2100)));velocityout.Put(velocity.Get());
    ar.Put(std::vector<float>(n,0));kold.Put(std::vector<float>(n,0));knew.Put(std::vector<float>(n,0));kdelta.Put(std::vector<float>(n,0));
    ace.Put(std::vector<float3>(n,make_float3(0,0,0)));rate.Put(std::vector<tsymatrix3f>(n,TSymMatrix3f()));
    code.Put(std::vector<typecode>(n,CODE_TYPE_FLUID));
  }
  void Call(unsigned scheme,const tsymatrix3d* old,tsymatrix3d* output,double dt,double dt2,TpDPCtes dp=DP_PS,bool floating=false){
    const tfloat3 gravity=TFloat3(0);
    if(scheme==0)cusphs::ComputeStepVerlet(floating,false,false,dp,MDBC2_None,n,nb,velocity.p,velocity.p,
      old,kold.p,rate.p,ar.p,ace.p,nullptr,nullptr,nullptr,dt,dt2,2100,1000,3000,gravity,
      code.p,movxy.p,movz.p,velocityout.p,output,knew.p,kdelta.p,nullptr);
    else if(scheme==1)cusphs::ComputeStepSymplecticPre(floating,false,false,dp,n,nb,velocity.p,ar.p,ace.p,nullptr,
      old,kold.p,rate.p,nullptr,dt*.5,2100,1000,3000,gravity,code.p,movxy.p,movz.p,velocityout.p,output,knew.p,kdelta.p,nullptr);
    else cusphs::ComputeStepSymplecticCor(floating,false,false,dp,MDBC2_None,n,nb,velocity.p,ar.p,ace.p,nullptr,
      old,kold.p,rate.p,nullptr,nullptr,dt*.5,dt,2100,1000,3000,gravity,code.p,movxy.p,movz.p,velocityout.p,output,knew.p,kdelta.p,nullptr);
    Sync();
  }
};

static void Accumulation(bool verlet,bool softening,unsigned steps){
  const auto mat=Material(false);cusphs::CteInteractionUpTStep(&mat,softening?1:0,0);Sync();
  const double dt=1.e-5;const unsigned n=7;
  const tsymatrix3f rate={-43.f,3.f,-7.f,-19.f,11.f,-31.f};
  StepFixture f(n);f.rate.Put(std::vector<tsymatrix3f>(n,rate));
  Device<tsymatrix3d> a(n),b(n),base(n);std::vector<tsymatrix3d> initial(n),previous(n);
  for(unsigned p=0;p<n;p++){initial[p]=Marker(p);previous[p]=initial[p]+ToTSymMatrix3d(rate)*(-dt);}
  a.Put(initial);b.Put(previous);tsymatrix3d* current=a.p;tsymatrix3d* history=b.p;
  Require(float(double(float(initial[0].xx))+rate.xx*dt)==float(initial[0].xx),"Float control must lose the small increment");
  const std::string label=std::string(verlet?"Verlet":"Symplectic")+(softening?"_softening":"_elastic");
  for(unsigned step=1;step<=steps;step++){
    if(verlet){const bool reset=(step%40==0);f.Call(0,reset?current:history,history,dt,reset?dt:2*dt);std::swap(current,history);}
    else{
      Cuda(cudaMemcpy(base.p,current,sizeof(tsymatrix3d)*n,cudaMemcpyDeviceToDevice));f.Call(1,base.p,current,dt,dt);
      if(step==1){Tensor(label+"_predictor",::Get(current,1)[0],initial[0]+ToTSymMatrix3d(rate)*(dt*.5),1.e-10);
        Require(Same(base.Get()[0],initial[0]),"Predictor overwrote original state");
        Cuda(cudaMemset(current,0,sizeof(tsymatrix3d)*n));} // Corrector must use original base, not predictor stress.
      f.Call(2,base.p,current,dt,dt);
    }
  }
  const auto result=::Get(current,n);
  const double tolerance=(std::max)(1.e-10,16.*steps*std::numeric_limits<double>::epsilon()*MaxAbs(initial[0]));
  for(unsigned p=0;p<n;p++)Tensor(label+"_accum_"+std::to_string(p),result[p],initial[p]+ToTSymMatrix3d(rate)*(steps*dt),tolerance);
  f.rate.Put(std::vector<tsymatrix3f>(n,TSymMatrix3f()));
  // Explicit one-step Verlet branch removes the old staggered nonzero-rate history.
  if(verlet){f.Call(0,current,history,dt,dt);std::swap(current,history);}
  const auto zero=::Get(current,n);
  for(unsigned k=0;k<20;k++){
    if(verlet){f.Call(0,current,history,dt,dt);std::swap(current,history);}
    else{Cuda(cudaMemcpy(base.p,current,sizeof(tsymatrix3d)*n,cudaMemcpyDeviceToDevice));f.Call(1,base.p,current,dt,dt);f.Call(2,base.p,current,dt,dt);}
  }
  const auto final=::Get(current,n);for(unsigned p=0;p<n;p++)Require(Same(zero[p],final[p]),label+" zero rate loses low bits");
}

static void Constitutive(){
  const tsymatrix3d states[]={Marker(0),TSymMatrix3d(-10000.,20000.,-5000.,-12000.,3500.,-8000.),
    TSymMatrix3d(11000.,3000.,-1000.,10000.,500.,9000.)};
  for(bool soft:{false,true})for(TpDPCtes dp:{DP_C,DP_MC,DP_PS}){
    const auto mat=Material(true);cusphs::CteInteractionUpTStep(&mat,soft?1:0,0);Sync();
    StepFixture f(3);f.kold.Put(std::vector<float>(3,.001f));Device<tsymatrix3d> old(3),out(3);
    old.Put(std::vector<tsymatrix3d>(states,states+3));out.Put(old.Get());f.Call(2,old.p,out.p,1.e-5,1.e-5,dp);
    const auto actual=out.Get();const auto kp=f.knew.Get();
    for(unsigned p=0;p<3;p++){
      tsymatrix3d expected;float expectedkp=0;
      if(soft)ConsRelationEPsft_fast(states[p],mat.ModulusK,mat.ModulusG,mat.phi,mat.phi_r,mat.n_phi,
        mat.coh,mat.coh_r,mat.n_coh,mat.dlt,dp,.001f,expected,expectedkp);
      else{float alpha,kc,beta;UpdateDPvars(alpha,kc,beta,mat.phi,mat.phi,0,mat.coh,mat.coh,0,mat.dlt,0,dp);
        ConsRelationEP_fast(states[p],mat.ModulusK,mat.ModulusG,alpha,kc,beta,.001f,expected,expectedkp);}
      const std::string label="return_"+std::to_string(soft)+"_dp"+std::to_string(unsigned(dp))+"_state"+std::to_string(p);
      // Float material coefficients / CUDA fast-math remain production behavior.
      // This is not a 0-ULP requirement on nonlinear CPU-vs-GPU arithmetic.
      const double tolerance=32.*std::numeric_limits<float>::epsilon()*(std::max)(1.,MaxAbs(expected));
      Tensor(label,actual[p],expected,tolerance);
      Near(label+"_kplastic",std::abs(double(kp[p])-expectedkp),32.*std::numeric_limits<float>::epsilon()*(std::max)(1.e-6,std::abs(double(expectedkp))));
      if(expectedkp==.001f)Require(Same(actual[p],states[p]),"Elastic return mapping truncated double state");
      else Require(kp[p]>.001f,"Plastic fixture did not exercise plastic increment");
    }
  }
}

static void IndexGuards(){
  const auto mat=Material(false);cusphs::CteInteractionUpTStep(&mat,0,0);Sync();
  const unsigned n=1031,size=n+5;std::vector<tsymatrix3d> initial(size);for(unsigned p=0;p<size;p++)initial[p]=Marker(p);
  for(unsigned scheme=0;scheme<3;scheme++){
    StepFixture f(size);f.n=n;f.nb=3;std::vector<typecode> codes(size,CODE_TYPE_FLUID);
    for(unsigned p=3;p<n;p++)if(p%3==0)codes[p]=CODE_TYPE_FLOATING;else if(p%3==1)codes[p]=CODE_SetPeriodic(CODE_TYPE_FLUID);
    f.code.Put(codes);const tsymatrix3f rate={-43.f,3.f,-7.f,-19.f,11.f,-31.f};f.rate.Put(std::vector<tsymatrix3f>(size,rate));
    Device<tsymatrix3d> source(size),dest(size);source.Put(initial);dest.Put(initial);f.Call(scheme,source.p,dest.p,1.e-5,1.e-5,DP_PS,true);
    const auto actual=dest.Get(),unchanged=source.Get();
    for(unsigned p=0;p<size;p++){
      Require(Same(unchanged[p],initial[p]),"Separate source was overwritten");
      if(p>=n || p<3 || !CODE_IsFluid(codes[p]))Require(Same(actual[p],initial[p]),"Index/type guard lost stress low bits");
      else Tensor("index_"+std::to_string(scheme)+"_"+std::to_string(p),actual[p],initial[p]+ToTSymMatrix3d(rate)*(scheme==1?5.e-6:1.e-5),1.e-10);
    }
  }
}

class SortFixture:public JCellDivGpu{
public:
  SortFixture():JCellDivGpu(true,false,0,4,1,true,CELLMODE_Full,1,TDouble3(0),TDouble3(16),TUint3(16),2,2,2,""){}
  void Configure(const std::vector<unsigned>& order,unsigned prefix){
    CheckMemoryNp(unsigned(order.size()));Nptot=unsigned(order.size());NpbFinal=prefix;DivideFull=(prefix==0);::Put(SortPart,order);
  }
};
static void PoolAndSort(){
  // TODO(G1 production): SIZE_48B, ReserveSymatrix3d, Free(double stress), and sort overload.
  JArraysGpu pool;pool.SetArrayCount(JArraysGpu::SIZE_48B,3);pool.SetArrayCount(JArraysGpu::SIZE_24B,1);pool.SetArraySize(1036);
  Require(pool.GetAllocMemoryGpu()==llong(1036)*(3*48+24),"48B pool accounting");
  auto a=pool.ReserveSymatrix3d();auto b=pool.ReserveSymatrix3d();auto c=pool.ReserveSymatrix3d();auto legacy=pool.ReserveSymatrix3f();
  std::vector<tsymatrix3d> initial(1036);for(unsigned p=0;p<initial.size();p++)initial[p]=Marker(p);::Put(a,initial);::Put(b,initial);::Put(c,initial);
  pool.Free(b);Require(pool.GetArrayCountUsed(JArraysGpu::SIZE_48B)==2,"Non-LIFO count");Require(pool.ReserveSymatrix3d()==b,"Non-LIFO recycle");
  SortFixture divider;
  for(unsigned prefix:{0u,3u,1031u}){
    std::vector<unsigned> order(1031);for(unsigned p=0;p<order.size();p++)order[p]=(p<prefix?p:prefix+(p-prefix+7)%(1031-prefix));
    divider.Configure(order,prefix);::Put(b,initial);divider.SortDataArrays(a,b);Sync();const auto sorted=::Get(b,1036);
    for(unsigned p=0;p<1036;p++)Require(Same(sorted[p],initial[p<1031?order[p]:p]),"48B full/fluid sort or excluded-tail guard");
  }
  pool.Free(a);pool.Free(b);pool.Free(c);pool.Free(legacy);pool.Free(static_cast<tsymatrix3d*>(nullptr));
  for(unsigned n:{19u,5u,0u,31u}){pool.SetArraySize(n);Require(pool.GetAllocMemoryGpu()==llong(n)*(3*48+24),"48B pool resizing/count");}
  pool.Reset();Require(pool.GetAllocMemoryGpu()==0,"48B pool reset");
}

static void Periodic(){
  StCteInteraction cte={};cte.scell=1;cte.axis=MGDIV_Z;cte.cellcode=DCEL_GetCode(10,10,11);cusph::CteInteractionUp(&cte);Sync();
  for(unsigned mode=0;mode<3;mode++){
    const unsigned n=8;Device<unsigned> ids(n),cells(n),list(2);Device<typecode> code(n);
    Device<double2> xy(n),xypre(n);Device<double> z(n),zpre(n);Device<float4> vel(n),velpre(n);
    Device<tsymatrix3d> stress(n),history(n);std::vector<unsigned> hi(n),hc(n,0);std::vector<tsymatrix3d> hs(n),hh(n);
    std::vector<double2> hx(n,make_double2(4,4));std::vector<double> hz(n,4);std::vector<float4> hv(n,make_float4(0,0,0,2100));
    for(unsigned p=0;p<n;p++){hi[p]=100+p;hs[p]=Marker(p);hh[p]=Marker(p+20);}
    ids.Put(hi);cells.Put(hc);list.Put({0,0x80000002u});code.Put(std::vector<typecode>(n,CODE_TYPE_FLUID));
    xy.Put(hx);xypre.Put(hx);z.Put(hz);zpre.Put(hz);vel.Put(hv);velpre.Put(hv);stress.Put(hs);history.Put(hh);
    if(mode==0)cusph::PeriodicDuplicateVerlet(2,4,TUint3(16),TDouble3(1,0,0),list.p,ids.p,code.p,cells.p,
      xy.p,z.p,vel.p,nullptr,velpre.p,stress.p,history.p,nullptr,nullptr,nullptr,nullptr);
    else cusph::PeriodicDuplicateSymplectic(2,4,TUint3(16),TDouble3(1,0,0),list.p,ids.p,code.p,cells.p,
      xy.p,z.p,vel.p,nullptr,mode==1?xypre.p:nullptr,mode==1?zpre.p:nullptr,mode==1?velpre.p:nullptr,
      stress.p,mode==1?history.p:nullptr,nullptr,nullptr,nullptr,nullptr);
    Sync();const auto actual=stress.Get(),old=history.Get();const auto oi=ids.Get();const auto oc=code.Get();const auto ox=xy.Get();
    for(unsigned p=0;p<n;p++){
      const bool copied=(p==4||p==5);const unsigned src=(p==4?0:p==5?2:p);
      Require(Same(actual[p],hs[src])&&Same(old[p],hh[mode==2?p:src]),"Periodic current/history/guard low bits");
      Require(oi[p]==hi[src]&&(!copied||CODE_IsPeriodic(oc[p])),"Periodic native ID association");
      Require(ox[p].x==hx[src].x+(p==4?1.:p==5?-1.:0.),"Periodic forward/inverse position");
    }
  }
}

static void ForceGauge(){
  // Independent one-neighbor result: r=h=1 gives grad(W)=bwen/8 along
  // each coordinate axis. mass/(rho_wall*rho_fluid)=2/(2*4)=1/4.
  // The two matrices (sigma_wall+sigma_fluid)/4 have these known columns.
  const float columns[2][3][3]={{{1,5,2},{5,9,3},{2,3,13}},{{3,8,6},{8,14,9},{6,9,20}}};
  const unsigned n=5,idbegin=40;const typecode selected=CODE_TYPE_FIXED;
  const std::vector<tsymatrix3d> stresses={
    TSymMatrix3d(8,12,16,20,24,28),TSymMatrix3d(16,24,32,40,48,56),
    Marker(50),Marker(51),TSymMatrix3d(-4,8,-8,16,-12,24)};
  // Duplicate native ID is periodic and must not race with the selected normal
  // particle. The other mk must leave output slot 2 untouched.
  const std::vector<unsigned> ids={40,41,40,42,100};
  const std::vector<typecode> codes={selected,selected,CODE_SetPeriodic(selected),typecode(selected+1),CODE_TYPE_FLUID};
  const unsigned orders[2][5]={{0,1,2,3,4},{4,3,1,2,0}};
  Device<double2> xy(n);Device<double> z(n);Device<float4> velocity(n);
  Device<unsigned> id(n);Device<typecode> code(n);Device<tsymatrix3d> sigma(n);
  Device<int2> cells(3);Device<float3> acceleration(3);
  StCteSph csp=CteSphNull();csp.tkernel=KERNEL_Wendland;csp.kernelh=1;
  csp.kwend.bwen=-2.08891f; // Production 3D Wendland normalization at h=1.
  csp.massfluid=2;csp.rhopzero=2;csp.gamma=1;csp.cs0=1;
  const StDivDataGpu dvd=MakeDivDataGpu(1,TUint3(1),TUint3(0),cells.p,2,DCEL_GetCode(10,10,11),TDouble3(0),4,2);
  const float3 sentinel=make_float3(123,-456,789);
  for(unsigned axis=0;axis<3;axis++){
    std::vector<float3> baseline;
    for(unsigned reordered=0;reordered<2;reordered++)for(unsigned lowbits=0;lowbits<2;lowbits++){
      std::vector<double2> hx(n,make_double2(1,1));std::vector<double> hz(n,1);
      std::vector<float4> hv(n,make_float4(0,0,0,2));std::vector<unsigned> hi(n);
      std::vector<typecode> hc(n);std::vector<tsymatrix3d> hs(n);unsigned fluid=0;
      for(unsigned p=0;p<n;p++){
        const unsigned native=orders[reordered][p];hi[p]=ids[native];hc[p]=codes[native];hs[p]=stresses[native];
        if(native==4){fluid=p;hv[p].w=4;if(axis==0)hx[p].x=0;else if(axis==1)hx[p].y=0;else hz[p]=0;}
        if(lowbits){
          const double d=std::ldexp(1.,-32);auto& s=hs[p];s.xx+=d;s.xy+=2*d;s.xz+=3*d;s.yy+=4*d;s.yz+=5*d;s.zz+=6*d;
          Require(!Same(s,stresses[native])&&Same(ToTSymMatrix3f(s),ToTSymMatrix3f(stresses[native])),"Gauge low-bit fixture must change double only");
        }
      }
      xy.Put(hx);z.Put(hz);velocity.Put(hv);id.Put(hi);code.Put(hc);sigma.Put(hs);
      cells.Put({make_int2(0,0),make_int2(0,0),make_int2(fluid,fluid+1)});
      acceleration.Put(std::vector<float3>(3,sentinel));
      cugauge::Interaction_GaugeForce(csp,dvd,n,idbegin,selected,xy.p,z.p,code.p,id.p,velocity.p,sigma.p,acceleration.p);Sync();
      const auto actual=acceleration.Get();const std::string label="gauge_axis"+std::to_string(axis)+"_order"+std::to_string(reordered)+"_low"+std::to_string(lowbits);
      for(unsigned p=0;p<2;p++){
        const double f=double(csp.kwend.bwen)/8.;const auto a=actual[p];const double values[3]={a.x,a.y,a.z};double error=0,scale=1;
        for(unsigned c=0;c<3;c++){const double expected=f*columns[p][axis][c];Require(std::isfinite(values[c]),label+" nonfinite force");error=(std::max)(error,std::abs(values[c]-expected));scale=(std::max)(scale,std::abs(expected));}
        // Declared before execution: 16 float eps accommodates local CUDA
        // fast-math rounding, not a physical or double force-accuracy claim.
        Near(label+"_native"+std::to_string(idbegin+p),error,16.*std::numeric_limits<float>::epsilon()*scale);
      }
      Require(Same(actual[2],sentinel),label+" unselected gauge slot overwritten");
      if(!reordered&&!lowbits)baseline=actual;
      else for(unsigned p=0;p<3;p++)Require(Same(actual[p],baseline[p]),label+" native reorder/float-projected low bits changed output");
    }
  }
}

class ResizeFixture:public JSphGpuSingle{
  JLog2 quiet;
public:
  explicit ResizeFixture(bool verlet):quiet(JLog2::Out_None){
    static_assert(std::is_same<decltype(Sigmag),tsymatrix3d*>::value,"TODO G1: persistent device stress is still float");
    static_assert(std::is_same<decltype(Sigma),tsymatrix3d*>::value,"TODO G1: download stress is still float");
    Log=&quiet;Np=7;Npb=NpbOk=1;CaseNp=7;CaseNbound=CaseNpb=1;CaseNfluid=6;CaseNfloat=0;
    TStep=verlet?STEP_Verlet:STEP_Symplectic;TVisco=VISCO_Artificial;HydroMech=false;
    DDTArray=false;ArtificialStress=false;UseNormals=false;WithFloating=false;PeriActive=0;
    TMdbc2=MDBC2_None;AllocCpuMemoryParticles(Np);AllocGpuMemoryParticles(Np,0);ReserveBasicArraysGpu();
    for(unsigned p=0;p<Np;p++){
      Idp[p]=p;Code[p]=(p==0?CODE_TYPE_FIXED:CODE_TYPE_FLUID);Dcell[p]=0;
      Posxy[p]=TDouble2(2.+p,0);Posz[p]=2;Velrhop[p]=TFloat4(0,0,0,2100);Sigma[p]=Marker(p);Kplastic[p]=0;
    }
    Code[2]=CODE_SetPeriodic(CODE_TYPE_FLUID);ParticlesDataUp(Np,nullptr,nullptr);
    Cuda(cudaMemset(PosCellg,0,sizeof(float4)*Np));Cuda(cudaMemset(CorrMatg,0,sizeof(tmatrix3d)*Np));
    Cuda(cudaMemset(FSTypeg,0,sizeof(unsigned)*Np));Cuda(cudaMemset(FSNormalg,0,sizeof(float3)*Np));Cuda(cudaMemset(PosDivg,0,sizeof(float)*Np));
    if(!verlet)SigmaPreg=ArraysGpu->ReserveSymatrix3d();
    else Cuda(cudaMemcpy(VelrhopM1g,Velrhopg,sizeof(float4)*Np,cudaMemcpyDeviceToDevice));
    std::vector<tsymatrix3d> history(Np);for(unsigned p=0;p<Np;p++)history[p]=Marker(p+100);
    ::Put(verlet?SigmaM1g:SigmaPreg,history);Sync();
  }
  ~ResizeFixture(){Log=nullptr;}
  void CheckState(){
    const bool verlet=(TStep==STEP_Verlet);const auto before=::Get(Sigmag,Np),old=::Get(verlet?SigmaM1g:SigmaPreg,Np);
    auto scratch=ArraysGpu->ReserveSymatrix3d();ArraysGpu->Free(scratch); // Third 48B slot must exist with both states live.
    const unsigned capacity=GpuParticlesSize;ResizeGpuMemoryParticles(capacity+17);Sync();Require(GpuParticlesSize>capacity,"Actual solver capacity did not grow");
    const auto after=::Get(Sigmag,Np),history=::Get(verlet?SigmaM1g:SigmaPreg,Np);
    for(unsigned p=0;p<Np;p++)Require(Same(before[p],after[p])&&Same(old[p],history[p]),"Solver resize altered double stress");
    const unsigned kept=ParticlesDataDown(Np,0,true,true);Require(kept==Np-1,"Native download count");
    for(unsigned p=0;p<kept;p++){
      Require(Idp[p]!=2&&Same(Sigma[p],Marker(Idp[p])),"Native download/compaction lost stress-ID pairing or precision");
      const auto s=Sigma[p];Require(AuxSigma_xx_yy_zz[p]==TFloat3(float(s.xx),float(s.yy),float(s.zz))&&
        AuxSigma_xy_yz_xz[p]==TFloat3(float(s.xy),float(s.yz),float(s.xz)),"Legacy display projection/order changed");
    }
  }
};
static std::string Quote(const std::string& text){std::string out="\"";for(char c:text){if(c=='"'||c=='\\')out+='\\';if(c=='\n')out+="\\n";else if(static_cast<unsigned char>(c)>=32)out+=c;}return out+'"';}
int main(int argc,char** argv){
  try{
    Require((argc==3||argc==4)&&std::string(argv[1])=="--json"&&(argc==3||std::string(argv[3])=="--memory-smoke"),"Usage: hg_gpu_stress_test --json NEW.json [--memory-smoke]");
    Require(!std::filesystem::exists(argv[2]),"Refusing existing result");const bool smoke=(argc==4);
    AppInfo.LogInit("");Cuda(cudaSetDevice(0));cudaDeviceProp prop;Cuda(cudaGetDeviceProperties(&prop,0));
    struct Result{std::string name,detail;bool pass;};std::vector<Result> checks;
    auto test=[&](const std::string& name,const std::function<void()>& action){
      try{action();checks.push_back({name,"",true});}catch(const std::exception& e){checks.push_back({name,e.what(),false});}
      std::cout<<(checks.back().pass?"PASS ":"FAIL ")<<name<<' '<<checks.back().detail<<std::endl;
    };
    for(bool verlet:{false,true})for(bool soft:{false,true})test(std::string(verlet?"Verlet":"Symplectic")+(soft?"_softening":"_elastic"),[&](){Accumulation(verlet,soft,smoke?4:10000);});
    test("six_component_CPU_constitutive_reference",Constitutive);test("mixed_types_boundary_and_kernel_tail",IndexGuards);
    test("48B_pool_and_full_fluid_sort",PoolAndSort);test("periodic_current_history_no_pre",Periodic);
    test("force_gauge_manual_columns_native_periodic_lowbits",ForceGauge);
    // JSphGpu's destructor resets the CUDA context. No device fixture is alive across these scopes.
    test("real_solver_resize_Verlet_download",[](){ResizeFixture f(true);f.CheckState();});
    test("real_solver_resize_Symplectic_download",[](){Cuda(cudaSetDevice(0));ResizeFixture f(false);f.CheckState();});
    unsigned failures=0;for(const auto& c:checks)if(!c.pass)failures++;
    std::ofstream out(argv[2]);Require(bool(out),"Cannot write result");out<<std::setprecision(17);
    out<<"{\"completed\":true,\"passed\":"<<(failures?"false":"true")<<",\"failures\":"<<failures<<",\"memory_smoke\":"<<(smoke?"true":"false")<<",\"device\":"<<Quote(prop.name)
      <<",\"stress_bytes\":48,\"scope\":\"Production GPU wrappers and CPU constitutive reference; prescribed rates, pool/sort/periodic/resize/download and force-gauge particle accelerations only. Gauge total reduction, coupled physical acceptance and actual PART SaveData/restart acceptance are not covered.\",\"pending_case_check\":\"Run existing stress_io_harness inspect on a newly generated GPU PART with SigmaState_kk/ij; legacy fields must equal its float projection.\",\"checks\":[";
    for(size_t i=0;i<checks.size();i++){if(i)out<<',';out<<"{\"name\":"<<Quote(checks[i].name)<<",\"passed\":"<<(checks[i].pass?"true":"false")<<",\"detail\":"<<Quote(checks[i].detail)<<'}';}
    out<<"],\"metrics\":[";for(size_t i=0;i<Metrics.size();i++){if(i)out<<',';const auto& m=Metrics[i];out<<"{\"name\":"<<Quote(m.name)<<",\"max_abs_error\":";if(std::isfinite(m.error))out<<m.error;else out<<"null";out<<",\"tolerance\":"<<m.tolerance<<'}';}
    out<<"]}\n";out.flush();Require(bool(out),"Result write failed");return failures?1:0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
