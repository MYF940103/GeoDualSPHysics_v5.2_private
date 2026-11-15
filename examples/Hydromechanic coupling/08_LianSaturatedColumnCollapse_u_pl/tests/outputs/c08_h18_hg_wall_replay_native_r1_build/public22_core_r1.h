// Offline-only canonical BI4 reader. Never invokes a solver or changes native data.
namespace fs=std::filesystem;
using TpData=JBinaryDataDef::TpData;
static constexpr TpData DatBool=JBinaryDataDef::DatBool,DatUint=JBinaryDataDef::DatUint,
  DatFloat=JBinaryDataDef::DatFloat,DatDouble=JBinaryDataDef::DatDouble,
  DatFloat3=JBinaryDataDef::DatFloat3,DatDouble3=JBinaryDataDef::DatDouble3;
static void Need(bool yes,const std::string& why){if(!yes)throw std::runtime_error(why);}
static bool Close(double got,double ref){return std::isfinite(got)&&std::isfinite(ref)&&std::fabs(got-ref)<=5e-13*(std::max)(std::fabs(ref),DBL_MIN);}
static double Norm2(tdouble3 x){return x.x*x.x+x.y*x.y+x.z*x.z;}
static double Norm2(tfloat3 x){return double(x.x)*x.x+double(x.y)*x.y+double(x.z)*x.z;}
static bool Finite(unsigned){return true;}
static bool Finite(float x){return std::isfinite(x);}
static bool Finite(double x){return std::isfinite(x);}
static bool Finite(tfloat3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}
static bool Finite(tdouble3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}
template<class T> static std::vector<T> NativeArray(JPartDataBi4& part,const char* name,unsigned count,TpData type){
  const auto* array=part.GetArray(name,type);
  Need((array->DataInPointer()?array->GetCount():array->GetFileDataCount())==count,"Wrong native array count: "+std::string(name));
  std::vector<T> result(count);Need(array->GetDataCopy(count,result.data())==count,"Incomplete native array: "+std::string(name));
  for(const auto& value:result)Need(Finite(value),"Nonfinite native array: "+std::string(name));return result;
}
template<class T> static void WriteTyped(std::ofstream& out,const std::vector<T>& values,const std::vector<unsigned>& slot){
  for(unsigned index:slot)out.write(reinterpret_cast<const char*>(&values[index]),sizeof(T));
}
struct Native{
  std::vector<unsigned> ids,fstype,slot;
  std::vector<tdouble3> pos,sk,si;
  std::vector<tfloat3> vel,legacykk,legacyij,normal,load;
  std::vector<float> rhop,plastic,p,p0,excess,posdiv;
  std::vector<double> j,n,theta,volume,rho,k;
};
static Native Load(JPartDataBi4& file,unsigned total,int model){
  Native a;a.ids=NativeArray<unsigned>(file,"Idp",total,DatUint);
  a.pos=NativeArray<tdouble3>(file,"Posd",total,DatDouble3);Need(!file.ArrayExists("Pos"),"Single-precision position is outside this test");
  a.vel=NativeArray<tfloat3>(file,"Vel",total,DatFloat3);a.rhop=NativeArray<float>(file,"Rhop",total,DatFloat);
  a.legacykk=NativeArray<tfloat3>(file,"Sigma_kk",total,DatFloat3);a.legacyij=NativeArray<tfloat3>(file,"Sigma_ij",total,DatFloat3);
  a.sk=NativeArray<tdouble3>(file,"SigmaState_kk",total,DatDouble3);a.si=NativeArray<tdouble3>(file,"SigmaState_ij",total,DatDouble3);
  a.plastic=NativeArray<float>(file,"Kplastic",total,DatFloat);a.fstype=NativeArray<unsigned>(file,"FSType",total,DatUint);
  a.normal=NativeArray<tfloat3>(file,"FSNormal",total,DatFloat3);a.load=NativeArray<tfloat3>(file,"HydroMechLoadAce",total,DatFloat3);
  a.p=NativeArray<float>(file,"PorePress",total,DatFloat);a.p0=NativeArray<float>(file,"PorePress0",total,DatFloat);
  a.excess=NativeArray<float>(file,"ExcessPorePress",total,DatFloat);
  a.slot.assign(total,~0u);
  for(unsigned p=0;p<total;p++){Need(a.ids[p]<total&&a.slot[a.ids[p]]==~0u,"Invalid/duplicate native ID");a.slot[a.ids[p]]=p;}
  for(unsigned index:a.slot)Need(index!=~0u,"Missing native ID");
  const char* dynamic[]={"PoroVolumeRatio","PoroPorosity","PoroThetaLastStage","PoroCurrentVolume","PoroMixtureDensity","PoroHydraulicConductivity"};
  for(const char* name:dynamic)Need(file.ArrayExists(name)==(model>=0),"Wrong ON/OFF dynamic array presence: "+std::string(name));
  Need(file.ArrayExists("PosDiv")==(model>=0),"Wrong ON/OFF actual PosDiv presence");
  if(model>=0){
    a.j=NativeArray<double>(file,dynamic[0],total,DatDouble);a.n=NativeArray<double>(file,dynamic[1],total,DatDouble);
    a.theta=NativeArray<double>(file,dynamic[2],total,DatDouble);a.volume=NativeArray<double>(file,dynamic[3],total,DatDouble);
    a.rho=NativeArray<double>(file,dynamic[4],total,DatDouble);a.k=NativeArray<double>(file,dynamic[5],total,DatDouble);
    a.posdiv=NativeArray<float>(file,"PosDiv",total,DatFloat);
  }return a;
}
static void Original15(std::ofstream& out,const Native& a){
  WriteTyped(out,a.ids,a.slot);WriteTyped(out,a.pos,a.slot);WriteTyped(out,a.vel,a.slot);
  WriteTyped(out,a.legacykk,a.slot);WriteTyped(out,a.legacyij,a.slot);WriteTyped(out,a.normal,a.slot);WriteTyped(out,a.load,a.slot);
  WriteTyped(out,a.rhop,a.slot);WriteTyped(out,a.plastic,a.slot);WriteTyped(out,a.p,a.slot);WriteTyped(out,a.p0,a.slot);WriteTyped(out,a.excess,a.slot);
  WriteTyped(out,a.sk,a.slot);WriteTyped(out,a.si,a.slot);WriteTyped(out,a.fstype,a.slot);
}
