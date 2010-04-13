''' Attempts to unpack the SPM orientation machinery

These are symbolic versions of the code in ``spm_dicom_convert``,
``write_volume`` subfunction, around line 509 in the version I have
(SPM8, late 2009 vintage). 

'''

import numpy as np

import sympy
from sympy import Matrix, Symbol, symbols, zeros, ones, eye

def numbered_matrix(nrows, ncols, symbol_prefix):
    return Matrix(nrows, ncols, lambda i, j: Symbol(
            symbol_prefix + '_{%d%d}' % (i+1, j+1)))

def numbered_vector(nrows, symbol_prefix):
    return Matrix(nrows, 1, lambda i, j: Symbol(
            symbol_prefix + '_{%d}' % (i+1)))


orient_pat = numbered_matrix(3, 2, 'DOP')
orient_cross = numbered_vector(3, 'CP')
pos_pat_0 = numbered_vector(3, 'IPP^0')
pos_pat_N = numbered_vector(3, 'IPP^N')
pixel_spacing = symbols(('XS', 'YS'))
NZ = Symbol('NZ')
slice_thickness = Symbol('ZS')

R3 = orient_pat * np.diag(pixel_spacing)
R = zeros((4,2))
R[:3,:] = R3

# The following is specific to the SPM algorithm. 
x1 = ones((4,1))
y1 = ones((4,1))
y1[:3,:] = pos_pat_0

to_inv = zeros((4,4))
to_inv[:,0] = x1
to_inv[:,1] = symbols('ABCD')
to_inv[0,2] = 1
to_inv[1,3] = 1
inv_lhs = zeros((4,4))
inv_lhs[:,0] = y1
inv_lhs[:,1] = symbols('EFGH')
inv_lhs[:,2:] = R

def full_matrix(x2, y2):
    rhs = to_inv[:,:]
    rhs[:,1] = x2
    lhs = inv_lhs[:,:]
    lhs[:,1] = y2
    return lhs * rhs.inv()

# single slice case
orient = zeros((3,3))
orient[:3,:2] = orient_pat
orient[:,2] = orient_cross
x2_ss = Matrix((0,0,1,0))
y2_ss = zeros((4,1))
y2_ss[:3,:] = orient * Matrix((0,0,slice_thickness))
A_ss = full_matrix(x2_ss, y2_ss)

# many slice case
x2_ms = Matrix((1,1,NZ,1))
y2_ms = ones((4,1))
y2_ms[:3,:] = pos_pat_N
A_ms = full_matrix(x2_ms, y2_ms)

# End of SPM algorithm

# Here's what I was expecting from first principles of the DICOM
# transform

# single slice case
single_aff = eye(4)
rot = orient
rot_scale = rot * np.diag(pixel_spacing[:] + [slice_thickness])
single_aff[:3,:3] = rot_scale
single_aff[:3,3] = pos_pat_0

# For multi-slice case, we have the start and the end slice position
# patient.  This should give us the third column of the affine, because,
# ``pat_pos_N = aff * [[0,0,ZN-1,1]].T
multi_aff = eye(4)
multi_aff[:3,:2] = R3
missing_r_col = numbered_vector(3, 'AZ')
trans_z_N = Matrix((0,0, NZ-1, 1))
multi_aff[:3, 2] = missing_r_col
multi_aff[:3, 3] = pos_pat_0
est_pos_pat_N = multi_aff * trans_z_N
eqns = tuple(est_pos_pat_N[:3,0] - pos_pat_N)
solved =  sympy.solve(eqns, tuple(missing_r_col))
multi_aff_solved = multi_aff[:,:]
multi_aff_solved[:3,2] = solved.values()

# Check that I got what I was expecting, from SPM
one_based = eye(4)
one_based[:3,3] = (1,1,1)
A_ms_0based = A_ms * one_based
A_ms_0based.simplify()
A_ss_0based = A_ss * one_based
A_ss_0based.simplify()
assert single_aff == A_ss_0based
assert multi_aff_solved == A_ms_0based

print 'Single slice case'
print single_aff

print 'Multi slice case'
print multi_aff_solved

# Now, trying to work out Z from slice affines
A_i = single_aff
nz_trans = eye(4)
NZT = Symbol('N_z')
nz_trans[2,3] = NZT
A_j = A_i * nz_trans
IPP_i = A_i[:3,3]
IPP_j = A_j[:3,3]

spm_z = IPP_j.T * orient_cross
spm_z.simplify()

div_sum = 0
for i in range(3):
    div_sum += IPP_j[i] / orient_cross[i]
div_sum = sympy.simplify(div_sum / 3)


def my_latex(expr):
    S = sympy.latex(expr)
    return S[1:-1]

print 'Latex stuff'
print '   R = ' + my_latex(to_inv)
print '   '
print '   L = ' + my_latex(inv_lhs)
print
print '   0B = ' + my_latex(one_based)
print
print '   A_{multi} = ' + my_latex(multi_aff_solved)
print '   '
print '   A_{single} = ' + my_latex(single_aff)
print
print r'   \left(\begin{smallmatrix}IPP^N\\1\end{smallmatrix}\right) = A ' + my_latex(trans_z_N)
print
print '   ' + my_latex(solved)
print
print '   A_j = A_{single} ' + my_latex(nz_trans)
print
print '   IPP_j = ' + my_latex(IPP_j)
print
print '   IPP_j^T CP = ' + my_latex(spm_z)
print
print '   ' + my_latex(div_sum)
