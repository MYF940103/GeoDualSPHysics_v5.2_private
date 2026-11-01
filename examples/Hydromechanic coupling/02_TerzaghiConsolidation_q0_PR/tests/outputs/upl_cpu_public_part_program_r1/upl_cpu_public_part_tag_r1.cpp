// Native metadata-copy diagnostic only. No solver class, force call or integration.
#include "JPartDataBi4.h"
#include "JBinaryData.h"
#include "JPartsLoad4.h"
#include "JAppInfo.h"
#include <algorithm>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
JAppInfo AppInfo("PublicPartFalseMetadata","r1","01-11-2026");
namespace fs=std::filesystem;
using Type=JBinaryDataDef::TpData;
static void Need(bool yes,const std::string& why){if(!yes)throw std::runtime_error(why);}
struct Blob{
  Type type;unsigned count;bool hide;std::vector<byte> data;
  bool operator==(const Blob& other)const{return type==other.type&&count==other.count&&hide==other.hide&&data==other.data;}
};
struct Tree{
  std::vector<std::string> nodes;std::map<std::string,Blob> values,arrays;
  bool operator==(const Tree& other)const{return nodes==other.nodes&&values==other.values&&arrays==other.arrays;}
};
template<class T> static Blob Scalar(Type type,T value){
  Blob b{type,1,false,{}};const byte* p=reinterpret_cast<const byte*>(&value);b.data.assign(p,p+sizeof(T));return b;
}
static Blob Value(JBinaryData* node,const std::string& name,Type type){
  #define GET(T,V) case JBinaryDataDef::T:return Scalar(type,node->V(name))
  switch(type){
    case JBinaryDataDef::DatText:{const auto s=node->GetvText(name);Blob b{type,1,false,{}};b.data.assign(s.begin(),s.end());return b;}
    GET(DatBool,GetvBool);GET(DatChar,GetvChar);GET(DatUchar,GetvUchar);
    GET(DatShort,GetvShort);GET(DatUshort,GetvUshort);GET(DatInt,GetvInt);GET(DatUint,GetvUint);
    GET(DatLlong,GetvLlong);GET(DatUllong,GetvUllong);GET(DatFloat,GetvFloat);GET(DatDouble,GetvDouble);
    GET(DatInt3,GetvInt3);GET(DatUint3,GetvUint3);GET(DatFloat3,GetvFloat3);GET(DatDouble3,GetvDouble3);
    default:throw std::runtime_error("Unknown native scalar type");
  }
  #undef GET
}
static void Capture(JBinaryData* node,const std::string& prefix,Tree& tree){
  const std::string path=prefix+"/"+node->GetName();
  tree.nodes.push_back(path+"|hide="+std::to_string(node->GetHide())+"|hidevalues="+std::to_string(node->GetHideValues()));
  for(unsigned i=0;i<node->GetValuesCount();i++){
    const auto name=node->NameOfValue(i);Need(tree.values.emplace(path+"/"+name,Value(node,name,node->TypeOfValue(i))).second,"Duplicate native scalar path");
  }
  for(unsigned i=0;i<node->GetArraysCount();i++){
    const auto* a=node->GetArray(i);const Type type=a->GetType();const unsigned count=a->DataInPointer()?a->GetCount():a->GetFileDataCount();
    Need(type!=JBinaryDataDef::DatText&&type!=JBinaryDataDef::DatNull,"Non-numeric diagnostic array");
    Blob b{type,count,a->GetHide(),{}};b.data.resize(size_t(count)*JBinaryDataDef::SizeOfType(type));
    Need(a->GetDataCopy(count,b.data.data())==count,"Incomplete native array snapshot");
    Need(tree.arrays.emplace(path+"/"+a->GetName(),std::move(b)).second,"Duplicate native array path");
  }
  for(unsigned i=0;i<node->GetItemsCount();i++)Capture(node->GetItem(i),path,tree);
}
static Tree Capture(JPartDataBi4& file){Tree result;Capture(file.GetData(),"",result);return result;}
static void InMemory(JBinaryData* node){
  for(unsigned i=0;i<node->GetArraysCount();i++){auto* a=node->GetArray(i);if(a->DataInFile()&&!a->DataInPointer())a->ReadFileData(true);}
  for(unsigned i=0;i<node->GetItemsCount();i++)InMemory(node->GetItem(i));
}
template<class T> static std::vector<T> Array(JPartDataBi4& f,const char* name,Type type){
  const auto* a=f.GetArray(name,type);const unsigned count=a->DataInPointer()?a->GetCount():a->GetFileDataCount();Need(count==512,"Wrong positive control native count");
  std::vector<T> out(count);Need(a->GetDataCopy(count,out.data())==count,"Incomplete positive control array");return out;
}
static void LegacyLoaderPositive(JPartDataBi4& source,const std::string& datadir,const std::string& casedir,const std::string& casename){
  JPartsLoad4 loaded(false);loaded.LoadParticles(casedir,casename,1,datadir);
  Need(loaded.GetCount()==512&&loaded.GetSoilDataLoaded()&&loaded.GetPorePressureDataLoaded(),"Legacy OFF native loader positive control failed");
  const auto ids=Array<unsigned>(source,"Idp",JBinaryDataDef::DatUint);
  const auto x=Array<tdouble3>(source,"Posd",JBinaryDataDef::DatDouble3),kk=Array<tdouble3>(source,"SigmaState_kk",JBinaryDataDef::DatDouble3),ij=Array<tdouble3>(source,"SigmaState_ij",JBinaryDataDef::DatDouble3);
  const auto v=Array<tfloat3>(source,"Vel",JBinaryDataDef::DatFloat3);
  const auto rho=Array<float>(source,"Rhop",JBinaryDataDef::DatFloat),p=Array<float>(source,"PorePress",JBinaryDataDef::DatFloat),p0=Array<float>(source,"PorePress0",JBinaryDataDef::DatFloat),kp=Array<float>(source,"Kplastic",JBinaryDataDef::DatFloat);
  std::vector<unsigned> slot(512,~0u);for(unsigned i=0;i<512;i++){Need(ids[i]<512&&slot[ids[i]]==~0u,"Duplicate positive control ID");slot[ids[i]]=i;}
  for(unsigned row=0;row<512;row++){
    const unsigned id=loaded.GetIdp()[row];Need(id<512&&slot[id]!=~0u,"Positive loader ID changed");const unsigned q=slot[id];const auto vr=loaded.GetVelRhop()[row];const auto s=loaded.GetSigma()[row];
    Need(!std::memcmp(loaded.GetPos()+row,x.data()+q,sizeof(tdouble3))&&vr.x==v[q].x&&vr.y==v[q].y&&vr.z==v[q].z&&vr.w==rho[q],"Positive loader position/velocity/density changed");
    Need(s.xx==kk[q].x&&s.yy==kk[q].y&&s.zz==kk[q].z&&s.xy==ij[q].x&&s.yz==ij[q].y&&s.xz==ij[q].z&&loaded.GetKplastic()[row]==kp[q]&&loaded.GetPorePress()[row]==p[q]&&loaded.GetPorePress0()[row]==p0[q],"Positive loader stress/pore data changed");
  }
}
int main(int argc,char** argv){try{
  Need(argc==7&&std::string(argv[1])=="--write-false","Use --write-false OFF_DATA_DIR CASE_DIR CASE_NAME NEW_SCRATCH_DIR NEW_CHECK_JSON");
  const fs::path sourceDir=argv[2],scratch=argv[5],receipt=argv[6],sourceFile=sourceDir/JPartDataBi4::GetFileNamePart(1);
  Need(fs::is_regular_file(sourceFile)&&!fs::exists(scratch)&&!fs::exists(receipt),"Retained scratch/receipt protected or source missing");
  JPartDataBi4 source;source.LoadFilePart(sourceDir.string(),1,0,1);
  Need(source.GetNpiece()==1&&source.Get_Npok()==512&&!source.Get_Nout()&&source.Get_CaseNfluid()==512&&!source.Get_CaseNfixed(),"Only retained real OFF512 one-piece PART1 accepted");
  const char* dynamic[]={"PoroVolumeRatio","PoroPorosity","PoroThetaLastStage","PoroCurrentVolume","PoroMixtureDensity","PoroHydraulicConductivity"};
  for(const char* name:dynamic)Need(!source.ArrayExists(name),"False-tag source is not genuine OFF data");
  const char* metadata[]={"HydroMechDynamicSeepage","DynamicSeepageSchema","HydroMechConductivityModel","HydroMechConductivityCk"};
  for(const char* name:metadata)Need(!source.GetPart()->ExistsValue(name),"False-tag source already has dynamic metadata");
  const auto before=Capture(source);Need(before.arrays.size()==15,"Expected original15 real OFF arrays");LegacyLoaderPositive(source,sourceDir.string(),argv[3],argv[4]);
  fs::create_directory(scratch);const fs::path target=scratch/JPartDataBi4::GetFileNamePart(1);fs::copy_file(sourceFile,target);
  JPartDataBi4 edited;edited.LoadFilePart(scratch.string(),1,0,1);Need(Capture(edited)==before,"Fresh scratch copy differs from real OFF source");
  InMemory(edited.GetData());edited.GetData()->CloseFileStructure();
  Need(Capture(edited)==before,"Materializing native arrays changed values");
  edited.GetPart()->SetvBool("HydroMechDynamicSeepage",false);
  edited.GetData()->SaveFile(target.string(),false,true);
  JPartDataBi4 checked;checked.LoadFilePart(scratch.string(),1,0,1);auto after=Capture(checked);
  const std::string added="/"+checked.GetData()->GetName()+"/"+checked.GetPart()->GetName()+"/HydroMechDynamicSeepage";
  Need(checked.GetPart()->ExistsValue("HydroMechDynamicSeepage",JBinaryDataDef::DatBool)&&!checked.GetPart()->GetvBool("HydroMechDynamicSeepage"),"Scratch new scalar is not bool false");
  Need(after.values.size()==before.values.size()+1&&after.values.erase(added)==1&&after==before,"Scratch changed more than the sole new false scalar");
  for(const char* name:dynamic)Need(!checked.ArrayExists(name),"Scratch writer fabricated a J array");
  JPartDataBi4 untouched;untouched.LoadFilePart(sourceDir.string(),1,0,1);Need(Capture(untouched)==before,"Retained original source changed");
  std::ofstream out(receipt);out<<"{\"passed\":true,\"real_OFF_loader_positive_control_passed\":true,\"loaded_positive_native_ids\":512,\"loaded_fields_unchanged\":true,\"arrays_preserved\":"<<before.arrays.size()<<",\"all_array_bits_preserved\":true,\"all_existing_scalar_typed_bits_preserved\":true,\"item_topology_and_hide_flags_preserved\":true,\"added_scalar\":\"HydroMechDynamicSeepage\",\"added_scalar_type\":\"DatBool\",\"added_scalar_value\":false,\"new_scalar_count\":1,\"dynamic_arrays_added\":0,\"original_source_unchanged\":true,\"PART\":1,\"native_count\":512,\"one_piece\":true,\"native_metadata_API_used\":true,\"solver_or_integration_called\":false,\"coupled_restart_acceptance\":false,\"physical_acceptance\":false}\n";out.flush();Need(bool(out),"False-tag writer receipt failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Native false-tag copy failed; retain all evidence\n";return 2;}}
