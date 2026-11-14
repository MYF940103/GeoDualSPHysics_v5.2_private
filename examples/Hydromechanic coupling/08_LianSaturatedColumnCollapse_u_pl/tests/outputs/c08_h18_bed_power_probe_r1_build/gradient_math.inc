namespace bedlit {
static tfloat3 ApplyGradCorr(const tfloat3 &grad,const tmatrix3d &corr){
  return(TFloat3(
    float(double(grad.x)*corr.a11 + double(grad.y)*corr.a12 + double(grad.z)*corr.a13)
   ,float(double(grad.x)*corr.a21 + double(grad.y)*corr.a22 + double(grad.z)*corr.a23)
   ,float(double(grad.x)*corr.a31 + double(grad.y)*corr.a32 + double(grad.z)*corr.a33)));
}
void GetStrainSpinRateTensor_sym(tfloat3 gradvp1_xx_xy_xz,tfloat3 gradvp1_yx_yy_yz,tfloat3 gradvp1_zx_zy_zz
  ,tsymatrix3f &e_tensor,tfloat3 &w_tensor_xy_yz_xz)
{
  //Build strain rate tensor
  e_tensor.xx=gradvp1_xx_xy_xz.x;		
  e_tensor.yy=gradvp1_yx_yy_yz.y;	  
  e_tensor.zz=gradvp1_zx_zy_zz.z;
  e_tensor.xy=0.5f*(gradvp1_xx_xy_xz.y+gradvp1_yx_yy_yz.x);
  e_tensor.yz=0.5f*(gradvp1_yx_yy_yz.z+gradvp1_zx_zy_zz.y);
  e_tensor.xz=0.5f*(gradvp1_xx_xy_xz.z+gradvp1_zx_zy_zz.x);

  //Build spin rate tensor
  w_tensor_xy_yz_xz.x = 0.5f*(gradvp1_xx_xy_xz.y-gradvp1_yx_yy_yz.x);
  w_tensor_xy_yz_xz.y = 0.5f*(gradvp1_yx_yy_yz.z-gradvp1_zx_zy_zz.y);
  w_tensor_xy_yz_xz.z = 0.5f*(gradvp1_xx_xy_xz.z-gradvp1_zx_zy_zz.x);
}
void GetStressRateTensor_Elastic(tsymatrix3f e_tensor,tfloat3 w_tensor_xy_yz_xz
,tsymatrix3f sigma,const float DP_K, const float DP_G,tsymatrix3f &rsigma)
{
  //Build Elastic stiffness matrix
	float K4G3 = float(DP_K + 4.*DP_G / 3.);
	float K2G3 = float(DP_K - 2.*DP_G / 3.);
	float m_a11 = K4G3; float m_a12 = K2G3; float m_a13 = K2G3;
	float m_a21 = K2G3; float m_a22 = K4G3; float m_a23 = K2G3;
	float m_a31 = K2G3; float m_a32 = K2G3; float m_a33 = K4G3; 

  //Get stress, stran rate and spin rate
  float sigmaxx = sigma.xx;
  float sigmaxy = sigma.xy;
  float sigmaxz = sigma.xz;
  float sigmayy = sigma.yy;
  float sigmayz = sigma.yz;
  float sigmazz = sigma.zz;

  float exx = e_tensor.xx;
  float exy = e_tensor.xy;
  float exz = e_tensor.xz;
  float eyy = e_tensor.yy;
  float eyz = e_tensor.yz;
  float ezz = e_tensor.zz;

  float wxy = w_tensor_xy_yz_xz.x;
  float wyz = w_tensor_xy_yz_xz.y;
  float wxz = w_tensor_xy_yz_xz.z;
  
  //Rigid-body contribution W*sigma-sigma*W, with W=(grad(v)-grad(v)^T)/2.
  float Jxx = 2.f*sigmaxy*wxy + 2.f*sigmaxz*wxz;
  float Jxy = -sigmaxx*wxy + sigmayy*wxy + sigmaxz*wyz + sigmayz*wxz;
  float Jxz = -sigmaxx*wxz - sigmaxy*wyz + sigmayz*wxy + sigmazz*wxz;
  float Jyy = -2.f*sigmaxy*wxy + 2.f*sigmayz*wyz;
  float Jyz = -sigmaxy*wxz - sigmaxz*wxy - sigmayy*wyz + sigmazz*wyz;
  float Jzz = -2.f*sigmaxz*wxz - 2.f*sigmayz*wyz;
 
  //Construct stress rate equation
  rsigma.xx = (m_a11*exx+m_a12*eyy+m_a13*ezz)+Jxx;
  rsigma.yy = (m_a21*exx+m_a22*eyy+m_a23*ezz)+Jyy;
  rsigma.zz = (m_a31*exx+m_a32*eyy+m_a33*ezz)+Jzz;
  rsigma.xy = 2.f*DP_G*exy+Jxy;
  rsigma.yz = 2.f*DP_G*eyz+Jyz;
  rsigma.xz = 2.f*DP_G*exz+Jxz;  
}
}
