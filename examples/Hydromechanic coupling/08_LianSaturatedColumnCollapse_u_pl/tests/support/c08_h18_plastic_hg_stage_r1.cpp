// Private bounded CPU-stage feasibility; no public physical TU or native exporter changes.
#define main c08_plastic_hg_unused_rhs_main
#include "../outputs/c08_h18_plastic_hg_stage_r1_build/shared.inc"
#undef main
#include "FunSoilMaterial.h"
#include "../outputs/c08_h18_plastic_hg_stage_r1_build/step_helpers.inc"
#include "c08_h18_plastic_hg_stage_r1.hpp"
#include <cfenv>
#include <xmmintrin.h>
static unsigned ArithmeticMode(){const unsigned csr=_mm_getcsr();Need(std::numeric_limits<double>::is_iec559&&std::fegetround()==FE_TONEAREST&&(csr&((1u<<15)|(1u<<6)|(3u<<13)))==0,"Binary64 RN/gradual-underflow environment required; never change physical FP flags");return csr;}

struct FixedScope{
  JDsFixedDt*& slot;JDsFixedDt* saved;std::unique_ptr<JDsFixedDt> fresh;
  explicit FixedScope(JDsFixedDt*& p):slot(p),saved(p),fresh(new JDsFixedDt(.000005)){
    Need(saved&&saved->GetFile().empty()&&Bits(saved->GetFixedValue(),.000005)&&fresh->GetFile().empty()&&Bits(fresh->GetFixedValue(),.000005),"Independent constant FixedDt required");slot=fresh.get();}
  ~FixedScope(){slot=saved;}FixedScope(const FixedScope&)=delete;FixedScope& operator=(const FixedScope&)=delete;
};
struct Cpu22{
  unsigned id=0,fs=0;tdouble3 pos=TDouble3(0),sk=TDouble3(0),si=TDouble3(0);
  tfloat3 vel=TFloat3(0),kk=TFloat3(0),ij=TFloat3(0),normal=TFloat3(0),load=TFloat3(0);
  float rhop=0,kap=0,p=0,p0=0,excess=0,posdiv=0;double j=0,n=0,theta=0,V=0,rho=0,k=0;
};
struct EndState{std::vector<Cpu22> body;double time=0,last=0,symdt=0,dterror=0;unsigned step=0;};
struct Pred{fsoil::Result material{};double gamma=0;};
struct NodeStage{tfloat3 ace0=TFloat3(0),ace1=TFloat3(0);float rate0=0,rate1=0;double mass=0,fx=0,fz=0,fxerr=0,fzerr=0,commitx=0,commitz=0,commitbudgetx=0,commitbudgetz=0;};
struct ManualResult{std::vector<StepState> n,fn,h,fh,raw,next;c08hg::Trial predictor,full;std::vector<NodeStage> an,ah;std::array<unsigned,2> preMode{},fullMode{};};
class PlasticStageProbe:public StepProbe{
  unsigned restores=0,baselineCalls=0,manualSteps=0,forceCalls=0,extraDarcy=0,shadowCalls=0,materialBits=0,nodeRows=0,bodyRows=0,offFieldBits=0,hgStages=0;
  std::ofstream stageFile,nodeFile,bodyFile,hgFile,focusFile,offFile,workFile;
  std::vector<float> fixedP0;
  void P0Guard()const{Need(fixedP0.size()==Original,"Immutable P0 map unavailable");const auto map=StageMap();for(unsigned id=2060;id<Original;id++)Need(Bits(PorePress0c[map[id]],fixedP0[id]),"Original inherited P0 changed ID="+std::to_string(id));}
  std::vector<StepState> Capture(const char* name,double offset,bool force,std::ofstream& file,const std::vector<StepState>* base){P0Guard();auto out=StepProbe::Capture(name,offset,force,file,base);P0Guard();return out;}
  void RestoreBranch(const Snapshot& a){Restore(a);fixedP0.assign(Original,0.f);for(unsigned id=2060;id<Original;id++)fixedP0[id]=a.p0[a.byid[id]];P0Guard();start=a.time;completed=a.completed;sourcePart=a.part;dt=.000005;LastDt=dt;SymplecticDtPre=dt;restores++;
    Need(FixedDt&&FixedDt->GetFile().empty()&&Bits(FixedDt->GetFixedValue(),dt),"Fresh FixedDt scope not installed");}
  EndState Body()const{
    ArithmeticMode();Need(!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec&&!Acec&&!Rsigmac,"Completed allocation required for CPU22-equivalent map");
    const auto map=StageMap();EndState s;s.body.resize(Original);s.time=TimeStep;s.step=unsigned(Nstep);s.last=LastDt;s.symdt=SymplecticDtPre;s.dterror=FixedDt->GetDtError(false);
    Need(Finite(s.dterror)&&!Bits(s.dterror,-DBL_MAX)&&s.dterror<=1e-14,"Actual signed fixed-dt error exceeds original gate");
    for(unsigned id=2060;id<Original;id++){const unsigned i=map[id];auto& r=s.body[id];const auto v=Velrhopc[i];const auto z=Sigmac[i];r.id=id;r.fs=FSTypec[i];r.pos=Posc[i];r.vel=TFloat3(v.x,v.y,v.z);r.rhop=v.w;r.kap=Kplasticc[i];r.p=PorePressc[i];r.p0=PorePress0c[i];Need(Bits(r.p0,fixedP0[id]),"Completed immutable P0 mismatch");r.excess=float(r.p-r.p0);r.j=PoroJc[i];r.theta=PoroThetac[i];r.normal=FSNormalc[i];r.load=HydroMechLoadAcec[i];r.posdiv=PosDivc[i];r.sk=TDouble3(z.xx,z.yy,z.zz);r.si=TDouble3(z.xy,z.yz,z.xz);r.kk=TFloat3(float(z.xx),float(z.yy),float(z.zz));r.ij=TFloat3(float(z.xy),float(z.yz),float(z.xz));GetPorosityFeedbackStateCpu(i,r.n,r.V,r.rho);r.k=GetDynamicConductivityCpu(i);
      Need(Finite(r.pos)&&Finite(r.vel)&&Finite(r.sk)&&Finite(r.si)&&Finite(r.p)&&Finite(r.j)&&Finite(r.kap)&&r.kap>=0&&r.j>1.-double(SoilCte.Porosity)&&r.n>0&&r.n<1&&r.V>0&&r.rho>0&&r.k>0&&Bits(r.rhop,float(r.rho)),"Completed soil safety/ledger differs");Need((r.fs!=2&&r.fs!=3)||r.p<=0,"Completed positive free-surface pressure");Need(r.pos.x>=-4e-8&&r.pos.z>=-4e-8,"Original plane geometry gate failed");
    }return s;
  }
  template<class X>void SameField(const X& a,const X& b,unsigned id,const char* name){Need(Bits(a,b),"Manual OFF mismatch part="+std::to_string(sourcePart)+" ID="+std::to_string(id)+" field="+name);offFieldBits++;}
  void CompareOff(const EndState& a,const EndState& b){
    for(unsigned id=2060;id<Original;id++){const auto& x=a.body[id];const auto& y=b.body[id];
#define C08_SAME(f) SameField(x.f,y.f,id,#f)
      C08_SAME(id);C08_SAME(pos);C08_SAME(vel);C08_SAME(kk);C08_SAME(ij);C08_SAME(normal);C08_SAME(load);C08_SAME(rhop);C08_SAME(kap);C08_SAME(p);C08_SAME(p0);C08_SAME(excess);C08_SAME(sk);C08_SAME(si);C08_SAME(fs);C08_SAME(j);C08_SAME(n);C08_SAME(theta);C08_SAME(V);C08_SAME(rho);C08_SAME(k);C08_SAME(posdiv);
#undef C08_SAME
    }
    Need(Bits(a.time,b.time)&&a.step==b.step&&Bits(a.last,b.last)&&Bits(a.symdt,b.symdt)&&Bits(a.dterror,b.dterror),"Manual OFF outer clock/LastDt/SymDt/signed dterror mismatch");
    offFile<<sourcePart<<','<<a.time<<','<<a.step<<','<<a.dterror<<','<<Soil<<",22,110000,1\n";
  }
  std::vector<Pred> Predict(double width,bool half,const std::vector<StepState>& n){
    const auto map=StageMap();std::vector<Pred> out(Original);const bool trigger=PartBegin&&StrainSoftening;
    for(unsigned id=2060;id<Original;id++){const unsigned i=map[id];Need(half?SigmaPrec!=NULL:SigmaPrec==NULL,"Material base time layer differs");const auto& b=(half?SigmaPrec[i]:Sigmac[i]);Need(Bits(b,n[id].sigma)&&Bits(Kplasticc[i],n[id].kappa),"Material predictor base/history differs");const auto r=Rsigmac[i];tsymatrix3d trial;
      trial.xx=b.xx+r.xx*width;trial.yy=b.yy+r.yy*width;trial.zz=b.zz+r.zz*width;trial.xy=b.xy+r.xy*width;trial.yz=b.yz+r.yz*width;trial.xz=b.xz+r.xz*width;
      auto& z=out[id];const fsoil::State input={{trial.xx,trial.yy,trial.zz,trial.xy,trial.yz,trial.xz},n[id].kappa};z.material=fsoil::EvaluateMaterial(input,SoilCte,DPCtes,StrainSoftening,trigger);shadowCalls++;
      const auto& m=z.material;Need(fsoil::CommitAllowed(m.status)&&Finite(m.trial_q)&&Finite(m.returned_q),"Original same-input material shadow rejected");
      switch(m.status){case fsoil::Status::Elastic:z.gamma=1;break;case fsoil::Status::Smooth:Need(m.trial_q>0,"Smooth gamma has zero trial q");z.gamma=m.returned_q/m.trial_q;break;case fsoil::Status::Apex:case fsoil::Status::TensionRepair:z.gamma=0;break;default:Need(false,"Illegal gamma status");}
      Need(Finite(z.gamma)&&z.gamma>=0&&z.gamma<=1,"Actual return gamma outside [0,1]; no clipping");
    }return out;
  }
  void Match(const std::vector<Pred>& p,const std::vector<StepState>& n,const std::vector<StepState>& committed,bool predictor){
    for(unsigned id=2060;id<Original;id++){const auto& r=p[id].material;const auto& z=committed[id];const tsymatrix3d expected={r.state.stress.xx,r.state.stress.xy,r.state.stress.xz,r.state.stress.yy,r.state.stress.yz,r.state.stress.zz};
      Need(Bits(z.sigma,expected)&&Bits(z.kappa,predictor?n[id].kappa:r.state.kappa),"Actual six-stress/kappa material commit differs ID="+std::to_string(id));materialBits+=7;}
  }
  std::vector<c08hg::Input> HgInput(const std::vector<Pred>& p)const{
    const auto map=StageMap();std::vector<c08hg::Input> in;in.reserve(Soil);
    for(unsigned id=2060;id<Original;id++){const unsigned i=map[id];double n,V,rho;GetPorosityFeedbackStateCpu(i,n,V,rho);const double mass=(double(MassFluid)/double(RhopZero))*(double(RhopZero)-double(SoilCte.PoreWaterRho)+double(SoilCte.PoreWaterRho)*PoroJc[i]);
      Need(mass>0&&Finite(mass)&&Bits(V,(double(MassFluid)/double(RhopZero))*PoroJc[i]),"HG actual volume/inertia qualification differs");in.push_back({id,Posc[i].x,Posc[i].z,double(Velrhopc[i].x),double(Velrhopc[i].z),V,mass,p[id].gamma});}return in;
  }
  c08hg::Trial AddHg(c08hg::State& model,const std::vector<Pred>& p,double width,bool full,std::vector<NodeStage>& nodes,std::array<unsigned,2>& arithmeticMode){
    arithmeticMode[0]=ArithmeticMode();auto trial=model.Evaluate(HgInput(p),width,full);arithmeticMode[1]=ArithmeticMode();Need(trial.force.size()==Soil,"HG force ID coverage differs");const auto map=StageMap();
    for(unsigned k=0;k<Soil;k++){const unsigned id=2060+k,i=map[id];const auto& f=trial.force[k];Need(f.id==id,"HG force not in original native-ID order");auto& z=nodes[id];double n,V,rho;GetPorosityFeedbackStateCpu(i,n,V,rho);z.mass=(double(MassFluid)/double(RhopZero))*(double(RhopZero)-double(SoilCte.PoreWaterRho)+double(SoilCte.PoreWaterRho)*PoroJc[i]);z.fx=f.x;z.fz=f.z;z.fxerr=f.error_x;z.fzerr=f.error_z;
      const double ax=double(z.ace0.x)+f.x/z.mass,az=double(z.ace0.z)+f.z/z.mass;Acec[i].x=float(ax);Acec[i].z=float(az);Need(Bits(Acec[i].y,z.ace0.y),"2D HG changed y acceleration");
      const double ex=fabs(double(Acec[i].x)-ax),ez=fabs(double(Acec[i].z)-az);Need(ex<=FLT_EPSILON*fabs(ax)+std::numeric_limits<float>::denorm_min()&&ez<=FLT_EPSILON*fabs(az)+std::numeric_limits<float>::denorm_min(),"HG float acceleration commit exceeds original cast bound");
      z.commitx=z.mass*(double(Acec[i].x)-double(z.ace0.x));z.commitz=z.mass*(double(Acec[i].z)-double(z.ace0.z));
      z.commitbudgetx=f.error_x+z.mass*ex+RoundoffGamma(12)*(fabs(z.commitx)+fabs(f.x)+z.mass*(fabs(double(Acec[i].x))+fabs(double(z.ace0.x))));
      z.commitbudgetz=f.error_z+z.mass*ez+RoundoffGamma(12)*(fabs(z.commitz)+fabs(f.z)+z.mass*(fabs(double(Acec[i].z))+fabs(double(z.ace0.z))));
      Need(Finite(z.commitbudgetx)&&Finite(z.commitbudgetz)&&fabs(z.commitx-f.x)<=z.commitbudgetx&&fabs(z.commitz-f.z)<=z.commitbudgetz,"HG float force-commit reconciliation failed");
    }
    // Original Interaction_Forces already evaluated a no-HG Darcy result. Discard
    // that result and rerun the COMPLETE original wrapper, including wall Ace.
    ComputeDynamicPorePressureRateCpu();extraDarcy++;AceMax=ComputeAceMax(Np-Npb,Acec+Npb,Codec+Npb);hgStages++;return trial;
  }
  void StageNodes(const char* mode,unsigned update,const char* stage,const std::vector<Pred>& p,const std::vector<NodeStage>& nodes,bool on){
    const auto map=StageMap();for(unsigned id=2060;id<Original;id++){const unsigned i=map[id];const auto& m=p[id].material;const auto& x=nodes[id];nodeFile<<sourcePart<<','<<mode<<','<<update<<','<<stage<<','<<start<<','<<completed<<','<<id<<','<<unsigned(m.status)<<','<<unsigned(m.reason)<<','<<m.trial_q<<','<<m.returned_q<<','<<p[id].gamma<<",1,"<<on<<','<<x.ace0.x<<','<<x.ace0.z<<','<<x.ace1.x<<','<<x.ace1.z<<','<<x.fx<<','<<x.fz<<','<<x.fxerr<<','<<x.fzerr<<','<<x.mass<<','<<x.commitx<<','<<x.commitz<<','<<x.commitbudgetx<<','<<x.commitbudgetz<<','<<x.rate0<<','<<x.rate1<<','<<PorePress0c[i]<<'\n';nodeRows++;}
  }
  void TrialLog(unsigned update,const char* stage,const c08hg::Trial& trial,const std::array<unsigned,2>& arithmeticMode){const auto& z=trial.stats;
    hgFile<<sourcePart<<','<<update<<','<<stage<<','<<start<<','<<completed<<','<<trial.generation<<','<<z.rows<<','<<z.kept<<','<<z.born<<','<<z.dead<<','<<z.returning<<','<<z.condition<<','<<z.lambda_upper<<','<<z.dt_ratio<<','<<z.min_r<<','<<z.max_omega<<','<<z.spin_bound<<','<<z.Eold<<','<<z.Enew<<','<<z.Edead<<','<<z.work_rows<<','<<z.work_nodes<<','<<z.loading_loss<<','<<z.rotation_change<<','<<z.ledger<<','<<z.ledger_bound<<','<<z.net_x<<','<<z.net_x_bound<<','<<z.net_z<<','<<z.net_z_bound<<','<<z.torque<<','<<z.torque_bound<<','<<z.max_error_ratio<<','<<z.known_constant_receivers<<','<<z.known_constant_rows<<','<<arithmeticMode[0]<<','<<arithmeticMode[1]<<'\n';
    for(const auto& f:trial.focus)focusFile<<sourcePart<<','<<update<<','<<stage<<','<<f.id_i<<','<<f.id_j<<','<<f.r<<','<<f.D<<','<<f.gamma<<','<<f.omega<<','<<f.eold_x<<','<<f.eold_z<<','<<f.enew_x<<','<<f.enew_z<<','<<f.u_x<<','<<f.u_z<<','<<f.I_x<<','<<f.I_z<<','<<f.work<<','<<f.work_bound<<','<<f.loading_loss<<','<<f.rotation_change<<','<<f.ledger<<','<<f.ledger_bound<<'\n';
  }
  void SamePrimary(const std::vector<StepState>& a,const std::vector<StepState>& b,const char* label)const{for(unsigned id=2060;id<Original;id++)Need(Bits(a[id].pos,b[id].pos)&&Bits(a[id].vel,b[id].vel)&&Bits(a[id].sigma,b[id].sigma)&&Bits(a[id].kappa,b[id].kappa)&&Bits(a[id].j,b[id].j)&&Bits(a[id].p,b[id].p),std::string(label)+" ID="+std::to_string(id));P0Guard();}
  void SourceUpdateGate(const ManualResult& r)const{
    for(unsigned id=2060;id<Original;id++){const auto& b=r.n[id];const auto& fn=r.fn[id];const auto& h=r.h[id];const auto& f=r.fh[id];const auto& raw=r.raw[id];const auto& next=r.next[id];
      double jp=b.j;jp+=dt*.5*b.j*fn.theta;const float pp=float(double(b.p)+dt*.5*double(fn.rate));double jc=b.j;jc+=dt*f.j*f.theta;const float pc=float(double(b.p)+dt*double(f.rate));
      Need(Bits(h.j,jp)&&Bits(h.p,pp)&&Bits(raw.j,jc)&&Bits(raw.p,pc)&&Bits(next.j,raw.j),"Original J/p source operation bits differ");const float cap=(next.fs==2||next.fs==3)&&raw.p>0?0.f:raw.p;Need(Bits(next.p,cap),"Original completed positive-only FS cap differs");
      const double solid=1.-double(SoilCte.Porosity),kw=SoilCte.PoreWaterBulkModulus,c=(f.j-solid)/kw,dj=raw.j-b.j,dp=double(next.p)-b.p,hyd=dt*f.j*f.hydraulic,dcap=c*(double(next.p)-raw.p);
      const double erate=double(f.rate)-f.literal,ep=(double(raw.p)-b.p)-dt*double(f.rate),ej=dj-dt*f.j*f.theta,esource=c*f.literal+f.j*f.theta-f.j*f.hydraulic;
      const double fp=ej+c*ep+dt*c*erate+dt*esource,defect=dj+c*dp-hyd-dcap,closure=defect-fp;
      const double mag=fabs(raw.j)+fabs(b.j)+fabs(dj)+fabs(c*dp)+fabs(hyd)+fabs(dcap)+fabs(ej)+fabs(c*ep)+fabs(dt*c*erate)+fabs(dt*esource)+fabs(dt*f.j*f.theta)+fabs(dt*c*f.literal)+fabs(dt*f.j*f.hydraulic);
      Need(Finite(closure)&&fabs(closure)<=RoundoffGamma(128)*mag+128*std::numeric_limits<double>::denorm_min(),"Original pressure/J balance arithmetic closure failed");
    }
  }
  ManualResult Manual(const char* mode,unsigned update,c08hg::State* model){
    start=TimeStep;completed=unsigned(Nstep);dt=SymplecticDtPre;const bool on=model!=NULL;ManualResult r;r.an.resize(Original);r.ah.resize(Original);r.n=Capture("restored_n",0,false,stageFile,NULL);bool scratch=false;
    std::vector<Pred> pn,ph;double ddtp=0,ddtc=0;
    try{DemDtForce=dt*.5f;scratch=true;Interaction_Forces(INTERSTEP_SymPredictor);forceCalls++;const auto mapn=StageMap();for(unsigned id=2060;id<Original;id++){auto& n=r.an[id];n.ace0=Acec[mapn[id]];n.rate0=PorePressRatec[mapn[id]];n.mass=(double(MassFluid)/double(RhopZero))*(double(RhopZero)-double(SoilCte.PoreWaterRho)+double(SoilCte.PoreWaterRho)*PoroJc[mapn[id]]);}
      pn=Predict(dt*.5,false,r.n);if(on)r.predictor=AddHg(*model,pn,dt*.5,false,r.an,r.preMode);ddtp=DtVariable(false);r.fn=Capture("force_n",0,true,stageFile,NULL);SamePrimary(r.n,r.fn,"Force_n changed soil primary");
      for(unsigned id=2060;id<Original;id++){r.an[id].ace1=r.fn[id].ace;r.an[id].rate1=r.fn[id].rate;}
      ComputeSymplecticPre(dt);r.h=Capture("half_before_divide",dt*.5,false,stageFile,&r.n);Match(pn,r.n,r.h,true);StageNodes(mode,update,"n",pn,r.an,on);PosInteraction_Forces();scratch=false;
      DemDtForce=dt;RunCellDivide(true);const auto hdiv=Capture("half_after_divide",dt*.5,false,stageFile,&r.n);SameJP(r.h,hdiv,"Half divide changed J/p");
      scratch=true;Interaction_Forces(INTERSTEP_SymCorrector);forceCalls++;const auto maph=StageMap();for(unsigned id=2060;id<Original;id++){auto& n=r.ah[id];n.ace0=Acec[maph[id]];n.rate0=PorePressRatec[maph[id]];n.mass=(double(MassFluid)/double(RhopZero))*(double(RhopZero)-double(SoilCte.PoreWaterRho)+double(SoilCte.PoreWaterRho)*PoroJc[maph[id]]);}
      ph=Predict(dt,true,r.n);if(on)r.full=AddHg(*model,ph,dt,true,r.ah,r.fullMode);ddtc=DtVariable(true);r.fh=Capture("force_h",dt*.5,true,stageFile,&r.n);SamePrimary(hdiv,r.fh,"Force_h changed soil primary");
      for(unsigned id=2060;id<Original;id++){r.ah[id].ace1=r.fh[id].ace;r.ah[id].rate1=r.fh[id].rate;}
      ComputeSymplecticCorr(dt);r.raw=Capture("raw_full",dt,false,stageFile,NULL);Match(ph,r.n,r.raw,false);StageNodes(mode,update,"h",ph,r.ah,on);PosInteraction_Forces();scratch=false;
      SymplecticDtPre=(std::min)(ddtp,ddtc);RunCellDivide(true);r.next=Capture("completed_cap",dt,false,stageFile,NULL);Map();Clock();
    }catch(...){if(scratch)PosInteraction_Forces();throw;}
    Need(Bits(ddtp,dt)&&Bits(ddtc,dt)&&Bits(SymplecticDtPre,dt),"Original necessary fixed timestep changed");SourceUpdateGate(r);
    TimeStep+=dt;LastDt=dt;Nstep++;Need(Bits(TimeStep,start+dt)&&unsigned(Nstep)==completed+1,"Exactly one outer scalar clock update required");
    manualSteps++;return r;
  }
  void OnBody(unsigned update,const ManualResult& r,const EndState& end){
    double toy=r.full.stats.work_nodes,wactual=0,wfloat=0,wpre=0,massTerm=0;
    for(unsigned id=2060;id<Original;id++){const auto& n=r.n[id];const auto& z=end.body[id];const auto& a=r.ah[id];const double vxpre=float(double(n.vel.x)+(double(r.fh[id].ace.x)+Gravity.x)*dt),vzpre=float(double(n.vel.z)+(double(r.fh[id].ace.z)+Gravity.z)*dt);
      const double bcx=.5*(double(n.vel.x)+z.vel.x),bcz=.5*(double(n.vel.z)+z.vel.z),bpx=.5*(double(n.vel.x)+vxpre),bpz=.5*(double(n.vel.z)+vzpre);
      wactual+=dt*(bcx*a.fx+bcz*a.fz);wfloat+=dt*(bcx*a.commitx+bcz*a.commitz);wpre+=dt*(bpx*a.fx+bpz*a.fz);const double massNext=(double(MassFluid)/double(RhopZero))*(double(RhopZero)-double(SoilCte.PoreWaterRho)+double(SoilCte.PoreWaterRho)*z.j);massTerm+=.5*(massNext-a.mass)*(double(z.vel.x)*z.vel.x+double(z.vel.z)*z.vel.z);
      Need(Bits(z.p0,fixedP0[id])&&z.kap>=n.kappa,"Original plastic history nondecrease differs");
      bodyFile<<sourcePart<<','<<update<<','<<end.time<<','<<end.step<<','<<id<<','<<z.pos.x<<','<<z.pos.z<<','<<z.vel.x<<','<<z.vel.z<<','<<z.p<<','<<z.p0<<','<<z.j<<','<<z.n<<','<<z.V<<','<<z.rho<<','<<z.k<<','<<z.kap<<','<<z.fs<<','<<z.sk.x-z.p<<','<<z.sk.y-z.p<<','<<z.sk.z-z.p<<','<<z.si.x<<','<<z.si.y<<','<<z.si.z<<','<<z.vel.x-vxpre<<','<<z.vel.z-vzpre<<','<<massNext-a.mass<<'\n';bodyRows++;
    }
    workFile<<sourcePart<<','<<update<<','<<start<<','<<completed<<','<<toy<<','<<wactual<<','<<wfloat<<','<<wpre<<','<<wactual-toy<<','<<wactual-wpre<<','<<wfloat-wactual<<','<<massTerm<<','<<r.full.stats.Enew-r.full.stats.Eold+wactual+r.full.stats.loading_loss+r.full.stats.Edead-r.full.stats.rotation_change<<'\n';
  }
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,const std::array<Snapshot,2>& states){
    Need(states[0].part==38&&states[0].completed==2076001&&states[1].part==76&&states[1].completed==2152001,"Only exact P38/P76 completed native states admitted");ArithmeticMode();AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();RunGravityPreloadHandoffCpu();FreePartsInit();
    Need(IsGravityPreloadHandoff()&&GravityPreload&&!GravityPreloadElasticSource&&!GravityPreloadReleased&&unsigned(Nstep)==2000000&&!GravityPreloadKeepBedOverlap&&GravityPreloadBedIds.empty(),"Original schema2 source handoff differs");RunGravityPreloadRelease();Map();
    Need(GravityPreloadReleased&&GravityPreloadActualStep==2000000&&GravityPreloadIdBegin==1805&&GravityPreloadIdCount==255&&DynamicPorePressure&&PorosityFeedback&&DynamicPoreWall&&DynamicPoreConductivity&&DynamicPoreConductivityCk==2.&&HydroMechFreeSeepage&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilDamping&&!PoreShepardRegularization,"Original release controls differ");
    Need(Simulate2D&&!PeriActive&&OmpThreads==1&&TKernel==KERNEL_Wendland&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundSlipModec&&SoilStressRateGradCorr&&!SoilBoundaryDerivativeSPR&&!HourglassCpu&&!SoilHourglassXi&&!WithFloating&&!UseDEM&&!AccInput&&!Shifting&&!Damping&&TDensity==DDT_None&&NoPenetration&&TMdbc2==MDBC2_NoPen&&UseDynamicPorePlaneContact(),"Original physical facility scope differs");
    Need(!CaseNmoving&&!CaseNfloat&&!RelaxZones&&!InOut&&!ViscoTime&&!DDTRamp.x&&ArtificialStress&&ArtificialStressCoef==.3f&&ArtificialStressExp==2.55f&&TVisco==VISCO_Artificial&&Visco==.1f&&Dp==.04&&KernelH==.072f&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==.0002f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&Gravity==TFloat3(0,0,-9.81f)&&FixedDt&&FixedDt->GetFixedValue()==.000005,"Original AS/AV/material/dt differs");
    code.resize(Original);wallnormal.resize(Original);slip.resize(Original);for(unsigned q=0;q<Np;q++){code[Idpc[q]]=Codec[q];if(q<Npb){wallnormal[Idpc[q]]=BoundNormalc[q];slip[Idpc[q]]=BoundSlipModec[q];}}Roles();
    const pf::path out(cfg->DirOut);stageFile.open("NUL");nodeFile.open(out/"stage_nodes.csv");bodyFile.open(out/"on_completed_soil.csv");hgFile.open(out/"hg_stages.csv");focusFile.open(out/"hg_focus.csv");offFile.open(out/"manual_off.csv");workFile.open(out/"actual_work.csv");
    for(auto f:{&stageFile,&nodeFile,&bodyFile,&hgFile,&focusFile,&offFile,&workFile}){Need(bool(*f),"Fresh bounded CSV unavailable");*f<<std::setprecision(17);}
    stageFile<<"stage,solver_time_s,stage_offset_s,solver_completed_step,native_id,x,y,z,vx,vy,vz,J,p_Pa,P0_Pa,FS,theta_s_1,PRE_owned,J_saved_base,p_saved_base,actual_rate_Pa_s,literal_rate_Pa_s,D_s_1,Acex,Acey,Acez,sigma_xx,sigma_yy,sigma_zz,sigma_xy,sigma_yz,sigma_xz,kappa,Rsigma_xx,Rsigma_yy,Rsigma_zz,Rsigma_xy,Rsigma_yz,Rsigma_xz\n";
    nodeFile<<"source_part,mode,update,force_stage,source_time_s,source_completed_step,native_id,same_input_shadow_status,reason,qtrial,qreturn,gamma,actual_sigma_kappa_match,HG_on,Ace0x,Ace0z,Ace1x,Ace1z,HG_Fx,HG_Fz,HG_Fx_bound,HG_Fz_bound,stage_mass,committed_deltaFx,committed_deltaFz,commit_budgetFx,commit_budgetFz,discarded_original_rate,new_full_rate,P0\n";
    bodyFile<<"source_part,update,time_s,completed_step,native_id,x,z,vx,vz,p,P0,J,n,V,rho,k,kappa,FS,total_xx,total_yy,total_zz,total_xy,total_yz,total_xz,contact_dvx,contact_dvz,mass_next_minus_force_h\n";
    hgFile<<"source_part,update,force_stage,time_s,completed_step,generation,directed_rows,kept,born,dead,returning,condition,lambda_upper,dt_ratio,min_r,max_omega,spin_bound,Eold,Enew,Edead,work_rows,work_nodes,loading_loss,rotation_change,ledger,ledger_bound,net_Fx,net_Fx_bound,net_Fz,net_Fz_bound,torque,torque_bound,max_error_ratio,known_constant_receivers,known_constant_rows,mxcsr_before,mxcsr_after\n";
    focusFile<<"source_part,update,stage,id_i,id_j,r,D,gamma,omega,eold_x,eold_z,enew_x,enew_z,u_x,u_z,I_x,I_z,work,work_bound,loss,rotation_change,ledger,ledger_bound\n";
    offFile<<"source_part,time_s,completed_step,signed_dterror_s,soil_IDs,CPU_export_equivalent_fields,field_bit_checks,all_match\n";
    workFile<<"source_part,update,source_time_s,source_completed_step,toy_drive_work,actual_midvelocity_work,float_committed_force_work,pre_contact_midvelocity_work,actual_minus_toy,contact_work_difference,float_commit_work_difference,changing_mass_energy_term,observed_full_discrete_defect_not_gate\n";
    for(const auto& a:states){EndState original,manual;
      {FixedScope fixed(FixedDt);RestoreBranch(a);const double originaldt=ComputeStep_Sym();baselineCalls++;Need(Bits(originaldt,dt),"Original complete method dt differs");RunCellDivide(true);TimeStep+=originaldt;LastDt=originaldt;Nstep++;original=Body();}
      {FixedScope fixed(FixedDt);RestoreBranch(a);Manual("OFF",0,NULL);manual=Body();CompareOff(original,manual);}
      {FixedScope fixed(FixedDt);RestoreBranch(a);c08hg::Config hc{double(CSP.kernelh),double(KernelSize),double(CSP.kwend.bwen),double(SoilCte.ModulusG),.1,.000005,2060,Soil};c08hg::State model(hc);
        for(unsigned update=0;update<2;update++){const auto r=Manual("ON",update,&model);const auto end=Body();model.Commit(r.full,r.predictor);TrialLog(update,"n_uncommitted",r.predictor,r.preMode);TrialLog(update,"h_accepted",r.full,r.fullMode);OnBody(update,r,end);}
      }
    }
    Need(restores==6&&baselineCalls==2&&manualSteps==6&&forceCalls==12&&extraDarcy==8&&hgStages==8&&shadowCalls==60000&&materialBits==420000&&nodeRows==60000&&bodyRows==20000&&offFieldBits==220000,"Exact bounded stage coverage differs");
    for(auto f:{&stageFile,&nodeFile,&bodyFile,&hgFile,&focusFile,&offFile,&workFile}){f->flush();Need(bool(*f),"Complete bounded CSV write failed");}
    std::ofstream done(out/"completion.json");done<<"{\"stage\":\"c08_h18_plastic_hg_stage_r1\",\"passed\":true,\"source_parts\":[38,76],\"restores\":6,\"original_ComputeStep_Sym_calls\":2,\"manual_updates\":6,\"total_updates\":8,\"manual_force_calls\":12,\"baseline_force_calls_from_original_closed_method\":4,\"original_Darcy_calls\":16,\"extra_full_Darcy_calls\":8,\"HG_stage_trials\":8,\"duplicate_material_calls\":60000,\"actual_internal_material_calls_from_closed_loops\":80000,\"material_sigma_kappa_scalar_bit_checks\":420000,\"manual_OFF_CPU22_equivalent_field_checks\":220000,\"stage_node_rows\":60000,\"ON_completed_soil_rows\":20000,\"new_source_native_frames_decoded\":0,\"source_PRE_recomputed\":false,\"candidate_actual_trajectory_steps\":4,\"cold_release_history_is_original_restart\":false,\"physical_acceptance\":false,\"same_stage_Darcy_wrapper_invoked\":true,\"coupled_energy_or_second_order_qualified\":false,\"new_native22_export_qualified\":false,\"public_source_changed\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=9&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--native","Use --check --native CLOSED_FULL301 -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 ORIGINAL_SEED FRESH_OUT");const pf::path tests=pf::path(__FILE__).parent_path().parent_path(),native=pf::absolute(argv[3]),seed=tests/"outputs/c08_h18_as03n255_full3_r1/c08_h18_as03n255_full3_r1";Need(pf::equivalent(native,tests/"outputs/c08_h18_as03n255_full3_r1/native_r1"),"Only the original sealed full301 admitted");
  std::vector<Stamp> protectedFiles;for(const char* s:{"typed22.bin","typed22_layout.csv","clocks.csv","completion.json","bedkeep_metadata.json"})protectedFiles.emplace_back(native/s);for(const char* s:{".xml",".bi4","_Normals.nbi4"})protectedFiles.emplace_back(pf::path(seed.string()+s));protectedFiles.emplace_back(tests/"outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4");
  for(const char* s:{"c08_h18_as03n255_full3_r1.run.json","c08_h18_as03n255_full3_native_r1.check.json","c08_h18_as03n255_full3_review_r1.check.json","c08_h18_as03_step_r1_p38.check.json","c08_h18_as03_step_r1_p76.check.json","c08_h18_hg_saved_geometry_r1.check.json","c08_h18_plastic_hg_stage_r1.build.json"})protectedFiles.emplace_back(tests/"logs"/s);
  protectedFiles.emplace_back(pf::absolute(argv[0]));for(const char* s:{"DsphConfig.xml","ChronoEngine.dll","dsphchrono.dll","vcomp140.dll","msvcp140.dll","vcruntime140.dll","vcruntime140_1.dll"})protectedFiles.emplace_back(pf::absolute(argv[0]).parent_path()/s);
  const std::array<Snapshot,2> states={Snapshot(native,0),Snapshot(native,1)};AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&pf::absolute(cfg.CaseName)==pf::absolute(seed)&&pf::absolute(cfg.DirOut)==pf::absolute(tests/"outputs/c08_h18_plastic_hg_stage_r1")&&!pf::exists(cfg.DirOut),"Original seed and fresh closed prototype output required");
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");PlasticStageProbe probe;probe.Execute(&cfg,AppInfo.LogPtr(),states);for(const auto& p:protectedFiles)p.Check();return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Private stage prototype failed; preserve outputs\n";return 2;}}
