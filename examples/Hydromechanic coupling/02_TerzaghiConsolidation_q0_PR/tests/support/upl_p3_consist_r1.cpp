// New standalone screen; the original three-operator implementation remains immutable.
#define main UplP3PairR1ControlMain
#include "upl_p3_pair_r1.cpp"
#undef main
#include <sstream>
static const char* StarName="symC_Lstar_plus_receiverC_DAce";
static double Component(tdouble3 a,unsigned axis){return axis==0?a.x:axis==1?a.y:a.z;}
static void SetComponent(tdouble3& a,unsigned axis,double value){if(axis==0)a.x=value;else if(axis==1)a.y=value;else a.z=value;}
struct StarResult{
  std::vector<double> rate,darcy,scale,tolerance,error;
  double maxExactError=0,maxExactTolerance=0;
};
static StarResult EvaluateStar(const Patch& p,const Field& f,const Result& old){
  const unsigned n=unsigned(p.nodes.size());std::vector<double> lp(n,0),da(n,0),lpAbs(n,0),daAbs(n,0);
  std::vector<tdouble3> lx(n,TDouble3(0)),lxAbs(n,TDouble3(0));
  for(const auto& e:p.edges){
    const auto i=e.i,j=e.j;const double wi=2*p.nodes[j].V*e.betaSym,wj=2*p.nodes[i].V*e.betaSym,dp=f.p[i]-f.p[j];
    const auto daij=f.ace[j]-f.ace[i],ci=Mul(p.nodes[i].c,e.g),cj=Mul(p.nodes[j].c,e.g*(-1.));
    lp[i]+=wi*dp;lp[j]+=wj*(-dp);lpAbs[i]+=fabs(wi*dp);lpAbs[j]+=fabs(wj*dp);
    lx[i]=lx[i]+e.d*wi;lx[j]=lx[j]+e.d*(-wj);
    for(unsigned a=0;a<3;a++){SetComponent(lxAbs[i],a,Component(lxAbs[i],a)+fabs(Component(e.d,a)*wi));SetComponent(lxAbs[j],a,Component(lxAbs[j],a)+fabs(Component(e.d,a)*wj));}
    const double ai=p.nodes[j].V*Dot(daij,ci),aj=p.nodes[i].V*Dot(daij*(-1.),cj);
    da[i]+=ai;da[j]+=aj;daAbs[i]+=fabs(ai);daAbs[j]+=fabs(aj);
  }
  StarResult r;r.rate.resize(n);r.darcy.resize(n);r.scale.resize(n);r.tolerance.resize(n);r.error.resize(n);
  for(unsigned i=0;i<n;i++){
    const double gain=Kw/p.nodes[i].n*f.k/Gamma,compression=-Kw/p.nodes[i].n*f.theta;
    r.darcy[i]=gain*(lp[i]-Dot(old.gp[i],lx[i])+RhoWater*da[i]);r.rate[i]=r.darcy[i]+compression;
    const auto g=old.gp[i];const double correctionScale=fabs(g.x)*lxAbs[i].x+fabs(g.y)*lxAbs[i].y+fabs(g.z)*lxAbs[i].z;
    r.scale[i]=gain*(lpAbs[i]+correctionScale+RhoWater*daAbs[i]+fabs(f.continuum))+fabs(compression);
    r.tolerance[i]=4096*DBL_EPSILON*(std::max)(1.,r.scale[i])+1e-7;
    const double reference=gain*f.continuum+compression;r.error[i]=fabs(r.rate[i]-reference);
    Need(std::isfinite(r.rate[i])&&std::isfinite(r.scale[i]),"Nonfinite consistency-star rate");
    if(f.affinePressure){Need(r.error[i]<=r.tolerance[i],"Consistency-star affine/constant-flux rate failed declared roundoff gate");r.maxExactError=(std::max)(r.maxExactError,r.error[i]);r.maxExactTolerance=(std::max)(r.maxExactTolerance,r.tolerance[i]);}
  }
  return r;
}
static Field QuadBalanced(const Patch& p){
  auto f=MakeField(p,5);f.name="quadratic_pressure_zero_physical_flux";f.purePressure=false;f.equilibrium=false;f.affinePressure=false;f.continuum=0;f.gravity=TDouble3(0,0,-8);
  for(unsigned i=0;i<p.nodes.size();i++){f.ace[i]=f.gradReference[i]*(-1./RhoWater);f.as[i]=f.ace[i]+f.gravity;}
  return f;
}
static std::vector<Field> BasisFields(const Patch& p){
  const unsigned axes[3]={0,p.dim==2?2u:1u,2};std::vector<Field> fields;
  static const char* quadNames[3][3]={{"quadratic_xx","quadratic_xy","quadratic_xz"},{"quadratic_xy","quadratic_yy","quadratic_yz"},{"quadratic_xz","quadratic_yz","quadratic_zz"}};
  static const char* aceNames[3][3]={{"affine_Ace_xx","affine_Ace_xy","affine_Ace_xz"},{"affine_Ace_yx","affine_Ace_yy","affine_Ace_yz"},{"affine_Ace_zx","affine_Ace_zy","affine_Ace_zz"}};
  for(unsigned a=0;a<p.dim;a++)for(unsigned b=a;b<p.dim;b++){
    Field f;f.name=quadNames[axes[a]][axes[b]];f.gravity=TDouble3(0);f.purePressure=true;f.continuum=a==b?1024.:0.;
    for(const auto& node:p.nodes){const double x=Component(node.x,axes[a]),y=Component(node.x,axes[b]);tdouble3 grad=TDouble3(0);
      if(a==b)SetComponent(grad,axes[a],1024*x);else{SetComponent(grad,axes[a],1024*y);SetComponent(grad,axes[b],1024*x);}
      f.p.push_back(2048+(a==b?512*x*x:1024*x*y));f.ace.push_back(TDouble3(0));f.as.push_back(TDouble3(0));f.gradReference.push_back(grad);
    }fields.push_back(std::move(f));
  }
  for(unsigned a=0;a<p.dim;a++)for(unsigned b=0;b<p.dim;b++){
    Field f;f.name=aceNames[axes[a]][axes[b]];f.gravity=TDouble3(0);f.affinePressure=true;f.continuum=a==b?RhoWater/16.:0.;
    for(const auto& node:p.nodes){tdouble3 ace=TDouble3(0);SetComponent(ace,axes[a],Component(node.x,axes[b])/16.);f.p.push_back(2048);f.ace.push_back(ace);f.as.push_back(ace);f.gradReference.push_back(TDouble3(0));}fields.push_back(std::move(f));
  }
  return fields;
}
static void RecordFour(const Patch& p,const Field& f,const Result& old,const StarResult& star,std::ostream& summary,std::ostream& core,std::ostream& balance,unsigned& balanceRows){
  for(unsigned op=0;op<4;op++){
    const auto& rate=op==3?star.rate:old.rate[op];const auto& darcy=op==3?star.darcy:old.darcy[op];
    long double budget=0,totalBudget=0,compression=0,energy=0;double core2=0,outer2=0,coreMax=0,outerMax=0;unsigned nc=0,no=0;
    for(unsigned i=0;i<p.nodes.size();i++){
      const auto& n=p.nodes[i];const double weight=n.V*n.n/Kw,reference=Kw/n.n*(f.k/Gamma*f.continuum-f.theta),error=rate[i]-reference;
      budget+=(long double)weight*darcy[i];totalBudget+=(long double)weight*rate[i];compression-=n.V*f.theta;energy+=(long double)weight*f.p[i]*rate[i];
      if(std::string(f.name)=="quadratic_pressure_zero_physical_flux"){const auto q=old.q[i],qr=old.qReference[i];balance<<p.dim<<','<<p.jitter<<','<<(op==3?StarName:Operator(op))<<','<<i<<','<<n.core<<','<<n.x.x<<','<<n.x.y<<','<<n.x.z<<','<<f.p[i]<<','<<rate[i]<<','<<reference<<','<<error<<','<<q.x<<','<<q.y<<','<<q.z<<','<<qr.x<<','<<qr.y<<','<<qr.z<<'\n';balanceRows++;}
      if(n.core){nc++;core2+=error*error;coreMax=(std::max)(coreMax,fabs(error));const auto q=old.q[i],qr=old.qReference[i];core<<p.dim<<','<<p.jitter<<','<<f.name<<','<<(op==3?StarName:Operator(op))<<','<<i<<','<<f.p[i]<<','<<rate[i]<<','<<reference<<','<<q.x<<','<<q.y<<','<<q.z<<','<<qr.x<<','<<qr.y<<','<<qr.z<<'\n';}
      else{no++;outer2+=error*error;outerMax=(std::max)(outerMax,fabs(error));}
    }
    summary<<p.dim<<','<<p.jitter<<','<<f.name<<','<<(op==3?StarName:Operator(op))<<','<<nc<<','<<no<<','<<f.purePressure<<','<<f.affinePressure<<','<<sqrt(core2/nc)<<','<<coreMax<<','<<sqrt(outer2/no)<<','<<outerMax<<','<<double(budget)<<','<<double(totalBudget)<<','<<double(compression)<<','<<double(energy)<<','<<(op==3?star.maxExactError:0)<<','<<(op==3?star.maxExactTolerance:0)<<'\n';
  }
}
static unsigned DirichletMatrices(const Patch& p,std::ostream& out){
  std::vector<unsigned> ids;for(unsigned i=0;i<p.nodes.size();i++)if(p.nodes[i].core)ids.push_back(i);
  for(unsigned col=0;col<ids.size();col++){
    Field f;f.name="core_dirichlet_unit_pressure";f.gravity=TDouble3(0);
    f.p.assign(p.nodes.size(),0);f.ace.assign(p.nodes.size(),TDouble3(0));f.as=f.ace;f.gradReference=f.ace;f.p[ids[col]]=1.;
    const auto old=Evaluate(p,f);const auto star=EvaluateStar(p,f,old);
    for(unsigned row=0;row<ids.size();row++)for(unsigned op=0;op<4;op++){
      const unsigned i=ids[row];const double value=op==3?star.rate[i]:old.rate[op][i],weight=p.nodes[i].V*p.nodes[i].n/Kw;
      out<<p.dim<<','<<p.jitter<<','<<(op==3?StarName:Operator(op))<<','<<row<<','<<col<<','<<i<<','<<ids[col]<<','<<weight<<','<<value<<'\n';
    }
  }
  return unsigned(ids.size()*ids.size()*4);
}
static void CentralSupport(const Patch& p,std::ostream& out){
  const unsigned center=unsigned((p.nodes.size()-1)/2);const double displacement=Dp/8.,outsideMin=5*Dp-displacement,support=2*H;
  Need(Norm(p.nodes[center].x)<=displacement,"Central reference node coverage changed");std::vector<bool> affected(p.nodes.size(),false);affected[center]=true;
  for(const auto& e:p.edges){if(e.i==center)affected[e.j]=true;if(e.j==center)affected[e.i]=true;}
  double clearance=DBL_MAX;unsigned count=0;
  for(unsigned i=0;i<p.nodes.size();i++)if(affected[i]){count++;for(unsigned a=0;a<3;a++)if(p.dim==3||a!=1)clearance=(std::min)(clearance,outsideMin-fabs(Component(p.nodes[i].x,a))-support);}
  Need(clearance>0,"Central node or neighbor correction support reaches an omitted reference node");
  out<<p.dim<<','<<p.jitter<<','<<center<<','<<count<<','<<clearance<<','<<outsideMin<<','<<support<<'\n';
}
int main(int argc,char** argv){
  try{
    Need(argc==3&&std::string(argv[1])=="--out","Use --out NEW_DIRECTORY");const fs::path out(argv[2]),control(out.string()+"_control");Need(!fs::exists(out)&&!fs::exists(control),"Retained output protected");
    std::string oldOut=control.string();char* oldArgs[3]={argv[0],argv[1],oldOut.data()};Need(UplP3PairR1ControlMain(3,oldArgs)==0,"Unchanged old control screen failed");
    fs::create_directories(out);std::ofstream summary(out/"summary.csv"),core(out/"core.csv"),matrices(out/"dirichlet_matrices.csv"),support(out/"central_support.csv"),balance(out/"quadratic_balance.csv");for(auto* s:{&summary,&core,&matrices,&support,&balance})*s<<std::setprecision(17);
    summary<<"dimension,jitter,field,operator,core_nodes,outer_nodes,pure_pressure,affine_exact_rate_required,core_rms_pa_s,core_absmax_pa_s,outer_rms_pa_s,outer_absmax_pa_s,frozen_Darcy_budget_mpowdim_s,frozen_total_budget_mpowdim_s,compression_budget_mpowdim_s,global_pressure_energy_rate_pa_mpowdim_s,star_exact_error_absmax_pa_s,star_exact_tolerance_absmax_pa_s\n";
    core<<"dimension,jitter,field,operator,id,p_pa,total_rate_pa_s,continuum_rate_pa_s,qx_m_s,qy_m_s,qz_m_s,qrefx_m_s,qrefy_m_s,qrefz_m_s\n";
    matrices<<"dimension,jitter,operator,row,col,receiver_id,source_id,storage_weight_Vn_Kw,A_per_s\n";
    support<<"dimension,jitter,central_id,central_and_neighbor_count,minimum_omitted_node_clearance_m,first_omitted_coordinate_min_m,kernel_support_m\n";
    balance<<"dimension,jitter,operator,id,receiver_core,x_m,y_m,z_m,p_pa,total_rate_pa_s,reference_rate_pa_s,error_pa_s,qx_m_s,qy_m_s,qz_m_s,qrefx_m_s,qrefy_m_s,qrefz_m_s\n";
    struct NullBuffer:std::streambuf{int overflow(int ch)override{return traits_type::not_eof(ch);}} buffer;std::ostream discard(&buffer);Totals oldChecks;
    unsigned fieldPatches=0,matrixRows=0,balanceRows=0;double maxExact=0,maxTolerance=0;
    for(unsigned dim:{2u,3u})for(bool jitter:{false,true}){
      Patch p(dim,jitter);CentralSupport(p,support);std::vector<Field> fields;for(unsigned f=0;f<13;f++)fields.push_back(MakeField(p,f));fields.push_back(QuadBalanced(p));auto basis=BasisFields(p);fields.insert(fields.end(),basis.begin(),basis.end());
      Need(fields.size()==(dim==2?21u:29u),"Consistency field coverage changed");
      for(const auto& f:fields){const auto old=Evaluate(p,f);Record(p,f,old,discard,discard,oldChecks);const auto star=EvaluateStar(p,f,old);RecordFour(p,f,old,star,summary,core,balance,balanceRows);maxExact=(std::max)(maxExact,star.maxExactError);maxTolerance=(std::max)(maxTolerance,star.maxExactTolerance);fieldPatches++;}
      matrixRows+=DirichletMatrices(p,matrices);
    }
    for(auto* s:{&summary,&core,&matrices,&support,&balance}){s->flush();Need(bool(*s),"Consistency CSV write failed");}
    std::ofstream done(out/"complete.json");done<<std::setprecision(17)<<"{\"screening_stage_gates_passed\":true,\"operators\":4,\"patches\":4,\"field_patch_cases\":"<<fieldPatches<<",\"matrix_rows\":"<<matrixRows<<",\"quadratic_balance_rows\":"<<balanceRows<<",\"star_exact_rate_error_absmax_pa_s\":"<<maxExact<<",\"star_exact_rate_tolerance_absmax_pa_s\":"<<maxTolerance<<",\"central_neighbor_support_verified\":true,\"old_controls_require_offline_hash_comparison\":true,\"core_energy_matrix_requires_offline_eigenscreen\":true,\"new_global_budget_and_energy_diagnostic_only\":true,\"production_rate_pass_called\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Consistency completion write failed");
    std::cout<<"Consistency-star component stage finished; old-control hashes and core matrix energy screen are still required. No candidate/physical admission.\n";return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
