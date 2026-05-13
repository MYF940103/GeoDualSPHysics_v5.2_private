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

//:#############################################################################
//:# Cambios:
//:# =========
//:# - El calculo de constantes en ConfigConstants() se hace usando double aunque
//:#   despues se convierte a float (22-04-2013)
//:# - Mejora la gestion de excepciones. (06-05-2020)
//:# - Comprobacion de la densidad inicial de las particulas fluido en la funcion
//:#   CheckRhopLimits(). (24-06-2020)
//:# - Funcion FtApplyExternalVel() para aplicar una velocidad externa a objetos
//:#   flotantes usando Chrono. (01-07-2020)
//:#############################################################################

/// \file JSph.h \brief Declares the class \ref JSph.

#ifndef _JSph_
#define _JSph_

#include "DualSphDef.h"
#include "JObject.h"
#include "JSphCfgRun.h"
#include "JLog2.h"
#include "JTimer.h"
#include <float.h>
#include <string>
#include <cmath>
#include <ctime>
#include <sstream>
#include <iostream>
#include <fstream>

class JSphMk;
class JDsMotion;
class JPartData;
class JPartPData;
class JDsFixedDt;
class JDsSaveDt;
class JDsViscoInput;
class JWaveGen;
class JMLPistons;
class JRelaxZones;
class JDsAccInput;
class JCaseParts;
class JPartDataBi4;
class JPartOutBi4Save;
class JPartFloatBi4Save;
class JDsPartsOut;
class JSphShifting;
class JDsDamping;
class JXml;
class JDsOutputTime;
class JGaugeSystem;
class JPartsLoad4;
class JCasePartBlock;
class JChronoObjects;
class JDsMooredFloatings;
class JDsFtForcePoints;
class JSphInOut;
class JDsPartsInit;
class JDsPips;
class JLinearValue;
class JCaseEParms;
class JDataArrays;
class JNumexLib;
class JFtMotionSave; //<vs_ftmottionsv>
class JDsExtraDataSave;

//##############################################################################
//# XML format of execution parameters in _FmtXML__Parameters.xml.
//##############################################################################

//##############################################################################
//# JSph
//##############################################################################
/// \brief Defines all the attributes and functions that CPU and GPU simulations share.

class JSph : protected JObject
{
public:
/// Structure with constants for the Cubic Spline kernel.
  typedef struct {
    float a1,a2,aa,a24,c1,d1,c2;
    float od_wdeltap;        ///<Parameter for tensile instability correction.  
  }StCubicCte;

/// Structure that saves extra information about the execution.
  typedef struct {
    double timesim;      ///<Seconds from the start of the simulation (after loading the initial data).                    | Segundos desde el inicio de la simulacion (despues de cargar los datos iniciales).
    unsigned nct;        ///<Number of cells used in the divide.                                                           | Numero de celdas usadas en el divide.                                                    
    unsigned npbin;      ///<Number of boundary particles within the area of the divide (includes periodic particles).     | Numero de particulas bound dentro del area del divide (incluye particulas periodicas).
    unsigned npbout;     ///<Number of boundary particles outside of the area of the divide (includes periodic particles). | Numero de particulas bound fuera del area del divide (incluye particulas periodicas).    
    unsigned npf;        ///<Number of fluid particles (includes periodic particles).                                      | Numero de particulas fluid (incluye particulas periodicas).                              
    unsigned npbper;     ///<Number of periodic boundary particles (inside and outside the area of the split).             | Numero de particulas bound periodicas (dentro y fuera del area del divide).              
    unsigned npfper;     ///<Number of periodic fluid particles.                                                           | Numero de particulas fluid periodicas.                                                   
    unsigned newnp;      ///<Number of new fluid particles (inlet conditions)                                              | Numero de nuevas particulas fluid (inlet conditions).                                    
    llong memorycpualloc;
    bool gpudata;
    llong memorynpalloc;
    llong memorynpused;
    llong memorynctalloc;
    llong memorynctused;
  }StInfoPartPlus;

private:
  //-Configuration variables to compute the case limits.
  //-Variables de configuracion para calcular el limite del caso.
  tdouble3 CfgDomainParticlesMin,CfgDomainParticlesMax;
  tdouble3 CfgDomainParticlesPrcMin,CfgDomainParticlesPrcMax;
  tdouble3 CfgDomainFixedMin,CfgDomainFixedMax;

  //-Object for saving particles and information in files.
  //-Objeto para la grabacion de particulas e informacion en ficheros.
  JPartDataBi4 *DataBi4;            ///<To store particles and info in bi4 format.      | Para grabar particulas e info en formato bi4.
  JPartOutBi4Save *DataOutBi4;      ///<To store excluded particles in bi4 format.      | Para grabar particulas excluidas en formato bi4.
  JPartFloatBi4Save *DataFloatBi4;  ///<To store floating data in bi4 format.           | Para grabar datos de floatings en formato bi4.

  //-Total number of excluded particles according to reason for exclusion.
  //-Numero acumulado de particulas excluidas segun motivo.
  unsigned OutPosCount,OutRhopCount,OutMoveCount;

  void InitVars();
  std::string CalcRunCode()const;
  void AddOutCount(unsigned outpos,unsigned outrhop,unsigned outmove){ OutPosCount+=outpos; OutRhopCount+=outrhop; OutMoveCount+=outmove; }
  void ClearCfgDomain();
  void ConfigDomainFixed(tdouble3 vmin,tdouble3 vmax);
  void ConfigDomainFixedValue(std::string key,double v);
  void ConfigDomainParticles(tdouble3 vmin,tdouble3 vmax);
  void ConfigDomainParticlesValue(std::string key,double v);
  void ConfigDomainParticlesPrc(tdouble3 vmin,tdouble3 vmax);
  void ConfigDomainParticlesPrcValue(std::string key,double v);
  void ConfigDomainResize(std::string key,const JCaseEParms *eparms);

protected:
  const bool Cpu;
  const bool Mgpu;
  const bool WithMpi;
  JLog2 *Log;

  const JSphCfgRun *CfgRun;

  bool Simulate2D;       ///<Toggles 2D simulation (cancels forces in Y axis). | Activa o desactiva simulacion en 2D (anula fuerzas en eje Y).
  double Simulate2DPosY; ///<Y value in 2D simulations.                        | Valor de Y en simulaciones 2D.
  bool Symmetry;         ///<Activates symmetry in plane y=0 (default=false).
  bool Stable;
  bool SvPosDouble;      ///<Indicates whether Pos is saved as double in bi4 files. | Indica si en los ficheros bi4 se guarda Pos como double.

  std::string AppName;
  std::string Hardware;  ///<Hardware description in short text.
  std::string RunMode;   ///<Overall mode of execution in short text.
  std::string ConfigInfo;  ///<Main configuration values in short text.
  std::string RunCode;
  std::string RunTimeDate;
  std::string CaseName,DirCase,RunName;
  std::string DirOut;         ///<Specifies the general output directory.
  std::string DirDataOut;     ///<Specifies the output subdirectory for binary data.
  std::string FileXml;

  //-Options for execution.
  TpStep TStep;               ///<Step Algorithm: Verlet or Symplectic.                                  | Algoritmo de paso: Verlet o Symplectic.
  int VerletSteps;            ///<Number of steps to apply Eulerian equations.

  TpKernel TKernel;                ///<Kernel type: Cubic or Wendland.
  fsph::StKCubicCte      KCubic;   ///<Constants for the Cubic Spline kernel.
  fsph::StKWendlandCte   KWend;    ///<Constants for the Wendland kernel.

  TpDensity TDensity;         ///<Density Diffusion Term 0:None, 1:Molteni, 2:Fourtakas, 3:Fourtakas(full) (default=0)
  float DDTValue;             ///<Value used with Density Diffusion Term (default=0.1)
  tdouble3 DDTRamp;           ///<Configuration of initial DDT ramp (Total time, time for maxvalue, maxvalue).  //<vs_ddramp>
  bool DDTArray;              ///<Use extra array to compute Density Diffusion Term. The correction is applied after particle interaction. 

  TpVisco TVisco;             ///<Viscosity type: Artificial,...                                         | Tipo de viscosidad: Artificial,...
  float Visco;  
  float ViscoBoundFactor;     ///<For boundary interaction use Visco*ViscoBoundFactor.                  | Para interaccion con contorno usa Visco*ViscoBoundFactor.
  JDsViscoInput *ViscoTime;   ///<Provides a viscosity value as a function of simulation time.          | Proporciona un valor de viscosidad en funcion del instante de la simulacion.

  TpBoundary TBoundary;       ///<Boundary condition: DBC, M-DBC.
  TpSlipMode SlipMode;        ///<Slip mode for mDBC 1:DBC vel=0, 2:No-slip, 3:Free slip (default=1).
  TpDPCtes DPCtes;            ///<DP constants 1:3D Circumscribed DP, 2:3D Mid Circumscribed DP, 3:Plain Strain condition (default=1). //mdbr
  bool ArtificialStress;      ///<Bui 2008 artificial stress for tensile instability (default=0). //mdbr
  float ArtificialStressCoef; ///<Coefficient epsilon for Bui 2008 artificial stress. //mdbr
  float ArtificialStressExp;  ///<Exponent n for Bui 2008 artificial stress kernel ratio. //mdbr
  bool ArtificialStressExpAuto; ///<Computes ArtificialStressExp from h/dp and kernel support when XML value is not defined. //mdbr
  bool HydromechCoupling;       ///<Hydromechanical coupling switch. 0:None, 1:Enable (default=0).
  int PorePressureModel;        ///<Pore pressure model. 0:None, 1:PR, 2:PPE unsupported (default=0).
  int PorePressureInit;         ///<Initial pore pressure. 0:Zero, 1:Hydrostatic, 2:FromFile, 3:Hydrostatic+analytical excess (default=0).
  float PorePressureWaterLevel; ///<Water level for hydrostatic pore-pressure initialization.
  float PorePressureExcessAmp;  ///<Amplitude of analytical excess pore pressure [Pa].
  int PorePressureAnalyticalProfile; ///<Analytical excess pore pressure profile. 1:sin(pi*eta), 2:cos(pi*eta/2), 3:uniform.
  bool PorePressureTopDrained;  ///<Top drained boundary for excess pore pressure. 0:off, 1:on.
  float PorePressureDrainThickness; ///<Top drained layer thickness. If <=0, KernelH is used.
  bool PorePressureBottomNoFlux; ///<Bottom no-flux boundary for excess pore pressure. 0:off, 1:on.
  float PorePressureBottomNoFluxThickness; ///<Bottom no-flux layer thickness. If <=0, KernelH is used.
  int PorePressureBoundaryOperator; ///<Hydraulic boundary contribution in PR operator. 0:legacy, 1:virtual ghost, 2:CPU hydraulic boundary-particle prototype, 3:CPU curved drained prototype.
  bool PorePressureCurvedDrained; ///<CPU curved drained pore-pressure boundary switch for operator mode 3.
  tdouble3 CurvedDrainedBoundaryCenter; ///<Sphere center for curved drained pore-pressure boundary.
  double CurvedDrainedBoundaryRadius; ///<Sphere radius for curved drained pore-pressure boundary.
  int CurvedDrainedBoundaryTargetMk; ///<Target mkfluid for curved drained boundary. -1:all material particles.
  double CurvedDrainedBoundaryValue; ///<Prescribed curved drained boundary pressure/excess value [Pa].
  bool CurvedDrainedBoundaryUseExcess; ///<True: value is excess pressure; false: value is total pressure.
  double CurvedDrainedBoundaryThickness; ///<Interior shell thickness for curved drained boundary. If <=0, KernelH is used.
  int CurvedDrainedBoundaryMode; ///<Curved drained mode. 0:Dirichlet ghost, 1:strengthened image ghost, 2:diagnostic surface clamp, 3:multi-sample quadrature, 4:boundary-particle Dirichlet state, 5:MLS flux correction, 6:radial-shell flux correction, 7:conservative multi-shell radial exchange, 8:corrected MLS Laplacian.
  int CurvedDrainedBoundaryTargetMkBound; ///<Target mkbound for mode 4 boundary-particle hydraulic state. -1:all boundary particles passing sphere selection.
  bool CurvedDrainedBoundaryUseBoundaryParticles; ///<Enable selected boundary-particle participation for curved drained mode 4.
  double CurvedDrainedBoundarySelectionTolerance; ///<Radius tolerance for selecting curved drained boundary particles. If <=0, KernelH is used.
  bool CurvedDrainedBoundaryAdamiDiagnostic; ///<Compute paper-style normalized-kernel boundary pressure extrapolation diagnostics without using it as Dirichlet value.
  int CurvedDrainedBoundaryWeighting; ///<Boundary-particle weighting for curved drained mode 4. 0:raw volume, 1:normalized partition, 3:diagnostic capped support.
  int CurvedDrainedMLSOrder; ///<MLS order for curved drained mode 5. 0:local gap fallback, 1:radial linear MLS.
  double CurvedDrainedMLSRadiusFactor; ///<Support radius multiplier for mode 5 radial MLS. If <=0, KernelH is used.
  bool CurvedDrainedFluxDiagnostics; ///<Print per-step mode 5 integrated flux diagnostics.
  double CurvedDrainedMLSConditionLimit; ///<Maximum accepted local MLS condition number for mode 5.
  int CurvedDrainedMLSFallbackMode; ///<Fallback for mode 5 ill-conditioned support. 3:mode-3-like ghost, 4:mode-4-like local gap.
  unsigned CurvedDrainedShellCount; ///<Shell count for mode 7. 0:auto.
  unsigned CurvedDrainedShellMinParticles; ///<Minimum particles per mode 7 shell before fallback.
  int CurvedDrainedShellMode; ///<Mode 7 shell layout. 0:auto count, 1:fixed CurvedDrainedShellCount.
  int CurvedDrainedShellCorrectionMode; ///<Mode 7 correction. 0:replace diffusion rate, 1:shell-average correction.
  bool CurvedDrainedShellDiagnostics; ///<Print per-step mode 7 shell diagnostics.
  double CurvedDrainedCorrectedLapRadiusFactor; ///<Support radius multiplier for mode 8 quadratic MLS Laplacian. If <=0, KernelSize is used.
  double CurvedDrainedCorrectedLapRMinFactor; ///<Minimum normalized radius where mode 8 replaces LapPorePress.
  unsigned CurvedDrainedCorrectedLapBoundarySamples; ///<Number of tangential boundary samples for mode 8, including the projected point.
  unsigned CurvedDrainedCorrectedLapMinSamples; ///<Minimum MLS samples for mode 8 before fallback.
  double CurvedDrainedCorrectedLapConditionLimit; ///<Maximum accepted local condition estimate for mode 8.
  double CurvedDrainedCorrectedLapBoundaryWeight; ///<Relative weight for mode 8 Dirichlet boundary samples.
  int CurvedDrainedCorrectedLapFallbackMode; ///<Fallback for mode 8. 0:keep existing material LapPorePress, 4:mode-4-like local gap.
  bool CurvedDrainedCorrectedLapDiagnostics; ///<Print per-step mode 8 corrected Laplacian diagnostics.
  int CurvedDrainedCorrectedLaplacianLimiter; ///<Limiter for mode 8. 0:off, 1:positivity, 3:blend.
  double CurvedDrainedLimiterCFL; ///<Maximum fraction of local pressure gap removed in one step by the positivity limiter.
  double CurvedDrainedLimiterBlend; ///<Mode 8 blend factor theta for theta*MLS+(1-theta)*material LapPorePress.
  bool CurvedDrainedLimiterPreventNegative; ///<Apply positivity cap after the selected mode 8 limiter.
  bool PorePressureBoundaryGhost; ///<Enable pore-pressure boundary ghost diagnostics. 0:off, 1:on.
  bool PorePressureBoundaryGhostOutput; ///<Save pore-pressure ghost diagnostics when SavePorePressure=1.
  bool HydraulicElevationSource; ///<Enable hydrostatic/elevation source convention in PR pressure equation. 0:gravity-free scaling only, 1:legacy source.
  float Porosity0;              ///<Deprecated execution-parameter fallback for SoilCte.Porosity0.
  float HydraulicConductivity;  ///<Deprecated execution-parameter fallback for SoilCte.HydraulicConductivity.
  float WaterBulkModulus;       ///<Deprecated execution-parameter fallback for SoilCte.WaterBulkModulus.
  float WaterDensity;           ///<Deprecated execution-parameter fallback for SoilCte.WaterDensity.
  bool Porosity0ParamDefined;             ///<True when deprecated Porosity0 execution parameter exists.
  bool HydraulicConductivityParamDefined; ///<True when deprecated HydraulicConductivity execution parameter exists.
  bool WaterBulkModulusParamDefined;      ///<True when deprecated WaterBulkModulus execution parameter exists.
  bool WaterDensityParamDefined;          ///<True when deprecated WaterDensity execution parameter exists.
  float PorePressureDtSafety;   ///<Safety factor for pore-pressure timestep restriction.
  bool PorePressureFeedback;    ///<Pore-pressure feedback to momentum. 0:off, 1:on (default=0).
  int PorePressureFeedbackMode;  ///<Pore-pressure feedback mode. 0:total pressure, 1:excess pressure relative to hydrostatic baseline.
  int PorePressureFeedbackOperator; ///<Pore-pressure feedback operator. 0:symmetric stress-style, 1:difference-gradient, 2:LSQ pressure gradient, 3:paper-style stress pair.
  double PorePressureFeedbackStartTime; ///<Time when pore-pressure feedback acceleration starts [s].
  double PorePressureFeedbackRampEndTime; ///<Optional time when feedback acceleration reaches full scale [s].
  double PorePressureFeedbackScale; ///<Maximum pore-pressure feedback acceleration scale.
  double PorePressureFeedbackLSQRadiusFactor; ///<Operator 2 support radius factor relative to kernel size. <=0 uses full support.
  double PorePressureFeedbackLSQConditionLimit; ///<Operator 2 maximum Frobenius condition proxy. <=0 disables the limit.
  int PorePressureFeedbackLSQFallback; ///<Operator 2 fallback. 0:difference-gradient, 1:zero feedback.
  bool SavePorePressureFeedbackDiagnostics; ///<Print pore-pressure feedback acceleration diagnostics.
  unsigned PorePressureFeedbackDiagInterval; ///<Step interval for pore-pressure feedback diagnostics.
  int PorePressureFeedbackLimiterMode; ///<Feedback limiter mode. 0:none, 1:absolute cap, 2:ratio cap, 3:absolute+ratio cap.
  double PorePressureFeedbackRelaxation; ///<Optional feedback acceleration relaxation alpha. 0:off, (0,1]: enabled.
  double PorePressureFeedbackMaxAccel; ///<Optional absolute cap for feedback acceleration magnitude [m/s2]. <=0:disabled.
  double PorePressureFeedbackMaxAccelRatio; ///<Optional cap ratio against non-feedback/confining acceleration. <=0:disabled.
  bool PorePressureFeedbackUseClassFilter; ///<Restrict feedback acceleration using cylinder class filters. Default off.
  bool PorePressureFeedbackExcludeCaps; ///<Class filter: skip top/bottom cap particles.
  bool PorePressureFeedbackExcludeEdges; ///<Class filter: skip cylinder edge-ring particles.
  bool PorePressureFeedbackExcludeConfinementTargets; ///<Class filter: skip selected lateral confinement target particles.
  bool PorePressureFeedbackInteriorOnly; ///<Class filter: apply feedback only to cylinder interior particles.
  bool PorePressureShepard;     ///<Apply Shepard regularization to pore pressure. 0:off, 1:on.
  unsigned PorePressureShepardInterval; ///<Apply Shepard regularization every N steps.
  int PorePressureShepardMode;  ///<Pore-pressure Shepard mode. 0:total pressure, 1:excess pressure.
  bool SavePorePressure;        ///<Save pore pressure field. 0:off, 1:on (default=0).
  tfloat3 HydraulicGravity;     ///<Optional hydraulic gravity vector [m/s2]. Zero vector falls back to body Gravity.
  double BodyGravityStopTime;   ///<Time to stop mechanical body gravity. <=0: body gravity remains active.
  bool BodyGravityStoppedLogged; ///<True when mechanical body gravity stop has been reported.
  int InitialStressMode;        ///<Initial skeleton/effective stress mode. 0:none, 1:uniform isotropic effective compression.
  float InitialEffectiveStressIso; ///<Initial isotropic effective compression magnitude [Pa]. Positive XML value is written as negative Sigmac diagonal.
  int InitialEffectiveStressTargetMk; ///<Target mkfluid for initial effective stress. -1:all material particles.
  bool FlexibleConfiningStress; ///<CPU flexible confining stress source. 0:off, 1:on.
  float ConfiningStressP0;      ///<Positive compression magnitude for flexible confining stress [Pa].
  double ConfiningStressRampStart; ///<Start time for confining stress ramp [s].
  double ConfiningStressRampEnd;   ///<End time for confining stress ramp [s].
  int ConfiningStressTargetMk;  ///<Target mkfluid for confining stress. -1:all material particles.
  int ConfiningStressMode;      ///<Flexible confining stress mode. 0:isotropic stress source.
  int ConfiningStressGradientMode; ///<Gradient mode for flexible confinement. 0:raw kernel gradient, 1:renormalized/corrected gradient.
  bool FlexibleConfiningStressFiDiagnostic; ///<Compute Zhao kernel-completeness diagnostic f_i.
  bool SaveConfiningStressDiagnostics; ///<Print extended CPU confinement diagnostics.
  double ConfiningStressFiThreshold; ///<Kernel-completeness threshold for near-boundary diagnostics/selectors.
  int ConfiningStressGeometry; ///<Confining geometry selector. 0:none, 1:cylinder.
  tdouble3 ConfiningStressCylinderCenter; ///<Cylinder selector center/base point [m].
  tdouble3 ConfiningStressCylinderAxis; ///<Cylinder selector axis unit vector.
  double ConfiningStressCylinderRadius; ///<Cylinder selector radius [m].
  double ConfiningStressCylinderHeight; ///<Cylinder selector height [m].
  double ConfiningStressCapExclusionLength; ///<Cap exclusion length along cylinder axis [m].
  double ConfiningStressEdgeExclusionLength; ///<Radial edge/lateral tolerance [m].
  bool ConfiningStressUseFiSelector; ///<Apply confinement only where f_i is below threshold.
  bool ConfiningStressUseLateralSelector; ///<Apply confinement only on selected lateral cylinder particles.
  double ConfiningStressLateralSelectorStartTime; ///<Time to activate lateral selector when ConfiningStressUseLateralSelector=1. <=0 keeps legacy behavior.
  bool CapConfiningStress; ///<CPU cap-normal hydrostatic support for triaxial staging. Default off.
  float CapConfiningStressP0; ///<Positive cap-normal support magnitude [Pa].
  double CapConfiningStressRampStart; ///<Start time for cap support ramp [s].
  double CapConfiningStressRampEnd; ///<End time for cap support ramp [s].
  int CapConfiningStressTopMk; ///<Top cap mkfluid target. -1:all top cap material particles.
  int CapConfiningStressBottomMk; ///<Bottom cap mkfluid target. -1:all bottom cap material particles.
  int CapConfiningStressMode; ///<Cap support mode. 0:uniform integrated pressure force over cap area.
  tdouble3 CapConfiningStressAxis; ///<Cap inward/outward axis direction; top receives -axis, bottom +axis.
  bool SaveCapConfiningStressDiagnostics; ///<Print CPU cap support diagnostics.
  mutable double CapConfiningStressDiagP0Eff; ///<Last effective cap support pressure after ramp [Pa].
  mutable unsigned CapConfiningStressDiagTopCount; ///<Last top cap target count.
  mutable unsigned CapConfiningStressDiagBottomCount; ///<Last bottom cap target count.
  mutable unsigned CapConfiningStressDiagEdgeSkippedCount; ///<Last edge-ring particles intentionally skipped by cap support.
  mutable double CapConfiningStressDiagTopAccelMean; ///<Last mean top cap support acceleration [m/s2].
  mutable double CapConfiningStressDiagBottomAccelMean; ///<Last mean bottom cap support acceleration [m/s2].
  mutable double CapConfiningStressDiagTopAccelMax; ///<Last maximum top cap support acceleration [m/s2].
  mutable double CapConfiningStressDiagBottomAccelMax; ///<Last maximum bottom cap support acceleration [m/s2].
  mutable tdouble3 CapConfiningStressDiagNetForce; ///<Last net cap support force estimate [N].
  mutable double CapConfiningStressDiagTotalAbsForce; ///<Last total absolute cap force estimate [N].
  mutable double CapConfiningStressDiagComAccel; ///<Last cap support center-of-mass acceleration estimate [m/s2].
  mutable double CapConfiningStressDiagSymResidual; ///<Last cap force symmetry residual.
  mutable int CapConfiningStressDiagLastPrintStep; ///<Last step printed for cap support diagnostics.
  bool SavePlatenReactionDiagnostics; ///<Print CPU pairwise platen reaction diagnostics.
  int PlatenTopMkBound;        ///<Top platen mkbound value for reaction diagnostics.
  int PlatenBottomMkBound;     ///<Bottom platen mkbound value for reaction diagnostics.
  int PlatenReactionMode;      ///<Reaction diagnostic mode. 0:pairwise fluid-bound force accumulator.
  double PlatenReactionArea;   ///<Reference platen area for axial stress [m2]. <=0 disables stress conversion.
  unsigned PlatenReactionInterval; ///<Log interval in steps for platen reaction diagnostics.
  mutable unsigned PlatenReactionDiagTopCount; ///<Top platen boundary particle count.
  mutable unsigned PlatenReactionDiagBottomCount; ///<Bottom platen boundary particle count.
  mutable unsigned long long PlatenReactionDiagTopPairs; ///<Fluid-bound interaction pairs accumulated for top platen.
  mutable unsigned long long PlatenReactionDiagBottomPairs; ///<Fluid-bound interaction pairs accumulated for bottom platen.
  mutable tdouble3 PlatenReactionDiagTopForce; ///<Force on top platen from specimen pair interactions [N].
  mutable tdouble3 PlatenReactionDiagBottomForce; ///<Force on bottom platen from specimen pair interactions [N].
  mutable double PlatenReactionDiagTopAxialStress; ///<Compression-positive top axial stress from reaction [Pa].
  mutable double PlatenReactionDiagBottomAxialStress; ///<Compression-positive bottom axial stress from reaction [Pa].
  mutable double PlatenReactionDiagForceBalanceError; ///<Norm(top+bottom)/(norm(top)+norm(bottom)).
  mutable int PlatenReactionDiagLastPrintStep; ///<Last step printed for platen reaction diagnostics.
  mutable double ConfiningStressDiagP0Eff; ///<Last effective confining stress after ramp [Pa].
  mutable unsigned ConfiningStressDiagTargetCount; ///<Last target particle count.
  mutable unsigned ConfiningStressDiagLegacyTargetCount; ///<Last legacy target particle count before selectors.
  mutable unsigned ConfiningStressDiagFiSelectedCount; ///<Last f_i threshold-selected count.
  mutable unsigned ConfiningStressDiagClassInteriorCount; ///<Last cylinder interior count.
  mutable unsigned ConfiningStressDiagClassLateralCount; ///<Last cylinder lateral count.
  mutable unsigned ConfiningStressDiagClassTopCount; ///<Last cylinder top-cap count.
  mutable unsigned ConfiningStressDiagClassBottomCount; ///<Last cylinder bottom-cap count.
  mutable unsigned ConfiningStressDiagClassEdgeCount; ///<Last cylinder edge-ring count.
  mutable unsigned ConfiningStressDiagClassOutsideCount; ///<Last cylinder outside count.
  mutable unsigned ConfiningStressDiagLateralFiSelectedCount; ///<Last lateral particles below f_i threshold.
  mutable unsigned ConfiningStressDiagCapFiSelectedCount; ///<Last cap/edge particles below f_i threshold.
  mutable double ConfiningStressDiagFiMin; ///<Last f_i minimum.
  mutable double ConfiningStressDiagFiMax; ///<Last f_i maximum.
  mutable double ConfiningStressDiagFiMean; ///<Last f_i mean over legacy targets.
  mutable double ConfiningStressDiagLateralRadialAccelMean; ///<Last inward radial acceleration mean on lateral class.
  mutable double ConfiningStressDiagLateralRadialAccelMax; ///<Last inward radial acceleration max on lateral class.
  mutable double ConfiningStressDiagCapAxialAccelMean; ///<Last absolute axial acceleration mean on cap classes.
  mutable double ConfiningStressDiagCapAxialAccelMax; ///<Last absolute axial acceleration max on cap classes.
  mutable tdouble3 ConfiningStressDiagNetForce; ///<Last net confining force estimate [N].
  mutable double ConfiningStressDiagTotalAbsForce; ///<Last total absolute confining force estimate [N].
  mutable double ConfiningStressDiagMaxAccel; ///<Last maximum confining acceleration estimate [m/s2].
  mutable double ConfiningStressDiagComAccel; ///<Last center-of-mass acceleration estimate [m/s2].
  mutable double ConfiningStressDiagSymResidual; ///<Last force symmetry residual.
  mutable unsigned ConfiningStressDiagGradCorrectedCount; ///<Last renormalized-gradient corrected target count.
  mutable unsigned ConfiningStressDiagGradFallbackCount; ///<Last renormalized-gradient fallback target count.
  mutable double ConfiningStressDiagGradDetMin; ///<Last renormalized-gradient determinant minimum.
  mutable double ConfiningStressDiagGradDetMax; ///<Last renormalized-gradient determinant maximum.
  mutable int ConfiningStressDiagLastPrintStep; ///<Last step printed for confining diagnostics.
  mutable double PorePressureFeedbackDiagFactor; ///<Last applied feedback gate factor.
  mutable unsigned PorePressureFeedbackDiagAppliedCount; ///<Last feedback-applied particle count.
  mutable unsigned PorePressureFeedbackDiagSkippedClassCount; ///<Last feedback-skipped count from class filter.
  mutable unsigned PorePressureFeedbackDiagLimitedCount; ///<Last limiter activation count.
  mutable unsigned PorePressureFeedbackDiagRelaxedCount; ///<Last relaxation activation count.
  mutable double PorePressureFeedbackDiagRawMax; ///<Last raw feedback acceleration max magnitude.
  mutable double PorePressureFeedbackDiagRawMean; ///<Last raw feedback acceleration mean magnitude.
  mutable double PorePressureFeedbackDiagUsedMax; ///<Last used feedback acceleration max magnitude.
  mutable double PorePressureFeedbackDiagUsedMean; ///<Last used feedback acceleration mean magnitude.
  mutable double PorePressureFeedbackDiagPreMax; ///<Last non-feedback acceleration max magnitude.
  mutable double PorePressureFeedbackDiagRatioMax; ///<Last used/non-feedback acceleration ratio max.
  mutable double PorePressureFeedbackDiagCapValueMin; ///<Last minimum active feedback acceleration cap.
  mutable double PorePressureFeedbackDiagConfiningRef; ///<Last confining acceleration reference.
  mutable double PorePressureFeedbackDiagClassLateralMax; ///<Last lateral-class used feedback acceleration max.
  mutable double PorePressureFeedbackDiagClassCapMax; ///<Last cap/edge-class used feedback acceleration max.
  mutable double PorePressureFeedbackDiagClassInteriorMax; ///<Last interior-class used feedback acceleration max.
  mutable unsigned PorePressureFeedbackDiagLsqSolvedCount; ///<Last LSQ feedback solved count.
  mutable unsigned PorePressureFeedbackDiagLsqFallbackCount; ///<Last LSQ feedback fallback count.
  mutable double PorePressureFeedbackDiagLsqCondMin; ///<Last LSQ feedback condition proxy minimum.
  mutable double PorePressureFeedbackDiagLsqCondMax; ///<Last LSQ feedback condition proxy maximum.
  mutable double PorePressureFeedbackDiagLsqCondMean; ///<Last LSQ feedback condition proxy mean.
  mutable int PorePressureFeedbackDiagLastPrintStep; ///<Last step printed for feedback diagnostics.
  double PorePressureTopDrainedStartTime; ///<Time when top drained boundary becomes active [s].
  bool HydromechDamping;        ///<Hydromechanical kinematic damping. 0:off, 1:on.
  float HydromechDampingXi;     ///<Dimensionless damping coefficient xi. If >0, c_d=xi*sqrt(E/(rho0*h^2)).
  float HydromechDampingCoef;   ///<Effective hydromechanical damping coefficient c_d [1/s].
  double HydromechDampingStartTime; ///<Start time for hydromechanical damping [s].
  double HydromechDampingEndTime;   ///<End time for hydromechanical damping [s]. If <= start, active after start.
  bool MdbcCorrector;         ///<mDBC correction is also applied in corrector of Symplectic (default=0).
  bool MdbcFastSingle;        ///<Matrix calculations are done in single precision (default=1).
  float MdbcThreshold;        ///<Kernel support limit to apply mDBC correction (default=0).
  bool UseNormals;            ///<Indicates use of normals for mDBC.
  bool UseNormalsFt;          ///<Indicates use of normals of floating bodies for mDBC.
  bool SvNormals;             ///<Saves normals VTK each PART (default=0).

  bool RhopOut;               ///<Indicates whether the RhopOut density correction is active or not.    | Indica si activa la correccion de densidad RhopOut o no.                       
  float RhopOutMin;           ///<Minimum limit for Rhopout correction.                                 | Limite minimo para la correccion de RhopOut.
  float RhopOutMax;           ///<Maximum limit for Rhopout correction.                                 | Limite maximo para la correccion de RhopOut.

  double TimeMax;             ///<Total time to simulate [s].
  double TimePart;            ///<Time of output data [s].
  JDsOutputTime *OutputTime;  ///<Manage the use of variable output time to save PARTs.
  int NstepsBreak;            ///<Maximum number of steps allowed (debug).
  bool SvAllSteps;            ///<Saves a PART for each step (debug).
  bool NoRtimes;              ///<Removes execution dependent values from bi4 files (debug).
  ullong TerminateMt;         ///<Modification time of file TERMINATE.

  double DtIni;              ///<Initial Dt
  double DtMin;              ///<Minimum allowed Dt (if the calculated value is lower is replaced by DTmin).
  float CoefDtMin;           ///<Coefficient to calculate minimum time step. dtmin=coefdtmin*h/speedsound (def=0.03).
  bool DtAllParticles;       ///<Velocity of particles used to calculate DT. 1:All, 0:Only fluid/floating (def=0).
  JDsFixedDt *FixedDt;
  JDsSaveDt *SaveDt;

  float PartsOutMax;         ///<Allowed percentage of fluid particles out of the domain. | Porcentaje maximo de particulas excluidas permitidas.                                  
  unsigned NpMinimum;        ///<Minimum number of particles allowed.                     | Numero minimo de particulas permitidas.                                                
  unsigned PartsOutWrn;      ///<Limit percentage for warning generation about number of excluded particles in one PART.
  unsigned PartsOutTotWrn;   ///<Limit percentage for warning generation about total excluded particles.

  //-Configuration for result output.
  bool CsvSepComa;           ///<Separator character in CSV files (0=semicolon, 1=coma).
  byte SvData;               ///<Combination of the TpSaveDat values.                            | Combinacion de valores TpSaveDat.                                                      
  bool SvRes;                ///<Creates file with execution summary.                            | Graba fichero con resumen de ejecucion.
  bool SvTimers;             ///<Computes the time for each process.                             | Obtiene tiempo para cada proceso.
  bool SvDomainVtk;          ///<Stores VTK file with the domain of particles of each PART file. | Graba fichero vtk con el dominio de las particulas en cada Part. 
  //bool SvInterCount;       ///<Computes and saves number of interactions.                      | Calcula y graba el numero de interacciones.

  //-Constants for computation (from input configuration).
  float KernelH;           ///<The smoothing length of SPH kernel [m].
  float CteB;              ///<Constant used in the state equation [Pa].
  float Gamma;             ///<Politropic constant for water used in the state equation.
  float RhopZero;          ///<Reference density of the fluid [kg/m3].
  double CFLnumber;        ///<Coefficient to multiply dt.
  double Dp;               ///<Initial distance between particles [m].
  float MassFluid;         ///<Reference mass of the fluid particle [kg].
  float MassBound;         ///<Reference mass of the general boundary particle [kg].
  tfloat3 Gravity;         ///<Gravitational acceleration [m/s^2].

  //-Constants for computation (computed starting from previous constants).
  float KernelSize;        ///<Maximum interaction distance between particles (KernelK*KernelH).
  float KernelSize2;       ///<Maximum interaction distance squared (KernelSize^2).
  double Cs0;              ///<Speed of sound at the reference density.
  float Eta2;              ///<Constant related to H (Eta2=(h*0.1)*(h*0.1)).

  //-Constants for computation 2 (computed starting from previous constants).
  float SpsSmag;           ///<Smagorinsky constant used in SPS turbulence model.
  float SpsBlin;           ///<Blin constant used in the SPS turbulence model.
  float DDTkhCte;          ///<Store fixed constant DDTkh.
  float DDTkh;             ///<Constant for DDT1 & DDT2. DDTkh=DDTValue*KernelSize
  float DDTgz;             ///<Constant for DDT2.        DDTgz=RhopZero*Gravity.z/CteB

  StCteSph CSP;            ///<Structure with main SPH constants values and configurations.

  //-General information about case.
  tdouble3 CasePosMin;       ///<Lower particle limit of the case in the initial instant. | Limite inferior de particulas del caso en instante inicial.
  tdouble3 CasePosMax;       ///<Upper particle limit of the case in the initial instant. | Limite superior de particulas del caso en instante inicial.
  unsigned CaseNp;           ///<Number of total particles of initial PART.  
  unsigned CaseNfixed;       ///<Number of fixed boundary particles. 
  unsigned CaseNmoving;      ///<Number of moving boundary particles. 
  unsigned CaseNfloat;       ///<Number of floating boundary particles. 
  unsigned CaseNfluid;       ///<Number of fluid particles (including the excluded ones). 
  unsigned CaseNbound;       ///<Number of boundary particles ( \ref Nfixed + \ref Nmoving + \ref Nfloat ).
  unsigned CaseNpb;          ///<Number of particles of the boundary block ( \ref Nbound - \ref Nfloat ) or ( \ref Nfixed + \ref Nmoving).

  JSphMk *MkInfo;            ///<Stores information for the Mk of the particles.
  JDsPartsInit *PartsInit;  ///<Stores initial particles data for automatic configurations.

  //-Variables for periodic conditions.
  byte PeriActive;
  bool PeriX,PeriY,PeriZ;
  tdouble3 PeriXinc;    ///<Value that is added at the outer limit to modify the position.
  tdouble3 PeriYinc;    ///<Value that is added at the outer limit to modify the position.
  tdouble3 PeriZinc;    ///<Value that is added at the outer limit to modify the position.

  //-Variables to restart simulation.
  std::string PartBeginDir;   ///<Searches directory for starting PART.                   | Directorio donde busca el PART de arranque.
  unsigned PartBegin;         ///<Indicates the start (0: no resumption).                 | Indica el PART de arranque (0:Sin reanudacion).
  unsigned PartBeginFirst;    ///<Indicates the number of the first PART to be generated. | Indica el numero del primer PART a generar.                                    
  double PartBeginTimeStep;   ///<initial instant of the simulation                       | Instante de inicio de la simulacion.                                          
  ullong PartBeginTotalNp;    ///<Total number of simulated particles.
  bool RestartChrono;         ///<Allows restart with Chrono active (default=0).

  JDsPartsOut *PartsOut;        ///<Stores excluded particles until they are saved. | Almacena las particulas excluidas hasta su grabacion.
  bool WrnPartsOut;           ///<Active warning according to number of out particles (default=1).

  //-Variables for predefined movement.
  JDsMotion *DsMotion;      ///<Manages moving objects. It is NULL when there are not moving objects.

  //-Variables for floating bodies.
  StFloatingData *FtObjs;        ///<Data of floating objects. [FtCount]
  unsigned FtCount;              ///<Number of floating objects.
  float FtPause;                 ///<Time to start floating bodies movement.
  TpRigidMode RigidMode;         ///<Rigid Algorithm 0:collision-free, 1:SPH, 2:DEM, 3:Chrono (default=1).
  TpFtMode FtMode;               ///<Defines interaction mode for floatings and boundaries.
  bool FtConstraints;            ///<Some floating motion constraint is defined.
  JLinearValue **FtLinearVel;    ///<Imposed linear velocity [FtCount].
  JLinearValue **FtAngularVel;   ///<Imposed angular velocity [FtCount].
  JLinearValue **FtLinearForce;  ///<Added linear force [FtCount].
  JLinearValue **FtAngularForce; ///<Added angular force [FtCount].
  bool FtIgnoreRadius;           ///<Ignores floating body radius with periodic boundary conditions (def=false).
  bool WithFloating;

  //-Variables for DEM (DEM).
  bool UseDEM;         ///<Use DEM for boundary collisions.
  static const unsigned DemDataSize=CODE_TYPE_FLUID;
  StDemData *DemData;  ///<Data of DEM objects. [DemDataSize]

  //-Variables for Chrono use.
  bool UseChrono;  ///<Use Chrono library for rigid body dynamics.
  JChronoObjects *ChronoObjects;  ///<Object for integration with Chrono Engine.

  JDsMooredFloatings* Moorings;     ///<Manages floating bodies with moorings. | Gestiona floating bodies con amarres.
  JDsFtForcePoints* ForcePoints; ///<Manages forces to apply on floating bodies.

  std::vector<std::string> InitializeInfo; ///<Stores information about initialize configuration applied.

  JNumexLib *NuxLib;            ///<Object to evaluate user-defined expressions in XML.

  JGaugeSystem *GaugeSystem;    ///<Object for automatic gauge system.

  JWaveGen *WaveGen;            ///<Object for wave generation.

  JMLPistons *MLPistons;        ///<Object for Multi-Layer Pistons.

  JRelaxZones *RelaxZones;      ///<Object for wave generation using Relaxation Zone (RZ).

  JSphShifting *Shifting;       ///<Object for shifting correction.
  TpShifting ShiftingMode;      ///<Mode of Shifting: None, NoBound, NoFixed, Full.

  JDsDamping *Damping;          ///<Object for damping zones.

  JDsAccInput *AccInput;    ///<Object for variable acceleration functionality.

  JSphInOut *InOut;         ///<Object for inlet/outlet conditions.

  JFtMotionSave *FtMotSave; ///<Object for saving floating motion data with high frequency. //<vs_ftmottionsv>

  std::string SvExtraParts;         ///<Part interval (or list) for saving extra data for restart option (default=empty=disabled)
  JDsExtraDataSave *SvExtraDataBi4; ///<To store extra data for restart option (SvExtraParts).

  JDsPips *DsPips;          ///<Object for PIPS calculation.

  //-Variables for division in cells.
  bool CellDomFixed;       ///<The Cell domain is fixed according maximum domain size.
  TpCellMode CellMode;     ///<Cell division mode.
  int ScellDiv;            ///<Value to divide KernelSize (1 or 2).
  float Scell;             ///<Cell size: KernelSize/ScellDiv (KernelSize or KernelSize/2).
  float MovLimit;          ///<Maximum distance a particle is allowed to move in one step (Scell*0.9).

  float PosCellSize;       ///<Size of cells used for coding PosCell on GPU (it is usually KernelSize).

  //-Defines global domain of the simulation.
  tdouble3 MapRealPosMin;  ///<Real lower limit of simulation (without the periodic condition borders). MapRealPosMin=CasePosMin-(H*BORDER_MAP) | Limite inferior real de simulacion (sin bordes de condiciones periodicas).
  tdouble3 MapRealPosMax;  ///<Real upper limit of simulation (without the periodic condition borders). MapRealPosMax=CasePosMax+(H*BORDER_MAP) | Limite superior real de simulacion (sin bordes de condiciones periodicas).
  tdouble3 MapRealSize;    ///<Result of MapRealSize = MapRealPosMax - MapRealPosMin

  tdouble3 Map_PosMin;     ///<Lower limit of simulation + edge (KernelSize) if periodic conditions. Map_PosMin=MapRealPosMin-KernelSize(in periodic axis) | Limite inferior de simulacion + borde (KernelSize) si hay condiciones periodicas.
  tdouble3 Map_PosMax;     ///<Upper limit of simulation + edge (KernelSize) if periodic conditions. Map_PosMax=MapRealPosMax+KernelSize(in periodic axis) | Limite superior de simulacion + borde (KernelSize) si hay condiciones periodicas.
  tdouble3 Map_Size;       ///<Result of Map_Size = Map_PosMax - Map_PosMin
  tuint3 Map_Cells;        ///<Maximum number of cells within case limits. Map_Cells=TUint3(unsigned(ceil(Map_Size.xyz/Scell))             | Numero de celdas maximo segun los limites del caso.

  //-Local domain of the simualtion.
  //-Dominio local de la simulacion.
  tuint3 DomCelIni;        ///<First cell within the Map defining local simulation area. DomCelIni=TUint3(0) for Single-CPU | Celda inicial dentro de Map que define el area de simulacion local.
  tuint3 DomCelFin;        ///<Last cell within the Map defining local simulation area. DomCelIni=Map_Cells for Single-CPU  | Celda final dentro de Map que define el area de simulacion local.
  tuint3 DomCells;         ///<Number of cells in each direction. DomCells=DomCelFin-DomCelIni                              | Numero de celdas en cada direccion.                                                                

  tdouble3 DomPosMin;      ///<Lower limit of simulation + edge (KernelSize) if periodic conditions. DomPosMin=Map_PosMin+(DomCelIni*Scell); | Limite inferior de simulacion + borde (KernelSize) si hay condiciones periodicas. 
  tdouble3 DomPosMax;      ///<Upper limit of simulation + edge (KernelSize) if periodic conditions. DomPosMax=min(Map_PosMax,Map_PosMin+(DomCelFin*Scell)); | Limite inferior de simulacion + borde (KernelSize) si hay condiciones periodicas. 
  tdouble3 DomSize;        ///<Result of DomSize = DomPosMax - DomPosMin

  tdouble3 DomRealPosMin;  ///<Real lower limit of the simulation according to DomCelIni/Fin (without periodic condition borders) DomRealPosMin=max(DomPosMin,MapRealPosMin) | Limite real inferior de simulacion segun DomCelIni/Fin (sin bordes de condiciones periodicas).
  tdouble3 DomRealPosMax;  ///<Real upper limit of the simulation according to DomCelIni/Fin (without periodic condition borders) DomRealPosMax=min(DomPosMax,MapRealPosMax) | Limite real superior de simulacion segun DomCelIni/Fin (sin bordes de condiciones periodicas).
  unsigned DomCellCode;    ///<Key for encoding cell position within the Domain. | Clave para la codificacion de la celda de posicion dentro de Domain.

  //-Controls particle number.
  bool NpDynamic;          ///<CaseNp can increase.
  bool ReuseIds;           ///<Id of particles excluded values ​​are reused.
  ullong TotalNp;          ///<Total number of simulated particles (no cuenta las particulas inlet no validas).
  unsigned IdMax;          ///<It is the maximum Id used.

  //-Monitors dt value.
  unsigned DtModif;       ///<Number of modifications on  dt computed when it is too low. | Numero de modificaciones del dt calculado por ser demasiado bajo.         
  unsigned DtModifWrn;    ///<Limit number for warning generation.
  double PartDtMin;       ///<Minimum value of dt in the current PART. | Valor minimo de dt en el PART actual.
  double PartDtMax;       ///<Maximum value of dt in the current PART. | Valor maximo de dt en el PART actual.
  
  //-Variables for simulation of PARTs.
  int PartIni;            ///<First generated PART.  | Primer PART generado. 
  int Part;               ///<Saves subsequent PART. | Siguiente PART a guardar.                                          
  int Nstep;              ///<Number of step in execution.             | Numero de paso en ejecucion.
  int PartNstep;          ///<Number of step when last PART was saved. | Numero de paso en el que se guardo el ultimo PART.
  unsigned PartOut;       ///<Total number of excluded particles. | Numero total de particulas excluidas al grabar el ultimo PART.
  double TimeStepIni;     ///<Initial instant of the simulation. | Instante inicial de la simulacion.
  double TimeStep;        ///<Current instant of the simulation. | Instante actual de la simulacion.                                 
  double TimeStepM1;      ///<Instant of the simulation when the last PART was stored. | Instante de la simulacion en que se grabo el ultimo PART.         
  double TimePartNext;    ///<Instant to store next PART file.   | Instante para grabar siguiente fichero PART.
  double LastDt;          ///<Last dt value added to TimeStep. | Ultimo valor de dt sumado a TimeStep.

  //-Control of the execution times.
  JTimer TimerTot;         ///<Measueres total runtime.                          | Mide el tiempo total de ejecucion.
  JTimer TimerSim;         ///<Measueres runtime since first step of simulation. | Mide el tiempo de ejecucion desde el primer paso de calculo.
  JTimer TimerPart;        ///<Measueres runtime since last PART.                | Mide el tiempo de ejecucion desde el ultimo PART.
  
  //-Execution variables.
  JPartsLoad4 *PartsLoaded;
  TpInterStep InterStep;
  int VerletStep;
  double SymplecticDtPre;  ///<Previous Dt to use with Symplectic.
  double DemDtForce;       ///<Dt for tangencial acceleration.
  StMaxNumbers MaxNumbers; ///<Maximum values (or almost) achieved during the simulation.


  bool SaveFtAce;    ///<Indicates whether linear and angular accelerations of each floating objects are saved.
  void SaveFtAceFun(double dt,bool predictor,StFtoForces *ftoforces);


protected:
  void AllocMemoryFloating(unsigned ftcount,bool imposedvel=false,bool addedforce=false);
  llong GetAllocMemoryCpu()const;


  void LoadConfig(const JSphCfgRun *cfg);
  void LoadKernelSelection(const JSphCfgRun *cfg,const JXml *xml);
  void LoadConfigCtes(const JXml *xml);
  void LoadConfigVars(const JXml *xml);
  void LoadConfigVarsExec();
  void LoadConfigParameters(const JXml *xml);
  void LoadConfigCommands(const JSphCfgRun *cfg);
  void LoadCaseConfig(const JSphCfgRun *cfg);

  StDemData LoadDemData(bool checkdata,const JCasePartBlock* block)const;
  void VisuDemCoefficients()const;

  void LoadCodeParticles(unsigned np,const unsigned *idp,typecode *code)const;
  void LoadBoundNormals(unsigned np,unsigned npb,const unsigned *idp,const typecode *code,tfloat3 *boundnormal);
  void ConfigBoundNormals(unsigned np,unsigned npb,const tdouble3 *pos,const unsigned *idp,tfloat3 *boundnormal);

  void PrepareCfgDomainValues(tdouble3 &v,tdouble3 vdef=TDouble3(0))const;
  void ResizeMapLimits();

  void ConfigConstants1(bool simulate2d);
  void ConfigConstants2();
  void VisuConfig();
  void VisuRefs();
  void VisuParticleSummary()const;
  double GetPorePressureFeedbackFactor(double timestep)const;
  bool HasNonDefaultPorePressureFeedbackStabilization()const;
  void LoadDcellParticles(unsigned n,const typecode *code,const tdouble3 *pos,unsigned *dcell)const;
  void RunInitialize(unsigned np,unsigned npb,const tdouble3 *pos,const unsigned *idp
    ,const typecode *code,tfloat4 *velrhop,tfloat3 *boundnormal);
  void CreatePartsInit(unsigned np,const tdouble3 *pos,const typecode *code);
  void FreePartsInit();

  void ConfigCellDivision();
  void SelecDomain(tuint3 celini,tuint3 celfin);
  void ConfigPosCellGpu();
  void CalcFloatingRadius(unsigned np,const tdouble3 *pos,const unsigned *idp);
  tdouble3 UpdatePeriodicPos(tdouble3 ps)const;

  void RestartCheckData(bool loadpsingle);
  void CheckRhopLimits();
  void LoadCaseParticles();
  void InitRun(unsigned np,const unsigned *idp,const tdouble3 *pos);

  void WavesInit(JGaugeSystem *gaugesystem,const JSphMk *mkinfo,double timemax,double timepart);
  void WavesLoadLastGaugeResults();
  void WavesUpdateGaugePoints();

  tfloat3 GetFtExternalForceLin(unsigned cf,double timestep)const;
  tfloat3 GetFtExternalForceAng(unsigned cf,double timestep)const;

  bool CalcMotion(double stepdt);
  void CalcMotionWaveGen(double stepdt);
  void ChronoFtApplyImposedVel();
  void PrintSizeNp(unsigned np,llong size,unsigned allocs)const;
  void PrintHeadPart();

  void ConfigSaveData(unsigned piece,unsigned pieces,std::string div);
  void ConfigFtMotionSave(unsigned np,const tdouble3 *pos,const unsigned *idp); //<vs_ftmottionsv>
  void AddParticlesOut(unsigned nout,const unsigned *idp,const tdouble3 *pos,const tfloat3 *vel,const float *rhop,const typecode *code);
  void AbortBoundOut(JLog2 *log,unsigned nout,const unsigned *idp,const tdouble3 *pos,const tfloat3 *vel,const float *rhop,const typecode *code);

  tfloat3* GetPointerDataFloat3(unsigned n,const tdouble3* v)const;
  void AddBasicArrays(JDataArrays &arrays,unsigned np,const tdouble3 *pos
    ,const unsigned *idp,const tfloat3 *vel,const float *rhop
    ,const tfloat3 *sigma_kk,const tfloat3 *sigma_ab,const float *kplastic)const;//ruofeng
  void AddBasicArrays(JDataArrays &arrays,unsigned np,const tdouble3 *pos
    ,const unsigned *idp,const tfloat3 *vel,const float *rhop)const;
  void SavePartData(unsigned npok,unsigned nout,const JDataArrays& arrays,unsigned ndom,const tdouble3 *vdom,const StInfoPartPlus *infoplus);
  void SaveData(unsigned npok,const JDataArrays& arrays,unsigned ndom,const tdouble3 *vdom,const StInfoPartPlus *infoplus);

  bool UseCustomHydraulicGravity()const;
  tfloat3 GetHydraulicGravity()const;
  tfloat3 GetMechanicalGravity(double timestep)const;
  bool IsMechanicalGravityStopped(double timestep)const;
  double GetFlexibleConfiningStressP0(double timestep)const;
  double GetCapConfiningStressP0(double timestep)const;
  bool IsFlexibleConfiningStressTarget(typecode code)const;
  int GetConfiningStressCylinderClass(const tdouble3 &pos)const;
  void ResetFlexibleConfiningStressDiagnostics()const;
  void PrintFlexibleConfiningStressDiagnostics()const;
  void ResetCapConfiningStressDiagnostics()const;
  void PrintCapConfiningStressDiagnostics()const;
  void ResetPlatenReactionDiagnostics()const;
  void PrintPlatenReactionDiagnostics()const;
  void ResetPorePressureFeedbackDiagnostics()const;
  void PrintPorePressureFeedbackDiagnostics()const;
  double GetHydraulicGmag()const;
  double GetHydraulicElevation(const tdouble3 &pos)const;
  double GetHydrostaticPorePressure(const tdouble3 &pos)const;

  void CheckTermination();
  void SaveDomainVtk(unsigned ndom,const tdouble3 *vdom)const;
  void SaveInitialDomainVtk()const;
  unsigned SaveMapCellsVtkSize()const;
  void SaveMapCellsVtk(float scell)const;
  void SaveVtkNormals(std::string filename,int numfile,unsigned np,unsigned npb
    ,const tdouble3 *pos,const unsigned *idp,const tfloat3 *boundnormal,float resize)const;
 
  void GetResInfo(float tsim,float ttot,std::string headplus,std::string detplus
    ,std::string &hinfo,std::string &dinfo)const;
  void SaveRes(float tsim,float ttot,const std::string &headplus="",const std::string &detplus="");
  void ShowResume(bool stop,float tsim,float ttot,bool all,std::string infoplus);

  unsigned GetOutPosCount()const{ return(OutPosCount); }
  unsigned GetOutRhopCount()const{ return(OutRhopCount); }
  unsigned GetOutMoveCount()const{ return(OutMoveCount); }

public:
  JSph(bool cpu,bool mgpu,bool withmpi);
  ~JSph();

  static std::string GetStepName(TpStep tstep);
  static std::string GetViscoName(TpVisco tvisco);
  static std::string GetBoundName(TpBoundary tboundary);
  static std::string GetSlipName(TpSlipMode tslip);
  static std::string GetDPName(TpDPCtes dpctes);
  std::string GetDDTName(TpDensity tdensity)const;

  std::string GetDDTConfig()const;

//-Functions for debug.
//----------------------
public:
  unsigned DgNum;
  void DgSaveVtkParticlesCpu(std::string filename,int numfile,unsigned pini,unsigned pfin,const tdouble3 *pos,const typecode *code,const unsigned *idp,const tfloat4 *velrhop,const tfloat3 *ace=NULL)const;
  void DgSaveVtkParticlesCpu(std::string filename,int numfile,unsigned pini,unsigned pfin,const tfloat3 *pos,const byte *check,const unsigned *idp,const tfloat3 *vel,const float *rhop);
  void DgSaveCsvParticlesCpu(std::string filename,int numfile,unsigned pini,unsigned pfin,std::string head,const tfloat3 *pos,const unsigned *idp=NULL,const tfloat3 *vel=NULL,const float *rhop=NULL,const float *ar=NULL,const tfloat3 *ace=NULL,const tfloat3 *vcorr=NULL);

  //-mdbr - Soil modelling
// Variables and methods.  
//------------------------------------------
protected:
  StSoilCte SoilCte;       ///<Contains constants of soils.

  void InitSoilParameters(const JXml *sxml,std::string xmlpath);
  void ConfigConstantsSoil();
};

//-----
/*:
ES: (2h se refiere a KernelSize)
Consideraciones sobre condiciones periodicas:
- Para cada eje periodico se define un valor tfloat3 para sumar a las particulas
  que se salgan por el extremo superior del dominio.
- En MapPosMin/Max se el anhade una holgura de H*BORDER_MAP, pero en el caso de
  condiciones periodicas esta holgura solo se aplica a MapPosMax.
- El ajuste de tamanho de dominio realizado por ResizeMapLimits() no afecta a los
  ejes periodicos.
- El halo periodico tendra una unica celda de grosor 2h aunque en los otros ejes
  se use celdas de tamanho h.
- En la interaccion, una celda de tamanho 2h o dos celdas de tamanho h del extremo 
  inferior interaccionan con el halo periodico. En el caso del extremo superior
  deben ser 2 celdas de 2h o 3 celdas de h.
EN:
Considerations for periodic conditions:
- For each periodic edge a tfloat3 value is defined to be added to the particles
   that they get out at the limits of the domain.
- In MapPosMin/Max there is the added space of H*BORDER_MAP, but in the case of
   periodic conditions this space only applies to MapPosMax.
- The adjustment of the domain size by ResizeMapLimits() does not affect the
   periodic edges.
- The periodic halo will have a single cell thick 2h although in the other axes
   h cell size is used.
- In the interaction, a cell of size 2h or two cells of size h in the
   lower end interact with the periodic halo. For the upper limit
   there must be either 2 2h cells or 3 h cells.
:*/

#endif


