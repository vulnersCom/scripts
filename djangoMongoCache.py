# -*- coding: utf-8 -*-
#  Based on ---->
#  Author:
#  Karol Sikora <karol.sikora@laboratorium.ee>, (c) 2012
#  Alireza Savand <alireza.savand@gmail.com>, (c) 2013, 2014, 2015
#
#
# Remake by isox@vulners.com
# Using TTL index collection

try:
    import cPickle as pickle
except ImportError:
    import pickle
import base64
import re
from datetime import datetime, timedelta

import pymongo
from django.core.cache.backends.base import BaseCache


class MongoDBCache(BaseCache):
    def __init__(self, location, params):
        BaseCache.__init__(self, params)
        self.location = location
        options = params.get('OPTIONS', {})
        self._host = options.get('HOST', 'localhost')
        self._port = options.get('PORT', 27017)
        self._username = options.get('USERNAME')
        self._password = options.get('PASSWORD')
        self._database = options.get('DATABASE', 'django_cache')
        self._collection = location
        self._db, self._coll = self.initMongoConnection()

    def initMongoConnection(self):
        if self._username is not None:
            self.connection = pymongo.MongoClient(
                'mongodb://{0}:{1}@{2}:{3}/{4}'.format(self._username, self._password, self._host, self._port,
                                                       self._database))
        else:
            self.connection = pymongo.MongoClient('mongodb://{0}:{1}/'.format(self._host, self._port))

        # Initialize key index
        self.connection[self._database][self._collection].ensure_index('key', background=True)
        # Initialize TTL index
        # Elements will be deleted after 5 seconds expiration date will be passed
        self.connection[self._database][self._collection].ensure_index('expires', background = True, expireAfterSeconds = 5)

        return self.connection[self._database], self.connection[self._database][self._collection]


    def make_key(self, key, version=None):
        """
         Additional regexp to remove $ and . cachaters,
        as they cause special behaviour in mongodb
        """
        key = super(MongoDBCache, self).make_key(key, version)

        return re.sub(r'\$|\.', '', key)

    def add(self, key, value, timeout=None, version=None):
        """
            Set a value in the cache if the key does not already exist. If
            timeout is given, that timeout will be used for the key; otherwise
            the default cache timeout will be used.

            Returns True if the value was stored, False otherwise.
        """
        key = self.make_key(key, version)
        self.validate_key(key)

        return self._base_set('add', key, value, timeout)

    def set(self, key, value, timeout=None, version=None):
        """
            Set a value in the cache. If timeout is given, that timeout will be
            used for the key; otherwise the default cache timeout will be used.
        """
        key = self.make_key(key, version)
        self.validate_key(key)

        return self._base_set('set', key, value, timeout)

    def _base_set(self, mode, key, value, timeout=None):

        timeout = timeout or self.default_timeout

        # Only UTC here for Mongo auto-purge

        now = datetime.utcnow()
        expires = now + timedelta(seconds=timeout)

        #

        pickled = pickle.dumps(value, pickle.HIGHEST_PROTOCOL)
        encoded = base64.encodebytes(pickled).strip()

        if mode == 'set':
            # Set sets new data. And there is no matter, that key exists
            self._coll.update({'key':key} ,{'key':key, 'data': encoded, 'expires': expires}, upsert = True)

        elif mode == 'add':
            if self._coll.find_one({'key': key}):
                return False
            self._coll.insert({'key': key, 'data': encoded, 'expires': expires})

        return True

    def get(self, key, default=None, version=None):
        """
            Fetch a given key from the cache. If the key does not exist, return
            default, which itself defaults to None.
        """
        key = self.make_key(key, version)
        self.validate_key(key)

        data = self._coll.find_one({'key': key})
        if not data:
            return default

        unencoded = base64.decodebytes(data['data'])
        unpickled = pickle.loads(unencoded)

        return unpickled

    def get_many(self, keys, version=None):
        """
            Fetch a bunch of keys from the cache. For certain backends (memcached,
            pgsql) this can be *much* faster when fetching multiple values.

            Returns a dict mapping each key in keys to its value. If the given
            key is missing, it will be missing from the response dict.
        """
        out = {}
        parsed_keys = {}

        for key in keys:
            pkey = self.make_key(key, version)
            self.validate_key(pkey)
            parsed_keys[pkey] = key

        data = self._coll.find({'key': {'$in': parsed_keys.keys()}})
        for result in data:
            unencoded = base64.decodebytes(result['data'])
            unpickled = pickle.loads(unencoded)
            out[parsed_keys[result['key']]] = unpickled

        return out

    def delete(self, key, version=None):
        """
            Delete a key from the cache, failing silently.
        """
        key = self.make_key(key, version)
        self.validate_key(key)
        self._coll.remove({'key': key})

    def has_key(self, key, version=None):
        """
            Returns True if the key is in the cache and has not expired.
        """
        key = self.make_key(key, version)
        self.validate_key(key)
        data = self._coll.find_one({'key': key})

        return data is not None

    def clear(self):
        """Remove *all* values from the cache at once."""
        self._coll.remove(None)

    def close(self, **kwargs):
        """Close the cache connection"""
        return self.connection.close()
