// Independent real-BI4 / real-JPartsLoad4 acceptance for the plain float rollback.
// This does not exercise coupled dynamics or change existing fixture sources.
#include "JPartsLoad4.h"
#include "JPartDataBi4.h"
#include <cstring>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs=std::filesystem;
enum Format { PlainFloat,ResidualFloat,DoubleState,NoPressure };
enum Damage { Valid,Missing,WrongType,DoubleField,ShortCount,LongCount,NaN,Infinity };
struct Check { std::string name,detail; bool passed; };
class Fixture:public JPartsLoad4 {
public:
  Fixture():JPartsLoad4(false){}
  void SortForTest(){ SortParticles(); }
};
static void Require(bool ok,const std::string& text){if(!ok)throw std::runtime_error(text);}
static float Pressure(unsigned id){return 20000.f+2.f*float(id);}
static float Reference(unsigned id){return float(id)*.125f;}
static bool Same(float a,float b){return std::memcmp(&a,&b,sizeof(float))==0;}
static void Test(std::vector<Check>& tests,const std::string& name,const std::function<void()>& action){
  try{action();tests.push_back({name,"",true});}
  catch(const std::exception& e){tests.push_back({name,e.what(),false});}
}
static std::string Quote(const std::string& text){
  std::string result="\"";
  for(char c:text){
    if(c=='"'||c=='\\'){result+='\\';result+=c;}
    else if(c=='\n')result+="\\n";
    else if(c=='\r')result+="\\r";
    else if(c=='\t')result+="\\t";
    else if(static_cast<unsigned char>(c)>=32)result+=c;
  }
  return result+'"';
}
static void WritePart(const fs::path& dir,const std::vector<unsigned>& ids,unsigned total,unsigned nbound,
  unsigned piece,unsigned pieces,Format format,const std::string& field="",Damage damage=Valid,bool cold=false)
{
  fs::create_directories(dir);
  const unsigned n=unsigned(ids.size());
  std::vector<unsigned> fileids(ids);fileids.resize(n+1);
  std::vector<tdouble3> pos(n+1);
  std::vector<tfloat3> vel(n+1,TFloat3(0)),sigma(n+1,TFloat3(0)),shear(n+1,TFloat3(0));
  std::vector<float> rhop(n+1,2100.f),plastic(n+1,0.f);
  for(unsigned p=0;p<n;p++){
    const unsigned id=ids[p];pos[p]=TDouble3(double(id),0,0);
    sigma[p]=TFloat3(float(id+1),float(id+2),float(id+3));
    shear[p]=TFloat3(float(id+4),float(id+5),float(id+6));plastic[p]=float(id)*.125f;
  }
  JPartDataBi4 writer;
  writer.ConfigBasic(piece,pieces,"float-restore","PlainFloatLoaderAcceptance","Fixture",true,0,dir.string());
  writer.ConfigParticles(total,nbound,0,0,total-nbound,TDouble3(0),TDouble3(10));
  writer.ConfigCtes(.1,.13,1e6,2100,7,1,1);
  writer.ConfigSimMap(TDouble3(-1),TDouble3(11));
  writer.AddPartInfo(cold?0:1,.000125,n,0,123,0,TDouble3(-1),TDouble3(11),total);
  writer.GetPart()->SetvDouble("SymplecticDtPre",62.5e-9);
  writer.AddPartData(n,fileids.data(),pos.data(),vel.data(),rhop.data());
  writer.AddPartData("Sigma_kk",n,sigma.data());writer.AddPartData("Sigma_ij",n,shear.data());
  writer.AddPartData("Kplastic",n,plastic.data());
  const auto add=[&](const std::string& name){
    const bool bad=(field==name);
    if(bad&&damage==Missing)return;
    const unsigned count=bad&&damage==ShortCount?n-1:bad&&damage==LongCount?n+1:n;
    std::vector<float> f(n+1,0.f);std::vector<double> d(n+1,0.);std::vector<int> wrong(n+1,0);
    for(unsigned p=0;p<n;p++){
      f[p]=(name=="PorePress"?Pressure(ids[p]):name=="PorePress0"?Reference(ids[p]):.0000125f);
      d[p]=double(f[p])+(name=="PorePress"?.000000001:0.);
    }
    if(bad&&n&&(damage==NaN||damage==Infinity)){
      f[0]=damage==NaN?std::numeric_limits<float>::quiet_NaN():std::numeric_limits<float>::infinity();
      d[0]=double(f[0]);
    }
    const auto type=bad&&damage==WrongType?JBinaryDataDef::DatInt:
      format==DoubleState||(bad&&damage==DoubleField)?JBinaryDataDef::DatDouble:JBinaryDataDef::DatFloat;
    const void* data=type==JBinaryDataDef::DatDouble?static_cast<const void*>(d.data()):
      type==JBinaryDataDef::DatInt?static_cast<const void*>(wrong.data()):static_cast<const void*>(f.data());
    // Bypass the normal writer count guard only for intentionally damaged fixtures.
    writer.GetPart()->CreateArray(name,type,count,data,false);
  };
  if(format!=NoPressure){add("PorePress");add("PorePress0");}
  if(format==ResidualFloat||field=="orphan_residual")add("PorePressRes");
  if(cold)writer.SaveFileCase("Fixture");else writer.SaveFilePart();
}
static void Load(Fixture& loader,const fs::path& dir){loader.LoadParticles(dir.string(),"Fixture",1,dir.string());}
static void Reject(const fs::path& dir,const std::string& expected=""){
  Fixture loader;
  try{Load(loader,dir);}
  catch(const std::exception& e){Require(std::string(e.what()).find(expected)!=std::string::npos,"Wrong rejection: "+std::string(e.what()));return;}
  throw std::runtime_error("Unsupported or malformed PART was accepted");
}
static void CheckPressure(Fixture& loader){
  Require(loader.GetPorePressureDataLoaded(),"Expected float pore arrays");
  for(unsigned p=0;p<loader.GetCount();p++){
    const unsigned id=loader.GetIdp()[p];
    Require(Same(loader.GetPorePress()[p],Pressure(id)),"Float pressure bits or ID mapping changed");
    Require(Same(loader.GetPorePress0()[p],Reference(id)),"Float reference bits or ID mapping changed");
    Require(loader.GetPos()[p].x==double(id),"Position/ID mismatch");
  }
}
int main(int argc,char** argv){
  try{
    Require(argc==3,"Usage: loader_float_harness NEW_FIXTURE_DIRECTORY NEW_RESULT_JSON");
    const fs::path root=argv[1],json=argv[2];
    Require(!fs::exists(root)&&!fs::exists(json),"Refusing existing fixtures/results");
    fs::create_directories(root);std::vector<Check> tests;
    Test(tests,"float_load_sort_remove_reset",[&](){
      const fs::path dir=root/"float";WritePart(dir,{0,3,1,4,2},5,1,0,1,PlainFloat);
      Fixture loader;Load(loader,dir);Require(loader.GetCount()==5,"Count changed");CheckPressure(loader);
      Require(loader.GetIdp()[1]==3,"Normal loader must preserve input order");
      Require(loader.GetSymplecticDtPre()==62.5e-9,"Restart timestep changed");
      Require(loader.GetSoilDataLoaded(),"Soil arrays lost on load");
      for(unsigned p=0;p<5;p++){
        const unsigned id=loader.GetIdp()[p];
        Require(loader.GetSigma()[p].xx==float(id+1)&&loader.GetSigma()[p].xz==float(id+6),"Soil load changed");
        Require(loader.GetKplastic()[p]==float(id)*.125f,"Plastic state load changed");
      }
      loader.SortForTest();CheckPressure(loader);
      for(unsigned p=0;p<5;p++)Require(loader.GetIdp()[p]==p,"ID sorting changed");
      loader.RemoveBoundary();Require(loader.GetCount()==4&&loader.GetIdp()[0]==1,"Boundary removal failed");CheckPressure(loader);
      loader.Reset();Require(loader.GetCount()==0&&!loader.GetPorePress()&&!loader.GetPorePress0(),"Reset failed");
    });
    Test(tests,"unequal_piece_counts",[&](){
      const fs::path dir=root/"unequal";WritePart(dir,{0,3},5,1,0,2,PlainFloat);WritePart(dir,{1,4,2},5,1,1,2,PlainFloat);
      Fixture loader;Load(loader,dir);Require(loader.GetCount()==5,"Piece counts did not add");CheckPressure(loader);
    });
    Test(tests,"empty_first_piece",[&](){
      const fs::path dir=root/"empty";WritePart(dir,{},3,0,0,2,PlainFloat);WritePart(dir,{2,0,1},3,0,1,2,PlainFloat);
      Fixture loader;Load(loader,dir);Require(loader.GetCount()==3,"Empty piece count wrong");CheckPressure(loader);
    });
    for(Format format:{ResidualFloat,DoubleState})Test(tests,"unsupported_format_"+std::to_string(int(format)),[&](){
      const fs::path dir=root/("format_"+std::to_string(int(format)));WritePart(dir,{0,1},2,1,0,1,format);
      Reject(dir,format==ResidualFloat?"PorePressRes restart":"must use float arrays");
    });
    Test(tests,"orphan_residual_rejected",[&](){
      const fs::path dir=root/"orphan";WritePart(dir,{0,1},2,1,0,1,NoPressure,"orphan_residual");Reject(dir,"PorePressRes restart");
    });
    for(const std::string field:{"PorePress","PorePress0"})for(Damage damage:{Missing,WrongType,DoubleField,ShortCount,LongCount,NaN,Infinity}){
      const std::string name=field+"_bad_"+std::to_string(int(damage));
      Test(tests,name,[&](){
        const fs::path dir=root/name;WritePart(dir,{0,1},2,1,0,1,PlainFloat,field,damage);
        Reject(dir,damage==Missing?"must both be present":damage==WrongType||damage==DoubleField?"must use float arrays":
          damage==ShortCount||damage==LongCount?"array size":"non-finite");
      });
    }
    for(Format first:{PlainFloat,ResidualFloat,DoubleState,NoPressure})for(Format second:{PlainFloat,ResidualFloat,DoubleState,NoPressure})if(first!=second){
      const std::string name="piece_schema_"+std::to_string(int(first))+"_"+std::to_string(int(second));
      Test(tests,name,[&](){const fs::path dir=root/name;
        WritePart(dir,{0,1},4,1,0,2,first);WritePart(dir,{2,3},4,1,1,2,second);Reject(dir);
      });
    }
    Test(tests,"restart_without_pressure_remains_unloaded",[&](){
      const fs::path dir=root/"no_pressure";WritePart(dir,{0,1},2,1,0,1,NoPressure);
      Fixture loader;Load(loader,dir);Require(!loader.GetPorePressureDataLoaded(),"No-pressure semantics changed");
    });
    Test(tests,"coldcase_still_ignores_restart_only_fields",[&](){
      const fs::path dir=root/"cold";WritePart(dir,{0,1},2,1,0,1,DoubleState,"PorePress",NaN,true);
      Fixture loader;loader.LoadParticles(dir.string(),"Fixture",0,"");
      Require(!loader.GetPorePressureDataLoaded()&&!loader.GetSoilDataLoaded(),"Cold-case semantics changed");
      Require(loader.GetCount()==2&&loader.GetPartBeginTimeStep()==0.,"Cold-case count/time changed");
    });
    unsigned failed=0;for(const auto& check:tests){if(!check.passed)failed++;std::cout<<(check.passed?"PASS ":"FAIL ")<<check.name<<' '<<check.detail<<'\n';}
    std::ofstream output(json);Require(bool(output),"Cannot create JSON");
    output<<"{\n\"passed\":"<<(failed?"false":"true")<<",\n\"check_count\":"<<tests.size()<<",\n\"failure_count\":"<<failed
      <<",\n\"scope\":\"Actual BI4 writer and JPartsLoad4. Plain float exact bits; residual/double/malformed restart rejected. No coupled accuracy claim. Soil fields checked immediately after load only.\",\n\"checks\":[\n";
    for(size_t i=0;i<tests.size();i++)output<<"{\"name\":"<<Quote(tests[i].name)<<",\"passed\":"<<(tests[i].passed?"true":"false")
      <<",\"detail\":"<<Quote(tests[i].detail)<<'}'<<(i+1<tests.size()?",\n":"\n");
    output<<"]\n}\n";output.flush();Require(bool(output),"Cannot write JSON");
    std::cout<<"COMPLETE checks="<<tests.size()<<" failures="<<failed<<'\n';return failed?1:0;
  }
  catch(const std::exception& e){std::cerr<<"HARNESS ERROR: "<<e.what()<<'\n';return 2;}
}
