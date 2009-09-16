'''
Functions to operate on, or return, quaternions

Quaternions here consist of 4 values ``w, x, y, z``, where ``w`` is the
real (scalar) part, and ``x, y, z`` are the complex (vector) part. 

Note - rotation matrices here apply to column vectors, that is,
they are applied on the left of the vector.  For example:

>>> import numpy as np
>>> q = [0, 1, 0, 0] # 180 degree rotation around axis 0
>>> M = quat2mat(q) # from this module
>>> vec = np.array([1, 2, 3]).reshape((3,1)) # column vector
>>> tvec = np.dot(M, vec)
'''

import numpy as np

MAX_FLOAT = np.maximum_sctype(np.float)
FLOAT_EPS = np.finfo(np.float).eps


def fillpositive(xyz, w2_thresh=None):
    ''' Compute unit quaternion from last 3 values
    
    Parameters
    ----------
    xyz : iterable
       iterable containing 3 values, corresponding to quaternion x, y, z
    w2_thresh : None or float, optional
       threshold to determine if w squared is really negative.
       If None (default) then w2_thresh set equal to
       ``-np.finfo(xyz.dtype).eps``, if possible, otherwise
       ``-np.finfo(np.float).eps``

    Returns
    -------
    wxyz : array shape (4,)
         Full 4 values of quaternion

    Notes
    -----
    If w, x, y, z are the values in the full quaternion, assumes w is
    positive.

    Gives error if w*w is estimated to be negative

    w = 0 corresponds to a 180 degree rotation

    The unit quaternion specifies that np.dot(wxyz, wxyz) == 1.
    
    If w is positive (assumed here), w is given by:

    w = np.sqrt(1.0-(x*x+y*y+z*z))

    w2 = 1.0-(x*x+y*y+z*z) can be near zero, which will lead to
    numerical instability in sqrt.  Here we use the system maximum
    float type to reduce numerical instability

    Examples
    --------
    >>> import numpy as np
    >>> wxyz = fillpositive([0,0,0])
    >>> np.all(wxyz == [1, 0, 0, 0])
    True
    >>> wxyz = fillpositive([1,0,0]) # Corner case; w is 0
    >>> np.all(wxyz == [0, 1, 0, 0])
    True
    >>> np.dot(wxyz, wxyz)
    1.0
    '''
    # Check inputs (force error if < 3 values)
    if len(xyz) != 3:
        raise ValueError('xyz should have length 3')
    # If necessary, guess precision of input
    if w2_thresh is None:
        try: # trap errors for non-array, integer array
            w2_thresh = -np.finfo(xyz.dtype).eps
        except (AttributeError, ValueError):
            w2_thresh = -FLOAT_EPS
    # Use maximum precision
    xyz = np.asarray(xyz, dtype=MAX_FLOAT)
    # Calculate w
    w2 = 1.0 - np.dot(xyz, xyz)
    if w2 < 0:
        if w2 < w2_thresh:
            raise ValueError('w2 should be positive, but is %f' % w2)
        w = 0
    else:
        w = np.sqrt(w2)
    return np.r_[w, xyz]


def quat2mat(q):
    ''' Calculate rotation matrix corresponding to quaternion

    Parameters
    ----------
    q : 4 element array-like

    Returns
    -------
    M : (3,3) array
      Rotation matrix corresponding to input quaternion *q*

    Notes
    -----
    Rotation matrix applies to column vectors, and is applied to the
    left of coordinate vectors.  The algorithm here allows non-unit
    quaternions.

    References
    ----------
    Algorithm from 
    http://en.wikipedia.org/wiki/Rotation_matrix#Quaternion

    Examples
    --------
    >>> import numpy as np
    >>> M = quat2mat([1, 0, 0, 0]) # Identity quaternion
    >>> np.allclose(M, np.eye(3))
    True
    >>> M = quat2mat([0, 1, 0, 0]) # 180 degree rotn around axis 0
    >>> np.allclose(M, np.diag([1, -1, -1]))
    True
    '''
    qa = np.array(q)
    Nq = np.dot(qa, qa)
    if Nq > 0.0:
        s = 2/Nq
    else:
        s = 0.0
    w, x, y, z = q
    X = x*s
    Y = y*s
    Z = z*s
    wX = w*X; wY = w*Y; wZ = w*Z
    xX = x*X; xY = x*Y; xZ = x*Z
    yY = y*Y; yZ = y*Z; zZ = z*Z
    return np.array(
           [[ 1.0-(yY+zZ), xY-wZ, xZ+wY ],
            [ xY+wZ, 1.0-(xX+zZ), yZ-wX ],
            [ xZ-wY, yZ+wX, 1.0-(xX+yY) ]])


def mat2quat(M):
    ''' Calculate quaternion corresponding to given rotation matrix

    Parameters
    ----------
    M : array-like
      3x3 rotation matrix

    Returns
    -------
    q : (4,) array
      closest quaternion to input matrix, having positive q[0]

    Notes
    -----    
    Method claimed to be robust to numerical errors in M

    Constructs quaternion by calculating maximum eigenvector for matrix
    K (constructed from input `M`).  Although this is not tested, a
    maximum eigenvalue of 1 corresponds to a valid rotation.

    A quaternion q*-1 corresponds to the same rotation as q; thus the
    sign of the reconstructed quaternion is arbitrary, and we return
    quaternions with positive w (q[0]).
    
    References
    ----------
     * http://en.wikipedia.org/wiki/Rotation_matrix#Quaternion
     * Bar-Itzhack, Itzhack Y. (2000), "New method for extracting the
    quaternion from a rotation matrix", AIAA Journal of Guidance,
    Control and Dynamics 23(6):1085-1087 (Engineering Note), ISSN
    0731-5090

    Examples
    --------
    >>> import numpy as np
    >>> q = mat2quat(np.eye(3)) # Identity rotation
    >>> np.allclose(q, [1, 0, 0, 0])
    True
    >>> q = mat2quat(np.diag([1, -1, -1]))
    >>> np.allclose(q, [0, 1, 0, 0]) # 180 degree rotn around axis 0
    True

    '''
    # Qyx refers to the contribution of the y input vector component to
    # the x output vector component.  Qyx is therefore the same as
    # M[0,1].  The notation is from the article cited above.
    Qxx,Qyx,Qzx,Qxy,Qyy,Qzy,Qxz,Qyz,Qzz=M.flat
    # Fill only lower half of symmetric matrix
    K = np.array([
        [Qxx-Qyy-Qzz, 0, 0, 0],
        [Qyx+Qxy, Qyy-Qxx-Qzz, 0, 0],
        [Qzx+Qxz, Qzy+Qyz, Qzz-Qxx-Qyy, 0],
        [Qyz-Qzy, Qzx-Qxz, Qxy-Qyx, Qxx+Qyy+Qzz]]) / 3
    # Use Hermitian eigenvectors, values for speed
    vals, vecs = np.linalg.eigh(K)
    # Select largest eigenvector, reorder to w,x,y,z quaternion
    q = vecs[[3, 0, 1, 2],np.argmax(vals)]
    # Prefer quaternion with positive w
    # (q * -1 corresponds to same rotation as q)
    if q[0]<0:
        q *= -1
    return q


def mult(q1, q2):
    ''' Multiply two quaternions

    Parameters
    ----------
    q1 : 4 element sequence
    q2 : 4 element sequence

    Returns
    -------
    q12 : shape (4,) array

    Notes
    -----
    See : http://en.wikipedia.org/wiki/Quaternions#Hamilton_product
    '''
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    w = w1*w2 - x1*x2 - y1*y2 - z1*z2
    x = w1*x2 + x1*w2 + y1*z2 - z1*y2
    y = w1*y2 + y1*w2 + z1*x2 - x1*z2
    z = w1*z2 + z1*w2 + x1*y2 - y1*x2
    return np.array([w, x, y, z])


def conjugate(q):
    ''' Conjugate of quaternion 

    Parameters
    ----------
    q : 4 element sequence
       w, i, j, k of quaternion

    Returns
    -------
    conjq : array shape (4,)
       w, i, j, k of conjugate of `q`
    '''
    return np.array(q) * np.array([1.0,-1,-1,-1])


def norm(q):
    ''' Return norm of quaternion 

    Parameters
    ----------
    q : 4 element sequence
       w, i, j, k of quaternion

    Returns
    -------
    n : scalar
       quaternion norm
    '''    
    return np.dot(q,q)


def isunit(q):
    ''' Return True is this is very nearly a unit quaternion '''
    return np.allclose(norm(q),1)


def inverse(q):
    ''' Return multiplicative inverse of quaternion `q`

    Parameters
    ----------
    q : 4 element sequence
       w, i, j, k of quaternion

    Returns
    -------
    invq : array shape (4,)
       w, i, j, k of quaternion inverse
    '''
    return conjugate(q) / norm(q)


def eye():
    ''' Return identity quaternion '''
    return np.array([1.0,0,0,0])


def rotate_vector(v, q):
    ''' Apply transformation in quaternion `q` to vector `v`

    Parameters
    ----------
    v : 3 element sequence
       3 dimensional vector
    q : 4 element sequence
       w, i, j, k of quaternion

    Returns
    -------
    vdash : array shape (3,)
       `v` rotated by quaternion `q`

    Notes
    -----
    See: http://en.wikipedia.org/wiki/Quaternions_and_spatial_rotation#Describing_rotations_with_quaternions
    
    '''
    varr = np.zeros((4,))
    varr[1:] = v
    return mult(q, mult(varr, conjugate(q)))[1:]
