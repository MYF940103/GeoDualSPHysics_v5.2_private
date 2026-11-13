// Actual-CPU frozen pressure controls/basis only; no force, integrator or production edit.
#define main RetainedFeedbackMain
#include "../../../02_TerzaghiConsolidation_q0_PR/tests/support/upl_p2_feedback_harness_r1.cpp"
#undef main
#include <sstream>

static double MDot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static double MAbsDot(tdouble3 a,tdouble3 b){return fabs(a.x*b.x)+fabs(a.y*b.y)+fabs(a.z*b.z);}
static tdouble3 MAbs(tdouble3 a){return TDouble3(fabs(a.x),fabs(a.y),fabs(a.z));}
static tdouble3 MMul(tmatrix3d c,tdouble3 a){return TDouble3(c.a11*a.x+c.a12*a.y+c.a13*a.z,c.a21*a.x+c.a22*a.y+c.a23*a.z,c.a31*a.x+c.a32*a.y+c.a33*a.z);}
static tdouble3 MTangent(tdouble3 a,tdouble3 n){const double nn=MDot(n,n);Require(std::isfinite(nn)&&nn>0,"Invalid actual FS normal");return a-n*(MDot(n,a)/nn);}
static unsigned MBits(float a){unsigned b=0;static_assert(sizeof(a)==sizeof(b),"Need binary32 bits");memcpy(&b,&a,sizeof(b));return b;}
class FsMatrix:public Feedback{
  static constexpr unsigned Count=81;
  static constexpr double Delta=.25;
  enum Field{Hydro,NonconstantAce,Chain,Basis};
  struct Point{tdouble3 x;unsigned id,key;};
  struct Ref{double rate=0,limit=0,quant=0,lp=0,lap=0,da=0,chain=0,scale=0;tdouble3 lx=TDouble3(0),gp=TDouble3(0),gradj=TDouble3(0),corr=TDouble3(0);};
  struct Sample{Ref ref;float actual;};
  using StateRow=std::array<double,21>;
  using FsRow=std::array<double,14>;
  unsigned Profile,ControlRows=0,BaseRows=0,MatrixRows=0,InteriorBits=0,ChainWitnesses=0;
  bool Raw;
  double MaxReferenceRatio=0,MaxHydroRatio=0,MaxChainRatio=0;
  std::vector<unsigned> Cells;
  std::vector<FsRow> FrozenFs;
  bool Surface(unsigned p)const{return IsFreeSurfaceParticle(p,Codec,FSTypec);}
  int Ix(unsigned p)const{return int(Idpc[p]%9)-4;}
  int Iz(unsigned p)const{return int(Idpc[p]/9)-4;}
  double JValue(unsigned p)const{return Profile?1.+double(Ix(p)+2*Iz(p))/512.:1.;}
  double HydroIdeal(unsigned p)const{return -4096.+double(SoilCte.PoreWaterRho)*double(Gravity.z)*(Posc[p].z-1.);}
  void NoStep()const{Require(TimeStep==0&&Nstep==0&&!PoroJPrec&&!PorePressPrec,"A physical stage/time was advanced");}
  std::vector<StateRow> State()const{
    std::vector<StateRow> out;for(unsigned p=0;p<Np;p++){const auto x=Posc[p];const auto v=Velrhopc[p];const auto s=Sigmac[p];const auto a=Acec[p];
      out.push_back({x.x,x.y,x.z,v.x,v.y,v.z,v.w,PorePressc[p],PorePress0c[p],PoroJc[p],PoroThetac[p],s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,Kplasticc[p],a.x,a.y,a.z});
      for(double b:out.back())Require(std::isfinite(b),"Nonfinite native fixture state");
    }return out;
  }
  std::vector<FsRow> FsState()const{
    std::vector<FsRow> out;for(unsigned p=0;p<Np;p++){const auto c=CorrMatc[p];const auto n=FSNormalc[p];out.push_back({c.a11,c.a12,c.a13,c.a21,c.a22,c.a23,c.a31,c.a32,c.a33,n.x,n.y,n.z,double(FSTypec[p]),PosDivc[p]});}return out;
  }
  void Fixed()const{NoStep();const auto a=FsState();Require(a.size()==FrozenFs.size()&&!memcmp(a.data(),FrozenFs.data(),a.size()*sizeof(FsRow)),"Production FS/C/normal changed within frozen profile");}
  void CellTable(){
    const tuint3 nc=TUint3(5,1,5);const unsigned ncell=nc.x*nc.y*nc.z,code=DCEL_GetCode(26,2,3);const auto origin=TDouble3(.5,0,.5);
    std::vector<Point> a;for(unsigned p=0;p<Np;p++){const auto x=Posc[p];const unsigned cx=unsigned((x.x-origin.x)/KernelSize),cz=unsigned((x.z-origin.z)/KernelSize);Require(cx<nc.x&&cz<nc.z,"Point outside cell table");a.push_back({x,Idpc[p],cx+nc.x*cz});}
    std::stable_sort(a.begin(),a.end(),[](const Point& x,const Point& y){return x.key<y.key;});Cells.assign(2*(ncell+1),0);unsigned cursor=0;
    for(unsigned c=0;c<=ncell;c++){while(cursor<Np&&a[cursor].key<c)cursor++;Cells[ncell+1+c]=cursor;}
    DivData=MakeDivDataCpu(1,nc,TUint3(0),Cells.data(),KernelSize,code,origin);
    for(unsigned p=0;p<Np;p++){Posc[p]=a[p].x;Idpc[p]=a[p].id;Codec[p]=CODE_TYPE_FLUID;Dcellc[p]=DCEL_Cell(code,a[p].key%nc.x,0,a[p].key/nc.x);Require(DCEL_Cellx(code,Dcellc[p])==a[p].key%nc.x&&DCEL_Celly(code,Dcellc[p])==0&&DCEL_Cellz(code,Dcellc[p])==a[p].key/nc.x,"Local cell encode/decode roundtrip failed");}
  }
  void SetField(Field f,unsigned column=Count){
    for(unsigned p=0;p<Np;p++){
      PoroJc[p]=JValue(p);double n,v,rho;GetPorosityFeedbackStateCpu(p,n,v,rho);Require(n>0&&n<1&&v>0&&rho>0,"Invalid actual J ledger");
      double pressure=-16.;tdouble3 a=TDouble3(0);
      if(f==Hydro){pressure=HydroIdeal(p);a=ToTDouble3(Gravity)*-1.;}
      if(f==NonconstantAce){pressure+=Ix(p)/8.+Iz(p)/16.;a=TDouble3(Ix(p)/128.+Iz(p)/256.,0,Ix(p)/256.-Iz(p)/128.);}
      if(f==Chain)pressure+=Ix(p)/4.+Iz(p)/8.;if(f==Basis&&Idpc[p]==column)pressure+=Delta;
      Require(std::isfinite(pressure)&&pressure<0,"Manufactured pressure is not strictly negative");if(f!=Hydro)Require(double(float(pressure))==pressure,"Nonhydro pressure input is not exact binary32");
      Velrhopc[p]=TFloat4(0,0,0,float(rho));Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;PoroThetac[p]=0;
      PorePressc[p]=float(pressure);PorePress0c[p]=0;PorePressRatec[p]=1234567.f;if(Acec)Acec[p]=ToTFloat3(a);
    }
  }
  Ref Assemble(Field f,unsigned i,bool on)const{
    Ref r;const double rho=SoilCte.PoreWaterRho,v0=double(MassFluid)/RhopZero,ki=GetDynamicConductivityCpu(i),dk=ki/((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk);
    double n,vol,rhot;GetPorosityFeedbackStateCpu(i,n,vol,rhot);r.scale=double(SoilCte.PoreWaterBulkModulus)/n/(rho*9.80665);
    double lpabs=0,daabs=0,lpq=0;tdouble3 gpq=TDouble3(0);const auto ai=ToTDouble3(Acec[i]);
    for(unsigned j=0;j<Np;j++){
      const auto d=Posc[i]-Posc[j];const double rr=MDot(d,d);if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;
      const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr))),gi=MMul(CorrMatc[i],g),gj=MMul(CorrMatc[j],g);
      const double v=v0*PoroJc[j],w=v*MDot(d,gi+gj)/(rr+double(Eta2)),dp=double(PorePressc[i])-PorePressc[j];const auto da=ToTDouble3(Acec[j])-ai;
      r.lp+=w*dp;r.lx=r.lx+d*w;r.gp=r.gp-gi*(v*dp);r.da+=v*MDot(da,gi);r.gradj=r.gradj+gi*(v*(PoroJc[j]-PoroJc[i]));
      lpabs+=fabs(w*dp);daabs+=v*MAbsDot(da,gi);
      if(f==Hydro){const double q=fabs(double(PorePressc[i])-HydroIdeal(i))+fabs(double(PorePressc[j])-HydroIdeal(j));lpq+=fabs(w)*q;gpq=gpq+MAbs(gi)*(v*q);}
    }
    const bool sf=on&&Surface(i),raw=sf&&Raw,project=sf&&!Raw;const auto normal=ToTDouble3(FSNormalc[i]);r.corr=r.gp;
    if(project)r.corr=r.gp-normal*(MDot(normal,r.gp+ai*rho)/MDot(normal,normal));
    r.lap=raw?r.lp+rho*(MDot(ai,r.lx)+r.da):r.lp-MDot(r.corr,r.lx)+rho*r.da;
    const auto force=r.corr+ai*rho;r.chain=dk*MDot(r.gradj,force);r.rate=r.scale*(ki*r.lap+r.chain);
    const double lapabs=lpabs+rho*daabs+(raw?rho*MAbsDot(ai,r.lx):MAbsDot(r.corr,r.lx));
    const double base=32*FLT_EPSILON+4096*DBL_EPSILON;r.limit=base*(std::max)(1.,r.scale*(ki*lapabs+dk*MAbsDot(r.gradj,force)));
    const auto ql=raw?TDouble3(0):(project?MTangent(r.lx,normal):r.lx),qj=project?MTangent(r.gradj,normal):r.gradj;
    r.quant=r.scale*(ki*(lpq+MAbsDot(ql,gpq))+dk*MAbsDot(qj,gpq));return r;
  }
  std::vector<Sample> Evaluate(Field f,bool on){
    Fixed();HydroMechFreeSeepage=on;const auto before=State();std::vector<Sample> out;for(unsigned p=0;p<Np;p++)out.push_back({Assemble(f,p,on),0});
    ComputeDynamicPorePressureRateCpu();
    for(unsigned p=0;p<Np;p++){
      auto& a=out[p];a.actual=PorePressRatec[p];const double error=fabs(double(a.actual)-a.ref.rate);Require(std::isfinite(a.actual)&&error<=a.ref.limit,"Actual production rate differs from expected formula");
      MaxReferenceRatio=(std::max)(MaxReferenceRatio,error/a.ref.limit);
      if(f==Hydro){const double limit=2*a.ref.limit+a.ref.quant;Require(fabs(double(a.actual))<=limit,"Hydraulic F0 null exceeds predeclared arithmetic/input budget");MaxHydroRatio=(std::max)(MaxHydroRatio,fabs(double(a.actual))/limit);}
      if(f==Chain&&on&&Profile&&Surface(p)){const double ratio=fabs(a.ref.scale*a.ref.chain)/a.ref.limit;MaxChainRatio=(std::max)(MaxChainRatio,ratio);if(ratio>1)ChainWitnesses++;}
    }
    const auto after=State();Require(!memcmp(before.data(),after.data(),Np*sizeof(StateRow)),"Zero-step RHS changed native state or prescribed Ace");Fixed();return out;
  }
  void ControlRow(std::ostream& out,unsigned field,bool on,unsigned p,const Sample& a)const{
    const auto& r=a.ref;out<<Profile<<','<<field<<','<<on<<','<<Idpc[p]<<','<<FSTypec[p]<<','<<PorePressc[p]<<','<<a.actual<<','<<MBits(a.actual)<<','<<r.rate<<','<<r.limit<<','<<r.quant<<','<<r.lp<<','<<r.lx.x<<','<<r.lx.z<<','<<r.gp.x<<','<<r.gp.z<<','<<r.da<<','<<r.gradj.x<<','<<r.gradj.z<<','<<r.corr.x<<','<<r.corr.z<<','<<r.lap<<','<<r.chain<<'\n';
  }
public:
  FsMatrix(unsigned profile,bool raw):Feedback(2,9),Profile(profile),Raw(raw){
    Require(profile<2,"Unknown fixed J profile");NoStep();Np=CaseNp=CaseNfluid=Count;Npb=NpbOk=CaseNpb=CaseNfixed=0;NpfPer=NpbPer=0;
    AllocCpuMemoryParticles(Count,0);ReserveBasicArraysCpu();Require(Count<=CpuParticlesSize&&CheckCpuParticlesSize(Count),"Insufficient allocation capacity");
    Dp=.04;RhopZero=2072.5f;MassFluid=MassBound=float(double(RhopZero)*Dp*Dp);SoilCte.Porosity=.35f;SoilCte.PoreWaterRho=1000;SoilCte.PoreWaterBulkModulus=1e9f;InitPorosityObserverCpu();
    TKernel=KERNEL_Wendland;KernelH=.072f;KernelSize=2*KernelH;KernelSize2=KernelSize*KernelSize;Eta2=.01f*KernelH*KernelH;
    CSP.tkernel=TKernel;CSP.dp=Dp;CSP.massfluid=MassFluid;CSP.massbound=MassBound;CSP.rhopzero=RhopZero;CSP.kernelh=KernelH;CSP.kernelsize=KernelSize;CSP.kernelsize2=KernelSize2;CSP.eta2=Eta2;CSP.kwend=fsph::GetKernelWendland_Ctes(true,KernelH);
    DynamicPorePressure=true;DynamicPoreWall=false;DynamicPoreConductivity=true;DynamicPoreConductivityCk=2.;SoilCte.HydraulicConductivity=.0002f;Gravity=CSP.gravity=TFloat3(0,0,-9.81f);HydroMechDrainage=false;HydroMechFreeSeepage=true;
    Require(!PeriActive&&!DynamicPoreFreeBody,"Unexpected fixture scope");unsigned p=0;
    for(int iz=-4;iz<=4;iz++)for(int ix=-4;ix<=4;ix++,p++){Posc[p]=TDouble3(1+ix*Dp+(iz<4?Dp/8:0),0,1+iz*Dp);Idpc[p]=p;}
    CellTable();SetField(Basis);for(unsigned i=0;i<Np;i++){FSTypec[i]=FST_Inner;FSNormalc[i]=TFloat3(0);PosDivc[i]=0;CorrMatc[i]=TMatrix3d(0);HydroMechLoadAcec[i]=TFloat3(0);}
  }
  void Run(std::ostream& rows,std::ostream& controls,std::ostream& nodes){
    PreInteraction_Forces();ComputeFreeSurfaceTracking();FrozenFs=FsState();unsigned inner=0,surface=0;
    for(unsigned p=0;p<Np;p++){
      Surface(p)?surface++:inner++;if(Idpc[p]==76)Require(Surface(p),"Predeclared actual flat-top ID76 is not FS");
      double n,v,rho;GetPorosityFeedbackStateCpu(p,n,v,rho);const auto x=Posc[p],normal=ToTDouble3(FSNormalc[p]);const auto c=CorrMatc[p];
      nodes<<Profile<<','<<Idpc[p]<<','<<x.x<<','<<x.y<<','<<x.z<<','<<FSTypec[p]<<','<<normal.x<<','<<normal.y<<','<<normal.z<<','<<PosDivc[p]<<','<<PoroJc[p]<<','<<n<<','<<v<<','<<rho<<','<<Velrhopc[p].w<<','<<GetDynamicConductivityCpu(p)<<','<<v*n/double(SoilCte.PoreWaterBulkModulus)<<','<<c.a11<<','<<c.a13<<','<<c.a31<<','<<c.a33<<'\n';
    }
    Require(inner&&surface,"Missing real inner/FS coverage");
    for(unsigned field=0;field<3;field++){
      const auto f=Field(field);SetField(f);const auto off=Evaluate(f,false),on=Evaluate(f,true);
      for(unsigned p=0;p<Np;p++){
        if(!Surface(p)){Require(MBits(off[p].actual)==MBits(on[p].actual),"Interior FreeSeepageOFF/ON bits differ");InteriorBits++;}
        for(unsigned enabled=0;enabled<2;enabled++){ControlRow(controls,field,enabled!=0,p,(enabled?on:off)[p]);ControlRows++;}
      }
    }
    SetField(Basis);const auto baseline=Evaluate(Basis,true);for(unsigned p=0;p<Np;p++){Require(baseline[p].actual==0&&baseline[p].ref.rate==0,"Constant negative basis baseline is not exactly null");ControlRow(controls,3,true,p,baseline[p]);BaseRows++;}
    for(unsigned column=0;column<Count;column++){
      SetField(Basis,column);const auto a=Evaluate(Basis,true);
      for(unsigned p=0;p<Np;p++){rows<<Profile<<','<<Idpc[p]<<','<<column<<','<<(double(a[p].actual)-baseline[p].actual)/Delta<<','<<(a[p].ref.rate-baseline[p].ref.rate)/Delta<<','<<(a[p].ref.limit+baseline[p].ref.limit)/Delta<<'\n';MatrixRows++;}
    }
    Require(ControlRows==486&&BaseRows==81&&MatrixRows==6561&&InteriorBits>0&&(!Profile||ChainWitnesses>0),"Declared frozen component coverage is incomplete");Fixed();PosInteraction_Forces();NoStep();
  }
  void Complete(std::ostream& out)const{NoStep();out<<std::setprecision(17)<<"{\"profile\":"<<Profile<<",\"controls\":"<<ControlRows<<",\"base_rows\":"<<BaseRows<<",\"matrix_rows\":"<<MatrixRows<<",\"interior_bits\":"<<InteriorBits<<",\"nonzero_FS_chain_witnesses\":"<<ChainWitnesses<<",\"max_reference_ratio\":"<<MaxReferenceRatio<<",\"max_F0_null_ratio\":"<<MaxHydroRatio<<",\"max_FS_chain_ratio\":"<<MaxChainRatio<<"}";}
};
int main(int argc,char** argv){try{
  Require(argc==5&&std::string(argv[1])=="--expect"&&std::string(argv[3])=="--out","Use --expect raw|normal --out FRESH_DIR");const std::string mode=argv[2];Require(mode=="raw"||mode=="normal","Unknown reference mode");const fs::path out(argv[4]);Require(!fs::exists(out),"Existing output protected");
  AppInfo.ConfigRunPaths(argv[0]);AppInfo.ConfigOutput(true,false,out.string(),"data");AppInfo.LogInit((out/"Run.out").string());
  std::ofstream matrix(out/"matrix.csv"),controls(out/"controls.csv"),nodes(out/"nodes.csv");for(auto* f:{&matrix,&controls,&nodes}){Require(bool(*f),"Cannot create fresh CSV");*f<<std::setprecision(17);}
  matrix<<"profile,row_id,column_id,actual_A_per_s,reference_A_per_s,propagated_entry_budget_per_s\n";
  controls<<"profile,field_0hydro_1Ace_2chain_3base,free_on,native_id,fstype,p_Pa,actual_rate_Pa_s,actual_bits,reference_rate_Pa_s,arithmetic_budget_Pa_s,input_quantization_budget_Pa_s,LP,Lx_x,Lx_z,gp_x,gp_z,da,gradJ_x,gradJ_z,gpcorr_x,gpcorr_z,lap,chain\n";
  nodes<<"profile,native_id,x_m,y_m,z_m,fstype,normal_x,normal_y,normal_z,posdiv,J,n,V_m2,rho_exact_kg_m3,rho_cache_kg_m3,k_m_s,storage_weight_Vn_Kw,Cxx,Cxz,Czx,Czz\n";
  std::ostringstream summaries;for(unsigned profile=0;profile<2;profile++){FsMatrix test(profile,mode=="raw");test.Run(matrix,controls,nodes);if(profile)summaries<<',';test.Complete(summaries);}
  for(auto* f:{&matrix,&controls,&nodes}){f->flush();Require(bool(*f),"Diagnostic CSV write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"c08_fs_matrix_cpu_r2\",\"formula_reference_matched\":true,\"expected_reference\":\""<<mode<<"\",\"reference_mode_changes_production\":false,\"operator_scope\":\"frozen_pressure_only_prescribed_Ace_J\",\"kernel\":\"Wendland\",\"dp\":0.04,\"H_actual_m\":"<<double(.072f)<<",\"Kw_Pa\":1e9,\"n0_actual\":"<<double(.35f)<<",\"k0_actual_m_s\":"<<double(.0002f)<<",\"Ck\":2,\"basis_base_Pa\":-16,\"basis_delta_Pa\":0.25,\"profiles\":["<<summaries.str()<<"],\"production_FS_C\":true,\"completed_physical_steps\":0,\"eigenvalues_computed\":false,\"physical_acceptance\":false}\n";done.flush();Require(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Frozen FS matrix fixture failed; preserve outputs\n";return 2;}}
