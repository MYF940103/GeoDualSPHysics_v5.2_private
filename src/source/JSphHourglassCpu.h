//HEAD_DSPH
/*
 <DUALSPHYSICS> Copyright (c) 2020 by Dr Jose M. Dominguez et al.
 This file is part of DualSPHysics, distributed under the GNU Lesser General
 Public License, version 2.1 or (at your option) any later version.
*/

/// \file JSphHourglassCpu.h \brief Elastic CPU hourglass history for small rotations.

#ifndef _JSphHourglassCpu_
#define _JSphHourglassCpu_

#include "DualSphDef.h"
#include "JObject.h"
#include <vector>

//##############################################################################
//# JSphHourglassCpu
//##############################################################################
/// Soil-only, matched-LS elastic HG term. History is indexed by native ID, not
/// by sorted particle slot; periodic copies never carry independent history.
/// The caller restricts use to 2D Wendland, bounded or axis-aligned X-periodic, fixed
/// native particles and fresh runs. Bare vector history is not finite-rotation
/// objective. The endpoint-trapezoidal update does not prove coupled stability.
class JSphHourglassCpu : protected JObject{
public:
  struct StRateInfo{
    double netx=0,netz=0;
    double condition=0,skew=0,form=0,lambda=0,tau=0;
    double ratepower=0,workerror=0,rmax=0,sumrate=0;
    double meandxx=0,rmsdxx=0,meandiv=0,rmsdiv=0;
  };
  struct StStats{
    unsigned forcecalls=0,predictorupdates=0,correctorupdates=0;
    unsigned ratecalls=0,predictorrates=0,endpointrates=0;
    unsigned firstpairs=0,minpairs=0,maxpairs=0;
    double maxnetforce=0,maxactualnetforce=0,maxnetrate=0;
    double maxrelativeforce=0,maxrelativerate=0,maxhistory=0;
    double maxcondition=0,maxpoweridentityerror=0,maxskew=0,spinbound=0;
    double maxtauratio=0,mintau=0,maxlambda=0;
    unsigned ratecalculations=0,ratecachehits=0; ///<Actual calculations vs reused endpoint rates; ratecalls remains logical.
  };

private:
  struct Vec{double x=0,z=0;};
  struct Node{
    double x=0,z=0,vx=0,vz=0,vol=0;
    double mxx=0,mxz=0,mzz=0,nxx=0,nxz=0,nzx=0,nzz=0;
    double lxx=0,lxz=0,lzx=0,lzz=0,betasum=0;
  };
  struct Pair{unsigned i,j;double x,z,w;};
  enum TpPhase{PH_Unconfigured,PH_PredictorForce,PH_PredictorUpdate,
    PH_CorrectorForce,PH_CorrectorUpdate};

  unsigned FirstId=0,Count=0;
  double Xi=0,Mass=0,Period=0,KernelH=0,Support=0,Bwen=0,Shear=0; ///<Period=0 uses real bounded neighbors.
  double StepDt=0,PredictorSkew=0;
  TpPhase Phase=PH_Unconfigured;
  bool EndpointRateReady=false;
  std::vector<Node> Nodes;
  std::vector<byte> RateSeen;
  std::vector<Vec> History,HistoryRate;
  std::vector<Pair> Pairs;
  std::vector<int> Heads,Next;
  StRateInfo RateInfo;
  StStats Stats;

  void Check(bool okay,const char* message)const;
  unsigned Index(unsigned id)const;
  double MinImage(double dx)const;
  void BuildPairs(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,
    const tdouble3* pos,const tfloat4* velrhop,const float* kplastic);
  void Rate();
  bool SameRateState(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,
    const tdouble3* pos,const tfloat4* velrhop,const float* kplastic);
  void EvaluateRate(bool endpoint,unsigned np,unsigned npb,const unsigned* idp,
    const typecode* code,const tdouble3* pos,const tfloat4* velrhop,const float* kplastic);
  void AddHistory(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,tfloat3* ace);
  void UpdateHistory(double dt);

public:
  JSphHourglassCpu();
  void Config(unsigned firstid,unsigned count,double xi,double mass,double period,
    double kernelh,double support,double bwen,double shear);
  void PredictorForce(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,
    const tdouble3* pos,const tfloat4* velrhop,const float* kplastic,tfloat3* ace,double dt);
  void PredictorUpdate(double dt);
  void CorrectorForce(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,tfloat3* ace);
  void CorrectorUpdate(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,
    const tdouble3* pos,const tfloat4* velrhop,const float* kplastic,double dt);

  llong GetAllocMemory()const;
  double GetDtLimit()const;
  unsigned GetFirstId()const{ return(FirstId); }
  unsigned GetCount()const{ return(Count); }
  unsigned GetPairCount()const{ return(unsigned(Pairs.size())); }
  const StStats& GetStats()const{ return(Stats); }
  const StRateInfo& GetRateInfo()const{ return(RateInfo); }
  tdouble3 GetHistory(unsigned id)const;
  tdouble3 GetRate(unsigned id)const;
};

#endif
