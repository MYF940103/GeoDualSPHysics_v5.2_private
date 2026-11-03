// Offline only: fixed CPU1 short458 old/new matched FreeSlip u-pw OFF comparison.
// Mechanical adaptation of upl_gpu_public_off_native_r1.cpp; no solver or CUDA.
#include "JPartDataBi4.h"
#include "JAppInfo.h"
#include <algorithm>
#include <cfloat>
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
// Link identity only; no solver configuration or invocation entry exists.
JAppInfo AppInfo("SprAvCpuOffNative","r1","03-11-2026");
using Tp=JBinaryDataDef::TpData;
static constexpr unsigned Native=1040,Fixed=40,Frames=458,Steps=13120;
static constexpr double Dt=0.0000019073486328125; // Exact2^-19, not rounded decimal cadence.
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
static std::vector<unsigned> SaveSteps(){
  std::vector<unsigned> saved;
  for(unsigned n=0;n<=Steps;n+=64)saved.push_back(n);
  for(unsigned n=5120;n<=5376;n++)saved.push_back(n);
  std::sort(saved.begin(),saved.end());saved.erase(std::unique(saved.begin(),saved.end()),saved.end());
  Need(saved.size()==Frames&&saved.front()==0&&saved.back()==Steps,"Declared458 integer saved-step set differs");
  return saved;
}
static State Load(const fs::path& dir,unsigned part,const std::vector<double>& clocks,const std::vector<unsigned>& saved){
  JPartDataBi4 f;f.LoadFilePart(dir.string(),part,0,1);Schema(f);
  Need(f.GetNpiece()==1&&f.Get_Npok()==Native&&!f.Get_Nout()&&f.Get_CaseNp()==Native&&f.Get_CaseNfixed()==Fixed&&f.Get_CaseNfluid()==Native-Fixed&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat(),"Native count/type/piece/exclusion changed");
  Need(f.Get_Data2d()&&!f.Get_Symmetry()&&!f.Get_NpDynamic()&&!f.Get_ReuseIds(),"Outside retained fixed-native2D scope");
  State s;s.time=f.Get_TimeStep();s.step=f.Get_Step();const auto* m=f.GetPart();
  Need(m->ExistsValue("dterror",JBinaryDataDef::DatDouble),"Typed signed dterror missing");s.error=m->GetvDouble("dterror");
  Need(std::isfinite(s.error)&&s.error<=1e-14,"Original signed dterror guard");
  if(part)Need(s.error!=-DBL_MAX,"Noninitial signed diagnostic interval is empty");
  Need(m->ExistsValue("SymplecticDtPre",JBinaryDataDef::DatDouble)&&m->GetvDouble("SymplecticDtPre")==Dt,"Actual locked DtFixed differs");
  const unsigned completed=saved[part],step=completed?completed-1:0;
  Need(s.step==step&&std::isfinite(s.time)&&Bits(s.time,clocks[completed]),"Actual declared integer clock/zero-based saved step differs");
  if(part==Frames-1)Need(s.step==Steps-1&&Bits(s.time,clocks.back()),"Actual complete13120-step window missing");
  for(const auto& field:Fields){const auto* a=f.GetArray(field.name,field.type);Need((a->DataInPointer()?a->GetCount():a->GetFileDataCount())==Native,"Native field count differs");Array b{field.type,JBinaryDataDef::SizeOfType(field.type),{}};b.bytes.resize(Native*b.stride);Need(a->GetDataCopy(Native,b.bytes.data())==Native,"Incomplete typed read");Finite(b);s.arrays.emplace(field.name,std::move(b));}
  s.slot.assign(Native,~0u);const auto& ids=s.arrays.at("Idp");for(unsigned p=0;p<Native;p++){unsigned id;std::memcpy(&id,ids.bytes.data()+p*sizeof(unsigned),sizeof(id));Need(id<Native&&s.slot[id]==~0u,"Duplicate/out-of-range native ID");s.slot[id]=p;}
  for(unsigned id=0;id<Native;id++){Need(s.slot[id]!=~0u,"Missing native ID");Need(At<float>(s,"Rhop",id)>0&&At<float>(s,"Kplastic",id)==0,"Original positive-density/elastic guard");}
  return s;
}
static void Sequence(const fs::path& dir){Need(fs::is_directory(dir),"Native data missing");unsigned n=0;for(const auto& e:fs::directory_iterator(dir))if(e.is_regular_file()&&e.path().filename().string().rfind("Part_",0)==0&&e.path().extension()==".bi4")n++;Need(n==Frames,"Expected exactly458 one-piece PARTs");for(unsigned p=0;p<Frames;p++)Need(fs::is_regular_file(dir/JPartDataBi4::GetFileNamePart(p)),"Missing PART");}
int main(int argc,char** argv){try{
  Need(argc==5&&std::string(argv[1])=="--compare","Use --compare OLD_OFF_DATA NEW_OFF_DATA FRESH_REVIEW_DIRECTORY");
  const fs::path old=fs::absolute(argv[2]),now=fs::absolute(argv[3]),out=fs::absolute(argv[4]);Need(!fs::equivalent(old,now)&&!fs::exists(out),"Control/self-comparison or retained review protected");Sequence(old);Sequence(now);
  const auto saved=SaveSteps();std::vector<double> clocks(Steps+1);for(unsigned s=1;s<=Steps;s++)clocks[s]=clocks[s-1]+Dt;
  Need(Bits(clocks.back(),double(Steps)*Dt),"Exact dyadic accumulated clock declaration differs");
  Need(fs::create_directory(out),"Fresh review directory creation failed");std::ofstream csv(out/"comparison.csv");Need(bool(csv),"Comparison CSV open failed");
  csv<<std::setprecision(17)<<"part,time_s,completed_step,saved_step,dt_s,signed_dterror_s,dterror_interval_empty,dterror_used_in_noninitial_summary,arrays,native_count,compared_bytes,different_bytes\n";
  unsigned long long total=0;double minerror=DBL_MAX,maxerror=-DBL_MAX;unsigned previous=0,intervals=0,initialEmpty=0;
  for(unsigned part=0;part<Frames;part++){
    const auto a=Load(old,part,clocks,saved),b=Load(now,part,clocks,saved);Need(Bits(a.time,b.time)&&a.step==b.step&&Bits(a.error,b.error),"Actual clock/Step/signed dterror not bitwise equal");if(part)Need(a.step>previous,"Saved steps not strictly increasing");previous=a.step;
    unsigned long long bytes=0;for(const auto& field:Fields){const auto& x=a.arrays.at(field.name);const auto& y=b.arrays.at(field.name);for(unsigned id=0;id<Native;id++){Need(!std::memcmp(x.bytes.data()+a.slot[id]*x.stride,y.bytes.data()+b.slot[id]*y.stride,x.stride),std::string("Typed native bits differ: PART")+std::to_string(part)+" ID"+std::to_string(id)+" "+field.name);bytes+=x.stride;}}
    Need(bytes==166400,"Original15 typed payload byte count differs");total+=bytes;
    const bool empty=a.error==-DBL_MAX;if(part){intervals++;minerror=std::min(minerror,a.error);maxerror=std::max(maxerror,a.error);}else initialEmpty+=unsigned(empty);
    csv<<part<<','<<a.time<<','<<saved[part]<<','<<a.step<<','<<Dt<<','<<a.error<<','<<empty<<','<<(part>0)<<",15,1040,"<<bytes<<",0\n";
  }
  Need(total==76211200ULL&&intervals==457,"Incomplete458-frame typed payload or noninitial diagnostic coverage");
  csv.flush();Need(bool(csv),"Comparison CSV failed");std::ofstream done(out/"completion.json");Need(bool(done),"Completion open failed");
  done<<std::setprecision(17)<<"{\"passed\":true,\"stage\":\"upl_spr_av_off_native_r1\",\"backend_label\":\"CPU_legacy_upw_OFF\",\"window\":\"short458\",\"frames\":458,\"native_count\":1040,\"fixed_count\":40,\"soil_count\":1000,\"original_arrays\":15,\"compared_bytes\":"<<total<<",\"different_bytes\":0,\"all_native_original15_typed_bits_exact\":true,\"actual_time_step_signed_dterror_exact\":true,\"typed_signed_dterror_present_finite_safe\":true,\"noninitial_signed_dterror_intervals\":"<<intervals<<",\"initial_empty_dterror_intervals\":"<<initialEmpty<<",\"initial_dterror_excluded_from_noninitial_summary\":true,\"min_noninitial_signed_dterror_s\":"<<minerror<<",\"max_noninitial_signed_dterror_s\":"<<maxerror<<",\"sequential_accumulated_binary64_clock_checked\":true,\"declared458_integer_schedule_exact\":true,\"dynamic_arrays_and_global_PART_metadata_absent_both\":true,\"absent_dynamic_fields_fabricated\":false,\"native_set_elastic_finite_no_exclusions\":true,\"dt_s\":"<<Dt<<",\"actual_end_s\":"<<clocks.back()<<",\"actual_steps\":13120,\"owned_solver_exits_or_program_backend_verified_by_reader\":false,\"runtime_parameters_or_input_SHA_verified_by_reader\":false,\"raw_input_SHA_verified_by_reader\":false,\"solver_or_restart_called\":false,\"half_comparison_performed\":false,\"physical_acceptance\":false}\n";
  done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"CPU short OFF native comparison failed; preserve evidence\n";return 2;}}
