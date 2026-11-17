//HEAD_DSPH
/*
 <DUALSPHYSICS> Copyright (c) 2020 by Dr Jose M. Dominguez et al.
 This file is part of DualSPHysics, distributed under the GNU Lesser General
 Public License, version 2.1 or (at your option) any later version.
*/

/// \file JSphHourglassGpu.h \brief Native-ID elastic GPU hourglass history.
#ifndef _JSphHourglassGpu_
#define _JSphHourglassGpu_

#include "JObjectGpu.h"
#include "JSphHourglassCpu.h"
#include "JSphHourglassGpu_ker.h"

/// Same small-rotation elastic law and four stages as JSphHourglassCpu.
/// Persistent double histories belong to native IDs, never periodic copies.
class JSphHourglassGpu : protected JObjectGpu{
public:
  using StRateInfo=JSphHourglassCpu::StRateInfo;
  using StStats=JSphHourglassCpu::StStats;
private:
  enum TpPhase{PH_Unconfigured,PH_PredictorForce,PH_PredictorUpdate,
    PH_CorrectorForce,PH_CorrectorUpdate};
  unsigned FirstId=0,Count=0,PairCount=0,CellCapacity=0,PartialCount=0;
  double Xi=0,Mass=0,Period=0,KernelH=0,Support=0,Bwen=0,Shear=0;
  double StepDt=0,PredictorSkew=0;
  TpPhase Phase=PH_Unconfigured;
  bool EndpointRateReady=false,RateCacheEnabled=true;
  cuhg::StNode* Nodesg=NULL;
  double2 *Historyg=NULL,*HistoryRateg=NULL;
  unsigned *Slotsg=NULL,*Keysg=NULL,*Orderg=NULL,*Errorg=NULL;
  int2* Rangesg=NULL;
  cuhg::StReduce *Partialg=NULL,*Resultg=NULL;
  StRateInfo RateInfo;
  StStats Stats;

  void Check(bool okay,const char* message)const;
  void CheckCuda(cudaError_t error)const;
  void FreeMemory();
  unsigned Index(unsigned id)const;
  cuhg::StReduce ReadResult()const;
  void CheckState(unsigned errors)const;
  void MapNative(unsigned np,unsigned npb,const unsigned* idp,const typecode* code);
  void EvaluateRate(bool endpoint,unsigned np,unsigned npb,const unsigned* idp,
    const typecode* code,const double2* posxy,const double* posz,
    const float4* velrhop,const float* kplastic);
  void AddHistory(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,float3* ace);
  void UpdateHistory(double dt);
public:
  JSphHourglassGpu();
  ~JSphHourglassGpu();
  JSphHourglassGpu(const JSphHourglassGpu&)=delete;
  JSphHourglassGpu& operator=(const JSphHourglassGpu&)=delete;
  void Config(unsigned firstid,unsigned count,double xi,double mass,double period,
    double kernelh,double support,double bwen,double shear);
  void PredictorForce(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,
    const double2* posxy,const double* posz,const float4* velrhop,const float* kplastic,float3* ace,double dt);
  void PredictorUpdate(double dt);
  void CorrectorForce(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,float3* ace);
  void CorrectorUpdate(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,
    const double2* posxy,const double* posz,const float4* velrhop,const float* kplastic,double dt);
  llong GetAllocMemory()const;
  double GetDtLimit()const;
  unsigned GetFirstId()const{ return(FirstId); }
  unsigned GetCount()const{ return(Count); }
  unsigned GetPairCount()const{ return(PairCount); }
  const StStats& GetStats()const{ return(Stats); }
  const StRateInfo& GetRateInfo()const{ return(RateInfo); }
  tdouble3 GetHistory(unsigned id)const;
  tdouble3 GetRate(unsigned id)const;
  /// Internal fixture control only; no XML option or alternative physical law.
  void SetRateCacheEnabled(bool enabled){ RateCacheEnabled=enabled;EndpointRateReady=false; }
};
#endif
