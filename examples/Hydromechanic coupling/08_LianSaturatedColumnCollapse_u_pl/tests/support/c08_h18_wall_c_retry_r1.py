"""Pure, reversible private-source derivation for one dynamic-wall C-quality retry.

Author asset only. Importing this module performs no I/O. The caller must separately
review/admit any private application, build, component, regression or physical run.
The accepted source filenames are deliberately closed to the two mDBC members.
"""

TAG = 'c08_h18_wall_c_retry_r1'


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def _derive(raw, filename, edits):
    need(isinstance(raw, bytes), 'Original source must be bytes')
    # Preserve the original BOM and LF/CRLF bytes; never normalize a frozen source.
    newline = '\r\n' if b'\r\n' in raw else '\n'
    need(b'\r' not in raw.replace(b'\r\n', b''), 'Bare CR source is not admitted')
    if newline == '\r\n':
        need(raw.count(b'\n') == raw.count(b'\r\n'), 'Mixed source line endings are not admitted')
    text = raw.decode('utf-8')
    actual = []
    for label, old, new in edits:
        old, new = old.replace('\n', newline), new.replace('\n', newline)
        need(old != new and text.count(old) == 1, 'Exactly one original anchor required: ' + label)
        need(text.count(new) == 0, 'Candidate or partial derivation already exists: ' + label)
        text = text.replace(old, new, 1)
        actual.append((label, old, new))
    changed = text.encode('utf-8')
    inverse = text
    for label, old, new in reversed(actual):
        need(inverse.count(new) == 1, 'Unique inverse anchor missing: ' + label)
        inverse = inverse.replace(new, old, 1)
    need(inverse.encode('utf-8') == raw, 'Inverse does not restore all original source bytes')
    return changed, dict(stage=TAG, filename=filename, original_bytes=len(raw), candidate_bytes=len(changed),
        source_newline='CRLF' if newline == '\r\n' else 'LF',
        original_BOM_preserved=raw.startswith(b'\xef\xbb\xbf') == changed.startswith(b'\xef\xbb\xbf'),
        exact_inverse_original_bytes=True, replacement_count=len(actual),
        replacements=[dict(label=label, original=old, candidate=new) for label, old, new in actual],
        candidate_is_numerical_change=True, output_only=False, public_source_written=False,
        new_XML_parameters=False, new_class_members=False, public_header_ABI_changed=False,
        solver_invocations=0, reader_invocations=0, build_invocations=0, SHA_scans=0,
        original_positive_C_gate_unchanged=True, original_geometry_threshold_unchanged=True,
        nonfinite_reconstructed_Cdet_retry_added=False, nonfinite_component_retry_added=False,
        invalid_J_retry_added=False, third_fit_added=False, identity_or_centroid_fallback_added=False,
        physical_acceptance=False)


CPU_EDITS = (
    ('writer_bool_commit_contract',
     '      else write(p1,fieldfinal,firstorder? gradfieldx: nullptr,firstorder? gradfieldy: nullptr,firstorder? gradfieldz: nullptr);',
     '      else if(!write(p1,fieldfinal,firstorder? gradfieldx: nullptr,firstorder? gradfieldy: nullptr,firstorder? gradfieldz: nullptr))geometryfailed=true;'),
    ('pressure_writer_accepts',
     '  const auto writepressure=[&](unsigned p,const double *excess,const double*,const double*,const double*){porepress[p]=float(double(porepress0[p])+excess[0]);};',
     '  const auto writepressure=[&](unsigned p,const double *excess,const double*,const double*,const double*){porepress[p]=float(double(porepress0[p])+excess[0]);return true;};'),
    ('SPR_inactive_writer_accepts',
     '    if(mode>=SLIP_NoSlip && BoundModec && BoundModec[p]==BMODE_MDBC2OFF)return;',
     '    if(mode>=SLIP_NoSlip && BoundModec && BoundModec[p]==BMODE_MDBC2OFF)return true;'),
    ('SPR_completed_writer_accepts',
     '''      else{//-Legacy Vel0 keeps wall tangential velocity and mirrors only the normal derivative.
        BoundDerivativeVelc[p]=TFloat3(float(double(v.x)+reflection*normal.x),
          float(double(v.y)+reflection*normal.y),float(double(v.z)+reflection*normal.z));
      }
    }
  };''',
     '''      else{//-Legacy Vel0 keeps wall tangential velocity and mirrors only the normal derivative.
        BoundDerivativeVelc[p]=TFloat3(float(double(v.x)+reflection*normal.x),
          float(double(v.y)+reflection*normal.y),float(double(v.z)+reflection*normal.z));
      }
    }
    return true;
  };'''),
    ('dynamic_state_writer_accepts',
     '''    Velrhopc[p]=TFloat4(0,0,0,RhopZero); //-The physical fixed wall never moves.
    BoundModec[p]=BMODE_MDBC2;
  };''',
     '''    Velrhopc[p]=TFloat4(0,0,0,RhopZero); //-The physical fixed wall never moves.
    BoundModec[p]=BMODE_MDBC2;
    return true;
  };'''),
    ('dynamic_C_writer_defers_finite_nonpositive_commit',
     '''  const auto write=[&](unsigned p,const double *v,const double*,const double*,const double*){
    const tdouble3 q=DynamicPoreWallParity(BoundNormalc[p]);
    CorrMatc[p]=TMatrix3d(v[0],q.x*q.y*v[1],q.x*q.z*v[2],q.y*q.x*v[3],v[4],q.y*q.z*v[5],q.z*q.x*v[6],q.z*q.y*v[7],v[8]);
  };''',
     '''  const auto write=[&](unsigned p,const double *v,const double*,const double*,const double*){
    const tdouble3 q=DynamicPoreWallParity(BoundNormalc[p]);
    const tmatrix3d m=TMatrix3d(v[0],q.x*q.y*v[1],q.x*q.z*v[2],q.y*q.x*v[3],v[4],q.y*q.z*v[5],q.z*q.x*v[6],q.z*q.y*v[7],v[8]);
    if(DynamicPoreWall && Simulate2D && !PeriActive){
      const double det=m.a11*m.a33-m.a13*m.a31;
      if(std::isfinite(det) && det<=0)return false; //-Do not commit before the existing one-source retry.
    }
    CorrMatc[p]=m;
    return true;
  };'''),
    ('dynamic_acceleration_writer_accepts',
     '''    Acec[p]=TFloat3(float(q.x*v[0]-Gravity.x),float(q.y*v[1]-Gravity.y),float(q.z*v[2]-Gravity.z));
  };''',
     '''    Acec[p]=TFloat3(float(q.x*v[0]-Gravity.x),float(q.y*v[1]-Gravity.y),float(q.z*v[2]-Gravity.z));
    return true;
  };'''),
)


GPU_EDITS = (
    ('stage1_finite_nonpositive_C_uses_original_single_nearest_retry',
     '''    const double determinant=m.a11*m.a33-m.a13*m.a31;
    if(!isfinite(determinant) || determinant<=0){atomicMin(invalid,p1);return;}
    corrmat[p1]=m;''',
     '''    const double determinant=m.a11*m.a33-m.a13*m.a31;
    if(isfinite(determinant) && determinant<=0 && CTE.simulate2d && !CTE.periactive && !retried){
      bool nearestfinite=isfinite(nearest2) && nearest2<DBL_MAX && isfinite(nearx) && isfinite(nearz);
      for(unsigned c=0;c<ncomp && nearestfinite;c++)nearestfinite=isfinite(nearest[c]);
      if(nearestfinite && (nearx!=0 || nearz!=0)){
        //-The same visited-source retry, still evaluated at the original mirror.
        gp.x-=nearx;gp.z-=nearz;fitshiftx-=nearx;fitshiftz-=nearz;
        retried=true;continue;
      }
    }
    if(!isfinite(determinant) || determinant<=0){atomicMin(invalid,p1);return;}
    corrmat[p1]=m;'''),
)


def transform_cpu(raw):
    """Return private CPU bytes and inverse proof; write no source or artifacts."""
    return _derive(raw, 'JSphCpu_mdbc.cpp', CPU_EDITS)


def transform_gpu(raw):
    """Return private GPU helper bytes and inverse proof; write no artifacts."""
    return _derive(raw, 'JSphGpu_mdbc_ker.cuh', GPU_EDITS)


def transform_source(filename, raw):
    """Closed two-filename entry point for a later independently admitted builder."""
    if filename == 'JSphCpu_mdbc.cpp':
        return transform_cpu(raw)
    if filename == 'JSphGpu_mdbc_ker.cuh':
        return transform_gpu(raw)
    raise RuntimeError('Private derivation permits only the two reviewed mDBC members')


if __name__ == '__main__':
    raise SystemExit('Author-only pure transformation: no standalone apply/build/run command is provided')
