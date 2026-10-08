// Read-only native BI4 exporter for the controlled Vel0 state comparison.
// Production JPartDataBi4 performs decoding; no VTK conversions or solver edits.
#include "JPartDataBi4.h"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <map>
#include <regex>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs=std::filesystem;
static void Require(bool ok,const std::string& message){if(!ok)throw std::runtime_error(message);}
static unsigned Count(const JBinaryDataArray* a){return a->DataInPointer()?a->GetCount():a->GetFileDataCount();}
static JBinaryDataArray* Array(JPartDataBi4& part,const char* name,unsigned n){
  JBinaryDataArray* a=part.GetArray(name);
  Require(Count(a)==n,std::string(name)+" count differs from Npok");return a;
}
static std::string Type(JPartDataBi4& part,const char* name){
  return part.ArrayExists(name)?JBinaryDataDef::TypeToStr(part.GetArray(name)->GetType()):"absent";
}
static std::vector<double> Scalar(JPartDataBi4& part,const char* name,unsigned n,bool optional=false){
  if(optional && !part.ArrayExists(name))return std::vector<double>(n,0.);
  JBinaryDataArray* a=Array(part,name,n);std::vector<double> values(n);
  if(a->GetType()==JBinaryDataDef::DatDouble){if(n)a->GetDataCopy(n,values.data());}
  else{
    Require(a->GetType()==JBinaryDataDef::DatFloat,std::string(name)+" must be float or double");
    std::vector<float> temporary(n);if(n)a->GetDataCopy(n,temporary.data());
    for(unsigned i=0;i<n;i++)values[i]=double(temporary[i]);
  }
  for(double v:values)Require(std::isfinite(v),std::string(name)+" contains non-finite values");
  return values;
}
static std::vector<tdouble3> Triple(JPartDataBi4& part,const char* name,unsigned n){
  JBinaryDataArray* a=Array(part,name,n);std::vector<tdouble3> values(n);
  if(a->GetType()==JBinaryDataDef::DatDouble3){if(n)a->GetDataCopy(n,values.data());}
  else{
    Require(a->GetType()==JBinaryDataDef::DatFloat3,std::string(name)+" must be float3 or double3");
    std::vector<tfloat3> temporary(n);if(n)a->GetDataCopy(n,temporary.data());
    for(unsigned i=0;i<n;i++)values[i]=ToTDouble3(temporary[i]);
  }
  for(const auto& v:values)Require(std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z),std::string(name)+" contains non-finite values");
  return values;
}
static std::vector<ullong> Integers(JPartDataBi4& part,const char* name,unsigned n){
  JBinaryDataArray* a=Array(part,name,n);std::vector<ullong> values(n);
  if(a->GetType()==JBinaryDataDef::DatUllong){if(n)a->GetDataCopy(n,values.data());}
  else if(a->GetType()==JBinaryDataDef::DatUint){
    std::vector<unsigned> temporary(n);if(n)a->GetDataCopy(n,temporary.data());
    for(unsigned i=0;i<n;i++)values[i]=temporary[i];
  }
  else if(a->GetType()==JBinaryDataDef::DatUchar){
    std::vector<unsigned char> temporary(n);if(n)a->GetDataCopy(n,temporary.data());
    for(unsigned i=0;i<n;i++)values[i]=temporary[i];
  }
  else Require(false,std::string(name)+" must be uint/ullong/uchar");
  return values;
}
struct Row{
  ullong id,fstype;tdouble3 pos,vel,sigma,shear;
  double pressure,reference,stored,residual,rhop;
};
struct FrameFiles{bool single=false,multi=false;std::map<unsigned,fs::path> pieces;};
static std::map<unsigned,FrameFiles> Discover(const fs::path& dir){
  Require(fs::is_directory(dir),"Input data directory not found: "+dir.string());
  const std::regex pattern("^Part(?:_p([0-9]+))?_([0-9]+)\\.bi4$");
  std::map<unsigned,FrameFiles> result;
  for(const auto& entry:fs::directory_iterator(dir))if(entry.is_regular_file()){
    std::smatch match;const std::string name=entry.path().filename().string();
    if(!std::regex_match(name,match,pattern))continue;
    const unsigned part=unsigned(std::stoul(match[2].str()));
    const bool split=match[1].matched;const unsigned piece=split?unsigned(std::stoul(match[1].str())):0;
    auto& frame=result[part];frame.single|=!split;frame.multi|=split;
    Require(!(frame.single && frame.multi),"Ambiguous single/multi-piece PART filenames");
    Require(frame.pieces.emplace(piece,entry.path()).second,"Duplicate PART piece index");
  }
  Require(!result.empty(),"No Part_####.bi4 / Part_p##_####.bi4 files found");
  return result;
}
static void Export(const fs::path& dir,const fs::path& output){
  Require(!fs::exists(output),"Refusing existing export directory: "+output.string());
  const auto frames=Discover(dir);fs::create_directories(output);
  std::ofstream state(output/"state.csv"),metadata(output/"frames.csv");
  Require(bool(state)&&bool(metadata),"Cannot create CSV output");
  state.imbue(std::locale::classic());metadata.imbue(std::locale::classic());
  state<<std::setprecision(17);metadata<<std::setprecision(17);
  state<<"part,id,time_s,x_m,y_m,z_m,pressure_pa,reference_pa,stored_pressure_pa,residual_pa,velx_m_s,vely_m_s,velz_m_s,rhop_kg_m3,sigma_xx_pa,sigma_yy_pa,sigma_zz_pa,sigma_xy_pa,sigma_yz_pa,sigma_xz_pa,fstype\n";
  metadata<<"part,time_s,particle_count,piece_count,id_type,pos_type,pressure_type,reference_type,residual_type,velocity_type,rhop_type,sigma_kk_type,sigma_ij_type,fstype_type,case_nfixed,case_nmoving,case_nfloat,case_nfluid\n";
  double previous=-std::numeric_limits<double>::infinity();ullong total=0;
  unsigned framecount=0;
  for(const auto& entry:frames){
    const unsigned index=entry.first,npiece=unsigned(entry.second.pieces.size());
    std::vector<Row> rows;std::string signature;
    double time=0;bool hasstress=false,hasfs=false;
    ullong nfixed=0,nmoving=0,nfloat=0,nfluid=0;
    for(unsigned piece=0;piece<npiece;piece++){
      Require(entry.second.pieces.count(piece)==1,"Non-contiguous PART piece indices");
      JPartDataBi4 part;part.LoadFilePart(dir.string(),index,piece,npiece);
      const unsigned n=part.Get_Npok();
      Require(part.ArrayExists("PorePress")&&part.ArrayExists("PorePress0"),"Pore-pressure fields absent");
      const char* posname=part.ArrayExists("Posd")?"Posd":"Pos";
      const char* idname=part.ArrayExists("Idp")?"Idp":"Idpd";
      const bool residual=part.ArrayExists("PorePressRes");
      if(residual)Require(part.GetArray("PorePress")->GetType()==JBinaryDataDef::DatFloat &&
        part.GetArray("PorePressRes")->GetType()==JBinaryDataDef::DatFloat,"Residual requires legacy float pressure/residual");
      const bool stress=part.ArrayExists("Sigma_kk")&&part.ArrayExists("Sigma_ij");
      Require(part.ArrayExists("Sigma_kk")==part.ArrayExists("Sigma_ij"),"Incomplete stress arrays");
      const bool fstype=part.ArrayExists("FSType");
      const std::string schema=Type(part,idname)+','+Type(part,posname)+','+Type(part,"PorePress")+','+Type(part,"PorePress0")+','+
        Type(part,"PorePressRes")+','+Type(part,"Vel")+','+Type(part,"Rhop")+','+Type(part,"Sigma_kk")+','+Type(part,"Sigma_ij")+','+Type(part,"FSType");
      if(piece==0){
        signature=schema;time=part.Get_TimeStep();hasstress=stress;hasfs=fstype;
        nfixed=part.Get_CaseNfixed();nmoving=part.Get_CaseNmoving();nfloat=part.Get_CaseNfloat();nfluid=part.Get_CaseNfluid();
        Require(std::isfinite(time)&&time>=previous,"PART time is non-finite or decreases");
      }
      else Require(schema==signature && part.Get_TimeStep()==time,"PART piece time/schema differ");
      const auto ids=Integers(part,idname,n);const auto pos=Triple(part,posname,n),vel=Triple(part,"Vel",n);
      const auto stored=Scalar(part,"PorePress",n),reference=Scalar(part,"PorePress0",n),low=Scalar(part,"PorePressRes",n,true),rhop=Scalar(part,"Rhop",n);
      const auto sigma=stress?Triple(part,"Sigma_kk",n):std::vector<tdouble3>(n,TDouble3(0));
      const auto shear=stress?Triple(part,"Sigma_ij",n):std::vector<tdouble3>(n,TDouble3(0));
      const auto fsvalues=fstype?Integers(part,"FSType",n):std::vector<ullong>(n,0);
      for(unsigned p=0;p<n;p++){
        const double pressure=stored[p]+low[p];Require(std::isfinite(pressure),"Reconstructed pressure not finite");
        rows.push_back({ids[p],fsvalues[p],pos[p],vel[p],sigma[p],shear[p],pressure,reference[p],stored[p],low[p],rhop[p]});
      }
    }
    std::sort(rows.begin(),rows.end(),[](const Row& a,const Row& b){return a.id<b.id;});
    for(size_t i=0;i<rows.size();i++){
      const Row& r=rows[i];Require(i==0 || rows[i-1].id!=r.id,"Duplicate particle ID across PART pieces");
      state<<index<<','<<r.id<<','<<time<<','<<r.pos.x<<','<<r.pos.y<<','<<r.pos.z<<','<<r.pressure<<','<<r.reference<<','<<r.stored<<','<<r.residual
        <<','<<r.vel.x<<','<<r.vel.y<<','<<r.vel.z<<','<<r.rhop<<',';
      if(hasstress)state<<r.sigma.x<<','<<r.sigma.y<<','<<r.sigma.z<<','<<r.shear.x<<','<<r.shear.y<<','<<r.shear.z;
      else state<<",,,,,";
      state<<',';if(hasfs)state<<r.fstype;state<<'\n';
    }
    metadata<<index<<','<<time<<','<<rows.size()<<','<<npiece<<','<<signature<<','<<nfixed<<','<<nmoving<<','<<nfloat<<','<<nfluid<<'\n';
    previous=time;total+=rows.size();framecount++;
    if(framecount==1 || framecount%50==0 || framecount==frames.size())std::cout<<"FRAME "<<index<<" time="<<std::setprecision(17)<<time<<" rows="<<rows.size()<<std::endl;
  }
  state.flush();metadata.flush();Require(bool(state)&&bool(metadata),"CSV write failed");
  std::ofstream complete(output/"complete.txt");Require(bool(complete),"Cannot create completion marker");
  complete<<"input="<<fs::absolute(dir).string()<<"\nframes="<<framecount<<"\nrows="<<total<<"\nprecision=17 significant digits; native Posd; pressure=stored+legacy residual\n";
  complete.flush();Require(bool(complete),"Completion marker write failed");
  std::cout<<"COMPLETE frames="<<framecount<<" rows="<<total<<" output="<<output.string()<<std::endl;
}
int main(int argc,char** argv){
  try{
    Require(argc>1&&(argc-1)%4==0,"Usage: export_state --dir DATA --out NEW_CSV_DIR [--dir DATA2 --out NEW_CSV_DIR2 ...]");
    for(int i=1;i<argc;i+=4){Require(std::string(argv[i])=="--dir"&&std::string(argv[i+2])=="--out","Expected --dir DATA --out NEW_CSV_DIR pairs");
      Require(!fs::exists(argv[i+3]),"Refusing existing export directory");}
    for(int i=1;i<argc;i+=4)Export(argv[i+1],argv[i+3]);return 0;
  }
  catch(const std::exception& e){std::cerr<<"EXPORT ERROR: "<<e.what()<<'\n';return 1;}
}
