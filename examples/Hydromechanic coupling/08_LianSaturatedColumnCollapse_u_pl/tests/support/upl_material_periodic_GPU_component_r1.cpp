// Actual periodic Symplectic wrapper, no solver/material return or copied device kernel.
#include "JSphGpu_ker.h"
#include "JDsDcellDef.h"
#include "JAppInfo.h"
#include <cuda_runtime.h>
#include <array>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
JAppInfo AppInfo("UplMaterialPeriodicGpu","r1","06-11-2026");
namespace fs=std::filesystem;
static constexpr unsigned Cap=8;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static void Cu(cudaError_t e){Need(e==cudaSuccess,cudaGetErrorString(e));}
template<class T>static bool Same(T a,T b){return !std::memcmp(&a,&b,sizeof(T));}
static bool Same(double2 a,double2 b){return Same(a.x,b.x)&&Same(a.y,b.y);}
static bool Same(float4 a,float4 b){return Same(a.x,b.x)&&Same(a.y,b.y)&&Same(a.z,b.z)&&Same(a.w,b.w);}
static bool Same(const tsymatrix3d& a,const tsymatrix3d& b){return Same(a.xx,b.xx)&&Same(a.xy,b.xy)&&Same(a.xz,b.xz)&&Same(a.yy,b.yy)&&Same(a.yz,b.yz)&&Same(a.zz,b.zz);}
static bool Same(const tsymatrix3f& a,const tsymatrix3f& b){return Same(a.xx,b.xx)&&Same(a.xy,b.xy)&&Same(a.xz,b.xz)&&Same(a.yy,b.yy)&&Same(a.yz,b.yz)&&Same(a.zz,b.zz);}
template<class T>struct Array{
  std::array<T,Cap> h{};T* p=nullptr;Array(){Cu(cudaMalloc(reinterpret_cast<void**>(&p),Cap*sizeof(T)));}~Array(){if(p)cudaFree(p);}
  Array(const Array&)=delete;Array& operator=(const Array&)=delete;
  void Put(){Cu(cudaMemcpy(p,h.data(),Cap*sizeof(T),cudaMemcpyHostToDevice));}
  std::array<T,Cap> Get()const{std::array<T,Cap> v;Cu(cudaMemcpy(v.data(),p,Cap*sizeof(T),cudaMemcpyDeviceToHost));return v;}
  void Check(std::ostream* raw=nullptr)const{const auto v=Get();for(unsigned q=0;q<Cap;q++)Need(Same(v[q],h[q]),"Actual wrapper output/input/tail member differs");if(raw)raw->write(reinterpret_cast<const char*>(v.data()),sizeof(T)*Cap);}
};
struct Patch{
  Array<unsigned> list,id,cell;Array<typecode> code;Array<double2> xy,prexy;Array<double> z,prez,j,theta,jpre;
  Array<float4> vel,prevel;Array<tsymatrix3f> sps;Array<tsymatrix3d> sigma,presigma;Array<float> p,p0,rate,ppre,k,dk;
  StCteInteraction ct{};
  Patch(){
    ct.scell=1.f;ct.cellcode=DCEL_GetCode(3,1,3);ct.domposminx=ct.domposminy=ct.domposminz=0.;cusph::CteInteractionUp(&ct);
    for(unsigned q=0;q<Cap;q++){
      const double d=q+1.;list.h[q]=0x1234abcdu+q;id.h[q]=100+q;cell.h[q]=0x34560000u+q;code.h[q]=CODE_TYPE_FLUID;
      xy.h[q]=make_double2(20*d,30*d);z.h[q]=40*d;prexy.h[q]=make_double2(50*d,60*d);prez.h[q]=70*d;
      vel.h[q]=make_float4(float(d),float(2*d),float(3*d),float(4*d));prevel.h[q]=make_float4(float(5*d),float(6*d),float(7*d),float(8*d));
      sps.h[q]={float(d),float(2*d),float(3*d),float(4*d),float(5*d),float(6*d)};
      sigma.h[q]=TSymMatrix3d(d,2*d,3*d,4*d,5*d,6*d);presigma.h[q]=TSymMatrix3d(7*d,8*d,9*d,10*d,11*d,12*d);
      p.h[q]=float(80+d);p0.h[q]=float(90+d);rate.h[q]=float(100+d);ppre.h[q]=float(110+d);j.h[q]=120+d;theta.h[q]=130+d;jpre.h[q]=140+d;k.h[q]=float(150+d);dk.h[q]=float(160+d);
    }
    id.h[0]=17;cell.h[0]=DCEL_Cell(ct.cellcode,4u,0u,4u);xy.h[0]=make_double2(4.25,0);z.h[0]=4.5;
    prexy.h[0]=make_double2(4,0);prez.h[0]=4.25;vel.h[0]=make_float4(.125f,.25f,.5f,2072.5f);prevel.h[0]=make_float4(.0625f,.125f,.25f,2072.5f);
    p.h[0]=128;p0.h[0]=64;rate.h[0]=-32;ppre.h[0]=96;j.h[0]=1.125;theta.h[0]=-.25;jpre.h[0]=1.0625;k.h[0]=.125f;dk.h[0]=.0625f;
    list.Put();id.Put();cell.Put();code.Put();xy.Put();z.Put();prexy.Put();prez.Put();vel.Put();prevel.Put();sps.Put();sigma.Put();presigma.Put();p.Put();p0.Put();rate.Put();ppre.Put();j.Put();theta.Put();jpre.Put();k.Put();dk.Put();
  }
  void Copy(unsigned dst,unsigned src,bool inverse,tdouble3 inc,bool pre,bool history){
    const double sign=inverse?-1.:1.;xy.h[dst]=make_double2(xy.h[src].x+sign*inc.x,xy.h[src].y+sign*inc.y);z.h[dst]=z.h[src]+sign*inc.z;
    const unsigned cx=unsigned(xy.h[dst].x),cy=unsigned(xy.h[dst].y),cz=unsigned(z.h[dst]);cell.h[dst]=DCEL_Cell(ct.cellcode,cx,cy,cz);
    id.h[dst]=id.h[src];code.h[dst]=CODE_SetPeriodic(code.h[src]);vel.h[dst]=vel.h[src];sigma.h[dst]=sigma.h[src];sps.h[dst]=sps.h[src];
    p.h[dst]=p.h[src];p0.h[dst]=p0.h[src];rate.h[dst]=rate.h[src];j.h[dst]=j.h[src];theta.h[dst]=theta.h[src];jpre.h[dst]=jpre.h[src];
    if(pre){prexy.h[dst]=prexy.h[src];prez.h[dst]=prez.h[src];prevel.h[dst]=prevel.h[src];presigma.h[dst]=presigma.h[src];ppre.h[dst]=ppre.h[src];}
    if(history){k.h[dst]=k.h[src];dk.h[dst]=dk.h[src];}
  }
  void Check(std::ostream& legacy){
    static_assert(sizeof(double2)==16&&sizeof(float4)==16&&sizeof(tsymatrix3d)==48&&sizeof(tsymatrix3f)==24,"Legacy scalar-only layouts differ");
    list.Check();id.Check(&legacy);cell.Check(&legacy);code.Check(&legacy);xy.Check(&legacy);z.Check(&legacy);prexy.Check(&legacy);prez.Check(&legacy);vel.Check(&legacy);prevel.Check(&legacy);sps.Check(&legacy);sigma.Check(&legacy);presigma.Check(&legacy);p.Check(&legacy);p0.Check(&legacy);rate.Check(&legacy);ppre.Check(&legacy);j.Check(&legacy);theta.Check(&legacy);jpre.Check(&legacy);k.Check();dk.Check();
  }
  void Call(unsigned n,unsigned first,tdouble3 inc,bool pre,bool history,std::ostream& legacy){
    list.Put();
    if(history)cusph::PeriodicDuplicateSymplectic(n,first,TUint3(8,1,8),inc,list.p,id.p,code.p,cell.p,xy.p,z.p,vel.p,sps.p,pre?prexy.p:nullptr,pre?prez.p:nullptr,pre?prevel.p:nullptr,sigma.p,pre?presigma.p:nullptr,p.p,p0.p,rate.p,pre?ppre.p:nullptr,j.p,theta.p,jpre.p,k.p,dk.p);
    else cusph::PeriodicDuplicateSymplectic(n,first,TUint3(8,1,8),inc,list.p,id.p,code.p,cell.p,xy.p,z.p,vel.p,sps.p,pre?prexy.p:nullptr,pre?prez.p:nullptr,pre?prevel.p:nullptr,sigma.p,pre?presigma.p:nullptr,p.p,p0.p,rate.p,pre?ppre.p:nullptr,j.p,theta.p,jpre.p);
    Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());for(unsigned q=0;q<n;q++)Copy(first+q,list.h[q]&0x7fffffffu,list.h[q]>=0x80000000u,inc,pre,history);Check(legacy);
  }
  void Run(bool pre,bool history,std::ostream& legacy,std::ostream& csv){
    list.h[0]=0;list.h[1]=0x80000000u;Call(2,1,TDouble3(1,0,0),pre,history,legacy);
    // Change the native source after its images exist: a corner must inherit its immediate image source, not re-read owner0.
    k.h[0]=.25f;dk.h[0]=.125f;Cu(cudaMemcpy(k.p,k.h.data(),sizeof(float),cudaMemcpyHostToDevice));Cu(cudaMemcpy(dk.p,dk.h.data(),sizeof(float),cudaMemcpyHostToDevice));
    list.h[0]=1;list.h[1]=0x80000002u;Call(2,3,TDouble3(0,0,1),pre,history,legacy);
    // A second-generation source gets a distinct value before the final chained-axis copy.
    k.h[3]=.375f;dk.h[3]=.1875f;Cu(cudaMemcpy(k.p+3,k.h.data()+3,sizeof(float),cudaMemcpyHostToDevice));Cu(cudaMemcpy(dk.p+3,dk.h.data()+3,sizeof(float),cudaMemcpyHostToDevice));
    list.h[0]=0x80000003u;Call(1,5,TDouble3(1,0,0),pre,history,legacy);
    const auto actualK=k.Get();const auto actualDk=dk.Get();for(unsigned q=0;q<6;q++)csv<<pre<<','<<history<<','<<q<<','<<id.h[q]<<','<<xy.h[q].x<<','<<z.h[q]<<','<<actualK[q]<<','<<actualDk[q]<<'\n';
  }
};
int main(int argc,char** argv){try{
  Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_DIR");const fs::path out=argv[2];Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh output/existing parent required");Need(fs::create_directory(out),"Cannot create fresh output");Cu(cudaSetDevice(0));
  std::ofstream csv(out/"copies.csv");csv<<std::setprecision(17)<<"predictor_arrays_present,history_pointers_present,slot,native_id,x,z,kappa,kplasticdk\n";std::ostringstream nullRaw,onRaw;
  for(bool pre:{false,true}){Patch no;no.Run(pre,false,nullRaw,csv);Patch yes;yes.Run(pre,true,onRaw,csv);}
  const auto a=nullRaw.str(),b=onRaw.str();Need(a==b&&!a.empty(),"Adding optional history writes changed old defined-array outputs");
  std::ofstream old(out/"legacy_NULL.bin",std::ios::binary),on(out/"legacy_ON.bin",std::ios::binary);old.write(a.data(),a.size());on.write(b.data(),b.size());
  csv.flush();old.flush();on.flush();Need(bool(csv)&&bool(old)&&bool(on),"Component output failed");
  std::ofstream done(out/"completion.json");done<<"{\"stage\":\"upl_material_periodic_GPU_component_r1\",\"passed\":true,\"conditions\":4,\"actual_wrapper_calls\":12,\"direct_or_chained_image_results\":20,\"two_tail_points_per_call\":true,\"legacy_NULL_vs_ON_defined_array_bytes_equal\":true,\"legacy_compared_bytes\":"<<a.size()<<",\"same_old_binary_claim\":false,\"spatial_solver\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}}
