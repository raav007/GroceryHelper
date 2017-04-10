import copy


class TripPlanner:

    def __init__(self, starting_location, items_needed):
        self.stores = None
        self.starting_location = starting_location
        self.items_needed = items_needed

    def find_routes(self, needed_items, nearby_stores, max_distance):
        """ Finds all the possible routes to purchase the needed items within the specified search radius.
            NOTE: The list of stores passed may include stores outside the search radius. This method will
            filter the list based on search radius before finding routes.
            :param needed_items: list of grocery items needed
            :param nearby_stores: list of nearby stores - [Store]
            :param max_distance: maximum distance (in miles) of stores from starting location to include in route - int
            :return a list of TripPlans sorted best to worst - [TripPlan]
        """
        # Filter the stores to only include stores with a Euclidean distance within the specified search radius
        self.stores = [store for store in nearby_stores if store.calc_euc_dist_from(self.starting_location) <= max_distance]  # TODO Reference correct Euclidean distance method
        base_plan = TripPlan(first_stop=self.starting_location)
        routes = self.__find_path_continuations(base_plan, [], needed_items, 2*max_distance)  # Max distance is the diameter of the circle

        # TODO Sort routes best to worst

        return routes

    def __find_path_continuations(self, base_plan, visited, items_needed, max_dist_btwn_stops):
        """ Recursively finds all the paths to other stores starting at a given store.

            :param base_plan: a TripPlan to extend - TripPlan
            :param visited: dictionary of Stores visited (key is store ID) - [int: Store]
            :param items_needed: list of items still needed - [string?]  # TODO Decide on type for item
            :return list of TripPlans
        """
        possible_paths = list()
        for next_store in self.stores:
            if next_store not in visited:
                visited.append(next_store)
                # Get list of items available at this store
                items_here = None  # TODO
                # If this store doesn't have any items, skip it
                if items_here == 0:
                    continue

                # Figure out which items we have left to get
                items_left = [item for item in items_needed not in items_here]

                # Calculate distance to here from previous stop
                distance_to_store = next_store.calc_euc_dist_from(base_plan.last_stop)  # TODO Call right method

                # Get the score for the store
                score = self.__get_store_score(items_here, items_needed, distance_to_store, max_dist_btwn_stops)

                # Now plan paths to all of the unvisited stores
                new_plans_from_here = self.__find_path_continuations(next_store, copy.copy(visited), items_left, max_dist_btwn_stops)
                for plan_extension in new_plans_from_here:
                    base_plan_copy = TripPlan(base_plan=base_plan)
                    base_plan_copy.add_stop(TripStop(base_plan.last_stop, next_store, distance_to_store, score))
                    possible_paths.append(TripPlan.combine(base_plan_copy, plan_extension))

        return possible_paths

    # Weights for scoring
    ITEMS_WEIGHT = 2
    DISTANCE_WEIGHT = 1

    def __get_store_score(self, items_at_store, items_needed, distance_to_store, max_dist_btwn_stops):
        """ Get a score for the store for ranking purposes. Scores range from 0 to 1 (inclusive), with
            1 being optimal and 0 being the worst possible score.
            :param items_at_store: a list of items at the store
            :param items_needed: a list of items still needed
            :param distance_to_store: the distance to the store in miles - int
            :param max_dist_btwn_stops: the maximum distance the user can travel between two stops (used for normalizing distance scores) - int
        """
        # Calculate percentage of items not available at store
        number_have = len([x for x in items_needed if x not in items_at_store])
        percent_do_not_have = number_have / len(items_needed)

        # Calculate distance score
        distance_score = distance_to_store / max_dist_btwn_stops

        # Take the weighted average and return the score
        return (percent_do_not_have * self.ITEMS_WEIGHT + distance_score * self.DISTANCE_WEIGHT)/(self.ITEMS_WEIGHT + self.DISTANCE_WEIGHT)


class TripPlan:

    def __init__(self, **options):
        if options['base_plan']:  # We're extending an existing route
            base_plan = options['base_plan']
            self.first_stop = base_plan.first_stop  # TODO Probably going to run into referencing problems. Need to copy base_plan?
            self.last_stop = base_plan.last_stop
            self.score = base_plan.score
        elif options['first_stop']:  # We're starting a new route, and we know our first stop
            self.first_stop = options['first_stop']
            self.last_stop = self.first_stop
            self.score = self.first_stop.score
        else:  # We're starting a new route, but we don't know our first stop yet
            self.first_stop = None
            self.last_stop = None
            self.score = 0

    def add_stop(self, new_stop):
        """ Adds a new stop to the plan.

            :param new_stop: the new stop - TripStop
        """
        if self.first_stop:  # Check if we already have at least one stop
            self.last_stop.next_stop = new_stop
            self.last_stop = new_stop
        else:  # No existing stops, so this is our first one
            self.first_stop = new_stop
            self.last_stop = new_stop
        self.score += new_stop.score

    @staticmethod
    def combine(first_plan, second_plan):
        """ Combines the two TripPlans into one. """
        first_plan.last_stop = second_plan.first_stop
        second_plan.first_stop = first_plan.last_stop

    @staticmethod
    def clone(first_stop):
        """ Creates a new copy this plan.

            :param first_stop: the first stop in the trip
            :return a new TripPlan with the same attributes as the old one
        """
        first_stop_new = TripStop(first_stop.prev_stop, first_stop.store, first_stop.dist_from_prev, first_stop.score)
        prev_stop = first_stop_new
        while prev_stop.next_stop:
            prev_stop.next_stop = TripStop(prev_stop.prev_stop, prev_stop.store, prev_stop.dist_from_prev, prev_stop.score)
        return first_stop_new


class TripStop:
    """ Node for planning trips """

    def __init__(self, prev_stop, store, dist_from_prev, score):
        """
        :param prev_stop: previous stop on this trip - TripStop
        :param store: store at this stop - Store
        :param dist_from_prev: distance from previous - int
        :param score: score of this store given item needs - int
        """
        self.prev_stop = prev_stop
        self.store = store
        self.dist_from_prev = dist_from_prev
        self.score = score
        self.next_stop = None
