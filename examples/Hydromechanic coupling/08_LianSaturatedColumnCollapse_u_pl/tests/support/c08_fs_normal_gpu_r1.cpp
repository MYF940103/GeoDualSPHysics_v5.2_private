// Private zero-step GPU FS operator controls; no force, integration or source modification.
#define main RetainedCubicComponentMain
#include "upl_cubic_component_r2.cpp"
#undef main
#include <sstream>

static tdouble3 GAbs(tdouble3 a){return TDouble3(fabs(a.x),fabs(a.y),fabs(a.z));}
static double GAbsDot(tdouble3 a,tdouble3 b){return fabs(a.x*b.x)+fabs(a.y*b.y)+fabs(a.z*b.z);}
static unsigned GBits(float a){unsigned b=0;static_assert(sizeof(a)==sizeof(b),"Need binary32 bits");memcpy(&b,&a,sizeof(b));return b;}
static tdouble3 GTangent(tdouble3 a,tdouble3 n){const double nn=Dot(n,n);Need(std::isfinite(nn)&&nn>0,"Invalid actual GPU FS normal");return a-n*(Dot(n,a)/nn);}

class FsNormalGpu{
  static constexpr unsigned N=81,Cap=N+2,Canary=0x1234abcd;
  static constexpr double Dp=.04,Rho0=2072.5,Rhow=1000.,Kw=1e9,Ck=2.;
  static constexpr float Sentinel=1234567.f;
  enum Field{Hydro,NonconstantAce,Chain,AffineTangent,Constant};
  struct Ref{double rate=0,limit=0,quant=0,lp=0,lap=0,da=0,chain=0,scale=0;tdouble3 lx=TDouble3(0),gp=TDouble3(0),gradj=TDouble3(0),corr=TDouble3(0);};
  const unsigned Profile;const bool Raw;
  const float Mass=float(Rho0*Dp*Dp),N0=.35f,K0=.0002f,Gz=-9.81f;
  const double Solid=1.-double(N0),V0=double(Mass)/Rho0;
  StCteSph sph=CteSphNull();StCteInteraction ct={};StDivDataGpu dvd;
  Device<int2> cells{4};Device<unsigned> dcg{Cap},fsg{Cap},invalidg{2};Device<typecode> codeg{Cap};
  Device<double2> xyg{Cap};Device<double> zg{Cap},jg{Cap},thetag{Cap};
  Device<float4> packedg{Cap},velg{Cap};Device<float3> aceg{Cap},normalg{Cap};
  Device<float> pg{Cap},rateg{Cap},divg{Cap};Device<tmatrix3d> cg{Cap};
  std::vector<double2> xy=std::vector<double2>(Cap);std::vector<double> z=std::vector<double>(Cap),j=std::vector<double>(Cap,1.),theta=std::vector<double>(Cap);
  std::vector<float4> packed=std::vector<float4>(Cap),vel=std::vector<float4>(Cap);
  std::vector<float3> ace=std::vector<float3>(Cap),normal;
  std::vector<float> p=std::vector<float>(Cap),posdiv;
  std::vector<typecode> code=std::vector<typecode>(Cap,CODE_TYPE_FIXED);
  std::vector<unsigned> types;std::vector<tmatrix3d> c;
  unsigned Rows=0,InteriorBits=0,ChainWitnesses=0,SurfaceRows=0,InnerCount=0,SurfaceCount=0,ProjectionChecks=0;
  double MaxReferenceRatio=0,MaxHydroRatio=0,MaxChainRatio=0;
  int Ix(unsigned i)const{return int(i%9)-4;}
  int Iz(unsigned i)const{return int(i/9)-4;}
  tdouble3 Pos(unsigned i)const{return TDouble3(xy[i].x,xy[i].y,z[i]);}
  bool Surface(unsigned i)const{return CODE_IsNormal(code[i])&&CODE_IsFluid(code[i])&&(types[i]==FST_FreeSurface||types[i]==FST_Isolated);}
  double HydroIdeal(unsigned i)const{return -4096.+Rhow*double(Gz)*(z[i]-1.);}
  double K(unsigned i)const{return j[i]==1.?double(K0):double(K0)*exp((j[i]-1.)/(Solid*Ck));}
  void SetField(Field field){
    for(unsigned i=0;i<N;i++){
      double pressure=-16.;tdouble3 a=TDouble3(0);
      if(field==Hydro){pressure=HydroIdeal(i);a=TDouble3(0,0,-double(Gz));}
      if(field==NonconstantAce){pressure+=Ix(i)/8.+Iz(i)/16.;a=TDouble3(Ix(i)/128.+Iz(i)/256.,0,Ix(i)/256.-Iz(i)/128.);}
      if(field==Chain)pressure+=Ix(i)/4.+Iz(i)/8.;
      if(field==AffineTangent)pressure+=Ix(i)/4.;
      Need(std::isfinite(pressure)&&pressure<0,"Manufactured pressure must be strictly negative");
      if(field!=Hydro)Need(double(float(pressure))==pressure,"Nonhydro pressure must be exact binary32");
      p[i]=float(pressure);ace[i]=make_float3(float(a.x),float(a.y),float(a.z));
      Need(Vec(ace[i]).x==a.x&&Vec(ace[i]).y==a.y&&Vec(ace[i]).z==a.z,"Prescribed acceleration must be exact binary32");
    }
    Up(pg.p,p);Up(aceg.p,ace);
  }
  void Tracking(){
    std::vector<unsigned> fs0(Cap,Canary);std::vector<float> div0(Cap,Sentinel);
    std::vector<tmatrix3d> c0(Cap,TMatrix3d(0));std::vector<float3> n0(Cap,make_float3(0,0,0));
    for(unsigned i=N;i<Cap;i++){c0[i]=TMatrix3d(777.);n0[i]=make_float3(123,456,789);}
    Up(fsg.p,fs0);Up(divg.p,div0);Up(cg.p,c0);Up(normalg.p,n0);
    // Nonnull jg selects the production porosity-feedback volumes, not rho-cache quadrature.
    cusph::ComputeFreeSurfaceTracking(KERNEL_Wendland,true,N,0,dvd,dcg.p,packedg.p,velg.p,codeg.p,cg.p,fsg.p,normalg.p,divg.p,false,jg.p);
    Cu(cudaDeviceSynchronize());types=Down(fsg.p,Cap);posdiv=Down(divg.p,Cap);c=Down(cg.p,Cap);normal=Down(normalg.p,Cap);
    for(unsigned i=N;i<Cap;i++)Need(types[i]==fs0[i]&&GBits(posdiv[i])==GBits(div0[i])&&!memcmp(&c[i],&c0[i],sizeof(tmatrix3d))&&!memcmp(&normal[i],&n0[i],sizeof(float3)),"GPU tracking changed a tail canary");
    for(unsigned i=0;i<N;i++){Surface(i)?SurfaceCount++:InnerCount++;const auto m=c[i];
      const double values[]={m.a11,m.a12,m.a13,m.a21,m.a22,m.a23,m.a31,m.a32,m.a33,normal[i].x,normal[i].y,normal[i].z,posdiv[i]};
      for(double value:values)Need(std::isfinite(value),"GPU tracking produced nonfinite C/normal/posdiv");
      if(Surface(i))Need(Dot(Vec(normal[i]),Vec(normal[i]))>0,"Actual FS normal has zero norm");
    }
    Need(InnerCount>0&&SurfaceCount>0&&Surface(76),"Own GPU tracking lacks actual interior/FS/top-ID76 coverage");
  }
  void InputsUnchanged()const{
    Need(Same(xy,Down(xyg.p,Cap))&&Same(z,Down(zg.p,Cap))&&Same(packed,Down(packedg.p,Cap))&&Same(vel,Down(velg.p,Cap))
      &&Same(code,Down(codeg.p,Cap))&&Same(j,Down(jg.p,Cap))&&Same(theta,Down(thetag.p,Cap))&&Same(p,Down(pg.p,Cap))&&Same(ace,Down(aceg.p,Cap))
      &&Same(c,Down(cg.p,Cap))&&Same(types,Down(fsg.p,Cap))&&Same(normal,Down(normalg.p,Cap))&&Same(posdiv,Down(divg.p,Cap)),"Zero-step wrapper changed a protected native/tail input");
    Need(Same(std::vector<unsigned>(Cap,0),Down(dcg.p,Cap))&&Same(std::vector<int2>{make_int2(0,0),make_int2(0,0),make_int2(0,N),make_int2(0,0)},Down(cells.p,4)),"Zero-step wrapper changed cell inputs");
  }
  Ref Assemble(Field field,unsigned i,bool on)const{
    Ref r;const double ki=K(i),dk=ki/(Solid*Ck),n=1.-Solid/j[i];r.scale=Kw/n/(Rhow*9.80665);
    double lpabs=0,daabs=0,lpq=0;tdouble3 gpq=TDouble3(0);const auto ai=Vec(ace[i]);
    // Independent all-particle search, using actual downloaded GPU C/J/normal and double Darcy positions.
    for(unsigned q=0;q<N;q++){
      const auto d=Pos(i)-Pos(q);const double rr=Dot(d,d);if(rr>double(sph.kernelsize2)||rr<ALMOSTZERO)continue;
      const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(sph,float(rr))),gi=Mul(c[i],g),gq=Mul(c[q],g);
      const double v=V0*j[q],w=v*Dot(d,gi+gq)/(rr+double(sph.eta2)),dp=double(p[i])-p[q];const auto da=Vec(ace[q])-ai;
      r.lp+=w*dp;r.lx=r.lx+d*w;r.gp=r.gp-gi*(v*dp);r.da+=v*Dot(da,gi);r.gradj=r.gradj+gi*(v*(j[q]-j[i]));
      lpabs+=fabs(w*dp);daabs+=v*GAbsDot(da,gi);
      if(field==Hydro){const double quant=fabs(double(p[i])-HydroIdeal(i))+fabs(double(p[q])-HydroIdeal(q));lpq+=fabs(w)*quant;gpq=gpq+GAbs(gi)*(v*quant);}
    }
    const bool sf=on&&Surface(i),raw=sf&&Raw,project=sf&&!Raw;const auto nrm=Vec(normal[i]);r.corr=r.gp;
    if(project)r.corr=r.gp-nrm*(Dot(nrm,r.gp+ai*Rhow)/Dot(nrm,nrm));
    r.lap=raw?r.lp+Rhow*(Dot(ai,r.lx)+r.da):r.lp-Dot(r.corr,r.lx)+Rhow*r.da;
    const auto force=r.corr+ai*Rhow;r.chain=dk*Dot(r.gradj,force);r.rate=r.scale*(ki*r.lap+r.chain);
    const double lapabs=lpabs+Rhow*daabs+(raw?Rhow*GAbsDot(ai,r.lx):GAbsDot(r.corr,r.lx));
    const double base=32*FLT_EPSILON+4096*DBL_EPSILON;r.limit=base*(std::max)(1.,r.scale*(ki*lapabs+dk*GAbsDot(r.gradj,force)));
    const auto ql=raw?TDouble3(0):(project?GTangent(r.lx,nrm):r.lx),qj=project?GTangent(r.gradj,nrm):r.gradj;
    r.quant=r.scale*(ki*(lpq+GAbsDot(ql,gpq))+dk*GAbsDot(qj,gpq));return r;
  }
  std::vector<float> Rate(bool on){
    Up(invalidg.p,std::vector<unsigned>{N,Canary});Up(rateg.p,std::vector<float>(Cap,Sentinel));
    cusph::ComputeDynamicPorePressureRate(N,0,dvd,dcg.p,xyg.p,zg.p,codeg.p,cg.p,aceg.p,jg.p,thetag.p,pg.p,rateg.p,
      Solid,Kw,Rhow,double(K0),Rhow*9.80665,V0,invalidg.p,true,Ck,nullptr,false,nullptr,fsg.p,normalg.p,false,false,HMLOAD_None,TDouble3(0),0.,KERNEL_Wendland,on);
    Cu(cudaDeviceSynchronize());Need(Down(invalidg.p,2)==std::vector<unsigned>({N,Canary}),"Actual GPU rate rejected a finite declared field");
    const auto result=Down(rateg.p,Cap);for(unsigned i=N;i<Cap;i++)Need(GBits(result[i])==GBits(Sentinel),"Actual rate changed a tail canary");InputsUnchanged();return result;
  }
  void NegativeProjection(){
    const std::vector<float> rates(Cap,Sentinel);Up(rateg.p,rates);
    cusph::ApplyFreeSurfacePorePressure(N,0,false,HMLOAD_None,xyg.p,codeg.p,fsg.p,pg.p,rateg.p,true);
    Cu(cudaDeviceSynchronize());Need(Same(p,Down(pg.p,Cap))&&Same(rates,Down(rateg.p,Cap)),"Negative-pressure projection changed p or rate bits");InputsUnchanged();ProjectionChecks++;
  }
public:
  FsNormalGpu(unsigned profile,bool raw):Profile(profile),Raw(raw){
    Need(Profile<2,"Unknown fixed J profile");const float h=.072f;
    sph.simulate2d=true;sph.tkernel=KERNEL_Wendland;sph.dp=Dp;sph.massfluid=Mass;sph.massbound=Mass;sph.rhopzero=float(Rho0);
    sph.kernelh=h;sph.kernelsize=2*h;sph.kernelsize2=sph.kernelsize*sph.kernelsize;sph.eta2=.01f*h*h;sph.kwend=fsph::GetKernelWendland_Ctes(true,h);
    ct.simulate2d=1;ct.nbound=0;ct.massf=ct.massb=Mass;ct.rhopzero=float(Rho0);ct.ovrhopzero=1.f/float(Rho0);ct.dp=float(Dp);
    ct.kernelh=h;ct.kernelsize=sph.kernelsize;ct.kernelsize2=sph.kernelsize2;ct.eta2=sph.eta2;ct.awen=sph.kwend.awen;ct.bwen=sph.kwend.bwen;
    ct.poscellsize=ct.scell=4.f;ct.cellcode=DCEL_GetCode(1,1,1);ct.axis=MGDIV_Z;ct.tboundary=BC_DBC;ct.slipmode=SLIP_Vel0;ct.periactive=0;
    ct.gamma=7.f;ct.cs0=40.f;ct.hydromech=1;ct.porewaterbulkmodulus=float(Kw);ct.porewaterrho=float(Rhow);ct.porosity=N0;
    ct.hydraulicconductivity=K0;ct.porekwn=float(Kw/double(N0));ct.poreghyd=9.80665f;ct.porecompgradcorr=ct.soilstressrategradcorr=1;ct.gravityz=Gz;
    for(unsigned i=0;i<N;i++){
      xy[i]=make_double2(1+Ix(i)*Dp+(Iz(i)<4?Dp/8:0),0);z[i]=1+Iz(i)*Dp;
      j[i]=Profile?1.+double(Ix(i)+2*Iz(i))/512.:1.;const double n=1.-Solid/j[i],rho=Rhow+(Rho0-Rhow)/j[i];
      Need(n>0&&n<1&&V0*j[i]>0&&std::isfinite(rho)&&rho>0&&std::isfinite(K(i))&&K(i)>0,"Invalid prescribed J/n/V/rho/k ledger");
      vel[i]=make_float4(0,0,0,float(rho));packed[i]=make_float4(float(xy[i].x),0,float(z[i]),0);code[i]=CODE_TYPE_FLUID;
      Need(xy[i].x>=0&&xy[i].x<4&&z[i]>=0&&z[i]<4,"Point outside legitimate one-cell position packing");
    }
    for(unsigned i=N;i<Cap;i++){xy[i]=make_double2(2.+i,3.+i);z[i]=4.+i;j[i]=9.+i;theta[i]=10.+i;p[i]=-999.f;ace[i]=make_float3(11,12,13);packed[i]=make_float4(21,22,23,0);vel[i]=make_float4(31,32,33,34);}
    cusph::CteInteractionUp(&ct);Up(xyg.p,xy);Up(zg.p,z);Up(packedg.p,packed);Up(velg.p,vel);Up(jg.p,j);Up(thetag.p,theta);Up(codeg.p,code);Up(pg.p,p);Up(aceg.p,ace);
    Up(dcg.p,std::vector<unsigned>(Cap,0));Up(cells.p,std::vector<int2>{make_int2(0,0),make_int2(0,0),make_int2(0,N),make_int2(0,0)});
    // A real4m cell contains every native point; empty boundary group and actual kernel radius cutoffs remain.
    dvd=MakeDivDataGpu(1,TUint3(1,1,1),TUint3(0),cells.p,4.f,ct.cellcode,TDouble3(0),sph.kernelsize2,4.f);
    Tracking();InputsUnchanged();
  }
  void Run(std::ostream& controls,std::ostream& nodes,std::ostream& offbytes){
    for(unsigned i=0;i<N;i++){const double n=1.-Solid/j[i],v=V0*j[i],rho=Rhow+(Rho0-Rhow)/j[i];const auto a=c[i];const auto nr=normal[i];
      nodes<<Profile<<','<<i<<','<<xy[i].x<<",0,"<<z[i]<<','<<types[i]<<','<<nr.x<<','<<nr.y<<','<<nr.z<<','<<posdiv[i]<<','<<j[i]<<','<<n<<','<<v<<','<<rho<<','<<vel[i].w<<','<<K(i)<<','<<v*n/Kw<<','<<a.a11<<','<<a.a13<<','<<a.a31<<','<<a.a33<<'\n';}
    for(unsigned field=0;field<5;field++){
      const auto f=Field(field);SetField(f);NegativeProjection();std::vector<Ref> refs[2];
      for(unsigned on=0;on<2;on++)for(unsigned i=0;i<N;i++)refs[on].push_back(Assemble(f,i,on!=0));
      const auto off=Rate(false),on=Rate(true);offbytes.write(reinterpret_cast<const char*>(off.data()),N*sizeof(float));
      for(unsigned i=0;i<N;i++){
        if(!Surface(i)){Need(GBits(off[i])==GBits(on[i]),"GPU interior OFF/ON rate bits differ");InteriorBits++;}else SurfaceRows++;
        for(unsigned enabled=0;enabled<2;enabled++){
          const auto& r=refs[enabled][i];const float actual=(enabled?on:off)[i];const double error=fabs(double(actual)-r.rate);
          Need(std::isfinite(actual)&&error<=r.limit,"Actual GPU rate differs from independent expected formula");MaxReferenceRatio=(std::max)(MaxReferenceRatio,error/r.limit);
          if(f==Hydro){const double limit=2*r.limit+r.quant;Need(fabs(double(actual))<=limit,"GPU F0 null exceeds unchanged arithmetic/input budget");MaxHydroRatio=(std::max)(MaxHydroRatio,fabs(double(actual))/limit);}
          if(f==Constant)Need(actual==0&&r.rate==0,"Constant negative field is not exactly null");
          if(f==Chain&&enabled&&Profile&&Surface(i)){const double ratio=fabs(r.scale*r.chain)/r.limit;MaxChainRatio=(std::max)(MaxChainRatio,ratio);if(ratio>1)ChainWitnesses++;}
          controls<<Profile<<','<<field<<','<<enabled<<','<<i<<','<<types[i]<<','<<p[i]<<','<<actual<<','<<GBits(actual)<<','<<r.rate<<','<<r.limit<<','<<r.quant<<','<<r.lp<<','<<r.lx.x<<','<<r.lx.z<<','<<r.gp.x<<','<<r.gp.z<<','<<r.da<<','<<r.gradj.x<<','<<r.gradj.z<<','<<r.corr.x<<','<<r.corr.z<<','<<r.lap<<','<<r.chain<<'\n';Rows++;
        }
      }
    }
    Need(Rows==810&&InteriorBits>0&&SurfaceRows>0&&ProjectionChecks==5&&(!Profile||ChainWitnesses>0),"Declared GPU zero-step coverage incomplete");InputsUnchanged();
  }
  void Complete(std::ostream& out)const{
    out<<std::setprecision(17)<<"{\"profile\":"<<Profile<<",\"controls\":"<<Rows<<",\"native_inner\":"<<InnerCount<<",\"native_FS\":"<<SurfaceCount<<",\"interior_bits\":"<<InteriorBits<<",\"nonzero_FS_chain_witnesses\":"<<ChainWitnesses<<",\"negative_projection_checks\":"<<ProjectionChecks<<",\"max_reference_ratio\":"<<MaxReferenceRatio<<",\"max_F0_null_ratio\":"<<MaxHydroRatio<<",\"max_FS_chain_ratio\":"<<MaxChainRatio<<"}";
  }
};

int main(int argc,char** argv){try{
  Need(argc==5&&std::string(argv[1])=="--expect"&&std::string(argv[3])=="--out","Use --expect raw|normal --out FRESH_DIR");
  const std::string mode=argv[2];Need(mode=="raw"||mode=="normal","Unknown reference mode");const fs::path out(argv[4]);Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh output/existing parent required");
  fs::create_directory(out);Cu(cudaSetDevice(0));cudaDeviceProp hardware{};Cu(cudaGetDeviceProperties(&hardware,0));
  int runtime=0,driver=0;Cu(cudaRuntimeGetVersion(&runtime));Cu(cudaDriverGetVersion(&driver));
  std::ofstream log(out/"Run.out"),controls(out/"controls.csv"),nodes(out/"nodes.csv"),off(out/"free_off_rates.bin",std::ios::binary);
  for(auto* f:{&log,&controls,&nodes,&off})Need(bool(*f),"Cannot create fresh GPU component output");
  log<<"device0="<<hardware.name<<" compute="<<hardware.major<<'.'<<hardware.minor<<" runtime="<<runtime<<" driver="<<driver<<" expected_reference="<<mode<<" physical_steps=0\n";
  controls<<std::setprecision(17);nodes<<std::setprecision(17);
  controls<<"profile,field_0hydro_1Ace_2chain_3tangent_4constant,free_on,native_id,fstype,p_Pa,actual_rate_Pa_s,actual_bits,reference_rate_Pa_s,arithmetic_budget_Pa_s,input_quantization_budget_Pa_s,LP,Lx_x,Lx_z,gp_x,gp_z,da,gradJ_x,gradJ_z,gpcorr_x,gpcorr_z,lap,chain\n";
  nodes<<"profile,native_id,x_m,y_m,z_m,fstype,normal_x,normal_y,normal_z,posdiv,J,n,V_m2,rho_exact_kg_m3,rho_cache_kg_m3,k_m_s,storage_weight_Vn_Kw,Cxx,Cxz,Czx,Czz\n";
  std::ostringstream summaries;
  for(unsigned profile=0;profile<2;profile++){FsNormalGpu test(profile,mode=="raw");test.Run(controls,nodes,off);if(profile)summaries<<',';test.Complete(summaries);}
  Cu(cudaDeviceSynchronize());
  for(auto* f:{&log,&controls,&nodes,&off}){f->flush();Need(bool(*f),"GPU diagnostic output write failed");}
  std::ofstream done(out/"completion.json");
  done<<std::setprecision(17)<<"{\"stage\":\"c08_fs_normal_gpu_r1\",\"formula_reference_matched\":true,\"expected_reference\":\""<<mode<<"\",\"reference_mode_changes_production\":false,\"production_GPU_FS_C\":true,\"CPU_FS_C_injected\":false,\"porosity_feedback_tracking\":true,\"dp_m\":0.04,\"H_actual_m\":"<<double(.072f)<<",\"mass_actual\":"<<double(float(2072.5*.04*.04))<<",\"n0_actual\":"<<double(.35f)<<",\"Kw_Pa\":1e9,\"k0_actual_m_s\":"<<double(.0002f)<<",\"Ck\":2,\"total_control_rows\":1620,\"node_rows\":162,\"profiles\":["<<summaries.str()<<"],\"input_and_tail_bits_preserved\":true,\"completed_physical_steps\":0,\"full_basis_computed\":false,\"CPU_GPU_bitwise_equivalence_proven\":false,\"coupled_stability_proven\":false,\"physical_acceptance\":false}\n";
  done.flush();Need(bool(done),"GPU completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"GPU FS component failed; preserve outputs\n";return 2;}}
