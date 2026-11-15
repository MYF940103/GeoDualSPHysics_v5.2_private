using cusphs::StPorosityRhopState;

template<bool corrector> static __device__ __forceinline__ bool CachedPorosityRhopCache
  (StPorosityRhopState state,unsigned p,double dt,float rho0,float minimum,float maximum,float &cache,const StSoilCte& cached_soil)
{
  const double jstage=state.j[p];
  double value=jstage;
  if(corrector){value=state.jn[p];value+=dt*jstage*state.theta[p];}
  const double rhow=double(cached_soil.PoreWaterRho);
  const double rhot=rhow+(double(rho0)-rhow)/value;
  const bool out=(!isfinite(value) || value<=1.-double(cached_soil.Porosity)
    || !isfinite(rhot) || rhot<=0 || rhot<minimum || rhot>maximum);
  cache=float(rhot);
  return(out || !isfinite(cache) || cache<=0.f);
}

template<bool floating,bool shift,bool inout,TpDPCtes dpctes> __global__ void CachedSymplecticPre
  (unsigned n,unsigned npb
  ,const float4 *velrhoppre,const float *ar,const float3 *ace,const float4 *shiftposfs
  ,const double2 *sigmapre,const float *kplasticpre,const float2 *rsigma
  ,const float3 *indirvel,double dtm,float rhopzero,float rhopoutmin,float rhopoutmax,float3 gravity
  ,typecode *code,double2 *movxy,double *movz,float4 *velrhop
  ,double2 *sigma,float *kplastic,float *kplasticdk,StPorosityRhopState porostate,unsigned *materialerror,bool requireelastic,CacheView cache,unsigned source_step,double source_time,const unsigned* native_id,StSoilCte cached_soil)
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
      if(feedbackj)feedbackout=CachedPorosityRhopCache<false>(porostate,p,dtm,rhopzero,rhopoutmin,rhopoutmax,rvelrhopnew.w,cached_soil);
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
        float kplasticold=kplasticpre[p];
        if(!ReadCachedMaterial(cache,p,native_id[p],source_step,source_time,dtm,false,
          sigmapre_xx_xy,sigmapre_xz_yy,sigmapre_yz_zz,rsigma_xx_xy,rsigma_xz_yy,rsigma_yz_zz,kplasticold,
          sigmanew_xx_xy,sigmanew_xz_yy,sigmanew_yz_zz,kplasticnew,materialerror,requireelastic))return;
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
#if defined(C08_STAGE_TRACE) && defined(C08_CAUSAL_TRACE)
      C08CausalMaterialSaved(p,kplastic[p]);
#endif
    }
  }
}

template<bool floating,bool shift,bool inout,TpDPCtes dpctes> __global__ void CachedSymplecticCor
  (unsigned n,unsigned npb
  ,const float4 *velrhoppre,const float *ar,const float3 *ace,const float4 *shiftposfs
  ,const double2 *sigmapre,const float *kplasticpre,const float2 *rsigma
  ,const float3 *indirvel,const float4 *nopenshift,TpMdbc2Mode mdbc2,double dtm,double dt,float rhopzero,float rhopoutmin,float rhopoutmax,float3 gravity
  ,typecode *code,double2 *movxy,double *movz,float4 *velrhop
  ,double2 *sigma,float *kplastic,float *kplasticdk,StPorosityRhopState porostate,unsigned *materialerror,bool requireelastic,CacheView cache,unsigned source_step,double source_time,const unsigned* native_id,StSoilCte cached_soil)
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
      if(feedbackj)feedbackout=CachedPorosityRhopCache<true>(porostate,p,dt,rhopzero,rhopoutmin,rhopoutmax,rvelrhopnew.w,cached_soil);
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
        float kplasticold=kplasticpre[p];
        if(!ReadCachedMaterial(cache,p,native_id[p],source_step,source_time,dt,true,
          sigmapre_xx_xy,sigmapre_xz_yy,sigmapre_yz_zz,rsigma_xx_xy,rsigma_xz_yy,rsigma_yz_zz,kplasticold,
          sigmanew_xx_xy,sigmanew_xz_yy,sigmanew_yz_zz,kplasticnew,materialerror,requireelastic))return;
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
#if defined(C08_STAGE_TRACE) && defined(C08_CAUSAL_TRACE)
      C08CausalMaterialSaved(p,kplastic[p]);
#endif
    }
  }
}
