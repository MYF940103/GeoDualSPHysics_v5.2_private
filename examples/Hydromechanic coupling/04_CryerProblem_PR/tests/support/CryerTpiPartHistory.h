// Private fixed-owner Cryer PART extension for the pressure predictor.
#pragma once
#include "JPartDataBi4.h"
#include <cmath>
#include <stdexcept>
#include <vector>

namespace cryer_history {
inline void Require(bool condition,const char* message){
  if(!condition)throw std::runtime_error(message);
}

// Return true only when a child was attached. Its lifetime is one PART write.
bool Attach(JPartDataBi4& file,bool noRtimes);

inline void Write(JPartDataBi4& file,bool noRtimes,unsigned long long commits,
  double previousTime,double savedTime,double dt,const std::vector<unsigned>& ids,
  const float* previous,unsigned count){
  JBinaryData& part=*file.GetPart();
  Require(!part.GetItem("TpiPressureHistory") && part.GetvUint("Cpart")>0
    && commits==1ull+file.Get_Step() && file.Get_TimeStep()==savedTime
    && previousTime+dt==savedTime && dt==part.GetvDouble("SymplecticDtPre")
    && std::isfinite(dt) && dt>0,"Invalid committed pressure clock");
  Require(!file.Get_Nout() && file.Get_Npok()==file.Get_CaseNp()
    && ids.size()==file.Get_CaseNfluid() && count==ids.size(),
    "Pressure history requires all fixed Cryer material owners");
  for(unsigned i=0;i<count;i++){
    Require(ids[i]==file.Get_CaseNfixed()+i && std::isfinite(previous[i]),
      "Invalid contiguous Cryer material ID or previous pressure");
  }
  JBinaryData& history=*part.CreateItem("TpiPressureHistory");
  history.SetvUint("Schema",1);
  history.SetvText("Scheme","P3_B_alpha_half_beta_zero");
  history.SetvText("RunCode",noRtimes? "00000000":file.Get_RunCode());
  history.SetvUint("CompletedUpdates",unsigned(commits));
  history.SetvDouble("PreviousTime",previousTime);
  history.SetvDouble("SavedTime",savedTime);
  history.SetvDouble("Dt",dt);
  history.SetvBool("Valid",true);
  history.CreateArray("Idp",JBinaryDataDef::DatUint,count,ids.data(),false);
  history.CreateArray("PorePressPrev",JBinaryDataDef::DatFloat,count,previous,false);
}
}
