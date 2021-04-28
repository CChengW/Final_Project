# Final_Project

Description:
-----------
This project allows users to query the restaurant information of 100 most populous cities according to the command line prompt. Users can view restaurant maps and three related information charts of 100 cities, as well as the detailed information of all restaurants in these cities.

Before getting started:
-----------
* 1.Yelp Fusion API
URLs: https://api.yelp.com/v3/businesses/search
This project uses Yelp Fusion API to get all the restaurant data. Yelp Fusion API uses private API Keys to authenticate requests, so you need to apply an API Key to access it. 
Visit https://www.yelp.com/fusion to get your own API Key. 
Name it API_KEY to run this project.
* 2.Mapbox
This project uses Mapbox to precise location data and create restaurant maps. You need to apply an mapbox token to use this toolbox.
Visit https://www.mapbox.com/ to get your own secret key. 
Name it MAPBOX_TOKEN to run this project.

* Required Python packages:
requests, beautifulsoup4, bs4, sqlite3, time, plotly

User guide:
-----------
Install the required python packages, then run the final_project.py file.  
First, the program provides a list of 100 cities you can choose from.     
Users can choose to see the fitting curve of rating distribution or get the list of all restaurants in the city.

    1.Choose a city to see the rating distribution.
    2.Choose a city to see all the restaurants here.
If choose 1, users can input a city to see the fitting curve of rating distribution (Using Kernel Density Estimation).   
If choose 2, users can input a city to see the list of all restaurants in this city sorted by rating.

Users will then have four options:

    1. View the review count distribution.
    2. View the average rating.
    3. View the restaurant distribution map.
    4. Enter a restaurant you like to see the details.
For 1, 2 & 3, users will see the corresponding charts and maps, for 4 they can input any restaurants in the list to see the detailed information.  
Note that users can choose to back to superior menu or exit at any time.
