from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from pymongo import MongoClient


_client = None


def get_application_collection():
    global _client

    if not settings.MONGODB_URI:
        raise ImproperlyConfigured('Set MONGODB_URI in your .env file to use the applications API.')

    if _client is None:
        _client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)

    return _client[settings.MONGODB_DATABASE]['applications']
