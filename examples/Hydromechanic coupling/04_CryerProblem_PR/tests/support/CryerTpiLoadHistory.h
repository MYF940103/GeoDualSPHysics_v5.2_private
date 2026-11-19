// Private fresh-trajectory round trip through a saved native PART.
#pragma once
#include "CryerTpiPartHistory.h"
#include <algorithm>
#include <cstring>

namespace cryer_history {
void Install(const std::vector<float>& previous,const std::vector<float>& current,unsigned fixed);

template <class T> inline std::vector<T> ReadArray(JBinaryData& data,const char* name,
  JBinaryDataDef::TpData type,unsigned count){
  const auto* array=data.GetArray(name);
  Require(array && array->GetType()==type && array->GetCount()==count,"Invalid history array");
  std::vector<T> result(count);
  Require(array->GetDataCopy(count,result.data())==count,"Incomplete history array");
  return result;
}

inline void Reload(JPartDataBi4& saved,const std::string& dir,unsigned number,bool noRtimes){
  // The native JBinaryData reader materializes the nested arrays as well as the PART.
  JBinaryData data;
  data.LoadFile(dir+JPartDataBi4::GetFileNamePart(number),"JPartDataBi4");
  auto* p=data.GetItem(saved.GetPart()->GetName());
  const std::string run=noRtimes? "00000000":saved.Get_RunCode();
  const unsigned fixed=unsigned(saved.Get_CaseNfixed()), total=saved.Get_Npok();
  Require(data.GetvText("RunCode")==run && p && total>=fixed
    && data.GetvUllong("CaseNfixed")==fixed && data.GetvUllong("CaseNfluid")==total-fixed
    && data.GetvUint("Npiece")==1 && !data.GetvBool("ReuseIds") && !data.GetvBool("NpDynamic")
    && p->GetvUint("Cpart")==number && !p->GetvUint("Nout") && p->GetvUint("Npok")==total
    && p->GetvUint("Step")==saved.Get_Step() && p->GetvDouble("TimeStep")==saved.Get_TimeStep(),
    "Saved pressure history has a different run, owner set or native clock");
  const double dt=p->GetvDouble("SymplecticDtPre");
  const auto h=p->GetItem("TpiPressureHistory");
  Require(h && h->GetvBool("Valid") && h->GetvUint("Schema")==1 && h->GetvText("RunCode")==run
    && h->GetvText("Scheme")=="P3_B_alpha_half_beta_zero" && h->GetArraysCount()==2 && !h->GetItemsCount()
    && h->GetvUint("CompletedUpdates")==1ull+saved.Get_Step()
    && dt==saved.GetPart()->GetvDouble("SymplecticDtPre") && dt>0 && std::isfinite(dt)
    && h->GetvDouble("Dt")==dt && h->GetvDouble("SavedTime")==saved.Get_TimeStep()
    && h->GetvDouble("PreviousTime")==saved.Get_TimeStep()-dt,"Missing or invalid P3 pressure history");
  const auto owners=ReadArray<unsigned>(*h,"Idp",JBinaryDataDef::DatUint,total-fixed);
  const auto values=ReadArray<float>(*h,"PorePressPrev",JBinaryDataDef::DatFloat,total-fixed);
  const auto nativeIds=ReadArray<unsigned>(*p,"Idp",JBinaryDataDef::DatUint,total);
  const auto pressure=ReadArray<float>(*p,"PorePress",JBinaryDataDef::DatFloat,total);
  std::vector<float> previous(total-fixed),current(total);
  std::vector<bool> inHistory(total-fixed),inPart(total);
  for(unsigned i=0;i<total-fixed;i++){
    const unsigned id=owners[i];
    Require(id>=fixed && id<total && !inHistory[id-fixed] && std::isfinite(values[i]),
      "Invalid material pressure-history owner or pressure");
    previous[id-fixed]=values[i];
    inHistory[id-fixed]=true;
  }
  for(unsigned i=0;i<total;i++){
    const unsigned id=nativeIds[i];
    Require(id<total && !inPart[id] && std::isfinite(pressure[i]),"Invalid native owner or pressure");
    current[id]=pressure[i];
    inPart[id]=true;
  }
  Install(previous,current,fixed);
}
}
