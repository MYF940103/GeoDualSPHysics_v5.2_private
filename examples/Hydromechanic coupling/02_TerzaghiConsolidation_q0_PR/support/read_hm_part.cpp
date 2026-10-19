// Case-02 read-only native PART -> CSV; no VTK rounding or solver changes.
#include "JPartDataBi4.h"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>

static void Check(bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);}
template<class T> static std::vector<T> Read(JPartDataBi4& p,const char* name,unsigned n,JBinaryDataDef::TpData type){
  const auto* a=p.GetArray(name,type);
  Check((a->DataInPointer()?a->GetCount():a->GetFileDataCount())==n,"PART array length differs");
  std::vector<T> v(n);if(n)a->GetDataCopy(n,v.data());return v;
}
int main(int argc,char** argv){
  try{
    Check(argc==3,"Usage: ReadHydroMechPart DATA_DIR PART_INDEX");
    const unsigned index=unsigned(std::stoul(argv[2]));
    JPartDataBi4 p;p.LoadFilePart(argv[1],index,0,1);const unsigned n=p.Get_Npok();
    Check(n==1040&&p.Get_CaseNp()==1040&&p.Get_CaseNfluid()==1000&&p.Get_CaseNfixed()==40
      &&p.GetNpiece()==1&&!p.Get_Nout()&&!p.Get_NpDynamic()&&!p.Get_ReuseIds(),"Case-02 native IDs/counts changed");
    const auto ids=Read<unsigned>(p,"Idp",n,JBinaryDataDef::DatUint);
    const auto x=Read<tdouble3>(p,"Posd",n,JBinaryDataDef::DatDouble3);
    const auto v=Read<tfloat3>(p,"Vel",n,JBinaryDataDef::DatFloat3);
    const auto rho=Read<float>(p,"Rhop",n,JBinaryDataDef::DatFloat);
    const auto pressure=Read<float>(p,"PorePress",n,JBinaryDataDef::DatFloat);
    const auto s=Read<tdouble3>(p,"SigmaState_kk",n,JBinaryDataDef::DatDouble3);
    const auto shear=Read<tdouble3>(p,"SigmaState_ij",n,JBinaryDataDef::DatDouble3);
    const auto plastic=Read<float>(p,"Kplastic",n,JBinaryDataDef::DatFloat);
    std::vector<unsigned> fstype(n);
    if(p.GetArray("FSType")->GetType()==JBinaryDataDef::DatUint)fstype=Read<unsigned>(p,"FSType",n,JBinaryDataDef::DatUint);
    else{const auto f=Read<unsigned char>(p,"FSType",n,JBinaryDataDef::DatUchar);std::copy(f.begin(),f.end(),fstype.begin());}
    const auto normal=Read<tfloat3>(p,"FSNormal",n,JBinaryDataDef::DatFloat3);
    const bool hasload=p.ArrayExists("HydroMechLoadAce");
    const auto load=hasload?Read<tfloat3>(p,"HydroMechLoadAce",n,JBinaryDataDef::DatFloat3):std::vector<tfloat3>(n,TFloat3(0));
    std::vector<unsigned> slot(n,~0u);
    for(unsigned i=0;i<n;i++){Check(ids[i]<n&&slot[ids[i]]==~0u,"Duplicate/invalid native ID");slot[ids[i]]=i;}
    std::cout<<std::setprecision(17)<<"time_s,step,stage,id,x,y,z,vx,vy,vz,rho,pressure,sigma_xx,sigma_yy,sigma_zz,sigma_xy,sigma_yz,sigma_xz,kplastic,load_az,fstype,normal_z,drained,single_loaded,load_available\n";
    for(unsigned id=40;id<1040;id++){
      const unsigned i=slot[id];Check(i!=~0u,"Missing native ID");
      const bool drained=p.Get_TimeStep()>=.01-1e-7&&(fstype[i]==2||fstype[i]==3);
      std::cout<<p.Get_TimeStep()<<','<<(index?p.Get_Step()+1:0)<<",full_step,"<<id<<','
        <<x[i].x<<','<<x[i].y<<','<<x[i].z<<','<<v[i].x<<','<<v[i].y<<','<<v[i].z<<','<<rho[i]<<','<<pressure[i]<<','
        <<s[i].x<<','<<s[i].y<<','<<s[i].z<<','<<shear[i].x<<','<<shear[i].y<<','<<shear[i].z<<','
        <<plastic[i]<<','<<load[i].z<<','<<fstype[i]<<','<<normal[i].z<<','<<drained<<','<<((id-40)%100==99&&p.Get_TimeStep()>0)<<','<<hasload<<'\n';
    }
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"PART decoding failed\n";return 2;}
}
