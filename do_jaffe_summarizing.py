#!/usr/bin/env python

# Summarize photos in a city, a la Jaffe 2006. 

import argparse, csv, collections, math, sys, pprint, numpy as np, random
import matplotlib.pyplot as plt
from munkres import Munkres, print_matrix # Hungarian clustering.
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--yfcc_file', default='data/pgh_yfcc100m.csv', help=' ')
args = parser.parse_args()

# The one tricky parameter; roughly, min cluster size.
T = 7

def dist(p1, p2):
    """ Euclidean distance between two (lat, lon) points. """
    # TODO should probably use haversine instead, welp.
    return math.sqrt(math.pow(p1[0] - p2[0], 2) + math.pow(p1[1] - p2[1], 2))

def cluster_dist(c1, c2):
    """ Distance between 2 clusters, as Goldberger and Tassa describe. c1 and
    c2 are both lists of points. """
    min_dist = sys.maxint
    for pt1 in c1:
        for pt2 in c2:
            if dist(pt1, pt2) < min_dist:
                min_dist = dist(pt1, pt2)
                closest_pt1 = pt1
                closest_pt2 = pt2
    # Check if there are at least T points in either cluster close enough.
    pts_close_enough1 = 0
    for pt in c1:
        if dist(pt, closest_pt1) < min_dist:
            pts_close_enough1 += 1
    if pts_close_enough1 >= T:
        return sys.maxint
    pts_close_enough2 = 0
    for pt in c2:
        if dist(pt, closest_pt2) < min_dist:
            pts_close_enough2 += 1
    if pts_close_enough2 >= T:
        return sys.maxint

    return min_dist

def make_clusters(indexes):
    """ indexes = [(0, 48), (1, 71), ...]
    clusters = [[0, 48, 73, 12], [1, 71], [2, 19, 92], ...] """
    clusters = []
    indexes_dict = {a: b for a, b in indexes}
    while len(indexes_dict) > 0:
        new_cluster = []
        pt1 = indexes_dict.keys()[0]
        pt2 = indexes_dict.pop(pt1)
        if pt1 == pt2: # cycle of size 1
            new_cluster.append(pt1)
            continue
        new_cluster.append(pt1)
        new_cluster.append(pt2)
        current_pt = pt2
        while True:
            next_pt = indexes_dict.pop(current_pt)
            if next_pt in new_cluster:
                break
            else:
                new_cluster.append(next_pt)
                current_pt = next_pt
        clusters.append(new_cluster)
    return clusters

def build_distance_matrix(cluster_pts):
    """ clusters = list of pts; e.g.
    [[[(40.523, -80.084), (40.498, -80.012)], [(40.479, -79.954), (40.478, -79.956)], ..."""
    dist_matrix = []
    for cluster in cluster_pts:
        dist_matrix.append([cluster_dist(cluster, othercluster) for othercluster in cluster_pts])
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
        if cycle[0] != cycle[1]:
            return False
    return True

munkres = Munkres()

lines = [line for line in csv.reader(open(args.yfcc_file))]
pts = [(float(line[2]), float(line[3])) for line in lines]

clusters = collections.defaultdict(list) # dict of iteration number -> indexes.
clusters[0] = [[pt] for pt in pts]
i = 0
while True:
    new_clusters = []
    dist_matrix = build_distance_matrix(clusters[i])
    indexes = munkres.compute(dist_matrix)
    cluster_indexes = make_clusters(indexes)

    for cluster_cycle in cluster_indexes:
        new_clusters.append(flatten([clusters[i][c] for c in cluster_cycle]))

    if is_all_singletons(new_clusters):
        break
    i += 1
    clusters[i] = new_clusters

final_clusters = clusters[len(clusters)-1]


## Just plotting this stuff.
xs = []
ys = []
colors = []
ctr = 0
for cluster in final_clusters:
    ctr += 1
    color = ctr
    for pt in cluster:
        xs.append(pt[0])#* 100 + random.random())
        ys.append(pt[1])#* 100 + random.random())
        colors.append(color)

plt.scatter(xs, ys, c=colors)
plt.show()
