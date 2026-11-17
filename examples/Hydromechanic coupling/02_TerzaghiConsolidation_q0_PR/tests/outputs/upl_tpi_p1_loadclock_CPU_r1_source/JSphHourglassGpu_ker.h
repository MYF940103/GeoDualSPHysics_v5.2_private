//HEAD_DSPH
/*
 <DUALSPHYSICS> Copyright (c) 2020 by Dr Jose M. Dominguez et al.
 This file is part of DualSPHysics, distributed under the GNU Lesser General
 Public License, version 2.1 or (at your option) any later version.
*/
/// \file JSphHourglassGpu_ker.h \brief Device operations for elastic HG history.
#ifndef _JSphHourglassGpu_ker_
#define _JSphHourglassGpu_ker_
#include "DualSphDef.h"
#include <cuda_runtime_api.h>

namespace cuhg{
enum TpError{ERR_Id=1,ERR_Duplicate=2,ERR_Missing=4,ERR_Density=8,
  ERR_Plastic=16,ERR_State=32,ERR_Coincident=64,ERR_Rank=128,
  ERR_Rate=256,ERR_History=512};
struct StNode{
  double x,z,vx,vz,vol;
  double lxx,lxz,lzx,lzz,condition,skew;
};
struct StGrid{
  unsigned nx,nz;
  double cellx,zmin,period,support,h,bwen,xi,mass,shear,xmin; ///<period=0: bounded X cells.
};
// Small fixed-tree reduction packet. Fields retain CPU sum/square-sum meaning.
struct StReduce{
  double zmin,zmax,netx,netz,actualx,actualz,sumforce,hmax;
  double condition,skew,form,lambda,ratepower,rmax,sumrate;
  double meandxx,rmsdxx,meandiv,rmsdiv;
  unsigned errors,changed,pairs;
  double xmin,xmax;
};
inline unsigned PartialCount(unsigned n){ return(n/128+(n%128!=0)); }
void MapNative(unsigned np,unsigned npb,unsigned firstid,unsigned count,
  const unsigned* idp,const typecode* code,unsigned* slots,unsigned* errors);
void Gather(unsigned count,double mass,const unsigned* slots,const unsigned* errors,
  const double2* posxy,const double* posz,const float4* velrhop,const float* kplastic,
  StNode* nodes,StReduce* partial);
void CellKeys(unsigned count,StGrid grid,const StNode* nodes,unsigned* keys,unsigned* order);
void Moments(unsigned count,StGrid grid,const unsigned* order,const int2* ranges,
  StNode* nodes,unsigned* errors);
void Rates(unsigned count,StGrid grid,const unsigned* order,const int2* ranges,
  const StNode* nodes,const unsigned* errors,double2* rates,StReduce* partial);
void AddHistory(unsigned count,double mass,const unsigned* slots,const unsigned* errors,
  const double2* history,float3* ace,StReduce* partial);
void UpdateHistory(unsigned count,double dt,const double2* rates,double2* history,StReduce* partial);
void Reduce(unsigned count,const StReduce* partial,StReduce* result);
}
#endif
