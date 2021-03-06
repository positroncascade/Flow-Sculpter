"""2D flow around a square cylinder in a channel.

Lift and drag coefficients of the cylinder are measured using the
momentum exchange method.

Fully developed parabolic profile is prescribed at the inflow and
a constant pressure condition is prescribed at the outflow.

The results can be compared with:
    [1] M. Breuer, J. Bernsdorf, T. Zeiser, F. Durst
    Accurate computations of the laminar flow past a square cylinder
    based on two different methods: lattice-Boltzmann and finite-volume
    Int. J. of Heat and Fluid Flow 21 (2000) 186-196.
"""


from __future__ import print_function

import sys
sys.path.append('../sailfish/')


import numpy as np
from sailfish.subdomain import Subdomain2D
from sailfish.node_type import NTHalfBBWall, NTEquilibriumVelocity, NTEquilibriumDensity, DynamicValue, NTFullBBWall
from sailfish.controller import LBSimulationController
from sailfish.lb_base import ForceObject
from sailfish.lb_single import LBFluidSim
from sailfish.sym import S

# Geometry set to match [1].
H = 256
L = 512
D = int(0.1 * L)

# St = f D / u_max

class BoxSubdomain(Subdomain2D):
    bc = NTHalfBBWall
    max_v = 0.04

    def boundary_conditions(self, hx, hy):
        #walls = (hy == 0) | (hy == self.gy - 1)
        walls = (hy == -2)
        self.set_node(walls, self.bc)

        #hhy = S.gy - self.bc.location
        self.set_node((hx == 0) &  np.logical_not(walls),
                      NTEquilibriumVelocity(
                          (self.max_v, 0.0)))
        self.set_node((hx == self.gx - 1) & np.logical_not(walls),
                      NTEquilibriumDensity(1))
        l = L / 4

        # Full bounce-back. For N box nodes, effective size is N+1.
        if self.bc.location == 0.5:
            eff_D = D - 1
        # Half-way bounce-back. For N box nodes, effective size is N-2.
        else:
            eff_D = D + 2

        box = ((hx > l - eff_D / 2.0) & (hx <= l + eff_D / 2.0) &
               (hy > (H - eff_D) / 2.0) & (hy <= (H + eff_D) / 2.0))
        self.set_node(box, self.bc)

    def initial_conditions(self, sim, hx, hy):
        sim.rho[:] = 1.0
        sim.vy[:] = 0.0

        hhy = hy - self.bc.location
        sim.vx[:] = self.max_v


class BoxSimulation(LBFluidSim):
    subdomain = BoxSubdomain

    @classmethod
    def update_defaults(cls, defaults):
        defaults.update({
            'lat_nx': L,
            'lat_ny': (H + 2 if BoxSubdomain.bc.location == 0.5 else H),
            'precision': 'half',
            #'periodic_y': True, 
            #'periodic_x': True, 
            'max_iters': 1000000,
            'visc': 0.007})
    """
    def __init__(self, *args, **kwargs):
        super(BoxSimulation, self).__init__(*args, **kwargs)

        margin = 5
        self.add_force_oject(ForceObject(
            (L / 4 - D / 2 - margin, (H - D) / 2 - margin),
            (L / 4 + D / 2 + margin, (H + D) / 2 + margin)))

        print('%d x %d | box: %d' % (L, H, D))
        print('Re = %2.f' % (BoxSubdomain.max_v * D / self.config.visc))
    """



if __name__ == '__main__':
    ctrl = LBSimulationController(BoxSimulation)
    ctrl.run()
