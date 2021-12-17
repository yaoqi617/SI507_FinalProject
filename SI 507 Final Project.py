from bs4 import BeautifulSoup
import requests
import json
import pandas as pd
import plotly.express as px
import numpy as np
from binary_tree import BST
from datetime import datetime
mapbox_token = 'input your token here'

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

#################################################
####### Create Cache Class   ####################
#################################################
class Cache:
    def __init__(self, filename):
        """Load cache from disk, if present"""
        self.filename = filename
        try:
            with open(self.filename, 'r') as cache_file:
                cache_json = cache_file.read()
                self.cache_diction = json.loads(cache_json)
        except:
            self.cache_diction = {}

    def _save_to_disk(self):
        """Save cache to disk"""
        with open(self.filename, 'w') as cache_file:
            cache_json = json.dumps(self.cache_diction)
            cache_file.write(cache_json)

    def get(self, identifier):
        """If unique identifier exists in the cache and has not expired, return the data associated with it from the request, else return None"""
        identifier = identifier.upper() # Assuming none will differ with case sensitivity here
        if identifier in self.cache_diction:
            data_assoc_dict = self.cache_diction[identifier]
            data = data_assoc_dict['values']
        else:
            data = None
        return data

    def set(self, identifier, data, expire_in_days):
        """Add identifier and its associated values (literal data) to the cache, and save the cache as json"""
        identifier = identifier.upper() # make unique
        self.cache_diction[identifier] = {
            'values': data,
            'timestamp': datetime.now().strftime(DATETIME_FORMAT),
            'expire_in_days': expire_in_days
        }

        self._save_to_disk()


#################################################
####### Create Natioal Park Class   #############
#################################################
class NationalPark():
    def __init__(self, count, type, name, desc, url, street, city, state, zip, latitude, longitude):
        self.type = type
        self.name = name
        self.description = desc
        self.url = url
        self.address_street = street
        self.address_city = city
        self.address_state = state
        self.address_zip = zip
        self.count = count
        self.cord = (latitude, longitude)

    def __str__(self):
        if (self.address_street == "Address Not Avaliable"):
            return ("Park {}: {} ({}). Address: {}".format(self.count, self.name, self.type, self.address_street).strip("\n\r"))
        else:
            return ("Park {}: {} ({}). Address: {}, {}, {} {}".format(self.count, self.name, self.type, self.address_street,
         self.address_city, self.address_state, self.address_zip).strip("\n\r"))


def create_id(site, topic, webUrl):
    return "{}_{}_{}.json".format(site, topic, webUrl)

# Read in zip to longitude & lagitude mapping file
zip_lat_long = pd.read_csv('Zip_Lat_Long.csv')

# Scrape each state with their nps webpage
def get_state_with_url():
    url = "https://www.nps.gov/index.htm"
    npsId = create_id("NPS", "States and websites", url)
    cache_file = "nps.json"
    cache = Cache(cache_file)
    response = cache.get(npsId)
    if response == None:
        response = requests.get(url).text
        cache.set(npsId, response, 1)

    soup = BeautifulSoup(response,features="html.parser")
    allStates = soup.find('ul', class_="dropdown-menu SearchBar-keywordSearch")
    states = allStates.find_all('li')
    lst = []
    #get state with website store in list
    baseUrl = "https://www.nps.gov"
    for state in states:
        stateAbbr = state.find('a').get('href')[7:9].upper()
        link = baseUrl + state.find('a').get('href')
        lst.append([stateAbbr, link])

    return lst

master = get_state_with_url()


########################################################
########## Scrape All National Parks in a State ########
########################################################

def get_sites_for_state(state_abbr):
    state_abbr = state_abbr.upper()
    for stateInfo in master:
        if (stateInfo[0] == state_abbr):
            stateUrl = stateInfo[1]

    #CACHING
    npsStateId = create_id("States", "Parks", stateUrl)
    cache_file = "parks.json"
    cache = Cache(cache_file)
    stateResponse = cache.get(identifier=npsStateId)
    if stateResponse == None:
        stateResponse = requests.get(stateUrl).text
        cache.set(npsStateId, stateResponse, 1)

    soup = BeautifulSoup(stateResponse, features="html.parser")
    allParks = soup.find('ul', id="list_parks")
    parks = allParks.find_all('li', class_ = "clearfix")
    list = []
    count = 1
    for park in parks:
        #get information for a park
        type = park.find('h2').text
        name = park.find('a').text
        description = park.find('p').text
        partialUrl = park.find('a').get('href')
        parkUrl = "https://www.nps.gov{}index.htm".format(partialUrl)

        #information for each park
        parkId = create_id("ParkInfo", "address", parkUrl)
        parkResponse = cache.get(parkId)
        if parkResponse == None:
            parkResponse = requests.get(parkUrl).text
            cache.set(parkId, parkResponse, 1)
        soup = BeautifulSoup(parkResponse, features="html.parser")
        #Get address for a park
        parkInfo = soup.find('p', class_ = "adr")
        #detail info for each park
        try:
            address_street = parkInfo.find(itemprop = "streetAddress").text
            address_street = address_street.strip("\n\r")
        except:
            address_street = None

        try:
            address_city = parkInfo.find(itemprop = "addressLocality").text
            address_city = address_city.strip("\n\r")
        except:
            address_city = None

        try:
            address_state = parkInfo.find(itemprop = "addressRegion").text
            address_state = address_state.strip("\n\r")
        except:
            address_state = None

        try:
            address_zip = parkInfo.find(itemprop = "postalCode").text
            address_zip = address_zip.replace(' ', '')
            latitude = zip_lat_long[zip_lat_long["ZIP"] == int(address_zip)]['LAT'].values[0]
            longitude = zip_lat_long[zip_lat_long["ZIP"] == int(address_zip)]['LNG'].values[0]
        except:
            address_zip = None
            latitude = None
            longitude = None

        #Disgard cases for mulitple location
        if (address_state == state_abbr):
            parks = NationalPark(count, type, name, description, parkUrl, address_street, address_city,
                                address_state, address_zip, latitude, longitude)
            list.append(parks)
            count = count + 1
    return list

lst = get_sites_for_state('MI')

################################################################
########## Define haversine formula to calc geo distance #######
################################################################
from math import radians, cos, sin, asin, sqrt

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in miles between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    try: 
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        # haversine formula 
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        r = 3956 
        return c * r
    except:
        return np.inf

########################################################
########## Find nearby places by zip & state #######
########################################################
class NearbyPlace():
    def __init__(self, name, dist):
        self.name = name
        self.dist = dist

    def __str__(self):
        return ("{} : geographical distance from this park to your location is {} miles".format(self.name, self.dist))


def nearByPlaces(zip_cd, state_abbr, park_dic):
    state_abbr = state_abbr.upper()
    if state_abbr in park_dic.keys():
        park_lst = park_dic[state_abbr]
    else:
        park_lst = get_sites_for_state(state_abbr)
    user_lat = zip_lat_long[zip_lat_long["ZIP"] == int(zip_cd)]['LAT'].values[0]
    user_lng = zip_lat_long[zip_lat_long["ZIP"] == int(zip_cd)]['LNG'].values[0]
    nearby_lst = []

    for park in park_lst:
        park_lat, park_lng = park.cord
        # print(user_lat, user_lng, park_lat, park_lng)
        nearby_lst.append(NearbyPlace(park.name, haversine(user_lng, user_lat, park_lng, park_lat)))

    # Put distance into BST and sort by distance
    bst = BST()
    for park in nearby_lst:
        bst.insert(park.dist)
    sorted_by_dist = bst.inorder([])
    treeFile = json.dumps(bst.jsonable())
    nearby_lst_sorted = []
    for distance in sorted_by_dist:
        for park in nearby_lst:
            if distance == park.dist:
                nearby_lst_sorted.append(park)
    return nearby_lst_sorted, treeFile

###############################################################
########## Plot Maps for all national parks in a state ########
###############################################################
def plot_map_for_state(state_abbr, park_dic):
    state_abbr = state_abbr.upper()
    if state_abbr in park_dic.keys():
        park_lst = park_dic[state_abbr]
    else:
        park_lst = get_sites_for_state(state_abbr)
    lst = []
    for park in park_lst:
        lat, lng = park.cord
        lst.append([park.name, lat, lng])
    df = pd.DataFrame(lst)
    df.columns = ['Park', 'Lat', 'Lng']
    px.set_mapbox_access_token(mapbox_token)
    fig = px.scatter_mapbox(df, lat="Lat", lon="Lng",color="Park",text="Park", 
        opacity=1.0,color_continuous_scale=px.colors.cyclical.IceFire, zoom=4.5, title="National Parks in {}".format(state_abbr))

    fig.show()
    return None

##################################################
########## Main Function User interaction ########
##################################################


def main():
    print("Welcome to the program! This program allows you to browse national parks near you!")
    print("-------------Instructions for Commands-------------")
    print("1. Find National Parks in the State you specify:")
    print("Please input the abbreviation of a state to give you a list of all national parks in that state.")
    print("2. Find National Parks near your current location:")
    print("You will need to input your zip code and the abbreviation of the state you want to visit. The program will list all national parks nearby in ascending order.")
    print("3. Plot the National Parks on the Map:")
    print("You will need to input the abbreviation of a state, and the program will plot all national parks in that state.")
    print("4. Exit:")
    print("Program will be terminated")
    print()
    choice = 0
    parks_lst_by_state = {}
    while choice != 4:
        choice = input("To use this program, please type in an integer number between 1 to 4.\n")
        try:
          choice = int(choice)
        except:
          print("--------------WARNING--------------")
          print("This is not a valid input.")
          print("-----------------------------------")

        if choice == 1:
            state_abbr = input("Please enter state abbreviation: \n")
            parks = get_sites_for_state(state_abbr)
            parks_lst_by_state[state_abbr] = parks
            for park in parks:
                print(park)

        elif choice == 2:
            zip_code = input("Please enter your zip code \n")
            user_st = input("Please input the abbreviation of the state you would like to go \n")
            zip_code = int(zip_code)
            while zip_code not in zip_lat_long['ZIP'].values:
              print("Zipcode is not found. Please try another nearby Zipcode")
              zip_code = input("Please enter your zip code \n")
              user_st = input("Please input the abbreviation of the state you would like to go \n")
              zip_code = int(zip_code)
            place, treeFile = nearByPlaces(zip_code, user_st, parks_lst_by_state)
            text_file = open("treeFile.txt", "w")
            n = text_file.write(treeFile)
            text_file.close()
            for park in place:
                print(park)

        elif choice == 3:
            user_st = input("Please input the abbreviation fo the state you want to see \n")
            plot_map_for_state(user_st, parks_lst_by_state)

        # elif choice != 4:
        #     print("--------------WARNING--------------")
        #     print("This is not a valid input. Please enter a command between 1 to 4. If you want to exit, enter 4")
        #     print("----------------END----------------")
    print()
    print("Thanks for using this program!")
    return None

if __name__ == '__main__':
    main()