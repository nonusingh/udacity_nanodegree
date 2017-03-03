
# Wrangling Open Street Map data with MongoDB

## Map Area
#### Austin, TX, United States
https://mapzen.com/data/metro-extracts/metro/austin_texas/

https://www.openstreetmap.org/relation/113314

Austin is where I did my first internship so it is special to me. I am also familiar with the street names so I will be able to audit it better. I downloaded osm file from mapzen.com which consisted of data from the shaded area in the map below. It is over 1.4 GB(uncompressed)

<img src = "https://github.com/nonusingh/udacity_nanodegree/blob/master/OpenStreetMap/Austin_OSM/img/SizeM.png">

## Auditing the data

Due to the huge size of the data, I will load a smaller section of data as a sample. 


```python
import xml.etree.ElementTree as ET
import pprint
from collections import defaultdict
import re
```


```python
OSM_FILE = "austin_texas.osm"
SAMPLE_FILE = "sample.osm"
```


```python
k = 10

def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag Reference: http://stackoverflow.com/questions/3095434/inserting-newlines-in-xml-file-generated-via-xml-etree-elementtree-in-python
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
```

After loading the sample data, lets parse one tag at a time with ElementTree and count the number of top level tags. Iterative parsing is utilized for this as data is too large to process on the complete document


```python
def count_tags(filename):
    """count tags in filename.
    
    Init 1 in dict if the key not exist, increment otherwise."""
    tags = {}
    for ev,elem in ET.iterparse(filename):
        tag = elem.tag
        if tag not in tags.keys():
            tags[tag] = 1
        else:
            tags[tag]+=1
    return tags
tags = count_tags(OSM_FILE) 
pprint.pprint(tags)
```

    {'bounds': 1,
     'member': 20369,
     'nd': 7020265,
     'node': 6386286,
     'osm': 1,
     'relation': 2396,
     'tag': 2387514,
     'way': 669483}


Next, Let us explore the data some more to check for potential problems in the data. I have created regular expressions to check for certain patterns in the tag "k=addr:", the function 'key_type' will count of each of the four tag categories in a dictionary:
  "lower", for tags that contain only lowercase letters and are valid,
  "lower_colon", for otherwise valid tags with a colon in their names,
  "problemchars", for tags with problematic characters, and
  "other", for other tags that do not fall into the other three categories.


```python
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
```

    {'lower': 1307962, 'lower_colon': 1067521, 'other': 12030, 'problemchars': 1}


Next, let's now find out how many unique users have contributed to the map in this osm, following code gives us 1260 different unique users who have contributed to the street map


```python
def process_map_users(filename):
    users = set()
    for _, element in ET.iterparse(filename):
        for e in element:
            if 'uid' in e.attrib:
                users.add(e.attrib['uid'])

    return users

users = process_map_users(OSM_FILE)
len(users)
```




    1260



## Auditing Street Names

The first step is to create a set of expected values for the street names. The next function is a regex to match the last token in a string optionally ending with a period


```python
street_type_reg = re.compile(r'\b\S+\.?$', re.IGNORECASE)

expected_street_types = ["Avenue", "Boulevard", "Commons", "Court", "Drive", "Lane", "Parkway", "Place", "Road", 
                        "Square", "Street", "Trail", "Way", "Vista", "Terrace","Trace","Valley", "View", "Walk","Run",
                        "Ridge","Row","Point","Plaza","Path","Pass","Park","Overlook","Meadows","Loop","Hollow",
                        "Hill","Highway","Expressway","Cove","Crossing","Creek","Circle","Canyon","Bend"]
```

The next function: audit_street_type will search for the above regex , If there is a match and it's not in our list of expected street types, it will add the street_name to the street_type dictionary.


```python
def audit_street_type(street_types, street_name, regex, expected_street_types):
    m = regex.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected_street_types:
            street_types[street_type].add(street_name)
```

The function is_street_name determines if an element contains an attribute k="addr:street" and returns it


```python
def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")
```

Finally, an audit function to iterate over way and node tags to print out all the various street types found in the data set


```python
def audit(osmfile, regex):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)

    # iteratively parse the mapping xml
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        # iterate 'tag' tags within 'node' and 'way' tags
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'], regex, expected_street_types)

    return street_types
```


```python
street_types = audit(OSM_FILE, street_type_reg)
pprint.pprint(dict(street_types))
```

    {'100': set(['Avery Ranch Blvd Building A #100',
                 'Jollyville Road Suite 100',
                 'Old Jollyville Road, Suite 100',
                 'RM 2222 Unit #100']),
     '101': set(['4207 James Casey st #101']),
     '104': set(['11410 Century Oaks Terrace Suite #104', 'S 1st St, Suite 104']),
     '1100': set(['Farm-to-Market Road 1100']),
     '117': set(['County Road 117']),
     '12': set(['Ranch to Market Road 12']),
     '120': set(['Building B Suite 120']),
     '129': set(['County Road 129']),
     '130': set(['Highway 130']),
     '1327': set(['FM 1327', 'Farm-to-Market Road 1327']),
     '138': set(['County Road 138']),
     '140': set(['S IH 35 Frontage Rd #140']),
     '1431': set(['Farm-to-Market Road 1431', 'Old Farm-to-Market 1431']),
     '150': set(['Farm-to-Market Road 150',
                 'IH-35 South, #150',
                 'Metric Boulevard #150',
                 'Ranch-to-Market Road 150']),
     '1625': set(['Farm-to-Market Road 1625']),
     '1626': set(['F.M. 1626', 'FM 1626', 'Farm-to-Market Road 1626']),
     '163': set(['Bee Cave Road Suite 163']),
     '170': set(['County Road 170']),
     '1805': set(['N Interstate 35, Suite 1805']),
     '1825': set(['FM 1825']),
     '1826': set(['Farm To Market Road 1826', 'Ranch to Market Road 1826']),
     '183': set(['Highway 183',
                 'N HWY 183',
                 'U.S. 183',
                 'US 183',
                 'US Highway 183',
                 'United States Highway 183']),
     '1869': set(['Ranch-to-Market Road 1869']),
     '2': set(['6800 Burnet Rd #2']),
     '200N': set(['Burnet Road #200N']),
     '203': set(['West Ben White Boulevard #203',
                 'West Ben White Boulevard, #203']),
     '213': set(['Executive Center Drive Suite 213']),
     '2222': set(['Ranch to Market Road 2222']),
     '2243': set(['Old FM 2243']),
     '2244': set(['RM 2244']),
     '260': set(['S Interstate 35, #260']),
     '2769': set(['Farm-to-Market Road 2769']),
     '280': set(['County Road 280']),
     '290': set(['C R 290',
                 'County Road 290',
                 'E Hwy 290',
                 'East Highway 290',
                 'East Hwy 290',
                 'Helios Way, Bldg 2, Suite 290',
                 'Highway 290',
                 'U.S. 290',
                 'US 290',
                 'US Highway 290',
                 'W HWY 290',
                 'W Hwy 290',
                 'W. Highway 290',
                 'West Highway 290',
                 'West US Highway 290']),
     '298': set(['N I-35 Suite 298']),
     '3': set(['Shoal Creek Blvd, Bld 3']),
     '300': set(['321 W Ben White Blvd #300', 'West 5th Street #300']),
     '3000a': set(['Research Blvd #3000a']),
     '301': set(['Hwy 290 W. Ste. 301']),
     '306': set(['Meadows Dr #306']),
     '311': set(['US 183 #311']),
     '3177': set(['FM 3177']),
     '320': set(['W. University Avenue,Ste 320']),
     '35': set(['9600 S IH 35',
                'Highway Interstate 35',
                'I 35',
                'Interstate 35',
                'Interstate Highway 35',
                'N Interstate Highway 35',
                'N. IH 35',
                'North IH 35',
                'North Interstate Highway 35',
                'S Interstate 35',
                'S Interstate Highway 35',
                'South I 35',
                'South Interstate 35']),
     '4': set(['4201 South Congress Avenue #4']),
     '400': set(['North Lakeline Boulevard, Ste. 400']),
     '406': set(['North Highway 183 #406']),
     '414': set(['County Road 414']),
     '425': set(['North MoPac Expressway #425']),
     '45': set(['TX 45']),
     '452': set(['Country Rd. 452']),
     '459': set(['County Road 459']),
     '5.700': set(['East 23rd Street, North End Zone, Suite 5.700']),
     '535': set(['FM 535']),
     '6': set(['N IH 35 Bldg. 6']),
     '600': set(['Burnet Road #600']),
     '608': set(['Burnet Rd #608']),
     '619': set(['FM 619']),
     '620': set(['FM 620',
                 'N FM 620',
                 'RM 620',
                 'RR 620',
                 'Ranch Road 620',
                 'Ranch-to-Market Road 620']),
     '685': set(['FM 685', 'Farm to Market 685']),
     '7': set(['N I H 35 Bldg 7']),
     '71': set(['Hwy 71',
                'TX 71',
                'US 290;HWY 71',
                'W Hwy 71',
                'West Highway 71']),
     '8': set(['Arterial 8', 'Burnet Road #8']),
     '812': set(['Farm-to-Market Road 812']),
     '969': set(['FM 969']),
     '973': set(['FM 973',
                 'Farm-to-Market Road 973',
                 'N Farm-To-Market Road 973']),
     'A': set(['Avenue A']),
     'A-15': set(['W. Anderson Lane, Suite A-15']),
     'A500': set(['Burnet Rd Ste, A500']),
     'Acres': set(['Green Acres']),
     'Adventurer': set(['Adventurer']),
     'Affirmed': set(['Affirmed']),
     'Alley': set(['Oak Alley']),
     'Alps': set(['Julian Alps']),
     'Alto': set(['Camino Alto', 'Palo Alto']),
     'Amistad': set(['Circulo de Amistad']),
     'Apache': set(['Apache']),
     'Arbolago': set(['Camino Arbolago']),
     'Arrow': set(['Broken Arrow']),
     'Atlantic': set(['Atlantic']),
     'Austin': set(['Research Blvd, Austin']),
     'Ave': set(['Barstow Ave',
                 'E. University Ave',
                 'Round Rock Ave',
                 'S Congress Ave',
                 'South Congress Ave']),
     'Ave.': set(['Woodrow Ave.']),
     'Avene': set(['South Congress Avene']),
     'B': set(['Avenue B', 'South Interstate 35, Suite B']),
     'B100': set(['North Lamar Boulevard suite #B100']),
     'Barrhead': set(['Barrhead']),
     'Birch': set(['River Birch']),
     'Blackfoot': set(['Blackfoot']),
     'Bluff': set(["Bubba's Bluff",
                   'Bullick Bluff',
                   'Crescent Bluff',
                   'Scout Bluff',
                   'Travis Bluff']),
     'Blvd': set(['10000 Research Blvd',
                  'Airport Blvd',
                  'E Palm Valley Blvd',
                  'Escarpment Blvd',
                  'Industrial Blvd',
                  'Industrial Oaks Blvd',
                  'N Bell Blvd',
                  'N. Lamar Blvd',
                  'North Lamar Blvd',
                  'North Research Blvd',
                  'Research Blvd',
                  'South Bell Blvd',
                  'South Lamar Blvd',
                  'Stonelake Blvd',
                  'Swenson Farms Blvd',
                  'West Louis Henna Blvd']),
     'Blvd.': set(['East Old Settlers Blvd.',
                   'Research Blvd.',
                   'South Exposition Blvd.',
                   'South Lamar Blvd.',
                   'Tandem Blvd.',
                   'W North Loop Blvd.']),
     'Boggy': set(['Big Boggy']),
     'Bonanza': set(['Bonanza']),
     'Bonita': set(['Sendera Bonita']),
     'Bottom': set(['Creek Bottom']),
     'Branch': set(['Malaquita Branch', 'Spring Branch']),
     'Bridge': set(['Knights Bridge']),
     'Buckskin': set(['Buckskin']),
     'C': set(['Avenue C']),
     'C-200': set(['9600 IH 35 C-200']),
     'C1-100': set(['Hill Country Blvd., Suite C1-100']),
     'Caliche': set(['Calle Caliche']),
     'Calle': set(['Medio Calle']),
     'Camelback': set(['Camelback']),
     'Camino': set(['El Viejo Camino']),
     'Cannon': set(['West William Cannon']),
     'Cantera': set(['La Cantera']),
     'Canterwood': set(['Canterwood']),
     'Capri': set(['Capri']),
     'Carrara': set(['Carrara']),
     'Casitas': set(['Casitas']),
     'Castle': set(['Caisteal Castle']),
     'CastlePath': set(['Raglan CastlePath']),
     'Catcher': set(['Dream Catcher']),
     'Catorce': set(['Real Catorce']),
     'Cave': set(['Wind Cave']),
     'Cc': set(['Misty Heights Cc']),
     'Challenger': set(['Challenger']),
     'Chase': set(['Glen Rose Chase',
                   'Mustang Chase',
                   'Pecan Chase',
                   'Pony Chase',
                   'Shetland Chase']),
     'Chavez': set(['West Cesar Chavez']),
     'Clark': set(['Lake Clark']),
     'Claro': set(['Arroyo Claro']),
     'Claw': set(['Bear Claw']),
     'Clearwater': set(['Clearwater']),
     'Cliff': set(['Eagle Cliff', 'Gila Cliff']),
     'Cobblestone': set(['Cobblestone']),
     'Colorado': set(['Sierra Colorado']),
     'Comanche': set(['Comanche']),
     'Comet': set(['Comet']),
     'Corners': set(['Chimney Corners']),
     'Corral': set(['O K Corral', 'Shepherds Corral']),
     'Corta': set(['Vista Corta']),
     'Costa': set(['Camino La Costa', 'La Costa']),
     'Crescent': set(['Margranita Crescent', 'Scott Crescent']),
     'Crest': set(['Meadow Crest']),
     'Crestmont': set(['Crestmont']),
     'Criswell': set(['Criswell']),
     'Ct': set(['Claro Vista Ct',
                'Costello Ct',
                'Ely Ct',
                'Krupa Ct',
                'Sterling Heights Ct',
                'Stirling Castle Ct',
                'Sweetgum Ct']),
     'Cutoff': set(['Ferguson Cutoff', 'West 35th Street Cutoff']),
     'Cv': set(['Arbole Cv',
                'Blue Sky Cv',
                'Clear Pond Cv',
                'Copper Point Cv',
                'Enchanted Cv',
                'Hal Sutton Cv',
                'Hilltop Canyon Cv',
                'La Estrella Cv',
                'La Roca Cv',
                'Lapin Cv',
                'Mallard Cv',
                'Mock Cherry Cv',
                'Morning Primrose Cv',
                'Old Corral Cv',
                'Peat Moors Cv',
                'Quiet Meadows Cv',
                'Red River Cv',
                'Ripley Castle Cv',
                'Rooney Cv',
                'Salem Oak Cv',
                'Sandy Creek Cv',
                'Secluded Willow Cv',
                'Texas Ash Cv',
                'Tom Kite Cv']),
     'D': set(['Avenue D']),
     'D1': set(['W Hwy 71, STE D1']),
     'D5000': set(['Speedway Stop D5000']),
     'Dale': set(['Michael Dale']),
     'Dalmahoy': set(['Dalmahoy']),
     'Dance': set(['Harvest Dance']),
     'Dancer': set(['Wolf Dancer']),
     'Divide': set(['Vail Divide']),
     'Dog': set(['Laughing Dog']),
     'Dorado': set(['El Dorado', 'North el Dorado', 'South el Dorado']),
     'Dr': set(['Bettis Trophy Dr',
                'Bill Baker Dr',
                'Canyon Springs Dr',
                'Carranzo Dr',
                'Corral de Tierra Dr',
                'Creekline Dr',
                'Dave Silk Dr',
                'Executive Center Dr',
                'Forest Creek Dr',
                'Horse Wagon Dr',
                'Ivy Dr',
                'Jack Nicklaus Dr',
                'Jimmy Clay Dr',
                'Justin Leonard Dr',
                'Kyle Center Dr',
                'Lighthouse Landing Dr',
                'Mineral Dr',
                'Octavia Dr',
                'Rain Song Dr',
                'Round Rock West Dr',
                "St Mary's Dr",
                'Via Dono Dr',
                'Via Ricco Dr',
                'W Lake Dr',
                'W William Cannon Dr',
                'Walter Seaholm Dr',
                'Winged Elm Dr',
                'Woodall Dr',
                'Yaupon Range Dr']),
     'Dr.': set(['11928 Stonehollow Dr.',
                 'Cannon Dr.',
                 'Sportsplex Dr.',
                 'Stonebridge Dr.']),
     'Dragon': set(['Dragon']),
     'Drive/Rd': set(['Spreading Oaks Drive/Rd']),
     'Dublin': set(['Royal Dublin']),
     'Dunes': set(['Indiana Dunes']),
     'E': set(['Beardsley Lane Bldg E']),
     'East': set(['Alpine Road East',
                  'Applegate Drive East',
                  'Basin Ledge East',
                  'Black Locust Drive East',
                  'Brenham Street East',
                  'Caddo Street East',
                  'Canyon Circle East',
                  'Colorado Drive East',
                  'Covington Drive East',
                  'Cypress Point East',
                  'Hwy 290 East',
                  'Ledgeway East',
                  'Main Street East',
                  'Mockingbird Lane East',
                  'Rapid Springs Cove East',
                  'Rutland Village East',
                  'US 290 East',
                  'Walnut Street East']),
     'Edenderry': set(['Edenderry']),
     'End': set(['The Living End']),
     'Estates': set(['Hidden Estates']),
     'Explorer': set(['Explorer']),
     'F': set(['Avenue F']),
     'F-4': set(['2901 Capital of Texas Hwy Suites F-4',
                 'S. Capitol of Texas Hwy, #F-4']),
     'FM1431': set(['FM1431']),
     'Fairway': set(['Fuzz Fairway']),
     'Falcon': set(['Falcon']),
     'Fandango': set(['Fandango']),
     'Fields': set(['Elysian Fields']),
     'Firebird': set(['Firebird']),
     'Flat': set(['Tortilla Flat']),
     'Fleur': set(['Rue Le Fleur']),
     'Flower': set(['Desert Flower']),
     'Folkway': set(['Kerrville Folkway']),
     'Ford': set(['Meadow Ford']),
     'Forest': set(['Sherwood Forest']),
     'Fork': set(['Roaring Fork']),
     'Fort': set(['Quick Fort']),
     'Fortuna': set(['Via Fortuna']),
     'Frijolita': set(['Frijolita']),
     'Frontage': set(['I-35 Frontage']),
     'G': set(['Avenue G']),
     'G-145': set(['E. Whitestone Blvd #G-145']),
     'Galaxy': set(['Galaxy']),
     'Gallop': set(['Victory Gallop']),
     'Gap': set(['Buffalo Gap', 'Gnu Gap']),
     'Garden': set(['Bayswater Garden']),
     'Germaine': set(['Rue de St Germaine']),
     'Glade': set(['Sylvan Glade']),
     'Glen': set(['Cedar Glen',
                  'Hunters Glen',
                  'Jacob Glen',
                  'Oak Glen',
                  'Welcome Glen',
                  'Willheather Glen']),
     'Gonzales': set(['Gonzales']),
     'Grande': set(['Laguna Grande', 'Mesa Grande', 'Rio Grande']),
     'Green': set(['Palace Green', 'Saint Georges Green']),
     'Greens': set(['Inland Greens']),
     'Greenway': set(['Greenway']),
     'Grotto': set(['Liberty Grotto']),
     'Grove': set(['China Grove']),
     'Gulch': set(['Bachelor Gulch', 'Grubstake Gulch', 'Thunder Gulch']),
     'Gunsmoke': set(['Gunsmoke']),
     'H': set(['Avenue H']),
     'Hall': set(['Panther Hall']),
     'Hambletonian': set(['Hambletonian']),
     'Harborway': set(['Palm Harborway']),
     'Hat': set(['Medicine Hat']),
     'Haven': set(['Circle Haven', 'Troll Haven']),
     'Highlander': set(['Highlander']),
     'Hilldale': set(['Hilldale']),
     'Horn': set(['Big Horn']),
     'Horse': set(['High Horse']),
     'Hwy': set(['S Capital of Texas Hwy']),
     'I': set(['Avenue I']),
     'I35': set(['I35']),
     'IH-35': set(['N IH-35', 'South IH-35']),
     'IH35': set(['1500 S. IH35']),
     'IH35,': set(['N. IH35,']),
     'Iron': set(['Branding Iron']),
     'Island': set(['Channel Island']),
     'J': set(['Business Interstate Highway 35 J']),
     'Jacinto': set(['San Jacinto']),
     'James': set(['Court of Saint James']),
     'Jr': set(['Robert Martinez Jr']),
     'Juniper': set(['Brown Juniper']),
     'K': set(['Avenue K']),
     'Kiss': set(['Sky Kiss']),
     'Knoll': set(['Chamois Knoll', 'Country Knoll']),
     'L2': set(['Research Blvd #L2']),
     'Lair': set(['Lions Lair']),
     'Lajitas': set(['Lajitas']),
     'Lake': set(['Buffalo Lake', 'Crater Lake', 'Plaza on the Lake']),
     'Lancaster': set(['House of Lancaster']),
     'Landing': set(['Longhorn Landing', 'Richfield Landing']),
     'Lanes': set(['Green Lanes']),
     'Ledge': set(['Basin Ledge', 'Warbler Ledge']),
     'Leon': set(['Sierra Leon']),
     'Liberty': set(['W. Liberty']),
     'Lido': set(['Lido']),
     'Limon': set(['Calle Limon']),
     'Linda': set(['Loma Linda']),
     'Ln': set(['Buzz Schneider Ln',
                'Calhoun Ln',
                'Chick Pea Ln',
                'Hidden Hills Ln',
                'Laguna Seca Ln',
                'Lantana Ln',
                'Pasadera Ln',
                'Pfennig Ln',
                'Rockwood Ln',
                'Rocky Top Ln',
                'Sky Ridge Ln',
                'W Anderson Ln',
                'W Braker Ln',
                'West Parmer Ln']),
     'Lodge': set(['Wild Basin Lodge']),
     'Lonesome': set(['High Lonesome']),
     'Madre': set(['Sierra Madre']),
     'Malabar': set(['Malabar']),
     'Mallow': set(['Poppy Mallow']),
     'Maple': set(['Canyon Maple']),
     'Mariner': set(['Mariner']),
     'Mas': set(['Una Mas']),
     'Maverick': set(['Maverick']),
     'Medalist': set(['Medalist']),
     'Media': set(['Via Media']),
     'Melody': set(['Melody']),
     'Meridian': set(['Greenwich Meridian']),
     'Merimac': set(['Merimac']),
     'Mesa': set(['Alta Mesa',
                  'Hidden Mesa',
                  'Lone Mesa',
                  'Mustang Mesa',
                  'Spicewood Mesa']),
     'Mirador': set(['Mirador']),
     'Mirage': set(['Rancho Mirage']),
     'Mist': set(['Lake Mist']),
     'Mohawk': set(['Mohawk']),
     'Montana': set(['Sierra Montana']),
     'Moor': set(['Chelsea Moor']),
     'Mountain': set(['Creek Mountain']),
     'Mustang': set(['Mustang']),
     'N': set(['Avenue N',
               'Capital of TX Hwy N',
               'Farm to Market 620 N',
               'IH 35 N']),
     'Navajo': set(['Navajo']),
     'Norte': set(['Ladera Norte', 'Montana Norte']),
     'North': set(['4th Street North',
                   '5th Street North',
                   'Ashwood North',
                   'Augusta Drive North',
                   'Chesapeake Bay Lane North',
                   'Cowal Drive North',
                   'Cuernavaca Drive North',
                   'Dunlap Road North',
                   'FM 620 North',
                   'Fresco Drive North',
                   'Hideaway North',
                   'Highway 95 North',
                   'Hillside North',
                   'IH 35 North',
                   'Interstate Highway 35 Service Road North',
                   'Kettleman Lane North',
                   'Lake Hills Drive North',
                   'Laurelwood Drive North',
                   'Lowell Lane North',
                   'Meadows Drive North',
                   'Pace Bend Road North',
                   'Ranch Road 620 North',
                   'Redondo Drive North',
                   'Sioux Trail North',
                   'State Highway 95 North',
                   'Summit Ridge Drive North',
                   'Tumbleweed Trail North',
                   'Ute Trail North',
                   'Venture Boulevard North',
                   'Weston Lane North']),
     'Northwest': set(['Carlos G Parker Boulevard Northwest']),
     'Oak': set(['Live Oak', 'Spanish Oak']),
     'Oaks': set(['Mesa Oaks', 'Sierra Oaks']),
     'Oltorf': set(['East Oltorf']),
     'Ovlk': set(['Royal Birkdale Ovlk']),
     'Pace': set(['Cane Pace']),
     'Pathway': set(['Happy Vale Pathway', 'Jigsaw Pathway', 'Pawnee Pathway']),
     'Pawnee': set(['Pawnee']),
     'Pflugerville': set(['N. IH 35 Pflugerville']),
     'Picadilly': set(['Picadilly']),
     'Pine': set(['Aleppo Pine']),
     'Pkwy': set(['Riata Trace Pkwy', 'Roger Hanks Pkwy', 'Soter Pkwy']),
     'Pl': set(['Bidens Pl', 'Veletta Pl']),
     'Pointe': set(['Royal Pointe']),
     'Porpoise': set(['Porpoise']),
     'Post': set(['Hitching Post']),
     'Print': set(['Paw Print']),
     'Ps': set(['Deer Shadow Ps']),
     'Quarry': set(['Quarry']),
     'RM1431': set(['RM1431']),
     'Race': set(['Buck Race']),
     'Range': set(['Rambling Range']),
     'Raphael': set(['Rue de St Raphael']),
     'Ravine': set(['Quail Ravine']),
     'Rd': set(['Barley Rd',
                'Barton Springs Rd',
                'Bee Creek Rd',
                'Big Meadow Rd',
                'Burnet Rd',
                'Commons Rd',
                'Moon Rock Rd',
                'N Interstate 35 Frontage Rd',
                'Palomino Ranch Rd',
                'Red Pebble Rd',
                'Skyline Rd',
                'Spicewood Springs Rd',
                'Tawny Farms Rd']),
     'Real': set(['Camino Real', 'El Camino Real']),
     'Reinhardt': set(['Edwin Reinhardt']),
     'River': set(['Red River']),
     'Rock': set(['Speaking Rock']),
     'Roost': set(['Pheasant Roost']),
     'Rope': set(['Running Rope']),
     'Rose': set(['Rock Rose']),
     'Royale': set(['Isle Royale']),
     'SB': set(['South I-35 Service SB']),
     'Saddles': set(['Twin Saddles']),
     'Sage': set(['Yellow Sage']),
     'Sandpiper': set(['Sandpiper']),
     'Season': set(['Wet Season']),
     'Seawind': set(['Seawind']),
     'Seco': set(['Arroyo Seco', 'Camino Seco', 'Rio Seco']),
     'Sidewinder': set(['Sidewinder']),
     'Silence': set(['Sunday Silence']),
     'Sioux': set(['Sioux']),
     'Sky': set(['Cantina Sky']),
     'Skyline': set(['Beverly Skyline', 'Hill Country Skyline']),
     'Skyview': set(['Deer Creek Skyview']),
     'Skyway': set(['Barton Skyway', 'Longhorn Skyway']),
     'Slew': set(['Seattle Slew']),
     'South': set(['Amberwood South',
                   'Farm-to-Market Road 973 South',
                   'Ranch Road 620 South',
                   'Sioux Trail South',
                   'US Highway 183 South',
                   'Venture Boulevard South',
                   'Whippoorwill Street South']),
     'Southview': set(['Southview']),
     'Speedway': set(['Speedway']),
     'Spicewood': set(['State Highway 71 W Spicewood']),
     'Spring': set(['Stillhouse Spring']),
     'Springwater': set(['Springwater']),
     'Spur': set(['Lohmans Spur', 'Rutledge Spur', 'Silver Spur']),
     'St': set(['Duval St',
                'E 43rd St',
                'E 51st St',
                'E 6th St',
                'E Oltorf St',
                'N Main St',
                'Pecan St',
                'Red River St',
                'Rio Grande St',
                'S 1st St',
                'W 10th St',
                'W 6th St',
                'W Annie St',
                'West Lynn St']),
     'St.': set(['E 38th 1/2 St.', 'E. 43rd St.', 'Pecan St.']),
     'Stakes': set(['Messenger Stakes']),
     'Stonebridge': set(['Stonebridge']),
     'Stonehedge': set(['Old Stonehedge']),
     'Strip': set(['Sunset Strip']),
     'Summit': set(['Indian Summit']),
     'Sundown': set(['Bold Sundown']),
     'Sunfish': set(['Sunfish']),
     'Sunterro': set(['Sunterro']),
     'Sutton': set(['Sutton']),
     'Tahoe': set(['Sierra Tahoe']),
     'Talamore': set(['Talamore']),
     'Tarlton': set(['Old Walsh Tarlton']),
     'Tealwood': set(['Tealwood']),
     'Terrance': set(['Holly Crest Terrance']),
     'Thunder': set(['Buffalo Thunder']),
     'Thunderbird': set(['Thunderbird']),
     'Tiempo': set(['Pasa Tiempo']),
     'Toro': set(['Paseo del Toro']),
     'Tr': set(['Posse Tr', 'Sunflower Tr', 'Sycamore Tr']),
     'Track': set(['Deer Track']),
     'Triangle': set(['Piland Triangle']),
     'Trl': set(['Harrier Flight Trl', 'Poppy Hills Trl', 'Scenic Overlook Trl']),
     'Tropez': set(['Rue de St Tropez']),
     'Tundra': set(['Buffalo Tundra']),
     'Turn': set(['Clubhouse Turn']),
     'Turnback': set(['Turnback']),
     'Vale': set(['East Meadow Vale']),
     'Van': set(['Clara Van']),
     'Vanguard': set(['Vanguard']),
     'Verde': set(['Casa Verde', 'Cuesta Verde', 'Encino Verde']),
     'Verdes': set(['Palos Verdes']),
     'Viejo': set(['Camino Viejo']),
     'Viento': set(['Lago Viento']),
     'Voyageurs': set(['Voyageurs']),
     'W': set(['Highway 71 W', 'Hwy 290 W']),
     'Welch': set(['Welch']),
     'West': set(['Alpine Road West',
                  'Carrie Manor Street West',
                  'Crystalbrook West',
                  'Old 2243 West',
                  'Pfluger Street West',
                  'Rutland Village West',
                  'Saint Elmo Road West',
                  'View West',
                  'Wagon Road West']),
     'Wheel': set(['Wagon Wheel']),
     'William': set(['Prince William']),
     'Willo': set(['Switch Willo']),
     'Withers': set(['Tall Withers']),
     'Wood': set(['Five Acre Wood']),
     'Woods': set(['Point O Woods', 'Trail of the Woods']),
     'Wow': set(['Pow Wow']),
     'Wren': set(['House Wren']),
     'Yard': set(['Scotland Yard']),
     'York': set(['House of York']),
     'court': set(['Fleming court']),
     'cove': set(['devonshire cove']),
     'lane': set(['brigadoon lane']),
     'pass': set(['Raven Caw pass']),
     'street': set(['East main street',
                    'South 1st street',
                    'White House street',
                    'south church street']),
     'suite#L131': set(['N. Lamar suite#L131']),
     'texas': set(['9901 N Capital Of texas']),
     'way': set(['Physicians way'])}


## Problems in Data Set

1) First Problem I noticed is abbreviated street types ex St for Street, Ct for Court, Ave for Avenue etc. Next function will be for mapping these to their unabbreviated form so they are consistent and standardized, I will also standardize N,E,W,S to North, East, West, South


```python
def update(name, mapping): 
    words = name.split()
    for w in range(len(words)):
        if words[w] in mapping:
            if words[w].lower() not in ['suite', 'ste.', 'ste']: 
                # For example, don't update 'Suite E' to 'Suite East'
                words[w] = mapping[words[w]] 
                name = " ".join(words)
    return name
```


```python
street_type_mapping = {'Ave'  : 'Avenue','Ave.' : 'Avenue','Avene' :'Avenue',
                       'Blvd' : 'Boulevard','Blvd.' : 'Boulevard',
                       'Cv' : 'Cove',
                       'Dr'   : 'Drive','Dr.' : 'Drive', 
                       'hwy' : 'Highway','Hwy' : 'Highway','HWY' : 'Highway',
                       'Ln' : 'Lane',
                       'Pkwy' : 'Parkway',
                       'Rd'   : 'Road',
                       'St'   : 'Street','St.' : 'Street','street' : 'Street',
                       'Ovlk' : 'Overlook',
                       'way': 'Way',
                       'N' : 'North','N.': 'North',
                       'S' : 'South','S.': 'South',
                       'E' : 'East','E.': 'East',
                       'W': 'West','W.': 'West',
                       'IH35': 'Interstate Highway 35','IH 35': 'Interstate Highway 35',
                       'I 35': 'Interstate Highway 35','I-35': 'Interstate Highway 35'}
```

let us search street types again and replace abbreviations with full standardized street types


```python
for street_type, ways in street_types.iteritems():
    for name in ways:
        better_name = update(name, street_type_mapping)
        print name, "=>", better_name
```

    Merimac => Merimac
    Clara Van => Clara Van
    Capri => Capri
    Chelsea Moor => Chelsea Moor
    Royal Birkdale Ovlk => Royal Birkdale Overlook
    Apache => Apache
    Farm-to-Market Road 812 => Farm-to-Market Road 812
    Bee Cave Road Suite 163 => Bee Cave Road Suite 163
    Adventurer => Adventurer
    Affirmed => Affirmed
    West 35th Street Cutoff => West 35th Street Cutoff
    Ferguson Cutoff => Ferguson Cutoff
    House Wren => House Wren
    N I-35 Suite 298 => North Interstate Highway 35 Suite 298
    Melody => Melody
    East Highway 290 => East Highway 290
    Highway 290 => Highway 290
    W. Highway 290 => West Highway 290
    East Hwy 290 => East Highway 290
    C R 290 => C R 290
    West Highway 290 => West Highway 290
    W Hwy 290 => West Highway 290
    U.S. 290 => U.S. 290
    West US Highway 290 => West US Highway 290
    E Hwy 290 => East Highway 290
    US Highway 290 => US Highway 290
    County Road 290 => County Road 290
    W HWY 290 => West Highway 290
    Helios Way, Bldg 2, Suite 290 => Helios Way, Bldg 2, Suite 290
    US 290 => US 290
    Pony Chase => Pony Chase
    Pecan Chase => Pecan Chase
    Mustang Chase => Mustang Chase
    Glen Rose Chase => Glen Rose Chase
    Shetland Chase => Shetland Chase
    Wild Basin Lodge => Wild Basin Lodge
    Palm Harborway => Palm Harborway
    south church street => south church Street
    East main street => East main Street
    South 1st street => South 1st Street
    White House street => White House Street
    Carlos G Parker Boulevard Northwest => Carlos G Parker Boulevard Northwest
    Raven Caw pass => Raven Caw pass
    Applegate Drive East => Applegate Drive East
    Mockingbird Lane East => Mockingbird Lane East
    Alpine Road East => Alpine Road East
    Brenham Street East => Brenham Street East
    Basin Ledge East => Basin Ledge East
    Hwy 290 East => Highway 290 East
    Ledgeway East => Ledgeway East
    Main Street East => Main Street East
    Black Locust Drive East => Black Locust Drive East
    Rutland Village East => Rutland Village East
    US 290 East => US 290 East
    Covington Drive East => Covington Drive East
    Colorado Drive East => Colorado Drive East
    Cypress Point East => Cypress Point East
    Walnut Street East => Walnut Street East
    Rapid Springs Cove East => Rapid Springs Cove East
    Caddo Street East => Caddo Street East
    Canyon Circle East => Canyon Circle East
    Edwin Reinhardt => Edwin Reinhardt
    Roaring Fork => Roaring Fork
    East 23rd Street, North End Zone, Suite 5.700 => East 23rd Street, North End Zone, Suite 5.700
    Hilldale => Hilldale
    Meadow Ford => Meadow Ford
    Sunterro => Sunterro
    Silver Spur => Silver Spur
    Rutledge Spur => Rutledge Spur
    Lohmans Spur => Lohmans Spur
    Quick Fort => Quick Fort
    W. Anderson Lane, Suite A-15 => West Anderson Lane, Suite A-15
    Farm-to-Market Road 2769 => Farm-to-Market Road 2769
    Woodrow Ave. => Woodrow Avenue
    Sioux => Sioux
    Inland Greens => Inland Greens
    Avenue K => Avenue K
    Palace Green => Palace Green
    Saint Georges Green => Saint Georges Green
    Bear Claw => Bear Claw
    Jollyville Road Suite 100 => Jollyville Road Suite 100
    Avery Ranch Blvd Building A #100 => Avery Ranch Boulevard Building A #100
    RM 2222 Unit #100 => RM 2222 Unit #100
    Old Jollyville Road, Suite 100 => Old Jollyville Road, Suite 100
    4207 James Casey st #101 => 4207 James Casey st #101
    S 1st St, Suite 104 => South 1st St, Suite 104
    11410 Century Oaks Terrace Suite #104 => 11410 Century Oaks Terrace Suite #104
    Arroyo Claro => Arroyo Claro
    Mirador => Mirador
    Lake Clark => Lake Clark
    Liberty Grotto => Liberty Grotto
    N. IH35, => North IH35,
    N. IH 35 => North IH 35
    South Interstate 35 => South Interstate 35
    S Interstate 35 => South Interstate 35
    N Interstate Highway 35 => North Interstate Highway 35
    North IH 35 => North IH 35
    Interstate 35 => Interstate 35
    Highway Interstate 35 => Highway Interstate 35
    South I 35 => South I 35
    North Interstate Highway 35 => North Interstate Highway 35
    I 35 => I 35
    S Interstate Highway 35 => South Interstate Highway 35
    9600 S IH 35 => 9600 South IH 35
    Interstate Highway 35 => Interstate Highway 35
    Avenue N => Avenue North
    IH 35 N => IH 35 North
    Capital of TX Hwy N => Capital of TX Highway North
    Farm to Market 620 N => Farm to Market 620 North
    Calle Limon => Calle Limon
    Creek Mountain => Creek Mountain
    Pecan St. => Pecan Street
    E 38th 1/2 St. => East 38th 1/2 Street
    E. 43rd St. => East 43rd Street
    Camelback => Camelback
    Green Acres => Green Acres
    Clearwater => Clearwater
    Michael Dale => Michael Dale
    Old Walsh Tarlton => Old Walsh Tarlton
    Pasa Tiempo => Pasa Tiempo
    Green Lanes => Green Lanes
    Explorer => Explorer
    N IH 35 Bldg. 6 => North IH 35 Bldg. 6
    Gunsmoke => Gunsmoke
    Dream Catcher => Dream Catcher
    Avenue F => Avenue F
    Voyageurs => Voyageurs
    Shepherds Corral => Shepherds Corral
    O K Corral => O K Corral
    Raglan CastlePath => Raglan CastlePath
    FM 1626 => FM 1626
    Farm-to-Market Road 1626 => Farm-to-Market Road 1626
    F.M. 1626 => F.M. 1626
    Farm-to-Market Road 1625 => Farm-to-Market Road 1625
    Yellow Sage => Yellow Sage
    Bold Sundown => Bold Sundown
    South I-35 Service SB => South Interstate Highway 35 Service SB
    Mustang => Mustang
    Sendera Bonita => Sendera Bonita
    West Parmer Ln => West Parmer Lane
    Hidden Hills Ln => Hidden Hills Lane
    Calhoun Ln => Calhoun Lane
    Buzz Schneider Ln => Buzz Schneider Lane
    Laguna Seca Ln => Laguna Seca Lane
    Lantana Ln => Lantana Lane
    Sky Ridge Ln => Sky Ridge Lane
    W Braker Ln => West Braker Lane
    W Anderson Ln => West Anderson Lane
    Rocky Top Ln => Rocky Top Lane
    Chick Pea Ln => Chick Pea Lane
    Pfennig Ln => Pfennig Lane
    Pasadera Ln => Pasadera Lane
    Rockwood Ln => Rockwood Lane
    Via Media => Via Media
    Wagon Wheel => Wagon Wheel
    Fleming court => Fleming court
    West William Cannon => West William Cannon
    Hambletonian => Hambletonian
    El Viejo Camino => El Viejo Camino
    Springwater => Springwater
    River Birch => River Birch
    Falcon => Falcon
    Eagle Cliff => Eagle Cliff
    Gila Cliff => Gila Cliff
    Avenue A => Avenue A
    9600 IH 35 C-200 => 9600 IH 35 C-200
    S IH 35 Frontage Rd #140 => South IH 35 Frontage Road #140
    Laughing Dog => Laughing Dog
    Running Rope => Running Rope
    Research Blvd #L2 => Research Boulevard #L2
    Fandango => Fandango
    South Congress Avene => South Congress Avenue
    Highlander => Highlander
    Farm to Market 685 => Farm to Market 685
    FM 685 => FM 685
    Stonebridge => Stonebridge
    Burnet Rd Ste, A500 => Burnet Road Ste, A500
    Creek Bottom => Creek Bottom
    Gonzales => Gonzales
    2901 Capital of Texas Hwy Suites F-4 => 2901 Capital of Texas Highway Suites F-4
    S. Capitol of Texas Hwy, #F-4 => South Capitol of Texas Hwy, #F-4
    Skyline Rd => Skyline Road
    Red Pebble Rd => Red Pebble Road
    Barley Rd => Barley Road
    Barton Springs Rd => Barton Springs Road
    Moon Rock Rd => Moon Rock Road
    Bee Creek Rd => Bee Creek Road
    N Interstate 35 Frontage Rd => North Interstate 35 Frontage Road
    Spicewood Springs Rd => Spicewood Springs Road
    Big Meadow Rd => Big Meadow Road
    Palomino Ranch Rd => Palomino Ranch Road
    Commons Rd => Commons Road
    Burnet Rd => Burnet Road
    Tawny Farms Rd => Tawny Farms Road
    Highway 130 => Highway 130
    Switch Willo => Switch Willo
    Mesa Oaks => Mesa Oaks
    Sierra Oaks => Sierra Oaks
    County Road 138 => County Road 138
    N. Lamar suite#L131 => North Lamar suite#L131
    Longhorn Landing => Longhorn Landing
    Richfield Landing => Richfield Landing
    North Highway 183 #406 => North Highway 183 #406
    North Lakeline Boulevard, Ste. 400 => North Lakeline Boulevard, Ste. 400
    Edenderry => Edenderry
    Circle Haven => Circle Haven
    Troll Haven => Troll Haven
    9901 N Capital Of texas => 9901 North Capital Of texas
    Ranch to Market Road 2222 => Ranch to Market Road 2222
    E. Whitestone Blvd #G-145 => East Whitestone Boulevard #G-145
    Calle Caliche => Calle Caliche
    High Lonesome => High Lonesome
    Messenger Stakes => Messenger Stakes
    Hill Country Blvd., Suite C1-100 => Hill Country Blvd., Suite C1-100
    Rue de St Tropez => Rue de Street Tropez
    Twin Saddles => Twin Saddles
    Sandpiper => Sandpiper
    The Living End => The Living End
    Indiana Dunes => Indiana Dunes
    Rock Rose => Rock Rose
    Pow Wow => Pow Wow
    W. Liberty => West Liberty
    FM 619 => FM 619
    Paw Print => Paw Print
    Tortilla Flat => Tortilla Flat
    Wet Season => Wet Season
    1500 S. IH35 => 1500 South Interstate Highway 35
    Prince William => Prince William
    Seawind => Seawind
    N I H 35 Bldg 7 => North I H 35 Bldg 7
    Camino Viejo => Camino Viejo
    RM1431 => RM1431
    Avenue G => Avenue G
    China Grove => China Grove
    I35 => I35
    La Cantera => La Cantera
    Highway 71 W => Highway 71 West
    Hwy 290 W => Highway 290 West
    Ranch Road 620 North => Ranch Road 620 North
    Lake Hills Drive North => Lake Hills Drive North
    Tumbleweed Trail North => Tumbleweed Trail North
    Summit Ridge Drive North => Summit Ridge Drive North
    Redondo Drive North => Redondo Drive North
    Cowal Drive North => Cowal Drive North
    Meadows Drive North => Meadows Drive North
    Interstate Highway 35 Service Road North => Interstate Highway 35 Service Road North
    Ute Trail North => Ute Trail North
    State Highway 95 North => State Highway 95 North
    Sioux Trail North => Sioux Trail North
    Hideaway North => Hideaway North
    Augusta Drive North => Augusta Drive North
    IH 35 North => IH 35 North
    FM 620 North => FM 620 North
    Fresco Drive North => Fresco Drive North
    Chesapeake Bay Lane North => Chesapeake Bay Lane North
    Cuernavaca Drive North => Cuernavaca Drive North
    Dunlap Road North => Dunlap Road North
    Ashwood North => Ashwood North
    Venture Boulevard North => Venture Boulevard North
    5th Street North => 5th Street North
    Weston Lane North => Weston Lane North
    Kettleman Lane North => Kettleman Lane North
    4th Street North => 4th Street North
    Pace Bend Road North => Pace Bend Road North
    Hillside North => Hillside North
    Highway 95 North => Highway 95 North
    Lowell Lane North => Lowell Lane North
    Laurelwood Drive North => Laurelwood Drive North
    Tandem Blvd. => Tandem Boulevard
    South Lamar Blvd. => South Lamar Boulevard
    South Exposition Blvd. => South Exposition Boulevard
    W North Loop Blvd. => West North Loop Boulevard
    East Old Settlers Blvd. => East Old Settlers Boulevard
    Research Blvd. => Research Boulevard
    Old Farm-to-Market 1431 => Old Farm-to-Market 1431
    Farm-to-Market Road 1431 => Farm-to-Market Road 1431
    Big Horn => Big Horn
    County Road 459 => County Road 459
    RM 620 => RM 620
    FM 620 => FM 620
    N FM 620 => North FM 620
    Ranch Road 620 => Ranch Road 620
    Ranch-to-Market Road 620 => Ranch-to-Market Road 620
    RR 620 => RR 620
    Real Catorce => Real Catorce
    Country Rd. 452 => Country Rd. 452
    County Road 170 => County Road 170
    Lido => Lido
    FM 973 => FM 973
    Farm-to-Market Road 973 => Farm-to-Market Road 973
    N Farm-To-Market Road 973 => North Farm-To-Market Road 973
    Montana Norte => Montana Norte
    Ladera Norte => Ladera Norte
    Broken Arrow => Broken Arrow
    East Meadow Vale => East Meadow Vale
    Highway 183 => Highway 183
    U.S. 183 => U.S. 183
    United States Highway 183 => United States Highway 183
    US 183 => US 183
    US Highway 183 => US Highway 183
    N HWY 183 => North Highway 183
    Barton Skyway => Barton Skyway
    Longhorn Skyway => Longhorn Skyway
    6800 Burnet Rd #2 => 6800 Burnet Road #2
    Picadilly => Picadilly
    Bachelor Gulch => Bachelor Gulch
    Thunder Gulch => Thunder Gulch
    Grubstake Gulch => Grubstake Gulch
    Hidden Mesa => Hidden Mesa
    Lone Mesa => Lone Mesa
    Spicewood Mesa => Spicewood Mesa
    Mustang Mesa => Mustang Mesa
    Alta Mesa => Alta Mesa
    Via Fortuna => Via Fortuna
    Avenue B => Avenue B
    South Interstate 35, Suite B => South Interstate 35, Suite B
    Chimney Corners => Chimney Corners
    Tall Withers => Tall Withers
    Indian Summit => Indian Summit
    Hitching Post => Hitching Post
    Sidewinder => Sidewinder
    Ranch to Market Road 12 => Ranch to Market Road 12
    Sierra Colorado => Sierra Colorado
    Galaxy => Galaxy
    Paseo del Toro => Paseo del Toro
    Canterwood => Canterwood
    Warbler Ledge => Warbler Ledge
    Basin Ledge => Basin Ledge
    Deer Creek Skyview => Deer Creek Skyview
    Piland Triangle => Piland Triangle
    W. University Avenue,Ste 320 => West University Avenue,Ste 320
    Sky Kiss => Sky Kiss
    Woodall Dr => Woodall Drive
    St Mary's Dr => Street Mary's Drive
    Walter Seaholm Dr => Walter Seaholm Drive
    Yaupon Range Dr => Yaupon Range Drive
    Lighthouse Landing Dr => Lighthouse Landing Drive
    Round Rock West Dr => Round Rock West Drive
    W Lake Dr => West Lake Drive
    W William Cannon Dr => West William Cannon Drive
    Dave Silk Dr => Dave Silk Drive
    Mineral Dr => Mineral Drive
    Forest Creek Dr => Forest Creek Drive
    Bill Baker Dr => Bill Baker Drive
    Corral de Tierra Dr => Corral de Tierra Drive
    Ivy Dr => Ivy Drive
    Jack Nicklaus Dr => Jack Nicklaus Drive
    Winged Elm Dr => Winged Elm Drive
    Carranzo Dr => Carranzo Drive
    Kyle Center Dr => Kyle Center Drive
    Canyon Springs Dr => Canyon Springs Drive
    Jimmy Clay Dr => Jimmy Clay Drive
    Justin Leonard Dr => Justin Leonard Drive
    Octavia Dr => Octavia Drive
    Horse Wagon Dr => Horse Wagon Drive
    Via Ricco Dr => Via Ricco Drive
    Creekline Dr => Creekline Drive
    Bettis Trophy Dr => Bettis Trophy Drive
    Rain Song Dr => Rain Song Drive
    Executive Center Dr => Executive Center Drive
    Via Dono Dr => Via Dono Drive
    Panther Hall => Panther Hall
    West Ben White Boulevard #203 => West Ben White Boulevard #203
    West Ben White Boulevard, #203 => West Ben White Boulevard, #203
    Court of Saint James => Court of Saint James
    Vanguard => Vanguard
    Holly Crest Terrance => Holly Crest Terrance
    W Hwy 71 => West Highway 71
    US 290;HWY 71 => US 290;HWY 71
    TX 71 => TX 71
    Hwy 71 => Highway 71
    West Highway 71 => West Highway 71
    Comet => Comet
    Knights Bridge => Knights Bridge
    N. IH 35 Pflugerville => North IH 35 Pflugerville
    Sunset Strip => Sunset Strip
    West Louis Henna Blvd => West Louis Henna Boulevard
    Airport Blvd => Airport Boulevard
    Swenson Farms Blvd => Swenson Farms Boulevard
    Industrial Oaks Blvd => Industrial Oaks Boulevard
    N Bell Blvd => North Bell Boulevard
    North Lamar Blvd => North Lamar Boulevard
    Industrial Blvd => Industrial Boulevard
    N. Lamar Blvd => North Lamar Boulevard
    Stonelake Blvd => Stonelake Boulevard
    Escarpment Blvd => Escarpment Boulevard
    E Palm Valley Blvd => East Palm Valley Boulevard
    South Lamar Blvd => South Lamar Boulevard
    South Bell Blvd => South Bell Boulevard
    North Research Blvd => North Research Boulevard
    Research Blvd => Research Boulevard
    10000 Research Blvd => 10000 Research Boulevard
    W Hwy 71, STE D1 => West Highway 71, STE D1
    Lions Lair => Lions Lair
    Cantina Sky => Cantina Sky
    High Horse => High Horse
    Medicine Hat => Medicine Hat
    Robert Martinez Jr => Robert Martinez Jr
    House of York => House of York
    Barrhead => Barrhead
    RM 2244 => RM 2244
    Burnet Road #8 => Burnet Road #8
    Arterial 8 => Arterial 8
    Old FM 2243 => Old FM 2243
    Kerrville Folkway => Kerrville Folkway
    Scotland Yard => Scotland Yard
    Avenue H => Avenue H
    North Lamar Boulevard suite #B100 => North Lamar Boulevard suite #B100
    Royal Dublin => Royal Dublin
    Building B Suite 120 => Building B Suite 120
    Clubhouse Turn => Clubhouse Turn
    Palos Verdes => Palos Verdes
    County Road 129 => County Road 129
    Red River => Red River
    FM 1825 => FM 1825
    Ranch to Market Road 1826 => Ranch to Market Road 1826
    Farm To Market Road 1826 => Farm To Market Road 1826
    Frijolita => Frijolita
    Oak Alley => Oak Alley
    County Road 414 => County Road 414
    Carrara => Carrara
    Wolf Dancer => Wolf Dancer
    Rancho Mirage => Rancho Mirage
    Hunters Glen => Hunters Glen
    Welcome Glen => Welcome Glen
    Oak Glen => Oak Glen
    Cedar Glen => Cedar Glen
    Jacob Glen => Jacob Glen
    Willheather Glen => Willheather Glen
    Deer Shadow Ps => Deer Shadow Ps
    Spring Branch => Spring Branch
    Malaquita Branch => Malaquita Branch
    Plaza on the Lake => Plaza on the Lake
    Buffalo Lake => Buffalo Lake
    Crater Lake => Crater Lake
    US 183 #311 => US 183 #311
    Rue Le Fleur => Rue Le Fleur
    Bidens Pl => Bidens Pl
    Veletta Pl => Veletta Pl
    Talamore => Talamore
    Buffalo Tundra => Buffalo Tundra
    Cobblestone => Cobblestone
    Shoal Creek Blvd, Bld 3 => Shoal Creek Blvd, Bld 3
    Navajo => Navajo
    Avenue C => Avenue C
    Buck Race => Buck Race
    South IH-35 => South IH-35
    N IH-35 => North IH-35
    East Oltorf => East Oltorf
    Harvest Dance => Harvest Dance
    Speedway => Speedway
    Point O Woods => Point O Woods
    Trail of the Woods => Trail of the Woods
    Poppy Mallow => Poppy Mallow
    Seattle Slew => Seattle Slew
    Sherwood Forest => Sherwood Forest
    Country Knoll => Country Knoll
    Chamois Knoll => Chamois Knoll
    West Cesar Chavez => West Cesar Chavez
    Malabar => Malabar
    Sunday Silence => Sunday Silence
    Isle Royale => Isle Royale
    Mohawk => Mohawk
    Royal Pointe => Royal Pointe
    Burnet Road #200N => Burnet Road #200N
    Dragon => Dragon
    Ranch-to-Market Road 1869 => Ranch-to-Market Road 1869
    Quail Ravine => Quail Ravine
    Mariner => Mariner
    Old Stonehedge => Old Stonehedge
    Porpoise => Porpoise
    Dalmahoy => Dalmahoy
    Medalist => Medalist
    Vail Divide => Vail Divide
    Misty Heights Cc => Misty Heights Cc
    FM 969 => FM 969
    Camino Arbolago => Camino Arbolago
    Farm-to-Market Road 1100 => Farm-to-Market Road 1100
    Lake Mist => Lake Mist
    Blue Sky Cv => Blue Sky Cove
    Texas Ash Cv => Texas Ash Cove
    Tom Kite Cv => Tom Kite Cove
    Quiet Meadows Cv => Quiet Meadows Cove
    Peat Moors Cv => Peat Moors Cove
    La Estrella Cv => La Estrella Cove
    Morning Primrose Cv => Morning Primrose Cove
    Mallard Cv => Mallard Cove
    Rooney Cv => Rooney Cove
    Copper Point Cv => Copper Point Cove
    Sandy Creek Cv => Sandy Creek Cove
    Old Corral Cv => Old Corral Cove
    Red River Cv => Red River Cove
    Secluded Willow Cv => Secluded Willow Cove
    Hilltop Canyon Cv => Hilltop Canyon Cove
    Hal Sutton Cv => Hal Sutton Cove
    La Roca Cv => La Roca Cove
    Arbole Cv => Arbole Cove
    Clear Pond Cv => Clear Pond Cove
    Salem Oak Cv => Salem Oak Cove
    Ripley Castle Cv => Ripley Castle Cove
    Enchanted Cv => Enchanted Cove
    Lapin Cv => Lapin Cove
    Mock Cherry Cv => Mock Cherry Cove
    Claro Vista Ct => Claro Vista Ct
    Ely Ct => Ely Ct
    Krupa Ct => Krupa Ct
    Sterling Heights Ct => Sterling Heights Ct
    Sweetgum Ct => Sweetgum Ct
    Costello Ct => Costello Ct
    Stirling Castle Ct => Stirling Castle Ct
    Spanish Oak => Spanish Oak
    Live Oak => Live Oak
    Five Acre Wood => Five Acre Wood
    Crestmont => Crestmont
    San Jacinto => San Jacinto
    Avenue D => Avenue D
    Bayswater Garden => Bayswater Garden
    North el Dorado => North el Dorado
    South el Dorado => South el Dorado
    El Dorado => El Dorado
    Bubba's Bluff => Bubba's Bluff
    Crescent Bluff => Crescent Bluff
    Bullick Bluff => Bullick Bluff
    Travis Bluff => Travis Bluff
    Scout Bluff => Scout Bluff
    S Capital of Texas Hwy => South Capital of Texas Highway
    Avenue I => Avenue I
    Thunderbird => Thunderbird
    Sylvan Glade => Sylvan Glade
    Rue de St Raphael => Rue de Street Raphael
    Vista Corta => Vista Corta
    Branding Iron => Branding Iron
    Stillhouse Spring => Stillhouse Spring
    Challenger => Challenger
    Welch => Welch
    Lago Viento => Lago Viento
    Desert Flower => Desert Flower
    Executive Center Drive Suite 213 => Executive Center Drive Suite 213
    Wind Cave => Wind Cave
    Aleppo Pine => Aleppo Pine
    Sierra Madre => Sierra Madre
    Sierra Tahoe => Sierra Tahoe
    Maverick => Maverick
    Buffalo Gap => Buffalo Gap
    Gnu Gap => Gnu Gap
    Encino Verde => Encino Verde
    Cuesta Verde => Cuesta Verde
    Casa Verde => Casa Verde
    4201 South Congress Avenue #4 => 4201 South Congress Avenue #4
    County Road 280 => County Road 280
    Buckskin => Buckskin
    Criswell => Criswell
    Camino Alto => Camino Alto
    Palo Alto => Palo Alto
    Harrier Flight Trl => Harrier Flight Trl
    Poppy Hills Trl => Poppy Hills Trl
    Scenic Overlook Trl => Scenic Overlook Trl
    Channel Island => Channel Island
    Camino Seco => Camino Seco
    Arroyo Seco => Arroyo Seco
    Rio Seco => Rio Seco
    Roger Hanks Pkwy => Roger Hanks Parkway
    Soter Pkwy => Soter Parkway
    Riata Trace Pkwy => Riata Trace Parkway
    Beverly Skyline => Beverly Skyline
    Hill Country Skyline => Hill Country Skyline
    S Interstate 35, #260 => South Interstate 35, #260
    Laguna Grande => Laguna Grande
    Mesa Grande => Mesa Grande
    Rio Grande => Rio Grande
    Tealwood => Tealwood
    FM 535 => FM 535
    FM 1327 => FM 1327
    Farm-to-Market Road 1327 => Farm-to-Market Road 1327
    Buffalo Thunder => Buffalo Thunder
    Research Blvd #3000a => Research Boulevard #3000a
    County Road 117 => County Road 117
    Bonanza => Bonanza
    Stonebridge Dr. => Stonebridge Drive
    Sportsplex Dr. => Sportsplex Drive
    Cannon Dr. => Cannon Drive
    11928 Stonehollow Dr. => 11928 Stonehollow Drive
    Pawnee Pathway => Pawnee Pathway
    Jigsaw Pathway => Jigsaw Pathway
    Happy Vale Pathway => Happy Vale Pathway
    Blackfoot => Blackfoot
    Quarry => Quarry
    Sierra Montana => Sierra Montana
    Greenway => Greenway
    North MoPac Expressway #425 => North MoPac Expressway #425
    West 5th Street #300 => West 5th Street #300
    321 W Ben White Blvd #300 => 321 West Ben White Boulevard #300
    Hwy 290 W. Ste. 301 => Highway 290 West Ste. 301
    Meadows Dr #306 => Meadows Drive #306
    Medio Calle => Medio Calle
    Cane Pace => Cane Pace
    Rambling Range => Rambling Range
    Speaking Rock => Speaking Rock
    Big Boggy => Big Boggy
    Fuzz Fairway => Fuzz Fairway
    Lajitas => Lajitas
    Rue de St Germaine => Rue de Street Germaine
    Meadow Crest => Meadow Crest
    FM1431 => FM1431
    Pheasant Roost => Pheasant Roost
    Physicians way => Physicians Way
    Pfluger Street West => Pfluger Street West
    Rutland Village West => Rutland Village West
    View West => View West
    Wagon Road West => Wagon Road West
    Crystalbrook West => Crystalbrook West
    Alpine Road West => Alpine Road West
    Old 2243 West => Old 2243 West
    Carrie Manor Street West => Carrie Manor Street West
    Saint Elmo Road West => Saint Elmo Road West
    Julian Alps => Julian Alps
    Sutton => Sutton
    Firebird => Firebird
    Speedway Stop D5000 => Speedway Stop D5000
    Business Interstate Highway 35 J => Business Interstate Highway 35 J
    N Interstate 35, Suite 1805 => North Interstate 35, Suite 1805
    Caisteal Castle => Caisteal Castle
    Research Blvd, Austin => Research Blvd, Austin
    FM 3177 => FM 3177
    Turnback => Turnback
    Sierra Leon => Sierra Leon
    Round Rock Ave => Round Rock Avenue
    Barstow Ave => Barstow Avenue
    South Congress Ave => South Congress Avenue
    E. University Ave => East University Avenue
    S Congress Ave => South Congress Avenue
    House of Lancaster => House of Lancaster
    Metric Boulevard #150 => Metric Boulevard #150
    Farm-to-Market Road 150 => Farm-to-Market Road 150
    IH-35 South, #150 => IH-35 South, #150
    Ranch-to-Market Road 150 => Ranch-to-Market Road 150
    Burnet Road #600 => Burnet Road #600
    Sycamore Tr => Sycamore Tr
    Posse Tr => Posse Tr
    Sunflower Tr => Sunflower Tr
    Burnet Rd #608 => Burnet Road #608
    Circulo de Amistad => Circulo de Amistad
    Southview => Southview
    Loma Linda => Loma Linda
    Casitas => Casitas
    El Camino Real => El Camino Real
    Camino Real => Camino Real
    Una Mas => Una Mas
    State Highway 71 W Spicewood => State Highway 71 West Spicewood
    Brown Juniper => Brown Juniper
    Deer Track => Deer Track
    TX 45 => TX 45
    Greenwich Meridian => Greenwich Meridian
    Atlantic => Atlantic
    Spreading Oaks Drive/Rd => Spreading Oaks Drive/Rd
    La Costa => La Costa
    Camino La Costa => Camino La Costa
    I-35 Frontage => Interstate Highway 35 Frontage
    Beardsley Lane Bldg E => Beardsley Lane Bldg East
    Elysian Fields => Elysian Fields
    devonshire cove => devonshire cove
    Hidden Estates => Hidden Estates
    Pecan St => Pecan Street
    N Main St => North Main Street
    S 1st St => South 1st Street
    E Oltorf St => East Oltorf Street
    E 43rd St => East 43rd Street
    Red River St => Red River Street
    W 10th St => West 10th Street
    W Annie St => West Annie Street
    E 51st St => East 51st Street
    Rio Grande St => Rio Grande Street
    W 6th St => West 6th Street
    West Lynn St => West Lynn Street
    E 6th St => East 6th Street
    Duval St => Duval Street
    Amberwood South => Amberwood South
    Venture Boulevard South => Venture Boulevard South
    Whippoorwill Street South => Whippoorwill Street South
    US Highway 183 South => US Highway 183 South
    Sioux Trail South => Sioux Trail South
    Farm-to-Market Road 973 South => Farm-to-Market Road 973 South
    Ranch Road 620 South => Ranch Road 620 South
    Comanche => Comanche
    brigadoon lane => brigadoon lane
    Victory Gallop => Victory Gallop
    Pawnee => Pawnee
    Scott Crescent => Scott Crescent
    Margranita Crescent => Margranita Crescent
    Canyon Maple => Canyon Maple
    Sunfish => Sunfish


As seen above the mapping has been applied correctly to give full forms for cardinal directions and Ln, Dr, etc. Also updated IH-35/I-35 etc to 'Interstate Highway 35'(major highway in austin connecting San Antonio and Dallas)

2) For Postal Codes I used a similar approach as in the Street Name Cleaning. I converted them to standard 5 digit postal codes


```python
zip_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
zip_types = defaultdict(set)
expected_zip = ["73301","73344","76574","78602","78610","78612","78613","78615","78616","78617","78619","78620",
                "78621","78626","78628","78634","78640","78641","78642","78644","78645","78646","78652","78653",
                "78654","78656","78660","78663","78664","78665","78666","78669","78676","78680","78681","78682",
                "78691","78701","78702","78703","78704","78705","78712","78717","78719","78721","78722","78723",
                "78724","78725","78726","78727","78728","78729","78730","78731","78732","78733","78734","78735",
                "78736","78737","78738","78739","78741","78742","78744","78745","78746","78747","78748","78749",
                "78750","78751","78752","78753","78754","78756","78757","78758","78759","78957"]
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
                    audit_zip_codes(zip_types, tag.attrib['v'], regex, expected_zip)
    return zip_types
```


```python
audit(OSM_FILE, zip_type_re)
pprint.pprint(dict(zip_types))
```

    {'76574-4649': set(['76574-4649']),
     '78613-2277': set(['78613-2277']),
     u'78626\u200e': set([u'78626\u200e']),
     '78640-4520': set(['78640-4520']),
     '78640-6137': set(['78640-6137']),
     '78704-5639': set(['78704-5639']),
     '78704-7205': set(['78704-7205']),
     '78724-1199': set(['78724-1199']),
     '78728-1275': set(['78728-1275']),
     '78753-4150': set(['78753-4150']),
     '78754-5701': set(['78754-5701']),
     '78758-7008': set(['78758-7008']),
     '78758-7013': set(['78758-7013']),
     '78759-3504': set(['78759-3504']),
     'Texas': set(['Texas']),
     'tx': set(['tx'])}


To standardize the zipcodes, I will keep the first 5 digits in the postal code and drop the digits after the hyphen.


```python
def update_postal(postcode):
    return postcode.split("-")[0]
```


```python
for zip_type, ways in zip_types.iteritems():
    for postal in ways:
        better_zip = update_postal(postal)
        print postal, "=>", better_zip
```

    78759-3504 => 78759
    tx => tx
    78626‎ => 78626‎
    78613-2277 => 78613
    76574-4649 => 76574
    78754-5701 => 78754
    78724-1199 => 78724
    78704-7205 => 78704
    Texas => Texas
    78758-7008 => 78758
    78728-1275 => 78728
    78753-4150 => 78753
    78640-4520 => 78640
    78758-7013 => 78758
    78640-6137 => 78640
    78704-5639 => 78704


## Preparing for Mongo DB


```python
from datetime import datetime

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
                    node['created'][attrib] = datetime.strptime(element.attrib[attrib], '%Y-%m-%dT%H:%M:%SZ')
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
                        better_name = update(tag.attrib['v'], street_type_mapping)
                        node['address'][sub_attr] = better_name
                    if key == 'postcode' or key == 'addr:postcode':
                        node['address'][sub_attr] = update_postal(tag.attrib['v'])
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
```

#### Write JSON file


```python
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
                    fo.write(json.dumps(el, indent=2, default=json_util.default)+"\n")
                else:
                    fo.write(json.dumps(el, default=json_util.default) + "\n")

process_map(OSM_FILE)
```

## Overview of the Data


```python
import os
print 'The downloaded file is {} MB'.format(os.path.getsize(OSM_FILE)/1.0e6) # convert from bytes to megabytes
```

    The downloaded file is 1414.558803 MB



```python
print 'The json file is {} MB'.format(os.path.getsize(OSM_FILE + ".json")/1.0e6) # convert from bytes to megabytes
```

    The json file is 2543.250995 MB


#### Number of Street Addresses


```python
osm_file = open(OSM_FILE, "r")
address_count = 0

for event, elem in ET.iterparse(osm_file, events=("start",)):
    if elem.tag == "node" or elem.tag == "way":
        for tag in elem.iter("tag"): 
            if is_street_name(tag):
                address_count += 1

address_count
```




    326698



## Working with MongoDB


```python
import signal
import subprocess

# The os.setsid() is passed in the argument preexec_fn so
# it's run after the fork() and before  exec() to run the shell.
pro = subprocess.Popen('mongod', preexec_fn = os.setsid)
```

#### Connect to database with PyMongo


```python
from pymongo import MongoClient

db_name = 'openstreetmap'

# Connect to Mongo DB
client = MongoClient('localhost:27017')
# Database 'openstreetmap' will be created if it does not exist.
db = client[db_name]
```

#### Import data set


```python
# Build mongoimport command
collection = OSM_FILE[:OSM_FILE.find('.')]
working_directory = '/Users/nonusingh/Documents/PythonProjects/code/'
json_file = OSM_FILE + '.json'

mongoimport_cmd = 'mongoimport -h 127.0.0.1:27017 ' + \
                  '--db ' + db_name + \
                  ' --collection ' + collection + \
                  ' --file ' + working_directory + json_file

# Before importing, drop collection if it exists (i.e. a re-run)
if collection in db.collection_names():
    print 'Dropping collection: ' + collection
    db[collection].drop()

# Execute the command
print 'Executing: ' + mongoimport_cmd
subprocess.call(mongoimport_cmd.split())
```

    Dropping collection: austin_texas
    Executing: mongoimport -h 127.0.0.1:27017 --db openstreetmap --collection austin_texas --file /Users/nonusingh/Documents/PythonProjects/code/austin_texas.osm.json





    0



## Investigating the Data


```python
austin_texas = db[collection]
```


```python
austin_texas
```




    Collection(Database(MongoClient(host=['localhost:27017'], document_class=dict, tz_aware=False, connect=True), u'openstreetmap'), u'austin_texas')



#### Number of Documents


```python
austin_texas.find().count()
```




    7055769



#### Number of Unique Users


```python
len(austin_texas.distinct('created.user'))
```




    1249



1249 vs 1260 users we began with, probably due to loss of data in shape_element function

#### Number of Nodes and Ways


```python
db.austin_texas.find( {"type":"node"} ).count()
```




    6386286




```python
db.austin_texas.find( {"type":"way"} ).count()
```




    669483



#### Top 5 Contributors


```python
pipeline = [{'$group': {'_id': '$created.user','count': {'$sum' : 1}}},{'$sort': {'count' : -1}},{'$limit': 5}]

def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)
```

    {u'_id': u'patisilva_atxbuildings', u'count': 2742450}
    {u'_id': u'ccjjmartin_atxbuildings', u'count': 1300433}
    {u'_id': u'ccjjmartin__atxbuildings', u'count': 940002}
    {u'_id': u'wilsaj_atxbuildings', u'count': 358812}
    {u'_id': u'jseppi_atxbuildings', u'count': 300855}


atx buildings works on tracking and documenting the community effort to import the 2013 building footprints and address points datasets from the City of Austin Data Portal. Andy Wilson(wilsaj_atxbuildings), 
John Clary(johnclary_atxbuildings), James Seppi(jseppi_atxbuildings), Chris Martin(ccjjmartin_atxbuildings), Kelvin Thompson(kkt_atxbuildings), Jonathan Pa(jonathan pa_atxbuildings) and Pati Silva(patisilva_atxbuildings) are all participants of this project. 

#### Number of users appearing only once


```python
pipeline = [{"$group":{"_id":"$created.user", "count":{"$sum":1}}}, {"$group":{"_id":"$count", "num_users":{"$sum":1}}}, {"$sort":{"_id":1}}, {"$limit":1}]

def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)
```

    {u'_id': 1, u'num_users': 280}


#### Postal Codes


```python
pipeline =[{'$match': {'address.postcode': {'$exists': 1}}},{'$group': {'_id': '$address.postcode','count': {'$sum': 1}}}, {'$sort': {'count': -1}},{'$limit': 10}]
def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)
```

    {u'_id': u'78645', u'count': 10883}
    {u'_id': u'78734', u'count': 5607}
    {u'_id': u'78653', u'count': 3544}
    {u'_id': u'78660', u'count': 3518}
    {u'_id': u'78669', u'count': 3189}
    {u'_id': u'78641', u'count': 2870}
    {u'_id': u'78704', u'count': 2466}
    {u'_id': u'78746', u'count': 2450}
    {u'_id': u'78759', u'count': 2093}
    {u'_id': u'78738', u'count': 1939}


Most of the postal codes have been cleaned up by our script


```python
pipeline =[{'$match': {'address.street': {'$exists': 1}}},{'$group': {'_id': '$address.street','count': {'$sum': 1}}}, {'$sort': {'count': -1}},{'$limit': 10}]
def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)
```

    {u'_id': u'North Lamar Boulevard', u'count': 679}
    {u'_id': u'Burnet Road', u'count': 558}
    {u'_id': u'North Interstate Highway 35 Service Road', u'count': 551}
    {u'_id': u'Ranch Road 620', u'count': 494}
    {u'_id': u'South Congress Avenue', u'count': 482}
    {u'_id': u'Shoal Creek Boulevard', u'count': 445}
    {u'_id': u'South 1st Street', u'count': 425}
    {u'_id': u'Guadalupe Street', u'count': 397}
    {u'_id': u'Manchaca Road', u'count': 391}
    {u'_id': u'Cameron Road', u'count': 369}


Most of the street names have been cleaned up by our script

#### Cities in the dataset


```python
pipeline =[{"$group":{"_id":"$address.city", "count":{"$sum":1}}}, {"$sort":{"count": -1}},{'$limit': 10}]
def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)
```

    {u'_id': None, u'count': 7052097}
    {u'_id': u'Austin', u'count': 3127}
    {u'_id': u'Round Rock', u'count': 119}
    {u'_id': u'Kyle', u'count': 62}
    {u'_id': u'Austin, TX', u'count': 50}
    {u'_id': u'Cedar Park', u'count': 40}
    {u'_id': u'Leander', u'count': 39}
    {u'_id': u'Pflugerville', u'count': 36}
    {u'_id': u'Buda', u'count': 26}
    {u'_id': u'Georgetown', u'count': 14}


A lot of addresses had 'None' in their city name. 

Other than Austin, TX, the map includes the neighboring areas like Kyle, Buda, Round Rock etc.

## Additional data exploration using MongoDB queries

#### Top Amenities


```python
pipeline = [{"$group":{"_id":"$amenity", "count":{"$sum":1}}}, {"$sort":{"count": -1}},{'$limit': 10}]
def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)
```

    {u'_id': None, u'count': 7047676}
    {u'_id': u'parking', u'count': 2198}
    {u'_id': u'restaurant', u'count': 805}
    {u'_id': u'waste_basket', u'count': 602}
    {u'_id': u'fast_food', u'count': 596}
    {u'_id': u'school', u'count': 559}
    {u'_id': u'place_of_worship', u'count': 515}
    {u'_id': u'fuel', u'count': 441}
    {u'_id': u'bench', u'count': 360}
    {u'_id': u'shelter', u'count': 239}


Top Amenities are Parking, Restaurants and Waste Baskets

#### Top Religion


```python
pipeline = [{"$match":{"amenity":{"$exists":1}, "amenity":"place_of_worship"}},{"$group":{"_id":"$religion", "count":{"$sum":1}}},{"$sort":{"count":-1}}, {"$limit":5}]
def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)
```

    {u'_id': u'christian', u'count': 465}
    {u'_id': None, u'count': 32}
    {u'_id': u'buddhist', u'count': 6}
    {u'_id': u'muslim', u'count': 3}
    {u'_id': u'jewish', u'count': 3}


Top Religion is 'Christianity' with 465 places of worship

#### Top Restaurants


```python
pipeline =[{'$match': {'amenity': 'restaurant'}},{'$group': {'_id': '$name','count': {'$sum': 1}}},{'$sort': {'count': -1}},{'$limit': 10}]
def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)
```

    {u'_id': None, u'count': 21}
    {u'_id': u"Chili's", u'count': 10}
    {u'_id': u'IHOP', u'count': 6}
    {u'_id': u"Applebee's", u'count': 5}
    {u'_id': u"Denny's", u'count': 5}
    {u'_id': u'Pizza Hut', u'count': 4}
    {u'_id': u'Baby Acapulco', u'count': 4}
    {u'_id': u'Chipotle Mexican Grill', u'count': 4}
    {u'_id': u'Olive Garden', u'count': 3}
    {u'_id': u"Chuy's", u'count': 3}


#### Popular Cuisine


```python
pipeline = [{"$match":{"amenity":{"$exists":1}, "amenity":"restaurant"}}, {"$group":{"_id":"$cuisine", "count":{"$sum":1}}},{"$sort":{"count":-1}}, {"$limit":5}]
def aggregate(db, pipeline):
    result = db.austin_texas.aggregate(pipeline)
    #pprint.pprint(result)
    return result

result = aggregate(db, pipeline)

for document in result:
    pprint.pprint(document)
```

    {u'_id': None, u'count': 405}
    {u'_id': u'mexican', u'count': 74}
    {u'_id': u'american', u'count': 35}
    {u'_id': u'pizza', u'count': 33}
    {u'_id': u'chinese', u'count': 23}


Popular cuisines include Mexican, American and Pizza- no surprise there 

## Other ideas about the dataset

As seen above atx-buildings has worked on mapping and loading of most of the addresses for austin osm. Their wiki page is http://wiki.openstreetmap.org/wiki/Austin,_TX/Buildings_Import and github repo is https://github.com/atx-osg/atx-buildings. Their scripts have jsons for converting and cleaning up of street addresses and zipcodes. Since the team standardized the data loading, our dataset was pretty clean to begin with. If we have similar structured data loading with a few rules and clean up scripts, then osm data would become robust. The problem with this however is that too many rules/madatory fields could deter users from contributing more. As an incentive, osm page should display top individual contributors and teams who are working on loading and cleaning of data. 

Another suggestion would be to indicate areas on the map that have less or incomplete data so that contributors can focus on that region to make the map more complete. There is a lot of missing data for 'city' field in addresses. Using Geopy package, some of the missing information can be filled in.

## Conclusion

After the review of Austin's OSM data, although incomplete, I believe it has been cleaned well for the purposes of this exercise. The scripts developed during this project was successful in parsing and cleaning most of the data.
