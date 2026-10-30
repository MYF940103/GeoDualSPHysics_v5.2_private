// Read-only all-ID Stage1 export: the original 35 columns are unchanged.
// mass remains Get_MassFluid() even for boundary rows; it is not per-ID mass.
// Requires native float PorePress0 and ExcessPorePress; neither is reconstructed.
#include "JPartDataBi4.h"
#include <algorithm>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
static void Check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
template<class T> static std::vector<T> Read(JPartDataBi4& p,const char* name,unsigned n,JBinaryDataDef::TpData type){
  const auto* a=p.GetArray(name,type);
  Check((a->DataInPointer()?a->GetCount():a->GetFileDataCount())==n,"Wrong native array length");
  std::vector<T> v(n);if(n)a->GetDataCopy(n,v.data());return v;
}
static std::vector<tdouble3> Triples(JPartDataBi4& p,const char* name,unsigned n){
  if(p.GetArray(name)->GetType()==JBinaryDataDef::DatDouble3)return Read<tdouble3>(p,name,n,JBinaryDataDef::DatDouble3);
  const auto f=Read<tfloat3>(p,name,n,JBinaryDataDef::DatFloat3);std::vector<tdouble3> v(n);
  for(unsigned i=0;i<n;i++)v[i]=TDouble3(f[i].x,f[i].y,f[i].z);return v;
}
int main(int argc,char** argv){
  try{
    Check(argc==3,"Usage: ReadSelfWeightNative DATA_DIR PART_INDEX");
    JPartDataBi4 p;p.LoadFilePart(argv[1],unsigned(std::stoul(argv[2])),0,1);
    const unsigned n=p.Get_Npok(),nb=unsigned(p.Get_CaseNfixed());
    Check(n==p.Get_CaseNp()&&nb+p.Get_CaseNfluid()==n&&p.GetNpiece()==1&&!p.Get_Nout()&&!p.Get_NpDynamic()&&!p.Get_ReuseIds(),"Native particle set changed");
    const auto id=Read<unsigned>(p,"Idp",n,JBinaryDataDef::DatUint);
    const bool posd=p.ArrayExists("Posd"),sd=p.ArrayExists("SigmaState_kk"),hl=p.ArrayExists("HydroMechLoadAce");
    const auto x=Triples(p,posd?"Posd":"Pos",n),s=Triples(p,sd?"SigmaState_kk":"Sigma_kk",n),t=Triples(p,sd?"SigmaState_ij":"Sigma_ij",n);
    const auto v=Read<tfloat3>(p,"Vel",n,JBinaryDataDef::DatFloat3),normal=Read<tfloat3>(p,"FSNormal",n,JBinaryDataDef::DatFloat3);
    const auto load=hl?Read<tfloat3>(p,"HydroMechLoadAce",n,JBinaryDataDef::DatFloat3):std::vector<tfloat3>(n,TFloat3(0));
    const auto rho=Read<float>(p,"Rhop",n,JBinaryDataDef::DatFloat),pw=Read<float>(p,"PorePress",n,JBinaryDataDef::DatFloat);
    Check(p.ArrayExists("PorePress0")&&p.ArrayExists("ExcessPorePress"),"Required native PorePress0/ExcessPorePress array is absent");
    const auto pw0=Read<float>(p,"PorePress0",n,JBinaryDataDef::DatFloat),excess=Read<float>(p,"ExcessPorePress",n,JBinaryDataDef::DatFloat);
    const auto plastic=Read<float>(p,"Kplastic",n,JBinaryDataDef::DatFloat);
    std::vector<unsigned> fs(n),slot(n,~0u);
    if(p.GetArray("FSType")->GetType()==JBinaryDataDef::DatUint)fs=Read<unsigned>(p,"FSType",n,JBinaryDataDef::DatUint);
    else{const auto f=Read<unsigned char>(p,"FSType",n,JBinaryDataDef::DatUchar);std::copy(f.begin(),f.end(),fs.begin());}
    for(unsigned i=0;i<n;i++){Check(id[i]<n&&slot[id[i]]==~0u,"Invalid native ID");slot[id[i]]=i;}
    const JBinaryData* part=p.GetPart();
    std::cout<<std::setprecision(17)<<"time_s,saved_step,id,x,y,z,vx,vy,vz,rho,pressure,sigma_xx,sigma_yy,sigma_zz,sigma_xy,sigma_yz,sigma_xz,kplastic,load_ax,load_ay,load_az,fstype,normal_x,normal_y,normal_z,load_available,position_double,stress_double,mass,dp,h,native_count,nout,has_dterror,dterror_s,is_boundary,porepress0,excess_native\n";
    for(unsigned idp=0;idp<n;idp++){
      const unsigned i=slot[idp];Check(i!=~0u,"Missing native ID");
      std::cout<<p.Get_TimeStep()<<','<<p.Get_Step()<<','<<idp<<','<<x[i].x<<','<<x[i].y<<','<<x[i].z<<','<<v[i].x<<','<<v[i].y<<','<<v[i].z<<','<<rho[i]<<','<<pw[i]<<','
        <<s[i].x<<','<<s[i].y<<','<<s[i].z<<','<<t[i].x<<','<<t[i].y<<','<<t[i].z<<','<<plastic[i]<<','<<load[i].x<<','<<load[i].y<<','<<load[i].z<<','
        <<fs[i]<<','<<normal[i].x<<','<<normal[i].y<<','<<normal[i].z<<','<<hl<<','<<posd<<','<<sd<<','<<p.Get_MassFluid()<<','<<p.Get_Dp()<<','<<p.Get_H()<<','
        <<n<<','<<p.Get_Nout()<<','<<part->ExistsValue("dterror")<<','<<part->GetvDouble("dterror",true,0)<<','<<(idp<nb)<<','<<pw0[i]<<','<<excess[i]<<'\n';
    }
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Native PART decode failed\n";return 2;}
}
