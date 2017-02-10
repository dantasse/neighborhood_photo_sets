#!/usr/bin/env python

# Summarize photos in a city, a la Jaffe 2006. 
# Hungarian clustering from Goldberger:
# http://www.openu.ac.il/personal_sites/tamirtassa/download/journals/clustering.pdf

import argparse, csv, collections, math, sys, random, numpy as np
import matplotlib.pyplot as plt
from haversine import haversine
from munkres import Munkres # Hungarian clustering.
# import hungarian, LAPJV
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--yfcc_file', default='data/pgh_yfcc100m.csv', help=' ')
parser.add_argument('--t_param', type=int, default=7, help='T as in the \
        Hungarian Clustering paper.')
parser.add_argument('--w_param', type=float, default=0.1, help='w as in the \
        Jaffe paper; what makes a cluster "prominent".')
parser.add_argument('--plot', action='store_true', help='if set, plot the results.')
parser.add_argument('--max_photos_per_nghd', type=int, default=1000, help='If there\
        are more than this many photos per nghd, only pick a random subset of\
        them (so that it is reasonably computable.) 0 = no limit.')
parser.add_argument('--output_file', default='jaffe_photos.csv', help=' ')
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

def is_ok_tag(tag):
    if 'nikon' in tag or 'canon' in tag or 'sony' in tag or 'f%2F' in tag\
            or 'filter' in tag or '+mm' in tag or '0mm' in tag:
        return False
    if tag.isdigit():
        return False
    if tag in ['square', 'no+flash', 'instagram+app', 'square+format',\
            'iphoneography', 'photoshop', 'illustrator', 'hdr', 'iphoto+original']:
        return False
    return True


class Cluster:
    """ Represents a cluster of photos, a la Hungarian clustering. """
    def __init__(self, subclusters, photos):
        self.subclusters = subclusters
        self.photos = photos
        self.w_param = args.w_param

    def all_points(self):
        if self.subclusters == None:
            return [(photo[2], photo[3]) for photo in self.photos]
        else:
            return flatten([subcluster.all_points() for subcluster in self.subclusters])

    def all_photos(self):
        if self.subclusters == None:
            return self.photos
        else:
            return flatten([subcluster.all_photos() for subcluster in self.subclusters])

    def tag_counts(self):
        """ Returns a Counter of each tag here and how often it is used. """
        tag_sets = [photo[5] for photo in self.all_photos()]
        tag_counter = collections.Counter()
        for tag_set in tag_sets:
            tags = tag_set.strip('"').split(',')
            tag_counter.update([tag for tag in tags if is_ok_tag(tag)])
        return tag_counter 

    def photog_counts(self):
        """ Returns a Counter of how often each NSID occurs in the dataset."""
        return collections.Counter([photo[1] for photo in self.all_photos()])


    def score(self, global_tag_counts, global_photog_counts):
        """ Just the score for this cluster, as in Jaffe et al. Need
        global_tag_counts to compute tf-idf."""

        if len(self.all_photos()) == 0:
            return 0

        # Ignore relevance

        # Tag-distinguishability
        tfidfs = []
        tag_counts = self.tag_counts()
        this_cluster_num_photos = len(self.all_photos())
        total_num_photos = sum(global_photog_counts.values()) # yep, photog.
        for tag in set(tag_counts.keys()):
            tf = tag_counts[tag] * 1.0 / this_cluster_num_photos
            idf = total_num_photos * 1.0 / global_tag_counts[tag]
            tfidfs.append(tf * math.log(idf))
        tag_disting = math.sqrt(sum([math.pow(x, 2) for x in tfidfs]))

        # Photographer-distinguishability
        photog_tfidfs = []
        photog_counts = self.photog_counts()
        for photographer in photog_counts.keys():
            tf = photog_counts[photographer] * 1.0 / this_cluster_num_photos
            idf = total_num_photos * 1.0 / global_photog_counts[photographer]
            photog_tfidfs.append(tf * math.log(idf))
        photog_disting = math.sqrt(sum([math.pow(x, 2) for x in photog_tfidfs]))

        # Density
        points = self.all_points()
        xs = [pt[1] for pt in points]
        ys = [pt[0] for pt in points]
        sigma = math.sqrt(math.pow(np.std(xs), 2) + math.pow(np.std(ys), 2))
        density = 1.0 / (1.0 + sigma)
        
        # Ignore image quality.

        # Go with regular old average for now. Meh.
        score = (tag_disting + photog_disting + density) / 3.0
        return score

    def pop_a_photo(self):
        """ Returns a randomly selected photo from this cluster. Removes it
        from this cluster."""
        if self.subclusters == [] and self.photos == []:
            return None
        if self.subclusters == None:
            return self.photos.pop(0)
        else:
            cluster_to_get = random.choice(self.subclusters)
            photo = cluster_to_get.pop_a_photo()
            if len(cluster_to_get.all_photos()) == 0:
                self.subclusters.remove(cluster_to_get)
            return photo

    def photo_order(self, global_tag_counts, global_photog_counts):
        """ The end goal of this thing! Returns an order of photos in this
        cluster."""
        if self.subclusters == None:
            if len(self.photos) != 1:
                print "There should only be one photo here."
            return self.photos # which I think will always have 1 element?

        order = []
        # First do the Head. find the "prominent" subclusters.
        subcluster_scores = {sc: sc.score(global_tag_counts, global_photog_counts) for sc in self.subclusters}
        subcluster_scores = sorted(subcluster_scores.items(), key=lambda x: -x[1])
        total_score = sum([x[1] for x in subcluster_scores])
        for subcluster, score in subcluster_scores:
            if score / total_score >= self.w_param:
                # it's "prominent"!
                # we would take the "most relevant" photo, but we don't have a
                # measure of relevance, so w/e.
                order.append(subcluster.pop_a_photo())

        # Now do the Tail.
        while len(self.all_photos()) > 0:
            subcluster_scores = {sc: sc.score(global_tag_counts, global_photog_counts) for sc in self.subclusters}
            subcluster_scores = sorted(subcluster_scores.items(), key=lambda x: -x[1])
            total_score = sum([x[1] for x in subcluster_scores])
            random_pick = random.random() * total_score
            for subcluster, score in subcluster_scores:
                if random_pick < score:
                    order.append(subcluster.pop_a_photo())
                    continue
                else:
                    random_pick -= score
        return order

munkres = Munkres()
lines = [line for line in csv.reader(open(args.yfcc_file))]
nghd_photos = collections.defaultdict(list)
for photo in lines:
    photo[2] = float(photo[2])
    photo[3] = float(photo[3])
    nghd_photos[photo[8]].append(photo)

writer = csv.writer(open(args.output_file, 'w'))

for nghd, photos in nghd_photos.items():
    if nghd == "None" or nghd == 'Mt. Oliver': # TODO undo this
        continue
    if args.max_photos_per_nghd > 0 and len(photos) > args.max_photos_per_nghd:
        photos = random.sample(photos, args.max_photos_per_nghd) # TODO making this computable :-/
    print "Processing ", nghd, ", this many photos: ", str(len(photos))

    clusters = collections.defaultdict(list) # dict of iteration number -> cluster list.
    clusters[0] = [Cluster(subclusters=None, photos=[photo]) for photo in photos]
    i = 0
    while True:
        new_clusters = []
        dist_matrix = build_distance_matrix(clusters[i])
        dist_matrix = np.array(dist_matrix)

        indexes = munkres.compute(dist_matrix)
        # OR
        # row_col_indexes = hungarian.lap(dist_matrix)
        # indexes = zip(row_col_indexes[0], row_col_indexes[1])
        # "segmentation fault" - eh.
        # OR
        # row_col_indexes = LAPJV.lap(dist_matrix)
        # print row_col_indexes[1]
        # indexes = zip(row_col_indexes[0], row_col_indexes[1])
        # "array is too big" - eh.

        print indexes
        cluster_cycle_indexes = make_cluster_cycles(indexes)

        for cluster_cycle in cluster_cycle_indexes:
            new_cluster = Cluster(subclusters=[clusters[i][c] for c in cluster_cycle], photos=[])
            new_clusters.append(new_cluster)

        print "Finished a round, this many clusters: ", len(new_clusters)
        if is_all_singletons(cluster_cycle_indexes):
            break
        i += 1
        clusters[i] = new_clusters

    final_clusters = clusters[len(clusters)-1]

    global_tag_counts = collections.Counter()
    for photo in photos:
        tag_set = photo[5].strip('"').split(',')
        global_tag_counts.update([tag for tag in tag_set if is_ok_tag(tag)])
    global_photog_counts = collections.Counter([photo[1] for photo in photos])

    supercluster = Cluster(subclusters=final_clusters, photos=[])
    order = supercluster.photo_order(global_tag_counts, global_photog_counts)
    for row in order[0:20]:
        writer.writerow(row)
    

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
                xs.append(pt[0])
                ys.append(pt[1])
                colors.append(color)

        plt.scatter(xs, ys, c=colors)
        plt.show()
