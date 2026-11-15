// Ten isolated stage1 queries of the separately built C-quality retry candidate.
// This main is not a physical solver, restart, parameter search or general SPD proof.
#include "JSphGpu_ker.h"
#include "Functions.h"
#include "JAppInfo.h"
#include <cuda_runtime_api.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("DualSPHysics5","v5.2.274","02-02-2024");
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
  Need(p.mode[p.target]!=BMODE_MDBC2OFF&&p.normal[p.target].x==0&&p.normal[p.target].y==0&&p.normal[p.target].z>0,"closed target normal/mode differs");
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
std::vector<double> Values(const tmatrix3d& m){return {m.a11,m.a12,m.a13,m.a21,m.a22,m.a23,m.a31,m.a32,m.a33};}
bool Finite(const tmatrix3d& m){for(double v:Values(m))if(!std::isfinite(v))return false;return true;}
double Det(const tmatrix3d& m){return m.a11*m.a33-m.a13*m.a31;}
void Number(std::ostream& o,double x){if(std::isfinite(x))o<<std::setprecision(17)<<x;else o<<"null";}
void Matrix(std::ostream& o,const tmatrix3d& m){
  const std::vector<double> values=Values(m);o<<'[';for(unsigned k=0;k<9;k++){if(k)o<<',';Number(o,values[k]);}o<<']';
}
void MatrixHex(std::ostream& o,const tmatrix3d& m){
  const std::vector<double> values=Values(m);o<<'[';for(unsigned k=0;k<9;k++){if(k)o<<',';o<<'"'<<Hex(values[k])<<'"';}o<<']';
}
enum Field{Actual,Identity,ConstantSPD,AffineSPD,AffineNegative,Overflow};
struct Fixture{const char* name;const char* purpose;const char* modifications;Field field;bool target_only,reject,normal02,bad_j,bad_c,zero_shift,compare_expected;};
const Fixture SUITE[]={
  {"01_actual_packet","actual captured C and mask with the candidate","none",Actual,false,false,false,false,false,false,false},
  {"02_constant_I","constant reproduction","5000 fluid C become identity",Identity,false,false,false,false,false,false,true},
  {"03_constant_SPD","constant tensor parity reproduction","5000 fluid C become prescribed constant SPD",ConstantSPD,false,false,false,false,false,false,true},
  {"04_affine_SPD","affine tensor at original G and Q parity","5000 fluid C become prescribed affine SPD field",AffineSPD,false,false,false,false,false,false,true},
  {"05_negative_affine","finite nonpositive target must remain rejected","target-only mode; affine C11=z-(Gz+.01)",AffineNegative,true,true,false,false,false,false,false},
  {"06_normal02_negative_affine","shifted geometry and negative target must remain rejected","target-only mode; normal.z=float(.02); negative affine field",AffineNegative,true,true,true,false,false,false,false},
  {"07_nearest_J_solid0","invalid donor J remains hard failure","target-only mode; native7030 J=solid0",Actual,true,true,false,true,false,false,false},
  {"08_nearest_C_NaN","nonfinite donor C remains hard failure","target-only mode; native7030 C11=NaN",Actual,true,true,false,false,true,false,false},
  {"09_finite_C_overflow_det","nonfinite reconstructed determinant remains hard failure","target-only mode; C11=C33=1e200 C22=1",Overflow,true,true,false,false,false,false,false},
  {"10_zero_shift_negative_affine","zero nearest recenter cannot introduce another fallback","target-only mode; move B so G equals native7030; negative affine field",AffineNegative,true,true,false,false,false,true,false}
};
const unsigned NFIX=sizeof(SUITE)/sizeof(SUITE[0]);
tmatrix3d FieldValue(Field field,double x,double z,double gz){
  tmatrix3d m={};m.a11=m.a22=m.a33=1.;
  if(field==ConstantSPD||field==AffineSPD){m.a11=2.;m.a22=1.2;m.a33=1.5;m.a13=m.a31=.1;}
  if(field==AffineSPD){m.a11=2.+.01*x+.02*z;m.a33=1.5+.02*x-.01*z;m.a13=m.a31=.1+.005*x;}
  if(field==AffineNegative)m.a11=z-(gz+.01);
  if(field==Overflow)m.a11=m.a33=1e200;
  return m;
}
tmatrix3d Parity(const tmatrix3d& m,const float3& bn){
  const double r2=double(bn.x)*bn.x+double(bn.y)*bn.y+double(bn.z)*bn.z;
  const double qx=(double(bn.x)*bn.x>.5*r2?-1.:1.),qy=(double(bn.y)*bn.y>.5*r2?-1.:1.),qz=(double(bn.z)*bn.z>.5*r2?-1.:1.);
  tmatrix3d v=m;v.a12*=qx*qy;v.a13*=qx*qz;v.a21*=qy*qx;v.a23*=qy*qz;v.a31*=qz*qx;v.a32*=qz*qy;return v;
}
unsigned NearestSlot(const Packet& p){
  unsigned found=p.np;for(unsigned i=0;i<p.np;i++)if(p.id[i]==7030){Need(found==p.np,"duplicate native7030");found=i;}
  Need(found==2140&&CODE_IsFluid(p.code[found]),"captured nearest native7030 slot differs");return found;
}
Packet Prepare(const Packet& original,const Fixture& f,unsigned& assigned,unsigned& changed){
  Packet p=original;assigned=changed=0;const unsigned near=NearestSlot(p);
  if(f.target_only){for(unsigned i=0;i<p.nb;i++)p.mode[i]=BMODE_MDBC2OFF;p.mode[p.target]=BMODE_MDBC2;}
  if(f.normal02)p.normal[p.target].z=.02f;
  if(f.zero_shift){
    p.xy[p.target].x=p.xy[near].x;p.z[p.target]=p.z[near]-double(p.normal[p.target].z);
    Need(p.xy[p.target].x+double(p.normal[p.target].x)==p.xy[near].x
      &&p.z[p.target]+double(p.normal[p.target].z)==p.z[near],"zero-shift mirror is not exactly the nearest donor");
  }
  const double gz=p.z[p.target]+double(p.normal[p.target].z);
  if(f.field!=Actual)for(unsigned i=0;i<p.np;i++)if(CODE_IsFluid(p.code[i])){
    const tmatrix3d v=FieldValue(f.field,p.xy[i].x,p.z[i],gz);changed+=unsigned(std::memcmp(&v,&p.corr[i],sizeof(v))!=0);p.corr[i]=v;assigned++;
  }
  Need(f.field==Actual||assigned==5000,"manufactured tensor field must cover exactly5000 fluid donors");
  if(f.bad_j)p.j[near]=p.d[3];
  if(f.bad_c)p.corr[near].a11=(std::numeric_limits<double>::quiet_NaN)();
  for(unsigned i=0;i<p.np;i++)if(!CODE_IsFluid(p.code[i]))Need(std::memcmp(&p.corr[i],&original.corr[i],sizeof(tmatrix3d))==0,"fixture changed fixed input C");
  return p;
}
void Walls(const std::string& path,const Packet& p,const std::vector<tmatrix3d>& after,unsigned invalid,bool target_only){
  Need(!fun::FileExists(path)&&!fun::DirExists(path),"existing result CSV protected");std::ofstream o(path);o.imbue(std::locale::classic());Need(bool(o),"result CSV open failed");
  o<<"sorted_wall_slot,native_ID,actual_mode,component_target_only_mask,selected_aggregate_invalid,changed_bits";
  const char* names[]={"11","12","13","21","22","23","31","32","33"};
  for(const char* n:names)o<<",before_a"<<n<<"_17,before_a"<<n<<"_hex,after_a"<<n<<"_17,after_a"<<n<<"_hex";o<<'\n';
  for(unsigned i=0;i<p.nb;i++){
    o<<i<<','<<p.id[i]<<','<<unsigned(p.mode[i])<<','<<unsigned(target_only)<<','<<unsigned(i==invalid)<<','<<unsigned(std::memcmp(&p.corr[i],&after[i],sizeof(tmatrix3d))!=0);
    const std::vector<double> a=Values(p.corr[i]),b=Values(after[i]);
    for(unsigned k=0;k<9;k++)o<<','<<std::setprecision(17)<<a[k]<<','<<Hex(a[k])<<','<<b[k]<<','<<Hex(b[k]);o<<'\n';
  }
  o.flush();Need(bool(o),"result CSV write failed");
}
struct Result{
  bool completed=false,verified=false,target_changed=false,target_finite=false;
  unsigned invalid=0,assigned=0,changed=0,active=0,disabled=0;double gx=0,gz=0,target_det=0,error=0,scale=1;
  tmatrix3d before={},after={},expected={};
};
Result Query(const Packet& p,const Fixture& f,const std::string& path,unsigned& wrapper_calls,unsigned assigned,unsigned changed){
  Result r;r.assigned=assigned;r.changed=changed;
  for(unsigned i=0;i<p.nb;i++)(p.mode[i]==BMODE_MDBC2OFF?r.disabled:r.active)++;
  Need(!f.target_only||(r.active==1&&r.disabled==939&&p.mode[p.target]!=BMODE_MDBC2OFF),"target-only component mode selection differs");
  Device<unsigned> id(p.np),dcell(p.np),invalid(1);Device<typecode> code(p.np);Device<double2> xy(p.np);
  Device<double> z(p.np),j(p.np);Device<float4> pc(p.np);Device<tmatrix3d> c(p.np);Device<float3> normal(p.nb);Device<byte> mode(p.nb);
  Device<int2> table(p.cellfluid+p.nct);std::vector<int2> padding(p.cellfluid+p.nct);
  for(unsigned i=0;i<p.nct;i++)padding[p.cellfluid+i]=p.cells[i];
  // Fresh allocations and uploads for every query; no prior target C is inherited.
  id.Up(p.id);dcell.Up(p.dcell);code.Up(p.code);xy.Up(p.xy);z.Up(p.z);j.Up(p.j);pc.Up(p.pc);c.Up(p.corr);normal.Up(p.normal);mode.Up(p.mode);table.Up(padding);invalid.Up(std::vector<unsigned>(1,p.np));
  Need(std::memcmp(pc.Down().data(),p.pc.data(),p.np*sizeof(float4))==0,"PosCell upload raw bits differ");
  StCteInteraction cte={};cte.massf=p.f[0];cte.rhopzero=p.f[1];cte.kernelh=p.f[2];cte.kernelsize2=p.f[3];cte.poscellsize=p.f[4];
  cte.scell=p.f[5];cte.awen=p.f[6];cte.bwen=p.f[7];cte.gravityx=p.f[8];cte.gravityy=p.f[9];cte.gravityz=p.f[10];cte.porewaterrho=p.f[11];cte.dp=p.f[13];
  cte.domposminx=p.d[0];cte.domposminy=p.d[1];cte.domposminz=p.d[2];cte.axis=p.axis;cte.cellcode=p.cellcode;cte.simulate2d=p.sim2d;cte.periactive=p.peri;cte.slipmode=p.slip;
  cusph::CteInteractionUp(&cte);Cuda(cudaGetLastError(),"candidate CTE upload");
  StDivDataGpu dvd=DivDataGpuNull();dvd.axis=TpMgDivMode(p.axis);dvd.ncells=p.ncells;dvd.scelldiv=int(p.scelldiv);dvd.nc=p.nc;dvd.cellzero=p.zero;dvd.cellfluid=p.cellfluid;dvd.beginendcell=table.p;
  dvd.scell=p.f[5];dvd.domcellcode=p.cellcode;dvd.domposmin.x=p.d[0];dvd.domposmin.y=p.d[1];dvd.domposmin.z=p.d[2];dvd.kernelsize2=p.f[3];dvd.poscellsize=p.f[4];
  // Read<1> only consumes C. Per-MK slip and all unused stage0/2 fields are null.
  wrapper_calls++;
  cusph::DynamicPoreWall(1,p.np,p.nb,p.f[12],dvd,xy.p,z.p,code.p,normal.p,mode.p,NULL,NULL,NULL,NULL,NULL,j.p,NULL,c.p,NULL,p.d[3],invalid.p,KERNEL_Wendland,NULL,pc.p);
  Cuda(cudaGetLastError(),"candidate stage1 launch");Cuda(cudaDeviceSynchronize(),"candidate stage1 synchronize");
  r.invalid=invalid.Down()[0];const std::vector<tmatrix3d> after=c.Down();Walls(path,p,after,r.invalid,f.target_only);
  for(unsigned i=0;i<p.np;i++)if(CODE_IsFluid(p.code[i])||(i<p.nb&&p.mode[i]==BMODE_MDBC2OFF))
    Need(std::memcmp(&after[i],&p.corr[i],sizeof(tmatrix3d))==0,"query modified donor or disabled-wall C");
  r.before=p.corr[p.target];r.after=after[p.target];r.target_changed=std::memcmp(&r.before,&r.after,sizeof(tmatrix3d))!=0;
  r.target_finite=Finite(r.after);r.target_det=Det(r.after);r.gx=p.xy[p.target].x+double(p.normal[p.target].x);r.gz=p.z[p.target]+double(p.normal[p.target].z);
  if(f.compare_expected){
    r.expected=Parity(FieldValue(f.field,r.gx,r.gz,r.gz),p.normal[p.target]);
    const std::vector<double> actual=Values(r.after),expected=Values(r.expected);
    for(unsigned k=0;k<9;k++){r.error=(std::max)(r.error,std::abs(actual[k]-expected[k]));r.scale=(std::max)(r.scale,std::abs(expected[k]));}
  }
  r.completed=true;
  r.verified=f.reject?(r.invalid==p.target&&!r.target_changed)
    :(r.invalid==p.np&&r.target_changed&&r.target_finite&&std::isfinite(r.target_det)&&r.target_det>0
      &&(!f.compare_expected||r.error<=1e-8*r.scale));
  return r;
}
void Completion(const std::string& dir,bool passed,const std::vector<Result>& results,unsigned wrapper_calls,const std::string& error){
  const std::string path=dir+"/completion.json";Need(!fun::FileExists(path)&&!fun::DirExists(path),"completion already exists; preserve partial output");
  std::ofstream o(path);o.imbue(std::locale::classic());Need(bool(o),"completion open failed");unsigned successful=0;for(const Result& r:results)successful+=unsigned(r.completed);
  o<<"{\"schema\":1,\"passed\":"<<(passed?"true":"false")<<",\"fixture_count\":"<<NFIX<<",\"kernel_wrapper_calls_attempted\":"<<wrapper_calls<<",\"successful_core_queries\":"<<successful
    <<",\"reported_invalid_is_aggregate_min_not_all_wall_status\":true,\"host_mapping_not_direct_original_device_CTE_snapshot\":true,\"component_target_only_mask_is_not_physical_mask_repair\":true"
    <<",\"GPU_retry_counter_observed\":false,\"GPU_M_C_registers_observed\":false,\"general_SPD_preservation_proved\":false,\"expected_tensor_relative_tolerance\":1e-8,\"physical_repair\":false,\"physical_acceptance\":false,\"solver_invocations\":0,\"fixtures\":[";
  for(unsigned i=0;i<NFIX;i++){
    if(i)o<<',';const Fixture& f=SUITE[i];const Result& r=results[i];
    o<<"{\"name\":\""<<f.name<<"\",\"purpose\":\""<<f.purpose<<"\",\"modifications\":\""<<f.modifications<<"\",\"query_completed\":"<<(r.completed?"true":"false")<<",\"verified\":"<<(r.verified?"true":"false")
      <<",\"expected_rejection\":"<<(f.reject?"true":"false")<<",\"component_target_only_mask\":"<<(f.target_only?"true":"false")<<",\"aggregate_invalid\":"<<r.invalid<<",\"active_wall_modes\":"<<r.active<<",\"disabled_wall_modes\":"<<r.disabled
      <<",\"assigned_fluid_C\":"<<r.assigned<<",\"changed_fluid_C_rows\":"<<r.changed<<",\"target_C_changed\":"<<(r.target_changed?"true":"false")<<",\"target_C_finite\":"<<(r.target_finite?"true":"false")<<",\"actual_Gx\":";Number(o,r.gx);o<<",\"actual_Gz\":";Number(o,r.gz);
    o<<",\"target_C_det\":";Number(o,r.target_det);o<<",\"target_C_det_hex\":\""<<Hex(r.target_det)<<"\",\"expected_tensor_compared\":"<<(f.compare_expected?"true":"false")<<",\"target_max_component_error\":";Number(o,r.error);o<<",\"expected_scale\":";Number(o,r.scale);
    o<<",\"target_before_17\":";Matrix(o,r.before);o<<",\"target_before_hex\":";MatrixHex(o,r.before);o<<",\"target_after_17\":";Matrix(o,r.after);o<<",\"target_after_hex\":";MatrixHex(o,r.after);
    o<<",\"expected_Q_C_G_Q_17\":";Matrix(o,r.expected);o<<",\"all940_wall_C_before_after_exported\":"<<(r.completed?"true":"false")<<'}';
  }
  o<<"],\"error_code\":\""<<(error.empty()?"":"component_failed_see_stderr")<<"\"}\n";o.flush();Need(bool(o),"completion flush failed");
}
}
int main(int argc,char** argv){
  static_assert(sizeof(unsigned)==4&&sizeof(float)==4&&sizeof(double)==8&&sizeof(tmatrix3d)==72,"original ABI required");
  std::vector<Result> results(NFIX);bool created=false;unsigned wrapper_calls=0;std::string out;
  try{
    Need(argc==3,"use fixture.bin FRESHOUT");const unsigned endian=1;Need(*reinterpret_cast<const unsigned char*>(&endian)==1,"little-endian host required");
    out=argv[2];Need(fun::Mkdir(out)==0,"fresh output directory required; no overwrite");created=true;
    const Packet original=Load(argv[1]);Cuda(cudaSetDevice(0),"select actual device0");
    for(unsigned i=0;i<NFIX;i++){
      unsigned assigned=0,changed=0;const Packet p=Prepare(original,SUITE[i],assigned,changed);
      results[i]=Query(p,SUITE[i],out+"/"+SUITE[i].name+"_walls.csv",wrapper_calls,assigned,changed);
      std::printf("RETRY_COMPONENT_QUERY %s aggregate_invalid=%u target_changed=%u target_det=%.17g verified=%u\n",SUITE[i].name,results[i].invalid,unsigned(results[i].target_changed),results[i].target_det,unsigned(results[i].verified));
      Need(results[i].verified,"fixture expected accept/reject or tensor reproduction failed; preserve outputs");
    }
    Completion(out,true,results,wrapper_calls,"");std::printf("RETRY_COMPONENT_PASSED queries=%u; component only, no physical repair selected\n",wrapper_calls);return 0;
  }catch(const std::exception& e){
    std::fprintf(stderr,"RETRY_COMPONENT_FAILED %s\n",e.what());if(created)try{Completion(out,false,results,wrapper_calls,e.what());}catch(...){}
    return 1;
  }
}
