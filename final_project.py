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
    params: dictionary
        A dictionary of param:value pairs
    
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
    '''Check the cache for a saved result for this request_url:values
    combo. If the result is found, return it. Otherwise send a new 
    request, save it, then return it.

    Parameters
    ----------
    request_url: string
        The URL for the API endpoint
    
    Returns
    -------
    dict
        the results of the query as a dictionary loaded from cache
        JSON
    '''
    if request_url in CACHE_DICT.keys():
        print("Using CACHE")
        return CACHE_URL[request_url]
    else:
        response=requests.get(request_url)
        CACHE_URL[request_url]=response.text
        save_cache(CACHE_URL)
        return CACHE_URL[request_url]



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
        time.sleep(0.1)
    city_list=[]  
    for i in range(len(city_name_list)):
        city_list.append((int(i+1),city_name_list[i],state_list[i],latitude_list[i],longitude_list[i]))
    # for i in city_list:
    #     print (i)

    
    return city_list


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
    '''a restaurant

    Instance Attributes
    -------------------
    name: string
        the name of a restaurant (e.g. 'Molinari Delicatessen')

    rating: float
        the rating of a restaurant (e.g. '4.5')

    phone: string
        the phone of a restaurant (e.g. '+14154212337')

    latitude: float
        the latitude of a restaurant (e.g. '37.7983818054199')

    longitude: float
        the longitude of a restaurant (e.g. '-122.407821655273')

    categories: string
        the categories of a restaurant (e.g. 'delis')

    review_count: int
        the review_count of a restaurant (e.g. '910')

    city: string
        the city of a restaurant (e.g. 'US')

    state: string
        the state of a restaurant (e.g. 'CA')

    address1: string
        the address1 of a restaurant (e.g. '373 Columbus Ave')

    zip_code: int
        the zip_code of a restaurant (e.g. '94133')
    '''
    def __init__(self,name,categories,rating,latitude,longitude,state,city,address1,zipcode,phone,review_count):
        self.name=name
        self.categories=categories
        self.rating=int(rating)
        self.latitude=latitude
        self.longitude=longitude
        self.state=state
        self.city=city
        self.address1=address1
        self.zipcode=zipcode
        self.phone=phone
        self.review_count=review_count
    def info(self):
        return self.name + self.categories+ self.rating + self.latitude+  self.longitude + self.state + self.city

def get_restaurants(city_name, term='food'):
    '''make a request to the Yelp Fusion API 
       and generates a restaurant dict with cache

    Parameters
    ----------
    city_name: str
        name of a city
    term: str
        term='food'

    Returns
    -------
    dict:
        the API dict
    '''
    yelp_url = 'https://api.yelp.com/v3/businesses/search'
    yelp_dict = make_request_with_cache(yelp_url, {
        'location': city_name,
        'term': term,
        'limit': 50
    })
    return yelp_dict

def get_restaurant_list(city_name):
    ''' get a list of all restaurants of a city, 
        including the information of  name, categories and rating,
        restaurants are sorted by rating 

    Parameters
    ----------
    city_name2: str
        name of a city

    Returns
    -------
    list
        A list of all the restaurant information
    '''
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
    # for i in restaurant_list:
    #     k+=1
    #     print(k,i)
    return restaurant_list

def get_restaurant_detail(res_name,city_name1):
    ''' get the detailed information of a restaurant

    Parameters
    ----------
    res_name: str
        name of a restaurant
    city_name1: str
        name of a city

    Returns
    -------
    str
        Detailed information of a restaurant
    '''
    restaurant_dict=get_restaurants(city_name1, term='food')
    name_list=[]
    for i in restaurant_dict["businesses"]:
        name_list.append(i['name'])
    detail_list=[]
   
    if res_name in name_list:
        for i in range(len(name_list)):
            if restaurant_dict["businesses"][i]['name']==res_name:
                name=restaurant_dict["businesses"][i]['name']
                rating=restaurant_dict["businesses"][i]['rating']
                phone=restaurant_dict["businesses"][i]['phone']
                latitude=restaurant_dict["businesses"][i]['coordinates']['latitude']
                longitude=restaurant_dict["businesses"][i]['coordinates']['longitude']
                categories=restaurant_dict["businesses"][i]['categories']
                review_count=restaurant_dict["businesses"][i]['review_count']
                city=restaurant_dict["businesses"][i]['location']['city']
                state=restaurant_dict["businesses"][i]['location']['state']
                address=restaurant_dict["businesses"][i]['location']['address1']
                zipcode=restaurant_dict["businesses"][i]['location']['zip_code']
                print(" ")
                print('name:',name)
                print('categories:',categories)
                print('rating:',rating)
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


def get_all_restaurant(city_name2):
    ''' get all restaurant information of a city

    Parameters
    ----------
    city_name2: str
        name of a city

    Returns
    -------
    list
        A list of all the restaurant information
    '''
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

def get_info_form_database(info, params=None):
    ''' get all restaurant information from the database

    Parameters
    ----------
    info: list
        a list of strings want to query
    params: dict
        A dictionary of param:value pairs

    Returns
    -------
    list
        A list of all the restaurant information queried
    '''
    conn = sqlite3.connect(DBNAME)
    cur = conn.cursor()

    real_info = ""
    for i in range(len(info)):
        real_info += "b.{}".format(info[i]) + ", "
    real_info = real_info[:-2]
    command = f'SELECT {real_info} FROM restaurants as b'
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

    return result

def kde_rating(user_city):
    ''' show kernel rating distribution of all restaurants in a city 

    Parameters
    ----------
    user_city: str
        name of a city

    Return
    ----------
    The kernel rating distribution of all restaurants in a city : fig
    '''
    text_list = []
    ra_list = []
    for bu in get_info_form_database(["name","CityName", "categories","rating"], {"CityName": user_city}):
        text_list.append("{} ({}): {}, rating: {}".format(bu[0], bu[1], bu[2], bu[3]))
        ra_list.append(bu[3])
    fig = ff.create_distplot([ra_list], ['rating'], bin_size=.2, 
                             show_hist=False, show_rug=False)
    fig.update_xaxes(title_text="rating", ticks="inside")
    fig.update_yaxes(title_text="Kernel Density", ticks="inside")
    fig.update_layout(font=dict(size=20, family='Calibri', color='black'),
                      template="ggplot2",
                      title={'text': "Kernel Rating Distribution"})
    print("Plotting")
    print('-' * 47)
    fig.write_html("rating_distribution.html", auto_open=True)
    return fig

def print_average_rating(params):
    ''' Caculate the average rating of all restaurants in a city 

    Parameters
    ----------
    params: dict
        A dictionary of param:value pairs

    Return
    ----------
    The average rating of all restaurants in a city: str
    '''
    info_list = get_info_form_database(['rating'], params)
    average = sum(float(rating[0]) for rating in info_list) / len(info_list)
    print(f'The average rating is {average}')
    print('-' * 47)

def plot_rating_distribution(params):
    ''' show the rating distribution of all restaurants in a city 

    Parameters
    ----------
    params: dict
        A dictionary of param:value pairs

    Return
    ----------
    The rating distribution of all restaurants in a city : fig
    '''
    info_list = get_info_form_database(['rating'], params)
    rating_list = [float(rating[0]) for rating in info_list]
    fig = ff.create_distplot([rating_list], ['Rating'], bin_size=0.5)
    fig.update_layout(font=dict(size=20, family='Calibri', color='black'),
                      template="ggplot2",
                      title={'text': "Rating Distribution"})
    print("Plotting")
    print('-' * 47)
    fig.write_html("rating.html", auto_open=True)

def plot_review_count_distribution(params):
    ''' show the review count distribution of all restaurants in a city 

    Parameters
    ----------
    params: dict
        A dictionary of param:value pairs

    Return
    ----------
    The review count distribution of all restaurants in a city : fig
    '''
    info_list = get_info_form_database(['review_count','name'], params)
    review_count_list = [float(review_count[0]) for review_count in info_list]
    name_list=[name[1] for name in info_list]

    bar_data = go.Bar(x=name_list, y=review_count_list)
    basic_layout = go.Layout(title="Review count Distribution")
    fig = go.Figure(data=bar_data, layout=basic_layout)
    fig.update_layout(font=dict(family='Calibri', color='black'),
                      template="ggplot2",
                      title={'text': "Review count Distribution"})
    print("Plotting")
    print('-' * 47)
    fig.write_html("scatter.html", auto_open=True)


def map_cities(user_city):
    ''' show the restaurant map in a city

    Parameters
    ----------
    user_city: str
        name of a city

    Return
    ----------
    The restaurant map: fig
    '''
    text_list = []
    lat_list = []
    lon_list = []
    rating_list = []
    for bu in get_info_form_database(["name", "CityName", "review_count", "Latitude", "Longitude", "rating"], {"CityName": user_city}):
        text_list.append("{} ({}): {}, rating: {}".format(bu[0], bu[1], bu[2], bu[5]))
        lat_list.append(bu[3])
        lon_list.append(bu[4])
        rating_list.append(bu[5])
    ave_lat = sum(lat_list) / len(lat_list)
    ave_lon = sum(lon_list) / len(lon_list)
    fig = go.Figure(
        go.Scattermapbox(
            lat=lat_list,
            lon=lon_list,
            mode='markers',
            marker=go.scattermapbox.Marker(size=15, color=rating_list,
                                           opacity=0.5,
                                           #symbol='star'
                                           colorbar=dict(title="ratings"),
                                           colorscale="sunset"),
            text=text_list,
        ))

    layout = dict(
        autosize=True,
        hovermode='closest',
        mapbox=go.layout.Mapbox(
            accesstoken=MAPBOX_TOKEN,
            bearing=0,
            center=go.layout.mapbox.Center(lat=ave_lat,
                                           lon=ave_lon),
            pitch=0,
            zoom=10),
        plot_bgcolor="slategrey",
        paper_bgcolor="lightyellow",
        width=1200,
        height=700
    )

    fig.update_layout(layout)
    print("----------------- Generating map -----------------")
    print(" ")
    fig.write_html("map.html", auto_open=True)

    return fig



if __name__ == "__main__":
    City_list=[]
    for city in build_city_information_list():
        City_list.append(city[1])
    print(" ")
    print("Welcome! This program provides you all the restaurant informations you want in the 100 most populous cities!")
    print("Let's start now!")
    print(" ")
    print("Here is the 100 largest cities in United States:")
    count=0
    for i in City_list:
        count+=1
        print(count,i)
    while True:
        print('-'*47)
        print("1.Choose a city to see the rating distribution.")
        print("2.Choose a city to see all the restaurants here.")
        print('-'*47)
        user_choice=input("Enter a number to get information or 'exit':")
        if user_choice.lower()=='exit':
            exit()
        elif user_choice.isnumeric():
            if int(user_choice) == 1:
                print(" ")
                city_input=input("Please enter a city you want to see the Kernel density distribution of rating:")
                if city_input in City_list:
                    print(" ")
                    kde_rating(city_input)
                else:
                    print('[Error] Please enter a proper city from above!')
            elif int(user_choice) == 2:
                while True:
                    flag = True
                    print(" ")
                    city_input1=input("Please input a city you want to see the restaurant information or back or exit:")
                    if city_input1 in City_list:
                        print(" ")
                        print("Here is all the restaurants in the city (sorted by ratings)!")
                        print(" ")
                        k=0
                        for i in get_restaurant_list(city_input1):
                            k+=1
                            print(k,i)
                        while True:
                            print('-'*47)
                            print("Now you have four choices:")
                            print("1. View the review count distribution.")
                            print("2. View the average rating.")
                            print("3. View the restaurant distribution map.")
                            print("4. Enter a restaurant you like to see the details.")
                            print('-'*47)
                            print(" ")
                            user_input=input("Please enter a number to get the corresponding information or back or exit:")
                            if user_input.isnumeric():
                                if int(user_input) == 1:
                                    print(" ")
                                    plot_review_count_distribution({"CityName": city_input1})
                                    print(" ")
                                    user_input1=input("Please enter any key to return or 'exit':")
                                    print(" ")
                                    if user_input1 == 'exit':
                                        exit()
                                    else:
                                        continue
                                elif int(user_input) == 2:
                                    print(" ")
                                    print("After caculation:")
                                    print_average_rating({"CityName": city_input1})
                                    print(" ")
                                    plot_rating_distribution({"CityName": city_input1})
                                    print(" ")
                                    user_input2=input("Please enter any key to return or 'exit':")
                                    print(" ")
                                    if user_input2 == 'exit':
                                        exit()
                                    else :
                                        continue
                                elif int(user_input) == 3:
                                    print(" ")
                                    map_cities(city_input1)
                                    print(" ")
                                    user_input3=input("Please enter any key to return or 'exit':")
                                    print(" ")
                                    if user_input3 == 'exit':
                                        exit()
                                    else:
                                        continue
                                elif int(user_input) == 4:
                                    print(" ")
                                    restaurant_input=input("Please enter a restaurant to see the details:")
                                    restaurant_list=[]
                                    for i in get_restaurant_list(city_input1):
                                        restaurant_list.append(i[0])
                                    if restaurant_input in restaurant_list:
                                        get_restaurant_detail(restaurant_input,city_input1)
                                        user_input4=input("Please enter any key to return or 'exit':")
                                        print(" ")
                                        if user_input4 == 'exit':
                                            exit()
                                        else:
                                            continue
                                    else:
                                        print(" ")
                                        print('[Error] Please enter a proper restaurant name!')
                                        print(" ")
                                else:
                                    print(" ")
                                    print('[Error] Please enter a proper number(1 or 2 or 3 or 4) or exit!')
                                    print('-'*47)
                                    print(" ")
                                    continue
                            elif user_input == 'exit':
                                exit()
                            elif user_input == 'back':
                                break
                            else:
                                print(" ")
                                print('[Error] Please enter a proper number (1 or 2 or 3 or 4) or enter "back" to choose another city or exit!')
                                print('-'*47)
                                print(" ")
                                continue
                    elif city_input1 == 'exit':
                        exit()
                    elif city_input1 == 'back':
                        break
                    else:
                        print(" ")
                        print('[Error] Please enter a proper city from above!')
                        print(" ")
                        continue
            else:
                print(" ")
                print('[Error] Please enter a proper number (1 or 2)!')
                print(" ")
                continue
        else:
            print(" ")
            print('[Error] Invalid input! Please enter a proper number (1 or 2) or exit!')
            print(" ")