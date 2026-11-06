// Private zero-step GPU rate/projection component, not a JSphGpu time integrator.
#define main RetainedCubicComponentMain
#include "upl_cubic_component_r2.cpp"
#undef main
#include <limits>

class FreeSeepageGpu{
  static constexpr unsigned N=81,Cap=N+2;
  static constexpr double Dp=.25,Rho=2100.,V0=Dp*Dp,Kw=2e8,Rhow=1000.;
  static constexpr float Sentinel=1234567.f;
  const double Solid=1.-double(float(.3)),K=double(float(1e-5));
  StCteSph sph=CteSphNull();StCteInteraction ct={};StDivDataGpu dvd;
  Device<int2> cellg{4};Device<unsigned> dcg{Cap},fsg{Cap},invalidg{2};Device<typecode> codeg{Cap};
  Device<double2> xyg{Cap};Device<double> zg{Cap},jg{Cap},thetag{Cap};Device<float4> posg{Cap},velg{Cap};
  Device<float> pg{Cap},rateg{Cap},divg{Cap};Device<tmatrix3d> cg{Cap};Device<float3> aceg{Cap},normalg{Cap};
  std::vector<double2> xy=std::vector<double2>(Cap);std::vector<double> z=std::vector<double>(Cap),j=std::vector<double>(Cap,1.),theta=std::vector<double>(Cap);
  std::vector<float> p=std::vector<float>(Cap),posdiv;std::vector<float4> packed=std::vector<float4>(Cap),vel=std::vector<float4>(Cap);
  std::vector<float3> ace=std::vector<float3>(Cap),normal;std::vector<tmatrix3d> c;std::vector<unsigned> types;
  std::vector<typecode> code=std::vector<typecode>(Cap,CODE_TYPE_FIXED);
  unsigned rateRows=0,innerRows=0,surfaceRows=0,negativeRows=0,projectionRows=0,nonfiniteRows=0;
  unsigned maskInner[3]={},maskSurface[3]={};double maxReference=0,maxHydro=0,maxNaive=0;
  struct Reference{double raw=0,old=0,naive=0,limit=0,oldlimit=0,head=0,curvature=0,continuum=0;};
  tdouble3 Pos(unsigned i)const{return TDouble3(xy[i].x,0,z[i]);}
  bool Surface(unsigned i)const{return CODE_IsFluid(code[i])&&(types[i]==FST_FreeSurface||types[i]==FST_Isolated);}
  tdouble3 Acceleration(unsigned field,unsigned i)const{
    if(!field)return TDouble3(0,0,1./16.);const auto u=Pos(i)-TDouble3(1,0,1);
    return TDouble3(1./32.,0,1./16.)+(field==2?TDouble3(u.x/16.+u.z/32.,0,u.x/32.-u.z/32.):TDouble3(0));
  }
  double Potential(unsigned field,unsigned i)const{
    if(!field)return Pos(i).z/16.;const auto u=Pos(i)-TDouble3(1,0,1);
    return u.x/32.+u.z/16.+(field==2?u.x*u.x/32.+u.x*u.z/32.-u.z*u.z/64.:0.);
  }
  void Field(unsigned field){
    for(unsigned i=0;i<N;i++){const auto u=Pos(i)-TDouble3(1,0,1);const double value=!field?128.-Rhow*Pos(i).z/16.:128.+16*u.x-32*u.z;
      Need(fabs(value)<=256&&double(float(value))==value,"Manufactured pressure is not exact binary32 at retained256 scale");p[i]=float(value);const auto a=Acceleration(field,i);ace[i]=make_float3(float(a.x),0,float(a.z));
      Need(Vec(ace[i]).x==a.x&&Vec(ace[i]).z==a.z,"Manufactured acceleration is not exact binary32");}
    Up(pg.p,p);Up(aceg.p,ace);
  }
  void Geometry(unsigned fixed){
    Need(fixed<=1,"Only a projection fixed-corner canary is admitted");ct.nbound=fixed;cusph::CteInteractionUp(&ct);
    for(unsigned i=0;i<Cap;i++)code[i]=(i>=fixed&&i<N?CODE_TYPE_FLUID:CODE_TYPE_FIXED);Up(codeg.p,code);
    Up(cellg.p,std::vector<int2>{make_int2(0,fixed),make_int2(0,0),make_int2(fixed,N),make_int2(0,0)});
    // One legitimate4m cell covers the unchanged0..2 geometry; kernels retain actual radius cutoffs.
    dvd=MakeDivDataGpu(1,TUint3(1,1,1),TUint3(0),cellg.p,4,ct.cellcode,TDouble3(0),sph.kernelsize2,4);
  }
  void Tracking(unsigned fixed){
    Up(fsg.p,std::vector<unsigned>(Cap,0x1234abcd));Up(divg.p,std::vector<float>(Cap,Sentinel));
    Up(cg.p,std::vector<tmatrix3d>(Cap,TMatrix3d(0)));Up(normalg.p,std::vector<float3>(Cap,make_float3(0,0,0)));
    cusph::ComputeFreeSurfaceTracking(KERNEL_Cubic,true,N,fixed,dvd,dcg.p,posg.p,velg.p,codeg.p,cg.p,fsg.p,normalg.p,divg.p,false,jg.p);Cu(cudaDeviceSynchronize());
    types=Down(fsg.p,Cap);posdiv=Down(divg.p,Cap);c=Down(cg.p,Cap);normal=Down(normalg.p,Cap);
    Need(types[N]==0x1234abcd&&types[N+1]==0x1234abcd&&posdiv[N]==Sentinel&&posdiv[N+1]==Sentinel,"Actual FS tail canary changed");
  }
  Reference Assemble(unsigned field,unsigned i)const{
    Reference r;const double scale=Kw/(1.-Solid/j[i])*K/(Rhow*9.80665);double lp=0,da=0,lpabs=0,daabs=0;tdouble3 gp=TDouble3(0),lx=TDouble3(0);
    // Independent total-potential differences plus explicit quadratic curvature, not a copied cell walker.
    for(unsigned q=0;q<N;q++){const auto d=Pos(i)-Pos(q);const double rr=Dot(d,d);if(rr>double(sph.kernelsize2)||rr<ALMOSTZERO)continue;
      const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Cubic>(sph,float(rr))),gi=Mul(c[i],g),gq=Mul(c[q],g);const double v=V0*j[q],w=v*Dot(d,gi+gq)/(rr+double(sph.eta2)),dp=double(p[i])-p[q];
      const double dh=dp+Rhow*(Potential(field,i)-Potential(field,q)),db=field==2?d.x*d.x/16.+d.x*d.z/16.-d.z*d.z/32.:0.;
      const auto delta=Vec(ace[q])-Vec(ace[i]);const double divergence=v*Dot(delta,gi);r.head+=w*dh;r.curvature+=Rhow*(.5*w*db+divergence);
      lp+=w*dp;lx=lx+d*w;gp=gp-gi*(v*dp);da+=divergence;lpabs+=fabs(w*dp);daabs+=v*(fabs(delta.x*gi.x)+fabs(delta.z*gi.z));}
    r.raw=scale*(r.head+r.curvature);r.old=scale*(lp-Dot(gp,lx)+Rhow*da);r.naive=scale*(lp+Rhow*da);r.continuum=field==2?scale*Rhow*(1./16.-1./32.):0.;
    const double base=32*FLT_EPSILON+4096*DBL_EPSILON;
    r.oldlimit=base*(std::max)(1.,scale*(lpabs+fabs(gp.x*lx.x)+fabs(gp.y*lx.y)+fabs(gp.z*lx.z)+Rhow*daabs));
    r.limit=base*(std::max)(1.,scale*(lpabs+Rhow*(fabs(double(ace[i].x)*lx.x)+fabs(double(ace[i].z)*lx.z)+daabs)));return r;
  }
  std::vector<float> Rate(bool free){
    Up(invalidg.p,std::vector<unsigned>{N,0x1234abcd});Up(rateg.p,std::vector<float>(Cap,Sentinel));
    #ifndef UPL_FREE_SEEPAGE_LEGACY_ONLY
      cusph::ComputeDynamicPorePressureRate(N,0,dvd,dcg.p,xyg.p,zg.p,codeg.p,cg.p,aceg.p,jg.p,thetag.p,pg.p,rateg.p,Solid,Kw,Rhow,K,Rhow*9.80665,V0,invalidg.p,false,0.,nullptr,false,nullptr,fsg.p,normalg.p,false,false,HMLOAD_None,TDouble3(0),0.,KERNEL_Cubic,free);
    #else
      Need(!free,"Old closure cannot select the new policy");
      cusph::ComputeDynamicPorePressureRate(N,0,dvd,dcg.p,xyg.p,zg.p,codeg.p,cg.p,aceg.p,jg.p,thetag.p,pg.p,rateg.p,Solid,Kw,Rhow,K,Rhow*9.80665,V0,invalidg.p,false,0.,nullptr,false,nullptr,fsg.p,normalg.p,false,false,HMLOAD_None,TDouble3(0),0.,KERNEL_Cubic);
    #endif
    Cu(cudaDeviceSynchronize());Need(Down(invalidg.p,2)==std::vector<unsigned>({N,0x1234abcd}),"Actual rate wrapper rejected the finite field");
    const auto result=Down(rateg.p,Cap);Need(result[N]==Sentinel&&result[N+1]==Sentinel,"Actual rate tail canary changed");return result;
  }
  void InputsUnchanged()const{
    Need(Same(xy,Down(xyg.p,Cap))&&Same(z,Down(zg.p,Cap))&&Same(packed,Down(posg.p,Cap))&&Same(vel,Down(velg.p,Cap))&&Same(code,Down(codeg.p,Cap))
      &&Same(j,Down(jg.p,Cap))&&Same(theta,Down(thetag.p,Cap))&&Same(p,Down(pg.p,Cap))&&Same(ace,Down(aceg.p,Cap))&&Same(c,Down(cg.p,Cap))
      &&Same(types,Down(fsg.p,Cap))&&Same(normal,Down(normalg.p,Cap))&&Same(posdiv,Down(divg.p,Cap)),"Zero-step rate/projection changed a protected input");
  }
public:
  FreeSeepageGpu(){
    const float h=float(1.2*Dp);sph.simulate2d=true;sph.tkernel=KERNEL_Cubic;sph.dp=Dp;sph.kernelh=h;sph.kernelsize=2*h;sph.kernelsize2=sph.kernelsize*sph.kernelsize;sph.eta2=.01f*h*h;sph.kcubic=fsph::GetKernelCubic_Ctes(true,h);
    ct.simulate2d=1;ct.kernelh=h;ct.kernelsize=sph.kernelsize;ct.kernelsize2=sph.kernelsize2;ct.eta2=sph.eta2;ct.poscellsize=ct.scell=4;ct.dp=float(Dp);ct.rhopzero=float(Rho);ct.massf=ct.massb=float(Rho*V0);ct.gamma=7;ct.cs0=40;
    ct.axis=MGDIV_Z;ct.cellcode=DCEL_GetCode(1,1,1);ct.tboundary=BC_DBC;ct.slipmode=SLIP_Vel0;ct.hydromech=1;ct.porewaterbulkmodulus=float(Kw);ct.porewaterrho=float(Rhow);ct.porosity=.3f;ct.porekwn=float(Kw/double(.3f));ct.porecompgradcorr=ct.soilstressrategradcorr=1;ct.gravityz=-1./16.;
    const auto kc=sph.kcubic;ct.cubic_a1=kc.a1;ct.cubic_a2=kc.a2;ct.cubic_aa=kc.aa;ct.cubic_a24=kc.a24;ct.cubic_c1=kc.c1;ct.cubic_d1=kc.d1;ct.cubic_c2=kc.c2;ct.cubic_odwdeltap=kc.od_wdeltap;
    for(unsigned i=0;i<N;i++){xy[i]=make_double2(double(i%9)*Dp,0);z[i]=double(i/9)*Dp;packed[i]=make_float4(float(xy[i].x),0,float(z[i]),0);vel[i]=make_float4(0,0,0,float(Rho));}
    Up(xyg.p,xy);Up(zg.p,z);Up(posg.p,packed);Up(velg.p,vel);Up(jg.p,j);Up(thetag.p,theta);Up(dcg.p,std::vector<unsigned>(Cap,0));Geometry(0);
  }
  void Rates(std::ostream& rows,std::ostream& masks,std::ostream& off){
    for(unsigned field=0;field<3;field++){Field(field);Tracking(0);unsigned inner=0,surface=0;
      for(unsigned i=0;i<N;i++){Surface(i)?surface++:inner++;masks<<field<<','<<i<<','<<xy[i].x<<','<<z[i]<<','<<types[i]<<','<<posdiv[i]<<'\n';}
      Need(inner>0&&surface>0,"Actual GPU FS mask lacks interior/truncated coverage");maskInner[field]=inner;maskSurface[field]=surface;
      std::vector<Reference> reference;for(unsigned i=0;i<N;i++)reference.push_back(Assemble(field,i));const auto old=Rate(false);off.write(reinterpret_cast<const char*>(old.data()),N*sizeof(float));
      for(unsigned i=0;i<N;i++)Need(std::isfinite(old[i])&&fabs(double(old[i])-reference[i].old)<=reference[i].oldlimit,"GPU OFF rate differs from independent old reference");InputsUnchanged();
      #ifndef UPL_FREE_SEEPAGE_LEGACY_ONLY
        const auto actual=Rate(true);for(unsigned i=0;i<N;i++){const auto& r=reference[i];const bool sf=Surface(i);const double expected=sf?r.raw:r.old,limit=sf?r.limit:r.oldlimit,error=fabs(double(actual[i])-expected);
          Need(std::isfinite(actual[i])&&error<=limit,"GPU free rate differs from independent potential/curvature reference");maxReference=(std::max)(maxReference,error/limit);
          if(!sf){Need(!memcmp(&actual[i],&old[i],sizeof(float)),"GPU interior changed rate bits under free policy");innerRows++;}
          else{surfaceRows++;if(field==0){Need(fabs(double(actual[i]))<=r.limit,"GPU hydrostatic surface has false flow");maxHydro=(std::max)(maxHydro,fabs(double(actual[i]))/r.limit);negativeRows+=unsigned(fabs(r.naive)>100*r.limit);maxNaive=(std::max)(maxNaive,fabs(r.naive)/r.limit);}}
          rows<<field<<','<<i<<','<<types[i]<<','<<sf<<','<<p[i]<<','<<ace[i].x<<','<<ace[i].z<<','<<old[i]<<','<<actual[i]<<','<<expected<<','<<limit<<','<<r.oldlimit<<','<<r.head<<','<<r.curvature<<','<<r.continuum<<','<<r.naive<<'\n';rateRows++;}InputsUnchanged();
      #else
        for(unsigned i=0;i<N;i++){rows<<field<<','<<i<<','<<types[i]<<','<<Surface(i)<<','<<old[i]<<','<<reference[i].old<<','<<reference[i].oldlimit<<'\n';rateRows++;}
      #endif
    }
  }
  void Projection(std::ostream& rows,std::ostream& nonfinite){
    #ifndef UPL_FREE_SEEPAGE_LEGACY_ONLY
      Geometry(1);Tracking(1);std::vector<unsigned> selected;for(unsigned i=1;i<N;i++)if(Surface(i))selected.push_back(i);Need(selected.size()>=4,"Projection surface lacks sign coverage");
      for(unsigned phase:{0u,2u,3u}){unsigned signs[4]={};std::vector<float> rates(Cap,Sentinel);
        for(unsigned i=0;i<N;i++){const unsigned sign=Surface(i)?unsigned(std::find(selected.begin(),selected.end(),i)-selected.begin())%4:3;signs[sign]+=Surface(i);p[i]=sign==0?-16.f:sign==1?0.f:sign==2?-0.f:16.f;rates[i]=float(1024+i);}
        Need(signs[0]&&signs[1]&&signs[2]&&signs[3],"Projection omitted signed-zero/pressure sign witness");const auto before=p;auto expected=p;auto expectedRates=rates;
        for(unsigned i=1;i<N;i++)if(Surface(i)&&(phase==3||(phase==2&&std::isfinite(p[i])&&p[i]>0))){expected[i]=0.f;if(phase==3)expectedRates[i]=0.f;}
        Up(pg.p,p);Up(rateg.p,rates);cusph::ApplyFreeSurfacePorePressure(N,1,phase==3,HMLOAD_None,xyg.p,codeg.p,fsg.p,pg.p,rateg.p,phase==2);Cu(cudaDeviceSynchronize());
        const auto actual=Down(pg.p,Cap);const auto actualRates=Down(rateg.p,Cap);Need(Same(expected,actual)&&Same(expectedRates,actualRates),"GPU projection finite value/rate/fixed/tail semantics differ");
        p=actual;InputsUnchanged();for(unsigned i=0;i<N;i++){unsigned b=0,a=0;memcpy(&b,&before[i],4);memcpy(&a,&actual[i],4);rows<<phase<<','<<i<<','<<(i==0)<<','<<types[i]<<','<<before[i]<<','<<actual[i]<<','<<expected[i]<<','<<rates[i]<<','<<actualRates[i]<<','<<b<<','<<a<<'\n';projectionRows++;}
      }
      std::fill(p.begin(),p.end(),-16.f);p[selected[0]]=std::numeric_limits<float>::infinity();p[selected[1]]=std::numeric_limits<float>::quiet_NaN();const auto before=p;const std::vector<float> rates(Cap,Sentinel);
      Up(pg.p,p);Up(rateg.p,rates);cusph::ApplyFreeSurfacePorePressure(N,1,false,HMLOAD_None,xyg.p,codeg.p,fsg.p,pg.p,rateg.p,true);Cu(cudaDeviceSynchronize());
      const auto actual=Down(pg.p,Cap);Need(Same(before,actual)&&Same(rates,Down(rateg.p,Cap)),"GPU projection repaired a nonfinite input or changed rate");p=actual;InputsUnchanged();
      for(unsigned k=0;k<2;k++){const unsigned i=selected[k];unsigned b=0,a=0;memcpy(&b,&before[i],4);memcpy(&a,&actual[i],4);nonfinite<<i<<','<<(k==0)<<','<<(k==1)<<','<<b<<','<<a<<'\n';nonfiniteRows++;}
    #endif
  }
  void Complete(std::ostream& out){
    #ifndef UPL_FREE_SEEPAGE_LEGACY_ONLY
      Need(rateRows==243&&innerRows>0&&surfaceRows>0&&negativeRows>0&&maxNaive>100&&projectionRows==243&&nonfiniteRows==2,"GPU declared checks incomplete");const bool legacy=false;
    #else
      Need(rateRows==243&&!projectionRows&&!nonfiniteRows,"GPU legacy-only declared checks incomplete");const bool legacy=true;
    #endif
    out<<std::setprecision(17)<<"{\"stage\":\"upl_free_seepage_gpu_r1\",\"passed\":true,\"legacy_only\":"<<(legacy?"true":"false")<<",\"rate_rows\":"<<rateRows<<",\"inner_counts\":["<<maskInner[0]<<','<<maskInner[1]<<','<<maskInner[2]<<"],\"surface_counts\":["<<maskSurface[0]<<','<<maskSurface[1]<<','<<maskSurface[2]<<"],\"inner_bit_checks\":"<<innerRows<<",\"surface_checks\":"<<surfaceRows<<",\"hydrostatic_naive_negative_witnesses\":"<<negativeRows<<",\"projection_rows\":"<<projectionRows<<",\"nonfinite_input_bits_preserved\":"<<nonfiniteRows<<",\"max_reference_ratio\":"<<maxReference<<",\"max_hydrostatic_ratio\":"<<maxHydro<<",\"max_naive_hydrostatic_ratio\":"<<maxNaive<<",\"completed_physical_steps\":0,\"actual_GPU_FS_rate_projection_wrappers\":true,\"CPU_production_called\":false,\"same_ID_CPU_result_assumed\":false,\"host_full_only_projection_timing_proven\":false,\"nonfinite_inputs_physically_accepted\":false,\"physical_acceptance\":false}\n";
  }
};
int main(int argc,char** argv){try{
  Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_OUTPUT_DIRECTORY");const fs::path out=argv[2];Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh output/existing parent required");fs::create_directory(out);Cu(cudaSetDevice(0));
  std::ofstream rows(out/"rates.csv"),mask(out/"mask.csv"),projection(out/"projection.csv"),nonfinite(out/"nonfinite_projection.csv"),off(out/"free_off_rates.bin",std::ios::binary);for(auto* f:{&rows,&mask,&projection})*f<<std::setprecision(17);
  #ifndef UPL_FREE_SEEPAGE_LEGACY_ONLY
    rows<<"field,native_id,fstype,surface,p_pa,Ace_x,Ace_z,free_off_rate,free_on_rate,independent_reference,roundoff_limit,old_roundoff_limit,potential_head_sum,curvature_correction,continuum_divergence_rate_descriptive,naive_pressure_defect_removed_rate\n";
  #else
    rows<<"field,native_id,fstype,surface,free_off_rate,independent_reference,roundoff_limit\n";
  #endif
  mask<<"field,native_id,x,z,fstype,posdiv\n";projection<<"device_phase,native_id,fixed,fstype,before_p,actual_p,expected_p,before_rate,actual_rate,bits_before,bits_after\n";nonfinite<<"native_id,positive_infinity_input,quiet_NaN_input,bits_before,bits_after\n";
  {FreeSeepageGpu test;test.Rates(rows,mask,off);test.Projection(projection,nonfinite);for(auto* f:{&rows,&mask,&projection,&nonfinite,&off}){f->flush();Need(bool(*f),"GPU fixture output write failed");}std::ofstream done(out/"completion.json");test.Complete(done);done.flush();Need(bool(done),"GPU completion write failed");}
  Cu(cudaDeviceSynchronize());return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}}
