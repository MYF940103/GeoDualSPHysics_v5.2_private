// Read-only native BI4 fields for a fixed-wall, fixed-native-particle case.
#include "JPartDataBi4.h"
#include <algorithm>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
static void Check(bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);}
template<class T> static std::vector<T> Read(JPartDataBi4& p,const char* name,unsigned n,JBinaryDataDef::TpData type){
  const auto* a=p.GetArray(name,type);Check((a->DataInPointer()?a->GetCount():a->GetFileDataCount())==n,"Wrong array length");
  std::vector<T> v(n);if(n)a->GetDataCopy(n,v.data());return v;
}
int main(int argc,char** argv){
  try{
    Check(argc==3,"Usage: ReadHydroMechPart DATA_DIR PART_INDEX");
    JPartDataBi4 p;p.LoadFilePart(argv[1],unsigned(std::stoul(argv[2])),0,1);
    const unsigned n=p.Get_Npok(),nb=unsigned(p.Get_CaseNfixed());
    Check(n==p.Get_CaseNp()&&nb+p.Get_CaseNfluid()==n&&p.GetNpiece()==1&&!p.Get_Nout()&&!p.Get_NpDynamic()&&!p.Get_ReuseIds(),"Fixed native set changed");
    const auto id=Read<unsigned>(p,"Idp",n,JBinaryDataDef::DatUint);
    const auto x=Read<tdouble3>(p,"Posd",n,JBinaryDataDef::DatDouble3);
    const auto v=Read<tfloat3>(p,"Vel",n,JBinaryDataDef::DatFloat3);
    const auto rho=Read<float>(p,"Rhop",n,JBinaryDataDef::DatFloat),pw=Read<float>(p,"PorePress",n,JBinaryDataDef::DatFloat);
    const auto s=Read<tdouble3>(p,"SigmaState_kk",n,JBinaryDataDef::DatDouble3),t=Read<tdouble3>(p,"SigmaState_ij",n,JBinaryDataDef::DatDouble3);
    const auto plastic=Read<float>(p,"Kplastic",n,JBinaryDataDef::DatFloat);
    std::vector<unsigned> fstype(n);
    if(p.GetArray("FSType")->GetType()==JBinaryDataDef::DatUint)fstype=Read<unsigned>(p,"FSType",n,JBinaryDataDef::DatUint);
    else{const auto f=Read<unsigned char>(p,"FSType",n,JBinaryDataDef::DatUchar);std::copy(f.begin(),f.end(),fstype.begin());}
    const auto normal=Read<tfloat3>(p,"FSNormal",n,JBinaryDataDef::DatFloat3);
    const bool hasload=p.ArrayExists("HydroMechLoadAce");
    const auto load=hasload?Read<tfloat3>(p,"HydroMechLoadAce",n,JBinaryDataDef::DatFloat3):std::vector<tfloat3>(n,TFloat3(0));
    std::vector<unsigned> slot(n,~0u);for(unsigned i=0;i<n;i++){Check(id[i]<n&&slot[id[i]]==~0u,"Duplicate/invalid ID");slot[id[i]]=i;}
    std::cout<<std::setprecision(17)<<"time_s,saved_step,id,x,y,z,vx,vy,vz,rho,pressure,sigma_xx,sigma_yy,sigma_zz,sigma_xy,sigma_yz,sigma_xz,kplastic,load_az,fstype,normal_x,normal_y,normal_z,load_available\n";
    for(unsigned idp=nb;idp<n;idp++){
      const unsigned i=slot[idp];Check(i!=~0u,"Missing native ID");
      std::cout<<p.Get_TimeStep()<<','<<p.Get_Step()<<','<<idp<<','<<x[i].x<<','<<x[i].y<<','<<x[i].z<<','<<v[i].x<<','<<v[i].y<<','<<v[i].z<<','<<rho[i]<<','<<pw[i]<<','
        <<s[i].x<<','<<s[i].y<<','<<s[i].z<<','<<t[i].x<<','<<t[i].y<<','<<t[i].z<<','<<plastic[i]<<','<<load[i].z<<','<<fstype[i]<<','<<normal[i].x<<','<<normal[i].y<<','<<normal[i].z<<','<<hasload<<'\n';
    }
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Native PART decode failed\n";return 2;}
}
