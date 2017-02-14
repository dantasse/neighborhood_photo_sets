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
        if nghd != 'None' and 'twimg' not in line[8]: # TODO for now excluding twimg links b/c many are broken
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
            if photo.startswith(nghd_sanitized + "_"): # So like all the Mission photos start with Mission_.
                output[city][nghd]['streetview_random'].append(
                        'images/'+city+'/streetview/'+photo)
        for photo in os.listdir('images/' + city + '/venues_streetview/'):
            if photo.startswith(nghd_sanitized + "_"):
                output[city][nghd]['streetview_venues'].append(
                        'images/'+city+'/venues_streetview/'+photo)

# Get flickr_random and flickr_selected_tags photos.
urls_nsids = {}
for city in ALL_CITIES:
    print "Reading Flickr photos for " + city
    flickr_photos = collections.defaultdict(list)
    flickr_good_photos = collections.defaultdict(list)
    for line in csv.reader(open(args.data_directory + city + '_yfcc100m.csv')):
        nsid = line[1]
        url = line[4]
        if line[5] == '':
            tags = []
        else:
            tags = line[5].split(',')
        nghd = line[8]
        if nghd != 'None':
            flickr_photos[nghd].append(url)
            # Here's where you put criteria for the "selected tags".
            # if 'outdoor' in tags: # nah let's just take all
            flickr_good_photos[nghd].append(url)
            urls_nsids[url] = nsid

    for nghd, urls in flickr_photos.iteritems():
        if len(urls) < 50:
            output[city][nghd]['flickr_random'] = urls
        else:
            output[city][nghd]['flickr_random'] = random.sample(urls, 50)

    for nghd, urls in flickr_good_photos.iteritems():
        nsids_seen = set()
        good_urls = []
        random.shuffle(urls)
        # Take 50 of these URLs, but only one per photographer.
        for url in urls:
            nsid = urls_nsids[url]
            if nsid not in nsids_seen:
                nsids_seen.add(nsid)
                good_urls.append(url)
                if len(good_urls) >= 50:
                    break
        output[city][nghd]['flickr_selected_tags'] = good_urls
        
# ok now get the flickr_jaffe photos.
for city in ALL_CITIES:
    nghd_urls = collections.defaultdict(list)
    print "Reading Jaffe photo orderings for " + city
    for line in csv.reader(open(args.data_directory + 'jaffe_' + city + '.csv')):
        nghd = line[8]
        url = line[4]
        nghd_urls[nghd].append(url)
    for nghd, urls in nghd_urls.items():
        output[city][nghd]['flickr_jaffe'] = urls[0:10]


json.dump(output, open(args.output_file, 'w'), indent=2)

