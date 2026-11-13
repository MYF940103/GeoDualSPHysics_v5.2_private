"""Same reviewed CPU object builder; fresh entry fixes only the invalid fixture cell encoding."""
import c08_fs_matrix_cpu_r1_build as original
original.TAG='c08_fs_matrix_cpu_r2'
original.OUT=original.T/'outputs/c08_fs_matrix_cpu_r2_build'
original.FIXTURE=original.T/'support/c08_fs_matrix_cpu_r2.cpp'
original.NOTE=original.T/'notes/c08_fs_matrix_cpu_r2.md'
if __name__=='__main__':original.main()
