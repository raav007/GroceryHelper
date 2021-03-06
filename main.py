from geolocation import Geolocation
from database import StoreInfoAccessor
from models import Location
from planning import TripPlanner
from flask import Flask

app = Flask(__name__)


def find_routes_given_ingredients(user_location, ingredients):
    """ Finds the best driving routes for the user to purchase
        all the needed ingredients.
        :param user_location: the user's starting location - Location
        :param ingredients: a comma-separated list of the ingredients the user needs - string
        :return a list of routes, sorted best to worst
    """
    Geolocation.load_lat_long_for_location(user_location)
    planner = TripPlanner(user_location)
    needed_items = ingredients.split(',')
    needed_items = [item.strip() for item in needed_items]
    print('Planning route from {} to get {}'.format(user_location, ', '.join(needed_items)))
    stores = get_stores_near_me(user_location, 20, 10)

    plans = planner.find_routes(needed_items, stores, 20, False)

    return plans


def get_stores_near_me(my_loc, radius, number):
    """ Get stores within a certain radius of user location.
        :param my_loc: location of the user - Location
        :param radius: search radius (miles)
        :param number: maximum number of stores to return
    """
    sia = StoreInfoAccessor()
    stores = sia.get_stores_in_zip_range(my_loc.zipcode-200, my_loc.zipcode+200)

    stores_in_range = []
    euc_dists = {}
    for s in stores:
        dist = Geolocation.get_euclidean_dist(my_loc, s.location)
        if dist <= radius:
            euc_dists[s.store_id] = dist
            stores_in_range.append(s)

    # Sort according to Euclidean distance
    stores_in_range.sort(key=lambda store: euc_dists[store.store_id])

    # Return the top _number_ of stores
    return stores_in_range[:number]

if __name__ == '__main__':
    with app.app_context():
        loc = Location('1000 Olin Way', 'Needham', 'MA', 2492)
        find_routes_given_ingredients(loc, ['A', 'B'])
