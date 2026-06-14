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

/// \file JSphGpu_ker.cu \brief Implements functions and CUDA kernels for the Particle Interaction and System Update.

#include "JSphGpu_ker.h"
#include "Functions.h"
#include "FunctionsCuda.h"
#include "JLog2.h"
#include <cfloat>
#include <math_constants.h>
//:#include "JDgKerPrint.h"
//:#include "JDgKerPrint_ker.h"

#pragma warning(disable : 4267) //Cancels "warning C4267: conversion from 'size_t' to 'int', possible loss of data"
#pragma warning(disable : 4244) //Cancels "warning C4244: conversion from 'unsigned __int64' to 'unsigned int', possible loss of data"
#pragma warning(disable : 4503) //Cancels "warning C4503: decorated name length exceeded, name was truncated"
#include <thrust/device_vector.h>
#include <thrust/sort.h>

__constant__ StCteInteraction CTE;
#define CTE_AVAILABLE
//#include <cuda_profiler_api.h> //mdbr

namespace cusph{
#include "FunctionsBasic_iker.h"
#include "FunctionsMath_iker.h"
#include "FunctionsGeo3d_iker.h"
#include "FunSphKernel_iker.h"
#include "FunSphEos_iker.h"
#include "JCellSearch_iker.h"


__device__ float4 KerComputePosCell(const double3 &ps,const double3 &mapposmin,float poscellsize);

//==============================================================================
/// Reduction using maximum of float values in shared memory for a warp.
/// Reduccion mediante maximo de valores float en memoria shared para un warp.
//==============================================================================
template <unsigned blockSize> __device__ void KerReduMaxFloatWarp(volatile float* sdat,unsigned tid){
  if(blockSize>=64)sdat[tid]=max(sdat[tid],sdat[tid+32]);
  if(blockSize>=32)sdat[tid]=max(sdat[tid],sdat[tid+16]);
  if(blockSize>=16)sdat[tid]=max(sdat[tid],sdat[tid+8]);
  if(blockSize>=8)sdat[tid]=max(sdat[tid],sdat[tid+4]);
  if(blockSize>=4)sdat[tid]=max(sdat[tid],sdat[tid+2]);
  if(blockSize>=2)sdat[tid]=max(sdat[tid],sdat[tid+1]);
}

//==============================================================================
/// Accumulates the maximum of n values of array dat[], storing the result in 
/// the beginning of res[].(Many positions of res[] are used as blocks, 
/// storing the final result in res[0]).
///
/// Acumula el maximo de n valores del vector dat[], guardando el resultado al 
/// principio de res[] (Se usan tantas posiciones del res[] como bloques, 
/// quedando el resultado final en res[0]).
//==============================================================================
template <unsigned blockSize> __global__ void KerReduMaxFloat(unsigned n,unsigned ini,const float *dat,float *res){
  extern __shared__ float sdat[];
  unsigned tid=threadIdx.x;
  unsigned c=blockIdx.x*blockDim.x + threadIdx.x;
  sdat[tid]=(c<n? dat[c+ini]: -FLT_MAX);
  __syncthreads();
  if(blockSize>=512){ if(tid<256)sdat[tid]=max(sdat[tid],sdat[tid+256]);  __syncthreads(); }
  if(blockSize>=256){ if(tid<128)sdat[tid]=max(sdat[tid],sdat[tid+128]);  __syncthreads(); }
  if(blockSize>=128){ if(tid<64) sdat[tid]=max(sdat[tid],sdat[tid+64]);   __syncthreads(); }
  if(tid<32)KerReduMaxFloatWarp<blockSize>(sdat,tid);
  if(tid==0)res[blockIdx.x]=sdat[0];
}

//==============================================================================
/// Returns the maximum of an array, using resu[] as auxiliar array.
/// Size of resu[] must be >= a (N/SPHBSIZE+1)+(N/(SPHBSIZE*SPHBSIZE)+SPHBSIZE)
///
/// Devuelve el maximo de un vector, usando resu[] como vector auxiliar. El tamanho
/// de resu[] debe ser >= a (N/SPHBSIZE+1)+(N/(SPHBSIZE*SPHBSIZE)+SPHBSIZE)
//==============================================================================
float ReduMaxFloat(unsigned ndata,unsigned inidata,float* data,float* resu){
  float resf=0;
  if(ndata>=1){
    unsigned n=ndata,ini=inidata;
    unsigned smemSize=SPHBSIZE*sizeof(float);
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    unsigned n_blocks=sgrid.x*sgrid.y;
    float *dat=data;
    float *resu1=resu,*resu2=resu+n_blocks;
    float *res=resu1;
    while(n>1){
      KerReduMaxFloat<SPHBSIZE><<<sgrid,SPHBSIZE,smemSize>>>(n,ini,dat,res);
      n=n_blocks; ini=0;
      sgrid=GetSimpleGridSize(n,SPHBSIZE);  
      n_blocks=sgrid.x*sgrid.y;
      if(n>1){
        dat=res; res=(dat==resu1? resu2: resu1); 
      }
    }
    if(ndata>1)cudaMemcpy(&resf,res,sizeof(float),cudaMemcpyDeviceToHost);
    else cudaMemcpy(&resf,data,sizeof(float),cudaMemcpyDeviceToHost);
  }
  //else{//-Using Thrust library is slower than ReduMasFloat() with ndata < 5M.
  //  thrust::device_ptr<float> dev_ptr(data);
  //  resf=thrust::reduce(dev_ptr,dev_ptr+ndata,-FLT_MAX,thrust::maximum<float>());
  //}
  return(resf);
}

//==============================================================================
/// Accumulates the sum of n values of array dat[], storing the result in 
/// the beginning of res[].(Many positions of res[] are used as blocks, 
/// storing the final result in res[0]).
///
/// Acumula la suma de n valores del vector dat[].w, guardando el resultado al 
/// principio de res[] (Se usan tantas posiciones del res[] como bloques, 
/// quedando el resultado final en res[0]).
//==============================================================================
template <unsigned blockSize> __global__ void KerReduMaxFloat_w(unsigned n,unsigned ini,const float4 *dat,float *res){
  extern __shared__ float sdat[];
  unsigned tid=threadIdx.x;
  unsigned c=blockIdx.x*blockDim.x + threadIdx.x;
  sdat[tid]=(c<n? dat[c+ini].w: -FLT_MAX);
  __syncthreads();
  if(blockSize>=512){ if(tid<256)sdat[tid]=max(sdat[tid],sdat[tid+256]);  __syncthreads(); }
  if(blockSize>=256){ if(tid<128)sdat[tid]=max(sdat[tid],sdat[tid+128]);  __syncthreads(); }
  if(blockSize>=128){ if(tid<64) sdat[tid]=max(sdat[tid],sdat[tid+64]);   __syncthreads(); }
  if(tid<32)KerReduMaxFloatWarp<blockSize>(sdat,tid);
  if(tid==0)res[blockIdx.x]=sdat[0];
}

//==============================================================================
/// Returns the maximum of an array, using resu[] as auxiliar array.
/// Size of resu[] must be >= a (N/SPHBSIZE+1)+(N/(SPHBSIZE*SPHBSIZE)+SPHBSIZE).
///
/// Devuelve el maximo de la componente w de un vector float4, usando resu[] como 
/// vector auxiliar. El tamanho de resu[] debe ser >= a (N/SPHBSIZE+1)+(N/(SPHBSIZE*SPHBSIZE)+SPHBSIZE).
//==============================================================================
float ReduMaxFloat_w(unsigned ndata,unsigned inidata,float4* data,float* resu){
  unsigned n=ndata,ini=inidata;
  unsigned smemSize=SPHBSIZE*sizeof(float);
  dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
  unsigned n_blocks=sgrid.x*sgrid.y;
  float *dat=NULL;
  float *resu1=resu,*resu2=resu+n_blocks;
  float *res=resu1;
  while(n>1){
    if(!dat)KerReduMaxFloat_w<SPHBSIZE><<<sgrid,SPHBSIZE,smemSize>>>(n,ini,data,res);
    else KerReduMaxFloat<SPHBSIZE><<<sgrid,SPHBSIZE,smemSize>>>(n,ini,dat,res);
    n=n_blocks; ini=0;
    sgrid=GetSimpleGridSize(n,SPHBSIZE);  
    n_blocks=sgrid.x*sgrid.y;
    if(n>1){
      dat=res; res=(dat==resu1? resu2: resu1); 
    }
  }
  float resf;
  if(ndata>1)cudaMemcpy(&resf,res,sizeof(float),cudaMemcpyDeviceToHost);
  else{
    float4 resf4;
    cudaMemcpy(&resf4,data,sizeof(float4),cudaMemcpyDeviceToHost);
    resf=resf4.w;
  }
  return(resf);
}

//==============================================================================
/// Stores constants for the GPU interaction.
/// Graba constantes para la interaccion a la GPU.
//==============================================================================
void CteInteractionUp(const StCteInteraction *cte){
  cudaMemcpyToSymbol(CTE,cte,sizeof(StCteInteraction));
}

//------------------------------------------------------------------------------
/// Initialises array with the indicated value.
/// Inicializa array con el valor indicado.
//------------------------------------------------------------------------------
__global__ void KerInitArray(unsigned n,float3 *v,float3 value)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n)v[p]=value;
}

//==============================================================================
/// Initialises array with the indicated value.
/// Inicializa array con el valor indicado.
//==============================================================================
void InitArray(unsigned n,float3 *v,tfloat3 value){
  if(n){
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    KerInitArray <<<sgrid,SPHBSIZE>>> (n,v,Float3(value));
  }
}

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
void Resety(unsigned n,unsigned ini,float3 *v){
  if(n){
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    KerResety <<<sgrid,SPHBSIZE>>> (n,ini,v);
  }
}

//------------------------------------------------------------------------------
/// Calculates module^2 of ace.
//------------------------------------------------------------------------------
__global__ void KerComputeAceMod(unsigned n,const float3 *ace,float *acemod)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    const float3 r=ace[p];
    acemod[p]=r.x*r.x+r.y*r.y+r.z*r.z;
  }
}

//==============================================================================
/// Calculates module^2 of ace.
//==============================================================================
void ComputeAceMod(unsigned n,const float3 *ace,float *acemod){
  if(n){
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    KerComputeAceMod <<<sgrid,SPHBSIZE>>> (n,ace,acemod);
  }
}

//------------------------------------------------------------------------------
/// Calculates module^2 of ace, comprobando que la particula sea normal.
/// Uses zero for periodic particles.
//------------------------------------------------------------------------------
__global__ void KerComputeAceMod(unsigned n,const typecode *code,const float3 *ace,float *acemod)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    const typecode rcod=code[p];
    const float3 r=(CODE_IsNormal(rcod) && !CODE_IsFluidInout(rcod)? ace[p]: make_float3(0,0,0));
    acemod[p]=r.x*r.x+r.y*r.y+r.z*r.z;
  }
}

//==============================================================================
/// Calculates module^2 of ace, comprobando que la particula sea normal.
/// Uses zero for periodic particles.
//==============================================================================
void ComputeAceMod(unsigned n,const typecode *code,const float3 *ace,float *acemod){
  if(n){
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    KerComputeAceMod <<<sgrid,SPHBSIZE>>> (n,code,ace,acemod);
  }
}


//##############################################################################
//# Other kernels...
//# Otros kernels...
//##############################################################################
//------------------------------------------------------------------------------
/// Calculates module^2 of vel.
//------------------------------------------------------------------------------
__global__ void KerComputeVelMod(unsigned n,const float4 *vel,float *velmod)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    const float4 r=vel[p];
    velmod[p]=r.x*r.x+r.y*r.y+r.z*r.z;
  }
}

//==============================================================================
/// Calculates module^2 of vel.
//==============================================================================
void ComputeVelMod(unsigned n,const float4 *vel,float *velmod){
  if(n){
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    KerComputeVelMod <<<sgrid,SPHBSIZE>>> (n,vel,velmod);
  }
}


//##############################################################################
//# Kernels para cambiar la posicion.
//# Kernels for changing the position.
//##############################################################################
//------------------------------------------------------------------------------
/// Updates pos, dcell and code from the indicated displacement.
/// The code may be CODE_OUTRHOP because in ComputeStepVerlet / Symplectic this is evaluated
/// and is executed before ComputeStepPos.
/// Checks limits depending on maprealposmin and maprealsize, this is valid 
/// for single-GPU because maprealpos and domrealpos are equal. For multi-gpu it is
/// important to mark particles that leave the domain without leaving the map.
///
/// Actualiza pos, dcell y code a partir del desplazamiento indicado.
/// Code puede ser CODE_OUTRHOP pq en ComputeStepVerlet/Symplectic se evalua esto 
/// y se ejecuta antes que ComputeStepPos.
/// Comprueba los limites en funcion de maprealposmin y maprealsize esto es valido
/// para single-gpu pq domrealpos y maprealpos son iguales. Para multi-gpu seria 
/// necesario marcar las particulas q salgan del dominio sin salir del mapa.
//------------------------------------------------------------------------------
template<bool periactive> __device__ void KerUpdatePos
  (double2 rxy,double rz,double movx,double movy,double movz
  ,bool outrhop,unsigned p,double2 *posxy,double *posz,unsigned *dcell,typecode *code)
{
  //-Checks validity of displacement. | Comprueba validez del desplazamiento.
  const bool outmove=(fmaxf(fabsf(float(movx)),fmaxf(fabsf(float(movy)),fabsf(float(movz))))>CTE.movlimit);
  //-Applies diplacement.
  double3 rpos=make_double3(rxy.x,rxy.y,rz);
  rpos.x+=movx; rpos.y+=movy; rpos.z+=movz;
  if(rpos.y<0 && CTE.symmetry)rpos.y=-rpos.y; //<vs_syymmetry>
  //-Checks limits of real domain. | Comprueba limites del dominio reales.
  double dx=rpos.x-CTE.maprealposminx;
  double dy=rpos.y-CTE.maprealposminy;
  double dz=rpos.z-CTE.maprealposminz;
  bool out=(dx!=dx || dy!=dy || dz!=dz || dx<0 || dy<0 || dz<0 || dx>=CTE.maprealsizex || dy>=CTE.maprealsizey || dz>=CTE.maprealsizez);
  if(periactive && out){
    bool xperi=(CTE.periactive&1),yperi=(CTE.periactive&2),zperi=(CTE.periactive&4);
    if(xperi){
      if(dx<0)                { dx-=CTE.xperincx; dy-=CTE.xperincy; dz-=CTE.xperincz; }
      if(dx>=CTE.maprealsizex){ dx+=CTE.xperincx; dy+=CTE.xperincy; dz+=CTE.xperincz; }
    }
    if(yperi){
      if(dy<0)                { dx-=CTE.yperincx; dy-=CTE.yperincy; dz-=CTE.yperincz; }
      if(dy>=CTE.maprealsizey){ dx+=CTE.yperincx; dy+=CTE.yperincy; dz+=CTE.yperincz; }
    }
    if(zperi){
      if(dz<0)                { dx-=CTE.zperincx; dy-=CTE.zperincy; dz-=CTE.zperincz; }
      if(dz>=CTE.maprealsizez){ dx+=CTE.zperincx; dy+=CTE.zperincy; dz+=CTE.zperincz; }
    }
    bool outx=!xperi && (dx<0 || dx>=CTE.maprealsizex);
    bool outy=!yperi && (dy<0 || dy>=CTE.maprealsizey);
    bool outz=!zperi && (dz<0 || dz>=CTE.maprealsizez);
    out=(outx||outy||outz);
    rpos=make_double3(dx+CTE.maprealposminx,dy+CTE.maprealposminy,dz+CTE.maprealposminz);
  }
  //-Stores updated position.
  posxy[p]=make_double2(rpos.x,rpos.y);
  posz[p]=rpos.z;
  //-Stores cell and check. | Guarda celda y check.
  if(outrhop || outmove || out){//-Particle out. Only brands as excluded normal particles (not periodic). | Particle out. Solo las particulas normales (no periodicas) se pueden marcar como excluidas.
    typecode rcode=code[p];
    if(out)rcode=CODE_SetOutPos(rcode);
    else if(outrhop)rcode=CODE_SetOutRhop(rcode);
    else rcode=CODE_SetOutMove(rcode);
    code[p]=rcode;
    dcell[p]=DCEL_CodeMapOut;
  }
  else{//-Particle in.
    if(periactive){
      dx=rpos.x-CTE.domposminx;
      dy=rpos.y-CTE.domposminy;
      dz=rpos.z-CTE.domposminz;
    }
    const unsigned cx=unsigned(dx/CTE.scell);
    const unsigned cy=unsigned(dy/CTE.scell);
    const unsigned cz=unsigned(dz/CTE.scell);
    dcell[p]=DCEL_Cell(CTE.cellcode,cx,cy,cz);
  }
}

//------------------------------------------------------------------------------
/// Returns the corrected position after applying periodic conditions.
/// Devuelve la posicion corregida tras aplicar condiciones periodicas.
//------------------------------------------------------------------------------
__device__ double3 KerUpdatePeriodicPos(double3 ps)
{
  double dx=ps.x-CTE.maprealposminx;
  double dy=ps.y-CTE.maprealposminy;
  double dz=ps.z-CTE.maprealposminz;
  const bool out=(dx!=dx || dy!=dy || dz!=dz || dx<0 || dy<0 || dz<0 || dx>=CTE.maprealsizex || dy>=CTE.maprealsizey || dz>=CTE.maprealsizez);
  //-Adjusts position according to periodic conditions and rechecks domain limits.
  //-Ajusta posicion segun condiciones periodicas y vuelve a comprobar los limites del dominio.
  if(out){
    bool xperi=(CTE.periactive&1),yperi=(CTE.periactive&2),zperi=(CTE.periactive&4);
    if(xperi){
      if(dx<0)                { dx-=CTE.xperincx; dy-=CTE.xperincy; dz-=CTE.xperincz; }
      if(dx>=CTE.maprealsizex){ dx+=CTE.xperincx; dy+=CTE.xperincy; dz+=CTE.xperincz; }
    }
    if(yperi){
      if(dy<0)                { dx-=CTE.yperincx; dy-=CTE.yperincy; dz-=CTE.yperincz; }
      if(dy>=CTE.maprealsizey){ dx+=CTE.yperincx; dy+=CTE.yperincy; dz+=CTE.yperincz; }
    }
    if(zperi){
      if(dz<0)                { dx-=CTE.zperincx; dy-=CTE.zperincy; dz-=CTE.zperincz; }
      if(dz>=CTE.maprealsizez){ dx+=CTE.zperincx; dy+=CTE.zperincy; dz+=CTE.zperincz; }
    }
    ps=make_double3(dx+CTE.maprealposminx,dy+CTE.maprealposminy,dz+CTE.maprealposminz);
  }
  return(ps);
}


//##############################################################################
//# Kernels for calculating forces (Pos-Double).
//# Kernels para calculo de fuerzas (Pos-Double).
//##############################################################################
//------------------------------------------------------------------------------
/// Interaction of a particle with a set of particles. Bound-Fluid/Float
/// Realiza la interaccion de una particula con un conjunto de ellas. Bound-Fluid/Float
//------------------------------------------------------------------------------
template<TpKernel tker,TpFtMode ftmode,bool symm>
  __device__ void KerInteractionForcesBoundBox
  (unsigned p1,const unsigned &pini,const unsigned &pfin
  ,const float *ftomassp
  ,const float4 *poscell,const float4 *velrhop,const typecode *code,const unsigned* idp
  ,float massf,const float4 &pscellp1,const float4 &velrhop1,float &arp1,float &visc)
{
  for(int p2=pini;p2<pfin;p2++){
    const float4 pscellp2=poscell[p2];
    float drx=pscellp1.x-pscellp2.x + CTE.poscellsize*(PSCEL_GetfX(pscellp1.w)-PSCEL_GetfX(pscellp2.w));
    float dry=pscellp1.y-pscellp2.y + CTE.poscellsize*(PSCEL_GetfY(pscellp1.w)-PSCEL_GetfY(pscellp2.w));
    float drz=pscellp1.z-pscellp2.z + CTE.poscellsize*(PSCEL_GetfZ(pscellp1.w)-PSCEL_GetfZ(pscellp2.w));
    if(symm)dry=pscellp1.y+pscellp2.y + CTE.poscellsize*PSCEL_GetfY(pscellp2.w); //<vs_syymmetry>
    const float rr2=drx*drx+dry*dry+drz*drz;
    if(rr2<=CTE.kernelsize2 && rr2>=ALMOSTZERO){
      //-Computes kernel.
      const float fac=cufsph::GetKernel_Fac<tker>(rr2);
      const float frx=fac*drx,fry=fac*dry,frz=fac*drz; //-Gradients.

      float4 velrhop2=velrhop[p2];
      if(symm)velrhop2.y=-velrhop2.y; //<vs_syymmetry>
      //-Obtains particle mass p2 if there are floating bodies.
      //-Obtiene masa de particula p2 en caso de existir floatings.
      float ftmassp2;    //-Contains mass of floating body or massf if fluid. | Contiene masa de particula floating o massf si es fluid.
      bool compute=true; //-Deactivated when DEM is used and is float-float or float-bound. | Se desactiva cuando se usa DEM y es float-float o float-bound.
      if(USE_FLOATING){
        const typecode cod=code[p2];
        bool ftp2=CODE_IsFloating(cod);
        ftmassp2=(ftp2? ftomassp[CODE_GetTypeValue(cod)]: massf);
        compute=!(USE_FTEXTERNAL && ftp2); //-Deactivated when DEM or Chrono is used and is bound-float. | Se desactiva cuando se usa DEM o Chrono y es bound-float.
      }

      if(compute){
        //-Density derivative (Continuity equation).
        const float dvx=velrhop1.x-velrhop2.x, dvy=velrhop1.y-velrhop2.y, dvz=velrhop1.z-velrhop2.z;
        arp1+=(USE_FLOATING? ftmassp2: massf)*(dvx*frx+dvy*fry+dvz*frz)*(velrhop1.w/velrhop2.w);

        {//===== Viscosity ===== 
          const float dot=drx*dvx + dry*dvy + drz*dvz;
          const float dot_rr2=dot/(rr2+CTE.eta2);
          visc=max(dot_rr2,visc); 
        }
      }
    }
  }
}

//------------------------------------------------------------------------------
/// Particle interaction. Bound-Fluid/Float
/// Realiza interaccion entre particulas. Bound-Fluid/Float
//------------------------------------------------------------------------------
template<TpKernel tker,TpFtMode ftmode,bool symm> 
  __global__ void KerInteractionForcesBound(unsigned n,unsigned pinit
  ,int scelldiv,int4 nc,int3 cellzero,const int2 *beginendcellfluid,const unsigned *dcell
  ,const float *ftomassp
  ,const float4 *poscell,const float4 *velrhop,const typecode *code,const unsigned *idp
  ,float *viscdt,float *ar)
{
  const unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of thread.
  if(p<n){
    const unsigned p1=p+pinit;      //-Number of particle.
    float visc=0,arp1=0;

    //-Loads particle p1 data.
    const float4 pscellp1=poscell[p1];
    const float4 velrhop1=velrhop[p1];
    const bool rsymp1=(symm && PSCEL_GetPartY(__float_as_uint(pscellp1.w))==0); //<vs_syymmetry>
    
    //-Obtains neighborhood search limits.
    int ini1,fin1,ini2,fin2,ini3,fin3;
    cunsearch::InitCte(dcell[p1],scelldiv,nc,cellzero,ini1,fin1,ini2,fin2,ini3,fin3);

    //-Boundary-Fluid interaction.
    for(int c3=ini3;c3<fin3;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
      unsigned pini,pfin=0;  cunsearch::ParticleRange(c2,c3,ini1,fin1,beginendcellfluid,pini,pfin);
      if(pfin){
                          KerInteractionForcesBoundBox<tker,ftmode,false> (p1,pini,pfin,ftomassp,poscell,velrhop,code,idp,CTE.massf,pscellp1,velrhop1,arp1,visc);
        if(symm && rsymp1)KerInteractionForcesBoundBox<tker,ftmode,true > (p1,pini,pfin,ftomassp,poscell,velrhop,code,idp,CTE.massf,pscellp1,velrhop1,arp1,visc);
      }
    }
    //-Stores results.
    if(arp1 || visc){
      ar[p1]+=arp1;
      if(visc>viscdt[p1])viscdt[p1]=visc;
    }
  }
}
//==============================================================================
/// Calculate strain/spin rate tensor
/// Input velgradient (3*3); Ouput strain (3*2)/spin (3*1) rate tensor
//==============================================================================
__device__ void GetStrainSpinRateTensor_sym(float3 gradvp1_xx_xy_xz,float3 gradvp1_yx_yy_yz,float3 gradvp1_zx_zy_zz
  ,float2 &e_tensor_xx_xy,float2 &e_tensor_xz_yy,float2 &e_tensor_yz_zz,float3 &w_tensor_xy_yz_xz)
{
  //Build strain rate tensor
  e_tensor_xx_xy.x=gradvp1_xx_xy_xz.x;//xx
  e_tensor_xz_yy.y=gradvp1_yx_yy_yz.y;//yy	  
  e_tensor_yz_zz.y=gradvp1_zx_zy_zz.z;//zz
  e_tensor_xx_xy.y=0.5f*(gradvp1_xx_xy_xz.y+gradvp1_yx_yy_yz.x);//xy
  e_tensor_yz_zz.x=0.5f*(gradvp1_yx_yy_yz.z+gradvp1_zx_zy_zz.y);//yz
  e_tensor_xz_yy.x=0.5f*(gradvp1_xx_xy_xz.z+gradvp1_zx_zy_zz.x);//xz

  //Build spin rate tensor
  w_tensor_xy_yz_xz.x = 0.5f*(gradvp1_xx_xy_xz.y-gradvp1_yx_yy_yz.x);//xy
  w_tensor_xy_yz_xz.y = 0.5f*(gradvp1_yx_yy_yz.z-gradvp1_zx_zy_zz.y);//yz
  w_tensor_xy_yz_xz.z = 0.5f*(gradvp1_xx_xy_xz.z-gradvp1_zx_zy_zz.x);//xz
}

//==============================================================================
/// Calculate elastic stress rate tensor
/// Input Strain/Spin Rate, Elastic Parameters, Stress, Ouput Elastic Stress Rate Tensor
//==============================================================================
__device__ void GetStressRateTensor_Elastic(float2 e_tensor_xx_xy,float2 e_tensor_xz_yy,float2 e_tensor_yz_zz,float3 w_tensor_xy_yz_xz
,float2 sigma_xx_xy,float2 sigma_xz_yy,float2 sigma_yz_zz
,const float DP_K, const float DP_G
,float2 &rsigma_xx_xy,float2 &rsigma_xz_yy,float2 &rsigma_yz_zz)
{
  //Build Elastic stiffness matrix
	float K4G3 = DP_K + 4.f*DP_G / 3.f;
	float K2G3 = DP_K - 2.f*DP_G / 3.f;
	float m_a11 = K4G3; float m_a12 = K2G3; float m_a13 = K2G3;
	float m_a21 = K2G3; float m_a22 = K4G3; float m_a23 = K2G3;
	float m_a31 = K2G3; float m_a32 = K2G3; float m_a33 = K4G3; 

  //Get stress, stran rate and spin rate
  float sigmaxx = sigma_xx_xy.x;
  float sigmaxy = sigma_xx_xy.y;
  float sigmaxz = sigma_xz_yy.x;
  float sigmayy = sigma_xz_yy.y;
  float sigmayz = sigma_yz_zz.x;
  float sigmazz = sigma_yz_zz.y;

  float exx = e_tensor_xx_xy.x;
  float exy = e_tensor_xx_xy.y;
  float exz = e_tensor_xz_yy.x;
  float eyy = e_tensor_xz_yy.y;
  float eyz = e_tensor_yz_zz.x;
  float ezz = e_tensor_yz_zz.y;

  float wxy = w_tensor_xy_yz_xz.x;
  float wyz = w_tensor_xy_yz_xz.y;
  float wxz = w_tensor_xy_yz_xz.z;
  
  //Jaumann stress rate
  float Jxx = - 2.f*sigmaxy*wxy - 2.f*sigmaxz*wxz;
  float Jyy = 2.f*sigmaxy*wxy - 2.f*sigmayz*wyz;
  float Jzz = 2.f*sigmaxz*wxz + 2.f*sigmayz*wyz;
  float Jxy = sigmaxx*wxy - sigmayy*wxy - sigmaxz*wyz - sigmayz*wxz;
  float Jxz = sigmaxx*wxz + sigmaxy*wyz - sigmayz*wxy - sigmazz*wxz;
  float Jyz = sigmaxy*wxz + sigmaxz*wxy + sigmayy*wyz - sigmazz*wyz;
 
  //Construct stress rate equation
  rsigma_xx_xy.x = (m_a11*exx+m_a12*eyy+m_a13*ezz)+Jxx;//
  rsigma_xz_yy.y = (m_a21*exx+m_a22*eyy+m_a23*ezz)+Jyy;//
  rsigma_yz_zz.y = (m_a31*exx+m_a32*eyy+m_a33*ezz)+Jzz;//
  rsigma_xx_xy.y = 2.f*DP_G*exy+Jxy;//
  rsigma_yz_zz.x = 2.f*DP_G*eyz+Jyz;//
  rsigma_xz_yy.x = 2.f*DP_G*exz+Jxz ;// 
}
//------------------------------------------------------------------------------
/// Computes eigenvalues and eigenvectors of a symmetric 3x3 stress tensor.
//------------------------------------------------------------------------------
__device__ void KerComputeSymmetricEigen3D(float xx,float yy,float zz,float xy,float yz,float xz,float eval[3],float evec[3][3]){
  float a[3][3]={
    {xx,xy,xz},
    {xy,yy,yz},
    {xz,yz,zz}
  };
  evec[0][0]=1.f; evec[0][1]=0.f; evec[0][2]=0.f;
  evec[1][0]=0.f; evec[1][1]=1.f; evec[1][2]=0.f;
  evec[2][0]=0.f; evec[2][1]=0.f; evec[2][2]=1.f;
  for(int it=0;it<16;it++){
    int p=0,q=1;
    float maxoff=fabsf(a[0][1]);
    const float a02=fabsf(a[0][2]);
    const float a12=fabsf(a[1][2]);
    if(a02>maxoff){maxoff=a02; p=0; q=2;}
    if(a12>maxoff){maxoff=a12; p=1; q=2;}
    const float scale=fabsf(a[0][0])+fabsf(a[1][1])+fabsf(a[2][2])+1.f;
    if(maxoff<=1e-6f*scale)break;
    const float phi=0.5f*atan2f(2.f*a[p][q],a[q][q]-a[p][p]);
    const float c=cosf(phi);
    const float sn=sinf(phi);
    for(int k=0;k<3;k++){
      const float akp=a[k][p];
      const float akq=a[k][q];
      a[k][p]=c*akp-sn*akq;
      a[k][q]=sn*akp+c*akq;
    }
    for(int k=0;k<3;k++){
      const float apk=a[p][k];
      const float aqk=a[q][k];
      a[p][k]=c*apk-sn*aqk;
      a[q][k]=sn*apk+c*aqk;
    }
    for(int k=0;k<3;k++){
      const float vkp=evec[k][p];
      const float vkq=evec[k][q];
      evec[k][p]=c*vkp-sn*vkq;
      evec[k][q]=sn*vkp+c*vkq;
    }
  }
  eval[0]=a[0][0];
  eval[1]=a[1][1];
  eval[2]=a[2][2];
}
//------------------------------------------------------------------------------
/// Computes Bui 2008 artificial stress tensor in global coordinates.
//------------------------------------------------------------------------------
__device__ void KerComputeBuiArtificialStress(float2 sigma_xx_xy,float2 sigma_xz_yy,float2 sigma_yz_zz,float rhop,float coef
  ,float2 &rstress_xx_xy,float2 &rstress_xz_yy,float2 &rstress_yz_zz)
{
  rstress_xx_xy=make_float2(0,0);
  rstress_xz_yy=make_float2(0,0);
  rstress_yz_zz=make_float2(0,0);
  if(rhop<=0.f)return;
  float eval[3];
  float evec[3][3];
  KerComputeSymmetricEigen3D(sigma_xx_xy.x,sigma_xz_yy.y,sigma_yz_zz.y,sigma_xx_xy.y,sigma_yz_zz.x,sigma_xz_yy.x,eval,evec);
  const float rrhop2=1.f/(rhop*rhop);
  float rp[3];
  for(int a=0;a<3;a++)rp[a]=(eval[a]>0.f? -coef*eval[a]*rrhop2: 0.f);
  for(int a=0;a<3;a++){
    const float rx=evec[0][a],ry=evec[1][a],rz=evec[2][a];
    rstress_xx_xy.x+=rp[a]*rx*rx;
    rstress_xz_yy.y+=rp[a]*ry*ry;
    rstress_yz_zz.y+=rp[a]*rz*rz;
    rstress_xx_xy.y+=rp[a]*rx*ry;
    rstress_yz_zz.x+=rp[a]*ry*rz;
    rstress_xz_yy.x+=rp[a]*rx*rz;
  }
}
//------------------------------------------------------------------------------
/// Precomputes Bui 2008 artificial stress tensor for each non-floating particle.
//------------------------------------------------------------------------------
__global__ void KerComputeArtificialStress(unsigned n,unsigned nbound,const typecode *code,const float4 *velrhop,const float2 *sigma,float2 *artificialstress){
  const unsigned p=blockIdx.x*blockDim.x+threadIdx.x;
  if(p<n){
    float2 rstress_xx_xy=make_float2(0,0);
    float2 rstress_xz_yy=make_float2(0,0);
    float2 rstress_yz_zz=make_float2(0,0);
    const bool ftp=CODE_IsFloating(code[p]);
    if(!ftp){
      KerComputeBuiArtificialStress(sigma[p*3],sigma[p*3+1],sigma[p*3+2],velrhop[p].w,CTE.artificialstresscoef,rstress_xx_xy,rstress_xz_yy,rstress_yz_zz);
    }
    artificialstress[p*3]=rstress_xx_xy;
    artificialstress[p*3+1]=rstress_xz_yy;
    artificialstress[p*3+2]=rstress_yz_zz;
  }
}
//==============================================================================
/// Precomputes Bui 2008 artificial stress tensor on GPU.
//==============================================================================
void ComputeArtificialStress(unsigned n,unsigned nbound,const typecode *code,const float4 *velrhop,const tsymatrix3f *sigma,tsymatrix3f *artificialstress){
  if(n){
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    KerComputeArtificialStress <<<sgrid,SPHBSIZE>>> (n,nbound,code,velrhop,(const float2*)sigma,(float2*)artificialstress);
  }
}

//------------------------------------------------------------------------------
/// Adds Bui-Fukagawa damping to non-boundary soil particles.
//------------------------------------------------------------------------------
__global__ void KerAddSoilDamping(unsigned n,unsigned pini,const typecode *code,const float4 *velrhop,float3 *ace){
  unsigned p=blockIdx.x*blockDim.x+threadIdx.x;
  if(p<n){
    p+=pini;
    const typecode rcode=code[p];
    if(CTE.soildamping && CTE.soildampingcoef>0.f && CTE.modulus_E>0.f && CTE.kernelh>0.f
      && CODE_IsNormal(rcode) && CODE_IsFluid(rcode) && !CODE_IsFluidInout(rcode))
    {
      const float4 vrhop=velrhop[p];
      if(vrhop.w>0.f){
        const float cd=CTE.soildampingcoef*sqrtf(CTE.modulus_E/(vrhop.w*CTE.kernelh*CTE.kernelh));
        float3 acep=ace[p];
        acep.x-=cd*vrhop.x;
        acep.y-=cd*vrhop.y;
        acep.z-=cd*vrhop.z;
        ace[p]=acep;
      }
    }
  }
}

//==============================================================================
/// Adds Bui-Fukagawa damping on GPU.
//==============================================================================
void AddSoilDamping(unsigned n,unsigned nbound,const typecode *code,const float4 *velrhop,float3 *ace){
  if(n>nbound){
    const unsigned npf=n-nbound;
    dim3 sgrid=GetSimpleGridSize(npf,SPHBSIZE);
    KerAddSoilDamping <<<sgrid,SPHBSIZE>>> (npf,nbound,code,velrhop,ace);
  }
}

//==============================================================================
/// Returns the inverse 3-D correction matrix, using the x-z block in 2-D.
//==============================================================================
template<bool sim2d> __device__ tmatrix3d KerFsCorrMatInverse(const tmatrix3d &mat){
  tmatrix3d inv;
  cumath::Tmatrix3dReset(inv);
  if(sim2d){
    const double det=mat.a11*mat.a33-mat.a13*mat.a31;
    if(det){
      inv.a11= mat.a33/det;
      inv.a13=-mat.a13/det;
      inv.a31=-mat.a31/det;
      inv.a33= mat.a11/det;
    }
    else{
      inv.a11=1;
      inv.a33=1;
    }
  }
  else{
    const double det=cumath::Determinant3x3(mat);
    if(det)inv=cumath::InverseMatrix3x3(mat,det);
  }
  return(inv);
}

//==============================================================================
/// Applies a kernel-gradient correction matrix to one velocity-gradient row.
//==============================================================================
__device__ float3 KerApplyGradCorr(const float3 &grad,const tmatrix3d &corr){
  return make_float3(
    float(grad.x*corr.a11 + grad.y*corr.a12 + grad.z*corr.a13),
    float(grad.x*corr.a21 + grad.y*corr.a22 + grad.z*corr.a23),
    float(grad.x*corr.a31 + grad.y*corr.a32 + grad.z*corr.a33));
}

//==============================================================================
/// Computes free-surface candidates, local normals and correction matrices.
//==============================================================================
template<TpKernel tker,bool sim2d> __global__ void KerComputeFSParticlesFreeSurface
  (unsigned np,unsigned npb,int scelldiv,int4 nc,int3 cellzero,const int2 *beginendcell
  ,unsigned cellfluid,const unsigned *dcell,const float4 *poscell,const float4 *velrhop
  ,const typecode *code,tmatrix3d *corrmat,unsigned *fstype,float3 *fsnormal,float *posdiv)
{
  const unsigned p1=blockIdx.x*blockDim.x+threadIdx.x;
  if(p1<np){
    tmatrix3d matzero;
    cumath::Tmatrix3dReset(matzero);
    if(p1<npb){
      corrmat[p1]=matzero;
      fstype[p1]=4;
      fsnormal[p1]=make_float3(0,0,0);
      posdiv[p1]=0;
      return;
    }

    corrmat[p1]=matzero;
    fstype[p1]=0;
    fsnormal[p1]=make_float3(0,0,0);
    posdiv[p1]=0;
    if(CODE_IsPeriodic(code[p1]))return;

    const float4 pscellp1=poscell[p1];
    double fs_treshold=0;
    double3 gradc=make_double3(0,0,0);
    tmatrix3d lcorr;
    cumath::Tmatrix3dReset(lcorr);
    unsigned neigh=0;
    const float volb=(sim2d? CTE.dp*CTE.dp: CTE.dp*CTE.dp*CTE.dp);

    for(int b2=0;b2<2;b2++){
      const bool boundp2=(b2==1);
      int ini1,fin1,ini2,fin2,ini3,fin3;
      cunsearch::InitCte(dcell[p1],scelldiv,nc,cellzero,ini1,fin1,ini2,fin2,ini3,fin3);
      if(!boundp2){ ini3+=cellfluid; fin3+=cellfluid; }
      for(int c3=ini3;c3<fin3;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
        unsigned pini,pfin=0;
        cunsearch::ParticleRange(c2,c3,ini1,fin1,beginendcell,pini,pfin);
        for(unsigned p2=pini;p2<pfin;p2++){
          const float4 pscellp2=poscell[p2];
          const float drx=pscellp1.x-pscellp2.x + CTE.poscellsize*(PSCEL_GetfX(pscellp1.w)-PSCEL_GetfX(pscellp2.w));
          const float dry=(sim2d? 0: pscellp1.y-pscellp2.y + CTE.poscellsize*(PSCEL_GetfY(pscellp1.w)-PSCEL_GetfY(pscellp2.w)));
          const float drz=pscellp1.z-pscellp2.z + CTE.poscellsize*(PSCEL_GetfZ(pscellp1.w)-PSCEL_GetfZ(pscellp2.w));
          const float rr2=drx*drx+dry*dry+drz*drz;
          if(rr2<=CTE.kernelsize2 && rr2>=ALMOSTZERO){
            const float fac=cufsph::GetKernel_Fac<tker>(rr2);
            const double frx=double(fac)*double(drx);
            const double fry=(sim2d? 0: double(fac)*double(dry));
            const double frz=double(fac)*double(drz);
            const float rhop2=velrhop[p2].w;
            const double vol2=(rhop2>0?
              double((boundp2? CTE.massb: CTE.massf)/rhop2): double(boundp2? volb: 0));
            if(vol2>0){
              neigh++;
              const double ddrx=double(drx);
              const double ddry=(sim2d? 0: double(dry));
              const double ddrz=double(drz);
              const double dot3=ddrx*frx+ddry*fry+ddrz*frz;
              gradc.x+=vol2*frx;
              gradc.y+=vol2*fry;
              gradc.z+=vol2*frz;
              fs_treshold-=vol2*dot3;
              lcorr.a11+=-ddrx*frx*vol2; lcorr.a12+=-ddrx*fry*vol2; lcorr.a13+=-ddrx*frz*vol2;
              lcorr.a21+=-ddry*frx*vol2; lcorr.a22+=-ddry*fry*vol2; lcorr.a23+=-ddry*frz*vol2;
              lcorr.a31+=-ddrz*frx*vol2; lcorr.a32+=-ddrz*fry*vol2; lcorr.a33+=-ddrz*frz*vol2;
            }
          }
        }
      }
    }

    posdiv[p1]=float(fs_treshold);
    unsigned fstypep1=0;
    if(neigh){
      const float nzero=(sim2d?
        CUDART_PI_F*CTE.kernelsize2/(CTE.dp*CTE.dp):
        (4.f/3.f)*CUDART_PI_F*CTE.kernelsize2*CTE.kernelsize2/(CTE.dp*CTE.dp*CTE.dp));
      if(sim2d){
        if(fs_treshold<1.7)fstypep1=2;
        if(fs_treshold<1.1 && nzero/float(neigh)<0.4f)fstypep1=3;
      }
      else{
        if(fs_treshold<2.75)fstypep1=2;
        if(fs_treshold<1.8 && nzero/float(neigh)<0.4f)fstypep1=3;
      }
    }
    else fstypep1=3;
    fstype[p1]=fstypep1;

    const tmatrix3d lcorr_inv=KerFsCorrMatInverse<sim2d>(lcorr);
    corrmat[p1]=lcorr_inv;
    const double3 gradc1=make_double3(
      gradc.x*lcorr_inv.a11+gradc.y*lcorr_inv.a12+gradc.z*lcorr_inv.a13,
      gradc.x*lcorr_inv.a21+gradc.y*lcorr_inv.a22+gradc.z*lcorr_inv.a23,
      gradc.x*lcorr_inv.a31+gradc.y*lcorr_inv.a32+gradc.z*lcorr_inv.a33);
    const double gradcnorm=sqrt(gradc1.x*gradc1.x+gradc1.y*gradc1.y+gradc1.z*gradc1.z);
    if(gradcnorm>1e-12){
      fsnormal[p1]=make_float3(float(-gradc1.x/gradcnorm),float(-gradc1.y/gradcnorm),float(-gradc1.z/gradcnorm));
    }
  }
}

//==============================================================================
/// Scans the umbrella region and rejects candidates with neighbours in that region.
//==============================================================================
template<bool sim2d> __global__ void KerScanUmbrellaFreeSurface
  (unsigned np,unsigned npb,int scelldiv,int4 nc,int3 cellzero,const int2 *beginendcell
  ,unsigned cellfluid,const unsigned *dcell,const float4 *poscell,const typecode *code
  ,const float3 *fsnormal,unsigned *fstype)
{
  const unsigned p1=blockIdx.x*blockDim.x+threadIdx.x;
  if(p1>=npb && p1<np){
    if(CODE_IsPeriodic(code[p1])){
      fstype[p1]=0;
      return;
    }
    if(fstype[p1]!=2)return;
    bool fs_flag=false;
    const float4 pscellp1=poscell[p1];
    const float3 normalp1=fsnormal[p1];
    const float norm2=normalp1.x*normalp1.x+normalp1.y*normalp1.y+normalp1.z*normalp1.z;
    if(norm2<=1e-12f)return;
    const float3 posq=make_float3(CTE.kernelh*normalp1.x,CTE.kernelh*normalp1.y,CTE.kernelh*normalp1.z);

    for(int b2=0;b2<2 && !fs_flag;b2++){
      const bool boundp2=(b2==1);
      int ini1,fin1,ini2,fin2,ini3,fin3;
      cunsearch::InitCte(dcell[p1],scelldiv,nc,cellzero,ini1,fin1,ini2,fin2,ini3,fin3);
      if(!boundp2){ ini3+=cellfluid; fin3+=cellfluid; }
      for(int c3=ini3;c3<fin3 && !fs_flag;c3+=nc.w)for(int c2=ini2;c2<fin2 && !fs_flag;c2+=nc.x){
        unsigned pini,pfin=0;
        cunsearch::ParticleRange(c2,c3,ini1,fin1,beginendcell,pini,pfin);
        for(unsigned p2=pini;p2<pfin;p2++){
          const float4 pscellp2=poscell[p2];
          const float drx=pscellp1.x-pscellp2.x + CTE.poscellsize*(PSCEL_GetfX(pscellp1.w)-PSCEL_GetfX(pscellp2.w));
          const float dry=(sim2d? 0: pscellp1.y-pscellp2.y + CTE.poscellsize*(PSCEL_GetfY(pscellp1.w)-PSCEL_GetfY(pscellp2.w)));
          const float drz=pscellp1.z-pscellp2.z + CTE.poscellsize*(PSCEL_GetfZ(pscellp1.w)-PSCEL_GetfZ(pscellp2.w));
          const float rr2=drx*drx+dry*dry+drz*drz;
          if(rr2<=CTE.kernelsize2 && rr2>=ALMOSTZERO){
            if(rr2>2.f*CTE.kernelh*CTE.kernelh){
              const float drxq=-drx-posq.x;
              const float dryq=(sim2d? 0: -dry-posq.y);
              const float drzq=-drz-posq.z;
              const float rrq=sqrtf(drxq*drxq+dryq*dryq+drzq*drzq);
              if(rrq<CTE.kernelh)fs_flag=true;
            }
            else{
              if(sim2d){
                const float drxq=-drx-posq.x;
                const float drzq=-drz-posq.z;
                const float normalqnorm=sqrtf((drxq*normalp1.x)*(drxq*normalp1.x)+(drzq*normalp1.z)*(drzq*normalp1.z));
                const float tangqnorm=sqrtf((-drxq*normalp1.z)*(-drxq*normalp1.z)+(drzq*normalp1.x)*(drzq*normalp1.x));
                if(normalqnorm+tangqnorm<CTE.kernelh)fs_flag=true;
              }
              else{
                const float rrr=rsqrtf(rr2);
                float cosine=(-drx*normalp1.x-dry*normalp1.y-drz*normalp1.z)*rrr;
                cosine=max(-1.f,min(1.f,cosine));
                if(acosf(cosine)<0.785398f)fs_flag=true;
              }
            }
          }
          if(fs_flag)break;
        }
      }
    }
    if(fs_flag)fstype[p1]=0;
  }
}

//==============================================================================
/// Computes free-surface classification with the lightweight umbrella algorithm.
//==============================================================================
template<TpKernel tker,bool sim2d> void ComputeFreeSurfaceTrackingT(unsigned np,unsigned npb
  ,const StDivDataGpu &dvd,const unsigned *dcell,const float4 *poscell,const float4 *velrhop
  ,const typecode *code,tmatrix3d *corrmat,unsigned *fstype,float3 *fsnormal,float *posdiv)
{
  if(np){
    dim3 sgrid=GetSimpleGridSize(np,SPHBSIZE);
    KerComputeFSParticlesFreeSurface<tker,sim2d> <<<sgrid,SPHBSIZE>>>
      (np,npb,dvd.scelldiv,dvd.nc,dvd.cellzero,dvd.beginendcell,dvd.cellfluid,dcell,poscell,velrhop,code,corrmat,fstype,fsnormal,posdiv);
    KerScanUmbrellaFreeSurface<sim2d> <<<sgrid,SPHBSIZE>>>
      (np,npb,dvd.scelldiv,dvd.nc,dvd.cellzero,dvd.beginendcell,dvd.cellfluid,dcell,poscell,code,fsnormal,fstype);
  }
}

//==============================================================================
/// Computes free-surface classification with the lightweight umbrella algorithm.
//==============================================================================
void ComputeFreeSurfaceTracking(TpKernel tkernel,bool simulate2d,unsigned np,unsigned npb
  ,const StDivDataGpu &dvd,const unsigned *dcell,const float4 *poscell
  ,const float4 *velrhop,const typecode *code,tmatrix3d *corrmat
  ,unsigned *fstype,float3 *fsnormal,float *posdiv)
{
  if(simulate2d){
    if(tkernel==KERNEL_Wendland)ComputeFreeSurfaceTrackingT<KERNEL_Wendland,true >(np,npb,dvd,dcell,poscell,velrhop,code,corrmat,fstype,fsnormal,posdiv);
    else if(tkernel==KERNEL_Cubic)ComputeFreeSurfaceTrackingT<KERNEL_Cubic,true >(np,npb,dvd,dcell,poscell,velrhop,code,corrmat,fstype,fsnormal,posdiv);
    else throw "Kernel unknown.";
  }
  else{
    if(tkernel==KERNEL_Wendland)ComputeFreeSurfaceTrackingT<KERNEL_Wendland,false>(np,npb,dvd,dcell,poscell,velrhop,code,corrmat,fstype,fsnormal,posdiv);
    else if(tkernel==KERNEL_Cubic)ComputeFreeSurfaceTrackingT<KERNEL_Cubic,false>(np,npb,dvd,dcell,poscell,velrhop,code,corrmat,fstype,fsnormal,posdiv);
    else throw "Kernel unknown.";
  }
}

//==============================================================================
/// Returns true when FSType marks a drained free-surface soil particle.
//==============================================================================
__device__ bool KerHydroMechIsFreeSurface(unsigned p,const typecode *code,const unsigned *fstype){
  return(code && fstype && CODE_IsFluid(code[p]) && (fstype[p]==2 || fstype[p]==3));
}

//==============================================================================
/// Enforces drained pore pressure on free-surface particles.
//==============================================================================
__global__ void KerApplyFreeSurfacePorePressure(unsigned np,unsigned npb,unsigned drainfs,const typecode *code,const unsigned *fstype,float *porepress)
{
  const unsigned p=blockIdx.x*blockDim.x + threadIdx.x + npb;
  if(drainfs && p<np && KerHydroMechIsFreeSurface(p,code,fstype))porepress[p]=0.f;
}

void ApplyFreeSurfacePorePressure(unsigned np,unsigned npb,bool drainfs,const typecode *code,const unsigned *fstype,float *porepress)
{
  if(np>npb && porepress && fstype){
    dim3 sgrid=GetSimpleGridSize(np-npb,SPHBSIZE);
    KerApplyFreeSurfacePorePressure <<<sgrid,SPHBSIZE>>> (np,npb,(drainfs? 1u: 0u),code,fstype,porepress);
  }
}

//==============================================================================
/// Applies q0 top load to upward free-surface particles.
//==============================================================================
__global__ void KerApplyHydroMechTopLoadAcceleration(unsigned np,unsigned npb,float az,const typecode *code,const unsigned *fstype,const float3 *fsnormal,float3 *ace)
{
  const unsigned p=blockIdx.x*blockDim.x + threadIdx.x + npb;
  if(p<np && CODE_IsNormal(code[p]) && KerHydroMechIsFreeSurface(p,code,fstype)){
    const float3 n=fsnormal[p];
    const double nlen=sqrt(double(n.x)*n.x+double(n.y)*n.y+double(n.z)*n.z);
    bool upward=false;
    if(nlen>1e-12){
      const double gx=double(CTE.gravityx);
      const double gy=double(CTE.gravityy);
      const double gz=double(CTE.gravityz);
      const double gnorm=sqrt(gx*gx+gy*gy+gz*gz);
      if(gnorm<=1e-12)upward=(double(n.z)/nlen>0.35);
      else upward=(-(double(n.x)*gx+double(n.y)*gy+double(n.z)*gz)/(nlen*gnorm)>0.35);
    }
    if(upward){
      float3 a=ace[p];
      a.z+=az;
      ace[p]=a;
    }
  }
}

void ApplyHydroMechTopLoadAcceleration(unsigned np,unsigned npb,float az,const typecode *code,const unsigned *fstype,const float3 *fsnormal,float3 *ace)
{
  if(np>npb && az && code && fstype && fsnormal && ace){
    dim3 sgrid=GetSimpleGridSize(np-npb,SPHBSIZE);
    KerApplyHydroMechTopLoadAcceleration <<<sgrid,SPHBSIZE>>> (np,npb,az,code,fstype,fsnormal,ace);
  }
}

//==============================================================================
/// Updates pore pressure with an explicit Euler/Verlet-history step.
//==============================================================================
__global__ void KerUpdatePorePressure(unsigned np,unsigned npb,double dt,const typecode *code,const float *poreold,const float *porepressrate,float *porepressnew)
{
  const unsigned p=blockIdx.x*blockDim.x + threadIdx.x;
  if(p<np){
    if(p<npb || !CODE_IsFluid(code[p]))porepressnew[p]=poreold[p];
    else porepressnew[p]=float(double(poreold[p])+dt*double(porepressrate[p]));
  }
}

void UpdatePorePressureVerlet(unsigned np,unsigned npb,double dt2,const typecode *code,const float *poreold,const float *porepressrate,float *porepressnew)
{
  if(np && poreold && porepressrate && porepressnew){
    dim3 sgrid=GetSimpleGridSize(np,SPHBSIZE);
    KerUpdatePorePressure <<<sgrid,SPHBSIZE>>> (np,npb,dt2,code,poreold,porepressrate,porepressnew);
  }
}

void UpdatePorePressureSymplectic(unsigned np,unsigned npb,double dt,const typecode *code,const float *porepresspre,const float *porepressrate,float *porepress)
{
  if(np && porepresspre && porepressrate && porepress){
    dim3 sgrid=GetSimpleGridSize(np,SPHBSIZE);
    KerUpdatePorePressure <<<sgrid,SPHBSIZE>>> (np,npb,dt,code,porepresspre,porepressrate,porepress);
  }
}

//==============================================================================
/// Extrapolates pore pressure to mDBC boundaries without touching other mDBC fields.
//==============================================================================
template<TpKernel tker,bool sim2d> __global__ void KerPorePressureMdbcCorrection
  (unsigned n,float mdbcthreshold,double3 mapposmin,float poscellsize
  ,int scelldiv,int4 nc,int3 cellzero,const int2 *beginendcellfluid
  ,const double2 *posxy,const double *posz,const float4 *poscell,const typecode *code,const float4 *velrhop
  ,const float3 *boundnormal,const float *porepress0,float *porepress)
{
  const unsigned p1=blockIdx.x*blockDim.x + threadIdx.x;
  if(p1<n){
    const float3 bnormalp1=boundnormal[p1];
    if(!CODE_IsFluid(code[p1]) && (bnormalp1.x!=0 || bnormalp1.y!=0 || bnormalp1.z!=0)){
      double3 gposp1=make_double3(posxy[p1].x+bnormalp1.x,posxy[p1].y+bnormalp1.y,posz[p1]+bnormalp1.z);
      gposp1=(CTE.periactive!=0? KerUpdatePeriodicPos(gposp1): gposp1);
      const float4 gpscellp1=KerComputePosCell(gposp1,mapposmin,poscellsize);
      double sumwab=0,pwexcesssum=0,submerged=0;
      int ini1,fin1,ini2,fin2,ini3,fin3;
      cunsearch::InitCte(gposp1.x,gposp1.y,gposp1.z,scelldiv,nc,cellzero,ini1,fin1,ini2,fin2,ini3,fin3);
      for(int c3=ini3;c3<fin3;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
        unsigned pini,pfin=0; cunsearch::ParticleRange(c2,c3,ini1,fin1,beginendcellfluid,pini,pfin);
        if(pfin)for(unsigned p2=pini;p2<pfin;p2++)if(CODE_IsFluid(code[p2]) && velrhop[p2].w>0.f){
          float drx,dry,drz;
          if(sim2d){
            const float4 pscellp2=poscell[p2];
            drx=gpscellp1.x-pscellp2.x + CTE.poscellsize*(PSCEL_GetfX(gpscellp1.w)-PSCEL_GetfX(pscellp2.w));
            dry=0.f;
            drz=gpscellp1.z-pscellp2.z + CTE.poscellsize*(PSCEL_GetfZ(gpscellp1.w)-PSCEL_GetfZ(pscellp2.w));
          }
          else{
            const double2 p2xy=posxy[p2];
            drx=float(gposp1.x-p2xy.x);
            dry=float(gposp1.y-p2xy.y);
            drz=float(gposp1.z-posz[p2]);
          }
          const float rr2=drx*drx+dry*dry+drz*drz;
          if(rr2<=CTE.kernelsize2){
            float fac;
            const float wab=cufsph::GetKernel_WabFac<tker>(rr2,fac);
            const float vol2=CTE.massf/velrhop[p2].w;
            const double vwab=double(wab)*double(vol2);
            sumwab+=vwab;
            pwexcesssum+=vwab*double(porepress[p2]-porepress0[p2]);
            submerged-=double(vol2)*(double(drx)*fac*drx+double(dry)*fac*dry+double(drz)*fac*drz);
          }
        }
      }
      const bool active=(submerged>0. || sumwab>=double(mdbcthreshold) || (mdbcthreshold>=2.f && sumwab+2.>=double(mdbcthreshold)));
      if(active && sumwab>0.)porepress[p1]=float(double(porepress0[p1])+pwexcesssum/sumwab);
    }
  }
}

template<TpKernel tker,bool sim2d> void PorePressureMdbcCorrectionT(unsigned n,float mdbcthreshold,const StDivDataGpu &dvd,const tdouble3 &mapposmin
  ,const double2 *posxy,const double *posz,const float4 *poscell,const typecode *code,const float4 *velrhop,const float3 *boundnormal,const float *porepress0,float *porepress)
{
  if(n && porepress0 && porepress && boundnormal){
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    KerPorePressureMdbcCorrection<tker,sim2d> <<<sgrid,SPHBSIZE>>> (n,mdbcthreshold,Double3(mapposmin),CTE.poscellsize,dvd.scelldiv,dvd.nc,dvd.cellzero,dvd.beginendcell+dvd.cellfluid,posxy,posz,poscell,code,velrhop,boundnormal,porepress0,porepress);
  }
}

void PorePressureMdbcCorrection(TpKernel tkernel,bool simulate2d,unsigned n
  ,float mdbcthreshold,const StDivDataGpu &dvd,const tdouble3 &mapposmin
  ,const double2 *posxy,const double *posz,const float4 *poscell
  ,const typecode *code,const float4 *velrhop,const float3 *boundnormal
  ,const float *porepress0,float *porepress)
{
  if(simulate2d){
    if(tkernel==KERNEL_Wendland)PorePressureMdbcCorrectionT<KERNEL_Wendland,true >(n,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,velrhop,boundnormal,porepress0,porepress);
    else if(tkernel==KERNEL_Cubic)PorePressureMdbcCorrectionT<KERNEL_Cubic,true >(n,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,velrhop,boundnormal,porepress0,porepress);
    else throw "Kernel unknown.";
  }
  else{
    if(tkernel==KERNEL_Wendland)PorePressureMdbcCorrectionT<KERNEL_Wendland,false>(n,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,velrhop,boundnormal,porepress0,porepress);
    else if(tkernel==KERNEL_Cubic)PorePressureMdbcCorrectionT<KERNEL_Cubic,false>(n,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,velrhop,boundnormal,porepress0,porepress);
    else throw "Kernel unknown.";
  }
}

//==============================================================================
/// Shepard regularization of excess pore pressure.
//==============================================================================
template<TpKernel tker,bool sim2d> __global__ void KerShepardRegularizePorePressure(unsigned np,unsigned npb,unsigned drainfs
  ,int scelldiv,int4 nc,int3 cellzero,const int2 *beginendcell,unsigned cellfluid,const unsigned *dcell
  ,const double2 *posxy,const double *posz,const float4 *velrhop,const typecode *code
  ,const unsigned *fstype,const byte *boundmode,const float *porepress0,const float *porepress,float *porepressnew)
{
  const unsigned p1=blockIdx.x*blockDim.x + threadIdx.x + npb;
  if(p1<np && CODE_IsFluid(code[p1])){
    if(drainfs && KerHydroMechIsFreeSurface(p1,code,fstype)){
      porepressnew[p1]=0.f;
      return;
    }
    const double2 posp1xy=posxy[p1];
    const double posp1z=posz[p1];
    double sumwab=0,pwexcesssum=0;
    if(velrhop[p1].w>0.f){
      const double vol1=double(CTE.massf)/double(velrhop[p1].w);
      const double wab0=double(cufsph::GetKernel_Wab<tker>(0.f));
      sumwab+=wab0*vol1;
      pwexcesssum+=wab0*vol1*double(porepress[p1]-porepress0[p1]);
    }
    int ini1,fin1,ini2,fin2,ini3,fin3;
    cunsearch::InitCte(dcell[p1],scelldiv,nc,cellzero,ini1,fin1,ini2,fin2,ini3,fin3);
    for(int b2=0;b2<2;b2++){
      const bool boundp2=(b2==1);
      const int zini=(boundp2? ini3: ini3+cellfluid);
      const int zfin=(boundp2? fin3: fin3+cellfluid);
      for(int c3=zini;c3<zfin;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
        unsigned pini,pfin=0; cunsearch::ParticleRange(c2,c3,ini1,fin1,beginendcell,pini,pfin);
        if(pfin)for(unsigned p2=pini;p2<pfin;p2++){
          if(!boundp2 && !CODE_IsFluid(code[p2]))continue;
          if(boundp2 && CTE.tboundary==BC_MDBC && CTE.slipmode>=SLIP_NoSlip && boundmode && boundmode[p2]==BMODE_MDBC2OFF)continue;
          if(velrhop[p2].w<=0.f)continue;
          const double2 p2xy=posxy[p2];
          const double drx=posp1xy.x-p2xy.x;
          const double dry=(sim2d? 0.: posp1xy.y-p2xy.y);
          const double drz=posp1z-posz[p2];
          const float rr2=float(drx*drx+dry*dry+drz*drz);
          if(rr2<=CTE.kernelsize2 && rr2>=ALMOSTZERO){
            const double vol2=double(boundp2? CTE.massb: CTE.massf)/double(velrhop[p2].w);
            const double vwab=double(cufsph::GetKernel_Wab<tker>(rr2))*vol2;
            sumwab+=vwab;
            pwexcesssum+=vwab*double(porepress[p2]-porepress0[p2]);
          }
        }
      }
    }
    if(sumwab>0.)porepressnew[p1]=float(double(porepress0[p1])+pwexcesssum/sumwab);
  }
}

template<TpKernel tker,bool sim2d> void ShepardRegularizePorePressureT(unsigned np,unsigned npb,bool drainfs,const StDivDataGpu &dvd,const unsigned *dcell
  ,const double2 *posxy,const double *posz,const float4 *velrhop,const typecode *code,const unsigned *fstype,const byte *boundmode
  ,const float *porepress0,const float *porepress,float *porepressnew)
{
  if(np>npb && porepress0 && porepress && porepressnew){
    dim3 sgrid=GetSimpleGridSize(np-npb,SPHBSIZE);
    KerShepardRegularizePorePressure<tker,sim2d> <<<sgrid,SPHBSIZE>>> (np,npb,(drainfs? 1u: 0u),dvd.scelldiv,dvd.nc,dvd.cellzero,dvd.beginendcell,dvd.cellfluid,dcell,posxy,posz,velrhop,code,fstype,boundmode,porepress0,porepress,porepressnew);
  }
}

void ShepardRegularizePorePressure(TpKernel tkernel,bool simulate2d,unsigned np,unsigned npb
  ,bool drainfs,const StDivDataGpu &dvd,const unsigned *dcell
  ,const double2 *posxy,const double *posz,const float4 *velrhop,const typecode *code
  ,const unsigned *fstype,const byte *boundmode
  ,const float *porepress0,const float *porepress,float *porepressnew)
{
  if(simulate2d){
    if(tkernel==KERNEL_Wendland)ShepardRegularizePorePressureT<KERNEL_Wendland,true >(np,npb,drainfs,dvd,dcell,posxy,posz,velrhop,code,fstype,boundmode,porepress0,porepress,porepressnew);
    else if(tkernel==KERNEL_Cubic)ShepardRegularizePorePressureT<KERNEL_Cubic,true >(np,npb,drainfs,dvd,dcell,posxy,posz,velrhop,code,fstype,boundmode,porepress0,porepress,porepressnew);
    else throw "Kernel unknown.";
  }
  else{
    if(tkernel==KERNEL_Wendland)ShepardRegularizePorePressureT<KERNEL_Wendland,false>(np,npb,drainfs,dvd,dcell,posxy,posz,velrhop,code,fstype,boundmode,porepress0,porepress,porepressnew);
    else if(tkernel==KERNEL_Cubic)ShepardRegularizePorePressureT<KERNEL_Cubic,false>(np,npb,drainfs,dvd,dcell,posxy,posz,velrhop,code,fstype,boundmode,porepress0,porepress,porepressnew);
    else throw "Kernel unknown.";
  }
}

//------------------------------------------------------------------------------
/// Interaction of a particle with a set of particles. (Fluid/Float-Fluid/Float/Bound)
/// Realiza la interaccion de una particula con un conjunto de ellas. (Fluid/Float-Fluid/Float/Bound)
//------------------------------------------------------------------------------
__device__ void ComputeNoPenVel(const float dv,const float norm,const float dr,float &nopencount,float &nopenshift){
  const float vfc=dv*norm;
  if(vfc<0.f){
    const float ratio=max(fabsf(dr/norm),0.25f);
    const float factor=-4.f*ratio+3.f;
    nopencount+=1.f;
    nopenshift-=factor*dv*norm*norm;
  }
}

template<TpKernel tker,TpFtMode ftmode,bool lamsps,TpDensity tdensity,bool shift,bool symm>
  __device__ void KerInteractionForcesFluidBox(bool boundp2,unsigned p1
  ,const unsigned &pini,const unsigned &pfin,float visco
  ,const float *ftomassp
  ,const float4 *poscell,const float4 *velrhop,const byte *boundmode,const float3 *tangenvel,const float3 *motionvel,const float3 *boundnormal,const typecode *code,const unsigned *idp
  ,const float2 *sigma
  ,const float2 *artificialstress
  ,TpMdbc2Mode mdbc2
  ,float massp2,bool ftp1
  ,const float4 &pscellp1,const float4 &velrhop1,float pressp1
  ,float3 &gradvp1_xx_xy_xz,float3 &gradvp1_yx_yy_yz,float3 &gradvp1_zx_zy_zz
  ,float3 &acep1,float &arp1,float &visc,float &deltap1
  ,TpShifting shiftmode,float4 &shiftposfsp1
  ,float2 &sigmap1_xx_xy,float2 &sigmap1_xz_yy,float2 &sigmap1_yz_zz
  ,const float2 &artstressp1_xx_xy,const float2 &artstressp1_xz_yy,const float2 &artstressp1_yz_zz,const float invwabdp
  ,float2 &dsigmap1_xx_xy,float2 &dsigmap1_xz_yy,float2 &dsigmap1_yz_zz
  ,float3 &nopencountp1,float3 &nopenshiftp1
  ,const float *porepress,const tmatrix3d &porecorr,bool poreratep1,const float pwp1,double &pore_ratep1)
{
  const bool useartstress=(CTE.artificialstress && !ftp1 && invwabdp>0.f);
  const bool useporefeedback=(CTE.hydromech && porepress);
  for(int p2=pini;p2<pfin;p2++){
    const float4 pscellp2=poscell[p2];
    float drx=pscellp1.x-pscellp2.x + CTE.poscellsize*(PSCEL_GetfX(pscellp1.w)-PSCEL_GetfX(pscellp2.w));
    float dry=pscellp1.y-pscellp2.y + CTE.poscellsize*(PSCEL_GetfY(pscellp1.w)-PSCEL_GetfY(pscellp2.w));
    float drz=pscellp1.z-pscellp2.z + CTE.poscellsize*(PSCEL_GetfZ(pscellp1.w)-PSCEL_GetfZ(pscellp2.w));
    if(symm)dry=pscellp1.y+pscellp2.y + CTE.poscellsize*PSCEL_GetfY(pscellp2.w); //<vs_syymmetry>
    const float rr2=drx*drx+dry*dry+drz*drz;
    if(rr2<=CTE.kernelsize2 && rr2>=ALMOSTZERO){
      //-Computes kernel.
      float fac;
      float wab=0.f;
      if(useartstress)wab=cufsph::GetKernel_WabFac<tker>(rr2,fac);
      else fac=cufsph::GetKernel_Fac<tker>(rr2);
      const float frx=fac*drx,fry=fac*dry,frz=fac*drz; //-Gradients.

      //-Obtains mass of particle p2 if any floating bodies exist.
      //-Obtiene masa de particula p2 en caso de existir floatings.
      float massp2p=massp2;    //-Effective mass of particle p2 for this interaction.
      bool ftp2=false;         //-Indicates if it is floating. | Indica si es floating.
      float ftmassp2=massp2p;  //-Contains mass of floating body or massf if fluid. | Contiene masa de particula floating o massp2 si es bound o fluid.
      bool compute=true; //-Deactivated when DEM is used and is float-float or float-bound. | Se desactiva cuando se usa DEM y es float-float o float-bound.
      if(USE_FLOATING){
        const typecode cod=code[p2];
        ftp2=CODE_IsFloating(cod);
        ftmassp2=(ftp2? ftomassp[CODE_GetTypeValue(cod)]: massp2p);
        #ifdef DELTA_HEAVYFLOATING
          if(ftp2 && tdensity==DDT_DDT && ftmassp2<=(massp2p*1.2f))deltap1=FLT_MAX;
        #else
          if(ftp2 && tdensity==DDT_DDT)deltap1=FLT_MAX;
        #endif
        if(ftp2 && shift && shiftmode==SHIFT_NoBound)shiftposfsp1.x=FLT_MAX; //-Cancels shifting with floating bodies. | Con floatings anula shifting.
        compute=!(USE_FTEXTERNAL && ftp1 && (boundp2 || ftp2)); //-Deactivated when DEM or Chrono is used and is float-float or float-bound. | Se desactiva cuando se usa DEM o Chrono y es float-float o float-bound.
      }
      if(boundp2 && CTE.tboundary==BC_MDBC && CTE.slipmode>=SLIP_NoSlip && boundmode && !ftp2 && boundmode[p2]==BMODE_MDBC2OFF){
        massp2p=0;
        ftmassp2=0;
      }
      const float massp2final=(USE_FLOATING? ftmassp2: massp2p);

      float4 velrhop2=velrhop[p2];
      if(symm)velrhop2.y=-velrhop2.y; //<vs_syymmetry>
      if(poreratep1 && !symm && velrhop[p2].w>0.f){
        const bool validporep2=(boundp2 || CODE_IsFluid(code[p2]));
        const bool inactiveporebound=(boundp2 && CTE.tboundary==BC_MDBC && CTE.slipmode>=SLIP_NoSlip && boundmode && boundmode[p2]==BMODE_MDBC2OFF);
        if(validporep2 && !inactiveporebound){
          const double pdrx=double(drx);
          const double pdry=(CTE.simulate2d? 0.: double(dry));
          const double pdrz=double(drz);
          const double prr2=pdrx*pdrx+pdry*pdry+pdrz*pdrz;
          if(prr2<=double(CTE.kernelsize2) && prr2>=ALMOSTZERO){
            const double pfac=double(cufsph::GetKernel_Fac<tker>(float(prr2)));
            const double pfrx=pfac*pdrx;
            const double pfry=(CTE.simulate2d? 0.: pfac*pdry);
            const double pfrz=pfac*pdrz;
            const double pcfrx=porecorr.a11*pfrx+porecorr.a12*pfry+porecorr.a13*pfrz;
            const double pcfry=porecorr.a21*pfrx+porecorr.a22*pfry+porecorr.a23*pfrz;
            const double pcfrz=porecorr.a31*pfrx+porecorr.a32*pfry+porecorr.a33*pfrz;
            const double vol2=double((boundp2? CTE.massb: CTE.massf)/velrhop[p2].w);
            const double pdvx=double(velrhop[p2].x)-double(velrhop1.x);
            const double pdvy=(CTE.simulate2d? 0.: double(velrhop[p2].y)-double(velrhop1.y));
            const double pdvz=double(velrhop[p2].z)-double(velrhop1.z);
            const double pdotgrad=pdrx*pcfrx+pdry*pcfry+pdrz*pcfrz;
            const double divv=vol2*(pdvx*pcfrx+pdvy*pcfry+pdvz*pcfrz);
            const double lapw=vol2*double(pwp1-porepress[p2])*pdotgrad/double(prr2+CTE.eta2);
            const double lapz=vol2*pdrz*pdotgrad/double(prr2+CTE.eta2);
            pore_ratep1+=double(CTE.porekwn)*(-divv);
            if(CTE.hydraulicconductivity>0.f){
              const double seep=2.0*double(CTE.hydraulicconductivity)*lapw/(double(CTE.porewaterrho)*double(CTE.poreghyd))
                + (double(CTE.poreghyd)>0.? 2.0*double(CTE.hydraulicconductivity)*lapz: 0.0);
              pore_ratep1+=double(CTE.porekwn)*seep;
            }
          }
        }
      }
      //===get stress of p2 ==== mdbr
	  float2 sigmap2_xx_xy=sigma[p2*3];
	  float2 sigmap2_xz_yy=sigma[p2*3+1];
	  float2 sigmap2_yz_zz=sigma[p2*3+2];
      //-Velocity derivative (Momentum equation).
      if(compute){
        //const float pressp2=cufsph::ComputePressCte(velrhop2.w);
        //const float prs=(pressp1+pressp2)/(velrhop1.w*velrhop2.w)
        //  +(tker==KERNEL_Cubic? cufsph::GetKernelCubic_Tensil(rr2,velrhop1.w,pressp1,velrhop2.w,pressp2): 0);
        //const float p_vpm=-prs*(USE_FLOATING? ftmassp2: massp2);
        //acep1.x+=p_vpm*frx; acep1.y+=p_vpm*fry; acep1.z+=p_vpm*frz;
          const float invrhop1_2=1.f/(velrhop1.w*velrhop1.w);
          const float invrhop2_2=1.f/(velrhop2.w*velrhop2.w);
          const float prsxx = massp2final*(sigmap1_xx_xy.x*invrhop1_2 + sigmap2_xx_xy.x*invrhop2_2);
		  const float prsyy = massp2final*(sigmap1_xz_yy.y*invrhop1_2 + sigmap2_xz_yy.y*invrhop2_2);
		  const float prszz = massp2final*(sigmap1_yz_zz.y*invrhop1_2 + sigmap2_yz_zz.y*invrhop2_2);
		  const float prsxy = massp2final*(sigmap1_xx_xy.y*invrhop1_2 + sigmap2_xx_xy.y*invrhop2_2);
		  const float prsxz = massp2final*(sigmap1_xz_yy.x*invrhop1_2 + sigmap2_xz_yy.x*invrhop2_2);
		  const float prsyz = massp2final*(sigmap1_yz_zz.x*invrhop1_2 + sigmap2_yz_zz.x*invrhop2_2);
		  acep1.x += (prsxx*frx + prsxy*fry + prsxz*frz); acep1.y += (prsyy*fry + prsxy*frx + prsyz*frz); acep1.z += (prszz*frz + prsyz*fry + prsxz*frx);//form 1
          if(useporefeedback && !ftp1 && !ftp2){
            const float prspw=-massp2final*(porepress[p1]+porepress[p2])/(velrhop1.w*velrhop2.w);
            acep1.x+=prspw*frx; acep1.y+=prspw*fry; acep1.z+=prspw*frz;
          }
          if(useartstress && !ftp2){
            const float2 artstressp2_xx_xy=artificialstress[p2*3];
            const float2 artstressp2_xz_yy=artificialstress[p2*3+1];
            const float2 artstressp2_yz_zz=artificialstress[p2*3+2];
            const float ratio=wab*invwabdp;
            const float arsxx0=artstressp1_xx_xy.x+artstressp2_xx_xy.x;
            const float arsyy0=artstressp1_xz_yy.y+artstressp2_xz_yy.y;
            const float arszz0=artstressp1_yz_zz.y+artstressp2_yz_zz.y;
            const float arsxy0=artstressp1_xx_xy.y+artstressp2_xx_xy.y;
            const float arsxz0=artstressp1_xz_yy.x+artstressp2_xz_yy.x;
            const float arsyz0=artstressp1_yz_zz.x+artstressp2_yz_zz.x;
            if(ratio>0.f && (arsxx0 || arsyy0 || arszz0 || arsxy0 || arsxz0 || arsyz0)){
              const float artmass=massp2final*powf(ratio,CTE.artificialstressexp);
              const float arsxx=artmass*arsxx0;
              const float arsyy=artmass*arsyy0;
              const float arszz=artmass*arszz0;
              const float arsxy=artmass*arsxy0;
              const float arsxz=artmass*arsxz0;
              const float arsyz=artmass*arsyz0;
              acep1.x+=(arsxx*frx+arsxy*fry+arsxz*frz);
              acep1.y+=(arsxy*frx+arsyy*fry+arsyz*frz);
              acep1.z+=(arsxz*frx+arsyz*fry+arszz*frz);
            }
          }
      }
      
      //-Density derivative (Continuity equation).
      const float dvx_rhop=velrhop1.x-velrhop2.x, dvy_rhop=velrhop1.y-velrhop2.y, dvz_rhop=velrhop1.z-velrhop2.z;
      float dvx_visc=dvx_rhop, dvy_visc=dvy_rhop, dvz_visc=dvz_rhop;
      if(boundp2 && CTE.tboundary==BC_MDBC && CTE.slipmode>=SLIP_NoSlip && !ftp2 && tangenvel){
        float3 tangentvelp2=tangenvel[p2];
        if(symm)tangentvelp2.y=-tangentvelp2.y; //<vs_syymmetry>
        dvx_visc=velrhop1.x-tangentvelp2.x;
        dvy_visc=velrhop1.y-tangentvelp2.y;
        dvz_visc=velrhop1.z-tangentvelp2.z;
      }
      if(compute)arp1+=massp2final*(dvx_rhop*frx+dvy_rhop*fry+dvz_rhop*frz)*(velrhop1.w/velrhop2.w);

      const float cbar=CTE.cs0;
      const float dot3=(tdensity!=DDT_None || shift? drx*frx+dry*fry+drz*frz: 0);
      //-Density Diffusion Term (Molteni and Colagrossi 2009).
//      if(tdensity==DDT_DDT && deltap1!=FLT_MAX){
//        const float rhop1over2=velrhop1.w/velrhop2.w;
//        const float visc_densi=CTE.ddtkh*cbar*(rhop1over2-1.f)/(rr2+CTE.eta2);
//        const float delta=visc_densi*dot3*(USE_FLOATING? ftmassp2: massp2);
        //deltap1=(boundp2? FLT_MAX: deltap1+delta);
//        deltap1=(boundp2 && CTE.tboundary==BC_DBC? FLT_MAX: deltap1+delta);
//      }
      //-Stress Diffusion Term (Form 1)
      if(tdensity==DDT_DDT && dsigmap1_xx_xy.x!=FLT_MAX){
        const float massrhop = massp2final/velrhop2.w;
        const float visc_stress=CTE.ddtkh*cbar*massrhop/(rr2+CTE.eta2);
        const float dsigmaxx=sigmap1_xx_xy.x-sigmap2_xx_xy.x;
        const float dsigmayy=sigmap1_xz_yy.y-sigmap2_xz_yy.y;
        const float dsigmazz=sigmap1_yz_zz.y-sigmap2_yz_zz.y;
        const float dsigmaxy=sigmap1_xx_xy.y-sigmap2_xx_xy.y;
        const float dsigmaxz=sigmap1_xz_yy.x-sigmap2_xz_yy.x;
        const float dsigmayz=sigmap1_yz_zz.x-sigmap2_yz_zz.x;
        dsigmap1_xx_xy.x=(boundp2&&CTE.tboundary==BC_DBC? FLT_MAX: dsigmap1_xx_xy.x+visc_stress*dot3*dsigmaxx);
        dsigmap1_xz_yy.y+=visc_stress*dot3*dsigmayy;
        dsigmap1_yz_zz.y+=visc_stress*dot3*dsigmazz;
        dsigmap1_xx_xy.y+=visc_stress*dot3*dsigmaxy;
        dsigmap1_xz_yy.x+=visc_stress*dot3*dsigmaxz;
        dsigmap1_yz_zz.x+=visc_stress*dot3*dsigmayz;
      }
      //-Density Diffusion Term (Fourtakas et al 2019).
//      if((tdensity==DDT_DDT2 || (tdensity==DDT_DDT2Full && !boundp2)) && deltap1!=FLT_MAX && !ftp2){
//        const float rh=1.f+CTE.ddtgz*drz;
//        const float drhop=CTE.rhopzero*pow(rh,1.f/CTE.gamma)-CTE.rhopzero;  
//        const float visc_densi=CTE.ddtkh*cbar*((velrhop2.w-velrhop1.w)-drhop)/(rr2+CTE.eta2);
//        const float delta=visc_densi*dot3*massp2/velrhop2.w;
//        deltap1=(boundp2? FLT_MAX: deltap1-delta); //-blocks it makes it boil - bloody DBC
//      }
      //-Stress Diffusion Term (Form 2)
      if((tdensity==DDT_DDT2 || (tdensity==DDT_DDT2Full && !boundp2)) && dsigmap1_xx_xy.x!=FLT_MAX && !ftp2){
        const float massrhop = massp2final/velrhop2.w;
        const float visc_stress=CTE.ddtkh*cbar*massrhop/(rr2+CTE.eta2);
        const float dsigmaxx=sigmap1_xx_xy.x-sigmap2_xx_xy.x;
        const float dsigmayy=sigmap1_xz_yy.y-sigmap2_xz_yy.y;
        const float dsigmazz=sigmap1_yz_zz.y-sigmap2_yz_zz.y;
        const float dsigmaxy=sigmap1_xx_xy.y-sigmap2_xx_xy.y;
        const float dsigmaxz=sigmap1_xz_yy.x-sigmap2_xz_yy.x;
        const float dsigmayz=sigmap1_yz_zz.x-sigmap2_yz_zz.x;
        const float dsigzS = CTE.sdtgz*drz;
		const float dsigxS = CTE.k0*dsigzS;
		const float dsigyS = CTE.k0*dsigzS;
        dsigmap1_xx_xy.x=(boundp2? FLT_MAX: dsigmap1_xx_xy.x+visc_stress*dot3*(dsigmaxx+dsigxS));
        dsigmap1_xz_yy.y+=visc_stress*dot3*(dsigmayy+dsigyS);
        dsigmap1_yz_zz.y+=visc_stress*dot3*(dsigmazz+dsigzS);
        dsigmap1_xx_xy.y+=visc_stress*dot3*dsigmaxy;
        dsigmap1_xz_yy.x+=visc_stress*dot3*dsigmaxz;
        dsigmap1_yz_zz.x+=visc_stress*dot3*dsigmayz;
      }
      //-Shifting correction.
      if(shift && shiftposfsp1.x!=FLT_MAX){
        const float massrhop=massp2final/velrhop2.w;
        const bool noshift=(boundp2 && (shiftmode==SHIFT_NoBound || (shiftmode==SHIFT_NoFixed && CODE_IsFixed(code[p2]))));
        shiftposfsp1.x=(noshift? FLT_MAX: shiftposfsp1.x+massrhop*frx); //-Removes shifting for the boundaries. | Con boundary anula shifting.
        shiftposfsp1.y+=massrhop*fry;
        shiftposfsp1.z+=massrhop*frz;
        shiftposfsp1.w-=massrhop*dot3;
      }

      if(boundp2 && mdbc2==MDBC2_NoPen && !ftp2 && boundnormal && motionvel){
        const float rrmag=sqrtf(rr2);
        if(rrmag<1.25f*CTE.dp){
          float3 normp2=boundnormal[p2];
          float3 movvelp2=motionvel[p2];
          if(symm){
            normp2.y=-normp2.y;
            movvelp2.y=-movvelp2.y;
          }
          const float norm=sqrtf(normp2.x*normp2.x+normp2.y*normp2.y+normp2.z*normp2.z);
          if(norm>0.f){
            const float normx=normp2.x/norm;
            const float normy=normp2.y/norm;
            const float normz=normp2.z/norm;
            const float normdist=(normx*drx+normy*dry+normz*drz);
            if(normdist<0.75f*norm && norm<1.75f*CTE.dp){
              const float absx=fabsf(normx);
              const float absy=fabsf(normy);
              const float absz=fabsf(normz);
              if(drx*normx<0.75f && absx>0.001f*CTE.dp)ComputeNoPenVel(velrhop1.x-movvelp2.x,normx,drx,nopencountp1.x,nopenshiftp1.x);
              if(dry*normy<0.75f && absy>0.001f*CTE.dp)ComputeNoPenVel(velrhop1.y-movvelp2.y,normy,dry,nopencountp1.y,nopenshiftp1.y);
              if(drz*normz<0.75f && absz>0.001f*CTE.dp)ComputeNoPenVel(velrhop1.z-movvelp2.z,normz,drz,nopencountp1.z,nopenshiftp1.z);
            }
          }
        }
      }

      //===== Viscosity ===== 
      if(compute){
        const float dot=drx*dvx_visc + dry*dvy_visc + drz*dvz_visc;
        const float dot_rr2=dot/(rr2+CTE.eta2);
        visc=max(dot_rr2,visc);  //ViscDt=max(dot/(rr2+Eta2),ViscDt);
        ///SPH velocity gradients calculation
        const float volp2=-massp2final/velrhop2.w;
        float dv=dvx_visc*volp2;  gradvp1_xx_xy_xz.x+=dv*frx; gradvp1_xx_xy_xz.y+=dv*fry; gradvp1_xx_xy_xz.z+=dv*frz;
              dv=dvy_visc*volp2;  gradvp1_yx_yy_yz.x+=dv*frx; gradvp1_yx_yy_yz.y+=dv*fry; gradvp1_yx_yy_yz.z+=dv*frz;
              dv=dvz_visc*volp2;  gradvp1_zx_zy_zz.x+=dv*frx; gradvp1_zx_zy_zz.y+=dv*fry; gradvp1_zx_zy_zz.z+=dv*frz;
        if(!lamsps){//-Artificial viscosity.
          if(dot<0){
            const float amubar=CTE.kernelh*dot_rr2;  //amubar=CTE.kernelh*dot/(rr2+CTE.eta2);
            const float robar=(velrhop1.w+velrhop2.w)*0.5f;
            const float pi_visc=(-visco*cbar*amubar/robar)*massp2final;
            acep1.x-=pi_visc*frx; acep1.y-=pi_visc*fry; acep1.z-=pi_visc*frz;
          }
        }
        else{//-Laminar+SPS viscosity.
          {//-Laminar contribution.
            const float robar2=(velrhop1.w+velrhop2.w);
            const float temp=4.f*visco/((rr2+CTE.eta2)*robar2);  //-Simplication of temp=2.0f*visco/((rr2+CTE.eta2)*robar); robar=(rhopp1+velrhop2.w)*0.5f;
            const float vtemp=massp2final*temp*(drx*frx+dry*fry+drz*frz);  
            acep1.x+=vtemp*dvx_visc; acep1.y+=vtemp*dvy_visc; acep1.z+=vtemp*dvz_visc;
          }
          //-SPS turbulence model. Removed
          /*float2 taup2_xx_xy = taup1_xx_xy; //-taup1 is always zero when p1 is not fluid. | taup1 siempre es cero cuando p1 no es fluid.
          float2 taup2_xz_yy=taup1_xz_yy;
          float2 taup2_yz_zz=taup1_yz_zz;
          if(!boundp2 && (USE_NOFLOATING || !ftp2)){//-When p2 is fluid.
            float2 taup2=tauff[p2*3];     taup2_xx_xy.x+=taup2.x; taup2_xx_xy.y+=taup2.y;
                   taup2=tauff[p2*3+1];   taup2_xz_yy.x+=taup2.x; taup2_xz_yy.y+=taup2.y;
                   taup2=tauff[p2*3+2];   taup2_yz_zz.x+=taup2.x; taup2_yz_zz.y+=taup2.y;
          }
          acep1.x+=(USE_FLOATING? ftmassp2: massp2)*(taup2_xx_xy.x*frx+taup2_xx_xy.y*fry+taup2_xz_yy.x*frz);
          acep1.y+=(USE_FLOATING? ftmassp2: massp2)*(taup2_xx_xy.y*frx+taup2_xz_yy.y*fry+taup2_yz_zz.x*frz);
          acep1.z+=(USE_FLOATING? ftmassp2: massp2)*(taup2_xz_yy.x*frx+taup2_yz_zz.x*fry+taup2_yz_zz.y*frz);*/
        }
      }
    }
  }
}

//------------------------------------------------------------------------------
/// Interaction between particles. Fluid/Float-Fluid/Float or Fluid/Float-Bound.
/// Includes artificial/laminar viscosity and normal/DEM floating bodies.
///
/// Realiza interaccion entre particulas. Fluid/Float-Fluid/Float or Fluid/Float-Bound
/// Incluye visco artificial/laminar y floatings normales/dem.
//------------------------------------------------------------------------------
template<TpKernel tker,TpFtMode ftmode,bool lamsps,TpDensity tdensity,bool shift,bool symm>
  __global__ void KerInteractionForcesFluid(unsigned n,unsigned pinit,float viscob,float viscof
  ,int scelldiv,int4 nc,int3 cellzero,const int2 *begincell,unsigned cellfluid,const unsigned *dcell
  ,const float *ftomassp
  ,const float4 *poscell,const float4 *velrhop,const tmatrix3d *corrmat,const byte *boundmode,const float3 *tangenvel
  ,const float3 *motionvel,const float3 *boundnormal,float4 *nopenshift,const typecode *code,const unsigned *idp
  ,const float2 *sigma,const float2 *artificialstress,float2 *rsigma
  ,TpMdbc2Mode mdbc2
  ,const float *porepress,float *porepressrate,const unsigned *fstype,const float3 *fsnormal,unsigned hydrodrainfs
  ,float *viscdt,float *ar,float3 *ace,float *delta
  ,TpShifting shiftmode,float4 *shiftposfs)
{
  const unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    const unsigned p1=p+pinit;      //-Number of particle.
    float visc=0,arp1=0,deltap1=0;
    float3 acep1=make_float3(0,0,0);
    float2 rsigmap1_xx_xy=make_float2(0,0);
    float2 rsigmap1_xz_yy=make_float2(0,0);
    float2 rsigmap1_yz_zz=make_float2(0,0);
    //-Stress diffusion
    float2 dsigmap1_xx_xy=make_float2(0,0);
    float2 dsigmap1_xz_yy=make_float2(0,0);
    float2 dsigmap1_yz_zz=make_float2(0,0);

    float2 e_tensorp1_xx_xy=make_float2(0,0);//strain rate tensor
    float2 e_tensorp1_xz_yy=make_float2(0,0);
    float2 e_tensorp1_yz_zz=make_float2(0,0);

    float3 w_tensorp1_xy_yz_xz=make_float3(0,0,0);//spin rate tensor
    double pore_ratep1=0;
    float3 nopencountp1=make_float3(0,0,0);
    float3 nopenshiftp1=make_float3(0,0,0);

    //-Variables for Shifting.
    float4 shiftposfsp1;
    if(shift)shiftposfsp1=shiftposfs[p1];

    //-Obtains data of particle p1 in case there are floating bodies.
    bool ftp1=false; //-Indicates if it is floating. | Indica si es floating.
    if(USE_FLOATING){
      const typecode cod=code[p1];
      ftp1=CODE_IsFloating(cod);
      if(ftp1 && tdensity!=DDT_None)deltap1=FLT_MAX; //-DDT is not applied to floating particles.
      if(ftp1 && tdensity!=DDT_None){dsigmap1_xx_xy.x=FLT_MAX;}
      if(ftp1 && shift)shiftposfsp1.x=FLT_MAX; //-Shifting is not calculated for floating bodies. | Para floatings no se calcula shifting.
    }

    //-Obtains basic data of particle p1.
    const float4 pscellp1=poscell[p1];
    const float4 velrhop1=velrhop[p1];
    const float pressp1=cufsph::ComputePressCte(velrhop1.w);
    const bool rsymp1=(symm && PSCEL_GetPartY(__float_as_uint(pscellp1.w))==0); //<vs_syymmetry>
    const bool poreratep1=(CTE.hydromech && porepress && porepressrate && CODE_IsFluid(code[p1]) && !(hydrodrainfs && KerHydroMechIsFreeSurface(p1,code,fstype)));
    const float pwp1=(poreratep1? porepress[p1]: 0.f);
    tmatrix3d porecorr;
    porecorr.a11=porecorr.a12=porecorr.a13=0;
    porecorr.a21=porecorr.a22=porecorr.a23=0;
    porecorr.a31=porecorr.a32=porecorr.a33=0;
    if(poreratep1 && corrmat)porecorr=corrmat[p1];
    //-Obtains stress tensor == mdbr
    float2 sigmap1_xx_xy=sigma[p1*3];
    float2 sigmap1_xz_yy=sigma[p1*3+1];
    float2 sigmap1_yz_zz=sigma[p1*3+2];
    float2 artstressp1_xx_xy=make_float2(0,0);
    float2 artstressp1_xz_yy=make_float2(0,0);
    float2 artstressp1_yz_zz=make_float2(0,0);
    const bool useartstressp1=(CTE.artificialstress && !ftp1 && CTE.artificialstresscoef>0.f);
    const float wabdp=(useartstressp1? cufsph::GetKernel_Wab<tker>(CTE.dp*CTE.dp): 0.f);
    const float invwabdp=(wabdp>0.f? 1.f/wabdp: 0.f);
    if(useartstressp1 && invwabdp>0.f){
      artstressp1_xx_xy=artificialstress[p1*3];
      artstressp1_xz_yy=artificialstress[p1*3+1];
      artstressp1_yz_zz=artificialstress[p1*3+2];
    }
    //-Obtains elastic parameters
    float modulus_K=CTE.modulus_K;
    float modulus_G=CTE.modulus_G;

    //-Variables for Laminar+SPS.
    /*float2 taup1_xx_xy, taup1_xz_yy, taup1_yz_zz;
    if(lamsps){
      taup1_xx_xy=tauff[p1*3];
      taup1_xz_yy=tauff[p1*3+1];
      taup1_yz_zz=tauff[p1*3+2];
    }*/
    //-Variables for Laminar+SPS (computation).
    float3 gradvp1_xx_xy_xz, gradvp1_yx_yy_yz,gradvp1_zx_zy_zz;
    //if(tvisco!=VISCO_Artificial) {
    gradvp1_xx_xy_xz=make_float3(0,0,0);
    gradvp1_yx_yy_yz=make_float3(0,0,0);
    gradvp1_zx_zy_zz=make_float3(0,0,0);

    //-Obtains neighborhood search limits.
    int ini1,fin1,ini2,fin2,ini3,fin3;
    cunsearch::InitCte(dcell[p1],scelldiv,nc,cellzero,ini1,fin1,ini2,fin2,ini3,fin3);

    //-Interaction with fluids.
    ini3+=cellfluid; fin3+=cellfluid;
    for(int c3=ini3;c3<fin3;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
      unsigned pini,pfin=0;  cunsearch::ParticleRange(c2,c3,ini1,fin1,begincell,pini,pfin);
      if(pfin){
                          KerInteractionForcesFluidBox<tker,ftmode,lamsps,tdensity,shift,false> (false,p1,pini,pfin,viscof,ftomassp,poscell,velrhop,boundmode,tangenvel,motionvel,boundnormal,code,idp,sigma,artificialstress,mdbc2,CTE.massf,ftp1,pscellp1,velrhop1,pressp1,gradvp1_xx_xy_xz,gradvp1_yx_yy_yz,gradvp1_zx_zy_zz,acep1,arp1,visc,deltap1,shiftmode,shiftposfsp1,sigmap1_xx_xy,sigmap1_xz_yy,sigmap1_yz_zz,artstressp1_xx_xy,artstressp1_xz_yy,artstressp1_yz_zz,invwabdp,dsigmap1_xx_xy,dsigmap1_xz_yy,dsigmap1_yz_zz,nopencountp1,nopenshiftp1,porepress,porecorr,poreratep1,pwp1,pore_ratep1);
        if(symm && rsymp1)KerInteractionForcesFluidBox<tker,ftmode,lamsps,tdensity,shift,true > (false,p1,pini,pfin,viscof,ftomassp,poscell,velrhop,boundmode,tangenvel,motionvel,boundnormal,code,idp,sigma,artificialstress,mdbc2,CTE.massf,ftp1,pscellp1,velrhop1,pressp1,gradvp1_xx_xy_xz,gradvp1_yx_yy_yz,gradvp1_zx_zy_zz,acep1,arp1,visc,deltap1,shiftmode,shiftposfsp1,sigmap1_xx_xy,sigmap1_xz_yy,sigmap1_yz_zz,artstressp1_xx_xy,artstressp1_xz_yy,artstressp1_yz_zz,invwabdp,dsigmap1_xx_xy,dsigmap1_xz_yy,dsigmap1_yz_zz,nopencountp1,nopenshiftp1,porepress,porecorr,poreratep1,pwp1,pore_ratep1); //<vs_syymmetry>
      }
    }
    //-Interaction with boundaries.
    ini3-=cellfluid; fin3-=cellfluid;
    for(int c3=ini3;c3<fin3;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
      unsigned pini,pfin=0;  cunsearch::ParticleRange(c2,c3,ini1,fin1,begincell,pini,pfin);
      if(pfin){
                        KerInteractionForcesFluidBox<tker,ftmode,lamsps,tdensity,shift,false> (true ,p1,pini,pfin,viscob,ftomassp,poscell,velrhop,boundmode,tangenvel,motionvel,boundnormal,code,idp,sigma,artificialstress,mdbc2,CTE.massb,ftp1,pscellp1,velrhop1,pressp1,gradvp1_xx_xy_xz,gradvp1_yx_yy_yz,gradvp1_zx_zy_zz,acep1,arp1,visc,deltap1,shiftmode,shiftposfsp1,sigmap1_xx_xy,sigmap1_xz_yy,sigmap1_yz_zz,artstressp1_xx_xy,artstressp1_xz_yy,artstressp1_yz_zz,invwabdp,dsigmap1_xx_xy,dsigmap1_xz_yy,dsigmap1_yz_zz,nopencountp1,nopenshiftp1,porepress,porecorr,poreratep1,pwp1,pore_ratep1);
      if(symm && rsymp1)KerInteractionForcesFluidBox<tker,ftmode,lamsps,tdensity,shift,true > (true ,p1,pini,pfin,viscob,ftomassp,poscell,velrhop,boundmode,tangenvel,motionvel,boundnormal,code,idp,sigma,artificialstress,mdbc2,CTE.massb,ftp1,pscellp1,velrhop1,pressp1,gradvp1_xx_xy_xz,gradvp1_yx_yy_yz,gradvp1_zx_zy_zz,acep1,arp1,visc,deltap1,shiftmode,shiftposfsp1,sigmap1_xx_xy,sigmap1_xz_yy,sigmap1_yz_zz,artstressp1_xx_xy,artstressp1_xz_yy,artstressp1_yz_zz,invwabdp,dsigmap1_xx_xy,dsigmap1_xz_yy,dsigmap1_yz_zz,nopencountp1,nopenshiftp1,porepress,porecorr,poreratep1,pwp1,pore_ratep1);
      }
    }
    if(CTE.soilstressrategradcorr && !ftp1 && corrmat){
      const tmatrix3d invcorr=corrmat[p1];
      gradvp1_xx_xy_xz=KerApplyGradCorr(gradvp1_xx_xy_xz,invcorr);
      gradvp1_yx_yy_yz=KerApplyGradCorr(gradvp1_yx_yy_yz,invcorr);
      gradvp1_zx_zy_zz=KerApplyGradCorr(gradvp1_zx_zy_zz,invcorr);
    }
    //Calculate strain/spin rate tensor mdbr
    GetStrainSpinRateTensor_sym(gradvp1_xx_xy_xz,gradvp1_yx_yy_yz,gradvp1_zx_zy_zz,e_tensorp1_xx_xy,e_tensorp1_xz_yy,e_tensorp1_yz_zz,w_tensorp1_xy_yz_xz);
    //Calculate stress rate tensor mdbr
    GetStressRateTensor_Elastic(e_tensorp1_xx_xy,e_tensorp1_xz_yy,e_tensorp1_yz_zz,w_tensorp1_xy_yz_xz,sigmap1_xx_xy,sigmap1_xz_yy,sigmap1_yz_zz,modulus_K,modulus_G,rsigmap1_xx_xy,rsigmap1_xz_yy,rsigmap1_yz_zz);
    if(mdbc2==MDBC2_NoPen && nopenshift && (nopencountp1.x>0.f || nopencountp1.y>0.f || nopencountp1.z>0.f)){
      float4 ns=make_float4(0,0,0,10.f);
      if(nopencountp1.x>0.f)ns.x=nopenshiftp1.x/nopencountp1.x;
      if(nopencountp1.y>0.f)ns.y=nopenshiftp1.y/nopencountp1.y;
      if(nopencountp1.z>0.f)ns.z=nopenshiftp1.z/nopencountp1.z;
      nopenshift[p1]=ns;
    }
    //-Stores results.
    if(poreratep1)porepressrate[p1]+=float(pore_ratep1);
    if(shift||arp1||acep1.x||acep1.y||acep1.z||visc){
      if(tdensity!=DDT_None){
        if(delta){
          const float rdelta=delta[p1];
          delta[p1]=(rdelta==FLT_MAX || deltap1==FLT_MAX? FLT_MAX: rdelta+deltap1);
        }
        else if(deltap1!=FLT_MAX)arp1+=deltap1;
        if(dsigmap1_xx_xy.x!=FLT_MAX){
        rsigmap1_xx_xy.x+=dsigmap1_xx_xy.x;
        rsigmap1_xx_xy.y+=dsigmap1_xx_xy.y;
        rsigmap1_xz_yy.x+=dsigmap1_xz_yy.x;
        rsigmap1_xz_yy.y+=dsigmap1_xz_yy.y;
        rsigmap1_yz_zz.x+=dsigmap1_yz_zz.x;
        rsigmap1_yz_zz.y+=dsigmap1_yz_zz.y;
        }
      }
      ar[p1]+=arp1;
      float3 r=ace[p1]; r.x+=acep1.x; r.y+=acep1.y; r.z+=acep1.z; ace[p1]=r;
      //===mdbr
      float2 rs;
      rs=rsigma[p1*3];	    rs=make_float2(rs.x+rsigmap1_xx_xy.x,rs.y+rsigmap1_xx_xy.y); rsigma[p1*3]=rs;
	  rs=rsigma[p1*3+1];	rs=make_float2(rs.x+rsigmap1_xz_yy.x,rs.y+rsigmap1_xz_yy.y); rsigma[p1*3+1]=rs;
	  rs=rsigma[p1*3+2];	rs=make_float2(rs.x+rsigmap1_yz_zz.x,rs.y+rsigmap1_yz_zz.y); rsigma[p1*3+2]=rs;
      //===
      if(visc>viscdt[p1])viscdt[p1]=visc;
    //  if(lamsps){
    //    float2 rg;
    //    rg=gradvelff[p1*3  ];  rg=make_float2(rg.x+grap1_xx_xy.x,rg.y+grap1_xx_xy.y);  gradvelff[p1*3  ]=rg;
    //    rg=gradvelff[p1*3+1];  rg=make_float2(rg.x+grap1_xz_yy.x,rg.y+grap1_xz_yy.y);  gradvelff[p1*3+1]=rg;
    //    rg=gradvelff[p1*3+2];  rg=make_float2(rg.x+grap1_yz_zz.x,rg.y+grap1_yz_zz.y);  gradvelff[p1*3+2]=rg;
    //  }
      if(shift)shiftposfs[p1]=shiftposfsp1;
    }
  }
}
//------------------------------------------------------------------------------
/// Interaction of a particle with a set of particles. (Fluid/Float-Fluid/Float/Bound)
/// Realiza la interaccion de una particula con un conjunto de ellas. (Fluid/Float-Fluid/Float/Bound)
//------------------------------------------------------------------------------
template<TpKernel tker,TpFtMode ftmode,bool lamsps,TpDensity tdensity,bool shift,bool symm>
  __device__ void KerInteractionForcesSoilsBox(bool boundp2,unsigned p1
  ,const unsigned &pini,const unsigned &pfin,float visco
  ,const float *ftomassp
  ,const float4 *poscell,const float4 *velrhop,const typecode *code,const unsigned *idp
  ,const float2 *sigma
  ,float massp2,bool ftp1
  ,const float4 &pscellp1,const float4 &velrhop1,float pressp1
  ,float2 &e_tensorp1_xx_xy,float2 &e_tensorp1_xz_yy,float2 &e_tensorp1_yz_zz,float3 &w_tensorp1_xy_yz_xz
  ,float3 &acep1,float &arp1,float &visc,float &deltap1
  ,TpShifting shiftmode,float4 &shiftposfsp1
  ,float2 &sigmap1_xx_xy,float2 &sigmap1_xz_yy,float2 &sigmap1_yz_zz)
{
  for(int p2=pini;p2<pfin;p2++){
    const float4 pscellp2=poscell[p2];
    float drx=pscellp1.x-pscellp2.x + CTE.poscellsize*(PSCEL_GetfX(pscellp1.w)-PSCEL_GetfX(pscellp2.w));
    float dry=pscellp1.y-pscellp2.y + CTE.poscellsize*(PSCEL_GetfY(pscellp1.w)-PSCEL_GetfY(pscellp2.w));
    float drz=pscellp1.z-pscellp2.z + CTE.poscellsize*(PSCEL_GetfZ(pscellp1.w)-PSCEL_GetfZ(pscellp2.w));
    if(symm)dry=pscellp1.y+pscellp2.y + CTE.poscellsize*PSCEL_GetfY(pscellp2.w); //<vs_syymmetry>
    const float rr2=drx*drx+dry*dry+drz*drz;
    if(rr2<=CTE.kernelsize2 && rr2>=ALMOSTZERO){
      //-Computes kernel.
      const float fac=cufsph::GetKernel_Fac<tker>(rr2);
      const float frx=fac*drx,fry=fac*dry,frz=fac*drz; //-Gradients.

      //-Obtains mass of particle p2 if any floating bodies exist.
      //-Obtiene masa de particula p2 en caso de existir floatings.
      bool ftp2=false;         //-Indicates if it is floating. | Indica si es floating.
      float ftmassp2;    //-Contains mass of floating body or massf if fluid. | Contiene masa de particula floating o massp2 si es bound o fluid.
      bool compute=true; //-Deactivated when DEM is used and is float-float or float-bound. | Se desactiva cuando se usa DEM y es float-float o float-bound.
      if(USE_FLOATING){
        const typecode cod=code[p2];
        ftp2=CODE_IsFloating(cod);
        ftmassp2=(ftp2? ftomassp[CODE_GetTypeValue(cod)]: massp2);
        #ifdef DELTA_HEAVYFLOATING
          if(ftp2 && tdensity==DDT_DDT && ftmassp2<=(massp2*1.2f))deltap1=FLT_MAX;
        #else
          if(ftp2 && tdensity==DDT_DDT)deltap1=FLT_MAX;
        #endif
        if(ftp2 && shift && shiftmode==SHIFT_NoBound)shiftposfsp1.x=FLT_MAX; //-Cancels shifting with floating bodies. | Con floatings anula shifting.
        compute=!(USE_FTEXTERNAL && ftp1 && (boundp2 || ftp2)); //-Deactivated when DEM or Chrono is used and is float-float or float-bound. | Se desactiva cuando se usa DEM o Chrono y es float-float o float-bound.
      }

      float4 velrhop2=velrhop[p2];
      if(symm)velrhop2.y=-velrhop2.y; //<vs_syymmetry>
      //===get stress of p2 ==== mdbr
	  float2 sigmap2_xx_xy=sigma[p2*3];
	  float2 sigmap2_xz_yy=sigma[p2*3+1];
	  float2 sigmap2_yz_zz=sigma[p2*3+2];
      //-Velocity derivative (Momentum equation).
      if(compute){
          const float massp2final=(USE_FLOATING? ftmassp2: massp2);
          const float invrhop1_2=1.f/(velrhop1.w*velrhop1.w);
          const float invrhop2_2=1.f/(velrhop2.w*velrhop2.w);
          const float prsxx = massp2final*(sigmap1_xx_xy.x*invrhop1_2 + sigmap2_xx_xy.x*invrhop2_2);
		  const float prsyy = massp2final*(sigmap1_xz_yy.y*invrhop1_2 + sigmap2_xz_yy.y*invrhop2_2);
		  const float prszz = massp2final*(sigmap1_yz_zz.y*invrhop1_2 + sigmap2_yz_zz.y*invrhop2_2);
		  const float prsxy = massp2final*(sigmap1_xx_xy.y*invrhop1_2 + sigmap2_xx_xy.y*invrhop2_2);
		  const float prsxz = massp2final*(sigmap1_xz_yy.x*invrhop1_2 + sigmap2_xz_yy.x*invrhop2_2);
		  const float prsyz = massp2final*(sigmap1_yz_zz.x*invrhop1_2 + sigmap2_yz_zz.x*invrhop2_2);
		  acep1.x += (prsxx*frx + prsxy*fry + prsxz*frz); acep1.y += (prsyy*fry + prsxy*frx + prsyz*frz); acep1.z += (prszz*frz + prsyz*fry + prsxz*frx);//form 1
      }

      //-Density derivative (Continuity equation).
      const float dvx=velrhop1.x-velrhop2.x, dvy=velrhop1.y-velrhop2.y, dvz=velrhop1.z-velrhop2.z;
      if(compute)arp1+=(USE_FLOATING? ftmassp2: massp2)*(dvx*frx+dvy*fry+dvz*frz)*(velrhop1.w/velrhop2.w);

      const float cbar=CTE.cs0;
      const float dot3=(tdensity!=DDT_None || shift? drx*frx+dry*fry+drz*frz: 0);
      //-Density Diffusion Term (Molteni and Colagrossi 2009).
      if(tdensity==DDT_DDT && deltap1!=FLT_MAX){
        const float rhop1over2=velrhop1.w/velrhop2.w;
        const float visc_densi=CTE.ddtkh*cbar*(rhop1over2-1.f)/(rr2+CTE.eta2);
        const float delta=visc_densi*dot3*(USE_FLOATING? ftmassp2: massp2);
        //deltap1=(boundp2? FLT_MAX: deltap1+delta);
        deltap1=(boundp2 && CTE.tboundary==BC_DBC? FLT_MAX: deltap1+delta);
      }
      //-Density Diffusion Term (Fourtakas et al 2019).
      if((tdensity==DDT_DDT2 || (tdensity==DDT_DDT2Full && !boundp2)) && deltap1!=FLT_MAX && !ftp2){
        const float rh=1.f+CTE.ddtgz*drz;
        const float drhop=CTE.rhopzero*pow(rh,1.f/CTE.gamma)-CTE.rhopzero;  
        const float visc_densi=CTE.ddtkh*cbar*((velrhop2.w-velrhop1.w)-drhop)/(rr2+CTE.eta2);
        const float delta=visc_densi*dot3*massp2/velrhop2.w;
        deltap1=(boundp2? FLT_MAX: deltap1-delta); //-blocks it makes it boil - bloody DBC
      }

      //-Shifting correction.
      if(shift && shiftposfsp1.x!=FLT_MAX){
        const float massrhop=(USE_FLOATING? ftmassp2: massp2)/velrhop2.w;
        const bool noshift=(boundp2 && (shiftmode==SHIFT_NoBound || (shiftmode==SHIFT_NoFixed && CODE_IsFixed(code[p2]))));
        shiftposfsp1.x=(noshift? FLT_MAX: shiftposfsp1.x+massrhop*frx); //-Removes shifting for the boundaries. | Con boundary anula shifting.
        shiftposfsp1.y+=massrhop*fry;
        shiftposfsp1.z+=massrhop*frz;
        shiftposfsp1.w-=massrhop*dot3;
      }

      //===== Viscosity ===== 
      if(compute){
        const float dot=drx*dvx + dry*dvy + drz*dvz;
        const float dot_rr2=dot/(rr2+CTE.eta2);
        visc=max(dot_rr2,visc);  //ViscDt=max(dot/(rr2+Eta2),ViscDt);
        ///SPH strain/spin rate tensor calculation
        const float volp2=-massp2/velrhop2.w;        
        
        e_tensorp1_xx_xy.x+=(dvx*frx)*volp2;
		e_tensorp1_xz_yy.y+=(dvy*fry)*volp2;
        e_tensorp1_yz_zz.y+=(dvz*frz)*volp2;
        e_tensorp1_xx_xy.y+=0.5f*(dvx*fry+dvy*frx)*volp2;
        e_tensorp1_xz_yy.x+=0.5f*(dvx*frz+dvz*frx)*volp2;
        e_tensorp1_yz_zz.x+=0.5f*(dvy*frz+dvz*fry)*volp2;
        w_tensorp1_xy_yz_xz.x+=0.5f*(dvx*fry-dvy*frx)*volp2;
        w_tensorp1_xy_yz_xz.y+=0.5f*(dvy*frz-dvz*fry)*volp2;
        w_tensorp1_xy_yz_xz.z+=0.5f*(dvx*frz-dvz*frx)*volp2;

        if(!lamsps){//-Artificial viscosity.
          if(dot<0){
            const float amubar=CTE.kernelh*dot_rr2;  //amubar=CTE.kernelh*dot/(rr2+CTE.eta2);
            const float robar=(velrhop1.w+velrhop2.w)*0.5f;
            const float pi_visc=(-visco*cbar*amubar/robar)*(USE_FLOATING? ftmassp2: massp2);
            acep1.x-=pi_visc*frx; acep1.y-=pi_visc*fry; acep1.z-=pi_visc*frz;
          }
        }
        else{//-Laminar+SPS viscosity.
          {//-Laminar contribution.
            const float robar2=(velrhop1.w+velrhop2.w);
            const float temp=4.f*visco/((rr2+CTE.eta2)*robar2);  //-Simplication of temp=2.0f*visco/((rr2+CTE.eta2)*robar); robar=(rhopp1+velrhop2.w)*0.5f;
            const float vtemp=(USE_FLOATING? ftmassp2: massp2)*temp*(drx*frx+dry*fry+drz*frz);  
            acep1.x+=vtemp*dvx; acep1.y+=vtemp*dvy; acep1.z+=vtemp*dvz;
          }
          //-SPS turbulence model. Removed
        }
      }
    }
  }
}
//------------------------------------------------------------------------------
/// Interaction between particles. Fluid/Float-Fluid/Float or Fluid/Float-Bound.
/// Includes artificial/laminar viscosity and normal/DEM floating bodies.
///
/// Realiza interaccion entre particulas. Fluid/Float-Fluid/Float or Fluid/Float-Bound
/// Incluye visco artificial/laminar y floatings normales/dem.
//------------------------------------------------------------------------------
template<TpKernel tker,TpFtMode ftmode,bool lamsps,TpDensity tdensity,bool shift,bool symm>
  __global__ void KerInteractionForcesSoils(unsigned n,unsigned pinit,float viscob,float viscof
  ,int scelldiv,int4 nc,int3 cellzero,const int2 *begincell,unsigned cellfluid,const unsigned *dcell
  ,const float *ftomassp,const float4 *poscell,const float4 *velrhop,const typecode *code,const unsigned *idp
  ,const float2 *sigma,float2 *rsigma
  ,float *viscdt,float *ar,float3 *ace,float *delta
  ,TpShifting shiftmode,float4 *shiftposfs)
{
  const unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    const unsigned p1=p+pinit;      //-Number of particle.
    float visc=0,arp1=0,deltap1=0;
    float3 acep1=make_float3(0,0,0);
    float2 rsigmap1_xx_xy=make_float2(0,0);
    float2 rsigmap1_xz_yy=make_float2(0,0);
    float2 rsigmap1_yz_zz=make_float2(0,0);

    float2 e_tensorp1_xx_xy=make_float2(0,0);//strain rate tensor
    float2 e_tensorp1_xz_yy=make_float2(0,0);
    float2 e_tensorp1_yz_zz=make_float2(0,0);

    float3 w_tensorp1_xy_yz_xz=make_float3(0,0,0);//spin rate tensor

    //-Variables for Shifting.
    float4 shiftposfsp1;
    if(shift)shiftposfsp1=shiftposfs[p1];

    //-Obtains data of particle p1 in case there are floating bodies.
    bool ftp1;       //-Indicates if it is floating. | Indica si es floating.
    if(USE_FLOATING){
      const typecode cod=code[p1];
      ftp1=CODE_IsFloating(cod);
      if(ftp1 && tdensity!=DDT_None)deltap1=FLT_MAX; //-DDT is not applied to floating particles.
      if(ftp1 && shift)shiftposfsp1.x=FLT_MAX; //-Shifting is not calculated for floating bodies. | Para floatings no se calcula shifting.
    }

    //-Obtains basic data of particle p1.
    const float4 pscellp1=poscell[p1];
    const float4 velrhop1=velrhop[p1];
    const float pressp1=cufsph::ComputePressCte(velrhop1.w);
    const bool rsymp1=(symm && PSCEL_GetPartY(__float_as_uint(pscellp1.w))==0); //<vs_syymmetry>
    //-Obtains stress tensor == mdbr
	float2 sigmap1_xx_xy=sigma[p1*3];
	float2 sigmap1_xz_yy=sigma[p1*3+1];
	float2 sigmap1_yz_zz=sigma[p1*3+2];
    //-Obtains elastic parameters
    float modulus_K=CTE.modulus_K;
    float modulus_G=CTE.modulus_G;

    //-Obtains neighborhood search limits.
    int ini1,fin1,ini2,fin2,ini3,fin3;
    cunsearch::InitCte(dcell[p1],scelldiv,nc,cellzero,ini1,fin1,ini2,fin2,ini3,fin3);

    //-Interaction with fluids.
    ini3+=cellfluid; fin3+=cellfluid;
    for(int c3=ini3;c3<fin3;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
      unsigned pini,pfin=0;  cunsearch::ParticleRange(c2,c3,ini1,fin1,begincell,pini,pfin);
      if(pfin){
                          KerInteractionForcesSoilsBox<tker,ftmode,lamsps,tdensity,shift,false> (false,p1,pini,pfin,viscof,ftomassp,poscell,velrhop,code,idp,sigma,CTE.massf,ftp1,pscellp1,velrhop1,pressp1,e_tensorp1_xx_xy,e_tensorp1_xz_yy,e_tensorp1_yz_zz,w_tensorp1_xy_yz_xz,acep1,arp1,visc,deltap1,shiftmode,shiftposfsp1,sigmap1_xx_xy,sigmap1_xz_yy,sigmap1_yz_zz);
        if(symm && rsymp1)KerInteractionForcesSoilsBox<tker,ftmode,lamsps,tdensity,shift,true > (false,p1,pini,pfin,viscof,ftomassp,poscell,velrhop,code,idp,sigma,CTE.massf,ftp1,pscellp1,velrhop1,pressp1,e_tensorp1_xx_xy,e_tensorp1_xz_yy,e_tensorp1_yz_zz,w_tensorp1_xy_yz_xz,acep1,arp1,visc,deltap1,shiftmode,shiftposfsp1,sigmap1_xx_xy,sigmap1_xz_yy,sigmap1_yz_zz); //<vs_syymmetry>
      }
    }
    //-Interaction with boundaries.
    ini3-=cellfluid; fin3-=cellfluid;
    for(int c3=ini3;c3<fin3;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
      unsigned pini,pfin=0;  cunsearch::ParticleRange(c2,c3,ini1,fin1,begincell,pini,pfin);
      if(pfin){
                        KerInteractionForcesSoilsBox<tker,ftmode,lamsps,tdensity,shift,false> (true ,p1,pini,pfin,viscob,ftomassp,poscell,velrhop,code,idp,sigma,CTE.massb,ftp1,pscellp1,velrhop1,pressp1,e_tensorp1_xx_xy,e_tensorp1_xz_yy,e_tensorp1_yz_zz,w_tensorp1_xy_yz_xz,acep1,arp1,visc,deltap1,shiftmode,shiftposfsp1,sigmap1_xx_xy,sigmap1_xz_yy,sigmap1_yz_zz);
      if(symm && rsymp1)KerInteractionForcesSoilsBox<tker,ftmode,lamsps,tdensity,shift,true > (true ,p1,pini,pfin,viscob,ftomassp,poscell,velrhop,code,idp,sigma,CTE.massb,ftp1,pscellp1,velrhop1,pressp1,e_tensorp1_xx_xy,e_tensorp1_xz_yy,e_tensorp1_yz_zz,w_tensorp1_xy_yz_xz,acep1,arp1,visc,deltap1,shiftmode,shiftposfsp1,sigmap1_xx_xy,sigmap1_xz_yy,sigmap1_yz_zz);
      }
    }
    //Calculate stress rate tensor mdbr
    GetStressRateTensor_Elastic(e_tensorp1_xx_xy,e_tensorp1_xz_yy,e_tensorp1_yz_zz,w_tensorp1_xy_yz_xz,sigmap1_xx_xy,sigmap1_xz_yy,sigmap1_yz_zz,modulus_K,modulus_G,rsigmap1_xx_xy,rsigmap1_xz_yy,rsigmap1_yz_zz);
    
    //-Stores results.
    if(shift||arp1||acep1.x||acep1.y||acep1.z||visc){
      if(tdensity!=DDT_None){
        if(delta){
          const float rdelta=delta[p1];
          delta[p1]=(rdelta==FLT_MAX || deltap1==FLT_MAX? FLT_MAX: rdelta+deltap1);
        }
        else if(deltap1!=FLT_MAX)arp1+=deltap1;
      }
      ar[p1]+=arp1;
      float3 r=ace[p1]; r.x+=acep1.x; r.y+=acep1.y; r.z+=acep1.z; ace[p1]=r;
      //===mdbr
      float2 rs;
      rs=rsigma[p1*3];	    rs=make_float2(rs.x+rsigmap1_xx_xy.x,rs.y+rsigmap1_xx_xy.y); rsigma[p1*3]=rs;
	  rs=rsigma[p1*3+1];	rs=make_float2(rs.x+rsigmap1_xz_yy.x,rs.y+rsigmap1_xz_yy.y); rsigma[p1*3+1]=rs;
	  rs=rsigma[p1*3+2];	rs=make_float2(rs.x+rsigmap1_yz_zz.x,rs.y+rsigmap1_yz_zz.y); rsigma[p1*3+2]=rs;
      //===
      if(visc>viscdt[p1])viscdt[p1]=visc;
      if(shift)shiftposfs[p1]=shiftposfsp1;
    }
  }
}
#ifndef DISABLE_BSMODES
//==============================================================================
/// Collects kernel information.
//==============================================================================
template<TpKernel tker,TpFtMode ftmode,bool lamsps,TpDensity tdensity,bool shift,bool symm> 
  void Interaction_ForcesT_KerInfo(StKerInfo *kerinfo)
{
 #if CUDART_VERSION >= 6050
  {
    typedef void (*fun_ptr)(unsigned,unsigned,float,float,int,int4,int3,const int2*,unsigned,const unsigned*,const float*,const float4*,const float4*,const tmatrix3d*,const byte*,const float3*,const float3*,const float3*,float4*,const typecode*,const unsigned*,const float2*,const float2*,float2*,TpMdbc2Mode,const float*,float*,const unsigned*,const float3*,unsigned,float*,float*,float3*,float*,TpShifting,float4*);
    fun_ptr ptr=&KerInteractionForcesFluid<tker,ftmode,lamsps,tdensity,shift,symm>;
    int qblocksize=0,mingridsize=0;
    cudaOccupancyMaxPotentialBlockSize(&mingridsize,&qblocksize,(void*)ptr,0,0);
    struct cudaFuncAttributes attr;
    cudaFuncGetAttributes(&attr,(void*)ptr);
    kerinfo->forcesfluid_bs=qblocksize;
    kerinfo->forcesfluid_rg=attr.numRegs;
    kerinfo->forcesfluid_bsmax=attr.maxThreadsPerBlock;
    //printf(">> KerInteractionForcesFluid  blocksize:%u (%u)\n",qblocksize,0);
  }
  {
    typedef void (*fun_ptr)(unsigned,unsigned,float,float,int,int4,int3,const int2*,unsigned,const unsigned*,const float*,const float4*,const float4*,const typecode*,const unsigned*,const float2*,float2*,float*,float*,float3*,float*,TpShifting,float4*);
    fun_ptr ptr=&KerInteractionForcesSoils<tker,ftmode,lamsps,tdensity,shift,symm>;
    int qblocksize=0,mingridsize=0;
    cudaOccupancyMaxPotentialBlockSize(&mingridsize,&qblocksize,(void*)ptr,0,0);
    struct cudaFuncAttributes attr;
    cudaFuncGetAttributes(&attr,(void*)ptr);
    kerinfo->forcesfluid_bs=qblocksize;
    kerinfo->forcesfluid_rg=attr.numRegs;
    kerinfo->forcesfluid_bsmax=attr.maxThreadsPerBlock;
    //printf(">> KerInteractionForcesSoils  blocksize:%u (%u)\n",qblocksize,0);
  }
  {
    typedef void (*fun_ptr)(unsigned,unsigned,int,int4,int3,const int2*,const unsigned*,const float*,const float4*,const float4*,const typecode*,const unsigned*,float*,float*);
    fun_ptr ptr=&KerInteractionForcesBound<tker,ftmode,symm>;
    int qblocksize=0,mingridsize=0;
    cudaOccupancyMaxPotentialBlockSize(&mingridsize,&qblocksize,(void*)ptr,0,0);
    struct cudaFuncAttributes attr;
    cudaFuncGetAttributes(&attr,(void*)ptr);
    kerinfo->forcesbound_bs=qblocksize;
    kerinfo->forcesbound_rg=attr.numRegs;
    kerinfo->forcesbound_bsmax=attr.maxThreadsPerBlock;
    //printf(">> KerInteractionForcesBound  blocksize:%u (%u)\n",qblocksize,0);
  }
  fcuda::Check_CudaErroorFun("Error collecting kernel information.");
 #endif
}
#endif

//==============================================================================
/// Interaction for the force computation.
/// Interaccion para el calculo de fuerzas.
//==============================================================================
template<TpKernel tker,TpFtMode ftmode,bool lamsps,TpDensity tdensity,bool shift> 
  void Interaction_ForcesGpuT(const StInterParmsg &t)
{
  //-Collects kernel information.
#ifndef DISABLE_BSMODES
  if(t.kerinfo){
    Interaction_ForcesT_KerInfo<tker,ftmode,lamsps,tdensity,shift,false>(t.kerinfo);
    return;
  }
#endif
  const StDivDataGpu &dvd=t.divdatag;
  const int2* beginendcell=dvd.beginendcell;
  //cudaProfilerStart();//mdbr
  //-Interaction Fluid-Fluid & Fluid-Bound.
  if(t.fluidnum){
    //printf("[ns:%u  id:%d] halo:%d fini:%d(%d) bini:%d(%d)\n",t.nstep,t.id,t.halo,t.fluidini,t.fluidnum,t.boundini,t.boundnum);
    dim3 sgridf=GetSimpleGridSize(t.fluidnum,t.bsfluid);
    if(t.symmetry) //<vs_syymmetry_ini>
      KerInteractionForcesFluid<tker,ftmode,lamsps,tdensity,shift,true> <<<sgridf,t.bsfluid,0,t.stm>>> 
      (t.fluidnum,t.fluidini,t.viscob,t.viscof,dvd.scelldiv,dvd.nc,dvd.cellzero,dvd.beginendcell,dvd.cellfluid,t.dcell
      ,t.ftomassp,t.poscell,t.velrhop,t.corrmat,t.boundmode,t.tangenvel,t.motionvel,t.boundnormal,t.nopenshift,t.code,t.idp,(const float2*)t.sigma,(const float2*)t.artificialstress,(float2*)t.rsigma,t.mdbc2
      ,t.porepress,t.porepressrate,t.fstype,t.fsnormal,(t.hydrodrainfs? 1u: 0u)
      ,t.viscdt,t.ar,t.ace,t.delta,t.shiftmode,t.shiftposfs);
    else //<vs_syymmetry_end>
      KerInteractionForcesFluid<tker,ftmode,lamsps,tdensity,shift,false> <<<sgridf,t.bsfluid,0,t.stm>>> 
      (t.fluidnum,t.fluidini,t.viscob,t.viscof,dvd.scelldiv,dvd.nc,dvd.cellzero,dvd.beginendcell,dvd.cellfluid,t.dcell
      ,t.ftomassp,t.poscell,t.velrhop,t.corrmat,t.boundmode,t.tangenvel,t.motionvel,t.boundnormal,t.nopenshift,t.code,t.idp,(const float2*)t.sigma,(const float2*)t.artificialstress,(float2*)t.rsigma,t.mdbc2
      ,t.porepress,t.porepressrate,t.fstype,t.fsnormal,(t.hydrodrainfs? 1u: 0u)
      ,t.viscdt,t.ar,t.ace,t.delta,t.shiftmode,t.shiftposfs);
  }
  //cudaProfilerStop();//mdbr
  //-Interaction Boundary-Fluid. Has been considered in cDBC/mDBC
  if(0){//t.boundnum
    const int2* beginendcellfluid=dvd.beginendcell+dvd.cellfluid;
    dim3 sgridb=GetSimpleGridSize(t.boundnum,t.bsbound);
    //printf("bsbound:%u\n",bsbound);
    if(t.symmetry) //<vs_syymmetry_ini>
      KerInteractionForcesBound<tker,ftmode,true > <<<sgridb,t.bsbound,0,t.stm>>> 
      (t.boundnum,t.boundini,dvd.scelldiv,dvd.nc,dvd.cellzero,beginendcell+dvd.cellfluid,t.dcell
        ,t.ftomassp,t.poscell,t.velrhop,t.code,t.idp,t.viscdt,t.ar);
    else //<vs_syymmetry_end>
      KerInteractionForcesBound<tker,ftmode,false> <<<sgridb,t.bsbound,0,t.stm>>> 
      (t.boundnum,t.boundini,dvd.scelldiv,dvd.nc,dvd.cellzero,beginendcellfluid,t.dcell
        ,t.ftomassp,t.poscell,t.velrhop,t.code,t.idp,t.viscdt,t.ar);
  }
}

//==============================================================================
//#define FAST_COMPILATION
template<TpKernel tker,TpFtMode ftmode,bool lamsps> void Interaction_Forces_gt2(const StInterParmsg &t){
#ifdef FAST_COMPILATION
  if(t.shiftmode || t.tdensity!=DDT_DDT4)throw "Shifting and extra DDT are disabled for FastCompilation...";
  Interaction_ForcesGpuT<tker,ftmode,lamsps,DDT_DDT4,false> (t);
#else
  if(t.shiftmode){               const bool shift=true;
    if(t.tdensity==DDT_None)    Interaction_ForcesGpuT<tker,ftmode,lamsps,DDT_None    ,shift> (t);
    if(t.tdensity==DDT_DDT)     Interaction_ForcesGpuT<tker,ftmode,lamsps,DDT_DDT     ,shift> (t);
    if(t.tdensity==DDT_DDT2)    Interaction_ForcesGpuT<tker,ftmode,lamsps,DDT_DDT2    ,shift> (t);
    if(t.tdensity==DDT_DDT2Full)Interaction_ForcesGpuT<tker,ftmode,lamsps,DDT_DDT2Full,shift> (t);
  }
  else{                           const bool shift=false;
    if(t.tdensity==DDT_None)    Interaction_ForcesGpuT<tker,ftmode,lamsps,DDT_None    ,shift> (t);
    if(t.tdensity==DDT_DDT)     Interaction_ForcesGpuT<tker,ftmode,lamsps,DDT_DDT     ,shift> (t);
    if(t.tdensity==DDT_DDT2)    Interaction_ForcesGpuT<tker,ftmode,lamsps,DDT_DDT2    ,shift> (t);
    if(t.tdensity==DDT_DDT2Full)Interaction_ForcesGpuT<tker,ftmode,lamsps,DDT_DDT2Full,shift> (t);
  }
#endif
}
//==============================================================================
template<TpKernel tker,TpFtMode ftmode> void Interaction_Forces_gt1(const StInterParmsg &t){
#ifdef FAST_COMPILATION
  if(t.lamsps)throw "Extra viscosity options are disabled for FastCompilation...";
  Interaction_Forces_gt2<tker,ftmode,false> (t);
#else
  if(t.lamsps)Interaction_Forces_gt2<tker,ftmode,true>  (t);
  else        Interaction_Forces_gt2<tker,ftmode,false> (t);
#endif
}
//==============================================================================
template<TpKernel tker> void Interaction_Forces_gt0(const StInterParmsg &t){
#ifdef FAST_COMPILATION
  if(t.ftmode!=FTMODE_None)throw "Extra FtMode options are disabled for FastCompilation...";
  Interaction_Forces_gt1<tker,FTMODE_None> (t);
#else
  if(t.ftmode==FTMODE_None)    Interaction_Forces_gt1<tker,FTMODE_None> (t);
  else if(t.ftmode==FTMODE_Sph)Interaction_Forces_gt1<tker,FTMODE_Sph>  (t);
  else if(t.ftmode==FTMODE_Ext)Interaction_Forces_gt1<tker,FTMODE_Ext>  (t);
#endif
}
//==============================================================================
void Interaction_Forces(const StInterParmsg &t){
#ifdef FAST_COMPILATION
  if(t.tkernel!=KERNEL_Wendland)throw "Extra kernels are disabled for FastCompilation...";
  Interaction_Forces_gt0<KERNEL_Wendland> (t);
#else
  if(t.tkernel==KERNEL_Wendland)     Interaction_Forces_gt0<KERNEL_Wendland> (t);
 #ifndef DISABLE_KERNELS_EXTRA
  else if(t.tkernel==KERNEL_Cubic)   Interaction_Forces_gt0<KERNEL_Cubic   > (t);
 #endif
#endif
}

//------------------------------------------------------------------------------
/// Returns the corrected position after applying periodic conditions.
/// Devuelve la posicion corregida tras aplicar condiciones periodicas.
//------------------------------------------------------------------------------
__device__ float4 KerComputePosCell(const double3 &ps,const double3 &mapposmin,float poscellsize)
{
  const double dx=ps.x-mapposmin.x;
  const double dy=ps.y-mapposmin.y;
  const double dz=ps.z-mapposmin.z;
  int cx=int(dx/poscellsize);
  int cy=int(dy/poscellsize);
  int cz=int(dz/poscellsize);
  cx=(cx>=0? cx: 0);
  cy=(cy>=0? cy: 0);
  cz=(cz>=0? cz: 0);
  const float px=float(dx-(double(poscellsize)*cx));
  const float py=float(dy-(double(poscellsize)*cy));
  const float pz=float(dz-(double(poscellsize)*cz));
  const float pw=__uint_as_float(PSCEL_Code(cx,cy,cz));
  return(make_float4(px,py,pz,pw));
}

//------------------------------------------------------------------------------
/// Calculates tangential velocity used by no-slip/free-slip mDBC viscous and gradient terms.
//------------------------------------------------------------------------------
__device__ float3 KerMdbc2TangenVel(const float3 boundnormal,const float3 velfinal){
  const float snormal2=boundnormal.x*boundnormal.x+boundnormal.y*boundnormal.y+boundnormal.z*boundnormal.z;
  if(snormal2<=ALMOSTZERO)return(make_float3(0,0,0));
  const float invnormal=rsqrtf(snormal2);
  const float3 normal=make_float3(boundnormal.x*invnormal,boundnormal.y*invnormal,boundnormal.z*invnormal);
  const float veldotnorm=velfinal.x*normal.x+velfinal.y*normal.y+velfinal.z*normal.z;
  return(make_float3(velfinal.x-veldotnorm*normal.x,
                     velfinal.y-veldotnorm*normal.y,
                     velfinal.z-veldotnorm*normal.z));
}

//------------------------------------------------------------------------------
/// Perform interaction between ghost node of selected bondary and fluid.
//------------------------------------------------------------------------------
template<TpKernel tker,bool sim2d,TpSlipMode tslip> __global__ void KerInteractionMdbcCorrection_Fast
  (unsigned n,unsigned nbound,float determlimit,float mdbcthreshold
  ,double3 mapposmin,float poscellsize,const float4 *poscell
  ,int scelldiv,int4 nc,int3 cellzero,const int2 *beginendcellfluid
  ,const double2 *posxy,const double *posz,const typecode *code,const unsigned *idp
  ,const float3 *boundnormal,const float3 *motionvel,float4 *velrhop,tsymatrix3f *sigma,byte *boundmode,float3 *tangenvel
  ,const float *porepress0,float *porepress)
{
  const unsigned p1=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p1<n){
    const bool useboundmode=(boundmode && tslip>=SLIP_NoSlip);
    const bool extrapolatepore=(porepress0 && porepress);
    const float3 bnormalp1=boundnormal[p1];
    if(bnormalp1.x!=0 || bnormalp1.y!=0 || bnormalp1.z!=0){
      float rhopfinal=FLT_MAX;
      float3 velrhopfinal=make_float3(0,0,0);
      tsymatrix3f sigmafinal={0,0,0,0,0,0};//mdbr
      float sumwab=0;
      float submerged=0;
      double pwexcesssum=0;

      //-Calculates ghost node position.
      double3 gposp1=make_double3(posxy[p1].x+bnormalp1.x,posxy[p1].y+bnormalp1.y,posz[p1]+bnormalp1.z);
      gposp1=(CTE.periactive!=0? KerUpdatePeriodicPos(gposp1): gposp1); //-Corrected interface Position.
      const float4 gpscellp1=KerComputePosCell(gposp1,mapposmin,poscellsize);

      //-Initializes variables for calculation.
      //float rhopp1=0;
      //float3 gradrhopp1=make_float3(0,0,0);
      //===== mdbr
	  //-Stress
	  tsymatrix3f sigmap1 = { 0,0,0,0,0,0 };//-First-order Stress value
	  float3 gradsigmaxxp1 = make_float3(0,0,0);//-Stress gradient
	  float3 gradsigmayyp1 = make_float3(0,0,0);
	  float3 gradsigmazzp1 = make_float3(0,0,0);
	  float3 gradsigmaxyp1 = make_float3(0,0,0);
	  float3 gradsigmayzp1 = make_float3(0,0,0);
	  float3 gradsigmaxzp1 = make_float3(0,0,0);
	  //=====
      float3 velp1=make_float3(0,0,0);                              // -Only for velocity
      tmatrix3f a_corr2; if(sim2d) cumath::Tmatrix3fReset(a_corr2); //-Only for 2D.
      tmatrix4f a_corr3; if(!sim2d)cumath::Tmatrix4fReset(a_corr3); //-Only for 3D.
    
      //-Obtains neighborhood search limits.
      int ini1,fin1,ini2,fin2,ini3,fin3;
      cunsearch::InitCte(gposp1.x,gposp1.y,gposp1.z,scelldiv,nc,cellzero,ini1,fin1,ini2,fin2,ini3,fin3);

      //-Boundary-Fluid interaction.
      for(int c3=ini3;c3<fin3;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
        unsigned pini,pfin=0;  cunsearch::ParticleRange(c2,c3,ini1,fin1,beginendcellfluid,pini,pfin);
        if(pfin)for(unsigned p2=pini;p2<pfin;p2++){
          const float4 pscellp2=poscell[p2];
          float drx=gpscellp1.x-pscellp2.x + CTE.poscellsize*(PSCEL_GetfX(gpscellp1.w)-PSCEL_GetfX(pscellp2.w));
          float dry=gpscellp1.y-pscellp2.y + CTE.poscellsize*(PSCEL_GetfY(gpscellp1.w)-PSCEL_GetfY(pscellp2.w));
          float drz=gpscellp1.z-pscellp2.z + CTE.poscellsize*(PSCEL_GetfZ(gpscellp1.w)-PSCEL_GetfZ(pscellp2.w));
          const float rr2=drx*drx+dry*dry+drz*drz;
          if(rr2<=CTE.kernelsize2 && CODE_IsFluid(code[p2])){//-Only with fluid particles (including inout).
            //-Computes kernel.
            float fac;
            const float wab=cufsph::GetKernel_WabFac<tker>(rr2,fac);
            const float frx=fac*drx,fry=fac*dry,frz=fac*drz; //-Gradients.

            //===== Get mass and volume of particle p2 =====
            const float4 velrhopp2=velrhop[p2];
            const tsymatrix3f sigmap2=sigma[p2];//mdbr
            float massp2=CTE.massf;
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
            if(extrapolatepore)pwexcesssum+=double(vwab)*double(porepress[p2]-porepress0[p2]);
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
            if(tslip!=SLIP_Vel0) {
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
      if(activebound){
        if(useboundmode)boundmode[p1]=BMODE_MDBC2;
        const float3 dpos=make_float3(-bnormalp1.x,-bnormalp1.y,-bnormalp1.z); //-Boundary particle position - ghost node position.
        if(sim2d){
          const double determ=cumath::Determinant3x3dbl(a_corr2);
          if(fabs(determ)>=determlimit){//-Use 1e-3f (first_order) or 1e+3f (zeroth_order).
            const tmatrix3f invacorr2=cumath::InverseMatrix3x3dbl(a_corr2,determ);
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
          else if(a_corr2.a11>0){//-Determinant is small but a11 is nonzero, 0th order ANGELO.
            //rhopfinal=float(rhopp1/a_corr2.a11);
            sigmafinal.xx = float(sigmap1.xx / a_corr2.a11);
			sigmafinal.zz = float(sigmap1.zz / a_corr2.a11);
			sigmafinal.xz = float(sigmap1.xz / a_corr2.a11);
          }
          //-Ghost node velocity (0th order).
          if(a_corr2.a11>0&&tslip!=SLIP_Vel0){
            velrhopfinal.x=float(velp1.x/a_corr2.a11);
            velrhopfinal.z=float(velp1.z/a_corr2.a11);
            velrhopfinal.y=0;
          }
        }
        else{
          const double determ=cumath::Determinant4x4dbl(a_corr3);
          if(fabs(determ)>=determlimit){
            const tmatrix4f invacorr3=cumath::InverseMatrix4x4dbl(a_corr3,determ);
            //-GHOST NODE DENSITY IS MIRRORED BACK TO THE BOUNDARY PARTICLES.
            //const float rhoghost=float(invacorr3.a11*rhopp1 + invacorr3.a12*gradrhopp1.x + invacorr3.a13*gradrhopp1.y + invacorr3.a14*gradrhopp1.z);
            //const float grx=    -float(invacorr3.a21*rhopp1 + invacorr3.a22*gradrhopp1.x + invacorr3.a23*gradrhopp1.y + invacorr3.a24*gradrhopp1.z);
            //const float gry=    -float(invacorr3.a31*rhopp1 + invacorr3.a32*gradrhopp1.x + invacorr3.a33*gradrhopp1.y + invacorr3.a34*gradrhopp1.z);
            //const float grz=    -float(invacorr3.a41*rhopp1 + invacorr3.a42*gradrhopp1.x + invacorr3.a43*gradrhopp1.y + invacorr3.a44*gradrhopp1.z);
            //rhopfinal=(rhoghost + grx*dpos.x + gry*dpos.y + grz*dpos.z);
            //-Ghost stress ==== mdbr
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
          else if(a_corr3.a11>0){//-Determinant is small but a11 is nonzero, 0th order ANGELO.
            //rhopfinal=float(rhopp1/a_corr3.a11);
            //==== mdbr
            sigmafinal.xx = float(sigmap1.xx / a_corr3.a11);
            sigmafinal.yy = float(sigmap1.yy / a_corr3.a11);
            sigmafinal.zz = float(sigmap1.zz / a_corr3.a11);
            sigmafinal.xy = float(sigmap1.xy / a_corr3.a11);
            sigmafinal.yz = float(sigmap1.yz / a_corr3.a11);
            sigmafinal.xz = float(sigmap1.xz / a_corr3.a11);
          }
          //-Ghost node velocity (0th order).
          if(a_corr3.a11>0&&tslip!=SLIP_Vel0){
            velrhopfinal.x=float(velp1.x/a_corr3.a11);
            velrhopfinal.y=float(velp1.y/a_corr3.a11);
            velrhopfinal.z=float(velp1.z/a_corr3.a11);
          }
        }
        //-Store the results.
        rhopfinal=CTE.rhopzero;//(rhopfinal!=FLT_MAX? rhopfinal: CTE.rhopzero);
        if(tslip==SLIP_Vel0){//-DBC vel=0
          velrhop[p1].w=rhopfinal;
          sigma[p1] = sigmafinal;
          if(extrapolatepore && sumwab>0)porepress[p1]=float(double(porepress0[p1])+pwexcesssum/double(sumwab));
        }
        if(tslip==SLIP_NoSlip){//-No-Slip
          const float3 v=motionvel[p1];
          const float3 v2=make_float3(v.x+v.x-velrhopfinal.x,v.y+v.y-velrhopfinal.y,v.z+v.z-velrhopfinal.z);
          velrhop[p1].w=rhopfinal;
          if(tangenvel)tangenvel[p1]=KerMdbc2TangenVel(bnormalp1,v2);
          sigma[p1] = sigmafinal;
          if(extrapolatepore && sumwab>0)porepress[p1]=float(double(porepress0[p1])+pwexcesssum/double(sumwab));
        }
        if(tslip==SLIP_FreeSlip){//-Free-slip keeps boundary velocity and stores extrapolated tangential velocity.
          velrhop[p1].w=rhopfinal;
          if(tangenvel)tangenvel[p1]=KerMdbc2TangenVel(bnormalp1,velrhopfinal);
          sigma[p1] = sigmafinal;
          if(extrapolatepore && sumwab>0)porepress[p1]=float(double(porepress0[p1])+pwexcesssum/double(sumwab));
        }
      }
      else if(useboundmode){
        boundmode[p1]=BMODE_MDBC2OFF;
        velrhop[p1].w=CTE.rhopzero;
        const tsymatrix3f sigmazero={0,0,0,0,0,0};
        sigma[p1]=sigmazero;
        if(tangenvel)tangenvel[p1]=KerMdbc2TangenVel(bnormalp1,motionvel[p1]);
      }
    }
  }
}

//------------------------------------------------------------------------------
/// Perform interaction between ghost node of selected bondary and fluid.
//------------------------------------------------------------------------------
template<TpKernel tker,bool sim2d,TpSlipMode tslip> __global__ void KerInteractionMdbcCorrection_Dbl
  (unsigned n,unsigned nbound,float determlimit,float mdbcthreshold
  ,int scelldiv,int4 nc,int3 cellzero,const int2 *beginendcellfluid
  ,const double2 *posxy,const double *posz,const typecode *code,const unsigned *idp
  ,const float3 *boundnormal,const float3 *motionvel,float4 *velrhop,tsymatrix3f *sigma,byte *boundmode,float3 *tangenvel
  ,const float *porepress0,float *porepress)
{
  const unsigned p1=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p1<n){
    const bool useboundmode=(boundmode && tslip>=SLIP_NoSlip);
    const bool extrapolatepore=(porepress0 && porepress);
    const float3 bnormalp1=boundnormal[p1];
    if(bnormalp1.x!=0 || bnormalp1.y!=0 || bnormalp1.z!=0){
      float rhopfinal=FLT_MAX;
      float3 velrhopfinal=make_float3(0,0,0);
      tsymatrix3f sigmafinal={0,0,0,0,0,0};//mdbr
      float sumwab=0;
      float submerged=0;
      double pwexcesssum=0;

      //-Calculates ghost node position.
      double3 gposp1=make_double3(posxy[p1].x+bnormalp1.x,posxy[p1].y+bnormalp1.y,posz[p1]+bnormalp1.z);
      gposp1=(CTE.periactive!=0? KerUpdatePeriodicPos(gposp1): gposp1); //-Corrected interface Position.
      //-Initializes variables for calculation.
      float rhopp1=0;
      float3 gradrhopp1=make_float3(0,0,0);
      //===== mdbr
	  //-Stress
	  tsymatrix3f sigmap1 = { 0,0,0,0,0,0 };//-First-order Stress value
	  float3 gradsigmaxxp1 = make_float3(0,0,0);//-Stress gradient
	  float3 gradsigmayyp1 = make_float3(0,0,0);
	  float3 gradsigmazzp1 = make_float3(0,0,0);
	  float3 gradsigmaxyp1 = make_float3(0,0,0);
	  float3 gradsigmayzp1 = make_float3(0,0,0);
	  float3 gradsigmaxzp1 = make_float3(0,0,0);
	  //=====
      float3 velp1=make_float3(0,0,0);                              // -Only for velocity
      tmatrix3d a_corr2; if(sim2d) cumath::Tmatrix3dReset(a_corr2); //-Only for 2D.
      tmatrix4d a_corr3; if(!sim2d)cumath::Tmatrix4dReset(a_corr3); //-Only for 3D.
    
      //-Obtains neighborhood search limits.
      int ini1,fin1,ini2,fin2,ini3,fin3;
      cunsearch::InitCte(gposp1.x,gposp1.y,gposp1.z,scelldiv,nc,cellzero,ini1,fin1,ini2,fin2,ini3,fin3);

      //-Boundary-Fluid interaction.
      for(int c3=ini3;c3<fin3;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
        unsigned pini,pfin=0;  cunsearch::ParticleRange(c2,c3,ini1,fin1,beginendcellfluid,pini,pfin);
        if(pfin)for(unsigned p2=pini;p2<pfin;p2++){
          const double2 p2xy=posxy[p2];
          const float drx=float(gposp1.x-p2xy.x);
          const float dry=float(gposp1.y-p2xy.y);
          const float drz=float(gposp1.z-posz[p2]);
          const float rr2=drx*drx+dry*dry+drz*drz;
          if(rr2<=CTE.kernelsize2 && CODE_IsFluid(code[p2])){//-Only with fluid particles (including inout).
            //-Computes kernel.
            float fac;
            const float wab=cufsph::GetKernel_WabFac<tker>(rr2,fac);
            const float frx=fac*drx,fry=fac*dry,frz=fac*drz; //-Gradients.

            //===== Get mass and volume of particle p2 =====
            const float4 velrhopp2=velrhop[p2];
            const tsymatrix3f sigmap2=sigma[p2];//mdbr
            float massp2=CTE.massf;
            const float volp2=massp2/velrhopp2.w;
            if(useboundmode)submerged-=volp2*(drx*frx + dry*fry + drz*frz);

            //===== Density and its gradient =====
            rhopp1+=massp2*wab;
            gradrhopp1.x+=massp2*frx;
            gradrhopp1.y+=massp2*fry;
            gradrhopp1.z+=massp2*frz;

            //===== Kernel values multiplied by volume =====
            const float vwab=wab*volp2;
            sumwab+=vwab;
            if(extrapolatepore)pwexcesssum+=double(vwab)*double(porepress[p2]-porepress0[p2]);
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
            if(tslip!=SLIP_Vel0) {
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
      const bool activebound=(useboundmode? submerged>0.f: sumwab>=mdbcthreshold);
      if(activebound){
        if(useboundmode)boundmode[p1]=BMODE_MDBC2;
        const float3 dpos=make_float3(-bnormalp1.x,-bnormalp1.y,-bnormalp1.z); //-Boundary particle position - ghost node position.
        if(sim2d){
          const double determ=cumath::Determinant3x3(a_corr2);
          if(fabs(determ)>=determlimit){//-Use 1e-3f (first_order) or 1e+3f (zeroth_order).
            const tmatrix3d invacorr2=cumath::InverseMatrix3x3(a_corr2,determ);
            //-GHOST NODE DENSITY IS MIRRORED BACK TO THE BOUNDARY PARTICLES.
            const float rhoghost=float(invacorr2.a11*rhopp1 + invacorr2.a12*gradrhopp1.x + invacorr2.a13*gradrhopp1.z);
            const float grx=    -float(invacorr2.a21*rhopp1 + invacorr2.a22*gradrhopp1.x + invacorr2.a23*gradrhopp1.z);
            const float grz=    -float(invacorr2.a31*rhopp1 + invacorr2.a32*gradrhopp1.x + invacorr2.a33*gradrhopp1.z);
            rhopfinal=(rhoghost + grx*dpos.x + grz*dpos.z);
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
          }
          else if(a_corr2.a11>0){//-Determinant is small but a11 is nonzero, 0th order ANGELO.
            rhopfinal=float(rhopp1/a_corr2.a11);
            //====mdbr
            sigmafinal.xx = float(sigmap1.xx / a_corr2.a11);
            sigmafinal.zz = float(sigmap1.zz / a_corr2.a11);
            sigmafinal.xz = float(sigmap1.xz / a_corr2.a11);
          }
          //-Ghost node velocity (0th order).
          if(a_corr2.a11>0&&tslip!=SLIP_Vel0){
            velrhopfinal.x=float(velp1.x/a_corr2.a11);
            velrhopfinal.z=float(velp1.z/a_corr2.a11);
            velrhopfinal.y=0;
          }
        }
        else{
          const double determ=cumath::Determinant4x4(a_corr3);
          if(fabs(determ)>=determlimit){
            const tmatrix4d invacorr3=cumath::InverseMatrix4x4(a_corr3,determ);
            //-GHOST NODE DENSITY IS MIRRORED BACK TO THE BOUNDARY PARTICLES.
            const float rhoghost=float(invacorr3.a11*rhopp1 + invacorr3.a12*gradrhopp1.x + invacorr3.a13*gradrhopp1.y + invacorr3.a14*gradrhopp1.z);
            const float grx=    -float(invacorr3.a21*rhopp1 + invacorr3.a22*gradrhopp1.x + invacorr3.a23*gradrhopp1.y + invacorr3.a24*gradrhopp1.z);
            const float gry=    -float(invacorr3.a31*rhopp1 + invacorr3.a32*gradrhopp1.x + invacorr3.a33*gradrhopp1.y + invacorr3.a34*gradrhopp1.z);
            const float grz=    -float(invacorr3.a41*rhopp1 + invacorr3.a42*gradrhopp1.x + invacorr3.a43*gradrhopp1.y + invacorr3.a44*gradrhopp1.z);
            rhopfinal=(rhoghost + grx*dpos.x + gry*dpos.y + grz*dpos.z);
            //-Ghost stress ==== mdbr
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
          else if(a_corr3.a11>0){//-Determinant is small but a11 is nonzero, 0th order ANGELO.
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
          if(a_corr3.a11>0&&tslip!=SLIP_Vel0){
            velrhopfinal.x=float(velp1.x/a_corr3.a11);
            velrhopfinal.y=float(velp1.y/a_corr3.a11);
            velrhopfinal.z=float(velp1.z/a_corr3.a11);
          }
        }
        //-Store the results.
        rhopfinal=(rhopfinal!=FLT_MAX? rhopfinal: CTE.rhopzero);
        if(tslip==SLIP_Vel0){//-DBC vel=0
          velrhop[p1].w=rhopfinal;
          sigma[p1]=sigmafinal;//mdbr
          if(extrapolatepore && sumwab>0)porepress[p1]=float(double(porepress0[p1])+pwexcesssum/double(sumwab));
        }
        if(tslip==SLIP_NoSlip){//-No-Slip
          const float3 v=motionvel[p1];
          const float3 v2=make_float3(v.x+v.x-velrhopfinal.x,v.y+v.y-velrhopfinal.y,v.z+v.z-velrhopfinal.z);
          velrhop[p1].w=rhopfinal;
          if(tangenvel)tangenvel[p1]=KerMdbc2TangenVel(bnormalp1,v2);
          sigma[p1]=sigmafinal;//mdbr
          if(extrapolatepore && sumwab>0)porepress[p1]=float(double(porepress0[p1])+pwexcesssum/double(sumwab));
        }
        if(tslip==SLIP_FreeSlip){//-Free-slip keeps boundary velocity and stores extrapolated tangential velocity.
          velrhop[p1].w=rhopfinal;
          if(tangenvel)tangenvel[p1]=KerMdbc2TangenVel(bnormalp1,velrhopfinal);
          sigma[p1]=sigmafinal;//mdbr
          if(extrapolatepore && sumwab>0)porepress[p1]=float(double(porepress0[p1])+pwexcesssum/double(sumwab));
        }
      }
      else if(useboundmode){
        boundmode[p1]=BMODE_MDBC2OFF;
        velrhop[p1].w=CTE.rhopzero;
        const tsymatrix3f sigmazero={0,0,0,0,0,0};
        sigma[p1]=sigmazero;
        if(tangenvel)tangenvel[p1]=KerMdbc2TangenVel(bnormalp1,motionvel[p1]);
      }
    }
  }
}


//==============================================================================
/// Calculates extrapolated data on boundary particles from fluid domain for mDBC.
/// Calcula datos extrapolados en el contorno para mDBC.
//==============================================================================
template<TpKernel tker,bool sim2d,TpSlipMode tslip> void Interaction_MdbcCorrectionT2(
  bool fastsingle,unsigned n,unsigned nbound,float mdbcthreshold,const StDivDataGpu &dvd
  ,const tdouble3 &mapposmin,const double2 *posxy,const double *posz,const float4 *poscell
  ,const typecode *code,const unsigned *idp,const float3 *boundnormal,const float3 *motionvel
  ,float4 *velrhop,tsymatrix3f *sigma,byte *boundmode,float3 *tangenvel
  ,const float *porepress0,float *porepress)
{
  const int2* beginendcellfluid=dvd.beginendcell+dvd.cellfluid;
  const float determlimit=1e-3f;
  //-Interaction GhostBoundaryNodes-Fluid.
  if(n){
    const unsigned bsbound=128;
    dim3 sgridb=cusph::GetSimpleGridSize(n,bsbound);
    if(fastsingle){//-mDBC-Fast_v2
      KerInteractionMdbcCorrection_Fast <tker,sim2d,tslip> <<<sgridb,bsbound>>> (n,nbound
        ,determlimit,mdbcthreshold,Double3(mapposmin),dvd.poscellsize,poscell
        ,dvd.scelldiv,dvd.nc,dvd.cellzero,beginendcellfluid
        ,posxy,posz,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,tangenvel,porepress0,porepress);
    }
    else{//-mDBC_v0
      KerInteractionMdbcCorrection_Dbl <tker,sim2d,tslip> <<<sgridb,bsbound>>> (n,nbound
        ,determlimit,mdbcthreshold,dvd.scelldiv,dvd.nc,dvd.cellzero,beginendcellfluid
        ,posxy,posz,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,tangenvel,porepress0,porepress);
    }
  }
}
//==============================================================================
template<TpKernel tker> void Interaction_MdbcCorrectionT(bool simulate2d
  ,TpSlipMode slipmode,bool fastsingle,unsigned n,unsigned nbound
  ,float mdbcthreshold,const StDivDataGpu &dvd,const tdouble3 &mapposmin
  ,const double2 *posxy,const double *posz,const float4 *poscell,const typecode *code
  ,const unsigned *idp,const float3 *boundnormal,const float3 *motionvel,float4 *velrhop,tsymatrix3f *sigma,byte *boundmode,float3 *tangenvel
  ,const float *porepress0,float *porepress)
{
  switch(slipmode){
    case SLIP_Vel0:{ const TpSlipMode tslip=SLIP_Vel0;
      if(simulate2d)Interaction_MdbcCorrectionT2 <tker,true ,tslip> (fastsingle,n,nbound,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,tangenvel,porepress0,porepress);
      else          Interaction_MdbcCorrectionT2 <tker,false,tslip> (fastsingle,n,nbound,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,tangenvel,porepress0,porepress);
    }break;
    case SLIP_NoSlip:{ const TpSlipMode tslip=SLIP_NoSlip;
      if(simulate2d)Interaction_MdbcCorrectionT2 <tker,true ,tslip> (fastsingle,n,nbound,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,tangenvel,porepress0,porepress);
      else          Interaction_MdbcCorrectionT2 <tker,false,tslip> (fastsingle,n,nbound,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,tangenvel,porepress0,porepress);
    }break;
    case SLIP_FreeSlip:{ const TpSlipMode tslip=SLIP_FreeSlip;
      if(simulate2d)Interaction_MdbcCorrectionT2 <tker,true ,tslip> (fastsingle,n,nbound,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,tangenvel,porepress0,porepress);
      else          Interaction_MdbcCorrectionT2 <tker,false,tslip> (fastsingle,n,nbound,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,tangenvel,porepress0,porepress);
    }break;
    default: throw "SlipMode unknown at Interaction_MdbcCorrectionT().";
  }
}
//==============================================================================
/// Calculates extrapolated data on boundary particles from fluid domain for mDBC.
/// Calcula datos extrapolados en el contorno para mDBC.
//==============================================================================
void Interaction_MdbcCorrection(TpKernel tkernel,bool simulate2d,TpSlipMode slipmode
  ,bool fastsingle,unsigned n,unsigned nbound,float mdbcthreshold
  ,const StDivDataGpu &dvd,const tdouble3 &mapposmin
  ,const double2 *posxy,const double *posz,const float4 *poscell,const typecode *code
  ,const unsigned *idp,const float3 *boundnormal,const float3 *motionvel,float4 *velrhop,tsymatrix3f *sigma,byte *boundmode,float3 *tangenvel
  ,const float *porepress0,float *porepress)
{
  switch(tkernel){
    case KERNEL_Wendland:{ const TpKernel tker=KERNEL_Wendland;
      Interaction_MdbcCorrectionT <tker> (simulate2d,slipmode,fastsingle,n,nbound,mdbcthreshold
        ,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,tangenvel,porepress0,porepress);
    }break;
#ifndef DISABLE_KERNELS_EXTRA
    case KERNEL_Cubic:{ const TpKernel tker=KERNEL_Cubic;
      Interaction_MdbcCorrectionT <tker> (simulate2d,slipmode,fastsingle,n,nbound,mdbcthreshold
        ,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,tangenvel,porepress0,porepress);
    }break;
#endif
    default: throw "Kernel unknown at Interaction_MdbcCorrection().";
  }
}
//<vs_cdbc_ini>
//------------------------------------------------------------------------------
/// Perform interaction between boundary and fluid.
//------------------------------------------------------------------------------
template<TpKernel tker,bool sim2d,TpSlipMode tslip> __global__ void KerInteractionCdbcCorrection_Fast
  (unsigned n,unsigned nbound,float determlimit,float mdbcthreshold
  ,float poscellsize,const unsigned* dcell,const float4 *poscell
  ,int scelldiv,int4 nc,int3 cellzero,const int2 *beginendcellfluid
  ,const double2 *posxy,const double *posz,const typecode *code,const unsigned *idp
  ,const float3 *motionvel,float4 *velrhop,tsymatrix3f *sigma)
{
  const unsigned p1=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p1<n){
      const typecode cod=code[p1];
      if(CODE_IsNotFluid(cod)){
      float rhopfinal=FLT_MAX;
      float3 velrhopfinal=make_float3(0,0,0);
	  tsymatrix3f sigmafinal={0,0,0,0,0,0};//mdbr
      float sumwab=0;

      //if(CODE_IsFloating(cod)) printf("floating objects are included");
      //-Calculates ghost node position.
      //double3 gposp1=make_double3(posxy[p1].x, posxy[p1].y, posz[p1]);
      //gposp1=(CTE.periactive!=0? KerUpdatePeriodicPos(gposp1): gposp1); //-Corrected interface Position.
      //const float4 gpscellp1=KerComputePosCell(gposp1,mapposmin,poscellsize);
      const float4 pscellp1=poscell[p1];
      //-Initializes variables for calculation.
	  //===== mdbr
	  //-Solid stress
	  tsymatrix3f sigmap1 = { 0,0,0,0,0,0 };//-First-order Stress value
	  float3 gradsigmaxxp1 = make_float3(0,0,0);//-Stress gradient
	  float3 gradsigmayyp1 = make_float3(0,0,0);
	  float3 gradsigmazzp1 = make_float3(0,0,0);
	  float3 gradsigmaxyp1 = make_float3(0,0,0);
	  float3 gradsigmayzp1 = make_float3(0,0,0);
	  float3 gradsigmaxzp1 = make_float3(0,0,0);
	  //=====
      float3 velp1=make_float3(0,0,0);                              // -Only for velocity
      tmatrix3f a_corr2; if(sim2d) cumath::Tmatrix3fReset(a_corr2); //-Only for 2D.
      tmatrix4f a_corr3; if(!sim2d)cumath::Tmatrix4fReset(a_corr3); //-Only for 3D.
    
      //-Obtains neighborhood search limits.
      int ini1,fin1,ini2,fin2,ini3,fin3;
      //cunsearch::InitCte(gposp1.x,gposp1.y,gposp1.z,scelldiv,nc,cellzero,ini1,fin1,ini2,fin2,ini3,fin3);
      cunsearch::InitCte(dcell[p1],scelldiv,nc,cellzero,ini1,fin1,ini2,fin2,ini3,fin3);
      //-Boundary-Fluid interaction.
      for(int c3=ini3;c3<fin3;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
        unsigned pini,pfin=0;  cunsearch::ParticleRange(c2,c3,ini1,fin1,beginendcellfluid,pini,pfin);
        if(pfin)for(unsigned p2=pini;p2<pfin;p2++){
          const float4 pscellp2=poscell[p2];
          float drx=pscellp1.x-pscellp2.x + CTE.poscellsize*(PSCEL_GetfX(pscellp1.w)-PSCEL_GetfX(pscellp2.w));
          float dry=pscellp1.y-pscellp2.y + CTE.poscellsize*(PSCEL_GetfY(pscellp1.w)-PSCEL_GetfY(pscellp2.w));
          float drz=pscellp1.z-pscellp2.z + CTE.poscellsize*(PSCEL_GetfZ(pscellp1.w)-PSCEL_GetfZ(pscellp2.w));
          const float rr2=drx*drx+dry*dry+drz*drz;
          if(rr2<=CTE.kernelsize2 && rr2>=ALMOSTZERO && CODE_IsFluid(code[p2])){//-Only with fluid particles (including inout).
            //-Computes kernel.
            float fac;
            const float wab=cufsph::GetKernel_WabFac<tker>(rr2,fac);
            const float frx=fac*drx,fry=fac*dry,frz=fac*drz; //-Gradients.

            //===== Get mass and volume of particle p2 =====
            const float4 velrhopp2=velrhop[p2];
			const tsymatrix3f sigmap2=sigma[p2];//mdbr
            float massp2=CTE.massf;
            const float volp2=massp2/velrhopp2.w;

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
            velp1.x+=vwab*velrhopp2.x;
            velp1.y+=vwab*velrhopp2.y;
            velp1.z+=vwab*velrhopp2.z;

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
      if(sumwab>=mdbcthreshold){
        if(sim2d){
          const double determ=cumath::Determinant3x3dbl(a_corr2);
          if(fabs(determ)>=determlimit){//-Use 1e-3f (first_order) or 1e+3f (zeroth_order).
            const tmatrix3f invacorr2=cumath::InverseMatrix3x3dbl(a_corr2,determ);
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
        else if(a_corr2.a11>0){//-Determinant is small but a11 is nonzero, 0th order ANGELO.
			      //====mdbr
			      sigmafinal.xx = float(sigmap1.xx / a_corr2.a11);
			      sigmafinal.zz = float(sigmap1.zz / a_corr2.a11);
			      sigmafinal.xz = float(sigmap1.xz / a_corr2.a11);
          }
           //-Ghost node velocity (0th order).
          if(tslip!=SLIP_Vel0&&a_corr2.a11>0){
            velrhopfinal.x=float(velp1.x/a_corr2.a11);
            velrhopfinal.z=float(velp1.z/a_corr2.a11);
            velrhopfinal.y=0;
          }
        }
        else{
          const double determ=cumath::Determinant4x4dbl(a_corr3);
          if(fabs(determ)>=determlimit){//determlimit fabs(determ)>=1e+3f
            const tmatrix4f invacorr3=cumath::InverseMatrix4x4dbl(a_corr3,determ);
            //printf(">> determ :%.8f ", determ);
			//-Ghost stress ==== mdbr
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
          else if(a_corr3.a11>0){//-Determinant is small but a11 is nonzero, 0th order ANGELO.
			      sigmafinal.xx = float(sigmap1.xx / a_corr3.a11);
			      sigmafinal.yy = float(sigmap1.yy / a_corr3.a11);
			      sigmafinal.zz = float(sigmap1.zz / a_corr3.a11);
			      sigmafinal.xy = float(sigmap1.xy / a_corr3.a11);
			      sigmafinal.yz = float(sigmap1.yz / a_corr3.a11);
			      sigmafinal.xz = float(sigmap1.xz / a_corr3.a11);
          }
          //-Ghost node velocity (0th order).
          if(tslip!=SLIP_Vel0&&a_corr3.a11>0){
            velrhopfinal.x=float(velp1.x/a_corr3.a11);
            velrhopfinal.y=float(velp1.y/a_corr3.a11);
            velrhopfinal.z=float(velp1.z/a_corr3.a11);
          }
        }        
        if (tslip==SLIP_Vel0) {//-DBC velocity as it is
            velrhopfinal = make_float3(velrhop[p1].x, velrhop[p1].y, velrhop[p1].z);
      }
        if (tslip==SLIP_NoSlip) {//-No-Slip
      const float3 v = motionvel[p1];
            velrhopfinal = make_float3(v.x + v.x - velrhopfinal.x, v.y + v.y - velrhopfinal.y, v.z + v.z - velrhopfinal.z);
        }
      }
      //-Store the results.
      rhopfinal=CTE.rhopzero;// (rhopfinal != FLT_MAX ? rhopfinal : CTE.rhopzero);
      velrhop[p1] = make_float4(velrhopfinal.x, velrhopfinal.y, velrhopfinal.z, rhopfinal);
      sigma[p1] = sigmafinal;
  }
  }
}
//==============================================================================
/// Calculates extrapolated data on boundary particles from fluid domain for cDBC.
/// Calcula datos extrapolados en el contorno para cDBC.
//==============================================================================
template<TpKernel tker,bool sim2d,TpSlipMode tslip> void Interaction_CdbcCorrectionT2(
  unsigned n,unsigned nbound,float mdbcthreshold,const StDivDataGpu &dvd
  ,const double2 *posxy,const double *posz,const unsigned* dcell,const float4 *poscell
  ,const typecode *code,const unsigned *idp,const float3 *motionvel
  ,float4 *velrhop,tsymatrix3f *sigma)
{
  const int2* beginendcellfluid=dvd.beginendcell+dvd.cellfluid;
  const float determlimit=1e-3f;
  //-Interaction GhostBoundaryNodes-Fluid.
  if(n){
    const unsigned bsbound=128;
    dim3 sgridb=cusph::GetSimpleGridSize(n,bsbound);
      KerInteractionCdbcCorrection_Fast <tker,sim2d,tslip> <<<sgridb,bsbound>>> (n,nbound
        ,determlimit,mdbcthreshold,dvd.poscellsize,dcell,poscell
        ,dvd.scelldiv,dvd.nc,dvd.cellzero,beginendcellfluid
        ,posxy,posz,code,idp,motionvel,velrhop,sigma);
  }
}
//==============================================================================
template<TpKernel tker> void Interaction_CdbcCorrectionT(bool simulate2d
  ,TpSlipMode slipmode,unsigned n,unsigned nbound
  ,float mdbcthreshold,const StDivDataGpu &dvd
  ,const double2 *posxy,const double *posz
  ,const unsigned* dcell,const float4 *poscell,const typecode *code
  ,const unsigned *idp,const float3 *motionvel,float4 *velrhop,tsymatrix3f *sigma)
{
  switch(slipmode){
    case SLIP_Vel0:{ const TpSlipMode tslip=SLIP_Vel0;
      if(simulate2d)Interaction_CdbcCorrectionT2 <tker,true ,tslip> (n,nbound,mdbcthreshold,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma);
      else          Interaction_CdbcCorrectionT2 <tker,false,tslip> (n,nbound,mdbcthreshold,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma);
    }break;
    case SLIP_NoSlip:{ const TpSlipMode tslip=SLIP_NoSlip;
      if(simulate2d)Interaction_CdbcCorrectionT2 <tker,true ,tslip> (n,nbound,mdbcthreshold,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma);
      else          Interaction_CdbcCorrectionT2 <tker,false,tslip> (n,nbound,mdbcthreshold,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma);
    }break;
#ifndef DISABLE_MDBC_EXTRAMODES
    case SLIP_FreeSlip:{ const TpSlipMode tslip=SLIP_FreeSlip;
      if(simulate2d)Interaction_CdbcCorrectionT2 <tker,true ,tslip> (n,nbound,mdbcthreshold,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma);
      else          Interaction_CdbcCorrectionT2 <tker,false,tslip> (n,nbound,mdbcthreshold,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma);
    }break;
#endif
    default: throw "SlipMode unknown at Interaction_CdbcCorrectionT().";
  }
}
//==============================================================================
/// Calculates extrapolated data on boundary particles from fluid domain for cDBC.
/// Calcula datos extrapolados en el contorno para cDBC.
//==============================================================================
void Interaction_CdbcCorrection(TpKernel tkernel,bool simulate2d
    ,TpSlipMode slipmode,unsigned n,unsigned nbound,float mdbcthreshold
    ,const StDivDataGpu &dvd,const double2 *posxy,const double *posz
    ,const unsigned* dcell,const float4 *poscell,const typecode *code,const unsigned *idp
    ,const float3 *motionvel,float4 *velrhop,tsymatrix3f *sigma)
{
  switch(tkernel){
    case KERNEL_Wendland:{ const TpKernel tker=KERNEL_Wendland;
      Interaction_CdbcCorrectionT <tker> (simulate2d,slipmode,n,nbound,mdbcthreshold
        ,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma);
    }break;
#ifndef DISABLE_KERNELS_EXTRA
    case KERNEL_Cubic:{ const TpKernel tker=KERNEL_Cubic;
      Interaction_CdbcCorrectionT <tker> (simulate2d,slipmode,n,nbound,mdbcthreshold
        ,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma);
    }break;
#endif
    default: throw "Kernel unknown at Interaction_CdbcCorrection().";
  }
}
//<vs_cdbc_end>

//##############################################################################
//# Kernels for DEM interaction.
//# Kernels para interaccion DEM.
//##############################################################################
//------------------------------------------------------------------------------
/// DEM interaction of a particle with a set of particles. (Float-Float/Bound)
/// Realiza la interaccion DEM de una particula con un conjunto de ellas. (Float-Float/Bound)
//------------------------------------------------------------------------------
__device__ void KerInteractionForcesDemBox 
  (bool boundp2,const unsigned &pini,const unsigned &pfin
  ,const float4 *demdata,float dtforce
  ,const float4 *poscell,const float4 *velrhop,const typecode *code,const unsigned *idp
  ,const float4 &pscellp1,const float4 &velp1,typecode tavp1,float masstotp1
  ,float ftmassp1,float taup1,float kfricp1,float restitup1
  ,float3 &acep1,float &demdtp1)
{
  for(int p2=pini;p2<pfin;p2++){
    const typecode codep2=code[p2];
    if(CODE_IsNotFluid(codep2) && tavp1!=CODE_GetTypeAndValue(codep2)){
      const float4 pscellp2=poscell[p2];
      const float drx=pscellp1.x-pscellp2.x + CTE.poscellsize*(PSCEL_GetfX(pscellp1.w)-PSCEL_GetfX(pscellp2.w));
      const float dry=pscellp1.y-pscellp2.y + CTE.poscellsize*(PSCEL_GetfY(pscellp1.w)-PSCEL_GetfY(pscellp2.w));
      const float drz=pscellp1.z-pscellp2.z + CTE.poscellsize*(PSCEL_GetfZ(pscellp1.w)-PSCEL_GetfZ(pscellp2.w));
      const float rr2=drx*drx+dry*dry+drz*drz;
      const float rad=sqrt(rr2);

      //-Computes maximum value of demdt.
      float4 demdatap2=demdata[CODE_GetTypeAndValue(codep2)];
      const float nu_mass=(boundp2? masstotp1/2: masstotp1*demdatap2.x/(masstotp1+demdatap2.x)); //-With boundary takes the actual mass of floating 1. | Con boundary toma la propia masa del floating 1.
      const float kn=4/(3*(taup1+demdatap2.y))*sqrt(CTE.dp/4); //-Generalized rigidity - Lemieux 2008.
      const float dvx=velp1.x-velrhop[p2].x, dvy=velp1.y-velrhop[p2].y, dvz=velp1.z-velrhop[p2].z; //vji
      const float nx=drx/rad, ny=dry/rad, nz=drz/rad; //-normal_ji             
      const float vn=dvx*nx+dvy*ny+dvz*nz; //-vji.nji    
      const float demvisc=0.2f/(3.21f*(pow(nu_mass/kn,0.4f)*pow(fabs(vn),-0.2f))/40.f);
      if(demdtp1<demvisc)demdtp1=demvisc;

      const float over_lap=1.0f*CTE.dp-rad; //-(ri+rj)-|dij|
      if(over_lap>0.0f){ //-Contact.
        //-Normal.
        const float eij=(restitup1+demdatap2.w)/2;
        const float gn=-(2.0f*log(eij)*sqrt(nu_mass*kn))/(sqrt(float(PI)+log(eij)*log(eij))); //-Generalized damping - Cummins 2010.
        //const float gn=0.08f*sqrt(nu_mass*sqrt(CTE.dp/2)/((taup1+demdatap2.y)/2)); //-generalized damping - Lemieux 2008.
        const float rep=kn*pow(over_lap,1.5f);
        const float fn=rep-gn*pow(over_lap,0.25f)*vn;
        float acef=fn/ftmassp1; //-Divides by the mass of particle to obtain the acceleration.
        acep1.x+=(acef*nx); acep1.y+=(acef*ny); acep1.z+=(acef*nz); //-Force is applied in the normal between the particles.
        //-Tangencial.
        const float dvxt=dvx-vn*nx, dvyt=dvy-vn*ny, dvzt=dvz-vn*nz; //Vji_t
        const float vt=sqrt(dvxt*dvxt + dvyt*dvyt + dvzt*dvzt);
        const float tx=(vt!=0? dvxt/vt: 0), ty=(vt!=0? dvyt/vt: 0), tz=(vt!=0? dvzt/vt: 0); //-Tang vel unit vector.
        const float ft_elast=2*(kn*dtforce-gn)*vt/7; //-Elastic frictional string -->  ft_elast=2*(kn*fdispl-gn*vt)/7; fdispl=dtforce*vt;
        const float kfric_ij=(kfricp1+demdatap2.z)/2;
        float ft=kfric_ij*fn*tanh(8*vt);  //-Coulomb.
        ft=(ft<ft_elast? ft: ft_elast);   //-Not above yield criteria, visco-elastic model.
        acef=ft/ftmassp1; //-Divides by the mass of particle to obtain the acceleration.
        acep1.x+=(acef*tx); acep1.y+=(acef*ty); acep1.z+=(acef*tz);
      }
    }
  }
}

//------------------------------------------------------------------------------
/// Interaction between particles. Fluid/Float-Fluid/Float or Fluid/Float-Bound.
/// Includes artificial/laminar viscosity and normal/DEM floating bodies.
///
/// Realiza interaccion entre particulas. Fluid/Float-Fluid/Float or Fluid/Float-Bound
/// Incluye visco artificial/laminar y floatings normales/dem.
//------------------------------------------------------------------------------
__global__ void KerInteractionForcesDem(unsigned nfloat
  ,int scelldiv,int4 nc,int3 cellzero,const int2 *begincell,unsigned cellfluid,const unsigned *dcell
  ,const unsigned *ftridp,const float4 *demdata,const float *ftomassp,float dtforce
  ,const float4 *poscell,const float4 *velrhop,const typecode *code,const unsigned *idp
  ,float *viscdt,float3 *ace)
{
  const unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<nfloat){
    const unsigned p1=ftridp[p]; //-Number of particle.
    if(p1!=UINT_MAX){
      float demdtp1=0;
      float3 acep1=make_float3(0,0,0);

      //-Obtains basic data of particle p1.
      const float4 pscellp1=poscell[p1];
      const float4 velp1=velrhop[p1];
      const typecode cod=code[p1];
      const typecode tavp1=CODE_GetTypeAndValue(cod);
      const float4 rdata=demdata[tavp1];
      const float masstotp1=rdata.x;
      const float taup1=rdata.y;
      const float kfricp1=rdata.z;
      const float restitup1=rdata.w;
      const float ftmassp1=ftomassp[CODE_GetTypeValue(cod)];

      //-Obtains neighborhood search limits.
      int ini1,fin1,ini2,fin2,ini3,fin3;
      cunsearch::InitCte(dcell[p1],scelldiv,nc,cellzero,ini1,fin1,ini2,fin2,ini3,fin3);

      //-Interaction with boundaries.
      for(int c3=ini3;c3<fin3;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
        unsigned pini,pfin=0;  cunsearch::ParticleRange(c2,c3,ini1,fin1,begincell,pini,pfin);
        if(pfin)KerInteractionForcesDemBox (true ,pini,pfin,demdata,dtforce,poscell,velrhop,code,idp,pscellp1,velp1,tavp1,masstotp1,ftmassp1,taup1,kfricp1,restitup1,acep1,demdtp1);
      }

      //-Interaction with fluids.
      ini3+=cellfluid; fin3+=cellfluid;
      for(int c3=ini3;c3<fin3;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
        unsigned pini,pfin=0;  cunsearch::ParticleRange(c2,c3,ini1,fin1,begincell,pini,pfin);
        if(pfin)KerInteractionForcesDemBox (false,pini,pfin,demdata,dtforce,poscell,velrhop,code,idp,pscellp1,velp1,tavp1,masstotp1,ftmassp1,taup1,kfricp1,restitup1,acep1,demdtp1);
      }

      //-Stores results.
      if(acep1.x || acep1.y || acep1.z || demdtp1){
        float3 r=ace[p1]; r.x+=acep1.x; r.y+=acep1.y; r.z+=acep1.z; ace[p1]=r;
        if(viscdt[p1]<demdtp1)viscdt[p1]=demdtp1;
      }
    }
  }
}

#ifndef DISABLE_BSMODES
//==============================================================================
/// Collects kernel information.
//==============================================================================
void Interaction_ForcesDemT_KerInfo(StKerInfo *kerinfo)
{
#if CUDART_VERSION >= 6050
  {
    typedef void (*fun_ptr)(unsigned,int,int4,int3,const int2*,unsigned,const unsigned*,const unsigned*,const float4*,const float*,float,const float4*,const float4*,const typecode*,const unsigned*,float*,float3*);
    fun_ptr ptr=&KerInteractionForcesDem;
    int qblocksize=0,mingridsize=0;
    cudaOccupancyMaxPotentialBlockSize(&mingridsize,&qblocksize,(void*)ptr,0,0);
    struct cudaFuncAttributes attr;
    cudaFuncGetAttributes(&attr,(void*)ptr);
    kerinfo->forcesdem_bs=qblocksize;
    kerinfo->forcesdem_rg=attr.numRegs;
    kerinfo->forcesdem_bsmax=attr.maxThreadsPerBlock;
    //printf(">> KerInteractionForcesDem  blocksize:%u (%u)\n",qblocksize,0);
  }
  fcuda::Check_CudaErroorFun("Error collecting kernel information.");
#endif
}
#endif

//==============================================================================
/// Interaction for the force computation.
/// Interaccion para el calculo de fuerzas.
//==============================================================================
void Interaction_ForcesDem(unsigned bsize,unsigned nfloat
  ,const StDivDataGpu &dvd,const unsigned *dcell
  ,const unsigned *ftridp,const float4 *demdata,const float *ftomassp,float dtforce
  ,const float4 *poscell,const float4 *velrhop
  ,const typecode *code,const unsigned *idp,float *viscdt,float3 *ace,StKerInfo *kerinfo)
{
  const int2* beginendcell=dvd.beginendcell;
  //-Collects kernel information.
#ifndef DISABLE_BSMODES
  if(kerinfo){
    Interaction_ForcesDemT_KerInfo(kerinfo);
    return;
  }
#endif
  //-Interaction Fluid-Fluid & Fluid-Bound.
  if(nfloat){
    dim3 sgrid=GetSimpleGridSize(nfloat,bsize);
    KerInteractionForcesDem <<<sgrid,bsize>>> (nfloat
      ,dvd.scelldiv,dvd.nc,dvd.cellzero,beginendcell,dvd.cellfluid,dcell
      ,ftridp,demdata,ftomassp,dtforce,poscell,velrhop,code,idp,viscdt,ace);
  }
}


//##############################################################################
//# Kernels for Laminar+SPS.
//##############################################################################
//------------------------------------------------------------------------------
/// Computes sub-particle stress tensor (Tau) for SPS turbulence model.
//------------------------------------------------------------------------------
__global__ void KerComputeSpsTau(unsigned n,unsigned pini,float smag,float blin
  ,const float4 *velrhop,const float2 *gradvelff,float2 *tauff)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; 
  if(p<n){
    const unsigned p1=p+pini;
    float2 rr=gradvelff[p1*3];   const float grad_xx=rr.x,grad_xy=rr.y;
           rr=gradvelff[p1*3+1]; const float grad_xz=rr.x,grad_yy=rr.y;
           rr=gradvelff[p1*3+2]; const float grad_yz=rr.x,grad_zz=rr.y;
    const float pow1=grad_xx*grad_xx + grad_yy*grad_yy + grad_zz*grad_zz;
    const float prr= grad_xy*grad_xy + grad_xz*grad_xz + grad_yz*grad_yz + pow1+pow1;
    const float visc_sps=smag*sqrt(prr);
    const float div_u=grad_xx+grad_yy+grad_zz;
    const float sps_k=(2.0f/3.0f)*visc_sps*div_u;
    const float sps_blin=blin*prr;
    const float sumsps=-(sps_k+sps_blin);
    const float twovisc_sps=(visc_sps+visc_sps);
    float one_rho2=1.0f/velrhop[p1].w;
    //-Computes new values of tau[].
    const float tau_xx=one_rho2*(twovisc_sps*grad_xx +sumsps);
    const float tau_xy=one_rho2*(visc_sps   *grad_xy);
    tauff[p1*3]=make_float2(tau_xx,tau_xy);
    const float tau_xz=one_rho2*(visc_sps   *grad_xz);
    const float tau_yy=one_rho2*(twovisc_sps*grad_yy +sumsps);
    tauff[p1*3+1]=make_float2(tau_xz,tau_yy);
    const float tau_yz=one_rho2*(visc_sps   *grad_yz);
    const float tau_zz=one_rho2*(twovisc_sps*grad_zz +sumsps);
    tauff[p1*3+2]=make_float2(tau_yz,tau_zz);
  }
}

//==============================================================================
/// Computes sub-particle stress tensor (Tau) for SPS turbulence model.
//==============================================================================
void ComputeSpsTau(unsigned np,unsigned npb,float smag,float blin
  ,const float4 *velrhop,const tsymatrix3f *gradvelg,tsymatrix3f *tau,cudaStream_t stm)
{
  const unsigned npf=np-npb;
  if(npf){
    dim3 sgridf=GetSimpleGridSize(npf,SPHBSIZE);
    KerComputeSpsTau <<<sgridf,SPHBSIZE,0,stm>>> (npf,npb,smag,blin,velrhop,(const float2*)gradvelg,(float2*)tau);
  }
}


//##############################################################################
//# Kernels for Delta-SPH.
//# Kernels para Delta-SPH.
//##############################################################################
//------------------------------------------------------------------------------
/// Adds value of delta[] to ar[] provided it is not FLT_MAX.
/// Anhade valor de delta[] a ar[] siempre que no sea FLT_MAX.
//------------------------------------------------------------------------------
__global__ void KerAddDelta(unsigned n,const float *delta,float *ar)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    float rdelta=delta[p];
    if(rdelta!=FLT_MAX)ar[p]+=rdelta;
  }
}

//==============================================================================
/// Adds value of delta[] to ar[] provided it is not FLT_MAX.
/// Anhade valor de delta[] a ar[] siempre que no sea FLT_MAX.
//==============================================================================
void AddDelta(unsigned n,const float *delta,float *ar,cudaStream_t stm){
  if(n){
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    KerAddDelta <<<sgrid,SPHBSIZE,0,stm>>> (n,delta,ar);
  }
}


//##############################################################################
//# Kernels para ComputeStep (position)
//# Kernels for ComputeStep (position)
//##############################################################################
//------------------------------------------------------------------------------
/// Updates particle position according to displacement.
/// Actualizacion de posicion de particulas segun desplazamiento.
//------------------------------------------------------------------------------
template<bool periactive,bool floatings> __global__ void KerComputeStepPos(unsigned n,unsigned pini
  ,const double2 *movxy,const double *movz
  ,double2 *posxy,double *posz,unsigned *dcell,typecode *code)
{
  unsigned pt=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(pt<n){
    unsigned p=pt+pini;
    const typecode rcode=code[p];
    const bool outrhop=CODE_IsOutRhop(rcode);
    const bool fluid=(!floatings || CODE_IsFluid(rcode));
    const bool normal=(!periactive || outrhop || CODE_IsNormal(rcode));
    if(normal && fluid){ //-Does not apply to periodic or floating particles. | No se aplica a particulas periodicas o floating.
      const double2 rmovxy=movxy[p];
      KerUpdatePos<periactive>(posxy[p],posz[p],rmovxy.x,rmovxy.y,movz[p],outrhop,p,posxy,posz,dcell,code);
    }
    //-In case of floating maintains the original position.
    //-En caso de floating mantiene la posicion original.
  }
}

//==============================================================================
/// Updates particle position according to displacement.
/// Actualizacion de posicion de particulas segun desplazamiento.
//==============================================================================
void ComputeStepPos(byte periactive,bool floatings,unsigned np,unsigned npb
  ,const double2 *movxy,const double *movz
  ,double2 *posxy,double *posz,unsigned *dcell,typecode *code)
{
  const unsigned pini=npb;
  const unsigned npf=np-pini;
  if(npf){
    dim3 sgrid=GetSimpleGridSize(npf,SPHBSIZE);
    if(periactive){ const bool peri=true;
      if(floatings)KerComputeStepPos<peri,true>  <<<sgrid,SPHBSIZE>>> (npf,pini,movxy,movz,posxy,posz,dcell,code);
      else         KerComputeStepPos<peri,false> <<<sgrid,SPHBSIZE>>> (npf,pini,movxy,movz,posxy,posz,dcell,code);
    }
    else{ const bool peri=false;
      if(floatings)KerComputeStepPos<peri,true>  <<<sgrid,SPHBSIZE>>> (npf,pini,movxy,movz,posxy,posz,dcell,code);
      else         KerComputeStepPos<peri,false> <<<sgrid,SPHBSIZE>>> (npf,pini,movxy,movz,posxy,posz,dcell,code);
    }
  }
}

//------------------------------------------------------------------------------
/// Updates particle position according to displacement.
/// Actualizacion de posicion de particulas segun desplazamiento.
//------------------------------------------------------------------------------
template<bool periactive,bool floatings> __global__ void KerComputeStepPos2(unsigned n,unsigned pini
  ,const double2 *posxypre,const double *poszpre,const double2 *movxy,const double *movz
  ,double2 *posxy,double *posz,unsigned *dcell,typecode *code)
{
  unsigned pt=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(pt<n){
    unsigned p=pt+pini;
    const typecode rcode=code[p];
    const bool outrhop=CODE_IsOutRhop(rcode);
    const bool fluid=(!floatings || CODE_IsFluid(rcode));
    const bool normal=(!periactive || outrhop || CODE_IsNormal(rcode));
    if(normal){//-Does not apply to periodic particles. | No se aplica a particulas periodicas
      if(fluid){//-Only applied for fluid displacement. | Solo se aplica desplazamiento al fluido.
        const double2 rmovxy=movxy[p];
        KerUpdatePos<periactive>(posxypre[p],poszpre[p],rmovxy.x,rmovxy.y,movz[p],outrhop,p,posxy,posz,dcell,code);
      }
      else{ //-Copy position of floating particles.
        posxy[p]=posxypre[p];
        posz[p]=poszpre[p];
      }
    }
  }
}

//==============================================================================
/// Updates particle position according to displacement.
/// Actualizacion de posicion de particulas segun desplazamiento.
//==============================================================================
void ComputeStepPos2(byte periactive,bool floatings,unsigned np,unsigned npb
  ,const double2 *posxypre,const double *poszpre,const double2 *movxy,const double *movz
  ,double2 *posxy,double *posz,unsigned *dcell,typecode *code)
{
  const unsigned pini=npb;
  const unsigned npf=np-pini;
  if(npf){
    dim3 sgrid=GetSimpleGridSize(npf,SPHBSIZE);
    if(periactive){ const bool peri=true;
      if(floatings)KerComputeStepPos2<peri,true>  <<<sgrid,SPHBSIZE>>> (npf,pini,posxypre,poszpre,movxy,movz,posxy,posz,dcell,code);
      else         KerComputeStepPos2<peri,false> <<<sgrid,SPHBSIZE>>> (npf,pini,posxypre,poszpre,movxy,movz,posxy,posz,dcell,code);
    }
    else{ const bool peri=false;
      if(floatings)KerComputeStepPos2<peri,true>  <<<sgrid,SPHBSIZE>>> (npf,pini,posxypre,poszpre,movxy,movz,posxy,posz,dcell,code);
      else         KerComputeStepPos2<peri,false> <<<sgrid,SPHBSIZE>>> (npf,pini,posxypre,poszpre,movxy,movz,posxy,posz,dcell,code);
    }
  }
}



//##############################################################################
//# Kernels for motion.
//# Kernels para Motion
//##############################################################################
//------------------------------------------------------------------------------
/// Computes for a range of particles, their position according to idp[].
/// Calcula para un rango de particulas calcula su posicion segun idp[].
//------------------------------------------------------------------------------
__global__ void KerCalcRidp(unsigned n,unsigned ini,unsigned idini,unsigned idfin,const typecode *code,const unsigned *idp,unsigned *ridp)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    p+=ini;
    unsigned id=idp[p];
    if(idini<=id && id<idfin){
      if(CODE_IsNormal(code[p]))ridp[id-idini]=p;
    }
  }
}
//------------------------------------------------------------------------------
__global__ void KerCalcRidp(unsigned n,unsigned ini,unsigned idini,unsigned idfin,const unsigned *idp,unsigned *ridp)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    p+=ini;
    const unsigned id=idp[p];
    if(idini<=id && id<idfin)ridp[id-idini]=p;
  }
}

//==============================================================================
/// Calculate particle position according to idp[]. When it does not find UINT_MAX.
/// When periactive is false it means there are no duplicate particles (periodic)
/// and all are CODE_NORMAL.
///
/// Calcula posicion de particulas segun idp[]. Cuando no la encuentra es UINT_MAX.
/// Cuando periactive es False sumpone que no hay particulas duplicadas (periodicas)
/// y todas son CODE_NORMAL.
//==============================================================================
void CalcRidp(bool periactive,unsigned np,unsigned pini,unsigned idini,unsigned idfin,const typecode *code,const unsigned *idp,unsigned *ridp){
  //-Assigns values UINT_MAX
  const unsigned nsel=idfin-idini;
  cudaMemset(ridp,255,sizeof(unsigned)*nsel); 
  //-Computes position according to id. | Calcula posicion segun id.
  if(np){
    dim3 sgrid=GetSimpleGridSize(np,SPHBSIZE);
    if(periactive)KerCalcRidp <<<sgrid,SPHBSIZE>>> (np,pini,idini,idfin,code,idp,ridp);
    else          KerCalcRidp <<<sgrid,SPHBSIZE>>> (np,pini,idini,idfin,idp,ridp);
  }
}

//------------------------------------------------------------------------------
/// Applies a linear movement to a set of particles.
/// Aplica un movimiento lineal a un conjunto de particulas.
//------------------------------------------------------------------------------
template<bool periactive> __global__ void KerMoveLinBound(unsigned n,unsigned ini,double3 mvpos,float3 mvvel
  ,const unsigned *ridpmv,double2 *posxy,double *posz,unsigned *dcell,float4 *velrhop,typecode *code)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    int pid=ridpmv[p+ini];
    if(pid>=0){
      //-Computes displacement and updates position.
      KerUpdatePos<periactive>(posxy[pid],posz[pid],mvpos.x,mvpos.y,mvpos.z,false,pid,posxy,posz,dcell,code);
      //-Computes velocity.
      velrhop[pid]=make_float4(mvvel.x,mvvel.y,mvvel.z,velrhop[pid].w);
    }
  }
}

//==============================================================================
/// Applies a linear movement to a set of particles.
/// Aplica un movimiento lineal a un conjunto de particulas.
//==============================================================================
void MoveLinBound(byte periactive,unsigned np,unsigned ini,tdouble3 mvpos,tfloat3 mvvel
  ,const unsigned *ridp,double2 *posxy,double *posz,unsigned *dcell,float4 *velrhop,typecode *code)
{
  dim3 sgrid=GetSimpleGridSize(np,SPHBSIZE);
  if(periactive)KerMoveLinBound<true>  <<<sgrid,SPHBSIZE>>> (np,ini,Double3(mvpos),Float3(mvvel),ridp,posxy,posz,dcell,velrhop,code);
  else          KerMoveLinBound<false> <<<sgrid,SPHBSIZE>>> (np,ini,Double3(mvpos),Float3(mvvel),ridp,posxy,posz,dcell,velrhop,code);
}



//------------------------------------------------------------------------------
/// Applies a matrix movement to a set of particles.
/// Aplica un movimiento matricial a un conjunto de particulas.
//------------------------------------------------------------------------------
template<bool periactive,bool simulate2d> __global__ void KerMoveMatBound(unsigned n,unsigned ini,tmatrix4d m,double dt
  ,const unsigned *ridpmv,double2 *posxy,double *posz,unsigned *dcell,float4 *velrhop,typecode *code,float3 *boundnormal)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    int pid=ridpmv[p+ini];
    if(pid>=0){
      double2 rxy=posxy[pid];
      double3 rpos=make_double3(rxy.x,rxy.y,posz[pid]);
      //-Computes new position.
      double3 rpos2;
      rpos2.x= rpos.x*m.a11 + rpos.y*m.a12 + rpos.z*m.a13 + m.a14;
      rpos2.y= rpos.x*m.a21 + rpos.y*m.a22 + rpos.z*m.a23 + m.a24;
      rpos2.z= rpos.x*m.a31 + rpos.y*m.a32 + rpos.z*m.a33 + m.a34;
      if(simulate2d)rpos2.y=rpos.y;
      //-Computes displacement and updates position.
      const double dx=rpos2.x-rpos.x;
      const double dy=rpos2.y-rpos.y;
      const double dz=rpos2.z-rpos.z;
      KerUpdatePos<periactive>(make_double2(rpos.x,rpos.y),rpos.z,dx,dy,dz,false,pid,posxy,posz,dcell,code);
      //-Computes velocity.
      velrhop[pid]=make_float4(float(dx/dt),float(dy/dt),float(dz/dt),velrhop[pid].w);
      //-Computes normal.
      if(boundnormal){
        const float3 bnor=boundnormal[pid];
        const double3 gs=make_double3(rpos.x+bnor.x,rpos.y+bnor.y,rpos.z+bnor.z);
        const double gs2x=gs.x*m.a11 + gs.y*m.a12 + gs.z*m.a13 + m.a14;
        const double gs2y=gs.x*m.a21 + gs.y*m.a22 + gs.z*m.a23 + m.a24;
        const double gs2z=gs.x*m.a31 + gs.y*m.a32 + gs.z*m.a33 + m.a34;
        boundnormal[pid]=make_float3(gs2x-rpos2.x,gs2y-rpos2.y,gs2z-rpos2.z);
      }
    }
  }
}

//==============================================================================
/// Applies a matrix movement to a set of particles.
/// Aplica un movimiento matricial a un conjunto de particulas.
//==============================================================================
void MoveMatBound(byte periactive,bool simulate2d,unsigned np,unsigned ini,tmatrix4d m,double dt
  ,const unsigned *ridpmv,double2 *posxy,double *posz,unsigned *dcell,float4 *velrhop,typecode *code,float3 *boundnormal)
{
  dim3 sgrid=GetSimpleGridSize(np,SPHBSIZE);
  if(periactive){ const bool peri=true;
    if(simulate2d)KerMoveMatBound<peri,true>  <<<sgrid,SPHBSIZE>>> (np,ini,m,dt,ridpmv,posxy,posz,dcell,velrhop,code,boundnormal);
    else          KerMoveMatBound<peri,false> <<<sgrid,SPHBSIZE>>> (np,ini,m,dt,ridpmv,posxy,posz,dcell,velrhop,code,boundnormal);
  }
  else{ const bool peri=false;
    if(simulate2d)KerMoveMatBound<peri,true>  <<<sgrid,SPHBSIZE>>> (np,ini,m,dt,ridpmv,posxy,posz,dcell,velrhop,code,boundnormal);
    else          KerMoveMatBound<peri,false> <<<sgrid,SPHBSIZE>>> (np,ini,m,dt,ridpmv,posxy,posz,dcell,velrhop,code,boundnormal);
  }
}

//------------------------------------------------------------------------------
/// Copy motion velocity to MotionVel[].
/// Copia velocidad de movimiento a MotionVel[].
//------------------------------------------------------------------------------
template<bool periactive> __global__ void KerCopyMotionVel(unsigned n
  ,const unsigned *ridpmv,const float4 *velrhop,float3 *motionvel)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    int pid=ridpmv[p];
    if(pid>=0){
      //-Computes velocity.
      const float4 v=velrhop[pid];
      motionvel[pid]=make_float3(v.x,v.y,v.z);
    }
  }
}

//==============================================================================
/// Copy motion velocity to MotionVel[].
/// Copia velocidad de movimiento a MotionVel[].
//==============================================================================
void CopyMotionVel(unsigned nmoving,const unsigned *ridp,const float4 *velrhop,float3 *motionvel)
{
  dim3 sgrid=GetSimpleGridSize(nmoving,SPHBSIZE);
  KerCopyMotionVel<true>  <<<sgrid,SPHBSIZE>>> (nmoving,ridp,velrhop,motionvel);
}


//------------------------------------------------------------------------------
/// Applies a matrix movement to a set of particles.
/// Aplica un movimiento matricial a un conjunto de particulas.
//------------------------------------------------------------------------------
__global__ void KerFtNormalsUpdate(unsigned n,unsigned fpini
  ,double a11,double a12,double a13,double a21,double a22,double a23,double a31,double a32,double a33
  ,const unsigned *ftridp,float3 *boundnormal)
{
  const unsigned fp=blockIdx.x*blockDim.x + threadIdx.x; //-Number of floating particle.
  if(fp<n){
    const unsigned p=ftridp[fp+fpini];
    if(p!=UINT_MAX){
      float3 rnor=boundnormal[p];
      const double nx=rnor.x;
      const double ny=rnor.y;
      const double nz=rnor.z;
      rnor.x=float(a11*nx + a12*ny + a13*nz);
      rnor.y=float(a21*nx + a22*ny + a23*nz);
      rnor.z=float(a31*nx + a32*ny + a33*nz);
      boundnormal[p]=rnor;
    }
  }
}

//==============================================================================
/// Applies a matrix movement to a set of particles.
/// Aplica un movimiento matricial a un conjunto de particulas.
//==============================================================================
void FtNormalsUpdate(unsigned np,unsigned ini,tmatrix4d m,const unsigned *ftridp
  ,float3 *boundnormal)
{
  dim3 sgrid=GetSimpleGridSize(np,SPHBSIZE);
  if(np)KerFtNormalsUpdate <<<sgrid,SPHBSIZE>>> (np,ini,m.a11,m.a12,m.a13
    ,m.a21,m.a22,m.a23,m.a31,m.a32,m.a33,ftridp,boundnormal);
}



//##############################################################################
//# Kernels for MLPistons motion.
//##############################################################################
//------------------------------------------------------------------------------
/// Applies movement and velocity of piston 1D to a group of particles.
/// Aplica movimiento y velocidad de piston 1D a conjunto de particulas.
//------------------------------------------------------------------------------
template<byte periactive> __global__ void KerMovePiston1d(unsigned n,unsigned idini
  ,double dp,double poszmin,unsigned poszcount,const byte *pistonid,const double* movx,const double* velx
  ,const unsigned *ridpmv,double2 *posxy,double *posz,unsigned *dcell,float4 *velrhop,typecode *code)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle
  if(p<n){
    const unsigned id=p+idini;
    int pid=ridpmv[id];
    if(pid>=0){
      const unsigned pisid=pistonid[CODE_GetTypeValue(code[pid])];
      if(pisid<255){
        const double2 rpxy=posxy[pid];
        const double rpz=posz[pid];
        const unsigned cz=unsigned((rpz-poszmin)/dp);
        const double rmovx=(cz<poszcount? movx[pisid*poszcount+cz]: 0);
        const float rvelx=float(cz<poszcount? velx[pisid*poszcount+cz]: 0);
        //-Updates position.
        KerUpdatePos<periactive>(rpxy,rpz,rmovx,0,0,false,pid,posxy,posz,dcell,code);
        //-Updates velocity.
        velrhop[pid].x=rvelx;
      }
    }
  }
}

//==============================================================================
/// Applies movement and velocity of piston 1D to a group of particles.
/// Aplica movimiento y velocidad de piston 1D a conjunto de particulas.
//==============================================================================
void MovePiston1d(bool periactive,unsigned np,unsigned idini
  ,double dp,double poszmin,unsigned poszcount,const byte *pistonid,const double* movx,const double* velx
  ,const unsigned *ridpmv,double2 *posxy,double *posz,unsigned *dcell,float4 *velrhop,typecode *code)
{
  if(np){
    dim3 sgrid=GetSimpleGridSize(np,SPHBSIZE);
    if(periactive)KerMovePiston1d<true>  <<<sgrid,SPHBSIZE>>> (np,idini,dp,poszmin,poszcount,pistonid,movx,velx,ridpmv,posxy,posz,dcell,velrhop,code);
    else          KerMovePiston1d<false> <<<sgrid,SPHBSIZE>>> (np,idini,dp,poszmin,poszcount,pistonid,movx,velx,ridpmv,posxy,posz,dcell,velrhop,code);
  }
}

//------------------------------------------------------------------------------
/// Applies movement and velocity of piston 2D to a group of particles.
/// Aplica movimiento y velocidad de piston 2D a conjunto de particulas.
//------------------------------------------------------------------------------
template<byte periactive> __global__ void KerMovePiston2d(unsigned n,unsigned idini
  ,double dp,double posymin,double poszmin,unsigned poszcount,const double* movx,const double* velx
  ,const unsigned *ridpmv,double2 *posxy,double *posz,unsigned *dcell,float4 *velrhop,typecode *code)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle
  if(p<n){
    const unsigned id=p+idini;
    int pid=ridpmv[id];
    if(pid>=0){
      const double2 rpxy=posxy[pid];
      const double rpz=posz[pid];
      const unsigned cy=unsigned((rpxy.y-posymin)/dp);
      const unsigned cz=unsigned((rpz-poszmin)/dp);
      const double rmovx=(cz<poszcount? movx[cy*poszcount+cz]: 0);
      const float rvelx=float(cz<poszcount? velx[cy*poszcount+cz]: 0);
      //-Actualiza posicion.
      KerUpdatePos<periactive>(rpxy,rpz,rmovx,0,0,false,pid,posxy,posz,dcell,code);
      //-Actualiza velocidad.
      velrhop[pid].x=rvelx;
    }
  }
}

//==============================================================================
/// Applies movement and velocity of piston 2D to a group of particles.
/// Aplica movimiento y velocidad de piston 2D a conjunto de particulas.
//==============================================================================
void MovePiston2d(bool periactive,unsigned np,unsigned idini
  ,double dp,double posymin,double poszmin,unsigned poszcount,const double* movx,const double* velx
  ,const unsigned *ridpmv,double2 *posxy,double *posz,unsigned *dcell,float4 *velrhop,typecode *code)
{
  if(np){
    dim3 sgrid=GetSimpleGridSize(np,SPHBSIZE);
    if(periactive)KerMovePiston2d<true>  <<<sgrid,SPHBSIZE>>> (np,idini,dp,posymin,poszmin,poszcount,movx,velx,ridpmv,posxy,posz,dcell,velrhop,code);
    else          KerMovePiston2d<false> <<<sgrid,SPHBSIZE>>> (np,idini,dp,posymin,poszmin,poszcount,movx,velx,ridpmv,posxy,posz,dcell,velrhop,code);
  }
}


//##############################################################################
//# Kernels for Floating bodies.
//##############################################################################
//==============================================================================
/// Computes distance between floating and centre particles according to periodic conditions.
/// Calcula distancia entre pariculas floating y centro segun condiciones periodicas.
//==============================================================================
template<bool periactive> __device__ void KerFtPeriodicDist(double px,double py,double pz,double cenx,double ceny,double cenz,float radius,float &dx,float &dy,float &dz){
  if(periactive){
    double ddx=px-cenx;
    double ddy=py-ceny;
    double ddz=pz-cenz;
    const unsigned peri=CTE.periactive;
    if(PERI_AxisX(peri) && fabs(ddx)>radius){
      if(ddx>0){ ddx+=CTE.xperincx; ddy+=CTE.xperincy; ddz+=CTE.xperincz; }
      else{      ddx-=CTE.xperincx; ddy-=CTE.xperincy; ddz-=CTE.xperincz; }
    }
    if(PERI_AxisY(peri) && fabs(ddy)>radius){
      if(ddy>0){ ddx+=CTE.yperincx; ddy+=CTE.yperincy; ddz+=CTE.yperincz; }
      else{      ddx-=CTE.yperincx; ddy-=CTE.yperincy; ddz-=CTE.yperincz; }
    }
    if(PERI_AxisZ(peri) && fabs(ddz)>radius){
      if(ddz>0){ ddx+=CTE.zperincx; ddy+=CTE.zperincy; ddz+=CTE.zperincz; }
      else{      ddx-=CTE.zperincx; ddy-=CTE.zperincy; ddz-=CTE.zperincz; }
    }
    dx=float(ddx);
    dy=float(ddy);
    dz=float(ddz);
  }
  else{
    dx=float(px-cenx);
    dy=float(py-ceny);
    dz=float(pz-cenz);
  }
}

//------------------------------------------------------------------------------
/// Calculate summation: face, fomegaace in ftoforcessum[].
/// Calcula suma de face y fomegaace a partir de particulas floating en ftoforcessum[].
//------------------------------------------------------------------------------
template<bool periactive> __global__ void KerFtCalcForcesSum( //ftodatp={pini,np,radius,massp}
  const float4 *ftodatp,const double3 *ftocenter,const unsigned *ftridp
  ,const double2 *posxy,const double *posz,const float3 *ace
  ,float3 *ftoforcessum)
{
  extern __shared__ float rfacex[];
  float *rfacey=rfacex+blockDim.x;
  float *rfacez=rfacey+blockDim.x;
  float *rfomegaacex=rfacez+blockDim.x;
  float *rfomegaacey=rfomegaacex+blockDim.x;
  float *rfomegaacez=rfomegaacey+blockDim.x;

  const unsigned tid=threadIdx.x;  //-Thread number.
  const unsigned cf=blockIdx.x;    //-Floating number.
  
  //-Loads floating data.
  const float4 rfdata=ftodatp[cf];
  const unsigned fpini=(unsigned)__float_as_int(rfdata.x);
  const unsigned fnp=(unsigned)__float_as_int(rfdata.y);
  const float fradius=rfdata.z;
  const float fmassp=rfdata.w;
  const double3 rcenter=ftocenter[cf];

  //-Initialises shared memory to zero.
  const unsigned ntid=(fnp<blockDim.x? fnp: blockDim.x); //-Number of used threads. | Numero de threads utilizados.
  if(tid<ntid){
    rfacex[tid]=rfacey[tid]=rfacez[tid]=0;
    rfomegaacex[tid]=rfomegaacey[tid]=rfomegaacez[tid]=0;
  }

  //-Computes data in shared memory. | Calcula datos en memoria shared.
  const unsigned nfor=unsigned((fnp+blockDim.x-1)/blockDim.x);
  for(unsigned cfor=0;cfor<nfor;cfor++){
    unsigned p=cfor*blockDim.x+tid;
    if(p<fnp){
      const unsigned rp=ftridp[p+fpini];
      if(rp!=UINT_MAX){
        float3 force=ace[rp];
        force.x*=fmassp; force.y*=fmassp; force.z*=fmassp;
        rfacex[tid]+=force.x; rfacey[tid]+=force.y; rfacez[tid]+=force.z;
        //-Computes distance from the centre. | Calcula distancia al centro.
        double2 rposxy=posxy[rp];
        float dx,dy,dz;
        KerFtPeriodicDist<periactive>(rposxy.x,rposxy.y,posz[rp],rcenter.x,rcenter.y,rcenter.z,fradius,dx,dy,dz);
        //-Computes omegaace.
        rfomegaacex[tid]+=(force.z*dy - force.y*dz);
        rfomegaacey[tid]+=(force.x*dz - force.z*dx);
        rfomegaacez[tid]+=(force.y*dx - force.x*dy);
      }
    }
  }

  //-Reduces data in shared memory and stores results.
  //-Reduce datos de memoria shared y guarda resultados.
  __syncthreads();
  if(!tid){
    float3 face=make_float3(0,0,0);
    float3 fomegaace=make_float3(0,0,0);
    for(unsigned c=0;c<ntid;c++){
      face.x+=rfacex[c];  face.y+=rfacey[c];  face.z+=rfacez[c];
      fomegaace.x+=rfomegaacex[c]; fomegaace.y+=rfomegaacey[c]; fomegaace.z+=rfomegaacez[c];
    }
    //-Stores results in ftoforcessum[].
    unsigned cf2=cf*2;
    float3 aux=ftoforcessum[cf2];
    face.x+=aux.x; face.y+=aux.y; face.z+=aux.z;
    ftoforcessum[cf2]=face;
    cf2++;
    aux=ftoforcessum[cf2];
    fomegaace.x+=aux.x; fomegaace.y+=aux.y; fomegaace.z+=aux.z;
    ftoforcessum[cf2]=fomegaace;
  }
}

//==============================================================================
/// Calculate summation: face, fomegaace in ftoforcessum[].
/// Calcula suma de face y fomegaace a partir de particulas floating en ftoforcessum[].
//==============================================================================
void FtCalcForcesSum(bool periactive,unsigned ftcount
  ,const float4 *ftodatp,const double3 *ftocenter,const unsigned *ftridp
  ,const double2 *posxy,const double *posz,const float3 *ace
  ,float3 *ftoforcessum)
{
  if(ftcount){
    const unsigned bsize=256;
    const unsigned smem=sizeof(float)*(3+3)*bsize;
    dim3 sgrid=GetSimpleGridSize(ftcount*bsize,bsize);
    if(periactive)KerFtCalcForcesSum<true>  <<<sgrid,bsize,smem>>> (ftodatp,ftocenter,ftridp,posxy,posz,ace,ftoforcessum);
    else          KerFtCalcForcesSum<false> <<<sgrid,bsize,smem>>> (ftodatp,ftocenter,ftridp,posxy,posz,ace,ftoforcessum);
  }
}

//------------------------------------------------------------------------------
/// Carga valores de matriz 3x3 en bloques de 4, 4 y 1.
/// Loads values of matrix 3x3 in blocks of 4, 4 y 1.
//------------------------------------------------------------------------------
__device__ void KerLoadMatrix3f(unsigned c,const float4 *data8,const float *data1,tmatrix3f &v)
{
  float4 v4=data8[c*2];
  v.a11=v4.x; v.a12=v4.y; v.a13=v4.z; v.a21=v4.w;
  v4=data8[c*2+1];
  v.a22=v4.x; v.a23=v4.y; v.a31=v4.z; v.a32=v4.w;
  v.a33=data1[c];
}

//------------------------------------------------------------------------------
/// Computes final acceleration from particles and from external forces to ftoforces[].
/// Calcula aceleracion final a parti de particulas y de fuerzas externas en ftoforces[].
//------------------------------------------------------------------------------
__global__ void KerFtCalcForces(unsigned ftcount,float3 gravity
  ,const float *ftomass,const float3 *ftoangles
  ,const float4 *ftoinertiaini8,const float *ftoinertiaini1
  ,float3 *ftoforces) //fdata={pini,np,radius,mass}
{
  const unsigned cf=blockIdx.x*blockDim.x + threadIdx.x; //-Number of floating.
  if(cf<ftcount){
    //-Loads floating data.
    const float fmass=ftomass[cf];
    const float3 fang=ftoangles[cf];
    tmatrix3f inert;
    KerLoadMatrix3f(cf,ftoinertiaini8,ftoinertiaini1,inert);

    //-Compute a cumulative rotation matrix.
    const tmatrix3f frot=cumath::RotMatrix3x3(fang);
    //-Compute the inertia tensor by rotating the initial tensor to the curent orientation I=(R*I_0)*R^T.
    inert=cumath::MulMatrix3x3(cumath::MulMatrix3x3(frot,inert),cumath::TrasMatrix3x3(frot));
    //-Calculates the inverse of the inertia matrix to compute the I^-1 * L= W
    const tmatrix3f invinert=cumath::InverseMatrix3x3(inert);

    //-Loads traslational and rotational velocities.
    const unsigned cf2=cf*2;
    float3 face=ftoforces[cf2];
    float3 fomegaace=ftoforces[cf2+1];

    //-Calculate omega starting from fomegaace & invinert. | Calcula omega a partir de fomegaace y invinert.
    {
      float3 omegaace;
      omegaace.x=(fomegaace.x*invinert.a11+fomegaace.y*invinert.a12+fomegaace.z*invinert.a13);
      omegaace.y=(fomegaace.x*invinert.a21+fomegaace.y*invinert.a22+fomegaace.z*invinert.a23);
      omegaace.z=(fomegaace.x*invinert.a31+fomegaace.y*invinert.a32+fomegaace.z*invinert.a33);
      fomegaace=omegaace;
    }
    //-Add gravity force and divide by mass. | Suma fuerza de gravedad y divide por la masa.
    face.x=(face.x + fmass*gravity.x) / fmass;
    face.y=(face.y + fmass*gravity.y) / fmass;
    face.z=(face.z + fmass*gravity.z) / fmass;
    //-Stores final results.
    ftoforces[cf2]  =face; //-Saves acceleration (forces/fmass);
    ftoforces[cf2+1]=fomegaace;
  }
}

//==============================================================================
/// Computes final acceleration from particles and from external forces to ftoforces[].
/// Calcula aceleracion final a parti de particulas y de fuerzas externas en ftoforces[].
//==============================================================================
void FtCalcForces(unsigned ftcount,tfloat3 gravity
  ,const float *ftomass,const float3 *ftoangles
  ,const float4 *ftoinertiaini8,const float *ftoinertiaini1
  ,float3 *ftoforces)
{
  if(ftcount){
    dim3 sgrid=GetSimpleGridSize(ftcount,SPHBSIZE);
    KerFtCalcForces <<<sgrid,SPHBSIZE>>> (ftcount,Float3(gravity),ftomass
      ,ftoangles,ftoinertiaini8,ftoinertiaini1,ftoforces);
  }
}


//------------------------------------------------------------------------------
/// Calculate data to update floatings.
/// Calcula datos para actualizar floatings.
//------------------------------------------------------------------------------
__global__ void KerFtCalcForcesRes(unsigned ftcount,bool simulate2d,double dt
  ,const float3 *ftovelace,const double3 *ftocenter,const float3 *ftoforces
  ,float3 *ftoforcesres,double3 *ftocenterres)
{
  const unsigned cf=blockIdx.x*blockDim.x + threadIdx.x; //-Floating number.
  if(cf<ftcount){
    //-Compute fomega.
    float3 fomega=ftovelace[ftcount+cf];
    {
      const float3 omegaace=ftoforces[cf*2+1];
      fomega.x=float(dt*omegaace.x+fomega.x);
      fomega.y=float(dt*omegaace.y+fomega.y);
      fomega.z=float(dt*omegaace.z+fomega.z);
    }
    float3 fvel=ftovelace[cf];
    //-Zero components for 2-D simulation. | Anula componentes para 2D.
    float3 face=ftoforces[cf*2];
    if(simulate2d){ face.y=0; fomega.x=0; fomega.z=0; fvel.y=0; }
    //-Compute fcenter.
    double3 fcenter=ftocenter[cf];
    fcenter.x+=dt*fvel.x;
    fcenter.y+=dt*fvel.y;
    fcenter.z+=dt*fvel.z;
    //-Compute fvel.
    fvel.x=float(dt*face.x+fvel.x);
    fvel.y=float(dt*face.y+fvel.y);
    fvel.z=float(dt*face.z+fvel.z);
    //-Store data to update floating. | Guarda datos para actualizar floatings.
    ftoforcesres[cf*2]=fomega;
    ftoforcesres[cf*2+1]=fvel;
    ftocenterres[cf]=fcenter;
  }
}

//==============================================================================
/// Computes forces on floatings.
/// Calcula fuerzas sobre floatings.
//==============================================================================
void FtCalcForcesRes(unsigned ftcount,bool simulate2d,double dt
  ,const float3 *ftovelace,const double3 *ftocenter,const float3 *ftoforces
  ,float3 *ftoforcesres,double3 *ftocenterres)
{
  if(ftcount){
    dim3 sgrid=GetSimpleGridSize(ftcount,SPHBSIZE);
    KerFtCalcForcesRes <<<sgrid,SPHBSIZE>>> (ftcount,simulate2d,dt,ftovelace,ftocenter,ftoforces,ftoforcesres,ftocenterres);
  }
}


//------------------------------------------------------------------------------
/// Applies motion constraints.
/// Aplica restricciones de movimiento.
//------------------------------------------------------------------------------
__global__ void KerFtApplyConstraints(unsigned ftcount,const byte *ftoconstraints
  ,float3 *ftoforces,float3 *ftoforcesres)
{
  const unsigned cf=blockIdx.x*blockDim.x + threadIdx.x; //-Floating number.
  if(cf<ftcount){
    //-Applies motion constraints.
    const byte constr=ftoconstraints[cf];
    if(constr!=0){
      const unsigned cf2=cf*2;
      const unsigned cf21=cf2+1;
      float3 face=ftoforces[cf2];
      float3 fomegaace=ftoforces[cf21];
      float3 fomega=ftoforcesres[cf2];
      float3 fvel=ftoforcesres[cf21];
      //-Updates values.
      face.x=(constr&FTCON_MoveX? 0: face.x);
      face.y=(constr&FTCON_MoveY? 0: face.y);
      face.z=(constr&FTCON_MoveZ? 0: face.z);
      fomegaace.x=(constr&FTCON_RotateX? 0: fomegaace.x);
      fomegaace.y=(constr&FTCON_RotateY? 0: fomegaace.y);
      fomegaace.z=(constr&FTCON_RotateZ? 0: fomegaace.z);
      fvel.x=(constr&FTCON_MoveX? 0: fvel.x);
      fvel.y=(constr&FTCON_MoveY? 0: fvel.y);
      fvel.z=(constr&FTCON_MoveZ? 0: fvel.z);
      fomega.x=(constr&FTCON_RotateX? 0: fomega.x);
      fomega.y=(constr&FTCON_RotateY? 0: fomega.y);
      fomega.z=(constr&FTCON_RotateZ? 0: fomega.z);
      //-Stores updated values.
      ftoforces[cf2]=face;
      ftoforces[cf21]=fomegaace;
      ftoforcesres[cf2]=fomega;
      ftoforcesres[cf21]=fvel;
    }
  }
}

//==============================================================================
/// Applies motion constraints.
/// Aplica restricciones de movimiento.
//==============================================================================
void FtApplyConstraints(unsigned ftcount,const byte *ftoconstraints
  ,float3 *ftoforces,float3 *ftoforcesres)
{
  if(ftcount){
    dim3 sgrid=GetSimpleGridSize(ftcount,SPHBSIZE);
    KerFtApplyConstraints <<<sgrid,SPHBSIZE>>> (ftcount,ftoconstraints,ftoforces,ftoforcesres);
  }
}


//------------------------------------------------------------------------------
/// Updates information and particles of floating bodies.
//------------------------------------------------------------------------------
template<bool periactive> __global__ void KerFtUpdate(bool predictor,double dt //ftodata={pini,np,radius,massp}
  ,unsigned nft,const float4 *ftodatp,const float3 *ftoforcesres
  ,double3 *ftocenterres,const unsigned *ftridp
  ,double3 *ftocenter,float3 *ftoangles,float3 *ftovelace
  ,double2 *posxy,double *posz,unsigned *dcell,float4 *velrhop,typecode *code)
{
  const unsigned tid=threadIdx.x;  //-Thread number.
  const unsigned cf=blockIdx.x;    //-Floating number.
  //-Obtains floating data.
  const float3 fomega=ftoforcesres[cf*2];
  const float3 fvel=ftoforcesres[cf*2+1];
  const double3 fcenter=ftocenterres[cf];
  float4 rfdata=ftodatp[cf];
  const unsigned fpini=(unsigned)__float_as_int(rfdata.x);
  const unsigned fnp=(unsigned)__float_as_int(rfdata.y);
  const float fradius=rfdata.z;
  //-Updates floating particles.
  const unsigned nfor=unsigned((fnp+blockDim.x-1)/blockDim.x);
  for(unsigned cfor=0;cfor<nfor;cfor++){
    unsigned fp=cfor*blockDim.x+tid;
    if(fp<fnp){
      const unsigned p=ftridp[fp+fpini];
      if(p!=UINT_MAX){
        double2 rposxy=posxy[p];
        double rposz=posz[p];
        float4 rvel=velrhop[p];
        //-Computes and stores position displacement.
        const double dx=dt*double(rvel.x);
        const double dy=dt*double(rvel.y);
        const double dz=dt*double(rvel.z);
        KerUpdatePos<periactive>(rposxy,rposz,dx,dy,dz,false,p,posxy,posz,dcell,code);
        //-Computes and stores new velocity.
        float disx,disy,disz;
        KerFtPeriodicDist<periactive>(rposxy.x+dx,rposxy.y+dy,rposz+dz,fcenter.x,fcenter.y,fcenter.z,fradius,disx,disy,disz);
        rvel.x=fvel.x+(fomega.y*disz-fomega.z*disy);
        rvel.y=fvel.y+(fomega.z*disx-fomega.x*disz);
        rvel.z=fvel.z+(fomega.x*disy-fomega.y*disx);
        velrhop[p]=rvel;
      }
    }
  }

  //-Stores floating data.
  __syncthreads();
  if(!tid && !predictor){
    ftocenter[cf]=(periactive? KerUpdatePeriodicPos(fcenter): fcenter);
    float3 rangles=ftoangles[cf];
    rangles.x=float(double(rangles.x)+double(fomega.x)*dt);
    rangles.y=float(double(rangles.y)+double(fomega.y)*dt);
    rangles.z=float(double(rangles.z)+double(fomega.z)*dt);
    ftoangles[cf]=rangles;
    //-Linear velocity and acceleration.
    float3 v=ftovelace[cf];
    v.x=(fvel.x-v.x)/float(dt);
    v.y=(fvel.y-v.y)/float(dt);
    v.z=(fvel.z-v.z)/float(dt);
    ftovelace[cf]=fvel;
    ftovelace[nft+nft+cf]=v;
    //-Angular velocity and acceleration.
    v=ftovelace[nft+cf];
    v.x=(fomega.x-v.x)/float(dt);
    v.y=(fomega.y-v.y)/float(dt);
    v.z=(fomega.z-v.z)/float(dt);
    ftovelace[nft+cf]=fomega;
    ftovelace[nft*3+cf]=v;
  }
}

//==============================================================================
/// Updates information and particles of floating bodies.
//==============================================================================
void FtUpdate(bool periactive,bool predictor,unsigned ftcount,double dt
  ,const float4 *ftodatp,const float3 *ftoforcesres,double3 *ftocenterres,const unsigned *ftridp
  ,double3 *ftocenter,float3 *ftoangles,float3 *ftovelace
  ,double2 *posxy,double *posz,unsigned *dcell,float4 *velrhop,typecode *code)
{
  if(ftcount){
    const unsigned bsize=128; 
    dim3 sgrid=GetSimpleGridSize(ftcount*bsize,bsize);
    if(periactive)KerFtUpdate<true>  <<<sgrid,bsize>>> (predictor,dt,ftcount,ftodatp,ftoforcesres,ftocenterres,ftridp,ftocenter,ftoangles,ftovelace,posxy,posz,dcell,velrhop,code);
    else          KerFtUpdate<false> <<<sgrid,bsize>>> (predictor,dt,ftcount,ftodatp,ftoforcesres,ftocenterres,ftridp,ftocenter,ftoangles,ftovelace,posxy,posz,dcell,velrhop,code);
  }
}


//<vs_ftmottionsv_ini>
//------------------------------------------------------------------------------
/// Get reference position of floating bodies.
//------------------------------------------------------------------------------
__global__ void KerFtGetPosRef(unsigned np,const unsigned *idpref
  ,const unsigned *ftridp,const double2 *posxy,const double *posz,double *posref)
{
  unsigned cp=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle
  if(cp<np){
    bool ok=false;
    const unsigned cid=idpref[cp];
    if(cid!=UINT_MAX){
      const unsigned p=ftridp[cid];
      if(p!=UINT_MAX){
        const double2 rxy=posxy[p];
        const unsigned c=cp*3;
        posref[c  ]=rxy.x;
        posref[c+1]=rxy.y;
        posref[c+2]=posz[p];
        ok=true;
      }
    }
    if(!ok)posref[cp*3]=DBL_MAX;
  }
}
//==============================================================================
/// Get reference position of floating bodies.
//==============================================================================
void FtGetPosRef(unsigned np,const unsigned *idpref,const unsigned *ftridp
  ,const double2 *posxy,const double *posz,double *posref)
{
  if(np){
    const unsigned bsize=128; 
    dim3 sgrid=GetSimpleGridSize(np,bsize);
    KerFtGetPosRef <<<sgrid,bsize>>> (np,idpref,ftridp,posxy,posz,posref);
  }
}
//<vs_ftmottionsv_end>



//##############################################################################
//# Kernels for Periodic conditions
//# Kernels para Periodic conditions
//##############################################################################
//------------------------------------------------------------------------------
/// Marks current periodics to be ignored.
/// Marca las periodicas actuales como ignorar.
//------------------------------------------------------------------------------
__global__ void KerPeriodicIgnore(unsigned n,typecode *code)
{
  const unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    //-Checks code of particles.
    //-Comprueba codigo de particula.
    const typecode rcode=code[p];
    if(CODE_IsPeriodic(rcode))code[p]=CODE_SetOutIgnore(rcode);
  }
}

//==============================================================================
/// Marks current periodics to be ignored.
/// Marca las periodicas actuales como ignorar.
//==============================================================================
void PeriodicIgnore(unsigned n,typecode *code){
  if(n){
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    KerPeriodicIgnore <<<sgrid,SPHBSIZE>>> (n,code);
  }
}

//------------------------------------------------------------------------------
/// Create list of new periodic particles to be duplicated and 
/// marks old periodics to be ignored.
///
/// Crea lista de nuevas particulas periodicas a duplicar y con delper activado
/// marca las periodicas viejas para ignorar.
//------------------------------------------------------------------------------
__global__ void KerPeriodicMakeList(unsigned n,unsigned pini,unsigned nmax
  ,double3 mapposmin,double3 mapposmax,double3 perinc
  ,const double2 *posxy,const double *posz,const typecode *code,unsigned *listp)
{
  extern __shared__ unsigned slist[];
  if(!threadIdx.x)slist[0]=0;
  __syncthreads();
  const unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    const unsigned p2=p+pini;
    //-Inteacts with normal or periodic particles.
    //-Se queda con particulas normales o periodicas.
    if(CODE_GetSpecialValue(code[p2])<=CODE_PERIODIC){
      //-Obtains particle position.
      const double2 rxy=posxy[p2];
      const double rx=rxy.x,ry=rxy.y;
      const double rz=posz[p2];
      double rx2=rx+perinc.x,ry2=ry+perinc.y,rz2=rz+perinc.z;
      if(mapposmin.x<=rx2 && mapposmin.y<=ry2 && mapposmin.z<=rz2 && rx2<mapposmax.x && ry2<mapposmax.y && rz2<mapposmax.z){
        unsigned cp=atomicAdd(slist,1);  slist[cp+1]=p2;
      }
      rx2=rx-perinc.x; ry2=ry-perinc.y; rz2=rz-perinc.z;
      if(mapposmin.x<=rx2 && mapposmin.y<=ry2 && mapposmin.z<=rz2 && rx2<mapposmax.x && ry2<mapposmax.y && rz2<mapposmax.z){
        unsigned cp=atomicAdd(slist,1);  slist[cp+1]=(p2|0x80000000);
      }
    }
  }
  __syncthreads();
  const unsigned ns=slist[0];
  __syncthreads();
  if(!threadIdx.x && ns)slist[0]=atomicAdd((listp+nmax),ns);
  __syncthreads();
  if(threadIdx.x<ns){
    unsigned cp=slist[0]+threadIdx.x;
    if(cp<nmax)listp[cp]=slist[threadIdx.x+1];
  }
  if(blockDim.x+threadIdx.x<ns){ //-There may be twice as many periodics per thread. | Puede haber el doble de periodicas que threads.
    unsigned cp=blockDim.x+slist[0]+threadIdx.x;
    if(cp<nmax)listp[cp]=slist[blockDim.x+threadIdx.x+1];
  }
}

//==============================================================================
/// Create list of new periodic particles to be duplicated.
/// With stable activated reorders perioc list.
///
/// Crea lista de nuevas particulas periodicas a duplicar.
/// Con stable activado reordena lista de periodicas.
//==============================================================================
unsigned PeriodicMakeList(unsigned n,unsigned pini,bool stable,unsigned nmax
  ,tdouble3 mapposmin,tdouble3 mapposmax,tdouble3 perinc
  ,const double2 *posxy,const double *posz,const typecode *code,unsigned *listp)
{
  unsigned count=0;
  if(n){
    //-lspg size list initialized to zero.
    //-Inicializa tamanho de lista lspg a cero.
    cudaMemset(listp+nmax,0,sizeof(unsigned));
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    const unsigned smem=(SPHBSIZE*2+1)*sizeof(unsigned); //-Each particle can leave two new periodic over the counter position. | De cada particula pueden salir 2 nuevas periodicas mas la posicion del contador.
    KerPeriodicMakeList <<<sgrid,SPHBSIZE,smem>>> (n,pini,nmax,Double3(mapposmin),Double3(mapposmax),Double3(perinc),posxy,posz,code,listp);
    cudaMemcpy(&count,listp+nmax,sizeof(unsigned),cudaMemcpyDeviceToHost);
    //-Reorders list if it is valid and stable has been activated.
    //-Reordena lista si es valida y stable esta activado.
    if(stable && count && count<=nmax){
      thrust::device_ptr<unsigned> dev_list(listp);
      thrust::sort(dev_list,dev_list+count);
    }
  }
  return(count);
}

//------------------------------------------------------------------------------
/// Doubles the position of the indicated particle using a displacement.
/// Duplicate particles are considered valid and are always within
/// the domain.
/// This kernel applies to single-GPU and multi-GPU because the calculations are made
/// from domposmin.
/// It controls the cell coordinates not exceed the maximum.
///
/// Duplica la posicion de la particula indicada aplicandole un desplazamiento.
/// Las particulas duplicadas se considera que siempre son validas y estan dentro
/// del dominio.
/// Este kernel vale para single-gpu y multi-gpu porque los calculos se hacen 
/// a partir de domposmin.
/// Se controla que las coordendas de celda no sobrepasen el maximo.
//------------------------------------------------------------------------------
__device__ void KerPeriodicDuplicatePos(unsigned pnew,unsigned pcopy
  ,bool inverse,double dx,double dy,double dz,uint3 cellmax
  ,double2 *posxy,double *posz,unsigned *dcell)
{
  //-Obtains position of the particle to be duplicated.
  //-Obtiene pos de particula a duplicar.
  double2 rxy=posxy[pcopy];
  double rz=posz[pcopy];
  //-Applies displacement.
  rxy.x+=(inverse? -dx: dx);
  rxy.y+=(inverse? -dy: dy);
  rz+=(inverse? -dz: dz);
  //-Computes cell coordinates within the domain.
  //-Calcula coordendas de celda dentro de dominio.
  unsigned cx=unsigned((rxy.x-CTE.domposminx)/CTE.scell);
  unsigned cy=unsigned((rxy.y-CTE.domposminy)/CTE.scell);
  unsigned cz=unsigned((rz-CTE.domposminz)/CTE.scell);
  //-Adjust cell coordinates if they exceed the maximum.
  //-Ajusta las coordendas de celda si sobrepasan el maximo.
  cx=(cx<=cellmax.x? cx: cellmax.x);
  cy=(cy<=cellmax.y? cy: cellmax.y);
  cz=(cz<=cellmax.z? cz: cellmax.z);
  //-Stores position and cell of the new particles.
  //-Graba posicion y celda de nuevas particulas.
  posxy[pnew]=rxy;
  posz[pnew]=rz;
  dcell[pnew]=DCEL_Cell(CTE.cellcode,cx,cy,cz);
}

//------------------------------------------------------------------------------
/// Creates periodic particles from a list of particles to duplicate.
/// It is assumed that all particles are valid.
/// This kernel applies to single-GPU and multi-GPU because it uses domposmin.
///
/// Crea particulas periodicas a partir de una lista con las particulas a duplicar.
/// Se presupone que todas las particulas son validas.
/// Este kernel vale para single-gpu y multi-gpu porque usa domposmin. 
//------------------------------------------------------------------------------
__global__ void KerPeriodicDuplicateVerlet(unsigned n,unsigned pini,uint3 cellmax,double3 perinc
  ,const unsigned *listp,unsigned *idp,typecode *code,unsigned *dcell
  ,double2 *posxy,double *posz,float4 *velrhop,tsymatrix3f *spstau,float4 *velrhopm1,tsymatrix3f *sigma,tsymatrix3f *sigmam1
  ,float *porepress,float *porepress0,float *porepressrate,float *porepressm1)
{
  const unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    const unsigned pnew=p+pini;
    const unsigned rp=listp[p];
    const unsigned pcopy=(rp&0x7FFFFFFF);
    //-Adjusts cell position of the new particles.
    //-Ajusta posicion y celda de nueva particula.
    KerPeriodicDuplicatePos(pnew,pcopy,(rp>=0x80000000),perinc.x,perinc.y,perinc.z,cellmax,posxy,posz,dcell);
    //-Copies the remaining data.
    //-Copia el resto de datos.
    idp[pnew]=idp[pcopy];
    code[pnew]=CODE_SetPeriodic(code[pcopy]);
    velrhop[pnew]=velrhop[pcopy];
    velrhopm1[pnew]=velrhopm1[pcopy];
    sigma[pnew]=sigma[pcopy];
    sigmam1[pnew]=sigmam1[pcopy];
    if(porepress)porepress[pnew]=porepress[pcopy];
    if(porepress0)porepress0[pnew]=porepress0[pcopy];
    if(porepressrate)porepressrate[pnew]=porepressrate[pcopy];
    if(porepressm1)porepressm1[pnew]=porepressm1[pcopy];
    if(spstau)spstau[pnew]=spstau[pcopy];
  }
}

//==============================================================================
/// Creates periodic particles from a list of particles to duplicate.
/// Crea particulas periodicas a partir de una lista con las particulas a duplicar.
//==============================================================================
void PeriodicDuplicateVerlet(unsigned n,unsigned pini,tuint3 domcells,tdouble3 perinc
  ,const unsigned *listp,unsigned *idp,typecode *code,unsigned *dcell
  ,double2 *posxy,double *posz,float4 *velrhop,tsymatrix3f *spstau,float4 *velrhopm1
  ,tsymatrix3f *sigma,tsymatrix3f *sigmam1,float *porepress,float *porepress0,float *porepressrate,float *porepressm1)
{
  if(n){
    uint3 cellmax=make_uint3(domcells.x-1,domcells.y-1,domcells.z-1);
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    KerPeriodicDuplicateVerlet <<<sgrid,SPHBSIZE>>> (n,pini,cellmax,Double3(perinc),listp,idp,code,dcell,posxy,posz,velrhop,spstau,velrhopm1,sigma,sigmam1,porepress,porepress0,porepressrate,porepressm1);
  }
}

//------------------------------------------------------------------------------
/// Creates periodic particles from a list of particles to duplicate.
/// It is assumed that all particles are valid.
/// This kernel applies to single-GPU and multi-GPU because it uses domposmin.
///
/// Crea particulas periodicas a partir de una lista con las particulas a duplicar.
/// Se presupone que todas las particulas son validas.
/// Este kernel vale para single-gpu y multi-gpu porque usa domposmin. 
//------------------------------------------------------------------------------
template<bool varspre> __global__ void KerPeriodicDuplicateSymplectic(unsigned n,unsigned pini
  ,uint3 cellmax,double3 perinc,const unsigned *listp,unsigned *idp,typecode *code,unsigned *dcell
  ,double2 *posxy,double *posz,float4 *velrhop,tsymatrix3f *spstau,double2 *posxypre,double *poszpre,float4 *velrhoppre
  ,tsymatrix3f *sigma, tsymatrix3f *sigmapre,float *porepress,float *porepress0,float *porepressrate,float *porepresspre)
{
  const unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    const unsigned pnew=p+pini;
    const unsigned rp=listp[p];
    const unsigned pcopy=(rp&0x7FFFFFFF);
    //-Adjusts cell position of the new particles.
    //-Ajusta posicion y celda de nueva particula.
    KerPeriodicDuplicatePos(pnew,pcopy,(rp>=0x80000000),perinc.x,perinc.y,perinc.z,cellmax,posxy,posz,dcell);
    //-Copies the remaining data.
    //-Copia el resto de datos.
    idp[pnew]=idp[pcopy];
    code[pnew]=CODE_SetPeriodic(code[pcopy]);
    velrhop[pnew]=velrhop[pcopy];
    sigma[pnew]=sigma[pcopy];//mdbr
    if(porepress)porepress[pnew]=porepress[pcopy];
    if(porepress0)porepress0[pnew]=porepress0[pcopy];
    if(porepressrate)porepressrate[pnew]=porepressrate[pcopy];
    if(varspre){
      posxypre[pnew]=posxypre[pcopy];
      poszpre[pnew]=poszpre[pcopy];
      velrhoppre[pnew]=velrhoppre[pcopy];
      sigmapre[pnew]=sigmapre[pcopy];//mdbr
      if(porepresspre)porepresspre[pnew]=porepresspre[pcopy];
    }
    if(spstau)spstau[pnew]=spstau[pcopy];
  }
}

//==============================================================================
/// Creates periodic particles from a list of particles to duplicate.
/// Crea particulas periodicas a partir de una lista con las particulas a duplicar.
//==============================================================================
void PeriodicDuplicateSymplectic(unsigned n,unsigned pini
  ,tuint3 domcells,tdouble3 perinc,const unsigned *listp,unsigned *idp,typecode *code,unsigned *dcell
  ,double2 *posxy,double *posz,float4 *velrhop,tsymatrix3f *spstau,double2 *posxypre,double *poszpre,float4 *velrhoppre
  ,tsymatrix3f *sigma, tsymatrix3f *sigmapre,float *porepress,float *porepress0,float *porepressrate,float *porepresspre)
{
  if(n){
    uint3 cellmax=make_uint3(domcells.x-1,domcells.y-1,domcells.z-1);
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    if(posxypre!=NULL)KerPeriodicDuplicateSymplectic<true>  <<<sgrid,SPHBSIZE>>> (n,pini,cellmax,Double3(perinc),listp,idp,code,dcell,posxy,posz,velrhop,spstau,posxypre,poszpre,velrhoppre,sigma,sigmapre,porepress,porepress0,porepressrate,porepresspre);
    else              KerPeriodicDuplicateSymplectic<false> <<<sgrid,SPHBSIZE>>> (n,pini,cellmax,Double3(perinc),listp,idp,code,dcell,posxy,posz,velrhop,spstau,posxypre,poszpre,velrhoppre,sigma,sigmapre,porepress,porepress0,porepressrate,porepresspre);
  }
}

//------------------------------------------------------------------------------
/// Creates periodic particles from a list of particles to duplicate.
/// It is assumed that all particles are valid.
/// This kernel applies to single-GPU and multi-GPU because it uses domposmin.
///
/// Crea particulas periodicas a partir de una lista con las particulas a duplicar.
/// Se presupone que todas las particulas son validas.
/// Este kernel vale para single-gpu y multi-gpu porque usa domposmin. 
//------------------------------------------------------------------------------
__global__ void KerPeriodicDuplicateNormals(unsigned n,unsigned pini,const unsigned *listp,float3 *normals,float3 *motionvel)
{
  const unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    const unsigned pnew=p+pini;
    const unsigned rp=listp[p];
    const unsigned pcopy=(rp&0x7FFFFFFF);
    normals[pnew]=normals[pcopy];
    if(motionvel)motionvel[pnew]=motionvel[pcopy];
  }
}

//==============================================================================
/// Creates periodic particles from a list of particles to duplicate.
/// Crea particulas periodicas a partir de una lista con las particulas a duplicar.
//==============================================================================
void PeriodicDuplicateNormals(unsigned n,unsigned pini,const unsigned *listp,float3 *normals,float3 *motionvel)
{
  if(n){
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    KerPeriodicDuplicateNormals <<<sgrid,SPHBSIZE>>> (n,pini,listp,normals,motionvel);
  }
}

//##############################################################################
//# Kernels for Damping.
//##############################################################################
//------------------------------------------------------------------------------
/// Returns TRUE when code==NULL or particle is normal and fluid.
//------------------------------------------------------------------------------
__device__ bool KerIsNormalFluid(const typecode *code,unsigned p){
  if(code){//-Descarta particulas floating o periodicas.
    const typecode cod=code[p];
    return(CODE_IsNormal(cod) && CODE_IsFluid(cod));
  }
  return(true);
}
//------------------------------------------------------------------------------
/// Checks position is inside box limits.
/// Comprueba si la posicion esta dentro de los limites.
//------------------------------------------------------------------------------
__device__ bool KerPointInBox(double px,double py,double pz,const double3 &p1,const double3 &p2)
{
  return(p1.x<=px && p1.y<=py && p1.z<=pz && px<=p2.x && py<=p2.y && pz<=p2.z);
}
//------------------------------------------------------------------------------
/// Solves point on the plane.
/// Resuelve punto en el plano.
//------------------------------------------------------------------------------
__device__ double KerPointPlane(const double4 &pla,double px,double py,double pz)
{
  return(pla.x*px+pla.y*py+pla.z*pz+pla.w);
}
//------------------------------------------------------------------------------
/// Solves point on the plane.
/// Resuelve punto en el plano.
//------------------------------------------------------------------------------
__device__ double KerPointPlane(const double4 &pla,const double3 &pt)
{
  return(pla.x*pt.x+pla.y*pt.y+pla.z*pt.z+pla.w);
}

//------------------------------------------------------------------------------
/// Applies Damping.
/// Aplica Damping.
//------------------------------------------------------------------------------
__global__ void KerComputeDampingPlane(unsigned n,unsigned pini
  ,double dt,double4 plane,float dist,float over,float3 factorxyz,float redumax
  ,const double2 *posxy,const double *posz,const typecode *code
  ,float4 *velrhop)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    const unsigned p1=p+pini;
    const bool ok=KerIsNormalFluid(code,p1);//-Ignore floating and periodic particles. | Descarta particulas floating o periodicas.
    if(ok){
      const double2 rposxy=posxy[p1];
      const double rposz=posz[p1];
      double vdis=KerPointPlane(plane,rposxy.x,rposxy.y,rposz);  //fgeo::PlanePoint(plane,ps);
      if(0<vdis && vdis<=dist+over){
        const double fdis=(vdis>=dist? 1.: vdis/dist);
        const double redudt=dt*(fdis*fdis)*redumax;
        double redudtx=(1.-redudt*factorxyz.x);
        double redudty=(1.-redudt*factorxyz.y);
        double redudtz=(1.-redudt*factorxyz.z);
        redudtx=(redudtx<0? 0.: redudtx);
        redudty=(redudty<0? 0.: redudty);
        redudtz=(redudtz<0? 0.: redudtz);
        float4 rvel=velrhop[p1];
        rvel.x=float(redudtx*rvel.x); 
        rvel.y=float(redudty*rvel.y); 
        rvel.z=float(redudtz*rvel.z);
        velrhop[p1]=rvel;
      }
    }
  }
}
//==============================================================================
/// Applies Damping.
/// Aplica Damping.
//==============================================================================
void ComputeDampingPlane(double dt,double4 plane,float dist,float over
  ,float3 factorxyz,float redumax,unsigned n,unsigned pini
  ,const double2 *posxy,const double *posz,const typecode *code,float4 *velrhop)
{
  if(n){
    dim3 sgridf=GetSimpleGridSize(n,SPHBSIZE);
    KerComputeDampingPlane <<<sgridf,SPHBSIZE>>> (n,pini,dt,plane,dist,over
      ,factorxyz,redumax,posxy,posz,code,velrhop);
  }
}

//------------------------------------------------------------------------------
/// Applies Damping to limited domain.
/// Aplica Damping limitado a un dominio.
//------------------------------------------------------------------------------
__global__ void KerComputeDampingPlaneDom(unsigned n,unsigned pini
  ,double dt,double4 plane,float dist,float over,float3 factorxyz,float redumax
  ,double zmin,double zmax,double4 pla0,double4 pla1,double4 pla2,double4 pla3
  ,const double2 *posxy,const double *posz,const typecode *code
  ,float4 *velrhop)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    const unsigned p1=p+pini;
    const bool ok=KerIsNormalFluid(code,p1);//-Ignore floating and periodic particles. | Descarta particulas floating o periodicas.
    if(ok){
      const double2 rposxy=posxy[p1];
      const double rposz=posz[p1];
      const double3 ps=make_double3(rposxy.x,rposxy.y,rposz);
      double vdis=KerPointPlane(plane,ps);  //fgeo::PlanePoint(plane,ps);
      if(0<vdis && vdis<=dist+over){
        if(ps.z>=zmin && ps.z<=zmax && KerPointPlane(pla0,ps)<=0 && KerPointPlane(pla1,ps)<=0 && KerPointPlane(pla2,ps)<=0 && KerPointPlane(pla3,ps)<=0){
          const double fdis=(vdis>=dist? 1.: vdis/dist);
          const double redudt=dt*(fdis*fdis)*redumax;
          double redudtx=(1.-redudt*factorxyz.x);
          double redudty=(1.-redudt*factorxyz.y);
          double redudtz=(1.-redudt*factorxyz.z);
          redudtx=(redudtx<0? 0.: redudtx);
          redudty=(redudty<0? 0.: redudty);
          redudtz=(redudtz<0? 0.: redudtz);
          float4 rvel=velrhop[p1];
          rvel.x=float(redudtx*rvel.x); 
          rvel.y=float(redudty*rvel.y); 
          rvel.z=float(redudtz*rvel.z); 
          velrhop[p1]=rvel;
        }
      }
    }
  }
}
//==============================================================================
/// Applies Damping to limited domain.
/// Aplica Damping limitado a un dominio.
//==============================================================================
void ComputeDampingPlaneDom(double dt,double4 plane,float dist,float over
  ,float3 factorxyz,float redumax
  ,double zmin,double zmax,double4 pla0,double4 pla1,double4 pla2,double4 pla3
  ,unsigned n,unsigned pini,const double2 *posxy,const double *posz,const typecode *code
  ,float4 *velrhop)
{
  if(n){
    dim3 sgridf=GetSimpleGridSize(n,SPHBSIZE);
    KerComputeDampingPlaneDom <<<sgridf,SPHBSIZE>>> (n,pini,dt,plane,dist,over,factorxyz
      ,redumax,zmin,zmax,pla0,pla1,pla2,pla3,posxy,posz,code,velrhop);
  }
}


//------------------------------------------------------------------------------
/// Applies Damping according box configuration.
/// Aplica Damping segun cofiguracion de caja.
//------------------------------------------------------------------------------
__global__ void KerComputeDampingBox(unsigned n,unsigned pini
  ,double dt,float3 factorxyz,float redumax
  ,double3 limitmin1,double3 limitmin2,double3 limitmax1,double3 limitmax2
  ,double3 limitover1,double3 limitover2,double3 boxsize1,double3 boxsize2
  ,const double2 *posxy,const double *posz,const typecode *code
  ,float4 *velrhop)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    const unsigned p1=p+pini;
    const bool ok=KerIsNormalFluid(code,p1);//-Ignore floating and periodic particles. | Descarta particulas floating o periodicas.
    if(ok){
      const double2 rposxy=posxy[p1];
      const double rposz=posz[p1];
      //-Check if it is within the domain. | Comprueba si esta dentro del dominio.
      if(KerPointInBox(rposxy.x,rposxy.y,rposz,limitover1,limitover2)){//-Inside overlimit domain.
        if(!KerPointInBox(rposxy.x,rposxy.y,rposz,limitmin1,limitmin2)){//-Outside free domain.
          double fdis=1.;
          if(KerPointInBox(rposxy.x,rposxy.y,rposz,limitmax1,limitmax2)){//-Compute damping coefficient.
            fdis=0;
            if(boxsize2.z){ const double fdiss=(rposz   -limitmin2.z)/boxsize2.z; fdis=(fdis>=fdiss? fdis: fdiss); }
            if(boxsize2.y){ const double fdiss=(rposxy.y-limitmin2.y)/boxsize2.y; fdis=(fdis>=fdiss? fdis: fdiss); }
            if(boxsize2.x){ const double fdiss=(rposxy.x-limitmin2.x)/boxsize2.x; fdis=(fdis>=fdiss? fdis: fdiss); }
            if(boxsize1.z){ const double fdiss=(limitmin1.z-rposz   )/boxsize1.z; fdis=(fdis>=fdiss? fdis: fdiss); }
            if(boxsize1.y){ const double fdiss=(limitmin1.y-rposxy.y)/boxsize1.y; fdis=(fdis>=fdiss? fdis: fdiss); }
            if(boxsize1.x){ const double fdiss=(limitmin1.x-rposxy.x)/boxsize1.x; fdis=(fdis>=fdiss? fdis: fdiss); }
          }
          const double redudt=dt*(fdis*fdis)*redumax;
          double redudtx=(1.-redudt*factorxyz.x);
          double redudty=(1.-redudt*factorxyz.y);
          double redudtz=(1.-redudt*factorxyz.z);
          redudtx=(redudtx<0? 0.: redudtx);
          redudty=(redudty<0? 0.: redudty);
          redudtz=(redudtz<0? 0.: redudtz);
          float4 rvel=velrhop[p1];
          rvel.x=float(redudtx*rvel.x); 
          rvel.y=float(redudty*rvel.y); 
          rvel.z=float(redudtz*rvel.z);
          //rvel.x=rvel.y=rvel.z=0;
          velrhop[p1]=rvel;
        }
      }
    }
  }
}
//==============================================================================
/// Applies Damping according box configuration.
/// Aplica Damping segun cofiguracion de caja.
//==============================================================================
void ComputeDampingBox(unsigned n,unsigned pini,double dt,float3 factorxyz,float redumax
  ,double3 limitmin1,double3 limitmin2,double3 limitmax1,double3 limitmax2
  ,double3 limitover1,double3 limitover2,double3 boxsize1,double3 boxsize2
  ,const double2 *posxy,const double *posz,const typecode *code,float4 *velrhop)
{
  if(n){
    dim3 sgridf=GetSimpleGridSize(n,SPHBSIZE);
    KerComputeDampingBox <<<sgridf,SPHBSIZE>>> (n,pini,dt,factorxyz,redumax
      ,limitmin1,limitmin2,limitmax1,limitmax2,limitover1,limitover2,boxsize1,boxsize2
      ,posxy,posz,code,velrhop);
  }
}


//------------------------------------------------------------------------------
/// Applies Damping to limited cylinder domain.
/// Aplica Damping limitado a un dominio de cilindro.
//------------------------------------------------------------------------------
__global__ void KerComputeDampingCylinder(unsigned n,unsigned pini
  ,double dt,bool isvertical,double3 point1,double3 point2,double limitmin
  ,float dist,float over,float3 factorxyz,float redumax
  ,const double2 *posxy,const double *posz,const typecode *code
  ,float4 *velrhop)
{
  unsigned p=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p<n){
    const unsigned p1=p+pini;
    const bool ok=KerIsNormalFluid(code,p1);//-Ignore floating and periodic particles. | Descarta particulas floating o periodicas.
    if(ok){
      //-Check if it is within the domain. | Comprueba si esta dentro del dominio.
      const double2 rposxy=posxy[p1];
      const double rposz=posz[p1];
      const double3 ps=make_double3(rposxy.x,rposxy.y,rposz);
      const double vdis=(isvertical? 
        sqrt((ps.x-point1.x)*(ps.x-point1.x)+(ps.y-point1.y)*(ps.y-point1.y)): 
        cugeo::LinePointDist(ps,point1,point2)
        ) - limitmin;
      if(0<vdis && vdis<=dist+over){
        const double fdis=(vdis>=dist? 1.: vdis/dist);
        const double redudt=dt*(fdis*fdis)*redumax;
        double redudtx=(1.-redudt*factorxyz.x);
        double redudty=(1.-redudt*factorxyz.y);
        double redudtz=(1.-redudt*factorxyz.z);
        redudtx=(redudtx<0? 0.: redudtx);
        redudty=(redudty<0? 0.: redudty);
        redudtz=(redudtz<0? 0.: redudtz);
        float4 rvel=velrhop[p1];
        rvel.x=float(redudtx*rvel.x); 
        rvel.y=float(redudty*rvel.y); 
        rvel.z=float(redudtz*rvel.z); 
        velrhop[p1]=rvel;
      }
    }
  }
}
//==============================================================================
/// Applies Damping to limited cylinder domain.
/// Aplica Damping limitado a un dominio de cilindro.
//==============================================================================
void ComputeDampingCylinder(unsigned n,unsigned pini
  ,double dt,double3 point1,double3 point2,double limitmin
  ,float dist,float over,float3 factorxyz,float redumax
  ,const double2 *posxy,const double *posz,const typecode *code
  ,float4 *velrhop)
{
  if(n){
    const bool isvertical=(point1.x==point2.x && point1.y==point2.y);
    dim3 sgridf=GetSimpleGridSize(n,SPHBSIZE);
    KerComputeDampingCylinder <<<sgridf,SPHBSIZE>>> (n,pini,dt
      ,isvertical,point1,point2,limitmin,dist,over,factorxyz,redumax
      ,posxy,posz,code,velrhop);
  }
}


}


//##############################################################################
//# Kernels for InOut (JSphInOut).
//# Kernels para InOut (JSphInOut).
//##############################################################################
#include "JSphGpu_InOut_iker.cu"


