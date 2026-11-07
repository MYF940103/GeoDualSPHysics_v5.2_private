// Actual CUDA periodic wrappers and minimal public history-sort witness; no new kernel.
#include "JSphGpu_ker.h"
#include "JCellDivGpuSingle.h"
#include "JDsTimersGpu.h"
#include "JDsDcellDef.h"
#include "JDsDcell.h"
#include "JPeriodicDef.h"
#include "JAppInfo.h"
#include "JException.h"
#include <cuda_runtime.h>
#include <array>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
JAppInfo AppInfo("UplMaterialPeriodicGpu","r2","07-11-2026");
namespace fs=std::filesystem;static constexpr unsigned Cap=8;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static void Cu(cudaError_t e){Need(e==cudaSuccess,cudaGetErrorString(e));}
template<class T>static bool Same(T a,T b){return !std::memcmp(&a,&b,sizeof(T));}
static bool Same(double2 a,double2 b){return Same(a.x,b.x)&&Same(a.y,b.y);}
static bool Same(float4 a,float4 b){return Same(a.x,b.x)&&Same(a.y,b.y)&&Same(a.z,b.z)&&Same(a.w,b.w);}
static bool Same(const tsymatrix3d& a,const tsymatrix3d& b){return Same(a.xx,b.xx)&&Same(a.xy,b.xy)&&Same(a.xz,b.xz)&&Same(a.yy,b.yy)&&Same(a.yz,b.yz)&&Same(a.zz,b.zz);}
static bool Same(const tsymatrix3f& a,const tsymatrix3f& b){return Same(a.xx,b.xx)&&Same(a.xy,b.xy)&&Same(a.xz,b.xz)&&Same(a.yy,b.yy)&&Same(a.yz,b.yz)&&Same(a.zz,b.zz);}
template<class T>struct Array{
  std::array<T,Cap> h{};T* p=nullptr;Array(){Cu(cudaMalloc(reinterpret_cast<void**>(&p),Cap*sizeof(T)));}~Array(){if(p)cudaFree(p);}Array(const Array&)=delete;Array& operator=(const Array&)=delete;
  void Put(){Cu(cudaMemcpy(p,h.data(),Cap*sizeof(T),cudaMemcpyHostToDevice));}
  std::array<T,Cap> Get()const{std::array<T,Cap> v;Cu(cudaMemcpy(v.data(),p,Cap*sizeof(T),cudaMemcpyDeviceToHost));return v;}
  void Check()const{const auto v=Get();for(unsigned q=0;q<Cap;q++)Need(Same(v[q],h[q]),"Defined CUDA input/output/canary member differs");}
};
struct Patch{
  const bool Sym;Array<unsigned> list,id,cell;Array<typecode> code;Array<double2> xy,prexy;Array<double> z,prez,j,theta,jpre;Array<float4> vel,prevel;Array<tsymatrix3f> sps;Array<tsymatrix3d> sigma,presigma;Array<float> p,p0,rate,ppre,k,dk;std::unique_ptr<Array<float>> km1;StCteInteraction ct{};
  unsigned Cell(double2 a,double b)const{return DCEL_Cell(ct.cellcode,unsigned((a.x+4.)/.125),unsigned(a.y/.125),unsigned((b+4.)/.125));}
  explicit Patch(bool sym):Sym(sym){
    ct.scell=.125f;ct.cellcode=JDsDcell::CalcCellCode(TUint3(65,2,65));ct.domposminx=ct.domposminz=-4.;ct.domposminy=0.;cusph::CteInteractionUp(&ct);if(!Sym)km1=std::make_unique<Array<float>>();
    for(unsigned q=0;q<Cap;q++){const double d=q+1.;list.h[q]=0x1234abcdu+q;id.h[q]=q<2?41+q:1000+q;code.h[q]=CODE_TYPE_FLUID;xy.h[q]=make_double2(.125+.5*q,0);z.h[q]=.375+.5*q;cell.h[q]=Cell(xy.h[q],z.h[q]);prexy.h[q]=make_double2(xy.h[q].x+1./64,0);prez.h[q]=z.h[q]+1./32;
      vel.h[q]=make_float4(float(q)/8,0,-float(q)/16,2072.5f);prevel.h[q]=make_float4(-float(q)/32,0,float(q)/64,2048.f+q);sps.h[q]={float(d),float(2*d),float(3*d),float(4*d),float(5*d),float(6*d)};sigma.h[q]=TSymMatrix3d(d,2*d,3*d,4*d,5*d,6*d);presigma.h[q]=TSymMatrix3d(7*d,8*d,9*d,10*d,11*d,12*d);
      p.h[q]=float(16+q);p0.h[q]=float(32+q);rate.h[q]=-.125f*float(q+1);ppre.h[q]=float(64+q);j.h[q]=1.+q/16.;theta.h[q]=q/8.;jpre.h[q]=1.-q/32.;k.h[q]=q==0?.125f:q==1?.75f:2.f+float(q)/4;dk.h[q]=.0625f+float(q)/32;if(km1)km1->h[q]=.03125f+float(q)/16;
    }
    list.Put();id.Put();cell.Put();code.Put();xy.Put();z.Put();prexy.Put();prez.Put();vel.Put();prevel.Put();sps.Put();sigma.Put();presigma.Put();p.Put();p0.Put();rate.Put();ppre.Put();j.Put();theta.Put();jpre.Put();k.Put();dk.Put();if(km1)km1->Put();
  }
  void Check(){list.Check();id.Check();cell.Check();code.Check();xy.Check();z.Check();prexy.Check();prez.Check();vel.Check();prevel.Check();sps.Check();sigma.Check();presigma.Check();p.Check();p0.Check();rate.Check();ppre.Check();j.Check();theta.Check();jpre.Check();k.Check();dk.Check();if(km1)km1->Check();}
  void Expected(unsigned dst,unsigned src,bool inverse,tdouble3 inc){
    const double sign=inverse?-1.:1.;xy.h[dst]=make_double2(xy.h[src].x+sign*inc.x,xy.h[src].y+sign*inc.y);z.h[dst]=z.h[src]+sign*inc.z;cell.h[dst]=Cell(xy.h[dst],z.h[dst]);id.h[dst]=id.h[src];code.h[dst]=CODE_SetPeriodic(code.h[src]);vel.h[dst]=vel.h[src];sigma.h[dst]=sigma.h[src];sps.h[dst]=sps.h[src];p.h[dst]=p.h[src];p0.h[dst]=p0.h[src];rate.h[dst]=rate.h[src];prevel.h[dst]=prevel.h[src];presigma.h[dst]=presigma.h[src];ppre.h[dst]=ppre.h[src];k.h[dst]=k.h[src];dk.h[dst]=dk.h[src];
    if(Sym){prexy.h[dst]=prexy.h[src];prez.h[dst]=prez.h[src];j.h[dst]=j.h[src];theta.h[dst]=theta.h[src];jpre.h[dst]=jpre.h[src];}else km1->h[dst]=km1->h[src];
  }
  void Copy(unsigned first,tdouble3 inc,const char* axis,std::ostream& csv){
    list.Put();if(Sym)cusph::PeriodicDuplicateSymplectic(2,first,TUint3(64,1,64),inc,list.p,id.p,code.p,cell.p,xy.p,z.p,vel.p,sps.p,prexy.p,prez.p,prevel.p,sigma.p,presigma.p,p.p,p0.p,rate.p,ppre.p,j.p,theta.p,jpre.p,k.p,dk.p);
    else cusph::PeriodicDuplicateVerlet(2,first,TUint3(64,1,64),inc,list.p,id.p,code.p,cell.p,xy.p,z.p,vel.p,sps.p,prevel.p,sigma.p,presigma.p,p.p,p0.p,rate.p,ppre.p,k.p,dk.p,km1->p);
    Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());for(unsigned n=0;n<2;n++){const unsigned src=list.h[n]&0x7fffffffu,dst=first+n;Expected(dst,src,list.h[n]>=0x80000000u,inc);csv<<(Sym?"Symplectic":"Verlet")<<','<<axis<<','<<src<<','<<dst<<','<<id.h[dst]<<','<<xy.h[dst].x<<','<<z.h[dst]<<','<<k.h[dst]<<','<<dk.h[dst]<<',';if(km1)csv<<km1->h[dst];csv<<",1\n";}Check();csv.flush();Need(bool(csv),"Copy CSV write failed");
  }
  std::array<float,Cap> Sorted(Array<float>& a,JCellDivGpuSingle& divider,const std::array<unsigned,6>& order){
    Array<float> output;output.h=a.h;output.Put();divider.SortDataArrays(a.p,output.p);Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());for(unsigned q=0;q<6;q++)output.h[q]=a.h[order[q]];output.Check();a.Check();return output.Get();
  }
  void Run(std::ostream& copy,std::ostream& sorted,const fs::path& out){
    list.h[0]=0;list.h[1]=0x80000001u;Copy(2,TDouble3(1.25,0,0),"X",copy);k.h[0]=.25f;dk.h[0]=.125f;Cu(cudaMemcpy(k.p,k.h.data(),sizeof(float),cudaMemcpyHostToDevice));Cu(cudaMemcpy(dk.p,dk.h.data(),sizeof(float),cudaMemcpyHostToDevice));if(km1){km1->h[0]=.015625f;Cu(cudaMemcpy(km1->p,km1->h.data(),sizeof(float),cudaMemcpyHostToDevice));}
    list.h[0]=2;list.h[1]=0x80000003u;Copy(4,TDouble3(0,0,1.25),"Z_after_X",copy);
    std::ofstream cells(out/(Sym?"cells_Symplectic.csv":"cells_Verlet.csv"));cells<<"slot,key,expected_x,expected_y,expected_z,decoded_x,decoded_y,decoded_z\n";Need(ct.cellcode!=0&&DCEL_GetSx(ct.cellcode)-1+DCEL_GetSy(ct.cellcode)+DCEL_GetSz(ct.cellcode)==31,"Invalid GPU fixture cell distribution");
    for(unsigned q=0;q<6;q++){unsigned key=cell.h[q];const unsigned x=unsigned((xy.h[q].x+4.)/.125),y=unsigned(xy.h[q].y/.125),zz=unsigned((z.h[q]+4.)/.125),ax=DCEL_Cellx(ct.cellcode,key),ay=DCEL_Celly(ct.cellcode,key),az=DCEL_Cellz(ct.cellcode,key);cells<<q<<','<<key<<','<<x<<','<<y<<','<<zz<<','<<ax<<','<<ay<<','<<az<<'\n';cells.flush();Need(bool(cells)&&x<64&&y<1&&zz<64&&x==ax&&y==ay&&zz==az,"GPU fixture cell decode failed before Divide");}
    JDsTimersGpu timers;timers.Config(false);JCellDivGpuSingle divider(true,false,DefPeriActive(true,false,true),.0625f,.25f,true,CELLMODE_Full,.125f,TDouble3(-4,0,-4),TDouble3(4,.125,4),TUint3(64,1,64),0,0,0,out.string());divider.DefineDomain(ct.cellcode,TUint3(0),TUint3(64,1,64),TDouble3(-4,0,-4),TDouble3(4,.125,4));std::cerr<<"before GPU Divide\n"<<std::flush;divider.Divide(0,2,0,4,true,cell.p,code.p,xy.p,z.p,id.p,&timers);Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());std::cerr<<"after GPU Divide\n"<<std::flush;Need(divider.GetNpFinal()==6&&!divider.GetNpfOut()&&!divider.GetNpfOutIgnore(),"Actual GPU divide excluded a defined slot");
    Array<unsigned> si,sc;Array<typecode> sco;Array<double2> sxy;Array<double> sz;Array<float4> sv;si.h=id.h;sc.h=cell.h;sco.h=code.h;sxy.h=xy.h;sz.h=z.h;sv.h=vel.h;si.Put();sc.Put();sco.Put();sxy.Put();sz.Put();sv.Put();divider.SortBasicArrays(id.p,code.p,cell.p,xy.p,z.p,vel.p,si.p,sco.p,sc.p,sxy.p,sz.p,sv.p);Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());
    const auto ai=si.Get();const auto ax=sxy.Get();const auto az=sz.Get();std::array<unsigned,6> order{};std::array<bool,6> used{};unsigned moved=0;
    for(unsigned q=0;q<6;q++){unsigned src=6;for(unsigned s=0;s<6;s++)if(ai[q]==id.h[s]&&Same(ax[q],xy.h[s])&&Same(az[q],z.h[s])){Need(src==6,"Ambiguous GPU fixture identity");src=s;}Need(src<6&&!used[src],"GPU basic permutation lost identity");used[src]=true;order[q]=src;moved+=src!=q;si.h[q]=id.h[src];sc.h[q]=cell.h[src];sco.h[q]=code.h[src];sxy.h[q]=xy.h[src];sz.h[q]=z.h[src];sv.h[q]=vel.h[src];}Need(moved>0,"GPU sort witness is identity");si.Check();sc.Check();sco.Check();sxy.Check();sz.Check();sv.Check();
    const auto sk=Sorted(k,divider,order),sd=Sorted(dk,divider,order);std::array<float,Cap> sm{};if(km1)sm=Sorted(*km1,divider,order);
    for(unsigned q=0;q<6;q++){sorted<<(Sym?"Symplectic":"Verlet")<<','<<q<<','<<order[q]<<','<<ai[q]<<','<<ax[q].x<<','<<az[q]<<','<<sk[q]<<','<<sd[q]<<',';if(km1)sorted<<sm[q];sorted<<",1\n";}Check();
  }
};
int main(int argc,char** argv){try{
  Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_DIR");const fs::path out=argv[2];Need(!fs::exists(out)&&fs::is_directory(out.parent_path())&&fs::create_directory(out),"Fresh output required");AppInfo.LogInit((out/"component.log").string());Cu(cudaSetDevice(0));std::ofstream copy(out/"copies.csv"),sorted(out/"sort.csv");copy<<std::setprecision(17)<<"integrator,axis,source_slot,destination_slot,native_id,x,z,kappa,raw_DK,kappaM1,all_fields_exact\n";sorted<<std::setprecision(17)<<"integrator,destination_slot,source_slot,native_id,x,z,kappa,raw_DK,kappaM1,history_fields_exact\n";
  for(bool sym:{true,false}){Patch p(sym);p.Run(copy,sorted,out);}copy.flush();sorted.flush();Need(bool(copy)&&bool(sorted),"Copy/sort output failed");std::ofstream done(out/"completion.json");done<<"{\"stage\":\"upl_material_periodic_gpu_r2\",\"passed\":true,\"actual_periodic_copy_calls\":4,\"copy_rows\":8,\"public_Divide_calls\":2,\"public_SortBasicArrays_calls\":2,\"public_history_SortDataArrays_calls\":5,\"sort_rows\":12,\"nonidentity_permutation\":true,\"Verlet_current_M1_DK\":true,\"Symplectic_no_M1_allocation\":true,\"all_defined_copy_fields_and_tails_exact\":true,\"sort_scope\":\"basic_identity_and_current_M1_DK\",\"InitRun_force_integrator_or_new_kernel\":false,\"physical_steps\":0,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}}
