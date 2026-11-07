// Narrow, certified elastic gravity-preload PRE state. This is not a PART restart.
#ifndef _JGravityPreloadState_
#define _JGravityPreloadState_

#include "JPartDataBi4.h"
#include "JBinaryData.h"
#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

// The caller first validates the fresh axis-aligned fixed 2-D container and its
// contract. After Load it must match fixed positions, all p0 bits and the MK
// interval to that fresh seed before importing by original ID.
class JGravityPreloadState{
public:
  unsigned Count=0,Fixed=0,CompletedStep=0,MaterialLawVersion=0;
  unsigned RetireBegin=0,RetireCount=0,MkBound=0;
  double Time=0.,Dt=0.;
  std::vector<unsigned> Idp,ById,FSType;
  std::vector<tdouble3> Pos,SigmaKK,SigmaIJ;
  std::vector<tfloat4> VelRhop;
  std::vector<float> Kplastic,PorePress,PorePress0,PosDiv;
  std::vector<double> J,Theta;
  std::vector<tfloat3> FSNormal;

private:
  typedef JBinaryDataDef::TpData TpData;
  static constexpr TpData DatText=JBinaryDataDef::DatText,DatBool=JBinaryDataDef::DatBool,
    DatUint=JBinaryDataDef::DatUint,DatFloat=JBinaryDataDef::DatFloat,
    DatDouble=JBinaryDataDef::DatDouble,DatFloat3=JBinaryDataDef::DatFloat3,
    DatDouble3=JBinaryDataDef::DatDouble3;
  static void Need(bool valid,const std::string& text){
    if(!valid)throw std::runtime_error(text);
  }
  static bool Finite(unsigned){return true;}
  static bool Finite(float x){return std::isfinite(x);}
  static bool Finite(double x){return std::isfinite(x);}
  static bool Finite(tfloat3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}
  static bool Finite(tdouble3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}
  static bool Bits(float a,float b){return !std::memcmp(&a,&b,sizeof(a));}
  static bool Bits(double a,double b){return !std::memcmp(&a,&b,sizeof(a));}
  static bool Close(double got,double ref){
    return Finite(got)&&Finite(ref)
      && std::fabs(got-ref)<=5e-13*(std::max)(std::fabs(ref),DBL_MIN);
  }
  template<class T> static std::vector<T> Read(JPartDataBi4& file
    ,const char* name,unsigned count,TpData type)
  {
    const JBinaryDataArray* a=file.GetArray(name,type);
    Need((a->DataInPointer()? a->GetCount(): a->GetFileDataCount())==count
      ,std::string("Wrong native array count: ")+name);
    std::vector<T> values(count);
    Need(a->GetDataCopy(count,values.data())==count
      ,std::string("Incomplete native array: ")+name);
    for(const auto& value:values)Need(Finite(value),std::string("Nonfinite native array: ")+name);
    return values;
  }

public:
  void Load(const std::string& file,const std::string& contract,unsigned count
    ,unsigned fixed,unsigned eventstep,double eventtime,double dt,float targetcoh
    ,double n0,double rho0,double water,double mass,double k0,double ck)
  {
    try{
      static_assert(sizeof(unsigned)==4&&sizeof(float)==4&&sizeof(double)==8
        && sizeof(tfloat3)==12&&sizeof(tdouble3)==24,"Native typed layout differs.");
      Need(count>fixed&&fixed>0&&!contract.empty(),"Empty handoff geometry/contract.");
      Need(eventstep>0&&eventstep<unsigned((std::numeric_limits<int>::max)())
        && Finite(eventtime)&&eventtime>0&&Finite(dt)&&dt>0,"Invalid handoff event/dt.");
      const double grid=eventtime/dt;
      Need(Finite(grid)&&std::fabs(grid-double(eventstep))
        <=16.*DBL_EPSILON*(std::max)(1.,std::fabs(grid)),"Event is not on the fixed-step grid.");
      Need(Finite(targetcoh)&&targetcoh>=0&&Finite(n0)&&n0>0&&n0<1
        && Finite(rho0)&&Finite(water)&&water>0&&rho0>n0*water
        && Finite(mass)&&mass>0&&Finite(k0)&&k0>0&&Finite(ck)&&ck>0
        ,"Invalid effective material/hydraulic constants.");

      const std::size_t slash=file.find_last_of("/\\");
      const std::string name=file.substr(slash==std::string::npos? 0: slash+1);
      Need(name.size()>=13&&name.compare(0,5,"Part_")==0
        && name.compare(name.size()-4,4,".bi4")==0,"Only a standard Part_####.bi4 file is allowed.");
      for(std::size_t c=5;c<name.size()-4;c++)
        Need(name[c]>='0'&&name[c]<='9',"Invalid native PART number.");
      const unsigned long number=std::stoul(name.substr(5,name.size()-9));
      Need(number<=(std::numeric_limits<unsigned>::max)(),"Native PART number overflow.");
      const unsigned part=unsigned(number);
      Need(name==JPartDataBi4::GetFileNamePart(part),"Nonstandard native PART filename.");
      const std::string dir=(slash==std::string::npos? ".": file.substr(0,slash+1));
      JPartDataBi4 f;f.LoadFilePart(dir,part,0,1);
      Need(f.GetNpiece()==1&&f.GetPiece()==0&&f.Get_Npok()==count&&!f.Get_Nout()
        && f.Get_CaseNp()==count&&f.Get_CaseNfixed()==fixed
        && f.Get_CaseNfluid()==count-fixed&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat()
        ,"Native original registry/counts/exclusions differ.");
      Need(f.Get_Data2d()&&f.Get_Data2dPosY()==0&&!f.Get_Symmetry()
        && !f.Get_NpDynamic()&&!f.Get_ReuseIds()&&f.Get_PeriMode()==PERI_None
        ,"Handoff requires a static nonperiodic 2-D native case.");
      Need(Finite(f.Get_Dp())&&f.Get_Dp()>0&&Finite(f.Get_H())&&f.Get_H()>0
        && f.Get_Rhop0()==rho0&&f.Get_MassFluid()==mass&&f.Get_MassBound()==mass
        ,"Native geometry/reference density/mass differs.");
      const JBinaryData* p=f.GetPart();
      Need(p->ExistsValue("GravityPreloadHandoffSchema",DatUint)
        && p->GetvUint("GravityPreloadHandoffSchema")==1
        && p->ExistsValue("GravityPreloadElasticSource",DatBool)
        && p->GetvBool("GravityPreloadElasticSource")
        && p->ExistsValue("GravityPreloadHandoffContract",DatText)
        && p->GetvText("GravityPreloadHandoffContract")==contract
        ,"Missing/incompatible certified elastic handoff schema/contract.");
      Need(p->ExistsValue("GravityPreloadSourceCohesion",DatFloat)
        && Finite(p->GetvFloat("GravityPreloadSourceCohesion"))
        && p->GetvFloat("GravityPreloadSourceCohesion")>=0.f
        && p->GetvFloat("GravityPreloadSourceCohesion")<=targetcoh
        ,"Source cohesion exceeds the target or is invalid.");
      Need(p->ExistsValue("GravityPreloadPhase",DatUint)&&p->GetvUint("GravityPreloadPhase")==0
        && p->ExistsValue("GravityPreloadRequestedTime",DatDouble)
        && Bits(p->GetvDouble("GravityPreloadRequestedTime"),eventtime)
        && p->ExistsValue("GravityPreloadEventCompletedStep",DatUint)
        && p->GetvUint("GravityPreloadEventCompletedStep")==eventstep
        && !p->ExistsValue("GravityPreloadActualTime")
        && !p->ExistsValue("GravityPreloadActualCompletedStep")
        ,"The native state is not an unreleased PRE event.");
      Need(p->ExistsValue("SoilDampingActive",DatBool)&&p->GetvBool("SoilDampingActive")
        && p->ExistsValue("PoreShepardActive",DatBool)&&p->GetvBool("PoreShepardActive")
        && p->ExistsValue("HydroMechFreeSeepage",DatBool)&&p->GetvBool("HydroMechFreeSeepage")
        ,"Required preload/free-seepage flags differ.");
      const bool unified=p->ExistsValue("MaterialLawVersion");
      if(unified)Need(p->ExistsValue("MaterialLawVersion",DatUint)&&p->GetvUint("MaterialLawVersion")==2
        ,"Unknown/untyped material-law version in certified PRE.");
      else Need(p->ExistsValue("MaterialReturn",DatUint)&&p->GetvUint("MaterialReturn")==1
        ,"Legacy certified elastic PRE requires MaterialReturn=1.");
      Need(p->ExistsValue("DilationDecay",DatFloat)
        && Finite(p->GetvFloat("DilationDecay"))&&p->GetvFloat("DilationDecay")>=0.f
        && p->ExistsValue("HydroMechDynamicSeepage",DatBool)&&p->GetvBool("HydroMechDynamicSeepage")
        && p->ExistsValue("DynamicSeepageSchema",DatUint)&&p->GetvUint("DynamicSeepageSchema")==1
        && p->ExistsValue("HydroMechConductivityModel",DatUint)&&p->GetvUint("HydroMechConductivityModel")==1
        && p->ExistsValue("HydroMechConductivityCk",DatDouble)
        && Bits(p->GetvDouble("HydroMechConductivityCk"),ck)
        ,"Material/dynamic/conductivity metadata differs.");
      Need(p->ExistsValue("GravityPreloadReleaseMkBound",DatUint)
        && p->ExistsValue("GravityPreloadTargetIdBegin",DatUint)
        && p->ExistsValue("GravityPreloadTargetIdCount",DatUint)
        ,"Typed release target metadata is missing.");
      Need(p->ExistsValue("SymplecticDtPre",DatDouble)
        && Bits(p->GetvDouble("SymplecticDtPre"),dt)&&f.Get_Step()==eventstep-1
        ,"Native current dt/completed-step event differs.");
      Need(p->ExistsValue("dterror",DatDouble),"Native signed necessary-step diagnostic is missing.");
      const double error=p->GetvDouble("dterror");
      Need(Finite(error)&&error!=-DBL_MAX&&error<=1e-14,"Native signed necessary-step guard failed/empty.");
      volatile double scalar=0.;
      for(unsigned step=0;step<eventstep;step++)scalar+=dt;
      Need(Finite(f.Get_TimeStep())&&f.Get_TimeStep()>0
        && std::fabs(f.Get_TimeStep()-double(scalar))<=1e-14
        ,"Native clock differs from actual scalar+=dt replay.");

      JGravityPreloadState state;
      state.Count=count;state.Fixed=fixed;state.CompletedStep=f.Get_Step()+1;
      state.MaterialLawVersion=(unified? 2u: 1u);
      state.Time=f.Get_TimeStep();state.Dt=p->GetvDouble("SymplecticDtPre");
      state.MkBound=p->GetvUint("GravityPreloadReleaseMkBound");
      state.RetireBegin=p->GetvUint("GravityPreloadTargetIdBegin");
      state.RetireCount=p->GetvUint("GravityPreloadTargetIdCount");
      Need(state.RetireBegin<fixed&&state.RetireCount>0
        && state.RetireCount<=fixed-state.RetireBegin,"Release target is outside the original fixed ID domain.");
      Need(f.ArraysCount()==22&&!f.ArrayExists("Pos"),"Exactly 22 original double-position typed arrays are required.");
      state.Idp=Read<unsigned>(f,"Idp",count,DatUint);
      state.Pos=Read<tdouble3>(f,"Posd",count,DatDouble3);
      const auto velocity=Read<tfloat3>(f,"Vel",count,DatFloat3);
      const auto rhop=Read<float>(f,"Rhop",count,DatFloat);
      const auto legacykk=Read<tfloat3>(f,"Sigma_kk",count,DatFloat3);
      const auto legacyij=Read<tfloat3>(f,"Sigma_ij",count,DatFloat3);
      state.SigmaKK=Read<tdouble3>(f,"SigmaState_kk",count,DatDouble3);
      state.SigmaIJ=Read<tdouble3>(f,"SigmaState_ij",count,DatDouble3); // (xy,yz,xz).
      state.Kplastic=Read<float>(f,"Kplastic",count,DatFloat);
      state.FSType=Read<unsigned>(f,"FSType",count,DatUint);
      state.FSNormal=Read<tfloat3>(f,"FSNormal",count,DatFloat3);
      const auto load=Read<tfloat3>(f,"HydroMechLoadAce",count,DatFloat3);
      state.PorePress=Read<float>(f,"PorePress",count,DatFloat);
      state.PorePress0=Read<float>(f,"PorePress0",count,DatFloat);
      const auto excess=Read<float>(f,"ExcessPorePress",count,DatFloat);
      state.J=Read<double>(f,"PoroVolumeRatio",count,DatDouble);
      const auto porosity=Read<double>(f,"PoroPorosity",count,DatDouble);
      state.Theta=Read<double>(f,"PoroThetaLastStage",count,DatDouble);
      const auto volume=Read<double>(f,"PoroCurrentVolume",count,DatDouble);
      const auto density=Read<double>(f,"PoroMixtureDensity",count,DatDouble);
      const auto conductivity=Read<double>(f,"PoroHydraulicConductivity",count,DatDouble);
      state.PosDiv=Read<float>(f,"PosDiv",count,DatFloat);
      state.ById.assign(count,~0u);state.VelRhop.resize(count);
      const double solid=1.-n0,v0=mass/rho0;
      unsigned freesurface=0;
      for(unsigned q=0;q<count;q++){
        const unsigned id=state.Idp[q];
        Need(id<count&&state.ById[id]==~0u&&(id<fixed)==(q<fixed)
          ,"Unknown/duplicate native ID or fixed/raw classification differs.");
        state.ById[id]=q;
        const auto x=state.Pos[q],s=state.SigmaKK[q],t=state.SigmaIJ[q];
        const auto v=velocity[q];
        state.VelRhop[q]=TFloat4(v.x,v.y,v.z,rhop[q]);
        Need(x.y==0&&rhop[q]>=700.f&&rhop[q]<=3000.f
          && state.Kplastic[q]==0.f&&state.FSType[q]<=4
          && load[q].x==0.f&&load[q].y==0.f&&load[q].z==0.f
          && excess[q]==float(state.PorePress[q]-state.PorePress0[q])
          ,"Native plane/density/elastic history/FS/no-load/excess guard failed.");
        Need(legacykk[q].x==float(s.x)&&legacykk[q].y==float(s.y)&&legacykk[q].z==float(s.z)
          && legacyij[q].x==float(t.x)&&legacyij[q].y==float(t.y)&&legacyij[q].z==float(t.z)
          ,"Legacy stress display does not round the full double state.");
        const double j=state.J[q];
        Need(j>solid,"Native J is outside the saturated domain.");
        if(id<fixed){
          Need(v.x==0.f&&v.y==0.f&&v.z==0.f&&state.Theta[q]==0.
            && porosity[q]==0.&&volume[q]==0.&&density[q]==0.&&conductivity[q]==0.
            ,"Native fixed velocity/theta/derived zero marker differs.");
        }
        else{
          const double n=1.-solid/j,V=v0*j,rho=water+(rho0-water)/j;
          const double k=(j==1.? k0: k0*std::exp((j-1.)/(solid*ck)));
          Need(n>0&&n<1&&V>0&&rho>0&&Finite(k)&&k>0
            && std::fabs((1.-porosity[q])*j-solid)<=5e-13
            && Close(porosity[q],n)&&Close(volume[q],V)&&Close(density[q],rho)
            && conductivity[q]>0&&Close(conductivity[q],k)
            ,"Native n/V/rho/k does not follow its actual J.");
          if(j==1.)Need(Bits(conductivity[q],k0),"J1 conductivity differs from exact k0.");
          Need(Bits(rhop[q],float(rho)),"Native float density cache differs from actual J.");
          if(state.FSType[q]==2||state.FSType[q]==3){
            Need(state.PorePress[q]<=0.f,"Native free-surface soil pressure is positive.");
            freesurface++;
          }
        }
      }
      for(unsigned slot:state.ById)Need(slot!=~0u,"Missing original native ID.");
      Need(freesurface>0,"Native free-seepage mask is empty.");
      // Preserve raw array order. ById alone maps each original ID to its raw slot.
      *this=std::move(state);
    }
    catch(const std::exception& e){
      throw std::runtime_error(std::string("Gravity preload handoff '")+file+"': "+e.what());
    }
    catch(...){
      throw std::runtime_error(std::string("Gravity preload handoff '")+file+"': native load failed.");
    }
  }
};

#endif
