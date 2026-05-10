# Sensitive Clay Softening Development Run Log

Date: 2026-05-11

## Starting Commit

`20a67ed` - `Add final CPU strict smoke completion report`

## Working Tree Notes

`git status --short` shows no tracked source modifications at the start of this
run. The working tree still contains long-standing untracked reference/input
files, including example input CSVs, the main u-pw PDF, `src/docs/`,
`src/source_DualSPHysics+/`, and untracked reference source files under
`src/source/`. These are not modified by this run.

## Goal

Implement a CPU-only sensitive-clay softening module suitable for reduced
retrogressive landslide and Sainte-Monique smoke tests.

The primary target case is:

`examples/u-pw/05_Retrogressive_Slope`

## Hard Scope

- No GPU coding.
- No `JSphGpu*`, `JCellDivGpu*`, `.cu`, CUDA kernels, GPU builds, or GPU runs.
- No long production runs or parameter sweeps.
- CPU source changes are allowed only for the softening material model and
  closely related XML soil-parameter parsing/output diagnostics.

## Planned Phases

1. Literature and existing-code audit.
2. Implementation design.
3. CPU source implementation.
4. Micro validation.
5. Reduced retrogressive slope softening smoke.
6. Documentation and final report.
