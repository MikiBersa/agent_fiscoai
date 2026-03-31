from datetime import datetime

import certifi
from bson import ObjectId
from pymongo import MongoClient

# MONGODB_CONNECTION = "mongodb://admin:admin123@localhost:27017/"
MONGODB_CONNECTION = "mongodb://192.168.178.29:27017/"

# mongodb+srv://<db_username>:<db_password>@atlascluster.szzzwuw.mongodb.net/?retryWrites=true&w=majority&appName=AtlasCluster
class MongoDBConnection:
    def __init__(self, collection_name="log", azure=True, db_name="VerticalAI"):
        # Configurazione
        # self.mongo_cluster_uri = "mongodb+srv://aiagentsystemopenai:yjTwh90bDHHFMyjl@verticalai.qgef8.mongodb.net/?retryWrites=true&w=majority&appName=VerticalAI"

        if azure:
            # self.mongo_cluster_uri = "mongodb://normativa:i3LEvZYYfe2C6BrPxNwHRAqL3YLuacU3j7a2IS7mdvYMBIeNiAlHSf0u5cXGXj8gqWw1jxi0VIjGACDbYNN1Cg==@normativa.mongo.cosmos.azure.com:10255/?ssl=true&retryWrites=false"
            self.mongo_cluster_uri = MONGODB_CONNECTION
        else:
            self.mongo_cluster_uri = "mongodb+srv://enricomartinelli:StUUQCsIwPXBfSRG@verticalai.lgaluzb.mongodb.net/?retryWrites=true&w=majority&appName=VerticalAI&tlsAllowInvalidCertificates=true"

        self.azure = azure
        self.db_name = db_name
        self.collection_name = collection_name
        self.db = None
        self.client = None

    def __get_timestamp(self):
        # Valore da impostare
        timestamp = datetime.strptime(
            "2025-04-11T16:40:47.617+00:00", "%Y-%m-%dT%H:%M:%S.%f%z"
        )
        return timestamp

    def connection(self):
        ca = certifi.where()
        # Connessione al cluster MongoDB
        self.client = MongoClient(
            self.mongo_cluster_uri,
            # tlsCAFile=ca,
            connectTimeoutMS=100000,
            socketTimeoutMS=100000,
        )

        if self.db_name != None and self.db_name != "":
            self.db = self.client[self.db_name]

        if self.collection_name != None and self.collection_name != "":
            self.collection = self.db[self.collection_name]

    def set_collection(self, name_collection):
        # db = self.client[self.db_name]
        if self.db != None:
            self.collection = self.db[name_collection]
            self.collection_name = name_collection

    def set_db_name(self, name_db):
        if self.client != None:
            self.db = self.client[name_db]
        # self.collection = self.db[name_collection]

    def get_norma(self, name_collection):
        self.set_collection(name_collection)
        docs = self.collection.find(
            {}, {"_id": 1, "id": 1, "data": 1, "parent_id": 1, "text": 1}
        )

        return docs
