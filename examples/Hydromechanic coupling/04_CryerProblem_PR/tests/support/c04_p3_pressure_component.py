"""Frozen-reference 3D Cryer P3 pressure rows, assembled from the retained particle cloud.

The hydraulic rows use the original uniform native soil volume. The mechanics caller
supplies theta, acceleration and its divergence at each actual pressure substage.
"""
from pathlib import Path
import argparse
import os
from time import perf_counter
from scipy import sparse
from cryer_coupled_shell_modes import Graph, T, RHOW, np, pd

CACHE=T/"outputs/c04_p3_pressure_component_r1.npz"
K=float(np.float32(1e-5))
GAMMA=RHOW*9.80665


class CryerSPHPressure:
    def __init__(self,E,S0,fs,normal_lx,ids):
        self.E=E
        self.S0=S0
        self.fs=fs
        self.normal_lx=normal_lx
        self.ids=ids

    @classmethod
    def from_graph(cls,g):
        ids=np.arange(8,37181,dtype=np.int32)
        fs_table=pd.read_csv(T/"figures/upl_cryer_fs_audit_r1.csv",
                              usecols=["id","actual_fstype","native_normal_x","native_normal_y","native_normal_z"])
        assert np.array_equal(fs_table.id,ids)
        fs=fs_table.actual_fstype.isin([2,3]).to_numpy()
        normal=fs_table[["native_normal_x","native_normal_y","native_normal_z"]].to_numpy()
        assert np.array_equal(fs,g.shell==19) and fs.sum()==5153
        lengths=np.linalg.norm(normal[fs],axis=1)
        assert np.all(np.isfinite(lengths)) and min(lengths)>0
        normal[fs]/=lengths[:,None]
        normal_lx=np.zeros_like(g.x)
        normal_lx[fs]=normal[fs]*np.einsum("ij,ij->i",normal[fs],g.lx[fs])[:,None]
        S0=-g.sumw
        assert np.all(S0>0)
        # L(p) has a Taylor-defect term -grad(p).(lx - normal_lx).
        coeff=np.einsum("ikl,ik->il",g.C,g.lx-normal_lx)
        diag=np.einsum("il,il->i",coeff,g.rows)/S0
        W=g.W
        assert all(np.array_equal(G.indices,W.indices) and np.array_equal(G.indptr,W.indptr) for G in g.raw)
        out=np.empty_like(W.data)
        for start in range(0,g.n,512):
            end=min(start+512,g.n)
            i=np.repeat(np.arange(start,end),np.diff(W.indptr[start:end+1]))
            sl=slice(W.indptr[start],W.indptr[end])
            correction=sum(coeff[i,k]*g.raw[k].data[sl] for k in range(3))
            out[sl]=(-W.data[sl]-correction)/S0[i]
        E=(sparse.csr_matrix((out,W.indices,W.indptr),shape=W.shape)+sparse.diags(diag)).tocsr()
        E.sort_indices()
        assert np.max(abs(E@np.ones(g.n)-1))<2e-12
        return cls(E,S0,fs,normal_lx,ids)

    def save(self,path):
        partial=path.with_suffix(".writing.npz")
        if path.exists() or partial.exists():
            raise FileExistsError(path)
        np.savez(partial,indptr=self.E.indptr,indices=self.E.indices,data=self.E.data,S0=self.S0,
                 fs=self.fs,normal_lx=self.normal_lx,k=K,gamma=GAMMA,rhow=RHOW,ids=self.ids)
        os.rename(partial,path)

    @classmethod
    def load(cls,path=CACHE):
        with np.load(path) as f:
            ids=f["ids"]
            E=sparse.csr_matrix((f["data"],f["indices"],f["indptr"]),shape=(len(ids),len(ids)))
            assert (float(f["k"]),float(f["gamma"]),float(f["rhow"]))==(K,GAMMA,RHOW)
            return cls(E,f["S0"],f["fs"],f["normal_lx"],ids)

    def predict(self,pn,previous,drain):
        p=np.asarray(pn,dtype=np.float64)
        q=(p+.5*(p-np.asarray(previous,dtype=np.float64))).astype(np.float32)
        if drain:
            q[self.fs]=0
        return q

    def sweep(self,q,theta,acceleration,divergence,drain):
        a=np.asarray(acceleration)
        div=np.asarray(divergence)
        assert q.shape==self.S0.shape and theta.shape==div.shape==q.shape and a.shape==(len(q),3)
        # Closed rows use the normal projection. An open surface receives exactly zero.
        rhs=RHOW*(div+np.einsum("ij,ij->i",self.normal_lx,a))-GAMMA/K*theta
        value=self.E@q+rhs/self.S0
        if drain:
            value[self.fs]=0
        if not np.isfinite(value).all():
            raise FloatingPointError("nonfinite P3 iterate")
        return value.astype(np.float32)

    def rounds(self,pn,previous,theta,acceleration,divergence,drain,rounds=3):
        q=self.predict(pn,previous,drain)
        for _ in range(rounds):
            a=acceleration(q)
            q=self.sweep(q,theta,a,divergence(a),drain)
            yield q


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-cache",action="store_true",required=True)
    parser.parse_args()
    if CACHE.exists():
        raise FileExistsError(CACHE)
    start=perf_counter()
    g=Graph()
    p=CryerSPHPressure.from_graph(g)
    p.save(CACHE)
    print(len(p.ids),p.E.nnz,p.S0.min(),p.S0.max(),perf_counter()-start,CACHE,flush=True)
