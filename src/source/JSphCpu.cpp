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
#include "JSphMk.h"
#include "JSphInOut.h"
#include "JSphShifting.h"

#include <climits>
#include <cfloat>
#include <cmath>
#include <array>
#include <algorithm>
#include <vector>

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
  MccPcc=NULL; MccVoidRatioc=NULL; MccPlasticVolStrainc=NULL; MccEqPlasticStrainc=NULL; MccYieldFlagc=NULL; MccPlasticMultiplierc=NULL; MccReturnStatusc=NULL; MccReturnIterationsc=NULL; MccYieldResidualc=NULL; MccSubstepCountc=NULL; MccSubstepFailureCountc=NULL; MccAdmissibilityFailureCountc=NULL; MccFallbackUsedc=NULL; MccSubstepTriggerReasonc=NULL; MccLineSearchBacktrackCountc=NULL; MccLineSearchRejectReasonc=NULL; MccLineSearchMinAlphac=NULL;
  ArtificialStressc=NULL;
  //======
  PorePressc=NULL; PorePressRatec=NULL; DivVelc=NULL; LapPorePressc=NULL; LapZc=NULL; DivVelCorrc=NULL; LapPorePressCorrc=NULL; LapZCorrc=NULL; PorePressureAcec=NULL; PorePressureAceDiffc=NULL; PorePressureFeedbackUsedAcec=NULL;
  PorePressGhostc=NULL; ExcessPorePressGhostc=NULL; PorePressureBoundaryModec=NULL; LapPorePressGhostc=NULL; LapZGhostc=NULL;
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
  PorePressureTopDrainedStepPrint=false;
  PorePressureBottomNoFluxStepPrint=false;
  PorePressureShepardStepPrint=false;
  PorePressureBoundaryGhostPrint=false;
  PorePressureBoundaryOperatorPrint=false;
  HydroCorrDiagPrint=false;
  HydromechDampingStepPrint=false;
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
  delete[] MccPcc; MccPcc=NULL;
  delete[] MccVoidRatioc; MccVoidRatioc=NULL;
  delete[] MccPlasticVolStrainc; MccPlasticVolStrainc=NULL;
  delete[] MccEqPlasticStrainc; MccEqPlasticStrainc=NULL;
  delete[] MccYieldFlagc; MccYieldFlagc=NULL;
  delete[] MccPlasticMultiplierc; MccPlasticMultiplierc=NULL;
  delete[] MccReturnStatusc; MccReturnStatusc=NULL;
  delete[] MccReturnIterationsc; MccReturnIterationsc=NULL;
  delete[] MccYieldResidualc; MccYieldResidualc=NULL;
  delete[] MccSubstepCountc; MccSubstepCountc=NULL;
  delete[] MccSubstepFailureCountc; MccSubstepFailureCountc=NULL;
  delete[] MccAdmissibilityFailureCountc; MccAdmissibilityFailureCountc=NULL;
  delete[] MccFallbackUsedc; MccFallbackUsedc=NULL;
  delete[] MccSubstepTriggerReasonc; MccSubstepTriggerReasonc=NULL;
  delete[] MccLineSearchBacktrackCountc; MccLineSearchBacktrackCountc=NULL;
  delete[] MccLineSearchRejectReasonc; MccLineSearchRejectReasonc=NULL;
  delete[] MccLineSearchMinAlphac; MccLineSearchMinAlphac=NULL;
  CpuParticlesSize=0;
  MemCpuParticles=0;
  ArraysCpu->Reset();
  PorePressc=NULL; PorePressRatec=NULL; DivVelc=NULL; LapPorePressc=NULL; LapZc=NULL; DivVelCorrc=NULL; LapPorePressCorrc=NULL; LapZCorrc=NULL; PorePressureAcec=NULL; PorePressureAceDiffc=NULL; PorePressureFeedbackUsedAcec=NULL;
  PorePressGhostc=NULL; ExcessPorePressGhostc=NULL; PorePressureBoundaryModec=NULL; LapPorePressGhostc=NULL; LapZGhostc=NULL;
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
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,7); //-porepressrate,divvel,lapporepress,lapz,divvelcorr,lapporepresscorr,lapzcorr
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_12B,3); //-porepressureace,porepressureacediff,porepressurefeedbackused
  }
  if(PorePressureBoundaryGhost){
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_8B,2); //-porepressghost,excessporepressghost
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,3); //-porepressureboundarymode,lapporepressghost,lapzghost
  }
  if(SavePorePressure){
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_8B,2); //-porepress,excessporepress output
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,7); //-porepressrate,divvel,lapporepress,lapz,divvelcorr,lapporepresscorr,lapzcorr output
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_12B,2); //-porepressureace,porepressureacediff output
    if(PorePressureBoundaryGhost && PorePressureBoundaryGhostOutput){
      ArraysCpu->AddArrayCount(JArraysCpu::SIZE_8B,2); //-porepressghost,excessporepressghost output
      ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,3); //-porepressureboundarymode,lapporepressghost,lapzghost output
    }
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
  float        *mccpc     =SaveArrayCpu(Np,MccPcc);
  float        *mccvoidratio=SaveArrayCpu(Np,MccVoidRatioc);
  float        *mccplasticvolstrain=SaveArrayCpu(Np,MccPlasticVolStrainc);
  float        *mcceqplasticstrain=SaveArrayCpu(Np,MccEqPlasticStrainc);
  float        *mccyieldflag=SaveArrayCpu(Np,MccYieldFlagc);
  float        *mccplasticmultiplier=SaveArrayCpu(Np,MccPlasticMultiplierc);
  float        *mccreturnstatus=SaveArrayCpu(Np,MccReturnStatusc);
  float        *mccreturniterations=SaveArrayCpu(Np,MccReturnIterationsc);
  float        *mccyieldresidual=SaveArrayCpu(Np,MccYieldResidualc);
  float        *mccsubstepcount=SaveArrayCpu(Np,MccSubstepCountc);
  float        *mccsubstepfailurecount=SaveArrayCpu(Np,MccSubstepFailureCountc);
  float        *mccadmissibilityfailurecount=SaveArrayCpu(Np,MccAdmissibilityFailureCountc);
  float        *mccfallbackused=SaveArrayCpu(Np,MccFallbackUsedc);
  float        *mccsubsteptriggerreason=SaveArrayCpu(Np,MccSubstepTriggerReasonc);
  float        *mcclinesearchbacktrackcount=SaveArrayCpu(Np,MccLineSearchBacktrackCountc);
  float        *mcclinesearchrejectreason=SaveArrayCpu(Np,MccLineSearchRejectReasonc);
  float        *mcclinesearchminalpha=SaveArrayCpu(Np,MccLineSearchMinAlphac);
  double       *porepress =SaveArrayCpu(Np,PorePressc);
  float        *porepressrate=SaveArrayCpu(Np,PorePressRatec);
  float        *divvel    =SaveArrayCpu(Np,DivVelc);
  float        *lapporepress=SaveArrayCpu(Np,LapPorePressc);
  float        *lapz      =SaveArrayCpu(Np,LapZc);
  float        *divvelcorr=SaveArrayCpu(Np,DivVelCorrc);
  float        *lapporepresscorr=SaveArrayCpu(Np,LapPorePressCorrc);
  float        *lapzcorr=SaveArrayCpu(Np,LapZCorrc);
  tfloat3      *porepressureace=SaveArrayCpu(Np,PorePressureAcec);
  tfloat3      *porepressureacediff=SaveArrayCpu(Np,PorePressureAceDiffc);
  tfloat3      *porepressurefeedbackused=SaveArrayCpu(Np,PorePressureFeedbackUsedAcec);
  double       *porepressghost=SaveArrayCpu(Np,PorePressGhostc);
  double       *excessporepressghost=SaveArrayCpu(Np,ExcessPorePressGhostc);
  float        *porepressureboundarymode=SaveArrayCpu(Np,PorePressureBoundaryModec);
  float        *lapporepressghost=SaveArrayCpu(Np,LapPorePressGhostc);
  float        *lapzghost=SaveArrayCpu(Np,LapZGhostc);
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
  delete[] MccPcc; MccPcc=NULL;
  delete[] MccVoidRatioc; MccVoidRatioc=NULL;
  delete[] MccPlasticVolStrainc; MccPlasticVolStrainc=NULL;
  delete[] MccEqPlasticStrainc; MccEqPlasticStrainc=NULL;
  delete[] MccYieldFlagc; MccYieldFlagc=NULL;
  delete[] MccPlasticMultiplierc; MccPlasticMultiplierc=NULL;
  delete[] MccReturnStatusc; MccReturnStatusc=NULL;
  delete[] MccReturnIterationsc; MccReturnIterationsc=NULL;
  delete[] MccYieldResidualc; MccYieldResidualc=NULL;
  delete[] MccSubstepCountc; MccSubstepCountc=NULL;
  delete[] MccSubstepFailureCountc; MccSubstepFailureCountc=NULL;
  delete[] MccAdmissibilityFailureCountc; MccAdmissibilityFailureCountc=NULL;
  delete[] MccFallbackUsedc; MccFallbackUsedc=NULL;
  delete[] MccSubstepTriggerReasonc; MccSubstepTriggerReasonc=NULL;
  delete[] MccLineSearchBacktrackCountc; MccLineSearchBacktrackCountc=NULL;
  delete[] MccLineSearchRejectReasonc; MccLineSearchRejectReasonc=NULL;
  delete[] MccLineSearchMinAlphac; MccLineSearchMinAlphac=NULL;
  ArraysCpu->Free(PorePressc);
  ArraysCpu->Free(PorePressRatec);
  ArraysCpu->Free(DivVelc);
  ArraysCpu->Free(LapPorePressc);
  ArraysCpu->Free(LapZc);
  ArraysCpu->Free(DivVelCorrc);
  ArraysCpu->Free(LapPorePressCorrc);
  ArraysCpu->Free(LapZCorrc);
  ArraysCpu->Free(PorePressureAcec);
  ArraysCpu->Free(PorePressureAceDiffc);
  ArraysCpu->Free(PorePressureFeedbackUsedAcec);
  ArraysCpu->Free(PorePressGhostc);
  ArraysCpu->Free(ExcessPorePressGhostc);
  ArraysCpu->Free(PorePressureBoundaryModec);
  ArraysCpu->Free(LapPorePressGhostc);
  ArraysCpu->Free(LapZGhostc);
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
  try{
    if(mccpc)       MccPcc = new float[npnew];
    if(mccvoidratio)MccVoidRatioc = new float[npnew];
    if(mccplasticvolstrain)MccPlasticVolStrainc = new float[npnew];
    if(mcceqplasticstrain)MccEqPlasticStrainc = new float[npnew];
    if(mccyieldflag)MccYieldFlagc = new float[npnew];
    if(mccplasticmultiplier)MccPlasticMultiplierc = new float[npnew];
    if(mccreturnstatus)MccReturnStatusc = new float[npnew];
    if(mccreturniterations)MccReturnIterationsc = new float[npnew];
    if(mccyieldresidual)MccYieldResidualc = new float[npnew];
    if(mccsubstepcount)MccSubstepCountc = new float[npnew];
    if(mccsubstepfailurecount)MccSubstepFailureCountc = new float[npnew];
    if(mccadmissibilityfailurecount)MccAdmissibilityFailureCountc = new float[npnew];
    if(mccfallbackused)MccFallbackUsedc = new float[npnew];
    if(mccsubsteptriggerreason)MccSubstepTriggerReasonc = new float[npnew];
    if(mcclinesearchbacktrackcount)MccLineSearchBacktrackCountc = new float[npnew];
    if(mcclinesearchrejectreason)MccLineSearchRejectReasonc = new float[npnew];
    if(mcclinesearchminalpha)MccLineSearchMinAlphac = new float[npnew];
  }
  catch(const std::bad_alloc){
    Run_Exceptioon("Could not allocate the requested MCC state memory.");
  }
  if(porepress)     PorePressc = ArraysCpu->ReserveDouble();
  if(porepressrate) PorePressRatec = ArraysCpu->ReserveFloat();
  if(divvel)        DivVelc = ArraysCpu->ReserveFloat();
  if(lapporepress)  LapPorePressc = ArraysCpu->ReserveFloat();
  if(lapz)          LapZc = ArraysCpu->ReserveFloat();
  if(divvelcorr)    DivVelCorrc = ArraysCpu->ReserveFloat();
  if(lapporepresscorr) LapPorePressCorrc = ArraysCpu->ReserveFloat();
  if(lapzcorr)      LapZCorrc = ArraysCpu->ReserveFloat();
  if(porepressureace) PorePressureAcec = ArraysCpu->ReserveFloat3();
  if(porepressureacediff) PorePressureAceDiffc = ArraysCpu->ReserveFloat3();
  if(porepressurefeedbackused) PorePressureFeedbackUsedAcec = ArraysCpu->ReserveFloat3();
  if(porepressghost) PorePressGhostc = ArraysCpu->ReserveDouble();
  if(excessporepressghost) ExcessPorePressGhostc = ArraysCpu->ReserveDouble();
  if(porepressureboundarymode) PorePressureBoundaryModec = ArraysCpu->ReserveFloat();
  if(lapporepressghost) LapPorePressGhostc = ArraysCpu->ReserveFloat();
  if(lapzghost) LapZGhostc = ArraysCpu->ReserveFloat();
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
  RestoreArrayCpu(Np,mccpc,MccPcc);
  RestoreArrayCpu(Np,mccvoidratio,MccVoidRatioc);
  RestoreArrayCpu(Np,mccplasticvolstrain,MccPlasticVolStrainc);
  RestoreArrayCpu(Np,mcceqplasticstrain,MccEqPlasticStrainc);
  RestoreArrayCpu(Np,mccyieldflag,MccYieldFlagc);
  RestoreArrayCpu(Np,mccplasticmultiplier,MccPlasticMultiplierc);
  RestoreArrayCpu(Np,mccreturnstatus,MccReturnStatusc);
  RestoreArrayCpu(Np,mccreturniterations,MccReturnIterationsc);
  RestoreArrayCpu(Np,mccyieldresidual,MccYieldResidualc);
  RestoreArrayCpu(Np,mccsubstepcount,MccSubstepCountc);
  RestoreArrayCpu(Np,mccsubstepfailurecount,MccSubstepFailureCountc);
  RestoreArrayCpu(Np,mccadmissibilityfailurecount,MccAdmissibilityFailureCountc);
  RestoreArrayCpu(Np,mccfallbackused,MccFallbackUsedc);
  RestoreArrayCpu(Np,mccsubsteptriggerreason,MccSubstepTriggerReasonc);
  RestoreArrayCpu(Np,mcclinesearchbacktrackcount,MccLineSearchBacktrackCountc);
  RestoreArrayCpu(Np,mcclinesearchrejectreason,MccLineSearchRejectReasonc);
  RestoreArrayCpu(Np,mcclinesearchminalpha,MccLineSearchMinAlphac);
  RestoreArrayCpu(Np,porepress,PorePressc);
  RestoreArrayCpu(Np,porepressrate,PorePressRatec);
  RestoreArrayCpu(Np,divvel,DivVelc);
  RestoreArrayCpu(Np,lapporepress,LapPorePressc);
  RestoreArrayCpu(Np,lapz,LapZc);
  RestoreArrayCpu(Np,divvelcorr,DivVelCorrc);
  RestoreArrayCpu(Np,lapporepresscorr,LapPorePressCorrc);
  RestoreArrayCpu(Np,lapzcorr,LapZCorrc);
  RestoreArrayCpu(Np,porepressureace,PorePressureAcec);
  RestoreArrayCpu(Np,porepressureacediff,PorePressureAceDiffc);
  RestoreArrayCpu(Np,porepressurefeedbackused,PorePressureFeedbackUsedAcec);
  RestoreArrayCpu(Np,porepressghost,PorePressGhostc);
  RestoreArrayCpu(Np,excessporepressghost,ExcessPorePressGhostc);
  RestoreArrayCpu(Np,porepressureboundarymode,PorePressureBoundaryModec);
  RestoreArrayCpu(Np,lapporepressghost,LapPorePressGhostc);
  RestoreArrayCpu(Np,lapzghost,LapZGhostc);
  //=====
  //-Updates values.
  CpuParticlesSize=npnew;
  MemCpuParticles=ArraysCpu->GetAllocMemoryCpu();
  if(MccPcc)MemCpuParticles+=sizeof(float)*14*CpuParticlesSize;
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
  if(SoilCte.SoilConstitutiveModel==3 || SoilCte.SaveMccState){
    try{
      MccPcc=new float[CpuParticlesSize];
      MccVoidRatioc=new float[CpuParticlesSize];
      MccPlasticVolStrainc=new float[CpuParticlesSize];
      MccEqPlasticStrainc=new float[CpuParticlesSize];
      MccYieldFlagc=new float[CpuParticlesSize];
      MccPlasticMultiplierc=new float[CpuParticlesSize];
      MccReturnStatusc=new float[CpuParticlesSize];
      MccReturnIterationsc=new float[CpuParticlesSize];
      MccYieldResidualc=new float[CpuParticlesSize];
      MccSubstepCountc=new float[CpuParticlesSize];
      MccSubstepFailureCountc=new float[CpuParticlesSize];
      MccAdmissibilityFailureCountc=new float[CpuParticlesSize];
      MccFallbackUsedc=new float[CpuParticlesSize];
      MccSubstepTriggerReasonc=new float[CpuParticlesSize];
      MccLineSearchBacktrackCountc=new float[CpuParticlesSize];
      MccLineSearchRejectReasonc=new float[CpuParticlesSize];
      MccLineSearchMinAlphac=new float[CpuParticlesSize];
      MemCpuParticles+=sizeof(float)*17*CpuParticlesSize;
    }
    catch(const std::bad_alloc){
      Run_Exceptioon("Could not allocate the requested MCC state memory.");
    }
  }
  //=====
  if(HydromechCoupling || SavePorePressure){
    PorePressc=ArraysCpu->ReserveDouble();
    PorePressRatec=ArraysCpu->ReserveFloat();
    DivVelc=ArraysCpu->ReserveFloat();
    LapPorePressc=ArraysCpu->ReserveFloat();
    LapZc=ArraysCpu->ReserveFloat();
    DivVelCorrc=ArraysCpu->ReserveFloat();
    LapPorePressCorrc=ArraysCpu->ReserveFloat();
    LapZCorrc=ArraysCpu->ReserveFloat();
    PorePressureAcec=ArraysCpu->ReserveFloat3();
    PorePressureAceDiffc=ArraysCpu->ReserveFloat3();
    PorePressureFeedbackUsedAcec=ArraysCpu->ReserveFloat3();
  }
  if(PorePressureBoundaryGhost){
    PorePressGhostc=ArraysCpu->ReserveDouble();
    ExcessPorePressGhostc=ArraysCpu->ReserveDouble();
    PorePressureBoundaryModec=ArraysCpu->ReserveFloat();
    LapPorePressGhostc=ArraysCpu->ReserveFloat();
    LapZGhostc=ArraysCpu->ReserveFloat();
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
  ,unsigned *idp,tdouble3 *pos,tfloat3 *vel,float *rhop,tfloat3 *sigmakk,tfloat3 *sigmaij,float *kplastic,typecode *code,double *porepress,float *porepressrate,float *divvel,float *lapporepress,float *lapz,tfloat3 *porepressureace,tfloat3 *porepressureacediff,double *porepressghost,double *excessporepressghost,float *porepressureboundarymode,float *lapporepressghost,float *lapzghost,float *divvelcorr,float *lapporepresscorr,float *lapzcorr,float *mccpc,float *mccvoidratio,float *mccplasticvolstrain,float *mcceqplasticstrain,float *mccyieldflag,float *mccplasticmultiplier,float *mccreturnstatus,float *mccreturniterations,float *mccyieldresidual,float *mccsubstepcount,float *mccsubstepfailurecount,float *mccadmissibilityfailurecount,float *mccfallbackused,float *mccsubsteptriggerreason,float *mcclinesearchbacktrackcount,float *mcclinesearchrejectreason,float *mcclinesearchminalpha)
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
  if(porepressureace){
      for (unsigned p=0;p<n;p++)porepressureace[p]=PorePressureAcec[p+pini];
  }
  if(porepressureacediff){
      for (unsigned p=0;p<n;p++)porepressureacediff[p]=PorePressureAceDiffc[p+pini];
  }
  if(porepressghost){
      for (unsigned p=0;p<n;p++)porepressghost[p]=PorePressGhostc[p+pini];
  }
  if(excessporepressghost){
      for (unsigned p=0;p<n;p++)excessporepressghost[p]=ExcessPorePressGhostc[p+pini];
  }
  if(porepressureboundarymode){
      for (unsigned p=0;p<n;p++)porepressureboundarymode[p]=PorePressureBoundaryModec[p+pini];
  }
  if(lapporepressghost){
      for (unsigned p=0;p<n;p++)lapporepressghost[p]=LapPorePressGhostc[p+pini];
  }
  if(lapzghost){
      for (unsigned p=0;p<n;p++)lapzghost[p]=LapZGhostc[p+pini];
  }
  if(divvelcorr){
      for (unsigned p=0;p<n;p++)divvelcorr[p]=DivVelCorrc[p+pini];
  }
  if(lapporepresscorr){
      for (unsigned p=0;p<n;p++)lapporepresscorr[p]=LapPorePressCorrc[p+pini];
  }
  if(lapzcorr){
      for (unsigned p=0;p<n;p++)lapzcorr[p]=LapZCorrc[p+pini];
  }
  if(mccpc){
      for (unsigned p=0;p<n;p++)mccpc[p]=MccPcc[p+pini];
  }
  if(mccvoidratio){
      for (unsigned p=0;p<n;p++)mccvoidratio[p]=MccVoidRatioc[p+pini];
  }
  if(mccplasticvolstrain){
      for (unsigned p=0;p<n;p++)mccplasticvolstrain[p]=MccPlasticVolStrainc[p+pini];
  }
  if(mcceqplasticstrain){
      for (unsigned p=0;p<n;p++)mcceqplasticstrain[p]=MccEqPlasticStrainc[p+pini];
  }
  if(mccyieldflag){
      for (unsigned p=0;p<n;p++)mccyieldflag[p]=MccYieldFlagc[p+pini];
  }
  if(mccplasticmultiplier){
      for (unsigned p=0;p<n;p++)mccplasticmultiplier[p]=MccPlasticMultiplierc[p+pini];
  }
  if(mccreturnstatus){
      for (unsigned p=0;p<n;p++)mccreturnstatus[p]=MccReturnStatusc[p+pini];
  }
  if(mccreturniterations){
      for (unsigned p=0;p<n;p++)mccreturniterations[p]=MccReturnIterationsc[p+pini];
  }
  if(mccyieldresidual){
      for (unsigned p=0;p<n;p++)mccyieldresidual[p]=MccYieldResidualc[p+pini];
  }
  if(mccsubstepcount){
      for (unsigned p=0;p<n;p++)mccsubstepcount[p]=MccSubstepCountc[p+pini];
  }
  if(mccsubstepfailurecount){
      for (unsigned p=0;p<n;p++)mccsubstepfailurecount[p]=MccSubstepFailureCountc[p+pini];
  }
  if(mccadmissibilityfailurecount){
      for (unsigned p=0;p<n;p++)mccadmissibilityfailurecount[p]=MccAdmissibilityFailureCountc[p+pini];
  }
  if(mccfallbackused){
      for (unsigned p=0;p<n;p++)mccfallbackused[p]=MccFallbackUsedc[p+pini];
  }
  if(mccsubsteptriggerreason){
      for (unsigned p=0;p<n;p++)mccsubsteptriggerreason[p]=MccSubstepTriggerReasonc[p+pini];
  }
  if(mcclinesearchbacktrackcount){
      for (unsigned p=0;p<n;p++)mcclinesearchbacktrackcount[p]=MccLineSearchBacktrackCountc[p+pini];
  }
  if(mcclinesearchrejectreason){
      for (unsigned p=0;p<n;p++)mcclinesearchrejectreason[p]=MccLineSearchRejectReasonc[p+pini];
  }
  if(mcclinesearchminalpha){
      for (unsigned p=0;p<n;p++)mcclinesearchminalpha[p]=MccLineSearchMinAlphac[p+pini];
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
        if(porepressureace)porepressureace[pdel]=porepressureace[p];
        if(porepressureacediff)porepressureacediff[pdel]=porepressureacediff[p];
        if(porepressghost)porepressghost[pdel]=porepressghost[p];
        if(excessporepressghost)excessporepressghost[pdel]=excessporepressghost[p];
        if(porepressureboundarymode)porepressureboundarymode[pdel]=porepressureboundarymode[p];
        if(lapporepressghost)lapporepressghost[pdel]=lapporepressghost[p];
        if(lapzghost)lapzghost[pdel]=lapzghost[p];
        if(divvelcorr)divvelcorr[pdel]=divvelcorr[p];
        if(lapporepresscorr)lapporepresscorr[pdel]=lapporepresscorr[p];
        if(lapzcorr)lapzcorr[pdel]=lapzcorr[p];
        if(mccpc)mccpc[pdel]=mccpc[p];
        if(mccvoidratio)mccvoidratio[pdel]=mccvoidratio[p];
        if(mccplasticvolstrain)mccplasticvolstrain[pdel]=mccplasticvolstrain[p];
        if(mcceqplasticstrain)mcceqplasticstrain[pdel]=mcceqplasticstrain[p];
        if(mccyieldflag)mccyieldflag[pdel]=mccyieldflag[p];
        if(mccplasticmultiplier)mccplasticmultiplier[pdel]=mccplasticmultiplier[p];
        if(mccreturnstatus)mccreturnstatus[pdel]=mccreturnstatus[p];
        if(mccreturniterations)mccreturniterations[pdel]=mccreturniterations[p];
        if(mccyieldresidual)mccyieldresidual[pdel]=mccyieldresidual[p];
        if(mccsubstepcount)mccsubstepcount[pdel]=mccsubstepcount[p];
        if(mccsubstepfailurecount)mccsubstepfailurecount[pdel]=mccsubstepfailurecount[p];
        if(mccadmissibilityfailurecount)mccadmissibilityfailurecount[pdel]=mccadmissibilityfailurecount[p];
        if(mccfallbackused)mccfallbackused[pdel]=mccfallbackused[p];
        if(mccsubsteptriggerreason)mccsubsteptriggerreason[pdel]=mccsubsteptriggerreason[p];
        if(mcclinesearchbacktrackcount)mcclinesearchbacktrackcount[pdel]=mcclinesearchbacktrackcount[p];
        if(mcclinesearchrejectreason)mcclinesearchrejectreason[pdel]=mcclinesearchrejectreason[p];
        if(mcclinesearchminalpha)mcclinesearchminalpha[pdel]=mcclinesearchminalpha[p];
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
  const float porosity0=SoilCte.Porosity0;
  const float hydraulicconductivity=SoilCte.HydraulicConductivity;
  const float waterbulkmodulus=SoilCte.WaterBulkModulus;
  const float waterdensity=SoilCte.WaterDensity;
  if(hydraulicconductivity>0.f && waterbulkmodulus>0.f && waterdensity>0.f && porosity0>0.f && porosity0<1.f && PorePressureDtSafety>0.f){
    const double gmag=GetHydraulicGmag();
    if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for pore-pressure timestep restriction.");
    const double cw=double(waterdensity)*gmag*double(porosity0)/double(waterbulkmodulus);
    dtpore=double(PorePressureDtSafety)*cw*double(KernelH)*double(KernelH)/double(hydraulicconductivity);
    if(dtpore<=0. || fun::IsNAN(dtpore) || fun::IsInfinity(dtpore))Run_Exceptioon(fun::PrintStr("The computed pore-pressure timestep is invalid (dt_pore=%g).",dtpore));
    dtporeactive=true;
    if(!PorePressureDtConfigPrint){
      Log->Printf("Pore-pressure timestep restriction: active=True, Cw=%g, dt_pore=%g, safety=%g, h(KernelH)=%g, hydraulic_gmag=%g.",cw,dtpore,PorePressureDtSafety,KernelH,gmag);
      if(FixedDt)Log->PrintWarning(fun::PrintStr("Fixed dt is enabled. Fixed dt should be <= dt_pore=%g for PR pore-pressure update.",dtpore));
      PorePressureDtConfigPrint=true;
      PorePressureDtFixedPrint=(FixedDt!=NULL);
    }
  }
  else if(hydraulicconductivity==0.f){
    if(!PorePressureDtConfigPrint){
      Log->Print("Pore-pressure timestep restriction: active=False, disabled because HydraulicConductivity=0.");
      PorePressureDtConfigPrint=true;
    }
  }
  else if(hydraulicconductivity>0.f)Run_Exceptioon("Invalid hydromechanical parameters for pore-pressure timestep restriction.");
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
  if(PorePressureAcec)memset(PorePressureAcec,0,sizeof(tfloat3)*np);  //PorePressureAcec[]=(0,0,0)
  if(PorePressureAceDiffc)memset(PorePressureAceDiffc,0,sizeof(tfloat3)*np); //PorePressureAceDiffc[]=(0,0,0)
  if(PorePressGhostc)memset(PorePressGhostc,0,sizeof(double)*np); //PorePressGhostc[]=0
  if(ExcessPorePressGhostc)memset(ExcessPorePressGhostc,0,sizeof(double)*np); //ExcessPorePressGhostc[]=0
  if(PorePressureBoundaryModec)memset(PorePressureBoundaryModec,0,sizeof(float)*np); //PorePressureBoundaryModec[]=0
  if(LapPorePressGhostc)memset(LapPorePressGhostc,0,sizeof(float)*np); //LapPorePressGhostc[]=0
  if(LapZGhostc)memset(LapZGhostc,0,sizeof(float)*np); //LapZGhostc[]=0
  if(DivVelCorrc)memset(DivVelCorrc,0,sizeof(float)*np); //DivVelCorrc[]=0
  if(LapPorePressCorrc)memset(LapPorePressCorrc,0,sizeof(float)*np); //LapPorePressCorrc[]=0
  if(LapZCorrc)memset(LapZCorrc,0,sizeof(float)*np); //LapZCorrc[]=0
  if(SpsGradvelc)memset(SpsGradvelc+npb,0,sizeof(tsymatrix3f)*npf);  //SpsGradvelc[]=(0,0,0,0,0,0).
  //====== mdbr
  memset(Rsigmac,0,sizeof(tsymatrix3f)*np);
  //======
  //-Select particles for shifting.
  if(ShiftPosfsc)Shifting->InitCpu(npf,npb,Posc,ShiftPosfsc);

  //-Adds variable acceleration from input configuration.
  if(AccInput)AccInput->RunCpu(TimeStep,Gravity,npf,npb,Codec,Posc,Velrhopc,Acec);
  if(IsMechanicalGravityStopped(TimeStep) && !BodyGravityStoppedLogged){
    Log->Print(fun::PrintStr("Mechanical body gravity stopped at TimeStep=%g. Hydraulic gravity remains active.",TimeStep));
    BodyGravityStoppedLogged=true;
  }

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
  const double confp0d=(!boundp2? GetFlexibleConfiningStressP0(TimeStep): 0.);
  const bool useconf=(confp0d>0.);
  const bool conflateralactive=(ConfiningStressUseLateralSelector && (ConfiningStressLateralSelectorStartTime<=0. || TimeStep>=ConfiningStressLateralSelectorStartTime));
  const bool conffi=(useconf && (FlexibleConfiningStressFiDiagnostic || ConfiningStressUseFiSelector || SaveConfiningStressDiagnostics));
  const bool confgeom=(useconf && (ConfiningStressGeometry==1 || ConfiningStressUseLateralSelector || SaveConfiningStressDiagnostics));
  const float confp0=float(confp0d);
  struct StConfDiagThread{
    double netx,nety,netz,absforce,maxaccel,count;
    double legacycount,ficount,fiselcount,fisum,fimin,fimax;
    double classinterior,classlateral,classtop,classbottom,classedge,classoutside;
    double latfiseld,capfiseld,latrsum,latrmax,latrcount,capasum,capamax,capacount;
    double gradcorrected,gradfallback,graddetmin,graddetmax;
  };
  vector<StConfDiagThread> confth(OMP_MAXTHREADS);
  for(int th=0;th<OmpThreads;th++){
    StConfDiagThread &ct=confth[th];
    ct.netx=ct.nety=ct.netz=ct.absforce=ct.maxaccel=ct.count=0.;
    ct.legacycount=ct.ficount=ct.fiselcount=ct.fisum=0.;
    ct.fimin=DBL_MAX; ct.fimax=-DBL_MAX;
    ct.classinterior=ct.classlateral=ct.classtop=ct.classbottom=ct.classedge=ct.classoutside=0.;
    ct.latfiseld=ct.capfiseld=0.;
    ct.latrsum=ct.latrmax=ct.latrcount=0.;
    ct.capasum=ct.capamax=ct.capacount=0.;
    ct.gradcorrected=ct.gradfallback=0.;
    ct.graddetmin=DBL_MAX; ct.graddetmax=-DBL_MAX;
  }
  const bool useplatenreact=(SavePlatenReactionDiagnostics && boundp2 && PlatenReactionMode==0);
  struct StPlatenReactionThread{
    double topx,topy,topz,bottomx,bottomy,bottomz;
    unsigned long long toppairs,bottompairs;
  };
  vector<StPlatenReactionThread> platenreactth(OMP_MAXTHREADS);
  if(useplatenreact){
    ResetPlatenReactionDiagnostics();
    for(unsigned p=0;p<pinit;p++){
      const typecode c=code[p];
      if(CODE_IsNormal(c) && !CODE_IsFluid(c)){
        int mk=int(CODE_GetTypeValue(c));
        if(MkInfo){
          const unsigned cmk=MkInfo->GetMkBlockByCode(c);
          if(cmk<MkInfo->Size())mk=int(MkInfo->Mkblock(cmk)->MkType);
        }
        const bool istop=(mk==PlatenTopMkBound);
        const bool isbottom=(mk==PlatenBottomMkBound);
        if(istop)PlatenReactionDiagTopCount++;
        else if(isbottom)PlatenReactionDiagBottomCount++;
      }
    }
    for(int th=0;th<OmpThreads;th++){
      StPlatenReactionThread &pt=platenreactth[th];
      pt.topx=pt.topy=pt.topz=pt.bottomx=pt.bottomy=pt.bottomz=0.;
      pt.toppairs=pt.bottompairs=0;
    }
  }
  //-Initialise execution with OpenMP. | Inicia ejecucion con OpenMP.
  const int pfin=int(pinit+n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided)
  #endif
  for(int p1=int(pinit);p1<pfin;p1++){
    float visc=0,arp1=0,deltap1=0;
    tfloat3 acep1=TFloat3(0);
    tfloat3 confacep1=TFloat3(0);
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
    const bool conftargetp1=(useconf && !ftp1 && IsFlexibleConfiningStressTarget(code[p1]));

    //-Obtain data of particle p1.
    const tdouble3 posp1=pos[p1];
    const tfloat3 velp1=TFloat3(velrhop[p1].x,velrhop[p1].y,velrhop[p1].z);
    const float rhopp1=velrhop[p1].w;
    const float pressp1=press[p1];
    const tsymatrix3f sigmap1=sigma[p1]; //mdbr
    tsymatrix3f artstressp1={0,0,0,0,0,0};
    if(useartstress && !ftp1 && invwabdp>0.f)artstressp1=artificialstress[p1];
    double conffip1=0.;
    int confclassp1=0;
    if(conftargetp1 && (conffi || ConfiningStressUseFiSelector)){
      conffip1=double(MassFluid)/double(rhopp1)*double(fsph::GetKernel_Wab<tker>(CSP,0.f));
      const StNgSearch ngsfi=nsearch::Init(dcell[p1],false,divdata);
      for(int z=ngsfi.zini;z<ngsfi.zfin;z++)for(int y=ngsfi.yini;y<ngsfi.yfin;y++){
        const tuint2 pif=nsearch::ParticleRange(y,z,ngsfi,divdata);
        for(unsigned p2=pif.x;p2<pif.y;p2++)if(p2!=unsigned(p1) && IsFlexibleConfiningStressTarget(code[p2])){
          const float drx=float(posp1.x-pos[p2].x);
          const float dry=float(posp1.y-pos[p2].y);
          const float drz=float(posp1.z-pos[p2].z);
          const float rr2=drx*drx+dry*dry+drz*drz;
          if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
            const double wab=double(fsph::GetKernel_Wab<tker>(CSP,rr2));
            conffip1+=double(MassFluid)/double(velrhop[p2].w)*wab;
          }
        }
      }
    }
    if(conftargetp1 && confgeom)confclassp1=GetConfiningStressCylinderClass(posp1);
    const bool conffiselp1=(!ConfiningStressUseFiSelector || conffip1<=ConfiningStressFiThreshold);
    const bool conflatselp1=(!conflateralactive || confclassp1==2);
    const bool confactivep1=(conftargetp1 && conffiselp1 && conflatselp1);
    const bool rsymp1=(Symmetry && posp1.y<=KernelSize); //<vs_syymmetry>
    bool confgradcorrp1=false;
    double confgraddetp1=0.;
    tmatrix3d confgradinvp1=TMatrix3d(0);
    if(confactivep1 && ConfiningStressGradientMode==1){
      const bool sim2d=Simulate2D;
      const unsigned minneigh=(sim2d? 6u: 12u);
      const double detlimit=(sim2d? 1e-6: 1e-8);
      tmatrix3d lcorr=TMatrix3d(0);
      unsigned nneigh=0;
      const StNgSearch ngscg=nsearch::Init(dcell[p1],false,divdata);
      for(int z=ngscg.zini;z<ngscg.zfin;z++)for(int y=ngscg.yini;y<ngscg.yfin;y++){
        const tuint2 pif=nsearch::ParticleRange(y,z,ngscg,divdata);
        bool rsym=false; //<vs_syymmetry>
        for(unsigned p2=pif.x;p2<pif.y;p2++){
          if(p2==unsigned(p1) || !IsFlexibleConfiningStressTarget(code[p2])){ rsym=false; continue; }
          const float drx=float(posp1.x-pos[p2].x);
                float dry=float(posp1.y-pos[p2].y);
          if(rsym)dry=float(posp1.y+pos[p2].y); //<vs_syymmetry>
          const float drz=float(posp1.z-pos[p2].z);
          const float rr2=drx*drx+dry*dry+drz*drz;
          if(rr2<=KernelSize2 && rr2>=ALMOSTZERO && velrhop[p2].w>0.f){
            const float fac=fsph::GetKernel_Fac<tker>(CSP,rr2);
            const double frx=double(fac*drx);
            const double fry=double(fac*dry);
            const double frz=double(fac*drz);
            const double vol2=double(MassFluid)/double(velrhop[p2].w);
            lcorr.a11+=-double(drx)*frx*vol2; lcorr.a12+=-double(drx)*fry*vol2; lcorr.a13+=-double(drx)*frz*vol2;
            lcorr.a21+=-double(dry)*frx*vol2; lcorr.a22+=-double(dry)*fry*vol2; lcorr.a23+=-double(dry)*frz*vol2;
            lcorr.a31+=-double(drz)*frx*vol2; lcorr.a32+=-double(drz)*fry*vol2; lcorr.a33+=-double(drz)*frz*vol2;
            nneigh++;
            rsym=(rsymp1 && !rsym && float(posp1.y-dry)<=KernelSize); //<vs_syymmetry>
            if(rsym)p2--;                                             //<vs_syymmetry>
          }
          else rsym=false;                                            //<vs_syymmetry>
        }
      }
      if(nneigh>=minneigh){
        if(sim2d){
          const double a=lcorr.a11,b=lcorr.a13,c=lcorr.a31,d=lcorr.a33;
          confgraddetp1=a*d-b*c;
          if(fabs(confgraddetp1)>=detlimit){
            confgradinvp1.a11= d/confgraddetp1; confgradinvp1.a13=-b/confgraddetp1;
            confgradinvp1.a31=-c/confgraddetp1; confgradinvp1.a33= a/confgraddetp1;
            confgradcorrp1=(confgradinvp1.a11==confgradinvp1.a11 && confgradinvp1.a13==confgradinvp1.a13
              && confgradinvp1.a31==confgradinvp1.a31 && confgradinvp1.a33==confgradinvp1.a33);
          }
        }
        else{
          confgraddetp1=fmath::Determinant3x3(lcorr);
          if(fabs(confgraddetp1)>=detlimit){
            confgradinvp1=fmath::InverseMatrix3x3(lcorr,confgraddetp1);
            confgradcorrp1=(confgradinvp1.a11==confgradinvp1.a11 && confgradinvp1.a12==confgradinvp1.a12 && confgradinvp1.a13==confgradinvp1.a13
              && confgradinvp1.a21==confgradinvp1.a21 && confgradinvp1.a22==confgradinvp1.a22 && confgradinvp1.a23==confgradinvp1.a23
              && confgradinvp1.a31==confgradinvp1.a31 && confgradinvp1.a32==confgradinvp1.a32 && confgradinvp1.a33==confgradinvp1.a33);
          }
        }
      }
    }
    //-Obtains elastic parameters
    float modulus_K=SoilCte.ModulusK;
    float modulus_G=SoilCte.ModulusG;
    float phi=SoilCte.phi;
    const tsymatrix3f taup1=(tvisco==VISCO_Artificial? gradvelp1: tau[p1]);

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
          int platenreactclass=0;
          if(useplatenreact && !ftp1 && CODE_IsNormal(code[p2]) && !CODE_IsFluid(code[p2])){
            int mk=int(CODE_GetTypeValue(code[p2]));
            if(MkInfo){
              const unsigned cmk=MkInfo->GetMkBlockByCode(code[p2]);
              if(cmk<MkInfo->Size())mk=int(MkInfo->Mkblock(cmk)->MkType);
            }
            if(mk==PlatenTopMkBound)platenreactclass=1;
            else if(mk==PlatenBottomMkBound)platenreactclass=2;
          }
          tfloat3 platenpairace=TFloat3(0);

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
            const tfloat3 acestress=TFloat3(prsxx*frx+prsxy*fry+prsxz*frz,prsyy*fry+prsxy*frx+prsyz*frz,prszz*frz+prsyz*fry+prsxz*frx);
			acep1.x += acestress.x; acep1.y += acestress.y; acep1.z += acestress.z;//form 1
            if(platenreactclass){
              platenpairace.x+=acestress.x; platenpairace.y+=acestress.y; platenpairace.z+=acestress.z;
            }
            if(confactivep1 && !ftp2 && IsFlexibleConfiningStressTarget(code[p2])){
              const float prsconf=massp2*(confp0+confp0)/(rhopp1*velrhop2.w);
              float frxconf=frx,fryconf=fry,frzconf=frz;
              if(ConfiningStressGradientMode==1 && confgradcorrp1){
                if(Simulate2D){
                  frxconf=float(confgradinvp1.a11*double(frx)+confgradinvp1.a13*double(frz));
                  fryconf=0.f;
                  frzconf=float(confgradinvp1.a31*double(frx)+confgradinvp1.a33*double(frz));
                }
                else{
                  frxconf=float(confgradinvp1.a11*double(frx)+confgradinvp1.a12*double(fry)+confgradinvp1.a13*double(frz));
                  fryconf=float(confgradinvp1.a21*double(frx)+confgradinvp1.a22*double(fry)+confgradinvp1.a23*double(frz));
                  frzconf=float(confgradinvp1.a31*double(frx)+confgradinvp1.a32*double(fry)+confgradinvp1.a33*double(frz));
                }
              }
              const tfloat3 aceconf=TFloat3(prsconf*frxconf,prsconf*fryconf,prsconf*frzconf);
              acep1.x+=aceconf.x; acep1.y+=aceconf.y; acep1.z+=aceconf.z;
              confacep1.x+=aceconf.x; confacep1.y+=aceconf.y; confacep1.z+=aceconf.z;
            }
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
                const tfloat3 acevisc=TFloat3(-pi_visc*frx,-pi_visc*fry,-pi_visc*frz);
                acep1.x+=acevisc.x; acep1.y+=acevisc.y; acep1.z+=acevisc.z;
                if(platenreactclass){
                  platenpairace.x+=acevisc.x; platenpairace.y+=acevisc.y; platenpairace.z+=acevisc.z;
                }
              }
            }
            else if(tvisco==VISCO_LaminarSPS){//-Laminar+SPS viscosity. 
              {//-Laminar contribution.
                const float robar2=(rhopp1+velrhop2.w);
                const float temp=4.f*visco/((rr2+Eta2)*robar2);  //-Simplification of: temp=2.0f*visco/((rr2+CTE.eta2)*robar); robar=(rhopp1+velrhop2.w)*0.5f;
                const float vtemp=massp2*temp*(drx*frx+dry*fry+drz*frz);  
                const tfloat3 acevisc=TFloat3(vtemp*dvx,vtemp*dvy,vtemp*dvz);
                acep1.x+=acevisc.x; acep1.y+=acevisc.y; acep1.z+=acevisc.z;
                if(platenreactclass){
                  platenpairace.x+=acevisc.x; platenpairace.y+=acevisc.y; platenpairace.z+=acevisc.z;
                }
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
            if(platenreactclass && (platenpairace.x || platenpairace.y || platenpairace.z)){
              StPlatenReactionThread &pt=platenreactth[omp_get_thread_num()];
              const double fx=-double(MassFluid)*double(platenpairace.x);
              const double fy=-double(MassFluid)*double(platenpairace.y);
              const double fz=-double(MassFluid)*double(platenpairace.z);
              if(platenreactclass==1){
                pt.topx+=fx; pt.topy+=fy; pt.topz+=fz; pt.toppairs++;
              }
              else{
                pt.bottomx+=fx; pt.bottomy+=fy; pt.bottomz+=fz; pt.bottompairs++;
              }
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
    if(conftargetp1){
      const int th=omp_get_thread_num();
      StConfDiagThread &ct=confth[th];
      ct.legacycount+=1.;
      if(conffi || ConfiningStressUseFiSelector){
        ct.ficount+=1.;
        ct.fisum+=conffip1;
        if(ct.fimin>conffip1)ct.fimin=conffip1;
        if(ct.fimax<conffip1)ct.fimax=conffip1;
        if(conffip1<=ConfiningStressFiThreshold){
          ct.fiselcount+=1.;
          ct.latfiseld+=(confclassp1==2? 1.: 0.);
          ct.capfiseld+=(confclassp1==3 || confclassp1==4 || confclassp1==5? 1.: 0.);
        }
      }
      if(confgeom){
        switch(confclassp1){
          case 1: ct.classinterior+=1.; break;
          case 2: ct.classlateral+=1.; break;
          case 3: ct.classtop+=1.; break;
          case 4: ct.classbottom+=1.; break;
          case 5: ct.classedge+=1.; break;
          case 6: ct.classoutside+=1.; break;
        }
      }
      const double ax=confacep1.x, ay=confacep1.y, az=confacep1.z;
      const double amag=sqrt(ax*ax+ay*ay+az*az);
      if(confactivep1 && confgeom && (confclassp1==2 || confclassp1==3 || confclassp1==4 || confclassp1==5)){
        const double dx=posp1.x-ConfiningStressCylinderCenter.x;
        const double dy=posp1.y-ConfiningStressCylinderCenter.y;
        const double dz=posp1.z-ConfiningStressCylinderCenter.z;
        const double s=dx*ConfiningStressCylinderAxis.x+dy*ConfiningStressCylinderAxis.y+dz*ConfiningStressCylinderAxis.z;
        const double rx=dx-s*ConfiningStressCylinderAxis.x;
        const double ry=dy-s*ConfiningStressCylinderAxis.y;
        const double rz=dz-s*ConfiningStressCylinderAxis.z;
        const double rn=sqrt(rx*rx+ry*ry+rz*rz);
        if(confclassp1==2 && rn>0.){
          const double arad=-(ax*rx+ay*ry+az*rz)/rn;
          ct.latrsum+=arad;
          if(ct.latrmax<arad)ct.latrmax=arad;
          ct.latrcount+=1.;
        }
        if(confclassp1==3 || confclassp1==4 || confclassp1==5){
          const double aax=fabs(ax*ConfiningStressCylinderAxis.x+ay*ConfiningStressCylinderAxis.y+az*ConfiningStressCylinderAxis.z);
          ct.capasum+=aax;
          if(ct.capamax<aax)ct.capamax=aax;
          ct.capacount+=1.;
        }
      }
      if(confactivep1){
        if(ConfiningStressGradientMode==1){
          if(confgradcorrp1)ct.gradcorrected+=1.;
          else ct.gradfallback+=1.;
          if(ct.graddetmin>confgraddetp1)ct.graddetmin=confgraddetp1;
          if(ct.graddetmax<confgraddetp1)ct.graddetmax=confgraddetp1;
        }
        ct.netx+=double(MassFluid)*ax;
        ct.nety+=double(MassFluid)*ay;
        ct.netz+=double(MassFluid)*az;
        ct.absforce+=double(MassFluid)*amag;
        if(ct.maxaccel<amag)ct.maxaccel=amag;
        ct.count+=1.;
      }
    }
  }
  //-Keep max value in viscdt. | Guarda en viscdt el valor maximo.
  for(int th=0;th<OmpThreads;th++)if(viscdt<viscth[th*OMP_STRIDE])viscdt=viscth[th*OMP_STRIDE];
  if(useconf){
    double netx=0.,nety=0.,netz=0.,absforce=0.,maxaccel=0.,count=0.,legacycount=0.;
    double ficount=0.,fiselcount=0.,fisum=0.,fimin=DBL_MAX,fimax=-DBL_MAX;
    double classinterior=0.,classlateral=0.,classtop=0.,classbottom=0.,classedge=0.,classoutside=0.;
    double latfiseld=0.,capfiseld=0.,latrsum=0.,latrmax=0.,latrcount=0.,capasum=0.,capamax=0.,capacount=0.;
    double gradcorrected=0.,gradfallback=0.,graddetmin=DBL_MAX,graddetmax=-DBL_MAX;
    for(int th=0;th<OmpThreads;th++){
      const StConfDiagThread &ct=confth[th];
      netx+=ct.netx; nety+=ct.nety; netz+=ct.netz;
      absforce+=ct.absforce; count+=ct.count;
      if(maxaccel<ct.maxaccel)maxaccel=ct.maxaccel;
      legacycount+=ct.legacycount;
      ficount+=ct.ficount; fiselcount+=ct.fiselcount; fisum+=ct.fisum;
      if(fimin>ct.fimin)fimin=ct.fimin;
      if(fimax<ct.fimax)fimax=ct.fimax;
      classinterior+=ct.classinterior; classlateral+=ct.classlateral; classtop+=ct.classtop;
      classbottom+=ct.classbottom; classedge+=ct.classedge; classoutside+=ct.classoutside;
      latfiseld+=ct.latfiseld; capfiseld+=ct.capfiseld;
      latrsum+=ct.latrsum; latrcount+=ct.latrcount;
      if(latrmax<ct.latrmax)latrmax=ct.latrmax;
      capasum+=ct.capasum; capacount+=ct.capacount;
      if(capamax<ct.capamax)capamax=ct.capamax;
      gradcorrected+=ct.gradcorrected; gradfallback+=ct.gradfallback;
      if(graddetmin>ct.graddetmin)graddetmin=ct.graddetmin;
      if(graddetmax<ct.graddetmax)graddetmax=ct.graddetmax;
    }
    const double netmag=sqrt(netx*netx+nety*nety+netz*netz);
    ConfiningStressDiagP0Eff=confp0d;
    ConfiningStressDiagTargetCount=unsigned(count);
    ConfiningStressDiagLegacyTargetCount=unsigned(legacycount);
    ConfiningStressDiagFiSelectedCount=unsigned(fiselcount);
    ConfiningStressDiagClassInteriorCount=unsigned(classinterior);
    ConfiningStressDiagClassLateralCount=unsigned(classlateral);
    ConfiningStressDiagClassTopCount=unsigned(classtop);
    ConfiningStressDiagClassBottomCount=unsigned(classbottom);
    ConfiningStressDiagClassEdgeCount=unsigned(classedge);
    ConfiningStressDiagClassOutsideCount=unsigned(classoutside);
    ConfiningStressDiagLateralFiSelectedCount=unsigned(latfiseld);
    ConfiningStressDiagCapFiSelectedCount=unsigned(capfiseld);
    ConfiningStressDiagFiMin=(ficount>0.? fimin: 0.);
    ConfiningStressDiagFiMax=(ficount>0.? fimax: 0.);
    ConfiningStressDiagFiMean=(ficount>0.? fisum/ficount: 0.);
    ConfiningStressDiagLateralRadialAccelMean=(latrcount>0.? latrsum/latrcount: 0.);
    ConfiningStressDiagLateralRadialAccelMax=latrmax;
    ConfiningStressDiagCapAxialAccelMean=(capacount>0.? capasum/capacount: 0.);
    ConfiningStressDiagCapAxialAccelMax=capamax;
    ConfiningStressDiagNetForce=TDouble3(netx,nety,netz);
    ConfiningStressDiagTotalAbsForce=absforce;
    ConfiningStressDiagMaxAccel=maxaccel;
    ConfiningStressDiagComAccel=(count>0.? netmag/(double(MassFluid)*count): 0.);
    ConfiningStressDiagSymResidual=(absforce>0.? netmag/absforce: 0.);
    ConfiningStressDiagGradCorrectedCount=unsigned(gradcorrected);
    ConfiningStressDiagGradFallbackCount=unsigned(gradfallback);
    ConfiningStressDiagGradDetMin=(graddetmin==DBL_MAX? 0.: graddetmin);
    ConfiningStressDiagGradDetMax=(graddetmax==-DBL_MAX? 0.: graddetmax);
  }
  if(useplatenreact){
    double topx=0.,topy=0.,topz=0.,bottomx=0.,bottomy=0.,bottomz=0.;
    unsigned long long toppairs=0,bottompairs=0;
    for(int th=0;th<OmpThreads;th++){
      const StPlatenReactionThread &pt=platenreactth[th];
      topx+=pt.topx; topy+=pt.topy; topz+=pt.topz;
      bottomx+=pt.bottomx; bottomy+=pt.bottomy; bottomz+=pt.bottomz;
      toppairs+=pt.toppairs; bottompairs+=pt.bottompairs;
    }
    PlatenReactionDiagTopPairs=toppairs;
    PlatenReactionDiagBottomPairs=bottompairs;
    PlatenReactionDiagTopForce=TDouble3(topx,topy,topz);
    PlatenReactionDiagBottomForce=TDouble3(bottomx,bottomy,bottomz);
    double ax=ConfiningStressCylinderAxis.x,ay=ConfiningStressCylinderAxis.y,az=ConfiningStressCylinderAxis.z;
    double an=sqrt(ax*ax+ay*ay+az*az);
    if(an<=0.){ ax=0.; ay=0.; az=1.; an=1.; }
    ax/=an; ay/=an; az/=an;
    const double area=PlatenReactionArea;
    if(area>0.){
      const double ftopaxis=topx*ax+topy*ay+topz*az;
      const double fbottomaxis=bottomx*ax+bottomy*ay+bottomz*az;
      PlatenReactionDiagTopAxialStress=ftopaxis/area;
      PlatenReactionDiagBottomAxialStress=-fbottomaxis/area;
    }
    const double ftopmag=sqrt(topx*topx+topy*topy+topz*topz);
    const double fbottommag=sqrt(bottomx*bottomx+bottomy*bottomy+bottomz*bottomz);
    const double fbalx=topx+bottomx,fbaly=topy+bottomy,fbalz=topz+bottomz;
    const double fbalsum=ftopmag+fbottommag;
    PlatenReactionDiagForceBalanceError=(fbalsum>0.? sqrt(fbalx*fbalx+fbaly*fbaly+fbalz*fbalz)/fbalsum: 0.);
  }
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
  if(FlexibleConfiningStress)ResetFlexibleConfiningStressDiagnostics();
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
  if(FlexibleConfiningStress)PrintFlexibleConfiningStressDiagnostics();
  if(t.npbok){
    //-Interaction Bound-Fluid.
    InteractionForcesBound<tker,ftmode> (t.npbok,0,t.divdata,t.dcell
      ,t.pos,t.velrhop,t.code,t.idp,viscdt,t.ar);
  }
  if(SavePlatenReactionDiagnostics)PrintPlatenReactionDiagnostics();
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
  const float porosity0=SoilCte.Porosity0;
  const float hydraulicconductivity=SoilCte.HydraulicConductivity;
  const float waterbulkmodulus=SoilCte.WaterBulkModulus;
  const float waterdensity=SoilCte.WaterDensity;
  if(porosity0<=0.f || porosity0>=1.f)Run_Exceptioon("Soil Porosity0 must be between 0 and 1 for PR pore-pressure-rate update.");
  if(waterbulkmodulus<=0.f)Run_Exceptioon("Soil WaterBulkModulus must be greater than zero for PR pore-pressure-rate update.");
  if(waterdensity<=0.f)Run_Exceptioon("Soil WaterDensity must be greater than zero for PR pore-pressure-rate update.");
  const double gmag=GetHydraulicGmag();
  if(hydraulicconductivity>0.f && gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero when soil HydraulicConductivity is enabled.");
  const unsigned np=pini+n;
  memset(porepressrate,0,sizeof(float)*np);
  const float factor=waterbulkmodulus/porosity0;
  const float difcoef=(hydraulicconductivity>0.f? float(double(hydraulicconductivity)/(double(waterdensity)*gmag)): 0.f);
  const float elevcoef=(HydraulicElevationSource? hydraulicconductivity: 0.f);
  const int nint=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(nint>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int cp=0;cp<nint;cp++){
    const unsigned p1=pini+unsigned(cp);
    // DivVelc stores the mathematical divergence of the skeleton velocity.
    // Compression gives DivVelc < 0, while pore-pressure generation is
    // compression-positive, so the volumetric PR contribution is -DivVelc.
    if(CODE_IsFluid(code[p1]))porepressrate[p1]=factor*(-divvel[p1]+difcoef*lapporepress[p1]+elevcoef*lapz[p1]);
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
/// Applies diagnostic material-surface drained clamp for curved boundary mode 2.
//==============================================================================
unsigned JSphCpu::ApplyPorePressureCurvedDrainedClamp(unsigned n,unsigned pini,const tdouble3 *pos,const typecode *code
  ,double *porepress,double timestep,const char *stage,bool printlog)
{
  if(!HydromechCoupling || PorePressureModel!=1 || PorePressureBoundaryOperator!=3 || !PorePressureCurvedDrained || CurvedDrainedBoundaryMode!=2 || !porepress)return(0);
  if(!pos || !code)Run_Exceptioon("Pointers without data for curved drained diagnostic clamp.");
  if(CurvedDrainedBoundaryRadius<=0.)
    Run_Exceptioon("CurvedDrainedBoundaryRadius must be greater than zero for CurvedDrainedBoundaryMode=2.");
  const double shellthick=(CurvedDrainedBoundaryThickness>0.? CurvedDrainedBoundaryThickness: double(KernelH));
  if(shellthick<=0.)Run_Exceptioon("CurvedDrainedBoundaryMode=2 requires positive CurvedDrainedBoundaryThickness or KernelH.");
  const double rtarget=CurvedDrainedBoundaryRadius;
  const double rmin=max(0.,rtarget-shellthick);
  unsigned affected=0,skipped=0,npmat=0;
  double beforemin=DBL_MAX,beforemax=-DBL_MAX,aftermin=DBL_MAX,aftermax=-DBL_MAX;
  double rselmin=DBL_MAX,rselmax=0.;
  for(unsigned p=pini;p<pini+n;p++)if(CODE_IsFluid(code[p])){
    npmat++;
    if(CurvedDrainedBoundaryTargetMk>=0 && int(CODE_GetTypeValue(code[p]))!=CurvedDrainedBoundaryTargetMk)continue;
    const tdouble3 rel=pos[p]-CurvedDrainedBoundaryCenter;
    const double r=sqrt(rel.x*rel.x+rel.y*rel.y+rel.z*rel.z);
    if(r<rmin || r<=ALMOSTZERO)continue;
    const double hydro=GetHydrostaticPorePressure(pos[p]);
    const double before=(CurvedDrainedBoundaryUseExcess? porepress[p]-hydro: porepress[p]);
    const double target=(CurvedDrainedBoundaryUseExcess? hydro+CurvedDrainedBoundaryValue: CurvedDrainedBoundaryValue);
    porepress[p]=target;
    const double after=(CurvedDrainedBoundaryUseExcess? porepress[p]-hydro: porepress[p]);
    beforemin=min(beforemin,before);
    beforemax=max(beforemax,before);
    aftermin=min(aftermin,after);
    aftermax=max(aftermax,after);
    rselmin=min(rselmin,r);
    rselmax=max(rselmax,r);
    affected++;
  }
  if(!npmat && printlog)Log->PrintWarning("Curved drained diagnostic clamp found no material particles.");
  if(!affected){
    skipped=npmat;
    beforemin=beforemax=aftermin=aftermax=0.;
    rselmin=0.;
  }
  if(printlog){
    Log->Printf("Curved drained diagnostic clamp: stage=%s, TimeStep=%g, mode=2, affected=%u, skipped=%u, radius_range=[%g,%g], value=%g Pa, value_type=%s, before=[%g,%g] Pa, after=[%g,%g] Pa."
      ,(stage? stage: "unknown"),timestep,affected,skipped,rselmin,rselmax,CurvedDrainedBoundaryValue
      ,(CurvedDrainedBoundaryUseExcess? "excess": "total"),beforemin,beforemax,aftermin,aftermax);
    Log->Print("Curved drained diagnostic clamp is not production: it directly overwrites material surface pressure to test the upper-bound effect of perfect surface drainage.");
  }
  return(affected);
}

//==============================================================================
/// Applies optional Shepard regularization to pore pressure on material particles.
//==============================================================================
template<TpKernel tker> unsigned JSphCpu::ApplyPorePressureShepardT(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code
  ,double *porepress,unsigned step,bool printlog)
{
  if(!HydromechCoupling || PorePressureModel!=1 || !PorePressureShepard || !PorePressureShepardInterval || !porepress)return(0);
  if(!pos || !velrhop || !code || !dcell)Run_Exceptioon("Pointers without data for pore-pressure Shepard regularization.");
  if(PorePressureShepardMode==1 && HydraulicElevationSource && GetHydraulicGmag()<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for excess pore-pressure Shepard regularization.");

  const unsigned np=pini+n;
  std::vector<double> preg(np,0.);
  std::vector<unsigned char> valid(np,0);

  unsigned npmat=0;
  double pwbeforemin=DBL_MAX,pwbeforemax=-DBL_MAX;
  double excessbeforemin=DBL_MAX,excessbeforemax=-DBL_MAX;
  const bool excessmode=(PorePressureShepardMode==1);
  for(unsigned p=pini;p<pini+n;p++)if(CODE_IsFluid(code[p])){
    npmat++;
    pwbeforemin=min(pwbeforemin,porepress[p]);
    pwbeforemax=max(pwbeforemax,porepress[p]);
    if(excessmode){
      const double hydro=GetHydrostaticPorePressure(pos[p]);
      const double excess=porepress[p]-hydro;
      excessbeforemin=min(excessbeforemin,excess);
      excessbeforemax=max(excessbeforemax,excess);
    }
  }
  if(!npmat){
    if(printlog)Log->PrintWarning("Pore-pressure Shepard regularization found no material particles.");
    return(0);
  }

  const int nint=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided) if(nint>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int cp=0;cp<nint;cp++){
    const unsigned p1=pini+unsigned(cp);
    if(!CODE_IsFluid(code[p1]))continue;
    const tdouble3 posp1=pos[p1];
    const bool rsymp1=(Symmetry && posp1.y<=KernelSize); //<vs_syymmetry>
    const double hydro1=GetHydrostaticPorePressure(posp1);
    const double pvalue1=(excessmode? porepress[p1]-hydro1: porepress[p1]);
    const double volp1=double(MassFluid)/double(velrhop[p1].w);
    double psum=volp1*pvalue1*double(fsph::GetKernel_Wab<tker>(CSP,0.f));
    double wsum=volp1*double(fsph::GetKernel_Wab<tker>(CSP,0.f));

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
          const float wab=fsph::GetKernel_Wab<tker>(CSP,rr2);
          const double volp2=double(MassFluid)/double(velrhop[p2].w);
          double pvalue=porepress[p2];
          if(excessmode){
            const double hydro2=GetHydrostaticPorePressure(pos[p2]);
            pvalue-=hydro2;
          }
          psum+=volp2*pvalue*double(wab);
          wsum+=volp2*double(wab);
          rsym=(rsymp1 && !rsym && float(posp1.y-dry)<=KernelSize); //<vs_syymmetry>
          if(rsym)p2--;                                             //<vs_syymmetry>
        }
        else rsym=false;                                            //<vs_syymmetry>
      }
    }
    if(wsum>ALMOSTZERO){
      const double pregvalue=psum/wsum;
      preg[p1]=(excessmode? hydro1+pregvalue: pregvalue);
      valid[p1]=1;
    }
  }

  unsigned affected=0,skipped=0;
  double pwaftermin=DBL_MAX,pwaftermax=-DBL_MAX;
  double excessaftermin=DBL_MAX,excessaftermax=-DBL_MAX;
  for(unsigned p=pini;p<pini+n;p++)if(CODE_IsFluid(code[p])){
    if(valid[p]){
      porepress[p]=preg[p];
      affected++;
    }
    else skipped++;
    pwaftermin=min(pwaftermin,porepress[p]);
    pwaftermax=max(pwaftermax,porepress[p]);
    if(excessmode){
      const double hydro=GetHydrostaticPorePressure(pos[p]);
      const double excess=porepress[p]-hydro;
      excessaftermin=min(excessaftermin,excess);
      excessaftermax=max(excessaftermax,excess);
    }
  }

  if(printlog){
    Log->Printf("Pore-pressure Shepard regularization applied on CPU: step=%u, TimeStep=%g, mode=%s, interval=%u, affected=%u/%u, skipped=%u, PorePress before=[%g,%g] Pa, after=[%g,%g] Pa."
      ,step,TimeStep,(excessmode? "ExcessPressure": "TotalPressure"),PorePressureShepardInterval,affected,npmat,skipped,pwbeforemin,pwbeforemax,pwaftermin,pwaftermax);
    if(excessmode)Log->Printf("Pore-pressure Shepard excess stats: before=[%g,%g] Pa, after=[%g,%g] Pa."
      ,excessbeforemin,excessbeforemax,excessaftermin,excessaftermax);
  }
  return(affected);
}

//==============================================================================
/// Applies optional Shepard regularization to pore pressure on material particles.
//==============================================================================
unsigned JSphCpu::ApplyPorePressureShepard(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code
  ,double *porepress,unsigned step,bool printlog)
{
       if(TKernel==KERNEL_Wendland)return(ApplyPorePressureShepardT<KERNEL_Wendland>(n,pini,divdata,dcell,pos,velrhop,code,porepress,step,printlog));
  else if(TKernel==KERNEL_Cubic)   return(ApplyPorePressureShepardT<KERNEL_Cubic   >(n,pini,divdata,dcell,pos,velrhop,code,porepress,step,printlog));
  return(0);
}

//==============================================================================
/// Applies a minimal top drained condition for excess pore pressure on material particles.
//==============================================================================
unsigned JSphCpu::ApplyPorePressureTopDrained(unsigned n,unsigned pini,const tdouble3 *pos,const typecode *code
  ,double *porepress,double timestep,const char *stage,bool printlog)
{
  if(!HydromechCoupling || PorePressureModel!=1 || !PorePressureTopDrained || !porepress)return(0);
  if(timestep<PorePressureTopDrainedStartTime)return(0);
  if(!pos || !code)Run_Exceptioon("Pointers without data for top drained pore-pressure boundary.");
  const double gmag=GetHydraulicGmag();
  if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for top drained pore-pressure boundary.");
  const double drainthick=(PorePressureDrainThickness>0.f? double(PorePressureDrainThickness): double(KernelH));
  if(drainthick<=0.)Run_Exceptioon("Top drained pore-pressure boundary requires a positive drain thickness or KernelH.");

  unsigned npmat=0;
  double zmax=-DBL_MAX;
  double pwbeforemin=DBL_MAX,pwbeforemax=-DBL_MAX;
  for(unsigned p=pini;p<pini+n;p++){
    if(CODE_IsFluid(code[p])){
      npmat++;
      const tdouble3 ps=pos[p];
      const double z=GetHydraulicElevation(ps);
      zmax=max(zmax,z);
      pwbeforemin=min(pwbeforemin,porepress[p]);
      pwbeforemax=max(pwbeforemax,porepress[p]);
    }
  }
  if(!npmat){
    if(printlog)Log->PrintWarning("Top drained pore-pressure boundary found no material particles.");
    return(0);
  }

  const double zthreshold=zmax-drainthick;
  unsigned affected=0;
  double pwaftermin=DBL_MAX,pwaftermax=-DBL_MAX;
  for(unsigned p=pini;p<pini+n;p++){
    if(CODE_IsFluid(code[p])){
      const tdouble3 ps=pos[p];
      const double z=GetHydraulicElevation(ps);
      if(z>=zthreshold){
        porepress[p]=GetHydrostaticPorePressure(ps);
        affected++;
      }
      pwaftermin=min(pwaftermin,porepress[p]);
      pwaftermax=max(pwaftermax,porepress[p]);
    }
  }

  if(printlog){
    Log->Printf("Top drained pore-pressure boundary activated on CPU (%s): TimeStep=%g, start_time=%g, enabled=True, zmax_material=%g, drain_thickness=%g, z_threshold=%g, affected=%u/%u, PorePress before=[%g,%g] Pa, after=[%g,%g] Pa."
      ,(stage? stage: "unknown"),timestep,PorePressureTopDrainedStartTime,zmax,drainthick,zthreshold,affected,npmat,pwbeforemin,pwbeforemax,pwaftermin,pwaftermax);
    if(double(PorePressureWaterLevel)<zmax)Log->PrintWarning(fun::PrintStr("Top drained pore-pressure boundary is used with WaterLevel=%g below top elevation=%g. The drained top layer may be above the water level.",PorePressureWaterLevel,zmax));
  }
  return(affected);
}

//==============================================================================
/// Applies a minimal bottom no-flux condition for excess pore pressure on material particles.
//==============================================================================
unsigned JSphCpu::ApplyPorePressureBottomNoFlux(unsigned n,unsigned pini,const tdouble3 *pos,const typecode *code
  ,double *porepress,const char *stage,bool printlog)
{
  if(!HydromechCoupling || PorePressureModel!=1 || !PorePressureBottomNoFlux || !porepress)return(0);
  if(!pos || !code)Run_Exceptioon("Pointers without data for bottom no-flux pore-pressure boundary.");
  const double gmag=GetHydraulicGmag();
  if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for bottom no-flux pore-pressure boundary.");
  const double bottomthick=(PorePressureBottomNoFluxThickness>0.f? double(PorePressureBottomNoFluxThickness): double(KernelH));
  if(bottomthick<=0.)Run_Exceptioon("Bottom no-flux pore-pressure boundary requires a positive thickness or KernelH.");

  unsigned npmat=0;
  double zmin=DBL_MAX,zmax=-DBL_MAX;
  for(unsigned p=pini;p<pini+n;p++){
    if(CODE_IsFluid(code[p])){
      npmat++;
      const tdouble3 ps=pos[p];
      const double z=GetHydraulicElevation(ps);
      zmin=min(zmin,z);
      zmax=max(zmax,z);
    }
  }
  if(!npmat){
    if(printlog)Log->PrintWarning("Bottom no-flux pore-pressure boundary found no material particles.");
    return(0);
  }

  const double zthreshold=zmin+bottomthick;
  const double zrefmin=zthreshold;
  const double zrefmax=zmin+2.*bottomthick;
  unsigned refcount=0;
  double excesssum=0.;
  for(unsigned p=pini;p<pini+n;p++){
    if(CODE_IsFluid(code[p])){
      const tdouble3 ps=pos[p];
      const double z=GetHydraulicElevation(ps);
      if(z>zrefmin && z<=zrefmax){
        const double hydro=GetHydrostaticPorePressure(ps);
        excesssum+=porepress[p]-hydro;
        refcount++;
      }
    }
  }
  if(!refcount){
    if(printlog)Log->PrintWarning(fun::PrintStr("Bottom no-flux pore-pressure boundary (%s) skipped: reference layer has no material particles. zmin=%g, reference=[%g,%g]."
      ,(stage? stage: "unknown"),zmin,zrefmin,zrefmax));
    return(0);
  }
  const double excessmean=excesssum/double(refcount);

  unsigned affected=0;
  double excessbeforemin=DBL_MAX,excessbeforemax=-DBL_MAX;
  double excessaftermin=DBL_MAX,excessaftermax=-DBL_MAX;
  for(unsigned p=pini;p<pini+n;p++){
    if(CODE_IsFluid(code[p])){
      const tdouble3 ps=pos[p];
      const double z=GetHydraulicElevation(ps);
      if(z<=zthreshold){
        const double hydro=GetHydrostaticPorePressure(ps);
        const double excessbefore=porepress[p]-hydro;
        excessbeforemin=min(excessbeforemin,excessbefore);
        excessbeforemax=max(excessbeforemax,excessbefore);
        porepress[p]=hydro+excessmean;
        const double excessafter=porepress[p]-hydro;
        excessaftermin=min(excessaftermin,excessafter);
        excessaftermax=max(excessaftermax,excessafter);
        affected++;
      }
    }
  }
  if(!affected){
    excessbeforemin=excessbeforemax=excessaftermin=excessaftermax=0.;
  }

  if(printlog){
    Log->Printf("Bottom no-flux pore-pressure boundary (%s): enabled=True, zmin_material=%g, bottom_thickness=%g, z_threshold=%g, reference=[%g,%g], affected=%u/%u, reference_count=%u, excess_ref_mean=%g Pa, bottom excess before=[%g,%g] Pa, after=[%g,%g] Pa."
      ,(stage? stage: "unknown"),zmin,bottomthick,zthreshold,zrefmin,zrefmax,affected,npmat,refcount,excessmean,excessbeforemin,excessbeforemax,excessaftermin,excessaftermax);
    if(PorePressureTopDrained){
      const double topthick=(PorePressureDrainThickness>0.f? double(PorePressureDrainThickness): double(KernelH));
      const double ztopthreshold=zmax-topthick;
      if(zthreshold>=ztopthreshold)Log->PrintWarning(fun::PrintStr("Top drained and bottom no-flux pore-pressure correction layers overlap or touch. bottom_threshold=%g, top_threshold=%g.",zthreshold,ztopthreshold));
    }
    if(double(PorePressureWaterLevel)<zmax)Log->PrintWarning(fun::PrintStr("Bottom no-flux pore-pressure boundary is used with WaterLevel=%g below top elevation=%g. This is not the recommended saturated PR verification setup.",PorePressureWaterLevel,zmax));
  }
  return(affected);
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
  const double gmag=GetHydraulicGmag();
  if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for elevation-head Laplacian.");
  const int nint=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided) if(nint>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int cp=0;cp<nint;cp++){
    const unsigned p1=pini+unsigned(cp);
    if(!CODE_IsFluid(code[p1]))continue;

    float lapp1=0;
    const tdouble3 posp1=pos[p1];
    const double zp1=GetHydraulicElevation(posp1);
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
          tdouble3 posp2h=posp2;
          posp2h.y=posp2y;
          const double zp2=GetHydraulicElevation(posp2h);
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
/// Adds CPU-only hydraulic boundary contributions to PR LapPorePress/LapZ operators.
//==============================================================================
template<TpKernel tker> unsigned JSphCpu::ApplyPorePressureBoundaryOperatorT(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,const tfloat3 *boundnormal,const double *porepress
  ,float *lapporepress,float *lapz,double timestep,bool printlog)
{
  if(!HydromechCoupling || PorePressureModel!=1 || (PorePressureBoundaryOperator!=1 && PorePressureBoundaryOperator!=2 && PorePressureBoundaryOperator!=3))return(0);
  if(!pos || !velrhop || !code || !porepress || !lapporepress || !lapz)
    Run_Exceptioon("Pointers without data for pore-pressure boundary operator.");
  if(PorePressureBoundaryOperator==2 && !dcell)
    Run_Exceptioon("PorePressureBoundaryOperator=2 requires cell data for boundary-particle hydraulic reconstruction.");
  if(PorePressureBoundaryOperator==3){
    if(!PorePressureCurvedDrained)return(0);
  }
  else if(!PorePressureTopDrained && !PorePressureBottomNoFlux)return(0);
  const double gmag=GetHydraulicGmag();
  if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for pore-pressure boundary operator.");
  const double rhog=double(SoilCte.WaterDensity)*gmag;
  const tfloat3 hgrav=GetHydraulicGravity();
  const double elevux=-double(hgrav.x)/gmag;
  const double elevuy=-double(hgrav.y)/gmag;
  const double elevuz=-double(hgrav.z)/gmag;
  const auto hydrostatic_linear=[&](const double z)->double{
    return(HydraulicElevationSource? rhog*(double(PorePressureWaterLevel)-z): 0.);
  };

  unsigned npmat=0;
  double zmin=DBL_MAX,zmax=-DBL_MAX;
  for(unsigned p=pini;p<pini+n;p++)if(CODE_IsFluid(code[p])){
    const double z=GetHydraulicElevation(pos[p]);
    zmin=min(zmin,z);
    zmax=max(zmax,z);
    npmat++;
  }
  if(!npmat){
    if(printlog)Log->PrintWarning("Pore-pressure boundary operator found no material particles.");
    return(0);
  }

  const double gap=(Dp>0.? 0.5*double(Dp): 0.25*double(KernelSize));
  const double topthick=(PorePressureDrainThickness>0.f? double(PorePressureDrainThickness): double(KernelH));
  const double bottomthick=(PorePressureBottomNoFluxThickness>0.f? double(PorePressureBottomNoFluxThickness): double(KernelH));
  if((PorePressureTopDrained && topthick<=0.) || (PorePressureBottomNoFlux && bottomthick<=0.))
    Run_Exceptioon("Pore-pressure boundary operator requires positive boundary thickness or KernelH.");
  const bool topactive=(PorePressureTopDrained && timestep>=PorePressureTopDrainedStartTime);
  const bool bottomactive=PorePressureBottomNoFlux;
  const double ztopplane=zmax+gap;
  const double zbottomplane=zmin-gap;
  const double ztopthreshold=zmax-topthick;
  const double zbottomthreshold=zmin+bottomthick;

  unsigned topaffected=0,bottomaffected=0,skipped=0;
  double maxabsdpwtop=0.,maxabsdpwbottom=0.;
  double maxabslapadd=0.,maxabsheadadd=0.;

  if(PorePressureBoundaryOperator==1){
    for(unsigned p=pini;p<pini+n;p++)if(CODE_IsFluid(code[p])){
      if(velrhop[p].w<=0.f){ skipped++; continue; }
      const double zi=GetHydraulicElevation(pos[p]);
      const double hydroi=GetHydrostaticPorePressure(pos[p]);
      const double voli=double(MassFluid)/double(velrhop[p].w);

      if(topactive && zi>=ztopthreshold){
        const double zg=2.*ztopplane-zi;
        const double delta=zg-zi;
        const double drx=-delta*elevux;
        const double dry=-delta*elevuy;
        const double drz=-delta*elevuz;
        const double rr2=drx*drx+dry*dry+drz*drz;
        if(rr2<=double(KernelSize2) && rr2>=ALMOSTZERO){
          const float fac=fsph::GetKernel_Fac<tker>(CSP,float(rr2));
          const double dotrgrad=rr2*double(fac);
          // Virtual points use the linear hydrostatic reference, not the physical
          // non-negative clamp, so a hydrostatic field keeps LapP/(rho*g)+LapZ=0
          // across the mirrored boundary stencil.
          const double pwg=hydrostatic_linear(zg);
          const double lapadd=2.*voli*(porepress[p]-pwg)*dotrgrad/(rr2+ALMOSTZERO);
          const double zadd=2.*voli*(zi-zg)*dotrgrad/(rr2+ALMOSTZERO);
          lapporepress[p]+=float(lapadd);
          lapz[p]+=float(zadd);
          topaffected++;
          maxabsdpwtop=max(maxabsdpwtop,fabs(porepress[p]-pwg));
          maxabslapadd=max(maxabslapadd,fabs(lapadd));
          maxabsheadadd=max(maxabsheadadd,fabs(lapadd/rhog+zadd));
        }
        else skipped++;
      }

      if(bottomactive && zi<=zbottomthreshold){
        const double zg=2.*zbottomplane-zi;
        const double delta=zg-zi;
        const double drx=-delta*elevux;
        const double dry=-delta*elevuy;
        const double drz=-delta*elevuz;
        const double rr2=drx*drx+dry*dry+drz*drz;
        if(rr2<=double(KernelSize2) && rr2>=ALMOSTZERO){
          const float fac=fsph::GetKernel_Fac<tker>(CSP,float(rr2));
          const double dotrgrad=rr2*double(fac);
          const double excessi=porepress[p]-hydroi;
          const double hydrog=hydrostatic_linear(zg);
          const double pwg=hydrog+excessi; // excess/head Neumann mirror; not zero total pressure gradient.
          const double lapadd=2.*voli*(porepress[p]-pwg)*dotrgrad/(rr2+ALMOSTZERO);
          const double zadd=2.*voli*(zi-zg)*dotrgrad/(rr2+ALMOSTZERO);
          lapporepress[p]+=float(lapadd);
          lapz[p]+=float(zadd);
          bottomaffected++;
          maxabsdpwbottom=max(maxabsdpwbottom,fabs(porepress[p]-pwg));
          maxabslapadd=max(maxabslapadd,fabs(lapadd));
          maxabsheadadd=max(maxabsheadadd,fabs(lapadd/rhog+zadd));
        }
        else skipped++;
      }
    }
  }

  unsigned bndtop=0,bndbottom=0,bndinactive=0,bndnormals=0,bndmlssamples=0,bndmlsfallback=0;
  double bndexmin=DBL_MAX,bndexmax=-DBL_MAX;
  unsigned curvedaffected=0,curvedskipped=0;
  unsigned curvedquadparticles=0,curvedquadsamples=0;
  unsigned curvedbndselected=0,curvedbndtargets=0,curvedbndpairs=0;
  unsigned curvedbndadamisamples=0,curvedbndadamifallback=0;
  double curvedbndadamiabsmean=0.,curvedbndadamimaxabs=0.;
  unsigned curvedbndweighttargets=0;
  double curvedbndsmmean=0.,curvedbndsmean=0.,curvedbndscalemean=0.,curvedbndfracmean=0.;
  double curvedbndsmmax=0.,curvedbndsmax=0.,curvedbndscalemax=0.,curvedbndfracmax=0.;
  double curvedbndscalemin=DBL_MAX;
  unsigned curvedmlstargets=0,curvedmlssamples=0,curvedmlsfallback=0,curvedmlscondcount=0;
  double curvedmlscondmean=0.,curvedmlscondmin=DBL_MAX,curvedmlscondmax=0.;
  double curvedmlsgradmean=0.,curvedmlsgradmax=0.,curvedmlsfluxintegral=0.,curvedmlsstoragerate=0.;
  double curvedmlsarea=0.,curvedmlsshellvolume=0.,curvedmlslapcorrmax=0.;
  const unsigned curvedshellbinmax=4;
  unsigned curvedshellpop[4]={0,0,0,0};
  double curvedshellvol[4]={0.,0.,0.,0.};
  double curvedshellpsum[4]={0.,0.,0.,0.};
  double curvedshellrsum[4]={0.,0.,0.,0.};
  unsigned curvedshelltargets=0,curvedshellfallback=0;
  double curvedshellwidth=0.,curvedshelloutermean=0.,curvedshellouterrmean=0.,curvedshellgrad=0.;
  double curvedshellfluxdensity=0.,curvedshellfluxintegral=0.,curvedshellstoragerate=0.;
  double curvedshellsinkvolume=0.,curvedshelllapcorr=0.,curvedshellresidual=0.;
  unsigned curvedshell7count=0,curvedshell7corrected=0,curvedshell7fallback=0;
  unsigned curvedshell7minpop=0,curvedshell7maxpop=0,curvedshell7negative=0;
  double curvedshell7width=0.,curvedshell7totalstorage=0.,curvedshell7boundaryflux=0.;
  double curvedshell7targetstorage=0.,curvedshell7currentstorage=0.,curvedshell7correctionstorage=0.,curvedshell7correctedstorage=0.;
  double curvedshell7conservationresidual=0.,curvedshell7maxabslapcorr=0.,curvedshell7maxabsratecorr=0.;
  double curvedshell7minpressure=DBL_MAX,curvedshell7maxpressure=-DBL_MAX;
  vector<int> curvedshell7pbin;
  vector<unsigned> curvedshell7pop;
  vector<double> curvedshell7edge,curvedshell7volana,curvedshell7veff,curvedshell7psum,curvedshell7rsum;
  vector<double> curvedshell7pmean,curvedshell7rmean,curvedshell7flux,curvedshell7targetrate,curvedshell7currentrate,curvedshell7corrrate,curvedshell7lapcorr;
  unsigned curvedlap8targets=0,curvedlap8corrected=0,curvedlap8fallback=0,curvedlap8materials=0,curvedlap8boundaries=0,curvedlap8condcount=0;
  double curvedlap8condmean=0.,curvedlap8condmin=DBL_MAX,curvedlap8condmax=0.;
  double curvedlap8lapmean=0.,curvedlap8lapmax=0.,curvedlap8replacedmean=0.,curvedlap8replacedmax=0.;
  unsigned curvedlap8limitertargets=0,curvedlap8blendlimited=0,curvedlap8positivitylimited=0;
  double curvedlap8thetamean=0.,curvedlap8thetamin=DBL_MAX,curvedlap8thetamax=0.;
  double curvedlap8limitedmean=0.,curvedlap8limitedmax=0.,curvedlap8ratediffmax=0.;
  double curvedlap8support=0.,curvedlap8rthreshold=0.;
  double curvedresidualmax=0.,curvedrmin=DBL_MAX,curvedrmax=0.;

  if(PorePressureBoundaryOperator==2){
    const auto boundary_hydraulic_pos=[&](unsigned pb)->tdouble3{
      tdouble3 r=pos[pb];
      if(boundnormal && boundnormal[pb]!=TFloat3(0))r=r+ToTDouble3(boundnormal[pb]);
      return(r);
    };
    const auto reconstruct_excess=[&](unsigned pb)->double{
      tdouble3 refpos=boundary_hydraulic_pos(pb);
      if(boundnormal && boundnormal[pb]!=TFloat3(0)){
        bndnormals++;
      }
      double wsum=0., exsum=0.;
      const StNgSearch ngb=nsearch::Init(dcell[pb],false,divdata);
      for(int z=ngb.zini;z<ngb.zfin;z++)for(int y=ngb.yini;y<ngb.yfin;y++){
        const tuint2 pif=nsearch::ParticleRange(y,z,ngb,divdata);
        for(unsigned p3=pif.x;p3<pif.y;p3++)if(CODE_IsFluid(code[p3]) && velrhop[p3].w>0.f){
          const float drx=float(refpos.x-pos[p3].x);
          const float dry=float(refpos.y-pos[p3].y);
          const float drz=float(refpos.z-pos[p3].z);
          const float rr2=drx*drx+dry*dry+drz*drz;
          if(rr2<=KernelSize2){
            const double wab=double(fsph::GetKernel_Wab<tker>(CSP,rr2));
            const double vol=double(MassFluid)/double(velrhop[p3].w);
            const double weight=vol*wab;
            const double z3=GetHydraulicElevation(pos[p3]);
            const double excess3=porepress[p3]-hydrostatic_linear(z3);
            exsum+=weight*excess3;
            wsum+=weight;
            bndmlssamples++;
          }
        }
      }
      if(wsum>0.)return(exsum/wsum);
      bndmlsfallback++;
      return(0.);
    };

    for(unsigned p=pini;p<pini+n;p++)if(CODE_IsFluid(code[p])){
      if(velrhop[p].w<=0.f){ skipped++; continue; }
      const tdouble3 posp1=pos[p];
      const double zi=GetHydraulicElevation(posp1);
      const double pwp1=porepress[p];

      // The current PR cell-neighbour path is material-centric, so this
      // CPU-only prototype explicitly scans original boundary particles and
      // filters them by distance. This keeps legacy modes untouched and makes
      // reconstructed hydraulic boundary particles enter the PR quadrature.
      for(unsigned p2=0;p2<pini;p2++){
          const bool p2bound=(CODE_IsNormal(code[p2]) && !CODE_IsFluid(code[p2]));
          if(!p2bound)continue;
          if(velrhop[p2].w<=0.f){ skipped++; continue; }

          const tdouble3 posb=boundary_hydraulic_pos(p2);
          const double zb=GetHydraulicElevation(posb);
          int bmode=0;
          if(bottomactive && zb<=zbottomthreshold)bmode=2;
          if(topactive && zb>=ztopthreshold)bmode=1; // drained overrides if layers touch.
          if(!bmode){ bndinactive++; continue; }

          const float drx=float(posp1.x-posb.x);
          const float dry=float(posp1.y-posb.y);
          const float drz=float(posp1.z-posb.z);
          const float rr2=drx*drx+dry*dry+drz*drz;
          if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
            const float fac=fsph::GetKernel_Fac<tker>(CSP,rr2);
            const float frx=fac*drx,fry=fac*dry,frz=fac*drz;
            const double dotrgrad=double(drx*frx+dry*fry+drz*frz);
            const double volp2=double(MassBound)/double(velrhop[p2].w);
            double excessb=0.;
            if(bmode==1){
              excessb=0.;
              bndtop++;
            }
            else{
              excessb=reconstruct_excess(p2);
              bndbottom++;
            }
            const double pwb=hydrostatic_linear(zb)+excessb;
            const double lapadd=2.*volp2*(pwp1-pwb)*dotrgrad/(double(rr2)+ALMOSTZERO);
            const double zadd=2.*volp2*(zi-zb)*dotrgrad/(double(rr2)+ALMOSTZERO);
            lapporepress[p]+=float(lapadd);
            lapz[p]+=float(zadd);
            if(bmode==1)maxabsdpwtop=max(maxabsdpwtop,fabs(pwp1-pwb));
            else maxabsdpwbottom=max(maxabsdpwbottom,fabs(pwp1-pwb));
            bndexmin=min(bndexmin,excessb);
            bndexmax=max(bndexmax,excessb);
            maxabslapadd=max(maxabslapadd,fabs(lapadd));
            maxabsheadadd=max(maxabsheadadd,fabs(lapadd/rhog+zadd));
          }
      }
    }
    topaffected=bndtop;
    bottomaffected=bndbottom;
    if(bndexmin==DBL_MAX)bndexmin=bndexmax=0.;
  }

  if(PorePressureBoundaryOperator==3){
    if(CurvedDrainedBoundaryRadius<=0.)
      Run_Exceptioon("CurvedDrainedBoundaryRadius must be greater than zero for PorePressureBoundaryOperator=3.");
    const double shellthick=(CurvedDrainedBoundaryThickness>0.? CurvedDrainedBoundaryThickness: double(KernelH));
    if(shellthick<=0.)Run_Exceptioon("PorePressureBoundaryOperator=3 requires positive CurvedDrainedBoundaryThickness or KernelH.");
    const double mindist=(Dp>0.? 0.5*double(Dp): 0.25*double(KernelSize));
    const double rtarget=CurvedDrainedBoundaryRadius;
    const double rmin=max(0.,rtarget-shellthick);
    const double pi=3.1415926535897932384626433832795;
    const double spherearea=4.*pi*rtarget*rtarget;
    const double shellvolume=(4.*pi/3.)*(rtarget*rtarget*rtarget-rmin*rmin*rmin);
    const double shellareafactor=(shellvolume>ALMOSTZERO? spherearea/shellvolume: 0.);
    const double diffcoef=(double(SoilCte.WaterBulkModulus)/double(SoilCte.Porosity0))*(double(SoilCte.HydraulicConductivity)/(rhog));
    curvedmlsarea=spherearea;
    curvedmlsshellvolume=shellvolume;
    struct StCurvedBndHyd{
      unsigned p;
      tdouble3 pos;
      double z;
      double hydro;
      double volume;
      double adami_excess;
    };
    struct StCurvedMlsFluxCorrection{
      unsigned p;
    };
    vector<StCurvedBndHyd> curvedbnd;
    vector<StCurvedMlsFluxCorrection> curvedmlscorrections;
    double curvedmlsareaweight=0.;
    const auto solve_mls10=[&](double a[10][10],double b[10],double x[10],double &cond)->bool{
      double m[10][11];
      for(unsigned i=0;i<10;i++){
        for(unsigned j=0;j<10;j++)m[i][j]=a[i][j];
        m[i][10]=b[i];
        x[i]=0.;
      }
      double minpivot=DBL_MAX,maxpivot=0.;
      for(unsigned k=0;k<10;k++){
        unsigned ip=k;
        double ap=fabs(m[k][k]);
        for(unsigned i=k+1;i<10;i++){
          const double ai=fabs(m[i][k]);
          if(ai>ap){ ap=ai; ip=i; }
        }
        if(ap<=ALMOSTZERO)return(false);
        if(ip!=k)for(unsigned j=k;j<11;j++)swap(m[k][j],m[ip][j]);
        maxpivot=max(maxpivot,ap);
        minpivot=min(minpivot,ap);
        const double piv=m[k][k];
        for(unsigned j=k;j<11;j++)m[k][j]/=piv;
        for(unsigned i=0;i<10;i++)if(i!=k){
          const double f=m[i][k];
          if(f!=0.)for(unsigned j=k;j<11;j++)m[i][j]-=f*m[k][j];
        }
      }
      cond=(minpivot>ALMOSTZERO? maxpivot/minpivot: DBL_MAX);
      for(unsigned i=0;i<10;i++)x[i]=m[i][10];
      return(true);
    };
    if(CurvedDrainedBoundaryMode==4){
      const double bndtol=(CurvedDrainedBoundarySelectionTolerance>0.? CurvedDrainedBoundarySelectionTolerance: max(double(KernelH),double(Dp)));
      const double rbmin=max(0.,rtarget-bndtol);
      const double rbmax=rtarget+max(bndtol,shellthick);
      for(unsigned pb=0;pb<pini;pb++){
        const bool pbbound=(CODE_IsNormal(code[pb]) && !CODE_IsFluid(code[pb]));
        if(!pbbound)continue;
        if(CurvedDrainedBoundaryTargetMkBound>=0 && int(CODE_GetTypeValue(code[pb]))!=CurvedDrainedBoundaryTargetMkBound)continue;
        if(velrhop[pb].w<=0.f){ skipped++; continue; }
        const tdouble3 brel=pos[pb]-CurvedDrainedBoundaryCenter;
        const double rb=sqrt(brel.x*brel.x+brel.y*brel.y+brel.z*brel.z);
        if(rb<rbmin || rb>rbmax)continue;
        if(rb<=ALMOSTZERO){ skipped++; continue; }
        const tdouble3 bdir=brel*(1./rb);
        StCurvedBndHyd b;
        b.p=pb;
        // The selected boundary particle provides the angular quadrature site;
        // the hydraulic Dirichlet state is evaluated on the drained spherical
        // surface so the dummy shell can remain mechanically separated.
        b.pos=CurvedDrainedBoundaryCenter + bdir*rtarget;
        b.z=GetHydraulicElevation(b.pos);
        b.hydro=hydrostatic_linear(b.z);
        b.volume=double(MassBound)/double(velrhop[pb].w);
        b.adami_excess=0.;
        curvedbnd.push_back(b);
      }
      curvedbndselected=unsigned(curvedbnd.size());
      if(CurvedDrainedBoundaryAdamiDiagnostic && curvedbndselected){
        for(unsigned ib=0;ib<curvedbndselected;ib++){
          double wsum=0.,exsum=0.;
          for(unsigned p3=pini;p3<pini+n;p3++)if(CODE_IsFluid(code[p3]) && velrhop[p3].w>0.f){
            if(CurvedDrainedBoundaryTargetMk>=0 && int(CODE_GetTypeValue(code[p3]))!=CurvedDrainedBoundaryTargetMk)continue;
            const double drx=curvedbnd[ib].pos.x-pos[p3].x;
            const double dry=curvedbnd[ib].pos.y-pos[p3].y;
            const double drz=curvedbnd[ib].pos.z-pos[p3].z;
            const double rr2=drx*drx+dry*dry+drz*drz;
            if(rr2<=double(KernelSize2)){
              const double wab=double(fsph::GetKernel_Wab<tker>(CSP,float(rr2)));
              const double vol=double(MassFluid)/double(velrhop[p3].w);
              const double weight=vol*wab;
              const double z3=GetHydraulicElevation(pos[p3]);
              const double excess3=porepress[p3]-hydrostatic_linear(z3);
              exsum+=weight*excess3;
              wsum+=weight;
              curvedbndadamisamples++;
            }
          }
          if(wsum>0.){
            curvedbnd[ib].adami_excess=exsum/wsum;
            curvedbndadamiabsmean+=fabs(curvedbnd[ib].adami_excess);
            curvedbndadamimaxabs=max(curvedbndadamimaxabs,fabs(curvedbnd[ib].adami_excess));
          }
          else curvedbndadamifallback++;
        }
        if(curvedbndselected)curvedbndadamiabsmean/=double(curvedbndselected);
      }
    }
    if(CurvedDrainedBoundaryMode==6){
      curvedshellwidth=shellthick;
      const double shellinner=max(0.,rtarget-curvedshellwidth*double(curvedshellbinmax));
      for(unsigned p3=pini;p3<pini+n;p3++)if(CODE_IsFluid(code[p3]) && velrhop[p3].w>0.f){
        if(CurvedDrainedBoundaryTargetMk>=0 && int(CODE_GetTypeValue(code[p3]))!=CurvedDrainedBoundaryTargetMk)continue;
        const tdouble3 rel3=pos[p3]-CurvedDrainedBoundaryCenter;
        const double r3=sqrt(rel3.x*rel3.x+rel3.y*rel3.y+rel3.z*rel3.z);
        if(r3<=ALMOSTZERO)continue;
        const double reff=min(rtarget,r3);
        if(reff<shellinner)continue;
        int ib=int(floor((rtarget-reff)/curvedshellwidth));
        if(ib<0)ib=0;
        if(ib>=int(curvedshellbinmax))ib=int(curvedshellbinmax)-1;
        const double vol=double(MassFluid)/double(velrhop[p3].w);
        const double z3=GetHydraulicElevation(pos[p3]);
        const double u3=(CurvedDrainedBoundaryUseExcess? porepress[p3]-hydrostatic_linear(z3): porepress[p3]);
        curvedshellpop[ib]++;
        curvedshellvol[ib]+=vol;
        curvedshellpsum[ib]+=vol*u3;
        curvedshellrsum[ib]+=vol*reff;
      }
      if(curvedshellpop[0]>=3 && curvedshellvol[0]>ALMOSTZERO && diffcoef>ALMOSTZERO){
        curvedshelloutermean=curvedshellpsum[0]/curvedshellvol[0];
        curvedshellouterrmean=curvedshellrsum[0]/curvedshellvol[0];
        const double gap=max(mindist,rtarget-curvedshellouterrmean);
        curvedshellgrad=(curvedshelloutermean-CurvedDrainedBoundaryValue)/gap;
        curvedshellfluxdensity=diffcoef*curvedshellgrad;
        curvedshellfluxintegral=curvedshellfluxdensity*spherearea;
        curvedshellstoragerate=-curvedshellfluxintegral;
        curvedshellsinkvolume=curvedshellvol[0];
        curvedshelllapcorr=-curvedshellfluxintegral/(diffcoef*curvedshellsinkvolume);
        curvedshellresidual=curvedshellstoragerate+curvedshellfluxintegral;
      }
      else curvedshellfallback=1;
    }
    if(CurvedDrainedBoundaryMode==7){
      // Conservative multi-shell radial exchange prototype. The existing
      // material-material LapPorePress field is first reduced to shell-average
      // pressure rates, then a conservative FV shell correction is added back.
      const double basewidth=(CurvedDrainedBoundaryThickness>0.? CurvedDrainedBoundaryThickness: (Dp>0.? double(Dp): double(KernelH)));
      if(basewidth<=ALMOSTZERO || diffcoef<=ALMOSTZERO)curvedshell7fallback=1;
      else{
        const unsigned autocount=unsigned(max(2.,ceil(rtarget/basewidth)));
        curvedshell7count=(CurvedDrainedShellMode==1 && CurvedDrainedShellCount? CurvedDrainedShellCount: autocount);
        if(curvedshell7count<2)curvedshell7count=2;
        curvedshell7width=rtarget/double(curvedshell7count);
        curvedshell7pbin.assign(n,-1);
        curvedshell7pop.assign(curvedshell7count,0);
        curvedshell7edge.assign(curvedshell7count+1,0.);
        curvedshell7volana.assign(curvedshell7count,0.);
        curvedshell7veff.assign(curvedshell7count,0.);
        curvedshell7psum.assign(curvedshell7count,0.);
        curvedshell7rsum.assign(curvedshell7count,0.);
        curvedshell7pmean.assign(curvedshell7count,0.);
        curvedshell7rmean.assign(curvedshell7count,0.);
        curvedshell7flux.assign(curvedshell7count+1,0.);
        curvedshell7targetrate.assign(curvedshell7count,0.);
        curvedshell7currentrate.assign(curvedshell7count,0.);
        curvedshell7corrrate.assign(curvedshell7count,0.);
        curvedshell7lapcorr.assign(curvedshell7count,0.);
        for(unsigned k=0;k<=curvedshell7count;k++)curvedshell7edge[k]=rtarget*double(k)/double(curvedshell7count);
        for(unsigned k=0;k<curvedshell7count;k++){
          const double rin=curvedshell7edge[k];
          const double rout=curvedshell7edge[k+1];
          curvedshell7volana[k]=(4.*pi/3.)*(rout*rout*rout-rin*rin*rin);
        }
        for(unsigned p=pini;p<pini+n;p++)if(CODE_IsFluid(code[p]) && velrhop[p].w>0.f){
          if(CurvedDrainedBoundaryTargetMk>=0 && int(CODE_GetTypeValue(code[p]))!=CurvedDrainedBoundaryTargetMk)continue;
          const tdouble3 rel=pos[p]-CurvedDrainedBoundaryCenter;
          const double r=sqrt(rel.x*rel.x+rel.y*rel.y+rel.z*rel.z);
          if(r<=ALMOSTZERO)continue;
          curvedrmin=min(curvedrmin,r);
          curvedrmax=max(curvedrmax,r);
          const double reff=min(rtarget*(1.-1.e-12),max(0.,r));
          unsigned ib=unsigned(floor(reff/rtarget*double(curvedshell7count)));
          if(ib>=curvedshell7count)ib=curvedshell7count-1;
          const double vol=double(MassFluid)/double(velrhop[p].w);
          const double zi=GetHydraulicElevation(pos[p]);
          const double u=(CurvedDrainedBoundaryUseExcess? porepress[p]-hydrostatic_linear(zi): porepress[p]);
          curvedshell7pbin[p-pini]=int(ib);
          curvedshell7pop[ib]++;
          curvedshell7veff[ib]+=vol;
          curvedshell7psum[ib]+=vol*u;
          curvedshell7rsum[ib]+=vol*reff;
          curvedshell7currentrate[ib]+=vol*diffcoef*double(lapporepress[p]);
          curvedshell7totalstorage+=vol*u;
          curvedshell7minpressure=min(curvedshell7minpressure,u);
          curvedshell7maxpressure=max(curvedshell7maxpressure,u);
          if(u<0.)curvedshell7negative++;
          curvedresidualmax=max(curvedresidualmax,fabs(u-CurvedDrainedBoundaryValue));
        }
        curvedshell7minpop=UINT_MAX;
        for(unsigned k=0;k<curvedshell7count;k++){
          curvedshell7minpop=min(curvedshell7minpop,curvedshell7pop[k]);
          curvedshell7maxpop=max(curvedshell7maxpop,curvedshell7pop[k]);
          if(curvedshell7pop[k]<CurvedDrainedShellMinParticles || curvedshell7veff[k]<=ALMOSTZERO)curvedshell7fallback++;
          if(curvedshell7veff[k]>ALMOSTZERO){
            curvedshell7pmean[k]=curvedshell7psum[k]/curvedshell7veff[k];
            curvedshell7rmean[k]=curvedshell7rsum[k]/curvedshell7veff[k];
            curvedshell7currentrate[k]/=curvedshell7veff[k];
          }
          else{
            curvedshell7pmean[k]=0.;
            curvedshell7rmean[k]=0.5*(curvedshell7edge[k]+curvedshell7edge[k+1]);
            curvedshell7currentrate[k]=0.;
          }
        }
        if(curvedshell7minpop==UINT_MAX)curvedshell7minpop=0;
        int shellfirst=-1,shelllast=-1;
        for(unsigned k=0;k<curvedshell7count;k++)if(curvedshell7pop[k]>=CurvedDrainedShellMinParticles && curvedshell7veff[k]>ALMOSTZERO){
          if(shellfirst<0)shellfirst=int(k);
          shelllast=int(k);
        }
        curvedshell7fallback=0;
        if(shellfirst<0 || shelllast<0)curvedshell7fallback=1;
        else{
          for(int k=shellfirst;k<=shelllast;k++){
            const unsigned ku=unsigned(k);
            if(curvedshell7pop[ku]<CurvedDrainedShellMinParticles || curvedshell7veff[ku]<=ALMOSTZERO)curvedshell7fallback++;
          }
          if(unsigned(shelllast)!=curvedshell7count-1)curvedshell7fallback++;
        }
        if(!curvedshell7fallback){
          curvedshell7flux[unsigned(shellfirst)]=0.;
          for(unsigned k=unsigned(shellfirst);k<unsigned(shelllast);k++){
            const double rface=curvedshell7edge[k+1];
            const double area=4.*pi*rface*rface;
            const double dr=max(mindist,curvedshell7rmean[k+1]-curvedshell7rmean[k]);
            curvedshell7flux[k+1]=-diffcoef*area*(curvedshell7pmean[k+1]-curvedshell7pmean[k])/dr;
          }
          {
            const unsigned k=unsigned(shelllast);
            const double gapr=max(mindist,rtarget-curvedshell7rmean[k]);
            curvedshell7flux[k+1]=diffcoef*spherearea*(curvedshell7pmean[k]-CurvedDrainedBoundaryValue)/gapr;
            curvedshell7boundaryflux=curvedshell7flux[k+1];
          }
          for(unsigned k=unsigned(shellfirst);k<=unsigned(shelllast);k++){
            const double storagerate=curvedshell7flux[k]-curvedshell7flux[k+1];
            const double targetrate=storagerate/curvedshell7veff[k];
            curvedshell7targetrate[k]=targetrate;
            curvedshell7corrrate[k]=targetrate-curvedshell7currentrate[k];
            curvedshell7lapcorr[k]=curvedshell7corrrate[k]/diffcoef;
            curvedshell7targetstorage+=storagerate;
            curvedshell7currentstorage+=curvedshell7currentrate[k]*curvedshell7veff[k];
            curvedshell7correctionstorage+=curvedshell7corrrate[k]*curvedshell7veff[k];
            curvedshell7maxabsratecorr=max(curvedshell7maxabsratecorr,fabs(curvedshell7corrrate[k]));
            curvedshell7maxabslapcorr=max(curvedshell7maxabslapcorr,fabs(curvedshell7lapcorr[k]));
          }
          for(unsigned p=pini;p<pini+n;p++)if(CODE_IsFluid(code[p])){
            if(CurvedDrainedBoundaryTargetMk>=0 && int(CODE_GetTypeValue(code[p]))!=CurvedDrainedBoundaryTargetMk)continue;
            const int ib=curvedshell7pbin[p-pini];
            if(ib<0){ curvedskipped++; continue; }
            if(velrhop[p].w<=0.f){ curvedskipped++; continue; }
            if(CurvedDrainedShellCorrectionMode==0){
              const double replacement=curvedshell7targetrate[unsigned(ib)]/diffcoef-double(lapporepress[p]);
              lapporepress[p]+=float(replacement);
              maxabslapadd=max(maxabslapadd,fabs(replacement));
              maxabsheadadd=max(maxabsheadadd,fabs(replacement/rhog));
            }
            else{
              const double lapadd=curvedshell7lapcorr[unsigned(ib)];
              lapporepress[p]+=float(lapadd);
              maxabslapadd=max(maxabslapadd,fabs(lapadd));
              maxabsheadadd=max(maxabsheadadd,fabs(lapadd/rhog));
            }
            curvedaffected++;
            curvedshell7corrected++;
            const double zi=GetHydraulicElevation(pos[p]);
            const double u=(CurvedDrainedBoundaryUseExcess? porepress[p]-hydrostatic_linear(zi): porepress[p]);
            maxabsdpwtop=max(maxabsdpwtop,fabs(u-CurvedDrainedBoundaryValue));
          }
          curvedshell7correctedstorage=curvedshell7currentstorage+curvedshell7correctionstorage;
          curvedshell7conservationresidual=curvedshell7targetstorage+curvedshell7boundaryflux;
        }
      }
      topaffected=curvedaffected;
      if(curvedshell7minpressure==DBL_MAX)curvedshell7minpressure=0.;
      if(curvedshell7maxpressure==-DBL_MAX)curvedshell7maxpressure=0.;
    }
    if(CurvedDrainedBoundaryMode!=7)for(unsigned p=pini;p<pini+n;p++)if(CODE_IsFluid(code[p])){
      if(CurvedDrainedBoundaryTargetMk>=0 && int(CODE_GetTypeValue(code[p]))!=CurvedDrainedBoundaryTargetMk)continue;
      if(velrhop[p].w<=0.f){ skipped++; continue; }
      const tdouble3 rel=pos[p]-CurvedDrainedBoundaryCenter;
      const double r=sqrt(rel.x*rel.x+rel.y*rel.y+rel.z*rel.z);
      if(r<rmin || r<=ALMOSTZERO)continue;
      curvedrmin=min(curvedrmin,r);
      curvedrmax=max(curvedrmax,r);
      const tdouble3 normal=rel*(1./r);
      const double voli=double(MassFluid)/double(velrhop[p].w);
      const double zi=GetHydraulicElevation(pos[p]);
      const double hydroi=hydrostatic_linear(zi);
      const double excessi=porepress[p]-hydroi;
      const double pval=(CurvedDrainedBoundaryUseExcess? excessi: porepress[p]);
      curvedresidualmax=max(curvedresidualmax,fabs(pval-CurvedDrainedBoundaryValue));

      if(CurvedDrainedBoundaryMode==8){
        // Boundary-aware corrected Laplacian prototype. Near the drained
        // spherical surface, replace the material SPH LapPorePress with a
        // local quadratic MLS recovery that includes Dirichlet samples on the
        // physical sphere. Material pore pressure is never clamped.
        curvedlap8targets++;
        curvedlap8support=max(mindist,(CurvedDrainedCorrectedLapRadiusFactor>0.? CurvedDrainedCorrectedLapRadiusFactor*double(KernelH): double(KernelSize)));
        curvedlap8rthreshold=CurvedDrainedCorrectedLapRMinFactor*rtarget;
        if(r<curvedlap8rthreshold)continue;
        if(curvedlap8support<=ALMOSTZERO){ curvedlap8fallback++; continue; }
        const double support=curvedlap8support;
        const double support2=support*support;
        const double invsupport=1./support;
        double ata[10][10];
        double atb[10];
        for(unsigned ia=0;ia<10;ia++){
          atb[ia]=0.;
          for(unsigned ib=0;ib<10;ib++)ata[ia][ib]=0.;
        }
        unsigned materials=0,boundaries=0;
        const auto add_mls_sample=[&](const tdouble3 &ps,const double u,const double weight)->void{
          if(weight<=0.)return;
          const double sx=(ps.x-pos[p].x)*invsupport;
          const double sy=(ps.y-pos[p].y)*invsupport;
          const double sz=(ps.z-pos[p].z)*invsupport;
          const double phi[10]={1.,sx,sy,sz,sx*sx,sy*sy,sz*sz,sx*sy,sx*sz,sy*sz};
          for(unsigned ia=0;ia<10;ia++){
            atb[ia]+=weight*phi[ia]*u;
            for(unsigned ib=0;ib<10;ib++)ata[ia][ib]+=weight*phi[ia]*phi[ib];
          }
        };
        for(unsigned p3=pini;p3<pini+n;p3++)if(CODE_IsFluid(code[p3]) && velrhop[p3].w>0.f){
          if(CurvedDrainedBoundaryTargetMk>=0 && int(CODE_GetTypeValue(code[p3]))!=CurvedDrainedBoundaryTargetMk)continue;
          const double dx=pos[p3].x-pos[p].x;
          const double dy=pos[p3].y-pos[p].y;
          const double dz=pos[p3].z-pos[p].z;
          const double rr2=dx*dx+dy*dy+dz*dz;
          if(rr2>support2)continue;
          const double q=max(0.,1.-sqrt(rr2)*invsupport);
          if(q<=0.)continue;
          const double z3=GetHydraulicElevation(pos[p3]);
          const double u3=(CurvedDrainedBoundaryUseExcess? porepress[p3]-hydrostatic_linear(z3): porepress[p3]);
          add_mls_sample(pos[p3],u3,q*q*q*q);
          materials++;
        }
        tdouble3 t1;
        if(fabs(normal.z)<0.9)t1=TDouble3(-normal.y,normal.x,0.);
        else t1=TDouble3(0.,-normal.z,normal.y);
        const double t1m=sqrt(t1.x*t1.x+t1.y*t1.y+t1.z*t1.z);
        if(t1m>ALMOSTZERO){
          t1=t1*(1./t1m);
          const tdouble3 t2=TDouble3(
            normal.y*t1.z-normal.z*t1.y,
            normal.z*t1.x-normal.x*t1.z,
            normal.x*t1.y-normal.y*t1.x);
          const double tanstep=min(0.5*support,max(mindist,(Dp>0.? double(Dp): 0.5*double(KernelH))));
          const unsigned nsurf=max(1u,CurvedDrainedCorrectedLapBoundarySamples);
          for(unsigned is=0;is<nsurf;is++){
            tdouble3 srel=normal*rtarget;
            if(is>0){
              const double ang=2.*pi*double(is-1)/double(max(1u,nsurf-1));
              srel=srel + t1*(tanstep*cos(ang)) + t2*(tanstep*sin(ang));
            }
            const double srm=sqrt(srel.x*srel.x+srel.y*srel.y+srel.z*srel.z);
            if(srm<=ALMOSTZERO)continue;
            const tdouble3 sdir=srel*(1./srm);
            const tdouble3 posb=CurvedDrainedBoundaryCenter + sdir*rtarget;
            const double dx=posb.x-pos[p].x;
            const double dy=posb.y-pos[p].y;
            const double dz=posb.z-pos[p].z;
            const double rr2=dx*dx+dy*dy+dz*dz;
            if(rr2>support2)continue;
            const double q=max(0.,1.-sqrt(rr2)*invsupport);
            if(q<=0.)continue;
            add_mls_sample(posb,CurvedDrainedBoundaryValue,CurvedDrainedCorrectedLapBoundaryWeight*q*q*q*q);
            boundaries++;
          }
        }
        curvedlap8materials+=materials;
        curvedlap8boundaries+=boundaries;
        const unsigned samples=materials+boundaries;
        bool fallback=(samples<CurvedDrainedCorrectedLapMinSamples || samples<10);
        double coeff[10],cond=DBL_MAX;
        if(!fallback){
          fallback=!solve_mls10(ata,atb,coeff,cond);
          if(!fallback && cond>CurvedDrainedCorrectedLapConditionLimit)fallback=true;
        }
        if(fallback){
          curvedlap8fallback++;
          if(CurvedDrainedCorrectedLapFallbackMode==4){
            const double gapr=max(mindist,rtarget-r);
            const double lapgap=-shellareafactor*(pval-CurvedDrainedBoundaryValue)/gapr;
            const double oldlap=double(lapporepress[p]);
            lapporepress[p]=float(lapgap);
            curvedaffected++;
            maxabslapadd=max(maxabslapadd,fabs(lapgap-oldlap));
            maxabsheadadd=max(maxabsheadadd,fabs(lapgap-oldlap)/rhog);
          }
          continue;
        }
        const double lapmls=2.*(coeff[4]+coeff[5]+coeff[6])/(support*support);
        const double oldlap=double(lapporepress[p]);
        double lap=lapmls;
        double theta=1.;
        const bool blendlimiter=(CurvedDrainedCorrectedLaplacianLimiter==3);
        const bool positivitylimiter=(CurvedDrainedCorrectedLaplacianLimiter==1 || CurvedDrainedLimiterPreventNegative);
        if(blendlimiter){
          theta=max(0.,min(1.,CurvedDrainedLimiterBlend));
          lap=theta*lapmls+(1.-theta)*oldlap;
          curvedlap8blendlimited++;
        }
        const double limiterdt=(LastDt>ALMOSTZERO? LastDt: (SymplecticDtPre>ALMOSTZERO? SymplecticDtPre: ((PorePressureDt<DBL_MAX && PorePressureDt>ALMOSTZERO)? PorePressureDt: 0.)));
        if(positivitylimiter && diffcoef>ALMOSTZERO && limiterdt>ALMOSTZERO){
          const double gap=max(0.,pval-CurvedDrainedBoundaryValue);
          const double lapmin=-CurvedDrainedLimiterCFL*gap/(limiterdt*diffcoef);
          if(lap<lapmin){
            lap=lapmin;
            curvedlap8positivitylimited++;
          }
        }
        if(blendlimiter || positivitylimiter){
          curvedlap8limitertargets++;
          curvedlap8thetamean+=theta;
          curvedlap8thetamin=min(curvedlap8thetamin,theta);
          curvedlap8thetamax=max(curvedlap8thetamax,theta);
          curvedlap8limitedmean+=fabs(lap-lapmls);
          curvedlap8limitedmax=max(curvedlap8limitedmax,fabs(lap-lapmls));
        }
        lapporepress[p]=float(lap);
        curvedaffected++;
        curvedlap8corrected++;
        curvedlap8condcount++;
        curvedlap8condmean+=cond;
        curvedlap8condmin=min(curvedlap8condmin,cond);
        curvedlap8condmax=max(curvedlap8condmax,cond);
        curvedlap8lapmean+=lap;
        curvedlap8lapmax=max(curvedlap8lapmax,fabs(lap));
        curvedlap8replacedmean+=fabs(lap-oldlap);
        curvedlap8replacedmax=max(curvedlap8replacedmax,fabs(lap-oldlap));
        curvedlap8ratediffmax=max(curvedlap8ratediffmax,fabs(diffcoef*lap));
        maxabsdpwtop=max(maxabsdpwtop,fabs(pval-CurvedDrainedBoundaryValue));
        maxabslapadd=max(maxabslapadd,fabs(lap-oldlap));
        maxabsheadadd=max(maxabsheadadd,fabs(lap-oldlap)/rhog);
      }
      else if(CurvedDrainedBoundaryMode==6){
        // Radial-shell / FV-consistent drained prototype. The outer material
        // shell supplies a volume-averaged pressure and radius. The prescribed
        // spherical Dirichlet value defines du/dr at R, and the integrated
        // spherical flux is distributed as an explicit LapPorePress correction
        // over the same outer shell. Material pressure is never clamped.
        if(curvedshellfallback || curvedshellsinkvolume<=ALMOSTZERO){
          curvedskipped++;
          continue;
        }
        const double reff=min(rtarget,r);
        if(reff<rtarget-curvedshellwidth){
          curvedskipped++;
          continue;
        }
        lapporepress[p]+=float(curvedshelllapcorr);
        curvedaffected++;
        curvedshelltargets++;
        maxabsdpwtop=max(maxabsdpwtop,fabs((CurvedDrainedBoundaryUseExcess? excessi: porepress[p])-CurvedDrainedBoundaryValue));
        maxabslapadd=max(maxabslapadd,fabs(curvedshelllapcorr));
        maxabsheadadd=max(maxabsheadadd,fabs(curvedshelllapcorr/rhog));
      }
      else if(CurvedDrainedBoundaryMode==5){
        // Radial MLS / flux-consistent drained prototype. A local radial MLS
        // fit estimates the normal pressure gradient at the physical sphere
        // surface with the prescribed drained value as a Dirichlet constraint.
        // The resulting integrated normal flux is distributed over the
        // near-surface material shell as a LapPorePress correction. Material
        // pore pressure is never clamped.
        const tdouble3 posb=CurvedDrainedBoundaryCenter + normal*rtarget;
        const double zb=GetHydraulicElevation(posb);
        const double ub=CurvedDrainedBoundaryValue;
        const double support=max(mindist,(CurvedDrainedMLSRadiusFactor>0.? CurvedDrainedMLSRadiusFactor*double(KernelH): double(KernelH)));
        const double invsupport=(support>ALMOSTZERO? 1./support: 0.);
        double sumw=0.,sumws=0.,sumws2=0.,sumwsu=0.;
        unsigned samples=0;
        for(unsigned p3=pini;p3<pini+n;p3++)if(CODE_IsFluid(code[p3]) && velrhop[p3].w>0.f){
          if(CurvedDrainedBoundaryTargetMk>=0 && int(CODE_GetTypeValue(code[p3]))!=CurvedDrainedBoundaryTargetMk)continue;
          const tdouble3 rel3=pos[p3]-CurvedDrainedBoundaryCenter;
          const double r3=sqrt(rel3.x*rel3.x+rel3.y*rel3.y+rel3.z*rel3.z);
          if(r3<=ALMOSTZERO)continue;
          const double s=max(0.,rtarget-r3);
          if(s>support)continue;
          const double drx=pos[p3].x-posb.x;
          const double dry=pos[p3].y-posb.y;
          const double drz=pos[p3].z-posb.z;
          const double rr2=drx*drx+dry*dry+drz*drz;
          if(rr2>support*support)continue;
          const double q=1.-sqrt(rr2)*invsupport;
          if(q<=0.)continue;
          const double wab=q*q*q*q; // compact, smooth local MLS weight.
          const double vol=double(MassFluid)/double(velrhop[p3].w);
          const double weight=vol*wab;
          const double z3=GetHydraulicElevation(pos[p3]);
          const double u3=(CurvedDrainedBoundaryUseExcess? porepress[p3]-hydrostatic_linear(z3): porepress[p3]);
          sumw+=weight;
          sumws+=weight*s;
          sumws2+=weight*s*s;
          sumwsu+=weight*s*(u3-ub);
          samples++;
        }
        const double wb=max(sumw,ALMOSTZERO);
        const double m00=sumw+wb;
        const double m01=sumws*invsupport;
        const double m11=sumws2*invsupport*invsupport;
        const double tr=m00+m11;
        const double det=m00*m11-m01*m01;
        double cond=DBL_MAX;
        if(det>ALMOSTZERO && tr>0.){
          const double disc=max(0.,tr*tr-4.*det);
          const double lmax=0.5*(tr+sqrt(disc));
          const double lmin=0.5*(tr-sqrt(disc));
          if(lmin>ALMOSTZERO)cond=lmax/lmin;
        }
        bool fallback=(CurvedDrainedMLSOrder==0 || samples<3 || sumws2<=ALMOSTZERO || cond>CurvedDrainedMLSConditionLimit);
        double grad=0.;
        if(!fallback)grad=sumwsu/sumws2;
        else{
          curvedmlsfallback++;
          if(CurvedDrainedMLSFallbackMode==3){
            double ghostdist=rtarget-r;
            if(ghostdist<mindist)ghostdist=mindist;
            const tdouble3 posg=pos[p]+normal*(2.*ghostdist);
            const double drx=pos[p].x-posg.x;
            const double dry=pos[p].y-posg.y;
            const double drz=pos[p].z-posg.z;
            const double rr2=drx*drx+dry*dry+drz*drz;
            if(rr2<=double(KernelSize2) && rr2>=ALMOSTZERO){
              const float fac=fsph::GetKernel_Fac<tker>(CSP,float(rr2));
              const double dotrgrad=rr2*double(fac);
              const double zg=GetHydraulicElevation(posg);
              const double hydrog=hydrostatic_linear(zg);
              const double pwg=(CurvedDrainedBoundaryUseExcess? hydrog+CurvedDrainedBoundaryValue: CurvedDrainedBoundaryValue);
              const double lapadd=2.*voli*(porepress[p]-pwg)*dotrgrad/(rr2+ALMOSTZERO);
              const double zadd=2.*voli*(zi-zg)*dotrgrad/(rr2+ALMOSTZERO);
              lapporepress[p]+=float(lapadd);
              lapz[p]+=float(zadd);
              curvedaffected++;
              curvedmlstargets++;
              curvedmlssamples+=samples;
              maxabsdpwtop=max(maxabsdpwtop,fabs(porepress[p]-pwg));
              maxabslapadd=max(maxabslapadd,fabs(lapadd));
              maxabsheadadd=max(maxabsheadadd,fabs(lapadd/rhog+zadd));
            }
            else curvedskipped++;
            continue;
          }
          const double gap=max(mindist,rtarget-r);
          const double ui=(CurvedDrainedBoundaryUseExcess? excessi: porepress[p]);
          grad=(ui-ub)/gap;
        }
        const double area_i=voli*shellareafactor;
        StCurvedMlsFluxCorrection corr;
        corr.p=p;
        curvedmlscorrections.push_back(corr);
        curvedaffected++;
        curvedmlstargets++;
        curvedmlssamples+=samples;
        if(cond<DBL_MAX){
          curvedmlscondcount++;
          curvedmlscondmean+=cond;
          curvedmlscondmin=min(curvedmlscondmin,cond);
          curvedmlscondmax=max(curvedmlscondmax,cond);
        }
        curvedmlsgradmean+=grad;
        curvedmlsgradmax=max(curvedmlsgradmax,fabs(grad));
        curvedmlsfluxintegral+=diffcoef*grad*area_i;
        curvedmlsstoragerate-=diffcoef*grad*area_i;
        curvedmlsareaweight+=area_i;
        maxabsdpwtop=max(maxabsdpwtop,fabs((CurvedDrainedBoundaryUseExcess? excessi: porepress[p])-ub));
      }
      else if(CurvedDrainedBoundaryMode==4){
        // Paper-style boundary-particle drained Dirichlet prototype. Selected
        // boundary particles carry the prescribed hydraulic state and enter the
        // PR LapPorePress/LapZ quadrature. Material pore pressure is never
        // clamped here; Adami/MLS extrapolation is diagnostic only.
        struct StCurvedBndPair{
          const StCurvedBndHyd *b;
          double rr2;
          double dotrgrad;
          double wab;
          double pwb;
        };
        vector<StCurvedBndPair> bpair;
        double sb=0.;
        unsigned psamples=0;
        for(unsigned ib=0;ib<curvedbndselected;ib++){
          const StCurvedBndHyd &b=curvedbnd[ib];
          if(b.volume<=0.)continue;
          const double drx=pos[p].x-b.pos.x;
          const double dry=pos[p].y-b.pos.y;
          const double drz=pos[p].z-b.pos.z;
          const double rr2=drx*drx+dry*dry+drz*drz;
          if(rr2>double(KernelSize2) || rr2<ALMOSTZERO)continue;
          const float fac=fsph::GetKernel_Fac<tker>(CSP,float(rr2));
          const double dotrgrad=rr2*double(fac);
          const double wab=double(fsph::GetKernel_Wab<tker>(CSP,float(rr2)));
          const double pwb=(CurvedDrainedBoundaryUseExcess? b.hydro+CurvedDrainedBoundaryValue: CurvedDrainedBoundaryValue);
          StCurvedBndPair bp;
          bp.b=&b;
          bp.rr2=rr2;
          bp.dotrgrad=dotrgrad;
          bp.wab=wab;
          bp.pwb=pwb;
          bpair.push_back(bp);
          sb+=b.volume*wab;
        }
        double sm=0.;
        if(CurvedDrainedBoundaryWeighting==1 || CurvedDrainedBoundaryWeighting==3){
          for(unsigned p3=pini;p3<pini+n;p3++)if(CODE_IsFluid(code[p3]) && velrhop[p3].w>0.f){
            if(CurvedDrainedBoundaryTargetMk>=0 && int(CODE_GetTypeValue(code[p3]))!=CurvedDrainedBoundaryTargetMk)continue;
            const double drx=pos[p].x-pos[p3].x;
            const double dry=pos[p].y-pos[p3].y;
            const double drz=pos[p].z-pos[p3].z;
            const double rr2=drx*drx+dry*dry+drz*drz;
            if(rr2<=double(KernelSize2)){
              const double wab=double(fsph::GetKernel_Wab<tker>(CSP,float(rr2)));
              const double vol=double(MassFluid)/double(velrhop[p3].w);
              sm+=vol*wab;
            }
          }
        }
        double bscale=1.;
        if(CurvedDrainedBoundaryWeighting==1){
          const double stot=sm+sb;
          bscale=(stot>ALMOSTZERO? min(1.,1./stot): 1.);
        }
        else if(CurvedDrainedBoundaryWeighting==3){
          const double missing=max(0.,1.-sm);
          bscale=(sb>ALMOSTZERO? min(1.,missing/sb): 0.);
        }
        for(unsigned ib=0;ib<unsigned(bpair.size());ib++){
          const StCurvedBndPair &bp=bpair[ib];
          const StCurvedBndHyd &b=*bp.b;
          const double effvol=b.volume*bscale;
          if(effvol<=0.)continue;
          const double lapadd=2.*effvol*(porepress[p]-bp.pwb)*bp.dotrgrad/(bp.rr2+ALMOSTZERO);
          const double zadd=2.*effvol*(zi-b.z)*bp.dotrgrad/(bp.rr2+ALMOSTZERO);
          lapporepress[p]+=float(lapadd);
          lapz[p]+=float(zadd);
          maxabsdpwtop=max(maxabsdpwtop,fabs(porepress[p]-bp.pwb));
          maxabslapadd=max(maxabslapadd,fabs(lapadd));
          maxabsheadadd=max(maxabsheadadd,fabs(lapadd/rhog+zadd));
          psamples++;
        }
        if(psamples){
          curvedaffected++;
          curvedbndtargets++;
          curvedbndpairs+=psamples;
          if(CurvedDrainedBoundaryWeighting==1 || CurvedDrainedBoundaryWeighting==3){
            const double stot=sm+sb;
            const double bfrac=(stot>ALMOSTZERO? sb/stot: 0.);
            curvedbndweighttargets++;
            curvedbndsmmean+=sm;
            curvedbndsmean+=sb;
            curvedbndscalemean+=bscale;
            curvedbndfracmean+=bfrac;
            curvedbndsmmax=max(curvedbndsmmax,sm);
            curvedbndsmax=max(curvedbndsmax,sb);
            curvedbndscalemax=max(curvedbndscalemax,bscale);
            curvedbndscalemin=min(curvedbndscalemin,bscale);
            curvedbndfracmax=max(curvedbndfracmax,bfrac);
          }
        }
        else curvedskipped++;
      }
      else if(CurvedDrainedBoundaryMode==3){
        // Multi-sample spherical Dirichlet quadrature. The samples sit on a
        // thin exterior shell around the projected spherical boundary point.
        // They enter the same LapPorePress/LapZ operator as material pairs and
        // never overwrite material pressure.
        const double normaloffset=mindist;
        const double tanstep=(Dp>0.? 0.5*double(Dp): 0.25*double(KernelH));
        const double volscale=(Dp>0.? max(1.,double(KernelH)/double(Dp)): 1.);
        const double volsample=voli*volscale/5.;
        tdouble3 t1;
        if(fabs(normal.z)<0.9)t1=TDouble3(-normal.y,normal.x,0.);
        else t1=TDouble3(0.,-normal.z,normal.y);
        const double t1m=sqrt(t1.x*t1.x+t1.y*t1.y+t1.z*t1.z);
        if(t1m<=ALMOSTZERO){ curvedskipped++; continue; }
        t1=t1*(1./t1m);
        const tdouble3 t2=TDouble3(
          normal.y*t1.z-normal.z*t1.y,
          normal.z*t1.x-normal.x*t1.z,
          normal.x*t1.y-normal.y*t1.x);
        const double shifts[5][2]={{0.,0.},{1.,0.},{-1.,0.},{0.,1.},{0.,-1.}};
        unsigned psamples=0;
        for(unsigned is=0;is<5;is++){
          tdouble3 srel=normal*rtarget + t1*(shifts[is][0]*tanstep) + t2*(shifts[is][1]*tanstep);
          const double srm=sqrt(srel.x*srel.x+srel.y*srel.y+srel.z*srel.z);
          if(srm<=ALMOSTZERO)continue;
          const tdouble3 sdir=srel*(1./srm);
          const tdouble3 posg=CurvedDrainedBoundaryCenter + sdir*(rtarget+normaloffset);
          const double drx=pos[p].x-posg.x;
          const double dry=pos[p].y-posg.y;
          const double drz=pos[p].z-posg.z;
          const double rr2=drx*drx+dry*dry+drz*drz;
          if(rr2>double(KernelSize2) || rr2<ALMOSTZERO)continue;
          const float fac=fsph::GetKernel_Fac<tker>(CSP,float(rr2));
          const double dotrgrad=rr2*double(fac);
          const double zg=GetHydraulicElevation(posg);
          const double hydrog=hydrostatic_linear(zg);
          const double pwg=(CurvedDrainedBoundaryUseExcess? hydrog+CurvedDrainedBoundaryValue: CurvedDrainedBoundaryValue);
          const double lapadd=2.*volsample*(porepress[p]-pwg)*dotrgrad/(rr2+ALMOSTZERO);
          const double zadd=2.*volsample*(zi-zg)*dotrgrad/(rr2+ALMOSTZERO);
          lapporepress[p]+=float(lapadd);
          lapz[p]+=float(zadd);
          maxabsdpwtop=max(maxabsdpwtop,fabs(porepress[p]-pwg));
          maxabslapadd=max(maxabslapadd,fabs(lapadd));
          maxabsheadadd=max(maxabsheadadd,fabs(lapadd/rhog+zadd));
          psamples++;
        }
        if(psamples){
          curvedaffected++;
          curvedquadparticles++;
          curvedquadsamples+=psamples;
        }
        else curvedskipped++;
      }
      else{
        double ghostdist=rtarget-r;
        if(ghostdist<mindist)ghostdist=mindist;
        const tdouble3 posg=pos[p]+normal*(2.*ghostdist);
        const double drx=pos[p].x-posg.x;
        const double dry=pos[p].y-posg.y;
        const double drz=pos[p].z-posg.z;
        const double rr2=drx*drx+dry*dry+drz*drz;
        if(rr2>double(KernelSize2) || rr2<ALMOSTZERO){ curvedskipped++; continue; }
        const float fac=fsph::GetKernel_Fac<tker>(CSP,float(rr2));
        const double dotrgrad=rr2*double(fac);
        const double zg=GetHydraulicElevation(posg);
        const double hydrog=hydrostatic_linear(zg);
        double pwg=0.;
        if(CurvedDrainedBoundaryMode==1){
          // Image-ghost Dirichlet state: mirror the material-side value around
          // the prescribed boundary value. This strengthens the operator-level
          // Dirichlet influence without changing the PR governing equation.
          if(CurvedDrainedBoundaryUseExcess){
            const double excessg=2.*CurvedDrainedBoundaryValue-excessi;
            pwg=hydrog+excessg;
          }
          else pwg=2.*CurvedDrainedBoundaryValue-porepress[p];
        }
        else pwg=(CurvedDrainedBoundaryUseExcess? hydrog+CurvedDrainedBoundaryValue: CurvedDrainedBoundaryValue);
        const double lapadd=2.*voli*(porepress[p]-pwg)*dotrgrad/(rr2+ALMOSTZERO);
        const double zadd=2.*voli*(zi-zg)*dotrgrad/(rr2+ALMOSTZERO);
        lapporepress[p]+=float(lapadd);
        lapz[p]+=float(zadd);
        curvedaffected++;
        maxabsdpwtop=max(maxabsdpwtop,fabs(porepress[p]-pwg));
        maxabslapadd=max(maxabslapadd,fabs(lapadd));
        maxabsheadadd=max(maxabsheadadd,fabs(lapadd/rhog+zadd));
      }
    }
    if(CurvedDrainedBoundaryMode==5 && !curvedmlscorrections.empty()){
      const double gradavg=(curvedmlsareaweight>ALMOSTZERO? curvedmlsfluxintegral/(diffcoef*curvedmlsareaweight): 0.);
      const double lapcorr=-gradavg*shellareafactor;
      for(unsigned ic=0;ic<unsigned(curvedmlscorrections.size());ic++)
        lapporepress[curvedmlscorrections[ic].p]+=float(lapcorr);
      curvedmlslapcorrmax=fabs(lapcorr);
      maxabslapadd=max(maxabslapadd,curvedmlslapcorrmax);
      maxabsheadadd=max(maxabsheadadd,curvedmlslapcorrmax/rhog);
    }
    topaffected=curvedaffected;
  }

  if(printlog){
    Log->Printf("CPU pore-pressure boundary operator: mode=%d, TimeStep=%g, top_active=%s, bottom_active=%s, zmin=%g, zmax=%g, gap=%g, top_thickness=%g, bottom_thickness=%g, top_contrib=%u, bottom_contrib=%u, skipped=%u, max|dpw_top|=%g Pa, max|dpw_bottom|=%g Pa, max|LapP add|=%g, max|head add|=%g."
      ,PorePressureBoundaryOperator,timestep,(topactive? "True": "False"),(bottomactive? "True": "False"),zmin,zmax,gap,topthick,bottomthick,topaffected,bottomaffected,skipped,maxabsdpwtop,maxabsdpwbottom,maxabslapadd,maxabsheadadd);
    if(PorePressureBoundaryOperator==1)
      Log->Print("CPU pore-pressure boundary operator convention: top ghost enforces excess pressure = 0; bottom ghost mirrors excess pressure for zero normal hydraulic-head gradient.");
    if(PorePressureBoundaryOperator==2){
      Log->Printf("CPU hydraulic boundary-particle operator: inactive_boundary_neighbours=%u, normals_used=%u, MLS_samples=%u, MLS_fallback=%u, reconstructed_excess=[%g,%g] Pa."
        ,bndinactive,bndnormals,bndmlssamples,bndmlsfallback,bndexmin,bndexmax);
      Log->Print("CPU hydraulic boundary-particle convention: top boundary particles use excess pressure = 0; bottom no-flux boundary particles use reconstructed excess/head state, not zero total pressure gradient.");
    }
    if(PorePressureBoundaryOperator==3){
      Log->Printf("CPU curved drained pore-pressure boundary: active=%s, center=(%g,%g,%g), radius=%g, shell_thickness=%g, target_mk=%d, value=%g Pa, value_type=%s, affected=%u, skipped=%u, radius_range=[%g,%g], boundary_residual_max=%g Pa."
        ,(PorePressureCurvedDrained? "True": "False"),CurvedDrainedBoundaryCenter.x,CurvedDrainedBoundaryCenter.y,CurvedDrainedBoundaryCenter.z
        ,CurvedDrainedBoundaryRadius,(CurvedDrainedBoundaryThickness>0.? CurvedDrainedBoundaryThickness: double(KernelH))
        ,CurvedDrainedBoundaryTargetMk,CurvedDrainedBoundaryValue,(CurvedDrainedBoundaryUseExcess? "excess": "total")
        ,curvedaffected,curvedskipped,(curvedrmin==DBL_MAX? 0.: curvedrmin),curvedrmax,curvedresidualmax);
      if(CurvedDrainedBoundaryMode==0)
        Log->Print("CPU curved drained convention: first-order spherical exterior Dirichlet ghost contributes to LapPorePress/LapZ before PR rate; no post-update clamp is applied.");
      if(CurvedDrainedBoundaryMode==1)
        Log->Print("CPU curved drained convention: strengthened image Dirichlet ghost contributes to LapPorePress/LapZ before PR rate; no post-update clamp is applied.");
      if(CurvedDrainedBoundaryMode==2)
        Log->Print("CPU curved drained convention: first-order ghost contribution plus diagnostic post-update material surface clamp; mode 2 is not production.");
      if(CurvedDrainedBoundaryMode==3){
        Log->Printf("CPU curved drained quadrature: material_targets=%u, boundary_samples=%u, average_samples=%g, quadrature_volume_scale=%g."
          ,curvedquadparticles,curvedquadsamples,(curvedquadparticles? double(curvedquadsamples)/double(curvedquadparticles): 0.)
          ,(Dp>0.? max(1.,double(KernelH)/double(Dp)): 1.));
        Log->Print("CPU curved drained convention: multi-sample spherical Dirichlet boundary quadrature contributes to LapPorePress/LapZ before PR rate; no material clamp is applied.");
      }
      if(CurvedDrainedBoundaryMode==4){
        if(curvedbndweighttargets){
          curvedbndsmmean/=double(curvedbndweighttargets);
          curvedbndsmean/=double(curvedbndweighttargets);
          curvedbndscalemean/=double(curvedbndweighttargets);
          curvedbndfracmean/=double(curvedbndweighttargets);
        }
        if(curvedbndscalemin==DBL_MAX)curvedbndscalemin=0.;
        Log->Printf("CPU curved drained boundary-particle Dirichlet: selected_boundary_particles=%u, material_targets=%u, material_boundary_pairs=%u, average_pairs=%g, target_mkbound=%d, selection_tolerance=%g, prescribed_value=%g Pa, value_type=%s, AdamiDiagnostic=%s, Adami_samples=%u, Adami_fallback=%u, Adami_mean_abs_excess=%g Pa, Adami_max_abs_excess=%g Pa."
          ,curvedbndselected,curvedbndtargets,curvedbndpairs,(curvedbndtargets? double(curvedbndpairs)/double(curvedbndtargets): 0.)
          ,CurvedDrainedBoundaryTargetMkBound,(CurvedDrainedBoundarySelectionTolerance>0.? CurvedDrainedBoundarySelectionTolerance: max(double(KernelH),double(Dp)))
          ,CurvedDrainedBoundaryValue,(CurvedDrainedBoundaryUseExcess? "excess": "total"),(CurvedDrainedBoundaryAdamiDiagnostic? "True": "False")
          ,curvedbndadamisamples,curvedbndadamifallback,curvedbndadamiabsmean,curvedbndadamimaxabs);
        Log->Printf("CPU curved drained boundary-particle weighting: mode=%d, weighted_targets=%u, mean_Sm=%g, max_Sm=%g, mean_Sb=%g, max_Sb=%g, mean_boundary_fraction=%g, max_boundary_fraction=%g, mean_scale=%g, min_scale=%g, max_scale=%g."
          ,CurvedDrainedBoundaryWeighting,curvedbndweighttargets,curvedbndsmmean,curvedbndsmmax,curvedbndsmean,curvedbndsmax
          ,curvedbndfracmean,curvedbndfracmax,curvedbndscalemean,curvedbndscalemin,curvedbndscalemax);
        Log->Print("CPU curved drained convention: selected boundary particles use prescribed drained hydraulic state and contribute to LapPorePress/LapZ before PR rate; material pore pressure is not clamped and Adami/MLS extrapolation is diagnostic only.");
      }
      if(CurvedDrainedBoundaryMode==5){
        if(curvedmlstargets)curvedmlsgradmean/=double(curvedmlstargets);
        if(curvedmlscondcount)curvedmlscondmean/=double(curvedmlscondcount);
        if(curvedmlscondmin==DBL_MAX)curvedmlscondmin=0.;
        Log->Printf("CPU curved drained MLS flux correction: order=%d, targets=%u, samples=%u, average_samples=%g, fallback=%u, fallback_mode=%d, support_radius=%g, condition_limit=%g, cond_min=%g, cond_mean=%g, cond_max=%g."
          ,CurvedDrainedMLSOrder,curvedmlstargets,curvedmlssamples,(curvedmlstargets? double(curvedmlssamples)/double(curvedmlstargets): 0.)
          ,curvedmlsfallback,CurvedDrainedMLSFallbackMode,(CurvedDrainedMLSRadiusFactor>0.? CurvedDrainedMLSRadiusFactor*double(KernelH): double(KernelH))
          ,CurvedDrainedMLSConditionLimit,curvedmlscondmin,curvedmlscondmean,curvedmlscondmax);
        Log->Printf("CPU curved drained MLS flux diagnostics: TimeStep=%g, boundary_area=%g, shell_volume=%g, mean_normal_gradient=%g Pa/m, max_abs_normal_gradient=%g Pa/m, max_abs_lap_correction=%g, boundary_flux_integral=%g Pa*m3/s, storage_rate_correction=%g Pa*m3/s."
          ,timestep,curvedmlsarea,curvedmlsshellvolume,curvedmlsgradmean,curvedmlsgradmax,curvedmlslapcorrmax,curvedmlsfluxintegral,curvedmlsstoragerate);
        Log->Print("CPU curved drained convention: mode 5 uses a radial MLS Dirichlet fit to estimate the spherical normal gradient and adds only an integrated LapPorePress flux correction; material pore pressure is not clamped and selected dummy particles are not volume-counted.");
      }
      if(CurvedDrainedBoundaryMode==6){
        double pmean[4]={0.,0.,0.,0.};
        double rmean[4]={0.,0.,0.,0.};
        for(unsigned ib=0;ib<curvedshellbinmax;ib++)if(curvedshellvol[ib]>ALMOSTZERO){
          pmean[ib]=curvedshellpsum[ib]/curvedshellvol[ib];
          rmean[ib]=curvedshellrsum[ib]/curvedshellvol[ib];
        }
        Log->Printf("CPU curved drained radial-shell flux correction: TimeStep=%g, bins=%u, shell_width=%g, target_shell_particles=%u, sink_volume=%g, fallback=%u, outer_population=%u, outer_pressure_mean=%g Pa, outer_radius_mean=%g m, boundary_value=%g Pa, du_dr_R=%g Pa/m, boundary_flux_density=%g Pa*m/s, boundary_flux_integral=%g Pa*m3/s, storage_rate_correction=%g Pa*m3/s, max_abs_lap_correction=%g, flux_storage_residual=%g."
          ,timestep,curvedshellbinmax,curvedshellwidth,curvedshelltargets,curvedshellsinkvolume,curvedshellfallback,curvedshellpop[0]
          ,curvedshelloutermean,curvedshellouterrmean,CurvedDrainedBoundaryValue,curvedshellgrad,curvedshellfluxdensity
          ,curvedshellfluxintegral,curvedshellstoragerate,fabs(curvedshelllapcorr),curvedshellresidual);
        Log->Printf("CPU curved drained radial-shell bins: populations=[%u,%u,%u,%u], pressure_means=[%g,%g,%g,%g] Pa, radius_means=[%g,%g,%g,%g] m, volumes=[%g,%g,%g,%g] m3."
          ,curvedshellpop[0],curvedshellpop[1],curvedshellpop[2],curvedshellpop[3]
          ,pmean[0],pmean[1],pmean[2],pmean[3],rmean[0],rmean[1],rmean[2],rmean[3]
          ,curvedshellvol[0],curvedshellvol[1],curvedshellvol[2],curvedshellvol[3]);
        Log->Print("CPU curved drained convention: mode 6 estimates a spherical FV boundary flux from radial shell averages and distributes the integrated flux as a LapPorePress correction; material pore pressure is not clamped and no curve-fit coefficient is calibrated.");
      }
      if(CurvedDrainedBoundaryMode==7){
        Log->Printf("CPU curved drained conservative shell exchange: TimeStep=%g, shells=%u, shell_width=%g, shell_mode=%d, correction_mode=%d, min_particles=%u, corrected_particles=%u, fallback_shells=%u, min_pop=%u, max_pop=%u, total_storage=%g Pa*m3, boundary_flux=%g Pa*m3/s, target_storage_rate=%g Pa*m3/s, current_storage_rate=%g Pa*m3/s, correction_storage_rate=%g Pa*m3/s, corrected_storage_rate=%g Pa*m3/s, conservation_residual=%g Pa*m3/s, max_abs_rate_correction=%g Pa/s, max_abs_lap_correction=%g, min_pressure=%g Pa, max_pressure=%g Pa, negative_count=%u."
          ,timestep,curvedshell7count,curvedshell7width,CurvedDrainedShellMode,CurvedDrainedShellCorrectionMode,CurvedDrainedShellMinParticles
          ,curvedshell7corrected,curvedshell7fallback,curvedshell7minpop,curvedshell7maxpop,curvedshell7totalstorage
          ,curvedshell7boundaryflux,curvedshell7targetstorage,curvedshell7currentstorage,curvedshell7correctionstorage
          ,curvedshell7correctedstorage,curvedshell7conservationresidual,curvedshell7maxabsratecorr,curvedshell7maxabslapcorr
          ,curvedshell7minpressure,curvedshell7maxpressure,curvedshell7negative);
        for(unsigned k=0;k<curvedshell7count;k++){
          Log->Printf("CPU curved drained conservative shell bin: TimeStep=%g, k=%u, r_inner=%g, r_outer=%g, population=%u, effective_volume=%g m3, analytic_volume=%g m3, pressure_mean=%g Pa, radius_mean=%g m, flux_in=%g Pa*m3/s, flux_out=%g Pa*m3/s, fv_rate=%g Pa/s, current_rate=%g Pa/s, correction_rate=%g Pa/s, lap_correction=%g."
            ,timestep,k,curvedshell7edge[k],curvedshell7edge[k+1],curvedshell7pop[k],curvedshell7veff[k],curvedshell7volana[k]
            ,curvedshell7pmean[k],curvedshell7rmean[k],curvedshell7flux[k],curvedshell7flux[k+1]
            ,curvedshell7targetrate[k],curvedshell7currentrate[k],curvedshell7corrrate[k],curvedshell7lapcorr[k]);
        }
        Log->Print("CPU curved drained convention: mode 7 applies a conservative radial FV shell-average correction to LapPorePress; it does not clamp material pressure and it does not volume-count dummy boundary particles.");
      }
      if(CurvedDrainedBoundaryMode==8){
        if(curvedlap8corrected)curvedlap8lapmean/=double(curvedlap8corrected);
        if(curvedlap8corrected)curvedlap8replacedmean/=double(curvedlap8corrected);
        if(curvedlap8condcount)curvedlap8condmean/=double(curvedlap8condcount);
        if(curvedlap8limitertargets)curvedlap8thetamean/=double(curvedlap8limitertargets);
        if(curvedlap8limitertargets)curvedlap8limitedmean/=double(curvedlap8limitertargets);
        if(curvedlap8thetamin==DBL_MAX)curvedlap8thetamin=0.;
        if(curvedlap8condmin==DBL_MAX)curvedlap8condmin=0.;
        Log->Printf("CPU curved drained corrected Laplacian: TimeStep=%g, targets=%u, corrected=%u, fallback=%u, material_samples=%u, boundary_samples=%u, average_material_samples=%g, average_boundary_samples=%g, support_radius=%g, r_min_factor=%g, r_threshold=%g, boundary_weight=%g, condition_limit=%g, cond_min=%g, cond_mean=%g, cond_max=%g, mean_laplacian=%g, max_abs_laplacian=%g, mean_abs_replaced_lap=%g, max_abs_replaced_lap=%g, limiter=%d, prevent_negative=%u, limiter_dt=%g, limiter_cfl=%g, blend=%g, limiter_targets=%u, blend_limited=%u, positivity_limited=%u, theta_mean=%g, theta_min=%g, theta_max=%g, mean_abs_limiter_delta=%g, max_abs_limiter_delta=%g, max_abs_diffusion_rate=%g."
          ,timestep,curvedlap8targets,curvedlap8corrected,curvedlap8fallback,curvedlap8materials,curvedlap8boundaries
          ,(curvedlap8targets? double(curvedlap8materials)/double(curvedlap8targets): 0.)
          ,(curvedlap8targets? double(curvedlap8boundaries)/double(curvedlap8targets): 0.)
          ,curvedlap8support,CurvedDrainedCorrectedLapRMinFactor,curvedlap8rthreshold,CurvedDrainedCorrectedLapBoundaryWeight
          ,CurvedDrainedCorrectedLapConditionLimit,curvedlap8condmin,curvedlap8condmean,curvedlap8condmax
          ,curvedlap8lapmean,curvedlap8lapmax,curvedlap8replacedmean,curvedlap8replacedmax
          ,CurvedDrainedCorrectedLaplacianLimiter,(CurvedDrainedLimiterPreventNegative? 1u: 0u)
          ,(LastDt>ALMOSTZERO? LastDt: (SymplecticDtPre>ALMOSTZERO? SymplecticDtPre: ((PorePressureDt<DBL_MAX && PorePressureDt>ALMOSTZERO)? PorePressureDt: 0.))),CurvedDrainedLimiterCFL,CurvedDrainedLimiterBlend
          ,curvedlap8limitertargets,curvedlap8blendlimited,curvedlap8positivitylimited
          ,curvedlap8thetamean,curvedlap8thetamin,curvedlap8thetamax,curvedlap8limitedmean,curvedlap8limitedmax,curvedlap8ratediffmax);
        Log->Print("CPU curved drained convention: mode 8 replaces near-boundary material LapPorePress by a local quadratic MLS Laplacian with spherical Dirichlet samples; optional limiters act only on the recovered Laplacian, do not clamp material pressure, and do not volume-count dummy boundary particles.");
      }
    }
  }
  return(topaffected+bottomaffected);
}

//==============================================================================
/// Adds CPU-only hydraulic boundary contributions to PR LapPorePress/LapZ operators.
//==============================================================================
unsigned JSphCpu::ApplyPorePressureBoundaryOperator(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,const tfloat3 *boundnormal,const double *porepress
  ,float *lapporepress,float *lapz,double timestep,bool printlog)
{
       if(TKernel==KERNEL_Wendland)return(ApplyPorePressureBoundaryOperatorT<KERNEL_Wendland>(n,pini,divdata,dcell,pos,velrhop,code,boundnormal,porepress,lapporepress,lapz,timestep,printlog));
  else if(TKernel==KERNEL_Cubic)   return(ApplyPorePressureBoundaryOperatorT<KERNEL_Cubic   >(n,pini,divdata,dcell,pos,velrhop,code,boundnormal,porepress,lapporepress,lapz,timestep,printlog));
  return(0);
}

//==============================================================================
/// Computes corrected-gradient diagnostic PR operators for material particles.
//==============================================================================
template<TpKernel tker> void JSphCpu::ComputeHydroCorrectedOperatorsT(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code
  ,const double *porepress,float *divvelcorr,float *lapporepresscorr,float *lapzcorr,bool printlog)
{
  const unsigned np=pini+n;
  if(divvelcorr)memset(divvelcorr,0,sizeof(float)*np);
  if(lapporepresscorr)memset(lapporepresscorr,0,sizeof(float)*np);
  if(lapzcorr)memset(lapzcorr,0,sizeof(float)*np);
  if(!divvelcorr || !lapporepresscorr || !lapzcorr || !porepress)return;
  const double gmag=GetHydraulicGmag();
  if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for corrected-gradient PR diagnostics.");

  const bool sim2d=Simulate2D;
  const unsigned minneigh=(sim2d? 6u: 12u);
  const double detlimit=(sim2d? 1e-6: 1e-8);
  unsigned corrected=0, fallback=0;
  double detmin=DBL_MAX, detmax=-DBL_MAX;

  for(unsigned p1=pini;p1<pini+n;p1++){
    if(!CODE_IsFluid(code[p1]))continue;
    const tdouble3 posp1=pos[p1];
    const tfloat4 velrhop1=velrhop[p1];
    const tfloat3 velp1=TFloat3(velrhop1.x,velrhop1.y,velrhop1.z);
    const double pwp1=porepress[p1];
    const double zp1=GetHydraulicElevation(posp1);
    const bool rsymp1=(Symmetry && posp1.y<=KernelSize); //<vs_syymmetry>

    tmatrix3d lcorr=TMatrix3d(0);
    unsigned nneigh=0;

    const StNgSearch ngs1=nsearch::Init(dcell[p1],false,divdata);
    for(int z=ngs1.zini;z<ngs1.zfin;z++)for(int y=ngs1.yini;y<ngs1.yfin;y++){
      const tuint2 pif=nsearch::ParticleRange(y,z,ngs1,divdata);
      bool rsym=false; //<vs_syymmetry>
      for(unsigned p2=pif.x;p2<pif.y;p2++){
        if(!CODE_IsFluid(code[p2])){ rsym=false; continue; }
        const float drx=float(posp1.x-pos[p2].x);
              float dry=float(posp1.y-pos[p2].y);
        if(rsym)dry=float(posp1.y+pos[p2].y); //<vs_syymmetry>
        const float drz=float(posp1.z-pos[p2].z);
        const float rr2=drx*drx+dry*dry+drz*drz;
        if(rr2<=KernelSize2 && rr2>=ALMOSTZERO && velrhop[p2].w>0.f){
          const float fac=fsph::GetKernel_Fac<tker>(CSP,rr2);
          const double frx=double(fac*drx);
          const double fry=double(fac*dry);
          const double frz=double(fac*drz);
          const double vol2=double(MassFluid)/double(velrhop[p2].w);
          lcorr.a11+=-double(drx)*frx*vol2; lcorr.a12+=-double(drx)*fry*vol2; lcorr.a13+=-double(drx)*frz*vol2;
          lcorr.a21+=-double(dry)*frx*vol2; lcorr.a22+=-double(dry)*fry*vol2; lcorr.a23+=-double(dry)*frz*vol2;
          lcorr.a31+=-double(drz)*frx*vol2; lcorr.a32+=-double(drz)*fry*vol2; lcorr.a33+=-double(drz)*frz*vol2;
          nneigh++;
          rsym=(rsymp1 && !rsym && float(posp1.y-dry)<=KernelSize); //<vs_syymmetry>
          if(rsym)p2--;                                             //<vs_syymmetry>
        }
        else rsym=false;                                            //<vs_syymmetry>
      }
    }

    bool usecorr=false;
    double det=0.;
    tmatrix3d linv=TMatrix3d(0);
    if(nneigh>=minneigh){
      if(sim2d){
        const double a=lcorr.a11,b=lcorr.a13,c=lcorr.a31,d=lcorr.a33;
        det=a*d-b*c;
        if(fabs(det)>=detlimit){
          linv.a11= d/det; linv.a13=-b/det;
          linv.a31=-c/det; linv.a33= a/det;
          usecorr=(linv.a11==linv.a11 && linv.a13==linv.a13 && linv.a31==linv.a31 && linv.a33==linv.a33
            && fabs(linv.a11)<DBL_MAX && fabs(linv.a13)<DBL_MAX && fabs(linv.a31)<DBL_MAX && fabs(linv.a33)<DBL_MAX);
        }
      }
      else{
        det=fmath::Determinant3x3(lcorr);
        if(fabs(det)>=detlimit){
          linv=fmath::InverseMatrix3x3(lcorr,det);
          usecorr=(linv.a11==linv.a11 && linv.a12==linv.a12 && linv.a13==linv.a13
            && linv.a21==linv.a21 && linv.a22==linv.a22 && linv.a23==linv.a23
            && linv.a31==linv.a31 && linv.a32==linv.a32 && linv.a33==linv.a33
            && fabs(linv.a11)<DBL_MAX && fabs(linv.a12)<DBL_MAX && fabs(linv.a13)<DBL_MAX
            && fabs(linv.a21)<DBL_MAX && fabs(linv.a22)<DBL_MAX && fabs(linv.a23)<DBL_MAX
            && fabs(linv.a31)<DBL_MAX && fabs(linv.a32)<DBL_MAX && fabs(linv.a33)<DBL_MAX);
        }
      }
    }
    detmin=min(detmin,det);
    detmax=max(detmax,det);
    if(usecorr)corrected++;
    else fallback++;

    float divp1=0.f,lappwp1=0.f,lapzp1=0.f;
    const StNgSearch ngs2=nsearch::Init(dcell[p1],false,divdata);
    for(int z=ngs2.zini;z<ngs2.zfin;z++)for(int y=ngs2.yini;y<ngs2.yfin;y++){
      const tuint2 pif=nsearch::ParticleRange(y,z,ngs2,divdata);
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
        if(rr2<=KernelSize2 && rr2>=ALMOSTZERO && velrhop[p2].w>0.f){
          const float fac=fsph::GetKernel_Fac<tker>(CSP,rr2);
          const float frx=fac*drx,fry=fac*dry,frz=fac*drz;
          float frxc=frx,fryc=fry,frzc=frz;
          if(usecorr){
            if(sim2d){
              frxc=float(linv.a11*double(frx)+linv.a13*double(frz));
              fryc=0.f;
              frzc=float(linv.a31*double(frx)+linv.a33*double(frz));
            }
            else{
              frxc=float(linv.a11*double(frx)+linv.a12*double(fry)+linv.a13*double(frz));
              fryc=float(linv.a21*double(frx)+linv.a22*double(fry)+linv.a23*double(frz));
              frzc=float(linv.a31*double(frx)+linv.a32*double(fry)+linv.a33*double(frz));
            }
          }
          tfloat4 velrhop2=velrhop[p2];
          if(rsym)velrhop2.y=-velrhop2.y; //<vs_syymmetry>
          const float volp2=MassFluid/velrhop2.w;
          if(sim2d)divp1+=volp2*((velrhop2.x-velp1.x)*frxc+(velrhop2.z-velp1.z)*frzc);
          else divp1+=volp2*((velrhop2.x-velp1.x)*frxc+(velrhop2.y-velp1.y)*fryc+(velrhop2.z-velp1.z)*frzc);
          const float dotrgrad=(sim2d? drx*frxc+drz*frzc: drx*frxc+dry*fryc+drz*frzc);
          lappwp1+=float(2.*double(volp2)*(pwp1-porepress[p2])*double(dotrgrad)/(double(rr2)+ALMOSTZERO));
          tdouble3 posp2h=posp2;
          posp2h.y=posp2y;
          const double zp2=GetHydraulicElevation(posp2h);
          lapzp1+=2.f*volp2*float(zp1-zp2)*dotrgrad/(rr2+ALMOSTZERO);
          rsym=(rsymp1 && !rsym && float(posp1.y-dry)<=KernelSize); //<vs_syymmetry>
          if(rsym)p2--;                                             //<vs_syymmetry>
        }
        else rsym=false;                                            //<vs_syymmetry>
      }
    }
    divvelcorr[p1]=divp1;
    lapporepresscorr[p1]=lappwp1;
    lapzcorr[p1]=lapzp1;
  }

  if(printlog){
    const unsigned total=corrected+fallback;
    if(detmin==DBL_MAX)detmin=detmax=0.;
    Log->Printf("Corrected-gradient PR diagnostics on CPU: mode=%s, corrected=%u, fallback=%u, fallback_ratio=%g, det=[%g,%g], det_limit=%g, min_neighbours=%u."
      ,(sim2d? "2D_xz": "3D"),corrected,fallback,(total? double(fallback)/double(total): 0.),detmin,detmax,detlimit,minneigh);
  }
}

//==============================================================================
/// Computes corrected-gradient diagnostic PR operators for material particles.
//==============================================================================
void JSphCpu::ComputeHydroCorrectedOperators(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code
  ,const double *porepress,float *divvelcorr,float *lapporepresscorr,float *lapzcorr,bool printlog)
{
       if(TKernel==KERNEL_Wendland)ComputeHydroCorrectedOperatorsT<KERNEL_Wendland>(n,pini,divdata,dcell,pos,velrhop,code,porepress,divvelcorr,lapporepresscorr,lapzcorr,printlog);
  else if(TKernel==KERNEL_Cubic)   ComputeHydroCorrectedOperatorsT<KERNEL_Cubic   >(n,pini,divdata,dcell,pos,velrhop,code,porepress,divvelcorr,lapporepresscorr,lapzcorr,printlog);
}

//==============================================================================
/// Computes diagnostic pore-pressure Laplacian including output-only hydraulic boundary ghost values.
//==============================================================================
template<TpKernel tker> void JSphCpu::ComputeHydroLapPorePressGhostT(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code
  ,const double *porepress,const double *porepressghost,const float *porepressureboundarymode,float *lapporepressghost)const
{
  const unsigned np=pini+n;
  memset(lapporepressghost,0,sizeof(float)*np);
  if(!PorePressureBoundaryGhost || !porepress || !porepressghost || !porepressureboundarymode)return;
  const int nint=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided) if(nint>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int cp=0;cp<nint;cp++){
    const unsigned p1=pini+unsigned(cp);
    if(!CODE_IsFluid(code[p1]))continue;

    double lapp1=0.;
    const tdouble3 posp1=pos[p1];
    const double pwp1=porepress[p1];
    const bool rsymp1=(Symmetry && posp1.y<=KernelSize); //<vs_syymmetry>

    const StNgSearch ngs=nsearch::Init(dcell[p1],false,divdata);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
      bool rsym=false; //<vs_syymmetry>
      for(unsigned p2=pif.x;p2<pif.y;p2++){
        const bool p2fluid=CODE_IsFluid(code[p2]);
        const bool p2ghost=(!p2fluid && CODE_IsNormal(code[p2]) && porepressureboundarymode[p2]>0.5f);
        if(!p2fluid && !p2ghost){ rsym=false; continue; }
        const float drx=float(posp1.x-pos[p2].x);
              float dry=float(posp1.y-pos[p2].y);
        if(rsym)dry=float(posp1.y+pos[p2].y); //<vs_syymmetry>
        const float drz=float(posp1.z-pos[p2].z);
        const float rr2=drx*drx+dry*dry+drz*drz;
        if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
          const float fac=fsph::GetKernel_Fac<tker>(CSP,rr2);
          const float frx=fac*drx,fry=fac*dry,frz=fac*drz;
          const float dotrgrad=drx*frx+dry*fry+drz*frz;
          const float massp2=(p2fluid? MassFluid: MassBound);
          const float volp2=massp2/velrhop[p2].w;
          const double pwp2=(p2fluid? porepress[p2]: porepressghost[p2]);
          lapp1+=2.*double(volp2)*(pwp1-pwp2)*double(dotrgrad)/(double(rr2)+ALMOSTZERO);
          rsym=(rsymp1 && !rsym && float(posp1.y-dry)<=KernelSize); //<vs_syymmetry>
          if(rsym)p2--;                                             //<vs_syymmetry>
        }
        else rsym=false;                                            //<vs_syymmetry>
      }
    }
    lapporepressghost[p1]=float(lapp1);
  }
}

//==============================================================================
/// Computes diagnostic pore-pressure Laplacian including output-only hydraulic boundary ghost values.
//==============================================================================
void JSphCpu::ComputeHydroLapPorePressGhost(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code
  ,const double *porepress,const double *porepressghost,const float *porepressureboundarymode,float *lapporepressghost)const
{
       if(TKernel==KERNEL_Wendland)ComputeHydroLapPorePressGhostT<KERNEL_Wendland>(n,pini,divdata,dcell,pos,velrhop,code,porepress,porepressghost,porepressureboundarymode,lapporepressghost);
  else if(TKernel==KERNEL_Cubic)   ComputeHydroLapPorePressGhostT<KERNEL_Cubic   >(n,pini,divdata,dcell,pos,velrhop,code,porepress,porepressghost,porepressureboundarymode,lapporepressghost);
}

//==============================================================================
/// Computes diagnostic elevation-head Laplacian including output-only hydraulic boundary ghost values.
//==============================================================================
template<TpKernel tker> void JSphCpu::ComputeHydroLapZGhostT(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code
  ,const float *porepressureboundarymode,float *lapzghost)const
{
  const unsigned np=pini+n;
  memset(lapzghost,0,sizeof(float)*np);
  if(!PorePressureBoundaryGhost || !porepressureboundarymode)return;
  const double gmag=GetHydraulicGmag();
  if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for ghost elevation-head Laplacian.");
  const int nint=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided) if(nint>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int cp=0;cp<nint;cp++){
    const unsigned p1=pini+unsigned(cp);
    if(!CODE_IsFluid(code[p1]))continue;

    float lapp1=0;
    const tdouble3 posp1=pos[p1];
    const double zp1=GetHydraulicElevation(posp1);
    const bool rsymp1=(Symmetry && posp1.y<=KernelSize); //<vs_syymmetry>

    const StNgSearch ngs=nsearch::Init(dcell[p1],false,divdata);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
      bool rsym=false; //<vs_syymmetry>
      for(unsigned p2=pif.x;p2<pif.y;p2++){
        const bool p2fluid=CODE_IsFluid(code[p2]);
        const bool p2ghost=(!p2fluid && CODE_IsNormal(code[p2]) && porepressureboundarymode[p2]>0.5f);
        if(!p2fluid && !p2ghost){ rsym=false; continue; }
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
          const float massp2=(p2fluid? MassFluid: MassBound);
          const float volp2=massp2/velrhop[p2].w;
          tdouble3 posp2h=posp2;
          posp2h.y=posp2y;
          const double zp2=GetHydraulicElevation(posp2h);
          lapp1+=2.f*volp2*float(zp1-zp2)*dotrgrad/(rr2+ALMOSTZERO);
          rsym=(rsymp1 && !rsym && float(posp1.y-dry)<=KernelSize); //<vs_syymmetry>
          if(rsym)p2--;                                             //<vs_syymmetry>
        }
        else rsym=false;                                            //<vs_syymmetry>
      }
    }
    lapzghost[p1]=lapp1;
  }
}

//==============================================================================
/// Computes diagnostic elevation-head Laplacian including output-only hydraulic boundary ghost values.
//==============================================================================
void JSphCpu::ComputeHydroLapZGhost(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code
  ,const float *porepressureboundarymode,float *lapzghost)const
{
       if(TKernel==KERNEL_Wendland)ComputeHydroLapZGhostT<KERNEL_Wendland>(n,pini,divdata,dcell,pos,velrhop,code,porepressureboundarymode,lapzghost);
  else if(TKernel==KERNEL_Cubic)   ComputeHydroLapZGhostT<KERNEL_Cubic   >(n,pini,divdata,dcell,pos,velrhop,code,porepressureboundarymode,lapzghost);
}

//==============================================================================
/// Computes candidate pore-pressure feedback acceleration for material particles.
//==============================================================================
template<TpKernel tker> void JSphCpu::ComputePorePressureAccelT(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,const double *porepress,tfloat3 *porepressureace)const
{
  const bool excessmode=(PorePressureFeedbackMode==1);
  if(excessmode && HydraulicElevationSource && GetHydraulicGmag()<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for excess pore-pressure feedback mode.");
  const int nint=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided) if(nint>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int cp=0;cp<nint;cp++){
    const unsigned p1=pini+unsigned(cp);
    if(!CODE_IsFluid(code[p1]))continue;

    tfloat3 acep1=TFloat3(0);
    const tdouble3 posp1=pos[p1];
    const double hydro1=(excessmode? GetHydrostaticPorePressure(posp1): 0.);
    const double pwp1=porepress[p1]-hydro1;
    const double rhop1=double(velrhop[p1].w);
    if(rhop1<=0.)continue;
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
          const double rhop2=double(velrhop[p2].w);
          if(rhop2>0.){
            const double hydro2=(excessmode? GetHydrostaticPorePressure(pos[p2]): 0.);
            const double pwp2=porepress[p2]-hydro2;
            const double pterm=-double(MassFluid)*(pwp1+pwp2)/(rhop1*rhop2);
            acep1.x+=float(pterm*double(frx));
            acep1.y+=float(pterm*double(fry));
            acep1.z+=float(pterm*double(frz));
          }
          rsym=(rsymp1 && !rsym && float(posp1.y-dry)<=KernelSize); //<vs_syymmetry>
          if(rsym)p2--;                                             //<vs_syymmetry>
        }
        else rsym=false;                                            //<vs_syymmetry>
      }
    }
    porepressureace[p1]=acep1;
  }
}

//==============================================================================
/// Computes candidate pore-pressure feedback acceleration for material particles.
//==============================================================================
void JSphCpu::ComputePorePressureAccel(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,const double *porepress,tfloat3 *porepressureace)const
{
       if(TKernel==KERNEL_Wendland)ComputePorePressureAccelT<KERNEL_Wendland>(n,pini,divdata,dcell,pos,velrhop,code,porepress,porepressureace);
  else if(TKernel==KERNEL_Cubic)   ComputePorePressureAccelT<KERNEL_Cubic   >(n,pini,divdata,dcell,pos,velrhop,code,porepress,porepressureace);
  else Run_Exceptioon("Kernel unknown.");
}

//==============================================================================
/// Computes paper-style stress-pair pore-pressure momentum acceleration.
//==============================================================================
template<TpKernel tker> void JSphCpu::ComputePorePressureAccelPaperT(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,const double *porepress,tfloat3 *porepressureace)const
{
  const bool excessmode=(PorePressureFeedbackMode==1);
  if(excessmode && HydraulicElevationSource && GetHydraulicGmag()<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for paper-style pore-pressure feedback mode.");
  const int nint=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided) if(nint>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int cp=0;cp<nint;cp++){
    const unsigned p1=pini+unsigned(cp);
    if(!CODE_IsFluid(code[p1]))continue;

    tfloat3 acep1=TFloat3(0);
    const tdouble3 posp1=pos[p1];
    const double hydro1=(excessmode? GetHydrostaticPorePressure(posp1): 0.);
    const double pwp1=porepress[p1]-hydro1;
    const double rhop1=double(velrhop[p1].w);
    if(rhop1<=0.)continue;
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
          const double rhop2=double(velrhop[p2].w);
          if(rhop2>0.){
            const double hydro2=(excessmode? GetHydrostaticPorePressure(pos[p2]): 0.);
            const double pwp2=porepress[p2]-hydro2;
            const double pterm=double(MassFluid)*(pwp1+pwp2)/(rhop1*rhop2);
            acep1.x+=float(pterm*double(frx));
            acep1.y+=float(pterm*double(fry));
            acep1.z+=float(pterm*double(frz));
          }
          rsym=(rsymp1 && !rsym && float(posp1.y-dry)<=KernelSize); //<vs_syymmetry>
          if(rsym)p2--;                                             //<vs_syymmetry>
        }
        else rsym=false;                                            //<vs_syymmetry>
      }
    }
    porepressureace[p1]=acep1;
  }
}

//==============================================================================
/// Computes paper-style stress-pair pore-pressure momentum acceleration.
//==============================================================================
void JSphCpu::ComputePorePressureAccelPaper(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,const double *porepress,tfloat3 *porepressureace)const
{
       if(TKernel==KERNEL_Wendland)ComputePorePressureAccelPaperT<KERNEL_Wendland>(n,pini,divdata,dcell,pos,velrhop,code,porepress,porepressureace);
  else if(TKernel==KERNEL_Cubic)   ComputePorePressureAccelPaperT<KERNEL_Cubic   >(n,pini,divdata,dcell,pos,velrhop,code,porepress,porepressureace);
  else Run_Exceptioon("Kernel unknown.");
}

//==============================================================================
/// Computes difference-gradient pore-pressure feedback acceleration diagnostic for material particles.
//==============================================================================
template<TpKernel tker> void JSphCpu::ComputePorePressureAccelDiffT(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,const double *porepress,tfloat3 *porepressureacediff)const
{
  const bool excessmode=(PorePressureFeedbackMode==1);
  if(excessmode && HydraulicElevationSource && GetHydraulicGmag()<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for excess pore-pressure feedback difference diagnostic.");
  const int nint=int(n);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided) if(nint>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int cp=0;cp<nint;cp++){
    const unsigned p1=pini+unsigned(cp);
    if(!CODE_IsFluid(code[p1]))continue;

    tfloat3 acep1=TFloat3(0);
    const tdouble3 posp1=pos[p1];
    const double hydro1=(excessmode? GetHydrostaticPorePressure(posp1): 0.);
    const double pwp1=porepress[p1]-hydro1;
    const double rhop1=double(velrhop[p1].w);
    if(rhop1<=0.)continue;
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
          const double rhop2=double(velrhop[p2].w);
          if(rhop2>0.){
            const double hydro2=(excessmode? GetHydrostaticPorePressure(pos[p2]): 0.);
            const double pwp2=porepress[p2]-hydro2;
            const double coef=-double(MassFluid)*(pwp2-pwp1)/(rhop2*rhop1);
            acep1.x+=float(coef*double(frx));
            acep1.y+=float(coef*double(fry));
            acep1.z+=float(coef*double(frz));
          }
          rsym=(rsymp1 && !rsym && float(posp1.y-dry)<=KernelSize); //<vs_syymmetry>
          if(rsym)p2--;                                             //<vs_syymmetry>
        }
        else rsym=false;                                            //<vs_syymmetry>
      }
    }
    porepressureacediff[p1]=acep1;
  }
}

//==============================================================================
/// Computes difference-gradient pore-pressure feedback acceleration diagnostic for material particles.
//==============================================================================
void JSphCpu::ComputePorePressureAccelDiff(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,const double *porepress,tfloat3 *porepressureacediff)const
{
       if(TKernel==KERNEL_Wendland)ComputePorePressureAccelDiffT<KERNEL_Wendland>(n,pini,divdata,dcell,pos,velrhop,code,porepress,porepressureacediff);
  else if(TKernel==KERNEL_Cubic)   ComputePorePressureAccelDiffT<KERNEL_Cubic   >(n,pini,divdata,dcell,pos,velrhop,code,porepress,porepressureacediff);
  else Run_Exceptioon("Kernel unknown.");
}

//==============================================================================
/// Computes LSQ-corrected pore-pressure feedback acceleration diagnostic for material particles.
//==============================================================================
template<TpKernel tker> void JSphCpu::ComputePorePressureAccelLsqT(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,const double *porepress,tfloat3 *porepressureacelsq)const
{
  const bool excessmode=(PorePressureFeedbackMode==1);
  if(excessmode && HydraulicElevationSource && GetHydraulicGmag()<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for excess pore-pressure feedback LSQ diagnostic.");
  const double rfac=(PorePressureFeedbackLSQRadiusFactor>0.? PorePressureFeedbackLSQRadiusFactor: 1.);
  const double rrmax2=min(double(KernelSize2),double(KernelSize2)*rfac*rfac);
  const double condlimit=PorePressureFeedbackLSQConditionLimit;
  const bool fallbackdiff=(PorePressureFeedbackLSQFallback==0);
  const bool sim2d=Simulate2D;
  const unsigned minneigh=(sim2d? 4u: 6u);
  const double detlimit=1e-30;

  struct StLsqDiag{
    unsigned solved,fallback,condcount;
    double condsum,condmin,condmax;
    StLsqDiag():solved(0),fallback(0),condcount(0),condsum(0),condmin(DBL_MAX),condmax(0){}
  };
  const int nint=int(n);
  const unsigned nth=
  #ifdef OMP_USE
    (nint>OMP_LIMIT_COMPUTELIGHT? unsigned(omp_get_max_threads()): 1u);
  #else
    1u;
  #endif
  vector<StLsqDiag> diag(nth);

  #ifdef OMP_USE
    #pragma omp parallel for schedule (guided) if(nint>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int cp=0;cp<nint;cp++){
    unsigned th=0;
    #ifdef OMP_USE
      if(nint>OMP_LIMIT_COMPUTELIGHT)th=unsigned(omp_get_thread_num());
    #endif
    StLsqDiag &dg=diag[th];
    const unsigned p1=pini+unsigned(cp);
    if(!CODE_IsFluid(code[p1]))continue;

    const tdouble3 posp1=pos[p1];
    const double hydro1=(excessmode? GetHydrostaticPorePressure(posp1): 0.);
    const double pwp1=porepress[p1]-hydro1;
    const double rhop1=double(velrhop[p1].w);
    if(rhop1<=0.)continue;
    const bool rsymp1=(Symmetry && posp1.y<=KernelSize); //<vs_syymmetry>

    tmatrix3d amat=TMatrix3d(0);
    tdouble3 bvec=TDouble3(0);
    tfloat3 difface=TFloat3(0);
    unsigned nneigh=0;

    const StNgSearch ngs=nsearch::Init(dcell[p1],false,divdata);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
      bool rsym=false; //<vs_syymmetry>
      for(unsigned p2=pif.x;p2<pif.y;p2++){
        if(p2==p1 || !CODE_IsFluid(code[p2])){ rsym=false; continue; }
        const double x2=pos[p2].x;
        const double y2=(rsym? -pos[p2].y: pos[p2].y);
        const double z2=pos[p2].z;
        const float drx=float(posp1.x-x2);
              float dry=float(posp1.y-y2);
        const float drz=float(posp1.z-z2);
        const float rr2=drx*drx+dry*dry+drz*drz;
        if(double(rr2)<=rrmax2 && rr2>=ALMOSTZERO && velrhop[p2].w>0.f){
          const float fac=fsph::GetKernel_Fac<tker>(CSP,rr2);
          const float frx=fac*drx,fry=fac*dry,frz=fac*drz;
          const double rhop2=double(velrhop[p2].w);
          const tdouble3 posp2h=TDouble3(x2,y2,z2);
          const double hydro2=(excessmode? GetHydrostaticPorePressure(posp2h): 0.);
          const double pwp2=porepress[p2]-hydro2;
          const double coef=-double(MassFluid)*(pwp2-pwp1)/(rhop2*rhop1);
          difface.x+=float(coef*double(frx));
          difface.y+=float(coef*double(fry));
          difface.z+=float(coef*double(frz));

          const double wab=double(fsph::GetKernel_Wab<tker>(CSP,rr2));
          const double vol2=double(MassFluid)/rhop2;
          const double w=vol2*wab;
          if(w>0.){
            const double dx=x2-posp1.x;
            const double dy=(sim2d? 0.: y2-posp1.y);
            const double dz=z2-posp1.z;
            const double dp=pwp2-pwp1;
            amat.a11+=w*dx*dx; amat.a12+=w*dx*dy; amat.a13+=w*dx*dz;
            amat.a21+=w*dy*dx; amat.a22+=w*dy*dy; amat.a23+=w*dy*dz;
            amat.a31+=w*dz*dx; amat.a32+=w*dz*dy; amat.a33+=w*dz*dz;
            bvec.x+=w*dp*dx; bvec.y+=w*dp*dy; bvec.z+=w*dp*dz;
            nneigh++;
          }
          rsym=(rsymp1 && !rsym && float(posp1.y-dry)<=KernelSize); //<vs_syymmetry>
          if(rsym)p2--;                                             //<vs_syymmetry>
        }
        else rsym=false;                                            //<vs_syymmetry>
      }
    }

    bool solved=false;
    double cond=0.;
    tdouble3 grad=TDouble3(0);
    if(nneigh>=minneigh){
      if(sim2d){
        const double a=amat.a11,b=amat.a13,c=amat.a31,d=amat.a33;
        const double det=a*d-b*c;
        if(fabs(det)>detlimit){
          const double i11=d/det,i13=-b/det,i31=-c/det,i33=a/det;
          const double norm=sqrt(a*a+b*b+c*c+d*d);
          const double invnorm=sqrt(i11*i11+i13*i13+i31*i31+i33*i33);
          cond=norm*invnorm;
          if((condlimit<=0. || cond<=condlimit) && cond==cond){
            grad.x=i11*bvec.x+i13*bvec.z;
            grad.y=0.;
            grad.z=i31*bvec.x+i33*bvec.z;
            solved=(grad.x==grad.x && grad.z==grad.z);
          }
        }
      }
      else{
        const double det=fmath::Determinant3x3(amat);
        if(fabs(det)>detlimit){
          const tmatrix3d inv=fmath::InverseMatrix3x3(amat,det);
          const double norm=sqrt(amat.a11*amat.a11+amat.a12*amat.a12+amat.a13*amat.a13
            +amat.a21*amat.a21+amat.a22*amat.a22+amat.a23*amat.a23
            +amat.a31*amat.a31+amat.a32*amat.a32+amat.a33*amat.a33);
          const double invnorm=sqrt(inv.a11*inv.a11+inv.a12*inv.a12+inv.a13*inv.a13
            +inv.a21*inv.a21+inv.a22*inv.a22+inv.a23*inv.a23
            +inv.a31*inv.a31+inv.a32*inv.a32+inv.a33*inv.a33);
          cond=norm*invnorm;
          if((condlimit<=0. || cond<=condlimit) && cond==cond){
            grad.x=inv.a11*bvec.x+inv.a12*bvec.y+inv.a13*bvec.z;
            grad.y=inv.a21*bvec.x+inv.a22*bvec.y+inv.a23*bvec.z;
            grad.z=inv.a31*bvec.x+inv.a32*bvec.y+inv.a33*bvec.z;
            solved=(grad.x==grad.x && grad.y==grad.y && grad.z==grad.z);
          }
        }
      }
    }

    if(solved){
      porepressureacelsq[p1]=TFloat3(float(-grad.x/rhop1),float(-grad.y/rhop1),float(-grad.z/rhop1));
      dg.solved++;
      dg.condcount++;
      dg.condsum+=cond;
      dg.condmin=min(dg.condmin,cond);
      dg.condmax=max(dg.condmax,cond);
    }
    else{
      porepressureacelsq[p1]=(fallbackdiff? difface: TFloat3(0));
      dg.fallback++;
    }
  }

  unsigned solved=0,fallback=0,condcount=0;
  double condsum=0.,condmin=DBL_MAX,condmax=0.;
  for(unsigned c=0;c<nth;c++){
    solved+=diag[c].solved;
    fallback+=diag[c].fallback;
    condcount+=diag[c].condcount;
    condsum+=diag[c].condsum;
    condmin=min(condmin,diag[c].condmin);
    condmax=max(condmax,diag[c].condmax);
  }
  PorePressureFeedbackDiagLsqSolvedCount=solved;
  PorePressureFeedbackDiagLsqFallbackCount=fallback;
  PorePressureFeedbackDiagLsqCondMin=(condmin<DBL_MAX? condmin: 0.);
  PorePressureFeedbackDiagLsqCondMax=condmax;
  PorePressureFeedbackDiagLsqCondMean=(condcount? condsum/double(condcount): 0.);
}

//==============================================================================
/// Computes LSQ-corrected pore-pressure feedback acceleration diagnostic for material particles.
//==============================================================================
void JSphCpu::ComputePorePressureAccelLsq(unsigned n,unsigned pini
  ,StDivDataCpu divdata,const unsigned *dcell,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code,const double *porepress,tfloat3 *porepressureacelsq)const
{
       if(TKernel==KERNEL_Wendland)ComputePorePressureAccelLsqT<KERNEL_Wendland>(n,pini,divdata,dcell,pos,velrhop,code,porepress,porepressureacelsq);
  else if(TKernel==KERNEL_Cubic)   ComputePorePressureAccelLsqT<KERNEL_Cubic   >(n,pini,divdata,dcell,pos,velrhop,code,porepress,porepressureacelsq);
  else Run_Exceptioon("Kernel unknown.");
}

//==============================================================================
/// Adds pore-pressure feedback acceleration to material particles.
//==============================================================================
void JSphCpu::ApplyPorePressureFeedback(unsigned n,unsigned pini,const typecode *code,const tdouble3 *pos,const tfloat3 *porepressureace,const tfloat3 *porepressureacediff,tfloat3 *porepressurefeedbackused,tfloat3 *ace)const
{
  const tfloat3 *porepressurefeedbackace=(PorePressureFeedbackOperator==0 || PorePressureFeedbackOperator==3? porepressureace: porepressureacediff);
  if(!porepressurefeedbackace)Run_Exceptioon("Selected pore-pressure feedback operator has no acceleration array.");
  ResetPorePressureFeedbackDiagnostics();
  const double feedbackfactor=GetPorePressureFeedbackFactor(TimeStep);
  PorePressureFeedbackDiagFactor=feedbackfactor;
  const int nint=int(n);
  if(feedbackfactor<=0.){
    if(porepressurefeedbackused){
      #ifdef OMP_USE
        #pragma omp parallel for schedule (static) if(nint>OMP_LIMIT_COMPUTELIGHT)
      #endif
      for(int cp=0;cp<nint;cp++){
        const unsigned p=pini+unsigned(cp);
        if(CODE_IsFluid(code[p]))porepressurefeedbackused[p]=TFloat3(0);
      }
    }
    return;
  }
  const bool userelax=(PorePressureFeedbackRelaxation>0. && PorePressureFeedbackRelaxation<1. && porepressurefeedbackused);
  const bool useabscap=((PorePressureFeedbackLimiterMode==1 || PorePressureFeedbackLimiterMode==3) && PorePressureFeedbackMaxAccel>0.);
  const bool useratiocap=((PorePressureFeedbackLimiterMode==2 || PorePressureFeedbackLimiterMode==3) && PorePressureFeedbackMaxAccelRatio>0.);
  const double confref=max(ConfiningStressDiagMaxAccel,0.);
  const double alpha=PorePressureFeedbackRelaxation;
  const double eps=1e-30;

  struct StFbDiag{
    unsigned applied,skippedclass,limited,relaxed;
    double rawsum,usedsum,rawmax,usedmax,premax,ratiomax,capmin,lateralmax,capmax,interiormax;
    StFbDiag():applied(0),skippedclass(0),limited(0),relaxed(0),rawsum(0),usedsum(0),rawmax(0),usedmax(0),premax(0),ratiomax(0),capmin(DBL_MAX),lateralmax(0),capmax(0),interiormax(0){}
  };
  const unsigned nth=
  #ifdef OMP_USE
    (nint>OMP_LIMIT_COMPUTELIGHT? unsigned(omp_get_max_threads()): 1u);
  #else
    1u;
  #endif
  vector<StFbDiag> diag(nth);
  #ifdef OMP_USE
    #pragma omp parallel for schedule (static) if(nint>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int cp=0;cp<nint;cp++){
    unsigned th=0;
    #ifdef OMP_USE
      if(nint>OMP_LIMIT_COMPUTELIGHT)th=unsigned(omp_get_thread_num());
    #endif
    StFbDiag &dg=diag[th];
    const unsigned p=pini+unsigned(cp);
    if(CODE_IsFluid(code[p])){
      int cls=0;
      if(PorePressureFeedbackUseClassFilter){
        cls=(ConfiningStressGeometry==1 && pos? GetConfiningStressCylinderClass(pos[p]): 0);
        bool allowed=true;
        if(cls==6)allowed=false;
        if(PorePressureFeedbackInteriorOnly)allowed=(cls==1);
        else{
          if(PorePressureFeedbackExcludeCaps && (cls==3 || cls==4))allowed=false;
          if(PorePressureFeedbackExcludeEdges && cls==5)allowed=false;
          if(PorePressureFeedbackExcludeConfinementTargets && FlexibleConfiningStress && ConfiningStressUseLateralSelector && IsFlexibleConfiningStressTarget(code[p]) && cls==2)allowed=false;
        }
        if(!allowed){
          if(porepressurefeedbackused)porepressurefeedbackused[p]=TFloat3(0);
          dg.skippedclass++;
          continue;
        }
      }
      const tfloat3 raw=TFloat3(float(double(porepressurefeedbackace[p].x)*feedbackfactor)
        ,float(double(porepressurefeedbackace[p].y)*feedbackfactor)
        ,float(double(porepressurefeedbackace[p].z)*feedbackfactor));
      const double rawmag=sqrt(double(raw.x)*double(raw.x)+double(raw.y)*double(raw.y)+double(raw.z)*double(raw.z));
      tfloat3 used=raw;
      if(userelax){
        const tfloat3 old=porepressurefeedbackused[p];
        used.x=float(double(old.x)+alpha*(double(raw.x)-double(old.x)));
        used.y=float(double(old.y)+alpha*(double(raw.y)-double(old.y)));
        used.z=float(double(old.z)+alpha*(double(raw.z)-double(old.z)));
        dg.relaxed++;
      }
      double usedmag=sqrt(double(used.x)*double(used.x)+double(used.y)*double(used.y)+double(used.z)*double(used.z));
      const double premag=sqrt(double(ace[p].x)*double(ace[p].x)+double(ace[p].y)*double(ace[p].y)+double(ace[p].z)*double(ace[p].z));
      double cap=DBL_MAX;
      if(useabscap)cap=min(cap,PorePressureFeedbackMaxAccel);
      if(useratiocap){
        const double ref=max(max(premag,confref),eps);
        cap=min(cap,PorePressureFeedbackMaxAccelRatio*ref);
      }
      if(cap<DBL_MAX)dg.capmin=min(dg.capmin,cap);
      if(usedmag>cap && cap>=0.){
        const double s=(usedmag>eps? cap/usedmag: 0.);
        used.x=float(double(used.x)*s);
        used.y=float(double(used.y)*s);
        used.z=float(double(used.z)*s);
        usedmag=cap;
        dg.limited++;
      }
      if(porepressurefeedbackused)porepressurefeedbackused[p]=used;
      ace[p].x+=used.x;
      ace[p].y+=used.y;
      ace[p].z+=used.z;

      dg.applied++;
      dg.rawsum+=rawmag;
      dg.usedsum+=usedmag;
      dg.rawmax=max(dg.rawmax,rawmag);
      dg.usedmax=max(dg.usedmax,usedmag);
      dg.premax=max(dg.premax,premag);
      const double ratio=usedmag/max(max(premag,confref),eps);
      dg.ratiomax=max(dg.ratiomax,ratio);
      if(ConfiningStressGeometry==1 && pos){
        if(!cls)cls=GetConfiningStressCylinderClass(pos[p]);
        if(cls==2)dg.lateralmax=max(dg.lateralmax,usedmag);
        else if(cls==3 || cls==4 || cls==5)dg.capmax=max(dg.capmax,usedmag);
        else if(cls==1)dg.interiormax=max(dg.interiormax,usedmag);
      }
    }
  }
  unsigned applied=0,skippedclass=0,limited=0,relaxed=0;
  double rawsum=0.,usedsum=0.,rawmax=0.,usedmax=0.,premax=0.,ratiomax=0.,capmin=DBL_MAX,lateralmax=0.,capmax=0.,interiormax=0.;
  for(unsigned c=0;c<nth;c++){
    applied+=diag[c].applied;
    skippedclass+=diag[c].skippedclass;
    limited+=diag[c].limited;
    relaxed+=diag[c].relaxed;
    rawsum+=diag[c].rawsum;
    usedsum+=diag[c].usedsum;
    rawmax=max(rawmax,diag[c].rawmax);
    usedmax=max(usedmax,diag[c].usedmax);
    premax=max(premax,diag[c].premax);
    ratiomax=max(ratiomax,diag[c].ratiomax);
    capmin=min(capmin,diag[c].capmin);
    lateralmax=max(lateralmax,diag[c].lateralmax);
    capmax=max(capmax,diag[c].capmax);
    interiormax=max(interiormax,diag[c].interiormax);
  }
  PorePressureFeedbackDiagAppliedCount=applied;
  PorePressureFeedbackDiagSkippedClassCount=skippedclass;
  PorePressureFeedbackDiagLimitedCount=limited;
  PorePressureFeedbackDiagRelaxedCount=relaxed;
  PorePressureFeedbackDiagRawMax=rawmax;
  PorePressureFeedbackDiagRawMean=(applied? rawsum/double(applied): 0.);
  PorePressureFeedbackDiagUsedMax=usedmax;
  PorePressureFeedbackDiagUsedMean=(applied? usedsum/double(applied): 0.);
  PorePressureFeedbackDiagPreMax=premax;
  PorePressureFeedbackDiagRatioMax=ratiomax;
  PorePressureFeedbackDiagCapValueMin=(capmin<DBL_MAX? capmin: 0.);
  PorePressureFeedbackDiagConfiningRef=confref;
  PorePressureFeedbackDiagClassLateralMax=lateralmax;
  PorePressureFeedbackDiagClassCapMax=capmax;
  PorePressureFeedbackDiagClassInteriorMax=interiormax;
}

//==============================================================================
/// Applies opt-in top/bottom cap-normal hydrostatic support for triaxial staging.
//==============================================================================
void JSphCpu::ApplyCapConfiningStress(unsigned n,unsigned pini,const typecode *code,const tdouble3 *pos,const tfloat4 *velrhop,tfloat3 *ace)const
{
  if(!CapConfiningStress || !ace)return;
  if(!code || !pos || !velrhop)Run_Exceptioon("Pointers without data for cap confining stress.");
  ResetCapConfiningStressDiagnostics();
  const double p0=GetCapConfiningStressP0(TimeStep);
  CapConfiningStressDiagP0Eff=p0;
  if(p0<=0.)return;
  if(ConfiningStressGeometry!=1)Run_Exceptioon("CapConfiningStress requires ConfiningStressGeometry=1.");

  unsigned topcount=0,bottomcount=0,edgeskip=0;
  for(unsigned cp=0;cp<n;cp++){
    const unsigned p=pini+cp;
    const typecode c=code[p];
    if(CODE_IsNormal(c) && CODE_IsFluid(c) && !CODE_IsFluidInout(c) && !CODE_IsFloating(c)){
      const int mk=int(CODE_GetTypeValue(c));
      const int cls=GetConfiningStressCylinderClass(pos[p]);
      if(cls==3 && (CapConfiningStressTopMk<0 || mk==CapConfiningStressTopMk))topcount++;
      else if(cls==4 && (CapConfiningStressBottomMk<0 || mk==CapConfiningStressBottomMk))bottomcount++;
      else if(cls==5)edgeskip++;
    }
  }

  const double area=PI*ConfiningStressCylinderRadius*ConfiningStressCylinderRadius;
  const double topforce=(topcount? p0*area: 0.);
  const double bottomforce=(bottomcount? p0*area: 0.);
  const double topacc=(topcount && MassFluid>0.? topforce/(double(MassFluid)*double(topcount)): 0.);
  const double bottomacc=(bottomcount && MassFluid>0.? bottomforce/(double(MassFluid)*double(bottomcount)): 0.);
  const tdouble3 ax=CapConfiningStressAxis;
  double netx=0.,nety=0.,netz=0.,absforce=0.;
  double topasum=0.,bottomasum=0.,topamax=0.,bottomamax=0.;

  for(unsigned cp=0;cp<n;cp++){
    const unsigned p=pini+cp;
    const typecode c=code[p];
    if(CODE_IsNormal(c) && CODE_IsFluid(c) && !CODE_IsFluidInout(c) && !CODE_IsFloating(c)){
      const int mk=int(CODE_GetTypeValue(c));
      const int cls=GetConfiningStressCylinderClass(pos[p]);
      bool istop=false,isbottom=false;
      if(cls==3 && (CapConfiningStressTopMk<0 || mk==CapConfiningStressTopMk))istop=true;
      else if(cls==4 && (CapConfiningStressBottomMk<0 || mk==CapConfiningStressBottomMk))isbottom=true;
      if(istop || isbottom){
        const double amag=(istop? topacc: bottomacc);
        const double s=(istop? -1.: 1.);
        const tfloat3 adda=TFloat3(float(s*amag*ax.x),float(s*amag*ax.y),float(s*amag*ax.z));
        ace[p].x+=adda.x;
        ace[p].y+=adda.y;
        ace[p].z+=adda.z;
        const double fx=double(MassFluid)*double(adda.x);
        const double fy=double(MassFluid)*double(adda.y);
        const double fz=double(MassFluid)*double(adda.z);
        netx+=fx; nety+=fy; netz+=fz;
        const double fmag=sqrt(fx*fx+fy*fy+fz*fz);
        absforce+=fmag;
        if(istop){ topasum+=amag; topamax=max(topamax,amag); }
        else{ bottomasum+=amag; bottomamax=max(bottomamax,amag); }
      }
    }
  }

  const double netmag=sqrt(netx*netx+nety*nety+netz*netz);
  const unsigned count=topcount+bottomcount;
  CapConfiningStressDiagTopCount=topcount;
  CapConfiningStressDiagBottomCount=bottomcount;
  CapConfiningStressDiagEdgeSkippedCount=edgeskip;
  CapConfiningStressDiagTopAccelMean=(topcount? topasum/double(topcount): 0.);
  CapConfiningStressDiagBottomAccelMean=(bottomcount? bottomasum/double(bottomcount): 0.);
  CapConfiningStressDiagTopAccelMax=topamax;
  CapConfiningStressDiagBottomAccelMax=bottomamax;
  CapConfiningStressDiagNetForce=TDouble3(netx,nety,netz);
  CapConfiningStressDiagTotalAbsForce=absforce;
  CapConfiningStressDiagComAccel=(count? netmag/(double(MassFluid)*double(count)): 0.);
  CapConfiningStressDiagSymResidual=(absforce>0.? netmag/absforce: 0.);
}

//==============================================================================
/// Computes diagnostic ghost pore pressure for simple geometric hydraulic boundary modes.
//==============================================================================
unsigned JSphCpu::ComputePorePressureBoundaryGhost(unsigned n,unsigned pini,const tdouble3 *pos,const typecode *code,const double *porepress
  ,double *porepressghost,double *excessporepressghost,float *porepressureboundarymode,double timestep,const char *stage,bool printlog)const
{
  if(!HydromechCoupling || PorePressureModel!=1 || !PorePressureBoundaryGhost)return(0);
  if(!pos || !code || !porepress || !porepressghost || !excessporepressghost || !porepressureboundarymode)
    Run_Exceptioon("Pointers without data for pore-pressure boundary ghost diagnostics.");
  const double gmag=GetHydraulicGmag();
  if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for pore-pressure boundary ghost diagnostics.");
  const unsigned np=pini+n;
  memset(porepressghost,0,sizeof(double)*np);
  memset(excessporepressghost,0,sizeof(double)*np);
  memset(porepressureboundarymode,0,sizeof(float)*np);

  unsigned npmat=0;
  double zmin=DBL_MAX,zmax=-DBL_MAX;
  for(unsigned p=pini;p<pini+n;p++)if(CODE_IsNormal(code[p]) && CODE_IsFluid(code[p])){
    const double z=GetHydraulicElevation(pos[p]);
    zmin=min(zmin,z);
    zmax=max(zmax,z);
    npmat++;
  }
  if(!npmat){
    if(printlog)Log->PrintWarning("Pore-pressure boundary ghost diagnostics found no material particles.");
    return(0);
  }

  const bool topactive=(PorePressureTopDrained && timestep>=PorePressureTopDrainedStartTime);
  const double topthick=(PorePressureDrainThickness>0.f? double(PorePressureDrainThickness): double(KernelH));
  const double bottomthick=(PorePressureBottomNoFluxThickness>0.f? double(PorePressureBottomNoFluxThickness): double(KernelH));
  const double topthreshold=zmax-topthick;
  const double bottomthreshold=zmin+bottomthick;
  const double zrefmin=bottomthreshold;
  const double zrefmax=zmin+2.*bottomthick;

  unsigned refcount=0;
  double refexcesssum=0.;
  for(unsigned p=pini;p<pini+n;p++)if(CODE_IsNormal(code[p]) && CODE_IsFluid(code[p])){
    const double z=GetHydraulicElevation(pos[p]);
    if(z>zrefmin && z<=zrefmax){
      const double hydro=GetHydrostaticPorePressure(pos[p]);
      refexcesssum+=porepress[p]-hydro;
      refcount++;
    }
  }
  const double nofluxexcess=(refcount? refexcesssum/double(refcount): 0.);

  unsigned countdrained=0,countnoflux=0,countinactive=0;
  unsigned countdrainedbound=0,countnofluxbound=0,countinactivebound=0;
  unsigned countdrainedmat=0,countnofluxmat=0,countinactivemat=0;
  double pwminmode1=DBL_MAX,pwmaxmode1=-DBL_MAX,exminmode1=DBL_MAX,exmaxmode1=-DBL_MAX;
  double pwminmode2=DBL_MAX,pwmaxmode2=-DBL_MAX,exminmode2=DBL_MAX,exmaxmode2=-DBL_MAX;

  for(unsigned p=pini;p<pini+n;p++)if(CODE_IsNormal(code[p])){
    const bool ismat=CODE_IsFluid(code[p]);
    const double z=GetHydraulicElevation(pos[p]);
    int mode=0;
    if(PorePressureBottomNoFlux && z<=bottomthreshold)mode=2;
    if(topactive && z>=topthreshold)mode=1; //-Drained overrides no-flux if layers touch.

    const double hydro=GetHydrostaticPorePressure(pos[p]);
    double excessghost=0.;
    if(mode==1)excessghost=0.;
    else if(mode==2)excessghost=nofluxexcess;
    else excessghost=0.;

    const double pwghost=(mode? hydro+excessghost: 0.);
    porepressureboundarymode[p]=float(mode);
    porepressghost[p]=pwghost;
    excessporepressghost[p]=excessghost;

    if(mode==1){
      countdrained++;
      if(ismat)countdrainedmat++; else countdrainedbound++;
      pwminmode1=min(pwminmode1,pwghost); pwmaxmode1=max(pwmaxmode1,pwghost);
      exminmode1=min(exminmode1,excessghost); exmaxmode1=max(exmaxmode1,excessghost);
    }
    else if(mode==2){
      countnoflux++;
      if(ismat)countnofluxmat++; else countnofluxbound++;
      pwminmode2=min(pwminmode2,pwghost); pwmaxmode2=max(pwmaxmode2,pwghost);
      exminmode2=min(exminmode2,excessghost); exmaxmode2=max(exmaxmode2,excessghost);
    }
    else{
      countinactive++;
      if(ismat)countinactivemat++; else countinactivebound++;
    }
  }

  if(!countdrained){ pwminmode1=pwmaxmode1=exminmode1=exmaxmode1=0.; }
  if(!countnoflux){ pwminmode2=pwmaxmode2=exminmode2=exmaxmode2=0.; }
  if(printlog){
    Log->Printf("Pore-pressure boundary ghost diagnostics on CPU (%s): TimeStep=%g, top_active=%s, zmin_material=%g, zmax_material=%g, top_threshold=%g, bottom_threshold=%g, bottom_reference=[%g,%g], reference_count=%u, reference_excess_mean=%g Pa."
      ,(stage? stage: "unknown"),timestep,(topactive? "True": "False"),zmin,zmax,topthreshold,bottomthreshold,zrefmin,zrefmax,refcount,nofluxexcess);
    Log->Printf("Pore-pressure boundary ghost modes: drained=%u (boundary=%u, material=%u), noflux=%u (boundary=%u, material=%u), inactive=%u (boundary=%u, material=%u)."
      ,countdrained,countdrainedbound,countdrainedmat,countnoflux,countnofluxbound,countnofluxmat,countinactive,countinactivebound,countinactivemat);
    Log->Printf("Pore-pressure ghost values: drained PorePress=[%g,%g] Pa, drained Excess=[%g,%g] Pa; noflux PorePress=[%g,%g] Pa, noflux Excess=[%g,%g] Pa."
      ,pwminmode1,pwmaxmode1,exminmode1,exmaxmode1,pwminmode2,pwmaxmode2,exminmode2,exmaxmode2);
    if(PorePressureBottomNoFlux && !refcount)
      Log->PrintWarning("Pore-pressure boundary ghost no-flux diagnostic used zero excess because the reference material layer was empty.");
    Log->Print("Pore-pressure boundary ghost diagnostics are output-only and are not used by PR rate, feedback, Shepard, or boundary corrections.");
  }
  return(countdrained+countnoflux);
}

//==============================================================================
/// Applies hydromechanical kinematic damping to material particles.
//==============================================================================
unsigned JSphCpu::ApplyHydromechDamping(unsigned n,unsigned pini,const tfloat4 *velrhop,const typecode *code,tfloat3 *ace,bool printlog)const
{
  if(!HydromechCoupling || PorePressureModel!=1 || !PorePressureFeedback || !HydromechDamping || HydromechDampingCoef<=0.f || !ace)return(0);
  if(!velrhop || !code)Run_Exceptioon("Pointers without data for hydromechanical damping.");
  if(TimeStep<HydromechDampingStartTime)return(0);
  if(HydromechDampingEndTime>HydromechDampingStartTime && TimeStep>HydromechDampingEndTime)return(0);
  const double coef=double(HydromechDampingCoef);
  unsigned affected=0;
  double amin=DBL_MAX,amax=0.;
  for(int cp=0;cp<int(n);cp++){
    const unsigned p=pini+unsigned(cp);
    if(CODE_IsFluid(code[p])){
      const double ax=-coef*double(velrhop[p].x);
      const double ay=-coef*double(velrhop[p].y);
      const double az=-coef*double(velrhop[p].z);
      ace[p].x+=float(ax);
      ace[p].y+=float(ay);
      ace[p].z+=float(az);
      const double amag=sqrt(ax*ax+ay*ay+az*az);
      amin=min(amin,amag);
      amax=max(amax,amag);
      affected++;
    }
  }
  if(affected==0)amin=0.;
  if(printlog && affected && amax>0.){
    Log->Printf("Hydromechanical damping activated at TimeStep=%g: coef=%g 1/s, start=%g, end=%g, affected=%u/%u, acceleration magnitude range=[%g,%g] m/s2."
      ,TimeStep,HydromechDampingCoef,HydromechDampingStartTime,HydromechDampingEndTime,affected,n,amin,amax);
  }
  return(amax>0.? affected: 0);
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
/// Small CPU-only Modified Cam Clay helper for the SPH constitutive branch.
/// The helper keeps the M2/M3a convention internally: compression is positive.
/// The production Sigmac tensor uses the opposite sign, so all components are
/// sign-flipped at the branch boundary only.
//==============================================================================
struct StMccCpuTensor{
  double xx,yy,zz,xy,yz,xz;
};

static double MccCpuMax(double a,double b){ return(a>b? a: b); }
static double MccCpuMin(double a,double b){ return(a<b? a: b); }

static StMccCpuTensor MccCpuTensorZero(){
  StMccCpuTensor v={0.,0.,0.,0.,0.,0.};
  return(v);
}

static StMccCpuTensor MccCpuTensorEye(double p){
  StMccCpuTensor v={p,p,p,0.,0.,0.};
  return(v);
}

static StMccCpuTensor MccCpuTensorAdd(const StMccCpuTensor &a,const StMccCpuTensor &b){
  StMccCpuTensor v={a.xx+b.xx,a.yy+b.yy,a.zz+b.zz,a.xy+b.xy,a.yz+b.yz,a.xz+b.xz};
  return(v);
}

static StMccCpuTensor MccCpuTensorScale(const StMccCpuTensor &a,double s){
  StMccCpuTensor v={a.xx*s,a.yy*s,a.zz*s,a.xy*s,a.yz*s,a.xz*s};
  return(v);
}

static double MccCpuTrace(const StMccCpuTensor &a){ return(a.xx+a.yy+a.zz); }

static StMccCpuTensor MccCpuDeviator(const StMccCpuTensor &a){
  const double p=MccCpuTrace(a)/3.;
  StMccCpuTensor v={a.xx-p,a.yy-p,a.zz-p,a.xy,a.yz,a.xz};
  return(v);
}

static double MccCpuDot(const StMccCpuTensor &a,const StMccCpuTensor &b){
  return(a.xx*b.xx+a.yy*b.yy+a.zz*b.zz+2.*(a.xy*b.xy+a.yz*b.yz+a.xz*b.xz));
}

static void MccCpuInvariants(const StMccCpuTensor &s,double &p,double &q){
  p=MccCpuTrace(s)/3.;
  const StMccCpuTensor dev=MccCpuDeviator(s);
  const double j2=0.5*MccCpuDot(dev,dev);
  q=sqrt(MccCpuMax(0.,3.*j2));
}

static StMccCpuTensor MccCpuFromSigmac(const tsymatrix3f &sig){
  StMccCpuTensor v={-double(sig.xx),-double(sig.yy),-double(sig.zz),-double(sig.xy),-double(sig.yz),-double(sig.xz)};
  return(v);
}

static tsymatrix3f MccCpuToSigmac(const StMccCpuTensor &s){
  tsymatrix3f sig;
  sig.xx=float(-s.xx); sig.yy=float(-s.yy); sig.zz=float(-s.zz);
  sig.xy=float(-s.xy); sig.yz=float(-s.yz); sig.xz=float(-s.xz);
  return(sig);
}

static double MccCpuYield(double p,double q,double pc,double m){
  return(q*q+m*m*p*(p-pc));
}

static double MccCpuNorm4(const std::array<double,4> &v){
  double s=0.;
  for(unsigned c=0;c<4;c++)s+=v[c]*v[c];
  return(sqrt(s));
}

static std::array<double,4> MccCpuResidual4(const std::array<double,4> &x,double ptr,double qtr
  ,double pcold,double eold,double bulk,double shear,double m,double lambda,double kappa)
{
  const double p=x[0],q=x[1],pc=x[2],dl=x[3];
  const double a=m*m;
  const double h=(1.+eold)/(lambda-kappa);
  const double dfdp=a*(2.*p-pc);
  const double dfdq=2.*q;
  const double depv=dl*dfdp;
  const double expo=MccCpuMax(-60.,MccCpuMin(60.,h*depv));
  const double pchard=pcold*exp(expo);
  return(std::array<double,4>{{p-ptr+bulk*dl*dfdp,q-qtr+3.*shear*dl*dfdq,pc-pchard,MccCpuYield(p,q,pc,m)}});
}

static std::array<std::array<double,4>,4> MccCpuNumericJacobian(const std::array<double,4> &x,double ptr,double qtr
  ,double pcold,double eold,double bulk,double shear,double m,double lambda,double kappa)
{
  const std::array<double,4> base=MccCpuResidual4(x,ptr,qtr,pcold,eold,bulk,shear,m,lambda,kappa);
  std::array<std::array<double,4>,4> jac;
  for(unsigned r=0;r<4;r++)for(unsigned c=0;c<4;c++)jac[r][c]=0.;
  for(unsigned c=0;c<4;c++){
    const double step=1.e-6*MccCpuMax(1.,fabs(x[c]));
    std::array<double,4> xp=x;
    xp[c]+=step;
    const std::array<double,4> rp=MccCpuResidual4(xp,ptr,qtr,pcold,eold,bulk,shear,m,lambda,kappa);
    for(unsigned r=0;r<4;r++)jac[r][c]=(rp[r]-base[r])/step;
  }
  return(jac);
}

static bool MccCpuSolve4(std::array<std::array<double,4>,4> a,const std::array<double,4> &b,std::array<double,4> &x){
  std::array<std::array<double,5>,4> m;
  for(unsigned r=0;r<4;r++){
    for(unsigned c=0;c<4;c++)m[r][c]=a[r][c];
    m[r][4]=b[r];
  }
  for(unsigned col=0;col<4;col++){
    unsigned pivot=col;
    for(unsigned r=col+1;r<4;r++)if(fabs(m[r][col])>fabs(m[pivot][col]))pivot=r;
    if(fabs(m[pivot][col])<1.e-18)return(false);
    if(pivot!=col)std::swap(m[pivot],m[col]);
    const double piv=m[col][col];
    for(unsigned c=col;c<5;c++)m[col][c]/=piv;
    for(unsigned r=0;r<4;r++){
      if(r==col)continue;
      const double fac=m[r][col];
      if(fac==0.)continue;
      for(unsigned c=col;c<5;c++)m[r][c]-=fac*m[col][c];
    }
  }
  for(unsigned r=0;r<4;r++)x[r]=m[r][4];
  return(true);
}

static std::array<double,4> MccCpuInitialPlasticGuess(double ptr,double qtr,double pcold,double bulk,double shear,double m,double tensioncutoff){
  const double ftr=MccCpuYield(ptr,qtr,pcold,m);
  const double denom=MccCpuMax(bulk*m*m+6.*shear,1.);
  double dl=MccCpuMax(0.,ftr/(denom*MccCpuMax(fabs(ptr)+fabs(qtr)+fabs(pcold),1.)));
  dl=MccCpuMin(dl,1.e-2);
  const double q=MccCpuMax(0.,qtr/(1.+6.*shear*dl));
  const double p=MccCpuMax(tensioncutoff,MccCpuMin(MccCpuMax(ptr,tensioncutoff),pcold*0.999));
  const double pc=MccCpuMax(pcold,p+tensioncutoff);
  return(std::array<double,4>{{p,q,pc,MccCpuMax(dl,1.e-12)}});
}

static unsigned MccCpuLineCandidateRejectReason(const StSoilCte &soilcte,const std::array<double,4> &cand){
  const double tension=double(soilcte.MccTensionCutoff);
  bool finite=true;
  for(unsigned c=0;c<4;c++)if(!std::isfinite(cand[c]))finite=false;
  if(!finite)return(5);
  if(cand[0]<=tension)return(1);
  if(cand[1]<0.)return(2);
  if(cand[2]<=tension)return(3);
  const bool enforce=(!soilcte.MccAdmissibleLineSearch || soilcte.MccEnforcePositivePlasticMultiplier);
  if(enforce && cand[3]<0.)return(4);
  return(0);
}

static void MccCpuProjectLineCandidate(const StSoilCte &soilcte,std::array<double,4> &cand){
  const double tension=double(soilcte.MccTensionCutoff);
  cand[0]=MccCpuMax(cand[0],tension);
  cand[1]=MccCpuMax(cand[1],0.);
  cand[2]=MccCpuMax(cand[2],tension);
  if(soilcte.MccEnforcePositivePlasticMultiplier)cand[3]=MccCpuMax(cand[3],0.);
}

static void MccCpuReturnMapping(const StSoilCte &soilcte,const StMccCpuTensor &sigold,const StMccCpuTensor &trial
  ,double pcold,double eold,double epspvold,double epspeqold,StMccCpuTensor &signew
  ,double &pcnew,double &enew,double &epspvnew,double &epspeqnew,double &dlnew
  ,int &yieldflag,int &status,int &iters,double &residual
  ,unsigned &lsbacktracks,unsigned &lsreject,double &lsminalpha)
{
  const double m=double(soilcte.MccM);
  const double lambda=double(soilcte.MccLambda);
  const double kappa=double(soilcte.MccKappa);
  const double bulk=double(soilcte.ModulusK);
  const double shear=double(soilcte.ModulusG);
  const double tol=double(soilcte.MccReturnTolerance);
  const int maxiter=int(soilcte.MccReturnMaxIter);
  const double tension=double(soilcte.MccTensionCutoff);
  double ptr=0.,qtr=0.;
  MccCpuInvariants(trial,ptr,qtr);
  const double dptrial=(MccCpuTrace(trial)-MccCpuTrace(sigold))/3.;
  const double epsvtrial=(bulk>0.? dptrial/bulk: 0.);

  signew=trial; pcnew=pcold; enew=eold; epspvnew=epspvold; epspeqnew=epspeqold;
  dlnew=0.; yieldflag=0; status=0; iters=0; residual=0.;
  lsbacktracks=0; lsreject=0; lsminalpha=1.;

  if(ptr<=tension){
    status=-1;
    residual=ptr-tension;
    return;
  }
  const double ftr=MccCpuYield(ptr,qtr,pcold,m);
  const double fscale=MccCpuMax(qtr*qtr+m*m*ptr*MccCpuMax(pcold,ptr),1.);
  if(ftr<=tol*fscale){
    enew=MccCpuMax(-0.999,eold-(1.+eold)*epsvtrial);
    residual=ftr;
    return;
  }

  std::array<double,4> x=MccCpuInitialPlasticGuess(ptr,qtr,pcold,bulk,shear,m,tension);
  std::array<double,4> res=MccCpuResidual4(x,ptr,qtr,pcold,eold,bulk,shear,m,lambda,kappa);
  double bestnorm=MccCpuNorm4(res);
  status=-4;
  for(int it=1;it<=maxiter;it++){
    iters=it;
    const std::array<std::array<double,4>,4> jac=MccCpuNumericJacobian(x,ptr,qtr,pcold,eold,bulk,shear,m,lambda,kappa);
    std::array<double,4> rhs;
    for(unsigned c=0;c<4;c++)rhs[c]=-res[c];
    std::array<double,4> dx;
    if(!MccCpuSolve4(jac,rhs,dx)){
      status=-2;
      break;
    }
    bool accepted=false;
    const unsigned maxback=(soilcte.MccAdmissibleLineSearch? soilcte.MccLineSearchMaxBacktrack: 12u);
    const double minalpha=(soilcte.MccAdmissibleLineSearch? double(soilcte.MccLineSearchMinStep): 0.);
    const double red=(soilcte.MccAdmissibleLineSearch? double(soilcte.MccLineSearchResidualReduction): 1.e-4);
    for(unsigned ls=0;ls<=maxback;ls++){
      const double fac=pow(0.5,ls);
      if(fac<minalpha){ if(!lsreject)lsreject=7; break; }
      std::array<double,4> cand;
      for(unsigned c=0;c<4;c++)cand[c]=x[c]+fac*dx[c];
      unsigned reason=MccCpuLineCandidateRejectReason(soilcte,cand);
      if(reason && soilcte.MccAdmissibleLineSearch && soilcte.MccAdmissibleProjection==2){
        MccCpuProjectLineCandidate(soilcte,cand);
        reason=MccCpuLineCandidateRejectReason(soilcte,cand);
      }
      if(reason){
        if(!lsreject)lsreject=reason;
        if(ls>lsbacktracks)lsbacktracks=ls;
        continue;
      }
      const std::array<double,4> rc=MccCpuResidual4(cand,ptr,qtr,pcold,eold,bulk,shear,m,lambda,kappa);
      const double nc=MccCpuNorm4(rc);
      const bool reduced=(red>0.? nc<=bestnorm*(1.-red*fac)+1.e-18: nc<=bestnorm+1.e-18);
      if(std::isfinite(nc) && reduced){
        x=cand; res=rc; bestnorm=nc; accepted=true;
        if(ls>lsbacktracks)lsbacktracks=ls;
        if(fac<lsminalpha)lsminalpha=fac;
        break;
      }
      if(!lsreject)lsreject=6;
      if(ls>lsbacktracks)lsbacktracks=ls;
    }
    if(!accepted){
      status=-3;
      if(!lsreject)lsreject=8;
      break;
    }
    const double normscale=MccCpuMax(fabs(x[2])*m*m*MccCpuMax(fabs(x[0]),1.),1.);
    if(bestnorm<=tol*normscale){
      status=1;
      break;
    }
  }
  if(status<0){
    residual=MccCpuYield(ptr,qtr,pcold,m);
    return;
  }

  const double p=x[0],q=x[1],pc=x[2],dl=x[3];
  const StMccCpuTensor devtr=MccCpuDeviator(trial);
  StMccCpuTensor devnew=MccCpuTensorZero();
  if(qtr>1.e-14)devnew=MccCpuTensorScale(devtr,q/qtr);
  signew=MccCpuTensorAdd(MccCpuTensorEye(p),devnew);
  const double a=m*m;
  const double depv=dl*a*(2.*p-pc);
  const double depeq=fabs(dl)*sqrt(pow(a*(2.*p-pc),2.)+pow(2.*q,2.));
  pcnew=pc;
  epspvnew=epspvold+depv;
  epspeqnew=epspeqold+depeq;
  dlnew=dl;
  yieldflag=1;
  residual=MccCpuYield(p,q,pc,m);

  enew=MccCpuMax(-0.999,eold-(1.+eold)*epsvtrial);
}

struct StMccCpuState{
  StMccCpuTensor sig;
  double pc,e,epspv,epspeq;
};

struct StMccCpuUpdateDiag{
  int yieldflag,status,iters;
  double residual,dl;
  unsigned substeps,failures,admissfails,fallback,trigger;
  unsigned lsbacktracks,lsreject;
  double lsminalpha;
};

static bool MccCpuFiniteTensor(const StMccCpuTensor &s){
  return(std::isfinite(s.xx) && std::isfinite(s.yy) && std::isfinite(s.zz)
    && std::isfinite(s.xy) && std::isfinite(s.yz) && std::isfinite(s.xz));
}

static bool MccCpuAdmissibleState(const StSoilCte &soilcte,const StMccCpuState &st,double dl,unsigned &admfails){
  bool ok=true;
  double p=0.,q=0.;
  MccCpuInvariants(st.sig,p,q);
  const double tension=double(soilcte.MccTensionCutoff);
  if(!MccCpuFiniteTensor(st.sig) || !std::isfinite(st.pc) || !std::isfinite(st.e) || !std::isfinite(st.epspv) || !std::isfinite(st.epspeq) || !std::isfinite(dl)){
    ok=false; admfails++;
  }
  if(!std::isfinite(p) || !std::isfinite(q) || p<=tension || st.pc<=tension || st.e<=-0.999 || dl<0.){
    ok=false; admfails++;
  }
  return(ok);
}

static StMccCpuTensor MccCpuInterpolateTrial(const StMccCpuTensor &old,const StMccCpuTensor &fulltrial,double frac){
  return(MccCpuTensorAdd(old,MccCpuTensorScale(MccCpuTensorAdd(fulltrial,MccCpuTensorScale(old,-1.)),frac)));
}

static double MccCpuApproxStrainIncrement(const StSoilCte &soilcte,const StMccCpuTensor &old,const StMccCpuTensor &trial){
  const StMccCpuTensor ds=MccCpuTensorAdd(trial,MccCpuTensorScale(old,-1.));
  double dp=0.,dq=0.;
  MccCpuInvariants(ds,dp,dq);
  const double ev=(soilcte.ModulusK>0.f? fabs(dp)/double(soilcte.ModulusK): 0.);
  const double es=(soilcte.ModulusG>0.f? fabs(dq)/(3.*double(soilcte.ModulusG)): 0.);
  return(sqrt(ev*ev+es*es));
}

static double MccCpuNormalizedYieldDistance(const StSoilCte &soilcte,const StMccCpuTensor &trial,double pcold){
  double ptr=0.,qtr=0.;
  MccCpuInvariants(trial,ptr,qtr);
  const double m=double(soilcte.MccM);
  const double ftr=MccCpuYield(ptr,qtr,pcold,m);
  const double fscale=MccCpuMax(qtr*qtr+m*m*ptr*MccCpuMax(pcold,ptr),1.);
  return(MccCpuMax(0.,ftr/fscale));
}

static bool MccCpuRunSubsteps(const StSoilCte &soilcte,const StMccCpuState &initial,const StMccCpuTensor &fulltrial
  ,unsigned nsub,StMccCpuState &out,StMccCpuUpdateDiag &diag)
{
  StMccCpuState cur=initial;
  diag.substeps=nsub;
  diag.yieldflag=0; diag.status=0; diag.iters=0; diag.residual=0.; diag.dl=0.;
  diag.lsbacktracks=0; diag.lsreject=0; diag.lsminalpha=1.;
  for(unsigned s=1;s<=nsub;s++){
    const double frac=double(s)/double(nsub);
    const StMccCpuTensor subtrial=MccCpuInterpolateTrial(initial.sig,fulltrial,frac);
    StMccCpuState next=cur;
    double dl=0.,res=0.;
    int yf=0,status=0,iters=0;
    unsigned lsback=0,lsreject=0;
    double lsalpha=1.;
    MccCpuReturnMapping(soilcte,cur.sig,subtrial,cur.pc,cur.e,cur.epspv,cur.epspeq
      ,next.sig,next.pc,next.e,next.epspv,next.epspeq,dl,yf,status,iters,res,lsback,lsreject,lsalpha);
    diag.iters+=iters;
    diag.residual=res;
    diag.dl+=dl;
    diag.lsbacktracks+=lsback;
    if(lsreject)diag.lsreject=lsreject;
    diag.lsminalpha=MccCpuMin(diag.lsminalpha,lsalpha);
    if(status<0){
      diag.status=status;
      diag.yieldflag=yf;
      diag.failures++;
      out=(nsub>1? cur: next);
      return(false);
    }
    if(soilcte.MccAdmissibilityGuard && !MccCpuAdmissibleState(soilcte,next,dl,diag.admissfails)){
      diag.status=-6;
      diag.yieldflag=yf;
      diag.failures++;
      out=(nsub>1? cur: next);
      return(false);
    }
    if(yf)diag.yieldflag=1;
    cur=next;
  }
  out=cur;
  if(nsub>1 && diag.yieldflag)diag.status=2;
  else diag.status=diag.yieldflag? 1: 0;
  return(true);
}

static void MccCpuReturnMappingRobust(const StSoilCte &soilcte,const StMccCpuTensor &sigold,const StMccCpuTensor &trial
  ,double pcold,double eold,double epspvold,double epspeqold,StMccCpuTensor &signew
  ,double &pcnew,double &enew,double &epspvnew,double &epspeqnew,double &dlnew
  ,int &yieldflag,int &status,int &iters,double &residual
  ,unsigned &substeps,unsigned &substepfails,unsigned &admissfails,unsigned &fallbackused,unsigned &triggerreason
  ,unsigned &lsbacktracks,unsigned &lsreject,double &lsminalpha)
{
  StMccCpuState initial={sigold,pcold,eold,epspvold,epspeqold};
  StMccCpuState result=initial;
  StMccCpuUpdateDiag diag={0,0,0,0.,0.,1,0,0,0,0,0,0,1.};
  substeps=1; substepfails=0; admissfails=0; fallbackused=0; triggerreason=0; lsbacktracks=0; lsreject=0; lsminalpha=1.;
  if(!soilcte.MccSubstepping){
    const bool ok=MccCpuRunSubsteps(soilcte,initial,trial,1,result,diag);
    if(!ok && soilcte.MccAdmissibilityGuard)MccCpuAdmissibleState(soilcte,result,diag.dl,diag.admissfails);
  }
  else{
    const unsigned maxsub=(soilcte.MccMaxSubsteps<1? 1u: soilcte.MccMaxSubsteps);
    unsigned firstsub=1;
    unsigned trigger=0;
    if(soilcte.MccSubstepMode==0){ firstsub=maxsub; trigger=1; }
    else if(soilcte.MccSubstepMode==2){
      const unsigned minsub=(soilcte.MccMinSubsteps<1? 1u: soilcte.MccMinSubsteps);
      if(minsub>firstsub){ firstsub=minsub; trigger=4; }
      if(soilcte.MccSubstepStrainThreshold>0.f){
        const double inc=MccCpuApproxStrainIncrement(soilcte,sigold,trial);
        const unsigned nstrain=(unsigned)ceil(inc/double(soilcte.MccSubstepStrainThreshold));
        if(nstrain>firstsub){ firstsub=nstrain; trigger=2; }
      }
      if(soilcte.MccSubstepYieldDistanceThreshold>0.f){
        const double ydist=MccCpuNormalizedYieldDistance(soilcte,trial,pcold);
        const unsigned nyield=(unsigned)ceil(ydist/double(soilcte.MccSubstepYieldDistanceThreshold));
        if(nyield>firstsub){ firstsub=nyield; trigger=3; }
      }
      if(firstsub<1)firstsub=1;
      if(firstsub>maxsub)firstsub=maxsub;
    }
    diag.trigger=trigger;
    bool done=false;
    unsigned nsub=firstsub;
    StMccCpuState lastgood=initial;
    StMccCpuUpdateDiag lastdiag=diag;
    while(!done){
      StMccCpuUpdateDiag attempt={0,0,0,0.,0.,nsub,0,0,0,diag.trigger,0,0,1.};
      StMccCpuState attemptout=initial;
      const bool ok=MccCpuRunSubsteps(soilcte,initial,trial,nsub,attemptout,attempt);
      diag.failures+=attempt.failures;
      diag.admissfails+=attempt.admissfails;
      diag.iters=attempt.iters;
      diag.residual=attempt.residual;
      diag.dl=attempt.dl;
      diag.lsbacktracks=attempt.lsbacktracks;
      diag.lsreject=attempt.lsreject;
      diag.lsminalpha=attempt.lsminalpha;
      diag.substeps=nsub;
      diag.yieldflag=attempt.yieldflag;
      diag.status=attempt.status;
      if(ok){
        result=attemptout;
        lastgood=attemptout;
        lastdiag=attempt;
        done=true;
      }
      else{
        lastgood=attemptout;
        lastdiag=attempt;
        if(soilcte.MccSubstepMode==0 || nsub>=maxsub)break;
        const unsigned nextsub=nsub*2u;
        nsub=(nextsub>maxsub? maxsub: nextsub);
        diag.trigger=5;
      }
    }
    if(!done && soilcte.MccFailureFallback==2 && diag.substeps>1){
      result=lastgood;
      diag.status=-5;
      diag.fallback=1;
      diag.yieldflag=lastdiag.yieldflag;
      diag.residual=lastdiag.residual;
    }
  }
  signew=result.sig;
  pcnew=result.pc;
  enew=result.e;
  epspvnew=result.epspv;
  epspeqnew=result.epspeq;
  dlnew=diag.dl;
  yieldflag=diag.yieldflag;
  status=diag.status;
  iters=diag.iters;
  residual=diag.residual;
  substeps=diag.substeps;
  substepfails=diag.failures;
  admissfails=diag.admissfails;
  fallbackused=diag.fallback;
  triggerreason=diag.trigger;
  lsbacktracks=diag.lsbacktracks;
  lsreject=diag.lsreject;
  lsminalpha=diag.lsminalpha;
}

//==============================================================================
/// Applies the selected soil constitutive skeleton to an elastic trial stress.
//==============================================================================
static void ApplySoilConstitutiveModelCpu(const StSoilCte &soilcte,const TpDPCtes dpctes
  ,const tsymatrix3f &sigma_old,const tsymatrix3f &sigma_e,const float kplasticold,const bool updateplastic
  ,float *mccpc,float *mcce,float *mccplasticvol,float *mcceqplastic,float *mccyield
  ,float *mccdl,float *mccstatus,float *mcciters,float *mccresidual
  ,float *mccsubstepcount,float *mccsubstepfailurecount,float *mccadmissibilityfailurecount,float *mccfallbackused
  ,float *mccsubsteptriggerreason,float *mcclinesearchbacktrackcount,float *mcclinesearchrejectreason,float *mcclinesearchminalpha
  ,tsymatrix3f &signew,float &kplasnew)
{
  if(soilcte.SoilConstitutiveModel==0){
    signew=sigma_e;
    kplasnew=0.f;
    return;
  }
  if(soilcte.SoilConstitutiveModel==3){
    const bool ready=(mccpc && mcce && mccplasticvol && mcceqplastic && mccyield && mccdl && mccstatus && mcciters && mccresidual);
    if(!ready){
      signew=sigma_e;
      kplasnew=kplasticold;
      return;
    }
    StMccCpuTensor sigcp=MccCpuFromSigmac(sigma_old);
    StMccCpuTensor trialcp=MccCpuFromSigmac(sigma_e);
    StMccCpuTensor newcp=trialcp;
    double pcnew=double(*mccpc);
    double enew=double(*mcce);
    double epspvnew=double(*mccplasticvol);
    double epspeqnew=double(*mcceqplastic);
    double dlnew=0.;
    int yieldflag=0,status=0,iters=0;
    double residual=0.;
    unsigned substeps=1,substepfails=0,admissfails=0,fallbackused=0,triggerreason=0,lsbacktracks=0,lsreject=0;
    double lsminalpha=1.;
    MccCpuReturnMappingRobust(soilcte,sigcp,trialcp,double(*mccpc),double(*mcce),double(*mccplasticvol),double(*mcceqplastic)
      ,newcp,pcnew,enew,epspvnew,epspeqnew,dlnew,yieldflag,status,iters,residual
      ,substeps,substepfails,admissfails,fallbackused,triggerreason,lsbacktracks,lsreject,lsminalpha);
    signew=MccCpuToSigmac(newcp);
    kplasnew=(updateplastic? float(epspeqnew): kplasticold);
    if(updateplastic){
      *mccpc=float(pcnew);
      *mcce=float(enew);
      *mccplasticvol=float(epspvnew);
      *mcceqplastic=float(epspeqnew);
      *mccyield=float(yieldflag);
      *mccdl=float(dlnew);
      *mccstatus=float(status);
      *mcciters=float(iters);
      *mccresidual=float(residual);
      if(mccsubstepcount)*mccsubstepcount=float(substeps);
      if(mccsubstepfailurecount)*mccsubstepfailurecount=float(substepfails);
      if(mccadmissibilityfailurecount)*mccadmissibilityfailurecount=float(admissfails);
      if(mccfallbackused)*mccfallbackused=float(fallbackused);
      if(mccsubsteptriggerreason)*mccsubsteptriggerreason=float(triggerreason);
      if(mcclinesearchbacktrackcount)*mcclinesearchbacktrackcount=float(lsbacktracks);
      if(mcclinesearchrejectreason)*mcclinesearchrejectreason=float(lsreject);
      if(mcclinesearchminalpha)*mcclinesearchminalpha=float(lsminalpha);
      }
    return;
  }
  if(soilcte.SoilConstitutiveModel==2){
    ConsRelationEPsft_fast(sigma_e,soilcte.ModulusK,soilcte.ModulusG,soilcte.phi,soilcte.phi_r,soilcte.n_phi
      ,soilcte.coh,soilcte.coh_r,soilcte.n_coh,soilcte.dlt,kplasticold,signew,kplasnew);
  }
  else{
    const float phi=soilcte.phi;
    const float coh=soilcte.coh;
    const float psi=soilcte.dlt;
    float DP_phi=2.f*sin(phi)/((3.f-sin(phi))*1.732f);
    float DP_kc=6.f*coh*cos(phi)/((3.f-sin(phi))*1.732f);
    float DP_psi=2.f*sin(psi)/((3.f-sin(psi))*1.732f);
    if(dpctes==DP_MC){
      DP_phi=2.f*sin(phi)/((3.f+sin(phi))*1.732f);
      DP_kc=6.f*coh*cos(phi)/((3.f+sin(phi))*1.732f);
      DP_psi=2.f*sin(psi)/((3.f+sin(psi))*1.732f);
    }
    if(dpctes==DP_PS){
      DP_phi=tan(phi)/sqrt(9.f+12.f*tan(phi)*tan(phi));
      DP_kc=3.f*coh/sqrt(9.f+12.f*tan(phi)*tan(phi));
      DP_psi=tan(psi)/sqrt(9.f+12.f*tan(psi)*tan(psi));
    }
    ConsRelationEP_fast(sigma_e,soilcte.ModulusK,soilcte.ModulusG,DP_phi,DP_kc,DP_psi,kplasticold,signew,kplasnew);
  }
  if(!updateplastic)kplasnew=kplasticold;
}

//==============================================================================
/// Calculate new values of position, velocity & density for fluid (using Verlet).
/// Calcula nuevos valores de posicion, velocidad y densidad para el fluido (usando Verlet).
//==============================================================================
void JSphCpu::ComputeVerletVarsFluid(bool shift,const tfloat3 *indirvel
  ,const tfloat4 *velrhop1,const tfloat4 *velrhop2,const tsymatrix3f *sigma2,const float *kplastic,const tsymatrix3f *rsigma
  ,double dt,double dt2,tdouble3 *pos,unsigned *dcell,typecode *code,tfloat4 *velrhopnew, tsymatrix3f *sigmanew, float *kplasticnew)const
{
  if(SoilCte.SoilConstitutiveModel==3 && !(MccPcc && MccVoidRatioc && MccPlasticVolStrainc && MccEqPlasticStrainc && MccYieldFlagc && MccPlasticMultiplierc && MccReturnStatusc && MccReturnIterationsc && MccYieldResidualc && MccSubstepCountc && MccSubstepFailureCountc && MccAdmissibilityFailureCountc && MccFallbackUsedc && MccSubstepTriggerReasonc && MccLineSearchBacktrackCountc && MccLineSearchRejectReasonc && MccLineSearchMinAlphac))
    Run_Exceptioon("MCC CPU stress update requires allocated MCC state arrays.");
  const double dt205=0.5*dt*dt;
  const tdouble3 gravity=ToTDouble3(GetMechanicalGravity(TimeStep));
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
      ApplySoilConstitutiveModelCpu(SoilCte,DPCtes,sigma2[p],sigma_e,kplasticold,true
        ,(MccPcc? MccPcc+p: NULL),(MccVoidRatioc? MccVoidRatioc+p: NULL),(MccPlasticVolStrainc? MccPlasticVolStrainc+p: NULL)
        ,(MccEqPlasticStrainc? MccEqPlasticStrainc+p: NULL),(MccYieldFlagc? MccYieldFlagc+p: NULL),(MccPlasticMultiplierc? MccPlasticMultiplierc+p: NULL)
        ,(MccReturnStatusc? MccReturnStatusc+p: NULL),(MccReturnIterationsc? MccReturnIterationsc+p: NULL),(MccYieldResidualc? MccYieldResidualc+p: NULL)
        ,(MccSubstepCountc? MccSubstepCountc+p: NULL),(MccSubstepFailureCountc? MccSubstepFailureCountc+p: NULL)
        ,(MccAdmissibilityFailureCountc? MccAdmissibilityFailureCountc+p: NULL),(MccFallbackUsedc? MccFallbackUsedc+p: NULL)
        ,(MccSubstepTriggerReasonc? MccSubstepTriggerReasonc+p: NULL),(MccLineSearchBacktrackCountc? MccLineSearchBacktrackCountc+p: NULL),(MccLineSearchRejectReasonc? MccLineSearchRejectReasonc+p: NULL),(MccLineSearchMinAlphac? MccLineSearchMinAlphac+p: NULL)
        ,signew,kplasnew);
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
  if(SoilCte.SoilConstitutiveModel==3 && !(MccPcc && MccVoidRatioc && MccPlasticVolStrainc && MccEqPlasticStrainc && MccYieldFlagc && MccPlasticMultiplierc && MccReturnStatusc && MccReturnIterationsc && MccYieldResidualc && MccSubstepCountc && MccSubstepFailureCountc && MccAdmissibilityFailureCountc && MccFallbackUsedc && MccSubstepTriggerReasonc && MccLineSearchBacktrackCountc && MccLineSearchRejectReasonc && MccLineSearchMinAlphac))
    Run_Exceptioon("MCC CPU stress update requires allocated MCC state arrays.");
  const bool shift=false; //(ShiftingMode!=SHIFT_None); //-We strongly recommend running the shifting correction only for the corrector. If you want to re-enable shifting in the predictor, change the value here to "true".
  const double dt05=dt*.5;
  const tfloat3 mechgravity=GetMechanicalGravity(TimeStep);
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
        float(double(VelrhopPrec[p].x) + (double(Acec[p].x)+mechgravity.x) * dt05),
        float(double(VelrhopPrec[p].y) + (double(Acec[p].y)+mechgravity.y) * dt05),
        float(double(VelrhopPrec[p].z) + (double(Acec[p].z)+mechgravity.z) * dt05),
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
      ApplySoilConstitutiveModelCpu(SoilCte,DPCtes,SigmaPrec[p],sigma_e,kplasticold,false
        ,(MccPcc? MccPcc+p: NULL),(MccVoidRatioc? MccVoidRatioc+p: NULL),(MccPlasticVolStrainc? MccPlasticVolStrainc+p: NULL)
        ,(MccEqPlasticStrainc? MccEqPlasticStrainc+p: NULL),(MccYieldFlagc? MccYieldFlagc+p: NULL),(MccPlasticMultiplierc? MccPlasticMultiplierc+p: NULL)
        ,(MccReturnStatusc? MccReturnStatusc+p: NULL),(MccReturnIterationsc? MccReturnIterationsc+p: NULL),(MccYieldResidualc? MccYieldResidualc+p: NULL)
        ,(MccSubstepCountc? MccSubstepCountc+p: NULL),(MccSubstepFailureCountc? MccSubstepFailureCountc+p: NULL)
        ,(MccAdmissibilityFailureCountc? MccAdmissibilityFailureCountc+p: NULL),(MccFallbackUsedc? MccFallbackUsedc+p: NULL)
        ,(MccSubstepTriggerReasonc? MccSubstepTriggerReasonc+p: NULL),(MccLineSearchBacktrackCountc? MccLineSearchBacktrackCountc+p: NULL),(MccLineSearchRejectReasonc? MccLineSearchRejectReasonc+p: NULL),(MccLineSearchMinAlphac? MccLineSearchMinAlphac+p: NULL)
        ,signew,kplasnew);
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
  if(SoilCte.SoilConstitutiveModel==3 && !(MccPcc && MccVoidRatioc && MccPlasticVolStrainc && MccEqPlasticStrainc && MccYieldFlagc && MccPlasticMultiplierc && MccReturnStatusc && MccReturnIterationsc && MccYieldResidualc && MccSubstepCountc && MccSubstepFailureCountc && MccAdmissibilityFailureCountc && MccFallbackUsedc && MccSubstepTriggerReasonc && MccLineSearchBacktrackCountc && MccLineSearchRejectReasonc && MccLineSearchMinAlphac))
    Run_Exceptioon("MCC CPU stress update requires allocated MCC state arrays.");
  const bool shift=(Shifting!=NULL);
  const double dt05=dt*.5;
  const tfloat3 mechgravity=GetMechanicalGravity(TimeStep);
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
        float(double(VelrhopPrec[p].x) + (double(Acec[p].x)+mechgravity.x) * dt), 
        float(double(VelrhopPrec[p].y) + (double(Acec[p].y)+mechgravity.y) * dt), 
        float(double(VelrhopPrec[p].z) + (double(Acec[p].z)+mechgravity.z) * dt),
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
      ApplySoilConstitutiveModelCpu(SoilCte,DPCtes,SigmaPrec[p],sigma_e,kplasticold,true
        ,(MccPcc? MccPcc+p: NULL),(MccVoidRatioc? MccVoidRatioc+p: NULL),(MccPlasticVolStrainc? MccPlasticVolStrainc+p: NULL)
        ,(MccEqPlasticStrainc? MccEqPlasticStrainc+p: NULL),(MccYieldFlagc? MccYieldFlagc+p: NULL),(MccPlasticMultiplierc? MccPlasticMultiplierc+p: NULL)
        ,(MccReturnStatusc? MccReturnStatusc+p: NULL),(MccReturnIterationsc? MccReturnIterationsc+p: NULL),(MccYieldResidualc? MccYieldResidualc+p: NULL)
        ,(MccSubstepCountc? MccSubstepCountc+p: NULL),(MccSubstepFailureCountc? MccSubstepFailureCountc+p: NULL)
        ,(MccAdmissibilityFailureCountc? MccAdmissibilityFailureCountc+p: NULL),(MccFallbackUsedc? MccFallbackUsedc+p: NULL)
        ,(MccSubstepTriggerReasonc? MccSubstepTriggerReasonc+p: NULL),(MccLineSearchBacktrackCountc? MccLineSearchBacktrackCountc+p: NULL),(MccLineSearchRejectReasonc? MccLineSearchRejectReasonc+p: NULL),(MccLineSearchMinAlphac? MccLineSearchMinAlphac+p: NULL)
        ,signew,kplasnew);
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
    const float porosity0=SoilCte.Porosity0;
    const float hydraulicconductivity=SoilCte.HydraulicConductivity;
    const float waterbulkmodulus=SoilCte.WaterBulkModulus;
    const float waterdensity=SoilCte.WaterDensity;
    if(hydraulicconductivity>0.f && waterbulkmodulus>0.f && waterdensity>0.f && porosity0>0.f && porosity0<1.f && PorePressureDtSafety>0.f){
      const double gmag=GetHydraulicGmag();
      if(gmag<=0.)Run_Exceptioon("Hydraulic gravity magnitude must be greater than zero for pore-pressure timestep restriction.");
      const double cw=double(waterdensity)*gmag*double(porosity0)/double(waterbulkmodulus);
      dtpore=double(PorePressureDtSafety)*cw*double(KernelH)*double(KernelH)/double(hydraulicconductivity);
      if(dtpore<=0. || fun::IsNAN(dtpore) || fun::IsInfinity(dtpore))Run_Exceptioon(fun::PrintStr("The computed pore-pressure timestep is invalid (dt_pore=%g).",dtpore));
      dtporeactive=true;
      if(!PorePressureDtConfigPrint){
        Log->Printf("Pore-pressure timestep restriction: active=True, Cw=%g, dt_pore=%g, safety=%g, h(KernelH)=%g, hydraulic_gmag=%g.",cw,dtpore,PorePressureDtSafety,KernelH,gmag);
        if(FixedDt)Log->PrintWarning(fun::PrintStr("Fixed dt is enabled. Fixed dt should be <= dt_pore=%g for PR pore-pressure update.",dtpore));
        PorePressureDtConfigPrint=true;
        PorePressureDtFixedPrint=(FixedDt!=NULL);
      }
    }
    else if(hydraulicconductivity==0.f){
      if(!PorePressureDtConfigPrint){
        Log->Print("Pore-pressure timestep restriction: active=False, disabled because HydraulicConductivity=0.");
        PorePressureDtConfigPrint=true;
      }
    }
    else if(hydraulicconductivity>0.f)Run_Exceptioon("Invalid hydromechanical parameters for pore-pressure timestep restriction.");
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



