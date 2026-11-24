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

/// \file JSphCpu_preloop.cpp \brief CPU free-surface classification, correction matrices and applied surface loads.

#include "JSphCpu.h"
#include "JCellSearch_inline.h"
#include "JArraysCpu.h"
#include "FunctionsMath.h"
#include "FunSphKernel.h"
#include "FunExternalLoad.h"

#include <cfloat>
#include <cmath>

using namespace std;

//==============================================================================
/// Returns the inverse 3-D correction matrix, using the x-z block in 2-D.
//==============================================================================
static tmatrix3d FsCorrMatInverse(const tmatrix3d &mat,bool sim2d){
  tmatrix3d inv=TMatrix3d(0);
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
    const double det=fmath::Determinant3x3(mat);
    inv=(det? fmath::InverseMatrix3x3(mat,det): TMatrix3d());
  }
  return(inv);
}

//==============================================================================
/// Computes free-surface candidates, local normals and correction matrices.
//==============================================================================
template<TpKernel tker,bool sim2d> void JSphCpu::ComputeFSParticlesFreeSurface
  (unsigned np,unsigned npb,StDivDataCpu divdata,const unsigned *dcell
  ,const tdouble3 *pos,const tfloat4 *velrhop,const typecode *code
  ,tmatrix3d *corrmat,unsigned *fstype,tfloat3 *fsnormal,float *posdiv)const
{
  const int n=int(np);
  const double volb=(sim2d? Dp*Dp: Dp*Dp*Dp);
  const double porov0=(PorosityFeedback? double(MassFluid)/double(RhopZero): 0);
  const float nzero=(sim2d?
    float(3.141592*KernelSize2/(Dp*Dp)):
    float((4.f/3.f)*3.141592*KernelSize2*KernelSize2/(Dp*Dp*Dp)));

  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided)
  #endif
  for(int p1=0;p1<int(npb);p1++){
    fstype[p1]=FST_Boundary;
    fsnormal[p1]=TFloat3(0);
    posdiv[p1]=0;
    if(corrmat)corrmat[p1]=TMatrix3d(0);
  }

  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided)
  #endif
  for(int p1=int(npb);p1<n;p1++){
    fstype[p1]=FST_Inner;
    fsnormal[p1]=TFloat3(0);
    posdiv[p1]=0;
    if(corrmat)corrmat[p1]=TMatrix3d(0);
    if(CODE_IsPeriodic(code[p1]))continue;

    double fs_treshold=0;
    tdouble3 gradc=TDouble3(0);
    tmatrix3d lcorr=TMatrix3d(0);
    unsigned neigh=0;
    const tdouble3 posp1=pos[p1];

    for(int b2=0;b2<2;b2++){
      const bool boundp2=(b2==1);
      const StNgSearch ngs=nsearch::Init(dcell[p1],boundp2,divdata);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
        const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
        for(unsigned p2=pif.x;p2<pif.y;p2++){
          const double drx=posp1.x-pos[p2].x;
          const double dry=(sim2d? 0: posp1.y-pos[p2].y);
          const double drz=posp1.z-pos[p2].z;
          const float rr2=float(drx*drx+dry*dry+drz*drz);
          if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
            const double fac=double(fsph::GetKernel_Fac<tker>(CSP,rr2));
            const double frx=fac*drx;
            const double fry=(sim2d? 0: fac*dry);
            const double frz=fac*drz;
            const double vol2=(PorosityFeedback? porov0*PoroJc[p2]:
              (velrhop[p2].w>0? double((boundp2? MassBound: MassFluid)/velrhop[p2].w): (boundp2? volb: 0)));
            if(vol2>0){
              neigh++;
              const double dot3=drx*frx+dry*fry+drz*frz;
              gradc.x+=vol2*frx;
              gradc.y+=vol2*fry;
              gradc.z+=vol2*frz;
              fs_treshold-=vol2*dot3;
              lcorr.a11+=-drx*frx*vol2; lcorr.a12+=-drx*fry*vol2; lcorr.a13+=-drx*frz*vol2;
              lcorr.a21+=-dry*frx*vol2; lcorr.a22+=-dry*fry*vol2; lcorr.a23+=-dry*frz*vol2;
              lcorr.a31+=-drz*frx*vol2; lcorr.a32+=-drz*fry*vol2; lcorr.a33+=-drz*frz*vol2;
            }
          }
        }
      }
    }

    posdiv[p1]=float(fs_treshold);
    unsigned fstypep1=FST_Inner;
    if(neigh){
      if(sim2d){
        if(fs_treshold<1.7)fstypep1=FST_FreeSurface;
        if(fs_treshold<1.1 && nzero/float(neigh)<0.4f)fstypep1=FST_Isolated;
      }
      else{
        if(fs_treshold<2.75)fstypep1=FST_FreeSurface;
        if(fs_treshold<1.8 && nzero/float(neigh)<0.4f)fstypep1=FST_Isolated;
      }
    }
    else fstypep1=FST_Isolated;
    fstype[p1]=fstypep1;

    const tmatrix3d lcorr_inv=FsCorrMatInverse(lcorr,sim2d);
    if(corrmat)corrmat[p1]=lcorr_inv;
    const tdouble3 gradc1=TDouble3(
      gradc.x*lcorr_inv.a11+gradc.y*lcorr_inv.a12+gradc.z*lcorr_inv.a13,
      gradc.x*lcorr_inv.a21+gradc.y*lcorr_inv.a22+gradc.z*lcorr_inv.a23,
      gradc.x*lcorr_inv.a31+gradc.y*lcorr_inv.a32+gradc.z*lcorr_inv.a33);
    const double gradcnorm=sqrt(gradc1.x*gradc1.x+gradc1.y*gradc1.y+gradc1.z*gradc1.z);
    if(gradcnorm>1e-12){
      fsnormal[p1]=TFloat3(float(-gradc1.x/gradcnorm),float(-gradc1.y/gradcnorm),float(-gradc1.z/gradcnorm));
    }
  }
}

//==============================================================================
/// Scans the umbrella region and rejects candidates with neighbours in that region.
//==============================================================================
template<bool sim2d> void JSphCpu::ScanUmbrellaFreeSurface
  (unsigned np,unsigned npb,StDivDataCpu divdata,const unsigned *dcell
  ,const tdouble3 *pos,const typecode *code,const tfloat3 *fsnormal,unsigned *fstype)const
{
  const int n=int(np);
  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided)
  #endif
  for(int p1=int(npb);p1<n;p1++){
    if(CODE_IsPeriodic(code[p1])){
      fstype[p1]=FST_Inner;
      continue;
    }
    if(fstype[p1]!=FST_FreeSurface)continue;
    bool fs_flag=false;
    const tdouble3 posp1=pos[p1];
    const tfloat3 normalp1=fsnormal[p1];
    const float norm2=normalp1.x*normalp1.x+normalp1.y*normalp1.y+normalp1.z*normalp1.z;
    if(norm2<=1e-12f)continue;
    const tfloat3 posq=TFloat3(KernelH*normalp1.x,KernelH*normalp1.y,KernelH*normalp1.z);

    for(int b2=0;b2<2 && !fs_flag;b2++){
      const bool boundp2=(b2==1);
      const StNgSearch ngs=nsearch::Init(dcell[p1],boundp2,divdata);
      for(int z=ngs.zini;z<ngs.zfin && !fs_flag;z++)for(int y=ngs.yini;y<ngs.yfin && !fs_flag;y++){
        const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
        for(unsigned p2=pif.x;p2<pif.y;p2++){
          const float drx=float(posp1.x-pos[p2].x);
          const float dry=(sim2d? 0: float(posp1.y-pos[p2].y));
          const float drz=float(posp1.z-pos[p2].z);
          const float rr2=drx*drx+dry*dry+drz*drz;
          if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
            if(rr2>2.f*KernelH*KernelH){
              const float drxq=-drx-posq.x;
              const float dryq=(sim2d? 0: -dry-posq.y);
              const float drzq=-drz-posq.z;
              const float rrq=sqrt(drxq*drxq+dryq*dryq+drzq*drzq);
              if(rrq<KernelH)fs_flag=true;
            }
            else{
              if(sim2d){
                const float drxq=-drx-posq.x;
                const float drzq=-drz-posq.z;
                const tfloat3 normalq=TFloat3(drxq*normalp1.x,0,drzq*normalp1.z);
                const tfloat3 tangq=TFloat3(-drxq*normalp1.z,0,drzq*normalp1.x);
                const float normalqnorm=sqrt(normalq.x*normalq.x+normalq.z*normalq.z);
                const float tangqnorm=sqrt(tangq.x*tangq.x+tangq.z*tangq.z);
                if(normalqnorm+tangqnorm<KernelH)fs_flag=true;
              }
              else{
                const float rrr=1.f/sqrt(rr2);
                float cosine=(-drx*normalp1.x-dry*normalp1.y-drz*normalp1.z)*rrr;
                if(cosine<-1.f)cosine=-1.f;
                if(cosine> 1.f)cosine= 1.f;
                if(acos(cosine)<0.785398f)fs_flag=true;
              }
            }
          }
          if(fs_flag)break;
        }
      }
    }
    if(fs_flag)fstype[p1]=FST_Inner;
  }
}

//==============================================================================
/// Marks inner particles close to tracked free surface as near-free-surface.
//==============================================================================
template<bool sim2d> void JSphCpu::MarkNearFreeSurfaceParticles
  (unsigned np,unsigned npb,StDivDataCpu divdata,const unsigned *dcell
  ,const tdouble3 *pos,const typecode *code,unsigned *fstype)const
{
  const int n=int(np);
  const float limit=float(max(0.0,2.0*KernelH-0.5*Dp));
  const float limit2=limit*limit;
  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided)
  #endif
  for(int p1=int(npb);p1<n;p1++){
    if(!CODE_IsFluid(code[p1]) || CODE_IsPeriodic(code[p1]) || fstype[p1]!=FST_Inner)continue;
    bool nearfs=false;
    const tdouble3 posp1=pos[p1];
    const StNgSearch ngs=nsearch::Init(dcell[p1],false,divdata);
    for(int z=ngs.zini;z<ngs.zfin && !nearfs;z++)for(int y=ngs.yini;y<ngs.yfin && !nearfs;y++){
      const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
      for(unsigned p2=pif.x;p2<pif.y;p2++){
        if(p2==unsigned(p1) || !CODE_IsFluid(code[p2]))continue;
        if(fstype[p2]!=FST_FreeSurface && fstype[p2]!=FST_Isolated)continue;
        const float drx=float(posp1.x-pos[p2].x);
        const float dry=(sim2d? 0: float(posp1.y-pos[p2].y));
        const float drz=float(posp1.z-pos[p2].z);
        const float rr2=drx*drx+dry*dry+drz*drz;
        if(rr2<=limit2){
          nearfs=true;
          break;
        }
      }
    }
    if(nearfs)fstype[p1]=FST_NearFreeSurface;
  }
}

//==============================================================================
/// Computes kernel-gradient correction matrix for free-surface tracking.
//==============================================================================
template<TpKernel tker,bool sim2d> void JSphCpu::ComputeCorrMatrixFreeSurface
  (unsigned np,unsigned npb,StDivDataCpu divdata,const unsigned *dcell
  ,const tdouble3 *pos,const tfloat4 *velrhop,tmatrix3d *corrmat)const
{
  const int n=int(np);
  const double volb=(sim2d? Dp*Dp: Dp*Dp*Dp);
  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided)
  #endif
  for(int p1=0;p1<n;p1++){
    tmatrix3d lcorr=TMatrix3d(0);
    const tdouble3 posp1=pos[p1];
    const int nloops=(p1<int(npb)? 1: 2);
    for(int b2=0;b2<nloops;b2++){
      const bool boundp2=(p1<int(npb)? true: b2==1);
      const StNgSearch ngs=nsearch::Init(dcell[p1],boundp2,divdata);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
        const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
        for(unsigned p2=pif.x;p2<pif.y;p2++){
          const double drx=posp1.x-pos[p2].x;
          const double dry=(sim2d? 0: posp1.y-pos[p2].y);
          const double drz=posp1.z-pos[p2].z;
          const float rr2=float(drx*drx+dry*dry+drz*drz);
          if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
            const double fac=double(fsph::GetKernel_Fac<tker>(CSP,rr2));
            const double frx=fac*drx;
            const double fry=(sim2d? 0: fac*dry);
            const double frz=fac*drz;
            const double vol2=(boundp2? volb: (velrhop[p2].w>0? double(MassFluid/velrhop[p2].w): 0));
            lcorr.a11+=-drx*frx*vol2; lcorr.a12+=-drx*fry*vol2; lcorr.a13+=-drx*frz*vol2;
            lcorr.a21+=-dry*frx*vol2; lcorr.a22+=-dry*fry*vol2; lcorr.a23+=-dry*frz*vol2;
            lcorr.a31+=-drz*frx*vol2; lcorr.a32+=-drz*fry*vol2; lcorr.a33+=-drz*frz*vol2;
          }
        }
      }
    }
    corrmat[p1]=FsCorrMatInverse(lcorr,sim2d);
  }
}

//==============================================================================
/// Computes local concentration-gradient normals.
//==============================================================================
template<TpKernel tker,bool sim2d> void JSphCpu::ComputeNormalsFreeSurface
  (unsigned np,unsigned npb,StDivDataCpu divdata,const unsigned *dcell
  ,const tdouble3 *pos,const tfloat4 *velrhop,const tmatrix3d *corrmat,tfloat3 *fsnormal)const
{
  const int n=int(np);
  const double volb=(sim2d? Dp*Dp: Dp*Dp*Dp);
  float *ci=new float[n]();

  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided)
  #endif
  for(int p1=0;p1<n;p1++){
    const tdouble3 posp1=pos[p1];
    double csum=0;
    const int nloops=(p1<int(npb)? 1: 2);
    for(int b2=0;b2<nloops;b2++){
      const bool boundp2=(p1<int(npb)? true: b2==1);
      const StNgSearch ngs=nsearch::Init(dcell[p1],boundp2,divdata);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
        const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
        for(unsigned p2=pif.x;p2<pif.y;p2++){
          const double drx=posp1.x-pos[p2].x;
          const double dry=(sim2d? 0: posp1.y-pos[p2].y);
          const double drz=posp1.z-pos[p2].z;
          const float rr2=float(drx*drx+dry*dry+drz*drz);
          if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
            const double vol2=(boundp2? volb: (velrhop[p2].w>0? double(MassFluid/velrhop[p2].w): 0));
            csum+=double(fsph::GetKernel_Wab<tker>(CSP,rr2))*vol2;
          }
        }
      }
    }
    const double vol1=(p1<int(npb)? volb: (velrhop[p1].w>0? double(MassFluid/velrhop[p1].w): 0));
    ci[p1]=float(csum+double(fsph::GetKernel_Wab<tker>(CSP,0))*vol1);
  }

  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided)
  #endif
  for(int p1=0;p1<n;p1++){
    const tdouble3 posp1=pos[p1];
    const tmatrix3d lcorr=corrmat[p1];
    tdouble3 gradc=TDouble3(0);
    const int nloops=(p1<int(npb)? 1: 2);
    for(int b2=0;b2<nloops;b2++){
      const bool boundp2=(p1<int(npb)? true: b2==1);
      const StNgSearch ngs=nsearch::Init(dcell[p1],boundp2,divdata);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
        const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
        for(unsigned p2=pif.x;p2<pif.y;p2++){
          const double drx=posp1.x-pos[p2].x;
          const double dry=(sim2d? 0: posp1.y-pos[p2].y);
          const double drz=posp1.z-pos[p2].z;
          const float rr2=float(drx*drx+dry*dry+drz*drz);
          if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
            const double fac=double(fsph::GetKernel_Fac<tker>(CSP,rr2));
            const double frx=fac*drx;
            const double fry=(sim2d? 0: fac*dry);
            const double frz=fac*drz;
            const double vol2=(boundp2? volb: (velrhop[p2].w>0? double(MassFluid/velrhop[p2].w): 0));
            const double dc=double(ci[p2]-ci[p1]);
            gradc.x+=(lcorr.a11*frx+lcorr.a12*fry+lcorr.a13*frz)*vol2*dc;
            gradc.y+=(lcorr.a21*frx+lcorr.a22*fry+lcorr.a23*frz)*vol2*dc;
            gradc.z+=(lcorr.a31*frx+lcorr.a32*fry+lcorr.a33*frz)*vol2*dc;
          }
        }
      }
    }
    const double norm=sqrt(gradc.x*gradc.x+gradc.y*gradc.y+gradc.z*gradc.z);
    fsnormal[p1]=(norm>1e-12? TFloat3(float(-gradc.x/norm),float(-gradc.y/norm),float(-gradc.z/norm)): TFloat3(0));
  }
  delete[] ci;
}

//==============================================================================
/// Classifies free-surface, vicinity, inner and wall-vicinity particles.
//==============================================================================
template<TpKernel tker,bool sim2d> void JSphCpu::ClassifyFreeSurface
  (unsigned np,unsigned npb,StDivDataCpu divdata,const unsigned *dcell
  ,const tdouble3 *pos,const tfloat4 *velrhop,const tfloat3 *fsnormal,unsigned *fstype,float *posdiv)const
{
  const int n=int(np);
  const double volb=(sim2d? Dp*Dp: Dp*Dp*Dp);
  unsigned *ni=new unsigned[n]();
  const float lowerlimit=(sim2d? 0.4f: 0.6f);
  const float upperlimit=(sim2d? 1.75f: 2.5f);
  const float cos45=0.7071067811865476f;

  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided)
  #endif
  for(int p1=0;p1<int(npb);p1++){
    fstype[p1]=FST_Boundary;
    posdiv[p1]=0;
  }

  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided)
  #endif
  for(int p1=int(npb);p1<n;p1++){
    const tdouble3 posp1=pos[p1];
    double div=0;
    unsigned nneigh=0;
    for(int b2=0;b2<2;b2++){
      const bool boundp2=(b2==1);
      const StNgSearch ngs=nsearch::Init(dcell[p1],boundp2,divdata);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
        const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
        for(unsigned p2=pif.x;p2<pif.y;p2++){
          const double drx=posp1.x-pos[p2].x;
          const double dry=(sim2d? 0: posp1.y-pos[p2].y);
          const double drz=posp1.z-pos[p2].z;
          const float rr2=float(drx*drx+dry*dry+drz*drz);
          if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
            const double fac=double(fsph::GetKernel_Fac<tker>(CSP,rr2));
            const double frx=fac*drx;
            const double fry=(sim2d? 0: fac*dry);
            const double frz=fac*drz;
            const double vol2=(boundp2? volb: (velrhop[p2].w>0? double(MassFluid/velrhop[p2].w): 0));
            div-=vol2*(drx*frx+dry*fry+drz*frz);
            if(!boundp2)nneigh++;
          }
        }
      }
    }
    posdiv[p1]=float(div);
    ni[p1]=nneigh;
  }

  unsigned n0=0;
  for(unsigned p=npb;p<np;p++)if(n0<ni[p])n0=ni[p];

  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided)
  #endif
  for(int p1=int(npb);p1<n;p1++){
    if     (posdiv[p1]<lowerlimit && float(ni[p1])<0.4f*float(n0))fstype[p1]=FST_Isolated;
    else if(posdiv[p1]>=lowerlimit && posdiv[p1]<upperlimit)      fstype[p1]=FST_FreeSurface;
    else                                                          fstype[p1]=FST_Inner;
  }

  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided)
  #endif
  for(int p1=int(npb);p1<n;p1++){
    if(fstype[p1]==FST_FreeSurface){
      const tdouble3 posp1=pos[p1];
      for(int b2=0;b2<2 && fstype[p1]==FST_FreeSurface;b2++){
        const bool boundp2=(b2==1);
        const StNgSearch ngs=nsearch::Init(dcell[p1],boundp2,divdata);
        for(int z=ngs.zini;z<ngs.zfin && fstype[p1]==FST_FreeSurface;z++)for(int y=ngs.yini;y<ngs.yfin && fstype[p1]==FST_FreeSurface;y++){
          const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
          for(unsigned p2=pif.x;p2<pif.y;p2++){
            const float drx=float(posp1.x-pos[p2].x);
            const float dry=(sim2d? 0: float(posp1.y-pos[p2].y));
            const float drz=float(posp1.z-pos[p2].z);
            const float rr2=drx*drx+dry*dry+drz*drz;
            if(rr2<=KernelSize2 && rr2>=ALMOSTZERO){
              const float invr=1.f/sqrt(rr2);
              const float vecproduct=(-drx*fsnormal[p1].x-dry*fsnormal[p1].y-drz*fsnormal[p1].z)*invr;
              const bool insidecone=(rr2<2.f*KernelH*KernelH && vecproduct>cos45);
              const float rtx=KernelH*fsnormal[p1].x;
              const float rty=(sim2d? 0: KernelH*fsnormal[p1].y);
              const float rtz=KernelH*fsnormal[p1].z;
              const float dist2=(drx+rtx)*(drx+rtx)+(dry+rty)*(dry+rty)+(drz+rtz)*(drz+rtz);
              const bool insidecap=(rr2>=2.f*KernelH*KernelH && dist2<KernelH*KernelH);
              if(insidecone || insidecap){
                fstype[p1]=FST_Inner;
                break;
              }
            }
          }
        }
      }
    }
  }

  #ifdef OMP_USE
    #pragma omp parallel for schedule(guided)
  #endif
  for(int p1=int(npb);p1<n;p1++){
    if(fstype[p1]==FST_FreeSurface){
      const tdouble3 posp1=pos[p1];
      float rmin=FLT_MAX;
      const StNgSearch ngs=nsearch::Init(dcell[p1],true,divdata);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
        const tuint2 pif=nsearch::ParticleRange(y,z,ngs,divdata);
        for(unsigned p2=pif.x;p2<pif.y;p2++){
          const float drx=float(posp1.x-pos[p2].x);
          const float dry=(sim2d? 0: float(posp1.y-pos[p2].y));
          const float drz=float(posp1.z-pos[p2].z);
          const float rr=sqrt(drx*drx+dry*dry+drz*drz);
          rmin=min(rmin,rr);
        }
      }
      if(rmin<1.8f*float(Dp))fstype[p1]=FST_Boundary;
    }
  }

  delete[] ni;
}

//==============================================================================
/// Reconstructs stage wall fields, classifies the surface and extends the new correction matrix to the walls.
//==============================================================================
void JSphCpu::UpdateWallAndFreeSurfaceState(){
  if(!Np || !DivData.begincell || !CorrMatc || !FSTypec || !FSNormalc || !PosDivc)return;
  if(DynamicPoreWall)ComputeDynamicPoreWallStateCpu();
  const bool marknearfs=false; //-Near-free-surface search is retained but disabled for the global pair-wise confinement path.

  if(Simulate2D){
    switch(TKernel){
      case KERNEL_Wendland:
        ComputeFSParticlesFreeSurface<KERNEL_Wendland,true>(Np,Npb,DivData,Dcellc,Posc,Velrhopc,Codec,CorrMatc,FSTypec,FSNormalc,PosDivc);
        ScanUmbrellaFreeSurface<true>(Np,Npb,DivData,Dcellc,Posc,Codec,FSNormalc,FSTypec);
        if(marknearfs)MarkNearFreeSurfaceParticles<true>(Np,Npb,DivData,Dcellc,Posc,Codec,FSTypec);
      break;
      case KERNEL_Cubic:
        ComputeFSParticlesFreeSurface<KERNEL_Cubic,true>(Np,Npb,DivData,Dcellc,Posc,Velrhopc,Codec,CorrMatc,FSTypec,FSNormalc,PosDivc);
        ScanUmbrellaFreeSurface<true>(Np,Npb,DivData,Dcellc,Posc,Codec,FSNormalc,FSTypec);
        if(marknearfs)MarkNearFreeSurfaceParticles<true>(Np,Npb,DivData,Dcellc,Posc,Codec,FSTypec);
      break;
      default: Run_Exceptioon("Kernel unknown.");
    }
  }
  else{
    switch(TKernel){
      case KERNEL_Wendland:
        ComputeFSParticlesFreeSurface<KERNEL_Wendland,false>(Np,Npb,DivData,Dcellc,Posc,Velrhopc,Codec,CorrMatc,FSTypec,FSNormalc,PosDivc);
        ScanUmbrellaFreeSurface<false>(Np,Npb,DivData,Dcellc,Posc,Codec,FSNormalc,FSTypec);
        if(marknearfs)MarkNearFreeSurfaceParticles<false>(Np,Npb,DivData,Dcellc,Posc,Codec,FSTypec);
      break;
      case KERNEL_Cubic:
        ComputeFSParticlesFreeSurface<KERNEL_Cubic,false>(Np,Npb,DivData,Dcellc,Posc,Velrhopc,Codec,CorrMatc,FSTypec,FSNormalc,PosDivc);
        ScanUmbrellaFreeSurface<false>(Np,Npb,DivData,Dcellc,Posc,Codec,FSNormalc,FSTypec);
        if(marknearfs)MarkNearFreeSurfaceParticles<false>(Np,Npb,DivData,Dcellc,Posc,Codec,FSTypec);
      break;
      default: Run_Exceptioon("Kernel unknown.");
    }
  }
  if(DynamicPorePressure && PeriActive){
    unsigned* ridp=GetDynamicPeriodicMapCpu();
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsPeriodic(Codec[p]))CorrMatc[p]=CorrMatc[ridp[Idpc[p]]];
    ArraysCpu->Free(ridp);
  }
  if(DynamicPoreWall)ComputeDynamicPoreWallMatrixCpu();
}

//==============================================================================
/// Applies q0 ramp surcharge as an acceleration on selected free-surface soil.
//==============================================================================
void JSphCpu::ApplyHydroMechTopLoadAcceleration(){
  if(!HydroMech || HydroMechTopLoadMode==HMLOAD_None)return;
  if(HydroMechTopLoadMode==HMLOAD_FlexibleConfinement)return;
  if(!Acec || !FSTypec || !FSNormalc)return;
  const bool alltop=(HydroMechTopLoadMode==HMLOAD_TopVertical || HydroMechTopLoadMode==HMLOAD_TopKernelBand);
  const bool striptop=(HydroMechTopLoadMode==HMLOAD_TopStripVertical || HydroMechTopLoadMode==HMLOAD_LianFlexibleStrip);
  if(!alltop && !striptop)return;
  const double q0=double(HydroMechTopLoadQ0);
  if(q0<=0)return;
  const double tramp=HydroMechTopLoadRampTime;
  const double q=externalload::RampedPressure(q0,tramp,TimeStep);
  if(q<=0)return;
  const double por=double(SoilCte.Porosity);
  const double rhol=double(SoilCte.PoreWaterRho);
  const double rhos=((1.0-por)>0? (double(RhopZero)-por*rhol)/(1.0-por): double(RhopZero));
  const double rhomix=(rhos>0? (1.0-por)*rhos+por*rhol: double(RhopZero));
  const double denom=rhomix*double(Dp);
  if(denom<=0)return;
  const float accmag=float(q/denom);
  const int pini=int(Npb),pfin=int(Np);
  #ifdef OMP_USE
    #pragma omp parallel for schedule(static) if((pfin-pini)>OMP_LIMIT_COMPUTELIGHT)
  #endif
  for(int p=pini;p<pfin;p++){
    if(!CODE_IsNormal(Codec[p]))continue;
    const bool upwardfs=IsUpwardFreeSurface(unsigned(p),Codec,FSTypec,FSNormalc);
    const bool stripgeom=(striptop && externalload::IsStripSurface(HydroMechTopLoadMode,Posc[p].x,Posc[p].z,double(Dp)));
    if(upwardfs || stripgeom){
      if(striptop && !stripgeom && !externalload::InStripFootprint(HydroMechTopLoadMode,Posc[p].x))continue;
      const tfloat3 load=TFloat3(0,0,-accmag);
      Acec[p].x+=load.x; Acec[p].y+=load.y; Acec[p].z+=load.z;
      if(HydroMechLoadAcec)HydroMechLoadAcec[p]=load;
    }
  }
}

//==============================================================================
/// Redistributes the existing top load over its vertical kernel-support band.
//==============================================================================
void JSphCpu::NormalizeHydroMechTopBandLoad(){
  if(!HydroMech || HydroMechTopLoadMode!=HMLOAD_TopKernelBand)return;
  double zmax=-DBL_MAX,target=0;
  for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p])){
    zmax=max(zmax,Posc[p].z);
    target+=double(MassFluid)*HydroMechLoadAcec[p].z;
  }
  if(target==0)return;
  //-Keep the reference top resultant q(t)*A0; only the band inertia changes with J.
  double raw=0;
  for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p]) && Posc[p].z>zmax-KernelSize){
    if(PorosityFeedback){
      double porosity,volume,rhot;
      GetPorosityFeedbackStateCpu(p,porosity,volume,rhot);
      raw+=rhot*volume*HydroMechTopLoadRawc[p];
    }
    else raw+=double(MassFluid)*HydroMechTopLoadRawc[p];
  }
  if(!(raw<0))Run_Exceptioon("TopKernelBand requires a negative raw vertical load on the top support band.");
  const double scale=target/raw;
  //-Keep the tested float replacement order and serial force normalization.
  for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p])){
    const float load=(Posc[p].z>zmax-KernelSize? float(HydroMechTopLoadRawc[p]*scale): 0.f);
    Acec[p].z+=load-HydroMechLoadAcec[p].z;
    HydroMechLoadAcec[p]=TFloat3(0,0,load);
  }
}
