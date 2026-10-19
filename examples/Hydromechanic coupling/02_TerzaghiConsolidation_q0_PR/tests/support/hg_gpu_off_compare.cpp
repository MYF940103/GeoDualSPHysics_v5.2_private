// Read-only G1/G2 old-mode regression: all 21 native-ID-matched PART arrays.
// This compares emitted fields, not unrecorded solver work arrays or physics accuracy.
#include "JPartDataBi4.h"
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs=std::filesystem;
static void Require(bool okay,const std::string& why){if(!okay)throw std::runtime_error(why);}
static std::string Json(const std::string& text){
  std::ostringstream out;out<<'"';
  for(unsigned char c:text){
    if(c=='"'||c=='\\')out<<'\\'<<char(c);
    else if(c<32)out<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<unsigned(c)<<std::dec;
    else out<<char(c);
  }
  out<<'"';return out.str();
}
template<class T> static bool Same(const T& a,const T& b){return std::memcmp(&a,&b,sizeof(T))==0;}
struct Array{JBinaryDataDef::TpData type;size_t stride;std::vector<unsigned char> bytes;};
struct Part{
  double time;unsigned count,soil,step;
  std::vector<unsigned> slot;
  std::map<std::string,Array> arrays;
};
static void Finite(const Array& a,const std::string& name){
  const bool single=(a.type==JBinaryDataDef::DatFloat || a.type==JBinaryDataDef::DatFloat3);
  const bool twice=(a.type==JBinaryDataDef::DatDouble || a.type==JBinaryDataDef::DatDouble3);
  if(single)for(size_t p=0;p<a.bytes.size();p+=sizeof(float)){
    float v;std::memcpy(&v,a.bytes.data()+p,sizeof(v));Require(std::isfinite(v),"Nonfinite float array: "+name);
  }
  if(twice)for(size_t p=0;p<a.bytes.size();p+=sizeof(double)){
    double v;std::memcpy(&v,a.bytes.data()+p,sizeof(v));Require(std::isfinite(v),"Nonfinite double array: "+name);
  }
}
static Part Load(const fs::path& dir,unsigned index,unsigned expected,double dt){
  JPartDataBi4 file;file.LoadFilePart(dir.string(),index,0,1);
  Require(file.GetNpiece()==1,"Only actual single-GPU one-piece PART files are supported");
  Part p;p.time=file.Get_TimeStep();p.count=file.Get_Npok();p.step=file.Get_Step();
  p.soil=unsigned(file.Get_CaseNfluid());
  Require(!file.Get_NpDynamic()&&!file.Get_ReuseIds(),"Dynamic/reused native IDs are outside this regression");
  Require(p.count==expected && file.Get_CaseNp()==expected && file.Get_Nout()==0,"Native count changed or particles excluded");
  Require(p.soil==1000 && file.Get_CaseNfixed()==40 && !file.Get_CaseNmoving() && !file.Get_CaseNfloat(),"Not the retained 1040-particle case-02 seed");
  // JSphGpuSingle saves the completed step before Nstep++, so PART1 stores
  // Step=0 although its physical time is dt. PART0 is the initial state.
  const unsigned expectedstep=(index? index-1: 0);
  if(p.step!=expectedstep || !std::isfinite(p.time) || std::abs(p.time-double(index)*dt)>1e-12){
    std::ostringstream why;why<<std::setprecision(17)<<"PART metadata mismatch: index="<<index
      <<" observed_step="<<p.step<<" expected_step="<<expectedstep
      <<" observed_time="<<p.time<<" expected_time="<<double(index)*dt<<" time_limit=1e-12";
    Require(false,why.str());
  }
  for(unsigned a=0;a<file.ArraysCount();a++){
    const std::string name=file.ArrayName(a);const auto* source=file.GetArray(name);
    const auto type=source->GetType();
    Require(type!=JBinaryDataDef::DatNull && type!=JBinaryDataDef::DatText,"Non-numeric PART array: "+name);
    const unsigned count=source->DataInPointer()?source->GetCount():source->GetFileDataCount();
    Require(count==p.count,"Array count differs from native count: "+name);
    Array value;value.type=type;value.stride=JBinaryDataDef::SizeOfType(type);
    Require(value.stride>0,"Unknown array element size: "+name);
    value.bytes.resize(size_t(count)*value.stride);
    Require(source->GetDataCopy(count,value.bytes.data())==count,"Incomplete array read: "+name);
    Finite(value,name);Require(p.arrays.emplace(name,std::move(value)).second,"Duplicate array name: "+name);
  }
  for(const char* name:{"Idp","Vel","Rhop","Sigma_kk","Sigma_ij","SigmaState_kk","SigmaState_ij","Kplastic","PorePress","PorePress0","HydroMechLoadAce"})
    Require(p.arrays.count(name)!=0,std::string("Missing required emitted field: ")+name);
  Require(p.arrays.count("Pos")+p.arrays.count("Posd")==1,"Require exactly one position array");
  const auto& ids=p.arrays.at("Idp");Require(ids.type==JBinaryDataDef::DatUint,"Idp must be native uint32");
  Require(p.arrays.at("SigmaState_kk").type==JBinaryDataDef::DatDouble3 && p.arrays.at("SigmaState_ij").type==JBinaryDataDef::DatDouble3,"Persistent stress fields must be double3");
  p.slot.assign(expected,~0u);
  for(unsigned k=0;k<p.count;k++){
    unsigned id;std::memcpy(&id,ids.bytes.data()+size_t(k)*ids.stride,sizeof(id));
    Require(id<expected && p.slot[id]==~0u,"Invalid/duplicate native particle ID");p.slot[id]=k;
  }
  for(unsigned slot:p.slot)Require(slot!=~0u,"Missing native ID");
  return p;
}
static void Sequence(const fs::path& dir){
  Require(fs::is_directory(dir),"Data directory not found");unsigned count=0;
  for(const auto& entry:fs::directory_iterator(dir)){
    const std::string name=entry.path().filename().string();
    if(entry.is_regular_file() && name.rfind("Part_",0)==0 && entry.path().extension()==".bi4")count++;
  }
  Require(count==21,"Expected exactly 21 PART files, with no extra part/piece");
  for(unsigned i=0;i<=20;i++)Require(fs::is_regular_file(dir/JPartDataBi4::GetFileNamePart(i)),"Missing PART "+std::to_string(i));
}
int main(int argc,char** argv){
  if(argc!=6){std::cerr<<"Use hg_gpu_off_compare BASE_DATA NEW_DATA NEW_CHECK_JSON EXPECTED_NATIVE_COUNT DT\n";return 2;}
  const fs::path output=fs::absolute(argv[3]);
  if(fs::exists(output)){std::cerr<<"Refusing existing check JSON\n";return 2;}
  bool passed=false;std::string reason;unsigned compared=0;unsigned long long mismatching=0,bytes=0;
  std::ostringstream parts,first;bool firstdifference=true;
  try{
    const fs::path base=fs::absolute(argv[1]),candidate=fs::absolute(argv[2]);
    Require(!fs::equivalent(base,candidate),"Cannot compare a directory with itself");
    size_t used=0;const unsigned count=std::stoul(argv[4],&used);Require(used==std::strlen(argv[4])&&count==1040,"Expected native count must be 1040");
    const double dt=std::stod(argv[5],&used);Require(used==std::strlen(argv[5])&&std::isfinite(dt)&&dt==1e-5,"Expected fixed dt is 1e-5 s");
    Sequence(base);Sequence(candidate);
    for(unsigned part=0;part<=20;part++){
      const Part a=Load(base,part,count,dt),b=Load(candidate,part,count,dt);
      Require(Same(a.time,b.time),"Actual PART times differ by bits");
      Require(a.arrays.size()==b.arrays.size(),"Emitted array set changed");
      unsigned long long differentpart=0;
      for(const auto& field:a.arrays){
        const auto found=b.arrays.find(field.first);Require(found!=b.arrays.end(),"Missing candidate field: "+field.first);
        const Array& x=field.second;const Array& y=found->second;
        Require(x.type==y.type && x.stride==y.stride,"Field type changed: "+field.first);
        for(unsigned id=0;id<count;id++){
          const auto* left=x.bytes.data()+size_t(a.slot[id])*x.stride;
          const auto* right=y.bytes.data()+size_t(b.slot[id])*y.stride;
          for(size_t k=0;k<x.stride;k++)if(left[k]!=right[k]){
            differentpart++;
            if(firstdifference){first<<"{\"part\":"<<part<<",\"native_id\":"<<id<<",\"field\":"<<Json(field.first)<<",\"element_byte\":"<<k<<'}';firstdifference=false;}
          }
        }
        bytes+=size_t(count)*x.stride;
      }
      if(compared)parts<<',';
      parts<<std::setprecision(17)<<"{\"part\":"<<part<<",\"step\":"<<a.step<<",\"expected_saved_step\":"<<(part? part-1: 0)<<",\"actual_time_s\":"<<a.time
        <<",\"native_count\":"<<a.count<<",\"soil_count\":"<<a.soil<<",\"arrays\":[";
      bool initial=true;for(const auto& field:a.arrays){if(!initial)parts<<',';initial=false;parts<<Json(field.first);}
      parts<<"],\"differing_bytes\":"<<differentpart<<'}';compared++;mismatching+=differentpart;
    }
    Require(mismatching==0,"Emitted particle fields differ; inspect first_difference");passed=true;
  }catch(const std::exception& error){reason=error.what();}
  catch(...){reason="Production BI4 reader raised an unknown exception";}
  std::ofstream record(output);record<<"{\"passed\":"<<(passed?"true":"false")<<",\"reason\":"<<Json(reason)
    <<",\"scope\":\"Read-only native-ID byte comparison of every emitted particle array, PART0 through PART20\""
    <<",\"base_data\":"<<Json(fs::absolute(argv[1]).string())<<",\"candidate_data\":"<<Json(fs::absolute(argv[2]).string())
    <<",\"parts_compared\":"<<compared<<",\"compared_bytes\":"<<bytes<<",\"differing_bytes\":"<<mismatching
    <<",\"required_differing_bytes\":0,\"first_difference\":"<<(firstdifference?"null":first.str())<<",\"parts\":["<<parts.str()<<']'
    <<",\"saved_step_convention\":\"PART0 Step=0; PARTk Step=k-1 because SaveData precedes Nstep++\""
    <<",\"limitations\":[\"Only emitted native fields are compared; unrecorded work arrays are not inspected\",\"Runtime metadata is not compared\",\"Twenty steps are not physical or full-cycle acceptance\"],\"physical_acceptance\":false}\n";
  record.flush();if(!record){std::cerr<<"Cannot save comparison JSON\n";return 2;}
  std::cout<<(passed?"PASS":"FAIL")<<" native PART comparison: "<<compared<<" parts, "<<mismatching<<" differing bytes; "<<reason<<'\n';
  return passed?0:1;
}
