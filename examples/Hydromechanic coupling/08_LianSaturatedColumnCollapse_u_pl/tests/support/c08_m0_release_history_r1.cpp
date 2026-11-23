// Native regression for the experimental read-only C08 pressure history transfer.
#include "c08_m0_release_history_r1.h"
#include "JException.h"
#include <algorithm>
#include <cstring>
#include <filesystem>
#include <iomanip>
#include <iostream>

using namespace c08_history;
namespace fs=std::filesystem;
using U=unsigned;

static void Load(JPartDataBi4& f,const fs::path& path,U part){
  Require(path.filename().string()==JPartDataBi4::GetFileNamePart(part),"Unexpected physical PART filename");
  f.LoadFilePart(path.parent_path().string(),part);
}
static bool Same(float a,float b){return std::memcmp(&a,&b,sizeof(a))==0;}
static double Clock(U n,double dt){
  double t=0.;for(U i=0;i<n;i++)t+=dt;return t;
}
template<class F> static void Reject(F action,const char* text){
  try{action();}catch(const std::runtime_error& e){
    Require(std::string(e.what()).find(text)!=std::string::npos,"Wrong rejection reason");return;
  }
  throw std::runtime_error("An invalid history was accepted");
}
static std::vector<U> Ids(JPartDataBi4& f){
  return Array<U>(*f.GetPart(),"Idp",DatUint,f.Get_Npok());
}

// This reference is appropriate only for consecutive, non-Dirichlet source
// steps; projected source pressure may differ from the previous saved PART at opening.
static void CheckAdjacent(const Source& src,JPartDataBi4& previous){
  Require(previous.Get_TimeStep()==src.previousTime && previous.Get_Step()+2u==src.completed,
    "Reference source is not the previous completed physical step");
  auto ids=Ids(previous);auto p=Array<float>(*previous.GetPart(),"PorePress",DatFloat,previous.Get_Npok());
  Require(ids.size()==src.fixed+src.current.size(),"Wrong previous-step geometry");
  std::vector<bool> seen(ids.size());
  for(U slot=0;slot<ids.size();slot++){
    const U id=ids[slot];Require(id<ids.size() && !seen[id],"Invalid previous-step material ID");
    seen[id]=true;
    if(id>=src.fixed)Require(Same(src.previous[id-src.fixed],p[slot]),"Reference source pressure bits differ");
  }
}
static void CheckPermutation(const Source& src,std::vector<U> receiver,U begin,U count){
  auto result=Gather(src,receiver,begin,count);
  std::reverse(receiver.begin(),receiver.end());
  auto permuted=Gather(src,receiver,begin,count);
  std::reverse(permuted.begin(),permuted.end());
  for(U i=0;i<result.size();i++){
    Require(result[i].id==permuted[i].id && result[i].slot+permuted[i].slot==receiver.size()-1
      && Same(result[i].current,permuted[i].current) && Same(result[i].previous,permuted[i].previous),
      "A slot permutation changed the two carried pressures");
  }
  Reject([&]{auto bad=receiver;bad.pop_back();Gather(src,bad,begin,count);},"registry");
  Reject([&]{auto bad=receiver;bad[0]=bad[1];Gather(src,bad,begin,count);},"receiver ID");
  if(count){
    Reject([&]{auto bad=receiver;bad[0]=begin;Gather(src,bad,begin,count);},"receiver ID");
    Reject([&]{Gather(src,receiver,begin+1,count);},"registry");
  }
}
static void CheckNegativePaths(const fs::path& file,U part,U fixed,U soil,U step,double dt){
  const double prev=Clock(step-1,dt),saved=prev+dt;
  auto read=[&](JPartDataBi4& f){return Read(f,fixed,soil,step,prev,saved,dt);};
  {
    JPartDataBi4 f;Load(f,file,part);
    Reject([&]{Read(f,fixed,soil,step-1,prev,saved,dt);},"clock");
    Reject([&]{Read(f,fixed,soil,step,prev-dt,saved,dt);},"clock");
    auto* h=f.GetPart()->GetItem("TpiPressureHistory");
    h->SetvDouble("PreviousTime",prev-dt);
    Reject([&]{read(f);},"Stale TPI");
    h->SetvDouble("PreviousTime",prev);h->SetvText("RunCode","wrong-source");
    Reject([&]{read(f);},"schema or run");
    h->SetvText("RunCode",f.Get_RunCode());h->SetvUint("CompletedUpdates",step-1);
    Reject([&]{read(f);},"Stale TPI");
    h->SetvUint("CompletedUpdates",step);h->SetvBool("Valid",false);
    Reject([&]{read(f);},"schema or run");
  }
  {
    JPartDataBi4 f;Load(f,file,part);auto* h=f.GetPart()->GetItem("TpiPressureHistory");
    auto owners=Array<U>(*h,"Idp",DatUint,soil);
    std::swap(owners.front(),owners.back());
    auto p=Array<float>(*h,"PorePressPrev",DatFloat,soil);std::swap(p.front(),p.back());
    const auto original=read(f);
    h->GetArray("Idp")->SetData(soil,owners.data(),false);
    h->GetArray("PorePressPrev")->SetData(soil,p.data(),false);
    const auto permuted=read(f);
    Require(!std::memcmp(original.previous.data(),permuted.previous.data(),soil*sizeof(float)),
      "Native history payload order changed source values");
    owners.front()=owners.back();h->GetArray("Idp")->SetData(soil,owners.data(),false);
    Reject([&]{read(f);},"history owner");
    f.GetPart()->RemoveItem("TpiPressureHistory");
    Reject([&]{read(f);},"source pressure-history item");
  }
}
int main(int argc,char** argv){try{
  Require(argc==3||argc==8,"usage: reader retained HYDRO_ROOT | reader short SHORT_DATA PART STEP DT PREVIOUS_PART HYDRO_ROOT");
  std::cout<<std::setprecision(17);
  const fs::path hydro=argv[argc-1];
  const auto out=hydro/"08_LianSaturatedColumnCollapse_u_pl/tests/outputs";
  const auto receiverFile=out/"c08_h18_storage_debug2_GPU_r1/data/Part_0000.bi4";
  JPartDataBi4 pre,receiver;
  Load(pre,out/"c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4",1000);Load(receiver,receiverFile,0);
  const auto* pm=pre.GetPart();
  const U total=7060,fixed=2060,soil=5000,begin=pm->GetvUint("GravityPreloadTargetIdBegin"),
    count=pm->GetvUint("GravityPreloadTargetIdCount");
  Require(begin==1805 && count==255 && pm->GetvUint("GravityPreloadHandoffSchema")==2
    && !pm->GetvUint("GravityPreloadPhase") && receiver.GetPart()->GetvUint("GravityPreloadPhase")==1
    && !pre.Get_Nout() && !receiver.Get_Nout() && pre.Get_Npok()==total && receiver.Get_Npok()==6805,
    "Unexpected real C08 source or released geometry");
  auto receiverIds=Ids(receiver);
  Reject([&]{Read(pre,fixed,soil,2000000,Clock(1999999,5e-6),Clock(2000000,5e-6),5e-6);},"missing public M0");
  if(std::string(argv[1])=="retained"){
    Require(argc==3,"Unexpected retained arguments");
    const auto sphere=hydro/"04_CryerProblem_PR/tests/outputs/public_tpi_sphere4hist_gpu_hist1/result/data";
    const double dt=std::ldexp(1.,-19);
    JPartDataBi4 f,f3;Load(f,sphere/"Part_0004.bi4",4);Load(f3,sphere/"Part_0003.bi4",3);
    auto source=Read(f,8,37173,4,3*dt,4*dt,dt);
    CheckAdjacent(source,f3);CheckPermutation(source,Ids(f),0,0);
    CheckNegativePaths(sphere/"Part_0004.bi4",4,8,37173,4,dt);
    // The adjacent REAL finite-Kw post-release records exercise only gather
    // and geometry. No M0 child is attached, manufactured or inferred for PRE.
    JPartDataBi4 second;Load(second,receiverFile.parent_path()/"Part_0001.bi4",1);
    const auto right=Ids(second);
    auto p=Array<float>(*receiver.GetPart(),"PorePress",DatFloat,receiver.Get_Npok());
    auto q=Array<float>(*second.GetPart(),"PorePress",DatFloat,second.Get_Npok());
    Source mapping{fixed,2000002,receiver.Get_TimeStep(),second.Get_TimeStep(),5e-6,
      std::vector<float>(soil),std::vector<float>(soil)};
    Require(receiver.Get_Step()+1==2000001 && second.Get_Step()+1==mapping.completed
      && mapping.previousTime+mapping.dt==mapping.time,"Old C08 frames are not adjacent");
    for(U i=0;i<p.size();i++)if(receiverIds[i]>=fixed)mapping.previous.at(receiverIds[i]-fixed)=p[i];
    for(U i=0;i<q.size();i++)if(right[i]>=fixed)mapping.current.at(right[i]-fixed)=q[i];
    CheckPermutation(mapping,receiverIds,begin,count);CheckPermutation(mapping,right,begin,count);
    auto fsvalues=Array<U>(*second.GetPart(),"FSType",DatUint,second.Get_Npok());
    U surface=0,negative=0,changed=0;
    for(const auto& s:Gather(mapping,right,begin,count)){
      Require(Same(s.current,q[s.slot]),"C08 mapping did not return original pressure");
      changed+=!Same(s.current,s.previous);
      if(fsvalues[s.slot]==2 || fsvalues[s.slot]==3){
        surface++;Require(s.current<=0,"Positive completed free-seepage pressure");negative+=s.current<0;
      }
    }
    std::cout<<"{\"real_M0_reference\":\"C04\",\"m0_soil_ids\":37173,\"c08_geometry_frame\":0,"
      "\"c08_gathered_soil\":5000,\"retired_fixed\":255,\"legacy_source_rejected\":true,"
      "\"finite_Kw_changed_pressures\":"<<changed<<",\"finite_Kw_FS\":"<<surface<<",\"finite_Kw_negative_FS\":"<<negative<<"}\n";
  }else{
    Require(argc==8&&std::string(argv[1])=="short","Unknown test mode");
    fs::path data=argv[2];U part=std::stoul(argv[3]),step=std::stoul(argv[4]);
    const double dt=std::stod(argv[5]);U previousPart=std::stoul(argv[6]);
    JPartDataBi4 f,f1;Load(f,data/JPartDataBi4::GetFileNamePart(part),part);
    Load(f1,data/JPartDataBi4::GetFileNamePart(previousPart),previousPart);
    const double previousTime=Clock(step-1,dt);
    Require(!f.GetPart()->GetvUint("GravityPreloadPhase") && !f1.GetPart()->GetvUint("GravityPreloadPhase")
      && f.Get_RunCode()==f1.Get_RunCode(),"Short source phase or trajectory differs");
    const auto s=Read(f,fixed,soil,step,previousTime,previousTime+dt,dt);
    CheckAdjacent(s,f1);CheckPermutation(s,receiverIds,begin,count);
    CheckNegativePaths(data/JPartDataBi4::GetFileNamePart(part),part,fixed,soil,step,dt);
    U changed=0;for(const auto& x:Gather(s,receiverIds,begin,count))changed+=!Same(x.current,x.previous);
    std::cout<<"{\"real_M0_reference\":\"C08 walled short\",\"completed\":"<<step<<",\"saved_s\":"<<s.time
      <<",\"previous_s\":"<<s.previousTime<<",\"soil_ids\":5000,\"retired_fixed\":255,"
      "\"history_differs_from_current\":"<<changed<<",\"actual_release_in_this_test\":false}\n";
  }
  return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';}catch(const std::exception& e){std::cerr<<e.what()<<'\n';}
return 1;}
