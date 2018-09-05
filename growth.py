# encoding: utf-8
'''
This application does an NVE+Langevin LAMMPS simulation of spherocylinder-like rods
(defined in a .cfg file) using the "lammps_multistate_rods" library, with some rods
preassembled in a fibril (using "tools/prepare_fibril.py).
The initial locations of the rods are at SC lattice points defined by the input params,
excluding the fibril region, and their orientations are randomly determined at each
insertion point.

Created on 16 Mar 2018

@author: Eugen Rožić
'''

import argparse

parser = argparse.ArgumentParser(description=
                                 'Program for NVE+Langevin hybrid LAMMPS simulation of\
spherocylinder-like rods, with a preassembled fibril.',
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('config_file',
                    help='path to the "lammps_multistate_rods" model config file')
parser.add_argument('output_folder',
                    help='name for the folder that will be created for output files')
parser.add_argument('cell_size', type=float,
                    help='size of an SC cell (i.e. room for one rod)')
parser.add_argument('num_cells', type=float,
                    help='the number of cells per dimension')
parser.add_argument('phi', type=float,
                    help='fibril azimuth angle (from y-axis); in degrees [0-360>')
parser.add_argument('theta', type=float,
                    help='fibril elevation angle (from x-y plane); in degrees [-90,90]')
parser.add_argument('sim_length', type=int,
                    help='the total number of MD steps to simulate')

parser.add_argument('--seed', type=int,
                    help='the seed for random number generators')

parser.add_argument('--r0', nargs=3, type=float, default=[0.,0.,0.],
                    help='the location of the center of the fibril')
parser.add_argument('--N', type=int, default=20,
                    help='number of monomers in the fibril')

parser.add_argument('-T', '--temp', default=4.0, type=float,
                    help='the temperature of the system (e.g. for Langevin)')
parser.add_argument('-D', '--damp', default=0.1, type=float,
                    help='viscous damping (for Langevin)')

parser.add_argument('-R', '--run_length', default=200, type=int,
                    help='number of MD steps between MC moves')
parser.add_argument('--MC_moves', default=1.0, type=float,
                    help='number of MC moves per rod between MD runs')

parser.add_argument('--clusters', default=2.5, type=float,
                    help='the max distance (in rod radii) for two rods to be\
in the same cluster (put to 0.0 to turn cluster tracking off)')

parser.add_argument('-o', '--output_freq', type=int,
                    help='configuration output frequency (in MD steps);\
default behavior is after every batch of MC moves')
parser.add_argument('-s', '--silent', action='store_true',
                    help="doesn't print anything to stdout")

args = parser.parse_args()

#========================================================================================

import os
if not os.path.exists(args.output_folder):
    os.makedirs(args.output_folder)

#from mpi4py import MPI #TODO make MPI work...
from lammps import PyLammps
import lammps_multistate_rods as rods
from tools.prepare_fibril import prepare_fibril

if args.seed is None:
    import time
    args.seed = int((time.time() % 1)*1000000)
    print "WARNING: no seed given explicitly; using:", args.seed
    
dump_path = str(args.cell_size)+'-'+str(args.num_cells)+'_'+str(args.seed)+'.dump'
dump_path = os.path.join(args.output_folder, dump_path)

fibril_path = os.path.join(args.output_folder, 'fibril.dat')
    
log_path = os.path.join(args.output_folder, str(args.seed)+'_lammps.log')

py_lmp = PyLammps(cmdargs=['-screen','none'])
model = rods.Model(args.config_file)
box_size = args.num_cells * args.cell_size
simulation = rods.Simulation(py_lmp, model, args.seed, args.temp, args.output_folder,
                             log_path, clusters=args.clusters)
py_lmp.units("lj")
py_lmp.dimension(3)
py_lmp.boundary("p p p")
py_lmp.lattice("sc", 1/(args.cell_size**3))
py_lmp.region("box", "block",
              -args.num_cells / 2, args.num_cells / 2,
              -args.num_cells / 2, args.num_cells / 2,
              -args.num_cells / 2, args.num_cells / 2)
simulation.setup("box")

# create fibril
fibril_edges = prepare_fibril(model, args.N, args.phi, args.theta, args.r0, fibril_path)
simulation.create_rods(state_ID=model.num_states-1, file=fibril_path)
# create other rods
xmin = fibril_edges[0][0] - model.rod_length / 2
xmax = fibril_edges[0][1] + model.rod_length / 2
ymin = fibril_edges[1][0] - model.rod_length / 2
ymax = fibril_edges[1][1] + model.rod_length / 2
zmin = fibril_edges[2][0] - model.rod_length / 2
zmax = fibril_edges[2][1] + model.rod_length / 2
py_lmp.region("fibril", "block", xmin, xmax, ymin, ymax, zmin, zmax, "units box")
#TODO py_lmp.region("box_minus_fibril", "subtract", 2, "box", "fibril")
py_lmp.region("left", "block",
              -box_size/2, xmin,
              -box_size / 2, box_size / 2,
              -box_size / 2, box_size / 2,
              "units box")
py_lmp.region("right", "block",
               xmax, box_size / 2,
              -box_size / 2, box_size / 2,
              -box_size / 2, box_size / 2,
              "units box")
py_lmp.region("front", "block",
              -box_size / 2, box_size / 2,
              -box_size / 2, ymin,
              -box_size / 2, box_size / 2,
              "units box")
py_lmp.region("back", "block",
              -box_size / 2, box_size / 2,
               ymax, box_size / 2,
              -box_size / 2, box_size / 2,
              "units box")
py_lmp.region("down", "block",
              -box_size / 2, box_size / 2,
              -box_size / 2, box_size / 2,
              -box_size / 2, zmin,
              "units box")
py_lmp.region("up", "block",
              -box_size / 2, box_size / 2,
              -box_size / 2, box_size / 2,
               zmax, box_size / 2,
              "units box")
py_lmp.region("box_minus_fibril", "union", 6, "up", "down", "front", "back", "left", "right")
simulation.create_rods(region = "box_minus_fibril")

# DYNAMICS
py_lmp.fix("thermostat", "all", "langevin", args.temp, args.temp, args.damp, args.seed)#, "zero yes")
simulation.set_rod_dynamics("nve")

py_lmp.neigh_modify("every 1 delay 1")

# OUTPUT
dump_elems = "id x y z type mol"
if args.clusters > 0.0:
    dump_elems += " c_"+simulation.cluster_compute
if (args.output_freq != None):
    py_lmp.dump("dump_cmd", "all", "custom", args.output_freq, dump_path, dump_elems)
    py_lmp.dump_modify("dump_cmd", "sort id")
else:
    py_lmp.variable("out_timesteps", "equal", "stride(1,{:d},{:d})".format(args.sim_length+1, args.run_length))
    py_lmp.dump("dump_cmd", "all", "custom", 1, dump_path, dump_elems)
    py_lmp.dump_modify("dump_cmd", "every v_out_timesteps", "sort id")

py_lmp.thermo_style("custom", "step atoms", "pe temp")
py_lmp.thermo(args.run_length)

# RUN...
mc_moves_per_run = int(args.MC_moves * simulation.rods_count())

if mc_moves_per_run == 0:
    py_lmp.command('run {:d}'.format(args.sim_length))
else:
    for i in range(int(args.sim_length/args.run_length)-1):   
        py_lmp.command('run {:d} post no'.format(args.run_length))
        success = simulation.conformation_Monte_Carlo(mc_moves_per_run)
        if not args.silent:
            base_count = simulation.state_count(0)
            beta_count = simulation.state_count(1)
            print 'step {:d} / {:d} :  beta-to-base ratio = {:d}/{:d} = {:.5f} (accept rate = {:.5f})'.format(
                    (i+1)*args.run_length, args.sim_length, beta_count, base_count,
                        float(beta_count)/base_count, float(success)/mc_moves_per_run)
            
    py_lmp.command('run {:d} post no'.format(args.run_length))
