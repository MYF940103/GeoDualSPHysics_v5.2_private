"""Closed/open conservative Darcy total flux and work-paired constant-pressure constraint.

Private total-Lagrangian small-strain Cryer experiment, constant hydraulic conductivity.
K uses P1 element gradients; HT is the transpose of integral N_i grad(N_j).
"""
from cryer_coupled_shell_modes import np, T, RHOW
from cryer_tet_darcy_spectrum import assemble
from cryer_tet_mechanics import TetMechanics
from c04_p3_pressure_component import K as CONDUCTIVITY, GAMMA
from scipy.sparse.linalg import LinearOperator


class FaceFluxPressure:
    def __init__(self,mechanics,geometry):
        self.m=mechanics
        *_,self.K=assemble(geometry)
        self.row=np.asarray(abs(self.K).sum(axis=1)).ravel()
        self.ones=np.ones(self.m.n)
        self.b=self.m.pressure_force(self.ones)
        self.bm=self.b/self.m.mass[:,None]
        self.closed_response=float(np.sum(self.b*self.bm))
        self.ell=sum(H.T@self.bm[:,d] for d,H in enumerate(self.m.HT))/self.closed_response
        self.fs=np.zeros(self.m.n,dtype=bool)
        self.fs[self.m.surface]=True
        if min(self.row)<=0 or abs(self.ell.sum()-1)>1.e-10:
            raise ValueError("Broken row budget or constant-pressure work pairing")

    def volume_rate(self,v):
        return float(np.sum(self.b*v))

    def pressure_acceleration(self,p):
        return self.m.pressure_force(p)/self.m.mass[:,None]

    def volume_multiplier(self,base_acceleration,p,target_volume_acceleration=0.):
        # Scalar correction in Pa so b^T(a+M^-1*b*c) equals the requested flux derivative.
        return ((target_volume_acceleration-np.sum(self.b*base_acceleration))/self.closed_response
                -self.ell@p)

    def total_flux(self,p,a):
        # Row returns integrated div(grad(p)+rho*a); prescribed exterior normal flux is zero.
        return -(self.K@p+RHOW*sum(H@a[:,d] for d,H in enumerate(self.m.HT)))

    def sweep(self,q,theta,base_acceleration,drain,target_volume_acceleration=0.):
        # theta and base_acceleration are the held endpoint kinematics/mechanical stress+load.
        a=base_acceleration+self.pressure_acceleration(q)
        r=self.total_flux(q,a)-GAMMA/CONDUCTIVITY*self.m.volume*theta
        q=q+r/self.row
        if drain:
            q[self.fs]=0
        else:
            q+=self.volume_multiplier(base_acceleration,q,target_volume_acceleration)
        return q

    def fixed_endpoint_operator(self,drain):
        active=np.flatnonzero(~self.fs) if drain else np.arange(self.m.n)
        def action(z):
            q=np.zeros(self.m.n,dtype=z.dtype)
            q[active]=z
            a=self.pressure_acceleration(q)
            q=q+self.total_flux(q,a)/self.row
            if not drain:
                q-=self.ell@q
            return q[active]
        return LinearOperator((len(active),len(active)),matvec=action,dtype=np.float64)
