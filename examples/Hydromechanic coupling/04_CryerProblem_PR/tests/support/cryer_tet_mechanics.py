"""Private fixed-reference 3-D linear-elastic Cryer mechanics, with area-applied traction.

Node slots index the cache native_ids. Strains use engineering shear (xx,yy,zz,xy,yz,xz);
stresses use physical shear in the same order and tension-positive normal components.
"""
import numpy as np
from scipy import sparse


class TetMechanics:
    def __init__(self, cache, young=2.e6, poisson=.3):
        with np.load(cache) as z:
            self.x=z["x0"]; self.ids=z["native_ids"]; self.mass=z["native_mass_kg"]
            self.surface=z["native_surface"]; self.shells=z["material_shell"]
            self.native_volume=z["native_volume_m3"]
            t=z["tets"];v=z["Ve"];g=z["Ve_gradN"];f=z["faces"];area=z["face_area_out"]
        if not (young>0 and -1<poisson<.5):
            raise ValueError("Invalid isotropic elasticity constants.")
        self.young=young;self.poisson=poisson
        self.mu=young/(2*(1+poisson))
        self.lam=young*poisson/((1+poisson)*(1-2*poisson))
        self.n=len(self.ids)
        self.volume=np.bincount(t.ravel(),weights=np.repeat(v/4,4),minlength=self.n)
        self.unit_surface_force=np.zeros_like(self.x)
        for i in range(3):
            np.add.at(self.unit_surface_force,f[:,i],-area/3)
        # H_j = Vdual*D_j. Nodal strain averages the gradient of each incident tet
        # with its volume/4. H_j.T distributes stress by the negative adjoint.
        shape=(len(t),4,4)
        rows=np.broadcast_to(t[:,:,None],shape).ravel()
        cols=np.broadcast_to(t[:,None,:],shape).ravel()
        self.D=[]; self.HT=[]
        for j in range(3):
            data=np.broadcast_to(.25*g[:,None,:,j],shape).ravel()
            H=sparse.coo_matrix((data,(rows,cols)),shape=(self.n,self.n)).tocsr()
            self.HT.append(H.T.tocsr())
            self.D.append(H.multiply((1/self.volume)[:,None]).tocsr())

    def strain(self,u):
        """The work-conjugate nodal engineering strain or strain rate."""
        gx,gy,gz=(mat@u for mat in self.D)
        return np.column_stack((gx[:,0],gy[:,1],gz[:,2],
                                gx[:,1]+gy[:,0],gy[:,2]+gz[:,1],gx[:,2]+gz[:,0]))

    def divergence(self,u):
        return sum(D@u[:,j] for j,D in enumerate(self.D))

    def elastic_stress(self,eps):
        sigma=eps.copy()
        sigma[:,:3]=2*self.mu*eps[:,:3]+self.lam*eps[:,:3].sum(axis=1)[:,None]
        sigma[:,3:]=self.mu*eps[:,3:]
        return sigma

    def internal_stress(self,sigma):
        """Nodal forces in N from tension-positive effective or total Cauchy stress."""
        return -(self.HT[0]@sigma[:,[0,3,5]]+self.HT[1]@sigma[:,[3,1,4]]
                 +self.HT[2]@sigma[:,[5,4,2]])

    def pressure_force(self,p):
        """Positive compression pressure contributes total stress -p*I."""
        return np.column_stack([H@p for H in self.HT])

    def surface_force(self,q):
        """Compressive uniform scalar pressure on the real boundary triangles."""
        return float(q)*self.unit_surface_force

    def total_force(self,u,p,q):
        """Elastic plus pore pressure plus prescribed traction on the fixed reference."""
        return self.internal_stress(self.elastic_stress(self.strain(u)))+self.pressure_force(p)+self.surface_force(q)

    def acceleration(self,u,p,q):
        return self.total_force(u,p,q)/self.mass[:,None]

    def elastic_energy(self,u):
        eps=self.strain(u)
        return .5*np.sum(self.volume*np.einsum("ij,ij->i",eps,self.elastic_stress(eps)))
