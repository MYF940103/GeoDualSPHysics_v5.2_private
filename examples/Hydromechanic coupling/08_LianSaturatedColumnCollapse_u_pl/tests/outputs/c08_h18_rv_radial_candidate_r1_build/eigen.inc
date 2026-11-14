static void DiagnosticEigen3D(const tsymatrix3f &sigma,float eval[3],float evec[3][3]){
  float a[3][3]={
    {sigma.xx,sigma.xy,sigma.xz},
    {sigma.xy,sigma.yy,sigma.yz},
    {sigma.xz,sigma.yz,sigma.zz}
  };
  evec[0][0]=1.f; evec[0][1]=0.f; evec[0][2]=0.f;
  evec[1][0]=0.f; evec[1][1]=1.f; evec[1][2]=0.f;
  evec[2][0]=0.f; evec[2][1]=0.f; evec[2][2]=1.f;
  for(int it=0;it<16;it++){
    int p=0,q=1;
    float maxoff=fabsf(a[0][1]);
    const float a02=fabsf(a[0][2]);
    const float a12=fabsf(a[1][2]);
    if(a02>maxoff){maxoff=a02; p=0; q=2;}
    if(a12>maxoff){maxoff=a12; p=1; q=2;}
    const float scale=fabsf(a[0][0])+fabsf(a[1][1])+fabsf(a[2][2])+1.f;
    if(maxoff<=1e-6f*scale)break;
    const float phi=0.5f*atan2f(2.f*a[p][q],a[q][q]-a[p][p]);
    const float c=cosf(phi);
    const float sn=sinf(phi);
    for(int k=0;k<3;k++){
      const float akp=a[k][p];
      const float akq=a[k][q];
      a[k][p]=c*akp-sn*akq;
      a[k][q]=sn*akp+c*akq;
    }
    for(int k=0;k<3;k++){
      const float apk=a[p][k];
      const float aqk=a[q][k];
      a[p][k]=c*apk-sn*aqk;
      a[q][k]=sn*apk+c*aqk;
    }
    for(int k=0;k<3;k++){
      const float vkp=evec[k][p];
      const float vkq=evec[k][q];
      evec[k][p]=c*vkp-sn*vkq;
      evec[k][q]=sn*vkp+c*vkq;
    }
  }
  eval[0]=a[0][0];
  eval[1]=a[1][1];
  eval[2]=a[2][2];
}

//==============================================================================
/// Computes Bui 2008 artificial stress tensor in global coordinates.
//==============================================================================
