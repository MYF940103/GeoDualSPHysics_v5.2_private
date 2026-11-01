// Actual CUDA force-kernel component only; no JSph class, integration or PDE patch.
// The host supplies a scalar isotropic correction from an independent 2-D moment.
#include "JSphGpu_ker.h"
#include "FunSphKernel.h"
#include "JDsDcellDef.h"
#include "JAppInfo.h"
#include <cuda_runtime.h>
#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

JAppInfo AppInfo("GpuObserverTheta","r1","02-11-2026");
namespace fs=std::filesystem;
static void Check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
static void Cu(cudaError_t e){Check(e==cudaSuccess,cudaGetErrorString(e));}
template<class T,unsigned N>struct Device{
  T* p=nullptr;
  Device(){Cu(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*N));clear();}
  ~Device(){if(p)cudaFree(p);}
  Device(const Device&)=delete;Device& operator=(const Device&)=delete;
  void clear(){Cu(cudaMemset(p,0,sizeof(T)*N));}
  void put(const std::array<T,N>& a){Cu(cudaMemcpy(p,a.data(),sizeof(T)*N,cudaMemcpyHostToDevice));}
  std::array<T,N> get()const{std::array<T,N> a;Cu(cudaMemcpy(a.data(),p,sizeof(T)*N,cudaMemcpyDeviceToHost));return a;}
};
constexpr unsigned N=9,Centre=4;
struct Trial{const char* name;float axx,axz,azx,azz,tx,tz;};
struct Result{
  std::array<float,N> ar,rate,visc;
  std::array<float3,N> ace;
  std::array<tsymatrix3f,N> stress;
  std::array<double,N> theta;
};
template<class T,std::size_t K>static bool Same(const std::array<T,K>& a,const std::array<T,K>& b){return !memcmp(a.data(),b.data(),sizeof(T)*K);}
static void ExactPhysical(const Result& a,const Result& b){
  Check(Same(a.ar,b.ar)&&Same(a.rate,b.rate)&&Same(a.visc,b.visc)&&Same(a.ace,b.ace)&&Same(a.stress,b.stress),"Observer ON changed actual force outputs");
}
static void Finite(const Result& a){
  for(unsigned i=0;i<N;i++){
    const auto v=a.ace[i];const auto s=a.stress[i];
    Check(std::isfinite(a.ar[i])&&std::isfinite(a.rate[i])&&std::isfinite(a.visc[i])&&std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z),"Nonfinite physical force output");
    Check(std::isfinite(s.xx)&&std::isfinite(s.yy)&&std::isfinite(s.zz)&&std::isfinite(s.xy)&&std::isfinite(s.yz)&&std::isfinite(s.xz),"Nonfinite stress-rate output");
  }
}
class ForceGrid{
  Device<int2,4> cells;
  Device<unsigned,N> dcell,id,fstype;
  Device<typecode,N> code;
  Device<double2,N> xy;
  Device<double,N> z,theta;
  Device<float4,N> pos,velocity;
  Device<tmatrix3d,N> correction;
  Device<tsymatrix3d,N> sigma;
  Device<tsymatrix3f,N> stress;
  Device<float3,N> ace,fsnormal;
  Device<float,N> pressure,rate,ar,visc;
  StDivDataGpu dvd;
  StCteInteraction c={};
  std::array<float4,N> positions={};
  std::array<tmatrix3d,N> matrices={};
  double mxx=0,mxz=0,mzz=0,inv=0;
public:
  explicit ForceGrid(std::ostream& moment){
    // Empty boundary range, nine fluid nodes in one actual linked-list cell.
    cells.put({make_int2(0,0),make_int2(0,0),make_int2(0,N),make_int2(0,0)});
    std::array<unsigned,N> ids={},fst={};std::array<typecode,N> codes={};
    std::array<double2,N> xs={};std::array<double,N> zs={};
    for(unsigned ix=0;ix<3;ix++)for(unsigned iz=0;iz<3;iz++){
      const unsigned i=3*ix+iz;const float x=.125f+float(ix)*.125f,zz=.125f+float(iz)*.125f;
      ids[i]=i;codes[i]=typecode(CODE_TYPE_FLUID);xs[i]=make_double2(x,0.);zs[i]=zz;
      positions[i]=make_float4(x,0.f,zz,0.f);
    }
    id.put(ids);code.put(codes);fstype.put(fst);xy.put(xs);z.put(zs);pos.put(positions);
    const unsigned cellcode=DCEL_GetCode(1,1,1);
    dvd=MakeDivDataGpu(1,TUint3(1,1,1),TUint3(0),cells.p,.5f,cellcode,TDouble3(0),.125f,.5f);
    c.simulate2d=true;c.nbound=0;c.massb=c.massf=1.f;c.kernelh=.125f;c.kernelsize=.25f;c.kernelsize2=.0625f;c.poscellsize=.5f;
    c.cs0=4;c.eta2=(.1f*c.kernelh)*(.1f*c.kernelh);c.scell=.5f;c.dp=.125f;
    c.cteb=1;c.gamma=7;c.rhopzero=2;c.ovrhopzero=.5f;c.tboundary=BC_DBC;
    c.axis=MGDIV_Z;c.cellcode=cellcode;c.modulus_K=16;c.modulus_G=8;
    c.hydromech=1;c.soilstressrategradcorr=1;c.porecompgradcorr=1;c.porecompsourcemode=0;
    c.porewaterbulkmodulus=128;c.porosity=.5f;c.porekwn=256;c.porewaterrho=1;c.poreghyd=1;
    const auto kw=fsph::GetKernelWendland_Ctes(true,double(c.kernelh));c.awen=kw.awen;c.bwen=kw.bwen;
    const double volume=double(c.massf/2.f);
    moment<<std::setprecision(17)<<"neighbour_id,drx,drz,float_rr2,float_fac,volume,mxx_term,mxz_term,mzz_term\n";
    for(unsigned j=0;j<N;j++)if(j!=Centre){
      const float dx=positions[Centre].x-positions[j].x,dz=positions[Centre].z-positions[j].z,rr2=dx*dx+dz*dz;
      const float fac=fsph::GetKernelWendland_Fac(kw,c.kernelh,rr2);
      const double gx=double(fac)*double(dx),gz=double(fac)*double(dz);
      const double xx=-volume*double(dx)*gx,xz=-volume*double(dx)*gz,zz=-volume*double(dz)*gz;
      mxx+=xx;mxz+=xz;mzz+=zz;moment<<j<<','<<dx<<','<<dz<<','<<rr2<<','<<fac<<','<<volume<<','<<xx<<','<<xz<<','<<zz<<'\n';
    }
    const double scale=(std::max)(1.,(std::max)(fabs(mxx),fabs(mzz)));
    Check(std::isfinite(mxx)&&mxx>0&&fabs(mxx-mzz)<=64*DBL_EPSILON*scale&&fabs(mxz)<=64*DBL_EPSILON*scale,"Independent full-support center moment is not isotropic");
    inv=1./(.5*(mxx+mzz));Check(std::isfinite(inv)&&inv>0,"Invalid independent correction");
    for(auto& v:matrices){v.a11=v.a33=inv;v.a22=1.;}correction.put(matrices);
    // Second-grid-step axial nodes are exactly at2h and have zero Wendland fac;
    // the center's omitted further lattice samples therefore contribute zero.
    const float boundary=fsph::GetKernelWendland_Fac(kw,c.kernelh,c.kernelsize2);
    Check(boundary==0.f,"Kernel support-edge factor is not exactly zero");
    cusph::CteInteractionUp(&c);Cu(cudaGetLastError());
  }
  Result Run(const Trial& t,bool drained,bool observe,std::ostream& nodes,unsigned caseid,unsigned stage){
    std::array<float4,N> v={};std::array<unsigned,N> fs={};std::array<double,N> sentinel={};
    for(unsigned i=0;i<N;i++){
      const float x=positions[i].x-.25f,zz=positions[i].z-.25f;
      v[i]=make_float4(t.tx+t.axx*x+t.axz*zz,0.f,t.tz+t.azx*x+t.azz*zz,2.f);
      sentinel[i]=123.+double(i)*.25;
    }
    if(drained)fs[Centre]=FST_FreeSurface;
    velocity.put(v);fstype.put(fs);sigma.clear();pressure.clear();ar.clear();rate.clear();stress.clear();ace.clear();visc.clear();
    if(observe)theta.clear();else theta.put(sentinel); // Same caller reset as PreInteractionVars_Forces.
    const StInterParmsg p=StrInterParmsg(true,false,KERNEL_Wendland,FTMODE_None,false,DDT_None,SHIFT_None,MDBC2_None,
      0.f,0.f,128,128,N,0,0,0,0,dvd,dcell.p,xy.p,z.p,pos.p,velocity.p,id.p,code.p,
      nullptr,nullptr,nullptr,correction.p,nullptr,nullptr,nullptr,nullptr,nullptr,nullptr,
      visc.p,ar.p,ace.p,nullptr,nullptr,sigma.p,stress.p,nullptr,pressure.p,rate.p,fstype.p,fsnormal.p,drained,
      nullptr,nullptr,nullptr,nullptr,nullptr,nullptr,(observe?theta.p:nullptr));
    cusph::Interaction_Forces(p);Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());
    Check(Same(v,velocity.get())&&Same(matrices,correction.get()),"Actual interaction changed physical velocity or input correction");
    const auto sig=sigma.get();const auto pw=pressure.get();for(unsigned i=0;i<N;i++)Check(sig[i].xx==0&&sig[i].yy==0&&sig[i].zz==0&&sig[i].xy==0&&sig[i].yz==0&&sig[i].xz==0&&pw[i]==0,"Actual interaction changed stored stress or pressure");
    Result r={ar.get(),rate.get(),visc.get(),ace.get(),stress.get(),theta.get()};Finite(r);
    if(!observe)Check(Same(r.theta,sentinel),"NULL observer pointer wrote diagnostic sentinel");
    for(unsigned i=0;i<N;i++){
      const auto a=r.ace[i];const auto s=r.stress[i];nodes<<caseid<<','<<stage<<','<<i<<','<<r.ar[i]<<','<<r.rate[i]<<','<<r.visc[i]<<','<<a.x<<','<<a.y<<','<<a.z<<','
        <<s.xx<<','<<s.yy<<','<<s.zz<<','<<s.xy<<','<<s.yz<<','<<s.xz<<','<<r.theta[i]<<'\n';
    }
    return r;
  }
  void Summary(std::ostream& out)const{out<<std::setprecision(17)<<"\"moment_xx\":"<<mxx<<",\"moment_xz\":"<<mxz<<",\"moment_zz\":"<<mzz<<",\"supplied_isotropic_Cxx_Czz\":"<<inv;}
};
int main(int argc,char** argv){
  try{
    fs::path out;int device=0;
    for(int i=1;i<argc;i++){const std::string key=argv[i];Check(i+1<argc,"Missing argument value");if(key=="--out")out=argv[++i];else if(key=="--device")device=std::stoi(argv[++i]);else Check(false,"Unknown option");}
    Check(!out.empty()&&!fs::exists(out),"Require a fresh output directory");Cu(cudaSetDevice(device));fs::create_directories(out);
    std::ofstream moment(out/"moment.csv"),nodes(out/"node_outputs.csv"),cases(out/"theta_cases.csv");nodes<<std::setprecision(17);cases<<std::setprecision(17);
    nodes<<"case_id,stage,node_id,ar,pore_rate,viscdt,ace_x,ace_y,ace_z,rsigma_xx,rsigma_yy,rsigma_zz,rsigma_xy,rsigma_yz,rsigma_xz,theta\n";
    cases<<"case_id,trial,drained_center,trace_reference,theta_stage1,theta_stage2,theta_tolerance,pore_rate_reference,pore_rate_actual,pore_tolerance,shear_stress_xz,original_physical_outputs_exact,caller_reset_exact\n";
    const Trial trials[]={{"translation",0,0,0,0,.25f,-.125f},{"dilation",.5f,0,0,.5f,0,0},{"compression",-.5f,0,0,-.5f,0,0},
      {"simple_shear",0,.5f,0,0,0,0},{"rigid_rotation",0,-.5f,.5f,0,0,0}};
    ForceGrid grid(moment);unsigned count=0,nonzero=0,drainednonzero=0,shear=0;
    for(const auto& t:trials)for(bool drained:{false,true}){
      const unsigned caseid=count++;const auto off=grid.Run(t,drained,false,nodes,caseid,0);
      const auto on1=grid.Run(t,drained,true,nodes,caseid,1),on2=grid.Run(t,drained,true,nodes,caseid,2);
      ExactPhysical(off,on1);ExactPhysical(off,on2);Check(Same(on1.theta,on2.theta),"Independent caller reset did not give exact same-stage theta");
      const double trace=double(t.axx)+double(t.azz),tol=64*FLT_EPSILON*(std::max)(1.,fabs(trace));
      for(const auto* r:{&on1,&on2})Check(std::isfinite(r->theta[Centre])&&fabs(r->theta[Centre]-trace)<=tol,"Center theta differs from manufactured trace");
      const double expected=drained?0.:-256.*trace,ptol=64*FLT_EPSILON*(std::max)(1.,fabs(expected));
      Check(fabs(double(on1.rate[Centre])-expected)<=ptol,"Center pore-rate compression/drainage guard differs");
      if(trace!=0){Check(fabs(on1.theta[Centre])>.5*fabs(trace),"Dilation/compression theta coverage is empty");nonzero+=2;if(drained){Check(on1.rate[Centre]==0.f&&on2.rate[Centre]==0.f,"Drained center pressure rate is not exactly zero");drainednonzero+=2;}}
      if(std::string(t.name)=="simple_shear"){Check(on1.stress[Centre].xz>0.f&&on2.stress[Centre].xz>0.f,"Shear stress-rate control is empty");shear+=2;}
      cases<<caseid<<','<<t.name<<','<<drained<<','<<trace<<','<<on1.theta[Centre]<<','<<on2.theta[Centre]<<','<<tol<<','<<expected<<','<<on1.rate[Centre]<<','<<ptol<<','<<on1.stress[Centre].xz<<",1,1\n";
    }
    moment.flush();nodes.flush();cases.flush();Check(bool(moment)&&bool(nodes)&&bool(cases),"Component CSV write failed");
    Check(count==10&&nonzero==8&&drainednonzero==4&&shear==4,"Declared nonempty case coverage changed");
    std::ofstream done(out/"completion.json");done<<"{\"passed\":true,\"cases\":"<<count<<",\"actual_kernel_calls\":30,\"node_output_rows\":270,\"particles\":9,\"center_ID\":4,\"dimensions\":[2],\"native_OFF_ON_output_pairs\":180,\"NULL_theta_sentinel_checks\":90,\"same_stage_reset_theta_pairs\":90,\"nonzero_trace_ON_checks\":"<<nonzero
      <<",\"drained_nonzero_theta_zero_pore_rate_checks\":"<<drainednonzero<<",\"nonempty_shear_stress_checks\":"<<shear<<',';grid.Summary(done);
    done<<",\"correction_supplied_from_independent_center_moment\":true,\"general_C_matrix_solver_tested\":false,\"actual_force_kernel_only\":true,\"physical_drained_run_admitted\":false,\"time_integrated\":false,\"feedback_tested\":false,\"physical_acceptance\":false}\n";
    done.flush();Check(bool(done),"Component completion write failed");return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(const char* e){std::cerr<<e<<'\n';return 1;}
  catch(...){std::cerr<<"GPU theta component failed; preserve partial evidence\n";return 2;}
}
