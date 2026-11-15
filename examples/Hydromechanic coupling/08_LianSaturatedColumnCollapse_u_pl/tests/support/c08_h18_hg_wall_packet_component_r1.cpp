// Isolated query of the retained original Release stage1 CUDA kernel, not a solver.
#include "JSphGpu_ker.h"
#include "Functions.h"
#include <cuda_runtime_api.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
void Need(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
void Cuda(cudaError_t e,const char* why){if(e!=cudaSuccess)throw std::runtime_error(std::string(why)+": "+cudaGetErrorString(e));}
template<class T> T Read(std::istream& in){T q={};in.read(reinterpret_cast<char*>(&q),sizeof(q));Need(bool(in),"truncated fixture scalar");return q;}
template<class T> void ReadArray(std::istream& in,const char* name,unsigned kind,unsigned components,size_t count,std::vector<T>& out){
  char leaf[16]={};in.read(leaf,16);Need(bool(in)&&std::string(leaf,leaf+std::strlen(name))==name&&leaf[std::strlen(name)]==0,"fixture array name/order differs");
  const unsigned k=Read<unsigned>(in),c=Read<unsigned>(in);const std::uint64_t n=Read<std::uint64_t>(in),bytes=Read<std::uint64_t>(in);
  Need(k==kind&&c==components&&n==count&&bytes==count*sizeof(T),"fixture dtype/components/count/bytes differ");
  out.resize(count);in.read(reinterpret_cast<char*>(out.data()),std::streamsize(bytes));Need(bool(in),"truncated fixture array");
}
struct Packet{
  unsigned np,npb,nb,nct,cellfluid,target,codebytes,stage,kernel,axis,sim2d,peri,slip,cellcode,scelldiv;
  std::uint64_t step;int4 nc;int3 zero;tuint3 ncells;float f[14];double d[5];
  std::vector<unsigned> id,dcell;std::vector<typecode> code;std::vector<double2> xy;std::vector<double> z,j;
  std::vector<float4> pc;std::vector<tmatrix3d> corr;std::vector<float3> normal;std::vector<byte> mode;std::vector<int2> cells;
};
Packet Load(const char* path){
  std::ifstream in(path,std::ios::binary);Need(bool(in),"fixture open failed");char magic[8];in.read(magic,8);
  Need(bool(in)&&std::memcmp(magic,"C08WPK1\0",8)==0,"fixture magic differs");Need(Read<unsigned>(in)==1,"fixture version differs");
  Packet p;p.np=Read<unsigned>(in);p.npb=Read<unsigned>(in);p.nb=Read<unsigned>(in);p.nct=Read<unsigned>(in);p.cellfluid=Read<unsigned>(in);
  p.target=Read<unsigned>(in);p.codebytes=Read<unsigned>(in);p.stage=Read<unsigned>(in);p.kernel=Read<unsigned>(in);p.axis=Read<unsigned>(in);
  p.sim2d=Read<unsigned>(in);p.peri=Read<unsigned>(in);p.slip=Read<unsigned>(in);p.cellcode=Read<unsigned>(in);p.scelldiv=Read<unsigned>(in);p.step=Read<std::uint64_t>(in);
  p.nc.x=Read<int>(in);p.nc.y=Read<int>(in);p.nc.z=Read<int>(in);p.nc.w=Read<int>(in);
  p.zero.x=Read<int>(in);p.zero.y=Read<int>(in);p.zero.z=Read<int>(in);
  p.ncells.x=Read<unsigned>(in);p.ncells.y=Read<unsigned>(in);p.ncells.z=Read<unsigned>(in);
  for(float& v:p.f)v=Read<float>(in);for(double& v:p.d)v=Read<double>(in);
  Need(p.np==6805&&p.npb==1805&&p.nb==940&&p.nct==608&&p.cellfluid==609&&p.target==690
    &&p.codebytes==sizeof(typecode)&&p.stage==1&&p.kernel==unsigned(KERNEL_Wendland)&&p.axis==unsigned(MGDIV_Z)
    &&p.sim2d==1&&p.peri==0&&p.slip==3&&p.step==2196678,"only the actual closed failed packet is admitted");
  Need(p.nc.x==38&&p.nc.y==1&&p.nc.z==16&&p.nc.w==38&&p.scelldiv==1&&Read<unsigned>(in)==11,"actual cell/array extent differs");
  ReadArray(in,"Idp",3,1,p.np,p.id);ReadArray(in,"Code",sizeof(typecode)==2?2:3,1,p.np,p.code);
  ReadArray(in,"Posxy",6,2,p.np,p.xy);ReadArray(in,"Posz",6,1,p.np,p.z);ReadArray(in,"PosCell",5,4,p.np,p.pc);
  ReadArray(in,"Dcell",3,1,p.np,p.dcell);ReadArray(in,"PoroJ",6,1,p.np,p.j);ReadArray(in,"CorrMat",6,9,p.np,p.corr);
  ReadArray(in,"BoundNormal",5,3,p.nb,p.normal);ReadArray(in,"BoundMode",1,1,p.nb,p.mode);ReadArray(in,"FluidCells",4,2,p.nct,p.cells);
  Need(in.peek()==std::char_traits<char>::eof(),"fixture has trailing bytes");Need(p.id[p.target]==894,"actual target native identity differs");
  unsigned fluid=0;for(unsigned i=0;i<p.np;i++)fluid+=unsigned(CODE_IsFluid(p.code[i]));Need(fluid==5000,"fluid count differs");
  for(unsigned i=0;i<p.nb;i++)Need(CODE_IsFixed(p.code[i]),"receiver prefix is not actual fixed particles");
  return p;
}
template<class T> struct Device{
  T* p;size_t n;explicit Device(size_t count):p(NULL),n(count){Cuda(cudaMalloc(reinterpret_cast<void**>(&p),n*sizeof(T)),"cudaMalloc");}
  ~Device(){if(p)cudaFree(p);}Device(const Device&)=delete;Device& operator=(const Device&)=delete;
  void Up(const std::vector<T>& v){Need(v.size()==n,"upload extent differs");Cuda(cudaMemcpy(p,v.data(),n*sizeof(T),cudaMemcpyHostToDevice),"upload");}
  std::vector<T> Down(){std::vector<T> v(n);Cuda(cudaMemcpy(v.data(),p,n*sizeof(T),cudaMemcpyDeviceToHost),"download");return v;}
};
template<class T> std::string Hex(T value){
  std::uint64_t v=0;std::memcpy(&v,&value,sizeof(value));std::ostringstream o;o.imbue(std::locale::classic());
  o<<std::hex<<std::setfill('0')<<std::setw(2*sizeof(value))<<v;return o.str();
}
void Walls(const std::string& path,const Packet& p,const std::vector<tmatrix3d>& before,const std::vector<tmatrix3d>& after,unsigned invalid){
  Need(!fun::FileExists(path)&&!fun::DirExists(path),"existing result CSV protected");std::ofstream o(path);o.imbue(std::locale::classic());Need(bool(o),"result CSV open failed");
  o<<"sorted_wall_slot,native_ID,actual_mode,selected_aggregate_invalid,changed_bits";
  const char* names[]={"11","12","13","21","22","23","31","32","33"};
  for(const char* n:names)o<<",before_a"<<n<<"_17,before_a"<<n<<"_hex,after_a"<<n<<"_17,after_a"<<n<<"_hex";o<<'\n';
  for(unsigned i=0;i<p.nb;i++){
    o<<i<<','<<p.id[i]<<','<<unsigned(p.mode[i])<<','<<unsigned(i==invalid)<<','<<unsigned(std::memcmp(&before[i],&after[i],sizeof(tmatrix3d))!=0);
    const tmatrix3d& x=before[i];const tmatrix3d& y=after[i];
    const double a[]={x.a11,x.a12,x.a13,x.a21,x.a22,x.a23,x.a31,x.a32,x.a33};
    const double b[]={y.a11,y.a12,y.a13,y.a21,y.a22,y.a23,y.a31,y.a32,y.a33};
    for(unsigned k=0;k<9;k++)o<<','<<std::setprecision(17)<<a[k]<<','<<Hex(a[k])<<','<<b[k]<<','<<Hex(b[k]);o<<'\n';
  }
  o.flush();Need(bool(o),"result CSV write failed");
}
struct Result{unsigned invalid,assigned,changed;double target_det;bool target_changed;};
Result Query(const Packet& p,bool identity,const std::string& path,unsigned& wrapper_calls){
  std::vector<tmatrix3d> corr=p.corr;unsigned assigned=0,changed=0;
  if(identity)for(unsigned i=0;i<p.np;i++)if(CODE_IsFluid(p.code[i])){
    tmatrix3d one={};one.a11=one.a22=one.a33=1.;changed+=unsigned(std::memcmp(&one,&corr[i],sizeof(one))!=0);corr[i]=one;assigned++;
  }
  Need(!identity||assigned==5000,"counterfactual must assign exactly5000 fluid matrices");
  for(unsigned i=0;i<p.np;i++)if(!CODE_IsFluid(p.code[i]))Need(std::memcmp(&corr[i],&p.corr[i],sizeof(tmatrix3d))==0,"boundary C changed in counterfactual");
  Device<unsigned> id(p.np),dcell(p.np),invalid(1);Device<typecode> code(p.np);Device<double2> xy(p.np);
  Device<double> z(p.np),j(p.np);Device<float4> pc(p.np);Device<tmatrix3d> c(p.np);Device<float3> normal(p.nb);Device<byte> mode(p.nb);
  Device<int2> table(p.cellfluid+p.nct);std::vector<int2> padding(p.cellfluid+p.nct);
  for(unsigned i=0;i<p.nct;i++)padding[p.cellfluid+i]=p.cells[i];
  // Every core query creates and uploads a completely fresh packet. Padding is
  // initialized, not claimed captured; only the actual offset fluid block is used.
  id.Up(p.id);dcell.Up(p.dcell);code.Up(p.code);xy.Up(p.xy);z.Up(p.z);j.Up(p.j);pc.Up(p.pc);c.Up(corr);normal.Up(p.normal);mode.Up(p.mode);table.Up(padding);invalid.Up(std::vector<unsigned>(1,p.np));
  Need(std::memcmp(pc.Down().data(),p.pc.data(),p.np*sizeof(float4))==0,"PosCell upload raw bits differ");
  StCteInteraction cte={};cte.massf=p.f[0];cte.rhopzero=p.f[1];cte.kernelh=p.f[2];cte.kernelsize2=p.f[3];cte.poscellsize=p.f[4];
  cte.scell=p.f[5];cte.awen=p.f[6];cte.bwen=p.f[7];cte.gravityx=p.f[8];cte.gravityy=p.f[9];cte.gravityz=p.f[10];cte.porewaterrho=p.f[11];cte.dp=p.f[13];
  cte.domposminx=p.d[0];cte.domposminy=p.d[1];cte.domposminz=p.d[2];cte.axis=p.axis;cte.cellcode=p.cellcode;cte.simulate2d=p.sim2d;cte.periactive=p.peri;cte.slipmode=p.slip;
  cusph::CteInteractionUp(&cte);Cuda(cudaGetLastError(),"original CTE upload");
  StDivDataGpu dvd=DivDataGpuNull();dvd.axis=TpMgDivMode(p.axis);dvd.ncells=p.ncells;dvd.scelldiv=int(p.scelldiv);dvd.nc=p.nc;dvd.cellzero=p.zero;dvd.cellfluid=p.cellfluid;dvd.beginendcell=table.p;
  dvd.scell=p.f[5];dvd.domcellcode=p.cellcode;dvd.domposmin.x=p.d[0];dvd.domposmin.y=p.d[1];dvd.domposmin.z=p.d[2];dvd.kernelsize2=p.f[3];dvd.poscellsize=p.f[4];
  // stage1 short-circuits stage==0 before reading per-MK slip. Read<1> consumes
  // only donor CorrMat; all other unused field pointers are explicitly null.
  wrapper_calls++;
  cusph::DynamicPoreWall(1,p.np,p.nb,p.f[12],dvd,xy.p,z.p,code.p,normal.p,mode.p,NULL,NULL,NULL,NULL,NULL,j.p,NULL,c.p,NULL,p.d[3],invalid.p,KERNEL_Wendland,NULL,pc.p);
  Cuda(cudaGetLastError(),"original stage1 launch");Cuda(cudaDeviceSynchronize(),"original stage1 synchronize");
  const unsigned rejected=invalid.Down()[0];const std::vector<tmatrix3d> after=c.Down();Walls(path,p,corr,after,rejected);
  const tmatrix3d& target=after[p.target];
  return {rejected,assigned,changed,target.a11*target.a33-target.a13*target.a31,std::memcmp(&target,&corr[p.target],sizeof(target))!=0};
}
void Completion(const std::string& dir,bool passed,const Result& a,const Result& b,bool have_a,bool have_b,unsigned wrapper_calls,const std::string& error){
  // Error text is emitted to stderr verbatim; JSON has a closed reason code only.
  const std::string path=dir+"/completion.json";Need(!fun::FileExists(path)&&!fun::DirExists(path),"completion already exists; preserve partial output");
  std::ofstream o(path);o.imbue(std::locale::classic());Need(bool(o),"completion open failed");
  o<<"{\"schema\":1,\"passed\":"<<(passed?"true":"false")<<",\"baseline_invalid\":"<<a.invalid<<",\"baseline_numeric_rejection_not_CUDA_runtime_error\":"<<(a.invalid==690?"true":"false")
    <<",\"baseline_query_completed\":"<<(have_a?"true":"false")<<",\"identity_query_completed\":"<<(have_b?"true":"false")<<",\"identity_invalid\":"<<b.invalid<<",\"identity_assigned_fluid\":"<<b.assigned<<",\"identity_changed_fluid_rows\":"<<b.changed
    <<",\"identity_target_C_changed\":"<<(b.target_changed?"true":"false")<<",\"identity_target_C_det\":"<<std::setprecision(17)<<b.target_det
    <<",\"reported_invalid_is_aggregate_min_not_all_wall_status\":true,\"all940_wall_C_before_after_exported\":"<<(passed?"true":"false")
    <<",\"host_mapping_not_direct_original_device_CTE_snapshot\":true,\"physical_repair\":false,\"physical_acceptance\":false,\"solver_invocations\":0,\"kernel_wrapper_calls_attempted\":"<<wrapper_calls<<",\"successful_core_queries\":"<<(unsigned(have_a)+unsigned(have_b))
    <<",\"error_code\":\""<<(error.empty()?"":"component_failed_see_stderr")<<"\"}\n";o.flush();Need(bool(o),"completion flush failed");
}
}
int main(int argc,char** argv){
  static_assert(sizeof(unsigned)==4&&sizeof(float)==4&&sizeof(double)==8&&sizeof(tmatrix3d)==72,"original ABI required");
  Result a={},b={};bool have_a=false,have_b=false,created=false;unsigned wrapper_calls=0;std::string out;
  try{
    Need(argc==3,"use fixture.bin FRESHOUT");const unsigned endian=1;Need(*reinterpret_cast<const unsigned char*>(&endian)==1,"little-endian host required");
    out=argv[2];Need(fun::Mkdir(out)==0,"fresh output directory required; no overwrite");created=true;
    const Packet p=Load(argv[1]);Cuda(cudaSetDevice(0),"select actual device0");
    a=Query(p,false,out+"/actual_C_walls.csv",wrapper_calls);have_a=true;Need(a.invalid==p.target,"original compiled-kernel baseline did not reproduce invalid690; no counterfactual admitted");
    b=Query(p,true,out+"/identity_C_walls.csv",wrapper_calls);have_b=true;
    Completion(out,true,a,b,have_a,have_b,wrapper_calls,"");std::printf("PACKET_COMPONENT_PASSED actual_invalid=%u identity_invalid=%u target_det=%.17g; not a physical repair\n",a.invalid,b.invalid,b.target_det);return 0;
  }catch(const std::exception& e){
    std::fprintf(stderr,"PACKET_COMPONENT_FAILED %s\n",e.what());if(created)try{Completion(out,false,a,b,have_a,have_b,wrapper_calls,e.what());}catch(...){}
    return 1;
  }
}
