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

/// \file JSphGpu.cpp \brief Implements the class \ref JSphGpu.

#include "JSphGpu.h"
#include "JException.h"
#include "JSphGpu_ker.h"
#include "JSphGpuSimple_ker.h"
#include "JCellDivGpu.h"
#include "JDsGpuInfo.h"
#include "JPartFloatBi4.h"
#include "Functions.h"
#include "FunctionsCuda.h"
#include "JDsMotion.h"
#include "JArraysGpu.h"
#include "JDsFixedDt.h"
#include "JDsSaveDt.h"
#include "JDsOutputTime.h"
#include "JWaveGen.h"
#include "JMLPistons.h"
#include "JRelaxZones.h"
#include "JChronoObjects.h"
#include "JDsFtForcePoints.h"
#include "JDsDamping.h"
#include "JDsAccInput.h"
#include "JXml.h"
#include "JDsGaugeSystem.h"
#include "JSphInOut.h"
#include "JSphShifting.h"
#include <float.h>
#include "JDataArrays.h"
#include "JVtkLib.h"

#include <climits>

using namespace std;

//==============================================================================
/// Constructor.
//==============================================================================
JSphGpu::JSphGpu(bool withmpi):JSph(false,false,withmpi),DivAxis(MGDIV_None){
  ClassName="JSphGpu";
  Idp=NULL; Code=NULL; Dcell=NULL; Posxy=NULL; Posz=NULL; Velrhop=NULL;
  Sigma=NULL; AuxSigma_xx_yy_zz=NULL;AuxSigma_xy_yz_xz=NULL;Kplastic=NULL;AuxKplastic=NULL;//ruofeng
  AuxPos=NULL; AuxVel=NULL; AuxRhop=NULL;
  CellDiv=NULL;
  FtoAuxDouble6=NULL; FtoAuxFloat15=NULL; //-Calculates forces on floating bodies.
  GpuInfo=new JDsGpuInfo;
  ArraysGpu=new JArraysGpu;
  Timersg=new JDsTimersGpu;
  InitVars();
}

//==============================================================================
/// Destructor.
//==============================================================================
JSphGpu::~JSphGpu(){
  DestructorActive=true;
  FreeCpuMemoryParticles();
  FreeGpuMemoryParticles();
  FreeGpuMemoryFixed();
  delete ArraysGpu; ArraysGpu=NULL;
  delete GpuInfo;   GpuInfo=NULL;
  delete Timersg;    Timersg=NULL;
  cudaDeviceReset();
}

//==============================================================================
/// Throws exception related to a CUDA error from a static method.
//==============================================================================
void JSphGpu::RunExceptioonCudaStatic(const std::string &srcfile,int srcline
  ,const std::string &method
  ,cudaError_t cuerr,std::string msg)
{
  msg=msg+fun::PrintStr(" (CUDA error %d (%s)).\n",cuerr,cudaGetErrorString(cuerr));
  throw JException(srcfile,srcline,"JSphGpu",method,msg,"");
}

//==============================================================================
/// Checks CUDA error and throws exception from a static method.
//==============================================================================
void JSphGpu::CheckCudaErroorStatic(const std::string &srcfile,int srcline
  ,const std::string &method,std::string msg)
{
  const cudaError_t cuerr=cudaGetLastError();
  if(cuerr!=cudaSuccess)RunExceptioonCudaStatic(srcfile,srcline,method,cuerr,msg);
}

//==============================================================================
/// Throws exception related to a CUDA error.
//==============================================================================
void JSphGpu::RunExceptioonCuda(const std::string &srcfile,int srcline
  ,const std::string &classname,const std::string &method
  ,cudaError_t cuerr,std::string msg)const
{
  msg=msg+fun::PrintStr(" (CUDA error %d (%s)).\n",cuerr,cudaGetErrorString(cuerr));
  throw JException(srcfile,srcline,classname,method,msg,"");
}

//==============================================================================
/// Checks CUDA error and throws exception.
/// Comprueba error de CUDA y lanza excepcion si lo hubiera.
//==============================================================================
void JSphGpu::CheckCudaErroor(const std::string &srcfile,int srcline
  ,const std::string &classname,const std::string &method
  ,std::string msg)const
{
  cudaError_t cuerr=cudaGetLastError();
  if(cuerr!=cudaSuccess)RunExceptioonCuda(srcfile,srcline,classname,method,cuerr,msg);
}

//==============================================================================
/// Initialisation of variables.
//==============================================================================
void JSphGpu::InitVars(){
  RunMode="";
  memset(&BlockSizes,0,sizeof(StBlockSizes));
  BlockSizesStr="";

  DivData=DivDataGpuNull();

  Np=Npb=NpbOk=0;
  NpbPer=NpfPer=0;

  FreeCpuMemoryParticles();
  FreeCpuMemoryFixed();
  Idpg=NULL; Codeg=NULL; Dcellg=NULL; Posxyg=NULL; Poszg=NULL; PosCellg=NULL; Velrhopg=NULL;
  Sigmag=NULL; Kplasticg=NULL;//ruofeng
  PorePressg=NULL;
  PorePressRateg=NULL; DivVelg=NULL; LapPorePressg=NULL; LapZg=NULL;
  PorePressureAceDiffg=NULL;
  PorePressShepardTmpg=NULL;
  PorePressureDt=DBL_MAX;
  PorePressureDtActive=false;
  PorePressureDtConfigPrint=PorePressureDtLimitPrint=PorePressureDtFixedPrint=false;
  PorePressureUpdateDtPrint=false;
  PorePressureTopDrainedStepPrint=false;
  PorePressureBottomNoFluxStepPrint=false;
  PorePressureShepardStepPrint=false;
  PorePressureBoundaryOperatorPrint=false;
  HydromechDampingStepPrint=false;
  BoundNormalg=NULL; MotionVelg=NULL; //-mDBC
  VelrhopM1g=NULL;                                 //-Verlet
  SigmaM1g=NULL;//ruofeng
  PosxyPreg=NULL; PoszPreg=NULL; VelrhopPreg=NULL; //-Symplectic
  SigmaPreg=NULL;//ruofeng
  SpsTaug=NULL; SpsGradvelg=NULL;                  //-Laminar+SPS. 
  ViscDtg=NULL; 
  Arg=NULL; Aceg=NULL; Deltag=NULL;
  Rsigmag=NULL;//ruofeng
  ArtificialStressg=NULL;//mdbr
  ShiftPosfsg=NULL;                                //-Shifting.
  RidpMoveg=NULL;
  FtRidpg=NULL;   FtoMasspg=NULL;                  //-Floatings.
  FtoDatpg=NULL;  FtoMassg=NULL;  FtoConstraintsg=NULL;                           //-Calculates forces on floating bodies.
  FtoForcesg=NULL;  FtoForcesResg=NULL;  FtoCenterResg=NULL; //-Calculates forces on floating bodies.
  FtoCenterg=NULL; FtoAnglesg=NULL; FtoVelAceg=NULL;//-Management of floating bodies.
  FtoInertiaini8g=NULL; FtoInertiaini1g=NULL;//-Management of floating bodies.
  FtObjsOutdated=true;
  DemDatag=NULL; //(DEM)
  GpuParticlesAllocs=0;
  GpuParticlesSize=0;
  MemGpuParticles=MemGpuFixed=0;
  FreeGpuMemoryParticles();
  FreeGpuMemoryFixed();
}

//==============================================================================
/// Frees fixed memory on CPU for moving and floating bodies.
/// Libera memoria fija en CPU para moving y floating.
//==============================================================================
void JSphGpu::FreeCpuMemoryFixed(){
  MemCpuFixed=0;
  delete[] FtoAuxDouble6; FtoAuxDouble6=NULL;
  delete[] FtoAuxFloat15; FtoAuxFloat15=NULL;
}

//==============================================================================
/// Allocates memory for arrays with fixed size (motion and floating bodies).
//==============================================================================
void JSphGpu::AllocCpuMemoryFixed(){
  MemCpuFixed=0;
  if(sizeof(tfloat3)*2!=sizeof(StFtoForces))Run_Exceptioon("Error: FtoForcesg does not match float3*2.");
  if(sizeof(float)*9!=sizeof(tmatrix3f))Run_Exceptioon("Error: FtoInertiainig does not match float*9.");
  try{
    //-Allocates memory for floating bodies.
    if(CaseNfloat){
      FtoAuxDouble6=new tdouble3[FtCount*2];  MemCpuFixed+=(sizeof(tdouble3)*FtCount*2);
      FtoAuxFloat15=new tfloat3 [FtCount*5];  MemCpuFixed+=(sizeof(tfloat3) *FtCount*5);
    }
  }
  catch(const std::bad_alloc){
    Run_Exceptioon("Could not allocate the requested memory.");
  }
}

//==============================================================================
/// Frees fixed memory on the GPU for moving and floating bodies.
/// Libera memoria fija en GPU para moving y floating.
//==============================================================================
void JSphGpu::FreeGpuMemoryFixed(){
  MemGpuFixed=0;
  if(RidpMoveg)         cudaFree(RidpMoveg);          RidpMoveg=NULL;
  if(FtRidpg)           cudaFree(FtRidpg);            FtRidpg=NULL;
  if(FtoMasspg)         cudaFree(FtoMasspg);          FtoMasspg=NULL;
  if(FtoDatpg)          cudaFree(FtoDatpg);           FtoDatpg=NULL;
  if(FtoMassg)          cudaFree(FtoMassg);           FtoMassg=NULL;
  if(FtoConstraintsg)   cudaFree(FtoConstraintsg);    FtoConstraintsg=NULL;
  if(FtoForcesg)        cudaFree(FtoForcesg);         FtoForcesg=NULL;
  if(FtoForcesResg)     cudaFree(FtoForcesResg);      FtoForcesResg=NULL;
  if(FtoCenterg)        cudaFree(FtoCenterg);         FtoCenterg=NULL;
  if(FtoAnglesg)        cudaFree(FtoAnglesg);         FtoAnglesg=NULL;
  if(FtoVelAceg)        cudaFree(FtoVelAceg);         FtoVelAceg=NULL;
  if(FtoInertiaini8g)   cudaFree(FtoInertiaini8g);    FtoInertiaini8g=NULL;
  if(FtoInertiaini1g)   cudaFree(FtoInertiaini1g);    FtoInertiaini1g=NULL;
  if(DemDatag)          cudaFree(DemDatag);           DemDatag=NULL;
}

//==============================================================================
/// Allocates memory for arrays with fixed size (motion and floating bodies).
//==============================================================================
void JSphGpu::AllocGpuMemoryFixed(){
  MemGpuFixed=0;
  //-Allocates memory for moving objects.
  if(CaseNmoving){
    size_t m=sizeof(unsigned)*CaseNmoving;
    cudaMalloc((void**)&RidpMoveg,m);   MemGpuFixed+=m;
  }
  //-Allocates memory for floating bodies.
  if(CaseNfloat){
    size_t m=0;
    m=sizeof(unsigned)*CaseNfloat;  cudaMalloc((void**)&FtRidpg           ,m);  MemGpuFixed+=m;
    m=sizeof(float)   *FtCount;     cudaMalloc((void**)&FtoMasspg         ,m);  MemGpuFixed+=m;
    m=sizeof(float4)  *FtCount;     cudaMalloc((void**)&FtoDatpg          ,m);  MemGpuFixed+=m;
    m=sizeof(float)   *FtCount;     cudaMalloc((void**)&FtoMassg          ,m);  MemGpuFixed+=m;
    m=sizeof(byte)    *FtCount;     cudaMalloc((void**)&FtoConstraintsg   ,m);  MemGpuFixed+=m;
    m=sizeof(float3)  *FtCount*2;   cudaMalloc((void**)&FtoForcesg        ,m);  MemGpuFixed+=m;
    m=sizeof(float3)  *FtCount*2;   cudaMalloc((void**)&FtoForcesResg     ,m);  MemGpuFixed+=m;
    m=sizeof(double3) *FtCount;     cudaMalloc((void**)&FtoCenterResg     ,m);  MemGpuFixed+=m;
    m=sizeof(double3) *FtCount;     cudaMalloc((void**)&FtoCenterg        ,m);  MemGpuFixed+=m;
    m=sizeof(float3)  *FtCount;     cudaMalloc((void**)&FtoAnglesg        ,m);  MemGpuFixed+=m;
    m=sizeof(float3)  *FtCount*4;   cudaMalloc((void**)&FtoVelAceg        ,m);  MemGpuFixed+=m;
    m=sizeof(float4)  *FtCount*2;   cudaMalloc((void**)&FtoInertiaini8g   ,m);  MemGpuFixed+=m;
    m=sizeof(float)   *FtCount;     cudaMalloc((void**)&FtoInertiaini1g   ,m);  MemGpuFixed+=m;
  }
  if(UseDEM){ //(DEM)
    size_t m=sizeof(float4)*DemDataSize;
    cudaMalloc((void**)&DemDatag,m);     MemGpuFixed+=m;
  }
}

//==============================================================================
/// Releases memory for the main particle data.
/// Libera memoria para datos principales de particulas.
//==============================================================================
void JSphGpu::FreeCpuMemoryParticles(){
  CpuParticlesSize=0;
  MemCpuParticles=0;
  delete[] Idp;        Idp=NULL;
  delete[] Code;       Code=NULL;
  delete[] Dcell;      Dcell=NULL;
  delete[] Posxy;      Posxy=NULL;
  delete[] Posz;       Posz=NULL;
  delete[] Velrhop;    Velrhop=NULL;
  //ruofeng
  delete[] Sigma;      Sigma = NULL;
  delete[] Kplastic;   Kplastic = NULL;
  //
  delete[] AuxPos;     AuxPos=NULL;
  delete[] AuxVel;     AuxVel=NULL;
  delete[] AuxRhop;    AuxRhop=NULL;
  //ruofeng
  delete[] AuxSigma_xx_yy_zz;   AuxSigma_xx_yy_zz = NULL;
  delete[] AuxSigma_xy_yz_xz;   AuxSigma_xy_yz_xz = NULL;
  delete[] AuxKplastic; AuxKplastic = NULL;
}

//==============================================================================
/// Allocates memory for the main particle data.
/// Reserva memoria para datos principales de particulas.
//==============================================================================
void JSphGpu::AllocCpuMemoryParticles(unsigned np){
  FreeCpuMemoryParticles();
  if(np>0)np=np+PARTICLES_OVERMEMORY_MIN;
  CpuParticlesSize=np;
  if(np>0){
    try{
      Idp=new unsigned[np];      MemCpuParticles+=sizeof(unsigned)*np;
      Code=new typecode[np];     MemCpuParticles+=sizeof(typecode)*np;
      Dcell=new unsigned[np];    MemCpuParticles+=sizeof(unsigned)*np;
      Posxy=new tdouble2[np];    MemCpuParticles+=sizeof(tdouble2)*np;
      Posz=new double[np];       MemCpuParticles+=sizeof(double)*np;
      Velrhop=new tfloat4[np];   MemCpuParticles+=sizeof(tfloat4)*np;
      //=========mdbr
	  Sigma=new tsymatrix3f[np]; MemCpuParticles+=sizeof(tsymatrix3f)*np;
      Kplastic = new float[np]; MemCpuParticles += sizeof(float) * np;
      //==========
      AuxPos=new tdouble3[np];   MemCpuParticles+=sizeof(tdouble3)*np; 
      AuxVel=new tfloat3[np];    MemCpuParticles+=sizeof(tfloat3)*np;
      AuxRhop=new float[np];     MemCpuParticles+=sizeof(float)*np;
      //======mdbr
      AuxSigma_xx_yy_zz = new tfloat3[np]; MemCpuParticles+=sizeof(tfloat3)*np;
      AuxSigma_xy_yz_xz = new tfloat3[np]; MemCpuParticles+=sizeof(tfloat3)*np;
      AuxKplastic = new float[np];   MemCpuParticles += sizeof(float) *np;
      //======
    }
    catch(const std::bad_alloc){
      Run_Exceptioon(fun::PrintStr("Could not allocate the requested memory (np=%u).",np));
    }
  }
}

//==============================================================================
/// Frees GPU memory for the particles.
/// Libera memoria en Gpu para particulas.
//==============================================================================
void JSphGpu::FreeGpuMemoryParticles(){
  //GpuParticlesAllocs=0; This values is kept.
  GpuParticlesSize=0;
  MemGpuParticles=0;
  ArraysGpu->Reset();
  Idpg=NULL; Codeg=NULL; Dcellg=NULL; Posxyg=NULL; Poszg=NULL; PosCellg=NULL; Velrhopg=NULL;
  Sigmag=NULL; Kplasticg=NULL; PorePressg=NULL;
  PorePressRateg=NULL; DivVelg=NULL; LapPorePressg=NULL; LapZg=NULL;
  PorePressureAceDiffg=NULL;
  PorePressShepardTmpg=NULL;
  VelrhopM1g=NULL; SigmaM1g=NULL;
  PosxyPreg=NULL; PoszPreg=NULL; VelrhopPreg=NULL; SigmaPreg=NULL;
  SpsTaug=NULL; BoundNormalg=NULL; MotionVelg=NULL;
}

//==============================================================================
/// Allocates GPU memory for the particles.
/// Reserva memoria en Gpu para las particulas. 
//==============================================================================
void JSphGpu::AllocGpuMemoryParticles(unsigned np,float over){
  FreeGpuMemoryParticles();
  //-Computes number of particles for which memory will be allocated.
  //-Calcula numero de particulas para las que se reserva memoria.
  const unsigned np2=(over>0? unsigned(over*np): np);
  GpuParticlesSize=np2+PARTICLES_OVERMEMORY_MIN;
  //-Define number or arrays to use. | Establece numero de arrays a usar.
  ArraysGpu->SetArraySize(GpuParticlesSize);
  #ifdef CODE_SIZE4
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_4B,2);  //-code,code2
  #else
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_2B,2);  //-code,code2
  #endif
  ArraysGpu->AddArrayCount(JArraysGpu::SIZE_4B,4);  //-idp,ar,viscdt,dcell
  if(DDTArray)ArraysGpu->AddArrayCount(JArraysGpu::SIZE_4B,1);  //-delta
  ArraysGpu->AddArrayCount(JArraysGpu::SIZE_12B,1); //-ace
  ArraysGpu->AddArrayCount(JArraysGpu::SIZE_16B,5); //-velrhop,posxy,poscell
  ArraysGpu->AddArrayCount(JArraysGpu::SIZE_8B,2);  //-posz
  //====== mdbr
  ArraysGpu->AddArrayCount(JArraysGpu::SIZE_24B, 1);//-sigma
  ArraysGpu->AddArrayCount(JArraysGpu::SIZE_24B, 1);//-rsigma
  if(ArtificialStress)ArraysGpu->AddArrayCount(JArraysGpu::SIZE_24B,1);//-artificialstress
  ArraysGpu->AddArrayCount(JArraysGpu::SIZE_4B, 2);//-kplastic
  if(HydromechCoupling || SavePorePressure){
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_8B,2);//-porepress + sort buffer
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_4B,8);//-PR diagnostic arrays + sort buffers
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_12B,2);//-PorePressureAceDiff + sort buffer
  }
  if(HydromechCoupling && PorePressureModel==1 && PorePressureShepard)
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_8B,1);//-temporary pore-pressure Shepard buffer
  if(TStep==STEP_Verlet){
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_16B,1); //-velrhopm1
    //====mdbr
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_24B, 1);//-sigmam1
  }
  else if(TStep==STEP_Symplectic){
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_8B,1);  //-poszpre
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_16B,2); //-posxypre,velrhoppre
    //====mdbr
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_24B, 1);//-sigmapre
  }
  if(TVisco==VISCO_LaminarSPS){     
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_24B,2); //-SpsTau,SpsGradvel
  }
  if(CaseNfloat){
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_4B,4);  //-FtMasspg
  }
  if(Shifting){
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_16B,1); //-shiftposfs
  }
  if(UseNormals){
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_12B,1); //-BoundNormal
    if(SlipMode!=SLIP_Vel0)ArraysGpu->AddArrayCount(JArraysGpu::SIZE_12B,1); //-MotionVel
  }
  if(InOut){
    //ArraysGpu->AddArrayCount(JArraysGpu::SIZE_4B,1);  //-InOutPartg
    ArraysGpu->AddArrayCount(JArraysGpu::SIZE_1B,2);  //-newizone,zsurfok
  }

  //-Shows the allocated memory.
  MemGpuParticles=ArraysGpu->GetAllocMemoryGpu();
  PrintSizeNp(GpuParticlesSize,MemGpuParticles,GpuParticlesAllocs);
  Check_CudaErroor("Failed GPU memory allocation.");
}

//==============================================================================
/// Resizes space in GPU memory for particles.
//==============================================================================
void JSphGpu::ResizeGpuMemoryParticles(unsigned npnew){
  npnew=npnew+PARTICLES_OVERMEMORY_MIN;
  //-Saves current data from GPU.
  unsigned    *idp        =SaveArrayGpu(Np,Idpg);
  typecode    *code       =SaveArrayGpu(Np,Codeg);
  unsigned    *dcell      =SaveArrayGpu(Np,Dcellg);
  double2     *posxy      =SaveArrayGpu(Np,Posxyg);
  double      *posz       =SaveArrayGpu(Np,Poszg);
  float4      *poscell    =SaveArrayGpu(Np,PosCellg);
  float4      *velrhop    =SaveArrayGpu(Np,Velrhopg);
  float4      *velrhopm1  =SaveArrayGpu(Np,VelrhopM1g);
  double2     *posxypre   =SaveArrayGpu(Np,PosxyPreg);
  double      *poszpre    =SaveArrayGpu(Np,PoszPreg);
  float4      *velrhoppre =SaveArrayGpu(Np,VelrhopPreg);
  tsymatrix3f *spstau     =SaveArrayGpu(Np,SpsTaug);
  float3      *boundnormal=SaveArrayGpu(Np,BoundNormalg);
  float3      *motionvel  =SaveArrayGpu(Np,MotionVelg);
  //==mdbr
  tsymatrix3f* sigma = SaveArrayGpu(Np, Sigmag);
  float* kplastic = SaveArrayGpu(Np, Kplasticg);
  double* porepress = SaveArrayGpu(Np, PorePressg);
  float* porepressrate = SaveArrayGpu(Np, PorePressRateg);
  float* divvel = SaveArrayGpu(Np, DivVelg);
  float* lapporepress = SaveArrayGpu(Np, LapPorePressg);
  float* lapz = SaveArrayGpu(Np, LapZg);
  float3* porepressureacediff = SaveArrayGpu(Np, PorePressureAceDiffg);
  const bool porepressshepardtmp = (PorePressShepardTmpg!=NULL);
  tsymatrix3f* sigmapre = SaveArrayGpu(Np, SigmaPreg);
  tsymatrix3f* sigmam1 = SaveArrayGpu(Np, SigmaM1g);
  // 
  //-Frees pointers.
  ArraysGpu->Free(Idpg);
  ArraysGpu->Free(Codeg);
  ArraysGpu->Free(Dcellg);
  ArraysGpu->Free(Posxyg);
  ArraysGpu->Free(Poszg);
  ArraysGpu->Free(PosCellg);
  ArraysGpu->Free(Velrhopg);
  ArraysGpu->Free(VelrhopM1g);
  ArraysGpu->Free(PosxyPreg);
  ArraysGpu->Free(PoszPreg);
  ArraysGpu->Free(VelrhopPreg);
  ArraysGpu->Free(SpsTaug);
  ArraysGpu->Free(BoundNormalg);
  ArraysGpu->Free(MotionVelg);
  //-mdbr
  ArraysGpu->Free(Sigmag);
  ArraysGpu->Free(Kplasticg);
  ArraysGpu->Free(PorePressg);
  ArraysGpu->Free(PorePressRateg);
  ArraysGpu->Free(DivVelg);
  ArraysGpu->Free(LapPorePressg);
  ArraysGpu->Free(LapZg);
  ArraysGpu->Free(PorePressureAceDiffg);
  ArraysGpu->Free(PorePressShepardTmpg);
  ArraysGpu->Free(SigmaPreg);
  ArraysGpu->Free(SigmaM1g);
  // 
  //-Resizes GPU memory allocation.
  const double mbparticle=(double(MemGpuParticles)/(1024*1024))/GpuParticlesSize; //-MB por particula.
  Log->Printf("**JSphGpu: Requesting gpu memory for %u particles: %.1f MB.",npnew,mbparticle*npnew);
  ArraysGpu->SetArraySize(npnew);
  //-Reserve pointers.
  Idpg    =ArraysGpu->ReserveUint();
  Codeg   =ArraysGpu->ReserveTypeCode();
  Dcellg  =ArraysGpu->ReserveUint();
  Posxyg  =ArraysGpu->ReserveDouble2();
  Poszg   =ArraysGpu->ReserveDouble();
  PosCellg=ArraysGpu->ReserveFloat4();
  Velrhopg=ArraysGpu->ReserveFloat4();
  if(velrhopm1)  VelrhopM1g  =ArraysGpu->ReserveFloat4();
  if(posxypre)   PosxyPreg   =ArraysGpu->ReserveDouble2();
  if(poszpre)    PoszPreg    =ArraysGpu->ReserveDouble();
  if(velrhoppre) VelrhopPreg =ArraysGpu->ReserveFloat4();
  if(spstau)     SpsTaug     =ArraysGpu->ReserveSymatrix3f();
  if(boundnormal)BoundNormalg=ArraysGpu->ReserveFloat3();
  if(motionvel)  MotionVelg  =ArraysGpu->ReserveFloat3();
  //--mdbr
  if(sigma)      Sigmag = ArraysGpu->ReserveSymatrix3f();
  if(kplastic)   Kplasticg = ArraysGpu->ReserveFloat();
  if(porepress)  PorePressg = ArraysGpu->ReserveDouble();
  if(porepressrate) PorePressRateg = ArraysGpu->ReserveFloat();
  if(divvel)        DivVelg = ArraysGpu->ReserveFloat();
  if(lapporepress)  LapPorePressg = ArraysGpu->ReserveFloat();
  if(lapz)          LapZg = ArraysGpu->ReserveFloat();
  if(porepressureacediff) PorePressureAceDiffg = ArraysGpu->ReserveFloat3();
  if(porepressshepardtmp) PorePressShepardTmpg = ArraysGpu->ReserveDouble();
  if(sigmapre)   SigmaPreg = ArraysGpu->ReserveSymatrix3f();
  if(sigmam1)      SigmaM1g = ArraysGpu->ReserveSymatrix3f();
  // 
  //-Restore data in GPU memory.
  RestoreArrayGpu(Np,idp,Idpg);
  RestoreArrayGpu(Np,code,Codeg);
  RestoreArrayGpu(Np,dcell,Dcellg);
  RestoreArrayGpu(Np,posxy,Posxyg);
  RestoreArrayGpu(Np,posz,Poszg);
  RestoreArrayGpu(Np,poscell,PosCellg);
  RestoreArrayGpu(Np,velrhop,Velrhopg);
  RestoreArrayGpu(Np,velrhopm1,VelrhopM1g);
  RestoreArrayGpu(Np,posxypre,PosxyPreg);
  RestoreArrayGpu(Np,poszpre,PoszPreg);
  RestoreArrayGpu(Np,velrhoppre,VelrhopPreg);
  RestoreArrayGpu(Np,spstau,SpsTaug);
  RestoreArrayGpu(Np,boundnormal,BoundNormalg);
  RestoreArrayGpu(Np,motionvel,MotionVelg);
  //---mdbr
  RestoreArrayGpu(Np,sigma,Sigmag);
  RestoreArrayGpu(Np,kplastic,Kplasticg);
  RestoreArrayGpu(Np,porepress,PorePressg);
  RestoreArrayGpu(Np,porepressrate,PorePressRateg);
  RestoreArrayGpu(Np,divvel,DivVelg);
  RestoreArrayGpu(Np,lapporepress,LapPorePressg);
  RestoreArrayGpu(Np,lapz,LapZg);
  RestoreArrayGpu(Np,porepressureacediff,PorePressureAceDiffg);
  RestoreArrayGpu(Np,sigmam1,SigmaM1g);
  RestoreArrayGpu(Np,sigmapre,SigmaPreg);
  //
  //-Updates values.
  GpuParticlesAllocs++;
  GpuParticlesSize=npnew;
  MemGpuParticles=ArraysGpu->GetAllocMemoryGpu();
}

//==============================================================================
/// Saves a GPU array in CPU memory. 
//==============================================================================
template<class T> T* JSphGpu::TSaveArrayGpu(unsigned np,const T *datasrc)const{
  T *data=NULL;
  if(datasrc){
    try{
      data=new T[np];
    }
    catch(const std::bad_alloc){
      Run_Exceptioon("Could not allocate the requested memory.");
    }
    cudaMemcpy(data,datasrc,sizeof(T)*np,cudaMemcpyDeviceToHost);
  }
  return(data);
}

//==============================================================================
/// Restores a GPU array (generic) from CPU memory. 
//==============================================================================
template<class T> void JSphGpu::TRestoreArrayGpu(unsigned np,T *data,T *datanew)const{
  if(data&&datanew)cudaMemcpy(datanew,data,sizeof(T)*np,cudaMemcpyHostToDevice);
  delete[] data;
}

//==============================================================================
/// Saves a GPU scalar array in CPU memory, removing periodic particles when needed.
//==============================================================================
double* JSphGpu::SaveNormalArrayGpu(unsigned npsave,const double *datasrc)const{
  double *out=NULL;
  if(datasrc){
    double *all=SaveArrayGpu(Np,datasrc);
    out=JDataArrays::NewArrayDouble(npsave,false);
    if(PeriActive){
      typecode *codeall=SaveArrayGpu(Np,Codeg);
      unsigned q=0;
      for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(codeall[p])){
        if(q<npsave)out[q]=all[p];
        q++;
      }
      delete[] codeall;
      if(q!=npsave){
        delete[] all;
        delete[] out;
        Run_Exceptioon("The number of normal scalar particles is invalid.");
      }
    }
    else memcpy(out,all,sizeof(double)*npsave);
    delete[] all;
  }
  return(out);
}

//==============================================================================
/// Saves a GPU scalar array in CPU memory, removing periodic particles when needed.
//==============================================================================
float* JSphGpu::SaveNormalArrayGpu(unsigned npsave,const float *datasrc)const{
  float *out=NULL;
  if(datasrc){
    float *all=SaveArrayGpu(Np,datasrc);
    out=JDataArrays::NewArrayFloat(npsave,false);
    if(PeriActive){
      typecode *codeall=SaveArrayGpu(Np,Codeg);
      unsigned q=0;
      for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(codeall[p])){
        if(q<npsave)out[q]=all[p];
        q++;
      }
      delete[] codeall;
      if(q!=npsave){
        delete[] all;
        delete[] out;
        Run_Exceptioon("The number of normal scalar particles is invalid.");
      }
    }
    else memcpy(out,all,sizeof(float)*npsave);
    delete[] all;
  }
  return(out);
}

//==============================================================================
/// Saves a GPU float3 array in CPU memory, removing periodic particles when needed.
//==============================================================================
tfloat3* JSphGpu::SaveNormalArrayGpu(unsigned npsave,const float3 *datasrc)const{
  tfloat3 *out=NULL;
  if(datasrc){
    float3 *all=SaveArrayGpu(Np,datasrc);
    out=new tfloat3[npsave];
    if(PeriActive){
      typecode *codeall=SaveArrayGpu(Np,Codeg);
      unsigned q=0;
      for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(codeall[p])){
        if(q<npsave)out[q]=TFloat3(all[p].x,all[p].y,all[p].z);
        q++;
      }
      delete[] codeall;
      if(q!=npsave){
        delete[] all;
        delete[] out;
        Run_Exceptioon("The number of normal float3 particles is invalid.");
      }
    }
    else for(unsigned p=0;p<npsave;p++)out[p]=TFloat3(all[p].x,all[p].y,all[p].z);
    delete[] all;
  }
  return(out);
}

//==============================================================================
/// Arrays for basic particle data.
/// Arrays para datos basicos de las particulas. 
//==============================================================================
void JSphGpu::ReserveBasicArraysGpu(){
  Idpg=ArraysGpu->ReserveUint();
  Codeg=ArraysGpu->ReserveTypeCode();
  Dcellg=ArraysGpu->ReserveUint();
  Posxyg=ArraysGpu->ReserveDouble2();
  Poszg=ArraysGpu->ReserveDouble();
  PosCellg=ArraysGpu->ReserveFloat4();
  Velrhopg=ArraysGpu->ReserveFloat4();
  //mdbr
  Sigmag = ArraysGpu->ReserveSymatrix3f();
  Kplasticg = ArraysGpu->ReserveFloat();
  if(HydromechCoupling || SavePorePressure){
    PorePressg=ArraysGpu->ReserveDouble();
    PorePressRateg=ArraysGpu->ReserveFloat();
    DivVelg=ArraysGpu->ReserveFloat();
    LapPorePressg=ArraysGpu->ReserveFloat();
    LapZg=ArraysGpu->ReserveFloat();
    PorePressureAceDiffg=ArraysGpu->ReserveFloat3();
  }
  if(HydromechCoupling && PorePressureModel==1 && PorePressureShepard)
    PorePressShepardTmpg=ArraysGpu->ReserveDouble();
  if(TStep==STEP_Verlet){VelrhopM1g=ArraysGpu->ReserveFloat4();
  SigmaM1g = ArraysGpu->ReserveSymatrix3f();//mdbr
  }
  if(TVisco==VISCO_LaminarSPS)SpsTaug=ArraysGpu->ReserveSymatrix3f();
  if(UseNormals){
    BoundNormalg=ArraysGpu->ReserveFloat3();
    if(SlipMode!=SLIP_Vel0)MotionVelg=ArraysGpu->ReserveFloat3();
  }
}

//==============================================================================
/// Returns the allocated memory on the CPU.
/// Devuelve la memoria reservada en CPU.
//==============================================================================
llong JSphGpu::GetAllocMemoryCpu()const{  
  llong s=JSph::GetAllocMemoryCpu();
  //-Allocated in AllocCpuMemoryFixed().
  s+=MemCpuFixed;
  //-Allocated in AllocMemoryParticles().
  s+=MemCpuParticles;
  //-Allocated in other objects.
  if(MLPistons)s+=MLPistons->GetAllocMemoryCpu();
  return(s);
}

//==============================================================================
/// Returns the allocated memory in the GPU.
/// Devuelve la memoria reservada en GPU.
//==============================================================================
llong JSphGpu::GetAllocMemoryGpu()const{  
  llong s=0;
  //-Allocated in AllocGpuMemoryParticles().
  s+=MemGpuParticles;
  //-Allocated in AllocGpuMemoryFixed().
  s+=MemGpuFixed;
  //-Allocated in ther objects.
  if(MLPistons)s+=MLPistons->GetAllocMemoryGpu();
  return(s);
}

//==============================================================================
/// Displays the allocated memory.
/// Visualiza la memoria reservada.
//==============================================================================
void JSphGpu::PrintAllocMemory(llong mcpu,llong mgpu)const{
  Log->Printf("Allocated memory in CPU: %lld (%.2f MB)",mcpu,double(mcpu)/(1024*1024));
  Log->Printf("Allocated memory in GPU: %lld (%.2f MB)",mgpu,double(mgpu)/(1024*1024));
}

//==============================================================================
/// Uploads constants to the GPU.
/// Copia constantes a la GPU.
//==============================================================================
void JSphGpu::ConstantDataUp(){
  StCteInteraction ctes;
  memset(&ctes,0,sizeof(StCteInteraction));
  ctes.nbound=CaseNbound;
  ctes.massb=MassBound; ctes.massf=MassFluid;
  ctes.kernelh=KernelH;
  ctes.kernelsize2=KernelSize2; 
  ctes.poscellsize=PosCellSize; 
  //-Wendland constants are always computed since this kernel is used in some parts where other kernels are not defined (e.g. mDBC, inlet/outlet...).
  ctes.awen=KWend.awen; ctes.bwen=KWend.bwen;
  //-Copies constants for other kernels.
  if(TKernel==KERNEL_Cubic){
    ctes.cubic_a1=KCubic.a1; ctes.cubic_a2=KCubic.a2; ctes.cubic_aa=KCubic.aa; ctes.cubic_a24=KCubic.a24;
    ctes.cubic_c1=KCubic.c1; ctes.cubic_c2=KCubic.c2; ctes.cubic_d1=KCubic.d1; ctes.cubic_odwdeltap=KCubic.od_wdeltap;
  }
  ctes.cs0=float(Cs0); ctes.eta2=Eta2;
  ctes.ddtkh=DDTkh;
  ctes.ddtgz=DDTgz;
  ctes.sdtgz=RhopZero*Gravity.z;//mdbr
  ctes.k0=1.f-sin(SoilCte.phi);//mdbr
  ctes.scell=Scell; 
  ctes.kernelsize=KernelSize;
  ctes.dp=float(Dp);
  ctes.artificialstress=(ArtificialStress? 1: 0);
  ctes.artificialstresscoef=ArtificialStressCoef;
  ctes.artificialstressexp=ArtificialStressExp;
  ctes.cteb=CteB; ctes.gamma=Gamma;
  ctes.rhopzero=RhopZero;
  ctes.ovrhopzero=1.f/RhopZero;
  ctes.movlimit=MovLimit;
  ctes.maprealposminx=MapRealPosMin.x; ctes.maprealposminy=MapRealPosMin.y; ctes.maprealposminz=MapRealPosMin.z;
  ctes.maprealsizex=MapRealSize.x; ctes.maprealsizey=MapRealSize.y; ctes.maprealsizez=MapRealSize.z;
  ctes.symmetry=Symmetry;   //<vs_syymmetry>
  ctes.tboundary=unsigned(TBoundary);
  ctes.periactive=PeriActive;
  ctes.xperincx=PeriXinc.x; ctes.xperincy=PeriXinc.y; ctes.xperincz=PeriXinc.z;
  ctes.yperincx=PeriYinc.x; ctes.yperincy=PeriYinc.y; ctes.yperincz=PeriYinc.z;
  ctes.zperincx=PeriZinc.x; ctes.zperincy=PeriZinc.y; ctes.zperincz=PeriZinc.z;
  ctes.axis=MGDIV_Z;//-Necessary to avoid errors in KerGetInteraction_Cells().
  ctes.cellcode=DomCellCode;
  ctes.domposminx=DomPosMin.x; ctes.domposminy=DomPosMin.y; ctes.domposminz=DomPosMin.z;
  ctes.modulus_K=SoilCte.ModulusK; ctes.modulus_G=SoilCte.ModulusG;
  cusph::CteInteractionUp(&ctes);
  cusphs::CteInteractionUpTStep(&SoilCte);//mbdr
  Check_CudaErroor("Failed copying constants to GPU.");
}

//==============================================================================
/// Uploads particle data to the GPU.
/// Sube datos de particulas a la GPU.
//==============================================================================
void JSphGpu::ParticlesDataUp(unsigned n,const tfloat3 *boundnormal){
  cudaMemcpy(Idpg    ,Idp    ,sizeof(unsigned)*n,cudaMemcpyHostToDevice);
  cudaMemcpy(Codeg   ,Code   ,sizeof(typecode)*n,cudaMemcpyHostToDevice);
  cudaMemcpy(Dcellg  ,Dcell  ,sizeof(unsigned)*n,cudaMemcpyHostToDevice);
  cudaMemcpy(Posxyg  ,Posxy  ,sizeof(double2)*n ,cudaMemcpyHostToDevice);
  cudaMemcpy(Poszg   ,Posz   ,sizeof(double)*n  ,cudaMemcpyHostToDevice);
  cudaMemcpy(Velrhopg,Velrhop,sizeof(float4)*n  ,cudaMemcpyHostToDevice);
  //===mdbr
  cudaMemcpy(Sigmag, Sigma, sizeof(tsymatrix3f)*n, cudaMemcpyHostToDevice);
  cudaMemcpy(Kplasticg, Kplastic, sizeof(float)*n, cudaMemcpyHostToDevice);
  //====
  if(PorePressg){
    InitPorePressureGpu(n);
    if(HydromechCoupling && PorePressureModel==1){
      if(PorePressureTopDrained)ApplyPorePressureTopDrainedGpu(TimeStep,"initialization",true);
      if(PorePressureBottomNoFlux)ApplyPorePressureBottomNoFluxGpu("initialization",true);
    }
  }
  if(PorePressRateg || DivVelg || LapPorePressg || LapZg || PorePressureAceDiffg)InitPorePressureDiagnosticsGpu(n);
  if(UseNormals)cudaMemcpy(BoundNormalg,boundnormal,sizeof(float3)*n,cudaMemcpyHostToDevice);
  Check_CudaErroor("Failed copying data to GPU.");
}

//==============================================================================
/// Initialises passive pore pressure on GPU for G1 output/parity.
//==============================================================================
void JSphGpu::InitPorePressureGpu(unsigned n){
  if(!PorePressg)return;
  if(PorePressureInit==2)Run_Exceptioon("PorePressureInit=2 is not implemented for GPU passive pore-pressure G1.");
  double *porepress=NULL;
  try{
    porepress=new double[n];
  }
  catch(const std::bad_alloc){
    Run_Exceptioon("Could not allocate temporary pore-pressure initialisation buffer.");
  }
  memset(porepress,0,sizeof(double)*n);
  if(HydromechCoupling && (PorePressureInit==1 || PorePressureInit==3)){
    if(SoilCte.WaterDensity<=0.f)Run_Exceptioon("Soil WaterDensity must be greater than zero for GPU pore pressure initialization.");
    const double gmag=GetHydraulicGmag();
    if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for GPU pore pressure initialization.");
    unsigned npmat=0,npnonzero=0;
    double zmin=DBL_MAX,zmax=-DBL_MAX;
    for(unsigned p=0;p<n;p++)if(CODE_IsFluid(Code[p])){
      npmat++;
      const tdouble3 ps=TDouble3(Posxy[p].x,Posxy[p].y,Posz[p]);
      const double z=GetHydraulicElevation(ps);
      zmin=min(zmin,z);
      zmax=max(zmax,z);
    }
    if(!npmat)Log->PrintWarning("GPU pore pressure initialization found no material particles.");
    const double zrange=zmax-zmin;
    if(PorePressureInit==3 && zrange<=0.)Log->PrintWarning("GPU analytical excess pore pressure initialization found zero material elevation range. eta is set to zero.");
    double pwmax=-DBL_MAX;
    for(unsigned p=0;p<n;p++)if(CODE_IsFluid(Code[p])){
      const tdouble3 ps=TDouble3(Posxy[p].x,Posxy[p].y,Posz[p]);
      const double z=GetHydraulicElevation(ps);
      const double depth=double(PorePressureWaterLevel)-z;
      const double hydrostatic=(depth>0.? double(SoilCte.WaterDensity)*gmag*depth: 0.);
      double excess=0.;
      if(PorePressureInit==3){
        double eta=(zrange>0.? (z-zmin)/zrange: 0.);
        eta=max(0.,min(1.,eta));
        if(PorePressureAnalyticalProfile==1)excess=double(PorePressureExcessAmp)*sin(PI*eta);
        else if(PorePressureAnalyticalProfile==2)excess=double(PorePressureExcessAmp)*cos(PIHALF*eta);
        else if(PorePressureAnalyticalProfile==3)excess=double(PorePressureExcessAmp);
        else Run_Exceptioon("PorePressureAnalyticalProfile mode is not valid.");
      }
      const double pw=hydrostatic+excess;
      porepress[p]=pw;
      pwmax=max(pwmax,pw);
      if(pw)npnonzero++;
    }
    if(!npmat){
      zmin=zmax=0.;
      pwmax=0.;
    }
    Log->Printf("Passive GPU pore pressure initialised: Init=%d, WaterLevel=%g, material elevation range=[%g,%g], nonzero=%u/%u, max(PorePress)=%g Pa."
      ,PorePressureInit,PorePressureWaterLevel,zmin,zmax,npnonzero,npmat,pwmax);
  }
  else Log->Printf("Passive GPU pore pressure initialised: PorePress=0 for %u particles.",n);
  cudaMemcpy(PorePressg,porepress,sizeof(double)*n,cudaMemcpyHostToDevice);
  delete[] porepress;
}

//==============================================================================
/// Initialises passive GPU PR diagnostic arrays to zero.
//==============================================================================
void JSphGpu::InitPorePressureDiagnosticsGpu(unsigned n){
  if(PorePressRateg)cudaMemset(PorePressRateg,0,sizeof(float)*n);
  if(DivVelg)cudaMemset(DivVelg,0,sizeof(float)*n);
  if(LapPorePressg)cudaMemset(LapPorePressg,0,sizeof(float)*n);
  if(LapZg)cudaMemset(LapZg,0,sizeof(float)*n);
  if(PorePressureAceDiffg)cudaMemset(PorePressureAceDiffg,0,sizeof(float3)*n);
}

//==============================================================================
/// Computes passive GPU PR diagnostic fields. It does not update PorePressg.
//==============================================================================
void JSphGpu::ComputeHydroPrDiagnosticsGpu(){
  if(!HydromechCoupling || PorePressureModel!=1)return;
  if(!PorePressg || !PorePressRateg || !DivVelg || !LapPorePressg || !LapZg)return;
  if(!Np || !DivData.beginendcell)return;
  const float porosity0=SoilCte.Porosity0;
  const float hydraulicconductivity=SoilCte.HydraulicConductivity;
  const float waterbulkmodulus=SoilCte.WaterBulkModulus;
  const float waterdensity=SoilCte.WaterDensity;
  if(porosity0<=0.f || porosity0>=1.f)Run_Exceptioon("Soil Porosity0 must be between 0 and 1 for GPU PR diagnostics.");
  if(waterbulkmodulus<=0.f)Run_Exceptioon("Soil WaterBulkModulus must be greater than zero for GPU PR diagnostics.");
  if(waterdensity<=0.f)Run_Exceptioon("Soil WaterDensity must be greater than zero for GPU PR diagnostics.");
  const double gmag=GetHydraulicGmag();
  if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for GPU PR diagnostics.");
  const tfloat3 hg=GetHydraulicGravity();
  const unsigned bsfluid=(BlockSizes.forcesfluid? BlockSizes.forcesfluid: SPHBSIZE);
  cusph::ComputeHydroPrDiagnostics(TKernel,Symmetry,bsfluid
    ,Np-Npb,Npb,DivData,Dcellg,PosCellg,Velrhopg,Codeg,PorePressg
    ,hg.x,hg.y,hg.z,gmag,porosity0,hydraulicconductivity,waterbulkmodulus,waterdensity
    ,DivVelg,LapPorePressg,LapZg,PorePressRateg);
  Check_CudaErroor("Failed computing GPU PR pore-pressure diagnostics.");
  if(PorePressureBoundaryOperator==1){
    if(ApplyPorePressureBoundaryOperatorGpu(!PorePressureBoundaryOperatorPrint))
      PorePressureBoundaryOperatorPrint=true;
  }
}

//==============================================================================
/// Adds GPU hydraulic boundary contributions to PR LapPorePress/LapZ operators.
//==============================================================================
unsigned JSphGpu::ApplyPorePressureBoundaryOperatorGpu(bool printlog){
  if(!HydromechCoupling || PorePressureModel!=1 || PorePressureBoundaryOperator!=1)return(0);
  if(!PorePressg || !PorePressRateg || !DivVelg || !LapPorePressg || !LapZg)return(0);
  if(!PorePressureTopDrained && !PorePressureBottomNoFlux)return(0);
  const unsigned nfluid=(Np>Npb? Np-Npb: 0);
  if(!nfluid)return(0);
  const double gmag=GetHydraulicGmag();
  if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for GPU pore-pressure boundary operator.");
  if(SoilCte.WaterDensity<=0.f)Run_Exceptioon("Soil WaterDensity must be greater than zero for GPU pore-pressure boundary operator.");
  if(SoilCte.Porosity0<=0.f || SoilCte.Porosity0>=1.f)Run_Exceptioon("Soil Porosity0 must be between 0 and 1 for GPU pore-pressure boundary operator.");
  if(SoilCte.WaterBulkModulus<=0.f)Run_Exceptioon("Soil WaterBulkModulus must be greater than zero for GPU pore-pressure boundary operator.");
  const double topthick=(PorePressureDrainThickness>0.f? double(PorePressureDrainThickness): double(KernelH));
  const double bottomthick=(PorePressureBottomNoFluxThickness>0.f? double(PorePressureBottomNoFluxThickness): double(KernelH));
  if((PorePressureTopDrained && topthick<=0.) || (PorePressureBottomNoFlux && bottomthick<=0.))
    Run_Exceptioon("GPU pore-pressure boundary operator requires positive boundary thickness or KernelH.");
  const tfloat3 hg=GetHydraulicGravity();

  float *zmaxg=ArraysGpu->ReserveFloat();
  float *negzming=ArraysGpu->ReserveFloat();
  float *auxmem=NULL;
  const unsigned auxsize=max(cusph::ReduMaxFloatSize(nfluid),cusph::ReduSumFloatSize(nfluid));
  cudaMalloc((void**)&auxmem,sizeof(float)*auxsize);
  Check_CudaErroor("Failed allocating GPU pore-pressure boundary operator reduction memory.");
  cusph::PreparePorePressureBoundaryElevations(nfluid,Npb,Codeg,Posxyg,Poszg,hg.x,hg.y,hg.z,gmag,zmaxg,negzming);
  Check_CudaErroor("Failed preparing GPU pore-pressure boundary operator elevations.");
  const float zmaxf=cusph::ReduMaxFloat(nfluid,Npb,zmaxg,auxmem);
  const float negzminf=cusph::ReduMaxFloat(nfluid,Npb,negzming,auxmem);
  ArraysGpu->Free(zmaxg);
  ArraysGpu->Free(negzming);
  if(zmaxf<=-FLT_MAX/4.f || negzminf<=-FLT_MAX/4.f){
    cudaFree(auxmem);
    if(printlog)Log->PrintWarning("GPU pore-pressure boundary operator found no material particles.");
    return(0);
  }

  float *topaffectedg=(printlog? ArraysGpu->ReserveFloat(): NULL);
  float *bottomaffectedg=(printlog? ArraysGpu->ReserveFloat(): NULL);
  const double zmin=-double(negzminf);
  const double zmax=double(zmaxf);
  const double gap=(Dp>0.? 0.5*double(Dp): 0.25*double(KernelSize));
  const bool topactive=(PorePressureTopDrained && TimeStep>=PorePressureTopDrainedStartTime);
  const bool bottomactive=PorePressureBottomNoFlux;
  cusph::ApplyPorePressureBoundaryOperator(TKernel
    ,nfluid,Npb,Codeg,Posxyg,Poszg,Velrhopg,PorePressg
    ,hg.x,hg.y,hg.z,gmag,PorePressureWaterLevel,SoilCte.WaterDensity
    ,SoilCte.Porosity0,SoilCte.HydraulicConductivity,SoilCte.WaterBulkModulus
    ,zmin,zmax,gap,topthick,bottomthick,topactive,bottomactive
    ,DivVelg,LapPorePressg,LapZg,PorePressRateg,topaffectedg,bottomaffectedg);
  Check_CudaErroor("Failed applying GPU pore-pressure boundary operator.");

  unsigned topaffected=0,bottomaffected=0;
  if(printlog){
    if(topaffectedg){
      const float v=cusph::ReduSumFloat(nfluid,Npb,topaffectedg,auxmem);
      topaffected=unsigned(v+0.5f);
      ArraysGpu->Free(topaffectedg);
    }
    if(bottomaffectedg){
      const float v=cusph::ReduSumFloat(nfluid,Npb,bottomaffectedg,auxmem);
      bottomaffected=unsigned(v+0.5f);
      ArraysGpu->Free(bottomaffectedg);
    }
  }
  cudaFree(auxmem);

  if(printlog){
    Log->Printf("GPU pore-pressure boundary operator: TimeStep=%g, top_active=%s, bottom_active=%s, zmin=%g, zmax=%g, gap=%g, top_thickness=%g, bottom_thickness=%g, top_contrib=%u, bottom_contrib=%u."
      ,TimeStep,(topactive? "True": "False"),(bottomactive? "True": "False"),zmin,zmax,gap,topthick,bottomthick,topaffected,bottomaffected);
    Log->Print("GPU pore-pressure boundary operator convention: top ghost enforces excess pressure = 0; bottom ghost mirrors excess pressure for zero normal hydraulic-head gradient. Legacy layer projection remains active after pressure update.");
  }
  return(topaffected+bottomaffected);
}

//==============================================================================
/// Computes GPU difference-gradient pore-pressure feedback acceleration.
//==============================================================================
void JSphGpu::ComputePorePressureAccelDiffGpu(){
  if(!HydromechCoupling || PorePressureModel!=1)return;
  if(!PorePressg || !PorePressureAceDiffg)return;
  if(!Np || !DivData.beginendcell)return;
  if(PorePressureFeedbackMode!=0 && PorePressureFeedbackMode!=1)
    Run_Exceptioon("PorePressureFeedbackMode is not valid for GPU pore-pressure feedback.");
  const float waterdensity=SoilCte.WaterDensity;
  if(waterdensity<=0.f)Run_Exceptioon("Soil WaterDensity must be greater than zero for GPU pore-pressure feedback.");
  const double gmag=GetHydraulicGmag();
  if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for GPU pore-pressure feedback.");
  const tfloat3 hg=GetHydraulicGravity();
  const unsigned bsfluid=(BlockSizes.forcesfluid? BlockSizes.forcesfluid: SPHBSIZE);
  cusph::ComputePorePressureAccelDiff(TKernel,Symmetry,bsfluid
    ,Np-Npb,Npb,DivData,Dcellg,Posxyg,Poszg,PosCellg,Velrhopg,Codeg,PorePressg
    ,hg.x,hg.y,hg.z,gmag,PorePressureWaterLevel,waterdensity,unsigned(PorePressureFeedbackMode),PorePressureAceDiffg);
  Check_CudaErroor("Failed computing GPU difference-gradient pore-pressure feedback acceleration.");
}

//==============================================================================
/// Adds GPU difference-gradient pore-pressure feedback acceleration to Aceg.
//==============================================================================
void JSphGpu::ApplyPorePressureFeedbackGpu(){
  if(!HydromechCoupling || PorePressureModel!=1 || !PorePressureFeedback)return;
  if(PorePressureFeedbackStartTime>0. || PorePressureFeedbackRampEndTime>0. || PorePressureFeedbackScale!=1. || HasNonDefaultPorePressureFeedbackStabilization())
    Run_Exceptioon("GPU pore-pressure feedback gating/stabilization diagnostics are not supported. Use default feedback timing/stabilization or run CPU.");
  if(PorePressureFeedbackOperator!=1)
    Run_Exceptioon("GPU pore-pressure feedback currently supports PorePressureFeedbackOperator=1 only.");
  if(!PorePressureAceDiffg)Run_Exceptioon("GPU pore-pressure feedback acceleration array is not allocated.");
  cusph::ApplyPorePressureFeedback(Np-Npb,Npb,Codeg,PorePressureAceDiffg,Aceg);
  Check_CudaErroor("Failed applying GPU difference-gradient pore-pressure feedback acceleration.");
}

//==============================================================================
/// Applies GPU hydromechanical kinematic damping to material particles.
//==============================================================================
unsigned JSphGpu::ApplyHydromechDampingGpu(bool printlog){
  if(!HydromechCoupling || PorePressureModel!=1 || !PorePressureFeedback || !HydromechDamping || HydromechDampingCoef<=0.f || !Aceg)return(0);
  if(TimeStep<HydromechDampingStartTime)return(0);
  if(HydromechDampingEndTime>HydromechDampingStartTime && TimeStep>HydromechDampingEndTime)return(0);
  const unsigned nfluid=(Np>Npb? Np-Npb: 0);
  if(!nfluid)return(0);

  float *dampmag=ArraysGpu->ReserveFloat();
  float *auxmem=NULL;
  cudaMalloc((void**)&auxmem,sizeof(float)*cusph::ReduMaxFloatSize(nfluid));
  Check_CudaErroor("Failed allocating GPU hydromechanical damping reduction memory.");
  cusph::ApplyHydromechDamping(nfluid,Npb,double(HydromechDampingCoef),Codeg,Velrhopg,Aceg,dampmag);
  Check_CudaErroor("Failed applying GPU hydromechanical damping.");
  const float amax=cusph::ReduMaxFloat(nfluid,Npb,dampmag,auxmem);
  ArraysGpu->Free(dampmag);
  cudaFree(auxmem);
  if(printlog && amax>0.f){
    Log->Printf("Hydromechanical damping activated on GPU at TimeStep=%g: coef=%g 1/s, start=%g, end=%g, max acceleration magnitude=%g m/s2."
      ,TimeStep,HydromechDampingCoef,HydromechDampingStartTime,HydromechDampingEndTime,double(amax));
  }
  return(amax>0.f? 1u: 0u);
}

//==============================================================================
/// Updates passive GPU pore pressure explicitly for material particles.
//==============================================================================
void JSphGpu::UpdatePorePressureGpu(double dt){
  if(!HydromechCoupling || PorePressureModel!=1 || !PorePressg || !PorePressRateg)return;
  if(PorePressureDtActive && dt>PorePressureDt*(1.+1.e-6) && !PorePressureUpdateDtPrint){
    Log->PrintWarning(fun::PrintStr("GPU pore-pressure update dt=%g is greater than dt_pore=%g. This can occur on the first Symplectic step before the next-step dt restriction is applied.",dt,PorePressureDt));
    PorePressureUpdateDtPrint=true;
  }
  cusph::UpdatePorePressure(Np-Npb,Npb,Codeg,dt,PorePressg,PorePressRateg);
  Check_CudaErroor("Failed updating GPU pore pressure.");
}

//==============================================================================
/// Applies optional GPU Shepard regularization to pore pressure on material particles.
//==============================================================================
unsigned JSphGpu::ApplyPorePressureShepardGpu(unsigned step,bool printlog){
  if(!HydromechCoupling || PorePressureModel!=1 || !PorePressureShepard || !PorePressureShepardInterval || !PorePressg)return(0);
  if(!PorePressShepardTmpg)Run_Exceptioon("GPU pore-pressure Shepard temporary array is not allocated.");
  if(PorePressureShepardMode==1 && GetHydraulicGmag()<=0.)
    Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for GPU excess pore-pressure Shepard regularization.");
  if(!Np || !DivData.beginendcell)return(0);
  const float waterdensity=SoilCte.WaterDensity;
  if(waterdensity<=0.f)Run_Exceptioon("Soil WaterDensity must be greater than zero for GPU pore-pressure Shepard regularization.");
  const double gmag=GetHydraulicGmag();
  const tfloat3 hg=GetHydraulicGravity();
  const unsigned bsfluid=(BlockSizes.forcesfluid? BlockSizes.forcesfluid: SPHBSIZE);
  cusph::ApplyPorePressureShepard(TKernel,Symmetry,bsfluid
    ,Np-Npb,Npb,DivData,Dcellg,Posxyg,Poszg,PosCellg,Velrhopg,Codeg,PorePressg
    ,hg.x,hg.y,hg.z,gmag,PorePressureWaterLevel,waterdensity,unsigned(PorePressureShepardMode),PorePressShepardTmpg);
  cusph::CopyPorePressureShepard(Np-Npb,Npb,Codeg,PorePressShepardTmpg,PorePressg);
  Check_CudaErroor("Failed applying GPU pore-pressure Shepard regularization.");
  if(printlog){
    Log->Printf("Pore-pressure Shepard regularization applied on GPU: step=%u, TimeStep=%g, mode=%s, interval=%u."
      ,step,TimeStep,(PorePressureShepardMode==1? "ExcessPressure": "TotalPressure"),PorePressureShepardInterval);
  }
  return(1);
}

//==============================================================================
/// Applies GPU top drained condition to the total pore-pressure state.
//==============================================================================
unsigned JSphGpu::ApplyPorePressureTopDrainedGpu(double timestep,const char *stage,bool printlog){
  if(!HydromechCoupling || PorePressureModel!=1 || !PorePressureTopDrained || !PorePressg)return(0);
  if(timestep<PorePressureTopDrainedStartTime)return(0);
  const unsigned nfluid=(Np>Npb? Np-Npb: 0);
  if(!nfluid)return(0);
  const double gmag=GetHydraulicGmag();
  if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for GPU top drained pore-pressure boundary.");
  if(SoilCte.WaterDensity<=0.f)Run_Exceptioon("Soil WaterDensity must be greater than zero for GPU top drained pore-pressure boundary.");
  const double drainthick=(PorePressureDrainThickness>0.f? double(PorePressureDrainThickness): double(KernelH));
  if(drainthick<=0.)Run_Exceptioon("GPU top drained pore-pressure boundary requires a positive drain thickness or KernelH.");
  const tfloat3 hg=GetHydraulicGravity();

  float *zmaxg=ArraysGpu->ReserveFloat();
  float *auxmem=NULL;
  cudaMalloc((void**)&auxmem,sizeof(float)*cusph::ReduMaxFloatSize(nfluid));
  Check_CudaErroor("Failed allocating GPU top drained reduction memory.");
  cusph::PreparePorePressureBoundaryElevations(nfluid,Npb,Codeg,Posxyg,Poszg,hg.x,hg.y,hg.z,gmag,zmaxg,NULL);
  Check_CudaErroor("Failed preparing GPU top drained boundary elevations.");
  const float zmaxf=cusph::ReduMaxFloat(nfluid,Npb,zmaxg,auxmem);
  ArraysGpu->Free(zmaxg);
  zmaxg=NULL;
  if(zmaxf<=-FLT_MAX/4.f){
    cudaFree(auxmem);
    if(printlog)Log->PrintWarning("GPU top drained pore-pressure boundary found no material particles.");
    return(0);
  }
  const double zmax=double(zmaxf);
  const double zthreshold=zmax-drainthick;

  float *affectedg=ArraysGpu->ReserveFloat();
  cusph::ApplyPorePressureTopDrained(nfluid,Npb,Codeg,Posxyg,Poszg,hg.x,hg.y,hg.z,gmag
    ,PorePressureWaterLevel,SoilCte.WaterDensity,zthreshold,PorePressg,affectedg);
  Check_CudaErroor("Failed applying GPU top drained pore-pressure boundary.");
  const float affectedf=cusph::ReduSumFloat(nfluid,Npb,affectedg,auxmem);
  ArraysGpu->Free(affectedg);
  cudaFree(auxmem);
  const unsigned affected=unsigned(affectedf+0.5f);

  if(printlog){
    Log->Printf("Top drained pore-pressure boundary activated on GPU (%s): TimeStep=%g, start_time=%g, zmax_material=%g, drain_thickness=%g, z_threshold=%g, affected=%u."
      ,(stage? stage: "unknown"),timestep,PorePressureTopDrainedStartTime,zmax,drainthick,zthreshold,affected);
    if(double(PorePressureWaterLevel)<zmax)Log->PrintWarning(fun::PrintStr("GPU top drained pore-pressure boundary is used with WaterLevel=%g below top elevation=%g.",PorePressureWaterLevel,zmax));
  }
  return(affected);
}

//==============================================================================
/// Applies GPU bottom no-flux layer correction to the total pore-pressure state.
//==============================================================================
unsigned JSphGpu::ApplyPorePressureBottomNoFluxGpu(const char *stage,bool printlog){
  if(!HydromechCoupling || PorePressureModel!=1 || !PorePressureBottomNoFlux || !PorePressg)return(0);
  const unsigned nfluid=(Np>Npb? Np-Npb: 0);
  if(!nfluid)return(0);
  const double gmag=GetHydraulicGmag();
  if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for GPU bottom no-flux pore-pressure boundary.");
  if(SoilCte.WaterDensity<=0.f)Run_Exceptioon("Soil WaterDensity must be greater than zero for GPU bottom no-flux pore-pressure boundary.");
  const double bottomthick=(PorePressureBottomNoFluxThickness>0.f? double(PorePressureBottomNoFluxThickness): double(KernelH));
  if(bottomthick<=0.)Run_Exceptioon("GPU bottom no-flux pore-pressure boundary requires a positive thickness or KernelH.");
  const tfloat3 hg=GetHydraulicGravity();

  float *negzming=ArraysGpu->ReserveFloat();
  float *auxmem=NULL;
  const unsigned auxsize=max(cusph::ReduMaxFloatSize(nfluid),cusph::ReduSumFloatSize(nfluid));
  cudaMalloc((void**)&auxmem,sizeof(float)*auxsize);
  Check_CudaErroor("Failed allocating GPU bottom no-flux reduction memory.");
  cusph::PreparePorePressureBoundaryElevations(nfluid,Npb,Codeg,Posxyg,Poszg,hg.x,hg.y,hg.z,gmag,NULL,negzming);
  Check_CudaErroor("Failed preparing GPU bottom no-flux boundary elevations.");
  const float negzminf=cusph::ReduMaxFloat(nfluid,Npb,negzming,auxmem);
  ArraysGpu->Free(negzming);
  negzming=NULL;
  if(negzminf<=-FLT_MAX/4.f){
    cudaFree(auxmem);
    if(printlog)Log->PrintWarning("GPU bottom no-flux pore-pressure boundary found no material particles.");
    return(0);
  }
  const double zmin=-double(negzminf);
  const double zthreshold=zmin+bottomthick;
  const double zrefmax=zmin+2.*bottomthick;

  float *refexcessg=ArraysGpu->ReserveFloat();
  float *refcountg=ArraysGpu->ReserveFloat();
  float *bottomcountg=ArraysGpu->ReserveFloat();
  cusph::PreparePorePressureBottomNoFlux(nfluid,Npb,Codeg,Posxyg,Poszg,hg.x,hg.y,hg.z,gmag
    ,PorePressureWaterLevel,SoilCte.WaterDensity,zmin,bottomthick,PorePressg,refexcessg,refcountg,bottomcountg);
  Check_CudaErroor("Failed preparing GPU bottom no-flux pore-pressure reference layer.");
  const float refsumf=cusph::ReduSumFloat(nfluid,Npb,refexcessg,auxmem);
  const float refcountf=cusph::ReduSumFloat(nfluid,Npb,refcountg,auxmem);
  const float bottomcountf=cusph::ReduSumFloat(nfluid,Npb,bottomcountg,auxmem);
  ArraysGpu->Free(refexcessg);
  ArraysGpu->Free(refcountg);
  ArraysGpu->Free(bottomcountg);
  const unsigned refcount=unsigned(refcountf+0.5f);
  if(!refcount){
    cudaFree(auxmem);
    if(printlog)Log->PrintWarning(fun::PrintStr("GPU bottom no-flux pore-pressure boundary (%s) skipped: reference layer has no material particles. zmin=%g, reference=[%g,%g]."
      ,(stage? stage: "unknown"),zmin,zthreshold,zrefmax));
    return(0);
  }
  const double excessmean=double(refsumf)/double(refcountf);

  float *affectedg=ArraysGpu->ReserveFloat();
  cusph::ApplyPorePressureBottomNoFlux(nfluid,Npb,Codeg,Posxyg,Poszg,hg.x,hg.y,hg.z,gmag
    ,PorePressureWaterLevel,SoilCte.WaterDensity,zthreshold,excessmean,PorePressg,affectedg);
  Check_CudaErroor("Failed applying GPU bottom no-flux pore-pressure boundary.");
  const float affectedf=cusph::ReduSumFloat(nfluid,Npb,affectedg,auxmem);
  ArraysGpu->Free(affectedg);
  cudaFree(auxmem);
  const unsigned affected=unsigned(affectedf+0.5f);

  if(printlog){
    Log->Printf("Bottom no-flux pore-pressure boundary on GPU (%s): zmin_material=%g, bottom_thickness=%g, z_threshold=%g, reference=[%g,%g], affected=%u, bottom_count=%u, reference_count=%u, excess_ref_mean=%g Pa."
      ,(stage? stage: "unknown"),zmin,bottomthick,zthreshold,zthreshold,zrefmax,affected,unsigned(bottomcountf+0.5f),refcount,excessmean);
  }
  return(affected);
}

//==============================================================================
/// Recovers particle data from the GPU and returns the particle number that
/// are less than n if the paeriodic particles are removed.
/// - code: Recovers data of Codeg.
/// - onlynormal: Onlly retains the normal particles, removes the periodic ones.
///
/// Recupera datos de particulas de la GPU y devuelve el numero de particulas que
/// sera menor que n si se eliminaron las periodicas.
/// - code: Recupera datos de Codeg.
/// - onlynormal: Solo se queda con las normales, elimina las particulas periodicas.
//==============================================================================
unsigned JSphGpu::ParticlesDataDown(unsigned n,unsigned pini,bool code,bool onlynormal){
  unsigned num=n;
  cudaMemcpy(Idp    ,Idpg    +pini,sizeof(unsigned)*n,cudaMemcpyDeviceToHost);
  cudaMemcpy(Posxy  ,Posxyg  +pini,sizeof(double2) *n,cudaMemcpyDeviceToHost);
  cudaMemcpy(Posz   ,Poszg   +pini,sizeof(double)  *n,cudaMemcpyDeviceToHost);
  cudaMemcpy(Velrhop,Velrhopg+pini,sizeof(float4)  *n,cudaMemcpyDeviceToHost);
  if(code || onlynormal)cudaMemcpy(Code,Codeg+pini,sizeof(typecode)*n,cudaMemcpyDeviceToHost);
  //==mdbr
  cudaMemcpy(Sigma,Sigmag+pini,sizeof(tsymatrix3f)*n,cudaMemcpyDeviceToHost);
  cudaMemcpy(Kplastic,Kplasticg+pini,sizeof(float)*n,cudaMemcpyDeviceToHost);
  //
  Check_CudaErroor("Failed copying data from GPU.");
  //-Eliminates abnormal particles (periodic and others). | Elimina particulas no normales (periodicas y otras).
  if(onlynormal){
    unsigned ndel=0;
    for(unsigned p=0;p<n;p++){
      const bool normal=CODE_IsNormal(Code[p]);
      if(ndel && normal){
        Idp[p-ndel]    =Idp[p];
        Posxy[p-ndel]  =Posxy[p];
        Posz[p-ndel]   =Posz[p];
        Velrhop[p-ndel]=Velrhop[p];
        Code[p-ndel]   =Code[p];
        //==== mdbr
		Sigma[p-ndel]  =Sigma[p];
        Kplastic[p-ndel] = Kplastic[p];
      }
      if(!normal)ndel++;
    }
    num-=ndel;
  }
  //-Converts data to a simple format. | Convierte datos a formato simple.
  for(unsigned p=0;p<n;p++){
    AuxPos[p]=TDouble3(Posxy[p].x,Posxy[p].y,Posz[p]);
    AuxVel[p]=TFloat3(Velrhop[p].x,Velrhop[p].y,Velrhop[p].z);
    AuxRhop[p]=Velrhop[p].w;
    //==== mdbr
    AuxSigma_xx_yy_zz[p]=TFloat3(Sigma[p].xx,Sigma[p].yy,Sigma[p].zz);
    AuxSigma_xy_yz_xz[p]=TFloat3(Sigma[p].xy,Sigma[p].yz,Sigma[p].xz);
    AuxKplastic[p]=Kplastic[p];
  }
  return(num);
}

//==============================================================================
/// Initialises CUDA device.
/// Inicializa dispositivo CUDA.
//==============================================================================
void JSphGpu::SelecDevice(int gpuid){
  //-Shows information on available GPUs.
  JDsGpuInfo::ShowGpusInfo(Log);
  //-GPU selection.
  Log->Print("[GPU Hardware]");
  GpuInfo->SelectGpu(gpuid);
  GpuInfo->ShowSelectGpusInfo(Log);
  cudaSetDevice(GpuInfo->GetGpuId());
}

//==============================================================================
/// Configures BlockSize for main interaction CUDA kernels.
//==============================================================================
void JSphGpu::ConfigBlockSizes(bool usezone,bool useperi){
  Log->Print(" ");
  BlockSizesStr="";
  if(CellMode==CELLMODE_Full || CellMode==CELLMODE_Half){
    const bool lamsps=(TVisco==VISCO_LaminarSPS);
    BlockSizes.forcesbound=BlockSizes.forcesfluid=BlockSizes.forcesdem=BSIZE_FORCES;
    //-Collects kernel information.
    StKerInfo kerinfo;
    memset(&kerinfo,0,sizeof(StKerInfo));
    StDivDataGpu divdatag;
    memset(&divdatag,0,sizeof(StDivDataGpu));
    #ifndef DISABLE_BSMODES
      const StInterParmsg parms=StrInterParmsg(Simulate2D
        ,Symmetry  //<vs_syymmetry>
        ,TKernel,FtMode
        ,lamsps,TDensity,ShiftingMode
        ,0,0,0,0,100,0,0
        ,0,0,divdatag,NULL
        ,NULL,NULL,NULL,NULL,NULL,NULL
        ,NULL,NULL,NULL
        ,NULL,NULL,NULL,NULL
        ,NULL,NULL,NULL,NULL
        ,NULL
        ,NULL,&kerinfo);
      cusph::Interaction_Forces(parms);
      if(UseDEM)cusph::Interaction_ForcesDem(BlockSizes.forcesdem,CaseNfloat,divdatag,NULL,NULL,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,&kerinfo);
    #endif
    //Log->Printf("====> bound -> rg:%d  bs:%d  bsmax:%d",kerinfo.forcesbound_rg,kerinfo.forcesbound_bs,kerinfo.forcesbound_bsmax);
    //Log->Printf("====> fluid -> rg:%d  bs:%d  bsmax:%d",kerinfo.forcesfluid_rg,kerinfo.forcesfluid_bs,kerinfo.forcesfluid_bsmax);
    //Log->Printf("====> dem   -> rg:%d  bs:%d  bsmax:%d",kerinfo.forcesdem_rg  ,kerinfo.forcesdem_bs  ,kerinfo.forcesdem_bsmax);
    Log->Printf("BlockSize calculation mode: Fixed.");
    const string txb=fun::PrintStr("BsForcesBound=%d ",BlockSizes.forcesbound)+(kerinfo.forcesbound_rg? fun::PrintStr("(%d regs)",kerinfo.forcesbound_rg): string("(? regs)"));
    const string txf=fun::PrintStr("BsForcesFluid=%d ",BlockSizes.forcesfluid)+(kerinfo.forcesfluid_rg? fun::PrintStr("(%d regs)",kerinfo.forcesfluid_rg): string("(? regs)"));
    const string txd=fun::PrintStr("BsForcesDem=%d "  ,BlockSizes.forcesdem)  +(kerinfo.forcesdem_rg  ? fun::PrintStr("(%d regs)",kerinfo.forcesdem_rg  ): string("(? regs)"));
    Log->Print(string("  ")+txb);
    Log->Print(string("  ")+txf);
    if(UseDEM)Log->Print(string("  ")+txd);
    if(!BlockSizesStr.empty())BlockSizesStr=BlockSizesStr+" - ";
    BlockSizesStr=BlockSizesStr+txb+" - "+txf;
    if(UseDEM)BlockSizesStr=BlockSizesStr+" - "+txd;
  }
  else Run_Exceptioon("CellMode unrecognised.");
  Log->Print(" ");
}

//==============================================================================
/// Configures execution mode in the GPU.
/// Configura modo de ejecucion en GPU.
//==============================================================================
void JSphGpu::ConfigRunMode(){
  Hardware=GpuInfo->GetHardware();
  //-Defines RunMode.
  RunMode="";
  if(Stable)RunMode=RunMode+(!RunMode.empty()? " - ": "")+"Stable";
  RunMode=RunMode+(!RunMode.empty()? " - ": "")+"Pos-Cell";
  RunMode=RunMode+(!RunMode.empty()? " - ": "")+"Single-GPU";
  //-Shows RunMode.
  Log->Print(" ");
  Log->Print(fun::VarStr("RunMode",RunMode));
  Log->Print(" ");
}

//==============================================================================
/// Adjusts variables of particles of floating bodies.
//==============================================================================
void JSphGpu::InitFloating(){
  if(PartBegin){
    JPartFloatBi4Load ftdata;
    ftdata.LoadFile(PartBeginDir);
    //-Checks if the constant data match.
    //-Comprueba coincidencia de datos constantes.
    for(unsigned cf=0;cf<FtCount;cf++){
      const StFloatingData &ft=FtObjs[cf];
      ftdata.CheckHeadData(cf,ft.mkbound,ft.begin,ft.count,ft.mass,ft.massp);
    }
    //-Loads PART data.
    ftdata.LoadPart(PartBegin);
    for(unsigned cf=0;cf<FtCount;cf++){
      FtObjs[cf].center=ftdata.GetPartCenter(cf);
      FtObjs[cf].fvel  =ftdata.GetPartVelLin(cf);
      FtObjs[cf].fomega=ftdata.GetPartVelAng(cf);
      FtObjs[cf].radius=ftdata.GetHeadRadius(cf);
    }
    DemDtForce=ftdata.GetPartDemDtForce();
  }
  //-Copies massp values to GPU.
  {
    float *massp=new float[FtCount];
    for(unsigned cf=0;cf<FtCount;cf++)massp[cf]=FtObjs[cf].massp;
    cudaMemcpy(FtoMasspg,massp,sizeof(float)*FtCount,cudaMemcpyHostToDevice);
    delete[] massp;
  }
  //-Copies floating values to GPU.
  {
    typedef struct{
      unsigned pini;
      unsigned np;
      float radius;
      float massp;
    }stdata;

    stdata   *datp  =new stdata  [FtCount];
    float    *ftmass=new float   [FtCount];
    byte     *constr=new byte    [FtCount];
    tdouble3 *center=new tdouble3[FtCount];
    tfloat3  *angles=new tfloat3 [FtCount];
    tfloat3  *velace=new tfloat3 [FtCount*4];
    tfloat4  *inert8=new tfloat4 [FtCount*2];
    float    *inert1=new float   [FtCount];
    memset(velace,0,sizeof(tfloat3)*FtCount*4);
    for(unsigned cf=0;cf<FtCount;cf++){
      const StFloatingData &fobj=FtObjs[cf];
      datp[cf].pini=fobj.begin-CaseNpb;
      datp[cf].np=fobj.count;
      datp[cf].radius=fobj.radius;
      datp[cf].massp=fobj.massp;
      ftmass[cf]=fobj.mass;
      constr[cf]=fobj.constraints;
      center[cf]=fobj.center;
      angles[cf]=fobj.angles;
      velace[cf]=fobj.fvel;
      velace[FtCount+cf]=fobj.fomega;
      const tmatrix3f v=fobj.inertiaini;
      inert8[cf*2]  =TFloat4(v.a11,v.a12,v.a13,v.a21);
      inert8[cf*2+1]=TFloat4(v.a22,v.a23,v.a31,v.a32);
      inert1[cf]    =v.a33;
    }
    cudaMemcpy(FtoDatpg       ,datp  ,sizeof(float4)   *FtCount  ,cudaMemcpyHostToDevice);
    cudaMemcpy(FtoMassg       ,ftmass,sizeof(float)    *FtCount  ,cudaMemcpyHostToDevice);
    cudaMemcpy(FtoConstraintsg,constr,sizeof(byte)     *FtCount  ,cudaMemcpyHostToDevice);
    cudaMemcpy(FtoCenterg     ,center,sizeof(double3)  *FtCount  ,cudaMemcpyHostToDevice);
    cudaMemcpy(FtoAnglesg     ,angles,sizeof(float3)   *FtCount  ,cudaMemcpyHostToDevice);
    cudaMemcpy(FtoVelAceg     ,velace,sizeof(float3)   *FtCount*4,cudaMemcpyHostToDevice);
    cudaMemcpy(FtoInertiaini8g,inert8,sizeof(float4)   *FtCount*2,cudaMemcpyHostToDevice);
    cudaMemcpy(FtoInertiaini1g,inert1,sizeof(float)    *FtCount  ,cudaMemcpyHostToDevice);
    delete[] datp;
    delete[] ftmass;
    delete[] center;
    delete[] angles;
    delete[] velace;
    delete[] inert8;
    delete[] inert1;
  }
  //-Copies data object for DEM to GPU.
  if(UseDEM){ //(DEM)
    float4 *data=new float4[DemDataSize];
    for(unsigned c=0;c<DemDataSize;c++){
      data[c].x=DemData[c].mass;
      data[c].y=DemData[c].tau;
      data[c].z=DemData[c].kfric;
      data[c].w=DemData[c].restitu;
    }
    cudaMemcpy(DemDatag,data,sizeof(float4)*DemDataSize,cudaMemcpyHostToDevice);
    delete[] data;
  }
}

//==============================================================================
/// Initialises arrays and variables for the execution.
/// Inicializa vectores y variables para la ejecucion.
//==============================================================================
void JSphGpu::InitRunGpu(){
  if(ConfiningStressGradientMode==1)Run_Exceptioon("ConfiningStressGradientMode=1 is CPU-only in this branch. GPU support is not implemented.");
  if(FlexibleConfiningStress)Run_Exceptioon("FlexibleConfiningStress=1 is CPU-only in this branch. GPU support is not implemented.");
  ParticlesDataDown(Np,0,false,false);
  InitRun(Np,Idp,AuxPos);
  if(TStep==STEP_Symplectic)SymplecticDtPre=LimitInitialDtByPorePressure(SymplecticDtPre);

  if(TStep==STEP_Verlet){cudaMemcpy(VelrhopM1g,Velrhopg,sizeof(float4)*Np,cudaMemcpyDeviceToDevice);
  //======mdbr
  cudaMemcpy(SigmaM1g,Sigmag,sizeof(tsymatrix3f)*Np,cudaMemcpyDeviceToDevice);
  }
  if(TVisco==VISCO_LaminarSPS)cudaMemset(SpsTaug,0,sizeof(tsymatrix3f)*Np);
  if(CaseNfloat)InitFloating();
  if(MotionVelg)cudaMemset(MotionVelg,0,sizeof(float3)*Np);
  Check_CudaErroor("Failed initializing variables for execution.");
}

//==============================================================================
/// Applies pore-pressure stability restriction to the initial GPU timestep.
//==============================================================================
double JSphGpu::LimitInitialDtByPorePressure(double dt){
  if(!HydromechCoupling || PorePressureModel!=1)return(dt);
  double dtpore=DBL_MAX;
  bool dtporeactive=false;
  const float porosity0=SoilCte.Porosity0;
  const float hydraulicconductivity=SoilCte.HydraulicConductivity;
  const float waterbulkmodulus=SoilCte.WaterBulkModulus;
  const float waterdensity=SoilCte.WaterDensity;
  if(hydraulicconductivity>0.f && waterbulkmodulus>0.f && waterdensity>0.f && porosity0>0.f && porosity0<1.f && PorePressureDtSafety>0.f){
    const double gmag=GetHydraulicGmag();
    if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for GPU pore-pressure timestep restriction.");
    const double cw=double(waterdensity)*gmag*double(porosity0)/double(waterbulkmodulus);
    dtpore=double(PorePressureDtSafety)*cw*double(KernelH)*double(KernelH)/double(hydraulicconductivity);
    if(dtpore<=0. || fun::IsNAN(dtpore) || fun::IsInfinity(dtpore))Run_Exceptioon(fun::PrintStr("The computed GPU pore-pressure timestep is invalid (dt_pore=%g).",dtpore));
    dtporeactive=true;
    if(!PorePressureDtConfigPrint){
      Log->Printf("GPU pore-pressure timestep restriction: active=True, Cw=%g, dt_pore=%g, safety=%g, h(KernelH)=%g, hydraulic_gmag=%g.",cw,dtpore,PorePressureDtSafety,KernelH,gmag);
      if(FixedDt)Log->PrintWarning(fun::PrintStr("Fixed dt is enabled. Fixed dt should be <= GPU dt_pore=%g for PR pore-pressure update.",dtpore));
      PorePressureDtConfigPrint=true;
      PorePressureDtFixedPrint=(FixedDt!=NULL);
    }
  }
  else if(hydraulicconductivity==0.f){
    if(!PorePressureDtConfigPrint){
      Log->Print("GPU pore-pressure timestep restriction: active=False, disabled because HydraulicConductivity=0.");
      PorePressureDtConfigPrint=true;
    }
  }
  else if(hydraulicconductivity>0.f)Run_Exceptioon("Invalid hydromechanical parameters for GPU pore-pressure timestep restriction.");
  PorePressureDt=dtpore;
  PorePressureDtActive=dtporeactive;
  if(dtporeactive && dt>dtpore){
    Log->Printf("Initial GPU timestep limited by pore-pressure dt_pore: old_dt=%g, dt_pore=%g, new_dt=%g.",dt,dtpore,dtpore);
    dt=dtpore;
  }
  return(dt);
}

//==============================================================================
/// Prepares variables for interaction.
/// Prepara variables para interaccion.
//==============================================================================
void JSphGpu::PreInteractionVars_Forces(unsigned np,unsigned npb){
  //-Initialise arrays.
  const unsigned npf=np-npb;
  cudaMemset(ViscDtg,0,sizeof(float)*np);                                //ViscDtg[]=0
  cudaMemset(Arg,0,sizeof(float)*np);                                    //Arg[]=0
  if(Deltag)cudaMemset(Deltag,0,sizeof(float)*np);                       //Deltag[]=0
  cudaMemset(Aceg,0,sizeof(tfloat3)*np);                                 //Aceg[]=(0,0,0)
  if(SpsGradvelg)cudaMemset(SpsGradvelg+npb,0,sizeof(tsymatrix3f)*npf);  //SpsGradvelg[]=(0,0,0,0,0,0).
  //====mdbr
  cudaMemset(Rsigmag,0,sizeof(tsymatrix3f)*np);
  //======
  //-Select particles for shifting.
  if(ShiftPosfsg)Shifting->InitGpu(npf,npb,Posxyg,Poszg,ShiftPosfsg);

  //-Apply the extra forces to the correct particle sets.
  if(AccInput)AccInput->RunGpu(TimeStep,Gravity,npf,npb,Codeg,Posxyg,Poszg,Velrhopg,Aceg);
  if(IsMechanicalGravityStopped(TimeStep) && !BodyGravityStoppedLogged){
    Log->Print(fun::PrintStr("Mechanical body gravity stopped on GPU at TimeStep=%g. Hydraulic gravity remains active.",TimeStep));
    BodyGravityStoppedLogged=true;
  }
}

//==============================================================================
/// Prepares variables for interaction.
/// Prepara variables para interaccion.
//==============================================================================
void JSphGpu::PreInteraction_Forces(){
  Timersg->TmStart(TMG_CfPreForces,false);
  //-Assign memory.
  ViscDtg=ArraysGpu->ReserveFloat();
  Arg=ArraysGpu->ReserveFloat();
  Aceg=ArraysGpu->ReserveFloat3();
  Rsigmag=ArraysGpu->ReserveSymatrix3f();//ruofeng
  if(ArtificialStress)ArtificialStressg=ArraysGpu->ReserveSymatrix3f();
  if(DDTArray)Deltag=ArraysGpu->ReserveFloat();
  if(Shifting)ShiftPosfsg=ArraysGpu->ReserveFloat4();
  if(TVisco==VISCO_LaminarSPS)SpsGradvelg=ArraysGpu->ReserveSymatrix3f();

  //-Initialise arrays.
  PreInteractionVars_Forces(Np,Npb);
  if(ArtificialStressg)cusph::ComputeArtificialStress(Np,Npb,Codeg,Velrhopg,Sigmag,ArtificialStressg);

  //-Computes VelMax: Includes the particles from floating bodies and does not affect the periodic conditions.
  //-Calcula VelMax: Se incluyen las particulas floatings y no afecta el uso de condiciones periodicas.
  const unsigned pini=(DtAllParticles? 0: Npb);
  cusph::ComputeVelMod(Np-pini,Velrhopg+pini,ViscDtg);
  float velmax=cusph::ReduMaxFloat(Np-pini,0,ViscDtg,CellDiv->GetAuxMem(cusph::ReduMaxFloatSize(Np-pini)));
  VelMax=sqrt(velmax);
  cudaMemset(ViscDtg,0,sizeof(float)*Np);           //ViscDtg[]=0
  ViscDtMax=0;
  Timersg->TmStop(TMG_CfPreForces,true);
  Check_CudaErroor("Failed calculating VelMax.");
}

//==============================================================================
/// Frees memory allocated for ArraysGpu.
/// Libera memoria asignada de ArraysGpu.
//==============================================================================
void JSphGpu::PosInteraction_Forces(){
  //-Frees memory allocated in PreInteraction_Forces().
  ArraysGpu->Free(Arg);          Arg=NULL;
  ArraysGpu->Free(Aceg);         Aceg=NULL;
  ArraysGpu->Free(ViscDtg);      ViscDtg=NULL;
  ArraysGpu->Free(Deltag);       Deltag=NULL;
  ArraysGpu->Free(ShiftPosfsg);  ShiftPosfsg=NULL;
  ArraysGpu->Free(SpsGradvelg);  SpsGradvelg=NULL;
  ArraysGpu->Free(Rsigmag);      Rsigmag=NULL;//ruofeng
  ArraysGpu->Free(ArtificialStressg); ArtificialStressg=NULL;//mdbr
}

//==============================================================================
/// Updates particles according to forces and dt using Verlet.
/// Actualizacion de particulas segun fuerzas y dt usando Verlet.
//==============================================================================
void JSphGpu::ComputeVerlet(double dt){  //pdtedom
  Timersg->TmStart(TMG_SuComputeStep,false);
  const bool shift=(ShiftingMode!=SHIFT_None);
  const bool inout=(InOut!=NULL);
  const float3 *indirvel=(inout? InOut->GetDirVelg(): NULL);
  const tfloat3 mechgravity=GetMechanicalGravity(TimeStep);
  VerletStep++;
  //-Allocates memory to compute the displacement.
  //-Asigna memoria para calcular el desplazamiento.
  double2 *movxyg=ArraysGpu->ReserveDouble2();
  double *movzg=ArraysGpu->ReserveDouble();
  //-Computes displacement, velocity and density.
  //-Calcula desplazamiento, velocidad y densidad.
  if(VerletStep<VerletSteps){
    cusphs::ComputeStepVerlet(WithFloating,shift,inout,DPCtes,Np,Npb,Velrhopg,VelrhopM1g,SigmaM1g,Kplasticg,Rsigmag,Arg
      ,Aceg,ShiftPosfsg,indirvel,dt,dt+dt,RhopZero,RhopOutMin,RhopOutMax,mechgravity,Codeg,movxyg,movzg,VelrhopM1g,SigmaM1g,Kplasticg,NULL);
  }
  else{
    cusphs::ComputeStepVerlet(WithFloating,shift,inout,DPCtes,Np,Npb,Velrhopg,Velrhopg,Sigmag,Kplasticg,Rsigmag,Arg
      ,Aceg,ShiftPosfsg,indirvel,dt,dt,RhopZero,RhopOutMin,RhopOutMax,mechgravity,Codeg,movxyg,movzg,VelrhopM1g,SigmaM1g,Kplasticg,NULL);
    VerletStep=0;
  }
  //-The new values are calculated in VelRhopM1g.
  //-Los nuevos valores se calculan en VelrhopM1g.
  swap(Velrhopg,VelrhopM1g);   //-Exchanges Velrhopg and VelrhopM1g. | Intercambia Velrhopg y VelrhopM1g.
  //==== mdbr
  swap(Sigmag,SigmaM1g);
  //-Applies displacement to non-periodic fluid particles.
  //-Aplica desplazamiento a las particulas fluid no periodicas.
  cusph::ComputeStepPos(PeriActive,WithFloating,Np,Npb,movxyg,movzg,Posxyg,Poszg,Dcellg,Codeg);
  //-Frees memory allocated for the diplacement.
  ArraysGpu->Free(movxyg);   movxyg=NULL;
  ArraysGpu->Free(movzg);    movzg=NULL;
  Timersg->TmStop(TMG_SuComputeStep,false);
}

//==============================================================================
/// Updates particles according to forces and dt using Symplectic-Predictor.
/// Actualizacion de particulas segun fuerzas y dt usando Symplectic-Predictor.
//==============================================================================
void JSphGpu::ComputeSymplecticPre(double dt){
  Timersg->TmStart(TMG_SuComputeStep,false);
  const bool shift=false; //(ShiftingMode!=SHIFT_None); //-We strongly recommend running the shifting correction only for the corrector. If you want to re-enable shifting in the predictor, change the value here to "true".
  const bool inout=(InOut!=NULL);
  const tfloat3 mechgravity=GetMechanicalGravity(TimeStep);
  //-Allocates memory to PRE variables.
  PosxyPreg=ArraysGpu->ReserveDouble2();
  PoszPreg=ArraysGpu->ReserveDouble();
  VelrhopPreg=ArraysGpu->ReserveFloat4();
  //==== mdbr
  SigmaPreg=ArraysGpu->ReserveSymatrix3f();
  //-Changes data of PRE variables for calculating the new data.
  //-Cambia datos a variables PRE para calcular nuevos datos.
  swap(PosxyPreg,Posxyg);      //-PosxyPre[] <= Posxy[]
  swap(PoszPreg,Poszg);        //-PoszPre[] <= Posz[]
  swap(VelrhopPreg,Velrhopg);  //-VelrhopPre[] <= Velrhop[]
  //==== mdbr
  swap(SigmaPreg,Sigmag);
  //-Allocate memory to compute the diplacement.
  double2 *movxyg=ArraysGpu->ReserveDouble2();
  double *movzg=ArraysGpu->ReserveDouble();
  //-Compute displacement, velocity and density.
  const double dt05=dt*.5;
  const float3 *indirvel=(InOut? InOut->GetDirVelg(): NULL);
  cusphs::ComputeStepSymplecticPre(WithFloating,shift,inout,DPCtes,Np,Npb,VelrhopPreg,Arg
    ,Aceg,ShiftPosfsg,SigmaPreg,Kplasticg,Rsigmag,indirvel,dt05,RhopZero,RhopOutMin,RhopOutMax,mechgravity
    ,Codeg,movxyg,movzg,Velrhopg,Sigmag,Kplasticg,NULL);

  //-Applies displacement to non-periodic fluid particles.
  //-Aplica desplazamiento a las particulas fluid no periodicas.
  cusph::ComputeStepPos2(PeriActive,WithFloating,Np,Npb,PosxyPreg,PoszPreg
    ,movxyg,movzg,Posxyg,Poszg,Dcellg,Codeg);
  //-Frees memory allocated for the displacement.
  ArraysGpu->Free(movxyg);   movxyg=NULL;
  ArraysGpu->Free(movzg);    movzg=NULL;
  //-Copies previous position of the boundaries.
  //-Copia posicion anterior del contorno.
  cudaMemcpy(Posxyg,PosxyPreg,sizeof(double2)*Npb,cudaMemcpyDeviceToDevice);
  cudaMemcpy(Poszg,PoszPreg,sizeof(double)*Npb,cudaMemcpyDeviceToDevice);
  Timersg->TmStop(TMG_SuComputeStep,false);
}

//==============================================================================
/// Updates particles according to forces and dt using Symplectic-Corrector.
/// Actualizacion de particulas segun fuerzas y dt usando Symplectic-Corrector.
//==============================================================================
void JSphGpu::ComputeSymplecticCorr(double dt){
  Timersg->TmStart(TMG_SuComputeStep,false);
  const bool shift=(ShiftingMode!=SHIFT_None);
  const bool inout=(InOut!=NULL);
  const tfloat3 mechgravity=GetMechanicalGravity(TimeStep);
  //-Allocates memory to calculate the displacement.
  double2 *movxyg=ArraysGpu->ReserveDouble2();
  double *movzg=ArraysGpu->ReserveDouble();
  //-Computes displacement, velocity and density.
  const double dt05=dt*.5;
  const float3 *indirvel=(InOut? InOut->GetDirVelg(): NULL);
  cusphs::ComputeStepSymplecticCor(WithFloating,shift,inout,DPCtes,Np,Npb,VelrhopPreg
    ,Arg,Aceg,ShiftPosfsg,SigmaPreg,Kplasticg,Rsigmag,indirvel,dt05,dt,RhopZero,RhopOutMin,RhopOutMax,mechgravity
    ,Codeg,movxyg,movzg,Velrhopg,Sigmag,Kplasticg,NULL);

  //-Applies displacement to non-periodic fluid particles.
  //-Aplica desplazamiento a las particulas fluid no periodicas.
  cusph::ComputeStepPos2(PeriActive,WithFloating,Np,Npb,PosxyPreg,PoszPreg
    ,movxyg,movzg,Posxyg,Poszg,Dcellg,Codeg);
  //-Frees memory allocated for diplacement.
  ArraysGpu->Free(movxyg);   movxyg=NULL;
  ArraysGpu->Free(movzg);    movzg=NULL;
  //-Frees memory allocated for the predictor variables in ComputeSymplecticPre().
  ArraysGpu->Free(PosxyPreg);    PosxyPreg=NULL;
  ArraysGpu->Free(PoszPreg);     PoszPreg=NULL;
  ArraysGpu->Free(VelrhopPreg);  VelrhopPreg=NULL;
  //==== mdbr
  ArraysGpu->Free(SigmaPreg);	SigmaPreg = NULL;
  //====
  Timersg->TmStop(TMG_SuComputeStep,false);
}

//==============================================================================
/// Computes the variable Dt.
/// Calcula un Dt variable.
//==============================================================================
double JSphGpu::DtVariable(bool final){
  //-dt1 depends on force per unit mass.
  const double acemax=sqrt(double(AceMax));
  const double dt1=(AceMax? (sqrt(double(KernelH)/AceMax)): DBL_MAX); 
  //-dt2 combines the Courant and the viscous time-step controls.
  const double dt2=double(KernelH)/(max(Cs0,VelMax*10.)+double(KernelH)*ViscDtMax);
  //-dt new value of time step.
  double dt=CFLnumber*min(dt1,dt2);
  if(FixedDt)dt=FixedDt->GetDt(TimeStep,dt);
  if(fun::IsNAN(dt) || fun::IsInfinity(dt))Run_Exceptioon(fun::PrintStr("The computed Dt=%f (from AceMax=%f, VelMax=%f, ViscDtMax=%f) is NaN or infinity at nstep=%u.",dt,AceMax,VelMax,ViscDtMax,Nstep));
  if(dt<double(DtMin)){ 
    dt=double(DtMin); DtModif++;
    if(DtModif>=DtModifWrn){
      Log->PrintfWarning("%d DTs adjusted to DtMin (t:%g, nstep:%u)",DtModif,TimeStep,Nstep);
      DtModifWrn*=10;
    }
  }
  //-Pore-pressure stability timestep restriction for saturated u-pw PR GPU prototype.
  double dtpore=DBL_MAX;
  bool dtporeactive=false;
  if(HydromechCoupling && PorePressureModel==1){
    const float porosity0=SoilCte.Porosity0;
    const float hydraulicconductivity=SoilCte.HydraulicConductivity;
    const float waterbulkmodulus=SoilCte.WaterBulkModulus;
    const float waterdensity=SoilCte.WaterDensity;
    if(hydraulicconductivity>0.f && waterbulkmodulus>0.f && waterdensity>0.f && porosity0>0.f && porosity0<1.f && PorePressureDtSafety>0.f){
      const double gmag=GetHydraulicGmag();
      if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for GPU pore-pressure timestep restriction.");
      const double cw=double(waterdensity)*gmag*double(porosity0)/double(waterbulkmodulus);
      dtpore=double(PorePressureDtSafety)*cw*double(KernelH)*double(KernelH)/double(hydraulicconductivity);
      if(dtpore<=0. || fun::IsNAN(dtpore) || fun::IsInfinity(dtpore))Run_Exceptioon(fun::PrintStr("The computed GPU pore-pressure timestep is invalid (dt_pore=%g).",dtpore));
      dtporeactive=true;
      if(!PorePressureDtConfigPrint){
        Log->Printf("GPU pore-pressure timestep restriction: active=True, Cw=%g, dt_pore=%g, safety=%g, h(KernelH)=%g, hydraulic_gmag=%g.",cw,dtpore,PorePressureDtSafety,KernelH,gmag);
        if(FixedDt)Log->PrintWarning(fun::PrintStr("Fixed dt is enabled. Fixed dt should be <= GPU dt_pore=%g for PR pore-pressure update.",dtpore));
        PorePressureDtConfigPrint=true;
        PorePressureDtFixedPrint=(FixedDt!=NULL);
      }
    }
    else if(hydraulicconductivity==0.f){
      if(!PorePressureDtConfigPrint){
        Log->Print("GPU pore-pressure timestep restriction: active=False, disabled because HydraulicConductivity=0.");
        PorePressureDtConfigPrint=true;
      }
    }
    else if(hydraulicconductivity>0.f)Run_Exceptioon("Invalid hydromechanical parameters for GPU pore-pressure timestep restriction.");
  }
  PorePressureDt=dtpore;
  PorePressureDtActive=dtporeactive;
  if(dtporeactive && dt>dtpore){
    if(final && !PorePressureDtLimitPrint){
      Log->Printf("Current GPU dt is limited by pore-pressure timestep: existing_dt=%g, dt_pore=%g.",dt,dtpore);
      PorePressureDtLimitPrint=true;
    }
    dt=dtpore;
  }
  //-Saves information about dt.
  if(final){
    if(PartDtMin>dt)PartDtMin=dt;
    if(PartDtMax<dt)PartDtMax=dt;
    //-Saves detailed information about dt in SaveDt object.
    if(SaveDt)SaveDt->AddValues(TimeStep,dt,dt1*CFLnumber,dt2*CFLnumber,AceMax,ViscDtMax,VelMax);
  }
  return(dt);
}

//==============================================================================
/// Computes final shifting distance for the particle position.
/// Calcula Shifting final para posicion de particulas.
//==============================================================================
void JSphGpu::RunShifting(double dt){
  Timersg->TmStart(TMG_SuShifting,false);
  Shifting->RunGpu(Np-Npb,Npb,dt,Velrhopg,ShiftPosfsg);
  Timersg->TmStop(TMG_SuShifting,false);
}

//==============================================================================
/// Calculates predefined movement of boundary particles.
/// Calcula movimiento predefinido de boundary particles.
//==============================================================================
void JSphGpu::CalcMotion(double stepdt){
  Timersg->TmStart(TMG_SuMotion,false);
  JSph::CalcMotion(stepdt);
  Timersg->TmStop(TMG_SuMotion,false);
}

//==============================================================================
/// Processes boundary particle movement.
/// Procesa movimiento de boundary particles.
//==============================================================================
void JSphGpu::RunMotion(double stepdt){
  Timersg->TmStart(TMG_SuMotion,false);
  float3 *boundnormal=NULL;
  boundnormal=BoundNormalg;
  const bool motsim=true;
  BoundChanged=false;
  //-Add motion from automatic wave generation.
  if(WaveGen)CalcMotionWaveGen(stepdt);
  //-Process particles motion.
  if(DsMotion->GetActiveMotion()){
    cusph::CalcRidp(PeriActive!=0,Npb,0,CaseNfixed,CaseNfixed+CaseNmoving,Codeg,Idpg,RidpMoveg);
    BoundChanged=true;
    const unsigned nref=DsMotion->GetNumObjects();
    for(unsigned ref=0;ref<nref;ref++){
      const StMotionData& m=DsMotion->GetMotionData(ref);
      if(m.type==MOTT_Linear){//-Linear movement.
        if(motsim)cusph::MoveLinBound   (PeriActive,m.count,m.idbegin-CaseNfixed,m.linmov,ToTFloat3(m.linvel),RidpMoveg,Posxyg,Poszg,Dcellg,Velrhopg,Codeg);
        //else    cusph::MoveLinBoundAce(PeriActive,m.count,m.idbegin-CaseNfixed,m.linmov,ToTFloat3(m.linvel),ToTFloat3(m.linace),RidpMoveg,Posxyg,Poszg,Dcellg,Velrhopg,Codeg);
      }
      if(m.type==MOTT_Matrix){//-Matrix movement (for rotations).
        if(motsim)cusph::MoveMatBound   (PeriActive,Simulate2D,m.count,m.idbegin-CaseNfixed,m.matmov,stepdt,RidpMoveg,Posxyg,Poszg,Dcellg,Velrhopg,Codeg,boundnormal);
        //else    cusph::MoveMatBoundAce(PeriActive,Simulate2D,m.count,m.idbegin-CaseNfixed,m.matmov,m.matmov2,stepdt,RidpMoveg,Posxyg,Poszg,Dcellg,Velrhopg,Codeg);
      }      
    }
  }
  //-Management of Multi-Layer Pistons.
  if(MLPistons){
    if(!BoundChanged)cusph::CalcRidp(PeriActive!=0,Npb,0,CaseNfixed,CaseNfixed+CaseNmoving,Codeg,Idpg,RidpMoveg);
    BoundChanged=true;
    if(MLPistons->GetPiston1dCount()){//-Process motion for pistons 1D.
      MLPistons->CalculateMotion1d(TimeStep+MLPistons->GetTimeMod()+stepdt);
      cusph::MovePiston1d(PeriActive!=0,CaseNmoving,0,Dp,MLPistons->GetPoszMin(),MLPistons->GetPoszCount(),MLPistons->GetPistonIdGpu(),MLPistons->GetMovxGpu(),MLPistons->GetVelxGpu(),RidpMoveg,Posxyg,Poszg,Dcellg,Velrhopg,Codeg);
    }
    for(unsigned cp=0;cp<MLPistons->GetPiston2dCount();cp++){//-Process motion for pistons 2D.
      JMLPistons::StMotionInfoPiston2D mot=MLPistons->CalculateMotion2d(cp,TimeStep+MLPistons->GetTimeMod()+stepdt);
      cusph::MovePiston2d(PeriActive!=0,mot.np,mot.idbegin-CaseNfixed,Dp,mot.posymin,mot.poszmin,mot.poszcount,mot.movyz,mot.velyz,RidpMoveg,Posxyg,Poszg,Dcellg,Velrhopg,Codeg);
    }
  }
  if(MotionVelg)cusph::CopyMotionVel(CaseNmoving,RidpMoveg,Velrhopg,MotionVelg);
  Timersg->TmStop(TMG_SuMotion,false);
}

//==============================================================================
/// Applies RelaxZone to selected particles.
/// Aplica RelaxZone a las particulas indicadas.
//==============================================================================
void JSphGpu::RunRelaxZone(double dt){
  Timersg->TmStart(TMG_SuMotion,false);
  byte* rzid=NULL; 
  float* rzfactor=NULL; 
  RelaxZones->SetFluidVelGpu(TimeStep,dt,Np-Npb,Npb,(const tdouble2*)Posxyg
    ,Poszg,Idpg,(tfloat4*)Velrhopg,rzid,rzfactor);
  Timersg->TmStop(TMG_SuMotion,false);
}

//==============================================================================
/// Applies Damping to indicated particles.
/// Aplica Damping a las particulas indicadas.
//==============================================================================
void JSphGpu::RunDamping(double dt,unsigned np,unsigned npb,const double2 *posxy
  ,const double *posz,const typecode *code,float4 *velrhop)
{
  const typecode *codeptr=(CaseNfloat || PeriActive? code: NULL);
  Damping->ComputeDampingGpu(TimeStep,dt,np-npb,npb,posxy,posz,codeptr,velrhop);
}

//==============================================================================
/// Save VTK file with particle data (debug).
/// Graba fichero VTK con datos de las particulas (debug).
//==============================================================================
void JSphGpu::SaveVtkNormalsGpu(std::string filename,int numfile,unsigned np,unsigned npb
  ,const double2 *posxyg,const double *poszg,const unsigned *idpg,const float3 *boundnormalg)
{
  //-Allocates memory.
  const unsigned n=(UseNormalsFt? np: npb);
  tdouble3 *pos=fcuda::ToHostPosd3(0,n,posxyg,poszg);
  unsigned *idp=fcuda::ToHostUint(0,n,idpg);
  tfloat3  *nor=fcuda::ToHostFloat3(0,n,boundnormalg);
  //-Generates VTK file.
  SaveVtkNormals(filename,numfile,np,npb,pos,idp,nor,1.f);
  //-Frees memory.
  delete[] pos;
  delete[] idp;
  delete[] nor;
}

//==============================================================================
/// Saves VTK file with particle data (degug).
/// Graba fichero VTK con datos de las particulas (degug).
//==============================================================================
void JSphGpu::DgSaveVtkParticlesGpu(std::string filename,int numfile,unsigned pini,unsigned pfin
 ,const double2 *posxyg,const double *poszg,const typecode *codeg,const unsigned *idpg
 ,const float4 *velrhopg)const
{
  const unsigned np=pfin-pini;
  //-Copy data to CPU memory.
  tdouble3 *posh=fcuda::ToHostPosd3(pini,np,posxyg,poszg);
  #ifdef CODE_SIZE4
    typecode *codeh=fcuda::ToHostUint(pini,np,codeg);
  #else
    typecode *codeh=fcuda::ToHostWord(pini,np,codeg);
  #endif
  unsigned *idph=fcuda::ToHostUint(pini,np,idpg);
  tfloat4  *velrhoph=fcuda::ToHostFloat4(pini,np,velrhopg);
  //-Creates VTK file.
  DgSaveVtkParticlesCpu(filename,numfile,0,np,posh,codeh,idph,velrhoph);
  //-Deallocates memory.
  delete[] posh;  
  delete[] codeh;
  delete[] idph;
  delete[] velrhoph;
}

//==============================================================================
/// Saves VTK file with particle data (debug).
/// Graba fichero vtk con datos de las particulas (debug).
//==============================================================================
void JSphGpu::DgSaveVtkParticlesGpu(std::string filename,int numfile,unsigned pini,unsigned pfin,unsigned cellcode
  ,const double2 *posxyg,const double *poszg,const unsigned *idpg,const unsigned *dcelg
  ,const typecode *codeg,const float4 *velrhopg,const float4 *velrhopm1g,const float3 *aceg)
{
  //-Allocates memory.
  const unsigned n=pfin-pini;
  //-Loads position.
  tfloat3 *pos=new tfloat3[n];
  {
    tdouble2 *pxy=new tdouble2[n];
    double *pz=new double[n];
    cudaMemcpy(pxy,posxyg+pini,sizeof(double2)*n,cudaMemcpyDeviceToHost);
    cudaMemcpy(pz,poszg+pini,sizeof(double)*n,cudaMemcpyDeviceToHost);
    for(unsigned p=0;p<n;p++)pos[p]=TFloat3(float(pxy[p].x),float(pxy[p].y),float(pz[p]));
    delete[] pxy;
    delete[] pz;
  }
  //-Loads idp.
  unsigned *idp=NULL;
  if(idpg){
    idp=new unsigned[n];
    cudaMemcpy(idp,idpg+pini,sizeof(unsigned)*n,cudaMemcpyDeviceToHost);
  }
  //-Loads dcel.
  tuint3 *dcel=NULL;
  if(dcelg){
    dcel=new tuint3[n];
    unsigned *aux=new unsigned[n];
    cudaMemcpy(aux,dcelg+pini,sizeof(unsigned)*n,cudaMemcpyDeviceToHost);
    for(unsigned p=0;p<n;p++)dcel[p]=TUint3(unsigned(DCEL_Cellx(cellcode,aux[p])),unsigned(DCEL_Celly(cellcode,aux[p])),unsigned(DCEL_Cellz(cellcode,aux[p])));
    delete[] aux;
  }
  //-Loads vel and rhop.
  tfloat3 *vel=NULL;
  float *rhop=NULL;
  if(velrhopg){
    vel=new tfloat3[n];
    rhop=new float[n];
    tfloat4 *aux=new tfloat4[n];
    cudaMemcpy(aux,velrhopg+pini,sizeof(float4)*n,cudaMemcpyDeviceToHost);
    for(unsigned p=0;p<n;p++){ vel[p]=TFloat3(aux[p].x,aux[p].y,aux[p].z); rhop[p]=aux[p].w; }
    delete[] aux;
  }
  //-Loads velm1 and rhopm1.
  tfloat3 *velm1=NULL;
  float *rhopm1=NULL;
  if(velrhopm1g){
    velm1=new tfloat3[n];
    rhopm1=new float[n];
    tfloat4 *aux=new tfloat4[n];
    cudaMemcpy(aux,velrhopm1g+pini,sizeof(float4)*n,cudaMemcpyDeviceToHost);
    for(unsigned p=0;p<n;p++){ velm1[p]=TFloat3(aux[p].x,aux[p].y,aux[p].z); rhopm1[p]=aux[p].w; }
    delete[] aux;
  }
  //-Loads ace.
  tfloat3 *ace=NULL;
  if(aceg){
    ace=new tfloat3[n];
    cudaMemcpy(ace,aceg+pini,sizeof(float3)*n,cudaMemcpyDeviceToHost);
  }
  //-Loads type.
  byte *type=NULL;
  if(codeg){
    type=new byte[n];
    typecode *aux=new typecode[n];
    cudaMemcpy(aux,codeg+pini,sizeof(typecode)*n,cudaMemcpyDeviceToHost);
    for(unsigned p=0;p<n;p++){ 
      const typecode cod=aux[p];
      byte tp=99;
      if(CODE_IsFixed(cod))tp=0;
      else if(CODE_IsMoving(cod))tp=1;
      else if(CODE_IsFloating(cod))tp=2;
      else if(CODE_IsFluid(cod))tp=3;
      if(CODE_IsNormal(cod))tp+=0;
      else if(CODE_IsPeriodic(cod))tp+=10;
      else if(CODE_IsOutIgnore(cod))tp+=20;
      else tp+=30;
      type[p]=tp;
    }
    delete[] aux;
  }
  //-Saves VTK file.
  JDataArrays arrays;
  arrays.AddArray("Pos",n,pos,true);
  if(idp)   arrays.AddArray("Idp"   ,n,idp   ,true);
  if(dcel)  arrays.AddArray("Dcel"  ,n,dcel  ,true);
  if(vel)   arrays.AddArray("Vel"   ,n,vel   ,true);
  if(rhop)  arrays.AddArray("Rhop"  ,n,rhop  ,true);
  if(velm1) arrays.AddArray("Velm1" ,n,velm1 ,true);
  if(rhopm1)arrays.AddArray("Rhopm1",n,rhopm1,true);
  if(ace)   arrays.AddArray("Ace"   ,n,ace   ,true);
  if(type)  arrays.AddArray("Typex" ,n,type  ,true);
  JVtkLib::SaveVtkData(fun::FileNameSec(filename,numfile),arrays,"Pos");
  arrays.Reset();
}

//==============================================================================
/// Save VTK file with particle data (debug).
/// Graba fichero VTK con datos de las particulas (debug).
//==============================================================================
void JSphGpu::DgSaveVtkParticlesGpu(std::string filename,int numfile,unsigned pini,unsigned pfin,bool idp,bool vel,bool rhop,bool code)
{
  if(numfile>=0)filename=fun::FileNameSec(filename,numfile);
  if(Log->GetMpiRank()>=0)filename=string("p")+fun::IntStr(Log->GetMpiRank())+"_"+filename;
  filename=DirDataOut+filename;
  //-Allocates memory.
  const unsigned n=pfin-pini;
  ParticlesDataDown(n,pini,code,false);
  tfloat3 *pos=new tfloat3[n];
  for(unsigned p=0;p<n;p++)pos[p]=ToTFloat3(AuxPos[p]);
  byte *type=new byte[n];
  for(unsigned p=0;p<n;p++){
    const typecode cod=Code[p];
    byte tp=99;
    if(CODE_IsFixed(cod))tp=0;
    else if(CODE_IsMoving(cod))tp=1;
    else if(CODE_IsFloating(cod))tp=2;
    else if(CODE_IsFluid(cod))tp=3;
    if(CODE_IsNormal(cod))tp+=0;
    else if(CODE_IsPeriodic(cod))tp+=10;
    else if(CODE_IsOutIgnore(cod))tp+=20;
    else tp+=30;
    type[p]=tp;
  }
  //-Saves VTK file.
  JDataArrays arrays;
  arrays.AddArray("Pos",n,pos,true);
  if(idp) arrays.AddArray("Idp"  ,n,Idp    ,false);
  if(type)arrays.AddArray("Typex",n,type   ,true);
  if(vel) arrays.AddArray("Vel"  ,n,AuxVel ,false);
  if(rhop)arrays.AddArray("Rhop" ,n,AuxRhop,false);
#ifdef CODE_SIZE4
  if(code)arrays.AddArray("Code" ,n,(unsigned*)Code,false);
#else
  if(code)arrays.AddArray("Code" ,n,(word*)    Code,false);
#endif
  JVtkLib::SaveVtkData(filename,arrays,"Pos");
  arrays.Reset();
}

//==============================================================================
/// Save VTK file with particle data (debug).
/// Graba fichero VTK con datos de las particulas (debug).
//==============================================================================
void JSphGpu::DgSaveVtkParticlesGpu(std::string filename,int numfile,unsigned pini,unsigned pfin,const float3 *posg,const byte *checkg,const unsigned *idpg,const float3 *velg,const float *rhopg){
  //-Allocates memory.
  const unsigned n=pfin-pini;
  tfloat3 *pos=new tfloat3[n];
  byte *check=NULL;
  unsigned *idp=NULL;
  tfloat3 *vel=NULL;
  float *rhop=NULL;
  if(checkg)check=new byte[n];
  if(idpg)idp=new unsigned[n];
  if(velg)vel=new tfloat3[n];
  if(rhopg)rhop=new float[n];
  //-Copies data from GPU.
  cudaMemcpy(pos,posg+pini,sizeof(float3)*n,cudaMemcpyDeviceToHost);
  if(checkg)cudaMemcpy(check,checkg+pini,sizeof(byte)*n,cudaMemcpyDeviceToHost);
  if(idpg)cudaMemcpy(idp,idpg+pini,sizeof(unsigned)*n,cudaMemcpyDeviceToHost);
  if(velg)cudaMemcpy(vel,velg+pini,sizeof(float3)*n,cudaMemcpyDeviceToHost);
  if(rhopg)cudaMemcpy(rhop,rhopg+pini,sizeof(float)*n,cudaMemcpyDeviceToHost);
  //-Generates VTK file.
  DgSaveVtkParticlesCpu(filename,numfile,0,n,pos,check,idp,vel,rhop);
  //-Frees memory.
  delete[] pos;
  delete[] check;
  delete[] idp;
  delete[] vel;
  delete[] rhop;
}

//==============================================================================
/// Save CSV file with particle data (debug).
/// Graba fichero CSV con datos de las particulas (debug).
//==============================================================================
void JSphGpu::DgSaveCsvParticlesGpu(std::string filename,int numfile,unsigned pini,unsigned pfin,std::string head,const float3 *posg,const unsigned *idpg,const float3 *velg,const float *rhopg,const float *arg,const float3 *aceg,const float3 *vcorrg){
  //-Allocates memory.
  const unsigned n=pfin-pini;
  unsigned *idp=NULL;  if(idpg)idp=new unsigned[n];
  tfloat3 *pos=NULL;   if(posg)pos=new tfloat3[n];
  tfloat3 *vel=NULL;   if(velg)vel=new tfloat3[n];
  float *rhop=NULL;    if(rhopg)rhop=new float[n];
  float *ar=NULL;      if(arg)ar=new float[n];
  tfloat3 *ace=NULL;   if(aceg)ace=new tfloat3[n];
  tfloat3 *vcorr=NULL; if(vcorrg)vcorr=new tfloat3[n];
  //-Copies data from GPU.
  if(idpg)cudaMemcpy(idp,idpg+pini,sizeof(unsigned)*n,cudaMemcpyDeviceToHost);
  if(posg)cudaMemcpy(pos,posg+pini,sizeof(float3)*n,cudaMemcpyDeviceToHost);
  if(velg)cudaMemcpy(vel,velg+pini,sizeof(float3)*n,cudaMemcpyDeviceToHost);
  if(rhopg)cudaMemcpy(rhop,rhopg+pini,sizeof(float)*n,cudaMemcpyDeviceToHost);
  if(arg)cudaMemcpy(ar,arg+pini,sizeof(float)*n,cudaMemcpyDeviceToHost);
  if(aceg)cudaMemcpy(ace,aceg+pini,sizeof(float3)*n,cudaMemcpyDeviceToHost);
  if(vcorrg)cudaMemcpy(vcorr,vcorrg+pini,sizeof(float3)*n,cudaMemcpyDeviceToHost);
  Check_CudaErroor("Failed copying data from GPU.");
  //-Generates CSV file.
  DgSaveCsvParticlesCpu(filename,numfile,0,n,head,pos,idp,vel,rhop,ar,ace,vcorr);
  //-Frees memory.
  delete[] idp;
  delete[] pos;
  delete[] vel;
  delete[] rhop;
  delete[] ar;
  delete[] ace;
  delete[] vcorr;
}

//==============================================================================
/// Save CSV file with particle data (debug).
/// Graba fichero CSV con datos de las particulas (debug).
//==============================================================================
void JSphGpu::DgSaveCsvParticlesGpu2(std::string filename,int numfile,unsigned pini,unsigned pfin,std::string head,const float3 *posg,const unsigned *idpg,const float3 *velg,const float *rhopg,const float4 *pospresg,const float4 *velrhopg){
  //-Allocates memory.
  const unsigned n=pfin-pini;
  unsigned *idp=NULL;  if(idpg)idp=new unsigned[n];
  tfloat3 *pos=NULL;   if(posg)pos=new tfloat3[n];
  tfloat3 *vel=NULL;   if(velg)vel=new tfloat3[n];
  float *rhop=NULL;    if(rhopg)rhop=new float[n];
  tfloat4 *pospres=NULL;  if(pospresg)pospres=new tfloat4[n];
  tfloat4 *velrhop=NULL;  if(velrhopg)velrhop=new tfloat4[n];
  //-Copies data from GPU.
  if(idpg)cudaMemcpy(idp,idpg+pini,sizeof(unsigned)*n,cudaMemcpyDeviceToHost);
  if(posg)cudaMemcpy(pos,posg+pini,sizeof(float3)*n,cudaMemcpyDeviceToHost);
  if(velg)cudaMemcpy(vel,velg+pini,sizeof(float3)*n,cudaMemcpyDeviceToHost);
  if(rhopg)cudaMemcpy(rhop,rhopg+pini,sizeof(float)*n,cudaMemcpyDeviceToHost);
  if(pospresg)cudaMemcpy(pospres,pospresg+pini,sizeof(float4)*n,cudaMemcpyDeviceToHost);
  if(velrhopg)cudaMemcpy(velrhop,velrhopg+pini,sizeof(float4)*n,cudaMemcpyDeviceToHost);
  Check_CudaErroor("Failed copying data from GPU.");
  //-Generates CSV file.
  DgSaveCsvParticles2(filename,numfile,0,n,head,pos,idp,vel,rhop,pospres,velrhop);
  //-Frees memory.
  delete[] idp;
  delete[] pos;
  delete[] vel;
  delete[] rhop;
  delete[] pospres;
  delete[] velrhop;
}

//==============================================================================
/// Save CSV file with particle data (debug).
/// Graba fichero CSV con datos de las particulas (debug).
//==============================================================================
void JSphGpu::DgSaveCsvParticles2(std::string filename,int numfile,unsigned pini,unsigned pfin,std::string head,const tfloat3 *pos,const unsigned *idp,const tfloat3 *vel,const float *rhop,const tfloat4 *pospres,const tfloat4 *velrhop){
  int mpirank=Log->GetMpiRank();
  if(mpirank>=0)filename=string("p")+fun::IntStr(mpirank)+"_"+filename;
  if(numfile>=0)filename=fun::FileNameSec(filename,numfile);
  filename=DirDataOut+filename;
  //-Generates CSV file.
  ofstream pf;
  pf.open(filename.c_str());
  if(pf){
    if(!head.empty())pf << head << endl;
    pf << "Num";
    if(idp)pf << ";Idp";
    if(pos)pf << ";PosX;PosY;PosZ";
    if(vel)pf << ";VelX;VelY;VelZ";
    if(rhop)pf << ";Rhop";
    if(pospres)pf << ";Px;Py;Pz;Pp";
    if(velrhop)pf << ";Vx;Vy;Vz;Vr";
    pf << endl;
    const char fmt1[]="%f"; //="%24.16f";
    const char fmt3[]="%f;%f;%f"; //="%24.16f;%24.16f;%24.16f";
    for(unsigned p=pini;p<pfin;p++){
      pf << fun::UintStr(p-pini);
      if(idp)pf << ";" << fun::UintStr(idp[p]);
      if(pos)pf << ";" << fun::Float3Str(pos[p],fmt3);
      if(vel)pf << ";" << fun::Float3Str(vel[p],fmt3);
      if(rhop)pf << ";" << fun::FloatStr(rhop[p],fmt1);
      if(pospres)pf << ";" <<  fun::FloatStr(pospres[p].x,fmt1) << ";" << fun::FloatStr(pospres[p].y,fmt1) << ";" << fun::FloatStr(pospres[p].z,fmt1) << ";" << fun::FloatStr(pospres[p].w,fmt1);
      if(velrhop)pf << ";" <<  fun::FloatStr(velrhop[p].x,fmt1) << ";" << fun::FloatStr(velrhop[p].y,fmt1) << ";" << fun::FloatStr(velrhop[p].z,fmt1) << ";" << fun::FloatStr(velrhop[p].w,fmt1);
      pf << endl;
    }
    if(pf.fail())Run_ExceptioonFile("Failed writing to file.",filename);
    pf.close();
  }
  else Run_ExceptioonFile("File could not be opened.",filename);
}


