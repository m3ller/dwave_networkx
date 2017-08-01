from __future__ import division

import sys
import re

import networkx as nx
from networkx import draw, diameter
from networkx.algorithms.bipartite import color


# compatibility for python 2/3
if sys.version_info[0] == 2:
    range = xrange
    itervalues = lambda d: d.itervalues()
    iteritems = lambda d: d.iteritems()
else:
    itervalues = lambda d: d.values()
    iteritems = lambda d: d.items()

__all__ = ['chimera_layout', 'draw_chimera']


def chimera_layout(G, scale=1, center=None, dim=2):
    """

    """

    if not isinstance(G, nx.Graph):
        empty_graph = nx.Graph()
        empty_graph.add_nodes_from(G)
        G = empty_graph

    # best case scenario, each node in G has a chimera_index attribute. Otherwise
    # we will try to determine it
    if all('chimera_index' in dat for __, dat in G.nodes_iter(data=True)):
        chimera_indices = {v: dat['chimera_index'] for v, dat in G.nodes_iter(data=True)}
        m = max(idx[0] for idx in itervalues(chimera_indices)) + 1
        n = max(idx[1] for idx in itervalues(chimera_indices)) + 1
        t = max(idx[3] for idx in itervalues(chimera_indices)) + 1
    else:
        raise NotImplementedError
        # m = re.match("chimera_graph\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", G.name)
        # if m:
        #     M, N, T = m.group(1), m.group(2), m.group(3)

    # ok, given the chimera indices, let's determine the coordinates
    xy_coords = chimera_node_placer_2d(m, n, t, scale, center, dim)
    pos = {v: xy_coords(i, j, u, k) for v, (i, j, u, k) in iteritems(chimera_indices)}

    return pos


def chimera_node_placer_2d(m, n, t, scale=1., center=None, dim=2):
    """Generates a function that converts chimera-indices to x, y
    coordinates for a plot.

    Parameters
    ----------
    m : int
        The number of rows in the Chimera lattice.
    n : int
        The number of columns in the Chimera lattice.
    t : int
        The size of the shore within each Chimera tile.
    scale : float (default 1.)
        Scale factor. When scale = 1 the all positions will fit within [0, 1]
        on the x-axis and [-1, 0] on the y-axis.
    center : None or array (default None)
        Coordinates of the top left corner.
    dim : int (default 2)
        Number of dimensions. When dim > 2, all extra dimensions are
        set to 0.
    paddims : int (optional, default 0)
        The number of additional dimensions.

    Returns
    -------
    xy_coords : function
        A function that maps a Chimera-index (i, j, u, k) in an
        (m, n, t) Chimera lattice to x,y coordinates as could be
        used by a plot.

    """
    import numpy as np

    tile_center = t // 2
    tile_length = t + 3  # 1 for middle of cross, 2 for spacing between tiles
    scale /= max(m, n) * tile_length - 3  # want the enter plot to fill in [0, 1] when scale=1

    grid_offsets = {}

    if center is None:
        center = np.zeros(dim)
    else:
        center = np.asarray(center)

    paddims = dim - 2
    if paddims < 0:
        raise ValueError("layout must have at least two dimensions")

    if len(center) != dim:
        raise ValueError("length of center coordinates must match dimension of layout")

    def _xy_coords(i, j, u, k):
        # row, col, shore, shore index

        # first get the coordinatiates within the tile
        if k < tile_center:
            p = k
        else:
            p = k + 1

        if u:
            xy = np.array([tile_center, -1 * p])
        else:
            xy = np.array([p, -1 * tile_center])

        # next offset the corrdinates based on the which tile
        if i > 0 or j > 0:
            if (i, j) in grid_offsets:
                xy += grid_offsets[(i, j)]
            else:
                off = np.array([j * tile_length, -1 * i * tile_length])
                xy += off
                grid_offsets[(i, j)] = off

        # convention for Chimera-lattice pictures is to invert the y-axis
        return np.hstack((xy * scale, np.zeros(paddims))) + center

    return _xy_coords


def _find_chimera_indices(G):
    """Tries to determine the chimera dimensions of G, not intended to
    be particularily fast. Makes a good faith effort, but it may fail.

    Fun facts:
        diameter(G) == M + N
        max_degree(G) == shore size <==> M == 1 and N == 1
    """

    # if the nodes are orderable, we want the lowest order one.
    try:
        nlist = sorted(G.nodes_iter())
    except TypeError:
        nlist = G.nodes()

    # need to check that the graph is bipartite. color gets a 2-color of the graph and raises
    # an exception if G is not bipartite
    coloring = color(G)

    # we want the lowest order node to have color 1
    # generally, we would actually like it to have color 0, but by default color seems to
    # choose 1 for the lowest labelled node, so for performance we'll go with 1
    if coloring[nlist[0]] != 1:
        coloring = {v: 1 - coloring[v] for v in coloring}

    # we also need the max degree, which will tell us about the shores of the bipartite
    delta = max(G.degree(v) for v in G)

    # let's determine the size of the shores
    shores = [0, 0]
    for v in coloring:
        shores[coloring[v]] += 1
    shore_size = max(shores)

    # if the max degree is the same size as the largest shore, then we are dealing with a single
    # tile
    if shore_size == delta:
        chimera_indices = {}
        shore_indices = [0, 0]

        for v in nlist:
            u = 1 - coloring[v]  # 1-colored
            chimera_indices[v] = (0, 0, u, shore_indices[u])
            shore_indices[u] += 1

        return chimera_indices

    # ok, so we have more than one tile, we need to figure out the dimensions of the lattice

    dia = diameter(G)
    raise NotImplementedError


def draw_chimera(G, linear_biases={}, quadratic_biases={},
                 nodelist=None, edgelist=None, cmap=None, edge_cmap=None, vmin=None, vmax=None,
                 edge_vmin=None, edge_vmax=None,
                 **kwargs):
    """TODO
    """

    if linear_biases or quadratic_biases:
        try:
            import matplotlib.pyplot as plt
            import matplotlib as mpl
        except ImportError:
            raise ImportError("Matplotlib and numpy required for draw_chimera()")

        if nodelist is None:
            nodelist = G.nodes()

        if edgelist is None:
            edgelist = G.edges()

        if cmap is None:
            cmap = plt.get_cmap('coolwarm')

        if edge_cmap is None:
            edge_cmap = plt.get_cmap('coolwarm')

        if 'node_color' in kwargs or 'edge_color' in kwargs:
            raise ValueError(('if linear_biases and/or quadratic_biases are provided,',
                              'cannot also provide node_color or edge_color'))

        def edge_color(u, v):
            c = 0.
            if (u, v) in quadratic_biases:
                c += quadratic_biases[(u, v)]
            if (v, u) in quadratic_biases:
                c += quadratic_biases[(v, u)]
            return c

        def node_color(v):
            c = 0.
            if v in linear_biases:
                c += linear_biases[v]
            if (v, v) in quadratic_biases:
                c += quadratic_biases[(v, v)]
            return c

        node_color = [node_color(v) for v in nodelist]
        edge_color = [edge_color(u, v) for u, v in edgelist]

        kwargs['edge_color'] = edge_color
        kwargs['node_color'] = node_color

        vmag = max(max(abs(c) for c in node_color), max(abs(c) for c in edge_color))
        if vmin is None:
            vmin = -1 * vmag
        if vmax is None:
            vmax = vmag
        if edge_vmin is None:
            edge_vmin = -1 * vmag
        if edge_vmax is None:
            edge_vmax = vmag

    draw(G, chimera_layout(G), nodelist=nodelist, edgelist=edgelist,
         cmap=cmap, edge_cmap=edge_cmap, vmin=vmin, vmax=vmax, edge_vmin=edge_vmin,
         edge_vmax=edge_vmax,
         **kwargs)

    if linear_biases or quadratic_biases:
        fig = plt.figure(1)
        # cax = fig.add_axes([])
        cax = fig.add_axes([.9, 0.2, 0.04, 0.6])  # left, bottom, width, height
        mpl.colorbar.ColorbarBase(cax, cmap=cmap,
                                  norm=mpl.colors.Normalize(vmin=-1 * vmag, vmax=vmag, clip=False),
                                  orientation='vertical')