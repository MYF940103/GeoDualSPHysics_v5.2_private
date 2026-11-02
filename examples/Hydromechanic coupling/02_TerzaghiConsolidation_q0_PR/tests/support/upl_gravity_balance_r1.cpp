// Descriptive continuous-hydrostatic residual through actual CPU force assembly.
#define main RetainedBalanceFeedbackMain
#include "upl_p2_feedback_harness_r1.cpp"
#undef main

static double BDot(const tdouble3& a,const tdouble3& b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static double BNorm(const tdouble3& a){return sqrt(BDot(a,a));}
static tdouble3 BProduct(const tmatrix3d& c,const tdouble3& a){return TDouble3(c.a11*a.x+c.a12*a.y+c.a13*a.z,c.a21*a.x+c.a22*a.y+c.a23*a.z,c.a31*a.x+c.a32*a.y+c.a33*a.z);}
static void BVector(std::ostream& out,const tdouble3& a){out<<','<<a.x<<','<<a.y<<','<<a.z;}

class BalanceActual:public Feedback{
  unsigned Dimension;bool Jitter;std::vector<unsigned> Cells;
  std::vector<double> TrueTotal;
  struct Point{tdouble3 x;unsigned id,key;};
  struct Reference{
    tfloat3 rounded=TFloat3(0);
    tdouble3 input=TDouble3(0),continuous=TDouble3(0),e0=TDouble3(0),gp=TDouble3(0);
    tmatrix3d moment=TMatrix3d(0);
    double raw_input_abs=0,raw_continuous_abs=0;
  };
  Reference Assemble(unsigned i)const{
    Reference r{};const double v0=double(MassFluid)/double(RhopZero),coeff=v0/double(RhopZero);
    const auto si=ToTSymMatrix3f(Sigmac[i]);
    // Independent all-particle enumeration, no production cell-range calls.
    for(unsigned j=0;j<Np;j++){
      const auto d=Posc[i]-Posc[j];const float dx=float(d.x),dy=float(d.y),dz=float(d.z),rr=dx*dx+dy*dy+dz*dz;
      if(rr<=KernelSize2&&rr>=ALMOSTZERO){
        const float fac=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,rr);
        const float gx=fac*dx,gy=fac*dy,gz=fac*dz;const auto sj=ToTSymMatrix3f(Sigmac[j]);
        const double pw=double(PorePressc[i])+double(PorePressc[j]);
        const double xx=double(si.xx)+sj.xx-pw,yy=double(si.yy)+sj.yy-pw,zz=double(si.zz)+sj.zz-pw;
        const double xy=double(si.xy)+sj.xy,xz=double(si.xz)+sj.xz,yz=double(si.yz)+sj.yz;
        // Match production's float displacement/factor/product, double coefficient,
        // actual double->float stress reads, and each-pair float acceleration store.
        const auto pair=TDouble3(coeff*(xx*gx+xy*gy+xz*gz),coeff*(yy*gy+xy*gx+yz*gz),coeff*(zz*gz+yz*gy+xz*gx));
        r.input=r.input+pair;r.rounded.x+=float(pair.x);r.rounded.y+=float(pair.y);r.rounded.z+=float(pair.z);
        r.raw_input_abs+=fabs(pair.x)+fabs(pair.y)+fabs(pair.z);
        const auto grad=TDouble3(gx,gy,gz);const double tt=TrueTotal[i]+TrueTotal[j];
        r.continuous=r.continuous+grad*(coeff*tt);r.raw_continuous_abs+=coeff*fabs(tt)*(fabs(gx)+fabs(gy)+fabs(gz));
        r.e0=r.e0+grad*v0;const auto delta=Posc[j]-Posc[i];
        r.moment.a11+=v0*gx*delta.x;r.moment.a12+=v0*gx*delta.y;r.moment.a13+=v0*gx*delta.z;
        r.moment.a21+=v0*gy*delta.x;r.moment.a22+=v0*gy*delta.y;r.moment.a23+=v0*gy*delta.z;
        r.moment.a31+=v0*gz*delta.x;r.moment.a32+=v0*gz*delta.y;r.moment.a33+=v0*gz*delta.z;
      }
      const double rrDouble=BDot(d,d);
      if(rrDouble<=double(KernelSize2)&&rrDouble>=ALMOSTZERO){
        const auto grad=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rrDouble)));
        const auto corrected=BProduct(CorrMatc[i],grad);
        r.gp=r.gp+corrected*(v0*(double(PorePressc[j])-PorePressc[i]));
      }
    }
    return r;
  }
public:
  BalanceActual(unsigned dim,bool jitter):Feedback(dim,dim==2?9:27),Dimension(dim),Jitter(jitter){
    // Same nonperiodic cell recipe as immutable upl_p3_actual_r3.cpp:41-69.
    // Direct Feedback include avoids that .cpp's nested main/undef collision.
    DynamicPorePressure=true;DynamicPoreConductivity=false;SoilCte.HydraulicConductivity=1e-5f;
    Gravity=dim==2? TFloat3(-4,0,-8):TFloat3(-4,2,-8);CSP.gravity=Gravity;
    KernelH=.25f;KernelSize=.5f;KernelSize2=.25f;Eta2=.000625f;
    CSP.kernelh=KernelH;CSP.kernelsize=KernelSize;CSP.kernelsize2=KernelSize2;CSP.eta2=Eta2;CSP.kwend=fsph::GetKernelWendland_Ctes(Simulate2D,KernelH);
    InitPorosityObserverCpu();std::vector<Point> particles;unsigned id=0;
    for(int y=(dim==3?-1:0);y<=(dim==3?1:0);y++)for(int z=-1;z<=1;z++)for(int x=-1;x<=1;x++){
      tdouble3 p=TDouble3(1.+x*Dp,dim==3?1.+y*Dp:0.,1.+z*Dp);
      if(jitter){const unsigned axis=id%dim;const double offset=(id%2?1.:-1.)*Dp/8.;if(axis==0)p.x+=offset;else if(axis==1&&dim==3)p.y+=offset;else p.z+=offset;}
      particles.push_back({p,id++,0});
    }
    Np=unsigned(particles.size());CaseNp=CaseNfluid=Np;NpfPer=NpbPer=0;Require(Np<=CpuParticlesSize,"Balance patch exceeds arrays");
    const tuint3 nc=TUint3(4,dim==3?3:1,3);const unsigned ncell=nc.x*nc.y*nc.z,code=DCEL_GetCode(27,2,2);
    for(auto& p:particles){const unsigned cx=unsigned(p.x.x/KernelSize),cy=dim==3?unsigned(p.x.y/KernelSize):0,cz=unsigned(p.x.z/KernelSize);Require(cx<nc.x&&cy<nc.y&&cz<nc.z,"Balance cell outside table");p.key=cx+nc.x*(cy+nc.y*cz);}
    std::stable_sort(particles.begin(),particles.end(),[](const Point& a,const Point& b){return a.key<b.key;});
    Cells.assign(2*(ncell+1),0);unsigned cursor=0;for(unsigned c=0;c<=ncell;c++){while(cursor<Np&&particles[cursor].key<c)cursor++;Cells[ncell+1+c]=cursor;}
    DivData=MakeDivDataCpu(1,nc,TUint3(0),Cells.data(),KernelSize,code,TDouble3(0));TrueTotal.resize(Np);
    const auto referencePoint=dim==2? TDouble3(1,0,1):TDouble3(1,1,1);const auto gravity=ToTDouble3(Gravity);
    for(unsigned p=0;p<Np;p++){
      const auto& a=particles[p];Posc[p]=a.x;Idpc[p]=a.id;Codec[p]=CODE_TYPE_FLUID;
      const unsigned cx=a.key%nc.x,cy=(a.key/nc.x)%nc.y,cz=a.key/(nc.x*nc.y);Dcellc[p]=DCEL_Cell(code,cx,cy,cz);
      Require(DCEL_Cellx(code,Dcellc[p])==cx&&DCEL_Celly(code,Dcellc[p])==cy&&DCEL_Cellz(code,Dcellc[p])==cz,"Packed cell round-trip failed");
      PoroJc[p]=1;PoroThetac[p]=0;Velrhopc[p]=TFloat4(0,0,0,RhopZero);Kplasticc[p]=0;
      const double gx=BDot(gravity,a.x-referencePoint),pressure=65536.+double(SoilCte.PoreWaterRho)*gx;
      TrueTotal[p]=-double(RhopZero)*gx;const double effective=TrueTotal[p]+pressure;
      Sigmac[p]=TSymMatrix3d(effective,0,0,effective,0,effective);PorePressc[p]=float(pressure);PorePress0c[p]=0;PorePressRatec[p]=1234567.f;
      CorrMatc[p]=TMatrix3d();FSNormalc[p]=TFloat3(0);FSTypec[p]=FST_Inner;PosDivc[p]=0;HydroMechLoadAcec[p]=TFloat3(0);
    }
  }
  unsigned Check(std::ostream& rows,std::ostream& moments,std::ostream& summary){
    PreInteraction_Forces();ComputeFreeSurfaceTracking();
    const auto parameters=StInterparmsc(Np,Npb,NpbOk,DivData,Dcellc,Posc,Velrhopc,Idpc,Codec,Pressc,PorePressc,PorePressRatec,FSTypec,FSNormalc,nullptr,CorrMatc,Arc,Acec,nullptr,SHIFT_None,nullptr,nullptr,nullptr,Sigmac,Rsigmac,nullptr);
    StInterResultc result{};Interaction_Forces_ct(parameters,result);
    const auto gravity=ToTDouble3(Gravity);const double rho=RhopZero,rhow=SoilCte.PoreWaterRho,gamma=rhow*BNorm(gravity),k=SoilCte.HydraulicConductivity;
    std::vector<Reference> references;for(unsigned p=0;p<Np;p++)references.push_back(Assemble(p));
    ComputeDynamicPorePressureRateCpu();double maxImplementation=0,maxClosure=0,maxPhysical=0,maxFlux=0;unsigned bitExact=0;
    for(unsigned p=0;p<Np;p++){
      const auto& r=references[p];const auto actual=ToTDouble3(Acec[p]),rounded=ToTDouble3(r.rounded),physical=actual+gravity;
      const auto e0term=r.e0*(2.*TrueTotal[p]/rho),firstMoment=gravity-BProduct(r.moment,gravity);
      const auto storedField=r.input-r.continuous,pairRounding=rounded-r.input,implementation=actual-rounded;
      const auto decomposed=e0term+firstMoment+storedField+pairRounding+implementation;
      const double forceBound=(32.*FLT_EPSILON+4096.*DBL_EPSILON)*(std::max)(1.,r.raw_input_abs);
      const double decompositionBound=4096.*DBL_EPSILON*(std::max)(1.,r.raw_continuous_abs+BNorm(e0term)+BNorm(firstMoment)+BNorm(gravity));
      const double forceError=BNorm(implementation),closureError=BNorm(physical-decomposed);
      Require(std::isfinite(forceError)&&forceError<=forceBound,"Actual force differs from independent float-pair all-particle assembly");
      Require(std::isfinite(closureError)&&closureError<=decompositionBound,"E0/first-moment/rounding decomposition identity failed");
      Require(PoroJc[p]==1&&PoroThetac[p]==0&&Kplasticc[p]==0&&std::isfinite(PorePressRatec[p]),"Conditional balance state changed or became nonfinite");
      if(!memcmp(Acec+p,&r.rounded,sizeof(tfloat3)))bitExact++;
      const auto q=(r.gp+actual*rhow)*(-k/gamma),qGradientDefect=(r.gp-gravity*rhow)*(-k/gamma),qAcceleration=physical*(-k*rhow/gamma);
      Require(std::isfinite(BNorm(q)),"Nonfinite descriptive flux");
      maxImplementation=(std::max)(maxImplementation,forceError/forceBound);maxClosure=(std::max)(maxClosure,closureError/decompositionBound);maxPhysical=(std::max)(maxPhysical,BNorm(physical));maxFlux=(std::max)(maxFlux,BNorm(q));
      const char* pointRole=Idpc[p]==(Dimension==2?4u:13u)? "center":"patch_edge";
      rows<<Dimension<<','<<Jitter<<','<<Idpc[p]<<','<<pointRole<<','<<TrueTotal[p]<<','<<PorePressc[p]<<','<<Sigmac[p].xx;
      BVector(rows,actual);BVector(rows,rounded);rows<<','<<forceError<<','<<forceBound;BVector(rows,physical);BVector(rows,e0term);BVector(rows,firstMoment);BVector(rows,storedField);BVector(rows,pairRounding);BVector(rows,implementation);
      rows<<','<<closureError<<','<<decompositionBound;BVector(rows,r.gp);BVector(rows,q);BVector(rows,qGradientDefect);BVector(rows,qAcceleration);rows<<','<<PorePressRatec[p]<<'\n';
      moments<<Dimension<<','<<Jitter<<','<<Idpc[p]<<','<<pointRole;BVector(moments,r.e0);moments<<','<<r.moment.a11<<','<<r.moment.a12<<','<<r.moment.a13<<','<<r.moment.a21<<','<<r.moment.a22<<','<<r.moment.a23<<','<<r.moment.a31<<','<<r.moment.a32<<','<<r.moment.a33<<','<<r.raw_input_abs<<','<<r.raw_continuous_abs<<'\n';
    }
    summary<<Dimension<<','<<Jitter<<','<<Np<<','<<bitExact<<','<<maxImplementation<<','<<maxClosure<<','<<maxPhysical<<','<<maxFlux<<'\n';PosInteraction_Forces();return Np;
  }
};

int main(int argc,char** argv){
  try{
    Require(argc==3&&std::string(argv[1])=="--out","Use --out NEW_DIRECTORY");const fs::path out(argv[2]);Require(!fs::exists(out),"Retained output protected");
    AppInfo.ConfigRunPaths(argv[0]);AppInfo.ConfigOutput(true,false,out.string(),"data");AppInfo.LogInit((out/"Run.out").string());
    std::ofstream rows(out/"balance.csv"),moments(out/"moments.csv"),summary(out/"summary.csv");for(auto* f:{&rows,&moments,&summary})*f<<std::setprecision(17);
    rows<<"dimension,jitter,native_id,point_role,T_scalar_true,p_float,sigma_double_xx,Ace_x,Ace_y,Ace_z,reference_Ace_x,reference_Ace_y,reference_Ace_z,force_error,force_bound,physical_as_x,physical_as_y,physical_as_z,E0_term_x,E0_term_y,E0_term_z,first_moment_residual_x,first_moment_residual_y,first_moment_residual_z,stored_field_quantization_x,stored_field_quantization_y,stored_field_quantization_z,pair_rounding_x,pair_rounding_y,pair_rounding_z,implementation_x,implementation_y,implementation_z,decomposition_error,decomposition_bound,Gp_x,Gp_y,Gp_z,q_x,q_y,q_z,q_gradient_defect_x,q_gradient_defect_y,q_gradient_defect_z,q_physical_acceleration_x,q_physical_acceleration_y,q_physical_acceleration_z,descriptive_complete_rate\n";
    moments<<"dimension,jitter,native_id,point_role,E0_x,E0_y,E0_z,M11,M12,M13,M21,M22,M23,M31,M32,M33,raw_input_abs,raw_continuous_abs\n";
    summary<<"dimension,jitter,native_rows,float_pair_reference_bit_exact_nodes,max_force_error_over_bound,max_decomposition_error_over_bound,max_continuous_equilibrium_acceleration_residual,max_descriptive_flux\n";
    unsigned cases=0,checks=0;for(unsigned dim:{2u,3u})for(bool jitter:{false,true}){BalanceActual a(dim,jitter);checks+=a.Check(rows,moments,summary);cases++;}
    Require(cases==4&&checks==72,"Balance diagnostic coverage differs");for(auto* f:{&rows,&moments,&summary}){f->flush();Require(bool(*f),"Diagnostic write failed");}
    std::ofstream done(out/"completion.json");done<<"{\"passed\":true,\"stage\":\"upl_gravity_balance_r1\",\"cases\":4,\"native_rows\":72,\"actual_force_ct_calls\":4,\"actual_complete_rate_calls\":4,\"independent_float_pair_momentum_reference\":true,\"prior_rounding_and_decomposition_bounds\":true,\"continuous_equilibrium_residual_is_descriptive\":true,\"production_modified\":false,\"public_guard_changed\":false,\"wall_tested\":false,\"actual_Run_or_ComputeStep_called\":false,\"completed_physical_steps\":0,\"mechanical_hydrostatic_well_balance_accepted\":false,\"physical_acceptance\":false}\n";done.flush();Require(bool(done),"Completion write failed");
    std::cout<<"Hydrostatic force/decomposition diagnostic passed implementation checks only.\n";return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Balance diagnostic failed; preserve output\n";return 2;}
}
