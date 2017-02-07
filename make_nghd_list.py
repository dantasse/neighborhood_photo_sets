#!/usr/bin/env python

# Just make a file that looks like this:
# { "Pittsburgh": ["Shadyside", "Squirrel Hill North", ...],
#   "Chicago": ["Wicker Park", "Logan Square", ...] ...}

import argparse, csv, collections, json
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--output_file', default='nghd_list.json')
parser.add_argument('--source_files', nargs='+', default= ['nghd_bounds/austin.geojson',
        'nghd_bounds/chicago.geojson', 'nghd_bounds/houston.geojson',
        'nghd_bounds/pgh.geojson', 'nghd_bounds/sf.geojson'],
    help='All the neighborhood bounds files')
args = parser.parse_args()

output = {}
for file in args.source_files:
    city_name = file.replace('nghd_bounds/', '').replace('.geojson', '')
    json_data = json.load(open(file))
    nghd_list = list(set([n['properties']['name'] for n in json_data['features']]))
    output[city_name] = sorted(nghd_list)
json.dump(output, open(args.output_file, 'w'))

