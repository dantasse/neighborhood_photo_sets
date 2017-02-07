#!/usr/bin/env python

# Make a JSON file of the form:
# {'pgh': {'Shadyside': {'twitter_random': ['www.twimg.com/...', ...]}}}
# Categories are 'twitter_random', 'streetview_random', 'streetview_venues',
# 'flickr_random', 'flickr_selected_tags', 'flickr_tfidf'.
# Requires the following files for each city:
# nghd_list.json (just one file, contains all cities' neighborhoods.)
# tweet_(city)_images.csv

import argparse, csv, collections, random, json, os, ast
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--data_directory', default='data/', help=' ')
parser.add_argument('--output_file', default='data/urls.json', help=' ')
args = parser.parse_args()

# Load the neighborhoods from the nghd_list.json file.
output = {'austin': {}, 'chicago': {}, 'houston': {}, 'pgh': {}, 'sf': {}}
nghd_list = json.load(open(args.data_directory + 'nghd_list.json'))
for city, nghds in nghd_list.iteritems():
    for nghd in nghds:
        output[city][nghd] = collections.defaultdict(list)
ALL_CITIES = output.keys()
print ALL_CITIES

# Get the Twitter-random photos.
# for city in ['austin', 'chicago', 'houston', 'pgh', 'sf']:
for city in ALL_CITIES:
    twitter_photos = collections.defaultdict(list)
    print "Reading Twitter photos for: " + city
    for line in csv.reader(open(args.data_directory + 'tweet_' + city + '_images.csv')):
        nghd = line[7]
        if nghd != 'None':
            twitter_photos[nghd].append(line[8])
    for nghd, urls in twitter_photos.iteritems():
        if len(urls) < 50:
            output[city][nghd]['twitter_random'] = urls
        else:
            output[city][nghd]['twitter_random'] = random.sample(urls, 50)

# Get the Street View random and Street View venue photos.
for city in ALL_CITIES:
    print "Reading Street view photos for " + city
    for nghd in output[city]:
        nghd_sanitized = nghd.replace("/", "-")
        for photo in os.listdir('images/' + city + '/streetview/'):
            if photo.startswith(nghd_sanitized):
                output[city][nghd]['streetview_random'].append(
                        'images/'+city+'/streetview/'+photo)
        for photo in os.listdir('images/' + city + '/venues_streetview/'):
            if photo.startswith(nghd_sanitized):
                output[city][nghd]['streetview_venues'].append(
                        'images/'+city+'/venues_streetview/'+photo)

for city in ALL_CITIES:
    print "Reading Flickr photos for " + city
    flickr_photos = collections.defaultdict(list)
    flickr_good_photos = collections.defaultdict(list)
    for line in csv.reader(open(args.data_directory + city + '_yfcc100m.csv')):
        url = line[4]
        tags = ast.literal_eval(line[5])
        nghd = line[7]
        if nghd != 'None':
            flickr_photos[nghd].append(url)
            # Here's where you put criteria for the "selected tags".
            if 'outdoor' in tags:
                flickr_good_photos[nghd].append(url)

    for nghd, urls in flickr_photos.iteritems():
        if len(urls) < 50:
            output[city][nghd]['flickr_random'] = urls
        else:
            output[city][nghd]['flickr_random'] = random.sample(urls, 50)

    for nghd, urls in flickr_good_photos.iteritems():
        if len(urls) < 50:
            output[city][nghd]['flickr_selected_tags'] = urls
        else:
            output[city][nghd]['flickr_selected_tags'] = random.sample(urls, 50)



json.dump(output, open(args.output_file, 'w'), indent=2)

