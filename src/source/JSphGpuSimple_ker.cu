//HEAD_DSPH
/*
 <DUALSPHYSICS>  Copyright (c) 2020 by Dr Jose M. Dominguez et al. (see http://dual.sphysics.org/index.php/developers/). 

 EPHYSLAB Environmental Physics Laboratory, Universidade de Vigo, Ourense, Spain.
 School of Mechanical, Aerospace and Civil Engineering, University of Manchester, Manchester, U.K.

 This file is part of DualSPHysics. 

 DualSPHysics is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or (at your option) any later version. 

 DualSPHysics is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details. 

 You should have received a copy of the GNU General Public License, along with DualSPHysics. If not, see <http://www.gnu.org/licenses/>. 
*/

/// \file JSphGpuSimple_ker.cu \brief Implements functions and CUDA kernels for the Particle Interaction and System Update.

#include "JSphGpuSimple_ker.h"
#include "FunSoilMaterial.h"
//#include "Functions.h"
//#include "FunctionsCuda.h"
//#include <math_constants.h>
//#include "JDgKerPrint.h"
//#include "JDgKerPrint_ker.h"
#include <cfloat>

__constant__ StSoilCte SOILSCTE;
__constant__ unsigned SOILSTRAINSOFTENING;
__constant__ unsigned SOILPARTBEGIN;
#define CTE_AVAILABLE
//#include <cuda_profiler_api.h> //mdbr
namespace cusphs{
#include "FunctionsBasic_iker.h"


//##############################################################################
//# Kernels to prepare data before Interaction_Forces().
//##############################################################################
//------------------------------------------------------------------------------
/// Update PosCellg[] according to current position of particles.
/// Actualiza PosCellg[] segun la posicion de las particulas.
//------------------------------------------------------------------------------
__global__ void KerUpdatePosCell(unsigned np,double3 posmin,float poscellsize
  ,const double2 *posxy,const double *posz,float4 *poscell)
{
  const unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<np){
    const double2 rxy=posxy[p];
    const double dx=rxy.x-posmin.x;
    const double dy=rxy.y-posmin.y;
    const double dz=posz[p]-posmin.z;
    const unsigned cx=unsigned(dx/poscellsize);
    const unsigned cy=unsigned(dy/poscellsize);
    const unsigned cz=unsigned(dz/poscellsize);
    const float px=float(dx-(double(poscellsize)*cx));
    const float py=float(dy-(double(poscellsize)*cy));
    const float pz=float(dz-(double(poscellsize)*cz));
    const float pw=__uint_as_float(PSCEL_Code(cx,cy,cz));
    poscell[p]=make_float4(px,py,pz,pw);
  }
}
//==============================================================================
/// Update PosCellg[] according to current position of particles.
/// Actualiza PosCellg[] segun la posicion de las particulas.
//==============================================================================
void UpdatePosCell(unsigned np,tdouble3 posmin,float poscellsize
  ,const double2 *posxy,const double *posz,float4 *poscell,cudaStream_t stm)
{
  const dim3 sgrid=GetSimpleGridSize(np,SPHBSIZE);
  if(np)KerUpdatePosCell <<<sgrid,SPHBSIZE,0,stm>>> (np,Double3(posmin),poscellsize,posxy,posz,poscell);
}

//------------------------------------------------------------------------------
/// Initialises ace array with 0 for bound and gravity for fluid.
/// Inicializa el array ace con 0 para contorno y gravity para fluido.
//------------------------------------------------------------------------------
__global__ void KerInitAceGravity(unsigned np,unsigned npb,float3 gravity,float3 *ace)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<np){
    ace[p]=(p<npb? make_float3(0,0,0): gravity);
  }
}
//==============================================================================
/// Initialises ace array with 0 for bound and gravity for fluid.
/// Inicializa el array ace con 0 para contorno y gravity para fluido.
//==============================================================================
void InitAceGravity(unsigned np,unsigned npb,tfloat3 gravity,float3 *ace,cudaStream_t stm){
  if(np){
    dim3 sgrid=GetSimpleGridSize(np,SPHBSIZE);
    KerInitAceGravity <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,Float3(gravity),ace);
  }
}


//##############################################################################
//# Kernels to run after Interaction_Forces().
//##############################################################################
//------------------------------------------------------------------------------
/// Sets v[].y to zero.
/// Pone v[].y a cero.
//------------------------------------------------------------------------------
__global__ void KerResety(unsigned n,unsigned ini,float3 *v)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n)v[p+ini].y=0;
}
//==============================================================================
/// Sets v[].y to zero.
/// Pone v[].y a cero.
//==============================================================================
void Resety(unsigned n,unsigned ini,float3 *v,cudaStream_t stm){
  if(n){
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    KerResety <<<sgrid,SPHBSIZE,0,stm>>> (n,ini,v);
  }
}
//##############################################################################
//# Kernels for ComputeStep (vel & rhop).
//# Kernels para ComputeStep (vel & rhop).
//##############################################################################
//------------------------------------------------------------------------------
/// Computes new values for Pos, Check, Vel and Ros (using Verlet).
/// The value of Vel always set to be reset.
///
/// Calcula nuevos valores de  Pos, Check, Vel y Rhop (usando Verlet).
/// El valor de Vel para bound siempre se pone a cero.
//------------------------------------------------------------------------------
template<bool floating,bool shift,bool inout,TpDPCtes dpctes> __global__ void KerComputeStepVerlet
  (unsigned n,unsigned npb,float rhopzero,float rhopoutmin,float rhopoutmax
  ,const float4 *velrhop1,const float4 *velrhop2
  ,const double2 *sigma2,const float *kplastic2,const float *kplasticcurrent,const float2 *rsigma
  ,const float *ar,const float3 *ace,const float4 *shiftposfs,const float3 *indirvel,const float4 *nopenshift
  ,TpMdbc2Mode mdbc2
  ,double dt,double dt205,double dt2,float3 gravity
  ,double2 *movxy,double *movz,typecode *code,float4 *velrhopnew
  ,double2 *sigma,float *kplastic,float *kplasticdk,unsigned *materialerror,bool requireelastic)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    const float kplasticcurr=kplasticcurrent[p]; //-Read before writing the output M1 layer.
    if(p<npb){ //-Particles: Fixed & Moving.
      //float rrhop=float(double(velrhop2[p].w)+dt2*ar[p]);
      //rrhop=(rrhop<rhopzero? rhopzero: rrhop); //-To prevent absorption of fluid particles by boundaries. | Evita q las boundary absorvan a las fluidas.
      float rrhop=rhopzero;
      velrhopnew[p]=make_float4(0,0,0,rrhop);
      //--mdbr--has been swapped return back
      sigma[p*3]=sigma2[p*3];
      sigma[p*3+1]=sigma2[p*3+1];
      sigma[p*3+2]=sigma2[p*3+2];
      kplastic[p]=kplastic2[p];
    }
    else{ //-Particles: Floating & Fluid.
      const typecode rcode=code[p];
      //-Updates density.
      const float4 rvelrhop2=velrhop2[p];
      const float rhopnew=float(double(velrhop2[p].w)+dt2*ar[p]);
      float4 rvel1=velrhop1[p];
      //==== mdbr ===
      double2 sigmanew_xx_xy=sigma2[p*3];
      double2 sigmanew_xz_yy=sigma2[p*3+1]; 
      double2 sigmanew_yz_zz=sigma2[p*3+2];
      float kplasticnew=kplastic2[p];
      if(!floating || CODE_IsFluid(rcode)){ //-Particles: Fluid.
        //-Calculate displacement. | Calcula desplazamiento.
        const float3 race=ace[p];
        const double acegrx=double(race.x)+gravity.x;
        const double acegry=double(race.y)+gravity.y;
        const double acegrz=double(race.z)+gravity.z;
        double dx=double(rvel1.x)*dt + acegrx*dt205;
        double dy=double(rvel1.y)*dt + acegry*dt205;
        double dz=double(rvel1.z)*dt + acegrz*dt205;
        if(shift){
          const float4 rshiftpos=shiftposfs[p];
          dx+=double(rshiftpos.x);
          dy+=double(rshiftpos.y);
          dz+=double(rshiftpos.z);
        }
        bool outrhop=(rhopnew<rhopoutmin || rhopnew>rhopoutmax);
        //-Calculate velocity & density. | Calcula velocidad y densidad.
        float4 rvelrhopnew=make_float4(
          float(double(rvelrhop2.x) + acegrx*dt2),
          float(double(rvelrhop2.y) + acegry*dt2),
          float(double(rvelrhop2.z) + acegrz*dt2),
          rhopnew);
        if(mdbc2==MDBC2_NoPen && nopenshift && nopenshift[p].w>5.f){
          if(nopenshift[p].x!=0.f){
            rvelrhopnew.x=rvel1.x+nopenshift[p].x;
            dx=double(rvelrhopnew.x)*dt;
          }
          if(nopenshift[p].y!=0.f){
            rvelrhopnew.y=rvel1.y+nopenshift[p].y;
            dy=double(rvelrhopnew.y)*dt;
          }
          if(nopenshift[p].z!=0.f){
            rvelrhopnew.z=rvel1.z+nopenshift[p].z;
            dz=double(rvelrhopnew.z)*dt;
          }
        }
        //-Calculate elastic stress
        double2 sigma_e_xx_xy=make_double2(0,0);double2 sigma_e_xz_yy=make_double2(0,0);double2 sigma_e_yz_zz=make_double2(0,0);
        float kplasticold = kplastic2[p];
        sigma_e_xx_xy.x = double(sigma2[p*3].x)   + rsigma[p*3].x   * dt2;
        sigma_e_xz_yy.y = double(sigma2[p*3+1].y) + rsigma[p*3+1].y * dt2;
        sigma_e_yz_zz.y = double(sigma2[p*3+2].y) + rsigma[p*3+2].y * dt2;
        sigma_e_xx_xy.y = double(sigma2[p*3].y)   + rsigma[p*3].y   * dt2;
        sigma_e_yz_zz.x = double(sigma2[p*3+2].x) + rsigma[p*3+2].x * dt2;
        sigma_e_xz_yy.x = double(sigma2[p*3+1].x) + rsigma[p*3+1].x * dt2;
        const bool usesoftening=(SOILSTRAINSOFTENING!=0);
        const fsoil::Status status=fsoil::ReturnMaterial(sigma_e_xx_xy,sigma_e_xz_yy,sigma_e_yz_zz,kplasticold,SOILSCTE
          ,dpctes,usesoftening,(SOILPARTBEGIN && usesoftening),sigmanew_xx_xy,sigmanew_xz_yy,sigmanew_yz_zz,kplasticnew);
        if(!fsoil::CommitAllowed(status) || (requireelastic && status!=fsoil::Status::Elastic)){atomicOr(materialerror,1u<<unsigned(status));return;}

        //-Restore data of inout particles.
        if(inout && CODE_IsFluidInout(rcode)){
          outrhop=false;
          rvelrhopnew=rvelrhop2;
          const float3 vd=indirvel[CODE_GetIzoneFluidInout(rcode)];
          if(vd.x!=FLT_MAX){
            const float v=rvel1.x*vd.x + rvel1.y*vd.y + rvel1.z*vd.z;
            dx=double(v*vd.x) * dt;
            dy=double(v*vd.y) * dt;
            dz=double(v*vd.z) * dt;
          }
          else{
            dx=double(rvel1.x) * dt;
            dy=double(rvel1.y) * dt;
            dz=double(rvel1.z) * dt;
          }
        }
        //-Update particle data.
        movxy[p]=make_double2(dx,dy);
        movz[p]=dz;
        if(outrhop){ //-Only brands as excluded normal particles (not periodic). | Solo marca como excluidas las normales (no periodicas).
          if(CODE_IsNormal(rcode))code[p]=CODE_SetOutRhop(rcode);
        }
        velrhopnew[p]=rvelrhopnew;
      }
      else{ //-Particles: Floating.
        rvel1.w=(rhopnew<rhopzero? rhopzero: rhopnew); //-To prevent absorption of fluid particles by boundaries. | Evita q las floating absorvan a las fluidas.
        velrhopnew[p]=rvel1;
      }
      //-Update stress/equivelant plastic strain
      sigma[p*3]  =sigmanew_xx_xy;
      sigma[p*3+1]=sigmanew_xz_yy;
      sigma[p*3+2]=sigmanew_yz_zz;
      if(kplasticdk)kplasticdk[p]+=fmaxf(kplasticnew-kplasticcurr,0.f);
      kplastic[p] = kplasticnew;
    }
  }
}
template<TpDPCtes dpctes> void ComputeStepVerletT(bool floating,bool shift,bool inout,TpMdbc2Mode mdbc2,unsigned np,unsigned npb
  ,const float4 *velrhop1,const float4 *velrhop2
  ,const tsymatrix3d *sigma2,const float*kplastic2,const float *kplasticcurrent,const tsymatrix3f *rsigma
  ,const float *ar,const float3 *ace,const float4 *shiftposfs,const float3 *indirvel,const float4 *nopenshift
  ,double dt,double dt2,float rhopzero,float rhopoutmin,float rhopoutmax,tfloat3 gravity
  ,typecode *code,double2 *movxy,double *movz,float4 *velrhopnew
  ,tsymatrix3d *sigmanew,float *kplasticnew,float *kplasticdk
  ,cudaStream_t stm,unsigned *materialerror,bool requireelastic)
  {
    double dt205=(0.5*dt*dt);
  if(np){
    dim3 sgrid=GetSimpleGridSize(np,SPHBSIZE);
    if(inout){      const bool tinout=true;
      if(shift){    const bool shift=true;
        if(floating)KerComputeStepVerlet<true ,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,rhopzero,rhopoutmin,rhopoutmax,velrhop1,velrhop2,(const double2*)sigma2,kplastic2,kplasticcurrent,(const float2*)rsigma,ar,ace,shiftposfs,indirvel,nopenshift,mdbc2,dt,dt205,dt2,Float3(gravity),movxy,movz,code,velrhopnew,(double2*)sigmanew,kplasticnew,kplasticdk,materialerror,requireelastic);
        else        KerComputeStepVerlet<false,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,rhopzero,rhopoutmin,rhopoutmax,velrhop1,velrhop2,(const double2*)sigma2,kplastic2,kplasticcurrent,(const float2*)rsigma,ar,ace,shiftposfs,indirvel,nopenshift,mdbc2,dt,dt205,dt2,Float3(gravity),movxy,movz,code,velrhopnew,(double2*)sigmanew,kplasticnew,kplasticdk,materialerror,requireelastic);
      }else{        const bool shift=false;
        if(floating)KerComputeStepVerlet<true ,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,rhopzero,rhopoutmin,rhopoutmax,velrhop1,velrhop2,(const double2*)sigma2,kplastic2,kplasticcurrent,(const float2*)rsigma,ar,ace,shiftposfs,indirvel,nopenshift,mdbc2,dt,dt205,dt2,Float3(gravity),movxy,movz,code,velrhopnew,(double2*)sigmanew,kplasticnew,kplasticdk,materialerror,requireelastic);
        else        KerComputeStepVerlet<false,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,rhopzero,rhopoutmin,rhopoutmax,velrhop1,velrhop2,(const double2*)sigma2,kplastic2,kplasticcurrent,(const float2*)rsigma,ar,ace,shiftposfs,indirvel,nopenshift,mdbc2,dt,dt205,dt2,Float3(gravity),movxy,movz,code,velrhopnew,(double2*)sigmanew,kplasticnew,kplasticdk,materialerror,requireelastic);
      }
    }
    else{           const bool tinout=false;
      if(shift){    const bool shift=true;
        if(floating)KerComputeStepVerlet<true ,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,rhopzero,rhopoutmin,rhopoutmax,velrhop1,velrhop2,(const double2*)sigma2,kplastic2,kplasticcurrent,(const float2*)rsigma,ar,ace,shiftposfs,indirvel,nopenshift,mdbc2,dt,dt205,dt2,Float3(gravity),movxy,movz,code,velrhopnew,(double2*)sigmanew,kplasticnew,kplasticdk,materialerror,requireelastic);
        else        KerComputeStepVerlet<false,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,rhopzero,rhopoutmin,rhopoutmax,velrhop1,velrhop2,(const double2*)sigma2,kplastic2,kplasticcurrent,(const float2*)rsigma,ar,ace,shiftposfs,indirvel,nopenshift,mdbc2,dt,dt205,dt2,Float3(gravity),movxy,movz,code,velrhopnew,(double2*)sigmanew,kplasticnew,kplasticdk,materialerror,requireelastic);
      }else{        const bool shift=false;
        if(floating)KerComputeStepVerlet<true ,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,rhopzero,rhopoutmin,rhopoutmax,velrhop1,velrhop2,(const double2*)sigma2,kplastic2,kplasticcurrent,(const float2*)rsigma,ar,ace,shiftposfs,indirvel,nopenshift,mdbc2,dt,dt205,dt2,Float3(gravity),movxy,movz,code,velrhopnew,(double2*)sigmanew,kplasticnew,kplasticdk,materialerror,requireelastic);
        else        KerComputeStepVerlet<false,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,rhopzero,rhopoutmin,rhopoutmax,velrhop1,velrhop2,(const double2*)sigma2,kplastic2,kplasticcurrent,(const float2*)rsigma,ar,ace,shiftposfs,indirvel,nopenshift,mdbc2,dt,dt205,dt2,Float3(gravity),movxy,movz,code,velrhopnew,(double2*)sigmanew,kplasticnew,kplasticdk,materialerror,requireelastic);
      }
    }
  }  
  }
//==============================================================================
/// Updates particles according to forces and dt using Verlet. 
/// Actualizacion de particulas segun fuerzas y dt usando Verlet.
//==============================================================================
void ComputeStepVerlet(bool floating,bool shift,bool inout,TpDPCtes dpctes,TpMdbc2Mode mdbc2,unsigned np,unsigned npb
  ,const float4 *velrhop1,const float4 *velrhop2
  ,const tsymatrix3d *sigma2,const float*kplastic2,const float *kplasticcurrent,const tsymatrix3f *rsigma
  ,const float *ar,const float3 *ace,const float4 *shiftposfs,const float3 *indirvel,const float4 *nopenshift
  ,double dt,double dt2,float rhopzero,float rhopoutmin,float rhopoutmax,tfloat3 gravity
  ,typecode *code,double2 *movxy,double *movz,float4 *velrhopnew
  ,tsymatrix3d *sigmanew,float *kplasticnew,float *kplasticdk
  ,cudaStream_t stm,unsigned *materialerror,bool requireelastic)
{
  //cudaProfilerStart();//mdbr
  switch(dpctes){
	  case DP_C:{ const TpDPCtes tdpctes=DP_C;
		  ComputeStepVerletT<tdpctes>(floating,shift,inout,mdbc2,np,npb,velrhop1,velrhop2,sigma2,kplastic2,kplasticcurrent,rsigma,ar,ace,shiftposfs,indirvel,nopenshift
      ,dt,dt2,rhopzero,rhopoutmin,rhopoutmax, gravity,code,movxy,movz,velrhopnew,sigmanew,kplasticnew,kplasticdk,stm,materialerror,requireelastic);
	  }break;
	  case DP_MC:{ const TpDPCtes tdpctes=DP_MC;
		  ComputeStepVerletT<tdpctes>(floating,shift,inout,mdbc2,np,npb,velrhop1,velrhop2,sigma2,kplastic2,kplasticcurrent,rsigma,ar,ace,shiftposfs,indirvel,nopenshift
      ,dt,dt2,rhopzero,rhopoutmin,rhopoutmax, gravity,code,movxy,movz,velrhopnew,sigmanew,kplasticnew,kplasticdk,stm,materialerror,requireelastic);
	  }break;
	  case DP_PS:{ const TpDPCtes tdpctes=DP_PS;
		  ComputeStepVerletT<tdpctes>(floating,shift,inout,mdbc2,np,npb,velrhop1,velrhop2,sigma2,kplastic2,kplasticcurrent,rsigma,ar,ace,shiftposfs,indirvel,nopenshift
      ,dt,dt2,rhopzero,rhopoutmin,rhopoutmax, gravity,code,movxy,movz,velrhopnew,sigmanew,kplasticnew,kplasticdk,stm,materialerror,requireelastic);
	  }break;
	  default: throw "DP Constants unknown at ComputeStepVerlet().";
  }
  //cudaProfilerStop();//mdbr
}

//------------------------------------------------------------------------------
/// Computes new values for Pos, Check, Vel and Ros (used with Symplectic-Predictor).
/// Calcula los nuevos valores de Pos, Vel y Rhop (usando para Symplectic-Predictor).
//------------------------------------------------------------------------------
//-Cache native mixture density from stage J; the existing J kernel still owns its commit.
template<bool corrector> static __device__ __forceinline__ bool KerPorosityRhopCache
  (StPorosityRhopState state,unsigned p,double dt,float rho0,float minimum,float maximum,float &cache)
{
  const double jstage=state.j[p];
  double value=jstage;
  if(corrector){value=state.jn[p];value+=dt*jstage*state.theta[p];}
  const double rhow=double(SOILSCTE.PoreWaterRho);
  const double rhot=rhow+(double(rho0)-rhow)/value;
  const bool out=(!isfinite(value) || value<=1.-double(SOILSCTE.Porosity)
    || !isfinite(rhot) || rhot<=0 || rhot<minimum || rhot>maximum);
  cache=float(rhot);
  return(out || !isfinite(cache) || cache<=0.f);
}

template<bool floating,bool shift,bool inout,TpDPCtes dpctes> __global__ void KerComputeStepSymplecticPre
  (unsigned n,unsigned npb
  ,const float4 *velrhoppre,const float *ar,const float3 *ace,const float4 *shiftposfs
  ,const double2 *sigmapre,const float *kplasticpre,const float2 *rsigma
  ,const float3 *indirvel,double dtm,float rhopzero,float rhopoutmin,float rhopoutmax,float3 gravity
  ,typecode *code,double2 *movxy,double *movz,float4 *velrhop
  ,double2 *sigma,float *kplastic,float *kplasticdk,StPorosityRhopState porostate,unsigned *materialerror,bool requireelastic)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    if(p<npb){ //-Particles: Fixed & Moving.
      //==== mdbr ==boundary keeps the same No update
      float4 rvelrhop=velrhoppre[p];
      //rvelrhop.w=float(double(rvelrhop.w)+dtm*ar[p]);
      //rvelrhop.w=(rvelrhop.w<rhopzero? rhopzero: rvelrhop.w); //-To prevent absorption of fluid particles by boundaries. | Evita que las boundary absorvan a las fluidas.
      rvelrhop.w=rhopzero;
      velrhop[p]=rvelrhop;
      sigma[p*3]=sigmapre[p*3];
      sigma[p*3+1]=sigmapre[p*3+1];
      sigma[p*3+2]=sigmapre[p*3+2];
      //kplastic[p] = kplasticpre[p];
    }
    else{ //-Particles: Floating & Fluid.
      const typecode rcode=code[p];
      //-Updates density.
      const float4 rvelrhoppre=velrhoppre[p];
      float4 rvelrhopnew=rvelrhoppre;
      const bool feedbackj=(porostate.j && CODE_IsFluid(rcode));
      bool feedbackout=false;
      if(feedbackj)feedbackout=KerPorosityRhopCache<false>(porostate,p,dtm,rhopzero,rhopoutmin,rhopoutmax,rvelrhopnew.w);
      else rvelrhopnew.w=float(double(rvelrhoppre.w)+dtm*ar[p]);
      //==== mdbr ==
      double2 sigmapre_xx_xy=sigmapre[p*3];
	  double2 sigmapre_xz_yy=sigmapre[p*3+1];
	  double2 sigmapre_yz_zz=sigmapre[p*3+2];
      double2 sigmanew_xx_xy=sigmapre_xx_xy;double2 sigmanew_xz_yy=sigmapre_xz_yy; double2 sigmanew_yz_zz=sigmapre_yz_zz;      
      float kplasticnew=0;
      if(!floating || CODE_IsFluid(rcode)){ //-Particles: Fluid.
        //-Calculate displacement. | Calcula desplazamiento.
        double dx=double(rvelrhoppre.x)*dtm;
        double dy=double(rvelrhoppre.y)*dtm;
        double dz=double(rvelrhoppre.z)*dtm;
        if(shift){
          const float4 rshiftpos=shiftposfs[p];
          dx+=double(rshiftpos.x);
          dy+=double(rshiftpos.y);
          dz+=double(rshiftpos.z);
        }
        bool outrhop=(feedbackj? feedbackout: (rvelrhopnew.w<rhopoutmin || rvelrhopnew.w>rhopoutmax));
        //-Calculate velocity & density. | Calcula velocidad y densidad.
        const float3 race=ace[p];
        rvelrhopnew.x=float(double(rvelrhoppre.x) + (double(race.x)+gravity.x) * dtm);
        rvelrhopnew.y=float(double(rvelrhoppre.y) + (double(race.y)+gravity.y) * dtm);
        rvelrhopnew.z=float(double(rvelrhoppre.z) + (double(race.z)+gravity.z) * dtm);
        //-Calculate elastic stress
        float2 rsigma_xx_xy=rsigma[p*3];
	    float2 rsigma_xz_yy=rsigma[p*3+1];
        float2 rsigma_yz_zz=rsigma[p*3+2];
        double2 sigma_e_xx_xy=make_double2(0,0);   double2 sigma_e_xz_yy=make_double2(0,0);   double2 sigma_e_yz_zz=make_double2(0,0);
        float kplasticold = kplasticpre[p];
        sigma_e_xx_xy.x = double(sigmapre_xx_xy.x) + double(rsigma_xx_xy.x) * dtm;
        sigma_e_xz_yy.y = double(sigmapre_xz_yy.y) + double(rsigma_xz_yy.y) * dtm;
        sigma_e_yz_zz.y = double(sigmapre_yz_zz.y) + double(rsigma_yz_zz.y) * dtm;
        sigma_e_xx_xy.y = double(sigmapre_xx_xy.y) + double(rsigma_xx_xy.y) * dtm;
        sigma_e_yz_zz.x = double(sigmapre_yz_zz.x) + double(rsigma_yz_zz.x) * dtm;
        sigma_e_xz_yy.x = double(sigmapre_xz_yy.x) + double(rsigma_xz_yy.x) * dtm;
        const bool usesoftening=(SOILSTRAINSOFTENING!=0);
        const fsoil::Status status=fsoil::ReturnMaterial(sigma_e_xx_xy,sigma_e_xz_yy,sigma_e_yz_zz,kplasticold,SOILSCTE
          ,dpctes,usesoftening,(SOILPARTBEGIN && usesoftening),sigmanew_xx_xy,sigmanew_xz_yy,sigmanew_yz_zz,kplasticnew);
        if(!fsoil::CommitAllowed(status) || (requireelastic && status!=fsoil::Status::Elastic)){atomicOr(materialerror,1u<<unsigned(status));return;}
		kplasticnew=kplasticold;//Update in the corrector step
        //-Restore data of inout particles.
        if(inout && CODE_IsFluidInout(rcode)){
          outrhop=false;
          rvelrhopnew=rvelrhoppre;
          const float3 vd=indirvel[CODE_GetIzoneFluidInout(rcode)];
          if(vd.x!=FLT_MAX){
            const float v=rvelrhopnew.x*vd.x + rvelrhopnew.y*vd.y + rvelrhopnew.z*vd.z;
            dx=double(v*vd.x) * dtm;
            dy=double(v*vd.y) * dtm;
            dz=double(v*vd.z) * dtm;
          }
        }
        //-Update particle data.
        movxy[p]=make_double2(dx,dy);
        movz[p]=dz;
        if(outrhop){ //-Only brands as excluded normal particles (not periodic). | Solo marca como excluidas las normales (no periodicas).
          if(CODE_IsNormal(rcode))code[p]=CODE_SetOutRhop(rcode);
        }
      }
      else{ //-Particles: Floating.
        rvelrhopnew.w=(rvelrhopnew.w<rhopzero? rhopzero: rvelrhopnew.w); //-To prevent absorption of fluid particles by boundaries. | Evita q las floating absorvan a las fluidas.
      }
      //-Stores new velocity and density.
      velrhop[p]=rvelrhopnew;
      //-Store new stress and kappa
      sigma[p*3]  =sigmanew_xx_xy;
      sigma[p*3+1]=sigmanew_xz_yy;
      sigma[p*3+2]=sigmanew_yz_zz;
      kplastic[p]=kplasticnew;
    }
  }
}
//==============================================================================
template<TpDPCtes dpctes> void ComputeStepSymplecticPreT(bool floating,bool shift,bool inout,unsigned np,unsigned npb
  ,const float4 *velrhoppre,const float *ar,const float3 *ace,const float4 *shiftposfs
  ,const tsymatrix3d *sigmapre,const float *kplasticpre,const tsymatrix3f *rsigma
  ,const float3 *indirvel,double dtm,float rhopzero,float rhopoutmin,float rhopoutmax,tfloat3 gravity
  ,typecode *code,double2 *movxy,double *movz,float4 *velrhop
  ,tsymatrix3d *sigma,float *kplastic,float *kplasticdk
  ,cudaStream_t stm,StPorosityRhopState porostate,unsigned *materialerror,bool requireelastic)
{
	if(np){
    dim3 sgrid=GetSimpleGridSize(np,SPHBSIZE);
    if(inout){      const bool tinout=true;
      if(shift){    const bool shift=true;
        if(floating)KerComputeStepSymplecticPre<true ,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,dtm,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
        else        KerComputeStepSymplecticPre<false,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,dtm,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
      }else{        const bool shift=false;
        if(floating)KerComputeStepSymplecticPre<true ,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,dtm,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
        else        KerComputeStepSymplecticPre<false,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,dtm,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
      }
    }
    else{           const bool tinout=false;
      if(shift){    const bool shift=true;
        if(floating)KerComputeStepSymplecticPre<true ,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,dtm,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
        else        KerComputeStepSymplecticPre<false,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,dtm,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
      }else{        const bool shift=false;
        if(floating)KerComputeStepSymplecticPre<true ,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,dtm,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
        else        KerComputeStepSymplecticPre<false,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,dtm,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
      }
    }
  }
}
//==============================================================================
/// Updates particles using Symplectic-Predictor.
/// Actualizacion de particulas usando Symplectic-Predictor.
//==============================================================================   
void ComputeStepSymplecticPre(bool floating,bool shift,bool inout,TpDPCtes dpctes,unsigned np,unsigned npb
  ,const float4 *velrhoppre,const float *ar,const float3 *ace,const float4 *shiftposfs
  ,const tsymatrix3d *sigmapre,const float *kplasticpre,const tsymatrix3f *rsigma
  ,const float3 *indirvel,double dtm,float rhopzero,float rhopoutmin,float rhopoutmax,tfloat3 gravity
  ,typecode *code,double2 *movxy,double *movz,float4 *velrhop
  ,tsymatrix3d *sigma,float *kplastic,float *kplasticdk
  ,cudaStream_t stm,StPorosityRhopState porostate,unsigned *materialerror,bool requireelastic)
{
  //cudaProfilerStart();//mdbr
    switch(dpctes){
	  case DP_C:{ const TpDPCtes tdpctes=DP_C;
		  ComputeStepSymplecticPreT<tdpctes>(floating,shift,inout,np,npb,velrhoppre,ar,ace,shiftposfs,sigmapre,kplasticpre,rsigma
            ,indirvel,dtm,rhopzero,rhopoutmin,rhopoutmax,gravity,code,movxy,movz,velrhop,sigma,kplastic,kplasticdk,stm,porostate,materialerror,requireelastic);
	  }break;
	  case DP_MC:{ const TpDPCtes tdpctes=DP_MC;
		  ComputeStepSymplecticPreT<tdpctes>(floating,shift,inout,np,npb,velrhoppre,ar,ace,shiftposfs,sigmapre,kplasticpre,rsigma
            ,indirvel,dtm,rhopzero,rhopoutmin,rhopoutmax,gravity,code,movxy,movz,velrhop,sigma,kplastic,kplasticdk,stm,porostate,materialerror,requireelastic);
	  }break;
	  case DP_PS:{ const TpDPCtes tdpctes=DP_PS;
		  ComputeStepSymplecticPreT<tdpctes>(floating,shift,inout,np,npb,velrhoppre,ar,ace,shiftposfs,sigmapre,kplasticpre,rsigma
            ,indirvel,dtm,rhopzero,rhopoutmin,rhopoutmax,gravity,code,movxy,movz,velrhop,sigma,kplastic,kplasticdk,stm,porostate,materialerror,requireelastic);
	  }break;
	  default: throw "DP Constants unknown at ComputeStepSymplecticPre().";
  }
  //cudaProfilerStop();//mdbr
}

//------------------------------------------------------------------------------
/// Computes new values for Pos, Check, Vel and Ros (using Verlet).
/// The value of Vel always set to be reset.
///
/// Calcula los nuevos valores de Pos, Vel y Rhop (usandopara Symplectic-Corrector).
/// Pone vel de contorno a cero.
//------------------------------------------------------------------------------
template<bool floating,bool shift,bool inout,TpDPCtes dpctes> __global__ void KerComputeStepSymplecticCor
  (unsigned n,unsigned npb
  ,const float4 *velrhoppre,const float *ar,const float3 *ace,const float4 *shiftposfs
  ,const double2 *sigmapre,const float *kplasticpre,const float2 *rsigma
  ,const float3 *indirvel,const float4 *nopenshift,TpMdbc2Mode mdbc2,double dtm,double dt,float rhopzero,float rhopoutmin,float rhopoutmax,float3 gravity
  ,typecode *code,double2 *movxy,double *movz,float4 *velrhop
  ,double2 *sigma,float *kplastic,float *kplasticdk,StPorosityRhopState porostate,unsigned *materialerror,bool requireelastic)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    if(p<npb){ //-Particles: Fixed & Moving.
      //double epsilon_rdot=(-double(ar[p])/double(velrhop[p].w))*dt;
      //float rrhop=float(double(velrhoppre[p].w) * (2.-epsilon_rdot)/(2.+epsilon_rdot));
      //rrhop=(rrhop<rhopzero? rhopzero: rrhop); //-To prevent absorption of fluid particles by boundaries. | Evita q las boundary absorvan a las fluidas.
      float rrhop=rhopzero;
      velrhop[p]=make_float4(0,0,0,rrhop);
      //==== mdbr == No Update, Calculated in BoundCorr
      //kplastic[p] = kplasticpre[p];
    }
    else{ //-Particles: Floating & Fluid.
      const typecode rcode=code[p];
      //-Updates density.
      //const double epsilon_rdot=(-double(ar[p])/double(velrhop[p].w))*dt;
      //const float4 rvelrhoppre=velrhoppre[p];
      //float4 rvelrhopnew=rvelrhoppre;
      //rvelrhopnew.w=float(double(rvelrhoppre.w) * (2.-epsilon_rdot)/(2.+epsilon_rdot));

      const float4 rvelrhoppre=velrhoppre[p];
      float4 rvelrhopnew=rvelrhoppre;
      //rvelrhopnew.w=float(double(rvelrhoppre.w) * (2.-epsilon_rdot)/(2.+epsilon_rdot));
      const bool feedbackj=(porostate.j && CODE_IsFluid(rcode));
      bool feedbackout=false;
      if(feedbackj)feedbackout=KerPorosityRhopCache<true>(porostate,p,dt,rhopzero,rhopoutmin,rhopoutmax,rvelrhopnew.w);
      else rvelrhopnew.w=float(double(rvelrhoppre.w)+dt*ar[p]);
      //==== mdbr ==
     //==== mdbr ==
      double2 sigmapre_xx_xy=sigmapre[p*3];
      double2 sigmapre_xz_yy=sigmapre[p*3+1];
	  double2 sigmapre_yz_zz=sigmapre[p*3+2];
      double2 sigmanew_xx_xy=sigmapre_xx_xy;double2 sigmanew_xz_yy=sigmapre_xz_yy; double2 sigmanew_yz_zz=sigmapre_yz_zz;      
      float kplasticnew=0;
      if(!floating || CODE_IsFluid(rcode)){//-Particles: Fluid.
        //-Calculate velocity. | Calcula velocidad.
        const float3 race=ace[p];
        rvelrhopnew.x=float(double(rvelrhoppre.x) + (double(race.x)+gravity.x) * dt);
        rvelrhopnew.y=float(double(rvelrhoppre.y) + (double(race.y)+gravity.y) * dt);
        rvelrhopnew.z=float(double(rvelrhoppre.z) + (double(race.z)+gravity.z) * dt);
        //-Calculate displacement. | Calcula desplazamiento.
        double dx=(double(rvelrhoppre.x)+double(rvelrhopnew.x)) * dtm;
        double dy=(double(rvelrhoppre.y)+double(rvelrhopnew.y)) * dtm;
        double dz=(double(rvelrhoppre.z)+double(rvelrhopnew.z)) * dtm;
        if(mdbc2==MDBC2_NoPen && nopenshift && nopenshift[p].w>5.f){
          if(nopenshift[p].x!=0.f){
            rvelrhopnew.x=rvelrhoppre.x+nopenshift[p].x;
            dx=double(rvelrhopnew.x)*dt;
          }
          if(nopenshift[p].y!=0.f){
            rvelrhopnew.y=rvelrhoppre.y+nopenshift[p].y;
            dy=double(rvelrhopnew.y)*dt;
          }
          if(nopenshift[p].z!=0.f){
            rvelrhopnew.z=rvelrhoppre.z+nopenshift[p].z;
            dz=double(rvelrhopnew.z)*dt;
          }
        }
        if(shift){
          const float4 rshiftpos=shiftposfs[p];
          dx+=double(rshiftpos.x);
          dy+=double(rshiftpos.y);
          dz+=double(rshiftpos.z);
        }
        bool outrhop=(feedbackj? feedbackout: (rvelrhopnew.w<rhopoutmin || rvelrhopnew.w>rhopoutmax));
        //-Calculate elastic stress
        double2 sigmapre_xx_xy=sigmapre[p*3];
	    double2 sigmapre_xz_yy=sigmapre[p*3+1];
	    double2 sigmapre_yz_zz=sigmapre[p*3+2];
        float2 rsigma_xx_xy=rsigma[p*3];
	    float2 rsigma_xz_yy=rsigma[p*3+1];
	    float2 rsigma_yz_zz=rsigma[p*3+2];
        double2 sigma_e_xx_xy=make_double2(0,0);double2 sigma_e_xz_yy=make_double2(0,0);double2 sigma_e_yz_zz=make_double2(0,0);
        float kplasticold = kplasticpre[p];
        sigma_e_xx_xy.x = double(sigmapre_xx_xy.x) + double(rsigma_xx_xy.x) * dt;
        sigma_e_xz_yy.y = double(sigmapre_xz_yy.y) + double(rsigma_xz_yy.y) * dt;
        sigma_e_yz_zz.y = double(sigmapre_yz_zz.y) + double(rsigma_yz_zz.y) * dt;
        sigma_e_xx_xy.y = double(sigmapre_xx_xy.y) + double(rsigma_xx_xy.y) * dt;
        sigma_e_yz_zz.x = double(sigmapre_yz_zz.x) + double(rsigma_yz_zz.x) * dt;
        sigma_e_xz_yy.x = double(sigmapre_xz_yy.x) + double(rsigma_xz_yy.x) * dt;
        const bool usesoftening=(SOILSTRAINSOFTENING!=0);
        const fsoil::Status status=fsoil::ReturnMaterial(sigma_e_xx_xy,sigma_e_xz_yy,sigma_e_yz_zz,kplasticold,SOILSCTE
          ,dpctes,usesoftening,(SOILPARTBEGIN && usesoftening),sigmanew_xx_xy,sigmanew_xz_yy,sigmanew_yz_zz,kplasticnew);
        if(!fsoil::CommitAllowed(status) || (requireelastic && status!=fsoil::Status::Elastic)){atomicOr(materialerror,1u<<unsigned(status));return;}
        //-Restore data of inout particles.
        if(inout && CODE_IsFluidInout(rcode)){
          outrhop=false;
          rvelrhopnew=rvelrhoppre;
          const float3 vd=indirvel[CODE_GetIzoneFluidInout(rcode)];
          if(vd.x!=FLT_MAX){
            const float v=rvelrhopnew.x*vd.x + rvelrhopnew.y*vd.y + rvelrhopnew.z*vd.z;
            dx=double(v*vd.x) * dt;
            dy=double(v*vd.y) * dt;
            dz=double(v*vd.z) * dt;
          }
          else{
            dx=double(rvelrhopnew.x) * dt; 
            dy=double(rvelrhopnew.y) * dt; 
            dz=double(rvelrhopnew.z) * dt;
          }
        }
        //-Update particle data.
        movxy[p]=make_double2(dx,dy);
        movz[p]=dz;
        if(outrhop){ //-Only brands as excluded normal particles (not periodic). | Solo marca como excluidas las normales (no periodicas).
          const typecode rcode=code[p];
          if(CODE_IsNormal(rcode))code[p]=CODE_SetOutRhop(rcode);
        }
      }
      else{ //-Particles: Floating.
        rvelrhopnew.w=(rvelrhopnew.w<rhopzero? rhopzero: rvelrhopnew.w); //-To prevent absorption of fluid particles by boundaries. | Evita q las floating absorvan a las fluidas.
      }
      //-Stores new velocity and density.
      velrhop[p]=rvelrhopnew;
      //-Store new stress and kappa
      sigma[p*3]  =sigmanew_xx_xy;
      sigma[p*3+1]=sigmanew_xz_yy;
      sigma[p*3+2]=sigmanew_yz_zz;
      if(kplasticdk)kplasticdk[p]+=fmaxf(kplasticnew-kplasticpre[p],0.f);
      kplastic[p] = kplasticnew;
    }
  }
}
//==============================================================================  
template<TpDPCtes dpctes> void ComputeStepSymplecticCorT(bool floating,bool shift,bool inout,TpMdbc2Mode mdbc2,unsigned np,unsigned npb
  ,const float4 *velrhoppre,const float *ar,const float3 *ace,const float4 *shiftposfs
  ,const tsymatrix3d* sigmapre, const float* kplasticpre, const tsymatrix3f* rsigma
  ,const float3 *indirvel,const float4 *nopenshift,double dtm,double dt,float rhopzero,float rhopoutmin,float rhopoutmax,tfloat3 gravity
  ,typecode *code,double2 *movxy,double *movz,float4 *velrhop
  ,tsymatrix3d* sigma,float* kplastic,float* kplasticdk 
  ,cudaStream_t stm,StPorosityRhopState porostate,unsigned *materialerror,bool requireelastic)
{
	if(np){
    dim3 sgrid=GetSimpleGridSize(np,SPHBSIZE);
    if(inout){      const bool tinout=true;
      if(shift){    const bool shift=true;
        if(floating)KerComputeStepSymplecticCor<true ,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,nopenshift,mdbc2,dtm,dt,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
        else        KerComputeStepSymplecticCor<false,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,nopenshift,mdbc2,dtm,dt,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
      }else{        const bool shift=false;
        if(floating)KerComputeStepSymplecticCor<true ,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,nopenshift,mdbc2,dtm,dt,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
        else        KerComputeStepSymplecticCor<false,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,nopenshift,mdbc2,dtm,dt,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
      }
    }
    else{           const bool tinout=false;
      if(shift){    const bool shift=true;
        if(floating)KerComputeStepSymplecticCor<true ,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,nopenshift,mdbc2,dtm,dt,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
        else        KerComputeStepSymplecticCor<false,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,nopenshift,mdbc2,dtm,dt,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
      }else{        const bool shift=false;
        if(floating)KerComputeStepSymplecticCor<true ,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,nopenshift,mdbc2,dtm,dt,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
        else        KerComputeStepSymplecticCor<false,shift,tinout,dpctes> <<<sgrid,SPHBSIZE,0,stm>>> (np,npb,velrhoppre,ar,ace,shiftposfs,(const double2*)sigmapre,kplasticpre,(const float2*)rsigma,indirvel,nopenshift,mdbc2,dtm,dt,rhopzero,rhopoutmin,rhopoutmax,Float3(gravity),code,movxy,movz,velrhop,(double2*)sigma,kplastic,kplasticdk,porostate,materialerror,requireelastic);
      }
    }
  }
}
//==============================================================================
/// Updates particles using Symplectic-Corrector.
/// Actualizacion de particulas usando Symplectic-Corrector.
//==============================================================================   
void ComputeStepSymplecticCor(bool floating,bool shift,bool inout,TpDPCtes dpctes,TpMdbc2Mode mdbc2,unsigned np,unsigned npb
  ,const float4 *velrhoppre,const float *ar,const float3 *ace,const float4 *shiftposfs
  ,const tsymatrix3d* sigmapre, const float* kplasticpre, const tsymatrix3f* rsigma
  ,const float3 *indirvel,const float4 *nopenshift,double dtm,double dt,float rhopzero,float rhopoutmin,float rhopoutmax,tfloat3 gravity
  ,typecode *code,double2 *movxy,double *movz,float4 *velrhop
  ,tsymatrix3d* sigma,float* kplastic,float* kplasticdk
  ,cudaStream_t stm,StPorosityRhopState porostate,unsigned *materialerror,bool requireelastic)
{
  //cudaProfilerStart();//mdbr
      switch(dpctes){
	  case DP_C:{ const TpDPCtes tdpctes=DP_C;
		  ComputeStepSymplecticCorT<tdpctes>(floating,shift,inout,mdbc2,np,npb,velrhoppre,ar,ace,shiftposfs,sigmapre,kplasticpre,rsigma
            ,indirvel,nopenshift,dtm,dt,rhopzero,rhopoutmin,rhopoutmax,gravity,code,movxy,movz,velrhop,sigma,kplastic,kplasticdk,stm,porostate,materialerror,requireelastic);
	  }break;
	  case DP_MC:{ const TpDPCtes tdpctes=DP_MC;
		  ComputeStepSymplecticCorT<tdpctes>(floating,shift,inout,mdbc2,np,npb,velrhoppre,ar,ace,shiftposfs,sigmapre,kplasticpre,rsigma
            ,indirvel,nopenshift,dtm,dt,rhopzero,rhopoutmin,rhopoutmax,gravity,code,movxy,movz,velrhop,sigma,kplastic,kplasticdk,stm,porostate,materialerror,requireelastic);
	  }break;
	  case DP_PS:{ const TpDPCtes tdpctes=DP_PS;
		  ComputeStepSymplecticCorT<tdpctes>(floating,shift,inout,mdbc2,np,npb,velrhoppre,ar,ace,shiftposfs,sigmapre,kplasticpre,rsigma
            ,indirvel,nopenshift,dtm,dt,rhopzero,rhopoutmin,rhopoutmax,gravity,code,movxy,movz,velrhop,sigma,kplastic,kplasticdk,stm,porostate,materialerror,requireelastic);
	  }break;
	  default: throw "DP Constants unknown at ComputeStepSymplecticCor().";
  }
  //cudaProfilerStop();//mdbr
}
//==============================================================================
/// Stores constants for the GPU interaction.
/// Graba constantes para la interaccion a la GPU.
//==============================================================================

void CteInteractionUpTStep(const StSoilCte* soilcte,unsigned strainsoftening,unsigned partbegin){
    cudaMemcpyToSymbol(SOILSCTE,soilcte,sizeof(StSoilCte));
    cudaMemcpyToSymbol(SOILSTRAINSOFTENING,&strainsoftening,sizeof(unsigned));
    cudaMemcpyToSymbol(SOILPARTBEGIN,&partbegin,sizeof(unsigned));
  }
}

