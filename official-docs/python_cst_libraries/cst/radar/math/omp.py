# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

"""
Orthogonal Matching Pursuit Module
"""

import numpy as np
import scipy
import scipy.sparse
import scipy.sparse.linalg


def normalize_dict(D):
    """
    normalize the atoms in the dictionary D
    returns scaled dictionary and scaling factor

    Parameters:
    -----------
    D : np.array((n, m), dtype=np.complex128)
      Dictionary

    Returns:
    --------
    Scaled Dictionary : np.array((n, m), dtype=np.complex128)
    Scaling : np.array((n,), dtype=real)
    """
    inverse_scale = 1.0/np.linalg.norm(D, axis=0)
    return [D * inverse_scale, inverse_scale]


def solve(D, b, nn_max, eps, normalize_colum_vectors=True):
    """
    Orthogonal Matching Pursuit Algorithm
    Greedy approximation for solving: min_x |D x - b|^2 subject to ||x||_0 <= nn_max

    Parameters:
    -----------
    D: np.array((n, m), dtype=np.complex128)
        complex dictionary
    b: np.array((n,), dtype=np.complex128)
        complex samples
    nn_max max: int > 0
      number of non zero entries
    eps: real > 0
      stopping criterion

    Returns:
    --------
    xsol: np.array((n, m), dtype=np.complex128)
        sparse greedy approximate solution
    resids: np.array((j,), dtype=np.real)
        residuals |D x - b| for each iteration
    j: int
        number of iterations until convergence or when nn_max is reached
    """
    # calculate inverse column vector norm
    inverse_scale = 1.0/np.linalg.norm(D, axis=0)
    inverse_scale = np.reshape(inverse_scale, -1)
    # setup arrays
    M, K = D.shape
    xsol = np.zeros((K, ), dtype=np.complex128)
    x = b
    DH = np.conjugate(np.transpose(D))
    indx = set()
    resids = np.zeros(nn_max+1)
    residual = x
    # interation loop
    for j in range(0, nn_max):
        proj = DH @ residual  # project residual on atoms
        if normalize_colum_vectors:
            proj = np.multiply(proj, inverse_scale)
        pos = np.argmax(np.abs(proj))  # location of max magnitude
        if pos in indx:
            tmp = np.abs(proj)
            tmp[list(indx)] = 0
            pos = np.argmax(tmp)
        indx.add(pos)
        # best lsqr sol in subspace
        Drestricted = D[:, list(indx)]
        lsqr_res = scipy.sparse.linalg.lsqr(
            Drestricted, x)
        a = lsqr_res[0]
        # solving the lsqr problem via pseudo inverse
        # a = np.matmul(np.linalg.pinv(D[:, list(indx)], rcond=1e-7), x)
        residual = x - Drestricted @ a  # calc new residual
        resids[j+1] = np.linalg.norm(residual)
        if (resids[j+1] < eps or j == nn_max-1):
            xsol[list(indx)] = a
            break
    xsol = xsol
    return [xsol, resids, j+1]
