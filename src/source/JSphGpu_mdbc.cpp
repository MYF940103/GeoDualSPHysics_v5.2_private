//HEAD_DSPH
/*
 <DUALSPHYSICS>  Copyright (c) 2020 by Dr Jose M. Dominguez et al. (see http://dual.sphysics.org/index.php/developers/). 

 EPHYSLAB Environmental Physics Laboratory, Universidade de Vigo, Ourense, Spain.
 School of Mechanical, Aerospace and Civil Engineering, University of Manchester, Manchester, U.K.

 This file is part of DualSPHysics. 

 DualSPHysics is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License 
 as published by the Free Software Foundation; either version 2.1 of the License, or (at your option) any later version.
 
 DualSPHysics is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more details. 

 You should have received a copy of the GNU Lesser General Public License along with DualSPHysics. If not, see <http://www.gnu.org/licenses/>. 
*/

/// \file JSphGpu_mdbc.cpp \brief GPU mDBC host reconstruction and SPR initialization.

#include "JSphGpu.h"
#include "JSphGpu_ker.h"
#include "FunctionsCuda.h"
#include "JArraysGpu.h"
#include "JSphMk.h"
#include <cfloat>
#include <cmath>
#include <map>

//==============================================================================
/// Initializes the existing fixed-plane SPR geometry at its original startup stage.
//==============================================================================
void JSphGpu::InitBoundaryDerivativeGpu(const tfloat3 *boundnormal){
  if(SoilBoundaryDerivativeSPR){
    //-Each wall mk defines one stationary plane; never average corner normals.
    if(!Npb)Run_Exceptioon("SoilBoundaryDerivativeSPR requires fixed boundary planes.");
    std::map<word,unsigned> wallplanes;
    const double normaltol=8.*FLT_EPSILON; //-Float-normal direction roundoff, not a fitted geometry tolerance.
    for(unsigned p=0;p<Npb;p++){
      const word mk=MkInfo->GetMkByCode(Code[p]);
      const unsigned p0=wallplanes.insert(std::make_pair(mk,p)).first->second;
      const tdouble3 n0=ToTDouble3(boundnormal[p0]);
      const double len0=sqrt(n0.x*n0.x+n0.y*n0.y+n0.z*n0.z);
      if(!std::isfinite(len0) || len0<=0)
        Run_Exceptioon("SoilBoundaryDerivativeSPR requires finite nonzero boundary normals.");
      const tdouble3 unit0=n0/len0,wall0=AuxPos[p0]+n0*.5;
      const bool legacyhorizontal=(n0.z>0 && fabs(n0.x)<=1e-8*Dp && fabs(n0.y)<=1e-8*Dp);
      const tdouble3 n=ToTDouble3(boundnormal[p]),wall=AuxPos[p]+n*.5;
      const double len=sqrt(n.x*n.x+n.y*n.y+n.z*n.z);
      if(!CODE_IsFixed(Code[p]) || !std::isfinite(len) || len<=0
        || !std::isfinite(wall.x) || !std::isfinite(wall.y) || !std::isfinite(wall.z)
        || Velrhop[p].x!=0 || Velrhop[p].y!=0 || Velrhop[p].z!=0)
        Run_Exceptioon("SoilBoundaryDerivativeSPR requires finite stationary fixed-wall particles and nonzero normals.");
      if(NoPenetration){
        const tdouble3 unit=n/len;
        const unsigned components=unsigned(fabs(unit.x)>normaltol)+unsigned(fabs(unit.y)>normaltol)+unsigned(fabs(unit.z)>normaltol);
        if(components!=1)Run_Exceptioon("SPR with existing NoPen requires axis-aligned wall normals; inclined NoPen is not rotation-consistent.");
      }
      if(legacyhorizontal){
        //-Keep the original case-02 direction and coplanarity thresholds unchanged.
        if(n.z<=0 || fabs(n.x)>1e-8*Dp || fabs(n.y)>1e-8*Dp || fabs(wall.z-wall0.z)>1e-6*Dp)
          Run_Exceptioon("SoilBoundaryDerivativeSPR requires stationary coplanar horizontal bottom-wall normals within each wall mk.");
      }
      else{
        const tdouble3 unit=n/len,delta=wall-wall0;
        //-A float normal affects both the wall midpoint and its projection over the plane span.
        const double planetol=1e-6*Dp+normaltol*(len0+len+sqrt(delta.x*delta.x+delta.y*delta.y+delta.z*delta.z));
        if(fabs(unit.x-unit0.x)>normaltol || fabs(unit.y-unit0.y)>normaltol || fabs(unit.z-unit0.z)>normaltol
          || (Simulate2D && fabs(unit.y)>normaltol)
          || fabs(delta.x*unit0.x+delta.y*unit0.y+delta.z*unit0.z)>planetol)
          Run_Exceptioon("SoilBoundaryDerivativeSPR requires one coplanar, consistently oriented fixed wall per mk (x-z plane normals in 2-D).");
      }
    }
    const tdouble3 perinc[3]={PeriXinc,PeriYinc,PeriZinc};
    const bool peractive[3]={PeriX,PeriY,PeriZ};
    for(const auto &plane:wallplanes)for(unsigned a=0;a<3;a++)if(peractive[a]){
      const tdouble3 n=ToTDouble3(boundnormal[plane.second]);
      const tdouble3 unit=n/sqrt(n.x*n.x+n.y*n.y+n.z*n.z);
      const tdouble3 inc=perinc[a];
      const double len=sqrt(inc.x*inc.x+inc.y*inc.y+inc.z*inc.z);
      if(!std::isfinite(len) || len<=0 || fabs(inc.x*unit.x+inc.y*unit.y+inc.z*unit.z)>normaltol*len)
        Run_Exceptioon("SoilBoundaryDerivativeSPR permits periodic translations tangent to every wall plane only.");
    }
    if(wallplanes.size()>1){
      std::vector<tdouble4> planes;
      for(const auto &plane:wallplanes){
        const unsigned p=plane.second;
        const tdouble3 raw=ToTDouble3(boundnormal[p]);
        const tdouble3 n=raw/sqrt(raw.x*raw.x+raw.y*raw.y+raw.z*raw.z),wall=AuxPos[p]+raw*.5;
        planes.push_back(TDouble4(n.x,n.y,n.z,-(n.x*wall.x+n.y*wall.y+n.z*wall.z)));
      }
      std::vector<tdouble3> fitshift(CaseNpb,TDouble3(0));
      for(unsigned p=0;p<Npb;p++){
        const tdouble3 target=AuxPos[p]+ToTDouble3(boundnormal[p]);
        bool outside=false;
        for(const auto &a:planes)outside=outside || (a.x*target.x+a.y*target.y+a.z*target.z+a.w < -1e-6*Dp);
        if(!outside)continue;
        tdouble3 centre=target;
        //-Static convex half-space projection; leave one dp of interior MLS support.
        for(unsigned iteration=0;iteration<128;iteration++){
          double residual=0;
          for(const auto &a:planes){
            const double gap=Dp-(a.x*centre.x+a.y*centre.y+a.z*centre.z+a.w);
            if(gap>0){centre=centre+TDouble3(a.x,a.y,a.z)*gap;residual=(std::max)(residual,gap);}
          }
          if(residual<=1e-6*Dp)break;
          if(iteration==127)Run_Exceptioon("SPR fixed wall planes do not admit a common interior MLS centre with one-dp clearance.");
        }
        fitshift[Idp[p]]=centre-target;
      }
      static_assert(sizeof(tdouble3)==sizeof(double3),"CPU/GPU MLS offset layouts differ");
      const size_t bytes=sizeof(double3)*CaseNpb;
      cudaMalloc((void**)&BoundDerivativeFitShiftg,bytes); MemGpuFixed+=bytes;
      cudaMemcpy(BoundDerivativeFitShiftg,fitshift.data(),bytes,cudaMemcpyHostToDevice);
      Check_CudaErroor("Failed in fixed SPR MLS offset upload.");
    }
    Log->Printf("SPR stationary wall planes (one per mk): %u",unsigned(wallplanes.size()));
  }
}

//==============================================================================
/// Extrapolates pore pressure to mDBC boundary particles.
//==============================================================================
void JSphGpu::InteractionPorePressureMdbcCorrection(){
  if(!HydroMech || !PorePressg || !PorePress0g || !UseNormals || !BoundNormalg || !DivData.beginendcell)return;
  const unsigned n=(UseNormalsFt? Np: NpbOk);
  cusph::PorePressureMdbcCorrection(TKernel,Simulate2D,n,MdbcThreshold,DivData,Map_PosMin
    ,Posxyg,Poszg,PosCellg,Codeg,Velrhopg,BoundNormalg,PorePress0g,PorePressg);
  Check_CudaErroor("Failed in pore-pressure mDBC correction.");
}

//==============================================================================
/// Reconstructs derivative-only wall velocity after each stage's mDBC update.
//==============================================================================
void JSphGpu::ComputeBoundaryDerivativeVelocity(){
  //-The same-stage single-J wall closure already owns the derivative velocity.
  if(DynamicPoreWall)return;
  if(SoilBoundaryDerivativeSPR)cusph::BoundaryDerivativeVelocity(Simulate2D,Npb,NpbOk,
    MdbcThreshold,SlipMode,DivData,Posxyg,Poszg,Codeg,Velrhopg,BoundNormalg,
    BoundModeg,BoundSlipModeg,BoundDerivativeVelg,Idpg,BoundDerivativeFitShiftg);
}

//==============================================================================
/// Validates private static walls and strictly tangential gravity before host arrays are freed.
//==============================================================================
void JSphGpu::InitDynamicPoreWallGpu(const tfloat3 *boundnormal,const byte *boundslipmode){
  if(!DynamicPoreWall)return;
  const bool loadedcolumn=(DynamicPorePressure && Simulate2D && DynamicPoreWall
    && !DynamicPoreConductivity && !Gravity.x && !Gravity.y && !Gravity.z
    && HydroMechInitMode==HMINIT_None && HydroMechTopLoadMode==HMLOAD_TopKernelBand
    && HydroMechDrainage && HydroMechDrainageFixedGrid);
  const bool allowcolumnspr=(HydroMechDynamicSeepage && PorosityFeedback && loadedcolumn
    && PeriX && !PeriY && !PeriZ && !ViscoTime);
  if(!DynamicPorePressure || !PorosityFeedback || !Simulate2D || !CaseNpb
    || TBoundary!=BC_MDBC || !UseNormals || !boundnormal
    || !std::isfinite(Gravity.x) || !std::isfinite(Gravity.y) || !std::isfinite(Gravity.z) || Gravity.y!=0
    || (SoilBoundaryDerivativeSPR && !allowcolumnspr) || CaseNmoving || CaseNfloat
    || !std::isfinite(MassBound) || !(MassBound>0) || !std::isfinite(MassFluid) || !(MassFluid>0)
    || fabs(double(MassBound)-MassFluid)>4.*FLT_EPSILON*double(MassFluid))
    Run_Exceptioon("GPU dynamic wall requires equal-dp fixed mDBC FreeSlip planes, finite tangential gravity and its own derivative closure.");
  if(IsDynamicPoreContainerConfig()){
    CheckDynamicPoreContainer(Np,Npb,AuxPos,Code,Velrhop,boundnormal,boundslipmode,Idp);
    return;
  }
  const auto component=[](const tdouble3 &v,int a){return(a==0? v.x: (a==1? v.y: v.z));};
  const bool hasgravity=(Gravity.x!=0 || Gravity.y!=0 || Gravity.z!=0);
  int axis=-1;bool seen[2]={false,false};double plane[2]={0,0};
  for(unsigned p=0;p<Npb;p++){
    const tdouble3 raw=ToTDouble3(boundnormal[p]);
    const double len=sqrt(raw.x*raw.x+raw.y*raw.y+raw.z*raw.z);
    if(!CODE_IsFixed(Code[p]) || !std::isfinite(len) || len<=0
      || Velrhop[p].x || Velrhop[p].y || Velrhop[p].z
      || (boundslipmode? TpSlipMode(boundslipmode[p]): SlipMode)!=SLIP_FreeSlip)
      Run_Exceptioon("GPU dynamic wall requires finite stationary FreeSlip wall normals.");
    const tdouble3 n=raw/len,wall=AuxPos[p]+raw*.5;
    const int a=(fabs(n.x)>.5? 0: (fabs(n.y)>.5? 1: 2));
    if(axis<0)axis=a;
    if(a!=axis || a==1)Run_Exceptioon("GPU dynamic wall permits parallel x/z axis planes only, without corners.");
    for(int b=0;b<3;b++)if(b!=axis && fabs(component(n,b))>8.*FLT_EPSILON)
      Run_Exceptioon("GPU dynamic wall rejects inclined normals.");
    if(hasgravity && (component(ToTDouble3(Gravity),axis)!=0 || Gravity.x*raw.x+Gravity.y*raw.y+Gravity.z*raw.z!=0))
      Run_Exceptioon("GPU dynamic wall requires gravity exactly tangent to every wall mirror vector.");
    const unsigned side=(component(n,axis)>0? 0: 1);
    const double xp=component(wall,axis);
    if(!std::isfinite(xp) || (seen[side] && fabs(xp-plane[side])>1e-6*Dp))
      Run_Exceptioon("GPU dynamic wall requires one coplanar face per inward normal direction.");
    if(!seen[side])plane[side]=xp;
    seen[side]=true;
  }
  if(seen[0] && seen[1] && plane[1]-plane[0]<=2.*double(KernelSize))
    Run_Exceptioon("GPU dynamic wall requires separated opposing mirror supports.");
  if(!loadedcolumn && (!seen[0] || !seen[1] || PeriY || (axis==0? (!PeriZ || PeriX): (!PeriX || PeriZ))))
    Run_Exceptioon("GPU dynamic wall requires separated opposing axis planes and tangential periodicity.");
  if(loadedcolumn && (axis!=2 || !seen[0] || seen[1] || !PeriX || PeriY || PeriZ))
    Run_Exceptioon("GPU dynamic consolidation requires one upward bottom plane and horizontal X periodicity.");
  const tdouble3 inc[3]={PeriXinc,PeriYinc,PeriZinc};const bool periodic[3]={PeriX,PeriY,PeriZ};
  for(int a=0;a<3;a++)if(periodic[a]){
    for(int b=0;b<3;b++)if(!std::isfinite(component(inc[a],b)) || (b!=a && component(inc[a],b)!=0))
      Run_Exceptioon("GPU dynamic wall permits finite axis-aligned tangential periodic translations only.");
    if(component(inc[a],a)==0)Run_Exceptioon("GPU dynamic wall periodic length must be nonzero.");
  }
  for(unsigned p=0;p<Npb;p++){
    const double xm=component(AuxPos[p]+ToTDouble3(boundnormal[p]),axis);
    if(!std::isfinite(xm) || (seen[0] && xm<=plane[0]) || (seen[1] && xm>=plane[1]))
      Run_Exceptioon("GPU dynamic wall mirror sample must lie strictly inside the fluid slab.");
  }
}

//==============================================================================
/// Reconstructs active fixed samples. A borrowed invalid flag is owned by the rate caller.
//==============================================================================
void JSphGpu::ComputeDynamicPoreWallGpu(unsigned stage,unsigned *invalidg){
  if(!DynamicPoreWall || !NpbOk)return;
  if(stage>2 || !Simulate2D || !BoundNormalg || !BoundModeg || !TangenVelg || (stage==2 && !Aceg))
    Run_Exceptioon("GPU dynamic wall requires its bounded 2-D mirror state and mDBC arrays.");
  const bool owned=(invalidg==NULL);unsigned invalid=Np;
  try{
    if(owned){invalidg=ArraysGpu->ReserveUint();cudaMemcpy(invalidg,&invalid,sizeof(unsigned),cudaMemcpyHostToDevice);}
    cusph::DynamicPoreWall(stage,Np,NpbOk,MdbcThreshold,DivData,Posxyg,Poszg,Codeg,BoundNormalg
      ,BoundModeg,TangenVelg,BoundDerivativeVelg,Velrhopg,Sigmag,PorePressg,PoroJg,PoroThetag,CorrMatg,Aceg
      ,1.-double(SoilCte.Porosity),invalidg,TKernel,BoundSlipModeg,(Simulate2D && !PeriActive? PosCellg: NULL));
    if(owned)cudaMemcpy(&invalid,invalidg,sizeof(unsigned),cudaMemcpyDeviceToHost);
  }
  catch(...){if(owned && invalidg)ArraysGpu->Free(invalidg);throw;}
  if(owned){
    ArraysGpu->Free(invalidg);
    Check_CudaErroor("Failed reconstructing GPU dynamic wall samples.");
    if(invalid<Np)Run_Exceptioon("GPU dynamic wall requires a finite saturated first-order mirror fit at every active sample.");
  }
}
void JSphGpu::ComputeDynamicPoreWallStateGpu(){ComputeDynamicPoreWallGpu(0);}
void JSphGpu::ComputeDynamicPoreWallMatrixGpu(){ComputeDynamicPoreWallGpu(1);}
void JSphGpu::ComputeDynamicPoreWallAccelerationGpu(unsigned *invalidg){ComputeDynamicPoreWallGpu(2,invalidg);}

//==============================================================================
/// Rejects NoWall markers entering any existing fluid interaction support.
//==============================================================================
void JSphGpu::CheckHydroMechNoWallSupportGpu(){
  if(!HydroMechNoWall)Run_Exceptioon("Hydromechanical no-wall support check requires HydroMechNoWall.");
  if(!NpbOk || DynamicPoreFreeBody)return;
  unsigned invalid=NpbOk;
  unsigned *invalidg=NULL;
  try{
    invalidg=ArraysGpu->ReserveUint();
    cudaMemcpy(invalidg,&invalid,sizeof(unsigned),cudaMemcpyHostToDevice);
    cusph::CheckHydroMechNoWallSupport(NpbOk,DivData,Posxyg,Poszg,PosCellg,Codeg,invalidg);
    cudaMemcpy(&invalid,invalidg,sizeof(unsigned),cudaMemcpyDeviceToHost);
    Check_CudaErroor("Failed checking hydromechanical NoWall marker support.");
  }
  catch(...){if(invalidg)ArraysGpu->Free(invalidg);throw;}
  ArraysGpu->Free(invalidg);
  if(invalid<NpbOk)Run_Exceptioon("A hydromechanical NoWall marker enters fluid interaction support.");
}

