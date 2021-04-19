#################################
##### Name: Chengcheng Wang
##### Uniqname: chchwang@umich.edu
#################################

from bs4 import BeautifulSoup
import requests
import json
import sqlite3
import sys
import time
import secrets 
import plotly
import plotly.graph_objects as go 
import plotly.figure_factory as ff

CACHE_FILENAME = "yelp.json"
CACHE_DICT = {}
CACHE_URL = {}
BASIC_URL='https://api.yelp.com'
SEARCH_PATH ='/v3/businesses/search'
API_KEY=secrets.API_KEY
MAPBOX_TOKEN=secrets.MAPBOX_TOKEN
headers = {"Authorization": "Bearer " + API_KEY}
DBNAME = 'final.db'


def open_cache():
    ''' Opens the cache file if it exists and loads the JSON into
    the CACHE_DICT dictionary.
    if the cache file doesn't exist, creates a new cache dictionary
    
    Parameters
    ----------
    None
    
    Returns
    -------
    The opened cache: dict
    '''
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict


def save_cache(cache_dict):
    ''' Saves the current state of the cache to disk
    
    Parameters
    ----------
    cache_dict: dict
        The dictionary to save
    
    Returns
    -------
    None
    '''
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(CACHE_FILENAME,"w")
    fw.write(dumped_json_cache)
    fw.close() 

def construct_unique_key(baseurl, params):
    ''' constructs a key that is guaranteed to uniquely and 
    repeatably identify an API request by its baseurl and params
    
    Parameters
    ----------
    baseurl: string
        The URL for the API endpoint
    params: dict
        A dictionary of param:value pairs
    
    Returns
    -------
    string
        the unique key as a string
    '''
    param_strings=[]
    connector = '_'
    for k in params.keys():
        param_strings.append(f"{k}_{params[k]}")
    param_strings.sort()
    unique_key = baseurl + connector + connector.join(param_strings)
    return unique_key

def make_request(baseurl, params):
    '''Make a request to the Web API using the baseurl and params
    
    Parameters
    ----------
    baseurl: string
        The URL for the API endpoint
    params: dictionary
        A dictionary of param:value pairs
    
    Returns
    -------
    dict
        the data returned from making the request in the form of 
        a dictionary
    '''
    response = requests.get(baseurl, 
                        params=params, 
                        headers=headers)
    return response.json()

def make_request_with_cache(baseurl, params):
    '''Check the cache for a saved result for this baseurl+params:values
    combo. If the result is found, return it. Otherwise send a new 
    request, save it, then return it.

    Parameters
    ----------
    baseurl: string
        The URL for the API endpoint
    
    Returns
    -------
    dict
        the results of the query as a dictionary loaded from cache
        JSON
    '''
    request_url=construct_unique_key(baseurl, params)
    if request_url in CACHE_DICT.keys():
        print("Using CACHE")
        return CACHE_DICT[request_url]
    else:
        print("Fetching")
        CACHE_DICT[request_url]=make_request(baseurl, params)
        save_cache(CACHE_DICT)
        return CACHE_DICT[request_url]

def make_request_with_cache_url(request_url):
    if request_url in CACHE_DICT.keys():
        print("Using CACHE")
        return CACHE_URL[request_url]
    else:
        response=requests.get(request_url)
        CACHE_URL[request_url]=response.text
        save_cache(CACHE_URL)
        return CACHE_URL[request_url]
class City:

    def __init__(self, name, rank, state, location):
        self.name=name
        self.rank=int(rank)
        self.state=state
        self.location=location
    def info(self):
        return self.rank + self.name+ self.state + self.location

conn = sqlite3.connect(DBNAME)
cur = conn.cursor()
##scrape the wikipedia page
def build_city_information_list():
    ''' Make a list of city information from "https://en.wikipedia.org/wiki/List_of_United_States_cities_by_population"

    Parameters
    ----------
    None

    Returns
    -------
    list
        the city list that contains all the information
    '''
    basic_URL="https://en.wikipedia.org/wiki/List_of_United_States_cities_by_population"
    response=make_request_with_cache_url(basic_URL)
    soup=BeautifulSoup(response, 'html.parser')

    listing_parent=soup.find_all("table", class_="wikitable sortable")[0]
    city_listing_parent=listing_parent.find_all("tr")
    city_url_dict={}
    city_name_list=[]
    state_list=[]
    latitude_list=[]
    longitude_list=[]
    for i in range(100):
        city_listing=city_listing_parent[i+1].find_all('td')
        city_name_list.append(city_listing[1].find('a').text.strip())
        try:
            state_list.append(city_listing[2].find('a').text)
        except:
            state_list.append(city_listing[2].text[1:-1])
        latitude_list.append((city_listing[-1].find("span",class_="geo-dec").text.split()[0][:2]))    
        longitude_list.append((city_listing[-1].find("span",class_="geo-dec").text.split()[0][:2])) 
        time.sleep(0.5)
    city_list=[]  
    for i in range(len(city_name_list)):
        city_list.append((int(i+1),city_name_list[i],state_list[i],latitude_list[i],longitude_list[i]))
    for i in city_list:
        print (i)

    
    return city_list
#build_city_information_list()
City_list=[]
for city in build_city_information_list():
    City_list.append(city[1])
#print(City_list)

#Create city database
drop_cities = '''
    DROP TABLE IF EXISTS 'cities';
'''
create_cities = '''
    CREATE TABLE IF NOT EXISTS 'cities' (
        'id' INTEGER PRIMARY KEY,
        'CityName'  TEXT NOT NULL,
        'StateName' TEXT NOT NULL,
        'Latitude'  REAL NOT NULL,
        'Longitude'  REAL NOT NULL
    );
'''
cur.execute(drop_cities)
cur.execute(create_cities)
insert_cities = '''
    INSERT INTO cities
    VALUES (?, ?, ?, ?, ?)
'''
for i in build_city_information_list():
    cur.execute(insert_cities,i)
conn.commit()


###Get restaurants information from YELP FUSION API###
class restaurant:
    def __init__(self,name,categories,rating,latitude,longitude,state,city,zipcode):
        self.name=name
        self.categories=categories
        self.rating=int(rating)
        self.coordinates=coordinates
        self.state=state
        self.city=city
        self.zipcode=zipcode
    def info(self):
        return self.name + self.categories+ self.rating + self.state + self.city

def get_restaurants(city_name, term='food'):
    """Generates a resturant dict from Yelp Fusion api for a specific city with cache checking
    Parameters
    ----------
    city_name
    term
    Returns
    -------
    dict:
        API raw dict
    """
    yelp_url = 'https://api.yelp.com/v3/businesses/search'
    yelp_dict = make_request_with_cache(yelp_url, {
        'location': city_name,
        'term': term,
        'limit': 50
    })
    return yelp_dict
#get_restaurants('Hoboken city', term='food')
def get_restaurant_list(city_name):
    restaurant_dict=get_restaurants(city_name, term='food')
    restaurant_list=[]
    id_list=[]
    #count=0
    for i in restaurant_dict["businesses"]:
        #count+=1
        businesses_list=[]
        if i['id'] not in id_list:
            id_list.append(i['id'])
            #businesses_list.append(i['id'])
        else:
            continue
        #businesses_list.append(count)
        businesses_list.append(i['name'])
        businesses_list.append(i['categories'][0]['title'])
        businesses_list.append(i['rating'])
        #businesses_list.append(i['coordinates']['latitude'])
        #businesses_list.append(i['coordinates']['longitude'])
        restaurant_list.append(tuple(businesses_list))
    restaurant_list=sorted(restaurant_list,key=lambda bu:bu[2],reverse=True) 
    k=0
    for i in restaurant_list:
        k+=1
        print(k,i)
    return restaurant_list
#get_restaurant_list('Hoboken city')
def get_restaurant_detail(res_name,city_name1):
    restaurant_dict=get_restaurants(city_name1, term='food')
    name_list=[]
    for i in restaurant_dict["businesses"]:
        name_list.append(i['name'])
    detail_list=[]
    #print(restaurant_dict["businesses"][1]['name'])
    if res_name in name_list:
        for i in range(len(name_list)):
            if restaurant_dict["businesses"][i]['name']==res_name:
                name=restaurant_dict["businesses"][i]['name']
                rating=restaurant_dict["businesses"][i]['rating']
                price=restaurant_dict["businesses"][i]['price']
                phone=restaurant_dict["businesses"][i]['phone']
                latitude=restaurant_dict["businesses"][i]['coordinates']['latitude']
                longitude=restaurant_dict["businesses"][i]['coordinates']['longitude']
                categories=restaurant_dict["businesses"][i]['categories']
                review_count=restaurant_dict["businesses"][i]['review_count']
                city=restaurant_dict["businesses"][i]['location']['city']
                state=restaurant_dict["businesses"][i]['location']['state']
                address=restaurant_dict["businesses"][i]['location']['address1']
                zipcode=restaurant_dict["businesses"][i]['location']['zip_code']
                print('name:',name)
                print('categories:',categories)
                print('rating:',rating)
                print('price:',price)
                print('phone:',phone)
                print('review_count:',review_count)
                print('coordinates:','[',latitude,longitude,']')
                print('address:',address)
                print('city:',city)
                print('state:',state)
                print('zipcode:',zipcode)
            else:
                continue
    else:
        print('Sorry,no such restaurant in this city. Please choose another restaurant.')
#get_restaurant_detail('Loquito','Hoboken city')

#Create restaurant database
def get_all_restaurant(city_name2):
    restaurant_dict=get_restaurants(city_name2, term='food')
    restaurant_list=[]
    id_list=[]
    count=0
    for i in restaurant_dict["businesses"]:
        count+=1
        all_list=[]
        try:
            if i['id'] not in id_list:
                id_list.append(i['id'])
                all_list.append(i['id'])
            else:
                continue
            all_list.append(count)
            all_list.append(i['name'])
            all_list.append(i['categories'][0]['title'])
            all_list.append(i['rating'])
            all_list.append(i['phone'])
            all_list.append(i['coordinates']['latitude'])
            all_list.append(i['coordinates']['longitude'])
            all_list.append(i['review_count'])
            all_list.append(i['location']['city'])
            all_list.append(i['location']['state'])
            all_list.append(i['location']['zip_code'])
            restaurant_list.append(tuple(all_list))
            #print(restaurant_list[1])
        except:
            continue
    return restaurant_list

###CREATE restaurant DATABASE###
conn = sqlite3.connect(DBNAME)
cur = conn.cursor()
drop_restaurants = '''
    DROP TABLE IF EXISTS 'restaurants';
'''
create_restaurants = '''
    CREATE TABLE IF NOT EXISTS 'restaurants' (
        'id' TEXT PRIMARY KEY,
        'cityid' INTEGER NOT NULL,
        'name'  TEXT NOT NULL,
        'categories'  TEXT,
        'rating'  REAL,
        'Phone' TEXT,
        'Latitude'  REAL,
        'Longitude'  REAL,
        'review_count'  INTEGER,
        'CityName'  TEXT,
        'StateName'  TEXT,
        'zipcode'  REAL,
        FOREIGN KEY (cityid) REFERENCES cities (id)
    );
'''
cur.execute(drop_restaurants)
cur.execute(create_restaurants)
insert_restaurants = '''
    INSERT OR IGNORE INTO restaurants
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
'''
for i in City_list:
    for c in get_all_restaurant(i):
        cur.execute(insert_restaurants,c)
conn.commit()

def get_info_form_database(props, params=None):
    conn = sqlite3.connect(DBNAME)
    cur = conn.cursor()
    #print(len(props))
    real_props = ""
    for i in range(len(props)):
        real_props += "b.{}".format(props[i]) + ", "
    real_props = real_props[:-2]
    command = f'SELECT {real_props} FROM restaurants as b'
    if params is not None:
        keys = list(params.keys())
        for key in keys:
            if keys.index(key) == 0:
                command += f' WHERE {key}="{params[key]}"'
            else:
                command += f' AND {key}="{params[key]}"'
    command += ";"
    result = cur.execute(command).fetchall()
    conn.close()
    print(result)
    return result