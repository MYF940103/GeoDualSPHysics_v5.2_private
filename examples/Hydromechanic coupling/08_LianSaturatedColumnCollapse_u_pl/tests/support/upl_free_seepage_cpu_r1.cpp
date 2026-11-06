// Private zero-step free-seepage candidate. No wall fit, integrator or public admission.
#define main RetainedFeedbackMain
#include "../../../02_TerzaghiConsolidation_q0_PR/tests/support/upl_p2_feedback_harness_r1.cpp"
#undef main
#include <limits>

static double SDot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static tdouble3 SProduct(tmatrix3d c,tdouble3 a){return TDouble3(c.a11*a.x+c.a12*a.y+c.a13*a.z,c.a21*a.x+c.a22*a.y+c.a23*a.z,c.a31*a.x+c.a32*a.y+c.a33*a.z);}
class Seepage:public Feedback{
  static constexpr unsigned Count=81;
  struct Point{tdouble3 x;unsigned id,key;};
  struct Reference{double raw=0,old=0,naive=0,limit=0,oldlimit=0,head=0,curvature=0,continuum=0;};
  using StateRow=std::array<double,18>;
  std::vector<unsigned> Cells;
  unsigned RateRows=0,InnerRows=0,SurfaceRows=0,NegativeRows=0,ProjectionRows=0,NonfiniteRows=0;
  unsigned MaskInner[3]={},MaskSurface[3]={};
  double MaxReferenceRatio=0,MaxHydroRatio=0,MaxNaiveRatio=0;
  void Policy(bool value){
    #ifndef UPL_FREE_SEEPAGE_LEGACY_ONLY
      HydroMechFreeSeepage=value;
    #else
      Require(!value,"Legacy closure cannot run the new policy");
    #endif
  }
  bool Surface(unsigned p)const{return IsFreeSurfaceParticle(p,Codec,FSTypec);}
  void NoStep()const{Require(TimeStep==0&&Nstep==0&&!PoroJPrec&&!PorePressPrec,"A physical stage/time was advanced");}
  std::vector<StateRow> State(bool omitPressure=false)const{
    std::vector<StateRow> result;for(unsigned p=0;p<Np;p++){
      const auto x=Posc[p];const auto v=Velrhopc[p];const auto s=Sigmac[p];
      result.push_back({x.x,x.y,x.z,v.x,v.y,v.z,v.w,(omitPressure?0.:double(PorePressc[p])),PorePress0c[p],PoroJc[p],PoroThetac[p],s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,Kplasticc[p]});
      for(double a:result.back())Require(std::isfinite(a),"Nonfinite native state");
    }return result;
  }
  void CellTable(){
    const tuint3 nc=TUint3(5,1,5);const unsigned ncell=nc.x*nc.y*nc.z,code=DCEL_GetCode(27,2,2);
    Require(!Npb||(Npb==1&&Idpc[0]==0&&Posc[0].x==0&&Posc[0].y==0&&Posc[0].z==0),"Projection boundary is not the first real corner");
    std::vector<Point> points;for(unsigned p=0;p<Np;p++){
      const auto x=Posc[p];const unsigned cx=unsigned(x.x/KernelSize),cz=unsigned(x.z/KernelSize);
      Require(cx<nc.x&&cz<nc.z,"Manufactured point is outside cell table");points.push_back({x,Idpc[p],cx+nc.x*cz});
    }
    // Initial fixture is fluid-only. In projection mode slot0 is the already first corner.
    std::stable_sort(points.begin()+Npb,points.end(),[](const Point& a,const Point& b){return a.key<b.key;});
    Require(!Npb||points[0].key==0,"Projection boundary key is not the minimum cell");
    Cells.assign(2*(ncell+1),0);
    for(unsigned group=0;group<2;group++){
      unsigned cursor=group? Npb:0;const unsigned end=group? Np:Npb;
      for(unsigned c=0;c<=ncell;c++){while(cursor<end&&points[cursor].key<c)cursor++;Cells[group*(ncell+1)+c]=cursor;}
    }
    DivData=MakeDivDataCpu(1,nc,TUint3(0),Cells.data(),KernelSize,code,TDouble3(0));
    for(unsigned p=0;p<Np;p++){
      const auto a=points[p];Posc[p]=a.x;Idpc[p]=a.id;Codec[p]=(p<Npb? CODE_TYPE_FIXED:CODE_TYPE_FLUID);
      Dcellc[p]=DCEL_Cell(code,a.key%nc.x,0,a.key/nc.x);
    }
  }
  void Field(unsigned field){
    Require(field<3,"Unknown manufactured field");
    for(unsigned p=0;p<Np;p++){
      const auto u=Posc[p]-TDouble3(1,0,1);double pressure=128.;tdouble3 a=TDouble3(1./32.,0,1./16.);
      if(field==0){pressure+=double(SoilCte.PoreWaterRho)*SDot(ToTDouble3(Gravity),Posc[p]);a=ToTDouble3(Gravity)*-1.;}
      else{pressure+=16*u.x-32*u.z;if(field==2)a=a+TDouble3(u.x/16.+u.z/32.,0,u.x/32.-u.z/32.);}
      Require(fabs(pressure)<=256&&double(float(pressure))==pressure,"Pressure manufacture is not exact binary32 within the retained256 scale");
      const auto af=ToTFloat3(a);Require(double(af.x)==a.x&&double(af.y)==a.y&&double(af.z)==a.z,"Acceleration input is not exact binary32");
      Velrhopc[p]=TFloat4(0,0,0,RhopZero);Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;
      PoroJc[p]=1;PoroThetac[p]=0;PorePressc[p]=float(pressure);PorePress0c[p]=0;PorePressRatec[p]=1234567.f;
    }
  }
  double Potential(unsigned field,unsigned p)const{
    const auto x=Posc[p];if(field==0)return -SDot(ToTDouble3(Gravity),x);
    const auto u=x-TDouble3(1,0,1);return u.x/32.+u.z/16.+(field==2? u.x*u.x/32.+u.x*u.z/32.-u.z*u.z/64.:0.);
  }
  tdouble3 Acceleration(unsigned field,unsigned p)const{
    if(field==0)return ToTDouble3(Gravity)*-1.;const auto u=Posc[p]-TDouble3(1,0,1);
    return TDouble3(1./32.,0,1./16.)+(field==2? TDouble3(u.x/16.+u.z/32.,0,u.x/32.-u.z/32.):TDouble3(0));
  }
  Reference Assemble(unsigned field,unsigned i)const{
    Reference r;const double rho=SoilCte.PoreWaterRho,v0=double(MassFluid)/RhopZero,kw=SoilCte.PoreWaterBulkModulus;
    const double n=1.-(1.-double(SoilCte.Porosity))/PoroJc[i],scale=kw/n*double(SoilCte.HydraulicConductivity)/(rho*9.80665);
    double lp=0,da=0,lpabs=0,daabs=0;tdouble3 gp=TDouble3(0),lx=TDouble3(0);
    // Independent all-particle search; potential differences, not the production cell walker.
    for(unsigned j=0;j<Np;j++){
      const auto d=Posc[i]-Posc[j];const double rr=SDot(d,d);if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;
      const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Cubic>(CSP,float(rr))),gi=SProduct(CorrMatc[i],g),gj=SProduct(CorrMatc[j],g);
      const double v=v0*PoroJc[j],w=v*SDot(d,gi+gj)/(rr+double(Eta2)),dp=double(PorePressc[i])-PorePressc[j];
      const double dh=dp+rho*(Potential(field,i)-Potential(field,j));
      const double db=field==2? d.x*d.x/16.+d.x*d.z/16.-d.z*d.z/32.:0.;
      const auto delta=ToTDouble3(Acec[j])-ToTDouble3(Acec[i]);const double divergence=v*SDot(delta,gi);
      r.head+=w*dh;r.curvature+=rho*(.5*w*db+divergence);
      lp+=w*dp;lx=lx+d*w;gp=gp-gi*(v*dp);da+=divergence;
      lpabs+=fabs(w*dp);daabs+=v*(fabs(delta.x*gi.x)+fabs(delta.z*gi.z));
    }
    r.raw=scale*(r.head+r.curvature);r.old=scale*(lp-SDot(gp,lx)+rho*da);r.naive=scale*(lp+rho*da);
    r.continuum=field==2? scale*rho*(1./16.-1./32.):0.;
    // Same retained direct-sum roundoff constants; no fitted physical accuracy gate.
    const double base=32*FLT_EPSILON+4096*DBL_EPSILON;
    r.oldlimit=base*(std::max)(1.,scale*(lpabs+fabs(gp.x*lx.x)+fabs(gp.y*lx.y)+fabs(gp.z*lx.z)+rho*daabs));
    r.limit=base*(std::max)(1.,scale*(lpabs+rho*(fabs(double(Acec[i].x)*lx.x)+fabs(double(Acec[i].z)*lx.z)+daabs)));return r;
  }
public:
  Seepage():Feedback(2,9){
    NoStep();
    Np=CaseNp=CaseNfluid=Count;Npb=NpbOk=CaseNpb=CaseNfixed=0;NpfPer=NpbPer=0;
    // Alloc calls FreeCpuMemoryParticles/ArraysCpu::Reset; rebind EVERY basic array.
    AllocCpuMemoryParticles(Count,0);ReserveBasicArraysCpu();
    Require(Count<=CpuParticlesSize&&CheckCpuParticlesSize(Count),"Retained allocator capacity is insufficient for81 points");
    InitPorosityObserverCpu(); // Real fresh81 J/theta initialization under inherited zero-g/k0/private dynamicOFF.
    TKernel=KERNEL_Cubic;CSP.tkernel=TKernel;KernelH=float(1.2*Dp);KernelSize=2*KernelH;KernelSize2=KernelSize*KernelSize;Eta2=.01f*KernelH*KernelH;
    CSP.kernelh=KernelH;CSP.kernelsize=KernelSize;CSP.kernelsize2=KernelSize2;CSP.eta2=Eta2;CSP.kcubic=fsph::GetKernelCubic_Ctes(true,KernelH);
    DynamicPorePressure=true;DynamicPoreWall=false;DynamicPoreConductivity=false;SoilCte.HydraulicConductivity=1e-5f;
    Gravity=CSP.gravity=TFloat3(0,0,-1./16.);Policy(false);
    unsigned p=0;for(int z=-4;z<=4;z++)for(int x=-4;x<=4;x++,p++){Posc[p]=TDouble3(1+x*Dp,0,1+z*Dp);Idpc[p]=p;}
    CellTable();Field(0);for(unsigned i=0;i<Np;i++){FSTypec[i]=FST_Inner;FSNormalc[i]=TFloat3(0);PosDivc[i]=0;CorrMatc[i]=TMatrix3d(0);HydroMechLoadAcec[i]=TFloat3(0);}
  }
  void Rates(std::ostream& out,std::ostream& mask,std::ostream& off){
    for(unsigned field=0;field<3;field++){
      Field(field);Policy(false);PreInteraction_Forces();ComputeFreeSurfaceTracking();
      unsigned inner=0,surface=0;for(unsigned p=0;p<Np;p++){Surface(p)?surface++:inner++;Acec[p]=ToTFloat3(Acceleration(field,p));mask<<field<<','<<Idpc[p]<<','<<Posc[p].x<<','<<Posc[p].z<<','<<FSTypec[p]<<','<<PosDivc[p]<<'\n';}
      Require(inner>0&&surface>0,"Actual FS mask has empty interior or truncated-surface coverage");
      MaskInner[field]=inner;MaskSurface[field]=surface;
      const auto before=State();const std::vector<tfloat3> acceleration(Acec,Acec+Np);std::vector<Reference> ref;for(unsigned p=0;p<Np;p++)ref.push_back(Assemble(field,p));
      ComputeDynamicPorePressureRateCpu();const std::vector<float> old(PorePressRatec,PorePressRatec+Np);off.write(reinterpret_cast<const char*>(old.data()),sizeof(float)*Np);
      for(unsigned p=0;p<Np;p++)Require(fabs(double(old[p])-ref[p].old)<=ref[p].oldlimit,"Default-OFF rate differs from retained independent reference");
      #ifndef UPL_FREE_SEEPAGE_LEGACY_ONLY
        Policy(true);ComputeDynamicPorePressureRateCpu();
        for(unsigned p=0;p<Np;p++){
          const auto& r=ref[p];const bool surfacep=Surface(p);const double expected=surfacep?r.raw:r.old,error=fabs(double(PorePressRatec[p])-expected),limit=surfacep?r.limit:r.oldlimit;
          Require(std::isfinite(PorePressRatec[p])&&error<=limit,"Free-seepage rate differs from independent potential reference");
          if(!surfacep){Require(!memcmp(&old[p],PorePressRatec+p,sizeof(float)),"Interior rate changed bits when free policy enabled");InnerRows++;}
          else{SurfaceRows++;if(field==0){Require(fabs(double(PorePressRatec[p]))<=r.limit,"Hydrostatic surface generated false flow");MaxHydroRatio=(std::max)(MaxHydroRatio,fabs(double(PorePressRatec[p]))/r.limit);if(fabs(r.naive)>100*r.limit)NegativeRows++;MaxNaiveRatio=(std::max)(MaxNaiveRatio,fabs(r.naive)/r.limit);}}
          MaxReferenceRatio=(std::max)(MaxReferenceRatio,error/limit);
          out<<field<<','<<Idpc[p]<<','<<FSTypec[p]<<','<<surfacep<<','<<PorePressc[p]<<','<<Acec[p].x<<','<<Acec[p].z<<','<<old[p]<<','<<PorePressRatec[p]<<','<<expected<<','<<limit<<','<<r.oldlimit<<','<<r.head<<','<<r.curvature<<','<<r.continuum<<','<<r.naive<<'\n';RateRows++;
        }
      #else
        for(unsigned p=0;p<Np;p++){out<<field<<','<<Idpc[p]<<','<<FSTypec[p]<<','<<Surface(p)<<','<<old[p]<<','<<ref[p].old<<','<<ref[p].oldlimit<<'\n';RateRows++;}
      #endif
      const auto after=State();Require(before.size()==after.size()&&!memcmp(before.data(),after.data(),before.size()*sizeof(StateRow))&&!memcmp(acceleration.data(),Acec,Np*sizeof(tfloat3)),"Zero-step rate changed native state or supplied acceleration");
      Policy(false);PosInteraction_Forces();NoStep();
    }
  }
  void Projection(std::ostream& out,std::ostream& nonfinite){
    #ifndef UPL_FREE_SEEPAGE_LEGACY_ONLY
      // One fixed corner is only a projection selector canary, not a wall operator fixture.
      Npb=NpbOk=CaseNpb=CaseNfixed=1;CaseNfluid=Count-1;CellTable();Field(0);ComputeFreeSurfaceTracking();
      const std::vector<unsigned> types(FSTypec,FSTypec+Np);unsigned inner=0,surface=0;for(unsigned p=Npb;p<Np;p++)Surface(p)?surface++:inner++;
      Require(inner>0&&surface>=3,"Projection mask has empty interior/surface sign coverage");
      for(unsigned phase=0;phase<4;phase++){
        unsigned signs[3]={};for(unsigned p=0;p<Np;p++){
          const bool sf=Surface(p);const unsigned sign=sf?(signs[0]+signs[1]+signs[2])%3:2;if(sf)signs[sign]++;
          PorePressc[p]=sign==0?-16.f:sign==1?0.f:16.f;PorePressRatec[p]=float(1024+p);
        }
        Require(signs[0]&&signs[1]&&signs[2],"Projection omitted a surface pressure sign");
        auto expected=State();const std::vector<float> rates(PorePressRatec,PorePressRatec+Np);Policy(phase==1||phase==2);HydroMechDrainage=phase==3;HydroMechDrainageStartTime=0;HydroMechDrainageFixedGrid=false;
        if(phase==1){
          // Owned nonnull pointer exercises the existing predicate ONLY; no predictor is run.
          float* dummy=ArraysCpu->ReserveFloat();PorePressPrec=dummy;
          try{ApplyPorePressureBoundaries();}catch(...){ArraysCpu->Free(dummy);PorePressPrec=nullptr;throw;}
          ArraysCpu->Free(dummy);PorePressPrec=nullptr;
        }else ApplyPorePressureBoundaries();
        Require(!memcmp(types.data(),FSTypec,Np*sizeof(unsigned)),"Projection fixture FS mask changed across identical geometry");
        for(unsigned p=0;p<Np;p++){
          const double before=expected[p][7];const bool sf=Surface(p),clip=sf&&(phase==3||(phase==2&&before>0));if(clip)expected[p][7]=0;
          const float rateExpected=phase==3&&sf?0.f:rates[p];Require(PorePressRatec[p]==rateExpected,"Projection changed an unconstrained rate or missed legacy drainage");
          out<<phase<<','<<Idpc[p]<<','<<(p<Npb)<<','<<FSTypec[p]<<','<<before<<','<<PorePressc[p]<<','<<expected[p][7]<<','<<rates[p]<<','<<PorePressRatec[p]<<','<<(phase==1)<<'\n';ProjectionRows++;
        }
        const auto actual=State();Require(!memcmp(expected.data(),actual.data(),Np*sizeof(StateRow)),"Projection altered fixed/interior or nonpressure native state");NoStep();
      }
      Policy(true);HydroMechDrainage=false;
      std::vector<unsigned> chosen;for(unsigned p=Npb;p<Np&&chosen.size()<2;p++)if(Surface(p))chosen.push_back(p);Require(chosen.size()==2,"Missing nonfinite surface canaries");
      for(unsigned p=0;p<Np;p++)PorePressc[p]=-16.f;
      PorePressc[chosen[0]]=std::numeric_limits<float>::infinity();PorePressc[chosen[1]]=std::numeric_limits<float>::quiet_NaN();
      const std::vector<float> pressures(PorePressc,PorePressc+Np),rates(PorePressRatec,PorePressRatec+Np);const auto state=State(true);
      ApplyPorePressureBoundaries();const auto after=State(true);
      Require(!memcmp(pressures.data(),PorePressc,Np*sizeof(float))&&!memcmp(rates.data(),PorePressRatec,Np*sizeof(float))&&!memcmp(state.data(),after.data(),Np*sizeof(StateRow)),"Projection repaired a nonfinite pressure or changed other state");
      for(unsigned i=0;i<2;i++){const unsigned p=chosen[i];unsigned beforeBits=0,afterBits=0;static_assert(sizeof(unsigned)==sizeof(float),"Expected binary32 bit container");memcpy(&beforeBits,&pressures[p],sizeof(float));memcpy(&afterBits,PorePressc+p,sizeof(float));nonfinite<<Idpc[p]<<','<<(i==0)<<','<<(i==1)<<','<<beforeBits<<','<<afterBits<<'\n';NonfiniteRows++;}
      Policy(false);NoStep();
    #endif
  }
  void Complete(std::ostream& out){
    #ifndef UPL_FREE_SEEPAGE_LEGACY_ONLY
      Require(RateRows==243&&InnerRows>0&&SurfaceRows>0&&NegativeRows>0&&MaxNaiveRatio>100&&ProjectionRows==324&&NonfiniteRows==2,"Declared candidate checks are incomplete");
      const bool legacy=false;
    #else
      Require(RateRows==243&&!ProjectionRows,"Declared legacy-only checks are incomplete");const bool legacy=true;
    #endif
    NoStep();out<<std::setprecision(17)<<"{\"stage\":\"upl_free_seepage_cpu_r1\",\"passed\":true,\"legacy_only\":"<<(legacy?"true":"false")<<",\"rate_rows\":"<<RateRows<<",\"inner_counts\":["<<MaskInner[0]<<','<<MaskInner[1]<<','<<MaskInner[2]<<"],\"surface_counts\":["<<MaskSurface[0]<<','<<MaskSurface[1]<<','<<MaskSurface[2]<<"],\"inner_bit_checks\":"<<InnerRows<<",\"surface_checks\":"<<SurfaceRows<<",\"hydrostatic_naive_negative_witnesses\":"<<NegativeRows<<",\"projection_rows\":"<<ProjectionRows<<",\"nonfinite_input_bits_preserved\":"<<NonfiniteRows<<",\"max_reference_ratio\":"<<MaxReferenceRatio<<",\"max_hydrostatic_ratio\":"<<MaxHydroRatio<<",\"max_naive_hydrostatic_ratio\":"<<MaxNaiveRatio<<",\"completed_physical_steps\":0,\"dummy_pointer_is_actual_integrator\":false,\"nonfinite_inputs_physically_accepted\":false,\"public_scope_admitted\":false,\"physical_acceptance\":false}\n";
  }
};
int main(int argc,char** argv){try{
  Require(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_DIR");const fs::path out(argv[2]);Require(!fs::exists(out),"Existing output protected");
  AppInfo.ConfigRunPaths(argv[0]);AppInfo.ConfigOutput(true,false,out.string(),"data");AppInfo.LogInit((out/"Run.out").string());
  std::ofstream rows(out/"rates.csv"),mask(out/"mask.csv"),projection(out/"projection.csv"),nonfinite(out/"nonfinite_projection.csv"),off(out/"free_off_rates.bin",std::ios::binary);for(auto* f:{&rows,&mask,&projection})*f<<std::setprecision(17);
  #ifndef UPL_FREE_SEEPAGE_LEGACY_ONLY
    rows<<"field,native_id,fstype,surface,p_pa,Ace_x,Ace_z,free_off_rate,free_on_rate,independent_reference,roundoff_limit,old_roundoff_limit,potential_head_sum,curvature_correction,continuum_divergence_rate_descriptive,naive_pressure_defect_removed_rate\n";
  #else
    rows<<"field,native_id,fstype,surface,free_off_rate,independent_reference,roundoff_limit\n";
  #endif
  mask<<"field,native_id,x,z,fstype,posdiv\n";projection<<"phase,native_id,fixed,fstype,before_p,actual_p,expected_p,before_rate,actual_rate,owned_dummy_pre_pointer\n";nonfinite<<"native_id,positive_infinity_input,quiet_NaN_input,bits_before,bits_after\n";
  Seepage test;test.Rates(rows,mask,off);test.Projection(projection,nonfinite);for(auto* f:{&rows,&mask,&projection,&nonfinite,&off}){f->flush();Require(bool(*f),"Fixture output write failed");}
  std::ofstream done(out/"completion.json");test.Complete(done);done.flush();Require(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Free-seepage fixture failed; preserve outputs\n";return 2;}}
