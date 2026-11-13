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

/// \file JSphGpu_mdbc_ker.cuh \brief mDBC kernels included by JSphGpu_ker.cu.
// Included once inside namespace cusph; shares its original CTE and device helpers.
// This file is not a separate CUDA translation unit.

//==============================================================================
/// Static 2-D mirror samples: the fitted d=target-source coefficients are -grad.
/// The anchored value avoids smoothing a mirror point coincident with a fluid node.
//==============================================================================
//-Reuse the legacy tangent projection; its definition follows the force kernels.
__device__ float3 KerMdbc2TangenVel(const float3 boundnormal,const float3 velfinal);

template<unsigned stage> __device__ double KerDynamicPoreWallRead(unsigned p,unsigned c
  ,const float3 normalg,const double2 *posxy,const double *posz
  ,const float4 *velrhop,const tsymatrix3d *sigma,const float *porepress,const double *j
  ,const tmatrix3d *corrmat,const float3 *ace)
{
  if(stage==0){
    if(c==0)return j[p];
    if(c==1){
      if(normalg.x!=0.f || normalg.y!=0.f || normalg.z!=0.f)
        return double(porepress[p])-double(CTE.porewaterrho)*(double(normalg.x)*posxy[p].x
          +double(normalg.y)*posxy[p].y+double(normalg.z)*posz[p]);
      return double(porepress[p]); //-Keep the old zero-normal-g path, including signed zero.
    }
    if(c<5)return(c==2? double(velrhop[p].x): (c==3? double(velrhop[p].y): double(velrhop[p].z)));
    const tsymatrix3d s=sigma[p];const double v[6]={s.xx,s.yy,s.zz,s.xy,s.xz,s.yz};return v[c-5];
  }
  if(stage==1){
    const tmatrix3d m=corrmat[p];const double v[9]={m.a11,m.a12,m.a13,m.a21,m.a22,m.a23,m.a31,m.a32,m.a33};return v[c];
  }
  const double a=(c==0? double(ace[p].x): (c==1? double(ace[p].y): double(ace[p].z)));
  if(normalg.x!=0.f || normalg.y!=0.f || normalg.z!=0.f)
    return a+(c==0? double(normalg.x): (c==1? double(normalg.y): double(normalg.z)));
  return a; //-Do not add signed zero on the old zero-normal-g path.
}

template<TpKernel tker,unsigned stage> __global__ void KerDynamicPoreWall(unsigned np,unsigned npbok,float threshold
  ,int scelldiv,int4 nc,int3 cellzero,const int2 *fluidcells,const double2 *posxy,const double *posz
  ,const typecode *code,const float3 *boundnormal,byte *boundmode,float3 *tangenvel,float3 *derivativevel
  ,float4 *velrhop,tsymatrix3d *sigma,float *porepress,double *j,double *theta,tmatrix3d *corrmat,float3 *ace
  ,double solid0,unsigned *invalid,const byte *boundslipmode,const float4 *poscell)
{
  const unsigned p1=blockIdx.x*blockDim.x+threadIdx.x;
  if(p1>=npbok || p1>=np)return;
  const float3 bn=boundnormal[p1];
  const bool noslip=(stage==0 && (boundslipmode? unsigned(boundslipmode[p1]): CTE.slipmode)==unsigned(SLIP_NoSlip));
  const double r2=double(bn.x)*bn.x+double(bn.y)*bn.y+double(bn.z)*bn.z;
  if(!CODE_IsFixed(code[p1]) || !isfinite(r2) || !(r2>0)){atomicMin(invalid,p1);return;}
  const bool currentb=(poscell && CTE.simulate2d && !CTE.periactive);
  if(currentb){
    if(stage==0){
      //-Participation at current physical B, not at a fitted mirror or a dry/wet height.
      bool activeb=false;
      const float4 pc1=poscell[p1];
      int bi1,bf1,bi2,bf2,bi3,bf3;
      cunsearch::InitCte(posxy[p1].x,posxy[p1].y,posz[p1],scelldiv,nc,cellzero,bi1,bf1,bi2,bf2,bi3,bf3);
      for(int c3=bi3;c3<bf3 && !activeb;c3+=nc.w)for(int c2=bi2;c2<bf2 && !activeb;c2+=nc.x){
        unsigned pini,pfin=0;cunsearch::ParticleRange(c2,c3,bi1,bf1,fluidcells,pini,pfin);
        if(pfin)for(unsigned p2=pini;p2<pfin && !activeb;p2++)if(CODE_IsFluid(code[p2])){
          const double dx=posxy[p1].x-posxy[p2].x,dz=posz[p1]-posz[p2],drr2=dx*dx+dz*dz;
          const float4 pc2=poscell[p2];
          const float drx=pc1.x-pc2.x + CTE.poscellsize*(PSCEL_GetfX(pc1.w)-PSCEL_GetfX(pc2.w));
          const float dry=pc1.y-pc2.y + CTE.poscellsize*(PSCEL_GetfY(pc1.w)-PSCEL_GetfY(pc2.w));
          const float drz=pc1.z-pc2.z + CTE.poscellsize*(PSCEL_GetfZ(pc1.w)-PSCEL_GetfZ(pc2.w));
          const float fsrr2=drx*drx+drz*drz,forcerr2=drx*drx+dry*dry+drz*drz;
          activeb=(drr2<=double(CTE.kernelsize2) && drr2>=ALMOSTZERO)
            || (fsrr2<=CTE.kernelsize2 && fsrr2>=ALMOSTZERO)
            || (forcerr2<=CTE.kernelsize2 && forcerr2>=ALMOSTZERO);
        }
      }
      boundmode[p1]=(activeb? BMODE_MDBC2: BMODE_MDBC2OFF);
    }
    if(boundmode[p1]==BMODE_MDBC2OFF)return;
  }
  const double qx=(double(bn.x)*bn.x>.5*r2? -1.: 1.),qy=(double(bn.y)*bn.y>.5*r2? -1.: 1.),qz=(double(bn.z)*bn.z>.5*r2? -1.: 1.);
  //-Only the admitted axis-plane normal head is extended; tangential/periodic semantics stay unchanged.
  const float3 normalg=make_float3(qx<0? CTE.gravityx: 0.f,qy<0? CTE.gravityy: 0.f,qz<0? CTE.gravityz: 0.f);
  double3 gp=make_double3(posxy[p1].x+bn.x,posxy[p1].y+bn.y,posz[p1]+bn.z);
  if(CTE.periactive)gp=KerUpdatePeriodicPos(gp);
  enum {ncomp=(stage==0? 11: (stage==1? 9: 3))};
  double fitshiftx=0,fitshiftz=0;bool retried=false,centroidretried=false;
  for(;;){ //-Keep primary/nearest fits; one final centroid retry after geometry failure.
  double sum[ncomp]={0},gx[ncomp]={0},gz[ncomp]={0},nearest[ncomp]={0};
  double sumwab=0,submerged=0,nearest2=DBL_MAX,nearx=0,nearz=0;
  tmatrix3d moment;cumath::Tmatrix3dReset(moment);
  int ini1,fin1,ini2,fin2,ini3,fin3;
  cunsearch::InitCte(gp.x,gp.y,gp.z,scelldiv,nc,cellzero,ini1,fin1,ini2,fin2,ini3,fin3);
  for(int c3=ini3;c3<fin3;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
    unsigned pini,pfin=0;cunsearch::ParticleRange(c2,c3,ini1,fin1,fluidcells,pini,pfin);
    if(pfin)for(unsigned p2=pini;p2<pfin;p2++)if(CODE_IsFluid(code[p2])){
      const double dx=gp.x-posxy[p2].x,dz=gp.z-posz[p2];
      const float rr2=float(dx*dx+dz*dz);
      if(rr2<=CTE.kernelsize2){
        if(!isfinite(j[p2]) || j[p2]<=solid0){atomicMin(invalid,p1);return;}
        float fac;
        const double wab=(rr2==0? (fac=0.f,double(cufsph::GetKernel_Wab<tker>(rr2))): double(cufsph::GetKernel_WabFac<tker>(rr2,fac)));
        const double fx=double(fac)*dx,fz=double(fac)*dz;
        const double vol=double(CTE.massf)/double(CTE.rhopzero)*j[p2],w=wab*vol,vx=fx*vol,vz=fz*vol;
        const double distance2=dx*dx+dz*dz;const bool nearer=(distance2<nearest2);
        for(unsigned c=0;c<ncomp;c++){
          const double field=KerDynamicPoreWallRead<stage>(p2,c,normalg,posxy,posz,velrhop,sigma,porepress,j,corrmat,ace);
          sum[c]+=w*field;gx[c]+=vx*field;gz[c]+=vz*field;if(nearer)nearest[c]=field;
        }
        if(nearer){nearest2=distance2;nearx=dx;nearz=dz;}
        sumwab+=w;submerged-=vol*(dx*fx+dz*fz);
        moment.a11+=w; moment.a12+=dx*w; moment.a13+=dz*w;
        moment.a21+=vx;moment.a22+=dx*vx;moment.a23+=dz*vx;
        moment.a31+=vz;moment.a32+=dx*vz;moment.a33+=dz*vz;
      }
    }
  }
  const bool active=(submerged>0 || sumwab>=double(threshold) || (threshold>=2 && sumwab+2>=double(threshold)));
  const double det=cumath::Determinant3x3(moment);
  if(!active || !(sumwab>0) || !isfinite(det) || fabs(det)<1e-3){
    bool nearestfinite=isfinite(nearest2) && nearest2<DBL_MAX && isfinite(nearx) && isfinite(nearz);
    for(unsigned c=0;c<ncomp && nearestfinite;c++)nearestfinite=isfinite(nearest[c]);
    if(CTE.simulate2d && !CTE.periactive && !retried && nearestfinite && (nearx!=0 || nearz!=0)){
      //-Use the visited real source, retaining the original evaluation mirror.
      gp.x-=nearx;gp.z-=nearz;fitshiftx-=nearx;fitshiftz-=nearz;
      retried=true;continue;
    }
    if(tker==KERNEL_Wendland && CTE.simulate2d && !CTE.periactive && retried && !centroidretried && nearestfinite
      && isfinite(moment.a11) && moment.a11>0){
      //-Positive W*V first moments locate the donor centroid; retain the original mirror target.
      const double dx=moment.a12/moment.a11,dz=moment.a13/moment.a11;
      const double cx=gp.x-dx,cz=gp.z-dz;
      if(isfinite(dx) && isfinite(dz) && isfinite(cx) && isfinite(cz) && (cx!=gp.x || cz!=gp.z)){
        gp.x=cx;gp.z=cz;fitshiftx-=dx;fitshiftz-=dz;
        centroidretried=true;continue;
      }
    }
    atomicMin(invalid,p1);return;
  }
  const tmatrix3d inv=cumath::InverseMatrix3x3(moment,det);
  double v[ncomp];
  for(unsigned c=0;c<ncomp;c++){
    const double gradx=inv.a21*sum[c]+inv.a22*gx[c]+inv.a23*gz[c];
    const double gradz=inv.a31*sum[c]+inv.a32*gx[c]+inv.a33*gz[c];
    v[c]=nearest[c]-gradx*nearx-gradz*nearz;
    if(retried)v[c]+=gradx*fitshiftx+gradz*fitshiftz;
    gx[c]=gradx;gz[c]=gradz; //-Keep the existing d=target-source coefficients for the state writer.
    if(!isfinite(v[c])){atomicMin(invalid,p1);return;}
  }
  if(stage==0){
    const bool hydrostatichead=(normalg.x!=0.f || normalg.y!=0.f || normalg.z!=0.f);
    //-Restore the normal head at the boundary sample, not at its fitted mirror target.
    const double pressure=(hydrostatichead? v[1]+double(CTE.porewaterrho)*(double(normalg.x)*posxy[p1].x
      +double(normalg.y)*posxy[p1].y+double(normalg.z)*posz[p1]): v[1]);
    float3 dv,tv;tsymatrix3d s;
    if(noslip){
      dv=make_float3(float(-v[2]),float(-v[3]),float(-v[4]));
      tv=KerMdbc2TangenVel(bn,dv);
      //-Legacy stress is extrapolated from the mirror target to B: physical grad is -gx/-gz.
      s.xx=v[5]+gx[5]*bn.x+gz[5]*bn.z;s.yy=v[6]+gx[6]*bn.x+gz[6]*bn.z;s.zz=v[7]+gx[7]*bn.x+gz[7]*bn.z;
      s.xy=v[8]+gx[8]*bn.x+gz[8]*bn.z;s.xz=v[9]+gx[9]*bn.x+gz[9]*bn.z;s.yz=v[10]+gx[10]*bn.x+gz[10]*bn.z;
    }
    else{
      dv=make_float3(float(qx*v[2]),float(qy*v[3]),float(qz*v[4]));
      tv=make_float3(float(.5*(1.+qx)*v[2]),float(.5*(1.+qy)*v[3]),float(.5*(1.+qz)*v[4]));
      s.xx=v[5];s.yy=v[6];s.zz=v[7];s.xy=qx*qy*v[8];s.xz=qx*qz*v[9];s.yz=qy*qz*v[10];
    }
    if(v[0]<=solid0 || !isfinite(pressure) || fabs(pressure)>FLT_MAX || !isfinite(dv.x) || !isfinite(dv.y) || !isfinite(dv.z)
      || !isfinite(tv.x) || !isfinite(tv.y) || !isfinite(tv.z)){atomicMin(invalid,p1);return;}
    j[p1]=v[0];theta[p1]=0.;porepress[p1]=float(pressure);sigma[p1]=s;
    if(derivativevel)derivativevel[p1]=dv;
    if(tangenvel)tangenvel[p1]=tv;
    velrhop[p1]=make_float4(0,0,0,CTE.rhopzero);boundmode[p1]=BMODE_MDBC2;
  }
  else if(stage==1){
    tmatrix3d m;m.a11=v[0];m.a12=qx*qy*v[1];m.a13=qx*qz*v[2];m.a21=qy*qx*v[3];m.a22=v[4];m.a23=qy*qz*v[5];m.a31=qz*qx*v[6];m.a32=qz*qy*v[7];m.a33=v[8];
    const double determinant=m.a11*m.a33-m.a13*m.a31;
    if(!isfinite(determinant) || determinant<=0){atomicMin(invalid,p1);return;}
    corrmat[p1]=m;
  }
  else{
    const bool hydrostatichead=(normalg.x!=0.f || normalg.y!=0.f || normalg.z!=0.f);
    const float3 a=(hydrostatichead? make_float3(float(qx*v[0]-double(normalg.x)),float(qy*v[1]-double(normalg.y)),float(qz*v[2]-double(normalg.z)))
      : make_float3(float(qx*v[0]),float(qy*v[1]),float(qz*v[2])));
    if(!isfinite(a.x) || !isfinite(a.y) || !isfinite(a.z)){atomicMin(invalid,p1);return;}
    ace[p1]=a; //-Q*(Ace+g_n)-g_n equals Q*(Ace+g)-g; zero g_n keeps the old literal path.
  }
  break;
  }
}

template<TpKernel tker> void DynamicPoreWallT(unsigned stage,unsigned np,unsigned npbok,float threshold,const StDivDataGpu &dvd
  ,const double2 *posxy,const double *posz,const typecode *code,const float3 *boundnormal
  ,byte *boundmode,float3 *tangenvel,float3 *derivativevel,float4 *velrhop,tsymatrix3d *sigma
  ,float *porepress,double *j,double *theta,tmatrix3d *corrmat,float3 *ace,double solid0,unsigned *invalid,const byte *boundslipmode,const float4 *poscell)
{
  if(npbok){
    dim3 grid=GetSimpleGridSize(npbok,SPHBSIZE);
    if(stage==0)KerDynamicPoreWall<tker,0><<<grid,SPHBSIZE>>>(np,npbok,threshold,dvd.scelldiv,dvd.nc,dvd.cellzero,dvd.beginendcell+dvd.cellfluid,posxy,posz,code,boundnormal,boundmode,tangenvel,derivativevel,velrhop,sigma,porepress,j,theta,corrmat,ace,solid0,invalid,boundslipmode,poscell);
    else if(stage==1)KerDynamicPoreWall<tker,1><<<grid,SPHBSIZE>>>(np,npbok,threshold,dvd.scelldiv,dvd.nc,dvd.cellzero,dvd.beginendcell+dvd.cellfluid,posxy,posz,code,boundnormal,boundmode,tangenvel,derivativevel,velrhop,sigma,porepress,j,theta,corrmat,ace,solid0,invalid,boundslipmode,poscell);
    else if(stage==2)KerDynamicPoreWall<tker,2><<<grid,SPHBSIZE>>>(np,npbok,threshold,dvd.scelldiv,dvd.nc,dvd.cellzero,dvd.beginendcell+dvd.cellfluid,posxy,posz,code,boundnormal,boundmode,tangenvel,derivativevel,velrhop,sigma,porepress,j,theta,corrmat,ace,solid0,invalid,boundslipmode,poscell);
  }
}

void DynamicPoreWall(unsigned stage,unsigned np,unsigned npbok,float threshold,const StDivDataGpu &dvd
  ,const double2 *posxy,const double *posz,const typecode *code,const float3 *boundnormal
  ,byte *boundmode,float3 *tangenvel,float3 *derivativevel,float4 *velrhop,tsymatrix3d *sigma
  ,float *porepress,double *j,double *theta,tmatrix3d *corrmat,float3 *ace,double solid0,unsigned *invalid,TpKernel tkernel,const byte *boundslipmode,const float4 *poscell)
{
  if(tkernel==KERNEL_Wendland)DynamicPoreWallT<KERNEL_Wendland>(stage,np,npbok,threshold,dvd,posxy,posz,code,boundnormal,boundmode,tangenvel,derivativevel,velrhop,sigma,porepress,j,theta,corrmat,ace,solid0,invalid,boundslipmode,poscell);
  else if(tkernel==KERNEL_Cubic)DynamicPoreWallT<KERNEL_Cubic>(stage,np,npbok,threshold,dvd,posxy,posz,code,boundnormal,boundmode,tangenvel,derivativevel,velrhop,sigma,porepress,j,theta,corrmat,ace,solid0,invalid,boundslipmode,poscell);
  else throw "Kernel unknown.";
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
      double gradpwexcessx=0,gradpwexcessy=0,gradpwexcessz=0;
      tmatrix3d a_corr2; if(sim2d) cumath::Tmatrix3dReset(a_corr2);
      tmatrix4d a_corr3; if(!sim2d)cumath::Tmatrix4dReset(a_corr3);
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
            const double vfrx=double(fac)*double(drx)*double(vol2);
            const double vfry=double(fac)*double(dry)*double(vol2);
            const double vfrz=double(fac)*double(drz)*double(vol2);
            const double pwexcess=double(porepress[p2])-double(porepress0[p2]);
            sumwab+=vwab;
            pwexcesssum+=vwab*pwexcess;
            gradpwexcessx+=vfrx*pwexcess;
            gradpwexcessy+=vfry*pwexcess;
            gradpwexcessz+=vfrz*pwexcess;
            submerged-=double(vol2)*(double(drx)*fac*drx+double(dry)*fac*dry+double(drz)*fac*drz);
            if(sim2d){
              a_corr2.a11+=vwab;  a_corr2.a12+=double(drx)*vwab;  a_corr2.a13+=double(drz)*vwab;
              a_corr2.a21+=vfrx;  a_corr2.a22+=double(drx)*vfrx;  a_corr2.a23+=double(drz)*vfrx;
              a_corr2.a31+=vfrz;  a_corr2.a32+=double(drx)*vfrz;  a_corr2.a33+=double(drz)*vfrz;
            }
            else{
              a_corr3.a11+=vwab;  a_corr3.a12+=double(drx)*vwab;  a_corr3.a13+=double(dry)*vwab;  a_corr3.a14+=double(drz)*vwab;
              a_corr3.a21+=vfrx;  a_corr3.a22+=double(drx)*vfrx;  a_corr3.a23+=double(dry)*vfrx;  a_corr3.a24+=double(drz)*vfrx;
              a_corr3.a31+=vfry;  a_corr3.a32+=double(drx)*vfry;  a_corr3.a33+=double(dry)*vfry;  a_corr3.a34+=double(drz)*vfry;
              a_corr3.a41+=vfrz;  a_corr3.a42+=double(drx)*vfrz;  a_corr3.a43+=double(dry)*vfrz;  a_corr3.a44+=double(drz)*vfrz;
            }
          }
        }
      }
      const bool active=(submerged>0. || sumwab>=double(mdbcthreshold) || (mdbcthreshold>=2.f && sumwab+2.>=double(mdbcthreshold)));
      if(active && sumwab>0.){
        const double determlimit=1e-3;
        double pwexcessfinal=pwexcesssum/sumwab; //-0th-order fallback.
        if(sim2d){
          const double determ=cumath::Determinant3x3(a_corr2);
          if(fabs(determ)>=determlimit){
            const tmatrix3d inv=cumath::InverseMatrix3x3(a_corr2,determ);
            const double qg = inv.a11*pwexcesssum + inv.a12*gradpwexcessx + inv.a13*gradpwexcessz;
            pwexcessfinal=qg;
          }
        }
        else{
          const double determ=cumath::Determinant4x4(a_corr3);
          if(fabs(determ)>=determlimit){
            const tmatrix4d inv=cumath::InverseMatrix4x4(a_corr3,determ);
            const double qg = inv.a11*pwexcesssum + inv.a12*gradpwexcessx + inv.a13*gradpwexcessy + inv.a14*gradpwexcessz;
            pwexcessfinal=qg;
          }
        }
        porepress[p1]=float(double(porepress0[p1])+pwexcessfinal);
      }
    }
  }
}

template<TpKernel tker,bool sim2d> void PorePressureMdbcCorrectionT(unsigned n,float mdbcthreshold,const StDivDataGpu &dvd,const tdouble3 &mapposmin
  ,const double2 *posxy,const double *posz,const float4 *poscell,const typecode *code,const float4 *velrhop,const float3 *boundnormal,const float *porepress0,float *porepress)
{
  if(n && porepress0 && porepress && boundnormal){
    dim3 sgrid=GetSimpleGridSize(n,SPHBSIZE);
    KerPorePressureMdbcCorrection<tker,sim2d> <<<sgrid,SPHBSIZE>>> (n,mdbcthreshold,Double3(mapposmin),dvd.poscellsize,dvd.scelldiv,dvd.nc,dvd.cellzero,dvd.beginendcell+dvd.cellfluid,posxy,posz,poscell,code,velrhop,boundnormal,porepress0,porepress);
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
/// Reconstructs a three-component ghost velocity for derivative operators only.
//==============================================================================
template<bool sim2d> __global__ void KerBoundaryDerivativeVelocity(unsigned npb,unsigned npbok
  ,float threshold,unsigned slipmode,int scelldiv,int4 nc,int3 cellzero,const int2 *fluidcells
  ,const double2 *posxy,const double *posz,const typecode *code,const float4 *velrhop
  ,const float3 *boundnormal,const byte *boundmode,const byte *boundslipmode,float3 *derivativevel
  ,const unsigned *idp,const double3 *fitshifts)
{
  const unsigned p1=blockIdx.x*blockDim.x+threadIdx.x;
  if(p1>=npb)return;
  const float4 wall=velrhop[p1];
  const float3 bn=boundnormal[p1];
  const unsigned mode=(boundslipmode? unsigned(boundslipmode[p1]): slipmode);
  float3 fallback=make_float3(wall.x,wall.y,wall.z);
  if(mode==SLIP_Vel0 && bn.x==0 && bn.y==0)fallback.z=-wall.z;
  derivativevel[p1]=fallback;
  if(p1>=npbok || CODE_IsFluid(code[p1]) || (bn.x==0 && bn.y==0 && bn.z==0))return;
  if(mode>=SLIP_NoSlip && boundmode && boundmode[p1]==BMODE_MDBC2OFF)return;
  double3 gp=make_double3(posxy[p1].x+bn.x,posxy[p1].y+bn.y,posz[p1]+bn.z);
  const double3 fitshift=(fitshifts? fitshifts[idp[p1]]: make_double3(0,0,0));
  const bool shifted=(fitshift.x!=0 || fitshift.y!=0 || fitshift.z!=0);
  if(shifted){gp.x+=fitshift.x;gp.y+=fitshift.y;gp.z+=fitshift.z;}
  if(CTE.periactive)gp=KerUpdatePeriodicPos(gp);
  double sumwab=0,submerged=0;
  double sum[3]={0},gx[3]={0},gy[3]={0},gz[3]={0};
  tmatrix3d a2;cumath::Tmatrix3dReset(a2);
  tmatrix4d a3;cumath::Tmatrix4dReset(a3);
  int ini1,fin1,ini2,fin2,ini3,fin3;
  cunsearch::InitCte(gp.x,gp.y,gp.z,scelldiv,nc,cellzero,ini1,fin1,ini2,fin2,ini3,fin3);
  for(int c3=ini3;c3<fin3;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
    unsigned pini,pfin=0;cunsearch::ParticleRange(c2,c3,ini1,fin1,fluidcells,pini,pfin);
    if(pfin)for(unsigned p2=pini;p2<pfin;p2++)if(CODE_IsFluid(code[p2]) && velrhop[p2].w>0.f){
      //-Match CPU vector MLS precision; the existing scalar pressure MLS is untouched.
      const double dx=gp.x-posxy[p2].x,dy=(sim2d? 0.: gp.y-posxy[p2].y),dz=gp.z-posz[p2];
      const float rr2=float(dx*dx+dy*dy+dz*dz);
      if(rr2<=CTE.kernelsize2){
        float fac;
        const double wab=double(cufsph::GetKernel_WabFac<KERNEL_Wendland>(rr2,fac));
        const double fx=double(fac)*dx,fy=(sim2d? 0.: double(fac)*dy),fz=double(fac)*dz;
        const double vol=double(CTE.massf/velrhop[p2].w);
        const double w=wab*vol,vx=fx*vol,vy=fy*vol,vz=fz*vol;
        const float4 v=velrhop[p2];const double field[3]={double(v.x),double(v.y),double(v.z)};
        sumwab+=w;
        for(unsigned c=0;c<3;c++){sum[c]+=w*field[c];gx[c]+=vx*field[c];gy[c]+=vy*field[c];gz[c]+=vz*field[c];}
        submerged-=vol*(dx*fx+dy*fy+dz*fz);
        if(sim2d){
          a2.a11+=w; a2.a12+=dx*w; a2.a13+=dz*w;
          a2.a21+=vx;a2.a22+=dx*vx;a2.a23+=dz*vx;
          a2.a31+=vz;a2.a32+=dx*vz;a2.a33+=dz*vz;
        }
        else{
          a3.a11+=w; a3.a12+=dx*w; a3.a13+=dy*w; a3.a14+=dz*w;
          a3.a21+=vx;a3.a22+=dx*vx;a3.a23+=dy*vx;a3.a24+=dz*vx;
          a3.a31+=vy;a3.a32+=dx*vy;a3.a33+=dy*vy;a3.a34+=dz*vy;
          a3.a41+=vz;a3.a42+=dx*vz;a3.a43+=dy*vz;a3.a44+=dz*vz;
        }
      }
    }
  }
  const bool active=(submerged>0 || sumwab>=double(threshold) || (threshold>=2 && sumwab+2>=double(threshold)));
  if(!active || sumwab<=0)return;
  double ghost[3];for(unsigned c=0;c<3;c++)ghost[c]=sum[c]/sumwab;
  if(sim2d){
    const double det=cumath::Determinant3x3(a2);
    if(fabs(det)>=1e-3){
      const tmatrix3d inv=cumath::InverseMatrix3x3(a2,det);
      for(unsigned c=0;c<3;c++){
        ghost[c]=inv.a11*sum[c]+inv.a12*gx[c]+inv.a13*gz[c];
        if(shifted){
          const double qx=inv.a21*sum[c]+inv.a22*gx[c]+inv.a23*gz[c];
          const double qz=inv.a31*sum[c]+inv.a32*gx[c]+inv.a33*gz[c];
          ghost[c]+=qx*fitshift.x+qz*fitshift.z;
        }
      }
    }
  }
  else{
    const double det=cumath::Determinant4x4(a3);
    if(fabs(det)>=1e-3){
      const tmatrix4d inv=cumath::InverseMatrix4x4(a3,det);
      for(unsigned c=0;c<3;c++){
        ghost[c]=inv.a11*sum[c]+inv.a12*gx[c]+inv.a13*gy[c]+inv.a14*gz[c];
        if(shifted){
          const double qx=inv.a21*sum[c]+inv.a22*gx[c]+inv.a23*gy[c]+inv.a24*gz[c];
          const double qy=inv.a31*sum[c]+inv.a32*gx[c]+inv.a33*gy[c]+inv.a34*gz[c];
          const double qz=inv.a41*sum[c]+inv.a42*gx[c]+inv.a43*gy[c]+inv.a44*gz[c];
          ghost[c]+=qx*fitshift.x+qy*fitshift.y+qz*fitshift.z;
        }
      }
    }
  }
  if(mode==SLIP_Vel0 && bn.x==0 && bn.y==0)
    derivativevel[p1]=make_float3(wall.x,wall.y,-float(0.0+ghost[2]));
  else if(mode==SLIP_NoSlip)
    derivativevel[p1]=make_float3(float(2.0*double(wall.x)-ghost[0]),float(2.0*double(wall.y)-ghost[1]),float(2.0*double(wall.z)-ghost[2]));
  else{
    const double len=sqrt(double(bn.x)*bn.x+double(bn.y)*bn.y+double(bn.z)*bn.z);
    const double nx=double(bn.x)/len,ny=double(bn.y)/len,nz=double(bn.z)/len;
    const double reflection=(double(wall.x)*nx+double(wall.y)*ny+double(wall.z)*nz)-(ghost[0]*nx+ghost[1]*ny+ghost[2]*nz);
    if(mode==SLIP_FreeSlip)
      derivativevel[p1]=make_float3(float(ghost[0]+2.0*reflection*nx),float(ghost[1]+2.0*reflection*ny),float(ghost[2]+2.0*reflection*nz));
    else derivativevel[p1]=make_float3(float(double(wall.x)+reflection*nx),float(double(wall.y)+reflection*ny),float(double(wall.z)+reflection*nz));
  }
}

void BoundaryDerivativeVelocity(bool simulate2d,unsigned npb,unsigned npbok,float mdbcthreshold
  ,TpSlipMode slipmode,const StDivDataGpu &dvd,const double2 *posxy,const double *posz
  ,const typecode *code,const float4 *velrhop,const float3 *boundnormal
  ,const byte *boundmode,const byte *boundslipmode,float3 *boundderivativevel
  ,const unsigned *idp,const double3 *fitshift)
{
  if(!npb)return;
  const dim3 grid=GetSimpleGridSize(npb,SPHBSIZE);
  if(simulate2d)KerBoundaryDerivativeVelocity<true><<<grid,SPHBSIZE>>>(npb,npbok,mdbcthreshold,unsigned(slipmode),dvd.scelldiv,dvd.nc,dvd.cellzero,dvd.beginendcell+dvd.cellfluid,posxy,posz,code,velrhop,boundnormal,boundmode,boundslipmode,boundderivativevel,idp,fitshift);
  else KerBoundaryDerivativeVelocity<false><<<grid,SPHBSIZE>>>(npb,npbok,mdbcthreshold,unsigned(slipmode),dvd.scelldiv,dvd.nc,dvd.cellzero,dvd.beginendcell+dvd.cellfluid,posxy,posz,code,velrhop,boundnormal,boundmode,boundslipmode,boundderivativevel,idp,fitshift);
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
  ,const float3 *boundnormal,const float3 *motionvel,float4 *velrhop,tsymatrix3d *sigma,byte *boundmode,const byte *boundslipmode,float3 *tangenvel
  ,const float *porepress0,float *porepress)
{
  const unsigned p1=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p1<n){
    const bool extrapolatepore=(porepress0 && porepress);
    const float3 bnormalp1=boundnormal[p1];
    if(bnormalp1.x!=0 || bnormalp1.y!=0 || bnormalp1.z!=0){
      const TpSlipMode slipmodep1=(boundslipmode? TpSlipMode(boundslipmode[p1]): tslip);
      const bool useboundmode=(boundmode && slipmodep1>=SLIP_NoSlip);
      float rhopfinal=FLT_MAX;
      float3 velrhopfinal=make_float3(0,0,0);
      tsymatrix3f sigmafinal={0,0,0,0,0,0};//mdbr
      float sumwab=0;
      float submerged=0;
      double pwexcesssum=0;
      double gradpwexcessx=0,gradpwexcessy=0,gradpwexcessz=0;

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
            const tsymatrix3f sigmap2=KerStressToFloat(sigma[p2]);//mdbr
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
            if(slipmodep1!=SLIP_Vel0) {
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
      const bool poremls=(CTE.poremdbcinterp==1);
      bool hasinv2=false;
      bool hasinv3=false;
      tmatrix3f invacorr2; if(sim2d) cumath::Tmatrix3fReset(invacorr2);
      tmatrix4f invacorr3; if(!sim2d)cumath::Tmatrix4fReset(invacorr3);
      if(activebound || (poremls && extrapolatepore && activepore && sumwab>0)){
        if(sim2d){
          const double determ=cumath::Determinant3x3dbl(a_corr2);
          if(fabs(determ)>=double(determlimit)){
            invacorr2=cumath::InverseMatrix3x3dbl(a_corr2,determ);
            hasinv2=true;
          }
        }
        else{
          const double determ=cumath::Determinant4x4dbl(a_corr3);
          if(fabs(determ)>=double(determlimit)){
            invacorr3=cumath::InverseMatrix4x4dbl(a_corr3,determ);
            hasinv3=true;
          }
        }
      }
      if(extrapolatepore && activepore && sumwab>0){
        double pwexcessfinal=pwexcesssum/double(sumwab); //-0th-order fallback.
        if(poremls && sim2d){
          if(hasinv2){
            const double qg = double(invacorr2.a11)*pwexcesssum + double(invacorr2.a12)*gradpwexcessx + double(invacorr2.a13)*gradpwexcessz;
            pwexcessfinal=qg;
          }
        }
        else if(poremls){
          if(hasinv3){
            const double qg = double(invacorr3.a11)*pwexcesssum + double(invacorr3.a12)*gradpwexcessx + double(invacorr3.a13)*gradpwexcessy + double(invacorr3.a14)*gradpwexcessz;
            pwexcessfinal=qg;
          }
        }
        porepress[p1]=float(double(porepress0[p1])+pwexcessfinal);
      }
      if(activebound){
        if(useboundmode)boundmode[p1]=BMODE_MDBC2;
        const float3 dpos=make_float3(-bnormalp1.x,-bnormalp1.y,-bnormalp1.z); //-Boundary particle position - ghost node position.
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
          else if(a_corr2.a11>0){//-Determinant is small but a11 is nonzero, 0th order ANGELO.
            //rhopfinal=float(rhopp1/a_corr2.a11);
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
          if(a_corr3.a11>0&&slipmodep1!=SLIP_Vel0){
            velrhopfinal.x=float(velp1.x/a_corr3.a11);
            velrhopfinal.y=float(velp1.y/a_corr3.a11);
            velrhopfinal.z=float(velp1.z/a_corr3.a11);
          }
        }
        //-Store the results.
        rhopfinal=CTE.rhopzero;//(rhopfinal!=FLT_MAX? rhopfinal: CTE.rhopzero);
        if(slipmodep1==SLIP_Vel0){//-DBC vel=0
          velrhop[p1].w=rhopfinal;
          sigma[p1] = KerStressToDouble(sigmafinal);
        }
        if(slipmodep1==SLIP_NoSlip){//-No-Slip
          const float3 v=motionvel[p1];
          const float3 v2=make_float3(v.x+v.x-velrhopfinal.x,v.y+v.y-velrhopfinal.y,v.z+v.z-velrhopfinal.z);
          velrhop[p1].w=rhopfinal;
          if(tangenvel)tangenvel[p1]=KerMdbc2TangenVel(bnormalp1,v2);
          sigma[p1] = KerStressToDouble(sigmafinal);
        }
        if(slipmodep1==SLIP_FreeSlip){//-Free-slip keeps boundary velocity and stores extrapolated tangential velocity.
          velrhop[p1].w=rhopfinal;
          if(tangenvel)tangenvel[p1]=KerMdbc2TangenVel(bnormalp1,velrhopfinal);
          sigma[p1] = KerStressToDouble(sigmafinal);
        }
      }
      else if(useboundmode){
        boundmode[p1]=BMODE_MDBC2OFF;
        velrhop[p1].w=CTE.rhopzero;
        const tsymatrix3d sigmazero={0,0,0,0,0,0};
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
  ,const float3 *boundnormal,const float3 *motionvel,float4 *velrhop,tsymatrix3d *sigma,byte *boundmode,const byte *boundslipmode,float3 *tangenvel
  ,const float *porepress0,float *porepress)
{
  const unsigned p1=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p1<n){
    const bool extrapolatepore=(porepress0 && porepress);
    const float3 bnormalp1=boundnormal[p1];
    if(bnormalp1.x!=0 || bnormalp1.y!=0 || bnormalp1.z!=0){
      const TpSlipMode slipmodep1=(boundslipmode? TpSlipMode(boundslipmode[p1]): tslip);
      const bool useboundmode=(boundmode && slipmodep1>=SLIP_NoSlip);
      float rhopfinal=FLT_MAX;
      float3 velrhopfinal=make_float3(0,0,0);
      tsymatrix3f sigmafinal={0,0,0,0,0,0};//mdbr
      float sumwab=0;
      float submerged=0;
      double pwexcesssum=0;
      double gradpwexcessx=0,gradpwexcessy=0,gradpwexcessz=0;

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
            const tsymatrix3f sigmap2=KerStressToFloat(sigma[p2]);//mdbr
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
            if(slipmodep1!=SLIP_Vel0) {
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
      const bool poremls=(CTE.poremdbcinterp==1);
      bool hasinv2=false;
      bool hasinv3=false;
      tmatrix3d invacorr2; if(sim2d) cumath::Tmatrix3dReset(invacorr2);
      tmatrix4d invacorr3; if(!sim2d)cumath::Tmatrix4dReset(invacorr3);
      if(activebound || (poremls && extrapolatepore && activepore && sumwab>0)){
        if(sim2d){
          const double determ=cumath::Determinant3x3(a_corr2);
          if(fabs(determ)>=double(determlimit)){
            invacorr2=cumath::InverseMatrix3x3(a_corr2,determ);
            hasinv2=true;
          }
        }
        else{
          const double determ=cumath::Determinant4x4(a_corr3);
          if(fabs(determ)>=double(determlimit)){
            invacorr3=cumath::InverseMatrix4x4(a_corr3,determ);
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
        const float3 dpos=make_float3(-bnormalp1.x,-bnormalp1.y,-bnormalp1.z); //-Boundary particle position - ghost node position.
        if(sim2d){
          if(hasinv2){//-Use 1e-3f (first_order) or 1e+3f (zeroth_order).
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
          if(a_corr2.a11>0&&slipmodep1!=SLIP_Vel0){
            velrhopfinal.x=float(velp1.x/a_corr2.a11);
            velrhopfinal.z=float(velp1.z/a_corr2.a11);
            velrhopfinal.y=0;
          }
        }
        else{
          if(hasinv3){
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
          if(a_corr3.a11>0&&slipmodep1!=SLIP_Vel0){
            velrhopfinal.x=float(velp1.x/a_corr3.a11);
            velrhopfinal.y=float(velp1.y/a_corr3.a11);
            velrhopfinal.z=float(velp1.z/a_corr3.a11);
          }
        }
        //-Store the results.
        rhopfinal=(rhopfinal!=FLT_MAX? rhopfinal: CTE.rhopzero);
        if(slipmodep1==SLIP_Vel0){//-DBC vel=0
          velrhop[p1].w=rhopfinal;
          sigma[p1]=KerStressToDouble(sigmafinal);//mdbr
        }
        if(slipmodep1==SLIP_NoSlip){//-No-Slip
          const float3 v=motionvel[p1];
          const float3 v2=make_float3(v.x+v.x-velrhopfinal.x,v.y+v.y-velrhopfinal.y,v.z+v.z-velrhopfinal.z);
          velrhop[p1].w=rhopfinal;
          if(tangenvel)tangenvel[p1]=KerMdbc2TangenVel(bnormalp1,v2);
          sigma[p1]=KerStressToDouble(sigmafinal);//mdbr
        }
        if(slipmodep1==SLIP_FreeSlip){//-Free-slip keeps boundary velocity and stores extrapolated tangential velocity.
          velrhop[p1].w=rhopfinal;
          if(tangenvel)tangenvel[p1]=KerMdbc2TangenVel(bnormalp1,velrhopfinal);
          sigma[p1]=KerStressToDouble(sigmafinal);//mdbr
        }
      }
      else if(useboundmode){
        boundmode[p1]=BMODE_MDBC2OFF;
        velrhop[p1].w=CTE.rhopzero;
        const tsymatrix3d sigmazero={0,0,0,0,0,0};
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
  ,float4 *velrhop,tsymatrix3d *sigma,byte *boundmode,const byte *boundslipmode,float3 *tangenvel
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
        ,posxy,posz,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
    }
    else{//-mDBC_v0
      KerInteractionMdbcCorrection_Dbl <tker,sim2d,tslip> <<<sgridb,bsbound>>> (n,nbound
        ,determlimit,mdbcthreshold,dvd.scelldiv,dvd.nc,dvd.cellzero,beginendcellfluid
        ,posxy,posz,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
    }
  }
}
//==============================================================================
template<TpKernel tker> void Interaction_MdbcCorrectionT(bool simulate2d
  ,TpSlipMode slipmode,bool fastsingle,unsigned n,unsigned nbound
  ,float mdbcthreshold,const StDivDataGpu &dvd,const tdouble3 &mapposmin
  ,const double2 *posxy,const double *posz,const float4 *poscell,const typecode *code
  ,const unsigned *idp,const float3 *boundnormal,const float3 *motionvel,float4 *velrhop,tsymatrix3d *sigma,byte *boundmode,const byte *boundslipmode,float3 *tangenvel
  ,const float *porepress0,float *porepress)
{
  switch(slipmode){
    case SLIP_Vel0:{ const TpSlipMode tslip=SLIP_Vel0;
      if(simulate2d)Interaction_MdbcCorrectionT2 <tker,true ,tslip> (fastsingle,n,nbound,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
      else          Interaction_MdbcCorrectionT2 <tker,false,tslip> (fastsingle,n,nbound,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
    }break;
    case SLIP_NoSlip:{ const TpSlipMode tslip=SLIP_NoSlip;
      if(simulate2d)Interaction_MdbcCorrectionT2 <tker,true ,tslip> (fastsingle,n,nbound,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
      else          Interaction_MdbcCorrectionT2 <tker,false,tslip> (fastsingle,n,nbound,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
    }break;
    case SLIP_FreeSlip:{ const TpSlipMode tslip=SLIP_FreeSlip;
      if(simulate2d)Interaction_MdbcCorrectionT2 <tker,true ,tslip> (fastsingle,n,nbound,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
      else          Interaction_MdbcCorrectionT2 <tker,false,tslip> (fastsingle,n,nbound,mdbcthreshold,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
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
  ,const unsigned *idp,const float3 *boundnormal,const float3 *motionvel,float4 *velrhop,tsymatrix3d *sigma,byte *boundmode,const byte *boundslipmode,float3 *tangenvel
  ,const float *porepress0,float *porepress)
{
  switch(tkernel){
    case KERNEL_Wendland:{ const TpKernel tker=KERNEL_Wendland;
      Interaction_MdbcCorrectionT <tker> (simulate2d,slipmode,fastsingle,n,nbound,mdbcthreshold
        ,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
    }break;
#ifndef DISABLE_KERNELS_EXTRA
    case KERNEL_Cubic:{ const TpKernel tker=KERNEL_Cubic;
      Interaction_MdbcCorrectionT <tker> (simulate2d,slipmode,fastsingle,n,nbound,mdbcthreshold
        ,dvd,mapposmin,posxy,posz,poscell,code,idp,boundnormal,motionvel,velrhop,sigma,boundmode,boundslipmode,tangenvel,porepress0,porepress);
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
  ,const float3 *motionvel,float4 *velrhop,tsymatrix3d *sigma,const byte *boundslipmode)
{
  const unsigned p1=blockIdx.x*blockDim.x + threadIdx.x; //-Number of particle.
  if(p1<n){
      const typecode cod=code[p1];
      if(CODE_IsNotFluid(cod)){
      const TpSlipMode slipmodep1=(boundslipmode? TpSlipMode(boundslipmode[p1]): tslip);
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
			const tsymatrix3f sigmap2=KerStressToFloat(sigma[p2]);//mdbr
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
          if(slipmodep1!=SLIP_Vel0&&a_corr2.a11>0){
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
          if(slipmodep1!=SLIP_Vel0&&a_corr3.a11>0){
            velrhopfinal.x=float(velp1.x/a_corr3.a11);
            velrhopfinal.y=float(velp1.y/a_corr3.a11);
            velrhopfinal.z=float(velp1.z/a_corr3.a11);
          }
        }        
        if (slipmodep1==SLIP_Vel0) {//-DBC velocity as it is
            velrhopfinal = make_float3(velrhop[p1].x, velrhop[p1].y, velrhop[p1].z);
      }
        if (slipmodep1==SLIP_NoSlip) {//-No-Slip
      const float3 v = motionvel[p1];
            velrhopfinal = make_float3(v.x + v.x - velrhopfinal.x, v.y + v.y - velrhopfinal.y, v.z + v.z - velrhopfinal.z);
        }
      }
      //-Store the results.
      rhopfinal=CTE.rhopzero;// (rhopfinal != FLT_MAX ? rhopfinal : CTE.rhopzero);
      velrhop[p1] = make_float4(velrhopfinal.x, velrhopfinal.y, velrhopfinal.z, rhopfinal);
      sigma[p1] = KerStressToDouble(sigmafinal);
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
  ,float4 *velrhop,tsymatrix3d *sigma,const byte *boundslipmode)
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
        ,posxy,posz,code,idp,motionvel,velrhop,sigma,boundslipmode);
  }
}
//==============================================================================
template<TpKernel tker> void Interaction_CdbcCorrectionT(bool simulate2d
  ,TpSlipMode slipmode,unsigned n,unsigned nbound
  ,float mdbcthreshold,const StDivDataGpu &dvd
  ,const double2 *posxy,const double *posz
  ,const unsigned* dcell,const float4 *poscell,const typecode *code
  ,const unsigned *idp,const float3 *motionvel,float4 *velrhop,tsymatrix3d *sigma,const byte *boundslipmode)
{
  switch(slipmode){
    case SLIP_Vel0:{ const TpSlipMode tslip=SLIP_Vel0;
      if(simulate2d)Interaction_CdbcCorrectionT2 <tker,true ,tslip> (n,nbound,mdbcthreshold,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma,boundslipmode);
      else          Interaction_CdbcCorrectionT2 <tker,false,tslip> (n,nbound,mdbcthreshold,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma,boundslipmode);
    }break;
    case SLIP_NoSlip:{ const TpSlipMode tslip=SLIP_NoSlip;
      if(simulate2d)Interaction_CdbcCorrectionT2 <tker,true ,tslip> (n,nbound,mdbcthreshold,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma,boundslipmode);
      else          Interaction_CdbcCorrectionT2 <tker,false,tslip> (n,nbound,mdbcthreshold,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma,boundslipmode);
    }break;
#ifndef DISABLE_MDBC_EXTRAMODES
    case SLIP_FreeSlip:{ const TpSlipMode tslip=SLIP_FreeSlip;
      if(simulate2d)Interaction_CdbcCorrectionT2 <tker,true ,tslip> (n,nbound,mdbcthreshold,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma,boundslipmode);
      else          Interaction_CdbcCorrectionT2 <tker,false,tslip> (n,nbound,mdbcthreshold,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma,boundslipmode);
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
    ,const float3 *motionvel,float4 *velrhop,tsymatrix3d *sigma,const byte *boundslipmode)
{
  switch(tkernel){
    case KERNEL_Wendland:{ const TpKernel tker=KERNEL_Wendland;
      Interaction_CdbcCorrectionT <tker> (simulate2d,slipmode,n,nbound,mdbcthreshold
        ,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma,boundslipmode);
    }break;
#ifndef DISABLE_KERNELS_EXTRA
    case KERNEL_Cubic:{ const TpKernel tker=KERNEL_Cubic;
      Interaction_CdbcCorrectionT <tker> (simulate2d,slipmode,n,nbound,mdbcthreshold
        ,dvd,posxy,posz,dcell,poscell,code,idp,motionvel,velrhop,sigma,boundslipmode);
    }break;
#endif
    default: throw "Kernel unknown at Interaction_CdbcCorrection().";
  }
}
//<vs_cdbc_end>

//==============================================================================
/// Read-only union of the existing fluid/marker distance predicates.
//==============================================================================
__global__ void KerCheckHydroMechNoWallSupport(unsigned npbok
  ,int scelldiv,int4 nc,int3 cellzero,const int2 *fluidcells
  ,const double2 *posxy,const double *posz,const float4 *poscell,const typecode *code,unsigned *invalid)
{
  const unsigned p1=blockIdx.x*blockDim.x+threadIdx.x;
  if(p1>=npbok)return;
  const double2 xy=posxy[p1];
  const double z=posz[p1];
  const float4 pc1=poscell[p1];
  int ini1,fin1,ini2,fin2,ini3,fin3;
  cunsearch::InitCte(xy.x,xy.y,z,scelldiv,nc,cellzero,ini1,fin1,ini2,fin2,ini3,fin3);
  for(int c3=ini3;c3<fin3;c3+=nc.w)for(int c2=ini2;c2<fin2;c2+=nc.x){
    unsigned pini=0,pfin=0;
    cunsearch::ParticleRange(c2,c3,ini1,fin1,fluidcells,pini,pfin);
    if(pfin)for(unsigned p2=pini;p2<pfin;p2++)if(CODE_IsFluid(code[p2])){
      const double dx=xy.x-posxy[p2].x,dy=(CTE.simulate2d? 0.: xy.y-posxy[p2].y),dz=z-posz[p2];
      const double rr2=dx*dx+dy*dy+dz*dz;
      const float fx=float(dx),fy=float(dy),fz=float(dz);
      const float directrr2=fx*fx+fy*fy+fz*fz;
      const float4 pc2=poscell[p2];
      const float px=pc1.x-pc2.x+CTE.poscellsize*(PSCEL_GetfX(pc1.w)-PSCEL_GetfX(pc2.w));
      const float py=pc1.y-pc2.y+CTE.poscellsize*(PSCEL_GetfY(pc1.w)-PSCEL_GetfY(pc2.w));
      const float pz=pc1.z-pc2.z+CTE.poscellsize*(PSCEL_GetfZ(pc1.w)-PSCEL_GetfZ(pc2.w));
      const float packedrr2=px*px+py*py+pz*pz;
      const float fsrr2=(CTE.simulate2d? px*px+pz*pz: packedrr2);
      if(rr2<=double(CTE.kernelsize2) || directrr2<=CTE.kernelsize2
        || float(rr2)<=CTE.kernelsize2 || packedrr2<=CTE.kernelsize2 || fsrr2<=CTE.kernelsize2){
        atomicMin(invalid,p1);return;
      }
    }
  }
}

void CheckHydroMechNoWallSupport(unsigned npbok,const StDivDataGpu &dvd
  ,const double2 *posxy,const double *posz,const float4 *poscell,const typecode *code,unsigned *invalid)
{
  if(npbok){
    const dim3 grid=GetSimpleGridSize(npbok,SPHBSIZE);
    KerCheckHydroMechNoWallSupport<<<grid,SPHBSIZE>>>(npbok,dvd.scelldiv,dvd.nc,dvd.cellzero
      ,dvd.beginendcell+dvd.cellfluid,posxy,posz,poscell,code,invalid);
  }
}

