// Component only: calls actual project CUDA sort overloads and JCellDivGpu wrappers.
// No solver, particle dynamics, J state, replacement kernel or private-access macro.
#include "JAppInfo.h"
#include "JCellDivGpu.h"
#include "JCellDivGpu_ker.h"
#include <cuda_runtime_api.h>
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("GpuDoubleSortComponent","r1","01-11-2026");
namespace fs=std::filesystem;
static constexpr unsigned Guard=17;
static void Need(bool b,const std::string& s){if(!b)throw std::runtime_error(s);}
static void Cu(cudaError_t e,const std::string& s){Need(e==cudaSuccess,s+": "+cudaGetErrorString(e));}
template<class T> static T Bits(std::uint64_t bits){T value{};std::memcpy(&value,&bits,sizeof(T));return value;}
template<class T> struct Buffer{
  T* p=nullptr;unsigned count;
  explicit Buffer(unsigned n):count(n){Cu(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*n),"allocate component buffer");}
  ~Buffer(){if(p)cudaFree(p);}
  Buffer(const Buffer&)=delete;Buffer& operator=(const Buffer&)=delete;
  void Up(const std::vector<T>& v){Need(v.size()==count,"upload size");Cu(cudaMemcpy(p,v.data(),sizeof(T)*count,cudaMemcpyHostToDevice),"upload");}
  std::vector<T> Down()const{std::vector<T> v(count);Cu(cudaMemcpy(v.data(),p,sizeof(T)*count,cudaMemcpyDeviceToHost),"download");return v;}
};
class SortFixture:public JCellDivGpu{
public:
  SortFixture():JCellDivGpu(true,false,0,4.f,2.f,true,CELLMODE_Full,1.f,
    TDouble3(0),TDouble3(1),TUint3(1),0,0,0,"",false,0,0){}
  // This fixture owns the uploaded map. Detach before the base Reset/destructor.
  ~SortFixture(){if(SortPart)cudaFree(SortPart);SortPart=nullptr;}
  void Configure(unsigned n,unsigned prefix,bool full,const std::vector<unsigned>& map){
    if(SortPart){Cu(cudaFree(SortPart),"release previous sort map");SortPart=nullptr;}
    Nptot=n;NpbFinal=prefix;DivideFull=full;
    Cu(cudaMalloc(reinterpret_cast<void**>(&SortPart),sizeof(unsigned)*map.size()),"allocate actual wrapper map");
    Cu(cudaMemcpy(SortPart,map.data(),sizeof(unsigned)*map.size(),cudaMemcpyHostToDevice),"upload actual wrapper map");
  }
  const unsigned* Map()const{return SortPart;}
  std::vector<unsigned> DownloadMap(unsigned n)const{std::vector<unsigned> out(n);Cu(cudaMemcpy(out.data(),SortPart,sizeof(unsigned)*n,cudaMemcpyDeviceToHost),"read map");return out;}
};
static double DoubleValue(unsigned i,bool target=false){
  const std::uint64_t special[]={0,0x8000000000000000ull,1,0x8000000000000001ull,
    0x0010000000000000ull,0x8010000000000000ull,0x3ff0000000000001ull,0x3ff0000000000002ull,
    0x7fd0000000000000ull,0xffd0000000000000ull,0x3e10000000000001ull,0xbe10000000000001ull,
    0x4000000000000001ull,0xc000000000000001ull,0x3fd0000000000001ull,0xbfd0000000000001ull};
  return Bits<double>(target?(0x4080000000000000ull+i):(i<16?special[i]:0x3ff0000000000020ull+i));
}
static float FloatValue(unsigned i,bool target=false){
  const std::uint32_t special[]={0,0x80000000u,1,0x80000001u,0x00800000u,0x80800000u,
    0x3f800001u,0x3f800002u,0x7e800000u,0xfe800000u,0x3a800001u,0xba800001u,
    0x40000001u,0xc0000001u,0x3e800001u,0xbe800001u};
  return Bits<float>(target?(0x44800000u+i):(i<16?special[i]:0x3f800020u+i));
}
template<class T> static T Value(unsigned i,bool target);
template<> double Value<double>(unsigned i,bool target){return DoubleValue(i,target);}
template<> float Value<float>(unsigned i,bool target){return FloatValue(i,target);}
template<> byte Value<byte>(unsigned i,bool target){return byte((i*37+(target?101:11))&255);}
template<> tsymatrix3d Value<tsymatrix3d>(unsigned i,bool target){
  static_assert(sizeof(tsymatrix3d)==6*sizeof(double),"Actual sigma layout");
  double x[6];for(unsigned c=0;c<6;c++)x[c]=DoubleValue(i*6+c,target);
  tsymatrix3d s;std::memcpy(&s,x,sizeof(s));return s;
}
struct Counts{unsigned cases=0,direct=0,wrapper=0,zero=0;std::uint64_t copied=0,source=0,tail=0;};
template<class T> static void Test(SortFixture& fixture,const char* type,unsigned n,unsigned prefix,bool full,
  const std::string& shape,const std::string& permutation,const std::vector<unsigned>& map,bool wrapper,std::ofstream& csv,Counts& count){
  std::vector<T> source(n+Guard),target(n+Guard),expected;
  for(unsigned i=0;i<source.size();i++){source[i]=Value<T>(i,false);target[i]=Value<T>(i,true);}
  expected=target;const unsigned pini=full?0:prefix;
  for(unsigned p=0;p<n;p++){const unsigned old=p<pini?p:map[p];Need(old<n,"declared map out of native range");expected[p]=source[old];}
  Buffer<T> src(n+Guard),dst(n+Guard);src.Up(source);dst.Up(target);
  if(wrapper)fixture.SortDataArrays(src.p,dst.p);
  else cudiv::SortDataParticles(n,pini,fixture.Map(),src.p,dst.p);
  Cu(cudaGetLastError(),"actual sort launch");Cu(cudaDeviceSynchronize(),"actual sort completion");
  const auto got=dst.Down(),unchanged=src.Down();const auto mapafter=fixture.DownloadMap(unsigned(map.size()));
  Need(!std::memcmp(got.data(),expected.data(),sizeof(T)*got.size()),"actual copy/prefix/tail bytes differ");
  Need(!std::memcmp(unchanged.data(),source.data(),sizeof(T)*source.size()),"source/guard bytes changed");
  Need(mapafter==map,"source permutation/tail guard changed");
  count.cases++;count.direct+=!wrapper;count.wrapper+=wrapper;count.zero+=!n;
  count.copied+=sizeof(T)*n;count.source+=sizeof(T)*source.size();count.tail+=sizeof(T)*Guard;
  csv<<(wrapper?"JCellDivGpu":"cudiv")<<','<<type<<','<<n<<','<<prefix<<','<<full<<','<<pini<<','<<shape<<','<<permutation<<','<<sizeof(T)*n<<','<<sizeof(T)*source.size()<<','<<sizeof(T)*Guard<<",true,true,true,true\n";
  csv.flush();Need(bool(csv),"component CSV write failed");
}
static void Run(const fs::path& out){
  Need(!fs::exists(out),"Retained component output protected");fs::create_directory(out);
  Cu(cudaSetDevice(0),"select device0");cudaDeviceProp props{};Cu(cudaGetDeviceProperties(&props,0),"actual device metadata");
  int runtime=0,driver=0;Cu(cudaRuntimeGetVersion(&runtime),"runtime version");Cu(cudaDriverGetVersion(&driver),"driver version");
  std::ofstream csv(out/"cases.csv");csv<<"api,type,np,wrapper_NpbFinal,DivideFull,effective_pini,shape,permutation,copied_bytes,source_guard_bytes,output_tail_bytes,output_exact,source_unchanged,map_unchanged,tail_unchanged\n";
  Counts count;
  {
    SortFixture fixture;
    for(unsigned n:{0u,1u,127u,128u,129u,257u})for(unsigned mode=0;mode<4;mode++)for(unsigned kind=0;kind<3;kind++){
      const bool full=mode==0;const unsigned prefix=(full?n:(mode==1?0:(mode==2?n/2:n))),pini=full?0:prefix;
      const std::string shape=full?"full_ignore_NpbFinal":(mode==1?"prefix0":(mode==2?"prefix_middle":"prefix_np"));
      const std::string permutation=kind==0?"identity":(kind==1?"prefix_and_tail_reverse":"prefix_and_tail_rotate");
      std::vector<unsigned> map(n+Guard,0xf0000000u);for(unsigned p=0;p<n;p++)map[p]=p;
      // Poison the in-range prefix permutation too: actual copying MUST ignore it.
      for(unsigned p=0;p<pini;p++)map[p]=kind==0?p:(kind==1?pini-1-p:(p+1)%pini);
      for(unsigned p=pini;p<n;p++)map[p]=kind==0?p:(kind==1?n-1-(p-pini):pini+(p-pini+1)%(n-pini));
      std::vector<unsigned> sorted(map.begin(),map.begin()+n);std::sort(sorted.begin(),sorted.end());
      for(unsigned p=0;p<n;p++)Need(sorted[p]==p,"not a native permutation");
      fixture.Configure(n,prefix,full,map);
      for(bool wrapper:{false,true}){
        Test<double>(fixture,"double",n,prefix,full,shape,permutation,map,wrapper,csv,count);
        Test<float>(fixture,"legacy_float",n,prefix,full,shape,permutation,map,wrapper,csv,count);
        Test<byte>(fixture,"legacy_byte",n,prefix,full,shape,permutation,map,wrapper,csv,count);
        Test<tsymatrix3d>(fixture,"legacy_double_sigma",n,prefix,full,shape,permutation,map,wrapper,csv,count);
      }
    }
  }
  Need(count.cases==576&&count.direct==288&&count.wrapper==288&&count.zero==96,"Declared component coverage differs");
  Cu(cudaDeviceSynchronize(),"before reset");Cu(cudaDeviceReset(),"component context cleanup");
  std::ofstream complete(out/"complete.json");complete<<"{\"passed\":true,\"cases\":"<<count.cases<<",\"direct_cases\":"<<count.direct
    <<",\"wrapper_cases\":"<<count.wrapper<<",\"zero_size_cases\":"<<count.zero<<",\"types\":4,\"sizes\":[0,1,127,128,129,257],\"prefix_modes\":4,\"permutations\":3,\"tail_guard_slots\":17,\"copied_bytes\":"<<count.copied
    <<",\"source_guard_bytes\":"<<count.source<<",\"output_tail_guard_bytes\":"<<count.tail<<",\"byte_exact\":true,\"source_unchanged\":true,\"map_unchanged\":true,\"tail_unchanged\":true,\"actual_class_wrapper\":true,\"actual_cell_division_tested\":false,\"replacement_kernel\":false,\"runtime_version\":"<<runtime<<",\"driver_version\":"<<driver<<",\"device_name\":\""<<props.name<<"\",\"physics_or_J_state_tested\":false,\"physical_acceptance\":false}\n";
  complete.flush();Need(bool(complete),"component completion write failed");
}
int main(int argc,char** argv){try{Need(argc==3&&std::string(argv[1])=="--run","Use --run FRESH_OUTPUT");Run(argv[2]);return 0;}
  catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"GPU sort component rejected; preserve evidence\n";return 2;}}
