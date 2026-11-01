// r2 setup repair: refresh real-native Dcell only; production RunPeriodic regenerates old images.
// Private variable-k actual integration component, not a formal physical benchmark.
// Reuse unchanged binary schema and independent half comparator only; no constant-k theory is used.
#define main RetainedSpatialMain
#include "upl_p3_spatial_wave_harness_r2.cpp"
#undef main
#include <iterator>
template<class T> struct InitialCopy{
  std::vector<T> value;InitialCopy(const T* p,unsigned n):value(p,p+n){}
  void Restore(T* p)const{memcpy(p,value.data(),value.size()*sizeof(T));}
  bool Equal(const T* p)const{return !memcmp(p,value.data(),value.size()*sizeof(T));}
};
class VariableWave:public JSphCpuSingle{
  static constexpr unsigned Native=512;
  static constexpr double DeltaJ=1./32768.,Ck=1./1024.,InitialPressure=128.;
  std::vector<tdouble3> X;
  std::vector<double> InitialK;
  bool ZeroK=false,SwitchOn=false;
  double Cu0=0,Pstar=0,Ustar=0,E0=0,MaxEnergy=0,MaxCfl=0,MaxDiffusion=0,MaxGradientCfl=0,MinBound=DBL_MAX;
  double InitialMinK=DBL_MAX,InitialMaxK=0,FinalKChange=0;
  double SourceRMS=0,ChainRMS=0,PressureChainRMS=0,AceChainRMS=0,SourceBudget=0,AuditReferenceError=0;
  std::ofstream Ledger,Policy,Modes;
  struct Grad{tdouble3 j=TDouble3(0),p=TDouble3(0),lx=TDouble3(0);double lp=0,da=0;};
  static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
  static double Norm(tdouble3 a){return sqrt(Dot(a,a));}
  static tdouble3 Mul(const tmatrix3d& c,tdouble3 g){return TDouble3(c.a11*g.x+c.a12*g.y+c.a13*g.z,c.a21*g.x+c.a22*g.y+c.a23*g.z,c.a31*g.x+c.a32*g.y+c.a33*g.z);}
  std::vector<unsigned> Ids()const{
    std::vector<unsigned> ids(Native,UINT_MAX);unsigned n=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){
      Check(CODE_IsFluid(Codec[p])&&Idpc[p]<Native&&ids[Idpc[p]]==UINT_MAX,"Real native identity changed");ids[Idpc[p]]=p;n++;
    }
    Check(n==Native&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Real native count/exclusions changed");return ids;
  }
  double Gamma()const{return double(SoilCte.PoreWaterRho)*9.80665;}
  double Alpha()const{return 1./((1.-double(SoilCte.Porosity))*Ck);}
  double IndependentK(unsigned p,bool enabled)const{
    const double k0=SoilCte.HydraulicConductivity;return !enabled||k0==0?k0:k0*exp(Alpha()*(PoroJc[p]-1.));
  }
  Grad Gradient(unsigned i,bool withPressure,bool withAce=false)const{
    Grad a;const double V0=double(MassFluid)/RhopZero;
    // Independent O(N^2) endpoint/initial-audit assembly; not a production-cell-order equality claim.
    for(unsigned j=0;j<Np;j++)if(CODE_IsFluid(Codec[j])){
      const auto d=TDouble3(Posc[i].x-Posc[j].x,0,Posc[i].z-Posc[j].z);const double rr=Dot(d,d);
      if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;
      const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr))),gi=Mul(CorrMatc[i],g);
      const double Vj=V0*PoroJc[j];a.j=a.j+gi*(Vj*(PoroJc[j]-PoroJc[i]));
      if(withPressure){
        const double dp=double(PorePressc[i])-PorePressc[j],w=Vj*Dot(d,gi+Mul(CorrMatc[j],g))/(rr+double(Eta2));
        a.p=a.p-gi*(Vj*dp);a.lp+=w*dp;a.lx=a.lx+d*w;
      }
      if(withAce)a.da+=Vj*Dot(ToTDouble3(Acec[j])-ToTDouble3(Acec[i]),gi);
    }return a;
  }
  Frame Snapshot()const{
    Frame f;f.time=TimeStep;f.rows.resize(Native);const auto ids=Ids();
    for(unsigned id=0;id<Native;id++){
      const unsigned p=ids[id];const auto x=Posc[p];const auto v=Velrhopc[p];const auto s=Sigmac[p];const auto n=FSNormalc[p],load=HydroMechLoadAcec[p];
      f.rows[id]={x.x,x.y,x.z,double(v.x),double(v.y),double(v.z),double(PorePressc[p]),double(PorePress0c[p]),PoroJc[p],PoroThetac[p],s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,double(Kplasticc[p]),double(FSTypec[p]),double(n.x),double(n.y),double(n.z),double(PosDivc[p]),double(load.x),double(load.y),double(load.z),double(v.w)};
      for(double z:f.rows[id])Check(std::isfinite(z),"Nonfinite native serialization");
    }return f;
  }
  double Energy()const{
    double sum=0;
    for(unsigned p:Ids()){
      double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);const auto s=Sigmac[p];const auto v=Velrhopc[p];
      const double tr=s.xx+s.yy+s.zz,m=tr/3.,dev=(s.xx-m)*(s.xx-m)+(s.yy-m)*(s.yy-m)+(s.zz-m)*(s.zz-m)+2*(s.xy*s.xy+s.xz*s.xz+s.yz*s.yz);
      sum+=V*(.5*rho*(double(v.x)*v.x+double(v.y)*v.y+double(v.z)*v.z)+dev/(4*SoilCte.ModulusG)+tr*tr/(18*SoilCte.ModulusK)+n*double(PorePressc[p])*PorePressc[p]/(2*SoilCte.PoreWaterBulkModulus));
    }return sum;
  }
  void Guard(double dt,bool forceStats){
    const auto ids=Ids();const double kw=SoilCte.PoreWaterBulkModulus,rhow=SoilCte.PoreWaterRho,m=double(SoilCte.ModulusK)+4.*double(SoilCte.ModulusG)/3.;
    double cu2max=0,dmax=0,minMargin=DBL_MAX;
    for(unsigned p:ids){
      double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);const double J=PoroJc[p],ki=GetDynamicConductivityCpu(p),kr=IndependentK(p,SwitchOn),b=kw/n;
      Check(std::isfinite(J)&&J>1-double(SoilCte.Porosity)&&fabs(J-1)<=1e-4&&n>0&&n<1&&V>0&&rho>0,"Physical J/n/V/rho domain failed");
      Check(fabs((1-n)*J-(1-double(SoilCte.Porosity)))<=5e-13,"Original solid-volume identity failed");
      Check(std::isfinite(ki)&&ki>=0&&fabs(ki-kr)<=5e-13*(std::max)(fabs(kr),DBL_MIN),"Actual current conductivity law failed");
      Check(Kplasticc[p]==0&&PorePress0c[p]==0&&Velrhopc[p].w>=RhopOutMin&&Velrhopc[p].w<=RhopOutMax,"Original elastic/p0/passive-rho screen failed");
      const auto s=Sigmac[p];const auto v=Velrhopc[p];for(double z:{n,V,rho,ki,s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,double(v.x),double(v.y),double(v.z),double(PorePressc[p]),double(PorePressRatec[p]),PoroThetac[p],Posc[p].x,Posc[p].y,Posc[p].z})Check(std::isfinite(z),"Nonfinite native state");
      const double cu2=(m+b)/rho,D=b*ki/Gamma(),cfl=sqrt(cu2)*dt/KernelH,diff=D*dt/(double(KernelH)*KernelH);
      if(ki>0){const double margin=rho*b/(m+b)-rhow;Check(margin>64*DBL_EPSILON*(std::max)(rho,rhow),"Original strict continuous decay domain failed");minMargin=(std::min)(minMargin,margin);}
      Check(cfl<=.01&&diff<=.01&&(D==0||dt<=double(PoreDtSafety)*KernelH*KernelH/D),"Original coupled CFL/pore-step budget failed");
      MaxCfl=(std::max)(MaxCfl,cfl);MaxDiffusion=(std::max)(MaxDiffusion,diff);cu2max=(std::max)(cu2max,cu2);dmax=(std::max)(dmax,D);
    }
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){
      Check(Idpc[p]<Native,"Periodic ID outside native set");const unsigned q=ids[Idpc[p]];
      Check(!memcmp(PoroJc+p,PoroJc+q,8)&&!memcmp(PoroThetac+p,PoroThetac+q,8)&&!memcmp(PorePressc+p,PorePressc+q,4)&&!memcmp(PorePress0c+p,PorePress0c+q,4)&&!memcmp(PorePressRatec+p,PorePressRatec+q,4)&&!memcmp(Velrhopc+p,Velrhopc+q,sizeof(tfloat4))&&!memcmp(Sigmac+p,Sigmac+q,sizeof(tsymatrix3d)),"Periodic full-state owner equality failed");
    }
    const double e=Energy()/E0;Check(std::isfinite(e)&&e<=1.1,"Original energy1.1 screen failed");MaxEnergy=(std::max)(MaxEnergy,e);
    if(forceStats){
      double wave,pore;GetDynamicStepScalesCpu(wave,pore);const double wr=double(KernelH)/((std::max)(sqrt(cu2max),VelMax*10.)+double(KernelH)*ViscDtMax),pr=dmax?double(PoreDtSafety)*KernelH*KernelH/dmax:DBL_MAX;
      Check(fabs(wave-wr)<=64*DBL_EPSILON*(std::max)(fabs(wr),DBL_MIN)&&fabs(pore-pr)<=64*DBL_EPSILON*(std::max)(fabs(pr),DBL_MIN),"Current-state necessary step policy reference failed");
      const double force=AceMax?sqrt(double(KernelH)/AceMax):DBL_MAX,bound=(std::min)(double(CFLnumber)*(std::min)(force,wave),pore);
      Check(dt<=bound&&double(DtMin)<=bound,"Original necessary force/wave/pore bound failed");MinBound=(std::min)(MinBound,bound);
      const double legacy=double(CFLnumber)*(std::min)(force,double(KernelH)/((std::max)(Cs0,VelMax*10.)+double(KernelH)*ViscDtMax));
      Check(dt<=legacy&&fabs(FixedDt->GetDtError(false))<=1e-14,"Original drained-step/fixed-error budget failed");
      Policy<<Nstep<<','<<TimeStep<<','<<dt<<','<<wave<<','<<pore<<','<<bound<<','<<minMargin<<','<<e<<','<<FixedDt->GetDtError(false)<<'\n';
    }
  }
  void SaveLedger(double dt){
    const auto ids=Ids();double pm=0,jm=0,totalV=0,solidV=0,vmode=0,pmode=0,umode=0,minK=DBL_MAX,maxK=0,maxChange=0;
    const double kw=SoilCte.PoreWaterBulkModulus,k0=SoilCte.HydraulicConductivity,kWave=2*acos(-1.)/Lx;
    for(unsigned id=0;id<Native;id++){
      const unsigned p=ids[id];double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);const double ki=GetDynamicConductivityCpu(p),kr=IndependentK(p,SwitchOn);
      const auto gj=Gradient(p,false).j,gk=gj*(SwitchOn?Alpha()*ki:0.);const double uk=kw/n*Norm(gk)/Gamma(),courant=uk*dt/KernelH;
      Check(std::isfinite(uk)&&courant<=.01,"Predeclared necessary gradient-k advection screen failed");MaxGradientCfl=(std::max)(MaxGradientCfl,courant);
      if(k0>0)maxChange=(std::max)(maxChange,fabs(ki-InitialK[id])/k0);
      Ledger<<Nstep<<','<<TimeStep<<','<<id<<','<<PoroJc[p]<<','<<n<<','<<V<<','<<rho<<','<<ki<<','<<kr<<','<<gj.x<<','<<gj.y<<','<<gj.z<<','<<uk<<','<<courant<<'\n';
      pm+=PorePressc[p]/Native;jm+=PoroJc[p]/Native;totalV+=V;solidV+=(1-n)*V;
      vmode+=2.*Velrhopc[p].x*sin(kWave*X[id].x)/Native;pmode+=2.*PorePressc[p]*cos(kWave*X[id].x)/Native;umode+=2.*(Posc[p].x-X[id].x)*sin(kWave*X[id].x)/Native;
      minK=(std::min)(minK,ki);maxK=(std::max)(maxK,ki);
    }
    FinalKChange=maxChange;Modes<<Nstep<<','<<TimeStep<<','<<vmode<<','<<pmode<<','<<umode<<','<<pm<<','<<jm<<','<<totalV<<','<<solidV<<','<<minK<<','<<maxK<<','<<maxChange<<','<<Energy()/E0<<'\n';
  }
  void InitialAudit(const fs::path& out){
    const auto before=Snapshot();const unsigned np=Np,nb=Npb,step=Nstep;const double time=TimeStep,pre=SymplecticDtPre,last=LastDt,fe=FixedDt->GetDtError(false);const auto stage=InterStep;
    const InitialCopy<tdouble3> pos(Posc,np);const InitialCopy<unsigned> ids(Idpc,np),fs(FSTypec,np);const InitialCopy<typecode> code(Codec,np);
    const InitialCopy<tfloat4> vel(Velrhopc,np);const InitialCopy<tsymatrix3d> sig(Sigmac,np);const InitialCopy<tmatrix3d> corr(CorrMatc,np);
    const InitialCopy<float> p(PorePressc,np),p0(PorePress0c,np),rate(PorePressRatec,np),plastic(Kplasticc,np),pd(PosDivc,np);
    const InitialCopy<double> j(PoroJc,np),theta(PoroThetac,np);const InitialCopy<tfloat3> norm(FSNormalc,np),load(HydroMechLoadAcec,np);
    // Before the first actual force, AceMax is undefined: do not read or restore it.
    Interaction_Forces(INTERSTEP_SymPredictor);const auto native=Ids();const bool saved=DynamicPoreConductivity;
    DynamicPoreConductivity=true;ComputeDynamicPorePressureRateCpu();std::vector<float> on(PorePressRatec,PorePressRatec+Np);
    DynamicPoreConductivity=false;ComputeDynamicPorePressureRateCpu();std::vector<float> off(PorePressRatec,PorePressRatec+Np);DynamicPoreConductivity=saved;
    std::ofstream csv(out/"initial_source.csv");csv<<std::setprecision(17)<<"native_id,rate_ON,rate_constant_OFF,rate_difference,reference_difference,reference_error,reference_limit,chain_pressure_rate,chain_acceleration_rate,chain_total_rate\n";
    double sd=0,ch=0,pc=0,ac=0,budget=0;const double kw=SoilCte.PoreWaterBulkModulus,rhow=SoilCte.PoreWaterRho,k0=SoilCte.HydraulicConductivity;
    for(unsigned id=0;id<Native;id++){
      const unsigned p1=native[id];double n,V,rho;GetPorosityFeedbackStateCpu(p1,n,V,rho);const auto g=Gradient(p1,true,true);
      const double ki=IndependentK(p1,true),s=kw/n/Gamma(),pchain=s*Alpha()*ki*Dot(g.j,g.p),achain=s*Alpha()*ki*rhow*Dot(g.j,ToTDouble3(Acec[p1]));
      const double reference=s*((ki-k0)*(g.lp-Dot(g.p,g.lx)+rhow*g.da))+pchain+achain,diff=double(on[p1])-off[p1];
      const double b=32*FLT_EPSILON*(std::max)({1.,fabs(double(on[p1])),fabs(double(off[p1]))})+1e-6,err=fabs(diff-reference);
      Check(err<=2*b,"Actual initial same-state source difference differs from independent complete product");
      sd+=diff*diff;ch+=(pchain+achain)*(pchain+achain);pc+=pchain*pchain;ac+=achain*achain;budget=(std::max)(budget,b);AuditReferenceError=(std::max)(AuditReferenceError,err);
      csv<<id<<','<<on[p1]<<','<<off[p1]<<','<<diff<<','<<reference<<','<<err<<','<<2*b<<','<<pchain<<','<<achain<<','<<pchain+achain<<'\n';
    }
    SourceRMS=sqrt(sd/Native);ChainRMS=sqrt(ch/Native);PressureChainRMS=sqrt(pc/Native);AceChainRMS=sqrt(ac/Native);SourceBudget=budget;
    if(SwitchOn&&!ZeroK)Check(SourceRMS>100*budget&&ChainRMS>100*budget&&PressureChainRMS>10*budget&&AceChainRMS>10*budget,"Predeclared actual gradient-k pressure/acceleration source effect is empty");
    csv.flush();Check(bool(csv),"Initial source audit write failed");PosInteraction_Forces();
    Check(Np==np&&Npb==nb&&Nstep==step&&TimeStep==time&&SymplecticDtPre==pre&&LastDt==last&&pos.Equal(Posc)&&ids.Equal(Idpc)&&code.Equal(Codec),"Additional initial force changed immutable identity/clock/positions");
    vel.Restore(Velrhopc);sig.Restore(Sigmac);corr.Restore(CorrMatc);p.Restore(PorePressc);p0.Restore(PorePress0c);rate.Restore(PorePressRatec);plastic.Restore(Kplasticc);pd.Restore(PosDivc);j.Restore(PoroJc);theta.Restore(PoroThetac);norm.Restore(FSNormalc);load.Restore(HydroMechLoadAcec);fs.Restore(FSTypec);InterStep=stage;
    Check(FixedDt->GetDtError(false)==fe,"Additional initial force changed fixed-step telemetry");
    const auto after=Snapshot();Check(before.time==after.time&&!memcmp(before.rows.data(),after.rows.data(),Native*sizeof(Row))&&corr.Equal(CorrMatc),"Covered initial physical-state/26-column rollback was not exact");
    // Retain the now-defined real force statistics; no fabricated initial force values.
  }
public:
  VariableWave(){PorosityObserver=PorosityFeedback=DynamicPorePressure=true;DynamicPoreConductivityCk=Ck;}
  void Execute(const JSphCfgRun* cfg,JLog2* log,unsigned steps,bool smoke,bool zero,bool enabled){
    ZeroK=zero;SwitchOn=enabled;DynamicPoreConductivity=enabled;AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);
    Check(SoilCte.HydraulicConductivity==float(.0001),"Original seed k0 changed");if(zero)SoilCte.HydraulicConductivity=0;
    LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Check(HydroMech&&Simulate2D&&TStep==STEP_Symplectic&&!CaseNpb&&CaseNfluid==Native&&PeriX&&PeriZ&&!PeriY&&!DynamicPoreWall,"Wrong actual periodic geometry");
    Check(!CaseNmoving&&!CaseNfloat&&!HourglassCpu&&!Shifting&&!Damping&&!RelaxZones&&!InOut&&!AccInput&&!NoPenetration,"Unsupported auxiliary path");
    Check(Dp==Lx/32&&MapRealSize.x==Lx&&MapRealSize.z==Lz&&TimeStep==0&&FixedDt,"Wrong exact periodic seed/domain/clock");
    Check(SoilCte.ModulusK==89478488.f&&SoilCte.ModulusG==134217728.f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==67108864.f&&SoilCte.Porosity==.25f&&RhopZero==2048&&double(MassFluid)/RhopZero==Dp*Dp&&KernelH==float(1.8*Dp),"Changed manufactured material");
    const double dt=SymplecticDtPre;Check(dt==pow(2.,-24)||dt==pow(2.,-25),"Undeclared actual step");const bool half=dt==pow(2.,-25);
    Check(smoke?(!half&&steps==2):(zero?(!half&&steps==16):(steps==(half?1024u:512u))),"Undeclared bounded steps");
    const unsigned samples=smoke?3:(zero?17:257),stride=smoke||zero?1:steps/256;const double stop=steps*dt,kWave=2*acos(-1.)/Lx;
    const auto initial=Ids();X.resize(Native);InitialK.resize(Native);std::vector<bool> lattice(Native,false);
    for(unsigned id=0;id<Native;id++){
      const unsigned p=initial[id];const auto x=Posc[p];const double ix=x.x/Dp-.5,iz=x.z/Dp-.5;
      Check(ix==round(ix)&&iz==round(iz)&&ix>=0&&ix<32&&iz>=0&&iz<16&&x.y==0,"Initial material tensor changed");
      const unsigned key=unsigned(ix)+32*unsigned(iz);Check(!lattice[key],"Duplicate material coordinate");lattice[key]=true;X[id]=x;
      const double phase=kWave*x.x;Posc[p].x=x.x+DeltaJ/kWave*sin(phase);PoroJc[p]=1.+DeltaJ*cos(phase);PoroThetac[p]=0;
      PorePressc[p]=float(InitialPressure*cos(phase));PorePress0c[p]=PorePressRatec[p]=0;Velrhopc[p]=TFloat4(float(Amplitude*sin(phase)),0,0,RhopZero);
      Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;
    }
    // Rebuild real production cells and periodic images after prescribing the compatible material map.
    // Existing periodic images may legally lie outside DomReal; they are not new natives.
    for(unsigned p:initial)LoadDcellParticles(1,Codec+p,Posc+p,Dcellc+p);
    RunCellDivide(true);
    const auto mapped=Ids();std::ofstream material(fs::path(cfg->DirOut)/"native_ids.csv");material<<std::setprecision(17)<<"native_id,X,Y,Z,initial_x,initial_y,initial_z,initial_J,initial_k\n";
    for(unsigned id=0;id<Native;id++){const unsigned p=mapped[id];InitialK[id]=GetDynamicConductivityCpu(p);InitialMinK=(std::min)(InitialMinK,InitialK[id]);InitialMaxK=(std::max)(InitialMaxK,InitialK[id]);material<<id<<','<<X[id].x<<','<<X[id].y<<','<<X[id].z<<','<<Posc[p].x<<','<<Posc[p].y<<','<<Posc[p].z<<','<<PoroJc[p]<<','<<InitialK[id]<<'\n';}
    if(SwitchOn&&!ZeroK)Check(InitialMinK/double(SoilCte.HydraulicConductivity)<.97&&InitialMaxK/double(SoilCte.HydraulicConductivity)>1.03,"Initial spatial conductivity range is empty");
    Cu0=sqrt((double(SoilCte.ModulusK)+4.*double(SoilCte.ModulusG)/3.+double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity)/RhopZero);
    Pstar=double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity*Amplitude/Cu0;Ustar=Amplitude/(Cu0*kWave);E0=Energy();Check(E0>0,"Initial energy is zero");
    Policy.open(fs::path(cfg->DirOut)/"endpoint_policy.csv");Policy<<std::setprecision(17)<<"step,time_s,used_dt_s,wave_scale_s,pore_scale_s,complete_bound_s,min_RH_margin,energy_ratio,cumulative_fixed_error_s\n";
    Ledger.open(fs::path(cfg->DirOut)/"ledger.csv");Ledger<<std::setprecision(17)<<"step,time_s,native_id,J,n,V,rho,actual_k,reference_k,endpoint_GJ_x,endpoint_GJ_y,endpoint_GJ_z,necessary_gradient_speed,gradient_dt_over_h\n";
    Modes.open(fs::path(cfg->DirOut)/"modes.csv");Modes<<std::setprecision(17)<<"step,time_s,v_material_sine,p_material_cosine,u_from_X_material_sine,mean_p,mean_J,total_volume,solid_volume,min_k,max_k,max_k_change_over_initial_k0,energy_ratio\n";
    Guard(dt,false);InitialAudit(fs::path(cfg->DirOut));
    std::ofstream bin(fs::path(cfg->DirOut)/"physical.bin",std::ios::binary);const unsigned header[3]={Native,Columns,samples};bin.write(reinterpret_cast<const char*>(header),12);WriteFrame(bin,Snapshot());SaveLedger(dt);unsigned saved=1;
    for(unsigned it=0;it<steps;it++){
      InterStep=INTERSTEP_SymPredictor;const double used=ComputeStep_Sym();Check(used==dt,"Actual production locked step changed");
      RunCellDivide(true);TimeStep+=used;LastDt=used;UpdateMaxValues();Nstep++;Guard(dt,true);
      if((it+1)%stride==0){WriteFrame(bin,Snapshot());SaveLedger(dt);saved++;}
    }
    Check(Nstep==steps&&TimeStep==stop&&saved==samples&&!PoroJPrec,"Incomplete actual variable-k trajectory");
    if(!smoke&&SwitchOn&&!ZeroK)Check(FinalKChange>1e-4,"Final time conductivity evolution is empty");
    bin.flush();Ledger.flush();Policy.flush();Modes.flush();material.flush();Check(bin&&Ledger&&Policy&&Modes&&material,"Actual output write failed");
    std::ofstream done(fs::path(cfg->DirOut)/"complete.json");done<<std::setprecision(17)<<"{\"passed\":true,\"actual_ComputeStep_Sym\":true,\"Nx\":32,\"Nz\":16,\"native_ids\":512,\"steps\":"<<steps<<",\"samples\":"<<samples<<",\"dt_actual\":"<<dt<<",\"actual_end_s\":"<<TimeStep<<",\"smoke\":"<<(smoke?"true":"false")<<",\"k0\":"<<(zero?"true":"false")<<",\"conductivity_switch\":"<<(enabled?"true":"false")<<",\"Ck\":"<<Ck<<",\"cu\":"<<Cu0<<",\"Pstar\":"<<Pstar<<",\"Ustar\":"<<Ustar<<",\"initial_pressure_amplitude_Pa\":128,\"initial_J_amplitude\":"<<DeltaJ<<",\"initial_min_k\":"<<InitialMinK<<",\"initial_max_k\":"<<InitialMaxK<<",\"final_max_k_change_over_initial_k0\":"<<FinalKChange<<",\"max_energy_ratio\":"<<MaxEnergy<<",\"max_coupled_CFL\":"<<MaxCfl<<",\"max_Ddt_h2\":"<<MaxDiffusion<<",\"max_necessary_gradient_k_CFL\":"<<MaxGradientCfl<<",\"min_endpoint_bound_s\":"<<MinBound<<",\"initial_source_difference_RMS_Pa_s\":"<<SourceRMS<<",\"initial_chain_RMS_Pa_s\":"<<ChainRMS<<",\"initial_pressure_chain_RMS_Pa_s\":"<<PressureChainRMS<<",\"initial_acceleration_chain_RMS_Pa_s\":"<<AceChainRMS<<",\"initial_max_single_rate_roundoff_budget_Pa_s\":"<<SourceBudget<<",\"initial_source_reference_max_error_Pa_s\":"<<AuditReferenceError<<",\"extra_initial_force_audits\":1,\"extra_initial_option_rate_calls\":2,\"initial_covered_state_and_26columns_rollback_exact\":true,\"first_audit_initialized_real_force_statistics\":true,\"automatic_force_stage_counts_directly_observed\":false,\"constant_coefficient_theory_used_as_truth\":false,\"finite_Kw_conditional_storage_claimed_exact_water_mass\":false,\"manufactured_nonequilibrium_initial_state\":true,\"physical_acceptance\":false}\n";done.flush();Check(bool(done),"Actual completion write failed");
  }
};
static void Effect(const fs::path& on,const fs::path& off,double measuredHalf,const fs::path& target){
  Check(!fs::exists(target)&&std::isfinite(measuredHalf)&&measuredHalf>=0,"New effect label and finite actual half error required");
  std::ifstream a(on,std::ios::binary),b(off,std::ios::binary);unsigned ha[3],hb[3];a.read(reinterpret_cast<char*>(ha),12);b.read(reinterpret_cast<char*>(hb),12);
  Check(a&&b&&!memcmp(ha,hb,12)&&ha[0]==512&&ha[1]==26&&ha[2]==257,"Wrong option-effect binary schema");double mp=0,mv=0,mu=0;
  for(unsigned i=0;i<257;i++){const auto x=ReadFrame(a,512),y=ReadFrame(b,512);Check(x.time==y.time&&x.time==i/8388608.,"Actual option clocks differ");double ps=0,vs=0;
    for(unsigned id=0;id<512;id++){const auto& u=x.rows[id];const auto& v=y.rows[id];if(!i)Check(!memcmp(u.data(),v.data(),26*8),"Initial mapped physical fields differ");ps+=pow(u[6]-v[6],2);double du=0;for(unsigned k=0;k<3;k++){du+=pow(u[k]-v[k],2);vs+=pow(u[k+3]-v[k+3],2);}mu=(std::max)(mu,1000*sqrt(du));}
    mp=(std::max)(mp,sqrt(ps/512));mv=(std::max)(mv,sqrt(vs/512));
  }
  Check(a.peek()==std::char_traits<char>::eof()&&b.peek()==std::char_traits<char>::eof(),"Unexpected option output length");const double required=(std::max)(.001,10*measuredHalf);Check(mp>required,"ON-vs-constant actual pressure effect not resolved above measured time error");
  std::ofstream out(target);out<<std::setprecision(17)<<"{\"passed\":true,\"samples\":257,\"native_ids\":512,\"columns\":26,\"max_pressure_RMS_Pa\":"<<mp<<",\"required_pressure_effect_Pa\":"<<required<<",\"measured_half_pressure_RMS_Pa\":"<<measuredHalf<<",\"max_material_displacement_mm\":"<<mu<<",\"max_velocity_RMS\":"<<mv<<",\"comparison_kind\":\"same_initial_ON_vs_constant_OFF_not_half_or_theory\",\"physical_acceptance\":false}\n";out.flush();Check(bool(out),"Effect check write failed");
}
int main(int argc,char** argv){try{
  if(argc==7&&std::string(argv[1])=="--half")return RetainedSpatialMain(argc,argv);
  if(argc==6&&std::string(argv[1])=="--effect"){Effect(argv[2],argv[3],std::stod(argv[4]),argv[5]);return 0;}
  Check(argc>10&&std::string(argv[1])=="--job","Use --job STEPS SMOKE KZERO SWITCHON solverargs; --half A B PSTAR USTAR NEWJSON; --effect ON OFF HALF_MAXP NEWJSON");
  const unsigned steps=unsigned(std::stoul(argv[2]));const bool smoke=std::string(argv[3])=="1",zero=std::string(argv[4])=="1",enabled=std::string(argv[5])=="1";
  for(unsigned i=3;i<=5;i++)Check(std::string(argv[i])=="0"||std::string(argv[i])=="1","Invalid Boolean CLI");
  AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=6;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());cfg.Cpu=true;
  Check(!fs::exists(cfg.DirOut),"Retained actual output protected");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
  VariableWave wave;wave.Execute(&cfg,AppInfo.LogPtr(),steps,smoke,zero,enabled);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Variable-k actual integration rejected; preserve output\n";return 2;}}

