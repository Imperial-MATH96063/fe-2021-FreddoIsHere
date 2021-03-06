# Cause division to always mean floating point division.
from __future__ import division
import numpy as np
from itertools import product
from .reference_elements import ReferenceInterval, ReferenceTriangle

np.seterr(invalid='ignore', divide='ignore')


def lagrange_points(cell, degree):
    """Construct the locations of the equispaced Lagrange nodes on cell.

    :param cell: the :class:`~.reference_elements.ReferenceCell`
    :param degree: the degree of polynomials for which to construct nodes.

    :returns: a rank 2 :class:`~numpy.array` whose rows are the
        coordinates of the nodes.

    The implementation of this function is left as an :ref:`exercise
    <ex-lagrange-points>`.

    """
    equi_lag_points = []
    for i in product(range(degree + 1), repeat=cell.dim):  # if cell.dim=2, is all (i, j) combinations
        if sum(i) <= degree:  # if cell.dim=1, trivially true
            equi_lag_points.append(np.array(i[::-1]) / degree)
    return np.array(equi_lag_points)


def vandermonde_matrix(cell, degree, points, grad=False):
    """Construct the generalised Vandermonde matrix for polynomials of the
    specified degree on the cell provided.

    :param cell: the :class:`~.reference_elements.ReferenceCell`
    :param degree: the degree of polynomials for which to construct the matrix.
    :param points: a list of coordinate tuples corresponding to the points.
    :param grad: whether to evaluate the Vandermonde matrix or its gradient.

    :returns: the generalised :ref:`Vandermonde matrix <sec-vandermonde>`

    The implementation of this function is left as an :ref:`exercise
    <ex-vandermonde>`.
    """

    def column(i, idx, j):  # computes single column of vandermonde matrix
        exp_1 = max([(i - j) - grad * (1 - idx), 0])  # (i-j) for grad=False
        exp_2 = max([j - grad * idx, 0])  # j for grad=False
        return np.multiply(points[:, None, 0] ** exp_1, points[:, None, -1] ** exp_2)

    matrix = []
    if grad:  # i loops over the degrees, j loops over the columns containing the polynomials of degree at most i
        for i in range(degree + 1):
            matrix += [np.hstack([((i - j) * (1 - k) + j * k) * column(i, k, j) for k in range(cell.dim)])
                       for j in range((cell.dim - 1) * i + 1)]  # k loops over the dimensions of a point
        return np.swapaxes(matrix, 0, 1)
    for i in range(degree + 1):
        matrix += [column(i, 0, j) for j in range((cell.dim - 1) * i + 1)]
    return np.hstack(matrix)


class FiniteElement(object):
    def __init__(self, cell, degree, nodes, entity_nodes=None):
        """A finite element defined over cell.

        :param cell: the :class:`~.reference_elements.ReferenceCell`
            over which the element is defined.
        :param degree: the
            polynomial degree of the element. We assume the element
            spans the complete polynomial space.
        :param nodes: a list of coordinate tuples corresponding to
            the nodes of the element.
        :param entity_nodes: a dictionary of dictionaries such that
            entity_nodes[d][i] is the list of nodes associated with entity `(d, i)`.

        Most of the implementation of this class is left as exercises.
        """

        #: The :class:`~.reference_elements.ReferenceCell`
        #: over which the element is defined.
        self.cell = cell
        #: The polynomial degree of the element. We assume the element
        #: spans the complete polynomial space.
        self.degree = degree
        #: The list of coordinate tuples corresponding to the nodes of
        #: the element.
        self.nodes = nodes
        #: A dictionary of dictionaries such that ``entity_nodes[d][i]``
        #: is the list of nodes associated with entity `(d, i)`.
        self.entity_nodes = entity_nodes

        if entity_nodes:
            #: ``nodes_per_entity[d]`` is the number of entities
            #: associated with an entity of dimension d.
            self.nodes_per_entity = np.array([len(entity_nodes[d][0])
                                              for d in range(cell.dim + 1)])

        # Replace this exception with some code which sets
        # self.basis_coefs
        # to an array of polynomial coefficients defining the basis functions.
        V = vandermonde_matrix(cell, degree, nodes)
        self.basis_coefs = np.linalg.inv(V)
        #: The number of nodes in this element.
        self.node_count = nodes.shape[0]

    def tabulate(self, points, grad=False):
        """Evaluate the basis functions of this finite element at the points
        provided.

        :param points: a list of coordinate tuples at which to
            tabulate the basis.
        :param grad: whether to return the tabulation of the basis or the
            tabulation of the gradient of the basis.

        :result: an array containing the value of each basis function
            at each point. If `grad` is `True`, the gradient vector of
            each basis vector at each point is returned as a rank 3
            array. The shape of the array is (points, nodes) if
            ``grad`` is ``False`` and (points, nodes, dim) if ``grad``
            is ``True``.

        The implementation of this method is left as an :ref:`exercise
        <ex-tabulate>`.

        """
        if grad:
            T = vandermonde_matrix(self.cell, self.degree, points, grad)
            return np.einsum("ijk,jl->ilk", T, self.basis_coefs)
        V = vandermonde_matrix(self.cell, self.degree, points)
        return V @ self.basis_coefs

    def interpolate(self, fn):
        """Interpolate fn onto this finite element by evaluating it
        at each of the nodes.

        :param fn: A function ``fn(X)`` which takes a coordinate
           vector and returns a scalar value.

        :returns: A vector containing the value of ``fn`` at each node
           of this element.

        The implementation of this method is left as an :ref:`exercise
        <ex-interpolate>`.

        """

        return np.array([fn(node) for node in self.nodes])

    def __repr__(self):
        return "%s(%s, %s)" % (self.__class__.__name__,
                               self.cell,
                               self.degree)


class LagrangeElement(FiniteElement):
    def __init__(self, cell, degree):
        """An equispaced Lagrange finite element.

        :param cell: the :class:`~.reference_elements.ReferenceCell`
            over which the element is defined.
        :param degree: the
            polynomial degree of the element. We assume the element
            spans the complete polynomial space.

        The implementation of this class is left as an :ref:`exercise
        <ex-lagrange-element>`.
        """

        nodes = lagrange_points(cell, degree)
        entity_nodes = {
            d: {i: [] for i in range(cell.entity_counts[d])} for d in range(cell.dim + 1)
        }

        def add_entity_node(n_idx, n):
            for d in range(cell.dim + 1):
                for i in range(cell.entity_counts[d]):
                    if cell.point_in_entity(n, (d, i)):
                        entity_nodes[d][i].append(n_idx)
                        return

        for n_idx, n in enumerate(nodes):
            add_entity_node(n_idx, n)
        # Use lagrange_points to obtain the set of nodes.  Once you
        # have obtained nodes, the following line will call the
        # __init__ method on the FiniteElement class to set up the
        # basis coefficients.
        super(LagrangeElement, self).__init__(cell, degree, nodes, entity_nodes)


class VectorFiniteElement:
    def __init__(self, fe):
        self.finite_element = fe
        self.nodes = np.vstack([np.tile(n, (fe.cell.dim, 1)) for n in fe.nodes])
        self.entity_nodes = {
            d: {i: [] for i in range(fe.cell.entity_counts[d])} for d in range(fe.cell.dim + 1)
        }

        def add_entity_node(n_idx, n):
            for d in range(fe.cell.dim + 1):
                for i in range(fe.cell.entity_counts[d]):
                    if fe.cell.point_in_entity(n, (d, i)):
                        self.entity_nodes[d][i] += [2 * n_idx, 2 * n_idx + 1]
                        return

        for n_idx, n in enumerate(fe.nodes):
            add_entity_node(n_idx, n)

        self.nodes_per_entity = np.array([len(self.entity_nodes[d][0])
                                          for d in range(fe.cell.dim + 1)])

        self.node_weights = np.array([[(i+1) % 2, i % 2] for i in range(self.nodes.shape[0])])
        self.node_count = self.nodes.shape[0]

    @property
    def cell(self):
        return self.finite_element.cell

    @property
    def degree(self):
        return self.finite_element.degree

    def tabulate(self, points, grad=False):
        einsum_string = "ik, j-> ikj" if grad else "i, j-> ij"
        phi = self.finite_element.tabulate(points, grad)
        raw_shape = list(phi.shape)
        raw_shape[1] *= self.cell.dim
        vphi = np.zeros(raw_shape + [2])

        for i in range(vphi.shape[1]):
            e = np.array([(i+1) % 2, i % 2])
            vphi[:, i] = np.einsum(einsum_string, phi[:, i//2], e)

        return vphi

