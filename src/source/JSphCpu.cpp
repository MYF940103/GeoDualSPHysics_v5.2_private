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

/// \file JSphCpu.cpp \brief Implements the class \ref JSphCpu.

#include "JSphCpu.h"
#include "JCellSearch_inline.h"
#include "JCellDivCpu.h"
#include "JPartFloatBi4.h"
#include "FunSphKernel.h"
#include "FunSphEos.h"
#include "Functions.h"
#include "FunctionsMath.h"
#include "JDsMotion.h"
#include "JArraysCpu.h"
#include "JDsFixedDt.h"
#include "JWaveGen.h"
#include "JMLPistons.h"
#include "JRelaxZones.h"
#include "JChronoObjects.h"
#include "JDsFtForcePoints.h"
#include "JDsDamping.h"
#include "JXml.h"
#include "JDsSaveDt.h"
#include "JDsOutputTime.h"
#include "JDsAccInput.h"
#include "JDsGaugeSystem.h"
#include "JSphInOut.h"
#include "JSphShifting.h"

#include <climits>
#include <cmath>

using namespace std;

static void ComputeArtificialStressArray(unsigned np,unsigned npb,const typecode *code,const tfloat4 *velrhop,const tsymatrix3f *sigma,const float coef,tsymatrix3f *artificialstress);

//==============================================================================
/// Constructor.
//==============================================================================
JSphCpu::JSphCpu(bool withmpi):JSph(true,false,withmpi){
  ClassName="JSphCpu";
  CellDiv=NULL;
  ArraysCpu=new JArraysCpu;
  Timersc=new JDsTimersCpu;
  InitVars();
}

//==============================================================================
/// Destructor.
//==============================================================================
JSphCpu::~JSphCpu(){
  DestructorActive=true;
  FreeCpuMemoryParticles();
  FreeCpuMemoryFixed();
  delete ArraysCpu; ArraysCpu=NULL;
  delete Timersc;   Timersc=NULL;
}

//==============================================================================
/// Initialisation of variables.
//==============================================================================
void JSphCpu::InitVars(){
  RunMode="";
  OmpThreads=1;

  DivData=DivDataCpuNull();

  Np=Npb=NpbOk=0;
  NpbPer=NpfPer=0;

  Idpc=NULL; Codec=NULL; Dcellc=NULL; Posc=NULL; Velrhopc=NULL;
  BoundNormalc=NULL; MotionVelc=NULL; //-mDBC
  //====== mdbr
  Sigmac=NULL;SigmaPrec=NULL;SigmaM1c=NULL;
  Rsigmac=NULL;Kplasticc=NULL;
  ArtificialStressc=NULL;
  //======
  PorePressc=NULL; PorePressRatec=NULL; DivVelc=NULL; LapPorePressc=NULL; LapZc=NULL;
  VelrhopM1c=NULL;                //-Verlet
  PosPrec=NULL; VelrhopPrec=NULL; //-Symplectic
  SpsTauc=NULL; SpsGradvelc=NULL; //-Laminar+SPS.
  Arc=NULL; Acec=NULL; Deltac=NULL;
  ShiftPosfsc=NULL;               //-Shifting.
  Pressc=NULL;
  PorePressureDt=DBL_MAX;
  PorePressureDtActive=false;
  PorePressureDtConfigPrint=PorePressureDtLimitPrint=PorePressureDtFixedPrint=false;
  PorePressureUpdateDtPrint=false;
  RidpMove=NULL; 
  FtRidp=NULL;
  FtoForces=NULL;
  FtoForcesRes=NULL;
  FreeCpuMemoryParticles();
  FreeCpuMemoryFixed();
}

//==============================================================================
/// Deallocate fixed memory on CPU for moving and floating bodies.
/// Libera memoria fija en cpu para moving y floating.
//==============================================================================
void JSphCpu::FreeCpuMemoryFixed(){
  MemCpuFixed=0;
  delete[] RidpMove;     RidpMove=NULL;
  delete[] FtRidp;       FtRidp=NULL;
  delete[] FtoForces;    FtoForces=NULL;
  delete[] FtoForcesRes; FtoForcesRes=NULL;
}

//==============================================================================
/// Allocates memory for arrays with fixed size (motion and floating bodies).
//==============================================================================
void JSphCpu::AllocCpuMemoryFixed(){
  MemCpuFixed=0;
  try{
    //-Allocates memory for moving objects.
    if(CaseNmoving){
      RidpMove=new unsigned[CaseNmoving];  MemCpuFixed+=(sizeof(unsigned)*CaseNmoving);
    }
    //-Allocates memory for floating bodies.
    if(CaseNfloat){
      FtRidp      =new unsigned[CaseNfloat];     MemCpuFixed+=(sizeof(unsigned)*CaseNfloat);
      FtoForces   =new StFtoForces[FtCount];     MemCpuFixed+=(sizeof(StFtoForces)*FtCount);
      FtoForcesRes=new StFtoForcesRes[FtCount];  MemCpuFixed+=(sizeof(StFtoForcesRes)*FtCount);
    }
  }
  catch(const std::bad_alloc){
    Run_Exceptioon("Could not allocate the requested memory.");
  }
}

//==============================================================================
/// Deallocate memory in CPU for particles.
/// Libera memoria en cpu para particulas.
//==============================================================================
void JSphCpu::FreeCpuMemoryParticles(){
  CpuParticlesSize=0;
  MemCpuParticles=0;
  ArraysCpu->Reset();
  PorePressc=NULL; PorePressRatec=NULL; DivVelc=NULL; LapPorePressc=NULL; LapZc=NULL;
}

//==============================================================================
/// Allocte memory on CPU for the particles. 
/// Reserva memoria en Cpu para las particulas. 
//==============================================================================
void JSphCpu::AllocCpuMemoryParticles(unsigned np,float over){
  FreeCpuMemoryParticles();
  //-Calculate number of partices with reserved memory | Calcula numero de particulas para las que se reserva memoria.
  const unsigned np2=(over>0? unsigned(over*np): np);
  CpuParticlesSize=np2+PARTICLES_OVERMEMORY_MIN;
  //-Define number or arrays to use. | Establece numero de arrays a usar.
  ArraysCpu->SetArraySize(CpuParticlesSize);
  #ifdef CODE_SIZE4
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,2);  //-code,code2
  #else
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_2B,2);  //-code,code2
  #endif
  ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,5);  //-idp,ar,viscdt,dcell,prrhop
  if(DDTArray)ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,1);  //-delta
  ArraysCpu->AddArrayCount(JArraysCpu::SIZE_12B,1); //-ace
  ArraysCpu->AddArrayCount(JArraysCpu::SIZE_16B,2); //-velrhop,poscell
  ArraysCpu->AddArrayCount(JArraysCpu::SIZE_24B,2); //-pos
  //====== mdbr
  ArraysCpu->AddArrayCount(JArraysCpu::SIZE_24B,2);//-sigma,rsigma
  if(ArtificialStress)ArraysCpu->AddArrayCount(JArraysCpu::SIZE_24B,1);//-artificialstress
  ArraysCpu->AddArrayCount(JArraysCpu::SIZE_12B,2);//-sigmakk,sigmaij
  ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,1);//-kplastic
  //======
  if(HydromechCoupling || SavePorePressure){
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_8B,1); //-porepress
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,4); //-porepressrate,divvel,lapporepress,lapz
  }
  if(SavePorePressure){
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_8B,1); //-porepress output
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,4); //-porepressrate,divvel,lapporepress,lapz output
  }
  if(TStep==STEP_Verlet){
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_16B,1); //-velrhopm1
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_24B,1);//-sigmam1
  }
  else if(TStep==STEP_Symplectic){
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_24B,1); //-pospre
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_16B,1); //-velrhoppre
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_24B,1);//-sigmapre
  }
  if(TVisco==VISCO_LaminarSPS){     
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_24B,2); //-SpsTau,SpsGradvel
  }
  if(Shifting){
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_16B,1); //-shiftposfs
  }
  if(UseNormals){
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_12B,1); //-BoundNormal
    if(SlipMode!=SLIP_Vel0)ArraysCpu->AddArrayCount(JArraysCpu::SIZE_12B,1); //-MotionVel
  }
  if(InOut){
    //ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,1);  //-InOutPart
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_1B,2);  //-newizone,zsurfok
  }
  //-Shows the allocated memory.
  MemCpuParticles=ArraysCpu->GetAllocMemoryCpu();
  PrintSizeNp(CpuParticlesSize,MemCpuParticles,0);
}

//==============================================================================
/// Resizes space in CPU memory for particles.
//==============================================================================
void JSphCpu::ResizeCpuMemoryParticles(unsigned npnew){
  npnew=npnew+PARTICLES_OVERMEMORY_MIN;
  //-Saves current data from CPU.
  unsigned    *idp        =SaveArrayCpu(Np,Idpc);
  typecode    *code       =SaveArrayCpu(Np,Codec);
  unsigned    *dcell      =SaveArrayCpu(Np,Dcellc);
  tdouble3    *pos        =SaveArrayCpu(Np,Posc);
  tfloat4     *velrhop    =SaveArrayCpu(Np,Velrhopc);
  tfloat4     *velrhopm1  =SaveArrayCpu(Np,VelrhopM1c);
  tdouble3    *pospre     =SaveArrayCpu(Np,PosPrec);
  tfloat4     *velrhoppre =SaveArrayCpu(Np,VelrhopPrec);
  tsymatrix3f *spstau     =SaveArrayCpu(Np,SpsTauc);
  tfloat3     *boundnormal=SaveArrayCpu(Np,BoundNormalc);
  tfloat3     *motionvel  =SaveArrayCpu(Np,MotionVelc);
  //====mdbr
  tsymatrix3f  *sigma     =SaveArrayCpu(Np,Sigmac);
  tsymatrix3f  *sigmapre  =SaveArrayCpu(Np,SigmaPrec);
  tsymatrix3f  *sigmam1   =SaveArrayCpu(Np,SigmaM1c);
  float        *kplastic  =SaveArrayCpu(Np,Kplasticc);
  double       *porepress =SaveArrayCpu(Np,PorePressc);
  float        *porepressrate=SaveArrayCpu(Np,PorePressRatec);
  float        *divvel    =SaveArrayCpu(Np,DivVelc);
  float        *lapporepress=SaveArrayCpu(Np,LapPorePressc);
  float        *lapz      =SaveArrayCpu(Np,LapZc);
  //==== 
  //-Frees pointers.
  ArraysCpu->Free(Idpc);
  ArraysCpu->Free(Codec);
  ArraysCpu->Free(Dcellc);
  ArraysCpu->Free(Posc);
  ArraysCpu->Free(Velrhopc);
  ArraysCpu->Free(VelrhopM1c);
  ArraysCpu->Free(PosPrec);
  ArraysCpu->Free(VelrhopPrec);
  ArraysCpu->Free(SpsTauc);
  ArraysCpu->Free(BoundNormalc);
  ArraysCpu->Free(MotionVelc);
  //====mdbr
  ArraysCpu->Free(Sigmac);
  ArraysCpu->Free(SigmaPrec);
  ArraysCpu->Free(SigmaM1c);
  ArraysCpu->Free(Kplasticc);
  ArraysCpu->Free(PorePressc);
  ArraysCpu->Free(PorePressRatec);
  ArraysCpu->Free(DivVelc);
  ArraysCpu->Free(LapPorePressc);
  ArraysCpu->Free(LapZc);
  //====
  //-Resizes CPU memory allocation.
  const double mbparticle=(double(MemCpuParticles)/(1024*1024))/CpuParticlesSize; //-MB por particula.
  Log->Printf("**JSphCpu: Requesting cpu memory for %u particles: %.1f MB.",npnew,mbparticle*npnew);
  ArraysCpu->SetArraySize(npnew);
  //-Reserve pointers.
  Idpc    =ArraysCpu->ReserveUint();
  Codec   =ArraysCpu->ReserveTypeCode();
  Dcellc  =ArraysCpu->ReserveUint();
  Posc    =ArraysCpu->ReserveDouble3();
  Velrhopc=ArraysCpu->ReserveFloat4();
  if(velrhopm1)  VelrhopM1c  =ArraysCpu->ReserveFloat4();
  if(pospre)     PosPrec     =ArraysCpu->ReserveDouble3();
  if(velrhoppre) VelrhopPrec =ArraysCpu->ReserveFloat4();
  if(spstau)     SpsTauc     =ArraysCpu->ReserveSymatrix3f();
  if(boundnormal)BoundNormalc=ArraysCpu->ReserveFloat3();
  if(motionvel)  MotionVelc  =ArraysCpu->ReserveFloat3();
  //===== mdbr
  if(sigma)      Sigmac = ArraysCpu->ReserveSymatrix3f();
  if(sigmapre)   SigmaPrec = ArraysCpu->ReserveSymatrix3f();
  if(sigmam1)    SigmaM1c = ArraysCpu->ReserveSymatrix3f();
  if(kplastic)   Kplasticc = ArraysCpu->ReserveFloat();
  if(porepress)     PorePressc = ArraysCpu->ReserveDouble();
  if(porepressrate) PorePressRatec = ArraysCpu->ReserveFloat();
  if(divvel)        DivVelc = ArraysCpu->ReserveFloat();
  if(lapporepress)  LapPorePressc = ArraysCpu->ReserveFloat();
  if(lapz)          LapZc = ArraysCpu->ReserveFloat();
  //=====
  //-Restore data in CPU memory.
  RestoreArrayCpu(Np,idp,Idpc);
  RestoreArrayCpu(Np,code,Codec);
  RestoreArrayCpu(Np,dcell,Dcellc);
  RestoreArrayCpu(Np,pos,Posc);
  RestoreArrayCpu(Np,velrhop,Velrhopc);
  RestoreArrayCpu(Np,velrhopm1,VelrhopM1c);
  RestoreArrayCpu(Np,pospre,PosPrec);
  RestoreArrayCpu(Np,velrhoppre,VelrhopPrec);
  RestoreArrayCpu(Np,spstau,SpsTauc);
  RestoreArrayCpu(Np,boundnormal,BoundNormalc);
  RestoreArrayCpu(Np,motionvel,MotionVelc);
  //===== mdbr
  RestoreArrayCpu(Np,sigma,Sigmac);
  RestoreArrayCpu(Np,sigmapre,SigmaPrec);
  RestoreArrayCpu(Np,sigmam1,SigmaM1c);
  RestoreArrayCpu(Np,kplastic,Kplasticc);
  RestoreArrayCpu(Np,porepress,PorePressc);
  RestoreArrayCpu(Np,porepressrate,PorePressRatec);
  RestoreArrayCpu(Np,divvel,DivVelc);
  RestoreArrayCpu(Np,lapporepress,LapPorePressc);
  RestoreArrayCpu(Np,lapz,LapZc);
  //=====
  //-Updates values.
  CpuParticlesSize=npnew;
  MemCpuParticles=ArraysCpu->GetAllocMemoryCpu();
}

//==============================================================================
/// Saves a CPU array in CPU memory. 
//==============================================================================
template<class T> T* JSphCpu::TSaveArrayCpu(unsigned np,const T *datasrc)const{
  T *data=NULL;
  if(datasrc){
    try{
      data=new T[np];
    }
    catch(const std::bad_alloc){
      Run_Exceptioon("Could not allocate the requested memory.");
    }
    memcpy(data,datasrc,sizeof(T)*np);
  }
  return(data);
}

//==============================================================================
/// Restores an array (generic) from CPU memory. 
//==============================================================================
template<class T> void JSphCpu::TRestoreArrayCpu(unsigned np,T *data,T *datanew)const{
  if(data&&datanew)memcpy(datanew,data,sizeof(T)*np);
  delete[] data;
}

//==============================================================================
/// Arrays for basic particle data. 
/// Arrays para datos basicos de las particulas. 
//==============================================================================
void JSphCpu::ReserveBasicArraysCpu(){
  Idpc=ArraysCpu->ReserveUint();
  Codec=ArraysCpu->ReserveTypeCode();
  Dcellc=ArraysCpu->ReserveUint();
  Posc=ArraysCpu->ReserveDouble3();
  Velrhopc=ArraysCpu->ReserveFloat4();
  //-mdbr
  Sigmac=ArraysCpu->ReserveSymatrix3f();
  Kplasticc=ArraysCpu->ReserveFloat();
  //=====
  if(HydromechCoupling || SavePorePressure){
    PorePressc=ArraysCpu->ReserveDouble();
    PorePressRatec=ArraysCpu->ReserveFloat();
    DivVelc=ArraysCpu->ReserveFloat();
    LapPorePressc=ArraysCpu->ReserveFloat();
    LapZc=ArraysCpu->ReserveFloat();
  }
  if(TStep==STEP_Verlet){VelrhopM1c=ArraysCpu->ReserveFloat4();
  SigmaM1c=ArraysCpu->ReserveSymatrix3f();}//mdbr
  if(TVisco==VISCO_LaminarSPS)SpsTauc=ArraysCpu->ReserveSymatrix3f();
  if(UseNormals){
    BoundNormalc=ArraysCpu->ReserveFloat3();
    if(SlipMode!=SLIP_Vel0)MotionVelc=ArraysCpu->ReserveFloat3();
  }
}

//==============================================================================
/// Return memory reserved on CPU.
/// Devuelve la memoria reservada en cpu.
//==============================================================================
llong JSphCpu::GetAllocMemoryCpu()const{  
  llong s=JSph::GetAllocMemoryCpu();
  //-Reserved in AllocCpuMemoryParticles().
  s+=MemCpuParticles;
  //-Reserved in AllocCpuMemoryFixed().
  s+=MemCpuFixed;
  //-Reserved in other objects.
  if(MLPistons)s+=MLPistons->GetAllocMemoryCpu();
  return(s);
}

//==============================================================================
/// Visualize the reserved memory.
/// Visualiza la memoria reservada.
//==============================================================================
void JSphCpu::PrintAllocMemory(llong mcpu)const{
  Log->Printf("Allocated memory in CPU: %lld (%.2f MB)",mcpu,double(mcpu)/(1024*1024));
}

//==============================================================================
/// Collect data from a range of particles and return the number of particles that 
/// will be less than n and eliminate the periodic ones
/// - onlynormal: Only keep the normal ones and eliminate the periodic particles.
///
/// Recupera datos de un rango de particulas y devuelve el numero de particulas que
/// sera menor que n si se eliminaron las periodicas.
/// - onlynormal: Solo se queda con las normales, elimina las particulas periodicas.
//==============================================================================
unsigned JSphCpu::GetParticlesData(unsigned n,unsigned pini,bool onlynormal
  ,unsigned *idp,tdouble3 *pos,tfloat3 *vel,float *rhop,tfloat3 *sigmakk,tfloat3 *sigmaij,float *kplastic,typecode *code,double *porepress,float *porepressrate,float *divvel,float *lapporepress,float *lapz)
{
  unsigned num=n;
  //-Copy selected values.
  if(code)memcpy(code,Codec+pini,sizeof(typecode)*n);
  if(idp) memcpy(idp ,Idpc +pini,sizeof(unsigned)*n);
  if(pos) memcpy(pos ,Posc +pini,sizeof(tdouble3)*n);
  if(vel && rhop){
    for(unsigned p=0;p<n;p++){
      tfloat4 vr=Velrhopc[p+pini];
      vel[p]=TFloat3(vr.x,vr.y,vr.z);
      rhop[p]=vr.w;
    }
  }
  else{
    if(vel) for(unsigned p=0;p<n;p++){ tfloat4 vr=Velrhopc[p+pini]; vel[p]=TFloat3(vr.x,vr.y,vr.z); }
    if(rhop)for(unsigned p=0;p<n;p++)rhop[p]=Velrhopc[p+pini].w;
  }
  //========= mdbr
  if(sigmakk){
	  for (unsigned p=0;p<n;p++) {
		  tsymatrix3f sig=Sigmac[p+pini];
		  sigmakk[p]=TFloat3(sig.xx,sig.yy,sig.zz);
          sigmaij[p]=TFloat3(sig.xy,sig.yz,sig.xz);
	  }
  }
  if(kplastic){
      for (unsigned p=0;p<n;p++) {
          float kplas=Kplasticc[p+pini];
          kplastic[p]=kplas;
      }  
  }
  if(porepress){
      for (unsigned p=0;p<n;p++)porepress[p]=PorePressc[p+pini];
  }
  if(porepressrate){
      for (unsigned p=0;p<n;p++)porepressrate[p]=PorePressRatec[p+pini];
  }
  if(divvel){
      for (unsigned p=0;p<n;p++)divvel[p]=DivVelc[p+pini];
  }
  if(lapporepress){
      for (unsigned p=0;p<n;p++)lapporepress[p]=LapPorePressc[p+pini];
  }
  if(lapz){
      for (unsigned p=0;p<n;p++)lapz[p]=LapZc[p+pini];
  }
  //=========
  //-Eliminate non-normal particles (periodic & others). | Elimina particulas no normales (periodicas y otras).
  if(onlynormal){
    if(!idp || !pos || !vel || !rhop)Run_Exceptioon("Pointers without data.");
    typecode *code2=code;
    if(!code2){
      code2=ArraysCpu->ReserveTypeCode();
      memcpy(code2,Codec+pini,sizeof(typecode)*n);
    }
    unsigned ndel=0;
    for(unsigned p=0;p<n;p++){
      bool normal=CODE_IsNormal(code2[p]);
      if(ndel && normal){
        const unsigned pdel=p-ndel;
        idp[pdel]  =idp[p];
        pos[pdel]  =pos[p];
        vel[pdel]  =vel[p];
        rhop[pdel] =rhop[p];
        //===mdbr
        sigmakk[pdel]=sigmakk[p];
        sigmaij[pdel]=sigmaij[p];
        kplastic[pdel]=kplastic[p];
        if(porepress)porepress[pdel]=porepress[p];
        if(porepressrate)porepressrate[pdel]=porepressrate[p];
        if(divvel)divvel[pdel]=divvel[p];
        if(lapporepress)lapporepress[pdel]=lapporepress[p];
        if(lapz)lapz[pdel]=lapz[p];
        //====
        code2[pdel]=code2[p];
      }
      if(!normal)ndel++;
    }
    num-=ndel;
    if(!code)ArraysCpu->Free(code2);
  }
  return(num);
}

//==============================================================================
/// Load the execution configuration with OpenMP.
/// Carga la configuracion de ejecucion con OpenMP.
//==============================================================================
void JSphCpu::ConfigOmp(const JSphCfgRun *cfg){
#ifdef OMP_USE
  //-Determine number of threads for host with OpenMP. | Determina numero de threads por host con OpenMP.
  if(Cpu && cfg->OmpThreads!=1){
    OmpThreads=cfg->OmpThreads;
    if(OmpThreads<=0)OmpThreads=max(omp_get_num_procs(),1);
    if(OmpThreads>OMP_MAXTHREADS)OmpThreads=OMP_MAXTHREADS;
    omp_set_num_threads(OmpThreads);
    Log->Printf("Threads by host for parallel execution: %d",omp_get_max_threads());
  }
  else{
    OmpThreads=1;
    omp_set_num_threads(OmpThreads);
  }
#else
  OmpThreads=1;
#endif
}

//==============================================================================
/// Configures execution mode in CPU.
/// Configura modo de ejecucion en CPU.
//==============================================================================
void JSphCpu::ConfigRunMode(){
  Hardware="CPU";
  //-Defines RunMode.
  RunMode="";
  if(Stable)RunMode=RunMode+(!RunMode.empty()? " - ": "") + "Stable";
  RunMode=RunMode+(!RunMode.empty()? " - ": "") + "Pos-Double";
  if(OmpThreads==1)RunMode=RunMode+(!RunMode.empty()? " - ": "") + "Single core";
  else             RunMode=RunMode+(!RunMode.empty()? " - ": "") + fun::PrintStr("OpenMP(Threads:%d)",OmpThreads); 
  //-Shows RunMode.
  Log->Print(" ");
  Log->Print(fun::VarStr("RunMode",RunMode));
  Log->Print(" ");
}

//==============================================================================
/// Initialisation of arrays and variables for execution.
/// Inicializa vectores y variables para la ejecucion.
//==============================================================================
void JSphCpu::InitRunCpu(){
  InitRun(Np,Idpc,Posc);
  if(TStep==STEP_Symplectic)SymplecticDtPre=LimitInitialDtByPorePressure(SymplecticDtPre);

  if(TStep==STEP_Verlet)memcpy(VelrhopM1c,Velrhopc,sizeof(tfloat4)*Np);
  if(TVisco==VISCO_LaminarSPS)memset(SpsTauc,0,sizeof(tsymatrix3f)*Np);
  if(CaseNfloat)InitFloating();
  if(MotionVelc)memset(MotionVelc,0,sizeof(tfloat3)*Np);
}

//==============================================================================
/// Applies pore-pressure stability restriction to the initial CPU timestep.
//==============================================================================
double JSphCpu::LimitInitialDtByPorePressure(double dt){
  if(!HydromechCoupling || PorePressureModel!=1)return(dt);
  double dtpore=DBL_MAX;
  bool dtporeactive=false;
  if(HydraulicConductivity>0.f && WaterBulkModulus>0.f && WaterDensity>0.f && Porosity0>0.f && Porosity0<1.f && PorePressureDtSafety>0.f){
    const double gmag=sqrt(double(Gravity.x)*double(Gravity.x)+double(Gravity.y)*double(Gravity.y)+double(Gravity.z)*double(Gravity.z));
    if(gmag<=0.)Run_Exceptioon("Gravity magnitude must be greater than zero for pore-pressure timestep restriction.");
    const double cw=double(WaterDensity)*gmag*double(Porosity0)/double(WaterBulkModulus);
    dtpore=double(PorePressureDtSafety)*cw*double(KernelH)*double(KernelH)/double(HydraulicConductivity);
    if(dtpore<=0. || fun::IsNAN(dtpore) || fun::IsInfinity(dtpore))Run_Exceptioon(fun::PrintStr("The computed pore-pressure timestep is invalid (dt_pore=%g).",dtpore));
    dtporeactive=true;
    if(!PorePressureDtConfigPrint){
      Log->Printf("Pore-pressure timestep restriction: active=True, Cw=%g, dt_pore=%g, safety=%g, h(KernelH)=%g.",cw,dtpore,PorePressureDtSafety,KernelH);
      if(FixedDt)Log->PrintWarning(fun::PrintStr("Fixed dt is enabled. Fixed dt should be <= dt_pore=%g for PR pore-pressure update.",dtpore));
      PorePressureDtConfigPrint=true;
      PorePressureDtFixedPrint=(FixedDt!=NULL);
    }
  }
  else if(HydraulicConductivity==0.f){
    if(!PorePressureDtConfigPrint){
      Log->Print("Pore-pressure timestep restriction: active=False, disabled because HydraulicConductivity=0.");
      PorePressureDtConfigPrint=true;
    }
  }
  else if(HydraulicConductivity>0.f)Run_Exceptioon("Invalid hydromechanical parameters for pore-pressure timestep restriction.");
  PorePressureDt=dtpore;
  PorePressureDtActive=dtporeactive;
  if(dtporeactive && dt>dtpore){
    Log->Printf("Initial timestep limited by pore-pressure dt_pore: old_dt=%g, dt_pore=%g, new_dt=%g.",dt,dtpore,dtpore);
    dt=dtpore;
  }
  return(dt);
}

//==============================================================================
/// Prepare variables for interaction functions.
/// Prepara variables para interaccion.
//==============================================================================
void JSphCpu::PreInteractionVars_Forces(unsigned np,unsigned npb){
  //-Initialise arrays.
  const unsigned npf=np-npb;
  memset(Arc,0,sizeof(float)*np);                                    //Arc[]=0
  if(Deltac)memset(Deltac,0,sizeof(float)*np);                       //Deltac[]=0
  memset(Acec,0,sizeof(tfloat3)*np);                                 //Acec[]=(0,0,0)
  if(SpsGradvelc)memset(SpsGradvelc+npb,0,sizeof(tsymatrix3f)*npf);  //SpsGradvelc[]=(0,0,0,0,0,0).
  //====== mdbr
  memset(Rsigmac,0,sizeof(tsymatrix3f)*np);
  //======
  //-Select particles for shifting.
  if(ShiftPosfsc)Shifting->InitCpu(npf,npb,Posc,ShiftPosfsc);

  //-Adds variable acceleration from input configuration.
  if(AccInput)AccInput->RunCpu(TimeStep,Gravity,npf,npb,Codec,Posc,Velrhopc,Acec);

  //-Prepare press values for interaction.
  const int n=int(np);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(n>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int p=0;p<n;p++){
    Pressc[p]=fsph::ComputePress(Velrhopc[p].w,CSP);
  }
}

//==============================================================================
/// Prepare variables for interaction functions.
/// Prepara variables para interaccion.
//==============================================================================
void JSphCpu::PreInteraction_Forces(){
  Timersc->TmStart(TMC_CfPreForces);
  //-Assign memory.
  Arc=ArraysCpu->ReserveFloat();
  Acec=ArraysCpu->ReserveFloat3();
  //=========== mdbr
  Rsigmac=ArraysCpu->ReserveSymatrix3f();
  if(ArtificialStress)ArtificialStressc=ArraysCpu->ReserveSymatrix3f();
  //===========
  if(DDTArray)Deltac=ArraysCpu->ReserveFloat();
  if(Shifting)ShiftPosfsc=ArraysCpu->ReserveFloat4();
  Pressc=ArraysCpu->ReserveFloat();
  if(TVisco==VISCO_LaminarSPS)SpsGradvelc=ArraysCpu->ReserveSymatrix3f();

  //-Initialise arrays.
  PreInteractionVars_Forces(Np,Npb);
  if(ArtificialStressc)ComputeArtificialStressArray(Np,Npb,Codec,Velrhopc,Sigmac,ArtificialStressCoef,ArtificialStressc);

  //-Calculate VelMax: Floating object particles are included and do not affect use of periodic condition.
  //-Calcula VelMax: Se incluyen las particulas floatings y no afecta el uso de condiciones periodicas.
  const unsigned pini=(DtAllParticles? 0: Npb);
  VelMax=CalcVelMaxOmp(Np-pini,Velrhopc+pini);
  ViscDtMax=0;
  Timersc->TmStop(TMC_CfPreForces);
}

//==============================================================================
/// Returns maximum velocity from an array tfloat4.
/// Devuelve la velociad maxima de un array tfloat4.
//==============================================================================
float JSphCpu::CalcVelMaxSeq(unsigned np,const tfloat4* velrhop)const{
  float velmax=0;
  for(unsigned p=0;p<np;p++){
    const tfloat4 v=velrhop[p];
    const float v2=v.x*v.x+v.y*v.y+v.z*v.z;
    velmax=max(velmax,v2);
  }
  return(sqrt(velmax));
}

//==============================================================================
/// Returns maximum velocity from an array tfloat4 using OpenMP.
/// Devuelve la velociad maxima de un array tfloat4 usando OpenMP.
//==============================================================================
float JSphCpu::CalcVelMaxOmp(unsigned np,const tfloat4* velrhop)const{
  float velmax=0;
  #ifdef OMP_USE
    if(np>OMP_LIMIT_COMPUTELIGHT){
      const int n=int(np);
      if(n<0)Run_Exceptioon("Number of values is too big.");
      float vmax=0;
      #pragma omp parallel 
      {
        float vmax2=0;
        #pragma omp for nowait
        for(int c=0;c<n;++c){
          const tfloat4 v=velrhop[c];
          const float v2=v.x*v.x+v.y*v.y+v.z*v.z;
          if(vmax2<v2)vmax2=v2;
        }
        #pragma omp critical 
        {
          if(vmax<vmax2)vmax=vmax2;
        }
      }
      //-Saves result.
      velmax=sqrt(vmax);
    }
    else if(np)velmax=CalcVelMaxSeq(np,velrhop);
  #else
    if(np)velmax=CalcVelMaxSeq(np,velrhop);
  #endif
  return(velmax);
}

//==============================================================================
/// Free memory assigned to ArraysCpu.
/// Libera memoria asignada de ArraysCpu.
//==============================================================================
void JSphCpu::PosInteraction_Forces(){
  //-Free memory assigned in PreInteraction_Forces(). | Libera memoria asignada en PreInteraction_Forces().
  ArraysCpu->Free(Arc);          Arc=NULL;
  ArraysCpu->Free(Acec);         Acec=NULL;
  ArraysCpu->Free(Deltac);       Deltac=NULL;
  ArraysCpu->Free(ShiftPosfsc);  ShiftPosfsc=NULL;
  ArraysCpu->Free(Pressc);       Pressc=NULL;
  ArraysCpu->Free(SpsGradvelc);  SpsGradvelc=NULL;
   //-mdbr
  ArraysCpu->Free(Rsigmac);      Rsigmac=NULL;
  ArraysCpu->Free(ArtificialStressc); ArtificialStressc=NULL;
}

//==============================================================================
/// Perform interaction between particles. Bound-Fluid/Float
/// Realiza interaccion entre particulas. Bound-Fluid/Float
//==============================================================================
template<TpKernel tker,TpFtMode ftmode> void JSphCpu::InteractionForcesBound
  (unsigned n,unsigned pinit,StDivDataCpu divdata,const unsigned *dcell
  ,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,const unsigned *idp
  ,float &viscdt,float *ar)const
{
  //-Initialize viscth to calculate max viscdt with OpenMP. | Inicializa viscth para calcular visdt maximo con OpenMP.
  float viscth[OMP_MAXTHREADS*OMP_STRIDE];
  for(int th=0;th<OmpThreads;th++)viscth[th*OMP_STRIDE]=0;
  //-Starts execution using OpenMP.
  const int pfin=int(pinit+n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided)
  #endif
  for(int p1=int(pinit);p1<pfin;p1++){
    float visc=0,arp1=0;

    //-Load data of particle p1. | Carga datos de particula p1.
    const tdouble3 posp1=pos[p1];
    const bool rsymp1=(Symmetry && posp1.y<=KernelSize); //<vs_syymmetry>
    const tfloat4 velrhop1=velrhop[p1];

    //-Search for neighbours in adjacent cells.
    const StNgSearch ngs=nsearch::Init(dcell[p1],false,divdata);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);

      //-Interaction of boundary with type Fluid/Float | Interaccion de Bound con varias Fluid/Float.
      //---------------------------------------------------------------------------------------------
      bool rsym=false; //<vs_syymmetry>
      for(unsigned p2=pif.x;p2<pif.y;p2++){
        const float drx=float(posp1.x-pos[p2].x);
              float dry=float(posp1.y-pos[p2].y);
        if(rsym)    dry=float(posp1.y+pos[p2].y); //<vs_syymmetry>
        const float drz=float(posp1.z-pos[p2].z);
        const float rr2=drx*drx+dry*dry+drz*drz;
        if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
          //-Computes kernel.
          const float fac=fsph::GetKernel_Fac<tker>(CSP,rr2);
          const float frx=fac*drx,fry=fac*dry,frz=fac*drz; //-Gradients.

          //===== Get mass of particle p2 ===== 
          float massp2=MassFluid; //-Contains particle mass of incorrect fluid. | Contiene masa de particula por defecto fluid.
          bool compute=true;      //-Deactivate when using DEM and/or bound-float. | Se desactiva cuando se usa DEM y es bound-float.
          if(USE_FLOATING){
            bool ftp2=CODE_IsFloating(code[p2]);
            if(ftp2)massp2=FtObjs[CODE_GetTypeValue(code[p2])].massp;
            compute=!(USE_FTEXTERNAL && ftp2); //-Deactivate when using DEM/Chrono and/or bound-float. | Se desactiva cuando se usa DEM/Chrono y es bound-float.
          }

          if(compute){
            //-Density derivative (Continuity equation).
            tfloat4 velrhop2=velrhop[p2];
            if(rsym)velrhop2.y=-velrhop2.y; //<vs_syymmetry>
            const float dvx=velrhop1.x-velrhop2.x, dvy=velrhop1.y-velrhop2.y, dvz=velrhop1.z-velrhop2.z;
            if(compute)arp1+=massp2*(dvx*frx+dvy*fry+dvz*frz)*(velrhop1.w/velrhop2.w);

            {//-Viscosity.
              const float dot=drx*dvx + dry*dvy + drz*dvz;
              const float dot_rr2=dot/(rr2+Eta2);
              visc=max(dot_rr2,visc);
            }
          }
          rsym=(rsymp1 && !rsym && float(posp1.y-dry)<=KernelSize); //<vs_syymmetry>
          if(rsym)p2--;                                             //<vs_syymmetry>
        }
        else rsym=false;                                            //<vs_syymmetry>
      }
    }
    //-Sum results together. | Almacena resultados.
    if(arp1||visc){
      ar[p1]+=arp1;
      const int th=omp_get_thread_num();
      if(visc>viscth[th*OMP_STRIDE])viscth[th*OMP_STRIDE]=visc;
    }
  }
  //-Keep max value in viscdt. | Guarda en viscdt el valor maximo.
  for(int th=0;th<OmpThreads;th++)if(viscdt<viscth[th*OMP_STRIDE])viscdt=viscth[th*OMP_STRIDE];
}
//==============================================================================
/// Calculate strain/spin rate tensor
/// Input velgradient (3*3); Ouput strain (3*2)/spin (3*1) rate tensor
//==============================================================================
void GetStrainSpinRateTensor_sym(tfloat3 gradvp1_xx_xy_xz,tfloat3 gradvp1_yx_yy_yz,tfloat3 gradvp1_zx_zy_zz
  ,tsymatrix3f &e_tensor,tfloat3 &w_tensor_xy_yz_xz)
{
  //Build strain rate tensor
  e_tensor.xx=gradvp1_xx_xy_xz.x;		
  e_tensor.yy=gradvp1_yx_yy_yz.y;	  
  e_tensor.zz=gradvp1_zx_zy_zz.z;
  e_tensor.xy=0.5f*(gradvp1_xx_xy_xz.y+gradvp1_yx_yy_yz.x);
  e_tensor.yz=0.5f*(gradvp1_yx_yy_yz.z+gradvp1_zx_zy_zz.y);
  e_tensor.xz=0.5f*(gradvp1_xx_xy_xz.z+gradvp1_zx_zy_zz.x);

  //Build spin rate tensor
  w_tensor_xy_yz_xz.x = 0.5f*(gradvp1_xx_xy_xz.y-gradvp1_yx_yy_yz.x);
  w_tensor_xy_yz_xz.y = 0.5f*(gradvp1_yx_yy_yz.z-gradvp1_zx_zy_zz.y);
  w_tensor_xy_yz_xz.z = 0.5f*(gradvp1_xx_xy_xz.z-gradvp1_zx_zy_zz.x);
}

//==============================================================================
/// Calculate elastic stress rate tensor
/// Input Strain/Spin Rate, Elastic Parameters, Stress, Ouput Elastic Stress Rate Tensor
//==============================================================================
void GetStressRateTensor_Elastic(tsymatrix3f e_tensor,tfloat3 w_tensor_xy_yz_xz
,tsymatrix3f sigma,const float DP_K, const float DP_G,tsymatrix3f &rsigma)
{
  //Build Elastic stiffness matrix
	float K4G3 = float(DP_K + 4.*DP_G / 3.);
	float K2G3 = float(DP_K - 2.*DP_G / 3.);
	float m_a11 = K4G3; float m_a12 = K2G3; float m_a13 = K2G3;
	float m_a21 = K2G3; float m_a22 = K4G3; float m_a23 = K2G3;
	float m_a31 = K2G3; float m_a32 = K2G3; float m_a33 = K4G3; 

  //Get stress, stran rate and spin rate
  float sigmaxx = sigma.xx;
  float sigmaxy = sigma.xy;
  float sigmaxz = sigma.xz;
  float sigmayy = sigma.yy;
  float sigmayz = sigma.yz;
  float sigmazz = sigma.zz;

  float exx = e_tensor.xx;
  float exy = e_tensor.xy;
  float exz = e_tensor.xz;
  float eyy = e_tensor.yy;
  float eyz = e_tensor.yz;
  float ezz = e_tensor.zz;

  float wxy = w_tensor_xy_yz_xz.x;
  float wyz = w_tensor_xy_yz_xz.y;
  float wxz = w_tensor_xy_yz_xz.z;
  
  //Jaumann stress rate
  float Jxx = - 2.f*sigmaxy*wxy - 2.f*sigmaxz*wxz;
  float Jxy = sigmaxx*wxy - sigmayy*wxy - sigmaxz*wyz - sigmayz*wxz;
  float Jxz = sigmaxx*wxz + sigmaxy*wyz - sigmayz*wxy - sigmazz*wxz;
  float Jyy = 2.f*sigmaxy*wxy - 2.f*sigmayz*wyz;
  float Jyz = sigmaxy*wxz + sigmaxz*wxy + sigmayy*wyz - sigmazz*wyz;
  float Jzz = 2.f*sigmaxz*wxz + 2.f*sigmayz*wyz;
 
  //Construct stress rate equation
  rsigma.xx = (m_a11*exx+m_a12*eyy+m_a13*ezz)+Jxx;
  rsigma.yy = (m_a21*exx+m_a22*eyy+m_a23*ezz)+Jyy;
  rsigma.zz = (m_a31*exx+m_a32*eyy+m_a33*ezz)+Jzz;
  rsigma.xy = 2.f*DP_G*exy+Jxy;
  rsigma.yz = 2.f*DP_G*eyz+Jyz;
  rsigma.xz = 2.f*DP_G*exz+Jxz;  
}

//==============================================================================
/// Computes eigenvalues and eigenvectors of a symmetric 3x3 stress tensor.
//==============================================================================
static void ComputeSymmetricEigen3D(const tsymatrix3f &sigma,float eval[3],float evec[3][3]){
  float a[3][3]={
    {sigma.xx,sigma.xy,sigma.xz},
    {sigma.xy,sigma.yy,sigma.yz},
    {sigma.xz,sigma.yz,sigma.zz}
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

//==============================================================================
/// Computes Bui 2008 artificial stress tensor in global coordinates.
//==============================================================================
static tsymatrix3f ComputeBuiArtificialStress(const tsymatrix3f &sigma,const float rhop,const float coef){
  tsymatrix3f rstress={0,0,0,0,0,0};
  if(rhop<=0.f)return(rstress);
  float eval[3];
  float evec[3][3];
  ComputeSymmetricEigen3D(sigma,eval,evec);
  const float rrhop2=1.f/(rhop*rhop);
  float rp[3];
  for(int a=0;a<3;a++)rp[a]=(eval[a]>0.f? -coef*eval[a]*rrhop2: 0.f);
  for(int a=0;a<3;a++){
    const float rx=evec[0][a],ry=evec[1][a],rz=evec[2][a];
    rstress.xx+=rp[a]*rx*rx;
    rstress.yy+=rp[a]*ry*ry;
    rstress.zz+=rp[a]*rz*rz;
    rstress.xy+=rp[a]*rx*ry;
    rstress.yz+=rp[a]*ry*rz;
    rstress.xz+=rp[a]*rx*rz;
  }
  return(rstress);
}

//==============================================================================
/// Precomputes Bui 2008 artificial stress tensor for each non-boundary particle.
//==============================================================================
static void ComputeArtificialStressArray(unsigned np,unsigned npb,const typecode *code,const tfloat4 *velrhop,const tsymatrix3f *sigma,const float coef,tsymatrix3f *artificialstress){
  const int n=int(np);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(n>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int p=0;p<n;p++){
    tsymatrix3f rstress={0,0,0,0,0,0};
    if(unsigned(p)>=npb && !CODE_IsFloating(code[p])){
      rstress=ComputeBuiArtificialStress(sigma[p],velrhop[p].w,coef);
    }
    artificialstress[p]=rstress;
  }
}

//==============================================================================
/// Perform interaction between particles: Fluid/Float-Fluid/Float or Fluid/Float-Bound
/// Realiza interaccion entre particulas: Fluid/Float-Fluid/Float or Fluid/Float-Bound
//==============================================================================
template<TpKernel tker,TpFtMode ftmode,TpVisco tvisco,TpDensity tdensity,bool shift> 
  void JSphCpu::InteractionForcesFluid(unsigned n,unsigned pinit,bool boundp2,float visco
  ,StDivDataCpu divdata,const unsigned *dcell
  ,const tsymatrix3f* tau,tsymatrix3f* gradvel
  ,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,const unsigned *idp
  ,const float *press,const tsymatrix3f *sigma,const tfloat3 *dengradcorr
  ,const tsymatrix3f *artificialstress
  ,float &viscdt,float *ar,tfloat3 *ace,float *delta
  ,TpShifting shiftmode,tfloat4 *shiftposfs,tsymatrix3f *rsigma)const
{
  //-Initialize viscth to calculate viscdt maximo con OpenMP. | Inicializa viscth para calcular visdt maximo con OpenMP.
  float viscth[OMP_MAXTHREADS*OMP_STRIDE];
  for(int th=0;th<OmpThreads;th++)viscth[th*OMP_STRIDE]=0;
  const bool useartstress=(ArtificialStress && !boundp2 && artificialstress);
  const float wabdp=(useartstress? fsph::GetKernel_Wab<tker>(CSP,float(Dp*Dp)): 0.f);
  const float invwabdp=(wabdp>0.f? 1.f/wabdp: 0.f);
  //-Initialise execution with OpenMP. | Inicia ejecucion con OpenMP.
  const int pfin=int(pinit+n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided)
  #endif
  for(int p1=int(pinit);p1<pfin;p1++){
    float visc=0,arp1=0,deltap1=0;
    tfloat3 acep1=TFloat3(0);
    tsymatrix3f gradvelp1={0,0,0,0,0,0};
    tsymatrix3f rsigmap1={0,0,0,0,0,0};//-mdbr
    tsymatrix3f dsigmap1={0,0,0,0,0,0};//-diffusion
    tsymatrix3f e_tensorp1={0,0,0,0,0,0};//-mdbr
    tfloat3 gradvp1_xx_xy_xz=TFloat3(0);
    tfloat3 gradvp1_yx_yy_yz=TFloat3(0);
    tfloat3 gradvp1_zx_zy_zz=TFloat3(0);
    tfloat3 w_tensorp1_xy_yz_xz=TFloat3(0);
    //-Variables for Shifting.
    tfloat4 shiftposfsp1;
    if(shift)shiftposfsp1=shiftposfs[p1];

    //-Obtain data of particle p1 in case of floating objects. | Obtiene datos de particula p1 en caso de existir floatings.
    bool ftp1=false;     //-Indicate if it is floating. | Indica si es floating.
    if(USE_FLOATING){
      ftp1=CODE_IsFloating(code[p1]);
      if(ftp1 && tdensity!=DDT_None)deltap1=FLT_MAX; //-DDT is not applied to floating particles.
      if(ftp1 && tdensity!=DDT_None){dsigmap1.xx=FLT_MAX;}
      if(ftp1 && shift)shiftposfsp1.x=FLT_MAX;  //-For floating objects do not calculate shifting. | Para floatings no se calcula shifting.
    }

    //-Obtain data of particle p1.
    const tdouble3 posp1=pos[p1];
    const tfloat3 velp1=TFloat3(velrhop[p1].x,velrhop[p1].y,velrhop[p1].z);
    const float rhopp1=velrhop[p1].w;
    const float pressp1=press[p1];
    const tsymatrix3f sigmap1=sigma[p1]; //mdbr
    tsymatrix3f artstressp1={0,0,0,0,0,0};
    if(useartstress && !ftp1 && invwabdp>0.f)artstressp1=artificialstress[p1];
    //-Obtains elastic parameters
    float modulus_K=SoilCte.ModulusK;
    float modulus_G=SoilCte.ModulusG;
    float phi=SoilCte.phi;
    const tsymatrix3f taup1=(tvisco==VISCO_Artificial? gradvelp1: tau[p1]);
    const bool rsymp1=(Symmetry && posp1.y<=KernelSize); //<vs_syymmetry>

    //-Search for neighbours in adjacent cells.
    const StNgSearch ngs=nsearch::Init(dcell[p1],boundp2,divdata);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);

      //-Interaction of Fluid with type Fluid or Bound. | Interaccion de Fluid con varias Fluid o Bound.
      //------------------------------------------------------------------------------------------------
      bool rsym=false; //<vs_syymmetry>
      for(unsigned p2=pif.x;p2<pif.y;p2++){
        const float drx=float(posp1.x-pos[p2].x);
              float dry=float(posp1.y-pos[p2].y);
        if(rsym)    dry=float(posp1.y+pos[p2].y); //<vs_syymmetry>
        const float drz=float(posp1.z-pos[p2].z);
        const float rr2=drx*drx+dry*dry+drz*drz;
        if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
          //-Computes kernel.
          float fac;
          float wab=0.f;
          if(useartstress)wab=fsph::GetKernel_WabFac<tker>(CSP,rr2,fac);
          else fac=fsph::GetKernel_Fac<tker>(CSP,rr2);
          const float frx=fac*drx,fry=fac*dry,frz=fac*drz; //-Gradients.

          //===== Get mass of particle p2 ===== 
          float massp2=(boundp2? MassBound: MassFluid); //-Contiene masa de particula segun sea bound o fluid.
          bool ftp2=false;    //-Indicate if it is floating | Indica si es floating.
          bool compute=true;  //-Deactivate when using DEM and if it is of type float-float or float-bound | Se desactiva cuando se usa DEM y es float-float o float-bound.
          //===== Get stress of particle p2 ====
		  const tsymatrix3f sigmap2=sigma[p2]; //mdbr
          if(USE_FLOATING){
            ftp2=CODE_IsFloating(code[p2]);
            if(ftp2)massp2=FtObjs[CODE_GetTypeValue(code[p2])].massp;
            #ifdef DELTA_HEAVYFLOATING
              if(ftp2 && tdensity==DDT_DDT && massp2<=(MassFluid*1.2f))deltap1=FLT_MAX;
            #else
              if(ftp2 && tdensity==DDT_DDT)deltap1=FLT_MAX;
            #endif
            if(ftp2 && shift && shiftmode==SHIFT_NoBound)shiftposfsp1.x=FLT_MAX; //-With floating objects do not use shifting. | Con floatings anula shifting.
            compute=!(USE_FTEXTERNAL && ftp1 && (boundp2 || ftp2)); //-Deactivate when using DEM and if it is of type float-float or float-bound. | Se desactiva cuando se usa DEM y es float-float o float-bound.
          }

          tfloat4 velrhop2=velrhop[p2];
          if(rsym)velrhop2.y=-velrhop2.y; //<vs_syymmetry>

          //-Velocity derivative (Momentum equation).
          if(compute){
            //const float prs=(pressp1+press[p2])/(rhopp1*velrhop2.w) + (tker==KERNEL_Cubic? fsph::GetKernelCubic_Tensil(CSP,rr2,rhopp1,pressp1,velrhop2.w,press[p2]): 0);
            //const float p_vpm=-prs*massp2;
            //acep1.x+=p_vpm*frx; acep1.y+=p_vpm*fry; acep1.z+=p_vpm*frz;
            const float prsxx = massp2*(sigmap1.xx + sigmap2.xx) / (rhopp1*velrhop2.w);
			const float prsyy = massp2*(sigmap1.yy + sigmap2.yy) / (rhopp1*velrhop2.w);
			const float prszz = massp2*(sigmap1.zz + sigmap2.zz) / (rhopp1*velrhop2.w);
			const float prsxy = massp2*(sigmap1.xy + sigmap2.xy) / (rhopp1*velrhop2.w);
			const float prsxz = massp2*(sigmap1.xz + sigmap2.xz) / (rhopp1*velrhop2.w);
			const float prsyz = massp2*(sigmap1.yz + sigmap2.yz) / (rhopp1*velrhop2.w);
			acep1.x += (prsxx*frx+prsxy*fry+prsxz*frz); acep1.y += (prsyy*fry+prsxy*frx+prsyz*frz); acep1.z += (prszz*frz+prsyz*fry+prsxz*frx);//form 1
            if(useartstress && !ftp1 && !ftp2 && invwabdp>0.f){
              const tsymatrix3f artstressp2=artificialstress[p2];
              const float ratio=wab*invwabdp;
              const float arsxx0=artstressp1.xx+artstressp2.xx;
              const float arsyy0=artstressp1.yy+artstressp2.yy;
              const float arszz0=artstressp1.zz+artstressp2.zz;
              const float arsxy0=artstressp1.xy+artstressp2.xy;
              const float arsxz0=artstressp1.xz+artstressp2.xz;
              const float arsyz0=artstressp1.yz+artstressp2.yz;
              if(ratio>0.f && (arsxx0 || arsyy0 || arszz0 || arsxy0 || arsxz0 || arsyz0)){
                const float artmass=massp2*powf(ratio,ArtificialStressExp);
                const float arsxx=artmass*arsxx0;
                const float arsyy=artmass*arsyy0;
                const float arszz=artmass*arszz0;
                const float arsxy=artmass*arsxy0;
                const float arsxz=artmass*arsxz0;
                const float arsyz=artmass*arsyz0;
                acep1.x += (arsxx*frx+arsxy*fry+arsxz*frz);
                acep1.y += (arsyy*fry+arsxy*frx+arsyz*frz);
                acep1.z += (arszz*frz+arsyz*fry+arsxz*frx);
              }
            }
          }

          //-Density derivative (Continuity equation).
          const float dvx=velp1.x-velrhop2.x, dvy=velp1.y-velrhop2.y, dvz=velp1.z-velrhop2.z;
          if(compute)arp1+=massp2*(dvx*frx+dvy*fry+dvz*frz)*(rhopp1/velrhop2.w);

          const float cbar=(float)Cs0;
          const float dot3=(drx*frx+dry*fry+drz*frz);
          //-Density Diffusion Term (Molteni and Colagrossi 2009).
          /*if(tdensity==DDT_DDT && deltap1!=FLT_MAX){
            const float rhop1over2=rhopp1/velrhop2.w;
            const float visc_densi=DDTkh*cbar*(rhop1over2-1.f)/(rr2+Eta2);
            const float dot3=(drx*frx+dry*fry+drz*frz);
            const float delta=visc_densi*dot3*massp2;
            //deltap1=(boundp2? FLT_MAX: deltap1+delta);
            deltap1=(boundp2 && TBoundary==BC_DBC? FLT_MAX: deltap1+delta);
          }*/
          //-Stress Diffusion Term (Form 1)
          if (tdensity == DDT_DDT && dsigmap1.xx != FLT_MAX) {
              const float massrhop = massp2 / velrhop2.w;
              const float visc_stress = DDTkh*cbar*massrhop/(rr2+Eta2);
              const float dsigmaxx = sigmap1.xx - sigmap2.xx;
              const float dsigmayy = sigmap1.yy - sigmap2.yy;
              const float dsigmazz = sigmap1.zz - sigmap2.zz;
              const float dsigmaxy = sigmap1.xy - sigmap2.xy;
              const float dsigmaxz = sigmap1.xz - sigmap2.xz;
              const float dsigmayz = sigmap1.yz - sigmap2.yz;
              dsigmap1.xx = (boundp2 && TBoundary == BC_DBC ? FLT_MAX:dsigmap1.xx+visc_stress*dot3*dsigmaxx);
              dsigmap1.yy += visc_stress * dot3 * dsigmayy;
              dsigmap1.zz += visc_stress * dot3 * dsigmazz;
              dsigmap1.xy += visc_stress * dot3 * dsigmaxy;
              dsigmap1.xz += visc_stress * dot3 * dsigmaxz;
              dsigmap1.yz += visc_stress * dot3 * dsigmayz;
          }
          //-Density Diffusion Term (Fourtakas et al 2019).
          /*if((tdensity==DDT_DDT2 || (tdensity==DDT_DDT2Full && !boundp2)) && deltap1!=FLT_MAX && !ftp2){
            const float rh=1.f+DDTgz*drz;
            const float drhop=RhopZero*pow(rh,1.f/Gamma)-RhopZero;    
            const float visc_densi=DDTkh*cbar*((velrhop2.w-rhopp1)-drhop)/(rr2+Eta2);
            const float dot3=(drx*frx+dry*fry+drz*frz);
            const float delta=visc_densi*dot3*massp2/velrhop2.w;
            deltap1=(boundp2? FLT_MAX: deltap1-delta); //-blocks it makes it boil - bloody DBC
          }*/
          //-Stress Diffusion Term (Form 2)
          if ((tdensity == DDT_DDT2 || (tdensity == DDT_DDT2Full && !boundp2)) && dsigmap1.xx != FLT_MAX && !ftp2) {
              const float massrhop = massp2 / velrhop2.w;
              const float visc_stress = DDTkh*cbar*massrhop/(rr2+Eta2);
              const float dsigmaxx = sigmap1.xx - sigmap2.xx;
              const float dsigmayy = sigmap1.yy - sigmap2.yy;
              const float dsigmazz = sigmap1.zz - sigmap2.zz;
              const float dsigmaxy = sigmap1.xy - sigmap2.xy;
              const float dsigmaxz = sigmap1.xz - sigmap2.xz;
              const float dsigmayz = sigmap1.yz - sigmap2.yz;
              const float dsigzS = RhopZero*Gravity.z*drz;
              const float dsigxS = (1.f-sin(phi)) * dsigzS;
              const float dsigyS = (1.f-sin(phi)) * dsigzS;
              dsigmap1.xx = (boundp2 ? FLT_MAX : dsigmap1.xx + visc_stress * dot3 * (dsigmaxx + dsigxS));
              dsigmap1.yy += visc_stress * dot3 * (dsigmayy + dsigyS);
              dsigmap1.zz += visc_stress * dot3 * (dsigmazz + dsigzS);
              dsigmap1.xy += visc_stress * dot3 * dsigmaxy;
              dsigmap1.xz += visc_stress * dot3 * dsigmaxz;
              dsigmap1.yz += visc_stress * dot3 * dsigmayz;
          }       
          //-Shifting correction.
          if(shift && shiftposfsp1.x!=FLT_MAX){
            const float massrhop=massp2/velrhop2.w;
            const bool noshift=(boundp2 && (shiftmode==SHIFT_NoBound || (shiftmode==SHIFT_NoFixed && CODE_IsFixed(code[p2]))));
            shiftposfsp1.x=(noshift? FLT_MAX: shiftposfsp1.x+massrhop*frx); //-For boundary do not use shifting. | Con boundary anula shifting.
            shiftposfsp1.y+=massrhop*fry;
            shiftposfsp1.z+=massrhop*frz;
            shiftposfsp1.w-=massrhop*(drx*frx+dry*fry+drz*frz);
          }

          //===== Viscosity ===== 
          if(compute){
            const float dot=drx*dvx + dry*dvy + drz*dvz;
            const float dot_rr2=dot/(rr2+Eta2);
            visc=max(dot_rr2,visc);
            ///SPH velocity gradients calculation
            const float volp2=-massp2/velrhop2.w;
            float dv=dvx*volp2;  gradvp1_xx_xy_xz.x+=dv*frx; gradvp1_xx_xy_xz.y+=dv*fry; gradvp1_xx_xy_xz.z+=dv*frz;
                  dv=dvy*volp2;  gradvp1_yx_yy_yz.x+=dv*frx; gradvp1_yx_yy_yz.y+=dv*fry; gradvp1_yx_yy_yz.z+=dv*frz;
                  dv=dvz*volp2;  gradvp1_zx_zy_zz.x+=dv*frx; gradvp1_zx_zy_zz.y+=dv*fry; gradvp1_zx_zy_zz.z+=dv*frz;
            if(tvisco==VISCO_Artificial){//-Artificial viscosity.
              if(dot<0){
                const float amubar=KernelH*dot_rr2;  //amubar=CTE.h*dot/(rr2+CTE.eta2);
                const float robar=(rhopp1+velrhop2.w)*0.5f;
                const float pi_visc=(-visco*cbar*amubar/robar)*massp2;
                acep1.x-=pi_visc*frx; acep1.y-=pi_visc*fry; acep1.z-=pi_visc*frz;
              }
            }
            else if(tvisco==VISCO_LaminarSPS){//-Laminar+SPS viscosity. 
              {//-Laminar contribution.
                const float robar2=(rhopp1+velrhop2.w);
                const float temp=4.f*visco/((rr2+Eta2)*robar2);  //-Simplification of: temp=2.0f*visco/((rr2+CTE.eta2)*robar); robar=(rhopp1+velrhop2.w)*0.5f;
                const float vtemp=massp2*temp*(drx*frx+dry*fry+drz*frz);  
                acep1.x+=vtemp*dvx; acep1.y+=vtemp*dvy; acep1.z+=vtemp*dvz;
              }
              //-SPS turbulence model.
              /*float tau_xx=taup1.xx,tau_xy=taup1.xy,tau_xz=taup1.xz; //-taup1 is always zero when p1 is not a fluid particle. | taup1 siempre es cero cuando p1 no es fluid.
              float tau_yy=taup1.yy,tau_yz=taup1.yz,tau_zz=taup1.zz;
              if(!boundp2 && !ftp2){//-When p2 is a fluid particle. 
                tau_xx+=tau[p2].xx; tau_xy+=tau[p2].xy; tau_xz+=tau[p2].xz;
                tau_yy+=tau[p2].yy; tau_yz+=tau[p2].yz; tau_zz+=tau[p2].zz;
              }
              acep1.x+=massp2*(tau_xx*frx + tau_xy*fry + tau_xz*frz);
              acep1.y+=massp2*(tau_xy*frx + tau_yy*fry + tau_yz*frz);
              acep1.z+=massp2*(tau_xz*frx + tau_yz*fry + tau_zz*frz);
              //-Velocity gradients.
              if(!ftp1){//-When p1 is a fluid particle. 
                const float volp2=-massp2/velrhop2.w;
                float dv=dvx*volp2; gradvelp1.xx+=dv*frx; gradvelp1.xy+=dv*fry; gradvelp1.xz+=dv*frz;
                      dv=dvy*volp2; gradvelp1.xy+=dv*frx; gradvelp1.yy+=dv*fry; gradvelp1.yz+=dv*frz;
                      dv=dvz*volp2; gradvelp1.xz+=dv*frx; gradvelp1.yz+=dv*fry; gradvelp1.zz+=dv*frz;
                //-To compute tau terms we assume that gradvel.xy=gradvel.dudy+gradvel.dvdx, gradvel.xz=gradvel.dudz+gradvel.dwdx, gradvel.yz=gradvel.dvdz+gradvel.dwdy
                //-so only 6 elements are needed instead of 3x3.
              }*/
            }
          }
          rsym=(rsymp1 && !rsym && float(posp1.y-dry)<=KernelSize); //<vs_syymmetry>
          if(rsym)p2--;                                             //<vs_syymmetry>
        }
        else rsym=false;                                            //<vs_syymmetry>
      }
    }
    //Calculate strain/spin rate tensor mdbr
    GetStrainSpinRateTensor_sym(gradvp1_xx_xy_xz,gradvp1_yx_yy_yz,gradvp1_zx_zy_zz,e_tensorp1,w_tensorp1_xy_yz_xz);
    //Calculate stress rate tensor mdbr
    GetStressRateTensor_Elastic(e_tensorp1,w_tensorp1_xy_yz_xz,sigmap1,modulus_K,modulus_G,rsigmap1);
    //-Sum results together. | Almacena resultados.
    if(shift||arp1||acep1.x||acep1.y||acep1.z||visc){
      if(tdensity!=DDT_None){
        if(delta)delta[p1]=(delta[p1]==FLT_MAX || deltap1==FLT_MAX? FLT_MAX: delta[p1]+deltap1);
        else if(deltap1!=FLT_MAX)arp1+=deltap1;
      }
      if(dsigmap1.xx!=FLT_MAX){
        rsigmap1.xx+=dsigmap1.xx;
        rsigmap1.xy+=dsigmap1.xy;
        rsigmap1.xz+=dsigmap1.xz;
        rsigmap1.yy+=dsigmap1.yy;
        rsigmap1.yz+=dsigmap1.yz;
        rsigmap1.zz+=dsigmap1.zz;
      }
      ar[p1]+=arp1;
      ace[p1]=ace[p1]+acep1;
      //-mdbr
      rsigma[p1].xx+=rsigmap1.xx;
      rsigma[p1].xy+=rsigmap1.xy;
      rsigma[p1].xz+=rsigmap1.xz;
      rsigma[p1].yy+=rsigmap1.yy;
      rsigma[p1].yz+=rsigmap1.yz;
      rsigma[p1].zz+=rsigmap1.zz;
      //====
      const int th=omp_get_thread_num();
      if(visc>viscth[th*OMP_STRIDE])viscth[th*OMP_STRIDE]=visc;
      if(tvisco==VISCO_LaminarSPS){
        gradvel[p1].xx+=gradvelp1.xx;
        gradvel[p1].xy+=gradvelp1.xy;
        gradvel[p1].xz+=gradvelp1.xz;
        gradvel[p1].yy+=gradvelp1.yy;
        gradvel[p1].yz+=gradvelp1.yz;
        gradvel[p1].zz+=gradvelp1.zz;
      }
      if(shift)shiftposfs[p1]=shiftposfsp1;
    }
  }
  //-Keep max value in viscdt. | Guarda en viscdt el valor maximo.
  for(int th=0;th<OmpThreads;th++)if(viscdt<viscth[th*OMP_STRIDE])viscdt=viscth[th*OMP_STRIDE];
}

//==============================================================================
/// Perform DEM interaction between particles Floating-Bound & Floating-Floating //(DEM)
/// Realiza interaccion DEM entre particulas Floating-Bound & Floating-Floating //(DEM)
//==============================================================================
void JSphCpu::InteractionForcesDEM(unsigned nfloat,StDivDataCpu divdata,const unsigned *dcell
  ,const unsigned *ftridp,const StDemData* demdata
  ,const tdouble3 *pos,const tfloat4 *velrhop
  ,const typecode *code,const unsigned *idp
  ,float &viscdt,tfloat3 *ace)const
{
  //-Initialise demdtth to calculate max demdt with OpenMP. | Inicializa demdtth para calcular demdt maximo con OpenMP.
  float demdtth[OMP_MAXTHREADS*OMP_STRIDE];
  for(int th=0;th<OmpThreads;th++)demdtth[th*OMP_STRIDE]=-FLT_MAX;
  //-Initialise execution with OpenMP. | Inicia ejecucion con OpenMP.
  const int nft=int(nfloat);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided)
  #endif
  for(int cf=0;cf<nft;cf++){
    const unsigned p1=ftridp[cf];
    if(p1!=UINT_MAX){
      float demdtp1=0;
      tfloat3 acep1=TFloat3(0);

      //-Get data of particle p1.
      const tdouble3 posp1=pos[p1];
      const typecode tavp1=CODE_GetTypeAndValue(code[p1]);
      const float masstotp1=demdata[tavp1].mass;
      const float taup1=demdata[tavp1].tau;
      const float kfricp1=demdata[tavp1].kfric;
      const float restitup1=demdata[tavp1].restitu;
      const float ftmassp1=demdata[tavp1].massp;

      //-Search for neighbours in adjacent cells (first bound and then fluid+floating).
      for(byte tpfluid=0;tpfluid<=1;tpfluid++){
        const StNgSearch ngs=nsearch::Init(dcell[p1],!tpfluid,divdata);
        for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
          const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);

          //-Interaction of Floating Object particles with type Fluid or Bound. | Interaccion de Floating con varias Fluid o Bound.
          //-----------------------------------------------------------------------------------------------------------------------
          for(unsigned p2=pif.x;p2<pif.y;p2++)if(CODE_IsNotFluid(code[p2]) && tavp1!=CODE_GetTypeAndValue(code[p2])){
            const float drx=float(posp1.x-pos[p2].x);
            const float dry=float(posp1.y-pos[p2].y);
            const float drz=float(posp1.z-pos[p2].z);
            const float rr2=drx*drx+dry*dry+drz*drz;
            const float rad=sqrt(rr2);

            //-Calculate max value of demdt. | Calcula valor maximo de demdt.
            const typecode tavp2=CODE_GetTypeAndValue(code[p2]);
            const float masstotp2=demdata[tavp2].mass;
            const float taup2=demdata[tavp2].tau;
            const float kfricp2=demdata[tavp2].kfric;
            const float restitup2=demdata[tavp2].restitu;
            //const StDemData *demp2=demobjs+CODE_GetTypeAndValue(code[p2]);

            const float nu_mass=(!tpfluid? masstotp1/2: masstotp1*masstotp2/(masstotp1+masstotp2)); //-Con boundary toma la propia masa del floating 1.
            const float kn=4/(3*(taup1+taup2))*sqrt(float(Dp)/4); //-Generalized rigidity - Lemieux 2008.
            const float dvx=velrhop[p1].x-velrhop[p2].x, dvy=velrhop[p1].y-velrhop[p2].y, dvz=velrhop[p1].z-velrhop[p2].z; //vji
            const float nx=drx/rad, ny=dry/rad, nz=drz/rad; //normal_ji               
            const float vn=dvx*nx+dvy*ny+dvz*nz; //vji.nji
            const float demvisc=0.2f/(3.21f*(pow(nu_mass/kn,0.4f)*pow(fabs(vn),-0.2f))/40.f);
            if(demdtp1<demvisc)demdtp1=demvisc;

            const float over_lap=1.0f*float(Dp)-rad; //-(ri+rj)-|dij|
            if(over_lap>0.0f){ //-Contact.
              //-Normal.
              const float eij=(restitup1+restitup2)/2;
              const float gn=-(2.0f*log(eij)*sqrt(nu_mass*kn))/(sqrt(float(PI)+log(eij)*log(eij))); //-Generalized damping - Cummins 2010.
              //const float gn=0.08f*sqrt(nu_mass*sqrt(float(Dp)/2)/((taup1+taup2)/2)); //-Generalized damping - Lemieux 2008.
              const float rep=kn*pow(over_lap,1.5f);
              const float fn=rep-gn*pow(over_lap,0.25f)*vn;
              float acef=fn/ftmassp1; //-Divides by the mass of particle to obtain the acceleration.
              acep1.x+=(acef*nx); acep1.y+=(acef*ny); acep1.z+=(acef*nz); //-Force is applied in the normal between the particles.
              //-Tangential.
              const float dvxt=dvx-vn*nx, dvyt=dvy-vn*ny, dvzt=dvz-vn*nz; //Vji_t
              const float vt=sqrt(dvxt*dvxt + dvyt*dvyt + dvzt*dvzt);
              float tx=0, ty=0, tz=0; //-Tang vel unit vector.
              if(vt!=0){ tx=dvxt/vt; ty=dvyt/vt; tz=dvzt/vt; }
              const float ft_elast=2*(kn*float(DemDtForce)-gn)*vt/7; //-Elastic frictional string -->  ft_elast=2*(kn*fdispl-gn*vt)/7; fdispl=dtforce*vt;
              const float kfric_ij=(kfricp1+kfricp2)/2;
              float ft=kfric_ij*fn*tanh(8*vt);  //-Coulomb.
              ft=(ft<ft_elast? ft: ft_elast);   //-Not above yield criteria, visco-elastic model.
              acef=ft/ftmassp1; //-Divides by the mass of particle to obtain the acceleration.
              acep1.x+=(acef*tx); acep1.y+=(acef*ty); acep1.z+=(acef*tz);
            } 
          }
        }
      }
      //-Sum results together. | Almacena resultados.
      if(acep1.x||acep1.y||acep1.z){
        ace[p1]=ace[p1]+acep1;
        const int th=omp_get_thread_num();
        if(demdtth[th*OMP_STRIDE]<demdtp1)demdtth[th*OMP_STRIDE]=demdtp1;
      }
    }
  }
  //-Update viscdt with max value of viscdt or demdt* | Actualiza viscdt con el valor maximo de viscdt y demdt*.
  float demdt=demdtth[0];
  for(int th=1;th<OmpThreads;th++)if(demdt<demdtth[th*OMP_STRIDE])demdt=demdtth[th*OMP_STRIDE];
  if(viscdt<demdt)viscdt=demdt;
}


//==============================================================================
/// Computes sub-particle stress tensor (Tau) for SPS turbulence model.   
//==============================================================================
void JSphCpu::ComputeSpsTau(unsigned n,unsigned pini,const tfloat4 *velrhop,const tsymatrix3f *gradvel,tsymatrix3f *tau)const{
  const int pfin=int(pini+n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static)
  #endif
  for(int p=int(pini);p<pfin;p++){
    const tsymatrix3f gradvel=SpsGradvelc[p];
    const float pow1=gradvel.xx*gradvel.xx + gradvel.yy*gradvel.yy + gradvel.zz*gradvel.zz;
    const float prr=pow1+pow1 + gradvel.xy*gradvel.xy + gradvel.xz*gradvel.xz + gradvel.yz*gradvel.yz;
    const float visc_sps=SpsSmag*sqrt(prr);
    const float div_u=gradvel.xx+gradvel.yy+gradvel.zz;
    const float sps_k=(2.0f/3.0f)*visc_sps*div_u;
    const float sps_blin=SpsBlin*prr;
    const float sumsps=-(sps_k+sps_blin);
    const float twovisc_sps=(visc_sps+visc_sps);
    const float one_rho2=1.0f/velrhop[p].w;   
    tau[p].xx=one_rho2*(twovisc_sps*gradvel.xx +sumsps);
    tau[p].xy=one_rho2*(visc_sps   *gradvel.xy);
    tau[p].xz=one_rho2*(visc_sps   *gradvel.xz);
    tau[p].yy=one_rho2*(twovisc_sps*gradvel.yy +sumsps);
    tau[p].yz=one_rho2*(visc_sps   *gradvel.yz);
    tau[p].zz=one_rho2*(twovisc_sps*gradvel.zz +sumsps);
  }
}

//==============================================================================
/// Interaction of Fluid-Fluid/Bound & Bound-Fluid (forces and DEM).
/// Interaccion Fluid-Fluid/Bound & Bound-Fluid (forces and DEM).
//==============================================================================
template<TpKernel tker,TpFtMode ftmode,TpVisco tvisco,TpDensity tdensity,bool shift>
  void JSphCpu::Interaction_ForcesCpuT(const stinterparmsc &t,StInterResultc &res)const
{
  float viscdt=res.viscdt;
  if(t.npf){
    //-Interaction Fluid-Fluid.
    InteractionForcesFluid<tker,ftmode,tvisco,tdensity,shift> (t.npf,t.npb,false,Visco                 
      ,t.divdata,t.dcell,t.spstau,t.spsgradvel,t.pos,t.velrhop,t.code,t.idp,t.press,t.sigma,t.dengradcorr,t.artificialstress
      ,viscdt,t.ar,t.ace,t.delta,t.shiftmode,t.shiftposfs,t.rsigma);
    //-Interaction Fluid-Bound.
    InteractionForcesFluid<tker,ftmode,tvisco,tdensity,shift> (t.npf,t.npb,true ,Visco*ViscoBoundFactor
      ,t.divdata,t.dcell,t.spstau,t.spsgradvel,t.pos,t.velrhop,t.code,t.idp,t.press,t.sigma,NULL,t.artificialstress
      ,viscdt,t.ar,t.ace,t.delta,t.shiftmode,t.shiftposfs,t.rsigma);

    //-Interaction of DEM Floating-Bound & Floating-Floating. //(DEM)
    if(UseDEM)InteractionForcesDEM(CaseNfloat,t.divdata,t.dcell
      ,FtRidp,DemData,t.pos,t.velrhop,t.code,t.idp,viscdt,t.ace);

    //-Computes tau for Laminar+SPS.
    if(tvisco==VISCO_LaminarSPS)ComputeSpsTau(t.npf,t.npb,t.velrhop,t.spsgradvel,t.spstau);
  }
  if(t.npbok){
    //-Interaction Bound-Fluid.
    InteractionForcesBound<tker,ftmode> (t.npbok,0,t.divdata,t.dcell
      ,t.pos,t.velrhop,t.code,t.idp,viscdt,t.ar);
  }
  res.viscdt=viscdt;
}
//==============================================================================
template<TpKernel tker,TpFtMode ftmode,TpVisco tvisco,TpDensity tdensity> void JSphCpu::Interaction_Forces_ct5(const stinterparmsc &t,StInterResultc &res)const{
  if(Shifting)Interaction_ForcesCpuT<tker,ftmode,tvisco,tdensity,true >(t,res);
  else        Interaction_ForcesCpuT<tker,ftmode,tvisco,tdensity,false>(t,res);
}
//==============================================================================
template<TpKernel tker,TpFtMode ftmode,TpVisco tvisco> void JSphCpu::Interaction_Forces_ct4(const stinterparmsc &t,StInterResultc &res)const{
       if(TDensity==DDT_None)    Interaction_Forces_ct5<tker,ftmode,tvisco,DDT_None    >(t,res);
  else if(TDensity==DDT_DDT)     Interaction_Forces_ct5<tker,ftmode,tvisco,DDT_DDT     >(t,res);
  else if(TDensity==DDT_DDT2)    Interaction_Forces_ct5<tker,ftmode,tvisco,DDT_DDT2    >(t,res);
  else if(TDensity==DDT_DDT2Full)Interaction_Forces_ct5<tker,ftmode,tvisco,DDT_DDT2Full>(t,res);
}
//==============================================================================
template<TpKernel tker,TpFtMode ftmode> void JSphCpu::Interaction_Forces_ct3(const stinterparmsc &t,StInterResultc &res)const{
       if(TVisco==VISCO_Artificial)Interaction_Forces_ct4<tker,ftmode,VISCO_Artificial>(t,res);
  else if(TVisco==VISCO_LaminarSPS)Interaction_Forces_ct4<tker,ftmode,VISCO_LaminarSPS>(t,res);
}
//==============================================================================
template<TpKernel tker> void JSphCpu::Interaction_Forces_ct2(const stinterparmsc &t,StInterResultc &res)const{
       if(FtMode==FTMODE_None)Interaction_Forces_ct3<tker,FTMODE_None>(t,res);
  else if(FtMode==FTMODE_Sph )Interaction_Forces_ct3<tker,FTMODE_Sph >(t,res);
  else if(FtMode==FTMODE_Ext )Interaction_Forces_ct3<tker,FTMODE_Ext >(t,res);
}
//==============================================================================
void JSphCpu::Interaction_Forces_ct(const stinterparmsc &t,StInterResultc &res)const{
       if(TKernel==KERNEL_Wendland)  Interaction_Forces_ct2<KERNEL_Wendland>(t,res);
  else if(TKernel==KERNEL_Cubic)     Interaction_Forces_ct2<KERNEL_Cubic   >(t,res);
}

//==============================================================================
/// Computes diagnostic skeleton velocity divergence for material particles.
//==============================================================================
template<TpKernel tker> void JSphCpu::ComputeHydroDivVelT(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,float *divvel)const
{
  const unsigned np=pini+n;
  memset(divvel,0,sizeof(float)*np);
  const int nint=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided) if(nint>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int cp=0;cp<nint;cp++){
    const unsigned p1=pini+unsigned(cp);
    if(!CODE_IsFluid(code[p1]))continue;

    float divp1=0;
    const tdouble3 posp1=pos[p1];
    const tfloat4 velrhop1=velrhop[p1];
    const tfloat3 velp1=TFloat3(velrhop1.x,velrhop1.y,velrhop1.z);
    const bool rsymp1=(Symmetry && posp1.y<=KernelSize); //<vs_syymmetry>

    const StNgSearch ngs=nsearch::Init(dcell[p1],false,divdata);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
      bool rsym=false; //<vs_syymmetry>
      for(unsigned p2=pif.x;p2<pif.y;p2++){
        if(!CODE_IsFluid(code[p2])){ rsym=false; continue; }
        const float drx=float(posp1.x-pos[p2].x);
              float dry=float(posp1.y-pos[p2].y);
        if(rsym)dry=float(posp1.y+pos[p2].y); //<vs_syymmetry>
        const float drz=float(posp1.z-pos[p2].z);
        const float rr2=drx*drx+dry*dry+drz*drz;
        if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
          const float fac=fsph::GetKernel_Fac<tker>(CSP,rr2);
          const float frx=fac*drx,fry=fac*dry,frz=fac*drz;
          tfloat4 velrhop2=velrhop[p2];
          if(rsym)velrhop2.y=-velrhop2.y; //<vs_syymmetry>
          const float volp2=MassFluid/velrhop2.w;
          divp1+=volp2*((velrhop2.x-velp1.x)*frx+(velrhop2.y-velp1.y)*fry+(velrhop2.z-velp1.z)*frz);
          rsym=(rsymp1 && !rsym && float(posp1.y-dry)<=KernelSize); //<vs_syymmetry>
          if(rsym)p2--;                                             //<vs_syymmetry>
        }
        else rsym=false;                                            //<vs_syymmetry>
      }
    }
    divvel[p1]=divp1;
  }
}

//==============================================================================
/// Computes diagnostic skeleton velocity divergence for material particles.
//==============================================================================
void JSphCpu::ComputeHydroDivVel(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,float *divvel)const
{
       if(TKernel==KERNEL_Wendland)ComputeHydroDivVelT<KERNEL_Wendland>(n,pini,divdata,dcell,pos,velrhop,code,divvel);
  else if(TKernel==KERNEL_Cubic)   ComputeHydroDivVelT<KERNEL_Cubic   >(n,pini,divdata,dcell,pos,velrhop,code,divvel);
}

//==============================================================================
/// Computes PR pore-pressure-rate contribution from velocity divergence and hydraulic head diffusion.
//==============================================================================
void JSphCpu::ComputeHydroPorePressRatePR(unsigned n,unsigned pini
  ,const typecode *code,const float *divvel,const float *lapporepress,const float *lapz,float *porepressrate)const
{
  if(Porosity0<=0.f || Porosity0>=1.f)Run_Exceptioon("Porosity0 must be between 0 and 1 for PR pore-pressure-rate update.");
  if(WaterBulkModulus<=0.f)Run_Exceptioon("WaterBulkModulus must be greater than zero for PR pore-pressure-rate update.");
  if(WaterDensity<=0.f)Run_Exceptioon("WaterDensity must be greater than zero for PR pore-pressure-rate update.");
  const float gmag=sqrt(Gravity.x*Gravity.x+Gravity.y*Gravity.y+Gravity.z*Gravity.z);
  if(HydraulicConductivity>0.f && gmag<=0.f)Run_Exceptioon("Gravity magnitude must be greater than zero when HydraulicConductivity is enabled.");
  const unsigned np=pini+n;
  memset(porepressrate,0,sizeof(float)*np);
  const float factor=WaterBulkModulus/Porosity0;
  const float difcoef=(HydraulicConductivity>0.f? HydraulicConductivity/(WaterDensity*gmag): 0.f);
  const int nint=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(nint>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int cp=0;cp<nint;cp++){
    const unsigned p1=pini+unsigned(cp);
    if(CODE_IsFluid(code[p1]))porepressrate[p1]=factor*(divvel[p1]+difcoef*lapporepress[p1]+HydraulicConductivity*lapz[p1]);
  }
}

//==============================================================================
/// Updates pore pressure explicitly for material particles.
//==============================================================================
void JSphCpu::UpdatePorePressure(unsigned n,unsigned pini,const typecode *code,double dt
  ,double *porepress,const float *porepressrate)
{
  if(!HydromechCoupling || PorePressureModel!=1 || !porepress || !porepressrate)return;
  if(PorePressureDtActive && dt>PorePressureDt*(1.+1.e-6) && !PorePressureUpdateDtPrint){
    Log->PrintWarning(fun::PrintStr("Pore-pressure update dt=%g is greater than dt_pore=%g. This can occur on the first Symplectic step before the next-step dt restriction is applied.",dt,PorePressureDt));
    PorePressureUpdateDtPrint=true;
  }
  const int nint=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(nint>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int cp=0;cp<nint;cp++){
    const unsigned p1=pini+unsigned(cp);
    if(CODE_IsFluid(code[p1]))porepress[p1]+=double(porepressrate[p1])*dt;
  }
}

//==============================================================================
/// Computes diagnostic pore-pressure Laplacian for material particles.
//==============================================================================
template<TpKernel tker> void JSphCpu::ComputeHydroLapPorePressT(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,const double *porepress,float *lapporepress)const
{
  const unsigned np=pini+n;
  memset(lapporepress,0,sizeof(float)*np);
  const int nint=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided) if(nint>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int cp=0;cp<nint;cp++){
    const unsigned p1=pini+unsigned(cp);
    if(!CODE_IsFluid(code[p1]))continue;

    double lapp1=0;
    const tdouble3 posp1=pos[p1];
    const double pwp1=porepress[p1];
    const bool rsymp1=(Symmetry && posp1.y<=KernelSize); //<vs_syymmetry>

    const StNgSearch ngs=nsearch::Init(dcell[p1],false,divdata);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
      bool rsym=false; //<vs_syymmetry>
      for(unsigned p2=pif.x;p2<pif.y;p2++){
        if(!CODE_IsFluid(code[p2])){ rsym=false; continue; }
        const float drx=float(posp1.x-pos[p2].x);
              float dry=float(posp1.y-pos[p2].y);
        if(rsym)dry=float(posp1.y+pos[p2].y); //<vs_syymmetry>
        const float drz=float(posp1.z-pos[p2].z);
        const float rr2=drx*drx+dry*dry+drz*drz;
        if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
          const float fac=fsph::GetKernel_Fac<tker>(CSP,rr2);
          const float frx=fac*drx,fry=fac*dry,frz=fac*drz;
          const float dotrgrad=drx*frx+dry*fry+drz*frz;
          const float volp2=MassFluid/velrhop[p2].w;
          lapp1+=2.*double(volp2)*(pwp1-porepress[p2])*double(dotrgrad)/(double(rr2)+ALMOSTZERO);
          rsym=(rsymp1 && !rsym && float(posp1.y-dry)<=KernelSize); //<vs_syymmetry>
          if(rsym)p2--;                                             //<vs_syymmetry>
        }
        else rsym=false;                                            //<vs_syymmetry>
      }
    }
    lapporepress[p1]=float(lapp1);
  }
}

//==============================================================================
/// Computes diagnostic pore-pressure Laplacian for material particles.
//==============================================================================
void JSphCpu::ComputeHydroLapPorePress(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,const double *porepress,float *lapporepress)const
{
       if(TKernel==KERNEL_Wendland)ComputeHydroLapPorePressT<KERNEL_Wendland>(n,pini,divdata,dcell,pos,velrhop,code,porepress,lapporepress);
  else if(TKernel==KERNEL_Cubic)   ComputeHydroLapPorePressT<KERNEL_Cubic   >(n,pini,divdata,dcell,pos,velrhop,code,porepress,lapporepress);
}

//==============================================================================
/// Computes diagnostic elevation-head Laplacian for material particles.
//==============================================================================
template<TpKernel tker> void JSphCpu::ComputeHydroLapZT(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,float *lapz)const
{
  const unsigned np=pini+n;
  memset(lapz,0,sizeof(float)*np);
  const double gmag=sqrt(double(Gravity.x)*double(Gravity.x)+double(Gravity.y)*double(Gravity.y)+double(Gravity.z)*double(Gravity.z));
  if(gmag<=0)return;
  const double invg=1./gmag;
  const int nint=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided) if(nint>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int cp=0;cp<nint;cp++){
    const unsigned p1=pini+unsigned(cp);
    if(!CODE_IsFluid(code[p1]))continue;

    float lapp1=0;
    const tdouble3 posp1=pos[p1];
    const double zp1=-(double(posp1.x)*Gravity.x+double(posp1.y)*Gravity.y+double(posp1.z)*Gravity.z)*invg;
    const bool rsymp1=(Symmetry && posp1.y<=KernelSize); //<vs_syymmetry>

    const StNgSearch ngs=nsearch::Init(dcell[p1],false,divdata);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
      bool rsym=false; //<vs_syymmetry>
      for(unsigned p2=pif.x;p2<pif.y;p2++){
        if(!CODE_IsFluid(code[p2])){ rsym=false; continue; }
        const tdouble3 posp2=pos[p2];
        const float drx=float(posp1.x-posp2.x);
              float dry=float(posp1.y-posp2.y);
        const double posp2y=(rsym? -posp2.y: posp2.y); //<vs_syymmetry>
        if(rsym)dry=float(posp1.y+posp2.y);            //<vs_syymmetry>
        const float drz=float(posp1.z-posp2.z);
        const float rr2=drx*drx+dry*dry+drz*drz;
        if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
          const float fac=fsph::GetKernel_Fac<tker>(CSP,rr2);
          const float frx=fac*drx,fry=fac*dry,frz=fac*drz;
          const float dotrgrad=drx*frx+dry*fry+drz*frz;
          const float volp2=MassFluid/velrhop[p2].w;
          const double zp2=-(double(posp2.x)*Gravity.x+posp2y*Gravity.y+double(posp2.z)*Gravity.z)*invg;
          lapp1+=2.f*volp2*float(zp1-zp2)*dotrgrad/(rr2+ALMOSTZERO);
          rsym=(rsymp1 && !rsym && float(posp1.y-dry)<=KernelSize); //<vs_syymmetry>
          if(rsym)p2--;                                             //<vs_syymmetry>
        }
        else rsym=false;                                            //<vs_syymmetry>
      }
    }
    lapz[p1]=lapp1;
  }
}

//==============================================================================
/// Computes diagnostic elevation-head Laplacian for material particles.
//==============================================================================
void JSphCpu::ComputeHydroLapZ(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,float *lapz)const
{
       if(TKernel==KERNEL_Wendland)ComputeHydroLapZT<KERNEL_Wendland>(n,pini,divdata,dcell,pos,velrhop,code,lapz);
  else if(TKernel==KERNEL_Cubic)   ComputeHydroLapZT<KERNEL_Cubic   >(n,pini,divdata,dcell,pos,velrhop,code,lapz);
}

//==============================================================================
/// Perform interaction between ghost nodes of boundaries and fluid.
//==============================================================================
template<TpKernel tker,bool sim2d,TpSlipMode tslip> void JSphCpu::InteractionMdbcCorrectionT2
  (unsigned n,StDivDataCpu divdata,float determlimit,float mdbcthreshold
  ,const tdouble3 *pos,const typecode *code,const unsigned *idp
  ,const tfloat3 *boundnormal,const tfloat3 *motionvel,tfloat4 *velrhop,tsymatrix3f* sigma)
{
  if(tslip==SLIP_FreeSlip)Run_Exceptioon("SlipMode=\'Free slip\' is not yet implemented...");
  const int nn=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided)
  #endif
  for(int p1=0;p1<nn;p1++)if(boundnormal[p1]!=TFloat3(0)){
    float rhopfinal=FLT_MAX;
    tfloat3 velrhopfinal=TFloat3(0);
    tsymatrix3f sigmafinal={0,0,0,0,0,0};//mdbr
    float sumwab=0;

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
          const tsymatrix3f sigmap2=sigma[p2];//mdbr
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
          if(tslip!=SLIP_Vel0){
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
        if(a_corr2.a11>0&&tslip!=SLIP_Vel0){
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
        if(a_corr3.a11>0&&tslip!=SLIP_Vel0){
          velrhopfinal.x=float(velp1.x/a_corr3.a11);
          velrhopfinal.y=float(velp1.y/a_corr3.a11);
          velrhopfinal.z=float(velp1.z/a_corr3.a11);
        }
      }
      //-Store the results.
      rhopfinal=RhopZero;//rhopfinal=(rhopfinal!=FLT_MAX? rhopfinal: RhopZero);
      if(tslip==SLIP_Vel0){//-DBC vel=0
        velrhop[p1].w=rhopfinal;
        sigma[p1] = sigmafinal;
      }
      if(tslip==SLIP_NoSlip){//-No-Slip
        const tfloat3 v=motionvel[p1];
        velrhop[p1]=TFloat4(v.x+v.x-velrhopfinal.x,v.y+v.y-velrhopfinal.y,v.z+v.z-velrhopfinal.z,rhopfinal);
        sigma[p1] = sigmafinal;
      }
      if(tslip==SLIP_FreeSlip){//-No-Penetration and free slip    SHABA

		tfloat3 FSVelFinal; // final free slip boundary velocity
		const tfloat3 v = motionvel[p1];
		float motion = sqrt(v.x*v.x + v.y*v.y + v.z*v.z); // to check if boundary moving
		float norm = sqrt(boundnormal[p1].x*boundnormal[p1].x + boundnormal[p1].y*boundnormal[p1].y + boundnormal[p1].z*boundnormal[p1].z);
		tfloat3 normal; // creating a normailsed boundary normal
		normal.x = fabs(boundnormal[p1].x )/ norm; normal.y = fabs(boundnormal[p1].y) / norm; normal.z = fabs(boundnormal[p1].z) / norm;
		
		// finding the velocity componants normal and tangential to boundary 
		tfloat3 normvel = TFloat3(velrhopfinal.x*normal.x, velrhopfinal.y*normal.y, velrhopfinal.z*normal.z); // velocity in direction of normal pointin ginto fluid)
		tfloat3 tangvel = TFloat3(velrhopfinal.x - normvel.x, velrhopfinal.y - normvel.y, velrhopfinal.z - normvel.z); // velocity tangential to normal
		
		if (motion > 0.f) { // if moving boundary
			tfloat3 normmot = TFloat3(v.x*normal.x, v.y*normal.y, v.z*normal.z); // boundary motion in direction normal to boundary 
			FSVelFinal = TFloat3(normmot.x+normmot.x-normvel.x, normmot.y + normmot.y -normvel.y, normmot.z + normmot.z -normvel.z);
			// only velocity in normal direction for no-penetration
			// fluid sees zero velocity in the tangetial direction
		}
		else {
			FSVelFinal = TFloat3(tangvel.x - normvel.x, tangvel.y - normvel.y, tangvel.z - normvel.z);
			// tangential velocity equal to fluid velocity for free slip
			// normal velocity reversed for no-penetration
		}
		
		// Save the velocity and density
		velrhop[p1]=TFloat4(FSVelFinal.x, FSVelFinal.y, FSVelFinal.z,rhopfinal); 
        sigma[p1] = sigmafinal;
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
  ,const tfloat3 *boundnormal,const tfloat3 *motionvel,tfloat4 *velrhop,tsymatrix3f* sigma)
{
  const float determlimit=1e-3f;
  //-Interaction GhostBoundaryNodes-Fluid.
  const unsigned n=(UseNormalsFt? Np: NpbOk);
  if(Simulate2D){ const bool sim2d=true;
    if(slipmode==SLIP_Vel0    )InteractionMdbcCorrectionT2 <tker,sim2d,SLIP_Vel0    > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma);
    if(slipmode==SLIP_NoSlip  )InteractionMdbcCorrectionT2 <tker,sim2d,SLIP_NoSlip  > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma);
    if(slipmode==SLIP_FreeSlip)InteractionMdbcCorrectionT2 <tker,sim2d,SLIP_FreeSlip> (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma);
  }else{          const bool sim2d=false;
    if(slipmode==SLIP_Vel0    )InteractionMdbcCorrectionT2 <tker,sim2d,SLIP_Vel0    > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma);
    if(slipmode==SLIP_NoSlip  )InteractionMdbcCorrectionT2 <tker,sim2d,SLIP_NoSlip  > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma);
    if(slipmode==SLIP_FreeSlip)InteractionMdbcCorrectionT2 <tker,sim2d,SLIP_FreeSlip> (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma);
  }
}

//==============================================================================
/// Calculates extrapolated data on boundary particles from fluid domain for mDBC.
/// Calcula datos extrapolados en el contorno para mDBC.
//==============================================================================
void JSphCpu::Interaction_MdbcCorrection(TpSlipMode slipmode,const StDivDataCpu &divdata
  ,const tdouble3 *pos,const typecode *code,const unsigned *idp
  ,const tfloat3 *boundnormal,const tfloat3 *motionvel,tfloat4 *velrhop,tsymatrix3f* sigma)
{
  switch(TKernel){
    case KERNEL_Cubic:       Interaction_MdbcCorrectionT <KERNEL_Cubic     > (slipmode,divdata,pos,code,idp,boundnormal,motionvel,velrhop,sigma);  break;
    case KERNEL_Wendland:    Interaction_MdbcCorrectionT <KERNEL_Wendland  > (slipmode,divdata,pos,code,idp,boundnormal,motionvel,velrhop,sigma);  break;
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
  ,const tfloat3 *boundnormal,const tfloat3 *motionvel,tfloat4 *velrhop,tsymatrix3f* sigma)
{
  if(tslip==SLIP_FreeSlip)Run_Exceptioon("SlipMode=\'Free slip\' is not yet implemented...");
  const int nn=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided)
  #endif
  for(int p1=0;p1<nn;p1++){
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
          const tsymatrix3f sigmap2=sigma[p2];//mdbr
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
          if(tslip!=SLIP_Vel0){
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
        if(a_corr2.a11>0&&tslip!=SLIP_Vel0){
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
        if(a_corr3.a11>0&&tslip!=SLIP_Vel0){
          velrhopfinal.x=float(velp1.x/a_corr3.a11);
          velrhopfinal.y=float(velp1.y/a_corr3.a11);
          velrhopfinal.z=float(velp1.z/a_corr3.a11);
        }
      }
      //-Store the results.
      rhopfinal=RhopZero;//rhopfinal=(rhopfinal!=FLT_MAX? rhopfinal: RhopZero);
      if(tslip==SLIP_Vel0){//-DBC vel=0
        velrhop[p1].w=rhopfinal;
        sigma[p1] = sigmafinal;
      }
      if(tslip==SLIP_NoSlip){//-No-Slip
        const tfloat3 v=motionvel[p1];
        velrhop[p1]=TFloat4(v.x+v.x-velrhopfinal.x,v.y+v.y-velrhopfinal.y,v.z+v.z-velrhopfinal.z,rhopfinal);
        sigma[p1] = sigmafinal;
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
  ,const tfloat3 *boundnormal,const tfloat3 *motionvel,tfloat4 *velrhop,tsymatrix3f* sigma)
{
  const float determlimit=1e-3f;
  //-Interaction GhostBoundaryNodes-Fluid.
  //const unsigned n=(UseNormalsFt? Np: NpbOk);
  const unsigned n=(WithFloating? Np: NpbOk);
  if(Simulate2D){ const bool sim2d=true;
    if(slipmode==SLIP_Vel0    )InteractionCdbcCorrectionT2 <tker,sim2d,SLIP_Vel0    > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma);
    if(slipmode==SLIP_NoSlip  )InteractionCdbcCorrectionT2 <tker,sim2d,SLIP_NoSlip  > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma);
    if(slipmode==SLIP_FreeSlip)InteractionCdbcCorrectionT2 <tker,sim2d,SLIP_FreeSlip> (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma);
  }else{          const bool sim2d=false;
    if(slipmode==SLIP_Vel0    )InteractionCdbcCorrectionT2 <tker,sim2d,SLIP_Vel0    > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma);
    if(slipmode==SLIP_NoSlip  )InteractionCdbcCorrectionT2 <tker,sim2d,SLIP_NoSlip  > (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma);
    if(slipmode==SLIP_FreeSlip)InteractionCdbcCorrectionT2 <tker,sim2d,SLIP_FreeSlip> (n,divdata,determlimit,MdbcThreshold,pos,code,idp,boundnormal,motionvel,velrhop,sigma);
  }
}

 //==============================================================================
/// Calculates extrapolated data on boundary particles from fluid domain for mDBC.
/// Calcula datos extrapolados en el contorno para mDBC.
//==============================================================================
void JSphCpu::Interaction_CdbcCorrection(TpSlipMode slipmode,const StDivDataCpu &divdata
  ,const tdouble3 *pos,const typecode *code,const unsigned *idp
  ,const tfloat3 *boundnormal,const tfloat3 *motionvel,tfloat4 *velrhop,tsymatrix3f* sigma)
{
  switch(TKernel){
    case KERNEL_Cubic:       Interaction_CdbcCorrectionT <KERNEL_Cubic     > (slipmode,divdata,pos,code,idp,boundnormal,motionvel,velrhop,sigma);  break;
    case KERNEL_Wendland:    Interaction_CdbcCorrectionT <KERNEL_Wendland  > (slipmode,divdata,pos,code,idp,boundnormal,motionvel,velrhop,sigma);  break;
    default: Run_Exceptioon("Kernel unknown.");
  }
}

//==============================================================================
/// Update pos, dcell and code to move with indicated displacement.
/// The value of outrhop indicates is it outside of the density limits.
/// Check the limits in funcion of MapRealPosMin & MapRealSize that this is valid
/// for single-cpu because DomRealPos & MapRealPos are equal. For multi-cpu it will be 
/// necessary to mark the particles that leave the domain without leaving the map.
///
/// Actualiza pos, dcell y code a partir del desplazamiento indicado.
/// El valor de outrhop indica si esta fuera de los limites de densidad.
/// Comprueba los limites en funcion de MapRealPosMin y MapRealSize esto es valido
/// para single-cpu pq DomRealPos y MapRealPos son iguales. Para multi-cpu seria 
/// necesario marcar las particulas q salgan del dominio sin salir del mapa.
//==============================================================================
void JSphCpu::UpdatePos(tdouble3 rpos,double movx,double movy,double movz
  ,bool outrhop,unsigned p,tdouble3 *pos,unsigned *cell,typecode *code)const
{
  //-Check validity of displacement. | Comprueba validez del desplazamiento.
  bool outmove=(fabs(float(movx))>MovLimit || fabs(float(movy))>MovLimit || fabs(float(movz))>MovLimit);
  //-Applies dsiplacement. | Aplica desplazamiento.
  rpos.x+=movx; rpos.y+=movy; rpos.z+=movz;
  if(Symmetry && rpos.y<0)rpos.y=-rpos.y; //<vs_syymmetry>
  //-Check limits of real domain. | Comprueba limites del dominio reales.
  double dx=rpos.x-MapRealPosMin.x;
  double dy=rpos.y-MapRealPosMin.y;
  double dz=rpos.z-MapRealPosMin.z;
  bool out=(dx!=dx || dy!=dy || dz!=dz || dx<0 || dy<0 || dz<0 || dx>=MapRealSize.x || dy>=MapRealSize.y || dz>=MapRealSize.z);
  //-Adjust position according to periodic conditions and compare domain limits. | Ajusta posicion segun condiciones periodicas y vuelve a comprobar los limites del dominio.
  if(PeriActive && out){
    if(PeriX){
      if(dx<0)             { dx-=PeriXinc.x; dy-=PeriXinc.y; dz-=PeriXinc.z; }
      if(dx>=MapRealSize.x){ dx+=PeriXinc.x; dy+=PeriXinc.y; dz+=PeriXinc.z; }
    }
    if(PeriY){
      if(dy<0)             { dx-=PeriYinc.x; dy-=PeriYinc.y; dz-=PeriYinc.z; }
      if(dy>=MapRealSize.y){ dx+=PeriYinc.x; dy+=PeriYinc.y; dz+=PeriYinc.z; }
    }
    if(PeriZ){
      if(dz<0)             { dx-=PeriZinc.x; dy-=PeriZinc.y; dz-=PeriZinc.z; }
      if(dz>=MapRealSize.z){ dx+=PeriZinc.x; dy+=PeriZinc.y; dz+=PeriZinc.z; }
    }
    bool outx=!PeriX && (dx<0 || dx>=MapRealSize.x);
    bool outy=!PeriY && (dy<0 || dy>=MapRealSize.y);
    bool outz=!PeriZ && (dz<0 || dz>=MapRealSize.z);
    out=(outx||outy||outz);
    rpos=TDouble3(dx,dy,dz)+MapRealPosMin;
  }
  //-Keep current position. | Guarda posicion actualizada.
  pos[p]=rpos;
  //-Keep cell and check. | Guarda celda y check.
  if(outrhop || outmove || out){//-Particle out.
    typecode rcode=code[p];
    if(out)rcode=CODE_SetOutPos(rcode);
    else if(outrhop)rcode=CODE_SetOutRhop(rcode);
    else rcode=CODE_SetOutMove(rcode);
    code[p]=rcode;
    cell[p]=0xFFFFFFFF;
  }
  else{//-Particle in.
    if(PeriActive){
      dx=rpos.x-DomPosMin.x;
      dy=rpos.y-DomPosMin.y;
      dz=rpos.z-DomPosMin.z;
    }
    unsigned cx=unsigned(dx/Scell),cy=unsigned(dy/Scell),cz=unsigned(dz/Scell);
    cell[p]=DCEL_Cell(DomCellCode,cx,cy,cz);
  }
}
//========Implement Soil Constitutive Model=========


//==========Include DP without softening for testing===
//==============================================================================
void GetStressInvariant(float sigmaxx, float sigmayy, float sigmazz, float sigmaxy, float sigmayz, float sigmaxz,float &I1,float &J2)
{
  I1= sigmaxx + sigmayy + sigmazz;
  J2=((sigmaxx-sigmazz)*(sigmaxx-sigmazz)+(sigmayy-sigmazz)*(sigmayy-sigmazz)+(sigmayy-sigmaxx)*(sigmayy-sigmaxx))/6.f+sigmaxy*sigmaxy+sigmayz*sigmayz+sigmaxz*sigmaxz;
}

void GetDPYieldFunction(float &f, float I1, float J2, const float DP_phi, const float DP_kc)
{
   f=sqrt(J2)+DP_phi*I1-DP_kc;
}
void UpdateDPvars(float &DP_phi, float &DP_kc, float &DP_psi,const float phi_p, const float phi_r, const float n_p
							,const float coh_p, const float coh_r, const float n_c, const float psi, const float kplastic) {
    float phi = phi_r + (phi_p - phi_r)*exp(-n_p*kplastic);
	float coh = coh_r + (coh_p - coh_r)*exp(-n_c*kplastic);
	///Plain strain
	//DP_phi = tan(phi)/sqrt(9.f+12.f*tan(phi)*tan(phi)); // Make it as a function
    //DP_kc = 3.f*coh/sqrt(9.f+12.f*tan(phi)*tan(phi)); 
    //DP_psi = tan(psi)/sqrt(9.f+12.f*tan(psi)*tan(psi)); //
	///3D
	//DP_phi = 2.f*sin(phi)/((3.f-sin(phi))* 1.732f);
	//DP_kc = 6.f*coh*cos(phi)/((3.f-sin(phi))* 1.732f);
	//DP_psi = 2.f*sin(psi)/((3.f-sin(psi))* 1.732f);
	///Medium set
	DP_phi = 2.f*sin(phi)/((3.f+sin(phi))* 1.732f);
	DP_kc = 6.f*coh*cos(phi)/((3.f+sin(phi))* 1.732f);
	DP_psi = 2.f*sin(psi)/((3.f+sin(psi))* 1.732f);
}
void Updatedfdk(float &dfdk,const float phi_p,const float phi_r, const float n_p
						  ,const float coh_p,const float coh_r,const float n_c,const float psi,const float kplastic
						  ,const float I1)
{
	float phi = phi_r + (phi_p - phi_r)*exp(-n_p*kplastic);
	float coh = coh_r + (coh_p - coh_r)*exp(-n_c*kplastic);
	float dalphadk = I1*(sqrt(3.f)*(tan(phi)*tan(phi)+1.f))/pow((4.f*tan(phi)*tan(phi)+3.f),1.5f)*-n_p*(phi-phi_r);
	float dkcdk = (3.f/pow(12.f*tan(phi)*tan(phi)+9.f,0.5f))*-n_c*(coh-coh_r)+-(36.f*coh*tan(phi)*(tan(phi)*tan(phi)+1.f))/pow(12.f*tan(phi)*tan(phi)+9.f, 3.f/2.f)*-n_p*(phi-phi_r);
	dfdk = dalphadk-dkcdk;
}
void ConsRelationEP_fast(tsymatrix3f sigma
		, const float E_ModulusK, const float E_ModulusG, const float dp_phi, const float dp_kc, const float dp_psi
		, float kplastic, tsymatrix3f &nsigma, float& nkplastic)
{// simple return mapping Bui et al. 2021; single floating precisions
    float tsigma_xx, tsigma_yy, tsigma_zz, tsigma_xy, tsigma_yz, tsigma_xz, tk;// trial value
	float ModulusK = E_ModulusK;
	float ModulusG = E_ModulusG;
    float DP_phi= dp_phi;
    float DP_kc = dp_kc;
    float DP_psi= dp_psi;
	//Build Elastic stiffness matrix
	float K4G3 = float(ModulusK + 4.f*ModulusG/3.f);
	float K2G3 = float(ModulusK- 2.f*ModulusG/3.f);
	//Build Inversed elastic stiffness matrix
	float invK4G3 = (K2G3 + K4G3) / (-2.f * K2G3*K2G3 + K2G3*K4G3 + K4G3*K4G3);
	float invK2G3 = -K2G3 / (-2.f * K2G3*K2G3 + K2G3*K4G3 + K4G3*K4G3);
	float invm_a11 = invK4G3; float invm_a12 = invK2G3; float invm_a13 = invK2G3;
	float invm_a21 = invK2G3; float invm_a22 = invK4G3; float invm_a23 = invK2G3;
	float invm_a31 = invK2G3; float invm_a32 = invK2G3; float invm_a33 = invK4G3;
	//trail stress from elastic update
    tsigma_xx = sigma.xx;
    tsigma_yy = sigma.yy;
    tsigma_zz = sigma.zz;
    tsigma_xy = sigma.xy;
    tsigma_yz = sigma.yz;
    tsigma_xz = sigma.xz;
	tk = kplastic;
	float f=0, I1=0, J2=0;
	float err = 1e-5f;
	GetStressInvariant(tsigma_xx,tsigma_yy,tsigma_zz,tsigma_xy,tsigma_yz,tsigma_xz,I1,J2);
	GetDPYieldFunction(f,I1,J2,DP_phi,DP_kc);
	if (f<err) {//elastic 
		//Update plastic strain internal variable & stress
		nkplastic = tk;
		nsigma.xx = tsigma_xx;
		nsigma.yy = tsigma_yy;
		nsigma.zz = tsigma_zz;
		nsigma.xy = tsigma_xy;
		nsigma.yz = tsigma_yz;
		nsigma.xz = tsigma_xz;
	}	
	else {//plastic corrector
		float dsigmap_xx = 0, dsigmap_yy = 0, dsigmap_zz = 0, dsigmap_xy = 0, dsigmap_yz = 0, dsigmap_xz = 0
			 , depsp_xx = 0, depsp_yy = 0, depsp_zz = 0, depsp_xy = 0, depsp_yz = 0, depsp_xz = 0, dk = 0;
			//MODIFY PLASTIC MULTIPLFY
			float dlambda = f /(9.f*ModulusK*DP_phi*DP_psi+ModulusG);
			float GJ2=ModulusG/sqrt(J2);
			//evaluate De : plastic potential
			float Deppxx = 3.f*ModulusK*DP_psi+GJ2*(tsigma_xx-I1/3.f);
			float Deppyy = 3.f*ModulusK*DP_psi+GJ2*(tsigma_yy-I1/3.f);
			float Deppzz = 3.f*ModulusK*DP_psi+GJ2*(tsigma_zz-I1/3.f);
			float Deppxy = GJ2*tsigma_xy;
			float Deppyz = GJ2*tsigma_yz;
			float Deppxz = GJ2*tsigma_xz;
			//Compute plastic stress increment
			dsigmap_xx = dlambda*Deppxx;
			dsigmap_yy = dlambda*Deppyy;
			dsigmap_zz = dlambda*Deppzz;
			dsigmap_xy = dlambda*Deppxy;
			dsigmap_yz = dlambda*Deppyz;
			dsigmap_xz = dlambda*Deppxz;
			//Update new stress matrix
			tsigma_xx = tsigma_xx - dsigmap_xx;
			tsigma_yy = tsigma_yy - dsigmap_yy;
			tsigma_zz = tsigma_zz - dsigmap_zz;
			tsigma_xy = tsigma_xy - dsigmap_xy;
			tsigma_yz = tsigma_yz - dsigmap_yz;
			tsigma_xz = tsigma_xz - dsigmap_xz;
			//Compute plastic strain increment
			depsp_xx = invm_a11*dsigmap_xx + invm_a12*dsigmap_yy + invm_a13*dsigmap_zz;
			depsp_yy = invm_a21*dsigmap_xx + invm_a22*dsigmap_yy + invm_a23*dsigmap_zz;
			depsp_zz = invm_a31*dsigmap_xx + invm_a32*dsigmap_yy + invm_a33*dsigmap_zz;
			depsp_xy = 0.5f/ModulusG*dsigmap_xy;
			depsp_yz = 0.5f/ModulusG*dsigmap_yz;
			depsp_xz = 0.5f/ModulusG*dsigmap_xz; 
			//bulk plastic strain increment
			float depsp_b = (depsp_xx + depsp_yy + depsp_zz)/3.f;
			//deviatoric trail plastic strain
			float dtepsp_xx = depsp_xx - depsp_b;
			float dtepsp_yy = depsp_yy - depsp_b;
			float dtepsp_zz = depsp_zz - depsp_b;
			float dtepsp_xy = depsp_xy;
			float dtepsp_yz = depsp_yz;
			float dtepsp_xz = depsp_xz;
			//Update internal variable
			dk = sqrt((2.f/3.f)*(dtepsp_xx*dtepsp_xx+dtepsp_yy*dtepsp_yy+dtepsp_zz*dtepsp_zz+2.f*dtepsp_xy*dtepsp_xy+2.f*dtepsp_yz*dtepsp_yz+2.f*dtepsp_xz*dtepsp_xz));
			tk = tk + dk;
			//Update stress invariant
			GetStressInvariant(tsigma_xx,tsigma_yy,tsigma_zz,tsigma_xy,tsigma_yz,tsigma_xz,I1,J2);

			float kalpha = DP_kc / DP_phi;
			
			if (I1 > kalpha)// I1 > kalpha check tensile cracking & perform stress scaling
			{
				tsigma_xx = tsigma_xx - (I1 - kalpha) / 3.f;
				tsigma_yy = tsigma_yy - (I1 - kalpha) / 3.f;
				tsigma_zz = tsigma_zz - (I1 - kalpha) / 3.f;
				GetStressInvariant(tsigma_xx, tsigma_yy, tsigma_zz, tsigma_xy, tsigma_yz, tsigma_xz, I1, J2);
			}
			float fscale = (-DP_phi * I1 + DP_kc) / sqrt(J2);
			if (J2 != 0 && fscale < 1.f)// stress scaling
			{
				tsigma_xx = fscale * (tsigma_xx - I1 / 3.f) + I1 / 3.f;
				tsigma_yy = fscale * (tsigma_yy - I1 / 3.f) + I1 / 3.f;
				tsigma_zz = fscale * (tsigma_zz - I1 / 3.f) + I1 / 3.f;
				tsigma_xy = fscale * tsigma_xy;
				tsigma_yz = fscale * tsigma_yz;
				tsigma_xz = fscale * tsigma_xz;
			}
			
		//Update plastic strain internal variable & stress
		nkplastic = tk;
        nsigma.xx = tsigma_xx;
		nsigma.yy = tsigma_yy;
		nsigma.zz = tsigma_zz;
		nsigma.xy = tsigma_xy;
		nsigma.yz = tsigma_yz;
		nsigma.xz = tsigma_xz;
	}
}

void ConsRelationEPsft_fast(tsymatrix3f sigma
		, const float E_ModulusK, const float E_ModulusG, const float MC_phi, const float MC_phir, const float n_phi
		, const float MC_c, const float MC_cr, const float n_coh, const float MC_psi
		, float kplastic
        , tsymatrix3f &nsigma, float& nkplastic)
{// simple return mapping Bui et al. 2021; single floating precisions
    float tsigma_xx, tsigma_yy, tsigma_zz, tsigma_xy, tsigma_yz, tsigma_xz, tk;// trial value
	float ModulusK = E_ModulusK;
	float ModulusG = E_ModulusG;
	const float phi_p = MC_phi;
	const float phi_r = MC_phir;
	const float n_p   = n_phi;
	const float coh_p = MC_c;
	const float coh_r = MC_cr;
	const float n_c   = n_coh;
	const float psi = MC_psi;
	//Build Elastic stiffness matrix
	float K4G3 = float(ModulusK + 4.f*ModulusG/3.f);
	float K2G3 = float(ModulusK- 2.f*ModulusG/3.f);
	//Build Inversed elastic stiffness matrix
	float invK4G3 = (K2G3 + K4G3) / (-2.f * K2G3*K2G3 + K2G3*K4G3 + K4G3*K4G3);
	float invK2G3 = -K2G3 / (-2.f * K2G3*K2G3 + K2G3*K4G3 + K4G3*K4G3);
	float invm_a11 = invK4G3; float invm_a12 = invK2G3; float invm_a13 = invK2G3;
	float invm_a21 = invK2G3; float invm_a22 = invK4G3; float invm_a23 = invK2G3;
	float invm_a31 = invK2G3; float invm_a32 = invK2G3; float invm_a33 = invK4G3;
	//trail stress from elastic update
    tsigma_xx = sigma.xx;
    tsigma_yy = sigma.yy;
    tsigma_zz = sigma.zz;
    tsigma_xy = sigma.xy;
    tsigma_yz = sigma.yz;
    tsigma_xz = sigma.xz;
	tk = kplastic;
	//evaluate yeild condition
	float DP_phi=0, DP_kc=0, DP_psi=0;
	UpdateDPvars(DP_phi,DP_kc,DP_psi,phi_p,phi_r,n_p,coh_p,coh_r,n_c,psi,tk);
	float f=0, I1=0, J2=0;
	float err = 1e-5f;
	GetStressInvariant(tsigma_xx,tsigma_yy,tsigma_zz,tsigma_xy,tsigma_yz,tsigma_xz,I1,J2);
	GetDPYieldFunction(f,I1,J2,DP_phi,DP_kc);
	if (f<err) {//elastic 
		//Update plastic strain internal variable & stress
		nkplastic = tk;
        nsigma.xx = tsigma_xx;
        nsigma.yy = tsigma_yy;
        nsigma.zz = tsigma_zz;
        nsigma.xy = tsigma_xy;
        nsigma.yz = tsigma_yz;
        nsigma.xz = tsigma_xz;
	}	
	else {//plastic corrector
		float dsigmap_xx = 0, dsigmap_yy = 0, dsigmap_zz = 0, dsigmap_xy = 0, dsigmap_yz = 0, dsigmap_xz = 0
			 , depsp_xx = 0, depsp_yy = 0, depsp_zz = 0, depsp_xy = 0, depsp_yz = 0, depsp_xz = 0, dk = 0;;
			//kplastic related term
			float dfdk = 0;
			Updatedfdk(dfdk,phi_p,phi_r,n_p,coh_p,coh_r,n_c,psi,tk,I1);
			float extra = dfdk*sqrt((2.f/3.f)*(3.f*DP_psi*DP_psi+0.5f));			
			//MODIFY PLASTIC MULTIPLFY
			float dlambda = f /(9.f*ModulusK*DP_phi*DP_psi+ModulusG+extra);
			//evaluate De : plastic potential
			float GJ2 = ModulusG / sqrt(J2);
			float Deppxx = 3.f*ModulusK*DP_psi+GJ2*(tsigma_xx-I1/3.f);
			float Deppyy = 3.f*ModulusK*DP_psi+GJ2*(tsigma_yy-I1/3.f);
			float Deppzz = 3.f*ModulusK*DP_psi+GJ2*(tsigma_zz-I1/3.f);
			float Deppxy = GJ2*tsigma_xy;
			float Deppyz = GJ2*tsigma_yz;
			float Deppxz = GJ2*tsigma_xz;
			//Compute plastic stress increment
			dsigmap_xx = dlambda*Deppxx;
			dsigmap_yy = dlambda*Deppyy;
			dsigmap_zz = dlambda*Deppzz;
			dsigmap_xy = dlambda*Deppxy;
			dsigmap_yz = dlambda*Deppyz;
			dsigmap_xz = dlambda*Deppxz;
			//Update new stress matrix
			tsigma_xx = tsigma_xx - dsigmap_xx;
			tsigma_yy = tsigma_yy - dsigmap_yy;
			tsigma_zz = tsigma_zz - dsigmap_zz;
			tsigma_xy = tsigma_xy - dsigmap_xy;
			tsigma_yz = tsigma_yz - dsigmap_yz;
			tsigma_xz = tsigma_xz - dsigmap_xz;
			//Compute plastic strain increment
			depsp_xx = invm_a11*dsigmap_xx + invm_a12*dsigmap_yy + invm_a13*dsigmap_zz;
			depsp_yy = invm_a21*dsigmap_xx + invm_a22*dsigmap_yy + invm_a23*dsigmap_zz;
			depsp_zz = invm_a31*dsigmap_xx + invm_a32*dsigmap_yy + invm_a33*dsigmap_zz;
			depsp_xy = 0.5f/ModulusG*dsigmap_xy;
			depsp_yz = 0.5f/ModulusG*dsigmap_yz;
			depsp_xz = 0.5f/ModulusG*dsigmap_xz; 
			//bulk plastic strain increment
			float depsp_b = (depsp_xx + depsp_yy + depsp_zz)/3.f;
			//deviatoric trail plastic strain
			float dtepsp_xx = depsp_xx - depsp_b;
			float dtepsp_yy = depsp_yy - depsp_b;
			float dtepsp_zz = depsp_zz - depsp_b;
			float dtepsp_xy = depsp_xy;
			float dtepsp_yz = depsp_yz;
			float dtepsp_xz = depsp_xz;
			//Update internal variable
			dk = sqrt((2.f/3.f)*(dtepsp_xx*dtepsp_xx+dtepsp_yy*dtepsp_yy+dtepsp_zz*dtepsp_zz+2.f*dtepsp_xy*dtepsp_xy+2.f*dtepsp_yz*dtepsp_yz+2.f*dtepsp_xz*dtepsp_xz));
			tk = tk + dk;
			//Update stress invariant
			GetStressInvariant(tsigma_xx,tsigma_yy,tsigma_zz,tsigma_xy,tsigma_yz,tsigma_xz,I1,J2);
			float kalpha = DP_kc / DP_phi;
			
			if (I1 > kalpha)// I1 > kalpha check tensile cracking & perform stress scaling
			{
				tsigma_xx = tsigma_xx - (I1 - kalpha) / 3.f;
				tsigma_yy = tsigma_yy - (I1 - kalpha) / 3.f;
				tsigma_zz = tsigma_zz - (I1 - kalpha) / 3.f;
				GetStressInvariant(tsigma_xx, tsigma_yy, tsigma_zz, tsigma_xy, tsigma_yz, tsigma_xz, I1, J2);
			}
			float fscale = (-DP_phi * I1 + DP_kc) / sqrt(J2);
			if (J2 != 0 && fscale < 1.f)// stress scaling
			{
				tsigma_xx = fscale * (tsigma_xx - I1 / 3.f) + I1 / 3.f;
				tsigma_yy = fscale * (tsigma_yy - I1 / 3.f) + I1 / 3.f;
				tsigma_zz = fscale * (tsigma_zz - I1 / 3.f) + I1 / 3.f;
				tsigma_xy = fscale * tsigma_xy;
				tsigma_yz = fscale * tsigma_yz;
				tsigma_xz = fscale * tsigma_xz;
			}
			
		//Update plastic strain internal variable & stress
		nkplastic = tk;
        nsigma.xx = tsigma_xx;
        nsigma.yy = tsigma_yy;
        nsigma.zz = tsigma_zz;
        nsigma.xy = tsigma_xy;
        nsigma.yz = tsigma_yz;
        nsigma.xz = tsigma_xz;
	}
}

//==============================================================================
/// Calculate new values of position, velocity & density for fluid (using Verlet).
/// Calcula nuevos valores de posicion, velocidad y densidad para el fluido (usando Verlet).
//==============================================================================
void JSphCpu::ComputeVerletVarsFluid(bool shift,const tfloat3 *indirvel
  ,const tfloat4 *velrhop1,const tfloat4 *velrhop2,const tsymatrix3f *sigma2,const float *kplastic,const tsymatrix3f *rsigma
  ,double dt,double dt2,tdouble3 *pos,unsigned *dcell,typecode *code,tfloat4 *velrhopnew, tsymatrix3f *sigmanew, float *kplasticnew)const
{
  const double dt205=0.5*dt*dt;
  const tdouble3 gravity=ToTDouble3(Gravity);
  const int pini=int(Npb),pfin=int(Np),npf=int(Np-Npb);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(npf>OMP_LIMIT_COMPUTESTEP)
  #endif
  for(int p=pini;p<pfin;p++){
    //-Calculate density. | Calcula densidad.
    const float rhopnew=float(double(velrhop2[p].w)+dt2*Arc[p]);
    tsymatrix3f signew=sigma2[p];//mdbr
    float kplasnew=kplastic[p];
    if(!WithFloating || CODE_IsFluid(code[p])){//-Fluid Particles.
      const tdouble3 acegr=ToTDouble3(Acec[p])+gravity; //-Adds gravity.
      //-Calculate displacement. | Calcula desplazamiento.
      double dx=double(velrhop1[p].x)*dt + acegr.x*dt205;
      double dy=double(velrhop1[p].y)*dt + acegr.y*dt205;
      double dz=double(velrhop1[p].z)*dt + acegr.z*dt205;
      if(shift){
        dx+=double(ShiftPosfsc[p].x);
        dy+=double(ShiftPosfsc[p].y);
        dz+=double(ShiftPosfsc[p].z);
      }
      bool outrhop=(rhopnew<RhopOutMin || rhopnew>RhopOutMax);
      //-Calculate velocity & density. | Calcula velocidad y densidad.
      tfloat4 rvelrhopnew=TFloat4(
        float(double(velrhop2[p].x) + acegr.x*dt2),
        float(double(velrhop2[p].y) + acegr.y*dt2),
        float(double(velrhop2[p].z) + acegr.z*dt2),
        rhopnew);
      //-Calculate elastic stress
        tsymatrix3f sigma_e={0,0,0,0,0,0};
        float kplasticold = kplastic[p];
        sigma_e.xx = float(double(sigma2[p].xx) + rsigma[p].xx * dt2);
        sigma_e.yy = float(double(sigma2[p].yy) + rsigma[p].yy * dt2);
        sigma_e.zz = float(double(sigma2[p].zz) + rsigma[p].zz * dt2);
        sigma_e.xy = float(double(sigma2[p].xy) + rsigma[p].xy * dt2);
        sigma_e.yz = float(double(sigma2[p].yz) + rsigma[p].yz * dt2);
        sigma_e.xz = float(double(sigma2[p].xz) + rsigma[p].xz * dt2);
      //-Update DP constants
      float phi=SoilCte.phi;
      float coh=SoilCte.coh;
      float psi=SoilCte.dlt;
      //default 3D 
      float DP_phi = 2.f*sin(phi)/((3.f-sin(phi))* 1.732f);
      float DP_kc = 6.f*coh*cos(phi)/((3.f-sin(phi))* 1.732f);
      float DP_psi = 2.f*sin(psi)/((3.f-sin(psi))* 1.732f);
      if(DPCtes==DP_MC){
         DP_phi = 2.f*sin(phi)/((3.f+sin(phi))* 1.732f);
	     DP_kc = 6.f*coh*cos(phi)/((3.f+sin(phi))* 1.732f);
	     DP_psi = 2.f*sin(psi)/((3.f+sin(psi))* 1.732f);
      }
      if(DPCtes==DP_PS){
         DP_phi = tan(phi)/sqrt(9.f+12.f*tan(phi)*tan(phi));
         DP_kc = 3.f*coh/sqrt(9.f+12.f*tan(phi)*tan(phi)); 
         DP_psi = tan(psi)/sqrt(9.f+12.f*tan(psi)*tan(psi));
      }	
      //-Plastic Corretor
      ConsRelationEP_fast(sigma_e,SoilCte.ModulusK,SoilCte.ModulusG,DP_phi,DP_kc,DP_psi,kplasticold,signew,kplasnew);
      // 
      //-Restore data of inout particles.
      if(InOut && CODE_IsFluidInout(Codec[p])){
        outrhop=false;
        rvelrhopnew=velrhop2[p];
        const tfloat3 vd=indirvel[CODE_GetIzoneFluidInout(Codec[p])];
        if(vd.x!=FLT_MAX){
          const float v=velrhop1[p].x*vd.x + velrhop1[p].y*vd.y + velrhop1[p].z*vd.z;
          dx=double(v*vd.x) * dt;
          dy=double(v*vd.y) * dt;
          dz=double(v*vd.z) * dt;
        }
        else{
          dx=double(velrhop1[p].x) * dt;
          dy=double(velrhop1[p].y) * dt;
          dz=double(velrhop1[p].z) * dt;
        }
      }
      //-Update particle data.
      UpdatePos(pos[p],dx,dy,dz,outrhop,p,pos,dcell,code);
      velrhopnew[p]=rvelrhopnew;
    }
    else{//-Floating Particles.
      velrhopnew[p]=velrhop1[p];
      velrhopnew[p].w=(rhopnew<RhopZero? RhopZero: rhopnew); //-Avoid fluid particles being absorved by floating ones. | Evita q las floating absorvan a las fluidas.
    }
    sigmanew[p]=signew;//mdbr
    kplasticnew[p]=kplasnew;//mdbr
  }
}

//==============================================================================
/// Calculate new values of density and set velocity=zero for cases of  
/// (fixed+moving, no floating).
///
/// Calcula nuevos valores de densidad y pone velocidad a cero para el contorno 
/// (fixed+moving, no floating).
//==============================================================================
void JSphCpu::ComputeVelrhopBound(const tfloat4* velrhopold,const tsymatrix3f *sigma,double armul,tfloat4* velrhopnew,tsymatrix3f *sigmanew)const{
  const int npb=int(Npb);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(npb>OMP_LIMIT_COMPUTESTEP)
  #endif
  for(int p=0;p<npb;p++){
    const float rhopnew=float(double(velrhopold[p].w)+armul*Arc[p]);
    velrhopnew[p]=TFloat4(0,0,0,(rhopnew<RhopZero? RhopZero: rhopnew));//-Avoid fluid particles being absorved by boundary ones. | Evita q las boundary absorvan a las fluidas.
    sigmanew[p]=sigma[p];
  }
}

//==============================================================================
/// Update of particles according to forces and dt using Verlet.
/// Actualizacion de particulas segun fuerzas y dt usando Verlet.
//==============================================================================
void JSphCpu::ComputeVerlet(double dt){
  Timersc->TmStart(TMC_SuComputeStep);
  const bool shift=(Shifting!=NULL);
  const tfloat3 *indirvel=(InOut? InOut->GetDirVel(): NULL);
  VerletStep++;
  if(VerletStep<VerletSteps){
    const double twodt=dt+dt;
    ComputeVerletVarsFluid(shift,indirvel,Velrhopc,VelrhopM1c,SigmaM1c,Kplasticc,Rsigmac,dt,twodt,Posc,Dcellc,Codec,VelrhopM1c,SigmaM1c,Kplasticc);
    ComputeVelrhopBound(VelrhopM1c,SigmaM1c,twodt,VelrhopM1c,SigmaM1c);
  }
  else{
    ComputeVerletVarsFluid(shift,indirvel,Velrhopc,Velrhopc,Sigmac,Kplasticc,Rsigmac,dt,dt,Posc,Dcellc,Codec,VelrhopM1c,SigmaM1c,Kplasticc);
    ComputeVelrhopBound(Velrhopc,Sigmac,dt,VelrhopM1c,SigmaM1c);
    VerletStep=0;
  }
  //-New values are calculated en VelrhopM1c. | Los nuevos valores se calculan en VelrhopM1c.
  swap(Velrhopc,VelrhopM1c);     //-Swap Velrhopc & VelrhopM1c. | Intercambia Velrhopc y VelrhopM1c.
  swap(Sigmac,SigmaM1c);
  Timersc->TmStop(TMC_SuComputeStep);
}


//==============================================================================
/// Update of particles according to forces and dt using Symplectic-Predictor.
/// Actualizacion de particulas segun fuerzas y dt usando Symplectic-Predictor.
//==============================================================================
void JSphCpu::ComputeSymplecticPre(double dt){
  Timersc->TmStart(TMC_SuComputeStep);
  const bool shift=false; //(ShiftingMode!=SHIFT_None); //-We strongly recommend running the shifting correction only for the corrector. If you want to re-enable shifting in the predictor, change the value here to "true".
  const double dt05=dt*.5;
  const int np=int(Np);
  const int npb=int(Npb);
  const int npf=np-npb;

  //-Assign memory to variables Pre. | Asigna memoria a variables Pre.
  PosPrec=ArraysCpu->ReserveDouble3();
  VelrhopPrec=ArraysCpu->ReserveFloat4();
  //====mdbr
  SigmaPrec=ArraysCpu->ReserveSymatrix3f();
  //-Change data to variables Pre to calculate new data. | Cambia datos a variables Pre para calcular nuevos datos.
  swap(PosPrec,Posc);         //Put value of Pos[] in PosPre[].         | Es decir... PosPre[] <= Pos[].
  swap(VelrhopPrec,Velrhopc); //Put value of Velrhop[] in VelrhopPre[]. | Es decir... VelrhopPre[] <= Velrhop[].
  //=====mdbr
  swap(SigmaPrec, Sigmac);
  //-Calculate new density for boundary and copy velocity. | Calcula nueva densidad para el contorno y copia velocidad.
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(npb>OMP_LIMIT_COMPUTESTEP)
  #endif
  for(int p=0;p<npb;p++){
    const tfloat4 vr=VelrhopPrec[p];
    const float rhopnew=float(double(vr.w)+dt05*Arc[p]);
    Velrhopc[p]=TFloat4(vr.x,vr.y,vr.z,(rhopnew<RhopZero? RhopZero: rhopnew));//-Avoid fluid particles being absorbed by boundary ones. | Evita q las boundary absorvan a las fluidas.
    Sigmac[p]=SigmaPrec[p];//mdbr
  }

  //-Compute displacement, velocity and density for fluid.
  tdouble3 *movc=ArraysCpu->ReserveDouble3();
  const tfloat3 *indirvel=(InOut? InOut->GetDirVel(): NULL);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(npf>OMP_LIMIT_COMPUTESTEP)
  #endif
  for(int p=npb;p<np;p++){
    const typecode rcode=Codec[p];
    //-Calculate density.
    const float rhopnew=float(double(VelrhopPrec[p].w)+dt05*Arc[p]);
    tsymatrix3f signew=SigmaPrec[p];//mdbr
    float kplasnew=Kplasticc[p];//
    if(!WithFloating || CODE_IsFluid(rcode)){//-Fluid Particles.
      //-Calculate displacement. | Calcula desplazamiento.
      double dx=double(VelrhopPrec[p].x)*dt05;
      double dy=double(VelrhopPrec[p].y)*dt05;
      double dz=double(VelrhopPrec[p].z)*dt05;
      if(shift){
        dx+=double(ShiftPosfsc[p].x);
        dy+=double(ShiftPosfsc[p].y);
        dz+=double(ShiftPosfsc[p].z);
      }
      bool outrhop=(rhopnew<RhopOutMin || rhopnew>RhopOutMax);
      //-Calculate velocity & density. | Calcula velocidad y densidad.
      tfloat4 rvelrhopnew=TFloat4(
        float(double(VelrhopPrec[p].x) + (double(Acec[p].x)+Gravity.x) * dt05),
        float(double(VelrhopPrec[p].y) + (double(Acec[p].y)+Gravity.y) * dt05),
        float(double(VelrhopPrec[p].z) + (double(Acec[p].z)+Gravity.z) * dt05),
        rhopnew);
      //-Calculate elastic stress
        tsymatrix3f sigma_e={0,0,0,0,0,0};
        float kplasticold = Kplasticc[p];
        sigma_e.xx = float(double(SigmaPrec[p].xx) + Rsigmac[p].xx * dt05);
        sigma_e.yy = float(double(SigmaPrec[p].yy) + Rsigmac[p].yy * dt05);
        sigma_e.zz = float(double(SigmaPrec[p].zz) + Rsigmac[p].zz * dt05);
        sigma_e.xy = float(double(SigmaPrec[p].xy) + Rsigmac[p].xy * dt05);
        sigma_e.yz = float(double(SigmaPrec[p].yz) + Rsigmac[p].yz * dt05);
        sigma_e.xz = float(double(SigmaPrec[p].xz) + Rsigmac[p].xz * dt05);
      //-Update DP constants
      float phi=SoilCte.phi;
      float coh=SoilCte.coh;
      float psi=SoilCte.dlt;
      //default 3D 
      float DP_phi = 2.f*sin(phi)/((3.f-sin(phi))* 1.732f);
      float DP_kc = 6.f*coh*cos(phi)/((3.f-sin(phi))* 1.732f);
      float DP_psi = 2.f*sin(psi)/((3.f-sin(psi))* 1.732f);
      if(DPCtes==DP_MC){
         DP_phi = 2.f*sin(phi)/((3.f+sin(phi))* 1.732f);
	     DP_kc = 6.f*coh*cos(phi)/((3.f+sin(phi))* 1.732f);
	     DP_psi = 2.f*sin(psi)/((3.f+sin(psi))* 1.732f);
      }
      if(DPCtes==DP_PS){
         DP_phi = tan(phi)/sqrt(9.f+12.f*tan(phi)*tan(phi));
         DP_kc = 3.f*coh/sqrt(9.f+12.f*tan(phi)*tan(phi)); 
         DP_psi = tan(psi)/sqrt(9.f+12.f*tan(psi)*tan(psi));
      }	
      //-Plastic Corretor
      ConsRelationEP_fast(sigma_e,SoilCte.ModulusK,SoilCte.ModulusG,DP_phi,DP_kc,DP_psi,kplasticold,signew,kplasnew);      
      kplasnew=kplasticold;
      // 
      //-Restore data of inout particles.
      if(InOut && CODE_IsFluidInout(rcode)){
        outrhop=false;
        rvelrhopnew=VelrhopPrec[p];
        const tfloat3 vd=indirvel[CODE_GetIzoneFluidInout(rcode)];
        if(vd.x!=FLT_MAX){
          const float v=rvelrhopnew.x*vd.x + rvelrhopnew.y*vd.y + rvelrhopnew.z*vd.z;
          dx=double(v*vd.x) * dt05;
          dy=double(v*vd.y) * dt05;
          dz=double(v*vd.z) * dt05;
        }
      }
      //-Update particle data.
      movc[p]=TDouble3(dx,dy,dz);
      Velrhopc[p]=rvelrhopnew;
      if(outrhop && CODE_IsNormal(rcode))Codec[p]=CODE_SetOutRhop(rcode); //-Only brands as excluded normal particles (not periodic). | Solo marca como excluidas las normales (no periodicas).
    }
    else{//-Floating Particles.
      Velrhopc[p]=VelrhopPrec[p];
      Velrhopc[p].w=(rhopnew<RhopZero? RhopZero: rhopnew); //-Avoid fluid particles being absorbed by floating ones. | Evita q las floating absorvan a las fluidas.
    }
    Sigmac[p]=signew;//mdbr
    Kplasticc[p]=kplasnew;//mdbr
  }

  //-Applies displacement to non-periodic fluid particles.
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(npf>OMP_LIMIT_COMPUTESTEP)
  #endif
  for(int p=npb;p<np;p++){
    const typecode rcode=Codec[p];
    const bool outrhop=CODE_IsOutRhop(rcode);
    const bool normal=(!PeriActive || outrhop || CODE_IsNormal(rcode));
    if(normal){//-Does not apply to periodic particles. | No se aplica a particulas periodicas
      if(CODE_IsFluid(rcode)){//-Only applied for fluid displacement. | Solo se aplica desplazamiento al fluido.
        UpdatePos(PosPrec[p],movc[p].x,movc[p].y,movc[p].z,outrhop,p,Posc,Dcellc,Codec);
      }
      else Posc[p]=PosPrec[p]; //-Copy position of floating particles.
    }
  }
  
  //-Frees memory allocated for the displacement.
  ArraysCpu->Free(movc);   movc=NULL;

  //-Copy previous position of boundary. | Copia posicion anterior del contorno.
  memcpy(Posc,PosPrec,sizeof(tdouble3)*Npb);

  Timersc->TmStop(TMC_SuComputeStep);
}

//==============================================================================
/// Update particles according to forces and dt using Symplectic-Corrector.
/// Actualizacion de particulas segun fuerzas y dt usando Symplectic-Corrector.
//==============================================================================
void JSphCpu::ComputeSymplecticCorr(double dt){
  Timersc->TmStart(TMC_SuComputeStep);
  const bool shift=(Shifting!=NULL);
  const double dt05=dt*.5;
  const int np=int(Np);
  const int npb=int(Npb);
  const int npf=np-npb;
  
  //-Calculate rhop of boudary and set velocity=0. | Calcula rhop de contorno y vel igual a cero.
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(npb>OMP_LIMIT_COMPUTESTEP)
  #endif
  for(int p=0;p<npb;p++){
    const double epsilon_rdot=(-double(Arc[p])/double(Velrhopc[p].w))*dt;
    const float rhopnew=float(double(VelrhopPrec[p].w) * (2.-epsilon_rdot)/(2.+epsilon_rdot));
    Velrhopc[p]=TFloat4(0,0,0,(rhopnew<RhopZero? RhopZero: rhopnew));//-Avoid fluid particles being absorbed by boundary ones. | Evita q las boundary absorvan a las fluidas.
  }

  //-Compute displacement, velocity and density for fluid.
  tdouble3 *movc=ArraysCpu->ReserveDouble3();
  const tfloat3 *indirvel=(InOut? InOut->GetDirVel(): NULL);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(npf>OMP_LIMIT_COMPUTESTEP)
  #endif
  for(int p=npb;p<np;p++){
    const typecode rcode=Codec[p];
    const double epsilon_rdot=(-double(Arc[p])/double(Velrhopc[p].w))*dt;
    const float rhopnew=float(double(VelrhopPrec[p].w) * (2.-epsilon_rdot)/(2.+epsilon_rdot));
    tsymatrix3f signew=SigmaPrec[p];//mdbr
    float kplasnew=Kplasticc[p];//
    if(!WithFloating || CODE_IsFluid(rcode)){//-Fluid Particles.
      //-Calculate velocity & density. | Calcula velocidad y densidad.
      tfloat4 rvelrhopnew=TFloat4(
        float(double(VelrhopPrec[p].x) + (double(Acec[p].x)+Gravity.x) * dt), 
        float(double(VelrhopPrec[p].y) + (double(Acec[p].y)+Gravity.y) * dt), 
        float(double(VelrhopPrec[p].z) + (double(Acec[p].z)+Gravity.z) * dt),
        rhopnew);
      //-Calculate elastic stress
        tsymatrix3f sigma_e={0,0,0,0,0,0};
        float kplasticold = Kplasticc[p];
        sigma_e.xx = float(double(SigmaPrec[p].xx) + Rsigmac[p].xx * dt);
        sigma_e.yy = float(double(SigmaPrec[p].yy) + Rsigmac[p].yy * dt);
        sigma_e.zz = float(double(SigmaPrec[p].zz) + Rsigmac[p].zz * dt);
        sigma_e.xy = float(double(SigmaPrec[p].xy) + Rsigmac[p].xy * dt);
        sigma_e.yz = float(double(SigmaPrec[p].yz) + Rsigmac[p].yz * dt);
        sigma_e.xz = float(double(SigmaPrec[p].xz) + Rsigmac[p].xz * dt);
      //-Update DP constants
      float phi=SoilCte.phi;
      float coh=SoilCte.coh;
      float psi=SoilCte.dlt;
      //default 3D 
      float DP_phi = 2.f*sin(phi)/((3.f-sin(phi))* 1.732f);
      float DP_kc = 6.f*coh*cos(phi)/((3.f-sin(phi))* 1.732f);
      float DP_psi = 2.f*sin(psi)/((3.f-sin(psi))* 1.732f);
      if(DPCtes==DP_MC){
         DP_phi = 2.f*sin(phi)/((3.f+sin(phi))* 1.732f);
	     DP_kc = 6.f*coh*cos(phi)/((3.f+sin(phi))* 1.732f);
	     DP_psi = 2.f*sin(psi)/((3.f+sin(psi))* 1.732f);
      }
      if(DPCtes==DP_PS){
         DP_phi = tan(phi)/sqrt(9.f+12.f*tan(phi)*tan(phi));
         DP_kc = 3.f*coh/sqrt(9.f+12.f*tan(phi)*tan(phi)); 
         DP_psi = tan(psi)/sqrt(9.f+12.f*tan(psi)*tan(psi));
      }	
      //-Plastic Corretor
      ConsRelationEP_fast(sigma_e,SoilCte.ModulusK,SoilCte.ModulusG,DP_phi,DP_kc,DP_psi,kplasticold,signew,kplasnew);
      // 
      //-Calculate displacement. | Calcula desplazamiento.
      double dx=(double(VelrhopPrec[p].x)+double(rvelrhopnew.x)) * dt05; 
      double dy=(double(VelrhopPrec[p].y)+double(rvelrhopnew.y)) * dt05; 
      double dz=(double(VelrhopPrec[p].z)+double(rvelrhopnew.z)) * dt05;
      if(shift){
        dx+=double(ShiftPosfsc[p].x);
        dy+=double(ShiftPosfsc[p].y);
        dz+=double(ShiftPosfsc[p].z);
      }
      bool outrhop=(rhopnew<RhopOutMin || rhopnew>RhopOutMax);
      //-Restore data of inout particles.
      if(InOut && CODE_IsFluidInout(rcode)){
        outrhop=false;
        rvelrhopnew=VelrhopPrec[p];
        const tfloat3 vd=indirvel[CODE_GetIzoneFluidInout(rcode)];
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
      movc[p]=TDouble3(dx,dy,dz);
      if(outrhop && CODE_IsNormal(rcode))Codec[p]=CODE_SetOutRhop(rcode); //-Only brands as excluded normal particles (not periodic). | Solo marca como excluidas las normales (no periodicas).
      Velrhopc[p]=rvelrhopnew;
    }
    else{//-Floating Particles.
      Velrhopc[p]=VelrhopPrec[p];
      Velrhopc[p].w=(rhopnew<RhopZero? RhopZero: rhopnew); //-Avoid fluid particles being absorbed by floating ones. | Evita q las floating absorvan a las fluidas.
    }
    Sigmac[p]=signew;//mdbr
    Kplasticc[p]=kplasnew;//mdbr
  }

  //-Applies displacement to non-periodic fluid particles.
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(npf>OMP_LIMIT_COMPUTESTEP)
  #endif
  for(int p=npb;p<np;p++){
    const typecode rcode=Codec[p];
    const bool outrhop=CODE_IsOutRhop(rcode);
    const bool normal=(!PeriActive || outrhop || CODE_IsNormal(rcode));
    if(normal){//-Does not apply to periodic particles. | No se aplica a particulas periodicas
      if(CODE_IsFluid(rcode)){//-Only applied for fluid displacement. | Solo se aplica desplazamiento al fluido.
        UpdatePos(PosPrec[p],movc[p].x,movc[p].y,movc[p].z,outrhop,p,Posc,Dcellc,Codec);
      }
      else Posc[p]=PosPrec[p]; //-Copy position of floating particles.
    }
  }
 
  //-Frees memory allocated for the displacement.
  ArraysCpu->Free(movc);   movc=NULL;

  //-Free memory assigned to variables Pre and ComputeSymplecticPre(). | Libera memoria asignada a variables Pre en ComputeSymplecticPre().
  ArraysCpu->Free(PosPrec);      PosPrec=NULL;
  ArraysCpu->Free(VelrhopPrec);  VelrhopPrec=NULL;
  ArraysCpu->Free(SigmaPrec);    SigmaPrec=NULL;//mdbr
  Timersc->TmStop(TMC_SuComputeStep);
}



//==============================================================================
/// Calculate variable Dt.
/// Calcula un Dt variable.
//==============================================================================
double JSphCpu::DtVariable(bool final){
  //-dt1 depends on force per unit mass.
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
  //-Pore-pressure stability timestep restriction for saturated u-pw PR prototype.
  double dtpore=DBL_MAX;
  bool dtporeactive=false;
  if(HydromechCoupling && PorePressureModel==1){
    if(HydraulicConductivity>0.f && WaterBulkModulus>0.f && WaterDensity>0.f && Porosity0>0.f && Porosity0<1.f && PorePressureDtSafety>0.f){
      const double gmag=sqrt(double(Gravity.x)*double(Gravity.x)+double(Gravity.y)*double(Gravity.y)+double(Gravity.z)*double(Gravity.z));
      if(gmag<=0.)Run_Exceptioon("Gravity magnitude must be greater than zero for pore-pressure timestep restriction.");
      const double cw=double(WaterDensity)*gmag*double(Porosity0)/double(WaterBulkModulus);
      dtpore=double(PorePressureDtSafety)*cw*double(KernelH)*double(KernelH)/double(HydraulicConductivity);
      if(dtpore<=0. || fun::IsNAN(dtpore) || fun::IsInfinity(dtpore))Run_Exceptioon(fun::PrintStr("The computed pore-pressure timestep is invalid (dt_pore=%g).",dtpore));
      dtporeactive=true;
      if(!PorePressureDtConfigPrint){
        Log->Printf("Pore-pressure timestep restriction: active=True, Cw=%g, dt_pore=%g, safety=%g, h(KernelH)=%g.",cw,dtpore,PorePressureDtSafety,KernelH);
        if(FixedDt)Log->PrintWarning(fun::PrintStr("Fixed dt is enabled. Fixed dt should be <= dt_pore=%g for PR pore-pressure update.",dtpore));
        PorePressureDtConfigPrint=true;
        PorePressureDtFixedPrint=(FixedDt!=NULL);
      }
    }
    else if(HydraulicConductivity==0.f){
      if(!PorePressureDtConfigPrint){
        Log->Print("Pore-pressure timestep restriction: active=False, disabled because HydraulicConductivity=0.");
        PorePressureDtConfigPrint=true;
      }
    }
    else if(HydraulicConductivity>0.f)Run_Exceptioon("Invalid hydromechanical parameters for pore-pressure timestep restriction.");
  }
  PorePressureDt=dtpore;
  PorePressureDtActive=dtporeactive;
  if(dtporeactive && dt>dtpore){
    if(final && !PorePressureDtLimitPrint){
      Log->Printf("Current dt is limited by pore-pressure timestep: existing_dt=%g, dt_pore=%g.",dt,dtpore);
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
/// Calculate final Shifting for particles' position.
/// Calcula Shifting final para posicion de particulas.
//==============================================================================
void JSphCpu::RunShifting(double dt){
  Timersc->TmStart(TMC_SuShifting);
  Shifting->RunCpu(Np-Npb,Npb,dt,Velrhopc,ShiftPosfsc);
  Timersc->TmStop(TMC_SuShifting);
}

//==============================================================================
/// Calculate position of particles according to idp[]. When it is not met set as UINT_MAX.
/// When periactive is False assume that there are no duplicate particles (periodic ones)
/// and all are set as CODE_NORMAL.
///
/// Calcula posicion de particulas segun idp[]. Cuando no la encuentra es UINT_MAX.
/// Cuando periactive es False supone que no hay particulas duplicadas (periodicas)
/// y todas son CODE_NORMAL.
//==============================================================================
void JSphCpu::CalcRidp(bool periactive,unsigned np,unsigned pini,unsigned idini,unsigned idfin,const typecode *code,const unsigned *idp,unsigned *ridp)const{
  //-Assign values UINT_MAX. | Asigna valores UINT_MAX.
  const unsigned nsel=idfin-idini;
  memset(ridp,255,sizeof(unsigned)*nsel); 
  //-Calculate position according to id. | Calcula posicion segun id.
  const int pfin=int(pini+np);
  if(periactive){//-Calculate position according to id checking that the particles are normal (i.e. not periodic). | Calcula posicion segun id comprobando que las particulas son normales (no periodicas).
    #ifdef OMP_USE
      #pragma omp parallel for schedule (static) if(pfin>OMP_LIMIT_COMPUTELIGHT)
    #endif
    for(int p=int(pini);p<pfin;p++){
      const unsigned id=idp[p];
      if(idini<=id && id<idfin){
        if(CODE_IsNormal(code[p]))ridp[id-idini]=p;
      }
    }
  }
  else{//-Calculate position according to id assuming that all the particles are normal (i.e. not periodic). | Calcula posicion segun id suponiendo que todas las particulas son normales (no periodicas).
    #ifdef OMP_USE
      #pragma omp parallel for schedule (static) if(pfin>OMP_LIMIT_COMPUTELIGHT)
    #endif
    for(int p=int(pini);p<pfin;p++){
      const unsigned id=idp[p];
      if(idini<=id && id<idfin)ridp[id-idini]=p;
    }
  }
}

//==============================================================================
/// Applies a linear movement to a group of particles.
/// Aplica un movimiento lineal a un conjunto de particulas.
//==============================================================================
void JSphCpu::MoveLinBound(unsigned np,unsigned ini,const tdouble3 &mvpos,const tfloat3 &mvvel
  ,const unsigned *ridp,tdouble3 *pos,unsigned *dcell,tfloat4 *velrhop,typecode *code)const
{
  const unsigned fin=ini+np;
  for(unsigned id=ini;id<fin;id++){
    const unsigned pid=RidpMove[id];
    if(pid!=UINT_MAX){
      UpdatePos(pos[pid],mvpos.x,mvpos.y,mvpos.z,false,pid,pos,dcell,code);
      velrhop[pid].x=mvvel.x;  velrhop[pid].y=mvvel.y;  velrhop[pid].z=mvvel.z;
    }
  }
}

//==============================================================================
/// Applies a matrix movement to a group of particles.
/// Aplica un movimiento matricial a un conjunto de particulas.
//==============================================================================
void JSphCpu::MoveMatBound(unsigned np,unsigned ini,tmatrix4d m,double dt,const unsigned *ridpmv
  ,tdouble3 *pos,unsigned *dcell,tfloat4 *velrhop,typecode *code,tfloat3 *boundnormal)const
{
  const unsigned fin=ini+np;
  for(unsigned id=ini;id<fin;id++){
    const unsigned pid=RidpMove[id];
    if(pid!=UINT_MAX){
      const tdouble3 ps=pos[pid];
      tdouble3 ps2=MatrixMulPoint(m,ps);
      if(Simulate2D)ps2.y=ps.y;
      const double dx=ps2.x-ps.x, dy=ps2.y-ps.y, dz=ps2.z-ps.z;
      UpdatePos(ps,dx,dy,dz,false,pid,pos,dcell,code);
      velrhop[pid].x=float(dx/dt);  velrhop[pid].y=float(dy/dt);  velrhop[pid].z=float(dz/dt);
      //-Computes normal.
      if(boundnormal){
        const tdouble3 gs=ps+ToTDouble3(boundnormal[pid]);
        const tdouble3 gs2=MatrixMulPoint(m,gs);
        boundnormal[pid]=ToTFloat3(gs2-ps2);
      }
    }
  }
}

//==============================================================================
/// Copy motion velocity to MotionVel[].
/// Copia velocidad de movimiento a MotionVel[].
//==============================================================================
void JSphCpu::CopyMotionVel(unsigned nmoving,const unsigned *ridp
  ,const tfloat4 *velrhop,tfloat3 *motionvel)const
{
  for(unsigned id=0;id<nmoving;id++){
    const unsigned pid=RidpMove[id];
    if(pid!=UINT_MAX){
      const tfloat4 v=velrhop[pid];
      motionvel[pid]=TFloat3(v.x,v.y,v.z);
    }
  }
}

//==============================================================================
/// Calculates predefined movement of boundary particles.
/// Calcula movimiento predefinido de boundary particles.
//==============================================================================
void JSphCpu::CalcMotion(double stepdt){
  Timersc->TmStart(TMC_SuMotion);
  JSph::CalcMotion(stepdt);
  Timersc->TmStop(TMC_SuMotion);
}

//==============================================================================
/// Process movement of boundary particles.
/// Procesa movimiento de boundary particles.
//==============================================================================
void JSphCpu::RunMotion(double stepdt){
  Timersc->TmStart(TMC_SuMotion);
  tfloat3 *boundnormal=NULL;
  boundnormal=BoundNormalc;
  const bool motsim=true;
  BoundChanged=false;
  //-Add motion from automatic wave generation.
  if(WaveGen)CalcMotionWaveGen(stepdt);
  //-Process particles motion.
  if(DsMotion->GetActiveMotion()){
    CalcRidp(PeriActive!=0,Npb,0,CaseNfixed,CaseNfixed+CaseNmoving,Codec,Idpc,RidpMove);
    BoundChanged=true;
    const unsigned nref=DsMotion->GetNumObjects();
    for(unsigned ref=0;ref<nref;ref++){
      const StMotionData& m=DsMotion->GetMotionData(ref);
      if(m.type==MOTT_Linear){//-Linear movement.
        if(motsim)MoveLinBound   (m.count,m.idbegin-CaseNfixed,m.linmov,ToTFloat3(m.linvel),RidpMove,Posc,Dcellc,Velrhopc,Codec);
        //else    MoveLinBoundAce(m.count,m.idbegin-CaseNfixed,m.linmov,ToTFloat3(m.linvel),ToTFloat3(m.linace),RidpMove,Posc,Dcellc,Velrhopc,Acec,Codec);
      }
      if(m.type==MOTT_Matrix){//-Matrix movement (for rotations).
        if(motsim)MoveMatBound   (m.count,m.idbegin-CaseNfixed,m.matmov,stepdt,RidpMove,Posc,Dcellc,Velrhopc,Codec,boundnormal); 
        //else    MoveMatBoundAce(m.count,m.idbegin-CaseNfixed,m.matmov,m.matmov2,stepdt,RidpMove,Posc,Dcellc,Velrhopc,Acec,Codec);
      }      
    }
  }
  //-Management of Multi-Layer Pistons.
  if(MLPistons){
    if(!BoundChanged)CalcRidp(PeriActive!=0,Npb,0,CaseNfixed,CaseNfixed+CaseNmoving,Codec,Idpc,RidpMove);
    BoundChanged=true;
    if(MLPistons->GetPiston1dCount()){//-Process motion for pistons 1D.
      MLPistons->CalculateMotion1d(TimeStep+MLPistons->GetTimeMod()+stepdt);
      MovePiston1d(CaseNmoving,0,MLPistons->GetPoszMin(),MLPistons->GetPoszCount()
        ,MLPistons->GetPistonId(),MLPistons->GetMovx(),MLPistons->GetVelx()
        ,RidpMove,Posc,Dcellc,Velrhopc,Codec);
    }
    for(unsigned cp=0;cp<MLPistons->GetPiston2dCount();cp++){//-Process motion for pistons 2D.
      JMLPistons::StMotionInfoPiston2D mot=MLPistons->CalculateMotion2d(cp,TimeStep+MLPistons->GetTimeMod()+stepdt);
      MovePiston2d(mot.np,mot.idbegin-CaseNfixed,mot.posymin,mot.poszmin,mot.poszcount,mot.movyz,mot.velyz
        ,RidpMove,Posc,Dcellc,Velrhopc,Codec);
    }
  }
  if(MotionVelc)CopyMotionVel(CaseNmoving,RidpMove,Velrhopc,MotionVelc);
  Timersc->TmStop(TMC_SuMotion);
}

//==============================================================================
/// Applies movement and velocity of piston 1D to a group of particles.
/// Aplica movimiento y velocidad de piston 1D a conjunto de particulas.
//==============================================================================
void JSphCpu::MovePiston1d(unsigned np,unsigned ini
  ,double poszmin,unsigned poszcount,const byte *pistonid,const double* movx,const double* velx
  ,const unsigned *ridpmv,tdouble3 *pos,unsigned *dcell,tfloat4 *velrhop,typecode *code)const
{
  const int fin=int(ini+np);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(fin>OMP_LIMIT_LIGHT)
  #endif
  for(int id=int(ini);id<fin;id++){
    const unsigned pid=ridpmv[id];
    if(pid!=UINT_MAX){
      const unsigned pisid=pistonid[CODE_GetTypeValue(code[pid])];
      if(pisid<255){
        const unsigned cz=unsigned((pos[pid].z-poszmin)/Dp);
        const double rmovx=(cz<poszcount? movx[pisid*poszcount+cz]: 0);
        const float rvelx=float(cz<poszcount? velx[pisid*poszcount+cz]: 0);
        //-Updates position.
        UpdatePos(pos[pid],rmovx,0,0,false,pid,pos,dcell,code);
        //-Updates velocity.
        velrhop[pid].x=rvelx;
      }
    }
  }
}
//==============================================================================
/// Applies movement and velocity of piston 2D to a group of particles.
/// Aplica movimiento y velocidad de piston 2D a conjunto de particulas.
//==============================================================================
void JSphCpu::MovePiston2d(unsigned np,unsigned ini
  ,double posymin,double poszmin,unsigned poszcount,const double* movx,const double* velx
  ,const unsigned *ridpmv,tdouble3 *pos,unsigned *dcell,tfloat4 *velrhop,typecode *code)const
{
  const int fin=int(ini+np);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(fin>OMP_LIMIT_LIGHT)
  #endif
  for(int id=int(ini);id<fin;id++){
    const unsigned pid=ridpmv[id];
    if(pid!=UINT_MAX){
      const tdouble3 ps=pos[pid];
      const unsigned cy=unsigned((ps.y-posymin)/Dp);
      const unsigned cz=unsigned((ps.z-poszmin)/Dp);
      const double rmovx=(cz<poszcount? movx[cy*poszcount+cz]: 0);
      const float rvelx=float(cz<poszcount? velx[cy*poszcount+cz]: 0);
      //-Updates position.
      UpdatePos(ps,rmovx,0,0,false,pid,pos,dcell,code);
      //-Updates velocity.
      velrhop[pid].x=rvelx;
    }
  }
}

//==============================================================================
/// Applies RelaxZone to selected particles.
/// Aplica RelaxZone a las particulas indicadas.
//==============================================================================
void JSphCpu::RunRelaxZone(double dt){
  Timersc->TmStart(TMC_SuMotion);
  byte* rzid=NULL;
  float* rzfactor=NULL; 
  RelaxZones->SetFluidVel(TimeStep,dt,Np-Npb,Npb,Posc,Idpc,Velrhopc,rzid,rzfactor);
  Timersc->TmStop(TMC_SuMotion);
}

//==============================================================================
/// Applies Damping to selected particles.
/// Aplica Damping a las particulas indicadas.
//==============================================================================
void JSphCpu::RunDamping(double dt,unsigned np,unsigned npb,const tdouble3 *pos,const typecode *code,tfloat4 *velrhop)const{
  const typecode *codeptr=(CaseNfloat || PeriActive? code: NULL);
  Damping->ComputeDampingCpu(TimeStep,dt,np-npb,npb,pos,codeptr,velrhop);
}

//==============================================================================
/// Adjust variables of floating body particles.
/// Ajusta variables de particulas floating body.
//==============================================================================
void JSphCpu::InitFloating(){
  if(PartBegin){
    JPartFloatBi4Load ftdata;
    ftdata.LoadFile(PartBeginDir);
    //-Check cases of constant values. | Comprueba coincidencia de datos constantes.
    for(unsigned cf=0;cf<FtCount;cf++){
      const StFloatingData &ft=FtObjs[cf];
      ftdata.CheckHeadData(cf,ft.mkbound,ft.begin,ft.count,ft.mass,ft.massp);
    }
    //-Load PART data. | Carga datos de PART.
    ftdata.LoadPart(PartBegin);
    for(unsigned cf=0;cf<FtCount;cf++){
      FtObjs[cf].center=ftdata.GetPartCenter(cf);
      FtObjs[cf].fvel  =ftdata.GetPartVelLin(cf);
      FtObjs[cf].fomega=ftdata.GetPartVelAng(cf);
      FtObjs[cf].radius=ftdata.GetHeadRadius(cf);
    }
    DemDtForce=ftdata.GetPartDemDtForce();
  }
}



