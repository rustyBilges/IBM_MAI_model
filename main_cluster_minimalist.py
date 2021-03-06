
import os
from datetime import datetime
import shutil
import networkx as nx
import csv
import math
import numpy as np

from copy import copy

from web import Network
from network_creator import obtain_interactions_network
from ecosystem import Ecosystem

from utilities import get_out_row, get_eco_state_row, NetStats, EcosystemStats, write_spatial_analysis, write_spatial_state, write_adjacency_matrix

from configure import ITERATIONS, HABITAT_LOSS, HABITAT_LOSS_ITER, INVASION, INVASION_ITER, NETWORK_RESET, SPATIAL_VARIATION
from configure import REFRESH_RATE, REMOVAL_LEVEL, REMOVAL_FRACTION, EXTINCTION_EVENT, TIME_WINDOW
from configure import SRC_NET_FILE, READ_FILE_NETWORK, NETWORK_RECORD, ITERATIONS_TO_RECORD, INT_STRENGTHS, RECORD_SPATIAL_VAR


if __name__ == '__main__':
    start_sim = datetime.now()
    
    ##### these modifications are performed so different replicates can be run on the cluster
    #job = '1'  ## Manually set these values 
    #task = '1'    
    job = os.environ['PBS_JOBID'];  ## Take values from Blue Crystal job ref.
    job = job[0:7]
    task = os.environ['PBS_ARRAYID'];
    
    #output_dir = '../'  ## Use this option if running locally with src directory. (Not batch submission)
    output_dir = './' + job + '_' + task;

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if (os.path.isfile('./output/'+SRC_NET_FILE)):
        shutil.copy('./output/'+SRC_NET_FILE, output_dir)
    ##############################################
    # we now make sure that links between TL 0 and 3 are removed for any network, both those read from file and those created on the fly.  
    

    network_file = output_dir+'/'+SRC_NET_FILE  ## use this when generating niche modle networks and want to save in output directory
    
    #network_file = SRC_NET_FILE  ## use this when running with networks saved locally in src
    #network_file = output_dir + '/new_network_%d.graphml' %(int(task)-1)

    
    if READ_FILE_NETWORK:
        graph = nx.read_graphml(network_file)
        net = Network(graph)
    else:
        net = obtain_interactions_network()
    
    print 'connectance = ', net.connectance()
        
    tls = net.get_trophic_levels()
        
    top, top_preds = net.top_predators()
    basal, basal_sps = net.basal()
    for u,v in net.edges():
        if u in basal_sps and v in top_preds and tls[v] == 3:
            net.remove_edge(u,v)
                
    print 'new connectance = ', net.connectance()

    if not READ_FILE_NETWORK:
        net_to_save = net.copy()
        nx.write_graphml(net_to_save, network_file)
    
    ##############################################
    ecosystem = Ecosystem(net, drawing=False)
    ecosystem.initialise_world(True)

    # here it works out the inital populations
    series_counts = dict()
    dict_stats = get_eco_state_row(0, ecosystem)
    series_counts[0] = ecosystem.populations

    # we don't this to store data, just for its keys
    cumulative_sps_stats = dict.fromkeys(net.nodes(), None)

       
    ##############################################
    for i in range(1, ITERATIONS+1):
        print i
        ecosystem.update_world()
                                            
        
    	dict_stats = get_eco_state_row(ITERATIONS, ecosystem)
    	series_counts[i] = ecosystem.populations

        if HABITAT_LOSS and i == HABITAT_LOSS_ITER:
            ecosystem.apply_habitat_loss()

	if i%1000 == 0 or i == ITERATIONS:
    		net_temp = ecosystem.realised_net.copy()
    		series = copy(series_counts)
    		write_adjacency_matrix(i, NETWORK_RECORD, series, net_temp, output_dir)
		ecosystem.clear_realised_network()   ## WARNING: TO USE OR NOT TO USE!!
    	write_spatial_state(ecosystem, i, output_dir)  ## WARNING: THIS HAPPENS EVERY ITERATION
   
    ##############################################
### OUTPUT:
    ## testing output of adjacency and spatial state. Do they require more than the following?
    #net_temp = ecosystem.realised_net.copy()
    #series = copy(series_counts)
    #write_adjacency_matrix(ITERATIONS, NETWORK_RECORD, series, net_temp, output_dir)
    #write_spatial_state(ecosystem, ITERATIONS, output_dir)
   
    header_names = ['species', 'init_tl', 'mutualist', 'mutualistic_producer', 'individuals_init', 'immigrants', 'born', 'dead', 'individuals_final']
    file_species = open(output_dir+'/output_species.csv', 'w')
    out_species = csv.DictWriter(file_species, header_names)
    
    out_species.writeheader()
    out_row_species = dict()
    
    for sp in sorted(cumulative_sps_stats.keys()):
        out_row_species['species'] = sp
        
        init_tls = net.get_trophic_levels()
        out_row_species['init_tl'] = init_tls[sp]
        
        out_row_species['mutualist'] = net.node[sp]['mut']
        out_row_species['mutualistic_producer'] = net.node[sp]['mut_prod']
        
        out_row_species['individuals_init'] = series_counts[0][sp]
        out_row_species['individuals_final'] = series_counts[ITERATIONS][sp]
        
        out_species.writerow(out_row_species)
        
    file_species.close()
    
    pops = np.zeros((ITERATIONS+1, net.number_of_nodes()))
 
    
    for i in range(0, ITERATIONS+1):
	    for sp in sorted(cumulative_sps_stats.keys()):
		pops[i,int(sp)-1] = series_counts[i][sp]


    np.savetxt(output_dir+'/output_pops.csv', pops, delimiter=',')


    stop_sim = datetime.now()
    elapsed_sim = stop_sim-start_sim
    print 'time for simulation' , elapsed_sim    
    
     
