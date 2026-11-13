// Zero-step diagnostic of the existing negative-p free-seepage RHS. No production edit.
#define main RetainedFeedbackMain
#include "../../../02_TerzaghiConsolidation_q0_PR/tests/support/upl_p2_feedback_harness_r1.cpp"
#undef main
#include <sstream>

static double ADot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static tdouble3 AMul(tmatrix3d c,tdouble3 a){return TDouble3(c.a11*a.x+c.a12*a.y+c.a13*a.z,c.a21*a.x+c.a22*a.y+c.a23*a.z,c.a31*a.x+c.a32*a.y+c.a33*a.z);}
class AffineFs:public Feedback{
  static constexpr unsigned Count=81;
  struct Point{tdouble3 x;unsigned id,key;};
  struct Sum{double lp=0,da=0,lpabs=0,gpabs=0,scale=0,raw=0,corrected=0,rawlimit=0,oldlimit=0,gradientlimit=0,identitylimit=0;tdouble3 lx=TDouble3(0),gp=TDouble3(0);};
  using StateRow=std::array<double,18>;
  std::vector<unsigned> Cells;
  unsigned Rows=0,TopRows=0,Signals=0;
  double MaxReferenceRatio=0,MaxCorrectedRatio=0,MaxContinuumRatio=0;
  bool Surface(unsigned p)const{return IsFreeSurfaceParticle(p,Codec,FSTypec);}
  bool Top(unsigned p)const{return Idpc[p]==76;}
  const char* KernelName()const{return TKernel==KERNEL_Cubic?"Cubic":"Wendland";}
  double Hdp()const{return TKernel==KERNEL_Cubic?1.2:1.8;}
  void NoStep()const{Require(TimeStep==0&&Nstep==0&&!PoroJPrec&&!PorePressPrec,"A physical stage/time was advanced");}
  std::vector<StateRow> Snapshot()const{
    std::vector<StateRow> result;for(unsigned p=0;p<Np;p++){
      const auto x=Posc[p];const auto v=Velrhopc[p];const auto s=Sigmac[p];
      result.push_back({x.x,x.y,x.z,v.x,v.y,v.z,v.w,PorePressc[p],PorePress0c[p],PoroJc[p],PoroThetac[p],s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,Kplasticc[p]});
      for(double a:result.back())Require(std::isfinite(a),"Nonfinite native fixture state");
    }return result;
  }
  void CellTable(){
    const tuint3 nc=TUint3(5,1,5);const unsigned ncell=nc.x*nc.y*nc.z,code=DCEL_GetCode(27,2,2);
    std::vector<Point> points;for(unsigned p=0;p<Np;p++){
      const auto x=Posc[p];const unsigned cx=unsigned(x.x/KernelSize),cz=unsigned(x.z/KernelSize);
      Require(cx<nc.x&&cz<nc.z,"Manufactured point outside inherited cell table");points.push_back({x,Idpc[p],cx+nc.x*cz});
    }
    std::stable_sort(points.begin(),points.end(),[](const Point& a,const Point& b){return a.key<b.key;});
    Cells.assign(2*(ncell+1),0);unsigned cursor=0;
    for(unsigned c=0;c<=ncell;c++){while(cursor<Np&&points[cursor].key<c)cursor++;Cells[ncell+1+c]=cursor;}
    DivData=MakeDivDataCpu(1,nc,TUint3(0),Cells.data(),KernelSize,code,TDouble3(0));
    for(unsigned p=0;p<Np;p++){const auto a=points[p];Posc[p]=a.x;Idpc[p]=a.id;Codec[p]=CODE_TYPE_FLUID;Dcellc[p]=DCEL_Cell(code,a.key%nc.x,0,a.key/nc.x);}
  }
  void Field(double b){
    for(unsigned p=0;p<Np;p++){
      const double pressure=-16+b*Posc[p].x;
      Require(pressure<0&&fabs(pressure)<=256&&double(float(pressure))==pressure,"Pressure must be strictnegative exact binary32 within inherited256 scale");
      Velrhopc[p]=TFloat4(0,0,0,RhopZero);Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;
      PoroJc[p]=1;PoroThetac[p]=0;PorePressc[p]=float(pressure);PorePress0c[p]=0;PorePressRatec[p]=1234567.f;
    }
  }
  template<TpKernel tker> Sum Assemble(double b,unsigned i)const{
    Sum r;const double rho=SoilCte.PoreWaterRho,v0=double(MassFluid)/RhopZero;
    const double n=1.-(1.-double(SoilCte.Porosity))/PoroJc[i];
    r.scale=double(SoilCte.PoreWaterBulkModulus)/n*double(SoilCte.HydraulicConductivity)/(rho*9.80665);
    // Independent all-particle sum of the production formulas, using actual production C/J/Ace/p.
    for(unsigned j=0;j<Np;j++){
      const auto d=Posc[i]-Posc[j];const double rr=ADot(d,d);if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;
      const auto g=d*double(fsph::GetKernel_Fac<tker>(CSP,float(rr))),gi=AMul(CorrMatc[i],g),gj=AMul(CorrMatc[j],g);
      const double v=v0*PoroJc[j],w=v*ADot(d,gi+gj)/(rr+double(Eta2)),dp=double(PorePressc[i])-PorePressc[j];
      r.lp+=w*dp;r.lx=r.lx+d*w;r.gp=r.gp-gi*(v*dp);r.da+=v*ADot(ToTDouble3(Acec[j])-ToTDouble3(Acec[i]),gi);
      r.lpabs+=fabs(w*dp);r.gpabs+=v*fabs(dp)*(fabs(gi.x)+fabs(gi.y)+fabs(gi.z));
    }
    r.raw=r.lp+rho*(ADot(ToTDouble3(Acec[i]),r.lx)+r.da);r.corrected=r.lp-ADot(r.gp,r.lx)+rho*r.da;
    // Retained direct-sum sourcefloat constants, declared before any execution; not physical tolerances.
    const double base=32*FLT_EPSILON+4096*DBL_EPSILON;
    r.rawlimit=base*(std::max)(1.,r.scale*r.lpabs);
    r.oldlimit=base*(std::max)(1.,r.scale*(r.lpabs+fabs(r.gp.x*r.lx.x)+fabs(r.gp.y*r.lx.y)+fabs(r.gp.z*r.lx.z)));
    r.gradientlimit=base*(std::max)(1.,r.gpabs+fabs(b));r.identitylimit=base*(std::max)(1.,r.lpabs+fabs(b*r.lx.x));return r;
  }
public:
  AffineFs(TpKernel kernel):Feedback(2,9){
    NoStep();Np=CaseNp=CaseNfluid=Count;Npb=NpbOk=CaseNpb=CaseNfixed=0;NpfPer=NpbPer=0;
    AllocCpuMemoryParticles(Count,0);ReserveBasicArraysCpu();
    Require(Count<=CpuParticlesSize&&CheckCpuParticlesSize(Count),"Insufficient inherited allocation capacity");InitPorosityObserverCpu();
    Require(kernel==KERNEL_Cubic||kernel==KERNEL_Wendland,"Unknown predeclared kernel");TKernel=kernel;CSP.tkernel=TKernel;KernelH=float(Hdp()*Dp);KernelSize=2*KernelH;KernelSize2=KernelSize*KernelSize;Eta2=.01f*KernelH*KernelH;
    CSP.kernelh=KernelH;CSP.kernelsize=KernelSize;CSP.kernelsize2=KernelSize2;CSP.eta2=Eta2;
    if(TKernel==KERNEL_Cubic)CSP.kcubic=fsph::GetKernelCubic_Ctes(true,KernelH);else CSP.kwend=fsph::GetKernelWendland_Ctes(true,KernelH);
    DynamicPorePressure=true;DynamicPoreWall=false;DynamicPoreConductivity=false;SoilCte.HydraulicConductivity=1e-5f;
    Gravity=CSP.gravity=TFloat3(0,0,-1./16.);HydroMechFreeSeepage=true;HydroMechDrainage=false;
    Require(Dp==.25&&!PeriActive&&!DynamicPoreFreeBody,"Unexpected inherited fixture scope");
    unsigned p=0;for(int z=-4;z<=4;z++)for(int x=-4;x<=4;x++,p++){
      // One predeclared tangential perturbation: every subsurface row shifts +Dp/8; top plane stays z=2.
      Posc[p]=TDouble3(1+x*Dp+(z<4? Dp/8:0),0,1+z*Dp);Idpc[p]=p;
    }
    CellTable();Field(0);for(unsigned i=0;i<Np;i++){FSTypec[i]=FST_Inner;FSNormalc[i]=TFloat3(0);PosDivc[i]=0;CorrMatc[i]=TMatrix3d(0);HydroMechLoadAcec[i]=TFloat3(0);}
  }
  void Run(std::ostream& out){
    const double slopes[3]={0,4,-4};std::vector<float> plus(Count);std::vector<unsigned> initialMask;
    for(unsigned field=0;field<3;field++){
      const double b=slopes[field];Field(b);PreInteraction_Forces();ComputeFreeSurfaceTracking();
      unsigned inner=0,top=0;for(unsigned p=0;p<Np;p++){if(!Surface(p))inner++;if(Top(p)){Require(Posc[p].z==2&&Surface(p),"Predeclared flat-top interior was not actually FS");top++;}Acec[p]=TFloat3(0);}
      Require(inner>0&&top==1,"Missing actual interior/flat-top FS coverage");
      if(field==0)initialMask.assign(FSTypec,FSTypec+Np);else Require(!memcmp(initialMask.data(),FSTypec,Np*sizeof(unsigned)),"Actual FS mask changed with pressure slope");
      const auto before=Snapshot();const std::vector<float> sentinels(PorePressRatec,PorePressRatec+Np);
      ApplyPorePressureBoundaries();const auto projected=Snapshot();
      Require(!memcmp(before.data(),projected.data(),Np*sizeof(StateRow))&&!memcmp(sentinels.data(),PorePressRatec,Np*sizeof(float)),"Accepted negative FS pressure/rate was projected");
      std::vector<Sum> sums;for(unsigned p=0;p<Np;p++)sums.push_back(TKernel==KERNEL_Cubic?Assemble<KERNEL_Cubic>(b,p):Assemble<KERNEL_Wendland>(b,p));
      ComputeDynamicPorePressureRateCpu();
      for(unsigned p=0;p<Np;p++){
        const auto& r=sums[p];const bool sf=Surface(p);const double actual=PorePressRatec[p],expected=r.scale*(sf?r.raw:r.corrected),limit=sf?r.rawlimit:r.oldlimit;
        Require(std::isfinite(actual)&&fabs(actual-expected)<=limit,"Actual Darcy RHS differs from all-particle reference");
        Require(r.da==0&&fabs(r.lp-b*r.lx.x)<=r.identitylimit,"Affine LP identity or constant acceleration failed");
        Require(fabs(r.gp.x-b)+fabs(r.gp.y)+fabs(r.gp.z)<=r.gradientlimit,"Actual C did not reproduce the affine pressure gradient");
        Require(fabs(r.scale*r.corrected)<=r.oldlimit,"Corrected affine RHS exceeds inherited roundoff budget");
        if(field==0)Require(fabs(actual)<=limit,"Constant pressure produced nonzero RHS");
        if(field==1)plus[Idpc[p]]=PorePressRatec[p];if(field==2)Require(fabs(actual+plus[Idpc[p]])<=2*limit,"Opposite affine drives did not reverse RHS within summed budgets");
        if(Top(p)){TopRows++;if(b!=0&&fabs(r.scale*b*r.lx.x)>r.rawlimit&&fabs(actual)>r.rawlimit)Signals++;}
        MaxReferenceRatio=(std::max)(MaxReferenceRatio,fabs(actual-expected)/limit);MaxCorrectedRatio=(std::max)(MaxCorrectedRatio,fabs(r.scale*r.corrected)/r.oldlimit);
        if(Top(p)&&b!=0)MaxContinuumRatio=(std::max)(MaxContinuumRatio,fabs(actual)/r.rawlimit);
        out<<KernelName()<<','<<Hdp()<<','<<KernelH<<','<<b<<','<<Idpc[p]<<','<<Posc[p].x<<','<<Posc[p].z<<','<<FSTypec[p]<<','<<sf<<','<<Top(p)<<','<<FSNormalc[p].x<<','<<FSNormalc[p].z<<','<<PosDivc[p]<<','<<PorePressc[p]<<','<<Acec[p].x<<','<<Acec[p].z<<','<<r.lp<<','<<r.lx.x<<','<<r.lx.z<<','<<r.gp.x<<','<<r.gp.z<<','<<r.da<<','<<r.raw<<','<<r.corrected<<",0,"<<b*r.lx.x<<','<<actual<<','<<expected<<",0,"<<r.rawlimit<<','<<r.oldlimit<<','<<r.gradientlimit<<','<<r.identitylimit<<'\n';Rows++;
      }
      const auto after=Snapshot();Require(!memcmp(before.data(),after.data(),Np*sizeof(StateRow)),"Zero-step RHS changed native state");
      for(unsigned p=0;p<Np;p++)Require(Acec[p].x==0&&Acec[p].y==0&&Acec[p].z==0,"RHS changed prescribed Ace");
      PosInteraction_Forces();NoStep();
    }
    Require(Rows==243&&TopRows==3&&Signals>0,"No resolved affine tangential-drive witness on actual flat-top FS; do not retune silently");
  }
  void Complete(std::ostream& out)const{
    NoStep();out<<std::setprecision(17)<<"{\"kernel\":\""<<KernelName()<<"\",\"nominal_h_dp\":"<<Hdp()<<",\"kernel_h_m\":"<<KernelH<<",\"rows\":"<<Rows<<",\"flat_top_rows\":"<<TopRows<<",\"resolved_signal_rows\":"<<Signals<<",\"max_reference_ratio\":"<<MaxReferenceRatio<<",\"max_corrected_roundoff_ratio\":"<<MaxCorrectedRatio<<",\"max_flat_top_continuum_excess_ratio\":"<<MaxContinuumRatio<<"}";
  }
};
int main(int argc,char** argv){try{
  Require(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_DIR");const fs::path out(argv[2]);Require(!fs::exists(out),"Existing output protected");
  AppInfo.ConfigRunPaths(argv[0]);AppInfo.ConfigOutput(true,false,out.string(),"data");AppInfo.LogInit((out/"Run.out").string());
  std::ofstream rows(out/"rates.csv");Require(bool(rows),"Cannot create fresh diagnostic CSV");rows<<std::setprecision(17);
  rows<<"kernel,nominal_h_dp,kernel_h_m,b_Pa_per_m,native_id,x_m,z_m,fstype,surface,flat_top_interior,fsnormal_x,fsnormal_z,posdiv,p_Pa,Ace_x,Ace_z,direct_LP,direct_Lx_x,direct_Lx_z,direct_gp_x,direct_gp_z,direct_da,direct_H_raw,direct_H_corrected,analytic_H,direct_bLx_x,actual_rate_Pa_s,reference_actual_branch_rate_Pa_s,analytic_rate_Pa_s,raw_rate_roundoff_Pa_s,corrected_rate_roundoff_Pa_s,gradient_roundoff_Pa_per_m,LP_identity_roundoff_Pa_per_m2\n";
  std::ostringstream summaries;bool first=true;for(auto kernel:{KERNEL_Cubic,KERNEL_Wendland}){AffineFs test(kernel);test.Run(rows);if(!first)summaries<<',';test.Complete(summaries);first=false;}
  rows.flush();Require(bool(rows),"Diagnostic CSV write failed");std::ofstream done(out/"completion.json");
  done<<"{\"stage\":\"c08_fs_affine_cpu_r1\",\"fixture_passed\":true,\"operator_continuum_passed\":false,\"continuum_consistency_witness\":true,\"kernel_reviews\":["<<summaries.str()<<"],\"total_rows\":486,\"production_FS_C\":true,\"manual_FS_C\":false,\"completed_physical_steps\":0,\"physical_acceptance\":false,\"C08_causation_proven\":false}\n";
  done.flush();Require(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Affine FS fixture failed; preserve outputs\n";return 2;}}
