// Synthetic BI4 loader tests only. No solver, physical PRE or state integration.
#include "JGravityPreloadState.h"
#include "JException.h"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>

namespace fs=std::filesystem;
static constexpr unsigned Count=5,Fixed=2,Event=4;
static constexpr double Dt=.005,EventTime=.02,N0=.35,Rho0=2000.,Water=1000.,Mass=3.2,K0=.0002,Ck=2.;
static void Need(bool ok,const std::string& text){if(!ok)throw std::runtime_error(text);}
template<class T> static bool Bits(const T& a,const T& b){return !std::memcmp(&a,&b,sizeof(T));}
static std::string Quote(const std::string& s){std::string out="\"";for(char c:s){if(c=='\"')out+='\"';out+=c;}return out+'\"';}
static double ScalarTime(){volatile double value=0.;for(unsigned i=0;i<Event;i++)value+=Dt;return value;}

// Mirror only the public contract2 serialization tokens, with an explicit
// synthetic base contract. This does NOT exercise JSph's configuration parser.
struct Material{unsigned dp=3;float K=19607844.f,G=7518796.5f,cp=5000.f,cr=1000.f,nc=5.f,psi=0.f,sf=0.f;bool soft=true,trigger=true;std::string base="SYNTHETIC_LOADER_ONLY phi=25 phi_r=25 n_phi=0";};
static std::string Contract2(const Material& m){std::ostringstream out;out<<std::setprecision(17)<<"gravity-preload-2 "<<m.base<<" material "<<m.dp<<' '<<m.K<<' '<<m.G<<' '<<m.cp<<' '<<m.cr<<' '<<m.nc<<' '<<m.psi<<' '<<m.sf<<' '<<m.soft<<" law 2 trigger PartBeginSoftening "<<(m.trigger&&m.soft)<<" tension JointExistingApexCap history KappaDeviatoric";return out.str();}
static const std::string Contract1="SYNTHETIC_LOADER_ONLY_SCHEMA1_NOT_PHYSICS";
struct Fixture{
  unsigned schema=2;bool legacy=false,elastic=false,positive=true;
  float sourcecoh=5000.f,targetcoh=5000.f;int badk=0;
  Material source,target;bool empty_contract2=false;
  unsigned id[Count]={1,0,4,2,3},fst[Count]={0,0,2,0,0};
  tdouble3 pos[Count],sk[Count],si[Count];tfloat3 vel[Count],legacyk[Count],legacyi[Count],normal[Count],load[Count];
  float rhop[Count],kap[Count],p[Count],p0[Count],excess[Count],posdiv[Count];
  double j[Count],theta[Count],n[Count],volume[Count],rho[Count],k[Count];
  void Fields(){for(unsigned q=0;q<Count;q++){
    const unsigned a=id[q];const bool fixed=a<Fixed;
    pos[q]=TDouble3(.02+.04*a,0.,fixed?-.02:.02+.04*(a-Fixed));
    vel[q]=fixed?TFloat3(0):TFloat3(.001f*a,0.f,-.002f*a);
    sk[q]=TDouble3(-1000.-a,-2000.-a,-3000.-a);si[q]=TDouble3(.25*a,-.5*a,.75*a);
    legacyk[q]=TFloat3(float(sk[q].x),float(sk[q].y),float(sk[q].z));legacyi[q]=TFloat3(float(si[q].x),float(si[q].y),float(si[q].z));
    normal[q]=(fst[q]==2?TFloat3(0,0,1):TFloat3(0));load[q]=TFloat3(0);
    kap[q]=(!fixed&&positive?.01f*a:0.f);p0[q]=1000.f+10.f*a;p[q]=(fst[q]==2?-25.f:900.f+5.f*a);excess[q]=float(p[q]-p0[q]);posdiv[q]=float(a)/16.f;
    j[q]=fixed?1.:1.+.001*a;theta[q]=fixed?0.:.0001*a;
    n[q]=fixed?0.:1.-(1.-N0)/j[q];volume[q]=fixed?0.:Mass/Rho0*j[q];rho[q]=fixed?0.:Water+(Rho0-Water)/j[q];
    k[q]=fixed?0.:K0*std::exp((j[q]-1.)/((1.-N0)*Ck));rhop[q]=fixed?float(Rho0):float(rho[q]);
  }if(badk==1)kap[3]=-.01f;else if(badk==2)kap[0]=.01f;}
};
static fs::path Write(const fs::path& dir,Fixture& v){
  Need(fs::create_directory(dir),"Synthetic fixture directory must be fresh");v.Fields();JPartDataBi4 f;
  f.ConfigBasic(0,1,"SYNTHETIC","Schema2LoaderTest","SYNTHETIC_NOT_PHYSICS",true,0.,dir.string());
  f.ConfigParticles(Count,Fixed,0,0,Count-Fixed,TDouble3(-1),TDouble3(1));f.ConfigCtes(.04,double(float(.048)),1.,Rho0,7.,Mass,Mass);
  f.ConfigSimMap(TDouble3(-1),TDouble3(1));f.ConfigSimPeri(PERI_None,TDouble3(0),TDouble3(0),TDouble3(0));f.ConfigSymmetry(false);f.ConfigSplitting(false);
  auto* p=f.AddPartInfo(1,ScalarTime(),Count,0,Event-1,0.,TDouble3(-1),TDouble3(1));
  p->SetvUint("GravityPreloadHandoffSchema",v.schema);p->SetvBool("GravityPreloadElasticSource",v.elastic);
  p->SetvText("GravityPreloadHandoffContract",v.schema==1?Contract1:Contract2(v.source));p->SetvFloat("GravityPreloadSourceCohesion",v.sourcecoh);
  p->SetvBool("DynamicArtificialStressActive",false);p->SetvUint("GravityPreloadPhase",0);p->SetvDouble("GravityPreloadRequestedTime",EventTime);p->SetvUint("GravityPreloadEventCompletedStep",Event);
  p->SetvBool("SoilDampingActive",true);p->SetvBool("PoreShepardActive",true);p->SetvBool("HydroMechFreeSeepage",true);
  if(v.legacy)p->SetvUint("MaterialReturn",1);else p->SetvUint("MaterialLawVersion",2);
  p->SetvFloat("DilationDecay",v.source.sf);p->SetvBool("HydroMechDynamicSeepage",true);p->SetvUint("DynamicSeepageSchema",1);p->SetvUint("HydroMechConductivityModel",1);p->SetvDouble("HydroMechConductivityCk",Ck);
  p->SetvUint("GravityPreloadReleaseMkBound",2);p->SetvUint("GravityPreloadTargetIdBegin",1);p->SetvUint("GravityPreloadTargetIdCount",1);p->SetvDouble("SymplecticDtPre",Dt);p->SetvDouble("dterror",-1e-4);
  f.AddPartData(Count,v.id,v.pos,v.vel,v.rhop);
  f.AddPartData("Sigma_kk",Count,v.legacyk);f.AddPartData("Sigma_ij",Count,v.legacyi);f.AddPartData("SigmaState_kk",Count,v.sk);f.AddPartData("SigmaState_ij",Count,v.si);
  f.AddPartData("Kplastic",Count,v.kap);f.AddPartData("FSType",Count,v.fst);f.AddPartData("FSNormal",Count,v.normal);f.AddPartData("HydroMechLoadAce",Count,v.load);
  f.AddPartData("PorePress",Count,v.p);f.AddPartData("PorePress0",Count,v.p0);f.AddPartData("ExcessPorePress",Count,v.excess);f.AddPartData("PoroVolumeRatio",Count,v.j);
  f.AddPartData("PoroPorosity",Count,v.n);f.AddPartData("PoroThetaLastStage",Count,v.theta);f.AddPartData("PoroCurrentVolume",Count,v.volume);f.AddPartData("PoroMixtureDensity",Count,v.rho);f.AddPartData("PoroHydraulicConductivity",Count,v.k);f.AddPartData("PosDiv",Count,v.posdiv);
  Need(f.ArraysCount()==22,"Synthetic writer must emit exact22 arrays");f.SaveFilePart();return dir/JPartDataBi4::GetFileNamePart(1);
}
static void Carry(const JGravityPreloadState& s,const Fixture& v){
  Need(s.Schema==v.schema&&s.Count==Count&&s.Fixed==Fixed&&s.CompletedStep==Event&&s.MaterialLawVersion==(v.legacy?1u:2u)&&Bits(s.Time,ScalarTime())&&Bits(s.Dt,Dt),"Accepted metadata not carried");
  Need(s.RetireBegin==1&&s.RetireCount==1&&s.MkBound==2,"Accepted release registry not carried");
  for(unsigned q=0;q<Count;q++){
    Need(s.Idp[q]==v.id[q]&&s.ById[v.id[q]]==q&&s.FSType[q]==v.fst[q],"Original raw order/ById/FS not carried");
    Need(Bits(s.Pos[q],v.pos[q])&&Bits(s.SigmaKK[q],v.sk[q])&&Bits(s.SigmaIJ[q],v.si[q])&&Bits(s.Kplastic[q],v.kap[q])&&Bits(s.PorePress[q],v.p[q])&&Bits(s.PorePress0[q],v.p0[q])&&Bits(s.J[q],v.j[q])&&Bits(s.Theta[q],v.theta[q])&&Bits(s.FSNormal[q],v.normal[q])&&Bits(s.PosDiv[q],v.posdiv[q]),"Accepted state bits not carried");
    const auto vr=TFloat4(v.vel[q].x,v.vel[q].y,v.vel[q].z,v.rhop[q]);Need(Bits(s.VelRhop[q],vr),"Accepted velocity/rhop bits not carried");
  }
}
struct Test{std::string name;Fixture fixture;bool accept;std::string reason;bool old_signature=false;};
int wmain(int argc,wchar_t** argv){try{
  Need(argc==2,"Use C08PreloadSchema2Loader_win64.exe FRESH_SYNTHETIC_OUT");const fs::path out=argv[1];Need(!fs::exists(out)&&fs::create_directory(out),"Synthetic output protected; use one fresh directory");
  std::vector<Test> tests;Fixture s1;s1.schema=1;s1.elastic=true;s1.positive=false;s1.legacy=true;
  tests.push_back({"schema1_legacy_original_signature",s1,true,"",true});s1.legacy=false;tests.push_back({"schema1_law2_original_signature",s1,true,"",true});
  s1.sourcecoh=4000;tests.push_back({"schema1_weaker_source_cohesion",s1,true,"",true});s1.sourcecoh=5000;s1.positive=true;tests.push_back({"schema1_positive_kappa_reject",s1,false,"history"});
  Fixture good;tests.push_back({"schema2_positive_kappa_carry",good,true,""});Fixture q=good;q.positive=false;tests.push_back({"schema2_zero_kappa_carry",q,true,""});
  q=good;q.badk=1;tests.push_back({"schema2_negative_soil_kappa_reject",q,false,"history"});q=good;q.badk=2;tests.push_back({"schema2_fixed_kappa_reject",q,false,"fixed"});
  q=good;q.legacy=true;tests.push_back({"schema2_law1_reject",q,false,"requires unified material law2"});q=good;q.schema=99;tests.push_back({"unknown_schema_reject",q,false,"schema/contract"});
  q=good;q.elastic=true;tests.push_back({"schema2_elastic_flag_reject",q,false,"schema/contract"});q=good;q.empty_contract2=true;tests.push_back({"schema2_missing_target_contract_reject",q,false,"schema/contract"});
  q=good;q.sourcecoh=4000;tests.push_back({"schema2_typed_source_cp_reject",q,false,"cohesion differs"});
  q=good;q.target.cp=7500;tests.push_back({"schema2_contract_cp_reject",q,false,"schema/contract"});q=good;q.target.psi=2.5f;tests.push_back({"schema2_contract_psi_reject",q,false,"schema/contract"});
  q=good;q.target.sf=.2f;tests.push_back({"schema2_contract_sf_reject",q,false,"schema/contract"});q=good;q.target.dp=2;tests.push_back({"schema2_contract_DP_reject",q,false,"schema/contract"});
  q=good;q.target.cr=2000;tests.push_back({"schema2_contract_residual_cp_reject",q,false,"schema/contract"});q=good;q.target.nc=6;tests.push_back({"schema2_contract_softening_rate_reject",q,false,"schema/contract"});
  q=good;q.target.K=2e7f;tests.push_back({"schema2_contract_K_reject",q,false,"schema/contract"});q=good;q.target.G=8e6f;tests.push_back({"schema2_contract_G_reject",q,false,"schema/contract"});
  q=good;q.target.soft=false;tests.push_back({"schema2_contract_softening_policy_reject",q,false,"schema/contract"});q=good;q.target.trigger=false;tests.push_back({"schema2_contract_trigger_reject",q,false,"schema/contract"});
  q=good;q.target.base="SYNTHETIC_LOADER_ONLY phi=26 phi_r=25 n_phi=0";tests.push_back({"schema2_base_contract_phi_reject",q,false,"schema/contract"});
  std::ofstream csv(out/"tests.csv");csv<<"case,schema,expected_accept,accepted,carry_bits_checked,passed,error\n";unsigned passed=0,accepted=0,rejected=0;
  for(auto& t:tests){const auto file=Write(out/("synthetic_"+t.name),t.fixture);JGravityPreloadState state;bool got=false,carried=false;std::string error;
    try{if(t.old_signature)state.Load(file.string(),Contract1,Count,Fixed,Event,EventTime,Dt,t.fixture.targetcoh,N0,Rho0,Water,Mass,K0,Ck);
      else state.Load(file.string(),Contract1,Count,Fixed,Event,EventTime,Dt,t.fixture.targetcoh,N0,Rho0,Water,Mass,K0,Ck,t.fixture.empty_contract2?std::string():Contract2(t.fixture.target));got=true;}
    catch(const std::exception& e){error=e.what();}
    bool ok=got==t.accept;if(got&&t.accept){try{Carry(state,t.fixture);carried=true;}catch(const std::exception& e){ok=false;error=e.what();}}
    if(!t.accept)ok=ok&&!error.empty()&&error.find(t.reason)!=std::string::npos;
    if(ok){passed++;if(got)accepted++;else rejected++;}csv<<Quote(t.name)<<','<<t.fixture.schema<<','<<t.accept<<','<<got<<','<<carried<<','<<ok<<','<<Quote(error)<<'\n';
  }
  csv.flush();Need(bool(csv),"Synthetic test CSV write failed");std::ofstream done(out/"completion.json");done<<"{\"stage\":\"c08_preload_schema2_loader_r1\",\"passed\":"<<(passed==tests.size()?"true":"false")<<",\"tests\":"<<tests.size()<<",\"passed_tests\":"<<passed<<",\"accepted_cases\":"<<accepted<<",\"rejected_cases\":"<<rejected<<",\"synthetic_only\":true,\"physical_acceptance\":false,\"solver_calls\":0,\"physical_updates\":0}\n";done.flush();Need(bool(done),"Synthetic completion write failed");Need(passed==tests.size(),"At least one loader test failed; preserve synthetic fixtures/CSV");return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
