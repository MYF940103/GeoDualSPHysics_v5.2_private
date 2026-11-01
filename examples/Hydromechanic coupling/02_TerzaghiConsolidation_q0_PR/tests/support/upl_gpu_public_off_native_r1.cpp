// Offline only: retained case02 mDBC151 control versus one new public-default-OFF run.
// No solver, CUDA, restart, metadata editing or output repair entry exists.
#include "JPartDataBi4.h"
#include "JAppInfo.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
namespace fs=std::filesystem;
// One link identity is required by the authoritative non-main object closure.
// It is not configured or used to invoke any solver path.
JAppInfo AppInfo("GpuPublicOffNative","r1","02-11-2026");
using Tp=JBinaryDataDef::TpData;
static constexpr unsigned Native=1040,Fixed=40,Frames=151,Steps=15000;
static constexpr double Dt=1e-5,Cadence=.001;
static void Need(bool b,const std::string& s){if(!b)throw std::runtime_error(s);}
template<class T>static bool Bits(const T& a,const T& b){return !std::memcmp(&a,&b,sizeof(T));}
struct Field{const char* name;Tp type;};
static const Field Fields[]={
  {"Idp",JBinaryDataDef::DatUint},{"Posd",JBinaryDataDef::DatDouble3},
  {"Vel",JBinaryDataDef::DatFloat3},{"Rhop",JBinaryDataDef::DatFloat},
  {"Sigma_kk",JBinaryDataDef::DatFloat3},{"Sigma_ij",JBinaryDataDef::DatFloat3},
  {"SigmaState_kk",JBinaryDataDef::DatDouble3},{"SigmaState_ij",JBinaryDataDef::DatDouble3},
  {"Kplastic",JBinaryDataDef::DatFloat},{"PorePress",JBinaryDataDef::DatFloat},
  {"PorePress0",JBinaryDataDef::DatFloat},{"ExcessPorePress",JBinaryDataDef::DatFloat},
  {"FSType",JBinaryDataDef::DatUint},{"FSNormal",JBinaryDataDef::DatFloat3},
  {"HydroMechLoadAce",JBinaryDataDef::DatFloat3}};
struct Array{Tp type;size_t stride;std::vector<unsigned char> bytes;};
struct State{double time,error;unsigned step;std::vector<unsigned> slot;std::map<std::string,Array> arrays;};
template<class T>static T At(const State& s,const char* name,unsigned id){T x;const auto& a=s.arrays.at(name);Need(sizeof(T)==a.stride,"Typed access size");std::memcpy(&x,a.bytes.data()+s.slot[id]*a.stride,sizeof(T));return x;}
static void Schema(JPartDataBi4& f){
  for(const char* n:{"PoroVolumeRatio","PoroPorosity","PoroThetaLastStage","PoroCurrentVolume","PoroMixtureDensity","PoroHydraulicConductivity","PosDiv"})Need(!f.ArrayExists(n),std::string("OFF unexpected array: ")+n);
  for(const char* n:{"HydroMechDynamicSeepage","DynamicSeepageSchema","HydroMechConductivityModel","HydroMechConductivityCk"})Need(!f.GetPart()->ExistsValue(n)&&!f.GetData()->ExistsValue(n),std::string("OFF unexpected metadata: ")+n);
  Need(f.ArraysCount()==15,"OFF array set must be exactly original15");
}
static void Finite(const Array& a){
  const bool d=a.type==JBinaryDataDef::DatDouble||a.type==JBinaryDataDef::DatDouble3;
  const bool f=a.type==JBinaryDataDef::DatFloat||a.type==JBinaryDataDef::DatFloat3;
  if(d)for(size_t b=0;b<a.bytes.size();b+=sizeof(double)){double x;std::memcpy(&x,a.bytes.data()+b,sizeof(x));Need(std::isfinite(x),"Nonfinite double field");}
  if(f)for(size_t b=0;b<a.bytes.size();b+=sizeof(float)){float x;std::memcpy(&x,a.bytes.data()+b,sizeof(x));Need(std::isfinite(x),"Nonfinite float field");}
}
static State Load(const fs::path& dir,unsigned part,const std::vector<double>& clocks){
  JPartDataBi4 f;f.LoadFilePart(dir.string(),part,0,1);Schema(f);
  Need(f.GetNpiece()==1&&f.Get_Npok()==Native&&!f.Get_Nout()&&f.Get_CaseNp()==Native&&f.Get_CaseNfixed()==Fixed&&f.Get_CaseNfluid()==Native-Fixed&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat(),"Native count/type/piece/exclusion changed");
  Need(f.Get_Data2d()&&!f.Get_Symmetry()&&!f.Get_NpDynamic()&&!f.Get_ReuseIds(),"Outside retained fixed-native2D scope");
  State s;s.time=f.Get_TimeStep();s.step=f.Get_Step();const auto* m=f.GetPart();
  Need(m->ExistsValue("dterror",JBinaryDataDef::DatDouble),"Typed signed dterror missing");s.error=m->GetvDouble("dterror");
  Need(std::isfinite(s.error)&&s.error<=1e-14,"Original signed dterror guard");
  Need(m->ExistsValue("SymplecticDtPre",JBinaryDataDef::DatDouble)&&m->GetvDouble("SymplecticDtPre")==Dt,"Actual locked DtFixed differs");
  Need(s.step<Steps&&std::isfinite(s.time)&&s.time==clocks[part?s.step+1:0],"Actual accumulated binary64 time/zero-based step differs");
  Need((part||s.step==0)&&std::abs(s.time-part*Cadence)<=1.01*Dt,"Original saved-cadence screen");
  if(part==Frames-1)Need(s.step==Steps-1&&s.time==clocks.back(),"Actual complete15000-step window missing");
  for(const auto& field:Fields){const auto* a=f.GetArray(field.name,field.type);Need((a->DataInPointer()?a->GetCount():a->GetFileDataCount())==Native,"Native field count differs");Array b{field.type,JBinaryDataDef::SizeOfType(field.type),{}};b.bytes.resize(Native*b.stride);Need(a->GetDataCopy(Native,b.bytes.data())==Native,"Incomplete typed read");Finite(b);s.arrays.emplace(field.name,std::move(b));}
  s.slot.assign(Native,~0u);const auto& ids=s.arrays.at("Idp");for(unsigned p=0;p<Native;p++){unsigned id;std::memcpy(&id,ids.bytes.data()+p*sizeof(unsigned),sizeof(id));Need(id<Native&&s.slot[id]==~0u,"Duplicate/out-of-range native ID");s.slot[id]=p;}
  for(unsigned id=0;id<Native;id++){Need(s.slot[id]!=~0u,"Missing native ID");Need(At<float>(s,"Rhop",id)>0&&At<float>(s,"Kplastic",id)==0,"Original positive-density/elastic guard");}
  return s;
}
static void Sequence(const fs::path& dir){Need(fs::is_directory(dir),"Native data missing");unsigned n=0;for(const auto& e:fs::directory_iterator(dir))if(e.is_regular_file()&&e.path().filename().string().rfind("Part_",0)==0&&e.path().extension()==".bi4")n++;Need(n==Frames,"Expected exactly151 one-piece PARTs");for(unsigned p=0;p<Frames;p++)Need(fs::is_regular_file(dir/JPartDataBi4::GetFileNamePart(p)),"Missing PART");}
int main(int argc,char** argv){try{
  Need(argc==5&&std::string(argv[1])=="--compare","Use --compare OLD_DATA NEW_DATA NEWREVIEWDIR");
  const fs::path old=fs::absolute(argv[2]),now=fs::absolute(argv[3]),out=fs::absolute(argv[4]);Need(!fs::equivalent(old,now)&&!fs::exists(out),"Control/self-comparison or retained review protected");Sequence(old);Sequence(now);
  std::vector<double> clocks(Steps+1);for(unsigned s=1;s<=Steps;s++)clocks[s]=clocks[s-1]+Dt;
  fs::create_directory(out);std::ofstream csv(out/"comparison.csv");csv<<std::setprecision(17)<<"part,time_s,saved_step,dterror_s,arrays,native_count,compared_bytes,different_bytes\n";
  unsigned long long total=0;double minerror=0,maxerror=-1e300;unsigned previous=0;
  for(unsigned part=0;part<Frames;part++){
    const auto a=Load(old,part,clocks),b=Load(now,part,clocks);Need(Bits(a.time,b.time)&&a.step==b.step&&Bits(a.error,b.error),"Actual clock/Step/signed dterror not bitwise equal");if(part)Need(a.step>previous,"Saved steps not strictly increasing");previous=a.step;
    unsigned long long bytes=0;for(const auto& field:Fields){const auto& x=a.arrays.at(field.name);const auto& y=b.arrays.at(field.name);for(unsigned id=0;id<Native;id++){Need(!std::memcmp(x.bytes.data()+a.slot[id]*x.stride,y.bytes.data()+b.slot[id]*y.stride,x.stride),std::string("Typed native bits differ: PART")+std::to_string(part)+" ID"+std::to_string(id)+" "+field.name);bytes+=x.stride;}}
    total+=bytes;minerror=std::min(minerror,a.error);maxerror=std::max(maxerror,a.error);csv<<part<<','<<a.time<<','<<a.step<<','<<a.error<<",15,1040,"<<bytes<<",0\n";
  }
  csv.flush();Need(bool(csv),"Comparison CSV failed");std::ofstream done(out/"complete.json");done<<std::setprecision(17)<<"{\"passed\":true,\"frames\":151,\"native_count\":1040,\"fixed_count\":40,\"soil_count\":1000,\"original_arrays\":15,\"compared_bytes\":"<<total<<",\"different_bytes\":0,\"all_native_original15_typed_bits_exact\":true,\"actual_time_step_signed_dterror_exact\":true,\"typed_signed_dterror_present_finite_safe\":true,\"min_signed_dterror_s\":"<<minerror<<",\"max_signed_dterror_s\":"<<maxerror<<",\"sequential_accumulated_binary64_clock_checked\":true,\"dynamic_arrays_and_metadata_absent_both\":true,\"native_set_elastic_finite_no_exclusions\":true,\"actual_end_s\":"<<clocks.back()<<",\"actual_steps\":15000,\"solver_or_restart_called\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Offline native comparison failed; preserve evidence\n";return 2;}}
