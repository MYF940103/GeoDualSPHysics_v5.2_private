// Fixed completed-state S_LP/Rgamma feasibility, never a TPI time trajectory.
#define main unused_original_as03_rhs_main
#include "../outputs/c08_tpi_state_r1_build/shared.inc"
#undef main
#include "../outputs/c08_tpi_state_r1_build/reference.inc"
static const unsigned FocusIds[4]={4953,4954,6767,6865};
static std::string WallDetail(const char* label,unsigned id,unsigned i,unsigned ok){std::ostringstream s;s<<label<<" native_id="<<id<<" i="<<i<<" NpbOk="<<ok;return s.str();}
struct StateRow{
  float p=0,rate=0,raw=0;double S=0,R=0,n=0,V=0,k=0,theta=0,J=0;unsigned fs=0,neighbors=0,fixedDonors=0;bool drained=false,admissible=false;
  tdouble3 position=TDouble3(0);tfloat3 velocity=TFloat3(0),ace=TFloat3(0);tsymatrix3f rs={0,0,0,0,0,0},art={0,0,0,0,0,0};tmatrix3d C={};
};
struct StateEvaluation{std::vector<StateRow> soil;unsigned npbok=0,active=0,inactive=0,ignored=0,badS=0,badRaw=0,positiveCap=0;bool proposalAllowed=true;double R2=0,Rmax=0,rate2=0;StateEvaluation():soil(Original){}};
static bool IsFocus(unsigned id){return std::find(std::begin(FocusIds),std::end(FocusIds),id)!=std::end(FocusIds);}
static std::array<double,3> SpectrumXZ(const tsymatrix3f& a){
  // Actual 2D tensor: retain the independent yy eigenvalue, do not discard it.
  Need(a.xy==0.f&&a.yz==0.f,"AS tensor is outside the exact 2D xz+yy spectral diagnostic");
  const double middle=.5*(double(a.xx)+a.zz),radius=std::hypot(.5*(double(a.xx)-a.zz),double(a.xz));
  std::array<double,3> v={{middle-radius,double(a.yy),middle+radius}};std::sort(v.begin(),v.end());return v;
}
class TpiStateProbe:public Probe{
  unsigned calls=0,baselineBits=0,soilRows=0,focusRows=0,pairRows=0,summaryRows=0,proposalCalls=0;
  double maxFloatRatio=0,maxExpandedRatio=0;
  StateEvaluation Evaluate(const Snapshot& a,const StateEvaluation* baseline,const std::vector<RhsReference>& reference,
    double kw,double rho,double gamma,std::ofstream& soil,std::ofstream& focus){
    Restore(a);Snapshot expected=a;StateEvaluation out;
    if(baseline){
      Need(baseline->proposalAllowed,"Nonpositive S/overflowed raw pressure cannot enter an extra force");
      for(unsigned i=Npb;i<Np;i++){const unsigned id=Idpc[i],s=a.byid[id];expected.p[s]=baseline->soil[id].raw;expected.excess[s]=expected.p[s]-expected.p0[s];}
      Copy(expected);Unchanged(expected);
      // Genuine completed-step positive-FS policy; not beta47 and never a negative-pressure clip.
      ApplyPorePressureBoundaries();
      for(unsigned i=Npb;i<Np;i++){const unsigned s=a.byid[Idpc[i]];out.positiveCap+=!Bits(PorePressc[i],expected.p[s]);
        if(expected.p[s]<0.f)Need(Bits(PorePressc[i],expected.p[s]),"Original completed positive cap changed negative pressure");
        expected.p[s]=PorePressc[i];expected.excess[s]=expected.p[s]-expected.p0[s];expected.fs[s]=FSTypec[i];expected.normal[s]=FSNormalc[i];expected.posdiv[s]=PosDivc[i];}
      Unchanged(expected);
    }
    bool cleanup=true;try{
      Interaction_Forces(INTERSTEP_SymCorrector);calls++;if(baseline)proposalCalls++;
      Need(Acec&&Rsigmac&&PorePressRatec&&BoundDerivativeVelc&&CorrMatc&&ArtificialStressc&&TangenVelc,"Original force scratch incomplete");Unchanged(expected);
      Need(NpbOk<=Npb,"Effective boundary prefix exceeds all fixed");out.npbok=NpbOk;
      for(unsigned i=0;i<Npb;i++){
        const unsigned id=Idpc[i];
        if(i>=NpbOk){out.ignored++;continue;} // No ignored BoundMode or scratch read.
        const byte mode=BoundModec[i];Need(mode==BMODE_MDBC2||mode==BMODE_MDBC2OFF,WallDetail("Effective wall mode invalid",id,i,NpbOk));
        if(mode==BMODE_MDBC2){out.active++;const auto d=BoundDerivativeVelc[i],t=TangenVelc[i];const auto C=CorrMatc[i];
          Need(Finite(d)&&Finite(t),WallDetail("Active wall derivative/tangent not finite",id,i,NpbOk));
          for(double v:{C.a11,C.a12,C.a13,C.a21,C.a22,C.a23,C.a31,C.a32,C.a33})Need(Finite(v),WallDetail("Active wall C not finite",id,i,NpbOk));}
        else out.inactive++;
      }
      Need(out.active+out.inactive==out.npbok&&out.ignored==Npb-out.npbok,"Defined active/OFF/ignored coverage differs");
      if(baseline)Need(out.npbok==baseline->npbok&&out.active==baseline->active&&out.inactive==baseline->inactive&&out.ignored==baseline->ignored,"Pressure-only stage changed geometric wall partition");
      for(unsigned i=Npb;i<Np;i++){
        const unsigned id=Idpc[i],s=a.byid[id];const auto r=Probe::Assemble(i);const Sums& z=r[0];const auto ai=ToTDouble3(Acec[i]);const bool sf=IsFreeSurfaceParticle(i,Codec,FSTypec);double n,V,rhot;GetPorosityFeedbackStateCpu(i,n,V,rhot);
        const double k=GetDynamicConductivityCpu(i),B=kw/n,dk=k/((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk),weight=n*V/kw;
#include "../outputs/c08_tpi_state_r1_build/rhs_literal.inc"
        auto& o=out.soil[id];o.p=PorePressc[i];o.rate=actual;o.S=-k*z.sumw;o.R=-gamma*PoroThetac[i]+k*lap+chain;o.n=n;o.V=V;o.k=k;o.theta=PoroThetac[i];o.J=PoroJc[i];o.fs=FSTypec[i];o.neighbors=z.count;o.fixedDonors=r[2].count;
        o.drained=IsHydroMechDrainageActive()&&IsHydroMechDrainedParticle(i,Posc,Codec,FSTypec);o.position=Posc[i];o.velocity=TFloat3(Velrhopc[i].x,Velrhopc[i].y,Velrhopc[i].z);o.ace=Acec[i];o.rs=Rsigmac[i];o.art=ArtificialStressc[i];o.C=CorrMatc[i];
        Need(Finite(o.R),Detail("Unscaled residual not finite",a.part,id,o.R,o.S,0));
        if(!baseline){
          const auto& b=reference[id];Need(b.present&&b.step==unsigned(Nstep)&&Bits(b.time,TimeStep)&&b.fs==o.fs&&Bits(b.ace,o.ace)&&Bits(b.rs,o.rs)&&Bits(b.theta,o.theta)&&Bits(b.rate,o.rate),"Actual5000 baseline differs from passed AS03 RHS");baselineBits++;
          if(o.drained){o.raw=0.f;o.admissible=true;}
          else if(!Finite(o.S)||!(o.S>0.)){out.badS++;out.proposalAllowed=false;}
          else{const double p=double(o.p)+o.R/o.S;if(!Finite(p)||fabs(p)>FLT_MAX){out.badRaw++;out.proposalAllowed=false;}else{o.raw=float(p);o.admissible=true;}}
        }
        else{
          const auto& b=baseline->soil[id];Need(Bits(o.theta,b.theta)&&Bits(o.rs,b.rs)&&Bits(o.J,b.J)&&Bits(o.n,b.n)&&Bits(o.V,b.V)&&Bits(o.k,b.k)&&o.fs==b.fs&&Bits(o.C,b.C),"Pressure-only force changed soil strain/J/geometry/ledger/FS");
          Need(o.drained==b.drained,"Fixed source-clock true drainage changed");
        }
        out.R2+=o.R*o.R;out.Rmax=(std::max)(out.Rmax,fabs(o.R));out.rate2+=double(o.rate)*o.rate;const auto ev=SpectrumXZ(o.art);const char* cohort=sf?"FS":o.fixedDonors?"wall_adjacent":"no_fixed_donor";
        soil<<a.part<<','<<TimeStep<<','<<unsigned(Nstep)<<','<<(baseline?"proposal_after_original_BC":"baseline")<<','<<id<<','<<o.position.x<<','<<o.position.y<<','<<o.position.z<<','<<o.p<<','<<PorePress0c[i]<<','<<o.J<<','<<o.n<<','<<o.V<<','<<o.k<<','<<o.theta<<','<<o.fs<<','<<o.neighbors<<','<<o.fixedDonors<<','<<cohort<<','<<o.drained<<','<<o.S<<','<<o.R<<',';
        if(!baseline&&o.admissible)soil<<o.raw;soil<<','<<(!baseline&&o.admissible)<<','<<o.rate<<','<<literal<<','<<ferr<<','<<fbudget<<','<<eerror<<','<<ebudget<<','<<o.ace.x<<','<<o.ace.y<<','<<o.ace.z;
        for(float v:{o.art.xx,o.art.yy,o.art.zz,o.art.xy,o.art.yz,o.art.xz})soil<<','<<v;for(double v:ev)soil<<','<<v;for(double v:pieces[0])soil<<','<<v;soil<<','<<double(actual)-expanded<<'\n';soilRows++;
        if(IsFocus(id)){focus<<a.part<<','<<(baseline?"proposal_after_original_BC":"baseline")<<','<<id<<','<<o.p<<','<<o.S<<','<<o.R<<','<<o.rate<<','<<o.ace.x<<','<<o.ace.y<<','<<o.ace.z;for(double v:ev)focus<<','<<v;focus<<'\n';focusRows++;}
      }
      Need(Finite(out.R2)&&Finite(out.Rmax)&&Finite(out.rate2),"Nonfinite descriptive residual norm");Unchanged(expected);PosInteraction_Forces();cleanup=false;
      Need(!Acec&&!Rsigmac&&!ArtificialStressc&&!BoundDerivativeVelc,"Original force scratch not released");Copy(a);Unchanged(a);
    }catch(...){if(cleanup)PosInteraction_Forces();throw;}
    return out;
  }
  void Pairs(const Snapshot& a,const StateEvaluation& e,const char* mode,std::ofstream& file){
    const unsigned pairs[2][2]={{4953,4954},{6767,6865}};
    for(const auto& p:pairs){const auto& i=e.soil[p[0]];const auto& j=e.soil[p[1]];const auto d=j.position-i.position;const double r=sqrt(Dot(d,d));Need(Finite(r)&&r>0,"Frozen focus pair distance invalid");const auto axis=d*(1./r),v=ToTDouble3(j.velocity)-ToTDouble3(i.velocity),acc=ToTDouble3(j.ace)-ToTDouble3(i.ace);const double rdot=Dot(v,axis),radial=Dot(acc,axis),curvature=(Dot(v,v)-rdot*rdot)/r;
      file<<a.part<<','<<a.time<<','<<a.completed<<','<<mode<<','<<p[0]<<','<<p[1]<<','<<r<<','<<rdot<<','<<radial<<','<<curvature<<','<<radial+curvature<<','<<i.p<<','<<j.p<<','<<i.R<<','<<j.R<<'\n';pairRows++;}
  }
public:
  void ExecuteState(const JSphCfgRun* cfg,JLog2* log,const std::array<Snapshot,2>& states,const std::array<std::vector<RhsReference>,2>& refs){
#include "../outputs/c08_tpi_state_r1_build/setup.inc"
    const pf::path out(cfg->DirOut);std::ofstream soil(out/"soil.csv"),focus(out/"focus.csv"),pairs(out/"pairs.csv"),summary(out/"summary.csv");for(auto f:{&soil,&focus,&pairs,&summary})*f<<std::setprecision(17);
    soil<<"part,time_s,completed_step,leg,native_id,x_m,y_m,z_m,p_actual_Pa,P0_Pa,J,n,V_m2,k_m_s,theta_s_1,FS,neighbors,fixed_donors,cohort,true_Dirichlet,S_LP_1_per_m_s,Rgamma_Pa_per_m_s,p_conditional_raw_Pa,conditional_raw_defined,actual_rate_Pa_s,literal_Pa_s,float_error_Pa_s,float_budget_Pa_s,expanded_error_Pa_s,expanded_budget_Pa_s,Acex,Acey,Acez,ASxx,ASyy,ASzz,ASxy,ASyz,ASxz,AS_eig_min,AS_eig_mid,AS_eig_max";for(const char* name:Terms)soil<<','<<name<<"_Pa_s";soil<<",numeric_float_source_residual_Pa_s\n";
    focus<<"part,leg,native_id,p_actual_Pa,S_LP,Rgamma,actual_rate_Pa_s,Acex,Acey,Acez,AS_eig_min,AS_eig_mid,AS_eig_max\n";
    pairs<<"part,time_s,completed_step,leg,id_i,id_j,r_m,rdot_m_s,relative_all_neighbor_a_radial_m_s2,tangential_curvature_m_s2,rddot_m_s2,p_i_Pa,p_j_Pa,Rgamma_i,Rgamma_j\n";
    summary<<"part,time_s,completed_step,leg,Rgamma_RMS,Rgamma_abs_max,actual_rate_RMS_Pa_s,nonpositive_S_rows,raw_overflow_rows,proposal_allowed,positive_FS_cap_changes,NpbOk,active_walls,OFF_walls,ignored_walls\n";
    unsigned allAdmitted=0;
    for(unsigned which=0;which<2;which++){
      const auto& a=states[which];const auto b=Evaluate(a,nullptr,refs[which],kw,rho,gamma,soil,focus);Pairs(a,b,"baseline",pairs);
      auto Write=[&](const StateEvaluation& e,const char* mode){summary<<a.part<<','<<a.time<<','<<a.completed<<','<<mode<<','<<sqrt(e.R2/Soil)<<','<<e.Rmax<<','<<sqrt(e.rate2/Soil)<<','<<e.badS<<','<<e.badRaw<<','<<e.proposalAllowed<<','<<e.positiveCap<<','<<e.npbok<<','<<e.active<<','<<e.inactive<<','<<e.ignored<<'\n';summaryRows++;};Write(b,"baseline");
      if(b.proposalAllowed){allAdmitted++;const auto trial=Evaluate(a,&b,refs[which],kw,rho,gamma,soil,focus);Pairs(a,trial,"proposal_after_original_BC",pairs);Write(trial,"proposal_after_original_BC");}
      Restore(a);Unchanged(a);for(auto f:{&soil,&focus,&pairs,&summary}){f->flush();Need(bool(*f),"Conditional state CSV write failed");}
    }
    Need(baselineBits==10000&&calls==2+proposalCalls&&proposalCalls==allAdmitted&&calls<=4&&soilRows==calls*Soil&&focusRows==calls*4&&pairRows==calls*2&&summaryRows==calls,"Bounded two-state coverage differs");
    std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"c08_tpi_state_r1\",\"passed\":true,\"parts\":[38,76],\"baseline_native_bits_rows\":"<<baselineBits<<",\"actual_force_calls\":"<<calls<<",\"actual_Darcy_calls\":"<<calls<<",\"proposal_force_calls\":"<<proposalCalls<<",\"admitted_state_proposals\":"<<allAdmitted<<",\"both_states_S_LP_and_raw_admissible\":"<<(allAdmitted==2?"true":"false")<<",\"soil_rows\":"<<soilRows<<",\"focus_rows\":"<<focusRows<<",\"pair_rows\":"<<pairRows<<",\"summary_rows\":"<<summaryRows<<",\"max_final_float_budget_ratio\":"<<maxFloatRatio<<",\"max_expanded_budget_ratio\":"<<maxExpandedRatio<<",\"S_is_only_LP_split_diagonal\":true,\"Rgamma_direct_double_not_float_inverse\":true,\"full301_native_used_only_two_parts\":true,\"all5000_nonpressure_soil_primary_bits_unchanged\":true,\"wall_ghost_reconstruction_is_not_physical_state_advance\":true,\"ignored_modes_and_scratch_not_read\":true,\"proposal_completed_positive_FS_cap_is_not_beta\":true,\"negative_pressure_not_clipped\":true,\"true_Dirichlet_uses_original_drain_predicate\":true,\"history_available\":false,\"cold_frozen_state_proposal_only\":true,\"TPI_trajectory_or_full_coupled_spectrum\":false,\"physical_steps\":0,\"material_return_calls\":0,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Conditional state completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=9&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--native","Use --check --native SEALED_FULL301_NATIVE -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 ORIGINAL_N255_SEED FRESH_OUT");
  const pf::path tests=pf::path(__FILE__).parent_path().parent_path(),native=pf::absolute(argv[3]),seed=tests/"outputs/c08_h18_as03n255_full3_r1/c08_h18_as03n255_full3_r1",pre=tests/"outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4",rhs=tests/"outputs/c08_h18_as03_rhs_r1/soil_rhs.csv";
  Need(pf::equivalent(native,tests/"outputs/c08_h18_as03n255_full3_r1/native_r1"),"Only original sealed full301 AS03 native admitted");std::vector<Stamp> protectedFiles;
  for(const char* name:{"typed22.bin","typed22_layout.csv","clocks.csv","completion.json","bedkeep_metadata.json"})protectedFiles.emplace_back(native/name);for(const char* suffix:{".xml",".bi4","_Normals.nbi4"})protectedFiles.emplace_back(pf::path(seed.string()+suffix));protectedFiles.emplace_back(pre);protectedFiles.emplace_back(rhs);
  for(const char* name:{"c08_h18_as03n255_full3_r1.run.json","c08_h18_as03n255_full3_native_r1.check.json","c08_h18_as03n255_full3_review_r1.check.json","c08_h18_as03_rhs_r1.check.json","c08_tpi_state_r1.build.json"})protectedFiles.emplace_back(tests/"logs"/name);protectedFiles.emplace_back(pf::absolute(argv[0]));for(const char* name:{"DsphConfig.xml","ChronoEngine.dll","dsphchrono.dll","vcomp140.dll","msvcp140.dll","vcruntime140.dll","vcruntime140_1.dll"})protectedFiles.emplace_back(pf::absolute(argv[0]).parent_path()/name);
  const std::array<Snapshot,2> states={Snapshot(native,0),Snapshot(native,1)};const auto reference=ReadReference(rhs);AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());
  Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&pf::absolute(cfg.CaseName)==pf::absolute(seed)&&pf::absolute(cfg.DirOut)==pf::absolute(tests/"outputs/c08_tpi_state_r1")&&!pf::exists(cfg.DirOut),"Only original seed and fresh exact conditional-state output admitted");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");TpiStateProbe probe;probe.ExecuteState(&cfg,AppInfo.LogPtr(),states,reference);for(const auto& e:protectedFiles)e.Check();return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Conditional state audit failed; preserve partials\n";return 2;}}
