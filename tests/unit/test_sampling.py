# Copyright (C) 2015-2018 by the RBniCS authors
#
# This file is part of RBniCS.
#
# RBniCS is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RBniCS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with RBniCS. If not, see <http://www.gnu.org/licenses/>.
#

from math import log
from numpy import linspace, random
import scipy.stats as stats
import matplotlib.pyplot as plt
from rbnics.sampling import ParameterSpaceSubset
from rbnics.sampling.distributions import DrawFrom, EquispacedDistribution, LogUniformDistribution, UniformDistribution

# Common data
box = [(2., 5.), (10., 1000.)]
n = int(1.1e4)
bins = 50
min = 0
max = 1

# Auxiliary functions
def plot(p, box, set_, bins, generator=None, *args, **kwargs):
    sub_box_p = box[p]
    sub_set_p = [mu[p] for mu in set_]
    fig, ax = plt.subplots(1, 1)
    if generator is not None:
        distribution = generator(*args, **kwargs)
        x = linspace(sub_box_p[0], sub_box_p[1], bins**2)
        ax.plot(x, distribution.pdf(x), 'r-', lw=2)
    ax.hist(sub_set_p, bins=bins, normed=True, histtype='stepfilled', alpha=0.2)
    
class stats_equispaced(object):
    def __init__(self, *args, **kwargs):
        self.scale = kwargs["scale"]
    
    def pdf(self, x):
        return [1./self.scale]*len(x)
        
class stats_loguniform(object):
    def __init__(self, *args, **kwargs):
        loc = kwargs["loc"]
        scale = kwargs["scale"]
        log_min = log(loc)
        log_max = log(loc + scale)
        self.log_min = log_min
        self.log_max = log_max
    
    def pdf(self, x):
        return [1./(v*(self.log_max - self.log_min)) for v in x]

# Default generator
def test_sampling_default():
    parameter_space_subset = ParameterSpaceSubset()
    parameter_space_subset.generate(box, n)
    plot(0, box, parameter_space_subset, bins, stats.uniform, loc=box[0][min], scale=box[0][max]-box[0][min])
    plot(1, box, parameter_space_subset, bins, stats.uniform, loc=box[1][min], scale=box[1][max]-box[1][min])
    plt.show()

# Uniform generator
def test_sampling_uniform():
    parameter_space_subset = ParameterSpaceSubset()
    parameter_space_subset.generate(box, n, sampling=UniformDistribution())
    plot(0, box, parameter_space_subset, bins, stats.uniform, loc=box[0][min], scale=box[0][max]-box[0][min])
    plot(1, box, parameter_space_subset, bins, stats.uniform, loc=box[1][min], scale=box[1][max]-box[1][min])
    plt.show()

# Composite uniform generator
def test_sampling_composite_uniform():
    parameter_space_subset = ParameterSpaceSubset()
    parameter_space_subset.generate(box, n, sampling=(UniformDistribution(), UniformDistribution()))
    plot(0, box, parameter_space_subset, bins, stats.uniform, loc=box[0][min], scale=box[0][max]-box[0][min])
    plot(1, box, parameter_space_subset, bins, stats.uniform, loc=box[1][min], scale=box[1][max]-box[1][min])
    plt.show()

# Equispaced generator
def test_sampling_equispaced_generator():
    parameter_space_subset = ParameterSpaceSubset()
    parameter_space_subset.generate(box, n, sampling=EquispacedDistribution())
    plot(0, box, parameter_space_subset, bins, stats_equispaced, loc=box[0][min], scale=box[0][max]-box[0][min])
    plot(1, box, parameter_space_subset, bins, stats_equispaced, loc=box[1][min], scale=box[1][max]-box[1][min])
    plt.show()

# Composite equispaced generator
def test_sampling_composite_equispaced_generator():
    parameter_space_subset = ParameterSpaceSubset()
    parameter_space_subset.generate(box, n, sampling=(EquispacedDistribution(), EquispacedDistribution()))
    plot(0, box, parameter_space_subset, bins, stats_equispaced, loc=box[0][min], scale=box[0][max]-box[0][min])
    plot(1, box, parameter_space_subset, bins, stats_equispaced, loc=box[1][min], scale=box[1][max]-box[1][min])
    plt.show()

# Log uniform generator
def test_sampling_log_uniform_generator():
    parameter_space_subset = ParameterSpaceSubset()
    parameter_space_subset.generate(box, n, sampling=LogUniformDistribution())
    plot(0, box, parameter_space_subset, bins, stats_loguniform, loc=box[0][min], scale=box[0][max]-box[0][min])
    plot(1, box, parameter_space_subset, bins, stats_loguniform, loc=box[1][min], scale=box[1][max]-box[1][min])
    plt.show()

# Composite log uniform generator
def test_sampling_composite_log_uniform_generator():
    parameter_space_subset = ParameterSpaceSubset()
    parameter_space_subset.generate(box, n, sampling=(LogUniformDistribution(), LogUniformDistribution()))
    plot(0, box, parameter_space_subset, bins, stats_loguniform, loc=box[0][min], scale=box[0][max]-box[0][min])
    plot(1, box, parameter_space_subset, bins, stats_loguniform, loc=box[1][min], scale=box[1][max]-box[1][min])
    plt.show()

# Beta generator
def test_sampling_beta_generator():
    parameter_space_subset = ParameterSpaceSubset()
    parameter_space_subset.generate(box, n, sampling=DrawFrom(random.beta, a=2, b=5))
    plot(0, box, parameter_space_subset, bins, stats.beta, a=2, b=5, loc=box[0][min], scale=box[0][max]-box[0][min])
    plot(1, box, parameter_space_subset, bins, stats.beta, a=2, b=5, loc=box[1][min], scale=box[1][max]-box[1][min])
    plt.show()

# Composite beta generator
def test_sampling_composite_beta_generator():
    parameter_space_subset = ParameterSpaceSubset()
    parameter_space_subset.generate(box, n, sampling=(DrawFrom(random.beta, a=2, b=5), DrawFrom(random.beta, a=5, b=1)))
    plot(0, box, parameter_space_subset, bins, stats.beta, a=2, b=5, loc=box[0][min], scale=box[0][max]-box[0][min])
    plot(1, box, parameter_space_subset, bins, stats.beta, a=5, b=1, loc=box[1][min], scale=box[1][max]-box[1][min])
    plt.show()

# Composite equispaced and uniform generator
def test_sampling_composite_equispaced_and_uniform():
    parameter_space_subset = ParameterSpaceSubset()
    parameter_space_subset.generate(box, n, sampling=(EquispacedDistribution(), UniformDistribution()))
    plot(0, box, parameter_space_subset, bins, stats_equispaced, loc=box[0][min], scale=box[0][max]-box[0][min])
    plot(1, box, parameter_space_subset, bins, stats.uniform, loc=box[1][min], scale=box[1][max]-box[1][min])
    plt.show()

# Composite uniform and equispaced generator
def test_sampling_composite_uniform_and_equispaced():
    parameter_space_subset = ParameterSpaceSubset()
    parameter_space_subset.generate(box, n, sampling=(UniformDistribution(), EquispacedDistribution()))
    plot(0, box, parameter_space_subset, bins, stats.uniform, loc=box[0][min], scale=box[0][max]-box[0][min])
    plot(1, box, parameter_space_subset, bins, stats_equispaced, loc=box[1][min], scale=box[1][max]-box[1][min])
    plt.show()

# Composite equispaced and log uniform generator
def test_sampling_composite_equispaced_and_log_uniform():
    parameter_space_subset = ParameterSpaceSubset()
    parameter_space_subset.generate(box, n, sampling=(EquispacedDistribution(), LogUniformDistribution()))
    plot(0, box, parameter_space_subset, bins, stats_equispaced, loc=box[0][min], scale=box[0][max]-box[0][min])
    plot(1, box, parameter_space_subset, bins, stats_loguniform, loc=box[1][min], scale=box[1][max]-box[1][min])
    plt.show()

# Composite equispaced and beta generator
def test_sampling_composite_equispaced_and_beta():
    parameter_space_subset = ParameterSpaceSubset()
    parameter_space_subset.generate(box, n, sampling=(EquispacedDistribution(), DrawFrom(random.beta, a=2, b=5)))
    plot(0, box, parameter_space_subset, bins, stats_equispaced, loc=box[0][min], scale=box[0][max]-box[0][min])
    plot(1, box, parameter_space_subset, bins, stats.beta, a=2, b=5, loc=box[1][min], scale=box[1][max]-box[1][min])
    plt.show()

# Composite loguniform and beta generator
def test_sampling_composite_log_uniform_and_beta():
    parameter_space_subset = ParameterSpaceSubset()
    parameter_space_subset.generate(box, n, sampling=(LogUniformDistribution(), DrawFrom(random.beta, a=2, b=5)))
    plot(0, box, parameter_space_subset, bins, stats_loguniform, loc=box[0][min], scale=box[0][max]-box[0][min])
    plot(1, box, parameter_space_subset, bins, stats.beta, a=2, b=5, loc=box[1][min], scale=box[1][max]-box[1][min])
    plt.show()
