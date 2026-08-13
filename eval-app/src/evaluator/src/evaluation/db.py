from .utils import Config
from pymongo import MongoClient

class MongoDB():

    def __init__(self, db_name, collection_name):
        client = MongoClient(f'mongodb://{Config.env_config['MONGO_USERNAME']}:{Config.env_config['MONGO_PASSWORD']}@{Config.env_config['MONGO_HOST']}:{Config.env_config['MONGO_PORT']}')
        self.db = client[db_name]
        self.collection = self.db[collection_name]

    def add(self, data: list[dict] | dict):
        if isinstance(data, list):
            self.collection.insert_many(data)
        elif isinstance(data, dict):
            self.collection.insert_one(data)
        else:
            raise Exception('Invalid data type. Data type must be either dict or list of dicts.')

    def exists(self, value=None):
        if value is not None:
            return self.getOne(value) is not None
        
        return self.collection.name in self.db.list_collection_names()
            
    def get(self, value):
        return self.collection.find(value)
    
    def getOne(self, value):
        return self.collection.find_one(value)

    def getAll(self):
        return self.collection.find({})
        
    def drop(self):
        self.collection.drop()

    def update(self, filter: dict, value: dict):
        self.collection.update_one(filter, {"$set": value})

    def addOrUpdate(self, filter: dict, value: dict):
        if self.exists(filter):
            self.update(filter, value)
        else:
            self.add(value)

    def __len__(self):
        return self.collection.count_documents({})

class EvalDB(MongoDB):

    def __init__(self, collection_name: str):
        super().__init__(db_name=Config.env_config['MONGO_EVAL_DB_NAME'], collection_name=collection_name)

class EvalConfigDB(MongoDB):

    def __init__(self, collection_name: str):
        super().__init__(db_name=Config.env_config['MONGO_EVAL_CONFIG_DB_NAME'], collection_name=collection_name)