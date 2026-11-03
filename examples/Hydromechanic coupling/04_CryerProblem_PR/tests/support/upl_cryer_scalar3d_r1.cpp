// Standalone 3-D frozen scalar companion; actual Wendland API, NOT a production force/rate call.
#include "FunSphKernel.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace scalar3d {
constexpr int Half=9,Side=2*Half+1,FieldCount=14;
constexpr double Dp=.01,Alpha=2.;
const double H=double(float(.018)),Volume=Dp*Dp*Dp;
struct V { double a[3]={}; double& operator[](int k){return a[k];} double operator[](int k)const{return a[k];} };
struct M { double a[3][3]={}; };
static V Vec(double x,double y,double z){return {{x,y,z}};}
static V operator+(V x,V y){for(int k=0;k<3;k++)x[k]+=y[k];return x;}
static V operator-(V x,V y){for(int k=0;k<3;k++)x[k]-=y[k];return x;}
static V operator*(double s,V x){for(int k=0;k<3;k++)x[k]*=s;return x;}
static double Dot(V x,V y){return x[0]*y[0]+x[1]*y[1]+x[2]*y[2];}
static V Apply(const M& m,V x){V y;for(int a=0;a<3;a++)for(int b=0;b<3;b++)y[a]+=m.a[a][b]*x[b];return y;}
static void Need(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
static M Inverse(const M& x,double& det){
  const double a=x.a[0][0],b=x.a[0][1],c=x.a[0][2],d=x.a[1][0],e=x.a[1][1],f=x.a[1][2],g=x.a[2][0],h=x.a[2][1],i=x.a[2][2];
  det=a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g);Need(std::isfinite(det)&&det>1e-12,"Singular manufactured 3-D correction moment");
  M r;const double q[3][3]={{e*i-f*h,c*h-b*i,b*f-c*e},{f*g-d*i,a*i-c*g,c*d-a*f},{d*h-e*g,b*g-a*h,a*e-b*d}};
  for(int u=0;u<3;u++)for(int v=0;v<3;v++){r.a[u][v]=q[u][v]/det;Need(std::isfinite(r.a[u][v]),"Nonfinite inverse");}return r;
}
static uint32_t Next(uint32_t& s){s^=s<<13;s^=s>>17;s^=s<<5;return s;}
static double Jitter(uint32_t& s){return .3*(double(Next(s))/4294967295.-.5);}
struct Node { int ix=0,iy=0,iz=0,id=0;V x;M c;bool ready=false;double det=0; };
struct Edge { unsigned j;V d,g;double rr2;float fac; };
struct Mesh {
  bool sphere,disorder;std::vector<Node> p;std::vector<int> map;
  fsph::StKWendlandCte kw=fsph::GetKernelWendland_Ctes(false,H);
  float support=float(2*H),support2=support*support,eta2=float((H*.1)*(H*.1));unsigned corrections=0;
  int Index(int x,int y,int z)const{return (z+Half)*Side*Side+(y+Half)*Side+x+Half;}
  Mesh(bool curved,bool jitter):sphere(curved),disorder(jitter),map(Side*Side*Side,-1){
    uint32_t state=20261101;
    for(int z=-Half;z<=Half;z++)for(int y=-Half;y<=Half;y++)for(int x=-Half;x<=Half;x++){
      Node n;n.ix=x;n.iy=y;n.iz=z;n.id=Index(x,y,z);n.x=Vec(x*Dp,y*Dp,z*Dp);
      if(disorder)for(int k=0;k<3;k++)n.x[k]+=Dp*Jitter(state); // Consume same three offsets before either shape selection.
      if(sphere&&Dot(n.x,n.x)>36*Dp*Dp)continue;
      map[n.id]=int(p.size());p.push_back(n);
    }
  }
  std::vector<Edge> Edges(unsigned i)const{
    std::vector<Edge> r;const Node& q=p[i];
    for(int z=q.iz-4;z<=q.iz+4;z++)for(int y=q.iy-4;y<=q.iy+4;y++)for(int x=q.ix-4;x<=q.ix+4;x++){
      if(std::max({std::abs(x),std::abs(y),std::abs(z)})>Half)continue;
      const int j=map[Index(x,y,z)];if(j<0||unsigned(j)==i)continue;
      const V d=q.x-p[j].x;const double rr2=Dot(d,d);if(rr2>double(support2))continue;
      Need(rr2>0,"Coincident manufactured points");const float fac=fsph::GetKernelWendland_Fac(kw,float(H),float(rr2));
      Need(std::isfinite(fac),"Nonfinite kernel factor");r.push_back({unsigned(j),d,double(fac)*d,rr2,fac});
    }return r;
  }
  const M& C(unsigned i){
    Node& q=p[i];if(!q.ready){M moment;for(const Edge& e:Edges(i))for(int a=0;a<3;a++)for(int b=0;b<3;b++)moment.a[a][b]-=Volume*e.d[a]*e.g[b];
      q.c=Inverse(moment,q.det);q.ready=true;corrections++;}return q.c;
  }
  std::vector<unsigned> Receivers()const{
    const std::array<std::array<int,3>,5> indices={{{0,0,0},{4,0,0},{0,4,0},{0,0,4},{3,3,3}}};std::vector<unsigned> r;
    for(unsigned k=0;k<(sphere?5u:1u);k++){const auto a=indices[k];const int i=map[Index(a[0],a[1],a[2])];Need(i>=0,"Predeclared receiver missing");r.push_back(unsigned(i));}return r;
  }
};
struct Row { std::vector<Edge> e;std::vector<double> w,a;V lx,first;M gx,second;double cdelta=0; };
struct Rows {
  Mesh& m;int method;double eta;std::map<unsigned,Row> saved;
  Rows(Mesh& mesh,int which,double regularization):m(mesh),method(which),eta(regularization){}
  const Row& Get(unsigned i){
    auto found=saved.find(i);if(found!=saved.end())return found->second;
    Row r;r.e=m.Edges(i);const M ci=m.C(i);
    for(const Edge& e:r.e){
      const M cj=m.C(e.j);V cg=Apply(ci,e.g);
      for(int a=0;a<3;a++)for(int b=0;b<3;b++)r.cdelta=std::max(r.cdelta,std::abs(ci.a[a][b]-cj.a[a][b]));
      if(method==1)cg=.5*(cg+Apply(cj,e.g)); // Real Cavg, never a cloned neighbor C.
      const double w=2*Volume*Dot(e.d,cg)/(e.rr2+eta);r.w.push_back(w);r.lx=r.lx+w*e.d;
      const V b=Volume*Apply(ci,e.g);
      for(int a=0;a<3;a++)for(int c=0;c<3;c++)r.gx.a[a][c]-=b[a]*e.d[c];
    }
    for(unsigned k=0;k<r.e.size();k++){
      const Edge& e=r.e[k];const double a=-r.w[k]-Dot(Volume*Apply(ci,e.g),r.lx);r.a.push_back(a);r.first=r.first-a*e.d;
      for(int u=0;u<3;u++)for(int v=0;v<3;v++)r.second.a[u][v]+=.5*a*e.d[u]*e.d[v];
    }return saved.emplace(i,std::move(r)).first->second;
  }
};
static const char* Fields[FieldCount]={"constant","affine_x","affine_y","affine_z","affine_xyz","quadratic_x","quadratic_y","quadratic_z","quadratic_xy","quadratic_xz","quadratic_yz","quadratic_mix","quadratic_isotropic","smooth_cos_xyz"};
static double Field(int f,V x){
  switch(f){case 0:return 7;case 1:return x[0];case 2:return x[1];case 3:return x[2];case 4:return 1+3*x[0]-2*x[1]+.5*x[2];
    case 5:return .5*Alpha*x[0]*x[0];case 6:return .5*Alpha*x[1]*x[1];case 7:return .5*Alpha*x[2]*x[2];
    case 8:return Alpha*x[0]*x[1];case 9:return Alpha*x[0]*x[2];case 10:return Alpha*x[1]*x[2];
    case 11:return Alpha*(.5*x[0]*x[0]+x[1]*x[1]+1.5*x[2]*x[2]+.3*x[0]*x[1]-.2*x[0]*x[2]+.4*x[1]*x[2]);
    case 12:return .5*Alpha*Dot(x,x);default:{const double k=PI/(12*Dp);return cos(k*x[0])*cos(k*x[1])*cos(k*x[2]);}}
}
static double ExactLap(int f,V x){if(f>=5&&f<=7)return Alpha;if(f==11)return 6*Alpha;if(f==12)return 3*Alpha;if(f==13){const double k=PI/(12*Dp);return -3*k*k*Field(f,x);}return 0;}
static V ExactGrad(int f,V x){
  switch(f){case 1:return Vec(1,0,0);case 2:return Vec(0,1,0);case 3:return Vec(0,0,1);case 4:return Vec(3,-2,.5);
    case 5:return Vec(Alpha*x[0],0,0);case 6:return Vec(0,Alpha*x[1],0);case 7:return Vec(0,0,Alpha*x[2]);
    case 8:return Alpha*Vec(x[1],x[0],0);case 9:return Alpha*Vec(x[2],0,x[0]);case 10:return Alpha*Vec(0,x[2],x[1]);
    case 11:return Alpha*Vec(x[0]+.3*x[1]-.2*x[2],2*x[1]+.3*x[0]+.4*x[2],3*x[2]-.2*x[0]+.4*x[1]);case 12:return Alpha*x;
    case 13:{const double k=PI/(12*Dp);return -k*Vec(sin(k*x[0])*cos(k*x[1])*cos(k*x[2]),cos(k*x[0])*sin(k*x[1])*cos(k*x[2]),cos(k*x[0])*cos(k*x[1])*sin(k*x[2]));}default:return {};}
}
struct Value { double lp=0,star=0,action=0,scale=0;V grad; };
static Value Evaluate(Mesh& m,unsigned i,const Row& r,int f){
  Value v;const M ci=m.C(i);const double fi=Field(f,m.p[i].x);v.scale=std::abs(fi);
  for(unsigned k=0;k<r.e.size();k++){const Edge& e=r.e[k];const double fj=Field(f,m.p[e.j].x),df=fj-fi;
    v.grad=v.grad+(Volume*df)*Apply(ci,e.g);v.lp-=r.w[k]*df;v.action+=r.a[k]*df;v.scale=std::max(v.scale,std::abs(fj));}
  v.star=v.lp-Dot(v.grad,r.lx);Need(std::isfinite(v.star)&&std::isfinite(v.action),"Nonfinite scalar response");return v;
}
static void WriteV(std::ostream& s,V v){for(int k=0;k<3;k++)s<<','<<v[k];}
static void WriteM(std::ostream& s,const M& m){for(int a=0;a<3;a++)for(int b=0;b<3;b++)s<<','<<m.a[a][b];}
struct Gates { unsigned rows=0,failed=0;double constant=0,gradient=0,affine=0; };
static void Gate(std::ofstream& out,Gates& g,const std::string& prefix,const char* name,double error,double limit){
  const bool pass=std::isfinite(error)&&error<=limit;out<<prefix<<','<<name<<','<<error<<','<<limit<<','<<pass<<'\n';g.rows++;if(!pass)g.failed++;
}
static void Diagnose(const std::filesystem::path& out){
  std::ofstream fields(out/"fields.csv"),moments(out/"moments.csv"),neighbors(out/"neighbors.csv"),budgets(out/"budgets.csv"),gates(out/"arithmetic.csv"),identity(out/"isotropic_clone.csv");
  for(auto* s:{&fields,&moments,&neighbors,&budgets,&gates,&identity}){Need(bool(*s),"New diagnostic output unavailable");*s<<std::setprecision(17);}
  fields<<"shape,disorder,eta,method,receiver_id,field,x,y,z,input,lp,Lstar,exact_lap,error,grad_x,grad_y,grad_z,exact_grad_x,exact_grad_y,exact_grad_z,grad_error,coefficient_action_error,local_max_abs_field\n";
  moments<<"shape,disorder,eta,method,receiver_id,neighbors,eta2,receiver_moment_determinant";for(const char* p:{"Ci","Gx","Lstar_second"})for(int a=0;a<3;a++)for(int b=0;b<3;b++)moments<<','<<p<<a<<b;
  moments<<",lx,ly,lz,Lstar_first_x,Lstar_first_y,Lstar_first_z,second_minus_I_Frobenius,neighbor_C_max_difference,raw_pair_volume_defect_max,star_pair_volume_defect_max,star_pair_volume_defect_sumabs,star_pair_relative_max\n";
  neighbors<<"shape,disorder,receiver_id,neighbor_id,dx,dy,dz,rr2_double,kernel_fac_float";for(const char* p:{"Cj","Cavg"})for(int a=0;a<3;a++)for(int b=0;b<3;b++)neighbors<<','<<p<<a<<b;neighbors<<'\n';
  budgets<<"shape,disorder,eta,method,field,selected_receivers,selected_volume,selected_V_Lstar,selected_V_exact,selected_budget_difference,global_or_boundary_flux_proof\n";
  gates<<"shape,disorder,eta,method,receiver_id,field,gate,error,threshold,pass\n";
  identity<<"disorder,eta,eta2,common_Cj_equals_Ci_counterfactual,conditional_regular_eta0_identity,alpha,expected_3alpha,clone_receiverC_Lstar,clone_error,real_symC_Lstar,neighbor_C_variation,coefficient3_counterfactual,expected_coefficient3_4p5alpha\n";
  Gates result;unsigned fieldRows=0,momentRows=0,neighborRows=0,budgetRows=0,cloneRows=0,receiverRows=0,totalNodes=0,totalCorrections=0;
  for(bool sphere:{false,true})for(bool disorder:{false,true}){
    Mesh m(sphere,disorder);const auto receivers=m.Receivers();totalNodes+=unsigned(m.p.size());receiverRows+=unsigned(receivers.size());const std::string shape=sphere?"sphere_cut":"full_support";
    for(int eta=0;eta<2;eta++)for(int method=0;method<2;method++){
      Rows rows(m,method,eta?double(m.eta2):0);const char* label=method?"symC_star":"receiverC_star";double actualBudget[FieldCount]={},exactBudget[FieldCount]={};
      for(unsigned i:receivers){
        const Row& r=rows.Get(i);const M ci=m.C(i);double rawdef=0,stardef=0,defsum=0,rel=0,secondError=0;
        for(unsigned k=0;k<r.e.size();k++){
          const Edge& e=r.e[k];const Row& reverse=rows.Get(e.j);unsigned q=0;while(q<reverse.e.size()&&reverse.e[q].j!=i)q++;Need(q<reverse.e.size(),"Missing reciprocal geometric neighbor");
          const double aa=Volume*r.a[k],bb=Volume*reverse.a[q],delta=std::abs(aa-bb);
          rawdef=std::max(rawdef,Volume*std::abs(r.w[k]-reverse.w[q]));stardef=std::max(stardef,delta);defsum+=delta;
          if(std::abs(aa)+std::abs(bb)>0)rel=std::max(rel,delta/(std::abs(aa)+std::abs(bb)));
          if(eta==0&&method==0){neighbors<<shape<<','<<disorder<<','<<m.p[i].id<<','<<m.p[e.j].id;WriteV(neighbors,e.d);neighbors<<','<<e.rr2<<','<<e.fac;
            const M cj=m.C(e.j);M avg;for(int a=0;a<3;a++)for(int b=0;b<3;b++)avg.a[a][b]=.5*(ci.a[a][b]+cj.a[a][b]);WriteM(neighbors,cj);WriteM(neighbors,avg);neighbors<<'\n';neighborRows++;}
        }
        for(int a=0;a<3;a++)for(int b=0;b<3;b++){const double error=r.second.a[a][b]-(a==b?1.:0.);secondError+=error*error;}
        moments<<shape<<','<<disorder<<','<<eta<<','<<label<<','<<m.p[i].id<<','<<r.e.size()<<','<<rows.eta<<','<<m.p[i].det;WriteM(moments,ci);WriteM(moments,r.gx);WriteM(moments,r.second);WriteV(moments,r.lx);WriteV(moments,r.first);
        moments<<','<<sqrt(secondError)<<','<<r.cdelta<<','<<rawdef<<','<<stardef<<','<<defsum<<','<<rel<<'\n';momentRows++;
        for(int f=0;f<FieldCount;f++){
          const Value v=Evaluate(m,i,r,f);const double exact=ExactLap(f,m.p[i].x);const V eg=ExactGrad(f,m.p[i].x);const double ge=sqrt(Dot(v.grad-eg,v.grad-eg));
          fields<<shape<<','<<disorder<<','<<eta<<','<<label<<','<<m.p[i].id<<','<<Fields[f];WriteV(fields,m.p[i].x);fields<<','<<Field(f,m.p[i].x)<<','<<v.lp<<','<<v.star<<','<<exact<<','<<v.star-exact;WriteV(fields,v.grad);WriteV(fields,eg);fields<<','<<ge<<','<<v.action-v.star<<','<<v.scale<<'\n';fieldRows++;
          const std::string prefix=shape+','+std::to_string(disorder)+','+std::to_string(eta)+','+label+','+std::to_string(m.p[i].id)+','+Fields[f];
          if(f==0){Gate(gates,result,prefix,"constant",std::abs(v.star),1e-10);result.constant=std::max(result.constant,std::abs(v.star));}
          if(f>=1&&f<=4){Gate(gates,result,prefix,"affine_gradient",ge,1e-10);Gate(gates,result,prefix,"affine_star",std::abs(v.star),1e-8);result.gradient=std::max(result.gradient,ge);result.affine=std::max(result.affine,std::abs(v.star));}
          actualBudget[f]+=Volume*v.star;exactBudget[f]+=Volume*exact;
        }
      }
      for(int f=0;f<FieldCount;f++){budgets<<shape<<','<<disorder<<','<<eta<<','<<label<<','<<Fields[f]<<','<<receivers.size()<<','<<receivers.size()*Volume<<','<<actualBudget[f]<<','<<exactBudget[f]<<','<<actualBudget[f]-exactBudget[f]<<",0\n";budgetRows++;}
      if(!sphere&&method==0){
        const unsigned i=receivers.front();const Row& cloned=rows.Get(i);const Value cv=Evaluate(m,i,cloned,12);Rows sym(m,1,rows.eta);const Row& actual=sym.Get(i);const Value sv=Evaluate(m,i,actual,12);
        identity<<disorder<<','<<eta<<','<<rows.eta<<",1,"<<(!disorder&&eta==0)<<','<<Alpha<<','<<3*Alpha<<','<<cv.star<<','<<cv.star-3*Alpha<<','<<sv.star<<','<<actual.cdelta<<','<<1.5*cv.star<<','<<4.5*Alpha<<'\n';cloneRows++;
      }
    }totalCorrections+=m.corrections;
  }
  Need(fieldRows==672&&momentRows==48&&budgetRows==224&&result.rows==432&&cloneRows==4&&receiverRows==12,"Declared bounded diagnostic coverage differs");
  for(auto* s:{&fields,&moments,&neighbors,&budgets,&gates,&identity}){s->flush();Need(bool(*s),"Diagnostic CSV write failed");}
  std::ofstream done(out/"completion.json");Need(bool(done),"Completion unavailable");done<<std::setprecision(17)<<std::boolalpha
    <<"{\"stage\":\"upl_cryer_scalar3d_r1\",\"passed\":"<<(result.failed==0)<<",\"diagnostic_only\":true,\"production_call_regression\":false,\"physical_acceptance\":false,\"public_3D_admitted\":false,\"physical_steps_advanced\":0,\"actual_force_or_complete_rate_calls\":0,\"source_cloud_max_nodes\":6859,\"total_source_nodes_four_clouds\":"<<totalNodes<<",\"lazy_correction_matrices\":"<<totalCorrections<<",\"receiver_instances\":12,\"moment_rows\":"<<momentRows<<",\"field_rows\":"<<fieldRows<<",\"neighbor_rows\":"<<neighborRows<<",\"budget_rows\":"<<budgetRows<<",\"isotropic_clone_rows\":"<<cloneRows<<",\"arithmetic_rows\":"<<result.rows<<",\"arithmetic_failures\":"<<result.failed<<",\"constant_abs_max\":"<<result.constant<<",\"affine_gradient_abs_max\":"<<result.gradient<<",\"affine_star_abs_max\":"<<result.affine<<",\"dp_m\":"<<Dp<<",\"h_m\":"<<H<<",\"uniform_volume_m3\":"<<Volume<<",\"current_Eta2_float\":"<<double(float((H*.1)*(H*.1)))<<",\"kernel_3D_awen_float\":"<<double(fsph::GetKernelWendland_Ctes(false,H).awen)<<",\"kernel_3D_bwen_float\":"<<double(fsph::GetKernelWendland_Ctes(false,H).bwen)<<",\"field_storage_binary64_not_production_pressure_float\":true,\"quadratic_or_smooth_accuracy_gate\":false,\"full_matrix_or_spectrum_formed\":false,\"global_conservation_or_surface_flux_proved\":false}\n";
  done.flush();Need(bool(done),"Completion write failed");if(result.failed)throw std::runtime_error("Predeclared constant/affine arithmetic gate failed; outputs retained");
}
} // namespace scalar3d
int main(int argc,char** argv){
  if(argc!=3||std::string(argv[1])!="--out"){std::cerr<<"usage: upl_cryer_scalar3d_r1.exe --out FRESH_OUTPUT_DIRECTORY\n";return 2;}
  try{const std::filesystem::path out(argv[2]);scalar3d::Need(!std::filesystem::exists(out),"Retained output directory protected");scalar3d::Need(std::filesystem::create_directories(out),"Cannot create fresh output");scalar3d::Diagnose(out);return 0;}
  catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
