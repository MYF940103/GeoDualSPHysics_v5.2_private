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

/// \file JSphCpu_porepressure.cpp \brief CPU pore-pressure rates, boundary conditions and time updates.

#include "JSphCpu.h"
#include "JCellSearch_inline.h"
#include "JArraysCpu.h"
#include "Functions.h"
#include "FunSphKernel.h"
#include "FunExternalLoad.h"
#include "TpiPressureRow.h"

#include <cfloat>
#include <cmath>
#include <limits>

using namespace std;

//==============================================================================
/// Initialises pore pressure and optional effective stress for hydromechanics.
//==============================================================================
void JSphCpu::InitHydroMechState(){
  if(!HydroMech || !PorePressc || !PorePress0c)return;
  if(HydroMechInitMode==HMINIT_None)return;
  const double gnorm=sqrt(double(Gravity.x)*Gravity.x+double(Gravity.y)*Gravity.y+double(Gravity.z)*Gravity.z);
  const double gzabs=fabs(double(Gravity.z));
  const double gammaw=double(SoilCte.PoreWaterRho)*(gzabs>0? gzabs: gnorm);
  unsigned nfs=0;
  unsigned *fsp=NULL;
  if(HydroMechInitMode==HMINIT_FreeSurface){
    if(!FSTypec || !FSNormalc)Run_Exceptioon("Free-surface tracking data is required for HydroMechInitMode=FreeSurface.");
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p]) && IsFreeSurfaceParticle(p,Codec,FSTypec))nfs++;
    if(!nfs)Run_Exceptioon("No free-surface particles were found for hydromechanical pore-pressure initialization.");
    try{
      fsp=new unsigned[nfs];
    }
    catch(const std::bad_alloc){
      Run_Exceptioon("Could not allocate the requested memory.");
    }
    unsigned c=0;
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p]) && IsFreeSurfaceParticle(p,Codec,FSTypec))fsp[c++]=p;
  }

  double pmin=DBL_MAX,pmax=-DBL_MAX;
  double smin=DBL_MAX,smax=-DBL_MAX;
  double topz=-DBL_MAX;
  bool analyticgravityoff=false;
  double analyticg=gnorm;
  if(HydroMechInitMode==HMINIT_AnalyticalSelfWeight1D){
    analyticgravityoff=(gnorm<=1e-12);
    if(analyticgravityoff)analyticg=9.80665;
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsFluid(Codec[p]))topz=max(topz,Posc[p].z);
    if(topz==-DBL_MAX)Run_Exceptioon("HydroMechInitMode=AnalyticalSelfWeight1D requires soil particles.");
    topz+=double(Dp)*0.5;
  }
  for(unsigned p=0;p<Np;p++){
    double zwt=HydroMechInitZ;
    if(HydroMechInitMode==HMINIT_FreeSurface){
      const tdouble3 ps=Posc[p];
      double distmin=DBL_MAX;
      unsigned pnear=fsp[0];
      for(unsigned c=0;c<nfs;c++){
        const tdouble3 pf=Posc[fsp[c]];
        const double dx=ps.x-pf.x;
        const double dy=(Simulate2D? 0: ps.y-pf.y);
        const double dist2=dx*dx+dy*dy;
        if(dist2<distmin){
          distmin=dist2;
          pnear=fsp[c];
        }
      }
      zwt=Posc[pnear].z;
    }
    if(HydroMechInitMode==HMINIT_AnalyticalSelfWeight1D){
      const tdouble3 pposhydro=Posc[p];
      tdouble3 pposexcess=Posc[p];
      if(!CODE_IsFluid(Codec[p]) && BoundNormalc && BoundNormalc[p]!=TFloat3(0)){
        pposexcess=Posc[p]+ToTDouble3(BoundNormalc[p]);
        if(PeriActive)pposexcess=UpdatePeriodicPos(pposexcess);
      }
      const double depthhydro=max(0.,topz-pposhydro.z);
      const double depthghost=max(0.,topz-pposexcess.z);
      const double kwn=double(SoilCte.PoreWaterBulkModulus)/double(SoilCte.Porosity);
      const double mcon=double(SoilCte.ModulusK)+4.0*double(SoilCte.ModulusG)/3.0;
      const double undrained_ratio=kwn/(mcon+kwn);
      const double effective_ratio=mcon/(mcon+kwn);
      const double rhosw=(analyticgravityoff? double(RhopZero): max(0.,double(RhopZero)-double(SoilCte.PoreWaterRho)));
      const double hydroactual=double(SoilCte.PoreWaterRho)*analyticg*depthhydro;
      const double excessghost=undrained_ratio*rhosw*analyticg*depthghost;
      float hydro=(analyticgravityoff? 0.f: float(hydroactual));
      float pw=(analyticgravityoff? float(excessghost): float(hydroactual+excessghost));
      if(p>=Npb && IsFreeSurfaceParticle(p,Codec,FSTypec)){
        hydro=0.f;
        pw=0.f;
      }
      PorePressc[p]=pw;
      PorePress0c[p]=hydro;
      if(Sigmac){
        const float szz=float(-effective_ratio*rhosw*analyticg*depthghost);
        const float k0=float(SoilCte.PRvs/(1.f-SoilCte.PRvs));
        tsymatrix3f sig={k0*szz,0.f,0.f,k0*szz,0.f,szz};
        Sigmac[p]=ToTSymMatrix3d(sig);
        smin=min(smin,double(szz));
        smax=max(smax,double(szz));
      }
    }
    else{
      float pw=float(gammaw*max(0.,zwt-Posc[p].z));
      //-Extend the dynamic hydrostatic baseline affinely through fixed wall samples.
      if(DynamicPorePressure && HydroMechInitMode==HMINIT_ConstantZ && p<Npb)
        pw=float(gammaw*(zwt-Posc[p].z));
      if(HydroMechInitMode==HMINIT_FreeSurface && p>=Npb && IsFreeSurfaceParticle(p,Codec,FSTypec))pw=0.f;
      PorePressc[p]=pw;
      PorePress0c[p]=pw;
    }
    pmin=min(pmin,double(PorePressc[p]));
    pmax=max(pmax,double(PorePressc[p]));
  }
  delete[] fsp; fsp=NULL;
  Log->Printf("Hydromechanics: initial pore pressure assigned to %u particles (%s, min=%g, max=%g)."
    ,Np,GetHydroMechInitModeName(HydroMechInitMode).c_str(),pmin,pmax);
  if(HydroMechInitMode==HMINIT_AnalyticalSelfWeight1D){
    Log->Printf("Hydromechanics: analytical 1D self-weight mode=%s, reference gravity=%g, hydrostatic baseline=%s."
      ,(analyticgravityoff? "gravity-off dissipation": "gravity-on self-weight"),analyticg,(analyticgravityoff? "zero": "retained"));
    Log->Printf("Hydromechanics: analytical 1D self-weight effective stress initialized (sigma_zz min=%g, max=%g).",smin,smax);
  }
}

//==============================================================================
/// Enforces drained pore pressure on free-surface soil particles.
//==============================================================================
void JSphCpu::ApplyFreeSurfacePorePressure(){
  if(!HydroMech || !PorePressc || !FSTypec)return;
  if(!IsHydroMechDrainageActive()){
    ApplyYaoTopStripPorePressureExtrapolation();
    return;
  }
  const int pini=int(Npb),pfin=int(Np);
  #ifdef OMP_USE
    #pragma omp parallel for schedule(static) if((pfin-pini)>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int p=pini;p<pfin;p++){
    if(IsHydroMechDrainedParticle(unsigned(p),Posc,Codec,FSTypec)){
      PorePressc[p]=0;
      if(DynamicPorePressure)PorePressRatec[p]=0;
    }
  }
  if(DynamicPorePressure && PeriActive){
    //-Projection changes native p after periodic cloning; refresh the same-stage neighbours.
    unsigned* ridp=GetDynamicPeriodicMapCpu();
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsPeriodic(Codec[p]))PorePressc[p]=PorePressc[ridp[Idpc[p]]];
    ArraysCpu->Free(ridp);
  }
  ApplyYaoTopStripPorePressureExtrapolation();
}

//==============================================================================
/// Extrapolates pore pressure to the impermeable Yao strip contact surface.
//==============================================================================
template<TpKernel tker,bool sim2d> void JSphCpu::ApplyYaoTopStripPorePressureExtrapolationT(){
  if((HydroMechTopLoadMode!=HMLOAD_TopStripVertical && HydroMechTopLoadMode!=HMLOAD_LianFlexibleStrip) || !PorePressc || !Posc || !Velrhopc || !Codec || !FSTypec || !DivData.begincell)return;
  const int pini=int(Npb),pfin=int(Np);
  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided)
  #endif
  for(int p1=pini;p1<pfin;p1++){
    if(!CODE_IsFluid(Codec[p1]) || !IsFreeSurfaceParticle(unsigned(p1),Codec,FSTypec) || !externalload::IsStripSurface(HydroMechTopLoadMode,Posc[p1].x,Posc[p1].z,double(Dp)))continue;
    const tdouble3 posp1=Posc[p1];
    double sumwab=0,pwsum=0;
    const StNgSearch ngs=nsearch::Init(Dcellc[p1],false,DivData);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 pif=nsearch::ParticleRange(y,z,ngs,DivData);
      for(unsigned p2=pif.x;p2<pif.y;p2++){
        if(p2==unsigned(p1) || !CODE_IsFluid(Codec[p2]) || Velrhopc[p2].w<=0)continue;
        if(externalload::IsStripSurface(HydroMechTopLoadMode,Posc[p2].x,Posc[p2].z,double(Dp)))continue;
        if(Posc[p2].z>posp1.z-0.25*double(Dp))continue;
        const double drx=posp1.x-Posc[p2].x;
        const double dry=(sim2d? 0: posp1.y-Posc[p2].y);
        const double drz=posp1.z-Posc[p2].z;
        const float rr2=float(drx*drx+dry*dry+drz*drz);
        if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
          const double vol2=double(MassFluid/Velrhopc[p2].w);
          const double wab=double(fsph::GetKernel_Wab<tker>(CSP,rr2))*vol2;
          sumwab+=wab;
          pwsum+=wab*double(PorePressc[p2]);
        }
      }
    }
    if(sumwab>0)PorePressc[p1]=float(pwsum/sumwab);
  }
}

//==============================================================================
/// Selects pore-pressure extrapolation for the impermeable Yao strip surface.
//==============================================================================
void JSphCpu::ApplyYaoTopStripPorePressureExtrapolation(){
  if(HydroMechTopLoadMode!=HMLOAD_TopStripVertical && HydroMechTopLoadMode!=HMLOAD_LianFlexibleStrip)return;
  if(Simulate2D){
    switch(TKernel){
      case KERNEL_Wendland: ApplyYaoTopStripPorePressureExtrapolationT<KERNEL_Wendland,true >(); break;
      case KERNEL_Cubic:    ApplyYaoTopStripPorePressureExtrapolationT<KERNEL_Cubic   ,true >(); break;
      default: Run_Exceptioon("Kernel unknown.");
    }
  }
  else{
    switch(TKernel){
      case KERNEL_Wendland: ApplyYaoTopStripPorePressureExtrapolationT<KERNEL_Wendland,false>(); break;
      case KERNEL_Cubic:    ApplyYaoTopStripPorePressureExtrapolationT<KERNEL_Cubic   ,false>(); break;
      default: Run_Exceptioon("Kernel unknown.");
    }
  }
}

//==============================================================================
/// Computes dpw/dt for the explicit u-pw pressure-rate formulation.
//==============================================================================
template<TpKernel tker,bool sim2d> void JSphCpu::InteractionPorePressureRateT
  (unsigned np,unsigned npb,StDivDataCpu divdata,const unsigned *dcell
  ,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code
  ,const tmatrix3d *corrmat,const unsigned *fstype,const tfloat3 *fsnormal,const float *porepress,float *porepressrate)const
{
  const double gnorm=sqrt(double(Gravity.x)*Gravity.x+double(Gravity.y)*Gravity.y+double(Gravity.z)*Gravity.z);
  const double ghyd=(gnorm>0? gnorm: 9.80665);
  const double kw=double(SoilCte.PoreWaterBulkModulus);
  const double por=double(SoilCte.Porosity);
  const double khyd=double(SoilCte.HydraulicConductivity);
  const double kwn=kw/por;
  const bool drainfs=IsHydroMechDrainageActive();
  const int pini=int(npb),pfin=int(np);
  memset(porepressrate,0,sizeof(float)*np);
  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided)
  #endif
  for(int p1=pini;p1<pfin;p1++){
    if(!CODE_IsFluid(code[p1]))continue;
    if(drainfs && IsHydroMechDrainedParticle(unsigned(p1),pos,code,fstype)){
      porepressrate[p1]=0;
      continue;
    }
    const tdouble3 posp1=pos[p1];
    const tfloat4 vrp1=velrhop[p1];
    const float pwp1=porepress[p1];
    const tmatrix3d lmat=(corrmat? corrmat[p1]: TMatrix3d());
    double divv=0,lapw=0,lapz=0;

    for(int b2=0;b2<2;b2++){
      const bool boundp2=(b2==1);
      const StNgSearch ngs=nsearch::Init(dcell[p1],boundp2,divdata);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
        const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
        for(unsigned p2=pif.x;p2<pif.y;p2++){
          if(!boundp2 && !CODE_IsFluid(code[p2]))continue;
          const TpSlipMode slipmodep2=(boundp2 && BoundSlipModec? TpSlipMode(BoundSlipModec[p2]): SlipMode);
          if(boundp2 && TBoundary==BC_MDBC && slipmodep2>=SLIP_NoSlip && BoundModec && BoundModec[p2]==BMODE_MDBC2OFF)continue;
          const double drx=posp1.x-pos[p2].x;
          const double dry=(sim2d? 0: posp1.y-pos[p2].y);
          const double drz=posp1.z-pos[p2].z;
          const float rr2=float(drx*drx+dry*dry+drz*drz);
          if(rr2<=KernelSize2 && rr2>=ALMOSTZERO && velrhop[p2].w>0){
            const double fac=double(fsph::GetKernel_Fac<tker>(CSP,rr2));
            const double frx=fac*drx;
            const double fry=(sim2d? 0: fac*dry);
            const double frz=fac*drz;
            const double cfrx=lmat.a11*frx+lmat.a12*fry+lmat.a13*frz;
            const double cfry=lmat.a21*frx+lmat.a22*fry+lmat.a23*frz;
            const double cfrz=lmat.a31*frx+lmat.a32*fry+lmat.a33*frz;
            const double dcfrx=(PoreCompressionGradCorr? cfrx: frx);
            const double dcfry=(PoreCompressionGradCorr? cfry: fry);
            const double dcfrz=(PoreCompressionGradCorr? cfrz: frz);
            const double vol2=double((boundp2? MassBound: MassFluid)/velrhop[p2].w);
            const tfloat4 vrp2=velrhop[p2];
            const double dvx=double(vrp2.x)-double(vrp1.x);
            const double dvy=(sim2d? 0: double(vrp2.y)-double(vrp1.y));
            const double dvz=double(vrp2.z)-double(vrp1.z);
            const double dotgrad=drx*cfrx+dry*cfry+drz*cfrz;
            divv+=vol2*(dvx*dcfrx+dvy*dcfry+dvz*dcfrz);
            if(khyd>0){
              const double dz=posp1.z-pos[p2].z;
              const double pwp2=double(porepress[p2]);
              // mDBC pore pressure already stores the hydraulic ghost value used by Darcy diffusion.
              const double pwp2seep=pwp2;
              lapw+=vol2*(double(pwp1)-pwp2seep)*dotgrad/double(rr2+Eta2);
              lapz+=vol2*dz*dotgrad/double(rr2+Eta2);
            }
          }
        }
      }
    }
    // Current velocity-gradient convention is tensile-positive; compression is -div(v_s).
    const double compression=-divv;
    const double seepage=(khyd>0? 2.0*khyd*lapw/(double(SoilCte.PoreWaterRho)*ghyd) + (gnorm>0? 2.0*khyd*lapz: 0.0): 0.0);
    const double rate=kwn*compression + kwn*seepage;
    porepressrate[p1]=float(rate);
  }
}

//==============================================================================
/// Selects the compiled pore-pressure-rate interaction.
//==============================================================================
void JSphCpu::InteractionPorePressureRate(){
  if(!HydroMech || !PorePressc || !PorePressRatec)return;
  ApplyFreeSurfacePorePressure();
  if(Simulate2D){
    switch(TKernel){
      case KERNEL_Wendland: InteractionPorePressureRateT<KERNEL_Wendland,true >(Np,Npb,DivData,Dcellc,Posc,Velrhopc,Codec,CorrMatc,FSTypec,FSNormalc,PorePressc,PorePressRatec); break;
      case KERNEL_Cubic:    InteractionPorePressureRateT<KERNEL_Cubic   ,true >(Np,Npb,DivData,Dcellc,Posc,Velrhopc,Codec,CorrMatc,FSTypec,FSNormalc,PorePressc,PorePressRatec); break;
      default: Run_Exceptioon("Kernel unknown.");
    }
  }
  else{
    switch(TKernel){
      case KERNEL_Wendland: InteractionPorePressureRateT<KERNEL_Wendland,false>(Np,Npb,DivData,Dcellc,Posc,Velrhopc,Codec,CorrMatc,FSTypec,FSNormalc,PorePressc,PorePressRatec); break;
      case KERNEL_Cubic:    InteractionPorePressureRateT<KERNEL_Cubic   ,false>(Np,Npb,DivData,Dcellc,Posc,Velrhopc,Codec,CorrMatc,FSTypec,FSNormalc,PorePressc,PorePressRatec); break;
      default: Run_Exceptioon("Kernel unknown.");
    }
  }
}

//==============================================================================
/// Updates free-surface tracking and applies drained free-surface pore pressure.
//==============================================================================
void JSphCpu::ApplyPorePressureBoundaries(){
  if(!HydroMech || !PorePressc || !DivData.begincell)return;
  UpdateWallAndFreeSurfaceState();
  ApplyFreeSurfacePorePressure();
  if(HydroMechFreeSeepage && !PorePressPrec){
    //-Completed geometry only; predictor pressure/rate are not constrained by this policy.
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p])
      && IsFreeSurfaceParticle(p,Codec,FSTypec) && std::isfinite(PorePressc[p]) && PorePressc[p]>0)PorePressc[p]=0.f;
    //-The next force/save refreshes wall state before consuming its pressure samples.
  }
}

//==============================================================================
/// Applies Shepard regularization to the excess pore-pressure field.
//==============================================================================
template<TpKernel tker,bool sim2d> void JSphCpu::ShepardRegularizePorePressureT
  (unsigned np,unsigned npb,StDivDataCpu divdata,const unsigned *dcell
  ,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code
  ,const unsigned *fstype,const tfloat3 *fsnormal,const float *porepress0,float *porepress)const
{
  float *preg=NULL;
  try{ preg=new float[np]; }
  catch(const std::bad_alloc){ Run_Exceptioon("Could not allocate the requested memory."); }
  memcpy(preg,porepress,sizeof(float)*np);
  const bool dynamicvolume=(DynamicPorePressure && PorosityFeedback);
  const int pini=int(npb),pfin=int(np);
  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided)
  #endif
  for(int p1=pini;p1<pfin;p1++){
    if(!CODE_IsFluid(code[p1]))continue;
    if(IsHydroMechDrainageActive() && IsHydroMechDrainedParticle(unsigned(p1),pos,code,fstype)){
      preg[p1]=0;
      continue;
    }
    const tdouble3 posp1=pos[p1];
    double sumwab=0,pwexcesssum=0;
    if(velrhop[p1].w>0){
      const double vol1=(dynamicvolume? (double(MassFluid)/double(RhopZero))*PoroJc[p1]: double(MassFluid/velrhop[p1].w));
      const double wab0=double(fsph::GetKernel_Wab<tker>(CSP,0));
      sumwab+=wab0*vol1;
      pwexcesssum+=wab0*vol1*(double(porepress[p1])-double(porepress0[p1]));
    }
    for(int b2=0;b2<2;b2++){
      const bool boundp2=(b2==1);
      const StNgSearch ngs=nsearch::Init(dcell[p1],boundp2,divdata);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
        const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
        for(unsigned p2=pif.x;p2<pif.y;p2++){
          if(!boundp2 && !CODE_IsFluid(code[p2]))continue;
          const TpSlipMode slipmodep2=(boundp2 && BoundSlipModec? TpSlipMode(BoundSlipModec[p2]): SlipMode);
          if(boundp2 && TBoundary==BC_MDBC && slipmodep2>=SLIP_NoSlip && BoundModec && BoundModec[p2]==BMODE_MDBC2OFF)continue;
          if(velrhop[p2].w<=0)continue;
          const double drx=posp1.x-pos[p2].x;
          const double dry=(sim2d? 0: posp1.y-pos[p2].y);
          const double drz=posp1.z-pos[p2].z;
          const float rr2=float(drx*drx+dry*dry+drz*drz);
          if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
            const double vol2=(dynamicvolume? (double(boundp2? MassBound: MassFluid)/double(RhopZero))*PoroJc[p2]
              : double((boundp2? MassBound: MassFluid)/velrhop[p2].w));
            const double vwab=double(fsph::GetKernel_Wab<tker>(CSP,rr2))*vol2;
            sumwab+=vwab;
            pwexcesssum+=vwab*(double(porepress[p2])-double(porepress0[p2]));
          }
        }
      }
    }
    if(sumwab>0)preg[p1]=float(double(porepress0[p1])+pwexcesssum/sumwab);
  }
  memcpy(porepress+npb,preg+npb,sizeof(float)*(np-npb));
  delete[] preg;
}

//==============================================================================
/// Selects Shepard regularization for pore pressure.
//==============================================================================
void JSphCpu::ShepardRegularizePorePressure(){
  if(!HydroMech || !PoreShepardRegularization || !PorePressc || !PorePress0c || !PoreShepardInterval || !DivData.begincell)return;
  if(Simulate2D){
    switch(TKernel){
      case KERNEL_Wendland: ShepardRegularizePorePressureT<KERNEL_Wendland,true >(Np,Npb,DivData,Dcellc,Posc,Velrhopc,Codec,FSTypec,FSNormalc,PorePress0c,PorePressc); break;
      case KERNEL_Cubic:    ShepardRegularizePorePressureT<KERNEL_Cubic   ,true >(Np,Npb,DivData,Dcellc,Posc,Velrhopc,Codec,FSTypec,FSNormalc,PorePress0c,PorePressc); break;
      default: Run_Exceptioon("Kernel unknown.");
    }
  }
  else{
    switch(TKernel){
      case KERNEL_Wendland: ShepardRegularizePorePressureT<KERNEL_Wendland,false>(Np,Npb,DivData,Dcellc,Posc,Velrhopc,Codec,FSTypec,FSNormalc,PorePress0c,PorePressc); break;
      case KERNEL_Cubic:    ShepardRegularizePorePressureT<KERNEL_Cubic   ,false>(Np,Npb,DivData,Dcellc,Posc,Velrhopc,Codec,FSTypec,FSNormalc,PorePress0c,PorePressc); break;
      default: Run_Exceptioon("Kernel unknown.");
    }
  }
  ApplyFreeSurfacePorePressure();
  //-Regularization keeps the existing classification; do not repeat its neighbour pass.
  if(HydroMechFreeSeepage && !PorePressPrec){
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p])
      && IsFreeSurfaceParticle(p,Codec,FSTypec) && std::isfinite(PorePressc[p]) && PorePressc[p]>0)PorePressc[p]=0.f;
  }
}

//==============================================================================
/// Private CPU rate: Kw/n*(-theta + div(k*(grad(p)+rho_w*Ace))/gamma).
/// Ace excludes Gravity: grad(p)-rho_w*(g-a_s) = grad(p)+rho_w*Ace.
/// Lstar cancels affine-pressure bias, but is not a conservative pair flux.
//==============================================================================
template<TpKernel tker> void JSphCpu::ComputeDynamicPorePressureRateCpuT(){
  DynamicConductivitySpeedMax=0.;
  unsigned* ridp=NULL;
  if(PeriActive){
    ridp=GetDynamicPeriodicMapCpu();
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){
      const unsigned owner=ridp[Idpc[p]];
      Acec[p]=Acec[owner];PoroThetac[p]=PoroThetac[owner];
    }
  }
  if(DynamicPoreWall)ComputeDynamicPoreWallAccelerationCpu();
  const double kw=SoilCte.PoreWaterBulkModulus,rhow=SoilCte.PoreWaterRho;
  const double khyd=SoilCte.HydraulicConductivity,vol0=double(MassFluid)/double(RhopZero);
  const double gamma=rhow*9.80665; //-k [m/s] uses standard reference weight, independent of body acceleration.
  const bool drainfs=IsHydroMechDrainageActive();
  const bool closedfs=(HydroMechDrainage && !drainfs); //-Closed loaded surface before drainage opens; Taylor defect only, not an exact zero-flux boundary.
  double speedth[OMP_MAXTHREADS*OMP_STRIDE];
  if(DynamicPoreConductivity)for(int th=0;th<OmpThreads;th++)speedth[th*OMP_STRIDE]=0.;
  unsigned invalid=0;
  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided) reduction(+:invalid)
  #endif
  for(int p1=int(Npb);p1<int(Np);p1++)if(CODE_IsNormal(Codec[p1]) && CODE_IsFluid(Codec[p1])){
    if(DynamicPoreFreeBody){
      const tdouble3 d=Posc[p1]-DynamicPoreBodyCentre;
      const double r2=d.x*d.x+d.y*d.y+d.z*d.z;
      if(!std::isfinite(r2) || r2>=DynamicPoreBodyRadius2){invalid++;continue;}
    }
    const double ki=GetDynamicConductivityCpu(unsigned(p1));
    if(!std::isfinite(ki) || ki<0 || (khyd>0 && ki==0)){invalid++;continue;}
    if(drainfs && IsHydroMechDrainedParticle(unsigned(p1),Posc,Codec,FSTypec)){
      if(TpiEndpoint)TpiNext[Idpc[p1]]=0.f;
      PorePressRatec[p1]=0; //-Dirichlet p is constrained; theta and J still evolve normally.
      continue;
    }
    double porosity,volume,rhot;
    GetPorosityFeedbackStateCpu(unsigned(p1),porosity,volume,rhot);
    double lp=0,da=0,sumweights=0;
    tdouble3 lx=TDouble3(0),gp=TDouble3(0),gjstate=TDouble3(0);
    if(khyd>0){
      const tmatrix3d ci=CorrMatc[p1];
      for(unsigned group=0;group<(DynamicPoreWall? 2u: 1u);group++){
      const bool boundary=(group==1);
      const StNgSearch ngs=nsearch::Init(Dcellc[p1],boundary,DivData);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
        const tuint2 pif=nsearch::ParticleRange(y,z,ngs,DivData);
        for(unsigned p2=pif.x;p2<pif.y;p2++)if(CODE_IsFluid(Codec[p2]) || (boundary && CODE_IsFixed(Codec[p2]))){
          const tdouble3 d=TDouble3(Posc[p1].x-Posc[p2].x,(Simulate2D? 0: Posc[p1].y-Posc[p2].y),Posc[p1].z-Posc[p2].z);
          const double rr2=d.x*d.x+d.y*d.y+d.z*d.z;
          if(rr2>double(KernelSize2) || rr2<ALMOSTZERO)continue;
          if(boundary && BoundModec[p2]==BMODE_MDBC2OFF){invalid++;continue;}
          const double fac=fsph::GetKernel_Fac<tker>(CSP,float(rr2));
          const tdouble3 g=d*fac;
          const tdouble3 gi=TDouble3(ci.a11*g.x+ci.a12*g.y+ci.a13*g.z,ci.a21*g.x+ci.a22*g.y+ci.a23*g.z,ci.a31*g.x+ci.a32*g.y+ci.a33*g.z);
          const tmatrix3d cj=CorrMatc[p2];
          const tdouble3 gj=TDouble3(cj.a11*g.x+cj.a12*g.y+cj.a13*g.z,cj.a21*g.x+cj.a22*g.y+cj.a23*g.z,cj.a31*g.x+cj.a32*g.y+cj.a33*g.z);
          const double vol2=vol0*PoroJc[p2],dp=double(PorePressc[p1])-double(PorePressc[p2]);
          const double w=vol2*(d.x*(gi.x+gj.x)+d.y*(gi.y+gj.y)+d.z*(gi.z+gj.z))/(rr2+double(Eta2));
          if(TpiEndpoint)sumweights+=w;
          lp+=w*dp;lx=lx+d*w;gp=gp-gi*(vol2*dp);
          if(DynamicPoreConductivity)gjstate=gjstate+gi*(vol2*(PoroJc[p2]-PoroJc[p1]));
          da+=vol2*((double(Acec[p2].x)-Acec[p1].x)*gi.x
            +(double(Acec[p2].y)-Acec[p1].y)*gi.y+(double(Acec[p2].z)-Acec[p1].z)*gi.z);
        }
      }
      }
    }
    tdouble3 gpcorr=gp;
    if(khyd>0 && closedfs && IsFreeSurfaceParticle(unsigned(p1),Codec,FSTypec)){
      const tdouble3 normal=ToTDouble3(FSNormalc[p1]);
      const double norm2=normal.x*normal.x+normal.y*normal.y+normal.z*normal.z;
      if(!std::isfinite(norm2) || norm2<=0){invalid++;continue;}
      //-Neumann target for the Taylor defect only: (grad p+rho_w*Ace).n=0.
      //-Ace excludes Gravity, so it already represents a_true-body_acceleration.
      const double flux=(normal.x*(gp.x+rhow*Acec[p1].x)
        +normal.y*(gp.y+rhow*Acec[p1].y)+normal.z*(gp.z+rhow*Acec[p1].z))/norm2;
      gpcorr=gp-normal*flux;
    }
    //-Candidate raw hydraulic term omits the complete (grad p+rho_w*Ace) defect, not just grad p.
    const double lap=(HydroMechFreeSeepage && IsFreeSurfaceParticle(unsigned(p1),Codec,FSTypec)?
      lp+rhow*(double(Acec[p1].x)*lx.x+double(Acec[p1].y)*lx.y+double(Acec[p1].z)*lx.z+da):
      lp-gpcorr.x*lx.x-gpcorr.y*lx.y-gpcorr.z*lx.z+rhow*da);
    double rate=kw/porosity*(-PoroThetac[p1]+khyd/gamma*lap);
    double chain=0.;
    if(DynamicPoreConductivity && khyd>0){
      //-Smooth scalar k: div(k*(grad p+rho_w*Ace)); not a conservative interface flux.
      const double scale=ki/((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk);
      chain=scale*(gjstate.x*(gpcorr.x+rhow*Acec[p1].x)
        +gjstate.y*(gpcorr.y+rhow*Acec[p1].y)+gjstate.z*(gpcorr.z+rhow*Acec[p1].z));
      rate=kw/porosity*(-PoroThetac[p1]+ki/gamma*lap+chain/gamma);
      const double speed=kw/porosity/gamma*scale*sqrt(gjstate.x*gjstate.x+gjstate.y*gjstate.y+gjstate.z*gjstate.z);
      if(!std::isfinite(speed)){invalid++;continue;}
      const int th=omp_get_thread_num();
      if(speedth[th*OMP_STRIDE]<speed)speedth[th*OMP_STRIDE]=speed;
    }
    if(TpiEndpoint){
      //-Invert the principal Laplacian diagonal; Taylor and grad(k) terms use this round's fields.
      const double diagonal=-ki*sumweights;
      double residual=-gamma*PoroThetac[p1]+ki*lap;
      if(DynamicPoreConductivity)residual+=chain;
      if(!tpi_pressure::Endpoint(false,PorePressc[p1],diagonal,residual,TpiNext[Idpc[p1]]))invalid++;
    }
    if(!std::isfinite(rate) || fabs(rate)>FLT_MAX)invalid++;
    PorePressRatec[p1]=float(rate); //-Replace the complete old rate; never add compression twice.
  }
  if(ridp){
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsPeriodic(Codec[p]))PorePressRatec[p]=PorePressRatec[ridp[Idpc[p]]];
    ArraysCpu->Free(ridp);
  }
  if(invalid && TpiEndpoint)Run_Exceptioon("TPI pressure correction failed: invalid Darcy state, nonpositive diagonal or nonfinite corrected pressure.");
  if(invalid)Run_Exceptioon(DynamicPoreFreeBody?
    "Dynamic free body lost its inactive-DBC separation envelope or produced an invalid Darcy rate.":
    "Dynamic Darcy fixture produced a nonfinite pressure rate or conductivity-gradient speed.");
  if(DynamicPoreConductivity)for(int th=0;th<OmpThreads;th++)
    if(DynamicConductivitySpeedMax<speedth[th*OMP_STRIDE])DynamicConductivitySpeedMax=speedth[th*OMP_STRIDE];
}

//==============================================================================
/// Selects the dynamic Darcy kernel once, outside all particle/neighbour loops.
//==============================================================================
void JSphCpu::ComputeDynamicPorePressureRateCpu(){
  if(!DynamicPorePressure)return;
  switch(TKernel){
    case KERNEL_Wendland: ComputeDynamicPorePressureRateCpuT<KERNEL_Wendland>(); break;
    case KERNEL_Cubic:    ComputeDynamicPorePressureRateCpuT<KERNEL_Cubic   >(); break;
    default: Run_Exceptioon("Kernel unknown.");
  }
}

//==============================================================================
/// Updates pore pressure using the same Verlet history convention as other fields.
//==============================================================================
void JSphCpu::ComputeVerletPorePressure(double dt2){
  if(!HydroMech || !PorePressc || !PorePressRatec || !PorePressM1c)return;
  const float *poreold=(VerletStep<VerletSteps? PorePressM1c: PorePressc);
  const int np=int(Np);
  #ifdef OMP_USE
    #pragma omp parallel for schedule(static) if(np>OMP_LIMIT_COMPUTESTEP)
  #endif
  for(int p=0;p<np;p++){
    if(p<int(Npb) || !CODE_IsFluid(Codec[p]))PorePressM1c[p]=poreold[p];
    else PorePressM1c[p]=float(double(poreold[p])+dt2*double(PorePressRatec[p]));
  }
}

//==============================================================================
/// The present TPI model has a fixed material set. Never advance on a shortened
/// column or sphere; periodic copies are allowed only with a live native owner.
//==============================================================================
void JSphCpu::CheckTpiMaterialSet(){
  TpiMaterialSeen.assign(CaseNfluid,0);
  const unsigned first=CaseNp-CaseNfluid;
  unsigned count=0;
  for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p])){
    const unsigned id=Idpc[p];
    if(id<first || id>=CaseNp || TpiMaterialSeen[id-first])
      Run_Exceptioon(fun::PrintStr("TPI invalid or duplicate native soil ID %u.",id));
    TpiMaterialSeen[id-first]=1;count++;
  }
  if(count!=CaseNfluid)Run_Exceptioon(fun::PrintStr("TPI lost native soil particles: found %u of %u.",count,CaseNfluid));
  for(unsigned p=Npb;p<Np;p++)if(CODE_IsPeriodic(Codec[p]) && CODE_IsFluid(Codec[p])){
    const unsigned id=Idpc[p];
    if(id<first || id>=CaseNp || !TpiMaterialSeen[id-first])
      Run_Exceptioon(fun::PrintStr("TPI periodic copy has no native soil owner for ID %u.",id));
  }
}

//==============================================================================
/// Prepare ID-indexed pressure history once for a fresh simulation.
//==============================================================================
void JSphCpu::InitTpiPressure(){
  TpiPrevious.assign(CaseNp,std::numeric_limits<float>::quiet_NaN());
  TpiSource.resize(CaseNp);TpiGuess.resize(CaseNp);TpiNext.resize(CaseNp);
  for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p])){
    const unsigned id=Idpc[p];
    if(id>=CaseNp || !std::isnan(TpiPrevious[id]) || !std::isfinite(PorePressc[p]))
      Run_Exceptioon("Invalid TPI initial material ID or pressure.");
    TpiPrevious[id]=PorePressc[p]; //-Cold start: the previous pressure equals the initial pressure.
  }
}

//==============================================================================
/// Both the mechanical half-step pressure and the first endpoint guess use pAlpha.
//==============================================================================
void JSphCpu::PredictTpiPressure(bool predictor){
  if(predictor){
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p])){
      const unsigned id=Idpc[p];
      double predicted;
      if(id>=TpiPrevious.size() || !tpi_pressure::Predict(tpi_pressure::Predictor::Linear,
          PorePressPrec[p],TpiPrevious[id],predicted))Run_Exceptioon("Invalid TPI pressure history or prediction.");
      TpiSource[id]=PorePressPrec[p];
      TpiGuess[id]=tpi_pressure::WritePressure(predicted);
    }
  }
  const tdouble3* pos=(predictor? PosPrec: Posc);
  const bool drain=IsHydroMechDrainageActive();
  for(unsigned p=0;p<Np;p++){
    if(p<Npb || !CODE_IsFluid(Codec[p]))PorePressc[p]=PorePressPrec[p];
    else if(drain && IsHydroMechDrainedParticle(p,pos,Codec,FSTypec))PorePressc[p]=0;
    else PorePressc[p]=TpiGuess[Idpc[p]];
  }
}

//==============================================================================
/// Updates pore pressure to the Symplectic predictor half step.
//==============================================================================
void JSphCpu::ComputeSymplecticPrePorePressure(double dt){
  if(!HydroMech || !PorePressc || !PorePressPrec || !PorePressRatec)return;
  if(HydroMechTpi){ PredictTpiPressure(true);return; }
  const double dt05=dt*.5;
  const bool drainfs=(DynamicPorePressure && IsHydroMechDrainageActive());
  const int np=int(Np);
  #ifdef OMP_USE
    #pragma omp parallel for schedule(static) if(np>OMP_LIMIT_COMPUTESTEP)
  #endif
  for(int p=0;p<np;p++){
    if(p<int(Npb) || !CODE_IsFluid(Codec[p]))PorePressc[p]=PorePressPrec[p];
    else if(drainfs && IsHydroMechDrainedParticle(unsigned(p),PosPrec,Codec,FSTypec))PorePressc[p]=0;
    else PorePressc[p]=float(double(PorePressPrec[p])+dt05*double(PorePressRatec[p]));
  }
  //-Boundary conditions follow cell division, with matching geometry and neighbours.
}

//==============================================================================
/// Updates pore pressure to the Symplectic corrector full step.
//==============================================================================
void JSphCpu::ComputeSymplecticCorrPorePressure(double dt){
  if(!HydroMech || !PorePressc || !PorePressPrec || !PorePressRatec)return;
  if(HydroMechTpi){ PredictTpiPressure(false);return; }
  const bool drainfs=(DynamicPorePressure && IsHydroMechDrainageActive());
  const int np=int(Np);
  #ifdef OMP_USE
    #pragma omp parallel for schedule(static) if(np>OMP_LIMIT_COMPUTESTEP)
  #endif
  for(int p=0;p<np;p++){
    if(p<int(Npb) || !CODE_IsFluid(Codec[p]))PorePressc[p]=PorePressPrec[p];
    else if(drainfs && IsHydroMechDrainedParticle(unsigned(p),Posc,Codec,FSTypec))PorePressc[p]=0;
    else PorePressc[p]=float(double(PorePressPrec[p])+dt*double(PorePressRatec[p]));
  }
  //-Boundary conditions follow cell division, with matching geometry and neighbours.
}
