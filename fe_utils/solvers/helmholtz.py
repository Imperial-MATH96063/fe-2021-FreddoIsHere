"""Solve a model helmholtz problem using the finite element method.
If run as a script, the result is plotted. This file can also be
imported as a module and convergence tests run on the solver.
"""
from fe_utils import *
import numpy as np
from numpy import cos, pi
import scipy.sparse as sp
import scipy.sparse.linalg as splinalg
from argparse import ArgumentParser
from itertools import product


def assemble(fs, f):
    """Assemble the finite element system for the Helmholtz problem given
    the function space in which to solve and the right hand side
    function."""

    # Create an appropriate (complete) quadrature rule.
    cg1 = LagrangeElement(fs.mesh.cell, fs.element.degree + 20) # 4 for helmholtz.py 1 2
    Q = gauss_quadrature(cg1.cell, cg1.degree)

    # Tabulate the basis functions and their gradients at the quadrature points.
    phi = fs.element.tabulate(Q.points)  # (points, nodes)
    phi_grad = fs.element.tabulate(Q.points, grad=True)  # (points, nodes, dim)
    # ∇_XΦ_j^(X_q) = phi_grad[X_q, j]

    # Create the left hand side matrix and right hand side vector.
    # This creates a sparse matrix because creating a dense one may
    # well run your machine out of memory!
    A = sp.lil_matrix((fs.node_count, fs.node_count))
    l = np.zeros(fs.node_count)

    # Now loop over all the cells and assemble A and l
    nodes = fs.cell_nodes
    for c in range(nodes.shape[0]):
        cell_nodes = fs.cell_nodes[c, :]
        J = fs.mesh.jacobian(c)
        detJ = np.abs(np.linalg.det(J))
        l[cell_nodes] += (phi.T*Q.weights) @ (f.values[cell_nodes] @ phi.T) * detJ

    for c in range(nodes.shape[0]):
        J = fs.mesh.jacobian(c)
        inv_J = np.linalg.inv(J)
        detJ = np.abs(np.linalg.det(J))
        # m is a ixj matrix for 1 2 it is 6x6
        J_phi_grad = np.einsum("dk, pnk->nk", inv_J, phi_grad*Q.weights.reshape(-1, 1, 1))
        J_phi_grad_T = np.einsum("dk, pnk->nk", inv_J, phi_grad).T
        sum = J_phi_grad @ J_phi_grad_T + Q.weights*phi.T @ phi
        A[np.ix_(nodes[c, :], nodes[c, :])] += sum*detJ
        """phi_ij = phi_i.reshape(-1, 1) @ phi_i.reshape(1, -1)
        phi_i_grad = np.tensordot(phi_grad, inv_J, axes=1)
        phi_product = phi_i_grad @ phi_i_grad.swapaxes(1, 2)
        A[np.ix_(nodes[c, :], nodes[c, :])] += \
            (np.sum(Q.weights.reshape((-1,) + (1,)*(phi_product.ndim - 1))*phi_product, axis=0) + phi_ij)*detJ
        """
        """
        for i, j in product(range(phi.shape[1]), range(phi.shape[1])):
            A[nodes[c, i], nodes[c, j]] += np.sum([
                ((inv_J.T @ phi_grad[q_idx, i]) @ (inv_J.T @ phi_grad[q_idx, j]) + phi[q_idx, i] * phi[q_idx, j])*detJ
                for q_idx, q in enumerate(Q.weights)
            ])
        """

    return A, l


def solve_helmholtz(degree, resolution, analytic=False, return_error=False):
    """Solve a model Helmholtz problem on a unit square mesh with
    ``resolution`` elements in each direction, using equispaced
    Lagrange elements of degree ``degree``."""

    # Set up the mesh, finite element and function space required.
    mesh = UnitSquareMesh(resolution, resolution)
    fe = LagrangeElement(mesh.cell, degree)
    fs = FunctionSpace(mesh, fe)

    # Create a function to hold the analytic solution for comparison purposes.
    analytic_answer = Function(fs)
    analytic_answer.interpolate(lambda x: cos(4*pi*x[0])*x[1]**2*(1.-x[1])**2)

    # If the analytic answer has been requested then bail out now.
    if analytic:
        return analytic_answer, 0.0

    # Create the right hand side function and populate it with the
    # correct values.
    f = Function(fs)
    f.interpolate(lambda x: ((16*pi**2 + 1)*(x[1] - 1)**2*x[1]**2 - 12*x[1]**2 + 12*x[1] - 2) *
                  cos(4*pi*x[0]))

    # Assemble the finite element system.
    A, l = assemble(fs, f)

    # Create the function to hold the solution.
    u = Function(fs)

    # Cast the matrix to a sparse format and use a sparse solver for
    # the linear system. This is vastly faster than the dense
    # alternative.
    A = sp.csr_matrix(A)
    u.values[:] = splinalg.spsolve(A, l)

    # Compute the L^2 error in the solution for testing purposes.
    error = errornorm(analytic_answer, u)

    if return_error:
        u.values -= analytic_answer.values

    # Return the solution and the error in the solution.
    return u, error

if __name__ == "__main__":

    parser = ArgumentParser(
        description="""Solve a Helmholtz problem on the unit square.""")
    parser.add_argument("--analytic", action="store_true",
                        help="Plot the analytic solution instead of solving the finite element problem.")
    parser.add_argument("--error", action="store_true",
                        help="Plot the error instead of the solution.")
    parser.add_argument("resolution", type=int, nargs=1,
                        help="The number of cells in each direction on the mesh.")
    parser.add_argument("degree", type=int, nargs=1,
                        help="The degree of the polynomial basis for the function space.")
    args = parser.parse_args()
    resolution = args.resolution[0]
    degree = args.degree[0]
    analytic = args.analytic
    plot_error = args.error

    u, error = solve_helmholtz(degree, resolution, analytic, plot_error)

    u.plot()
