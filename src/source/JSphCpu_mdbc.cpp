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

/// \file JSphCpu_mdbc.cpp \brief CPU boundary MLS, mDBC/cDBC and dynamic-wall reconstruction.

#include "JSphCpu.h"
#include "JCellSearch_inline.h"
#include "FunSphKernel.h"
#include "FunctionsMath.h"
#include "JSphMk.h"

#include <cfloat>
#include <cmath>
#include <map>

using namespace std;

//==============================================================================
/// Rejects contact between inactive fixed markers and actual hydromechanical soil support.
//==============================================================================
void JSphCpu::CheckHydroMechNoWallSupportCpu(){
  if(!HydroMechNoWall)Run_Exceptioon("Hydromechanical no-wall support check requires HydroMechNoWall.");
  if(!NpbOk || DynamicPoreFreeBody)return;
  for(unsigned p1=0;p1<NpbOk;p1++)if(CODE_IsNormal(Codec[p1]) && CODE_IsFixed(Codec[p1])){
    const StNgSearch ngs=nsearch::Init(Posc[p1],false,DivData);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 range=nsearch::ParticleRange(y,z,ngs,DivData);
      for(unsigned p2=range.x;p2<range.y;p2++)if(CODE_IsFluid(Codec[p2])){
        const double drx=Posc[p1].x-Posc[p2].x,dry=Posc[p1].y-Posc[p2].y,drz=Posc[p1].z-Posc[p2].z;
        const double rr2=drx*drx+dry*dry+drz*drz;
        const float fx=float(drx),fy=float(dry),fz=float(drz);
        const float forcerr2=fx*fx+fy*fy+fz*fz;
        if(rr2<=double(KernelSize2) || forcerr2<=KernelSize2)
          Run_Exceptioon("HydroMech with cDBC does not support fixed markers inside fluid kernel support; use mDBC for hydromechanical walls.");
      }
    }
  }
}

//==============================================================================
/// Initializes fixed-plane derivative reconstruction at the original domain-configuration stage.
//==============================================================================
void JSphCpu::InitBoundaryDerivativeCpu(){
  if(SoilBoundaryDerivativeSPR){
    //-Each wall mk defines one stationary plane; never average corner normals.
    if(!Npb)Run_Exceptioon("SoilBoundaryDerivativeSPR requires fixed boundary planes.");
    std::map<word,unsigned> wallplanes;
    const double normaltol=8.*FLT_EPSILON; //-Float-normal direction roundoff, not a fitted geometry tolerance.
    for(unsigned p=0;p<Npb;p++){
      const word mk=MkInfo->GetMkByCode(Codec[p]);
      const unsigned p0=wallplanes.insert(std::make_pair(mk,p)).first->second;
      const tdouble3 n0=ToTDouble3(BoundNormalc[p0]);
      const double len0=sqrt(n0.x*n0.x+n0.y*n0.y+n0.z*n0.z);
      if(!std::isfinite(len0) || len0<=0)
        Run_Exceptioon("SoilBoundaryDerivativeSPR requires finite nonzero boundary normals.");
      const tdouble3 unit0=n0/len0,wall0=Posc[p0]+n0*.5;
      const bool legacyhorizontal=(n0.z>0 && fabs(n0.x)<=1e-8*Dp && fabs(n0.y)<=1e-8*Dp);
      const tdouble3 n=ToTDouble3(BoundNormalc[p]),wall=Posc[p]+n*.5;
      const double len=sqrt(n.x*n.x+n.y*n.y+n.z*n.z);
      if(!CODE_IsFixed(Codec[p]) || !std::isfinite(len) || len<=0
        || !std::isfinite(wall.x) || !std::isfinite(wall.y) || !std::isfinite(wall.z)
        || Velrhopc[p].x!=0 || Velrhopc[p].y!=0 || Velrhopc[p].z!=0)
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
      const tdouble3 n=ToTDouble3(BoundNormalc[plane.second]);
      const tdouble3 unit=n/sqrt(n.x*n.x+n.y*n.y+n.z*n.z);
      const tdouble3 inc=perinc[a];
      const double len=sqrt(inc.x*inc.x+inc.y*inc.y+inc.z*inc.z);
      if(!std::isfinite(len) || len<=0 || fabs(inc.x*unit.x+inc.y*unit.y+inc.z*unit.z)>normaltol*len)
        Run_Exceptioon("SoilBoundaryDerivativeSPR permits periodic translations tangent to every wall plane only.");
    }
    BoundDerivativeFitShift.clear();
    if(wallplanes.size()>1){
      std::vector<tdouble4> planes;
      for(const auto &plane:wallplanes){
        const unsigned p=plane.second;
        const tdouble3 raw=ToTDouble3(BoundNormalc[p]);
        const tdouble3 n=raw/sqrt(raw.x*raw.x+raw.y*raw.y+raw.z*raw.z),wall=Posc[p]+raw*.5;
        planes.push_back(TDouble4(n.x,n.y,n.z,-(n.x*wall.x+n.y*wall.y+n.z*wall.z)));
      }
      BoundDerivativeFitShift.resize(CaseNpb,TDouble3(0));
      for(unsigned p=0;p<Npb;p++){
        const tdouble3 target=Posc[p]+ToTDouble3(BoundNormalc[p]);
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
        BoundDerivativeFitShift[Idpc[p]]=centre-target;
      }
    }
    Log->Printf("SPR stationary wall planes (one per mk): %u",unsigned(wallplanes.size()));
  }
}

//==============================================================================
/// Interpolates field components at boundary ghost points using one MLS matrix.
/// Writer receives physical gradients (null for 0th order), reusing fitted RHS storage.
//==============================================================================
template<TpKernel tker,bool sim2d,unsigned ncomp,class TRead,class TWrite> void JSphCpu::InterpolateBoundaryGhostFieldT
  (unsigned n,StDivDataCpu divdata,const tdouble3 *pos,const typecode *code
  ,const tfloat4 *velrhop,const tfloat3 *boundnormal,const TRead &read,const TWrite &write,bool recenter)const
{
  const int nn=int(n);
  const bool feedbackj=(PorosityFeedback && DynamicPoreWall);
  unsigned missing=0;
  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided) reduction(+:missing)
  #endif
  for(int p1=0;p1<nn;p1++){
    if(CODE_IsFluid(code[p1]) || boundnormal[p1]==TFloat3(0))continue;
    if(DynamicPoreWall && sim2d && !PeriActive && BoundModec[p1]==BMODE_MDBC2OFF)continue;
    tdouble3 gposp1=pos[p1]+ToTDouble3(boundnormal[p1]);
    tdouble3 fitshift=(recenter && !BoundDerivativeFitShift.empty()? BoundDerivativeFitShift[Idpc[p1]]: TDouble3(0));
    bool shifted=(fitshift!=TDouble3(0));
    if(shifted)gposp1=gposp1+fitshift;
    gposp1=(PeriActive!=0? UpdatePeriodicPos(gposp1): gposp1);
    bool retried=false,centroidretried=false;
    for(;;){ //-Keep primary/nearest fits; one final centroid retry for dynamic 2-D walls.
    double sumwab=0,submerged=0;
    bool invalidj=false;
    double fieldsum[ncomp]={0};
    double gradfieldx[ncomp]={0},gradfieldy[ncomp]={0},gradfieldz[ncomp]={0};
    double nearest[ncomp]={0},nearest2=DBL_MAX;
    tdouble3 neardr=TDouble3(0);
    tmatrix3d a_corr2=TMatrix3d(0);
    tmatrix4d a_corr3=TMatrix4d(0);
    const StNgSearch ngs=nsearch::Init(gposp1,false,divdata);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
      for(unsigned p2=pif.x;p2<pif.y;p2++)if(CODE_IsFluid(code[p2]) && (feedbackj || velrhop[p2].w>0)){
        const double drx=gposp1.x-pos[p2].x;
        const double dry=(sim2d? 0: gposp1.y-pos[p2].y);
        const double drz=gposp1.z-pos[p2].z;
        const float rr2=float(drx*drx+dry*dry+drz*drz);
        if(rr2<=KernelSize2){
          if(feedbackj && (!std::isfinite(PoroJc[p2]) || PoroJc[p2]<=1.-double(SoilCte.Porosity))){invalidj=true;continue;}
          float fac;
          //-A mirror sample can coincide with a fluid node: W(0) is finite and grad W(0)=0.
          const double wab=(DynamicPoreWall && rr2==0? (fac=0.f,double(fsph::GetKernel_Wab<tker>(CSP,rr2))): double(fsph::GetKernel_WabFac<tker>(CSP,rr2,fac)));
          const double frx=double(fac)*drx;
          const double fry=(sim2d? 0: double(fac)*dry);
          const double frz=double(fac)*drz;
          const double vol2=(DynamicPoreWall? double(MassFluid)/double(RhopZero)*PoroJc[p2]: double(MassFluid/velrhop[p2].w));
          const double vwab=wab*vol2;
          const double vfrx=frx*vol2;
          const double vfry=fry*vol2;
          const double vfrz=frz*vol2;
          double field[ncomp];
          for(unsigned c=0;c<ncomp;c++)field[c]=read(unsigned(p1),p2,c);
          const double distance2=drx*drx+dry*dry+drz*drz;
          if(DynamicPoreWall && distance2<nearest2){
            nearest2=distance2;neardr=TDouble3(drx,dry,drz);
            for(unsigned c=0;c<ncomp;c++)nearest[c]=field[c];
          }
          sumwab+=vwab;
          for(unsigned c=0;c<ncomp;c++){
            fieldsum[c]+=vwab*field[c];
            gradfieldx[c]+=vfrx*field[c];
            gradfieldy[c]+=vfry*field[c];
            gradfieldz[c]+=vfrz*field[c];
          }
          submerged-=vol2*(drx*frx+dry*fry+drz*frz);
          if(sim2d){
            a_corr2.a11+=vwab;  a_corr2.a12+=drx*vwab;  a_corr2.a13+=drz*vwab;
            a_corr2.a21+=vfrx;  a_corr2.a22+=drx*vfrx;  a_corr2.a23+=drz*vfrx;
            a_corr2.a31+=vfrz;  a_corr2.a32+=drx*vfrz;  a_corr2.a33+=drz*vfrz;
          }
          else{
            a_corr3.a11+=vwab;  a_corr3.a12+=drx*vwab;  a_corr3.a13+=dry*vwab;  a_corr3.a14+=drz*vwab;
            a_corr3.a21+=vfrx;  a_corr3.a22+=drx*vfrx;  a_corr3.a23+=dry*vfrx;  a_corr3.a24+=drz*vfrx;
            a_corr3.a31+=vfry;  a_corr3.a32+=drx*vfry;  a_corr3.a33+=dry*vfry;  a_corr3.a34+=drz*vfry;
            a_corr3.a41+=vfrz;  a_corr3.a42+=drx*vfrz;  a_corr3.a43+=dry*vfrz;  a_corr3.a44+=drz*vfrz;
          }
        }
      }
    }
    if(invalidj){missing++;break;} //-Invalid source state is not a geometry-retry candidate.
    const bool active=(submerged>0 || sumwab>=double(MdbcThreshold) || (MdbcThreshold>=2 && sumwab+2>=double(MdbcThreshold)));
    bool geometryfailed=false;
    if(active && sumwab>0){
      const double determlimit=1e-3;
      double fieldfinal[ncomp];
      bool firstorder=false;
      for(unsigned c=0;c<ncomp;c++)fieldfinal[c]=fieldsum[c]/sumwab; //-0th-order fallback.
      if(sim2d){
        const double determ=fmath::Determinant3x3(a_corr2);
        if(fabs(determ)>=determlimit){
          firstorder=true;
          const tmatrix3d inv=fmath::InverseMatrix3x3(a_corr2,determ);
          for(unsigned c=0;c<ncomp;c++){
            const double qg = inv.a11*fieldsum[c] + inv.a12*gradfieldx[c] + inv.a13*gradfieldz[c];
            fieldfinal[c]=qg;
            const double qx=inv.a21*fieldsum[c]+inv.a22*gradfieldx[c]+inv.a23*gradfieldz[c];
            const double qz=inv.a31*fieldsum[c]+inv.a32*gradfieldx[c]+inv.a33*gradfieldz[c];
            if(shifted || DynamicPoreWall){
              //-The fitted d=target-source coefficients are minus the physical gradient.
              //-Anchor to a native sample to avoid smoothing a coincident mirror node.
              if(DynamicPoreWall)fieldfinal[c]=nearest[c]-qx*neardr.x-qz*neardr.z;
              if(shifted)fieldfinal[c]+=qx*fitshift.x+qz*fitshift.z;
            }
            gradfieldx[c]=-qx;gradfieldy[c]=0.;gradfieldz[c]=-qz;
          }
        }
      }
      else{
        const double determ=fmath::Determinant4x4(a_corr3);
        if(fabs(determ)>=determlimit){
          firstorder=true;
          const tmatrix4d inv=fmath::InverseMatrix4x4(a_corr3,determ);
          for(unsigned c=0;c<ncomp;c++){
            const double qg = inv.a11*fieldsum[c] + inv.a12*gradfieldx[c] + inv.a13*gradfieldy[c] + inv.a14*gradfieldz[c];
            fieldfinal[c]=qg;
            const double qx=inv.a21*fieldsum[c]+inv.a22*gradfieldx[c]+inv.a23*gradfieldy[c]+inv.a24*gradfieldz[c];
            const double qy=inv.a31*fieldsum[c]+inv.a32*gradfieldx[c]+inv.a33*gradfieldy[c]+inv.a34*gradfieldz[c];
            const double qz=inv.a41*fieldsum[c]+inv.a42*gradfieldx[c]+inv.a43*gradfieldy[c]+inv.a44*gradfieldz[c];
            if(shifted || DynamicPoreWall){
              if(DynamicPoreWall)fieldfinal[c]=nearest[c]-qx*neardr.x-qy*neardr.y-qz*neardr.z;
              if(shifted)fieldfinal[c]+=qx*fitshift.x+qy*fitshift.y+qz*fitshift.z;
            }
            gradfieldx[c]=-qx;gradfieldy[c]=-qy;gradfieldz[c]=-qz;
          }
        }
      }
      bool finite=true;
      if(DynamicPoreWall)for(unsigned c=0;c<ncomp;c++)finite=finite && std::isfinite(fieldfinal[c]);
      if(DynamicPoreWall && (!firstorder || !finite)){
        if(!firstorder)geometryfailed=true;
        else missing++;
      }
      else write(p1,fieldfinal,firstorder? gradfieldx: nullptr,firstorder? gradfieldy: nullptr,firstorder? gradfieldz: nullptr);
    }
    else if(DynamicPoreWall)geometryfailed=true;
    if(geometryfailed){
      bool nearestfinite=std::isfinite(nearest2) && nearest2<DBL_MAX
        && std::isfinite(neardr.x) && std::isfinite(neardr.y) && std::isfinite(neardr.z);
      for(unsigned c=0;c<ncomp && nearestfinite;c++)nearestfinite=std::isfinite(nearest[c]);
      if(DynamicPoreWall && sim2d && !PeriActive && !retried && nearestfinite && neardr!=TDouble3(0)){
        //-Fit once at an existing real source, then return to the original mirror with q*fitshift.
        gposp1=gposp1-neardr;fitshift=fitshift-neardr;shifted=(fitshift!=TDouble3(0));
        retried=true;continue;
      }
      if(tker==KERNEL_Wendland && DynamicPoreWall && sim2d && !PeriActive && retried && !centroidretried && nearestfinite
        && std::isfinite(a_corr2.a11) && a_corr2.a11>0){
        //-Positive W*V first moments locate the donor centroid; still evaluate at the original mirror.
        const tdouble3 centroiddr=TDouble3(a_corr2.a12/a_corr2.a11,0.,a_corr2.a13/a_corr2.a11);
        const tdouble3 centre=gposp1-centroiddr;
        if(std::isfinite(centroiddr.x) && std::isfinite(centroiddr.z)
          && std::isfinite(centre.x) && std::isfinite(centre.z) && centre!=gposp1){
          gposp1=centre;fitshift=fitshift-centroiddr;shifted=(fitshift!=TDouble3(0));
          centroidretried=true;continue;
        }
      }
      missing++;
    }
    break;
    }
  }
  if(missing)Run_Exceptioon("Dynamic wall requires a finite first-order MLS fit at every active mirror sample.");
}

//==============================================================================
/// Extrapolates excess pore pressure to mDBC boundary particles for undrained walls.
//==============================================================================
template<TpKernel tker,bool sim2d> void JSphCpu::InteractionPorePressureMdbcCorrectionT
  (unsigned n,StDivDataCpu divdata,const tdouble3 *pos,const typecode *code
  ,const tfloat4 *velrhop,const tfloat3 *boundnormal,const float *porepress0,float *porepress)const
{
  const auto readpressure=[&](unsigned,unsigned p,unsigned){return(double(porepress[p])-double(porepress0[p]));};
  const auto writepressure=[&](unsigned p,const double *excess,const double*,const double*,const double*){porepress[p]=float(double(porepress0[p])+excess[0]);};
  InterpolateBoundaryGhostFieldT<tker,sim2d,1>(n,divdata,pos,code,velrhop,boundnormal,readpressure,writepressure);
}

//==============================================================================
/// Reconstructs derivative-only velocity at a fixed plane using its local slip mode.
//==============================================================================
void JSphCpu::ComputeBoundaryDerivativeVelocity(){
  //-The dynamic wall supplies the authoritative same-stage J-weighted mirror velocity.
  if(!SoilBoundaryDerivativeSPR || DynamicPoreWall)return;
  for(unsigned p=0;p<Npb;p++){
    const tfloat4 v=Velrhopc[p];
    const TpSlipMode mode=(BoundSlipModec? TpSlipMode(BoundSlipModec[p]): SlipMode);
    BoundDerivativeVelc[p]=TFloat3(v.x,v.y,v.z);
    //-Preserve the retained horizontal Vel0 fallback, including signed zero.
    if(mode==SLIP_Vel0 && BoundNormalc[p].x==0 && BoundNormalc[p].y==0)BoundDerivativeVelc[p].z=-v.z;
  }
  const auto readvelocity=[&](unsigned,unsigned p,unsigned c){
    const tfloat4 v=Velrhopc[p];
    return(double(c==0? v.x: (c==1? v.y: v.z)));
  };
  const auto writevelocity=[&](unsigned p,const double *velocity,const double*,const double*,const double*){
    const TpSlipMode mode=(BoundSlipModec? TpSlipMode(BoundSlipModec[p]): SlipMode);
    if(mode>=SLIP_NoSlip && BoundModec && BoundModec[p]==BMODE_MDBC2OFF)return;
    const tfloat4 v=Velrhopc[p];
    const tfloat3 bnormal=BoundNormalc[p];
    if(mode==SLIP_Vel0 && bnormal.x==0 && bnormal.y==0){
      //-Keep the accepted z-only path bit-compatible; do not replace its projection.
      BoundDerivativeVelc[p]=TFloat3(v.x,v.y,-float(0.0+velocity[2]));
    }
    else if(mode==SLIP_NoSlip){
      BoundDerivativeVelc[p]=TFloat3(float(2.0*double(v.x)-velocity[0]),
        float(2.0*double(v.y)-velocity[1]),float(2.0*double(v.z)-velocity[2]));
    }
    else{
      const tdouble3 nraw=ToTDouble3(bnormal);
      const tdouble3 normal=nraw/sqrt(nraw.x*nraw.x+nraw.y*nraw.y+nraw.z*nraw.z);
      const double wallnormal=double(v.x)*normal.x+double(v.y)*normal.y+double(v.z)*normal.z;
      const double ghostnormal=velocity[0]*normal.x+velocity[1]*normal.y+velocity[2]*normal.z;
      const double reflection=wallnormal-ghostnormal;
      if(mode==SLIP_FreeSlip){
        BoundDerivativeVelc[p]=TFloat3(float(velocity[0]+2.0*reflection*normal.x),
          float(velocity[1]+2.0*reflection*normal.y),float(velocity[2]+2.0*reflection*normal.z));
      }
      else{//-Legacy Vel0 keeps wall tangential velocity and mirrors only the normal derivative.
        BoundDerivativeVelc[p]=TFloat3(float(double(v.x)+reflection*normal.x),
          float(double(v.y)+reflection*normal.y),float(double(v.z)+reflection*normal.z));
      }
    }
  };
  if(Simulate2D)InterpolateBoundaryGhostFieldT<KERNEL_Wendland,true,3>(
    NpbOk,DivData,Posc,Codec,Velrhopc,BoundNormalc,readvelocity,writevelocity,true);
  else InterpolateBoundaryGhostFieldT<KERNEL_Wendland,false,3>(
    NpbOk,DivData,Posc,Codec,Velrhopc,BoundNormalc,readvelocity,writevelocity,true);
}

//==============================================================================
/// Selects mDBC pore-pressure extrapolation.
//==============================================================================
void JSphCpu::InteractionPorePressureMdbcCorrection(){
  if(!HydroMech || !PorePressc || !PorePress0c || !UseNormals || !BoundNormalc || !DivData.begincell)return;
  const unsigned n=(UseNormalsFt? Np: NpbOk);
  if(Simulate2D){
    switch(TKernel){
      case KERNEL_Wendland: InteractionPorePressureMdbcCorrectionT<KERNEL_Wendland,true >(n,DivData,Posc,Codec,Velrhopc,BoundNormalc,PorePress0c,PorePressc); break;
      case KERNEL_Cubic:    InteractionPorePressureMdbcCorrectionT<KERNEL_Cubic   ,true >(n,DivData,Posc,Codec,Velrhopc,BoundNormalc,PorePress0c,PorePressc); break;
      default: Run_Exceptioon("Kernel unknown.");
    }
  }
  else{
    switch(TKernel){
      case KERNEL_Wendland: InteractionPorePressureMdbcCorrectionT<KERNEL_Wendland,false>(n,DivData,Posc,Codec,Velrhopc,BoundNormalc,PorePress0c,PorePressc); break;
      case KERNEL_Cubic:    InteractionPorePressureMdbcCorrectionT<KERNEL_Cubic   ,false>(n,DivData,Posc,Codec,Velrhopc,BoundNormalc,PorePress0c,PorePressc); break;
      default: Run_Exceptioon("Kernel unknown.");
    }
  }
}

//==============================================================================
/// Calculates tangential velocity used by no-slip/free-slip mDBC viscous and gradient terms.
//==============================================================================
tfloat3 JSphCpu::Mdbc2TangenVel(const tfloat3 &boundnormal,const tfloat3 &velfinal)const{
  const float snormal2=boundnormal.x*boundnormal.x + boundnormal.y*boundnormal.y + boundnormal.z*boundnormal.z;
  if(snormal2<=ALMOSTZERO)return(TFloat3(0));
  const float invnormal=1.f/sqrt(snormal2);
  const tfloat3 normal=TFloat3(boundnormal.x*invnormal,boundnormal.y*invnormal,boundnormal.z*invnormal);
  const float veldotnorm=velfinal.x*normal.x + velfinal.y*normal.y + velfinal.z*normal.z;
  return(TFloat3(velfinal.x-veldotnorm*normal.x,
                 velfinal.y-veldotnorm*normal.y,
                 velfinal.z-veldotnorm*normal.z));
}

//==============================================================================
/// Perform interaction between ghost nodes of boundaries and fluid.
//==============================================================================
template<TpKernel tker,bool sim2d,TpSlipMode tslip> void JSphCpu::InteractionMdbcCorrectionT2
  (unsigned n,StDivDataCpu divdata,float determlimit,float mdbcthreshold
  ,const tdouble3 *pos,const typecode *code,const unsigned *idp
  ,const tfloat3 *boundnormal,const tfloat3 *motionvel,tfloat4 *velrhop,tsymatrix3d* sigma,byte *boundmode,const byte *boundslipmode,tfloat3 *tangenvel
  ,const float *porepress0,float *porepress)
{
  const int nn=int(n);
  const bool extrapolatepore=(porepress0 && porepress);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided)
  #endif
  for(int p1=0;p1<nn;p1++){
    if(boundnormal[p1]!=TFloat3(0)){
    const TpSlipMode slipmodep1=(boundslipmode? TpSlipMode(boundslipmode[p1]): tslip);
    const bool useboundmode=(boundmode && slipmodep1>=SLIP_NoSlip);
    float rhopfinal=FLT_MAX;
    tfloat3 velrhopfinal=TFloat3(0);
    tsymatrix3f sigmafinal={0,0,0,0,0,0};//mdbr
    float sumwab=0;
    float submerged=0;
    double pwexcesssum=0;
    double gradpwexcessx=0,gradpwexcessy=0,gradpwexcessz=0;

    //-Calculates ghost node position.
    tdouble3 gposp1=pos[p1]+ToTDouble3(boundnormal[p1]);
    gposp1=(PeriActive!=0? UpdatePeriodicPos(gposp1): gposp1); //-Corrected interface Position.
    //-Initializes variables for calculation.
    float rhopp1=0;
    tfloat3 gradrhopp1=TFloat3(0);
    //===== mdbr
	//-Stress
	tsymatrix3f sigmap1 = { 0,0,0,0,0,0 };//-First-order Stress value
	tfloat3 gradsigmaxxp1 = TFloat3(0);//-Stress gradient
	tfloat3 gradsigmayyp1 = TFloat3(0);
	tfloat3 gradsigmazzp1 = TFloat3(0);
	tfloat3 gradsigmaxyp1 = TFloat3(0);
	tfloat3 gradsigmayzp1 = TFloat3(0);
	tfloat3 gradsigmaxzp1 = TFloat3(0);
	//=====
    tdouble3 velp1=TDouble3(0);       //-Only for velocity.
    tmatrix3d a_corr2=TMatrix3d(0);   //-Only for 2D.
    tmatrix4d a_corr3=TMatrix4d(0);   //-Only for 3D.

    //-Search for neighbours in adjacent cells.
    const StNgSearch ngs=nsearch::Init(gposp1,false,divdata);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
      //-Interaction of boundary with type Fluid/Float.
      for(unsigned p2=pif.x;p2<pif.y;p2++){
        const float drx=float(gposp1.x-pos[p2].x);
        const float dry=float(gposp1.y-pos[p2].y);
        const float drz=float(gposp1.z-pos[p2].z);
        const float rr2=(drx*drx + dry*dry + drz*drz);
        if(rr2<=KernelSize2 && CODE_IsFluid(code[p2])){//-Only with fluid particles (including inout).
          //-Wendland kernel.
          float fac;
          const float wab=fsph::GetKernel_WabFac<tker>(CSP,rr2,fac);
          const float frx=fac*drx,fry=fac*dry,frz=fac*drz; //-Gradients.

          //===== Get mass and volume of particle p2 =====
          const tfloat4 velrhopp2=velrhop[p2];
          const tsymatrix3f sigmap2=ToTSymMatrix3f(sigma[p2]);//mdbr
          const float massp2=MassFluid;
          const float volp2=massp2/velrhopp2.w;
          if(useboundmode)submerged-=volp2*(drx*frx + dry*fry + drz*frz);

          //===== Density and its gradient =====
          //rhopp1+=massp2*wab;
          //gradrhopp1.x+=massp2*frx;
          //gradrhopp1.y+=massp2*fry;
          //gradrhopp1.z+=massp2*frz;

          //===== Kernel values multiplied by volume =====
          const float vwab=wab*volp2;
          sumwab+=vwab;
          const float vfrx=frx*volp2;
          const float vfry=fry*volp2;
          const float vfrz=frz*volp2;
          if(extrapolatepore){
            const double pwexcess=double(porepress[p2])-double(porepress0[p2]);
            pwexcesssum+=double(vwab)*pwexcess;
            gradpwexcessx+=double(vfrx)*pwexcess;
            gradpwexcessy+=double(vfry)*pwexcess;
            gradpwexcessz+=double(vfrz)*pwexcess;
          }
          //===== mdbr
		  //===== Stress value =====
		  sigmap1.xx += vwab*sigmap2.xx;
		  sigmap1.yy += vwab*sigmap2.yy;
		  sigmap1.zz += vwab*sigmap2.zz;
		  sigmap1.xy += vwab*sigmap2.xy;
		  sigmap1.yz += vwab*sigmap2.yz;
		  sigmap1.xz += vwab*sigmap2.xz;

		  //===== Stress gradient =====
		  //===== xx
		  gradsigmaxxp1.x += vfrx*sigmap2.xx;
		  gradsigmaxxp1.y += vfry*sigmap2.xx;
		  gradsigmaxxp1.z += vfrz*sigmap2.xx;
		  //===== yy
		  gradsigmayyp1.x += vfrx*sigmap2.yy;
		  gradsigmayyp1.y += vfry*sigmap2.yy;
		  gradsigmayyp1.z += vfrz*sigmap2.yy;
		  //===== zz
		  gradsigmazzp1.x += vfrx*sigmap2.zz;
		  gradsigmazzp1.y += vfry*sigmap2.zz;
		  gradsigmazzp1.z += vfrz*sigmap2.zz;
		  //===== xy
		  gradsigmaxyp1.x += vfrx*sigmap2.xy;
		  gradsigmaxyp1.y += vfry*sigmap2.xy;
		  gradsigmaxyp1.z += vfrz*sigmap2.xy;
		  //===== yz
		  gradsigmayzp1.x += vfrx*sigmap2.yz;
		  gradsigmayzp1.y += vfry*sigmap2.yz;
		  gradsigmayzp1.z += vfrz*sigmap2.yz;
		  //===== xz
		  gradsigmaxzp1.x += vfrx*sigmap2.xz;
		  gradsigmaxzp1.y += vfry*sigmap2.xz;
		  gradsigmaxzp1.z += vfrz*sigmap2.xz;
		  //===== End
          //===== Velocity =====
          if(slipmodep1!=SLIP_Vel0){
            velp1.x+=vwab*velrhopp2.x;
            velp1.y+=vwab*velrhopp2.y;
            velp1.z+=vwab*velrhopp2.z;
          }

          //===== Matrix A for correction =====
          if(sim2d){
            a_corr2.a11+=vwab;  a_corr2.a12+=drx*vwab;  a_corr2.a13+=drz*vwab;
            a_corr2.a21+=vfrx;  a_corr2.a22+=drx*vfrx;  a_corr2.a23+=drz*vfrx;
            a_corr2.a31+=vfrz;  a_corr2.a32+=drx*vfrz;  a_corr2.a33+=drz*vfrz;
          }
          else{
            a_corr3.a11+=vwab;  a_corr3.a12+=drx*vwab;  a_corr3.a13+=dry*vwab;  a_corr3.a14+=drz*vwab;
            a_corr3.a21+=vfrx;  a_corr3.a22+=drx*vfrx;  a_corr3.a23+=dry*vfrx;  a_corr3.a24+=drz*vfrx;
            a_corr3.a31+=vfry;  a_corr3.a32+=drx*vfry;  a_corr3.a33+=dry*vfry;  a_corr3.a34+=drz*vfry;
            a_corr3.a41+=vfrz;  a_corr3.a42+=drx*vfrz;  a_corr3.a43+=dry*vfrz;  a_corr3.a44+=drz*vfrz;
          }
        }
      }
    }

    //-Store the results.
    //--------------------
    const bool activebound=(useboundmode? submerged>0.f: (sumwab>=mdbcthreshold || (mdbcthreshold>=2 && sumwab+2>=mdbcthreshold)));
    const bool activepore=(submerged>0.f || sumwab>=mdbcthreshold || (mdbcthreshold>=2 && sumwab+2>=mdbcthreshold));
    const bool poremls=(PoreMdbcInterpolationMode==1);
    bool hasinv2=false;
    bool hasinv3=false;
    tmatrix3d invacorr2=TMatrix3d(0);
    tmatrix4d invacorr3=TMatrix4d(0);
    if(activebound || (poremls && extrapolatepore && activepore && sumwab>0)){
      if(sim2d){
        const double determ=fmath::Determinant3x3(a_corr2);
        if(fabs(determ)>=determlimit){
          invacorr2=fmath::InverseMatrix3x3(a_corr2,determ);
          hasinv2=true;
        }
      }
      else{
        const double determ=fmath::Determinant4x4(a_corr3);
        if(fabs(determ)>=determlimit){
          invacorr3=fmath::InverseMatrix4x4(a_corr3,determ);
          hasinv3=true;
        }
      }
    }
    if(extrapolatepore && activepore && sumwab>0){
      double pwexcessfinal=pwexcesssum/double(sumwab); //-0th-order fallback.
      if(poremls && sim2d){
        if(hasinv2){
          const double qg = invacorr2.a11*pwexcesssum + invacorr2.a12*gradpwexcessx + invacorr2.a13*gradpwexcessz;
          pwexcessfinal=qg;
        }
      }
      else if(poremls){
        if(hasinv3){
          const double qg = invacorr3.a11*pwexcesssum + invacorr3.a12*gradpwexcessx + invacorr3.a13*gradpwexcessy + invacorr3.a14*gradpwexcessz;
          pwexcessfinal=qg;
        }
      }
      porepress[p1]=float(double(porepress0[p1])+pwexcessfinal);
    }
    if(activebound){
      if(useboundmode)boundmode[p1]=BMODE_MDBC2;
      const tfloat3 dpos=(boundnormal[p1]*(-1.f)); //-Boundary particle position - ghost node position.
      if(sim2d){
        if(hasinv2){//-Use 1e-3f (first_order) or 1e+3f (zeroth_order).
          //-GHOST NODE DENSITY IS MIRRORED BACK TO THE BOUNDARY PARTICLES.
          //const float rhoghost=float(invacorr2.a11*rhopp1 + invacorr2.a12*gradrhopp1.x + invacorr2.a13*gradrhopp1.z);
          //const float grx=    -float(invacorr2.a21*rhopp1 + invacorr2.a22*gradrhopp1.x + invacorr2.a23*gradrhopp1.z);
          //const float grz=    -float(invacorr2.a31*rhopp1 + invacorr2.a32*gradrhopp1.x + invacorr2.a33*gradrhopp1.z);
          //rhopfinal=(rhoghost + grx*dpos.x + grz*dpos.z);
          //-Ghost stress ==== mdbr
			//-xx
			const float sigmaxxg = float(invacorr2.a11*sigmap1.xx + invacorr2.a12*gradsigmaxxp1.x + invacorr2.a13*gradsigmaxxp1.z);
			const float sixxgrx = -float(invacorr2.a21*sigmap1.xx + invacorr2.a22*gradsigmaxxp1.x + invacorr2.a23*gradsigmaxxp1.z);
			const float sixxgrz = -float(invacorr2.a31*sigmap1.xx + invacorr2.a32*gradsigmaxxp1.x + invacorr2.a33*gradsigmaxxp1.z);
			//-zz
			const float sigmazzg = float(invacorr2.a11*sigmap1.zz + invacorr2.a12*gradsigmazzp1.x + invacorr2.a13*gradsigmazzp1.z);
			const float sizzgrx = -float(invacorr2.a21*sigmap1.zz + invacorr2.a22*gradsigmazzp1.x + invacorr2.a23*gradsigmazzp1.z);
			const float sizzgrz = -float(invacorr2.a31*sigmap1.zz + invacorr2.a32*gradsigmazzp1.x + invacorr2.a33*gradsigmazzp1.z);
			//-xz
			const float sigmaxzg = float(invacorr2.a11*sigmap1.xz + invacorr2.a12*gradsigmaxzp1.x + invacorr2.a13*gradsigmaxzp1.z);
			const float sixzgrx = -float(invacorr2.a21*sigmap1.xz + invacorr2.a22*gradsigmaxzp1.x + invacorr2.a23*gradsigmaxzp1.z);
			const float sixzgrz = -float(invacorr2.a31*sigmap1.xz + invacorr2.a32*gradsigmaxzp1.x + invacorr2.a33*gradsigmaxzp1.z);
			//-Final stress
			sigmafinal.xx = sigmaxxg + sixxgrx*dpos.x + sixxgrz*dpos.z;
			sigmafinal.zz = sigmazzg + sizzgrx*dpos.x + sizzgrz*dpos.z;
			sigmafinal.xz = sigmaxzg + sixzgrx*dpos.x + sixzgrz*dpos.z;
			//=====
        }
        else if(a_corr2.a11>0){//-Determinant is small but a11 is nonzero (0th order).
          rhopfinal=float(rhopp1/a_corr2.a11);
          sigmafinal.xx = float(sigmap1.xx / a_corr2.a11);
		  sigmafinal.zz = float(sigmap1.zz / a_corr2.a11);
		  sigmafinal.xz = float(sigmap1.xz / a_corr2.a11);
        }
        //-Ghost node velocity (0th order).
        if(a_corr2.a11>0&&slipmodep1!=SLIP_Vel0){
          velrhopfinal.x=float(velp1.x/a_corr2.a11);
          velrhopfinal.z=float(velp1.z/a_corr2.a11);
          velrhopfinal.y=0;
        }
      }
      else{
        if(hasinv3){
          //-GHOST NODE DENSITY IS MIRRORED BACK TO THE BOUNDARY PARTICLES.
          //const float rhoghost=float(invacorr3.a11*rhopp1 + invacorr3.a12*gradrhopp1.x + invacorr3.a13*gradrhopp1.y + invacorr3.a14*gradrhopp1.z);
          //const float grx=    -float(invacorr3.a21*rhopp1 + invacorr3.a22*gradrhopp1.x + invacorr3.a23*gradrhopp1.y + invacorr3.a24*gradrhopp1.z);
          //const float gry=    -float(invacorr3.a31*rhopp1 + invacorr3.a32*gradrhopp1.x + invacorr3.a33*gradrhopp1.y + invacorr3.a34*gradrhopp1.z);
          //const float grz=    -float(invacorr3.a41*rhopp1 + invacorr3.a42*gradrhopp1.x + invacorr3.a43*gradrhopp1.y + invacorr3.a44*gradrhopp1.z);
          //rhopfinal=(rhoghost + grx*dpos.x + gry*dpos.y + grz*dpos.z);
          //-xx
			const float sigmaxxg = float(invacorr3.a11*sigmap1.xx + invacorr3.a12*gradsigmaxxp1.x + invacorr3.a13*gradsigmaxxp1.y + invacorr3.a14*gradsigmaxxp1.z);
			const float sixxgrx = -float(invacorr3.a21*sigmap1.xx + invacorr3.a22*gradsigmaxxp1.x + invacorr3.a23*gradsigmaxxp1.y + invacorr3.a24*gradsigmaxxp1.z);
			const float sixxgry = -float(invacorr3.a31*sigmap1.xx + invacorr3.a32*gradsigmaxxp1.x + invacorr3.a33*gradsigmaxxp1.y + invacorr3.a34*gradsigmaxxp1.z);
			const float sixxgrz = -float(invacorr3.a41*sigmap1.xx + invacorr3.a42*gradsigmaxxp1.x + invacorr3.a43*gradsigmaxxp1.y + invacorr3.a44*gradsigmaxxp1.z);
			//-yy
			const float sigmayyg = float(invacorr3.a11*sigmap1.yy + invacorr3.a12*gradsigmayyp1.x + invacorr3.a13*gradsigmayyp1.y + invacorr3.a14*gradsigmayyp1.z);
			const float siyygrx = -float(invacorr3.a21*sigmap1.yy + invacorr3.a22*gradsigmayyp1.x + invacorr3.a23*gradsigmayyp1.y + invacorr3.a24*gradsigmayyp1.z);
			const float siyygry = -float(invacorr3.a31*sigmap1.yy + invacorr3.a32*gradsigmayyp1.x + invacorr3.a33*gradsigmayyp1.y + invacorr3.a34*gradsigmayyp1.z);
			const float siyygrz = -float(invacorr3.a41*sigmap1.yy + invacorr3.a42*gradsigmayyp1.x + invacorr3.a43*gradsigmayyp1.y + invacorr3.a44*gradsigmayyp1.z);
			//-zz
			const float sigmazzg = float(invacorr3.a11*sigmap1.zz + invacorr3.a12*gradsigmazzp1.x + invacorr3.a13*gradsigmazzp1.y + invacorr3.a14*gradsigmazzp1.z);
			const float sizzgrx = -float(invacorr3.a21*sigmap1.zz + invacorr3.a22*gradsigmazzp1.x + invacorr3.a23*gradsigmazzp1.y + invacorr3.a24*gradsigmazzp1.z);
			const float sizzgry = -float(invacorr3.a31*sigmap1.zz + invacorr3.a32*gradsigmazzp1.x + invacorr3.a33*gradsigmazzp1.y + invacorr3.a34*gradsigmazzp1.z);
			const float sizzgrz = -float(invacorr3.a41*sigmap1.zz + invacorr3.a42*gradsigmazzp1.x + invacorr3.a43*gradsigmazzp1.y + invacorr3.a44*gradsigmazzp1.z);
			//-xy
			const float sigmaxyg = float(invacorr3.a11*sigmap1.xy + invacorr3.a12*gradsigmaxyp1.x + invacorr3.a13*gradsigmaxyp1.y + invacorr3.a14*gradsigmaxyp1.z);
			const float sixygrx = -float(invacorr3.a21*sigmap1.xy + invacorr3.a22*gradsigmaxyp1.x + invacorr3.a23*gradsigmaxyp1.y + invacorr3.a24*gradsigmaxyp1.z);
			const float sixygry = -float(invacorr3.a31*sigmap1.xy + invacorr3.a32*gradsigmaxyp1.x + invacorr3.a33*gradsigmaxyp1.y + invacorr3.a34*gradsigmaxyp1.z);
			const float sixygrz = -float(invacorr3.a41*sigmap1.xy + invacorr3.a42*gradsigmaxyp1.x + invacorr3.a43*gradsigmaxyp1.y + invacorr3.a44*gradsigmaxyp1.z);
			//-yz
			const float sigmayzg = float(invacorr3.a11*sigmap1.yz + invacorr3.a12*gradsigmayzp1.x + invacorr3.a13*gradsigmayzp1.y + invacorr3.a14*gradsigmayzp1.z);
			const float siyzgrx = -float(invacorr3.a21*sigmap1.yz + invacorr3.a22*gradsigmayzp1.x + invacorr3.a23*gradsigmayzp1.y + invacorr3.a24*gradsigmayzp1.z);
			const float siyzgry = -float(invacorr3.a31*sigmap1.yz + invacorr3.a32*gradsigmayzp1.x + invacorr3.a33*gradsigmayzp1.y + invacorr3.a34*gradsigmayzp1.z);
			const float siyzgrz = -float(invacorr3.a41*sigmap1.yz + invacorr3.a42*gradsigmayzp1.x + invacorr3.a43*gradsigmayzp1.y + invacorr3.a44*gradsigmayzp1.z);
			//-xz
			const float sigmaxzg = float(invacorr3.a11*sigmap1.xz + invacorr3.a12*gradsigmaxzp1.x + invacorr3.a13*gradsigmaxzp1.y + invacorr3.a14*gradsigmaxzp1.z);
			const float sixzgrx = -float(invacorr3.a21*sigmap1.xz + invacorr3.a22*gradsigmaxzp1.x + invacorr3.a23*gradsigmaxzp1.y + invacorr3.a24*gradsigmaxzp1.z);
			const float sixzgry = -float(invacorr3.a31*sigmap1.xz + invacorr3.a32*gradsigmaxzp1.x + invacorr3.a33*gradsigmaxzp1.y + invacorr3.a34*gradsigmaxzp1.z);
			const float sixzgrz = -float(invacorr3.a41*sigmap1.xz + invacorr3.a42*gradsigmaxzp1.x + invacorr3.a43*gradsigmaxzp1.y + invacorr3.a44*gradsigmaxzp1.z);
			//-Final stress
			sigmafinal.xx = sigmaxxg + sixxgrx*dpos.x + sixxgry*dpos.y + sixxgrz*dpos.z;
			sigmafinal.yy = sigmayyg + siyygrx*dpos.x + siyygry*dpos.y + siyygrz*dpos.z;
			sigmafinal.zz = sigmazzg + sizzgrx*dpos.x + sizzgry*dpos.y + sizzgrz*dpos.z;
			sigmafinal.xy = sigmaxyg + sixygrx*dpos.x + sixygry*dpos.y + sixygrz*dpos.z;
			sigmafinal.yz = sigmayzg + siyzgrx*dpos.x + siyzgry*dpos.y + siyzgrz*dpos.z;
			sigmafinal.xz = sigmaxzg + sixzgrx*dpos.x + sixzgry*dpos.y + sixzgrz*dpos.z;
        }
        else if(a_corr3.a11>0){//-Determinant is small but a11 is nonzero (0th order).
          rhopfinal=float(rhopp1/a_corr3.a11);
          //==== mdbr
          sigmafinal.xx = float(sigmap1.xx / a_corr3.a11);
          sigmafinal.yy = float(sigmap1.yy / a_corr3.a11);
          sigmafinal.zz = float(sigmap1.zz / a_corr3.a11);
          sigmafinal.xy = float(sigmap1.xy / a_corr3.a11);
          sigmafinal.yz = float(sigmap1.yz / a_corr3.a11);
          sigmafinal.xz = float(sigmap1.xz / a_corr3.a11);
        }
        //-Ghost node velocity (0th order).
        if(a_corr3.a11>0&&slipmodep1!=SLIP_Vel0){
          velrhopfinal.x=float(velp1.x/a_corr3.a11);
          velrhopfinal.y=float(velp1.y/a_corr3.a11);
          velrhopfinal.z=float(velp1.z/a_corr3.a11);
        }
      }
      //-Store the results.
      rhopfinal=RhopZero;//rhopfinal=(rhopfinal!=FLT_MAX? rhopfinal: RhopZero);
      if(slipmodep1==SLIP_Vel0){//-DBC vel=0
        velrhop[p1].w=rhopfinal;
        sigma[p1] = ToTSymMatrix3d(sigmafinal);
      }
      if(slipmodep1==SLIP_NoSlip){//-No-Slip
        const tfloat3 v=motionvel[p1];
        const tfloat3 v2=TFloat3(v.x+v.x-velrhopfinal.x,v.y+v.y-velrhopfinal.y,v.z+v.z-velrhopfinal.z);
        velrhop[p1].w=rhopfinal;
        if(tangenvel)tangenvel[p1]=Mdbc2TangenVel(boundnormal[p1],v2);
        sigma[p1] = ToTSymMatrix3d(sigmafinal);
      }
      if(slipmodep1==SLIP_FreeSlip){//-Free-slip keeps boundary velocity and stores extrapolated tangential velocity.
        velrhop[p1].w=rhopfinal;
        if(tangenvel)tangenvel[p1]=Mdbc2TangenVel(boundnormal[p1],velrhopfinal);
        sigma[p1] = ToTSymMatrix3d(sigmafinal);
      }
    }
    else if(useboundmode){
      boundmode[p1]=BMODE_MDBC2OFF;
      velrhop[p1].w=RhopZero;
      sigma[p1]=TSymMatrix3d();
      if(tangenvel)tangenvel[p1]=Mdbc2TangenVel(boundnormal[p1],motionvel[p1]);
    }
    }
  }
}

//==============================================================================
/// Calculates extrapolated data on boundary particles from fluid domain for mDBC.
/// Calcula datos extrapolados en el contorno para mDBC.
//==============================================================================
 template<TpKernel tker> void JSphCpu::Interaction_MdbcCorrectionT(TpSlipMode slipmode
  ,const StDivDataCpu &divdata,const tdouble3 *pos,const typecode *code,const unsigned *idp
  ,const tfloat3 *boundnormal,const tfloat3 *motionvel,tfloat4 *velrhop,tsymatrix3d* sigma,byte *boundmode,const byte *boundslipmode,tfloat3 *tangenvel
  ,const float *porepress0,float *porepress)
{
  const float determlimit=1e-3f;
  //-Interaction GhostBoundaryNodes-Fluid.
  const unsigned n=(UseNormalsFt? Np: NpbOk);
  if(Simulate2D){ const bool sim2d=true;
    if(slipmode==SLIP_Vel0    )InteractionMdbcCorrectionT2 <tker,sim2d,SLIP_Vel0    > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
    if(slipmode==SLIP_NoSlip  )InteractionMdbcCorrectionT2 <tker,sim2d,SLIP_NoSlip  > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
    if(slipmode==SLIP_FreeSlip)InteractionMdbcCorrectionT2 <tker,sim2d,SLIP_FreeSlip> (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
  }else{          const bool sim2d=false;
    if(slipmode==SLIP_Vel0    )InteractionMdbcCorrectionT2 <tker,sim2d,SLIP_Vel0    > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
    if(slipmode==SLIP_NoSlip  )InteractionMdbcCorrectionT2 <tker,sim2d,SLIP_NoSlip  > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
    if(slipmode==SLIP_FreeSlip)InteractionMdbcCorrectionT2 <tker,sim2d,SLIP_FreeSlip> (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
  }
}

//==============================================================================
/// Calculates extrapolated data on boundary particles from fluid domain for mDBC.
/// Calcula datos extrapolados en el contorno para mDBC.
//==============================================================================
void JSphCpu::Interaction_MdbcCorrection(TpSlipMode slipmode,const StDivDataCpu &divdata
  ,const tdouble3 *pos,const typecode *code,const unsigned *idp
  ,const tfloat3 *boundnormal,const tfloat3 *motionvel,tfloat4 *velrhop,tsymatrix3d* sigma,byte *boundmode,const byte *boundslipmode,tfloat3 *tangenvel
  ,const float *porepress0,float *porepress)
{
  switch(TKernel){
    case KERNEL_Cubic:       Interaction_MdbcCorrectionT <KERNEL_Cubic     > (slipmode,divdata,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);  break;
    case KERNEL_Wendland:    Interaction_MdbcCorrectionT <KERNEL_Wendland  > (slipmode,divdata,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);  break;
    default: Run_Exceptioon("Kernel unknown.");
  }
}

//====================CDBC implementation============
//==============================================================================
/// Perform interaction between ghost nodes of boundaries and fluid.
//==============================================================================
template<TpKernel tker,bool sim2d,TpSlipMode tslip> void JSphCpu::InteractionCdbcCorrectionT2
  (unsigned n,StDivDataCpu divdata,float determlimit,float mdbcthreshold
  ,const tdouble3 *pos,const typecode *code,const unsigned *idp
  ,const tfloat3 *boundnormal,const tfloat3 *motionvel,tfloat4 *velrhop,tsymatrix3d* sigma,const byte *boundslipmode,tfloat3 *tangenvel)
{
  const int nn=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided)
  #endif
  for(int p1=0;p1<nn;p1++){
    const TpSlipMode slipmodep1=(boundslipmode? TpSlipMode(boundslipmode[p1]): tslip);
    if(tangenvel && slipmodep1==SLIP_NoSlip)tangenvel[p1]=motionvel[p1];
    if(tangenvel && slipmodep1==SLIP_FreeSlip)tangenvel[p1]=Mdbc2TangenVel(boundnormal[p1],motionvel[p1]);
   const typecode cod = code[p1];
   if (CODE_IsNotFluid(cod)){
    float rhopfinal=FLT_MAX;
    tfloat3 velrhopfinal=TFloat3(0);
    tsymatrix3f sigmafinal={0,0,0,0,0,0};//mdbr
    float sumwab=0;
    //-Calculates ghost node position.
    tdouble3 gposp1=pos[p1];//+ToTDouble3(boundnormal[p1]);
    //gposp1=(PeriActive!=0? UpdatePeriodicPos(gposp1): gposp1); //-Corrected interface Position.
    //-Initializes variables for calculation.
    float rhopp1=0;
    tfloat3 gradrhopp1=TFloat3(0);
    //===== mdbr
	//-Stress
	tsymatrix3f sigmap1 = { 0,0,0,0,0,0 };//-First-order Stress value
	tfloat3 gradsigmaxxp1 = TFloat3(0);//-Stress gradient
	tfloat3 gradsigmayyp1 = TFloat3(0);
	tfloat3 gradsigmazzp1 = TFloat3(0);
	tfloat3 gradsigmaxyp1 = TFloat3(0);
	tfloat3 gradsigmayzp1 = TFloat3(0);
	tfloat3 gradsigmaxzp1 = TFloat3(0);
	//=====
    tdouble3 velp1=TDouble3(0);       //-Only for velocity.
    tmatrix3d a_corr2=TMatrix3d(0);   //-Only for 2D.
    tmatrix4d a_corr3=TMatrix4d(0);   //-Only for 3D.

    //-Search for neighbours in adjacent cells.
    const StNgSearch ngs=nsearch::Init(gposp1,false,divdata);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
      //-Interaction of boundary with type Fluid/Float.
      for(unsigned p2=pif.x;p2<pif.y;p2++){
        const float drx=float(gposp1.x-pos[p2].x);
        const float dry=float(gposp1.y-pos[p2].y);
        const float drz=float(gposp1.z-pos[p2].z);
        const float rr2=(drx*drx + dry*dry + drz*drz);
        if(rr2<=KernelSize2 && CODE_IsFluid(code[p2])){//-Only with fluid particles (including inout).
          //-Wendland kernel.
          float fac;
          const float wab=fsph::GetKernel_WabFac<tker>(CSP,rr2,fac);
          const float frx=fac*drx,fry=fac*dry,frz=fac*drz; //-Gradients.

          //===== Get mass and volume of particle p2 =====
          const tfloat4 velrhopp2=velrhop[p2];
          const tsymatrix3f sigmap2=ToTSymMatrix3f(sigma[p2]);//mdbr
          const float massp2=MassFluid;
          const float volp2=massp2/velrhopp2.w;

          //===== Density and its gradient =====
          //rhopp1+=massp2*wab;
          //gradrhopp1.x+=massp2*frx;
          //gradrhopp1.y+=massp2*fry;
          //gradrhopp1.z+=massp2*frz;

          //===== Kernel values multiplied by volume =====
          const float vwab=wab*volp2;
          sumwab+=vwab;
          const float vfrx=frx*volp2;
          const float vfry=fry*volp2;
          const float vfrz=frz*volp2;
          //===== mdbr
		  //===== Stress value =====
			sigmap1.xx += vwab*sigmap2.xx;
			sigmap1.yy += vwab*sigmap2.yy;
			sigmap1.zz += vwab*sigmap2.zz;
			sigmap1.xy += vwab*sigmap2.xy;
			sigmap1.yz += vwab*sigmap2.yz;
			sigmap1.xz += vwab*sigmap2.xz;

			//===== Stress gradient =====
			//===== xx
			gradsigmaxxp1.x += vfrx*sigmap2.xx;
			gradsigmaxxp1.y += vfry*sigmap2.xx;
			gradsigmaxxp1.z += vfrz*sigmap2.xx;
			//===== yy
			gradsigmayyp1.x += vfrx*sigmap2.yy;
			gradsigmayyp1.y += vfry*sigmap2.yy;
			gradsigmayyp1.z += vfrz*sigmap2.yy;
			//===== zz
			gradsigmazzp1.x += vfrx*sigmap2.zz;
			gradsigmazzp1.y += vfry*sigmap2.zz;
			gradsigmazzp1.z += vfrz*sigmap2.zz;
			//===== xy
			gradsigmaxyp1.x += vfrx*sigmap2.xy;
			gradsigmaxyp1.y += vfry*sigmap2.xy;
			gradsigmaxyp1.z += vfrz*sigmap2.xy;
			//===== yz
			gradsigmayzp1.x += vfrx*sigmap2.yz;
			gradsigmayzp1.y += vfry*sigmap2.yz;
			gradsigmayzp1.z += vfrz*sigmap2.yz;
			//===== xz
			gradsigmaxzp1.x += vfrx*sigmap2.xz;
			gradsigmaxzp1.y += vfry*sigmap2.xz;
			gradsigmaxzp1.z += vfrz*sigmap2.xz;
			//===== End
          //===== Velocity =====
          if(slipmodep1!=SLIP_Vel0){
            velp1.x+=vwab*velrhopp2.x;
            velp1.y+=vwab*velrhopp2.y;
            velp1.z+=vwab*velrhopp2.z;
          }

          //===== Matrix A for correction =====
          if(sim2d){
            a_corr2.a11+=vwab;  a_corr2.a12+=drx*vwab;  a_corr2.a13+=drz*vwab;
            a_corr2.a21+=vfrx;  a_corr2.a22+=drx*vfrx;  a_corr2.a23+=drz*vfrx;
            a_corr2.a31+=vfrz;  a_corr2.a32+=drx*vfrz;  a_corr2.a33+=drz*vfrz;
          }
          else{
            a_corr3.a11+=vwab;  a_corr3.a12+=drx*vwab;  a_corr3.a13+=dry*vwab;  a_corr3.a14+=drz*vwab;
            a_corr3.a21+=vfrx;  a_corr3.a22+=drx*vfrx;  a_corr3.a23+=dry*vfrx;  a_corr3.a24+=drz*vfrx;
            a_corr3.a31+=vfry;  a_corr3.a32+=drx*vfry;  a_corr3.a33+=dry*vfry;  a_corr3.a34+=drz*vfry;
            a_corr3.a41+=vfrz;  a_corr3.a42+=drx*vfrz;  a_corr3.a43+=dry*vfrz;  a_corr3.a44+=drz*vfrz;
          }
        }
      }
    }

    //-Store the results.
    //--------------------
    if(sumwab>=mdbcthreshold || (mdbcthreshold>=2 && sumwab+2>=mdbcthreshold)){
      const tfloat3 dpos=(boundnormal[p1]*(-1.f)); //-Boundary particle position - ghost node position.
      if(sim2d){
        const double determ=fmath::Determinant3x3(a_corr2);
        if(fabs(determ)>=determlimit){//-Use 1e-3f (first_order) or 1e+3f (zeroth_order).
          const tmatrix3d invacorr2=fmath::InverseMatrix3x3(a_corr2,determ);
          //-GHOST NODE DENSITY IS MIRRORED BACK TO THE BOUNDARY PARTICLES.
          //const float rhoghost=float(invacorr2.a11*rhopp1 + invacorr2.a12*gradrhopp1.x + invacorr2.a13*gradrhopp1.z);
          //const float grx=    -float(invacorr2.a21*rhopp1 + invacorr2.a22*gradrhopp1.x + invacorr2.a23*gradrhopp1.z);
          //const float grz=    -float(invacorr2.a31*rhopp1 + invacorr2.a32*gradrhopp1.x + invacorr2.a33*gradrhopp1.z);
          //rhopfinal=(rhoghost + grx*dpos.x + grz*dpos.z);
          //-Ghost stress ==== mdbr
			//-xx
			const float sigmaxxg = float(invacorr2.a11*sigmap1.xx + invacorr2.a12*gradsigmaxxp1.x + invacorr2.a13*gradsigmaxxp1.z);
			//-zz
			const float sigmazzg = float(invacorr2.a11*sigmap1.zz + invacorr2.a12*gradsigmazzp1.x + invacorr2.a13*gradsigmazzp1.z);
			//-xz
			const float sigmaxzg = float(invacorr2.a11*sigmap1.xz + invacorr2.a12*gradsigmaxzp1.x + invacorr2.a13*gradsigmaxzp1.z);
			//-Final stress
			sigmafinal.xx = sigmaxxg;
			sigmafinal.zz = sigmazzg;
			sigmafinal.xz = sigmaxzg;
			//=====
        }
        else if(a_corr2.a11>0){//-Determinant is small but a11 is nonzero (0th order).
          rhopfinal=float(rhopp1/a_corr2.a11);
          sigmafinal.xx = float(sigmap1.xx / a_corr2.a11);
		  sigmafinal.zz = float(sigmap1.zz / a_corr2.a11);
		  sigmafinal.xz = float(sigmap1.xz / a_corr2.a11);
        }
        //-Ghost node velocity (0th order).
        if(a_corr2.a11>0&&slipmodep1!=SLIP_Vel0){
          velrhopfinal.x=float(velp1.x/a_corr2.a11);
          velrhopfinal.z=float(velp1.z/a_corr2.a11);
          velrhopfinal.y=0;
        }
      }
      else{
        const double determ=fmath::Determinant4x4(a_corr3);
        if(fabs(determ)>=determlimit){
          const tmatrix4d invacorr3=fmath::InverseMatrix4x4(a_corr3,determ);
          //-GHOST NODE DENSITY IS MIRRORED BACK TO THE BOUNDARY PARTICLES.
          //const float rhoghost=float(invacorr3.a11*rhopp1 + invacorr3.a12*gradrhopp1.x + invacorr3.a13*gradrhopp1.y + invacorr3.a14*gradrhopp1.z);
          //const float grx=    -float(invacorr3.a21*rhopp1 + invacorr3.a22*gradrhopp1.x + invacorr3.a23*gradrhopp1.y + invacorr3.a24*gradrhopp1.z);
          //const float gry=    -float(invacorr3.a31*rhopp1 + invacorr3.a32*gradrhopp1.x + invacorr3.a33*gradrhopp1.y + invacorr3.a34*gradrhopp1.z);
          //const float grz=    -float(invacorr3.a41*rhopp1 + invacorr3.a42*gradrhopp1.x + invacorr3.a43*gradrhopp1.y + invacorr3.a44*gradrhopp1.z);
          //rhopfinal=(rhoghost + grx*dpos.x + gry*dpos.y + grz*dpos.z);
          	//-xx
			const float sigmaxxg = float(invacorr3.a11*sigmap1.xx + invacorr3.a12*gradsigmaxxp1.x + invacorr3.a13*gradsigmaxxp1.y + invacorr3.a14*gradsigmaxxp1.z);
			//-yy
			const float sigmayyg = float(invacorr3.a11*sigmap1.yy + invacorr3.a12*gradsigmayyp1.x + invacorr3.a13*gradsigmayyp1.y + invacorr3.a14*gradsigmayyp1.z);
			//-zz
			const float sigmazzg = float(invacorr3.a11*sigmap1.zz + invacorr3.a12*gradsigmazzp1.x + invacorr3.a13*gradsigmazzp1.y + invacorr3.a14*gradsigmazzp1.z);
			//-xy
			const float sigmaxyg = float(invacorr3.a11*sigmap1.xy + invacorr3.a12*gradsigmaxyp1.x + invacorr3.a13*gradsigmaxyp1.y + invacorr3.a14*gradsigmaxyp1.z);
			//-yz
			const float sigmayzg = float(invacorr3.a11*sigmap1.yz + invacorr3.a12*gradsigmayzp1.x + invacorr3.a13*gradsigmayzp1.y + invacorr3.a14*gradsigmayzp1.z);
			//-xz
			const float sigmaxzg = float(invacorr3.a11*sigmap1.xz + invacorr3.a12*gradsigmaxzp1.x + invacorr3.a13*gradsigmaxzp1.y + invacorr3.a14*gradsigmaxzp1.z);
			//-Final stress
			sigmafinal.xx = sigmaxxg;
			sigmafinal.yy = sigmayyg;
			sigmafinal.zz = sigmazzg;
			sigmafinal.xy = sigmaxyg;
			sigmafinal.yz = sigmayzg;
			sigmafinal.xz = sigmaxzg;
        }
        else if(a_corr3.a11>0){//-Determinant is small but a11 is nonzero (0th order).
          rhopfinal=float(rhopp1/a_corr3.a11);
            //==== mdbr
            sigmafinal.xx = float(sigmap1.xx / a_corr3.a11);
            sigmafinal.yy = float(sigmap1.yy / a_corr3.a11);
            sigmafinal.zz = float(sigmap1.zz / a_corr3.a11);
            sigmafinal.xy = float(sigmap1.xy / a_corr3.a11);
            sigmafinal.yz = float(sigmap1.yz / a_corr3.a11);
            sigmafinal.xz = float(sigmap1.xz / a_corr3.a11);
        }
        //-Ghost node velocity (0th order).
        if(a_corr3.a11>0&&slipmodep1!=SLIP_Vel0){
          velrhopfinal.x=float(velp1.x/a_corr3.a11);
          velrhopfinal.y=float(velp1.y/a_corr3.a11);
          velrhopfinal.z=float(velp1.z/a_corr3.a11);
        }
      }
      //-Store the results.
      rhopfinal=RhopZero;//rhopfinal=(rhopfinal!=FLT_MAX? rhopfinal: RhopZero);
      if(slipmodep1==SLIP_Vel0){//-DBC vel=0
        velrhop[p1].w=rhopfinal;
        sigma[p1] = ToTSymMatrix3d(sigmafinal);
      }
      if(slipmodep1==SLIP_NoSlip){//-No-Slip
        const tfloat3 v=motionvel[p1];
        const tfloat3 v2=TFloat3(v.x+v.x-velrhopfinal.x,v.y+v.y-velrhopfinal.y,v.z+v.z-velrhopfinal.z);
        velrhop[p1].w=rhopfinal;
        if(tangenvel)tangenvel[p1]=Mdbc2TangenVel(boundnormal[p1],v2);
        sigma[p1] = ToTSymMatrix3d(sigmafinal);
      }
      if(slipmodep1==SLIP_FreeSlip){//-Free-slip keeps boundary velocity and stores extrapolated tangential velocity.
        velrhop[p1].w=rhopfinal;
        if(tangenvel)tangenvel[p1]=Mdbc2TangenVel(boundnormal[p1],velrhopfinal);
        sigma[p1] = ToTSymMatrix3d(sigmafinal);
      }
    }
  }
  }
}

//==============================================================================
/// Calculates extrapolated data on boundary particles from fluid domain for mDBC.
/// Calcula datos extrapolados en el contorno para mDBC.
//==============================================================================
 template<TpKernel tker> void JSphCpu::Interaction_CdbcCorrectionT(TpSlipMode slipmode
  ,const StDivDataCpu &divdata,const tdouble3 *pos,const typecode *code,const unsigned *idp
  ,const tfloat3 *boundnormal,const tfloat3 *motionvel,tfloat4 *velrhop,tsymatrix3d* sigma,const byte *boundslipmode,tfloat3 *tangenvel)
{
  const float determlimit=1e-3f;
  //-Interaction GhostBoundaryNodes-Fluid.
  //const unsigned n=(UseNormalsFt? Np: NpbOk);
  const unsigned n=(WithFloating? Np: NpbOk);
  if(Simulate2D){ const bool sim2d=true;
    if(slipmode==SLIP_Vel0    )InteractionCdbcCorrectionT2 <tker,sim2d,SLIP_Vel0    > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundslipmode,tangenvel);
    if(slipmode==SLIP_NoSlip  )InteractionCdbcCorrectionT2 <tker,sim2d,SLIP_NoSlip  > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundslipmode,tangenvel);
    if(slipmode==SLIP_FreeSlip)InteractionCdbcCorrectionT2 <tker,sim2d,SLIP_FreeSlip> (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundslipmode,tangenvel);
  }else{          const bool sim2d=false;
    if(slipmode==SLIP_Vel0    )InteractionCdbcCorrectionT2 <tker,sim2d,SLIP_Vel0    > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundslipmode,tangenvel);
    if(slipmode==SLIP_NoSlip  )InteractionCdbcCorrectionT2 <tker,sim2d,SLIP_NoSlip  > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundslipmode,tangenvel);
    if(slipmode==SLIP_FreeSlip)InteractionCdbcCorrectionT2 <tker,sim2d,SLIP_FreeSlip> (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundslipmode,tangenvel);
  }
}

 //==============================================================================
/// Calculates extrapolated data on boundary particles from fluid domain for mDBC.
/// Calcula datos extrapolados en el contorno para mDBC.
//==============================================================================
void JSphCpu::Interaction_CdbcCorrection(TpSlipMode slipmode,const StDivDataCpu &divdata
  ,const tdouble3 *pos,const typecode *code,const unsigned *idp
  ,const tfloat3 *boundnormal,const tfloat3 *motionvel,tfloat4 *velrhop,tsymatrix3d* sigma,const byte *boundslipmode,tfloat3 *tangenvel)
{
  switch(TKernel){
    case KERNEL_Cubic:       Interaction_CdbcCorrectionT <KERNEL_Cubic     > (slipmode,divdata,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundslipmode,tangenvel);  break;
    case KERNEL_Wendland:    Interaction_CdbcCorrectionT <KERNEL_Wendland  > (slipmode,divdata,pos,code,idp,boundnormal,motionvel,velrhop,sigma,boundslipmode,tangenvel);  break;
    default: Run_Exceptioon("Kernel unknown.");
  }
}

//==============================================================================
/// Axis-parallel reflection signs for the restricted fixed-wall fixture.
//==============================================================================
static tdouble3 DynamicPoreWallParity(const tfloat3 &raw){
  const double r2=double(raw.x)*raw.x+double(raw.y)*raw.y+double(raw.z)*raw.z;
  return TDouble3(double(raw.x)*raw.x>.5*r2? -1.: 1.,
    double(raw.y)*raw.y>.5*r2? -1.: 1.,double(raw.z)*raw.z>.5*r2? -1.: 1.);
}

//==============================================================================
/// Admits static parallel axis planes with strictly tangential gravity; private only.
//==============================================================================
void JSphCpu::InitDynamicPoreWallCpu(){
  if(!DynamicPoreWall)return;
  const bool loadedcolumn=(DynamicPorePressure && Simulate2D && DynamicPoreWall
    && !DynamicPoreConductivity && !Gravity.x && !Gravity.y && !Gravity.z
    && HydroMechInitMode==HMINIT_None && HydroMechTopLoadMode==HMLOAD_TopKernelBand
    && HydroMechDrainage && HydroMechDrainageFixedGrid);
  const bool allowcolumnspr=(HydroMechDynamicSeepage && PorosityFeedback && loadedcolumn
    && PeriX && !PeriY && !PeriZ && !ViscoTime);
  if(!DynamicPorePressure || !CaseNpb || TBoundary!=BC_MDBC || !UseNormals || !BoundNormalc || !BoundModec
    || !std::isfinite(Gravity.x) || !std::isfinite(Gravity.y) || !std::isfinite(Gravity.z)
    || (Simulate2D && Gravity.y!=0) || (SoilBoundaryDerivativeSPR && !allowcolumnspr)
    || fabs(double(MassBound)-MassFluid)>4.*FLT_EPSILON*double(MassFluid))
    Run_Exceptioon("Dynamic wall fixture requires equal-dp fixed mDBC FreeSlip planes, finite tangential gravity and its own derivative closure.");
  if(IsDynamicPoreContainerConfig()){
    CheckDynamicPoreContainer(Np,Npb,Posc,Codec,Velrhopc,BoundNormalc,BoundSlipModec,Idpc);
    return;
  }
  const auto component=[](const tdouble3 &v,int a){return(a==0? v.x: (a==1? v.y: v.z));};
  const bool hasgravity=(Gravity.x!=0 || Gravity.y!=0 || Gravity.z!=0);
  int axis=-1;
  bool seen[2]={false,false};
  double plane[2]={0,0};
  for(unsigned p=0;p<Npb;p++){
    const tdouble3 raw=ToTDouble3(BoundNormalc[p]);
    const double len=sqrt(raw.x*raw.x+raw.y*raw.y+raw.z*raw.z);
    if(!CODE_IsFixed(Codec[p]) || !std::isfinite(len) || len<=0
      || Velrhopc[p].x || Velrhopc[p].y || Velrhopc[p].z
      || (BoundSlipModec? TpSlipMode(BoundSlipModec[p]): SlipMode)!=SLIP_FreeSlip)
      Run_Exceptioon("Dynamic wall fixture requires finite stationary FreeSlip wall normals.");
    const tdouble3 n=raw/len,wall=Posc[p]+raw*.5;
    const int a=(fabs(n.x)>.5? 0: (fabs(n.y)>.5? 1: 2));
    if(axis<0)axis=a;
    if(a!=axis || (Simulate2D && a==1))
      Run_Exceptioon("Dynamic wall fixture permits parallel axis planes only, without corners.");
    for(int b=0;b<3;b++)if(b!=axis && fabs(component(n,b))>8.*FLT_EPSILON)
      Run_Exceptioon("Dynamic wall fixture rejects inclined normals.");
    if(hasgravity && (component(ToTDouble3(Gravity),axis)!=0 || Gravity.x*raw.x+Gravity.y*raw.y+Gravity.z*raw.z!=0))
      Run_Exceptioon("Dynamic wall fixture requires gravity exactly tangent to every wall mirror vector.");
    const unsigned side=(component(n,axis)>0? 0: 1);
    const double xp=component(wall,axis);
    if(!std::isfinite(xp) || (seen[side] && fabs(xp-plane[side])>1e-6*Dp))
      Run_Exceptioon("Dynamic wall fixture requires one coplanar face per inward normal direction.");
    if(!seen[side])plane[side]=xp;
    seen[side]=true;
  }
  if(seen[0] && seen[1] && plane[1]-plane[0]<=2.*double(KernelSize))
    Run_Exceptioon("Dynamic wall fixture requires separated opposing mirror supports.");
  if(HydroMechDynamicSeepage && !loadedcolumn && (!seen[0] || !seen[1] || PeriY
    || (axis==0? (!PeriZ || PeriX): (!PeriX || PeriZ))))
    Run_Exceptioon("Experimental dynamic seepage walls require two opposing axis planes and tangential periodicity.");
  if((HydroMechTopLoadMode!=HMLOAD_None || HydroMechDrainage)
    && (!Simulate2D || axis!=2 || !seen[0] || seen[1] || !PeriX || PeriY || PeriZ
      || !std::isfinite(PeriXinc.x) || PeriXinc.x==0 || PeriXinc.y || PeriXinc.z))
    Run_Exceptioon("Dynamic consolidation requires one upward bottom plane and horizontal X periodicity.");
  const tdouble3 inc[3]={PeriXinc,PeriYinc,PeriZinc};
  const bool periodic[3]={PeriX,PeriY,PeriZ};
  for(int a=0;a<3;a++)if(periodic[a] && component(inc[a],axis)!=0)
    Run_Exceptioon("Dynamic wall fixture permits tangential periodic translations only.");
  for(unsigned p=0;p<Npb;p++){
    const double xm=component(Posc[p]+ToTDouble3(BoundNormalc[p]),axis);
    if((seen[0] && xm<=plane[0]) || (seen[1] && xm>=plane[1]))
      Run_Exceptioon("Dynamic wall mirror sample must lie strictly inside the fluid slab.");
  }
}

//==============================================================================
/// Reconstructs fixed quadrature samples, not moving native particle owners.
/// CPU per-receiver normal-head candidate; public plane/gravity guards remain unchanged.
/// J and hydrostatic excess keep their geometry; NoSlip follows the legacy stress/velocity policy.
//==============================================================================
void JSphCpu::ComputeDynamicPoreWallStateCpu(){
  if(!DynamicPoreWall || !NpbOk)return;
  if(Simulate2D && !PeriActive){
    //-Current support participation, not a wet/contact test; no density or J weighting.
    const int n=int(NpbOk);
    #ifdef OMP_USE
      #pragma omp parallel for schedule(guided)
    #endif
    for(int p1=0;p1<n;p1++){
      bool active=false;
      const StNgSearch ngs=nsearch::Init(Posc[p1],false,DivData);
      for(int z=ngs.zini;z<ngs.zfin && !active;z++)for(int y=ngs.yini;y<ngs.yfin && !active;y++){
        const tuint2 range=nsearch::ParticleRange(y,z,ngs,DivData);
        for(unsigned p2=range.x;p2<range.y && !active;p2++)if(CODE_IsFluid(Codec[p2])){
          const double dx=Posc[p1].x-Posc[p2].x,dy=Posc[p1].y-Posc[p2].y,dz=Posc[p1].z-Posc[p2].z;
          const double rr2=dx*dx+dz*dz; //-2-D Darcy and FS use no Y distance.
          const float fsrr2=float(rr2),fx=float(dx),fy=float(dy),fz=float(dz);
          const float forcerr2=fx*fx+fy*fy+fz*fz,umbrellarr2=fx*fx+fz*fz;
          active=(rr2<=double(KernelSize2) && rr2>=ALMOSTZERO)
            || (fsrr2<=KernelSize2 && fsrr2>=ALMOSTZERO)
            || (forcerr2<=KernelSize2 && forcerr2>=ALMOSTZERO)
            || (umbrellarr2<=KernelSize2 && umbrellarr2>=ALMOSTZERO);
        }
      }
      BoundModec[p1]=(active? BMODE_MDBC2: BMODE_MDBC2OFF);
    }
  }
  const double rhow=SoilCte.PoreWaterRho;
  const auto read=[&](unsigned receiver,unsigned p,unsigned c){
    if(c==0)return PoroJc[p];
    if(c==1){
      const tdouble3 q=DynamicPoreWallParity(BoundNormalc[receiver]);
      const tdouble3 normalg=TDouble3(q.x<0? double(Gravity.x): 0.
        ,q.y<0? double(Gravity.y): 0.,q.z<0? double(Gravity.z): 0.);
      const bool hydrostatichead=(normalg.x!=0 || normalg.y!=0 || normalg.z!=0);
      return(hydrostatichead? double(PorePressc[p])-rhow*(normalg.x*Posc[p].x
        +normalg.y*Posc[p].y+normalg.z*Posc[p].z): double(PorePressc[p]));
    }
    if(c<5)return double(c==2? Velrhopc[p].x: (c==3? Velrhopc[p].y: Velrhopc[p].z));
    const tsymatrix3d s=Sigmac[p];
    const double v[6]={s.xx,s.yy,s.zz,s.xy,s.xz,s.yz};return v[c-5];
  };
  const auto write=[&](unsigned p,const double *v,const double *gradx,const double *grady,const double *gradz){
    const tdouble3 q=DynamicPoreWallParity(BoundNormalc[p]);
    const tdouble3 normalg=TDouble3(q.x<0? double(Gravity.x): 0.
      ,q.y<0? double(Gravity.y): 0.,q.z<0? double(Gravity.z): 0.);
    const bool hydrostatichead=(normalg.x!=0 || normalg.y!=0 || normalg.z!=0);
    //-Even excess over this receiver's normal head pairs with its geometric Darcy reflection.
    PoroJc[p]=v[0];PoroThetac[p]=0.;
    PorePressc[p]=float(hydrostatichead? v[1]+rhow*(normalg.x*Posc[p].x
      +normalg.y*Posc[p].y+normalg.z*Posc[p].z): v[1]);
    const bool noslip=((BoundSlipModec? TpSlipMode(BoundSlipModec[p]): SlipMode)==SLIP_NoSlip);
    if(noslip){
      //-Legacy NoSlip stress is extrapolated to the boundary; fixed-wall velocity image is -v_mirror.
      const tfloat3 raw=BoundNormalc[p],imagevel=TFloat3(float(-v[2]),float(-v[3]),float(-v[4]));
      const auto sigmab=[&](unsigned c){return v[c]-(gradx[c]*raw.x+grady[c]*raw.y+gradz[c]*raw.z);};
      Sigmac[p]=TSymMatrix3d(sigmab(5),sigmab(8),sigmab(9),sigmab(6),sigmab(10),sigmab(7));
      if(BoundDerivativeVelc)BoundDerivativeVelc[p]=imagevel;
      if(TangenVelc)TangenVelc[p]=Mdbc2TangenVel(raw,imagevel);
    }
    else{
      Sigmac[p]=TSymMatrix3d(v[5],q.x*q.y*v[8],q.x*q.z*v[9],v[6],q.y*q.z*v[10],v[7]);
      if(BoundDerivativeVelc)BoundDerivativeVelc[p]=TFloat3(float(q.x*v[2]),float(q.y*v[3]),float(q.z*v[4]));
      if(TangenVelc)TangenVelc[p]=TFloat3(float(.5*(1.+q.x)*v[2]),float(.5*(1.+q.y)*v[3]),float(.5*(1.+q.z)*v[4]));
    }
    Velrhopc[p]=TFloat4(0,0,0,RhopZero); //-The physical fixed wall never moves.
    BoundModec[p]=BMODE_MDBC2;
  };
  if(TKernel==KERNEL_Wendland){
    if(Simulate2D)InterpolateBoundaryGhostFieldT<KERNEL_Wendland,true,11>(NpbOk,DivData,Posc,Codec,Velrhopc,BoundNormalc,read,write);
    else InterpolateBoundaryGhostFieldT<KERNEL_Wendland,false,11>(NpbOk,DivData,Posc,Codec,Velrhopc,BoundNormalc,read,write);
  }
  else if(TKernel==KERNEL_Cubic){
    if(Simulate2D)InterpolateBoundaryGhostFieldT<KERNEL_Cubic,true,11>(NpbOk,DivData,Posc,Codec,Velrhopc,BoundNormalc,read,write);
    else InterpolateBoundaryGhostFieldT<KERNEL_Cubic,false,11>(NpbOk,DivData,Posc,Codec,Velrhopc,BoundNormalc,read,write);
  }
  else Run_Exceptioon("Kernel unknown.");
  for(unsigned p=0;p<NpbOk;p++){
    if(Simulate2D && !PeriActive && BoundModec[p]==BMODE_MDBC2OFF)continue;
    if(!std::isfinite(PoroJc[p]) || PoroJc[p]<=1.-double(SoilCte.Porosity)
      || !std::isfinite(PorePressc[p]) || (BoundDerivativeVelc && (!std::isfinite(BoundDerivativeVelc[p].x)
        || !std::isfinite(BoundDerivativeVelc[p].y) || !std::isfinite(BoundDerivativeVelc[p].z))))
      Run_Exceptioon("Dynamic wall left the finite saturated state domain.");
  }
}

//==============================================================================
/// Extends current fluid C after free-surface tracking has rebuilt it.
//==============================================================================
void JSphCpu::ComputeDynamicPoreWallMatrixCpu(){
  if(!DynamicPoreWall || !NpbOk)return;
  const auto read=[&](unsigned,unsigned p,unsigned c){const tmatrix3d m=CorrMatc[p];
    const double v[9]={m.a11,m.a12,m.a13,m.a21,m.a22,m.a23,m.a31,m.a32,m.a33};return v[c];};
  const auto write=[&](unsigned p,const double *v,const double*,const double*,const double*){
    const tdouble3 q=DynamicPoreWallParity(BoundNormalc[p]);
    CorrMatc[p]=TMatrix3d(v[0],q.x*q.y*v[1],q.x*q.z*v[2],q.y*q.x*v[3],v[4],q.y*q.z*v[5],q.z*q.x*v[6],q.z*q.y*v[7],v[8]);
  };
  if(TKernel==KERNEL_Wendland){
    if(Simulate2D)InterpolateBoundaryGhostFieldT<KERNEL_Wendland,true,9>(NpbOk,DivData,Posc,Codec,Velrhopc,BoundNormalc,read,write);
    else InterpolateBoundaryGhostFieldT<KERNEL_Wendland,false,9>(NpbOk,DivData,Posc,Codec,Velrhopc,BoundNormalc,read,write);
  }
  else if(TKernel==KERNEL_Cubic){
    if(Simulate2D)InterpolateBoundaryGhostFieldT<KERNEL_Cubic,true,9>(NpbOk,DivData,Posc,Codec,Velrhopc,BoundNormalc,read,write);
    else InterpolateBoundaryGhostFieldT<KERNEL_Cubic,false,9>(NpbOk,DivData,Posc,Codec,Velrhopc,BoundNormalc,read,write);
  }
  else Run_Exceptioon("Kernel unknown.");
  for(unsigned p=0;p<NpbOk;p++){
    if(Simulate2D && !PeriActive && BoundModec[p]==BMODE_MDBC2OFF)continue;
    const tmatrix3d m=CorrMatc[p];
    const double det=(Simulate2D? m.a11*m.a33-m.a13*m.a31: fmath::Determinant3x3(m));
    if(!std::isfinite(det) || det<=0)Run_Exceptioon("Dynamic wall C reconstruction must remain nonsingular and positive oriented.");
  }
}

//==============================================================================
/// Reads finished native acceleration, never stationary-wall velocity or old Ace.
//==============================================================================
void JSphCpu::ComputeDynamicPoreWallAccelerationCpu(){
  if(!DynamicPoreWall || !NpbOk)return;
  const auto read=[&](unsigned,unsigned p,unsigned c){return(c==0? double(Acec[p].x)+Gravity.x: (c==1? double(Acec[p].y)+Gravity.y: double(Acec[p].z)+Gravity.z));};
  const auto write=[&](unsigned p,const double *v,const double*,const double*,const double*){
    const tdouble3 q=DynamicPoreWallParity(BoundNormalc[p]);
    Acec[p]=TFloat3(float(q.x*v[0]-Gravity.x),float(q.y*v[1]-Gravity.y),float(q.z*v[2]-Gravity.z));
  };
  if(TKernel==KERNEL_Wendland){
    if(Simulate2D)InterpolateBoundaryGhostFieldT<KERNEL_Wendland,true,3>(NpbOk,DivData,Posc,Codec,Velrhopc,BoundNormalc,read,write);
    else InterpolateBoundaryGhostFieldT<KERNEL_Wendland,false,3>(NpbOk,DivData,Posc,Codec,Velrhopc,BoundNormalc,read,write);
  }
  else if(TKernel==KERNEL_Cubic){
    if(Simulate2D)InterpolateBoundaryGhostFieldT<KERNEL_Cubic,true,3>(NpbOk,DivData,Posc,Codec,Velrhopc,BoundNormalc,read,write);
    else InterpolateBoundaryGhostFieldT<KERNEL_Cubic,false,3>(NpbOk,DivData,Posc,Codec,Velrhopc,BoundNormalc,read,write);
  }
  else Run_Exceptioon("Kernel unknown.");
  for(unsigned p=0;p<NpbOk;p++){
    if(Simulate2D && !PeriActive && BoundModec[p]==BMODE_MDBC2OFF)continue;
    if(!std::isfinite(Acec[p].x) || !std::isfinite(Acec[p].y) || !std::isfinite(Acec[p].z))
      Run_Exceptioon("Dynamic wall acceleration reconstruction must remain finite.");
  }
}

