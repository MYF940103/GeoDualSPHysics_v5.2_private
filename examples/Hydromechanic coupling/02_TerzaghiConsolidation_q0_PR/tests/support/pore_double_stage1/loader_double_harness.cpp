// Stage 1: exercise the real BI4 writer, loader, sorting and boundary removal.
// This fixture does not reimplement the loader and does not claim coupled accuracy.
#include "JPartsLoad4.h"
#include "JPartDataBi4.h"
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs=std::filesystem;
enum Format { LegacyFloat,CompensatedFloat,DoubleState,DoubleWithResidual,NoPressure };
enum Damage { Valid,Missing,WrongType,OtherPrecision,ShortCount,LongCount,NaN,Infinity };
struct Check { std::string name,detail; bool pass; };
class LoaderFixture:public JPartsLoad4 {
public:
  LoaderFixture():JPartsLoad4(false){}
  void SortForTest(){ SortParticles(); }
};

static void Require(bool ok,const std::string& message){ if(!ok)throw std::runtime_error(message); }
static bool Same(double a,double b){ return std::memcmp(&a,&b,sizeof(double))==0; }
static float High(unsigned id){ return 20000.f+2.f*float(id); }
static float Low(unsigned id){ return (id%2?-1.f:1.f)*float(id+1)*.00003125f; }
static double Pressure(unsigned id,Format format){
  return double(High(id))+(format==CompensatedFloat?double(Low(id)):
    format==DoubleState? .000123456789*double(id+1):0.);
}
static double Reference(unsigned id,Format format){
  return double(id)+(format==DoubleState?.125000000007:0.);
}
static std::string Quote(const std::string& value){
  std::string result="\"";
  for(char c:value){
    if(c=='"' || c=='\\'){result+='\\';result+=c;}
    else if(c=='\n')result+="\\n";
    else if(c=='\r')result+="\\r";
    else if(c=='\t')result+="\\t";
    else if(static_cast<unsigned char>(c)>=32)result+=c;
  }
  return result+'"';
}
static void Test(std::vector<Check>& checks,const std::string& name,const std::function<void()>& action){
  try{action();checks.push_back({name,"",true});}
  catch(const std::exception& e){checks.push_back({name,e.what(),false});}
  catch(...){checks.push_back({name,"Unknown exception",false});}
}

static void WritePart(const fs::path& dir,const std::vector<unsigned>& ids,unsigned total,unsigned nbound,
  unsigned piece,unsigned pieces,Format format,const std::string& field="",Damage damage=Valid,bool cold=false)
{
  fs::create_directories(dir);
  const unsigned n=unsigned(ids.size());
  // The production writer requires non-null pointers even for a zero-count piece.
  std::vector<unsigned> fileids(ids);fileids.resize(n+1);
  std::vector<tdouble3> pos(n+1);
  std::vector<tfloat3> vel(n+1,TFloat3(0)),sigma(n+1,TFloat3(0)),shear(n+1,TFloat3(0));
  std::vector<float> rhop(n+1,2100.f),plastic(n+1,0.f);
  for(unsigned p=0;p<n;p++){
    pos[p]=TDouble3(double(ids[p]),0,0);
    sigma[p]=TFloat3(float(ids[p]+1),float(ids[p]+2),float(ids[p]+3));
    shear[p]=TFloat3(float(ids[p]+4),float(ids[p]+5),float(ids[p]+6));
    plastic[p]=float(ids[p])*.125f;
  }
  JPartDataBi4 writer;
  writer.ConfigBasic(piece,pieces,"stage1","PoreDoubleLoaderAcceptance","Fixture",true,0,dir.string());
  writer.ConfigParticles(total,nbound,0,0,total-nbound,TDouble3(0),TDouble3(10));
  writer.ConfigCtes(.1,.13,1e6,2100,7,1,1);
  writer.ConfigSimMap(TDouble3(-1),TDouble3(11));
  writer.AddPartInfo(cold?0:1,.000125,n,0,123,0,TDouble3(-1),TDouble3(11),total);
  writer.GetPart()->SetvDouble("SymplecticDtPre",62.5e-9);
  writer.AddPartData(n,fileids.data(),pos.data(),vel.data(),rhop.data());
  writer.AddPartData("Sigma_kk",n,sigma.data());
  writer.AddPartData("Sigma_ij",n,shear.data());
  writer.AddPartData("Kplastic",n,plastic.data());
  const auto addfield=[&](const std::string& name,bool isdouble){
    const bool corrupt=(name==field);
    if(corrupt && damage==Missing)return;
    if(corrupt && damage==OtherPrecision)isdouble=!isdouble;
    unsigned count=n;
    if(corrupt && damage==ShortCount){Require(n>0,"Cannot shorten empty fixture");count=n-1;}
    if(corrupt && damage==LongCount)count=n+1;
    std::vector<float> floats(n+1,0.f);
    std::vector<double> doubles(n+1,0.);
    std::vector<int> wrong(n+1,0);
    for(unsigned p=0;p<n;p++){
      const unsigned id=ids[p];
      const double value=(name=="PorePress"?Pressure(id,format==DoubleState?DoubleState:LegacyFloat):
        name=="PorePress0"?Reference(id,format):double(Low(id)));
      floats[p]=float(value);doubles[p]=value;
    }
    if(corrupt && n && (damage==NaN || damage==Infinity)){
      floats[0]=(damage==NaN?std::numeric_limits<float>::quiet_NaN():std::numeric_limits<float>::infinity());
      doubles[0]=(damage==NaN?std::numeric_limits<double>::quiet_NaN():std::numeric_limits<double>::infinity());
    }
    // Intentionally bypass AddPartData's size check for malformed fixtures only.
    const JBinaryDataDef::TpData type=(corrupt && damage==WrongType?JBinaryDataDef::DatInt:
      isdouble?JBinaryDataDef::DatDouble:JBinaryDataDef::DatFloat);
    const void* data=(type==JBinaryDataDef::DatInt?static_cast<const void*>(wrong.data()):
      isdouble?static_cast<const void*>(doubles.data()):static_cast<const void*>(floats.data()));
    writer.GetPart()->CreateArray(name,type,count,data,false);
  };
  if(format!=NoPressure){
    addfield("PorePress",format==DoubleState || format==DoubleWithResidual);
    addfield("PorePress0",format==DoubleState || format==DoubleWithResidual);
  }
  if(format==CompensatedFloat || format==DoubleWithResidual || field=="orphan_residual")
    addfield("PorePressRes",false);
  if(cold)writer.SaveFileCase("Fixture");
  else writer.SaveFilePart();
}
static void Load(LoaderFixture& loader,const fs::path& dir){loader.LoadParticles(dir.string(),"Fixture",1,dir.string());}
static void Reject(const fs::path& dir,const std::string& expected){
  LoaderFixture loader;
  try{Load(loader,dir);}
  catch(const std::exception& e){
    Require(std::string(e.what()).find(expected)!=std::string::npos,"Unexpected rejection: "+std::string(e.what()));
    return;
  }
  throw std::runtime_error("Malformed PART was accepted");
}
static void CheckById(LoaderFixture& loader,Format format){
  Require(loader.GetPorePressureDataLoaded(),"Pore-pressure state not loaded");
  for(unsigned p=0;p<loader.GetCount();p++){
    const unsigned id=loader.GetIdp()[p];
    Require(Same(loader.GetPorePress()[p],Pressure(id,format)),"Pressure bits or ID mapping differ");
    Require(Same(loader.GetPorePress0()[p],Reference(id,format)),"Reference bits or ID mapping differ");
    Require(loader.GetPos()[p].x==double(id),"Position and ID mapping differ");
  }
}

int main(int argc,char** argv){
  try{
    Require(argc==3,"Usage: loader_double_harness NEW_FIXTURE_DIRECTORY NEW_RESULT_JSON");
    const fs::path root=argv[1],json=argv[2];
    Require(!fs::exists(root),"Refusing existing fixture directory");
    Require(!fs::exists(json),"Refusing existing result JSON");
    fs::create_directories(root);
    std::vector<Check> checks;
    for(Format format:{LegacyFloat,CompensatedFloat,DoubleState}){
      const std::string label=(format==LegacyFloat?"float_promote":format==CompensatedFloat?"float_reconstruct":"double_exact");
      Test(checks,label+"_load_sort_remove_reset",[&](){
        const fs::path dir=root/label;
        WritePart(dir,{0,3,1,4,2},5,1,0,1,format);
        LoaderFixture loader;Load(loader,dir);
        Require(loader.GetCount()==5,"Wrong loaded count");CheckById(loader,format);
        Require(loader.GetIdp()[1]==3,"Load must preserve original particle order");
        Require(loader.GetSymplecticDtPre()==62.5e-9,"Restart timestep changed");
        Require(loader.GetSoilDataLoaded(),"Soil arrays lost");
        for(unsigned p=0;p<loader.GetCount();p++){
          const unsigned id=loader.GetIdp()[p];
          Require(loader.GetSigma()[p].xx==float(id+1) && loader.GetSigma()[p].xz==float(id+6),"Soil state changed on load");
          Require(loader.GetKplastic()[p]==float(id)*.125f,"Plastic state changed on load");
        }
        loader.SortForTest();CheckById(loader,format);
        for(unsigned p=0;p<5;p++)Require(loader.GetIdp()[p]==p,"Sort did not reorder IDs");
        loader.RemoveBoundary();Require(loader.GetCount()==4 && loader.GetIdp()[0]==1,"Boundary removal changed count/ID");
        CheckById(loader,format);
        loader.Reset();Require(loader.GetCount()==0 && !loader.GetPorePress() && !loader.GetPorePress0(),"Reset leaked pore arrays");
      });
      Test(checks,label+"_unequal_pieces",[&](){
        const fs::path dir=root/(label+"_pieces");
        WritePart(dir,{0,3},5,1,0,2,format);WritePart(dir,{1,4,2},5,1,1,2,format);
        LoaderFixture loader;Load(loader,dir);Require(loader.GetCount()==5,"Piece count differs");CheckById(loader,format);
      });
      Test(checks,label+"_empty_first_piece",[&](){
        const fs::path dir=root/(label+"_empty");
        WritePart(dir,{},3,0,0,2,format);WritePart(dir,{2,0,1},3,0,1,2,format);
        LoaderFixture loader;Load(loader,dir);Require(loader.GetCount()==3,"Empty piece count differs");CheckById(loader,format);
      });
      for(const std::string field:{"PorePress","PorePress0"}){
        for(Damage damage:{Missing,WrongType,OtherPrecision,ShortCount,LongCount,NaN,Infinity}){
          const std::string name=label+"_"+field+"_bad"+std::to_string(int(damage));
          Test(checks,name,[&](){
            const fs::path dir=root/name;WritePart(dir,{0,1,2},3,1,0,1,format,field,damage);
            const std::string expected=(damage==Missing?"must both be present":
              damage==ShortCount || damage==LongCount?"array size":
              damage==NaN || damage==Infinity?"non-finite":
              field=="PorePress" && damage==WrongType?"must use float or double":
              format==CompensatedFloat && field=="PorePress" && damage==OtherPrecision?"only valid with legacy float":"types must agree");
            Reject(dir,expected);
          });
        }
      }
    }
    for(Damage damage:{WrongType,OtherPrecision,ShortCount,LongCount,NaN,Infinity}){
      const std::string name="residual_bad"+std::to_string(int(damage));
      Test(checks,name,[&](){
        const fs::path dir=root/name;WritePart(dir,{0,1,2},3,1,0,1,CompensatedFloat,"PorePressRes",damage);
        Reject(dir,damage==WrongType || damage==OtherPrecision?"Type of array":
          damage==ShortCount || damage==LongCount?"array size":"non-finite");
      });
    }
    Test(checks,"double_plus_residual_rejected",[&](){
      const fs::path dir=root/"ambiguous";WritePart(dir,{0,1},2,1,0,1,DoubleWithResidual);
      Reject(dir,"only valid with legacy float");
    });
    Test(checks,"orphan_residual_rejected",[&](){
      const fs::path dir=root/"orphan_residual";WritePart(dir,{0,1},2,1,0,1,NoPressure,"orphan_residual");
      Reject(dir,"PorePressRes requires");
    });
    for(Format first:{NoPressure,LegacyFloat,CompensatedFloat,DoubleState}){
      for(Format second:{NoPressure,LegacyFloat,CompensatedFloat,DoubleState})if(first!=second){
        const std::string name="piece_schema_"+std::to_string(int(first))+"_"+std::to_string(int(second));
        Test(checks,name,[&](){
          const fs::path dir=root/name;
          WritePart(dir,{0,1},4,1,0,2,first);WritePart(dir,{2,3},4,1,1,2,second);
          Reject(dir,first==NoPressure || second==NoPressure?"availability is inconsistent":
            first==CompensatedFloat || second==CompensatedFloat?"PorePressRes availability":"types must agree");
        });
      }
    }
    Test(checks,"restart_without_pressure_remains_unloaded",[&](){
      const fs::path dir=root/"no_pressure";WritePart(dir,{0,1},2,1,0,1,NoPressure);
      LoaderFixture loader;Load(loader,dir);Require(!loader.GetPorePressureDataLoaded(),"No-pressure restart changed meaning");
    });
    Test(checks,"coldcase_does_not_load_restart_arrays",[&](){
      const fs::path dir=root/"coldcase";WritePart(dir,{0,1},2,1,0,1,DoubleState,"PorePress",NaN,true);
      LoaderFixture loader;loader.LoadParticles(dir.string(),"Fixture",0,"");
      Require(!loader.GetPorePressureDataLoaded() && !loader.GetSoilDataLoaded(),"Cold-case semantics changed");
      Require(loader.GetCount()==2 && loader.GetPartBeginTimeStep()==0.,"Cold-case count/time changed");
    });
    unsigned failures=0;
    for(const Check& check:checks){
      if(!check.pass)failures++;
      std::cout<<(check.pass?"PASS ":"FAIL ")<<check.name<<' '<<check.detail<<'\n';
    }
    std::ofstream out(json);Require(bool(out),"Cannot create result JSON");
    out<<"{\n\"schema_version\":1,\n\"complete\":true,\n\"passed\":"<<(failures?"false":"true")
      <<",\n\"check_count\":"<<checks.size()<<",\n\"failure_count\":"<<failures
      <<",\n\"scope\":\"Real JPartsLoad4 with real BI4 files. Exact pressure/reference state bits, schema validation, preserved loading order, pore sorting and boundary removal; not coupled solver accuracy or exact time-integration restart.\",\n"
      <<"\"soil_scope\":\"Soil fields checked immediately after load. Existing inactive legacy sort/remove helpers' soil behavior is intentionally unchanged.\",\n\"checks\":[\n";
    for(size_t i=0;i<checks.size();i++)out<<"{\"name\":"<<Quote(checks[i].name)<<",\"pass\":"<<(checks[i].pass?"true":"false")
      <<",\"detail\":"<<Quote(checks[i].detail)<<'}'<<(i+1<checks.size()?",\n":"\n");
    out<<"]\n}\n";out.flush();Require(bool(out),"Cannot write result JSON");
    std::cout<<"COMPLETE checks="<<checks.size()<<" failures="<<failures<<'\n';
    return failures?1:0;
  }
  catch(const std::exception& e){std::cerr<<"HARNESS ERROR: "<<e.what()<<'\n';return 2;}
}
