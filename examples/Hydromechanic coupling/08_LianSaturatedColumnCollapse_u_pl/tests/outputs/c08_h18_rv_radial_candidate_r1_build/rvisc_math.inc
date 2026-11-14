static constexpr double Alpha=.1;
struct Mat2{double xx=0,xz=0,zx=0,zz=0;};
static tdouble3 Mul(const Mat2& a,tdouble3 d){return TDouble3(a.xx*d.x+a.xz*d.z,0,a.zx*d.x+a.zz*d.z);}
static void Outer(Mat2& a,tdouble3 v,tdouble3 d,double w){a.xx+=w*v.x*d.x;a.xz+=w*v.x*d.z;a.zx+=w*v.z*d.x;a.zz+=w*v.z*d.z;}
static double MN(const Mat2& a){return sqrt(a.xx*a.xx+a.xz*a.xz+a.zx*a.zx+a.zz*a.zz);}
static double MDot(const Mat2& a,const Mat2& b){return a.xx*b.xx+a.xz*b.xz+a.zx*b.zx+a.zz*b.zz;}
static double Len(tdouble3 a){return sqrt(Dot(a,a));}
struct Stats{
  double edges=0;
  double max_degree=0;
  double max_condition=0;
  double gamma64=0;
  double dmax_unit=0;
  double alpha_dt_dmax=0;
  double work=0;
  double form=0;
  double work_plus_2form=0;
  double work_budget=0;
  double work_defect_prediction=0;
  double work_certificate_error=0;
  double max_normal_defect=0;
  double max_normal_budget_fraction=0;
  double net_force_norm=0;
  double net_force_budget=0;
  double torque_y=0;
  double torque_budget=0;
  double torque_defect_prediction=0;
  double torque_certificate_error=0;
  double max_force=0;
  double max_added_accel=0;
  double committed_work=0;
  double committed_work_budget=0;
  double committed_net_force_norm=0;
  double committed_net_force_budget=0;
  double committed_torque_y=0;
  double committed_torque_budget=0;
  double max_commit_force_error=0;
  double manufacture_max_residual=0;
  double manufacture_residual_budget=0;
  double manufacture_force_budget=0;
};
static void StatsHeader(std::ostream& f){const char* names[]={"edges","max_degree","max_condition","gamma64","dmax_unit","alpha_dt_dmax","work","form","work_plus_2form","work_budget","work_defect_prediction","work_certificate_error","max_normal_defect","max_normal_budget_fraction","net_force_norm","net_force_budget","torque_y","torque_budget","torque_defect_prediction","torque_certificate_error","max_force","max_added_accel","committed_work","committed_work_budget","committed_net_force_norm","committed_net_force_budget","committed_torque_y","committed_torque_budget","max_commit_force_error","manufacture_max_residual","manufacture_residual_budget","manufacture_force_budget"};for(const char* n:names)f<<','<<n;}
static void StatsWrite(std::ostream& f,const Stats& s){const double values[]={s.edges,s.max_degree,s.max_condition,s.gamma64,s.dmax_unit,s.alpha_dt_dmax,s.work,s.form,s.work_plus_2form,s.work_budget,s.work_defect_prediction,s.work_certificate_error,s.max_normal_defect,s.max_normal_budget_fraction,s.net_force_norm,s.net_force_budget,s.torque_y,s.torque_budget,s.torque_defect_prediction,s.torque_certificate_error,s.max_force,s.max_added_accel,s.committed_work,s.committed_work_budget,s.committed_net_force_norm,s.committed_net_force_budget,s.committed_torque_y,s.committed_torque_budget,s.max_commit_force_error,s.manufacture_max_residual,s.manufacture_residual_budget,s.manufacture_force_budget};for(double v:values){Need(Finite(v),"Nonfinite candidate metric");f<<','<<v;}}
struct Edge{unsigned i,j;tdouble3 d;double weight,eta0,beta0;};
struct Graph{
  std::vector<tdouble3> x,v;std::vector<double> V,rho,mass,degree,condition;std::vector<Mat2> M;std::vector<Edge> edges;double G=0,h=0,gamma=0,dmax=0,maxdegree=0,maxcond=0;
  explicit Graph(unsigned n):x(n),v(n),V(n),rho(n),mass(n),degree(n),condition(n),M(n){}
  void Prepare(){
    std::vector<unsigned> count(x.size());for(const auto& e:edges){Outer(M[e.i],e.d,e.d,e.eta0*V[e.j]*e.weight);Outer(M[e.j],e.d,e.d,e.eta0*V[e.i]*e.weight);degree[e.i]+=e.beta0;degree[e.j]+=e.beta0;count[e.i]++;count[e.j]++;}
    for(unsigned i=0;i<x.size();i++){M[i].zx=M[i].xz;const auto a=M[i];const double scale=(std::max)({fabs(a.xx),fabs(a.xz),fabs(a.zz)});Need(scale>0&&Finite(scale),"Empty matched LS moment; no skipped node");const double aa=a.xx/scale,b=a.xz/scale,c=a.zz/scale,det=aa*c-b*b;Need(aa>0&&c>0&&det>128.*DBL_EPSILON*(aa*c+b*b),"Rank-deficient matched2D LS moment; no regularization");const double large=.5*(aa+c+hypot(aa-c,2*b)),eigenlo=det/large;condition[i]=large/eigenlo;maxcond=(std::max)(maxcond,condition[i]);maxdegree=(std::max)(maxdegree,double(count[i]));dmax=(std::max)(dmax,degree[i]/mass[i]);}
    const double ne=64.*double(x.size()+edges.size()+unsigned(maxdegree)+1)*DBL_EPSILON;Need(ne<1.,"Invalid declared double gamma");gamma=ne/(1.-ne);
  }
  std::vector<Mat2> Fit(const std::vector<tdouble3>& velocity)const{
    std::vector<Mat2> N(x.size()),L(x.size());for(const auto& e:edges){const auto dv=velocity[e.i]-velocity[e.j];Outer(N[e.i],dv,e.d,e.eta0*V[e.j]*e.weight);Outer(N[e.j],dv,e.d,e.eta0*V[e.i]*e.weight);}
    for(unsigned i=0;i<x.size();i++){const auto a=M[i],b=N[i];const double scale=(std::max)({fabs(a.xx),fabs(a.xz),fabs(a.zz)}),aa=a.xx/scale,bb=a.xz/scale,c=a.zz/scale,den=scale*(aa*c-bb*bb);L[i]={ (b.xx*c-b.xz*bb)/den,(-b.xx*bb+b.xz*aa)/den,(b.zx*c-b.zz*bb)/den,(-b.zx*bb+b.zz*aa)/den};Need(Finite(MN(L[i])),"Nonfinite unregularized LS solution");}return L;
  }
};
struct Evaluation{Stats s;std::vector<tdouble3> force;std::vector<Mat2> L;};
static Evaluation Evaluate(const Graph& g,const std::vector<tdouble3>& v,double alpha){
  Evaluation r;r.force.assign(v.size(),TDouble3(0));r.L=g.Fit(v);r.s.edges=double(g.edges.size());r.s.max_degree=g.maxdegree;r.s.max_condition=g.maxcond;r.s.gamma64=g.gamma;r.s.dmax_unit=g.dmax;
  std::vector<Mat2> defect(v.size());std::vector<double> defectScale(v.size()),forceScale(v.size());double rawScale=0,forcePairs=0,edgeVelocity=0;
  for(const auto& e:g.edges){const auto dv=v[e.i]-v[e.j],pi=Mul(r.L[e.i],e.d),pj=Mul(r.L[e.j],e.d),ri=dv-pi,rj=dv-pj;const double vv=Len(dv),li=Len(pi),lj=Len(pj),distance=Len(e.d);const auto f=(ri+rj)*(-.5*alpha*e.beta0);r.force[e.i]=r.force[e.i]+f;r.force[e.j]=r.force[e.j]-f;Outer(defect[e.i],ri,e.d,e.beta0);Outer(defect[e.j],rj,e.d,e.beta0);defectScale[e.i]+=e.beta0*(vv+li)*distance;defectScale[e.j]+=e.beta0*(vv+lj)*distance;forceScale[e.i]+=alpha*e.beta0*(vv+li+lj);forceScale[e.j]+=alpha*e.beta0*(vv+li+lj);r.s.form+=.25*alpha*e.beta0*(Dot(ri,ri)+Dot(rj,rj));rawScale+=alpha*e.beta0*(Dot(dv,dv)+Dot(pi,pi)+Dot(pj,pj));forcePairs+=2*Len(f);edgeVelocity=(std::max)(edgeVelocity,vv+li+lj);r.s.manufacture_max_residual=(std::max)({r.s.manufacture_max_residual,Len(ri),Len(rj)});}
  tdouble3 net=TDouble3(0);double contraction=0,normalWorkBudget=0,normalTorqueBudget=0,torqueScale=0,nodePowerScale=0;
  for(unsigned i=0;i<v.size();i++){const double dn=MN(defect[i]),budget=4*g.gamma*(1+g.condition[i])*defectScale[i];Need(dn<=budget,"Matched LS normal equation exceeds declared forward budget");r.s.max_normal_defect=(std::max)(r.s.max_normal_defect,dn);r.s.max_normal_budget_fraction=(std::max)(r.s.max_normal_budget_fraction,budget?dn/budget:0.);contraction+=MDot(r.L[i],defect[i]);normalWorkBudget+=.5*alpha*MN(r.L[i])*budget;normalTorqueBudget+=alpha*budget;net=net+r.force[i];r.s.work+=Dot(v[i],r.force[i]);r.s.torque_y+=g.x[i].z*r.force[i].x-g.x[i].x*r.force[i].z;r.s.torque_defect_prediction-=.5*alpha*(defect[i].xz-defect[i].zx);torqueScale+=fabs(g.x[i].z*r.force[i].x)+fabs(g.x[i].x*r.force[i].z);nodePowerScale+=fabs(v[i].x*r.force[i].x)+fabs(v[i].z*r.force[i].z);r.s.max_force=(std::max)(r.s.max_force,Len(r.force[i]));r.s.manufacture_force_budget=(std::max)(r.s.manufacture_force_budget,4*g.gamma*(1+g.condition[i])*forceScale[i]);}
  r.s.work_plus_2form=r.s.work+2*r.s.form;r.s.work_defect_prediction=-.5*alpha*contraction;r.s.work_certificate_error=r.s.work_plus_2form-r.s.work_defect_prediction;r.s.work_budget=g.gamma*(rawScale+nodePowerScale+2*r.s.form)+normalWorkBudget;r.s.net_force_norm=Len(net);r.s.net_force_budget=g.gamma*forcePairs;r.s.torque_budget=g.gamma*torqueScale+normalTorqueBudget;r.s.torque_certificate_error=r.s.torque_y-r.s.torque_defect_prediction;r.s.manufacture_residual_budget=4*g.gamma*(1+g.maxcond)*edgeVelocity;
  Need(fabs(r.s.work_certificate_error)<=g.gamma*(rawScale+nodePowerScale+2*r.s.form)&&fabs(r.s.torque_certificate_error)<=g.gamma*(torqueScale+fabs(r.s.torque_defect_prediction))&&fabs(r.s.work_plus_2form)<=r.s.work_budget&&r.s.work<=r.s.work_budget&&r.s.net_force_norm<=r.s.net_force_budget&&fabs(r.s.torque_y)<=r.s.torque_budget,"Damping quadratic/global force/torque certificate failed");return r;
}

