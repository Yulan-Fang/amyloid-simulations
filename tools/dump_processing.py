# encoding: utf-8
'''
A program/tool for post-processing of LAMMPS dump files generated by the
"lammps_multistate_rods" library.

Created on 16 May 2018

@author: Eugen Rožić
'''

import os
import argparse

import lammps_multistate_rods as rods
import lammps_multistate_rods.tools as rods_tools

parser = argparse.ArgumentParser(description='Application for the processing of LAMMPS'\
                                 'dump files generated with lammps_multistate_rods library',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('config_file',
                    help='path to the "lammps_multistate_rods" model config file')
parser.add_argument('in_files', nargs='+',
                    help='path(s) of the dump file(s) to analyse')

parser.add_argument('-c', '--cluster_data', action='store_true',
                    help='produce a "_cluster_data" file for each input file')
parser.add_argument('-l', '--last_dump', action='store_true',
                    help='produce a "_last_dump" file, containing the last snapshot, for each input file')
parser.add_argument('-m', '--membrane', action='store_true', 
                    help='produce an "_adsorbed" file for each input file')

parser.add_argument('-t', '--type_offset', type=int, default=0,
                    help='the type offset for the rod models of the simulation (for cluster data)')
parser.add_argument('-n', '--every', type=int, default=1,
                    help='every which snapshot to analyse (for cluster data')

args = parser.parse_args()
    
model = rods.Model(args.config_file)
    
for in_file in args.in_files:
    
    if args.cluster_data:
        raw_data = rods_tools.parse_dump_file(in_file)
        cluster_output_path = os.path.splitext(in_file)[0]+"_cluster_data"
        timesteps, box_sizes, cluster_data = rods_tools.clusters.get_cluster_data(
            raw_data, args.every, model, args.type_offset)
        rods_tools.clusters.write_cluster_data(timesteps, box_sizes, cluster_data,
                                               cluster_output_path)
    
    if args.last_dump:
        raw_data = rods_tools.parse_dump_file(in_file)
        last_dump_output_path = os.path.splitext(in_file)[0]+"_last_dump"
        for timestep, box_bounds, data_structure, data in raw_data:
            pass
        rods_tools.write_dump_snapshot((timestep, box_bounds, data_structure, data),
                                       last_dump_output_path)
    
    if args.membrane:
        raw_data = rods_tools.parse_dump_file(in_file)
        adsorbed_output_path = os.path.splitext(in_file)[0]+"_adsorbed"
        try:
            timesteps, box_sizes, mem_cluster_data = rods_tools.clusters.get_cluster_data(
                raw_data, args.every, model, args.type_offset, compute_ID='mem_cluster')
        except KeyError:
            raise Exception('No membrane data to analyse! (invalid -m option)')
        biggest_cluster_IDs = [] #those clusters will be the membrane + adsorbed
        for snapshot in mem_cluster_data:
            biggest_cluster_ID = 0
            biggest_cluster_size = 0
            for cluster_ID, cluster in snapshot.iteritems():
                cluster_size = len(cluster)
                if cluster_size > biggest_cluster_size:
                    biggest_cluster_size = cluster_size
                    biggest_cluster_ID = cluster_ID
            biggest_cluster_IDs.append(biggest_cluster_ID)
        adsorbed_rods = []
        for i in range(len(biggest_cluster_IDs)):
            adsorbed = []
            for elem in mem_cluster_data[i][biggest_cluster_IDs[i]]:
                if elem[1] != None: #if a rod, not something else (e.g. a lipid)
                    adsorbed.append(elem[0])
            adsorbed_rods.append(adsorbed)
            
        rods_tools.clusters.write_cluster_data(timesteps, box_sizes, adsorbed_rods,
                                               adsorbed_output_path)        