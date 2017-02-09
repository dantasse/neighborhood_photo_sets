#!/usr/bin/env python

# Summarize photos in a city, a la Jaffe 2006. 
# Hungarian clustering from Goldberger:
# http://www.openu.ac.il/personal_sites/tamirtassa/download/journals/clustering.pdf

import argparse, csv, collections, math, sys, random
import matplotlib.pyplot as plt
from haversine import haversine
from munkres import Munkres # Hungarian clustering.
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--yfcc_file', default='data/pgh_yfcc100m.csv', help=' ')
parser.add_argument('--t_param', type=int, default=7, help='T as in the \
        Hungarian Clustering paper.')
parser.add_argument('--plot', action='store_true', help='if set, plot the results.')
args = parser.parse_args()

# The one tricky parameter; roughly, min cluster size.
T = args.t_param

def dist(p1, p2):
    """ Distance between two (lat, lon) points. """
    # return math.sqrt(math.pow(p1[0] - p2[0], 2) + math.pow(p1[1] - p2[1], 2))
    return haversine(p1, p2)

def cluster_dist(c1, c2):
    """ Distance between 2 clusters, as Goldberger and Tassa describe. c1 and
    c2 are both Cluster objects. """
    min_dist = sys.maxint
    for pt1 in c1.all_points():
        for pt2 in c2.all_points():
            if dist(pt1, pt2) < min_dist:
                min_dist = dist(pt1, pt2)
                closest_pt1 = pt1
                closest_pt2 = pt2
    # Check if there are at least T points in either cluster close enough.
    pts_close_enough1 = 0
    for pt in c1.all_points():
        if dist(pt, closest_pt1) < min_dist:
            pts_close_enough1 += 1
    if pts_close_enough1 >= T:
        return sys.maxint
    pts_close_enough2 = 0
    for pt in c2.all_points():
        if dist(pt, closest_pt2) < min_dist:
            pts_close_enough2 += 1
    if pts_close_enough2 >= T:
        return sys.maxint

    return min_dist

def make_cluster_cycles(indexes):
    """ indexes = [(0, 48), (1, 71), ... (12, 0) ... (48, 73) ... (73, 12)...]
    cycles = [[0, 48, 73, 12], [1, 71], [2, 19, 92], ...] """
    print indexes
    cycles = []
    indexes_dict = {a: b for a, b in indexes}
    while len(indexes_dict) > 0:
        new_cycle = []
        pt1 = indexes_dict.keys()[0]
        pt2 = indexes_dict.pop(pt1)
        if pt1 == pt2: # cycle of size 1
            new_cycle.append(pt1)
            cycles.append(new_cycle)
            continue
        new_cycle.append(pt1)
        new_cycle.append(pt2)
        current_pt = pt2
        while True:
            next_pt = indexes_dict.pop(current_pt)
            if next_pt in new_cycle:
                break
            else:
                new_cycle.append(next_pt)
                current_pt = next_pt
        cycles.append(new_cycle)
    return cycles

def build_distance_matrix(clusters):
    """ clusters = list of Cluster objects.
    [[[(40.523, -80.084), (40.498, -80.012)], [(40.479, -79.954), (40.478, -79.956)], ..."""
    dist_matrix = []
    for cluster in clusters:
        dist_matrix.append([cluster_dist(cluster, othercluster) for othercluster in clusters])
    # Now to set along the diagonal. If it's "too far" from every other cluster,
    # set its self-distance to -inf. Otherwise its self-distance is +inf.
    for i in range(len(dist_matrix)):
        dist_matrix[i][i] = sys.maxint
    for i in range(len(dist_matrix)):
        is_all_inf = True
        for j in range(len(dist_matrix)):
            if dist_matrix[i][j] < sys.maxint:
                is_all_inf = False
        if is_all_inf:
            dist_matrix[i][i] = -1 * sys.maxint
    return dist_matrix
 
def flatten(lol):
    """ lol is a list of lists. returns just one list."""
    return [item for ls in lol for item in ls]

def is_all_singletons(cycles):
    for cycle in cycles:
        if len(cycle) > 1:
            return False
    return True

class Cluster:
    """ Represents a cluster of photos, a la Hungarian clustering. """
    def __init__(self, subclusters, points):
        self.subclusters = subclusters
        self.points = points

    def all_points(self):
        if self.subclusters == None:
            return self.points
        else:
            return flatten([subcluster.all_points() for subcluster in self.subclusters])

munkres = Munkres()

lines = [line for line in csv.reader(open(args.yfcc_file))]
pts = [(float(line[2]), float(line[3])) for line in lines]

clusters = collections.defaultdict(list) # dict of iteration number -> cluster list.
clusters[0] = [Cluster(subclusters=None, points=[pt]) for pt in pts]
i = 0
while True:
    new_clusters = []
    dist_matrix = build_distance_matrix(clusters[i])
    indexes = munkres.compute(dist_matrix)
    cluster_cycle_indexes = make_cluster_cycles(indexes)

    for cluster_cycle in cluster_cycle_indexes:
        new_cluster = Cluster(subclusters=[clusters[i][c] for c in cluster_cycle], points=[])
        new_clusters.append(new_cluster)
        # new_clusters.append(flatten([clusters[i][c] for c in cluster_cycle]))

    print "Finished a round, this many clusters: ", len(new_clusters)
    # print [len(a.subclusters) for a in new_clusters]
    if is_all_singletons(cluster_cycle_indexes):
        break
    i += 1
    clusters[i] = new_clusters

final_clusters = clusters[len(clusters)-1]

if args.plot:
    ## Just plotting this stuff.
    xs = []
    ys = []
    colors = []
    ctr = 0
    for cluster in final_clusters:
        ctr += 1
        color = ctr
        for pt in cluster.all_points():
            xs.append(pt[0])#* 100 + random.random())
            ys.append(pt[1])#* 100 + random.random())
            colors.append(color)

    plt.scatter(xs, ys, c=colors)
    plt.show()
