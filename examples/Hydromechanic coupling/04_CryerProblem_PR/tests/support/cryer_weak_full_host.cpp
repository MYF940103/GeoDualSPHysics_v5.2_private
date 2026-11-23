// Windows host for the existing native-mass weak CUDA DLL. Frame layout is
// little-endian doubles ordered by material ID: p, previous p, u, v, stress, J.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

extern "C" {
const char* errorText();
int currentStep(), init(int,double,double,double,double), start(), startWeak(), releaseWeak();
int setCsr(int,int,const int*,const int*,const double*);
int setGeometry(const double*,const double*,const double*,const double*,const double*,const unsigned char*);
int uploadWeak(int,const int*,const int*,const double*,const double*,const double*);
int restore(int,const double*,const double*,const double*,const double*,const double*,const double*);
int advanceWeak(int), readState(double*,double*,double*,double*,double*), readPrevious(double*);
}
namespace fs=std::filesystem;
constexpr int n=37173;
using Frame=std::vector<double>;
void require(bool condition,const std::string& error){if(!condition)throw std::runtime_error(error);}
void checked(int result){if(result)throw std::runtime_error(errorText());}
template<class T> std::vector<T> readArray(std::istream& input,size_t length){
  std::vector<T> value(length);
  input.read(reinterpret_cast<char*>(value.data()),length*sizeof(T));
  require(bool(input),"Short binary input");return value;
}
void setup(){
  std::ifstream input("inputs/operators.bin",std::ios::binary);
  const auto args=readArray<double>(input,4);
  checked(init(n,args[0],args[1],args[2],args[3]));
  for(int key:{0,1,2,4}){
    int nz=readArray<int>(input,1)[0];require(nz>0 && nz<20000000,"Invalid operator size");
    auto row=readArray<int>(input,n+1),col=readArray<int>(input,nz);
    auto value=readArray<double>(input,(key<2?3:1)*size_t(nz));
    checked(setCsr(key,nz,row.data(),col.data(),value.data()));
    if(key==2)checked(setCsr(3,nz,row.data(),col.data(),value.data()));
  }
  auto x=readArray<double>(input,3*n),mass=readArray<double>(input,n),traction=readArray<double>(input,3*n);
  auto inverse=readArray<double>(input,n),normal=readArray<double>(input,3*n);
  auto surface=readArray<unsigned char>(input,n);
  checked(setGeometry(x.data(),mass.data(),traction.data(),inverse.data(),normal.data(),surface.data()));
  checked(start());
  int nz=readArray<int>(input,1)[0];require(nz>0 && nz<20000000,"Invalid weak operator size");
  auto row=readArray<int>(input,n+1),col=readArray<int>(input,nz);
  auto value=readArray<double>(input,nz),volume=readArray<double>(input,n),diagonal=readArray<double>(input,n);
  checked(uploadWeak(nz,row.data(),col.data(),value.data(),volume.data(),diagonal.data()));
  require(input.peek()==std::char_traits<char>::eof(),"Unexpected operator data");
  checked(startWeak());
}
std::string frameName(int step){return "state_"+std::to_string(step)+".bin";}
Frame anchor(int step){
  const auto path=fs::path("inputs")/frameName(step);
  require(fs::file_size(path)==15ull*n*sizeof(double),"Invalid checkpoint size");
  std::ifstream stream(path,std::ios::binary);return readArray<double>(stream,15*n);
}
Frame state(){
  Frame f(15*n);auto a=f.data();
  checked(readState(a,a+2*n,a+5*n,a+8*n,a+14*n));checked(readPrevious(a+n));
  require(std::all_of(f.begin(),f.end(),[](double v){return std::isfinite(v);}),"Nonfinite material state");
  return f;
}
void match(const Frame& expected,const Frame& actual,int step){
  require(std::memcmp(actual.data(),expected.data(),actual.size()*sizeof(double))==0,
          "Checkpoint bytes differ at step "+std::to_string(step));
}
void restoreChecked(int step){
  auto expected=anchor(step);const double* a=expected.data();
  checked(restore(step,a,a+n,a+2*n,a+5*n,a+8*n,a+14*n));
  require(currentStep()==step,"Unexpected restore clock");match(expected,state(),step);
}
void advanceTo(int step){
  const int startStep=currentStep();require(startStep>=0 && startStep<=step,"Nonmonotonic clock");
  if(step>startStep)checked(advanceWeak(step-startStep));
  require(currentStep()==step,"Unexpected GPU clock");
}
void saveFrame(const fs::path& path,const Frame& f){
  auto temporary=path;temporary+=".writing";require(!fs::exists(path)&&!fs::exists(temporary),"Frame already exists");
  std::ofstream out(temporary,std::ios::binary);out.write(reinterpret_cast<const char*>(f.data()),f.size()*sizeof(double));
  out.close();require(bool(out),"Failed writing frame");fs::rename(temporary,path);
}
int main(int argc,char** argv){
  try{
    require(argc==3,"Usage: weak_full.exe full|smoke NEW_OUTPUT");
    const std::string mode=argv[1];const fs::path output=argv[2];
    require(mode=="full"||mode=="smoke","Unknown run mode");
    require(fs::create_directory(output),"Output directory already exists");
    auto startTime=std::chrono::steady_clock::now();setup();
    std::ofstream log(output/"actual_clock.csv");log<<"step,time_s,elapsed_s\n"<<std::setprecision(17);
    auto record=[&](int step,const Frame& f){
      saveFrame(output/frameName(step),f);
      double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-startTime).count();
      log<<step<<','<<std::ldexp(double(step),-19)<<','<<elapsed<<std::endl;
      require(bool(log),"Clock write failed");
      std::cout<<"step "<<step<<", elapsed "<<elapsed<<" s"<<std::endl;
    };
    if(mode=="smoke"){
      restoreChecked(4096);advanceTo(4097);auto opening=state();match(anchor(4097),opening,4097);record(4097,opening);
      restoreChecked(36864);advanceTo(36867);auto after=state();match(anchor(36867),after,36867);record(36867,after);
    }else{
      std::ifstream schedule("inputs/steps.txt");std::set<int> steps;int step;
      while(schedule>>step)require(steps.insert(step).second,"Duplicate scheduled step");
      require(schedule.eof()&&steps.size()==265&&*steps.begin()==0&&*steps.rbegin()==481685,"Bad full schedule");
      for(int special:{4097,4160,25984,36864})steps.insert(special);
      for(int next:steps){
        advanceTo(next);auto f=state();
        if(next==4096||next==4097||next==4160||next==36864)match(anchor(next),f,next);
        record(next,f);
        if(next==36864)restoreChecked(36864);
      }
    }
    checked(releaseWeak());
    std::ofstream done(output/"complete.txt");done<<mode<<std::endl;
    require(bool(done),"Unable to seal run");return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}
}
