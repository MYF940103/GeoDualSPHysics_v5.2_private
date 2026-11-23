// Experimental read-only pressure-history transfer after the mechanical PRE has been checked.
#pragma once
#include "JPartDataBi4.h"
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace c08_history {
constexpr auto DatUint=JBinaryDataDef::DatUint,DatFloat=JBinaryDataDef::DatFloat;
inline void Require(bool ok,const char* message){
  if(!ok)throw std::runtime_error(message);
}

template<class T> std::vector<T> Array(JBinaryData& node,const char* name,
  JBinaryDataDef::TpData type,unsigned count)
{
  auto* a=node.GetArray(name);
  Require(a && a->GetType()==type,"Missing or incorrectly typed native array");
  const unsigned n=a->DataInPointer()? a->GetCount(): a->GetFileDataCount();
  Require(n==count,"Native pressure or ID array extent differs");
  std::vector<T> x(count);
  Require(a->GetDataCopy(count,x.data())==count,"Incomplete native pressure or ID array");
  return x;
}

struct Source {
  unsigned fixed,completed;
  double previousTime,time,dt;
  std::vector<float> current,previous; // Indexed by ORIGINAL material ID minus original fixed count.
};

inline Source Read(JPartDataBi4& file,unsigned fixed,unsigned soil,unsigned completed,
  double previousTime,double savedTime,double dt)
{
  Require(soil && fixed && soil<=(std::numeric_limits<unsigned>::max)()-fixed,
    "Invalid geometry");
  const unsigned total=fixed+soil;
  auto& p=*file.GetPart();
  Require(p.ExistsValue("HydroMechModel",DatUint) && p.GetvUint("HydroMechModel")==2,
    "Source is missing public M0 TPI identity");
  Require(file.GetNpiece()==1 && !file.GetPiece() && file.Get_CaseNp()==total
    && file.Get_CaseNfixed()==fixed && file.Get_CaseNfluid()==soil && !file.Get_CaseNmoving()
    && !file.Get_CaseNfloat() && !file.Get_NpDynamic() && !file.Get_ReuseIds()
    && file.Get_Npok()==total && !file.Get_Nout(),"Source particle registry differs");
  Require(completed && std::isfinite(dt) && dt>0 && std::isfinite(savedTime) && previousTime>=0.
    && previousTime+dt==savedTime && previousTime<savedTime && file.Get_TimeStep()==savedTime
    && file.Get_Step()==completed-1 && p.GetvDouble("SymplecticDtPre")==dt,"Source clock differs");
  Require(p.GetArraysCount()==22 && p.GetItemsCount()==1,"Missing complete source pressure-history item");
  auto* h=p.GetItem("TpiPressureHistory");
  Require(h && h->GetValuesCount()==8 && h->GetArraysCount()==2 && !h->GetItemsCount()
    && h->GetvUint("Schema")==1 && h->GetvText("Scheme")=="P3_B_alpha_half_beta_zero"
    && h->GetvBool("Valid") && !file.Get_RunCode().empty()
    && h->GetvText("RunCode")==file.Get_RunCode(),"Wrong TPI schema or run");
  Require(h->GetvUint("CompletedUpdates")==completed && h->GetvDouble("PreviousTime")==previousTime
    && h->GetvDouble("SavedTime")==savedTime && h->GetvDouble("Dt")==dt,"Stale TPI source history");
  auto ids=Array<unsigned>(p,"Idp",DatUint,total);
  auto pn=Array<float>(p,"PorePress",DatFloat,total);
  auto owners=Array<unsigned>(*h,"Idp",DatUint,soil);
  auto prev=Array<float>(*h,"PorePressPrev",DatFloat,soil);
  Source out{fixed,completed,previousTime,savedTime,dt,std::vector<float>(soil),std::vector<float>(soil)};
  std::vector<bool> seen(total),historySeen(soil);
  for(unsigned i=0;i<total;i++){
    unsigned id=ids[i];
    Require(id<total && !seen[id],"Duplicate or invalid source particle ID");
    seen[id]=true;
    if(id>=fixed){
      Require(std::isfinite(pn[i]),"Nonfinite source pressure");
      out.current[id-fixed]=pn[i];
    }
  }
  for(unsigned i=0;i<soil;i++){
    const unsigned id=owners[i];
    Require(id>=fixed && id<total && !historySeen[id-fixed],"Duplicate or invalid history owner");
    Require(std::isfinite(prev[i]),"Nonfinite previous pressure");
    historySeen[id-fixed]=true;
    out.previous[id-fixed]=prev[i];
  }
  return out;
}

struct SlotPressure { unsigned slot,id; float current,previous; };

// The receiver retains the original ID namespace even when a contiguous block of
// wall slots disappears. Fixed particles do not own TPI pressure-history entries.
inline std::vector<SlotPressure> Gather(const Source& source,const std::vector<unsigned>& receiver,
  unsigned retireBegin,unsigned retireCount)
{
  const size_t total=source.fixed+source.current.size();
  Require(source.current.size()==source.previous.size() && retireBegin<=source.fixed
    && retireCount<=source.fixed-retireBegin && receiver.size()==total-retireCount,
    "Wrong receiver registry or fixed retirement interval");
  std::vector<bool> seen(total);
  std::vector<SlotPressure> result; result.reserve(source.current.size());
  for(unsigned slot=0;slot<receiver.size();slot++){
    const unsigned id=receiver[slot];
    Require(id<total && !seen[id] && !(id>=retireBegin && id<retireBegin+retireCount),
      "Repeated, retired or invalid receiver ID");
    seen[id]=true;
    if(id>=source.fixed){
      const unsigned i=id-source.fixed;
      result.push_back({slot,id,source.current[i],source.previous[i]});
    }
  }
  Require(result.size()==source.current.size(),"Missing receiver material ID");
  return result;
}
} // namespace c08_history
