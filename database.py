import sqlite3
from flask import g
import os
from models import Store, Location, FoodItem


class DatabaseAccessor:

    FILENAME = 'grocery_db.sqlite'  # name of the sqlite database file
    DATABASE_PATH = '{}/{}'.format(os.path.dirname(os.path.realpath(__file__)), FILENAME)

    def __init__(self, db=None):
        """ Instantiates a new DatabaseAccessor object.
            :param db: (optional) an existing connection to the database to use, rather than create a new one
        """
        if db:
            self.db = db
        else:
            self.db = getattr(g, '_database', None)
            if self.db is None:
                self.db = g._database = sqlite3.connect(self.DATABASE_PATH)
            # Make the database query return a list of dictionaries rather than cursor rows
            self.db.row_factory = self.__make_dicts

    def _query_db(self, query, args=(), one=False):
        """ Queries (reads) the database.
            :param query: a SQL query statement (e.g. 'select * from stores') - string
            :param args: some SQL argument?
            :param one: if True, will return only the first result, otherwise all
            :return a tuple of dictionaries, where each element in the tuple represents a result in the database.
             The keys of the dictionaries correspond to the database column name and the values are the cell values.
        """
        cur = self.db.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        return (rv[0] if rv else None) if one else rv

    def _save(self, table_name, data, id=None):
        """ Saves data to the database, either by adding a new row (if id is None) or
            by updating an existing row (if is is not None).
            :param table_name: the table in the database to save the data to
            :param data: a dictionary where the keys correspond to the column names and the
             values correspond to the values to store in those cells
            :param id: the identifier of the row to update in the database
            :return the row id of the added new row, or 0 if an existing row was successfully updated
        """
        # Remove any items with a value of None
        cols = list(data.keys())
        vals = list(data.values())
        cols_clean = list()
        vals_clean = list()
        for i in range(len(cols)):
            val = vals[i]
            if val is not None:
                cols_clean.append(str(cols[i]))
                if isinstance(val, int):
                    vals_clean.append(str(val))
                elif isinstance(val, str):
                    vals_clean.append('"{}"'.format(val))
                else:
                    raise TypeError('Expected str or int, got {}.'.format(type(val)))
        # Create the SQL and execute it
        cursor = self.db.cursor()
        if id:
            sql_set = list()
            for i in range(len(cols_clean)):
                sql_set.append('{}={}'.format(cols_clean[i], vals_clean[i]))
            sql = "UPDATE {tn} SET {set} WHERE id={id}". \
                format(tn=table_name, set=','.join(sql_set), id=id)
            cursor.execute(sql, ())
            row_id = None
        else:
            cols_sql = ','.join(cols_clean)
            vals_sql = ','.join(vals_clean)
            sql = "INSERT INTO {tn} ({cn}) VALUES ({vals})". \
                format(tn=table_name, cn=cols_sql, vals=vals_sql)
            row_id = cursor.execute(sql, ()).lastrowid

        self.db.commit()
        return row_id if row_id else 0

    def close(self):
        """ Closes the database connection """
        if self.db is not None:
            self.db.close()

    @staticmethod
    def __make_dicts(cursor, row):
        """ Converts the results of a database query into a list of dictionaries, where each key corresponds to the
            column name and each value is the value of the cell for that row.
        """
        return dict((cursor.description[idx][0], value)
                    for idx, value in enumerate(row))


class DatabaseCreator:

    SQL_CREATES = ['CREATE TABLE {} ('
                   'id INTEGER PRIMARY KEY AUTOINCREMENT,'
                   'store_id CHAR(15),'
                   'name CHAR(50),'
                   'location_id INT,'
                   'items CHAR(200));'.format(Store.DB_TABLE_NAME),

                   'CREATE TABLE {} ('
                   'id INTEGER PRIMARY KEY AUTOINCREMENT,'
                   'street_address CHAR(50),'
                   'city CHAR(20),'
                   'state CHAR(15),'
                   'zipcode INT,'
                   'latitude DOUBLE,'
                   'longitude DOUBLE,'
                   'store_id CHAR(15));'.format(Location.DB_TABLE_NAME),

                   'CREATE TABLE {} ('
                   'id INTEGER PRIMARY KEY AUTOINCREMENT,'
                   'item_id CHAR(15),'
                   'name CHAR(200),'
                   'aisle CHAR(15),'
                   'category CHAR(20),'
                   'description CHAR(100),'
                   'image_url CHAR(200));'.format(FoodItem.DB_TABLE_NAME)]

    def init_db(self):
        """ Creates the SQLite database file on the disk and creates the desired tables within the database """
        # Connecting to the database file
        conn = sqlite3.connect(DatabaseAccessor.DATABASE_PATH)
        c = conn.cursor()

        # Create new tables
        for sql in self.SQL_CREATES:
            c.execute(sql)

        # Committing changes and closing the connection to the database file
        conn.commit()
        conn.close()


class StoreInfoAccessor(DatabaseAccessor):
    def __init__(self, db=None):
        super().__init__(db)
        self.loc_info_accessor = LocationInfoAccessor(self.db)

    def get_all_stores(self):
        """ Gets all of the stores in the database
            :return a list of Store objects - [Store]
        """
        store_sql = 'SELECT * FROM {}'.format(Store.DB_TABLE_NAME)
        query_res = self._query_db(store_sql, ())
        res = list()
        for row in query_res:
            res.append(self.__parse_store(row))
        return res

    def get_stores_in_zip_range(self, start_zip, end_zip):
        """ Gets all the stores located in the given ZIP code range.
        :param start_zip: the starting ZIP code - int
        :param end_zip: the ending ZIP code (also searched) - int
        :return: a list of stores found in the given range - [Store]
        """
        locations = LocationInfoAccessor().get_locations_in_zip_range(start_zip, end_zip)
        res = list()
        for loc in locations:
            store_id = loc.store_id
            store = self.get_store(store_id)
            res.append(store)
        return res

    def get_store(self, store_id):
        """ Gets the information for one store.
        :param store_id: the store's alphanumeric ID
        :return: a Store object containing the store's information - Store
        """
        store_sql = 'SELECT * FROM {} WHERE id={}'.format(Store.DB_TABLE_NAME, store_id)
        query_res = self._query_db(store_sql, (), True)
        return self.__parse_store(query_res)

    def __parse_store(self, row):
        """ Internal method for parsing the results of a database query and saving it into a Store object """
        loc = self.loc_info_accessor.get_location(row['location_id'])
        store = Store(
            row['store_id'],
            row['name'],
            loc,
            row['id']
        )
        return store

    def save_store(self, store, location_info_accessor=None):
        """
        Saves a store to the database.
        :param store: the database to store
        :param location_info_accessor: (optional) a LocationInfoAccessor (with a database connection) to use to save the location
        :return: the new row ID in the database if a new record, None if updating existing
        """
        if location_info_accessor:
            location_info_accessor.save_location(store.location)
        data = {
            'store_id': store.store_id,
            'name': store.name,
            'location_id': store.location.id,
        }
        new_id = self._save(store.DB_TABLE_NAME, data, store.id)
        # If we just added a store to the database, set the id attribute on the Store object
        if new_id:
            store.id = new_id
        return new_id


class LocationInfoAccessor(DatabaseAccessor):
    def __init__(self, db=None):
        super().__init__(db)

    def get_all_locations(self):
        """ Gets all of the locations stored in the database.
        :return: a Location object containing all the location's information - Location
        """
        location_sql = 'SELECT * FROM {}'.format(Location.DB_TABLE_NAME)
        query_res = self._query_db(location_sql, ())
        res = list()
        for row in query_res:
            res.append(self.__parse_location(row))
        return res

    def get_locations_in_zip_range(self, start_zip, end_zip):
        """ Gets the information for locations in ZIP codes in the given range.
        :param start_zip: the starting ZIP code - int
        :param end_zip: the ending ZIP code (also searched) - int
        :return: a list of Location objects in the given ZIP range - [Location]
        """
        sql = 'SELECT * FROM {} WHERE zipcode>={} AND zipcode<={}'.format(Location.DB_TABLE_NAME, start_zip, end_zip)
        query_res = self._query_db(sql, ())
        res = list()
        for row in query_res:
            res.append(self.__parse_location(row))
        return res

    def get_location(self, location_id):
        """ Gets the information for a location.
        :param location_id: the unique ID for the location - int
        :return: a Location object containing all the location's information - Location
        """
        sql = 'SELECT * FROM {} WHERE id={}'.format(Location.DB_TABLE_NAME, location_id)
        row = self._query_db(sql, (), True)
        return self.__parse_location(row)

    @staticmethod
    def __parse_location(row):
        """ Internal method for parsing the results of a database query and saving it into a Location object """
        loc = Location(
            row['street_address'],
            row['city'],
            row['state'],
            row['zipcode'],
            row['latitude'],
            row['longitude'],
            row['id'],
            row['store_id']
        )
        return loc

    def save_location(self, location):
        """" Saves a location to the database """
        data = {
            'store_id': location.store_id,
            'street_address': location.street_address,
            'city': location.city,
            'state': location.state,
            'zipcode': location.zipcode,
            'latitude': location.latitude,
            'longitude': location.longitude,
        }
        new_row_id = self._save(location.DB_TABLE_NAME, data, location.id)
        if new_row_id:
            location.id = new_row_id
        return new_row_id


class FoodItemInfoAccessor(DatabaseAccessor):
    def __init__(self, db=None):
        super().__init__(db)

    def get_food_item_by_row_id(self, row_id):
        """ Gets the information for a food item.
        :param row_id: the unique database row ID for the food item - int
        :return: a FoodItem object containing all the food item's information - FoodItem
        """
        sql = 'SELECT * FROM {} WHERE id={}'.format(FoodItem.DB_TABLE_NAME, row_id)
        row = self._query_db(sql, (), True)
        return self.__parse_food_item(row)

    def get_food_item_by_item_id(self, item_id):
        """ Gets the information for a food item.
        :param item_id: the unique Supermarket API item ID or the UPC code - string
        :return: a FoodItem object containing all the food item's information - FoodItem
        """
        sql = 'SELECT * FROM {} WHERE id={}'.format(FoodItem.DB_TABLE_NAME, item_id)
        row = self._query_db(sql, (), True)
        return self.__parse_food_item(row)

    def get_foods_by_name(self, name):
        """
        Queries the database for all of the items whose name contains the given words.
        :param name: the word(s) to use when searching for a matching item name - string
        :return: 
        """
        # TODO Use a more robust method for string escaping and SQL injection prevention
        name = name.replace("'", "''")
        name = name.replace('"', '""')
        sql = 'SELECT * FROM {} WHERE name LIKE "%{}%"'.format(FoodItem.DB_TABLE_NAME, name)
        rows = self._query_db(sql, ())
        res = list()
        for row in rows:
            res.append(self.__parse_food_item(row))
        return res


    @staticmethod
    def __parse_food_item(row):
        """ Internal method for parsing the results of a database query and saving it into a Location object """
        item = FoodItem(
            row['item_id'],
            row['name'],
            row['aisle'],
            row['category'],
            row['description'],
            row['image_url'],
            row['id']
        )
        return item

    def save_item(self, item):
        """
        Saves the item to the database
        :param item: the item to be saved - FoodItem
        """
        data = {
            'item_id': item.item_id,
            'name': item.name,
        }
        #     'aisle': item.aisle,
        #     'category': item.category,
        #     'description': item.description,
        #     'image_url': item.image_url
        # }
        new_row_id = self._save(item.DB_TABLE_NAME, data, item.id)
        if new_row_id:
            item.id = new_row_id
        return new_row_id
