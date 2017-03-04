
# coding: utf-8

# # Wrangling Open Street Map data with MongoDB

# ## Map Area
# #### Austin, TX, United States
# https://mapzen.com/data/metro-extracts/metro/austin_texas/
# 
# https://www.openstreetmap.org/relation/113314
# 
# Austin is where I did my first internship so it is special to me. I am also familiar with the street names so I will be able to audit it better. I downloaded osm file from mapzen.com which consisted of data from the shaded area in the map below. It is over 1.4 GB(uncompressed)

# <img src = "img/SizeM.png">

# ## Auditing the data

# Due to the huge size of the data, I will load a smaller section of data as a sample. 

# In[1]:

import xml.etree.ElementTree as ET
import pprint
from collections import defaultdict
import re


# In[2]:

OSM_FILE = "austin_texas.osm"
SAMPLE_FILE = "sample.osm"


# In[ ]:

k = 10

def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag Reference: http://stackoverflow.com/questions/
    3095434/inserting-newlines-in-xml-file-generated-via-xml-etree-elementtree-in-python
    """
    context = iter(ET.iterparse(osm_file, events=('start', 'end')))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


with open(SAMPLE_FILE, 'wb') as output:
    output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    output.write('<osm>\n  ')

    # Write every kth top level element
    for i, element in enumerate(get_element(OSM_FILE)):
        if i % k == 0:
            output.write(ET.tostring(element, encoding='utf-8'))

    output.write('</osm>')


# After loading the sample data, lets parse one tag at a time with ElementTree and count the number of top level tags. Iterative parsing is utilized for this as data is too large to process on the complete document

# In[3]:

def count_tags(filename):
    """count tags in filename.
    
    Init 1 in dict if the key not exist, increment otherwise."""
    tags = {}
    for ev, elem in ET.iterparse(filename):
        tag = elem.tag
        if tag not in tags.keys():
            tags[tag] = 1
        else:
            tags[tag] += 1
    return tags


tags = count_tags(OSM_FILE)
pprint.pprint(tags)


# Next, Let us explore the data some more to check for potential problems in the data. I have created regular expressions to check for certain patterns in the tag "k=addr:", the function 'key_type' will count of each of the four tag categories in a dictionary:
#   "lower", for tags that contain only lowercase letters and are valid,
#   "lower_colon", for otherwise valid tags with a colon in their names,
#   "problemchars", for tags with problematic characters, and
#   "other", for other tags that do not fall into the other three categories.

# In[4]:

lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')


def key_type(element, keys):
    if element.tag == "tag":
        for tag in element.iter('tag'):
            k = tag.get('k')
            if lower.search(k):
                keys['lower'] += 1
            elif lower_colon.search(k):
                keys['lower_colon'] += 1
            elif problemchars.search(k):
                keys['problemchars'] += 1
            else:
                keys['other'] += 1
    return keys


def process_map(filename):
    keys = {"lower": 0, "lower_colon": 0, "problemchars": 0, "other": 0}
    for _, element in ET.iterparse(filename):
        keys = key_type(element, keys)
    return keys


keys = process_map(OSM_FILE)
pprint.pprint(keys)


# Next, let's now find out how many unique users have contributed to the map in this osm, following code gives us 1260 different unique users who have contributed to the street map

# In[5]:

def process_map_users(filename):
    users = set()
    for _, element in ET.iterparse(filename):
        for e in element:
            if 'uid' in e.attrib:
                users.add(e.attrib['uid'])

    return users


users = process_map_users(OSM_FILE)
len(users)


# ## Auditing Street Names

# The first step is to create a set of expected values for the street names. The next function is a regex to match the last token in a string optionally ending with a period

# In[6]:

street_type_reg = re.compile(r'\b\S+\.?$', re.IGNORECASE)

expected_street_types = ["Avenue", "Boulevard", "Commons", "Court",
                         "Drive","Lane", "Parkway", "Place", "Road",
                         "Square", "Street", "Trail", "Way", "Vista",
                         "Terrace","Trace","Valley", "View", "Walk",
                         "Run","Ridge","Row","Point","Plaza","Path",
                         "Pass","Park","Overlook","Meadows","Loop",
                         "Hollow","Hill","Highway","Expressway","Cove",
                         "Crossing","Creek","Circle","Canyon","Bend"]


# The next function: audit_street_type will search for the above regex , If there is a match and it's not in our list of expected street types, it will add the street_name to the street_type dictionary.

# In[7]:

def audit_street_type(street_types, street_name,
                      regex, expected_street_types):
    m = regex.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected_street_types:
            street_types[street_type].add(street_name)


# The function is_street_name determines if an element contains an attribute k="addr:street" and returns it

# In[8]:

def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")


# Finally, an audit function to iterate over way and node tags to print out all the various street types found in the data set

# In[9]:

def audit(osmfile, regex):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)

    # iteratively parse the mapping xml
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        # iterate 'tag' tags within 'node' and 'way' tags
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'],
                                      regex, expected_street_types)

    return street_types


# Let us print some of the street types now using pprint and depth=5 as it is a very long list

# In[10]:

street_types = audit(OSM_FILE, street_type_reg)
pprint.pprint(dict(street_types), depth = 10)


# ## Problems in Data Set

# 1) First Problem I noticed is abbreviated street types ex St for Street, Ct for Court, Ave for Avenue etc. Next function will be for mapping these to their unabbreviated form so they are consistent and standardized, I will also standardize N,E,W,S to North, East, West, South

# In[11]:

def update(name, mapping): 
    words = name.split()
    for w in range(len(words)):
        if words[w] in mapping:
            if words[w].lower() not in ['suite', 'ste.', 'ste']: 
                # For example, don't update 'Suite E' to 'Suite East'
                words[w] = mapping[words[w]] 
                name = " ".join(words)
    return name


# In[12]:

street_type_mapping = {'Ave':'Avenue','Ave.':'Avenue','Avene':'Avenue',
                       'Blvd' : 'Boulevard','Blvd.' : 'Boulevard',
                       'Cv' : 'Cove',
                       'Dr'   : 'Drive','Dr.' : 'Drive', 
                       'hwy':'Highway','Hwy':'Highway','HWY':'Highway',
                       'Ln' : 'Lane',
                       'Pkwy' : 'Parkway',
                       'Rd'   : 'Road',
                       'St':'Street','St.':'Street','street':'Street',
                       'Ovlk' : 'Overlook',
                       'way': 'Way',
                       'N' : 'North','N.': 'North',
                       'S' : 'South','S.': 'South',
                       'E' : 'East','E.': 'East',
                       'W': 'West','W.': 'West',
                       'IH35':'Interstate Highway 35',
                       'IH 35':'Interstate Highway 35',
                       'I 35':'Interstate Highway 35',
                       'I-35':'Interstate Highway 35'}


# let us search street types again and replace abbreviations with full standardized street types

# In[13]:

for street_type, ways in street_types.iteritems():
    for name in ways:
        better_name = update(name, street_type_mapping)
        print name, "=>", better_name


# As seen above the mapping has been applied correctly to give full forms for cardinal directions and Ln, Dr, etc. Also updated IH-35/I-35 etc to 'Interstate Highway 35'(major highway in austin connecting San Antonio and Dallas)

# 2) For Postal Codes I used a similar approach as in the Street Name Cleaning. I converted them to standard 5 digit postal codes

# In[14]:

zip_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
zip_types = defaultdict(set)
expected_zip = ["73301","73344","76574","78602","78610","78612",
                "78613","78615","78616","78617","78619","78620",
                "78621","78626","78628","78634","78640","78641",
                "78642","78644","78645","78646","78652","78653",
                "78654","78656","78660","78663","78664","78665",
                "78666","78669","78676","78680","78681","78682",
                "78691","78701","78702","78703","78704","78705",
                "78712","78717","78719","78721","78722","78723",
                "78724","78725","78726","78727","78728","78729",
                "78730","78731","78732","78733","78734","78735",
                "78736","78737","78738","78739","78741","78742",
                "78744","78745","78746","78747","78748","78749",
                "78750","78751","78752","78753","78754","78756",
                "78757","78758","78759","78957"]
def audit_zip_codes(zip_types, zip_name, regex, expected_zip):
    m = regex.search(zip_name)
    if m:
        zip_type = m.group()
        if zip_type not in expected_zip:
             zip_types[zip_type].add(zip_name)
def is_zip_name(elem):
    return (elem.attrib['k'] == "addr:postcode")
def audit(filename, regex):
    for event, elem in ET.iterparse(filename, events=("start",)):
        if elem.tag == "way" or elem.tag == "node":
            for tag in elem.iter("tag"):
                if is_zip_name(tag):
                    audit_zip_codes(zip_types, tag.attrib['v'], 
                                    regex, expected_zip)
    return zip_types


# In[15]:

audit(OSM_FILE, zip_type_re)
pprint.pprint(dict(zip_types))


# To standardize the zipcodes, I will keep the first 5 digits in the postal code and drop the digits after the hyphen.

# In[16]:

def update_zip(postcode):
    return postcode.split("-")[0]


# In[18]:

for zip_type, ways in zip_types.iteritems():
    for postal in ways:
        better_zip = update_zip(postal)
        print postal, "=>", better_zip


# ## Preparing for Mongo DB

# In[19]:

from datetime import datetime as dt

CREATED = ["version", "changeset", "timestamp", "user", "uid"]

def shape_element(element):
    node = {}    
    if element.tag == "node" or element.tag == "way" :
        node['type'] = element.tag

        # Parse attributes
        for attrib in element.attrib:

            # Data creation details
            if attrib in CREATED:
                if 'created' not in node:
                    node['created'] = {}
                if attrib == 'timestamp':
                    node['created'][attrib] = dt.strptime(element.attrib[attrib], 
                                                                '%Y-%m-%dT%H:%M:%SZ')
                else:
                    node['created'][attrib] = element.get(attrib)

            # Parse location
            if attrib in ['lat', 'lon']:
                lat = float(element.attrib.get('lat'))
                lon = float(element.attrib.get('lon'))
                node['pos'] = [lat, lon]

            # Parse the rest of attributes
            else:
                node[attrib] = element.attrib.get(attrib)

        # Process tags
        for tag in element.iter('tag'):
            key   = tag.attrib['k']
            value = tag.attrib['v']
            if not problemchars.search(key):

                # Tags with single colon and beginning with addr
                if lower_colon.search(key) and key.find('addr') == 0:
                    if 'address' not in node:
                        node['address'] = {}
                    sub_attr = key.split(':')[1]
                    if is_street_name(tag):
                        # Do some cleaning
                        better_name = update(tag.attrib['v'],
                        street_type_mapping)
                        node['address'][sub_attr] = better_name
                    if key == 'postcode' or key == 'addr:postcode':
                        node['address'][sub_attr]=update_zip(tag.attrib['v'])
                    else:    
                        node['address'][sub_attr] = value
                

                # All other tags that don't begin with "addr"
                elif not key.find('addr') == 0:
                    if key not in node:
                        node[key] = value
                else:
                    node["tag:" + key] = value

        # Process nodes
        for nd in element.iter('nd'):
            if 'node_refs' not in node:
                node['node_refs'] = []
            node['node_refs'].append(nd.attrib['ref'])

        return node
    else:
        return None


# #### Write JSON file

# In[21]:

lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

import json
from bson import json_util

def process_map(file_in, pretty = False):
    file_out = "{0}.json".format(file_in)    
    with open(file_out, "wb") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                if pretty:
                    fo.write(json.dumps(el, indent=2,
                                        default=json_util.default)+"\n")
                else:
                    fo.write(json.dumps(el,default=json_util.default)+"\n")

process_map(OSM_FILE)


# ## Overview of the Data

# In[22]:

import os
print 'The downloaded file is {} MB'.format(os.path.getsize(OSM_FILE)
                                            /1.0e6) 
# convert from bytes to megabytes


# In[23]:

print 'The json file is {} MB'.format(os.path.getsize(OSM_FILE + ".json")
                                      /1.0e6) 
# convert from bytes to megabytes


# #### Number of Street Addresses

# In[24]:

osm_file = open(OSM_FILE, "r")
address_count = 0

for event, elem in ET.iterparse(osm_file, events=("start",)):
    if elem.tag == "node" or elem.tag == "way":
        for tag in elem.iter("tag"): 
            if is_street_name(tag):
                address_count += 1

address_count


# ## Working with MongoDB

# In[25]:

import signal
import subprocess

# The os.setsid() is passed in the argument preexec_fn so
# it's run after the fork() and before  exec() to run the shell.
pro = subprocess.Popen('mongod', preexec_fn = os.setsid)


# #### Connect to database with PyMongo

# In[26]:

from pymongo import MongoClient

db_name = 'openstreetmap'

# Connect to Mongo DB
client = MongoClient('localhost:27017')
# Database 'openstreetmap' will be created if it does not exist.
db = client[db_name]


# #### Import data set

# In[32]:

# Build mongoimport command
collection = OSM_FILE[:OSM_FILE.find('.')]
working_directory = '/Users/tarunparmar/Nonu/'
json_file = OSM_FILE + '.json'

mongoimport_cmd = 'mongoimport -h 127.0.0.1:27017 ' +                   '--db ' + db_name +                   ' --collection ' + collection +                   ' --file ' + working_directory + json_file

# Before importing, drop collection if it exists (i.e. a re-run)
if collection in db.collection_names():
    print 'Dropping collection: ' + collection
    db[collection].drop()

# Execute the command
print 'Executing: ' + mongoimport_cmd
subprocess.call(mongoimport_cmd.split())


# ## Investigating the Data

# In[33]:

austin_texas = db[collection]


# In[34]:

austin_texas


# #### Number of Documents

# In[35]:

austin_texas.find().count()


# #### Number of Unique Users

# In[36]:

len(austin_texas.distinct('created.user'))


# 1249 vs 1260 users we began with, probably due to loss of data in shape_element function

# #### Number of Nodes and Ways

# In[37]:

db.austin_texas.find( {"type":"node"} ).count()


# In[38]:

db.austin_texas.find( {"type":"way"} ).count()


# #### Top 5 Contributors

# In[39]:

pipeline = [{'$group': {'_id': '$created.user','count': {'$sum' : 1}}},{'$sort': {'count' : -1}},{'$limit': 5}]

def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)


# atx buildings works on tracking and documenting the community effort to import the 2013 building footprints and address points datasets from the City of Austin Data Portal. Andy Wilson(wilsaj_atxbuildings), 
# John Clary(johnclary_atxbuildings), James Seppi(jseppi_atxbuildings), Chris Martin(ccjjmartin_atxbuildings), Kelvin Thompson(kkt_atxbuildings), Jonathan Pa(jonathan pa_atxbuildings) and Pati Silva(patisilva_atxbuildings) are all participants of this project. 

# #### Number of users appearing only once

# In[40]:

pipeline = [{"$group":{"_id":"$created.user", "count":{"$sum":1}}}, {"$group":{"_id":"$count", "num_users":{"$sum":1}}}, {"$sort":{"_id":1}}, {"$limit":1}]

def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)


# #### Postal Codes

# In[41]:

pipeline =[{'$match': {'address.postcode': {'$exists': 1}}},{'$group': {'_id': '$address.postcode','count': {'$sum': 1}}}, {'$sort': {'count': -1}},{'$limit': 10}]
def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)


# Most of the postal codes have been cleaned up by our script

# In[42]:

pipeline =[{'$match': {'address.street': {'$exists': 1}}},{'$group': {'_id': '$address.street','count': {'$sum': 1}}}, {'$sort': {'count': -1}},{'$limit': 10}]
def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)


# Most of the street names have been cleaned up by our script

# #### Cities in the dataset

# In[43]:

pipeline =[{"$group":{"_id":"$address.city", "count":{"$sum":1}}}, {"$sort":{"count": -1}},{'$limit': 10}]
def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)


# A lot of addresses had 'None' in their city name. 
# 
# Other than Austin, TX, the map includes the neighboring areas like Kyle, Buda, Round Rock etc.

# ## Additional data exploration using MongoDB queries

# #### Top Amenities

# In[44]:

pipeline = [{"$group":{"_id":"$amenity", "count":{"$sum":1}}}, {"$sort":{"count": -1}},{'$limit': 10}]
def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)


# Top Amenities are Parking, Restaurants and Waste Baskets

# #### Top Religion

# In[45]:

pipeline = [{"$match":{"amenity":{"$exists":1}, "amenity":"place_of_worship"}},{"$group":{"_id":"$religion", "count":{"$sum":1}}},{"$sort":{"count":-1}}, {"$limit":5}]
def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)


# Top Religion is 'Christianity' with 465 places of worship

# #### Top Restaurants

# In[46]:

pipeline =[{'$match': {'amenity': 'restaurant'}},{'$group': {'_id': '$name','count': {'$sum': 1}}},{'$sort': {'count': -1}},{'$limit': 10}]
def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)


# #### Popular Cuisine

# In[47]:

pipeline = [{"$match":{"amenity":{"$exists":1}, "amenity":"restaurant"}}, {"$group":{"_id":"$cuisine", "count":{"$sum":1}}},{"$sort":{"count":-1}}, {"$limit":5}]
def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)


# Popular cuisines include Mexican, American and Pizza- no surprise there 

# ## Other ideas about the dataset

# As seen above atx-buildings has worked on mapping and loading of most of the addresses for austin osm. Their wiki page is http://wiki.openstreetmap.org/wiki/Austin,_TX/Buildings_Import and github repo is https://github.com/atx-osg/atx-buildings. Their scripts have jsons for converting and cleaning up of street addresses and zipcodes. Since the team standardized the data loading, our dataset was pretty clean to begin with. If we have similar structured data loading with a few rules and clean up scripts, then osm data would become robust. The problem with this however is that too many rules/madatory fields could deter users from contributing more. As an incentive, osm page should display top individual contributors and teams who are working on loading and cleaning of data. 
# 
# Another suggestion would be to indicate areas on the map that have less or incomplete data so that contributors can focus on that region to make the map more complete. There is a lot of missing data for 'city' field in addresses. Using Geopy package, some of the missing information can be filled in.

# ## Conclusion

# After the review of Austin's OSM data, although incomplete, I believe it has been cleaned well for the purposes of this exercise. The scripts developed during this project was successful in parsing and cleaning most of the data.
