""" 
Route Optimization Script 
Converted from Jupyter Notebook to Python script with modular functions. 
""" 

import numpy as np
import pandas as pd
import osmnx as ox
import networkx as nx
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import folium

# Load dataset
def load_data(file_path, city_filter):
    df = pd.read_csv(file_path)
    df = df[df['City'] == city_filter][['Street Address', 'Latitude', 'Longitude']].reset_index(drop=True)
    df = df.reset_index().rename(columns={'index': 'id', 'Latitude': 'y', 'Longitude': 'x'})
    return df

# Create road network graph
def create_graph(start_location, distance=10000):
    G = ox.graph_from_point(start_location, dist=distance, network_type='drive')
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    return G

# Compute distance matrix
def compute_distance_matrix(G, nodes):
    def compute_travel_time(a, b):
        try:
            return nx.shortest_path_length(G, source=a, target=b, method='dijkstra', weight='travel_time')
        except:
            return np.nan

    distance_matrix = np.asarray([[compute_travel_time(a, b) for b in nodes] for a in nodes])
    return np.nan_to_num(distance_matrix, nan=1e6)

# Solve TSP using OR-Tools
def solve_tsp(distance_matrix, nodes):
    num_locations = len(nodes)
    manager = pywrapcp.RoutingIndexManager(num_locations, 1, 0)
    model = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(distance_matrix[from_node, to_node])

    transit_callback_index = model.RegisterTransitCallback(distance_callback)
    model.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

    solution = model.SolveWithParameters(search_parameters)
    
    if solution:
        index = model.Start(0)
        optimized_route = []
        while not model.IsEnd(index):
            optimized_route.append(manager.IndexToNode(index))
            index = solution.Value(model.NextVar(index))
        optimized_route.append(manager.IndexToNode(index))
        return optimized_route, solution.ObjectiveValue()
    else:
        return None, None

# Plot route on map
def plot_route(G, nodes, route):
    map_ = folium.Map(location=[G.nodes[nodes[0]]['y'], G.nodes[nodes[0]]['x']], zoom_start=12)
    for i in range(len(route) - 1):
        a, b = nodes[route[i]], nodes[route[i + 1]]
        path = nx.shortest_path(G, source=a, target=b, method='dijkstra', weight='travel_time')
        coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in path]
        folium.PolyLine(coords, color='blue', weight=2.5, opacity=1).add_to(map_)
    return map_

# Main execution
if __name__ == '__main__':
    file_path = '/mnt/data/data_stores.csv'
    city = 'London'

    # Load data
    df_london = load_data(file_path, city)
    start_location = df_london.loc[0, ['y', 'x']].values

    # Create graph
    G = create_graph(start_location)
    df_london['node'] = df_london.apply(lambda row: ox.distance.nearest_nodes(G, row['x'], row['y']), axis=1)
    df_london = df_london.drop_duplicates('node', keep='first')

    # Compute distances
    nodes = df_london['node'].tolist()
    distance_matrix = compute_distance_matrix(G, nodes)

    # Solve TSP
    route, total_travel_time = solve_tsp(distance_matrix, nodes)
    if route:
        print('Optimized Route (Node IDs):', route)
        print('Total Travel Time:', total_travel_time, 'seconds')

        # Plot route
        map_ = plot_route(G, nodes, route)
        map_.save('optimized_route_map.html')
        print('Map saved as optimized_route_map.html')
    else:
        print('No solution found.')
