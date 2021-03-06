# ----------------------------------------------------------------------------
# Copyright (c) 2013--, scikit-bio development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

from __future__ import absolute_import, division, print_function

import sys
import numpy as np
from scipy.stats import pearsonr
import sys

from skbio.core.distance import DistanceMatrix

if sys.hexversion > 0x03000000:
    xrange = range


def hommola_cospeciation(host_dist, par_dist, interaction, permutations):
    """Performs a cospeciation test

    This test for host/parasite cospeciation is as described in [1]_. This test
    is a modification of a Mantel test, with a correction for the case where
    multiple hosts map to a single parasite (and vice versa).

    Parameters
    ----------
    host_dist : array_like or DistanceMatrix 
        Symmetric matrix of m x m pairwise distances between hosts
    par_dist : array_like or DistanceMatrix
        Symmetric matrix of n x n pairwise distances between parasites
    interaction : numpy.array
        n x m binary matrix of parasite x host interactions
    permutations : int
        Number of permutations to run

    Returns
    -------
    p_val : float
        Significance of host : parasite association
    r : float
        Correlation coefficient of host : parasite association
    perm_stats : list of floats
        List of r values observed using permuted host : parasite interactions

    Examples
    --------

    >>> import numpy as np
    >>> from skbio.math.stats.evolve.hommola import hommola_cospeciation

    Import arrays for host distances, parasite distances, and the interactions

    >>> hdist = np.array([[0,3,8,8,9],[3,0,7,7,8],[8,7,0,6,7],[8,7,6,0,3],
    ...                  [9,8,7,3,0]])
    >>> pdist = np.array([[0,5,8,8,8],[5,0,7,7,7],[8,7,0,4,4],[8,7,4,0,2],
    ...                  [8,7,4,2,0]])
    >>> interaction = np.array([[1,0,0,0,0],[0,1,0,0,0],[0,0,1,0,0],
    ...                        [0,0,0,1,0],[0,0,0,1,1]])

    Run the permutation test. Note that the correlation coefficient for the
    observed values counts against the final reported p value.

    >>> p_val, r_val, perm_stats = hommola_cospeciation(hdist, pdist,
    ...                                                 interaction, 99)
    >>> r_val
    0.83170965463247903

    In this case, the host distances explain about 80%% of the variation in
    symbiont distances. However, this may also reflect structure inherent in
    the phylogeny, and is not itself indicative of significance.

    >>> print(p_val <= 0.05)
    True

    After permuting host : parasite interactions, we find that the observed
    correlation is indeed greater than we would expect by chance.

    References
    ----------
    .. [1] Hommola K, Smith JE, Qiu Y, Gilks WR (2009) A Permutation Test of
       Host-Parasite Cospeciation. Molecular Biology and Evolution, 26,
       1457-1468.
    """

    # Generate lists of host and symbiont edges, such that the index
    # of the lists represents an edge connecting the host to the parasite.
    host_dist = DistanceMatrix(host_dist)
    par_dist = DistanceMatrix(par_dist)

    pars, hosts = np.nonzero(interaction)
    pars_k_labels, pars_t_labels = _gen_lists(pars)
    hosts_k_labels, hosts_t_labels = _gen_lists(hosts)

    # get a vector of pairwise distances for each interaction edge
    x = _get_dist(hosts_k_labels, hosts_t_labels, host_dist.data,
                  np.arange(interaction.shape[1]))
    y = _get_dist(pars_k_labels, pars_t_labels, par_dist.data,
                  np.arange(interaction.shape[0]))

    # calculate the observed correlation coefficient for this host/symbionts
    r = pearsonr(x, y)[0]

    # now do permutaitons. Initialize index lists of the appropriate size.
    mp = np.arange(par_dist.data.shape[1])
    mh = np.arange(host_dist.data.shape[1])
    below = 0

    perm_stats = []  # initialize list of shuffled correlation vals

    for i in xrange(permutations):
        # Generate a shuffled list of indexes for each permutation. This
        # effectively randomizes which host is associated with which symbiont,
        # but maintains the distribution of genetic distances.
        np.random.shuffle(mp)
        np.random.shuffle(mh)

        # Get pairwise distances in shuffled order
        y_p = _get_dist(pars_k_labels, pars_t_labels, par_dist.data, mp)
        x_p = _get_dist(hosts_k_labels, hosts_t_labels, host_dist.data, mh)

        # calculate shuffled correlation.
        # If greater than observed value, iterate counter below.
        r_p = pearsonr(x_p, y_p)[0]
        perm_stats.append(r_p)
        if r_p >= r:
            below += 1

    p_val = (below + 1) / (permutations + 1)

    return p_val, r, perm_stats


def _get_dist(k_labels, t_labels, dists, index):
    """Function for picking a subset of pairwise distances from a distance
    matrix according to a set of (randomizable) indices.
    Derived from Hommola et al R code

    Parameters
    ----------
    labels : list of strings
        names associated with pairwise distance matrix
    dists : numpy.array
        pairwise distance matrix
    index : list of ints
        permutable indices for changing order in pairwise distance matrix

    Returns
    -------
    vec : list of floats
        Returns list of distances associated with host:parasite edges, per
        description in Hommola et al. 2009.
    """

    vec = dists[index[k_labels], index[t_labels]]
    return vec


def _gen_lists(labels):
    i_array, j_array = np.transpose(np.tri(len(labels)-1)).nonzero()
    j_array = j_array + 1
    k_labels = labels[i_array]
    t_labels = labels[j_array]
    return k_labels, t_labels
