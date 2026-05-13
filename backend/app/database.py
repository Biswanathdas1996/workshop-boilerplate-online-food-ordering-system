from functools import lru_cache
import os
from pymongo import MongoClient
from pymongo.database import Database


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    mongodb_uri = os.getenv('MONGODB_URI')
    if not mongodb_uri:
        raise RuntimeError('MONGODB_URI is not configured.')
    return MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)


def get_database() -> Database:
    client = get_mongo_client()
    return client.get_default_database()


# Collection names
USERS_COLLECTION = "users"
MENU_ITEMS_COLLECTION = "menu_items"
CARTS_COLLECTION = "carts"
ORDERS_COLLECTION = "orders"
INVOICES_COLLECTION = "invoices"
NOTIFICATIONS_COLLECTION = "notifications"
VENUES_COLLECTION = "venues"
RESTAURANT_PROFILES_COLLECTION = "restaurant_profiles"
